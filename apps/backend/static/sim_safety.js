window.SimSafety = (() => {
  function clamp(value, limit) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return 0;
    return Math.max(-Math.abs(limit), Math.min(Math.abs(limit), numeric));
  }

  function supervise(rawCmd, scan, params, flags) {
    const maxLinear = Number(params.maxLinear);
    const maxAngular = Number(params.maxAngular);
    let finalCmd = {
      linearX: Math.max(0, Math.min(maxLinear, Number(rawCmd?.linearX) || 0)),
      angularZ: clamp(rawCmd?.angularZ, maxAngular),
    };
    let reason = String(flags?.reason || "front_clear");
    let safe = true;
    const front = Number(scan?.frontMin);

    if (flags?.estop) {
      reason = "estop";
      safe = false;
      finalCmd = { linearX: 0, angularZ: 0 };
    } else if (!scan?.online || flags?.lidarTimedOut) {
      reason = "lidar_timeout";
      safe = false;
      finalCmd = { linearX: 0, angularZ: 0 };
    } else if (!Number.isFinite(front) || front < Number(params.stopDistance)) {
      reason = "front_blocked";
      safe = false;
      finalCmd = { linearX: 0, angularZ: 0 };
    }

    return { safe, reason, finalCmd };
  }

  return { supervise };
})();
