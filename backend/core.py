"""Core of the backend.

Receives events over a serial connection, handles reading and writing values as well as scheduling.
More information about the API can be found in README.md.
"""
import time
import datetime
import os
import threading
from functools import reduce
from decouple import config
from apscheduler.schedulers.blocking import BlockingScheduler
import serial
import pandas as pd

PATH = os.path.dirname(os.path.abspath(__file__))
CURRENT_FILE_PATH = os.path.join(PATH, "current.txt")
DAILY_FILE_PATH = os.path.join(PATH, "daily.txt")
WEEKLY_FILE_PATH = os.path.join(PATH, "weekly.txt")

COUNTER_LIMIT_MIN = 0
COUNTER_LIMIT_MAX = 400

AVG_CUSTOMER_COUNT = 10

WEEKDAY = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

ARDUINO_PORT = "ARDUINO_PORT"

IN_PORT = 0
QUEUE_PORT = 1
OUT_PORT = 2

FMT = "%H:%M:%S"


def init_and_start_core():
    """Initializes and starts the core.

    During the initialization process, the name of the serial connection of the Arduino is read
    from an environment variable. This environment variable needs to be set in a .env file in the
    backend folder.

    A scheduler will also be started to stop the cores operation every day from monday to friday,
    by sending an event at midnight.
    """
    port = config(ARDUINO_PORT)
    ser = serial.Serial(port=port, baudrate=9600, timeout=None)
    core = Core(ser)
    core.start()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        core.thread_event.set, trigger="cron", day_of_week="mon-fri", hour=0
    )
    scheduler.start()


class Core(threading.Thread):
    """
    Core thread, which handles reading from a serial connection as well as file operations.

    Attributes
    ----------
    ser : serial.Serial
        The serial connection to the Arduino.
    current_counter: int
        The number of customers inside the cafeteria.
    max_counter: int
        The maximum number of customers inside the cafeteria.
    current_queue_size: int
        The number of customers waiting in line at the cash register.
    events: list
        Holds all the events received over the serial connection. The events contain a timestamp
        and the number of the sensor.
    thread_event: Event
        A thread event, which can be set by another thread to end the current operation of the core.
    """

    def __init__(self, ser):
        threading.Thread.__init__(self)
        self.ser: serial.Serial = ser
        self.current_counter = 0
        self.max_counter = 0
        self.current_queue_size = 0
        self.events = []
        self.thread_event = threading.Event()

    def run(self):
        """
        Starts the core.

        The core detects events coming over a serial connection from the Arduino.
        Counter values will be changed based on incoming events.

        When stopped through an event, the core starts updating the weekly and daily values,
        as well as resetting its own state to start receiving events for the next day.
        """
        while True:
            # start write for current day
            self.write_current_counter()

            # dump data for one day
            current_day = pd.DataFrame(self.events, columns=["time", "port"])
            current_day["time"] = pd.to_datetime(current_day["time"])

            self.write_daily(current_day)
            self.write_weekly()

            # write for last day has finished
            self.reset_state()

    def write_daily(self, current_day: pd.DataFrame):
        """Updates daily values with the current values.

        The total numbers of days passed as well as the average number of customers at the end of
        a 30 minute intervall will be saved to a filed.
        At the end of the day, a new average value gets calculated from the old and current data.
        The number of days passed also gets incremented by one.
        """

        def change_counter(counter, port):
            """Helper function.

            Increments counter by one for every customer who arrived and decrements the counter
            for every customer who left.
            """
            if port == 0:
                return counter + 1
            if port == 2:
                return counter - 1
            return counter

        def customers_per_timespan(values):
            """Calculates the number of customers at the end of a list of events."""
            return reduce(change_counter, values)

        # only get events which occurred during opening hours
        start = datetime.time(11, 0, 0)
        end = datetime.time(14, 0, 0)
        current_values = current_day[
            (current_day["time"].dt.time >= start)
            & (current_day["time"].dt.time <= end)
        ]

        # find number of customers at the end of 30 minute timerange
        timerange = pd.date_range(start="11:00:00", end="14:00:00", freq="30min")
        current_values = (
            current_values.groupby(pd.Grouper(key="time", freq="30min"))
            .aggregate(customers_per_timespan)
            .reindex(timerange)  # reindex to include timeranges with no customers
        )
        current_values = current_values.transpose().reset_index(drop=True)
        current_values = current_values.set_axis(
            ["t1", "t2", "t3", "t4", "t5", "t6", "t7"], axis=1, copy=False
        )

        # read old values and extract days
        old_values = pd.read_csv(DAILY_FILE_PATH, index_col=False)
        old_day_count = old_values.iat[0, 0]
        old_values = (old_values[old_values.columns[1:]] * old_day_count).reset_index(
            drop=True
        )

        # add current values to old values by building new average
        new_day_count = old_day_count + 1
        new_values = old_values.add(current_values, fill_value=0).div(new_day_count)
        new_values.insert(loc=0, column="day", value=new_day_count)
        new_values.to_csv(DAILY_FILE_PATH, index=False)

    def write_weekly(self):
        """Writes the maximum number of customers per day to a file."""
        current_day = get_current_day()
        max_per_day = self.max_counter

        old_values = pd.read_csv(WEEKLY_FILE_PATH, index_col=False)
        current_values = pd.DataFrame(
            {
                "date": [current_day[0]],
                "weekday": [current_day[1]],
                "count": [max_per_day],
            },
        )
        new_values = pd.concat([old_values, current_values])
        new_values.to_csv(WEEKLY_FILE_PATH, index=False)

    def write_current_counter(self):
        """Receives events over a serial connection and updates current values.

        This function reads events over a serial connection coming from an Arduino.
        Detected events will be used to update the total number of customers
        as well as the number of customers inside the queue.

        There are three types of events:

            PORT0: Customer entered cafeteria and queue.
            PORT1: Customer left queue.
            PORT2: Customer left cafeteria.

        The current values will be written to a file every time an event occurs.
        This operation only stoppes when explicitly signaled by a thread event.
        """
        with open(CURRENT_FILE_PATH, "w", encoding="Ascii") as current_file:

            while not self.thread_event.is_set():

                if self.ser.in_waiting > 0:
                    serial_data = ""
                    serial_data = self.ser.readline()

                    match self.extract_from_serial(serial_data):
                        case "PORT0":  # customers entering cafeteria and queue
                            self.increment_counter()
                            self.add_event(IN_PORT)
                            self.write_values(current_file)
                        case "PORT1":  # customers leaving queue
                            self.decrement_queue()
                            self.add_event(QUEUE_PORT)
                            self.write_values(current_file)
                        case "PORT2":  # customers leaving cafeteria
                            self.decrement_counter()
                            self.add_event(OUT_PORT)
                            self.write_values(current_file)
                        case "EXIT":
                            break
                        case _:
                            # ignore
                            pass

                time.sleep(0.1)

            current_file.close()

    def write_values(self, current_file):
        estimated_queue_time = self._avg_waiting_time(15)
        line = f"{self.current_counter}\n{self.current_queueSize}\n{estimated_queue_time}"
        current_file.seek(0)
        current_file.write(line)
        current_file.truncate()
        current_file.flush()

    def calculate_estimated_queue_time(self):
        """Calculates the estimated queue time"""
        estimated_queue_time = 0
        customers = AVG_CUSTOMER_COUNT
        for i in range(AVG_CUSTOMER_COUNT):
            val = self._get_waiting_time_of_customer(i)
            if val == -1:
                customers -= 1
                continue
            estimated_queue_time += self._get_waiting_time_of_customer(i)
        return estimated_queue_time / (customers * 60)

    def add_event(self, port_number):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        row = [timestamp, port_number]
        self.events.append(row)

    def extract_from_serial(self, data):
        """Extracts data coming from the serial connection."""
        return data.decode("Ascii").rstrip("\n")

    def increment_counter(self):
        """Increments the counter for the number of customers.

        The counter value will not be incremented when the maximum number of customers is reached.
        This fuction also increments the counter for the number of customers inside the
        queue.
        """
        self.current_counter = min(COUNTER_LIMIT_MAX, self.current_counter + 1)
        self.current_queueSize = self.current_queueSize + 1
        self.max_counter = max(self.current_counter, self.max_counter)

    def decrement_counter(self):
        """Decrements the counter for the number of customers.

        The counter value will not be decremented when the minimum number of customers is reached.
        """
        self.current_counter = max(COUNTER_LIMIT_MIN, self.current_counter - 1)

    def decrement_queue(self):
        """Decrements the counter for the number of customers inside the queue.

        The counter value will not be decremented when the queue is empty.
        """
        self.current_queue_size = max(0, self.current_queue_size - 1)

    def reset_state(self):
        """Resets the state of the core to its intitial state."""
        self.current_counter = 0
        self.max_counter = 0
        self.current_queue_size = 0
        self.events = []
        self.thread_event.clear()

    def _avg_waiting_time(self, person_count):
        """Calculates the average waiting time for the last person_count customers
        """
        # old queue size
        old_queue_size = self.current_queueSize + 1
        # extract port 0 and port 1 events from self.events
        port0_events = [event[0]
                        for event in reversed(self.events) if event[1] == 0]
        port1_events = [event[0]
                        for event in reversed(self.events) if event[1] == 1]

        # collect combined end and begin time deltas
        time_deltas = []
        actual_person_count = 0
        for i in range(person_count):
            if i >= len(port1_events) or i+old_queue_size >= len(port0_events):
                break
            actual_person_count += 1
            end_time = datetime.datetime.strptime(port1_events[i], FMT)
            begin_time = datetime.datetime.strptime(
                port0_events[i+old_queue_size], FMT)
            time_deltas.append((end_time - begin_time).seconds)
        if (actual_person_count == 0):
            return 0
        return sum(time_deltas) / (actual_person_count*60)


def get_current_day():
    """Returns the date and name of the current day."""
    day = datetime.date.today()
    return (day, WEEKDAY[day.weekday()])


if __name__ == "__main__":
    print("Core started")
    init_and_start_core()
    print("Core stopped")
