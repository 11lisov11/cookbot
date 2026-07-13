import {
  AlertTriangle,
  Bluetooth,
  Bot,
  Calculator,
  Camera,
  CheckCircle2,
  Code2,
  Download,
  FileText,
  Hand,
  Home,
  ListTodo,
  ListChecks,
  Mic,
  Play,
  Pause,
  RefreshCw,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Upload,
  XCircle
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type AxisState = {
  id: string;
  commanded_position: number;
  min_position: number;
  max_position: number;
  homed: boolean;
  calibrated: boolean;
  moving: boolean;
  limit_min: boolean;
  limit_max: boolean;
};

type SystemState = {
  mode: string;
  estop: boolean;
  homed: boolean;
  calibrated: boolean;
  motion_enabled: boolean;
  services: Record<string, string>;
  axes: AxisState[];
  gripper: { position: number; homed: boolean; calibrated: boolean; moving: boolean };
  limit_switches: Record<string, boolean>;
  queue_depth: number;
  last_error: string | null;
  updated_at: string;
};

type RecipeSummary = {
  id: string;
  name: string;
  locked: boolean;
  description: string;
};

type RecipeRuntimeStatus = {
  active_recipe_id: string | null;
  running: boolean;
  paused: boolean;
  aborted: boolean;
  current_step: number;
  total_steps: number;
  last_message: string | null;
};

type WorkspaceModel = {
  verified_for_real_motion: boolean;
  zones: Array<{ id: string; name: string; kind: string; description: string; verified: boolean }>;
};

type CameraSnapshot = {
  data_url: string;
  media_type: string;
  created_at: string;
};

type DiagnosticCheck = {
  name: string;
  ok: boolean;
  detail: string;
};

type DiagnosticsResponse = {
  ok: boolean;
  checks: DiagnosticCheck[];
};

type CommandLogEntry = {
  timestamp: string;
  source: string;
  event: string;
  command_id: string | null;
  rejected_reason: string | null;
};

type HardwareReadinessResponse = {
  ready_for_real_motion: boolean;
  items: Array<{ id: string; label: string; verified: boolean; evidence: string | null }>;
};

type HardwareGateReport = {
  ready_for_real_motion: boolean;
  real_motion_locked: boolean;
  hardware_configured: boolean;
  verified_count: number;
  evidence_count: number;
  total_count: number;
  blockers: Array<{ id: string; label: string; detail: string; severity: string }>;
};

type CalibrationWizardStatus = {
  active: boolean;
  completed: boolean;
  current_step: number;
  total_steps: number;
  current_step_id: string | null;
  completed_steps: string[];
  last_message: string | null;
};

type AcceptanceReport = {
  ok: boolean;
  items: Array<{ id: string; label: string; ok: boolean; detail: string }>;
};

type PublicSettings = {
  app: "CookBot";
  mode: string;
  mega_transport: string;
  camera: string;
  ai: string;
  bind: string;
  port: number;
  api_auth_required: boolean;
  bluetooth_configured: boolean;
  bluetooth_channel: number | null;
};

type VersionResponse = {
  app: "CookBot";
  backend_version: string;
  git_commit: string;
  build_mode: string;
  api_schema_version: string;
  hardware_configured: boolean;
};

type ProductReadinessResponse = {
  ok: boolean;
  status: string;
  items: Array<{ id: string; label: string; ok: boolean; detail: string }>;
};

type CommissioningGuideResponse = {
  ok: boolean;
  real_motion_locked: boolean;
  ready_for_real_motion: boolean;
  steps: Array<{ id: string; label: string; ok: boolean; detail: string }>;
  commands: Array<{ id: string; label: string; command: string; description: string }>;
};

type RestoreValidationResponse = {
  valid: boolean;
  reasons: string[];
  accepted_sections: string[];
  applies_real_motion_settings: boolean;
};

type VendorProfileResponse = {
  source: string;
  feed_mm_s: { minimum: number; default: number; maximum: number };
  missing_controller_parameters: string[];
  direct_execution_enabled: boolean;
};

type StepperMotionEstimateResponse = {
  step_period_us: number;
  step_frequency_hz: number;
  motor_rpm: number;
  output_rpm: number;
  steps_per_motor_revolution: number;
  steps_per_output_revolution: number;
  linear_speed_mm_s: number | null;
};

type VendorGCodeValidationResponse = {
  accepted: boolean;
  command: { normalized: string; name: string } | null;
  rejected_reason: string | null;
  direct_execution_enabled: boolean;
};

type TabId = "control" | "recipes" | "diagnostics" | "calibration" | "hardware" | "settings";

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE || window.location.origin;
const TABS: Array<{ id: TabId; label: string }> = [
  { id: "control", label: "Control" },
  { id: "recipes", label: "Recipes" },
  { id: "diagnostics", label: "Diagnostics" },
  { id: "calibration", label: "Calibration" },
  { id: "hardware", label: "Hardware Gate" },
  { id: "settings", label: "Settings" }
];

function currentApiBase() {
  return localStorage.getItem("cookbot_backend_url") || DEFAULT_API_BASE;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("cookbot_api_token");
  const response = await fetch(`${currentApiBase()}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-CookBot-Token": token } : {}),
      ...(init?.headers || {})
    },
    ...init
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [state, setState] = useState<SystemState | null>(null);
  const [snapshot, setSnapshot] = useState<CameraSnapshot | null>(null);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [runtime, setRuntime] = useState<RecipeRuntimeStatus | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceModel | null>(null);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);
  const [logs, setLogs] = useState<CommandLogEntry[]>([]);
  const [hardwareReadiness, setHardwareReadiness] = useState<HardwareReadinessResponse | null>(null);
  const [hardwareGate, setHardwareGate] = useState<HardwareGateReport | null>(null);
  const [wizard, setWizard] = useState<CalibrationWizardStatus | null>(null);
  const [acceptance, setAcceptance] = useState<AcceptanceReport | null>(null);
  const [settings, setSettings] = useState<PublicSettings | null>(null);
  const [version, setVersion] = useState<VersionResponse | null>(null);
  const [productReadiness, setProductReadiness] = useState<ProductReadinessResponse | null>(null);
  const [commissioningGuide, setCommissioningGuide] = useState<CommissioningGuideResponse | null>(null);
  const [vendorProfile, setVendorProfile] = useState<VendorProfileResponse | null>(null);
  const [motionEstimate, setMotionEstimate] = useState<StepperMotionEstimateResponse | null>(null);
  const [motionInputs, setMotionInputs] = useState({
    motorSteps: "200",
    microsteps: "16",
    gearbox: "10",
    delayUs: "3500",
    pulseUs: "3",
    travelMm: ""
  });
  const [vendorGcode, setVendorGcode] = useState("G1 X0 Y205 Z100 F100");
  const [gcodeValidation, setGcodeValidation] = useState<VendorGCodeValidationResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("control");
  const [onboarded, setOnboarded] = useState(() => localStorage.getItem("cookbot_onboarded") === "1");
  const [backendUrl, setBackendUrl] = useState(() => currentApiBase());
  const [apiToken, setApiToken] = useState(() => localStorage.getItem("cookbot_api_token") || "");
  const [restoreResult, setRestoreResult] = useState<RestoreValidationResponse | null>(null);
  const [axisTargets, setAxisTargets] = useState<Record<string, number>>({});
  const [gripperTarget, setGripperTarget] = useState(0);
  const [aiCommand, setAiCommand] = useState("look at the workspace");
  const [useStream, setUseStream] = useState(true);
  const [message, setMessage] = useState("Connecting to CookBot");

  const wsUrl = useMemo(() => {
    const suffix = apiToken.trim() ? `?cookbot_token=${encodeURIComponent(apiToken.trim())}` : "";
    return backendUrl.replace(/^http/, "ws") + `/ws/state${suffix}`;
  }, [backendUrl, apiToken]);

  useEffect(() => {
    refreshAll();
    const socket = new WebSocket(wsUrl);
    socket.onmessage = (event) => {
      const next = JSON.parse(event.data) as SystemState;
      setState(next);
      setAxisTargets((previous) => seedTargets(previous, next));
      setGripperTarget(next.gripper.position);
    };
    socket.onerror = () => setMessage("State stream unavailable; manual refresh still works.");
    return () => socket.close();
  }, [wsUrl]);

  async function refreshAll() {
    try {
      const [nextSettings, nextVersion] = await Promise.all([
        api<PublicSettings>("/settings"),
        api<VersionResponse>("/version")
      ]);
      const [nextState, nextSnapshot, nextRecipes] = await Promise.all([
        api<SystemState>("/state"),
        api<CameraSnapshot>("/camera/snapshot"),
        api<RecipeSummary[]>("/recipes")
      ]);
      const [
        nextRuntime,
        nextWorkspace,
        nextDiagnostics,
        nextLogs,
        nextReadiness,
        nextHardwareGate,
        nextWizard,
        nextAcceptance,
        nextProductReadiness,
        nextCommissioningGuide,
        nextVendorProfile
      ] = await Promise.all([
        api<RecipeRuntimeStatus>("/recipes/runtime/status"),
        api<WorkspaceModel>("/workspace"),
        api<DiagnosticsResponse>("/diagnostics"),
        api<CommandLogEntry[]>("/logs?limit=8"),
        api<HardwareReadinessResponse>("/hardware/readiness"),
        api<HardwareGateReport>("/hardware/gate/report"),
        api<CalibrationWizardStatus>("/calibration/wizard/status"),
        api<AcceptanceReport>("/acceptance"),
        api<ProductReadinessResponse>("/product/readiness"),
        api<CommissioningGuideResponse>("/commissioning/guide"),
        api<VendorProfileResponse>("/vendor/profile")
      ]);
      setState(nextState);
      setSettings(nextSettings);
      setVersion(nextVersion);
      setSnapshot(nextSnapshot);
      setRecipes(nextRecipes);
      setRuntime(nextRuntime);
      setWorkspace(nextWorkspace);
      setDiagnostics(nextDiagnostics);
      setLogs(nextLogs);
      setHardwareReadiness(nextReadiness);
      setHardwareGate(nextHardwareGate);
      setWizard(nextWizard);
      setAcceptance(nextAcceptance);
      setProductReadiness(nextProductReadiness);
      setCommissioningGuide(nextCommissioningGuide);
      setVendorProfile(nextVendorProfile);
      setAxisTargets((previous) => seedTargets(previous, nextState));
      setGripperTarget(nextState.gripper.position);
      setMessage("CookBot ready in no-hardware mode");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "CookBot request failed");
    }
  }

  async function runAction(label: string, action: () => Promise<SystemState | unknown>) {
    try {
      const result = await action();
      if (result && typeof result === "object" && "mode" in result) {
        setState(result as SystemState);
      }
      if (result && typeof result === "object" && "active_recipe_id" in result) {
        setRuntime(result as RecipeRuntimeStatus);
      }
      if (result && typeof result === "object" && "current_step_id" in result) {
        setWizard(result as CalibrationWizardStatus);
      }
      setMessage(label);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "CookBot command failed");
    }
  }

  function submitAi(event: FormEvent) {
    event.preventDefault();
    runAction("AI plan checked by safety layer", async () => {
      const response = await api<{ accepted: boolean; rejected_reason: string | null }>("/ai/command", {
        method: "POST",
        body: JSON.stringify({ command: aiCommand, include_snapshot: true })
      });
      setMessage(response.accepted ? "AI plan accepted for review" : `AI rejected: ${response.rejected_reason}`);
      return response;
    });
  }

  async function calculateMotion(event: FormEvent) {
    event.preventDefault();
    try {
      const travel = motionInputs.travelMm.trim();
      const result = await api<StepperMotionEstimateResponse>("/motion/estimate", {
        method: "POST",
        body: JSON.stringify({
          motor_full_steps_per_revolution: Number(motionInputs.motorSteps),
          microsteps: Number(motionInputs.microsteps),
          gearbox_ratio: Number(motionInputs.gearbox),
          step_delay_us: Number(motionInputs.delayUs),
          pulse_us: Number(motionInputs.pulseUs),
          travel_per_output_revolution_mm: travel ? Number(travel) : null
        })
      });
      setMotionEstimate(result);
      setMessage("Motion estimate calculated; no hardware command was sent");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Motion estimate failed");
    }
  }

  async function validateVendorGcode(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await api<VendorGCodeValidationResponse>("/vendor/gcode/validate", {
        method: "POST",
        body: JSON.stringify({ line: vendorGcode })
      });
      setGcodeValidation(result);
      setMessage(result.accepted ? "Vendor command parsed; direct execution remains locked" : `Vendor command rejected: ${result.rejected_reason}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Vendor command validation failed");
    }
  }

  function startVoiceInput() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessage("Voice input is not available in this browser.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "ru-RU";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript;
      if (text) {
        setAiCommand(text);
        setMessage("Voice command captured");
      }
    };
    recognition.onerror = () => setMessage("Voice input failed");
    recognition.start();
  }

  function saveApiToken() {
    const nextBackendUrl = backendUrl.trim() || DEFAULT_API_BASE;
    localStorage.setItem("cookbot_backend_url", nextBackendUrl);
    setBackendUrl(nextBackendUrl);
    if (apiToken.trim()) {
      localStorage.setItem("cookbot_api_token", apiToken.trim());
    } else {
      localStorage.removeItem("cookbot_api_token");
    }
    refreshAll();
  }

  function finishOnboarding() {
    saveApiToken();
    localStorage.setItem("cookbot_onboarded", "1");
    setOnboarded(true);
    setMessage("First-run setup saved");
  }

  async function downloadExport() {
    try {
      const bundle = await api<Record<string, unknown>>("/export");
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "cookbot-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("CookBot export downloaded");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "CookBot export failed");
    }
  }

  async function downloadBackup() {
    try {
      const bundle = await api<Record<string, unknown>>("/backup");
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "cookbot-backup.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("CookBot backup downloaded");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "CookBot backup failed");
    }
  }

  async function validateRestoreFile(file: File | null) {
    if (!file) {
      return;
    }
    try {
      const parsed = JSON.parse(await file.text());
      const result = await api<RestoreValidationResponse>("/restore/validate", {
        method: "POST",
        body: JSON.stringify(parsed)
      });
      setRestoreResult(result);
      setMessage(result.valid ? "Restore bundle validated" : `Restore rejected: ${result.reasons.join(",")}`);
    } catch (error) {
      setRestoreResult({ valid: false, reasons: ["malformed_restore_bundle"], accepted_sections: [], applies_real_motion_settings: false });
      setMessage(error instanceof Error ? error.message : "Restore validation failed");
    }
  }

  function cameraStreamUrl() {
    const token = localStorage.getItem("cookbot_api_token");
    const suffix = token ? `?cookbot_token=${encodeURIComponent(token)}` : "";
    return `${backendUrl}/camera/stream${suffix}`;
  }

  function panelClass(tab: TabId, base = "panel") {
    return activeTab === tab ? base : `${base} hidden`;
  }

  function diagnostic(name: string) {
    return diagnostics?.checks.find((check) => check.name === name);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Bot size={26} aria-hidden="true" />
          <div>
            <h1>CookBot</h1>
            <span>{state?.mode || "simulator"}</span>
          </div>
        </div>
        <button
          className="estop"
          title="Emergency stop"
          onClick={() => runAction("Emergency stop active", () => api<SystemState>("/estop", { method: "POST" }))}
        >
          <ShieldAlert size={22} />
          ESTOP
        </button>
      </header>

      <section className="status-strip" aria-live="polite">
        <StatusPill label="Mega" value={state?.services.mega || "unknown"} ok={state?.services.mega !== "error"} />
        <StatusPill label="Camera" value={state?.services.camera || "unknown"} ok />
        <StatusPill label="AI" value={state?.services.ai || "unknown"} ok />
        <StatusPill label="Homed" value={state?.homed ? "yes" : "no"} ok={Boolean(state?.homed)} />
        <StatusPill label="ESTOP" value={state?.estop ? "active" : "clear"} ok={!state?.estop} />
      </section>

      <section className="notice">
        {state?.last_error ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
        <span>{state?.last_error || message}</span>
      </section>

      {!onboarded ? (
        <section className="panel onboarding">
          <div className="panel-title">
            <ShieldAlert size={19} />
            <h2>First Run</h2>
          </div>
          <div className="settings-grid">
            <div className="diagnostic-item warn">
              <strong>No-hardware product mode</strong>
              <span>Simulator, fake Mega, mock camera, and mock AI are expected. Real motion stays locked.</span>
            </div>
            <label className="token-field">
              <span>Backend URL</span>
              <input value={backendUrl} onChange={(event) => setBackendUrl(event.target.value)} />
            </label>
            <label className="token-field">
              <span>Optional API token</span>
              <input value={apiToken} onChange={(event) => setApiToken(event.target.value)} type="password" />
            </label>
            <button type="button" onClick={finishOnboarding}>
              <CheckCircle2 size={17} />
              Start CookBot
            </button>
          </div>
        </section>
      ) : null}

      <nav className="tabbar" aria-label="CookBot sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "active" : ""}
            type="button"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="work-grid">
        <section className={panelClass("control", "panel camera-panel")}>
          <div className="panel-title">
            <Camera size={19} />
            <h2>Camera</h2>
            <button className="icon-button" title="Toggle stream" onClick={() => setUseStream((value) => !value)}>
              <Play size={18} />
            </button>
            <button className="icon-button" title="Refresh camera" onClick={refreshAll}>
              <RefreshCw size={18} />
            </button>
          </div>
          {useStream ? (
            <img src={cameraStreamUrl()} alt="CookBot mock camera stream" />
          ) : snapshot ? (
            <img src={snapshot.data_url} alt="CookBot mock camera" />
          ) : (
            <div className="empty">No image</div>
          )}
        </section>

        <section className={panelClass("control")}>
          <div className="panel-title">
            <SlidersHorizontal size={19} />
            <h2>Manual</h2>
          </div>
          <div className="button-row">
            <button onClick={() => runAction("Homing complete", () => api<SystemState>("/home", { method: "POST" }))}>
              <Home size={17} />
              Home
            </button>
            <button
              onClick={() =>
                runAction("Simulated calibration marked", () =>
                  api<SystemState>("/calibration/simulate", { method: "POST" })
                )
              }
            >
              <CheckCircle2 size={17} />
              Calibrate
            </button>
            <button
              onClick={() =>
                runAction("Calibration saved", () => api("/calibration/save", { method: "POST" }))
              }
            >
              <CheckCircle2 size={17} />
              Save
            </button>
            <button
              onClick={() => runAction("ESTOP cleared; re-home required", () => api<SystemState>("/estop/clear", { method: "POST" }))}
            >
              <XCircle size={17} />
              Clear
            </button>
            <button
              onClick={() => runAction("Calibration reset", () => api("/calibration/reset", { method: "POST" }))}
            >
              <RefreshCw size={17} />
              Reset
            </button>
          </div>

          <div className="axis-list">
            {state?.axes.map((axis) => (
              <div className="axis-row" key={axis.id}>
                <label htmlFor={axis.id}>{axis.id}</label>
                <input
                  id={axis.id}
                  type="range"
                  min={axis.min_position}
                  max={axis.max_position}
                  step="0.5"
                  value={axisTargets[axis.id] ?? axis.commanded_position}
                  onChange={(event) =>
                    setAxisTargets((previous) => ({ ...previous, [axis.id]: Number(event.target.value) }))
                  }
                />
                <output>{(axisTargets[axis.id] ?? axis.commanded_position).toFixed(1)}</output>
                <button
                  className="icon-button"
                  title={`Move ${axis.id}`}
                  onClick={() =>
                    runAction(`${axis.id} moved`, () =>
                      api<SystemState>(`/joints/${axis.id}/move`, {
                        method: "POST",
                        body: JSON.stringify({ position: axisTargets[axis.id] ?? axis.commanded_position, speed: 0.25 })
                      })
                    )
                  }
                >
                  <Play size={17} />
                </button>
              </div>
            ))}
            <div className="axis-row">
              <label htmlFor="gripper">gripper</label>
              <input
                id="gripper"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={gripperTarget}
                onChange={(event) => setGripperTarget(Number(event.target.value))}
              />
              <output>{gripperTarget.toFixed(2)}</output>
              <button
                className="icon-button"
                title="Set gripper"
                onClick={() =>
                  runAction("Gripper moved", () =>
                    api<SystemState>("/gripper", { method: "POST", body: JSON.stringify({ position: gripperTarget }) })
                  )
                }
              >
                <Hand size={17} />
              </button>
            </div>
          </div>
        </section>

        <section className={panelClass("control")}>
          <div className="panel-title">
            <Sparkles size={19} />
            <h2>AI Check</h2>
          </div>
          <form className="ai-form" onSubmit={submitAi}>
            <textarea value={aiCommand} onChange={(event) => setAiCommand(event.target.value)} />
            <div className="button-row two">
              <button type="button" onClick={startVoiceInput}>
                <Mic size={17} />
                Voice
              </button>
              <button type="submit">
                <ShieldAlert size={17} />
                Validate
              </button>
            </div>
          </form>
        </section>

        <section className={panelClass("recipes")}>
          <div className="panel-title">
            <Play size={19} />
            <h2>Recipes</h2>
          </div>
          <div className="runtime-strip">
            <span>{runtime?.active_recipe_id || "idle"}</span>
            <strong>
              {runtime?.current_step || 0}/{runtime?.total_steps || 0}
            </strong>
            <button className="icon-button" title="Pause recipe" onClick={() => runAction("Recipe paused", () => api<RecipeRuntimeStatus>("/recipes/runtime/pause", { method: "POST" }))}>
              <Pause size={16} />
            </button>
            <button className="icon-button" title="Resume recipe" onClick={() => runAction("Recipe resumed", () => api<RecipeRuntimeStatus>("/recipes/runtime/resume", { method: "POST" }))}>
              <Play size={16} />
            </button>
            <button className="icon-button" title="Abort recipe" onClick={() => runAction("Recipe aborted", () => api<RecipeRuntimeStatus>("/recipes/runtime/abort", { method: "POST" }))}>
              <ShieldAlert size={16} />
            </button>
          </div>
          <div className="recipe-list">
            {recipes.map((recipe) => (
              <div className="recipe-item" key={recipe.id}>
                <div>
                  <strong>{recipe.name}</strong>
                  <span>{recipe.locked ? "locked" : recipe.description}</span>
                </div>
                <button
                  disabled={recipe.locked}
                  onClick={() =>
                    runAction(`${recipe.name} requested`, () =>
                      api(`/recipes/${recipe.id}/run`, {
                        method: "POST"
                      })
                    )
                  }
                >
                  <Play size={16} />
                  Run
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className={panelClass("diagnostics")}>
          <div className="panel-title">
            <ShieldAlert size={19} />
            <h2>Workspace</h2>
          </div>
          <div className="workspace-list">
            {workspace?.zones.map((zone) => (
              <div className="zone-item" key={zone.id}>
                <strong>{zone.name}</strong>
                <span>{zone.kind} - {zone.verified ? "verified" : "placeholder"}</span>
              </div>
            ))}
          </div>
        </section>

        <section className={panelClass("diagnostics")}>
          <div className="panel-title">
            <ListChecks size={19} />
            <h2>Diagnostics</h2>
            <button className="icon-button" title="Refresh diagnostics" onClick={refreshAll}>
              <RefreshCw size={18} />
            </button>
          </div>
          <div className="diagnostic-list">
            {diagnostics?.checks.map((check) => (
              <div className={`diagnostic-item ${check.ok ? "ok" : "warn"}`} key={check.name}>
                <strong>{check.name}</strong>
                <span>{check.detail}</span>
              </div>
            ))}
          </div>
        </section>

        <section className={panelClass("diagnostics")}>
          <div className="panel-title">
            <FileText size={19} />
            <h2>Logs</h2>
          </div>
          <div className="log-list">
            {logs.map((entry) => (
              <div className="log-item" key={`${entry.timestamp}-${entry.source}-${entry.event}`}>
                <strong>{entry.source}:{entry.event}</strong>
                <span>{entry.rejected_reason || entry.command_id || new Date(entry.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
            {logs.length === 0 ? <div className="empty-list">No events yet</div> : null}
          </div>
        </section>

        <section className={panelClass("hardware")}>
          <div className="panel-title">
            <ShieldAlert size={19} />
            <h2>Hardware Gate</h2>
          </div>
          <div className="diagnostic-list">
            <div className={`diagnostic-item ${settings?.mega_transport === "bluetooth_rfcomm" && settings.bluetooth_configured ? "ok" : "warn"}`}>
              <strong><Bluetooth size={16} /> Mega Bluetooth</strong>
              <span>
                {settings?.mega_transport === "bluetooth_rfcomm"
                  ? settings.bluetooth_configured
                    ? `RFCOMM configured, channel ${settings.bluetooth_channel}`
                    : "RFCOMM selected; MAC address missing"
                  : "RFCOMM not selected"}
              </span>
            </div>
            <div className="diagnostic-item warn">
              <strong>commissioning scripts only</strong>
              <span>ADB deploy, Bluetooth pairing, PlatformIO upload, protocol probes, and bench pulses run from scripts, not from the browser.</span>
            </div>
            {["smart_home_integration", "bluetooth_config", "mega_firmware_status", "mega_hardware_config", "mega_limit_switches", "mega_self_test", "mega_inputs"].map((name) => {
              const check = diagnostic(name);
              return (
                <div className={`diagnostic-item ${check?.ok ? "ok" : "warn"}`} key={name}>
                  <strong>{name}</strong>
                  <span>{check?.detail || "not checked"}</span>
                </div>
              );
            })}
            <div className="diagnostic-item warn">
              <strong>bench mode</strong>
              <span>Compile with cookbot_mega2560_bench, unlock with BENCH_ONLY, pulse one explicit pin, then lock again.</span>
            </div>
            <div className={`diagnostic-item ${commissioningGuide?.real_motion_locked ? "ok" : "warn"}`}>
              <strong>commissioning guide</strong>
              <span>{commissioningGuide?.real_motion_locked ? "real motion locked; scripts only" : "guide unavailable"}</span>
            </div>
            {commissioningGuide?.steps.map((item) => (
              <div className={`diagnostic-item ${item.ok ? "ok" : "warn"}`} key={`commissioning-${item.id}`}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
            {commissioningGuide?.commands.map((item) => (
              <div className="command-item" key={`command-${item.id}`}>
                <strong>{item.label}</strong>
                <code>{item.command}</code>
                <span>{item.description}</span>
              </div>
            ))}
            <div className={`diagnostic-item ${hardwareReadiness?.ready_for_real_motion ? "ok" : "warn"}`}>
              <strong>{hardwareReadiness?.ready_for_real_motion ? "real motion ready" : "real motion locked"}</strong>
              <span>{hardwareReadiness?.items.filter((item) => item.verified).length || 0}/{hardwareReadiness?.items.length || 0} checks verified</span>
            </div>
            {hardwareGate ? (
              <div className={`diagnostic-item ${hardwareGate.real_motion_locked ? "warn" : "ok"}`}>
                <strong>{hardwareGate.real_motion_locked ? "gate blockers active" : "gate clear"}</strong>
                <span>
                  {hardwareGate.verified_count}/{hardwareGate.total_count} verified, {hardwareGate.evidence_count} evidence notes, {hardwareGate.blockers.length} blockers
                </span>
              </div>
            ) : null}
            {hardwareGate?.blockers.map((item) => (
              <div className="diagnostic-item warn" key={`gate-${item.id}`}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
            {hardwareReadiness?.items.map((item) => (
              <div className={`diagnostic-item ${item.verified ? "ok" : "warn"}`} key={item.id}>
                <strong>{item.label}</strong>
                <span>{item.evidence || "missing evidence"}</span>
              </div>
            ))}
          </div>
        </section>

        <section className={panelClass("hardware")}>
          <div className="panel-title">
            <Code2 size={19} />
            <h2>Vendor G-code</h2>
          </div>
          <form className="compact-form" onSubmit={validateVendorGcode}>
            <label className="token-field">
              <span>AXIS4UI command</span>
              <textarea value={vendorGcode} onChange={(event) => setVendorGcode(event.target.value)} />
            </label>
            <button type="submit">
              <ShieldAlert size={17} />
              Validate only
            </button>
          </form>
          <div className="diagnostic-list result-list">
            <div className="diagnostic-item warn">
              <strong>Direct execution locked</strong>
              <span>{vendorProfile?.source || "Vendor profile unavailable"}; observed feed range {vendorProfile?.feed_mm_s.minimum || 5}-{vendorProfile?.feed_mm_s.maximum || 150} mm/s.</span>
            </div>
            {gcodeValidation ? (
              <div className={`diagnostic-item ${gcodeValidation.accepted ? "ok" : "warn"}`}>
                <strong>{gcodeValidation.accepted ? gcodeValidation.command?.name : "rejected"}</strong>
                <span>{gcodeValidation.command?.normalized || gcodeValidation.rejected_reason}</span>
              </div>
            ) : null}
          </div>
        </section>

        <section className={panelClass("calibration")}>
          <div className="panel-title">
            <ListTodo size={19} />
            <h2>Calibration Wizard</h2>
          </div>
          <div className="runtime-strip">
            <span>{wizard?.current_step_id || (wizard?.completed ? "completed" : "idle")}</span>
            <strong>
              {wizard?.current_step || 0}/{wizard?.total_steps || 0}
            </strong>
            <button className="icon-button" title="Start wizard" onClick={() => runAction("Calibration wizard started", () => api<CalibrationWizardStatus>("/calibration/wizard/start", { method: "POST" }))}>
              <Play size={16} />
            </button>
            <button className="icon-button" title="Advance wizard" onClick={() => runAction("Calibration wizard advanced", () => api<CalibrationWizardStatus>("/calibration/wizard/advance", { method: "POST" }))}>
              <CheckCircle2 size={16} />
            </button>
            <button className="icon-button" title="Reset wizard" onClick={() => runAction("Calibration wizard reset", () => api<CalibrationWizardStatus>("/calibration/wizard/reset", { method: "POST" }))}>
              <RefreshCw size={16} />
            </button>
          </div>
        </section>

        <section className={panelClass("calibration")}>
          <div className="panel-title">
            <Calculator size={19} />
            <h2>Coordinate Motion</h2>
          </div>
          <form className="compact-form" onSubmit={calculateMotion}>
            <div className="calibration-grid">
              <label className="token-field">
                <span>Motor full steps/rev</span>
                <input type="number" min="1" value={motionInputs.motorSteps} onChange={(event) => setMotionInputs({ ...motionInputs, motorSteps: event.target.value })} />
              </label>
              <label className="token-field">
                <span>Microsteps</span>
                <select value={motionInputs.microsteps} onChange={(event) => setMotionInputs({ ...motionInputs, microsteps: event.target.value })}>
                  {[1, 2, 4, 8, 16].map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <label className="token-field">
                <span>Gearbox ratio</span>
                <input type="number" min="0.001" step="0.001" value={motionInputs.gearbox} onChange={(event) => setMotionInputs({ ...motionInputs, gearbox: event.target.value })} />
              </label>
              <label className="token-field">
                <span>STEP delay, us</span>
                <input type="number" min="0.1" step="0.1" value={motionInputs.delayUs} onChange={(event) => setMotionInputs({ ...motionInputs, delayUs: event.target.value })} />
              </label>
              <label className="token-field">
                <span>Pulse width, us</span>
                <input type="number" min="0.1" step="0.1" value={motionInputs.pulseUs} onChange={(event) => setMotionInputs({ ...motionInputs, pulseUs: event.target.value })} />
              </label>
              <label className="token-field">
                <span>Slider travel/rev, mm</span>
                <input type="number" min="0.001" step="0.001" placeholder="optional" value={motionInputs.travelMm} onChange={(event) => setMotionInputs({ ...motionInputs, travelMm: event.target.value })} />
              </label>
            </div>
            <button type="submit">
              <Calculator size={17} />
              Calculate
            </button>
          </form>
          {motionEstimate ? (
            <div className="metric-grid result-list">
              <Metric label="STEP frequency" value={`${motionEstimate.step_frequency_hz.toFixed(2)} Hz`} />
              <Metric label="Motor speed" value={`${motionEstimate.motor_rpm.toFixed(3)} RPM`} />
              <Metric label="Output speed" value={`${motionEstimate.output_rpm.toFixed(3)} RPM`} />
              <Metric label="Steps/output rev" value={motionEstimate.steps_per_output_revolution.toFixed(0)} />
              {motionEstimate.linear_speed_mm_s !== null ? <Metric label="Linear speed" value={`${motionEstimate.linear_speed_mm_s.toFixed(3)} mm/s`} /> : null}
            </div>
          ) : null}
          <div className="diagnostic-item warn result-list">
            <strong>Measurement required</strong>
            <span>Microstep jumpers, A4988 Vref/Rsense, screw lead, joint zero, link lengths, and measured travel are not present in AXIS4UI.</span>
          </div>
        </section>

        <section className={panelClass("diagnostics")}>
          <div className="panel-title">
            <ListChecks size={19} />
            <h2>Product Readiness</h2>
          </div>
          <div className="diagnostic-list">
            {productReadiness ? (
              <div className={`diagnostic-item ${productReadiness.ok ? "ok" : "warn"}`}>
                <strong>{productReadiness.status}</strong>
                <span>{productReadiness.ok ? "no-hardware product ready" : "checks pending"}</span>
              </div>
            ) : null}
            {productReadiness?.items.map((item) => (
              <div className={`diagnostic-item ${item.ok ? "ok" : "warn"}`} key={`product-${item.id}`}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
            {acceptance?.items.map((item) => (
              <div className={`diagnostic-item ${item.ok ? "ok" : "warn"}`} key={`acceptance-${item.id}`}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
          </div>
        </section>

        <section className={panelClass("settings")}>
          <div className="panel-title">
            <FileText size={19} />
            <h2>Settings</h2>
          </div>
          <div className="settings-grid">
            <div className="diagnostic-item ok">
              <strong>API auth</strong>
              <span>{settings?.api_auth_required ? "token required" : "not required"}</span>
            </div>
            <div className="diagnostic-item ok">
              <strong>mode</strong>
              <span>{settings?.mode || "unknown"} / {settings?.mega_transport || "unknown"}</span>
            </div>
            <div className={`diagnostic-item ${settings?.mega_transport !== "bluetooth_rfcomm" || settings.bluetooth_configured ? "ok" : "warn"}`}>
              <strong>Bluetooth RFCOMM</strong>
              <span>
                {settings?.mega_transport === "bluetooth_rfcomm"
                  ? settings.bluetooth_configured
                    ? `configured / channel ${settings.bluetooth_channel}`
                    : "address required on UNO Q"
                  : "inactive"}
              </span>
            </div>
            <div className="diagnostic-item ok">
              <strong>version</strong>
              <span>{version?.backend_version || "unknown"} / {version?.git_commit || "unknown"}</span>
            </div>
            <label className="token-field">
              <span>Backend URL</span>
              <input value={backendUrl} onChange={(event) => setBackendUrl(event.target.value)} />
            </label>
            <label className="token-field">
              <span>API token</span>
              <input value={apiToken} onChange={(event) => setApiToken(event.target.value)} type="password" />
            </label>
            <div className="button-row two">
              <button type="button" onClick={saveApiToken}>
                <CheckCircle2 size={17} />
                Save token
              </button>
              <button type="button" onClick={downloadExport}>
                <FileText size={17} />
                Export
              </button>
            </div>
            <div className="button-row two">
              <button type="button" onClick={downloadBackup}>
                <Download size={17} />
                Backup
              </button>
              <label className="file-button">
                <Upload size={17} />
                Validate restore
                <input
                  type="file"
                  accept="application/json,.json"
                  onChange={(event) => validateRestoreFile(event.target.files?.[0] || null)}
                />
              </label>
            </div>
            {restoreResult ? (
              <div className={`diagnostic-item ${restoreResult.valid ? "ok" : "warn"}`}>
                <strong>{restoreResult.valid ? "restore valid" : "restore rejected"}</strong>
                <span>
                  {restoreResult.valid
                    ? restoreResult.accepted_sections.join(",")
                    : restoreResult.reasons.join(",")}
                </span>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}

function StatusPill({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className={`status-pill ${ok ? "ok" : "warn"}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function seedTargets(previous: Record<string, number>, state: SystemState) {
  const next = { ...previous };
  for (const axis of state.axes) {
    if (!(axis.id in next)) {
      next[axis.id] = axis.commanded_position;
    }
  }
  return next;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

type SpeechRecognitionConstructor = new () => {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  start: () => void;
};

type SpeechRecognitionEventLike = {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};
