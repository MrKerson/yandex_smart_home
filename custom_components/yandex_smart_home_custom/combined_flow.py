"""Options-flow UI for combined Yandex Smart Home devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_ENTITIES, CONF_NAME, CONF_ROOM
from homeassistant.helpers import selector
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES, FILTER_SCHEMA, EntityFilter
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .combined import (
    COMBINED_KIND_SENSOR,
    COMBINED_KIND_SWITCH,
    build_combined_entity_config,
    unique_entities,
    validate_combined_definition,
)
from .const import (
    CONF_COMBINED_ACTION,
    CONF_COMBINED_DEVICES,
    CONF_COMBINED_ENTITIES,
    CONF_COMBINED_EXPOSED,
    CONF_COMBINED_KIND,
    CONF_COMBINED_SELECTED,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_UI_ENTITY_CONFIG,
    EntityFilterSource,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant

_ACTION_CREATE = "create"
_ACTION_EDIT = "edit"
_ACTION_DELETE = "delete"


def _combined_member_entities(definitions: ConfigType) -> set[str]:
    """Return all entities already used as members of combined devices."""
    return {
        str(entity_id)
        for definition in definitions.values()
        for entity_id in definition.get(CONF_COMBINED_ENTITIES, [])
    }


class CombinedOptionsFlowMixin:
    """Add a UI builder for combined devices to the integration options flow."""

    _combined_action: str | None = None
    _combined_selected: str | None = None

    if TYPE_CHECKING:
        hass: HomeAssistant
        _options: ConfigType

        def async_show_form(self, *args: Any, **kwargs: Any) -> ConfigFlowResult:
            """Type stub for FlowHandler.async_show_form."""
            ...

        async def async_step_done(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
            """Type stub for the concrete options flow completion step."""
            ...

    async def async_step_combined_devices(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose an action for combined devices."""
        combined = self._options.get(CONF_COMBINED_DEVICES, {})

        if user_input is not None:
            action = str(user_input[CONF_COMBINED_ACTION])
            self._combined_action = action
            self._combined_selected = None

            if action == _ACTION_CREATE:
                return await self.async_step_combined_device_form()

            return await self.async_step_combined_device_select()

        actions = [SelectOptionDict(value=_ACTION_CREATE, label="Создать объединенное устройство")]
        if combined:
            actions.extend(
                [
                    SelectOptionDict(value=_ACTION_EDIT, label="Изменить объединенное устройство"),
                    SelectOptionDict(value=_ACTION_DELETE, label="Удалить объединенное устройство"),
                ]
            )

        return self.async_show_form(
            step_id="combined_devices",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COMBINED_ACTION): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            options=actions,
                        )
                    )
                }
            ),
        )

    async def async_step_combined_device_select(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Select an existing combined device."""
        combined: ConfigType = self._options.get(CONF_COMBINED_DEVICES, {})
        if not combined:
            return await self.async_step_combined_devices()

        if user_input is not None:
            selected = str(user_input[CONF_COMBINED_SELECTED])
            self._combined_selected = selected

            if self._combined_action == _ACTION_DELETE:
                definitions = dict(combined)
                definitions.pop(selected, None)
                self._options[CONF_COMBINED_DEVICES] = definitions

                ui_entity_config = dict(self._options.get(CONF_UI_ENTITY_CONFIG, {}))
                ui_entity_config.pop(selected, None)
                self._options[CONF_UI_ENTITY_CONFIG] = ui_entity_config

                exposed = set(self._options.get(CONF_COMBINED_EXPOSED, []))
                exposed.discard(selected)
                self._options[CONF_COMBINED_EXPOSED] = sorted(exposed)

                filter_config = dict(self._options.get(CONF_FILTER, {}))
                include_entities = set(filter_config.get(CONF_INCLUDE_ENTITIES, []))
                include_entities.discard(selected)
                self._options[CONF_FILTER] = {CONF_INCLUDE_ENTITIES: sorted(include_entities)}

                return await self.async_step_done()

            return await self.async_step_combined_device_form()

        options = [
            SelectOptionDict(value=base_entity, label=str(definition.get(CONF_NAME, base_entity)))
            for base_entity, definition in combined.items()
        ]

        return self.async_show_form(
            step_id="combined_device_select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COMBINED_SELECTED): SelectSelector(
                        SelectSelectorConfig(mode=SelectSelectorMode.DROPDOWN, options=options)
                    )
                }
            ),
        )

    async def async_step_combined_device_form(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Create or edit a combined device."""
        errors: dict[str, str] = {}
        existing: ConfigType = {}
        definitions: ConfigType = dict(self._options.get(CONF_COMBINED_DEVICES, {}))

        if self._combined_selected:
            existing = dict(definitions.get(self._combined_selected, {}))

        if user_input is not None:
            entities = unique_entities(user_input.get(CONF_COMBINED_ENTITIES, []))
            definition: ConfigType = {
                CONF_NAME: str(user_input[CONF_NAME]).strip(),
                CONF_ROOM: str(user_input.get(CONF_ROOM, "")).strip(),
                CONF_COMBINED_KIND: str(user_input[CONF_COMBINED_KIND]),
                CONF_COMBINED_ENTITIES: entities,
            }

            if not definition[CONF_NAME]:
                errors[CONF_NAME] = "combined_name_required"
            elif error := validate_combined_definition(self.hass, definition):
                errors["base"] = error
            else:
                base_entity = entities[0]

                if base_entity in definitions and base_entity != self._combined_selected:
                    errors["base"] = "combined_base_already_used"
                else:
                    old_base = self._combined_selected
                    old_members = set(existing.get(CONF_COMBINED_ENTITIES, []))
                    if old_base and old_base != base_entity:
                        definitions.pop(old_base, None)

                    definitions[base_entity] = definition
                    self._options[CONF_COMBINED_DEVICES] = definitions

                    ui_entity_config = dict(self._options.get(CONF_UI_ENTITY_CONFIG, {}))
                    if old_base and old_base != base_entity:
                        ui_entity_config.pop(old_base, None)
                    ui_entity_config[base_entity] = build_combined_entity_config(self.hass, definition)
                    self._options[CONF_UI_ENTITY_CONFIG] = ui_entity_config

                    exposed = set(self._options.get(CONF_COMBINED_EXPOSED, []))
                    if old_base:
                        exposed.discard(old_base)
                    exposed.add(base_entity)
                    self._options[CONF_COMBINED_EXPOSED] = sorted(exposed)

                    # Members of a combined device must not also be exposed as standalone devices.
                    # Remove previous and current members from the regular list and then add only
                    # the base entity that represents the combined Yandex device.
                    filter_config = dict(self._options.get(CONF_FILTER, {}))
                    include_entities = set(filter_config.get(CONF_INCLUDE_ENTITIES, []))
                    include_entities.difference_update(old_members)
                    include_entities.difference_update(entities)
                    include_entities.add(base_entity)
                    self._options[CONF_FILTER] = {CONF_INCLUDE_ENTITIES: sorted(include_entities)}

                    # With UI-based exposure, immediately show the normal transfer page.
                    # The newly created combined device is already selected there.
                    if self._options.get(CONF_FILTER_SOURCE) == EntityFilterSource.CONFIG_ENTRY:
                        return await self.async_step_include_entities()

                    return await self.async_step_done()

        kind_options = [
            SelectOptionDict(value=COMBINED_KIND_SWITCH, label="Многоклавишный выключатель (экспериментально)"),
            SelectOptionDict(value=COMBINED_KIND_SENSOR, label="Датчики / свойства в одном устройстве"),
        ]

        return self.async_show_form(
            step_id="combined_device_form",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=existing.get(CONF_NAME, "")): str,
                    vol.Optional(CONF_ROOM, default=existing.get(CONF_ROOM, "")): str,
                    vol.Required(
                        CONF_COMBINED_KIND,
                        default=existing.get(CONF_COMBINED_KIND, COMBINED_KIND_SWITCH),
                    ): SelectSelector(
                        SelectSelectorConfig(mode=SelectSelectorMode.LIST, options=kind_options)
                    ),
                    vol.Required(
                        CONF_COMBINED_ENTITIES,
                        default=existing.get(CONF_COMBINED_ENTITIES, []),
                    ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
                }
            ),
            errors=errors,
        )

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose normal entities and UI-combined devices to expose."""
        combined: ConfigType = self._options.get(CONF_COMBINED_DEVICES, {})
        errors: dict[str, str] = {}
        all_combined_base_entities = set(combined)
        all_combined_members = _combined_member_entities(combined)
        explicit_entities: set[str] = set()

        if entity_filter_config := self._options.get(CONF_FILTER):
            explicit_entities.update(entity_filter_config.get(CONF_INCLUDE_ENTITIES, []))

            if len(entity_filter_config) > 1 or CONF_INCLUDE_ENTITIES not in entity_filter_config:
                entity_filter: EntityFilter = FILTER_SCHEMA(entity_filter_config)
                if not entity_filter.empty_filter:
                    explicit_entities.update(
                        [s.entity_id for s in self.hass.states.async_all() if entity_filter(s.entity_id)]
                    )

        explicit_entities -= all_combined_members
        combined_exposed = set(self._options.get(CONF_COMBINED_EXPOSED, [])) & all_combined_base_entities

        if user_input is not None:
            normal_entities = set(user_input.get(CONF_ENTITIES, [])) - all_combined_members
            combined_exposed = set(user_input.get(CONF_COMBINED_EXPOSED, [])) & all_combined_base_entities

            if normal_entities or combined_exposed:
                self._options[CONF_FILTER] = {
                    CONF_INCLUDE_ENTITIES: sorted(normal_entities | combined_exposed)
                }
                self._options[CONF_COMBINED_EXPOSED] = sorted(combined_exposed)
                return await self.async_step_done()

            errors["base"] = "entities_not_selected"
            explicit_entities.clear()
            combined_exposed.clear()

        schema: dict[Any, Any] = {
            vol.Required(CONF_ENTITIES, default=sorted(explicit_entities)): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True)
            )
        }

        if combined:
            combined_options = [
                SelectOptionDict(
                    value=base_entity,
                    label=f"{definition.get(CONF_NAME, base_entity)} ({base_entity})",
                )
                for base_entity, definition in combined.items()
            ]
            schema[vol.Optional(CONF_COMBINED_EXPOSED, default=sorted(combined_exposed))] = SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    multiple=True,
                    options=combined_options,
                )
            )

        return self.async_show_form(
            step_id="include_entities",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
