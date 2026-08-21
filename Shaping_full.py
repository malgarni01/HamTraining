#Software is provided and licensed under the CC-BY-NC 4.0 license: https://creativecommons.org/licenses/by-nc/4.0/. 
#This means that you can use, adapt, and share so long as you provide attribution. 
#However, commercial uses are not permitted. 
#This software was developed by Dr. Vonder Haar. Please attribute to him and provide a citation to published work or this GitHub, as appropriate. 
#For commercial use, please contact Dr. Vonder Haar for licensing options. Generally, use for small-scale research will be made free of charge.

from tkinter import *
import tkinter as tk  # for GUI
# import RPi.GPIO as GPIO  # For inputs/outputs
from threading import Timer  # for periodic loops
import random  # for random number selection
from time import perf_counter  # for calculating latencies/timers
import time
import os
import sys
from iointerface_api import *
from platform_config import play_sound, ensure_sound_files

ensure_sound_files()

scan_time = 1
print(f"scanning for {scan_time} seconds, please wait...")

# On the Med Associates COM-106 (Windows) drive the ENV-204 feeder through
# MED-PC's file-drop backend; elsewhere fall back to Mock/serial. The MED-PC
# backend itself falls back to MockDevice if C:\MED-PC is not present, so a
# plain Windows dev box still runs without stalling on dispense acks.
# USE_MEDPC = sys.platform == "win32"
USE_MEDPC = sys.platform == "darwin"
devices = IOInterface.discover_interfaces(timeout=scan_time,
                                          use_medpc=USE_MEDPC)
for device in devices:
    print(f"Found I/O Interface: {device.address}")

if len(devices) == 0:
    print("Failed to find device!")
    exit()

# GLOBAL CONSTANTS
VI_list = [3, 4, 4, 5, 5, 5, 6, 6, 7]  # list of variable interval schedule times to randomly select from
position_list = [(0.4, 0.0), (0.7, 0.3), (1, 0.55)]  # stage 3 button position list
new_pos_list = [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)]  # stage 4 button position list
btn_size = 0.7  # button size constant
fr_req = 1  # fixed ratio requirement
FLASH_MS = 60  # dwell time for every flash, in ms. Without an explicit hold the
               # label was placed and removed inside one event-loop pass, so
               # nothing was actually shown to the animal.
NEUTRAL_FLASH_BG = "gray50"  # sub-criterion touch acknowledgement. Must be identical
                             # for correct and incorrect touches, and distinct from
                             # both yellow (target) and black (background).
color_on = 0    #to flag color change on buttons

# Global Counters
hand_shape_resp = 0  # hand shaped responses counter
trial = 0  # trial number counter
size_adj_trials = 0  # size adjustment trial counter
fr_resp = 0  # fixed ratio response
inc_resp = 0  # incorrect response counter

# Global Timers
stage_1_start_time = 0  # timers for each stage
stage_2_start_time = 0
stage_3_start_time = 0
stage_4_start_time = 0

# Global Misc
# when a button is pushed, these variables changes to whatever button is pushed (correct or incorrect,
# defined in the code as "response" or "inc")
# these are bound and initialized to buttons, found at the bottom of the program
inc = 0
response = 0

# Misc
size_adj_correct = [0, 0, 0]  # size adjustment array for correct responses in stage 4

# Data Global Counters
stage_0_responses = 0
stage_1_responses = 0
stage_2_responses = 0
stage_3_responses = 0
stage_3_omissions = 0
stage_4_responses = 0
stage_4_omissions = 0
stage_4_incorrects = 0

# Default Settings (Can be modified)
Autoshape = 1  # if this variable is set to 1, goes to autoshaping for stage 0, otherwise does keyboard hand shaping
DelivTimer = 30  # stage 0 and stage 2 timeout value for timer
LimitedHold = 25	#Time which animal has to respond
Stage0Resp = 20
Stage1Resp = 40
Stage2Resp = 15
Stage3Resp = 40
Stage4Resp = 50
MaxTrial = 100
StartStage = 0
Blackout = 0.15  # timer in min
ReinfAmt = 1


# btn_size = local variable modified in loop
# position list
# x - upper right corner starts from X,Y, goes down+left
# y - starts from top
# x = new_pos_list[]+0.5*btn_size
# y = new_pos_list[]-0.5*btn_size*5/4


# flash helpers


def _hold(ms):
    """Keep a flash on screen for a fixed time.

    time.sleep is the house idiom in this file, and press()/incorrect() are Tk
    event handlers -- nothing else needs to run during a 60 ms flash. Without
    this the label was placed and removed within a single pass of the event
    loop, i.e. for less than one 60 Hz frame, so no flash was actually drawn.
    """
    gui.update()
    time.sleep(ms / 1000.0)


def neutral_flash():
    """Acknowledge a sub-criterion touch without revealing correctness.

    Full screen, one colour, identical whichever region was touched. The old
    per-touch feedback differed by button -- yellow-on-black for the target,
    all-black for off-target -- which handed the pig the answer on touch 1 of
    an FR-3, so the ratio measured nothing. Sound is withheld entirely until
    the ratio completes.

    The overlay is full screen on purpose: flashing only the touched region
    would still differ by button, since resp_btn is a small rectangle while
    inc_btn covers the whole screen. The geometry alone would carry the signal.
    """
    lbl = tk.Label(gui, bg=NEUTRAL_FLASH_BG, activebackground=NEUTRAL_FLASH_BG)
    lbl.place(relheight=1.1, relwidth=1.1, relx=1.05, rely=-0.05, anchor="ne")
    _hold(FLASH_MS)
    lbl.place_forget()
    gui.update()


# press function handles correct button presses

def press(var):
    global response, size_adj_correct, fr_resp, inc_resp

    # Count first and gate immediately. Everything below this point -- tone and
    # differential flash alike -- is the reinforced-response signal and must not
    # fire until the fixed ratio is complete.
    fr_resp += 1
    if fr_resp < fr_req:
        neutral_flash()  # touch registered; correctness withheld
        return

    # flashes the background yellow
    lbl = tk.Label(gui, bg="yellow", activebackground="yellow")
    pos = resp_btn.place_info()
    inc_lbl = tk.Label(bg="black", activebackground="black")
    inc_lbl.place(relheight=1.1, relwidth=1.1, relx=1.05, rely=-0.05, anchor="ne")
    lbl.place(relx=pos["relx"], rely=pos["rely"], relwidth=pos["relwidth"], relheight=pos["relheight"],
              anchor=pos["anchor"])
    play_sound('2900.short.wav') # play tone for response
    _hold(FLASH_MS)              # tone and flash coincide
    lbl.place_forget()
    inc_lbl.place_forget()
    gui.update()

    inc_btn.place_forget()
    resp_btn.place_forget()
    gui.update()
    response = var
    fr_resp = 0
    inc_resp = 0
    if stage_4_start_time > 0:
        size_adj_correct[size_adj_trials - 1] = 1


# incorrect function handles incorrect button presses

def incorrect(var):
    # fr_resp, not fr_rsp: the old name was a typo, so the reset below bound a
    # local and the global partial count on the target was never cleared.
    global inc, size_adj_correct, response, inc_resp, fr_resp

    # Count first and gate immediately -- see press(). An off-target touch that
    # does not complete the ratio must be indistinguishable from an on-target
    # one that does not complete the ratio.
    inc_resp += 1
    if inc_resp < fr_req:
        neutral_flash()  # touch registered; correctness withheld
        return

    # flash background back
    inc_lbl = tk.Label(gui, bg="black", activebackground="black")
    pos = inc_btn.place_info()
    inc_lbl.place(relx=pos["relx"], rely=pos["rely"], relwidth=pos["relwidth"], relheight=pos["relheight"],
                  anchor=pos["anchor"])
    play_sound('290.short.wav') # play tone for response
    _hold(FLASH_MS)             # tone and flash coincide
    inc_lbl.place_forget()
    gui.update()

    fr_resp = 0
    inc_resp = 0
    inc = var
    resp_btn.place_forget()
    inc_btn.place_forget()
    gui.update()
    response = 0
    size_adj_correct[size_adj_trials - 1] = 0


# Basic reinforcement/punishment function

def reinforcement():
    global response
    response = 0
    reinforcers = 0

    def reinf_off():
        # these commands are responsible for signaling the pellet dispenser
        # if you want to change reinforcer amount, that can be done through the ReinfAmt variable
        # otherwise try not to touch
        # On the MED-PC backend, write_output(1, ACTIVE) arms the feeder and
        # write_output(1, INACTIVE) commits one IR-verified dispense request;
        # on Mock/serial these are plain output toggles (unchanged behavior).
        device.write_output(1, IOState.INACTIVE)  # Stop asserting pellet dispenser
        device.write_output(2, IOState.INACTIVE)  # Turn of beeper

    # IR-verification payoff: snapshot the cumulative delivered count so we
    # can log requested-vs-actually-delivered for this reinforcement. This is
    # a no-op attribute on Mock/serial devices (getattr default -> None).
    _delivered_before = getattr(device, "pellets_delivered_total", None)

    while True:
        device.write_output(1, IOState.ACTIVE)  # Turn on pellet dispenser
        device.write_output(2, IOState.ACTIVE)  # Turn on beeper
        pellet_timer = Timer(0.25, reinf_off)  # timer 0.25s delay for pellet cycle
        pellet_timer.start()
        pellet_timer.join()
        reinforcers += 1  # breaks from loop when reinforcement limit is reached
        if reinforcers >= ReinfAmt:
            break

    # Per-trial IR-verification log (MED-PC backend only).
    if _delivered_before is not None:
        requested = int(ReinfAmt)
        delivered = getattr(device, "pellets_delivered_total",
                            _delivered_before) - _delivered_before
        status = getattr(device, "last_status", None)
        if getattr(device, "last_empty_hopper", False) or delivered < requested:
            print(f"[REWARD] trial {trial}: requested={requested} "
                  f"delivered={delivered} status={status} *** CHECK FEEDER ***")
        else:
            print(f"[REWARD] trial {trial}: requested={requested} "
                  f"delivered={delivered} status={status}")


# START MAIN PROGRAM LOOP

# ---------------------------------------------------------------------------
# Stage 0: Any screen touch reinforces. Can hand shape using keyboard input
# Settings located at the top of program after counter definitions
# Autoshape: Setting for autoshape delivery, change to either 0 or 1 - autoshape will deliver a pellet after illumination. Disable for hand-shaping.

def stage_0_setup():
    global trial, stage_0_start_time, fr_resp
    trial += 1
    fr_resp = 0  # a partial ratio must not carry into the next trial
    print("trial started - stage 0")
    stage_0_start_time = perf_counter() #start timer
    resp_btn.config(bg="black")
    resp_btn.place(relheight=1.0, relwidth=1, relx=1.0, rely=0.0, anchor="ne") #place response button (whole screen)
    stage_0()


def stage_0():
    # loop function
    def stage_0_loop():
        global response, hand_shape_resp, stage_0_start_time, stage_0_responses, color_on

        # response is the button variable, default set to 0
        # on button press, the response variable is changed in the press() function, triggering this if statement
        if response != 0:
            # on response, increment response counter and remove button
            stage_0_responses += 1
            resp_btn.place_forget()
            # reinforce, then reset response variable back to 0
            reinforcement()
            response = 0
            color_on = 0
            # if max number of stage 0 responses is exceeded, begin stage 1, else loop
            if stage_0_responses >= Stage0Resp:
                gui.update()
                stage_1_setup()
            else:
                stage_0_setup()

        # if hand_shape_resp is set to anything but 0, remove the response button to allow handshaping
        elif hand_shape_resp != 0:
            resp_btn.place_forget()
            reinforcement()
            response = 0
            color_on = 0
            hand_shape_resp = 0
            stage_0_setup()

        # Autoshape trigger
        elif color_on == 0:
            if perf_counter() - stage_0_start_time >= DelivTimer-10:
                if Autoshape == 1:
                    resp_btn.config(bg="yellow")
                    play_sound('7500.long.wav') # long tone signals start
                    color_on = 1
                    stage_0()
            else:
                stage_0()
            
        #End with reinforcement after timeout for autoshape or end trial for non-autoshape
        else:
            if perf_counter() - stage_0_start_time >= DelivTimer:
                # if autoshape is enabled (set to 1), run this statement
                if Autoshape == 1:
                    print("autoshape reinforced")
                    reinforcement()
                    color_on = 0
                    resp_btn.place_forget()
                    time.sleep(1)
                    stage_0_setup()
                else:
                    stage_0()
            else:
                stage_0()

    # schedule next tick on the Tk main thread (gui.after, not threading.Timer)
    gui.after(10, stage_0_loop)

# ---------------------------------------------------------------------------
# Stage 1: Same as stage 0, except only presses when the screen illuminated result in pellet delivery

def stage_1_setup():
    global trial, stage_1_start_time, fr_resp
    time.sleep(random.choice(VI_list)) # pause for a random amount of time chosen from the VI_list array
    trial += 1
    fr_resp = 0  # a partial ratio must not carry into the next trial
    play_sound('7500.long.wav') # long tone signals start
    stage_1_start_time = perf_counter()

    # creates response button, colored yellow by default
    resp_btn.place(relheight=1.0, relwidth=1, relx=1.0, rely=0.0, anchor="ne")
    resp_btn.config(bg="yellow")
    stage_1()


def stage_1():
    def stage_1_loop():
        global response, hand_shape_resp, stage_1_start_time, stage_1_responses

        # response if block, waiting for button press
        if response != 0:
            stage_1_responses += 1
            resp_btn.place_forget()
            reinforcement()
            response = 0
            # stage 2 if max stage 1 responses is reached
            if stage_1_responses >= Stage1Resp:
                resp_btn.place_forget()
                gui.update()
                stage_2_setup()
            else:
                stage_1_setup()

        # hand shaping block if enabled
        elif hand_shape_resp != 0:
            resp_btn.place_forget()
            reinforcement()
            response = 0
            hand_shape_resp = 0
            stage_1_setup()

        # loops on no response
        else:
            stage_1()

    gui.after(10, stage_1_loop)

# ---------------------------------------------------------------------------
# Stage 2: Button now moves horizontally but full screen width. Same size button every trial

def stage_2_setup():
    global trial, stage_2_start_time, fr_resp
    time.sleep(random.choice(VI_list)) # pause for a random amount of time chosen from the VI_list array
    trial += 1
    fr_resp = 0  # a partial ratio must not carry into the next trial
    play_sound('7500.long.wav') # play long tone for trial start
    stage_2_start_time = perf_counter()

    # places response button
    resp_btn.place(relheight=0.4, relwidth=1, relx=1.0, rely=0.2, anchor="ne")
    resp_btn.config(bg="yellow")
    stage_2()


def stage_2():
    def stage_2_loop():
        global response, stage_2_start_time, stage_2_responses

        # response if block, waiting for button press
        if response != 0:
            stage_2_responses += 1
            resp_btn.place_forget()
            reinforcement()
            response = 0
            # stage 3 if max stage 2 responses is reached
            if stage_2_responses >= Stage2Resp:
                resp_btn.place_forget()
                gui.update()
                stage_3_setup()
            else:
                stage_2_setup()

        # timeout handler
        else:
            if perf_counter() - stage_2_start_time >= DelivTimer:
                resp_btn.place_forget()
                stage_2_setup()
            else:
                stage_2()

    gui.after(10, stage_2_loop)

# ---------------------------------------------------------------------------
# Stage 3: Button begins moving around 5 possible positions on screen, though stays the same size

def stage_3_setup():
    global trial, stage_3_start_time, fr_resp
    time.sleep(random.choice(VI_list)) # pause for a random amount of time chosen from the VI_list array
    trial += 1
    fr_resp = 0
    print("trials:" + str(trial))
    play_sound('7500.long.wav') # play long tone for trial start

    # place response button
    # position is determined by random selection from the position_list array
    resp_btn.place(relheight=0.45, relwidth=0.4,
                   relx=random.choice(position_list)[:1],
                   rely=random.choice(position_list)[1:], anchor="ne")
    resp_btn.config(bg="yellow")
    stage_3_start_time = perf_counter()
    stage_3()


def stage_3():
    def stage_3_loop():
        global response, stage_3_start_time, stage_3_responses, stage_3_omissions

        # response if block, waiting for button press
        if response != 0:
            stage_3_responses += 1
            resp_btn.place_forget()
            reinforcement()
            response = 0
            # stage 4 if max stage 3 responses is reached
            if stage_3_responses >= Stage3Resp:
                resp_btn.place_forget()
                stage_4_setup()
            else:
                stage_3_setup()

        # timeout handler
        else:
            if perf_counter() - stage_3_start_time >= LimitedHold:
                stage_3_omissions += 1
                resp_btn.place_forget()
                stage_3_setup()
            else:
                stage_3()

    gui.after(10, stage_3_loop)

# ---------------------------------------------------------------------------
# Stage 4: Button begins moving around the screen, changing size based on number of correct responses
# now punishes incorrect responses
# This stage is only necessary to shape responses to very small boxes. Consider deleting/disabling if this is not necessary for experiment

def stage_4_setup():
    global inc, trial, stage_4_start_time, btn_size, size_adj_trials, fr_resp, inc_resp

    # inc functions the same as the response variable
    # when an incorrect response is given, pause for a random time divided by 3
    # otherwise, pause full length
    if inc != 0:
        inc = 0
        time.sleep(random.choice(VI_list) / 3)
    else:
        time.sleep(random.choice(VI_list))
    trial += 1
    fr_resp = 0
    inc_resp = 0
    play_sound('7500.long.wav') # play long tone for trial start

    # every three trials; check corrects and adjust button size
    if size_adj_trials >= 3:
        size_adj_trials = 0
        if sum(size_adj_correct) >= 2:
            btn_size = btn_size * 0.85
        else:
            btn_size = btn_size / .85

    # place button randomly
    rand_list = [0, 1, 2, 3, 4]
    rand = int(random.choice(rand_list))
    inc_btn.place(relheight=1.1, relwidth=1.1, relx=1.05, rely=-0.05, anchor="ne")
    inc_btn.config(bg="black")
    resp_btn.place(relheight=btn_size * 5 / 4, relwidth=btn_size,
                   relx=float(new_pos_list[rand][0]) + 0.5 * btn_size,
                   rely=float(new_pos_list[rand][1]) - 0.5 * (btn_size * 5 / 4),
                   anchor="ne")
    resp_btn.config(bg="yellow")
    size_adj_trials += 1

    # print button info
    print("X-" + str(new_pos_list[rand][0]))
    print("Y-" + str(new_pos_list[rand][1]))
    print(btn_size)
    print(size_adj_trials)
    print(size_adj_correct)
    stage_4_start_time = perf_counter()
    stage_4()


def stage_4():
    def stage_4_loop():
        global response, stage_4_start_time, stage_4_responses, stage_4_omissions, inc, stage_4_incorrects

        # incorrect if block, waiting for button press
        if inc != 0:
            stage_4_incorrects += 1
            response = 0
            resp_btn.place_forget()
            inc_btn.place_forget()
            gui.update()
            stage_4_setup()

        # correct response if block, waiting for button press
        elif response != 0 and inc == 0:
            stage_4_responses += 1
            resp_btn.place_forget()
            inc_btn.place_forget()
            gui.update()
            reinforcement()
            response = 0
            # clears screen when max trials is exceeded
            if stage_4_responses >= Stage4Resp:
                resp_btn.place_forget()
                gui.update()
                play_sound('end_tone.wav')  # play tone for end

            else:
                stage_4_setup()

        # timeout handler
        else:
            if perf_counter() - stage_4_start_time >= LimitedHold:
                stage_4_omissions += 1
                resp_btn.place_forget()
                inc_btn.place_forget()
                gui.update()
                stage_4_setup()
            else:
                stage_4()

    gui.after(100, stage_4_loop)

# exit program function, clears gui elements, calls report function
def exit_program():
    if resp_btn.winfo_exists():
        end_program()
    report()

# report function, destroys gui, calls report_end function
def report():
    # Cancel pending after() callbacks so they don't fire on a destroyed root
    # and print "invalid command name ..." at shutdown.
    for aid in gui.tk.eval('after info').split():
        gui.after_cancel(aid)
    gui.destroy()
    report_end()

# gui clear function called by exit_program (report() destroys gui)
def end_program():
    pass

# setup function, called on program start
def start():
    def full_start():
        if StartStage == 0:
            stage_0_setup()
        if StartStage == 1:
            stage_1_setup()
        if StartStage == 2:
            stage_2_setup()
        if StartStage == 3:
            stage_3_setup()
        if StartStage == 4:
            stage_4_setup()

    start_button.destroy()
    gui.after(int(Blackout * 60 * 1000), full_start)


# settings menu called on program start allows changing of max trials per stage, reinforcer delay,
# limited hold, and blackout timers
def settings():

    # gets current values for all variables listed below
    def update_vals():
        global DelivTimer, LimitedHold, Stage0Resp, Stage1Resp, Stage2Resp, Stage3Resp, \
            Stage4Resp, StartStage, Blackout, Autoshape, fr_req
        DelivTimer = float(e4.get())
        LimitedHold = float(e5.get())
        Blackout = float(e6.get())
        # int, and never below 1: a fractional ratio is meaningless and a zero
        # or negative one would make the gate always true.
        fr_req = max(1, int(float(e9.get())))
        Stage0Resp = float(e0.get())
        Stage1Resp = float(e1.get())
        Stage2Resp = float(e2.get())
        Stage3Resp = float(e3.get())
        Stage4Resp = float(e8.get())
        if auto_var.get() == "Yes":
            Autoshape = 1
        else:
            Autoshape = 0

    # sets up settings menu
    def setup(var):
        global StartStage, response
        StartStage = var
        update_vals()
        popup.destroy()

    # settings gui popup initialization
    popup = tk.Tk()
    width = popup.winfo_screenwidth()
    height = popup.winfo_screenheight()
    popup.geometry(f'{int(width * 0.85)}x{int(height * 0.8)}+{int(width * 0.075)}+{int(height * 0.075)}')

    # creates settings buttons
    b1 = tk.Button(popup, text="Start",
                   command=lambda: setup(stage_var.get()), font=("bold", "14"), height=3, width=12)
    b1.grid(row=6, column=1, rowspan=1, columnspan=2)

    stage_var = IntVar()
    rd0 = Radiobutton(popup, text="Stage 0\nFR-1", variable=stage_var, value=0)
    rd1 = Radiobutton(popup, text="Stage 1\nColor Discrimination", variable=stage_var, value=1)
    rd2 = Radiobutton(popup, text="Stage 2\nSmaller Box", variable=stage_var, value=2)
    rd3 = Radiobutton(popup, text="Stage 3\nMoving Box", variable=stage_var, value=3)
    rd4 = Radiobutton(popup, text="Stage 4\nPunish Incorrect", variable=stage_var, value=4)
    rd0.grid(row=1, column=1, rowspan=1, columnspan=2)
    rd1.grid(row=2, column=1, rowspan=1, columnspan=2)
    rd2.grid(row=3, column=1, rowspan=1, columnspan=2)
    rd3.grid(row=4, column=1, rowspan=1, columnspan=2)
    rd4.grid(row=5, column=1, rowspan=1, columnspan=2)

    # creates settings labels
    l0 = tk.Label(popup, text=("Responses:" + str(Stage1Resp)), font=24)
    l1 = tk.Label(popup, text=("Responses:" + str(Stage2Resp)), font=24)
    l2 = tk.Label(popup, text=("Responses:" + str(Stage2Resp)), font=24)
    l3 = tk.Label(popup, text=("Responses:" + str(Stage3Resp)), font=24)
    l8 = tk.Label(popup, text=("Responses:" + str(Stage4Resp)), font=24)
    l4 = tk.Label(popup, text=("Reinforcer\nDelay (s):\n" + str(DelivTimer)), font=24)
    l5 = tk.Label(popup, text=("Limited\nHold (s):\n" + str(LimitedHold)), font=24)
    l6 = tk.Label(popup, text=("Blackout (s):\n" + str(Blackout)), font=24)
    options = ["Yes", "No"]
    auto_var = StringVar(popup)
    auto_var.set(options[0])
    l7 = tk.Label(popup, text=("Autoshape: " + str(Autoshape) + "\n(1=Yes)"), font=24)
    dropdown = OptionMenu(popup, auto_var, *options)
    l9 = tk.Label(popup, text=("FR Requirement:\n" + str(fr_req)), font=24)

    # organizing of all labels and entry boxes into a grid
    dropdown.grid(row=4, rowspan=1, column=6, padx=2, pady=25)

    l0.grid(row=1, rowspan=1, column=3, padx=2, pady=25)
    l1.grid(row=2, rowspan=1, column=3, padx=2, pady=25)
    l2.grid(row=3, rowspan=1, column=3, padx=2, pady=25)
    l3.grid(row=4, rowspan=1, column=3, padx=2, pady=25)
    l8.grid(row=5, rowspan=1, column=3, padx=2, pady=25)
    l4.grid(row=1, rowspan=1, column=5, padx=2, pady=25)
    l5.grid(row=2, rowspan=1, column=5, padx=2, pady=25)
    l6.grid(row=3, rowspan=1, column=5, padx=2, pady=25)
    l7.grid(row=4, rowspan=1, column=5, padx=2, pady=25)
    l9.grid(row=5, rowspan=1, column=5, padx=2, pady=25)

    e0 = tk.Entry(popup, width=3, font=24)
    e1 = tk.Entry(popup, width=3, font=24)
    e2 = tk.Entry(popup, width=3, font=24)
    e3 = tk.Entry(popup, width=3, font=24)
    e4 = tk.Entry(popup, width=3, font=24)
    e5 = tk.Entry(popup, width=3, font=24)
    e6 = tk.Entry(popup, width=3, font=24)
    e8 = tk.Entry(popup, width=3, font=24)
    e9 = tk.Entry(popup, width=3, font=24)

    e0.grid(row=1, rowspan=1, column=4, ipadx=5, ipady=8, padx=7, pady=10)
    e1.grid(row=2, rowspan=1, column=4, ipadx=5, ipady=8, padx=7, pady=10)
    e2.grid(row=3, rowspan=1, column=4, ipadx=5, ipady=8, padx=7, pady=10)
    e3.grid(row=4, rowspan=1, column=4, ipadx=5, ipady=8, padx=7, pady=10)
    e8.grid(row=5, rowspan=1, column=4, ipadx=5, ipady=8, padx=7, pady=10)
    e4.grid(row=1, rowspan=1, column=6, ipadx=5, ipady=8, padx=7, pady=10)
    e5.grid(row=2, rowspan=1, column=6, ipadx=5, ipady=8, padx=7, pady=10)
    e6.grid(row=3, rowspan=1, column=6, ipadx=5, ipady=8, padx=7, pady=10)
    e9.grid(row=5, rowspan=1, column=6, ipadx=5, ipady=8, padx=7, pady=10)

    # inserts the current values for the variables into the entry boxes
    e0.insert(0, str(Stage0Resp))
    e1.insert(0, str(Stage1Resp))
    e2.insert(0, str(Stage2Resp))
    e3.insert(0, str(Stage3Resp))
    e8.insert(0, str(Stage4Resp))
    e4.insert(0, str(DelivTimer))
    e5.insert(0, str(LimitedHold))
    e6.insert(0, str(Blackout))
    e9.insert(0, str(fr_req))

    # configure grid size
    popup.grid_rowconfigure(0, weight=1)
    popup.grid_rowconfigure(8, weight=1)
    popup.grid_columnconfigure(0, weight=1)
    popup.grid_columnconfigure(6, weight=1)

    # run the window
    popup.mainloop()

# pulls up a report of responses, omissions, and incorrect responses from each stage
def report_end():

    # window initialization
    popup_end = tk.Tk()
    width = popup_end.winfo_screenwidth()
    height = popup_end.winfo_screenheight()
    popup_end.geometry(f'{int(width * 1)}x{int(height * 1)}+{int(width * 0.0)}+{int(height * 0.0)}')

    # label creation with all the data
    l0_1 = tk.Label(popup_end, text="Stage 0\n", font=("Bold", 24))
    l0_2 = tk.Label(popup_end, text="Responses:\n" + str(stage_0_responses), font=("Arial", 24))

    l1_1 = tk.Label(popup_end, text="Stage 1\n", font=("Bold", 24))
    l1_2 = tk.Label(popup_end, text="Responses:\n" + str(stage_1_responses), font=("Arial", 24))

    l2_1 = tk.Label(popup_end, text="Stage 2\n", font=("Bold", 24))
    l2_2 = tk.Label(popup_end, text="Responses:\n" + str(stage_2_responses), font=("Arial", 24))

    l3_1 = tk.Label(popup_end, text="Stage 3\n", font=("Bold", 24))
    l3_2 = tk.Label(popup_end, text="Responses:\n" + str(stage_3_responses), font=("Arial", 24))
    l3_3 = tk.Label(popup_end, text="Omissions:\n" + str(stage_3_omissions), font=("Arial", 24))

    l4_1 = tk.Label(popup_end, text="Stage 4\n", font=("Bold", 24))
    l4_2 = tk.Label(popup_end, text="Correct:\n" + str(stage_4_responses), font=("Arial", 24))
    l4_3 = tk.Label(popup_end, text="Incorrect:\n" + str(stage_4_incorrects), font=("Arial", 24))
    l4_4 = tk.Label(popup_end, text="Button size:\n" + str(btn_size), font=("Arial", 24))
    l4_5 = tk.Label(popup_end, text="Omissions:\n" + str(stage_4_omissions), font=("Arial", 24))

    # organizes data into a grid
    l0_1.grid(row=1, column=1, padx=10, pady=5)
    l0_2.grid(row=2, column=1, padx=10, pady=5)
    l1_1.grid(row=1, column=2, padx=10, pady=5)
    l1_2.grid(row=2, column=2, padx=10, pady=5)
    l2_1.grid(row=1, column=3, padx=10, pady=5)
    l2_2.grid(row=2, column=3, padx=10, pady=5)
    l3_1.grid(row=1, column=4, padx=10, pady=5)
    l3_2.grid(row=2, column=4, padx=10, pady=5)
    l3_3.grid(row=3, column=4, padx=10, pady=5)
    l4_1.grid(row=1, column=5, padx=10, pady=5)
    l4_2.grid(row=2, column=5, padx=10, pady=5)
    l4_3.grid(row=3, column=5, padx=10, pady=5)
    l4_4.grid(row=2, column=6, padx=10, pady=5)
    l4_5.grid(row=3, column=6, padx=10, pady=5)

    # creates and places an exit button
    b1 = tk.Button(popup_end, text='Exit', command=lambda: popup_end.destroy(), font=("bold", "20"), height=3, width=10)
    b1.grid(row=3, column=1, columnspan=4, padx=5, pady=5)

    # configures grid size
    popup_end.grid_rowconfigure(0, weight=1)
    popup_end.grid_rowconfigure(4, weight=1)
    popup_end.grid_columnconfigure(0, weight=1)
    popup_end.grid_columnconfigure(7, weight=1)

    # runs the window
    popup_end.mainloop()

# hand shape variable, changes based on keyboard inputs found below in the main pig gui initialization
def hand_shape(var):
    global hand_shape_resp
    hand_shape_resp = var

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
    gui.configure(bg="black")
    gui.configure(bg="black", cursor="none")

    # places start button
    start_button = tk.Button(gui, text="START", font=("bold", "40"), command=lambda: start())
    start_button.place(relheight=1, relwidth=1, relx=1, rely=0, anchor="ne")

    # configures inc_btn, resp_btn, and quit_btn
    # binding them to incorrect(var), press(var), and exit_program() respectively
    inc_btn = tk.Frame(gui, bg="black")
    inc_btn.bind("<Button-1>", lambda x: incorrect(1))
    resp_btn = tk.Frame(gui, bg="yellow")
    resp_btn.bind("<Button-1>", lambda x: press(1))
    quit_btn = tk.Button(gui, bg="gray10", highlightbackground="gray10", command=lambda: exit_program())
    quit_btn.place(relheight=0.007, relwidth=0.007, relx=0.007, rely=0, anchor="ne")

    # binds hand_shape(var) to the keyboard inputs
    # currently Ctrl+r or Ctrl+R
    gui.bind("<Control-r>", lambda x: hand_shape(1))
    gui.bind("<Control-R>", lambda x: hand_shape(1))

    # if overrideredirect is True, disables the X button and closing by alt+f4
    gui.overrideredirect(True)
    gui.overrideredirect(False)

    # fullscreens the application, and runs the window
    gui.attributes('-fullscreen', True)
    gui.mainloop()
    print("Disconnecting...")
print("Disconnected!")
