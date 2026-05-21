"""Plan §8 step 10: empty-hopper / status=empty validation.

Procedure:
  1. Empty the ENV-204 hopper.
  2. Re-issue S;1 in MPCLoader (fresh MSN session).
  3. Run this script.

What it does:
  * Confirms MSN is alive via heartbeat.
  * Sends one dispense request.
  * Python's 5 s wait will time out (MSN's S7 takes 80 s on empty hopper).
  * Waits up to 110 s for the LATE ack to arrive via the watcher.
  * Confirms:
       - last_status flips to 'empty'
       - empty_hopper_errors counter == 1
       - last_empty_hopper flag is True

PASS criteria: late ack received with status=empty, counter incremented.

After running: refill the hopper before any production session.
"""

import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from iointerface_api import MedPCFileDropDevice, IOState  # noqa: E402

LATE_ACK_WAIT_S = 110   # MSN S7 timeout is 80 s, leave headroom for S8-S10-S1

device = MedPCFileDropDevice()
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
    print("Sending one dispense request to an empty hopper...")

    t0 = time.perf_counter()
    device.write_output(1, IOState.ACTIVE)
    device.write_output(1, IOState.INACTIVE)
    py_wall = time.perf_counter() - t0
    print(f"Python returned in {py_wall:.1f}s — status={device.last_status} "
          f"(expected: timeout — Python's 5s budget is shorter than MSN's 80s)")
    print()

    print(f"Waiting up to {LATE_ACK_WAIT_S}s for late status=empty ack...")
    deadline = time.monotonic() + LATE_ACK_WAIT_S
    poll = 0
    while time.monotonic() < deadline:
        if device.last_status == "empty":
            break
        time.sleep(1.0)
        poll += 1
        if poll % 10 == 0:
            elapsed = LATE_ACK_WAIT_S - (deadline - time.monotonic())
            print(f"  ...{elapsed:.0f}s elapsed, last_status={device.last_status}")
    print()

    print("=== final state ===")
    print(f"  last_status            = {device.last_status}")
    print(f"  last_empty_hopper      = {device.last_empty_hopper}")
    print(f"  last_pellets_requested = {device.last_pellets_requested}")
    print(f"  last_pellets_delivered = {device.last_pellets_delivered}")
    print(f"  last_elapsed_ms        = {device.last_elapsed_ms}")
    print(f"  empty_hopper_errors    = {device.empty_hopper_errors}")
    print(f"  pellets_delivered_total= {device.pellets_delivered_total}")
    print()

    ok = (device.last_status == "empty"
          and device.last_empty_hopper is True
          and device.empty_hopper_errors == 1)
    if ok:
        print("VERDICT: PASS — late status=empty ack received and counters updated")
    else:
        print("VERDICT: FAIL — empty-hopper path did not behave as expected")
        sys.exit(2)
