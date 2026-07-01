-- Local development seed data.
-- Apply after backend/db/mysql_schema.sql. Admin user is created by backend startup.

INSERT INTO robots
    (id, model, ip_address, status, health, battery, speed, `signal`, latency, lng, lat, heading)
VALUES
    (1, '本地测试机器人-01', '127.0.0.1', 'idle', 100, 88, 0.00, 100, 0, 113.584411, 22.349433, 0)
ON DUPLICATE KEY UPDATE
    model = VALUES(model),
    ip_address = VALUES(ip_address),
    status = VALUES(status),
    health = VALUES(health),
    battery = VALUES(battery),
    speed = VALUES(speed),
    `signal` = VALUES(`signal`),
    latency = VALUES(latency),
    lng = VALUES(lng),
    lat = VALUES(lat),
    heading = VALUES(heading);

INSERT INTO device_categories (id, name, description, status)
VALUES
    (1, '本地测试设备', '本地开发用设备分类', 'active')
ON DUPLICATE KEY UPDATE
    description = VALUES(description),
    status = VALUES(status);

INSERT INTO devices
    (id, name, code, model, manufacturer, serial_number, status, category_id, robot_id, notes)
VALUES
    (1, '本地测试传感器', 'LOCAL-SENSOR-001', 'local-dev', 'Project4', 'LOCAL-001', 'normal', 1, 1, '本地开发测试数据')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    code = VALUES(code),
    model = VALUES(model),
    manufacturer = VALUES(manufacturer),
    serial_number = VALUES(serial_number),
    status = VALUES(status),
    category_id = VALUES(category_id),
    robot_id = VALUES(robot_id),
    notes = VALUES(notes);

INSERT INTO tasks
    (id, name, robot_id, priority, description, start_at, end_at, status)
VALUES
    (1, '本地测试巡检任务', 1, 'medium', '本地开发用任务', NOW(), DATE_ADD(NOW(), INTERVAL 1 HOUR), 'pending')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    robot_id = VALUES(robot_id),
    priority = VALUES(priority),
    description = VALUES(description),
    start_at = VALUES(start_at),
    end_at = VALUES(end_at),
    status = VALUES(status);

INSERT INTO alerts
    (id, level, title, detail, happened_at)
VALUES
    (1, 'info', '本地测试告警', '用于确认告警列表渲染。', NOW())
ON DUPLICATE KEY UPDATE
    level = VALUES(level),
    title = VALUES(title),
    detail = VALUES(detail),
    happened_at = VALUES(happened_at);

INSERT INTO reports
    (id, title, value, trend, tone, detail, report_date)
VALUES
    (1, '本地测试报告', 'OK', 'stable', 'good', '用于确认报告列表渲染。', CURDATE())
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    value = VALUES(value),
    trend = VALUES(trend),
    tone = VALUES(tone),
    detail = VALUES(detail),
    report_date = VALUES(report_date);
