"""
Support for controlling an mpd-server as an alarm-clock.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/alarmclock/
"""
# pylint: disable=import-error
import logging

import voluptuous as vol

from homeassistant.const import (CONF_HOST, CONF_PORT, CONF_PASSWORD, SERVICE_TURN_OFF, SERVICE_TURN_ON)
import homeassistant.helpers.config_validation as cv

from datetime import datetime
from threading import Timer
import time
import logging

REQUIREMENTS = ['python-mpd2']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'alarmclock'

DEFAULT_PORT = 6600

ATTR_MIN_VOL = 'min_volume'
ATTR_MAX_VOL = 'max_volume'
ATTR_DURATION = 'duration'

ALARM_TURN_ON_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    ATTR_MIN_VOL: vol.All(vol.Coerce(int), vol.Clamp(min=0, max=100)),
    ATTR_MAX_VOL: vol.All(vol.Coerce(int), vol.Clamp(min=0, max=100)),
    ATTR_DURATION: vol.Coerce(int),
})
ALARM_TURN_OFF_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
})

def mpd_connect(host, port, password):
    from mpd import MPDClient
    client = MPDClient()
    client.timeout = 10
    client.idletimeout = None
    client.connect(host, port)
    if password:
        client.password(password)
    return client

def ramp_up(client, min_volume, max_volume, duration):
    interval = duration / (max_volume - min_volume)
    for vol in range(min_volume, max_volume+1):
        time.sleep(interval)
        client.setvol(vol)
        _LOGGER.info("Volume set to %d", vol)


def turn_on(hass, host=None, port=None, password=None, min_volume=None, max_volume=None, duration=None):
    _LOGGER.info("### turning on")
    client = mpd_connect(host, port, password)
    client.setvol(min_volume)
    client.play()
    client.next()
    ramp_up(client, min_volume, max_volume, duration)
    client.disconnect()

def turn_off(hass, host=None, port=None, password=None):
    client = mpd_connect(host, port, password)
    client.stop()
    client.disconnect()

def setup(hass, config):
    def handle_alarm_service(service):
        # Get the validated data
        params = service.data.copy()
        _LOGGER.info("#### %s", params)

        if service.service == SERVICE_TURN_ON:
            turn_on(hass, **params)
        elif service.service == SERVICE_TURN_OFF:
            turn_off(hass, **params)

    hass.services.register(DOMAIN, SERVICE_TURN_OFF, handle_alarm_service, schema=ALARM_TURN_OFF_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_TURN_ON, handle_alarm_service, schema=ALARM_TURN_ON_SCHEMA)
    return True

from mpd import MPDClient
