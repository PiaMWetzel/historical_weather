#Author: Pia Wetzel

from flask import Flask, render_template, redirect, jsonify
from datetime import datetime
import pandas as pd
import numpy as np
import math, requests, json, pytz, time
from Temperature import Temperature
import matplotlib.pyplot as plt
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
scheduler = BackgroundScheduler()
temp_data = {}
csv_file = "CA_LA_USC.csv"
days_in_month = {
    "January": 31,
    "February": 29,
    "March": 31,
    "April": 30,
    "May": 31,
    "June": 30,
    "July": 31,
    "August": 31,
    "September": 30,
    "October": 31,
    "November": 30,
    "December": 31,
}
temperature_today = Temperature(0, 0, 0)


def get_plot1(x, y, title, filename):
    Data = {"Years": x[0 : len(x) - 1], "Temperature": y[0 : len(y) - 1]}
    df = pd.DataFrame(Data, columns=["Years", "Temperature"])
    df.plot(x="Years", y="Temperature", kind="scatter")
    plt.scatter(x[len(x) - 1], y[len(y) - 1], color="red")
    label = "Today"
    plt.annotate(label, (x[len(x) - 1], y[len(y) - 1]))

    axes = plt.axes()
    f = np.linspace(0, len(x) - 1, num=5)
    axes.set_xticks(f)

    plt.ylabel("Temperatures in Fahrenheit")
    plt.title(title)
    plt.savefig(filename)

#creates scatterplots comparing today's low and high to historical lows and highs from the same day
def get_plot(todays_temps):

    tmax_all = [list(v.values())[0]["tmax"] for v in todays_temps]
    tmin_all = [list(v.values())[0]["tmin"] for v in todays_temps]
    x = [list(v.keys())[0] for v in todays_temps]
    date = temperature_today.get_month_day()
    get_plot1(
        x,
        tmax_all,
        f"Temperatures on {date} in Los Angeles since 1921 (Day)",
        "static/images/highs.png",
    )
    get_plot1(
        x,
        tmin_all,
        f"Temperatures on {date} in Los Angeles since 1921 (Night)",
        "static/images/lows.png",
    )


@app.route("/error")
def error():
    return render_template("error.html")

#accesses the National Weather Service API to gather today's temperature low, high,
#icon, and detailed forecast
def get_lows_and_highs():
    response = requests.get("https://api.weather.gov/gridpoints/LOX/152,43/forecast")
    current_obj = response.json()["properties"]["periods"][0]
    next_obj = response.json()["properties"]["periods"][1]
    high = current_obj["temperature"]
    low = next_obj["temperature"]
    icon = current_obj["icon"]
    detailed_forecast = current_obj["detailedForecast"]
    return high, low, icon, detailed_forecast

#creates dictionary from data in .csv file for faster lookup
def fill_dict():
    temp_data = {
        month + " " + str(day): []
        for month in days_in_month.keys()
        for day in range(1, days_in_month[month] + 1)
    }
    return temp_data

#returns data related to historical temperature maximums (TMAX)
def get_high_min_max(todays_temps):

    tmax_all = [list(v.values())[0]["tmax"] for v in todays_temps]
    # exclude today's temperature
    tmax_all = tmax_all[0 : len(tmax_all) - 1]
    max_high = max(tmax_all)
    min_high = min(tmax_all)
    high_perc = round(
        100
        - 100
        * (
            len([t for t in tmax_all if t > temperature_today.get_high()])
            / (len(tmax_all) - 1)
        ),
        2,
    )
    max_date = [
        list(v.keys())[0]
        for v in todays_temps
        if list(v.values())[0]["tmax"] == max_high
    ]
    min_date = [
        list(v.keys())[0]
        for v in todays_temps
        if list(v.values())[0]["tmax"] == min_high
    ]
    return max_high, min_high, high_perc, max_date, min_date

#returns data related to historical temperature minimums (TMIN)
def get_low_min_max(todays_temps):
    tmin_all = [list(v.values())[0]["tmin"] for v in todays_temps]
    # exclude today's temperature
    tmin_all = tmin_all[0 : len(tmin_all) - 1]
    max_low = max(tmin_all)
    min_low = min(tmin_all)
    low_perc = round(
        100
        - 100
        * (
            len([t for t in tmin_all if t > temperature_today.get_low()])
            / (len(tmin_all) - 1)
        ),
        2,
    )
    max_date = [
        list(v.keys())[0]
        for v in todays_temps
        if list(v.values())[0]["tmin"] == max_low
    ]
    min_date = [
        list(v.keys())[0]
        for v in todays_temps
        if list(v.values())[0]["tmin"] == min_low
    ]
    return max_low, min_low, low_perc, max_date, min_date

#writes today's temperature to .csv
def add_temperature_to_file():

    date = temperature_today.get_date()
    high = temperature_today.get_high()
    low = temperature_today.get_low()

    date_str = date.strftime("%Y-%m-%d")
    df1 = pd.read_csv("csv/" + csv_file)
    df2 = pd.DataFrame(
        [["NA", "Downtown USC", date, high, low]],
        columns=["STATION", "NAME", "DATE", "TMAX", "TMIN"],
    )
    last_saved_date = df1["DATE"][len(df1["DATE"]) - 1]

    if last_saved_date != date_str:
        df3 = df1.append(df2, ignore_index=True)
        df3.to_csv("csv/" + csv_file, index=False)

#is executed once per day to gather new temperature data
def start():

    la_temps = pd.read_csv("csv/" + csv_file)
    test = []
    temp_data = fill_dict()

    months = list(days_in_month.keys())
    for i in range(len(la_temps["DATE"])):
        year, month, day = la_temps["DATE"][i].split("-")
        tmax = la_temps["TMAX"][i]
        tmin = la_temps["TMIN"][i]

        temp_data[months[int(month) - 1] + " " + str(int(day))].append(
            {year: {"tmax": tmax, "tmin": tmin}}
        )
        test.append(months[int(month) - 1])
    # set temperature
    set_temp()
    # add new forecast to file
    add_temperature_to_file()

    return temp_data

#creates new temperature object with current day's temperature values
def set_temp():
    high, low, icon, detailed_forecast = get_lows_and_highs()
    temperature_today.set_values(
        high, low, datetime.now().date(), icon, detailed_forecast
    )


#displays index page
@app.route("/")
def st():

    # get today's temperature info
    low = temperature_today.get_low()
    high = temperature_today.get_high()
    icon = temperature_today.get_icon()
    detailed_forecast = temperature_today.get_detailed_forecast()
    date = temperature_today.get_month_day()
    # max_temp, max_year, tmax_hotter_than, min_temp, min_year,tmin_hotter_than = find_hottest_day(temp_data)
    max_high, min_high, high_perc, max_high_date, min_high_date = get_high_min_max(
        temp_data[date]
    )
    max_low, min_low, low_perc, max_low_date, min_low_date = get_low_min_max(
        temp_data[date]
    )
    past_temp_info = {
        "current_date": date,
        "date_highest_high": max_high_date[0],
        "date_lowest_high": min_high_date[0],
        "highest_high": max_high,
        "lowest_high": min_high,
        "high_perc": high_perc,
        "date_highest_low": max_low_date[0],
        "date_lowest_low": min_low_date[0],
        "highest_low": max_low,
        "lowest_low": min_low,
        "low_perc": low_perc,
    }

    get_plot(temp_data[temperature_today.get_month_day()])
    return render_template(
        "st.html",
        high=high,
        low=low,
        icon=icon,
        detailed_forecast=detailed_forecast,
        past_temp_info=past_temp_info,
    )


# -------------JOB SCHEDULE----------------


def scheduled():
    global temp_data
    temp_data = start()

print('ytytyt')
#scheduler executes 'start()' function once per day 
#to collect new temperature data
scheduler.start()
scheduled()
job = scheduler.add_job(scheduled, "cron", hour=0, minute=1)

if __name__ == "__main__":

    print('runnint')
    app.run()