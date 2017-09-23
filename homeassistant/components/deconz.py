"""
Support for the deCONZ websocket API.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/deconz/
"""

import logging
import asyncio
import threading
import json

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['websocket-client']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'deconz'
DATA_INSTANCE = 'deconz_instance'
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "443"


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)


def setup_sensor(hass, id, update_state):
    inst = hass.data[DATA_INSTANCE]
    inst.setup_sensor(str(id), update_state)


@asyncio.coroutine
def async_setup(hass, config):
    """Set up the deCONZ websocket component."""
    from websocket import create_connection

    conf = config.get(DOMAIN, {})
    ws_url = "ws://{}:{}".format(conf.get(CONF_HOST), conf.get(CONF_PORT))

    _LOGGER.debug("Connecting to websocket...")
    websocket = create_connection(ws_url)

    instance = hass.data[DATA_INSTANCE] = Deconz(
        hass, websocket
    )
    instance.start()

    _LOGGER.debug("Setup complete")
    return True


class Deconz(threading.Thread):
    def __init__(self, hass: HomeAssistant, websocket) -> None:
        """ Initialize the websocket client."""

        threading.Thread.__init__(self, name='deconz')

        self.hass = hass
        self.websocket = websocket
        self._sensors = {}

    def setup_sensor(self, id, update_state):
        self._sensors[id] = update_state

    def run(self):
        _LOGGER.debug("Starting listener")

        def shutdown(event):
            _LOGGER.debug("Shutting down")
            self.websocket.close()
            self.websocket = None
            self.join()

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown)

        while self.websocket is not None:
            response = self.websocket.recv()
            if response is None or response == "":
                _LOGGER.debug("Disconnected?")
                break
            _LOGGER.debug("Response: {}".format(response))
            response_json = json.loads(response)

            try:
                id = response_json["id"]
                type = response_json["r"]
                state = response_json["state"]
            except KeyError as e:
                continue

            if type == "sensors":
                new_state = state["presence"] if "presence" in state else False
                _LOGGER.debug("Motion detected")
                if id in self._sensors:
                    self._sensors[id](new_state)
