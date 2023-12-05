from flask import Response
from flask import Flask
from flask import render_template
import threading
import argparse
import numpy as np
import time
import cv2

import picamera2 

# initialize the output frame and a lock used to ensure thread-safe
lock = threading.Lock()
init_frame = None
original_frame = None
output_frame = None

refresh_requested = False

mode_names = ["Original", "Color Diff", "Mono Diff"]
mode_id = 0


# initialize a flask object
app = Flask(__name__)

picam2 = picamera2.PiCamera2()
# picam2.resolution = (640, 480)
# picam2.framerate = 25
mode = picam2.sensor_modes[0]
video_config = picam2.create_video_configuration(main={"size": mode['size']}, sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']})
picam2.configure(video_config)
picam2.set_controls({"ExposureTime": 10000, "AnalogueGain": 1.0})
picam2.set_controls({"AwbEnable": False, "Brightness": 0})  # brightness value: from -1 to 1
picam2.set_controls({"ColourGains": (1.0, 1.5)}) # corlor gains range: 0.0-32.0
picam2.set_controls({"ExposureValue": 5.0}) # between -8 and 8
# Need to set ISO prior to fixing exposure mode
# picam2.iso = 400
picam2.start()
image = picam2.capture_array("main")
# stream = PiRGBArray(picam2, size=(640, 480))

# encoder = H264Encoder(1000000)

last_time = time.time()
frame_count = 0
FPS = ""


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")

@app.route("/update_fps", methods=["GET"])
def update_fps():
    global FPS
    return FPS


def process():
    # grab global references to the video stream, output frame, and
    # lock variables
    global init_frame, output_frame, lock, last_time, refresh_requested, FPS, frame_count, mode_id
    # loop over frames from the video stream
    for frame in picam2.capture_continuous(image, format="bgr", use_video_port=True):
        # image.truncate()
        # stream.seek(0)
        # image = stream.array

        frame_count += 1
        if (frame_count >= 5):
            FPS = "FPS: {:.1f}".format(5. / (time.time() - last_time))
            last_time = time.time()
            frame_count = 0
        
        with lock:
            original_frame = image.copy().astype(np.int32)
            if init_frame is None or refresh_requested:
                init_frame = original_frame.copy()
                refresh_requested = False
            
            if mode_id == 0:
                # Original color image
                output_frame = original_frame.copy()
            elif mode_id == 1:
                # Color diff image
                output_frame = original_frame - init_frame + 128
            elif mode_id == 2:
                # Mono diff image
                output_frame = original_frame - init_frame + 128
                output_frame[:, :, 0] = output_frame[:, :, 2] - output_frame[:, :, 1] + 128
                output_frame[:, :, 1] = output_frame[:, :, 0]
                output_frame[:, :, 2] = output_frame[:, :, 0]
            output_frame = output_frame.astype(np.uint8)


def generate():
    # grab global references to the output frame and lock variables
    global output_frame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if output_frame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + bytearray(encodedImage) + b"\r\n"
        )


@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/btn_refresh")
def btn_refresh():
    print("Refresh button hit.")
    global refresh_requested
    refresh_requested = True
    return "nothing"


@app.route("/btn_mode")
def btn_mode():
    global mode_id, mode_names, refresh_requested
    refresh_requested = True
    mode_id = (mode_id + 1) % 3
    print("Mode swithing button hit. Switching to {} mode".format(mode_names[mode_id]))
    return "nothing"

@app.route("/update_btn_mode", methods=["GET"])
def update_btn_mode():
    global mode_names, mode_id
    return mode_names[mode_id]

# check to see if this is the main thread of execution
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-i", "--ip", type=str, required=True, help="ip address of the device"
    )
    ap.add_argument(
        "-o",
        "--port",
        type=int,
        required=True,
        help="ephemeral port number of the server (1024 to 65535)",
    )
    args = vars(ap.parse_args())
    t = threading.Thread(target=process)
    t.daemon = True
    t.start()
    # start the flask app
    app.run(
        host=args["ip"],
        port=args["port"],
        debug=False,
        threaded=True,
        use_reloader=False,
    )
