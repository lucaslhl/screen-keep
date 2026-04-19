import sys
import ctypes
import ctypes.wintypes as wintypes
from PIL import Image, ImageDraw
import pystray
from threading import Thread
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_DISPLAYCHANGE = 0x007E
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170
HWND_BROADCAST = 0xFFFF

SW_MINIMIZE = 2
SW_MAXIMIZE = 3
SW_SHOWNORMAL = 1
SW_RESTORE = 9

SWP_NOZORDER = 0x0040
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

def turn_off_monitor():
    user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition", POINT),
        ("ptMaxPosition", POINT),
        ("rcNormalPosition", RECT)
    ]

def get_monitor_count():
    count = 0
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        nonlocal count
        count += 1
        return True
    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p)
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
    return count

def get_monitors_info():
    monitors = []
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        class MONITORINFOEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
                ("szDevice", ctypes.c_wchar * 32)
            ]
        info = MONITORINFOEX()
        info.cbSize = ctypes.sizeof(MONITORINFOEX)
        try:
            user32.GetMonitorInfoW(hMonitor, ctypes.byref(info))
            is_primary = (info.dwFlags & 0x00000001) != 0
            monitors.append({
                'left': info.rcMonitor.left,
                'top': info.rcMonitor.top,
                'right': info.rcMonitor.right,
                'bottom': info.rcMonitor.bottom,
                'work_left': info.rcWork.left,
                'work_top': info.rcWork.top,
                'work_right': info.rcWork.right,
                'work_bottom': info.rcWork.bottom,
                'device': info.szDevice,
                'is_primary': is_primary
            })
        except:
            pass
        return True
    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p)
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
    return monitors

def get_window_placement(hwnd):
    placement = WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(WINDOWPLACEMENT)
    user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
    return placement

def set_window_pos(hwnd, x, y, width, height):
    flags = SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
    user32.SetWindowPos(hwnd, 0, x, y, width, height, flags)

def show_window(hwnd, cmd):
    user32.ShowWindow(hwnd, cmd)

def get_window_rect(hwnd):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect

def get_all_windows():
    windows = []
    def callback(hwnd, lParam):
        try:
            hwnd = ctypes.c_void_p(hwnd)
            if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                title = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, title, 256)
                class_name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_name, 256)
                if class_name.value not in ['Shell_TrayWnd', 'Shell_SecondaryTrayWnd', 'Button', 'Progman', 'WorkerW']:
                    if len(title.value.strip()) > 0:
                        try:
                            placement = get_window_placement(hwnd)
                            rect = get_window_rect(hwnd)
                            windows.append({
                                'hwnd': hwnd,
                                'title': title.value,
                                'class': class_name.value,
                                'placement': placement,
                                'showCmd': placement.showCmd,
                                'rect': rect
                            })
                        except:
                            pass
        except:
            pass
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows

def create_icon():
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([4, 4, size-4, size-4], fill=(52, 152, 219, 255))
    monitor_x = 16
    monitor_y = 18
    monitor_width = 32
    monitor_height = 24
    draw.rectangle([monitor_x, monitor_y, monitor_x + monitor_width, monitor_y + monitor_height], fill=(255, 255, 255, 255), outline=(255, 255, 255, 255), width=2)
    stand_x = monitor_x + monitor_width // 2 - 4
    stand_y = monitor_y + monitor_height
    draw.rectangle([stand_x, stand_y, stand_x + 8, stand_y + 6], fill=(255, 255, 255, 255))
    draw.rectangle([monitor_x + monitor_width // 2 - 8, stand_y + 6, monitor_x + monitor_width // 2 + 8, stand_y + 9], fill=(255, 255, 255, 255))
    return image

class ScreenKeeper:
    def __init__(self):
        self.running = True
        self.last_monitor_count = get_monitor_count()
        self.last_monitors = get_monitors_info()
        self.monitor_removed = False
        self.saved_window_positions = {}
        self.icon = None
        self.tracked_windows = {}
        self.monitor_reconnected = False
        self.reconnect_time = None
        self.restore_started = False

    def is_window_on_monitor(self, win_rect, monitor_info):
        left, top, right, bottom = win_rect
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return (center_x >= monitor_info['left'] and center_x < monitor_info['right'] and 
                center_y >= monitor_info['top'] and center_y < monitor_info['bottom'])

    def track_all_windows(self, monitors):
        all_windows = get_all_windows()
        for win in all_windows:
            hwnd = win['hwnd']
            hwnd_value = hwnd.value if hasattr(hwnd, 'value') else hwnd
            placement = win['placement']
            
            if placement.showCmd == SW_SHOWNORMAL:
                rect = win['rect']
                normal_rect = [rect.left, rect.top, rect.right, rect.bottom]
            else:
                rect = placement.rcNormalPosition
                normal_rect = [rect.left, rect.top, rect.right, rect.bottom]
            
            for mon in monitors:
                if self.is_window_on_monitor(normal_rect, mon):
                    if hwnd_value not in self.tracked_windows:
                        state = "正常"
                        if placement.showCmd == SW_MAXIMIZE:
                            state = "最大化"
                        elif placement.showCmd == SW_MINIMIZE:
                            state = "最小化"
                        
                        self.tracked_windows[hwnd_value] = {
                            'hwnd': hwnd,
                            'title': win['title'],
                            'showCmd': placement.showCmd,
                            'x': normal_rect[0],
                            'y': normal_rect[1],
                            'width': normal_rect[2] - normal_rect[0],
                            'height': normal_rect[3] - normal_rect[1],
                            'state': state,
                            'original_is_primary': mon['is_primary'],
                            'original_width': normal_rect[2] - normal_rect[0],
                            'original_height': normal_rect[3] - normal_rect[1]
                        }
                    break

    def find_suitable_monitor(self, win_info):
        current_monitors = get_monitors_info()
        original_is_primary = win_info.get('original_is_primary', True)
        
        for mon in current_monitors:
            if mon['is_primary'] == original_is_primary:
                return mon
        
        for mon in current_monitors:
            if mon['is_primary']:
                return mon
        
        return current_monitors[0] if current_monitors else None
    
    def adjust_window_position(self, win_info, monitor):
        x = win_info['x']
        y = win_info['y']
        width = win_info.get('original_width', win_info['width'])
        height = win_info.get('original_height', win_info['height'])
        
        work_left = monitor['work_left']
        work_top = monitor['work_top']
        work_right = monitor['work_right']
        work_bottom = monitor['work_bottom']
        
        max_width = work_right - work_left
        max_height = work_bottom - work_top
        
        if width > max_width:
            width = max_width
        if height > max_height:
            height = max_height
        
        if y < work_top:
            y = work_top
        
        if y + height > work_bottom:
            y = work_bottom - height
            if y < work_top:
                y = work_top
        
        if x < work_left:
            x = work_left
        elif x + width > work_right:
            x = work_right - width
            if x < work_left:
                x = work_left
        
        return x, y, width, height
    
    def restore_window_positions(self):
        for hwnd, win_info in list(self.saved_window_positions.items()):
            if user32.IsWindow(hwnd):
                try:
                    monitor = self.find_suitable_monitor(win_info)
                    if not monitor:
                        continue
                    
                    x, y, width, height = self.adjust_window_position(win_info, monitor)
                    showCmd = win_info['showCmd']
                    state = win_info.get('state', '正常')
                    
                    if showCmd == SW_MAXIMIZE:
                        show_window(hwnd, SW_RESTORE)
                        time.sleep(0.01)
                        set_window_pos(hwnd, x, y, width, height)
                        time.sleep(0.01)
                        show_window(hwnd, SW_MAXIMIZE)
                    elif showCmd == SW_MINIMIZE:
                        show_window(hwnd, SW_RESTORE)
                        time.sleep(0.01)
                        set_window_pos(hwnd, x, y, width, height)
                        time.sleep(0.01)
                        show_window(hwnd, SW_MINIMIZE)
                    else:
                        set_window_pos(hwnd, x, y, width, height)
                    
                    print(f"[恢复] {win_info['title'][:40]} | {state} | ({x}, {y}) {width}x{height}")
                except Exception as e:
                    print(f"[错误] {win_info['title'][:40]}: {e}")

    def monitor_loop(self):
        if self.last_monitor_count >= 2:
            print(f"[初始化] 记录窗口位置...")
            self.track_all_windows(self.last_monitors)
            print(f"[初始化] 共记录 {len(self.tracked_windows)} 个窗口")
            print(f"[初始化] 当前显示器数量: {self.last_monitor_count}")
            time.sleep(0.5)
            print(f"[初始化] 息屏...")
            turn_off_monitor()
            print(f"[初始化] 开始监控显示器状态...\n")
        
        while self.running:
            current_count = get_monitor_count()
            
            if current_count != self.last_monitor_count:
                print(f"[检测] 显示器数量变化: {self.last_monitor_count} -> {current_count}")
            
            if self.last_monitor_count >= 2 and current_count >= 1 and current_count < self.last_monitor_count:
                if not self.monitor_removed:
                    print(f"\n[事件] 显示器断开 ({self.last_monitor_count} -> {current_count})")
                    print(f"[保存] 保存窗口位置...")
                    self.saved_window_positions = dict(self.tracked_windows)
                    print(f"[保存] 共保存 {len(self.saved_window_positions)} 个窗口")
                    print(f"[等待] 等待显示器重新连接...\n")
                    self.monitor_removed = True
                    self.monitor_reconnected = False
                    self.restore_started = False
            
            elif current_count > self.last_monitor_count:
                if self.monitor_removed:
                    print(f"\n[事件] 显示器重新连接 ({self.last_monitor_count} -> {current_count})")
                    print(f"[等待] 等待5秒后恢复窗口...\n")
                    self.monitor_reconnected = True
                    self.reconnect_time = time.time()
            
            if self.monitor_reconnected and self.reconnect_time and not self.restore_started:
                elapsed = time.time() - self.reconnect_time
                if elapsed >= 5:
                    print(f"[恢复] 开始恢复窗口位置...\n")
                    self.restore_window_positions()
                    print(f"\n[完成] 恢复完成")
                    print(f"[退出] 程序即将退出\n")
                    self.running = False
                    if self.icon:
                        self.icon.stop()
            
            self.last_monitor_count = current_count
            
            time.sleep(0.5)

    def create_tray_icon(self):
        image = create_icon()
        def on_quit(icon, item):
            self.running = False
            icon.stop()
        menu = pystray.Menu(pystray.MenuItem("退出", on_quit))
        self.icon = pystray.Icon("screen_keeper", image, "Screen Keeper", menu)
        return self.icon

def main():
    keeper = ScreenKeeper()
    tray_icon = keeper.create_tray_icon()
    monitor_thread = Thread(target=keeper.monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    tray_icon.run()

if __name__ == "__main__":
    main()
