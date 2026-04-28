"""Light platform."""

import asyncio
from collections.abc import Awaitable
import json
import logging
from typing import Any

from homeassistant.components.group.light import FORWARDED_ATTRIBUTES, LightGroup
from homeassistant.components.group.util import find_state_attributes
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGBW_COLOR,
    DOMAIN as DOMAIN_LIGHT,
    ColorMode,
)
from homeassistant.components.sensor import RestoreSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITY_ID,
    CONF_NAME,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_COLD_CHANNEL,
    CONF_COLD_LIGHT,
    CONF_COLD_LIGHT_TEMPERATURE_KELVIN,
    CONF_RGBW_CONTROLLER,
    CONF_SETUP_TYPE,
    CONF_WARM_CHANNEL,
    CONF_WARM_LIGHT,
    CONF_WARM_LIGHT_TEMPERATURE_KELVIN,
    DOMAIN,
    RGBW_CHANNEL_MAP,
    SETUP_TYPE_RGBW,
)
from .helper import (
    BrightnessCalculator,
    BrightnessTemperaturePriority,
    TemperatureCalculator,
    TurnOnSettings,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    """Set up the sensor platform."""
    config = entry.as_dict()["data"]

    if config.get(CONF_SETUP_TYPE) == SETUP_TYPE_RGBW:
        light = RGBWTemperatureMixerLight(
            name=config[CONF_NAME],
            rgbw_entity_id=config[CONF_RGBW_CONTROLLER],
            warm_channel=config[CONF_WARM_CHANNEL],
            cold_channel=config[CONF_COLD_CHANNEL],
            warm_temperature_kelvin=config[CONF_WARM_LIGHT_TEMPERATURE_KELVIN],
            cold_temperature_kelvin=config[CONF_COLD_LIGHT_TEMPERATURE_KELVIN],
            config_id=entry.entry_id,
        )
    else:
        light = TemperatureMixerLight(
            name=config[CONF_NAME],
            warm_light={
                CONF_ENTITY_ID: config[CONF_WARM_LIGHT],
                ATTR_COLOR_TEMP_KELVIN: config[CONF_WARM_LIGHT_TEMPERATURE_KELVIN],
            },
            cold_light={
                CONF_ENTITY_ID: config[CONF_COLD_LIGHT],
                ATTR_COLOR_TEMP_KELVIN: config[CONF_COLD_LIGHT_TEMPERATURE_KELVIN],
            },
            config_id=entry.entry_id,
        )

    async_add_devices([light])


class TemperatureMixerLight(LightGroup, RestoreSensor):
    """Light group that mixes a group of lights having different color temperature."""

    _attr_has_entity_name = True
    _attr_name = None  # This is the main feature of the service

    def __init__(
        self,
        name: str,
        warm_light: dict[str, Any],
        cold_light: dict[str, Any],
        config_id: str,
    ) -> None:
        """Initialize the CCT light."""
        self._attr_unique_id = config_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=name,
        )
        super().__init__(
            unique_id=self.unique_id,
            name=None,  # type: ignore
            entity_ids=[warm_light[ATTR_ENTITY_ID], cold_light[ATTR_ENTITY_ID]],
            mode=False,
        )
        self._attr_min_color_temp_kelvin = warm_light[ATTR_COLOR_TEMP_KELVIN]
        self._attr_max_color_temp_kelvin = cold_light[ATTR_COLOR_TEMP_KELVIN]
        self._attr_color_mode = ColorMode.COLOR_TEMP
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}

        self.warm_light = warm_light
        self.cold_light = cold_light
        self.config_id = config_id

        # Initialize previous state to empty dict to avoid None
        self.previous_turn_on_state = {}

    def _friendly_name(self) -> str:
        """Return the best available name for logs."""
        return (
            self._cached_friendly_name
            or self.name
            or self.entity_id
            or self.unique_id
            or "unknown"
        )

    async def async_added_to_hass(self) -> None:
        """Read the previous turn_on state from the restore data, if available."""
        restored_data = await self.async_get_last_sensor_data()
        # Deserialized the saved state from JSON, if available
        if restored_data and restored_data.native_value:
            serialized_state: str = restored_data.native_value  # type: ignore -> we know it is as string
            self.previous_turn_on_state = json.loads(serialized_state)
            _LOGGER.debug(
                "%s: restoring previous_turn_on_state: %s",
                self._friendly_name(),
                self.previous_turn_on_state,
            )

        # Continue initialization of parent object
        await super().async_added_to_hass()

    @callback
    def async_update_group_state(self) -> None:
        """Update the state of the light group."""
        states = {
            entity_id: state
            for entity_id in self._entity_ids
            if (state := self.hass.states.get(entity_id)) is not None
        }
        # Filter for states that are on
        on_states = {
            state: value for (state, value) in states.items() if value.state == STATE_ON
        }

        valid_state = self.mode(
            state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
            for state in states.values()
        )

        if not valid_state:
            # Set as unknown if any / all member is unknown or unavailable
            self._attr_is_on = None
        else:
            # Set as ON if any / all member is ON
            self._attr_is_on = self.mode(
                state.state == STATE_ON for state in states.values()
            )

        self._attr_available = any(
            state.state != STATE_UNAVAILABLE for state in states.values()
        )

        brightnesses: list[int] = list(
            find_state_attributes(list(on_states.values()), ATTR_BRIGHTNESS)
        )
        self._attr_brightness = int(sum(brightnesses) / 2) if brightnesses else None
        self._attr_color_temp_kelvin = self._compute_color_temp_kelvin(on_states)

    def _compute_color_temp_kelvin(self, on_states: dict[str, State]) -> int | None:
        """Given the dictionary of states containing the lights that are currently on, compute the combined temperature of the light group as a weighted average of the two lights temperatures."""
        # If no light is on, we are unable to compute the temperature
        if not on_states:
            return

        warm_light_state = on_states.get(self.warm_light[ATTR_ENTITY_ID])
        cold_light_state = on_states.get(self.cold_light[ATTR_ENTITY_ID])

        # Try to extract the brightness attribute if the light is on, otherwise fallback to 0
        self.warm_light[ATTR_BRIGHTNESS] = (
            int(warm_light_state.attributes.get(ATTR_BRIGHTNESS, 0))
            if warm_light_state is not None
            else 0
        )
        self.cold_light[ATTR_BRIGHTNESS] = (
            int(cold_light_state.attributes.get(ATTR_BRIGHTNESS, 0))
            if cold_light_state is not None
            else 0
        )

        temperature_calc = TemperatureCalculator(
            self.warm_light[ATTR_BRIGHTNESS],
            self.warm_light[ATTR_COLOR_TEMP_KELVIN],
            self.cold_light[ATTR_BRIGHTNESS],
            self.cold_light[ATTR_COLOR_TEMP_KELVIN],
        )
        computed_temp = temperature_calc.current_temperature()

        return computed_temp

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Given a combination of brightness or color_temp_kelvin, compute the required brightnesses for all the lights in the group."""
        _LOGGER.debug(
            "%s: turn on with params: %s", self._friendly_name(), kwargs
        )

        # Extract information about the target temperature and brightness passed as kwargs, if available.
        # Otherwise try to maintain the currently set temperature and brightness, restoring them from the dedicated sensors if unavailable locally
        target_brightness = kwargs.get(ATTR_BRIGHTNESS)
        target_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        # By default we prioritize both temp and brightness
        priority = BrightnessTemperaturePriority.MIXED
        if not any([target_brightness, target_temp_kelvin]):
            # If no brightness and temperature has been provided, fallback to their current value
            target_brightness = self.brightness
            target_temp_kelvin = self.color_temp_kelvin
        elif target_brightness is None:
            # If not provided in the service call, fallback to the current value of the light brightness and prioritize temperature
            target_brightness = self.brightness
            priority = BrightnessTemperaturePriority.TEMPERATURE
        elif target_temp_kelvin is None:
            # If not provided in the service call, fallback to the current value of the light temperature and prioritize brightness
            target_temp_kelvin = self.color_temp_kelvin
            priority = BrightnessTemperaturePriority.BRIGHTNESS

        # If one of the two parameter (brightness/temp) is undefined,
        # it means we do not have a state to fallback to, so read the values from our fallback state, if available
        if target_brightness is None:
            target_brightness = self.previous_turn_on_state.get(ATTR_BRIGHTNESS)
            _LOGGER.debug(
                "%s: using previous brightness: %s",
                self._friendly_name(),
                target_brightness,
            )
        if target_temp_kelvin is None:
            target_temp_kelvin = self.previous_turn_on_state.get(ATTR_COLOR_TEMP_KELVIN)
            _LOGGER.debug(
                "%s: using previous temperature: %s",
                self._friendly_name(),
                target_temp_kelvin,
            )

        # Populate the base service data common to all the lights
        common_data = {
            key: value for key, value in kwargs.items() if key in FORWARDED_ATTRIBUTES
        }

        if not all([target_brightness, target_temp_kelvin]):
            _LOGGER.debug(
                "%s: no restored state available, turning all each light to its default state",
                self._friendly_name(),
            )
            ww_settings = TurnOnSettings(self.warm_light[CONF_ENTITY_ID], common_data)
            cw_settings = TurnOnSettings(self.cold_light[CONF_ENTITY_ID], common_data)
            await self._turn_on_lights(ww_settings, cw_settings)
            return

        # Clamp between min and max possible temperatures
        target_temp_kelvin = min(
            self.cold_light[ATTR_COLOR_TEMP_KELVIN],
            max(target_temp_kelvin, self.warm_light[ATTR_COLOR_TEMP_KELVIN]),
        )

        brightness_calculator = BrightnessCalculator(
            self.min_color_temp_kelvin,
            self.max_color_temp_kelvin,
            target_temp_kelvin,  # type: ignore
            target_brightness,  # type: ignore
            priority,
        )
        ww_brightness, cw_brightness = brightness_calculator.compute_brightnesses()

        # Personalize the service data with the light-specific brightness
        ww_settings = TurnOnSettings(
            self.warm_light[CONF_ENTITY_ID], common_data.copy(), ww_brightness
        )
        cw_settings = TurnOnSettings(
            self.cold_light[CONF_ENTITY_ID], common_data.copy(), cw_brightness
        )

        await self._turn_on_lights(ww=ww_settings, cw=cw_settings)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Forward the turn_off command to all the lights in the light group."""
        # Save our turned on state
        self._save_turn_on_state()

        _LOGGER.debug(
            "%s: invoking turn_off for the light group", self._friendly_name()
        )
        await super().async_turn_off(**kwargs)

    def _save_turn_on_state(self):
        """Store the turned on state as a serialized JSON string, to read it in case HA restarts."""
        # Check that we have a value for both brightness and temperature before firing the signal
        if self.brightness is None or self.color_temp_kelvin is None:
            return

        # Store the state as a serialized JSON string
        self.previous_turn_on_state = {
            ATTR_BRIGHTNESS: self.brightness,
            ATTR_COLOR_TEMP_KELVIN: self.color_temp_kelvin,
        }
        self._attr_native_value = json.dumps(self.previous_turn_on_state)
        _LOGGER.debug(
            "%s: saving serialized state: %s",
            self._friendly_name(),
            self.previous_turn_on_state,
        )

    async def _turn_on_lights(
        self, ww: TurnOnSettings, cw: TurnOnSettings
    ) -> Awaitable:
        service_calls = []
        for light in (ww, cw):
            target = {ATTR_ENTITY_ID: light.entity_id}
            service_data = light.common_data

            if light.brightness is not None:
                service_data[ATTR_BRIGHTNESS] = light.brightness

            _LOGGER.debug(
                "%s: forward turn_on: %s %s",
                self._friendly_name(),
                target,
                service_data,
            )
            service_calls.append(
                self.hass.services.async_call(
                    DOMAIN_LIGHT,
                    SERVICE_TURN_ON,
                    target=target,
                    service_data=service_data,
                    blocking=False,
                    context=self._context,
                )
            )

        return asyncio.gather(*service_calls)


class RGBWTemperatureMixerLight(LightGroup, RestoreSensor):
    """Light that controls a single RGBW controller, using two channels as warm/cold light."""

    _attr_has_entity_name = True
    _attr_name = None  # This is the main feature of the service

    def __init__(
        self,
        name: str,
        rgbw_entity_id: str,
        warm_channel: str,
        cold_channel: str,
        warm_temperature_kelvin: int,
        cold_temperature_kelvin: int,
        config_id: str,
    ) -> None:
        """Initialize the RGBW temperature mixer light."""
        self._attr_unique_id = config_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=name,
        )
        super().__init__(
            unique_id=self.unique_id,
            name=None,  # type: ignore
            entity_ids=[rgbw_entity_id],
            mode=False,
        )
        self._rgbw_entity_id = rgbw_entity_id
        self._warm_channel_index: int = RGBW_CHANNEL_MAP[warm_channel]
        self._cold_channel_index: int = RGBW_CHANNEL_MAP[cold_channel]
        self._warm_temperature_kelvin = warm_temperature_kelvin
        self._cold_temperature_kelvin = cold_temperature_kelvin
        self.config_id = config_id

        self._attr_min_color_temp_kelvin = warm_temperature_kelvin
        self._attr_max_color_temp_kelvin = cold_temperature_kelvin
        self._attr_color_mode = ColorMode.COLOR_TEMP
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}

        # Initialize previous state to empty dict to avoid None
        self.previous_turn_on_state = {}

    def _friendly_name(self) -> str:
        """Return the best available name for logs."""
        return (
            self._cached_friendly_name
            or self.name
            or self.entity_id
            or self.unique_id
            or "unknown"
        )

    async def async_added_to_hass(self) -> None:
        """Read the previous turn_on state from the restore data, if available."""
        restored_data = await self.async_get_last_sensor_data()
        if restored_data and restored_data.native_value:
            serialized_state: str = restored_data.native_value  # type: ignore
            self.previous_turn_on_state = json.loads(serialized_state)
            _LOGGER.debug(
                "%s: restoring previous_turn_on_state: %s",
                self._friendly_name(),
                self.previous_turn_on_state,
            )

        await super().async_added_to_hass()

    @callback
    def async_update_group_state(self) -> None:
        """Update the state of the RGBW light."""
        state = self.hass.states.get(self._rgbw_entity_id)

        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._attr_is_on = None
            self._attr_available = state is not None and state.state != STATE_UNAVAILABLE
            self._attr_brightness = None
            self._attr_color_temp_kelvin = None
            return

        self._attr_available = True
        self._attr_is_on = state.state == STATE_ON

        if not self._attr_is_on:
            self._attr_brightness = None
            self._attr_color_temp_kelvin = None
            return

        rgbw_color = state.attributes.get(ATTR_RGBW_COLOR)
        if rgbw_color is not None:
            warm_brightness = int(rgbw_color[self._warm_channel_index])
            cold_brightness = int(rgbw_color[self._cold_channel_index])

            self._attr_brightness = min(
                max(warm_brightness, cold_brightness), 255
            )
            temperature_calc = TemperatureCalculator(
                warm_brightness,
                self._warm_temperature_kelvin,
                cold_brightness,
                self._cold_temperature_kelvin,
            )
            self._attr_color_temp_kelvin = temperature_calc.current_temperature()
        else:
            self._attr_brightness = state.attributes.get(ATTR_BRIGHTNESS)
            self._attr_color_temp_kelvin = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Compute warm/cold channel brightnesses and turn on the RGBW controller."""
        _LOGGER.debug(
            "%s: turn on with params: %s", self._friendly_name(), kwargs
        )

        target_brightness = kwargs.get(ATTR_BRIGHTNESS)
        target_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        priority = BrightnessTemperaturePriority.MIXED
        if not any([target_brightness, target_temp_kelvin]):
            target_brightness = self.brightness
            target_temp_kelvin = self.color_temp_kelvin
        elif target_brightness is None:
            target_brightness = self.brightness
            priority = BrightnessTemperaturePriority.TEMPERATURE
        elif target_temp_kelvin is None:
            target_temp_kelvin = self.color_temp_kelvin
            priority = BrightnessTemperaturePriority.BRIGHTNESS

        if target_brightness is None:
            target_brightness = self.previous_turn_on_state.get(ATTR_BRIGHTNESS)
            _LOGGER.debug(
                "%s: using previous brightness: %s",
                self._friendly_name(),
                target_brightness,
            )
        if target_temp_kelvin is None:
            target_temp_kelvin = self.previous_turn_on_state.get(ATTR_COLOR_TEMP_KELVIN)
            _LOGGER.debug(
                "%s: using previous temperature: %s",
                self._friendly_name(),
                target_temp_kelvin,
            )

        if not all([target_brightness, target_temp_kelvin]):
            _LOGGER.debug(
                "%s: no restored state available, turning on the controller to its default state",
                self._friendly_name(),
            )
            await self.hass.services.async_call(
                DOMAIN_LIGHT,
                SERVICE_TURN_ON,
                target={ATTR_ENTITY_ID: self._rgbw_entity_id},
                blocking=False,
                context=self._context,
            )
            return

        # Clamp temperature to the supported range
        target_temp_kelvin = min(
            self._cold_temperature_kelvin,
            max(target_temp_kelvin, self._warm_temperature_kelvin),
        )

        brightness_calculator = BrightnessCalculator(
            self._warm_temperature_kelvin,
            self._cold_temperature_kelvin,
            target_temp_kelvin,  # type: ignore
            target_brightness,  # type: ignore
            priority,
        )
        ww_brightness, cw_brightness = brightness_calculator.compute_brightnesses()

        # Build the RGBW tuple: set computed values in the warm/cold channel slots
        rgbw: list[int] = [0, 0, 0, 0]
        rgbw[self._warm_channel_index] = max(0, min(255, ww_brightness))
        rgbw[self._cold_channel_index] = max(0, min(255, cw_brightness))

        _LOGGER.debug(
            "%s: forward turn_on RGBW controller %s rgbw=%s",
            self._friendly_name(),
            self._rgbw_entity_id,
            rgbw,
        )
        # Set the controller brightness to its maximum so that the RGBW channel
        # values computed above are applied without any additional scaling.
        # The desired output brightness is already encoded in the per-channel values.
        await self.hass.services.async_call(
            DOMAIN_LIGHT,
            SERVICE_TURN_ON,
            target={ATTR_ENTITY_ID: self._rgbw_entity_id},
            service_data={ATTR_RGBW_COLOR: tuple(rgbw), ATTR_BRIGHTNESS: 255},
            blocking=False,
            context=self._context,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Save state and forward the turn_off command to the RGBW controller."""
        self._save_turn_on_state()

        _LOGGER.debug(
            "%s: invoking turn_off for the RGBW controller", self._friendly_name()
        )
        await super().async_turn_off(**kwargs)

    def _save_turn_on_state(self):
        """Store the turned on state as a serialized JSON string."""
        if self.brightness is None or self.color_temp_kelvin is None:
            return

        self.previous_turn_on_state = {
            ATTR_BRIGHTNESS: self.brightness,
            ATTR_COLOR_TEMP_KELVIN: self.color_temp_kelvin,
        }
        self._attr_native_value = json.dumps(self.previous_turn_on_state)
        _LOGGER.debug(
            "%s: saving serialized state: %s",
            self._friendly_name(),
            self.previous_turn_on_state,
        )

