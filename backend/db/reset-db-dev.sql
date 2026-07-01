-- Local development reset script.
-- Run this only against a disposable local database.

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE device_sensor_data;
TRUNCATE TABLE control_commands;
TRUNCATE TABLE formation_members;
TRUNCATE TABLE formations;
TRUNCATE TABLE cluster_nodes;
TRUNCATE TABLE clusters;
TRUNCATE TABLE network_channels;
TRUNCATE TABLE onboard_units;
TRUNCATE TABLE device_telemetry;
TRUNCATE TABLE device_checkins;
TRUNCATE TABLE device_tokens;
TRUNCATE TABLE reports;
TRUNCATE TABLE alerts;
TRUNCATE TABLE tasks;
TRUNCATE TABLE devices;
TRUNCATE TABLE robots;
TRUNCATE TABLE device_categories;
TRUNCATE TABLE users;

SET FOREIGN_KEY_CHECKS = 1;
