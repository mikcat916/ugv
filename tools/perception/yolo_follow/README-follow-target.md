# YOLO Target Follow

This setup uses a separate computer to run YOLO and keeps the Raspberry Pi focused on video streaming and motor control.

## Current Raspberry Pi endpoints

- MJPEG stream: `http://192.168.31.198:8080/?action=stream`
- Robot control server: `192.168.31.198:9000`

The control server accepts newline-delimited JSON messages:

```json
{"type":"cmd_vel","v":0.18,"w":0.35}
{"type":"stop"}
```

## Local setup

```bash
pip install -r requirements.txt
python follow_target_yolo.py
```

## Useful examples

Follow a person:

```bash
python follow_target_yolo.py --target-class person
```

Stable person-follow settings for the `oneday` server:

```bash
python follow_target_yolo.py --device cuda:0 --target-class person --frame-skip 2 --image-size 416 --conf 0.55 --linear-speed 0.10 --max-angular-speed 0.35 --deadband 0.12 --target-width-ratio 0.20 --max-width-ratio 0.32
```

Use a local model file:

```bash
python follow_target_yolo.py --model C:\\path\\to\\best.pt --target-class bottle
```

Reduce load further:

```bash
python follow_target_yolo.py --frame-skip 3 --image-size 320
```

Show a local preview window on a desktop machine:

```bash
python follow_target_yolo.py --show-window
```

## Notes

- `robot_server` on the Raspberry Pi must be running on port `9000`.
- If the target is lost, the script sends `stop`.
- Start with low speed values and test with the robot lifted off the ground first.
- On headless Linux servers, keep `--show-window` off.
- Recommended for people-following: slower forward speed, larger deadband, and lower turn rate to reduce jitter.
