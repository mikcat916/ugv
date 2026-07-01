const appConfig = window.APP_CONFIG || {};
const pageContent = document.getElementById("page-content");
const logoutButton = document.getElementById("logout-button");
const generatedAt = document.getElementById("generated-at");
const siteName = document.getElementById("site-name");
const clockPill = document.getElementById("clock-pill");
const gpsStatus = document.getElementById("gps-status");
const systemLocation = document.getElementById("system-location");
const heroLocation = document.getElementById("hero-location");
const currentLocation = document.getElementById("current-location");
const crudModal = document.getElementById("crud-modal");
const crudModalForm = document.getElementById("crud-modal-form");
const crudModalTitle = document.getElementById("crud-modal-title");
const crudModalBody = document.getElementById("crud-modal-body");
const crudModalError = document.getElementById("crud-modal-error");
const crudModalSave = document.getElementById("crud-modal-save");
const navToggle = document.getElementById("nav-toggle");
const navLinks = document.getElementById("nav-links");
const VIDEO_SNAPSHOT_REFRESH_MS = 2000;

const state = {
  pageId: appConfig.pageId,
  data: null,
  maps: {},
  pageData: {},
  paging: {
    users: { page: 1, size: 10 },
    devices: { page: 1, size: 10 },
    areas: { page: 1, size: 10, keyword: "" },
    points: { page: 1, size: 10 },
    routes: { page: 1, size: 10 },
    zones: { page: 1, size: 10 },
    reports: { page: 1, size: 10 },
    deviceCategories: { page: 1, size: 10 },
    onboardUnits: { page: 1, size: 10 },
    networkChannels: { page: 1, size: 10 },
    clusters: { page: 1, size: 10 },
    clusterNodes: { page: 1, size: 10 },
    formations: { page: 1, size: 10 },
    controlCommands: { page: 1, size: 10 },
  },
  areaSelection: [],
  areaDeleteError: "",
  routeEditor: { routeId: null, selected: [] },
  formAreaDefaults: {
    device: { value: "", touched: false },
    point: { value: "", touched: false },
    route: { value: "", touched: false },
    zone: { value: "", touched: false },
  },
  pointDraft: {
    coords: null,
    zoneId: null,
    zoneName: "",
    marker: null,
  },
  deviceFilters: { keyword: "", status: "" },
  deviceImageDraft: { file: null, previewUrl: "", fileName: "" },
  robotDiscovery: {
    items: [],
    scannedAt: "",
    expiresAt: "",
    subnets: [],
    loading: false,
    error: "",
    selectedIp: "",
    manualConfirmedIp: "",
  },
  modal: { onSubmit: null },
  zoneDraft: {
    path: [],
    strokeColor: "#0db9f2",
    fillColor: "rgba(13, 185, 242, 0.18)",
    complete: false,
    clickTimer: null,
    pendingPoint: null,
  },
  geo: {
    coords: null,
    promise: null,
    status: "idle",
    watchId: null,
    locationText: null,
    currentZoneId: null,
    currentZoneName: "",
    currentAreaId: null,
    currentAreaName: "",
  },
  realtime: {
    socket: null,
    heartbeatTimer: null,
    reconnectTimer: null,
  },
  video: {
    mainRobotId: "",
    snapshotTick: Date.now(),
    snapshotTimer: null,
  },
  perception: {
    robotId: "",
    latest: null,
    error: "",
    loading: false,
  },
  control: {
    activeTimer: null,
    activeRobotId: "",
    robotId: "",
    status: "尚未连接控制服务。",
  },
  deviceManagementTab: "categories",
  clusterManagementTab: "clusters",
  managementFilters: {
    deviceCategories: { keyword: "" },
    managedDevices: { keyword: "" },
    onboardUnits: { keyword: "" },
    networkChannels: { keyword: "" },
    clusters: { keyword: "" },
    clusterNodes: { keyword: "" },
    formations: { keyword: "" },
  },
  commandStatus: "",
};

const TOKEN_TEXT = {
  active: "运行中",
  charging: "充电中",
  critical: "严重",
  disabled: "已停用",
  degraded: "性能下降",
  fault: "故障",
  good: "良好",
  healthy: "正常",
  high: "高",
  idle: "待命",
  info: "提示",
  inspection: "巡检区",
  low: "低",
  medium: "中",
  neutral: "平稳",
  normal: "正常",
  offline: "离线",
  online: "在线",
  paused: "暂停",
  positive: "上升",
  repair: "维修中",
  restricted: "管控区",
  scheduled: "已排期",
  storage: "仓储区",
  warning: "告警",
  standby: "待接入",
  connected: "已接入",
  disconnected: "已退出",
  draft: "草稿",
  success: "成功",
  failed: "失败",
  pending: "执行中",
  line: "直线",
  wedge: "楔形",
  column: "纵队",
};

const ZONE_PALETTE = [
  "#0db9f2",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#6366f1",
  "#14b8a6",
  "#eab308",
  "#f97316",
];

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
const FALLBACK_SITE_CENTER = [113.584411, 22.349433];
const URL_SYNC_PAGE_IDS = new Set(["users", "devices", "areas", "zones", "points", "routes", "reports"]);
const COMMAND_PAGE_IDS = new Set(["device_control", "cluster_control"]);
const DEVICE_STATUS_FILTERS = new Set(["normal", "repair", "offline"]);
const MANAGEMENT_FILTER_PAGING_KEYS = {
  deviceCategories: "deviceCategories",
  managedDevices: "devices",
  onboardUnits: "onboardUnits",
  networkChannels: "networkChannels",
  clusters: "clusters",
  clusterNodes: "clusterNodes",
  formations: "formations",
};
const MANAGEMENT_PAGE_CONFIG = {
  device_management: {
    tabStateKey: "deviceManagementTab",
    defaultTab: "categories",
    tabs: {
      categories: { filterKey: "deviceCategories", pagingKey: "deviceCategories" },
      devices: { filterKey: "managedDevices", pagingKey: "devices" },
      units: { filterKey: "onboardUnits", pagingKey: "onboardUnits" },
      network: { filterKey: "networkChannels", pagingKey: "networkChannels" },
    },
  },
  cluster_management: {
    tabStateKey: "clusterManagementTab",
    defaultTab: "clusters",
    tabs: {
      clusters: { filterKey: "clusters", pagingKey: "clusters" },
      nodes: { filterKey: "clusterNodes", pagingKey: "clusterNodes" },
      formations: { filterKey: "formations", pagingKey: "formations" },
    },
  },
};
const ZONE_COLOR_NAMES = {
  "#0db9f2": "蓝色",
  "#22c55e": "绿色",
  "#f59e0b": "橙色",
  "#ef4444": "红色",
  "#6366f1": "靛蓝色",
  "#14b8a6": "青绿色",
  "#eab308": "黄色",
  "#f97316": "深橙色",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDateTime(value) {
  if (!value) return "-";
  return value.replace("T", " ");
}

function localizeToken(value) {
  const token = String(value || "").toLowerCase();
  return TOKEN_TEXT[token] || String(value || "-");
}

function siteCenter() {
  const center = state.data?.site?.center;
  const lng = Number(center?.[0]);
  const lat = Number(center?.[1]);
  return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : FALLBACK_SITE_CENTER;
}

function siteZoom() {
  const zoom = Number(state.data?.site?.zoom);
  return Number.isFinite(zoom) ? zoom : 17.2;
}

function zoneOptionLabel(zone) {
  const name = zone?.name || `区域 ${zone?.id ?? ""}`.trim();
  const details = [localizeToken(zone?.type), zone?.areaName].filter(Boolean).join(" · ");
  return details ? `${name} (${details})` : name;
}

function robotOptionLabel(robot) {
  const name = robot?.model || `机器人 ${robot?.id ?? ""}`.trim();
  return robot?.ipAddress ? `${name} · ${robot.ipAddress}` : name;
}

function renderZoneOptions(selectedValue = "", emptyLabel = "不绑定区域") {
  const zones = Array.isArray(state.data?.zones) ? state.data.zones : [];
  return renderSelectOptions(zones, selectedValue, zones.length ? emptyLabel : "暂无区域，请先新建区域", zoneOptionLabel);
}

function renderRobotOptions(selectedValue = "", emptyLabel = "不指定机器人") {
  const robots = Array.isArray(state.data?.robots) ? state.data.robots : [];
  return renderSelectOptions(robots, selectedValue, robots.length ? emptyLabel : "暂无机器人，请先添加机器人", robotOptionLabel);
}

function formatRobotLocation(robot) {
  const location = Array.isArray(robot?.location) ? robot.location : [];
  if (location.length !== 2) return "-";
  const [lng, lat] = location;
  return `${formatCoordinate(lat)}, ${formatCoordinate(lng)}`;
}

function describeRobotNetwork(robot) {
  const status = localizeToken(robot.networkStatus || robot.telemetryStatus || "offline");
  const signal = Number.isFinite(Number(robot.signal)) ? `${robot.signal}%` : "-";
  return `${status} · 信号 ${signal}`;
}

function robotMarkerTitle(robot) {
  return `${robot.model} | ${localizeToken(robot.status)} | 网络 ${localizeToken(robot.networkStatus)} | 电量 ${robot.battery}%`;
}

function toRgba(hex, alpha = 0.18) {
  const normalized = String(hex || "").replace("#", "");
  if (normalized.length !== 6) return `rgba(13, 185, 242, ${alpha})`;
  const red = Number.parseInt(normalized.slice(0, 2), 16);
  const green = Number.parseInt(normalized.slice(2, 4), 16);
  const blue = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function resetZoneDraft() {
  if (state.zoneDraft.clickTimer) {
    window.clearTimeout(state.zoneDraft.clickTimer);
    state.zoneDraft.clickTimer = null;
  }
  state.zoneDraft.pendingPoint = null;
  state.zoneDraft.path = [];
  state.zoneDraft.complete = false;
  syncZoneDraftUi();
  refreshZoneDraftPreview();
}

function updateZoneColor(color) {
  state.zoneDraft.strokeColor = color;
  state.zoneDraft.fillColor = toRgba(color);
  syncZoneDraftUi();
  refreshZoneDraftPreview();
}

function zoneDraftEffectivePath() {
  const { path, pendingPoint } = state.zoneDraft;
  if (!pendingPoint) return path;
  const lastPoint = path[path.length - 1] || null;
  const isDuplicatePoint = lastPoint
    && Math.abs(lastPoint[0] - pendingPoint[0]) < 1e-6
    && Math.abs(lastPoint[1] - pendingPoint[1]) < 1e-6;
  return isDuplicatePoint ? path : [...path, pendingPoint];
}

function zoneColorLabel(color) {
  return ZONE_COLOR_NAMES[String(color || "").toLowerCase()] || String(color || "自定义");
}

function syncZoneDraftUi() {
  const pathField = document.querySelector('#zone-form [name="path"]');
  const strokeField = document.querySelector('#zone-form [name="strokeColor"]');
  const fillField = document.querySelector('#zone-form [name="fillColor"]');
  const status = document.getElementById("zone-draw-status");
  const preview = document.getElementById("zone-color-preview");
  const completeButton = document.getElementById("zone-complete-button");
  const effectivePath = zoneDraftEffectivePath();
  const pointCount = effectivePath.length;
  if (pathField) pathField.value = JSON.stringify(effectivePath);
  if (strokeField) strokeField.value = state.zoneDraft.strokeColor;
  if (fillField) fillField.value = state.zoneDraft.fillColor;
  if (status) {
    if (!pointCount) {
      status.textContent = "单击地图加点，右键撤销，至少 3 点即可保存。";
    } else if (pointCount < 3) {
      status.textContent = `已选择 ${pointCount} 个点，还需 ${3 - pointCount} 个点即可保存。`;
    } else if (state.zoneDraft.complete) {
      status.textContent = `已完成绘制，共 ${pointCount} 个点，可直接保存。`;
    } else {
      status.textContent = `已选择 ${pointCount} 个点，可直接保存，继续单击可追加点。`;
    }
  }
  if (preview) {
    preview.style.background = state.zoneDraft.strokeColor;
  }
  if (completeButton) {
    completeButton.disabled = pointCount < 3;
    completeButton.textContent = state.zoneDraft.complete ? "已完成绘制" : "完成绘制";
  }
  document.querySelectorAll("[data-zone-color]").forEach((button) => {
    const active = button.dataset.zoneColor === state.zoneDraft.strokeColor;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function refreshZoneDraftPreview() {
  const entry = state.maps["zones-map"];
  if (!entry?.map) return;
  if (entry.draftPolyline) {
    entry.draftPolyline.setMap(null);
    entry.draftPolyline = null;
  }
  if (entry.draftPolygon) {
    entry.draftPolygon.setMap(null);
    entry.draftPolygon = null;
  }
  const path = zoneDraftEffectivePath();
  if (path.length >= 2) {
    entry.draftPolyline = new AMap.Polyline({
      map: entry.map,
      path,
      strokeColor: state.zoneDraft.strokeColor,
      strokeWeight: 3,
      strokeStyle: state.zoneDraft.complete ? "solid" : "dashed",
      bubble: true,
    });
  }
  if (path.length >= 3) {
    entry.draftPolygon = new AMap.Polygon({
      map: entry.map,
      path,
      strokeColor: state.zoneDraft.strokeColor,
      fillColor: state.zoneDraft.fillColor,
      fillOpacity: state.zoneDraft.complete ? 0.28 : 0.16,
      strokeWeight: 2,
      bubble: true,
    });
  }
}

function queueZonePoint(coords) {
  if (state.zoneDraft.clickTimer) {
    window.clearTimeout(state.zoneDraft.clickTimer);
  }
  state.zoneDraft.pendingPoint = coords;
  state.zoneDraft.complete = false;
  syncZoneDraftUi();
  refreshZoneDraftPreview();
  state.zoneDraft.clickTimer = window.setTimeout(() => {
    commitPendingZonePoint();
  }, 220);
}

function commitPendingZonePoint() {
  if (!state.zoneDraft.pendingPoint) return false;
  const lastPoint = state.zoneDraft.path[state.zoneDraft.path.length - 1] || null;
  const isDuplicatePoint = lastPoint
    && Math.abs(lastPoint[0] - state.zoneDraft.pendingPoint[0]) < 1e-6
    && Math.abs(lastPoint[1] - state.zoneDraft.pendingPoint[1]) < 1e-6;
  if (!isDuplicatePoint) {
    state.zoneDraft.path = [...state.zoneDraft.path, state.zoneDraft.pendingPoint];
  }
  state.zoneDraft.pendingPoint = null;
  state.zoneDraft.complete = false;
  if (state.zoneDraft.clickTimer) {
    window.clearTimeout(state.zoneDraft.clickTimer);
    state.zoneDraft.clickTimer = null;
  }
  syncZoneDraftUi();
  refreshZoneDraftPreview();
  return true;
}

function clearPendingZonePoint() {
  if (state.zoneDraft.clickTimer) {
    window.clearTimeout(state.zoneDraft.clickTimer);
    state.zoneDraft.clickTimer = null;
  }
  state.zoneDraft.pendingPoint = null;
}

function setupZoneDrawing(map) {
  if (typeof map.setStatus === "function") {
    map.setStatus({ doubleClickZoom: false });
  }
  map.on("click", (event) => {
    queueZonePoint([event.lnglat.getLng(), event.lnglat.getLat()]);
  });
  map.on("dblclick", () => {
    commitPendingZonePoint();
    if (state.zoneDraft.path.length >= 3) {
      state.zoneDraft.complete = true;
      syncZoneDraftUi();
      refreshZoneDraftPreview();
    }
  });
  map.on("rightclick", () => {
    if (state.zoneDraft.pendingPoint) {
      clearPendingZonePoint();
      syncZoneDraftUi();
      refreshZoneDraftPreview();
      return;
    }
    if (!state.zoneDraft.path.length) return;
    state.zoneDraft.path = state.zoneDraft.path.slice(0, -1);
    state.zoneDraft.complete = false;
    syncZoneDraftUi();
    refreshZoneDraftPreview();
  });
  syncZoneDraftUi();
  refreshZoneDraftPreview();
}

function padSerial(value) {
  return String(value).padStart(2, "0");
}

function nextDraftIndex(type, listName) {
  return ((state.data?.[listName]?.length || 0) + 1);
}

function todayLabel() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${month}-${day}`;
}

function friendlyDefaults(formName) {
  const draftIndexMap = {
    task: nextDraftIndex("task", "tasks"),
    robot: nextDraftIndex("robot", "robots"),
    alert: nextDraftIndex("alert", "alerts"),
    report: nextDraftIndex("report", "reports"),
    zone: nextDraftIndex("zone", "zones"),
  };
  const index = draftIndexMap[formName] || 1;
  const serial = padSerial(index);

  const defaults = {
    task: {
      name: `瀚林巡检任务-${serial}`,
      description: "重点检查楼宇周边通道、围栏和设备点位。",
    },
    robot: {
      model: `巡检机器人-${serial}`,
    },
    alert: {
      title: `楼宇通道异常告警-${serial}`,
      detail: "发现现场状态异常，请值班人员尽快核查。",
    },
    report: {
      title: `${todayLabel()} 巡检运行简报`,
      value: "98%",
      detail: "今日任务执行稳定，重点区域状态正常。",
      trend: "+2%",
    },
    zone: {
      name: `${index}号巡检区`,
      type: "inspection",
      frequency: "30分钟/次",
      notes: "覆盖楼宇通道、设备柜和围栏转角。",
    },
  };

  return defaults[formName] || {};
}

function applyFriendlyFormDefaults(formName, form) {
  if (!form) return;
  const defaults = friendlyDefaults(formName);
  Object.entries(defaults).forEach(([name, value]) => {
    const field = form.elements.namedItem(name);
    if (!field) return;
    if (field.tagName === "SELECT") {
      field.value = value;
      return;
    }
    if (!field.value) {
      field.value = value;
    }
  });
}

function pillClass(value) {
  const token = String(value || "").toLowerCase();
  if (["critical", "offline", "danger"].includes(token)) return "pill critical";
  if (["warning", "degraded", "medium"].includes(token)) return "pill warning";
  if (["active", "healthy", "online", "good", "low", "positive"].includes(token)) return "pill healthy";
  return "pill";
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("登录状态已失效，请重新登录。");
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    throw new Error(payload?.detail || `请求失败：${response.status}`);
  }

  return payload;
}

async function loadDashboard() {
  const payload = await apiFetch("/api/dashboard");
  state.data = payload.data;
  if (state.geo.coords) {
    syncResolvedGeoArea(state.geo.coords);
  }
  renderShellMeta();
  renderCurrentPage();
}

function renderShellMeta() {
  if (!state.data) return;
  siteName.textContent = state.data.site.name;
  updateLocationLabels(state.geo.locationText || state.data.site.city);
  generatedAt.textContent = `最近更新时间：${formatDateTime(state.data.generatedAt)}`;
}

function setGpsStatus(text, tone = "") {
  if (!gpsStatus) return;
  gpsStatus.textContent = text;
  gpsStatus.className = `meta-pill${tone ? ` ${tone}` : ""}`;
}

function updateLocationLabels(text) {
  const label = text || state.data?.site?.city || "未知位置";
  if (systemLocation) systemLocation.textContent = label;
  if (heroLocation) heroLocation.textContent = label;
  if (currentLocation) {
    const areaText = state.geo.currentAreaName ? ` ｜ 当前区域：${state.geo.currentAreaName}` : "";
    currentLocation.textContent = `当前位置：${label}${areaText}`;
  }
}

async function reverseGeocode(coords) {
  if (typeof window.AMap === "undefined" || typeof window.AMap.Geocoder === "undefined") {
    return `${coords[1].toFixed(6)}, ${coords[0].toFixed(6)}`;
  }
  return new Promise((resolve) => {
    const geocoder = new AMap.Geocoder({ radius: 1000, extensions: "all" });
    geocoder.getAddress(coords, (status, result) => {
      if (status === "complete" && result?.regeocode) {
        const address = result.regeocode.formattedAddress;
        const component = result.regeocode.addressComponent || {};
        resolve(
          component.township ||
            component.street ||
            component.district ||
            component.city ||
            component.province ||
            address ||
            `${coords[1].toFixed(6)}, ${coords[0].toFixed(6)}`,
        );
        return;
      }
      resolve(`${coords[1].toFixed(6)}, ${coords[0].toFixed(6)}`);
    });
  });
}

async function applyGeoUpdate(coords, sourceLabel) {
  state.geo.coords = coords;
  state.geo.status = "ready";
  const locationText = await reverseGeocode(coords);
  state.geo.locationText = locationText;
  syncResolvedGeoArea(coords);
  updateLocationLabels(locationText);
  if (state.geo.currentAreaId) {
    setGpsStatus(`${sourceLabel}已定位`, "success");
  } else {
    setGpsStatus(`${sourceLabel}已定位，但当前位置不在任何已配置区域内`, "warning");
  }
  syncManagedFormAreaUi();
  refreshMapsWithLocation();
  return coords;
}

async function locateWithBrowser() {
  if (!navigator.geolocation) {
    throw new Error("当前浏览器不支持 GPS 定位。");
  }
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve([position.coords.longitude, position.coords.latitude]);
      },
      () => reject(new Error("浏览器定位失败或定位权限被拒绝。")),
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      },
    );
  });
}

async function locateWithAmap() {
  if (typeof window.AMap === "undefined") {
    throw new Error("高德地图尚未加载。");
  }
  return new Promise((resolve, reject) => {
    const geolocation = new AMap.Geolocation({
      enableHighAccuracy: true,
      timeout: 10000,
      zoomToAccuracy: false,
      convert: true,
    });
    geolocation.getCurrentPosition((status, result) => {
      if (status === "complete" && result?.position) {
        resolve([result.position.lng, result.position.lat]);
        return;
      }
      reject(new Error("高德定位失败。"));
    });
  });
}

async function ensureUserLocation() {
  if (state.geo.coords) {
    return state.geo.coords;
  }
  if (state.geo.promise) {
    return state.geo.promise;
  }

  state.geo.status = "locating";
  setGpsStatus("定位中");

  state.geo.promise = (async () => {
    try {
      const coords = await locateWithBrowser();
      return await applyGeoUpdate(coords, "GPS ");
    } catch (browserError) {
      try {
        const coords = await locateWithAmap();
        return await applyGeoUpdate(coords, "高德");
      } catch (amapError) {
        state.geo.status = "failed";
        setGpsStatus("定位失败", "danger");
        throw new Error(browserError.message || amapError.message);
      }
    } finally {
      state.geo.promise = null;
    }
  })();

  return state.geo.promise;
}

function renderStats() {
  const counts = state.data.counts;
  return `
    <section class="stats-grid">
      <article class="stat-card"><span>机器人</span><strong>${counts.robots}</strong><small class="muted">当前接入设备数</small></article>
      <article class="stat-card"><span>任务</span><strong>${counts.tasks}</strong><small class="muted">已创建巡检任务</small></article>
      <article class="stat-card"><span>告警</span><strong>${counts.alerts}</strong><small class="muted">待处理事件数量</small></article>
      <article class="stat-card"><span>区域</span><strong>${counts.zones}</strong><small class="muted">已管理巡检区域</small></article>
    </section>
  `;
}

function refreshMapsWithLocation() {
  const coords = state.geo.coords;
  if (!coords) return;
  Object.values(state.maps).forEach((entry) => {
    if (!entry?.map) return;
    entry.map.setCenter(coords);
    if (!entry.userMarker) {
      entry.userMarker = new AMap.Marker({
        map: entry.map,
        position: coords,
        title: "我的当前位置",
        label: { content: "我", direction: "top" },
        bubble: true,
      });
    } else {
      entry.userMarker.setPosition(coords);
    }
  });
}

function startLocationWatch() {
  if (!navigator.geolocation || state.geo.watchId !== null) {
    return;
  }
  state.geo.watchId = navigator.geolocation.watchPosition(
    async (position) => {
      const coords = [position.coords.longitude, position.coords.latitude];
      await applyGeoUpdate(coords, "GPS ");
    },
    () => {
      if (!state.geo.coords) {
        setGpsStatus("定位失败", "danger");
      }
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 10000,
    },
  );
}

function renderOverviewPage() {
  const robots = state.data.robots.slice(0, 4);
  const alerts = state.data.alerts.slice(0, 5);
  const zones = state.data.zones.slice(0, 4);
  return `
    ${renderStats()}
    <section class="dashboard-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>机器人动态</h2><p class="muted">车队实时遥测信息</p></div></div>
        <div class="list-stack">
          ${robots.length ? robots.map((robot) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(robot.model)}</strong>
                <p>${escapeHtml(robot.zoneName)} · 最近上报 ${escapeHtml(formatDateTime(robot.lastSeenAt || robot.createdAt))}</p>
                <div class="inline-meta">
                  <span class="${pillClass(robot.status)}">${escapeHtml(localizeToken(robot.status))}</span>
                  <span class="${pillClass(robot.networkStatus)}">网络 ${escapeHtml(localizeToken(robot.networkStatus))}</span>
                  <span class="meta-pill">电量 ${robot.battery}%</span>
                  <span class="meta-pill">信号 ${robot.signal}%</span>
                  <span class="meta-pill">健康度 ${robot.health}%</span>
                </div>
              </div>
              <div class="muted">位置 ${escapeHtml(formatRobotLocation(robot))} · 速度 ${robot.speed} m/s</div>
            </div>
          `).join("") : `<div class="empty-state">暂无机器人数据。</div>`}
        </div>
      </article>

      <article class="panel">
        <div class="panel-header"><div><h2>告警流</h2><p class="muted">最新事件记录</p></div></div>
        <div class="list-stack">
          ${alerts.length ? alerts.map((alert) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(alert.title)}</strong>
                <p>${escapeHtml(alert.detail || "暂无详细说明。")}</p>
              </div>
              <div>
                <span class="${pillClass(alert.level)}">${escapeHtml(localizeToken(alert.level))}</span>
                <p class="muted">${formatDateTime(alert.happenedAt)}</p>
              </div>
            </div>
          `).join("") : `<div class="empty-state">暂无告警记录。</div>`}
        </div>
      </article>
    </section>
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>区域地图</h2><p class="muted">区域多边形与机器人位置</p></div></div>
        <div id="overview-map" class="map-shell"><div class="map-fallback">检测到高德地图后将在此渲染。</div></div>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h2>重点区域</h2><p class="muted">优先关注的巡检区域</p></div></div>
        <div class="list-stack">
          ${zones.length ? zones.map((zone) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(zone.name)}</strong>
                <p>${escapeHtml(localizeToken(zone.type))} · ${escapeHtml(zone.frequency)}</p>
              </div>
              <span class="${pillClass(zone.risk)}">${escapeHtml(localizeToken(zone.risk))}</span>
            </div>
          `).join("") : `<div class="empty-state">暂无区域配置。</div>`}
        </div>
      </article>
    </section>
  `;
}

function renderTasksPage() {
  return `
    ${renderStats()}
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>新建任务</h2><p class="muted">为机器人分配巡检时间窗口</p></div></div>
        <form id="task-form" class="stack-form">
          <div class="grid-form">
            <label><span>任务名称</span><input name="name" placeholder="例：瀚林2号周边晨检任务" required></label>
            <label><span>优先级</span><select name="priority"><option value="low">低</option><option value="medium" selected>中</option><option value="high">高</option></select></label>
            <label><span>执行机器人</span><select name="robotId">${renderRobotOptions("", "不指定机器人")}</select></label>
            <label><span>巡检区域</span><select name="zoneId">${renderZoneOptions("", "不指定区域")}</select></label>
            <label><span>开始时间</span><input name="startAt" type="datetime-local" required></label>
            <label><span>结束时间</span><input name="endAt" type="datetime-local" required></label>
          </div>
          <label><span>任务说明</span><textarea name="description" placeholder="填写本次巡检范围、关注点和执行要求"></textarea></label>
          <div class="button-row"><button class="primary-button" type="submit">创建任务</button></div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="task"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h2>任务列表</h2><p class="muted">当前巡检任务队列</p></div></div>
        ${renderTable("tasks", ["ID", "任务名称", "机器人", "区域", "时间窗口", "优先级", "状态", "操作"], state.data.tasks.map((task) => `
          <tr>
            <td>${task.id}</td>
            <td>${escapeHtml(task.name)}</td>
            <td>${escapeHtml(task.robotName)}</td>
            <td>${escapeHtml(task.zoneName)}</td>
            <td>${escapeHtml(task.window)}</td>
            <td><span class="${pillClass(task.priority)}">${escapeHtml(localizeToken(task.priority))}</span></td>
            <td><span class="${pillClass(task.status)}">${escapeHtml(localizeToken(task.status))}</span></td>
            <td><button class="danger-button" data-delete="tasks" data-id="${task.id}">删除</button></td>
          </tr>
        `))}
      </article>
    </section>
  `;
}

function renderReportsPage() {
  const reportsData = state.pageData.reports;
  if (!reportsData) {
    return renderLoadingPage("历史报告", "查看历史报告并维护统计卡片。");
  }
  return `
    ${renderStats()}
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>新建报告卡片</h2><p class="muted">向总览页补充统计指标</p></div></div>
        <form id="report-form" class="stack-form">
          <div class="grid-form">
            <label><span>标题</span><input name="title" placeholder="例：当日巡检完成率" required></label>
            <label><span>指标值</span><input name="value" placeholder="例：98%" required></label>
            <label><span>趋势</span><input name="trend" value="+2%"></label>
            <label><span>趋势语义</span><select name="tone"><option value="neutral">持平</option><option value="positive">上升</option><option value="warning">预警</option></select></label>
            <label><span>报告日期</span><input name="reportDate" type="date" required></label>
          </div>
          <label><span>说明</span><textarea name="detail" placeholder="补充这个指标的业务解释"></textarea></label>
          <div class="button-row"><button class="primary-button" type="submit">创建报告</button></div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="report"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h2>历史报告</h2><p class="muted">已有管理统计快照</p></div></div>
        <div class="metric-grid">
          ${reportsData.items.length ? reportsData.items.map((report) => `
            <article class="metric-card">
              <strong>${escapeHtml(report.title)}</strong>
              <div class="inline-meta">
                <span class="meta-pill">${escapeHtml(report.value)}</span>
                <span class="${pillClass(report.tone)}">${escapeHtml(report.trend)}</span>
              </div>
              <p>${escapeHtml(report.detail || "暂无说明。")}</p>
              <div class="button-row">
                <span class="muted">${escapeHtml(report.reportDate)}</span>
                <button class="danger-button" type="button" data-report-delete data-id="${report.id}">删除</button>
              </div>
            </article>
          `).join("") : `<div class="empty-state">暂无报告数据。</div>`}
        </div>
        ${renderPagination("reports", reportsData, "份报告")}
      </article>
    </section>
  `;
}

function renderStatusPage() {
  const discovery = state.robotDiscovery;
  const selectableItems = discovery.items.filter((item) => item.confirmed || item.ipAddress === discovery.manualConfirmedIp);
  const selectedIp = selectableItems.some((item) => item.ipAddress === discovery.selectedIp)
    ? discovery.selectedIp
    : "";
  const submitDisabled = !selectedIp || discovery.loading;
  const [defaultLng, defaultLat] = siteCenter();
  return `
    ${renderStats()}
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>新增机器人</h2><p class="muted">必须先扫描当前 Wi-Fi 网络并确认机器人实体</p></div></div>
        <form id="robot-form" class="stack-form">
          <div class="grid-form">
            <label><span>名称</span><input name="model" placeholder="例：巡检机器人-01" required></label>
            <label class="field-span-2">
              <span>Wi-Fi 扫描确认</span>
              <div class="inline-meta robot-discovery-toolbar">
                <button class="secondary-button" id="robot-discovery-refresh" type="button"${discovery.loading ? " disabled" : ""}>${discovery.loading ? "扫描中…" : "扫描 Wi-Fi 网络"}</button>
                <span class="muted">${discovery.scannedAt ? `最近扫描：${escapeHtml(formatDateTime(discovery.scannedAt))}` : "尚未扫描"}</span>
              </div>
              <select id="robot-discovery-select" name="ipAddress" required${discovery.loading ? " disabled" : ""}>
                <option value="">请先扫描并选择已确认的机器人 IP</option>
                ${selectableItems.map((item) => `
                  <option value="${escapeHtml(item.ipAddress)}"${item.ipAddress === selectedIp ? " selected" : ""}>
                    ${escapeHtml(item.ipAddress)} | ${escapeHtml(item.deviceName || item.hostName || "unknown")} | ${escapeHtml(item.confirmed ? item.summary || "" : "人工确认")}
                  </option>
                `).join("")}
              </select>
              <small class="muted">${discovery.subnets?.length ? `扫描网段：${escapeHtml(discovery.subnets.join(", "))}` : "仅允许添加当前 Wi-Fi 网络中已识别的机器人。"} 未自动确认时，可由管理员人工确认后选择。</small>
            </label>
            <label><span>所属区域（可选）</span><select name="zoneId">${renderZoneOptions("", "不绑定区域")}</select></label>
            <label><span>状态</span><select name="status"><option value="idle">待命</option><option value="active">执行中</option><option value="charging">充电中</option><option value="offline">离线</option></select></label>
            <label><span>健康度</span><input name="health" type="number" value="92" min="0" max="100"></label>
            <label><span>电量</span><input name="battery" type="number" value="78" min="0" max="100"></label>
            <label><span>速度</span><input name="speed" type="number" step="0.1" value="1.2"></label>
            <label><span>信号</span><input name="signal" type="number" value="88" min="0" max="100"></label>
            <label><span>延迟</span><input name="latency" type="number" value="28"></label>
            <label><span>经度</span><input name="lng" type="number" step="0.000001" value="${formatCoordinate(defaultLng)}"></label>
            <label><span>纬度</span><input name="lat" type="number" step="0.000001" value="${formatCoordinate(defaultLat)}"></label>
            <label><span>航向角</span><input name="heading" type="number" value="0" min="0" max="359"></label>
          </div>
          ${discovery.error ? `<div class="form-error" role="alert" aria-live="polite">${escapeHtml(discovery.error)}</div>` : ""}
          <div class="button-row"><button class="primary-button" type="submit"${submitDisabled ? " disabled" : ""}>添加机器人</button></div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="robot"></p>
        </form>
        <div class="list-stack robot-discovery-list">
          ${discovery.items.length ? discovery.items.map((item) => `
            <div class="list-item robot-discovery-item${item.confirmed ? " confirmed" : ""}">
              <div>
                <strong>${escapeHtml(item.ipAddress)}</strong>
                <p>${escapeHtml(item.deviceName || item.hostName || "unknown host")} | MAC ${escapeHtml(item.macAddress || "-")}</p>
              </div>
              <div>
                <span class="${item.confirmed ? "pill healthy" : "pill warning"}">${item.confirmed ? "已确认" : item.ipAddress === discovery.manualConfirmedIp ? "人工确认" : "未确认"}</span>
                <p class="muted">ports: ${escapeHtml(formatPorts(item.openPorts))}</p>
                ${!item.confirmed ? `<button class="ghost-button robot-manual-confirm" type="button" data-robot-manual-confirm="${escapeHtml(item.ipAddress)}">人工确认</button>` : ""}
              </div>
            </div>
          `).join("") : `<div class="empty-state">还没有扫描结果。</div>`}
        </div>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h2>机器人状态板</h2><p class="muted">遥测与运行状态</p></div></div>
        ${renderTable("robots", ["ID", "机器人名称", "IP", "区域", "运行状态", "网络", "电量", "位置", "最近上报", "操作"], state.data.robots.map((robot) => `
          <tr>
            <td>${robot.id}</td>
            <td>${escapeHtml(robot.model)}</td>
            <td>${escapeHtml(robot.ipAddress || "-")}</td>
            <td>${escapeHtml(robot.zoneName)}</td>
            <td><span class="${pillClass(robot.status)}">${escapeHtml(localizeToken(robot.status))}</span></td>
            <td>
              <div class="inline-meta">
                <span class="${pillClass(robot.networkStatus)}">${escapeHtml(localizeToken(robot.networkStatus))}</span>
                <span class="muted">信号 ${robot.signal}%</span>
              </div>
            </td>
            <td>${robot.battery}%</td>
            <td>${escapeHtml(formatRobotLocation(robot))}</td>
            <td>${escapeHtml(formatDateTime(robot.lastSeenAt || robot.createdAt))}</td>
            <td><button class="danger-button" data-delete="robots" data-id="${robot.id}">删除</button></td>
          </tr>
        `))}
      </article>
    </section>
  `;
}

function renderMaintenancePage() {
  return `
    ${renderStats()}
    <section class="dashboard-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>维护队列</h2><p class="muted">机器人健康与告警联动处理</p></div></div>
        <div class="list-stack">
          ${state.data.maintenance.length ? state.data.maintenance.map((item) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(item.asset)}</strong>
                <p>${escapeHtml(item.zoneName)} · ${escapeHtml(item.summary)}</p>
              </div>
              <div>
                <span class="${pillClass(item.state)}">${escapeHtml(localizeToken(item.state))}</span>
                <p class="muted">${formatDateTime(item.lastCheck)}</p>
              </div>
            </div>
          `).join("") : `<div class="empty-state">暂无维护项。</div>`}
        </div>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h2>手动创建告警</h2><p class="muted">供值班人员手动录入事件</p></div></div>
        <form id="alert-form" class="stack-form">
          <div class="grid-form">
            <label><span>等级</span><select name="level"><option value="info">提示</option><option value="warning" selected>告警</option><option value="critical">严重</option></select></label>
            <label><span>标题</span><input name="title" placeholder="例：东侧围栏异常告警" required></label>
            <label><span>发生时间</span><input name="happenedAt" type="datetime-local"></label>
          </div>
          <label><span>详情</span><textarea name="detail" placeholder="填写现场现象、影响范围和处理建议"></textarea></label>
          <div class="button-row"><button class="primary-button" type="submit">创建告警</button></div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="alert"></p>
        </form>
      </article>
    </section>
  `;
}

function videoRobots() {
  return Array.isArray(state.data?.robots) ? state.data.robots : [];
}

function robotCanBeControlled(robot) {
  return Boolean(String(robot?.ipAddress || "").trim());
}

function controlRobots() {
  return videoRobots().filter(robotCanBeControlled);
}

function robotIsOffline(robot) {
  return String(robot?.networkStatus || robot?.telemetryStatus || "").toLowerCase() === "offline";
}

function robotIsOnline(robot) {
  return String(robot?.networkStatus || robot?.telemetryStatus || "").toLowerCase() === "online";
}

function findControlRobot(robotId) {
  return controlRobots().find((robot) => String(robot.id) === String(robotId)) || null;
}

function resolveControlRobot() {
  const robots = controlRobots();
  if (!robots.length) {
    state.control.robotId = "";
    return null;
  }
  const current = findControlRobot(state.control.robotId);
  if (current) return current;
  const next = robots.find(robotIsOnline) || robots[0];
  state.control.robotId = String(next.id);
  return next;
}

function renderControlRobotOptions(selectedValue = "") {
  const robots = videoRobots();
  if (!robots.length) return `<option value="">暂无机器人，请先添加机器人</option>`;
  return robots.map((robot) => {
    const value = String(robot.id);
    const disabled = robotCanBeControlled(robot) ? "" : " disabled";
    const selected = value === String(selectedValue) ? " selected" : "";
    return `<option value="${escapeHtml(value)}"${selected}${disabled}>${escapeHtml(robotOptionLabel(robot))}</option>`;
  }).join("");
}

function resolveMainVideoRobot() {
  const robots = videoRobots();
  if (!robots.length) {
    state.video.mainRobotId = "";
    return null;
  }
  const current = robots.find((robot) => String(robot.id) === String(state.video.mainRobotId));
  if (current && !robotIsOffline(current)) {
    return current;
  }
  const next = robots.find(robotIsOnline) || robots[0];
  state.video.mainRobotId = String(next.id);
  return next;
}

function cameraStreamUrl(robot) {
  return robot ? `/api/robots/${encodeURIComponent(robot.id)}/camera/stream` : "";
}

function cameraSnapshotBaseUrl(robot) {
  return robot ? `/api/robots/${encodeURIComponent(robot.id)}/camera/snapshot` : "";
}

function cameraSnapshotUrl(robot) {
  const base = cameraSnapshotBaseUrl(robot);
  return base ? `${base}?t=${state.video.snapshotTick}` : "";
}

function renderVideoPage() {
  const robots = videoRobots();
  const mainRobot = resolveMainVideoRobot();
  const vnc = appConfig.vnc || appConfig.video?.vnc || {};
  const proxyHost = vnc.proxyHost || window.location.hostname;
  const proxyPort = vnc.proxyPort || 6080;
  const vncTargetHost = mainRobot?.ipAddress || vnc.targetHost || "未选择";
  const targetPort = vnc.targetPort || 5900;
  const viewOnly = vnc.viewOnly !== false;
  const vncPassword = vnc.password || "";
  const frameParams = new URLSearchParams({
    host: proxyHost,
    port: String(proxyPort),
    view_only: viewOnly ? "1" : "0",
    client: "3",
  });
  if (vncPassword) {
    frameParams.set("password", vncPassword);
  }
  if (!robots.length) {
    return `
      <section class="panel video-console">
        <div class="panel-header">
          <div>
            <h2>车队实时画面</h2>
            <p class="muted">添加机器人后，这里会自动生成每辆车的摄像头画面。</p>
          </div>
        </div>
        <div class="empty-state">暂无机器人，请先在“机器人状态”中添加小车。</div>
      </section>
    `;
  }

  const mainStatus = localizeToken(mainRobot.networkStatus || mainRobot.telemetryStatus || "offline");
  const mainStreamUrl = cameraStreamUrl(mainRobot);
  const cardMarkup = robots.map((robot) => {
    const selected = String(robot.id) === String(state.video.mainRobotId);
    const snapshotBase = cameraSnapshotBaseUrl(robot);
    const snapshotUrl = cameraSnapshotUrl(robot);
    const status = robot.networkStatus || robot.telemetryStatus || "offline";
    return `
      <button class="video-robot-card${selected ? " active" : ""}" type="button" data-video-select data-id="${robot.id}">
        <div class="video-thumb-shell">
          <img
            class="video-thumb"
            src="${escapeHtml(snapshotUrl)}"
            alt="${escapeHtml(robot.model)} 摄像头快照"
            width="640"
            height="400"
            loading="lazy"
            data-video-snapshot
            data-video-snapshot-base="${escapeHtml(snapshotBase)}"
          >
        </div>
        <div class="video-card-body">
          <div>
            <strong>${escapeHtml(robot.model)}</strong>
            <p>${escapeHtml(robot.ipAddress || "未配置 IP")}</p>
          </div>
          <span class="${pillClass(status)}">${escapeHtml(localizeToken(status))}</span>
        </div>
        <div class="video-card-meta">
          <span>最近上报 ${escapeHtml(formatDateTime(robot.lastSeenAt || robot.createdAt))}</span>
          <span>信号 ${robot.signal ?? "-"}%</span>
        </div>
      </button>
    `;
  }).join("");

  return `
    <section class="panel video-console camera-console">
      <div class="panel-header">
        <div>
          <h2>车队实时画面</h2>
          <p class="muted">主画面使用 MJPEG 实时流；下方小画面按 2 秒刷新快照，点击任意车辆即可切换主画面。</p>
        </div>
        <div class="panel-actions">
          <a class="secondary-button" href="${escapeHtml(mainStreamUrl)}" target="_blank" rel="noreferrer">打开主画面源</a>
        </div>
      </div>
      <div class="video-main-layout">
        <div class="camera-frame-shell video-main-frame">
          <img class="camera-stream" src="${escapeHtml(mainStreamUrl)}" alt="${escapeHtml(mainRobot.model)} 实时画面" width="1280" height="720">
        </div>
        <aside class="video-main-meta">
          <span class="panel-kicker">主显示</span>
          <h3>${escapeHtml(mainRobot.model)}</h3>
          <p>${escapeHtml(mainRobot.ipAddress || "未配置 IP")}</p>
          <div class="inline-meta">
            <span class="${pillClass(mainRobot.networkStatus || mainRobot.telemetryStatus || "offline")}">网络 ${escapeHtml(mainStatus)}</span>
            <span class="meta-pill">信号 ${mainRobot.signal ?? "-"}%</span>
            <span class="meta-pill">最近上报 ${escapeHtml(formatDateTime(mainRobot.lastSeenAt || mainRobot.createdAt))}</span>
          </div>
          <p class="muted">如果主画面加载失败，通常是该车的 <code>mjpg_streamer</code> 未运行或 8080 端口不可达。</p>
        </aside>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h3>车辆画面列表</h3>
          <p class="muted">共 ${robots.length} 辆车，快照每 ${VIDEO_SNAPSHOT_REFRESH_MS / 1000} 秒刷新一次。</p>
        </div>
      </div>
      <div class="video-wall-grid">
        ${cardMarkup}
      </div>
    </section>

    <section class="panel video-fallback-panel">
      <div class="panel-header">
        <div>
          <h3>桌面调试入口</h3>
          <p class="muted">仅用于排障，不作为摄像头画面来源。</p>
        </div>
        <div class="panel-actions">
          <a class="secondary-button" href="/static/novnc-lite.html?${frameParams.toString()}" target="_blank" rel="noreferrer">打开 noVNC 调试</a>
        </div>
      </div>
      <p class="muted">
        noVNC 代理：<code>${escapeHtml(proxyHost)}:${proxyPort}</code>，当前主车：<code>${escapeHtml(vncTargetHost)}:${targetPort}</code>。
      </p>
    </section>
  `;
}

function ensurePerceptionRobotSelection() {
  const robots = videoRobots();
  if (!robots.length) {
    state.perception.robotId = "";
    state.perception.latest = null;
    return null;
  }
  const current = robots.find((robot) => String(robot.id) === String(state.perception.robotId));
  const next = current || robots.find(robotIsOnline) || robots[0];
  state.perception.robotId = String(next.id);
  return next;
}

async function loadPerceptionLatest(force = false) {
  const robot = ensurePerceptionRobotSelection();
  if (!robot || (!force && state.perception.latest?.robotId === robot.id)) return;
  state.perception.loading = true;
  state.perception.error = "";
  renderCurrentPage();
  try {
    state.perception.latest = await apiFetch(`/api/robots/${encodeURIComponent(robot.id)}/perception/latest`);
  } catch (error) {
    state.perception.latest = null;
    state.perception.error = error.message;
  } finally {
    state.perception.loading = false;
    if (state.pageId === "perception") renderCurrentPage();
  }
}

function perceptionAssetImage(latest) {
  const overlay = latest?.assets?.overlay || "";
  if (!overlay) {
    return `<div class="video-unavailable"><strong>暂无感知画面</strong><p class="muted">等待 Orin 上传真实 overlay 图。</p></div>`;
  }
  return `<img class="camera-stream perception-overlay" src="${escapeHtml(overlay)}?t=${Date.now()}" width="960" height="540" alt="Orin 智能感知结果叠加图" loading="lazy">`;
}

function renderStatusDict(items) {
  const entries = Object.entries(items || {});
  if (!entries.length) return `<p class="muted">暂无传感器状态。</p>`;
  return `<div class="control-target-grid">${entries.map(([key, value]) => `<span>${escapeHtml(key)} <strong>${escapeHtml(value)}</strong></span>`).join("")}</div>`;
}

function renderPerceptionObjects(title, items, emptyText) {
  const rows = (items || []).map((item) => `
    <tr>
      <td>${escapeHtml(item.trackId ?? item.id ?? "-")}</td>
      <td>${escapeHtml(item.class || item.label || "-")}</td>
      <td>${escapeHtml(item.confidence ?? "-")}</td>
      <td>${escapeHtml(item.distanceM ?? item.depthM ?? "-")}</td>
    </tr>
  `);
  return `<section class="panel"><h2>${title}</h2>${rows.length ? renderTable("perception-objects", ["ID", "类别", "置信度", "距离/深度"], rows) : `<div class="empty-state">${emptyText}</div>`}</section>`;
}

function renderPerceptionPage() {
  const robot = ensurePerceptionRobotSelection();
  const robots = videoRobots();
  const latest = state.perception.latest;
  const frame = latest?.frame;
  const performance = latest?.performance || {};
  if (!robots.length) return `<section class="panel"><div class="empty-state">暂无机器人，请先添加并接入 Orin 设备。</div></section>`;
  return `
    <section class="panel video-console perception-console">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Orin AI</p>
          <h2>智能感知</h2>
          <p class="muted">只展示真实上报的检测、分割、融合和跟踪结果，不参与运动控制。</p>
        </div>
        <div class="button-row">
          <select id="perception-robot">${renderControlRobotOptions(state.perception.robotId)}</select>
          <button class="secondary-button" id="perception-refresh" type="button"${state.perception.loading ? " disabled" : ""}>刷新结果</button>
        </div>
      </div>
      ${state.perception.error ? `<p class="form-error" role="alert">${escapeHtml(state.perception.error)}</p>` : ""}
      <div class="video-main-layout">
        <div class="camera-frame-shell video-main-frame">${state.perception.loading ? `<div class="video-unavailable"><strong>正在读取感知结果</strong></div>` : perceptionAssetImage(latest)}</div>
        <aside class="video-main-meta">
          <h3>${escapeHtml(robot?.model || "未选择机器人")}</h3>
          <p class="muted">IP：${escapeHtml(robot?.ipAddress || "未配置")} | 网络：${escapeHtml(localizeToken(robot?.networkStatus || "offline"))}</p>
          <div class="control-target-grid">
            <span>帧 ID <strong>${escapeHtml(frame?.frameId || "暂无")}</strong></span>
            <span>模型 <strong>${escapeHtml(performance.model || "未知")}</strong></span>
            <span>精度 <strong>${escapeHtml(performance.precision || "未知")}</strong></span>
            <span>FPS <strong>${escapeHtml(performance.fps ?? "暂无")}</strong></span>
            <span>延迟 <strong>${escapeHtml(performance.latencyMs ?? "暂无")} ms</strong></span>
            <span>融合 <strong>${escapeHtml(latest?.fusionStatus || "offline")}</strong></span>
            <span>更新时间 <strong>${escapeHtml(frame?.createdAt || "暂无")}</strong></span>
          </div>
          <h3>传感器状态</h3>
          ${renderStatusDict(latest?.sensorStatus)}
        </aside>
      </div>
    </section>
    <div class="dual-grid">
      ${renderPerceptionObjects("检测目标", latest?.detections || [], "暂无检测目标。")}
      ${renderPerceptionObjects("跟踪轨迹", latest?.tracks || [], "暂无跟踪轨迹。")}
    </div>
  `;
}

function renderControlPage() {
  const control = appConfig.robotControl || {};
  const selectedRobot = resolveControlRobot();
  const selectableRobots = controlRobots();
  const port = control.port || 9000;
  const disabledReason = controlDisabledReason(selectedRobot, selectableRobots);
  const disabled = disabledReason ? " disabled" : "";
  const targetTitle = selectedRobot ? selectedRobot.model : "未选择机器人";
  const targetHost = selectedRobot?.ipAddress || control.host || "未配置";
  const targetStatus = selectedRobot ? localizeToken(selectedRobot.networkStatus || selectedRobot.telemetryStatus || "offline") : "无可控车辆";
  const lastSeen = selectedRobot ? formatDateTime(selectedRobot.lastSeenAt || selectedRobot.createdAt) : "-";
  const statusTone = selectedRobot ? pillClass(selectedRobot.networkStatus || selectedRobot.telemetryStatus || "offline") : "pill warning";
  return `
    <section class="panel control-console">
      <div class="panel-header">
        <div>
          <h2>远程遥控无人车</h2>
          <p class="muted">按住方向键持续发送速度指令，松开或离开页面会自动发送停车指令。</p>
        </div>
        <div class="panel-actions">
          <button class="secondary-button" id="control-ping" type="button"${disabled}>检测连接</button>
          <button class="danger-button critical-action" id="control-stop" type="button"${disabled}>急停</button>
        </div>
      </div>
      <div class="notice-card danger control-risk-card" role="status" aria-live="polite">
        <strong>真实车辆控制</strong>
        <p>${disabledReason ? escapeHtml(disabledReason) : "当前页面会向所选无人车真实下发速度或停车指令，请确认目标车辆周边安全。"}</p>
      </div>
      <div class="control-layout">
        <div class="control-pad" aria-label="无人车方向控制">
          <button class="control-button diagonal" type="button" data-control-linear="1" data-control-angular="1"${disabled}>↖</button>
          <button class="control-button" type="button" data-control-linear="1" data-control-angular="0"${disabled}>前进</button>
          <button class="control-button diagonal" type="button" data-control-linear="1" data-control-angular="-1"${disabled}>↗</button>
          <button class="control-button" type="button" data-control-linear="0" data-control-angular="1"${disabled}>左转</button>
          <button class="control-button stop critical-action" type="button" data-control-stop${disabled}>停止</button>
          <button class="control-button" type="button" data-control-linear="0" data-control-angular="-1"${disabled}>右转</button>
          <button class="control-button diagonal" type="button" data-control-linear="-1" data-control-angular="-1"${disabled}>↙</button>
          <button class="control-button" type="button" data-control-linear="-1" data-control-angular="0"${disabled}>后退</button>
          <button class="control-button diagonal" type="button" data-control-linear="-1" data-control-angular="1"${disabled}>↘</button>
        </div>
        <aside class="control-meta control-target-card stack-form">
          <label>
            <span>选择机器人</span>
            <select id="control-robot"${selectableRobots.length ? "" : " disabled"}>
              ${renderControlRobotOptions(state.control.robotId)}
            </select>
          </label>
          <div>
            <span class="panel-kicker">控制目标</span>
            <h3>${escapeHtml(targetTitle)}</h3>
            <p class="muted">后端通过内网 TCP 长连接转发到树莓派底盘控制服务。</p>
            <div class="control-target-grid">
              <span>地址 <code>${escapeHtml(targetHost)}:${escapeHtml(port)}</code></span>
              <span>网络 <span class="${statusTone}">${escapeHtml(targetStatus)}</span></span>
              <span>最近上报 ${escapeHtml(lastSeen)}</span>
              <span>最近指令 <strong id="control-status" aria-live="polite">${escapeHtml(state.control.status)}</strong></span>
            </div>
          </div>
          <label><span>线速度倍率</span><input id="control-linear-scale" type="range" min="10" max="100" value="35"></label>
          <label><span>角速度倍率</span><input id="control-angular-scale" type="range" min="10" max="100" value="45"></label>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="control"></p>
        </aside>
      </div>
    </section>
  `;
}

function controlDisabledReason(selectedRobot, selectableRobots) {
  if (!selectableRobots.length) return "没有可控车辆：请先在机器人或设备管理中配置车辆 IP。";
  if (!selectedRobot) return "请选择要控制的机器人。";
  if (robotIsOffline(selectedRobot)) return "当前目标处于离线状态，已禁用运动、停止和急停操作。";
  return "";
}

function renderZonesPage() {
  const zonesData = state.pageData.zones;
  if (!zonesData) {
    return renderLoadingPage("区域控制", "创建、编辑和删除巡检区域。");
  }
  return `
    ${renderStats()}
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>新建区域</h2><p class="muted">在地图上点选轮廓并选择区域颜色</p></div></div>
        <form id="zone-form" class="stack-form">
          <div class="grid-form">
            <label><span>区域名称</span><input name="name" placeholder="例：1号泊位巡检区" required></label>
            <label><span>所属区域</span><select name="areaId">${renderSelectOptions(zonesData.areas || [], state.formAreaDefaults.zone.value, "请选择区域")}</select></label>
            <label><span>区域类型</span><select name="type"><option value="inspection">巡检区</option><option value="charging">充电区</option><option value="storage">仓储区</option><option value="restricted">管控区</option></select></label>
            <label><span>风险等级</span><select name="risk"><option value="low">低</option><option value="medium" selected>中</option><option value="high">高</option></select></label>
            <label><span>状态</span><select name="status"><option value="active" selected>启用</option><option value="paused">暂停</option></select></label>
            <label><span>巡检频率</span><input name="frequency" value="30分钟/次"></label>
          </div>
          <input name="strokeColor" type="hidden">
          <input name="fillColor" type="hidden">
          <input name="path" type="hidden">
          <div class="inline-meta">
            <span class="meta-pill" id="zone-color-preview">色</span>
            <span class="muted" id="zone-draw-status">单击地图加点，右键撤销，至少 3 点即可保存。</span>
          </div>
          <p id="zone-area-status" class="muted">${escapeHtml(areaSelectionMessage())}</p>
          <div class="zone-palette">
            ${ZONE_PALETTE.map((color) => {
              const label = `选择${zoneColorLabel(color)}区域颜色`;
              return `<button class="zone-color-chip" type="button" data-zone-color="${color}" style="background:${color}" aria-label="${escapeHtml(label)}" title="${escapeHtml(label)}" aria-pressed="${color === state.zoneDraft.strokeColor ? "true" : "false"}"></button>`;
            }).join("")}
          </div>
          <label><span>备注</span><textarea name="notes" placeholder="说明区域用途、重点设备和巡检要求"></textarea></label>
          <div class="button-row">
            <button class="secondary-button" id="zone-reset-button" type="button">清空绘制</button>
            <button class="secondary-button" id="zone-complete-button" type="button" disabled>完成绘制</button>
            <button class="primary-button" type="submit">创建区域</button>
          </div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="zone"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header"><div><h2>区域列表</h2><p class="muted">已保存区域与风险标签</p></div></div>
        <div id="zones-map" class="map-shell"><div class="map-fallback">检测到高德地图后将在此渲染。</div></div>
        <div class="list-stack">
          ${zonesData.items.length ? zonesData.items.map((zone) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(zone.name)}</strong>
                <p>${escapeHtml(localizeToken(zone.type))} · ${escapeHtml(zone.areaName || "未设置区域")} · ${escapeHtml(zone.notes || "暂无备注")}</p>
              </div>
              <div>
                <span class="${pillClass(zone.risk)}">${escapeHtml(localizeToken(zone.risk))}</span>
                <p class="muted">${escapeHtml(zone.frequency)}</p>
                <div class="inline-meta">
                  <button class="secondary-button" type="button" data-zone-edit data-id="${zone.id}">编辑</button>
                  <button class="danger-button" type="button" data-zone-delete data-id="${zone.id}">删除</button>
                </div>
              </div>
            </div>
          `).join("") : `<div class="empty-state">暂无区域配置。</div>`}
        </div>
        ${renderPagination("zones", zonesData, "个区域")}
      </article>
    </section>
  `;
}

function renderLoadingPage(title, description) {
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>${escapeHtml(title)}</h2>
          <p class="muted">${escapeHtml(description)}</p>
        </div>
      </div>
      <div class="empty-state">加载中…</div>
    </section>
  `;
}

function renderSelectOptions(items, selectedValue = "", emptyLabel = "未设置", labelFormatter = null) {
  const normalized = selectedValue === undefined || selectedValue === null ? "" : String(selectedValue);
  const options = [];
  if (emptyLabel !== null) {
    options.push(`<option value="">${escapeHtml(emptyLabel)}</option>`);
  }
  items.forEach((item) => {
    const value = String(item.id);
    const label = labelFormatter
      ? labelFormatter(item)
      : String(item.name || item.title || item.username || item.displayName || item.id);
    options.push(
      `<option value="${escapeHtml(value)}"${value === normalized ? " selected" : ""}>${escapeHtml(label)}</option>`,
    );
  });
  return options.join("");
}

function formatCoordinate(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(6) : "-";
}

function formatPorts(value) {
  return Array.isArray(value) && value.length ? value.join(", ") : "-";
}

async function fetchRobotDiscovery(refresh = false) {
  state.robotDiscovery.loading = true;
  state.robotDiscovery.error = "";
  if (state.pageId === "status") {
    renderCurrentPage();
  }
  try {
    const query = refresh ? "?refresh=1" : "";
    const payload = await apiFetch(`/api/robots/discovery${query}`);
    state.robotDiscovery.items = payload.items || [];
    state.robotDiscovery.scannedAt = payload.scannedAt || "";
    state.robotDiscovery.expiresAt = payload.expiresAt || "";
    state.robotDiscovery.subnets = payload.subnets || [];
    const selectedStillAvailable = state.robotDiscovery.items.some((item) => (
      item.ipAddress === state.robotDiscovery.selectedIp &&
      (item.confirmed || item.ipAddress === state.robotDiscovery.manualConfirmedIp)
    ));
    if (!selectedStillAvailable) {
      state.robotDiscovery.selectedIp = "";
    }
  } catch (error) {
    state.robotDiscovery.error = error.message;
  } finally {
    state.robotDiscovery.loading = false;
    if (state.pageId === "status") {
      renderCurrentPage();
    }
  }
}

function pointInPolygon(coords, polygon) {
  const [lng, lat] = coords;
  let inside = false;
  for (let current = 0, previous = polygon.length - 1; current < polygon.length; previous = current, current += 1) {
    const [currentLng, currentLat] = polygon[current];
    const [previousLng, previousLat] = polygon[previous];
    const intersects = ((currentLat > lat) !== (previousLat > lat))
      && (lng < ((previousLng - currentLng) * (lat - currentLat)) / ((previousLat - currentLat) || 1e-12) + currentLng);
    if (intersects) inside = !inside;
  }
  return inside;
}

function resolveZoneForPoint(coords) {
  return (state.data?.zones || []).find((zone) => pointInPolygon(coords, zone.path)) || null;
}

function areaSelectionMessage() {
  if (state.geo.status === "locating") return "正在根据当前位置匹配默认区域。";
  if (state.geo.currentAreaId) return `已按当前位置匹配到区域：${state.geo.currentAreaName || "未命名区域"}。`;
  if (state.geo.status === "failed") return "定位失败，请手动选择区域。";
  if (state.geo.coords) return "当前位置不在任何已配置区域内，请手动选择区域。";
  return "等待定位结果，或手动选择区域。";
}

function syncResolvedGeoArea(coords) {
  const zone = Array.isArray(coords) ? resolveZoneForPoint(coords) : null;
  state.geo.currentZoneId = zone ? Number(zone.id) : null;
  state.geo.currentZoneName = zone?.name || "";
  state.geo.currentAreaId = zone?.areaId == null ? null : Number(zone.areaId);
  state.geo.currentAreaName = zone?.areaName || "";
  Object.values(state.formAreaDefaults).forEach((entry) => {
    if (!entry.touched) {
      entry.value = state.geo.currentAreaId == null ? "" : String(state.geo.currentAreaId);
    }
  });
}

function syncManagedFormAreaUi() {
  const bindings = [
    ["device", "device-form", "device-area-status"],
    ["point", "point-form", "point-area-status"],
    ["route", "route-form", "route-area-status"],
    ["zone", "zone-form", "zone-area-status"],
  ];
  bindings.forEach(([formKey, formId, statusId]) => {
    const form = document.getElementById(formId);
    const statusNode = document.getElementById(statusId);
    if (!form) return;
    const field = form.elements.namedItem("areaId");
    if (field && !state.formAreaDefaults[formKey].touched) {
      field.value = state.formAreaDefaults[formKey].value || "";
    }
    if (statusNode) {
      statusNode.textContent = areaSelectionMessage();
    }
  });
  updateLocationLabels(state.geo.locationText || state.data?.site?.city || "未知位置");
}

function bindAreaDefaultSelect(formId, formKey) {
  const form = document.getElementById(formId);
  if (!form) return;
  const field = form.elements.namedItem("areaId");
  if (!field) return;
  field.value = state.formAreaDefaults[formKey].value || "";
  field.addEventListener("change", () => {
    state.formAreaDefaults[formKey].touched = true;
    state.formAreaDefaults[formKey].value = field.value || "";
    syncManagedFormAreaUi();
  });
}

function resetAreaDefault(formKey, form) {
  const nextValue = state.geo.currentAreaId == null ? "" : String(state.geo.currentAreaId);
  state.formAreaDefaults[formKey] = { value: nextValue, touched: false };
  const field = form?.elements?.namedItem?.("areaId");
  if (field) {
    field.value = nextValue;
  }
  syncManagedFormAreaUi();
}

function ensureAreaSelectedForSubmit(formKey, form) {
  const field = form?.elements?.namedItem?.("areaId");
  const value = field?.value?.trim?.() || "";
  if (value) {
    state.formAreaDefaults[formKey].value = value;
    return value;
  }
  throw new Error(areaSelectionMessage());
}

function syncPointDraftUi() {
  const form = document.getElementById("point-form");
  const status = document.getElementById("point-picker-status");
  if (!form) return;
  const latField = form.elements.namedItem("lat");
  const lngField = form.elements.namedItem("lng");
  if (latField) latField.value = state.pointDraft.coords ? state.pointDraft.coords[1].toFixed(6) : "";
  if (lngField) lngField.value = state.pointDraft.coords ? state.pointDraft.coords[0].toFixed(6) : "";
  if (status) {
    status.textContent = state.pointDraft.coords
      ? `已选择 ${state.pointDraft.zoneName} 内的巡检点：${state.pointDraft.coords[1].toFixed(6)}, ${state.pointDraft.coords[0].toFixed(6)}`
      : "请在地图中的巡检区域内点击选择巡检点。";
  }
}

function resetPointDraft() {
  state.pointDraft.coords = null;
  state.pointDraft.zoneId = null;
  state.pointDraft.zoneName = "";
  if (state.pointDraft.marker) {
    state.pointDraft.marker.setMap(null);
    state.pointDraft.marker = null;
  }
  syncPointDraftUi();
}

function setupPointPicker(map) {
  syncPointDraftUi();
  map.on("click", (event) => {
    const coords = [event.lnglat.getLng(), event.lnglat.getLat()];
    const zone = resolveZoneForPoint(coords);
    if (!zone) {
      setFormError("point", "请在巡检区域多边形内部点击选择巡检点。");
      return;
    }
    setFormError("point");
    state.pointDraft.coords = coords;
    state.pointDraft.zoneId = zone.id;
    state.pointDraft.zoneName = zone.name;
    if (!state.formAreaDefaults.point.touched) {
      state.formAreaDefaults.point.value = zone.areaId == null ? "" : String(zone.areaId);
      syncManagedFormAreaUi();
    }
    if (!state.pointDraft.marker) {
      state.pointDraft.marker = new AMap.Marker({
        map,
        position: coords,
        title: `巡检点 | ${zone.name}`,
        bubble: true,
      });
    } else {
      state.pointDraft.marker.setPosition(coords);
      state.pointDraft.marker.setMap(map);
    }
    syncPointDraftUi();
  });
}

function findPageItem(pageId, itemId) {
  const source = state.pageData[pageId];
  const items = Array.isArray(source?.items) ? source.items : [];
  return items.find((item) => Number(item.id) === Number(itemId)) || null;
}

function safePageValue(value, fallback = 1) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function safePageSize(value, fallback = 10) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.min(parsed, 100);
}

function normalizeDeviceStatusFilter(value) {
  const normalized = String(value || "").trim();
  return DEVICE_STATUS_FILTERS.has(normalized) ? normalized : "";
}

function normalizePagedPayload(payload, fallbackPage = 1, fallbackSize = 10) {
  const source = payload && typeof payload === "object" ? payload : {};
  const items = Array.isArray(source.items) ? source.items : [];
  const size = safePageSize(source.size, fallbackSize);
  const total = Math.max(0, Number(source.total) || 0);
  const totalPages = Math.max(1, Math.ceil(total / size));
  const page = Math.min(totalPages, safePageValue(source.page, fallbackPage));
  return { ...source, items, total, page, size };
}

function activeManagementState(pageId = state.pageId) {
  const config = MANAGEMENT_PAGE_CONFIG[pageId];
  if (!config) return null;
  const rawTab = state[config.tabStateKey] || config.defaultTab;
  const tab = config.tabs[rawTab] ? rawTab : config.defaultTab;
  if (state[config.tabStateKey] !== tab) state[config.tabStateKey] = tab;
  return { config, tab, current: config.tabs[tab] };
}

function applyPagedParamsFromUrl(paging, params) {
  if (!paging) return;
  if (params.has("page")) paging.page = safePageValue(params.get("page"), paging.page);
  if (params.has("size")) paging.size = safePageSize(params.get("size"), paging.size);
}

function writePagedParamsToUrl(params, paging) {
  const page = safePageValue(paging?.page, 1);
  const size = safePageSize(paging?.size, 10);
  if (page !== 1) params.set("page", String(page));
  if (size !== 10) params.set("size", String(size));
}

function clearListUrlParams(params) {
  ["tab", "page", "size", "keyword", "status"].forEach((key) => params.delete(key));
}

function hydrateListStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const management = activeManagementState();
  if (management) {
    const tab = params.get("tab") || management.config.defaultTab;
    if (management.config.tabs[tab]) state[management.config.tabStateKey] = tab;
    const current = activeManagementState();
    applyPagedParamsFromUrl(state.paging[current.current.pagingKey], params);
    if (params.has("keyword")) {
      state.managementFilters[current.current.filterKey].keyword = params.get("keyword") || "";
    }
    return;
  }
  if (COMMAND_PAGE_IDS.has(state.pageId)) {
    applyPagedParamsFromUrl(state.paging.controlCommands, params);
    return;
  }
  if (!URL_SYNC_PAGE_IDS.has(state.pageId)) return;
  const paging = state.paging[state.pageId];
  if (!paging) return;
  if (params.has("page")) {
    paging.page = safePageValue(params.get("page"), paging.page);
  }
  if (params.has("size")) {
    paging.size = safePageSize(params.get("size"), paging.size);
  }
  if (state.pageId === "areas" && params.has("keyword")) {
    paging.keyword = params.get("keyword") || "";
  }
  if (state.pageId === "devices") {
    state.deviceFilters.keyword = params.get("keyword") || "";
    state.deviceFilters.status = normalizeDeviceStatusFilter(params.get("status"));
  }
}

function syncCurrentPageUrl() {
  if (typeof window.history?.replaceState !== "function") return;
  const params = new URLSearchParams(window.location.search);
  clearListUrlParams(params);
  const management = activeManagementState();
  if (management) {
    if (management.tab !== management.config.defaultTab) params.set("tab", management.tab);
    writePagedParamsToUrl(params, state.paging[management.current.pagingKey]);
    const keyword = state.managementFilters[management.current.filterKey]?.keyword?.trim();
    if (keyword) params.set("keyword", keyword);
  } else if (COMMAND_PAGE_IDS.has(state.pageId)) {
    writePagedParamsToUrl(params, state.paging.controlCommands);
  } else if (URL_SYNC_PAGE_IDS.has(state.pageId) && state.paging[state.pageId]) {
    const paging = state.paging[state.pageId];
    writePagedParamsToUrl(params, paging);
    if (state.pageId === "areas" && paging.keyword?.trim()) {
      params.set("keyword", paging.keyword.trim());
    }
    if (state.pageId === "devices") {
      if (state.deviceFilters.keyword.trim()) params.set("keyword", state.deviceFilters.keyword.trim());
      const status = normalizeDeviceStatusFilter(state.deviceFilters.status);
      if (status) params.set("status", status);
    }
  } else {
    return;
  }
  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (nextUrl !== currentUrl) {
    window.history.replaceState({}, "", nextUrl);
  }
}

function pageSizeOptionsMarkup(currentSize) {
  const normalized = safePageSize(currentSize, 10);
  return PAGE_SIZE_OPTIONS.map((size) => (
    `<option value="${size}"${size === normalized ? " selected" : ""}>${size} 条/页</option>`
  )).join("");
}

function ensureExistingAreaSelection() {
  const currentItems = state.pageData.areas?.items || [];
  const idSet = new Set(currentItems.map((item) => Number(item.id)));
  state.areaSelection = state.areaSelection.filter((id) => idSet.has(Number(id)));
}

function renderPagination(pageId, payload, label = "条") {
  const page = safePageValue(payload?.page, 1);
  const size = safePageSize(payload?.size, 10);
  const total = Math.max(0, Number(payload?.total) || 0);
  const totalPages = Math.max(1, Math.ceil(total / size));
  const disablePrev = page <= 1;
  const disableNext = page >= totalPages;
  return `
    <div class="pagination-bar">
      <div class="inline-meta">
        <span class="muted">共 ${total} ${escapeHtml(label)}，第 ${page} / ${totalPages} 页</span>
        <label class="pagination-size">
          <span class="muted">每页</span>
          <select data-page-size="${pageId}">${pageSizeOptionsMarkup(size)}</select>
        </label>
      </div>
      <div class="button-row">
        <button class="secondary-button" type="button" data-page-nav="${pageId}" data-page-target="${page - 1}"${disablePrev ? " disabled" : ""}>上一页</button>
        <button class="secondary-button" type="button" data-page-nav="${pageId}" data-page-target="${page + 1}"${disableNext ? " disabled" : ""}>下一页</button>
      </div>
    </div>
  `;
}

function bindPagination(pageId) {
  document.querySelectorAll(`[data-page-nav="${pageId}"]`).forEach((button) => {
    button.addEventListener("click", async () => {
      const targetPage = safePageValue(button.dataset.pageTarget, state.paging[pageId]?.page || 1);
      if (!state.paging[pageId]) return;
      if (targetPage === state.paging[pageId].page) return;
      state.paging[pageId].page = targetPage;
      await ensureManagementPageData(pageId, true);
    });
  });
  document.querySelectorAll(`[data-page-size="${pageId}"]`).forEach((select) => {
    select.addEventListener("change", async () => {
      if (!state.paging[pageId]) return;
      const nextSize = safePageSize(select.value, state.paging[pageId].size || 10);
      if (nextSize === state.paging[pageId].size) return;
      state.paging[pageId].size = nextSize;
      state.paging[pageId].page = 1;
      await ensureManagementPageData(pageId, true);
    });
  });
}

async function fetchAllPagedItems(url) {
  const items = [];
  let page = 1;
  const size = 100;
  while (true) {
    const query = new URLSearchParams({
      page: String(page),
      size: String(size),
    });
    const payload = normalizePagedPayload(await apiFetch(`${url}?${query.toString()}`), page, size);
    items.push(...(payload.items || []));
    const totalPages = Math.max(1, Math.ceil(payload.total / payload.size));
    if (page >= totalPages || payload.items.length === 0) {
      break;
    }
    page += 1;
  }
  return items;
}

async function fetchAreaOptions() {
  return fetchAllPagedItems("/api/areas");
}

async function fetchDeviceOptions() {
  return fetchAllPagedItems("/api/devices");
}

async function fetchPointOptions() {
  return fetchAllPagedItems("/api/points");
}

async function fetchPagedResource(pageId, url, extraParams = {}) {
  const paging = state.paging[pageId];
  const query = new URLSearchParams({
    page: String(safePageValue(paging.page, 1)),
    size: String(safePageSize(paging.size, 10)),
  });
  Object.entries(extraParams).forEach(([key, value]) => {
    const normalized = String(value ?? "").trim();
    if (normalized) query.set(key, normalized);
  });
  let payload = normalizePagedPayload(await apiFetch(`${url}?${query.toString()}`), paging.page, paging.size);
  const totalPages = Math.max(1, Math.ceil(payload.total / payload.size));
  if (paging.page > totalPages && payload.total > 0) {
    paging.page = totalPages;
    query.set("page", String(totalPages));
    payload = normalizePagedPayload(await apiFetch(`${url}?${query.toString()}`), paging.page, paging.size);
  } else {
    paging.page = payload.page;
    paging.size = payload.size;
  }
  return payload;
}

async function ensureManagementPageData(pageId, force = false) {
  if (!force && state.pageData[pageId]) {
    return state.pageData[pageId];
  }

  if (pageId === "users") {
    state.pageData.users = await fetchPagedResource("users", "/api/users");
  } else if (pageId === "devices") {
    const [devices, areas] = await Promise.all([
      fetchPagedResource("devices", "/api/devices"),
      fetchAreaOptions(),
    ]);
    state.pageData.devices = { ...devices, areas };
  } else if (pageId === "areas") {
    const paging = state.paging.areas;
    const query = new URLSearchParams({
      page: String(safePageValue(paging.page, 1)),
      size: String(safePageSize(paging.size, 10)),
    });
    if (paging.keyword?.trim()) {
      query.set("keyword", paging.keyword.trim());
    }
    let payload = normalizePagedPayload(await apiFetch(`/api/areas?${query.toString()}`), paging.page, paging.size);
    const totalPages = Math.max(1, Math.ceil(payload.total / payload.size));
    if (paging.page > totalPages && payload.total > 0) {
      paging.page = totalPages;
      query.set("page", String(totalPages));
      payload = normalizePagedPayload(await apiFetch(`/api/areas?${query.toString()}`), paging.page, paging.size);
    } else {
      paging.page = payload.page;
      paging.size = payload.size;
    }
    state.pageData.areas = payload;
    ensureExistingAreaSelection();
  } else if (pageId === "points") {
    const [points, areas, devices] = await Promise.all([
      fetchPagedResource("points", "/api/points"),
      fetchAreaOptions(),
      fetchDeviceOptions(),
    ]);
    state.pageData.points = {
      ...points,
      areas,
      devices,
    };
  } else if (pageId === "routes") {
    const previousRoutePoints = state.pageData.routes?.routePoints || {};
    const [routes, areas, points] = await Promise.all([
      fetchPagedResource("routes", "/api/routes"),
      fetchAreaOptions(),
      fetchPointOptions(),
    ]);
    state.pageData.routes = {
      ...routes,
      areas,
      points,
      routePoints: previousRoutePoints,
    };
    if (
      state.routeEditor.routeId &&
      !state.pageData.routes.items.some((route) => Number(route.id) === Number(state.routeEditor.routeId))
    ) {
      state.routeEditor = { routeId: null, selected: [] };
    }
  } else if (pageId === "zones") {
    const [zones, areas] = await Promise.all([fetchPagedResource("zones", "/api/zones"), fetchAreaOptions()]);
    state.pageData.zones = { ...zones, areas };
  } else if (pageId === "reports") {
    state.pageData.reports = await fetchPagedResource("reports", "/api/reports");
  } else if (pageId === "device_management") {
    const [categories, devices, units, channels, areas, robots, categoryOptions, deviceOptions] = await Promise.all([
      fetchPagedResource("deviceCategories", "/api/device-categories", filterParams("deviceCategories")),
      fetchPagedResource("devices", "/api/devices", filterParams("managedDevices")),
      fetchPagedResource("onboardUnits", "/api/onboard-units", filterParams("onboardUnits")),
      fetchPagedResource("networkChannels", "/api/network-channels", filterParams("networkChannels")),
      fetchAreaOptions(),
      Promise.resolve(videoRobots()),
      fetchAllPagedItems("/api/device-categories"),
      fetchDeviceOptions(),
    ]);
    state.pageData.device_management = { categories, devices, units, channels, areas, robots, categoryOptions, deviceOptions };
  } else if (pageId === "device_control") {
    const [devices, units, channels, commands] = await Promise.all([
      fetchDeviceOptions(),
      fetchAllPagedItems("/api/onboard-units"),
      fetchAllPagedItems("/api/network-channels"),
      fetchPagedResource("controlCommands", "/api/control/commands"),
    ]);
    state.pageData.device_control = { devices, units, channels, commands, robots: videoRobots() };
  } else if (pageId === "cluster_management") {
    const [clusters, nodes, formations, robots, clusterOptions] = await Promise.all([
      fetchPagedResource("clusters", "/api/clusters", filterParams("clusters")),
      fetchPagedResource("clusterNodes", "/api/cluster-nodes", filterParams("clusterNodes")),
      fetchPagedResource("formations", "/api/formations", filterParams("formations")),
      Promise.resolve(videoRobots()),
      fetchAllPagedItems("/api/clusters"),
    ]);
    state.pageData.cluster_management = { clusters, nodes, formations, robots, clusterOptions };
  } else if (pageId === "cluster_control") {
    const [clusters, nodes, formations, commands] = await Promise.all([
      fetchAllPagedItems("/api/clusters"),
      fetchAllPagedItems("/api/cluster-nodes"),
      fetchAllPagedItems("/api/formations"),
      fetchPagedResource("controlCommands", "/api/control/commands"),
    ]);
    state.pageData.cluster_control = { clusters, nodes, formations, commands, robots: videoRobots() };
  }

  if (state.pageId === pageId) {
    syncCurrentPageUrl();
    renderCurrentPage();
  }
  return state.pageData[pageId];
}

async function ensureRoutePoints(routeId, force = false) {
  if (!state.pageData.routes) {
    await ensureManagementPageData("routes");
  }
  const current = state.pageData.routes?.routePoints?.[routeId];
  if (!force && current) {
    state.routeEditor.selected = current.map((item) => item.id);
    return current;
  }
  const payload = await apiFetch(`/api/routes/${routeId}/points`);
  state.pageData.routes.routePoints = {
    ...(state.pageData.routes.routePoints || {}),
    [routeId]: payload.items || [],
  };
  state.routeEditor.selected = (payload.items || []).map((item) => item.id);
  if (state.pageId === "routes") {
    renderCurrentPage();
  }
  return payload.items || [];
}

function bindManagedForm(formId, errorKey, handler) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(errorKey);
    try {
      await handler(form);
    } catch (error) {
      setFormError(errorKey, error.message);
    }
  });
}

function renderModalField(field, values) {
  const value = values[field.name] ?? "";
  const required = field.required ? "required" : "";
  const disabled = field.disabled ? "disabled" : "";
  const readonly = field.readonly ? "readonly" : "";
  const className = field.className ? ` ${field.className}` : "";

  if (field.type === "select") {
    return `
      <label class="${className.trim()}">
        <span>${escapeHtml(field.label)}</span>
        <select name="${escapeHtml(field.name)}" ${required} ${disabled}>
          ${(field.options || []).map((option) => {
            const optionValue = String(option.value);
            return `<option value="${escapeHtml(optionValue)}"${optionValue === String(value) ? " selected" : ""}>${escapeHtml(option.label)}</option>`;
          }).join("")}
        </select>
      </label>
    `;
  }

  if (field.type === "textarea") {
    return `
      <label class="${className.trim()}">
        <span>${escapeHtml(field.label)}</span>
        <textarea name="${escapeHtml(field.name)}" placeholder="${escapeHtml(field.placeholder || "")}" ${required} ${disabled} ${readonly}>${escapeHtml(value)}</textarea>
      </label>
    `;
  }

  return `
    <label class="${className.trim()}">
      <span>${escapeHtml(field.label)}</span>
      <input
        name="${escapeHtml(field.name)}"
        type="${escapeHtml(field.type || "text")}"
        value="${escapeHtml(value)}"
        placeholder="${escapeHtml(field.placeholder || "")}"
        ${required}
        ${disabled}
        ${readonly}
        ${field.min !== undefined ? `min="${escapeHtml(field.min)}"` : ""}
        ${field.max !== undefined ? `max="${escapeHtml(field.max)}"` : ""}
        ${field.step !== undefined ? `step="${escapeHtml(field.step)}"` : ""}
      />
    </label>
  `;
}

function closeCrudModal() {
  state.modal.onSubmit = null;
  if (crudModalError) crudModalError.textContent = "";
  if (crudModalBody) crudModalBody.innerHTML = "";
  crudModalForm?.reset();
  if (!crudModal) return;
  if (typeof crudModal.close === "function" && crudModal.open) {
    crudModal.close();
  } else {
    crudModal.removeAttribute("open");
  }
}

function showCrudModal({ title, fields, values = {}, saveText = "保存", onSubmit }) {
  if (!crudModal || !crudModalForm || !crudModalBody || !crudModalTitle || !crudModalSave) {
    return;
  }
  if (crudModal.open && typeof crudModal.close === "function") {
    crudModal.close();
  }
  crudModalTitle.textContent = title;
  crudModalSave.textContent = saveText;
  crudModalError.textContent = "";
  crudModalBody.innerHTML = fields.map((field) => renderModalField(field, values)).join("");
  state.modal.onSubmit = async () => {
    crudModalError.textContent = "";
    crudModalSave.disabled = true;
    try {
      const payload = formToObject(crudModalForm);
      await onSubmit(payload);
      closeCrudModal();
    } catch (error) {
      crudModalError.textContent = error.message;
    } finally {
      crudModalSave.disabled = false;
    }
  };
  if (typeof crudModal.showModal === "function") {
    crudModal.showModal();
  } else {
    crudModal.setAttribute("open", "open");
  }
}

function showConfirmModal({ title, message, confirmText = "确认", onConfirm }) {
  if (!crudModal || !crudModalBody || !crudModalTitle || !crudModalSave) return;
  if (crudModal.open && typeof crudModal.close === "function") crudModal.close();
  crudModalTitle.textContent = title;
  crudModalSave.textContent = confirmText;
  crudModalError.textContent = "";
  crudModalBody.innerHTML = `<div class="notice-card danger field-span-2"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p></div>`;
  state.modal.onSubmit = async () => {
    crudModalError.textContent = "";
    crudModalSave.disabled = true;
    try {
      await onConfirm();
      closeCrudModal();
    } catch (error) {
      crudModalError.textContent = error.message;
    } finally {
      crudModalSave.disabled = false;
    }
  };
  if (typeof crudModal.showModal === "function") {
    crudModal.showModal();
  } else {
    crudModal.setAttribute("open", "open");
  }
}

async function apiUpload(url, formData) {
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    body: formData,
  });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("登录状态已失效，请重新登录。");
  }
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;
  if (!response.ok) {
    throw new Error(payload?.detail || `请求失败：${response.status}`);
  }
  return payload;
}

function clearDeviceImageDraft() {
  if (state.deviceImageDraft.previewUrl) {
    URL.revokeObjectURL(state.deviceImageDraft.previewUrl);
  }
  state.deviceImageDraft = { file: null, previewUrl: "", fileName: "" };
}

function setDeviceImageDraft(file) {
  clearDeviceImageDraft();
  if (!file) return;
  state.deviceImageDraft = {
    file,
    previewUrl: URL.createObjectURL(file),
    fileName: file.name,
  };
}

crudModalSave?.addEventListener("click", async () => {
  if (!state.modal.onSubmit) return;
  await state.modal.onSubmit();
});

crudModal?.addEventListener("close", () => {
  state.modal.onSubmit = null;
  if (crudModalError) crudModalError.textContent = "";
  if (crudModalBody) crudModalBody.innerHTML = "";
  crudModalForm?.reset();
});

function renderUsersPage() {
  const usersData = state.pageData.users;
  if (!usersData) {
    return renderLoadingPage("用户管理", "创建账号并管理访问权限。");
  }
  const activeCount = Number.isFinite(Number(usersData.statusCounts?.active))
    ? Number(usersData.statusCounts.active)
    : (usersData.items || []).filter((user) => user.status === "active").length;
  const disabledCount = Number.isFinite(Number(usersData.statusCounts?.disabled))
    ? Number(usersData.statusCounts.disabled)
    : (usersData.items || []).filter((user) => user.status === "disabled").length;
  const rows = (usersData.items || []).map((user) => `
    <tr>
      <td>${escapeHtml(user.username)}</td>
      <td>${escapeHtml(user.displayName || "-")}</td>
      <td><span class="${pillClass(user.status)}">${escapeHtml(localizeToken(user.status))}</span></td>
      <td>${escapeHtml(formatDateTime(user.createdAt))}</td>
      <td>
        <div class="inline-meta">
          <button class="secondary-button" type="button" data-user-edit data-id="${user.id}">编辑</button>
          <button class="ghost-button" type="button" data-user-toggle data-id="${user.id}" data-next-status="${user.status === "active" ? "disabled" : "active"}">
            ${user.status === "active" ? "停用" : "启用"}
          </button>
        </div>
      </td>
    </tr>
  `);
  return `
    <section class="metric-grid">
      <article class="metric-card"><strong>账号总数</strong><span class="muted">${usersData.total || (usersData.items || []).length} 个</span></article>
      <article class="metric-card"><strong>启用中</strong><span class="muted">${activeCount} 个</span></article>
      <article class="metric-card"><strong>已停用</strong><span class="muted">${disabledCount} 个</span></article>
    </section>
    <section class="page-content">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>用户列表</h2>
            <p class="muted">支持状态切换，并通过弹窗新增或编辑用户。</p>
          </div>
          <div class="panel-actions">
            <button class="primary-button" type="button" data-user-create>新增用户</button>
          </div>
        </div>
        ${renderTable("users", ["用户名", "显示名称", "状态", "创建时间", "操作"], rows)}
        ${renderPagination("users", usersData, "个用户")}
      </article>
    </section>
  `;
}

function renderDevicesPage() {
  const devicesData = state.pageData.devices;
  if (!devicesData) {
    return renderLoadingPage("设备管理", "管理设备并分配所属区域。");
  }
  const previewUrl = state.deviceImageDraft.previewUrl;
  const rows = (devicesData.items || []).map((device) => `
    <tr>
      <td>${escapeHtml(device.name)}</td>
      <td>${escapeHtml(device.model)}</td>
      <td>${escapeHtml(device.areaName || "-")}</td>
      <td><span class="${pillClass(device.status)}">${escapeHtml(localizeToken(device.status))}</span></td>
      <td>${device.imagePath ? `<img class="device-thumb" src="${escapeHtml(device.imagePath)}" alt="${escapeHtml(device.name)}" width="84" height="56" loading="lazy">` : "-"}</td>
      <td>
        <div class="inline-meta">
          <button class="secondary-button" type="button" data-device-edit data-id="${device.id}">编辑</button>
          <button class="danger-button" type="button" data-device-delete data-id="${device.id}">删除</button>
        </div>
      </td>
    </tr>
  `);
  return `
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>设备登记</h2>
            <p class="muted">登记平台设备并绑定所属区域。</p>
          </div>
        </div>
        <form id="device-form" class="stack-form">
          <div class="grid-form">
            <label><span>名称</span><input name="name" required /></label>
            <label><span>型号</span><input name="model" required /></label>
            <label><span>状态</span>
              <select name="status">
                <option value="normal">正常</option>
                <option value="repair">维修中</option>
                <option value="offline">离线</option>
              </select>
            </label>
            <label><span>区域</span>
              <select name="areaId">${renderSelectOptions(devicesData.areas || [], state.formAreaDefaults.device.value, "请选择区域")}</select>
            </label>
          </div>
          <p id="device-area-status" class="muted">${escapeHtml(areaSelectionMessage())}</p>
          <label><span>备注</span><textarea name="notes" placeholder="可选设备备注"></textarea></label>
          <div class="device-upload-grid">
            <label>
              <span>设备图片</span>
              <input id="device-image-input" type="file" accept="image/*" />
            </label>
            <div class="image-preview-card">
              <div class="image-preview-shell">
                ${previewUrl ? `<img src="${escapeHtml(previewUrl)}" alt="设备预览" width="360" height="180">` : `<span class="muted">选择图片后在这里预览</span>`}
              </div>
              <div class="inline-meta">
                <span class="muted">${escapeHtml(state.deviceImageDraft.fileName || "未选择图片")}</span>
                <button class="ghost-button" id="device-image-clear" type="button">清空图片</button>
              </div>
            </div>
          </div>
          <div class="button-row">
            <button class="primary-button" type="submit">新建设备</button>
          </div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="device"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>设备列表</h2>
            <p class="muted">支持按名称、型号、区域和状态筛选。</p>
          </div>
          <div class="panel-actions toolbar-filters">
            <input id="device-search" type="search" value="${escapeHtml(state.deviceFilters.keyword)}" placeholder="搜索名称 / 型号 / 区域 / 备注" autocomplete="off" />
            <select id="device-status-filter">
              <option value="">全部状态</option>
              <option value="normal"${state.deviceFilters.status === "normal" ? " selected" : ""}>正常</option>
              <option value="repair"${state.deviceFilters.status === "repair" ? " selected" : ""}>维修中</option>
              <option value="offline"${state.deviceFilters.status === "offline" ? " selected" : ""}>离线</option>
            </select>
            <button class="primary-button" id="device-filter-apply" type="button">筛选</button>
            <button class="secondary-button" id="device-filter-reset" type="button">重置筛选</button>
          </div>
        </div>
        ${renderTable("devices", ["名称", "型号", "区域", "状态", "图片", "操作"], rows)}
        ${renderPagination("devices", devicesData, "台设备")}
      </article>
    </section>
  `;
}

function renderAreasPage() {
  const areasData = state.pageData.areas;
  if (!areasData) {
    return renderLoadingPage("区域管理", "管理巡检区域。");
  }
  ensureExistingAreaSelection();
  const selectedIds = new Set((state.areaSelection || []).map((id) => Number(id)));
  const allSelected = areasData.items.length > 0 && areasData.items.every((area) => selectedIds.has(Number(area.id)));
  const rows = (areasData.items || []).map((area) => `
    <tr>
      <td class="table-select-cell">
        <input class="table-checkbox" type="checkbox" data-area-select value="${area.id}" aria-label="选择${escapeHtml(area.name)}区域"${selectedIds.has(Number(area.id)) ? " checked" : ""} />
      </td>
      <td>${escapeHtml(area.name)}</td>
      <td>${escapeHtml(area.manager || "-")}</td>
      <td>${escapeHtml(area.description || "-")}</td>
      <td>${escapeHtml(formatDateTime(area.createdAt))}</td>
      <td>
        <div class="inline-meta">
          <button class="secondary-button" type="button" data-area-edit data-id="${area.id}">编辑</button>
          <button class="danger-button" type="button" data-area-delete data-id="${area.id}">删除</button>
        </div>
      </td>
    </tr>
  `);
  return `
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>区域配置</h2>
            <p class="muted">创建设备、点位和路线共用的逻辑区域。</p>
          </div>
        </div>
        <form id="area-form" class="stack-form">
          <div class="grid-form">
            <label><span>名称</span><input name="name" required /></label>
            <label><span>负责人</span><input name="manager" /></label>
          </div>
          <label><span>描述</span><textarea name="description" placeholder="区域描述"></textarea></label>
          <div class="button-row">
            <button class="primary-button" type="submit">新建区域</button>
          </div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="area"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>区域列表</h2>
            <p class="muted">支持关键词搜索、批量删除和分页浏览。</p>
          </div>
          <div class="panel-actions toolbar-filters">
            <form id="area-search-form" class="inline-meta">
              <input id="area-search-keyword" type="search" value="${escapeHtml(state.paging.areas.keyword || "")}" placeholder="搜索名称 / 负责人 / 描述" autocomplete="off" />
              <button class="primary-button" type="submit">搜索</button>
              <button class="secondary-button" id="area-search-reset" type="button">重置</button>
            </form>
            <button class="danger-button" type="button" id="areas-batch-delete"${state.areaSelection.length ? "" : " disabled"}>批量删除（${state.areaSelection.length}）</button>
          </div>
        </div>
        ${renderTable("areas", [
          `<input class="table-checkbox" id="area-select-all" type="checkbox"${allSelected ? " checked" : ""} aria-label="全选当前页区域" />`,
          "名称",
          "负责人",
          "描述",
          "创建时间",
          "操作",
        ], rows)}
        ${state.areaDeleteError ? `<p class="form-error" role="alert" aria-live="polite">${escapeHtml(state.areaDeleteError)}</p>` : ""}
        ${renderPagination("areas", areasData, "个区域")}
      </article>
    </section>
  `;
}

function renderPointsPage() {
  const pointsData = state.pageData.points;
  if (!pointsData) {
    return renderLoadingPage("点位管理", "配置巡检点位。");
  }
  const pointPickerStatus = state.pointDraft.coords
    ? `已选择 ${state.pointDraft.zoneName} 内的巡检点：${state.pointDraft.coords[1].toFixed(6)}, ${state.pointDraft.coords[0].toFixed(6)}`
    : "请在地图中的巡检区域内点击选择巡检点。";
  const rows = (pointsData.items || []).map((point) => `
    <tr>
      <td>${escapeHtml(point.name)}</td>
      <td>${escapeHtml(point.areaName || "-")}</td>
      <td>${escapeHtml(point.deviceName || "-")}</td>
      <td>${escapeHtml(formatCoordinate(point.lat))}</td>
      <td>${escapeHtml(formatCoordinate(point.lng))}</td>
      <td>${escapeHtml(point.description || "-")}</td>
      <td>
        <div class="inline-meta">
          <button class="secondary-button" type="button" data-point-edit data-id="${point.id}">编辑</button>
          <button class="danger-button" type="button" data-point-delete data-id="${point.id}">删除</button>
        </div>
      </td>
    </tr>
  `);
  return `
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>巡检点位</h2>
            <p class="muted">先在巡检区域内点击地图选点，再提交点位信息。</p>
          </div>
        </div>
        <form id="point-form" class="stack-form">
          <div id="points-map" class="map-shell"><div class="map-fallback">检测到高德地图后将在此渲染。</div></div>
          <div class="inline-meta point-picker-meta">
            <span id="point-picker-status" class="muted">${escapeHtml(pointPickerStatus)}</span>
            <button class="ghost-button" id="point-picker-reset" type="button">清空选点</button>
          </div>
          <div class="grid-form">
            <label><span>名称</span><input name="name" required /></label>
            <label><span>区域</span>
              <select name="areaId">${renderSelectOptions(pointsData.areas || [], state.formAreaDefaults.point.value, "请选择区域")}</select>
            </label>
            <label><span>设备</span>
              <select name="deviceId">${renderSelectOptions(pointsData.devices || [], "", "未设置")}</select>
            </label>
            <label><span>纬度</span><input name="lat" type="number" step="0.000001" required readonly /></label>
            <label><span>经度</span><input name="lng" type="number" step="0.000001" required readonly /></label>
          </div>
          <p id="point-area-status" class="muted">${escapeHtml(areaSelectionMessage())}</p>
          <label><span>描述</span><textarea name="description" placeholder="点位描述"></textarea></label>
          <div class="button-row">
            <button class="primary-button" type="submit">新建点位</button>
          </div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="point"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>点位列表</h2>
            <p class="muted">这些点位可供路线配置复用。</p>
          </div>
        </div>
        ${renderTable("points", ["名称", "区域", "设备", "纬度", "经度", "描述", "操作"], rows)}
        ${renderPagination("points", pointsData, "个点位")}
      </article>
    </section>
  `;
}

function renderRoutesPage() {
  const routesData = state.pageData.routes;
  if (!routesData) {
    return renderLoadingPage("路线管理", "由巡检点位组成巡检路线。");
  }
  const activeRoute = (routesData.items || []).find((route) => Number(route.id) === Number(state.routeEditor.routeId)) || null;
  const activePointIds = new Set((state.routeEditor.selected || []).map((value) => Number(value)));
  const activeRoutePoints = activeRoute ? (routesData.routePoints?.[activeRoute.id] || []) : [];
  const pointsById = new Map((routesData.points || []).map((point) => [Number(point.id), point]));
  const selectedPoints = (state.routeEditor.selected || []).map((id) => pointsById.get(Number(id))).filter(Boolean);
  const availablePoints = (routesData.points || []).filter((point) => !activePointIds.has(Number(point.id)));
  const rows = (routesData.items || []).map((route) => `
    <tr>
      <td>${escapeHtml(route.name)}</td>
      <td>${escapeHtml(route.areaName || "-")}</td>
      <td>${escapeHtml(route.description || "-")}</td>
      <td>${escapeHtml(String(route.pointCount || 0))}</td>
      <td>${escapeHtml(formatDateTime(route.createdAt))}</td>
      <td>
        <div class="inline-meta">
          <button class="secondary-button" type="button" data-route-edit data-id="${route.id}">编辑</button>
          <button class="ghost-button" type="button" data-route-manage data-id="${route.id}">
            ${activeRoute && activeRoute.id === route.id ? "收起点位" : "配置点位"}
          </button>
          <button class="danger-button" type="button" data-route-delete data-id="${route.id}">删除</button>
        </div>
      </td>
    </tr>
  `);
  const editorHtml = activeRoute ? `
    <article class="panel">
      <div class="panel-header">
        <div>
          <h2>路线点位</h2>
          <p class="muted">${escapeHtml(activeRoute.name)} 当前已绑定 ${activeRoutePoints.length} 个点位。</p>
        </div>
        <span class="pill">已选 ${state.routeEditor.selected.length}</span>
      </div>
      <div class="route-transfer">
        <div class="transfer-panel">
          <strong>待选点位</strong>
          <select id="route-available-points" class="transfer-select" multiple size="12">
            ${availablePoints.map((point) => `
              <option value="${point.id}">
                ${escapeHtml(`${point.name} ｜ ${point.areaName || "-"} ｜ ${formatCoordinate(point.lat)}, ${formatCoordinate(point.lng)}`)}
              </option>
            `).join("")}
          </select>
          <p class="muted">左侧展示还未加入该路线的巡检点。</p>
        </div>
        <div class="transfer-actions">
          <button class="secondary-button" id="route-points-add" type="button">加入 →</button>
          <button class="secondary-button" id="route-points-remove" type="button">← 移出</button>
          <button class="ghost-button" id="route-points-up" type="button">上移</button>
          <button class="ghost-button" id="route-points-down" type="button">下移</button>
        </div>
        <div class="transfer-panel">
          <strong>路线顺序</strong>
          <select id="route-selected-points" class="transfer-select" multiple size="12">
            ${selectedPoints.map((point, index) => `
              <option value="${point.id}">
                ${escapeHtml(`${index + 1}. ${point.name} ｜ ${point.areaName || "-"} ｜ ${formatCoordinate(point.lat)}, ${formatCoordinate(point.lng)}`)}
              </option>
            `).join("")}
          </select>
          <p class="muted">右侧顺序即保存后的巡检顺序。</p>
        </div>
      </div>
      <div class="button-row">
        <button class="primary-button" id="route-points-save" type="button">保存点位配置</button>
        <button class="secondary-button" id="route-points-close" type="button">关闭</button>
      </div>
      <p class="form-error" role="alert" aria-live="polite" data-form-error="route-points"></p>
    </article>
  ` : "";
  return `
    <section class="dual-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>巡检路线</h2>
            <p class="muted">创建巡检路线并绑定所属区域。</p>
          </div>
        </div>
        <form id="route-form" class="stack-form">
          <div class="grid-form">
            <label><span>名称</span><input name="name" required /></label>
            <label><span>区域</span>
              <select name="areaId">${renderSelectOptions(routesData.areas || [], state.formAreaDefaults.route.value, "请选择区域")}</select>
            </label>
          </div>
          <p id="route-area-status" class="muted">${escapeHtml(areaSelectionMessage())}</p>
          <label><span>描述</span><textarea name="description" placeholder="路线描述"></textarea></label>
          <div class="button-row">
            <button class="primary-button" type="submit">新建路线</button>
          </div>
          <p class="form-error" role="alert" aria-live="polite" data-form-error="route"></p>
        </form>
      </article>
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>路线列表</h2>
            <p class="muted">点击“配置点位”设置路线点位。</p>
          </div>
        </div>
        ${renderTable("routes", ["名称", "区域", "描述", "点位数", "创建时间", "操作"], rows)}
        ${renderPagination("routes", routesData, "条路线")}
      </article>
    </section>
    ${editorHtml}
  `;
}

function bindUsersPage() {
  if (!state.pageData.users) {
    void ensureManagementPageData("users");
    return;
  }
  bindPagination("users");
  document.querySelector("[data-user-create]")?.addEventListener("click", () => {
    showCrudModal({
      title: "新增用户",
      saveText: "创建用户",
      fields: [
        { name: "username", label: "用户名", required: true },
        { name: "displayName", label: "显示名称" },
        { name: "password", label: "密码", type: "password", required: true },
      ],
      onSubmit: async (payload) => {
        await apiFetch("/api/users", { method: "POST", body: JSON.stringify(payload) });
        await ensureManagementPageData("users", true);
      },
    });
  });
  document.querySelectorAll("[data-user-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const user = findPageItem("users", button.dataset.id);
      if (!user) return;
      showCrudModal({
        title: `编辑用户：${user.username}`,
        saveText: "保存修改",
        values: {
          displayName: user.displayName || user.username,
          password: "",
        },
        fields: [
          { name: "displayName", label: "显示名称", required: true },
          { name: "password", label: "新密码", type: "password", placeholder: "留空则保持不变" },
        ],
        onSubmit: async (payload) => {
          if (!payload.displayName && !payload.password) {
            throw new Error("请至少填写显示名称或新密码。");
          }
          await apiFetch(`/api/users/${user.id}`, { method: "PUT", body: JSON.stringify(payload) });
          await ensureManagementPageData("users", true);
        },
      });
    });
  });
  document.querySelectorAll("[data-user-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      await apiFetch(`/api/users/${button.dataset.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: button.dataset.nextStatus }),
      });
      await ensureManagementPageData("users", true);
    });
  });
}

function bindDevicesPage() {
  if (!state.pageData.devices) {
    void ensureManagementPageData("devices");
    return;
  }
  bindPagination("devices");
  bindAreaDefaultSelect("device-form", "device");
  syncManagedFormAreaUi();
  bindManagedForm("device-form", "device", async (form) => {
    ensureAreaSelectedForSubmit("device", form);
    const payload = numericPayload(formToObject(form), ["areaId"]);
    const created = await apiFetch("/api/devices", { method: "POST", body: JSON.stringify(payload) });
    if (state.deviceImageDraft.file && created.deviceId) {
      const formData = new FormData();
      formData.append("file", state.deviceImageDraft.file);
      await apiUpload(`/api/devices/${created.deviceId}/image`, formData);
    }
    form.reset();
    clearDeviceImageDraft();
    resetAreaDefault("device", form);
    state.paging.devices.page = 1;
    await ensureManagementPageData("devices", true);
  });
  document.getElementById("device-image-input")?.addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    setDeviceImageDraft(file || null);
    renderCurrentPage();
  });
  document.getElementById("device-image-clear")?.addEventListener("click", () => {
    clearDeviceImageDraft();
    renderCurrentPage();
  });
  document.getElementById("device-filter-apply")?.addEventListener("click", async () => {
    state.deviceFilters.keyword = document.getElementById("device-search")?.value?.trim() || "";
    state.deviceFilters.status = normalizeDeviceStatusFilter(document.getElementById("device-status-filter")?.value);
    state.paging.devices.page = 1;
    await ensureManagementPageData("devices", true);
  });
  document.getElementById("device-filter-reset")?.addEventListener("click", async () => {
    state.deviceFilters = { keyword: "", status: "" };
    state.paging.devices.page = 1;
    await ensureManagementPageData("devices", true);
  });
  document.querySelectorAll("[data-device-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const device = findPageItem("devices", button.dataset.id);
      if (!device) return;
      showCrudModal({
        title: `编辑设备：${device.name}`,
        saveText: "保存设备",
        values: {
          name: device.name,
          model: device.model,
          status: device.status || "normal",
          areaId: device.areaId == null ? "" : String(device.areaId),
          notes: device.notes || "",
        },
        fields: [
          { name: "name", label: "名称", required: true },
          { name: "model", label: "型号", required: true },
          {
            name: "status",
            label: "状态",
            type: "select",
            options: [
              { value: "normal", label: "正常" },
              { value: "repair", label: "维修中" },
              { value: "offline", label: "离线" },
            ],
          },
          {
            name: "areaId",
            label: "区域",
            type: "select",
            options: [{ value: "", label: "未设置" }].concat(
              (state.pageData.devices?.areas || []).map((area) => ({ value: String(area.id), label: area.name })),
            ),
          },
          { name: "notes", label: "备注", type: "textarea", className: "field-span-2" },
        ],
        onSubmit: async (payload) => {
          const nextPayload = numericPayload({
            code: device.code || "",
            manufacturer: device.manufacturer || "",
            serialNumber: device.serialNumber || "",
            categoryId: device.categoryId == null ? "" : String(device.categoryId),
            robotId: device.robotId == null ? "" : String(device.robotId),
            ...payload,
          }, ["areaId", "categoryId", "robotId"]);
          await apiFetch(`/api/devices/${device.id}`, { method: "PUT", body: JSON.stringify(nextPayload) });
          await ensureManagementPageData("devices", true);
        },
      });
    });
  });
  document.querySelectorAll("[data-device-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("确认删除该设备？")) return;
      try {
        await apiFetch(`/api/devices/${button.dataset.id}`, { method: "DELETE" });
        await ensureManagementPageData("devices", true);
      } catch (error) {
        window.alert(error.message);
      }
    });
  });
}

function bindAreasPage() {
  if (!state.pageData.areas) {
    void ensureManagementPageData("areas");
    return;
  }
  bindManagedForm("area-form", "area", async (form) => {
    await apiFetch("/api/areas", { method: "POST", body: JSON.stringify(formToObject(form)) });
    form.reset();
    state.paging.areas.page = 1;
    state.areaSelection = [];
    state.areaDeleteError = "";
    await ensureManagementPageData("areas", true);
  });
  bindPagination("areas");
  document.getElementById("area-search-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.paging.areas.keyword = document.getElementById("area-search-keyword")?.value?.trim() || "";
    state.paging.areas.page = 1;
    state.areaSelection = [];
    state.areaDeleteError = "";
    await ensureManagementPageData("areas", true);
  });
  document.getElementById("area-search-reset")?.addEventListener("click", async () => {
    state.paging.areas.keyword = "";
    state.paging.areas.page = 1;
    state.areaSelection = [];
    state.areaDeleteError = "";
    await ensureManagementPageData("areas", true);
  });
  document.getElementById("area-select-all")?.addEventListener("change", (event) => {
    const checked = Boolean(event.target.checked);
    const visibleIds = (state.pageData.areas?.items || []).map((item) => Number(item.id));
    if (checked) {
      state.areaSelection = Array.from(new Set([...state.areaSelection, ...visibleIds]));
    } else {
      const hidden = new Set(visibleIds);
      state.areaSelection = state.areaSelection.filter((id) => !hidden.has(Number(id)));
    }
    renderCurrentPage();
  });
  document.querySelectorAll("[data-area-select]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const areaId = Number(checkbox.value);
      if (checkbox.checked) {
        if (!state.areaSelection.includes(areaId)) {
          state.areaSelection = [...state.areaSelection, areaId];
        }
      } else {
        state.areaSelection = state.areaSelection.filter((id) => Number(id) !== areaId);
      }
      renderCurrentPage();
    });
  });
  document.getElementById("areas-batch-delete")?.addEventListener("click", async () => {
    if (!state.areaSelection.length) return;
    if (!window.confirm(`确认批量删除选中的 ${state.areaSelection.length} 个区域？`)) return;
    state.areaDeleteError = "";
    try {
      await apiFetch("/api/areas/batch-delete", {
        method: "POST",
        body: JSON.stringify({ ids: state.areaSelection }),
      });
      state.areaSelection = [];
      await ensureManagementPageData("areas", true);
    } catch (error) {
      state.areaDeleteError = error.message;
      renderCurrentPage();
    }
  });
  document.querySelectorAll("[data-area-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const area = findPageItem("areas", button.dataset.id);
      if (!area) return;
      showCrudModal({
        title: `编辑区域：${area.name}`,
        saveText: "保存区域",
        values: {
          name: area.name,
          manager: area.manager || "",
          description: area.description || "",
        },
        fields: [
          { name: "name", label: "名称", required: true },
          { name: "manager", label: "负责人" },
          { name: "description", label: "描述", type: "textarea", className: "field-span-2" },
        ],
        onSubmit: async (payload) => {
          await apiFetch(`/api/areas/${area.id}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
          state.areaDeleteError = "";
          await ensureManagementPageData("areas", true);
        },
      });
    });
  });
  document.querySelectorAll("[data-area-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("确认删除该区域？")) return;
      state.areaDeleteError = "";
      try {
        await apiFetch(`/api/areas/${button.dataset.id}`, { method: "DELETE" });
        state.areaSelection = state.areaSelection.filter((id) => Number(id) !== Number(button.dataset.id));
        await ensureManagementPageData("areas", true);
      } catch (error) {
        state.areaDeleteError = error.message;
        renderCurrentPage();
      }
    });
  });
}

function bindReportsPage() {
  if (!state.pageData.reports) {
    void ensureManagementPageData("reports");
    return;
  }
  const form = document.getElementById("report-form");
  if (form) {
    applyFriendlyFormDefaults("report", form);
  }
  bindManagedForm("report-form", "report", async (form) => {
    await apiFetch("/api/reports", { method: "POST", body: JSON.stringify(formToObject(form)) });
    form.reset();
    applyFriendlyFormDefaults("report", form);
    state.paging.reports.page = 1;
    await Promise.all([loadDashboard(), ensureManagementPageData("reports", true)]);
  });
  bindPagination("reports");
  document.querySelectorAll("[data-report-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("确认删除该报告？")) return;
      await apiFetch(`/api/reports/${button.dataset.id}`, { method: "DELETE" });
      await Promise.all([loadDashboard(), ensureManagementPageData("reports", true)]);
    });
  });
}

function bindZonesPage() {
  if (!state.pageData.zones) {
    void ensureManagementPageData("zones");
    return;
  }
  bindPagination("zones");
  const form = document.getElementById("zone-form");
  if (form) {
    applyFriendlyFormDefaults("zone", form);
  }
  bindAreaDefaultSelect("zone-form", "zone");
  syncManagedFormAreaUi();
  bindManagedForm("zone-form", "zone", async (form) => {
    commitPendingZonePoint();
    if (state.zoneDraft.path.length < 3) {
      throw new Error("请先在地图上绘制至少 3 个点的区域。");
    }
    state.zoneDraft.complete = true;
    syncZoneDraftUi();
    refreshZoneDraftPreview();
    const payload = {
      ...formToObject(form),
      path: state.zoneDraft.path,
      strokeColor: state.zoneDraft.strokeColor,
      fillColor: state.zoneDraft.fillColor,
    };
    await apiFetch("/api/zones", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    applyFriendlyFormDefaults("zone", form);
    resetAreaDefault("zone", form);
    resetZoneDraft();
    state.paging.zones.page = 1;
    await Promise.all([loadDashboard(), ensureManagementPageData("zones", true)]);
  });
  document.querySelectorAll("[data-zone-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const zone = findPageItem("zones", button.dataset.id);
      if (!zone) return;
      showCrudModal({
        title: `编辑区域：${zone.name}`,
        saveText: "保存区域",
        values: {
          name: zone.name,
          areaId: zone.areaId == null ? "" : String(zone.areaId),
          type: zone.type,
          risk: zone.risk,
          status: zone.status,
          frequency: zone.frequency || "",
          notes: zone.notes || "",
        },
        fields: [
          { name: "name", label: "区域名称", required: true },
          {
            name: "areaId",
            label: "所属区域",
            type: "select",
            options: [{ value: "", label: "请选择区域" }].concat(
              (state.pageData.zones?.areas || []).map((area) => ({ value: String(area.id), label: area.name })),
            ),
          },
          {
            name: "type",
            label: "区域类型",
            type: "select",
            options: [
              { value: "inspection", label: "巡检区" },
              { value: "charging", label: "充电区" },
              { value: "storage", label: "仓储区" },
              { value: "restricted", label: "管控区" },
            ],
          },
          {
            name: "risk",
            label: "风险等级",
            type: "select",
            options: [
              { value: "low", label: "低" },
              { value: "medium", label: "中" },
              { value: "high", label: "高" },
            ],
          },
          {
            name: "status",
            label: "状态",
            type: "select",
            options: [
              { value: "active", label: "启用" },
              { value: "paused", label: "暂停" },
            ],
          },
          { name: "frequency", label: "巡检频率" },
          { name: "notes", label: "备注", type: "textarea", className: "field-span-2" },
        ],
        onSubmit: async (payload) => {
          await apiFetch(`/api/zones/${zone.id}`, { method: "PUT", body: JSON.stringify(payload) });
          await Promise.all([loadDashboard(), ensureManagementPageData("zones", true)]);
        },
      });
    });
  });
  document.querySelectorAll("[data-zone-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("确认删除该区域？")) return;
      await apiFetch(`/api/zones/${button.dataset.id}`, { method: "DELETE" });
      await Promise.all([loadDashboard(), ensureManagementPageData("zones", true)]);
    });
  });
}

function bindPointsPage() {
  if (!state.pageData.points) {
    void ensureManagementPageData("points");
    return;
  }
  bindPagination("points");
  bindAreaDefaultSelect("point-form", "point");
  syncManagedFormAreaUi();
  bindManagedForm("point-form", "point", async (form) => {
    if (!state.pointDraft.coords) {
      throw new Error("请先在巡检区域内点击地图选择巡检点。");
    }
    ensureAreaSelectedForSubmit("point", form);
    const payload = numericPayload(formToObject(form), ["areaId", "deviceId"]);
    payload.lat = state.pointDraft.coords[1];
    payload.lng = state.pointDraft.coords[0];
    await apiFetch("/api/points", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    resetAreaDefault("point", form);
    resetPointDraft();
    state.paging.points.page = 1;
    await ensureManagementPageData("points", true);
  });
  document.getElementById("point-picker-reset")?.addEventListener("click", () => {
    resetPointDraft();
    setFormError("point");
  });
  syncPointDraftUi();
  document.querySelectorAll("[data-point-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const point = findPageItem("points", button.dataset.id);
      if (!point) return;
      showCrudModal({
        title: `编辑点位：${point.name}`,
        saveText: "保存点位",
        values: {
          name: point.name,
          areaId: point.areaId == null ? "" : String(point.areaId),
          deviceId: point.deviceId == null ? "" : String(point.deviceId),
          lat: String(point.lat ?? ""),
          lng: String(point.lng ?? ""),
          description: point.description || "",
        },
        fields: [
          { name: "name", label: "名称", required: true },
          {
            name: "areaId",
            label: "区域",
            type: "select",
            options: [{ value: "", label: "未设置" }].concat(
              (state.pageData.points?.areas || []).map((area) => ({ value: String(area.id), label: area.name })),
            ),
          },
          {
            name: "deviceId",
            label: "设备",
            type: "select",
            options: [{ value: "", label: "未设置" }].concat(
              (state.pageData.points?.devices || []).map((device) => ({ value: String(device.id), label: device.name })),
            ),
          },
          { name: "lat", label: "纬度", type: "number", step: "0.000001", required: true },
          { name: "lng", label: "经度", type: "number", step: "0.000001", required: true },
          { name: "description", label: "描述", type: "textarea", className: "field-span-2" },
        ],
        onSubmit: async (payload) => {
          const nextPayload = numericPayload(payload, ["areaId", "deviceId", "lat", "lng"]);
          await apiFetch(`/api/points/${point.id}`, { method: "PUT", body: JSON.stringify(nextPayload) });
          await ensureManagementPageData("points", true);
        },
      });
    });
  });
  document.querySelectorAll("[data-point-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("确认删除该点位？")) return;
      await apiFetch(`/api/points/${button.dataset.id}`, { method: "DELETE" });
      await ensureManagementPageData("points", true);
    });
  });
}

function bindRoutesPage() {
  if (!state.pageData.routes) {
    void ensureManagementPageData("routes");
    return;
  }
  bindPagination("routes");
  bindAreaDefaultSelect("route-form", "route");
  syncManagedFormAreaUi();
  bindManagedForm("route-form", "route", async (form) => {
    ensureAreaSelectedForSubmit("route", form);
    const payload = numericPayload(formToObject(form), ["areaId"]);
    await apiFetch("/api/routes", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    resetAreaDefault("route", form);
    state.paging.routes.page = 1;
    await ensureManagementPageData("routes", true);
  });
  document.querySelectorAll("[data-route-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const route = findPageItem("routes", button.dataset.id);
      if (!route) return;
      showCrudModal({
        title: `编辑路线：${route.name}`,
        saveText: "保存路线",
        values: {
          name: route.name,
          areaId: route.areaId == null ? "" : String(route.areaId),
          description: route.description || "",
        },
        fields: [
          { name: "name", label: "名称", required: true },
          {
            name: "areaId",
            label: "区域",
            type: "select",
            options: [{ value: "", label: "未设置" }].concat(
              (state.pageData.routes?.areas || []).map((area) => ({ value: String(area.id), label: area.name })),
            ),
          },
          { name: "description", label: "描述", type: "textarea", className: "field-span-2" },
        ],
        onSubmit: async (payload) => {
          const nextPayload = numericPayload(payload, ["areaId"]);
          await apiFetch(`/api/routes/${route.id}`, { method: "PUT", body: JSON.stringify(nextPayload) });
          await ensureManagementPageData("routes", true);
        },
      });
    });
  });
  document.querySelectorAll("[data-route-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("确认删除该路线？")) return;
      await apiFetch(`/api/routes/${button.dataset.id}`, { method: "DELETE" });
      if (Number(state.routeEditor.routeId) === Number(button.dataset.id)) {
        state.routeEditor = { routeId: null, selected: [] };
      }
      await ensureManagementPageData("routes", true);
    });
  });
  document.querySelectorAll("[data-route-manage]").forEach((button) => {
    button.addEventListener("click", async () => {
      const routeId = Number(button.dataset.id);
      if (Number(state.routeEditor.routeId) === routeId) {
        state.routeEditor = { routeId: null, selected: [] };
        renderCurrentPage();
        return;
      }
      state.routeEditor.routeId = routeId;
      state.routeEditor.selected = [];
      await ensureRoutePoints(routeId, true);
    });
  });
  document.getElementById("route-points-add")?.addEventListener("click", () => {
    const availableSelect = document.getElementById("route-available-points");
    const ids = Array.from(availableSelect?.selectedOptions || []).map((option) => Number(option.value));
    if (!ids.length) return;
    state.routeEditor.selected = [...state.routeEditor.selected, ...ids.filter((id) => !state.routeEditor.selected.includes(id))];
    renderCurrentPage();
  });
  document.getElementById("route-points-remove")?.addEventListener("click", () => {
    const selectedSelect = document.getElementById("route-selected-points");
    const ids = new Set(Array.from(selectedSelect?.selectedOptions || []).map((option) => Number(option.value)));
    if (!ids.size) return;
    state.routeEditor.selected = state.routeEditor.selected.filter((id) => !ids.has(Number(id)));
    renderCurrentPage();
  });
  document.getElementById("route-points-up")?.addEventListener("click", () => {
    const selectedSelect = document.getElementById("route-selected-points");
    const ids = new Set(Array.from(selectedSelect?.selectedOptions || []).map((option) => Number(option.value)));
    if (!ids.size) return;
    for (let index = 1; index < state.routeEditor.selected.length; index += 1) {
      const currentId = Number(state.routeEditor.selected[index]);
      const previousId = Number(state.routeEditor.selected[index - 1]);
      if (ids.has(currentId) && !ids.has(previousId)) {
        [state.routeEditor.selected[index - 1], state.routeEditor.selected[index]] = [state.routeEditor.selected[index], state.routeEditor.selected[index - 1]];
      }
    }
    renderCurrentPage();
  });
  document.getElementById("route-points-down")?.addEventListener("click", () => {
    const selectedSelect = document.getElementById("route-selected-points");
    const ids = new Set(Array.from(selectedSelect?.selectedOptions || []).map((option) => Number(option.value)));
    if (!ids.size) return;
    for (let index = state.routeEditor.selected.length - 2; index >= 0; index -= 1) {
      const currentId = Number(state.routeEditor.selected[index]);
      const nextId = Number(state.routeEditor.selected[index + 1]);
      if (ids.has(currentId) && !ids.has(nextId)) {
        [state.routeEditor.selected[index + 1], state.routeEditor.selected[index]] = [state.routeEditor.selected[index], state.routeEditor.selected[index + 1]];
      }
    }
    renderCurrentPage();
  });
  document.getElementById("route-points-save")?.addEventListener("click", async () => {
    if (!state.routeEditor.routeId) return;
    setFormError("route-points");
    try {
      await apiFetch(`/api/routes/${state.routeEditor.routeId}/points`, {
        method: "PUT",
        body: JSON.stringify({ pointIds: state.routeEditor.selected }),
      });
      await ensureManagementPageData("routes", true);
      await ensureRoutePoints(state.routeEditor.routeId, true);
    } catch (error) {
      setFormError("route-points", error.message);
    }
  });
  document.getElementById("route-points-close")?.addEventListener("click", () => {
    state.routeEditor = { routeId: null, selected: [] };
    renderCurrentPage();
  });
}

function renderTabButtons(active, tabs, attrName) {
  return `<div class="inline-meta tab-strip" role="tablist" aria-label="子模块切换">${tabs.map((tab) => `
    <button class="${tab.value === active ? "primary-button" : "secondary-button"}" role="tab" aria-selected="${tab.value === active ? "true" : "false"}" type="button" ${attrName}="${escapeHtml(tab.value)}">${escapeHtml(tab.label)}</button>
  `).join("")}</div>`;
}

function renderStatusSelect(name = "status", selected = "active") {
  const options = ["active", "normal", "repair", "standby", "connected", "disconnected", "paused", "offline", "fault", "draft"];
  return `<select name="${escapeHtml(name)}">${options.map((value) => `<option value="${value}"${value === selected ? " selected" : ""}>${escapeHtml(localizeToken(value))}</option>`).join("")}</select>`;
}

function filterParams(filterKey) {
  return state.managementFilters[filterKey] || {};
}

function renderListSearch(filterKey, placeholder) {
  const keyword = filterParams(filterKey).keyword || "";
  const inputId = `management-search-${filterKey}`;
  return `
    <div class="panel-actions toolbar-filters">
      <label class="visually-hidden" for="${inputId}">${escapeHtml(placeholder)}</label>
      <input id="${inputId}" aria-label="${escapeHtml(placeholder)}" data-management-search="${filterKey}" type="search" value="${escapeHtml(keyword)}" placeholder="${escapeHtml(placeholder)}" autocomplete="off" />
      <button class="primary-button" data-management-search-apply="${filterKey}" type="button">搜索</button>
      <button class="secondary-button" data-management-search-reset="${filterKey}" type="button">重置</button>
    </div>
  `;
}

function renderSubPagination(pageId, payload, ownerPage, label = "条") {
  return renderPagination(pageId, payload, label)
    .replaceAll(`data-page-nav="${pageId}"`, `data-sub-page-nav="${ownerPage}:${pageId}"`)
    .replaceAll(`data-page-size="${pageId}"`, `data-sub-page-size="${ownerPage}:${pageId}"`);
}

function bindSubPagination(pageId, ownerPage) {
  document.querySelectorAll(`[data-sub-page-nav="${ownerPage}:${pageId}"]`).forEach((button) => {
    button.addEventListener("click", async () => {
      const targetPage = safePageValue(button.dataset.pageTarget, state.paging[pageId]?.page || 1);
      if (!state.paging[pageId] || targetPage === state.paging[pageId].page) return;
      state.paging[pageId].page = targetPage;
      await ensureManagementPageData(ownerPage, true);
    });
  });
  document.querySelectorAll(`[data-sub-page-size="${ownerPage}:${pageId}"]`).forEach((select) => {
    select.addEventListener("change", async () => {
      const nextSize = safePageSize(select.value, state.paging[pageId]?.size || 10);
      if (!state.paging[pageId] || nextSize === state.paging[pageId].size) return;
      state.paging[pageId].size = nextSize;
      state.paging[pageId].page = 1;
      await ensureManagementPageData(ownerPage, true);
    });
  });
}

function renderDeviceManagementPage() {
  const data = state.pageData.device_management;
  if (!data) return renderLoadingPage("设备管理", "加载设备体系数据。");
  const tabs = [
    { value: "categories", label: "设备类别管理" },
    { value: "devices", label: "设备信息管理" },
    { value: "units", label: "机载单元管理" },
    { value: "network", label: "网络通信管理" },
  ];
  return `
    <section class="panel"><div class="panel-header"><div><h2>设备管理</h2><p class="muted">按类别、设备、机载单元和通信通道维护设备体系。</p></div></div>${renderTabButtons(state.deviceManagementTab, tabs, "data-device-management-tab")}</section>
    ${state.deviceManagementTab === "categories" ? renderDeviceCategoriesPanel(data) : ""}
    ${state.deviceManagementTab === "devices" ? renderManagedDevicesPanel(data) : ""}
    ${state.deviceManagementTab === "units" ? renderOnboardUnitsPanel(data) : ""}
    ${state.deviceManagementTab === "network" ? renderNetworkChannelsPanel(data) : ""}
  `;
}

function renderDeviceCategoriesPanel(data) {
  const rows = (data.categories.items || []).map((item) => `
    <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(localizeToken(item.status))}</td><td>${escapeHtml(item.description || "-")}</td><td>${escapeHtml(formatDateTime(item.createdAt))}</td>
    <td><div class="inline-meta"><button class="secondary-button" data-device-category-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="device-categories" data-owner-page="device_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>类别列表</h2><p class="muted">列表优先展示，新增和编辑统一在弹窗中完成。</p></div>
        <div class="management-header-actions">${renderListSearch("deviceCategories", "搜索类别名称 / 描述")}<button class="primary-button" data-device-category-create type="button">新增类别</button></div>
      </div>
      ${renderTable("device-categories", ["名称", "状态", "描述", "创建时间", "操作"], rows)}
      ${renderSubPagination("deviceCategories", data.categories, "device_management", "个类别")}
    </section>
  `;
}

function renderManagedDevicesPanel(data) {
  const rows = (data.devices.items || []).map((item) => `
    <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.code || "-")}</td><td>${escapeHtml(item.categoryName || "-")}</td><td>${escapeHtml(item.robotName || "-")}</td><td>${escapeHtml(localizeToken(item.status))}</td>
    <td><div class="inline-meta"><button class="secondary-button" data-managed-device-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="devices" data-owner-page="device_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>设备列表</h2><p class="muted">设备详情较多，新增和编辑放在弹窗里，列表只保留关键字段。</p></div>
        <div class="management-header-actions">${renderListSearch("managedDevices", "搜索名称 / 型号 / 区域 / 备注")}<button class="primary-button" data-managed-device-create type="button">新增设备</button></div>
      </div>
      ${renderTable("managed-devices", ["名称", "编码", "类别", "机器人", "状态", "操作"], rows)}
      ${renderSubPagination("devices", data.devices, "device_management", "台设备")}
    </section>
  `;
}

function renderOnboardUnitsPanel(data) {
  const rows = (data.units.items || []).map((item) => `
    <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.deviceName)}</td><td>${escapeHtml(item.unitType)}</td><td>${escapeHtml(item.protocol || "-")}</td><td>${escapeHtml(localizeToken(item.status))}</td><td><div class="inline-meta"><button class="secondary-button" data-onboard-unit-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="onboard-units" data-owner-page="device_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>单元列表</h2><p class="muted">机载传感、计算或执行单元按设备关联维护。</p></div>
        <div class="management-header-actions">${renderListSearch("onboardUnits", "搜索单元 / 类型 / 设备 / 协议")}<button class="primary-button" data-onboard-unit-create type="button">新增单元</button></div>
      </div>
      ${renderTable("onboard-units", ["名称", "设备", "类型", "协议", "状态", "操作"], rows)}
      ${renderSubPagination("onboardUnits", data.units, "device_management", "个单元")}
    </section>
  `;
}

function renderNetworkChannelsPanel(data) {
  const rows = (data.channels.items || []).map((item) => `
    <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.deviceName)}</td><td>${escapeHtml(item.channelType)}</td><td>${escapeHtml(item.host || "-")}:${escapeHtml(item.port || "-")}</td><td>${escapeHtml(localizeToken(item.status))}</td><td><div class="inline-meta"><button class="secondary-button" data-network-channel-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="network-channels" data-owner-page="device_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>通信列表</h2><p class="muted">网络、串口或控制网关通道集中展示。</p></div>
        <div class="management-header-actions">${renderListSearch("networkChannels", "搜索通道 / 类型 / 设备 / 地址")}<button class="primary-button" data-network-channel-create type="button">新增通道</button></div>
      </div>
      ${renderTable("network-channels", ["名称", "设备", "类型", "地址", "状态", "操作"], rows)}
      ${renderSubPagination("networkChannels", data.channels, "device_management", "个通道")}
    </section>
  `;
}

function renderClusterManagementPage() {
  const data = state.pageData.cluster_management;
  if (!data) return renderLoadingPage("集群管理", "加载集群与编队数据。");
  const tabs = [
    { value: "clusters", label: "集群信息管理" },
    { value: "nodes", label: "节点信息管理" },
    { value: "formations", label: "编队信息管理" },
  ];
  return `
    <section class="panel"><div class="panel-header"><div><h2>集群管理</h2><p class="muted">维护集群、节点和编队方案。</p></div></div>${renderTabButtons(state.clusterManagementTab, tabs, "data-cluster-management-tab")}</section>
    ${state.clusterManagementTab === "clusters" ? renderClustersPanel(data) : ""}
    ${state.clusterManagementTab === "nodes" ? renderClusterNodesPanel(data) : ""}
    ${state.clusterManagementTab === "formations" ? renderFormationsPanel(data) : ""}
  `;
}

function renderClustersPanel(data) {
  const rows = (data.clusters.items || []).map((item) => `
    <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(localizeToken(item.status))}</td><td>${escapeHtml(String(item.nodeCount || 0))}</td><td>${escapeHtml(String(item.formationCount || 0))}</td><td>${escapeHtml(item.description || "-")}</td><td><div class="inline-meta"><button class="secondary-button" data-cluster-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="clusters" data-owner-page="cluster_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>集群列表</h2><p class="muted">集群信息集中浏览，新增和编辑在弹窗内完成。</p></div>
        <div class="management-header-actions">${renderListSearch("clusters", "搜索集群名称 / 描述")}<button class="primary-button" data-cluster-create type="button">新增集群</button></div>
      </div>
      ${renderTable("clusters", ["名称", "状态", "节点数", "编队数", "描述", "操作"], rows)}
      ${renderSubPagination("clusters", data.clusters, "cluster_management", "个集群")}
    </section>
  `;
}

function renderClusterNodesPanel(data) {
  const rows = (data.nodes.items || []).map((item) => `
    <tr><td>${escapeHtml(item.clusterName)}</td><td>${escapeHtml(item.robotName)}</td><td>${escapeHtml(item.ipAddress || "-")}</td><td>${escapeHtml(item.role)}</td><td>${escapeHtml(localizeToken(item.status))}</td><td><div class="inline-meta"><button class="secondary-button" data-cluster-node-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="cluster-nodes" data-owner-page="cluster_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>节点列表</h2><p class="muted">节点只关联现有机器人，接入和退出在集群控制中执行。</p></div>
        <div class="management-header-actions">${renderListSearch("clusterNodes", "搜索集群 / 机器人 / IP / 状态")}<button class="primary-button" data-cluster-node-create type="button">新增节点</button></div>
      </div>
      ${renderTable("cluster-nodes", ["集群", "机器人", "IP", "角色", "状态", "操作"], rows)}
      ${renderSubPagination("clusterNodes", data.nodes, "cluster_management", "个节点")}
    </section>
  `;
}

function renderFormationsPanel(data) {
  const rows = (data.formations.items || []).map((item) => `
    <tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.clusterName)}</td><td>${escapeHtml(localizeToken(item.formationType))}</td><td>${escapeHtml(localizeToken(item.status))}</td><td>${escapeHtml(String(item.memberCount || 0))}</td><td><div class="inline-meta"><button class="secondary-button" data-formation-edit data-id="${item.id}" type="button">编辑</button><button class="danger-button" data-resource-delete="formations" data-owner-page="cluster_management" data-id="${item.id}" type="button">删除</button></div></td></tr>
  `);
  return `
    <section class="panel management-list-panel">
      <div class="panel-header">
        <div><h2>编队列表</h2><p class="muted">编队方案和成员配置通过弹窗维护，列表保持轻量。</p></div>
        <div class="management-header-actions">${renderListSearch("formations", "搜索编队 / 集群 / 类型 / 描述")}<button class="primary-button" data-formation-create type="button">新增编队</button><button class="secondary-button" data-formation-member-create type="button">添加成员</button></div>
      </div>
      ${renderTable("formations", ["名称", "集群", "类型", "状态", "成员数", "操作"], rows)}
      ${renderSubPagination("formations", data.formations, "cluster_management", "个编队")}
    </section>
  `;
}

function renderDeviceControlPage() {
  const data = state.pageData.device_control;
  if (!data) return renderLoadingPage("设备控制", "加载设备控制台。");
  const deviceOptions = renderSelectOptions(data.devices || [], "", "请选择设备");
  const unitOptions = renderSelectOptions(data.units || [], "", "请选择机载单元");
  const channelOptions = renderSelectOptions(data.channels || [], "", "请选择通信通道");
  const hasDevices = (data.devices || []).length > 0;
  const hasUnits = (data.units || []).length > 0;
  const hasChannels = (data.channels || []).length > 0;
  return `
    <section class="panel"><div class="panel-header"><div><h2>设备控制</h2><p class="muted">连接测试和基础运动直接走真实车端；传感与网络控制走真实控制网关。</p></div></div></section>
    <section class="notice-card danger control-risk-card" role="status" aria-live="polite">
      <strong>真实设备控制目标</strong>
      <p>连接测试、运动、停止、传感和通信控制都会调用真实服务；未选择目标时按钮保持禁用。</p>
      <div class="control-target-grid">
        <span>基础运动目标 <strong id="device-control-target-summary">未选择设备</strong></span>
        <span>最近指令 <strong>${escapeHtml(state.commandStatus || "暂无")}</strong></span>
        <span>可选设备 ${hasDevices ? data.devices.length : 0} 台</span>
      </div>
    </section>
    <section class="dual-grid">
      <article class="panel"><h2>连接与基础运动</h2><form id="device-motion-form" class="stack-form"><label><span>目标设备</span><select name="targetId" required${hasDevices ? "" : " disabled"}>${deviceOptions}</select></label><div class="grid-form"><label><span>线速度</span><input name="linear" type="number" step="0.01" value="0.05"></label><label><span>角速度</span><input name="angular" type="number" step="0.01" value="0"></label></div><div class="button-row"><button class="secondary-button" data-device-command="connectivity_test" type="button" disabled>连接测试</button><button class="primary-button" data-device-command="cmd_vel" type="button" disabled>发送运动</button><button class="danger-button critical-action" data-device-command="stop" type="button" disabled>停止</button></div><p class="form-error" role="alert" aria-live="polite" data-form-error="device-control"></p></form></article>
      <article class="panel"><h2>传感与通信控制</h2><form id="device-gateway-form" class="stack-form"><div class="grid-form"><label><span>机载单元</span><select name="sensorId"${hasUnits ? "" : " disabled"}>${unitOptions}</select></label><label><span>通信通道</span><select name="networkId"${hasChannels ? "" : " disabled"}>${channelOptions}</select></label></div><label><span>控制参数 JSON</span><textarea name="params" placeholder='{"enabled":true}'></textarea></label><div class="button-row"><button class="secondary-button" data-gateway-command="sensor_control" type="button"${hasUnits ? "" : " disabled"}>传感控制</button><button class="secondary-button" data-gateway-command="network_control" type="button"${hasChannels ? "" : " disabled"}>网络控制</button></div><p class="form-error" role="alert" aria-live="polite" data-form-error="device-gateway"></p></form></article>
    </section>
    ${renderCommandHistory(data.commands)}
  `;
}

function renderClusterControlPage() {
  const data = state.pageData.cluster_control;
  if (!data) return renderLoadingPage("集群控制", "加载集群控制台。");
  const hasNodes = (data.nodes || []).length > 0;
  const hasFormations = (data.formations || []).length > 0;
  return `
    <section class="notice-card danger control-risk-card" role="status" aria-live="polite">
      <strong>真实集群控制目标</strong>
      <p>节点接入、退出和编队控制都会进入真实命令网关；未选择节点或编队时不会下发。</p>
      <div class="control-target-grid">
        <span>节点目标 <strong id="cluster-node-target-summary">未选择节点</strong></span>
        <span>编队目标 <strong id="formation-target-summary">未选择编队</strong></span>
        <span>最近指令 <strong>${escapeHtml(state.commandStatus || "暂无")}</strong></span>
      </div>
    </section>
    <section class="dual-grid">
      <article class="panel"><h2>节点接入 / 退出</h2><form id="cluster-node-control-form" class="stack-form"><label><span>集群节点</span><select name="targetId" required${hasNodes ? "" : " disabled"}>${renderSelectOptions(data.nodes || [], "", "请选择节点", (node) => `${node.clusterName} / ${node.robotName}`)}</select></label><div class="button-row"><button class="primary-button" data-cluster-command="node_join" type="button" disabled>节点接入</button><button class="danger-button critical-action" data-cluster-command="node_exit" type="button" disabled>节点退出</button></div><p class="form-error" role="alert" aria-live="polite" data-form-error="cluster-node-control"></p></form></article>
      <article class="panel"><h2>编队控制</h2><form id="formation-control-form" class="stack-form"><label><span>编队方案</span><select name="targetId" required${hasFormations ? "" : " disabled"}>${renderSelectOptions(data.formations || [], "", "请选择编队", (formation) => `${formation.clusterName} / ${formation.name}`)}</select></label><label><span>控制参数 JSON</span><textarea name="params" placeholder='{"action":"start"}'></textarea></label><div class="button-row"><button class="primary-button" data-formation-command="formation_control" type="button" disabled>执行编队控制</button></div><p class="form-error" role="alert" aria-live="polite" data-form-error="formation-control"></p></form></article>
    </section>
    ${renderCommandHistory(data.commands)}
  `;
}

function renderCommandHistory(commands) {
  const rows = (commands?.items || []).map((item) => `
    <tr><td>${escapeHtml(String(item.id))}</td><td>${escapeHtml(item.scope)}</td><td>${escapeHtml(item.commandType)}</td><td>${escapeHtml(item.targetType)}#${escapeHtml(item.targetId)}</td><td>${escapeHtml(localizeToken(item.status))}</td><td>${escapeHtml(item.error || "-")}</td><td>${escapeHtml(formatDateTime(item.createdAt))}</td></tr>
  `);
  return `<section class="panel"><h2>最近控制命令</h2>${renderTable("control-commands", ["ID", "范围", "命令", "目标", "状态", "错误", "时间"], rows)}${commands ? renderSubPagination("controlCommands", commands, state.pageId, "条命令") : ""}</section>`;
}

function renderTable(type, headers, rows) {
  return rows.length ? `
    <div class="table-scroll">
      <table class="data-table" data-table="${type}" aria-label="${escapeHtml(type)}数据列表">
        <caption class="visually-hidden">${escapeHtml(type)}数据列表</caption>
        <thead><tr>${headers.map((header) => `<th scope="col">${header}</th>`).join("")}</tr></thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </div>
  ` : `<div class="empty-state">暂无记录。</div>`;
}

function renderCurrentPage() {
  if (state.pageId !== "video") {
    clearVideoSnapshotTimer();
  }
  if (state.pageId !== "control" && state.control.activeTimer) {
    void sendControlStop();
  }
  const renderers = {
    overview: renderOverviewPage,
    tasks: renderTasksPage,
    reports: renderReportsPage,
    status: renderStatusPage,
    video: renderVideoPage,
    perception: renderPerceptionPage,
    control: renderControlPage,
    device_management: renderDeviceManagementPage,
    device_control: renderDeviceControlPage,
    cluster_management: renderClusterManagementPage,
    cluster_control: renderClusterControlPage,
    maintenance: renderMaintenancePage,
    zones: renderZonesPage,
    users: renderUsersPage,
    devices: renderDevicesPage,
    areas: renderAreasPage,
    points: renderPointsPage,
    routes: renderRoutesPage,
  };
  const renderer = renderers[state.pageId];
  pageContent.innerHTML = renderer ? renderer() : `<section class="panel"><div class="empty-state">页面不存在。</div></section>`;
  bindForms();
  renderMaps();
}

function formToObject(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  for (const key of Object.keys(data)) {
    if (data[key] === "") {
      delete data[key];
    }
  }
  return data;
}

function setFormError(name, message = "") {
  const target = document.querySelector(`[data-form-error="${name}"]`);
  if (target) target.textContent = message;
}

async function handleCreate(formName, endpoint, transform = (payload) => payload) {
  const form = document.getElementById(`${formName}-form`);
  if (!form) return;
  applyFriendlyFormDefaults(formName, form);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(formName);
    try {
      const payload = transform(formToObject(form));
      if (formName === "robot" && !payload.ipAddress) {
        throw new Error("请先扫描当前 Wi-Fi 网络，并选择已确认的机器人 IP。");
      }
      if (formName === "robot") {
        payload.manualConfirm = payload.ipAddress === state.robotDiscovery.manualConfirmedIp;
      }
      await apiFetch(endpoint, { method: "POST", body: JSON.stringify(payload) });
      form.reset();
      applyFriendlyFormDefaults(formName, form);
      if (formName === "zone") {
        resetZoneDraft();
      }
      if (formName === "robot") {
        state.robotDiscovery.selectedIp = "";
        state.robotDiscovery.manualConfirmedIp = "";
      }
      await loadDashboard();
    } catch (error) {
      setFormError(formName, error.message);
    }
  });
}

function bindZoneTools() {
  if (!document.getElementById("zone-form")) return;
  document.querySelectorAll("[data-zone-color]").forEach((button) => {
    button.addEventListener("click", () => {
      updateZoneColor(button.dataset.zoneColor);
    });
  });
  document.getElementById("zone-reset-button")?.addEventListener("click", () => {
    resetZoneDraft();
  });
  document.getElementById("zone-complete-button")?.addEventListener("click", () => {
    commitPendingZonePoint();
    if (state.zoneDraft.path.length < 3) {
      setFormError("zone", "请至少绘制 3 个点。");
      syncZoneDraftUi();
      refreshZoneDraftPreview();
      return;
    }
    setFormError("zone");
    state.zoneDraft.complete = true;
    syncZoneDraftUi();
    refreshZoneDraftPreview();
  });
  syncZoneDraftUi();
}

function bindRobotDiscoveryTools() {
  const form = document.getElementById("robot-form");
  if (!form) return;
  const select = document.getElementById("robot-discovery-select");
  const submitButton = form.querySelector('button[type="submit"]');
  if (select) {
    state.robotDiscovery.selectedIp = select.value || state.robotDiscovery.selectedIp || "";
    select.addEventListener("change", () => {
      state.robotDiscovery.selectedIp = select.value || "";
      if (submitButton) {
        submitButton.disabled = !state.robotDiscovery.selectedIp || state.robotDiscovery.loading;
      }
    });
  }
  document.getElementById("robot-discovery-refresh")?.addEventListener("click", async () => {
    await fetchRobotDiscovery(true);
  });
  document.querySelectorAll("[data-robot-manual-confirm]").forEach((button) => {
    button.addEventListener("click", () => {
      state.robotDiscovery.manualConfirmedIp = button.dataset.robotManualConfirm || "";
      state.robotDiscovery.selectedIp = state.robotDiscovery.manualConfirmedIp;
      renderCurrentPage();
    });
  });
  if (!state.robotDiscovery.loading && !state.robotDiscovery.scannedAt && !state.robotDiscovery.items.length && !state.robotDiscovery.error) {
    void fetchRobotDiscovery(true);
  }
}

function bindDeleteButtons() {
  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await apiFetch(`/api/${button.dataset.delete}/${button.dataset.id}`, { method: "DELETE" });
        await loadDashboard();
      } catch (error) {
        window.alert(error.message);
      }
    });
  });
}

function clearVideoSnapshotTimer() {
  if (state.video.snapshotTimer) {
    window.clearInterval(state.video.snapshotTimer);
    state.video.snapshotTimer = null;
  }
}

function refreshVideoSnapshots() {
  if (state.pageId !== "video") {
    clearVideoSnapshotTimer();
    return;
  }
  state.video.snapshotTick = Date.now();
  document.querySelectorAll("[data-video-snapshot]").forEach((image) => {
    const base = image.dataset.videoSnapshotBase || "";
    if (base) {
      image.src = `${base}?t=${state.video.snapshotTick}`;
    }
  });
}

function bindVideoPage() {
  if (state.pageId !== "video") return;
  document.querySelectorAll("[data-video-select]").forEach((button) => {
    button.addEventListener("click", () => {
      state.video.mainRobotId = button.dataset.id || "";
      state.video.snapshotTick = Date.now();
      renderCurrentPage();
    });
  });
  if (!state.video.snapshotTimer) {
    state.video.snapshotTimer = window.setInterval(refreshVideoSnapshots, VIDEO_SNAPSHOT_REFRESH_MS);
  }
}

function bindPerceptionPage() {
  if (state.pageId !== "perception") return;
  document.getElementById("perception-robot")?.addEventListener("change", (event) => {
    state.perception.robotId = event.target.value || "";
    state.perception.latest = null;
    void loadPerceptionLatest(true);
  });
  document.getElementById("perception-refresh")?.addEventListener("click", () => {
    void loadPerceptionLatest(true);
  });
  if (!state.perception.latest && !state.perception.loading && !state.perception.error) {
    void loadPerceptionLatest(true);
  }
}

function clearControlTimer() {
  if (state.control.activeTimer) {
    window.clearInterval(state.control.activeTimer);
    state.control.activeTimer = null;
  }
  state.control.activeRobotId = "";
}

function setControlStatus(text) {
  state.control.status = text;
  const target = document.getElementById("control-status");
  if (target) target.textContent = text;
}

function selectedControlRobotId() {
  return String(document.getElementById("control-robot")?.value || state.control.robotId || "").trim();
}

function controlRequestBody(extra = {}, robotId = selectedControlRobotId()) {
  const normalized = String(robotId || "").trim();
  if (!normalized) throw new Error("请选择要控制的机器人。");
  return { robotId: normalized, ...extra };
}

function controlValue(axis, multiplier) {
  const config = appConfig.robotControl || {};
  const sliderId = axis === "linear" ? "control-linear-scale" : "control-angular-scale";
  const max = Number(axis === "linear" ? config.maxLinear : config.maxAngular) || 0;
  const scale = Number(document.getElementById(sliderId)?.value || 0) / 100;
  return Number((Number(multiplier || 0) * max * scale).toFixed(3));
}

async function sendControlCommand(linear, angular, robotId = selectedControlRobotId()) {
  setFormError("control");
  await apiFetch("/api/robot-control/cmd_vel", {
    method: "POST",
    body: JSON.stringify(controlRequestBody({ linear, angular }, robotId)),
  });
  setControlStatus(`已发送：线速度 ${linear}，角速度 ${angular}`);
}

async function sendControlStop(robotId = state.control.activeRobotId || selectedControlRobotId()) {
  clearControlTimer();
  setFormError("control");
  await apiFetch("/api/robot-control/stop", {
    method: "POST",
    body: JSON.stringify(controlRequestBody({}, robotId)),
  });
  setControlStatus("已发送停车指令。");
}

function startControlHold(button) {
  const robotId = selectedControlRobotId();
  const linear = () => controlValue("linear", button.dataset.controlLinear);
  const angular = () => controlValue("angular", button.dataset.controlAngular);
  clearControlTimer();
  state.control.activeRobotId = robotId;
  const tick = async () => {
    try {
      await sendControlCommand(linear(), angular(), robotId);
    } catch (error) {
      clearControlTimer();
      setFormError("control", error.message);
    }
  };
  void tick();
  state.control.activeTimer = window.setInterval(tick, 180);
}

function bindControlPage() {
  if (state.pageId !== "control") return;
  document.getElementById("control-robot")?.addEventListener("change", async (event) => {
    const previousRobotId = state.control.activeRobotId;
    if (previousRobotId) {
      await sendControlStop(previousRobotId).catch((error) => setFormError("control", error.message));
    }
    state.control.robotId = event.target.value;
    setControlStatus(state.control.robotId ? "已切换控制目标。" : "请选择要控制的机器人。");
    renderCurrentPage();
  });
  document.getElementById("control-ping")?.addEventListener("click", async () => {
    try {
      setFormError("control");
      const query = new URLSearchParams(controlRequestBody()).toString();
      await apiFetch(`/api/robot-control/status?${query}`);
      setControlStatus("控制服务连接正常。");
    } catch (error) {
      setFormError("control", error.message);
    }
  });
  document.querySelectorAll("[data-control-linear]").forEach((button) => {
    button.addEventListener("pointerdown", () => {
      if (!button.disabled) startControlHold(button);
    });
    button.addEventListener("pointerup", () => void sendControlStop());
    button.addEventListener("pointercancel", () => void sendControlStop());
    button.addEventListener("pointerleave", () => void sendControlStop());
  });
  document.querySelectorAll("[data-control-stop], #control-stop").forEach((button) => {
    button.addEventListener("click", () => {
      if (!button.disabled) void sendControlStop();
    });
  });
}

function bindResourceDeleteButtons() {
  document.querySelectorAll("[data-resource-delete]").forEach((button) => {
    button.addEventListener("click", () => {
      showConfirmModal({
        title: "确认删除",
        message: "该操作会真实删除当前记录，若存在关联数据，后端会直接返回错误。",
        confirmText: "删除",
        onConfirm: async () => {
        await apiFetch(`/api/${button.dataset.resourceDelete}/${button.dataset.id}`, { method: "DELETE" });
        await ensureManagementPageData(button.dataset.ownerPage || state.pageId, true);
        },
      });
    });
  });
}

function nestedPageItem(ownerPage, collectionKey, itemId) {
  const items = state.pageData[ownerPage]?.[collectionKey]?.items || [];
  return items.find((item) => Number(item.id) === Number(itemId)) || null;
}

function modalOptions(items, emptyLabel = "未设置", labelFormatter = null) {
  const options = emptyLabel === null ? [] : [{ value: "", label: emptyLabel }];
  items.forEach((item) => {
    options.push({
      value: String(item.id),
      label: labelFormatter ? labelFormatter(item) : String(item.name || item.model || item.id),
    });
  });
  return options;
}

function statusOptions(selected = "active") {
  return ["active", "normal", "repair", "standby", "connected", "disconnected", "paused", "offline", "fault", "draft"]
    .map((value) => ({ value, label: localizeToken(value), selected: value === selected }));
}

function formationTypeOptions() {
  return ["line", "wedge", "column"].map((value) => ({ value, label: localizeToken(value) }));
}

function openDeviceCategoryCreator() {
  showCrudModal({
    title: "新增设备类别",
    values: { status: "active" },
    saveText: "新增",
    fields: [
      { name: "name", label: "类别名称", required: true },
      { name: "status", label: "状态", type: "select", options: statusOptions("active") },
      { name: "description", label: "描述", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/device-categories", { method: "POST", body: JSON.stringify(payload) });
      state.paging.deviceCategories.page = 1;
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openManagedDeviceCreator(data) {
  showCrudModal({
    title: "新增设备信息",
    values: { status: "normal" },
    saveText: "新增",
    fields: [
      { name: "name", label: "设备名称", required: true },
      { name: "code", label: "设备编码" },
      { name: "model", label: "型号", required: true },
      { name: "manufacturer", label: "厂商" },
      { name: "serialNumber", label: "序列号" },
      { name: "status", label: "状态", type: "select", options: statusOptions("normal") },
      { name: "categoryId", label: "类别", type: "select", options: modalOptions(data.categoryOptions || [], "未分类") },
      { name: "robotId", label: "关联机器人", type: "select", options: modalOptions(data.robots || [], "未关联", robotOptionLabel) },
      { name: "areaId", label: "区域", type: "select", options: modalOptions(data.areas || [], "未设置") },
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/devices", { method: "POST", body: JSON.stringify(numericPayload(payload, ["areaId", "categoryId", "robotId"])) });
      state.paging.devices.page = 1;
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openOnboardUnitCreator(data) {
  showCrudModal({
    title: "新增机载单元",
    values: { status: "active" },
    saveText: "新增",
    fields: [
      { name: "deviceId", label: "关联设备", type: "select", required: true, options: modalOptions(data.deviceOptions || [], "请选择设备") },
      { name: "name", label: "单元名称", required: true },
      { name: "unitType", label: "单元类型", required: true },
      { name: "model", label: "型号" },
      { name: "protocol", label: "协议" },
      { name: "status", label: "状态", type: "select", options: statusOptions("active") },
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/onboard-units", { method: "POST", body: JSON.stringify(numericPayload(payload, ["deviceId"])) });
      state.paging.onboardUnits.page = 1;
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openNetworkChannelCreator(data) {
  showCrudModal({
    title: "新增通信通道",
    values: { status: "active" },
    saveText: "新增",
    fields: [
      { name: "deviceId", label: "关联设备", type: "select", required: true, options: modalOptions(data.deviceOptions || [], "请选择设备") },
      { name: "name", label: "通道名称", required: true },
      { name: "channelType", label: "通信类型", required: true },
      { name: "host", label: "地址" },
      { name: "port", label: "端口", type: "number", min: 1, max: 65535 },
      { name: "protocol", label: "协议" },
      { name: "status", label: "状态", type: "select", options: statusOptions("active") },
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/network-channels", { method: "POST", body: JSON.stringify(numericPayload(payload, ["deviceId", "port"])) });
      state.paging.networkChannels.page = 1;
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openClusterCreator() {
  showCrudModal({
    title: "新增集群",
    values: { status: "active" },
    saveText: "新增",
    fields: [
      { name: "name", label: "集群名称", required: true },
      { name: "status", label: "状态", type: "select", options: statusOptions("active") },
      { name: "description", label: "描述", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/clusters", { method: "POST", body: JSON.stringify(payload) });
      state.paging.clusters.page = 1;
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function openClusterNodeCreator(data) {
  showCrudModal({
    title: "新增集群节点",
    values: { role: "member", status: "standby" },
    saveText: "新增",
    fields: [
      { name: "clusterId", label: "所属集群", type: "select", required: true, options: modalOptions(data.clusterOptions || [], "请选择集群") },
      { name: "robotId", label: "机器人", type: "select", required: true, options: modalOptions(data.robots || [], "请选择机器人", robotOptionLabel) },
      { name: "role", label: "角色" },
      { name: "status", label: "状态", type: "select", options: statusOptions("standby") },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/cluster-nodes", { method: "POST", body: JSON.stringify(numericPayload(payload, ["clusterId", "robotId"])) });
      state.paging.clusterNodes.page = 1;
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function openFormationCreator(data) {
  showCrudModal({
    title: "新增编队方案",
    values: { formationType: "line", status: "draft" },
    saveText: "新增",
    fields: [
      { name: "clusterId", label: "所属集群", type: "select", required: true, options: modalOptions(data.clusterOptions || [], "请选择集群") },
      { name: "name", label: "编队名称", required: true },
      { name: "formationType", label: "类型", type: "select", options: formationTypeOptions() },
      { name: "status", label: "状态", type: "select", options: statusOptions("draft") },
      { name: "description", label: "描述", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/formations", { method: "POST", body: JSON.stringify(numericPayload(payload, ["clusterId"])) });
      state.paging.formations.page = 1;
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function openFormationMemberCreator(data) {
  showCrudModal({
    title: "添加编队成员",
    values: { slotIndex: 1, role: "member", offsetX: 0, offsetY: 0 },
    saveText: "添加",
    fields: [
      { name: "formationId", label: "编队", type: "select", required: true, options: modalOptions(data.formations.items || [], "请选择编队") },
      { name: "robotId", label: "机器人", type: "select", required: true, options: modalOptions(data.robots || [], "请选择机器人", robotOptionLabel) },
      { name: "slotIndex", label: "槽位", type: "number", min: 1 },
      { name: "role", label: "角色" },
      { name: "offsetX", label: "X 偏移", type: "number", step: 0.1 },
      { name: "offsetY", label: "Y 偏移", type: "number", step: 0.1 },
    ],
    onSubmit: async (payload) => {
      const nextPayload = numericPayload(payload, ["formationId", "robotId", "slotIndex", "offsetX", "offsetY"]);
      await apiFetch("/api/formation-members", { method: "POST", body: JSON.stringify({ ...nextPayload, offsetYaw: 0 }) });
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function bindManagementSearch(ownerPage) {
  document.querySelectorAll("[data-management-search-apply]").forEach((button) => {
    button.addEventListener("click", async () => {
      const key = button.dataset.managementSearchApply;
      const filter = filterParams(key);
      filter.keyword = document.querySelector(`[data-management-search="${key}"]`)?.value?.trim() || "";
      state.paging[MANAGEMENT_FILTER_PAGING_KEYS[key]].page = 1;
      await ensureManagementPageData(ownerPage, true);
    });
  });
  document.querySelectorAll("[data-management-search-reset]").forEach((button) => {
    button.addEventListener("click", async () => {
      const key = button.dataset.managementSearchReset;
      filterParams(key).keyword = "";
      state.paging[MANAGEMENT_FILTER_PAGING_KEYS[key]].page = 1;
      await ensureManagementPageData(ownerPage, true);
    });
  });
}

function bindDeviceManagementEditors() {
  const data = state.pageData.device_management;
  document.querySelector("[data-device-category-create]")?.addEventListener("click", openDeviceCategoryCreator);
  document.querySelector("[data-managed-device-create]")?.addEventListener("click", () => openManagedDeviceCreator(data));
  document.querySelector("[data-onboard-unit-create]")?.addEventListener("click", () => openOnboardUnitCreator(data));
  document.querySelector("[data-network-channel-create]")?.addEventListener("click", () => openNetworkChannelCreator(data));
  document.querySelectorAll("[data-device-category-edit]").forEach((button) => {
    button.addEventListener("click", () => openDeviceCategoryEditor(nestedPageItem("device_management", "categories", button.dataset.id)));
  });
  document.querySelectorAll("[data-managed-device-edit]").forEach((button) => {
    button.addEventListener("click", () => openManagedDeviceEditor(nestedPageItem("device_management", "devices", button.dataset.id), data));
  });
  document.querySelectorAll("[data-onboard-unit-edit]").forEach((button) => {
    button.addEventListener("click", () => openOnboardUnitEditor(nestedPageItem("device_management", "units", button.dataset.id), data));
  });
  document.querySelectorAll("[data-network-channel-edit]").forEach((button) => {
    button.addEventListener("click", () => openNetworkChannelEditor(nestedPageItem("device_management", "channels", button.dataset.id), data));
  });
}

function bindClusterManagementEditors() {
  const data = state.pageData.cluster_management;
  document.querySelector("[data-cluster-create]")?.addEventListener("click", openClusterCreator);
  document.querySelector("[data-cluster-node-create]")?.addEventListener("click", () => openClusterNodeCreator(data));
  document.querySelector("[data-formation-create]")?.addEventListener("click", () => openFormationCreator(data));
  document.querySelector("[data-formation-member-create]")?.addEventListener("click", () => openFormationMemberCreator(data));
  document.querySelectorAll("[data-cluster-edit]").forEach((button) => {
    button.addEventListener("click", () => openClusterEditor(nestedPageItem("cluster_management", "clusters", button.dataset.id)));
  });
  document.querySelectorAll("[data-cluster-node-edit]").forEach((button) => {
    button.addEventListener("click", () => openClusterNodeEditor(nestedPageItem("cluster_management", "nodes", button.dataset.id), data));
  });
  document.querySelectorAll("[data-formation-edit]").forEach((button) => {
    button.addEventListener("click", () => openFormationEditor(nestedPageItem("cluster_management", "formations", button.dataset.id), data));
  });
}

function openDeviceCategoryEditor(item) {
  if (!item) return;
  showCrudModal({
    title: "编辑设备类别",
    values: item,
    fields: [
      { name: "name", label: "类别名称", required: true },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
      { name: "description", label: "描述", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/device-categories/${item.id}`, { method: "PUT", body: JSON.stringify(payload) });
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openManagedDeviceEditor(item, data) {
  if (!item) return;
  showCrudModal({
    title: "编辑设备信息",
    values: item,
    fields: [
      { name: "name", label: "设备名称", required: true },
      { name: "code", label: "设备编码" },
      { name: "model", label: "型号", required: true },
      { name: "manufacturer", label: "厂商" },
      { name: "serialNumber", label: "序列号" },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
      { name: "categoryId", label: "类别", type: "select", options: modalOptions(data.categoryOptions || [], "未分类") },
      { name: "robotId", label: "关联机器人", type: "select", options: modalOptions(data.robots || [], "未关联", robotOptionLabel) },
      { name: "areaId", label: "区域", type: "select", options: modalOptions(data.areas || [], "未设置") },
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/devices/${item.id}`, { method: "PUT", body: JSON.stringify(numericPayload(payload, ["areaId", "categoryId", "robotId"])) });
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openOnboardUnitEditor(item, data) {
  if (!item) return;
  showCrudModal({
    title: "编辑机载单元",
    values: item,
    fields: [
      { name: "deviceId", label: "关联设备", type: "select", required: true, options: modalOptions(data.deviceOptions || [], "请选择设备") },
      { name: "name", label: "单元名称", required: true },
      { name: "unitType", label: "单元类型", required: true },
      { name: "model", label: "型号" },
      { name: "protocol", label: "协议" },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/onboard-units/${item.id}`, { method: "PUT", body: JSON.stringify(numericPayload(payload, ["deviceId"])) });
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openNetworkChannelEditor(item, data) {
  if (!item) return;
  showCrudModal({
    title: "编辑通信通道",
    values: item,
    fields: [
      { name: "deviceId", label: "关联设备", type: "select", required: true, options: modalOptions(data.deviceOptions || [], "请选择设备") },
      { name: "name", label: "通道名称", required: true },
      { name: "channelType", label: "通信类型", required: true },
      { name: "host", label: "地址" },
      { name: "port", label: "端口", type: "number", min: 1, max: 65535 },
      { name: "protocol", label: "协议" },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/network-channels/${item.id}`, { method: "PUT", body: JSON.stringify(numericPayload(payload, ["deviceId", "port"])) });
      await ensureManagementPageData("device_management", true);
    },
  });
}

function openClusterEditor(item) {
  if (!item) return;
  showCrudModal({
    title: "编辑集群",
    values: item,
    fields: [
      { name: "name", label: "集群名称", required: true },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
      { name: "description", label: "描述", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/clusters/${item.id}`, { method: "PUT", body: JSON.stringify(payload) });
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function openClusterNodeEditor(item, data) {
  if (!item) return;
  showCrudModal({
    title: "编辑集群节点",
    values: item,
    fields: [
      { name: "clusterId", label: "所属集群", type: "select", required: true, options: modalOptions(data.clusterOptions || [], "请选择集群") },
      { name: "robotId", label: "机器人", type: "select", required: true, options: modalOptions(data.robots || [], "请选择机器人", robotOptionLabel) },
      { name: "role", label: "角色" },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/cluster-nodes/${item.id}`, { method: "PUT", body: JSON.stringify(numericPayload(payload, ["clusterId", "robotId"])) });
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function openFormationEditor(item, data) {
  if (!item) return;
  showCrudModal({
    title: "编辑编队方案",
    values: item,
    fields: [
      { name: "clusterId", label: "所属集群", type: "select", required: true, options: modalOptions(data.clusterOptions || [], "请选择集群") },
      { name: "name", label: "编队名称", required: true },
      { name: "formationType", label: "类型", type: "select", options: formationTypeOptions() },
      { name: "status", label: "状态", type: "select", options: statusOptions(item.status) },
      { name: "description", label: "描述", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/formations/${item.id}`, { method: "PUT", body: JSON.stringify(numericPayload(payload, ["clusterId"])) });
      await ensureManagementPageData("cluster_management", true);
    },
  });
}

function bindDeviceManagementPage() {
  if (!state.pageData.device_management) {
    void ensureManagementPageData("device_management");
    return;
  }
  document.querySelectorAll("[data-device-management-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.deviceManagementTab = button.dataset.deviceManagementTab;
      syncCurrentPageUrl();
      renderCurrentPage();
    });
  });
  bindSubPagination("deviceCategories", "device_management");
  bindSubPagination("devices", "device_management");
  bindSubPagination("onboardUnits", "device_management");
  bindSubPagination("networkChannels", "device_management");
  bindManagementSearch("device_management");
  bindDeviceManagementEditors();
  bindManagedForm("device-category-form", "device-category", async (form) => {
    await apiFetch("/api/device-categories", { method: "POST", body: JSON.stringify(formToObject(form)) });
    form.reset();
    state.paging.deviceCategories.page = 1;
    await ensureManagementPageData("device_management", true);
  });
  bindManagedForm("managed-device-form", "managed-device", async (form) => {
    const payload = numericPayload(formToObject(form), ["areaId", "categoryId", "robotId"]);
    await apiFetch("/api/devices", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.paging.devices.page = 1;
    await ensureManagementPageData("device_management", true);
  });
  bindManagedForm("onboard-unit-form", "onboard-unit", async (form) => {
    const payload = numericPayload(formToObject(form), ["deviceId"]);
    await apiFetch("/api/onboard-units", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.paging.onboardUnits.page = 1;
    await ensureManagementPageData("device_management", true);
  });
  bindManagedForm("network-channel-form", "network-channel", async (form) => {
    const payload = numericPayload(formToObject(form), ["deviceId", "port"]);
    await apiFetch("/api/network-channels", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.paging.networkChannels.page = 1;
    await ensureManagementPageData("device_management", true);
  });
  bindResourceDeleteButtons();
}

function bindClusterManagementPage() {
  if (!state.pageData.cluster_management) {
    void ensureManagementPageData("cluster_management");
    return;
  }
  document.querySelectorAll("[data-cluster-management-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.clusterManagementTab = button.dataset.clusterManagementTab;
      syncCurrentPageUrl();
      renderCurrentPage();
    });
  });
  bindSubPagination("clusters", "cluster_management");
  bindSubPagination("clusterNodes", "cluster_management");
  bindSubPagination("formations", "cluster_management");
  bindManagementSearch("cluster_management");
  bindClusterManagementEditors();
  bindManagedForm("cluster-form", "cluster", async (form) => {
    await apiFetch("/api/clusters", { method: "POST", body: JSON.stringify(formToObject(form)) });
    form.reset();
    state.paging.clusters.page = 1;
    await ensureManagementPageData("cluster_management", true);
  });
  bindManagedForm("cluster-node-form", "cluster-node", async (form) => {
    const payload = numericPayload(formToObject(form), ["clusterId", "robotId"]);
    await apiFetch("/api/cluster-nodes", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.paging.clusterNodes.page = 1;
    await ensureManagementPageData("cluster_management", true);
  });
  bindManagedForm("formation-form", "formation", async (form) => {
    const payload = numericPayload(formToObject(form), ["clusterId"]);
    await apiFetch("/api/formations", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.paging.formations.page = 1;
    await ensureManagementPageData("cluster_management", true);
  });
  bindManagedForm("formation-member-form", "formation-member", async (form) => {
    const payload = numericPayload(formToObject(form), ["formationId", "robotId", "slotIndex", "offsetX", "offsetY"]);
    payload.offsetYaw = 0;
    await apiFetch("/api/formation-members", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    await ensureManagementPageData("cluster_management", true);
  });
  bindResourceDeleteButtons();
}

function parseJsonParams(rawValue) {
  const raw = String(rawValue || "").trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error("控制参数必须是合法 JSON。");
  }
}

async function sendUnifiedCommand(payload, errorKey, ownerPage) {
  setFormError(errorKey);
  state.commandStatus = "";
  try {
    const response = await apiFetch("/api/control/commands", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.commandStatus = `命令 ${response.commandId} 已真实执行。`;
    await ensureManagementPageData(ownerPage, true);
  } catch (error) {
    setFormError(errorKey, error.message);
    state.commandStatus = error.message;
    renderCurrentPage();
  }
}

function selectedOptionLabel(select) {
  return select?.selectedOptions?.[0]?.textContent?.trim() || "";
}

function syncDeviceControlTargetUi() {
  const form = document.getElementById("device-motion-form");
  const select = form?.elements?.namedItem("targetId");
  const hasTarget = Boolean(select?.value);
  document.querySelectorAll("[data-device-command]").forEach((button) => {
    button.disabled = !hasTarget;
  });
  const summary = document.getElementById("device-control-target-summary");
  if (summary) summary.textContent = hasTarget ? selectedOptionLabel(select) : "未选择设备";
}

function syncClusterControlTargetUi() {
  const nodeSelect = document.querySelector("#cluster-node-control-form select[name='targetId']");
  const formationSelect = document.querySelector("#formation-control-form select[name='targetId']");
  const hasNode = Boolean(nodeSelect?.value);
  const hasFormation = Boolean(formationSelect?.value);
  document.querySelectorAll("[data-cluster-command]").forEach((button) => {
    button.disabled = !hasNode;
  });
  document.querySelectorAll("[data-formation-command]").forEach((button) => {
    button.disabled = !hasFormation;
  });
  const nodeSummary = document.getElementById("cluster-node-target-summary");
  const formationSummary = document.getElementById("formation-target-summary");
  if (nodeSummary) nodeSummary.textContent = hasNode ? selectedOptionLabel(nodeSelect) : "未选择节点";
  if (formationSummary) formationSummary.textContent = hasFormation ? selectedOptionLabel(formationSelect) : "未选择编队";
}

function bindDeviceControlPage() {
  if (!state.pageData.device_control) {
    void ensureManagementPageData("device_control");
    return;
  }
  bindSubPagination("controlCommands", "device_control");
  document.querySelector("#device-motion-form select[name='targetId']")?.addEventListener("change", syncDeviceControlTargetUi);
  syncDeviceControlTargetUi();
  document.querySelectorAll("[data-device-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      const form = document.getElementById("device-motion-form");
      const payload = numericPayload(formToObject(form), ["targetId", "linear", "angular"]);
      const params = button.dataset.deviceCommand === "cmd_vel"
        ? { linear: payload.linear, angular: payload.angular }
        : {};
      await sendUnifiedCommand({
        scope: "device",
        targetType: "device",
        targetId: payload.targetId,
        commandType: button.dataset.deviceCommand,
        params,
      }, "device-control", "device_control");
    });
  });
  document.querySelectorAll("[data-gateway-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      const form = document.getElementById("device-gateway-form");
      const payload = formToObject(form);
      const isSensor = button.dataset.gatewayCommand === "sensor_control";
      await sendUnifiedCommand({
        scope: "device",
        targetType: isSensor ? "sensor" : "network",
        targetId: Number(isSensor ? payload.sensorId : payload.networkId),
        commandType: button.dataset.gatewayCommand,
        params: parseJsonParams(payload.params),
      }, "device-gateway", "device_control");
    });
  });
}

function bindClusterControlPage() {
  if (!state.pageData.cluster_control) {
    void ensureManagementPageData("cluster_control");
    return;
  }
  bindSubPagination("controlCommands", "cluster_control");
  document.querySelector("#cluster-node-control-form select[name='targetId']")?.addEventListener("change", syncClusterControlTargetUi);
  document.querySelector("#formation-control-form select[name='targetId']")?.addEventListener("change", syncClusterControlTargetUi);
  syncClusterControlTargetUi();
  document.querySelectorAll("[data-cluster-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      const payload = numericPayload(formToObject(document.getElementById("cluster-node-control-form")), ["targetId"]);
      await sendUnifiedCommand({
        scope: "cluster",
        targetType: "cluster_node",
        targetId: payload.targetId,
        commandType: button.dataset.clusterCommand,
        params: {},
      }, "cluster-node-control", "cluster_control");
    });
  });
  document.querySelectorAll("[data-formation-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      const payload = numericPayload(formToObject(document.getElementById("formation-control-form")), ["targetId"]);
      await sendUnifiedCommand({
        scope: "cluster",
        targetType: "formation",
        targetId: payload.targetId,
        commandType: button.dataset.formationCommand,
        params: parseJsonParams(payload.params),
      }, "formation-control", "cluster_control");
    });
  });
}

function bindForms() {
  handleCreate("task", "/api/tasks");
  handleCreate("robot", "/api/robots", (payload) => numericPayload(payload, ["zoneId", "health", "battery", "speed", "signal", "latency", "lng", "lat", "heading"]));
  handleCreate("alert", "/api/alerts");
  bindZoneTools();
  bindRobotDiscoveryTools();
  bindDeleteButtons();
  if (state.pageId === "reports") bindReportsPage();
  if (state.pageId === "zones") bindZonesPage();
  if (state.pageId === "users") bindUsersPage();
  if (state.pageId === "devices") bindDevicesPage();
  if (state.pageId === "areas") bindAreasPage();
  if (state.pageId === "points") bindPointsPage();
  if (state.pageId === "routes") bindRoutesPage();
  if (state.pageId === "video") bindVideoPage();
  if (state.pageId === "perception") bindPerceptionPage();
  if (state.pageId === "control") bindControlPage();
  if (state.pageId === "device_management") bindDeviceManagementPage();
  if (state.pageId === "device_control") bindDeviceControlPage();
  if (state.pageId === "cluster_management") bindClusterManagementPage();
  if (state.pageId === "cluster_control") bindClusterControlPage();
}

function numericPayload(payload, keys) {
  const next = { ...payload };
  keys.forEach((key) => {
    if (next[key] !== undefined && next[key] !== "") {
      next[key] = Number(next[key]);
    }
  });
  return next;
}

function syncRobotMarkersInEntry(entry) {
  if (!entry?.map || typeof window.AMap === "undefined") return;
  if (!entry.robotMarkers) {
    entry.robotMarkers = {};
  }
  const nextIds = new Set((state.data?.robots || []).map((robot) => String(robot.id)));
  Object.entries(entry.robotMarkers).forEach(([robotId, marker]) => {
    if (nextIds.has(robotId)) return;
    marker.setMap(null);
    delete entry.robotMarkers[robotId];
  });
  (state.data?.robots || []).forEach((robot) => {
    const robotId = String(robot.id);
    const position = Array.isArray(robot.location) ? robot.location : null;
    if (!position || position.length !== 2) return;
    const label = {
      content: `${escapeHtml(robot.model)} ${escapeHtml(String(robot.battery))}%`,
      direction: "top",
    };
    if (!entry.robotMarkers[robotId]) {
      entry.robotMarkers[robotId] = new AMap.Marker({
        map: entry.map,
        position,
        title: robotMarkerTitle(robot),
        bubble: true,
        label,
      });
      return;
    }
    entry.robotMarkers[robotId].setPosition(position);
    entry.robotMarkers[robotId].setTitle(robotMarkerTitle(robot));
    entry.robotMarkers[robotId].setLabel(label);
    entry.robotMarkers[robotId].setMap(entry.map);
  });
}

function syncRobotMarkersInMaps() {
  Object.values(state.maps).forEach((entry) => {
    syncRobotMarkersInEntry(entry);
  });
}

async function renderMaps() {
  const mapIds = ["overview-map", "zones-map", "points-map"].filter((id) => document.getElementById(id));
  state.maps = {};
  if (!mapIds.length) {
    return;
  }

  let userCoords = null;
  try {
    userCoords = await ensureUserLocation();
  } catch (error) {
    console.warn(error.message);
  }

  if (typeof window.AMap === "undefined") {
    mapIds.forEach((id) => {
      const container = document.getElementById(id);
      if (!container) return;
      const locationText = userCoords
        ? `当前网页定位：${state.geo.locationText || `${userCoords[1].toFixed(6)}, ${userCoords[0].toFixed(6)}`}`
        : "网页定位未获取成功，请检查浏览器定位权限。";
      const amapText = appConfig.amapKey
        ? "高德脚本加载失败，当前提供的 key 不是可用的 Web JS API Key。"
        : "未配置高德 Web JS API Key。";
      container.innerHTML = `<div class=\"map-fallback\"><div><p>${amapText}</p><p>${locationText}</p></div></div>`;
    });
    return;
  }

  const defaultCenter = siteCenter();
  const defaultZoom = siteZoom();
  mapIds.forEach((id) => {
    const container = document.getElementById(id);
    if (!container) return;
    container.innerHTML = "";
    const map = new AMap.Map(id, {
      zoom: defaultZoom,
      center: defaultCenter,
    });
    state.maps[id] = { map, userMarker: null, draftPolyline: null, draftPolygon: null, robotMarkers: {} };
    map.addControl(new AMap.Scale());
    map.addControl(new AMap.ToolBar());
    state.data.zones.forEach((zone) => {
      new AMap.Polygon({
        map,
        path: zone.path,
        strokeColor: zone.strokeColor,
        fillColor: zone.fillColor,
        fillOpacity: 0.38,
        strokeWeight: 2,
        bubble: true,
      });
    });
    syncRobotMarkersInEntry(state.maps[id]);
    if (id === "points-map") {
      (state.pageData.points?.items || []).forEach((point) => {
        if (!Number.isFinite(Number(point.lng)) || !Number.isFinite(Number(point.lat))) return;
        new AMap.Marker({
          map,
          position: [Number(point.lng), Number(point.lat)],
          title: point.name,
          bubble: true,
          label: {
            content: escapeHtml(point.name),
            direction: "top",
          },
        });
      });
    }
    if (userCoords) {
      state.maps[id].userMarker = new AMap.Marker({
        map,
        position: userCoords,
        title: "我的当前位置",
        bubble: true,
        label: {
          content: "我",
          direction: "top",
        },
      });
    }
    if (id === "zones-map") {
      setupZoneDrawing(map);
    }
    if (id === "points-map") {
      setupPointPicker(map);
      if (state.pointDraft.coords) {
        if (!state.pointDraft.marker) {
          state.pointDraft.marker = new AMap.Marker({
            map,
            position: state.pointDraft.coords,
            title: `巡检点 | ${state.pointDraft.zoneName || "未命名区域"}`,
            bubble: true,
          });
        } else {
          state.pointDraft.marker.setPosition(state.pointDraft.coords);
          state.pointDraft.marker.setMap(map);
        }
      }
    }
  });
}

function canRefreshRealtimePage() {
  const active = document.activeElement;
  return !(active && (active.closest("form") || active.closest("dialog")));
}

function handleDashboardSocketMessage(message) {
  if (!message || message.type !== "dashboard_update" || !message.data) return;
  state.data = message.data;
  renderShellMeta();
  if (state.pageId === "perception" && canRefreshRealtimePage()) {
    void loadPerceptionLatest(true);
    return;
  }
  if (["overview", "status", "maintenance", "video"].includes(state.pageId) && canRefreshRealtimePage()) {
    renderCurrentPage();
    return;
  }
  if (Object.keys(state.maps).length) {
    syncRobotMarkersInMaps();
  }
}

function clearRealtimeTimers() {
  if (state.realtime.heartbeatTimer) {
    window.clearInterval(state.realtime.heartbeatTimer);
    state.realtime.heartbeatTimer = null;
  }
  if (state.realtime.reconnectTimer) {
    window.clearTimeout(state.realtime.reconnectTimer);
    state.realtime.reconnectTimer = null;
  }
}

function scheduleDashboardSocketReconnect() {
  if (state.realtime.reconnectTimer) return;
  state.realtime.reconnectTimer = window.setTimeout(() => {
    state.realtime.reconnectTimer = null;
    connectDashboardSocket();
  }, 3000);
}

function connectDashboardSocket() {
  if (typeof window.WebSocket === "undefined") return;
  const currentSocket = state.realtime.socket;
  if (currentSocket && (currentSocket.readyState === WebSocket.OPEN || currentSocket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  clearRealtimeTimers();
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/dashboard`);
  state.realtime.socket = socket;
  socket.addEventListener("open", () => {
    if (state.realtime.socket !== socket) return;
    state.realtime.heartbeatTimer = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 20000);
  });
  socket.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data);
      handleDashboardSocketMessage(payload);
    } catch (error) {
      console.warn("实时消息解析失败。", error);
    }
  });
  socket.addEventListener("error", () => {
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close();
    }
  });
  socket.addEventListener("close", () => {
    if (state.realtime.socket === socket) {
      state.realtime.socket = null;
    }
    if (state.realtime.heartbeatTimer) {
      window.clearInterval(state.realtime.heartbeatTimer);
      state.realtime.heartbeatTimer = null;
    }
    scheduleDashboardSocketReconnect();
  });
}

function tickClock() {
  clockPill.textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

logoutButton?.addEventListener("click", async () => {
  if (state.control.activeTimer) {
    await sendControlStop();
  }
  await apiFetch("/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

navToggle?.addEventListener("click", () => {
  const isOpen = document.body.classList.toggle("nav-open");
  navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  navToggle.textContent = isOpen ? "收起导航" : "展开导航";
});

navLinks?.addEventListener("click", (event) => {
  if (!event.target.closest("a")) return;
  document.body.classList.remove("nav-open");
  navToggle?.setAttribute("aria-expanded", "false");
  if (navToggle) navToggle.textContent = "展开导航";
});

window.addEventListener("blur", () => {
  if (state.control.activeTimer) {
    void sendControlStop();
  }
});

tickClock();
setInterval(tickClock, 1000);
hydrateListStateFromUrl();
startLocationWatch();

loadDashboard()
  .then(() => {
    connectDashboardSocket();
  })
  .catch((error) => {
    pageContent.innerHTML = `<section class="panel"><div class="empty-state">${escapeHtml(error.message)}</div></section>`;
  });
