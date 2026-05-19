"""iointerface_api module.

Backends:
  * MockDevice           — off-hardware development (default fallback).
  * SerialDevice         — USB serial (Arduino/FTDI) pellet dispensers.
  * MedPCFileDropDevice  — Med Associates COM-106 / ENV-204 VeriFEED via
                           MED-PC V, using the file-drop IPC described in
                           Manuals/MED-PC_Integration_Plan.pdf Section 5.1.

The three classes expose the same surface (write_output / configure_io /
context manager / .address) so Shaping_full.py needs no structural changes.
"""

import os
import time
import threading


class IOState:
    ACTIVE = 1
    INACTIVE = 0


class OutputConfig:
    ACTIVE_LOW = 0


class MockDevice:
    def __init__(self):
        self.address = "MOCK-DEVICE"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def write_output(self, channel, state):
        pass

    def configure_io(self, inputs, outputs):
        pass


class SerialDevice:
    """USB serial device (Arduino/FTDI) for pellet dispensers on Mac/Linux."""

    def __init__(self, port):
        import serial
        self.address = port
        self._ser = serial.Serial(port, baudrate=9600, timeout=1)

    def __enter__(self):
        if not self._ser.is_open:
            self._ser.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ser.is_open:
            self._ser.close()
        return False

    def write_output(self, channel, state):
        cmd = f"OUT {channel} {state}\n"
        self._ser.write(cmd.encode())

    def configure_io(self, inputs, outputs):
        pass


# Default install locations on the Med Associates COM-106 (plan Section 3/7).
MEDPC_ROOT = r"C:\MED-PC"
MEDPC_IPC_BASE = r"C:\MED-PC\CoasterChase"


class MedPCFileDropDevice:
    """File-drop bridge to MED-PC V driving the ENV-204 VeriFEED feeder.

    Pulse semantics are preserved from reinforcement() in Shaping_full.py
    (the existing two-call ACTIVE/INACTIVE pattern is left untouched):

        write_output(1, ACTIVE)   -> arm the feeder (no hardware action yet)
        write_output(1, INACTIVE) -> commit: drop one IR-verified dispense
                                     request, then block up to `timeout`
                                     seconds for MED-PC's ack.

    Each ACTIVE/INACTIVE pair == one ``cmd=dispense reward_size=1`` request,
    so the ReinfAmt loop produces one file-drop per iteration (plan 5.1/5.2).

    Channels other than 1 (e.g. the Sonalert beeper on channel 2) are not
    mapped on the MED-PC backend and are silently ignored — the audible
    response/trial tones come from platform_config.play_sound instead.

    A background thread watches the ack directory; late acks (e.g. the ~80 s
    empty-hopper case that exceeds the 5 s wait) are still consumed so the
    cumulative counters stay correct. We never auto-retry a request — a
    silent double dispense on a lagging ack is worse than a missed one
    (plan Section 3 / Section 9).

    Wire format (one key=value per line — see MED-PC_DEPLOYMENT.md):
        request  cmd=dispense|stop|ping  reward_size=<int>  seq=<int>
        ack      seq=<int|heartbeat> status=ok|partial|empty|stopped|alive
                 pellets_requested=<int> pellets_delivered=<int>
                 elapsed_ms=<int>
    """

    def __init__(self, base_dir=MEDPC_IPC_BASE, timeout=5.0,
                 poll_interval=0.02):
        self.address = f"MED-PC@{base_dir}"
        self._base = base_dir
        self._trigger = os.path.join(base_dir, "trigger")
        self._ack = os.path.join(base_dir, "ack")
        self._logdir = os.path.join(base_dir, "log")
        for d in (self._trigger, self._ack, self._logdir):
            os.makedirs(d, exist_ok=True)

        self._timeout = timeout
        self._poll = poll_interval

        self._seq = 0
        self._lock = threading.Lock()
        self._pending = {}          # seq -> threading.Event
        self._results = {}          # seq -> parsed ack dict (handed to waiter)
        self._armed = False         # channel-1 pulse arm state

        # Counters surfaced to Shaping_full.py for per-trial IR logging.
        self.pellets_delivered_total = 0
        self.empty_hopper_errors = 0
        self.last_pellets_requested = 0
        self.last_pellets_delivered = 0
        self.last_status = None
        self.last_elapsed_ms = None
        self.last_empty_hopper = False

        # Optional liveness signal (heartbeat round-trip).
        self.med_pc_alive = None
        self.last_heartbeat_monotonic = None

        self._stop = threading.Event()
        self._watcher = None

    # -- context manager -------------------------------------------------
    def __enter__(self):
        self._stop.clear()
        self._watcher = threading.Thread(
            target=self._watch_acks, name="medpc-ack-watcher", daemon=True)
        self._watcher.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Best-effort: ask MED-PC to STOPSAVE its own per-session data file.
        try:
            self._send_request("stop", wait=False)
        except Exception as e:
            print(f"MED-PC: stop request failed: {e}")
        self._stop.set()
        if self._watcher is not None:
            self._watcher.join(timeout=2.0)
        return False

    # -- public surface (mirrors MockDevice) -----------------------------
    def configure_io(self, inputs, outputs):
        # Hardware I/O mapping is done once in MED-PC's Hardware Config
        # Utility, not at runtime — nothing to do here.
        pass

    def write_output(self, channel, state):
        if channel != 1:
            return  # beeper / other outputs are not mapped on the MED-PC path
        if state == IOState.ACTIVE:
            self._armed = True
        elif state == IOState.INACTIVE:
            if self._armed:
                self._armed = False
                self._dispense(reward_size=1)

    # -- optional health check ------------------------------------------
    def send_heartbeat(self):
        """Fire-and-forget liveness probe; med_pc_alive updates when the
        heartbeat.ack comes back (lets the caller detect a dead MED-PC
        without attempting a dispense — plan Section 3 / Section 9)."""
        try:
            self._send_request("ping", wait=False, seq_name="heartbeat")
        except Exception as e:
            print(f"MED-PC: heartbeat failed: {e}")

    # -- internals -------------------------------------------------------
    def _write_atomic(self, path, text):
        tmp = path + ".tmp"
        with open(tmp, "w", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic within the same directory

    def _send_request(self, cmd, reward_size=1, wait=True, seq_name=None):
        if seq_name is None:
            with self._lock:
                self._seq += 1
                seq = self._seq
            name = f"{seq:06d}"
            seq_field = str(seq)
        else:
            seq = seq_name
            name = seq_name
            seq_field = seq_name

        ev = None
        if wait:
            ev = threading.Event()
            with self._lock:
                self._pending[seq] = ev

        lines = [f"cmd={cmd}"]
        if cmd == "dispense":
            lines.append(f"reward_size={int(reward_size)}")
        lines.append(f"seq={seq_field}")
        self._write_atomic(os.path.join(self._trigger, name + ".req"),
                           "\n".join(lines) + "\n")
        return seq, ev

    def _dispense(self, reward_size=1):
        seq, ev = self._send_request("dispense", reward_size=reward_size,
                                     wait=True)
        got = ev.wait(self._timeout) if ev is not None else False
        with self._lock:
            self._pending.pop(seq, None)
            res = self._results.pop(seq, None)
        if res is not None:
            self._apply_result(res)
        elif not got:
            self.last_status = "timeout"
            print(f"MED-PC: WARNING no ack for dispense seq={seq:06d} within "
                  f"{self._timeout:.1f}s - proceeding without retry "
                  f"(a late ack will still be counted).")

    def _apply_result(self, res):
        status = res.get("status", "")
        try:
            req = int(res.get("pellets_requested", 0) or 0)
        except ValueError:
            req = 0
        try:
            deliv = int(res.get("pellets_delivered", 0) or 0)
        except ValueError:
            deliv = 0
        ems = res.get("elapsed_ms")
        with self._lock:
            self.last_status = status
            self.last_pellets_requested = req
            self.last_pellets_delivered = deliv
            try:
                self.last_elapsed_ms = (int(ems) if ems not in (None, "")
                                        else None)
            except ValueError:
                self.last_elapsed_ms = None
            self.last_empty_hopper = status in ("empty", "partial")
            self.pellets_delivered_total += deliv
            if status in ("empty", "partial"):
                self.empty_hopper_errors += 1

    def _watch_acks(self):
        while not self._stop.is_set():
            try:
                names = [n for n in os.listdir(self._ack)
                         if n.endswith(".ack") and not n.endswith(".tmp")]
            except OSError:
                names = []
            for n in names:
                p = os.path.join(self._ack, n)
                try:
                    with open(p, "r") as f:
                        body = f.read()
                except OSError:
                    continue
                rec = {}
                for line in body.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        rec[k.strip()] = v.strip()
                try:
                    os.remove(p)
                except OSError:
                    pass

                raw_seq = rec.get("seq", "")
                if raw_seq == "heartbeat" or n == "heartbeat.ack":
                    self.med_pc_alive = (rec.get("status") == "alive")
                    self.last_heartbeat_monotonic = time.monotonic()
                    continue
                try:
                    seq = int(raw_seq)
                except (TypeError, ValueError):
                    continue

                with self._lock:
                    ev = self._pending.pop(seq, None)
                    if ev is not None:
                        self._results[seq] = rec
                if ev is not None:
                    ev.set()             # hand off to the waiting _dispense
                else:
                    self._apply_result(rec)   # late / unwaited ack
            self._stop.wait(self._poll)


class IOInterface:
    @staticmethod
    def discover_interfaces(timeout=1, use_serial=False, serial_port=None,
                            use_medpc=False, medpc_base_dir=None):
        """Discover available I/O interfaces.

        Args:
            timeout: Discovery timeout in seconds (serial scan only).
            use_serial: If True, attempt to connect via serial port.
            serial_port: Serial port path (e.g. "/dev/tty.usbmodem14101").
            use_medpc: If True, use the MED-PC file-drop backend (COM-106).
            medpc_base_dir: Override the IPC base dir (default C:\\MED-PC\\
                CoasterChase). Passing this also bypasses the C:\\MED-PC
                presence check, which is useful for tests.

        Returns:
            List with a single discovered device object. Falls back to
            MockDevice if the requested backend is unavailable.
        """
        if use_medpc:
            base = medpc_base_dir or MEDPC_IPC_BASE
            if medpc_base_dir is not None or os.path.isdir(MEDPC_ROOT):
                try:
                    return [MedPCFileDropDevice(base_dir=base)]
                except Exception as e:
                    print(f"MED-PC backend init failed: {e}")
                    print("Falling back to MockDevice.")
            else:
                print(f"MED-PC not detected ({MEDPC_ROOT} missing) — "
                      f"using MockDevice.")
            return [MockDevice()]

        if use_serial and serial_port:
            try:
                return [SerialDevice(serial_port)]
            except Exception as e:
                print(f"Serial connection failed: {e}")
                print("Falling back to MockDevice.")
        return [MockDevice()]
