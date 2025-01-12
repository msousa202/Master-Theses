from dotenv import load_dotenv
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import speech_recognition as sr
from openai import OpenAI
import threading
import os

##############################################################################
# IMPORTANT:
# 1) Replace "YOUR_API_KEY" with your actual OpenAI API key in your .env file
#    or directly here if you prefer (not recommended for production).
# 2) Make sure you have installed the dependencies:
#    pip install speechrecognition pipwin pyaudio openai python-dotenv
##############################################################################

load_dotenv()
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"), 
)

# test

class VoiceAssistantApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Simple Voice Assistant")

        # ----- NEW: Use ttk.Style to set a system-like theme -----
        self.style = ttk.Style()

        try:
            self.style.theme_use("vista")
        except:
            # Fallback if "winnative" is not available
            self.style.theme_use("default")

        # Frame for buttons (use ttk.Frame for consistent theme)
        self.button_frame = ttk.Frame(self.master)
        self.button_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Record Button (use ttk.Button)
        self.record_button = ttk.Button(
            self.button_frame, text="Record", command=self.record_audio_thread
        )
        self.record_button.pack(side=tk.LEFT, padx=5)

        # Stop Button (use ttk.Button)
        self.stop_button = ttk.Button(
            self.button_frame, text="Stop", command=self.stop_recording
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Console log (scrolled text)
        # Note that scrolledtext doesn’t have a ttk variant, so we keep it from tkinter
        self.log_area = scrolledtext.ScrolledText(
            self.master, wrap=tk.WORD, width=80, height=20
        )
        self.log_area.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Speech recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # To handle threads safely
        self.is_recording = False

    def record_audio_thread(self):
        """
        Run the record audio in a thread so that the UI doesn't block.
        """
        thread = threading.Thread(target=self.record_audio)
        thread.start()

    def record_audio(self):
        """
        Capture microphone audio, transcribe to text, call ChatGPT,
        and display the result in the log_area.
        """
        self.log_area.insert(tk.END, "Listening...\n")
        self.log_area.see(tk.END)

        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = self.recognizer.listen(source)

            self.log_area.insert(tk.END, "Transcribing...\n")
            self.log_area.see(tk.END)

            try:
                # Transcribe using Google Web Speech API (default in speech_recognition)
                question_text = self.recognizer.recognize_google(audio_data)
                self.log_area.insert(tk.END, f"You asked: {question_text}\n")
                self.log_area.see(tk.END)

                # Send to OpenAI (ChatGPT)
                ai_answer = self.query_openai_api(question_text)

                # Display answer
                self.log_area.insert(tk.END, f"AI says: {ai_answer}\n\n")
                self.log_area.see(tk.END)

            except sr.UnknownValueError:
                self.log_area.insert(tk.END, "Could not understand audio.\n\n")
                self.log_area.see(tk.END)
            except sr.RequestError as e:
                self.log_area.insert(tk.END, f"Could not request results; {e}\n\n")
                self.log_area.see(tk.END)

        except Exception as e:
            self.log_area.insert(tk.END, f"Error accessing microphone: {e}\n")
            self.log_area.see(tk.END)

    def stop_recording(self):
        self.is_recording = False
        self.log_area.insert(tk.END, "Stopped listening.\n")

    def query_openai_api(self, question):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": f"User question: {question}\nAI, please provide a concise answer."
                    }
                ]
                # max_tokens=100,
                # temperature=0.7,
            )
            ai_text = response.choices[0].message.content.strip()
            return ai_text
        except client.error.RateLimitError as e:
            return "Error: You have exceeded your quota. Please check your client usage or billing settings."
        except client.error.OpenAIError as e:
            return f"Error: {e}"


    # ----- NEW: handle window close -----
    def on_closing(self):
        """
        Cleanly close the application when user presses the X button.
        """
        # Perform any additional cleanup here if needed
        self.master.destroy()


def main():
    root = tk.Tk()
    app = VoiceAssistantApp(root)

    # Attach the custom close handler
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.mainloop()

if __name__ == "__main__":
    main()
