# Pig Training — Trainer Guide

A step-by-step guide for running a pig training session. Written for
day-to-day trainers, not programmers. You should not need to touch a
command line or a code file.

If anything looks wrong, **stop and call the lab tech**. Don't try to
debug terminal output yourself.

---

## What the system does

The training rig combines two pieces of equipment:

```
       +---------------------------+         +------------------+
       |    Touchscreen + PC       |  USB    |    MED-PC        |
       |    (this software)        | <-----> |    + ENV-204     |
       |                           |         |    pellet feeder |
       +---------------------------+         +------------------+
              (you sit here)                   (in the same rack)
```

- The **touchscreen PC** runs the training task. It shows buttons, plays
  tones, records responses.
- The **MED-PC computer** drives the pellet feeder. For tasks that
  reward with a pellet, the touchscreen PC tells MED-PC when to drop one.

---

## The three tasks

There are three trainer-runnable tasks in this system:

| Task | Pellets? | Use it for |
|---|---|---|
| **Shaping (full)** | Yes — MED-PC pellet feeder | Teaching new subjects to touch the screen, all the way through to fine motor accuracy. Five stages from autoshape → punish-incorrect. |
| **Motor Task — Accuracy** | No (touchscreen only) | Fine motor accuracy testing on subjects already trained. Saves a CSV of touch coordinates and accuracy. |
| **Motor Task — Reaction Time** | No (touchscreen only) | Reaction-time testing. Saves a CSV of stimulus-to-touch latencies. |

You pick which task in the launcher (next section). Only **Shaping**
requires MED-PC + a stocked hopper.

> **Known issue with the two Motor Task scripts:** they may stop
> partway through a session on the current Python version. If you see
> the touchscreen freeze or the program close unexpectedly, **stop and
> call the lab tech** — don't restart the session blind. Shaping is
> not affected.

---

## Before each session

### For all tasks
- [ ] Touchscreen is on and you can see the desktop.
- [ ] Subject is at the rig and able to reach the screen.
- [ ] You have ~30–60 minutes of uninterrupted time.

### For Shaping (pellet) sessions, also:
- [ ] **Hopper is full** — at least ~150 pellets in the ENV-204.
  - Open the feeder lid and top up.
- [ ] **MED-PC.exe is running** on the rack computer.
  - If the MED-PC screen is blank or asleep, wake the machine.
- [ ] **MSN is started** via MPCLoader.
  - Open MPCLoader, run the loader macro (your lab will have an icon or
    a saved shortcut), then click **S;1**.
  - The MED-PC display should show `Box 1` running with empty counters:
    `Verified-sess=0`, `Last-delivered=0`, `Empty-hopper-errs=0`.

If any of these aren't ready, **don't start the session** — fix them
first or ask the lab tech.

---

## Starting a session

### Step 1 — Open the launcher

Double-click **Start Training** on the desktop.

Two things happen:

1. A black **terminal window** opens. Leave it alone — it shows the
   reward log while the session is running.
2. A small **Pig Training** window appears on top:

```
+--------------------------------------------------+
|   Pig Training                                   |
|   Pick a task and click Start.                   |
|                                                  |
|   Task:                                          |
|   [ Shaping (MED-PC pellet)      v ]             |
|                                                  |
|   Notes:                                         |
|   +------------------------------------------+   |
|   | Uses the MED-PC pellet feeder.           |   |
|   |                                          |   |
|   | Before starting:                         |   |
|   |   - MED-PC.exe must be running           |   |
|   |   - In MPCLoader, run the loader macro   |   |
|   |     and click S;1                        |   |
|   |   - Hopper should hold at least 150      |   |
|   |     pellets                              |   |
|   +------------------------------------------+   |
|                                                  |
|        [   Start Training   ]                    |
|                                                  |
+--------------------------------------------------+
```

### Step 2 — Pick a task

Click the dropdown, choose the task you want. The notes box updates to
show what each task needs.

### Step 3 — Click "Start Training"

The launcher window closes. After a moment, a **settings window**
appears (this is the task's own configuration screen).

---

## Configuring the settings

Each task has its own settings popup. The fields are similar.

### Shaping (full)

```
+-----------------------------------------------------------------------+
|  Stage:                Responses:    Timers (seconds):                |
|  ( ) Stage 0 (FR-1)    Stage 0: 20   Reinforcer Delay: 30             |
|  ( ) Stage 1           Stage 1: 40   Limited Hold:     25             |
|  ( ) Stage 2           Stage 2: 15   Blackout:         0.15           |
|  ( ) Stage 3           Stage 3: 40   FR Requirement:   1              |
|  ( ) Stage 4           Stage 4: 50                                    |
|                                                                       |
|  Autoshape: [ Yes v ]                                                 |
|                                                                       |
|                          [   Start   ]                                |
+-----------------------------------------------------------------------+
```

| Field | What it does |
|---|---|
| **Stage** | Which stage the subject starts in. Stage 0 is autoshape (no responses required); Stage 4 punishes incorrect touches. Pick where the subject is in their training trajectory. |
| **Responses (per stage)** | How many correct touches before the task advances to the next stage. Defaults are calibrated for typical first-time subjects. |
| **Reinforcer Delay** | How long the screen waits before delivering the pellet on autoshape. |
| **Limited Hold** | How long the subject has to respond before the trial counts as an omission. |
| **Blackout** | How long the screen stays black between trials, in minutes. |
| **FR Requirement** | Fixed Ratio — how many presses count as one response. |
| **Autoshape** | If "Yes", Stage 0 automatically delivers a pellet after the Reinforcer Delay even without a press. Leave on "Yes" for new subjects. |

Click **Start** when you're done. The screen goes fullscreen black for
the Blackout duration, then the first trial begins.

### Motor Task — Accuracy / Reaction Time

These tasks have a similar settings screen with response counts and
timers. The defaults are usually fine. The Motor Tasks do not deliver
pellets — they only score the subject's touches.

---

## During the session

### What to watch

- The **touchscreen** shows the trial buttons. The subject does the work
  here — don't touch the screen during a trial.
- The **terminal window** shows one line per delivered pellet, like:

  ```
  trial started - stage 0
  [REWARD] trial 1: requested=1 delivered=1 status=ok
  ```

  Each `[REWARD]` line means one pellet was successfully delivered.
  The Motor Tasks don't print `[REWARD]` lines (no pellets).

### What you should NOT do

- Don't touch the keyboard.
- Don't click anywhere on the touchscreen unless the task is in a stage
  that explicitly waits for a hand-shape (most of the time it doesn't).
- Don't close the terminal window.
- Don't open another program on the same desktop.

### How long it takes

| Stage | Approximate duration |
|---|---|
| Stage 0 (Shaping, autoshape) | ~15 s per trial × 20 trials = ~5 min |
| Stage 1 | ~10 s per trial × 40 = ~7 min |
| Stage 2 | ~10 s per trial × 15 = ~3 min |
| Stage 3 | ~15 s per trial × 40 = ~10 min |
| Stage 4 | ~20 s per trial × 50 = ~17 min |
| Full Shaping session, all stages | ~40–50 min |

A Motor Task session is typically 15–30 min, depending on the response
count.

---

## Ending a session

### When the session ends on its own

After the last trial:

1. A **report screen** appears showing per-stage statistics:

   ```
   +-----------------------------------------------------+
   |  Stage 0   Stage 1   Stage 2   Stage 3   Stage 4    |
   |  Resp: 20  Resp: 40  Resp: 15  Resp: 40  Resp: 50   |
   |                                          Inc: 12    |
   |                                          Omit: 3    |
   |                                                     |
   |                 [   Exit   ]                        |
   +-----------------------------------------------------+
   ```

2. Click **Exit** to close the report.
3. The terminal window shows `Disconnected!` and waits.
4. Press any key to close the terminal.

### Ending early

If you need to stop a session before it completes:

1. Find the **tiny gray square** in the top-left corner of the
   touchscreen (about the size of a pencil eraser tip). Click it.
2. The report screen appears with whatever stats accumulated so far.
3. Proceed as above.

---

## Where the data is saved

| Task | Data location |
|---|---|
| Shaping (Shaping_full.py) | `C:\MED-PC\Data\` on the MED-PC computer (auto-saved when the session ends; one file per session) |
| Motor Task — Accuracy | `HamTraining\Data\*.csv` on the touchscreen PC |
| Motor Task — Reaction Time | `HamTraining\Data\*.csv` on the touchscreen PC |

Talk to the lab tech before moving or deleting these files.

---

## Quick checklist (for daily use)

The [reference card](REFERENCE_CARD.md) condenses this guide into a
single printable page. Print it and tape it to the rig.

---

## Glossary

- **MED-PC** — Med Associates Inc.'s control software for the pellet
  feeder hardware. Runs on its own computer in the rack.
- **MSN** — MED-PC State Notation. The "program" MED-PC runs. The one
  this lab uses is called *CoasterChase*.
- **MPCLoader** — The MED-PC utility used to load and start an MSN.
- **S;1** — The MPCLoader command that starts the MSN in Box 1.
- **ENV-204 / VeriFEED** — The pellet feeder hardware. Includes an IR
  sentry that confirms each pellet was actually delivered.
- **Hopper** — The pellet reservoir on the feeder. Holds a few hundred
  pellets when full.
- **Autoshape** — A training stage where the system delivers a pellet
  automatically on a schedule, even without a subject response. Used to
  bootstrap a new subject's screen-touching behavior.
- **FR (Fixed Ratio)** — The number of responses required per
  reinforcement. `FR-1` means one press per pellet.
