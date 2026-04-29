"""Test the helper utilities."""

from custom_components.color_temperature_light_mixer.const import (
    CONF_CCT_CAL_COLD_PCT,
    CONF_CCT_CAL_TEMP,
    CONF_CCT_CAL_WARM_PCT,
    CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
    CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
    default_calibration_points,
)
from custom_components.color_temperature_light_mixer.helper import (
    BRIGHTNESS_RANGE,
    BrightnessCalculator,
    BrightnessTemperaturePriority,
    compute_brightnesses_from_calibration,
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


class TestComputeBrightnessesFromCalibration:
    """Test compute_brightnesses_from_calibration."""

    def _default_cal(self):
        return default_calibration_points(
            CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
            CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
        )

    def test_default_calibration_warm_end(self):
        """At the warm endpoint, warm channel should be at target brightness, cold at 0."""
        cal = self._default_cal()
        ww, cw = compute_brightnesses_from_calibration(
            cal, CONF_DEFAULT_WARM_LIGHT_TEMPERATURE, BRIGHTNESS_RANGE[1]
        )
        assert ww == BRIGHTNESS_RANGE[1]
        assert cw == 0

    def test_default_calibration_cold_end(self):
        """At the cold endpoint, cold channel should be at target brightness, warm at 0."""
        cal = self._default_cal()
        ww, cw = compute_brightnesses_from_calibration(
            cal, CONF_DEFAULT_COLD_LIGHT_TEMPERATURE, BRIGHTNESS_RANGE[1]
        )
        assert ww == 0
        assert cw == BRIGHTNESS_RANGE[1]

    def test_default_calibration_matches_linear_formula(self):
        """Default calibration points should reproduce the linear mired formula."""
        cal = self._default_cal()
        for temp in [3000, 3500, 4000, 4500, 5000, 5500, 6000]:
            ww_cal, cw_cal = compute_brightnesses_from_calibration(
                cal, temp, BRIGHTNESS_RANGE[1]
            )
            ww_lin, cw_lin = compute_rgbw_channel_brightnesses(
                CONF_DEFAULT_WARM_LIGHT_TEMPERATURE,
                CONF_DEFAULT_COLD_LIGHT_TEMPERATURE,
                temp,
                BRIGHTNESS_RANGE[1],
            )
            assert abs(ww_cal - ww_lin) <= 4, (
                f"Warm mismatch at {temp}K: cal={ww_cal}, linear={ww_lin}"
            )
            assert abs(cw_cal - cw_lin) <= 4, (
                f"Cold mismatch at {temp}K: cal={cw_cal}, linear={cw_lin}"
            )

    def test_dominant_channel_equals_target_brightness(self):
        """max(warm, cold) must equal target_brightness for any temperature."""
        cal = self._default_cal()
        target_brightness = 200
        for temp in [3000, 3500, 4000, 4500, 5000, 5500, 6000]:
            ww, cw = compute_brightnesses_from_calibration(cal, temp, target_brightness)
            assert max(ww, cw) == target_brightness, (
                f"max channel {max(ww, cw)} != {target_brightness} at {temp}K"
            )

    def test_custom_calibration_4500k(self):
        """Custom calibration point: 4500K = 40% warm, 50% cold."""
        cal = [
            {CONF_CCT_CAL_TEMP: 3000, CONF_CCT_CAL_WARM_PCT: 100, CONF_CCT_CAL_COLD_PCT: 0},
            {CONF_CCT_CAL_TEMP: 4500, CONF_CCT_CAL_WARM_PCT: 40, CONF_CCT_CAL_COLD_PCT: 50},
            {CONF_CCT_CAL_TEMP: 6000, CONF_CCT_CAL_WARM_PCT: 0, CONF_CCT_CAL_COLD_PCT: 100},
        ]
        target_brightness = 200
        ww, cw = compute_brightnesses_from_calibration(cal, 4500, target_brightness)
        # cold dominates (50 > 40), so cold = target_brightness
        # warm = round(200 * 40/50) = 160
        assert cw == target_brightness
        assert ww == round(target_brightness * 40 / 50)

    def test_clamp_below_range(self):
        """Temperatures below the calibration range should be clamped to the first point."""
        cal = self._default_cal()
        ww_at_min, cw_at_min = compute_brightnesses_from_calibration(
            cal, CONF_DEFAULT_WARM_LIGHT_TEMPERATURE, BRIGHTNESS_RANGE[1]
        )
        ww_below, cw_below = compute_brightnesses_from_calibration(
            cal, 1000, BRIGHTNESS_RANGE[1]
        )
        assert ww_at_min == ww_below
        assert cw_at_min == cw_below

    def test_clamp_above_range(self):
        """Temperatures above the calibration range should be clamped to the last point."""
        cal = self._default_cal()
        ww_at_max, cw_at_max = compute_brightnesses_from_calibration(
            cal, CONF_DEFAULT_COLD_LIGHT_TEMPERATURE, BRIGHTNESS_RANGE[1]
        )
        ww_above, cw_above = compute_brightnesses_from_calibration(
            cal, 9999, BRIGHTNESS_RANGE[1]
        )
        assert ww_at_max == ww_above
        assert cw_at_max == cw_above

    def test_brightness_scaling(self):
        """Warm/cold ratio must be the same across different brightness levels."""
        cal = self._default_cal()
        target_temp = 4000
        ww_low, cw_low = compute_brightnesses_from_calibration(cal, target_temp, 51)
        ww_high, cw_high = compute_brightnesses_from_calibration(
            cal, target_temp, BRIGHTNESS_RANGE[1]
        )
        ratio_low = ww_low / (ww_low + cw_low)
        ratio_high = ww_high / (ww_high + cw_high)
        assert abs(ratio_low - ratio_high) < 0.02


class TestDefaultCalibrationPoints:
    """Test the default_calibration_points helper."""

    def test_returns_correct_count(self):
        """Should return exactly CCT_CALIBRATION_POINT_COUNT points."""
        from custom_components.color_temperature_light_mixer.const import (
            CCT_CALIBRATION_POINT_COUNT,
        )
        cal = default_calibration_points(3000, 6000)
        assert len(cal) == CCT_CALIBRATION_POINT_COUNT

    def test_endpoints(self):
        """First point is 100% warm; last point is 100% cold."""
        cal = default_calibration_points(3000, 6000)
        assert cal[0][CONF_CCT_CAL_WARM_PCT] == 100
        assert cal[0][CONF_CCT_CAL_COLD_PCT] == 0
        assert cal[-1][CONF_CCT_CAL_WARM_PCT] == 0
        assert cal[-1][CONF_CCT_CAL_COLD_PCT] == 100

    def test_temperatures_ascending(self):
        """Calibration temperatures must be in ascending order."""
        cal = default_calibration_points(3000, 6000)
        temps = [p[CONF_CCT_CAL_TEMP] for p in cal]
        assert temps == sorted(temps)
