import logging
from homeassistant.components.camera import Camera
import requests
import os
from homeassistant.components.local_file.camera import LocalFile
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Camera that works with local files."""
    if "assets" not in os.listdir("./"):
        os.mkdir("./assets")

    folder_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], "assets")
    _LOGGER.debug(f"folder path: {folder_path}")
    file_path = None
    if len(os.listdir(folder_path)) > 0:
        file_path = os.path.join(folder_path, os.listdir(folder_path)[0])

    camera = UrlCam(name=DOMAIN)

    async_add_entities([camera])


class UrlCam(Camera):
    """Representation of a local file camera."""

    def __init__(self, name: str):
        """Initialize Local File Camera component."""
        super().__init__()

        self._name = name
        self._urls = []
        self._url_index = 0
        self._default_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/No_image_available_600_x_450.svg/1280px-No_image_available_600_x_450.svg.png"
        self._max_images = 100

    def _return_default_img(self):
        img_response = requests.get(url=self._default_url)
        return img_response.content

    def is_url_valid(self, url):
        img_response = requests.get(url=self._urls[self._url_index])
        if img_response.status_code == 200:
            return True
        _LOGGER.error(
            f"{url} did not return a valid imgage | Response: {img_response.status_code}"
        )
        return False

    def camera_image(self):
        """Return image response."""

        if len(self._urls) == self._url_index:
            _LOGGER.debug("No custom image urls....serving default image")
            return self._return_default_img()

        img_response = requests.get(url=self._urls[self._url_index])
        if img_response.status_code == 200:
            return img_response.content
        else:
            _LOGGER.error(
                f"{self._urls[self._url_index]} did not return a valid imgage | Response: {img_response.status_code}"
            )
            return self._return_default_img()

    def append_img_url(self, img_url):
        if not self.is_url_valid(url=img_url):
            return

        if len(self._urls) == self._max_images:
            self._urls = [*self._urls[1:], img_url]
        else:
            self._urls = [*self._urls, img_url]
        return

    def rotate_img(self):
        self._url_index = (self._url_index + 1) % len(self._urls)
        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the camera state attributes."""
        if len(self._urls) == self._url_index:
            return {"img_url": self._default_url}
        return {"img_url": self._urls[self._url_index]}
