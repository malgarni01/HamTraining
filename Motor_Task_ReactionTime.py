#Software is provided and licensed under the CC-BY-NC 4.0 license: https://creativecommons.org/licenses/by-nc/4.0/. 
#This means that you can use, adapt, and share so long as you provide attribution. 
#However, commercial uses are not permitted. 
#This software was developed by Dr. Vonder Haar. Please attribute to him and provide a citation to published work or this GitHub, as appropriate. 
#For commercial use, please contact Dr. Vonder Haar for licensing options. Generally, use for small-scale research will be made free of charge.

from tkinter import *
import tkinter as tk  # for GUI
import glob, os, sys, time  # glob is for packing together file names, sys is for exiting cleanly
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
pos_list = [(0.125, 0.125), (0.125, 0.875), (0.875, 0.125), (0.875, 0.875)]  #  4 button position list
btn_size = 0.25


# Global Counters
trial = 0  # trial number counter
fr_resp = 0  # fixed ratio response
inc_resp = 0  # incorrect response counter

# Global Timers
btn_1_start_time = 0
btn_2_start_time = 0

# Global Misc
# when a button is pushed, these variables changes to whatever button is pushed (correct or incorrect,
# defined in the code as "response" or "inc")
# these are bound and initialized to buttons, found at the bottom of the program
inc = 0
response = 0
prior_correct = 0

# Data Global Counters
btn_1_responses = 0
btn_1_omissions = 0
btn_1_incorrects = 0
btn_2_responses = 0
btn_2_omissions = 0
btn_2_incorrects = 0

# Default Settings (Can be modified)
LimitedHold = 40  # Time which animal has to respond
Stage4Resp = 40
response_max = 5 # 5 second between buttons
Blackout = 0.25  # timer in min
ReinfAmt = 1
fr_req = 1  # fixed ratio requirement

#Variables for data recording
trial = 0
path = os.getcwd()
dir_path = get_data_dir()

recorded_variables = ["Subject", "Program", "Date",
                        "Time", "Session", "ITI", "FR", "LH",
                        "Trial", "RespLat", "Max Response Time", "Btn_X", "Btn_Y",
                        "CorrectResp", "IncResp", "Omission_first", "Omission_Second"]
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

def record_data(correct, incorrect, omission1, omission2):
    global recorded_variables
    now = datetime.now()
    date = now.strftime("%d/%m/%Y")
    time = now.strftime("%H:%M:%S.%f")[:-3]
    cur = perf_counter()
    resp_lat = cur - btn_1_start_time
    print(resp_lat)
    recorded_variables = [subject, "RT_MotorTask", date,
                          time, Session, sum(VI_list)/len(VI_list),
                          fr_req, LimitedHold, trial,
                          resp_lat, response_max,
                          resp_btn.winfo_rootx()/gui.winfo_screenwidth()+btn_size/2,
                          resp_btn.winfo_rooty()/gui.winfo_screenheight()+btn_size/2,
                          correct, incorrect, omission1, omission2]
    write_data()



# press function handles correct button presses
def press(var):
    global response, fr_resp, inc_resp

    fr_resp += 1
    if fr_resp >= fr_req:
        response = var


    # flashes the background yellow
    lbl = tk.Label(gui, bg="yellow", activebackground="yellow")
    pos = resp_btn.place_info()
    lbl.place(relx=pos["relx"], rely=pos["rely"], relwidth=pos["relwidth"], relheight=pos["relheight"],
              anchor=pos["anchor"])
    gui.update()
    play_sound('2900.short.wav')  # play tone for response
    lbl.place_forget()
    gui.update()

    # this block handles the fixed ratio response (need a certain number of responses per reinforce/punishment)
    record_data(1,0,0,0)
    if fr_resp >= fr_req:
        inc_btn.place_forget()
        resp_btn.place_forget()
        gui.update()
        fr_resp = 0
        inc_resp = 0
        
# incorrect function handles incorrect button presses
def incorrect(var):
    global inc,  response, inc_resp, fr_rsp
    # flash background back
    inc_lbl = tk.Label(gui, bg="black", activebackground="black")
    pos = inc_btn.place_info()
    gui.update()
    play_sound('290.short.wav')  # play tone for response
    inc_lbl.place_forget()
    gui.update()

    # this block handles the fixed ratio response (need a certain number of responses per reinforce/punishment)
    inc_resp += 1
    record_data(0, 1, 0, 0)
    if inc_resp >= fr_req:
        fr_resp = 0
        inc_resp = 0
        inc = var
        resp_btn.place_forget()
        inc_btn.place_forget()
        gui.update()
        response = 0

# function to grab xy coordinates at time of press
def check_position(pos):
    global x, y
    x = pos.x
    y = pos.y


# Basic reinforcement/punishment function
def reinforcement():
    global response, Stage4Resp
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

def btn_1_setup():
    global inc, trial, btn_1_start_time, fr_resp, inc_resp, trial, rand, response_max

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

    play_sound('7500.long.wav')  # play long tone for trial start

    # place button randomly
    rand_list = [0, 1, 2, 3]
    rand = int(random.choice(rand_list))
    inc_btn.config(bg="black")
    resp_btn.place(relheight=btn_size, relwidth=btn_size, anchor="center",
                   relx=float(pos_list[rand][0]),
                   rely=float(pos_list[rand][1]))
    resp_btn.config(bg="yellow")

    # Calculate response time limited hold
    if prior_correct == 1:
        response_max = response_max * 0.8
    elif prior_correct == 2:
        response_max = response_max / 0.8

    # print button info
    btn_1_start_time = perf_counter()
    btn_1()


def btn_1():
    def btn_1_loop():
        global response, btn_1_start_time, btn_1_responses, btn_1_omissions, inc, btn_1_incorrects,  rand, \
            btn_2_start_time, prior_correct
        btn_1_timer.cancel()

        # correct response if block, waiting for button press
        if response != 0 and inc == 0:
            btn_1_responses += 1
            resp_btn.place_forget()
            gui.update()
            response = 0
            time.sleep(0.1)

            temp_list = pos_list.copy(); del temp_list[rand]
            rand_list = [0, 1, 2]
            rand = int(random.choice(rand_list))
            resp_btn.place(relheight=btn_size, relwidth=btn_size, anchor="center",
                           relx=float(temp_list[rand][0]),
                           rely=float(temp_list[rand][1]))
            resp_btn.config(bg="yellow")

            btn_2_start_time = perf_counter()
            btn_2()

        # timeout handler
        else:
            if perf_counter() - btn_1_start_time >= LimitedHold:
                btn_1_omissions += 1
                resp_btn.place_forget()
                inc_btn.place_forget()
                gui.update()
                record_data(0, 0, 1, 0)
                prior_correct = 0
                btn_1_setup()
            else:
                btn_1()

    increment = 0.1
    btn_1_timer = Timer(increment, btn_1_loop)
    btn_1_timer.start()


def btn_2():
    def btn_2_loop():
        global response, btn_2_start_time, btn_2_responses, btn_2_omissions, inc, btn_2_incorrects, prior_correct
        btn_2_timer.cancel()

        # correct response if block, waiting for button press
        if response != 0 and inc == 0:
            btn_2_responses += 1
            resp_btn.place_forget()
            inc_btn.place_forget()
            gui.update()
            reinforcement()
            response = 0
            prior_correct = 1
            # clears screen when max trials is exceeded
            if btn_2_responses >= Stage4Resp:
                resp_btn.place_forget()
                play_sound('end_tone.wav')  # play tone for end
                gui.update()
            else:
                btn_1_setup()

        # timeout handler
        else:
            if perf_counter() - btn_2_start_time >= response_max:
                btn_2_omissions += 1
                prior_correct = 2
                resp_btn.place_forget()
                inc_btn.place_forget()
                gui.update()
                play_sound('290.short.wav')  # play tone for response
                record_data(0, 0, 0, 1)
                btn_1_setup()
            else:
                btn_2()

    increment = 0.1
    btn_2_timer = Timer(increment, btn_2_loop)
    btn_2_timer.start()


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
        btn_1_timer.cancel()
        btn_2_timer.cancel()
        # outputs_off()
        gui.destroy()
    except NameError:
        gui_destroy()


# setup function, called on program start
def start():
    start_button.destroy()
    gui.update()
    blackout_timer = Timer(Blackout * 60, btn_1_setup())
    blackout_timer.start()


# settings menu called on program start allows changing of max trials per stage, reinforcer delay,
# limited hold, and blackout timers
def settings():
    # gets current values for all variables listed below
    def update_vals():
        global LimitedHold, Stage4Resp, Blackout, subject, \
            Session, response_max
        Stage4Resp = float(e0.get())
        LimitedHold = float(e1.get())
        response_max = float(e2.get())
        Blackout = float(e3.get())
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
    l1 = tk.Label(popup, text=("Start Limited\nHold (s):\n" + str(LimitedHold)), font=24)
    l2 = tk.Label(popup, text=("Response Limited\nHold (s):" + str(response_max)), font=24)
    l3 = tk.Label(popup, text=("Blackout (s):\n" + str(Blackout)), font=24)
    # creates entry boxes
    e0 = tk.Entry(popup, width=3, font=24);     e1 = tk.Entry(popup, width=3, font=24)
    e2 = tk.Entry(popup, width=3, font=24);     e3 = tk.Entry(popup, width=3, font=24)
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

    e0.grid(row=1, column=5,  rowspan=2, ipadx=5, ipady=8, padx=7, pady=10);     e1.grid(row=3, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10)
    e2.grid(row=5, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10);     e3.grid(row=7, column=5, rowspan=2, ipadx=5, ipady=8, padx=7, pady=10)
    b1.grid(row=13, rowspan=2, column=2, columnspan=1)


    # inserts the current values for the variables into the entry boxes
    e0.insert(0, str(Stage4Resp));      e1.insert(0, str(LimitedHold))
    e2.insert(0, str(response_max));        e3.insert(0, str(Blackout))
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
    l4_2 = tk.Label(popup_end, text="Correct:\n" + str(btn_2_responses), font=("Arial", 24))
    l4_3 = tk.Label(popup_end, text="Trial Omission:\n" + str(btn_1_omissions), font=("Arial", 24))
    l4_4 = tk.Label(popup_end, text="Response Omission:\n" + str(btn_2_omissions), font=("Arial", 24))
    l4_5 = tk.Label(popup_end, text="Current Delay:\n" + str(response_max), font=("Arial", 24))

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
