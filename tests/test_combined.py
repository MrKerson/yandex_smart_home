from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, CONF_NAME, CONF_TYPE
from homeassistant.core import HomeAssistant

from custom_components.yandex_smart_home.combined import (
    COMBINED_KIND_SENSOR,
    COMBINED_KIND_SWITCH,
    build_combined_entity_config,
    validate_combined_definition,
)
from custom_components.yandex_smart_home.const import (
    CONF_COMBINED_ENTITIES,
    CONF_COMBINED_KIND,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
    CONF_ENTITY_CUSTOM_TOGGLES,
    CONF_ENTITY_PROPERTIES,
    CONF_ENTITY_PROPERTY_ENTITY,
    CONF_ENTITY_PROPERTY_TYPE,
    CONF_STATE_UNKNOWN,
    CONF_TURN_OFF,
    CONF_TURN_ON,
)


def test_build_combined_switch(hass: HomeAssistant) -> None:
    hass.states.async_set("switch.office_left", "off")
    hass.states.async_set("switch.office_right", "on")

    definition = {
        CONF_NAME: "Выключатель кабинет",
        CONF_COMBINED_KIND: COMBINED_KIND_SWITCH,
        CONF_COMBINED_ENTITIES: ["switch.office_left", "switch.office_right"],
    }

    assert validate_combined_definition(hass, definition) is None

    config = build_combined_entity_config(hass, definition)
    assert config[CONF_TYPE] == "devices.types.switch"
    assert config[CONF_STATE_UNKNOWN] is True
    assert config[CONF_TURN_ON] is False
    assert config[CONF_TURN_OFF] is False
    assert config[CONF_ENTITY_CUSTOM_TOGGLES]["channel_1"][CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID] == (
        "switch.office_left"
    )
    assert config[CONF_ENTITY_CUSTOM_TOGGLES]["channel_2"][CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID] == (
        "switch.office_right"
    )


def test_build_combined_sensors_from_sensor_base(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.room_temperature",
        "22.3",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
    )
    hass.states.async_set(
        "sensor.room_humidity",
        "45",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY},
    )
    hass.states.async_set(
        "sensor.room_battery",
        "89",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY},
    )

    definition = {
        CONF_NAME: "Климат кабинет",
        CONF_COMBINED_KIND: COMBINED_KIND_SENSOR,
        CONF_COMBINED_ENTITIES: [
            "sensor.room_temperature",
            "sensor.room_humidity",
            "sensor.room_battery",
        ],
    }

    assert validate_combined_definition(hass, definition) is None

    config = build_combined_entity_config(hass, definition)
    assert CONF_TYPE not in config
    assert config[CONF_ENTITY_PROPERTIES] == [
        {CONF_ENTITY_PROPERTY_TYPE: "temperature", CONF_ENTITY_PROPERTY_ENTITY: "sensor.room_temperature"},
        {CONF_ENTITY_PROPERTY_TYPE: "humidity", CONF_ENTITY_PROPERTY_ENTITY: "sensor.room_humidity"},
        {CONF_ENTITY_PROPERTY_TYPE: "battery_level", CONF_ENTITY_PROPERTY_ENTITY: "sensor.room_battery"},
    ]


def test_build_combined_sensors_on_non_sensor_base(hass: HomeAssistant) -> None:
    hass.states.async_set("humidifier.office", "on")
    hass.states.async_set(
        "sensor.office_temperature",
        "23",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
    )
    hass.states.async_set(
        "sensor.office_humidity",
        "40",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY},
    )

    definition = {
        CONF_NAME: "Увлажнитель кабинет",
        CONF_COMBINED_KIND: COMBINED_KIND_SENSOR,
        CONF_COMBINED_ENTITIES: [
            "humidifier.office",
            "sensor.office_temperature",
            "sensor.office_humidity",
        ],
    }

    assert validate_combined_definition(hass, definition) is None

    config = build_combined_entity_config(hass, definition)
    assert config[CONF_ENTITY_PROPERTIES] == [
        {CONF_ENTITY_PROPERTY_TYPE: "temperature", CONF_ENTITY_PROPERTY_ENTITY: "sensor.office_temperature"},
        {CONF_ENTITY_PROPERTY_TYPE: "humidity", CONF_ENTITY_PROPERTY_ENTITY: "sensor.office_humidity"},
    ]


def test_reject_duplicate_combined_sensor_property(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "sensor.humidity_1",
        "40",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY},
    )
    hass.states.async_set(
        "sensor.humidity_2",
        "42",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.HUMIDITY},
    )

    definition = {
        CONF_NAME: "Датчики",
        CONF_COMBINED_KIND: COMBINED_KIND_SENSOR,
        CONF_COMBINED_ENTITIES: ["sensor.humidity_1", "sensor.humidity_2"],
    }

    assert validate_combined_definition(hass, definition) == "combined_duplicate_property"
