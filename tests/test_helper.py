"""Test the helper utilities."""

from custom_components.color_temperature_light_mixer.const import (
    CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
    CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
)
from custom_components.color_temperature_light_mixer.helper import (
    BRIGHTNESS_RANGE,
    BrightnessCalculator,
    BrightnessTemperaturePriority,
    compute_rgbw_channel_brightnesses,
)
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired,
    color_temperature_mired_to_kelvin,
)


class TestBrightnessCalculator:
    """Test the BrightnessCalculator."""

    def test_full_warm_only(self):
        """Full brightness to warm."""
        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            3000,
            int(BRIGHTNESS_RANGE[1] / 2),
        )
        ww, cw = bc.compute_brightnesses()
        assert BRIGHTNESS_RANGE[1] - 1 <= ww <= BRIGHTNESS_RANGE[1]
        assert cw == 0

    def test_full_cold_only(self):
        """Full brightness to cold."""
        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            6000,
            int(BRIGHTNESS_RANGE[1] / 2),
        )
        ww, cw = bc.compute_brightnesses()
        assert ww == 0
        assert BRIGHTNESS_RANGE[1] - 1 <= cw <= BRIGHTNESS_RANGE[1]

    def test_inside_range(self):
        """Temperature inside allowable range."""

        target_temperature = 4000
        target_brightness = int(BRIGHTNESS_RANGE[1] / 2)

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            target_temperature,
            target_brightness,
        )
        ww, cw = bc.compute_brightnesses()

        assert ww == 128
        assert cw == 126

    def test_middle_temperature(self):
        """Temperature exactly in the middle point."""

        cold_light_mired = color_temperature_kelvin_to_mired(
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE
        )
        warm_light_mired = color_temperature_kelvin_to_mired(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE
        )
        target_temperature_mired = (cold_light_mired + warm_light_mired) / 2

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            color_temperature_mired_to_kelvin(target_temperature_mired),
            int((BRIGHTNESS_RANGE[0] + BRIGHTNESS_RANGE[1]) / 4),
        )
        ww, cw = bc.compute_brightnesses()

        mid_brightness = (BRIGHTNESS_RANGE[0] + BRIGHTNESS_RANGE[1]) / 4
        assert mid_brightness - 1 <= ww <= mid_brightness
        assert mid_brightness - 1 <= cw <= mid_brightness

    def test_full_cold_temperature_priority(self):
        """Full brightness with cold temperature, priority to temperature."""

        target_temperature = CONF_DEFAULT_COLD_LIGHT_TEMPERATURE

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            int(target_temperature),
            int(BRIGHTNESS_RANGE[1]),
            BrightnessTemperaturePriority.TEMPERATURE,
        )
        ww, cw = bc.compute_brightnesses()

        assert -1 <= ww <= 0
        assert BRIGHTNESS_RANGE[1] - 1 <= cw <= BRIGHTNESS_RANGE[1]

    def test_full_warm_temperature_priority(self):
        """Full brightness with warm temperature, priority to temperature."""

        target_temperature = CONF_DEFAULT_WARM_LIGHT_TEMPERATURE

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            int(target_temperature),
            int(BRIGHTNESS_RANGE[1]),
            BrightnessTemperaturePriority.TEMPERATURE,
        )
        ww, cw = bc.compute_brightnesses()

        assert BRIGHTNESS_RANGE[1] - 1 <= ww <= BRIGHTNESS_RANGE[1]
        assert -1 <= cw <= 0

    def test_full_cold_brightness_priority(self):
        """Full brightness with cold temperature, priority to brightness."""

        target_temperature = CONF_DEFAULT_COLD_LIGHT_TEMPERATURE
        target_brightness = int(BRIGHTNESS_RANGE[1])
        priority = BrightnessTemperaturePriority.BRIGHTNESS

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            int(target_temperature),
            target_brightness,
            priority,
        )
        ww, cw = bc.compute_brightnesses()

        assert BRIGHTNESS_RANGE[1] - 1 <= ww <= BRIGHTNESS_RANGE[1], ww
        assert BRIGHTNESS_RANGE[1] - 1 <= cw <= BRIGHTNESS_RANGE[1], cw

    def test_full_warm_brightness_priority(self):
        """Full brightness with warm temperature, priority to brightness."""

        target_temperature = CONF_DEFAULT_WARM_LIGHT_TEMPERATURE
        target_brightness = int(BRIGHTNESS_RANGE[1])
        priority = BrightnessTemperaturePriority.BRIGHTNESS

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            int(target_temperature),
            target_brightness,
            priority,
        )
        ww, cw = bc.compute_brightnesses()

        assert BRIGHTNESS_RANGE[1] - 1 <= ww <= BRIGHTNESS_RANGE[1], ww
        assert BRIGHTNESS_RANGE[1] - 1 <= cw <= BRIGHTNESS_RANGE[1], cw

    def test_outside_range_mixed(self):
        """Test a (brightness, temperature) range outside the allowable range."""

        target_temperature = 5000
        target_brightness = int(BRIGHTNESS_RANGE[1])
        priority = BrightnessTemperaturePriority.MIXED

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            int(target_temperature),
            target_brightness,
            priority,
        )
        ww, cw = bc.compute_brightnesses()

        assert ww == 223
        assert cw == 255

    def test_outside_range_mixed_second_half(self):
        """Test a (brightness, temperature) range outside the allowable range, in the warmer region of the plot."""

        target_temperature = 3500
        target_brightness = int(BRIGHTNESS_RANGE[1])
        priority = BrightnessTemperaturePriority.MIXED

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            int(target_temperature),
            target_brightness,
            priority,
        )
        ww, cw = bc.compute_brightnesses()

        assert 254 <= ww <= 255
        assert cw == 234

    def test_6000_189_mixed(self):
        """Test a (brightness, temperature) range outside the allowable range, in a random point."""

        target_temperature = 6000
        target_brightness = 189
        priority = BrightnessTemperaturePriority.MIXED

        bc = BrightnessCalculator(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            target_temperature,
            target_brightness,
            priority,
        )
        ww, cw = bc.compute_brightnesses()

        assert ww == 65
        assert cw == 255


class TestComputeRgbwChannelBrightnesses:
    """Test the compute_rgbw_channel_brightnesses helper."""

    def test_warm_temperature_full_brightness(self):
        """At warm temperature the warm channel should be at target brightness, cold at 0."""
        ww, cw = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            BRIGHTNESS_RANGE[1],
        )
        assert ww == BRIGHTNESS_RANGE[1]
        assert cw == 0

    def test_cold_temperature_full_brightness(self):
        """At cold temperature the cold channel should be at target brightness, warm at 0."""
        ww, cw = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            BRIGHTNESS_RANGE[1],
        )
        assert ww == 0
        assert cw == BRIGHTNESS_RANGE[1]

    def test_midpoint_temperature_full_brightness(self):
        """At the mired midpoint both channels should equal target brightness."""
        warm_mired = color_temperature_kelvin_to_mired(CONF_DEFAULT_WARM_LIGHT_TEMPERATURE)
        cold_mired = color_temperature_kelvin_to_mired(CONF_DEFAULT_COLD_LIGHT_TEMPERATURE)
        mid_kelvin = color_temperature_mired_to_kelvin((warm_mired + cold_mired) / 2)

        ww, cw = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            mid_kelvin,
            BRIGHTNESS_RANGE[1],
        )
        # Both channels should be at or very near target brightness at midpoint temperature
        assert max(ww, cw) == BRIGHTNESS_RANGE[1]
        assert min(ww, cw) >= BRIGHTNESS_RANGE[1] - 3

    def test_brightness_is_max_of_channels(self):
        """max(warm, cold) must equal target_brightness for any temperature."""
        target_brightness = 200
        for temp in [3000, 3500, 4000, 4500, 5000, 5500, 6000]:
            ww, cw = compute_rgbw_channel_brightnesses(
                CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
                CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
                temp,
                target_brightness,
            )
            assert max(ww, cw) == target_brightness, (
                f"max channel {max(ww, cw)} != target_brightness {target_brightness} at {temp}K"
            )

    def test_dimmer_change_preserves_temperature_ratio(self):
        """Changing brightness must not change the warm-to-cold ratio (i.e. temperature).

        This is the fix for: 'setting the dimmer from 20% to 100% sets both channels
        to 100% regardless of temperature'.
        """
        target_temp = 3500  # warm-biased temperature

        ww_low, cw_low = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            target_temp,
            51,  # ~20 % brightness
        )
        ww_high, cw_high = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            target_temp,
            BRIGHTNESS_RANGE[1],  # 100 % brightness
        )

        # At 100 % the dominant channel must be 255, NOT both channels 255
        assert ww_high == BRIGHTNESS_RANGE[1]
        assert cw_high < BRIGHTNESS_RANGE[1]

        # The warm/cold ratio must be the same at both brightness levels
        ratio_low = ww_low / (ww_low + cw_low)
        ratio_high = ww_high / (ww_high + cw_high)
        assert abs(ratio_low - ratio_high) < 0.01

    def test_temperature_change_preserves_brightness(self):
        """Changing temperature must not change max(warm, cold).

        This is the fix for: 'when both channels are 100% and I click warm white,
        the dimmer changes to 50%'.
        """
        brightness = BRIGHTNESS_RANGE[1]  # 100 %

        # Both channels at 255 → midpoint temperature, 100 % brightness
        warm_mired = color_temperature_kelvin_to_mired(CONF_DEFAULT_WARM_LIGHT_TEMPERATURE)
        cold_mired = color_temperature_kelvin_to_mired(CONF_DEFAULT_COLD_LIGHT_TEMPERATURE)
        mid_kelvin = color_temperature_mired_to_kelvin((warm_mired + cold_mired) / 2)
        ww_mid, cw_mid = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            mid_kelvin,
            brightness,
        )
        assert max(ww_mid, cw_mid) == brightness

        # Switch to warm white → brightness must remain 100 %
        ww_warm, cw_warm = compute_rgbw_channel_brightnesses(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            brightness,
        )
        assert max(ww_warm, cw_warm) == brightness
