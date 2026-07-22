# v0.3 Simulator MVP Todolist

## P0：新增仿真页面
- [x] 新增 /simulator 页面
- [x] Dashboard 导航栏增加“仿真”入口
- [x] 页面显示 2D Canvas 场景
- [x] 页面显示参数控制面板
- [x] 页面显示自动驾驶状态面板
- [x] 明确显示 SIMULATION MODE，避免误认为控制真车

## P1：小车实体
- [x] 绘制小车车体
- [x] 绘制车头方向
- [x] 绘制当前速度箭头
- [x] 支持重置小车位置
- [x] 支持拖动小车初始位置
- [x] 支持调整小车朝向
- [x] 支持显示运动轨迹

## P2：场景与障碍物
- [x] 绘制场地边界
- [x] 支持添加矩形障碍物
- [x] 支持拖动障碍物
- [x] 支持删除障碍物
- [x] 支持一键生成简单场景
- [x] 支持一键清空场景
- [x] 支持保存/恢复默认场景

## P3：LiDAR 仿真
- [x] 实现 LiDAR 射线扫描
- [x] 支持调整 LiDAR 最大距离
- [x] 支持调整 LiDAR 光束数量
- [x] 支持调整 LiDAR 视场角
- [x] 支持显示 LiDAR 扫描线
- [x] 支持显示命中点
- [x] 计算 frontMin
- [x] 计算 leftFrontMin
- [x] 计算 rightFrontMin
- [x] 支持 LiDAR 噪声
- [x] 支持 LiDAR 延迟
- [x] 支持 LiDAR 丢包率
- [x] 支持模拟 LiDAR 离线

## P4：自动驾驶决策
- [x] 实现 sim_autopilot.js
- [x] 前方安全时低速前进
- [x] 前方 0.5m ~ 1.0m 时减速
- [x] 前方小于 0.5m 时停车
- [x] 左前近、右前远时右转
- [x] 右前近、左前远时左转
- [x] 左右都近时停车
- [x] 输出 rawCmd
- [x] 输出 reason

## P5：Safety Supervisor 仿真
- [x] 实现 sim_safety.js
- [x] 限制最大线速度
- [x] 限制最大角速度
- [x] LiDAR 超时强制停车
- [x] frontMin 小于 0.5m 强制停车
- [x] 急停强制停车
- [x] 输出 finalCmd
- [x] 显示 rawCmd 和 finalCmd 差异

## P6：参数动态调整
- [x] 最大线速度 slider
- [x] 最大角速度 slider
- [x] 停车距离 slider
- [x] 减速距离 slider
- [x] 避障转向强度 slider
- [x] LiDAR 最大距离 slider
- [x] LiDAR 光束数量 slider
- [x] LiDAR 噪声 slider
- [x] LiDAR 丢包率 slider
- [x] 控制超时 slider
- [x] LiDAR 超时 slider
- [x] 参数修改后实时生效

## P7：展示状态
- [x] 显示当前 mode
- [x] 显示 safe / unsafe
- [x] 显示 reason
- [x] 显示 frontMin
- [x] 显示 leftFrontMin
- [x] 显示 rightFrontMin
- [x] 显示 raw linear / angular
- [x] 显示 final linear / angular
- [x] 显示是否急停
- [x] 显示是否 LiDAR 超时
- [x] 显示最近 20 条仿真事件

## P8：控制按钮
- [x] 开始仿真
- [x] 暂停仿真
- [x] 单步运行
- [x] 重置仿真
- [x] 开启自动驾驶
- [x] 暂停自动驾驶
- [x] 急停
- [x] 解除急停
- [x] 模拟 LiDAR 离线
- [x] 恢复 LiDAR

## P9：理论可行性展示
- [x] 增加“场景 1：直线避障”
- [x] 增加“场景 2：狭窄通道”
- [x] 增加“场景 3：前方突然出现障碍物”
- [x] 增加“场景 4：LiDAR 丢失”
- [x] 增加“场景 5：急停”
- [x] 每个场景显示对应结论