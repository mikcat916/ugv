# -*- coding: utf-8 -*-
"""
设备信息管理数据库模块
使用MySQL存储设备信息
"""

import pymysql
import hashlib
from typing import List, Optional


class DeviceDatabase:
    """设备数据库操作类 - MySQL版本"""
    
    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "",
                 database: str = "device_management"):
        """
        初始化数据库连接
        
        Args:
            host: MySQL服务器地址
            port: MySQL端口
            user: 用户名
            password: 密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """建立数据库连接"""
        # 先连接MySQL服务器，创建数据库（如果不存在）
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
        
        # 连接到指定数据库
        self.conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        self.cursor = self.conn.cursor()
    
    def _create_tables(self):
        """创建所有数据表"""
        # 设备基本信息表
        sql_devices = """
        CREATE TABLE IF NOT EXISTS devices (
            UGVId INT AUTO_INCREMENT PRIMARY KEY,
            UGVCode VARCHAR(32) UNIQUE NOT NULL,
            UGVName VARCHAR(64),
            UGVImage VARCHAR(255),
            UGVModel VARCHAR(255),
            UsePwd VARCHAR(64),
            MagPwd VARCHAR(64),
            Positioning VARCHAR(32),
            SensorList VARCHAR(500),
            BatteryCap FLOAT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql_devices)
        
        # 存储信息表
        sql_storage = """
        CREATE TABLE IF NOT EXISTS storage (
            MSId INT AUTO_INCREMENT PRIMARY KEY,
            UGVId INT NOT NULL,
            MemTotal FLOAT,
            MemUsed FLOAT,
            GPUShared FLOAT,
            MemBuffers FLOAT,
            MemCached FLOAT,
            MemFree FLOAT,
            DiskTotal FLOAT,
            DiskUsed FLOAT,
            TimeStamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UGVId) REFERENCES devices(UGVId) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql_storage)
        
        # 算力信息表
        sql_computing = """
        CREATE TABLE IF NOT EXISTS computing (
            CPId INT AUTO_INCREMENT PRIMARY KEY,
            UGVId INT NOT NULL,
            CPUUsage FLOAT,
            CPUCoreUsage VARCHAR(200),
            CPUCoreFreq VARCHAR(200),
            CPUTemp FLOAT,
            GPUUsage FLOAT,
            GPUTemp FLOAT,
            GPUFreq FLOAT,
            TimeStamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UGVId) REFERENCES devices(UGVId) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql_computing)

        sql_system_info = """
        CREATE TABLE IF NOT EXISTS system_info (
            SIId INT AUTO_INCREMENT PRIMARY KEY,
            UGVId INT NOT NULL,
            SerialNumber VARCHAR(64),
            HardwareModel VARCHAR(64),
            OpSystem VARCHAR(64),
            Eth0 VARCHAR(32),
            Wlan0 VARCHAR(32),
            Docker0 VARCHAR(32),
            HostName VARCHAR(64),
            Remark TEXT,
            FOREIGN KEY (UGVId) REFERENCES devices(UGVId) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql_system_info)

        sql_energy = """
        CREATE TABLE IF NOT EXISTS energy (
            BEId INT AUTO_INCREMENT PRIMARY KEY,
            UGVId INT NOT NULL,
            VDDIn FLOAT,
            VDDSoc FLOAT,
            VDDCpuGpuCv FLOAT,
            ComputeVoltage FLOAT,
            ComputeCurrent FLOAT,
            Uptime TIME,
            BatteryLevel INT,
            TimeStamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UGVId) REFERENCES devices(UGVId) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql_energy)

        sql_communication = """
        CREATE TABLE IF NOT EXISTS communication (
            NMId INT AUTO_INCREMENT PRIMARY KEY,
            UGVId INT NOT NULL,
            IfaceName VARCHAR(32),
            WifiRxRate FLOAT,
            WifiTxRate FLOAT,
            WifiRSSI INT,
            WifiLinkSpeed INT,
            WifiLossRate FLOAT,
            WsRxRate FLOAT,
            WsTxRate FLOAT,
            WsConnCount INT,
            WsReconnectCount INT,
            NetStatus INT,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (UGVId) REFERENCES devices(UGVId) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.cursor.execute(sql_communication)
        
        self.conn.commit()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行SHA256哈希加密"""
        if not password:
            return ""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # ==================== 设备信息 CRUD ====================
    
    def insert_device(self, device_data: dict) -> int:
        """插入新设备"""
        if device_data.get('UsePwd'):
            device_data['UsePwd'] = self.hash_password(device_data['UsePwd'])
        if device_data.get('MagPwd'):
            device_data['MagPwd'] = self.hash_password(device_data['MagPwd'])
        
        sql = """
        INSERT INTO devices (UGVCode, UGVName, UGVImage, UGVModel, UsePwd, 
                            MagPwd, Positioning, SensorList, BatteryCap)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            device_data.get('UGVCode', ''),
            device_data.get('UGVName', ''),
            device_data.get('UGVImage', ''),
            device_data.get('UGVModel', ''),
            device_data.get('UsePwd', ''),
            device_data.get('MagPwd', ''),
            device_data.get('Positioning', ''),
            device_data.get('SensorList', ''),
            device_data.get('BatteryCap', 0.0)
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_device(self, ugv_id: int, device_data: dict, update_password: bool = False) -> bool:
        """更新设备信息"""
        if update_password:
            if device_data.get('UsePwd'):
                device_data['UsePwd'] = self.hash_password(device_data['UsePwd'])
            if device_data.get('MagPwd'):
                device_data['MagPwd'] = self.hash_password(device_data['MagPwd'])
        
        sql = """
        UPDATE devices SET 
            UGVCode = %s, UGVName = %s, UGVImage = %s, UGVModel = %s,
            UsePwd = %s, MagPwd = %s, Positioning = %s, SensorList = %s, BatteryCap = %s
        WHERE UGVId = %s
        """
        values = (
            device_data.get('UGVCode', ''),
            device_data.get('UGVName', ''),
            device_data.get('UGVImage', ''),
            device_data.get('UGVModel', ''),
            device_data.get('UsePwd', ''),
            device_data.get('MagPwd', ''),
            device_data.get('Positioning', ''),
            device_data.get('SensorList', ''),
            device_data.get('BatteryCap', 0.0),
            ugv_id
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_device(self, ugv_id: int) -> bool:
        """删除设备"""
        sql = "DELETE FROM devices WHERE UGVId = %s"
        self.cursor.execute(sql, (ugv_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_devices(self) -> List[dict]:
        """获取所有设备"""
        sql = "SELECT * FROM devices ORDER BY UGVId"
        self.cursor.execute(sql)
        return self.cursor.fetchall()
    
    def get_device_by_id(self, ugv_id: int) -> Optional[dict]:
        """根据ID获取设备"""
        sql = "SELECT * FROM devices WHERE UGVId = %s"
        self.cursor.execute(sql, (ugv_id,))
        return self.cursor.fetchone()
    
    def search_devices(self, keyword: str) -> List[dict]:
        """搜索设备"""
        sql = """
        SELECT * FROM devices 
        WHERE UGVCode LIKE %s OR UGVName LIKE %s OR UGVModel LIKE %s
        ORDER BY UGVId
        """
        pattern = f"%{keyword}%"
        self.cursor.execute(sql, (pattern, pattern, pattern))
        return self.cursor.fetchall()
    
    def check_code_exists(self, code: str, exclude_id: int = None) -> bool:
        """检查设备编号是否已存在"""
        if exclude_id:
            sql = "SELECT COUNT(*) as cnt FROM devices WHERE UGVCode = %s AND UGVId != %s"
            self.cursor.execute(sql, (code, exclude_id))
        else:
            sql = "SELECT COUNT(*) as cnt FROM devices WHERE UGVCode = %s"
            self.cursor.execute(sql, (code,))
        result = self.cursor.fetchone()
        return result['cnt'] > 0
    
    def get_device_count(self) -> int:
        """获取设备总数"""
        sql = "SELECT COUNT(*) as cnt FROM devices"
        self.cursor.execute(sql)
        return self.cursor.fetchone()['cnt']
    
    # ==================== 存储信息 CRUD ====================
    
    def insert_storage(self, data: dict) -> int:
        """插入存储信息记录"""
        sql = """
        INSERT INTO storage (UGVId, MemTotal, MemUsed, GPUShared, MemBuffers, 
                            MemCached, MemFree, DiskTotal, DiskUsed, TimeStamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('UGVId'),
            data.get('MemTotal', 0.0),
            data.get('MemUsed', 0.0),
            data.get('GPUShared', 0.0),
            data.get('MemBuffers', 0.0),
            data.get('MemCached', 0.0),
            data.get('MemFree', 0.0),
            data.get('DiskTotal', 0.0),
            data.get('DiskUsed', 0.0),
            data.get('TimeStamp')
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_storage(self, ms_id: int, data: dict) -> bool:
        """更新存储信息记录"""
        sql = """
        UPDATE storage SET 
            UGVId = %s, MemTotal = %s, MemUsed = %s, GPUShared = %s, MemBuffers = %s,
            MemCached = %s, MemFree = %s, DiskTotal = %s, DiskUsed = %s, TimeStamp = %s
        WHERE MSId = %s
        """
        values = (
            data.get('UGVId'),
            data.get('MemTotal', 0.0),
            data.get('MemUsed', 0.0),
            data.get('GPUShared', 0.0),
            data.get('MemBuffers', 0.0),
            data.get('MemCached', 0.0),
            data.get('MemFree', 0.0),
            data.get('DiskTotal', 0.0),
            data.get('DiskUsed', 0.0),
            data.get('TimeStamp'),
            ms_id
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_storage(self, ms_id: int) -> bool:
        """删除存储信息记录"""
        sql = "DELETE FROM storage WHERE MSId = %s"
        self.cursor.execute(sql, (ms_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_storage(self) -> List[dict]:
        """获取所有存储信息"""
        sql = """
        SELECT s.*, d.UGVCode, d.UGVName 
        FROM storage s 
        LEFT JOIN devices d ON s.UGVId = d.UGVId 
        ORDER BY s.MSId DESC
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()
    
    def get_storage_by_id(self, ms_id: int) -> Optional[dict]:
        """根据ID获取存储信息"""
        sql = "SELECT * FROM storage WHERE MSId = %s"
        self.cursor.execute(sql, (ms_id,))
        return self.cursor.fetchone()
    
    def search_storage(self, keyword: str) -> List[dict]:
        """搜索存储信息"""
        sql = """
        SELECT s.*, d.UGVCode, d.UGVName 
        FROM storage s 
        LEFT JOIN devices d ON s.UGVId = d.UGVId 
        WHERE d.UGVCode LIKE %s OR d.UGVName LIKE %s
        ORDER BY s.MSId DESC
        """
        pattern = f"%{keyword}%"
        self.cursor.execute(sql, (pattern, pattern))
        return self.cursor.fetchall()
    
    def get_storage_count(self) -> int:
        """获取存储信息记录总数"""
        sql = "SELECT COUNT(*) as cnt FROM storage"
        self.cursor.execute(sql)
        return self.cursor.fetchone()['cnt']
    
    # ==================== 算力信息 CRUD ====================
    
    def insert_computing(self, data: dict) -> int:
        """插入算力信息记录"""
        sql = """
        INSERT INTO computing (UGVId, CPUUsage, CPUCoreUsage, CPUCoreFreq, 
                              CPUTemp, GPUUsage, GPUTemp, GPUFreq, TimeStamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('UGVId'),
            data.get('CPUUsage', 0.0),
            data.get('CPUCoreUsage', ''),
            data.get('CPUCoreFreq', ''),
            data.get('CPUTemp', 0.0),
            data.get('GPUUsage', 0.0),
            data.get('GPUTemp', 0.0),
            data.get('GPUFreq', 0.0),
            data.get('TimeStamp')
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_computing(self, cp_id: int, data: dict) -> bool:
        """更新算力信息记录"""
        sql = """
        UPDATE computing SET 
            UGVId = %s, CPUUsage = %s, CPUCoreUsage = %s, CPUCoreFreq = %s,
            CPUTemp = %s, GPUUsage = %s, GPUTemp = %s, GPUFreq = %s, TimeStamp = %s
        WHERE CPId = %s
        """
        values = (
            data.get('UGVId'),
            data.get('CPUUsage', 0.0),
            data.get('CPUCoreUsage', ''),
            data.get('CPUCoreFreq', ''),
            data.get('CPUTemp', 0.0),
            data.get('GPUUsage', 0.0),
            data.get('GPUTemp', 0.0),
            data.get('GPUFreq', 0.0),
            data.get('TimeStamp'),
            cp_id
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_computing(self, cp_id: int) -> bool:
        """删除算力信息记录"""
        sql = "DELETE FROM computing WHERE CPId = %s"
        self.cursor.execute(sql, (cp_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_computing(self) -> List[dict]:
        """获取所有算力信息"""
        sql = """
        SELECT c.*, d.UGVCode, d.UGVName 
        FROM computing c 
        LEFT JOIN devices d ON c.UGVId = d.UGVId 
        ORDER BY c.CPId DESC
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()
    
    def get_computing_by_id(self, cp_id: int) -> Optional[dict]:
        """根据ID获取算力信息"""
        sql = "SELECT * FROM computing WHERE CPId = %s"
        self.cursor.execute(sql, (cp_id,))
        return self.cursor.fetchone()
    
    def search_computing(self, keyword: str) -> List[dict]:
        """搜索算力信息"""
        sql = """
        SELECT c.*, d.UGVCode, d.UGVName 
        FROM computing c 
        LEFT JOIN devices d ON c.UGVId = d.UGVId 
        WHERE d.UGVCode LIKE %s OR d.UGVName LIKE %s
        ORDER BY c.CPId DESC
        """
        pattern = f"%{keyword}%"
        self.cursor.execute(sql, (pattern, pattern))
        return self.cursor.fetchall()
    
    def get_computing_count(self) -> int:
        """获取算力信息记录总数"""
        sql = "SELECT COUNT(*) as cnt FROM computing"
        self.cursor.execute(sql)
        return self.cursor.fetchone()['cnt']
    
    # ==================== 通用方法 ====================
    
    # ==================== 系统信息 CRUD ====================

    def insert_system(self, data: dict) -> int:
        sql = """
        INSERT INTO system_info (
            UGVId, SerialNumber, HardwareModel, OpSystem, Eth0, Wlan0, Docker0, HostName, Remark
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('UGVId'),
            data.get('SerialNumber', ''),
            data.get('HardwareModel', ''),
            data.get('OpSystem', ''),
            data.get('Eth0', ''),
            data.get('Wlan0', ''),
            data.get('Docker0', ''),
            data.get('HostName', ''),
            data.get('Remark', ''),
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def update_system(self, si_id: int, data: dict) -> bool:
        sql = """
        UPDATE system_info SET
            UGVId = %s, SerialNumber = %s, HardwareModel = %s, OpSystem = %s,
            Eth0 = %s, Wlan0 = %s, Docker0 = %s, HostName = %s, Remark = %s
        WHERE SIId = %s
        """
        values = (
            data.get('UGVId'),
            data.get('SerialNumber', ''),
            data.get('HardwareModel', ''),
            data.get('OpSystem', ''),
            data.get('Eth0', ''),
            data.get('Wlan0', ''),
            data.get('Docker0', ''),
            data.get('HostName', ''),
            data.get('Remark', ''),
            si_id,
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_system(self, si_id: int) -> bool:
        sql = "DELETE FROM system_info WHERE SIId = %s"
        self.cursor.execute(sql, (si_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_all_system(self) -> List[dict]:
        sql = """
        SELECT s.*, d.UGVCode, d.UGVName
        FROM system_info s
        LEFT JOIN devices d ON s.UGVId = d.UGVId
        ORDER BY s.SIId DESC
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_system_by_id(self, si_id: int) -> Optional[dict]:
        sql = "SELECT * FROM system_info WHERE SIId = %s"
        self.cursor.execute(sql, (si_id,))
        return self.cursor.fetchone()

    def search_system(self, keyword: str) -> List[dict]:
        sql = """
        SELECT s.*, d.UGVCode, d.UGVName
        FROM system_info s
        LEFT JOIN devices d ON s.UGVId = d.UGVId
        WHERE d.UGVCode LIKE %s OR d.UGVName LIKE %s OR s.SerialNumber LIKE %s OR s.HostName LIKE %s
        ORDER BY s.SIId DESC
        """
        pattern = f"%{keyword}%"
        self.cursor.execute(sql, (pattern, pattern, pattern, pattern))
        return self.cursor.fetchall()

    def get_system_count(self) -> int:
        sql = "SELECT COUNT(*) as cnt FROM system_info"
        self.cursor.execute(sql)
        return self.cursor.fetchone()['cnt']

    # ==================== 能量信息 CRUD ====================

    def insert_energy(self, data: dict) -> int:
        sql = """
        INSERT INTO energy (
            UGVId, VDDIn, VDDSoc, VDDCpuGpuCv, ComputeVoltage, ComputeCurrent, Uptime, BatteryLevel, TimeStamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('UGVId'),
            data.get('VDDIn', 0.0),
            data.get('VDDSoc', 0.0),
            data.get('VDDCpuGpuCv', 0.0),
            data.get('ComputeVoltage', 0.0),
            data.get('ComputeCurrent', 0.0),
            data.get('Uptime', '00:00:00'),
            data.get('BatteryLevel', 0),
            data.get('TimeStamp'),
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def update_energy(self, be_id: int, data: dict) -> bool:
        sql = """
        UPDATE energy SET
            UGVId = %s, VDDIn = %s, VDDSoc = %s, VDDCpuGpuCv = %s, ComputeVoltage = %s,
            ComputeCurrent = %s, Uptime = %s, BatteryLevel = %s, TimeStamp = %s
        WHERE BEId = %s
        """
        values = (
            data.get('UGVId'),
            data.get('VDDIn', 0.0),
            data.get('VDDSoc', 0.0),
            data.get('VDDCpuGpuCv', 0.0),
            data.get('ComputeVoltage', 0.0),
            data.get('ComputeCurrent', 0.0),
            data.get('Uptime', '00:00:00'),
            data.get('BatteryLevel', 0),
            data.get('TimeStamp'),
            be_id,
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_energy(self, be_id: int) -> bool:
        sql = "DELETE FROM energy WHERE BEId = %s"
        self.cursor.execute(sql, (be_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_all_energy(self) -> List[dict]:
        sql = """
        SELECT e.*, d.UGVCode, d.UGVName
        FROM energy e
        LEFT JOIN devices d ON e.UGVId = d.UGVId
        ORDER BY e.BEId DESC
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_energy_by_id(self, be_id: int) -> Optional[dict]:
        sql = "SELECT * FROM energy WHERE BEId = %s"
        self.cursor.execute(sql, (be_id,))
        return self.cursor.fetchone()

    def search_energy(self, keyword: str) -> List[dict]:
        sql = """
        SELECT e.*, d.UGVCode, d.UGVName
        FROM energy e
        LEFT JOIN devices d ON e.UGVId = d.UGVId
        WHERE d.UGVCode LIKE %s OR d.UGVName LIKE %s
        ORDER BY e.BEId DESC
        """
        pattern = f"%{keyword}%"
        self.cursor.execute(sql, (pattern, pattern))
        return self.cursor.fetchall()

    def get_energy_count(self) -> int:
        sql = "SELECT COUNT(*) as cnt FROM energy"
        self.cursor.execute(sql)
        return self.cursor.fetchone()['cnt']

    # ==================== 通信信息 CRUD ====================

    def insert_communication(self, data: dict) -> int:
        sql = """
        INSERT INTO communication (
            UGVId, IfaceName, WifiRxRate, WifiTxRate, WifiRSSI, WifiLinkSpeed, WifiLossRate,
            WsRxRate, WsTxRate, WsConnCount, WsReconnectCount, NetStatus, Timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('UGVId'),
            data.get('IfaceName', ''),
            data.get('WifiRxRate', 0.0),
            data.get('WifiTxRate', 0.0),
            data.get('WifiRSSI', 0),
            data.get('WifiLinkSpeed', 0),
            data.get('WifiLossRate', 0.0),
            data.get('WsRxRate', 0.0),
            data.get('WsTxRate', 0.0),
            data.get('WsConnCount', 0),
            data.get('WsReconnectCount', 0),
            data.get('NetStatus', 0),
            data.get('Timestamp'),
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.lastrowid

    def update_communication(self, nm_id: int, data: dict) -> bool:
        sql = """
        UPDATE communication SET
            UGVId = %s, IfaceName = %s, WifiRxRate = %s, WifiTxRate = %s, WifiRSSI = %s, WifiLinkSpeed = %s,
            WifiLossRate = %s, WsRxRate = %s, WsTxRate = %s, WsConnCount = %s, WsReconnectCount = %s,
            NetStatus = %s, Timestamp = %s
        WHERE NMId = %s
        """
        values = (
            data.get('UGVId'),
            data.get('IfaceName', ''),
            data.get('WifiRxRate', 0.0),
            data.get('WifiTxRate', 0.0),
            data.get('WifiRSSI', 0),
            data.get('WifiLinkSpeed', 0),
            data.get('WifiLossRate', 0.0),
            data.get('WsRxRate', 0.0),
            data.get('WsTxRate', 0.0),
            data.get('WsConnCount', 0),
            data.get('WsReconnectCount', 0),
            data.get('NetStatus', 0),
            data.get('Timestamp'),
            nm_id,
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_communication(self, nm_id: int) -> bool:
        sql = "DELETE FROM communication WHERE NMId = %s"
        self.cursor.execute(sql, (nm_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_all_communication(self) -> List[dict]:
        sql = """
        SELECT n.*, d.UGVCode, d.UGVName
        FROM communication n
        LEFT JOIN devices d ON n.UGVId = d.UGVId
        ORDER BY n.NMId DESC
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_communication_by_id(self, nm_id: int) -> Optional[dict]:
        sql = "SELECT * FROM communication WHERE NMId = %s"
        self.cursor.execute(sql, (nm_id,))
        return self.cursor.fetchone()

    def search_communication(self, keyword: str) -> List[dict]:
        sql = """
        SELECT n.*, d.UGVCode, d.UGVName
        FROM communication n
        LEFT JOIN devices d ON n.UGVId = d.UGVId
        WHERE d.UGVCode LIKE %s OR d.UGVName LIKE %s OR n.IfaceName LIKE %s
        ORDER BY n.NMId DESC
        """
        pattern = f"%{keyword}%"
        self.cursor.execute(sql, (pattern, pattern, pattern))
        return self.cursor.fetchall()

    def get_communication_count(self) -> int:
        sql = "SELECT COUNT(*) as cnt FROM communication"
        self.cursor.execute(sql)
        return self.cursor.fetchone()['cnt']

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
