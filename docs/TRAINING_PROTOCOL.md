# Touchscreen Training Protocol — Domestic Pigs

**Target endpoint:** two-choice visual (color) discrimination
**Rig:** CoasterChase touchscreen + MED-PC / DIG-705 → **ENV-203-1000** (1 g pellets, **no delivery sensor**)
**Adapted from:** Ao W, Grace M, Floyd CL, Vonder Haar C. *A Touchscreen Device for Behavioral Testing in Pigs.* Biomedicines 2022;10:2612. doi:10.3390/biomedicines10102612 (CC BY)

| | |
|---|---|
| Protocol version | 0.2 — **draft, not yet run on animals** |
| Written | 2026-07-31 |
| Last revised | 2026-08-04 — §14.0 blocker closed; MSN blind-fire landed 2026-07-28 (§0.1, §9.2, §14.0) |
| IACUC protocol # | `[SET LOCALLY]` |
| Approved by | `[SET LOCALLY]` |

### 0.1 Revision note — feeder change (v0.1 → v0.2)

The rig moved from the **ENV-204 VeriFEED** to the **ENV-203-1000** to handle 1 g pellets. The ENV-203-1000 has **no pellet-drop sensor**, and nothing replaced it on MED-PC Input 1.

The consequence runs deeper than a part number. Under v0.1 the rig could confirm that each pellet *physically fell*; it can now only confirm that a dispense was *commanded*. **An empty hopper, a jam, or a bridged pellet now fails silently** — the software will report success either way. Every section that relied on per-trial verification has been rewritten around manual pellet reconciliation and behavioral detection (§9, §10, §11.1).

One upside: the rig now matches the published configuration exactly. Ao et al. used an ENV-203-1000 with the same 1 g Bio-Serv pellets, so their reported failure modes and mitigations apply directly rather than by analogy.

> **Blocker — resolved 2026-07-28** (commit `bbc6f87`). `medpc/CoasterChase.mpc` no longer waits on the IR sentry: state S7 now blind-fires with a 300 ms settle, so the 80 s-per-pellet stall is gone and the rig is runnable. Four documentation and naming follow-ups remain open (§14.0 items 5–8). None of them stall a session.
>
> *Why this section originally read as an open blocker:* this protocol was drafted on 2026-07-31 against a working copy that was two months behind `origin/main` and therefore did not contain the 2026-07-28 fix. Corrected 2026-08-04.

---

## 0. How this document fits with the others

| Document | Answers |
|---|---|
| **TRAINING_PROTOCOL.md** (this file) | What to do with the *pig* — pre-training, stage criteria, when to advance, when to stop |
| [TRAINER_GUIDE.md](TRAINER_GUIDE.md) | What to do with the *software* — launcher, settings popup, reading the reward log |
| [REFERENCE_CARD.md](REFERENCE_CARD.md) | One-page daily checklist to tape to the rig |

This protocol never repeats software mechanics. Wherever a step says "start the session," follow TRAINER_GUIDE.md §*Starting a session*.

**Items tagged `[SET LOCALLY]` are decisions this protocol cannot make for you** — most are IACUC or PI calls, and several are values the source paper never reported. Fill them in before the first animal runs. Items tagged `[VERIFY]` are measurements to take on your own rig.

---

## 1. Scope and limitations

This protocol takes a naive domestic (Yorkshire-type) pig from first human contact to a stable two-choice color discrimination on the touchscreen. It covers three phases:

```
  Phase A            Phase B                      Phase C
  Pre-training  -->  Touchscreen shaping     -->  Two-choice discrimination
  (5 sessions)       (Stages 0-3, 5-7 sess.)      (Phases C1-C2, 6-12+ sess.)
   handling            responding to a small        yellow vs. blue,
   leash, transport    moving yellow box            correction trials
```

**What the source paper actually supports.** Ao et al. ran 4 pigs total (2 per experiment) and describe their own behavioral data as "proof of concept that pigs can be trained on a task rather than strong baseline data." Phases A and B below are well-supported: shaping worked reliably and quickly in both cohorts. Phase C is supported only as far as the simple discrimination with correction trials; the authors' attempt to push on to a *conditional* discrimination (match-the-sample) failed and did not recover. Treat Phase C1–C2 as achievable and anything beyond it as an open research question, not a protocol step.

**Growth is a real variable here.** Yorkshire pigs in the paper went from 24–26 kg to substantially larger across ~35 sessions. Screen height, frame stability, and reach all change under you. §4.3 handles this.

---

## 2. Personnel and roles

| Role | Responsibility | Minimum training |
|---|---|---|
| **Handler** | Leads the pig, runs Phase A, present in room for all sessions | IACUC species training + 3 supervised sessions |
| **Operator** | Runs the software, watches the reward log, scores the session sheet | TRAINER_GUIDE.md + 2 supervised sessions |
| **Lab tech** | Feeder/MED-PC faults, software faults, hardware repair | Full rig + MED-PC |
| **PI / veterinary** | Stop-rule decisions, protocol deviations | — |

Handler and Operator may be the same person from Phase B onward, but **not during Phase A** — leash work needs both hands free and a second person for the hallway blockade.

---

## 3. Materials

### 3.1 Reinforcers

| Use | Item | Notes |
|---|---|---|
| Phase A (hand-delivered) | Mini-marshmallows | Also used for DRO and for feeder-fault recovery — keep a pot at the rig at all times |
| Phases B–C (dispenser) | 1 g fruit-flavored sucrose pellets | Bio-Serv F05478 / F05711 — the same pellets the paper used, and what the ENV-203-1000 is rated for. Pellet size is now matched to the dispenser wheel; no substitutions without re-testing throughput (§9.2) |
| Approach motivator | Ketchup | Wiped on the screen for a pig that will not make first contact (§7.2) |

### 3.2 Equipment checklist

- [ ] Touchscreen in weighted rack, ballast installed (§4.2)
- [ ] ENV-203-1000, hopper ≥150 pellets **counted, not eyeballed** (§9.2), mounted **out of the pig's reach and away from the screen** (§4.1)
- [ ] Pellet receptacle/cup the pig can clear completely — post-session leftovers are part of the reconciliation count (§11.1)
- [ ] Sonalert / tone output confirmed audible at pig head height
- [ ] Clicker (Phase A)
- [ ] Large dog harness + lead
- [ ] Hallway blockade — board or barrier, plus a second person
- [ ] Session sheets printed (§11.1)

---

## 4. Rig configuration

### 4.1 Dispenser placement — do not skip this

Put the pellet dispenser **across the room from the screen**, elevated out of reach. This is not a convenience; it is the single change that fixed the paper's worst failure mode. In their first build, food dropped from just under the screen, and the pigs rooted at the screen hard enough to destroy it. Moving delivery away from the screen decoupled "food appears here" from "push on this," and the second build survived all 35 sessions intact.

A wall shelf, a box on a sink, or a 3D-printed hanger all work. The requirement is only: **elevated, remote from the screen, pig cannot contact it.**

### 4.2 Frame and ballast

Rooting scales with how much the device moves. If it moves, the pig roots harder; if it is immobile, rooting largely stops.

- [ ] Rack enclosed on the sides, back against a wall
- [ ] **No gap the pig can get its snout under** — this is how the paper's first device was levered up and broken
- [ ] Ballast at the base (paper used 2 × 9 kg sandbags; add more for larger pigs)
- [ ] Screen protector fitted
- [ ] Screen does not protrude past the rack face — protruding corners get chewed

### 4.3 Screen height — recheck as they grow

Set the screen so the center of the response area is at comfortable snout height with the pig standing square. The rack is modular; moving the screen is a two-minute job.

| Checkpoint | Action |
|---|---|
| Before first session | Set height, record rack unit position on the session sheet |
| **Weekly** | Re-measure; move the screen if the pig is reaching up or ducking |
| After any 5 kg gain | Re-measure |

Record height changes — a mid-study height change is a covariate for any latency or accuracy analysis.

### 4.4 Room

Small, plain, minimal distractions. The paper's Experiment 2 ran in a larger room and the pigs spent noticeably more time exploring wall fixtures (sink, hose) instead of working. If you cannot get a small room, screen off fixtures before the first session.

---

## 5. Feeding policy — decide before you start

**The source paper does not report any food-restriction protocol.** It states only that reinforcers were marshmallows and 1 g sucrose pellets. Whether their pigs were restricted, fed *ad libitum*, or simply run before a meal is not recoverable from the publication. You must set this yourself, and it must match your approved IACUC protocol.

`[SET LOCALLY]` — record the decision here:

| Item | Value |
|---|---|
| Feeding schedule relative to session | e.g. session ≥2 h after morning feed |
| Restriction, if any | e.g. none / % of *ad lib* / target body-weight band |
| Daily pellet cap | Pellets are 1 g each; a 100-trial session at FR-1 is ~100 g of sucrose |
| Weight monitoring frequency | |
| Veterinary sign-off | |

Practical note: motivation is what makes or breaks these sessions, and the paper's pigs were visibly sensitive to reinforcement — see §10. If sessions are stalling on low motivation, the answer is a feeding-schedule conversation with your vet, **not** longer sessions or bigger response requirements.

---

## 6. Phase A — Pre-training (target: 5 sessions)

**Goal:** the pig approaches the handler willingly, wears a harness, walks on a lead, and enters the testing room calmly. No touchscreen contact in this phase.

All steps happen in the home room until step A5. Reinforce with mini-marshmallows throughout, paired with the clicker.

| Step | Procedure | Advance when |
|---|---|---|
| **A1** | Habituate to experimenters. Sit in the pen; feed treats. No handling demands. | Pig approaches the handler without prompting. Paper: ~2 days |
| **A2** | Charge the clicker. Click → immediately deliver a marshmallow. Repeat until the click alone brings the pig over. | Pig orients to the handler on the click |
| **A3** | Leash desensitization, in order, reinforcing at each step: drape the lead over the pig → wrap it around → fit the harness over the shoulders and clip behind the legs. Back off a step if the pig disengages. | Harness on, pig relaxed |
| **A4** | Walk on the lead inside the home room. | Pig follows the lead without bracing |
| **A5** | Hallway. Block it off (barrier or second person with a board). Walk back and forth. | Pig walks the hallway both directions calmly |
| **A6** | Walk to the testing room. Let the pig explore with the rig powered off. | Pig enters and settles |

**Expected variation.** The paper's older/larger female pigs took the leash on day 1; the younger males took several days. Both cohorts finished in 2–5 days of leash work on top of 2 days of habituation. If a pig is not through A4 by session 8, escalate to the PI rather than pushing.

**Speeding it up.** Multiple short sessions per day work better than one long one. `[SET LOCALLY]` — max sessions/day and minimum inter-session interval.

---

## 7. Phase B — Touchscreen shaping (target: 5–7 sessions)

**Goal:** reliable, accurate presses to a small yellow box that moves around the screen.

### 7.1 What the program actually does

Run **Shaping (full)** from the launcher. The program's five stages advance automatically once the response count for a stage is met, and you can start a session at a later stage using the *Stage* radio buttons (TRAINER_GUIDE.md §*Configuring the settings*).

These are the **as-shipped defaults in `Shaping_full.py`** — verified against the source, not copied from the paper:

| Stage | Screen | Response requirement | Default criterion | Paper equivalent |
|---|---|---|---|---|
| **0** | Whole screen. Starts black; at 20 s it turns yellow with the 7500 Hz tone; at 30 s a free pellet drops. Any touch, at any time, is reinforced. | FR-1, whole screen | **20** responses | Stage 0 (Pavlovian autoshaping + FR-1) |
| **1** | Whole screen, yellow. Only presses **while illuminated** pay. | FR-1 | **40** responses | Stage 1 (paper used 15) |
| **2** | Band across the full screen width, 40% of screen height, **fixed position**. | FR-1 | **15** responses | Stage 2 (paper's rectangle moved between 3 heights — yours does not; see §14.1) |
| **3** | Box 40% width × 45% height, repositioned each trial. 25 s limited hold; non-responses scored as omissions. | FR-1 | **40** responses | Stage 3 |
| **4** | Box shrinks/grows adaptively (×0.85 after 2 of 3 correct); 5 positions; **incorrect touches punished**. | FR-1 + punishment | **50** responses | Optional stage 4 (box-shrinking) |

Between-trial interval is a variable interval drawn from 3–7 s (mean ~5 s), plus a 9 s blackout at session start. This is comfortably inside the paper's "keep ITIs under 20 s" guidance.

### 7.2 Getting first contact — the step that stalls

This is the one place new pigs reliably get stuck, and it is worse on a resistive screen because it needs a firm press. The paper's second cohort could not get started until the program was modified to reinforce *any* touch immediately, and one pig needed ketchup on the screen.

Escalate in this order, one step per session:

1. Run Stage 0 with **Autoshape = Yes**. The free pellet every 30 s pairs the screen with food even with zero responses.
2. Still nothing after one full session → wipe **ketchup** across the screen. Clean the protector afterward.
3. Still nothing → switch to hand-shaping (`Autoshape = 0`) and shape approach manually with the clicker and marshmallows, reinforcing successively closer approximations to the screen.
4. Still nothing after 3 sessions → stop and reassess with the PI. Do not extend session length to compensate.

> If your rig has a **capacitive** screen available, the paper's authors suggest shaping first on capacitive (pigs acquire the touch faster) and swapping to resistive for testing. Only do this if the swap does not compromise frame integrity — the capacitive build is what broke.

### 7.3 Advancing through stages

The program advances stages automatically within a session. Across sessions:

- A pig that **completed** a stage last session starts at the next stage today.
- A pig that **did not complete** a stage restarts at that stage.
- Do **not** hand-edit the per-stage response counts to "help a pig through." If a stage is not being met, that is data — record it and raise it.

**Stop Phase B at the end of Stage 3.** For a two-choice discrimination endpoint you do not need Stage 4's box-shrinking; the code's own comment says it is "only necessary to shape responses to very small boxes." Skipping it also avoids the punishment contingency, which adds frustration you do not want right before introducing a choice task. Record the decision on the session sheet.

### 7.4 Watch the topology, not just the counts

How a pig presses matters more than that it pressed, because the topology carries into every later task.

| Observation | Why it matters | Action |
|---|---|---|
| **Press-then-swipe upward at a diagonal** | The paper's most common topology. Registers as a press only because buttons fire on touch, not release. | Note it. If accuracy suffers, consider an invisible response box extending above the visible button (software change — §14). |
| Responses landing consistently **above** the button | Same cause, worse case. One of the paper's pigs developed pronounced swiping. | Log it; raise with lab tech before Phase C, since choice-button layout depends on it. |
| **Rooting at the frame** | Device is moving, or there is a gap under it. | Re-check §4.2. Add ballast. Consider DRO (§10). |
| Working the **corners/edges** of the rack | Chewing risk. | Check screen does not protrude; inspect the protector. |

### 7.5 Session limits

`[SET LOCALLY]` — the paper reports no session duration or trial cap. Suggested starting values, to be confirmed by your PI:

| Parameter | Suggested | Rationale |
|---|---|---|
| Max session duration | 45 min | Matches the guide's full-shaping estimate |
| Max trials/session | 100 (`MaxTrial` default) | As shipped |
| Sessions/day | 1, or 2 with ≥3 h between | Paper tested daily; notes multiple/day speeds acquisition |
| End session early if | 10 consecutive omissions | Motivation has left the building |

---

## 8. Phase C — Two-choice color discrimination

> **Software gap — read this first.** `Shaping_full.py` implements shaping only. The Programs directory currently holds no discrimination task; `Motor_Task_Acc.py` and `Motor_Task_ReactionTime.py` are motor tasks and do not deliver pellets. **Phase C cannot be run until a discrimination program exists.** Its requirements are specified below so it can be built to this protocol. See §14.3.

**Goal:** pig reliably selects the reinforced color regardless of screen side.

### 8.1 Trial structure

```
   [ITI, VI 3-7 s]
        |
        v
   7500 Hz tone + center start box (yellow)
        |
   press ---> two choice boxes appear, left and right
              one YELLOW (correct), one BLUE (incorrect)
              side assignment PSEUDORANDOM, max 3 same-side in a row
        |
   correct --> 2900 Hz tone + 1 pellet
   incorrect --> 290 Hz tone, boxes clear, next trial
```

Requiring a press on the center start box before the choices appear does real work: it puts the pig at a known position and orientation at choice onset, which is what makes latency interpretable and side bias measurable.

### 8.2 C1 — Free-choice acquisition

Both choices available on every trial; no correction. Reinforce yellow.

- Sessions: run until the C2 trigger below
- Expect **low, near-chance accuracy** at first. The paper's pigs sat at chance in this phase — this is normal and is not a reason to intervene.
- **Trigger to move to C2:** accuracy has not exceeded `[SET LOCALLY — suggest 65%]` over 2 consecutive sessions. Do not linger here; C1's purpose is exposure, and the paper's accuracy gains came from C2.

### 8.3 C2 — Correction trials

Same as C1, except: **after an incorrect choice, immediately re-present the identical trial with the incorrect option displayed but inactive.** The pig cannot advance without selecting the correct color.

This is the step that worked. In the paper, accuracy was very low until correction trials were introduced and then "rapidly increased over 1–2 sessions."

- Score correction trials **separately**; compute accuracy from first-presentation trials only.
- **Criterion:** `[SET LOCALLY — suggest ≥80% first-presentation accuracy over 2 consecutive sessions, ≥40 trials each]`. The paper reports no criterion.

### 8.4 Side bias

The paper's pigs showed clear side biases. Check every session: compute % left choices on first presentations.

| Left-choice % | Reading | Action |
|---|---|---|
| 40–60% | Normal | None |
| 60–75% (either side) | Emerging bias | Verify pseudorandom balance; check the pig's approach path and where the handler stands |
| >75% over 2 sessions | Established bias | Run a bias-correction block: present the correct color **only on the non-preferred side** until 10 consecutive correct, then resume |

Also check for a **color** bias, not just a side bias. When the paper moved to a harder conditional discrimination, the pigs developed a strong pull toward green independent of what was correct.

### 8.5 Do not proceed to conditional discrimination

The paper's Phase 3 — a center sample color, match it among the choices — collapsed performance, and adding an FR-3 requirement did not rescue it. If conditional discrimination is a project goal, scope it as its own study with a graded training plan, not as the next session after C2.

---

## 9. Daily session flow

**Before the pig arrives**

1. Complete the [REFERENCE_CARD.md](REFERENCE_CARD.md) steps 1–4 (hopper, MED-PC, MSN started, launcher configured).
2. **Feeder prime-and-count** — see §9.2. This replaces the per-trial IR verification the old ENV-204 provided and is now the *only* delivery check you have.
3. Confirm ballast, screen height, and that nothing has been left within reach.
4. Marshmallow pot at the rig. On this feeder you will need it (§10).

**Running**

5. Handler leads the pig in; let it settle before starting the first trial.
6. Operator starts the session and scores the sheet. Do not touch the screen during trials.
7. **Operator watches the feeder, not just the log.** Each `[REWARD]` line now means *commanded*, not *delivered*. The reliable real-time signals that a pellet did not arrive are the dispenser's audible cycle and the pig's behavior — a pig that stays at the feeder area and will not re-engage has almost certainly not been fed (§10).
8. Handler stays in the room, quiet and out of the pig's approach line to the screen.

**After**

9. **Reconcile the pellet count** (§9.2). A shortfall means pellets were commanded but not delivered — flag the session's data as suspect and call the lab tech before the next run.
10. Record counts, omissions, incidents, and any hardware change on the session sheet (§11.1).
11. Clean the screen protector. Inspect frame, ballast, and cabling.
12. Note hopper level and clear any pellets left in the receptacle.

### 9.2 Pellet reconciliation — the replacement for IR verification

The ENV-203-1000 cannot tell you whether a pellet fell. Counting is the substitute, and it is a *post hoc* check: it tells you a session was compromised, not that one is being compromised. Treat it as data quality control, not as a safety interlock.

**Before the session**

1. Empty the receptacle completely.
2. Count pellets loaded into the hopper, or top up to a **counted** reference level. Record it.
3. **Prime and test:** trigger 5 dispenses with no animal present. Confirm 5 pellets in the receptacle, and listen to the cycle so you know what a normal one sounds like. Any shortfall here — fix before the pig comes in. Expect a fast cycle: the ENV-203-1000 motor completes its revolution in ~150–250 ms, the MSN allows a 300 ms settle (§14.0), and bench validation on this rig measured p99 = 390 ms end-to-end over 100 requests. The ~0.5–1 s figure quoted for the paper's hardware does **not** apply to this feeder. `[VERIFY]` — confirm your own unit lands in that range and record it.
4. Clear those 5 pellets out before starting.

**After the session**

5. Expected pellets = (reinforced trials from the session report) × `ReinfAmt`.
6. Actual = pellets consumed + any left in the receptacle, reconciled against the hopper count.
7. Record both on the session sheet.

| Discrepancy | Reading | Action |
|---|---|---|
| 0 | Clean session | None |
| 1–2 pellets | Within counting error | Note it |
| >2, or >5% of expected | Feeder underdelivered | Flag session data as suspect; inspect for jam/bridging; call lab tech before next session |
| Large shortfall late in session | Likely hopper ran empty mid-session | Flag data from the point behavior deteriorated; raise the pre-session hopper floor |

`[SET LOCALLY]` — whether a flagged session is excluded from analysis or repeated.

---

## 10. Troubleshooting — behavioral

Every row here is a failure mode the source paper actually hit.

| Problem | Cause | Action |
|---|---|---|
| **Pig will not leave the feeder area and will not re-engage** | Almost certainly a missed pellet. **On this feeder the software cannot tell you** — the log will read `delivered=1 status=ok` regardless. The pig's behavior is now your primary fault detector, exactly as it was for the paper's authors, who hit this repeatedly on the same dispenser. | Hand a marshmallow to release the pig from the feeder area. Note the trial number. If it recurs within the session, **end the session** and call the lab tech. Reconcile the pellet count (§9.2) before deciding whether the session's data is usable. |
| **Dispenser cycles audibly but no pellet arrives** | Jam, bridged pellets, or empty hopper. Silent in software since the ENV-204 was removed. | End the session, hand-feed to release the pig, clear the jam, re-run the 5-pellet prime test (§9.2) before the next session. |
| **Rooting at the screen/frame** | Device moves, or gap underneath | Add ballast; close the gap. If it persists, run **DRO**: during ITIs, periodically toss a marshmallow to another part of the room to reinforce exploring away from the screen. |
| **Pig exploring the room instead of working** | Room too large or too interesting | Screen off fixtures; confirm the 7500 Hz trial-start tone is audible — it is what re-orients the pig to the device. |
| **Accuracy drops right after a settings change** | Sudden increase in response requirement or drop in reinforcer density. The paper saw visible frustration on an FR-1 → FR-3 change. | Revert the change. Move requirements gradually, one step at a time, never mid-session. |
| **Presses register above the button** | Swipe topology (§7.4) | Log it. Software fix (taller invisible response box) — do not compensate by making the visible box bigger, which undoes shaping. |
| **Long initiation latencies, rising omissions** | Motivation, or the task got too hard | Check feeding policy (§5) and the last thing you changed. Latency to initiate was the paper's earliest indicator that a manipulation was too aggressive. |
| **Pig will not make first screen contact** | Resistive screen needs a firm press | §7.2 escalation ladder. |

---

## 11. Data and records

### 11.1 Session sheet (one per pig per session)

```
Pig ID: ________  Date: __________  Session #: ____  Operator: ________  Handler: ________

Phase / Stage started: ______    Stage reached: ______
Screen height (rack U): ______  Changed today?  Y / N

FEEDER (ENV-203-1000 — no delivery sensor; counting is the only check)
  Hopper count pre-session:  ______     5-pellet prime test passed?  Y / N
  Receptacle emptied pre-session?  Y / N
  Expected pellets (reinforced trials x ReinfAmt): ______
  Actual (consumed + left in receptacle):          ______
  Discrepancy: ______   > 2 or > 5%?  Y / N  --> flag data, call lab tech
  Missed-pellet events observed (trial #s): ____________________

Responses:  S0 ___  S1 ___  S2 ___  S3 ___  S4 ___
Omissions: ______   Incorrects: ______   Trials: ______
Session duration: ______ min

Topology notes (swiping / rooting / exploring): ______________________________
Incidents / deviations: _______________________________________________________
Phase C only —  first-presentation accuracy: ____%   left-choice %: ____%
```

### 11.2 Electronic data

| Source | Location |
|---|---|
| Shaping session data | `C:\MED-PC\Data\` (MED-PC machine) |
| Motor task CSVs | `HamTraining\Data\*.csv` (touchscreen PC) |
| Session sheets | `[SET LOCALLY]` — scan or transcribe to the project drive weekly |

Back up before any software change. Do not move or delete raw files without the lab tech.

---

## 12. Welfare and stop rules

Stop the session immediately and notify the PI/veterinary staff if:

- The pig shows distress: vocalization beyond normal, escape attempts, refusal to enter the room
- Injury, lameness, or any bleeding — including from screen or frame contact
- 10 consecutive omissions (end session; not a welfare event on its own, but log it)
- Any suspected feeder fault (§10). Since the feeder change, "suspected" is the highest confidence available in real time — a pig stuck at the feeder area is sufficient grounds to stop. Err toward stopping; an unnecessary stop costs one session, a session run on a failing feeder costs the pig's engagement with the task.
- Any hardware failure that could injure the pig — loose ballast, cracked screen, exposed cable

Pause the *program* and escalate if a pig fails to progress past the same stage for 3 consecutive sessions.

`[SET LOCALLY]` — humane endpoints, veterinary contact, after-hours escalation, and the maximum daily sucrose load per §5.

---

## 13. Deviations from the published paper

Recorded so that later analyses and any publication can state them accurately.

| Item | Ao et al. 2022 | This protocol | Why |
|---|---|---|---|
| Control hardware | 2 × Raspberry Pi, custom 28 V PCB, 433 MHz RF link | PC + MED-PC / DIG-705 → SG-716B → ENV-203-1000 | Existing CoasterChase rig |
| Dispenser | ENV-203-1000 | **ENV-203-1000** — same | Converged as of 2026-07-31 (§0.1) |
| Pellet size | 1 g (Bio-Serv F05478 / F05711) | **1 g — same** | Dispenser rated for it |
| Pellet verification | None — dispenser failures disrupted sessions | **None** — manual reconciliation (§9.2) | Same limitation as the paper; their mitigations apply directly |
| Reinforcement delivery remote from screen | Yes (RF link across the room) | Yes (§4.1) | Same rationale — prevents screen-directed rooting |
| Stage count | 4 (0–3) + optional shrinking stage | 5 (0–4) as implemented; **we run 0–3** | Stage 4 unnecessary for a discrimination endpoint |
| Stage 1 criterion | 15 responses | **40** (as shipped) | Inherited default — `[SET LOCALLY]` whether to align to the paper |
| Stage 2 box | 1/3 screen, random among 3 heights | Full-width band, **fixed position** | Code as shipped; see §14.1 |
| ITI | Not specified; "<20 s" | VI 3–7 s | Code as shipped; within the paper's guidance |
| Limited hold | Not specified; "increased to allow more time" | 25 s | Code as shipped |
| Food restriction | **Not reported** | `[SET LOCALLY]` | Not recoverable from the publication |
| Advancement criteria beyond shaping | **Not reported** | `[SET LOCALLY]` (§8.2, §8.3) | Paper reports no criteria |

**Licensing.** `Shaping_full.py` derives from Vonder Haar Lab code under **CC BY-NC 4.0** (see `License_CC-BY-NC_4.0.txt`). Attribution is required and commercial use is not permitted. Confirm compatibility with your DARPA deliverable terms before any code release — `[VERIFY]`.

---

## 14. Software readiness — resolve before data collection

**§14.0 was a hard blocker introduced by the feeder change. The blocking half shipped on 2026-07-28 and the rig is runnable again**; what remains there is naming and documentation debt that misleads the next reader but stalls nothing. The other sections were found by reading `Shaping_full.py` against this protocol; 14.1 and 14.3 block clean data collection but not pilot shaping.

### 14.0 — RESOLVED 2026-07-28: the MSN no longer waits on the removed IR sentry

**Status: the blocking half is fixed and bench-validated. Items 5–8 below are still open, and none of them stall a session.**

`medpc/CoasterChase.mpc` state S7 *used to* block on the ENV-204's sentry pulse:

```
S7,           \ wait for IR verification, or 80 s empty-hopper timeout
   #R^Delivered: ADD P; ADD V; SHOW 2, Verified-sess, V ---> S4
   80": ADD X; SHOW 4, Empty-hopper-errs, X ---> S8
```

With nothing wired to Input 1, `#R^Delivered` never fired, so every dispense request stalled in S7 for the full 80 s and then took the timeout branch — miscounting a normal dispense as an empty-hopper error. Commit `bbc6f87` replaced that with a blind-fire settle:

```
S7,           \ blind-fire settle: ENV-203-1000 has no IR sentry, so we
              \ wait long enough for the pellet motor (~150-250 ms) to
              \ finish its revolution and drop the pellet, then count it
              \ as commanded. 300 ms leaves headroom without adding
              \ noticeable latency to the training loop.
   0.3": ADD P; ADD V; SHOW 2, Commanded-sess, V ---> S4
```

Validated on the COM-106 before merge: `heartbeat_check.py` ALIVE; `python_smoke.py` 2/2 ok; `python_latency.py` 100/100 ok, p99 = 390 ms against a 1500 ms budget; `python_soak.py` 39/39 ok, drift 1.02×, 0 backlog.

**Done**

1. ✅ **`medpc/CoasterChase.mpc` S7** — replaced with a fixed settle counting *commanded* pellets. Note the shipped settle is **300 ms**, not the ~1 s this section originally proposed: the ENV-203-1000 motor is faster than the paper's hardware. §9.2 step 3 carries the corrected figure.
2. ✅ **`X`, the empty-hopper counter** — retired in place. It is documented dead in the MSN header and `SHOW 4` is relabelled "unused", so the MED-PC screen no longer shows a counter reading "0 errors" when errors are undetectable.
3. ✅ **Header comments and SHOW labels** — rewritten. The `^Delivered` equate is dropped, `P`/`V` are documented as "commanded", and the screen fields are now `Commanded-sess` and `Last-commanded`.
4. ✅ **`medpc/smoke_test/python_empty_hopper.py`** — deleted (commit `5669acd`). Its replacement is the 5-pellet prime test in §9.2, run manually.

**Still open** — naming and documentation only; safe to run an animal with these outstanding, provided §9.2 reconciliation is being done.

5. ⬜ **`iointerface_api.py`** — untouched by the fix. `pellets_delivered_total` (line 127) and `last_empty_hopper` (line 133, assigned at line 262) still carry VeriFEED names for values that can no longer observe delivery. Rename or clearly comment them; a variable called `pellets_delivered_total` that cannot observe delivery is a trap for the next person. The module docstrings at lines 6, 77 and 83 still describe the ENV-204.
6. ⬜ **`Shaping_full.py:172, 177, 192`** — comments still describe an "IR-verified dispense" and the "IR-verification payoff"; line 24 still names the ENV-204 feeder.

   **The `*** CHECK FEEDER ***` branch on line 198 has inverted rather than disappeared.** `medpc/BACKPROC.PAS:217` sets `status = 'ok'` whenever delivered ≥ requested, and blind-fire makes those two always equal — so `last_empty_hopper` is now permanently false and the warning can **never** fire. Before the fix it fired on *every* reinforcement. Either delete the branch or repoint it at something real; leaving it in place advertises a delivery check that does not exist.
7. ⬜ **`medpc/MED-PC_DEPLOYMENT.md` line 97** — Hardware Config Utility mapping still assigns Input 1 to `^Delivered`. (Line 96, Output 1 → `^VeriFEED`, is still correct and must stay — `^VeriFEED` remains the operate-line label on the ENV-203-1000.)
8. ⬜ **`medpc/smoke_test/python_latency.py:14-15`** — header still paces requests around "the feeder + IR sentry" and an ENV-204 cycle time of ~0.5–1 s.

**Verify before running an animal:** 20 consecutive dispenses at the target rate with no stalls, `Last-commanded` matching the request, and 20 pellets physically counted in the receptacle.

### 14.1 Stage 3 draws X and Y independently — `Shaping_full.py:390-391`

```python
relx=random.choice(position_list)[:1],
rely=random.choice(position_list)[1:], anchor="ne")
```

`random.choice` is called **twice**, so the X and Y coordinates come from independent draws and are not paired. `position_list` defines three positions — `(0.4, 0.0)`, `(0.7, 0.3)`, `(1, 0.55)` — but the pig sees **nine** combinations of them. All nine land on-screen, so sessions run without error and existing pilot data is not invalid, but the stage does not match its documented design and is not reproducible as described. Compare `stage_4_setup` (line 460), which does it correctly with a single index into `new_pos_list`.

Related: the function header on line 377 says stage 3 uses "5 possible positions"; the list it actually reads has 3. The comment on line 40 is the correct one.

**Fix:** draw once, index both coordinates from the same tuple, and cast to `float`.

### 14.2 Stage 2 does not move the button — `Shaping_full.py:333, 344`

The comment says "Button now moves horizontally," but placement is hardcoded (`relx=1.0, rely=0.2`). The paper's equivalent stage randomized the rectangle among three heights specifically *to shape position tracking* before shrinking the target. As shipped, the first position-tracking demand arrives in stage 3.

**Decide:** either randomize stage 2's vertical position to match the paper, or correct the comment and accept the difference — and record it in §13 either way. Low risk for a discrimination endpoint; worth fixing for fidelity.

### 14.3 The Phase C discrimination program does not exist

Nothing in `Programs/` implements two-choice discrimination. To satisfy §8 it must provide: a center start button gating choice onset; pseudorandom L/R assignment with a same-side run cap; a correction-trial mode that re-presents the failed trial with the incorrect option inactive; separate logging of first-presentation vs. correction trials; and per-session first-presentation accuracy plus left-choice percentage. Reuse `iointerface_api.py` and `reinforcement()` so the feeder path stays common — but note §14.0 item 5: those now report *commanded* pellets, so do not build a delivery check on them.

### 14.4 Minor — typo'd global, `Shaping_full.py:136`

`incorrect()` declares `global ... fr_rsp` but assigns `fr_resp` on line 150, so the assignment creates a function-local and the global partial-FR counter is never reset after an incorrect response. **Harmless at the default `fr_req = 1`** (the counter never exceeds 1), and stage 4 is the only stage that punishes — so this only matters if you raise FR above 1. Fix when convenient.

### 14.5 Known issue carried from TRAINER_GUIDE

The two Motor Task scripts may terminate mid-session on the current Python version. Shaping is unaffected. Not on the path to Phase C.

---

## 15. References

1. Ao W, Grace M, Floyd CL, Vonder Haar C. A Touchscreen Device for Behavioral Testing in Pigs. *Biomedicines*. 2022;10(10):2612. doi:10.3390/biomedicines10102612. Open access, CC BY. Supplementary videos S1–S3 show the device, response shaping, and the discrimination task — worth watching before the first session.
2. Vonder Haar Lab code repository: https://github.com/VonderHaarLab/ (CC BY-NC 4.0)
3. Breland K, Breland M. The Misbehavior of Organisms. *Am Psychol*. 1961;16(11):681–684. Cited by the paper on instinctual drift toward rooting under extended food reinforcement — relevant background for §10.
4. Local: [TRAINER_GUIDE.md](TRAINER_GUIDE.md), [REFERENCE_CARD.md](REFERENCE_CARD.md), `../MED-PC_Integration_Plan.md`, `../INVENTORY.md`

---

*Protocol v0.1 — draft. Not for animal use until §5, §12, and all `[SET LOCALLY]` fields are completed and IACUC-approved.*
