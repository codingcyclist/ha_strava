"""Sensor platform for HA Strava"""
from datetime import datetime as dt
from aiohttp import ClientSession
import logging

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

from .const import (
    DOMAIN,
    CONF_STRAVA_UPDATE_EVENT,
    CONF_STRAVA_RELOAD_EVENT,
    CONF_SENSORS,
    CONF_SENSOR_DATE,
    CONF_SENSOR_DURATION,
    CONF_SENSOR_PACE,
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
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    entries = [
        StravaSummaryStatsSensor(index, metric)
        for metric in CONF_SENSORS.keys()
        for index in range(MAX_NB_ACTIVITIES)
    ]

    async_add_entities(entries)

    # make a post request to the webhook enpoint to initiate a data refresh
    async with ClientSession() as websession:
        webhook_url = (
            f"{get_url(hass, allow_internal=False, allow_ip=False)}/api/strava/webhook"
        )
        post_response = await websession.post(url=webhook_url, data={})

        if post_response.status == 200 or post_response.status == 502:
            # fire event to make sure there is a webhook subscription even after the sensor platform was
            # reloaded (e.g. when the user changed config options)
            hass.bus.fire(CONF_STRAVA_RELOAD_EVENT, {"component": DOMAIN})
            return

        _LOGGER.warning(
            f"Could reach webhook endpoint at {webhook_url} | Error code: {post_response.status} - {await post_response.text()}"
        )

    return


class StravaSummaryStatsSensor(Entity):
    _data = None
    _icon = None
    _metric = None
    _activity_index = None
    _activity_type = None

    def __init__(self, activityindex, metric):
        self._metric = metric
        self._activity_index = int(activityindex)

        self._icon = CONF_SENSORS[metric]["icon"]
        self.entity_id = f"{DOMAIN}.strava_{self._metric}_{self._activity_index}"

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
        return f"strava_{self._metric}_{self._activity_index}"

    @property
    def icon(self):
        if self._metric == CONF_SENSOR_DATE and self._activity_type:
            if self._activity_type == CONF_ACTIVITY_TYPE_RIDE:
                return "mdi:bike"
            if self._activity_type == CONF_ACTIVITY_TYPE_RUN:
                return "mdi:run"
        return self._icon

    @property
    def state(self):
        if not self._data:
            return -1
        return str(self._data["metric"])

    @property
    def name(self):
        if self._metric == CONF_SENSOR_DATE:
            return "Title & Date" if not self._data else self._data[CONF_SENSOR_TITLE]
        return "" + str.upper(self._metric[0]) + self._metric[1:]

    @property
    def should_poll(self):
        return False

    def strava_update_event_handler(self, event):
        """Handle Strava API data which is emmitted from a Strava Update Event"""
        activity = event.data["activities"][self._activity_index]

        self._activity_type = activity[CONF_SENSOR_ACTIVITY_TYPE]

        if self._metric == CONF_SENSOR_DATE:
            self._data = {
                "metric": f"{activity[CONF_SENSOR_TITLE]} | {activity[CONF_SENSOR_CITY]}",
                "title": f"{dt.strftime(activity[self._metric], '%d.%m. - %H:%M')}",
            }
        elif self._metric == CONF_SENSOR_DURATION:
            days = int(activity[CONF_SENSOR_MOVING_TIME] // (3600 * 24))
            hours = int(
                (activity[CONF_SENSOR_MOVING_TIME] - days * (3600 * 24)) // 3600
            )
            minutes = int(
                (activity[CONF_SENSOR_MOVING_TIME] - days * (3600 * 24) - hours * 3600)
                // 60
            )
            seconds = int(
                activity[CONF_SENSOR_MOVING_TIME]
                - days * (3600 * 24)
                - hours * 3600
                - minutes * 60
            )
            self._data = {
                "metric": ""
                + ("" if days == 0 else f"{days} Day(s), ")
                + ("" if hours == 0 and days == 0 else f"{hours:02}:")
                + ("" if minutes == 0 and hours == 0 else f"{minutes:02}:")
                + f"{seconds:02}"
            }

        elif self._metric == CONF_SENSOR_DISTANCE:
            distance = f"{round(activity[self._metric]/1000,2)}{LENGTH_KILOMETERS}"

            if not self.hass.config.units.is_metric:
                distance = f"{round(activity[self._metric]*FACTOR_METER_TO_MILE,2)}{LENGTH_MILES}"

            self._data = {"metric": distance}

        elif self._metric == CONF_SENSOR_PACE:
            pace = f"{round((activity[CONF_SENSOR_DISTANCE]/1000)/(activity[CONF_SENSOR_MOVING_TIME]/3600),2)}{SPEED_KILOMETERS_PER_HOUR}"

            if not self.hass.config.units.is_metric:
                pace = f"{round((activity[CONF_SENSOR_DISTANCE]*FACTOR_METER_TO_MILE)/(activity[CONF_SENSOR_MOVING_TIME]/3600),2)}{SPEED_MILES_PER_HOUR}"

            if activity[CONF_SENSOR_ACTIVITY_TYPE] == CONF_ACTIVITY_TYPE_RUN:
                pace = f"{round((activity[CONF_SENSOR_MOVING_TIME]/60)/(activity[CONF_SENSOR_DISTANCE]/1000),2)}{TIME_MINUTES}/{LENGTH_KILOMETERS}"

                if not self.hass.config.units.is_metric:
                    pace = f"{round((activity[CONF_SENSOR_MOVING_TIME]/60)/(activity[CONF_SENSOR_DISTANCE]*FACTOR_METER_TO_MILE),2)}{TIME_MINUTES}/{LENGTH_MILES}"

            self._data = {"metric": pace}

        elif self._metric == CONF_SENSOR_POWER:
            self._data = {"metric": f"{int(round(activity[CONF_SENSOR_POWER],0))}W"}

        elif self._metric == CONF_SENSOR_ELEVATION:
            elevation = f"{round(activity[CONF_SENSOR_ELEVATION],0)}{LENGTH_METERS}"
            if not self.hass.config.units.is_metric:
                elevation = f"{round(activity[CONF_SENSOR_ELEVATION]*FACTOR_METER_TO_FEET,0)}{LENGTH_FEET}"
            self._data = {"metric": elevation}

        else:
            self._data = {"metric": activity[self._metric]}

        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(
            CONF_STRAVA_UPDATE_EVENT, self.strava_update_event_handler
        )

    async def async_will_remove_from_hass(self):
        self.hass.bus._async_remove_listener(
            event_type=CONF_STRAVA_UPDATE_EVENT,
            listener=self.strava_update_event_handler,
        )

