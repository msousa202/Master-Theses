import csv
import os
from datetime import datetime

def save_data_to_csv(scenario_key, user_answers, ai_response, csv_file="decision_logs.csv"):
    """
    Save each user answer in a separate column, along with the AI response.
    """
    file_exists = os.path.isfile(csv_file)

    # Prepare headers dynamically
    question_keys = list(user_answers.keys())
    headers = ["timestamp", "scenario"] + question_keys + ["ai_response"]

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header if the file does not exist
        if not file_exists:
            writer.writerow(headers)

        # Prepare the row
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, scenario_key] + [user_answers.get(q, "") for q in question_keys] + [ai_response]

        # Write the row to the file
        writer.writerow(row)




