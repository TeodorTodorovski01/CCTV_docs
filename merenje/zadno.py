import time
import csv
import psutil

output_file = "test_zivkoKamera_i_2Dps.csv"

start_time = time.time()

with open(output_file, "a", newline="") as file:
    writer = csv.writer(file)

    if file.tell() == 0:
        writer.writerow([
            "Measurement",
            "Elapsed_Time",
            "Temperature_C",
            "CPU_Usage_Total_%",
            "CPU0_%",
            "CPU1_%",
            "CPU2_%",
            "CPU3_%",
            "CPU_Freq_MHz",
            "RAM_Used_MB",
            "RAM_Available_MB",
            "Thread_Count"
        ])

    count = 0

    print("System logging started...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            count += 1

            # Time from start
            elapsed_seconds = int(time.time() - start_time)

            hours = elapsed_seconds // 3600
            minutes = (elapsed_seconds % 3600) // 60
            seconds = elapsed_seconds % 60

            elapsed_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # Temperature
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
                temperature = float(temp_file.read()) / 1000.0

            # CPU usage
            cpu_usage_total = psutil.cpu_percent(interval=None)
            cpu_cores = psutil.cpu_percent(interval=None, percpu=True)

            # Make sure all 4 cores exist
            while len(cpu_cores) < 4:
                cpu_cores.append(0.0)

            # CPU frequency
            freq = psutil.cpu_freq()
            cpu_freq_mhz = round(freq.current, 1) if freq else 0

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

            writer.writerow([
                count,
                elapsed_time,
                round(temperature, 2),
                round(cpu_usage_total, 1),

                round(cpu_cores[0], 1),
                round(cpu_cores[1], 1),
                round(cpu_cores[2], 1),
                round(cpu_cores[3], 1),

                cpu_freq_mhz,

                round(ram_used_mb, 1),
                round(ram_available_mb, 1),

                thread_count
            ])

            file.flush()

            print(
                f"{count}: {elapsed_time} | "
                f"Temp={temperature:.1f}°C | "
                f"CPU={cpu_usage_total:.1f}% | "
                f"C0={cpu_cores[0]:.1f}% | "
                f"C1={cpu_cores[1]:.1f}% | "
                f"C2={cpu_cores[2]:.1f}% | "
                f"C3={cpu_cores[3]:.1f}% | "
                f"Freq={cpu_freq_mhz:.0f}MHz | "
                f"RAM={ram_used_mb:.0f}MB | "
                f"Free={ram_available_mb:.0f}MB | "
                f"Threads={thread_count}"
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nLogging stopped.")