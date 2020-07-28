import logging
import os
from homeassistant.components.local_file.camera import LocalFile
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

    camera = LocalFile(DOMAIN, file_path)

    async_add_entities([camera])
