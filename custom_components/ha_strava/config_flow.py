"""Config flow for Strava Home Assistant."""
import logging
import asyncio
import aiohttp
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.entity_registry import (
    async_get_registry,
    async_entries_for_config_entry,
)

# from homeassistant.helpers.device_registry import async_get_registry
from homeassistant.helpers.network import get_url, NoURLAvailableError
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, HTTP_OK
from .sensor import StravaSummaryStatsSensor
import aiohttp
from .const import (
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
    WEBHOOK_SUBSCRIPTION_URL,
    CONF_WEBHOOK_ID,
    CONF_CALLBACK_URL,
    CONF_NB_ACTIVITIES,
    DEFAULT_NB_ACTIVITIES,
    MAX_NB_ACTIVITIES,
)

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        ha_strava_config_entries = self.hass.config_entries.async_entries(domain=DOMAIN)

        if len(ha_strava_config_entries) != 1:
            return self.async_abort(reason="no_config")

        if user_input is not None:
            # await self.hass.config_entries.async_remove(
            #    entry_id=ha_strava_config_entries[0].entry_id
            # )
            # _device_registry = await async_get_registry(hass=self.hass)
            _entity_registry = await async_get_registry(hass=self.hass)
            entities = async_entries_for_config_entry(
                registry=_entity_registry,
                config_entry_id=ha_strava_config_entries[0].entry_id,
            )
            for entity in entities:
                if int(entity.entity_id.split("_")[-1]) >= int(
                    user_input[CONF_NB_ACTIVITIES]
                ):
                    _LOGGER.debug(f"disabling entity {entity}")
                    _entity_registry.async_update_entity(
                        entity.entity_id, disabled_by="user"
                    )
                else:
                    _entity_registry.async_update_entity(
                        entity.entity_id, disabled_by=None
                    )

            return self.async_create_entry(
                title=ha_strava_config_entries[0].title,
                data={CONF_NB_ACTIVITIES: user_input[CONF_NB_ACTIVITIES]},
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NB_ACTIVITIES,
                        default=ha_strava_config_entries[0].options.get(
                            CONF_NB_ACTIVITIES, DEFAULT_NB_ACTIVITIES
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=1,
                            max=MAX_NB_ACTIVITIES,
                            msg=f"max = {MAX_NB_ACTIVITIES}",
                        ),
                    )
                }
            ),
        )


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Strava Home Assistant OAuth2 authentication."""

    DOMAIN = DOMAIN
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "scope": "activity:read",
            "approval_prompt": "force",
            "response_type": "code",
        }

    async def async_step_renew_webhook_subscription(self, data):
        _LOGGER.debug("renew webhook subscription")
        return

    async def async_step_get_oauth_info(self, user_input=None):
        data_schema = {
            vol.Required(CONF_CLIENT_ID): str,
            vol.Required(CONF_CLIENT_SECRET): str,
        }

        assert self.hass is not None

        if self.hass.config_entries.async_entries(self.DOMAIN):
            return self.async_abort(reason="already_configured")

        try:
            get_url(self.hass, allow_internal=False, allow_ip=False)
        except NoURLAvailableError:
            return self.async_abort(reason="no_public_url")

        if user_input is not None:
            config_entry_oauth2_flow.async_register_implementation(
                self.hass,
                DOMAIN,
                config_entry_oauth2_flow.LocalOAuth2Implementation(
                    self.hass,
                    DOMAIN,
                    user_input[CONF_CLIENT_ID],
                    user_input[CONF_CLIENT_SECRET],
                    OAUTH2_AUTHORIZE,
                    OAUTH2_TOKEN,
                ),
            )
            return await self.async_step_pick_implementation()

        return self.async_show_form(
            step_id="get_oauth_info", data_schema=vol.Schema(data_schema)
        )

    async def async_oauth_create_entry(self, data: dict) -> dict:
        data[
            CONF_CALLBACK_URL
        ] = f"{get_url(self.hass, allow_internal=False, allow_ip=False)}/api/strava/webhook"
        data[CONF_CLIENT_ID] = self.flow_impl.client_id
        data[CONF_CLIENT_SECRET] = self.flow_impl.client_secret
        """
        async with aiohttp.ClientSession() as websession:

            post_response = await websession.post(
                url=WEBHOOK_SUBSCRIPTION_URL,
                data={
                    "client_id": self.flow_impl.client_id,
                    "client_secret": self.flow_impl.client_secret,
                    "callback_url": data[CONF_CALLBACK_URL],
                    "verify_token": "HA_STRAVA",
                },
            )
            if post_response.status == 400:
                post_response_content = await post_response.text()

                if "exists" in json.loads(post_response_content)["errors"][0]["code"]:
                    _LOGGER.debug(
                        f"a strava webhook subscription for {data[CONF_CALLBACK_URL]} already exists"
                    )
                else:
                    return self.async_abort(reason="webhook_fail")
            elif post_response.status == 201:
                data[CONF_WEBHOOK_ID] = json.loads(await post_response.text())["id"]
            else:
                _LOGGER.warning(
                    f"unexpected response (status code: {post_response.status}) while creating strava webhook subscription: {await post_response.text()}"
                )

        """
        return self.async_create_entry(title=self.flow_impl.name, data=data)

    async_step_user = async_step_get_oauth_info

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()
