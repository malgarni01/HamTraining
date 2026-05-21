"""Plan §8 step 11: session-long soak.

Drives back-to-back single-pellet dispenses for a configurable wall-clock
duration, then reports:
  * total dispenses, status counts
  * latency percentiles across the full run (medpc_ms, py_wall_ms)
  * first-half vs second-half p99 comparison (drift signal)
  * peak files-in-IPC-dirs observation (bridge backlog check)

Usage:
    python medpc\\smoke_test\\python_soak.py [duration_min] [spacing_sec]
        defaults: 30 min @ 15 s spacing

PASS criteria:
  * 100% status=ok across the run
  * medpc p99 < 1500 ms (plan §8 step 9 budget)
  * second-half p99 < 2x first-half p99 (no drift)
  * IPC dirs never accumulate more than a couple files at a time
"""

import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from iointerface_api import MedPCFileDropDevice, IOState  # noqa: E402

DURATION_MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
SPACING_S = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
STATUS_EVERY_S = 120.0
P99_BUDGET_MS = 1500
DRIFT_MAX_RATIO = 2.0

TRIGGER_DIR = r"C:\MED-PC\CoasterChase\trigger"
ACK_DIR = r"C:\MED-PC\CoasterChase\ack"


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def summarize(label, vals):
    s = sorted(v for v in vals if v is not None)
    if not s:
        return None
    print(f"  {label}: n={len(s)} min={s[0]:.0f} median={pct(s,50):.0f} "
          f"p95={pct(s,95):.0f} p99={pct(s,99):.0f} max={s[-1]:.0f}")
    return pct(s, 99)


device = MedPCFileDropDevice()
print(f"Soak: {DURATION_MIN:.0f} min @ {SPACING_S:.1f}s spacing "
      f"(~{int(DURATION_MIN * 60 / SPACING_S)} dispenses expected)")

medpc_ms = []
wall_ms = []
statuses = {}
peak_trigger_files = 0
peak_ack_files = 0

with device:
    device.send_heartbeat()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and device.med_pc_alive is None:
        time.sleep(0.05)
    if device.med_pc_alive is not True:
        print(f"FAIL: MSN not alive (heartbeat={device.med_pc_alive}). "
              "Re-issue S;1 in MPCLoader.")
        sys.exit(1)
    print(f"heartbeat alive={device.med_pc_alive}")
    print()

    start = time.monotonic()
    end_at = start + DURATION_MIN * 60
    next_status_at = start + STATUS_EVERY_S
    i = 0

    while time.monotonic() < end_at:
        i += 1
        t0 = time.perf_counter()
        device.write_output(1, IOState.ACTIVE)
        device.write_output(1, IOState.INACTIVE)
        wall = (time.perf_counter() - t0) * 1000
        wall_ms.append(wall)
        medpc_ms.append(device.last_elapsed_ms)
        statuses[device.last_status] = statuses.get(device.last_status, 0) + 1

        try:
            peak_trigger_files = max(peak_trigger_files,
                                     len(os.listdir(TRIGGER_DIR)))
            peak_ack_files = max(peak_ack_files,
                                 len(os.listdir(ACK_DIR)))
        except OSError:
            pass

        if time.monotonic() >= next_status_at:
            elapsed_min = (time.monotonic() - start) / 60
            print(f"  [{elapsed_min:.1f} min] dispenses={i} "
                  f"statuses={statuses} "
                  f"last medpc_ms={device.last_elapsed_ms} "
                  f"last wall_ms={wall:.0f} "
                  f"peak_trigger_files={peak_trigger_files} "
                  f"peak_ack_files={peak_ack_files}")
            next_status_at += STATUS_EVERY_S

        time.sleep(SPACING_S)

    print()
    print(f"=== final ({(time.monotonic() - start)/60:.1f} min, "
          f"{i} dispenses) ===")
    print(f"status counts: {statuses}")
    print(f"totals: delivered={device.pellets_delivered_total} "
          f"empty_errors={device.empty_hopper_errors}")
    print(f"peak files in trigger dir: {peak_trigger_files}")
    print(f"peak files in ack dir:     {peak_ack_files}")
    print()
    print("latency summary (ms) — full run:")
    p99_full = summarize("medpc_elapsed_ms", medpc_ms)
    summarize("py_wall_ms", wall_ms)
    print()

    half = len(medpc_ms) // 2
    if half >= 5:
        print("drift check (first half vs second half):")
        p99_h1 = summarize("medpc h1", medpc_ms[:half])
        p99_h2 = summarize("medpc h2", medpc_ms[half:])
    else:
        p99_h1 = p99_h2 = None
    print()

    ok = True
    bad_status = {k: v for k, v in statuses.items() if k != "ok"}
    if bad_status:
        print(f"FAIL: non-ok statuses observed: {bad_status}")
        ok = False
    if p99_full is None or p99_full >= P99_BUDGET_MS:
        print(f"FAIL: p99 {p99_full} ms >= {P99_BUDGET_MS} ms budget")
        ok = False
    if p99_h1 is not None and p99_h2 is not None:
        ratio = p99_h2 / p99_h1 if p99_h1 else float('inf')
        print(f"drift ratio (h2/h1) = {ratio:.2f}x "
              f"(budget: < {DRIFT_MAX_RATIO}x)")
        if ratio >= DRIFT_MAX_RATIO:
            print(f"FAIL: drift exceeds {DRIFT_MAX_RATIO}x")
            ok = False
    if peak_trigger_files > 2 or peak_ack_files > 2:
        print(f"WARN: IPC dir backlog observed "
              f"(trigger peak={peak_trigger_files}, "
              f"ack peak={peak_ack_files})")

    print()
    if ok:
        print(f"VERDICT: PASS — {i} dispenses clean, p99={p99_full:.0f} ms, "
              f"no drift")
    else:
        print("VERDICT: FAIL")
        sys.exit(2)
