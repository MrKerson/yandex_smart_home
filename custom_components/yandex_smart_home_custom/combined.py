"""Helpers for UI-configured combined Yandex Smart Home devices."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.const import CONF_NAME, CONF_ROOM, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_COMBINED_ENTITIES,
    CONF_COMBINED_KIND,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON,
    CONF_ENTITY_CUSTOM_TOGGLES,
    CONF_ENTITY_PROPERTIES,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_STATE_UNKNOWN,
    CONF_TURN_OFF,
    CONF_TURN_ON,
)

COMBINED_KIND_SWITCH = "switch"
COMBINED_KIND_SENSOR = "sensor"
MAX_COMBINED_SWITCH_CHANNELS = 8

# Home Assistant sensor device_class -> Yandex float property instance.
_SENSOR_PROPERTY_TYPES: dict[str, str] = {
    "temperature": "temperature",
    "humidity": "humidity",
    "atmospheric_pressure": "pressure",
    "pressure": "pressure",
    "co2": "co2_level",
    "illuminance": "illumination",
    "battery": "battery_level",
    "current": "amperage",
    "power": "power",
    "energy": "electricity_meter",
    "voltage": "voltage",
    "pm1": "pm1_density",
    "pm10": "pm10_density",
    "pm25": "pm2.5_density",
    "volatile_organic_compounds": "tvoc",
    "water": "water_meter",
}


def unique_entities(entities: Iterable[str]) -> list[str]:
    """Return entity IDs preserving their order and removing duplicates."""
    return list(dict.fromkeys(str(entity_id) for entity_id in entities))


def _sensor_property_type(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return a Yandex property type for a Home Assistant sensor entity."""
    state = hass.states.get(entity_id)
    if state is None:
        return None

    return _SENSOR_PROPERTY_TYPES.get(str(state.attributes.get("device_class", "")))


def validate_combined_definition(hass: HomeAssistant, definition: ConfigType) -> str | None:
    """Validate a UI combined device definition and return an error key."""
    entities = unique_entities(definition.get(CONF_COMBINED_ENTITIES, []))
    kind = definition.get(CONF_COMBINED_KIND)

    if not entities:
        return "combined_entities_not_selected"

    missing = [entity_id for entity_id in entities if hass.states.get(entity_id) is None]
    if missing:
        return "combined_entity_not_found"

    if kind == COMBINED_KIND_SWITCH:
        if len(entities) > MAX_COMBINED_SWITCH_CHANNELS:
            return "combined_too_many_channels"

        supported_domains = {"switch", "light", "input_boolean"}
        if any(entity_id.split(".", 1)[0] not in supported_domains for entity_id in entities):
            return "combined_invalid_switch_entity"

        return None

    if kind == COMBINED_KIND_SENSOR:
        property_types: list[str] = []
        for index, entity_id in enumerate(entities):
            property_type = _sensor_property_type(hass, entity_id)

            # The first entity is the base Yandex device. It may be a thermostat,
            # humidifier, sensor, etc. If it is itself a supported sensor, include
            # its value as the first property, matching the documented YAML recipe.
            if property_type is None and index == 0:
                continue
            if property_type is None:
                return "combined_unsupported_sensor"

            if property_type in property_types:
                return "combined_duplicate_property"

            property_types.append(property_type)

        if not property_types:
            return "combined_unsupported_sensor"

        return None

    return "combined_invalid_kind"


def build_combined_entity_config(hass: HomeAssistant, definition: ConfigType) -> ConfigType:
    """Build entity_config compatible with the existing YAML implementation."""
    entities = unique_entities(definition.get(CONF_COMBINED_ENTITIES, []))
    kind = str(definition[CONF_COMBINED_KIND])

    config: ConfigType = {
        CONF_NAME: definition.get(CONF_NAME, "Объединенное устройство"),
    }
    if room := str(definition.get(CONF_ROOM, "")).strip():
        config[CONF_ROOM] = room

    if kind == COMBINED_KIND_SWITCH:
        # We intentionally suppress the automatically discovered on_off capability.
        # Each source becomes an equal channel toggle instead.
        config.update(
            {
                CONF_TYPE: "devices.types.switch",
                CONF_STATE_UNKNOWN: True,
                CONF_TURN_ON: False,
                CONF_TURN_OFF: False,
            }
        )

        toggles: ConfigType = {}
        for index, entity_id in enumerate(entities, start=1):
            domain = entity_id.split(".", 1)[0]
            toggles[f"channel_{index}"] = {
                CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID: entity_id,
                CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON: {
                    "action": f"{domain}.turn_on",
                    "target": {"entity_id": entity_id},
                },
                CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF: {
                    "action": f"{domain}.turn_off",
                    "target": {"entity_id": entity_id},
                },
            }

        config[CONF_ENTITY_CUSTOM_TOGGLES] = toggles
        return config

    if kind == COMBINED_KIND_SENSOR:
        properties: list[ConfigType] = []

        for entity_id in entities:
            property_type = _sensor_property_type(hass, entity_id)
            if property_type is None:
                continue

            properties.append(
                {
                    CONF_ENTITY_PROPERTY_TYPE: property_type,
                    CONF_ENTITY_PROPERTY_ENTITY: entity_id,
                }
            )

        config[CONF_ENTITY_PROPERTIES] = properties
        return config

    raise ValueError(f"Unsupported combined device kind: {kind}")
