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
SW_SHOW = 5

SWP_NOZORDER = 0x0040
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

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

def turn_off_monitor():
    user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
    print("[息屏] 显示器已关闭")

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
            monitors.append({
                'hMonitor': hMonitor,
                'left': info.rcMonitor.left,
                'top': info.rcMonitor.top,
                'right': info.rcMonitor.right,
                'bottom': info.rcMonitor.bottom,
                'device': info.szDevice,
                'is_primary': (info.dwFlags & 0x00000001) != 0
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

def get_window_thread_process_id(hwnd):
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def get_all_windows():
    windows = []
    def callback(hwnd, lParam):
        if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if class_name.value not in ['Shell_TrayWnd', 'Shell_SecondaryTrayWnd', 'Button', 'Progman', 'WorkerW']:
                if len(title.value.strip()) > 0:
                    try:
                        placement = get_window_placement(hwnd)
                        normal_rect = [
                            placement.rcNormalPosition.left,
                            placement.rcNormalPosition.top,
                            placement.rcNormalPosition.right,
                            placement.rcNormalPosition.bottom
                        ]
                        pid = get_window_thread_process_id(hwnd)
                        windows.append({
                            'hwnd': hwnd,
                            'title': title.value,
                            'class': class_name.value,
                            'normal_rect': normal_rect,
                            'placement': placement,
                            'showCmd': placement.showCmd,
                            'pid': pid
                        })
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
    
    draw.rectangle(
        [monitor_x, monitor_y, monitor_x + monitor_width, monitor_y + monitor_height],
        fill=(255, 255, 255, 255),
        outline=(255, 255, 255, 255),
        width=2
    )
    
    stand_x = monitor_x + monitor_width // 2 - 4
    stand_y = monitor_y + monitor_height
    stand_width = 8
    stand_height = 6
    
    draw.rectangle(
        [stand_x, stand_y, stand_x + stand_width, stand_y + stand_height],
        fill=(255, 255, 255, 255)
    )
    
    base_x = monitor_x + monitor_width // 2 - 8
    base_y = stand_y + stand_height
    base_width = 16
    base_height = 3
    
    draw.rectangle(
        [base_x, base_y, base_x + base_width, base_y + base_height],
        fill=(255, 255, 255, 255)
    )
    
    return image

class ScreenKeeper:
    def __init__(self):
        self.running = True
        self.last_monitor_count = get_monitor_count()
        self.last_monitors = get_monitors_info()
        self.monitor_removed = False
        self.saved_window_positions = {}
        self.removed_monitor_info = None
        self.icon = None
        self.tracked_windows = {}
        self.monitor_reconnected = False
        self.reconnect_restore_count = 0
        self.primary_monitor_removed = False

    def detect_removed_monitor(self, old_monitors, new_monitors):
        for old in old_monitors:
            found = False
            for new in new_monitors:
                if old['device'] == new['device']:
                    found = True
                    break
            if not found:
                return old
        return None

    def is_window_on_monitor(self, win_rect, monitor_info):
        left, top, right, bottom = win_rect
        m_left = monitor_info['left']
        m_top = monitor_info['top']
        m_right = monitor_info['right']
        m_bottom = monitor_info['bottom']
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return (center_x >= m_left and center_x < m_right and 
                center_y >= m_top and center_y < m_bottom)

    def track_all_windows(self, monitors):
        all_windows = get_all_windows()
        for win in all_windows:
            hwnd = win['hwnd']
            normal_rect = win['normal_rect']
            for mon in monitors:
                if self.is_window_on_monitor(normal_rect, mon):
                    if hwnd not in self.tracked_windows:
                        placement = win['placement']
                        state = "正常"
                        if placement.showCmd == SW_MAXIMIZE:
                            state = "最大化"
                        elif placement.showCmd == SW_MINIMIZE:
                            state = "最小化"
                        
                        self.tracked_windows[hwnd] = {
                            'title': win['title'],
                            'class': win['class'],
                            'normal_rect': normal_rect.copy(),
                            'monitor': mon['device'],
                            'showCmd': placement.showCmd,
                            'pid': win['pid'],
                            'x': normal_rect[0],
                            'y': normal_rect[1],
                            'width': normal_rect[2] - normal_rect[0],
                            'height': normal_rect[3] - normal_rect[1],
                            'state': state
                        }
                        print(f"[跟踪] 窗口: {win['title'][:40]} | 状态: {state} | 显示器: {mon['device']}")
                    else:
                        self.tracked_windows[hwnd]['showCmd'] = win['showCmd']
                        self.tracked_windows[hwnd]['x'] = normal_rect[0]
                        self.tracked_windows[hwnd]['y'] = normal_rect[1]
                        self.tracked_windows[hwnd]['width'] = normal_rect[2] - normal_rect[0]
                        self.tracked_windows[hwnd]['height'] = normal_rect[3] - normal_rect[1]
                        state = "正常"
                        if win['showCmd'] == SW_MAXIMIZE:
                            state = "最大化"
                        elif win['showCmd'] == SW_MINIMIZE:
                            state = "最小化"
                        self.tracked_windows[hwnd]['state'] = state
                    break

    def restore_window_positions(self):
        restored_count = 0
        for hwnd, win_info in list(self.saved_window_positions.items()):
            if user32.IsWindow(hwnd):
                try:
                    x = win_info['x']
                    y = win_info['y']
                    width = win_info['width']
                    height = win_info['height']
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
                    
                    restored_count += 1
                    print(f"[恢复] 窗口: {win_info['title'][:40]} | 状态: {state} | 显示器: {win_info['monitor']}")
                except Exception as e:
                    print(f"[错误] 恢复失败: {win_info['title'][:40]} | 错误: {e}")
        return restored_count

    def monitor_loop(self):
        while self.running:
            current_count = get_monitor_count()
            current_monitors = get_monitors_info()
            
            if self.last_monitor_count >= 2 and current_count >= 2:
                if not self.monitor_removed and not self.monitor_reconnected:
                    self.track_all_windows(current_monitors)
            
            elif self.last_monitor_count >= 2 and current_count >= 1 and current_count < self.last_monitor_count:
                if not self.monitor_removed:
                    removed_monitor = self.detect_removed_monitor(self.last_monitors, current_monitors)
                    print(f"[调试] 检测到显示器断开")
                    print(f"[调试] 断开的显示器: {removed_monitor}")
                    print(f"[调试] 上次显示器列表: {[m['device'] for m in self.last_monitors]}")
                    print(f"[调试] 当前显示器列表: {[m['device'] for m in current_monitors]}")
                    print(f"[调试] 跟踪的窗口数量: {len(self.tracked_windows)}")
                    
                    if removed_monitor:
                        self.removed_monitor_info = removed_monitor
                        self.primary_monitor_removed = removed_monitor.get('is_primary', False)
                        self.saved_window_positions = {}
                        
                        if self.primary_monitor_removed:
                            for hwnd, win_info in list(self.tracked_windows.items()):
                                if win_info['monitor'] != removed_monitor['device']:
                                    self.saved_window_positions[hwnd] = win_info
                            print(f"\n[事件] 主显示器断开: {removed_monitor['device']}")
                            print(f"[保存] 共保存 {len(self.saved_window_positions)} 个副显示器窗口位置")
                        else:
                            for hwnd, win_info in list(self.tracked_windows.items()):
                                if win_info['monitor'] == removed_monitor['device']:
                                    self.saved_window_positions[hwnd] = win_info
                            print(f"\n[事件] 显示器断开: {removed_monitor['device']}")
                            print(f"[保存] 共保存 {len(self.saved_window_positions)} 个窗口位置")
                        
                        print(f"[等待] 等待显示器重新连接...\n")
                        self.monitor_removed = True
                        self.monitor_reconnected = False
            
            elif current_count > self.last_monitor_count:
                if self.monitor_removed:
                    print(f"\n[事件] 显示器重新连接")
                    print(f"[恢复] 开始恢复窗口位置...\n")
                    self.monitor_reconnected = True
                    self.reconnect_restore_count = 0
            
            if self.monitor_reconnected:
                restored = self.restore_window_positions()
                self.reconnect_restore_count += 1
                if self.reconnect_restore_count >= 3 or restored == 0:
                    print(f"\n[完成] 恢复完成，共恢复 {len(self.saved_window_positions)} 个窗口")
                    print(f"[退出] 程序即将退出\n")
                    self.running = False
                    if self.icon:
                        self.icon.stop()
            
            self.last_monitor_count = current_count
            self.last_monitors = current_monitors
            
            if self.monitor_reconnected:
                sleep_time = 0.1
            else:
                sleep_time = 0.5
            time.sleep(sleep_time)

    def create_tray_icon(self):
        image = create_icon()
        
        def on_quit(icon, item):
            self.running = False
            icon.stop()
        
        menu = pystray.Menu(
            pystray.MenuItem("退出", on_quit)
        )
        
        self.icon = pystray.Icon("screen_keeper", image, "屏幕保持工具", menu)
        self.icon.run()

    def start(self):
        monitor_thread = Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()
        self.create_tray_icon()

def main():
    monitor_count = get_monitor_count()
    print(f"当前显示器数量: {monitor_count}")
    
    if monitor_count < 2:
        print("检测到显示器数量少于2个，程序将不工作。")
        return
    
    print("[启动] 关闭显示器...")
    turn_off_monitor()
    
    app = ScreenKeeper()
    app.start()

if __name__ == "__main__":
    main()
