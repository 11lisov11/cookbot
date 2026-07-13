from .models import (
    CoordinateCalibrationRequest,
    CoordinateCalibrationResponse,
    StepperMotionEstimateRequest,
    StepperMotionEstimateResponse,
)


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
