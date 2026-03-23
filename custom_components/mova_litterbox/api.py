import base64
import hashlib
import json
import logging
import time
from typing import Any

import aiohttp

from .const import (
    AUTH_HEADER_BASIC,
    BASE_URLS,
    DEFAULT_REGION,
    ENDPOINT_AUTH_TOKEN,
    ENDPOINT_CONSUMABLES,
    ENDPOINT_DEVICE_INFO,
    ENDPOINT_DEVICE_LIST,
    ENDPOINT_PET_INFO,
    ENDPOINT_SEND_COMMAND,
    ENDPOINT_VISIT_DETAIL,
    ENDPOINT_VISIT_SUMMARY,
    PASSWORD_SALT,
    SIGN_SALT,
    TENANT_ID,
)

_LOGGER = logging.getLogger(__name__)


class MovaApiError(Exception):
    pass


class MovaAuthError(MovaApiError):
    pass


class MovaApiClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        country: str,
        region: str | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._country = country
        self._region = region or DEFAULT_REGION
        self._base_url = BASE_URLS.get(self._region, BASE_URLS[DEFAULT_REGION])
        self._access_token: str | None = None
        self._refresh_token_value: str | None = None
        self._token_expires_at: float = 0
        self._uid: str | None = None
        self._did: str | None = None
        self._request_id = 0

    @property
    def uid(self) -> str | None:
        return self._uid

    @property
    def did(self) -> str | None:
        return self._did

    @did.setter
    def did(self, value: str) -> None:
        self._did = value

    @property
    def region(self) -> str:
        return self._region

    @property
    def refresh_token_value(self) -> str | None:
        return self._refresh_token_value

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.md5((password + PASSWORD_SALT).encode()).hexdigest()

    @staticmethod
    def _sign_params(params: dict[str, Any]) -> str:
        sorted_keys = sorted(k for k in params if k != "sign")
        param_string = "&".join(f"{k}={params[k]}" for k in sorted_keys)
        return hashlib.md5((param_string + SIGN_SALT).encode()).hexdigest()

    def _auth_headers(self) -> dict[str, str]:
        return {
            "authorization": AUTH_HEADER_BASIC,
            "tenant-id": TENANT_ID,
            "content-type": "application/x-www-form-urlencoded",
        }

    @staticmethod
    def _extract_uid_from_jwt(token: str) -> str | None:
        try:
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get("uid") or payload.get("user_name") or payload.get("sub")
        except (IndexError, ValueError, json.JSONDecodeError):
            return None

    def _apply_token_response(self, body: dict[str, Any]) -> None:
        self._access_token = body["access_token"]
        self._refresh_token_value = body.get("refresh_token", self._refresh_token_value)
        self._token_expires_at = time.time() + body.get("expires_in", 7200) - 60

        uid = body.get("uid") or self._extract_uid_from_jwt(self._access_token)
        if uid:
            self._uid = str(uid)

        new_region = body.get("region")
        if new_region and new_region in BASE_URLS:
            self._region = new_region
            self._base_url = BASE_URLS[self._region]

    async def login(self) -> dict[str, Any]:
        """Log in with email and hashed password."""
        url = f"{self._base_url}{ENDPOINT_AUTH_TOKEN}"
        hashed = self._hash_password(self._password)
        data = (
            f"grant_type=password&scope=all&platform=ANDROID&type=account"
            f"&username={self._email}&password={hashed}"
            f"&country={self._country}&lang=en"
        )
        timeout = aiohttp.ClientTimeout(total=15)
        async with self._session.post(
            url, data=data, headers=self._auth_headers(), timeout=timeout
        ) as response:
            body = await response.json()
            if response.status == 400:
                error = body.get("error", "")
                description = body.get("error_description", "Login failed")
                if error == "invalid_user":
                    raise MovaAuthError("Invalid email or password")
                if error == "limit_attempts_unauthorized":
                    raise MovaAuthError("Account temporarily locked due to too many failed attempts")
                raise MovaAuthError(description)
            if response.status != 200:
                raise MovaApiError(f"Login failed with status {response.status}")

        self._apply_token_response(body)
        return body

    async def _refresh_access_token(self) -> dict[str, Any]:
        if not self._refresh_token_value:
            raise MovaAuthError("No refresh token available")

        url = f"{self._base_url}{ENDPOINT_AUTH_TOKEN}"
        data = f"grant_type=refresh_token&refresh_token={self._refresh_token_value}"
        timeout = aiohttp.ClientTimeout(total=15)
        async with self._session.post(
            url, data=data, headers=self._auth_headers(), timeout=timeout
        ) as response:
            body = await response.json()
            if response.status == 400:
                error = body.get("error_description", "Refresh token expired or invalid")
                raise MovaAuthError(error)
            if response.status != 200:
                raise MovaApiError(
                    f"Token refresh failed with status {response.status}"
                )

        self._apply_token_response(body)
        return body

    async def ensure_token(self) -> None:
        """Ensure we have a valid access token. Try refresh first, fall back to login."""
        if self._access_token and time.time() < self._token_expires_at:
            return

        if self._refresh_token_value:
            try:
                await self._refresh_access_token()
                return
            except MovaAuthError:
                _LOGGER.debug("Refresh token failed, falling back to login")

        await self.login()

    async def get_device_list(self) -> list[dict[str, Any]]:
        await self.ensure_token()
        url = f"{self._base_url}{ENDPOINT_DEVICE_LIST}"
        body = {
            "current": 1,
            "size": 200,
            "lang": "en",
            "sharedStatus": 1,
            "timestamp": self._timestamp(),
        }
        timeout = aiohttp.ClientTimeout(total=15)
        async with self._session.post(
            url, json=body, headers=self._headers(), timeout=timeout
        ) as response:
            if response.status == 401:
                raise MovaAuthError("Authentication failed")
            if response.status != 200:
                raise MovaApiError(
                    f"Device list request failed with status {response.status}"
                )
            result = await response.json()

        data = result.get("data", result)
        if isinstance(data, dict):
            page = data.get("page", data)
            if isinstance(page, dict):
                return page.get("records", [])
        return data if isinstance(data, list) else []

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": AUTH_HEADER_BASIC,
            "dreame-auth": self._access_token or "",
            "tenant-id": TENANT_ID,
            "content-type": "application/json; charset=utf-8",
        }

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _base_body(self) -> dict[str, Any]:
        return {
            "did": self._did,
            "uid": self._uid,
            "timestamp": self._timestamp(),
        }

    def _signed_body(self, body: dict[str, Any]) -> dict[str, Any]:
        body["sign"] = self._sign_params(body)
        return body

    async def _post(self, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
        await self.ensure_token()
        url = f"{self._base_url}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=15)
        async with self._session.post(
            url, json=body, headers=self._headers(), timeout=timeout
        ) as response:
            if response.status == 401:
                raise MovaAuthError("Authentication failed, token may be expired")
            if response.status != 200:
                raise MovaApiError(
                    f"API request failed with status {response.status}"
                )
            return await response.json()

    async def _get(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        await self.ensure_token()
        url = f"{self._base_url}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=15)
        async with self._session.get(
            url, params=params, headers=self._headers(), timeout=timeout
        ) as response:
            if response.status == 401:
                raise MovaAuthError("Authentication failed, token may be expired")
            if response.status != 200:
                raise MovaApiError(
                    f"API request failed with status {response.status}"
                )
            return await response.json()

    async def get_device_info(self) -> dict[str, Any]:
        body = self._base_body()
        result = await self._post(ENDPOINT_DEVICE_INFO, body)
        return result.get("data", result)

    async def get_pet_info(self) -> list[dict[str, Any]]:
        body = self._base_body()
        body["deviceFlag"] = 0
        result = await self._post(ENDPOINT_PET_INFO, body)
        data = result.get("data", result)
        if isinstance(data, dict):
            return data.get("petInfos", [])
        return data if isinstance(data, list) else []

    async def get_properties(
        self, params: list[tuple[int, int]]
    ) -> dict[tuple[int, int], Any]:
        """Fetch device properties via MIoT-style command.

        params: list of (siid, piid) tuples
        Returns: dict mapping (siid, piid) -> value
        """
        request_id = self._next_request_id()
        miot_params = [
            {"did": self._did, "siid": siid, "piid": piid}
            for siid, piid in params
        ]
        body = {
            "data": {
                "did": self._did,
                "from": "",
                "id": request_id,
                "method": "get_properties",
                "params": miot_params,
            },
            "did": self._did,
            "id": request_id,
            "timestamp": self._timestamp(),
        }
        result = await self._post(ENDPOINT_SEND_COMMAND, body)
        properties = {}
        result_data = result.get("data", result)
        if isinstance(result_data, dict):
            result_params = result_data.get("result", [])
        elif isinstance(result_data, list):
            result_params = result_data
        else:
            result_params = []
        for prop in result_params:
            key = (prop.get("siid"), prop.get("piid"))
            properties[key] = prop.get("value")
        return properties

    async def set_property(self, siid: int, piid: int, value: Any) -> dict[str, Any]:
        request_id = self._next_request_id()
        body = {
            "data": {
                "did": self._did,
                "from": "",
                "id": request_id,
                "method": "set_properties",
                "params": [
                    {
                        "did": self._did,
                        "siid": siid,
                        "piid": piid,
                        "value": value,
                    }
                ],
            },
            "did": self._did,
            "id": request_id,
            "timestamp": self._timestamp(),
        }
        return await self._post(ENDPOINT_SEND_COMMAND, body)

    async def get_visit_summary(
        self, date: str, timezone: str
    ) -> dict[str, Any]:
        """Fetch today's visit summary.

        date: format "YYYY/MM/DD"
        timezone: e.g. "Europe/Warsaw"
        """
        params = {
            "date": date,
            "zone": timezone,
            "did": self._did,
            "uid": self._uid,
        }
        result = await self._get(ENDPOINT_VISIT_SUMMARY, params)
        return result.get("data", result)

    async def get_visit_details(
        self,
        date: str,
        timezone: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        body = {
            "all": True,
            "date": date,
            "did": self._did,
            "filterType": 0,
            "pageNo": page,
            "pageSize": page_size,
            "petId": "",
            "uid": self._uid,
            "unknown": False,
            "zone": timezone,
            "timestamp": self._timestamp(),
        }
        result = await self._post(ENDPOINT_VISIT_DETAIL, body)
        data = result.get("data", result)
        if isinstance(data, dict):
            return data.get(
                "toiletDetailInfoRespList",
                data.get("records", data.get("list", [])),
            )
        return data if isinstance(data, list) else []

    async def get_consumables(self) -> list[dict[str, Any]]:
        url_endpoint = f"{ENDPOINT_CONSUMABLES}?did={self._did}"
        body = self._base_body()
        result = await self._post(url_endpoint, body)
        return result.get("data", result)
