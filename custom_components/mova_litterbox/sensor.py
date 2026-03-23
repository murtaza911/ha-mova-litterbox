import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DID,
    CONSUMABLE_TYPE_MAP,
    DEVICE_STATUS_MAP,
    ERROR_CODE_MAP,
)
from .coordinator import MovaLitterboxCoordinator
from .entity import MovaBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MovaLitterboxCoordinator = entry.runtime_data
    did = entry.data[CONF_DID]

    entities: list[SensorEntity] = []

    entities.append(MovaVisitCountSensor(coordinator, did))
    entities.append(MovaAvgDurationSensor(coordinator, did))
    entities.append(MovaVisitDifferenceSensor(coordinator, did))
    entities.append(MovaDeviceStatusSensor(coordinator, did))
    entities.append(MovaErrorCodeSensor(coordinator, did))
    entities.append(MovaFirmwareVersionSensor(coordinator, did))
    entities.append(MovaSerialNumberSensor(coordinator, did))
    entities.append(MovaTimestampSensor(coordinator, did))
    entities.append(MovaDndScheduleSensor(coordinator, did))
    entities.append(MovaHexConfigSensor(coordinator, did))

    for pet in coordinator.pet_info:
        pet_id = pet.get("id", "")
        pet_name = pet.get("nickName", f"Pet {pet_id}")
        entities.append(MovaPetVisitCountSensor(coordinator, did, pet_id, pet_name))
        entities.append(MovaPetYesterdayVisitsSensor(coordinator, did, pet_id, pet_name))
        entities.append(MovaPetWeightSensor(coordinator, did, pet_id, pet_name))
        entities.append(MovaPetLastVisitSensor(coordinator, did, pet_id, pet_name))

    consumables = coordinator.data.get("consumables", [])
    if isinstance(consumables, list):
        for item in consumables:
            material_type = item.get("materialType")
            if material_type is not None:
                entities.append(
                    MovaConsumableSensor(coordinator, did, material_type)
                )

    entities.append(MovaLastVisitSensor(coordinator, did))

    async_add_entities(entities)


class MovaBaseSensor(MovaBaseEntity, SensorEntity):
    pass


class MovaVisitCountSensor(MovaBaseSensor):
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "visits_today", "Visits Today")

    @property
    def native_value(self) -> int | None:
        summary = self.coordinator.data.get("visit_summary", {})
        if isinstance(summary, dict):
            return summary.get("toiletsCount")
        return None


class MovaAvgDurationSensor(MovaBaseSensor):
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "avg_duration", "Average Visit Duration")

    @property
    def native_value(self) -> float | None:
        summary = self.coordinator.data.get("visit_summary", {})
        if isinstance(summary, dict):
            value = summary.get("durationAvg")
            if value is not None:
                return round(value / 1000, 1)
        return None


class MovaVisitDifferenceSensor(MovaBaseSensor):
    _attr_icon = "mdi:delta"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(
            coordinator, did, "visit_difference", "Visit Difference From Yesterday"
        )

    @property
    def native_value(self) -> int | None:
        summary = self.coordinator.data.get("visit_summary", {})
        if isinstance(summary, dict):
            return summary.get("toiletDifferenceCount")
        return None


class MovaDeviceStatusSensor(MovaBaseSensor):
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "device_status", "Device Status")

    @property
    def native_value(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((2, 1))
        if value is not None:
            return DEVICE_STATUS_MAP.get(value, str(value))
        return None


class MovaErrorCodeSensor(MovaBaseSensor):
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "error_code", "Error Code")

    @property
    def native_value(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((2, 2))
        if value is not None:
            return ERROR_CODE_MAP.get(value, str(value))
        return None


class MovaFirmwareVersionSensor(MovaBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "firmware_version", "Firmware Version")

    @property
    def native_value(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        return props.get((1, 4))


class MovaSerialNumberSensor(MovaBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:identifier"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "serial_number", "Serial Number")

    @property
    def native_value(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        return props.get((1, 5))


class MovaTimestampSensor(MovaBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "device_timestamp", "Device Timestamp")

    @property
    def native_value(self) -> int | None:
        props = self.coordinator.data.get("properties", {})
        return props.get((2, 5))


class MovaDndScheduleSensor(MovaBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "dnd_schedule", "DND Schedule")

    @property
    def native_value(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((3, 6))
        if value is not None:
            return str(value)
        return None


class MovaHexConfigSensor(MovaBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:code-braces"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "hex_config", "Hex Config")

    @property
    def native_value(self) -> str | None:
        props = self.coordinator.data.get("properties", {})
        value = props.get((3, 20))
        if value is not None:
            return str(value)
        return None


class MovaPetVisitCountSensor(MovaBaseSensor):
    _attr_icon = "mdi:cat"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        pet_id: str,
        pet_name: str,
    ) -> None:
        super().__init__(
            coordinator, did, f"pet_{pet_id}_visits", f"{pet_name} Visits Today"
        )
        self._pet_id = pet_id

    @property
    def entity_picture(self) -> str | None:
        return self.coordinator.data.get("pet_avatars", {}).get(str(self._pet_id))

    @property
    def native_value(self) -> int | None:
        summary = self.coordinator.data.get("visit_summary", {})
        if not isinstance(summary, dict):
            return None
        count_list = summary.get("currentCountList", [])
        if isinstance(count_list, list):
            for entry in count_list:
                if str(entry.get("petId")) == str(self._pet_id):
                    return entry.get("toiletsCount")
        return None


class MovaPetYesterdayVisitsSensor(MovaBaseSensor):
    _attr_icon = "mdi:cat"

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        pet_id: str,
        pet_name: str,
    ) -> None:
        super().__init__(
            coordinator,
            did,
            f"pet_{pet_id}_yesterday_visits",
            f"{pet_name} Visits Yesterday",
        )
        self._pet_id = pet_id

    @property
    def entity_picture(self) -> str | None:
        return self.coordinator.data.get("pet_avatars", {}).get(str(self._pet_id))

    @property
    def native_value(self) -> int | None:
        summary = self.coordinator.data.get("visit_summary", {})
        if not isinstance(summary, dict):
            return None
        count_list = summary.get("yesterdayCountList", [])
        if isinstance(count_list, list):
            for entry in count_list:
                if str(entry.get("petId")) == str(self._pet_id):
                    return entry.get("toiletsCount")
        return None


class MovaPetWeightSensor(MovaBaseSensor):
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_icon = "mdi:scale"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        pet_id: str,
        pet_name: str,
    ) -> None:
        super().__init__(
            coordinator, did, f"pet_{pet_id}_weight", f"{pet_name} Weight"
        )
        self._pet_id = pet_id

    @property
    def entity_picture(self) -> str | None:
        return self.coordinator.data.get("pet_avatars", {}).get(str(self._pet_id))

    @property
    def native_value(self) -> float | None:
        # Prefer latest weight from visit details (most accurate, from the scale)
        latest_weights = self.coordinator.data.get("latest_weights", {})
        weight = latest_weights.get(str(self._pet_id))
        if weight is not None:
            return round(weight / 1000, 1)
        # Fall back to profile weight
        for pet in self.coordinator.pet_info:
            if str(pet.get("id")) == str(self._pet_id):
                profile_weight = pet.get("weight")
                if profile_weight is not None:
                    return round(profile_weight / 1000, 1)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        for pet in self.coordinator.pet_info:
            if str(pet.get("id")) == str(self._pet_id):
                profile_weight = pet.get("weight")
                if profile_weight is not None:
                    attrs["profile_weight_kg"] = round(profile_weight / 1000, 1)
                attrs["breed"] = pet.get("varietyName")
                attrs["birth_date"] = pet.get("birthDate")
                sex = pet.get("sex")
                if sex == 0:
                    attrs["sex"] = "male"
                elif sex == 1:
                    attrs["sex"] = "female"
                sterilization = pet.get("sterilization")
                if sterilization == 1:
                    attrs["sterilized"] = True
                elif sterilization == 2:
                    attrs["sterilized"] = False
                break
        return attrs


class MovaPetLastVisitSensor(MovaBaseSensor):
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        pet_id: str,
        pet_name: str,
    ) -> None:
        super().__init__(
            coordinator,
            did,
            f"pet_{pet_id}_last_visit",
            f"{pet_name} Last Visit",
        )
        self._pet_id = pet_id

    @property
    def entity_picture(self) -> str | None:
        return self.coordinator.data.get("pet_avatars", {}).get(str(self._pet_id))

    def _find_last_visit(self) -> dict[str, Any] | None:
        visit_details = self.coordinator.data.get("visit_details", [])
        for visit in visit_details:
            if str(visit.get("petId")) == str(self._pet_id):
                return visit
        return None

    @property
    def native_value(self) -> str | None:
        visit = self._find_last_visit()
        if visit is None:
            return None
        return visit.get("startTimestamp")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        visit = self._find_last_visit()
        if visit is None:
            return {}

        piss_or_poop = visit.get("pissOrPoop")
        if piss_or_poop == 1:
            visit_type = "piss"
        elif piss_or_poop == 2:
            visit_type = "poop"
        else:
            visit_type = "unknown"

        duration_ms = visit.get("timeDuration")
        duration_seconds = round(duration_ms / 1000, 1) if duration_ms is not None else None

        weight_g = visit.get("weight")
        weight_kg = round(weight_g / 1000, 1) if weight_g is not None else None

        return {
            "duration_seconds": duration_seconds,
            "type": visit_type,
            "weight_kg": weight_kg,
            "event_type": visit.get("eventType"),
            "operation_type": visit.get("operationType"),
        }


class MovaConsumableSensor(MovaBaseSensor):
    _attr_icon = "mdi:package-variant"
    _attr_native_unit_of_measurement = "days"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: MovaLitterboxCoordinator,
        did: str,
        material_type: int,
    ) -> None:
        type_name = CONSUMABLE_TYPE_MAP.get(material_type, f"Consumable {material_type}")
        key = f"consumable_{material_type}"
        super().__init__(coordinator, did, key, f"{type_name} Remaining Days")
        self._material_type = material_type

    @property
    def native_value(self) -> int | None:
        consumables = self.coordinator.data.get("consumables", [])
        if isinstance(consumables, list):
            for item in consumables:
                if item.get("materialType") == self._material_type:
                    return item.get("remainDays")
        return None


class MovaLastVisitSensor(MovaBaseSensor):
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: MovaLitterboxCoordinator, did: str) -> None:
        super().__init__(coordinator, did, "last_visit", "Last Visit")

    @property
    def native_value(self) -> str | None:
        visit = self.coordinator.data.get("last_visit")
        if visit is None:
            return None
        pet_id = visit.get("petId")
        pet_name = "Unknown"
        for pet in self.coordinator.pet_info:
            if str(pet.get("id")) == str(pet_id):
                pet_name = pet.get("nickName", pet_name)
                break
        return pet_name

    @property
    def entity_picture(self) -> str | None:
        visit = self.coordinator.data.get("last_visit")
        if visit is None:
            return None
        pet_id = visit.get("petId")
        if pet_id is None:
            return None
        return self.coordinator.data.get("pet_avatars", {}).get(str(pet_id))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        visit = self.coordinator.data.get("last_visit")
        if visit is None:
            return {}

        pet_id = visit.get("petId")
        pet_name = "Unknown"
        for pet in self.coordinator.pet_info:
            if str(pet.get("id")) == str(pet_id):
                pet_name = pet.get("nickName", pet_name)
                break

        piss_or_poop = visit.get("pissOrPoop")
        if piss_or_poop == 1:
            visit_type = "piss"
        elif piss_or_poop == 2:
            visit_type = "poop"
        else:
            visit_type = "unknown"

        duration_ms = visit.get("timeDuration")
        duration_seconds = round(duration_ms / 1000, 1) if duration_ms is not None else None

        weight_g = visit.get("weight")
        weight_kg = round(weight_g / 1000, 1) if weight_g is not None else None

        return {
            "pet_name": pet_name,
            "pet_id": pet_id,
            "timestamp": visit.get("startTimestamp"),
            "duration_seconds": duration_seconds,
            "type": visit_type,
            "weight_kg": weight_kg,
            "event_type": visit.get("eventType"),
            "operation_type": visit.get("operationType"),
        }
