const appConfig = window.APP_CONFIG || {};
const { apiFetch } = window.DashboardApi;
const { escapeHtml, formatDateTime, localizeToken, pillClass } = window.DashboardUi;
const dashboardRealtime = window.DashboardRealtime;
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
const VIDEO_SNAPSHOT_REFRESH_MS = 1000;
const SENSOR_STALE_FALLBACK_SECONDS = 8;
const LIDAR_SWEEP_DURATION_MS = 1200;
const LIDAR_TRAIL_LIMIT = 24;
const LIDAR_REFRESH_MS = 1500;
const AUTOPILOT_REFRESH_MS = 2000;

const state = {
  pageId: appConfig.pageId,
  data: null,
  maps: {},
  pageData: {},
  paging: {
    users: { page: 1, size: 10 },
    devices: { page: 1, size: 10 },
    reports: { page: 1, size: 10 },
    deviceCategories: { page: 1, size: 10 },
    onboardUnits: { page: 1, size: 10 },
    networkChannels: { page: 1, size: 10 },
    clusters: { page: 1, size: 10 },
    clusterNodes: { page: 1, size: 10 },
    formations: { page: 1, size: 10 },
    controlCommands: { page: 1, size: 10 },
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
  geo: {
    coords: null,
    promise: null,
    status: "idle",
    watchId: null,
    locationText: null,
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
  sensors: {
    robotId: "",
    data: null,
    error: "",
    loading: false,
    autoTimer: null,
    lidarTrail: [],
    lidarAnimationId: null,
    lidarSweepStartedAt: 0,
    lidarLastFrameKey: "",
    requestSeq: 0,
    loadingRobotId: "",
  },
  robotMaps: {
    items: [],
    selectedId: "",
    loading: false,
    error: "",
    zoom: 1,
  },
  control: {
    activeTimer: null,
    activeRobotId: "",
    commandInFlight: false,
    activeButton: "",
    activeKey: "",
    robotId: "",
    status: "尚未连接控制服务。",
    connection: "unknown",
    linear: 0,
    angular: 0,
    lastAck: null,
    lastSentAt: "",
  },
  autopilot: {
    robotId: "",
    status: null,
    error: "",
    loading: false,
    actionInFlight: "",
    timer: null,
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
  ok: "正常",
  line: "直线",
  wedge: "楔形",
  column: "纵队",
};
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
const FALLBACK_SITE_CENTER = [113.584411, 22.349433];
const CONTROL_HOLD_INTERVAL_MS = 180;
const CONTROL_KEY_BINDINGS = {
  ArrowUp: { linear: 1, angular: 0 },
  KeyW: { linear: 1, angular: 0 },
  ArrowDown: { linear: -1, angular: 0 },
  KeyS: { linear: -1, angular: 0 },
  ArrowLeft: { linear: 0, angular: 1 },
  KeyA: { linear: 0, angular: 1 },
  ArrowRight: { linear: 0, angular: -1 },
  KeyD: { linear: 0, angular: -1 },
  KeyQ: { linear: 1, angular: 1 },
  KeyE: { linear: 1, angular: -1 },
  KeyZ: { linear: -1, angular: -1 },
  KeyC: { linear: -1, angular: 1 },
};
const AUTOPILOT_MODE_TEXT = {
  manual: "手动",
  auto_ready: "自动就绪",
  auto_running: "自动运行",
  paused: "暂停",
  fault: "故障",
  estop: "急停",
};
const AUTOPILOT_REASON_TEXT = {
  manual_control: "人工控制",
  front_clear: "前方安全，低速前进",
  front_slow: "前方较近，自动减速",
  front_blocked: "前方障碍物过近，停车",
  both_front_blocked: "左右前方均受阻，停车",
  lidar_timeout: "LiDAR 超过 2 秒未更新",
  control_timeout: "控制指令超时",
  user_paused: "用户暂停",
  stopped_by_user: "用户停止",
  manual_override: "人工接管",
  user_estop: "用户触发急停",
  estop_cleared: "急停已手动解除",
};
const URL_SYNC_PAGE_IDS = new Set(["devices"]);
const COMMAND_PAGE_IDS = new Set([]);
const DEVICE_STATUS_FILTERS = new Set(["normal", "repair", "offline"]);
const MANAGEMENT_FILTER_PAGING_KEYS = {
  deviceCategories: "deviceCategories",
  managedDevices: "devices",
  onboardUnits: "onboardUnits",
  networkChannels: "networkChannels",
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
};
window.DashboardTokenText = TOKEN_TEXT;

// ===== Dashboard state and domain helpers =====

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


function robotOptionLabel(robot) {
  const name = robot?.model || `机器人 ${robot?.id ?? ""}`.trim();
  return robot?.ipAddress ? `${name} · ${robot.ipAddress}` : name;
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

async function loadDashboard() {
  const payload = await apiFetch("/api/dashboard");
  state.data = payload.data;
  renderShellMeta();
  renderCurrentPage();
}

// ===== Shell metadata and location =====
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
    currentLocation.textContent = `当前位置：${label}`;
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
  updateLocationLabels(locationText);
  setGpsStatus(`${sourceLabel}已定位`, "success");
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
      <article class="stat-card"><span>任务</span><strong>${counts.tasks ?? 0}</strong><small class="muted">已创建巡检任务</small></article>
      <article class="stat-card"><span>告警</span><strong>${counts.alerts}</strong><small class="muted">待处理事件数量</small></article>
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

// ===== Page renderers =====
function renderOverviewPage() {
  const robots = state.data.robots.slice(0, 4);
  return `
    <section class="dashboard-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>机器人动态</h2><p class="muted">车队实时遥测信息</p></div></div>
        <div class="list-stack">
          ${robots.length ? robots.map((robot) => `
            <div class="list-item">
              <div>
                <strong>${escapeHtml(robot.model)}</strong>
                <p>最近上报 ${escapeHtml(formatDateTime(robot.lastSeenAt || robot.createdAt))}</p>
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
    </section>
    <section class="dashboard-grid">
      <article class="panel">
        <div class="panel-header"><div><h2>地图</h2><p class="muted">机器人位置</p></div></div>
        <div id="overview-map" class="map-shell"><div class="map-fallback">检测到高德地图后将在此渲染。</div></div>
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
        ${renderTable("robots", ["ID", "机器人名称", "IP", "运行状态", "网络", "电量", "位置", "最近上报", "操作"], state.data.robots.map((robot) => `
          <tr>
            <td>${robot.id}</td>
            <td>${escapeHtml(robot.model)}</td>
            <td>${escapeHtml(robot.ipAddress || "-")}</td>
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

function markVideoImageOffline(image) {
  if (!image) return;
  image.dataset.offline = "1";
  const shell = image.closest(".camera-frame-shell, .video-thumb-shell");
  if (shell) shell.dataset.videoOffline = "1";
}

function markVideoImageOnline(image) {
  if (!image) return;
  delete image.dataset.offline;
  const shell = image.closest(".camera-frame-shell, .video-thumb-shell");
  if (shell) delete shell.dataset.videoOffline;
}

function bindVideoImageStatus() {
  document.querySelectorAll("[data-video-snapshot], [data-main-snapshot]").forEach((image) => {
    image.addEventListener("load", () => markVideoImageOnline(image), { once: false });
    image.addEventListener("error", () => markVideoImageOffline(image), { once: false });
  });
}

function probeVideoSnapshot(image, url, updateSrc = false) {
  if (!image || !url) return;
  const probe = new Image();
  image.__videoProbe = probe;
  probe.onload = () => {
    if (image.__videoProbe !== probe) return;
    markVideoImageOnline(image);
    if (updateSrc) image.src = url;
    image.__videoProbe = null;
  };
  probe.onerror = () => {
    if (image.__videoProbe !== probe) return;
    markVideoImageOffline(image);
    image.__videoProbe = null;
  };
  probe.src = url;
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
  const mainSnapshotUrl = cameraSnapshotUrl(mainRobot);
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
          <span class="video-offline-badge">画面离线</span>
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
          <p class="muted">主画面按 1 秒刷新实时快照；下方小画面同步刷新，点击任意车辆即可切换主画面。</p>
        </div>
        <div class="panel-actions">
          <a class="secondary-button" href="${escapeHtml(mainStreamUrl)}" target="_blank" rel="noreferrer">打开 MJPEG 源</a>
        </div>
      </div>
      <div class="video-main-layout">
        <div class="camera-frame-shell video-main-frame">
          <img class="camera-stream" src="${escapeHtml(mainSnapshotUrl)}" alt="${escapeHtml(mainRobot.model)} 实时画面" style="aspect-ratio: 16 / 9; width: 100%; height: auto;" data-main-snapshot data-main-snapshot-base="${escapeHtml(cameraSnapshotBaseUrl(mainRobot))}">
          <div class="video-offline-overlay">画面已离线，等待新帧</div>
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
          <p class="muted">主画面使用后端校验过的新鲜快照，车辆离线或没有新帧时会自动显示离线状态。</p>
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
    return `<img class="camera-stream perception-overlay" src="${escapeHtml(overlay)}?t=${Date.now()}" alt="Orin 智能感知结果叠加图" loading="lazy" style="aspect-ratio: 16 / 9; width: 100%; height: auto;">`;
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

/* ─── 传感器数据页 ──────────────────────────────────────────── */

function ensureSensorRobotSelection() {
  const robots = videoRobots();
  if (!robots.length) {
    state.sensors.robotId = "";
    state.sensors.data = null;
    return null;
  }
  const current = robots.find((r) => String(r.id) === String(state.sensors.robotId));
  const next = current || robots.find(robotIsOnline) || robots[0];
  state.sensors.robotId = String(next.id);
  return next;
}

async function loadRobotSensorData(force = false) {
  const robot = ensureSensorRobotSelection();
  if (!robot || (!force && state.sensors.data?.robotId === robot.id)) return;
  if (state.sensors.loading && state.sensors.loadingRobotId === String(robot.id)) return;
  const requestSeq = state.sensors.requestSeq + 1;
  state.sensors.requestSeq = requestSeq;
  state.sensors.loading = true;
  state.sensors.loadingRobotId = String(robot.id);
  state.sensors.error = "";
  updateSensorsDom();
  try {
    const data = await apiFetch(`/api/robots/${encodeURIComponent(robot.id)}/sensors/latest`);
    if (requestSeq !== state.sensors.requestSeq || String(state.sensors.robotId) !== String(robot.id)) return;
    state.sensors.data = data;
    const latestLidar = lidarItems(data)[0];
    if (latestLidar) {
      rememberLidarFrame(latestLidar);
    } else {
      state.sensors.lidarTrail = [];
      state.sensors.lidarLastFrameKey = "";
    }
  } catch (err) {
    if (requestSeq !== state.sensors.requestSeq || String(state.sensors.robotId) !== String(robot.id)) return;
    if (!state.sensors.data || String(state.sensors.data.robotId) !== String(robot.id)) {
      state.sensors.data = null;
    }
    state.sensors.error = err.message;
  } finally {
    if (requestSeq !== state.sensors.requestSeq) return;
    state.sensors.loading = false;
    state.sensors.loadingRobotId = "";
    updateSensorsDom();
  }
}

function stereoItems(data) {
  return sortSensorItems((data?.sensors || []).filter((s) => s.sensorType === "stereo" && s.filePath && !sensorIsStale(s)), "stereo");
}

function cameraItems(data) {
  return sortSensorItems((data?.sensors || []).filter((s) => s.sensorType === "camera" && s.filePath && !sensorIsStale(s)), "camera");
}

function lidarItems(data) {
  return (data?.sensors || []).filter((s) => s.sensorType === "lidar" && s.data && !sensorIsStale(s));
}

function sortSensorItems(items, fallbackChannel) {
  return items.slice().sort((a, b) => sensorItemKey(a, fallbackChannel).localeCompare(sensorItemKey(b, fallbackChannel)));
}

function sensorIsStale(item) {
  if (!item) return true;
  if (item.stale === true) return true;
  if (item.stale === false) return false;
  const reportedAt = Date.parse(item.reportedAt || "");
  if (!Number.isFinite(reportedAt)) return false;
  const staleAfterSeconds = Number(
    item.staleAfterSeconds
    || state.sensors.data?.staleAfterSecondsByType?.[item.sensorType]
    || state.sensors.data?.staleAfterSeconds
    || SENSOR_STALE_FALLBACK_SECONDS,
  );
  return (Date.now() - reportedAt) / 1000 > staleAfterSeconds;
}

function staleSensorCount(data, sensorType) {
  return (data?.sensors || []).filter((s) => s.sensorType === sensorType && sensorIsStale(s)).length;
}

function sensorImageUrl(item) {
  const src = String(item?.filePath || "");
  if (!src) return "";
  const stamp = encodeURIComponent(item?.reportedAt || item?.sizeBytes || Date.now());
  return `${src}${src.includes("?") ? "&" : "?"}t=${stamp}`;
}

function replaceHtmlIfChanged(element, html) {
  if (!element || element.__renderedHtml === html) return;
  element.innerHTML = html;
  element.__renderedHtml = html;
}

function sensorChannelLabel(item, fallback = "unknown") {
  return String(item?.channel || fallback);
}

function sensorItemKey(item, fallback = "sensor") {
  return [
    item?.sensorType || fallback,
    item?.channel || fallback,
    item?.contentType || "",
  ].join(":");
}

// ===== Sensor and LiDAR rendering =====
function renderSensorImageCard(item, fallbackChannel) {
  const key = sensorItemKey(item, fallbackChannel);
  const label = sensorChannelLabel(item, fallbackChannel);
  const src = sensorImageUrl(item);
  return `
    <div class="sensor-image-card" data-sensor-card="${escapeHtml(key)}">
      <img
        src="${escapeHtml(src)}"
        alt="${escapeHtml(label)}"
        loading="eager"
        decoding="async"
        class="sensor-thumb"
        data-sensor-image
        data-loaded-src="${escapeHtml(src)}"
      >
      <div class="sensor-image-meta">
        <span class="meta-pill" data-sensor-channel>${escapeHtml(label)}</span>
        <span class="muted" data-sensor-time>${escapeHtml(formatDateTime(item.reportedAt))}</span>
      </div>
    </div>`;
}

function renderSensorImageCards(items, emptyHtml, fallbackChannel) {
  return items.length
    ? items.map((item) => renderSensorImageCard(item, fallbackChannel)).join("")
    : emptyHtml;
}

function renderStereoEmptyState(data) {
  const hasStereoConfig = (data?.sensors || []).some((s) => s.sensorType === "stereo");
  const staleCount = staleSensorCount(data, "stereo");
  return `<div class="empty-state">${staleCount ? "双目/深度图已离线，等待新帧。" : hasStereoConfig ? "暂无双目/深度图数据。" : "当前设备未配备双目摄像头。"}</div>`;
}

function renderCameraEmptyState(data) {
  return `<div class="empty-state">${staleSensorCount(data, "camera") ? "单目摄像头已离线，等待新帧。" : "暂无单目摄像头数据。"}</div>`;
}

function formatMeters(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? `${(Math.round(numeric * 100) / 100).toFixed(2)} m` : "-";
}

function lidarNearestDistance(data) {
  const points = scanPoints(data, 1);
  if (!points.length) {
    const fallback = Number(data?.minRange);
    return Number.isFinite(fallback) && fallback > 0 ? fallback : null;
  }
  return points.reduce((min, point) => Math.min(min, point.dist), Infinity);
}

function lidarSectorDistance(data, minDeg, maxDeg) {
  const points = scanPoints(data, 1).filter((point) => {
    const deg = ((point.angle * 180 / Math.PI) % 360 + 360) % 360;
    return deg >= minDeg && deg <= maxDeg;
  });
  return points.length ? points.reduce((min, point) => Math.min(min, point.dist), Infinity) : null;
}

function latestLidarItem() {
  return lidarItems(state.sensors.data)[0] || null;
}

function latestLidarDebugPayload() {
  const item = latestLidarItem();
  if (!item) return null;
  return {
    robotId: state.sensors.data?.robotId ?? state.sensors.robotId ?? null,
    deviceId: state.sensors.data?.deviceId ?? null,
    deviceMatchSource: state.sensors.data?.deviceMatchSource || "",
    sensor: item,
  };
}

function renderLidarInfo(data) {
  const lidars = lidarItems(data);
  const lidarData = lidars.length ? lidars[0].data : null;
  const displayRange = lidarData ? Math.round(lidarFrameDisplayRange(lidarData) * 10) / 10 : null;
  const nearest = lidarData ? lidarNearestDistance(lidarData) : null;
  const rightFront = lidarData ? lidarSectorDistance(lidarData, 0, 60) : null;
  const front = lidarData ? lidarSectorDistance(lidarData, 60, 120) : null;
  const leftFront = lidarData ? lidarSectorDistance(lidarData, 120, 180) : null;
  return lidarData ? `
    <div class="metric-grid">
      <div class="metric-card"><strong>${escapeHtml(lidarData.numBeams ?? "-")}</strong><span>扫描光束数</span></div>
      <div class="metric-card"><strong>${escapeHtml(lidarData.renderedBeams ?? (lidarData.ranges || []).length ?? "-")}</strong><span>显示点数</span></div>
      <div class="metric-card"><strong>${escapeHtml(lidarData.validBeams ?? "-")}</strong><span>有效光束数</span></div>
      <div class="metric-card"><strong>${escapeHtml(formatMeters(nearest))}</strong><span>最近障碍物距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(formatMeters(leftFront))}</strong><span>左前最小距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(formatMeters(front))}</strong><span>正前最小距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(formatMeters(rightFront))}</strong><span>右前最小距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(formatMeters(lidarData.minRange))}</strong><span>全局最近距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(lidarData.maxRange ?? "-")} m</strong><span>最远距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(lidarData.meanRange ?? "-")} m</strong><span>平均距离</span></div>
      <div class="metric-card"><strong>${escapeHtml(displayRange ?? "-")} m</strong><span>显示范围</span></div>
      <div class="metric-card"><strong>${escapeHtml(lidarData.frameId || "-")}</strong><span>坐标系</span></div>
      <div class="metric-card"><strong>${escapeHtml(formatDateTime(lidars[0].reportedAt))}</strong><span>上报时间</span></div>
    </div>` : `<div class="empty-state">${staleSensorCount(data, "lidar") ? "雷达扫描已离线，等待新帧。" : "暂无雷达扫描数据。"}</div>`;
}

function updateSensorImageWhenReady(image, nextSrc) {
  if (!image || !nextSrc || image.dataset.loadedSrc === nextSrc || image.dataset.pendingSrc === nextSrc) return;
  image.dataset.pendingSrc = nextSrc;
  const preloader = new Image();
  image.__sensorPreloader = preloader;
  preloader.onload = () => {
    if (image.dataset.pendingSrc !== nextSrc) return;
    image.src = nextSrc;
    image.dataset.loadedSrc = nextSrc;
    delete image.dataset.pendingSrc;
    image.__sensorPreloader = null;
  };
  preloader.onerror = () => {
    if (image.dataset.pendingSrc === nextSrc) delete image.dataset.pendingSrc;
    if (image.__sensorPreloader === preloader) image.__sensorPreloader = null;
  };
  preloader.src = nextSrc;
}

function updateSensorImageCard(card, item, fallbackChannel) {
  const image = card?.querySelector("[data-sensor-image]");
  const channel = card?.querySelector("[data-sensor-channel]");
  const time = card?.querySelector("[data-sensor-time]");
  if (!card || !image || !channel || !time) return false;
  const label = sensorChannelLabel(item, fallbackChannel);
  image.alt = label;
  updateSensorImageWhenReady(image, sensorImageUrl(item));
  if (channel.textContent !== label) channel.textContent = label;
  const timeText = formatDateTime(item.reportedAt);
  if (time.textContent !== timeText) time.textContent = timeText;
  return true;
}

function updateSensorImageGrid(gridId, items, emptyHtml, fallbackChannel) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  if (!items.length) {
    grid.dataset.itemKeys = "";
    replaceHtmlIfChanged(grid, emptyHtml);
    return;
  }
  const keys = items.map((item) => sensorItemKey(item, fallbackChannel)).join("|");
  if (grid.dataset.itemKeys !== keys) {
    grid.innerHTML = renderSensorImageCards(items, emptyHtml, fallbackChannel);
    grid.dataset.itemKeys = keys;
    grid.__renderedHtml = "";
    return;
  }
  const cards = new Map();
  grid.querySelectorAll("[data-sensor-card]").forEach((card) => {
    cards.set(card.dataset.sensorCard || "", card);
  });
  const allUpdated = items.every((item) => {
    const key = sensorItemKey(item, fallbackChannel);
    return updateSensorImageCard(cards.get(key), item, fallbackChannel);
  });
  if (!allUpdated) {
    grid.innerHTML = renderSensorImageCards(items, emptyHtml, fallbackChannel);
    grid.dataset.itemKeys = keys;
    grid.__renderedHtml = "";
  }
}

function updateSensorsDom() {
  if (state.pageId !== "sensors") return;
  const stereoGrid = document.getElementById("sensor-stereo-grid");
  const cameraGrid = document.getElementById("sensor-camera-grid");
  if (!stereoGrid || !cameraGrid) {
    renderCurrentPage();
    return;
  }
  const data = state.sensors.data;
  const refreshButton = document.getElementById("sensor-refresh");
  if (refreshButton) refreshButton.disabled = state.sensors.loading && !data;
  const selector = document.getElementById("sensor-robot");
  if (selector && selector.value !== String(state.sensors.robotId || "")) {
    selector.value = String(state.sensors.robotId || "");
  }
  replaceHtmlIfChanged(
    document.getElementById("sensor-error-slot"),
    state.sensors.error ? `<p class="form-error" role="alert">${escapeHtml(state.sensors.error)}</p>` : "",
  );
  replaceHtmlIfChanged(
    document.getElementById("sensor-loading-slot"),
    state.sensors.loading && !data ? `<p class="muted">正在加载传感器数据…</p>` : "",
  );
  updateSensorImageGrid("sensor-stereo-grid", stereoItems(data), renderStereoEmptyState(data), "stereo");
  updateSensorImageGrid("sensor-camera-grid", cameraItems(data), renderCameraEmptyState(data), "camera");
  replaceHtmlIfChanged(document.getElementById("sensor-lidar-metrics"), renderLidarInfo(data));
  updateLidarActionButtons();
  const latestLidar = lidarItems(data)[0];
  if (latestLidar) {
    rememberLidarFrame(latestLidar);
  } else {
    state.sensors.lidarTrail = [];
    state.sensors.lidarLastFrameKey = "";
  }
  if (!document.hidden && !state.sensors.lidarAnimationId && document.getElementById("lidar-canvas")) {
    startLidarAnimation();
  }
}

function updateLidarActionButtons() {
  const hasLidar = Boolean(latestLidarItem());
  const copyButton = document.getElementById("lidar-copy-json");
  const downloadButton = document.getElementById("lidar-download-json");
  if (copyButton) copyButton.disabled = !hasLidar;
  if (downloadButton) downloadButton.disabled = !hasLidar;
}

function latestLidarJsonText() {
  const payload = latestLidarDebugPayload();
  return payload ? JSON.stringify(payload, null, 2) : "";
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

async function copyLatestLidarJson() {
  const button = document.getElementById("lidar-copy-json");
  const text = latestLidarJsonText();
  if (!text) return;
  await copyTextToClipboard(text);
  if (button) {
    const original = button.textContent;
    button.textContent = "已复制";
    window.setTimeout(() => {
      button.textContent = original || "复制 JSON";
    }, 1200);
  }
}

function downloadLatestLidarJson() {
  const text = latestLidarJsonText();
  if (!text) return;
  const robotId = String(state.sensors.data?.robotId || state.sensors.robotId || "unknown").replace(/[^\w.-]+/g, "_");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `lidar-${robotId}-${stamp}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function lidarFrameKey(item) {
  if (!item) return "";
  const data = item.data || item;
  return [
    item.reportedAt || data.timestamp || "",
    data.validBeams ?? "",
    data.minRange ?? "",
    data.meanRange ?? "",
    data.maxRange ?? "",
  ].join("|");
}

function rememberLidarFrame(item) {
  if (!item?.data) return;
  const key = lidarFrameKey(item);
  if (!key || key === state.sensors.lidarLastFrameKey) return;
  const trail = state.sensors.lidarTrail || [];
  trail.push({
    key,
    reportedAt: item.reportedAt || "",
    data: item.data,
    receivedAt: performance.now(),
  });
  while (trail.length > LIDAR_TRAIL_LIMIT) trail.shift();
  state.sensors.lidarTrail = trail;
  state.sensors.lidarLastFrameKey = key;
  state.sensors.lidarSweepStartedAt = performance.now();
}

function currentLidarFrame() {
  const trail = state.sensors.lidarTrail || [];
  return trail.length ? trail[trail.length - 1] : null;
}

function stopLidarAnimation() {
  if (state.sensors.lidarAnimationId) {
    window.cancelAnimationFrame(state.sensors.lidarAnimationId);
    state.sensors.lidarAnimationId = null;
  }
}

function startLidarAnimation() {
  if (state.sensors.lidarAnimationId) return;
  if (document.hidden) return;
  stopLidarAnimation();
  const tick = (now) => {
    if (state.pageId !== "sensors" || document.hidden) {
      stopLidarAnimation();
      return;
    }
    const canvas = document.getElementById("lidar-canvas");
    if (canvas) {
      drawLidarCanvas(canvas, state.sensors.lidarTrail || [], now);
    }
    state.sensors.lidarAnimationId = window.requestAnimationFrame(tick);
  };
  state.sensors.lidarAnimationId = window.requestAnimationFrame(tick);
}

function scanPoints(data, upto = 1) {
  const ranges = data?.ranges || [];
  if (!ranges.length) return [];
  const angleMin = Number(data.angleMin ?? -Math.PI);
  const angleIncrement = Number(data.angleIncrement || 0);
  const angleMax = Number(data.angleMax ?? Math.PI);
  const step = angleIncrement || ((angleMax - angleMin) / Math.max(ranges.length - 1, 1));
  const limit = Math.max(0, Math.min(ranges.length, Math.ceil(ranges.length * upto)));
  const displayMax = lidarFrameDisplayRange(data);
  const hardwareMax = Number(data.rangeMax || data.sourceRangeMax || 0);
  const validLimit = Math.max(displayMax * 1.08, Number.isFinite(hardwareMax) && hardwareMax > 0 ? hardwareMax : displayMax);
  const points = [];
  for (let i = 0; i < limit; i++) {
    const dist = Number(ranges[i]);
    if (!dist || dist <= 0 || !Number.isFinite(dist) || dist > validLimit) continue;
    points.push({ angle: angleMin + i * step, dist, index: i });
  }
  return points;
}

function lidarFrameDisplayRange(data) {
  const ranges = Array.isArray(data?.ranges) ? data.ranges : [];
  const finiteRanges = ranges
    .map(Number)
    .filter((value) => Number.isFinite(value) && value > 0);
  const candidates = [
    data?.displayRange,
    data?.maxRange,
    data?.meanRange ? Number(data.meanRange) * 2.4 : null,
    finiteRanges.length ? finiteRanges.reduce((max, value) => Math.max(max, value), 0) : null,
  ].map(Number).filter((value) => Number.isFinite(value) && value > 0);
  let displayRange = candidates.length ? Math.max(...candidates) : 12;
  displayRange = Math.min(displayRange, 40);
  return Math.max(4, displayRange * 1.08);
}

function lidarDisplayMax(frames) {
  let maxRange = 0;
  for (const frame of frames || []) {
    const data = frame.data || frame;
    const candidates = [lidarFrameDisplayRange(data), data.rangeMin].map(Number).filter(Number.isFinite);
    for (const value of candidates) {
      if (value > maxRange) maxRange = value;
    }
  }
  if (maxRange <= 0) maxRange = 12;
  return Math.max(4, Math.ceil(maxRange));
}

function prepareLidarCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const cssWidth = Math.max(1, Math.round(rect.width || canvas.clientWidth || 560));
  const cssHeight = Math.max(1, Math.round(rect.height || canvas.clientHeight || cssWidth));
  const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 3));
  const pixelWidth = Math.round(cssWidth * dpr);
  const pixelHeight = Math.round(cssHeight * dpr);
  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: cssWidth, h: cssHeight };
}

function drawLidarCanvas(canvas, frames, now = performance.now()) {
  if (!canvas) return;
  const { ctx, w, h } = prepareLidarCanvas(canvas);
  const cx = w / 2;
  const cy = h / 2;
  const padding = 42;
  const allFrames = frames || [];
  const current = allFrames.length ? allFrames[allFrames.length - 1] : null;
  const displayMax = lidarDisplayMax(allFrames);
  const scale = (Math.min(w, h) / 2 - padding) / displayMax;
  const sweepElapsed = now - (state.sensors.lidarSweepStartedAt || now);
  const sweepProgress = current ? Math.min(1, Math.max(0, sweepElapsed / LIDAR_SWEEP_DURATION_MS)) : 0;

  ctx.fillStyle = "#111111";
  ctx.fillRect(0, 0, w, h);
  const vignette = ctx.createRadialGradient(cx, cy, Math.min(w, h) * 0.08, cx, cy, Math.min(w, h) * 0.58);
  vignette.addColorStop(0, "rgba(45, 70, 56, 0.10)");
  vignette.addColorStop(1, "rgba(0, 0, 0, 0.45)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, w, h);

  drawRvizGrid(ctx, cx, cy, w, h, displayMax, scale);
  if (!current) {
    ctx.fillStyle = "rgba(210,255,210,0.42)";
    ctx.font = "15px 'Microsoft YaHei UI', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("等待 LiDAR 扫描", cx, cy - 18);
    drawRvizRobot(ctx, cx, cy);
    return;
  }

  for (let i = 0; i < allFrames.length; i++) {
    const frame = allFrames[i];
    const isCurrent = frame === current;
    const age = Math.max(0, now - (frame.receivedAt || now));
    const ageFade = Math.max(0, 1 - age / 26000);
    const orderFade = (i + 1) / allFrames.length;
    const alpha = isCurrent ? 0.95 : Math.max(0.04, ageFade * orderFade * 0.24);
    drawScanFrame(ctx, frame.data, cx, cy, scale, alpha, !isCurrent, isCurrent ? sweepProgress : 1);
  }
  drawSweepOverlay(ctx, current.data, cx, cy, scale, displayMax, sweepProgress);
  drawRvizRobot(ctx, cx, cy);
  drawLidarHud(ctx, current, displayMax, sweepProgress);
}

function drawRvizGrid(ctx, cx, cy, w, h, displayMax, scale) {
  ctx.save();
  ctx.strokeStyle = "rgba(82, 255, 111, 0.16)";
  ctx.fillStyle = "rgba(155, 255, 172, 0.48)";
  ctx.lineWidth = 1;
  ctx.font = "10px 'Cascadia Mono', 'Courier New', monospace";
  ctx.textAlign = "left";
  const ringStep = displayMax <= 6 ? 1 : displayMax <= 14 ? 2 : displayMax <= 28 ? 4 : 8;
  for (let d = ringStep; d <= displayMax; d += ringStep) {
    const r = d * scale;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.fillText(`${d} m`, cx + r + 5, cy - 5);
  }
  ctx.strokeStyle = "rgba(82, 255, 111, 0.20)";
  ctx.beginPath();
  ctx.moveTo(cx, 10);
  ctx.lineTo(cx, h - 10);
  ctx.moveTo(10, cy);
  ctx.lineTo(w - 10, cy);
  ctx.stroke();
  ctx.strokeStyle = "rgba(82, 255, 111, 0.10)";
  for (let deg = 30; deg < 180; deg += 30) {
    const angle = deg * Math.PI / 180;
    const dx = Math.cos(angle) * displayMax * scale;
    const dy = Math.sin(angle) * displayMax * scale;
    ctx.beginPath();
    ctx.moveTo(cx - dx, cy - dy);
    ctx.lineTo(cx + dx, cy + dy);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx - dx, cy + dy);
    ctx.lineTo(cx + dx, cy - dy);
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(155, 255, 172, 0.52)";
  ctx.font = "11px 'Microsoft YaHei UI', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("前", cx, 24);
  ctx.fillText("后", cx, h - 16);
  ctx.textAlign = "left";
  ctx.fillText("右", w - 30, cy - 8);
  ctx.textAlign = "right";
  ctx.fillText("左", 30, cy - 8);
  ctx.restore();
}

/** Draw a single scan frame with RViz-like color and decay. */
function drawScanFrame(ctx, data, cx, cy, scale, alphaMul, isTrail, progress = 1) {
  const points = scanPoints(data, progress);
  if (!points.length) return;
  const maxR = lidarFrameDisplayRange(data);
  const dotR = isTrail ? 1.25 : 2.2;
  for (const point of points) {
    const x = cx + Math.cos(point.angle) * point.dist * scale;
    const y = cy - Math.sin(point.angle) * point.dist * scale;
    const color = lidarColor(point.dist, maxR, alphaMul);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, dotR, 0, 2 * Math.PI);
    ctx.fill();
    if (!isTrail) {
      ctx.fillStyle = lidarColor(point.dist, maxR, alphaMul * 0.18);
      ctx.beginPath();
      ctx.arc(x, y, dotR + 3.2, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
}

/** Map distance to RViz-style color (red→yellow→green→cyan) */
function lidarColor(dist, maxRange, alpha) {
  const t = Math.min(dist / (maxRange || 1), 1.0);
  let r, g, b;
  if (t < 0.25) {
    // red → yellow
    const s = t / 0.25;
    r = 255; g = Math.round(200 * s); b = 30;
  } else if (t < 0.5) {
    // yellow → green
    const s = (t - 0.25) / 0.25;
    r = Math.round(255 * (1 - s)); g = 220; b = 30;
  } else if (t < 0.75) {
    // green → cyan
    const s = (t - 0.5) / 0.25;
    r = 0; g = Math.round(220 - 40 * s); b = Math.round(30 + 200 * s);
  } else {
    // cyan → blue
    const s = (t - 0.75) / 0.25;
    r = Math.round(30 * s); g = Math.round(180 * (1 - s)); b = Math.round(230 + 25 * s);
  }
  return `rgba(${r},${g},${b},${alpha})`;
}

function drawSweepOverlay(ctx, data, cx, cy, scale, displayMax, progress) {
  const ranges = data?.ranges || [];
  if (!ranges.length) return;
  const angleMin = Number(data.angleMin ?? -Math.PI);
  const angleIncrement = Number(data.angleIncrement || 0);
  const angleMax = Number(data.angleMax ?? Math.PI);
  const step = angleIncrement || ((angleMax - angleMin) / Math.max(ranges.length - 1, 1));
  const sweepIndex = Math.max(0, Math.min(ranges.length - 1, Math.floor((ranges.length - 1) * progress)));
  const sweepAngle = angleMin + sweepIndex * step;
  const radius = displayMax * scale;
  const wedge = 0.16;

  ctx.save();
  const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
  gradient.addColorStop(0, "rgba(100,255,130,0.16)");
  gradient.addColorStop(1, "rgba(100,255,130,0)");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, radius, -sweepAngle - wedge, -sweepAngle + wedge);
  ctx.closePath();
  ctx.fill();

  const x = cx + Math.cos(sweepAngle) * radius;
  const y = cy - Math.sin(sweepAngle) * radius;
  ctx.strokeStyle = "rgba(160,255,150,0.88)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(x, y);
  ctx.stroke();
  ctx.strokeStyle = "rgba(160,255,150,0.22)";
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(x, y);
  ctx.stroke();
  ctx.restore();
}

function drawLidarHud(ctx, frame, displayMax, progress) {
  const data = frame?.data || {};
  ctx.save();
  ctx.fillStyle = "rgba(17,17,17,0.70)";
  ctx.strokeStyle = "rgba(97,255,122,0.28)";
  ctx.lineWidth = 1;
  roundedRectPath(ctx, 14, 14, 178, 76, 8);
  ctx.fillStyle = "rgba(183,255,188,0.82)";
  ctx.font = "11px 'Cascadia Mono', 'Courier New', monospace";
  ctx.textAlign = "left";
  ctx.fillText(`Fixed Frame: laser`, 26, 34);
  ctx.fillText(`Points: ${data.validBeams ?? "-"} / ${data.numBeams ?? data.renderedBeams ?? "-"}`, 26, 51);
  ctx.fillText(`View: ${displayMax} m`, 26, 68);
  ctx.fillText(`Sweep: ${Math.round(progress * 100)}%`, 26, 85);
  ctx.restore();
}

function roundedRectPath(ctx, x, y, w, h, r) {
  if (typeof ctx.roundRect === "function") {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    ctx.fill();
    ctx.stroke();
    return;
  }
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + w - radius, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
  ctx.lineTo(x + w, y + h - radius);
  ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
  ctx.lineTo(x + radius, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}

/** Draw a small robot/vehicle icon at center */
function drawRvizRobot(ctx, cx, cy) {
  ctx.save();
  ctx.fillStyle = "rgba(97,255,122,0.14)";
  ctx.beginPath();
  ctx.arc(cx, cy, 15, 0, 2 * Math.PI);
  ctx.fill();
  ctx.fillStyle = "#1c261f";
  ctx.strokeStyle = "#74ff82";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, 7, 0, 2 * Math.PI);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "#74ff82";
  ctx.beginPath();
  ctx.moveTo(cx, cy - 13);
  ctx.lineTo(cx - 5, cy - 4);
  ctx.lineTo(cx + 5, cy - 4);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function renderSensorsPage() {
  const robot = ensureSensorRobotSelection();
  const robots = videoRobots();
  if (!robots.length) return `<section class="panel"><div class="empty-state">暂无机器人，请先添加机器人。</div></section>`;
  const data = state.sensors.data;
  const stereo = stereoItems(data);
  const cams = cameraItems(data);
  const stereoCards = renderSensorImageCards(stereo, renderStereoEmptyState(data), "stereo");
  const cameraCards = renderSensorImageCards(cams, renderCameraEmptyState(data), "camera");
  const lidarInfo = renderLidarInfo(data);
  const hasLidar = Boolean(lidarItems(data)[0]);

  return `
    <section class="panel sensor-console">
      <div class="panel-header">
        <div>
          <p class="eyebrow">传感器数据</p>
          <h2>深度图 & 雷达扫描</h2>
          <p class="muted">实时展示设备上传的双目深度图、摄像头快照和 LiDAR 雷达扫描数据。</p>
        </div>
        <div class="button-row">
          <select id="sensor-robot">${renderControlRobotOptions(state.sensors.robotId)}</select>
          <button class="secondary-button" id="sensor-refresh" type="button"${state.sensors.loading ? " disabled" : ""}>刷新数据</button>
        </div>
      </div>
      <div id="sensor-error-slot">${state.sensors.error ? `<p class="form-error" role="alert">${escapeHtml(state.sensors.error)}</p>` : ""}</div>
      <div id="sensor-loading-slot">${state.sensors.loading && !data ? `<p class="muted">正在加载传感器数据…</p>` : ""}</div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h3>双目摄像头 / 深度图</h3>
          <p class="muted">左右两路画面，来自 stereo 类型传感器上报。</p>
        </div>
      </div>
      <div class="sensor-image-grid" id="sensor-stereo-grid" data-item-keys="${escapeHtml(stereo.map((item) => sensorItemKey(item, "stereo")).join("|"))}">${stereoCards}</div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h3>单目摄像头</h3>
          <p class="muted">来自 camera 类型传感器的快照上报。</p>
        </div>
      </div>
      <div class="sensor-image-grid" id="sensor-camera-grid" data-item-keys="${escapeHtml(cams.map((item) => sensorItemKey(item, "camera")).join("|"))}">${cameraCards}</div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h3>雷达扫描 (LiDAR)</h3>
          <p class="muted">RViz 风格 2D 极坐标可视化，距离远近以颜色渐变显示（近红远蓝），含扫描拖尾效果。</p>
        </div>
        <div class="button-row">
          <button class="secondary-button" id="lidar-copy-json" type="button"${hasLidar ? "" : " disabled"}>复制 JSON</button>
          <button class="secondary-button" id="lidar-download-json" type="button"${hasLidar ? "" : " disabled"}>下载 JSON</button>
        </div>
      </div>
      <div class="sensor-lidar-layout">
        <div class="sensor-lidar-canvas-wrap">
          <canvas id="lidar-canvas" width="560" height="560"></canvas>
        </div>
        <div class="sensor-lidar-metrics" id="sensor-lidar-metrics">${lidarInfo}</div>
      </div>
    </section>
  `;
}

function bindSensorsPage() {
  if (state.pageId !== "sensors") return;
  document.getElementById("sensor-robot")?.addEventListener("change", (e) => {
    state.sensors.robotId = e.target.value || "";
    state.sensors.data = null;
    state.sensors.lidarTrail = [];
    state.sensors.lidarLastFrameKey = "";
    state.sensors.lidarSweepStartedAt = 0;
    void loadRobotSensorData(true);
  });
  document.getElementById("sensor-refresh")?.addEventListener("click", () => {
    void loadRobotSensorData(true);
  });
  document.getElementById("lidar-copy-json")?.addEventListener("click", () => {
    void copyLatestLidarJson();
  });
  document.getElementById("lidar-download-json")?.addEventListener("click", () => {
    downloadLatestLidarJson();
  });
  rememberLidarFrame(lidarItems(state.sensors.data)[0]);
  startLidarAnimation();
  // Auto load on first visit
  if (!state.sensors.data && !state.sensors.loading && !state.sensors.error) {
    void loadRobotSensorData(true);
  }
  // Auto refresh sensor frames; the canvas animation handles scan movement between uploads.
  if (!state.sensors.autoTimer) {
    state.sensors.autoTimer = window.setInterval(() => {
      if (state.pageId === "sensors" && canRefreshRealtimePage()) {
        void loadRobotSensorData(true);
      }
    }, LIDAR_REFRESH_MS);
  }
  updateLidarActionButtons();
}

/* ─── 车载地图页 ──────────────────────────────────────────── */

function ensureRobotMapSelection() {
  const maps = Array.isArray(state.robotMaps.items) ? state.robotMaps.items : [];
  if (!maps.length) {
    state.robotMaps.selectedId = "";
    return null;
  }
  const current = maps.find((item) => String(item.id) === String(state.robotMaps.selectedId));
  const next = current || maps[0];
  state.robotMaps.selectedId = String(next.id);
  return next;
}

// ===== Robot map loading and rendering =====
async function loadRobotMaps(force = false) {
  if (state.robotMaps.loading) return;
  if (!force && state.robotMaps.items.length) return;
  state.robotMaps.loading = true;
  state.robotMaps.error = "";
  if (state.pageId === "maps") {
    renderCurrentPage();
  }
  try {
    const payload = await apiFetch("/api/robot-maps");
    state.robotMaps.items = Array.isArray(payload.items) ? payload.items : [];
    ensureRobotMapSelection();
  } catch (error) {
    state.robotMaps.error = error.message;
  } finally {
    state.robotMaps.loading = false;
    if (state.pageId === "maps") {
      renderCurrentPage();
    }
  }
}

async function syncRobotMaps() {
  if (state.robotMaps.loading) return;
  const selected = ensureRobotMapSelection();
  state.robotMaps.loading = true;
  state.robotMaps.error = "";
  renderCurrentPage();
  try {
    const payload = selected ? {
      id: selected.id,
      robotId: selected.robotId,
      robotName: selected.robotName,
      name: selected.name,
      sourceHost: selected.sourceHost,
      sourceYamlPath: selected.sourceYamlPath,
      sourceImagePath: selected.sourceImagePath,
    } : {};
    const result = await apiFetch("/api/robot-maps/sync", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.robotMaps.items = Array.isArray(result.items) ? result.items : [];
    if (result.synced?.id) {
      state.robotMaps.selectedId = String(result.synced.id);
    }
    ensureRobotMapSelection();
  } catch (error) {
    state.robotMaps.error = error.message;
  } finally {
    state.robotMaps.loading = false;
    if (state.pageId === "maps") {
      renderCurrentPage();
    }
  }
}

function robotMapImageUrl(map) {
  const src = String(map?.imageUrl || "");
  if (!src) return "";
  const stamp = encodeURIComponent(map?.syncedAt || map?.sourceMtime || Date.now());
  return `${src}${src.includes("?") ? "&" : "?"}t=${stamp}`;
}

function formatMeters(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)} m` : "-";
}

function formatMapOrigin(origin) {
  if (!Array.isArray(origin) || origin.length < 2) return "-";
  return origin.map((value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric.toFixed(3) : String(value ?? "-");
  }).join(", ");
}

function renderRobotMapOptions(selectedValue = "") {
  const maps = state.robotMaps.items || [];
  if (!maps.length) return `<option value="">暂无地图</option>`;
  return maps.map((item) => {
    const value = String(item.id);
    const selected = value === String(selectedValue) ? " selected" : "";
    const robotName = item.robotName ? ` · ${item.robotName}` : "";
    return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(item.name || value)}${escapeHtml(robotName)}</option>`;
  }).join("");
}

function renderRobotMapMeta(map) {
  const sizeMeters = map?.sizeMeters || {};
  const widthMeters = formatMeters(sizeMeters.width);
  const heightMeters = formatMeters(sizeMeters.height);
  return `
    <aside class="robot-map-meta">
      <h3>${escapeHtml(map?.name || "未命名地图")}</h3>
      <p class="muted">${escapeHtml(map?.robotName || "未知机器人")} · ${escapeHtml(map?.sourceHost || "未知主机")}</p>
      <div class="control-target-grid">
        <span>像素尺寸 <strong>${escapeHtml(map?.width ?? "-")} × ${escapeHtml(map?.height ?? "-")}</strong></span>
        <span>物理尺寸 <strong>${escapeHtml(widthMeters)} × ${escapeHtml(heightMeters)}</strong></span>
        <span>分辨率 <strong>${escapeHtml(map?.resolution ?? "-")} m/px</strong></span>
        <span>地图原点 <strong>${escapeHtml(formatMapOrigin(map?.origin))}</strong></span>
        <span>占用阈值 <strong>${escapeHtml(map?.occupiedThresh ?? "-")}</strong></span>
        <span>空闲阈值 <strong>${escapeHtml(map?.freeThresh ?? "-")}</strong></span>
        <span>车端更新时间 <strong>${escapeHtml(formatDateTime(map?.sourceMtime))}</strong></span>
        <span>同步时间 <strong>${escapeHtml(formatDateTime(map?.syncedAt))}</strong></span>
      </div>
      <div class="robot-map-paths">
        <span>源 YAML</span>
        <code>${escapeHtml(map?.sourceYamlPath || "-")}</code>
        <span>源 PGM</span>
        <code>${escapeHtml(map?.sourceImagePath || "-")}</code>
      </div>
    </aside>
  `;
}

function renderRobotMapsPage() {
  const map = ensureRobotMapSelection();
  const maps = state.robotMaps.items || [];
  const zoom = Number.isFinite(Number(state.robotMaps.zoom)) ? Number(state.robotMaps.zoom) : 1;
  const zoomPercent = Math.round(zoom * 100);
  const imageUrl = robotMapImageUrl(map);

  return `
    <section class="panel robot-map-console">
      <div class="panel-header">
        <div>
          <p class="eyebrow">SLAM 地图</p>
          <h2>车载地图展示</h2>
          <p class="muted">展示无人车本地保存的占据栅格地图。</p>
        </div>
        <div class="button-row">
          <select id="robot-map-select">${renderRobotMapOptions(state.robotMaps.selectedId)}</select>
          <button class="secondary-button" id="robot-map-refresh" type="button"${state.robotMaps.loading ? " disabled" : ""}>${state.robotMaps.loading ? "同步中…" : "同步车端地图"}</button>
        </div>
      </div>
      ${state.robotMaps.error ? `<p class="form-error" role="alert">${escapeHtml(state.robotMaps.error)}</p>` : ""}
      ${state.robotMaps.loading && !maps.length ? `<div class="empty-state">正在读取地图…</div>` : ""}
      ${!state.robotMaps.loading && !maps.length ? `<div class="empty-state">暂无可展示地图，请先同步无人车上的 SLAM 地图。</div>` : ""}
    </section>

    ${map ? `
      <section class="panel robot-map-panel">
        <div class="panel-header">
          <div>
            <h3>${escapeHtml(map.name || "地图")}</h3>
            <p class="muted">${escapeHtml(map.robotName || "无人车")} · ${escapeHtml(map.sourceHost || "-")}</p>
          </div>
          <div class="button-row robot-map-tools">
            <button class="secondary-button" type="button" data-map-zoom="fit">适配</button>
            <button class="secondary-button" type="button" data-map-zoom="out">缩小</button>
            <span class="meta-pill">${escapeHtml(zoomPercent)}%</span>
            <button class="secondary-button" type="button" data-map-zoom="in">放大</button>
            ${map.yamlUrl ? `<a class="secondary-button" href="${escapeHtml(map.yamlUrl)}" target="_blank" rel="noreferrer">YAML</a>` : ""}
            ${map.pgmUrl ? `<a class="secondary-button" href="${escapeHtml(map.pgmUrl)}" target="_blank" rel="noreferrer">PGM</a>` : ""}
          </div>
        </div>
        <div class="robot-map-layout">
          <div class="robot-map-viewport" id="robot-map-viewport">
            ${imageUrl ? `<img class="robot-map-image" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(map.name || "SLAM 地图")}" style="width:${escapeHtml(zoomPercent)}%;">` : `<div class="empty-state">地图预览文件不存在。</div>`}
          </div>
          ${renderRobotMapMeta(map)}
        </div>
      </section>
    ` : ""}
  `;
}

function bindRobotMapsPage() {
  if (state.pageId !== "maps") return;
  document.getElementById("robot-map-select")?.addEventListener("change", (event) => {
    state.robotMaps.selectedId = event.target.value || "";
    state.robotMaps.zoom = 1;
    renderCurrentPage();
  });
  document.getElementById("robot-map-refresh")?.addEventListener("click", () => {
    void syncRobotMaps();
  });
  document.querySelectorAll("[data-map-zoom]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.mapZoom;
      const current = Number.isFinite(Number(state.robotMaps.zoom)) ? Number(state.robotMaps.zoom) : 1;
      if (action === "fit") {
        state.robotMaps.zoom = 1;
      } else if (action === "in") {
        state.robotMaps.zoom = Math.min(4, current + 0.25);
      } else if (action === "out") {
        state.robotMaps.zoom = Math.max(0.25, current - 0.25);
      }
      renderCurrentPage();
    });
  });
  if (!state.robotMaps.items.length && !state.robotMaps.loading && !state.robotMaps.error) {
    void loadRobotMaps(true);
  }
}

// ===== Remote control page =====
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
  const ack = state.control.lastAck || {};
  const connectionTone = pillClass(state.control.connection === "ready" ? "online" : state.control.connection === "error" ? "offline" : "warning");
  const activeLabel = controlDirectionLabel(state.control.linear, state.control.angular);
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
      <div class="control-status-strip">
        <span>控制链路 <strong class="${connectionTone}">${escapeHtml(controlConnectionText())}</strong></span>
        <span>当前方向 <strong>${escapeHtml(activeLabel)}</strong></span>
        <span>线速度 <strong>${escapeHtml(state.control.linear.toFixed(3))} m/s</strong></span>
        <span>角速度 <strong>${escapeHtml(state.control.angular.toFixed(3))} rad/s</strong></span>
        <span>底盘订阅 <strong>${escapeHtml(ack.cmdVelSubscribers ?? "-")}</strong></span>
      </div>
      <div class="control-layout">
        <div class="control-pad" aria-label="无人车方向控制">
          <button class="control-button diagonal" type="button" data-control-button="forward-left" data-control-linear="1" data-control-angular="1"${disabled}>↖</button>
          <button class="control-button" type="button" data-control-button="forward" data-control-linear="1" data-control-angular="0"${disabled}>前进</button>
          <button class="control-button diagonal" type="button" data-control-button="forward-right" data-control-linear="1" data-control-angular="-1"${disabled}>↗</button>
          <button class="control-button" type="button" data-control-button="left" data-control-linear="0" data-control-angular="1"${disabled}>左转</button>
          <button class="control-button stop critical-action" type="button" data-control-stop${disabled}>停止</button>
          <button class="control-button" type="button" data-control-button="right" data-control-linear="0" data-control-angular="-1"${disabled}>右转</button>
          <button class="control-button diagonal" type="button" data-control-button="back-left" data-control-linear="-1" data-control-angular="-1"${disabled}>↙</button>
          <button class="control-button" type="button" data-control-button="back" data-control-linear="-1" data-control-angular="0"${disabled}>后退</button>
          <button class="control-button diagonal" type="button" data-control-button="back-right" data-control-linear="-1" data-control-angular="1"${disabled}>↘</button>
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
              <span>ROS <strong id="control-ros-slot">${escapeHtml(ack.rosOk === undefined ? "-" : ack.rosOk ? "正常" : "异常")}</strong></span>
              <span>车端速度 <strong id="control-ack-velocity">${escapeHtml(formatControlAckVelocity(ack))}</strong></span>
            </div>
          </div>
          <label><span>线速度倍率</span><input id="control-linear-scale" type="range" min="10" max="100" value="75"></label>
          <label><span>角速度倍率</span><input id="control-angular-scale" type="range" min="10" max="100" value="45"></label>
          <div class="control-key-grid" aria-label="键盘控制">
            <span><strong>W/↑</strong> 前进</span>
            <span><strong>S/↓</strong> 后退</span>
            <span><strong>A/←</strong> 左转</span>
            <span><strong>D/→</strong> 右转</span>
            <span><strong>Q/E</strong> 前斜向</span>
            <span><strong>Z/C</strong> 后斜向</span>
            <span><strong>Space</strong> 急停</span>
          </div>
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

function controlConnectionText() {
  if (state.control.connection === "ready") return "已连接";
  if (state.control.connection === "moving") return "运动中";
  if (state.control.connection === "stopped") return "已停车";
  if (state.control.connection === "error") return "异常";
  return "未检测";
}

function controlDirectionLabel(linear, angular) {
  const v = Number(linear || 0);
  const w = Number(angular || 0);
  if (Math.abs(v) < 0.001 && Math.abs(w) < 0.001) return "停止";
  if (v > 0 && w > 0) return "前进左转";
  if (v > 0 && w < 0) return "前进右转";
  if (v < 0 && w < 0) return "后退左转";
  if (v < 0 && w > 0) return "后退右转";
  if (v > 0) return "前进";
  if (v < 0) return "后退";
  return w > 0 ? "左转" : "右转";
}

function formatControlAckVelocity(ack) {
  if (!ack || (ack.v === undefined && ack.w === undefined)) return "-";
  const v = Number(ack.v || 0);
  const w = Number(ack.w || 0);
  return `${v.toFixed(3)} / ${w.toFixed(3)}`;
}

// ===== Autopilot page =====
function autopilotRobots() {
  return controlRobots();
}

function findAutopilotRobot(robotId) {
  return autopilotRobots().find((robot) => String(robot.id) === String(robotId)) || null;
}

function resolveAutopilotRobot() {
  const robots = autopilotRobots();
  if (!robots.length) {
    state.autopilot.robotId = "";
    return null;
  }
  const current = findAutopilotRobot(state.autopilot.robotId);
  if (current) return current;
  const statusRobotId = state.autopilot.status?.robotId;
  const fromStatus = statusRobotId ? findAutopilotRobot(statusRobotId) : null;
  const next = fromStatus || robots.find(robotIsOnline) || robots[0];
  state.autopilot.robotId = String(next.id);
  return next;
}

function selectedAutopilotRobotId() {
  return String(document.getElementById("autopilot-robot")?.value || state.autopilot.robotId || "").trim();
}

function autopilotModeText(mode) {
  const key = String(mode || "").trim();
  return AUTOPILOT_MODE_TEXT[key] || key || "-";
}

function autopilotReasonText(reason, status = null) {
  const key = String(reason || "").trim();
  if (key === "front_slow" && status?.lidar?.frontMin !== undefined && status?.lidar?.frontMin !== null) {
    return `前方 ${Number(status.lidar.frontMin).toFixed(2)}m 有障碍物，自动减速`;
  }
  if (key === "front_blocked" && status?.lidar?.frontMin !== undefined && status?.lidar?.frontMin !== null) {
    return `前方 ${Number(status.lidar.frontMin).toFixed(2)}m 障碍物过近，停车`;
  }
  return AUTOPILOT_REASON_TEXT[key] || key || "-";
}

function autopilotStatusTone(status) {
  if (status?.estop || status?.mode === "estop") return pillClass("danger");
  if (status?.mode === "fault" || status?.safe === false) return pillClass("warning");
  if (status?.mode === "auto_running") return pillClass("online");
  return pillClass("neutral");
}

function formatNullableDistance(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)} m` : "-";
}

function formatNullableSeconds(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)} s` : "-";
}

function autopilotActionDisabled(action, selectedRobot, status) {
  const noTarget = !selectedRobot && !String(appConfig.robotControl?.host || "").trim();
  const offline = selectedRobot && robotIsOffline(selectedRobot);
  if (state.autopilot.actionInFlight) return " disabled";
  if (noTarget) return " disabled";
  if (offline && action !== "status") return " disabled";
  if (status?.estop || status?.mode === "estop") {
    return action === "clear-estop" ? "" : " disabled";
  }
  if (action === "clear-estop") return " disabled";
  if (action === "pause" && status?.mode !== "auto_running") return " disabled";
  if (action === "resume" && !["paused", "auto_ready", "fault"].includes(String(status?.mode || ""))) return " disabled";
  return "";
}

function renderAutopilotPage() {
  const selectedRobot = resolveAutopilotRobot();
  const status = state.autopilot.status || {};
  const lidar = status.lidar || {};
  const modeTone = autopilotStatusTone(status);
  const selectableRobots = autopilotRobots();
  const targetName = selectedRobot ? selectedRobot.model : "未选择机器人";
  const targetHost = selectedRobot?.ipAddress || appConfig.robotControl?.host || "未配置";
  const targetNetwork = selectedRobot ? localizeToken(selectedRobot.networkStatus || selectedRobot.telemetryStatus || "offline") : "无可控车辆";
  const events = Array.isArray(status.events) ? status.events : [];
  const error = state.autopilot.error ? `<p class="form-error" role="alert">${escapeHtml(state.autopilot.error)}</p>` : "";
  const actionButton = (action, label, className = "secondary-button") => (
    `<button class="${className}" type="button" data-autopilot-action="${escapeHtml(action)}"${autopilotActionDisabled(action, selectedRobot, status)}>${escapeHtml(label)}</button>`
  );

  return `
    <section class="panel autopilot-console">
      <div class="panel-header">
        <div>
          <p class="eyebrow">Autopilot MVP</p>
          <h2>自动驾驶安全面板</h2>
          <p class="muted">控制优先级：急停 > 人工接管 > 安全监督器 > 自动驾驶 > 普通远程控制。</p>
        </div>
        <div class="button-row">
          <select id="autopilot-robot"${selectableRobots.length ? "" : " disabled"}>
            ${renderControlRobotOptions(state.autopilot.robotId)}
          </select>
          <button class="secondary-button" id="autopilot-refresh" type="button"${state.autopilot.loading ? " disabled" : ""}>刷新</button>
          ${actionButton("estop", "急停", "danger-button critical-action")}
        </div>
      </div>
      ${error}
      <div class="autopilot-banner">
        <span class="${modeTone}">${escapeHtml(autopilotModeText(status.mode))}</span>
        <strong>${escapeHtml(autopilotReasonText(status.reason, status))}</strong>
        <span class="muted">${escapeHtml(targetName)} · ${escapeHtml(targetHost)} · ${escapeHtml(targetNetwork)}</span>
      </div>
      <div class="control-status-strip autopilot-status-grid">
        <span>安全状态 <strong>${status.safe === false ? "不安全" : "安全"}</strong></span>
        <span>线速度 <strong>${escapeHtml(formatNullableDistance(status.linearX).replace(" m", " m/s"))}</strong></span>
        <span>角速度 <strong>${Number.isFinite(Number(status.angularZ)) ? `${Number(status.angularZ).toFixed(3)} rad/s` : "-"}</strong></span>
        <span>人工接管 <strong>${status.manualOverride ? "是" : "否"}</strong></span>
        <span>急停 <strong>${status.estop ? "已触发" : "未触发"}</strong></span>
        <span>更新时间 <strong>${escapeHtml(formatDateTime(status.updatedAt))}</strong></span>
      </div>
      <div class="button-row autopilot-actions">
        ${actionButton("start", "启动自动驾驶", "primary-button")}
        ${actionButton("pause", "暂停")}
        ${actionButton("resume", "继续")}
        ${actionButton("stop", "停止")}
        ${actionButton("clear-estop", "解除急停")}
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h3>LiDAR 避障状态</h3>
          <p class="muted">来自车端自动驾驶节点的最新避障决策。</p>
        </div>
      </div>
      <div class="control-status-strip autopilot-lidar-grid">
        <span>在线 <strong>${lidar.online ? "在线" : "离线"}</strong></span>
        <span>数据年龄 <strong>${escapeHtml(formatNullableSeconds(lidar.ageSeconds))}</strong></span>
        <span>正前最近 <strong>${escapeHtml(formatNullableDistance(lidar.frontMin))}</strong></span>
        <span>左前最近 <strong>${escapeHtml(formatNullableDistance(lidar.leftFrontMin))}</strong></span>
        <span>右前最近 <strong>${escapeHtml(formatNullableDistance(lidar.rightFrontMin))}</strong></span>
        <span>障碍状态 <strong>${escapeHtml(autopilotReasonText(lidar.obstacleStatus || status.reason, status))}</strong></span>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h3>最近事件</h3>
          <p class="muted">最近 20 条自动驾驶状态与安全事件。</p>
        </div>
      </div>
      ${events.length ? `
        <div class="table-wrap">
          <table>
            <thead><tr><th>时间</th><th>等级</th><th>类型</th><th>消息</th></tr></thead>
            <tbody>
              ${events.map((event) => `
                <tr>
                  <td>${escapeHtml(formatDateTime(event.createdAt))}</td>
                  <td><span class="${pillClass(event.level || "info")}">${escapeHtml(localizeToken(event.level || "info"))}</span></td>
                  <td>${escapeHtml(event.eventType || "-")}</td>
                  <td>${escapeHtml(event.message || "-")}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `<div class="empty-state">暂无自动驾驶事件。</div>`}
    </section>
  `;
}

async function loadAutopilotStatus(force = false) {
  if (state.autopilot.loading && !force) return;
  state.autopilot.loading = true;
  state.autopilot.error = "";
  try {
    const payload = await apiFetch("/api/autopilot/status?limit=20");
    state.autopilot.status = payload;
  } catch (error) {
    state.autopilot.error = error.message;
  } finally {
    state.autopilot.loading = false;
    if (state.pageId === "autopilot") {
      renderCurrentPage();
    }
  }
}

async function sendAutopilotAction(action) {
  if (state.autopilot.actionInFlight) return;
  state.autopilot.actionInFlight = action;
  state.autopilot.error = "";
  renderCurrentPage();
  try {
    const robotId = selectedAutopilotRobotId();
    const payload = await apiFetch(`/api/autopilot/${action}`, {
      method: "POST",
      body: JSON.stringify(robotId ? { robotId } : {}),
    });
    state.autopilot.status = payload;
  } catch (error) {
    state.autopilot.error = error.message;
  } finally {
    state.autopilot.actionInFlight = "";
    if (state.pageId === "autopilot") {
      renderCurrentPage();
    }
  }
}

function bindAutopilotPage() {
  if (state.pageId !== "autopilot") return;
  document.getElementById("autopilot-robot")?.addEventListener("change", (event) => {
    state.autopilot.robotId = event.target.value || "";
    renderCurrentPage();
  });
  document.getElementById("autopilot-refresh")?.addEventListener("click", () => {
    void loadAutopilotStatus(true);
  });
  document.querySelectorAll("[data-autopilot-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!button.disabled) void sendAutopilotAction(button.dataset.autopilotAction);
    });
  });
  if (!state.autopilot.status && !state.autopilot.loading) {
    void loadAutopilotStatus(true);
  }
  if (!state.autopilot.timer) {
    state.autopilot.timer = window.setInterval(() => {
      if (state.pageId === "autopilot" && canRefreshRealtimePage()) {
        void loadAutopilotStatus(true);
      }
    }, AUTOPILOT_REFRESH_MS);
  }
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

async function fetchDeviceOptions() {
  return fetchAllPagedItems("/api/devices");
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

  if (pageId === "devices") {
    const devices = await fetchPagedResource("devices", "/api/devices");
    state.pageData.devices = { ...devices };
  } else if (pageId === "device_management") {
    const [categories, devices, units, channels, robots, categoryOptions, deviceOptions] = await Promise.all([
      fetchPagedResource("deviceCategories", "/api/device-categories", filterParams("deviceCategories")),
      fetchPagedResource("devices", "/api/devices", filterParams("managedDevices")),
      fetchPagedResource("onboardUnits", "/api/onboard-units", filterParams("onboardUnits")),
      fetchPagedResource("networkChannels", "/api/network-channels", filterParams("networkChannels")),
      Promise.resolve(videoRobots()),
      fetchAllPagedItems("/api/device-categories"),
      fetchDeviceOptions(),
    ]);
    state.pageData.device_management = { categories, devices, units, channels, robots, categoryOptions, deviceOptions };
  }

  if (state.pageId === pageId) {
    syncCurrentPageUrl();
    renderCurrentPage();
  }
  return state.pageData[pageId];
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
      <td><span class="${pillClass(device.status)}">${escapeHtml(localizeToken(device.status))}</span></td>
      <td>${device.imagePath ? `<img class="device-thumb" src="${escapeHtml(device.imagePath)}" alt="${escapeHtml(device.name)}" loading="lazy">` : "-"}</td>
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
            <p class="muted">登记平台设备信息。</p>
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
          </div>
          <label><span>备注</span><textarea name="notes" placeholder="可选设备备注"></textarea></label>
          <div class="device-upload-grid">
            <label>
              <span>设备图片</span>
              <input id="device-image-input" type="file" accept="image/*" />
            </label>
            <div class="image-preview-card">
              <div class="image-preview-shell">
                ${previewUrl ? `<img src="${escapeHtml(previewUrl)}" alt="设备预览" style="aspect-ratio: 2 / 1; width: 100%; height: auto;">` : `<span class="muted">选择图片后在这里预览</span>`}
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
            <p class="muted">支持按名称、型号和状态筛选。</p>
          </div>
          <div class="panel-actions toolbar-filters">
            <input id="device-search" type="search" value="${escapeHtml(state.deviceFilters.keyword)}" placeholder="搜索名称 / 型号 / 备注" autocomplete="off" />
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
        ${renderTable("devices", ["名称", "型号", "状态", "图片", "操作"], rows)}
        ${renderPagination("devices", devicesData, "台设备")}
      </article>
    </section>
  `;
}

function bindDevicesPage() {
  if (!state.pageData.devices) {
    void ensureManagementPageData("devices");
    return;
  }
  bindPagination("devices");
  bindManagedForm("device-form", "device", async (form) => {
    const payload = formToObject(form);
    const created = await apiFetch("/api/devices", { method: "POST", body: JSON.stringify(payload) });
    if (state.deviceImageDraft.file && created.deviceId) {
      const formData = new FormData();
      formData.append("file", state.deviceImageDraft.file);
      await apiUpload(`/api/devices/${created.deviceId}/image`, formData);
    }
    form.reset();
    clearDeviceImageDraft();
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
          }, ["categoryId", "robotId"]);
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

function renderLocalAdminPlaceholderPage(kind) {
  const copy = {
    users: {
      title: "用户管理",
      description: "本地管理员账号入口已接入，完整账号增删改能力通过后端 API 保留。",
      primary: "默认管理员",
      secondary: appConfig.currentUser?.username || "admin",
    },
    clusters: {
      title: "集群管理",
      description: "集群导航入口已接入，当前仅用于本地验收和后续节点管理扩展。",
      primary: "节点保护",
      secondary: "删除/迁移已有后端约束",
    },
    formations: {
      title: "编队管理",
      description: "编队导航入口已接入，当前仅用于本地验收和后续队形方案扩展。",
      primary: "编队保护",
      secondary: "成员归属已有后端约束",
    },
  }[kind];
  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>${escapeHtml(copy.title)}</h2>
          <p class="muted">${escapeHtml(copy.description)}</p>
        </div>
      </div>
      <div class="metrics-grid">
        <div class="metric-card"><strong>${escapeHtml(copy.primary)}</strong><span>入口状态</span></div>
        <div class="metric-card"><strong>${escapeHtml(copy.secondary)}</strong><span>本地验收</span></div>
      </div>
    </section>
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

// ===== Page orchestration =====
function renderCurrentPage() {
  if (state.pageId !== "video") {
    clearVideoSnapshotTimer();
  }
  if (state.pageId !== "sensors" && state.sensors.autoTimer) {
    window.clearInterval(state.sensors.autoTimer);
    state.sensors.autoTimer = null;
  }
  if (state.pageId !== "sensors") {
    stopLidarAnimation();
  }
  if (state.pageId !== "control" && state.control.activeTimer) {
    void sendControlStop();
  }
  if (state.pageId !== "autopilot" && state.autopilot.timer) {
    window.clearInterval(state.autopilot.timer);
    state.autopilot.timer = null;
  }
  const renderers = {
    overview: renderOverviewPage,
    status: renderStatusPage,
    video: renderVideoPage,
    perception: renderPerceptionPage,
    sensors: renderSensorsPage,
    maps: renderRobotMapsPage,
    control: renderControlPage,
    autopilot: renderAutopilotPage,
    device_management: renderDeviceManagementPage,
    users: () => renderLocalAdminPlaceholderPage("users"),
    clusters: () => renderLocalAdminPlaceholderPage("clusters"),
    formations: () => renderLocalAdminPlaceholderPage("formations"),
    devices: renderDevicesPage,
  };
  const renderer = renderers[state.pageId];
  pageContent.innerHTML = renderer ? renderer() : `<section class="panel"><div class="empty-state">页面不存在。</div></section>`;
  bindForms();
  renderMaps();
}

// ===== Form binding and page events =====
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
      probeVideoSnapshot(image, `${base}?t=${state.video.snapshotTick}`, true);
    }
  });
  document.querySelectorAll("[data-main-snapshot]").forEach((image) => {
    const base = image.dataset.mainSnapshotBase || "";
    if (base) {
      probeVideoSnapshot(image, `${base}?t=${state.video.snapshotTick}`, true);
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
  bindVideoImageStatus();
  refreshVideoSnapshots();
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
  state.control.activeButton = "";
  state.control.activeKey = "";
  state.control.commandInFlight = false;
  document.querySelectorAll(".control-button.active").forEach((button) => button.classList.remove("active"));
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
  const payload = await apiFetch("/api/robot-control/cmd_vel", {
    method: "POST",
    body: JSON.stringify(controlRequestBody({ linear, angular }, robotId)),
  });
  state.control.connection = "moving";
  state.control.linear = Number(linear || 0);
  state.control.angular = Number(angular || 0);
  state.control.lastAck = payload.response || null;
  state.control.lastSentAt = new Date().toISOString();
  setControlStatus(`已发送：线速度 ${linear}，角速度 ${angular}`);
  updateControlRuntimeDom();
}

async function sendControlStop(robotId = state.control.activeRobotId || selectedControlRobotId()) {
  clearControlTimer();
  if (!String(robotId || "").trim()) return;
  setFormError("control");
  const payload = await apiFetch("/api/robot-control/stop", {
    method: "POST",
    body: JSON.stringify(controlRequestBody({}, robotId)),
  });
  state.control.connection = "stopped";
  state.control.linear = 0;
  state.control.angular = 0;
  state.control.lastAck = payload.response || null;
  state.control.lastSentAt = new Date().toISOString();
  setControlStatus("已发送停车指令。");
  updateControlRuntimeDom();
}

function startControlHold(button) {
  const robotId = selectedControlRobotId();
  const linear = () => controlValue("linear", button.dataset.controlLinear);
  const angular = () => controlValue("angular", button.dataset.controlAngular);
  clearControlTimer();
  state.control.activeRobotId = robotId;
  state.control.activeButton = button.dataset.controlButton || "";
  button.classList.add("active");
  const tick = async () => {
    if (state.control.commandInFlight) return;
    state.control.commandInFlight = true;
    try {
      await sendControlCommand(linear(), angular(), robotId);
    } catch (error) {
      clearControlTimer();
      state.control.connection = "error";
      state.control.linear = 0;
      state.control.angular = 0;
      setFormError("control", error.message);
      updateControlRuntimeDom();
    } finally {
      state.control.commandInFlight = false;
    }
  };
  void tick();
  state.control.activeTimer = window.setInterval(tick, CONTROL_HOLD_INTERVAL_MS);
}

function updateControlRuntimeDom() {
  if (state.pageId !== "control") return;
  const statusStrip = document.querySelector(".control-status-strip");
  const ack = state.control.lastAck || {};
  if (statusStrip) {
    statusStrip.innerHTML = `
      <span>控制链路 <strong class="${pillClass(state.control.connection === "ready" ? "online" : state.control.connection === "error" ? "offline" : "warning")}">${escapeHtml(controlConnectionText())}</strong></span>
      <span>当前方向 <strong>${escapeHtml(controlDirectionLabel(state.control.linear, state.control.angular))}</strong></span>
      <span>线速度 <strong>${escapeHtml(state.control.linear.toFixed(3))} m/s</strong></span>
      <span>角速度 <strong>${escapeHtml(state.control.angular.toFixed(3))} rad/s</strong></span>
      <span>底盘订阅 <strong>${escapeHtml(ack.cmdVelSubscribers ?? "-")}</strong></span>
    `;
  }
  replaceHtmlIfChanged(document.getElementById("control-ros-slot"), escapeHtml(ack.rosOk === undefined ? "-" : ack.rosOk ? "正常" : "异常"));
  replaceHtmlIfChanged(document.getElementById("control-ack-velocity"), escapeHtml(formatControlAckVelocity(ack)));
}

function controlButtonForVector(vector) {
  return Array.from(document.querySelectorAll("[data-control-linear]")).find((button) => (
    Number(button.dataset.controlLinear) === Number(vector.linear) &&
    Number(button.dataset.controlAngular) === Number(vector.angular)
  )) || null;
}

function keyboardEventIsEditable(event) {
  const target = event.target;
  return Boolean(target && target.closest && target.closest("input, textarea, select, [contenteditable='true']"));
}

function handleControlKeyDown(event) {
  if (state.pageId !== "control" || keyboardEventIsEditable(event)) return;
  if (event.code === "Space") {
    event.preventDefault();
    void sendControlStop();
    return;
  }
  const vector = CONTROL_KEY_BINDINGS[event.code];
  if (!vector || state.control.activeKey === event.code || event.repeat) return;
  const button = controlButtonForVector(vector);
  if (!button || button.disabled) return;
  event.preventDefault();
  state.control.activeKey = event.code;
  startControlHold(button);
}

function handleControlKeyUp(event) {
  if (state.pageId !== "control") return;
  if (event.code && event.code === state.control.activeKey) {
    event.preventDefault();
    void sendControlStop();
  }
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
      const payload = await apiFetch(`/api/robot-control/status?${query}`);
      state.control.connection = "ready";
      state.control.lastAck = payload.response || null;
      state.control.linear = Number(payload.response?.v || 0);
      state.control.angular = Number(payload.response?.w || 0);
      setControlStatus("控制服务连接正常。");
      updateControlRuntimeDom();
    } catch (error) {
      state.control.connection = "error";
      setFormError("control", error.message);
      updateControlRuntimeDom();
    }
  });
  document.querySelectorAll("[data-control-linear]").forEach((button) => {
    button.addEventListener("pointerdown", (event) => {
      if (button.disabled) return;
      event.preventDefault();
      button.setPointerCapture?.(event.pointerId);
      startControlHold(button);
    });
    button.addEventListener("pointerup", (event) => {
      button.releasePointerCapture?.(event.pointerId);
      if (state.control.activeButton === (button.dataset.controlButton || "")) void sendControlStop();
    });
    button.addEventListener("pointercancel", (event) => {
      button.releasePointerCapture?.(event.pointerId);
      if (state.control.activeButton === (button.dataset.controlButton || "")) void sendControlStop();
    });
    button.addEventListener("lostpointercapture", () => {
      if (state.control.activeButton === (button.dataset.controlButton || "")) void sendControlStop();
    });
    button.addEventListener("contextmenu", (event) => {
      event.preventDefault();
    });
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
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch("/api/devices", { method: "POST", body: JSON.stringify(numericPayload(payload, ["categoryId", "robotId"])) });
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
      { name: "notes", label: "备注", type: "textarea" },
    ],
    onSubmit: async (payload) => {
      await apiFetch(`/api/devices/${item.id}`, { method: "PUT", body: JSON.stringify(numericPayload(payload, ["categoryId", "robotId"])) });
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
    const payload = numericPayload(formToObject(form), ["categoryId", "robotId"]);
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

function bindForms() {
  handleCreate("robot", "/api/robots", (payload) => numericPayload(payload, ["health", "battery", "speed", "signal", "latency", "lng", "lat", "heading"]));
  handleCreate("alert", "/api/alerts");
  bindRobotDiscoveryTools();
  bindDeleteButtons();
  if (state.pageId === "devices") bindDevicesPage();
  if (state.pageId === "video") bindVideoPage();
  if (state.pageId === "perception") bindPerceptionPage();
  if (state.pageId === "sensors") bindSensorsPage();
  if (state.pageId === "maps") bindRobotMapsPage();
  if (state.pageId === "control") bindControlPage();
  if (state.pageId === "autopilot") bindAutopilotPage();
  if (state.pageId === "device_management") bindDeviceManagementPage();
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
  const mapIds = ["overview-map"].filter((id) => document.getElementById(id));
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
    state.maps[id] = { map, userMarker: null, robotMarkers: {} };
    map.addControl(new AMap.Scale());
    map.addControl(new AMap.ToolBar());
    syncRobotMarkersInEntry(state.maps[id]);
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
  });
}

function canRefreshRealtimePage() {
  if (document.hidden) return false;
  const active = document.activeElement;
  return !(active && (active.closest("form") || active.closest("dialog")));
}

function handleVisibilityChange() {
  if (document.hidden) {
    stopLidarAnimation();
    return;
  }
  if (state.pageId === "sensors") {
    rememberLidarFrame(lidarItems(state.sensors.data)[0]);
    startLidarAnimation();
    void loadRobotSensorData(true);
  }
  if (state.pageId === "autopilot") {
    void loadAutopilotStatus(true);
  }
}

// ===== Realtime and bootstrap =====
function handleDashboardSocketMessage(message) {
  if (!message || message.type !== "dashboard_update" || !message.data) return;
  state.data = message.data;
  renderShellMeta();
  if (state.pageId === "perception" && canRefreshRealtimePage()) {
    void loadPerceptionLatest(true);
    return;
  }
  if (state.pageId === "sensors" && canRefreshRealtimePage()) {
    void loadRobotSensorData(true);
    return;
  }
  if (state.pageId === "autopilot" && canRefreshRealtimePage()) {
    void loadAutopilotStatus(true);
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
  dashboardRealtime.clearTimers(state);
}

function connectDashboardSocket() {
  dashboardRealtime.connect(state, handleDashboardSocketMessage);
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
document.addEventListener("visibilitychange", handleVisibilityChange);
window.addEventListener("keydown", handleControlKeyDown);
window.addEventListener("keyup", handleControlKeyUp);

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
