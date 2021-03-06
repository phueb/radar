import numpy as np
import os
from flask import Flask, render_template
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models.sources import AjaxDataSource, ColumnDataSource
from bokeh.resources import INLINE
import requests


SERIAL_URL = 'COM3'
LOCAL_SERVICE_URL = 'https://arduinoradar.ngrok.io/'  # include trailing forward slash

# data
ROLLOVER = 6
LINE_LENGTH = 6
BAUD_RATE = 9600
DISTANCE_UNITS = 'cm'
SENSOR_RANGE = [0, 200]
MS_PER_STEP = 1000  # smaller-> more frequent updates but risks breaking stream into too small chunks

# plot
SIZE = 600
PAD = 0.1
SCATTER_RADIUS = 0.05
LINE_WIDTH = 2
NUM_LINES = 5

app = Flask(__name__)
if os.getenv('APP_MODE') == "PRODUCTION":
    app.config.from_object('production_configs')
else:
    app.config.from_object('dev_configs')


def make_plot(data_url):
    def make_unit_poly_vertices(dist):
        x0, y0 = 0, 0
        theta = np.linspace(0, 2 * np.pi, 101, endpoint=True)
        theta += np.pi / 2  # start zero at top
        result = [(dist * np.cos(t) + x0, dist * np.sin(t) + y0) for t in theta]
        return result

    p = figure(plot_width=SIZE,
               plot_height=SIZE,
               x_range=(-1 - PAD, 1 + PAD),
               y_range=(-1 - PAD, 1 + PAD),
               min_border=0,
               background_fill_color="#000000")
    p.xgrid.visible = False
    p.ygrid.visible = False
    p.xaxis.axis_label = 'Distance ({})'.format(DISTANCE_UNITS)
    p.xaxis.axis_label = 'Distance ({})'.format(DISTANCE_UNITS)
    p.xaxis.ticker = [-1, 0, 1]
    p.yaxis.ticker = [-1, 0, 1]
    p.xaxis.major_label_overrides = {-1: str(-SENSOR_RANGE[-1]), 0: 'Zero', 1: str(SENSOR_RANGE[-1])}
    p.yaxis.major_label_overrides = {-1: str(-SENSOR_RANGE[-1]), 0: 'Zero', 1: str(SENSOR_RANGE[-1])}
    p.toolbar.logo = None
    p.toolbar_location = None

    # concentric lines
    distances_to_line = np.linspace(0, 1, NUM_LINES, endpoint=True)
    for d in distances_to_line:
        vertices = make_unit_poly_vertices(d)  # TODO make circle instead
        line_x = [v[0] for v in vertices]
        line_y = [v[1] for v in vertices]
        line_source = ColumnDataSource({'x': line_x,
                                        'y': line_y})
        p.line(x='x',
               y='y',
               source=line_source,
               line_width=LINE_WIDTH,
               line_color='#43ff00')

    # radial axes
    num_axes = 4
    big_angle = 2.0 * np.pi / num_axes
    angles = np.arange(num_axes) * big_angle - np.pi / 2
    p.annular_wedge(x=0,
                    y=0,
                    inner_radius=distances_to_line[0],
                    outer_radius=distances_to_line[-1],
                    start_angle=angles,
                    end_angle=angles,
                    color='#43ff00')

    # scatter
    scatter_source = AjaxDataSource(data_url=data_url,
                                    polling_interval=MS_PER_STEP,
                                    max_size=ROLLOVER,
                                    mode='replace')
    scatter_source.data = {'x': [],
                           'y': []}
    p.scatter(x='x',
              y='y',
              source=scatter_source,
              line_color=None,
              fill_color='#43ff00',
              radius=SCATTER_RADIUS)

    return p


# ////////////////////////////////////////// views


@app.route('/')
def index():
    return render_template('index.html', autopilot_status='off')


@app.route('/start_autopilot/<duration>')
def start_autopilot(duration):
    print('requesting autopilot to start...')
    r = requests.post(LOCAL_SERVICE_URL + 'autopilot', data={'duration': duration})  # TODO test
    print('sent request to ', r.url)
    return render_template('index.html', autopilot_status='started')


@app.route('/start_radar')
def start_radar():
    data_url = LOCAL_SERVICE_URL + 'com3'
    p = make_plot(data_url)
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    script, div = components(p, INLINE)
    return render_template('radar.html',
                           plot_script=script,
                           plot_div=div,
                           js_resources=js_resources,
                           css_resources=css_resources)


if __name__ == '__main__':
    app.run(port=80, debug=False, host='192.168.1.15')