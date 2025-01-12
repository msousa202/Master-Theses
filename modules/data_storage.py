import csv
import os
from datetime import datetime

def save_data_to_csv(scenario_key, user_answers, ai_response, csv_file="decision_logs.csv"):
    """
    Save all user answers and the AI response in a single row.
    """
    # Check if the file exists; if not, write the header row
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header if file doesn't exist
        if not file_exists:
            writer.writerow(["timestamp", "scenario", "user_answers", "ai_response"])

        # Format data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        combined_answers = "; ".join(f"{q_key}: {ans}" for q_key, ans in user_answers.items())

        # Write a single row with all data
        writer.writerow([timestamp, scenario_key, combined_answers, ai_response])



