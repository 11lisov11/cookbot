from .models import (
    CoordinateCalibrationRequest,
    CoordinateCalibrationResponse,
    StepperMotionEstimateRequest,
    StepperMotionEstimateResponse,
)


MOTION_PROFILES = ("trapezoid", "s_curve")
_PROFILE_SCALE = 1024


def estimate_stepper_motion(request: StepperMotionEstimateRequest) -> StepperMotionEstimateResponse:
    step_period_us = request.step_delay_us + request.pulse_us
    step_frequency_hz = 1_000_000.0 / step_period_us
    steps_per_motor_revolution = (
        request.motor_full_steps_per_revolution * request.microsteps
    )
    steps_per_output_revolution = steps_per_motor_revolution * request.gearbox_ratio
    motor_rpm = step_frequency_hz * 60.0 / steps_per_motor_revolution
    output_rpm = motor_rpm / request.gearbox_ratio
    linear_speed_mm_s = None
    if request.travel_per_output_revolution_mm is not None:
        linear_speed_mm_s = (
            output_rpm * request.travel_per_output_revolution_mm / 60.0
        )

    return StepperMotionEstimateResponse(
        step_period_us=step_period_us,
        step_frequency_hz=step_frequency_hz,
        motor_rpm=motor_rpm,
        output_rpm=output_rpm,
        steps_per_motor_revolution=steps_per_motor_revolution,
        steps_per_output_revolution=steps_per_output_revolution,
        linear_speed_mm_s=linear_speed_mm_s,
    )


def calibrate_steps_per_unit(
    request: CoordinateCalibrationRequest,
) -> CoordinateCalibrationResponse:
    steps_per_unit = request.commanded_steps / request.measured_units
    return CoordinateCalibrationResponse(
        unit=request.unit,
        steps_per_unit=steps_per_unit,
        units_per_step=1.0 / steps_per_unit,
    )


def profiled_step_delay_us(
    step_index: int,
    total_steps: int,
    start_delay_us: int,
    min_delay_us: int,
    accel_steps: int,
    decel_steps: int,
    motion_profile: str,
) -> int:
    """Mirror the Mega fixed-point commissioning profile without touching hardware."""
    if motion_profile not in MOTION_PROFILES:
        raise ValueError("invalid_motion_profile")
    if total_steps < 1 or step_index < 0 or step_index >= total_steps:
        raise ValueError("invalid_profile_step")
    if min_delay_us < 1 or start_delay_us < min_delay_us:
        raise ValueError("invalid_profile_timing")
    if accel_steps < 0 or decel_steps < 0:
        raise ValueError("invalid_profile_ramp")

    delay_us = min_delay_us
    delta_us = start_delay_us - min_delay_us
    if accel_steps > 0 and step_index < accel_steps:
        progress = _profile_progress(step_index, accel_steps, motion_profile)
        delay_us = max(
            delay_us,
            start_delay_us - ((delta_us * progress) // _PROFILE_SCALE),
        )

    steps_remaining = total_steps - step_index - 1
    if decel_steps > 0 and steps_remaining < decel_steps:
        decel_index = decel_steps - steps_remaining
        progress = _profile_progress(decel_index, decel_steps, motion_profile)
        delay_us = max(
            delay_us,
            min_delay_us + ((delta_us * progress) // _PROFILE_SCALE),
        )
    return delay_us


def _profile_progress(numerator: int, denominator: int, motion_profile: str) -> int:
    progress = min(_PROFILE_SCALE, max(0, numerator * _PROFILE_SCALE // denominator))
    if motion_profile == "trapezoid":
        return progress
    squared = progress * progress // _PROFILE_SCALE
    return squared * (3 * _PROFILE_SCALE - 2 * progress) // _PROFILE_SCALE
