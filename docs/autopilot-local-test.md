# Autopilot Local Test

This checklist covers the v0.2 autopilot MVP on a local backend plus a robot-side ROS environment.

## 1. Start Backend

```bash
cd /home/oneday/project4/backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health` and confirm `status` is `ok`.

## 2. Open Web Panel

1. Open `http://127.0.0.1:8000/login`.
2. Log in with the local admin account.
3. Open `http://127.0.0.1:8000/autopilot`.
4. Confirm `/api/autopilot/status` returns JSON with `mode`, `safe`, `reason`, `lidar`, `manualOverride`, and `estop`.

## 3. Start Desktop Client

```bash
cd /home/oneday/project4
python desktop/main.py
```

Open the basic control page and confirm the automatic driving status area shows the backend connection state.

## 4. Start Robot-Side ROS Nodes

Run these on the robot or in a ROS shell that can see `/scan` and publish `/cmd_vel`.

```bash
rosrun project4 lidar_obstacle.py
rosrun project4 safety_supervisor.py
rosrun project4 autopilot_node.py --server http://<backend-ip>:8000 --token <device-token> --robot-id <robot-id>
```

If running directly from this repository:

```bash
python3 scripts/lidar_obstacle.py
python3 scripts/safety_supervisor.py
python3 scripts/autopilot_node.py --server http://127.0.0.1:8000 --token <device-token>
```

## 5. API Regression Flow

Use the Web panel buttons or authenticated POST requests:

```bash
GET  /api/autopilot/status
POST /api/autopilot/start
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

## 6. LiDAR Simulation

Publish fake `/autopilot/obstacle_status` JSON or replay `/scan` data.

- Front `< 0.5m`: confirm `linearX = 0`, `/cmd_vel` is stopped, and an event is recorded.
- Front `0.5m ~ 1.0m`: confirm reduced speed.
- Left front near and right front clear: confirm right avoidance.
- Right front near and left front clear: confirm left avoidance.
- No LiDAR update for more than 2 seconds: confirm `reason = lidar_timeout` and the robot stops.

## 7. Event Log

Open the Web autopilot panel and confirm the recent event list includes start, pause, resume, stop, estop, clear-estop, LiDAR timeout, front obstacle, and manual override events as those actions occur.
