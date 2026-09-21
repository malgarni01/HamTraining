"""Two-stage yellow/blue discrimination for the CoasterChase pig rig.

Bridges Shaping_full.py (yellow box only) to a two-choice colour task, and
then measures performance on that task. Two stages, selected by the
experimenter at session start:

  Transitional  A "priming screen" -- a single yellow square in the centre --
                opens every trial. Pressing it clears the screen and brings
                up the yellow/blue choice pair; pressing yellow there is
                reinforced. Priming with the shaped stimulus immediately
                before the choice is what teaches the animal that yellow is
                still the correct option once a second colour is on screen.

  Testing       The same yellow/blue choice with the priming screen omitted:
                the choice pair appears at trial onset. Used for cognitive
                assessment, where a prime would cue the answer.

Both stages score identically -- yellow is S+, blue is S- -- so the two write
the same columns to the same CSV files and only the Phase field differs.

Either stage can run one of two choice layouts, also set at session start:

  Left / Right      The original pair: one yellow and one blue box at fixed
                    positions either side of centre.

  Random positions  One yellow box and 1-3 blue boxes, all the same size,
                    dropped at non-overlapping random positions anywhere on
                    the screen. Position carries no information about which
                    box is correct, and with more than one distractor chance
                    performance falls below 50%.

Geometry, tones, flashes and the feeder path are shared with
Shaping_full.py; this file does not import from it. The feeder is reached
through iointerface_api.
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

# Screen geometry, relative units.
FLASH_MS = 60                # dwell for a touch-acknowledgement flash, ms
NEUTRAL_FLASH_BG = "gray50"  # identical for every sub-criterion touch, and
                             # distinct from the choice colours

CENTRE_POS = (0.5, 0.5)
CENTRE_SIZE = (0.40, 0.45)  # relwidth, relheight. Matches the stage 3 box in
                            # Shaping_full.py (relwidth 0.4, relheight 0.45) so the
                            # start target is the same size the animal was shaped on.
CHOICE_POS = {"L": (0.22, 0.5), "R": (0.78, 0.5)}
CHOICE_SIZE = (0.28, 0.45)

# Choice layout codes. 1 is the fixed left/right pair; 2 scatters one yellow
# box and NumBlue blue boxes at random non-overlapping positions.
LAYOUT_LR = 1
LAYOUT_RANDOM = 2
LAYOUT_LABELS = {LAYOUT_LR: "LeftRight", LAYOUT_RANDOM: "Random"}
LAYOUT_MENU = {LAYOUT_LR: "Left / Right", LAYOUT_RANDOM: "Random positions"}

MAX_BLUE = 3                  # most S- boxes the settings screen offers
MAX_BOXES = MAX_BLUE + 1      # frames built up front: 1 yellow + MAX_BLUE blue

# Every box in a randomized trial is this size -- the S+ must not be findable
# by size alone, so the yellow box cannot keep CHOICE_SIZE while the blue ones
# shrink. Smaller than CHOICE_SIZE because four boxes plus gaps have to fit.
RANDOM_CHOICE_SIZE = (0.22, 0.30)
RANDOM_MIN_GAP = 0.02         # clear space between neighbouring boxes
RANDOM_EDGE_MARGIN = 0.02     # clear space between a box and the screen edge
RANDOM_TRIES = 200            # position samples per box before restarting
RANDOM_RESTARTS = 50          # whole-layout restarts before the grid fallback

# Yellow is correct in both stages; blue is the incorrect comparison. Yellow
# is also the colour of the priming square and of the box used throughout
# Shaping_full.py, so the stimulus the animal was shaped on is the stimulus
# it is reinforced for choosing here.
S_PLUS = "yellow"
S_MINUS = "blue"

# Stage codes. 1 keeps the priming screen, 2 drops it.
TRANSITIONAL = 1
TESTING = 2
STAGE_LABELS = {TRANSITIONAL: "Transitional", TESTING: "Testing"}

# Default Settings (Can be modified from the startup popup)
Stage = TRANSITIONAL   # 1 = Transitional (priming screen), 2 = Testing
Layout = LAYOUT_LR     # 1 = fixed left/right pair, 2 = random positions
NumBlue = 1            # blue (S-) boxes in the random layout; forced to 1
                       # in the left/right layout, which shows exactly one
Subject = "Sbj000"
MaxTrials = 60         # first presentations; correction trials do not count
LimitedHold = 25       # seconds the animal has to respond, each of the two steps
FRCentre = 1           # presses required on the priming square (Transitional only)
FRChoice = 1           # presses required on a choice box to commit it
ReinfAmt = 1           # pellets per correct choice
Blackout = 0.15        # delay before the session starts, minutes
Correction = 0         # 1 = correction trials enabled (either stage)
SessionCap = 60        # hard stop, minutes
ShowCursor = 0         # 0 = mouse pointer hidden over the task window
                       # (default: the pig's touches should not be
                       # accompanied by a pointer); 1 = visible, for
                       # mouse-driven testing without a touchscreen

# Session state
trial = 0                  # first-presentation counter
records = []               # per-trial dicts, also written to CSV as we go
session_start = 0.0
side_history = []          # realised L/R sequence, for the run-length cap and audit

# Per-presentation state.
#
# Boxes are identified by integer slot, 0..MAX_BOXES-1, in both layouts: the
# left/right pair is slots 0 and 1 pinned to CHOICE_POS. Keying on slots
# rather than "L"/"R" is what lets one set of choice/scoring code serve both
# layouts. Sides are derived from a box's position when a row is written, so
# CorrectSide and ChosenSide still mean what they always did.
is_correction = False
sample_color = ""          # priming square colour; blank in Testing
correct_slot = 0           # slot showing S+ this presentation
correct_side = "L"         # screen half that slot landed in
choice_slots = [0, 1]      # slots in play this presentation
choice_places = {0: CHOICE_POS["L"], 1: CHOICE_POS["R"]}   # slot -> (relx, rely)
choice_colors = {0: S_PLUS, 1: S_MINUS}
active_choices = set()     # which choice frames currently accept a press
fr_count = {"centre": 0}
centre_onset = 0.0
choice_onset = 0.0
start_latency = 0.0
awaiting = "none"          # "centre" | "choice" | "none"
timeout_id = None          # cancellable after() id for LimitedHold
iti_id = None              # cancellable after() id for the ITI
pellets_commanded = 0
shutting_down = False      # set once the session is over; makes the exit
                           # path idempotent and stops anything scheduling
                           # or scoring another trial behind the summary


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


def side_of(pos):
    """Screen half a box centre falls in, for the protocol 8.4 bias check.

    A box centred exactly on the midline counts as right. That is arbitrary,
    and it only arises in the random layout; any analysis that turns on it
    should use the logged ChosenX rather than this column.
    """
    return "L" if pos[0] < 0.5 else "R"


def _overlaps(a, b, w, h, gap):
    """True if two same-sized boxes centred at a and b are closer than gap."""
    return abs(a[0] - b[0]) < w + gap and abs(a[1] - b[1]) < h + gap


def _grid_slots(w, h, gap, margin):
    """Evenly spaced non-overlapping centres, used only as a fallback."""
    step_x, step_y = w + gap, h + gap
    lo_x, hi_x = margin + w / 2.0, 1.0 - margin - w / 2.0
    lo_y, hi_y = margin + h / 2.0, 1.0 - margin - h / 2.0
    cols = max(1, int((hi_x - lo_x) / step_x) + 1)
    rows = max(1, int((hi_y - lo_y) / step_y) + 1)
    xs = [lo_x + i * step_x for i in range(cols)]
    ys = [lo_y + j * step_y for j in range(rows)]
    return [(x, y) for y in ys for x in xs]


def random_positions(n):
    """n non-overlapping box centres, in relative screen coordinates.

    Rejection sampling rather than jittered grid cells: cells would leave the
    boxes in visibly regular rows and columns, which gives position a
    structure the animal could learn even though it does not predict the S+.

    Boxes are kept RANDOM_MIN_GAP apart rather than merely not overlapping,
    so two boxes never render as one wide block, and RANDOM_EDGE_MARGIN off
    the edges so none is clipped by the screen bounds.

    Falls back to a shuffled grid only if sampling cannot place n boxes,
    which with the default constants does not happen -- it is there so that
    raising RANDOM_CHOICE_SIZE degrades into regular positions instead of
    hanging or overlapping.
    """
    w, h = RANDOM_CHOICE_SIZE
    gap, margin = RANDOM_MIN_GAP, RANDOM_EDGE_MARGIN
    lo_x, hi_x = margin + w / 2.0, 1.0 - margin - w / 2.0
    lo_y, hi_y = margin + h / 2.0, 1.0 - margin - h / 2.0

    for _ in range(RANDOM_RESTARTS):
        placed = []
        for _ in range(n):
            for _ in range(RANDOM_TRIES):
                cand = (random.uniform(lo_x, hi_x), random.uniform(lo_y, hi_y))
                if all(not _overlaps(cand, q, w, h, gap) for q in placed):
                    placed.append(cand)
                    break
            else:
                break          # this box would not fit; restart the layout
        if len(placed) == n:
            return placed

    slots = _grid_slots(w, h, gap, margin)
    if len(slots) < n:
        print(f"[LAYOUT] WARNING only {len(slots)} non-overlapping positions "
              f"fit {n} boxes of {RANDOM_CHOICE_SIZE}; boxes WILL overlap. "
              f"Lower RANDOM_CHOICE_SIZE or show fewer blue boxes.")
        return [(random.uniform(lo_x, hi_x), random.uniform(lo_y, hi_y))
                for _ in range(n)]
    random.shuffle(slots)
    return slots[:n]


def build_layout():
    """Pick this trial's box positions, colours and which box is S+.

    Called for first presentations only. A correction trial reuses whatever
    this left behind, so it repeats the identical screen -- same count, same
    positions, same correct box -- in both layouts.
    """
    global correct_slot, correct_side, choice_slots, choice_places, choice_colors

    if Layout == LAYOUT_RANDOM:
        n = int(NumBlue) + 1
        choice_slots = list(range(n))
        wanted = next_side()
        # The run-length cap (protocol 8.1) still applies. It is applied by
        # choosing WHICH placed box turns yellow, not by constraining where
        # boxes may go -- constraining placement directly would leave a
        # learnable hole in the position distribution.
        #
        # That only works if some box actually landed in the half the cap
        # asks for, which with two boxes often fails; left alone, same-half
        # runs of six were reaching the animal. So redraw the whole screen
        # until the wanted half is represented. Positions stay uniform
        # within any one layout, and the only layouts made rarer are the
        # ones that would break the cap, which is what the cap is for.
        positions = random_positions(n)
        for _ in range(RANDOM_RESTARTS):
            if any(side_of(pos) == wanted for pos in positions):
                break
            positions = random_positions(n)
        choice_places = dict(zip(choice_slots, positions))
        candidates = [s for s in choice_slots
                      if side_of(choice_places[s]) == wanted] or choice_slots
        correct_slot = random.choice(candidates)
    else:
        choice_slots = [0, 1]
        choice_places = {0: CHOICE_POS["L"], 1: CHOICE_POS["R"]}
        correct_slot = 0 if next_side() == "L" else 1

    choice_colors = {s: (S_PLUS if s == correct_slot else S_MINUS)
                     for s in choice_slots}
    correct_side = side_of(choice_places[correct_slot])
    side_history.append(correct_side)


# ---------------------------------------------------------------------------
# Data logging

def trial_csv_path():
    return os.path.join(get_data_dir(), f"{Subject}_discrim.csv")


def session_csv_path():
    return os.path.join(get_data_dir(), f"{Subject}_discrim_sessions.csv")


# Column set is unchanged from the three-phase version so old and new
# sessions land in the same files. Two fields shift meaning with the stages:
#   Phase        now the stage name, "Transitional" or "Testing".
#   SampleColor  the priming square's colour in Transitional; blank in
#                Testing, which shows no priming screen.
# StartLatency and the "start" omission likewise only occur in Transitional;
# in Testing they are blank and zero, since there is nothing to start.
# The randomized layout adds a second block of columns, appended after the
# original set so the old columns keep their order and position:
#   Layout       "LeftRight" or "Random".
#   NumBlue      blue boxes shown; always 1 in the left/right layout.
#   BoxesLeft    how many of this trial's boxes fell in the left half. Chance
#                left-choice rate is not 50% in the random layout, so a side
#                bias can only be judged against what was actually offered.
#   CorrectX/Y, ChosenX/Y   box centres in relative screen coordinates, for
#                the spatial analyses the L/R columns are too coarse for.
TRIAL_COLUMNS = ["Subject", "Date", "Phase", "Trial", "Presentation",
                 "SampleColor", "CorrectSide", "ChosenSide", "ChosenColor",
                 "Correct", "StartLatency", "ChoiceLatency", "Omission",
                 "PelletsCommanded",
                 "Layout", "NumBlue", "BoxesLeft",
                 "CorrectX", "CorrectY", "ChosenX", "ChosenY"]

SESSION_COLUMNS = ["Subject", "Date", "Phase", "TrialsCompleted",
                   "FirstPresAccuracy", "LeftChoicePct", "CorrectionTrials",
                   "StartOmissions", "ChoiceOmissions", "MedianStartLatency",
                   "MedianChoiceLatency", "PelletsCommanded",
                   "Layout", "NumBlue"]


def append_path(path, columns):
    """Where to append, given a file that may carry an older header.

    Appending these wider rows to a file written before the randomized
    layout existed would leave the header naming 14 fields and every row
    after it carrying 21: the new values land under no header at all and the
    file reads as valid CSV, so nothing would flag it. When the header on
    disk is not the one about to be written, roll over to a numbered sibling
    and say so rather than corrupting the existing file.
    """
    if not os.path.isfile(path):
        return path
    try:
        with open(path, newline="") as f:
            if next(csv.reader(f), []) == columns:
                return path
    except OSError:
        return path

    stem, ext = os.path.splitext(path)
    n = 2
    while True:
        alt = f"{stem}_v{n}{ext}"
        if not os.path.isfile(alt):
            print(f"[DATA] {os.path.basename(path)} was written with an older "
                  f"column set; this session goes to {os.path.basename(alt)}")
            return alt
        with open(alt, newline="") as f:
            if next(csv.reader(f), []) == columns:
                return alt
        n += 1


def write_row(row):
    """Append one trial row, writing the header if the file is new.

    Motor_Task_Acc.py:95-101 opens in append mode and never writes a header,
    which is why Data/Sbj258.csv is bare numeric rows. Don't repeat that.
    """
    path = append_path(trial_csv_path(), TRIAL_COLUMNS)
    new_file = not os.path.isfile(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAL_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def record(presentation, chosen_slot, correct, omission, choice_latency):
    """Build, store and persist one trial record.

    chosen_slot is None on an omission. It is compared against None rather
    than tested for truth throughout: slot 0 is a real box.
    """
    chosen_pos = choice_places[chosen_slot] if chosen_slot is not None else None
    correct_pos = choice_places[correct_slot]
    row = {
        "Subject": Subject,
        "Date": datetime.datetime.now().isoformat(timespec="seconds"),
        "Phase": STAGE_LABELS[Stage],
        "Trial": trial,
        "Presentation": presentation,
        "SampleColor": sample_color,
        "CorrectSide": correct_side,
        "ChosenSide": side_of(chosen_pos) if chosen_pos is not None else "",
        "ChosenColor": choice_colors[chosen_slot] if chosen_slot is not None else "",
        "Correct": "" if omission != "none" else int(correct),
        "StartLatency": round(start_latency, 3) if start_latency else "",
        "ChoiceLatency": round(choice_latency, 3) if choice_latency else "",
        "Omission": omission,
        "PelletsCommanded": pellets_commanded,
        "Layout": LAYOUT_LABELS[Layout],
        "NumBlue": len(choice_slots) - 1,
        "BoxesLeft": sum(1 for s in choice_slots
                         if side_of(choice_places[s]) == "L"),
        "CorrectX": round(correct_pos[0], 4),
        "CorrectY": round(correct_pos[1], 4),
        "ChosenX": round(chosen_pos[0], 4) if chosen_pos is not None else "",
        "ChosenY": round(chosen_pos[1], 4) if chosen_pos is not None else "",
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
        "Phase": STAGE_LABELS[Stage],
        "TrialsCompleted": len(first),
        "FirstPresAccuracy": round(acc, 1),
        "LeftChoicePct": round(left, 1),
        "CorrectionTrials": len(corrections),
        "StartOmissions": sum(1 for r in records if r["Omission"] == "start"),
        "ChoiceOmissions": sum(1 for r in records if r["Omission"] == "choice"),
        "MedianStartLatency": round(statistics.median(start_lats), 2) if start_lats else "",
        "MedianChoiceLatency": round(statistics.median(choice_lats), 2) if choice_lats else "",
        "PelletsCommanded": pellets_commanded,
        "Layout": LAYOUT_LABELS[Layout],
        "NumBlue": int(NumBlue) if Layout == LAYOUT_RANDOM else 1,
    }


def write_session(summary):
    path = append_path(session_csv_path(), SESSION_COLUMNS)
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
    # Every frame in the pool, not just this trial's slots: the blue-box
    # count can only change between sessions, but clearing the pool keeps
    # this correct if that ever stops being true.
    centre_btn.place_forget()
    for slot in range(MAX_BOXES):
        choice_btn[slot].place_forget()
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
    global trial, is_correction, sample_color
    global fr_count, centre_onset, awaiting, start_latency

    if shutting_down:
        return

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

        # Yellow is correct in both stages and both layouts; all that moves
        # is where it sits and how many blue boxes sit beside it. The priming
        # square is logged as the sample in Transitional so the column says
        # what the animal was shown before the choice.
        sample_color = S_PLUS if Stage == TRANSITIONAL else ""
        build_layout()

    is_correction = correction
    fr_count = {"centre": 0}
    fr_count.update({slot: 0 for slot in range(MAX_BOXES)})
    start_latency = 0.0

    play_sound('7500.long.wav')  # long tone signals trial start

    if Stage != TRANSITIONAL:
        # Testing: no priming screen, so the trial opens on the choice pair.
        # centre_onset stays 0 and StartLatency is logged blank -- there is
        # no start response to time, and a "start" omission cannot occur.
        awaiting = "none"
        centre_onset = 0.0
        present_choices()
        return

    # Transitional: the priming screen is a single yellow square in the
    # centre, the same colour and size as the box in Shaping_full.py.
    #
    # Place FIRST, flush so the frame is really mapped, and only then set the
    # colour -- see paint_color() for why the order matters.
    awaiting = "centre"
    centre_btn.place(relx=CENTRE_POS[0], rely=CENTRE_POS[1],
                     relwidth=CENTRE_SIZE[0], relheight=CENTRE_SIZE[1],
                     anchor="center")
    paint_color(centre_btn, S_PLUS)
    gui.update()

    centre_onset = perf_counter()
    arm_timeout("start")


def arm_timeout(kind):
    global timeout_id
    cancel_timeout()
    timeout_id = gui.after(int(LimitedHold * 1000), lambda: omission(kind))


def centre_pressed(_event=None):
    """Priming square pressed (Transitional only).

    Gating the choices on a press of the shaped yellow square puts the pig at
    a known position and orientation at choice onset, and pairs the colour it
    was shaped on with the choice that is about to be reinforced.
    """
    global awaiting, start_latency

    if awaiting != "centre":
        return

    # Count first, gate immediately. No tone here at any point: trial start is
    # already marked by 7500.long.wav, and sounding 2900 -- the reinforcement
    # tone -- for merely clearing the priming screen devalues it as a signal.
    # The choices appearing is the feedback for a completed priming ratio.
    fr_count["centre"] += 1
    if fr_count["centre"] < FRCentre:
        neutral_flash()
        return

    cancel_timeout()
    start_latency = perf_counter() - centre_onset
    centre_btn.place_forget()
    present_choices()


def present_choices():
    """Show this trial's boxes and open the choice window.

    Reached from the priming press in Transitional and straight from
    trial_setup() in Testing, so the choice step itself is identical in the
    two stages -- same geometry, same limited hold, same scoring. It is also
    the single place either layout is drawn: build_layout() has already
    decided how many boxes there are and where they go, so nothing below
    depends on which layout is running.
    """
    global awaiting, choice_onset, active_choices

    size = RANDOM_CHOICE_SIZE if Layout == LAYOUT_RANDOM else CHOICE_SIZE

    # On a correction trial the incorrect options are displayed but inactive
    # -- they still absorb the touch, they just do not respond.
    for slot in choice_slots:
        relx, rely = choice_places[slot]
        choice_btn[slot].place(relx=relx, rely=rely,
                               relwidth=size[0], relheight=size[1],
                               anchor="center")
    # Colour only once every frame is mapped -- see paint_color().
    for slot in choice_slots:
        paint_color(choice_btn[slot], choice_colors[slot])
    active_choices = {correct_slot} if is_correction else set(choice_slots)
    gui.update()

    awaiting = "choice"
    choice_onset = perf_counter()
    arm_timeout("choice")


def choice_pressed(slot):
    """A choice box was touched."""
    global awaiting

    if awaiting != "choice" or slot not in active_choices:
        return

    fr_count[slot] += 1
    # The FR must be completed on a single button: touching any other choice
    # resets this one's partial count. [SET LOCALLY] -- Ao et al. do not
    # specify how partial runs across buttons should be handled.
    for other in choice_slots:
        if other != slot:
            fr_count[other] = 0

    if fr_count[slot] < FRChoice:
        # Sub-criterion presses are SILENT, with a neutral flash identical on
        # both buttons. Two separate reasons:
        #   - the correct/incorrect tones here would tell the pig the answer
        #     before the choice is committed, a confound once FRChoice > 1;
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
    outcome(slot, latency)


def outcome(chosen_slot, latency):
    """Score the choice, reinforce or not, then queue what comes next."""
    correct = (chosen_slot == correct_slot)
    presentation = "correction" if is_correction else "first"

    if correct:
        play_sound('2900.short.wav')
        # Reinforce before recording so PelletsCommanded on this row is the
        # session total including this trial's pellets.
        reinforcement()
        record(presentation, chosen_slot, True, "none", latency)
        next_trial()
    else:
        play_sound('290.short.wav')
        record(presentation, chosen_slot, False, "none", latency)
        # Correction trials are optional in both stages. They repeat the
        # identical trial -- priming screen included, in Transitional -- until
        # the pig chooses correctly, so no repeat cap is imposed; an omission
        # breaks the sequence via omission() below.
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
    # StartLatency survives on a "choice" omission in Transitional -- the pig
    # did press the priming square -- and is logged blank on a "start"
    # omission, and throughout Testing.
    record(presentation, None, False, kind, 0.0)
    print(f"[OMISSION] trial {trial}: {kind}")
    # An omission ends any correction sequence and moves to a fresh trial.
    next_trial(shortened=True)


def next_trial(correction=False, shortened=False):
    """Schedule the next presentation after a variable ITI.

    Shaping_full.py shortens the interval after an error (line 438); the same
    is done here so a run of errors does not stall the session.
    """
    global iti_id
    if shutting_down:
        return
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
    """Close the session down and put the summary up.

    Runs at most once: the quit button, a limit being reached and a touch
    that arrives while reinforcement() is pumping the event loop can all
    land here, and summarising twice would write two session rows.
    """
    global shutting_down, awaiting

    if shutting_down:
        return
    shutting_down = True

    # Cancel the pending ITI / limited hold so no trial starts behind the
    # summary, and stop the task widgets from scoring any further touches.
    for aid in gui.tk.eval('after info').split():
        try:
            gui.after_cancel(aid)
        except Exception:
            pass
    awaiting = "none"
    clear_screen()
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
        global Stage, Subject, MaxTrials, LimitedHold, FRCentre, FRChoice, \
            ReinfAmt, Blackout, Correction, SessionCap, ShowCursor, \
            Layout, NumBlue

        Stage = int(stage_var.get())
        Layout = (LAYOUT_RANDOM if layout_var.get() == LAYOUT_MENU[LAYOUT_RANDOM]
                  else LAYOUT_LR)
        # The left/right layout shows exactly one blue box whatever the menu
        # was left on, so NumBlue always matches what was actually displayed.
        NumBlue = int(blue_var.get()) if Layout == LAYOUT_RANDOM else 1
        Subject = e_subj.get().strip() or "Sbj000"
        MaxTrials = int(float(e_trials.get()))
        LimitedHold = float(e_hold.get())
        FRCentre = int(float(e_frc.get()))
        FRChoice = int(float(e_frx.get()))
        ReinfAmt = int(float(e_reinf.get()))
        Blackout = float(e_black.get())
        SessionCap = float(e_cap.get())
        Correction = 1 if corr_var.get() == "Yes" else 0
        ShowCursor = 1 if cursor_var.get() == "Visible" else 0

    def setup():
        update_vals()
        popup.destroy()

    def stage_defaults():
        """Grey out the priming ratio in Testing, where nothing primes."""
        e_frc.config(state=("normal" if int(stage_var.get()) == TRANSITIONAL
                            else "disabled"))

    def layout_defaults():
        """Grey out the blue-box count outside the randomized layout."""
        blue_menu.config(
            state=("normal" if layout_var.get() == LAYOUT_MENU[LAYOUT_RANDOM]
                   else "disabled"))

    popup = tk.Tk()
    popup.title("Colour Discrimination - Transitional / Testing")
    width = popup.winfo_screenwidth()
    height = popup.winfo_screenheight()
    popup.geometry(f'{int(width * 0.85)}x{int(height * 0.8)}+{int(width * 0.075)}+{int(height * 0.075)}')

    stage_var = IntVar(value=TRANSITIONAL)
    rd1 = Radiobutton(popup, text="Transitional\nPriming screen, then\nyellow vs blue",
                      variable=stage_var, value=TRANSITIONAL, command=stage_defaults)
    rd2 = Radiobutton(popup, text="Testing\nYellow vs blue only\n(no priming screen)",
                      variable=stage_var, value=TESTING, command=stage_defaults)
    rd1.grid(row=1, column=1, padx=2, pady=15)
    rd2.grid(row=2, column=1, padx=2, pady=15)

    labels = [
        ("Subject:", 1), ("Trials\n(first presentations):", 2),
        ("Limited\nHold (s):", 3), ("FR priming\n(Transitional only):", 4),
        ("FR choice:", 5), ("Choice layout:", 6),
    ]
    for text, row in labels:
        tk.Label(popup, text=text, font=24).grid(row=row, column=3, padx=2, pady=15)

    labels2 = [
        ("Pellets per\ncorrect:", 1), ("Blackout (min):", 2),
        ("Session cap\n(min):", 3), ("Correction trials:", 4),
        ("Mouse cursor:", 5), ("Blue boxes\n(random layout only):", 6),
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
    corr_var.set("Yes" if Correction else "No")
    OptionMenu(popup, corr_var, "Yes", "No").grid(row=4, column=6, padx=2, pady=10)

    # Hidden unless the experimenter changes it here; the choice is not
    # remembered between sessions, so every run starts hidden again.
    cursor_var = StringVar(popup)
    cursor_var.set("Visible" if ShowCursor else "Hidden")
    OptionMenu(popup, cursor_var, "Hidden", "Visible").grid(row=5, column=6, padx=2, pady=10)

    # Left / Right is the original two-box task and stays the default, so an
    # experimenter who opens this window and presses Start gets the session
    # the program has always run.
    layout_var = StringVar(popup)
    layout_var.set(LAYOUT_MENU[Layout])
    OptionMenu(popup, layout_var, LAYOUT_MENU[LAYOUT_LR],
               LAYOUT_MENU[LAYOUT_RANDOM],
               command=lambda _choice: layout_defaults()) \
        .grid(row=6, column=4, padx=2, pady=10)

    # A menu rather than a free entry: 0 blue boxes is not a discrimination
    # and more than MAX_BLUE will not fit on screen without overlapping.
    blue_var = StringVar(popup)
    blue_var.set(str(NumBlue))
    blue_menu = OptionMenu(popup, blue_var,
                           *[str(n) for n in range(1, MAX_BLUE + 1)])
    blue_menu.grid(row=6, column=6, padx=2, pady=10)

    e_subj.insert(0, Subject)
    e_trials.insert(0, str(MaxTrials))
    e_hold.insert(0, str(LimitedHold))
    e_frc.insert(0, str(FRCentre))
    e_frx.insert(0, str(FRChoice))
    e_reinf.insert(0, str(ReinfAmt))
    e_black.insert(0, str(Blackout))
    e_cap.insert(0, str(SessionCap))
    stage_defaults()
    layout_defaults()

    tk.Button(popup, text="Start", command=setup, font=("bold", "14"),
              height=3, width=12).grid(row=7, column=1, columnspan=2, pady=20)

    popup.grid_rowconfigure(0, weight=1)
    popup.grid_rowconfigure(8, weight=1)
    popup.grid_columnconfigure(0, weight=1)
    popup.grid_columnconfigure(7, weight=1)

    popup.mainloop()


def report_end():
    """
    End-of-session summary. First-presentation accuracy and left-choice
    percentage are the two numbers protocol 8.3 and 8.4 require checking
    every session; pellets commanded feeds the 9.2 reconciliation.

    Drawn inside the task window, in a panel that covers it, rather than in
    a second Tk root. Two roots meant two nested mainloops -- the summary's
    running inside the task window's -- and the process only ended if both
    unwound cleanly. With one root, Exit destroys it, gui.mainloop() returns
    and the script runs off the end of the `with device:` block.
    """
    summary = summarise()
    write_session(summary)

    print("\n--- SESSION SUMMARY ---")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"side sequence: {''.join(side_history)}")

    # The pointer is hidden during the task unless the experimenter asked
    # for it; the summary is for a person, so bring it back regardless --
    # Exit is unclickable with a mouse otherwise.
    gui.configure(cursor="")

    panel = tk.Frame(gui)
    panel.place(relx=0, rely=0, relwidth=1, relheight=1)

    if Layout == LAYOUT_RANDOM:
        layout_note = f"random positions, {int(NumBlue)} blue"
    else:
        layout_note = "left / right"
    tk.Label(panel,
             text=f"{Subject}  -  {STAGE_LABELS[Stage]} stage  -  {layout_note}",
             font=("Bold", 30)).grid(row=1, column=1, columnspan=3, pady=20)

    cells = [
        ("Trials\ncompleted", summary["TrialsCompleted"]),
        ("First-pres\naccuracy", f"{summary['FirstPresAccuracy']}%"),
        ("Left choice\n(first pres)", f"{summary['LeftChoicePct']}%"),
        ("Correction\ntrials", summary["CorrectionTrials"]),
        ("Start\nomissions", summary["StartOmissions"]),
        ("Choice\nomissions", summary["ChoiceOmissions"]),
        ("Median start\nlatency (s)", summary["MedianStartLatency"]),
        ("Median choice\nlatency (s)", summary["MedianChoiceLatency"]),
        ("Pellets\ncommanded", summary["PelletsCommanded"]),
    ]
    for i, (label, value) in enumerate(cells):
        col = 1 + (i % 3)
        row = 2 + 2 * (i // 3)
        tk.Label(panel, text=label, font=("Bold", 20)).grid(row=row, column=col, padx=15, pady=5)
        tk.Label(panel, text=str(value), font=("Arial", 26)).grid(row=row + 1, column=col, padx=15, pady=5)

    # Side bias reading, per the table in protocol 8.4. The thresholds there
    # assume the two-box left/right screen, where an unbiased animal chooses
    # each half half the time. In the random layout the boxes themselves are
    # not split evenly between the halves, so chance left-choice rate is not
    # 50% and these cut-offs do not apply -- the per-trial BoxesLeft and
    # ChosenX columns are what a bias test should be run against instead.
    left = summary["LeftChoicePct"]
    if summary["TrialsCompleted"] == 0:
        note = ""
    elif Layout == LAYOUT_RANDOM:
        note = "Random layout - judge side bias from BoxesLeft / ChosenX"
    elif left > 75 or left < 25:
        note = "ESTABLISHED SIDE BIAS"
    elif left > 60 or left < 40:
        note = "Emerging side bias"
    else:
        note = "Side balance normal"
    tk.Label(panel, text=note, font=("Bold", 22), fg="red" if "BIAS" in note else "black") \
        .grid(row=8, column=1, columnspan=3, pady=20)

    # Destroying the root ends the one mainloop, which is the whole exit.
    tk.Button(panel, text='Exit', command=gui.destroy,
              font=("bold", "20"), height=2, width=10).grid(row=10, column=1, columnspan=3, pady=20)

    panel.grid_rowconfigure(0, weight=1)
    panel.grid_rowconfigure(11, weight=1)
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_columnconfigure(4, weight=1)


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
    # An empty cursor spec means "inherit the default arrow"; "none" hides it.
    gui.configure(bg="black", cursor="" if ShowCursor else "none")

    # places start button
    start_button = tk.Button(gui, text="START", font=("bold", "40"), command=lambda: start())
    start_button.place(relheight=1, relwidth=1, relx=1, rely=0, anchor="ne")

    # centre start box and the pool of choice boxes
    centre_btn = tk.Frame(gui, bg=S_PLUS)
    centre_btn.bind("<Button-1>", centre_pressed)

    # One frame per slot, built once and re-placed each trial. MAX_BOXES of
    # them regardless of layout or blue-box count, so nothing is created
    # mid-session; unused slots are simply never placed. Bind the slot as a
    # default argument, not by closing over the loop variable, or every frame
    # would report the last slot.
    choice_btn = {}
    for _slot in range(MAX_BOXES):
        _frame = tk.Frame(gui, bg=S_MINUS)
        _frame.bind("<Button-1>", lambda e, s=_slot: choice_pressed(s))
        choice_btn[_slot] = _frame

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
