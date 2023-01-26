from flask import Flask, jsonify
import csv

# Creates a REST API which provides the current number of customers present and the estimated
# queue time as well as daily and weekly summaries.

app = Flask(__name__)
CURRENT_FILE_PATH = "current.txt"
DAILY_FILE_PATH = "daily.txt"
WEEKLY_FILE_PATH = "weekly.txt"


@app.get("/")
def get_base():
    return "Welcome to the Backend!"


@app.get("/current")
def get_current():
    data = create_curent_data()
    response = {"currentVisitorCount": data[0], "estimatedQueueTimeInMin": data[1]}
    return jsonify(response)


@app.get("/full")
def get_full():
    data = create_full_data()
    response = {
        "currentVisitorCount": data[0][0],
        "estimatedQueueTimeInMin": data[0][1],
        "stats": {"maxPerDayStat": data[1], "maxPerHourStat": data[2]},
    }
    return jsonify(response)


def create_curent_data():
    with open(CURRENT_FILE_PATH, mode="r", encoding="Ascii") as current_file:
        lines = current_file.readlines()
        current_visitor_count = lines[0].strip("\n")
        estimated_queue_time_in_min = lines[1]
        return (current_visitor_count, estimated_queue_time_in_min)


def create_full_data():
    current_data = create_curent_data()
    max_per_day_stat = read_daily_values()
    max_per_hour_stat = read_weekly_values()
    return (current_data, max_per_day_stat, max_per_hour_stat)


def read_daily_values():
    with open(DAILY_FILE_PATH, mode="r", encoding="Ascii") as daily_file:
        daily_reader = csv.DictReader(daily_file, fieldnames=["hour", "count"])
        daily_values = []
        for line in daily_reader:
            daily_values.append(line)
        return daily_values


def read_weekly_values():
    with open(WEEKLY_FILE_PATH, mode="r", encoding="Ascii") as weekly_file:
        weekly_reader = csv.DictReader(weekly_file, fieldnames=["day", "count"])
        weekly_values = []
        for line in weekly_reader:
            weekly_values.append(line)
        return weekly_values


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
