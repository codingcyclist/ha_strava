"""The Strava Home Assistant integration."""
import asyncio
import logging
import json
from typing import Callable
from json import JSONDecodeError
import voluptuous as vol
from aiohttp.web import json_response, Response, Request
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant import data_entry_flow
from aiohttp import ClientSession
from datetime import datetime as dt

from homeassistant.helpers.network import get_url, NoURLAvailableError


from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    HTTP_OK,
    CONF_WEBHOOK_ID,
    EVENT_COMPONENT_LOADED,
    EVENT_CORE_CONFIG_UPDATE,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.components.http.view import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
)

from .config_flow import OAuth2FlowHandler
from .const import (
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
    WEBHOOK_SUBSCRIPTION_URL,
    CONF_CALLBACK_URL,
    AUTH_CALLBACK_PATH,
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
    CONF_STRAVA_UPDATE_EVENT,
    CONF_STRAVA_RELOAD_EVENT,
    MAX_NB_ACTIVITIES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

"""
class StravaSubscribeView(HomeAssistantView):
    url = "/api/strava/webhook"
    name = "api:strava:webhook"
    requires_auth = False
    cors_allowed = True

    def __init__(self):
        pass

    async def get(self, request):
        webhook_subscription_challenge = request.query.get("hub.challenge", None)
        if webhook_subscription_challenge:
            return json_response(
                status=HTTP_OK, data={"hub.challenge": webhook_subscription_challenge}
            )

        return Response(status=HTTP_OK)

"""


class StravaWebhookView(HomeAssistantView):
    url = "/api/strava/webhook"
    name = "api:strava:webhook"
    requires_auth = False
    cors_allowed = True

    def __init__(
        self,
        websession: config_entry_oauth2_flow.OAuth2Session,
        event_factory: Callable,
        host: str,
        hass: HomeAssistant,
    ):
        """Init the view."""
        self.websession = websession
        self.event_factory = event_factory
        self.webhook_id = None
        self.host = host
        self.hass = hass

    async def fetch_strava_data(self):
        """
        Fetches data for the latest activities from the Strava API
        Fetches location data for these activities from https://geocode.xyz
        Fires a Strava Update Event for Sensors to listen to
        """

        _LOGGER.debug("Fetching Data from Strava API")

        activities_response = await self.websession.async_request(
            method="GET",
            url=f"https://www.strava.com/api/v3/athlete/activities?per_page={MAX_NB_ACTIVITIES}",
        )

        if activities_response.status == 200:
            activities = json.loads(await activities_response.text())

            cities = []
            for activity in activities:
                geo_location_response = await self.websession.async_request(
                    method="GET",
                    url=f'https://geocode.xyz/{activity.get("start_latitude", 0)},{activity.get("start_longitude", 0)}?geoit=json',
                )
                geo_location = json.loads(await geo_location_response.text())
                city = geo_location.get("city", None)
                if city:
                    cities.append(city)
                else:
                    cities.append(geo_location.get("name", "Paradise City"))

            activities = sorted(
                [
                    {
                        CONF_SENSOR_TITLE: activity.get("name", "Strava Activity"),
                        CONF_SENSOR_CITY: cities[idx],
                        CONF_SENSOR_ACTIVITY_TYPE: activity.get("type", "Ride"),
                        CONF_SENSOR_DISTANCE: float(activity.get("distance", -1)),
                        CONF_SENSOR_DATE: dt.strptime(
                            activity.get("start_date_local", "2000-01-01T00:00:00Z"),
                            "%Y-%m-%dT%H:%M:%SZ",
                        ),
                        CONF_SENSOR_DURATION: float(activity.get("elapsed_time", -1)),
                        CONF_SENSOR_MOVING_TIME: float(activity.get("moving_time", -1)),
                        CONF_SENSOR_KUDOS: int(activity.get("kudos_count", -1)),
                        CONF_SENSOR_CALORIES: int(activity.get("kilojoules", -1)),
                        CONF_SENSOR_ELEVATION: int(
                            activity.get("total_elevation_gain", -1)
                        ),
                        CONF_SENSOR_POWER: float(activity.get("average_watts", -1)),
                        CONF_SENSOR_TROPHIES: int(
                            activity.get("achievement_count", -1)
                        ),
                    }
                    for idx, activity in enumerate(activities)
                ],
                key=lambda activity: activity[CONF_SENSOR_DATE],
                reverse=True,
            )

        else:
            _LOGGER.error(
                f"Could not fetch strava activities (response code: {activities_response.status}): {await activities_response.text()}"
            )
            return

        self.event_factory({"activities": activities})
        return

    async def get(self, request):
        """Handle the incoming webhook challenge"""
        webhook_subscription_challenge = request.query.get("hub.challenge", None)
        if webhook_subscription_challenge:
            return json_response(
                status=HTTP_OK, data={"hub.challenge": webhook_subscription_challenge}
            )

        return Response(status=HTTP_OK)

    async def post(self, request: Request):
        """Handle incoming post request"""
        request_host = request.headers.get("Host", None)

        try:
            data = await request.json()
            webhook_id = int(data.get("subscription_id", -1))
        except JSONDecodeError:
            webhook_id = -1

        _LOGGER.debug(
            f"Strava Webhook Endppoint received a POST request from: {request_host}"
        )

        if webhook_id == self.webhook_id or request_host in self.host:
            # create asychronous task to meet the 2 sec response time
            self.hass.async_create_task(self.fetch_strava_data())

        # always return a 200 response
        return Response(status=HTTP_OK)


async def renew_webhook_subscription(
    hass: HomeAssistant, entry: ConfigEntry, webhook_view: StravaWebhookView
):

    config_data = {
        **entry.data,
    }
    try:
        ha_host = get_url(hass, allow_internal=False, allow_ip=False)
    except NoURLAvailableError:
        _LOGGER.error(
            "Your Home Assistant Instance does not seem to have a public URL. The Strava Home Assistant integration requires a public URL"
        )
        return

    config_data[CONF_CALLBACK_URL] = f"{ha_host}/api/strava/webhook"

    async with ClientSession() as websession:
        callback_response = await websession.get(url=config_data[CONF_CALLBACK_URL])

        if callback_response.status != 200:
            _LOGGER.error(
                f"HA Callback URL for Strava Webhook not available: {await callback_response.text()}"
            )
            return

        existing_webhook_subscriptions_response = await websession.get(
            url=WEBHOOK_SUBSCRIPTION_URL,
            params={
                "client_id": entry.data[CONF_CLIENT_ID],
                "client_secret": entry.data[CONF_CLIENT_SECRET],
            },
        )

        existing_webhook_subscriptions = json.loads(
            await existing_webhook_subscriptions_response.text()
        )

        if len(existing_webhook_subscriptions) == 1:
            if (
                config_data[CONF_CALLBACK_URL]
                != existing_webhook_subscriptions[0][CONF_CALLBACK_URL]
            ):
                _LOGGER.debug(
                    f"Deleting outdated Strava Webhook Subscription for {existing_webhook_subscriptions[0][CONF_CALLBACK_URL]}"
                )

                delete_response = await websession.delete(
                    url=WEBHOOK_SUBSCRIPTION_URL + f"/{config_data[CONF_WEBHOOK_ID]}",
                    data={
                        "client_id": config_data[CONF_CLIENT_ID],
                        "client_secret": config_data[CONF_CLIENT_SECRET],
                    },
                )

                if delete_response.status == 204:
                    _LOGGER.debug(
                        "Successfully deleted outdated Strava Webhook Subscription"
                    )
                    existing_webhook_subscriptions = []
                else:
                    _LOGGER.error(
                        f"Unexpected response (status code: {delete_response.status}) while deleting Strava Webhook Subscription: {await delete_response.text()}"
                    )
                    return

        elif len(existing_webhook_subscriptions) == 0:
            _LOGGER.debug(
                f"Creating a new Strava Webhook subscription for {config_data[CONF_CALLBACK_URL]}"
            )
            post_response = await websession.post(
                url=WEBHOOK_SUBSCRIPTION_URL,
                data={
                    CONF_CLIENT_ID: config_data[CONF_CLIENT_ID],
                    CONF_CLIENT_SECRET: config_data[CONF_CLIENT_SECRET],
                    CONF_CALLBACK_URL: config_data[CONF_CALLBACK_URL],
                    "verify_token": "HA_STRAVA",
                },
            )
            if post_response.status == 201:
                post_response_content = json.loads(await post_response.text())
                config_data[CONF_WEBHOOK_ID] = post_response_content["id"]
            else:
                _LOGGER.error(
                    f"Unexpected response (status code: {post_response.status}) while creating Strava Webhook Subscription: {await post_response.text()}"
                )
                return

        else:
            _LOGGER.error(
                f"Expected 1 existing Strava Webhook subscription for {config_data[CONF_CALLBACK_URL]}: Found {len(existing_webhook_subscriptions)}"
            )
            return

    hass.config_entries.async_update_entry(entry=entry, data=config_data)

    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """
    if DOMAIN not in config:
        return True

    #subscribe_view = StravaSubscribeView()
    #hass.http.register_view(subscribe_view)

    existing_config_entry = hass.config_entries.async_entries(DOMAIN)

    if len(existing_config_entry) == 1:
        OAuth2FlowHandler.async_register_implementation(
            hass,
            config_entry_oauth2_flow.LocalOAuth2Implementation(
                hass,
                DOMAIN,
                existing_config_entry[0].data[CONF_CLIENT_ID],
                existing_config_entry[0].data[CONF_CLIENT_SECRET],
                OAUTH2_AUTHORIZE,
                OAUTH2_TOKEN,
            ),
        )
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Set up Strava Home Assistant from a config entry.
    This function is called every time the system reboots
    """
    """
    try:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    except KeyError:
        _LOGGER.warning("HA Strava Component hasn't been set up in the UI")
        return True
    """

    # subscribe_view = StravaSubscribeView()
    # hass.http.register_view(subscribe_view)

    try:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass=hass, config_entry=entry
        )
    except ValueError:
        implementation = config_entry_oauth2_flow.LocalOAuth2Implementation(
            hass,
            DOMAIN,
            entry.data[CONF_CLIENT_ID],
            entry.data[CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        )

        OAuth2FlowHandler.async_register_implementation(hass, implementation)

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    await session.async_ensure_token_valid()

    def strava_update_event_factory(data):
        hass.bus.fire(CONF_STRAVA_UPDATE_EVENT, data)

    strava_webhook_view = StravaWebhookView(
        websession=session,
        event_factory=strava_update_event_factory,
        host=get_url(hass, allow_internal=False, allow_ip=False),
        hass=hass,
    )

    hass.http.register_view(strava_webhook_view)

    async def strava_startup_functions():
        await renew_webhook_subscription(
            hass=hass, entry=entry, webhook_view=strava_webhook_view
        )
        await strava_webhook_view.fetch_strava_data()
        return True

    def ha_start_handler(event):
        _LOGGER.debug("HA Start Handler fired")
        hass.async_create_task(strava_startup_functions())

    def component_init_handler(event):
        _LOGGER.debug("Component Init Handler fired")
        if event.data.get("component", "") == DOMAIN:
            hass.async_create_task(strava_startup_functions())

    def component_reload_handler(event):
        _LOGGER.debug("Component Reload Handler fired")
        hass.async_create_task(strava_startup_functions())

    def core_config_update_handler(event):
        _LOGGER.debug("Config Update Handler fired")
        if "external_url" in event.data.keys():
            hass.async_create_task(
                renew_webhook_subscription(
                    hass=hass, entry=entry, webhook_view=strava_webhook_view
                )
            )
        if "unit_system" in event.data.keys():
            hass.async_create_task(strava_webhook_view.fetch_strava_data())

    hass.bus.async_listen(EVENT_HOMEASSISTANT_START, ha_start_handler)
    hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, core_config_update_handler)
    hass.bus.async_listen(EVENT_COMPONENT_LOADED, component_init_handler)
    if hass.bus.async_listeners().get(CONF_STRAVA_RELOAD_EVENT, 0) < 1:
        hass.bus.async_listen(CONF_STRAVA_RELOAD_EVENT, component_reload_handler)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )

    async with ClientSession() as websession:
        # delete strava webhook subscription
        delete_response = await websession.delete(
            url=WEBHOOK_SUBSCRIPTION_URL + f"/{entry.data[CONF_WEBHOOK_ID]}",
            data={
                "client_id": entry.data[CONF_CLIENT_ID],
                "client_secret": entry.data[CONF_CLIENT_SECRET],
            },
        )

        if delete_response.status == 204:
            _LOGGER.debug(
                f"Successfully deleted strava webhook subscription for {entry.data[CONF_CALLBACK_URL]}"
            )
        else:
            _LOGGER.warn(
                f"Strava webhook for {entry.data[CONF_CALLBACK_URL]} could not be deleted: {await delete_response.text()}"
            )
            return False

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        del implementation
        del entry

    return unload_ok


class StravaOAuth2Imlementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    @property
    def redirect_uri(self) -> str:
        """Return the redirect uri."""
        return f"{get_url(self.hass, allow_internal=False, allow_ip=False)}{AUTH_CALLBACK_PATH}"
