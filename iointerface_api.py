"""iointerface_api module — Mock device for testing, optional serial for hardware."""


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


class IOInterface:
    @staticmethod
    def discover_interfaces(timeout=1, use_serial=False, serial_port=None):
        """Discover available I/O interfaces.

        Args:
            timeout: Discovery timeout in seconds.
            use_serial: If True, attempt to connect via serial port.
            serial_port: Serial port path (e.g. "/dev/tty.usbmodem14101").

        Returns:
            List of discovered device objects.
        """
        if use_serial and serial_port:
            try:
                return [SerialDevice(serial_port)]
            except Exception as e:
                print(f"Serial connection failed: {e}")
                print("Falling back to MockDevice.")
        return [MockDevice()]
