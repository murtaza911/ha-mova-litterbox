import logging
from datetime import timedelta
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_integration

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
CARD_PATH = "/mova_litterbox/mova-litter-card.js"

type MovaConfigEntry = ConfigEntry[MovaLitterboxCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve and register the bundled dashboard card once per Home Assistant run."""
    card_file = Path(__file__).parent / "frontend" / "mova-litter-card.js"
    if not card_file.is_file():
        _LOGGER.warning("MOVA dashboard card is missing from the installation")
        return True

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_PATH, str(card_file), False)]
    )

    lovelace = hass.data.get("lovelace")
    if lovelace is None or lovelace.resource_mode != "storage":
        _LOGGER.info(
            "MOVA card is served at %s; YAML resource mode requires a manual resource entry",
            CARD_PATH,
        )
        return True

    resources = lovelace.resources
    # Never read or write a lazy resource collection before loading its saved data.
    if not resources.loaded:
        await resources.async_load()
    integration = await async_get_integration(hass, DOMAIN)
    desired_url = f"{CARD_PATH}?v={integration.version}"
    existing = next(
        (item for item in resources.async_items()
         if item["url"].split("?", 1)[0] == CARD_PATH),
        None,
    )
    if existing is None:
        await resources.async_create_item({"res_type": "module", "url": desired_url})
    elif existing["url"] != desired_url or existing["res_type"] != "module":
        await resources.async_update_item(
            existing["id"], {"res_type": "module", "url": desired_url}
        )
    return True


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
    await coordinator.async_load_bag_tracker()
    try:
        await coordinator.async_setup()
    except (MovaApiError, MovaAuthError) as err:
        raise ConfigEntryNotReady(f"Failed to set up MOVA: {err}") from err
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        async_track_time_interval(hass, coordinator.async_check_bag_reminder, timedelta(hours=1))
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MovaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
