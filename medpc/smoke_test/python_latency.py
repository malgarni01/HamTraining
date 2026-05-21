"""Plan §8 step 9: dispense latency benchmark.

Drives N back-to-back single-pellet dispenses through MedPCFileDropDevice
and reports min / median / p95 / p99 / max for two latency series:

    medpc_elapsed_ms   — measured by the MSN accumulator (S.S.3)
    py_wall_ms         — Python's perf_counter() around the request

Plan budget: p99(medpc_elapsed_ms) < 1500 ms.

Run from the repo root, with MED-PC running CoasterChase (S;1):
    python medpc\\smoke_test\\python_latency.py [N]   (default N=100)

The script paces requests with INTER_REQUEST_S so the feeder + IR sentry
have time to settle between deliveries (the ENV-204 takes ~0.5-1 s per
pellet). It does NOT auto-restart MED-PC for you — if the prior Python
session sent cmd=stop, re-issue S;1 in MPCLoader before running.
"""

import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from iointerface_api import IOInterface, IOState  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
INTER_REQUEST_S = 1.0
P99_BUDGET_MS = 1500


def pct(sorted_vals, p):
    if not sorted_vals:
        return None
    # Linear interpolation between closest ranks.
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def summarize(label, vals):
    s = sorted(v for v in vals if v is not None)
    if not s:
        print(f"  {label}: (no samples)")
        return None
    print(f"  {label}: n={len(s)} "
          f"min={s[0]:.0f} "
          f"median={pct(s,50):.0f} "
          f"p95={pct(s,95):.0f} "
          f"p99={pct(s,99):.0f} "
          f"max={s[-1]:.0f}")
    return pct(s, 99)


devices = IOInterface.discover_interfaces(timeout=1, use_medpc=True)
if not devices:
    print("FAIL: no device discovered"); sys.exit(1)
device = devices[0]
if not device.address.startswith("MED-PC@"):
    print("FAIL: expected MedPCFileDropDevice, got fallback"); sys.exit(2)
print(f"Device: {device.address}")
print(f"Running {N} dispenses @ {INTER_REQUEST_S:.1f}s spacing...")

medpc_ms = []
wall_ms = []
statuses = {}

with device:
    device.configure_io({}, {})
    device.send_heartbeat()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and device.med_pc_alive is None:
        time.sleep(0.05)
    if device.med_pc_alive is not True:
        print(f"FAIL: MSN not alive (heartbeat got {device.med_pc_alive}). "
              "Re-issue S;1 in MPCLoader and try again.")
        sys.exit(5)

    for i in range(N):
        t0 = time.perf_counter()
        device.write_output(1, IOState.ACTIVE)
        device.write_output(1, IOState.INACTIVE)
        wall = (time.perf_counter() - t0) * 1000
        wall_ms.append(wall)
        medpc_ms.append(device.last_elapsed_ms)
        statuses[device.last_status] = statuses.get(device.last_status, 0) + 1
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{N} status={device.last_status} "
                  f"medpc_ms={device.last_elapsed_ms} wall_ms={wall:.0f}")
        time.sleep(INTER_REQUEST_S)

print()
print(f"status counts: {statuses}")
print(f"totals: delivered={device.pellets_delivered_total} "
      f"empty_errors={device.empty_hopper_errors}")
print()
print("latency summary (ms):")
p99_medpc = summarize("medpc_elapsed_ms", medpc_ms)
summarize("py_wall_ms", wall_ms)

print()
if p99_medpc is None:
    print("VERDICT: NO MED-PC SAMPLES — bridge likely not running")
    sys.exit(3)
if p99_medpc < P99_BUDGET_MS:
    print(f"VERDICT: PASS — p99 {p99_medpc:.0f} ms < {P99_BUDGET_MS} ms budget")
else:
    print(f"VERDICT: FAIL — p99 {p99_medpc:.0f} ms >= {P99_BUDGET_MS} ms budget")
    sys.exit(4)
