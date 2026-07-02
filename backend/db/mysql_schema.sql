-- ============================================================
-- robot_monitor 数据库结构
-- 包含用户、设备、机器人、任务、告警、报告和 IoT 相关表
-- ============================================================

CREATE DATABASE IF NOT EXISTS robot_monitor
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE robot_monitor;

-- ------------------------------------------------------------
-- 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT        PRIMARY KEY AUTO_INCREMENT,
    username      VARCHAR(64)   NOT NULL UNIQUE           COMMENT '登录用户名',
    password_hash VARCHAR(255)  NOT NULL                  COMMENT 'bcrypt 密码哈希',
    display_name  VARCHAR(128)  NOT NULL                  COMMENT '显示名称',
    status        VARCHAR(16)   NOT NULL DEFAULT 'active' COMMENT 'active | disabled',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='系统用户';

-- ------------------------------------------------------------
-- 设备表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    id         BIGINT        PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(128)  NOT NULL                  COMMENT '设备名称',
    code       VARCHAR(64)   NULL                      COMMENT '设备编码',
    model      VARCHAR(128)  NOT NULL                  COMMENT '设备型号',
    manufacturer VARCHAR(128) NULL                    COMMENT '厂商',
    serial_number VARCHAR(128) NULL                   COMMENT '序列号',
    image_path VARCHAR(512)  NULL                      COMMENT '设备图片路径',
    status     VARCHAR(32)   NOT NULL DEFAULT 'normal' COMMENT 'normal | fault | offline',
    category_id BIGINT       NULL                      COMMENT '设备类别 ID',
    robot_id   BIGINT        NULL                      COMMENT '关联机器人 ID',
    notes      TEXT          NULL                      COMMENT '备注',
    created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='巡检设备';

-- ------------------------------------------------------------
-- 机器人表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS robots (
    id         BIGINT         PRIMARY KEY AUTO_INCREMENT,
    model      VARCHAR(128)   NOT NULL,
    ip_address VARCHAR(64)    NULL,
    device_id  BIGINT         NULL COMMENT '主关联设备 ID',
    status     VARCHAR(32)    NOT NULL,
    health     INT            NOT NULL,
    battery    INT            NOT NULL,
    speed      DECIMAL(10,2)  NOT NULL,
    `signal`   INT            NOT NULL,
    latency    INT            NOT NULL,
    lng        DECIMAL(12,6)  NOT NULL,
    lat        DECIMAL(12,6)  NOT NULL,
    heading    INT            NOT NULL,
    created_at DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_robots_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
) COMMENT='巡检机器人';

CREATE INDEX idx_robots_device ON robots (device_id);

-- ------------------------------------------------------------
-- 任务表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(128)  NOT NULL,
    robot_id    BIGINT        NULL,
    priority    VARCHAR(32)   NOT NULL,
    description TEXT          NULL,
    start_at    DATETIME      NOT NULL,
    end_at      DATETIME      NOT NULL,
    status      VARCHAR(32)   NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tasks_robot FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE SET NULL
) COMMENT='巡检任务';

-- ------------------------------------------------------------
-- 告警表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    level       VARCHAR(32)   NOT NULL,
    title       VARCHAR(128)  NOT NULL,
    detail      TEXT          NULL,
    happened_at DATETIME      NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='系统告警';

-- ------------------------------------------------------------
-- 报告表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    title       VARCHAR(128)  NOT NULL,
    value       VARCHAR(64)   NOT NULL,
    trend       VARCHAR(64)   NOT NULL,
    tone        VARCHAR(32)   NOT NULL,
    detail      TEXT          NULL,
    report_date DATE          NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='运行报告';

-- ------------------------------------------------------------
-- IoT：设备 Token 表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_tokens (
    id         BIGINT        PRIMARY KEY AUTO_INCREMENT,
    device_id  BIGINT        NOT NULL                   COMMENT '设备 ID',
    token      VARCHAR(128)  NOT NULL UNIQUE            COMMENT '设备访问 Token（SHA-256 十六进制）',
    note       VARCHAR(256)  NULL                       COMMENT '备注',
    is_active  TINYINT(1)    NOT NULL DEFAULT 1         COMMENT '是否启用',
    created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dt_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='设备访问 Token';

-- ------------------------------------------------------------
-- IoT：设备签到表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_checkins (
    id         BIGINT         PRIMARY KEY AUTO_INCREMENT,
    device_id  BIGINT         NOT NULL                   COMMENT '设备 ID',
    lat        DECIMAL(10,7)  NULL                       COMMENT '纬度',
    lng        DECIMAL(10,7)  NULL                       COMMENT '经度',
    note       TEXT           NULL                       COMMENT '备注',
    checked_at DATETIME       NOT NULL                   COMMENT '签到时间',
    created_at DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ci_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='设备签到记录';

-- ------------------------------------------------------------
-- IoT：设备遥测表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_telemetry (
    id          BIGINT         PRIMARY KEY AUTO_INCREMENT,
    device_id   BIGINT         NOT NULL                   COMMENT '设备 ID',
    battery     TINYINT        NULL                       COMMENT '电量 0-100',
    `signal`    TINYINT        NULL                       COMMENT '信号强度 0-100',
    status      VARCHAR(32)    NULL                       COMMENT '状态 online|offline|fault',
    lat         DECIMAL(10,7)  NULL                       COMMENT '纬度',
    lng         DECIMAL(10,7)  NULL                       COMMENT '经度',
    source_ip   VARCHAR(64)    NULL                       COMMENT '上报来源 IP',
    extra_json  JSON           NULL                       COMMENT '附加信息',
    reported_at DATETIME       NOT NULL                   COMMENT '上报时间',
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tel_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='设备遥测记录';

CREATE INDEX idx_telemetry_device_time ON device_telemetry (device_id, reported_at DESC);

-- ------------------------------------------------------------
-- 设备管理扩展表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_categories (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(128)  NOT NULL UNIQUE,
    description TEXT          NULL,
    status      VARCHAR(32)   NOT NULL DEFAULT 'active',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='设备类别';

CREATE TABLE IF NOT EXISTS onboard_units (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    device_id   BIGINT        NOT NULL,
    name        VARCHAR(128)  NOT NULL,
    unit_type   VARCHAR(64)   NOT NULL,
    model       VARCHAR(128)  NULL,
    protocol    VARCHAR(64)   NULL,
    status      VARCHAR(32)   NOT NULL DEFAULT 'active',
    notes       TEXT          NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_onboard_units_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='机载单元';

CREATE TABLE IF NOT EXISTS network_channels (
    id           BIGINT       PRIMARY KEY AUTO_INCREMENT,
    device_id    BIGINT       NOT NULL,
    name         VARCHAR(128) NOT NULL,
    channel_type VARCHAR(64)  NOT NULL,
    host         VARCHAR(128) NULL,
    port         INT          NULL,
    protocol     VARCHAR(64)  NULL,
    status       VARCHAR(32)  NOT NULL DEFAULT 'active',
    notes        TEXT         NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_network_channels_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='网络通信通道';

-- ------------------------------------------------------------
-- 集群与编队
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clusters (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(128)  NOT NULL UNIQUE,
    description TEXT          NULL,
    status      VARCHAR(32)   NOT NULL DEFAULT 'active',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) COMMENT='机器人集群';

CREATE TABLE IF NOT EXISTS cluster_nodes (
    id         BIGINT       PRIMARY KEY AUTO_INCREMENT,
    cluster_id BIGINT       NOT NULL,
    robot_id   BIGINT       NOT NULL,
    role       VARCHAR(64)  NOT NULL DEFAULT 'member',
    status     VARCHAR(32)  NOT NULL DEFAULT 'standby',
    joined_at  DATETIME     NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cluster_nodes_cluster FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,
    CONSTRAINT fk_cluster_nodes_robot FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE,
    UNIQUE KEY uk_cluster_robot (cluster_id, robot_id)
) COMMENT='集群节点';

CREATE TABLE IF NOT EXISTS formations (
    id             BIGINT       PRIMARY KEY AUTO_INCREMENT,
    cluster_id     BIGINT       NOT NULL,
    name           VARCHAR(128) NOT NULL,
    formation_type VARCHAR(64)  NOT NULL DEFAULT 'line',
    status         VARCHAR(32)  NOT NULL DEFAULT 'draft',
    description    TEXT         NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_formations_cluster FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,
    UNIQUE KEY uk_formation_cluster_name (cluster_id, name)
) COMMENT='编队方案';

CREATE TABLE IF NOT EXISTS formation_members (
    id           BIGINT        PRIMARY KEY AUTO_INCREMENT,
    formation_id BIGINT        NOT NULL,
    robot_id     BIGINT        NOT NULL,
    slot_index   INT           NOT NULL DEFAULT 1,
    role         VARCHAR(64)   NOT NULL DEFAULT 'member',
    offset_x     DECIMAL(10,3) NOT NULL DEFAULT 0,
    offset_y     DECIMAL(10,3) NOT NULL DEFAULT 0,
    offset_yaw   DECIMAL(10,3) NOT NULL DEFAULT 0,
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_formation_members_formation FOREIGN KEY (formation_id) REFERENCES formations(id) ON DELETE CASCADE,
    CONSTRAINT fk_formation_members_robot FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE,
    UNIQUE KEY uk_formation_robot (formation_id, robot_id)
) COMMENT='编队成员';

CREATE TABLE IF NOT EXISTS control_commands (
    id            BIGINT       PRIMARY KEY AUTO_INCREMENT,
    scope         VARCHAR(32)  NOT NULL,
    target_type   VARCHAR(32)  NOT NULL,
    target_id     BIGINT       NOT NULL,
    command_type  VARCHAR(64)  NOT NULL,
    params_json   JSON         NULL,
    status        VARCHAR(32)  NOT NULL DEFAULT 'pending',
    error         TEXT         NULL,
    response_json JSON         NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at  DATETIME     NULL
) COMMENT='统一控制命令记录';

CREATE TABLE IF NOT EXISTS autonomy_events (
    id         BIGINT      PRIMARY KEY AUTO_INCREMENT,
    robot_id   BIGINT      NOT NULL,
    level      VARCHAR(20) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    message    TEXT        NULL,
    data_json  JSON        NULL,
    created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
) COMMENT='自动驾驶事件日志';

CREATE INDEX idx_autonomy_events_robot_time ON autonomy_events (robot_id, created_at DESC);

-- ------------------------------------------------------------
-- IoT：设备传感器数据表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_sensor_data (
    id           BIGINT       PRIMARY KEY AUTO_INCREMENT,
    device_id    BIGINT       NOT NULL                   COMMENT '设备 ID',
    sensor_type  VARCHAR(32)  NOT NULL                   COMMENT 'camera|stereo|lidar',
    channel      VARCHAR(32)  NULL                       COMMENT 'mono|left|right|depth|scan|pointcloud',
    file_path    VARCHAR(512) NULL                       COMMENT '文件存储路径（图片类）',
    data_json    JSON         NULL                       COMMENT '结构化数据（雷达/点云）',
    content_type VARCHAR(64)  NULL                       COMMENT 'MIME 类型',
    size_bytes   BIGINT       NULL DEFAULT 0             COMMENT '文件大小',
    extra_json   JSON         NULL                       COMMENT '附加元数据',
    reported_at  DATETIME     NOT NULL                   COMMENT '上报时间',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sensor_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='设备传感器数据';

CREATE INDEX idx_sensor_device_time ON device_sensor_data (device_id, sensor_type, reported_at DESC);
CREATE INDEX idx_sensor_device_type_channel_time ON device_sensor_data (device_id, sensor_type, channel, reported_at DESC);
