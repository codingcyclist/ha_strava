import logging
from homeassistant.components.camera import Camera
import requests
import os
from homeassistant.components.local_file.camera import LocalFile
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN,
    CONF_PHOTOS_ENTITY,
    CONF_PHOTOS,
    CONF_IMG_UPDATE_EVENT,
    CONF_IMG_ROTATE_EVENT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Camera that works with images from the web."""
    camera = UrlCam(name=DOMAIN)
    _LOGGER.debug(f"config entry: {config_entry}")
    if not config_entry.data.get(CONF_PHOTOS, False):
        camera.disabled_by = "user"
    async_add_entities([camera])
    return


class UrlCam(Camera):
    """Representation of a URL camera."""

    def __init__(self, name: str):
        """Initialize Local File Camera component."""
        super().__init__()

        self._name = name
        self._urls = []
        self._url_index = 0
        self._default_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/No_image_available_600_x_450.svg/1280px-No_image_available_600_x_450.svg.png"
        self._max_images = 100
        self._rotate_img = False

    def _return_default_img(self):
        img_response = requests.get(url=self._default_url)
        return img_response.content

    def is_url_valid(self, url):
        img_response = requests.get(url=url)
        if img_response.status_code == 200:
            return True
        _LOGGER.error(
            f"{url} did not return a valid imgage | Response: {img_response.status_code}"
        )
        return False

    def camera_image(self):
        """Return image response."""
        if self._rotate_img:
            self.rotate_img()
        self._rotate_img = not self._rotate_img

        if len(self._urls) == self._url_index:
            _LOGGER.debug("No custom image urls....serving default image")
            return self._return_default_img()

        img_response = requests.get(url=self._urls[self._url_index]["url"])
        if img_response.status_code == 200:
            return img_response.content
        else:
            _LOGGER.error(
                f"{self._urls[self._url_index]['url']} did not return a valid imgage | Response: {img_response.status_code}"
            )
            return self._return_default_img()

    def rotate_img(self):
        self._url_index = (self._url_index + 1) % len(self._urls)
        self.schedule_update_ha_state()

    @property
    def state(self):
        _LOGGER.debug("Camera state called!")
        if len(self._urls) == self._url_index:
            return self._default_url
        return self._urls[self._url_index]["url"]

    @property
    def unique_id(self):
        return CONF_PHOTOS_ENTITY

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the camera state attributes."""
        if len(self._urls) == self._url_index:
            return {"img_url": self._default_url}
        return {"img_url": self._urls[self._url_index]["url"]}

    def img_update_handler(self, event):
        """handle new urls of Strava images"""
        img_urls = []

        for img_url in event.data["img_urls"]:
            if self.is_url_valid(url=img_url["url"]):
                img_urls.append(img_url)

        img_urls = sorted(
            [*event.data["img_urls"], *self._urls], key=lambda img_url: img_url["date"]
        )
        self._urls = img_urls[-self._max_images :]
        return

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(CONF_IMG_UPDATE_EVENT, self.img_update_handler)

    async def async_will_remove_from_hass(self):
        self.hass.bus._async_remove_listener(
            event_type=CONF_IMG_UPDATE_EVENT, listener=self.img_update_handler,
        )

