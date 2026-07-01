# config.py
from __future__ import annotations
import os
import platform
import shutil
import sys
from pathlib import Path
from configparser import ConfigParser, NoSectionError, NoOptionError
from typing import Dict, Tuple, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QDialog, QWidget, QLineEdit, QFormLayout, QPushButton, QHBoxLayout, QVBoxLayout, \
    QMessageBox, QFileDialog, QGridLayout, QSizePolicy, QLabel, QGroupBox, QApplication

#CONFIG_DIR = Path.home() / "conf"  # 或者当前目录Path(".")
CONFIG_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = CONFIG_DIR / "config.ini"

# 首次运行标识文件名
FIRST_RUN_MARK = ".first_run_done"
FIRST_RUN_MARK_PATH = CONFIG_DIR / FIRST_RUN_MARK

SECTION_MYSQL = "mysql"

_DEFAULTS = {
    "DB_HOST": "127.0.0.1",
    "DB_PORT": "3306",
    "DB_USER": "root",
    "DB_PASS": "123456",
    "DB_NAME": "UGV_DB",
    "mysqldump_path": "",
    "mysql_path": "",
    "auto_backup_path": "./auto_backups",
    "manual_backup_path": "./manual_backups"
}

_ENV_OVERRIDES = {
    "DB_HOST": ("UAV_DB_HOST", "MYSQL_HOST"),
    "DB_PORT": ("UAV_DB_PORT", "MYSQL_PORT"),
    "DB_USER": ("UAV_DB_USER", "MYSQL_USER"),
    "DB_PASS": ("UAV_DB_PASSWORD", "MYSQL_PASSWORD"),
    "DB_NAME": ("UAV_DB_NAME", "MYSQL_DATABASE"),
}


def _apply_env_overrides(values: Dict[str, str]) -> Dict[str, str]:
    merged = dict(values)
    for key, env_names in _ENV_OVERRIDES.items():
        for env_name in env_names:
            env_value = os.getenv(env_name)
            if env_value not in (None, ""):
                merged[key] = env_value
                break
    return merged


def is_first_run(create_marker: bool = False) -> bool:
    """
    判断是否为首次打开软件：
    - 若 CONFIG_DIR 下不存在标识文件，则视为首次运行（返回 True）
    - 当 create_marker=True 且判定为首次运行时，会自动创建标识文件
    """
    try:
        if FIRST_RUN_MARK_PATH.exists():
            return False
        # 不存在 => 首次运行
        if create_marker:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            # 原子写入（尽量避免并发竞争）
            FIRST_RUN_MARK_PATH.write_text("ok", encoding="utf-8")
        return True
    except Exception:
        # 任何异常都不阻塞软件启动，保守按“首次”处理
        return True


def mark_first_run_done() -> None:
    """
    主动写入首次运行标识。适用于你在完成初始化（如引导向导、首次配置）后再调用。
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    FIRST_RUN_MARK_PATH.write_text("ok", encoding="utf-8")


def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, str]:
    """读取配置（不存在则用默认值并写入文件）。"""
    cfg = ConfigParser()
    if CONFIG_PATH.exists():
        cfg.read(CONFIG_PATH, encoding="utf-8")
    if not cfg.has_section(SECTION_MYSQL):
        cfg.add_section(SECTION_MYSQL)
    # 合并默认值
    for k, v in _DEFAULTS.items():
        if not cfg.has_option(SECTION_MYSQL, k):
            cfg.set(SECTION_MYSQL, k, v)
    _ensure_dir(CONFIG_PATH)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)
    # 返回 dict
    values = {k: cfg.get(SECTION_MYSQL, k) for k in _DEFAULTS.keys()}
    return _apply_env_overrides(values)


def save_config(values: Dict[str, str]) -> None:
    """写入配置（仅 mysql 节）。"""
    cfg = ConfigParser()
    if CONFIG_PATH.exists():
        cfg.read(CONFIG_PATH, encoding="utf-8")
    if not cfg.has_section(SECTION_MYSQL):
        cfg.add_section(SECTION_MYSQL)
    for k in _DEFAULTS.keys():
        if k in values and values[k] is not None:
            cfg.set(SECTION_MYSQL, k, str(values[k]))
    _ensure_dir(CONFIG_PATH)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)


def validate_config(values: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """基础校验：host 非空、port 为 1-65535、user 非空、db 名非空。"""
    host = (values.get("DB_HOST") or "").strip()
    if not host:
        return False, "DB_HOST 不能为空"
    port = values.get("DB_PORT", "").strip()
    if not port.isdigit():
        return False, "DB_PORT 必须是数字"
    p = int(port)
    if not (1 <= p <= 65535):
        return False, "DB_PORT 必须在 1~65535 之间"
    user = (values.get("DB_USER") or "").strip()
    if not user:
        return False, "DB_USER 不能为空"
    db = (values.get("DB_NAME") or "").strip()
    if not db:
        return False, "DB_NAME 不能为空"
    return True, None


def get_sqlalchemy_url(values: Dict[str, str]) -> str:
    """生成 SQLAlchemy MySQL 连接串（pymysql 驱动为例）。"""
    host = values["DB_HOST"]
    port = int(values["DB_PORT"])
    user = values["DB_USER"]
    pwd = values.get("DB_PASS", "")
    db = values["DB_NAME"]
    # 注意：若用户名/密码有特殊字符，可在此进行 urlencode
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"


# config.py
from typing import Tuple, Dict, Optional


def _test_mysql_connection(values: Dict[str, str],
                           check_db_exists: bool = True,
                           try_use_db: bool = True) -> Tuple[bool, str]:
    """
    测试到 MySQL 的连接，并（可选）检测 DB_NAME 是否存在。
    - check_db_exists=True 时，会查询 information_schema.SCHEMATA 判断库是否存在
    - try_use_db=True 时，会再执行一次 `SELECT 1`/`USE <db>` 验证当前用户是否能访问该库
    """
    try:
        import pymysql
    except Exception:
        return False, "未安装 pymysql，请先安装：pip install pymysql"

    ok, err = validate_config(values)
    if not ok:
        return False, err or "配置不合法"

    host = values["DB_HOST"].strip()
    port = int(values["DB_PORT"])
    user = values["DB_USER"].strip()
    pwd = values.get("DB_PASS", "")
    db = values["DB_NAME"].strip()

    # 1) 先连服务器（不指定 database，避免库不存在时直接报错）
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=pwd,
            charset="utf8mb4", connect_timeout=5,
            read_timeout=5, write_timeout=5,
        )
    except Exception as e:
        return False, f"无法连接到 MySQL 服务器：{e}"

    try:
        with conn.cursor() as cur:
            # 2) 检查库是否存在
            if check_db_exists:
                cur.execute(
                    "SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s",
                    (db,)
                )
                row = cur.fetchone()
                if not row:
                    return False, f"数据库不存在：{db}"

            # 3) （可选）验证对该库的访问权限
            if try_use_db:
                # 对部分受限账号，直接 USE 可能被拒绝；兼容两种方式
                try:
                    cur.execute(f"USE `{db}`")
                    cur.execute("SELECT 1")
                    _ = cur.fetchone()
                except Exception as e:
                    return False, f"已连接服务器，但无法访问数据库 `{db}`：{e}"

        return True, "连接成功，数据库存在且可访问"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _create_database_if_missing(values: Dict[str, str]) -> Tuple[bool, str]:
    """尝试自动创建数据库（utf8mb4），用于测试连接时的快捷操作。"""
    try:
        import pymysql
    except Exception:
        return False, "未安装 pymysql，请先安装：pip install pymysql"

    ok, err = validate_config(values)
    if not ok:
        return False, err or "配置不合法"

    host = values["DB_HOST"].strip()
    port = int(values["DB_PORT"])
    user = values["DB_USER"].strip()
    pwd = values.get("DB_PASS", "")
    db = values["DB_NAME"].strip()
    safe_db = db.replace("`", "``")

    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=pwd,
            charset="utf8mb4", connect_timeout=5,
            read_timeout=5, write_timeout=5,
        )
    except Exception as e:
        return False, f"无法连接到 MySQL 服务器：{e}"

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{safe_db}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        return True, f"数据库已创建：{db}"
    except Exception as e:
        return False, f"创建数据库失败：{e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def test_mysql_connection() -> Tuple[bool, str]:
    values = load_config()
    return _test_mysql_connection(values, True, True)


class ConfigEditorDialog(QDialog):
    """MySQL/备份配置编辑窗口（含自动识别可执行路径与备份目录）"""
    configSaved = pyqtSignal(dict)

    # ------------------------ 公共接口 ------------------------

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("MySQL 配置")
        self.resize(640, 460)

        # --- 基础字段 ---
        self.ed_host = QLineEdit()
        self.ed_port = QLineEdit()
        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit()
        self.ed_name = QLineEdit()

        self.ed_port.setValidator(QIntValidator(1, 65535, self))
        self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)

        # --- 新增：工具路径&备份目录 ---
        self.ed_mysql = QLineEdit()
        self.ed_mysqldump = QLineEdit()
        self.ed_auto_dir = QLineEdit()
        self.ed_manual_dir = QLineEdit()

        for _w in (self.ed_mysql, self.ed_mysqldump, self.ed_auto_dir, self.ed_manual_dir):
            _w.setPlaceholderText("自动识别失败可手动选择")
            _w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.btn_browse_mysql = QPushButton("浏览…")
        self.btn_browse_mysqldump = QPushButton("浏览…")
        self.btn_browse_auto = QPushButton("选择…")
        self.btn_browse_manual = QPushButton("选择…")
        self.btn_autodetect = QPushButton("自动识别路径")

        self.btn_test = QPushButton("测试连接")
        self.btn_save = QPushButton("保存")
        self.btn_cancel = QPushButton("取消")

        # --- 布局：三组分区 + 顶/底操作条 ---
        gb_conn = QGroupBox("数据库连接", self)
        grid_conn = QGridLayout(gb_conn)
        self._add_form_row(grid_conn, 0, "主机名：", self.ed_host)
        self._add_form_row(grid_conn, 1, "端口：", self.ed_port)
        self._add_form_row(grid_conn, 2, "用户名：", self.ed_user)
        self._add_form_row(grid_conn, 3, "密码：", self.ed_pass)
        self._add_form_row(grid_conn, 4, "数据库名：", self.ed_name)
        self._tune_grid(grid_conn)

        gb_tools = QGroupBox("工具路径", self)
        grid_tools = QGridLayout(gb_tools)
        self._add_form_row(grid_tools, 0, "mysql 路径：",
                           self._mk_row_with_browse(self.ed_mysql, self.btn_browse_mysql))
        self._add_form_row(grid_tools, 1, "mysqldump 路径：",
                           self._mk_row_with_browse(self.ed_mysqldump, self.btn_browse_mysqldump))
        self._tune_grid(grid_tools)

        gb_dirs = QGroupBox("备份目录", self)
        grid_dirs = QGridLayout(gb_dirs)
        self._add_form_row(grid_dirs, 0, "自动备份目录：",
                           self._mk_row_with_browse(self.ed_auto_dir, self.btn_browse_auto))
        self._add_form_row(grid_dirs, 1, "手动备份目录：",
                           self._mk_row_with_browse(self.ed_manual_dir, self.btn_browse_manual))
        self._tune_grid(grid_dirs)

        bar_top = QHBoxLayout()
        bar_top.setContentsMargins(0, 0, 0, 0)
        bar_top.addWidget(self.btn_autodetect)
        bar_top.addStretch(1)

        bar_bottom = QHBoxLayout()
        bar_bottom.setContentsMargins(0, 0, 0, 0)
        bar_bottom.addWidget(self.btn_test)
        bar_bottom.addStretch(1)
        bar_bottom.addWidget(self.btn_save)
        bar_bottom.addWidget(self.btn_cancel)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
        root.addWidget(gb_conn)
        root.addWidget(gb_tools)
        root.addWidget(gb_dirs)
        root.addLayout(bar_top)
        root.addLayout(bar_bottom)

        # --- 事件绑定 ---
        self.btn_browse_mysql.clicked.connect(self._on_browse_mysql)
        self.btn_browse_mysqldump.clicked.connect(self._on_browse_mysqldump)
        self.btn_browse_auto.clicked.connect(self._on_browse_auto)
        self.btn_browse_manual.clicked.connect(self._on_browse_manual)
        self.btn_autodetect.clicked.connect(self._on_autodetect)
        self.btn_test.clicked.connect(self._on_test)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.reject)

        # 初始加载
        self._load_values()

    # ------------------------ 交互逻辑 ------------------------

    def _on_browse_mysql(self):
        filt = "Executable (*.exe *.bat *.cmd);;All Files (*)" if self._is_windows() else "All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "选择 mysql 可执行文件", "", filt)
        if path:
            self.ed_mysql.setText(path)

    def _on_browse_mysqldump(self):
        filt = "Executable (*.exe *.bat *.cmd);;All Files (*)" if self._is_windows() else "All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "选择 mysqldump 可执行文件", "", filt)
        if path:
            self.ed_mysqldump.setText(path)

    def _on_browse_auto(self):
        base = self.ed_auto_dir.text() or self._default_auto_dir()
        path = QFileDialog.getExistingDirectory(self, "选择自动备份目录", base)
        if path:
            self.ed_auto_dir.setText(path)

    def _on_browse_manual(self):
        base = self.ed_manual_dir.text() or self._default_manual_dir()
        path = QFileDialog.getExistingDirectory(self, "选择手动备份目录", base)
        if path:
            self.ed_manual_dir.setText(path)

    def _on_autodetect(self):
        mysql_p = self._detect_mysql_path()
        mysqldump_p = self._detect_mysqldump_path()
        if mysql_p:
            self.ed_mysql.setText(mysql_p)
        if mysqldump_p:
            self.ed_mysqldump.setText(mysqldump_p)

        auto_dir, manual_dir = self._detect_backup_dirs()
        if not self.ed_auto_dir.text().strip():
            self.ed_auto_dir.setText(auto_dir)
        if not self.ed_manual_dir.text().strip():
            self.ed_manual_dir.setText(manual_dir)

        msg = []
        if not mysql_p: msg.append("未找到 mysql")
        if not mysqldump_p: msg.append("未找到 mysqldump")
        if msg:
            QMessageBox.information(self, "自动识别", "；".join(msg) + "，可手动选择。")
        else:
            QMessageBox.information(self, "自动识别", "已完成自动识别，可确认或手动调整。")

    def _on_test(self):
        values = self._collect()
        ok, msg = _test_mysql_connection(values)  # 依赖现有实现
        if ok:
            QMessageBox.information(self, "测试连接", msg)
            return

        # 数据库不存在时，提示是否自动创建
        if "数据库不存在" in msg:
            ret = QMessageBox.question(
                self,
                "测试连接",
                "数据库连接成功\n\n"+msg + "\n\n是否自动创建该数据库？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ret == QMessageBox.Yes:
                created, create_msg = _create_database_if_missing(values)
                if created:
                    QMessageBox.information(self, "自动创建", create_msg)
                    # 再测一次
                    ok2, msg2 = _test_mysql_connection(values)
                    QMessageBox.information(self, "测试连接", msg2) if ok2 else QMessageBox.warning(self, "测试连接", msg2)
                else:
                    QMessageBox.warning(self, "自动创建失败", create_msg)
            else:
                QMessageBox.warning(self, "测试连接", msg)
            return

        QMessageBox.warning(self, "测试连接", msg)

    def _on_save(self):
        values = self._collect()
        ok, err = validate_config(values)  # 依赖现有实现
        if not ok:
            QMessageBox.warning(self, "校验失败", err or "配置不合法")
            return

        # 轻量存在性校验（不强制）
        warns = []
        if values["mysql_path"] and not Path(values["mysql_path"]).exists():
            warns.append("mysql_path 不存在")
        if values["mysqldump_path"] and not Path(values["mysqldump_path"]).exists():
            warns.append("mysqldump_path 不存在")
        for k in ("auto_backup_path", "manual_backup_path"):
            p = values[k]
            if p:
                try:
                    Path(p).mkdir(parents=True, exist_ok=True)
                except Exception:
                    warns.append(f"{k} 无法创建")

        if warns:
            QMessageBox.warning(self, "提示", "路径校验提醒：\n- " + "\n- ".join(warns))

        try:
            save_config(values)  # 依赖现有实现
            self.configSaved.emit(values)
            QMessageBox.information(self, "保存成功", f"配置已保存到 {CONFIG_PATH}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    # ------------------------ 数据装载 ------------------------

    def _load_values(self):
        cfg = load_config()  # 依赖现有实现
        self.ed_host.setText(cfg.get("DB_HOST", ""))
        self.ed_port.setText(cfg.get("DB_PORT", "3306"))
        self.ed_user.setText(cfg.get("DB_USER", ""))
        self.ed_pass.setText(cfg.get("DB_PASS", ""))
        self.ed_name.setText(cfg.get("DB_NAME", ""))

        mysql_p = cfg.get("mysql_path", "") or self._detect_mysql_path()
        mysqldump_p = cfg.get("mysqldump_path", "") or self._detect_mysqldump_path()
        auto_dir = cfg.get("auto_backup_path", "") or self._default_auto_dir()
        manual_dir = cfg.get("manual_backup_path", "") or self._default_manual_dir()

        self.ed_mysql.setText(mysql_p)
        self.ed_mysqldump.setText(mysqldump_p)
        self.ed_auto_dir.setText(auto_dir)
        self.ed_manual_dir.setText(manual_dir)

    def _collect(self) -> Dict[str, str]:
        return {
            "DB_HOST": self.ed_host.text().strip(),
            "DB_PORT": self.ed_port.text().strip(),
            "DB_USER": self.ed_user.text().strip(),
            "DB_PASS": self.ed_pass.text(),  # 允许空格
            "DB_NAME": self.ed_name.text().strip(),
            "mysql_path": self.ed_mysql.text().strip(),
            "mysqldump_path": self.ed_mysqldump.text().strip(),
            "auto_backup_path": self.ed_auto_dir.text().strip(),
            "manual_backup_path": self.ed_manual_dir.text().strip(),
        }

    # ------------------------ 帮助函数 ------------------------

    @staticmethod
    def _is_windows() -> bool:
        return platform.system().lower().startswith("win")

    @staticmethod
    def _label(text: str) -> QLabel:
        from PyQt5.QtCore import Qt
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lab.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        return lab

    def _add_form_row(self, grid: QGridLayout, row: int, label_text: str, field_widget: QWidget):
        grid.addWidget(self._label(label_text), row, 0)
        grid.addWidget(field_widget, row, 1)

    @staticmethod
    def _mk_row_with_browse(editor: QLineEdit, browse_btn: QPushButton) -> QWidget:
        roww = QWidget()
        h = QHBoxLayout(roww)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(editor, 1)
        h.addWidget(browse_btn, 0)
        return roww

    @staticmethod
    def _tune_grid(grid: QGridLayout):
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 7)

    @staticmethod
    def _default_auto_dir() -> str:
        return _DEFAULTS["auto_backup_path"]

    @staticmethod
    def _default_manual_dir() -> str:
        return _DEFAULTS["manual_backup_path"]

    @classmethod
    def _detect_backup_dirs(cls) -> tuple[str, str]:
        return cls._default_auto_dir(), cls._default_manual_dir()

    @classmethod
    def _detect_mysql_path(cls) -> str:
        cand = shutil.which("mysql")
        if cand:
            return cand
        if cls._is_windows():
            roots = [
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            ]
            for root in roots:
                for base in (root / "MySQL", root / "MariaDB"):
                    if not base.exists():
                        continue
                    for p in base.rglob("mysql.exe"):
                        return str(p)
        return ""

    @classmethod
    def _detect_mysqldump_path(cls) -> str:
        cand = shutil.which("mysqldump")
        if cand:
            return cand
        if cls._is_windows():
            roots = [
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            ]
            for root in roots:
                for base in (root / "MySQL", root / "MariaDB"):
                    if not base.exists():
                        continue
                    for p in base.rglob("mysqldump.exe"):
                        return str(p)
        return ""

if __name__ == "__main__":
    # 运行应用
    app = QApplication(sys.argv)
    window = ConfigEditorDialog()
    window.show()
    sys.exit(app.exec())

