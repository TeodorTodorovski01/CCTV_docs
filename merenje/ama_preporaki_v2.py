import time
import csv
import cv2
import psutil
import subprocess
from datetime import datetime


# ===============================
# SETTINGS
# ===============================http://192.168.185.125:9081

output_file = "Kje_se_pukam_2.csv"

environment = "test"

target_fps = 30


camera_streams = [

    "http://192.168.100.129:9081"

]


# ===============================
# OPEN MOTIONEYE STREAMS
# ===============================

def open_cameras():

    cameras = []


    for url in camera_streams:


        print("Connecting:", url)


        cap = cv2.VideoCapture(
            url
        )


        if not cap.isOpened():

            print("FAILED:", url)

            continue



        width = int(
            cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )


        height = int(
            cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )


        cameras.append(

            {
                "url": url,

                "cap": cap,

                "resolution":
                f"{width}x{height}",

                "frames": 0,

                "drops": 0,

                "fps": 0,

                "last": time.time()

            }

        )


        print(
            "Connected",
            url,
            "Resolution:",
            width,
            "x",
            height
        )


    return cameras



# ===============================
# SYSTEM FUNCTIONS
# ===============================


def get_temperature():

    try:

        with open(
            "/sys/class/thermal/thermal_zone0/temp"
        ) as f:

            return round(
                int(f.read()) / 1000,
                2
            )

    except:

        return 0



def get_cpu_freq():

    try:

        return round(
            psutil.cpu_freq().current,
            1
        )

    except:

        return 0



def get_throttle():

    try:

        result = subprocess.check_output(
            [
                "vcgencmd",
                "get_throttled"
            ]
        )

        return result.decode().strip()

    except:

        return "N/A"



def get_threads():

    count = 0

    for p in psutil.process_iter():

        try:

            count += p.num_threads()

        except:

            pass

    return count



# ===============================
# START
# ===============================


print("\nStarting MotionEye monitor\n")


cameras = open_cameras()


if len(cameras) == 0:

    print("No streams found")

    exit()



print(
"\nCameras detected:",
len(cameras)
)



with open(
    output_file,
    "a",
    newline=""
) as file:


    writer = csv.writer(file)


    if file.tell() == 0:

        writer.writerow(
        [

        "Timestamp",

        "Environment",

        "Camera_Count",

        "Resolution",

        "Target_FPS",

        "Motion_Factor",


        "Total_CPU",

        "Core0_CPU",

        "Core1_CPU",

        "Core2_CPU",

        "Core3_CPU",


        "RAM_Used_MB",

        "SoC_Temp",

        "CPU_Freq",

        "Throttled_State",

        "IO_Wait",

        "Actual_FPS",

        "Drops",

        "Threads"

        ]
        )



    print("\nMonitoring started")
    print("CTRL+C to stop\n")



    try:


        while True:



            # CPU

            total_cpu = psutil.cpu_percent()



            cores = psutil.cpu_percent(
                percpu=True
            )


            while len(cores)<4:

                cores.append(0)



            # RAM

            mem = psutil.virtual_memory()


            ram_used = round(

                mem.used /
                (1024*1024),

                1

            )



            fps_values = []

            resolutions = []

            total_drops = 0



            # ===================
            # STREAM READ
            # ===================


            for cam in cameras:


                ret, frame = cam["cap"].read()


                now = time.time()



                if ret:

                    cam["frames"] += 1

                else:

                    cam["drops"] += 1



                elapsed = (
                    now -
                    cam["last"]
                )



                if elapsed >= 1:


                    cam["fps"] = round(

                        cam["frames"]
                        /
                        elapsed,

                        2

                    )


                    cam["frames"] = 0

                    cam["last"] = now



                fps_values.append(
                    cam["fps"]
                )


                resolutions.append(
                    cam["resolution"]
                )


                total_drops += cam["drops"]




            actual_fps = 0


            if len(fps_values):

                actual_fps = round(

                    sum(fps_values)
                    /
                    len(fps_values),

                    2

                )



            timestamp = datetime.now().strftime(

                "%Y-%m-%d %H:%M:%S"

            )



            writer.writerow(

            [

            timestamp,

            environment,

            len(cameras),

            ",".join(resolutions),

            target_fps,


            0,


            total_cpu,


            cores[0],

            cores[1],

            cores[2],

            cores[3],


            ram_used,


            get_temperature(),


            get_cpu_freq(),


            get_throttle(),


            psutil.cpu_times_percent().iowait,


            actual_fps,


            total_drops,


            get_threads()

            ]

            )



            file.flush()



            print(

                timestamp,

                "| CAM:",
                len(cameras),

                "| CPU:",
                total_cpu,

                "% | TEMP:",
                get_temperature(),

                "C | FPS:",
                actual_fps,

                "| DROP:",
                total_drops

            )



            time.sleep(1)



    except KeyboardInterrupt:


        print("\nStopped")


        for cam in cameras:

            cam["cap"].release()