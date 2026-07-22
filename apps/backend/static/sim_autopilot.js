window.SimAutopilot = (() => {
  function finite(value, fallback = Infinity) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : fallback;
  }

  function clamp(value, min, max) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return min;
    return Math.max(min, Math.min(max, numeric));
  }

  function decide(scan, params, enabled = true, navContext = {}) {
    if (!enabled) {
      return { mode: "paused", safe: false, reason: "autopilot_paused", rawCmd: { linearX: 0, angularZ: 0 } };
    }
    if (!scan || !scan.online) {
      return { mode: "auto_ready", safe: false, reason: "lidar_timeout", rawCmd: { linearX: 0, angularZ: 0 } };
    }

    const pathState = String(navContext.pathState || "no_target");
    if (pathState === "no_target") {
      return { mode: "auto_ready", safe: false, reason: "no_target", rawCmd: { linearX: 0, angularZ: 0 } };
    }
    if (pathState === "target_invalid") {
      return { mode: "auto_ready", safe: false, reason: "target_invalid", rawCmd: { linearX: 0, angularZ: 0 } };
    }
    if (pathState === "path_blocked") {
      return { mode: "auto_ready", safe: false, reason: "path_blocked", rawCmd: { linearX: 0, angularZ: 0 } };
    }
    if (pathState === "target_reached") {
      return { mode: "paused", safe: true, reason: "target_reached", rawCmd: { linearX: 0, angularZ: 0 } };
    }
    if (pathState === "planning") {
      return { mode: "auto_ready", safe: false, reason: "planning", rawCmd: { linearX: 0, angularZ: 0 } };
    }

    const front = finite(scan.frontMin);
    const left = finite(scan.leftFrontMin);
    const right = finite(scan.rightFrontMin);
    const stop = Number(params.stopDistance);
    const slow = Number(params.slowDistance);
    const maxLinear = Number(params.maxLinear);
    const maxAngular = Number(params.maxAngular);
    const turn = Number(params.turnStrength);
    const targetDistance = finite(navContext.targetDistance, 0);
    const headingError = Number(navContext.headingError) || 0;
    const absHeading = Math.abs(headingError);
    let reason = "path_ready";
    let safe = true;

    const turnCmd = clamp(headingError * 1.8, -maxAngular, maxAngular);
    const headingScale = clamp(1 - absHeading / Math.PI, 0.25, 1);
    const arrivalScale = clamp(targetDistance / 1.2, 0.25, 1);
    let rawCmd = {
      linearX: maxLinear * headingScale * arrivalScale,
      angularZ: turnCmd,
    };

    if (absHeading > Math.PI * 0.55) {
      rawCmd.linearX = maxLinear * 0.2;
    }

    if (left < slow && right < slow && front < slow) {
      reason = "both_front_blocked";
      rawCmd = { linearX: 0, angularZ: 0 };
      safe = false;
    } else if (front < stop) {
      reason = "front_blocked";
      rawCmd = { linearX: 0, angularZ: 0 };
      safe = false;
    } else if (left < slow && right >= left) {
      reason = "avoid_right";
      rawCmd = { linearX: maxLinear * 0.35, angularZ: -turn };
    } else if (right < slow && left > right) {
      reason = "avoid_left";
      rawCmd = { linearX: maxLinear * 0.35, angularZ: turn };
    } else if (front < slow) {
      reason = "front_slow";
      rawCmd = { linearX: maxLinear * 0.28, angularZ: left > right ? turn * 0.55 : -turn * 0.55 };
    }

    return { mode: "auto_running", safe, reason, rawCmd };
  }

  return { decide };
})();
