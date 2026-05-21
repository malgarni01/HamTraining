"""Plan §8 step 8 pre-flight: exercise MedPCFileDropDevice end-to-end.

Drops two dispense requests through the real MED-PC file-drop pipe and
prints the resulting status/counter values per request. No tkinter, no
stage logic — if this is green, Shaping_full.py is virtually guaranteed
to work.

Run from the repo root on the COM-106:
    python medpc\\smoke_test\\python_smoke.py
"""

import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from iointerface_api import IOInterface, IOState  # noqa: E402

N_DISPENSES = 2

devices = IOInterface.discover_interfaces(timeout=1, use_medpc=True)
if not devices:
    print("FAIL: no device discovered"); sys.exit(1)
device = devices[0]
print(f"Device: {device.address}")
if not device.address.startswith("MED-PC@"):
    print("FAIL: expected MedPCFileDropDevice, got fallback. Is C:\\MED-PC present?")
    sys.exit(2)

with device:
    device.configure_io({}, {})
    device.send_heartbeat()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and device.med_pc_alive is None:
        time.sleep(0.05)
    print(f"heartbeat alive={device.med_pc_alive}")
    if device.med_pc_alive is not True:
        print("FAIL: MSN not alive. Re-issue S;1 in MPCLoader and try again.")
        sys.exit(3)

    for i in range(N_DISPENSES):
        t0 = time.perf_counter()
        device.write_output(1, IOState.ACTIVE)
        device.write_output(1, IOState.INACTIVE)
        wall_ms = (time.perf_counter() - t0) * 1000
        print(f"dispense {i+1}/{N_DISPENSES}: "
              f"status={device.last_status} "
              f"req={device.last_pellets_requested} "
              f"delivered={device.last_pellets_delivered} "
              f"medpc_elapsed_ms={device.last_elapsed_ms} "
              f"py_wall_ms={wall_ms:.0f}")
        time.sleep(1.0)

    print(f"totals: delivered={device.pellets_delivered_total} "
          f"empty_errors={device.empty_hopper_errors}")
