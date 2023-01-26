import time
import datetime
import csv
import serial
import pandas as pd

# from apscheduler.schedulers.blocking import BlockingScheduler

CURRENT_FILE_PATH = "current_test.txt"
DAILY_FILE_PATH = "daily_test.txt"
WEEKLY_FILE_PATH = "weekly_test.txt"

COUNTER_LIMIT_MIN = 0
COUNTER_LIMIT_MAX = 400

WEEKDAY = ("monday", "tuesday", "wednesday", "thursday", "friday")


def run():
    # minimal example which only updates the current values
    port = "COM3"  # needs to be configured, device dependant
    ser = serial.Serial(port=port, baudrate=9600, timeout=None)
    core = Core(ser)
    core.write_current_counter()


class Core:
    def __init__(self, ser):
        self.ser = ser
        self.current_counter = 0
        self.max_counter = 0
        self.events = pd.DataFrame(columns=["time", "port"], index=[0])

    def write_current_counter(self):
        with open(CURRENT_FILE_PATH, "w", encoding="Ascii") as current_file:
            i = 0
            # update current values continuesly
            # limit number of activations for testing purposes
            while i < 10:

                if self.ser.in_waiting > 0:
                    serial_data = ""
                    serial_data = self.ser.readline()

                    match self.extract_from_serial(serial_data):
                        case "PORT0":
                            self.increment_counter()
                            self.add_event(0)
                        case "PORT1":
                            self.increment_counter()
                            self.add_event(1)
                        case "PORT2":
                            self.increment_counter()
                            self.add_event(2)
                        case _:
                            # ignore
                            pass

                    # overwrite current values
                    estimated_queue_time = 0
                    line = f"{self.current_counter}\n{estimated_queue_time}"
                    current_file.write(line)
                    current_file.flush()
                    i = i + 1

                time.sleep(0.1)

            # dump data for one day
            print(self.events)
            self.reset_counters()

    def add_event(self, port_number):
        timestamp = datetime.datetime.now()
        row = pd.Series({"time": timestamp, "port": port_number})
        self.events = pd.concat([self.events, row.to_frame().T], ignore_index=True)

    def extract_from_serial(self, data):
        return data.decode("Ascii").rstrip("\n")

    def increment_counter(self):
        updated_counter = (
            (self.current_counter + 1)
            if self.current_counter < COUNTER_LIMIT_MAX
            else COUNTER_LIMIT_MAX
        )

        self.current_counter = updated_counter
        self.max_counter = max(self.current_counter, self.max_counter)

    def decrement_counter(self):
        updated_counter = (
            (self.current_counter - 1)
            if self.current_counter > COUNTER_LIMIT_MIN
            else COUNTER_LIMIT_MIN
        )
        self.current_counter = updated_counter

    def reset_counters(self):
        self.current_counter = 0
        self.max_counter = 0


def get_max_per_day():
    with open(DAILY_FILE_PATH, mode="r", encoding="Ascii") as daily_file:
        daily_reader = csv.DictReader(daily_file, fieldnames=["hour", "count"])
        max_count = 0
        for line in daily_reader:
            count = line["count"]
            max_count = max(count, max_count)
        return max_count


def get_current_day():
    day = datetime.date.today()
    return WEEKDAY[day.weekday]


def create_timestamps():
    timerange = range(660, 840, 30)
    timestamps = []
    for t in timerange:
        timestamp = f"{t // 60}:{t % 60}:00"
        timestamps.append(timestamp)

    return timestamps


if __name__ == "__main__":
    print("Core started")
    run()
    print("Core stopped")
