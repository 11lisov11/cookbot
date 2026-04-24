import {
  AlertTriangle,
  Bot,
  Camera,
  CheckCircle2,
  FileText,
  Hand,
  Home,
  ListChecks,
  Mic,
  Play,
  Pause,
  RefreshCw,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
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

const API_BASE = import.meta.env.VITE_API_BASE || window.location.origin;

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
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
  const [axisTargets, setAxisTargets] = useState<Record<string, number>>({});
  const [gripperTarget, setGripperTarget] = useState(0);
  const [aiCommand, setAiCommand] = useState("look at the workspace");
  const [useStream, setUseStream] = useState(true);
  const [message, setMessage] = useState("Connecting to CookBot");

  const wsUrl = useMemo(() => API_BASE.replace(/^http/, "ws") + "/ws/state", []);

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
      const [nextState, nextSnapshot, nextRecipes] = await Promise.all([
        api<SystemState>("/state"),
        api<CameraSnapshot>("/camera/snapshot"),
        api<RecipeSummary[]>("/recipes")
      ]);
      const [nextRuntime, nextWorkspace, nextDiagnostics, nextLogs, nextReadiness] = await Promise.all([
        api<RecipeRuntimeStatus>("/recipes/runtime/status"),
        api<WorkspaceModel>("/workspace"),
        api<DiagnosticsResponse>("/diagnostics"),
        api<CommandLogEntry[]>("/logs?limit=8"),
        api<HardwareReadinessResponse>("/hardware/readiness")
      ]);
      setState(nextState);
      setSnapshot(nextSnapshot);
      setRecipes(nextRecipes);
      setRuntime(nextRuntime);
      setWorkspace(nextWorkspace);
      setDiagnostics(nextDiagnostics);
      setLogs(nextLogs);
      setHardwareReadiness(nextReadiness);
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
      if (result && typeof result === "object" && "current_step" in result) {
        setRuntime(result as RecipeRuntimeStatus);
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

      <div className="work-grid">
        <section className="panel camera-panel">
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
            <img src={`${API_BASE}/camera/stream`} alt="CookBot mock camera stream" />
          ) : snapshot ? (
            <img src={snapshot.data_url} alt="CookBot mock camera" />
          ) : (
            <div className="empty">No image</div>
          )}
        </section>

        <section className="panel">
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

        <section className="panel">
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

        <section className="panel">
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

        <section className="panel">
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

        <section className="panel">
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

        <section className="panel">
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

        <section className="panel">
          <div className="panel-title">
            <ShieldAlert size={19} />
            <h2>Hardware Gate</h2>
          </div>
          <div className="diagnostic-list">
            <div className={`diagnostic-item ${hardwareReadiness?.ready_for_real_motion ? "ok" : "warn"}`}>
              <strong>{hardwareReadiness?.ready_for_real_motion ? "real motion ready" : "real motion locked"}</strong>
              <span>{hardwareReadiness?.items.filter((item) => item.verified).length || 0}/{hardwareReadiness?.items.length || 0} checks verified</span>
            </div>
            {hardwareReadiness?.items.map((item) => (
              <div className={`diagnostic-item ${item.verified ? "ok" : "warn"}`} key={item.id}>
                <strong>{item.label}</strong>
                <span>{item.evidence || "missing evidence"}</span>
              </div>
            ))}
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
