import numpy as np
import io
import serial
import math
from flask import Flask, jsonify
from flask_cors import CORS, cross_origin


MOCK_DATA = True
SERIAL_URL = 'COM3'

# data
LINE_LENGTH = 6
BAUD_RATE = 9600
NUM_STEPS = 32
SENSOR_RANGE = [0, 200]

ser = serial.serial_for_url(SERIAL_URL, timeout=0, baudrate=BAUD_RATE)
ser.flushInput()
stream = io.BufferedRWPair(ser, ser)
sio = io.TextIOWrapper(stream, line_buffering=True)

app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'
cors = CORS(app, resources={r"/foo": {"origins": "http://localhost:port"}})


@app.route('/com3', methods=['POST', 'GET'])
@cross_origin(origin='localhost', headers=['Content- Type', 'Authorization'])
def com3():
    def convert(st, dist):
        deg = st / NUM_STEPS * 360
        rad = math.radians(deg)
        interp_dist = np.interp(dist, SENSOR_RANGE, [0, 1])
        result = - np.sin(rad) * interp_dist, np.cos(rad) * interp_dist
        return result

    buffer_size = ser.inWaiting()
    buffer = sio.read(buffer_size)
    x = []
    y = []
    for line in buffer.split('\n'):
        if len(line) == LINE_LENGTH:
            step, distance = line.strip('\n').split()
            xy = convert(float(step), float(distance))
            x.append(xy[0])
            y.append(xy[1])
            print('api:', x, y)
    return jsonify(x=x, y=y)

if __name__ == '__main__':
    app.run(port=5000, debug=False, host='192.168.1.15')