import json
import os

def load_scenarios_from_json(filepath):
    """Load scenario config from JSON file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Scenarios file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_scenario_prompt(scenario_data, user_answers):
    """
    Build a system or user prompt that includes:
    - The scenario description
    - The user’s textual answers
    - The BPM/ALife context
    This ensures ChatGPT gets the full context before responding.
    """
    prompt = (
        f"Scenario Name: {scenario_data['name']}\n"
        f"Description: {scenario_data['description']}\n\n"
        "Parameters:\n"
    )
    for param, val in scenario_data["parameters"].items():
        prompt += f"  {param}: {val}\n"

    prompt += "\nUser (Human Manager) Responses:\n"
    for q_key, answer in user_answers.items():
        prompt += f"  {q_key}: {answer}\n"

    # Optionally mention BPM or ALife constraints here, for example:
    prompt += (
        "\nBPM/ALife Notes:\n"
        "You are acting as an AI-driven decision advisor. "
        "Provide insights considering BPM principles (process efficiency, resource constraints) "
        "and an ALife perspective (agent-based dynamics, adaptation under competition).\n"
    )
    prompt += (
        "Please provide your best decision recommendation, highlighting any ethical considerations, "
        "resource constraints, or adaptive strategies.\n"
    )
    return prompt
