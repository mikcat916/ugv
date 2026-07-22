window.Project4Simulator = (() => {
  const field = { width: 10, height: 7 };
  const storageKey = "project4-simulator-default-scene";
  const gridResolution = 0.2;
  const robotRadius = 0.35;
  const arrivalRadius = 0.25;
  const waypointRadius = 0.28;
  const reasonText = {
    front_clear: "前方安全，低速前进",
    front_slow: "前方较近，自动减速",
    front_blocked: "前方障碍物过近，停车",
    both_front_blocked: "左右前方均受阻，停车",
    avoid_left: "右前较近，向左避障",
    avoid_right: "左前较近，向右避障",
    lidar_timeout: "LiDAR 超时或离线",
    estop: "急停触发",
    autopilot_paused: "自动驾驶暂停",
    no_target: "未设置目标点",
    planning: "路径规划中",
    path_ready: "路径可用，跟踪目标点",
    path_blocked: "无法规划路径",
    target_invalid: "目标点不可达",
    target_reached: "已到达目标点",
  };
  const pathStateText = {
    no_target: "未设置",
    planning: "规划中",
    path_ready: "路径可用",
    path_blocked: "无路径",
    target_invalid: "目标不可达",
    target_reached: "已到达",
  };
  const scenarioConclusions = {
    straight: "结论：设置目标点后，小车会规划 A* 路径并由 Safety 监督最终速度。",
    corridor: "结论：狭窄通道中路径会绕开膨胀障碍物，LiDAR 仍会触发减速或避让。",
    sudden: "结论：前方突然出现障碍物后可重新规划；若 frontMin 过近，Safety 强制停车。",
    lost: "结论：LiDAR 离线或丢包造成超时后，即使路径存在也会停车。",
    estop: "结论：急停优先级最高，无论目标点和路径如何，finalCmd 必须为零。",
  };

  const params = {
    maxLinear: 0.18,
    maxAngular: 0.9,
    stopDistance: 0.5,
    slowDistance: 1.0,
    turnStrength: 0.65,
    lidarRange: 4.5,
    lidarBeams: 96,
    lidarFov: 180,
    lidarNoise: 0.01,
    lidarDropout: 0,
    lidarDelay: 0,
    controlTimeout: 0.75,
    lidarTimeout: 2,
  };
  const initialCar = { x: 1.4, y: 3.5, theta: 0 };
  const state = {
    initialized: false,
    running: false,
    autoEnabled: true,
    estop: false,
    lidarOffline: false,
    showRays: true,
    showHits: true,
    showPath: true,
    selectedId: "",
    drag: null,
    pointerIntent: null,
    lastTs: 0,
    animationId: 0,
    lastScanAt: performance.now(),
    scanQueue: [],
    events: [],
    conclusion: "点击画布空白处设置目标点。",
    car: { ...initialCar, linear: 0, angular: 0, trail: [] },
    startPose: { ...initialCar },
    target: null,
    path: [],
    waypointIndex: 0,
    pathState: "no_target",
    pathMessage: "点击画布空白处设置目标点。",
    targetDistance: null,
    headingError: null,
    nextWaypoint: null,
    failedPoint: null,
    arrivedNotified: false,
    obstacles: [],
    scan: emptyScan(),
    rawCmd: { linearX: 0, angularZ: 0 },
    finalCmd: { linearX: 0, angularZ: 0 },
    mode: "paused",
    safe: false,
    reason: "no_target",
  };

  const controls = [
    ["maxLinear", "最大线速度", 0, 0.5, 0.01, " m/s"],
    ["maxAngular", "最大角速度", 0, 1.8, 0.05, " rad/s"],
    ["stopDistance", "停车距离", 0.2, 1.2, 0.05, " m"],
    ["slowDistance", "减速距离", 0.5, 2.0, 0.05, " m"],
    ["turnStrength", "避障转向强度", 0, 1.5, 0.05, " rad/s"],
    ["lidarRange", "LiDAR 最大距离", 1, 8, 0.1, " m"],
    ["lidarBeams", "LiDAR 光束数量", 16, 240, 1, ""],
    ["lidarFov", "LiDAR 视场角", 60, 270, 5, " deg"],
    ["lidarNoise", "LiDAR 噪声", 0, 0.2, 0.005, " m"],
    ["lidarDropout", "LiDAR 丢包率", 0, 1, 0.01, ""],
    ["lidarDelay", "LiDAR 延迟", 0, 2, 0.05, " s"],
    ["controlTimeout", "控制超时", 0.2, 3, 0.05, " s"],
    ["lidarTimeout", "LiDAR 超时", 0.2, 5, 0.05, " s"],
  ];

  function emptyScan() {
    return { online: false, frontMin: null, leftFrontMin: null, rightFrontMin: null, beams: [], hits: [] };
  }

  function renderPage() {
    return `
      <section class="panel simulator-console">
        <div class="panel-header simulator-topbar">
          <div>
            <p class="eyebrow">SIMULATION MODE</p>
            <h2>目标点自动驾驶 2D 仿真</h2>
            <p class="muted">点击画布空白处设置目标点，A* 规划路径，LiDAR 与 Safety 监督最终速度。</p>
          </div>
          <div class="button-row simulator-run-actions">
            <span class="pill warning">SIMULATION MODE</span>
            <button class="primary-button" data-sim-action="start" type="button">开始仿真</button>
            <button class="secondary-button" data-sim-action="pause" type="button">暂停仿真</button>
            <button class="secondary-button" data-sim-action="step" type="button">单步运行</button>
            <button class="secondary-button" data-sim-action="reset" type="button">重置仿真</button>
          </div>
        </div>
        <div class="simulator-layout">
          <div class="simulator-canvas-wrap">
            <canvas id="simulator-canvas" width="960" height="640" aria-label="2D 自动驾驶仿真场景"></canvas>
          </div>
          <aside class="simulator-side">
            <div class="simulator-control-group simulator-target-card" id="sim-target-card"></div>
            <div class="simulator-control-group">
              <h3>运行控制</h3>
              <div class="button-row">
                <button class="secondary-button" data-sim-action="toggle-auto" type="button">开启/暂停自动驾驶</button>
                <button class="danger-button" data-sim-action="estop" type="button">急停</button>
                <button class="secondary-button" data-sim-action="clear-estop" type="button">解除急停</button>
              </div>
              <div class="button-row">
                <button class="secondary-button" data-sim-action="lidar-offline" type="button">模拟 LiDAR 离线</button>
                <button class="secondary-button" data-sim-action="lidar-online" type="button">恢复 LiDAR</button>
              </div>
            </div>
            <div class="simulator-control-group">
              <h3>目标导航</h3>
              <div class="button-row">
                <button class="secondary-button" data-sim-action="clear-target" type="button">清除目标</button>
                <button class="secondary-button" data-sim-action="replan" type="button">重新规划</button>
                <button class="secondary-button" data-sim-action="return-start" type="button">回到起点</button>
              </div>
              <p class="muted compact-copy">点击画布空白处设置单个目标点；目标在障碍物内会标记为不可达。</p>
            </div>
            <div class="simulator-control-group">
              <h3>场景编辑</h3>
              <label class="simulator-range"><span>小车朝向 <strong id="sim-heading-label">0 deg</strong></span><input id="sim-heading" type="range" min="-180" max="180" step="1" value="0"></label>
              <div class="button-row">
                <button class="secondary-button" data-sim-action="reset-car" type="button">重置小车位置</button>
                <button class="secondary-button" data-sim-action="clear-trail" type="button">清除轨迹</button>
                <button class="secondary-button" data-sim-action="add-obstacle" type="button">添加矩形障碍物</button>
                <button class="secondary-button" data-sim-action="delete-obstacle" type="button">删除障碍物</button>
                <button class="secondary-button" data-sim-action="simple-scene" type="button">简单场景</button>
                <button class="secondary-button" data-sim-action="clear-scene" type="button">清空场景</button>
                <button class="secondary-button" data-sim-action="save-default" type="button">保存默认场景</button>
                <button class="secondary-button" data-sim-action="restore-default" type="button">恢复默认场景</button>
              </div>
            </div>
            <div class="simulator-control-group">
              <h3>显示层</h3>
              <label class="simulator-check"><input id="sim-show-path" type="checkbox" checked> 显示 A* 路径</label>
              <label class="simulator-check"><input id="sim-show-rays" type="checkbox" checked> 显示 LiDAR 扫描线</label>
              <label class="simulator-check"><input id="sim-show-hits" type="checkbox" checked> 显示命中点</label>
            </div>
          </aside>
        </div>
      </section>
      <section class="panel simulator-status-panel">
        <div class="panel-header"><div><h3>自动驾驶状态</h3><p class="muted">rawCmd 由目标路径跟踪输出，finalCmd 由 Safety Supervisor 输出。</p></div></div>
        <div class="simulator-live-strip" id="sim-live-strip"></div>
        <div class="control-status-strip simulator-status-grid" id="sim-status-grid"></div>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>动态参数</h3><p class="muted">参数修改后实时生效。</p></div></div>
        <div class="simulator-param-grid">${controls.map(renderControl).join("")}</div>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>理论可行性场景</h3><p class="muted">一键切换场景并观察目标导航结论。</p></div></div>
        <div class="button-row">
          <button class="secondary-button" data-sim-scenario="straight" type="button">场景 1：直线避障</button>
          <button class="secondary-button" data-sim-scenario="corridor" type="button">场景 2：狭窄通道</button>
          <button class="secondary-button" data-sim-scenario="sudden" type="button">场景 3：前方突然出现障碍物</button>
          <button class="secondary-button" data-sim-scenario="lost" type="button">场景 4：LiDAR 丢失</button>
          <button class="secondary-button" data-sim-scenario="estop" type="button">场景 5：急停</button>
        </div>
        <div class="notice-card" id="sim-conclusion">${escape(state.conclusion)}</div>
      </section>
      <section class="panel">
        <div class="panel-header"><div><h3>最近 20 条仿真事件</h3></div></div>
        <div class="table-wrap"><table><thead><tr><th>时间</th><th>类型</th><th>内容</th></tr></thead><tbody id="sim-events"></tbody></table></div>
      </section>
    `;
  }

  function renderControl(item) {
    const [key, label, min, max, step, unit] = item;
    return `<label class="simulator-range"><span>${escape(label)} <strong id="sim-param-${key}">${format(params[key])}${unit}</strong></span><input data-sim-param="${key}" type="range" min="${min}" max="${max}" step="${step}" value="${params[key]}"></label>`;
  }

  function bindPage() {
    init();
    const canvas = document.getElementById("simulator-canvas");
    if (!canvas) return;
    state.canvas = canvas;
    state.ctx = canvas.getContext("2d");
    bindCanvas(canvas);
    document.querySelectorAll("[data-sim-action]").forEach((button) => {
      button.addEventListener("click", () => handleAction(button.dataset.simAction));
    });
    document.querySelectorAll("[data-sim-param]").forEach((input) => {
      input.addEventListener("input", () => {
        const key = input.dataset.simParam;
        params[key] = Number(input.value);
        updateParamLabels();
      });
    });
    document.querySelectorAll("[data-sim-scenario]").forEach((button) => {
      button.addEventListener("click", () => loadScenario(button.dataset.simScenario));
    });
    document.getElementById("sim-heading")?.addEventListener("input", (event) => {
      state.car.theta = degToRad(Number(event.target.value));
      updateNavigationProgress();
      updateParamLabels();
    });
    document.getElementById("sim-show-path")?.addEventListener("change", (event) => {
      state.showPath = event.target.checked;
    });
    document.getElementById("sim-show-rays")?.addEventListener("change", (event) => {
      state.showRays = event.target.checked;
    });
    document.getElementById("sim-show-hits")?.addEventListener("change", (event) => {
      state.showHits = event.target.checked;
    });
    draw();
    updatePanels();
    startLoop();
  }

  function init() {
    if (state.initialized) return;
    state.initialized = true;
    loadScenario("straight", false);
    const saved = loadSavedScene();
    if (saved) applyScene(saved);
    addEvent("system", "仿真器初始化完成，点击画布设置目标点。");
  }

  function cleanup() {
    stopLoop();
    state.canvas = null;
    state.ctx = null;
    state.drag = null;
    state.pointerIntent = null;
  }

  function startLoop() {
    stopLoop();
    state.lastTs = performance.now();
    const tick = (ts) => {
      const dt = Math.min(0.08, Math.max(0.001, (ts - state.lastTs) / 1000));
      state.lastTs = ts;
      if (state.running) update(dt, ts);
      draw();
      updatePanels();
      state.animationId = requestAnimationFrame(tick);
    };
    state.animationId = requestAnimationFrame(tick);
  }

  function stopLoop() {
    if (state.animationId) cancelAnimationFrame(state.animationId);
    state.animationId = 0;
  }

  function update(dt, now) {
    updateNavigationProgress();
    const scan = simulateLidar(now);
    const auto = window.SimAutopilot.decide(scan, params, state.autoEnabled, navContext());
    const lidarTimedOut = !scan.online || (now - state.lastScanAt) / 1000 > params.lidarTimeout;
    const safety = window.SimSafety.supervise(auto.rawCmd, scan, params, {
      estop: state.estop,
      lidarTimedOut,
      reason: auto.reason,
    });
    state.scan = scan;
    state.mode = state.estop ? "estop" : state.autoEnabled ? auto.mode : "paused";
    state.safe = safety.safe;
    state.reason = safety.reason;
    state.rawCmd = auto.rawCmd;
    state.finalCmd = safety.finalCmd;
    integrateCar(dt, safety.finalCmd);
    updateNavigationProgress();
  }

  function navContext() {
    return {
      car: state.car,
      target: state.target,
      path: state.path,
      nextWaypoint: state.nextWaypoint,
      targetDistance: state.targetDistance,
      headingError: state.headingError,
      pathState: state.pathState,
    };
  }

  function integrateCar(dt, cmd) {
    state.car.linear = Number(cmd.linearX) || 0;
    state.car.angular = Number(cmd.angularZ) || 0;
    state.car.theta = normalizeAngle(state.car.theta + state.car.angular * dt);
    state.car.x += Math.cos(state.car.theta) * state.car.linear * dt;
    state.car.y += Math.sin(state.car.theta) * state.car.linear * dt;
    state.car.x = Math.max(0.25, Math.min(field.width - 0.25, state.car.x));
    state.car.y = Math.max(0.25, Math.min(field.height - 0.25, state.car.y));
    state.car.trail.push({ x: state.car.x, y: state.car.y });
    if (state.car.trail.length > 800) state.car.trail.shift();
  }

  function simulateLidar(now) {
    if (state.lidarOffline || Math.random() < params.lidarDropout) {
      return delayedScan(now, { ...emptyScan(), online: false });
    }
    const beams = [];
    const hits = [];
    const count = Math.max(2, Math.round(params.lidarBeams));
    const halfFov = degToRad(params.lidarFov) / 2;
    for (let i = 0; i < count; i += 1) {
      const t = count === 1 ? 0.5 : i / (count - 1);
      const angle = state.car.theta - halfFov + t * halfFov * 2;
      const hit = castRay(state.car.x, state.car.y, angle, params.lidarRange);
      const noisy = Math.max(0, Math.min(params.lidarRange, hit.distance + noise(params.lidarNoise)));
      beams.push({ angle, distance: noisy, hit: hit.hit });
      if (hit.hit) hits.push({ x: state.car.x + Math.cos(angle) * noisy, y: state.car.y + Math.sin(angle) * noisy });
    }
    const scan = summarizeScan(beams);
    scan.online = true;
    scan.beams = beams;
    scan.hits = hits;
    state.lastScanAt = now;
    return delayedScan(now, scan);
  }

  function delayedScan(now, scan) {
    state.scanQueue.push({ readyAt: now + params.lidarDelay * 1000, scan });
    let ready = null;
    while (state.scanQueue.length && state.scanQueue[0].readyAt <= now) {
      ready = state.scanQueue.shift().scan;
    }
    return ready || state.scan || scan;
  }

  function summarizeScan(beams) {
    const front = [];
    const left = [];
    const right = [];
    for (const beam of beams) {
      const rel = normalizeAngle(beam.angle - state.car.theta);
      const deg = radToDeg(rel);
      if (Math.abs(deg) <= 20) front.push(beam.distance);
      if (deg > 20 && deg <= 80) left.push(beam.distance);
      if (deg < -20 && deg >= -80) right.push(beam.distance);
    }
    return {
      frontMin: minOrNull(front),
      leftFrontMin: minOrNull(left),
      rightFrontMin: minOrNull(right),
    };
  }

  function castRay(x, y, angle, maxDistance) {
    const dx = Math.cos(angle);
    const dy = Math.sin(angle);
    let best = maxDistance;
    let hit = false;
    for (const segment of sceneSegments()) {
      const rayDistance = intersectRaySegment(x, y, dx, dy, segment);
      if (rayDistance !== null && rayDistance < best) {
        best = rayDistance;
        hit = true;
      }
    }
    return { distance: best, hit };
  }

  function sceneSegments() {
    const segments = [
      [{ x: 0, y: 0 }, { x: field.width, y: 0 }],
      [{ x: field.width, y: 0 }, { x: field.width, y: field.height }],
      [{ x: field.width, y: field.height }, { x: 0, y: field.height }],
      [{ x: 0, y: field.height }, { x: 0, y: 0 }],
    ];
    for (const o of state.obstacles) {
      segments.push([{ x: o.x, y: o.y }, { x: o.x + o.w, y: o.y }]);
      segments.push([{ x: o.x + o.w, y: o.y }, { x: o.x + o.w, y: o.y + o.h }]);
      segments.push([{ x: o.x + o.w, y: o.y + o.h }, { x: o.x, y: o.y + o.h }]);
      segments.push([{ x: o.x, y: o.y + o.h }, { x: o.x, y: o.y }]);
    }
    return segments;
  }

  function intersectRaySegment(x, y, dx, dy, segment) {
    const [a, b] = segment;
    const sx = b.x - a.x;
    const sy = b.y - a.y;
    const det = cross(dx, dy, sx, sy);
    if (Math.abs(det) < 1e-8) return null;
    const qx = a.x - x;
    const qy = a.y - y;
    const t = cross(qx, qy, sx, sy) / det;
    const u = cross(qx, qy, dx, dy) / det;
    return t >= 0 && u >= 0 && u <= 1 ? t : null;
  }

  function draw() {
    const canvas = state.canvas;
    const ctx = state.ctx;
    if (!canvas || !ctx) return;
    const ratio = window.devicePixelRatio || 1;
    const box = canvas.getBoundingClientRect();
    if (box.width && box.height && (canvas.width !== Math.round(box.width * ratio) || canvas.height !== Math.round(box.height * ratio))) {
      canvas.width = Math.round(box.width * ratio);
      canvas.height = Math.round(box.height * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const width = canvas.width / ratio;
    const height = canvas.height / ratio;
    ctx.clearRect(0, 0, width, height);
    const view = viewBox(width, height);
    drawField(ctx, view);
    drawPath(ctx, view);
    drawTrail(ctx, view);
    drawObstacles(ctx, view);
    drawTarget(ctx, view);
    drawLidar(ctx, view);
    drawCar(ctx, view);
    drawHud(ctx, width, view);
  }

  function viewBox(width, height) {
    const pad = 24;
    const scale = Math.min((width - pad * 2) / field.width, (height - pad * 2) / field.height);
    return { pad, scale, ox: (width - field.width * scale) / 2, oy: (height - field.height * scale) / 2 };
  }

  function worldToCanvas(point, view) {
    return { x: view.ox + point.x * view.scale, y: view.oy + point.y * view.scale };
  }

  function canvasToWorld(event, canvas) {
    const rect = canvas.getBoundingClientRect();
    const view = viewBox(rect.width, rect.height);
    return {
      x: clamp((event.clientX - rect.left - view.ox) / view.scale, 0, field.width),
      y: clamp((event.clientY - rect.top - view.oy) / view.scale, 0, field.height),
    };
  }

  function drawField(ctx, view) {
    const a = worldToCanvas({ x: 0, y: 0 }, view);
    ctx.fillStyle = "#f8fafc";
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 2;
    ctx.fillRect(a.x, a.y, field.width * view.scale, field.height * view.scale);
    ctx.strokeRect(a.x, a.y, field.width * view.scale, field.height * view.scale);
    ctx.strokeStyle = "rgba(15,23,42,0.08)";
    ctx.lineWidth = 1;
    for (let x = 1; x < field.width; x += 1) {
      const p = worldToCanvas({ x, y: 0 }, view);
      ctx.beginPath();
      ctx.moveTo(p.x, a.y);
      ctx.lineTo(p.x, a.y + field.height * view.scale);
      ctx.stroke();
    }
    for (let y = 1; y < field.height; y += 1) {
      const p = worldToCanvas({ x: 0, y }, view);
      ctx.beginPath();
      ctx.moveTo(a.x, p.y);
      ctx.lineTo(a.x + field.width * view.scale, p.y);
      ctx.stroke();
    }
  }

  function drawPath(ctx, view) {
    if (!state.showPath) return;
    if (state.path.length > 1) {
      ctx.strokeStyle = "#2563eb";
      ctx.lineWidth = 3;
      ctx.setLineDash([8, 6]);
      ctx.beginPath();
      state.path.forEach((point, index) => {
        const p = worldToCanvas(point, view);
        if (index === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }
    if (state.nextWaypoint) {
      const p = worldToCanvas(state.nextWaypoint, view);
      ctx.fillStyle = "#f59e0b";
      ctx.strokeStyle = "#92400e";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }

  function drawTrail(ctx, view) {
    if (state.car.trail.length < 2) return;
    ctx.strokeStyle = "#0f766e";
    ctx.lineWidth = 2;
    ctx.beginPath();
    state.car.trail.forEach((point, index) => {
      const p = worldToCanvas(point, view);
      if (index === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();
  }

  function drawObstacles(ctx, view) {
    for (const o of state.obstacles) {
      const p = worldToCanvas(o, view);
      ctx.fillStyle = o.id === state.selectedId ? "#f97316" : "#64748b";
      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 1.5;
      ctx.fillRect(p.x, p.y, o.w * view.scale, o.h * view.scale);
      ctx.strokeRect(p.x, p.y, o.w * view.scale, o.h * view.scale);
    }
  }

  function drawTarget(ctx, view) {
    if (!state.target) return;
    const p = worldToCanvas(state.target, view);
    const invalid = ["target_invalid", "path_blocked"].includes(state.pathState);
    ctx.strokeStyle = invalid ? "#dc2626" : "#7c3aed";
    ctx.fillStyle = invalid ? "rgba(220,38,38,0.16)" : "rgba(124,58,237,0.14)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(p.x, p.y, arrivalRadius * view.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = invalid ? "#dc2626" : "#7c3aed";
    ctx.beginPath();
    ctx.moveTo(p.x, p.y - 18);
    ctx.lineTo(p.x, p.y + 12);
    ctx.lineTo(p.x + 16, p.y + 4);
    ctx.lineTo(p.x, p.y - 4);
    ctx.closePath();
    ctx.fill();
    if (state.failedPoint) {
      const fp = worldToCanvas(state.failedPoint, view);
      ctx.strokeStyle = "rgba(220,38,38,0.55)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(fp.x, fp.y, 12, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(fp.x - 7, fp.y - 7);
      ctx.lineTo(fp.x + 7, fp.y + 7);
      ctx.moveTo(fp.x + 7, fp.y - 7);
      ctx.lineTo(fp.x - 7, fp.y + 7);
      ctx.stroke();
    }
  }

  function drawLidar(ctx, view) {
    if (!state.scan?.online) return;
    if (state.showRays) {
      ctx.strokeStyle = "rgba(14, 165, 233, 0.16)";
      ctx.lineWidth = 1;
      const origin = worldToCanvas(state.car, view);
      for (const beam of state.scan.beams || []) {
        const end = worldToCanvas({
          x: state.car.x + Math.cos(beam.angle) * beam.distance,
          y: state.car.y + Math.sin(beam.angle) * beam.distance,
        }, view);
        ctx.beginPath();
        ctx.moveTo(origin.x, origin.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }
    }
    if (state.showHits) {
      ctx.fillStyle = "#0284c7";
      for (const hit of state.scan.hits || []) {
        const p = worldToCanvas(hit, view);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function drawCar(ctx, view) {
    const p = worldToCanvas(state.car, view);
    const scale = view.scale;
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(state.car.theta);
    ctx.fillStyle = state.estop ? "#dc2626" : "#16a34a";
    ctx.strokeStyle = "#052e16";
    ctx.lineWidth = 2;
    ctx.fillRect(-0.28 * scale, -0.18 * scale, 0.56 * scale, 0.36 * scale);
    ctx.strokeRect(-0.28 * scale, -0.18 * scale, 0.56 * scale, 0.36 * scale);
    ctx.fillStyle = "#fef3c7";
    ctx.beginPath();
    ctx.moveTo(0.36 * scale, 0);
    ctx.lineTo(0.16 * scale, -0.12 * scale);
    ctx.lineTo(0.16 * scale, 0.12 * scale);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#dc2626";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo((0.55 + state.car.linear * 3) * scale, 0);
    ctx.stroke();
    ctx.restore();
  }

  function drawHud(ctx, width) {
    const items = [
      `mode ${state.mode}`,
      `path ${pathStateText[state.pathState] || state.pathState}`,
      `target ${meter(state.targetDistance)}`,
      `heading ${state.headingError === null ? "-" : `${Math.round(radToDeg(state.headingError))} deg`}`,
    ];
    const boxWidth = Math.min(360, Math.max(250, width - 36));
    ctx.save();
    ctx.fillStyle = "rgba(15, 23, 42, 0.82)";
    ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
    ctx.lineWidth = 1;
    roundRect(ctx, 18, 18, boxWidth, 78, 8);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "12px IBM Plex Mono, monospace";
    items.forEach((item, index) => ctx.fillText(item, 34 + (index % 2) * 160, 45 + Math.floor(index / 2) * 24));
    ctx.restore();
  }

  function bindCanvas(canvas) {
    canvas.onpointerdown = (event) => {
      const point = canvasToWorld(event, canvas);
      const obstacle = hitObstacle(point);
      state.pointerIntent = { point, clientX: event.clientX, clientY: event.clientY };
      if (distance(point, state.car) < 0.45) {
        state.drag = { type: "car", dx: point.x - state.car.x, dy: point.y - state.car.y };
        state.selectedId = "";
      } else if (obstacle) {
        state.drag = { type: "obstacle", id: obstacle.id, dx: point.x - obstacle.x, dy: point.y - obstacle.y };
        state.selectedId = obstacle.id;
      }
      canvas.setPointerCapture(event.pointerId);
    };
    canvas.onpointermove = (event) => {
      if (!state.drag) return;
      const point = canvasToWorld(event, canvas);
      if (state.drag.type === "car") {
        state.car.x = Math.max(0.25, Math.min(field.width - 0.25, point.x - state.drag.dx));
        state.car.y = Math.max(0.25, Math.min(field.height - 0.25, point.y - state.drag.dy));
        state.car.trail = [{ x: state.car.x, y: state.car.y }];
      } else {
        const o = state.obstacles.find((item) => item.id === state.drag.id);
        if (o) {
          o.x = Math.max(0, Math.min(field.width - o.w, point.x - state.drag.dx));
          o.y = Math.max(0, Math.min(field.height - o.h, point.y - state.drag.dy));
        }
      }
    };
    canvas.onpointerup = (event) => {
      const dragged = Boolean(state.drag);
      const dragType = state.drag?.type || "";
      state.drag = null;
      canvas.releasePointerCapture?.(event.pointerId);
      const intent = state.pointerIntent;
      state.pointerIntent = null;
      if (dragged) {
        if (state.target) replanPath(`${dragType === "car" ? "移动小车" : "移动障碍物"}后重新规划`);
        return;
      }
      if (!intent) return;
      const moved = Math.hypot(event.clientX - intent.clientX, event.clientY - intent.clientY);
      if (moved <= 6) setTarget(canvasToWorld(event, canvas));
    };
    canvas.onpointercancel = () => {
      state.drag = null;
      state.pointerIntent = null;
    };
  }

  function handleAction(action) {
    if (action === "start") {
      if (state.target && state.pathState !== "path_ready") replanPath("开始前重新规划");
      state.running = true;
      addEvent("control", "开始仿真");
    } else if (action === "pause") {
      state.running = false;
      addEvent("control", "暂停仿真");
    } else if (action === "step") {
      update(0.1, performance.now());
      addEvent("control", "单步运行 0.1s");
    } else if (action === "reset") {
      loadScenario("straight");
    } else if (action === "toggle-auto") {
      state.autoEnabled = !state.autoEnabled;
      addEvent("control", state.autoEnabled ? "开启自动驾驶" : "暂停自动驾驶");
    } else if (action === "estop") {
      state.estop = true;
      addEvent("safety", "急停触发");
    } else if (action === "clear-estop") {
      state.estop = false;
      addEvent("safety", "急停解除");
    } else if (action === "lidar-offline") {
      state.lidarOffline = true;
      addEvent("lidar", "模拟 LiDAR 离线");
    } else if (action === "lidar-online") {
      state.lidarOffline = false;
      addEvent("lidar", "恢复 LiDAR");
    } else if (action === "clear-target") {
      clearTarget();
    } else if (action === "replan") {
      replanPath("手动重新规划");
    } else if (action === "return-start") {
      setTarget({ x: state.startPose.x, y: state.startPose.y }, "设置回到起点目标");
    } else if (action === "reset-car") {
      resetCar();
      if (state.target) replanPath("重置小车后重新规划");
    } else if (action === "clear-trail") {
      state.car.trail = [];
    } else if (action === "add-obstacle") {
      addObstacle();
    } else if (action === "delete-obstacle") {
      deleteSelectedObstacle();
    } else if (action === "simple-scene") {
      loadScenario("straight");
    } else if (action === "clear-scene") {
      state.obstacles = [];
      state.selectedId = "";
      addEvent("scene", "清空场景");
      if (state.target) replanPath("清空场景后重新规划");
    } else if (action === "save-default") {
      localStorage.setItem(storageKey, JSON.stringify(sceneSnapshot()));
      addEvent("scene", "保存默认场景");
    } else if (action === "restore-default") {
      const saved = loadSavedScene();
      if (saved) applyScene(saved);
      addEvent("scene", "恢复默认场景");
      if (state.target) replanPath("恢复默认场景后重新规划");
    }
    updateParamLabels();
    updatePanels();
  }

  function loadScenario(name, announce = true) {
    state.running = false;
    state.autoEnabled = true;
    state.estop = name === "estop";
    state.lidarOffline = name === "lost";
    resetCar();
    clearTarget(false);
    if (name === "corridor") {
      state.obstacles = [
        rect(3.2, 1.1, 3.2, 1.2),
        rect(3.2, 4.7, 3.2, 1.2),
        rect(7.2, 2.8, 0.7, 1.2),
      ];
    } else if (name === "sudden") {
      state.obstacles = [rect(2.6, 3.05, 0.8, 0.9)];
    } else if (name === "lost") {
      state.obstacles = [rect(4.4, 3.0, 1.0, 1.0)];
    } else if (name === "estop") {
      state.obstacles = [rect(4.2, 2.7, 1.1, 1.2)];
    } else {
      state.obstacles = [rect(4.4, 3.0, 1.0, 1.0), rect(6.4, 1.3, 0.7, 1.3)];
    }
    state.conclusion = scenarioConclusions[name] || scenarioConclusions.straight;
    state.scanQueue = [];
    state.scan = emptyScan();
    if (announce) addEvent("scenario", state.conclusion);
    updateParamLabels();
  }

  function applyScene(scene) {
    state.car = { ...state.car, ...scene.car, trail: [] };
    state.obstacles = Array.isArray(scene.obstacles) ? scene.obstacles.map((o) => ({ ...o })) : [];
    if (scene.target) setTarget(scene.target, "恢复默认目标点");
  }

  function sceneSnapshot() {
    return { car: { x: state.car.x, y: state.car.y, theta: state.car.theta }, obstacles: state.obstacles, target: state.target };
  }

  function loadSavedScene() {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || "null");
    } catch {
      return null;
    }
  }

  function resetCar() {
    state.car.x = initialCar.x;
    state.car.y = initialCar.y;
    state.car.theta = initialCar.theta;
    state.car.linear = 0;
    state.car.angular = 0;
    state.car.trail = [{ x: state.car.x, y: state.car.y }];
  }

  function setTarget(point, message = "设置目标点") {
    state.target = { x: clamp(point.x, 0, field.width), y: clamp(point.y, 0, field.height) };
    state.arrivedNotified = false;
    addEvent("target", `${message}：${formatPoint(state.target)}`);
    replanPath("设置目标点后规划");
  }

  function clearTarget(announce = true) {
    state.target = null;
    state.path = [];
    state.waypointIndex = 0;
    state.pathState = "no_target";
    state.pathMessage = "点击画布空白处设置目标点。";
    state.targetDistance = null;
    state.headingError = null;
    state.nextWaypoint = null;
    state.failedPoint = null;
    state.arrivedNotified = false;
    state.reason = "no_target";
    if (announce) addEvent("target", "清除目标点");
  }

  function replanPath(message = "重新规划") {
    if (!state.target) {
      clearTarget(false);
      return;
    }
    state.pathState = "planning";
    state.pathMessage = "路径规划中。";
    state.failedPoint = null;
    const result = planPath(state.car, state.target);
    state.path = result.path;
    state.waypointIndex = result.path.length > 1 ? 1 : 0;
    state.pathState = result.state;
    state.pathMessage = result.message;
    state.failedPoint = result.failedPoint || null;
    state.reason = result.state;
    state.mode = state.running && result.state === "path_ready" ? state.mode : "auto_ready";
    state.safe = ["path_ready", "target_reached"].includes(result.state);
    state.arrivedNotified = false;
    updateNavigationProgress();
    addEvent("planner", `${message}：${result.message}`);
  }

  function planPath(start, target) {
    if (isWorldBlocked(target)) {
      return { state: "target_invalid", message: "目标点位于障碍物膨胀区或边界外。", path: [], failedPoint: target };
    }
    if (isWorldBlocked(start)) {
      return { state: "path_blocked", message: "小车位于障碍物膨胀区，无法规划。", path: [], failedPoint: start };
    }
    if (distance(start, target) <= arrivalRadius) {
      return { state: "target_reached", message: "小车已在目标点到达半径内。", path: [pointCopy(target)] };
    }
    const startCell = worldToCell(start);
    const goalCell = worldToCell(target);
    const startKey = cellKey(startCell);
    const goalKey = cellKey(goalCell);
    const open = [{ ...startCell, key: startKey, f: heuristic(startCell, goalCell), g: 0 }];
    const cameFrom = new Map();
    const gScore = new Map([[startKey, 0]]);
    const closed = new Set();
    let found = null;

    while (open.length) {
      open.sort((a, b) => a.f - b.f);
      const current = open.shift();
      if (!current || closed.has(current.key)) continue;
      if (current.key === goalKey) {
        found = current;
        break;
      }
      closed.add(current.key);
      for (const neighbor of neighbors(current)) {
        const key = cellKey(neighbor);
        if (closed.has(key) || !cellWalkable(neighbor.x, neighbor.y)) continue;
        if (neighbor.diagonal && !diagonalAllowed(current, neighbor)) continue;
        const tentative = (gScore.get(current.key) ?? Infinity) + neighbor.cost;
        if (tentative >= (gScore.get(key) ?? Infinity)) continue;
        cameFrom.set(key, current.key);
        gScore.set(key, tentative);
        open.push({ ...neighbor, key, g: tentative, f: tentative + heuristic(neighbor, goalCell) });
      }
    }

    if (!found) {
      return { state: "path_blocked", message: "A* 未找到从小车到目标点的可行路径。", path: [], failedPoint: target };
    }
    const cells = reconstructCells(found.key, cameFrom, startKey).map(parseCellKey);
    const path = simplifyPath(cells.map(cellToWorld));
    path[0] = pointCopy(start);
    path[path.length - 1] = pointCopy(target);
    return { state: "path_ready", message: `路径可用，${path.length} 个 waypoint。`, path };
  }

  function neighbors(cell) {
    const result = [];
    for (let dx = -1; dx <= 1; dx += 1) {
      for (let dy = -1; dy <= 1; dy += 1) {
        if (dx === 0 && dy === 0) continue;
        result.push({
          x: cell.x + dx,
          y: cell.y + dy,
          diagonal: dx !== 0 && dy !== 0,
          cost: Math.hypot(dx, dy) * gridResolution,
        });
      }
    }
    return result;
  }

  function diagonalAllowed(from, to) {
    return cellWalkable(to.x, from.y) && cellWalkable(from.x, to.y);
  }

  function reconstructCells(goalKey, cameFrom, startKey) {
    const cells = [goalKey];
    let current = goalKey;
    while (current !== startKey && cameFrom.has(current)) {
      current = cameFrom.get(current);
      cells.push(current);
    }
    return cells.reverse();
  }

  function simplifyPath(points) {
    if (points.length <= 2) return points;
    const result = [points[0]];
    let lastDx = null;
    let lastDy = null;
    for (let i = 1; i < points.length; i += 1) {
      const prev = points[i - 1];
      const current = points[i];
      const dx = Math.sign(Math.round((current.x - prev.x) * 1000));
      const dy = Math.sign(Math.round((current.y - prev.y) * 1000));
      if (lastDx !== null && (dx !== lastDx || dy !== lastDy)) {
        result.push(prev);
      }
      lastDx = dx;
      lastDy = dy;
    }
    result.push(points[points.length - 1]);
    return result;
  }

  function updateNavigationProgress() {
    if (!state.target) {
      state.targetDistance = null;
      state.headingError = null;
      state.nextWaypoint = null;
      return;
    }
    state.targetDistance = distance(state.car, state.target);
    if (state.targetDistance <= arrivalRadius) {
      state.pathState = "target_reached";
      state.pathMessage = "已到达目标点。";
      state.nextWaypoint = null;
      state.headingError = 0;
      state.rawCmd = { linearX: 0, angularZ: 0 };
      state.finalCmd = { linearX: 0, angularZ: 0 };
      state.car.linear = 0;
      state.car.angular = 0;
      state.mode = "paused";
      state.safe = true;
      state.reason = "target_reached";
      state.running = false;
      if (!state.arrivedNotified) {
        state.arrivedNotified = true;
        addEvent("target", "已到达目标点");
      }
      return;
    }
    if (state.pathState !== "path_ready" || !state.path.length) {
      state.nextWaypoint = null;
      state.headingError = null;
      return;
    }
    while (state.waypointIndex < state.path.length - 1 && distance(state.car, state.path[state.waypointIndex]) <= waypointRadius) {
      state.waypointIndex += 1;
    }
    state.nextWaypoint = state.path[state.waypointIndex] || state.target;
    const desired = Math.atan2(state.nextWaypoint.y - state.car.y, state.nextWaypoint.x - state.car.x);
    state.headingError = normalizeAngle(desired - state.car.theta);
  }

  function isWorldBlocked(point) {
    if (!point || point.x < robotRadius || point.y < robotRadius || point.x > field.width - robotRadius || point.y > field.height - robotRadius) {
      return true;
    }
    return state.obstacles.some((o) => (
      point.x >= o.x - robotRadius &&
      point.x <= o.x + o.w + robotRadius &&
      point.y >= o.y - robotRadius &&
      point.y <= o.y + o.h + robotRadius
    ));
  }

  function cellWalkable(cx, cy) {
    const point = cellToWorld({ x: cx, y: cy });
    return point.x >= 0 && point.x <= field.width && point.y >= 0 && point.y <= field.height && !isWorldBlocked(point);
  }

  function worldToCell(point) {
    return {
      x: clamp(Math.round(point.x / gridResolution), 0, Math.round(field.width / gridResolution)),
      y: clamp(Math.round(point.y / gridResolution), 0, Math.round(field.height / gridResolution)),
    };
  }

  function cellToWorld(cell) {
    return {
      x: clamp(cell.x * gridResolution, 0, field.width),
      y: clamp(cell.y * gridResolution, 0, field.height),
    };
  }

  function cellKey(cell) {
    return `${cell.x},${cell.y}`;
  }

  function parseCellKey(key) {
    const [x, y] = key.split(",").map(Number);
    return { x, y };
  }

  function heuristic(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y) * gridResolution;
  }

  function addObstacle() {
    const obstacle = rect(4.5, 2.8, 1.0, 1.0);
    state.obstacles.push(obstacle);
    state.selectedId = obstacle.id;
    addEvent("scene", "添加矩形障碍物");
    if (state.target) replanPath("添加障碍物后重新规划");
  }

  function deleteSelectedObstacle() {
    if (!state.selectedId) return;
    state.obstacles = state.obstacles.filter((o) => o.id !== state.selectedId);
    state.selectedId = "";
    addEvent("scene", "删除障碍物");
    if (state.target) replanPath("删除障碍物后重新规划");
  }

  function hitObstacle(point) {
    return [...state.obstacles].reverse().find((o) => point.x >= o.x && point.x <= o.x + o.w && point.y >= o.y && point.y <= o.y + o.h);
  }

  function updatePanels() {
    const live = document.getElementById("sim-live-strip");
    if (live) {
      live.innerHTML = [
        ["目标", state.target ? formatPoint(state.target) : "未设置"],
        ["路径", pathStateText[state.pathState] || state.pathState],
        ["目标距离", meter(state.targetDistance)],
        ["航向误差", state.headingError === null ? "-" : `${Math.round(radToDeg(state.headingError))} deg`],
      ].map(([k, v]) => `<span>${escape(k)} <strong>${escape(v)}</strong></span>`).join("");
    }
    const targetCard = document.getElementById("sim-target-card");
    if (targetCard) {
      targetCard.innerHTML = `
        <h3>目标导航</h3>
        <div class="simulator-target-summary">
          <span class="${pathPillClass()}">${escape(pathStateText[state.pathState] || state.pathState)}</span>
          <strong>${escape(state.target ? formatPoint(state.target) : "点击画布设置目标")}</strong>
          <p>${escape(state.pathMessage)}</p>
        </div>
      `;
    }
    const grid = document.getElementById("sim-status-grid");
    if (grid) {
      grid.innerHTML = [
        ["mode", state.mode],
        ["safe", state.safe ? "safe" : "unsafe"],
        ["reason", reasonText[state.reason] || state.reason],
        ["pathState", pathStateText[state.pathState] || state.pathState],
        ["waypoints", state.path.length ? `${state.waypointIndex + 1}/${state.path.length}` : "-"],
        ["next", state.nextWaypoint ? formatPoint(state.nextWaypoint) : "-"],
        ["arrivalRadius", `${arrivalRadius.toFixed(2)} m`],
        ["frontMin", meter(state.scan.frontMin)],
        ["leftFrontMin", meter(state.scan.leftFrontMin)],
        ["rightFrontMin", meter(state.scan.rightFrontMin)],
        ["raw linear", velocity(state.rawCmd.linearX)],
        ["raw angular", angular(state.rawCmd.angularZ)],
        ["final linear", velocity(state.finalCmd.linearX)],
        ["final angular", angular(state.finalCmd.angularZ)],
        ["急停", state.estop ? "是" : "否"],
        ["LiDAR 超时", state.scan.online ? "否" : "是"],
      ].map(([k, v]) => `<span>${escape(k)} <strong>${escape(v)}</strong></span>`).join("");
    }
    const events = document.getElementById("sim-events");
    if (events) {
      events.innerHTML = state.events.slice(0, 20).map((event) => `<tr><td>${escape(event.time)}</td><td>${escape(event.type)}</td><td>${escape(event.text)}</td></tr>`).join("") || `<tr><td colspan="3">暂无仿真事件。</td></tr>`;
    }
    const conclusion = document.getElementById("sim-conclusion");
    if (conclusion) conclusion.textContent = state.conclusion;
    updateParamLabels();
  }

  function pathPillClass() {
    if (state.pathState === "path_ready" || state.pathState === "target_reached") return "pill online";
    if (state.pathState === "path_blocked" || state.pathState === "target_invalid") return "pill danger";
    return "pill warning";
  }

  function updateParamLabels() {
    for (const [key, _label, _min, _max, _step, unit] of controls) {
      const label = document.getElementById(`sim-param-${key}`);
      if (label) label.textContent = `${format(params[key])}${unit}`;
    }
    const heading = document.getElementById("sim-heading");
    const headingLabel = document.getElementById("sim-heading-label");
    if (heading) heading.value = String(Math.round(radToDeg(state.car.theta)));
    if (headingLabel) headingLabel.textContent = `${Math.round(radToDeg(state.car.theta))} deg`;
  }

  function addEvent(type, text) {
    state.events.unshift({ time: new Date().toLocaleTimeString("zh-CN", { hour12: false }), type, text });
    state.events = state.events.slice(0, 20);
  }

  function rect(x, y, w, h) {
    return { id: `obs-${Date.now()}-${Math.random().toString(16).slice(2)}`, x, y, w, h };
  }

  function minOrNull(values) {
    const finite = values.filter(Number.isFinite);
    return finite.length ? Math.min(...finite) : null;
  }

  function noise(amount) {
    return amount ? (Math.random() * 2 - 1) * amount : 0;
  }

  function cross(ax, ay, bx, by) {
    return ax * by - ay * bx;
  }

  function distance(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function normalizeAngle(value) {
    let angle = value;
    while (angle > Math.PI) angle -= Math.PI * 2;
    while (angle < -Math.PI) angle += Math.PI * 2;
    return angle;
  }

  function clamp(value, min, max) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return min;
    return Math.max(min, Math.min(max, numeric));
  }

  function pointCopy(point) {
    return { x: Number(point.x), y: Number(point.y) };
  }

  function degToRad(value) {
    return (value * Math.PI) / 180;
  }

  function radToDeg(value) {
    return (value * 180) / Math.PI;
  }

  function meter(value) {
    if (value === null || value === undefined || value === "") return "-";
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${numeric.toFixed(2)} m` : "-";
  }

  function velocity(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${numeric.toFixed(3)} m/s` : "-";
  }

  function angular(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${numeric.toFixed(3)} rad/s` : "-";
  }

  function formatPoint(point) {
    return point ? `(${Number(point.x).toFixed(2)}, ${Number(point.y).toFixed(2)})` : "-";
  }

  function format(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "-";
    return Math.abs(numeric) >= 10 ? String(Math.round(numeric)) : numeric.toFixed(2).replace(/\.?0+$/, "");
  }

  function roundRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }

  function escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[char]);
  }

  return { renderPage, bindPage, cleanup };
})();
