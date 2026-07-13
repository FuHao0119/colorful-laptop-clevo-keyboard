# 这个分支做了什么

本分支具体解决了 ` 七彩虹隐星 P15 2024 游戏本 ` 官方无linux驱动、驱动限制加载以及新型号背光无法注册的问题，完美实现了对键盘RGB灯效的控制。

# 硬件与软件环境

* **笔记本型号**：七彩虹 隐星 P15 2024 版 (Colorful P15 24)
* **主板模具**：Clevo V250RND 准系统
* **系统环境**：Fedora Linux (已测试 Fedora 44, 内核 7.1.x, x86_64)
* **控制方式**：通过修改后的 `tuxedo-keyboard` 驱动，生成标准 `/sys/class/leds/rgb:kbd_backlight` 接口，并配合 Python 脚本控制效果。

> 目前只在这个环境做过测试，其他环境能不能用还不清楚

# 如何使用

## 使用可执行程序
如果你是使用dnf包管理器的发行版，那么可以直接使用可执行程序 `releases/colorful-keyboard`

```bash
chmod +x colorful-keyboard
```
双击执行程序，在程序中安装环境和驱动包

> 如果安装不上环境，可以手动按照下面的方法安装驱动包，程序能自动识别

## 手动安装安装驱动包
* 如果你是RedHat系的发行版，可以手动安装 `releases` 下的驱动包:
```bash
sudo dnf install ./tuxedo-keyboard-3.2.10-1.noarch.rpm
```
或者你也可以自己编译:
```bash
make clean
make package-rpm
sudo dnf install ./tuxedo-keyboard-3.2.10-1.noarch.rpm
```
* 如果你是debain系的发行版，可以自己编译:
```bash
make clean
make package-deb
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
# 呼吸灯效
./light-control-scripts/kbd_light_show.py --mode breath --color blue --speed 1.2
# 静态灯光
./light-control-scripts/kbd_light_show.py --mode solid --color cyan --brightness 180
```

# 编译与打包
在开始编译前，需要确保系统安装了编译链工具以及对应当前内核的开发头文件：
```bash
# Fedora / RHEL
sudo dnf install -y make gcc rpm-build dkms kernel-devel-$(uname -r)

# Ubuntu / Debian
sudo apt install -y make gcc dpkg-dev dkms linux-headers-$(uname -r)
```

* 构建驱动分发包
根目录下设计了规范的自动化 Makefile，可以直接调用底层包管理器规范：

编译并打包 RPM 安装包 (Fedora/CentOS/openSUSE):
```bash
make package-rpm
```
这会在根目录下生成 `tuxedo-keyboard-3.2.10-1.noarch.rpm`，并自动打包 dkms 配置。

编译并打包 DEB 安装包 (Ubuntu/Debian/Mint):
```bash
make package-deb
```
这会在根目录下生成对应的 `.deb` 安装包。

清理编译缓存:
```bash
make clean
```

* GUI 控制管理器开发与打包
图形管理程序基于 **Python 3** 与 **PyQt5** 编写，支持系统托盘缩入、自启动 Systemd 服务托管、实时灯效动画预览以及免依赖的一键驱动部署编译。

开发 GUI 需要以下运行库支持：
```bash
# 安装 PyQt5 界面库
pip install PyQt5
```

在项目根目录下调用 python 执行 GUI 脚本：
```bash
python3 gui/main.py
```
Daemon 模式：在被 Systemd 自启动服务调用时，后台会自动带上 `--daemon` 参数启动为无界面的纯逻辑守护循环，通过读取 `~/.config/colorful-keyboard/config.json` 的配置在后台控制键盘写值。

GUI 与 Daemon 独占控制：在运行 GUI 时，它会主动通过 `systemctl --user stop` 挂起后台服务，防止多重写值造成频闪；GUI 退出时，会自动重新拉起后台服务恢复托管。

```bash
pip install pyinstaller
```
进入 `gui` 目录，执行以下打包指令：
```bash
cd gui
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name="colorful-keyboard" \
    --add-data "../src:src" \
    --add-data "../Makefile:." \
    --add-data "../rpm:rpm" \
    --add-data "../src_pkg:src_pkg" \
    --add-data "../dkms.conf:." \
    --add-data "../tuxedo_keyboard.conf:." \
    --add-data "../LICENSE:." \
    --add-data "icon.jpg:." \
    main.py
```

打包完成后，可以在 `gui/dist/` 目录下找到编译好的 `colorful-keyboard` 单文件绿色程序，可直接拷贝到任何同架构的 Linux 系统上双击运行并分发。


* 获取笔记本背光规格码
如果您在适配新的笔记本模具，可以开启内核动态调试参数来捕获硬件上报的背光规格码：
```bash
# 卸载冲突的旧模块
sudo modprobe -r tuxedo_keyboard clevo_wmi clevo_acpi

# 重新载入并启用调试输出
sudo modprobe tuxedo_keyboard dyndbg=+p
sudo modprobe clevo_wmi
sudo modprobe clevo_acpi

# 查看内核日志（寻找"backlight type"相关输出）
sudo dmesg -w | grep -E "tuxedo|clevo"
```