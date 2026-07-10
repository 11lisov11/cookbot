from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AxisState(BaseModel):
    id: str
    commanded_position: float = 0.0
    min_position: float = -45.0
    max_position: float = 45.0
    homed: bool = False
    calibrated: bool = False
    moving: bool = False
    limit_min: bool = False
    limit_max: bool = False


class GripperState(BaseModel):
    position: float = 0.0
    homed: bool = False
    calibrated: bool = False
    moving: bool = False


class SystemState(BaseModel):
    mode: str = "simulator"
    estop: bool = False
    homed: bool = False
    calibrated: bool = False
    motion_enabled: bool = False
    services: dict[str, str] = Field(default_factory=dict)
    axes: list[AxisState] = Field(default_factory=list)
    gripper: GripperState = Field(default_factory=GripperState)
    limit_switches: dict[str, bool] = Field(default_factory=dict)
    queue_depth: int = 0
    last_error: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: Literal["CookBot"] = "CookBot"
    mode: str
    services: dict[str, str]


class PublicSettings(BaseModel):
    app: Literal["CookBot"] = "CookBot"
    mode: str
    mega_transport: str
    camera: str
    ai: str
    bind: str
    port: int
    api_auth_required: bool
    bluetooth_configured: bool = False
    bluetooth_channel: int | None = None


class VersionResponse(BaseModel):
    app: Literal["CookBot"] = "CookBot"
    backend_version: str
    git_commit: str
    build_mode: str
    api_schema_version: str = "1"
    hardware_configured: bool = False


class JointMoveRequest(BaseModel):
    position: float
    speed: float = Field(default=0.25, ge=0.01, le=1.0)


class GripperRequest(BaseModel):
    position: float = Field(ge=0.0, le=1.0)


class CameraSnapshot(BaseModel):
    mode: Literal["mock", "libcamera"]
    media_type: str
    data_base64: str
    data_url: str
    created_at: datetime = Field(default_factory=utc_now)


class CalibrationAxis(BaseModel):
    id: str
    min_position: float
    max_position: float
    homed: bool
    calibrated: bool


class CalibrationProfile(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    saved_at: datetime = Field(default_factory=utc_now)
    axes: list[CalibrationAxis]
    gripper_min: float = 0.0
    gripper_max: float = 1.0
    note: str = "Simulator calibration profile; verify real hardware before motion."


class CalibrationStatus(BaseModel):
    loaded: bool
    path: str
    profile: CalibrationProfile | None = None
    state_axes: list[CalibrationAxis] = Field(default_factory=list)


class MegaRequest(BaseModel):
    id: str
    command: str
    args: dict[str, Any] = Field(default_factory=dict)


class MegaResponse(BaseModel):
    id: str
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class MegaCapabilities(BaseModel):
    protocol_version: int = 1
    firmware: str
    version: str
    hardware_configured: bool = False
    supported_commands: list[str] = Field(default_factory=list)
    motion_commands_enabled: bool = False


class DiagnosticCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class ChecklistItem(BaseModel):
    id: str
    label: str
    ok: bool
    detail: str = ""


class DiagnosticsResponse(BaseModel):
    ok: bool
    checks: list[DiagnosticCheck]


class FaultInjectionRequest(BaseModel):
    code: str
    joint_id: str | None = None
    message: str | None = None


class AICommandRequest(BaseModel):
    command: str
    include_snapshot: bool = True


class AIPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AIPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[AIPlanStep]
    notes: str | None = None


class AICommandResponse(BaseModel):
    accepted: bool
    plan: AIPlan | None = None
    rejected_reason: str | None = None


class RecipeSummary(BaseModel):
    id: str
    name: str
    locked: bool = False
    description: str = ""


class RecipePreflightResponse(BaseModel):
    recipe_id: str
    ok: bool
    reasons: list[str] = Field(default_factory=list)
    checks: list[ChecklistItem] = Field(default_factory=list)


class RecipeRunResponse(BaseModel):
    recipe_id: str
    accepted: bool
    executed_steps: int = 0
    rejected_reason: str | None = None


class RecipeRuntimeStatus(BaseModel):
    active_recipe_id: str | None = None
    running: bool = False
    paused: bool = False
    aborted: bool = False
    current_step: int = 0
    total_steps: int = 0
    last_message: str | None = None


class CommandLogEntry(BaseModel):
    timestamp: datetime
    source: str
    event: str
    command_id: str | None = None
    rejected_reason: str | None = None
    errors: Any | None = None


class WorkspaceZone(BaseModel):
    id: str
    name: str
    kind: Literal["safe", "keepout", "ingredient", "tool", "vessel"]
    description: str
    verified: bool = False


class WorkspaceModel(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    verified_for_real_motion: bool = False
    zones: list[WorkspaceZone] = Field(default_factory=list)


class HardwareReadinessItem(BaseModel):
    id: str
    label: str
    verified: bool = False
    evidence: str | None = None


class HardwareReadinessResponse(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    ready_for_real_motion: bool = False
    items: list[HardwareReadinessItem] = Field(default_factory=list)


class HardwareGateBlocker(BaseModel):
    id: str
    label: str
    detail: str
    severity: Literal["blocker", "warning"] = "blocker"


class HardwareGateReport(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    ready_for_real_motion: bool = False
    real_motion_locked: bool = True
    hardware_configured: bool = False
    required_mode: Literal["hardware"] = "hardware"
    required_mega_transport: str = "serial_or_bluetooth_rfcomm"
    allowed_mega_transports: list[str] = Field(
        default_factory=lambda: ["serial", "bluetooth_rfcomm"]
    )
    verified_count: int = 0
    evidence_count: int = 0
    total_count: int = 0
    blockers: list[HardwareGateBlocker] = Field(default_factory=list)


class CalibrationWizardStatus(BaseModel):
    active: bool = False
    completed: bool = False
    current_step: int = 0
    total_steps: int = 0
    current_step_id: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    last_message: str | None = None


class AcceptanceReport(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    ok: bool
    items: list[ChecklistItem] = Field(default_factory=list)


class ExportBundle(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    state: SystemState
    diagnostics: DiagnosticsResponse
    acceptance: AcceptanceReport
    recipes: list[RecipeSummary]
    workspace: WorkspaceModel
    hardware_readiness: HardwareReadinessResponse
    calibration: CalibrationStatus


class BackupBundle(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    kind: Literal["cookbot_backup"] = "cookbot_backup"
    backup_version: Literal["1"] = "1"
    created_at: datetime = Field(default_factory=utc_now)
    workspace: WorkspaceModel
    hardware_readiness: HardwareReadinessResponse
    calibration: CalibrationStatus
    recipes: list[RecipeSummary]
    acceptance: AcceptanceReport


class RestoreValidationResponse(BaseModel):
    valid: bool
    reasons: list[str] = Field(default_factory=list)
    accepted_sections: list[str] = Field(default_factory=list)
    applies_real_motion_settings: bool = False


class ProductReadinessResponse(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    ok: bool
    status: str
    acceptance: AcceptanceReport
    diagnostics: DiagnosticsResponse
    hardware_readiness: HardwareReadinessResponse
    items: list[ChecklistItem] = Field(default_factory=list)


class CommissioningCommand(BaseModel):
    id: str
    label: str
    command: str
    description: str = ""


class CommissioningGuideResponse(BaseModel):
    project: Literal["CookBot"] = "CookBot"
    ok: bool = True
    real_motion_locked: bool = True
    ready_for_real_motion: bool = False
    steps: list[ChecklistItem] = Field(default_factory=list)
    commands: list[CommissioningCommand] = Field(default_factory=list)
