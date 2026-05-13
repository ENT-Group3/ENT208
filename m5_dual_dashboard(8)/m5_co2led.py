import os, sys, io
import M5
from M5 import *
from hardware import Pin, I2C, RGB
from unit import CO2Unit
import time
import json
import gc

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

# ====== Wi-Fi / Server Config ======
WIFI_SSID = "yyysh"
WIFI_PASSWORD = "12345678"
SERVER_HOST = "192.168.43.127"   # ⚠️务必用 ipconfig 确认这是你现在的最新电脑IP！
SERVER_PORT = 5000
DEVICE_ID = "m5stack-co2-01"
POST_INTERVAL_MS = 5000 
BACKEND_URL = "http://{}:{}/api/sensor".format(SERVER_HOST, SERVER_PORT)
# ===================================

I2C_SDA_PIN = 0
I2C_SCL_PIN = 1
LED_DATA_PIN = 9  
NUM_LEDS = 30

label_co2 = None; label_temp = None; label_hum = None; label_net = None; label_light = None
i2c0 = None; co2_0 = None; rgb_strip = None; wlan = None
last_post_time = 0

current_led_power = True
current_led_mode = "auto"
current_led_color_hex = 0x00ff00

def setup_wifi():
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    wlan.disconnect()
    time.sleep(0.5)
    
    print("Connecting to Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1
        
    if wlan.isconnected():
        print("\n✅ Wi-Fi Connected! M5Stack IP:", wlan.ifconfig()[0])
        return True
    else:
        print("\n❌ Wi-Fi Timeout!")
        return False

def parse_server_response(response_text):
    global current_led_power, current_led_mode, current_led_color_hex
    try:
        data = json.loads(response_text)
        if "led_command" in data:
            cmd = data["led_command"]
            current_led_power = cmd.get("power", True)
            current_led_mode = cmd.get("mode", "auto")
            
            color_str = cmd.get("color", "#00ff00")
            if color_str.startswith("#"):
                current_led_color_hex = int(color_str[1:], 16)
            print("🎛️ Got LED Command -> Power:", current_led_power, "Mode:", current_led_mode)
    except Exception as e:
        print("❌ Parse JSON error:", e)

def upload_sensor_data(co2_val, temp, hum, lamp_status):
    if not wlan or not wlan.isconnected(): 
        return False, "No WiFi"
        
    payload = {
        "device_kind": "env",
        "device_id": DEVICE_ID,
        "co2": co2_val, "temperature": temp, "humidity": hum,
        "lamp_status": lamp_status
    }
    
    try:
        print("🚀 Sending Data to Server...")
        headers = {'Content-Type': 'application/json'}
        response = requests.post(BACKEND_URL, json=payload, headers=headers, timeout=3)
        status_code = response.status_code
        
        if status_code == 200:
            resp_text = response.text # 必须在 close 之前读取
            response.close()
            print("✅ Server OK (200)")
            parse_server_response(resp_text)
            return True, "OK"
        else:
            response.close()
            print("⚠️ Server returned Error:", status_code)
            return False, "Err:{}".format(status_code)
    except Exception as e:
        print("❌ POST HTTP Error:", e)
        return False, "Req Fail"

def update_light_logic(co2_val):
    global rgb_strip
    if rgb_strip is None: return "NO_STRIP"
    
    if not current_led_power:
        rgb_strip.fill_color(0x000000)
        return "POWER_OFF"
        
    if current_led_mode == "manual":
        rgb_strip.fill_color(current_led_color_hex)
        return "MANUAL_COLOR"
        
    if co2_val > 1500:
        rgb_strip.fill_color(0xff0000)
        return "AUTO_RED"
    elif co2_val > 1000:
        rgb_strip.fill_color(0xffff00)
        return "AUTO_YELLOW"
    else:
        rgb_strip.fill_color(0x00ff00)
        return "AUTO_GREEN"

def setup():
    global label_co2, label_temp, label_hum, label_net, label_light
    global i2c0, co2_0, wlan, rgb_strip
    M5.begin()
    Widgets.setRotation(0)
    Widgets.fillScreen(0x000000)
    
    label_co2 = Widgets.Label("CO2:   WAIT...", 5, 10, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    label_temp = Widgets.Label("Temp:  --- C", 5, 40, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    label_hum = Widgets.Label("Hum:   --- %", 5, 70, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    label_light = Widgets.Label("Lamp:  Init", 5, 100, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    label_net = Widgets.Label("Net:   Init", 5, 130, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    
    if setup_wifi(): 
        label_net.setText("Net:   Wi-Fi OK")
    else: 
        label_net.setText("Net:   Wi-Fi Fail")
        
    try:
        rgb_strip = RGB(io=LED_DATA_PIN, n=NUM_LEDS, type="RGB")
        rgb_strip.set_brightness(20) 
        rgb_strip.fill_color(0x000000)
        
        i2c0 = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)
        co2_0 = CO2Unit(i2c0)
        try:
            co2_0.set_stop_periodic_measurement()
            time.sleep(0.5)
        except: 
            pass
        co2_0.set_start_periodic_measurement()
        print("🟢 Hardware Setup Complete. Waiting 5 seconds for first CO2 reading...")
    except Exception as e: 
        print("❌ Hardware Init Error:", e)

def loop():
    global last_post_time
    M5.update()
    current_time = time.ticks_ms()
    
    try:
        if co2_0 is not None and co2_0.is_data_ready():
            co2_val = co2_0.co2
            temperature = round(co2_0.temperature, 1)
            humidity = round(co2_0.humidity, 1)
            
            label_co2.setText("CO2:   {} ppm".format(co2_val))
            label_temp.setText("Temp:  {} C".format(temperature))
            label_hum.setText("Hum:   {} %".format(humidity))
            
            if time.ticks_diff(current_time, last_post_time) >= POST_INTERVAL_MS:
                last_post_time = current_time
                ok, upload_status = upload_sensor_data(co2_val, temperature, humidity, "SYNCING...")
                label_net.setText("Net:   {}".format(upload_status))
                
            lamp_text = update_light_logic(co2_val)
            label_light.setText("Lamp:  {}".format(lamp_text))
                
    except Exception as exc: 
        print("❌ Sensor loop failed:", exc)
        
    time.sleep(0.1) # 提高一点主循环响应速度

if __name__ == "__main__":
    try:
        setup()
        while True: loop()
    except Exception as e: 
        print("Crash:", e)