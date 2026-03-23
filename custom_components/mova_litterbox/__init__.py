import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MovaApiClient, MovaApiError, MovaAuthError
from .const import (
    CONF_COUNTRY,
    CONF_DID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MovaLitterboxCoordinator

_LOGGER = logging.getLogger(__name__)

type MovaConfigEntry = ConfigEntry[MovaLitterboxCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MovaConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = MovaApiClient(
        session=session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        country=entry.data[CONF_COUNTRY],
        region=entry.data.get(CONF_REGION),
    )
    client.did = entry.data[CONF_DID]

    stored_refresh = entry.data.get(CONF_REFRESH_TOKEN)
    if stored_refresh:
        client._refresh_token_value = stored_refresh

    try:
        await client.ensure_token()
    except MovaAuthError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except MovaApiError as err:
        raise ConfigEntryNotReady(f"Failed to connect to MOVA: {err}") from err

    if client.refresh_token_value != stored_refresh:
        new_data = {**entry.data, CONF_REFRESH_TOKEN: client.refresh_token_value}
        hass.config_entries.async_update_entry(entry, data=new_data)

    timezone = hass.config.time_zone

    coordinator = MovaLitterboxCoordinator(hass, client, entry, timezone)
    try:
        await coordinator.async_setup()
    except (MovaApiError, MovaAuthError) as err:
        raise ConfigEntryNotReady(f"Failed to set up MOVA: {err}") from err
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MovaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
