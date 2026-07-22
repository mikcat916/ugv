下面是专门针对你现在目标的 **小范围自动驾驶 Todolist**，不包含大型自动驾驶、SLAM、复杂导航这些暂时不需要的内容。

# v0.2 Autopilot MVP Todolist

## P0：安全基础，必须先做

* [x] 新增自动驾驶状态机

  * [x] `manual`
  * [x] `auto_ready`
  * [x] `auto_running`
  * [x] `paused`
  * [x] `fault`
  * [x] `estop`
* [x] 明确控制优先级

```text
急停 > 人工接管 > 安全监督器 > 自动驾驶 > 普通远程控制
```

* [x] 后端新增 `GET /api/autopilot/status`
* [x] 后端新增 `POST /api/autopilot/start`
* [x] 后端新增 `POST /api/autopilot/pause`
* [x] 后端新增 `POST /api/autopilot/resume`
* [x] 后端新增 `POST /api/autopilot/stop`
* [x] 后端新增 `POST /api/autopilot/estop`
* [x] 后端新增 `POST /api/autopilot/clear-estop`
* [x] Web 页面增加急停按钮
* [x] 急停触发后立即停车
* [x] 急停后必须手动解除，不能自动恢复
* [x] 手动控制时自动驾驶自动暂停
* [x] 自动模式下限制最大线速度
* [x] 自动模式下限制最大角速度
* [x] 控制指令超时后自动停车
* [x] LiDAR 数据超时后自动停车

## P1：LiDAR 避障

* [x] 新增 `tools/device/lidar_obstacle.py`
* [x] 订阅 ROS `/scan`
* [x] 过滤无效距离值：

  * [x] `inf`
  * [x] `nan`
  * [x] `0`
  * [x] 小于 `range_min`
  * [x] 大于 `range_max`
* [x] 将雷达分成三个区域：

  * [x] 左前
  * [x] 正前
  * [x] 右前
* [x] 计算 `left_front_min`
* [x] 计算 `front_min`
* [x] 计算 `right_front_min`
* [x] 生成 `obstacle_status`
* [x] 生成建议线速度 `linear_x`
* [x] 生成建议角速度 `angular_z`
* [x] 正前 `< 0.5m` 强制停车
* [x] 正前 `0.5m ~ 1.0m` 自动减速
* [x] 左前近、右前远时向右避让
* [x] 右前近、左前远时向左避让
* [x] 左右都近时停车
* [x] 雷达超过 2 秒无数据时停车

## P2：车端自动驾驶主循环

* [x] 新增 `tools/device/safety_supervisor.py`
* [x] 新增 `tools/device/autopilot_node.py`
* [x] 自动驾驶节点读取当前模式
* [x] 自动驾驶节点读取急停状态
* [x] 自动驾驶节点读取人工接管状态
* [x] 自动驾驶节点读取 LiDAR 避障结果
* [x] 自动模式下发布 `/cmd_vel`
* [x] 默认线速度上限为 `0.1 m/s`
* [x] 默认角速度限制为安全范围
* [x] LiDAR 正常且前方安全时低速前进
* [x] 前方较近时减速
* [x] 前方过近时停车
* [x] 障碍消失后继续低速前进
* [x] 任何异常状态下发布停车指令
* [x] 自动驾驶状态定期上报后端

## P3：后端状态与事件日志

* [x] 新增 `apps/backend/src/ugv_backend/autopilot.py`
* [x] 保存最近一次自动驾驶状态
* [x] 保存最近一次 LiDAR 避障状态
* [x] 保存最近一次控制状态
* [x] 新增 `autonomy_events` 表

```sql
CREATE TABLE autonomy_events (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  robot_id BIGINT NOT NULL,
  level VARCHAR(20) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  message TEXT,
  data_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

* [x] 记录自动驾驶启动事件
* [x] 记录自动驾驶暂停事件
* [x] 记录自动驾驶恢复事件
* [x] 记录自动驾驶停止事件
* [x] 记录急停事件
* [x] 记录解除急停事件
* [x] 记录 LiDAR 超时事件
* [x] 记录前方障碍物过近事件
* [x] 记录人工接管事件
* [x] `GET /api/autopilot/status` 返回当前状态和原因

推荐返回格式：

```json
{
  "mode": "auto_running",
  "safe": true,
  "reason": "front_clear",
  "linearX": 0.1,
  "angularZ": 0.0,
  "lidar": {
    "online": true,
    "ageSeconds": 0.4,
    "frontMin": 1.8,
    "leftFrontMin": 1.2,
    "rightFrontMin": 2.1
  },
  "manualOverride": false,
  "estop": false
}
```

## P4：Web 自动驾驶面板

* [x] 新增或扩展自动驾驶页面
* [x] 显示当前模式
* [x] 显示是否安全
* [x] 显示当前决策原因
* [x] 显示当前线速度
* [x] 显示当前角速度
* [x] 显示 LiDAR 在线状态
* [x] 显示 LiDAR 数据年龄
* [x] 显示正前最近距离
* [x] 显示左前最近距离
* [x] 显示右前最近距离
* [x] 显示人工接管状态
* [x] 显示急停状态
* [x] 增加启动自动驾驶按钮
* [x] 增加暂停按钮
* [x] 增加继续按钮
* [x] 增加停止按钮
* [x] 增加急停按钮
* [x] 增加解除急停按钮
* [x] 显示最近 20 条自动驾驶事件

状态文案建议：

```text
自动驾驶运行中：前方安全，低速前进
自动驾驶减速：前方 0.82m 有障碍物
自动驾驶暂停：前方 0.41m 障碍物过近
自动驾驶故障：LiDAR 超过 2 秒未更新
自动驾驶急停：用户触发急停
```

## P5：本地测试流程

* [x] 增加 `docs/checklists/autopilot-local-test.md`
* [x] 测试后端能启动
* [x] 测试 Web 页面能打开
* [x] 测试 `/api/autopilot/status`
* [x] 测试启动自动驾驶
* [x] 测试暂停自动驾驶
* [x] 测试继续自动驾驶
* [x] 测试停止自动驾驶
* [x] 测试急停
* [x] 测试解除急停
* [x] 模拟 LiDAR 正前 `< 0.5m`
* [x] 确认自动停车
* [x] 模拟 LiDAR 正前 `0.5m ~ 1.0m`
* [x] 确认自动减速
* [x] 模拟 LiDAR 超过 2 秒无数据
* [x] 确认进入故障或停车状态
* [x] 测试手动控制时自动驾驶暂停
* [x] 测试事件日志是否记录

## P6：回归测试

* [x] 测试 `GET /api/autopilot/status`
* [x] 测试 `POST /api/autopilot/start`
* [x] 测试 `POST /api/autopilot/pause`
* [x] 测试 `POST /api/autopilot/resume`
* [x] 测试 `POST /api/autopilot/stop`
* [x] 测试 `POST /api/autopilot/estop`
* [x] 测试 `POST /api/autopilot/clear-estop`
* [x] 测试急停状态下不能启动自动驾驶
* [x] 测试 LiDAR 超时状态下不能进入 `auto_running`
* [x] 测试手动接管会暂停自动驾驶
* [x] 测试事件日志写入
* [x] 测试非法状态切换会被拒绝

## P7：暂时不要做的内容

* [ ] 不做公共道路自动驾驶
* [ ] 不做高速运动
* [ ] 不做复杂 SLAM
* [ ] 不做视觉识别
* [ ] 不做多车协同
* [ ] 不做云端远程自动驾驶
* [ ] 不做复杂路径规划
* [ ] 不做自动回充

## 推荐执行顺序

```text
1. apps/backend/src/ugv_backend/autopilot.py
2. /api/autopilot/status
3. /api/autopilot/estop
4. Web 急停按钮
5. safety_supervisor.py
6. lidar_obstacle.py
7. autopilot_node.py
8. Web 自动驾驶状态面板
10. autonomy_events
11. 回归测试
12. docs/checklists/autopilot-local-test.md
```

## 最小交付标准

做到下面这些，就可以算第一版小范围自动驾驶 MVP 完成：

```text
- Web
- 可以启动自动模式
- 自动模式下低速前进
- LiDAR 正前小于 0.5m 自动停车
- LiDAR 正前 0.5m 到 1.0m 自动减速
- LiDAR 超时自动停车
- 手动控制会暂停自动驾驶
- 页面能看到当前状态和原因
- 事件日志能记录急停、启动、暂停、障碍物停车
```
