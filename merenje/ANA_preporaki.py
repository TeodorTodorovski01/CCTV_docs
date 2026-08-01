#!/usr/bin/env python3
"""
Lightweight system data logger for Raspberry Pi 4B.

Logs (every INTERVAL_SEC seconds, for DURATION_SEC total):
  - timestamp
  - CPU usage total (%)
  - CPU usage per core (%)
  - RAM usage (% and MB used)
  - CPU / SoC temperature (deg C)
  - Network throughput: download and upload (Mbit/s)
  - Approximate power usage (Watts) -- Pi 4B has no built-in power sensor,
    so this is a rough estimate based on CPU load + clock speed. Treat it
    as a ballpark figure, not a measurement.

Test metadata (number of cameras, test type, etc.) is fixed in the CONFIG
section below and written as commented header lines at the top of the
output CSV, before the actual data table starts.

Dependencies:
  pip3 install psutil
  (vcgencmd is already installed on Raspberry Pi OS)

Usage:
  python3 pi_datalogger.py
  (edit CONFIG below before running)
"""

import csv
import subprocess
import time
from datetime import datetime

import psutil

# ------------------------------------------------------------------
# CONFIG - edit these before each test run
# ------------------------------------------------------------------
NUM_CAMERAS   = 2                 # number of cameras active during this test
TEST_TYPE     = "idle_baseline"   # e.g. "idle_baseline", "recording_2cam", "stress_test"
NOTES         = "30fps na site 3 mesta 720p"        # free text, anything else worth remembering

INTERVAL_SEC  = 1                 # seconds between samples
DURATION_SEC  = 1200                # total logging duration in seconds (0 = run forever)

OUTPUT_FILE   = "1080p_15_1_udp{}.csv".format(datetime.now().strftime("%Y%m%d_%H%M%S"))

# Rough power model for Pi 4B (Watts). Calibrated loosely against
# commonly published measurements: ~2.7W idle, ~6.4W under full load.
# Real value depends on attached peripherals (cameras, USB, HAT, etc.)
# and is NOT measured directly -- adjust these two numbers if you ever
# measure your own setup with a USB power meter.
POWER_IDLE_W  = 2.7
POWER_MAX_W   = 6.4
# ------------------------------------------------------------------


def get_cpu_temp():
    """CPU / SoC temperature in deg C, via vcgencmd (falls back to psutil)."""
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_temp"], text=True, timeout=1
        )
        # out looks like "temp=45.6'C"
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        try:
            temps = psutil.sensors_temperatures()
            for key in ("cpu_thermal", "cpu-thermal"):
                if key in temps and temps[key]:
                    return temps[key][0].current
        except Exception:
            pass
        return None


def get_cpu_freq_mhz():
    """Current CPU (ARM core) clock speed in MHz.

    Uses vcgencmd first since it reads the real-time clock straight from
    the SoC. Falls back to psutil if vcgencmd isn't available (e.g. when
    testing this script off-Pi).
    """
    try:
        out = subprocess.check_output(
            ["vcgencmd", "measure_clock", "arm"], text=True, timeout=1
        )
        # out looks like "frequency(48)=1500000000"
        hz = int(out.strip().split("=")[1])
        return round(hz / 1_000_000, 1)
    except Exception:
        try:
            freq = psutil.cpu_freq()
            if freq:
                return round(freq.current, 1)
        except Exception:
            pass
        return None


def is_throttled():
    """Reads vcgencmd get_throttled and reports whether freq is currently
    capped due to undervoltage or thermal throttling. Returns None if
    vcgencmd isn't available."""
    try:
        out = subprocess.check_output(
            ["vcgencmd", "get_throttled"], text=True, timeout=1
        )
        # out looks like "throttled=0x50000"
        value = int(out.strip().split("=")[1], 16)
        # bits 2 and 3 = currently throttled / currently at reduced freq
        return bool(value & 0x000C)
    except Exception:
        return None


def estimate_power_w(cpu_percent):
    """Very rough power draw estimate from CPU load. Not a real measurement."""
    fraction = max(0.0, min(cpu_percent / 100.0, 1.0))
    return round(POWER_IDLE_W + fraction * (POWER_MAX_W - POWER_IDLE_W), 2)


def write_header(csv_path, num_cores):
    """Write test metadata as comment lines, then the CSV column header."""
    with open(csv_path, "w", newline="") as f:
        f.write("# Raspberry Pi 4B data logger\n")
        f.write("# start_time,{}\n".format(datetime.now().isoformat()))
        f.write("# num_cameras,{}\n".format(NUM_CAMERAS))
        f.write("# test_type,{}\n".format(TEST_TYPE))
        f.write("# notes,{}\n".format(NOTES))
        f.write("# interval_sec,{}\n".format(INTERVAL_SEC))
        f.write("# num_cores,{}\n".format(num_cores))
        f.write("# power_model,idle={}W max={}W (estimated, not measured)\n".format(
            POWER_IDLE_W, POWER_MAX_W))
        f.write("#\n")

        writer = csv.writer(f)
        header = (
            ["timestamp", "cpu_total_pct"]
            + ["cpu_core{}_pct".format(i) for i in range(num_cores)]
            + ["ram_pct", "ram_used_mb", "ram_total_mb",
               "cpu_temp_c", "cpu_freq_mhz", "throttled",
               "net_down_mbps", "net_up_mbps",
               "power_est_w"]
        )
        writer.writerow(header)


def main():
    num_cores = psutil.cpu_count(logical=True)
    write_header(OUTPUT_FILE, num_cores)
    print("Logging to {} (test_type={}, cameras={})".format(
        OUTPUT_FILE, TEST_TYPE, NUM_CAMERAS))
    print("Press Ctrl+C to stop.")

    # prime CPU percent calls (first call after start always returns 0.0)
    psutil.cpu_percent(percpu=True)
    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    start = time.time()
    try:
        with open(OUTPUT_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            while True:
                time.sleep(INTERVAL_SEC)

                now = time.time()
                elapsed = now - prev_time
                prev_time = now

                per_core = psutil.cpu_percent(percpu=True)
                cpu_total = sum(per_core) / len(per_core)

                mem = psutil.virtual_memory()

                temp = get_cpu_temp()
                freq = get_cpu_freq_mhz()
                throttled = is_throttled()

                net = psutil.net_io_counters()
                down_mbps = (net.bytes_recv - prev_net.bytes_recv) * 8 / elapsed / 1_000_000
                up_mbps = (net.bytes_sent - prev_net.bytes_sent) * 8 / elapsed / 1_000_000
                prev_net = net

                power_est = estimate_power_w(cpu_total)

                row = (
                    [datetime.now().isoformat(), round(cpu_total, 1)]
                    + [round(c, 1) for c in per_core]
                    + [mem.percent,
                       round(mem.used / (1024 * 1024), 1),
                       round(mem.total / (1024 * 1024), 1),
                       temp,
                       freq,
                       throttled,
                       round(down_mbps, 3),
                       round(up_mbps, 3),
                       power_est]
                )
                writer.writerow(row)
                f.flush()

                print(
                    "CPU {:5.1f}% | Freq {} MHz{} | RAM {:5.1f}% | Temp {} C | "
                    "Down {:6.2f} Mbps | Up {:6.2f} Mbps | Power ~{} W".format(
                        cpu_total,
                        freq if freq is not None else "n/a",
                        " [THROTTLED]" if throttled else "",
                        mem.percent,
                        temp if temp is not None else "n/a",
                        down_mbps, up_mbps, power_est
                    )
                )

                if DURATION_SEC and (now - start) >= DURATION_SEC:
                    break
    except KeyboardInterrupt:
        print("\nStopped by user.")

    print("Done. Data saved to {}".format(OUTPUT_FILE))


if __name__ == "__main__":
    main()