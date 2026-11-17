/*
 * Leapmotor Cloud – animated dashboard cards and a dashboard strategy for Home Assistant.
 *
 * Unofficial project, not affiliated with or endorsed by Leapmotor.
 * Cards find the entities of a vehicle by device and translation key, so renamed
 * entity ids keep working.
 */

const DOMAIN = "leapmotor_cloud";
const VERSION = "1.0.0";
const DOCS_URL = "https://github.com/VierNeunStein/ha-leapmotor-cloud";

const STRINGS = {
  en: {
    vehicle: "Vehicle",
    charging: "Charging",
    climate: "Climate",
    status: "Status",
    statistics: "Statistics",
    history: "History",
    details: "All entities",
    system: "System",
    locked: "Locked",
    unlocked: "Unlocked",
    plugged: "Plugged in",
    unplugged: "Not plugged in",
    charging_at: "Charging · {power}",
    climate_off: "Climate off",
    heating: "Heating",
    cooling: "Cooling",
    ventilating: "Ventilating",
    defrosting: "Defrosting",
    doors_closed: "Doors closed",
    door_open: "Door open",
    trunk_open: "Tailgate open",
    windows_closed: "Windows closed",
    windows_open: "Window open",
    sentry_on: "Sentry on",
    tire_warning: "Check tires",
    parked: "Parked",
    driving: "Driving",
    lock: "Lock",
    unlock: "Unlock",
    climate_on_action: "Climate",
    start_charging: "Start",
    stop_charging: "Stop",
    find: "Find",
    trunk: "Tailgate",
    open_trunk: "Open",
    close_trunk: "Close tailgate",
    windows: "Windows",
    vent: "Vent",
    close: "Close",
    close_windows: "Close windows",
    refresh: "Refresh",
    confirm: "Tap again to confirm",
    confirm_short: "Sure?",
    range: "Range",
    limit: "Limit",
    power: "Power",
    current: "Current",
    voltage: "Voltage",
    remaining: "Remaining",
    finished_at: "Done at",
    to_limit: "To limit",
    battery_temp: "Battery",
    schedule: "Charging schedule",
    charge_limit: "Charge limit",
    release_plug: "Release plug",
    last_charge: "Last charge",
    wallbox: "Wallbox",
    solar: "Solar",
    vehicle_node: "Vehicle",
    inside: "Inside",
    outside: "Outside",
    target: "Target",
    fan: "Fan",
    off: "Off",
    heat: "Heat",
    cool: "Cool",
    ventilate: "Ventilate",
    quick_cool: "Quick cool",
    quick_heat: "Quick heat",
    defrost: "Defrost",
    seats: "Seats",
    seat_heat: "Heating",
    seat_vent: "Ventilation",
    driver: "Driver",
    passenger: "Passenger",
    steering_wheel: "Steering wheel",
    mirrors: "Mirrors",
    battery_preheat: "Battery preheat",
    tires: "Tire pressure",
    openings: "Doors & windows",
    doors: "Doors",
    odometer: "Odometer",
    today: "Today",
    last_week: "Last week",
    driving_energy: "Driving",
    climate_energy: "Climate",
    other_energy: "Other",
    last_7_days: "Distance, last 7 days",
    consumption: "Ø consumption",
    total_energy: "Energy in total",
    delivered: "Days since delivery",
    no_vehicle: "No Leapmotor vehicle found. Set up the Leapmotor Cloud integration first.",
    offline: "Cloud not reachable",
    now: "just now",
    front: "Front",
    rear: "Rear",
    open: "open",
    closed: "closed",
    level: "Level",
  },
  de: {
    vehicle: "Fahrzeug",
    charging: "Laden",
    climate: "Klima",
    status: "Status",
    statistics: "Statistik",
    history: "Verlauf",
    details: "Alle Entitäten",
    system: "System",
    locked: "Verriegelt",
    unlocked: "Entriegelt",
    plugged: "Eingesteckt",
    unplugged: "Nicht eingesteckt",
    charging_at: "Lädt · {power}",
    climate_off: "Klima aus",
    heating: "Heizt",
    cooling: "Kühlt",
    ventilating: "Lüftet",
    defrosting: "Enteist",
    doors_closed: "Türen zu",
    door_open: "Tür offen",
    trunk_open: "Heckklappe offen",
    windows_closed: "Fenster zu",
    windows_open: "Fenster offen",
    sentry_on: "Wächter an",
    tire_warning: "Reifen prüfen",
    parked: "Geparkt",
    driving: "Fährt",
    lock: "Verriegeln",
    unlock: "Entriegeln",
    climate_on_action: "Klima",
    start_charging: "Starten",
    stop_charging: "Stoppen",
    find: "Finden",
    trunk: "Heckklappe",
    open_trunk: "Öffnen",
    close_trunk: "Klappe zu",
    windows: "Fenster",
    vent: "Spalt",
    close: "Schließen",
    close_windows: "Fenster zu",
    refresh: "Aktualisieren",
    confirm: "Zum Bestätigen nochmal tippen",
    confirm_short: "Sicher?",
    range: "Reichweite",
    limit: "Limit",
    power: "Leistung",
    current: "Strom",
    voltage: "Spannung",
    remaining: "Restzeit",
    finished_at: "Fertig um",
    to_limit: "Bis Limit",
    battery_temp: "Batterie",
    schedule: "Ladeplan",
    charge_limit: "Ladelimit",
    release_plug: "Stecker lösen",
    last_charge: "Letzte Ladung",
    wallbox: "Wallbox",
    solar: "PV",
    vehicle_node: "Fahrzeug",
    inside: "Innen",
    outside: "Außen",
    target: "Ziel",
    fan: "Gebläse",
    off: "Aus",
    heat: "Heizen",
    cool: "Kühlen",
    ventilate: "Lüften",
    quick_cool: "Schnellkühlen",
    quick_heat: "Schnellheizen",
    defrost: "Enteisen",
    seats: "Sitze",
    seat_heat: "Heizung",
    seat_vent: "Belüftung",
    driver: "Fahrer",
    passenger: "Beifahrer",
    steering_wheel: "Lenkrad",
    mirrors: "Spiegel",
    battery_preheat: "Batterie vorheizen",
    tires: "Reifendruck",
    openings: "Türen & Fenster",
    doors: "Türen",
    odometer: "Kilometerstand",
    today: "Heute",
    last_week: "Letzte Woche",
    driving_energy: "Fahren",
    climate_energy: "Klima",
    other_energy: "Sonstiges",
    last_7_days: "Strecke der letzten 7 Tage",
    consumption: "Ø Verbrauch",
    total_energy: "Energie gesamt",
    delivered: "Tage seit Auslieferung",
    no_vehicle: "Kein Leapmotor-Fahrzeug gefunden. Richte zuerst die Integration „Leapmotor Cloud“ ein.",
    offline: "Cloud nicht erreichbar",
    now: "gerade eben",
    front: "Vorne",
    rear: "Hinten",
    open: "offen",
    closed: "zu",
    level: "Stufe",
  },
};

const LEVELS = ["off", "low", "medium", "high"];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char],
  );

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

function localeOf(hass) {
  return hass?.locale?.language || hass?.language || navigator.language || "en";
}

function langOf(hass) {
  return localeOf(hass).toLowerCase().startsWith("de") ? "de" : "en";
}

function translate(hass, key, vars = {}) {
  let text = STRINGS[langOf(hass)][key] ?? STRINGS.en[key] ?? key;
  for (const [name, value] of Object.entries(vars)) text = text.replace(`{${name}}`, value);
  return text;
}

const DEMO_VIN = "LDEMO000000000001";

function isDemo(hass, deviceId) {
  const identifiers = hass?.devices?.[deviceId]?.identifiers || [];
  return identifiers.some(([domain, id]) => domain === DOMAIN && id === DEMO_VIN);
}

function allLeapmotorDevices(hass) {
  const ids = [];
  for (const entity of Object.values(hass?.entities || {})) {
    if (entity.platform === DOMAIN && entity.device_id && !ids.includes(entity.device_id)) {
      ids.push(entity.device_id);
    }
  }
  return ids.sort((a, b) => deviceName(hass, a).localeCompare(deviceName(hass, b)));
}

/** Device ids of all Leapmotor vehicles; the demo vehicle only when it is alone. */
function leapmotorDevices(hass) {
  const ids = allLeapmotorDevices(hass);
  const real = ids.filter((id) => !isDemo(hass, id));
  return real.length ? real : ids;
}

/** Map "domain.translation_key" to the entity id of one vehicle. */
function entityMap(hass, deviceId) {
  const map = {};
  for (const entity of Object.values(hass?.entities || {})) {
    if (entity.platform !== DOMAIN || entity.device_id !== deviceId || !entity.translation_key) {
      continue;
    }
    map[`${entity.entity_id.split(".")[0]}.${entity.translation_key}`] = entity.entity_id;
  }
  return map;
}

function deviceName(hass, deviceId) {
  const device = hass?.devices?.[deviceId];
  return device?.name_by_user || device?.name || "Leapmotor";
}

function deviceModel(hass, deviceId) {
  return hass?.devices?.[deviceId]?.model || "";
}

function socColors(soc) {
  if (soc === null || soc === undefined) return ["#9e9e9e", "#bdbdbd"];
  if (soc < 15) return ["#ff4d4f", "#ff7a45"];
  if (soc < 30) return ["#ff9f43", "#ffc048"];
  return ["#1abc9c", "#2ecc71"];
}

// ---------------------------------------------------------------------------
// Real pictures: the layers of the app's picture package
// ---------------------------------------------------------------------------

const PICTURE_CACHE = new Map();
const FRAME_TIME = 0.18;
/** Frames of the charging animation (carpic_charge2.png ...), as many as the package has. */
function chargeFrames(available) {
  return available
    .map((name) => [name, /^carpic_charge(\d+)\.png$/.exec(name)])
    .filter(([, match]) => match && Number(match[1]) >= 2)
    .sort((a, b) => Number(a[1][1]) - Number(b[1][1]))
    .map(([name]) => name);
}

/** Load one layer with the user's credentials; the result is kept for the session. */
function loadPicture(hass, url) {
  let entry = PICTURE_CACHE.get(url);
  if (!entry) {
    entry = { src: null, failed: false };
    entry.promise = hass
      .fetchWithAuth(url)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.blob();
      })
      .then((blob) => {
        entry.src = URL.createObjectURL(blob);
        return entry.src;
      })
      .catch((err) => {
        entry.failed = true;
        console.debug("Leapmotor Cloud: picture not available", url, err);
        return null;
      });
    PICTURE_CACHE.set(url, entry);
  }
  return entry;
}

/** The layers to stack for a vehicle state, back to front, the way the app does it. */
function pictureLayers(available, state) {
  const has = new Set(available);
  const stack = [];
  const add = (name) => {
    if (has.has(name)) stack.push(name);
  };
  // The open tailgate and the far-side doors lie behind the body.
  if (state.trunk) add("carpic_tailgate_open.png");
  add(state.rearRight ? "carpic_rightbehind_open.png" : "carpic_rightbehind_close.png");
  add(state.frontRight ? "carpic_rightfront_open.png" : "carpic_rightfront_close.png");
  add("carpic_body.png");
  add("carpic_hood_close.png");
  add(state.rearLeft ? "carpic_leftbehind_open.png" : "carpic_leftbehind_close.png");
  add(state.frontLeft ? "carpic_leftfront_open.png" : "carpic_leftfront_close.png");
  // Glass is only drawn while the window is closed.
  if (!state.windowFrontLeft) add("carpic_leftfront_window_close.png");
  if (!state.windowRearLeft) add("carpic_leftbehind_window_close.png");
  if (state.charging || state.plugged) add("carpic_charge_open.png");
  if (state.plugged && !state.charging) add("carpic_charge1.png");
  const frames = state.charging ? chargeFrames(available) : [];
  return { stack, frames };
}

const SPOKES = [0, 72, 144, 216, 288]
  .map((deg) => {
    const rad = (deg * Math.PI) / 180;
    const c = Math.cos(rad);
    const s = Math.sin(rad);
    return `M${(c * 5).toFixed(2)} ${(s * 5).toFixed(2)} L${(c * 16).toFixed(2)} ${(s * 16).toFixed(2)}`;
  })
  .join(" ");

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const BASE_CSS = `
  :host {
    --lm-green: #2ecc71;
    --lm-teal: #1abc9c;
    --lm-blue: #3d9be9;
    --lm-orange: #ff9f43;
    --lm-red: #ff5d5d;
    --lm-amber: #ffc048;
    --lm-soft: color-mix(in srgb, var(--primary-text-color) 6%, transparent);
    --lm-softer: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
    display: block;
  }
  ha-card { overflow: hidden; position: relative; height: 100%; box-sizing: border-box; }
  .card { padding: 16px; }
  .header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .title { font-size: 1.2rem; font-weight: 600; line-height: 1.25; color: var(--primary-text-color); display: flex; align-items: center; gap: 8px; }
  .title ha-icon { --mdc-icon-size: 22px; color: var(--title-color, var(--primary-color)); }
  .subtitle { color: var(--secondary-text-color); font-size: .875rem; margin-top: 2px; }
  .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: .78rem; background: var(--lm-soft); color: var(--secondary-text-color); white-space: nowrap; cursor: pointer; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--lm-green); animation: lm-ping 2.6s ease-out infinite; flex: none; }
  .dot.off { background: var(--lm-red); animation: none; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px 6px 8px; border-radius: 999px; background: var(--lm-soft); font-size: .84rem; color: var(--primary-text-color); cursor: pointer; transition: background .25s, transform .15s; user-select: none; }
  .chip:active { transform: scale(.97); }
  .chip ha-icon { --mdc-icon-size: 18px; color: var(--chip-color, var(--state-icon-color, var(--secondary-text-color))); }
  .chip.ok { --chip-color: var(--lm-green); }
  .chip.charge { --chip-color: var(--lm-green); background: color-mix(in srgb, var(--lm-green) 15%, transparent); }
  .chip.charge ha-icon { animation: lm-pulse 1.6s ease-in-out infinite; }
  .chip.warn { --chip-color: var(--lm-orange); background: color-mix(in srgb, var(--lm-orange) 15%, transparent); }
  .chip.warn ha-icon { animation: lm-wiggle 2.4s ease-in-out infinite; }
  .chip.alert { --chip-color: var(--lm-red); background: color-mix(in srgb, var(--lm-red) 15%, transparent); }
  .chip.heat { --chip-color: var(--lm-orange); background: color-mix(in srgb, var(--lm-orange) 13%, transparent); }
  .chip.heat ha-icon { animation: lm-flicker 1.3s ease-in-out infinite; }
  .chip.cool { --chip-color: var(--lm-blue); background: color-mix(in srgb, var(--lm-blue) 13%, transparent); }
  .chip.cool ha-icon, .chip.fan ha-icon { animation: lm-spin 4s linear infinite; }
  .chip.fan { --chip-color: var(--lm-teal); background: color-mix(in srgb, var(--lm-teal) 13%, transparent); }
  .chip.active { --chip-color: var(--lm-blue); }
  .actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(68px, 1fr)); gap: 8px; }
  .action { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-height: 64px; padding: 8px 4px; border: none; border-radius: 14px; background: var(--lm-soft); color: var(--primary-text-color); font: inherit; font-size: .76rem; line-height: 1.15; cursor: pointer; transition: transform .15s, background .25s; -webkit-tap-highlight-color: transparent; }
  .action:hover { background: color-mix(in srgb, var(--action-color, var(--primary-color)) 14%, transparent); }
  .action:active { transform: scale(.95); }
  .action ha-icon { --mdc-icon-size: 24px; color: var(--action-color, var(--primary-color)); transition: transform .3s; }
  .action[disabled] { opacity: .38; cursor: default; }
  .action.on { background: color-mix(in srgb, var(--action-color, var(--primary-color)) 18%, transparent); }
  .action.armed { background: color-mix(in srgb, var(--lm-orange) 24%, transparent); animation: lm-shake .45s; }
  .action.armed ha-icon { color: var(--lm-orange); }
  .action.pending ha-icon { animation: lm-breathe 1s ease-in-out infinite; }
  .action.pending::after { content: ""; position: absolute; top: 7px; right: 7px; width: 11px; height: 11px; border-radius: 50%; border: 2px solid color-mix(in srgb, var(--primary-color) 25%, transparent); border-top-color: var(--primary-color); animation: lm-spin .8s linear infinite; }
  .hint { min-height: 1.1em; margin-top: 8px; font-size: .78rem; color: var(--lm-orange); text-align: center; }
  .section-title { font-size: .78rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--secondary-text-color); margin: 16px 0 8px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 8px; }
  .stat { padding: 10px 12px; border-radius: 12px; background: var(--lm-soft); cursor: pointer; min-width: 0; }
  .stat span { display: block; font-size: .74rem; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .stat b { display: block; font-size: 1.08rem; font-weight: 600; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-top: 1px solid var(--divider-color); }
  .row:first-child { border-top: none; }
  .row .label { display: flex; align-items: center; gap: 8px; color: var(--primary-text-color); font-size: .92rem; }
  .row .label ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
  .row .value { color: var(--secondary-text-color); font-size: .92rem; }
  .toggle { position: relative; width: 44px; height: 24px; border-radius: 999px; background: color-mix(in srgb, var(--primary-text-color) 22%, transparent); border: none; cursor: pointer; transition: background .25s; flex: none; padding: 0; }
  .toggle::after { content: ""; position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.35); transition: transform .25s cubic-bezier(.3,1.4,.6,1); }
  .toggle.on { background: var(--primary-color); }
  .toggle.on::after { transform: translateX(20px); }
  .toggle.pending { opacity: .55; }
  input[type=range] { width: 100%; accent-color: var(--primary-color); margin: 0; }
  input[type=time] { font: inherit; font-size: .9rem; color: var(--primary-text-color); background: var(--lm-soft); border: 1px solid var(--divider-color); border-radius: 8px; padding: 4px 6px; color-scheme: light dark; }
  .empty { padding: 24px 16px; color: var(--secondary-text-color); display: flex; gap: 12px; align-items: center; }
  .empty ha-icon { --mdc-icon-size: 36px; color: var(--disabled-text-color, #999); }
  .muted { color: var(--secondary-text-color); }
  .stack { position: relative; width: fit-content; max-width: 100%; margin: 0 auto; }
  .stack .layer { display: block; }
  .stack .base { position: relative; max-width: 100%; max-height: 240px; width: auto; height: auto; }
  .stack .layer:not(.base) { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
  .stack .frame { opacity: 0; }
  @media (prefers-reduced-motion: reduce) { .stack .frame.last { opacity: 1; } }
  @keyframes lm-spin { to { transform: rotate(360deg); } }
  @keyframes lm-ping { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--lm-green) 55%, transparent); } 80%, 100% { box-shadow: 0 0 0 8px transparent; } }
  @keyframes lm-pulse { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.18); opacity: .75; } }
  @keyframes lm-breathe { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
  @keyframes lm-wiggle { 0%, 80%, 100% { transform: rotate(0); } 85% { transform: rotate(-12deg); } 90% { transform: rotate(10deg); } 95% { transform: rotate(-6deg); } }
  @keyframes lm-flicker { 0%, 100% { transform: scale(1) rotate(0); } 25% { transform: scale(1.1, .94) rotate(-3deg); } 50% { transform: scale(.94, 1.08) rotate(2deg); } 75% { transform: scale(1.06, .96) rotate(-1deg); } }
  @keyframes lm-shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-3px); } 75% { transform: translateX(3px); } }
  @keyframes lm-grow { from { transform: scaleY(0); } }
  @keyframes lm-grow-x { from { transform: scaleX(0); } }
  @keyframes lm-fade-up { from { opacity: 0; transform: translateY(6px); } }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
`;

// ---------------------------------------------------------------------------
// Base card
// ---------------------------------------------------------------------------

class LeapmotorBaseCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._pending = new Set();
    this._armed = null;
    this._armTimer = null;
    this._signature = null;
    this._ticker = null;
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
    this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
  }

  static getStubConfig(hass) {
    const [device] = leapmotorDevices(hass);
    return device ? { device_id: device } : {};
  }

  static get editorSchema() {
    return [{ name: "device_id", selector: { device: { integration: DOMAIN } } }];
  }

  static getConfigElement() {
    const editor = document.createElement("leapmotor-card-editor");
    editor.schema = this.editorSchema;
    return editor;
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Invalid configuration");
    this._config = { ...config };
    this._signature = null;
    this._refresh();
  }

  set hass(hass) {
    this._hass = hass;
    this._refresh();
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    // Relative times ("5 min ago") need a refresh even without new states.
    this._ticker = setInterval(() => {
      this._signature = null;
      this._refresh();
    }, 60000);
  }

  disconnectedCallback() {
    clearInterval(this._ticker);
    clearTimeout(this._armTimer);
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    // "full": also fill sections that span several columns.
    return { columns: "full", min_columns: 6, rows: "auto" };
  }

  // -- data access ------------------------------------------------------------

  get deviceId() {
    const chosen = this._config.device_id;
    if (chosen && allLeapmotorDevices(this._hass).includes(chosen)) return chosen;
    return leapmotorDevices(this._hass)[0];
  }

  t(key, vars) {
    return translate(this._hass, key, vars);
  }

  e(key) {
    return this._entities?.[key];
  }

  st(key) {
    const id = this.e(key);
    return id ? this._hass.states[id] : undefined;
  }

  v(key) {
    const state = this.st(key);
    return state && state.state !== "unavailable" && state.state !== "unknown" ? state.state : undefined;
  }

  n(key) {
    const value = parseFloat(this.v(key));
    return Number.isFinite(value) ? value : null;
  }

  on(key) {
    return this.v(key) === "on";
  }

  attr(key, name) {
    return this.st(key)?.attributes?.[name];
  }

  has(key) {
    return Boolean(this.st(key));
  }

  extra(entityId) {
    const state = entityId ? this._hass.states[entityId] : undefined;
    return state && state.state !== "unavailable" && state.state !== "unknown" ? state : undefined;
  }

  extraEntities() {
    return [];
  }

  // -- formatting -------------------------------------------------------------

  get locale() {
    return localeOf(this._hass);
  }

  num(value, digits = 0) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "–";
    return new Intl.NumberFormat(this.locale, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(Number(value));
  }

  unit(value, unit, digits = 0) {
    const text = this.num(value, digits);
    return text === "–" ? text : `${text} ${unit}`;
  }

  formatted(key) {
    const state = this.st(key);
    if (!state) return "–";
    if (this._hass.formatEntityState) return this._hass.formatEntityState(state);
    return state.state;
  }

  duration(minutes) {
    if (minutes === null || minutes === undefined || !Number.isFinite(minutes)) return "–";
    const hours = Math.floor(minutes / 60);
    const rest = Math.round(minutes % 60);
    return hours ? `${hours} h ${rest} min` : `${rest} min`;
  }

  clock(iso) {
    if (!iso) return "–";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "–";
    const today = new Date();
    const options = { hour: "2-digit", minute: "2-digit" };
    if (date.toDateString() !== today.toDateString()) options.weekday = "short";
    return new Intl.DateTimeFormat(this.locale, options).format(date);
  }

  ago(iso) {
    if (!iso) return "–";
    const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
    if (!Number.isFinite(seconds)) return "–";
    if (seconds < 60) return this.t("now");
    const format = new Intl.RelativeTimeFormat(this.locale, { numeric: "auto" });
    if (seconds < 3600) return format.format(-Math.round(seconds / 60), "minute");
    if (seconds < 86400) return format.format(-Math.round(seconds / 3600), "hour");
    return format.format(-Math.round(seconds / 86400), "day");
  }

  kw(state) {
    if (!state) return null;
    const value = parseFloat(state.state);
    if (!Number.isFinite(value)) return null;
    const unit = String(state.attributes?.unit_of_measurement || "").toLowerCase();
    if (unit === "w") return value / 1000;
    if (unit === "mw") return value * 1000;
    return value;
  }

  // -- rendering ----------------------------------------------------------------

  _refresh() {
    if (!this._hass) return;
    const deviceId = this.deviceId;
    this._entities = deviceId ? entityMap(this._hass, deviceId) : {};
    const ids = [...Object.values(this._entities), ...this.extraEntities()];
    let signature = `${deviceId}|${langOf(this._hass)}|${[...this._pending].join(",")}|${this._armed}|${this._local ? JSON.stringify(this._local) : ""}|`;
    for (const id of ids) {
      const state = this._hass.states[id];
      signature += state ? `${id}=${state.state}@${state.last_updated};` : `${id}=-;`;
    }
    if (signature === this._signature) return;
    this._signature = signature;
    const body = deviceId
      ? this.body(deviceId)
      : `<ha-card><div class="empty"><ha-icon icon="mdi:car-off"></ha-icon><span>${esc(this.t("no_vehicle"))}</span></div></ha-card>`;
    this.shadowRoot.innerHTML = `<style>${BASE_CSS}${this.constructor.styles || ""}</style>${body}`;
  }

  invalidate() {
    this._signature = null;
    this._refresh();
  }

  button(action, icon, label, { confirm = false, disabled = false, color = "", active = false } = {}) {
    const pending = this._pending.has(action);
    const armed = this._armed === action;
    const classes = ["action", pending && "pending", armed && "armed", active && "on"].filter(Boolean).join(" ");
    return `<button class="${classes}" data-action="${action}"${confirm ? ' data-confirm="1"' : ""}${disabled ? " disabled" : ""}${color ? ` style="--action-color:${color}"` : ""} title="${esc(label)}"><ha-icon icon="${icon}"></ha-icon><span>${esc(armed ? this.t("confirm_short") : label)}</span></button>`;
  }

  toggle(action, isOn) {
    const pending = this._pending.has(action);
    return `<button class="toggle${isOn ? " on" : ""}${pending ? " pending" : ""}" data-action="${action}" role="switch" aria-checked="${isOn ? "true" : "false"}"></button>`;
  }

  hint() {
    return `<div class="hint">${this._armed ? esc(this.t("confirm")) : ""}</div>`;
  }

  // -- interaction ----------------------------------------------------------------

  actions() {
    return {};
  }

  _target(ev, attribute) {
    return ev.composedPath().find((el) => el instanceof Element && el.hasAttribute?.(attribute));
  }

  _onClick(ev) {
    const more = this._target(ev, "data-more");
    if (more) {
      this.moreInfo(more.getAttribute("data-more"));
      return;
    }
    const target = this._target(ev, "data-action");
    if (!target || target.hasAttribute("disabled")) return;
    const action = target.getAttribute("data-action");
    const handler = this.actions()[action];
    if (!handler) return;
    if (this.constructor.instantActions?.includes(action)) {
      // Local changes (e.g. +/-) that the card sends later on its own.
      handler(target);
      return;
    }
    if (this._pending.has(action)) return;
    if (target.hasAttribute("data-confirm") && this._armed !== action) {
      this._arm(action);
      return;
    }
    this._disarm(false);
    this.run(action, () => handler(target));
  }

  _onChange(ev) {
    const target = this._target(ev, "data-change");
    if (!target) return;
    const action = target.getAttribute("data-change");
    const handler = this.actions()[action];
    if (handler) this.run(action, () => handler(target));
  }

  _onInput(ev) {
    const target = this._target(ev, "data-live");
    if (!target) return;
    const output = this.shadowRoot.getElementById(target.getAttribute("data-live"));
    if (output) output.textContent = `${target.value} %`;
  }

  _arm(action) {
    clearTimeout(this._armTimer);
    this._armed = action;
    this.invalidate();
    this._armTimer = setTimeout(() => this._disarm(true), 4000);
  }

  _disarm(render) {
    clearTimeout(this._armTimer);
    if (this._armed === null) return;
    this._armed = null;
    if (render) this.invalidate();
  }

  async run(action, handler) {
    this._pending.add(action);
    this.invalidate();
    try {
      await handler();
    } catch (err) {
      // Home Assistant already shows a notification for failed actions.
      console.debug("Leapmotor Cloud action failed", action, err);
    } finally {
      this._pending.delete(action);
      this.invalidate();
    }
  }

  call(domain, service, data) {
    return this._hass.callService(domain, service, data);
  }

  entityCall(key, domain, service, data = {}) {
    const entityId = this.e(key);
    if (!entityId) return Promise.resolve();
    return this.call(domain, service, { entity_id: entityId, ...data });
  }

  moreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId } }));
  }

  more(key) {
    const id = this.e(key);
    return id ? ` data-more="${esc(id)}"` : "";
  }

  header(icon, title, subtitle, badge = "") {
    return `<div class="header"><div><div class="title"><ha-icon icon="${icon}"></ha-icon>${esc(title)}</div>${subtitle ? `<div class="subtitle">${subtitle}</div>` : ""}</div>${badge}</div>`;
  }

  /** Openings and charger as used for the app's picture layers. */
  pictureState() {
    const chargingState = this.v("sensor.charging_state");
    // The per-window sensors are disabled by default; the cloud moves all windows together.
    const anyWindow = this.on("binary_sensor.windows") || this.v("cover.windows") === "open";
    const windowOpen = (key) => (this.has(key) ? this.on(key) : anyWindow);
    return {
      trunk: this.v("cover.trunk") === "open" || this.on("binary_sensor.trunk"),
      frontLeft: this.on("binary_sensor.door_driver"),
      frontRight: this.on("binary_sensor.door_passenger"),
      rearLeft: this.on("binary_sensor.door_rear_left"),
      rearRight: this.on("binary_sensor.door_rear_right"),
      windowFrontLeft: windowOpen("binary_sensor.window_driver"),
      windowRearLeft: windowOpen("binary_sensor.window_rear_left"),
      charging: chargingState === "charging" || this.on("binary_sensor.charging"),
      plugged:
        this.on("binary_sensor.plugged_in") ||
        ["plugged_in", "scheduled", "paused", "finished", "charging"].includes(chargingState),
    };
  }

  /** The app's picture layers for the current state: null, {loading} or {stack, frames}. */
  appPicture() {
    const layers = this.attr("image.picture", "layers");
    const path = this.attr("image.picture", "layer_path");
    if (!Array.isArray(layers) || !layers.includes("carpic_body.png") || !path || !this._hass.fetchWithAuth) {
      return null;
    }
    const version = encodeURIComponent(this.attr("image.picture", "layer_version") || "");
    const { stack, frames } = pictureLayers(layers, this.pictureState());
    const entries = [...stack, ...frames].map((name) => [name, loadPicture(this._hass, `${path}${name}?v=${version}`)]);
    const waiting = entries.filter(([, entry]) => !entry.src && !entry.failed);
    if (waiting.length) {
      Promise.all(waiting.map(([, entry]) => entry.promise)).then(() => this.invalidate());
      return { loading: true };
    }
    const src = Object.fromEntries(entries.filter(([, entry]) => entry.src).map(([name, entry]) => [name, entry.src]));
    if (!src["carpic_body.png"]) return null;
    return {
      stack: stack.filter((name) => src[name]).map((name) => src[name]),
      frames: frames.filter((name) => src[name]).map((name) => src[name]),
    };
  }

  pictureStack(picture) {
    const count = picture.frames.length;
    const layers = picture.stack
      .map((src, index) => `<img class="layer${index === 0 ? " base" : ""}" src="${esc(src)}" alt="">`)
      .join("");
    const frames = picture.frames
      .map((src, index) => `<img class="layer frame${index === count - 1 ? " last" : ""}" src="${esc(src)}" alt="" style="animation-delay:${(index * FRAME_TIME).toFixed(2)}s">`)
      .join("");
    const animation = count
      ? `<style>.frame{animation:lm-frames-${count} ${(count * FRAME_TIME).toFixed(2)}s step-end infinite}@keyframes lm-frames-${count}{0%{opacity:1}${(100 / count).toFixed(3)}%{opacity:0}100%{opacity:0}}</style>`
      : "";
    return `${animation}<div class="stack">${layers}${frames}</div>`;
  }

  onlineBadge() {
    const online = this.v("binary_sensor.cloud_connection") !== "off";
    const updated = this.v("sensor.last_update");
    const text = online ? this.ago(updated) : this.t("offline");
    return `<div class="badge"${this.more("sensor.last_update")}><span class="dot${online ? "" : " off"}"></span>${esc(text)}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Vehicle card
// ---------------------------------------------------------------------------

const CAR_BODY =
  "M24 104 C22 92 28 86 40 83 L118 70 C132 60 150 46 170 40 L296 38 C318 40 336 52 350 62 C366 66 376 72 378 86 L378 104 C378 110 374 114 366 114 L342 114 A32 32 0 0 0 278 114 L127 114 A32 32 0 0 0 63 114 L34 114 C28 114 24 110 24 104 Z";
const CABLE = "M413 96 C412 126 388 130 374 110 C367 100 363 90 356 80";

class LeapmotorVehicleCard extends LeapmotorBaseCard {
  static get editorSchema() {
    return [
      { name: "device_id", selector: { device: { integration: DOMAIN } } },
      { name: "show_picture", selector: { boolean: {} } },
      { name: "image", selector: { text: {} } },
    ];
  }

  getCardSize() {
    return 8;
  }

  wheel(cx) {
    return `<g transform="translate(${cx} 114)"><circle class="tire" r="26"></circle><g class="rim"><circle class="rim-disc" r="17"></circle><path class="spokes" d="${SPOKES}"></path><circle class="hub" r="4.5"></circle></g></g>`;
  }

  car(photo) {
    // The position sits on a wrapper group: a CSS animation of `transform`
    // would otherwise replace the SVG transform attribute.
    const particles = [190, 232, 274]
      .map(
        (x, index) => `
      <g transform="translate(${x} 34)"><path class="heat-wave" style="animation-delay:${index * 0.45}s" d="M0 0 c4 -5 4 -9 0 -14 c-4 -5 -4 -9 0 -14"></path></g>
      <g transform="translate(${x} 12)"><path class="snow" style="animation-delay:${index * 0.6}s" d="M0 -5 V5 M-4.33 -2.5 L4.33 2.5 M-4.33 2.5 L4.33 -2.5"></path></g>
      <g transform="translate(${x - 26} ${16 + index * 7})"><path class="breeze" style="animation-delay:${index * 0.5}s" d="M0 0 q8 -6 16 0 t16 0"></path></g>`,
      )
      .join("");
    if (photo) {
      // Real pictures: the app's layers (or one picture), effects drawn on top.
      const content = photo.single
        ? `<div class="stack"><img class="layer base" src="${esc(photo.single)}" alt=""></div>`
        : this.pictureStack(photo);
      return `<div class="photo">${content}<svg class="fx-layer" viewBox="0 0 440 166" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><g class="fx">${particles}</g><path class="road" d="M-40 152 H480"></path></svg></div>`;
    }
    const vehicle = `
      <g class="body">
        <path class="paint" d="${CAR_BODY}"></path>
        <path class="glass front" d="M128 71 C141 62 154 51 172 46 L228 45 L228 70 Z"></path>
        <path class="glass rear" d="M236 45 L292 44 C310 46 324 54 336 63 L336 68 L236 70 Z"></path>
        <path class="door-fx front" d="M131 74 L229 71 L229 112 L131 112 Z"></path>
        <path class="door-fx rear" d="M231 71 L299 69 L299 96 L284 100 L279 112 L231 112 Z"></path>
        <path class="trunk-fx" d="M300 40 C320 42 338 52 350 62 C366 66 376 72 378 86 L378 100 L344 100 L300 70 Z"></path>
        <path class="seam" d="M130 76 L130 110 M230 72 L230 112 M300 70 L300 98 M120 74 L344 68"></path>
        <rect class="handle" x="196" y="81" width="18" height="4" rx="2"></rect>
        <rect class="handle" x="266" y="80" width="18" height="4" rx="2"></rect>
        <path class="mirror" d="M150 70 L162 66 L166 72 L154 74 Z"></path>
        <path class="headlight" d="M27 92 C33 87 44 84 56 83 L54 88 C44 90 36 92 29 96 Z"></path>
        <path class="taillight" d="M352 64 L374 76 L375 82 L350 70 Z"></path>
        <rect class="port" x="342" y="74" width="12" height="8" rx="2"></rect>
        <circle class="sentry-eye" cx="158" cy="69" r="2.6"></circle>
      </g>
      ${this.wheel(95)}${this.wheel(310)}`;
    return `
      <svg class="car" viewBox="0 0 440 166" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="lm-paint" x1="0" y1="0" x2="0" y2="1">
            <stop class="paint-top" offset="0"></stop>
            <stop class="paint-mid" offset=".55"></stop>
            <stop class="paint-bottom" offset="1"></stop>
          </linearGradient>
          <linearGradient id="lm-glass" x1="0" y1="0" x2="1" y2="1">
            <stop class="glass-a" offset="0"></stop>
            <stop class="glass-b" offset="1"></stop>
          </linearGradient>
          <radialGradient id="lm-shadow">
            <stop offset="0" stop-color="#000" stop-opacity=".38"></stop>
            <stop offset="1" stop-color="#000" stop-opacity="0"></stop>
          </radialGradient>
        </defs>
        <g class="fx">${particles}</g>
        <path class="ground" d="M0 140.5 H440"></path>
        <path class="road" d="M-40 152 H480"></path>
        <ellipse class="shadow" cx="200" cy="141" rx="182" ry="9"></ellipse>
        <g class="wallbox">
          <rect class="wb-body" x="402" y="50" width="22" height="42" rx="5"></rect>
          <circle class="wb-led" cx="413" cy="61" r="2.6"></circle>
          <path class="wb-holster" d="M408 74 H418 V86 H408 Z"></path>
        </g>
        <path class="cable" d="${CABLE}"></path>
        <path class="energy" d="${CABLE}"></path>
        ${vehicle}
      </svg>`;
  }

  body(deviceId) {
    const name = deviceName(this._hass, deviceId);
    const model = deviceModel(this._hass, deviceId);
    const soc = this.n("sensor.soc");
    const range = this.n("sensor.range");
    const limit = this.n("number.charge_limit");
    const chargingState = this.v("sensor.charging_state");
    const charging = chargingState === "charging" || this.on("binary_sensor.charging");
    const plugged =
      this.on("binary_sensor.plugged_in") ||
      ["plugged_in", "scheduled", "paused", "finished", "charging"].includes(chargingState);
    const power = this.n("sensor.charging_power");
    const remaining = this.n("sensor.charge_time_remaining");
    const lockState = this.v("lock.lock");
    const climateMode = this.v("climate.climate");
    const hvacAction = this.attr("climate.climate", "hvac_action");
    const climateOn = (climateMode && climateMode !== "off") || this.on("binary_sensor.climate_active");
    const driving = this.on("binary_sensor.driving");
    const doorFront = this.on("binary_sensor.door_driver") || this.on("binary_sensor.door_passenger");
    const doorRear = this.on("binary_sensor.door_rear_left") || this.on("binary_sensor.door_rear_right");
    const anyDoor = this.on("binary_sensor.doors") || doorFront || doorRear;
    const trunkOpen = this.v("cover.trunk") === "open" || this.on("binary_sensor.trunk");
    const windowsOpen = this.on("binary_sensor.windows") || this.v("cover.windows") === "open";
    const sentry = this.on("switch.sentry_mode");
    const tireWarning = this.on("binary_sensor.tire_warning");
    const interior = this.n("sensor.interior_temperature");
    const target = this.attr("climate.climate", "temperature");

    let climateKind = "";
    if (climateOn) {
      if (hvacAction === "defrosting") climateKind = "defrost";
      else if (hvacAction === "heating" || climateMode === "heat") climateKind = "heat";
      else if (hvacAction === "cooling" || climateMode === "cool") climateKind = "cool";
      else climateKind = "fan";
    }
    const classes = [
      "vehicle",
      charging && "charging",
      plugged && "plugged",
      driving && "driving",
      climateKind,
      lockState === "unlocked" && "unlocked",
      (doorFront || (anyDoor && !doorRear)) && "door-front",
      doorRear && "door-rear",
      trunkOpen && "trunk-open",
      windowsOpen && "windows-open",
      sentry && "sentry",
      (driving || climateOn || this.on("binary_sensor.vehicle_ready")) && "awake",
    ]
      .filter(Boolean)
      .join(" ");

    // Own picture (option "image"), else the app's layers, else its preview, else the drawing.
    let photo = null;
    if (this._config.image) {
      photo = { single: this._config.image };
    } else if (this._config.show_picture !== false) {
      const real = this.appPicture();
      if (real && !real.loading) photo = real;
      else if (this.v("image.picture") && this.attr("image.picture", "entity_picture")) {
        photo = { single: this.attr("image.picture", "entity_picture") };
      }
    }
    const [socA, socB] = socColors(soc);
    const flow = power ? clamp(2.4 - power / 25, 0.35, 2.2).toFixed(2) : "1.6";

    let status = driving ? this.t("driving") : this.t("parked");
    if (charging) status = this.t("charging_at", { power: this.unit(power, "kW", 1) });
    else if (plugged && chargingState) status = this.formatted("sensor.charging_state");
    const subtitle = `${esc(model ? `Leapmotor ${model}` : "Leapmotor")} · ${esc(status)}`;

    // chips
    const chips = [];
    if (lockState) {
      chips.push(
        lockState === "locked"
          ? `<div class="chip ok"${this.more("lock.lock")}><ha-icon icon="mdi:car-door-lock"></ha-icon>${esc(this.t("locked"))}</div>`
          : `<div class="chip warn"${this.more("lock.lock")}><ha-icon icon="mdi:car-door-lock-open"></ha-icon>${esc(this.t("unlocked"))}</div>`,
      );
    }
    if (charging) {
      const eta = remaining ? ` · ${this.duration(remaining)}` : "";
      chips.push(
        `<div class="chip charge"${this.more("sensor.charging_state")}><ha-icon icon="mdi:lightning-bolt"></ha-icon>${esc(this.unit(power, "kW", 1))}${esc(eta)}</div>`,
      );
    } else if (plugged) {
      chips.push(
        `<div class="chip active"${this.more("sensor.charging_state")}><ha-icon icon="mdi:ev-plug-type2"></ha-icon>${esc(chargingState ? this.formatted("sensor.charging_state") : this.t("plugged"))}</div>`,
      );
    } else if (this.has("binary_sensor.plugged_in")) {
      chips.push(
        `<div class="chip"${this.more("binary_sensor.plugged_in")}><ha-icon icon="mdi:power-plug-off-outline"></ha-icon>${esc(this.t("unplugged"))}</div>`,
      );
    }
    if (climateOn) {
      const icon = { heat: "mdi:fire", cool: "mdi:snowflake", defrost: "mdi:car-defrost-front", fan: "mdi:fan" }[climateKind];
      const label = { heat: "heating", cool: "cooling", defrost: "defrosting", fan: "ventilating" }[climateKind];
      const temp = target ? ` · ${this.num(target)} °C` : "";
      chips.push(
        `<div class="chip ${climateKind === "defrost" ? "heat" : climateKind}"${this.more("climate.climate")}><ha-icon icon="${icon}"></ha-icon>${esc(this.t(label))}${esc(temp)}</div>`,
      );
    } else if (this.has("climate.climate")) {
      const temp = interior !== null ? ` · ${this.unit(interior, "°C", 1)}` : "";
      chips.push(
        `<div class="chip"${this.more("climate.climate")}><ha-icon icon="mdi:fan-off"></ha-icon>${esc(this.t("climate_off"))}${esc(temp)}</div>`,
      );
    }
    if (trunkOpen) {
      chips.push(`<div class="chip warn"${this.more("cover.trunk")}><ha-icon icon="mdi:car-back"></ha-icon>${esc(this.t("trunk_open"))}</div>`);
    }
    if (anyDoor) {
      chips.push(`<div class="chip warn"${this.more("binary_sensor.doors")}><ha-icon icon="mdi:car-door"></ha-icon>${esc(this.t("door_open"))}</div>`);
    } else if (this.has("binary_sensor.doors") && !trunkOpen) {
      chips.push(`<div class="chip ok"${this.more("binary_sensor.doors")}><ha-icon icon="mdi:car-door"></ha-icon>${esc(this.t("doors_closed"))}</div>`);
    }
    if (windowsOpen) {
      chips.push(`<div class="chip warn"${this.more("cover.windows")}><ha-icon icon="mdi:window-open-variant"></ha-icon>${esc(this.t("windows_open"))}</div>`);
    } else if (this.has("binary_sensor.windows")) {
      chips.push(`<div class="chip ok"${this.more("binary_sensor.windows")}><ha-icon icon="mdi:window-closed-variant"></ha-icon>${esc(this.t("windows_closed"))}</div>`);
    }
    if (sentry) {
      chips.push(`<div class="chip active"${this.more("switch.sentry_mode")}><ha-icon icon="mdi:cctv"></ha-icon>${esc(this.t("sentry_on"))}</div>`);
    }
    if (tireWarning) {
      chips.push(`<div class="chip alert"${this.more("binary_sensor.tire_warning")}><ha-icon icon="mdi:car-tire-alert"></ha-icon>${esc(this.t("tire_warning"))}</div>`);
    }

    // actions
    const buttons = [];
    if (lockState) {
      buttons.push(
        lockState === "unlocked"
          ? this.button("lock", "mdi:car-door-lock", this.t("lock"), { color: "var(--lm-green)" })
          : this.button("unlock", "mdi:car-door-lock-open", this.t("unlock"), { confirm: true, color: "var(--lm-orange)" }),
      );
    }
    if (this.has("climate.climate")) {
      buttons.push(
        this.button("climate", climateOn ? "mdi:fan" : "mdi:fan-off", this.t("climate_on_action"), {
          active: climateOn,
          color: climateKind === "heat" || climateKind === "defrost" ? "var(--lm-orange)" : "var(--lm-blue)",
        }),
      );
    }
    if (this.has("switch.charging")) {
      buttons.push(
        this.button(
          "charge",
          charging ? "mdi:stop-circle-outline" : "mdi:play-circle-outline",
          charging ? this.t("stop_charging") : this.t("start_charging"),
          { disabled: !plugged && !charging, active: charging, color: "var(--lm-green)" },
        ),
      );
    }
    if (this.has("button.find_vehicle")) buttons.push(this.button("find", "mdi:car-search", this.t("find")));
    if (this.has("cover.trunk")) {
      buttons.push(
        trunkOpen
          ? this.button("trunk_close", "mdi:car-back", this.t("close_trunk"), { active: true, color: "var(--lm-orange)" })
          : this.button("trunk_open", "mdi:car-back", this.t("trunk"), { confirm: true }),
      );
    }
    if (this.has("cover.windows")) {
      buttons.push(
        windowsOpen
          ? this.button("windows_close", "mdi:window-closed-variant", this.t("close_windows"), { active: true, color: "var(--lm-orange)" })
          : this.button("windows_vent", "mdi:window-open-variant", this.t("vent"), { confirm: true }),
      );
    }

    return `
      <ha-card class="${classes}" style="--soc-a:${socA};--soc-b:${socB};--flow:${flow}s">
        <div class="card">
          ${this.header("mdi:car-electric", name, subtitle, this.onlineBadge())}
          <div class="hero"${this.more("device_tracker.location")}>${this.car(photo)}</div>
          <div class="soc">
            <div class="soc-value"${this.more("sensor.soc")}>${this.num(soc)}<small>%</small></div>
            <div class="bar"${this.more("number.charge_limit")}>
              <div class="fill" style="width:${clamp(soc ?? 0, 0, 100)}%"></div>
              ${limit !== null ? `<div class="limit" style="left:${clamp(limit, 0, 100)}%" data-label="${esc(this.t("limit"))} ${this.num(limit)} %"></div>` : ""}
            </div>
            <div class="range"${this.more("sensor.range")}><b>${this.num(range)}</b> km<span>${esc(this.t("range"))}</span></div>
          </div>
          <div class="chips">${chips.join("")}</div>
          <div class="actions">${buttons.join("")}</div>
          ${this.hint()}
        </div>
      </ha-card>`;
  }

  actions() {
    return {
      lock: () => this.entityCall("lock.lock", "lock", "lock"),
      unlock: () => this.entityCall("lock.lock", "lock", "unlock"),
      climate: () => {
        const isOn = (this.v("climate.climate") || "off") !== "off";
        return this.entityCall("climate.climate", "climate", isOn ? "turn_off" : "turn_on");
      },
      charge: () => {
        const charging = this.v("sensor.charging_state") === "charging" || this.on("binary_sensor.charging");
        return this.entityCall("switch.charging", "switch", charging ? "turn_off" : "turn_on");
      },
      find: () => this.entityCall("button.find_vehicle", "button", "press"),
      trunk_open: () => this.entityCall("cover.trunk", "cover", "open_cover"),
      trunk_close: () => this.entityCall("cover.trunk", "cover", "close_cover"),
      windows_vent: () => this.entityCall("cover.windows", "cover", "set_cover_position", { position: 20 }),
      windows_close: () => this.entityCall("cover.windows", "cover", "close_cover"),
    };
  }

  static get styles() {
    return `
      .hero { position: relative; margin: 8px -16px 0; padding: 4px 16px 0; cursor: pointer; transition: background .8s;
        background: radial-gradient(110% 85% at 50% 100%, color-mix(in srgb, var(--glow, transparent) 30%, transparent), transparent 72%); }
      .vehicle.charging { --glow: var(--lm-green); }
      .vehicle.heat, .vehicle.defrost { --glow: var(--lm-orange); }
      .vehicle.cool, .vehicle.driving { --glow: var(--lm-blue); }
      .vehicle.fan { --glow: var(--lm-teal); }
      svg.car { width: 100%; height: auto; max-height: 230px; display: block; overflow: visible; }
      .paint-top { stop-color: color-mix(in srgb, var(--primary-text-color) 30%, var(--card-background-color, #fff)); }
      .paint-mid { stop-color: color-mix(in srgb, var(--primary-text-color) 18%, var(--card-background-color, #fff)); }
      .paint-bottom { stop-color: color-mix(in srgb, var(--primary-text-color) 42%, var(--card-background-color, #fff)); }
      .glass-a { stop-color: #1f2a38; } .glass-b { stop-color: #4c6a8a; }
      .paint { fill: url(#lm-paint) #9aa0a8; stroke: color-mix(in srgb, var(--primary-text-color) 30%, transparent); stroke-width: 1.2; }
      .glass { fill: url(#lm-glass) #2c3e50; stroke: color-mix(in srgb, var(--primary-text-color) 25%, transparent); stroke-width: 1; transition: fill-opacity .6s; }
      .seam { fill: none; stroke: color-mix(in srgb, var(--primary-text-color) 22%, transparent); stroke-width: 1; }
      .handle, .mirror { fill: color-mix(in srgb, var(--primary-text-color) 40%, transparent); }
      .headlight { fill: #e8eef5; transition: fill .4s, filter .4s; }
      .taillight { fill: #c0392b; opacity: .85; }
      .port { fill: color-mix(in srgb, var(--primary-text-color) 30%, transparent); transition: fill .4s; }
      .tire { fill: #1d1f22; stroke: #3a3d42; stroke-width: 2; }
      .rim-disc { fill: #8b9198; stroke: #c3c8ce; stroke-width: 1.4; }
      .spokes { stroke: #e3e7eb; stroke-width: 3; stroke-linecap: round; }
      .hub { fill: #50565d; }
      .rim { transform-box: fill-box; transform-origin: center; }
      .shadow { fill: url(#lm-shadow) rgba(0,0,0,.25); }
      .ground { stroke: color-mix(in srgb, var(--primary-text-color) 12%, transparent); stroke-width: 1; }
      .road { stroke: color-mix(in srgb, var(--primary-text-color) 18%, transparent); stroke-width: 3; stroke-dasharray: 18 22; stroke-linecap: round; opacity: 0; transition: opacity .5s; }
      .door-fx, .trunk-fx { fill: var(--lm-orange); opacity: 0; transition: opacity .4s; }
      .sentry-eye { fill: var(--lm-red); opacity: 0; }
      .wallbox { opacity: 0; transition: opacity .6s; }
      .wb-body { fill: color-mix(in srgb, var(--primary-text-color) 22%, var(--card-background-color, #fff)); stroke: color-mix(in srgb, var(--primary-text-color) 35%, transparent); stroke-width: 1; }
      .wb-holster { fill: color-mix(in srgb, var(--primary-text-color) 35%, transparent); }
      .wb-led { fill: color-mix(in srgb, var(--primary-text-color) 30%, transparent); }
      .cable { fill: none; stroke: #2b2f33; stroke-width: 4; stroke-linecap: round; opacity: 0; transition: opacity .6s; }
      .energy { fill: none; stroke: var(--lm-green); stroke-width: 3; stroke-linecap: round; stroke-dasharray: 3 11; opacity: 0; filter: drop-shadow(0 0 3px var(--lm-green)); }
      .heat-wave { fill: none; stroke: var(--lm-orange); stroke-width: 2.4; stroke-linecap: round; opacity: 0; }
      .snow { fill: none; stroke: var(--lm-blue); stroke-width: 1.8; stroke-linecap: round; opacity: 0; transform-box: fill-box; transform-origin: center; }
      .breeze { fill: none; stroke: var(--lm-teal); stroke-width: 2; stroke-linecap: round; opacity: 0; }
      .photo { position: relative; padding: 4px 0 10px; }
      .photo .fx-layer { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
      .driving .photo .stack { animation: lm-bounce .9s ease-in-out infinite; }

      .plugged .wallbox, .plugged .cable { opacity: 1; }
      .charging .energy { opacity: 1; animation: lm-energy var(--flow, 1.2s) linear infinite; }
      .charging .wb-led, .charging .port { fill: var(--lm-green); animation: lm-breathe 1.4s ease-in-out infinite; }
      .driving .road { opacity: 1; animation: lm-road .55s linear infinite; }
      .driving .rim { animation: lm-spin .6s linear infinite reverse; }
      .driving .body, .driving .picture { animation: lm-bounce .9s ease-in-out infinite; }
      .awake .headlight { fill: #fff6c4; filter: drop-shadow(0 0 6px #fff1a8); }
      .heat .heat-wave, .defrost .heat-wave { animation: lm-rise 2.2s ease-in-out infinite; }
      .cool .snow { animation: lm-snow 2.6s linear infinite; }
      .fan .breeze { animation: lm-breeze 2s ease-in-out infinite; }
      .defrost .glass.front { fill: var(--lm-orange); fill-opacity: .55; animation: lm-breathe 1.6s ease-in-out infinite; }
      .door-front .door-fx.front, .door-rear .door-fx.rear, .trunk-open .trunk-fx { opacity: .45; animation: lm-blink 1.4s ease-in-out infinite; }
      .windows-open .glass { fill-opacity: .25; stroke: var(--lm-orange); stroke-dasharray: 3 3; }
      .sentry .sentry-eye { opacity: 1; animation: lm-breathe 1.2s ease-in-out infinite; }
      .unlocked .handle { fill: var(--lm-orange); }

      .soc { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 14px; margin: 4px 0 2px; }
      .soc-value { font-size: 2.5rem; font-weight: 700; line-height: 1; letter-spacing: -1px; color: var(--primary-text-color); cursor: pointer; }
      .soc-value small { font-size: 1rem; font-weight: 500; color: var(--secondary-text-color); margin-left: 2px; letter-spacing: 0; }
      .bar { position: relative; height: 12px; border-radius: 999px; background: color-mix(in srgb, var(--primary-text-color) 10%, transparent); cursor: pointer; margin-top: 14px; }
      .bar .fill { position: absolute; inset: 0 auto 0 0; border-radius: inherit; background: linear-gradient(90deg, var(--soc-a), var(--soc-b)); transition: width 1.2s cubic-bezier(.2,.8,.2,1); animation: lm-grow-x 1.2s cubic-bezier(.2,.8,.2,1); transform-origin: left; }
      .charging .bar .fill { background-image: repeating-linear-gradient(-45deg, rgba(255,255,255,.32) 0 7px, transparent 7px 14px), linear-gradient(90deg, var(--soc-a), var(--soc-b)); background-size: 19.8px 19.8px, 100% 100%; animation: lm-stripes .9s linear infinite; box-shadow: 0 0 12px color-mix(in srgb, var(--lm-green) 50%, transparent); }
      .bar .limit { position: absolute; top: -4px; bottom: -4px; width: 3px; border-radius: 2px; background: var(--primary-text-color); opacity: .6; transform: translateX(-50%); }
      .bar .limit::after { content: attr(data-label); position: absolute; bottom: calc(100% + 2px); left: 50%; transform: translateX(-50%); font-size: .68rem; color: var(--secondary-text-color); white-space: nowrap; }
      .range { text-align: right; color: var(--secondary-text-color); font-size: .85rem; cursor: pointer; white-space: nowrap; }
      .range b { font-size: 1.45rem; color: var(--primary-text-color); font-weight: 600; }
      .range span { display: block; font-size: .72rem; }

      @keyframes lm-energy { to { stroke-dashoffset: -28; } }
      @keyframes lm-road { to { stroke-dashoffset: 40; } }
      @keyframes lm-bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-1.2px); } }
      @keyframes lm-rise { 0% { opacity: 0; transform: translateY(0); } 30% { opacity: .9; } 100% { opacity: 0; transform: translateY(-10px); } }
      @keyframes lm-snow { 0% { opacity: 0; transform: translateY(-4px) rotate(0); } 25% { opacity: .9; } 100% { opacity: 0; transform: translateY(20px) rotate(120deg); } }
      @keyframes lm-breeze { 0% { opacity: 0; transform: translateX(-6px); } 40% { opacity: .9; } 100% { opacity: 0; transform: translateX(18px); } }
      @keyframes lm-blink { 0%, 100% { opacity: .15; } 50% { opacity: .55; } }
      @keyframes lm-stripes { to { background-position: 19.8px 0, 0 0; } }
    `;
  }
}

// ---------------------------------------------------------------------------
// Charging card
// ---------------------------------------------------------------------------

class LeapmotorChargingCard extends LeapmotorBaseCard {
  static get editorSchema() {
    return [
      { name: "device_id", selector: { device: { integration: DOMAIN } } },
      { name: "wallbox_entity", selector: { entity: { domain: "sensor", device_class: "power" } } },
      { name: "solar_entity", selector: { entity: { domain: "sensor", device_class: "power" } } },
    ];
  }

  extraEntities() {
    return [this._config.wallbox_entity, this._config.solar_entity].filter(Boolean);
  }

  body() {
    const local = this._local || {};
    const soc = this.n("sensor.soc");
    const limit = local.limit ?? this.n("number.charge_limit");
    const chargingState = this.v("sensor.charging_state");
    const charging = chargingState === "charging" || this.on("binary_sensor.charging");
    const plugged =
      this.on("binary_sensor.plugged_in") ||
      ["plugged_in", "scheduled", "paused", "finished", "charging"].includes(chargingState);
    const power = this.n("sensor.charging_power");
    const wallboxState = this.extra(this._config.wallbox_entity);
    const wallbox = this.kw(wallboxState);
    const solarState = this.extra(this._config.solar_entity);
    const solar = this.kw(solarState);
    const flowPower = charging ? power ?? wallbox : null;
    const speed = flowPower ? clamp(2.6 - flowPower / 20, 0.35, 2.4).toFixed(2) : "1.6";
    const [socA, socB] = socColors(soc);

    const statusText = chargingState ? this.formatted("sensor.charging_state") : plugged ? this.t("plugged") : this.t("unplugged");
    const stateIcon = charging ? "mdi:battery-charging-high" : plugged ? "mdi:ev-plug-type2" : "mdi:power-plug-off-outline";
    const badge = `<div class="badge state ${charging ? "is-charging" : ""}"${this.more("sensor.charging_state")}><ha-icon icon="${stateIcon}"></ha-icon>${esc(statusText)}</div>`;

    // The charger node shows the wallbox meter if there is one, else what the car reports.
    const sourceValue = wallboxState ? this.unit(wallbox, "kW", 1) : this.unit(charging ? power : 0, "kW", 1);
    const sourceMore = wallboxState ? ` data-more="${esc(this._config.wallbox_entity)}"` : this.more("sensor.charging_power");

    const tiles = [];
    const tile = (key, label, value) => tiles.push(`<div class="stat"${this.more(key)}><span>${esc(label)}</span><b>${esc(value)}</b></div>`);
    if (wallboxState && this.has("sensor.charging_power")) tile("sensor.charging_power", this.t("power"), this.unit(power, "kW", 1));
    if (charging && this.has("sensor.battery_current")) tile("sensor.battery_current", this.t("current"), this.unit(Math.abs(this.n("sensor.battery_current") ?? 0), "A", 1));
    if (charging && this.has("sensor.battery_voltage")) tile("sensor.battery_voltage", this.t("voltage"), this.unit(this.n("sensor.battery_voltage"), "V"));
    if (this.has("sensor.charge_time_remaining")) tile("sensor.charge_time_remaining", this.t("remaining"), charging ? this.duration(this.n("sensor.charge_time_remaining")) : "–");
    if (this.has("sensor.charge_finish_time")) tile("sensor.charge_finish_time", this.t("finished_at"), this.clock(this.v("sensor.charge_finish_time")));
    if (this.has("sensor.energy_to_limit")) tile("sensor.energy_to_limit", this.t("to_limit"), this.unit(this.n("sensor.energy_to_limit"), "kWh", 1));
    if (this.has("sensor.battery_temperature")) tile("sensor.battery_temperature", this.t("battery_temp"), this.unit(this.n("sensor.battery_temperature"), "°C"));
    if (solarState) {
      tiles.push(`<div class="stat" data-more="${esc(this._config.solar_entity)}"><span>${esc(this.t("solar"))}</span><b>${esc(this.unit(solar, "kW", 1))}</b></div>`);
    }

    const rows = [];
    if (this.has("number.charge_limit")) {
      const state = this.st("number.charge_limit");
      const min = state.attributes.min ?? 20;
      const max = state.attributes.max ?? 100;
      const step = state.attributes.step ?? 1;
      rows.push(`
        <div class="row column">
          <div class="row-head"><span class="label"><ha-icon icon="mdi:battery-arrow-up-outline"></ha-icon>${esc(this.t("charge_limit"))}</span><span class="value" id="limit-value">${this.num(limit)} %</span></div>
          <input type="range" min="${min}" max="${max}" step="${step}" value="${limit ?? max}" data-change="limit" data-live="limit-value"${this._pending.has("limit") ? " disabled" : ""}>
        </div>`);
    }
    if (this.has("switch.charge_schedule")) {
      const start = local.start ?? (this.v("time.charge_schedule_start") || "").slice(0, 5);
      const end = local.end ?? (this.v("time.charge_schedule_end") || "").slice(0, 5);
      rows.push(`
        <div class="row">
          <span class="label"><ha-icon icon="mdi:calendar-clock"></ha-icon>${esc(this.t("schedule"))}</span>
          <span class="times">
            ${this.has("time.charge_schedule_start") ? `<input type="time" value="${esc(start)}" data-change="schedule_start">` : ""}
            ${this.has("time.charge_schedule_end") ? `<span class="muted">–</span><input type="time" value="${esc(end)}" data-change="schedule_end">` : ""}
            ${this.toggle("schedule", this.on("switch.charge_schedule"))}
          </span>
        </div>`);
    }

    const buttons = [];
    if (this.has("switch.charging")) {
      buttons.push(
        this.button(
          "charge",
          charging ? "mdi:stop-circle-outline" : "mdi:play-circle-outline",
          charging ? this.t("stop_charging") : this.t("start_charging"),
          { disabled: !plugged && !charging, active: charging, color: "var(--lm-green)" },
        ),
      );
    }
    if (this.has("button.unlock_charger")) {
      buttons.push(this.button("release", "mdi:ev-plug-type2", this.t("release_plug"), { confirm: true, disabled: !plugged }));
    }
    if (this.has("switch.battery_preheat")) {
      const on = this.on("switch.battery_preheat");
      buttons.push(this.button("preheat", "mdi:heat-wave", this.t("battery_preheat"), { active: on, color: "var(--lm-orange)" }));
    }

    let last = "";
    if (this.has("sensor.last_charge_energy") && this.v("sensor.last_charge_energy")) {
      const type = this.attr("sensor.last_charge_energy", "type");
      const end = this.attr("sensor.last_charge_energy", "end");
      last = `<div class="last"${this.more("sensor.last_charge_energy")}><ha-icon icon="mdi:history"></ha-icon>${esc(this.t("last_charge"))}: <b>${esc(this.unit(this.n("sensor.last_charge_energy"), "kWh", 1))}</b>${type ? ` · ${esc(String(type).toUpperCase())}` : ""}${end ? ` · ${esc(this.ago(end))}` : ""}</div>`;
    }

    return `
      <ha-card class="${charging ? "active" : ""}${plugged ? " plugged" : ""}" style="--soc-a:${socA};--soc-b:${socB};--speed:${speed}s;--soc:${clamp(soc ?? 0, 0, 100)}%">
        <div class="card">
          ${this.header("mdi:ev-station", this.t("charging"), "", badge)}
          <div class="flow">
            <div class="node source"${sourceMore}><div class="icon-wrap"><ha-icon icon="mdi:ev-station"></ha-icon></div><span>${esc(this.t("wallbox"))}</span><b>${esc(sourceValue)}</b></div>
            <svg class="pipe" viewBox="0 0 200 24" preserveAspectRatio="none" aria-hidden="true">
              <path class="track" d="M6 12 H194"></path>
              <path class="dash" d="M6 12 H194"></path>
            </svg>
            <div class="node target"${this.more("sensor.soc")}><div class="battery"><div class="lvl"></div><div class="pct">${this.num(soc)} %</div></div><span>${esc(this.t("vehicle_node"))}</span><b>${limit !== null ? `→ ${this.num(limit)} %` : "&nbsp;"}</b></div>
          </div>
          <div class="stats">${tiles.join("")}</div>
          <div class="controls">${rows.join("")}</div>
          ${buttons.length ? `<div class="actions">${buttons.join("")}</div>${this.hint()}` : ""}
          ${last}
        </div>
      </ha-card>`;
  }

  actions() {
    return {
      charge: () => {
        const charging = this.v("sensor.charging_state") === "charging" || this.on("binary_sensor.charging");
        return this.entityCall("switch.charging", "switch", charging ? "turn_off" : "turn_on");
      },
      release: () => this.entityCall("button.unlock_charger", "button", "press"),
      preheat: () => this.entityCall("switch.battery_preheat", "switch", this.on("switch.battery_preheat") ? "turn_off" : "turn_on"),
      schedule: () => this.entityCall("switch.charge_schedule", "switch", this.on("switch.charge_schedule") ? "turn_off" : "turn_on"),
      limit: (el) => this.withLocal("limit", Number(el.value), () =>
        this.entityCall("number.charge_limit", "number", "set_value", { value: Number(el.value) })),
      schedule_start: (el) => el.value && this.withLocal("start", el.value, () =>
        this.entityCall("time.charge_schedule_start", "time", "set_value", { time: `${el.value}:00` })),
      schedule_end: (el) => el.value && this.withLocal("end", el.value, () =>
        this.entityCall("time.charge_schedule_end", "time", "set_value", { time: `${el.value}:00` })),
    };
  }

  /** Show a value the user just chose until the command has finished. */
  async withLocal(key, value, call) {
    this._local = { ...(this._local || {}), [key]: value };
    this.invalidate();
    try {
      await call();
    } finally {
      const { [key]: _done, ...rest } = this._local || {};
      this._local = Object.keys(rest).length ? rest : null;
    }
  }

  static get styles() {
    return `
      .badge.state ha-icon { --mdc-icon-size: 16px; }
      .badge.state.is-charging { color: var(--lm-green); background: color-mix(in srgb, var(--lm-green) 14%, transparent); }
      .badge.state.is-charging ha-icon { animation: lm-pulse 1.6s ease-in-out infinite; }
      .flow { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; margin: 18px 0 14px; }
      .node { display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 84px; font-size: .76rem; color: var(--secondary-text-color); cursor: pointer; }
      .node b { color: var(--primary-text-color); font-size: .95rem; font-weight: 600; }
      .icon-wrap { width: 58px; height: 58px; border-radius: 18px; display: grid; place-items: center; background: color-mix(in srgb, var(--primary-color) 13%, transparent); transition: background .5s, box-shadow .5s; }
      .icon-wrap ha-icon { --mdc-icon-size: 32px; color: var(--primary-color); }
      .active .icon-wrap { background: color-mix(in srgb, var(--lm-green) 18%, transparent); box-shadow: 0 0 0 0 color-mix(in srgb, var(--lm-green) 40%, transparent); animation: lm-ring 2s ease-out infinite; }
      .active .icon-wrap ha-icon { color: var(--lm-green); }
      .pipe { width: 100%; height: 24px; overflow: visible; }
      .pipe .track { stroke: color-mix(in srgb, var(--primary-text-color) 12%, transparent); stroke-width: 8; stroke-linecap: round; fill: none; }
      .plugged .pipe .track { stroke: color-mix(in srgb, var(--lm-green) 22%, transparent); }
      .pipe .dash { stroke: var(--lm-green); stroke-width: 8; stroke-linecap: round; fill: none; stroke-dasharray: 1 15; opacity: 0; }
      .active .pipe .dash { opacity: 1; animation: lm-flow var(--speed, 1.2s) linear infinite; filter: drop-shadow(0 0 4px var(--lm-green)); }
      .battery { width: 74px; height: 38px; border-radius: 10px; border: 3px solid color-mix(in srgb, var(--primary-text-color) 45%, transparent); position: relative; padding: 3px; box-sizing: border-box; margin: 10px 8px 0 0; }
      .battery::after { content: ""; position: absolute; right: -9px; top: 10px; width: 5px; height: 12px; border-radius: 0 3px 3px 0; background: color-mix(in srgb, var(--primary-text-color) 45%, transparent); }
      .battery .lvl { height: 100%; width: var(--soc); border-radius: 5px; background: linear-gradient(90deg, var(--soc-a), var(--soc-b)); position: relative; overflow: hidden; transition: width 1.2s cubic-bezier(.2,.8,.2,1); }
      .active .battery .lvl::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,.65), transparent); transform: translateX(-100%); animation: lm-shine 1.8s ease-in-out infinite; }
      .battery .pct { position: absolute; inset: 0; display: grid; place-items: center; font-weight: 700; font-size: .84rem; color: var(--primary-text-color); text-shadow: 0 0 3px var(--card-background-color, #fff); }
      .controls { margin-top: 10px; }
      .row.column { display: block; }
      .row-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
      .times { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
      .actions { margin-top: 12px; }
      .last { display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: .82rem; color: var(--secondary-text-color); cursor: pointer; }
      .last ha-icon { --mdc-icon-size: 16px; }
      .last b { color: var(--primary-text-color); }
      @keyframes lm-flow { to { stroke-dashoffset: -32; } }
      @keyframes lm-shine { to { transform: translateX(100%); } }
      @keyframes lm-ring { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--lm-green) 45%, transparent); } 80%, 100% { box-shadow: 0 0 0 12px transparent; } }
    `;
  }
}

// ---------------------------------------------------------------------------
// Climate card
// ---------------------------------------------------------------------------

const DIAL_LENGTH = 326.7;

class LeapmotorClimateCard extends LeapmotorBaseCard {
  static instantActions = ["temp_up", "temp_down"];

  constructor() {
    super();
    this._local = null;
    this._tempTimer = null;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._tempTimer);
  }

  seat(seat, label) {
    const heatKey = `select.seat_heat_${seat}`;
    const ventKey = `select.seat_ventilation_${seat}`;
    if (!this.has(heatKey) && !this.has(ventKey)) return "";
    const levelOf = (key) => Math.max(0, LEVELS.indexOf(this.v(key) || "off"));
    const group = (key, kind, icon) => {
      if (!this.has(key)) return "";
      const level = levelOf(key);
      const dots = [1, 2, 3]
        .map((value) => `<button class="lvl-dot${value <= level ? " on" : ""}" data-action="seat" data-entity="${esc(key)}" data-level="${value}" aria-label="${esc(this.t("level"))} ${value}"></button>`)
        .join("");
      return `<div class="seat-group ${kind}${level ? " active" : ""}${this._pending.has("seat") ? " pending" : ""}"><ha-icon icon="${icon}"${this.more(key)}></ha-icon><div class="dots">${dots}</div></div>`;
    };
    return `<div class="seat"><span class="seat-name">${esc(label)}</span>${group(heatKey, "heat", "mdi:car-seat-heater")}${group(ventKey, "vent", "mdi:car-seat-cooler")}</div>`;
  }

  body() {
    const state = this.st("climate.climate");
    if (!state) {
      return `<ha-card><div class="empty"><ha-icon icon="mdi:air-conditioner"></ha-icon><span>${esc(this.t("climate"))}: –</span></div></ha-card>`;
    }
    const mode = this.v("climate.climate") || "off";
    const action = state.attributes.hvac_action;
    const on = mode !== "off";
    const min = state.attributes.min_temp ?? 18;
    const max = state.attributes.max_temp ?? 32;
    const target = this._local?.temperature ?? state.attributes.temperature ?? 22;
    const fan = Number(state.attributes.fan_mode) || 0;
    const interior = this.n("sensor.interior_temperature") ?? state.attributes.current_temperature;
    const outdoor = this.n("sensor.outdoor_temperature");
    const fraction = clamp((target - min) / (max - min), 0, 1);
    let kind = "off";
    if (on) {
      if (action === "defrosting") kind = "defrost";
      else if (mode === "heat" || action === "heating") kind = "heat";
      else if (mode === "cool" || action === "cooling") kind = "cool";
      else kind = "fan";
    }
    const statusText = on
      ? `${this.t({ heat: "heating", cool: "cooling", fan: "ventilating", defrost: "defrosting" }[kind])} · ${this.num(target)} °C`
      : this.t("climate_off");

    const temps = [
      interior !== null && interior !== undefined ? `<div class="temp"${this.more("sensor.interior_temperature")}><span>${esc(this.t("inside"))}</span><b>${esc(this.unit(interior, "°C", 1))}</b></div>` : "",
      outdoor !== null ? `<div class="temp"${this.more("sensor.outdoor_temperature")}><span>${esc(this.t("outside"))}</span><b>${esc(this.unit(outdoor, "°C", 1))}</b></div>` : "",
    ].join("");

    const modeButton = (value, icon, label) =>
      this.button(`mode_${value}`, icon, label, {
        active: mode === value,
        color: { heat: "var(--lm-orange)", cool: "var(--lm-blue)", fan_only: "var(--lm-teal)", off: "var(--secondary-text-color)" }[value],
      });
    const fanBars = [1, 2, 3, 4, 5, 6, 7]
      .map((level) => `<button class="fan-bar${level <= fan ? " on" : ""}" style="height:${8 + level * 3}px" data-action="fan" data-level="${level}" aria-label="${esc(this.t("fan"))} ${level}"></button>`)
      .join("");

    const presets = [];
    if (this.has("button.quick_cool")) presets.push(this.button("quick_cool", "mdi:snowflake", this.t("quick_cool"), { color: "var(--lm-blue)" }));
    if (this.has("button.quick_heat")) presets.push(this.button("quick_heat", "mdi:fire", this.t("quick_heat"), { color: "var(--lm-orange)" }));
    if (this.has("button.windshield_defrost")) presets.push(this.button("defrost", "mdi:car-defrost-front", this.t("defrost"), { color: "var(--lm-orange)" }));

    const comfort = [];
    const seats = this.seat("driver", this.t("driver")) + this.seat("passenger", this.t("passenger"));
    if (seats) comfort.push(`<div class="seats">${seats}</div>`);
    const switches = [];
    const switchRow = (key, icon, label, action) => {
      if (!this.has(key)) return;
      switches.push(`<div class="row"><span class="label"${this.more(key)}><ha-icon icon="${icon}" class="${this.on(key) ? "warm" : ""}"></ha-icon>${esc(label)}</span>${this.toggle(action, this.on(key))}</div>`);
    };
    switchRow("switch.steering_wheel_heat", "mdi:steering", this.t("steering_wheel"), "wheel");
    switchRow("switch.mirror_heat", "mdi:mirror-rectangle", this.t("mirrors"), "mirror");
    if (switches.length) comfort.push(`<div class="switches">${switches.join("")}</div>`);

    return `
      <ha-card class="climate-card ${kind}">
        <div class="card">
          ${this.header("mdi:air-conditioner", this.t("climate"), esc(statusText), `<div class="temps">${temps}</div>`)}
          <div class="dial-wrap">
            <button class="round" data-action="temp_down" aria-label="-"${target <= min ? " disabled" : ""}><ha-icon icon="mdi:minus"></ha-icon></button>
            <div class="dial"${this.more("climate.climate")}>
              <svg viewBox="0 0 200 160" aria-hidden="true">
                <path class="dial-track" d="M32.45 139 A78 78 0 1 1 167.55 139"></path>
                <path class="dial-value" d="M32.45 139 A78 78 0 1 1 167.55 139" style="stroke-dasharray:${(DIAL_LENGTH * fraction).toFixed(1)} 400"></path>
              </svg>
              <div class="dial-center"><div class="dial-temp">${this.num(target)}<small>°C</small></div><span>${esc(this.t("target"))}</span><ha-icon class="dial-icon" icon="${{ heat: "mdi:fire", cool: "mdi:snowflake", fan: "mdi:fan", defrost: "mdi:car-defrost-front", off: "mdi:power" }[kind]}"></ha-icon></div>
            </div>
            <button class="round" data-action="temp_up" aria-label="+"${target >= max ? " disabled" : ""}><ha-icon icon="mdi:plus"></ha-icon></button>
          </div>
          <div class="actions modes">
            ${modeButton("heat", "mdi:fire", this.t("heat"))}
            ${modeButton("cool", "mdi:snowflake", this.t("cool"))}
            ${modeButton("fan_only", "mdi:fan", this.t("ventilate"))}
            ${modeButton("off", "mdi:power", this.t("off"))}
          </div>
          <div class="fan-row"><span class="label"><ha-icon icon="mdi:fan"></ha-icon>${esc(this.t("fan"))}</span><div class="fan-bars${this._pending.has("fan") ? " pending" : ""}">${fanBars}</div></div>
          ${presets.length ? `<div class="actions presets">${presets.join("")}</div>` : ""}
          ${comfort.length ? `<div class="section-title">${esc(this.t("seats"))}</div>${comfort.join("")}` : ""}
        </div>
      </ha-card>`;
  }

  _changeTemperature(delta) {
    const state = this.st("climate.climate");
    if (!state) return;
    const min = state.attributes.min_temp ?? 18;
    const max = state.attributes.max_temp ?? 32;
    const current = this._local?.temperature ?? state.attributes.temperature ?? 22;
    this._local = { temperature: clamp(Math.round(current + delta), min, max) };
    this.invalidate();
    // Collect quick taps into one command: every command goes to the car.
    clearTimeout(this._tempTimer);
    this._tempTimer = setTimeout(() => {
      const temperature = this._local?.temperature;
      this.run("temperature", async () => {
        try {
          await this.entityCall("climate.climate", "climate", "set_temperature", { temperature });
        } finally {
          this._local = null;
        }
      });
    }, 1400);
  }

  actions() {
    return {
      temp_up: () => this._changeTemperature(1),
      temp_down: () => this._changeTemperature(-1),
      mode_heat: () => this.entityCall("climate.climate", "climate", "set_hvac_mode", { hvac_mode: "heat" }),
      mode_cool: () => this.entityCall("climate.climate", "climate", "set_hvac_mode", { hvac_mode: "cool" }),
      mode_fan_only: () => this.entityCall("climate.climate", "climate", "set_hvac_mode", { hvac_mode: "fan_only" }),
      mode_off: () => this.entityCall("climate.climate", "climate", "turn_off"),
      fan: (el) => this.entityCall("climate.climate", "climate", "set_fan_mode", { fan_mode: el.getAttribute("data-level") }),
      quick_cool: () => this.entityCall("button.quick_cool", "button", "press"),
      quick_heat: () => this.entityCall("button.quick_heat", "button", "press"),
      defrost: () => this.entityCall("button.windshield_defrost", "button", "press"),
      wheel: () => this.entityCall("switch.steering_wheel_heat", "switch", this.on("switch.steering_wheel_heat") ? "turn_off" : "turn_on"),
      mirror: () => this.entityCall("switch.mirror_heat", "switch", this.on("switch.mirror_heat") ? "turn_off" : "turn_on"),
      seat: (el) => {
        const key = el.getAttribute("data-entity");
        const level = Number(el.getAttribute("data-level"));
        const current = Math.max(0, LEVELS.indexOf(this.v(key) || "off"));
        const option = LEVELS[current === level ? 0 : level];
        return this.entityCall(key, "select", "select_option", { option });
      },
    };
  }

  static get styles() {
    return `
      .climate-card.heat, .climate-card.defrost { --dial: var(--lm-orange); }
      .climate-card.cool { --dial: var(--lm-blue); }
      .climate-card.fan { --dial: var(--lm-teal); }
      .climate-card.off { --dial: color-mix(in srgb, var(--primary-text-color) 35%, transparent); }
      .temps { display: flex; gap: 14px; text-align: right; }
      .temp { cursor: pointer; } .temp span { display: block; font-size: .72rem; color: var(--secondary-text-color); } .temp b { font-size: 1rem; }
      .dial-wrap { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; margin: 8px 0 4px; }
      .round { width: 44px; height: 44px; border-radius: 50%; border: none; background: var(--lm-soft); color: var(--primary-text-color); cursor: pointer; display: grid; place-items: center; transition: transform .15s, background .2s; }
      .round:hover { background: color-mix(in srgb, var(--dial) 18%, transparent); }
      .round:active { transform: scale(.92); }
      .round[disabled] { opacity: .35; cursor: default; }
      .dial { position: relative; max-width: 230px; width: 100%; margin: 0 auto; cursor: pointer; }
      .dial svg { width: 100%; display: block; }
      .dial-track { fill: none; stroke: color-mix(in srgb, var(--primary-text-color) 10%, transparent); stroke-width: 12; stroke-linecap: round; }
      .dial-value { fill: none; stroke: var(--dial); stroke-width: 12; stroke-linecap: round; transition: stroke-dasharray .6s cubic-bezier(.2,.8,.2,1), stroke .6s; filter: drop-shadow(0 0 6px color-mix(in srgb, var(--dial) 55%, transparent)); }
      .dial-center { position: absolute; inset: 22% 0 0; display: flex; flex-direction: column; align-items: center; }
      .dial-temp { font-size: 2.6rem; font-weight: 700; line-height: 1; color: var(--primary-text-color); }
      .dial-temp small { font-size: 1rem; font-weight: 500; color: var(--secondary-text-color); margin-left: 2px; }
      .dial-center span { font-size: .75rem; color: var(--secondary-text-color); margin-top: 2px; }
      .dial-icon { --mdc-icon-size: 22px; margin-top: 6px; color: var(--dial); }
      .heat .dial-icon, .defrost .dial-icon { animation: lm-flicker 1.3s ease-in-out infinite; }
      .cool .dial-icon { animation: lm-spin 6s linear infinite; }
      .fan .dial-icon { animation: lm-spin 1.6s linear infinite; }
      .modes { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .presets { grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); }
      .modes .action.on ha-icon { animation: lm-pulse 2s ease-in-out infinite; }
      .modes [data-action=mode_fan_only].on ha-icon { animation: lm-spin 1.6s linear infinite; }
      .modes [data-action=mode_cool].on ha-icon { animation: lm-spin 6s linear infinite; }
      .modes [data-action=mode_heat].on ha-icon { animation: lm-flicker 1.3s ease-in-out infinite; }
      .fan-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 14px 0 4px; }
      .fan-row .label { display: flex; align-items: center; gap: 8px; color: var(--secondary-text-color); font-size: .88rem; }
      .fan-row .label ha-icon { --mdc-icon-size: 20px; }
      .fan-bars { display: flex; align-items: flex-end; gap: 5px; height: 32px; }
      .fan-bars.pending { opacity: .5; }
      .fan-bar { width: 14px; border: none; border-radius: 4px; background: color-mix(in srgb, var(--primary-text-color) 14%, transparent); cursor: pointer; padding: 0; transition: background .3s, transform .15s; }
      .fan-bar.on { background: var(--dial); }
      .fan-bar:hover { transform: scaleY(1.08); }
      .presets { margin-top: 12px; }
      .seats { display: grid; gap: 8px; }
      .seat { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 12px; background: var(--lm-softer); }
      .seat-name { font-size: .88rem; color: var(--primary-text-color); }
      .seat-group { display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 999px; background: var(--lm-soft); }
      .seat-group ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); cursor: pointer; }
      .seat-group.heat.active ha-icon { color: var(--lm-orange); animation: lm-flicker 1.4s ease-in-out infinite; }
      .seat-group.vent.active ha-icon { color: var(--lm-blue); animation: lm-pulse 2s ease-in-out infinite; }
      .seat-group.pending { opacity: .5; }
      .dots { display: flex; gap: 4px; }
      .lvl-dot { width: 10px; height: 10px; border-radius: 50%; border: none; padding: 0; cursor: pointer; background: color-mix(in srgb, var(--primary-text-color) 20%, transparent); transition: background .3s, transform .15s; }
      .lvl-dot:hover { transform: scale(1.25); }
      .seat-group.heat .lvl-dot.on { background: var(--lm-orange); }
      .seat-group.vent .lvl-dot.on { background: var(--lm-blue); }
      .switches { margin-top: 6px; }
      .switches ha-icon.warm { color: var(--lm-orange); animation: lm-flicker 1.4s ease-in-out infinite; }
    `;
  }
}

// ---------------------------------------------------------------------------
// Status card (top view: doors, windows, tires)
// ---------------------------------------------------------------------------

class LeapmotorStatusCard extends LeapmotorBaseCard {
  static get editorSchema() {
    return [
      { name: "device_id", selector: { device: { integration: DOMAIN } } },
      { name: "show_picture", selector: { boolean: {} } },
      { name: "image", selector: { text: {} } },
    ];
  }

  pressureClass(value) {
    // Cold tyres read lower; only clearly low pressures are marked.
    if (value === null) return "";
    if (value < 1.8) return "bad";
    if (value < 2.0) return "low";
    return "good";
  }

  /** The vehicle picture for the current state: null (no pictures), {loading} or a picture. */
  statusPhoto() {
    if (this._config.image) return { single: this._config.image };
    if (this._config.show_picture === false) return null;
    return this.appPicture();
  }

  photoBody(photo, { tires, label, locked, list }) {
    let picture;
    if (photo.loading) picture = '<div class="photo-loading"></div>';
    else if (photo.single) picture = `<div class="stack"><img class="layer base" src="${esc(photo.single)}" alt=""></div>`;
    else picture = this.pictureStack(photo);
    const lockState = this.v("lock.lock");
    const lock = lockState
      ? `<div class="lock-chip ${locked ? "locked" : "unlocked"}"${this.more("lock.lock")}><ha-icon icon="${locked ? "mdi:lock" : "mdi:lock-open-variant"}"></ha-icon>${esc(this.t(locked ? "locked" : "unlocked"))}</div>`
      : "";
    const tireTiles = tires
      .filter(({ wheel }) => this.has(`sensor.tire_pressure_${wheel}`))
      .map(
        ({ wheel, value }) =>
          `<div class="tire-tile ${this.pressureClass(value)}"${this.more(`sensor.tire_pressure_${wheel}`)}><ha-icon icon="mdi:tire"></ha-icon><span>${esc(label(wheel))}</span><b>${value !== null ? `${this.num(value, 1)} bar` : "–"}</b></div>`,
      )
      .join("");
    const odometer = this.n("sensor.odometer");
    return `
      <ha-card class="${locked ? "locked" : "unlocked"}">
        <div class="card">
          ${this.header("mdi:car-info", this.t("status"), odometer !== null ? `${esc(this.t("odometer"))}: ${esc(this.unit(odometer, "km"))}` : "")}
          <div class="photo-wrap">${picture}${lock}</div>
          <div class="below">
            ${tireTiles ? `<div class="tires">${tireTiles}</div>` : ""}
            <div class="list">${list.join("")}</div>
          </div>
        </div>
      </ha-card>`;
  }

  body() {
    const doors = {
      fl: this.on("binary_sensor.door_driver"),
      fr: this.on("binary_sensor.door_passenger"),
      rl: this.on("binary_sensor.door_rear_left"),
      rr: this.on("binary_sensor.door_rear_right"),
    };
    const windows = {
      fl: this.on("binary_sensor.window_driver"),
      fr: this.on("binary_sensor.window_passenger"),
      rl: this.on("binary_sensor.window_rear_left"),
      rr: this.on("binary_sensor.window_rear_right"),
    };
    const anyWindow = this.on("binary_sensor.windows") || this.v("cover.windows") === "open";
    const trunk = this.v("cover.trunk") === "open" || this.on("binary_sensor.trunk");
    const locked = this.v("lock.lock") === "locked";
    const tires = ["fl", "fr", "rl", "rr"].map((wheel) => ({ wheel, value: this.n(`sensor.tire_pressure_${wheel}`) }));
    const label = (wheel) => ({ fl: `${this.t("front")} L`, fr: `${this.t("front")} R`, rl: `${this.t("rear")} L`, rr: `${this.t("rear")} R` })[wheel];
    const pos = {
      fl: { x: 34, y: 96, anchor: "end" },
      fr: { x: 206, y: 96, anchor: "start" },
      rl: { x: 34, y: 276, anchor: "end" },
      rr: { x: 206, y: 276, anchor: "start" },
    };
    const tireText = tires
      .map(({ wheel, value }) => `<g class="tire-label ${this.pressureClass(value)}"${this.more(`sensor.tire_pressure_${wheel}`)}><text x="${pos[wheel].x}" y="${pos[wheel].y - 8}" text-anchor="${pos[wheel].anchor}" class="t-name">${esc(label(wheel))}</text><text x="${pos[wheel].x}" y="${pos[wheel].y + 10}" text-anchor="${pos[wheel].anchor}" class="t-value">${value !== null ? `${this.num(value, 1)} bar` : "–"}</text></g>`)
      .join("");
    const tireRects = tires
      .map(({ wheel, value }) => {
        const x = wheel.endsWith("l") ? 46 : 180;
        const y = wheel.startsWith("f") ? 74 : 254;
        return `<rect class="tire ${this.pressureClass(value)}" x="${x}" y="${y}" width="14" height="40" rx="5"></rect>`;
      })
      .join("");
    const winClass = (key) => (windows[key] || (anyWindow && !Object.values(windows).some(Boolean)) ? " open" : "");

    const list = [];
    const item = (key, icon, name, isOpen) => {
      if (!this.has(key)) return;
      list.push(`<div class="item${isOpen ? " open" : ""}"${this.more(key)}><ha-icon icon="${icon}"></ha-icon><span>${esc(name)}</span><b>${esc(isOpen ? this.t("open") : this.t("closed"))}</b></div>`);
    };
    item("binary_sensor.doors", "mdi:car-door", this.t("doors"), Object.values(doors).some(Boolean) || this.on("binary_sensor.doors"));
    item("cover.trunk", "mdi:car-back", this.t("trunk"), trunk);
    item("binary_sensor.windows", "mdi:window-open-variant", this.t("windows"), anyWindow);

    // Real pictures of the vehicle when there are any; the drawing is only the fallback.
    const photo = this.statusPhoto();
    if (photo) return this.photoBody(photo, { tires, label, locked, list });

    const odometer = this.n("sensor.odometer");
    return `
      <ha-card class="${locked ? "locked" : "unlocked"}">
        <div class="card">
          ${this.header("mdi:car-info", this.t("status"), odometer !== null ? `${esc(this.t("odometer"))}: ${esc(this.unit(odometer, "km"))}` : "")}
          <div class="layout">
            <svg class="top" viewBox="0 0 240 360" aria-hidden="true">
              ${tireRects}
              <path class="shell" d="M120 28 C150 28 172 36 176 60 L182 130 L182 290 C182 316 168 332 120 332 C72 332 58 316 58 290 L58 130 L64 60 C68 36 90 28 120 28 Z"></path>
              <path class="glass" d="M74 104 Q120 88 166 104 L158 140 Q120 132 82 140 Z"></path>
              <path class="roof" d="M84 142 Q120 136 156 142 L156 248 Q120 254 84 248 Z"></path>
              <path class="glass" d="M82 252 Q120 260 158 252 L164 284 Q120 294 76 284 Z"></path>
              <path class="side-window${winClass("fl")}" d="M66 146 L78 144 L78 194 L64 194 Z"></path>
              <path class="side-window${winClass("rl")}" d="M64 198 L78 198 L78 246 L66 244 Z"></path>
              <path class="side-window${winClass("fr")}" d="M174 146 L162 144 L162 194 L176 194 Z"></path>
              <path class="side-window${winClass("rr")}" d="M176 198 L162 198 L162 246 L174 244 Z"></path>
              <line class="door l${doors.fl ? " open" : ""}" x1="58" y1="140" x2="58" y2="196"></line>
              <line class="door l${doors.rl ? " open" : ""}" x1="58" y1="198" x2="58" y2="252"></line>
              <line class="door r${doors.fr ? " open" : ""}" x1="182" y1="140" x2="182" y2="196"></line>
              <line class="door r${doors.rr ? " open" : ""}" x1="182" y1="198" x2="182" y2="252"></line>
              <path class="trunk-lid${trunk ? " open" : ""}" d="M84 326 L156 326 L150 352 L90 352 Z"></path>
              <path class="lights" d="M74 40 Q84 33 96 32 M166 40 Q156 33 144 32"></path>
              <g class="lock-badge"${this.more("lock.lock")} transform="translate(120 196)">
                <circle r="17"></circle>
                <path class="shackle" d="M-6 -2 V-7 A6 6 0 0 1 6 -7 V-2"></path>
                <rect x="-8" y="-2" width="16" height="12" rx="2.5"></rect>
              </g>
              ${tireText}
            </svg>
            <div class="list">${list.join("")}</div>
          </div>
        </div>
      </ha-card>`;
  }

  static get styles() {
    return `
      .layout { display: grid; grid-template-columns: minmax(170px, 1.3fr) 1fr; gap: 12px; align-items: center; margin-top: 6px; }
      @container (max-width: 340px) { .layout { grid-template-columns: 1fr; } }
      ha-card { container-type: inline-size; }
      svg.top { width: 100%; max-height: 330px; overflow: visible; }
      .shell { fill: color-mix(in srgb, var(--primary-text-color) 13%, var(--card-background-color, #fff)); stroke: color-mix(in srgb, var(--primary-text-color) 32%, transparent); stroke-width: 1.5; }
      .glass { fill: #2c3e50; opacity: .85; }
      .roof { fill: color-mix(in srgb, var(--primary-text-color) 20%, var(--card-background-color, #fff)); }
      .side-window { fill: #34495e; opacity: .8; transition: fill .4s; }
      .side-window.open { fill: var(--lm-orange); animation: lm-breathe 1.5s ease-in-out infinite; }
      .door { stroke: color-mix(in srgb, var(--primary-text-color) 45%, transparent); stroke-width: 4; stroke-linecap: round; transform-box: view-box; transition: transform .8s cubic-bezier(.3,1.3,.6,1), stroke .3s; }
      .door.l { transform-origin: 58px 140px; }
      .door.r { transform-origin: 182px 140px; }
      .door.l + .door.l { transform-origin: 58px 198px; }
      .door.r + .door.r { transform-origin: 182px 198px; }
      .door.open { stroke: var(--lm-orange); }
      .door.l.open { transform: rotate(38deg); }
      .door.r.open { transform: rotate(-38deg); }
      .trunk-lid { fill: var(--lm-orange); opacity: 0; transition: opacity .4s; }
      .trunk-lid.open { opacity: .75; animation: lm-breathe 1.4s ease-in-out infinite; }
      .lights { fill: none; stroke: #fff4c2; stroke-width: 3; stroke-linecap: round; opacity: .7; }
      .tire { fill: #2b2e33; }
      .tire.low { fill: var(--lm-orange); } .tire.bad { fill: var(--lm-red); animation: lm-breathe 1s ease-in-out infinite; }
      .tire-label { cursor: pointer; }
      .t-name { font-size: 11px; fill: var(--secondary-text-color); }
      .t-value { font-size: 15px; font-weight: 600; fill: var(--primary-text-color); }
      .tire-label.low .t-value { fill: var(--lm-orange); } .tire-label.bad .t-value { fill: var(--lm-red); }
      .lock-badge { cursor: pointer; }
      .lock-badge circle { fill: color-mix(in srgb, var(--lm-green) 20%, var(--card-background-color, #fff)); stroke: var(--lm-green); stroke-width: 1.5; }
      .lock-badge rect { fill: var(--lm-green); }
      .lock-badge .shackle { fill: none; stroke: var(--lm-green); stroke-width: 2.4; transition: transform .5s; transform-box: fill-box; transform-origin: right bottom; }
      .unlocked .lock-badge circle { fill: color-mix(in srgb, var(--lm-orange) 20%, var(--card-background-color, #fff)); stroke: var(--lm-orange); }
      .unlocked .lock-badge rect { fill: var(--lm-orange); }
      .unlocked .lock-badge .shackle { stroke: var(--lm-orange); transform: translate(5px, -3px) rotate(28deg); }
      .list { display: grid; gap: 8px; }
      .item { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 12px; background: var(--lm-soft); cursor: pointer; font-size: .88rem; }
      .item ha-icon { --mdc-icon-size: 20px; color: var(--lm-green); }
      .item b { font-weight: 600; color: var(--secondary-text-color); }
      .item.open { background: color-mix(in srgb, var(--lm-orange) 15%, transparent); }
      .item.open ha-icon { color: var(--lm-orange); animation: lm-wiggle 2.4s ease-in-out infinite; }
      .item.open b { color: var(--lm-orange); }
      .photo-wrap { position: relative; margin: 8px 0 12px; }
      .photo-wrap .stack .base { max-height: 220px; }
      .photo-loading { aspect-ratio: 2.3 / 1; max-height: 220px; border-radius: 16px; background: linear-gradient(90deg, var(--lm-soft) 25%, color-mix(in srgb, var(--primary-text-color) 11%, transparent) 50%, var(--lm-soft) 75%); background-size: 200% 100%; animation: lm-shimmer 1.4s linear infinite; }
      .lock-chip { position: absolute; top: 0; left: 0; display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px 5px 8px; border-radius: 999px; font-size: .8rem; font-weight: 500; cursor: pointer; color: var(--lm-green); background: color-mix(in srgb, var(--lm-green) 16%, var(--card-background-color, #fff)); }
      .lock-chip ha-icon { --mdc-icon-size: 16px; }
      .lock-chip.unlocked { color: var(--lm-orange); background: color-mix(in srgb, var(--lm-orange) 16%, var(--card-background-color, #fff)); }
      .lock-chip.unlocked ha-icon { animation: lm-wiggle 2.4s ease-in-out infinite; }
      .below { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: start; }
      @container (max-width: 360px) { .below { grid-template-columns: 1fr; } }
      .tires { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .tire-tile { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 8px; align-items: center; padding: 8px 10px; border-radius: 12px; background: var(--lm-soft); cursor: pointer; min-width: 0; }
      .tire-tile ha-icon { grid-row: span 2; --mdc-icon-size: 20px; color: var(--secondary-text-color); }
      .tire-tile span { font-size: .72rem; color: var(--secondary-text-color); white-space: nowrap; }
      .tire-tile b { font-size: .95rem; font-weight: 600; white-space: nowrap; }
      .tire-tile.good ha-icon { color: var(--lm-green); }
      .tire-tile.low ha-icon, .tire-tile.low b { color: var(--lm-orange); }
      .tire-tile.bad { background: color-mix(in srgb, var(--lm-red) 15%, transparent); }
      .tire-tile.bad ha-icon, .tire-tile.bad b { color: var(--lm-red); }
      .tire-tile.bad ha-icon { animation: lm-wiggle 2.4s ease-in-out infinite; }
      @keyframes lm-shimmer { to { background-position: -200% 0; } }
    `;
  }
}

// ---------------------------------------------------------------------------
// Statistics card
// ---------------------------------------------------------------------------

class LeapmotorStatsCard extends LeapmotorBaseCard {
  split(key, label) {
    if (!this.has(key) || this.v(key) === undefined) return "";
    const attrs = this.st(key).attributes;
    const parts = [
      ["driving", attrs.driving, "var(--lm-blue)", this.t("driving_energy")],
      ["climate", attrs.climate, "var(--lm-orange)", this.t("climate_energy")],
      ["other", attrs.other, "var(--lm-teal)", this.t("other_energy")],
    ].filter(([, value]) => Number(value) > 0);
    const total = parts.reduce((sum, [, value]) => sum + Number(value), 0);
    const bar = parts
      .map(([name, value, color]) => `<span class="seg ${name}" style="width:${((Number(value) / total) * 100).toFixed(1)}%;background:${color}"></span>`)
      .join("");
    const legend = parts
      .map(([, value, color, text]) => `<span class="legend"><i style="background:${color}"></i>${esc(text)} ${esc(this.unit(Number(value), "kWh", 1))}</span>`)
      .join("");
    return `
      <div class="split"${this.more(key)}>
        <div class="split-head"><span>${esc(label)}</span><b>${esc(this.unit(this.n(key), "kWh", 1))}</b></div>
        <div class="segments">${bar || '<span class="seg empty"></span>'}</div>
        <div class="legends">${legend}</div>
      </div>`;
  }

  week() {
    const days = this.attr("sensor.mileage_7d", "days");
    if (!Array.isArray(days) || !days.length) return "";
    const max = Math.max(1, ...days.map((day) => Number(day.distance) || 0));
    const weekday = new Intl.DateTimeFormat(this.locale, { weekday: "short" });
    const bars = days
      .map((day, index) => {
        const distance = Number(day.distance) || 0;
        const date = day.date ? new Date(`${day.date}T12:00:00`) : null;
        const name = date && !Number.isNaN(date.getTime()) ? weekday.format(date) : "";
        return `<div class="day"><span class="km">${distance ? this.num(distance) : ""}</span><div class="col"><div class="fill" style="height:${((distance / max) * 100).toFixed(1)}%;animation-delay:${index * 60}ms"></div></div><span class="name">${esc(name)}</span></div>`;
      })
      .join("");
    return `<div class="section-title">${esc(this.t("last_7_days"))} · ${esc(this.unit(this.n("sensor.mileage_7d"), "km"))}</div><div class="week"${this.more("sensor.mileage_7d")}>${bars}</div>`;
  }

  body() {
    const kpis = [];
    const kpi = (key, icon, label, value) => {
      if (!this.has(key)) return;
      kpis.push(`<div class="kpi"${this.more(key)}><ha-icon icon="${icon}"></ha-icon><span>${esc(label)}</span><b>${esc(value)}</b></div>`);
    };
    kpi("sensor.consumption_average", "mdi:gauge", this.t("consumption"), this.unit(this.n("sensor.consumption_average"), "kWh/100 km", 1));
    kpi("sensor.odometer", "mdi:counter", this.t("odometer"), this.unit(this.n("sensor.odometer"), "km"));
    kpi("sensor.total_energy", "mdi:sigma", this.t("total_energy"), this.unit(this.n("sensor.total_energy"), "kWh"));
    kpi("sensor.delivery_days", "mdi:calendar-heart", this.t("delivered"), this.num(this.n("sensor.delivery_days")));
    return `
      <ha-card>
        <div class="card">
          ${this.header("mdi:chart-box-outline", this.t("statistics"), "")}
          <div class="kpis">${kpis.join("")}</div>
          ${this.split("sensor.energy_today", this.t("today"))}
          ${this.split("sensor.energy_last_week", this.t("last_week"))}
          ${this.week()}
        </div>
      </ha-card>`;
  }

  static get styles() {
    return `
      .kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; margin: 12px 0 6px; }
      .kpi { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 10px; align-items: center; padding: 10px 12px; border-radius: 12px; background: var(--lm-soft); cursor: pointer; animation: lm-fade-up .5s ease-out both; }
      .kpi ha-icon { grid-row: span 2; --mdc-icon-size: 24px; color: var(--primary-color); }
      .kpi span { font-size: .74rem; color: var(--secondary-text-color); }
      .kpi b { font-size: 1.02rem; font-weight: 600; white-space: nowrap; }
      .split { margin-top: 14px; cursor: pointer; }
      .split-head { display: flex; justify-content: space-between; font-size: .88rem; color: var(--secondary-text-color); margin-bottom: 6px; }
      .split-head b { color: var(--primary-text-color); }
      .segments { display: flex; height: 12px; border-radius: 999px; overflow: hidden; background: color-mix(in srgb, var(--primary-text-color) 9%, transparent); }
      .seg { height: 100%; animation: lm-grow-x .9s cubic-bezier(.2,.8,.2,1) both; transform-origin: left; }
      .seg + .seg { margin-left: 2px; }
      .legends { display: flex; flex-wrap: wrap; gap: 4px 14px; margin-top: 6px; font-size: .76rem; color: var(--secondary-text-color); }
      .legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
      .week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; align-items: end; height: 130px; cursor: pointer; }
      .day { display: flex; flex-direction: column; align-items: center; height: 100%; gap: 4px; }
      .day .km { font-size: .68rem; color: var(--secondary-text-color); min-height: 1em; }
      .day .col { flex: 1; width: 100%; max-width: 28px; display: flex; align-items: flex-end; border-radius: 8px; background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); overflow: hidden; }
      .day .fill { width: 100%; border-radius: 8px; background: linear-gradient(180deg, var(--lm-blue), color-mix(in srgb, var(--lm-blue) 55%, var(--lm-teal))); transform-origin: bottom; animation: lm-grow .9s cubic-bezier(.2,.8,.2,1) both; }
      .day .name { font-size: .72rem; color: var(--secondary-text-color); }
    `;
  }
}

// ---------------------------------------------------------------------------
// Visual editor (shared by all cards)
// ---------------------------------------------------------------------------

const EDITOR_LABELS = {
  en: { device_id: "Vehicle", show_picture: "Show the pictures from the app", image: "Own picture instead (URL, optional)", wallbox_entity: "Wallbox power sensor (optional)", solar_entity: "Solar power sensor (optional)" },
  de: { device_id: "Fahrzeug", show_picture: "Bilder aus der App anzeigen", image: "Stattdessen eigenes Bild (URL, optional)", wallbox_entity: "Leistungssensor der Wallbox (optional)", solar_entity: "PV-Leistungssensor (optional)" },
};

class LeapmotorCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => EDITOR_LABELS[langOf(this._hass)][schema.name] ?? schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        const config = { ...this._config, ...ev.detail.value };
        for (const [key, value] of Object.entries(config)) {
          if (value === "" || value === undefined || value === null) delete config[key];
        }
        this._config = config;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    const schema = this.schema || LeapmotorBaseCard.editorSchema;
    this._form.hass = this._hass;
    this._form.schema = schema;
    const defaults = schema.some((field) => field.name === "show_picture") ? { show_picture: true } : {};
    this._form.data = { ...defaults, ...this._config };
  }
}

// ---------------------------------------------------------------------------
// Dashboard strategy
// ---------------------------------------------------------------------------

const DETAIL_GROUPS = [
  ["charging", "mdi:ev-station", ["sensor.soc", "sensor.range", "sensor.range_max", "sensor.charging_state", "binary_sensor.plugged_in", "binary_sensor.charging", "binary_sensor.charge_completed", "sensor.charging_power", "sensor.charge_time_remaining", "sensor.charge_finish_time", "sensor.energy_to_limit", "sensor.battery_energy", "number.charge_limit", "switch.charging", "switch.charge_schedule", "time.charge_schedule_start", "time.charge_schedule_end", "switch.healthy_charging", "switch.battery_preheat", "binary_sensor.battery_heating", "button.unlock_charger", "sensor.battery_temperature", "sensor.battery_power", "sensor.battery_current", "sensor.battery_voltage", "sensor.fuel_level", "sensor.fuel_range", "sensor.combined_range"]],
  ["climate", "mdi:air-conditioner", ["climate.climate", "binary_sensor.climate_active", "sensor.interior_temperature", "sensor.outdoor_temperature", "button.quick_cool", "button.quick_heat", "button.windshield_defrost", "binary_sensor.defrost", "binary_sensor.rear_window_heating", "select.seat_heat_driver", "select.seat_heat_passenger", "select.seat_ventilation_driver", "select.seat_ventilation_passenger", "switch.steering_wheel_heat", "switch.mirror_heat"]],
  ["status", "mdi:car-info", ["lock.lock", "cover.windows", "cover.trunk", "cover.sunshade", "binary_sensor.doors", "binary_sensor.door_driver", "binary_sensor.door_passenger", "binary_sensor.door_rear_left", "binary_sensor.door_rear_right", "binary_sensor.trunk", "binary_sensor.windows", "binary_sensor.window_driver", "binary_sensor.window_passenger", "binary_sensor.window_rear_left", "binary_sensor.window_rear_right", "switch.sentry_mode", "binary_sensor.alarm_armed", "button.find_vehicle", "sensor.tire_pressure_fl", "sensor.tire_pressure_fr", "sensor.tire_pressure_rl", "sensor.tire_pressure_rr", "binary_sensor.tire_warning"]],
  ["statistics", "mdi:chart-box-outline", ["sensor.odometer", "sensor.speed", "sensor.gear", "binary_sensor.driving", "device_tracker.location", "sensor.mileage_7d", "sensor.energy_7d", "sensor.energy_today", "sensor.energy_last_week", "sensor.total_energy", "sensor.consumption_average", "sensor.last_charge_energy", "sensor.last_charge_end", "sensor.delivery_days", "sensor.messages_unread"]],
  ["system", "mdi:cog-outline", ["sensor.last_update", "binary_sensor.cloud_connection", "sensor.polling_mode", "sensor.api_requests_today", "button.refresh", "update.software", "number.battery_capacity", "select.demo_scenario", "binary_sensor.vehicle_ready", "binary_sensor.parking_brake"]],
];

class LeapmotorDashboardStrategy extends HTMLElement {
  static async generate(config, hass) {
    const t = (key) => translate(hass, key);
    const devices = leapmotorDevices(hass);
    if (!devices.length) {
      return { title: "Leapmotor", views: [{ title: "Leapmotor", cards: [{ type: "markdown", content: t("no_vehicle") }] }] };
    }
    const extras = {};
    if (config.wallbox_entity) extras.wallbox_entity = config.wallbox_entity;
    if (config.solar_entity) extras.solar_entity = config.solar_entity;
    const views = [];
    devices.forEach((deviceId, index) => {
      const map = entityMap(hass, deviceId);
      const name = deviceName(hass, deviceId);
      const suffix = devices.length > 1 ? `-${index + 1}` : "";
      const graph = ["sensor.soc", "sensor.charging_power"].map((key) => map[key]).filter(Boolean);
      // Picture options apply to the vehicle and the status card.
      const pictureOptions = {
        ...(config.show_picture === false ? { show_picture: false } : {}),
        ...(config.image ? { image: config.image } : {}),
      };
      const sections = [
        { type: "grid", column_span: 2, cards: [{ type: "custom:leapmotor-vehicle-card", device_id: deviceId, ...pictureOptions }] },
        { type: "grid", cards: [{ type: "custom:leapmotor-charging-card", device_id: deviceId, ...extras }] },
        { type: "grid", cards: [{ type: "custom:leapmotor-climate-card", device_id: deviceId }] },
        { type: "grid", cards: [{ type: "custom:leapmotor-status-card", device_id: deviceId, ...pictureOptions }] },
      ];
      const location = map["device_tracker.location"];
      if (location) {
        sections.push({ type: "grid", cards: [{ type: "map", entities: [location], hours_to_show: 24, default_zoom: 15, theme_mode: "auto" }] });
      }
      sections.push({ type: "grid", cards: [{ type: "custom:leapmotor-stats-card", device_id: deviceId }] });
      if (graph.length) {
        sections.push({ type: "grid", cards: [{ type: "history-graph", title: t("history"), hours_to_show: 48, entities: graph }] });
      }
      views.push({ title: name, path: `vehicle${suffix}`, icon: "mdi:car-electric", type: "sections", max_columns: 3, sections });

      const groups = [];
      const used = new Set();
      for (const [titleKey, icon, keys] of DETAIL_GROUPS) {
        const entities = keys.map((key) => map[key]).filter(Boolean);
        entities.forEach((id) => used.add(id));
        if (entities.length) groups.push({ type: "entities", title: t(titleKey), icon, state_color: true, show_header_toggle: false, entities });
      }
      const rest = Object.values(map).filter((id) => !used.has(id));
      if (rest.length) groups.push({ type: "entities", title: "…", entities: rest });
      views.push({ title: `${t("details")}${devices.length > 1 ? ` · ${name}` : ""}`, path: `details${suffix}`, icon: "mdi:format-list-bulleted", type: "masonry", cards: groups });
    });
    return { title: "Leapmotor", views };
  }
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

const CARDS = [
  ["leapmotor-vehicle-card", LeapmotorVehicleCard, { en: "Leapmotor vehicle", de: "Leapmotor Fahrzeug" }, { en: "Animated vehicle with state of charge, status and quick actions.", de: "Animiertes Fahrzeug mit Ladestand, Status und Schnellaktionen." }],
  ["leapmotor-charging-card", LeapmotorChargingCard, { en: "Leapmotor charging", de: "Leapmotor Laden" }, { en: "Energy flow, charge limit, schedule and charging controls.", de: "Energiefluss, Ladelimit, Ladeplan und Ladesteuerung." }],
  ["leapmotor-climate-card", LeapmotorClimateCard, { en: "Leapmotor climate", de: "Leapmotor Klima" }, { en: "Air conditioning, presets, seats and steering wheel.", de: "Klimaanlage, Schnellprogramme, Sitze und Lenkrad." }],
  ["leapmotor-status-card", LeapmotorStatusCard, { en: "Leapmotor status", de: "Leapmotor Status" }, { en: "Doors, windows, tailgate and tire pressure from above.", de: "Türen, Fenster, Heckklappe und Reifendruck von oben." }],
  ["leapmotor-stats-card", LeapmotorStatsCard, { en: "Leapmotor statistics", de: "Leapmotor Statistik" }, { en: "Consumption, energy split and the last seven days.", de: "Verbrauch, Energieaufteilung und die letzten sieben Tage." }],
];

const define = (name, element) => {
  if (!customElements.get(name)) customElements.define(name, element);
};

define("leapmotor-card-editor", LeapmotorCardEditor);
define("ll-strategy-dashboard-leapmotor-dashboard", LeapmotorDashboardStrategy);

const pageLanguage = (document.documentElement.lang || navigator.language || "en").toLowerCase().startsWith("de") ? "de" : "en";
window.customCards = window.customCards || [];
for (const [name, element, title, description] of CARDS) {
  define(name, element);
  if (!window.customCards.some((card) => card.type === name)) {
    window.customCards.push({ type: name, name: title[pageLanguage], description: description[pageLanguage], preview: true, documentationURL: DOCS_URL });
  }
}

console.info(`%c LEAPMOTOR-CLOUD %c ${VERSION} `, "color:#fff;background:#1abc9c;font-weight:700;border-radius:3px 0 0 3px", "color:#1abc9c;background:#1f2a38;border-radius:0 3px 3px 0");
