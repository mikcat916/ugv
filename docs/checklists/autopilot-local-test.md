# Autopilot Local Test

This checklist covers the v0.2 autopilot MVP on a local backend plus a robot-side ROS environment.

## 1. Start Backend

```bash
cd /home/oneday/project4
python -m uvicorn ugv_backend.main:app --app-dir apps/backend/src --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health` and confirm `status` is `ok`.

## 2. Open Web Panel

1. Open `http://127.0.0.1:8000/login`.
2. Log in with the local admin account.
3. Open `http://127.0.0.1:8000/autopilot`.
4. Confirm `/api/autopilot/status` returns JSON with `mode`, `safe`, `reason`, `lidar`, `manualOverride`, and `estop`.

## 3. Start Robot-Side ROS Nodes

Before enabling motion on a real robot:

- Lift the drive wheels or put the robot on blocks for the first dry run.
- Keep an operator near the hardware E-stop and keep the Web E-stop page open.
- Confirm `rostopic echo /autopilot/obstacle_status` shows `online: true`, `ageSeconds < 2`, and `frontMin >= 0.5`.
- Confirm no node except `safety_supervisor.py` publishes final base commands to `/cmd_vel`.
- Confirm `autopilot_node.py` publishes raw commands on `/autopilot/cmd_vel_raw` and `safety_supervisor.py` forwards safe commands to `/cmd_vel`.

Run these on the robot or in a ROS shell that can see `/scan` and publish `/cmd_vel`.

```bash
rosrun project4 lidar_obstacle.py
rosrun project4 safety_supervisor.py
rosrun project4 autopilot_node.py --server http://<backend-ip>:8000 --token <device-token> --robot-id <robot-id>
```

Dry-run first pass:

```bash
python3 tools/device/safety_supervisor.py _dry_run:=true
python3 tools/device/autopilot_node.py --dry-run --server http://127.0.0.1:8000 --token <device-token>
```

Confirm decisions are printed and no velocity reaches the chassis before disabling dry-run.

If running directly from this repository:

```bash
python3 tools/device/lidar_obstacle.py
python3 tools/device/safety_supervisor.py
python3 tools/device/autopilot_node.py --server http://127.0.0.1:8000 --token <device-token>
```

## 4. API Regression Flow

Use the Web panel buttons or authenticated POST requests:

```bash
GET  /api/autopilot/status
POST /api/autopilot/start
POST /api/autopilot/deadman
POST /api/autopilot/pause
POST /api/autopilot/resume
POST /api/autopilot/stop
POST /api/autopilot/estop
POST /api/autopilot/clear-estop
```

Confirm:

- Start enters `auto_ready` when LiDAR is missing or stale.
- Fresh safe LiDAR allows `auto_running`.
- Estop immediately sends stop and blocks start/resume until `clear-estop`.
- Manual remote control pauses automatic driving.
- Front `< 0.5m` pauses or faults automatic driving and clears backend `linearX` / `angularZ`.
- Closing the Web panel for longer than `AUTOPILOT_DEADMAN_TIMEOUT_SECONDS` causes `reason = deadman_timeout`.
- Setting `AUTOPILOT_MAX_RUNTIME_SECONDS` to a small value causes `reason = runtime_timeout` after that limit.

## 5. LiDAR Simulation

Publish fake `/autopilot/obstacle_status` JSON or replay `/scan` data.

- Front `< 0.5m`: confirm backend `linearX = 0`, `angularZ = 0`, `/cmd_vel` is stopped by `safety_supervisor.py`, and an event is recorded.
- Front `0.5m ~ 1.0m`: confirm reduced speed.
- Left front near and right front clear: confirm right avoidance.
- Right front near and left front clear: confirm left avoidance.
- No LiDAR update for more than 2 seconds: confirm `reason = lidar_timeout` and the robot stops.

## 6. Raw Command Gate Check

Use these topic checks while the robot is still lifted:

```bash
rostopic echo /autopilot/cmd_vel_raw
rostopic echo /cmd_vel
```

Confirm raw commands appear first on `/autopilot/cmd_vel_raw`. With safe LiDAR, matching commands should appear on `/cmd_vel`. When LiDAR is stale, E-stop is active, or `frontMin < 0.5`, `/cmd_vel` should receive zero-speed stop commands.

## 7. Debug Log Export

In the Web autopilot panel, click `导出调试日志` after each test pass and save the downloaded JSON with the field record.

Confirm the file includes:

- `status.safety.rawCmd`
- `status.safety.finalCmd`
- `cmdVelLog`
- `obstacleStatusLog`
- `events`

## 8. Event Log

Open the Web autopilot panel and confirm the recent event list includes start, pause, resume, stop, estop, clear-estop, LiDAR timeout, front obstacle, and manual override events as those actions occur.

## 9. Field Test Record Template

```text
Test date/time:
Operator:
Robot ID:
Backend URL:
Weather / ground condition:
Battery level:
ROS topics checked:
LiDAR frontMin before start:
Dry-run result:
Deadman timeout test:
Max runtime setting:
Start time:
Stop time:
Stop reason:
Raw cmd sample:
Final cmd sample:
Debug log filename:
Observed issue:
Decision:
```
