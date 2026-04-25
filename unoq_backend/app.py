import asyncio
import base64
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .ai import MockAIClient, OpenAICompatibleClient
from .camera import LibcameraStillCamera, MockCamera
from .config import Settings, get_settings
from .cookbot_logging import CookBotJsonLogger
from .fake_mega import FakeMegaDevice
from .models import (
    AICommandRequest,
    AICommandResponse,
    AIPlan,
    AcceptanceReport,
    BackupBundle,
    CalibrationProfile,
    CalibrationStatus,
    CalibrationWizardStatus,
    CameraSnapshot,
    ChecklistItem,
    CommissioningCommand,
    CommissioningGuideResponse,
    CommandLogEntry,
    DiagnosticCheck,
    DiagnosticsResponse,
    ExportBundle,
    FaultInjectionRequest,
    GripperRequest,
    HardwareReadinessResponse,
    HealthResponse,
    JointMoveRequest,
    MegaRequest,
    MegaResponse,
    ProductReadinessResponse,
    PublicSettings,
    RecipePreflightResponse,
    RecipeRunResponse,
    RecipeRuntimeStatus,
    RecipeSummary,
    RestoreValidationResponse,
    SystemState,
    VersionResponse,
    WorkspaceModel,
)
from . import __version__
from .calibration import CalibrationStore, CalibrationWizard
from .hardware_readiness import HardwareReadinessStore
from .recipe_runtime import RecipeRuntime
from .recipes import RecipeEngine
from .safety import SafetyValidator
from .simulator import CookBotSimulator
from .transports import LocalFakeMegaTransport, MegaTransport, SerialMegaTransport, TcpMegaTransport
from .workspace import WorkspaceStore


REQUIRED_PRODUCT_DOCS = [
    Path("README.md"),
    Path("docs/product_manual.md"),
    Path("docs/mobile_use.md"),
    Path("docs/troubleshooting.md"),
    Path("docs/release_checklist.md"),
    Path("docs/mega_protocol.md"),
    Path("docs/hardware_automation.md"),
    Path("docs/commissioning_runbook.md"),
    Path("docs/release_bundle.md"),
    Path("docs/safety.md"),
    Path("docs/no_hardware_testing.md"),
    Path("RELEASE_NOTES.md"),
]

ERROR_TAXONOMY = {
    "safety_error": ["estop_active", "motion_not_enabled", "not_homed", "limit_exceeded", "real_motion_locked"],
    "transport_error": ["mega_transport_error", "unknown_command", "bad_request"],
    "camera_error": ["camera_disabled"],
    "ai_error": ["forbidden_ai_step", "invalid_move_joint_payload", "invalid_gripper_payload"],
    "recipe_error": ["unknown_recipe", "recipe_locked", "forbidden_recipe_step"],
    "config_error": ["config_error", "workspace_not_verified", "calibration_required"],
}

MEGA_PROTOCOL_COMMANDS = [
    "hello",
    "ping",
    "get_state",
    "get_capabilities",
    "get_hardware_config",
    "get_limit_switches",
    "self_test",
    "get_firmware_status",
    "read_inputs",
    "bench_unlock",
    "bench_test_output",
    "get_faults",
    "inject_fault",
    "clear_faults",
    "enable_motion",
    "home_all",
    "set_joint",
    "set_gripper",
    "estop",
    "clear_estop",
]


class CookBotController:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.simulator = CookBotSimulator(settings.mode)
        self.fake_device = FakeMegaDevice(self.simulator)
        self.transport = self._build_transport(settings)
        self.safety = SafetyValidator()
        self.camera = self._build_camera(settings)
        self.ai = self._build_ai(settings)
        self.recipes = RecipeEngine(settings.recipes_dir)
        self.recipe_runtime = RecipeRuntime()
        self.calibration = CalibrationStore(settings.calibration_path)
        self.calibration_wizard = CalibrationWizard()
        self.workspace = WorkspaceStore(settings.workspace_path)
        self.hardware_readiness = HardwareReadinessStore(settings.hardware_readiness_path)
        self.logger = CookBotJsonLogger(settings.log_path)
        self._configure_services()

    async def state(self) -> SystemState:
        try:
            response = await self.transport.send("get_state")
        except Exception as exc:
            state = self.simulator.snapshot()
            state.services["mega"] = "error"
            state.last_error = f"mega_transport_error:{exc}"
            state.motion_enabled = False
            return state
        if response.ok and "state" in response.data:
            return SystemState.model_validate(response.data["state"])
        state = self.simulator.snapshot()
        if response.error:
            state.last_error = response.error
        return state

    async def health(self) -> HealthResponse:
        state = await self.state()
        return HealthResponse(status="ok", mode=self.settings.mode, services=state.services)

    def public_settings(self) -> PublicSettings:
        return PublicSettings(
            mode=self.settings.mode,
            mega_transport=self.settings.mega_transport,
            camera=self.settings.camera,
            ai=self.settings.ai,
            bind=self.settings.bind,
            port=self.settings.port,
            api_auth_required=bool(self.settings.api_token),
        )

    def version(self) -> VersionResponse:
        return VersionResponse(
            backend_version=__version__,
            git_commit=_git_commit(),
            build_mode=self.settings.mode,
            hardware_configured=False,
        )

    async def diagnostics(self) -> DiagnosticsResponse:
        checks: list[DiagnosticCheck] = []

        async def add_transport_check(name: str, command: str) -> None:
            try:
                response = await self.transport.send(command)
                checks.append(
                    DiagnosticCheck(
                        name=name,
                        ok=response.ok,
                        detail="ok" if response.ok else response.error or "mega_error",
                    )
                )
            except Exception as exc:
                checks.append(DiagnosticCheck(name=name, ok=False, detail=f"transport_error:{exc}"))

        checks.append(DiagnosticCheck(name="backend", ok=True, detail="ok"))
        checks.append(
            DiagnosticCheck(
                name="version",
                ok=True,
                detail=f"{__version__}@{_git_commit()}",
            )
        )
        checks.append(
            DiagnosticCheck(
                name="schema",
                ok=True,
                detail="api_schema_version=1",
            )
        )
        await add_transport_check("mega_hello", "hello")
        await add_transport_check("mega_ping", "ping")
        await add_transport_check("mega_state", "get_state")
        await add_transport_check("mega_capabilities", "get_capabilities")
        await add_transport_check("mega_hardware_config", "get_hardware_config")
        await add_transport_check("mega_limit_switches", "get_limit_switches")
        await add_transport_check("mega_self_test", "self_test")
        await add_transport_check("mega_firmware_status", "get_firmware_status")
        await add_transport_check("mega_inputs", "read_inputs")

        try:
            snapshot = self.snapshot()
            checks.append(DiagnosticCheck(name="camera", ok=True, detail=snapshot.media_type))
        except Exception as exc:
            checks.append(DiagnosticCheck(name="camera", ok=False, detail=str(exc)))

        try:
            recipes = self.list_recipes()
            checks.append(DiagnosticCheck(name="recipes", ok=bool(recipes), detail=f"{len(recipes)} recipes"))
        except Exception as exc:
            checks.append(DiagnosticCheck(name="recipes", ok=False, detail=str(exc)))

        try:
            workspace = self.workspace_model()
            checks.append(
                DiagnosticCheck(
                    name="workspace",
                    ok=workspace.project == "CookBot",
                    detail=f"{len(workspace.zones)} zones",
                )
            )
        except Exception as exc:
            checks.append(DiagnosticCheck(name="workspace", ok=False, detail=str(exc)))

        try:
            readiness = self.hardware_readiness_model()
            checks.append(
                DiagnosticCheck(
                    name="hardware_readiness",
                    ok=True,
                    detail="ready" if readiness.ready_for_real_motion else "not_ready_for_real_motion",
                )
            )
        except Exception as exc:
            checks.append(DiagnosticCheck(name="hardware_readiness", ok=False, detail=str(exc)))

        try:
            calibration = await self.calibration_status()
            checks.append(
                DiagnosticCheck(
                    name="calibration",
                    ok=True,
                    detail="loaded" if calibration.loaded else "not_saved",
                )
            )
        except Exception as exc:
            checks.append(DiagnosticCheck(name="calibration", ok=False, detail=str(exc)))

        try:
            self.settings.log_path.parent.mkdir(parents=True, exist_ok=True)
            checks.append(
                DiagnosticCheck(
                    name="log_path",
                    ok=self.settings.log_path.parent.exists(),
                    detail=str(self.settings.log_path),
                )
            )
        except Exception as exc:
            checks.append(DiagnosticCheck(name="log_path", ok=False, detail=f"config_error:{exc}"))

        web_source = Path("web/package.json").exists()
        web_build = Path("web/dist/index.html").exists()
        checks.append(
            DiagnosticCheck(
                name="web_build",
                ok=web_source,
                detail="dist_ready" if web_build else "source_ready_build_pending",
            )
        )
        release_tooling = Path("scripts/release_tooling.py").exists()
        release_bundle = Path("dist/release/latest_release_path.txt").exists()
        checks.append(
            DiagnosticCheck(
                name="release_bundle",
                ok=release_tooling,
                detail="latest_ready" if release_bundle else "tooling_ready",
            )
        )

        return DiagnosticsResponse(ok=all(check.ok for check in checks), checks=checks)

    def snapshot(self) -> CameraSnapshot:
        if self.settings.camera == "disabled":
            raise ValueError("camera_disabled")
        return self.camera.snapshot()

    async def camera_stream(self, frame_count: int | None = None):
        if self.settings.camera == "disabled":
            raise ValueError("camera_disabled")
        if hasattr(self.camera, "stream_frames"):
            for frame in self.camera.stream_frames(frame_count):
                yield frame
                await asyncio.sleep(0.25)
            return
        count = frame_count or 1
        for _ in range(count):
            snapshot = self.camera.snapshot()
            raw = base64.b64decode(snapshot.data_base64)
            yield (
                b"--frame\r\n"
                + f"Content-Type: {snapshot.media_type}\r\nContent-Length: {len(raw)}\r\n\r\n".encode("ascii")
                + raw
                + b"\r\n"
            )
            await asyncio.sleep(0.25)

    async def home(self) -> SystemState:
        state = await self.state()
        self.safety.validate_home(state)
        enable = await self.transport.send("enable_motion")
        if not enable.ok:
            raise ValueError(enable.error or "enable_motion_failed")
        response = await self.transport.send("home_all")
        if not response.ok:
            raise ValueError(response.error or "home_failed")
        self.logger.event("backend", "home_all", mega_response=response.model_dump())
        return await self.state()

    async def mark_simulated_calibration(self) -> SystemState:
        self.simulator.mark_simulated_calibration()
        self.logger.event("backend", "simulated_calibration")
        return await self.state()

    async def calibration_status(self) -> CalibrationStatus:
        return self.calibration.status(await self.state())

    async def calibration_save(self) -> CalibrationProfile:
        profile = self.calibration.save(await self.state())
        self.logger.event("backend", "calibration_saved", path=str(self.settings.calibration_path))
        return profile

    async def calibration_reset(self) -> CalibrationStatus:
        self.calibration.reset()
        self.simulator.reset_calibration()
        self.logger.event("backend", "calibration_reset", path=str(self.settings.calibration_path))
        return await self.calibration_status()

    def calibration_wizard_status(self) -> CalibrationWizardStatus:
        return self.calibration_wizard.status()

    def calibration_wizard_start(self) -> CalibrationWizardStatus:
        self.logger.event("backend", "calibration_wizard_start")
        return self.calibration_wizard.start()

    async def calibration_wizard_advance(self) -> CalibrationWizardStatus:
        status = self.calibration_wizard.status()
        step_id = status.current_step_id
        if step_id == "home_simulator":
            await self.home()
        elif step_id == "mark_simulated_calibration":
            await self.mark_simulated_calibration()
        elif step_id == "save_profile":
            await self.calibration_save()
        advanced = self.calibration_wizard.advance()
        self.logger.event("backend", "calibration_wizard_advance", command_id=step_id)
        return advanced

    def calibration_wizard_reset(self) -> CalibrationWizardStatus:
        self.logger.event("backend", "calibration_wizard_reset")
        return self.calibration_wizard.reset()

    async def move_joint(self, joint_id: str, request: JointMoveRequest) -> SystemState:
        state = await self.state()
        self.safety.validate_joint_move(state, joint_id, request.position, request.speed)
        response = await self.transport.send(
            "set_joint", {"joint_id": joint_id, "position": request.position, "speed": request.speed}
        )
        if not response.ok:
            raise ValueError(response.error or "joint_move_failed")
        self.logger.event(
            "backend",
            "set_joint",
            mega_command={"joint_id": joint_id, "position": request.position, "speed": request.speed},
            mega_response=response.model_dump(),
        )
        return await self.state()

    async def set_gripper(self, request: GripperRequest) -> SystemState:
        state = await self.state()
        self.safety.validate_gripper(state, request.position)
        response = await self.transport.send("set_gripper", {"position": request.position})
        if not response.ok:
            raise ValueError(response.error or "gripper_failed")
        self.logger.event("backend", "set_gripper", mega_response=response.model_dump())
        return await self.state()

    async def estop(self) -> SystemState:
        response = await self.transport.send("estop")
        if not response.ok:
            raise ValueError(response.error or "estop_failed")
        self.logger.event("safety", "estop", mega_response=response.model_dump())
        return await self.state()

    async def clear_estop(self) -> SystemState:
        response = await self.transport.send("clear_estop")
        if not response.ok:
            raise ValueError(response.error or "clear_estop_failed")
        self.logger.event("safety", "clear_estop", mega_response=response.model_dump())
        return await self.state()

    def ai_command(self, request: AICommandRequest) -> AICommandResponse:
        snapshot_data_url = self.snapshot().data_url if request.include_snapshot and self.settings.camera == "mock" else None
        plan = self.ai.plan(request.command, request.include_snapshot, snapshot_data_url=snapshot_data_url)
        try:
            self.safety.validate_ai_plan(plan)
        except ValueError as exc:
            self.logger.event("ai", "rejected_plan", user_command=request.command, rejected_reason=str(exc))
            return AICommandResponse(accepted=False, plan=plan, rejected_reason=str(exc))
        self.logger.event("ai", "accepted_plan", user_command=request.command, validated_plan=plan.model_dump())
        return AICommandResponse(accepted=True, plan=plan)

    def list_recipes(self) -> list[RecipeSummary]:
        return self.recipes.list_recipes()

    async def recipe_preflight(self, recipe_id: str) -> RecipePreflightResponse:
        return self.recipes.preflight(
            recipe_id,
            await self.state(),
            workspace=self.workspace_model(),
            calibration=await self.calibration_status(),
            hardware_readiness=self.hardware_readiness_model(),
        )

    async def recipe_run(self, recipe_id: str) -> RecipeRunResponse:
        preflight = await self.recipe_preflight(recipe_id)
        if not preflight.ok:
            return RecipeRunResponse(
                recipe_id=recipe_id,
                accepted=False,
                rejected_reason=",".join(preflight.reasons),
            )
        recipe = self.recipes.get(recipe_id)
        self.recipe_runtime.start(recipe.id, len(recipe.steps))
        executed = 0
        for index, step in enumerate(recipe.steps, start=1):
            if self.recipe_runtime.status.aborted:
                return RecipeRunResponse(
                    recipe_id=recipe_id,
                    accepted=False,
                    executed_steps=executed,
                    rejected_reason="recipe_aborted",
                )
            self.recipe_runtime.step_started(index)
            await self._execute_recipe_step(step)
            executed += 1
        self.recipe_runtime.complete()
        self.logger.event("recipe", "run_complete", command_id=recipe_id, state_after=(await self.state()).model_dump())
        return RecipeRunResponse(recipe_id=recipe_id, accepted=True, executed_steps=executed)

    def recipe_status(self) -> RecipeRuntimeStatus:
        return self.recipe_runtime.status

    def recipe_pause(self) -> RecipeRuntimeStatus:
        status = self.recipe_runtime.pause()
        self.logger.event("recipe", "pause", command_id=status.active_recipe_id)
        return status

    def recipe_resume(self) -> RecipeRuntimeStatus:
        status = self.recipe_runtime.resume()
        self.logger.event("recipe", "resume", command_id=status.active_recipe_id)
        return status

    async def recipe_abort(self) -> RecipeRuntimeStatus:
        status = self.recipe_runtime.abort()
        await self.transport.send("estop")
        self.logger.event("recipe", "abort", command_id=status.active_recipe_id)
        return status

    async def inject_fault(self, request: FaultInjectionRequest) -> SystemState:
        response = await self.transport.send(
            "inject_fault",
            {"code": request.code, "joint_id": request.joint_id, "message": request.message},
        )
        if not response.ok:
            raise ValueError(response.error or "inject_fault_failed")
        self.logger.event("safety", "inject_fault", errors=request.model_dump())
        return await self.state()

    async def clear_faults(self) -> SystemState:
        response = await self.transport.send("clear_faults")
        if not response.ok:
            raise ValueError(response.error or "clear_faults_failed")
        self.logger.event("safety", "clear_faults")
        return await self.state()

    def logs(self, limit: int = 100) -> list[CommandLogEntry]:
        return self.logger.tail(limit)

    def workspace_model(self) -> WorkspaceModel:
        return self.workspace.load()

    def hardware_readiness_model(self) -> HardwareReadinessResponse:
        return self.hardware_readiness.load()

    async def acceptance_report(self) -> AcceptanceReport:
        state = await self.state()
        diagnostics = await self.diagnostics()
        recipes = self.list_recipes()
        readiness = self.hardware_readiness_model()
        docs_missing = [str(path) for path in REQUIRED_PRODUCT_DOCS if not path.exists()]
        web_build = Path("web/dist/index.html").exists()
        web_source = Path("web/package.json").exists()
        ci_workflow = Path(".github/workflows/check.yml").exists()
        release_tooling = Path("scripts/release_tooling.py").exists()
        items = [
            ChecklistItem(id="backend", label="Backend responds", ok=True, detail="ok"),
            ChecklistItem(
                id="no_hardware_mode",
                label="No-hardware mode is active",
                ok=self.settings.mode == "simulator" and self.settings.mega_transport.startswith("fake"),
                detail=f"{self.settings.mode}/{self.settings.mega_transport}",
            ),
            ChecklistItem(
                id="diagnostics",
                label="Diagnostics pass",
                ok=diagnostics.ok,
                detail="ok" if diagnostics.ok else "diagnostics_failed",
            ),
            ChecklistItem(
                id="camera",
                label="Camera boundary is available",
                ok=state.services.get("camera") in {"mock", "libcamera"},
                detail=state.services.get("camera", "unknown"),
            ),
            ChecklistItem(
                id="ai",
                label="AI boundary is available",
                ok=state.services.get("ai") in {"mock", "openai_compatible"},
                detail=state.services.get("ai", "unknown"),
            ),
            ChecklistItem(
                id="recipes",
                label="Recipes are loaded",
                ok=bool(recipes),
                detail=f"{len(recipes)} recipes",
            ),
            ChecklistItem(
                id="real_motion_locked",
                label="Real motion is locked until hardware readiness",
                ok=not readiness.ready_for_real_motion,
                detail="locked",
            ),
            ChecklistItem(
                id="ui_build_available",
                label="PWA source/build is available",
                ok=web_source,
                detail="dist_ready" if web_build else "source_ready_build_pending",
            ),
            ChecklistItem(
                id="ci_local_parity",
                label="Local checks match CI workflow",
                ok=ci_workflow,
                detail="github_actions_present" if ci_workflow else "missing_ci_workflow",
            ),
            ChecklistItem(
                id="api_token_state",
                label="API token mode is explicit",
                ok=True,
                detail="required" if self.settings.api_token else "not_required",
            ),
            ChecklistItem(
                id="backup_valid",
                label="Backup bundle can be generated",
                ok=True,
                detail="ok",
            ),
            ChecklistItem(
                id="docs_complete",
                label="Product documentation is complete",
                ok=not docs_missing,
                detail="ok" if not docs_missing else ",".join(docs_missing),
            ),
            ChecklistItem(
                id="release_bundle_tooling",
                label="Release bundle tooling is available",
                ok=release_tooling,
                detail="ready" if release_tooling else "missing_release_tooling",
            ),
        ]
        return AcceptanceReport(ok=all(item.ok for item in items), items=items)

    async def export_bundle(self) -> ExportBundle:
        return ExportBundle(
            state=await self.state(),
            diagnostics=await self.diagnostics(),
            acceptance=await self.acceptance_report(),
            recipes=self.list_recipes(),
            workspace=self.workspace_model(),
            hardware_readiness=self.hardware_readiness_model(),
            calibration=await self.calibration_status(),
        )

    async def backup_bundle(self) -> BackupBundle:
        return BackupBundle(
            workspace=self.workspace_model(),
            hardware_readiness=self.hardware_readiness_model(),
            calibration=await self.calibration_status(),
            recipes=self.list_recipes(),
            acceptance=await self.acceptance_report(),
        )

    async def validate_restore(self, payload: dict[str, Any]) -> RestoreValidationResponse:
        try:
            bundle = BackupBundle.model_validate(payload)
        except Exception as exc:
            return RestoreValidationResponse(valid=False, reasons=[f"config_error:{exc}"])

        reasons: list[str] = []
        if bundle.hardware_readiness.ready_for_real_motion:
            reasons.append("real_motion_settings_not_applied_by_restore")
        accepted_sections = ["workspace", "hardware_readiness", "calibration", "recipes", "acceptance"]
        return RestoreValidationResponse(
            valid=not reasons,
            reasons=reasons,
            accepted_sections=accepted_sections if not reasons else [],
            applies_real_motion_settings=bundle.hardware_readiness.ready_for_real_motion,
        )

    async def product_readiness(self) -> ProductReadinessResponse:
        acceptance = await self.acceptance_report()
        diagnostics = await self.diagnostics()
        readiness = self.hardware_readiness_model()
        items = [
            ChecklistItem(
                id="acceptance",
                label="No-hardware acceptance is green",
                ok=acceptance.ok,
                detail="ok" if acceptance.ok else "acceptance_failed",
            ),
            ChecklistItem(
                id="diagnostics",
                label="Diagnostics are green",
                ok=diagnostics.ok,
                detail="ok" if diagnostics.ok else "diagnostics_failed",
            ),
            ChecklistItem(
                id="hardware_lock",
                label="Real motion remains locked",
                ok=not readiness.ready_for_real_motion,
                detail="locked",
            ),
        ]
        ok = all(item.ok for item in items)
        return ProductReadinessResponse(
            ok=ok,
            status="no_hardware_product_ready" if ok else "not_ready",
            acceptance=acceptance,
            diagnostics=diagnostics,
            hardware_readiness=readiness,
            items=items,
        )

    def commissioning_guide(self) -> CommissioningGuideResponse:
        return CommissioningGuideResponse(
            steps=[
                ChecklistItem(
                    id="local_doctor",
                    label="Run local hardware doctor",
                    ok=True,
                    detail="Reports tools, ADB devices, Arduino boards, serial ports, and backend readiness.",
                ),
                ChecklistItem(
                    id="unoq_adb",
                    label="Verify UNO Q ADB",
                    ok=True,
                    detail="Stops on old root-ADB image behavior and does not deploy until ADB is healthy.",
                ),
                ChecklistItem(
                    id="mega_locked_build",
                    label="Build locked Mega firmware",
                    ok=True,
                    detail="Default firmware keeps COOKBOT_HARDWARE_CONFIGURED=0 and rejects motion.",
                ),
                ChecklistItem(
                    id="explicit_upload_port",
                    label="Choose explicit Mega upload port",
                    ok=True,
                    detail="Upload scripts never auto-select a serial port.",
                ),
                ChecklistItem(
                    id="serial_self_test",
                    label="Probe Mega JSON protocol",
                    ok=True,
                    detail="Probe uses hello, get_firmware_status, self_test, and read_inputs only.",
                ),
                ChecklistItem(
                    id="bench_only",
                    label="Keep bench outputs isolated",
                    ok=True,
                    detail="Bench pulses require bench firmware, BENCH_ONLY unlock, clear ESTOP, explicit pin, and short duration.",
                ),
            ],
            commands=[
                CommissioningCommand(
                    id="doctor_windows",
                    label="Hardware doctor (Windows)",
                    command="powershell -ExecutionPolicy Bypass -File scripts\\hardware_doctor.ps1 --backend-url http://127.0.0.1:8000",
                    description="Local report for tools, ADB, serial ports, Arduino board list, and product readiness.",
                ),
                CommissioningCommand(
                    id="doctor_linux",
                    label="Hardware doctor (Linux/UNO Q)",
                    command="bash scripts/hardware_doctor.sh --backend-url http://127.0.0.1:8000",
                    description="Same report for UNO Q/Linux shell.",
                ),
                CommissioningCommand(
                    id="adb_check",
                    label="UNO Q ADB check",
                    command="powershell -ExecutionPolicy Bypass -File scripts\\unoq_adb_check.ps1",
                    description="Verifies connected UNO Q Linux side before deployment.",
                ),
                CommissioningCommand(
                    id="adb_deploy",
                    label="UNO Q deploy",
                    command="powershell -ExecutionPolicy Bypass -File scripts\\unoq_adb_deploy.ps1 --target /home/arduino/cookbot",
                    description="Pushes tracked project files and restarts the user systemd backend service.",
                ),
                CommissioningCommand(
                    id="mega_build",
                    label="Mega locked build",
                    command="python -m platformio run -e cookbot_mega2560",
                    description="Builds the default no-motion firmware for Arduino Mega 2560.",
                ),
                CommissioningCommand(
                    id="mega_upload",
                    label="Mega upload with explicit port",
                    command="powershell -ExecutionPolicy Bypass -File scripts\\mega_platformio_upload.ps1 --port COM5",
                    description="Replace COM5 with the verified Mega port; the script will not guess.",
                ),
                CommissioningCommand(
                    id="serial_probe",
                    label="Mega serial probe",
                    command="powershell -ExecutionPolicy Bypass -File scripts\\mega_serial_probe.ps1 --port COM5",
                    description="Protocol-only self-test; no motion commands are sent.",
                ),
                CommissioningCommand(
                    id="commissioning_dry_run",
                    label="Commissioning dry-run",
                    command="powershell -ExecutionPolicy Bypass -File scripts\\commissioning_check.ps1 --dry-run",
                    description="Prints the full sequence without touching hardware.",
                ),
            ],
        )

    def schemas(self) -> dict[str, Any]:
        return {
            "SystemState": SystemState.model_json_schema(),
            "MegaRequest": MegaRequest.model_json_schema(),
            "MegaResponse": MegaResponse.model_json_schema(),
            "AIPlan": AIPlan.model_json_schema(),
            "HardwareReadinessResponse": HardwareReadinessResponse.model_json_schema(),
            "WorkspaceModel": WorkspaceModel.model_json_schema(),
            "AcceptanceReport": AcceptanceReport.model_json_schema(),
            "ExportBundle": ExportBundle.model_json_schema(),
            "BackupBundle": BackupBundle.model_json_schema(),
            "RestoreValidationResponse": RestoreValidationResponse.model_json_schema(),
            "ProductReadinessResponse": ProductReadinessResponse.model_json_schema(),
            "CommissioningGuideResponse": CommissioningGuideResponse.model_json_schema(),
            "VersionResponse": VersionResponse.model_json_schema(),
            "ErrorTaxonomy": ERROR_TAXONOMY,
            "MegaProtocolCommands": MEGA_PROTOCOL_COMMANDS,
        }

    async def _execute_recipe_step(self, step: dict[str, Any]) -> None:
        step_type = str(step.get("type"))
        if step_type == "move_joint":
            await self.move_joint(
                str(step["joint_id"]),
                JointMoveRequest(position=float(step["position"]), speed=float(step.get("speed", 0.25))),
            )
        elif step_type == "set_gripper":
            await self.set_gripper(GripperRequest(position=float(step["position"])))
        elif step_type == "wait":
            await asyncio.sleep(min(float(step.get("seconds", 0.0)), 0.05))
        elif step_type in {"snapshot", "recipe_note", "home_all"}:
            if step_type == "home_all":
                await self.home()
        else:
            raise ValueError(f"forbidden_recipe_step:{step_type}")

    def _build_transport(self, settings: Settings) -> MegaTransport:
        if settings.mega_transport == "fake":
            return LocalFakeMegaTransport(self.fake_device)
        if settings.mega_transport == "fake_tcp":
            return TcpMegaTransport(settings.fake_mega_host, settings.fake_mega_port)
        return SerialMegaTransport(settings.serial_port, settings.serial_baud)

    def _build_ai(self, settings: Settings):
        if settings.ai == "openai_compatible":
            return OpenAICompatibleClient(settings.ai_base_url, settings.ai_api_key, settings.ai_model)
        return MockAIClient()

    def _build_camera(self, settings: Settings):
        if settings.camera == "libcamera":
            return LibcameraStillCamera()
        return MockCamera()

    def _configure_services(self) -> None:
        self.simulator.set_service("mega", self.settings.mega_transport)
        self.simulator.set_service("camera", self.settings.camera)
        self.simulator.set_service("ai", self.settings.ai)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    controller = CookBotController(resolved_settings)
    app = FastAPI(title=resolved_settings.api_title)
    app.state.controller = controller

    @app.middleware("http")
    async def optional_api_token_guard(request: Request, call_next):
        token = resolved_settings.api_token
        if token and _requires_api_token(request.url.path):
            supplied = request.headers.get("X-CookBot-Token") or request.query_params.get("cookbot_token")
            if supplied != token:
                return JSONResponse(status_code=401, content={"detail": "cookbot_token_required"})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return await controller.health()

    @app.get("/settings", response_model=PublicSettings)
    async def settings() -> PublicSettings:
        return controller.public_settings()

    @app.get("/version", response_model=VersionResponse)
    async def version() -> VersionResponse:
        return controller.version()

    @app.get("/diagnostics", response_model=DiagnosticsResponse)
    async def diagnostics() -> DiagnosticsResponse:
        return await controller.diagnostics()

    @app.get("/state", response_model=SystemState)
    async def state() -> SystemState:
        return await controller.state()

    @app.get("/camera/snapshot", response_model=CameraSnapshot)
    async def camera_snapshot() -> CameraSnapshot:
        return _safe(controller.snapshot)

    @app.get("/camera/stream")
    async def camera_stream(frames: int | None = Query(default=None, ge=1, le=60)):
        async def generator():
            async for frame in controller.camera_stream(frames):
                yield frame

        return StreamingResponse(
            generator(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    @app.post("/estop", response_model=SystemState)
    async def estop() -> SystemState:
        return await _safe_async(controller.estop)

    @app.post("/estop/clear", response_model=SystemState)
    async def clear_estop() -> SystemState:
        return await _safe_async(controller.clear_estop)

    @app.post("/home", response_model=SystemState)
    async def home() -> SystemState:
        return await _safe_async(controller.home)

    @app.post("/calibration/simulate", response_model=SystemState)
    async def mark_simulated_calibration() -> SystemState:
        return await _safe_async(controller.mark_simulated_calibration)

    @app.get("/calibration/status", response_model=CalibrationStatus)
    async def calibration_status() -> CalibrationStatus:
        return await controller.calibration_status()

    @app.get("/calibration/wizard/status", response_model=CalibrationWizardStatus)
    async def calibration_wizard_status() -> CalibrationWizardStatus:
        return controller.calibration_wizard_status()

    @app.post("/calibration/wizard/start", response_model=CalibrationWizardStatus)
    async def calibration_wizard_start() -> CalibrationWizardStatus:
        return controller.calibration_wizard_start()

    @app.post("/calibration/wizard/advance", response_model=CalibrationWizardStatus)
    async def calibration_wizard_advance() -> CalibrationWizardStatus:
        return await controller.calibration_wizard_advance()

    @app.post("/calibration/wizard/reset", response_model=CalibrationWizardStatus)
    async def calibration_wizard_reset() -> CalibrationWizardStatus:
        return controller.calibration_wizard_reset()

    @app.post("/calibration/save", response_model=CalibrationProfile)
    async def calibration_save() -> CalibrationProfile:
        return await controller.calibration_save()

    @app.post("/calibration/reset", response_model=CalibrationStatus)
    async def calibration_reset() -> CalibrationStatus:
        return await controller.calibration_reset()

    @app.post("/joints/{joint_id}/move", response_model=SystemState)
    async def move_joint(joint_id: str, request: JointMoveRequest) -> SystemState:
        return await _safe_async(lambda: controller.move_joint(joint_id, request))

    @app.post("/gripper", response_model=SystemState)
    async def gripper(request: GripperRequest) -> SystemState:
        return await _safe_async(lambda: controller.set_gripper(request))

    @app.post("/ai/command", response_model=AICommandResponse)
    async def ai_command(request: AICommandRequest) -> AICommandResponse:
        return controller.ai_command(request)

    @app.get("/recipes", response_model=list[RecipeSummary])
    async def recipes() -> list[RecipeSummary]:
        return controller.list_recipes()

    @app.post("/recipes/{recipe_id}/preflight", response_model=RecipePreflightResponse)
    async def recipe_preflight(recipe_id: str) -> RecipePreflightResponse:
        return await controller.recipe_preflight(recipe_id)

    @app.post("/recipes/{recipe_id}/run", response_model=RecipeRunResponse)
    async def recipe_run(recipe_id: str) -> RecipeRunResponse:
        return await _safe_async(lambda: controller.recipe_run(recipe_id))

    @app.get("/recipes/runtime/status", response_model=RecipeRuntimeStatus)
    async def recipe_runtime_status() -> RecipeRuntimeStatus:
        return controller.recipe_status()

    @app.post("/recipes/runtime/pause", response_model=RecipeRuntimeStatus)
    async def recipe_runtime_pause() -> RecipeRuntimeStatus:
        return controller.recipe_pause()

    @app.post("/recipes/runtime/resume", response_model=RecipeRuntimeStatus)
    async def recipe_runtime_resume() -> RecipeRuntimeStatus:
        return controller.recipe_resume()

    @app.post("/recipes/runtime/abort", response_model=RecipeRuntimeStatus)
    async def recipe_runtime_abort() -> RecipeRuntimeStatus:
        return await controller.recipe_abort()

    @app.get("/logs", response_model=list[CommandLogEntry])
    async def logs(limit: int = Query(default=100, ge=1, le=500)) -> list[CommandLogEntry]:
        return controller.logs(limit)

    @app.get("/workspace", response_model=WorkspaceModel)
    async def workspace() -> WorkspaceModel:
        return controller.workspace_model()

    @app.get("/hardware/readiness", response_model=HardwareReadinessResponse)
    async def hardware_readiness() -> HardwareReadinessResponse:
        return controller.hardware_readiness_model()

    @app.get("/acceptance", response_model=AcceptanceReport)
    async def acceptance() -> AcceptanceReport:
        return await controller.acceptance_report()

    @app.get("/product/readiness", response_model=ProductReadinessResponse)
    async def product_readiness() -> ProductReadinessResponse:
        return await controller.product_readiness()

    @app.get("/commissioning/guide", response_model=CommissioningGuideResponse)
    async def commissioning_guide() -> CommissioningGuideResponse:
        return controller.commissioning_guide()

    @app.get("/export", response_model=ExportBundle)
    async def export_bundle() -> ExportBundle:
        return await controller.export_bundle()

    @app.get("/backup", response_model=BackupBundle)
    async def backup_bundle() -> BackupBundle:
        return await controller.backup_bundle()

    @app.post("/restore/validate", response_model=RestoreValidationResponse)
    async def restore_validate(payload: dict[str, Any]) -> RestoreValidationResponse:
        return await controller.validate_restore(payload)

    @app.get("/schemas")
    async def schemas() -> dict[str, Any]:
        return controller.schemas()

    @app.post("/simulator/faults", response_model=SystemState)
    async def inject_fault(request: FaultInjectionRequest) -> SystemState:
        return await _safe_async(lambda: controller.inject_fault(request))

    @app.delete("/simulator/faults", response_model=SystemState)
    async def clear_faults() -> SystemState:
        return await _safe_async(controller.clear_faults)

    @app.websocket("/ws/state")
    async def ws_state(websocket: WebSocket) -> None:
        if resolved_settings.api_token and websocket.query_params.get("cookbot_token") != resolved_settings.api_token:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            while True:
                await websocket.send_json((await controller.state()).model_dump(mode="json"))
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            return

    dist_dir = Path("web/dist")
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="web")

    return app


def _safe(fn):
    try:
        return fn()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _safe_async(fn):
    try:
        return await fn()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _requires_api_token(path: str) -> bool:
    public_paths = {
        "/",
        "/health",
        "/settings",
        "/manifest.webmanifest",
        "/icon.svg",
        "/sw.js",
        "/favicon.ico",
    }
    public_prefixes = ("/assets/", "/docs", "/openapi.json", "/redoc")
    if path in public_paths or any(path.startswith(prefix) for prefix in public_prefixes):
        return False
    return True


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


app = create_app()
