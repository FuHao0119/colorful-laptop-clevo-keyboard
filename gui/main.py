#!/usr/bin/env python3
import sys
import os
import time
import math
import glob
import json
import argparse
import signal
import subprocess
import pty
import select
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QTabWidget,
    QTextEdit, QInputDialog, QMessageBox, QGroupBox, QGridLayout, QColorDialog,
    QLineEdit, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

# Configurations path
CONFIG_DIR = os.path.expanduser('~/.config/colorful-keyboard')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
SYSTEMD_SERVICE_FILE = os.path.expanduser('~/.config/systemd/user/colorful-keyboard.service')

# Global service state and exit handling
SERVICE_WAS_RUNNING = False

def cleanup_service():
    global SERVICE_WAS_RUNNING
    print(f"[GUI Log] cleanup_service() 被触发. SERVICE_WAS_RUNNING = {SERVICE_WAS_RUNNING}", file=sys.stderr)
    if SERVICE_WAS_RUNNING:
        SERVICE_WAS_RUNNING = False
        print("[GUI Log] 正在尝试拉起后台自启动服务...", file=sys.stderr)
        res = subprocess.run(['systemctl', '--user', 'start', 'colorful-keyboard.service'], capture_output=True)
        print(f"[GUI Log] systemctl start 返回状态码: {res.returncode}", file=sys.stderr)

import atexit
atexit.register(cleanup_service)

def handle_os_signal(signum, frame):
    print(f"[GUI Log] 收到操作系统终止信号 {signum}", file=sys.stderr)
    cleanup_service()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_os_signal)
signal.signal(signal.SIGINT, handle_os_signal)

# Predefined colors
COLORS = {
    '红 (Red)': (255, 0, 0),
    '绿 (Green)': (0, 255, 0),
    '蓝 (Blue)': (0, 0, 255),
    '黄 (Yellow)': (255, 255, 0),
    '紫 (Purple)': (255, 0, 255),
    '青 (Cyan)': (0, 255, 255),
    '白 (White)': (255, 255, 255),
    '橙 (Orange)': (255, 127, 0),
    '粉 (Pink)': (255, 192, 203),
}

# Stylesheet for Catppuccin Mocha UI
STYLE = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #181825;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #313244;
    color: #a6adc8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #181825;
    color: #cba6f7;
    border-bottom: 2px solid #cba6f7;
}
QTabBar::tab:hover {
    background-color: #45475a;
    color: #cdd6f4;
}
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: #1e1e2e;
    font-weight: bold;
    color: #f5c2e7;
}
QPushButton {
    background-color: #89b4fa;
    color: #11111b;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton:pressed {
    background-color: #74c7ec;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #585b70;
}
QPushButton#dangerButton {
    background-color: #f38ba8;
}
QPushButton#dangerButton:hover {
    background-color: #eba0ac;
}
QSlider::groove:horizontal {
    border: 1px solid #313244;
    height: 6px;
    background: #313244;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #cba6f7;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #f5e0dc;
    border: 1px solid #f5e0dc;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}
QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 25px 6px 12px;
    color: #cdd6f4;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border: 0px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    selection-background-color: #45475a;
    selection-color: #cba6f7;
}
QTextEdit {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #a6e3a1;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #a6e3a1;
    image: url(checked.png); /* Fallback to standard check if no image */
}
QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #cba6f7;
}
QLabel#statusOk {
    color: #a6e3a1;
    font-weight: bold;
}
QLabel#statusError {
    color: #f38ba8;
    font-weight: bold;
}
QDialog {
    background-color: #1e1e2e;
    border: 1px solid #313244;
}
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
    color: #cdd6f4;
}
"""

# Keyboard driver controller helper
class KeyboardBacklight:
    def __init__(self):
        self.led_dirs = glob.glob('/sys/class/leds/*kbd_backlight*')
        self.legacy_mode = False
        if not self.led_dirs:
            if os.path.exists('/sys/devices/platform/tuxedo_keyboard'):
                self.legacy_mode = True

    def is_available(self):
        return len(self.led_dirs) > 0 or self.legacy_mode

    def set_color(self, r, g, b, brightness=255):
        if self.legacy_mode:
            hex_color = f"0x{r:02X}{g:02X}{b:02X}"
            for name in ['color', 'color_left', 'color_center', 'color_right']:
                path = f'/sys/devices/platform/tuxedo_keyboard/{name}'
                if os.path.exists(path):
                    try:
                        with open(path, 'w') as f:
                            f.write(hex_color + '\n')
                    except IOError:
                        pass
            state_path = '/sys/devices/platform/tuxedo_keyboard/state'
            if os.path.exists(state_path):
                try:
                    with open(state_path, 'w') as f:
                        f.write('1\n' if brightness > 0 else '0\n')
                except IOError:
                    pass
        else:
            for led_dir in self.led_dirs:
                # Brightness
                br_path = os.path.join(led_dir, 'brightness')
                if os.path.exists(br_path):
                    try:
                        with open(br_path, 'w') as f:
                            f.write(str(brightness) + '\n')
                    except IOError:
                        pass
                
                # Colors
                intensity_path = os.path.join(led_dir, 'multi_intensity')
                index_path = os.path.join(led_dir, 'multi_index')
                if os.path.exists(intensity_path):
                    order = ['red', 'green', 'blue']
                    if os.path.exists(index_path):
                        try:
                            with open(index_path, 'r') as f:
                                order = f.read().strip().split()
                        except IOError:
                            pass
                    val_map = {'red': r, 'green': g, 'blue': b}
                    vals = [str(val_map.get(c, 0)) for c in order]
                    try:
                        with open(intensity_path, 'w') as f:
                            f.write(' '.join(vals) + '\n')
                    except IOError:
                        pass

# Background Thread for Animation Loops
class BacklightThread(QThread):
    def __init__(self, backlight):
        super().__init__()
        self.backlight = backlight
        self.running = False
        self.mode = 'rainbow'
        self.color = (255, 255, 255)
        self.speed = 1.0
        self.brightness = 255

    def update_params(self, mode, color, speed, brightness):
        self.mode = mode
        self.color = color
        self.speed = speed
        self.brightness = brightness

    def run(self):
        self.running = True
        h = 0.0
        breath_t = 0.0
        strobe_state = True
        color_keys = list(COLORS.keys())
        cycle_idx = 0
        cycle_fade_step = 0

        while self.running:
            if not self.backlight.is_available():
                self.msleep(1000)
                continue

            speed_val = max(0.1, self.speed)

            if self.mode == 'off':
                self.backlight.set_color(0, 0, 0, 0)
                self.msleep(100)
            elif self.mode == 'solid':
                r, g, b = self.color
                self.backlight.set_color(r, g, b, self.brightness)
                self.msleep(100)
            elif self.mode == 'rainbow':
                # Convert HSV to RGB
                r, g, b = self.hsv_to_rgb(h, 1.0, 1.0)
                self.backlight.set_color(r, g, b, self.brightness)
                h += 0.005
                if h > 1.0: h -= 1.0
                self.msleep(int(20 / speed_val))
            elif self.mode == 'breath':
                factor = (math.sin(breath_t) + 1.0) / 2.0
                r, g, b = self.color
                curr_r = int(r * factor)
                curr_g = int(g * factor)
                curr_b = int(b * factor)
                curr_brightness = int(self.brightness * (0.2 + 0.8 * factor))
                self.backlight.set_color(curr_r, curr_g, curr_b, curr_brightness)
                breath_t += 0.03
                if breath_t > 2 * math.pi:
                    breath_t -= 2 * math.pi
                self.msleep(int(20 / speed_val))
            elif self.mode == 'strobe':
                if strobe_state:
                    r, g, b = self.color
                    self.backlight.set_color(r, g, b, self.brightness)
                else:
                    self.backlight.set_color(0, 0, 0, 0)
                strobe_state = not strobe_state
                self.msleep(int(100 / speed_val))
            elif self.mode == 'cycle':
                # Cycle through predefined colors
                curr_color_name = color_keys[cycle_idx]
                r, g, b = COLORS[curr_color_name]
                steps = 50
                if cycle_fade_step < steps // 2:
                    f = (steps // 2 - cycle_fade_step) / (steps // 2)
                    self.backlight.set_color(int(r * (1 - f)), int(g * (1 - f)), int(b * (1 - f)), self.brightness)
                else:
                    f = (cycle_fade_step - steps // 2) / (steps // 2)
                    self.backlight.set_color(int(r * f), int(g * f), int(b * f), self.brightness)
                
                cycle_fade_step += 1
                if cycle_fade_step > steps:
                    cycle_fade_step = 0
                    cycle_idx = (cycle_idx + 1) % len(color_keys)
                self.msleep(int(20 / speed_val))

    def stop(self):
        self.running = False
        self.wait()

    def hsv_to_rgb(self, h, s, v):
        if s == 0.0: return v, v, v
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        if i == 0: return int(v*255), int(t*255), int(p*255)
        if i == 1: return int(q*255), int(v*255), int(p*255)
        if i == 2: return int(p*255), int(v*255), int(t*255)
        if i == 3: return int(p*255), int(q*255), int(v*255)
        if i == 4: return int(t*255), int(p*255), int(v*255)
        if i == 5: return int(v*255), int(p*255), int(q*255)

# Thread for running installation commands via su
class InstallThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, password):
        super().__init__()
        self.password = password

    def run(self):
        self.log_signal.emit(">>> 开始执行驱动编译与部署流程...")
        if getattr(sys, 'frozen', False):
            repo_dir = sys._MEIPASS
        else:
            repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        rpm_file = os.path.join(repo_dir, 'tuxedo-keyboard-3.2.10-1.noarch.rpm')

        commands = (
            "echo '>>> 1. 正在检查并自动安装构建驱动所需的系统级依赖包 (make, gcc, rpm-build, dkms, kernel-devel)...' && "
            "dnf install -y make gcc rpm-build dkms && "
            "(dnf install -y kernel-devel-$(uname -r) || dnf install -y kernel-devel) && "
            "if [ ! -d /lib/modules/$(uname -r)/build ]; then "
            "  echo -e '\\n【错误】编译依赖校验失败：未找到当前运行内核的开发文件目录 /lib/modules/'$(uname -r)'/build。' >&2; "
            "  echo -e '提示：您的运行内核与安装的 kernel-devel 版本不匹配，请运行 [sudo dnf update kernel] 并重启电脑后再试！\\n' >&2; "
            "  exit 1; "
            "fi && "
            f"echo '>>> 2. 正在清理并打包本地驱动源码 (在 {repo_dir} 中)...' && "
            f"cd '{repo_dir}' && "
            "make clean && "
            "make package-rpm && "
            f"echo '>>> 3. 正在安装并配置编译出的 RPM 驱动包...' && "
            f"rpm -Uvh --force '{rpm_file}' && "
            "echo '>>> 4. 正在加载内核驱动模块并配置自动加载与权限规则...' && "
            "modprobe tuxedo_keyboard dyndbg=+p && "
            "modprobe uniwill_wmi && modprobe clevo_wmi && modprobe clevo_acpi && modprobe tuxedo_io && "
            "echo -e 'tuxedo_keyboard\\nuniwill_wmi\\nclevo_wmi\\nclevo_acpi\\ntuxedo_io' > /etc/modules-load.d/tuxedo_keyboard.conf && "
            "echo 'SUBSYSTEM==\"leds\", KERNEL==\"*kbd_backlight*\", RUN+=\"/bin/sh -c '\''chmod -R a+w /sys/class/leds/%k'\''\"' > /etc/udev/rules.d/99-kbd-backlight.rules && "
            "udevadm control --reload-rules && udevadm trigger"
        )
        self.log_signal.emit(">>> 正在启动 root 交互式终端部署流程...")

        try:
            status = self.run_su(commands)
            if status == 0:
                self.finished_signal.emit(True, "驱动编译、打包与安装部署成功！\n请测试灯光控制面板。")
            else:
                self.finished_signal.emit(False, f"部署命令执行失败，状态码: {status}，请检查 root 密码或查看日志输出。")
        except Exception as e:
            self.finished_signal.emit(False, f"部署过程发生异常: {e}")

    def run_su(self, command):
        pid, fd = pty.fork()
        if pid == 0:
            # Child process
            os.execvp('su', ['su', '-', '-c', command])
        else:
            # Parent process
            buffer = b""
            prompt_received = False
            while True:
                r, w, x = select.select([fd], [], [], 120)  # DKMS build can take up to 2 mins
                if not r:
                    self.log_signal.emit(">>> 进程响应超时！")
                    break
                try:
                    data = os.read(fd, 1024)
                except OSError:
                    break
                if not data:
                    break
                buffer += data
                # Send out logs to UI
                text_chunk = data.decode('utf-8', errors='ignore')
                self.log_signal.emit(text_chunk.strip())

                # Detect su password prompt (Chinese or English)
                if b"Password" in data or b"password" in data or b"\xe5\xaf\x86\xe7\xa0\x81" in data:
                    if not prompt_received:
                        os.write(fd, self.password.encode() + b'\n')
                        prompt_received = True
                        buffer = b""
            try:
                _, status = os.waitpid(pid, 0)
                return status
            except ChildProcessError:
                return 0

# Main GUI Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("七彩虹隐星键盘背光管理器")
        self.resize(650, 480)
        self.setStyleSheet(STYLE)
        
        self.backlight = KeyboardBacklight()
        self.config = {
            'mode': 'rainbow',
            'color': (255, 255, 255),
            'speed': 1.0,
            'brightness': 255
        }
        self.load_config()

        global SERVICE_WAS_RUNNING
        # Check if the systemd user service is running, and temporarily stop it to avoid conflicts
        res = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'colorful-keyboard.service'])
        if res.returncode == 0:
            SERVICE_WAS_RUNNING = True
            print("[GUI Log] 检测到后台服务正在运行，正在暂停它以防止写冲突...", file=sys.stderr)
            subprocess.run(['systemctl', '--user', 'stop', 'colorful-keyboard.service'], capture_output=True)
        else:
            print(f"[GUI Log] 检测到后台服务未运行 (状态码: {res.returncode})", file=sys.stderr)

        # Timer to let Python process OS signals (like SIGTERM/SIGINT) quickly
        self.sig_timer = QTimer()
        self.sig_timer.start(500)
        self.sig_timer.timeout.connect(lambda: None)

        self.anim_thread = BacklightThread(self.backlight)
        self.anim_thread.update_params(
            self.config['mode'],
            self.config['color'],
            self.config['speed'],
            self.config['brightness']
        )
        self.anim_thread.start()

        self.init_ui()
        self.check_status()

        # Regular timer to check driver status in background
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status)
        self.status_timer.start(5000)

        # System Tray Icon Setup
        self.allow_exit = False
        self.init_tray_icon()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Title
        title_label = QLabel("七彩虹 隐星 P15 键盘灯光管理器")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.init_control_tab()
        self.init_status_tab()
        self.init_settings_tab()

    def init_control_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Mode Box
        mode_group = QGroupBox("灯光模式选择")
        mode_layout = QGridLayout(mode_group)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "彩虹循环 (Rainbow)", 
            "呼吸灯效 (Breathing)", 
            "循环渐变 (Color Cycle)", 
            "爆闪灯效 (Strobe)", 
            "静态单色 (Solid)", 
            "关闭背光 (Off)"
        ])
        mode_map = {
            'rainbow': 0, 'breath': 1, 'cycle': 2, 'strobe': 3, 'solid': 4, 'off': 5
        }
        self.combo_mode.setCurrentIndex(mode_map.get(self.config['mode'], 0))
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(QLabel("选择效果："), 0, 0)
        mode_layout.addWidget(self.combo_mode, 0, 1)
        layout.addWidget(mode_group)

        # Parameters Box
        param_group = QGroupBox("效果参数调节")
        param_layout = QGridLayout(param_group)

        # Brightness ComboBox
        self.combo_brightness = QComboBox()
        self.combo_brightness.addItems([
            "0% (关闭)", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100% (最亮)"
        ])
        brightness_options = [0, 25, 51, 76, 102, 127, 153, 178, 204, 230, 255]
        b_closest = min(range(len(brightness_options)), key=lambda i: abs(brightness_options[i] - self.config['brightness']))
        self.combo_brightness.setCurrentIndex(b_closest)
        self.combo_brightness.currentIndexChanged.connect(self.on_param_changed)
        param_layout.addWidget(QLabel("最大亮度："), 0, 0)
        param_layout.addWidget(self.combo_brightness, 0, 1)

        # Speed ComboBox
        self.combo_speed = QComboBox()
        self.combo_speed.addItems([
            "0.2x (极慢)", "0.5x (较慢)", "1.0x (标准)", "1.5x (较快)", "2.0x (快速)", "3.0x (极快)", "5.0x (超快)"
        ])
        speed_options = [0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        s_closest = min(range(len(speed_options)), key=lambda i: abs(speed_options[i] - self.config['speed']))
        self.combo_speed.setCurrentIndex(s_closest)
        self.combo_speed.currentIndexChanged.connect(self.on_param_changed)
        param_layout.addWidget(QLabel("动画速度："), 1, 0)
        param_layout.addWidget(self.combo_speed, 1, 1)
        layout.addWidget(param_group)

        # Color Box
        self.color_group = QGroupBox("颜色调整")
        color_layout = QHBoxLayout(self.color_group)

        self.btn_pick_color = QPushButton("自定义调色盘")
        self.btn_pick_color.clicked.connect(self.on_pick_color)
        color_layout.addWidget(self.btn_pick_color)

        self.combo_presets = QComboBox()
        self.combo_presets.addItem("选择预设颜色...")
        for name in COLORS.keys():
            self.combo_presets.addItem(name)
        self.combo_presets.currentIndexChanged.connect(self.on_preset_changed)
        color_layout.addWidget(self.combo_presets)

        layout.addWidget(self.color_group)
        self.update_color_ui_visibility()

        layout.addStretch()
        self.tabs.addTab(tab, "灯光特效控制")

    def init_status_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Environment Info
        env_group = QGroupBox("系统与驱动环境")
        env_layout = QGridLayout(env_group)

        # Manufacturer info
        sys_vendor = self.read_sys_file('/sys/class/dmi/id/sys_vendor')
        board_name = self.read_sys_file('/sys/class/dmi/id/board_name')
        env_layout.addWidget(QLabel("主板厂商："), 0, 0)
        env_layout.addWidget(QLabel(sys_vendor if sys_vendor else "未知"), 0, 1)
        env_layout.addWidget(QLabel("主板型号："), 1, 0)
        env_layout.addWidget(QLabel(board_name if board_name else "未知"), 1, 1)

        # Driver load status
        self.lbl_driver_status = QLabel("检测中...")
        env_layout.addWidget(QLabel("背光驱动状态："), 2, 0)
        env_layout.addWidget(self.lbl_driver_status, 2, 1)

        layout.addWidget(env_group)

        # Installer Box
        self.install_group = QGroupBox("驱动管理与自助部署")
        ins_layout = QVBoxLayout(self.install_group)
        self.lbl_install_hint = QLabel("如未检测到背光驱动，可使用下方安装向导自动编译和配置。")
        self.lbl_install_hint.setWordWrap(True)
        ins_layout.addWidget(self.lbl_install_hint)

        self.btn_install = QPushButton("一键自动安装/修复驱动")
        self.btn_install.clicked.connect(self.on_install_driver)
        ins_layout.addWidget(self.btn_install)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("安装日志将实时输出在此处...")
        ins_layout.addWidget(self.log_output)

        layout.addWidget(self.install_group)
        self.tabs.addTab(tab, "环境与驱动状态")

    def init_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        settings_group = QGroupBox("软件设置")
        set_layout = QVBoxLayout(settings_group)

        self.chk_autostart = QCheckBox("开机自动登录后静默后台启动灯效")
        self.chk_autostart.setChecked(os.path.exists(SYSTEMD_SERVICE_FILE))
        self.chk_autostart.toggled.connect(self.on_autostart_toggled)
        set_layout.addWidget(self.chk_autostart)

        layout.addWidget(settings_group)
        
        info_group = QGroupBox("关于")
        info_layout = QVBoxLayout(info_group)
        info_lbl = QLabel(
            "针对七彩虹隐星 P15 2024 (蓝天公模) 游戏本定制。\n"
            "移除了 tuxedo-keyboard 驱动的 DMI 限制，并添加 0x26 背光类型支持。\n"
            "驱动源码仓库：SoftWareTask/colorful-laptop-clevo-keyboard"
        )
        info_lbl.setWordWrap(True)
        info_layout.addWidget(info_lbl)
        layout.addWidget(info_group)

        layout.addStretch()
        self.tabs.addTab(tab, "偏好与关于")

    # Logics
    def read_sys_file(self, path):
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return f.read().strip()
            except IOError:
                pass
        return None

    def check_status(self):
        available = self.backlight.is_available()
        if available:
            self.lbl_driver_status.setText("运行正常 (已就绪)")
            self.lbl_driver_status.setObjectName("statusOk")
            self.btn_install.setText("重新安装/修复驱动")
            self.btn_install.setObjectName("")
        else:
            self.lbl_driver_status.setText("未加载/未安装 (未就绪)")
            self.lbl_driver_status.setObjectName("statusError")
            self.btn_install.setText("自动安装键盘驱动")
            self.btn_install.setObjectName("dangerButton")
        self.lbl_driver_status.style().unpolish(self.lbl_driver_status)
        self.lbl_driver_status.style().polish(self.lbl_driver_status)
        self.btn_install.style().unpolish(self.btn_install)
        self.btn_install.style().polish(self.btn_install)

    def update_color_ui_visibility(self):
        mode = self.combo_mode.currentIndex()
        # show color box only for Breath, Strobe, Solid
        if mode in [1, 3, 4]:
            self.color_group.setVisible(True)
        else:
            self.color_group.setVisible(False)

    def on_mode_changed(self):
        mode_idx = self.combo_mode.currentIndex()
        modes = ['rainbow', 'breath', 'cycle', 'strobe', 'solid', 'off']
        self.config['mode'] = modes[mode_idx]
        self.update_color_ui_visibility()
        self.apply_settings()

    def on_param_changed(self):
        brightness_options = [0, 25, 51, 76, 102, 127, 153, 178, 204, 230, 255]
        speed_options = [0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        
        b_idx = self.combo_brightness.currentIndex()
        s_idx = self.combo_speed.currentIndex()
        
        self.config['brightness'] = brightness_options[b_idx]
        self.config['speed'] = speed_options[s_idx]
        
        self.apply_settings()

    def on_preset_changed(self):
        idx = self.combo_presets.currentIndex()
        if idx > 0:
            name = list(COLORS.keys())[idx - 1]
            self.config['color'] = COLORS[name]
            self.apply_settings()

    def on_pick_color(self):
        curr_color = QColor(*self.config['color'])
        color = QColorDialog.getColor(curr_color, self, "选择自定义颜色")
        if color.isValid():
            self.config['color'] = (color.red(), color.green(), color.blue())
            self.combo_presets.setCurrentIndex(0)
            self.apply_settings()

    def apply_settings(self):
        self.anim_thread.update_params(
            self.config['mode'],
            self.config['color'],
            self.config['speed'],
            self.config['brightness']
        )
        self.save_config()

    def save_config(self):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except IOError:
            pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception:
                pass

    def on_autostart_toggled(self, checked):
        global SERVICE_WAS_RUNNING
        print(f"[GUI Log] on_autostart_toggled 被调用，选中状态为: {checked}", file=sys.stderr)
        if checked:
            os.makedirs(os.path.dirname(SYSTEMD_SERVICE_FILE), exist_ok=True)
            script_path = os.path.abspath(__file__)
            content = f"""[Unit]
Description=Colorful Laptop Keyboard Backlight Daemon
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {script_path} --daemon
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
            try:
                with open(SYSTEMD_SERVICE_FILE, 'w') as f:
                    f.write(content)
                subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True)
                subprocess.run(['systemctl', '--user', 'enable', 'colorful-keyboard.service'], capture_output=True)
                # Defer starting the service until the GUI closes to prevent double-write conflicts
                SERVICE_WAS_RUNNING = True
                print("[GUI Log] 自启动服务已启用，设置 SERVICE_WAS_RUNNING = True", file=sys.stderr)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法启用自启动服务: {e}")
        else:
            if os.path.exists(SYSTEMD_SERVICE_FILE):
                try:
                    subprocess.run(['systemctl', '--user', 'stop', 'colorful-keyboard.service'], capture_output=True)
                    subprocess.run(['systemctl', '--user', 'disable', 'colorful-keyboard.service'], capture_output=True)
                    os.remove(SYSTEMD_SERVICE_FILE)
                    subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True)
                    SERVICE_WAS_RUNNING = False
                    print("[GUI Log] 自启动服务已禁用，设置 SERVICE_WAS_RUNNING = False", file=sys.stderr)
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"无法关闭自启动服务: {e}")

    def on_install_driver(self):
        passwd, ok = QInputDialog.getText(
            self, "输入Root密码", 
            "检测到本操作需要系统超级用户权限。\n请输入root账户密码以启动安装部署：",
            QLineEdit.Password
        )
        if ok and passwd:
            self.log_output.clear()
            self.btn_install.setEnabled(False)
            self.thread_install = InstallThread(passwd)
            self.thread_install.log_signal.connect(self.on_install_log)
            self.thread_install.finished_signal.connect(self.on_install_finished)
            self.thread_install.start()

    def on_install_log(self, text):
        clean_text = text.strip()
        # If the log is just dots (progress output), append inline to the end of the text
        if clean_text and all(c == '.' for c in clean_text):
            cursor = self.log_output.textCursor()
            cursor.movePosition(cursor.End)
            cursor.insertText(text)
        else:
            self.log_output.append(text)
        self.log_output.ensureCursorVisible()

    def on_install_finished(self, success, message):
        self.btn_install.setEnabled(True)
        if success:
            QMessageBox.information(self, "安装成功", message)
            self.backlight = KeyboardBacklight() # Re-init paths
            self.anim_thread.backlight = self.backlight
            self.check_status()
        else:
            QMessageBox.critical(self, "安装失败", message)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Load keyboard icon. Use the local custom generated icon if present.
        if getattr(sys, 'frozen', False):
            gui_dir = sys._MEIPASS
        else:
            gui_dir = os.path.dirname(os.path.abspath(__file__))
        custom_icon_path = os.path.join(gui_dir, 'icon.jpg')
        if os.path.exists(custom_icon_path):
            icon = QIcon(custom_icon_path)
            self.setWindowIcon(icon)  # Set QMainWindow window icon
        else:
            icon = QIcon.fromTheme("input-keyboard")
            if icon.isNull():
                icon = QIcon.fromTheme("keyboard")
            if icon.isNull():
                # Fallback to drawn mauve square
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor("#cba6f7"))
                icon = QIcon(pixmap)
            
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("七彩虹键盘背光管理器")

        # Tray Menu
        self.tray_menu = QMenu()
        
        show_action = QAction("打开主面板", self)
        show_action.triggered.connect(self.show_and_raise)
        self.tray_menu.addAction(show_action)

        self.tray_menu.addSeparator()

        off_action = QAction("关闭背光", self)
        off_action.triggered.connect(self.turn_off_backlight)
        self.tray_menu.addAction(off_action)

        exit_action = QAction("退出程序", self)
        exit_action.triggered.connect(self.exit_app)
        self.tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def turn_off_backlight(self):
        self.combo_mode.setCurrentIndex(5)  # Index 5 is Off (关闭背光)

    def exit_app(self):
        self.allow_exit = True
        self.close()

    def on_tray_activated(self, reason):
        if reason in [QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick]:
            if self.isVisible():
                self.hide()
            else:
                self.show_and_raise()

    def closeEvent(self, event):
        if getattr(self, 'allow_exit', False):
            self.anim_thread.stop()
            super().closeEvent(event)
        else:
            if self.tray_icon.isVisible():
                self.hide()
                event.ignore()
                if not getattr(self, 'hide_hint_shown', False):
                    self.tray_icon.showMessage(
                        "背光管理器",
                        "程序已最小化到系统托盘。可在右键托盘菜单中选择“退出程序”彻底退出。",
                        QSystemTrayIcon.Information,
                        3000
                    )
                    self.hide_hint_shown = True
            else:
                self.anim_thread.stop()
                super().closeEvent(event)

# Daemon loop (No GUI)
def run_daemon(backlight):
    config = {
        'mode': 'rainbow',
        'color': (255, 255, 255),
        'speed': 1.0,
        'brightness': 255
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config.update(json.load(f))
        except Exception:
            pass

    # Basic signal handling to gracefully restore white kbd light
    def daemon_signal_handler(sig, frame):
        try:
            backlight.set_color(255, 255, 255, 255)
        except Exception:
            pass
        sys.exit(0)
    
    signal.signal(signal.SIGINT, daemon_signal_handler)
    signal.signal(signal.SIGTERM, daemon_signal_handler)

    h = 0.0
    breath_t = 0.0
    strobe_state = True
    color_keys = list(COLORS.keys())
    cycle_idx = 0
    cycle_fade_step = 0

    while True:
        if not backlight.is_available():
            time.sleep(5)
            continue
        
        mode = config['mode']
        color = config['color']
        speed = max(0.1, config['speed'])
        brightness = config['brightness']

        if mode == 'off':
            backlight.set_color(0, 0, 0, 0)
            time.sleep(0.5)
        elif mode == 'solid':
            backlight.set_color(color[0], color[1], color[2], brightness)
            time.sleep(0.5)
        elif mode == 'rainbow':
            # HSV to RGB
            # Simple inlined hsv_to_rgb
            s, v = 1.0, 1.0
            i = int(h * 6.0)
            f = (h * 6.0) - i
            p = v * (1.0 - s)
            q = v * (1.0 - s * f)
            t = v * (1.0 - s * (1.0 - f))
            i = i % 6
            if i == 0: r, g, b = int(v*255), int(t*255), int(p*255)
            elif i == 1: r, g, b = int(q*255), int(v*255), int(p*255)
            elif i == 2: r, g, b = int(p*255), int(v*255), int(t*255)
            elif i == 3: r, g, b = int(p*255), int(q*255), int(v*255)
            elif i == 4: r, g, b = int(t*255), int(p*255), int(v*255)
            else: r, g, b = int(v*255), int(p*255), int(q*255)
            
            backlight.set_color(r, g, b, brightness)
            h += 0.005
            if h > 1.0: h -= 1.0
            time.sleep(0.02 / speed)
        elif mode == 'breath':
            factor = (math.sin(breath_t) + 1.0) / 2.0
            curr_brightness = int(brightness * (0.2 + 0.8 * factor))
            backlight.set_color(int(color[0]*factor), int(color[1]*factor), int(color[2]*factor), curr_brightness)
            breath_t += 0.03
            if breath_t > 2 * math.pi:
                breath_t -= 2 * math.pi
            time.sleep(0.02 / speed)
        elif mode == 'strobe':
            if strobe_state:
                backlight.set_color(color[0], color[1], color[2], brightness)
            else:
                backlight.set_color(0, 0, 0, 0)
            strobe_state = not strobe_state
            time.sleep(0.1 / speed)
        elif mode == 'cycle':
            curr_color_name = color_keys[cycle_idx]
            r, g, b = COLORS[curr_color_name]
            steps = 50
            if cycle_fade_step < steps // 2:
                f = (steps // 2 - cycle_fade_step) / (steps // 2)
                backlight.set_color(int(r * (1 - f)), int(g * (1 - f)), int(b * (1 - f)), brightness)
            else:
                f = (cycle_fade_step - steps // 2) / (steps // 2)
                backlight.set_color(int(r * f), int(g * f), int(b * f), brightness)
            
            cycle_fade_step += 1
            if cycle_fade_step > steps:
                cycle_fade_step = 0
                cycle_idx = (cycle_idx + 1) % len(color_keys)
            time.sleep(0.02 / speed)

        # Refresh configuration check occasionally
        if int(time.time()) % 5 == 0:
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        config.update(json.load(f))
                except Exception:
                    pass

def main():
    parser = argparse.ArgumentParser(description="Colorful Laptop Keyboard Backlight GUI & Daemon Manager")
    parser.add_argument('--daemon', action='store_true', help="Run silently in the background using saved config")
    args = parser.parse_args()

    bl = KeyboardBacklight()

    if args.daemon:
        run_daemon(bl)
    else:
        app = QApplication(sys.argv)
        # Apply dark theme stylesheet
        app.setStyleSheet(STYLE)
        
        # Modify checked checkbox style specifically for better visibility on Linux
        p = app.palette()
        p.setColor(QPalette.Highlight, QColor("#cba6f7"))
        app.setPalette(p)

        win = MainWindow()
        win.show()
        sys.exit(app.exec_())

if __name__ == '__main__':
    main()
