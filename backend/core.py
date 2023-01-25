import time
import datetime
import csv
import serial

# from apscheduler.schedulers.blocking import BlockingScheduler

CURRENT_FILE_PATH = "current_test.txt"
DAILY_FILE_PATH = "daily_test.txt"
WEEKLY_FILE_PATH = "weekly_test.txt"

COUNTER_LIMIT_MIN = 0
COUNTER_LIMIT_MAX = 400

MIN_TIME = "11:00:00"
MAX_TIME = "14:00:00"

WEEKDAY = ("monday", "tuesday", "wednesday", "thursday", "friday")


def run():
    # minimal example which only updates the current values
    port = "COM3"  # needs to be configured, device dependant
    ser = serial.Serial(port=port, baudrate=9600, timeout=None)
    core = Core(ser)
    core.write_current_counter()

    # reset counters for next interval
    core.reset_counters()


class Core:
    def __init__(self, ser):
        self.ser = ser
        self.current_counter = 0
        self.max_counter = 0

    def write_current_counter(self):
        i = 0
        # update current values continuesly
        # limit number of activations for testing purposes
        while i < 100:

            if self.ser.in_waiting > 0:
                serial_data = ""
                serial_data = self.ser.readline()

                match self.extract_from_serial(serial_data):
                    case "PORT0":
                        self.increment_counter()
                    case "PORT1":
                        self.increment_counter()
                    case "PORT2":
                        self.increment_counter()
                    case _:
                        # ignore
                        pass

                # overwrite current values
                with open(CURRENT_FILE_PATH, "w", encoding="Ascii") as f:
                    estimated_queue_time = 0
                    line = f"{self.current_counter}\n{estimated_queue_time}"
                    f.write(line)

                i = i + 1
                time.sleep(0.1)

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
