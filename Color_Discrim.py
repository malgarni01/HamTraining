"""Two-choice color discrimination for the CoasterChase pig rig.

Implements the discrimination procedure described in:

    Ao W, Grace M, Floyd CL, Vonder Haar C. A Touchscreen Device for
    Behavioral Testing in Pigs. Biomedicines. 2022;10(10):2612.
    doi:10.3390/biomedicines10102612

Three phases, selected by the experimenter at session start:

  C1  Free-choice acquisition. Yellow (correct) vs blue. No correction.
  C2  As C1, plus correction trials: after an incorrect choice the identical
      trial is re-presented with the incorrect option shown but inactive.
  C3  Conditional discrimination. A green or blue sample appears on the
      centre button; only the choice matching the sample is reinforced.
      FR-3 on the centre and on the choice buttons.

Shaping (Shaping_full.py) is Phase A/B and is a separate program; this file
does not import from it. The feeder path is shared via iointerface_api.
"""

from tkinter import *
import tkinter as tk  # for GUI
from time import perf_counter, sleep  # latencies/timers, and flash dwell
import csv
import datetime
import os
import random
import statistics
import sys
from iointerface_api import *
from platform_config import play_sound, ensure_sound_files, get_data_dir

ensure_sound_files()

scan_time = 1
print(f"scanning for {scan_time} seconds, please wait...")

# On the Med Associates COM-106 (Windows) drive the feeder through MED-PC's
# file-drop backend; elsewhere fall back to Mock/serial. The MED-PC backend
# itself falls back to MockDevice if C:\MED-PC is not present, so a plain
# Windows dev box still runs without stalling on dispense acks.
USE_MEDPC = sys.platform == "win32"
devices = IOInterface.discover_interfaces(timeout=scan_time,
                                          use_medpc=USE_MEDPC)
for device in devices:
    print(f"Found I/O Interface: {device.address}")

if len(devices) == 0:
    print("Failed to find device!")
    exit()

# GLOBAL CONSTANTS
VI_list = [3, 4, 4, 5, 5, 5, 6, 6, 7]  # variable interval ITI, seconds (protocol 8.1: VI 3-7 s)
MAX_SAME_SIDE = 3  # pseudorandom cap: never more than this many same-side trials in a row

# Screen geometry, relative units. Choices sit left and right of centre.
FLASH_MS = 60                # dwell for a touch-acknowledgement flash, ms
NEUTRAL_FLASH_BG = "gray50"  # identical for every sub-criterion touch, and
                             # distinct from the choice colours

CENTRE_POS = (0.5, 0.5)
CENTRE_SIZE = (0.40, 0.45)  # relwidth, relheight. Matches the stage 3 box in
                            # Shaping_full.py (relwidth 0.4, relheight 0.45) so the
                            # start target is the same size the animal was shaped on.
CHOICE_POS = {"L": (0.22, 0.5), "R": (0.78, 0.5)}
CHOICE_SIZE = (0.28, 0.45)

# Colors by phase. C1/C2 reinforce yellow against a blue comparison; C3
# reinforces whichever of green/blue matches the sample on the centre button.
S_PLUS = "yellow"
S_MINUS = "blue"
C3_COLORS = ["green", "blue"]

# Default Settings (Can be modified from the startup popup)
Phase = 1              # 1 = C1, 2 = C2, 3 = C3
Subject = "Sbj000"
MaxTrials = 60         # first presentations; correction trials do not count
LimitedHold = 25       # seconds the animal has to respond, each of the two steps
FRCentre = 1           # presses required on the centre start box
FRChoice = 1           # presses required on a choice box to commit it
ReinfAmt = 1           # pellets per correct choice
Blackout = 0.15        # delay before the session starts, minutes
Correction = 0         # 1 = correction trials enabled (forced on in C2)
SessionCap = 60        # hard stop, minutes

# Session state
trial = 0                  # first-presentation counter
records = []               # per-trial dicts, also written to CSV as we go
session_start = 0.0
side_history = []          # realised L/R sequence, for the run-length cap and audit

# Per-presentation state
is_correction = False
sample_color = ""          # C3 only
correct_side = "L"
choice_colors = {"L": S_PLUS, "R": S_MINUS}
active_choices = set()     # which choice frames currently accept a press
fr_count = {"centre": 0, "L": 0, "R": 0}
centre_onset = 0.0
choice_onset = 0.0
start_latency = 0.0
awaiting = "none"          # "centre" | "choice" | "none"
timeout_id = None          # cancellable after() id for LimitedHold
iti_id = None              # cancellable after() id for the ITI
pellets_commanded = 0


# ---------------------------------------------------------------------------
# Side assignment

def next_side():
    """Pseudorandom L/R with a run-length cap (protocol 8.1).

    Free choice unless the last MAX_SAME_SIDE trials all used the same side,
    in which case the other side is forced. Keeping the realised sequence in
    side_history lets 8.4's side-bias check be audited after the fact.
    """
    if len(side_history) >= MAX_SAME_SIDE:
        tail = side_history[-MAX_SAME_SIDE:]
        if all(s == tail[0] for s in tail):
            return "R" if tail[0] == "L" else "L"
    return random.choice(["L", "R"])


# ---------------------------------------------------------------------------
# Data logging

def trial_csv_path():
    return os.path.join(get_data_dir(), f"{Subject}_discrim.csv")


def session_csv_path():
    return os.path.join(get_data_dir(), f"{Subject}_discrim_sessions.csv")


TRIAL_COLUMNS = ["Subject", "Date", "Phase", "Trial", "Presentation",
                 "SampleColor", "CorrectSide", "ChosenSide", "ChosenColor",
                 "Correct", "StartLatency", "ChoiceLatency", "Omission",
                 "PelletsCommanded"]

SESSION_COLUMNS = ["Subject", "Date", "Phase", "TrialsCompleted",
                   "FirstPresAccuracy", "LeftChoicePct", "CorrectionTrials",
                   "StartOmissions", "ChoiceOmissions", "MedianStartLatency",
                   "MedianChoiceLatency", "PelletsCommanded"]


def write_row(row):
    """Append one trial row, writing the header if the file is new.

    Motor_Task_Acc.py:95-101 opens in append mode and never writes a header,
    which is why Data/Sbj258.csv is bare numeric rows. Don't repeat that.
    """
    path = trial_csv_path()
    new_file = not os.path.isfile(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAL_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def record(presentation, chosen_side, correct, omission, choice_latency):
    """Build, store and persist one trial record."""
    row = {
        "Subject": Subject,
        "Date": datetime.datetime.now().isoformat(timespec="seconds"),
        "Phase": f"C{Phase}",
        "Trial": trial,
        "Presentation": presentation,
        "SampleColor": sample_color,
        "CorrectSide": correct_side,
        "ChosenSide": chosen_side,
        "ChosenColor": choice_colors[chosen_side] if chosen_side else "",
        "Correct": "" if omission != "none" else int(correct),
        "StartLatency": round(start_latency, 3) if start_latency else "",
        "ChoiceLatency": round(choice_latency, 3) if choice_latency else "",
        "Omission": omission,
        "PelletsCommanded": pellets_commanded,
    }
    records.append(row)
    write_row(row)


def summarise():
    """Session-level numbers. Protocol 8.3 requires accuracy from first
    presentations only; 8.4 requires the left-choice percentage every session.
    """
    first = [r for r in records if r["Presentation"] == "first"]
    scored = [r for r in first if r["Omission"] == "none"]
    corrections = [r for r in records if r["Presentation"] == "correction"]

    acc = (100.0 * sum(int(r["Correct"]) for r in scored) / len(scored)) if scored else 0.0
    left = (100.0 * sum(1 for r in scored if r["ChosenSide"] == "L") / len(scored)) if scored else 0.0

    start_lats = [r["StartLatency"] for r in records if r["StartLatency"] != ""]
    choice_lats = [r["ChoiceLatency"] for r in records if r["ChoiceLatency"] != ""]

    return {
        "Subject": Subject,
        "Date": datetime.datetime.now().isoformat(timespec="seconds"),
        "Phase": f"C{Phase}",
        "TrialsCompleted": len(first),
        "FirstPresAccuracy": round(acc, 1),
        "LeftChoicePct": round(left, 1),
        "CorrectionTrials": len(corrections),
        "StartOmissions": sum(1 for r in records if r["Omission"] == "start"),
        "ChoiceOmissions": sum(1 for r in records if r["Omission"] == "choice"),
        "MedianStartLatency": round(statistics.median(start_lats), 2) if start_lats else "",
        "MedianChoiceLatency": round(statistics.median(choice_lats), 2) if choice_lats else "",
        "PelletsCommanded": pellets_commanded,
    }


def write_session(summary):
    path = session_csv_path()
    new_file = not os.path.isfile(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SESSION_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(summary)


# ---------------------------------------------------------------------------
# Reinforcement

def reinforcement():
    """Command ReinfAmt pellets and the tone.

    Ported from Shaping_full.py:162-203 with the IR-verification block
    removed. On the MED-PC backend write_output(1, ACTIVE) arms the feeder
    and write_output(1, INACTIVE) commits one dispense request; on
    Mock/serial these are plain output toggles. See the module docstring on
    why no delivery check is made here.
    """
    global pellets_commanded

    for _ in range(int(ReinfAmt)):
        device.write_output(1, IOState.ACTIVE)   # Turn on pellet dispenser
        device.write_output(2, IOState.ACTIVE)   # Turn on beeper
        gui.update()
        gui.after(250)                            # pellet cycle, blocking is fine here
        device.write_output(1, IOState.INACTIVE)  # Stop asserting pellet dispenser
        device.write_output(2, IOState.INACTIVE)  # Turn off beeper
        pellets_commanded += 1

    print(f"[REWARD] trial {trial}: commanded={int(ReinfAmt)} "
          f"session_total={pellets_commanded} (no delivery sensor -- "
          f"reconcile manually per protocol 9.2)")


# ---------------------------------------------------------------------------
# Trial state machine
#
# Event-driven rather than the recursive gui.after(10, loop) polling used in
# Shaping_full.py: clicks arrive as Tk events and the only scheduled work is
# the limited-hold timeout and the ITI, both held as cancellable after() ids.
# The ITI in particular is scheduled rather than time.sleep()'d, so the
# display stays live and the quit button still works between trials.

def _hold(ms):
    """Keep a flash on screen for a fixed time.

    These are Tk event handlers, so blocking briefly is safe -- nothing else
    needs to run during a 60 ms flash. Without an explicit hold the label is
    placed and removed inside one pass of the event loop and never renders.
    """
    gui.update()
    sleep(ms / 1000.0)


def neutral_flash():
    """Acknowledge a touch that did not complete the fixed ratio.

    Full screen, one colour, identical wherever the animal touched, and
    SILENT. Matches Shaping_full.py so that a sub-criterion touch means the
    same thing to the animal in both tasks.
    """
    lbl = tk.Label(gui, bg=NEUTRAL_FLASH_BG, activebackground=NEUTRAL_FLASH_BG)
    lbl.place(relheight=1.1, relwidth=1.1, relx=1.05, rely=-0.05, anchor="ne")
    _hold(FLASH_MS)
    lbl.place_forget()
    gui.update()


def paint_color(widget, color):
    """Set a frame's background so that it actually repaints.

    Tk only schedules a redraw for a widget that is currently mapped
    (frame.c ConfigureFrame guards the Tcl_DoWhenIdle on Tk_IsMapped). A
    frame that has been place_forget()'n is unmapped, so recolouring it there
    stores the option -- cget() reports the new colour -- without ever
    repainting, and the frame comes back blank when it is re-placed.

    place() alone is not enough: the geometry manager maps the widget at idle
    time, so we flush idle tasks first and only then set the colour.

    This bit once: trial 1 happened to need exactly the colours the frames
    were constructed with, so it looked right; from trial 2 the sides swap,
    both frames needed a new colour, and both came up white.
    """
    widget.update_idletasks()
    widget.config(bg=color)


def clear_screen():
    centre_btn.place_forget()
    for side in ("L", "R"):
        choice_btn[side].place_forget()
    gui.update()


def cancel_timeout():
    global timeout_id
    if timeout_id is not None:
        try:
            gui.after_cancel(timeout_id)
        except Exception:
            pass
        timeout_id = None


def trial_setup(correction=False):
    """Start a trial. A correction trial repeats the previous parameters."""
    global trial, is_correction, sample_color, correct_side, choice_colors
    global fr_count, centre_onset, awaiting, start_latency

    if not correction:
        # Session limits are checked on first presentations only, so a
        # correction sequence is never cut off half way through.
        if trial >= MaxTrials:
            end_session("trial limit reached")
            return
        if (perf_counter() - session_start) / 60.0 >= SessionCap:
            end_session("session time cap reached")
            return

        trial += 1
        correct_side = next_side()
        side_history.append(correct_side)

        if Phase == 3:
            # Conditional discrimination: the sample determines which color
            # is correct on this trial; the other color goes opposite.
            sample_color = random.choice(C3_COLORS)
            other = [c for c in C3_COLORS if c != sample_color][0]
            choice_colors = {correct_side: sample_color,
                             ("R" if correct_side == "L" else "L"): other}
        else:
            sample_color = ""
            choice_colors = {correct_side: S_PLUS,
                             ("R" if correct_side == "L" else "L"): S_MINUS}

    is_correction = correction
    fr_count = {"centre": 0, "L": 0, "R": 0}
    start_latency = 0.0
    awaiting = "centre"

    play_sound('7500.long.wav')  # long tone signals trial start

    # C3 shows the sample colour on the centre button; C1/C2 use a plain
    # yellow start box (protocol 8.1).
    #
    # Place FIRST, flush so the frame is really mapped, and only then set the
    # colour -- see paint_color() for why the order matters.
    centre_btn.place(relx=CENTRE_POS[0], rely=CENTRE_POS[1],
                     relwidth=CENTRE_SIZE[0], relheight=CENTRE_SIZE[1],
                     anchor="center")
    paint_color(centre_btn, sample_color if Phase == 3 else S_PLUS)
    gui.update()

    centre_onset = perf_counter()
    arm_timeout("start")


def arm_timeout(kind):
    global timeout_id
    cancel_timeout()
    timeout_id = gui.after(int(LimitedHold * 1000), lambda: omission(kind))


def centre_pressed(_event=None):
    """Centre start box. Gating the choices on a centre press puts the pig at
    a known position and orientation at choice onset (protocol 8.1)."""
    global awaiting, choice_onset, start_latency, active_choices

    if awaiting != "centre":
        return

    # Count first, gate immediately. No tone here at any point: trial start is
    # already marked by 7500.long.wav, and sounding 2900 -- the reinforcement
    # tone -- for merely starting a trial devalues it as a signal. The choices
    # appearing is the feedback for a completed centre ratio.
    fr_count["centre"] += 1
    if fr_count["centre"] < FRCentre:
        neutral_flash()
        return

    cancel_timeout()
    start_latency = perf_counter() - centre_onset
    centre_btn.place_forget()

    # Place both choices. On a correction trial the incorrect option is
    # displayed but inactive (protocol 8.3) -- it still absorbs the touch,
    # it just does not respond.
    for side in ("L", "R"):
        choice_btn[side].place(relx=CHOICE_POS[side][0], rely=CHOICE_POS[side][1],
                               relwidth=CHOICE_SIZE[0], relheight=CHOICE_SIZE[1],
                               anchor="center")
    # Colour only once both frames are mapped -- see paint_color().
    for side in ("L", "R"):
        paint_color(choice_btn[side], choice_colors[side])
    active_choices = {correct_side} if is_correction else {"L", "R"}
    gui.update()

    awaiting = "choice"
    choice_onset = perf_counter()
    arm_timeout("choice")


def choice_pressed(side):
    """A choice box was touched."""
    global awaiting

    if awaiting != "choice" or side not in active_choices:
        return

    fr_count[side] += 1
    # The FR must be completed on a single button: touching the other choice
    # resets this one's partial count. [SET LOCALLY] -- Ao et al. do not
    # specify how partial runs across buttons should be handled.
    other = "R" if side == "L" else "L"
    fr_count[other] = 0

    if fr_count[side] < FRChoice:
        # Sub-criterion presses are SILENT, with a neutral flash identical on
        # both buttons. Two separate reasons:
        #   - the correct/incorrect tones here would tell the pig the answer
        #     before the choice is committed, a confound once FRChoice > 1,
        #     which is exactly the C3 case;
        #   - 2900.short.wav is the reinforcement tone. Sounding it on touches
        #     that earn nothing -- including touches on the WRONG button --
        #     devalues it as a conditioned reinforcer. An earlier version
        #     played it here and called it neutral; it is identical on both
        #     buttons, but it is not neutral with respect to reward.
        neutral_flash()
        return

    cancel_timeout()
    awaiting = "none"
    latency = perf_counter() - choice_onset
    clear_screen()
    outcome(side, latency)


def outcome(chosen_side, latency):
    """Score the choice, reinforce or not, then queue what comes next."""
    correct = (chosen_side == correct_side)
    presentation = "correction" if is_correction else "first"

    if correct:
        play_sound('2900.short.wav')
        # Reinforce before recording so PelletsCommanded on this row is the
        # session total including this trial's pellets.
        reinforcement()
        record(presentation, chosen_side, True, "none", latency)
        next_trial()
    else:
        play_sound('290.short.wav')
        record(presentation, chosen_side, False, "none", latency)
        # Correction trials are enabled outright in C2 and by setting in C3.
        # They repeat the identical trial until the pig chooses correctly
        # (protocol 8.3), so no repeat cap is imposed; an omission breaks the
        # sequence via omission() below.
        if Correction:
            next_trial(correction=True, shortened=True)
        else:
            next_trial(shortened=True)


def omission(kind):
    """Limited hold expired with no completed response."""
    global awaiting
    awaiting = "none"
    cancel_timeout()
    clear_screen()

    presentation = "correction" if is_correction else "first"
    # No choice was committed, so ChoiceLatency is undefined either way.
    # StartLatency survives on a "choice" omission -- the pig did press the
    # centre box -- and is logged blank on a "start" omission.
    record(presentation, "", False, kind, 0.0)
    print(f"[OMISSION] trial {trial}: {kind}")
    # An omission ends any correction sequence and moves to a fresh trial.
    next_trial(shortened=True)


def next_trial(correction=False, shortened=False):
    """Schedule the next presentation after a variable ITI.

    Shaping_full.py shortens the interval after an error (line 438); the same
    is done here so a run of errors does not stall the session.
    """
    global iti_id
    iti = random.choice(VI_list)
    if shortened:
        iti = iti / 3.0
    iti_id = gui.after(int(iti * 1000), lambda: trial_setup(correction))


def end_session(reason):
    print(f"[SESSION END] {reason}")
    play_sound('end_tone.wav')
    clear_screen()
    exit_program()


# ---------------------------------------------------------------------------
# Exit and reporting

def exit_program():
    report()


def report():
    # Cancel pending after() callbacks so they don't fire on a destroyed root
    # and print "invalid command name ..." at shutdown.
    for aid in gui.tk.eval('after info').split():
        try:
            gui.after_cancel(aid)
        except Exception:
            pass
    gui.destroy()
    report_end()


def start():
    """Called by the START button; begins the first trial after the blackout."""
    global session_start
    start_button.destroy()
    session_start = perf_counter()
    gui.after(int(Blackout * 60 * 1000), lambda: trial_setup(False))


# ---------------------------------------------------------------------------
# Settings popup, shown before the task window opens

def settings():

    def update_vals():
        global Phase, Subject, MaxTrials, LimitedHold, FRCentre, FRChoice, \
            ReinfAmt, Blackout, Correction, SessionCap

        Phase = int(phase_var.get())
        Subject = e_subj.get().strip() or "Sbj000"
        MaxTrials = int(float(e_trials.get()))
        LimitedHold = float(e_hold.get())
        FRCentre = int(float(e_frc.get()))
        FRChoice = int(float(e_frx.get()))
        ReinfAmt = int(float(e_reinf.get()))
        Blackout = float(e_black.get())
        SessionCap = float(e_cap.get())

        # C2 is defined by correction trials, so they are forced on there.
        # C1 never uses them. C3 follows the dropdown.
        if Phase == 2:
            Correction = 1
        elif Phase == 1:
            Correction = 0
        else:
            Correction = 1 if corr_var.get() == "Yes" else 0

    def setup():
        update_vals()
        popup.destroy()

    def phase_defaults():
        """C3 runs FR-3 on the centre and the choices (Ao et al.); C1/C2 FR-1."""
        fr = "3" if int(phase_var.get()) == 3 else "1"
        e_frc.delete(0, END); e_frc.insert(0, fr)
        e_frx.delete(0, END); e_frx.insert(0, fr)

    popup = tk.Tk()
    popup.title("Phase C - Discrimination")
    width = popup.winfo_screenwidth()
    height = popup.winfo_screenheight()
    popup.geometry(f'{int(width * 0.85)}x{int(height * 0.8)}+{int(width * 0.075)}+{int(height * 0.075)}')

    phase_var = IntVar(value=1)
    rd1 = Radiobutton(popup, text="C1\nFree choice\n(yellow vs blue)",
                      variable=phase_var, value=1, command=phase_defaults)
    rd2 = Radiobutton(popup, text="C2\nCorrection trials",
                      variable=phase_var, value=2, command=phase_defaults)
    rd3 = Radiobutton(popup, text="C3\nConditional discrimination\n(FR-3)",
                      variable=phase_var, value=3, command=phase_defaults)
    rd1.grid(row=1, column=1, padx=2, pady=15)
    rd2.grid(row=2, column=1, padx=2, pady=15)
    rd3.grid(row=3, column=1, padx=2, pady=15)

    labels = [
        ("Subject:", 1), ("Trials\n(first presentations):", 2),
        ("Limited\nHold (s):", 3), ("FR centre:", 4), ("FR choice:", 5),
    ]
    for text, row in labels:
        tk.Label(popup, text=text, font=24).grid(row=row, column=3, padx=2, pady=15)

    labels2 = [
        ("Pellets per\ncorrect:", 1), ("Blackout (min):", 2),
        ("Session cap\n(min):", 3), ("Correction trials\n(C3 only):", 4),
    ]
    for text, row in labels2:
        tk.Label(popup, text=text, font=24).grid(row=row, column=5, padx=2, pady=15)

    e_subj = tk.Entry(popup, width=8, font=24)
    e_trials = tk.Entry(popup, width=4, font=24)
    e_hold = tk.Entry(popup, width=4, font=24)
    e_frc = tk.Entry(popup, width=4, font=24)
    e_frx = tk.Entry(popup, width=4, font=24)
    e_reinf = tk.Entry(popup, width=4, font=24)
    e_black = tk.Entry(popup, width=4, font=24)
    e_cap = tk.Entry(popup, width=4, font=24)

    for widget, row in [(e_subj, 1), (e_trials, 2), (e_hold, 3), (e_frc, 4), (e_frx, 5)]:
        widget.grid(row=row, column=4, ipadx=5, ipady=8, padx=7, pady=10)
    for widget, row in [(e_reinf, 1), (e_black, 2), (e_cap, 3)]:
        widget.grid(row=row, column=6, ipadx=5, ipady=8, padx=7, pady=10)

    corr_var = StringVar(popup)
    corr_var.set("Yes")
    OptionMenu(popup, corr_var, "Yes", "No").grid(row=4, column=6, padx=2, pady=10)

    e_subj.insert(0, Subject)
    e_trials.insert(0, str(MaxTrials))
    e_hold.insert(0, str(LimitedHold))
    e_frc.insert(0, str(FRCentre))
    e_frx.insert(0, str(FRChoice))
    e_reinf.insert(0, str(ReinfAmt))
    e_black.insert(0, str(Blackout))
    e_cap.insert(0, str(SessionCap))

    tk.Button(popup, text="Start", command=setup, font=("bold", "14"),
              height=3, width=12).grid(row=6, column=1, columnspan=2, pady=20)

    popup.grid_rowconfigure(0, weight=1)
    popup.grid_rowconfigure(7, weight=1)
    popup.grid_columnconfigure(0, weight=1)
    popup.grid_columnconfigure(7, weight=1)

    popup.mainloop()


def report_end():
    """
    End-of-session summary. First-presentation accuracy and left-choice
    percentage are the two numbers protocol 8.3 and 8.4 require checking
    every session; pellets commanded feeds the 9.2 reconciliation.
    """
    summary = summarise()
    write_session(summary)

    print("\n--- SESSION SUMMARY ---")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"side sequence: {''.join(side_history)}")

    popup_end = tk.Tk()
    popup_end.title("Session Summary")
    width = popup_end.winfo_screenwidth()
    height = popup_end.winfo_screenheight()
    popup_end.geometry(f'{int(width)}x{int(height)}+0+0')

    tk.Label(popup_end, text=f"{Subject}  -  Phase C{Phase}",
             font=("Bold", 30)).grid(row=1, column=1, columnspan=4, pady=20)

    cells = [
        ("Trials\ncompleted", summary["TrialsCompleted"]),
        ("First-pres\naccuracy", f"{summary['FirstPresAccuracy']}%"),
        ("Left choice\n(first pres)", f"{summary['LeftChoicePct']}%"),
        ("Correction\ntrials", summary["CorrectionTrials"]),
        ("Start\nomissions", summary["StartOmissions"]),
        ("Choice\nomissions", summary["ChoiceOmissions"]),
        ("Median start\nlatency (s)", summary["MedianStartLatency"]),
        ("Pellets\ncommanded", summary["PelletsCommanded"]),
    ]
    for i, (label, value) in enumerate(cells):
        col = 1 + (i % 4)
        row = 2 + 2 * (i // 4)
        tk.Label(popup_end, text=label, font=("Bold", 20)).grid(row=row, column=col, padx=15, pady=5)
        tk.Label(popup_end, text=str(value), font=("Arial", 26)).grid(row=row + 1, column=col, padx=15, pady=5)

    # Side bias reading, per the table in protocol 8.4.
    left = summary["LeftChoicePct"]
    if summary["TrialsCompleted"] == 0:
        note = ""
    elif left > 75 or left < 25:
        note = "ESTABLISHED SIDE BIAS"
    elif left > 60 or left < 40:
        note = "Emerging side bias"
    else:
        note = "Side balance normal"
    tk.Label(popup_end, text=note, font=("Bold", 22), fg="red" if "BIAS" in note else "black") \
        .grid(row=6, column=1, columnspan=4, pady=20)

    tk.Button(popup_end, text='Exit', command=popup_end.destroy,
              font=("bold", "20"), height=2, width=10).grid(row=8, column=1, columnspan=4, pady=20)

    popup_end.grid_rowconfigure(0, weight=1)
    popup_end.grid_rowconfigure(9, weight=1)
    popup_end.grid_columnconfigure(0, weight=1)
    popup_end.grid_columnconfigure(5, weight=1)

    popup_end.mainloop()


# ---------------------------------------------------------------------------
# Main

print("Connecting to I/O Interface")
# While code is running in this block, it'll stay connected
# As soon as this block exits, it'll disconnect
with device:
    # Outputs:
    # 1: Pellet Dispenser
    # 2: Sonalert
    device.configure_io({}, {1: OutputConfig.ACTIVE_LOW, 2: OutputConfig.ACTIVE_LOW})
    # calls settings upon program start
    settings()

    # gui initialization for main pig interface
    gui = tk.Tk()
    gui.configure(bg="black", cursor="none")

    # places start button
    start_button = tk.Button(gui, text="START", font=("bold", "40"), command=lambda: start())
    start_button.place(relheight=1, relwidth=1, relx=1, rely=0, anchor="ne")

    # centre start box and the two choice boxes
    centre_btn = tk.Frame(gui, bg=S_PLUS)
    centre_btn.bind("<Button-1>", centre_pressed)

    choice_btn = {
        "L": tk.Frame(gui, bg=S_PLUS),
        "R": tk.Frame(gui, bg=S_MINUS),
    }
    choice_btn["L"].bind("<Button-1>", lambda e: choice_pressed("L"))
    choice_btn["R"].bind("<Button-1>", lambda e: choice_pressed("R"))

    # small quit button in the corner, same placement as the other programs
    quit_btn = tk.Button(gui, bg="gray10", highlightbackground="gray10",
                         command=lambda: exit_program())
    quit_btn.place(relheight=0.007, relwidth=0.007, relx=0.007, rely=0, anchor="ne")

    # if overrideredirect is True, disables the X button and closing by alt+f4
    gui.overrideredirect(True)
    gui.overrideredirect(False)

    # fullscreens the application, and runs the window
    gui.attributes('-fullscreen', True)
    gui.mainloop()
    print("Disconnecting...")
print("Disconnected!")
