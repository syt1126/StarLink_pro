from nicegui import ui, app
import socket
from datetime import datetime, timezone
import ephem
import math
import multiprocessing

# ===========================
# 1. 配置 & 状态
# ===========================
# 颜色定义
C_BG = '#000000'
C_CARD = '#111111'
C_ACCENT = '#00f3ff'

state = {
    'ip': '192.168.68.106',
    'port': 8888,
    'status': 'STANDBY'
}

# ===========================
# 2. 核心逻辑函数
# ===========================


def get_realtime_body(name):
    observer = ephem.Observer()
    observer.lat = '22.3'
    observer.lon = '114.1'
    observer.elevation = 50
    # 修复：使用带时区的时间，避免报错
    observer.date = datetime.now(timezone.utc)

    body = None
    if name == 'Sun':
        body = ephem.Sun()
    elif name == 'Moon':
        body = ephem.Moon()
    elif name == 'Mars':
        body = ephem.Mars()
    elif name == 'Jupiter':
        body = ephem.Jupiter()
    elif name == 'Venus':
        body = ephem.Venus()
    elif name == 'Saturn':
        body = ephem.Saturn()

    if body:
        body.compute(observer)
        ra_deg = float(body.ra) * 57.29578
        dec_deg = float(body.dec) * 57.29578
        return round(ra_deg, 2), round(dec_deg, 2)

    if name == 'Sirius':
        return 101.28, -16.71
    return 0.0, 0.0


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

# ===========================
# 3. 界面构建 (封装在函数里！)
# ===========================
# 这一步至关重要：把界面放在 @ui.page('/') 下
# 这样只有当页面被访问时才会创建，防止打包后重复运行出错


@ui.page('/')
def index():
    # 开启暗色模式
    ui.dark_mode().enable()

    # 移除默认内边距
    with ui.element('div').classes('w-full min-h-screen flex flex-col items-center bg-black p-5 gap-5'):

        # --- Header ---
        with ui.row().classes('w-full justify-between items-center mt-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('satellite_alt', color=C_ACCENT).classes(
                    'text-2xl animate-pulse')
                with ui.column().classes('gap-0'):
                    ui.label('STARLINK').classes(
                        'text-lg font-black text-white tracking-widest leading-none')
                    ui.label('CONTROL TERMINAL').classes(
                        'text-[9px] font-mono text-gray-500 tracking-widest')
            with ui.row().classes('items-center gap-2'):
                ui.label('ONLINE').classes(
                    'text-[9px] font-bold text-green-500 border border-green-900 px-1 rounded')

        # --- 仪表盘 ---
        with ui.card().classes('w-full rounded-3xl p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-2xl') \
                .style(f'background-color: {C_CARD}; border: 1px solid #1a1a1a'):

            ui.element('div').classes(
                'absolute -top-12 -right-12 w-40 h-40 bg-cyan-900 rounded-full blur-[60px] opacity-20')
            ui.label('REAL-TIME TELEMETRY').classes(
                'text-[9px] text-gray-600 font-bold tracking-[0.2em] mb-4')

            with ui.row().classes('w-full justify-between items-center px-2'):
                with ui.column().classes('items-center gap-1'):
                    ui.label('TARGET RA').classes(
                        'text-[9px] text-cyan-700 font-bold')
                    display_az = ui.label('000.0°').classes(
                        'text-3xl font-black text-white font-mono tracking-tighter')
                ui.element('div').classes('h-8 w-[1px] bg-gray-800')
                with ui.column().classes('items-center gap-1'):
                    ui.label('TARGET DEC').classes(
                        'text-[9px] text-cyan-700 font-bold')
                    display_alt = ui.label('00.0°').classes(
                        'text-3xl font-black text-white font-mono tracking-tighter')

            with ui.row().classes('w-full justify-between items-center mt-6 pt-4 border-t border-gray-900'):
                status_label = ui.label('STATUS: STANDBY').classes(
                    'text-[10px] font-mono text-gray-400')
                status_dot = ui.element('div').classes(
                    'w-1.5 h-1.5 rounded-full bg-gray-600 transition-all duration-300')

        # --- Log 区域 (定义在外面以便调用) ---
        log_area = ui.log(max_lines=3).classes(
            'w-full h-12 text-[9px] font-mono text-gray-600 opacity-50')
        log_area.push(f"[{get_timestamp()}] System initialized.")

        # --- 逻辑控制函数 ---
        def add_log(msg):
            log_area.push(f"[{get_timestamp()}] {msg}")

        def send_command(name, ra, dec):
            add_log(f"Targeting: {name} (RA:{ra})")
            status_label.set_text(f'TRACKING: {name.upper()}')
            status_label.classes('text-cyan-400')
            status_dot.classes('bg-cyan-400 shadow-[0_0_8px_cyan]')
            display_az.set_text(f'{ra}')
            display_alt.set_text(f'{dec}')
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.2)
                sock.sendto(f"{ra},{dec}".encode(),
                            (state['ip'], state['port']))
                ui.notify(f'📡 指令已发送: {name}', position='top', type='positive')
            except Exception as e:
                ui.notify('❌ 连接超时', position='top', type='negative')
                add_log(f"Error: {e}")

        # --- 按钮生成 ---
        def create_live_btn(name, icon, color_cls):
            ra, dec = get_realtime_body(name)
            with ui.card().classes('p-4 rounded-2xl flex flex-col justify-between cursor-pointer transition-all active:scale-95 border border-gray-900 hover:border-gray-700') \
                    .style(f'background-color: {C_CARD}').on('click', lambda: send_command(name, ra, dec)):
                with ui.row().classes('w-full justify-between items-start'):
                    ui.icon(icon).classes(f'text-2xl {color_cls}')
                    ui.label(f'RA {int(ra)}').classes(
                        'text-[9px] text-gray-600 font-mono bg-black px-1 rounded')
                with ui.column().classes('gap-0 mt-2'):
                    ui.label(name).classes('text-sm font-bold text-gray-200')
                    ui.label(f'Dec: {dec}°').classes(
                        'text-[10px] text-gray-500 font-mono')

        # --- 按钮网格 ---
        ui.label('TARGET DESIGNATION (LIVE)').classes(
            'text-[10px] text-gray-500 font-bold ml-1')
        with ui.grid(columns=2).classes('w-full gap-3'):
            create_live_btn('Sun', 'wb_sunny', 'text-yellow-400')
            create_live_btn('Moon', 'bedtime', 'text-gray-200')
            create_live_btn('Mars', 'public', 'text-red-400')
            create_live_btn('Jupiter', 'circle', 'text-orange-300')

        # --- 手动控制 ---
        with ui.expansion('MANUAL OVERRIDE', icon='tune').classes('w-full bg-[#0a0a0a] rounded-2xl border border-[#1a1a1a] text-gray-500 text-xs'):
            with ui.column().classes('w-full p-4 gap-4'):
                ui.input('Target IP').bind_value(state, 'ip').props(
                    'dark dense outlined input-style="color:#00f3ff"').classes('w-full font-mono')
                with ui.row().classes('w-full gap-3'):
                    ra_in = ui.number(label='RA', format='%.2f').props(
                        'dark filled dense').classes('w-1/2')
                    dec_in = ui.number(label='DEC', format='%.2f').props(
                        'dark filled dense').classes('flex-grow')
                ui.button('ENGAGE THRUSTERS', on_click=lambda: send_command('MANUAL', ra_in.value, dec_in.value)) \
                    .classes('w-full bg-cyan-900 text-cyan-300 shadow-lg text-xs font-bold py-2')


# ===========================
# 4. 启动入口
# ===========================
if __name__ in {"__main__", "__mp_main__"}:
    # 必须放在第一行
    multiprocessing.freeze_support()

    # 启动配置
    ui.run(
        title='StarLink Controller',
        port=8899,
        host='0.0.0.0',          # <---【核心修改】允许局域网设备（手机）连接！
        native=True,             # 保持 Native 模式
        window_size=(390, 844),
        reload=False,            # 核心：关闭重载
        show=True,
        reconnect_timeout=0      # 防止断连后重试导致崩溃
    )
