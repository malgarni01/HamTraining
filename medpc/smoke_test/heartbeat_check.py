"""One-shot MSN liveness probe.

Writes a heartbeat.req, waits up to 1 s for the ack, reports alive/dead.
Doesn't send any other traffic — won't STOPSAVE the MSN, doesn't dispense.
Use this between Python sessions to confirm whether you need S;1.
"""

import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from iointerface_api import MedPCFileDropDevice  # noqa: E402

device = MedPCFileDropDevice()
with device:
    device.send_heartbeat()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and device.med_pc_alive is None:
        time.sleep(0.05)
    if device.med_pc_alive is True:
        print(f"ALIVE — MSN is running, ready for dispenses.")
        sys.exit(0)
    elif device.med_pc_alive is False:
        print(f"DEAD — heartbeat returned status != alive (got {device.last_status}).")
        sys.exit(1)
    else:
        print(f"NO RESPONSE within 1s — MSN is stopped. Re-issue S;1 in MPCLoader.")
        sys.exit(2)
