# ============================================================
#  LRC SeatSync - Study Spot Occupancy Management System
#  Course: Computational Thinking and Programming (2026CSAE100)
#
#  What it does:
#    - Students check in to a study spot, step away, return, check out
#    - Group Zone spots are booked by one group leader, who also enters
#      the number of people in the group
#    - Staff scan for spots left unattended too long, then release them
#    - Every event is saved in usage_log.csv
#    - Staff can view a usage report (peak hour, busiest zone, average stay)
#
#  Files used:
#    spots.csv        - the current state of every spot (created automatically)
#    usage_log.csv    - one row for every event (check-in, break, flag...)
#    usage_report.txt - the last report that staff generated
# ============================================================

import csv
import os
from datetime import datetime, timedelta

# ------------------------------------------------------------
#  SETTINGS  (change these to change how the system behaves)
# ------------------------------------------------------------
SPOTS_FILE = "spots.csv"
LOG_FILE = "usage_log.csv"
REPORT_FILE = "usage_report.txt"
TIME_FORMAT = "%Y-%m-%d %H:%M"
STAFF_PIN = "1221"  # change this to a new PIN before using the program in real life

# Group Zone rules.
#   A Group Zone spot is a table booked by ONE student (the group leader).
#   The leader also says how many people will sit there (including themselves).
#   The break and flag rules apply to the whole table, using the leader's ID.
GROUP_ZONE = "Group Zone"
MIN_GROUP_SIZE = 2
MAX_GROUP_SIZE = 6

# The three numbers below can change while the program runs.
#   break_limit  : minutes a student may be on break before the spot is flagged
#                  (staff can change it with option 11)
#   grace_period : minutes a flagged spot waits before staff may release it
#                  (staff can change it with option 11)
#   clock_offset : minutes added to the real clock (option 10, used only for demos)
#
# NOTE: because the log uses the same clock, events saved after option 10 carry
# the shifted ("demo") time, not the real time.
settings = {"break_limit": 30, "grace_period": 5, "clock_offset": 0}

# Column names of spots.csv
FIELDS = ["spot_id", "zone", "status", "student_id",
          "checkin_time", "break_start", "flag_time", "group_size"]

# Column names used by the earlier version (no group_size column).
# An old spots.csv with these columns is still accepted and upgraded.
OLD_FIELDS = FIELDS[:-1]

# The only statuses a spot can have
VALID_STATUSES = ["free", "occupied", "on_break", "flagged"]

# Used only the first time, when spots.csv does not exist yet.
# Change the zone names to match the real LRC.
DEFAULT_SPOTS = [
    ("A1", "Quiet Zone"), ("A2", "Quiet Zone"),
    ("A3", "Quiet Zone"), ("A4", "Quiet Zone"),
    ("B1", GROUP_ZONE), ("B2", GROUP_ZONE),
    ("B3", GROUP_ZONE), ("B4", GROUP_ZONE),
]


# ------------------------------------------------------------
#  TIME HELPERS
# ------------------------------------------------------------
def now():
    """Return the current time (plus any demo offset), without seconds."""
    current = datetime.now() + timedelta(minutes=settings["clock_offset"])
    return current.replace(second=0, microsecond=0)


def time_to_text(moment):
    """Turn a datetime into text like '2026-11-19 10:30' for saving."""
    return moment.strftime(TIME_FORMAT)


def minutes_since(text):
    """How many minutes have passed since the saved time 'text'?"""
    start = datetime.strptime(text, TIME_FORMAT)
    return (now() - start).total_seconds() / 60


def is_valid_time(text):
    """True if 'text' is a time saved in TIME_FORMAT."""
    try:
        datetime.strptime(text, TIME_FORMAT)
        return True
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------
#  FILE HANDLING
# ------------------------------------------------------------
def save_spots(spots):
    """Write the spots dictionary to spots.csv."""
    try:
        with open(SPOTS_FILE, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            for spot_id in spots:
                writer.writerow(spots[spot_id])
    except OSError:
        print("Error: could not save spots.csv. Is the file open in another program?")


def row_is_valid(row):
    """
    Check one row of spots.csv before the program trusts it.
    A hand-edited file with a blank or badly formatted time would
    otherwise crash the program later, inside minutes_since().
    """
    for field in FIELDS:
        if row[field] is None:              # row has fewer columns than expected
            return False
    if row["status"] not in VALID_STATUSES:
        return False
    if row["status"] == "on_break" and not is_valid_time(row["break_start"]):
        return False
    if row["status"] == "flagged" and not is_valid_time(row["flag_time"]):
        return False
    if row["group_size"] != "" and not row["group_size"].isdecimal():
        return False                        # group size must be blank or a number
    return True


def load_spots():
    """Read spots.csv into a dictionary. Create it if it does not exist."""
    spots = {}
    try:
        with open(SPOTS_FILE, newline="") as file:
            reader = csv.DictReader(file)
            old_format = (reader.fieldnames == OLD_FIELDS)
            if reader.fieldnames != FIELDS and not old_format:
                raise KeyError("columns")       # wrong or missing column names
            for row in reader:
                if old_format:                  # upgrade an old file: no group yet
                    row["group_size"] = ""
                if not row_is_valid(row):       # bad status or bad time value
                    raise KeyError("row")
                spots[row["spot_id"]] = row
    except FileNotFoundError:
        print("spots.csv not found. Creating a new one with default spots.")
        for spot_id, zone in DEFAULT_SPOTS:
            spots[spot_id] = {"spot_id": spot_id, "zone": zone, "status": "free",
                              "student_id": "", "checkin_time": "",
                              "break_start": "", "flag_time": "", "group_size": ""}
        save_spots(spots)
    except (KeyError, OSError):
        print("Error: spots.csv is damaged or unreadable. Fix or delete it and try again.")
        return None
    if len(spots) == 0:
        print("Error: spots.csv contains no spots. Fix or delete it and try again.")
        return None
    return spots


def log_event(student_id, spot_id, zone, action):
    """Add one row to usage_log.csv describing what just happened."""
    new_file = not os.path.exists(LOG_FILE)
    try:
        with open(LOG_FILE, "a", newline="") as file:
            writer = csv.writer(file)
            if new_file:
                writer.writerow(["timestamp", "student_id", "spot_id", "zone", "action"])
            writer.writerow([time_to_text(now()), student_id, spot_id, zone, action])
    except OSError:
        print("Error: could not write to usage_log.csv.")


# ------------------------------------------------------------
#  INPUT HELPERS  (always check input before using it)
# ------------------------------------------------------------
def ask_student_id():
    """Ask for a student ID. Return None if invalid."""
    student_id = input("Enter student ID: ").strip().upper().replace(" ", "")
    if not (student_id.isalnum()
            and student_id[0].isalpha()
            and student_id[-4:].isdecimal()
            and len(student_id) == 11):
        print("Error: Invalid student ID.")
        return None
    return student_id


def ask_spot_id(spots):
    """Ask for a spot ID. Return None if that spot does not exist."""
    spot_id = input("Enter spot ID: ").strip().upper()
    if spot_id not in spots:
        print("Error: That spot does not exist.")
        return None
    return spot_id


def ask_whole_number(question, minimum, maximum=None):
    """
    Ask a question that needs a whole number >= minimum
    (and <= maximum, if a maximum is given).
    Return the number, or None if the answer is not valid.
    (isdecimal is used because it accepts only characters that int() can convert.)
    """
    text = input(question).strip()
    if not text.isdecimal():
        print("Error: Please enter a whole number.")
        return None
    number = int(text)
    if number < minimum:
        print(f"Error: The number must be at least {minimum}.")
        return None
    if maximum is not None and number > maximum:
        print(f"Error: The number must be at most {maximum}.")
        return None
    return number


def student_has_spot(spots, student_id):
    """True if this student already holds any spot."""
    for spot_id in spots:
        if spots[spot_id]["student_id"] == student_id:
            return True
    return False


def get_my_spot(spots, allowed_statuses):
    """
    Ask for student ID and spot ID, then check that the spot really
    belongs to this student and is in one of the allowed statuses.
    Return the spot ID, or None if anything is wrong.
    """
    student_id = ask_student_id()
    if student_id is None:
        return None
    spot_id = ask_spot_id(spots)
    if spot_id is None:
        return None
    if spots[spot_id]["student_id"] != student_id:
        print("Error: That spot is not held by this student.")
        return None
    if spots[spot_id]["status"] not in allowed_statuses:
        print("Error: This action is not possible while the spot is "
              + spots[spot_id]["status"] + ".")
        return None
    return spot_id


def staff_login():
    """Ask for the staff PIN. Return True if it is correct."""
    pin = input("Enter staff PIN: ").strip()
    if pin == STAFF_PIN:
        return True
    print("Error: Wrong PIN.")
    return False


# ------------------------------------------------------------
#  STUDENT OPTIONS
# ------------------------------------------------------------
def view_spots(spots):
    """Show every spot with its zone, status, student and group size."""
    print("\n--- LRC STUDY SPOTS ---")
    print(f"{'Spot':<6}{'Zone':<14}{'Status':<11}{'Student':<13}{'Group'}")
    for spot_id in spots:
        spot = spots[spot_id]
        group = ""
        if spot["group_size"] != "":
            group = spot["group_size"] + " people"
        print(f"{spot_id:<6}{spot['zone']:<14}{spot['status']:<11}"
              f"{spot['student_id']:<13}{group}")


def check_in(spots):
    """
    A student claims a free spot.
    In the Group Zone the student is the group leader and also says
    how many people are in the group.
    """
    student_id = ask_student_id()
    if student_id is None:
        return
    spot_id = ask_spot_id(spots)
    if spot_id is None:
        return
    if spots[spot_id]["status"] != "free":
        print("Error: This spot is not available.")
        return
    if student_has_spot(spots, student_id):
        print("Error: You already hold a spot. Please check out first.")
        return

    spot = spots[spot_id]
    group_size = ""
    if spot["zone"] == GROUP_ZONE:
        group_size = ask_whole_number(
            f"Group size, including you ({MIN_GROUP_SIZE} to {MAX_GROUP_SIZE}): ",
            MIN_GROUP_SIZE, MAX_GROUP_SIZE)
        if group_size is None:
            return                          # invalid size: spot stays free
        group_size = str(group_size)

    spot["status"] = "occupied"
    spot["student_id"] = student_id
    spot["checkin_time"] = time_to_text(now())
    spot["break_start"] = ""
    spot["flag_time"] = ""
    spot["group_size"] = group_size
    log_event(student_id, spot_id, spot["zone"], "checkin")
    if group_size == "":
        print(f"Success! Student {student_id} checked in to spot {spot_id}.")
    else:
        print(f"Success! Student {student_id} checked in to spot {spot_id} "
              f"with a group of {group_size}.")


def step_away(spots):
    """A student starts a break. The break timer starts now."""
    spot_id = get_my_spot(spots, ["occupied"])
    if spot_id is None:
        return
    spot = spots[spot_id]
    spot["status"] = "on_break"
    spot["break_start"] = time_to_text(now())
    log_event(spot["student_id"], spot_id, spot["zone"], "break")
    print(f"Break started. Please return within {settings['break_limit']} minutes.")


def return_from_break(spots):
    """A student comes back before their spot is released."""
    spot_id = get_my_spot(spots, ["on_break", "flagged"])
    if spot_id is None:
        return
    spot = spots[spot_id]
    spot["status"] = "occupied"
    spot["break_start"] = ""
    spot["flag_time"] = ""
    log_event(spot["student_id"], spot_id, spot["zone"], "return")
    print("Welcome back! Your spot is yours again.")


def check_out(spots):
    """A student leaves for good, so the spot becomes free."""
    spot_id = get_my_spot(spots, ["occupied", "on_break", "flagged"])
    if spot_id is None:
        return
    spot = spots[spot_id]
    log_event(spot["student_id"], spot_id, spot["zone"], "checkout")
    print(f"Student {spot['student_id']} checked out of spot {spot_id}.")
    free_spot(spot)


def free_spot(spot):
    """Reset a spot so that it is free again."""
    spot["status"] = "free"
    spot["student_id"] = ""
    spot["checkin_time"] = ""
    spot["break_start"] = ""
    spot["flag_time"] = ""
    spot["group_size"] = ""


# ------------------------------------------------------------
#  STAFF OPTIONS
# ------------------------------------------------------------
def flag_overdue_spots(spots):
    """
    Look at every spot that is on break. If the student has been away
    longer than the break limit, flag the spot. Return how many spots
    were newly flagged.

    This runs AUTOMATICALLY every time the menu is about to be shown,
    so a spot is flagged the moment anyone uses the system after the
    limit has passed. Staff do not have to remember to do it.
    """
    found_new = 0
    for spot_id in spots:
        spot = spots[spot_id]
        if spot["status"] == "on_break":
            away = minutes_since(spot["break_start"])
            if away > settings["break_limit"]:       # strictly MORE than the limit
                spot["status"] = "flagged"
                spot["flag_time"] = time_to_text(now())
                log_event(spot["student_id"], spot_id, spot["zone"], "flagged")
                print(f"WARNING: Spot {spot_id} flagged. Student {spot['student_id']} "
                      f"has been away {int(away)} minutes.")
                found_new += 1
    return found_new


def scan_for_abandoned(spots):
    """Staff option: run the check on demand and list all flagged spots."""
    if not staff_login():
        return
    found_new = flag_overdue_spots(spots)
    if found_new == 0:
        print("Scan complete: no new abandoned spots.")

    print("\nCurrently flagged spots:")
    any_flagged = False
    for spot_id in spots:
        if spots[spot_id]["status"] == "flagged":
            print(f"  {spot_id}  (student {spots[spot_id]['student_id']}, "
                  f"flagged at {spots[spot_id]['flag_time']})")
            any_flagged = True
    if not any_flagged:
        print("  none")


def release_spot(spots):
    """
    Staff free a flagged spot, but only after the grace period has passed
    and only after confirming.
    """
    if not staff_login():
        return
    ready = []
    for spot_id in spots:
        spot = spots[spot_id]
        if spot["status"] == "flagged":
            waited = minutes_since(spot["flag_time"])
            if waited >= settings["grace_period"]:
                ready.append(spot_id)
            else:
                print(f"Spot {spot_id} is still in its grace period "
                      f"({int(waited)} of {settings['grace_period']} minutes).")
    if len(ready) == 0:
        print("No flagged spots are ready to be released.")
        return

    print("Spots ready to release: " + ", ".join(ready))
    spot_id = input("Enter spot ID to release: ").strip().upper()
    if spot_id not in ready:
        print("Error: That spot is not in the list.")
        return
    answer = input(f"Release spot {spot_id}? (yes/no): ").strip().lower()
    if answer != "yes":
        print("Cancelled. Nothing was changed.")
        return

    spot = spots[spot_id]
    log_event(spot["student_id"], spot_id, spot["zone"], "released")
    free_spot(spot)
    print(f"Spot {spot_id} has been released.")


def rank(counts):
    """Turn {'10:00': 5, '14:00': 9} into a list sorted high to low."""
    pairs = []
    for name in counts:
        pairs.append((counts[name], name))
    pairs.sort(reverse=True)
    return pairs


def usage_report():
    """Read the log, find busy hours and zones, and print a report."""
    if not staff_login():
        return
    try:
        with open(LOG_FILE, newline="") as file:
            rows = list(csv.DictReader(file))
    except FileNotFoundError:
        print("No usage data is available yet.")
        return
    if len(rows) == 0:
        print("No usage data is available yet.")
        return

    hour_count = {}
    zone_count = {}
    open_stays = {}      # (student, spot) -> time the stay started
    stay_minutes = []    # length of every finished stay (check-in to check-out/release)
    flagged = 0
    released = 0

    try:
        for row in rows:
            action = row["action"]
            key = (row["student_id"], row["spot_id"])
            moment = datetime.strptime(row["timestamp"], TIME_FORMAT)

            if action == "checkin":
                hour = row["timestamp"][11:13] + ":00"
                hour_count[hour] = hour_count.get(hour, 0) + 1
                zone_count[row["zone"]] = zone_count.get(row["zone"], 0) + 1
                open_stays[key] = moment
            elif action in ("checkout", "released"):
                if key in open_stays:
                    stay_minutes.append((moment - open_stays[key]).total_seconds() / 60)
                    del open_stays[key]
                if action == "released":
                    released += 1
            elif action == "flagged":
                flagged += 1
    except (KeyError, ValueError, TypeError):
        print("Error: usage_log.csv contains bad data.")
        return

    lines = ["LRC USAGE REPORT", "================",
             f"Events in log:   {len(rows)}",
             f"Total check-ins: {sum(hour_count.values())}"]
    if len(hour_count) > 0:
        best_hours = rank(hour_count)
        best_zones = rank(zone_count)
        lines.append(f"Busiest hour:    {best_hours[0][1]}  ({best_hours[0][0]} check-ins)")
        lines.append(f"Busiest zone:    {best_zones[0][1]}  ({best_zones[0][0]} check-ins)")
        top3 = [name for count, name in best_hours[:3]]
        lines.append("Top 3 hours:     " + ", ".join(top3))
    if len(stay_minutes) > 0:
        average = sum(stay_minutes) / len(stay_minutes)
        # Average stay counts the whole visit, so break time is included.
        lines.append(f"Average stay:    {int(average // 60)} h {int(average % 60)} min "
                     "(includes breaks)")
    else:
        lines.append("Average stay:    not enough data")
    lines.append(f"Spots flagged:   {flagged}")
    lines.append(f"Spots released:  {released}")

    print()
    for line in lines:
        print(line)
    try:
        with open(REPORT_FILE, "w") as file:
            file.write("\n".join(lines) + "\n")
        print(f"\n(Report saved to {REPORT_FILE})")
    except OSError:
        print("Error: could not save the report file.")


def advance_clock():
    """DEMO ONLY: move the program's clock forward so you do not have to wait."""
    if not staff_login():
        return
    minutes = ask_whole_number("Advance the clock by how many minutes? ", 0)
    if minutes is None:
        return
    settings["clock_offset"] += minutes
    print(f"Clock moved forward {minutes} minutes. Program time is now "
          + time_to_text(now()) + ".")
    print("(Events logged from now on use this shifted demo time.)")


def change_settings():
    """Staff option: change the break limit and the grace period."""
    if not staff_login():
        return
    print(f"Current break limit:  {settings['break_limit']} minutes")
    print(f"Current grace period: {settings['grace_period']} minutes")
    new_break = ask_whole_number("New break limit in minutes (at least 1): ", 1)
    if new_break is None:
        return
    new_grace = ask_whole_number("New grace period in minutes (0 or more): ", 0)
    if new_grace is None:
        return
    settings["break_limit"] = new_break      # change only after BOTH are valid
    settings["grace_period"] = new_grace
    print(f"Settings updated: break limit {new_break} min, grace period {new_grace} min.")


# ------------------------------------------------------------
#  MAIN PROGRAM
# ------------------------------------------------------------
def show_menu():
    """Print the main menu with all the options."""
    print("\n==============================")
    print("        LRC SEATSYNC")
    print("==============================")
    print("1. View spots")
    print("2. Check in")
    print("3. Step away")
    print("4. Return from break")
    print("5. Check out")
    print("6. Scan for abandoned spots   (staff, also runs automatically)")
    print("7. Release flagged spot       (staff)")
    print("8. Usage report               (staff)")
    print("9. Exit")
    print("10. Advance clock             (demo, staff)")
    print("11. Change break/grace limits (staff)")


def main():
    """Load the spots, then show the menu and run the chosen option until Exit."""
    spots = load_spots()
    if spots is None:
        return                      # file problem: stop safely

    while True:
        flag_overdue_spots(spots)   # automatic check, before every menu
        show_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            view_spots(spots)
        elif choice == "2":
            check_in(spots)
        elif choice == "3":
            step_away(spots)
        elif choice == "4":
            return_from_break(spots)
        elif choice == "5":
            check_out(spots)
        elif choice == "6":
            scan_for_abandoned(spots)
        elif choice == "7":
            release_spot(spots)
        elif choice == "8":
            usage_report()
        elif choice == "10":
            advance_clock()
        elif choice == "11":
            change_settings()
        elif choice == "9":
            save_spots(spots)
            print("Data saved. Goodbye!")
            break
        else:
            print("Error: Please enter a number from the menu.")

        save_spots(spots)           # save after every action


# Run the program only when this file is started directly,
# not when it is imported (for example by a test script).
if __name__ == "__main__":
    main()