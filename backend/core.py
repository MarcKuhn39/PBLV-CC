import time
import datetime
import sys
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

WEEKDAY = ("monday", "tuesday", "wednesday",
           "thursday", "friday", "saturday", "sunday")

ARDUINO_PORT = "ARDUINO_PORT"


def init_and_start_core():
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
    def __init__(self, ser):
        threading.Thread.__init__(self)
        self.ser = ser
        self.current_counter = 0
        self.max_counter = 0
        self.current_queueSize = 0
        self.events = []
        self.thread_event = threading.Event()

    def run(self):
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
        def change_counter(counter, port):
            if port == 0:
                return counter + 1
            if port == 2:
                return counter - 1
            return counter

        def customers_per_timespan(values):
            return reduce(change_counter, values)

        # only get events which occurred during opening hours
        start = datetime.time(11, 0, 0)
        end = datetime.time(14, 0, 0)
        current_values = current_day[
            (current_day["time"].dt.time >= start)
            & (current_day["time"].dt.time <= end)
        ]

        # find number of customers at the end of timerange
        timerange = pd.date_range(
            start="11:00:00", end="14:00:00", freq="30min")
        current_values = (
            current_values.groupby(pd.Grouper(key="time", freq="30min"))
            .aggregate(customers_per_timespan)
            .reindex(timerange)
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

        # add current values to old values
        new_day_count = old_day_count + 1
        new_values = old_values.add(
            current_values, fill_value=0).div(new_day_count)
        new_values.insert(loc=0, column="day", value=new_day_count)
        new_values.to_csv(DAILY_FILE_PATH, index=False)

    def write_weekly(self):
        # maybe just write down the day and the maximum per day for now
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
        with open(CURRENT_FILE_PATH, "w", encoding="Ascii") as current_file:
            # update current values continuesly
            # read from standard in for testing purposes
            while True:

                if self.thread_event.is_set():
                    break

                if self.ser.in_waiting > 0:
                    serial_data = ""
                    serial_data = self.ser.readline()

                    match self.extract_from_serial(serial_data):
                        case "PORT0":  # customers entering cafeteria and queue
                            self.increment_counter()
                            self.add_event(0)
                            self.write_values(current_file)
                        case "PORT1":  # customers leaving queue
                            self.decrement_queue()
                            self.add_event(1)
                            self.write_values(current_file)
                        case "PORT2":  # customers leaving cafeteria
                            self.decrement_counter()
                            self.add_event(2)
                            self.write_values(current_file)
                        case "EXIT":
                            break
                        case _:
                            # ignore
                            pass

                time.sleep(0.1)

            current_file.close()

    def write_values(self, current_file):
        timeNow = datetime.datetime.now()
        arrivals_5m = 0
        for (time, port) in reversed(self.events):
            if (timeNow - datetime.datetime.strptime(time, "%H:%M:%S")).seconds > 100:
                break
            if port == 0:
                arrivals_5m += 1
        estimated_queue_time = self.current_queueSize/(arrivals_5m)
        line = f"{self.current_counter}\n{self.current_queueSize}\n{estimated_queue_time}"
        current_file.seek(0)
        current_file.write(line)
        current_file.truncate()
        current_file.flush()

    def add_event(self, port_number):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        row = [timestamp, port_number]
        self.events.append(row)

    def extract_from_serial(self, data):
        return data.decode("Ascii").rstrip("\n")

    def increment_counter(self):
        updated_counter = (
            (self.current_counter + 1)
            if self.current_counter < COUNTER_LIMIT_MAX
            else COUNTER_LIMIT_MAX
        )
        self.current_queueSize = self.current_queueSize + 1
        self.current_counter = updated_counter
        self.max_counter = max(self.current_counter, self.max_counter)

    def decrement_counter(self):
        updated_counter = (
            (self.current_counter - 1)
            if self.current_counter > COUNTER_LIMIT_MIN
            else COUNTER_LIMIT_MIN
        )
        self.current_counter = updated_counter

    def decrement_queue(self):
        self.current_queueSize = self.current_queueSize - 1

    def reset_state(self):
        self.current_counter = 0
        self.max_counter = 0
        self.events = []
        self.thread_event.clear()


def get_current_day():
    day = datetime.date.today()
    return (day, WEEKDAY[day.weekday()])


if __name__ == "__main__":
    print("Core started")
    init_and_start_core()
    print("Core stopped")
