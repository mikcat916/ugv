# v0.2.1 Autopilot Safety Patch

## P0
- [x] 改 ROS 控制链路：autopilot_node 发布 /autopilot/cmd_vel_raw
- [x] safety_supervisor 订阅 /autopilot/cmd_vel_raw
- [x] safety_supervisor 最终发布 /cmd_vel
- [x] safety_supervisor 收到 raw cmd 时更新 last_control_at
- [x] safety_supervisor 增加 frontMin >= 0.5 强校验
- [x] 后端 LiDAR timeout 默认从 10 秒改成 2 或 3 秒
- [x] 后端前方障碍物过近时清零 linearX / angularZ
- [x] 后端前方障碍物过近时切到 paused 或 fault

## P1
- [x] autonomy_events 不再写 robot_id=0
- [x] 增加 safety_supervisor 单元测试
- [x] 增加 LiDAR timeout / front blocked / estop 回归测试
- [x] backend README 补自动驾驶 API
- [x] docs/autopilot-local-test.md 补实车前检查流程
