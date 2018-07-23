import numpy as np
import io
import serial
import math
import time
from flask import Flask, jsonify
from flask_cors import CORS, cross_origin
from collections import deque
from src.async import taskman

# ////////////////////////////////////////////////////////////// configs

SERIAL_URL = 'COM3'

# autopilot
AUTOPILOT_SLEEP_TIME = 1  # seconds
TRIGGER_DISTANCE = 50

# data
LINE_LENGTH = 6
BAUD_RATE = 9600
NUM_MEASUREMENTS = 8
SENSOR_RANGE = [0, 200]

# ////////////////////////////////////////////////////////////// setup

ser = serial.serial_for_url(SERIAL_URL, timeout=0, baudrate=BAUD_RATE)
ser.flushInput()
stream = io.BufferedRWPair(ser, ser)
sio = io.TextIOWrapper(stream, line_buffering=True)

app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'
cors = CORS(app)

steps = deque([], maxlen=NUM_MEASUREMENTS)
dists = deque([], maxlen=NUM_MEASUREMENTS)
x = deque([], maxlen=NUM_MEASUREMENTS)
y = deque([], maxlen=NUM_MEASUREMENTS)


# //////////////////////////////////////////////////////////// fns


def update_data():
    def to_position(st, dist):
        deg = st / NUM_MEASUREMENTS * 360
        rad = math.radians(deg)
        interp_dist = np.interp(dist, SENSOR_RANGE, [0, 1])
        result = - np.sin(rad) * interp_dist, np.cos(rad) * interp_dist
        return result

    buffer_size = ser.inWaiting()
    buffer = sio.read(buffer_size)
    last_lines = buffer.split('\n')[-NUM_MEASUREMENTS:]  # prevent reading from large buffer
    for line in last_lines:
        if len(line) == LINE_LENGTH:
            step, distance = line.strip('\n').split()
            position = to_position(float(step), float(distance))
            steps.append(step)
            dists.append(distance)
            x.append(position[0])
            y.append(position[1])


def auto_pilot_loop():
    for step, dist in zip(steps, dists):
        print('autopilot:', step, dist)
        if step == 0 and dist < TRIGGER_DISTANCE:
            print('detected trigger distance')
            line = 'F'  # TODO
            sio.write(line)


def run_auto_pilot_loop(duration):
    for _ in range(duration):
        print('entered autopilot loop')
        autopilot()
        time.sleep(AUTOPILOT_SLEEP_TIME)

# //////////////////////////////////////////////////////////// views


@app.route('/')
def index():
    return 'This is the source of serial data from an Arduino-powered ultrasound sensor'


@app.route('/autopilot/<duration>', methods=['POST', 'GET'])  # TODO trigger via ajax and execute asynchronoulsy
def autopilot(duration):
    taskman.add_task(run_auto_pilot_loop, duration)


@app.route('/com3', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content- Type', 'Authorization'])
def com3():
    update_data()
    return jsonify(x=list(x), y=list(y))


if __name__ == '__main__':
    app.run(port=5000, debug=False)
