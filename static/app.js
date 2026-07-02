const SES_CONFIG = window.SES_CONFIG || {};
const API_BASE_URL = String(SES_CONFIG.API_BASE_URL || "").replace(/\/+$/, "");
const SUPABASE_AUTH_URL = String(SES_CONFIG.SUPABASE_URL || "").replace(/\/+$/, "");
const SUPABASE_ANON_KEY = String(SES_CONFIG.SUPABASE_ANON_KEY || "");
const AUTH_MODE = String(SES_CONFIG.AUTH_MODE || "public").toLowerCase();
const AUTH_STORAGE_KEY = "ses_platform_auth";

const PANEL_CODES = ["FBH", "FHB", "FBHS", "SHB", "MHBS", "SISv", "SISh"];
const VISIBLE_EI_PANELS = PANEL_CODES.filter((panel) => panel !== "FBH");
const PANEL_LABELS = {
  FBH: "FBH",
  FHB: "FHB",
  FBHS: "FBHS",
  SHB: "SHB",
  MHBS: "MHBS",
  SISv: "SISv",
  SISh: "SISh",
  DASH: "Dashboard",
};
const DEFAULT_PANEL_HEIGHTS_MM = {
  FBH: 149.98,
  FHB: 121.68,
  FBHS: 337.81,
  SHB: 101.29,
  MHBS: 248.17,
  SISv: 274.86,
  SISh: 185.4,
};
const PANEL_EI_TARGETS = {
  FBH: 3400,
  FHB: 1700,
  FBHS: 4020,
  SHB: 2320,
  MHBS: 2680,
  SISv: 5110,
  SISh: 5110,
};
const PANEL_NAME_ABBREVIATIONS = {
  "frontbulkhead": "FBH",
  "fronthoopbulkhead": "FHB",
  "frontbulkheadside": "FBHS",
  "sidehoopbulkhead": "SHB",
  "mainhoopbulkheadside": "MHBS",
  "sideimpactstructurevertical": "SISv",
  "sideimpactstructurehorizontal": "SISh",
  "dashboard": "Dashboard",
};
const PERIMETER_SHEAR_CODES = ["FBH"];
const DEFAULT_DB_SORT = { key: "updated_at", dir: "desc" };
const ENERGY_ABSORBED_THRESHOLD_J = 111.7;

const state = {
  materials: [],
  coreMaterials: [],
  materialAddOpen: false,
  materialEditMode: false,
  coreAddOpen: false,
  coreEditMode: false,
  preDatabasesOpen: false,
  preSection: "calculator",
  shuffleResults: [],
  shuffleSort: { key: "elastic_gradient_theory", dir: "desc" },
  shuffleZeroUnder50: false,
  shuffleEiPass: false,
  shuffleMaterialsOpen: false,
  monocoqueSection: "weight",
  materialEditingId: null,
  coreEditingId: null,
  databaseEditMode: false,
  preLaminate: null,
  postLaminate: null,
  preSymmetric: false,
  postSymmetric: false,
  preManualBottomSkin: null,
  postManualBottomSkin: null,
  preCalculation: null,
  postView: "input",
  processResult: null,
  specimens: [],
  selectedSpecimen: null,
  dbFilter: "",
  dbTestFilter: "all",
  dbEiPassPanels: {},
  dbPerimeterPassPanels: {},
  dbEnergyPass: false,
  dbSort: { ...DEFAULT_DB_SORT },
  cars: [],
  monocoqueCalcs: [],
  selectedCarId: null,
  carProbeMetrics: {},
  selectedMonocoqueId: null,
  carEditMode: false,
  carEditingId: null,
  carAddOpen: false,
  carDatabaseOpen: false,
  monocoqueSavedOpen: false,
  monocoqueSavedEditMode: false,
  monocoqueSavedEditingId: null,
  monocoqueSavedEditingRecord: null,
  monocoqueAssignments: {},
  monocoqueResult: null,
  auth: {
    token: "",
    email: "",
    expiresAt: 0,
    message: "",
  },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${formatNumber(Number(value) * 100, digits)}%`;
}

function formatNumberNoGrouping(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("es-ES", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
    useGrouping: false,
  });
}

function normalizedTestType(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function calculatorDimensionsForTestType(testType) {
  const normalized = normalizedTestType(testType);
  if (normalized.includes("shear")) return { width: 100, length: 100 };
  return { width: 500, length: 275 };
}

function syncPreDimensionsFromTestType() {
  const dimensions = calculatorDimensionsForTestType($("#pre-test-type")?.value);
  const widthInput = $("#pre-width");
  const lengthInput = $("#pre-length");
  if (widthInput) widthInput.value = String(dimensions.width);
  if (lengthInput) lengthInput.value = String(dimensions.length);
  return dimensions;
}

function specialTestTypeKey(value) {
  const normalized = normalizedTestType(value);
  if (normalized.includes("harness")) return "harness";
  if (normalized.includes("lapbelt") && (normalized.includes("parallel") || normalized.includes("paralel"))) return "lap_belt_parallel";
  if (normalized.includes("lapbelt") && (normalized.includes("perpendicular") || normalized.includes("perp"))) return "lap_belt_perpendicular";
  return "";
}

function isSpecialTestType(value) {
  return Boolean(specialTestTypeKey(value));
}

function specialTestLimitKn(value) {
  const key = specialTestTypeKey(value);
  if (key === "harness") return 13;
  if (key === "lap_belt_parallel" || key === "lap_belt_perpendicular") return 19.5;
  return null;
}

function isEnergyAbsorbedRelevant(value) {
  const normalized = normalizedTestType(value);
  return (
    normalized.includes("3pb") ||
    normalized.includes("3pointbend") ||
    normalized.includes("threepointbend") ||
    normalized.includes("sideimpact") ||
    normalized.includes("sisv") ||
    normalized.includes("sish")
  );
}

function energyAbsorbedJ(specimen) {
  const common = specimen?.computed?.common || {};
  const computed = specimen?.computed || {};
  const value =
    specimen?.energyAbsorbedJ ??
    specimen?.energy_absorbed_j ??
    specimen?.energyAbsorbed ??
    common.energyAbsorbedJ ??
    common.energy_absorbed_j ??
    common.energyAbsorbed ??
    computed.energyAbsorbedJ ??
    computed.energy_absorbed_j ??
    computed.energyAbsorbed;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function kgFromGrams(value, digits = 3) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  return Number.isFinite(number) ? formatNumber(number / 1000, digits) : "-";
}

function isExcelFileName(name) {
  return /\.(xlsx|xlsm|xltx|xltm)$/i.test(String(name || ""));
}

function processValidationState() {
  const form = $("#process-form");
  if (!form) return { ok: false, missing: [], invalidFile: false };
  const missing = [];
  const specimenId = form.elements.specimen_id?.value.trim();
  const testType = form.elements.test_type?.value || "";
  const realMeasurementsOptional = isSpecialTestType(testType);
  const realWeight = form.elements.real_weight_g?.value;
  const realThickness = form.elements.real_thickness_mm?.value;
  const file = $("#process-file-input")?.files?.[0];
  if (!specimenId) missing.push("Specimen ID");
  if (!realMeasurementsOptional && (realWeight === "" || !Number.isFinite(Number(realWeight)))) missing.push("Real Weight");
  if (!realMeasurementsOptional && (realThickness === "" || !Number.isFinite(Number(realThickness)))) missing.push("Real Thickness");
  if (!file) missing.push("Excel file");
  const invalidFile = Boolean(file && !isExcelFileName(file.name));
  return {
    ok: missing.length === 0 && !invalidFile,
    missing,
    invalidFile,
    fileName: file?.name || "",
    realMeasurementsOptional,
  };
}

function updateProcessUploadUi() {
  const stateInfo = processValidationState();
  const fileName = $("#process-file-name");
  const dropzone = $("#process-file-drop");
  if (fileName) {
    fileName.textContent = stateInfo.fileName || "No file selected";
    fileName.classList.toggle("has-file", Boolean(stateInfo.fileName));
  }
  if (dropzone) dropzone.classList.toggle("has-file", Boolean(stateInfo.fileName));
  updateProcessValidation();
}

function setProcessUploadFiles(files) {
  const input = $("#process-file-input");
  if (!input || !files?.length) return;
  if (typeof DataTransfer !== "undefined") {
    const transfer = new DataTransfer();
    transfer.items.add(files[0]);
    input.files = transfer.files;
  } else {
    input.files = files;
  }
  updateProcessUploadUi();
}

function updateProcessValidation(options = {}) {
  const stateInfo = processValidationState();
  const button = $("#process-submit");
  const message = $("#process-validation");
  $("#real-weight-optional")?.classList.toggle("hidden", !stateInfo.realMeasurementsOptional);
  $("#real-thickness-optional")?.classList.toggle("hidden", !stateInfo.realMeasurementsOptional);
  if (button) button.disabled = !stateInfo.ok;
  if (message) {
    if (stateInfo.ok) {
      message.textContent = "";
      message.classList.remove("is-error");
    } else if (stateInfo.invalidFile) {
      message.textContent = "Upload a valid Excel workbook: .xlsx, .xlsm, .xltx or .xltm.";
      message.classList.add("is-error");
    } else {
      message.textContent = `Required before processing: ${stateInfo.missing.join(", ")}.`;
      message.classList.toggle("is-error", Boolean(options.force));
    }
  }
  return stateInfo.ok;
}

function resetDatabaseFilters() {
  state.dbFilter = "";
  state.dbTestFilter = "all";
  state.dbEiPassPanels = {};
  state.dbPerimeterPassPanels = {};
  state.dbEnergyPass = false;
  state.dbSort = { ...DEFAULT_DB_SORT };
  const search = $("#specimen-filter");
  const testFilter = $("#specimen-test-filter");
  if (search) search.value = "";
  if (testFilter) testFilter.value = "all";
  renderSpecimenTable();
}

function resetFormSafely(form) {
  if (form && typeof form.reset === "function") form.reset();
}

function clearProcessedProbeInputs() {
  const form = $("#process-form");
  if (!form) return;
  ["specimen_id", "real_weight_g", "real_thickness_mm", "comments"].forEach((name) => {
    if (form.elements[name]) form.elements[name].value = "";
  });
  if (form.elements.test_type) form.elements.test_type.value = form.elements.test_type.options?.[0]?.value || "3PB";
  const fileInput = $("#process-file-input");
  if (fileInput) fileInput.value = "";
  updateProcessUploadUi();
}

function apiUrl(path) {
  if (/^https?:\/\//i.test(String(path))) return String(path);
  return `${API_BASE_URL}${String(path).startsWith("/") ? path : `/${path}`}`;
}

function editAuthEnabled() {
  return ["authenticated", "auth", "login"].includes(AUTH_MODE) && Boolean(SUPABASE_AUTH_URL && SUPABASE_ANON_KEY);
}

function loadAuthSession() {
  try {
    const stored = JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || "{}");
    state.auth.token = stored.token || "";
    state.auth.email = stored.email || "";
    state.auth.expiresAt = Number(stored.expiresAt || 0);
  } catch {
    state.auth.token = "";
    state.auth.email = "";
    state.auth.expiresAt = 0;
  }
}

function saveAuthSession(session) {
  state.auth.token = session.token || "";
  state.auth.email = session.email || state.auth.email || "";
  state.auth.expiresAt = Number(session.expiresAt || 0);
  if (state.auth.token) {
    localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({
        token: state.auth.token,
        email: state.auth.email,
        expiresAt: state.auth.expiresAt,
      }),
    );
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
  renderAuthControls();
}

function parseAuthRedirect() {
  if (!window.location.hash || !window.location.hash.includes("access_token")) return;
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const token = hash.get("access_token") || "";
  const expiresIn = Number(hash.get("expires_in") || 0);
  if (token) {
    saveAuthSession({
      token,
      expiresAt: expiresIn ? Date.now() + expiresIn * 1000 : 0,
    });
    state.auth.message = "Login completed";
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }
}

function hasEditSession() {
  if (!editAuthEnabled()) return true;
  if (!state.auth.token) return false;
  return !state.auth.expiresAt || Date.now() < state.auth.expiresAt - 60_000;
}

function authHeaders(headers = {}) {
  const result = { ...headers };
  if (hasEditSession() && state.auth.token) {
    result.Authorization = `Bearer ${state.auth.token}`;
  }
  return result;
}

function requireEditSession() {
  if (hasEditSession()) return true;
  showToast("Login required to add, edit or delete shared data");
  return false;
}

function renderAuthControls() {
  const target = $("#auth-controls");
  if (!target) return;
  if (!editAuthEnabled()) {
    target.innerHTML = `<span class="auth-status">Local edit mode</span>`;
    return;
  }
  if (hasEditSession()) {
    target.innerHTML = `
      <span class="auth-status is-authenticated">${escapeHtml(state.auth.email || "Logged in")}</span>
      <button class="button ghost small" data-action="logout" type="button">Log out</button>`;
    return;
  }
  target.innerHTML = `
    <form id="auth-form" class="auth-form">
      <input name="email" type="email" placeholder="email for edit access" aria-label="Email for edit access" required value="${escapeHtml(state.auth.email || "")}">
      <button class="button primary small" type="submit">Log in</button>
    </form>`;
}

async function requestMagicLink(email) {
  if (!SUPABASE_AUTH_URL || !SUPABASE_ANON_KEY) {
    throw new Error("Supabase Auth is not configured");
  }
  const response = await fetch(`${SUPABASE_AUTH_URL}/auth/v1/otp`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_ANON_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      type: "magiclink",
      options: {
        email_redirect_to: `${window.location.origin}${window.location.pathname}`,
      },
    }),
  });
  if (!response.ok) {
    let message = "Could not send login link";
    try {
      const payload = await response.json();
      message = payload.error_description || payload.msg || payload.error || message;
    } catch {}
    throw new Error(message);
  }
  state.auth.email = email;
  localStorage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({ token: "", email, expiresAt: 0 }),
  );
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 3200);
}

async function api(path, options = {}) {
  const baseHeaders = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  const { headers, ...rest } = options;
  const response = await fetch(apiUrl(path), {
    ...rest,
    headers: authHeaders({ ...baseHeaders, ...(headers || {}) }),
  });
  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload.error || payload || `Request failed: ${response.status}`);
  return payload;
}

function materialById(id) {
  return state.materials.find((material) => String(material.id) === String(id));
}

function coreByKey(key) {
  const normalized = String(key || "").trim().toLowerCase();
  return (
    state.coreMaterials.find((core) => String(core.key || "").toLowerCase() === normalized) ||
    state.coreMaterials.find((core) => String(core.name || "").toLowerCase() === normalized) ||
    state.coreMaterials.find((core) =>
      String(core.aliases || "")
        .split(";")
        .map((alias) => alias.trim().toLowerCase())
        .includes(normalized),
    ) ||
    state.coreMaterials[0]
  );
}

function orientationChoices(materialId) {
  const material = materialById(materialId);
  if (!material) return [];
  const family = String(material.fiber_family || "").toLowerCase();
  if (family === "ud") return ["0", "90"];
  if (family === "twill" || family === "biaxial") return ["+-45", "+-90"];
  return material?.fiber_type === "unidirectional" ? ["0", "90"] : ["+-45", "+-90"];
}

function defaultLayer() {
  return {
    material_id: "",
    material_name: "",
    orientation: "",
  };
}

function defaultLaminate() {
  return {
    top_skin: [],
    bottom_skin: [],
    core: { key: state.coreMaterials[0]?.key || "hc_al" },
  };
}

function laminateFor(kind) {
  return kind === "pre" ? state.preLaminate : state.postLaminate;
}

function setLaminate(kind, laminate) {
  if (kind === "pre") state.preLaminate = laminate;
  else state.postLaminate = laminate;
}

function hydrateLaminate(kind) {
  if (!laminateFor(kind)) setLaminate(kind, defaultLaminate());
  const laminate = laminateFor(kind);
  laminate.core = { key: laminate.core?.key || state.coreMaterials[0]?.key || "hc_al" };
  laminate.top_skin ||= [];
  laminate.bottom_skin ||= [];
  return laminate;
}

function buildLaminate(kind) {
  syncSymmetricLaminate(kind);
  const laminate = hydrateLaminate(kind);
  return {
    top_skin: laminate.top_skin,
    bottom_skin: laminate.bottom_skin,
    core: coreByKey($(`#${kind}-core`).value),
  };
}

function isSymmetric(kind) {
  return kind === "pre" ? state.preSymmetric : state.postSymmetric;
}

function setSymmetric(kind, enabled) {
  const laminate = hydrateLaminate(kind);
  if (kind === "pre") {
    if (enabled && !state.preSymmetric) state.preManualBottomSkin = cloneLayers(laminate.bottom_skin);
    if (!enabled && state.preSymmetric && state.preManualBottomSkin) laminate.bottom_skin = cloneLayers(state.preManualBottomSkin);
    state.preSymmetric = enabled;
  } else {
    if (enabled && !state.postSymmetric) state.postManualBottomSkin = cloneLayers(laminate.bottom_skin);
    if (!enabled && state.postSymmetric && state.postManualBottomSkin) laminate.bottom_skin = cloneLayers(state.postManualBottomSkin);
    state.postSymmetric = enabled;
  }
  syncSymmetricLaminate(kind);
}

function cloneLayers(layers = []) {
  return (layers || []).map((layer) => ({ ...layer }));
}

function mirrorTopSkin(laminate) {
  laminate.bottom_skin = cloneLayers(laminate.top_skin).reverse();
}

function syncSymmetricLaminate(kind) {
  if (isSymmetric(kind)) mirrorTopSkin(hydrateLaminate(kind));
}

function layerIsComplete(layer) {
  return Boolean((layer?.material_id !== undefined && layer.material_id !== null && layer.material_id !== "") || layer?.material_name) && Boolean(layer?.orientation);
}

function layerSignature(layer) {
  return [
    String(layer?.material_id ?? ""),
    String(layer?.material_name ?? ""),
    String(layer?.orientation ?? ""),
  ].join("|");
}

function laminateIsSymmetric(laminate) {
  const top = laminate?.top_skin || [];
  const bottom = laminate?.bottom_skin || [];
  return top.length > 0 && top.length === bottom.length && top.every((layer, index) => layerSignature(layer) === layerSignature(bottom[bottom.length - 1 - index]));
}

function laminateSequence(laminate) {
  if (!laminate) return "Incomplete laminate";
  const top = laminate.top_skin || [];
  const bottom = laminate.bottom_skin || [];
  if (!top.length || !bottom.length) return "Incomplete laminate";
  if (![...top, ...bottom].every(layerIsComplete)) return "Incomplete laminate";
  const skinText = (layers) => layers.map((layer) => `${layer.orientation}\u00ba`).join("/");
  return laminateIsSymmetric(laminate) ? `[${skinText(top)}] S` : `[${skinText(top)}] Core [${skinText(bottom)}]`;
}

function specimenLaminateSequence(specimen) {
  const fromLaminate = laminateSequence(specimen?.laminate);
  if (fromLaminate !== "Incomplete laminate") return fromLaminate;
  return specimen?.laminate_sequence || specimen?.theoretical?.laminate_sequence || fromLaminate;
}

function renderSequenceBlock(sequence) {
  const isIncomplete = sequence === "Incomplete laminate";
  return `<div class="sequence-block ${isIncomplete ? "is-incomplete" : ""}">
    <span>Laminate sequence</span>
    <strong>${escapeHtml(sequence)}</strong>
  </div>`;
}

function materialDisplayId(material) {
  return material?.name || material?.technical_id || material?.aliases || "-";
}

function preserveAliases(existing, nextName, currentAliases = "") {
  const next = String(nextName || "").trim().toLowerCase();
  const values = new Set();
  const add = (value) => {
    const text = String(value || "").trim();
    if (text && text.toLowerCase() !== next) values.add(text);
  };
  String(currentAliases || "")
    .split(";")
    .forEach(add);
  String(existing?.aliases || "")
    .split(";")
    .forEach(add);
  add(existing?.name);
  add(existing?.technical_id);
  add(existing?.key);
  return Array.from(values).join(";");
}

function materialFamilyLabel(value) {
  const family = String(value || "").toLowerCase();
  if (family === "ud") return "UD";
  if (family === "biaxial") return "biaxial";
  if (family === "twill") return "Twill";
  return family || "-";
}

function materialForLayer(layer) {
  return materialById(layer?.material_id) || state.materials.find((material) => material.name === layer?.material_name);
}

function renderLaminateStackVisualization(laminate) {
  const structure = laminate || laminateFor("pre");
  if (!structure) return "";
  const core = coreByKey(structure.core?.key || structure.core?.name || structure.core);
  const rows = [
    ...(structure.top_skin || []).map((layer) => ({ ...layer, zone: "Top" })),
    { zone: "Core", isCore: true, material_name: core?.name || "Core", orientation: "CORE", thickness_mm: core?.thickness_mm },
    ...(structure.bottom_skin || []).map((layer) => ({ ...layer, zone: "Bottom" })),
  ];
  return `<div class="laminate-visual">
    ${rows
      .map((layer) => {
        const material = materialForLayer(layer);
        const thickness = Number(layer.thickness_mm ?? material?.thickness_mm ?? 0.1);
        const label = layer.isCore ? "CORE" : orientationDisplay(layer.orientation);
        const name = layer.isCore ? layer.material_name : materialDisplayId(material) || layer.material_name;
        return `<div class="laminate-visual-layer ${layer.isCore ? "is-core" : ""}" style="--layer-flex:${Math.max(thickness || 0.1, 0.1)}">
          <strong>${escapeHtml(label)}</strong>
          <span>${escapeHtml(name)}</span>
          <em>${escapeHtml(layer.zone)} · ${formatNumber(thickness, 3)} mm</em>
        </div>`;
      })
      .join("")}
  </div>`;
}

function formatScientific(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toExponential(digits) : "-";
}

function renderMatrix(matrix, title) {
  if (!Array.isArray(matrix)) return "";
  const rows = matrix
    .map((row) => `<tr>${row.map((value) => `<td>${formatScientific(value, 3)}</td>`).join("")}</tr>`)
    .join("");
  return `<div class="matrix-card"><h4>${escapeHtml(title)}</h4><table class="matrix-table"><tbody>${rows}</tbody></table></div>`;
}

function renderLaminateVisualization(theory) {
  const layers = theory?.layers || [];
  if (!layers.length) return "";
  return `<div class="laminate-visual">
    ${layers
      .map((layer) => {
        const isCore = layer.zone === "core";
        const label = isCore ? "CORE" : `${formatNumber(layer.orientation_deg, 0)}°`;
        return `<div class="laminate-visual-layer ${isCore ? "is-core" : ""}" style="--layer-flex:${Math.max(Number(layer.thickness_mm) || 0.1, 0.1)}">
          <strong>${escapeHtml(label)}</strong>
          <span>${escapeHtml(layer.material_name)}</span>
          <em>${formatNumber(layer.thickness_mm, 3)} mm</em>
        </div>`;
      })
      .join("")}
  </div>`;
}

function renderElasticGradientHero(theory) {
  const bending = theory?.elastic_gradient_theory || {};
  if (!theory?.available) {
    return `<div class="elastic-gradient-hero is-warning">
      <span>Elastic Gradient Theory</span>
      <strong>Missing material data</strong>
      <small>${escapeHtml((theory?.warnings || ["Material mechanical values are required."])[0])}</small>
    </div>`;
  }
  return `<div class="elastic-gradient-hero">
    <span>Elastic Gradient Theory</span>
    <strong>${formatNumber(bending.elastic_gradient_theory, 3)} N/mm</strong>
  </div>`;
}

function renderLaminateTheory(theory, laminate) {
  if (!theory) return "";
  if (!theory.available) {
    return `<section class="theory-block">
      <h3>Laminate Theory</h3>
      <div class="empty-state">${(theory.warnings || ["Material mechanical values are required for laminate theory."]).map(escapeHtml).join("<br>")}</div>
    </section>`;
  }
  const eq = theory.equivalent_properties || {};
  const bending = theory.elastic_gradient_theory || {};
  return `<section class="theory-block">
    <h3>Laminate Representation</h3>
    ${renderLaminateStackVisualization(laminate)}
    <h3>Equivalent Engineering Constants</h3>
    <div class="kpi-grid theory-kpis">
      <div class="kpi"><span>E11</span><strong>${formatNumber(eq.e11_gpa, 3)} GPa</strong></div>
      <div class="kpi"><span>E22</span><strong>${formatNumber(eq.e22_gpa, 3)} GPa</strong></div>
      <div class="kpi"><span>G12</span><strong>${formatNumber(eq.g122_gpa, 3)} GPa</strong></div>
      <div class="kpi"><span>ν12 / ν21</span><strong>${formatNumber(eq.nu12, 4)} / ${formatNumber(eq.nu21, 4)}</strong></div>
      <div class="kpi"><span>EI Theory</span><strong>${formatNumber(bending.ei_theory, 3)} N·m²</strong></div>
    </div>
    ${(theory.warnings || []).length ? `<div class="validation-message">${theory.warnings.map(escapeHtml).join("<br>")}</div>` : ""}
  </section>`;
}

function moduleShells() {
  $("#pre").innerHTML = `
    <div class="pre-shell">
      <nav class="subtabs" aria-label="Pre Calculations sections">
        <button class="subtab is-active" data-pre-section="calculator" type="button">Calculator</button>
        <button class="subtab" data-pre-section="shuffle" type="button">Shuffle</button>
        <button class="subtab" data-pre-section="databases" type="button">Core & Carbon Databases</button>
      </nav>

      <div id="pre-calculator-section" class="pre-section is-active">
        <div class="grid">
          <div>
            <section class="surface">
              <h2>Specimen Configuration</h2>
              <input id="pre-width" type="hidden" value="500">
              <input id="pre-length" type="hidden" value="275">
              <div class="form-grid">
                <label>Test type
                  <select id="pre-test-type">
                    <option value="3PB">3PB</option>
                    <option value="Shear">Shear</option>
                  </select>
                </label>
                <label>Active Car
                  <select id="pre-car-select"></select>
                </label>
              </div>
              <div class="button-row">
                <button class="button ghost" data-action="toggle-symmetric" data-kind="pre" type="button">Symmetric Laminate</button>
                <button class="button primary" data-action="add-skin-layer" data-kind="pre" data-skin="top">+ Top Skin</button>
                <button class="button primary" data-action="add-skin-layer" data-kind="pre" data-skin="bottom">+ Bottom Skin</button>
              </div>
              <h3>Laminate Builder</h3>
              <div id="pre-laminate-view"></div>
            </section>
          </div>
          <aside>
            <section class="surface">
              <h2>Calculated Properties</h2>
              <div id="pre-kpis" class="kpi-grid"></div>
            </section>
          </aside>
        </div>
      </div>

      <div id="pre-shuffle-section" class="pre-section hidden">
        <section class="surface">
          <div class="section-actions">
            <h2>Shuffle Generator</h2>
            <div class="button-row">
              <button class="button primary" id="run-shuffle" type="button">Generate Variants</button>
            </div>
          </div>
          <div class="form-grid">
            <label>Total carbon layers<input id="shuffle-layer-count" type="number" min="1" max="12" step="1" value="6"></label>
            <label>Number of 0° UD plies<input id="shuffle-zero-count" type="number" min="0" max="12" step="1" value="2"></label>
            <div class="wide-label shuffle-material-picker">
              <span class="field-label">Fibre Materials</span>
              <button class="button ghost" id="shuffle-material-toggle" type="button">Select fibre materials</button>
              <div id="shuffle-material-summary" class="selected-summary"></div>
              <div id="shuffle-materials" class="shuffle-material-panel hidden"></div>
            </div>
            <label>Core material
              <select id="shuffle-core"></select>
            </label>
            <label>Maximum variants<input id="shuffle-max" type="number" min="1" max="2000" step="1" value="500"></label>
            <label>Active Car
              <select id="shuffle-car-select"></select>
            </label>
            <label>Panel
              <select id="shuffle-panel-select"></select>
            </label>
          </div>
          <div class="shuffle-controls">
            <span class="field-label">Allowed orientations</span>
            <label><input class="shuffle-orientation" type="checkbox" value="0" checked> 0°</label>
            <label><input class="shuffle-orientation" type="checkbox" value="90" checked> 90°</label>
            <label><input class="shuffle-orientation" type="checkbox" value="+-45" checked> ±45°</label>
            <label><input class="shuffle-orientation" type="checkbox" value="+-90" checked> ±90°</label>
          </div>
          <div class="shuffle-constraint">
            <label class="toggle-row"><input id="shuffle-fix-layer-two" type="checkbox"> Fix one 0° ply in layer 2</label>
            <label class="toggle-row"><input id="shuffle-layer-one-rc" type="checkbox"> Layer 1 always RC</label>
          </div>
          <div id="shuffle-feedback" class="validation-message"></div>
          <div id="shuffle-results" class="table-wrap"></div>
        </section>
      </div>

      <div id="pre-databases-section" class="pre-section hidden">
        <div id="pre-database-panels">
          <section class="surface">
            <div class="section-actions">
              <h2>Carbon Fiber Database</h2>
              <div class="button-row">
                <button class="button primary" id="show-material-add">Add New Carbon Fiber</button>
                <button class="button ghost" id="toggle-material-edit">Edit Existing Carbon Fibers</button>
              </div>
            </div>
            <form id="material-form" class="form-grid hidden">
              <label>ID<input name="name" required placeholder="RC416"></label>
              <input name="technical_id" type="hidden">
              <input name="material_category" type="hidden" value="fiber">
              <input name="aliases" type="hidden">
              <label>Fibre Tipe
                <select name="fiber_family">
                  <option value="twill">Twill</option>
                  <option value="biaxial">biaxial</option>
                  <option value="ud">UD</option>
                </select>
              </label>
              <label>Espesor (mm)<input name="thickness_mm" type="number" step="0.001" required></label>
              <label>Gramaje [g/m2]<input name="areal_weight_g_m2" type="number" step="0.1" required></label>
              <label class="hidden">Fiber type
                <select name="fiber_type">
                  <option value="bidirectional">Bidirectional</option>
                  <option value="unidirectional">Unidirectional</option>
                </select>
              </label>
              <label>Resin percentage<input name="resin_fraction" type="number" step="0.01" min="0" max="0.95" value="0.35"></label>
              <label>E1 (Pa)<input name="e1_pa" type="number" step="any"></label>
              <label>E2 (Pa)<input name="e2_pa" type="number" step="any"></label>
              <label>G12 (Pa)<input name="g12_pa" type="number" step="any"></label>
              <label>Poisson de entrada<input name="poisson_input" type="number" step="any"></label>
              <label>Resistencia X (opcional)<input name="strength_x_mpa" type="number" step="any"></label>
              <label>Resistencia X compresión (opcional)<input name="strength_x_compression_mpa" type="number" step="any"></label>
              <label>Resistencia Y (opcional)<input name="strength_y_mpa" type="number" step="any"></label>
              <label>Resistencia Y compresión (opcional)<input name="strength_y_compression_mpa" type="number" step="any"></label>
              <label>Resistencia cortante (opcional)<input name="strength_s_mpa" type="number" step="any"></label>
              <label>Density [kg/m3]<input name="density_kg_m3" type="number" step="0.1"></label>
              <label>Notas (opcional)<input name="notes" placeholder="Notas de material"></label>
              <div class="button-row"><button class="button primary" type="submit">Create carbon fiber</button></div>
            </form>
            <div id="material-list" class="table-wrap"></div>
          </section>
          <section class="surface">
            <div class="section-actions">
              <h2>Core Database</h2>
              <div class="button-row">
                <button class="button primary" id="show-core-add">Add New Core Material</button>
                <button class="button ghost" id="toggle-core-edit">Edit Existing Core Materials</button>
              </div>
            </div>
            <form id="core-form" class="form-grid hidden">
              <label>ID<input name="name" required placeholder="Aluminum HC (20 mm)"></label>
              <input name="technical_id" type="hidden">
              <input name="material_category" type="hidden" value="core">
              <input name="fiber_family" type="hidden" value="">
              <input name="aliases" type="hidden">
              <label>Core type<input name="type" required placeholder="honeycomb"></label>
              <label>Espesor (mm)<input name="thickness_mm" type="number" step="0.001" required></label>
              <label>Density [kg/m3]<input name="density_kg_m3" type="number" step="0.1" required></label>
              <label>E1 (Pa)<input name="e1_pa" type="number" step="any"></label>
              <label>E2 (Pa)<input name="e2_pa" type="number" step="any"></label>
              <label>G12 (Pa)<input name="g12_pa" type="number" step="any"></label>
              <label>Poisson de entrada<input name="poisson_input" type="number" step="any"></label>
              <label>Resistencia X (opcional)<input name="strength_x_mpa" type="number" step="any"></label>
              <label>Resistencia X compresión (opcional)<input name="strength_x_compression_mpa" type="number" step="any"></label>
              <label>Resistencia Y (opcional)<input name="strength_y_mpa" type="number" step="any"></label>
              <label>Resistencia Y compresión (opcional)<input name="strength_y_compression_mpa" type="number" step="any"></label>
              <label>Resistencia cortante (opcional)<input name="strength_s_mpa" type="number" step="any"></label>
              <label>Notas (opcional)<input name="notes" placeholder="Notas de core"></label>
              <div class="button-row"><button class="button primary" type="submit">Create core material</button></div>
            </form>
            <div id="core-list" class="table-wrap"></div>
          </section>
        </div>
      </div>
    </div>`;

  $("#post").innerHTML = `
    <div id="post-input-view" class="post-input-view">
      <section class="surface">
        <h2>Specimen Laminate</h2>
        <div class="form-grid">
          <label>Specimen width [mm]<input id="post-width" type="number" step="0.01" value="500"></label>
          <label>Specimen length [mm]<input id="post-length" type="number" step="0.01" value="275"></label>
        </div>
        <div class="button-row">
          <button class="button ghost" data-action="toggle-symmetric" data-kind="post" type="button">Symmetric Laminate</button>
          <button class="button primary" data-action="add-skin-layer" data-kind="post" data-skin="top">+ Top Skin</button>
          <button class="button primary" data-action="add-skin-layer" data-kind="post" data-skin="bottom">+ Bottom Skin</button>
        </div>
        <div id="post-laminate-view"></div>
      </section>
      <section class="surface">
        <h2>Experimental Data</h2>
        <div id="post-laminate-summary"></div>
        <form id="process-form" class="form-grid" enctype="multipart/form-data">
          <label>Specimen ID<input name="specimen_id" id="process-id" required placeholder="2026-P04-01"></label>
          <label>Test type
            <select name="test_type" id="process-test-type">
              <option value="3PB">3PB</option>
              <option value="Shear">Shear</option>
              <option value="Harness">Harness</option>
              <option value="Lap Belt Parallel">Lap Belt Parallel</option>
              <option value="Lap Belt Perp.">Lap Belt Perp.</option>
            </select>
          </label>
          <label>Active car
            <select name="car_id" id="process-car-select"></select>
          </label>
          <label>Real weight [g]<span id="real-weight-optional" class="optional-hint hidden"> (optional)</span><input name="real_weight_g" type="number" step="0.001"></label>
          <label>Real thickness [mm]<span id="real-thickness-optional" class="optional-hint hidden"> (optional)</span><input name="real_thickness_mm" type="number" step="0.001"></label>
          <label>Span [mm]<input value="400" disabled><input name="span_mm" type="hidden" value="400"></label>
          <div class="upload-field wide-label">
            <span class="field-label">Excel file</span>
            <label id="process-file-drop" class="upload-dropzone" for="process-file-input">
              <input id="process-file-input" name="file" type="file" accept=".xlsx,.xlsm,.xltx,.xltm">
              <strong>Drag Excel file here or click to upload</strong>
              <span>Accepted: .xlsx, .xlsm, .xltx, .xltm</span>
              <em id="process-file-name">No file selected</em>
            </label>
          </div>
          <label class="wide-label">Comments<textarea name="comments" id="post-comments" rows="4" placeholder="Test observations, laminate notes, defects..."></textarea></label>
          <div class="button-row wide-label">
            <button id="process-submit" class="button primary" type="submit" disabled>Process data</button>
            <span id="process-validation" class="validation-message" aria-live="polite"></span>
          </div>
        </form>
      </section>
    </div>
    <div id="post-results-view" class="post-results-view hidden">
      <div id="processed-probe-header"></div>
      <section class="surface">
        <div class="section-actions">
          <h2>Results Overview</h2>
          <div class="button-row">
            <button class="button ghost" data-action="post-edit-input" type="button">Edit Input</button>
            <button class="button primary" data-action="post-edit-input" type="button">Process Another Probe</button>
          </div>
        </div>
        <canvas id="process-chart" width="900" height="520"></canvas>
      </section>
      <section id="post-computed-metrics-section" class="surface">
        <h2>Computed Metrics</h2>
        <div id="process-results" class="table-wrap"></div>
      </section>
    </div>`;

  $("#database").innerHTML = `
    <section class="surface database-only">
      <div class="section-actions">
        <h2>Probes</h2>
        <div class="database-control-stack">
          <div class="database-action-row">
            <button class="button ghost equal-action" id="refresh-db">Reset filters</button>
            <button class="button ghost equal-action" id="recalculate-selected-car" type="button">Recalculate SES</button>
          </div>
          <div class="database-filter-row">
            <input id="specimen-filter" class="table-search" aria-label="Search probes" placeholder="Search probes">
            <label class="inline-filter">Test
              <select id="specimen-test-filter">
                <option value="all">All</option>
                <option value="3PB">3PB</option>
                <option value="Shear">Shear</option>
              </select>
            </label>
            <label class="inline-filter">Active car
              <select id="database-car-select"></select>
            </label>
            <label class="toggle-row"><input id="database-edit-mode" type="checkbox"> Edit mode</label>
          </div>
        </div>
      </div>
      <div id="specimen-table" class="table-wrap"></div>
    </section>
    <div id="specimen-modal" class="modal-backdrop hidden">
      <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="specimen-modal-title">
        <div id="specimen-detail"></div>
      </section>
    </div>`;

  $("#monocoque").innerHTML = `
    <nav class="subtabs" aria-label="Monocoque Weight sections">
      <button class="subtab is-active" data-monocoque-section="weight" type="button">Weight</button>
      <button class="subtab" data-monocoque-section="databases" type="button">Car & Calculations Databases</button>
    </nav>
    <div class="grid monocoque-grid">
      <div>
        <section class="surface">
          <div class="section-actions">
            <h2>Monocoque Configuration</h2>
            <div class="button-row">
              <button class="button primary" id="save-monocoque">Save Calculation</button>
            </div>
          </div>
          <div class="form-grid">
            <label>Calculation name<input id="monocoque-name" value="Monocoque weight"></label>
            <label>Car
              <select id="monocoque-car-select"></select>
            </label>
            <label>Front Hoop volume [m³]<input id="front-hoop-volume" type="number" step="0.000001" value="0.000239266"></label>
            <label>FH material density [kg/m³]<input id="front-hoop-density" type="number" step="1" value="7850"></label>
            <label>Total hardpoints weight [kg]<input id="hardpoints-weight" type="number" step="0.001" value="0"></label>
          </div>
          <div id="monocoque-panel-assignments" class="table-wrap monocoque-table"></div>
        </section>
        <div class="database-gate">
          <button class="button ghost" id="toggle-car-database" type="button">Open Car Database</button>
        </div>
        <section id="car-database-panel" class="surface hidden">
          <div class="section-actions">
            <h2>Car Database</h2>
            <div class="button-row">
              <button class="button primary" id="show-car-add">Add New Car</button>
              <label class="toggle-row"><input id="car-edit-mode" type="checkbox"> Edit mode</label>
            </div>
          </div>
          <form id="car-form" class="form-grid hidden">
            <label>Car name<input name="name" required placeholder="MAD Formula MFT"></label>
            <div class="button-row"><button class="button primary" type="submit">Create car</button></div>
          </form>
          <div id="car-list" class="table-wrap"></div>
        </section>
        <div class="database-gate">
          <button class="button ghost" id="toggle-monocoque-saved" type="button">Open Saved Calculations</button>
        </div>
        <section id="monocoque-saved-panel" class="surface hidden">
          <div class="section-actions">
            <h2>Saved Calculations</h2>
            <div class="button-row">
              <label class="toggle-row"><input id="monocoque-saved-edit-mode" type="checkbox"> Edit mode</label>
            </div>
          </div>
          <div id="monocoque-saved-list" class="table-wrap"></div>
        </section>
      </div>
      <aside>
        <section class="surface">
          <h2>Weight Summary</h2>
          <div id="monocoque-summary" class="kpi-grid"></div>
        </section>
      </aside>
    </div>`;
}

function renderCoreOptions(kind) {
  const laminate = hydrateLaminate(kind);
  const select = $(`#${kind}-core`);
  if (!select) return;
  select.innerHTML = state.coreMaterials
    .map((core) => `<option value="${core.key}" ${core.key === laminate.core.key ? "selected" : ""}>${escapeHtml(core.name)}</option>`)
    .join("");
}

function paToGpa(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number / 1e9 : null;
}

function gpaToPa(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number * 1e9 : null;
}

function formatGpa(value, digits = 3) {
  const gpa = paToGpa(value);
  return gpa === null ? "-" : formatNumber(gpa, digits);
}

function inputNumberValue(value, digits = 6) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  return Number(number.toFixed(digits)).toString();
}

function inputGpaValue(value) {
  const gpa = paToGpa(value);
  return inputNumberValue(gpa, 6);
}

function materialHasTheoryData(material) {
  return ["e1_pa", "e2_pa", "g12_pa", "poisson_input"].every((key) => {
    const value = Number(material?.[key]);
    return Number.isFinite(value) && (key === "poisson_input" || value > 0);
  });
}

function renderMaterialEditor(material) {
  if (!material) return "";
  const family = material.fiber_family || (material.fiber_type === "unidirectional" ? "ud" : "twill");
  return `<section class="database-editor-panel">
    <div class="section-actions">
      <h3>Edit Carbon Fiber: ${escapeHtml(materialDisplayId(material))}</h3>
      <button class="button ghost small" data-action="close-material-editor" type="button">Close</button>
    </div>
    <div class="form-grid">
      <label>ID<input data-edit-material="${material.id}" data-field="name" value="${escapeHtml(materialDisplayId(material))}"></label>
      <input type="hidden" data-edit-material="${material.id}" data-field="technical_id" value="${escapeHtml(materialDisplayId(material))}">
      <input type="hidden" data-edit-material="${material.id}" data-field="aliases" value="${escapeHtml(material.aliases || "")}">
      <label>Fibre Tipe
        <select data-edit-material="${material.id}" data-field="fiber_family">
          <option value="twill" ${family === "twill" ? "selected" : ""}>Twill</option>
          <option value="biaxial" ${family === "biaxial" ? "selected" : ""}>biaxial</option>
          <option value="ud" ${family === "ud" ? "selected" : ""}>UD</option>
        </select>
      </label>
      <label>Gramaje [g/m2]<input data-edit-material="${material.id}" data-field="areal_weight_g_m2" type="number" step="0.1" value="${material.areal_weight_g_m2}"></label>
      <label>Thickness [mm]<input data-edit-material="${material.id}" data-field="thickness_mm" type="number" step="0.001" value="${material.thickness_mm}"></label>
      <label>Resin percentage<input data-edit-material="${material.id}" data-field="resin_fraction" type="number" step="0.01" value="${material.resin_fraction}"></label>
      <label>E1 (Pa)<input data-edit-material="${material.id}" data-field="e1_pa" type="number" step="any" value="${inputNumberValue(material.e1_pa, 3)}"></label>
      <label>E2 (Pa)<input data-edit-material="${material.id}" data-field="e2_pa" type="number" step="any" value="${inputNumberValue(material.e2_pa, 3)}"></label>
      <label>G12 (Pa)<input data-edit-material="${material.id}" data-field="g12_pa" type="number" step="any" value="${inputNumberValue(material.g12_pa, 3)}"></label>
      <label>Poisson de entrada<input data-edit-material="${material.id}" data-field="poisson_input" type="number" step="any" value="${material.poisson_input ?? ""}"></label>
      <label>Resistencia X (opcional)<input data-edit-material="${material.id}" data-field="strength_x_mpa" type="number" step="any" value="${material.strength_x_mpa ?? ""}"></label>
      <label>Resistencia X compresión (opcional)<input data-edit-material="${material.id}" data-field="strength_x_compression_mpa" type="number" step="any" value="${material.strength_x_compression_mpa ?? ""}"></label>
      <label>Resistencia Y (opcional)<input data-edit-material="${material.id}" data-field="strength_y_mpa" type="number" step="any" value="${material.strength_y_mpa ?? ""}"></label>
      <label>Resistencia Y compresión (opcional)<input data-edit-material="${material.id}" data-field="strength_y_compression_mpa" type="number" step="any" value="${material.strength_y_compression_mpa ?? ""}"></label>
      <label>Resistencia cortante (opcional)<input data-edit-material="${material.id}" data-field="strength_s_mpa" type="number" step="any" value="${material.strength_s_mpa ?? ""}"></label>
      <label>Density [kg/m3]<input data-edit-material="${material.id}" data-field="density_kg_m3" type="number" step="0.1" value="${material.density_kg_m3 ?? ""}"></label>
      <label>Notas (opcional)<input data-edit-material="${material.id}" data-field="notes" value="${escapeHtml(material.notes || "")}"></label>
    </div>
    <div class="button-row"><button class="button primary" data-action="save-material" data-id="${material.id}" type="button">Save carbon fiber</button></div>
  </section>`;
}

function renderCoreEditor(core) {
  if (!core) return "";
  return `<section class="database-editor-panel">
    <div class="section-actions">
      <h3>Edit Core: ${escapeHtml(core.name || core.key || "")}</h3>
      <button class="button ghost small" data-action="close-core-editor" type="button">Close</button>
    </div>
    <div class="form-grid">
      <label>ID<input data-edit-core="${core.id}" data-field="name" value="${escapeHtml(core.name || core.key || "")}"></label>
      <input type="hidden" data-edit-core="${core.id}" data-field="technical_id" value="${escapeHtml(core.technical_id || core.key || core.name || "")}">
      <input type="hidden" data-edit-core="${core.id}" data-field="aliases" value="${escapeHtml(core.aliases || "")}">
      <label>Espesor<input data-edit-core="${core.id}" data-field="thickness_mm" type="number" step="0.001" value="${core.thickness_mm}"></label>
      <label>Core Type<input data-edit-core="${core.id}" data-field="type" value="${escapeHtml(core.type || "")}"></label>
      <label>density<input data-edit-core="${core.id}" data-field="density_kg_m3" type="number" step="0.1" value="${core.density_kg_m3}"></label>
      <label>E1 (Pa)<input data-edit-core="${core.id}" data-field="e1_pa" type="number" step="any" value="${inputNumberValue(core.e1_pa, 3)}"></label>
      <label>E2 (Pa)<input data-edit-core="${core.id}" data-field="e2_pa" type="number" step="any" value="${inputNumberValue(core.e2_pa, 3)}"></label>
      <label>G12 (Pa)<input data-edit-core="${core.id}" data-field="g12_pa" type="number" step="any" value="${inputNumberValue(core.g12_pa, 3)}"></label>
      <label>Poisson de entrada<input data-edit-core="${core.id}" data-field="poisson_input" type="number" step="any" value="${core.poisson_input ?? ""}"></label>
      <label>Resistencia X (opcional)<input data-edit-core="${core.id}" data-field="strength_x_mpa" type="number" step="any" value="${core.strength_x_mpa ?? ""}"></label>
      <label>Resistencia X compresión (opcional)<input data-edit-core="${core.id}" data-field="strength_x_compression_mpa" type="number" step="any" value="${core.strength_x_compression_mpa ?? ""}"></label>
      <label>Resistencia Y (opcional)<input data-edit-core="${core.id}" data-field="strength_y_mpa" type="number" step="any" value="${core.strength_y_mpa ?? ""}"></label>
      <label>Resistencia Y compresión (opcional)<input data-edit-core="${core.id}" data-field="strength_y_compression_mpa" type="number" step="any" value="${core.strength_y_compression_mpa ?? ""}"></label>
      <label>Resistencia cortante (opcional)<input data-edit-core="${core.id}" data-field="strength_s_mpa" type="number" step="any" value="${core.strength_s_mpa ?? ""}"></label>
      <label>Notas (opcional)<input data-edit-core="${core.id}" data-field="notes" value="${escapeHtml(core.notes || "")}"></label>
    </div>
    <div class="button-row"><button class="button primary" data-action="save-core" data-id="${core.id}" type="button">Save core</button></div>
  </section>`;
}

function renderMaterialList() {
  const compactRows = state.materials
    .map((m) => {
      const actions = state.materialEditMode
        ? `<td class="row-actions"><button class="button small" data-action="edit-material" data-id="${m.id}">Edit</button><button class="button danger small" data-action="delete-material" data-id="${m.id}">Delete</button></td>`
        : "";
      return `<tr>
        <td>${escapeHtml(materialDisplayId(m))}</td>
        <td>${escapeHtml(materialFamilyLabel(m.fiber_family || (m.fiber_type === "unidirectional" ? "ud" : "twill")))}</td>
        <td>${formatNumber(m.areal_weight_g_m2, 1)}</td>
        <td>${formatNumber(m.thickness_mm, 3)}</td>
        ${actions}
      </tr>`;
    })
    .join("");
  const compactActionHeader = state.materialEditMode ? "<th>Actions</th>" : "";
  const editor = state.materialEditMode ? renderMaterialEditor(state.materials.find((m) => String(m.id) === String(state.materialEditingId))) : "";
  $("#material-list").innerHTML = `
    <table class="tight-table compact-database-table">
      <thead><tr><th>ID</th><th>Fibre Tipe</th><th>Gramaje [g/m2]</th><th>Thickness [mm]</th>${compactActionHeader}</tr></thead>
      <tbody>${compactRows}</tbody>
    </table>
    ${editor}`;
  $("#material-form").classList.toggle("hidden", !state.materialAddOpen);
  $("#toggle-material-edit").classList.toggle("is-active", state.materialEditMode);
  return;
  const rows = state.materials
    .map((m) => {
      const category = m.material_category || "fiber";
      const family = m.fiber_family || (m.fiber_type === "unidirectional" ? "ud" : "twill");
      if (state.materialEditMode) {
        return `
          <tr data-material-id="${m.id}">
            <td><input data-edit-material="${m.id}" data-field="technical_id" value="${escapeHtml(m.technical_id || m.name || "")}"></td>
            <td><input data-edit-material="${m.id}" data-field="name" value="${escapeHtml(m.name)}"></td>
            <td>
              <select data-edit-material="${m.id}" data-field="material_category">
                <option value="fiber" ${category === "fiber" ? "selected" : ""}>Fibra</option>
                <option value="core" ${category === "core" ? "selected" : ""}>Core</option>
              </select>
            </td>
            <td>
              <select data-edit-material="${m.id}" data-field="fiber_family">
                <option value="twill" ${family === "twill" ? "selected" : ""}>Twill</option>
                <option value="ud" ${family === "ud" ? "selected" : ""}>UD</option>
              </select>
            </td>
            <td><input data-edit-material="${m.id}" data-field="e1_pa" type="number" step="any" value="${inputNumberValue(m.e1_pa, 3)}"></td>
            <td><input data-edit-material="${m.id}" data-field="e2_pa" type="number" step="any" value="${inputNumberValue(m.e2_pa, 3)}"></td>
            <td><input data-edit-material="${m.id}" data-field="g12_pa" type="number" step="any" value="${inputNumberValue(m.g12_pa, 3)}"></td>
            <td><input data-edit-material="${m.id}" data-field="poisson_input" type="number" step="any" value="${m.poisson_input ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="strength_x_mpa" type="number" step="any" value="${m.strength_x_mpa ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="strength_x_compression_mpa" type="number" step="any" value="${m.strength_x_compression_mpa ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="strength_y_mpa" type="number" step="any" value="${m.strength_y_mpa ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="strength_y_compression_mpa" type="number" step="any" value="${m.strength_y_compression_mpa ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="strength_s_mpa" type="number" step="any" value="${m.strength_s_mpa ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="thickness_mm" type="number" step="0.001" value="${m.thickness_mm}"></td>
            <td><input data-edit-material="${m.id}" data-field="notes" value="${escapeHtml(m.notes || "")}"></td>
            <td><input data-edit-material="${m.id}" data-field="areal_weight_g_m2" type="number" step="0.1" value="${m.areal_weight_g_m2}"></td>
            <td><input data-edit-material="${m.id}" data-field="resin_fraction" type="number" step="0.01" value="${m.resin_fraction}"></td>
            <td><input data-edit-material="${m.id}" data-field="density_kg_m3" type="number" step="0.1" value="${m.density_kg_m3 ?? ""}"></td>
            <td><input data-edit-material="${m.id}" data-field="aliases" value="${escapeHtml(m.aliases || "")}"></td>
            <td>${materialHasTheoryData(m) ? `<span class="pill good">Ready</span>` : `<span class="pill warn">Missing</span>`}</td>
            <td class="row-actions">
              <button class="button small" data-action="save-material" data-id="${m.id}">Save</button>
              <button class="button danger small" data-action="delete-material" data-id="${m.id}">Delete</button>
            </td>
          </tr>`;
      }
      return `
        <tr>
          <td>${escapeHtml(m.technical_id || m.name || "")}</td>
          <td>${escapeHtml(m.name)}</td>
          <td><span class="pill blue">${category === "fiber" ? "Fibra" : "Core"}</span></td>
          <td>${escapeHtml(family)}</td>
          <td>${formatScientific(m.e1_pa, 3)}</td>
          <td>${formatScientific(m.e2_pa, 3)}</td>
          <td>${formatScientific(m.g12_pa, 3)}</td>
          <td>${formatNumber(m.poisson_input, 4)}</td>
          <td>${formatNumber(m.strength_x_mpa, 2)}</td>
          <td>${formatNumber(m.strength_x_compression_mpa, 2)}</td>
          <td>${formatNumber(m.strength_y_mpa, 2)}</td>
          <td>${formatNumber(m.strength_y_compression_mpa, 2)}</td>
          <td>${formatNumber(m.strength_s_mpa, 2)}</td>
          <td>${formatNumber(m.thickness_mm, 3)}</td>
          <td>${escapeHtml(m.notes || "")}</td>
          <td>${formatNumber(m.areal_weight_g_m2, 1)}</td>
          <td>${formatPercent(m.resin_fraction, 1)}</td>
          <td>${formatNumber(m.density_kg_m3, 1)}</td>
          <td>${escapeHtml(m.aliases || "")}</td>
          <td>${materialHasTheoryData(m) ? `<span class="pill good">Ready</span>` : `<span class="pill warn">Missing</span>`}</td>
        </tr>`;
    })
    .join("");
  const actionHeader = state.materialEditMode ? "<th>Actions</th>" : "";
  $("#material-list").innerHTML = `
    <table class="tight-table material-library-table">
      <thead><tr><th>ID técnico</th><th>Nombre visible</th><th>Tipo de material</th><th>Familia de fibra</th><th>E1 (Pa)</th><th>E2 (Pa)</th><th>G12 (Pa)</th><th>Poisson de entrada</th><th>Resistencia X (opcional)</th><th>Resistencia X compresión (opcional)</th><th>Resistencia Y (opcional)</th><th>Resistencia Y compresión (opcional)</th><th>Resistencia cortante (opcional)</th><th>Espesor (mm)</th><th>Notas (opcional)</th><th>Gramaje [g/m2]</th><th>Resin percentage</th><th>Density [kg/m3]</th><th>Aliases</th><th>Laminate theory</th>${actionHeader}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  $("#material-form").classList.toggle("hidden", !state.materialAddOpen);
  $("#toggle-material-edit").classList.toggle("is-active", state.materialEditMode);
}

function renderCoreList() {
  const compactRows = state.coreMaterials
    .map((core) => {
      const actions = state.coreEditMode
        ? `<td class="row-actions"><button class="button small" data-action="edit-core" data-id="${core.id}">Edit</button><button class="button danger small" data-action="delete-core" data-id="${core.id}">Delete</button></td>`
        : "";
      return `<tr>
        <td>${escapeHtml(core.name || core.technical_id || core.key || "")}</td>
        <td>${formatNumber(core.thickness_mm, 3)}</td>
        <td>${escapeHtml(core.type || "-")}</td>
        <td>${formatNumber(core.density_kg_m3, 1)}</td>
        ${actions}
      </tr>`;
    })
    .join("");
  const compactActionHeader = state.coreEditMode ? "<th>Actions</th>" : "";
  const editor = state.coreEditMode ? renderCoreEditor(state.coreMaterials.find((core) => String(core.id) === String(state.coreEditingId))) : "";
  $("#core-list").innerHTML = `
    <table class="tight-table compact-database-table">
      <thead><tr><th>ID</th><th>Espesor</th><th>Core Type</th><th>density</th>${compactActionHeader}</tr></thead>
      <tbody>${compactRows}</tbody>
    </table>
    ${editor}`;
  $("#core-form").classList.toggle("hidden", !state.coreAddOpen);
  $("#toggle-core-edit").classList.toggle("is-active", state.coreEditMode);
  return;
  const rows = state.coreMaterials
    .map((core) => {
      const category = core.material_category || "core";
      if (state.coreEditMode) {
        return `
          <tr data-core-id="${core.id}">
            <td><input data-edit-core="${core.id}" data-field="technical_id" value="${escapeHtml(core.technical_id || core.key || "")}"></td>
            <td><input data-edit-core="${core.id}" data-field="name" value="${escapeHtml(core.name)}"></td>
            <td>
              <select data-edit-core="${core.id}" data-field="material_category">
                <option value="core" ${category === "core" ? "selected" : ""}>Core</option>
                <option value="fiber" ${category === "fiber" ? "selected" : ""}>Fibra</option>
              </select>
            </td>
            <td>
              <select data-edit-core="${core.id}" data-field="fiber_family">
                <option value="" ${(core.fiber_family || "") === "" ? "selected" : ""}>N/A</option>
                <option value="twill" ${core.fiber_family === "twill" ? "selected" : ""}>Twill</option>
                <option value="ud" ${core.fiber_family === "ud" ? "selected" : ""}>UD</option>
              </select>
            </td>
            <td><input data-edit-core="${core.id}" data-field="e1_pa" type="number" step="any" value="${inputNumberValue(core.e1_pa, 3)}"></td>
            <td><input data-edit-core="${core.id}" data-field="e2_pa" type="number" step="any" value="${inputNumberValue(core.e2_pa, 3)}"></td>
            <td><input data-edit-core="${core.id}" data-field="g12_pa" type="number" step="any" value="${inputNumberValue(core.g12_pa, 3)}"></td>
            <td><input data-edit-core="${core.id}" data-field="poisson_input" type="number" step="any" value="${core.poisson_input ?? ""}"></td>
            <td><input data-edit-core="${core.id}" data-field="strength_x_mpa" type="number" step="any" value="${core.strength_x_mpa ?? ""}"></td>
            <td><input data-edit-core="${core.id}" data-field="strength_x_compression_mpa" type="number" step="any" value="${core.strength_x_compression_mpa ?? ""}"></td>
            <td><input data-edit-core="${core.id}" data-field="strength_y_mpa" type="number" step="any" value="${core.strength_y_mpa ?? ""}"></td>
            <td><input data-edit-core="${core.id}" data-field="strength_y_compression_mpa" type="number" step="any" value="${core.strength_y_compression_mpa ?? ""}"></td>
            <td><input data-edit-core="${core.id}" data-field="strength_s_mpa" type="number" step="any" value="${core.strength_s_mpa ?? ""}"></td>
            <td><input data-edit-core="${core.id}" data-field="thickness_mm" type="number" step="0.001" value="${core.thickness_mm}"></td>
            <td><input data-edit-core="${core.id}" data-field="notes" value="${escapeHtml(core.notes || "")}"></td>
            <td><input data-edit-core="${core.id}" data-field="type" value="${escapeHtml(core.type || "")}"></td>
            <td><input data-edit-core="${core.id}" data-field="density_kg_m3" type="number" step="0.1" value="${core.density_kg_m3}"></td>
            <td><input data-edit-core="${core.id}" data-field="aliases" value="${escapeHtml(core.aliases || "")}"></td>
            <td>${materialHasTheoryData(core) ? `<span class="pill good">Ready</span>` : `<span class="pill warn">Missing</span>`}</td>
            <td class="row-actions">
              <button class="button small" data-action="save-core" data-id="${core.id}">Save</button>
              <button class="button danger small" data-action="delete-core" data-id="${core.id}">Delete</button>
            </td>
          </tr>`;
      }
      return `
        <tr>
          <td>${escapeHtml(core.technical_id || core.key || "")}</td>
          <td>${escapeHtml(core.name)}</td>
          <td><span class="pill blue">${category === "core" ? "Core" : "Fibra"}</span></td>
          <td>${escapeHtml(core.fiber_family || "")}</td>
          <td>${formatScientific(core.e1_pa, 3)}</td>
          <td>${formatScientific(core.e2_pa, 3)}</td>
          <td>${formatScientific(core.g12_pa, 3)}</td>
          <td>${formatNumber(core.poisson_input, 4)}</td>
          <td>${formatNumber(core.strength_x_mpa, 2)}</td>
          <td>${formatNumber(core.strength_x_compression_mpa, 2)}</td>
          <td>${formatNumber(core.strength_y_mpa, 2)}</td>
          <td>${formatNumber(core.strength_y_compression_mpa, 2)}</td>
          <td>${formatNumber(core.strength_s_mpa, 2)}</td>
          <td>${formatNumber(core.thickness_mm, 3)}</td>
          <td>${escapeHtml(core.notes || "")}</td>
          <td>${escapeHtml(core.type || "")}</td>
          <td>${formatNumber(core.density_kg_m3, 1)}</td>
          <td>${escapeHtml(core.aliases || "")}</td>
          <td>${materialHasTheoryData(core) ? `<span class="pill good">Ready</span>` : `<span class="pill warn">Missing</span>`}</td>
        </tr>`;
    })
    .join("");
  const actionHeader = state.coreEditMode ? "<th>Actions</th>" : "";
  $("#core-list").innerHTML = `
    <table class="material-library-table">
      <thead><tr><th>ID técnico</th><th>Nombre visible</th><th>Tipo de material</th><th>Familia de fibra</th><th>E1 (Pa)</th><th>E2 (Pa)</th><th>G12 (Pa)</th><th>Poisson de entrada</th><th>Resistencia X (opcional)</th><th>Resistencia X compresión (opcional)</th><th>Resistencia Y (opcional)</th><th>Resistencia Y compresión (opcional)</th><th>Resistencia cortante (opcional)</th><th>Espesor (mm)</th><th>Notas (opcional)</th><th>Core type</th><th>Density [kg/m3]</th><th>Aliases</th><th>Laminate theory</th>${actionHeader}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  $("#core-form").classList.toggle("hidden", !state.coreAddOpen);
  $("#toggle-core-edit").classList.toggle("is-active", state.coreEditMode);
}

function renderShuffleControls() {
  const box = $("#shuffle-materials");
  if (!box) return;
  const checked = new Set($$(".shuffle-material-option:checked").map((input) => String(input.value)));
  const selected = checked.size ? checked : new Set(state.materials.map((material) => String(material.id)));
  const grouped = new Map();
  state.materials.forEach((material) => {
    const group = materialFamilyLabel(material.fiber_family || (material.fiber_type === "unidirectional" ? "ud" : "twill"));
    if (!grouped.has(group)) grouped.set(group, []);
    grouped.get(group).push(material);
  });
  box.classList.toggle("hidden", !state.shuffleMaterialsOpen);
  box.innerHTML = Array.from(grouped.entries())
    .map(([group, materials]) => `
      <section class="selector-group">
        <h4>${escapeHtml(group)}</h4>
        <div class="multi-check-grid">
          ${materials
            .map((material) => `<label class="check-card">
              <input class="shuffle-material-option" type="checkbox" value="${material.id}" ${selected.has(String(material.id)) ? "checked" : ""}>
              <strong>${escapeHtml(materialDisplayId(material))}</strong>
              <span>${escapeHtml(materialFamilyLabel(material.fiber_family))}</span>
            </label>`)
            .join("")}
        </div>
      </section>`)
    .join("");
  updateShuffleMaterialSummary();
  const coreSelect = $("#shuffle-core");
  if (coreSelect) {
    const currentCore = coreSelect.value;
    coreSelect.innerHTML = state.coreMaterials
      .map((core) => `<option value="${escapeHtml(core.key)}" ${String(core.key) === String(currentCore) ? "selected" : ""}>${escapeHtml(core.name)}</option>`)
      .join("");
    if (!coreSelect.value && state.coreMaterials[0]) coreSelect.value = state.coreMaterials[0].key;
  }
  renderShufflePanelOptions();
  renderShuffleResults();
}

function selectedShuffleMaterialIds() {
  return $$(".shuffle-material-option:checked").map((input) => String(input.value));
}

function updateShuffleMaterialSummary() {
  const target = $("#shuffle-material-summary");
  if (!target) return;
  const selected = new Set(selectedShuffleMaterialIds());
  const labels = state.materials
    .filter((material) => selected.has(String(material.id)))
    .map((material) => materialDisplayId(material));
  target.textContent = labels.length ? labels.join(", ") : "No fibres selected";
}

function orientationDisplay(value) {
  return `${String(value).replace("+-", "±")}°`;
}

async function runShuffleGenerator() {
  const total = Math.max(0, Number($("#shuffle-layer-count")?.value || 0));
  const zeroCount = Math.max(0, Number($("#shuffle-zero-count")?.value || 0));
  const maxVariants = Math.max(1, Number($("#shuffle-max")?.value || 500));
  const fixLayerTwo = Boolean($("#shuffle-fix-layer-two")?.checked);
  const layerOneAlwaysRc = Boolean($("#shuffle-layer-one-rc")?.checked);
  const materialIds = selectedShuffleMaterialIds();
  const coreKey = $("#shuffle-core")?.value || state.coreMaterials[0]?.key;
  const orientations = $$(".shuffle-orientation:checked").map((input) => input.value);
  const nonZeroOrientations = orientations.filter((angle) => angle !== "0");
  const feedback = $("#shuffle-feedback");

  if (!total || !materialIds.length) {
    feedback.textContent = "Choose at least one fibre material and at least one layer.";
    state.shuffleResults = [];
    renderShuffleResults();
    return;
  }
  if (zeroCount > total) {
    feedback.textContent = "Number of 0° UD plies cannot exceed total layers.";
    state.shuffleResults = [];
    renderShuffleResults();
    return;
  }
  if (zeroCount > 0 && !orientations.includes("0")) {
    feedback.textContent = "Enable 0° in allowed orientations when 0° plies are requested.";
    state.shuffleResults = [];
    renderShuffleResults();
    return;
  }
  if (zeroCount < total && nonZeroOrientations.length === 0) {
    feedback.textContent = "Select at least one non-0° orientation for the remaining plies.";
    state.shuffleResults = [];
    renderShuffleResults();
    return;
  }
  if (fixLayerTwo && (total < 2 || zeroCount < 1)) {
    feedback.textContent = "Layer 2 can only be fixed when total layers >= 2 and at least one 0° ply is requested.";
    state.shuffleResults = [];
    renderShuffleResults();
    return;
  }

  feedback.textContent = "Calculating laminate theory for generated variants...";
  try {
    const result = await api("/api/precalculate/shuffle", {
      method: "POST",
      body: JSON.stringify({
        total_layers: total,
        zero_plies: zeroCount,
        max_variants: maxVariants,
        fix_layer_two: fixLayerTwo,
        layer_one_always_rc: layerOneAlwaysRc,
        material_ids: materialIds,
        core: coreByKey(coreKey),
        orientations,
        specimen_width_mm: $("#pre-width")?.value || calculatorDimensionsForTestType($("#pre-test-type")?.value).width,
        specimen_length_mm: $("#pre-length")?.value || calculatorDimensionsForTestType($("#pre-test-type")?.value).length,
      }),
    });
    state.shuffleResults = result.variants || [];
    feedback.textContent = result.truncated
      ? `Showing first ${state.shuffleResults.length} variants. Increase the cap if needed.`
      : `${state.shuffleResults.length} variants generated with laminate theory.`;
    renderShuffleResults();
  } catch (error) {
    state.shuffleResults = [];
    feedback.textContent = error.message;
    renderShuffleResults();
  }
}

function sortedShuffleResults() {
  const { key, dir } = state.shuffleSort || {};
  const sign = dir === "asc" ? 1 : -1;
  let source = state.shuffleZeroUnder50
    ? (state.shuffleResults || []).filter((variant) => Number(variant.zero_percent) < 0.5)
    : (state.shuffleResults || []);
  if (state.shuffleEiPass) {
    source = source.filter((variant) => Number(shuffleEiCs(variant)) > 1);
  }
  return [...source].sort((a, b) => {
    const left = key === "ei_cs" ? shuffleEiCs(a) : a?.[key];
    const right = key === "ei_cs" ? shuffleEiCs(b) : b?.[key];
    const leftNumber = Number(left);
    const rightNumber = Number(right);
    if (Number.isFinite(leftNumber) || Number.isFinite(rightNumber)) {
      if (!Number.isFinite(leftNumber)) return 1;
      if (!Number.isFinite(rightNumber)) return -1;
      return (leftNumber - rightNumber) * sign;
    }
    return String(left || "").localeCompare(String(right || "")) * sign;
  });
}

function shuffleSortButton(label, key) {
  const sorted = state.shuffleSort?.key === key;
  return `<th class="${sorted ? "is-sorted" : ""}">
    <div class="header-stack">
      <button class="sort-button ${sorted ? "is-sorted" : ""}" data-action="sort-shuffle" data-key="${key}" type="button">${escapeHtml(label)}</button>
    </div>
  </th>`;
}

function shuffleFilteredSortButton(label, key, filterAction, filterLabel, active) {
  const sorted = state.shuffleSort?.key === key;
  return `<th class="metric-th ${sorted ? "is-sorted" : ""}">
    <div class="cs-header ${sorted ? "is-sorted" : ""}">
      <button class="sort-button ${sorted ? "is-sorted" : ""}" data-action="sort-shuffle" data-key="${key}" type="button">${escapeHtml(label)}</button>
      <button class="mini-filter ${active ? "is-active" : ""}" data-action="${filterAction}" aria-pressed="${active ? "true" : "false"}" type="button">${filterLabel}</button>
    </div>
  </th>`;
}

function shuffleEiCs(variant) {
  const panel = $("#shuffle-panel-select")?.value || activeCarEiPanels()[0];
  const target = PANEL_EI_TARGETS[panelAbbreviation(panel)];
  if (!target) return null;
  const theory = variant?.laminate_theory || {};
  const equivalent = theory.skin_equivalent_properties || theory.equivalent_properties || {};
  const eGpa = Number(equivalent.e11_gpa);
  const core = Number(variant?.core_thickness_mm);
  const skin = Number(variant?.top_skin_thickness_mm);
  const height = activePanelHeight(panel);
  if (![eGpa, core, skin, height].every(Number.isFinite) || skin <= 0 || height <= 0) return null;
  const ei = eGpa * 10 ** 9 * (secondMomentPanel(core, skin, height) / 10 ** 12);
  return ei / target;
}

function renderShuffleResults() {
  const target = $("#shuffle-results");
  if (!target) return;
  const rows = sortedShuffleResults()
    .map((variant, index) => {
      const cs = shuffleEiCs(variant);
      const csClass = Number.isFinite(cs) ? (cs >= 1 ? "good" : "bad") : "";
      return `
        <tr>
          <td>${index + 1}</td>
          <td class="sequence-cell">${escapeHtml(variant.orientation_laminate_sequence || variant.laminate_sequence || "-")}</td>
          <td>${escapeHtml(variant.cf_sequence || "-")}</td>
          <td>${formatNumber(variant.total_weight_g, 2)}</td>
          <td>${formatNumber(variant.total_thickness_mm, 3)}</td>
          <td>${formatPercent(variant.zero_percent, 1)}</td>
          <td>${formatNumber(variant.elastic_gradient_theory, 3)}</td>
          <td><span class="metric-value ${csClass}">${Number.isFinite(cs) ? formatNumber(cs, 3) : "N/A"}</span></td>
        </tr>`;
    })
    .join("");
  target.innerHTML = `
    <table class="tight-table shuffle-table">
      <thead><tr><th>#</th>${shuffleSortButton("Laminate Sequence", "orientation_laminate_sequence")}${shuffleSortButton("CF Sequence", "cf_sequence")}${shuffleSortButton("Weight [g]", "total_weight_g")}${shuffleSortButton("Thickness [mm]", "total_thickness_mm")}${shuffleFilteredSortButton("0° Fibers", "zero_percent", "toggle-shuffle-zero-filter", "&lt;50%", state.shuffleZeroUnder50)}${shuffleSortButton("Laminate Theory [N/mm]", "elastic_gradient_theory")}${shuffleFilteredSortButton("EI CS", "ei_cs", "toggle-shuffle-ei-filter", "&gt;1", state.shuffleEiPass)}</tr></thead>
      <tbody>${rows || `<tr><td colspan="8">Generate variants to see shuffle results.</td></tr>`}</tbody>
    </table>`;
}

function renderPreDatabaseVisibility() {
  renderPreSections();
}

function renderPreSections() {
  $$("[data-pre-section]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.preSection === state.preSection);
  });
  ["calculator", "shuffle", "databases"].forEach((section) => {
    const element = $(`#pre-${section}-section`);
    if (!element) return;
    element.classList.toggle("hidden", section !== state.preSection);
    element.classList.toggle("is-active", section === state.preSection);
  });
}

function skinLayerNumber(skin, index, layers) {
  return skin === "top" ? index + 1 : layers.length - index;
}

function renderSkinRows(kind, skin) {
  syncSymmetricLaminate(kind);
  const laminate = hydrateLaminate(kind);
  const layers = skin === "top" ? laminate.top_skin : laminate.bottom_skin;
  const locked = skin === "bottom" && isSymmetric(kind);
  if (!layers.length) return `<tr><td colspan="6" class="muted-cell">No ${skin} skin layers</td></tr>`;
  return layers
    .map((layer, index) => {
      const placement =
        skin === "top"
          ? index === 0
            ? "Outer surface"
            : index === layers.length - 1
              ? "Core side"
              : "Internal"
          : index === 0
            ? "Core side"
            : index === layers.length - 1
              ? "Outer surface"
              : "Internal";
      const materialOptions = state.materials
        .map((material) => `<option value="${material.id}" ${String(material.id) === String(layer.material_id) ? "selected" : ""}>${escapeHtml(material.name)}</option>`)
        .join("");
      const materialSelectOptions = `<option value="">Select fiber</option>${materialOptions}`;
      const orientations = orientationChoices(layer.material_id)
        .map((orientation) => `<option value="${orientation}" ${orientation === layer.orientation ? "selected" : ""}>${orientation}</option>`)
        .join("");
      const orientationSelectOptions = `<option value="">Select orientation</option>${orientations}`;
      const materialDisabled = locked ? "disabled" : "";
      const orientationDisabled = layer.material_id && !locked ? "" : "disabled";
      const removeButton = locked
        ? `<span class="pill blue">Mirrored</span>`
        : `<button class="icon-button" data-action="remove-skin-layer" data-kind="${kind}" data-skin="${skin}" data-index="${index}" title="Remove layer">x</button>`;
      return `
        <tr>
          <td class="layer-number">${skinLayerNumber(skin, index, layers)}</td>
          <td>${placement}</td>
          <td><select data-layer-kind="${kind}" data-skin="${skin}" data-index="${index}" data-field="material_id" ${materialDisabled}>${materialSelectOptions}</select></td>
          <td><select data-layer-kind="${kind}" data-skin="${skin}" data-index="${index}" data-field="orientation" ${orientationDisabled}>${orientationSelectOptions}</select></td>
          <td>${escapeHtml(materialById(layer.material_id)?.fiber_type || "")}</td>
          <td>${removeButton}</td>
        </tr>`;
    })
    .join("");
}

function renderLaminateView(kind) {
  const target = $(`#${kind}-laminate-view`);
  syncSymmetricLaminate(kind);
  const laminate = hydrateLaminate(kind);
  const core = coreByKey(laminate.core.key);
  target.innerHTML = `
    <div class="laminate-stack">
      <div class="stack-band stack-top">Top Skin</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Placement</th><th>Material</th><th>Orientation</th><th>Type</th><th></th></tr></thead>
          <tbody>${renderSkinRows(kind, "top")}</tbody>
        </table>
      </div>
      <div class="core-band">
        <span>CORE</span>
        <select id="${kind}-core" data-core-select="${kind}"></select>
        <strong>${formatNumber(core?.thickness_mm, 2)} mm</strong>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Placement</th><th>Material</th><th>Orientation</th><th>Type</th><th></th></tr></thead>
          <tbody>${renderSkinRows(kind, "bottom")}</tbody>
        </table>
      </div>
      <div class="stack-band stack-bottom">Bottom Skin</div>
    </div>`;
  renderCoreOptions(kind);
  $$(`[data-action="toggle-symmetric"][data-kind="${kind}"]`).forEach((button) => {
    button.classList.toggle("is-active", isSymmetric(kind));
  });
  $$(`[data-action="add-skin-layer"][data-kind="${kind}"][data-skin="bottom"]`).forEach((button) => {
    button.disabled = isSymmetric(kind);
    button.classList.toggle("is-disabled", isSymmetric(kind));
  });
  updateLaminateSequenceDisplays(kind);
}

function updateLaminateSequenceDisplays(kind) {
  const sequence = laminateSequence(laminateFor(kind));
  if (kind === "post" && $("#post-laminate-summary")) {
    $("#post-laminate-summary").innerHTML = renderSequenceBlock(sequence);
  }
  if (kind === "pre" && !state.preCalculation && $("#pre-kpis")) {
    renderPreResults(null);
  }
}

function activeCarEiPanels() {
  const car = selectedCar();
  const source = car?.panels?.length ? car.panels.map((panel) => panelAbbreviation(panel.name, panel.code)) : PANEL_CODES;
  return Array.from(new Set(source)).filter(Boolean);
}

function theoreticalCsEi(result, panel) {
  const code = panelAbbreviation(panel);
  const target = PANEL_EI_TARGETS[code];
  if (!result || !target) return null;
  const theory = result.laminate_theory || {};
  const equivalent = theory.skin_equivalent_properties || theory.equivalent_properties || {};
  const eGpa = Number(equivalent.e11_gpa);
  const core = Number(result.core_thickness_mm);
  const skin = Number(result.top_skin_thickness_mm || result.bottom_skin_thickness_mm);
  const height = activePanelHeight(code);
  if (![eGpa, core, skin, height].every(Number.isFinite) || skin <= 0 || height <= 0) return null;
  const panelSecondMomentM4 = secondMomentPanel(core, skin, height) / 10 ** 12;
  const ei = eGpa * 10 ** 9 * panelSecondMomentM4;
  return { ei, cs: ei / target };
}

function renderPreCsEiTable(result) {
  const panels = activeCarEiPanels().filter((panel) => {
    const code = panelAbbreviation(panel);
    return code !== "FBH" && code !== "Dashboard";
  });
  const rows = panels
    .map((panel) => {
      const code = panelAbbreviation(panel);
      const values = theoreticalCsEi(result, code);
      if (!PANEL_EI_TARGETS[code]) {
        return `<tr><td>${escapeHtml(code)}</td><td>N/A</td><td>N/A</td></tr>`;
      }
      const cs = values?.cs;
      const status = Number.isFinite(cs) ? (cs >= 1 ? "good" : "bad") : "";
      return `<tr>
        <td>${escapeHtml(code)}</td>
        <td>${Number.isFinite(values?.ei) ? formatNumber(values.ei, 3) : "N/A"}</td>
        <td><span class="metric-value ${status}">${Number.isFinite(cs) ? formatNumber(cs, 3) : "N/A"}</span></td>
      </tr>`;
    })
    .join("");
  return `<section class="cs-ei-block">
    <h3>CS EI by Active Car</h3>
    <table class="tight-table">
      <thead><tr><th>Panel</th><th>EI</th><th>CS EI</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="3">Select an active car to calculate CS EI</td></tr>`}</tbody>
    </table>
  </section>`;
}

function renderPreResults(result) {
  const sequence = laminateSequence(laminateFor("pre"));
  if (!result) {
    $("#pre-kpis").innerHTML = renderSequenceBlock(sequence);
    return;
  }
  $("#pre-kpis").innerHTML = `
    <div class="kpi sequence-kpi">${renderSequenceBlock(sequence)}</div>
    <div class="kpi"><span>Total weight</span><strong>${formatNumber(result.total_weight_g, 2)} g</strong></div>
    <div class="kpi"><span>Total thickness</span><strong>${formatNumber(result.total_thickness_mm, 3)} mm</strong></div>
    <div class="kpi"><span>Top skin thickness</span><strong>${formatNumber(result.top_skin_thickness_mm, 3)} mm</strong></div>
    <div class="kpi"><span>Bottom skin thickness</span><strong>${formatNumber(result.bottom_skin_thickness_mm, 3)} mm</strong></div>
    <div class="kpi"><span>Core thickness</span><strong>${formatNumber(result.core_thickness_mm, 3)} mm</strong></div>
    <div class="kpi"><span>0 deg fibers</span><strong>${formatPercent(result.zero_percent, 2)}</strong></div>
    <div class="wide-kpi">${renderElasticGradientHero(result.laminate_theory)}</div>
    <div class="wide-kpi">${renderPreCsEiTable(result)}</div>
    <div class="wide-kpi">${renderLaminateTheory(result.laminate_theory, laminateFor("pre"))}</div>`;
}

async function calculatePre() {
  const laminate = buildLaminate("pre");
  if (laminateSequence(laminate) === "Incomplete laminate") {
    state.preCalculation = null;
    renderPreResults(null);
    return;
  }
  const dimensions = syncPreDimensionsFromTestType();
  state.preCalculation = await api("/api/precalculate", {
    method: "POST",
    body: JSON.stringify({
      laminate,
      specimen_width_mm: dimensions.width,
      specimen_length_mm: dimensions.length,
      test_type: $("#pre-test-type").value,
    }),
  });
  renderPreResults(state.preCalculation);
}

function statusClass(value, mode = "min") {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  if (mode === "deflection") {
    if (n <= 1) return "good";
    if (n <= 1.66667) return "yellow";
    return "warn";
  }
  return n >= 1 ? "good" : "warn";
}

function statusPill(value, mode = "min") {
  const cls = statusClass(value, mode);
  return `<span class="pill ${cls}">${formatNumber(value, 3)}</span>`;
}

function panelResultsTable(panelResults = {}, colored = false) {
  const adjustedResults = adjustedPanelResults(panelResults);
  const rows = Object.entries(adjustedResults)
    .map(([panel, values]) => `
      <tr>
        <td><strong>${escapeHtml(panelAbbreviation(panel))}</strong></td>
        <td>${formatNumber(values.ei_gpa_m4, 3)}</td>
        <td>${statusPill(values.cs_ei)}</td>
        <td>${colored ? statusPill(values.cs_yield) : formatNumber(values.cs_yield, 3)}</td>
        <td>${colored ? statusPill(values.cs_uts) : formatNumber(values.cs_uts, 3)}</td>
        <td>${colored ? statusPill(values.cs_max_load_midspan) : formatNumber(values.cs_max_load_midspan, 3)}</td>
        <td>${colored ? statusPill(values.cs_max_deflection, "deflection") : formatNumber(values.cs_max_deflection, 3)}</td>
        <td>${colored ? statusPill(values.cs_energy) : formatNumber(values.cs_energy, 3)}</td>
        <td>${formatNumber(values.shear_stress_mpa, 3)}</td>
        <td>${statusPill(values.cs_perimeter_shear)}</td>
      </tr>`)
    .join("");
  return `
    <table>
      <thead><tr><th>Panel</th><th>EI</th><th>CS EI</th><th>CS Yield</th><th>CS UTS</th><th>CS Load</th><th>CS Defl.</th><th>CS Energy</th><th>Shear MPa</th><th>CS Perim.</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="10">No metrics</td></tr>`}</tbody>
    </table>`;
}

function processedProbeHeader(specimen) {
  if (!specimen) return "";
  return `<section class="surface processed-probe-header">
    <div>
      <span>Test</span>
      <strong>${escapeHtml(specimen.test_type || "-")}</strong>
    </div>
    <div>
      <span>Laminate</span>
      <strong>${escapeHtml(specimenLaminateSequence(specimen))}</strong>
    </div>
  </section>`;
}

function renderPostWorkflow() {
  const inputView = $("#post-input-view");
  const resultsView = $("#post-results-view");
  if (!inputView || !resultsView) return;
  const showingResults = state.postView === "results" && Boolean(state.processResult);
  inputView.classList.toggle("hidden", showingResults);
  resultsView.classList.toggle("hidden", !showingResults);
  const header = $("#processed-probe-header");
  if (header) header.innerHTML = showingResults ? processedProbeHeader(state.processResult) : "";
}

function renderProcessResult(specimen) {
  state.processResult = specimen;
  state.postView = "results";
  const metricsSection = $("#post-computed-metrics-section");
  if (metricsSection) metricsSection.classList.toggle("hidden", isSpecialTestType(specimen.test_type));
  $("#process-results").innerHTML = isSpecialTestType(specimen.test_type) ? "" : panelResultsTable(specimen.computed?.panel_results, true);
  renderPostWorkflow();
  requestAnimationFrame(() => drawGraph($("#process-chart"), specimen));
}

async function loadMaterials() {
  state.materials = await api("/api/materials");
  state.coreMaterials = await api("/api/core-materials");
  if (!state.preLaminate) state.preLaminate = defaultLaminate();
  if (!state.postLaminate) state.postLaminate = defaultLaminate();
  renderMaterialList();
  renderCoreList();
  renderPreSections();
  renderShuffleControls();
  renderLaminateView("pre");
  renderLaminateView("post");
}

function specimenSearchBlob(specimen) {
  return [
    specimen.id,
    specimen.test_type,
    specimen.core_type,
    specimen.laminate_sequence,
    carbonFiberNamesForSpecimen(specimen),
    specimen.real_weight_g,
    specimen.core_material,
    ...VISIBLE_EI_PANELS.map((panel) => csEiValue(specimen, panel)),
    energyAbsorbedJ(specimen),
    specimen.perimeter_shear_cs,
  ]
    .filter((value) => value !== undefined && value !== null)
    .join(" ")
    .toLowerCase();
}

function csEiValues(specimen) {
  if (isSpecialTestType(specimen?.test_type)) return [];
  return VISIBLE_EI_PANELS.map((panel) => csEiValue(specimen, panel)).filter((value) => value !== null);
}

function getSortValue(specimen, key) {
  if (isSpecialTestType(specimen?.test_type) && (key.startsWith("ei_") || key.startsWith("perimeter_") || key === "cs_ei_all")) return -Infinity;
  if (key.startsWith("ei_")) return csEiValue(specimen, key.slice(3)) ?? -Infinity;
  if (key.startsWith("perimeter_")) return specimen.perimeter_shear_by_panel?.[key.slice("perimeter_".length)] ?? -Infinity;
  if (key === "energyAbsorbedJ" || key === "energy_absorbed_j") return energyAbsorbedJ(specimen) ?? -Infinity;
  if (key === "carbon_fibers") return carbonFiberNamesForSpecimen(specimen);
  if (key === "cs_ei_all") {
    const values = csEiValues(specimen);
    return values.length ? Math.min(...values) : -Infinity;
  }
  if (key === "laminate_sequence") return specimenLaminateSequence(specimen);
  return specimen[key] ?? "";
}

function sortedFilteredSpecimens() {
  const filter = state.dbFilter.trim().toLowerCase();
  let rows = filter ? state.specimens.filter((specimen) => specimenSearchBlob(specimen).includes(filter)) : [...state.specimens];
  if (state.dbTestFilter !== "all") {
    rows = rows.filter((specimen) => String(specimen.test_type || "").toUpperCase().includes(state.dbTestFilter.toUpperCase()));
  }
  const activePassPanels = VISIBLE_EI_PANELS.filter((panel) => state.dbEiPassPanels[panel]);
  activePassPanels.forEach((panel) => {
    rows = rows.filter((specimen) => !isSpecialTestType(specimen.test_type) && Number(csEiValue(specimen, panel)) > 1);
  });
  const activePerimeterPanels = PERIMETER_SHEAR_CODES.filter((panel) => state.dbPerimeterPassPanels[panel]);
  activePerimeterPanels.forEach((panel) => {
    rows = rows.filter((specimen) => !isSpecialTestType(specimen.test_type) && Number(specimen.perimeter_shear_by_panel?.[panel]) > 1);
  });
  if (state.dbEnergyPass) {
    rows = rows.filter((specimen) => Number(energyAbsorbedJ(specimen)) > ENERGY_ABSORBED_THRESHOLD_J);
  }
  const { key, dir } = state.dbSort;
  rows.sort((a, b) => {
    const av = getSortValue(a, key);
    const bv = getSortValue(b, key);
    const an = Number(av);
    const bn = Number(bv);
    const result = Number.isFinite(an) && Number.isFinite(bn) ? an - bn : String(av).localeCompare(String(bv));
    return dir === "asc" ? result : -result;
  });
  return rows;
}

async function loadSpecimens() {
  state.specimens = await api("/api/specimens");
  await loadCarProbeMetrics().catch(() => {});
  renderTestFilterOptions();
  renderSpecimenTable();
  renderMonocoqueView();
}

function normalizePanelName(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function panelAbbreviation(nameOrCode, code = "") {
  const directCode = String(code || nameOrCode || "");
  if (PANEL_LABELS[directCode]) return PANEL_LABELS[directCode];
  const normalized = normalizePanelName(nameOrCode);
  return PANEL_NAME_ABBREVIATIONS[normalized] || String(nameOrCode || code || "-");
}

function panelKey(panel) {
  return String(panel?.id || panel?.code || panel?.name || "");
}

async function loadCarProbeMetrics(carId = state.selectedCarId) {
  if (!carId) return {};
  const rows = await api(`/api/cars/${encodeURIComponent(carId)}/probe-metrics`);
  state.carProbeMetrics[String(carId)] = Object.fromEntries(rows.map((row) => [String(row.specimen_id), row]));
  return state.carProbeMetrics[String(carId)];
}

function carProbeMetricForSpecimen(specimen) {
  return state.carProbeMetrics[String(state.selectedCarId)]?.[String(specimen?.id)] || null;
}

function activeCarPanelMetricsForSpecimen(specimen) {
  const car = selectedCar();
  if (!car) {
    return {
      panelResults: null,
      message: "No active car selected. Please select a car and recalculate SES.",
    };
  }
  const row = carProbeMetricForSpecimen(specimen);
  if (!row) {
    return {
      panelResults: null,
      message: "No panel metrics available for the active car. Please recalculate SES.",
    };
  }
  if (row.status && row.status !== "ok") {
    return {
      panelResults: null,
      message: `Panel metrics for the active car failed: ${row.error || "Unknown error"}. Please recalculate SES.`,
    };
  }
  const panelResults = row.metrics?.panel_results || {};
  if (!Object.keys(panelResults).length) {
    return {
      panelResults: null,
      message: "No panel metrics available for the active car. Please recalculate SES.",
    };
  }
  return { panelResults, message: "" };
}

async function loadCars() {
  state.cars = await api("/api/cars");
  if ((!state.selectedCarId || !state.cars.some((car) => String(car.id) === String(state.selectedCarId))) && state.cars.length) {
    state.selectedCarId = state.cars[0].id;
  }
  await loadCarProbeMetrics().catch(() => {});
  renderCarSelectors();
  renderCarList();
  renderMonocoqueView();
  renderSpecimenTable();
  renderShufflePanelOptions();
  renderShuffleResults();
  if (state.preCalculation) renderPreResults(state.preCalculation);
  if (state.selectedSpecimen && !$("#specimen-modal")?.classList.contains("hidden")) {
    renderSpecimenDetail(state.selectedSpecimen);
  }
}

async function loadMonocoqueCalculations() {
  state.monocoqueCalcs = await api("/api/monocoque-weights");
  renderMonocoqueSavedOptions();
}

function selectedCar() {
  return state.cars.find((car) => String(car.id) === String(state.selectedCarId)) || state.cars[0];
}

function carById(id) {
  return state.cars.find((car) => String(car.id) === String(id));
}

function carOptionsHtml(selectedId = state.selectedCarId) {
  return state.cars.map((car) => `<option value="${car.id}" ${String(car.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(car.name)}</option>`).join("");
}

function renderCarSelectors() {
  ["monocoque-car-select", "process-car-select", "database-car-select", "pre-car-select", "shuffle-car-select"].forEach((id) => {
    const select = $(`#${id}`);
    if (select) select.innerHTML = carOptionsHtml();
  });
  renderShufflePanelOptions();
}

function renderShufflePanelOptions() {
  const select = $("#shuffle-panel-select");
  if (!select) return;
  const current = select.value;
  const panels = activeCarEiPanels().filter((panel) => PANEL_EI_TARGETS[panelAbbreviation(panel)]);
  select.innerHTML = panels
    .map((panel) => `<option value="${escapeHtml(panelAbbreviation(panel))}" ${String(panelAbbreviation(panel)) === String(current) ? "selected" : ""}>${escapeHtml(panelAbbreviation(panel))}</option>`)
    .join("");
  if (!select.value && panels[0]) select.value = panelAbbreviation(panels[0]);
}

function activePanelHeight(panel) {
  const code = panelAbbreviation(panel);
  const carPanel = (selectedCar()?.panels || []).find((item) => panelAbbreviation(item.name, item.code) === code);
  const height = Number(carPanel?.height_mm);
  return Number.isFinite(height) && height > 0 ? height : DEFAULT_PANEL_HEIGHTS_MM[code];
}

function secondMomentPanel(coreThicknessMm, skinThicknessMm, panelHeightMm) {
  const x5 = panelHeightMm;
  const x6 = skinThicknessMm;
  const y5 = panelHeightMm;
  const y6 = skinThicknessMm;
  const x8 = x5 * x6;
  const x9 = y5 * y6;
  const x10 = x6 / 2;
  const x11 = (coreThicknessMm + 2 * skinThicknessMm) - 0.5 * skinThicknessMm;
  const x12 = (x8 * x10 + x9 * x11) / (x8 + x9);
  const z8 = (x5 * x6 ** 3) / 12;
  const z9 = (y5 * y6 ** 3) / 12;
  return z8 + (x8 * (x12 - x10) ** 2) + z9 + (x9 * (x12 - x11) ** 2);
}

function adjustedPanelValues(panel, values = {}) {
  const height = activePanelHeight(panel);
  const core = Number(values.core_thickness_mm);
  const skin = Number(values.skin_thickness_mm);
  const sigma = Number(values.sigma_uts_pa);
  const eGpa = Number(values.e_gpa);
  if (!Number.isFinite(height) || !Number.isFinite(core) || !Number.isFinite(skin)) return values;
  const adjusted = { ...values, panel_height_mm: height };
  const panelSecondMomentMm4 = secondMomentPanel(core, skin, height);
  const panelSecondMomentM4 = panelSecondMomentMm4 / 10 ** 12;
  adjusted.panel_second_moment_mm4 = panelSecondMomentMm4;
  adjusted.panel_second_moment_m4 = panelSecondMomentM4;
  if (Number.isFinite(eGpa)) {
    adjusted.ei_gpa_m4 = eGpa * 10 ** 9 * panelSecondMomentM4;
    const target = Number(values.ei_target_gpa_m4);
    adjusted.cs_ei = Number.isFinite(target) && target !== 0 ? adjusted.ei_gpa_m4 / target : values.cs_ei;
  }
  if (Number.isFinite(sigma)) {
    const skipStrength = ["SISv", "SISh"].includes(panelAbbreviation(panel));
    const effectiveSkinAreaMm2 = ((core + 2 * skin) - core) * height;
    adjusted.yield_probe_n = effectiveSkinAreaMm2 * sigma / 1_000_000;
    adjusted.uts_probe_n = adjusted.yield_probe_n;
    adjusted.cs_yield = skipStrength ? values.cs_yield : adjusted.yield_probe_n / Number(values.yield_target_n);
    adjusted.cs_uts = skipStrength ? values.cs_uts : adjusted.uts_probe_n / Number(values.uts_target_n);
    adjusted.max_load_midspan_probe_n = 4 * sigma * panelSecondMomentM4 / (0.001 * 0.5 * (core + 2 * skin));
    adjusted.cs_max_load_midspan = skipStrength ? values.cs_max_load_midspan : adjusted.max_load_midspan_probe_n / Number(values.max_load_target_n);
    adjusted.max_deflection_probe_m = Number(values.max_load_target_n) / (48 * adjusted.ei_gpa_m4);
    adjusted.cs_max_deflection = skipStrength ? values.cs_max_deflection : adjusted.max_deflection_probe_m / Number(values.max_deflection_target_m);
    adjusted.energy_absorbed_probe_j = 0.5 * adjusted.max_load_midspan_probe_n * (adjusted.max_load_midspan_probe_n / (48 * adjusted.ei_gpa_m4));
    adjusted.cs_energy = skipStrength ? values.cs_energy : adjusted.energy_absorbed_probe_j / Number(values.energy_target_j);
  }
  return adjusted;
}

function adjustedPanelResults(panelResults = {}) {
  return Object.fromEntries(Object.entries(panelResults || {}).map(([panel, values]) => [panel, adjustedPanelValues(panel, values)]));
}

function panelResultForSpecimen(specimen, panel) {
  const carMetrics = carProbeMetricForSpecimen(specimen)?.metrics || {};
  const source = carMetrics.panel_results?.[panel] || specimen?.panel_results?.[panel] || specimen?.computed?.panel_results?.[panel];
  return source ? adjustedPanelValues(panel, source) : null;
}

function csEiValue(specimen, panel) {
  const carMetrics = carProbeMetricForSpecimen(specimen)?.metrics || {};
  const adjusted = panelResultForSpecimen(specimen, panel);
  const value = adjusted?.cs_ei ?? carMetrics.cs_ei_by_panel?.[panel] ?? specimen?.cs_ei_by_panel?.[panel];
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function carbonFiberNamesForSpecimen(specimen) {
  const laminate = specimen?.laminate || {};
  const layers = [...(laminate.top_skin || []), ...(laminate.bottom_skin || [])];
  const names = layers
    .map((layer) => materialById(layer.material_id)?.name || layer.material_name || "")
    .map((name) => String(name).trim())
    .filter(Boolean);
  const unique = Array.from(new Set(names));
  return unique.length ? unique.join(", ") : "N/A";
}

function monocoquePayload() {
  const car = selectedCar();
  return {
    id: state.selectedMonocoqueId,
    name: $("#monocoque-name")?.value || "Monocoque weight",
    car_id: car?.id,
    assignments: { ...state.monocoqueAssignments },
    front_hoop_volume_m3: Number($("#front-hoop-volume")?.value || 0),
    front_hoop_density_kg_m3: Number($("#front-hoop-density")?.value || 0),
    hardpoints_weight_g: Number($("#hardpoints-weight")?.value || 0) * 1000,
  };
}

function specimenOptions(selectedId = "") {
  return [`<option value="">Select probe</option>`, ...state.specimens.map((specimen) => (
    `<option value="${escapeHtml(specimen.id)}" ${String(specimen.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(specimen.id)}</option>`
  ))].join("");
}

function renderMonocoqueView() {
  if (!$("#monocoque")) return;
  const car = selectedCar();
  const databaseMode = state.monocoqueSection === "databases";
  renderCarSelectors();
  $("#monocoque-saved-panel")?.classList.toggle("hidden", !databaseMode && !state.monocoqueSavedOpen);
  $("#toggle-monocoque-saved").textContent = state.monocoqueSavedOpen ? "Hide Saved Calculations" : "Open Saved Calculations";
  $("#toggle-monocoque-saved")?.classList.toggle("is-active", state.monocoqueSavedOpen);
  $("#monocoque-saved-edit-mode").checked = state.monocoqueSavedEditMode;
  renderMonocoqueSavedOptions();
  $("#save-monocoque").textContent = state.selectedMonocoqueId && state.monocoqueSavedEditMode ? "Update Saved Calculation" : "Save Calculation";
  $("#car-database-panel")?.classList.toggle("hidden", !databaseMode && !state.carDatabaseOpen);
  $("#toggle-car-database").textContent = state.carDatabaseOpen ? "Hide Car Database" : "Open Car Database";
  $("#toggle-car-database")?.classList.toggle("is-active", state.carDatabaseOpen);
  const target = $("#monocoque-panel-assignments");
  if (target) {
    const resultByPanel = new Map((state.monocoqueResult?.panels || []).map((panel) => [String(panel.panel_id), panel]));
    const rows = (car?.panels || []).map((panel) => {
      const panelId = panelKey(panel);
      const resultPanel = resultByPanel.get(panelId) || {};
      return `
        <tr>
          <td><strong>${escapeHtml(panelAbbreviation(panel.name, panel.code))}</strong></td>
          <td>
            <select data-monocoque-panel="${escapeHtml(panelId)}">${specimenOptions(state.monocoqueAssignments[panelId])}</select>
          </td>
          <td>${kgFromGrams(resultPanel.real_weight_g, 3)}</td>
          <td>${kgFromGrams(resultPanel.theoretical_weight_g, 3)}</td>
        </tr>`;
    }).join("");
    target.innerHTML = `
      <table>
        <thead><tr><th>Panel name</th><th>Probe ID</th><th>Real Weight [kg]</th><th>Theoretical Weight [kg]</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4">Create or select a car to define panels</td></tr>`}</tbody>
      </table>`;
  }
  renderMonocoqueResult(state.monocoqueResult);
  renderMonocoqueSections();
}

function renderMonocoqueSections() {
  const root = $("#monocoque");
  if (!root) return;
  root.classList.toggle("monocoque-databases-mode", state.monocoqueSection === "databases");
  root.classList.toggle("monocoque-weight-mode", state.monocoqueSection !== "databases");
  $$("[data-monocoque-section]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.monocoqueSection === state.monocoqueSection);
  });
}

function renderMonocoqueSavedEditor(record) {
  if (!record) return "";
  const carId = record.car_id || record.car_snapshot?.id || state.selectedCarId;
  const car = carById(carId) || record.car_snapshot || {};
  const assignments = record.assignments || record.computed?.assignments || {};
  const panelRows = (car.panels || [])
    .map((panel) => {
      const key = panelKey(panel);
      return `<tr>
        <td>${escapeHtml(panelAbbreviation(panel.name, panel.code))}</td>
        <td><select data-edit-monocoque-assignment="${escapeHtml(key)}">${specimenOptions(assignments[key])}</select></td>
      </tr>`;
    })
    .join("");
  return `<section class="database-editor-panel">
    <div class="section-actions">
      <h3>Edit Saved Calculation: ${escapeHtml(record.name || "")}</h3>
      <button class="button ghost small" data-action="close-monocoque-editor" type="button">Close</button>
    </div>
    <div class="form-grid">
      <label>Name<input data-edit-monocoque-record="${record.id}" data-field="name" value="${escapeHtml(record.name || "")}"></label>
      <label>Car
        <select data-edit-monocoque-record="${record.id}" data-field="car_id">${carOptionsHtml(carId)}</select>
      </label>
      <label>Front Hoop volume [m3]<input data-edit-monocoque-record="${record.id}" data-field="front_hoop_volume_m3" type="number" step="0.000001" value="${record.front_hoop_volume_m3 ?? record.computed?.front_hoop_volume_m3 ?? 0}"></label>
      <label>FH material density [kg/m3]<input data-edit-monocoque-record="${record.id}" data-field="front_hoop_density_kg_m3" type="number" step="1" value="${record.front_hoop_density_kg_m3 ?? record.computed?.front_hoop_density_kg_m3 ?? 0}"></label>
      <label>Hardpoints weight [kg]<input data-edit-monocoque-record="${record.id}" data-field="hardpoints_weight_kg" type="number" step="0.001" value="${Number(record.hardpoints_weight_g || record.computed?.hardpoints_weight_g || 0) / 1000}"></label>
    </div>
    <div class="table-wrap">
      <table class="nested-table">
        <thead><tr><th>Panel</th><th>Probe ID</th></tr></thead>
        <tbody>${panelRows || `<tr><td colspan="2">No panels available for this car</td></tr>`}</tbody>
      </table>
    </div>
    <div class="button-row"><button class="button primary" data-action="save-monocoque-record" data-id="${record.id}" type="button">Save calculation</button></div>
  </section>`;
}

function renderMonocoqueSavedOptions() {
  const target = $("#monocoque-saved-list");
  if (!target) return;
  const rows = state.monocoqueCalcs.map((calc) => {
    const active = String(calc.id) === String(state.selectedMonocoqueId) ? " is-selected" : "";
    const actions = state.monocoqueSavedEditMode
      ? `<td class="row-actions"><button class="button small" data-action="edit-monocoque-record" data-id="${calc.id}">Edit</button><button class="button danger small" data-action="delete-monocoque" data-id="${calc.id}">Delete</button></td>`
      : "";
    return `
      <tr class="${active}" data-saved-monocoque-id="${calc.id}">
        <td>${escapeHtml(calc.name || "-")}</td>
        <td>${escapeHtml(calc.car_name || "-")}</td>
        <td>${formatNumber(Number(calc.total_real_monocoque_g) / 1000, 3)}</td>
        <td>${formatNumber(Number(calc.final_total_weight_g) / 1000, 3)}</td>
        <td>${escapeHtml(calc.updated_at || "-")}</td>
        ${actions}
      </tr>`;
  }).join("");
  const actionHeader = state.monocoqueSavedEditMode ? "<th>Actions</th>" : "";
  const colSpan = state.monocoqueSavedEditMode ? 6 : 5;
  const editor = state.monocoqueSavedEditMode ? renderMonocoqueSavedEditor(state.monocoqueSavedEditingRecord) : "";
  target.innerHTML = `
    <table>
      <thead><tr><th>Name</th><th>Car</th><th>Real [kg]</th><th>Final [kg]</th><th>Updated</th>${actionHeader}</tr></thead>
      <tbody>${rows || `<tr><td colspan="${colSpan}">No saved calculations</td></tr>`}</tbody>
    </table>
    ${editor}`;
  $("#monocoque-saved-edit-mode").checked = state.monocoqueSavedEditMode;
}

function renderMonocoqueResult(result) {
  const summary = $("#monocoque-summary");
  if (!summary) return;
  if (!result) {
    summary.innerHTML = `<div class="empty-state">Assign specimens to calculate monocoque weight</div>`;
    return;
  }
  const theoretical = Number(result.total_theoretical_monocoque_g);
  const real = Number(result.total_real_monocoque_g);
  const frontHoopG = Number(result.front_hoop_weight_g ?? Number(result.front_hoop_weight_kg || 0) * 1000);
  const hardpointsG = Number(result.hardpoints_weight_g || 0);
  const finalTheoretical = Number.isFinite(theoretical) ? theoretical + frontHoopG + hardpointsG : null;
  const finalReal = Number.isFinite(real) ? real + frontHoopG + hardpointsG : null;
  const delta = Number.isFinite(finalReal) && Number.isFinite(finalTheoretical) ? finalReal - finalTheoretical : null;
  const deltaClass = Number.isFinite(finalReal) && Number.isFinite(finalTheoretical) && finalTheoretical <= finalReal ? "good" : "warn";
  summary.innerHTML = `
    <div class="kpi"><span>Theoretical monocoque weight</span><strong>${kgFromGrams(result.total_theoretical_monocoque_g, 3)} kg</strong></div>
    <div class="kpi"><span>Real monocoque weight</span><strong>${kgFromGrams(result.total_real_monocoque_g, 3)} kg</strong></div>
    <div class="kpi"><span>Front hoop weight</span><strong>${formatNumber(result.front_hoop_weight_kg, 3)} kg</strong></div>
    <div class="kpi"><span>Hardpoints weight</span><strong>${kgFromGrams(result.hardpoints_weight_g, 3)} kg</strong></div>
    <div class="kpi sequence-kpi final-weight-kpi"><div class="sequence-block"><span>Total theoretical weight</span><strong>${kgFromGrams(finalTheoretical, 3)} kg</strong></div></div>
    <div class="kpi sequence-kpi final-weight-kpi"><div class="sequence-block"><span>Total real weight</span><strong>${kgFromGrams(finalReal, 3)} kg</strong></div></div>
    <div class="kpi weight-delta-kpi"><span>Weight delta</span><strong><span class="pill ${deltaClass}">${kgFromGrams(delta, 3)} kg</span></strong></div>`;
}

async function calculateMonocoque() {
  if (!selectedCar()) return;
  state.monocoqueResult = await api("/api/monocoque-weights/calculate", {
    method: "POST",
    body: JSON.stringify(monocoquePayload()),
  });
  renderMonocoqueView();
}

async function openMonocoqueCalculation(id) {
  if (!id) {
    state.selectedMonocoqueId = null;
    state.monocoqueAssignments = {};
    state.monocoqueResult = null;
    renderMonocoqueView();
    return;
  }
  const saved = await api(`/api/monocoque-weights/${id}`);
  state.selectedMonocoqueId = saved.id;
  state.selectedCarId = saved.car_id || saved.car_snapshot?.id;
  state.monocoqueAssignments = saved.assignments || {};
  $("#monocoque-name").value = saved.name || "Monocoque weight";
  $("#front-hoop-volume").value = saved.front_hoop_volume_m3 ?? saved.computed?.front_hoop_volume_m3 ?? ((saved.front_hoop_volume_mm3 || 0) / 1_000_000_000);
  $("#front-hoop-density").value = saved.front_hoop_density_kg_m3 ?? saved.computed?.front_hoop_density_kg_m3 ?? ((saved.front_hoop_density_kg_mm3 || 0) * 1_000_000_000);
  $("#hardpoints-weight").value = (saved.hardpoints_weight_g || 0) / 1000;
  state.monocoqueResult = saved.computed;
  renderMonocoqueView();
}

function resetMonocoqueWorkspace() {
  state.selectedMonocoqueId = null;
  state.monocoqueAssignments = {};
  state.monocoqueResult = null;
  $("#monocoque-name").value = "Monocoque weight";
  $("#front-hoop-volume").value = "0.000239266";
  $("#front-hoop-density").value = "7850";
  $("#hardpoints-weight").value = "0";
}

function renderCarEditor(car) {
  if (!car) return "";
  const panelRows = (car.panels || []).map((panel, index) => {
    const abbreviation = panelAbbreviation(panel.name, panel.code);
    const defaultHeight = DEFAULT_PANEL_HEIGHTS_MM[abbreviation] || 0;
    return `
      <tr>
        <td><input data-edit-car-panel="${car.id}" data-index="${index}" data-field="name" value="${escapeHtml(panel.name || abbreviation)}"></td>
        <td><input data-edit-car-panel="${car.id}" data-index="${index}" data-field="code" value="${escapeHtml(panel.code || abbreviation)}"></td>
        <td><input data-edit-car-panel="${car.id}" data-index="${index}" data-field="area_mm2" type="number" step="0.01" value="${panel.area_mm2 ?? 0}"></td>
        <td><input data-edit-car-panel="${car.id}" data-index="${index}" data-field="height_mm" type="number" step="0.01" value="${panel.height_mm ?? defaultHeight}"></td>
      </tr>`;
  }).join("");
  return `<section class="database-editor-panel">
    <div class="section-actions">
      <h3>Edit Car: ${escapeHtml(car.name || "")}</h3>
      <button class="button ghost small" data-action="close-car-editor" type="button">Close</button>
    </div>
    <div class="form-grid">
      <label>Car name<input data-edit-car="${car.id}" data-field="name" value="${escapeHtml(car.name || "")}"></label>
    </div>
    <div class="table-wrap">
      <table class="nested-table">
        <thead><tr><th>Panel</th><th>Code</th><th>Area [mm2]</th><th>Height [mm]</th></tr></thead>
        <tbody>${panelRows || `<tr><td colspan="4">No panels stored</td></tr>`}</tbody>
      </table>
    </div>
    <div class="button-row"><button class="button primary" data-action="save-car" data-id="${car.id}" type="button">Save car</button></div>
  </section>`;
}

function renderCarList() {
  const target = $("#car-list");
  if (!target) return;
  const rows = state.cars.map((car) => {
    const actions = state.carEditMode
      ? `<td class="row-actions"><button class="button small" data-action="edit-car" data-id="${car.id}">Edit</button><button class="button danger small" data-action="delete-car" data-id="${car.id}">Delete</button></td>`
      : "";
    return `<tr><td>${escapeHtml(car.name)}</td><td>${car.panels.length} panels</td>${actions}</tr>`;
  }).join("");
  const actionHeader = state.carEditMode ? "<th>Actions</th>" : "";
  const colSpan = state.carEditMode ? 3 : 2;
  const editor = state.carEditMode ? renderCarEditor(carById(state.carEditingId)) : "";
  target.innerHTML = `
    <table>
      <thead><tr><th>Car</th><th>Panels</th>${actionHeader}</tr></thead>
      <tbody>${rows || `<tr><td colspan="${colSpan}">No cars stored</td></tr>`}</tbody>
    </table>
    ${editor}`;
  $("#car-form")?.classList.toggle("hidden", !state.carAddOpen);
  $("#car-edit-mode").checked = state.carEditMode;
}

function collectCarPayload(id) {
  const car = state.cars.find((item) => String(item.id) === String(id));
  const payload = { panels: cloneLayers(car?.panels || []) };
  $$(`[data-edit-car="${id}"]`).forEach((input) => {
    payload[input.dataset.field] = input.value;
  });
  $$(`[data-edit-car-panel="${id}"]`).forEach((input) => {
    const index = Number(input.dataset.index);
    if (!payload.panels[index]) return;
    payload.panels[index][input.dataset.field] = input.type === "number" ? Number(input.value) : input.value;
  });
  return payload;
}

function collectMonocoqueSavedPayload(id) {
  const record = state.monocoqueSavedEditingRecord || {};
  const payload = {
    id: Number(id),
    assignments: {},
  };
  $$(`[data-edit-monocoque-record="${id}"]`).forEach((input) => {
    const field = input.dataset.field;
    if (field === "hardpoints_weight_kg") {
      payload.hardpoints_weight_g = Number(input.value || 0) * 1000;
    } else if (["front_hoop_volume_m3", "front_hoop_density_kg_m3"].includes(field)) {
      payload[field] = Number(input.value || 0);
    } else if (field === "car_id") {
      payload.car_id = Number(input.value || record.car_id || state.selectedCarId);
    } else {
      payload[field] = input.value;
    }
  });
  $$("[data-edit-monocoque-assignment]").forEach((select) => {
    payload.assignments[select.dataset.editMonocoqueAssignment] = select.value;
  });
  if (!payload.car_id) payload.car_id = Number(record.car_id || state.selectedCarId);
  if (!payload.name) payload.name = record.name || "Monocoque weight";
  if (payload.front_hoop_volume_m3 === undefined) payload.front_hoop_volume_m3 = Number(record.front_hoop_volume_m3 || 0);
  if (payload.front_hoop_density_kg_m3 === undefined) payload.front_hoop_density_kg_m3 = Number(record.front_hoop_density_kg_m3 || 0);
  if (payload.hardpoints_weight_g === undefined) payload.hardpoints_weight_g = Number(record.hardpoints_weight_g || 0);
  return payload;
}

function renderTestFilterOptions() {
  const select = $("#specimen-test-filter");
  if (!select) return;
  const testTypes = Array.from(new Set(["3PB", "Shear", ...state.specimens.map((specimen) => specimen.test_type).filter(Boolean)]));
  select.innerHTML = [`<option value="all">All</option>`, ...testTypes.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`)].join("");
  select.value = testTypes.includes(state.dbTestFilter) ? state.dbTestFilter : "all";
  state.dbTestFilter = select.value;
}

function sortableTh(label, key) {
  const active = state.dbSort.key === key;
  return `<th class="${active ? "is-sorted" : ""}">
    <div class="header-stack">
      <button class="sort-button ${active ? "is-sorted" : ""}" data-action="sort-db" data-key="${key}">${label}</button>
    </div>
  </th>`;
}

function panelEiTh(panel, index) {
  const sorted = state.dbSort.key === `ei_${panel}`;
  const active = state.dbEiPassPanels[panel] ? "is-active" : "";
  return `<th class="metric-th">
    <div class="cs-header ${sorted ? "is-sorted" : ""}">
      <button class="sort-button ${sorted ? "is-sorted" : ""}" data-action="sort-db" data-key="ei_${panel}">CS EI ${escapeHtml(panelAbbreviation(panel))}</button>
      <button class="mini-filter ${active}" data-action="toggle-ei-pass" data-panel="${panel}" aria-pressed="${active ? "true" : "false"}" title="Show only CS EI ${panelAbbreviation(panel)} > 1">&gt;1</button>
    </div>
  </th>`;
}

function perimeterShearTh(panel) {
  const sorted = state.dbSort.key === `perimeter_${panel}`;
  const active = state.dbPerimeterPassPanels[panel] ? "is-active" : "";
  return `<th class="metric-th">
    <div class="cs-header ${sorted ? "is-sorted" : ""}">
      <button class="sort-button ${sorted ? "is-sorted" : ""}" data-action="sort-db" data-key="perimeter_${panel}">Perimeter Shear ${escapeHtml(panelAbbreviation(panel))}</button>
      <button class="mini-filter ${active}" data-action="toggle-perimeter-pass" data-panel="${panel}" aria-pressed="${active ? "true" : "false"}" title="Show only Perimeter Shear ${panelAbbreviation(panel)} > 1">&gt;1</button>
    </div>
  </th>`;
}

function energyAbsorbedTh() {
  const sorted = state.dbSort.key === "energyAbsorbedJ";
  const active = state.dbEnergyPass ? "is-active" : "";
  return `<th class="metric-th energy-th">
    <div class="cs-header ${sorted ? "is-sorted" : ""}">
      <button class="sort-button ${sorted ? "is-sorted" : ""}" data-action="sort-db" data-key="energyAbsorbedJ">Energy Absorbed [J]</button>
      <button class="mini-filter energy-filter ${active}" data-action="toggle-energy-pass" aria-pressed="${active ? "true" : "false"}" title="Show only Energy Absorbed > 111.7 J">&gt;111,7 J</button>
    </div>
  </th>`;
}

function eiCell(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return `<td class="metric-cell">-</td>`;
  const cls = Number(value) >= 1 ? "ei-ok" : "ei-bad";
  return `<td class="metric-cell"><span class="${cls}">${formatNumber(value, 3)}</span></td>`;
}

function notApplicableCell() {
  return `<td class="metric-cell muted-cell">N/A</td>`;
}

function energyAbsorbedCell(specimen) {
  const value = energyAbsorbedJ(specimen);
  if (value === null) return notApplicableCell();
  const cls = value > ENERGY_ABSORBED_THRESHOLD_J ? "ei-ok" : "ei-bad";
  return `<td class="metric-cell energy-cell"><span class="${cls}">${formatNumber(value, 2)}</span></td>`;
}

function renderSpecimenTable() {
  const rows = sortedFilteredSpecimens()
    .map((specimen) => {
      const special = isSpecialTestType(specimen.test_type);
      const panelCells = VISIBLE_EI_PANELS.map((panel) => (special ? notApplicableCell() : eiCell(csEiValue(specimen, panel)))).join("");
      const energyCell = energyAbsorbedCell(specimen);
      const perimeterCells = PERIMETER_SHEAR_CODES.map((panel) => (special ? notApplicableCell() : eiCell(specimen.perimeter_shear_by_panel?.[panel]))).join("");
      const actionCell = state.databaseEditMode
        ? `<td><button class="button danger small" data-action="delete-specimen" data-id="${escapeHtml(specimen.id)}">Delete</button></td>`
        : "";
      return `
        <tr data-specimen-id="${escapeHtml(specimen.id)}">
          <td><strong>${escapeHtml(specimen.id)}</strong></td>
          <td>${escapeHtml(specimen.test_type)}</td>
          <td>${escapeHtml(specimen.core_type || specimen.core_material || "-")}</td>
          <td class="sequence-cell">${escapeHtml(specimenLaminateSequence(specimen))}</td>
          <td>${escapeHtml(carbonFiberNamesForSpecimen(specimen))}</td>
          <td>${formatNumber(specimen.real_weight_g, 2)}</td>
          ${panelCells}
          ${energyCell}
          ${perimeterCells}
          ${actionCell}
        </tr>`;
    })
    .join("");
  const actionHeader = state.databaseEditMode ? "<th>Actions</th>" : "";
  const colSpan = 6 + VISIBLE_EI_PANELS.length + 1 + PERIMETER_SHEAR_CODES.length + (state.databaseEditMode ? 1 : 0);
  $("#specimen-table").innerHTML = `
    <table class="probes-table">
      <thead><tr>
        ${sortableTh("ID", "id")}
        ${sortableTh("Test", "test_type")}
        ${sortableTh("Core type", "core_type")}
        ${sortableTh("Laminate sequence", "laminate_sequence")}
        ${sortableTh("Carbon Fibers", "carbon_fibers")}
        ${sortableTh("Real Weight [g]", "real_weight_g")}
        ${VISIBLE_EI_PANELS.map((panel, index) => panelEiTh(panel, index)).join("")}
        ${energyAbsorbedTh()}
        ${PERIMETER_SHEAR_CODES.map((panel) => perimeterShearTh(panel)).join("")}
        ${actionHeader}
      </tr></thead>
      <tbody>${rows || `<tr><td colspan="${colSpan}">No probes stored</td></tr>`}</tbody>
    </table>`;
}

function detailValue(label, value, formatter = formatNumber) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${formatter(value)}</dd></div>`;
}

function finiteValue(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) return number;
  }
  return null;
}

function deltaValue(real, theoretical) {
  const r = Number(real);
  const t = Number(theoretical);
  return Number.isFinite(r) && Number.isFinite(t) ? r - t : null;
}

function comparisonClass(real, theoretical) {
  const r = Number(real);
  const t = Number(theoretical);
  if (!Number.isFinite(r) || !Number.isFinite(t)) return "";
  return r > t ? "warn" : "good";
}

function characteristicValue(label, value, unit = "", cls = "") {
  const text = typeof value === "string" ? escapeHtml(value || "-") : `${formatNumber(value, 3)}${unit}`;
  return `<div class="${cls ? `metric-${cls}` : ""}"><dt>${escapeHtml(label)}</dt><dd>${text}</dd></div>`;
}

function renderProbeCharacteristics(specimen) {
  const theoretical = specimen.theoretical || {};
  const computed = specimen.computed || {};
  const topTheoretical = finiteValue(theoretical.top_skin_thickness_mm);
  const bottomTheoretical = finiteValue(theoretical.bottom_skin_thickness_mm);
  const realWeight = finiteValue(specimen.real_weight_g);
  const theoreticalWeight = finiteValue(theoretical.total_weight_g);
  const realThickness = finiteValue(specimen.real_thickness_mm);
  const theoreticalThickness = finiteValue(theoretical.total_thickness_mm);
  const energy = energyAbsorbedJ(specimen);
  const showEnergy = isEnergyAbsorbedRelevant(specimen.test_type) || energy !== null;
  const energyRow = showEnergy
    ? characteristicValue(
        "Energy Absorbed [J]",
        energy === null ? "-" : `${formatNumber(energy, 2)} J`,
        "",
        energy !== null && energy > ENERGY_ABSORBED_THRESHOLD_J ? "good" : "warn",
      )
    : "";
  return `
    <section class="detail-section">
      <h3>Probe Characteristics</h3>
      <dl class="detail-list">
        ${characteristicValue("Theoretical weight [g]", theoreticalWeight)}
        ${characteristicValue("Real weight [g]", realWeight)}
        ${characteristicValue("Weight delta [g]", deltaValue(realWeight, theoreticalWeight), "", comparisonClass(realWeight, theoreticalWeight))}
        ${characteristicValue("Theoretical total thickness [mm]", theoreticalThickness)}
        ${characteristicValue("Real total thickness [mm]", realThickness)}
        ${characteristicValue("Total thickness delta [mm]", deltaValue(realThickness, theoreticalThickness), "", comparisonClass(realThickness, theoreticalThickness))}
        ${characteristicValue("Theoretical top skin thickness [mm]", topTheoretical)}
        ${characteristicValue("Theoretical bottom skin thickness [mm]", bottomTheoretical)}
        ${characteristicValue("Core thickness [mm]", finiteValue(computed.core_thickness_mm, specimen.core_thickness_mm, theoretical.core_thickness_mm))}
        ${energyRow}
        ${characteristicValue("Carbon Fibers", carbonFiberNamesForSpecimen(specimen), "", "")}
        ${characteristicValue("Warping percentage", formatPercent(theoretical.warping_percent, 2), "", "")}
        ${characteristicValue("0 degree fibers percentage", formatPercent(theoretical.zero_percent, 2), "", "")}
        ${characteristicValue("Comments", specimen.comments || "-", "", "")}
      </dl>
    </section>`;
}

function renderTestProperties(specimen) {
  const computed = specimen.computed || {};
  const common = computed.common || {};
  if (isSpecialTestType(specimen.test_type)) {
    const limit = specialTestLimitKn(specimen.test_type);
    const rows = [
      ["Fmax [N]", common.max_force_n, formatNumberNoGrouping],
      ["Limit [kN]", limit],
    ];
    return `
      <section class="detail-section">
        <h3>Test Properties</h3>
        <dl class="detail-list">${rows.map(([label, value, formatter]) => detailValue(label, value, formatter || formatNumber)).join("")}</dl>
      </section>`;
  }
  const region = common.linear_region || {};
  const isShear = computed.mode === "Shear" || String(specimen.test_type || "").toUpperCase().includes("SHEAR");
  const rows = isShear
    ? [
        ["Lower Peak x [mm]", common.lowest_peak_x_mm],
        ["Lower Peak y [N]", common.lowest_peak_n, formatNumberNoGrouping],
        ["Upper Peak x [mm]", common.highest_peak_x_mm],
        ["Upper Peak y [N]", common.highest_peak_n, formatNumberNoGrouping],
      ]
    : [
        ["x1 [mm]", region.x1_mm],
        ["x2 [mm]", region.x2_mm],
        ["y1 [N]", region.y1_n, formatNumberNoGrouping],
        ["y2 [N]", region.y2_n, formatNumberNoGrouping],
        ["Fmax [N]", common.max_force_n, formatNumberNoGrouping],
      ];
  return `
    <section class="detail-section">
      <h3>Test Properties</h3>
      <dl class="detail-list">${rows.map(([label, value, formatter]) => detailValue(label, value, formatter || formatNumber)).join("")}</dl>
    </section>`;
}

function renderLaminateSummary(laminate) {
  if (!laminate || !laminate.top_skin) return `<div class="empty-state">No laminate data</div>`;
  const layerText = (layer, index, skinLayers, skin) => {
    const material = materialById(layer.material_id)?.name || layer.material_name || `Material ${layer.material_id}`;
    return `<li><strong>${skinLayerNumber(skin, index, skinLayers)}</strong> ${escapeHtml(material)} ${escapeHtml(layer.orientation)}</li>`;
  };
  return `
    <div class="laminate-summary">
      <h3>Laminate Structure</h3>
      <div><strong>Top Skin</strong><ol>${laminate.top_skin.map((layer, index) => layerText(layer, index, laminate.top_skin, "top")).join("")}</ol></div>
      <div class="core-summary">CORE: ${escapeHtml(laminate.core?.name || laminate.core?.key || "")}</div>
      <div><strong>Bottom Skin</strong><ol>${laminate.bottom_skin.map((layer, index) => layerText(layer, index, laminate.bottom_skin, "bottom")).join("")}</ol></div>
    </div>`;
}

function renderSelectedPoints(specimen) {
  const rows = (specimen.selected_points || [])
    .map((point) => `<tr><td>${escapeHtml(point.role)}</td><td>${formatNumber(point.x_mm, 4)}</td><td>${formatNumber(point.y_n, 3)}</td><td>${formatNumber(Number(point.y_n) / 1000, 3)}</td></tr>`)
    .join("");
  return `
    <table class="tight-table">
      <thead><tr><th>Role</th><th>x [mm]</th><th>y [N]</th><th>y [kN]</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="4">No selected points</td></tr>`}</tbody>
    </table>`;
}

function renderPanelMetricsSection(specimen) {
  if (isSpecialTestType(specimen.test_type)) return "";
  const car = selectedCar();
  const { panelResults, message } = activeCarPanelMetricsForSpecimen(specimen);
  const subtitle = car ? `<span class="section-subtitle">Active car: ${escapeHtml(car.name)}</span>` : "";
  return `
    <section class="detail-section">
      <h3>Panel Metrics</h3>
      ${subtitle}
      ${panelResults
        ? `<div class="table-wrap">${panelResultsTable(panelResults, true)}</div>`
        : `<div class="empty-state">${escapeHtml(message)}</div>`}
    </section>`;
}

function renderSpecimenDetail(specimen) {
  const sequence = specimenLaminateSequence(specimen);
  $("#specimen-detail").innerHTML = `
    <div class="modal-header">
      <div class="modal-title-block">
        <h2 id="specimen-modal-title">${escapeHtml(specimen.id)}</h2>
        <strong>${escapeHtml(sequence)}</strong>
        <span>${escapeHtml(specimen.test_type)}</span>
      </div>
      <div class="button-row">
        <button class="button primary" data-action="export-specimen" data-id="${escapeHtml(specimen.id)}">Export Excel</button>
        <button class="icon-button" data-action="close-modal" title="Close">x</button>
      </div>
    </div>
    ${renderPanelMetricsSection(specimen)}
    ${renderProbeCharacteristics(specimen)}
    ${renderTestProperties(specimen)}
    <section class="detail-section">
      <h3>Test Graph</h3>
      <canvas id="detail-chart" width="900" height="520"></canvas>
    </section>`;
  drawGraph($("#detail-chart"), specimen);
}

async function selectSpecimen(id) {
  state.selectedSpecimen = await api(`/api/specimens/${encodeURIComponent(id)}`);
  if (state.selectedCarId && !state.carProbeMetrics[String(state.selectedCarId)]) {
    await loadCarProbeMetrics(state.selectedCarId).catch(() => {});
  }
  renderSpecimenDetail(state.selectedSpecimen);
  $("#specimen-modal").classList.remove("hidden");
}

function closeModal() {
  $("#specimen-modal").classList.add("hidden");
}

function niceTickStart(min, step) {
  return Math.floor(min / step) * step;
}

function drawGraph(canvas, specimen) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(Math.max(window.devicePixelRatio || 1, 2), 3);
  const cssWidth = canvas.clientWidth || 900;
  const cssHeight = canvas.clientHeight || 520;
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const points = specimen.reduced_points || specimen.computed?.reduced_points || [];
  const special = isSpecialTestType(specimen.test_type);
  const limitKn = specialTestLimitKn(specimen.test_type);
  const selected = special ? [] : specimen.selected_points || specimen.computed?.selected_points || [];
  if (!points.length) {
    ctx.fillStyle = "#A8B3BB";
    ctx.font = "700 16px sans-serif";
    ctx.fillText("No curve data", 24, 42);
    return;
  }

  const all = points.concat(selected.map((p) => ({ x_mm: p.x_mm, y_n: p.y_n })));
  if (Number.isFinite(limitKn)) all.push({ x_mm: points[0]?.x_mm || 0, y_n: limitKn * 1050 });
  const xs = all.map((p) => Number(p.x_mm)).filter(Number.isFinite);
  const ys = all.map((p) => Number(p.y_n) / 1000).filter(Number.isFinite);
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys);
  const margin = { left: 62, right: 22, top: 22, bottom: 48 };
  const plotW = cssWidth - margin.left - margin.right;
  const plotH = cssHeight - margin.top - margin.bottom;
  const scaleX = (x) => margin.left + ((x - minX) / (maxX - minX || 1)) * plotW;
  const scaleY = (yKn) => margin.top + plotH - ((yKn - minY) / (maxY - minY || 1)) * plotH;

  ctx.fillStyle = "#101820";
  ctx.fillRect(0, 0, cssWidth, cssHeight);
  ctx.strokeStyle = "rgba(168, 179, 187, 0.18)";
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  for (let xTick = niceTickStart(minX, 1); xTick <= maxX + 0.0001; xTick += 1) {
    const x = scaleX(xTick);
    ctx.moveTo(x, margin.top);
    ctx.lineTo(x, margin.top + plotH);
  }
  for (let yTick = niceTickStart(minY, 5); yTick <= maxY + 0.0001; yTick += 5) {
    const y = scaleY(yTick);
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + plotW, y);
  }
  ctx.stroke();

  ctx.strokeStyle = "#A8B3BB";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, margin.top + plotH);
  ctx.lineTo(margin.left + plotW, margin.top + plotH);
  ctx.stroke();

  ctx.fillStyle = "#A8B3BB";
  ctx.font = "800 13px sans-serif";
  ctx.fillText("Load [kN]", 8, 18);
  ctx.fillText("Displacement [mm]", margin.left + plotW - 132, cssHeight - 12);
  for (let yTick = niceTickStart(minY, 5); yTick <= maxY + 0.0001; yTick += 5) {
    const y = scaleY(yTick);
    ctx.fillText(formatNumber(yTick, 0), 10, y + 4);
  }
  for (let xTick = niceTickStart(minX, 1); xTick <= maxX + 0.0001; xTick += 1) {
    const x = scaleX(xTick);
    ctx.fillText(formatNumber(xTick, 0), x - 4, cssHeight - 26);
  }

  const region = specimen.computed?.common?.linear_region;
  if (region && !special) {
    const x1 = minX;
    const x2 = maxX;
    const y1 = (region.slope_n_per_mm * x1 + region.intercept_n) / 1000;
    const y2 = (region.slope_n_per_mm * x2 + region.intercept_n) / 1000;
    ctx.save();
    ctx.setLineDash([6, 5]);
    ctx.strokeStyle = "#1C93D8";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(scaleX(x1), scaleY(y1));
    ctx.lineTo(scaleX(x2), scaleY(y2));
    ctx.stroke();
    ctx.restore();
  }

  ctx.strokeStyle = "#FFFFFF";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = scaleX(Number(point.x_mm));
    const y = scaleY(Number(point.y_n) / 1000);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  if (Number.isFinite(limitKn)) {
    const y = scaleY(limitKn);
    ctx.save();
    ctx.setLineDash([7, 5]);
    ctx.strokeStyle = "#FF4F00";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + plotW, y);
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = "#FF4F00";
    ctx.font = "800 12px sans-serif";
    ctx.fillText(`Limit: ${formatNumber(limitKn, 1)} kN`, margin.left + 10, Math.max(margin.top + 14, y - 8));
  }

  selected.forEach((point) => {
    const x = scaleX(Number(point.x_mm));
    const y = scaleY(Number(point.y_n) / 1000);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    ctx.strokeStyle = "#FFFFFF";
    ctx.fillStyle = point.role === "ymax" ? "#1C93D8" : "#FF4F00";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.arc(x, y, 6.25, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "800 12px sans-serif";
    ctx.fillText(point.role, Math.min(x + 8, cssWidth - 96), Math.max(y - 8, 14));
  });
}

function updateLayer(kind, skin, index, field, value) {
  if (skin === "bottom" && isSymmetric(kind)) return;
  const laminate = hydrateLaminate(kind);
  const layers = skin === "top" ? laminate.top_skin : laminate.bottom_skin;
  const layer = layers[index];
  layer[field] = value;
  if (field === "material_id") {
    const material = materialById(value);
    layer.material_name = material?.name || "";
    layer.orientation = "";
  }
  syncSymmetricLaminate(kind);
}

function addSkinLayer(kind, skin) {
  if (skin === "bottom" && isSymmetric(kind)) return;
  const laminate = hydrateLaminate(kind);
  if (skin === "top") laminate.top_skin.unshift(defaultLayer());
  else laminate.bottom_skin.push(defaultLayer());
  syncSymmetricLaminate(kind);
  renderLaminateView(kind);
}

function removeSkinLayer(kind, skin, index) {
  if (skin === "bottom" && isSymmetric(kind)) return;
  const laminate = hydrateLaminate(kind);
  const layers = skin === "top" ? laminate.top_skin : laminate.bottom_skin;
  layers.splice(index, 1);
  syncSymmetricLaminate(kind);
  renderLaminateView(kind);
}

function collectEditPayload(selector, id) {
  const payload = {};
  $$(`${selector}[data-field]`).forEach((input) => {
    if (String(input.dataset.editMaterial || input.dataset.editCore) === String(id)) {
      if (input.dataset.unit === "gpa") {
        payload[input.dataset.field] = input.value === "" ? null : gpaToPa(input.value);
      } else {
        payload[input.dataset.field] = input.type === "number" ? (input.value === "" ? null : Number(input.value)) : input.value;
      }
    }
  });
  return payload;
}

function applyMechanicalFormFields(payload) {
  ["e1", "e2", "g12"].forEach((key) => {
    const formKey = `${key}_gpa`;
    if (payload[formKey] !== undefined) {
      payload[`${key}_pa`] = payload[formKey] === "" ? null : gpaToPa(payload[formKey]);
      delete payload[formKey];
    }
  });
  [
    "e1_pa",
    "e2_pa",
    "g12_pa",
    "poisson_input",
    "density_kg_m3",
    "strength_x_mpa",
    "strength_x_compression_mpa",
    "strength_y_mpa",
    "strength_y_compression_mpa",
    "strength_s_mpa",
  ].forEach((key) => {
    if (payload[key] !== undefined) payload[key] = payload[key] === "" ? null : Number(payload[key]);
  });
  return payload;
}

async function exportSpecimen(id) {
  const response = await fetch(apiUrl(`/api/specimens/${encodeURIComponent(id)}/export`), {
    headers: authHeaders(),
  });
  if (!response.ok) {
    let message = "Export failed";
    try {
      message = (await response.json()).error || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || `specimen_${id}_export.xlsx`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function bindEvents() {
  $("#auth-controls")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = new FormData(event.currentTarget).get("email");
    try {
      await requestMagicLink(String(email || "").trim());
      renderAuthControls();
      showToast("Check your email for the SES Platform login link");
    } catch (error) {
      showToast(error.message);
    }
  });
  $("#auth-controls")?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (target?.dataset.action === "logout") {
      saveAuthSession({ token: "", email: "", expiresAt: 0 });
      showToast("Logged out");
    }
  });

  $$(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      $$(".tab").forEach((tab) => tab.classList.toggle("is-active", tab === button));
      $$(".module").forEach((module) => module.classList.toggle("is-active", module.id === button.dataset.tab));
      if (button.dataset.tab === "database") loadSpecimens().catch((error) => showToast(error.message));
      if (button.dataset.tab === "monocoque") {
        Promise.all([loadCars(), loadSpecimens(), loadMonocoqueCalculations()]).catch((error) => showToast(error.message));
      }
    });
  });

  $$("[data-pre-section]").forEach((button) => {
    button.addEventListener("click", () => {
      state.preSection = button.dataset.preSection;
      renderPreSections();
      if (state.preSection === "shuffle") renderShuffleControls();
    });
  });
  $("#run-shuffle").addEventListener("click", () => runShuffleGenerator());
  $("#shuffle-material-toggle")?.addEventListener("click", () => {
    state.shuffleMaterialsOpen = !state.shuffleMaterialsOpen;
    renderShuffleControls();
  });
  ["shuffle-layer-count", "shuffle-zero-count", "shuffle-core", "shuffle-max", "shuffle-fix-layer-two", "shuffle-layer-one-rc"].forEach((id) => {
    $(`#${id}`)?.addEventListener("input", () => {
      $("#shuffle-feedback").textContent = "";
    });
    $(`#${id}`)?.addEventListener("change", () => {
      $("#shuffle-feedback").textContent = "";
    });
  });
  $$(".shuffle-orientation").forEach((input) => input.addEventListener("change", () => {
    $("#shuffle-feedback").textContent = "";
  }));
  $("#shuffle-panel-select")?.addEventListener("change", () => renderShuffleResults());
  document.addEventListener("change", (event) => {
    if (event.target?.classList?.contains("shuffle-material-option")) {
      $("#shuffle-feedback").textContent = "";
      updateShuffleMaterialSummary();
    }
  });
  $("#show-material-add").addEventListener("click", () => {
    state.materialAddOpen = !state.materialAddOpen;
    renderMaterialList();
  });
  $("#toggle-material-edit").addEventListener("click", () => {
    state.materialEditMode = !state.materialEditMode;
    state.materialEditingId = null;
    renderMaterialList();
  });
  $("#show-core-add").addEventListener("click", () => {
    state.coreAddOpen = !state.coreAddOpen;
    renderCoreList();
  });
  $("#toggle-core-edit").addEventListener("click", () => {
    state.coreEditMode = !state.coreEditMode;
    state.coreEditingId = null;
    renderCoreList();
  });
  $("#show-car-add").addEventListener("click", () => {
    state.carAddOpen = !state.carAddOpen;
    const form = $("#car-form");
    if (state.carAddOpen && form) {
      form.elements.name.value = "";
    }
    renderCarList();
  });
  $("#car-edit-mode").addEventListener("change", (event) => {
    state.carEditMode = event.target.checked;
    state.carEditingId = null;
    renderCarList();
  });
  $("#recalculate-selected-car").addEventListener("click", async () => {
    if (!state.selectedCarId) return showToast("Select a car first");
    try {
      showToast("Calculating probe metrics for selected car...");
      const result = await api(`/api/cars/${encodeURIComponent(state.selectedCarId)}/recalculate`, { method: "POST" });
      await loadCarProbeMetrics(state.selectedCarId);
      renderSpecimenTable();
      if (state.selectedSpecimen && !$("#specimen-modal")?.classList.contains("hidden")) {
        renderSpecimenDetail(state.selectedSpecimen);
      }
      const failed = result.failed || [];
      showToast(failed.length ? `Recalculated with failures: ${failed.map((item) => item.specimen_id).join(", ")}` : "Selected car probe metrics recalculated successfully");
    } catch (error) {
      showToast(error.message);
    }
  });
  $("#toggle-car-database").addEventListener("click", () => {
    state.carDatabaseOpen = !state.carDatabaseOpen;
    renderMonocoqueView();
  });
  $("#toggle-monocoque-saved").addEventListener("click", () => {
    state.monocoqueSavedOpen = !state.monocoqueSavedOpen;
    renderMonocoqueView();
  });
  $("#monocoque-saved-edit-mode").addEventListener("change", (event) => {
    state.monocoqueSavedEditMode = event.target.checked;
    state.monocoqueSavedEditingId = null;
    state.monocoqueSavedEditingRecord = null;
    renderMonocoqueView();
  });

  $("#process-form").addEventListener("input", () => updateProcessValidation());
  $("#process-test-type").addEventListener("change", () => updateProcessValidation());
  $("#process-file-input").addEventListener("change", () => updateProcessUploadUi());
  const dropzone = $("#process-file-drop");
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragover");
    });
  });
  dropzone.addEventListener("drop", (event) => {
    setProcessUploadFiles(event.dataTransfer?.files);
  });

  $("#material-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    try {
      const form = new FormData(formElement);
      const payload = Object.fromEntries(form.entries());
      payload.thickness_mm = Number(payload.thickness_mm);
      payload.areal_weight_g_m2 = Number(payload.areal_weight_g_m2);
      payload.resin_fraction = Number(payload.resin_fraction);
      payload.material_category = "fiber";
      payload.technical_id = payload.name;
      payload.aliases = payload.aliases || "";
      payload.fiber_type = payload.fiber_family === "ud" ? "unidirectional" : "bidirectional";
      applyMechanicalFormFields(payload);
      await api("/api/materials", { method: "POST", body: JSON.stringify(payload) });
      resetFormSafely(formElement);
      state.materialAddOpen = true;
      await loadMaterials();
      showToast("Carbon fiber saved");
    } catch (error) {
      showToast(error.message);
    }
  });

  $("#core-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    try {
      const form = new FormData(formElement);
      const payload = Object.fromEntries(form.entries());
      payload.thickness_mm = Number(payload.thickness_mm);
      payload.density_kg_m3 = Number(payload.density_kg_m3);
      payload.material_category = "core";
      payload.technical_id = payload.name;
      payload.aliases = payload.aliases || "";
      payload.fiber_family = "";
      applyMechanicalFormFields(payload);
      await api("/api/core-materials", { method: "POST", body: JSON.stringify(payload) });
      resetFormSafely(formElement);
      state.coreAddOpen = true;
      await loadMaterials();
      showToast("Core material saved");
    } catch (error) {
      showToast(error.message);
    }
  });

  $("#car-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    try {
      const form = new FormData(formElement);
      const payload = {
        name: form.get("name"),
        panels: cloneLayers(selectedCar()?.panels || []),
      };
      showToast("Calculating probe metrics for new car...");
      const created = await api("/api/cars", { method: "POST", body: JSON.stringify(payload) });
      state.selectedCarId = created.id;
      const failed = created.recalculation?.failed || [];
      resetFormSafely(formElement);
      state.carAddOpen = true;
      await loadCars();
      showToast(failed.length ? `Car created, probe metric failures: ${failed.map((item) => item.specimen_id).join(", ")}` : "Car created and probe metrics calculated successfully");
    } catch (error) {
      showToast(error.message);
    }
  });

  document.addEventListener("click", async (event) => {
    const savedRow = event.target.closest("[data-saved-monocoque-id]");
    if (savedRow && !state.monocoqueSavedEditMode) {
      try {
        await openMonocoqueCalculation(savedRow.dataset.savedMonocoqueId);
        showToast("Saved calculation loaded");
      } catch (error) {
        showToast(error.message);
      }
      return;
    }
    const target = event.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;
    const kind = target.dataset.kind;
    try {
      if (action === "add-skin-layer") {
        addSkinLayer(kind, target.dataset.skin);
        if (kind === "pre") await calculatePre();
      }
      if (action === "remove-skin-layer") {
        removeSkinLayer(kind, target.dataset.skin, Number(target.dataset.index));
        if (kind === "pre") await calculatePre();
      }
      if (action === "toggle-symmetric") {
        setSymmetric(kind, !isSymmetric(kind));
        renderLaminateView(kind);
        if (kind === "pre") await calculatePre();
      }
      if (action === "sort-shuffle") {
        const key = target.dataset.key;
        state.shuffleSort = {
          key,
          dir: state.shuffleSort?.key === key && state.shuffleSort.dir === "desc" ? "asc" : "desc",
        };
        renderShuffleResults();
      }
      if (action === "toggle-shuffle-zero-filter") {
        state.shuffleZeroUnder50 = !state.shuffleZeroUnder50;
        renderShuffleResults();
      }
      if (action === "toggle-shuffle-ei-filter") {
        state.shuffleEiPass = !state.shuffleEiPass;
        renderShuffleResults();
      }
      if (action === "edit-material") {
        if (!state.materialEditMode) return;
        state.materialEditingId = target.dataset.id;
        renderMaterialList();
      }
      if (action === "close-material-editor") {
        state.materialEditingId = null;
        renderMaterialList();
      }
      if (action === "save-material") {
        if (!state.materialEditMode) return;
        const payload = collectEditPayload("[data-edit-material]", target.dataset.id);
        const currentMaterial = state.materials.find((material) => String(material.id) === String(target.dataset.id));
        payload.material_category = "fiber";
        payload.technical_id = payload.name;
        payload.aliases = preserveAliases(currentMaterial, payload.name, payload.aliases);
        payload.fiber_type = payload.fiber_family === "ud" ? "unidirectional" : "bidirectional";
        applyMechanicalFormFields(payload);
        await api(`/api/materials/${target.dataset.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        await loadMaterials();
        showToast("Carbon fiber updated");
      }
      if (action === "delete-material") {
        if (!state.materialEditMode) return;
        if (!confirm("Delete this carbon fiber material?")) return;
        await api(`/api/materials/${target.dataset.id}`, { method: "DELETE" });
        if (String(state.materialEditingId) === String(target.dataset.id)) state.materialEditingId = null;
        await loadMaterials();
        showToast("Carbon fiber deleted");
      }
      if (action === "edit-core") {
        if (!state.coreEditMode) return;
        state.coreEditingId = target.dataset.id;
        renderCoreList();
      }
      if (action === "close-core-editor") {
        state.coreEditingId = null;
        renderCoreList();
      }
      if (action === "save-core") {
        if (!state.coreEditMode) return;
        const payload = collectEditPayload("[data-edit-core]", target.dataset.id);
        const currentCore = state.coreMaterials.find((core) => String(core.id) === String(target.dataset.id));
        payload.material_category = "core";
        payload.technical_id = payload.name;
        payload.aliases = preserveAliases(currentCore, payload.name, payload.aliases);
        payload.fiber_family = "";
        applyMechanicalFormFields(payload);
        await api(`/api/core-materials/${target.dataset.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        await loadMaterials();
        showToast("Core material updated");
      }
      if (action === "delete-core") {
        if (!state.coreEditMode) return;
        if (!confirm("Delete this core material?")) return;
        await api(`/api/core-materials/${target.dataset.id}`, { method: "DELETE" });
        if (String(state.coreEditingId) === String(target.dataset.id)) state.coreEditingId = null;
        await loadMaterials();
        showToast("Core material deleted");
      }
      if (action === "edit-car") {
        if (!state.carEditMode) return;
        state.carEditingId = target.dataset.id;
        renderCarList();
      }
      if (action === "close-car-editor") {
        state.carEditingId = null;
        renderCarList();
      }
      if (action === "save-car") {
        if (!state.carEditMode) return;
        showToast("Saving car and recalculating probe metrics...");
        const updated = await api(`/api/cars/${target.dataset.id}`, {
          method: "PUT",
          body: JSON.stringify(collectCarPayload(target.dataset.id)),
        });
        const failed = updated.recalculation?.failed || [];
        await loadCars();
        await calculateMonocoque().catch(() => {});
        showToast(failed.length ? `Car updated, probe metric failures: ${failed.map((item) => item.specimen_id).join(", ")}` : "Car updated and probe metrics recalculated");
      }
      if (action === "delete-car") {
        if (!state.carEditMode) return;
        if (!confirm("Delete this car?")) return;
        await api(`/api/cars/${target.dataset.id}`, { method: "DELETE" });
        if (String(state.carEditingId) === String(target.dataset.id)) state.carEditingId = null;
        await loadCars();
        showToast("Car deleted");
      }
      if (action === "open-monocoque") {
        await openMonocoqueCalculation(target.dataset.id);
        showToast("Saved calculation loaded");
      }
      if (action === "post-edit-input") {
        state.postView = "input";
        renderPostWorkflow();
      }
      if (action === "save-monocoque-meta") {
        if (!state.monocoqueSavedEditMode) return;
        const name = $(`[data-edit-monocoque="${target.dataset.id}"][data-field="name"]`)?.value;
        await api(`/api/monocoque-weights/${target.dataset.id}`, {
          method: "PUT",
          body: JSON.stringify({ metadata_only: true, name }),
        });
        await loadMonocoqueCalculations();
        renderMonocoqueView();
        showToast("Saved calculation updated");
      }
      if (action === "edit-monocoque-record") {
        if (!state.monocoqueSavedEditMode) return;
        state.monocoqueSavedEditingId = target.dataset.id;
        state.monocoqueSavedEditingRecord = await api(`/api/monocoque-weights/${target.dataset.id}`);
        renderMonocoqueSavedOptions();
      }
      if (action === "close-monocoque-editor") {
        state.monocoqueSavedEditingId = null;
        state.monocoqueSavedEditingRecord = null;
        renderMonocoqueSavedOptions();
      }
      if (action === "save-monocoque-record") {
        if (!state.monocoqueSavedEditMode) return;
        const saved = await api(`/api/monocoque-weights/${target.dataset.id}`, {
          method: "PUT",
          body: JSON.stringify(collectMonocoqueSavedPayload(target.dataset.id)),
        });
        state.monocoqueSavedEditingRecord = saved;
        await loadMonocoqueCalculations();
        renderMonocoqueView();
        showToast("Saved calculation updated");
      }
      if (action === "delete-monocoque") {
        if (!state.monocoqueSavedEditMode) return;
        if (!confirm("Delete this saved monocoque calculation?")) return;
        await api(`/api/monocoque-weights/${target.dataset.id}`, { method: "DELETE" });
        if (String(state.selectedMonocoqueId) === String(target.dataset.id)) {
          state.selectedMonocoqueId = null;
          state.monocoqueResult = null;
          state.monocoqueAssignments = {};
        }
        if (String(state.monocoqueSavedEditingId) === String(target.dataset.id)) {
          state.monocoqueSavedEditingId = null;
          state.monocoqueSavedEditingRecord = null;
        }
        await loadMonocoqueCalculations();
        renderMonocoqueView();
        showToast("Saved calculation deleted");
      }
      if (action === "sort-db") {
        const key = target.dataset.key;
        state.dbSort = {
          key,
          dir: state.dbSort.key === key && state.dbSort.dir === "asc" ? "desc" : "asc",
        };
        renderSpecimenTable();
      }
      if (action === "toggle-ei-pass") {
        const panel = target.dataset.panel;
        state.dbEiPassPanels[panel] = !state.dbEiPassPanels[panel];
        renderSpecimenTable();
      }
      if (action === "toggle-perimeter-pass") {
        const panel = target.dataset.panel;
        state.dbPerimeterPassPanels[panel] = !state.dbPerimeterPassPanels[panel];
        renderSpecimenTable();
      }
      if (action === "toggle-energy-pass") {
        state.dbEnergyPass = !state.dbEnergyPass;
        renderSpecimenTable();
      }
      if (action === "delete-specimen") {
        event.stopPropagation();
        if (!state.databaseEditMode) return;
        if (confirm(`Delete probe ${target.dataset.id}?`)) {
          await api(`/api/specimens/${encodeURIComponent(target.dataset.id)}`, { method: "DELETE" });
          await loadSpecimens();
          showToast("Specimen deleted");
        }
      }
      if (action === "close-modal") closeModal();
      if (action === "export-specimen") {
        await exportSpecimen(target.dataset.id);
        showToast("Excel export downloaded");
      }
    } catch (error) {
      showToast(error.message);
    }
  });

  document.addEventListener("change", async (event) => {
    const target = event.target;
    if (target.matches("[data-layer-kind]")) {
      updateLayer(target.dataset.layerKind, target.dataset.skin, Number(target.dataset.index), target.dataset.field, target.value);
      renderLaminateView(target.dataset.layerKind);
      if (target.dataset.layerKind === "pre") await calculatePre().catch((error) => showToast(error.message));
    }
    if (target.matches("[data-core-select]")) {
      const kind = target.dataset.coreSelect;
      hydrateLaminate(kind).core = { key: target.value };
      renderLaminateView(kind);
      if (kind === "pre") await calculatePre().catch((error) => showToast(error.message));
    }
    if (target.matches("[data-monocoque-panel]")) {
      state.monocoqueAssignments[target.dataset.monocoquePanel] = target.value;
      await calculateMonocoque().catch((error) => showToast(error.message));
    }
  });

  $("#pre-test-type").addEventListener("change", () => {
    syncPreDimensionsFromTestType();
    calculatePre().catch((error) => showToast(error.message));
  });

  $("#process-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      if (!updateProcessValidation({ force: true })) {
        throw new Error("Complete the required experimental data fields before processing");
      }
      const laminate = buildLaminate("post");
      if (laminateSequence(laminate) === "Incomplete laminate") {
        throw new Error("Complete the laminate sequence before processing experimental data");
      }
      const form = new FormData(event.currentTarget);
      form.set("laminate_json", JSON.stringify(laminate));
      form.set("specimen_width_mm", $("#post-width").value);
      form.set("specimen_length_mm", $("#post-length").value);
      form.set("car_id", state.selectedCarId || "");
      const response = await fetch(apiUrl("/api/specimens/process"), {
        method: "POST",
        body: form,
        headers: authHeaders(),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Processing failed");
      renderProcessResult(payload);
      clearProcessedProbeInputs();
      await loadSpecimens();
      showToast("Specimen processed and stored");
    } catch (error) {
      showToast(error.message);
    }
  });

  $("#database-edit-mode").addEventListener("change", (event) => {
    state.databaseEditMode = event.target.checked;
    renderSpecimenTable();
  });
  $("#specimen-filter").addEventListener("input", (event) => {
    state.dbFilter = event.target.value;
    renderSpecimenTable();
  });
  $("#specimen-test-filter").addEventListener("change", (event) => {
    state.dbTestFilter = event.target.value;
    renderSpecimenTable();
  });
  $("#refresh-db").addEventListener("click", () => {
    resetDatabaseFilters();
    showToast("Database filters reset");
  });
  const handleActiveCarChange = async (event, options = {}) => {
    state.selectedCarId = Number(event.target.value);
    if (options.resetAssignments) state.monocoqueAssignments = {};
    state.monocoqueResult = null;
    await loadCarProbeMetrics(state.selectedCarId).catch(() => {});
    renderCarSelectors();
    renderMonocoqueView();
    renderSpecimenTable();
    renderShufflePanelOptions();
    renderShuffleResults();
    if (state.preCalculation) renderPreResults(state.preCalculation);
    if (state.selectedSpecimen && !$("#specimen-modal")?.classList.contains("hidden")) {
      renderSpecimenDetail(state.selectedSpecimen);
    }
    if (options.recalculateMonocoque) await calculateMonocoque().catch(() => {});
  };
  $("#monocoque-car-select").addEventListener("change", async (event) => {
    await handleActiveCarChange(event, { resetAssignments: true, recalculateMonocoque: true });
  });
  $("#process-car-select").addEventListener("change", async (event) => {
    await handleActiveCarChange(event);
  });
  $("#database-car-select").addEventListener("change", async (event) => {
    await handleActiveCarChange(event);
  });
  $("#pre-car-select")?.addEventListener("change", async (event) => {
    await handleActiveCarChange(event);
  });
  $("#shuffle-car-select")?.addEventListener("change", async (event) => {
    await handleActiveCarChange(event);
  });
  $$("[data-monocoque-section]").forEach((button) => {
    button.addEventListener("click", () => {
      state.monocoqueSection = button.dataset.monocoqueSection;
      renderMonocoqueView();
    });
  });
  ["monocoque-name", "front-hoop-volume", "front-hoop-density", "hardpoints-weight"].forEach((id) => {
    $(`#${id}`).addEventListener("input", () => calculateMonocoque().catch((error) => showToast(error.message)));
  });
  $("#save-monocoque").addEventListener("click", async () => {
    try {
      const payload = monocoquePayload();
      if (!payload.car_id) return showToast("Select a car first");
      const canUpdateSaved = Boolean(payload.id && state.monocoqueSavedEditMode);
      const method = canUpdateSaved ? "PUT" : "POST";
      const path = canUpdateSaved ? `/api/monocoque-weights/${payload.id}` : "/api/monocoque-weights";
      if (!canUpdateSaved) delete payload.id;
      const saved = await api(path, { method, body: JSON.stringify(payload) });
      await loadMonocoqueCalculations();
      if (canUpdateSaved) {
        state.selectedMonocoqueId = saved.id;
        state.monocoqueResult = saved.computed;
      } else {
        resetMonocoqueWorkspace();
      }
      state.monocoqueSavedEditMode = false;
      renderMonocoqueView();
      showToast("Monocoque calculation saved");
    } catch (error) {
      showToast(error.message);
    }
  });
  $("#specimen-table").addEventListener("click", (event) => {
    if (event.target.closest("[data-action]")) return;
    const row = event.target.closest("[data-specimen-id]");
    if (row) selectSpecimen(row.dataset.specimenId).catch((error) => showToast(error.message));
  });
  $("#specimen-modal").addEventListener("click", (event) => {
    if (event.target.id === "specimen-modal") closeModal();
  });

  window.addEventListener("resize", () => {
    if (state.processResult && state.postView === "results") drawGraph($("#process-chart"), state.processResult);
    if (state.selectedSpecimen && !$("#specimen-modal").classList.contains("hidden")) {
      drawGraph($("#detail-chart"), state.selectedSpecimen);
    }
  });
}

async function init() {
  loadAuthSession();
  parseAuthRedirect();
  renderAuthControls();
  moduleShells();
  bindEvents();
  await loadMaterials();
  await calculatePre();
  await loadSpecimens();
  await loadCars();
  await loadMonocoqueCalculations();
  renderMonocoqueView();
  updateProcessUploadUi();
}

init().catch((error) => showToast(error.message));
