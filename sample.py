# ============================================================
#  generate_sample_data.py
#  Creates a FAKE usage_log.csv so the usage report has data to analyse.
#  Run this once, before choosing "Usage report" in Seat_Sync.py.
#  Warning: it replaces any existing usage_log.csv.
# ============================================================

import csv
import os
import random
from datetime import datetime, timedelta

LOG_FILE = "usage_log.csv"
TIME_FORMAT = "%Y-%m-%d %H:%M"

DAYS = 14               # how many past days to simulate
STAYS_PER_DAY = 25      # how many students per day
BREAK_LIMIT = 30        # same as in Seat_Sync.py

# Spot -> zone, and how popular each spot is (higher = busier).
# Quiet Zone is made busier on purpose so the report has a pattern to find.
ZONES = {"A1": "Quiet Zone", "A2": "Quiet Zone", "A3": "Quiet Zone", "A4": "Quiet Zone",
         "B1": "Group Zone", "B2": "Group Zone", "B3": "Group Zone", "B4": "Group Zone"}
POPULARITY = [4, 4, 4, 4, 2, 2, 1, 1]

# Hours students arrive and how likely each hour is.
# Busier around 10:00 and 15:00 to imitate real study peaks.
HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17]
HOUR_WEIGHTS = [3, 8, 6, 3, 3, 6, 8, 4, 2]


def add_event(rows, moment, student, spot, action):
    rows.append([moment.strftime(TIME_FORMAT), student, spot, ZONES[spot], action])


def main():
    if os.path.exists(LOG_FILE):
        answer = input(LOG_FILE + " already exists. Replace it? (yes/no): ").strip().lower()
        if answer != "yes":
            print("Cancelled. Nothing was changed.")
            return

    random.seed(42)             # same fake data every run (easier to test)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []

    for days_back in range(DAYS, 0, -1):
        day = today - timedelta(days=days_back)
        for _ in range(STAYS_PER_DAY):
            hour = random.choices(HOURS, weights=HOUR_WEIGHTS)[0]
            start = day + timedelta(hours=hour, minutes=random.randint(0, 59))
            student = str(random.randint(1000, 9999))
            spot = random.choices(list(ZONES), weights=POPULARITY)[0]

            add_event(rows, start, student, spot, "checkin")

            if random.random() < 0.12:
                # An abandoned spot: break -> flagged -> released
                break_time = start + timedelta(minutes=random.randint(20, 60))
                flag_time = break_time + timedelta(minutes=BREAK_LIMIT + 1)
                release_time = flag_time + timedelta(minutes=random.randint(5, 15))
                add_event(rows, break_time, student, spot, "break")
                add_event(rows, flag_time, student, spot, "flagged")
                add_event(rows, release_time, student, spot, "released")
            else:
                # A normal stay: checkout after 30 to 180 minutes
                end = start + timedelta(minutes=random.randint(30, 180))
                add_event(rows, end, student, spot, "checkout")

    rows.sort()                 # oldest event first (the report relies on this)

    with open(LOG_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "student_id", "spot_id", "zone", "action"])
        writer.writerows(rows)
    print(f"Created {LOG_FILE} with {len(rows)} simulated events.")


main()
