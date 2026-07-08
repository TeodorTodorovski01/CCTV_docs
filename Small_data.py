

import time
import csv
import psutil
from datetime import datetime

output_file = "test4.csv"

with open(output_file, "a", newline="") as file:
    writer = csv.writer(file)

    if file.tell() == 0:
        writer.writerow([
            "Measurement",
            "Timestamp",
            "Temperature_C",
            "CPU_Usage_%",
            "CPU_Freq_MHz",
            "RAM_Used_MB",
            "RAM_Available_MB",
            "Thread_Count",
            "Load_1min"
        ])

    count = 0

    print("System logging started...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            count += 1

            # Temperature
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
                temperature = float(temp_file.read()) / 1000.0

            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=None)

            # CPU frequency
            cpu_freq = psutil.cpu_freq()
            cpu_freq_mhz = cpu_freq.current if cpu_freq else 0

            # RAM
            mem = psutil.virtual_memory()
            ram_used_mb = mem.used / (1024 * 1024)
            ram_available_mb = mem.available / (1024 * 1024)

            # Thread count
            thread_count = 0
            for p in psutil.process_iter():
                try:
                    thread_count += p.num_threads()
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess
                ):
                    pass

            # System load
            load_1min = psutil.getloadavg()[0]

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            writer.writerow([
                count,
                timestamp,
                round(temperature, 2),
                round(cpu_usage, 1),
                round(cpu_freq_mhz, 0),
                round(ram_used_mb, 1),
                round(ram_available_mb, 1),
                thread_count,
                round(load_1min, 2)
            ])

            file.flush()

            print(
                f"{count}: {timestamp} | "
                f"Temp={temperature:.1f}Â°C | "
                f"CPU={cpu_usage:.1f}% | "
                f"Freq={cpu_freq_mhz:.0f}MHz | "
                f"RAM={ram_used_mb:.0f}MB | "
                f"Free={ram_available_mb:.0f}MB | "
                f"Threads={thread_count} | "
                f"Load={load_1min:.2f}"
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nLogging stopped.")
