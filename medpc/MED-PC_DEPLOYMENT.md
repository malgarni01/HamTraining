# CoasterChase ↔ MED-PC Deployment

Implements **Section 5 (Python) and Section 4 (MED-PC)** of
`Manuals/MED-PC_Integration_Plan.pdf`.

> Directory note: the plan predates a rename. `Programs/` is now
> **`HamTraining/`** (this repo) and `Hardware/` is now **`Manuals/`**
> (the PDF manuals + plan). Manual references below use the plan's page
> numbers (printed page, not PDF viewer page).

## What was built (software, no hardware required)

| Artifact | File | Plan §|
|---|---|---|
| MSN program | `medpc/CoasterChase.mpc` | 4.1 |
| Background procedures | `medpc/BACKPROC.PAS` | 4.2 |
| Python MED-PC backend | `iointerface_api.py` → `MedPCFileDropDevice` | 5.1 |
| GUI wiring + IR log | `Shaping_full.py` (discover call, `reinforcement()`) | 5.2 |
| Windows audio | `platform_config.py` (`winsound` branch) | 5.3 |

`MockDevice` and `SerialDevice` are unchanged; the macOS/Linux dev workflow
against `MockDevice` still works. The Python side was smoke-tested with a
simulated MED-PC (normal dispense, arm-without-commit, channel-2 no-op, 5 s
timeout path, heartbeat) — all green. The MED-PC `.mpc`/`.PAS` artifacts are
authored against the verbatim DOC-301 App. C/D Pascal API and DOC-337
Example 3.5, but **cannot be compiled or run without the COM-106** (see
"Still requires the physical COM-106").

## Wire format (one `key=value` per line)

The plan says "single text line"; this implementation uses **one pair per
line** instead — a deliberate, documented deviation: Pascal `Readln` parses
one field per line robustly, vs. hand-tokenizing a space-delimited line in
`BACKPROC.PAS`. Both ends here agree on this format.

```
trigger\request.req     cmd=dispense|stop      (one slot, serialized)
                        reward_size=<int>      (dispense only)
                        seq=<int>
ack    \request.ack     seq=<int>
                        status=ok|partial|empty|stopped
                        pellets_requested=<int>
                        pellets_delivered=<int>
                        elapsed_ms=<int>

trigger\heartbeat.req   cmd=ping
                        seq=heartbeat
ack    \heartbeat.ack   seq=heartbeat
                        status=alive
                        pellets_requested=0
                        pellets_delivered=0
                        elapsed_ms=0
```

**Fixed filenames, not per-seq.** The plan originally specified zero-padded
`<seq>.req`/`<seq>.ack` filenames enumerated by `SysUtils.FindFirst`. The
COM-106's bundled Pascal refuses that FindFirst overload (another FindFirst
from the stock unit's scope shadows the SysUtils one — error: *"Got
'TRawbyteSearchRec', expected 'QWord'"*). Step 8.7 proved the fixed-name
path compiles and works, so dispense / stop share the single
`request.req`/`request.ack` slot and the seq number is carried inside the
file body (so an ack can still be cross-checked against the matching
request). Plan §9 already requires "no second .req before reading the
prior ack", so a single slot is sufficient. Heartbeats use their own
`heartbeat.req`/`heartbeat.ack` slot so they don't block while a dispense
is in flight. Atomic write = `*.tmp` then rename, both sides.

Other intentional deviations from the plan, all to reduce risk:

- **MSN variable `G` is not used.** MED-PC pre-dimensions `G` as
  `array[0..10]` (DOC-301 App. D). The plan named `G` for cumulative
  verified pellets; this uses scalar **`V`** instead. Letters used:
  `R S Q E D C P V X T` (all scalar reals).
- **Windows dev fallback.** `discover_interfaces(use_medpc=True)` falls
  back to `MockDevice` if `C:\MED-PC` is absent, so a non-COM-106 Windows
  box does not stall 5 s per dispense waiting for acks that never come.
- **`elapsed_ms`** is measured by an MSN accumulator (`S.S.3`, ticks while
  `Q=1`) rather than an unverified `BTIME` builtin; Python independently
  logs wall-clock latency anyway (plan §8 step 9).

## MED-PC side install (on the COM-106)

1. **Create IPC dirs** (local disk only, not a share):
   `C:\MED-PC\CoasterChase\trigger\`, `...\ack\`, `...\log\`.
2. **Antivirus**: exclude `C:\MED-PC\CoasterChase\` (and ideally
   `C:\MED-PC\`) from real-time scanning — plan §9, may need IT approval
   (open question #8).
3. **BACKPROC.PAS**: back up the stock `C:\MED-PC\BACKPROC.PAS`, then
   splice in `BackProc1`/`BackProc2` from `medpc/BACKPROC.PAS` (keep the
   stock file's unit header / `uses` clause — the stock examples already
   use `SysUtils`, which is all these need). See open questions #1/#2.
4. **MSN**: copy `medpc/CoasterChase.mpc` to `C:\MED-PC\MSN\`.
5. **Compile**: run TRANS → `Translation | Batch Translate!` on any
   `.mpc`. MED-PC auto-recompiles a changed `BACKPROC.PAS` (DOC-301 p.215;
   there is no separate compiler command).
6. **Hardware Config Utility**: map Box 1 → Output 1 → `^VeriFEED`,
   Box 1 → Input 1 → `^Delivered` (plan §4.3).
7. **Loader macro / shortcut**: `MPCLoader.exe` with
   `L;1;<subj>;<expt>;<grp>;CoasterChase` then `S;1` (plan §7). Leave
   MED-PC minimized.

## Python side

No code changes needed beyond what's committed. On Windows the program
auto-selects the MED-PC backend (`Shaping_full.py` sets
`USE_MEDPC = sys.platform == "win32"`). `reinforcement()` is unchanged in
behavior — each `ACTIVE`/`INACTIVE` pair → one `reward_size=1` request —
and now prints a per-trial `[REWARD] ... requested=N delivered=M status=...`
line (flags `*** CHECK FEEDER ***` on shortfall/empty hopper).

## Still requires the physical COM-106 (I could not do these)

These plan steps are hardware-gated; do them on the box, in order:

- **Plan §10 open questions** #1, #2, #6, #7, #8 (BACKPROC.PAS toolchain &
  exact unit structure, SG-224A split cable presence, v5/v6 terminal
  command set, AV policy). #3/#4/#5 are already answered in the plan.
- **Plan §8 bench tests** steps 1–3 (feeder stand-alone Operate Button;
  MED-Test manual Output 1; MED-Test manual Input 1) — do **before** any
  software, per plan.
- **Plan §8** steps 4–11: stock MSN smoke (`K;1;1`), Example 3.5,
  BKGRND smoke, manual file-drop, Python file-drop, latency (p99 < 1.5 s),
  empty-hopper (`status=empty` after ~80 s), session-long soak.

## Verify-on-box caveats

- `BACKPROC.PAS`: the stock unit's `uses` clause must provide
  `Trim`/`LowerCase`/`Pos`/`Copy`/`Length`/`Val`/`IntToStr`/`DeleteFile`/
  `RenameFile` (all standard `SysUtils`). Steps 8.6 and 8.7 confirmed
  these compile on the COM-106. The earlier dependency on
  `FindFirst`/`TSearchRec`/`faAnyFile` was removed (see "Wire format"
  above for why) — there is no longer a directory scan.
- `0.01"`/`0.05"` MSN timer granularity is well within DOC-301 examples,
  but confirm idle-poll latency meets plan §8 step 9 (p99 < 1.5 s).
- DOC-337 Example 3.5 as printed has a typesetting defect (`- S4` instead
  of `---> S4`); `CoasterChase.mpc` uses correct `--->` throughout.
- Out of scope (plan §9): the `Ctrl+R` hand-shape bug in `Shaping_full.py`
  is unrelated to hardware and untouched here.
