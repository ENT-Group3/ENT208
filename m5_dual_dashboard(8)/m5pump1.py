import M5
from M5 import *
import time

try:
    import network
except ImportError:
    network = None

try:
    import urequests as requests
except ImportError:
    try:
        import requests
    except ImportError:
        requests = None

try:
    import ujson as json
except ImportError:
    import json

try:
    import gc
except ImportError:
    gc = None

try:
    from unit import WateringUnit
except ImportError:
    WateringUnit = None


# ====== Wi-Fi / Server Config ======
WIFI_SSID = "MagicV2"
WIFI_PASSWORD = "1221331yy"
SERVER_HOST = "10.21.70.62"
SERVER_PORT = 5000

DEVICE_ID = "m5stack-pump-01"

POST_INTERVAL_MS = 5000
COMMAND_POLL_MS = 2000

BACKEND_URL = "http://{}:{}/api/sensor".format(SERVER_HOST, SERVER_PORT)
COMMAND_URL = "http://{}:{}/api/pump/command".format(SERVER_HOST, SERVER_PORT)
# ===================================


# ====== Watering Unit Config ======
# 官方模块化编程导出使用的是 WateringUnit((33, 32))
# 其中原始湿度值应使用 get_raw() 获取。
WATERING_PINS = (1, 0)
AIR_RAW_VALUE = 31500.0
WATER_RAW_VALUE = 23100.0
# ==================================


label_title = None
label_cap = None
label_moi = None
label_adc = None
label_pump = None
label_net = None

wlan = None
watering_0 = None

last_post_time = 0
last_cmd_poll_time = 0
last_executed_command_id = 0
last_net_status = "NET init..."
pump_running_until = 0
last_done_msg = ""


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def shorten(msg, n=18):
    try:
        s = str(msg)
    except Exception:
        s = "err"
    return s if len(s) <= n else s[:n]


def wifi_ip():
    global wlan
    try:
        if wlan and wlan.isconnected():
            return wlan.ifconfig()[0]
    except Exception:
        pass
    return "0.0.0.0"


def connect_wifi(timeout_ms=15000):
    global wlan

    if network is None:
        return False, "No network module"

    try:
        if wlan is None:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)

        wlan.disconnect()
        time.sleep(0.5)

        if wlan.isconnected():
            return True, "WiFi OK {}".format(wifi_ip())

        print("Connecting WiFi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start_ms = time.ticks_ms()

        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_ms) >= timeout_ms:
                break
            M5.update()
            time.sleep_ms(250)

        if wlan.isconnected():
            print("WiFi connected:", wifi_ip())
            return True, "WiFi OK {}".format(wifi_ip())

        status = None
        try:
            status = wlan.status()
        except Exception:
            pass
        return False, "WiFi fail {}".format(status)
    except Exception as exc:
        return False, "WiFi err {}".format(shorten(exc))


def init_watering_unit():
    global watering_0

    if WateringUnit is None:
        return "WateringUnit missing"

    try:
        Power.setExtOutput(True)
    except Exception:
        pass

    try:
        watering_0 = WateringUnit(WATERING_PINS)
        try:
            watering_0.off()
        except Exception:
            try:
                watering_0.set_pump_status(0)
            except Exception:
                pass
        return "Watering OK {}".format(WATERING_PINS)
    except Exception as exc:
        watering_0 = None
        return "Watering init fail {}".format(shorten(exc))


def read_watering_raw(samples=5, delay_ms=20):
    if watering_0 is None:
        return None

    total = 0
    count = 0
    for _ in range(samples):
        try:
            total += int(watering_0.get_raw())
            count += 1
        except Exception:
            pass
        time.sleep_ms(delay_ms)

    if count == 0:
        return None
    return int(total / count)


def read_watering_voltage():
    if watering_0 is None:
        return None
    try:
        return round(float(watering_0.get_voltage()), 3)
    except Exception:
        return None


def raw_to_moisture_percent(raw_value):
    if raw_value is None:
        return None

    span = AIR_RAW_VALUE - WATER_RAW_VALUE
    if span == 0:
        return None

    moisture = (AIR_RAW_VALUE - raw_value) * 100.0 / span
    return round(clamp(moisture, 0.0, 100.0), 1)


def pump_is_running():
    return time.ticks_diff(pump_running_until, time.ticks_ms()) > 0


def set_pump(on):
    if watering_0 is None:
        return
    try:
        if on:
            try:
                watering_0.on()
            except Exception:
                watering_0.set_pump_status(1)
        else:
            try:
                watering_0.off()
            except Exception:
                watering_0.set_pump_status(0)
    except Exception as exc:
        print("Pump set failed:", exc)


def pump_status_text():
    return "RUNNING" if pump_is_running() else "IDLE"


def fetch_pump_command():
    if requests is None:
        return None

    if not (wlan and wlan.isconnected()):
        return None

    response = None
    try:
        response = requests.get(COMMAND_URL)
        status_code = getattr(response, "status_code", 0)
        if not (200 <= status_code < 300):
            return None

        data = json.loads(response.text)
        return data
    except Exception:
        return None
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if gc is not None:
            gc.collect()


def execute_command_if_needed(command_data):
    global last_executed_command_id, pump_running_until, last_done_msg

    if not command_data:
        return

    command_id = int(command_data.get("command_id", 0))
    duration_ms = int(command_data.get("duration_ms", 1000))

    if command_id <= 0 or command_id == last_executed_command_id:
        return

    duration_ms = int(clamp(duration_ms, 100, 5000))
    last_executed_command_id = command_id

    print("Execute pump command:", command_id, duration_ms, "ms")
    set_pump(True)
    pump_running_until = time.ticks_add(time.ticks_ms(), duration_ms)

    start_ms = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start_ms) < duration_ms:
        M5.update()
        time.sleep_ms(100)

    set_pump(False)
    pump_running_until = 0
    last_done_msg = " (#{} done)".format(command_id)


def upload_pump_data(raw_value, voltage_value, moisture_percent):
    if requests is None:
        return False, "No requests module"

    if not (wlan and wlan.isconnected()):
        ok, status = connect_wifi()
        if not ok:
            return False, status

    payload = {
        "device_kind": "pump",
        "device_id": DEVICE_ID,
        "adc_raw": raw_value,
        "moisture_capacitive_value": raw_value,
        "moisture_percent": moisture_percent,
        "moisture_voltage": voltage_value,
        "pump_status_text": pump_status_text(),
        "ip": wifi_ip(),
        "uptime_ms": time.ticks_ms(),
        "last_executed_command_id": last_executed_command_id,
    }

    response = None
    try:
        response = requests.post(
            BACKEND_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        status_code = getattr(response, "status_code", 0)
        if 200 <= status_code < 300:
            return True, "POST {}".format(status_code)
        return False, "POST {}".format(status_code)
    except Exception as exc:
        print("Upload failed:", exc)
        return False, "POST {}".format(shorten(exc, 12))
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if gc is not None:
            gc.collect()


def setup():
    global label_title, label_cap, label_moi, label_adc, label_pump, label_net, last_net_status

    M5.begin()
    Widgets.setRotation(1)
    Widgets.fillScreen(0x000000)

    try:
        M5.Display.setBrightness(30)
    except Exception:
        pass

    label_title = Widgets.Label("Pump M5 / Soil", 4, 4, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    label_cap = Widgets.Label("Raw:   --", 4, 28, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    label_moi = Widgets.Label("Mois:  --", 4, 52, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    label_adc = Widgets.Label("Volt:  --", 4, 76, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    label_pump = Widgets.Label("Pump:  init...", 4, 100, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)
    label_net = Widgets.Label("Net:   init...", 4, 124, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)

    watering_status = init_watering_unit()
    print(watering_status)

    ok, status = connect_wifi()
    last_net_status = status
    print(status)

    label_pump.setText("Pump:  {}".format("IDLE" if watering_0 else "unit error"))
    label_net.setText("Net:   {}".format(last_net_status))


def loop():
    global last_post_time, last_cmd_poll_time, last_net_status, last_done_msg

    M5.update()
    now_ms = time.ticks_ms()

    raw_value = read_watering_raw()
    voltage_value = read_watering_voltage()
    moisture_percent = raw_to_moisture_percent(raw_value)

    print("raw_value =", raw_value, "voltage =", voltage_value, "moisture_percent =", moisture_percent)

    label_cap.setText("Raw:   {}".format("--" if raw_value is None else raw_value))
    label_moi.setText("Mois:  {} %".format("--" if moisture_percent is None else moisture_percent))
    label_adc.setText("Volt:  {}".format("--" if voltage_value is None else voltage_value))

    if pump_is_running():
        label_pump.setText("Pump:  RUNNING")
    else:
        label_pump.setText("Pump:  IDLE" + last_done_msg)

    if time.ticks_diff(now_ms, last_cmd_poll_time) >= COMMAND_POLL_MS:
        last_cmd_poll_time = now_ms
        cmd = fetch_pump_command()
        execute_command_if_needed(cmd)

    if time.ticks_diff(now_ms, last_post_time) >= POST_INTERVAL_MS:
        last_post_time = now_ms
        ok, status = upload_pump_data(raw_value, voltage_value, moisture_percent)
        last_net_status = status
        label_net.setText("Net:   {}".format(last_net_status))

    time.sleep_ms(250)


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as exc:
        try:
            set_pump(False)
            print("Program stopped:", exc)
            from utility import print_error_msg
            print_error_msg(exc)
        except ImportError:
            pass