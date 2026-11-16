# First name: Ahmad | Last name: EL Samad | Group: B
#
# 1. In: The player's name and A/B/C choices, plus scenarios_B.csv.
#    The file uses semicolons and has 14 columns. Num is the scenario ID.
#    Situation is the story. For A, B and C, the four fields are Choice
#    (action text), Money (euros gained or lost), Buzz (reputation points
#    gained or lost), and Reaction (feedback). Money and Buzz are whole
#    numbers with a minus sign for a loss, such as -800 or -10.
#
# 2. Process for one day:
#    Show today's number, budget, reputation, situation, and three choices.
#    Ask for A, B or C until the player enters one of them.
#    Apply both changes, cap reputation at 100, and show the reaction.
#    Record the move using the change that actually reached the gauge.
#    Stop if either gauge is zero or below.
#    Otherwise check the streak bonus and continue to the next day.
#
# 3. Out: The player sees why they were fired or the score and final title,
#    plus the final gauges, best move, and worst move. Each results.csv
#    row has name,budget,reputation,title,date, in that order.
#
# 4. What could go wrong:
#    An invalid button gets another prompt. Lowercase A/B/C is accepted.
#    A gauge at zero or below ends the game immediately.
#    A missing file or an incorrect header stops the game with a message.
#    Incomplete rows or invalid impacts are skipped. The game needs at
#    least 10 usable scenarios so every day can have a different one.
#    If the player closes input, the unfinished game ends without logging.
#
# Feature A: I chose a streak bonus because it rewards consistent
# reputation gains. Every three days of actual gains in a row earns
# 500 EUR. A day with no gain resets the streak, including at the cap.

import csv
import random
from datetime import date
from pathlib import Path


# Keep both CSV files next to the game so the launch folder can vary.
FOLDER = Path(__file__).resolve().parent
SCENARIO_FILE = FOLDER / "scenarios_B.csv"
RESULTS_FILE = FOLDER / "results.csv"
OPTIONS = ("A", "B", "C")
OPTION_FIELDS = ("Choice", "Money", "Buzz", "Reaction")
SCENARIO_COLUMNS = ["Num", "Situation"] + [
    f"{letter}_{field}" for letter in OPTIONS for field in OPTION_FIELDS
]
DAYS = 10


# Read integer impacts, including whole values written as 15,0 in Excel.
def parse_impact(value):
    whole, separator, fraction = value.strip().replace(",", ".").partition(".")
    if separator and (not fraction or fraction.strip("0")):
        raise ValueError("Scenario impacts must be whole numbers.")
    return int(whole)


# Load playable scenarios and count the rows that cannot be played.
def load_scenarios(path):
    scenarios = []
    skipped_rows = 0
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";", strict=True)
        if reader.fieldnames != SCENARIO_COLUMNS:
            raise ValueError("The CSV header does not match Scenario B.")

        for row in reader:
            if None in row or any(not (row[column] or "").strip() for column in SCENARIO_COLUMNS):
                skipped_rows += 1
                continue

            choices = {}
            try:
                for letter in OPTIONS:
                    choices[letter] = (
                        row[f"{letter}_Choice"].strip(),
                        parse_impact(row[f"{letter}_Money"]),
                        parse_impact(row[f"{letter}_Buzz"]),
                        row[f"{letter}_Reaction"].strip(),
                    )
            except ValueError:
                skipped_rows += 1
                continue

            scenarios.append((row["Situation"].strip(), choices))
    return scenarios, skipped_rows


# Display the situation, each available action, and the current gauges.
def show_day(day, budget, reputation, situation, choices):
    print(f"\n--- Day {day} ---")
    print(f"[Budget: {budget} EUR | Reputation: {reputation}/100]")
    print(situation)
    for letter in OPTIONS:
        print(f"  {letter}: {choices[letter][0]}")


# Keep asking until the player gives a valid letter.
def ask_for_choice():
    choice = input("Your choice (A, B or C): ").strip().upper()
    while choice not in OPTIONS:
        choice = input("Please type A, B or C: ").strip().upper()
    return choice


# Add both impacts and return the two updated gauges as a tuple.
def apply_choice(budget, reputation, choice):
    _, budget_change, reputation_change, _ = choice
    return budget + budget_change, min(100, reputation + reputation_change)


# Translate a surviving score into the title from the brief.
def title_for_score(score):
    if score < 95:
        return "Eternal Intern"
    if score < 120:
        return "Growth Hacker"
    if score < 140:
        return "CMO Material"
    return "Viral Legend"


# Say which gauge caused the firing. Two gauges can fail on the same day.
def firing_reason(budget, reputation):
    if budget <= 0 and reputation <= 0:
        return "budget and reputation both hit zero or below"
    if budget <= 0:
        return "budget hit zero or below"
    if reputation <= 0:
        return "reputation hit zero or below"
    return None


# Pick moves by their reputation change. Ties favor the earliest day.
def show_best_and_worst(history):
    def reputation_change(move):
        return move[0]

    for label, move in (
        ("Best move", max(history, key=reputation_change)),
        ("Worst move", min(history, key=reputation_change)),
    ):
        change, day, action = move
        print(f'{label}: day {day}, "{action}" ({change:+d} reputation)')


# Append one completed game, writing the header on the first run.
def save_result(path, name, budget, reputation, title):
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(["name", "budget", "reputation", "title", "date"])
        writer.writerow([name, budget, reputation, title, date.today().isoformat()])


# Run the quarter and return the gauges and the player's final title.
def play_quarter(scenarios):
    budget = 10_000
    reputation = 50
    history = []
    streak = 0
    reason = None

    # Shuffle once so each day uses a different scenario.
    random.shuffle(scenarios)
    for day, (situation, choices) in enumerate(scenarios[:DAYS], start=1):
        show_day(day, budget, reputation, situation, choices)
        choice = choices[ask_for_choice()]

        # Apply the choice, display feedback, and record the actual gain or loss.
        old_reputation = reputation
        budget, reputation = apply_choice(budget, reputation, choice)
        action, budget_change, _, feedback = choice
        actual_change = reputation - old_reputation
        print(feedback)
        print(f"Budget {budget_change:+d} EUR | Reputation {actual_change:+d}")
        history.append((actual_change, day, action))

        # End play as soon as either gauge reaches zero or below.
        reason = firing_reason(budget, reputation)
        if reason:
            break

        # Reward every set of three consecutive reputation gains.
        streak = streak + 1 if actual_change > 0 else 0
        if streak == 3:
            budget += 500
            streak = 0
            print("Streak bonus: +500 EUR for three reputation gains in a row!")

    # Announce the outcome and show the strongest and weakest moves.
    print("\n" + "=" * 40)
    print(f"Final budget: {budget} EUR | Final reputation: {reputation}/100")
    if reason:
        title = "Fired"
        print(f"Fired: {reason}.")
    else:
        score = reputation + budget // 200
        title = title_for_score(score)
        print(f"Quarter survived! Final score: {score}")
        print(f"Your title: {title}")
    show_best_and_worst(history)
    return budget, reputation, title


# Collect the name, load the scenarios, and save the completed game.
def main():
    print("Survive the Quarter | Croissant Rocket")
    try:
        name = input("Player name: ").strip()
        while not name:
            name = input("Please enter your name: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGame ended before a result was recorded.")
        return

    try:
        scenarios, skipped_rows = load_scenarios(SCENARIO_FILE)
    except (OSError, csv.Error, ValueError):
        print("Cannot load scenarios_B.csv. Check the file name and Group B format.")
        return
    if skipped_rows:
        print(f"Skipped {skipped_rows} incomplete or invalid scenario row(s).")
    if len(scenarios) < DAYS:
        print("scenarios_B.csv needs at least 10 usable scenarios.")
        return

    try:
        budget, reputation, title = play_quarter(scenarios)
    except (EOFError, KeyboardInterrupt):
        print("\nGame ended before a result was recorded.")
        return

    try:
        save_result(RESULTS_FILE, name, budget, reputation, title)
    except OSError:
        print("Could not save this game to results.csv.")
    else:
        print(f"{name}, your result was saved in {RESULTS_FILE.name}.")


if __name__ == "__main__":
    main()
