# Refactored VoiceAssistantApp Class
from tkinter import scrolledtext
from tkinter import ttk
import tkinter as tk
import speech_recognition as sr
from dotenv import load_dotenv
from openai import OpenAI
import threading
import os

# Our helper modules
from modules.scenario_manager import load_scenarios_from_json, build_scenario_prompt
from modules.data_storage import save_data_to_csv

class VoiceAssistantApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Voice Assistant with Scenarios")

        # Initialize UI components and logic
        self.init_ui()

        # Load scenarios from JSON
        self.load_scenarios()

        # Initialize data structures
        self.user_responses = {}
        self.active_scenario_key = None

        # Initialize OpenAI client
        self.init_openai_client()

    def init_ui(self):
        # Create main UI layout
        self.top_frame = ttk.Frame(self.master)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.mid_frame = ttk.Frame(self.master)
        self.mid_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.bottom_frame = ttk.Frame(self.master)
        self.bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scenario ComboBox
        self.scenario_var = tk.StringVar()
        self.scenario_combo = ttk.Combobox(self.top_frame, textvariable=self.scenario_var, state="readonly")
        self.scenario_combo.pack(side=tk.LEFT, padx=5)
        self.scenario_combo.bind("<<ComboboxSelected>>", self.on_scenario_selected)

        # Buttons
        self.record_button = ttk.Button(self.mid_frame, text="Record", command=self.record_audio_thread)
        self.record_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(self.mid_frame, text="Stop", command=self.stop_recording)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Scenario Frame
        self.scenario_frame = ttk.Frame(self.bottom_frame)
        self.scenario_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Log Area
        self.log_area = scrolledtext.ScrolledText(self.bottom_frame, wrap=tk.WORD, width=60, height=20)
        self.log_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Speech recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def init_openai_client(self):
        # Load environment variables
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OpenAI API key is missing. Please set it in the environment variables.")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=openai_api_key)

    def load_scenarios(self):
        # Load scenarios from JSON
        scenarios_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../cases/scenario.json"))
        self.scenarios_data = load_scenarios_from_json(scenarios_file)
        self.scenario_combo["values"] = list(self.scenarios_data.keys())

    def on_scenario_selected(self, event=None):
        self.active_scenario_key = self.scenario_var.get()
        scenario_info = self.scenarios_data[self.active_scenario_key]

        # Reset the UI
        for widget in self.scenario_frame.winfo_children():
            widget.destroy()

        # Display predefined parameters
        ttk.Label(self.scenario_frame, text="Predefined Parameters:", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=2)
        for param, value in scenario_info["parameters"].items():
            ttk.Label(self.scenario_frame, text=f"{param}: {value}").pack(anchor="w", pady=2)

        # Flexible user inputs
        self.user_responses[self.active_scenario_key] = {}
        ttk.Label(self.scenario_frame, text="User Inputs:", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=5)
        for idx, question in enumerate(scenario_info["questions"], start=1):
            q_label = ttk.Label(self.scenario_frame, text=f"{idx}. {question}")
            q_label.pack(anchor="w", pady=2)

            q_entry = ttk.Entry(self.scenario_frame, width=50)
            q_entry.pack(anchor="w", pady=2)

            self.user_responses[self.active_scenario_key][f"q{idx}"] = q_entry

        # Submit Button
        submit_button = ttk.Button(
            self.scenario_frame,
            text="Submit Responses",
            command=self.collect_user_responses
        )
        submit_button.pack(pady=5)

    def collect_user_responses(self):
        if not self.active_scenario_key:
            return

        scenario_key = self.active_scenario_key
        entries = self.user_responses[scenario_key]
        final_answers = {key: widget.get() for key, widget in entries.items()}

        # Log user inputs
        self.log_area.insert(tk.END, f"[User Inputs for {scenario_key}]:\n")
        for q, ans in final_answers.items():
            self.log_area.insert(tk.END, f"  {q}: {ans}\n")
        self.log_area.insert(tk.END, "\n")
        self.log_area.see(tk.END)

        # Generate AI Response
        scenario_data = self.scenarios_data[scenario_key]
        combined_context = build_scenario_prompt(scenario_data, final_answers)
        ai_answer = self.query_openai_api(combined_context)

        # Ensure complete AI output is logged
        self.log_area.insert(tk.END, f"[AI Decision for {scenario_key}]:\n{ai_answer}\n\n")
        self.log_area.insert(tk.END, "--- END OF AI RESPONSE ---\n\n")
        self.log_area.see(tk.END)

        # Save to CSV
        self.save_responses_to_csv(scenario_key, final_answers, ai_answer)

    def save_responses_to_csv(self, scenario_key, user_answers, ai_response):
        """Save user responses and AI decision to the CSV, avoiding duplication."""
        # Save user answers as individual rows
        for q_key, ans in user_answers.items():
            save_data_to_csv(
                scenario_key=scenario_key,
                user_answers={q_key: ans},
                ai_response=""
            )
        # Save AI response as a separate entry
        save_data_to_csv(
            scenario_key=scenario_key,
            user_answers={},
            ai_response=ai_response
        )

    def query_openai_api(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,  # Increase max tokens to capture larger responses
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {e}"

    def record_audio_thread(self):
        threading.Thread(target=self.record_audio).start()

    def record_audio(self):
        self.log_area.insert(tk.END, "Listening...\n")
        self.log_area.see(tk.END)
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = self.recognizer.listen(source)

            self.log_area.insert(tk.END, "Transcribing...\n")
            self.log_area.see(tk.END)

            question_text = self.recognizer.recognize_google(audio_data)
            self.log_area.insert(tk.END, f"You asked: {question_text}\n")
            self.log_area.see(tk.END)

            ai_answer = self.query_openai_api(question_text)
            self.log_area.insert(tk.END, f"AI says: {ai_answer}\n\n")
            self.log_area.see(tk.END)

        except Exception as e:
            self.log_area.insert(tk.END, f"Error accessing microphone: {e}\n")
            self.log_area.see(tk.END)

    def stop_recording(self):
        self.log_area.insert(tk.END, "Stopped listening.\n")

    def on_closing(self):
        self.master.destroy()

