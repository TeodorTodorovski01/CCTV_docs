import time
import csv
import cv2
import psutil
import subprocess
import os
import threading
from datetime import datetime


# ==================================
# LOW LATENCY FFMPEG SETTINGS
# ==================================

os.environ[
    "OPENCV_FFMPEG_CAPTURE_OPTIONS"
] = "rtsp_transport;udp|fflags;nobuffer|flags;low_delay"


# ==================================
# SETTINGS
# ==================================

output_file ="remote_proba_01.csv"

environment = "android_ip_camera"

target_fps = 30


camera_streams = [

    # Android IP Webcam
    #"http://192.168.100.108:8080/video"

    # или RTSP:
    "rtsp://192.168.100.108:8080/h264_aac.sdp"

]



# ==================================
# THREADED CAMERA
# ==================================

class ThreadedCamera:


    def __init__(self,url):

        self.url=url

        self.running=True

        self.frame=None

        self.ret=False

        self.frames=0

        self.drops=0

        self.fps=0

        self.last=time.time()


        if url.startswith(
            ("rtsp://","http://")
        ):

            self.cap=cv2.VideoCapture(
                url,
                cv2.CAP_FFMPEG
            )

            self.cap.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1
            )

        else:

            self.cap=cv2.VideoCapture(
                url
            )


        self.width=int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        self.height=int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )


        self.resolution=f"{self.width}x{self.height}"


        self.thread=threading.Thread(
            target=self.update,
            daemon=True
        )


        self.thread.start()



    def update(self):

        while self.running:


            ret,frame=self.cap.read()


            if ret:

                self.ret=True

                self.frame=frame

                self.frames+=1


            else:

                self.drops+=1



    def read(self):

        return self.ret,self.frame



    def stop(self):

        self.running=False

        self.cap.release()





# ==================================
# SYSTEM FUNCTIONS
# ==================================

def temperature():

    try:

        with open(
        "/sys/class/thermal/thermal_zone0/temp"
        ) as f:

            return round(
                int(f.read())/1000,
                2
            )

    except:

        return 0



def cpu_freq():

    try:

        f=psutil.cpu_freq()

        if f:

            return round(
                f.current,
                1
            )

    except:

        pass

    return 0



def throttle():

    try:

        r=subprocess.check_output(
            [
            "vcgencmd",
            "get_throttled"
            ]
        )

        return r.decode().strip()


    except:

        return "N/A"





# ==================================
# START
# ==================================


print("\nStarting monitor\n")


cameras=[]


for url in camera_streams:


    print(
        "Connecting:",
        url
    )


    cam=ThreadedCamera(url)


    if cam.cap.isOpened():

        print(
            "Connected",
            cam.resolution
        )

        cameras.append(cam)


    else:

        print(
            "FAILED",
            url
        )



if not cameras:

    print("No cameras")

    exit()



with open(
    output_file,
    "a",
    newline=""
) as file:


    writer=csv.writer(file)


    if file.tell()==0:


        writer.writerow(

        [

        "Timestamp",
        "Camera",
        "Resolution",

        "CPU",
        "RAM_MB",
        "TEMP",

        "CPU_FREQ",
        "THROTTLE",

        "FPS",
        "DROPS",
        "THREADS"

        ]

        )




    print(
        "\nMonitoring started\n"
    )


    try:


        while True:



            cpu=psutil.cpu_percent()


            ram=round(

                psutil.virtual_memory().used
                /
                (1024*1024),

                1
            )



            for cam in cameras:


                now=time.time()


                elapsed=now-cam.last



                if elapsed>=1:


                    cam.fps=round(

                        cam.frames /
                        elapsed,

                        2
                    )


                    cam.frames=0

                    cam.last=now



                writer.writerow(

                [

                datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
                ),

                cam.url,

                cam.resolution,

                cpu,

                ram,

                temperature(),

                cpu_freq(),

                throttle(),

                cam.fps,

                cam.drops,

                threading.active_count()

                ]

                )


                file.flush()



                print(

                datetime.now(),

                "| FPS:",
                cam.fps,

                "| CPU:",
                cpu,

                "% | TEMP:",
                temperature()

                )



            time.sleep(1)



    except KeyboardInterrupt:


        print("\nStopped")



        for cam in cameras:

            cam.stop()