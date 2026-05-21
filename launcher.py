"""Pig training session launcher.

A small Tk window that lets the trainer pick a task from a dropdown and
launches it as a subprocess. Hides the PowerShell command line so casual
users never have to type a path. The terminal window (opened by the .bat
shortcut) stays visible so the trainer can read the [REWARD] log.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk


HERE = os.path.dirname(os.path.abspath(__file__))


# Each entry: display_label -> (script_filename, notes)
TASKS = [
    (
        "Shaping (MED-PC pellet)",
        "Shaping_full.py",
        [
            "Uses the MED-PC pellet feeder.",
            "",
            "Before starting:",
            "  - MED-PC.exe must be running",
            "  - In MPCLoader, run the loader macro and click S;1",
            "  - Hopper should hold at least 150 pellets",
        ],
    ),
    (
        "Motor Task - Accuracy",
        "Motor_Task_Acc.py",
        [
            "Touchscreen accuracy task (no pellets).",
            "",
            "Before starting:",
            "  - Make sure the touchscreen is responsive",
            "  - Data is written to HamTraining\\Data\\",
            "",
            "Known issue: may stop mid-session on the current Python.",
            "If it crashes, call the lab tech.",
        ],
    ),
    (
        "Motor Task - Reaction Time",
        "Motor_Task_ReactionTime.py",
        [
            "Touchscreen reaction time task (no pellets).",
            "",
            "Before starting:",
            "  - Make sure the touchscreen is responsive",
            "  - Data is written to HamTraining\\Data\\",
            "",
            "Known issue: may stop mid-session on the current Python.",
            "If it crashes, call the lab tech.",
        ],
    ),
]


def on_task_changed(*_):
    label = task_var.get()
    for disp, _script, notes in TASKS:
        if disp == label:
            notes_text.config(state="normal")
            notes_text.delete("1.0", "end")
            notes_text.insert("1.0", "\n".join(notes))
            notes_text.config(state="disabled")
            return


def launch():
    label = task_var.get()
    script = next(s for d, s, _ in TASKS if d == label)
    script_path = os.path.join(HERE, script)
    if not os.path.exists(script_path):
        status_var.set(f"ERROR: {script} not found in {HERE}")
        return
    status_var.set(f"Launching {script}...")
    root.update()
    # Inherit stdout/stderr so the terminal that ran us keeps showing
    # the task's [REWARD] / status output.
    subprocess.Popen([sys.executable, script_path], cwd=HERE)
    root.destroy()


root = tk.Tk()
root.title("Pig Training")
root.geometry("560x420")
root.configure(bg="white")

tk.Label(root, text="Pig Training",
         font=("Arial", 22, "bold"), bg="white").pack(pady=(20, 4))
tk.Label(root, text="Pick a task and click Start.",
         font=("Arial", 12), bg="white", fg="gray30").pack(pady=(0, 16))

# Task picker
tk.Label(root, text="Task:",
         font=("Arial", 13), bg="white").pack(anchor="w", padx=30)
task_var = tk.StringVar(value=TASKS[0][0])
task_var.trace_add("write", on_task_changed)
dropdown = ttk.Combobox(root, textvariable=task_var,
                        values=[t[0] for t in TASKS],
                        state="readonly", font=("Arial", 13), width=40)
dropdown.pack(padx=30, pady=(2, 14), anchor="w")

# Notes panel
tk.Label(root, text="Notes:",
         font=("Arial", 13), bg="white").pack(anchor="w", padx=30)
notes_text = tk.Text(root, height=7, width=58, font=("Consolas", 11),
                     bg="#f7f7f7", fg="black", relief="solid",
                     borderwidth=1, wrap="word")
notes_text.pack(padx=30, pady=(2, 14))
on_task_changed()  # populate initial notes

# Start button
tk.Button(root, text="Start Training",
          font=("Arial", 16, "bold"),
          bg="#1b7a1b", fg="white",
          activebackground="#155a15", activeforeground="white",
          width=20, height=2,
          command=launch).pack(pady=(4, 8))

# Status line
status_var = tk.StringVar(value="")
tk.Label(root, textvariable=status_var,
         font=("Arial", 10), bg="white", fg="gray40").pack()

root.mainloop()
