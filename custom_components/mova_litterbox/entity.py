from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MovaLitterboxCoordinator


class MovaBaseEntity(CoordinatorEntity[MovaLitterboxCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._did = did
        self._attr_unique_id = f"{did}_{key}"
        self._attr_name = name

    @property
    def device_info(self) -> DeviceInfo:
        info = self.coordinator.device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self._did)},
            name=info.get("customName", "MOVA Litter Box"),
            manufacturer="MOVA",
            model=info.get("model", "Smart Litter Box"),
            sw_version=info.get("curVersion"),
            serial_number=info.get("sn"),
        )
