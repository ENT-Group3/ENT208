
# M5Stack 双设备本地监控方案

这个版本把系统拆成两台 M5Stack：

1. **环境 / 灯光 M5**
   - 沿用你之前的 ENV + RGB 代码
   - 上传温度、湿度、气压、灯带状态

2. **水泵 / 土壤湿度 M5**
   - 读取电阻式湿度计
   - 计算土壤湿度百分比
   - 接收网页发来的“抽水 1 秒”命令

电脑端运行一个本地后端，同时提供网页面板。

---

## 文件说明

- `backend/app.py`
  - 电脑端后端 + 前端一体
  - 运行后访问 `http://127.0.0.1:5000`

- `m5_pump_sender.py`
  - 水泵 M5 的烧录代码

- `m5_env_sender_dual.py`
  - 可选：环境 M5 的双设备版上传脚本
  - 如果你原来的环境版已经正常上传，也可以继续用原版

---

## 电脑端启动

```bash
cd backend
python app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

---

## 环境 M5

如果你沿用旧版环境代码，只要它还在往 `/api/sensor` 上传下面这些字段就能兼容：

- `pressure_hpa`
- `temperature_c`
- `humidity_percent`
- `lamp_text`
- `ip`

---

## 水泵 M5 配置

修改 `m5_pump_sender.py` 顶部这几项：

```python
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"
SERVER_HOST = "你电脑在同一WiFi下的IP"
SERVER_PORT = 5000
```

### 引脚
默认：

- `MOISTURE_ADC_PIN = 33`
- `PUMP_RELAY_PIN = 26`

如果你接线不同，就改这两个值。

### 继电器高低电平
默认：

```python
PUMP_ACTIVE_LEVEL = 1
PUMP_INACTIVE_LEVEL = 0
```

如果你是低电平触发继电器，就改成：

```python
PUMP_ACTIVE_LEVEL = 0
PUMP_INACTIVE_LEVEL = 1
```

### 电阻计算参数
你必须确认自己的分压电路固定电阻值：

```python
FIXED_RESISTOR_OHM = 10000.0
```

湿度探头的两点标定已经按你给的数据写好了：

- 干燥：`23100 Ω`
- 水中：`31400 Ω`

湿度计算公式：

```text
moisture_percent = (R - dry) / (wet - dry) * 100
```

结果会自动限制在 `0~100%`。

---

## 网页功能

网页会显示两块区域：

### 环境 / 灯光 M5
- 温度
- 湿度
- 气压
- 灯带状态

### 水泵 / 土壤湿度 M5
- 土壤电阻
- 计算湿度
- ADC 原始值
- 泵状态
- “抽水 1 秒”按钮

---

## 水泵命令逻辑

网页点击一次按钮后，后端生成一个新的 `command_id`。

水泵 M5 会轮询 `/api/pump/command`，只执行**新的**命令编号，所以不会因为重复轮询而重复抽水。

---

## 常见问题

### 1. 网页能打开，但按钮没反应
先看水泵 M5 串口里有没有：
- `WiFi connected`
- `POST 200`

再看后端终端有没有：
- `[sensor:pump]`
- `[pump trigger]`

### 2. 湿度百分比不对
通常是这两个原因：
- `FIXED_RESISTOR_OHM` 填错了
- `SENSOR_TO_GND` 方向写反了

如果你发现“越湿数值越小”，把：

```python
SENSOR_TO_GND = True
```

改成：

```python
SENSOR_TO_GND = False
```

### 3. 点一次按钮，水泵没停
先检查继电器触发电平是否正确：
- 高电平触发：`1 / 0`
- 低电平触发：`0 / 1`

---

## 兼容说明

这个版本的后端会自动识别两类上传数据：

- 环境 M5：带温湿压字段
- 水泵 M5：带土壤湿度 / 电阻字段

所以你原先的环境 M5 逻辑不用大改。
