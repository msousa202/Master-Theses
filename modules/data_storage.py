import csv
import os
from datetime import datetime

def save_data_to_csv(scenario_key, user_answers, ai_response, csv_file="decision_logs.csv"):

    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header if file doesn't exist
        if not file_exists:
            writer.writerow(["timestamp", "scenario", "question_key", "user_answer", "ai_response"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # CASE 1: user_answers is NOT empty
        if user_answers:
            for q_key, ans in user_answers.items():
                writer.writerow([timestamp, scenario_key, q_key, ans, ai_response])
        else:
            # CASE 2: user_answers is empty => just store the AI response in a single row
            writer.writerow([timestamp, scenario_key, "", "", ai_response])

