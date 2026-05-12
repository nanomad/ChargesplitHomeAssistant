import logging

import requests
import urllib3

from .const import DOMAIN, CONF_CODE, CHARGEPOINT_SERIAL

_LOGGER = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_BASE_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "User-Agent": "Mozilla/5.0",
}


class ChargesplitApi:
    def __init__(self, code: str, serial: str) -> None:
        self.host = serial
        self.code = code
        self.serial = serial
        self.base_url = "https://europe-west1-chargesplithome.cloudfunctions.net/secureEndpoint"
        self.headers = {**_BASE_HEADERS, "Host": serial, "Origin": self.base_url}

    def get_data(self) -> bytes:
        response = requests.post(
            self.base_url,
            data={"SECRET": self.code, "SERIAL": self.serial},
            headers=self.headers,
            verify=False,
        )
        response.raise_for_status()
        return response.content

    def test_auth(self) -> None:
        response = requests.post(
            self.base_url,
            data={"SECRET": self.code, "SERIAL": self.serial},
            headers=self.headers,
            verify=False,
        )
        if response.status_code != 200:
            raise requests.ConnectionError(f"Auth failed with status {response.status_code}")

    def set_pilot_pwr(self, value: str) -> None:
        _LOGGER.debug("Calling API PILOTCHANGE with value: %s", value)
        requests.post(
            self.base_url,
            data={"SECRET": self.code, "SERIAL": self.serial, "COMMAND": "PILOTCHANGE", "VALUE": value},
            headers=self.headers,
            verify=False,
        ).raise_for_status()
