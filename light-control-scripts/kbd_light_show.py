#!/usr/bin/env python3
import sys
import time
import math
import glob
import argparse
import signal
import os

# Predefined colors
COLORS = {
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'purple': (255, 0, 255),
    'cyan': (0, 255, 255),
    'white': (255, 255, 255),
    'orange': (255, 127, 0),
    'pink': (255, 192, 203),
}

def parse_color(color_str):
    color_str = color_str.lower().strip()
    if color_str in COLORS:
        return COLORS[color_str]
    # Check if hex color
    hex_str = color_str.lstrip('#')
    if len(hex_str) == 6:
        try:
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        f"Invalid color: '{color_str}'. Must be a color name (e.g., 'red', 'blue') or a 6-digit hex string (e.g., 'FF0000')."
    )

class KeyboardBacklight:
    def __init__(self):
        self.led_dirs = glob.glob('/sys/class/leds/*kbd_backlight*')
        self.legacy_mode = False
        if not self.led_dirs:
            if os.path.exists('/sys/devices/platform/tuxedo_keyboard'):
                self.legacy_mode = True
                print("Using legacy tuxedo_keyboard sysfs interface.")
            else:
                print("Error: Keyboard backlight interface not found in /sys/class/leds/ or /sys/devices/platform/tuxedo_keyboard.")
                print("Make sure the tuxedo_keyboard kernel module is loaded.")
                sys.exit(1)
        else:
            print(f"Found backlight interfaces: {', '.join(os.path.basename(d) for d in self.led_dirs)}")

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
                # Set brightness
                br_path = os.path.join(led_dir, 'brightness')
                if os.path.exists(br_path):
                    try:
                        with open(br_path, 'w') as f:
                            f.write(str(brightness) + '\n')
                    except IOError as e:
                        print(f"Error writing to {br_path}: {e}.\nPlease run with sudo or set up udev rules.")
                        sys.exit(1)
                
                # Set color intensity
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

# HSV to RGB helper
def hsv_to_rgb(h, s, v):
    if s == 0.0:
        return v, v, v
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

# Effects
def run_rainbow(backlight, speed, max_brightness):
    print("Running Rainbow Cycle effect. Press Ctrl+C to stop.")
    h = 0.0
    delay = 0.02 / speed
    while True:
        r, g, b = hsv_to_rgb(h, 1.0, 1.0)
        backlight.set_color(r, g, b, max_brightness)
        h += 0.005
        if h > 1.0:
            h -= 1.0
        time.sleep(delay)

def run_breath(backlight, color, speed, max_brightness):
    print(f"Running Breath effect with color RGB{color}. Press Ctrl+C to stop.")
    r, g, b = color
    t = 0.0
    delay = 0.02 / speed
    while True:
        # Use sine wave for breathing effect
        factor = (math.sin(t) + 1.0) / 2.0
        curr_r = int(r * factor)
        curr_g = int(g * factor)
        curr_b = int(b * factor)
        # Apply factor to overall brightness too for a richer fade
        curr_brightness = int(max_brightness * (0.2 + 0.8 * factor))
        backlight.set_color(curr_r, curr_g, curr_b, curr_brightness)
        t += 0.03
        if t > 2 * math.pi:
            t -= 2 * math.pi
        time.sleep(delay)

def run_strobe(backlight, color, speed, max_brightness):
    print("Running Strobe effect. Press Ctrl+C to stop.")
    delay = 0.1 / speed
    while True:
        if color == 'random':
            h = time.time() * 0.618033988749895 % 1.0
            r, g, b = hsv_to_rgb(h, 1.0, 1.0)
        else:
            r, g, b = color
        
        backlight.set_color(r, g, b, max_brightness)
        time.sleep(delay)
        backlight.set_color(0, 0, 0, 0)
        time.sleep(delay)

def run_color_cycle(backlight, speed, max_brightness):
    print("Running Color Cycle effect. Press Ctrl+C to stop.")
    color_keys = list(COLORS.keys())
    delay = 1.0 / speed
    while True:
        for name in color_keys:
            r, g, b = COLORS[name]
            # Smooth transition between colors
            print(f"Transitioning to {name}...")
            # We will step-wise fade
            steps = 50
            for step in range(steps + 1):
                factor = step / steps
                # Just simple fade in/out
                if step < steps // 2:
                    curr_factor = (steps // 2 - step) / (steps // 2)
                    backlight.set_color(int(r * (1 - curr_factor)), int(g * (1 - curr_factor)), int(b * (1 - curr_factor)), max_brightness)
                else:
                    curr_factor = (step - steps // 2) / (steps // 2)
                    backlight.set_color(int(r * curr_factor), int(g * curr_factor), int(b * curr_factor), max_brightness)
                time.sleep(0.02 / speed)

def main():
    parser = argparse.ArgumentParser(description="Keyboard Backlight Effects for Clevo/Tuxedo Laptops on Linux.")
    parser.add_argument(
        '--mode', '-m',
        choices=['rainbow', 'breath', 'strobe', 'cycle', 'solid', 'off'],
        default='rainbow',
        help="Lighting mode to run (default: rainbow)"
    )
    parser.add_argument(
        '--color', '-c',
        type=parse_color,
        default=(255, 255, 255),
        help="Color for 'solid', 'breath', or 'strobe' modes. Can be name (e.g. 'red', 'blue') or hex code (e.g. 'FF0000')"
    )
    parser.add_argument(
        '--speed', '-s',
        type=float,
        default=1.0,
        help="Speed multiplier for effects (default: 1.0)"
    )
    parser.add_argument(
        '--brightness', '-b',
        type=int,
        default=255,
        choices=range(0, 256),
        metavar="0-255",
        help="Maximum brightness level (0-255, default: 255)"
    )
    
    args = parser.parse_args()

    backlight = KeyboardBacklight()

    # Handle graceful exit
    def signal_handler(sig, frame):
        print("\nStopping effect. Restoring white backlight...")
        try:
            backlight.set_color(255, 255, 255, 255)
        except Exception:
            pass
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.mode == 'off':
        backlight.set_color(0, 0, 0, 0)
        print("Keyboard backlight turned off.")
    elif args.mode == 'solid':
        r, g, b = args.color
        backlight.set_color(r, g, b, args.brightness)
        print(f"Set solid color to RGB({r}, {g}, {b}) with brightness {args.brightness}.")
    elif args.mode == 'rainbow':
        run_rainbow(backlight, args.speed, args.brightness)
    elif args.mode == 'breath':
        run_breath(backlight, args.color, args.speed, args.brightness)
    elif args.mode == 'strobe':
        run_strobe(backlight, args.color, args.speed, args.brightness)
    elif args.mode == 'cycle':
        run_color_cycle(backlight, args.speed, args.brightness)

if __name__ == '__main__':
    main()
