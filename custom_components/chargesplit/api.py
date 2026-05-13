import logging

import requests

from .const import CONF_CODE, CHARGEPOINT_SERIAL

_LOGGER = logging.getLogger(__name__)

_BASE_URL = "https://europe-west1-chargesplithome.cloudfunctions.net/secureEndpoint"

_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "User-Agent": "Mozilla/5.0",
}


class ChargesplitApi:
    def __init__(self, code: str, serial: str) -> None:
        self.code = code
        self.serial = serial
        self.headers = {**_HEADERS, "Host": serial, "Origin": _BASE_URL}

    def get_data(self) -> bytes:
        with requests.Session() as session:
            response = session.post(_BASE_URL, data={"SECRET": self.code, "SERIAL": self.serial})
            response.raise_for_status()
            return response.content

    def test_auth(self) -> None:
        with requests.Session() as session:
            response = session.post(_BASE_URL, data={"SECRET": self.code, "SERIAL": self.serial})
            if response.status_code != 200:
                raise requests.ConnectionError(f"Auth failed with status {response.status_code}")

    def set_pilot_pwr(self, value: str) -> None:
        _LOGGER.debug("Calling API PILOTCHANGE with value: %s", value)
        with requests.Session() as session:
            session.post(
                _BASE_URL,
                data={"SECRET": self.code, "SERIAL": self.serial, "COMMAND": "PILOTCHANGE", "VALUE": value},
            ).raise_for_status()
