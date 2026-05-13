import logging

import requests

_LOGGER = logging.getLogger(__name__)

_BASE_URL = "https://europe-west1-chargesplithome.cloudfunctions.net/secureEndpoint"


class ChargesplitApi:
    def __init__(self, code: str, serial: str) -> None:
        self.code = code
        self.serial = serial

    def get_data(self) -> bytes:
        response = requests.post(_BASE_URL, data={"SECRET": self.code, "SERIAL": self.serial})
        response.raise_for_status()
        return response.content

    def test_auth(self) -> None:
        response = requests.post(_BASE_URL, data={"SECRET": self.code, "SERIAL": self.serial})
        if response.status_code != 200:
            raise requests.ConnectionError(f"Auth failed with status {response.status_code}")

    def set_pilot_pwr(self, value: str) -> None:
        _LOGGER.debug("Calling API PILOTCHANGE with value: %s", value)
        requests.post(
            _BASE_URL,
            data={"SECRET": self.code, "SERIAL": self.serial, "COMMAND": "PILOTCHANGE", "VALUE": value},
        ).raise_for_status()
