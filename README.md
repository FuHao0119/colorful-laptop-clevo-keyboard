# 这个分支做了什么

本分支具体解决了 ` 七彩虹隐星 P15 2024 游戏本 ` 官方无linux驱动、驱动限制加载以及新型号背光无法注册的问题，完美实现了对键盘RGB灯效的控制。

# 硬件与软件环境

* **笔记本型号**：七彩虹 隐星 P15 2024 版 (Colorful P15 24)
* **主板模具**：Clevo V250RND 准系统
* **系统环境**：Fedora Linux (已测试 Fedora 44, 内核 7.1.x, x86_64)
* **控制方式**：通过修改后的 `tuxedo-keyboard` 驱动，生成标准 `/sys/class/leds/rgb:kbd_backlight` 接口，并配合 Python 脚本控制效果。

> 目前只在这个环境做过测试，其他环境能不能用还不清楚

# 如何使用

### 安装驱动包

如果你是RedHat系的发行版，可以直接使用`releases` 下的驱动包:
```bash
sudo dnf install ./tuxedo-keyboard-3.2.10-1.noarch.rpm
```
或者你也可以自己编译:
```bash
make clean
make package-rpm
sudo dnf install ./tuxedo-keyboard-3.2.10-1.noarch.rpm
```

### 配置开机自动载入与免密控制
为了保证以后开机即用且无需使用 `sudo` 权限控制灯效，请完成以下两项系统配置：
* 创建配置文件，使系统开机自动加载这5个内核模块: 
```bash
sudo tee /etc/modules-load.d/tuxedo_keyboard.conf << 'EOF'
tuxedo_keyboard
uniwill_wmi
clevo_wmi
clevo_acpi
tuxedo_io
EOF
```
* 配置免 Root 控制权限
```bash
sudo tee /etc/udev/rules.d/99-kbd-backlight.rules << 'EOF'
SUBSYSTEM=="leds", KERNEL=="*kbd_backlight*", RUN+="/bin/sh -c 'chmod -R a+w /sys/class/leds/%k'"
EOF

sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 使用python脚本控制灯效
```bash
chmod +x ./light-control-scripts/kbd_light_show.py
```

```bash
# 流光彩虹效果
./light-control-scripts/kbd_light_show.py --mode rainbow --speed 1.5
./light-control-scripts/kbd_light_show.py --mode breath --color blue --speed 1.2
./light-control-scripts/kbd_light_show.py --mode solid --color cyan --brightness 180
```