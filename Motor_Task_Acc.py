#Software is provided and licensed under the CC-BY-NC 4.0 license: https://creativecommons.org/licenses/by-nc/4.0/. 
#This means that you can use, adapt, and share so long as you provide attribution. 
#However, commercial uses are not permitted. 
#This software was developed by Dr. Vonder Haar. Please attribute to him and provide a citation to published work or this GitHub, as appropriate. 
#For commercial use, please contact Dr. Vonder Haar for licensing options. Generally, use for small-scale research will be made free of charge.


from tkinter import *
import tkinter as tk  # for GUI
import glob, os, random, sys, time  # glob is for packing together file names, sys is for exiting cleanly
from threading import Timer  # for periodic loops
import random  # for random number selection
from time import perf_counter  # for calculating latencies/timers
import time
import os
from csv import *  # for importing settings through settings.csv
import csv
from datetime import datetime

from iointerface_api import *
from platform_config import play_sound, ensure_sound_files, get_data_dir

ensure_sound_files()

scan_time = 1
print(f"scanning for {scan_time} seconds, please wait...")

devices = IOInterface.discover_interfaces(timeout=scan_time)
for device in devices:
    print(f"Found I/O Interface: {device.address}")

if len(devices) == 0:
    print("Failed to find device!")
    exit()

# GLOBAL CONSTANTS
VI_list = [3, 4, 4, 5, 5, 5, 6, 6, 7]  # list of variable interval schedule times to randomly select from
new_pos_list = [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)]  # stage 4 button position list

# Global Counters
trial = 0  # trial number counter
size_adj_trials = 0  # size adjustment trial counter
fr_resp = 0  # fixed ratio response
inc_resp = 0  # incorrect response counter

# Global Timers
stage_4_start_time = 0

# Global Misc
# when a button is pushed, these variables changes to whatever button is pushed (correct or incorrect,
# defined in the code as "response" or "inc")
# these are bound and initialized to buttons, found at the bottom of the program
inc = 0
response = 0

# Misc
size_adj_correct = [0,]  # size adjustment array for correct responses in stage 4

# Data Global Counters
stage_4_responses = 0
stage_4_omissions = 0
stage_4_incorrects = 0

# Default Settings (Can be modified)
LimitedHold = 40  # Time which animal has to respond
Stage4Resp = 40
Blackout = 0.25  # timer in min
ReinfAmt = 1
ExtraPunisher = 10  #extra time out if too many incorrects in a row. In sec
btn_size = 0.6  # button size constant
fr_req = 3  # fixed ratio requirement


#Variables for data recording
trial = 0
path = os.getcwd()
dir_path = get_data_dir()

recorded_variables = ["Subject", "Program", "Date",
                        "Time", "Session", "ITI", "FR", "LH",
                        "Trial", "RespLat", "ButtonSize",
                        "CorrectResp", "IncResp", "Omission"]
#Data dictionary
    #ITI = intertrial interval between presentations
    #FR = fixed ratio requirement
    #LH = limited hold to respond during
    #Trial = trial number
    #Response latency = time to respond for either stage
    #Button Size is current size of button
    #Correct and Incorrect responses on whatever FR
    #Correct: 1/0 flag for correct or incorrect total chain
    #Omission: Flag for omitted responses


def write_data():
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    with open(os.path.join(dir_path, str(filename) + ".csv"), "a") as file:
        global recorded_variables
        writer = csv.writer(file)
        writer.writerow(recorded_variables)

def record_data(correct, incorrect, omission):
    global recorded_variables
    now = datetime.now()
    date = now.strftime("%d/%m/%Y")
    time = now.strftime("%H:%M:%S.%f")[:-3]
    cur = perf_counter()
    resp_lat = cur - stage_4_start_time
    print(resp_lat)
    recorded_variables = [subject, "FineMotorTask", date,
                          time, Session, sum(VI_list)/len(VI_list),
                          fr_req, LimitedHold, trial,
                          resp_lat, btn_size,
                          correct, incorrect, omission]
    write_data()



# press function handles correct button presses
def press(var):
    global response, size_adj_correct, fr_resp, inc_resp

    # flashes the background yellow
    lbl = tk.Label(gui, bg="yellow", activebackground="yellow")
    pos = resp_btn.place_info()
    inc_lbl = tk.Label(bg="black", activebackground="black")
    inc_lbl.place(relheight=1.1, relwidth=1.1, relx=1.05, rely=-0.05, anchor="ne")
    lbl.place(relx=pos["relx"], rely=pos["rely"], relwidth=pos["relwidth"], relheight=pos["relheight"],
              anchor=pos["anchor"])
    gui.update()
    play_sound('2900.short.wav')  # play tone for response
    lbl.place_forget()
    inc_lbl.place_forget()
    gui.update()

    # this block handles the fixed ratio response (need a certain number of responses per reinforce/punishment)
    fr_resp += 1
    record_data(1,0,0)
    if fr_resp >= fr_req:
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
    global inc, size_adj_correct, response, inc_resp, fr_rsp
    # flash background back
    inc_lbl = tk.Label(gui, bg="black", activebackground="black")
    pos = inc_btn.place_info()
    inc_lbl.place(relx=pos["relx"], rely=pos["rely"], relwidth=pos["relwidth"], relheight=pos["relheight"],
                  anchor=pos["anchor"])
    gui.update()
    play_sound('290.short.wav')  # play tone for response
    inc_lbl.place_forget()
    gui.update()

    # this block handles the fixed ratio response (need a certain number of responses per reinforce/punishment)
    inc_resp += 1
    record_data(0, 1, 0)
    if inc_resp >= fr_req:
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
        # the send.py file should be placed in the location specified below in the commands
        # or the path should be changed accordingly
        # this also follows for the commands using aplay to play a tone
        device.write_output(1, IOState.INACTIVE)  # Stop asserting pellet dispenser
        device.write_output(2, IOState.INACTIVE)  # Turn of beeper

    while True:
        device.write_output(1, IOState.ACTIVE)  # Turn on pellet dispenser
        device.write_output(2, IOState.ACTIVE)  # Turn on beeper
        pellet_timer = Timer(0.25, reinf_off)  # timer 0.25s delay for pellet cycle
        pellet_timer.start()
        pellet_timer.join()
        reinforcers += 1  # breaks from loop when reinforcement limit is reached
        if reinforcers >= ReinfAmt:
            break


# START MAIN PROGRAM LOOP

# ---------------------------------------------------------------------------
# Stage 4: Button begins moving around the screen, changing size based on number of correct responses
# now punishes incorrect responses
# This stage is only necessary to shape responses to very small boxes. Consider deleting/disabling if this is not necessary for experiment

def stage_4_setup():
    global inc, trial, stage_4_start_time, btn_size, size_adj_trials, fr_resp, inc_resp, trial

    # inc functions the same as the response variable
    # when an incorrect response is given, pause for a random time divided by 3
    # otherwise, pause full length
    if inc != 0:
        inc = 0
        time.sleep(random.choice(VI_list))
    else:
        time.sleep(random.choice(VI_list))
    fr_resp = 0
    inc_resp = 0
    trial += 1

    # every three trials; check corrects and adjust button size
    if size_adj_trials >= 1:
        size_adj_trials = 0
        if sum(size_adj_correct) >= 1:
            btn_size = btn_size * 0.85
        else:
            btn_size = btn_size / .85
            time.sleep(ExtraPunisher)

    play_sound('7500.long.wav')  # play long tone for trial start


    # place button randomly
    rand_list = [0, 1, 2, 3, 4]
    rand = int(random.choice(rand_list))
    inc_btn.place(relheight=1.1, relwidth=1.1, relx=1.05, rely=-0.05, anchor="ne")
    inc_btn.config(bg="black")

    if rand != 4:
        if btn_size > 0.50:
            pos_adj = btn_size-0.5
            x_pos_adj = pos_adj;    y_pos_adj = pos_adj
            if new_pos_list[rand][0]>0.5:
                x_pos_adj = pos_adj*-1
            if new_pos_list[rand][1]>0.5:
                y_pos_adj = pos_adj * -1
            resp_btn.place(relheight=btn_size, relwidth=btn_size, anchor="center",
                           relx=float(new_pos_list[rand][0]) + x_pos_adj/2,
                           rely=float(new_pos_list[rand][1]) + y_pos_adj/2)
        else:
            resp_btn.place(relheight=btn_size, relwidth=btn_size, anchor="center",
                       relx=float(new_pos_list[rand][0]),
                       rely=float(new_pos_list[rand][1]))
    else:
        resp_btn.place(relheight=btn_size, relwidth=btn_size, anchor="center",
                       relx=float(new_pos_list[rand][0]),
                       rely=float(new_pos_list[rand][1]))

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
        stage_4_timer.cancel()

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
                play_sound('end_tone.wav')  # play tone for end
                gui.update()
            else:
                stage_4_setup()

        # timeout handler
        else:
            if perf_counter() - stage_4_start_time >= LimitedHold:
                stage_4_omissions += 1
                resp_btn.place_forget()
                inc_btn.place_forget()
                gui.update()
                record_data(0, 0, 1)
                stage_4_setup()
            else:
                stage_4()

    increment = 0.1
    stage_4_timer = Timer(increment, stage_4_loop)
    stage_4_timer.start()


# exit program function, clears gui elements, calls report function
def exit_program():
    if resp_btn.winfo_exists():
        end_program()
    report()


# report function, destroys gui, calls report_end function
def report():
    gui.destroy()
    report_end()


# gui clear function called by exit_program
def end_program():
    global stage_timer

    def gui_destroy():
        resp_btn.destroy()
        inc_btn.destroy()

    try:
        stage_timer.cancel()
        # outputs_off()
        gui.destroy()
    except NameError:
        gui_destroy()


# setup function, called on program start
def start():
    start_button.destroy()
    gui.update()
    blackout_timer = Timer(Blackout * 60, stage_4_setup())
    blackout_timer.start()


# settings menu called on program start allows changing of max trials per stage, reinforcer delay,
# limited hold, and blackout timers
def settings():
    # gets current values for all variables listed below
    def update_vals():
        global LimitedHold, Stage4Resp, Blackout, fr_req, subject, \
            Session, ExtraPunisher, btn_size
        Stage4Resp = float(e0.get())
        LimitedHold = float(e1.get())
        Blackout = float(e2.get())
        fr_req = float(e3.get())
        ExtraPunisher = float(e4.get())
        btn_size = float(e5.get())
        Session = float(e7.get())
        subject = Subject.get()

    # sets up settings menu
    def setup():
        global filename
        update_vals()
        if Subject == 0 or Session == 0:
            play_sound('290.short.wav')  # play tone for incorrect
            print("SESSION or SUBJECT is not selected")
        else:
            filename = "Sbj" + str(int(subject))
            popup.destroy()

    # settings gui popup initialization
    popup = tk.Tk();    width = popup.winfo_screenwidth();      height = popup.winfo_screenheight()
    popup.geometry(f'{int(width * 0.5)}x{int(height * 0.7)}+{int(width * 0.25)}+{int(height * 0.15)}')

     # creates settings labels
    l0 = tk.Label(popup, text=("Max Reinforcers:\n" + str(Stage4Resp)), font=24)
    l1 = tk.Label(popup, text=("Limited\nHold (s):\n" + str(LimitedHold)), font=24)
    l2 = tk.Label(popup, text=("Blackout (s):\n" + str(Blackout)), font=24)
    l3 = tk.Label(popup, text=("FR Requirement:\n" + str(fr_req)), font=24)
    l4 = tk.Label(popup, text=("Extra Time out (s):\n" + str(ExtraPunisher)), font=24)
    l5 = tk.Label(popup, text=("Button size (% screen):\n" + str(btn_size)), font=24)
    # creates entry boxes
    e0 = tk.Entry(popup, width=3, font=24);     e1 = tk.Entry(popup, width=3, font=24)
    e2 = tk.Entry(popup, width=3, font=24);     e3 = tk.Entry(popup, width=3, font=24)
    e4 = tk.Entry(popup, width=3, font=24);     e5 = tk.Entry(popup, width=3, font=24)
    # creates start button
    b1 = tk.Button(popup, text="Start", command=lambda: setup(), font=("bold", "14"), height=3, width=12)

    # session and subject labels
    Subject = IntVar()
    l6 = tk.Label(popup, text=("Subject"), font=24)
    rd0 = Radiobutton(popup, text="258", variable=Subject, value=258)
    rd1 = Radiobutton(popup, text="365", variable=Subject, value=365)
    l7 = tk.Label(popup, text=("Session"), font=24)
    e7 = tk.Entry(popup, width=3, font=24)

    # organizing of all labels and entry boxes into a grid
        #Subject/session in left corner
    l6.grid(row=1, column=0,  padx=2, pady=25)
    rd0.grid(row=2, column=0)
    rd1.grid(row=3, column=0 )
    l7.grid(row=1, column=1)
    e7.grid(row=2, column=1, ipadx=5, ipady=8, padx=7, pady=10)
        #rest in right side
    l0.grid(row=1, column=4, rowspan=2, padx=2, pady=25);       l1.grid(row=3, column=4, rowspan=2, padx=2, pady=25)
    l2.grid(row=5, column=4, rowspan=2, padx=2, pady=25);       l3.grid(row=7, column=4, rowspan=2, padx=2, pady=25)
    l4.grid(row=9, column=4, rowspan=2, padx=2, pady=25);       l5.grid(row=11, column=4, rowspan=2, padx=2, pady=25)

    e0.grid(row=1, column=5,  rowspan=2, ipadx=5, ipady=8, padx=7, pady=10);     e1.grid(row=3, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10)
    e2.grid(row=5, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10);     e3.grid(row=7, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10)
    e4.grid(row=9, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10);     e5.grid(row=11, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10)
    b1.grid(row=13, rowspan=2, column=2, columnspan=1)


    # inserts the current values for the variables into the entry boxes
    e0.insert(0, str(Stage4Resp));      e1.insert(0, str(LimitedHold))
    e2.insert(0, str(Blackout));        e3.insert(0, str(fr_req))
    e4.insert(0, str(ExtraPunisher));   e5.insert(0, str(btn_size))
    e7.insert(0, 0)

    # configure grid size
    popup.grid_rowconfigure(0, weight=1);           popup.grid_rowconfigure(11, weight=1)
    popup.grid_columnconfigure(0, weight=1);        popup.grid_columnconfigure(5, weight=1)

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
    l4_2 = tk.Label(popup_end, text="Correct:\n" + str(stage_4_responses), font=("Arial", 24))
    l4_3 = tk.Label(popup_end, text="Incorrect:\n" + str(stage_4_incorrects), font=("Arial", 24))
    l4_4 = tk.Label(popup_end, text="Button size:\n" + str(btn_size), font=("Arial", 24))
    l4_5 = tk.Label(popup_end, text="Omissions:\n" + str(stage_4_omissions), font=("Arial", 24))

    # organizes data into a grid
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

    # if overrideredirect is True, disables the X button and closing by alt+f4
    gui.overrideredirect(True)
    gui.overrideredirect(False)

    # fullscreens the application, and runs the window
    gui.attributes('-fullscreen', True)
    gui.mainloop()
    print("Disconnecting...")
print("Disconnected!")
