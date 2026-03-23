import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MovaApiClient, MovaApiError, MovaAuthError
from .const import (
    CONF_COUNTRY,
    CONF_DID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_UID,
    COUNTRY_CHOICES,
    DEFAULT_COUNTRY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRY_CHOICES),
    }
)


class MovaLitterboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    def __init__(self) -> None:
        self._client: MovaApiClient | None = None
        self._devices: list[dict[str, Any]] = []
        self._user_input: dict[str, Any] = {}
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = MovaApiClient(
                session=session,
                email=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
                country=user_input[CONF_COUNTRY],
            )
            try:
                await client.login()
                devices = await client.get_device_list()
            except MovaAuthError as err:
                error_msg = str(err)
                if "locked" in error_msg.lower() or "limit_attempts" in error_msg.lower():
                    errors["base"] = "account_locked"
                else:
                    errors["base"] = "invalid_auth"
            except (MovaApiError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "unknown"
            else:
                self._client = client
                self._user_input = user_input
                self._devices = devices

                if not devices:
                    errors["base"] = "no_devices"
                elif len(devices) == 1:
                    return await self._create_entry(devices[0])
                else:
                    return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            selected_did = user_input[CONF_DID]
            for device in self._devices:
                if device.get("did") == selected_did:
                    return await self._create_entry(device)
            return self.async_abort(reason="device_not_found")

        device_options = {
            device.get("did", ""): device.get("customName", device.get("model", device.get("did", "Unknown")))
            for device in self._devices
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DID): vol.In(device_options)}
            ),
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None
        existing_data = self._reauth_entry.data

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = MovaApiClient(
                session=session,
                email=existing_data[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
                country=existing_data[CONF_COUNTRY],
                region=existing_data.get(CONF_REGION),
            )
            try:
                await client.login()
            except MovaAuthError as err:
                error_msg = str(err)
                if "locked" in error_msg.lower() or "limit_attempts" in error_msg.lower():
                    errors["base"] = "account_locked"
                else:
                    errors["base"] = "invalid_auth"
            except (MovaApiError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauthentication")
                errors["base"] = "unknown"
            else:
                new_data = {
                    **existing_data,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_REFRESH_TOKEN: client.refresh_token_value,
                }
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, data=new_data
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={"email": existing_data[CONF_EMAIL]},
        )

    async def _create_entry(
        self, device: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        did = device.get("did", "")
        await self.async_set_unique_id(did)
        self._abort_if_unique_id_configured()

        title = device.get("customName", "MOVA Litter Box")
        data = {
            CONF_EMAIL: self._user_input[CONF_EMAIL],
            CONF_PASSWORD: self._user_input[CONF_PASSWORD],
            CONF_COUNTRY: self._user_input[CONF_COUNTRY],
            CONF_REGION: self._client.region,
            CONF_UID: self._client.uid,
            CONF_DID: did,
            CONF_REFRESH_TOKEN: self._client.refresh_token_value,
        }
        return self.async_create_entry(title=title, data=data)
