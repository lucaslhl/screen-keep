import sys
import os
import ctypes
import ctypes.wintypes as wintypes
import subprocess
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

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
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
        self.monitor_removed = False
        self.icon = None
        self.pw_process = None
        self.monitor_reconnected = False
        self.reconnect_time = None

    def monitor_loop(self):
        while self.running:
            current_count = get_monitor_count()
            
            if self.last_monitor_count >= 2 and current_count >= 1 and current_count < self.last_monitor_count:
                if not self.monitor_removed:
                    print(f"\n[事件] 显示器断开")
                    print(f"[等待] 等待显示器重新连接...\n")
                    self.monitor_removed = True
                    self.monitor_reconnected = False
            
            elif current_count > self.last_monitor_count:
                if self.monitor_removed:
                    print(f"\n[事件] 显示器重新连接")
                    self.monitor_reconnected = True
                    self.reconnect_time = time.time()
            
            if self.monitor_reconnected and self.reconnect_time:
                elapsed = time.time() - self.reconnect_time
                if elapsed >= 6:
                    print(f"\n[完成] 6秒已过，退出程序\n")
                    self.running = False
                    if self.icon:
                        self.icon.stop()
            
            self.last_monitor_count = current_count
            time.sleep(0.5)

    def create_tray_icon(self):
        image = create_icon()
        
        def on_quit(icon, item):
            self.running = False
            if self.pw_process:
                try:
                    self.pw_process.terminate()
                    print("[退出] 已终止pw.exe")
                except:
                    pass
            icon.stop()
        
        menu = pystray.Menu(
            pystray.MenuItem("退出", on_quit)
        )
        
        self.icon = pystray.Icon("screen_keeper", image, "屏幕保持工具", menu)
        self.icon.run()

    def start(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        pw_path = os.path.join(base_path, 'pw', 'pw.exe')
        
        print(f"[启动] 启动pw.exe: {pw_path}")
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 6
            self.pw_process = subprocess.Popen([pw_path], startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW)
            print("[启动] pw.exe已启动")
        except Exception as e:
            print(f"[错误] 启动pw.exe失败: {e}")
        
        monitor_thread = Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()
        
        def delayed_turn_off():
            time.sleep(1)
            print("[启动] 关闭显示器...")
            turn_off_monitor()
        
        turn_off_thread = Thread(target=delayed_turn_off, daemon=True)
        turn_off_thread.start()
        
        self.create_tray_icon()
        
        if self.pw_process:
            try:
                self.pw_process.terminate()
                print("[退出] 已终止pw.exe")
            except:
                pass

def main():
    monitor_count = get_monitor_count()
    print(f"当前显示器数量: {monitor_count}")
    
    if monitor_count < 2:
        print("检测到显示器数量少于2个，程序将不工作。")
        return
    
    app = ScreenKeeper()
    app.start()

if __name__ == "__main__":
    main()
