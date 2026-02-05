from m5stack import *
from m5ui import *
from uiflow import *
import math
import unit
import network
import socket
import wifiCfg

# ===========================
# 1. 先把界面画出来 (让用户知道机器活着)
# ===========================
setScreenColor(0x000000)

label_title = M5TextBox(10, 5, "STAR Link_Pro", lcd.FONT_DejaVu18, 0xFFFFFF, rotate=0)
label_ip = M5TextBox(10, 30, "Connecting WiFi...", lcd.FONT_Default, 0xaaaaaa, rotate=0) # 初始状态

M5TextBox(10, 70, "TARGET:", lcd.FONT_Default, 0x00ffc8, rotate=0)
label_target_data = M5TextBox(10, 90, "Az: 000.00  Alt: 00.00", lcd.FONT_DejaVu18, 0x00ffc8, rotate=0)

M5TextBox(10, 130, "CURRENT:", lcd.FONT_Default, 0xFFFFFF, rotate=0)
label_current_data = M5TextBox(10, 150, "Az: 000.00  Alt: 00.00", lcd.FONT_DejaVu18, 0xFFFFFF, rotate=0)

label_status = M5TextBox(0, 190, "STANDBY", lcd.FONT_DejaVu24, 0xaaaaaa, rotate=0)
label_status.setPosition(100, 190)

# ===========================
# 2. 界面画好后，后台静默连网
# ===========================
# lcdShow=False 表示：不要弹窗，不要清屏，悄悄连网
wifiCfg.autoConnect(lcdShow=False)

# 等待一小会儿确认连接状态
wait_ms(500)

try:
    if wifiCfg.wlan_sta.isconnected():
        my_ip = wifiCfg.wlan_sta.ifconfig()[0]
        label_ip.setText("IP: " + str(my_ip))
        label_ip.setColor(0x00ff00) # 变绿
    else:
        # 如果连不上，提示用户去设置
        label_ip.setText("No WiFi! Check Setup")
        label_ip.setColor(0xff0000) # 变红
except:
    label_ip.setText("IP: Error")

# ===========================
# 3. 硬件与变量初始化
# ===========================
servo_az = unit.get(unit.SERVO, unit.PORTB)
servo_alt = unit.get(unit.SERVO, unit.PORTC)

try:
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(('', 8888))
    udp.setblocking(False)
except:
    label_status.setText("UDP ERROR")

target_RA = 0.0
target_Dec = 0.0
LST = 12.0
Target_Az = 0.0
Target_Alt = 0.0
current_az = 0.0
current_alt = 0.0
start_distance = 1.0

# ===========================
# 4. 绘图函数
# ===========================
def draw_progress_bar(percent, color):
    lcd.rect(0, 230, 320, 10, 0x222222, 0x222222)
    w = int(320 * percent)
    if w > 320: w = 320
    lcd.rect(0, 230, w, 10, color, color)

# ===========================
# 5. 主循环
# ===========================
while True:
    try:
        data, addr = udp.recvfrom(1024)
        if data:
            text = data.decode()
            parts = text.split(',')
            if len(parts) == 2:
                target_RA = float(parts[0])
                target_Dec = float(parts[1])
                label_status.setText("COMPUTING")
                label_status.setColor(0x00FFFF)
                rgb.setColorAll(0x00FFFF)
                wait_ms(100)
    except:
        pass

    # 天文计算
    rad_lat = 22.3 * 0.01745 
    rad_dec = target_Dec * 0.01745
    rad_H = (LST * 15 - target_RA) * 0.01745 

    sin_alt = math.sin(rad_lat) * math.sin(rad_dec) + math.cos(rad_lat) * math.cos(rad_dec) * math.cos(rad_H)
    Target_Alt = math.asin(sin_alt) * 57.296 

    cos_az_val = (math.sin(rad_dec) - math.sin(rad_lat) * sin_alt) / (math.cos(rad_lat) * math.cos(math.asin(sin_alt)) + 0.0001)
    if cos_az_val > 1: cos_az_val = 1
    if cos_az_val < -1: cos_az_val = -1
    Target_Az = math.acos(cos_az_val) * 57.296

    # 模拟运动
    sim_speed = 0.5 
    diff_az = Target_Az - current_az
    if abs(diff_az) > sim_speed:
        current_az += sim_speed if diff_az > 0 else -sim_speed
    else:
        current_az = Target_Az 
    diff_alt = Target_Alt - current_alt
    if abs(diff_alt) > sim_speed:
        current_alt += sim_speed if diff_alt > 0 else -sim_speed
    else:
        current_alt = Target_Alt

    # 状态判断
    total_error = abs(Target_Az - current_az) + abs(Target_Alt - current_alt)
    if total_error > start_distance: start_distance = total_error + 0.1
    
    if total_error < 2.0: 
        sys_status = "LOCKED"
        sys_color = 0x00FF00
        bar_percent = 1.0
    elif total_error < 15.0:
        sys_status = "ALIGNING"
        sys_color = 0xFFFF00
        bar_percent = 1.0 - (total_error / start_distance)
    else:
        sys_status = "SLEWING"
        sys_color = 0xFF0000
        bar_percent = 1.0 - (total_error / start_distance)

    # 舵机驱动
    if sys_status == "LOCKED":
        servo_az.write_angle(90)
        servo_alt.write_angle(90)
    else:
        servo_az.write_angle(100 if Target_Az > current_az else 80)
        servo_alt.write_angle(100 if Target_Alt > current_alt else 80)

    # 刷新显示
    label_target_data.setText("Az:%.2f  Alt:%.2f" % (Target_Az, Target_Alt))
    label_current_data.setText("Az:%.2f  Alt:%.2f" % (current_az, current_alt))
    label_status.setText(sys_status)
    label_status.setColor(sys_color)
    rgb.setColorAll(sys_color)
    draw_progress_bar(bar_percent, sys_color)

    wait_ms(50)






