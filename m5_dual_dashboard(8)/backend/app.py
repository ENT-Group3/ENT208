import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = 5000

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>M5Stack 监控</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif; -webkit-font-smoothing: antialiased; background: linear-gradient(135deg, #e8f5e6 0%, #f5f9f4 100%); min-height: 100vh; display: flex; justify-content: center; align-items: flex-start; }
    .app { width: 440px; height: 956px; flex-shrink: 0; background: #fafbfa; border-radius: 52px; box-shadow: 0 24px 80px rgba(0,0,0,.22), 0 0 0 1px rgba(0,0,0,.08); display: flex; flex-direction: column; position: relative; overflow: hidden; transform: scale(0.9); transform-origin: top center; margin-bottom: -96px; }
    @media (min-width: 500px) { body { align-items: center; padding: 24px 0; min-height: 100vh; } }
    @media (max-width: 499px) { .app { width: 100%; height: 100vh; border-radius: 0; box-shadow: none; } }

    #splash { position: absolute; inset: 0; z-index: 999; background: linear-gradient(135deg, #A8D5A2 0%, #8BC88B 50%, #A8D5A2 100%); display: flex; align-items: center; justify-content: center; overflow: hidden; transition: opacity .5s ease; border-radius: inherit; }
    #splash.hidden { opacity: 0; pointer-events: none; }
    .sp-bg1 { position: absolute; top: -10%; right: -10%; width: 300px; height: 300px; border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.15) 0%, transparent 70%); }
    .sp-bg2 { position: absolute; bottom: -15%; left: -15%; width: 400px; height: 400px; border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.1) 0%, transparent 70%); }
    .sp-skip { position: absolute; top: 40px; right: 24px; padding: 10px 20px; background: rgba(255,255,255,.25); backdrop-filter: blur(10px); border: none; border-radius: 20px; color: white; font-size: 14px; font-weight: 500; cursor: pointer; transition: background .2s; z-index: 10; }
    .sp-skip:hover { background: rgba(255,255,255,.38); }
    .sp-body { text-align: center; animation: fadeUp .9s ease both; z-index: 5; }
    .sp-body h1 { font-size: 62px; font-weight: 400; color: #1a1a1a; letter-spacing: -1px; margin-bottom: 8px; }
    .sp-body p { font-size: 13px; color: #555; letter-spacing: 4px; text-transform: uppercase; }
    
    .page-title-block { padding: 36px 16px 8px 16px; }
    .page-main-title { font-size: 24px; font-weight: 700; color: #1a1a1a; letter-spacing: -0.5px; }
    .page-sub-title { font-size: 12px; color: #bbb; margin-top: 3px; }
    .page { display: none; flex: 1; overflow: hidden; min-height: 0; flex-direction: column; }
    .page.active { display: flex; }
    .page-scroll { flex: 1; overflow-y: auto; padding: 0 16px 24px; -webkit-overflow-scrolling: touch; }

    .section-header { display: flex; align-items: center; gap: 8px; margin: 20px 0 12px; }
    .section-header:first-child { margin-top: 4px; }
    .section-icon { width: 32px; height: 32px; border-radius: 10px; background: linear-gradient(135deg, #A8D5A2 0%, #8BC88B 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 4px 10px rgba(168,213,162,.3); }
    .section-title { font-size: 17px; font-weight: 700; color: #1a1a1a; }
    .section-status { margin-left: auto; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 999px; }
    .section-status.online  { background: rgba(168,213,162,.2); color: #2d6a4f; }
    .section-status.offline { background: rgba(239,68,68,.08);  color: #dc2626; }

    .stat-list { display: flex; flex-direction: column; gap: 10px; }
    .stat-card { background: white; border: 1.5px solid rgba(168,213,162,.45); border-radius: 18px; padding: 14px 18px; box-shadow: 0 2px 10px rgba(168,213,162,.12); display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .stat-label { font-size: 13px; color: #999; font-weight: 500; white-space: nowrap; }
    .stat-value { font-size: 22px; font-weight: 700; color: #1a1a1a; letter-spacing: -0.4px; text-align: right; }
    .stat-value.sm { font-size: 15px; font-weight: 600; color: #333; word-break: break-all; }

    /* ── LED Control Panel ── */
    .ctrl-panel { background: white; border: 1.5px solid rgba(168,213,162,.45); border-radius: 18px; padding: 16px; margin-top: 10px; box-shadow: 0 2px 10px rgba(168,213,162,.12); }
    .ctrl-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
    .ctrl-row:last-child { border-bottom: none; padding-bottom: 0; }
    .ctrl-label { font-size: 14px; font-weight: 600; color: #333; }
    
    .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }
    .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
    input:checked + .slider { background-color: #8BC88B; }
    input:checked + .slider:before { transform: translateX(20px); }
    
    select.ctrl-select { padding: 6px 10px; border-radius: 10px; border: 1px solid #ddd; background: #f9f9f9; font-size: 13px; outline: none; }
    
    .color-picker-wrapper { width: 32px; height: 32px; border-radius: 50%; overflow: hidden; border: 2px solid #eee; cursor: pointer; display: inline-block; }
    .color-picker-wrapper input[type="color"] { border: none; padding: 0; width: 150%; height: 150%; margin: -25%; cursor: pointer; }

    .pump-action { background: white; border: 1.5px solid rgba(168,213,162,.45); border-radius: 18px; padding: 16px; margin-top: 10px; }
    .pump-btn { width: 100%; padding: 15px; background: linear-gradient(135deg, #A8D5A2 0%, #8BC88B 100%); color: white; border: none; border-radius: 14px; font-size: 16px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 16px rgba(168,213,162,.35); transition: background .3s, opacity .15s, transform .15s; }
    .pump-btn:hover { opacity: .9; transform: translateY(-1px); }
    .pump-btn:active { transform: translateY(0); }
    .pump-btn:disabled { opacity: .55; cursor: not-allowed; }
    .pump-hint { margin-top: 10px; font-size: 12px; color: #aaa; text-align: center; }

    .chart-card { background: white; border: 1.5px solid rgba(168,213,162,.35); border-radius: 18px; padding: 12px 10px; margin-bottom: 12px; }
    .chart-title { font-size: 13px; font-weight: 600; color: #555; margin-bottom: 10px; }
    .chart-wrap  { position: relative; height: 160px; }

    .settings-group { background: white; border: 1.5px solid rgba(168,213,162,.35); border-radius: 18px; padding: 4px 16px; margin-bottom: 14px; }
    .settings-group-title { font-size: 11px; font-weight: 700; color: #A8D5A2; padding: 14px 0 4px; }
    .info-row { display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-bottom: 1px solid #f5f5f5; gap: 12px; }
    .info-row:last-child { border-bottom: none; }
    .info-key { font-size: 13px; color: #999; font-weight: 500; white-space: nowrap; }
    .info-val { font-size: 13px; font-weight: 600; color: #333; text-align: right; word-break: break-all; }
    .info-val.mono { font-family: ui-monospace, monospace; font-size: 12px; }

    #backToSplash { position: absolute; bottom: 20px; right: 16px; width: 14px; height: 14px; border-radius: 50%; background: rgba(0,0,0,.12); border: none; cursor: pointer; z-index: 300; }
    .bottom-nav { flex-shrink: 0; width: 100%; height: 68px; background: white; border-top: 1px solid #f0f0f0; display: flex; justify-content: space-around; align-items: center; padding: 0 4px 8px; z-index: 100; }
    .nav-btn { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; border: none; background: transparent; cursor: pointer; padding: 6px 2px; }
    .nav-icon-wrap { width: 36px; height: 26px; border-radius: 13px; display: flex; align-items: center; justify-content: center; }
    .nav-icon-wrap.active { background: rgba(168,213,162,.18); }
    .nav-icon  { font-size: 18px; }
    .nav-label { font-size: 9px; color: #bbb; font-weight: 500; }
    .nav-label.active { color: #A8D5A2; font-weight: 700; }

    /* ── iOS toggle ── */
    .ios-sw { position: relative; display: inline-block; width: 51px; height: 31px; flex-shrink: 0; }
    .ios-sw input { opacity: 0; width: 0; height: 0; }
    .ios-track { position: absolute; cursor: pointer; inset: 0; background: #e5e5ea; border-radius: 31px; transition: background .3s; }
    .ios-track:before { content: ""; position: absolute; width: 27px; height: 27px; left: 2px; top: 2px; background: white; border-radius: 50%; box-shadow: 0 2px 6px rgba(0,0,0,.18); transition: transform .3s; }
    .ios-sw input:checked + .ios-track { background: #A8D5A2; }
    .ios-sw input:checked + .ios-track:before { transform: translateX(20px); }

    /* ── Range slider ── */
    .rng-wrap { margin-bottom: 16px; }
    .rng-wrap:last-of-type { margin-bottom: 0; }
    .rng-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .rng-name { font-size: 13px; color: #555; font-weight: 500; }
    .rng-val  { font-size: 13px; font-weight: 700; color: #2d6a4f; min-width: 52px; text-align: right; }
    .rng-hints { display: flex; justify-content: space-between; margin-top: 5px; }
    .rng-hint { font-size: 10px; color: #ccc; }
    input[type=range].app-slider { -webkit-appearance: none; width: 100%; height: 4px; border-radius: 2px; background: #e8e8e8; outline: none; cursor: pointer; }
    input[type=range].app-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%; background: linear-gradient(135deg, #A8D5A2, #8BC88B); box-shadow: 0 2px 6px rgba(168,213,162,.5); cursor: pointer; }

    /* ── Mode grid ── */
    .mode-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .mode-card { background: white; border: 1.5px solid rgba(168,213,162,.35); border-radius: 16px; padding: 18px 10px; text-align: center; cursor: pointer; transition: all .2s; user-select: none; }
    .mode-card.selected { border-color: #8BC88B; background: rgba(168,213,162,.12); box-shadow: 0 0 0 2px rgba(168,213,162,.35); }
    .mode-card-name { font-size: 14px; font-weight: 600; color: #555; letter-spacing: 0.2px; }
    .mode-card.selected .mode-card-name { color: #2d6a4f; }

    /* ── Color preview ── */
    .color-preview-lbl { font-size: 12px; color: #999; font-weight: 500; margin-bottom: 8px; }
    .color-preview { border-radius: 14px; height: 48px; border: 1.5px solid rgba(168,213,162,.25); transition: background .3s; }

    /* ── Quick buttons ── */
    .quick-btns { display: flex; gap: 8px; margin-top: 12px; }
    .quick-btn { flex: 1; padding: 10px 0; border: 1.5px solid rgba(168,213,162,.45); border-radius: 12px; background: white; font-size: 12px; font-weight: 600; color: #2d6a4f; cursor: pointer; transition: all .2s; }
    .quick-btn:hover { background: rgba(168,213,162,.12); border-color: #8BC88B; }
    .quick-btn.qactive { background: rgba(168,213,162,.18); border-color: #8BC88B; }

    /* ── Setting row ── */
    .set-row { display: flex; justify-content: space-between; align-items: center; padding: 13px 0; border-bottom: 1px solid #f5f5f5; gap: 12px; }
    .set-row:last-child { border-bottom: none; }
    .set-key { font-size: 14px; color: #333; font-weight: 500; }
    .set-select { padding: 6px 10px; border: 1.5px solid rgba(168,213,162,.4); border-radius: 10px; font-size: 13px; font-weight: 500; color: #333; background: #f7faf7; outline: none; -webkit-appearance: none; appearance: none; }
    .time-input { padding: 6px 10px; border: 1.5px solid rgba(168,213,162,.45); border-radius: 12px; font-size: 13px; font-weight: 600; color: #333; background: #f7faf7; outline: none; width: 88px; text-align: center; cursor: pointer; }
    .time-input:focus { border-color: #8BC88B; background: white; }
    .time-input::-webkit-calendar-picker-indicator { opacity: 0; position: absolute; width: 100%; height: 100%; top: 0; left: 0; cursor: pointer; }

    /* ── Time wheel ── */
    .time-wheel-wrap { display: flex; align-items: center; gap: 4px; }
    .time-wheel { display: inline-block; width: 38px; padding: 6px 0; border: 1.5px solid rgba(168,213,162,.45); border-radius: 12px; font-size: 15px; font-weight: 700; color: #333; background: #f7faf7; text-align: center; cursor: ns-resize; user-select: none; transition: border-color .2s, background .2s; }
    .time-wheel:hover { border-color: #8BC88B; background: white; }
    .time-wheel-sep { font-size: 15px; font-weight: 700; color: #999; }s select { -webkit-appearance: none; appearance: none; border: 1.5px solid rgba(168,213,162,.45); border-radius: 12px; padding: 10px 14px; font-size: 22px; font-weight: 700; color: #1a1a1a; background: #f7faf7; outline: none; text-align: center; width: 80px; }
    .    /* ── Pump status ── */
    .pump-st-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f5f5f5; gap: 8px; }
    .pump-st-key { font-size: 14px; color: #555; font-weight: 500; }
    .pump-st-badge { padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }
    .pump-st-badge.idle    { background: rgba(168,213,162,.15); color: #2d6a4f; }
    .pump-st-badge.running { background: rgba(79,195,247,.15);  color: #0277bd; }

    /* ── Save button ── */
    .save-btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #A8D5A2 0%, #8BC88B 100%); color: white; border: none; border-radius: 16px; font-size: 16px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 16px rgba(168,213,162,.35); margin-top: 8px; transition: transform .15s, opacity .15s; }
    .save-btn:hover  { transform: translateY(-1px); }
    .save-btn:active { transform: translateY(0); }

    @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    ::-webkit-scrollbar { width: 0; background: transparent; }
    * { scrollbar-width: none; }

    /* ── Dark mode ── */
    .dark body { background: linear-gradient(135deg, #1a2e1a 0%, #1e2a1e 100%); }
    .dark .app { background: #1c1c1e; box-shadow: 0 24px 80px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.06); }
    .dark .page-main-title { color: #f0f0f0; }
    .dark .page-sub-title { color: #666; }
    .dark .section-title { color: #f0f0f0; }
    .dark .stat-card { background: #2c2c2e; border-color: rgba(168,213,162,.2); box-shadow: none; }
    .dark .stat-label { color: #888; }
    .dark .stat-value { color: #f0f0f0; }
    .dark .stat-value.sm { color: #ccc; }
    .dark .settings-group { background: #2c2c2e; border-color: rgba(168,213,162,.15); }
    .dark .settings-group-title { color: #8BC88B; }
    .dark .info-row { border-bottom-color: #3a3a3c; }
    .dark .info-key { color: #888; }
    .dark .info-val { color: #ddd; }
    .dark .set-key { color: #ddd; }
    .dark .set-row { border-bottom-color: #3a3a3c; }
    .dark .set-select { background: #3a3a3c; border-color: rgba(168,213,162,.25); color: #ddd; }
    .dark .bottom-nav { background: #2c2c2e; border-top-color: #3a3a3c; }
    .dark .nav-label { color: #666; }
    .dark .chart-card { background: #2c2c2e; border-color: rgba(168,213,162,.15); }
    .dark .chart-title { color: #aaa; }
    .dark .ctrl-panel { background: #2c2c2e; border-color: rgba(168,213,162,.2); }
    .dark .ctrl-row { border-bottom-color: #3a3a3c; }
    .dark .ctrl-label { color: #ddd; }
    .dark .pump-action { background: #2c2c2e; border-color: rgba(168,213,162,.2); }
    .dark .pump-hint { color: #666; }
    .dark .mode-card { background: #2c2c2e; border-color: rgba(168,213,162,.2); }
    .dark .mode-card-name { color: #aaa; }
    .dark .mode-card.selected { background: rgba(168,213,162,.1); }
    .dark .time-wheel { background: #3a3a3c; border-color: rgba(168,213,162,.25); color: #ddd; }
    .dark .time-wheel-sep { color: #666; }
    .dark .rng-name { color: #aaa; }
    .dark .rng-hint { color: #555; }
    .dark input[type=range].app-slider { background: #3a3a3c; }
    .dark .pump-st-key { color: #aaa; }
    .dark .pump-st-row { border-bottom-color: #3a3a3c; }
    .dark .sp-body h1 { color: #f0f0f0; }
    .dark .sp-body p { color: #aaa; }
    .dark .color-preview-lbl { color: #888; }
    .dark .quick-btn { background: #2c2c2e; border-color: rgba(168,213,162,.25); color: #8BC88B; }
    .dark .quick-btn.qactive { background: rgba(168,213,162,.12); }
  </style>
</head>
<body>
<div class="app">

  <div id="splash">
    <div class="sp-bg1"></div><div class="sp-bg2"></div>
    <button class="sp-skip" id="splashSkip">跳过</button>
    <div class="sp-body">
      <h1>mariana</h1><p>ROOTED IN NATURE</p>
    </div>
  </div>

  <div class="page active" id="pageHome">
    <div class="page-scroll">
    <div class="page-title-block">
      <div class="page-main-title" data-i18n="home_title">智能花盆监控</div>
      <div class="page-sub-title" data-i18n="home_sub">实时环境数据监控与智能控制</div>
    </div>
    
    <div class="section-header fade-up">
      <div class="section-icon">🌡️</div>
      <span class="section-title" data-i18n="env_data">环境数据</span>
      <span id="envOnlineBadge" class="section-status offline" data-i18n="offline">离线</span>
    </div>
    <div class="stat-list fade-up">
      <div class="stat-card"><span class="stat-label" data-i18n="temperature">环境温度</span><span class="stat-value" id="temperature">--</span></div>
      <div class="stat-card"><span class="stat-label" data-i18n="humidity">空气湿度</span><span class="stat-value" id="humidity">--</span></div>
      <div class="stat-card"><span class="stat-label" data-i18n="co2">CO2浓度</span><span class="stat-value" id="co2">--</span></div>
      <div class="stat-card"><span class="stat-label" data-i18n="soil">土壤湿度</span><span class="stat-value" id="soilMoisture">--</span></div>
    </div>

    <div class="section-header fade-up">
      <div class="section-icon">🔧</div>
      <span class="section-title" data-i18n="hw_status">硬件状态</span>
    </div>
    <div class="stat-list fade-up">
      <div class="stat-card">
        <span class="stat-label" data-i18n="led_status">灯带状态</span>
        <span class="stat-value sm" id="lampText">--</span>
      </div>
      <div class="stat-card">
        <span class="stat-label" data-i18n="led_color">灯带颜色</span>
        <span style="display:flex;align-items:center;gap:8px;">
          <span id="ledColorDot" style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#f7faf7;border:1.5px solid rgba(168,213,162,.4);flex-shrink:0;"></span>
        </span>
      </div>
      <div class="stat-card">
        <span class="stat-label" data-i18n="pump_status">水泵状态</span>
        <span class="stat-value sm" id="pumpStatus">--</span>
      </div>
    </div>

    <div class="settings-group fade-up" style="padding:4px 16px 16px; margin-top:10px;">
      <div style="position:relative;">
        <div class="pump-st-row" style="padding-right:80px;">
          <span class="pump-st-key" data-i18n="pump_status">水泵状态</span>
          <span class="pump-st-badge idle" id="homePumpStatusBadge" data-i18n="standby">待机</span>
        </div>
        <div style="position:absolute;right:0;top:2px;display:flex;align-items:center;gap:3px;background:#f7faf7;border:1.5px solid rgba(168,213,162,.45);border-radius:8px;padding:2px 6px;">
          <span class="time-wheel" id="homeDurWheel" data-val="5" onwheel="wheelDur(event,this)" style="width:18px;height:20px;font-size:12px;padding:0;border-radius:6px;">5</span>
          <span style="font-size:11px;color:#999;font-weight:500;" data-i18n="sec_unit">秒</span>
        </div>
      </div>
      <div style="margin-top:14px;">
        <button class="pump-btn" id="homeManualWaterBtn" onclick="manualWater('home')" data-i18n="water_now">立即浇水</button>
        <p class="pump-hint" id="homeManualWaterHint" style="display:none;"></p>
      </div>
    </div>
    </div>
  </div>

  <div class="page" id="pageHistory">
    <div class="page-scroll">
    <div class="page-title-block"><div class="page-main-title" data-i18n="history_title">数据历史</div></div>
    <div class="chart-card"><div class="chart-title" data-i18n="chart_temp">🌡️ 温度 (°C)</div><div class="chart-wrap"><canvas id="chartTemp"></canvas></div></div>
    <div class="chart-card"><div class="chart-title" data-i18n="chart_hum">💧 环境湿度 (%)</div><div class="chart-wrap"><canvas id="chartHumidity"></canvas></div></div>
    <div class="chart-card"><div class="chart-title" data-i18n="chart_co2">🟢 CO2 浓度 (ppm)</div><div class="chart-wrap"><canvas id="chartCo2"></canvas></div></div>
    <div class="chart-card"><div class="chart-title" data-i18n="chart_soil">🌱 土壤湿度 (%)</div><div class="chart-wrap"><canvas id="chartSoil"></canvas></div></div>
    </div>
  </div>

  <div class="page" id="pageSettings">
    <div class="page-scroll">
    <div class="page-title-block"><div class="page-main-title" data-i18n="settings_title">系统设置</div></div>

    <!-- 设备信息 -->
    <div class="settings-group">
      <div class="settings-group-title" data-i18n="device_info">设备信息</div>
      <div class="info-row"><span class="info-key" data-i18n="device_name">设备名称</span><span class="info-val">Mariana M5</span></div>
      <div class="info-row"><span class="info-key" data-i18n="device_id">设备编号</span><span class="info-val" id="settingEnvDeviceId">--</span></div>
      <div class="info-row"><span class="info-key" data-i18n="conn_status">连接状态</span><span class="info-val" id="settingConnStatus" data-i18n-id="not_connected">未连接</span></div>
      <div class="info-row"><span class="info-key" data-i18n="firmware">固件版本</span><span class="info-val">v1.0.0</span></div>
    </div>

    <!-- 通用设置 -->
    <div class="settings-group">
      <div class="settings-group-title" data-i18n="general_settings">通用设置</div>
      <div class="info-row">
        <span class="info-key" data-i18n="basic_settings">基础设置</span>
        <span class="info-val" style="color:#bbb;font-size:12px;">›</span>
      </div>
      <div class="info-row">
        <span class="info-key" data-i18n="notifications">通知提醒</span>
        <label class="ios-sw"><input type="checkbox" id="swNotify" checked><span class="ios-track"></span></label>
      </div>
      <div class="info-row">
        <span class="info-key" data-i18n="auto_sync">自动同步数据</span>
        <label class="ios-sw"><input type="checkbox" id="swAutoSync" checked><span class="ios-track"></span></label>
      </div>
      <div class="info-row">
        <span class="info-key" data-i18n="dark_mode">深色模式</span>
        <label class="ios-sw"><input type="checkbox" id="swDarkMode"><span class="ios-track"></span></label>
      </div>
      <div class="info-row">
        <span class="info-key" data-i18n="language">语言设置</span>
        <select class="set-select" id="langSelect">
          <option value="zh">简体中文</option>
          <option value="en">English</option>
        </select>
      </div>
    </div>

    <!-- 提醒设置 — 入口词条 -->
    <div class="settings-group">
      <div class="info-row" style="cursor:pointer;" onclick="switchPage('pageThreshold')">
        <span class="info-key" data-i18n="threshold_settings">提醒设置</span>
        <span class="info-val" style="color:#ccc;font-size:18px;font-weight:300;">›</span>
      </div>
    </div>

    <!-- 设备管理 -->
    <div class="settings-group">
      <div class="settings-group-title" data-i18n="device_mgmt">设备管理</div>
      <div class="info-row"><span class="info-key" data-i18n="wifi_settings">Wi-Fi 设置</span><span class="info-val" style="color:#ccc;font-size:18px;font-weight:300;">›</span></div>
      <div class="info-row"><span class="info-key" data-i18n="check_update">检查更新</span><span class="info-val" style="color:#ccc;font-size:18px;font-weight:300;">›</span></div>
      <div class="info-row"><span class="info-key" data-i18n="factory_reset">恢复出厂设置</span><span class="info-val" style="color:#ccc;font-size:18px;font-weight:300;">›</span></div>
    </div>

    <!-- 原有设备连接信息 -->
    <div class="settings-group">
      <div class="settings-group-title" data-i18n="device1">设备1</div>
      <div class="info-row"><span class="info-key" data-i18n="device_ip">设备 IP</span><span class="info-val" id="settingEnvDeviceIp">--</span></div>
      <div class="info-row"><span class="info-key" data-i18n="recv_time">收到时间</span><span class="info-val" id="envServerTime">--</span></div>
      <div class="info-row"><span class="info-key" data-i18n="data_delay">数据延迟</span><span class="info-val" id="envAge">--</span></div>
    </div>
    <div class="settings-group">
      <div class="settings-group-title" data-i18n="device2">设备2</div>
      <div class="info-row"><span class="info-key" data-i18n="device_id">设备 ID</span><span class="info-val" id="settingPumpDeviceId">--</span></div>
      <div class="info-row"><span class="info-key" data-i18n="device_ip">设备 IP</span><span class="info-val" id="settingPumpDeviceIp">--</span></div>
      <div class="info-row"><span class="info-key" data-i18n="recv_time">收到时间</span><span class="info-val" id="pumpServerTime">--</span></div>
      <div class="info-row"><span class="info-key" data-i18n="last_cmd">最近命令</span><span class="info-val mono" id="lastCommand">--</span></div>
    </div>

    <!-- 关于 -->
    <div class="settings-group">
      <div class="settings-group-title" data-i18n="about">关于</div>
      <div class="info-row"><span class="info-key" data-i18n="terms">用户协议</span><span class="info-val" style="color:#bbb;font-size:12px;">›</span></div>
      <div class="info-row"><span class="info-key" data-i18n="privacy">隐私政策</span><span class="info-val" style="color:#bbb;font-size:12px;">›</span></div>
      <div class="info-row"><span class="info-key" data-i18n="contact">联系我们</span><span class="info-val" style="color:#bbb;font-size:12px;">›</span></div>
    </div>

    </div>
  </div>

  <!-- ══ PAGE: LIGHT ══ -->
  <div class="page" id="pageLight">
    <div class="page-scroll">
      <div class="page-title-block">
        <div class="page-main-title" data-i18n="light_title">灯光调试</div>
        <div class="page-sub-title" data-i18n="light_sub">灯光效果与定时控制</div>
      </div>

      <!-- 板块1：灯光效果选择 -->
      <div class="section-header"><div class="section-icon">🌿</div><span class="section-title" data-i18n="light_effect">灯光效果选择</span></div>
      <div class="settings-group" style="padding:14px 16px;">
        <div class="mode-grid">
          <div class="mode-card selected" data-mode="grow" onclick="selectMode(this)">
            <div class="mode-card-name" data-i18n="mode_grow">生长模式</div>
          </div>
          <div class="mode-card" data-mode="bloom" onclick="selectMode(this)">
            <div class="mode-card-name" data-i18n="mode_bloom">开花模式</div>
          </div>
          <div class="mode-card" data-mode="seedling" onclick="selectMode(this)">
            <div class="mode-card-name" data-i18n="mode_seedling">育苗模式</div>
          </div>
          <div class="mode-card" data-mode="custom" onclick="selectMode(this)">
            <div class="mode-card-name" data-i18n="mode_custom">自定义</div>
          </div>
        </div>
      </div>

      <!-- 板块2：灯光色彩调节 -->
      <div class="section-header"><div class="section-icon">🎨</div><span class="section-title" data-i18n="light_color">灯光色彩调节</span></div>
      <div class="settings-group" style="padding:16px;">
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="red_spectrum">红色光谱</span><span class="rng-val" id="redVal">60%</span></div>
          <input type="range" class="app-slider" id="redSlider" min="0" max="100" value="60" oninput="updateColor(true)">
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="blue_spectrum">蓝色光谱</span><span class="rng-val" id="blueVal">40%</span></div>
          <input type="range" class="app-slider" id="blueSlider" min="0" max="100" value="40" oninput="updateColor(true)">
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="warm_ratio">暖光比例</span><span class="rng-val" id="warmVal">30%</span></div>
          <input type="range" class="app-slider" id="warmSlider" min="0" max="100" value="30" oninput="updateColor(true)">
        </div>
        <div style="margin-top:14px;">
          <div class="color-preview-lbl" data-i18n="color_preview">当前色彩预览</div>
          <div class="color-preview" id="colorPreview"></div>
        </div>
      </div>

      <!-- 板块2b：灯带控制 -->
      <div class="section-header"><div class="section-icon">💡</div><span class="section-title" data-i18n="led_ctrl">灯带控制</span></div>
      <div class="settings-group" style="padding:4px 16px;">
        <div class="set-row">
          <span class="set-key" data-i18n="led_power">💡 灯带开关</span>
          <label class="ios-sw"><input type="checkbox" id="uiLedPower" checked><span class="ios-track"></span></label>
        </div>
        <div class="set-row">
          <span class="set-key" data-i18n="led_mode">⚙️ 控制模式</span>
          <select class="set-select" id="uiLedMode">
            <option value="auto" data-i18n="mode_auto">自动 (随CO2)</option>
            <option value="manual" data-i18n="mode_manual">手动 (自定义颜色)</option>
          </select>
        </div>
        <div class="set-row" id="colorRow">
          <span class="set-key" data-i18n="led_color_pick">🎨 选择颜色</span>
          <div class="color-picker-wrapper">
            <input type="color" id="uiLedColor" value="#00ff00">
          </div>
        </div>
        <p style="font-size:11px;color:#aaa;text-align:center;padding:8px 0 4px;" data-i18n="led_sync_hint">设置将在 5 秒内同步至 M5Stack</p>
      </div>

      <!-- 板块3：灯光强度调节 -->
      <div class="section-header"><div class="section-icon">🔆</div><span class="section-title" data-i18n="light_intensity">灯光强度调节</span></div>
      <div class="settings-group" style="padding:16px;">
        <div class="rng-top"><span class="rng-name" data-i18n="intensity">强度</span><span class="rng-val" id="brightVal">70%</span></div>
        <input type="range" class="app-slider" id="brightSlider" min="0" max="100" value="70" oninput="document.getElementById('brightVal').textContent=this.value+'%'; updateQuickBtns();">
        <div class="rng-hints"><span class="rng-hint" data-i18n="light_weak">弱光</span><span class="rng-hint" data-i18n="light_mid">适中</span><span class="rng-hint" data-i18n="light_strong">强光</span></div>
        <div class="quick-btns">
          <button class="quick-btn" onclick="setBright(20)" data-i18n="bright_low">低亮度</button>
          <button class="quick-btn qactive" onclick="setBright(50)" data-i18n="bright_mid">中亮度</button>
          <button class="quick-btn" onclick="setBright(80)" data-i18n="bright_high">高亮度</button>
        </div>
      </div>

      <!-- 板块4：定时设置 -->
      <div class="section-header"><div class="section-icon">⏰</div><span class="section-title" data-i18n="timer_settings">定时设置</span></div>
      <div class="settings-group" style="padding:4px 16px;">
        <div class="set-row">
          <span class="set-key" data-i18n="auto_light">自动开关灯</span>
          <label class="ios-sw"><input type="checkbox" id="autoLightSwitch" checked><span class="ios-track"></span></label>
        </div>
        <div class="set-row">
          <span class="set-key" data-i18n="light_on_time">开灯时间</span>
          <div class="time-wheel-wrap">
            <span class="time-wheel" id="lightOnH" data-val="6" onwheel="wheelTime(event,this,24)">06</span>
            <span class="time-wheel-sep">:</span>
            <span class="time-wheel" id="lightOnM" data-val="0" onwheel="wheelTime(event,this,60)">00</span>
          </div>
        </div>
        <div class="set-row">
          <span class="set-key" data-i18n="light_off_time">关灯时间</span>
          <div class="time-wheel-wrap">
            <span class="time-wheel" id="lightOffH" data-val="22" onwheel="wheelTime(event,this,24)">22</span>
            <span class="time-wheel-sep">:</span>
            <span class="time-wheel" id="lightOffM" data-val="0" onwheel="wheelTime(event,this,60)">00</span>
          </div>
        </div>
      </div>

      <div style="padding:0 0 8px;">
        <button class="save-btn" onclick="saveLightSettings()" data-i18n="save_settings">保存设置</button>
      </div>
    </div>
  </div><!-- /pageLight -->

  <!-- ══ PAGE: PUMP ══ -->
  <div class="page" id="pagePump">
    <div class="page-scroll">
      <div class="page-title-block">
        <div class="page-main-title" data-i18n="pump_title">水泵调试</div>
        <div class="page-sub-title" data-i18n="pump_sub">浇水条件与手动控制</div>
      </div>

      <!-- 板块1：水泵触发条件 -->
      <div class="section-header"><div class="section-icon">⚙️</div><span class="section-title" data-i18n="pump_trigger">水泵触发条件</span></div>
      <div class="settings-group" style="padding:16px;">
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="temp_thresh">温度阈值</span><span class="rng-val" id="tempThreshVal">25°</span></div>
          <input type="range" class="app-slider" id="tempThresh" min="0" max="50" value="25" oninput="document.getElementById('tempThreshVal').textContent=this.value+'°'">
          <div class="rng-hints"><span class="rng-hint">0°</span><span class="rng-hint">25°</span><span class="rng-hint">50°</span></div>
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="air_hum_thresh">空气湿度阈值</span><span class="rng-val" id="airHumThreshVal">50%</span></div>
          <input type="range" class="app-slider" id="airHumThresh" min="20" max="80" value="50" oninput="document.getElementById('airHumThreshVal').textContent=this.value+'%'">
          <div class="rng-hints"><span class="rng-hint">20%</span><span class="rng-hint">50%</span><span class="rng-hint">80%</span></div>
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="soil_thresh">土壤湿度阈值</span><span class="rng-val" id="soilThreshVal">30%</span></div>
          <input type="range" class="app-slider" id="soilThresh" min="10" max="60" value="30" oninput="document.getElementById('soilThreshVal').textContent=this.value+'%'">
          <div class="rng-hints"><span class="rng-hint">10%</span><span class="rng-hint">35%</span><span class="rng-hint">60%</span></div>
        </div>
        <div class="set-row" style="margin-top:4px; border-bottom:none;">
          <span class="set-key" data-i18n="auto_watering">自动浇水</span>
          <label class="ios-sw"><input type="checkbox" id="autoWaterSwitch2" checked><span class="ios-track"></span></label>
        </div>
      </div>

      <!-- 板块2：浇水时长调节 -->
      <div class="section-header"><div class="section-icon">⏱️</div><span class="section-title" data-i18n="water_duration">浇水时长调节</span></div>
      <div class="settings-group" style="padding:16px;">
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="single_duration">单次浇水时长</span><span class="rng-val" id="waterDurVal">5 秒</span></div>
          <input type="range" class="app-slider" id="waterDur" min="1" max="20" value="5" oninput="document.getElementById('waterDurVal').textContent=this.value+' 秒'">
          <div class="rng-hints"><span class="rng-hint">1 秒</span><span class="rng-hint">10 秒</span><span class="rng-hint">20 秒</span></div>
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="min_interval">最小浇水间隔</span><span class="rng-val" id="waterIntervalVal">30 分钟</span></div>
          <input type="range" class="app-slider" id="waterInterval" min="0" max="120" value="30" oninput="document.getElementById('waterIntervalVal').textContent=this.value+' 分钟'">
          <div class="rng-hints"><span class="rng-hint">0</span><span class="rng-hint">60 分钟</span><span class="rng-hint">120 分钟</span></div>
        </div>
        <div class="set-row" style="margin-top:4px; border-bottom:none;">
          <span class="set-key" data-i18n="auto_watering">自动浇水</span>
          <label class="ios-sw"><input type="checkbox" id="autoWaterSwitch" checked><span class="ios-track"></span></label>
        </div>
      </div>

      <!-- 板块3：手动控制 -->
      <div class="section-header"><div class="section-icon">🕹️</div><span class="section-title" data-i18n="manual_ctrl">手动控制</span></div>
      <div class="settings-group" style="padding:4px 16px 16px;">
        <div style="position:relative;">
          <div class="pump-st-row" style="padding-right:80px;">
            <span class="pump-st-key" data-i18n="pump_status">水泵状态</span>
            <span class="pump-st-badge idle" id="pumpStatusBadge" data-i18n="standby">待机</span>
          </div>
          <div style="position:absolute;right:0;top:2px;display:flex;align-items:center;gap:3px;background:#f7faf7;border:1.5px solid rgba(168,213,162,.45);border-radius:8px;padding:2px 6px;">
            <span class="time-wheel" id="pumpDurWheel" data-val="5" onwheel="wheelDur(event,this)" style="width:18px;height:20px;font-size:12px;padding:0;border-radius:6px;">5</span>
            <span style="font-size:11px;color:#999;font-weight:500;" data-i18n="sec_unit">秒</span>
          </div>
        </div>
        <div style="margin-top:14px;">
          <button class="pump-btn" id="manualWaterBtn" onclick="manualWater('pump')" data-i18n="water_now">立即浇水</button>
          <p class="pump-hint" id="manualWaterHint" style="display:none;"></p>
        </div>
      </div>

    </div>
  </div><!-- /pagePump -->

  <!-- ══ PAGE: THRESHOLD (sub-page of settings) ══ -->
  <div class="page" id="pageThreshold">
    <div class="page-scroll">
      <div class="page-title-block">
        <div style="display:flex;align-items:center;gap:10px;">
          <button onclick="switchPage('pageSettings')" style="background:none;border:none;cursor:pointer;font-size:18px;color:#999;padding:0;line-height:1;">‹</button>
          <div class="page-main-title" data-i18n="threshold_settings">提醒设置</div>
        </div>
        <div class="page-sub-title" data-i18n="thresh_sub">设置各项环境指标的提醒阈值</div>
      </div>

      <div class="settings-group" style="padding:4px 16px;">
        <div class="set-row">
          <span class="set-key" data-i18n="alert_notify">提醒通知</span>
          <label class="ios-sw"><input type="checkbox" id="threshNotifySwitch" checked><span class="ios-track"></span></label>
        </div>
      </div>

      <div class="settings-group" style="padding:16px;margin-top:10px;">
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="temp_alert">温度提醒（°C）</span><span class="rng-val" id="stTempVal">28°</span></div>
          <input type="range" class="app-slider" id="stTemp" min="0" max="50" value="28" oninput="document.getElementById('stTempVal').textContent=this.value+'°'">
          <div class="rng-hints"><span class="rng-hint">0°</span><span class="rng-hint">25°</span><span class="rng-hint">50°</span></div>
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="air_alert">空气湿度提醒（%）</span><span class="rng-val" id="stAirVal">60%</span></div>
          <input type="range" class="app-slider" id="stAir" min="20" max="80" value="60" oninput="document.getElementById('stAirVal').textContent=this.value+'%'">
          <div class="rng-hints"><span class="rng-hint">20%</span><span class="rng-hint">50%</span><span class="rng-hint">80%</span></div>
        </div>
        <div class="rng-wrap">
          <div class="rng-top"><span class="rng-name" data-i18n="soil_alert">土壤湿度提醒（%）</span><span class="rng-val" id="stSoilVal">35%</span></div>
          <input type="range" class="app-slider" id="stSoil" min="10" max="60" value="35" oninput="document.getElementById('stSoilVal').textContent=this.value+'%'">
          <div class="rng-hints"><span class="rng-hint">10%</span><span class="rng-hint">35%</span><span class="rng-hint">60%</span></div>
        </div>
      </div>

      <div style="padding:0 0 8px;">
        <button class="save-btn" onclick="saveThreshSettings()" data-i18n="save_settings">保存设置</button>
      </div>
    </div>
  </div><!-- /pageThreshold -->

  <button id="backToSplash" title="返回品牌页"></button>
  <nav class="bottom-nav">
    <button class="nav-btn" data-target="pageHome"><div class="nav-icon-wrap active" id="navWrap-pageHome"><span class="nav-icon">🏡</span></div><span class="nav-label active" id="navLabel-pageHome" data-i18n="nav_home">首页</span></button>
    <button class="nav-btn" data-target="pageLight"><div class="nav-icon-wrap" id="navWrap-pageLight"><span class="nav-icon">💡</span></div><span class="nav-label" id="navLabel-pageLight" data-i18n="nav_light">灯光</span></button>
    <button class="nav-btn" data-target="pagePump"><div class="nav-icon-wrap" id="navWrap-pagePump"><span class="nav-icon">💧</span></div><span class="nav-label" id="navLabel-pagePump" data-i18n="nav_pump">水泵</span></button>
    <button class="nav-btn" data-target="pageHistory"><div class="nav-icon-wrap" id="navWrap-pageHistory"><span class="nav-icon">📈</span></div><span class="nav-label" id="navLabel-pageHistory" data-i18n="nav_history">历史</span></button>
    <button class="nav-btn" data-target="pageSettings"><div class="nav-icon-wrap" id="navWrap-pageSettings"><span class="nav-icon">⚙️</span></div><span class="nav-label" id="navLabel-pageSettings" data-i18n="nav_settings">设置</span></button>
  </nav>

</div>

<script>
function hideSplash() { const s=document.getElementById("splash"); s.classList.add("hidden"); setTimeout(()=>{s.style.display="none";},520); }
(function(){ document.getElementById("splashSkip").addEventListener("click", hideSplash); setTimeout(hideSplash, 2000); })();
document.getElementById("backToSplash").addEventListener("click", () => { const s=document.getElementById("splash"); s.style.display="flex"; s.offsetHeight; s.classList.remove("hidden"); });

const pages = ["pageHome", "pageLight", "pagePump", "pageHistory", "pageSettings", "pageThreshold"];
let activePage = "pageHome";
function switchPage(id) {
  pages.forEach(p => {
    const pg = document.getElementById(p); if(pg) pg.classList.toggle("active", p===id);
    const nw = document.getElementById("navWrap-"+p); if(nw) nw.classList.toggle("active", p===id);
    const nl = document.getElementById("navLabel-"+p); if(nl) nl.classList.toggle("active", p===id);
  });
  activePage = id;
  if(id==="pageHistory") setTimeout(renderCharts, 30);
}
document.querySelectorAll(".nav-btn").forEach(btn => btn.addEventListener("click", () => switchPage(btn.dataset.target)));
// 页面加载后立即初始化图表（脚本在body末尾，DOM已就绪，直接延迟执行）
setTimeout(renderCharts, 150);

/* ── Dark mode ── */
const appEl = document.querySelector(".app");
document.getElementById("swDarkMode").addEventListener("change", function() {
  if (this.checked) {
    appEl.classList.add("dark");
    document.body.classList.add("dark");
  } else {
    appEl.classList.remove("dark");
    document.body.classList.remove("dark");
  }
  // 深色模式下更新图表颜色
  const gridColor = this.checked ? "rgba(255,255,255,.06)" : "rgba(0,0,0,.04)";
  const tickColor = this.checked ? "#666" : "#bbb";
  Object.values(chartInstances).forEach(c => {
    c.options.scales.x.ticks.color = tickColor;
    c.options.scales.x.grid.color  = gridColor;
    c.options.scales.y.ticks.color = tickColor;
    c.options.scales.y.grid.color  = gridColor;
    c.update();
  });
});

/* ── i18n ── */
const i18n = {
  zh: {
    home_title:"智能花盆监控", home_sub:"实时环境数据监控与智能控制",
    env_data:"环境数据", hw_status:"硬件状态",
    temperature:"环境温度", humidity:"空气湿度", co2:"CO2浓度", soil:"土壤湿度",
    led_status:"灯带状态", led_color:"灯带颜色", pump_status:"水泵状态",
    auto_water_off:"自动抽水：关闭", auto_water_on:"自动抽水：开启",
    auto_water_hint:"开启后将根据土壤湿度自动触发水泵浇水",
    history_title:"数据历史",
    chart_temp:"🌡️ 温度 (°C)", chart_hum:"💧 环境湿度 (%)",
    chart_co2:"🟢 CO2 浓度 (ppm)", chart_soil:"🌱 土壤湿度 (%)",
    settings_title:"系统设置",
    device_info:"设备信息", device_name:"设备名称", device_id:"设备编号",
    conn_status:"连接状态", not_connected:"未连接", connected:"已连接", firmware:"固件版本",
    general_settings:"通用设置", basic_settings:"基础设置",
    notifications:"通知提醒", auto_sync:"自动同步数据",
    dark_mode:"深色模式", language:"语言设置",
    threshold_settings:"提醒设置",
    device_mgmt:"设备管理", wifi_settings:"Wi-Fi 设置",
    check_update:"检查更新", factory_reset:"恢复出厂设置",
    device1:"设备1", device2:"设备2",
    device_ip:"设备 IP", recv_time:"收到时间",
    data_delay:"数据延迟", last_cmd:"最近命令",
    about:"关于", terms:"用户协议", privacy:"隐私政策", contact:"联系我们",
    nav_home:"首页", nav_light:"灯光", nav_pump:"水泵",
    nav_history:"历史", nav_settings:"设置",
    online:"在线", offline:"离线",
    light_title:"灯光调试", light_sub:"灯光效果与定时控制",
    light_effect:"灯光效果选择", light_color:"灯光色彩调节", light_intensity:"灯光强度调节",
    mode_grow:"生长模式", mode_bloom:"开花模式", mode_seedling:"育苗模式", mode_custom:"自定义",
    red_spectrum:"红色光谱", blue_spectrum:"蓝色光谱", warm_ratio:"暖光比例",
    color_preview:"当前色彩预览", intensity:"强度",
    led_ctrl:"灯带控制", led_power:"💡 灯带开关", led_mode:"⚙️ 控制模式",
    led_color_pick:"🎨 选择颜色", led_sync_hint:"设置将在 5 秒内同步至 M5Stack",
    mode_auto:"自动 (随CO2)", mode_manual:"手动 (自定义颜色)",
    light_weak:"弱光", light_mid:"适中", light_strong:"强光",
    bright_low:"低亮度", bright_mid:"中亮度", bright_high:"高亮度",
    timer_settings:"定时设置", auto_light:"自动开关灯",
    light_on_time:"开灯时间", light_off_time:"关灯时间",
    save_settings:"保存设置", saved:"已保存",
    pump_title:"水泵调试", pump_sub:"浇水条件与手动控制",
    pump_trigger:"水泵触发条件", water_duration:"浇水时长调节", manual_ctrl:"手动控制",
    temp_thresh:"温度阈值", air_hum_thresh:"空气湿度阈值", soil_thresh:"土壤湿度阈值",
    auto_watering:"自动浇水", single_duration:"单次浇水时长", min_interval:"最小浇水间隔",
    standby:"待机", water_now:"立即浇水", sec_unit:"秒",
    running:"运行", exec_ok:"执行成功", exec_fail:"执行失败，请重试",
    thresh_sub:"设置各项环境指标的提醒阈值", alert_notify:"提醒通知",
    temp_alert:"温度提醒（°C）", air_alert:"空气湿度提醒（%）", soil_alert:"土壤湿度提醒（%）",
  },
  en: {
    home_title:"Smart Planter", home_sub:"Real-time monitoring & control",
    env_data:"Environment", hw_status:"Hardware",
    temperature:"Temperature", humidity:"Air Humidity", co2:"CO2 Level", soil:"Soil Moisture",
    led_status:"LED Status", led_color:"LED Color", pump_status:"Pump Status",
    auto_water_off:"Auto Water: Off", auto_water_on:"Auto Water: On",
    auto_water_hint:"Pump triggers automatically based on soil moisture",
    history_title:"History",
    chart_temp:"🌡️ Temperature (°C)", chart_hum:"💧 Air Humidity (%)",
    chart_co2:"🟢 CO2 Level (ppm)", chart_soil:"🌱 Soil Moisture (%)",
    settings_title:"Settings",
    device_info:"Device Info", device_name:"Device Name", device_id:"Device ID",
    conn_status:"Connection", not_connected:"Disconnected", connected:"Connected", firmware:"Firmware",
    general_settings:"General", basic_settings:"Basic Settings",
    notifications:"Notifications", auto_sync:"Auto Sync",
    dark_mode:"Dark Mode", language:"Language",
    threshold_settings:"Alert Settings",
    device_mgmt:"Device Mgmt", wifi_settings:"Wi-Fi Settings",
    check_update:"Check Update", factory_reset:"Factory Reset",
    device1:"Device 1", device2:"Device 2",
    device_ip:"IP Address", recv_time:"Received At",
    data_delay:"Data Delay", last_cmd:"Last Command",
    about:"About", terms:"Terms of Use", privacy:"Privacy Policy", contact:"Contact Us",
    nav_home:"Home", nav_light:"Light", nav_pump:"Pump",
    nav_history:"History", nav_settings:"Settings",
    online:"Online", offline:"Offline",
    light_title:"Light Control", light_sub:"Effects & timer settings",
    light_effect:"Light Effect", light_color:"Color Adjustment", light_intensity:"Intensity",
    mode_grow:"Grow", mode_bloom:"Bloom", mode_seedling:"Seedling", mode_custom:"Custom",
    red_spectrum:"Red Spectrum", blue_spectrum:"Blue Spectrum", warm_ratio:"Warm Ratio",
    color_preview:"Color Preview", intensity:"Intensity",
    led_ctrl:"LED Control", led_power:"💡 LED Switch", led_mode:"⚙️ Mode",
    led_color_pick:"🎨 Color", led_sync_hint:"Settings sync to M5Stack within 5s",
    mode_auto:"Auto (by CO2)", mode_manual:"Manual (custom color)",
    light_weak:"Dim", light_mid:"Medium", light_strong:"Bright",
    bright_low:"Low", bright_mid:"Medium", bright_high:"High",
    timer_settings:"Timer", auto_light:"Auto On/Off",
    light_on_time:"On Time", light_off_time:"Off Time",
    save_settings:"Save", saved:"Saved",
    pump_title:"Pump Control", pump_sub:"Watering conditions & manual",
    pump_trigger:"Trigger Conditions", water_duration:"Duration", manual_ctrl:"Manual",
    temp_thresh:"Temp Threshold", air_hum_thresh:"Air Humidity Threshold", soil_thresh:"Soil Threshold",
    auto_watering:"Auto Water", single_duration:"Duration per cycle", min_interval:"Min Interval",
    standby:"Idle", water_now:"Water Now", sec_unit:"s",
    running:"Running", exec_ok:"Success", exec_fail:"Failed, please retry",
    thresh_sub:"Set alert thresholds for each sensor", alert_notify:"Alert Notifications",
    temp_alert:"Temp Alert (°C)", air_alert:"Air Humidity Alert (%)", soil_alert:"Soil Alert (%)",
  }
};
let currentLang = "zh";
function applyLang(lang) {
  currentLang = lang;
  const t = i18n[lang];
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (t[key] !== undefined) el.textContent = t[key];
  });
  // 自动抽水按钮特殊处理（状态文字跟随当前开关状态）
  const btn = document.getElementById("autoWaterHomeBtn");
  if (btn) btn.textContent = autoWaterHomeEnabled ? t.auto_water_on : t.auto_water_off;
}
document.getElementById("langSelect").addEventListener("change", function() {
  applyLang(this.value);
});

/* ── Light page logic ── */
function selectMode(el) {
  document.querySelectorAll(".mode-card").forEach(c => c.classList.remove("selected"));
  el.classList.add("selected");
}

/* ── Auto water home button toggle ── */
let autoWaterHomeEnabled = false;
function toggleAutoWaterHome() {
  autoWaterHomeEnabled = !autoWaterHomeEnabled;
  const btn = document.getElementById("autoWaterHomeBtn");
  const t = i18n[currentLang] || i18n.zh;
  btn.textContent = autoWaterHomeEnabled ? t.auto_water_on : t.auto_water_off;
  // 不改变背景色，始终保持与"立即浇水"一致的绿色渐变
  const sw2 = document.getElementById("autoWaterSwitch2");
  if (sw2) sw2.checked = autoWaterHomeEnabled;
  const sw = document.getElementById("autoWaterSwitch");
  if (sw) sw.checked = autoWaterHomeEnabled;
}
function updateColor(fromSliders) {
  const r = +document.getElementById("redSlider").value;
  const b = +document.getElementById("blueSlider").value;
  const w = +document.getElementById("warmSlider").value;
  document.getElementById("redVal").textContent  = r + "%";
  document.getElementById("blueVal").textContent = b + "%";
  document.getElementById("warmVal").textContent = w + "%";

  // 将 r/b/w 百分比映射为 RGB 颜色
  const rr = Math.round((r / 100) * 255);
  const gg = Math.round((w / 100) * 180);  // 暖光影响绿通道
  const bb = Math.round((b / 100) * 255);
  const hex = "#" + [rr,gg,bb].map(v => v.toString(16).padStart(2,"0")).join("");

  // 更新预览色块
  document.getElementById("colorPreview").style.background = "rgb("+rr+","+gg+","+bb+")";

  // 同步首页灯带颜色点
  const dot = document.getElementById("ledColorDot");
  if (dot) dot.style.background = "rgb("+rr+","+gg+","+bb+")";

  // 如果是滑块触发，同步颜色选择器
  if (fromSliders) {
    const colorEl = document.getElementById("uiLedColor");
    if (colorEl) colorEl.value = hex;
    sendLedCommand();
  }
}

function colorPickerToSliders() {
  // 颜色选择器改变时，反向更新三个滑块
  const colorEl = document.getElementById("uiLedColor");
  if (!colorEl) return;
  const hex = colorEl.value;
  const rr = parseInt(hex.slice(1,3), 16);
  const gg = parseInt(hex.slice(3,5), 16);
  const bb = parseInt(hex.slice(5,7), 16);
  // 反向映射
  const r = Math.round((rr / 255) * 100);
  const w = Math.round((gg / 180) * 100);
  const b = Math.round((bb / 255) * 100);
  document.getElementById("redSlider").value  = Math.min(100, r);
  document.getElementById("blueSlider").value = Math.min(100, b);
  document.getElementById("warmSlider").value = Math.min(100, w);
  updateColor(false);  // 更新预览但不再触发颜色选择器同步（避免循环）
  sendLedCommand();
}
function setBright(v) {
  document.getElementById("brightSlider").value = v;
  document.getElementById("brightVal").textContent = v + "%";
  updateQuickBtns();
}
function updateQuickBtns() {
  const v = +document.getElementById("brightSlider").value;
  const targets = [20, 50, 80];
  document.querySelectorAll(".quick-btn").forEach((btn, i) => {
    btn.classList.toggle("qactive", Math.abs(v - targets[i]) < 16);
  });
}
function saveLightSettings() {
  const btn = event.target;
  const t = i18n[currentLang] || i18n.zh;
  btn.textContent = t.saved; btn.style.opacity = ".8";
  setTimeout(() => { btn.textContent = t.save_settings; btn.style.opacity = "1"; }, 1500);
}
updateColor(false);

/* ── Pump page logic ── */
function manualWater(source) {
  const btns   = [document.getElementById("manualWaterBtn"),    document.getElementById("homeManualWaterBtn")];
  const hints  = [document.getElementById("manualWaterHint"),   document.getElementById("homeManualWaterHint")];
  const badges = [document.getElementById("pumpStatusBadge"),   document.getElementById("homePumpStatusBadge")];
  const t = i18n[currentLang] || i18n.zh;

  const pumpSec = +(document.getElementById("pumpDurWheel")?.dataset.val || 5);
  const homeSec = +(document.getElementById("homeDurWheel")?.dataset.val || 5);
  const dur = (source === "home" ? homeSec : pumpSec) * 1000;

  btns.forEach(b   => { if(b) b.disabled = true; });
  badges.forEach(b => { if(b) { b.textContent = t.running; b.className = "pump-st-badge running"; } });
  hints.forEach(h  => { if(h) h.style.display = "none"; });

  fetch("/api/pump/trigger", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({duration_ms: dur}) })
    .then(r => r.json()).then(data => {
      if (data.ok) {
        hints.forEach(h => { if(h) { h.textContent = t.exec_ok; h.style.display = "block"; } });
      }
    }).catch(() => {
      hints.forEach(h => { if(h) { h.textContent = t.exec_fail; h.style.display = "block"; } });
    })
    .finally(() => {
      setTimeout(() => {
        btns.forEach(b   => { if(b) b.disabled = false; });
        badges.forEach(b => { if(b) { b.textContent = t.standby; b.className = "pump-st-badge idle"; } });
        hints.forEach(h  => { if(h) h.style.display = "none"; });
      }, dur + 500);
    });
}

/* ── Duration wheel (1–10 秒) ── */
function wheelDur(e, el) {
  e.preventDefault();
  let v = parseInt(el.dataset.val) || 5;
  v += e.deltaY > 0 ? 1 : -1;
  if (v < 1) v = 1;
  if (v > 10) v = 10;
  el.dataset.val = v;
  el.textContent = v;
}
function savePumpSettings() {
  const btn = event.target;
  const t = i18n[currentLang] || i18n.zh;
  btn.textContent = t.saved; btn.style.opacity = ".8";
  setTimeout(() => { btn.textContent = t.save_settings; btn.style.opacity = "1"; }, 1500);
}
function saveThreshSettings() {
  const btn = event.target;
  const t = i18n[currentLang] || i18n.zh;
  btn.textContent = t.saved; btn.style.opacity = ".8";
  setTimeout(() => { btn.textContent = t.save_settings; btn.style.opacity = "1"; }, 1500);
}

const MAX_POINTS = 10;

// 生成初始占位时间刻度，让图表在无数据时也显示坐标轴
function genInitLabels() {
  const arr = [];
  const now = new Date();
  for (let i = MAX_POINTS - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 60000);
    arr.push(t.getHours().toString().padStart(2,"0")+":"+t.getMinutes().toString().padStart(2,"0"));
  }
  return arr;
}
const history = {
  labels: genInitLabels(),
  temperature: new Array(MAX_POINTS).fill(null),
  humidity:    new Array(MAX_POINTS).fill(null),
  co2:         new Array(MAX_POINTS).fill(null),
  soil:        new Array(MAX_POINTS).fill(null)
};

function pushHistory(env, pump) {
  const now = new Date();
  history.labels.push(now.getHours().toString().padStart(2,"0")+":"+now.getMinutes().toString().padStart(2,"0")+":"+now.getSeconds().toString().padStart(2,"0"));
  history.temperature.push(env.temperature ?? null);
  history.humidity.push(env.humidity ?? null);
  history.co2.push(env.co2 ?? null);
  history.soil.push(pump.moisture_percent ?? null);
  if (history.labels.length > MAX_POINTS) { history.labels.shift(); history.temperature.shift(); history.humidity.shift(); history.co2.shift(); history.soil.shift(); }
  if (activePage === "pageHistory") renderCharts();
}

const chartInstances = {};
function makeChartCfg(label, color, data, labels) {
  return {
    type: "line", data: { labels, datasets: [{ label, data, borderColor: color, backgroundColor: color.replace("1)", ".08)"), borderWidth: 2, pointRadius: 3, pointBackgroundColor: color, tension: 0.35, fill: true, spanGaps: true }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks:{font:{size:10},color:"#bbb",maxTicksLimit:6}, grid:{color:"rgba(0,0,0,.04)"} },
        y: { ticks:{font:{size:10},color:"#bbb",maxTicksLimit:5}, grid:{color:"rgba(0,0,0,.04)"}, beginAtZero: false,
             suggestedMin: 0, suggestedMax: 100 }
      }
    }
  };
}
function renderCharts() {
  const defs = [
    { id: "chartTemp",     label: "温度 °C",   color: "rgba(255,138,101,1)",  key: "temperature" },
    { id: "chartHumidity", label: "湿度 %",    color: "rgba(79,195,247,1)",   key: "humidity"    },
    { id: "chartCo2",      label: "CO2 ppm",  color: "rgba(156, 39, 176,1)", key: "co2"         },
    { id: "chartSoil",     label: "土壤湿度 %", color: "rgba(129,199,132,1)", key: "soil"        },
  ];
  // 若历史页当前不可见，临时设为可见以便 canvas 获得正确尺寸
  const histPage = document.getElementById("pageHistory");
  const wasHidden = !histPage.classList.contains("active");
  if (wasHidden) {
    histPage.style.cssText = "display:flex!important;visibility:hidden;position:absolute;pointer-events:none;";
  }
  defs.forEach(({id,label,color,key}) => {
    const canvas = document.getElementById(id); if(!canvas) return;
    const data = history[key], labels = history.labels;
    if (chartInstances[id]) {
      chartInstances[id].data.labels = labels;
      chartInstances[id].data.datasets[0].data = data;
      chartInstances[id].update();
    } else {
      chartInstances[id] = new Chart(canvas, makeChartCfg(label, color, data, labels));
    }
  });
  if (wasHidden) {
    histPage.style.cssText = "";
  }
}

let lastHistoryTs = 0;
function fmt(v, suf) { return (v===null||v===undefined) ? "--" : v+(suf||""); }
function setBadge(el, isOnline) { const t=i18n[currentLang]||i18n.zh; el.textContent=isOnline?t.online:t.offline; el.className="section-status "+(isOnline?"online":"offline"); }

// 发送 LED 控制指令到后端（元素不存在时静默跳过）
async function sendLedCommand() {
  const powerEl = document.getElementById("uiLedPower");
  const modeEl  = document.getElementById("uiLedMode");
  const colorEl = document.getElementById("uiLedColor");
  if (!powerEl || !modeEl || !colorEl) return;
  const payload = { power: powerEl.checked, mode: modeEl.value, color: colorEl.value };
  try {
    await fetch("/api/led/command", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
  } catch(e) { console.error("LED update failed", e); }
}

// LED 控件事件绑定
const _ledPower = document.getElementById("uiLedPower");
const _ledMode  = document.getElementById("uiLedMode");
const _ledColor = document.getElementById("uiLedColor");
if (_ledPower) _ledPower.addEventListener("change", sendLedCommand);
if (_ledMode)  _ledMode.addEventListener("change", (e) => {
  const colorRow = document.getElementById("colorRow");
  if (colorRow) {
    colorRow.style.opacity = e.target.value === "auto" ? "0.3" : "1";
    colorRow.style.pointerEvents = e.target.value === "auto" ? "none" : "auto";
  }
  sendLedCommand();
});
// 颜色选择器改变 → 反向更新滑块 → 发送后端
if (_ledColor) _ledColor.addEventListener("input", colorPickerToSliders);

/* ── Time wheel scroll ── */
function wheelTime(e, el, max) {
  e.preventDefault();
  let v = parseInt(el.dataset.val);
  v = (v + (e.deltaY > 0 ? 1 : -1) + max) % max;
  el.dataset.val = v;
  el.textContent = String(v).padStart(2, '0');
}

async function fetchData() {
  try {
    const res = await fetch("/api/data", {cache:"no-store"}); const data = await res.json();
    const env = data.env || {}, pump = data.pump || {}, cmd = data.pump_command || {};
    const t = i18n[currentLang] || i18n.zh;

    document.getElementById("temperature").textContent = fmt(env.temperature, " °C");
    document.getElementById("humidity").textContent    = fmt(env.humidity, " %");
    document.getElementById("co2").textContent         = fmt(env.co2, " ppm");
    document.getElementById("lampText").textContent    = env.lamp_status || "--";
    setBadge(document.getElementById("envOnlineBadge"), Boolean(env.is_online));

    document.getElementById("soilMoisture").textContent = fmt(pump.moisture_percent, " %");
    document.getElementById("pumpStatus").textContent   = pump.pump_status_text || "--";

    const lastCmdEl = document.getElementById("lastCommand");
    if (lastCmdEl) lastCmdEl.textContent = cmd.command_id ? "#"+cmd.command_id+" / "+(cmd.duration_ms||1000)+" ms" : "--";

    // 设备信息 - 连接状态（跟随 i18n）
    const connEl = document.getElementById("settingConnStatus");
    if (connEl) {
      const online = env.is_online || pump.is_online;
      connEl.textContent = online ? (t.connected || "已连接") : (t.not_connected || "未连接");
      connEl.style.color = online ? "#2d6a4f" : "#dc2626";
    }

    // 设备 IP / 时间等设置页字段
    const fields = {
      settingEnvDeviceId: env.device_id, settingEnvDeviceIp: env.device_ip,
      envServerTime: env.server_received_at ? env.server_received_at.slice(11,19) : "--",
      envAge: env.age_seconds != null ? env.age_seconds.toFixed(1)+" s" : "--",
      settingPumpDeviceId: pump.device_id, settingPumpDeviceIp: pump.device_ip,
      pumpServerTime: pump.server_received_at ? pump.server_received_at.slice(11,19) : "--",
    };
    Object.entries(fields).forEach(([id, val]) => {
      const el = document.getElementById(id); if (el && val != null) el.textContent = val;
    });

    const now = Date.now();
    if (now - lastHistoryTs >= 30000) { lastHistoryTs=now; pushHistory(env, pump); }
  } catch (e) {}
}

fetchData(); setInterval(fetchData, 1000);
</script>
</body></html>
"""

state_lock = Lock()
device_state = {
    "env": { "device_id": "waiting", "co2": None, "temperature": None, "humidity": None, "lamp_status": None, "server_received_at": None },
    "pump": { "device_id": "waiting", "moisture_capacitive_value": None, "moisture_percent": None, "adc_raw": None, "pump_status_text": None, "server_received_at": None },
    # 【恢复】水泵的中央命令存储
    "pump_command": { "command_id": 0, "duration_ms": 1000, "issued_at": None },
    "led_command": { "power": True, "mode": "auto", "color": "#00ff00" }
}

def with_online_fields(snapshot):
    age_seconds = None; is_online = False
    if snapshot.get("server_received_at"):
        received = datetime.fromisoformat(snapshot["server_received_at"])
        age_seconds = (datetime.now(timezone.utc) - received).total_seconds()
        is_online = age_seconds <= 5
    result = dict(snapshot); result["age_seconds"] = age_seconds; result["is_online"] = is_online
    return result

def json_response(handler, data, status=200):
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
            
        if parsed.path == "/api/data":
            with state_lock:
                env = with_online_fields(device_state["env"])
                pump = with_online_fields(device_state["pump"])
                cmd = dict(device_state["pump_command"]) # 【恢复】在面板显示最新的水泵命令
            json_response(self, {"env": env, "pump": pump, "pump_command": cmd})
            return
            
        # 【恢复】水泵节点通过 GET 请求来拉取命令的接口
        if parsed.path == "/api/pump/command":
            with state_lock:
                cmd = dict(device_state["pump_command"])
            json_response(self, {"ok": True, **cmd})
            return
            
        json_response(self, {"ok": False}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try: payload = json.loads(raw.decode("utf-8"))
        except: payload = {}

        # 【恢复】处理网页端发来的水泵触发命令
        if parsed.path == "/api/pump/trigger":
            duration_ms = int(payload.get("duration_ms", 1000))
            if duration_ms < 100: duration_ms = 100
            if duration_ms > 5000: duration_ms = 5000
            with state_lock:
                device_state["pump_command"]["command_id"] += 1
                device_state["pump_command"]["duration_ms"] = duration_ms
                device_state["pump_command"]["issued_at"] = datetime.now(timezone.utc).isoformat()
                snapshot = dict(device_state["pump_command"])
            json_response(self, {"ok": True, **snapshot})
            return

        if parsed.path == "/api/led/command":
            with state_lock:
                if "power" in payload: device_state["led_command"]["power"] = payload["power"]
                if "mode" in payload: device_state["led_command"]["mode"] = payload["mode"]
                if "color" in payload: device_state["led_command"]["color"] = payload["color"]
            json_response(self, {"ok": True, "state": device_state["led_command"]})
            return

        if parsed.path == "/api/sensor":
            kind = payload.get("device_kind", "env" if "co2" in payload else "pump")
            now_iso = datetime.now(timezone.utc).isoformat()
            
            with state_lock:
                target = device_state[kind]
                target.update(payload)
                target["server_received_at"] = now_iso
                current_led_cmd = dict(device_state["led_command"])

            json_response(self, {"ok": True, "led_command": current_led_cmd})
            return

    def log_message(self, format, *args): return

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    print(f"Server running at http://127.0.0.1:{PORT}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass