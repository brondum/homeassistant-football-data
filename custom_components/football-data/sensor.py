import logging
from datetime import date, datetime, timedelta

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from pytz import timezone, utc

# default values
MAX_FIXTURES = 5
SCAN_INTERVAL = timedelta(seconds=360)
UPDATE_INTERVAL = 360
SENSOR_NAME = 'football_data'
_LOGGER = logging.getLogger(__name__)

# The schema for the configuration of the custom component
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required("api_key"): cv.string,
    vol.Required("team_id"): cv.string,
    vol.Optional("max_fixtures", default=MAX_FIXTURES): cv.positive_int,
    vol.Optional("update_interval", default=UPDATE_INTERVAL): cv.positive_int,
    vol.Optional("name", default=SENSOR_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    # Make sure discovery_info is not set
    assert discovery_info is None

    # Get the sensor name from the configuration
    name = config.get("name")
    _LOGGER.info("Setting up FootballData sensor with name: %s", name)

    add_devices([FootballData(hass, config, name)], True)


class FootballData(Entity):
    """Representation of an fixture sensor."""

    def __init__(self, hass, conf, name):
        """Initialize the sensor."""
        self._state = None
        self._name = name
        self.api_key = conf.get("api_key")
        self.max_fixtures = conf.get("max_fixtures")
        self.team_id = conf.get("team_id")
        # self.scan_interval = timedelta(seconds=conf.get("scan_interval"))
        self._tz = timezone(str(hass.config.time_zone))
        self.fixtures = []

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    # @property
    # def unique_id(self):
    #     """The unique id of the sensor."""
    #     return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['fixtures'] = self.fixtures,
        attributes['last_updated'] = datetime.now(tz=self._tz)

        return attributes

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.info(
            "Updating information for FootballData sensor: %s", self._name)

        # Make the HTTP request to the API
        headers = {
            "X-Auth-Token": self.api_key,
        }
        response = requests.get("https://api.football-data.org/v4/teams/" +
                                self.team_id + "/matches?status=SCHEDULED", headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract the fixtures from the response
        fixtures = []
        for match in data["matches"][:self.max_fixtures]:
            date = match["utcDate"]
            date = datetime.strptime(str(date), '%Y-%m-%dT%H:%M:%SZ')
            data = date.replace(tzinfo=utc).astimezone(self._tz)

            fixture = {
                "date": date,
                "date_formatted": date.strftime('%A, %d %b'),
                "kickoff": date.strftime('%H.%M'),
                "home_team": match["homeTeam"]["shortName"],
                "away_team": match["awayTeam"]["shortName"],
                "home_team_logo": match["homeTeam"]["crest"],
                "away_team_logo": match["awayTeam"]["crest"],
                "competition": match["competition"]["name"],
            }
            fixtures.append(fixture)

        self.fixtures = fixtures

        state = 'online'
        self._state = state
