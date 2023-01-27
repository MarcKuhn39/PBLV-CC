import time
import datetime
import csv
import sys
import os
from decouple import config
import serial
import pandas as pd

# from apscheduler.schedulers.blocking import BlockingScheduler

PATH = os.path.dirname(os.path.abspath(__file__))
CURRENT_FILE_PATH = os.path.join(PATH, "current_test.txt")
DAILY_FILE_PATH = os.path.join(PATH, "daily_test.txt")
WEEKLY_FILE_PATH = os.path.join(PATH, "weekly_test.txt")

COUNTER_LIMIT_MIN = 0
COUNTER_LIMIT_MAX = 400

WEEKDAY = ("monday", "tuesday", "wednesday", "thursday", "friday")

ARDUINO_PORT = "ARDUINO_PORT"


def run():
    port = config(ARDUINO_PORT)
    ser = serial.Serial(port=port, baudrate=9600, timeout=None)
    core = Core(ser)
    core.write_current_counter()


class Core:
    def __init__(self, ser):
        self.ser = ser
        self.current_counter = 0
        self.max_counter = 0
        self.events = []

    def write_current_counter(self):
        with open(CURRENT_FILE_PATH, "w", encoding="Ascii") as current_file:
            i = 0
            # update current values continuesly
            # read from standard in for testing purposes
            for line in sys.stdin:

                if True:
                    serial_data = ""
                    # serial_data = self.ser.readline()
                    serial_data = line.rstrip()

                    # match self.extract_from_serial(serial_data):
                    match serial_data:
                        case "PORT0":
                            self.increment_counter()
                            self.add_event(0)
                            self.write_values(current_file)
                        case "PORT1":
                            self.increment_counter()
                            self.add_event(1)
                            self.write_values(current_file)
                        case "PORT2":
                            self.increment_counter()
                            self.add_event(2)
                            self.write_values(current_file)
                        case "EXIT":
                            break
                        case _:
                            # ignore
                            pass

                    i = i + 1

                time.sleep(0.1)

            # dump data for one day
            df = pd.DataFrame(self.events, columns=["time", "port"])
            print(df)
            self.reset_counters()
            current_file.close()

    def write_values(self, current_file):
        estimated_queue_time = 0
        line = f"{self.current_counter}\n{estimated_queue_time}"
        current_file.seek(0)
        current_file.write(line)
        current_file.truncate()
        current_file.flush()

    def add_event(self, port_number):
        timestamp = datetime.datetime.now()
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


if __name__ == "__main__":
    print("Core started")
    run()
    print("Core stopped")
