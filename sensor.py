"""Sensor platform for HA Strava"""
# generic imports
from datetime import datetime as dt
from aiohttp import ClientSession
import logging

# HASS imports
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.network import get_url
from homeassistant.const import (
    LENGTH_MILES,
    LENGTH_KILOMETERS,
    LENGTH_METERS,
    LENGTH_FEET,
    SPEED_KILOMETERS_PER_HOUR,
    SPEED_MILES_PER_HOUR,
    TIME_MINUTES,
)

# custom module imports
from .const import (
    DOMAIN,
    CONF_STRAVA_DATA_UPDATE_EVENT,
    CONF_STRAVA_RELOAD_EVENT,
    CONF_SENSORS,
    CONF_SENSOR_DATE,
    CONF_SENSOR_DURATION,
    CONF_SENSOR_PACE,
    CONF_SENSOR_SPEED,
    CONF_SENSOR_DISTANCE,
    CONF_SENSOR_KUDOS,
    CONF_SENSOR_CALORIES,
    CONF_SENSOR_ELEVATION,
    CONF_SENSOR_POWER,
    CONF_SENSOR_TROPHIES,
    CONF_SENSOR_TITLE,
    CONF_SENSOR_CITY,
    CONF_SENSOR_MOVING_TIME,
    CONF_SENSOR_ACTIVITY_TYPE,
    CONF_ACTIVITY_TYPE_RUN,
    CONF_ACTIVITY_TYPE_RIDE,
    FACTOR_METER_TO_MILE,
    FACTOR_METER_TO_FEET,
    DEFAULT_NB_ACTIVITIES,
    MAX_NB_ACTIVITIES,
    CONF_SENSOR_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """
    create 5+1 sensor entities for 10 devices
    all sensor entities are hidden by default
    """
    entries = [
        StravaSummaryStatsSensor(
            activity_index=activity_index, sensor_index=sensor_index
        )
        for sensor_index in range(6)
        for activity_index in range(MAX_NB_ACTIVITIES)
    ]

    async_add_entities(entries)

    # make a post request to the webhook enpoint to initiate a data refresh
    hass.bus.fire(CONF_STRAVA_RELOAD_EVENT, {"component": DOMAIN})
    return


class StravaSummaryStatsSensor(Entity):
    _data = None  # Strava activity data
    _activity_index = None  # range: 1-5

    def __init__(self, activity_index, sensor_index):
        self._sensor_index = sensor_index  # range: 0-9
        self._activity_index = int(activity_index)
        self.entity_id = f"{DOMAIN}.strava_{self._activity_index}_{self._sensor_index}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"strava_activity_{self._activity_index}")},
            "name": f"Strava Activity {self._activity_index}",
            "manufacturer": "Strava",
            "model": "Activity",
        }

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._activity_index < DEFAULT_NB_ACTIVITIES

    @property
    def available(self):
        return True

    @property
    def unique_id(self):
        return f"strava_{self._activity_index}_{self._sensor_index}"

    @property
    def icon(self):
        if not self._data:
            return "mdi:run"

        ha_strava_config_entries = self.hass.config_entries.async_entries(domain=DOMAIN)

        if len(ha_strava_config_entries) != 1:
            return "mdi:run"

        _LOGGER.debug(
            f"Activity Index: {self._activity_index} | Activity Type: {self._data[CONF_SENSOR_ACTIVITY_TYPE]}"
        )
        sensor_options = ha_strava_config_entries[0].options.get(
            self._data[CONF_SENSOR_ACTIVITY_TYPE], CONF_SENSOR_DEFAULT
        )

        if self._sensor_index == 0:
            return sensor_options["icon"]

        metric = list(sensor_options.values())[self._sensor_index]
        return CONF_SENSORS[metric]["icon"]

    @property
    def state(self):
        if not self._data:
            return -1

        ha_strava_config_entries = self.hass.config_entries.async_entries(domain=DOMAIN)

        if len(ha_strava_config_entries) != 1:
            return -1

        sensor_metrics = list(
            ha_strava_config_entries[0]
            .options.get(self._data[CONF_SENSOR_ACTIVITY_TYPE], CONF_SENSOR_DEFAULT)
            .values()
        )

        metric = sensor_metrics[self._sensor_index]

        if self._sensor_index == 0:
            return f"{self._data[CONF_SENSOR_TITLE]} | {self._data[CONF_SENSOR_CITY]}"

        if metric == CONF_SENSOR_DURATION:
            days = int(self._data[CONF_SENSOR_MOVING_TIME] // (3600 * 24))
            hours = int(
                (self._data[CONF_SENSOR_MOVING_TIME] - days * (3600 * 24)) // 3600
            )
            minutes = int(
                (
                    self._data[CONF_SENSOR_MOVING_TIME]
                    - days * (3600 * 24)
                    - hours * 3600
                )
                // 60
            )
            seconds = int(
                self._data[CONF_SENSOR_MOVING_TIME]
                - days * (3600 * 24)
                - hours * 3600
                - minutes * 60
            )
            return "".join(
                [
                    "" if days == 0 else f"{days} Day(s), ",
                    "" if hours == 0 and days == 0 else f"{hours:02}:",
                    "" if minutes == 0 and hours == 0 else f"{minutes:02}:",
                    f"{seconds:02}",
                ]
            )

        if metric == CONF_SENSOR_DISTANCE:
            distance = (
                f"{round(self._data[CONF_SENSOR_DISTANCE]/1000,2)} {LENGTH_KILOMETERS}"
            )

            if not self.hass.config.units.is_metric:
                distance = f"{round(self._data[CONF_SENSOR_DISTANCE]*FACTOR_METER_TO_MILE,2)} {LENGTH_MILES}"

            return distance

        if metric == CONF_SENSOR_PACE:
            pace = self._data[CONF_SENSOR_MOVING_TIME] / (
                self._data[CONF_SENSOR_DISTANCE] / 1000
            )
            unit = f"{TIME_MINUTES}/{LENGTH_KILOMETERS}"
            if not self.hass.config.units.is_metric:
                pace = (self._data[CONF_SENSOR_MOVING_TIME]) / (
                    self._data[CONF_SENSOR_DISTANCE] * FACTOR_METER_TO_MILE
                )
                unit = f"{TIME_MINUTES}/{LENGTH_MILES}"

            minutes = int(pace // 60)
            seconds = int(pace - minutes * 60)
            return "".join(
                ["" if minutes == 0 else f"{minutes:02}:", f"{seconds:02}", " ", unit]
            )

        if metric == CONF_SENSOR_SPEED:
            speed = f"{round((self._data[CONF_SENSOR_DISTANCE]/1000)/(self._data[CONF_SENSOR_MOVING_TIME]/3600),2)} {SPEED_KILOMETERS_PER_HOUR}"

            if not self.hass.config.units.is_metric:
                speed = f"{round((self._data[CONF_SENSOR_DISTANCE]*FACTOR_METER_TO_MILE)/(self._data[CONF_SENSOR_MOVING_TIME]/3600),2)} {SPEED_MILES_PER_HOUR}"
            return speed

        if metric == CONF_SENSOR_POWER:
            return f"{int(round(self._data[CONF_SENSOR_POWER],1))} W"

        if metric == CONF_SENSOR_ELEVATION:
            elevation = f"{round(self._data[CONF_SENSOR_ELEVATION],0)} {LENGTH_METERS}"
            if not self.hass.config.units.is_metric:
                elevation = f"{round(self._data[CONF_SENSOR_ELEVATION]*FACTOR_METER_TO_FEET,0)} {LENGTH_FEET}"
            return elevation

        return str(self._data[metric])

    @property
    def name(self):
        if self._sensor_index == 0:
            return (
                "Title & Date"
                if not self._data
                else f"{dt.strftime(self._data[CONF_SENSOR_DATE], '%d.%m. - %H:%M')}"
            )

        if not self._data:
            metric = list(CONF_SENSOR_DEFAULT.values())[self._sensor_index]
        else:
            ha_strava_config_entries = self.hass.config_entries.async_entries(
                domain=DOMAIN
            )

            if len(ha_strava_config_entries) != 1:
                return -1

            sensor_metrics = list(
                ha_strava_config_entries[0]
                .options.get(self._data[CONF_SENSOR_ACTIVITY_TYPE], CONF_SENSOR_DEFAULT)
                .values()
            )

            metric = sensor_metrics[self._sensor_index]

        return "" + str.upper(metric[0]) + metric[1:]

    @property
    def should_poll(self):
        return False

    def strava_data_update_event_handler(self, event):
        """Handle Strava API data which is emmitted from a Strava Update Event"""
        self._data = event.data["activities"][self._activity_index]
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(
            CONF_STRAVA_DATA_UPDATE_EVENT, self.strava_data_update_event_handler
        )

    async def async_will_remove_from_hass(self):
        self.hass.bus._async_remove_listener(
            event_type=CONF_STRAVA_DATA_UPDATE_EVENT,
            listener=self.strava_data_update_event_handler,
        )

