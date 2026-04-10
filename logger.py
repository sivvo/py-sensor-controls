# temperature, humidity, light, motion (if we care)
# each RPI has a variety of sensors... they will obtain local metrics and then send them over to the rPI server that
# has the graphical display

import os
import time
import json
import logging
import sys
import lightmodule
import dht11
import datetime

project_folder = os.path.expanduser('~/deploy')  # adjust as appropriate

try:
    import RPi.GPIO as GPIO
except:
    pass
try:
    import smbus2
except:
    pass
try:
    import bme280
except:
    pass
import urllib
import urllib2
from influxdb import InfluxDBClient

influx_host = '192.168.1.13'
influx_port = '8086'
influx_database = 'homeclimate'
influx_dbuser = 'piweather'
influx_dbpassword = 'piweather'
client = InfluxDBClient(influx_host, influx_port, influx_dbuser, influx_dbpassword, influx_database)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler('logger.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)
logging.getLogger().addHandler(logging.StreamHandler())

SENSORINTERVAL = 300  # delay between sensor reads


class sensor(object):
    name = ""
    enabled = ""
    mode = ""
    location = ""
    type = ""
    dataport = 0

    def __init__(self, settings):
        self.name = self.try_to_load("name", settings)
        self.enabled = self.try_to_load("enabled", settings)
        self.mode = self.try_to_load("mode", settings)
        self.location = self.try_to_load("location", settings)
        self.dataport = self.try_to_load("dataport", settings)
        self.type = self.try_to_load("type", settings)
        self.local_settings()

    def local_settings(self):
        pass

    def try_to_load(self, key, settings):
        try:
            value = settings[key]
        except:
            value = ""
        return value

    def print_settings(self):
        logger.debug("name: %s", self.name)
        logger.debug("enabled: %s", self.enabled)
        logger.debug("mode: %s", self.mode)
        logger.debug("location: %s", self.location)
        logger.debug("dataport: %n", self.dataport)
        logger.debug("type: %s", self.type)

    def get_value(self):
        raise NotImplementedError("get_value must be defined in subclasses of sensor")


class temperaturesensor(sensor):
    def get_value(self):
        return self.read_temp()

    def temp_raw(self):
        f = open(self.location, 'r')
        lines = f.readlines()
        f.close
        return lines

    def read_temp(self):
        lines = self.temp_raw()
        while lines[0].strip()[-3:] == 'YES':
            time.sleep(0.2)
            lines = self.temp_raw()
            temp_output = lines[1].find('t=')
            if temp_output != -1:
                temp_string = lines[1].strip()[temp_output + 2:]
                temp_c = float(temp_string) / 1000.0
                return temp_c


class luxsensor(sensor):
    def get_value(self):
        return lightmodule.readLight()


class humiditysensor(sensor):
    def local_settings(self):
        # initialize GPIO
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            # GPIO.cleanup()
            # read data using pin 4
            self.instance = dht11.DHT11(pin=4)
        except:
            pass

    def get_value(self):

        result = self.instance.read()
        match = False
        while not match:
            result = self.instance.read()
            if result.is_valid():
                match = True
                return result.temperature, result.humidity
        else:
            # raise ValueError("We didn't get a valid response from the sensor %s" % result.error_code)^M
            logger.warn("the sensor returned junk %s" % result.error_code)


class outsidesensor(sensor):
    def get_value(self):
        # OUTSIDE TEMPERATURE
        apikey = ""  # sign up here http://www.wunderground.com/weather/api/ for a key
        unit = 'metric'  # For Fahrenheit use imperial, for Celsius use metric, and the default is Kelvin.
        apiurl = 'http://api.openweathermap.org/data/2.5/weather?id=2643741'
        full_api_url = apiurl + '&mode=json&units=metric&APPID=' + apikey

        url = urllib2.urlopen(full_api_url)
        output = url.read().decode('utf-8')
        raw_api_dict = json.loads(output)
        url.close()
        data = dict(
            city=raw_api_dict.get('name'),
            country=raw_api_dict.get('sys').get('country'),
            temp=raw_api_dict.get('main').get('temp'),
            temp_max=raw_api_dict.get('main').get('temp_max'),
            temp_min=raw_api_dict.get('main').get('temp_min'),
            humidity=raw_api_dict.get('main').get('humidity'),
            pressure=raw_api_dict.get('main').get('pressure'),
            sky=raw_api_dict['weather'][0]['main'],
            sunrise=self.time_converter(raw_api_dict.get('sys').get('sunrise')),
            sunset=self.time_converter(raw_api_dict.get('sys').get('sunset')),
            wind=raw_api_dict.get('wind').get('speed'),
            wind_deg=raw_api_dict.get('deg'),
            dt=self.time_converter(raw_api_dict.get('dt')),
            cloudiness=raw_api_dict.get('clouds').get('all')
        )

        m_symbol = '\xb0' + 'C'
        # print(data['temp'], m_symbol, data['sky'])
        temp = data['temp']
        min_temp = data['temp_min']
        max_temp = data['temp_max']
        humidity = data['humidity']
        sunrise = data['sunrise']
        sunset = data['sunset']

        return temp, min_temp, max_temp, humidity, sunrise, sunset

    def time_converter(self, time):
        converted_time = datetime.datetime.fromtimestamp(
            int(time)
        ).strftime('%I:%M %p')
        return converted_time


class bme280sensor(sensor):
    def local_settings(self):
        self.address = 0x76
        self.bus = smbus2.SMBus(self.dataport)
        self.calibration_params = bme280.load_calibration_params(self.bus, self.address)

    def get_value(self):
        data = bme280.sample(self.bus, self.address, self.calibration_params)
        return data.temperature, data.pressure


class bme680sensor(sensor):
    def local_settings(self):
        self.address = 0x76
        self.bus = smbus2.SMBus(self.dataport)
        self.calibration_params = bme280.load_calibration_params(self.bus, self.address)

    def get_value(self):
        data = bme280.sample(self.bus, self.address, self.calibration_params)
        return data.temperature, data.pressure


Runs the sensor for a burn-in period, then uses a
combination of relative humidity and gas resistance
to estimate indoor air quality as a percentage.

Press Ctrl+C to exit!
Gas: 214689.00 Ohms,humidity: 39.71 %RH,air quality: 99.02


Gas: 144231.00 Ohms,humidity: 68.75 %RH,air quality: 71.40
Gas: 145099.00 Ohms,humidity: 68.30 %RH,air quality: 71.94
Gas: 146104.00 Ohms,humidity: 67.79 %RH,air quality: 72.56




class TempLogger():
    def __init__(self):
        self.temperature = []
        self.humidity = []
        self.lux = []
        self.bme280 = []
        self.movement = []
        self.outside = []
        self.config_data = []
        self.active_sensors = []
        self.sensor_name = []

        self.loadConfig()  # read the config settings

    def parse_config_enabled(self, key_to_check):
        logger.debug("checking for " + key_to_check)
        try:
            conf_entry = self.config_data[key_to_check]
            logger.debug("setting defined")
        except:
            conf_entry = "[]"
            logger.debug("Key not found, auto-setting to blank")

        return conf_entry
        # if key_to_check in self.config_data:

    def config_set(self, key_to_check):
        logger.debug("testing if key exists %s", key_to_check)
        try:
            enabled_check = self.config_data[key_to_check]["enabled"]
        except:
            enabled_check = ""
        if enabled_check == "True":
            return True
        else:
            return False

    def loadConfig(self):
        try:
            with open('config.json') as json_data_file:
                self.config_data = json.load(json_data_file)
        except:
            logger.warn("No config file found")

        self.temperature = temperaturesensor(self.parse_config_enabled("temperature"))
        self.humidity = humiditysensor(self.parse_config_enabled("humidity"))
        self.lux = luxsensor(self.parse_config_enabled("lux"))
        self.movement = sensor(self.parse_config_enabled("movement"))
        self.sensor_name = self.parse_config_enabled('sensor_name')
        self.outside = outsidesensor(self.parse_config_enabled("outside"))
        self.bme280 = bme280sensor(self.parse_config_enabled("bme280"))

        # self.temperature.print_settings()
        # self.humidity.print_settings()
        # self.lux.print_settings()
        # self.movement.print_settings()

        if self.temperature.enabled == "True":
            logger.info("Enabling temperature")
            self.active_sensors.append(self.temperature)
        if self.humidity.enabled == "True":
            logger.info("Enabling Humidity")
            self.active_sensors.append(self.humidity)
        if self.lux.enabled == "True":
            logger.info("Enabling Lux")
            self.active_sensors.append(self.lux)
        if self.bme280.enabled == "True":
            logger.info("Enabling BME280")
            self.active_sensors.append(self.lux)
        if self.movement.enabled == "True":
            logger.info("Enabling Movement")
            self.active_sensors.append(self.movement)
        if self.outside.enabled == "True":
            logger.info("Enabling Outside")

    def getvalues(self):
        logger.info("Checking for values")

        # get each of our sensor values... and then log them
        # push them all at once?
        timestamp = time.time()  # not compatible with line
        timestamp = time.ctime()
        output = {}

        if self.temperature.enabled == "True":
            # self.get_temperature()
            output['temperature'] = self.get_data(self.temperature)

            # output.add("temperature: %s", self.get_data(self.temperature))
            # print self.get_data(self.temperature)
        if self.bme280.enabled == "True":
            # print self.get_data(self.humidity)
            resp = self.get_data(self.bme280)
            output['temperature'] = float(resp[0])
            output['pressure'] = resp[1]

        if self.humidity.enabled == "True":
            # print self.get_data(self.humidity)
            resp = self.get_data(self.humidity)
            output['temperature'] = float(resp[0])
            output['humidity'] = resp[1]
            # output.add("temperature: %s, humidity: %s", resp[0], resp[1])
            # self.get_humidity()
        if self.lux.enabled == "True":
            # print self.get_data(self.lux)
            output['lux'] = self.get_data(self.lux)
            # output.add("lux: %s", self.get_data(self.lux))
            # self.get_lux()
        if self.movement.enabled == "True":
            # print self.get_data(self.movement)
            raise NotImplementedError("Movement monitoring hasn't been implemented yet")
            # self.get_movement()
        if self.outside.enabled == "True":
            resp = self.get_data(self.outside)
            output['temperature'] = resp[0]
            output['min_temp'] = resp[1]
            output['max_temp'] = resp[2]
            output['humidity'] = resp[3]
            output['sunrise'] = resp[4]
            output['sunset'] = resp[5]

        if len(output) > 0:
            # we have some values
            # output['timestamp'] = timestamp
            # output['sensor'] = str(self.sensor_name["name"]) # don't need this anymore
            logger.debug(output)
            data = [
                {
                    "measurement": "piweather",
                    "tags": {
                        "location": str(self.sensor_name["name"]),
                    },
                    "time": timestamp,
                    "fields":
                        output
                }
            ]

            # Send the JSON data to InfluxDB
            logger.debug("writing data to the server")
            try:
                client.write_points(data)
            except:
                logger.warning("couldn't write to influxDB")

    def get_data(self, obj):
        response = obj.get_value()
        return response


templogger = TempLogger()
while True:
    templogger.getvalues()
    time.sleep(SENSORINTERVAL)
