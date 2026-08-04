# Methods — Phase B: Touchscreen Shaping

**Draft for publication.** Derived from `TRAINING_PROTOCOL.md` §7, with every parameter re-read from `Shaping_full.py` at commit `1826e56` rather than transcribed from the protocol.

---

## Note to the author — read before submitting

Three things about this draft that are editorial, not stylistic:

1. **Tense.** This is written in the procedural present ("the box is presented"), the convention for protocol and methods papers describing a procedure to be followed. `TRAINING_PROTOCOL.md` records that the protocol has **not yet been run on animals**. If this text is going into a results-bearing manuscript, it must be converted to past tense *and* the subject/session counts filled in — writing past tense now would assert experiments that have not happened.

2. **Section numbering** is `2.x` as a placeholder. Renumber to the target journal's scheme.

3. **§9 is not manuscript text.** It records places where the shipped code does not match the design the protocol describes. Each one is a decision you must make *before* submission, because a methods section has to describe the software that actually ran. They are flagged inline in the body as **[D1]**–**[D6]** and collected in §9.

Placeholders needing values are marked `[SET LOCALLY]` (a design or IACUC decision) or `[VERIFY]` (a measurement to take on your rig). Do not submit with any remaining.

---

## 2.1 Apparatus

### 2.1.1 Enclosure and display

Testing is conducted in a small, plain room with minimal wall fixtures. Visual clutter measurably reduces time on task: in the source study, pigs tested in a larger room with exposed plumbing spent substantially more time exploring fixtures than working [Ao et al., 2022]. Where a small room is not available, fixtures are screened before the first session.

The touchscreen is mounted in a rack that is enclosed on both sides and positioned with its back against a wall. Two constraints on the mount are load-bearing rather than incidental, both derived from a device the source study destroyed:

- **No gap beneath the frame.** A snout-sized gap allows the pig to lever the device upward. This is how the source study's first build was broken.
- **Ballast at the base.** The source study used 2 × 9 kg sandbags. Rooting intensity scales with how much the device moves under contact; an immobile device largely extinguishes rooting, and a mobile one escalates it.

The screen is fitted with a protector and does not protrude past the rack face, since protruding corners are chewed. Screen height is set so the centre of the response area sits at comfortable snout height with the animal standing square, re-measured weekly and after any 5 kg of growth. Height changes are recorded per session, as a mid-study change is a covariate for any latency or accuracy analysis.

> `[SET LOCALLY]` Display make, model, panel size, native resolution, and touch technology (resistive vs. capacitive). The project inventory does not currently record these. Touch technology in particular must be stated: response acquisition is markedly slower on resistive panels, which require a firm press, and the source study's authors recommend shaping on capacitive and transferring to resistive for testing where the frame permits.

The program runs full-screen with the cursor hidden. All stimulus geometry below is given in **normalised screen coordinates**, where (0, 0) is the top-left corner and (1, 1) the bottom-right, so the specification is resolution-independent.

### 2.1.2 Reinforcer delivery

Pellets are delivered by a **Med Associates ENV-203-1000** dispenser, driven from a MED-PC V installation over a DIG-705 USB interface and an SG-716B connection panel. The dispenser is mounted **across the room from the screen and elevated out of the animal's reach.**

That placement is a functional requirement, not a convenience. In the source study's first build, food dropped from immediately beneath the screen, and the animals rooted at the screen hard enough to destroy the device. Relocating delivery away from the screen decoupled the location of food from the location of the response, and the replacement build survived all 35 subsequent sessions intact.

**The ENV-203-1000 has no pellet-drop sensor, and none was substituted.** Delivery is therefore *command-confirmed only*: the control software records that a dispense was commanded and cannot observe whether a pellet fell. An empty hopper, a mechanical jam, or bridged pellets are indistinguishable from normal operation in the data stream. Two compensating procedures are used, and both must be reported alongside any reinforcement counts:

- **Pellet reconciliation.** The hopper is counted (not estimated) before each session and the receptacle emptied. After the session, pellets consumed plus pellets remaining in the receptacle are reconciled against the count expected from the session record. A discrepancy exceeding 2 pellets or 5% of expected flags that session's data as suspect.
- **Pre-session prime test.** With no animal present, 5 dispenses are triggered and 5 pellets confirmed in the receptacle. This also familiarises the operator with the sound of a normal cycle, which is the only real-time delivery signal available.

Dispense latency is short enough to be ignored relative to behavioural timescales: the dispenser motor completes a revolution in ~150–250 ms, the controller allows a 300 ms settle, and bench validation of the full command path measured a 99th-percentile round trip of 390 ms over 100 requests. `[VERIFY]` on the unit in use.

### 2.1.3 Auditory stimuli

Four signals are used. All are delivered through the touchscreen computer's audio output except the dispenser-concurrent tone, which is a panel-mounted Sonalert driven from the interface.

| Signal | Event | Duration |
|---|---|---|
| 7500 Hz, long | Trial onset (all stages) | Full waveform |
| 2900 Hz, short | Correct response, concurrent with reinforcement | Full waveform |
| 290 Hz, short | Incorrect response (Stage 4 only) | Full waveform |
| Sonalert | Concurrent with each dispense command | 250 ms |
| End tone | Session termination | Full waveform |

> `[VERIFY]` Confirm the 7500 Hz trial-onset tone is audible at the animal's head height at the screen. It is the signal that re-orients an animal that has drifted off task, and it is the one to check first when an animal is exploring the room rather than working.

### 2.1.4 Control software

Stimulus presentation, response recording, and reinforcement scheduling are handled by `Shaping_full.py`, a Python/Tkinter program derived from the Vonder Haar Lab touchscreen code under CC BY-NC 4.0. Pellet requests are passed to MED-PC V through a file-drop bridge (`iointerface_api.py`); the MED-PC state-notation program pulses the dispenser operate line and returns an acknowledgement.

> `[VERIFY]` CC BY-NC 4.0 prohibits commercial use and requires attribution. Confirm compatibility with the funder's deliverable terms before any code release accompanies publication.

## 2.2 Reinforcer

Reinforcement is **one 1 g fruit-flavoured sucrose pellet** (Bio-Serv F05478 or F05711) per delivery. Pellet size is matched to the dispenser's wheel; substitution requires re-testing throughput.

Mini-marshmallows are used as a hand-delivered reinforcer for pre-training, for differential reinforcement of other behaviour (§2.7), and to release an animal that has become stuck at the feeder following a suspected missed pellet. A supply is kept at the rig for the duration of every session.

> `[SET LOCALLY]` Feeding schedule relative to session, restriction regimen if any, daily pellet cap, weight-monitoring frequency, and veterinary sign-off. **The source study reports no food-restriction protocol**, so no defensible default can be inherited from it; the values used must be stated explicitly in the manuscript and must match the approved animal-use protocol. Note that a 100-trial session at FR-1 delivers ~100 g of sucrose pellets.

## 2.3 General session structure

**Session initiation.** The operator configures the starting stage and per-stage criteria, then starts the session. A **9 s blackout** follows initiation before the first trial begins.

**Inter-trial interval.** Trials are separated by a variable interval drawn uniformly from a nine-element schedule of 3–7 s (3, 4, 4, 5, 5, 5, 6, 6, 7 s; mean 5.0 s). This sits well inside the source study's recommendation that inter-trial intervals remain under 20 s. In Stage 4 only, the interval following an incorrect response is one-third of the drawn value.

**Trial onset** is signalled by the 7500 Hz tone concurrent with presentation of the response stimulus.

**Response detection.** Responses are registered on **touch onset, not release.** This is worth stating explicitly because it determines what counts as a response under the swipe topology described in §2.7: a press-and-drag registers at the moment of contact, so a response that terminates well away from the stimulus is still scored at the stimulus.

**Response feedback.** A correct response blacks out the screen and flashes the stimulus location yellow, concurrent with the 2900 Hz tone and the reinforcement command.

**Reinforcement.** The dispenser operate line and the Sonalert are pulsed for 250 ms per pellet. The schedule is **FR-1 throughout Phase B** — every stimulus-directed response is reinforced. **[D5]**

**Response requirement.** Fixed-ratio 1 in all stages of Phase B.

**Limited hold and omission scoring differ by stage, and only two stages record omissions at all:**

| Stage | Time limit on responding | Consequence of non-response | Recorded? |
|---|---|---|---|
| 0 | 30 s (autoshape only) | Free pellet delivered, trial restarts | No |
| 1 | **None** | Trial persists indefinitely | — |
| 2 | 30 s | Trial silently restarts | **No** |
| 3 | 25 s | Trial ends, next trial begins | **Yes** |
| 4 | 25 s | Trial ends, next trial begins | Yes |

This asymmetry is a real constraint on analysis, not a presentational detail: **omission data exist only for Stages 3 and 4.** Stage 2 non-responses restart the trial without incrementing any counter, so Stage 2 trial counts understate presentations by an unrecoverable amount. Any latency or engagement measure drawn from Stages 0–2 must be qualified accordingly. **[D4]**

**Session termination.** The session ends when the criterion for the final stage is met, at which point the end tone sounds and the screen clears. A summary report of per-stage responses, omissions, and incorrect responses is displayed. Sessions may be terminated early by the operator via an on-screen control. **[D3]**

> `[SET LOCALLY]` Maximum session duration, maximum trials per session, sessions per day and minimum inter-session interval, and the early-termination rule for disengagement. The source study reports none of these. The protocol's suggested starting values — 45 min, 1 session/day (or 2 with ≥3 h separation), and termination after 10 consecutive omissions — are proposals requiring PI confirmation, not inherited parameters. Note that **no trial cap is enforced by the software** (**[D3]**), so any cap stated in the manuscript is one the operator imposes manually.

## 2.4 Shaping stages

Animals progress through four stages. Advancement **within** a session is automatic: when the cumulative response count for a stage reaches its criterion, the next stage begins immediately, without an inter-stage break or signal.

### Stage 0 — Autoshaping and free operant contact

The full screen serves as the response area and is initially black. Any touch, at any point in the trial, is reinforced.

With autoshaping enabled (the default), the screen turns yellow and the 7500 Hz tone sounds at **20 s** after trial onset; at **30 s**, a pellet is delivered non-contingently and the trial restarts after a 1 s pause. This pairs the illuminated screen with food independently of any response, so acquisition does not require the animal to emit a response first.

With autoshaping disabled, the screen remains black and the trial persists until a response occurs or the operator delivers a reinforcer manually (§2.5).

**Criterion: 20 responses.**

### Stage 1 — Illumination-contingent responding

The full screen is presented, yellow, from trial onset. Only responses made while the screen is illuminated are reinforced. There is no time limit; the stimulus persists until a response occurs.

**Criterion: 40 responses.** The source study used 15 at the equivalent stage. **[D6]**

> Note on terminology: the software's stage-selection control labels this stage "Color Discrimination." It is not a discrimination — a single stimulus is presented and no alternative is available. The label is a software defect (**[D2]**), and the term should not propagate into the manuscript, where "colour discrimination" denotes the two-choice task of the subsequent phase.

### Stage 2 — Reduced response area

A yellow band spanning the **full screen width and 40% of screen height** is presented, occupying the region between 20% and 60% of screen height. Its position is **fixed across all trials**. Non-responses time out at 30 s and restart the trial without being recorded.

**Criterion: 15 responses.**

> The source study's equivalent stage randomised its rectangle among three vertical positions, specifically in order to establish position tracking before the target was reduced in size. As implemented, position tracking is first demanded in Stage 3. **[D1]**

### Stage 3 — Position tracking

A yellow box of **40% screen width × 45% screen height** is presented, repositioned on each trial. A **25 s limited hold** applies; non-responses are scored as omissions and the trial ends.

**Criterion: 40 responses.**

Position is selected per trial from a defined set of three coordinate pairs, given as the box's top-right corner in normalised coordinates: (0.4, 0.0), (0.7, 0.3), and (1.0, 0.55) — an upper-left, centre, and lower-right arrangement along the screen diagonal.

**As implemented, the horizontal and vertical coordinates are drawn independently**, so the realised stimulus set is the full 3 × 3 factorial of those coordinates — **nine positions on a grid**, not three along a diagonal. All nine fall entirely on-screen, so sessions run without error and no collected data are invalidated. But the stage as run does not match the stage as designed, and the discrepancy must be resolved before the methods section is fixed in print. **[D1]**

### Stage 4 — Adaptive sizing with punishment (not used in this protocol)

A fifth stage exists in the software: the response box is resized adaptively (×0.85 following 2 correct responses in any 3, ÷0.85 otherwise) across five fixed positions, from a starting size of 0.7 in normalised units, and incorrect responses — touches outside the box — are punished with a 290 Hz tone and trial termination. Criterion is 50 responses.

**Stage 4 is not part of this protocol.** It exists to shape responding to very small targets, which a two-choice discrimination endpoint does not require, and it introduces a punishment contingency immediately before a choice task, where the resulting frustration is undesirable. The decision to stop at Stage 3 is recorded per session.

> **This exclusion is not currently enforced by the software.** On reaching the Stage 3 criterion, the program advances into Stage 4 automatically and without a signal; the only normal session termination is the Stage 4 criterion. Excluding Stage 4 therefore requires the operator to terminate the session manually at the moment Stage 3 completes. **[D3]**

### Summary of stage parameters

| Stage | Stimulus | Geometry (normalised) | Position | Time limit | Criterion |
|---|---|---|---|---|---|
| 0 | Full screen, black → yellow at 20 s | 1.00 × 1.00 | Fixed | 30 s → free pellet | 20 responses |
| 1 | Full screen, yellow | 1.00 × 1.00 | Fixed | None | 40 responses |
| 2 | Yellow band | 1.00 × 0.40 | Fixed (y: 0.20–0.60) | 30 s → restart | 15 responses |
| 3 | Yellow box | 0.40 × 0.45 | Variable (3 specified / 9 realised) | 25 s → omission | 40 responses |
| 4 | Yellow box, adaptive | 0.70 initial, ×0.85 | 5 positions | 25 s → omission | 50 responses |

All criteria are software defaults and are operator-adjustable at session start. **[D6]**

## 2.5 Establishing first screen contact

The transition to the first reliable screen contact is the point at which acquisition most often stalls, and it is worse on resistive panels, which require a firm press. In the source study's second cohort, no progress occurred until the program was modified to reinforce any touch immediately, and one animal required an appetitive smear on the screen before making contact.

Escalation proceeds one step per session:

1. Run Stage 0 with autoshaping enabled. The non-contingent pellet at 30 s pairs the illuminated screen with food at zero response cost.
2. If a full session produces no contact, apply **ketchup** across the screen surface as an approach motivator. Clean the protector afterwards.
3. If contact still does not occur, disable autoshaping and hand-shape approach manually, reinforcing successively closer approximations to the screen using the clicker and marshmallows. Manual reinforcement is delivered from the keyboard via **Ctrl+R**.
4. If three sessions produce no contact, stop and reassess. **Session length is not extended to compensate.**

> **Known defect affecting step 3.** The manual reinforcement binding is documented in the project README as ceasing to respond mid-session, with the cause unresolved. Hand-shaping therefore cannot currently be relied upon for a full session. Verify the binding is live immediately before any session that depends on it, and treat loss of response as a reason to end the session rather than to continue without reinforcement. **[D5]**

## 2.6 Advancement between sessions

Within a session, stages advance automatically on criterion. Between sessions:

- An animal that **completed** a stage begins the following session at the next stage.
- An animal that **did not complete** a stage repeats that stage.
- **Per-stage criteria are not adjusted to move an individual animal forward.** Failure to meet a criterion is recorded as data and escalated, not engineered around.

Failure to progress beyond the same stage across three consecutive sessions triggers review rather than continued repetition.

## 2.7 Response topology

Response *form* is recorded alongside response *rate*, because topology established during shaping carries into every subsequent task and constrains the choice-stimulus layout of the discrimination phase.

The dominant topology in the source study was a **press followed by an upward diagonal swipe**. Because responses register on touch onset (§2.3), such responses score as valid presses even when the movement terminates well above the stimulus. One animal developed pronounced swiping, with contacts landing consistently above the target.

The following are recorded per session:

| Observation | Interpretation | Response |
|---|---|---|
| Press-then-swipe, upward diagonal | Expected dominant topology | Record. If accuracy degrades, an invisible response region extending above the visible stimulus is the appropriate remedy |
| Contacts landing consistently above the stimulus | Advanced swipe topology | Record and review before the discrimination phase, as choice-stimulus layout depends on it |
| Rooting at frame or screen | Device movement, or a gap beneath the frame | Re-check ballast and gap (§2.1.1). If persistent, apply DRO: deliver a marshmallow to a distal part of the room during inter-trial intervals, reinforcing activity away from the screen |
| Working the rack corners or edges | Chewing risk | Inspect protector and confirm the screen does not protrude |

Enlarging the visible stimulus is **not** used to compensate for swiping, as it reverses the shaping the stage is intended to produce.

## 2.8 Data collection

Per session, the software records per-stage response counts; per-stage omission counts (Stages 3 and 4 only, §2.3); incorrect responses (Stage 4 only); and trial count. Session records are written to the MED-PC data directory.

A per-session sheet additionally records: starting and terminal stage; screen height and whether it changed; pre-session hopper count and prime-test result; expected versus reconciled pellet counts and the resulting discrepancy; trial numbers of any suspected missed-pellet events; session duration; topology observations; and any deviation or incident.

> `[SET LOCALLY]` Retention and transcription schedule for session sheets, and whether a session flagged by pellet reconciliation is excluded from analysis or repeated. Fix this rule **before** data collection begins — deciding it afterwards is a post-hoc exclusion criterion.

## 2.9 Implementation notes — resolve before submission

Each item is a point where the shipped software diverges from the procedure as designed. A methods section must describe the software that actually ran, so each needs either a code change or an accurate description, and §2 above needs updating to match whichever is chosen.

**[D1] Stage 3 position sampling.** The horizontal and vertical coordinates are drawn from two independent calls, yielding a 3 × 3 grid of nine positions rather than the three specified. *Options:* (a) fix the sampling to draw one coordinate pair, and describe three positions; or (b) keep the behaviour and describe nine. Option (b) arguably produces better position tracking, but the choice must be made deliberately and stated. Related: Stage 2's fixed position also departs from the source study's three-position randomisation, and §2.4 currently describes it accurately as fixed.

**[D2] Stage 1 is mislabelled in the interface** as "Color Discrimination." Cosmetic in code, but a live confusion risk at the rig and in any screenshot reproduced in a figure.

**[D3] Session termination and trial caps.**
- `MaxTrial` is defined as 100 in the source but **is never referenced anywhere in the program.** No trial cap is enforced. Any cap reported in the manuscript is operator-imposed and must be described as such.
- Stage 3 completion advances into Stage 4 automatically, so the Stage-3 stopping rule in §2.4 depends entirely on operator intervention. Either gate the transition in code or describe the manual procedure explicitly.

**[D4] Omission recording is incomplete.** Stage 2 non-responses restart the trial without incrementing any counter, and Stages 0–1 have no omission concept. If omissions are to be an outcome measure across shaping, Stage 2 needs a counter; if not, the manuscript must state that omission data are Stage-3-onward only.

**[D5] Reinforcement path caveats.**
- The fixed-ratio field in the settings interface **does not take effect** — the value is assigned to a function-local variable and discarded, so FR is fixed at 1 regardless of what is entered. Phase B is specified at FR-1, so this does not affect the procedure as described, but it must be fixed before any manipulation of response requirement is attempted.
- The manual reinforcement binding (Ctrl+R) is documented as failing mid-session with unresolved cause (§2.5).
- A "check feeder" warning in the reinforcement path can no longer trigger under the current sensorless dispenser: delivered and requested counts are now always equal by construction, so the condition is unreachable. It should not be described as a delivery check.

**[D6] Stage criteria differ from the source study.** Stage 1 uses 40 responses against the source study's 15. The remaining criteria have no published counterpart. Decide whether to align to the source study or retain the inherited defaults, and state the choice and its rationale.

---

## Deviations from the source study

For the deviations table accompanying the manuscript:

| Item | Ao et al. 2022 | This protocol | Rationale |
|---|---|---|---|
| Control hardware | 2 × Raspberry Pi, custom 28 V PCB, 433 MHz RF link | PC + MED-PC / DIG-705 → SG-716B → ENV-203-1000 | Existing rig |
| Dispenser | ENV-203-1000 | ENV-203-1000 — same | Converged |
| Pellet size | 1 g (Bio-Serv F05478/F05711) | 1 g — same | Dispenser rating |
| Delivery verification | None | None; manual reconciliation | Same limitation; their mitigations apply directly |
| Delivery remote from screen | Yes (RF link) | Yes | Same rationale — prevents screen-directed rooting |
| Stage count | 4 (0–3) + optional shrinking stage | 5 implemented; **0–3 run** | Stage 4 unnecessary for a discrimination endpoint |
| Stage 1 criterion | 15 responses | 40 | Inherited default — **[D6]** |
| Stage 2 stimulus | 1/3 screen, randomised among 3 heights | Full-width band, fixed position | As implemented — **[D1]** |
| Stage 3 positions | Not specified | 3 specified / 9 realised | As implemented — **[D1]** |
| Inter-trial interval | Not specified; "<20 s" | VI 3–7 s, mean 5.0 s | Within stated guidance |
| Limited hold | Not specified | 25 s (Stages 3–4 only) | As implemented |
| Food restriction | **Not reported** | `[SET LOCALLY]` | Not recoverable from the publication |
| Advancement criteria | **Not reported** | `[SET LOCALLY]` | No published criteria exist |

## References

1. Ao W, Grace M, Floyd CL, Vonder Haar C. A Touchscreen Device for Behavioral Testing in Pigs. *Biomedicines*. 2022;10(10):2612. doi:10.3390/biomedicines10102612
2. Vonder Haar Lab code repository. https://github.com/VonderHaarLab/ (CC BY-NC 4.0)
3. Breland K, Breland M. The Misbehavior of Organisms. *Am Psychol*. 1961;16(11):681–684.

---

*Source: `TRAINING_PROTOCOL.md` §7, with all parameters verified against `Shaping_full.py` at commit `1826e56`.*
