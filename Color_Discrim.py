"""
Color Discrimination Training

Behavioral task:
- The screen is divided into either 2 halves or 4 quarters.
- Exactly one section is yellow; all remaining sections are blue.
- The pig must select the yellow section.
- A yellow touch is recorded as correct.
- A blue touch is recorded as incorrect.
- Correct responses are reinforced according to the selected FR schedule.
- Incorrect responses play the incorrect sound and are not reinforced.
- The user selects the total number of questions/trials.
- The program ends after that number of questions have been answered.
- Final accuracy is calculated as:
      correct yellow touches / total questions * 100
- Trial-level data are saved to a CSV file.

Hardware:
- Output 1 = pellet dispenser
- Output 2 = success sound/sonalert
"""

from tkinter import *
import tkinter as tk
import csv
import sys
import time
import random
from pathlib import Path
from time import perf_counter
from threading import Timer

from iointerface_api import *
from platform_config import play_sound, ensure_sound_files


# ---------------------------------------------------------------------------
# HARDWARE INITIALIZATION
# ---------------------------------------------------------------------------

ensure_sound_files()

scan_time = 1
print(f"Scanning for {scan_time} seconds, please wait...")

USE_MEDPC = sys.platform == "win32"

devices = IOInterface.discover_interfaces(
    timeout=scan_time,
    use_medpc=USE_MEDPC
)

for found_device in devices:
    print(f"Found I/O Interface: {found_device.address}")

if len(devices) == 0:
    print("Failed to find device!")
    raise SystemExit

device = devices[0]


# ---------------------------------------------------------------------------
# DEFAULT SETTINGS
# ---------------------------------------------------------------------------

# "halves" = 2 sections
# "quarters" = 4 sections
screen_mode = "halves"

# Time between one question ending and the next question beginning.
trial_wait = 3.0

# Fixed-ratio reinforcement requirement.
# FR=1 = reinforce every correct yellow response.
fr_req = 1

# Total number of questions/trials in the session.
total_questions = 20

# Number of pellets delivered per reinforcement.
ReinfAmt = 1


# ---------------------------------------------------------------------------
# RUNTIME VARIABLES
# ---------------------------------------------------------------------------

gui = None
settings_window = None
report_window = None

current_yellow_index = None

question_number = 0
correct_responses = 0
incorrect_responses = 0
fr_responses = 0
pellets_dispensed = 0

trial_start_time = 0.0
trial_active = False
round_finished = False

trial_data = []

choice_frames = []
choice_labels = []


# ---------------------------------------------------------------------------
# REINFORCEMENT
# ---------------------------------------------------------------------------

def reinforcement():
    """Dispense pellets and play the success sound."""

    global pellets_dispensed
    global ReinfAmt
    reinforcers = 0

    def reinfOff():
        # Success sound.
        play_sound("2900.short.wav")
        device.write_output(1, IOState.INACTIVE)
        device.write_output(2, IOState.INACTIVE)

    while True:
        # Output 1 = pellet dispenser
        # Output 2 = sonalert/success signal
        device.write_output(1, IOState.ACTIVE)
        device.write_output(2, IOState.ACTIVE)
        pellet_timer = Timer(0.15, reinfOff)
        pellet_timer.start()
        pellet_timer.join()

        pellets_dispensed += 1
        reinforcers += 1
        if reinforcers >= ReinfAmt:
            break
# ---------------------------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------------------------

def clear_choices():
    """Remove all current choice widgets."""

    global choice_frames, choice_labels

    for widget in choice_frames + choice_labels:
        try:
            widget.destroy()
        except tk.TclError:
            pass

    choice_frames = []
    choice_labels = []


def make_choice_layout():
    """
    Create the current question.

    In halves mode:
        [ YELLOW ] [ BLUE ]
        or
        [ BLUE ] [ YELLOW ]

    In quarters mode:
        one of four positions is yellow and the other three are blue.
    """

    global current_yellow_index, choice_frames, choice_labels

    clear_choices()

    if screen_mode == "halves":
        rows = 1
        cols = 2
        section_count = 2
    else:
        rows = 2
        cols = 2
        section_count = 4

    current_yellow_index = random.randrange(section_count)

    for index in range(section_count):
        row = index // cols
        col = index % cols

        bg_color = (
            "yellow"
            if index == current_yellow_index
            else "blue"
        )

        frame = tk.Frame(
            gui,
            bg=bg_color,
            bd=2,
            relief="solid"
        )

        frame.grid(
            row=row,
            column=col,
            sticky="nsew",
            padx=2,
            pady=2
        )

        gui.grid_rowconfigure(row, weight=1)
        gui.grid_columnconfigure(col, weight=1)

        frame.bind(
            "<Button-1>",
            lambda event, selected=index: choice_pressed(selected)
        )

        # A label fills the entire section so touching anywhere in the
        # section registers as a response.
        label = tk.Label(
            frame,
            bg=bg_color
        )

        label.place(
            relx=0,
            rely=0,
            relwidth=1,
            relheight=1
        )

        label.bind(
            "<Button-1>",
            lambda event, selected=index: choice_pressed(selected)
        )

        choice_frames.append(frame)
        choice_labels.append(label)


def disable_choices():
    """Remove the current choices while waiting for the next question."""

    clear_choices()


# ---------------------------------------------------------------------------
# RESPONSE HANDLING
# ---------------------------------------------------------------------------

def choice_pressed(selected_index):
    """
    Process a touchscreen response.

    Yellow = correct.
    Blue = incorrect.

    Every touch answers one question. Therefore both correct and incorrect
    responses count toward total_questions.
    """

    global question_number
    global correct_responses, incorrect_responses
    global fr_responses, trial_active

    if not trial_active or round_finished:
        return

    trial_active = False

    response_time = perf_counter() - trial_start_time

    is_correct = selected_index == current_yellow_index

    # Every touch represents one completed question.
    question_number += 1

    if is_correct:
        correct_responses += 1
        fr_responses += 1
        response_label = "correct"

        # Reinforce according to FR.
        if fr_responses >= fr_req:
            fr_responses = 0
            reinforcement()

    else:
        incorrect_responses += 1
        response_label = "incorrect"

    trial_data.append({
        "question": question_number,
        "screen_mode": screen_mode,
        "yellow_section": current_yellow_index + 1,
        "selected_section": selected_index + 1,
        "response": response_label,
        "response_time_s": round(response_time, 4),
        "correct_total": correct_responses,
        "incorrect_total": incorrect_responses,
        "accuracy_percent": round(
            (correct_responses / question_number) * 100,
            2
        ),
    })

    # The selected number of questions, rather than the number of correct
    # responses, determines when the session ends.
    if question_number >= total_questions:
        finish_round()
        return

    disable_choices()

    if gui is not None and gui.winfo_exists():
        gui.after(
            max(0, int(trial_wait * 1000)),
            start_question
        )


# ---------------------------------------------------------------------------
# QUESTION CONTROL
# ---------------------------------------------------------------------------

def start_question():
    """Present the next question."""

    global trial_start_time, trial_active

    if round_finished:
        return

    trial_start_time = perf_counter()
    trial_active = True

    # Play sound when a new question appears
    play_sound("7500.long.wav")

    make_choice_layout()


# ---------------------------------------------------------------------------
# DATA / REPORTING
# ---------------------------------------------------------------------------

def save_trial_data():
    """Save question-by-question data to a CSV file."""

    if not trial_data:
        return None

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"Color_Discrim_{timestamp}.csv"
    filepath = Path.cwd() / filename

    fieldnames = [
        "question",
        "screen_mode",
        "yellow_section",
        "selected_section",
        "response",
        "response_time_s",
        "correct_total",
        "incorrect_total",
        "accuracy_percent",
    ]

    with open(filepath, "w", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(trial_data)

    return filepath


def finish_round():
    """End the session and display final results."""

    global round_finished, trial_active

    round_finished = True
    trial_active = False

    disable_choices()

    try:
        device.write_output(1, IOState.INACTIVE)
        device.write_output(2, IOState.INACTIVE)
    except Exception:
        pass

    # Play end-of-session sound
    play_sound("end_tone.wav")

    csv_path = save_trial_data()

    show_report(csv_path)


def show_report(csv_path=None):
    """Display the final accuracy and response summary."""

    global report_window

    report_window = tk.Toplevel(gui)
    report_window.title("Color Discrimination - Results")

    width = report_window.winfo_screenwidth()
    height = report_window.winfo_screenheight()

    report_window.geometry(
        f"{int(width * 0.85)}x{int(height * 0.75)}"
        f"+{int(width * 0.075)}+{int(height * 0.125)}"
    )

    if question_number > 0:
        accuracy = (correct_responses / question_number) * 100
    else:
        accuracy = 0.0

    title = tk.Label(
        report_window,
        text="Round Complete",
        font=("Arial", 30, "bold")
    )
    title.pack(pady=25)

    configuration = (
        "Halves (2 choices)"
        if screen_mode == "halves"
        else "Quarters (4 choices)"
    )

    summary = (
        f"Screen configuration: {configuration}\n\n"
        f"Questions asked: {question_number}\n"
        f"Correct (yellow): {correct_responses}\n"
        f"Incorrect (blue): {incorrect_responses}\n"
        f"Accuracy: {accuracy:.1f}%\n"
        f"FR requirement: {fr_req}\n"
        f"Pellets dispensed: {pellets_dispensed}\n"
        f"Wait between questions: {trial_wait:.1f} s"
    )

    label = tk.Label(
        report_window,
        text=summary,
        font=("Arial", 24),
        justify="left"
    )
    label.pack(pady=20)

    if csv_path is not None:
        csv_label = tk.Label(
            report_window,
            text=f"Trial data saved to:\n{csv_path}",
            font=("Arial", 16),
            justify="center"
        )
        csv_label.pack(pady=10)

    exit_button = tk.Button(
        report_window,
        text="Exit",
        command=close_program,
        font=("Arial", 22, "bold"),
        height=2,
        width=12
    )
    exit_button.pack(pady=30)


# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------

def start_program():
    """Read settings and launch the color discrimination task."""

    global screen_mode, trial_wait, fr_req
    global total_questions, ReinfAmt

    try:
        screen_mode = mode_var.get()
        trial_wait = float(wait_entry.get())
        fr_req = int(fr_entry.get())
        total_questions = int(questions_entry.get())
        ReinfAmt = int(reinf_amount_entry.get())

        if screen_mode not in ("halves", "quarters"):
            raise ValueError("Invalid screen configuration.")

        if trial_wait < 0:
            raise ValueError("Wait between questions must be >= 0.")

        if fr_req < 1:
            raise ValueError("FR must be >= 1.")

        if total_questions < 1:
            raise ValueError("Number of questions must be >= 1.")

        if ReinfAmt < 1:
            raise ValueError("Pellets per reinforcement must be >= 1.")

    except ValueError as error:
        error_label.config(
            text=f"Please enter valid settings.\n{error}"
        )
        return

    settings_window.destroy()

    launch_task()


def launch_task():
    """Create the full-screen task window."""

    global gui

    gui = tk.Tk()
    gui.title("Color Discrimination")

    width = gui.winfo_screenwidth()
    height = gui.winfo_screenheight()

    gui.geometry(f"{width}x{height}+0+0")
    gui.attributes("-fullscreen", True)

    # Escape allows the experimenter to terminate the session.
    gui.bind(
        "<Escape>",
        lambda event: close_program()
    )

    gui.after(100, start_question)

    gui.mainloop()


def close_program():
    """Safely close the task and deactivate hardware outputs."""

    global round_finished, trial_active

    round_finished = True
    trial_active = False

    try:
        device.write_output(1, IOState.INACTIVE)
        device.write_output(2, IOState.INACTIVE)
    except Exception:
        pass

    try:
        if report_window is not None and report_window.winfo_exists():
            report_window.destroy()
    except Exception:
        pass

    try:
        if gui is not None and gui.winfo_exists():
            gui.destroy()
    except Exception:
        pass

    try:
        if settings_window is not None and settings_window.winfo_exists():
            settings_window.destroy()
    except Exception:
        pass


def build_settings():
    """Create the initial splash/settings screen."""

    global settings_window
    global mode_var
    global wait_entry, fr_entry
    global questions_entry, reinf_amount_entry
    global error_label

    settings_window = tk.Tk()
    settings_window.title("Color Discrimination - Settings")

    width = settings_window.winfo_screenwidth()
    height = settings_window.winfo_screenheight()

    settings_window.geometry(
        f"{int(width * 0.75)}x{int(height * 0.75)}"
        f"+{int(width * 0.125)}+{int(height * 0.125)}"
    )

    title = tk.Label(
        settings_window,
        text="Color Discrimination",
        font=("Arial", 30, "bold")
    )
    title.grid(
        row=0,
        column=0,
        columnspan=3,
        padx=20,
        pady=30
    )

    description = tk.Label(
        settings_window,
        text=(
            "The pig must select the yellow section of the screen.\n"
            "Yellow = correct; blue = incorrect."
        ),
        font=("Arial", 18),
        justify="center"
    )
    description.grid(
        row=1,
        column=0,
        columnspan=3,
        padx=20,
        pady=10
    )

    # Screen configuration
    tk.Label(
        settings_window,
        text="Screen configuration:",
        font=("Arial", 20, "bold")
    ).grid(
        row=2,
        column=0,
        sticky="e",
        padx=15,
        pady=15
    )

    mode_var = StringVar(
        settings_window,
        value="halves"
    )

    tk.Radiobutton(
        settings_window,
        text="Halves (2 choices)",
        variable=mode_var,
        value="halves",
        font=("Arial", 18)
    ).grid(
        row=2,
        column=1,
        sticky="w",
        padx=15,
        pady=15
    )

    tk.Radiobutton(
        settings_window,
        text="Quarters (4 choices)",
        variable=mode_var,
        value="quarters",
        font=("Arial", 18)
    ).grid(
        row=2,
        column=2,
        sticky="w",
        padx=15,
        pady=15
    )

    # Wait between questions
    tk.Label(
        settings_window,
        text="Wait between questions (s):",
        font=("Arial", 20)
    ).grid(
        row=3,
        column=0,
        sticky="e",
        padx=15,
        pady=15
    )

    wait_entry = tk.Entry(
        settings_window,
        width=8,
        font=("Arial", 20)
    )
    wait_entry.insert(0, "3")
    wait_entry.grid(
        row=3,
        column=1,
        sticky="w",
        padx=15,
        pady=15
    )

    # FR
    tk.Label(
        settings_window,
        text="FR requirement:",
        font=("Arial", 20)
    ).grid(
        row=4,
        column=0,
        sticky="e",
        padx=15,
        pady=15
    )

    fr_entry = tk.Entry(
        settings_window,
        width=8,
        font=("Arial", 20)
    )
    fr_entry.insert(0, "1")
    fr_entry.grid(
        row=4,
        column=1,
        sticky="w",
        padx=15,
        pady=15
    )

    tk.Label(
        settings_window,
        text="(FR-1 = reinforce every correct choice)",
        font=("Arial", 14)
    ).grid(
        row=4,
        column=2,
        sticky="w",
        padx=15,
        pady=15
    )

    # Number of questions
    tk.Label(
        settings_window,
        text="Number of questions:",
        font=("Arial", 20)
    ).grid(
        row=5,
        column=0,
        sticky="e",
        padx=15,
        pady=15
    )

    questions_entry = tk.Entry(
        settings_window,
        width=8,
        font=("Arial", 20)
    )
    questions_entry.insert(0, "20")
    questions_entry.grid(
        row=5,
        column=1,
        sticky="w",
        padx=15,
        pady=15
    )

    tk.Label(
        settings_window,
        text="(session ends after this many responses)",
        font=("Arial", 14)
    ).grid(
        row=5,
        column=2,
        sticky="w",
        padx=15,
        pady=15
    )

    # Pellets per reinforcement
    tk.Label(
        settings_window,
        text="Pellets per reinforcement:",
        font=("Arial", 20)
    ).grid(
        row=6,
        column=0,
        sticky="e",
        padx=15,
        pady=15
    )

    reinf_amount_entry = tk.Entry(
        settings_window,
        width=8,
        font=("Arial", 20)
    )
    reinf_amount_entry.insert(0, "1")
    reinf_amount_entry.grid(
        row=6,
        column=1,
        sticky="w",
        padx=15,
        pady=15
    )

    error_label = tk.Label(
        settings_window,
        text="",
        font=("Arial", 16),
        fg="red"
    )
    error_label.grid(
        row=7,
        column=0,
        columnspan=3,
        padx=20,
        pady=10
    )

    start_button = tk.Button(
        settings_window,
        text="START",
        command=start_program,
        font=("Arial", 24, "bold"),
        height=2,
        width=14
    )
    start_button.grid(
        row=8,
        column=0,
        columnspan=3,
        padx=20,
        pady=30
    )

    for row in range(9):
        settings_window.grid_rowconfigure(
            row,
            weight=1
        )

    for column in range(3):
        settings_window.grid_columnconfigure(
            column,
            weight=1
        )

    settings_window.protocol(
        "WM_DELETE_WINDOW",
        close_program
    )

    settings_window.mainloop()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with device:
        build_settings()
