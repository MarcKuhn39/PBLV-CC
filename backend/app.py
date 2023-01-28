import os
import datetime
from flask import Flask, jsonify
import pandas as pd


# Creates a REST API which provides the current number of customers present and the estimated
# queue time as well as daily and weekly summaries.

app = Flask(__name__)

PATH = os.path.dirname(os.path.abspath(__file__))
CURRENT_FILE_PATH = os.path.join(PATH, "current.txt")
DAILY_FILE_PATH = os.path.join(PATH, "daily.txt")
WEEKLY_FILE_PATH = os.path.join(PATH, "weekly.txt")


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
    max_per_day_stat = read_weekly_values()
    max_per_hour_stat = read_daily_values()
    return (current_data, max_per_day_stat, max_per_hour_stat)


def read_daily_values():
    daily_values_df = pd.read_csv(DAILY_FILE_PATH, index_col=False)
    daily_values = []
    for column in daily_values_df.columns[1:]:
        count = daily_values_df[column].to_list()[0]
        value = {"hour": column, "count": count}
        daily_values.append(value)

    return daily_values


def read_weekly_values():
    weekly_values_df = pd.read_csv(WEEKLY_FILE_PATH, index_col=False)
    weekly_values_df["date"] = pd.to_datetime(weekly_values_df["date"])
    weekly_values_df = weekly_values_df[
        weekly_values_df["date"].dt.isocalendar().week
        == datetime.datetime.now().isocalendar().week
    ]
    weekly_values = []
    for _, row in weekly_values_df.iterrows():
        value = {"day": row["weekday"], "count": row["count"]}
        weekly_values.append(value)
    return weekly_values


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
