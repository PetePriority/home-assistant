"""
Support for Adafruit DHT temperature and humidity sensor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.dht/
"""
import logging
from datetime import timedelta

import os
import time

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    TEMP_FAHRENHEIT, CONF_NAME, CONF_MONITORED_CONDITIONS)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.util.temperature import celsius_to_fahrenheit


_LOGGER = logging.getLogger(__name__)

CONF_SENSOR_PATH = 'sensor_path'

DEFAULT_NAME = 'DHT Sensor'

# DHT11 is able to deliver data once per second, DHT22 once every two
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

SENSOR_TEMPERATURE = 'temperature'
SENSOR_HUMIDITY = 'humidity'
SENSOR_TYPES = {
    SENSOR_TEMPERATURE: ['Temperature', None],
    SENSOR_HUMIDITY: ['Humidity', '%']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SENSOR_PATH): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the DHT sensor."""
    # pylint: disable=import-error

    SENSOR_TYPES[SENSOR_TEMPERATURE][1] = hass.config.units.temperature_unit
    sensor_path = config.get(CONF_SENSOR_PATH)


    data = DHTClient(sensor_path)
    dev = []
    name = config.get(CONF_NAME)

    try:
        for variable in config[CONF_MONITORED_CONDITIONS]:
            dev.append(DHTSensor(
                data, variable, SENSOR_TYPES[variable][1], name))
    except KeyError:
        pass

    add_devices(dev)


class DHTSensor(Entity):
    """Implementation of the DHT sensor."""

    def __init__(self, dht_client, sensor_type, temp_unit, name):
        """Initialize the sensor."""
        self.client_name = name
        self._name = SENSOR_TYPES[sensor_type][0]
        self.dht_client = dht_client
        self.temp_unit = temp_unit
        self.type = sensor_type
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self.client_name, self._name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest data from the DHT and updates the states."""
        self.dht_client.update()
        data = self.dht_client.data

        if self.type == SENSOR_TEMPERATURE:
            temperature = round(data[SENSOR_TEMPERATURE], 1)
            if (temperature >= -20) and (temperature < 80):
                self._state = temperature
                if self.temp_unit == TEMP_FAHRENHEIT:
                    self._state = round(celsius_to_fahrenheit(temperature), 1)
        elif self.type == SENSOR_HUMIDITY:
            humidity = round(data[SENSOR_HUMIDITY], 1)
            if (humidity >= 0) and (humidity <= 100):
                self._state = humidity


class DHTClient(object):
    """Get the latest data from the DHT sensor."""

    def __init__(self, sensor_path):
        """Initialize the sensor."""
        self.sensor_path_temp = os.path.join(sensor_path, 'in_temp_input')
        self.sensor_path_humidity = os.path.join(sensor_path, 'in_humidityrelative_input')
        self.data = dict()


    def _dht_read(self):
        temp = None
        humidity = None
        with open(self.sensor_path_temp, 'r') as fd:
            temp = float(fd.readline().strip('\n'))/1000
        with open(self.sensor_path_humidity, 'r') as fd:
            humidity = float(fd.readline().strip('\n'))/1000
            return humidity, temp

    def _dht_read_retry(self, retries=5, wait_on_error=1):
        temp = None
        humidity = None
        run = 0
        while (temp is None or humidity is None) and run < retries:
            try:
                humidity, temp = self._dht_read()
            except OSError as err:
                run = run + 1
                _LOGGER.debug('Failed to read: %s', err)
                _LOGGER.debug('Retrying in %ds (%d/%d)...',
                               wait_on_error, run, retries)
                time.sleep(wait_on_error)

        return humidity, temp


    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data the DHT sensor."""
        humidity, temperature = self._dht_read_retry()
        if temperature is None or humidity is None:
            _LOGGER.warning('Failed to read temperature/humidity.')
        if temperature:
            self.data[SENSOR_TEMPERATURE] = temperature
        if humidity:
            self.data[SENSOR_HUMIDITY] = humidity
