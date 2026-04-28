"""Adds config flow for Blueprint."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    CONF_SETUP_TYPE,
    DOMAIN,
    SETUP_TYPE_DUAL_LIGHT,
    SETUP_TYPE_RGBW,
    _DUAL_LIGHT_SCHEMA,
    _RGBW_SCHEMA,
    _SETUP_TYPE_SCHEMA,
    _build_dual_light_schema,
    _build_rgbw_schema,
    is_capitalized,
    is_rgbw_config,
)

_LOGGER = logging.getLogger(__name__)


class CCTVirtuaLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for CCT Virtual Light."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._shared_data: dict = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "CCTVirtualLightOptionsFlow":
        """Create the options flow (shown via the Configure button)."""
        return CCTVirtualLightOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the first step: collect name and setup type."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not is_capitalized(user_input[CONF_NAME]):
                _LOGGER.debug("Name is not capitalized")
                errors = {CONF_NAME: "Name must start with a capital letter"}
            else:
                self._shared_data = dict(user_input)
                setup_type = user_input.get(CONF_SETUP_TYPE, SETUP_TYPE_DUAL_LIGHT)
                if setup_type == SETUP_TYPE_RGBW:
                    return await self.async_step_rgbw()
                return await self.async_step_dual_light()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(_SETUP_TYPE_SCHEMA),
            errors=errors,
        )

    async def async_step_dual_light(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the dual-light configuration step."""
        if user_input is not None:
            data = {**self._shared_data, **user_input}
            # Explicitly stamp the setup type so it is always present in the stored entry
            data[CONF_SETUP_TYPE] = SETUP_TYPE_DUAL_LIGHT
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="dual_light",
            data_schema=vol.Schema(_DUAL_LIGHT_SCHEMA),
        )

    async def async_step_rgbw(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the RGBW controller configuration step."""
        if user_input is not None:
            data = {**self._shared_data, **user_input}
            # Explicitly stamp the setup type so it is always present in the stored entry
            data[CONF_SETUP_TYPE] = SETUP_TYPE_RGBW
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="rgbw",
            data_schema=vol.Schema(_RGBW_SCHEMA),
        )

    async def async_step_import(
        self,
        user_input: dict,
    ) -> ConfigFlowResult:
        """Handle configuration by YAML file."""
        await self.async_set_unique_id(user_input[CONF_NAME])
        # Keep a list of lights that are configured via YAML
        data = self.hass.data.setdefault(DOMAIN, {})
        data.setdefault("__yaml__", set()).add(self.unique_id)

        for entry in self._async_current_entries():
            if entry.unique_id == self.unique_id:
                _LOGGER.debug("Updating existing config entry")
                self.hass.config_entries.async_update_entry(entry, data=user_input)
                self._abort_if_unique_id_configured()

        _LOGGER.debug("Creating a new config entry")
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)


class CCTVirtualLightOptionsFlow(config_entries.OptionsFlow):
    """Options flow – allows reconfiguring an existing entry via the Configure button."""

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Route to the correct sub-step based on the current setup type."""
        current = {**self.config_entry.data, **self.config_entry.options}
        if is_rgbw_config(current):
            return await self.async_step_rgbw(user_input)
        return await self.async_step_dual_light(user_input)

    async def async_step_dual_light(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Reconfigure a dual-light entry."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="dual_light",
            data_schema=_build_dual_light_schema(current),
        )

    async def async_step_rgbw(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Reconfigure an RGBW entry."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="rgbw",
            data_schema=_build_rgbw_schema(current),
        )
