"""Cross-platform configuration for Pig Behavioral Testing Suite.

Centralizes OS-specific logic (audio, paths) so program files stay clean.
Supports macOS, Linux (Raspberry Pi), and Windows (Med Associates COM-106).
"""

import os
import sys
import platform
import subprocess
import struct
import wave
import math

IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_WINDOWS = sys.platform == "win32"

# Resolve paths relative to this script's directory
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(_SCRIPT_DIR, "sounds")
DATA_DIR = os.path.join(_SCRIPT_DIR, "Data")


def get_data_dir():
    """Return the data directory path, creating it if needed."""
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    return DATA_DIR


def play_sound(filename):
    """Play a .wav file non-blocking. Uses afplay on Mac, aplay on Linux."""
    filepath = os.path.join(SOUNDS_DIR, filename)
    if not os.path.isfile(filepath):
        print(f"Warning: sound file not found: {filepath}")
        return
    try:
        if IS_MACOS:
            subprocess.Popen(["afplay", filepath],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif IS_WINDOWS:
            import winsound
            # SND_ASYNC -> non-blocking, matches the afplay/aplay behavior.
            winsound.PlaySound(filepath,
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            subprocess.Popen(["aplay", filepath],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"Warning: audio player not found for {filename}")
    except RuntimeError as e:
        print(f"Warning: Windows sound playback failed for {filename}: {e}")


def _generate_tone(filepath, frequency, duration, sample_rate=44100, amplitude=0.8):
    """Generate a sine wave .wav file using only stdlib modules."""
    n_samples = int(sample_rate * duration)
    with wave.open(filepath, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        for i in range(n_samples):
            sample = amplitude * math.sin(2.0 * math.pi * frequency * i / sample_rate)
            wav.writeframes(struct.pack("<h", int(sample * 32767)))


def ensure_sound_files():
    """Generate placeholder .wav tones if sound files don't exist yet."""
    if not os.path.isdir(SOUNDS_DIR):
        os.makedirs(SOUNDS_DIR)

    tones = {
        "2900.short.wav": (2900, 0.15),   # correct response
        "290.short.wav":  (290, 0.15),     # incorrect response
        "7500.long.wav":  (7500, 0.5),     # trial start
        "end_tone.wav":   (1000, 1.0),     # end session
    }

    for filename, (freq, dur) in tones.items():
        filepath = os.path.join(SOUNDS_DIR, filename)
        if not os.path.isfile(filepath):
            print(f"Generating placeholder tone: {filename}")
            _generate_tone(filepath, freq, dur)
