"""
Support for a motion detection sensor using deCONZ websocket

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/deconz_motion/
"""
import logging

import voluptuous as vol

import homeassistant.components.deconz as deconz

from homeassistant.components.binary_sensor import (
    BinarySensorDevice, PLATFORM_SCHEMA)
from homeassistant.const import (DEVICE_DEFAULT_NAME, CONF_HOST, CONF_PORT)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_SENSORS = 'sensors'

DEPENDENCIES = ['deconz']

_SENSORS_SCHEMA = vol.Schema({
    cv.positive_int: cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    # vol.Required(CONF_TYPE): cv.string,
    # vol.Required(CONF_ID): cv.int
    # vol.Optional(CONF_NAME, default=DEVICE_DEFAULT_NAME): cv.string,
    # vol.Required(CONF_HOST):
    # vol.Optional(CONF_PORT, default=DEFAULT_PORT)
    vol.Required(CONF_SENSORS): _SENSORS_SCHEMA
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Raspberry PI GPIO devices."""

    binary_sensors = []
    sensors = config.get(CONF_SENSORS)
    for sensor_id, sensor_name in sensors.items():
        binary_sensors.append(ConbeeBinarySensor(
            hass, sensor_id, sensor_name))
    add_devices(binary_sensors, True)

class ConbeeBinarySensor(BinarySensorDevice):
    """Represent a binary sensor that uses the websocket API of a conbee device."""

    def __init__(self, hass, sensor_id, sensor_name):
        """Initialize the RPi binary sensor."""
        # pylint: disable=no-member
        self._name = sensor_name or DEVICE_DEFAULT_NAME
        self.id = sensor_id
        self._state = None
        self.hass = hass

        def update_state(state):
            _LOGGER.debug("Setting state to {}".format(state))
            self._state = state
            self.schedule_update_ha_state()

        deconz.setup_sensor(self.hass, self.id, update_state)


    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the entity."""
        return self._state

    def update(self):
        """Update the GPIO state."""
