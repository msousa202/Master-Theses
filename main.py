import tkinter as tk
from modules.assistant_app import VoiceAssistantApp

def main():
    root = tk.Tk()
    app = VoiceAssistantApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()