import asyncio
import base64
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .ai import MockAIClient, OpenAICompatibleClient
from .camera import LibcameraStillCamera, MockCamera
from .calibration import CalibrationStore
from .config import Settings, get_settings
from .cookbot_logging import CookBotJsonLogger
from .fake_mega import FakeMegaDevice
from .models import (
    AICommandRequest,
    AICommandResponse,
    AIPlan,
    CalibrationProfile,
    CalibrationStatus,
    CameraSnapshot,
    CommandLogEntry,
    DiagnosticCheck,
    DiagnosticsResponse,
    FaultInjectionRequest,
    GripperRequest,
    HardwareReadinessResponse,
    HealthResponse,
    JointMoveRequest,
    MegaRequest,
    MegaResponse,
    RecipePreflightResponse,
    RecipeRunResponse,
    RecipeRuntimeStatus,
    RecipeSummary,
    SystemState,
    WorkspaceModel,
)
from .hardware_readiness import HardwareReadinessStore
from .recipe_runtime import RecipeRuntime
from .recipes import RecipeEngine
from .safety import SafetyValidator
from .simulator import CookBotSimulator
from .transports import LocalFakeMegaTransport, MegaTransport, SerialMegaTransport, TcpMegaTransport
from .workspace import WorkspaceStore


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
        await add_transport_check("mega_hello", "hello")
        await add_transport_check("mega_ping", "ping")
        await add_transport_check("mega_state", "get_state")
        await add_transport_check("mega_capabilities", "get_capabilities")

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
        return self.recipes.preflight(recipe_id, await self.state())

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

    def schemas(self) -> dict[str, Any]:
        return {
            "SystemState": SystemState.model_json_schema(),
            "MegaRequest": MegaRequest.model_json_schema(),
            "MegaResponse": MegaResponse.model_json_schema(),
            "AIPlan": AIPlan.model_json_schema(),
            "HardwareReadinessResponse": HardwareReadinessResponse.model_json_schema(),
            "WorkspaceModel": WorkspaceModel.model_json_schema(),
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


app = create_app()
