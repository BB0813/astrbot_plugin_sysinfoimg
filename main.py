from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import psutil
import platform
import base64
import os
import datetime
import json
import asyncio
from typing import Dict, Any, Tuple, Optional

# ============================================================================
# Templates
# ============================================================================

TMPL_DARK_GLASS = '''
<html>
<head>
  <meta charset="utf-8" />
  <style>
    :root {
      --gap-xs: 4px;
      --gap-sm: 8px;
      --gap-md: 12px;
      --gap-lg: 16px;
      --gap-xl: 24px;
      --pad-card: 20px;
      --pad-root: 32px;
      --radius-card: 16px;
      --radius-bar: 4px;
      --color-text-primary: rgba(255, 255, 255, 0.95);
      --color-text-secondary: rgba(255, 255, 255, 0.75);
      --color-text-tertiary: rgba(255, 255, 255, 0.50);
      --color-bg-card: rgba(0, 0, 0, 0.45);
      --color-bg-bar: rgba(255, 255, 255, 0.15);
      --color-border: rgba(255, 255, 255, 0.1);
      --shadow-card: 0 8px 32px rgba(0, 0, 0, 0.2);
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    }
    * { box-sizing: border-box; }
    body { margin:0; width:100%; height:100%; font-family: var(--font-body); }
    .root { position: relative; width: 100%; height: 100%; }
    .bg { position:absolute; inset:0; background-size: {{ background_fit_css }}; background-position:center; filter: brightness(0.7) blur(0px); }
    .overlay { position:absolute; inset:0; background: linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.7) 100%); }
    .content { position:relative; z-index:2; padding: var(--pad-root) var(--pad-root) 80px var(--pad-root); color: var(--color-text-primary); }
    
    .header { margin-bottom: 24px; }
    .title { font-size: 36px; font-weight: 700; margin-bottom: 4px; letter-spacing: -0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
    .sub { font-size: 14px; color: var(--color-text-secondary); font-weight: 400; letter-spacing: 0.5px; }
    
    .cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--gap-lg); margin-bottom: var(--gap-xl); }
    .columns { display:grid; grid-template-columns: 1fr 1fr; gap: var(--gap-xl); }
    .col { display: flex; flex-direction: column; }
    .col .card { flex: 1; }
    
    .card { 
      background: var(--color-bg-card); 
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card); 
      padding: var(--pad-card); 
      box-shadow: var(--shadow-card);
      backdrop-filter: blur(12px);
      display: flex; flex-direction: column;
    }
    
    .metric { display:flex; align-items:center; justify-content:space-between; margin-bottom: var(--gap-sm); line-height:1.4; font-size: 14px; }
    .metric span:first-child { color: var(--color-text-secondary); font-weight: 500; }
    .val { font-family: var(--font-mono); font-weight: 600; color: var(--color-text-primary); }
    
    .bar { width:100%; height:8px; background: var(--color-bg-bar); border-radius: var(--radius-bar); overflow:hidden; margin-bottom: 2px; }
    .bar > div { height:100%; background: {{ accent_color }}; border-radius: var(--radius-bar); transition: width 0.3s ease; }
    
    .disk { margin-top: 0; }
    .disk-item { margin-bottom: var(--gap-md); font-size: 13px; }
    .disk-item:last-child { margin-bottom: 0; }
    .disk-header { display:flex; justify-content:space-between; margin-bottom: 4px; }
    .mount { font-family: var(--font-mono); font-weight:600; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%; display: inline-block; }
    .disk-val { font-family: var(--font-mono); font-size: 12px; color: var(--color-text-secondary); }

    .footer { position: absolute; bottom: 24px; color: var(--color-text-tertiary); font-size: 12px; z-index:3; width: 100%; padding: 0 var(--pad-root); box-sizing: border-box; pointer-events: none; font-weight: 500; letter-spacing: 0.5px; }
    
    .proc-table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
    .proc-table td { padding: 8px 0; vertical-align: top; border-bottom: 1px solid var(--color-border); }
    .proc-table tr:last-child td { border-bottom: none; }
    .proc-table td.p-name { padding-right: 12px; width: 65%; }
    .proc-table td.p-val { text-align: right; white-space: nowrap; width: 35%; }
    .proc-main { font-weight: 600; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .proc-sub { font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; font-family: var(--font-mono); }
    .proc-val-main { font-family: var(--font-mono); font-weight: 600; color: var(--color-text-primary); }
    .proc-val-sub { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; }
    
    .card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); }
    .card-title::before { content:''; display:block; width:4px; height:16px; background: {{ accent_color }}; border-radius: 2px; }
  </style>
  </head>
<body>
  <div class="root">
    {% if bg_image %}
      <div class="bg" style="background-image:url('{{ bg_image }}')"></div>
    {% else %}
      <div class="bg" style="background: linear-gradient(135deg, #1a1c2c 0%, #4a192c 100%)"></div>
    {% endif %}
    <div class="overlay"></div>
    <div class="content">
      <div class="header">
        <div class="title">{{ title }}</div>
        <div class="sub">{{ subline }}</div>
      </div>
      
      <div class="cards">
        {% if cpu_percent is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_cpu }}</span><span class="val">{{ cpu_percent }}%</span></div>
          <div class="bar"><div style="width: {{ cpu_percent }}%; background: {{ bar_color_cpu }};"></div></div>
        </div>
        {% endif %}
        {% if mem is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_memory }}</span><span class="val">{{ mem.percent }}%</span></div>
          <div class="bar"><div style="width: {{ mem.percent }}%; background: {{ bar_color_mem }};"></div></div>
          <div style="text-align:right; font-size:11px; color:var(--color-text-tertiary); margin-top:4px; font-family:var(--font-mono)">{{ mem.used_h }} / {{ mem.total_h }}</div>
        </div>
        {% endif %}
        {% if swap is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_swap }}</span><span class="val">{{ swap.percent }}%</span></div>
          <div class="bar"><div style="width: {{ swap.percent }}%; background: {{ bar_color_swap }};"></div></div>
          <div style="text-align:right; font-size:11px; color:var(--color-text-tertiary); margin-top:4px; font-family:var(--font-mono)">{{ swap.used_h }} / {{ swap.total_h }}</div>
        </div>
        {% endif %}
        {% if net_sent is not none and net_recv is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_network }}</span><span class="val" style="font-size:12px">{{ (net_sent/1024/1024)|round(2) }} MB/s ↑ · {{ (net_recv/1024/1024)|round(2) }} MB/s ↓</span></div>
          <div class="bar"><div style="width: {{ net_bar_percent if net_bar_percent is not none else 0 }}%; background: {{ bar_color_net }};"></div></div>
        </div>
        {% endif %}
      </div>

      <div class="columns">
        <div class="col">
          <div class="card disk">
            <div class="card-title">{{ label_disk }}</div>
            {% if disk_total %}
            <div class="disk-item">
              <div class="disk-header">
                <span class="mount">{{ label_total }}</span>
                <span class="disk-val">{{ disk_total.percent }}% ({{ disk_total.used_h }}/{{ disk_total.total_h }})</span>
              </div>
              <div class="bar"><div style="width: {{ disk_total.percent }}%; background: {{ bar_color_disk }};"></div></div>
            </div>
            {% endif %}
            {% if disk_info and disk_info|length > 0 %}
              {% for d in disk_info %}
                <div class="disk-item">
                  <div class="disk-header">
                    <span class="mount" title="{{ d.mount }}">{{ d.mount }}</span>
                    <span class="disk-val">{{ d.percent }}% ({{ d.used_h }}/{{ d.total_h }})</span>
                  </div>
                  <div class="bar"><div style="width: {{ d.percent }}%; background: {{ bar_color_disk }};"></div></div>
                </div>
              {% endfor %}
            {% else %}
              <div class="disk-item" style="text-align:center; color:var(--color-text-tertiary); padding:20px 0;">
                {{ label_no_part }}
              </div>
            {% endif %}
          </div>
        </div>
        
        <div class="col">
          {% if bottom_right_panel == 'net_ifaces' and net_per and net_per|length > 0 %}
          <div class="card">
            <div class="card-title">{{ label_network }}</div>
            <table class="proc-table">
            {% for n in net_per %}
              <tr>
                <td class="p-name">
                  <div class="proc-main">{{ n.name }}</div>
                </td>
                <td class="p-val">
                  <div class="proc-val-main">{{ (n.up/1024/1024)|round(2) }} MB/s ↑</div>
                  <div class="proc-val-sub">{{ (n.down/1024/1024)|round(2) }} MB/s ↓</div>
                </td>
              </tr>
            {% endfor %}
            </table>
          </div>
          {% elif bottom_right_panel == 'processes' and top_procs and top_procs|length > 0 %}
          <div class="card">
            <div class="card-title">{{ label_top }}</div>
            <table class="proc-table">
            {% for p in top_procs %}
              <tr>
                  <td class="p-name">
                      <div class="proc-main">{{ p.name }}</div>
                      {% if process_show_user %}<div class="proc-sub">PID: {{ p.pid }} · {{ p.username }}</div>{% endif %}
                  </td>
                  <td class="p-val">
                      <div class="proc-val-main">{{ p.mem_h }}</div>
                      <div class="proc-val-sub">CPU: {{ p.cpu }}%</div>
                  </td>
              </tr>
            {% endfor %}
            </table>
          </div>
          {% elif bottom_right_panel == 'summary' %}
          <div class="card">
            <div class="card-title">System Summary</div>
            <div class="metric"><span>CPU Usage</span><span class="val">{{ cpu_percent }}%</span></div>
            {% if mem %}<div class="metric"><span>Memory Usage</span><span class="val">{{ mem.percent }}%</span></div>{% endif %}
            {% if swap %}<div class="metric"><span>Swap Usage</span><span class="val">{{ swap.percent }}%</span></div>{% endif %}
          </div>
          {% endif %}
        </div>
      </div>
      <div class="footer" style="{% if footer_position == 'left_bottom' %}left:0; text-align:left;{% else %}right:0; text-align:right;{% endif %}">{{ label_powered }}</div>
    </div>
  </div>
</body>
</html>
'''

TMPL_LIGHT_CARD = '''
<html>
<head>
  <meta charset="utf-8" />
  <style>
    :root {
      --gap-xs: 4px;
      --gap-sm: 8px;
      --gap-md: 12px;
      --gap-lg: 16px;
      --gap-xl: 24px;
      --pad-card: 20px;
      --pad-root: 32px;
      --radius-card: 16px;
      --radius-bar: 4px;
      --color-text-primary: #111827;
      --color-text-secondary: #4b5563;
      --color-text-tertiary: #9ca3af;
      --color-bg-card: #ffffff;
      --color-bg-bar: #e5e7eb;
      --color-border: rgba(0, 0, 0, 0.05);
      --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    }
    * { box-sizing: border-box; }
    body { margin:0; width:100%; height:100%; font-family: var(--font-body); background: #f3f4f6; }
    .root { position: relative; width: 100%; height: 100%; }
    .bg { position:absolute; inset:0; background-size: {{ background_fit_css }}; background-position:center; opacity:.15; filter: saturate(0); }
    .content { position:relative; z-index:2; padding: var(--pad-root) var(--pad-root) 80px var(--pad-root); color: var(--color-text-primary); }
    
    .header { margin-bottom: 24px; }
    .title { font-size: 36px; font-weight: 800; margin-bottom: 4px; letter-spacing: -0.8px; color: #111827; }
    .sub { font-size: 14px; color: var(--color-text-secondary); font-weight: 500; letter-spacing: 0.2px; }
    
    .cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--gap-lg); margin-bottom: var(--gap-xl); }
    .columns { display:grid; grid-template-columns: 1fr 1fr; gap: var(--gap-xl); }
    .col { display: flex; flex-direction: column; }
    .col .card { flex: 1; }
    
    .card { 
      background: var(--color-bg-card); 
      border-radius: var(--radius-card); 
      padding: var(--pad-card); 
      box-shadow: var(--shadow-card);
      border: 1px solid var(--color-border);
      display: flex; flex-direction: column;
    }
    
    .metric { display:flex; align-items:center; justify-content:space-between; margin-bottom: var(--gap-sm); line-height:1.4; font-size: 14px; }
    .metric span:first-child { color: var(--color-text-secondary); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
    .val { font-family: var(--font-mono); font-weight: 700; color: var(--color-text-primary); }
    
    .bar { width:100%; height:8px; background: var(--color-bg-bar); border-radius: var(--radius-bar); overflow:hidden; margin-bottom: 2px; }
    .bar > div { height:100%; background: {{ accent_color }}; border-radius: var(--radius-bar); transition: width 0.3s ease; }
    
    .disk { margin-top: 0; }
    .disk-item { margin-bottom: var(--gap-md); font-size: 13px; }
    .disk-item:last-child { margin-bottom: 0; }
    .disk-header { display:flex; justify-content:space-between; margin-bottom: 4px; }
    .mount { font-family: var(--font-mono); font-weight:700; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%; display: inline-block; }
    .disk-val { font-family: var(--font-mono); font-size: 12px; color: var(--color-text-secondary); font-weight: 500; }

    .footer { position: absolute; bottom: 24px; color: var(--color-text-tertiary); font-size: 12px; z-index:3; width: 100%; padding: 0 var(--pad-root); box-sizing: border-box; pointer-events: none; font-weight: 600; letter-spacing: 0.5px; }
    
    .proc-table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
    .proc-table td { padding: 8px 0; vertical-align: top; border-bottom: 1px solid #f3f4f6; }
    .proc-table tr:last-child td { border-bottom: none; }
    .proc-table td.p-name { padding-right: 12px; width: 65%; }
    .proc-table td.p-val { text-align: right; white-space: nowrap; width: 35%; }
    .proc-main { font-weight: 700; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .proc-sub { font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; font-family: var(--font-mono); font-weight: 500; }
    .proc-val-main { font-family: var(--font-mono); font-weight: 700; color: var(--color-text-primary); }
    .proc-val-sub { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; font-weight: 500; }
    
    .card-title { font-size: 18px; font-weight: 800; margin-bottom: 20px; color: #111827; letter-spacing: -0.5px; }
  </style>
  </head>
<body>
  <div class="root">
    {% if bg_image %}
      <div class="bg" style="background-image:url('{{ bg_image }}')"></div>
    {% endif %}
    <div class="content">
      <div class="header">
        <div class="title">{{ title }}</div>
        <div class="sub">{{ subline }}</div>
      </div>
      
      <div class="cards">
        {% if cpu_percent is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_cpu }}</span><span class="val">{{ cpu_percent }}%</span></div>
          <div class="bar"><div style="width: {{ cpu_percent }}%; background: {{ bar_color_cpu }};"></div></div>
        </div>
        {% endif %}
        {% if mem is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_memory }}</span><span class="val">{{ mem.percent }}%</span></div>
          <div class="bar"><div style="width: {{ mem.percent }}%; background: {{ bar_color_mem }};"></div></div>
          <div style="text-align:right; font-size:11px; color:var(--color-text-tertiary); margin-top:4px; font-family:var(--font-mono)">{{ mem.used_h }} / {{ mem.total_h }}</div>
        </div>
        {% endif %}
        {% if swap is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_swap }}</span><span class="val">{{ swap.percent }}%</span></div>
          <div class="bar"><div style="width: {{ swap.percent }}%; background: {{ bar_color_swap }};"></div></div>
          <div style="text-align:right; font-size:11px; color:var(--color-text-tertiary); margin-top:4px; font-family:var(--font-mono)">{{ swap.used_h }} / {{ swap.total_h }}</div>
        </div>
        {% endif %}
        {% if net_sent is not none and net_recv is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_network }}</span><span class="val" style="font-size:12px">{{ (net_sent/1024/1024)|round(2) }} MB/s ↑ · {{ (net_recv/1024/1024)|round(2) }} MB/s ↓</span></div>
          <div class="bar"><div style="width: {{ net_bar_percent if net_bar_percent is not none else 0 }}%; background: {{ bar_color_net }};"></div></div>
        </div>
        {% endif %}
      </div>

      <div class="columns">
        <div class="col">
          <div class="card disk">
            <div class="card-title">{{ label_disk }}</div>
            {% if disk_total %}
            <div class="disk-item">
              <div class="disk-header">
                <span class="mount">{{ label_total }}</span>
                <span class="disk-val">{{ disk_total.percent }}% ({{ disk_total.used_h }}/{{ disk_total.total_h }})</span>
              </div>
              <div class="bar"><div style="width: {{ disk_total.percent }}%; background: {{ bar_color_disk }};"></div></div>
            </div>
            {% endif %}
            {% if disk_info and disk_info|length > 0 %}
              {% for d in disk_info %}
                <div class="disk-item">
                  <div class="disk-header">
                    <span class="mount" title="{{ d.mount }}">{{ d.mount }}</span>
                    <span class="disk-val">{{ d.percent }}% ({{ d.used_h }}/{{ d.total_h }})</span>
                  </div>
                  <div class="bar"><div style="width: {{ d.percent }}%; background: {{ bar_color_disk }};"></div></div>
                </div>
              {% endfor %}
            {% else %}
              <div class="disk-item">
                <div class="metric"><span class="mount">{{ label_no_part }}</span><span></span></div>
              </div>
            {% endif %}
          </div>
        </div>
        <div class="col">
          {% if bottom_right_panel == 'net_ifaces' and net_per and net_per|length > 0 %}
          <div class="card">
            <div class="card-title">{{ label_network }}</div>
            <table class="proc-table">
            {% for n in net_per %}
              <tr>
                <td class="p-name">
                  <div class="proc-main">{{ n.name }}</div>
                </td>
                <td class="p-val">
                  <div class="proc-val-main">{{ (n.up/1024/1024)|round(2) }} MB/s ↑</div>
                  <div class="proc-val-sub">{{ (n.down/1024/1024)|round(2) }} MB/s ↓</div>
                </td>
              </tr>
            {% endfor %}
            </table>
          </div>
          {% elif bottom_right_panel == 'processes' and top_procs and top_procs|length > 0 %}
          <div class="card">
            <div class="card-title">{{ label_top }}</div>
            <table class="proc-table">
            {% for p in top_procs %}
              <tr>
                  <td class="p-name">
                      <div class="proc-main">{{ p.name }}</div>
                      {% if process_show_user %}<div class="proc-sub">PID: {{ p.pid }} · {{ p.username }}</div>{% endif %}
                  </td>
                  <td class="p-val">
                      <div class="proc-val-main">{{ p.mem_h }}</div>
                      <div class="proc-val-sub">CPU: {{ p.cpu }}%</div>
                  </td>
              </tr>
            {% endfor %}
            </table>
          </div>
          {% elif bottom_right_panel == 'summary' %}
          <div class="card">
            <div class="card-title">System Summary</div>
            <div class="metric"><span>CPU Usage</span><span class="val">{{ cpu_percent }}%</span></div>
            {% if mem %}<div class="metric"><span>Memory Usage</span><span class="val">{{ mem.percent }}%</span></div>{% endif %}
            {% if swap %}<div class="metric"><span>Swap Usage</span><span class="val">{{ swap.percent }}%</span></div>{% endif %}
          </div>
          {% endif %}
        </div>
      </div>
      <div class="footer" style="{% if footer_position == 'left_bottom' %}left:24px{% else %}right:24px{% endif %}">{{ label_powered }}</div>
    </div>
  </div>
</body>
</html>
'''

TMPL_NEON = '''
<html>
<head>
  <meta charset="utf-8" />
  <style>
    :root {
      --gap-xs: 4px;
      --gap-sm: 8px;
      --gap-md: 12px;
      --gap-lg: 16px;
      --gap-xl: 24px;
      --pad-card: 20px;
      --pad-root: 32px;
      --radius-card: 16px;
      --radius-bar: 4px;
      --color-text-primary: #e2e8f0;
      --color-text-secondary: #94a3b8;
      --color-text-tertiary: #64748b;
      --color-bg-card: rgba(15, 23, 42, 0.85);
      --color-bg-bar: rgba(51, 65, 85, 0.5);
      --color-border: rgba(59, 130, 246, 0.3);
      --shadow-card: 0 0 0 1px rgba(59, 130, 246, 0.1), 0 0 20px rgba(59, 130, 246, 0.15);
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
      --neon-glow: 0 0 10px {{ accent_color }};
    }
    * { box-sizing: border-box; }
    body { margin:0; width:100%; height:100%; font-family: var(--font-body); background: #0b1020; }
    .root { position: relative; width: 100%; height: 100%; background: radial-gradient(circle at 50% -20%, rgba(59,130,246,0.15), transparent 70%); }
    .bg { position:absolute; inset:0; background-size: {{ background_fit_css }}; background-position:center; opacity:.15; filter: contrast(1.2) brightness(0.8); }
    .content { position:relative; z-index:2; padding: var(--pad-root) var(--pad-root) 80px var(--pad-root); color: var(--color-text-primary); }
    
    .header { margin-bottom: 24px; }
    .title { font-size: 36px; font-weight: 800; margin-bottom: 4px; letter-spacing: -0.5px; text-shadow: 0 0 20px rgba(59,130,246,0.6); color: #fff; }
    .sub { font-size: 14px; color: var(--color-text-secondary); font-weight: 500; letter-spacing: 1px; text-transform: uppercase; }
    
    .cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--gap-lg); margin-bottom: var(--gap-xl); }
    .columns { display:grid; grid-template-columns: 1fr 1fr; gap: var(--gap-xl); }
    .col { display: flex; flex-direction: column; }
    .col .card { flex: 1; }
    
    .card { 
      background: var(--color-bg-card); 
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card); 
      padding: var(--pad-card); 
      box-shadow: var(--shadow-card);
      backdrop-filter: blur(8px);
      display: flex; flex-direction: column;
    }
    
    .metric { display:flex; align-items:center; justify-content:space-between; margin-bottom: var(--gap-sm); line-height:1.4; font-size: 14px; }
    .metric span:first-child { color: var(--color-text-secondary); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
    .val { font-family: var(--font-mono); font-weight: 700; color: #fff; text-shadow: 0 0 10px rgba(255,255,255,0.3); }
    
    .bar { width:100%; height:8px; background: var(--color-bg-bar); border-radius: var(--radius-bar); overflow:hidden; margin-bottom: 2px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.3); }
    .bar > div { height:100%; background: {{ accent_color }}; border-radius: var(--radius-bar); box-shadow: var(--neon-glow); transition: width 0.3s ease; }
    
    .disk { margin-top: 0; }
    .disk-item { margin-bottom: var(--gap-md); font-size: 13px; }
    .disk-item:last-child { margin-bottom: 0; }
    .disk-header { display:flex; justify-content:space-between; margin-bottom: 4px; }
    .mount { font-family: var(--font-mono); font-weight:700; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%; display: inline-block; }
/sysinfo    .disk-val { font-family: var(--font-mono); font-size: 12px; color: var(--color-text-secondary); font-weight: 500; }
    
    .footer { position: absolute; bottom: 24px; color: var(--color-text-tertiary); font-size: 12px; z-index:3; width: 100%; padding: 0 var(--pad-root); box-sizing: border-box; pointer-events: none; font-weight: 500; letter-spacing: 0.5px; text-shadow: 0 0 5px rgba(0,0,0,0.5); }
    
    .proc-table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
    .proc-table td { padding: 8px 0; vertical-align: top; border-bottom: 1px solid rgba(59,130,246,0.15); }
    .proc-table tr:last-child td { border-bottom: none; }
    .proc-table td.p-name { padding-right: 12px; width: 65%; }
    .proc-table td.p-val { text-align: right; white-space: nowrap; width: 35%; }
    .proc-main { font-weight: 700; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .proc-sub { font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; font-family: var(--font-mono); font-weight: 500; }
    .proc-val-main { font-family: var(--font-mono); font-weight: 700; color: var(--color-text-primary); }
    .proc-val-sub { font-family: var(--font-mono); font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; font-weight: 500; }
    
    .card-title { font-size: 18px; font-weight: 700; margin-bottom: 20px; color: #fff; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 10px; }
    .card-title::before { content:''; display:block; width:8px; height:8px; background:{{ accent_color }}; border-radius:50%; box-shadow: 0 0 10px {{ accent_color }}; }
  </style>
  </head>
<body>
  <div class="root">
      {% if bg_image %}
        <div class="bg" style="background-image:url('{{ bg_image }}')"></div>
      {% endif %}
      <div class="content">
      <div class="header">
        <div class="title">{{ title }}</div>
        <div class="sub">{{ subline }}</div>
      </div>
      
      <div class="cards">
        {% if cpu_percent is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_cpu }}</span><span class="val">{{ cpu_percent }}%</span></div>
          <div class="bar"><div style="width: {{ cpu_percent }}%; background: {{ bar_color_cpu }};"></div></div>
        </div>
        {% endif %}
        {% if mem is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_memory }}</span><span class="val">{{ mem.percent }}%</span></div>
          <div class="bar"><div style="width: {{ mem.percent }}%; background: {{ bar_color_mem }};"></div></div>
          <div style="text-align:right; font-size:11px; color:var(--color-text-tertiary); margin-top:4px; font-family:var(--font-mono)">{{ mem.used_h }} / {{ mem.total_h }}</div>
        </div>
        {% endif %}
        {% if swap is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_swap }}</span><span class="val">{{ swap.percent }}%</span></div>
          <div class="bar"><div style="width: {{ swap.percent }}%; background: {{ bar_color_swap }};"></div></div>
          <div style="text-align:right; font-size:11px; color:var(--color-text-tertiary); margin-top:4px; font-family:var(--font-mono)">{{ swap.used_h }} / {{ swap.total_h }}</div>
        </div>
        {% endif %}
        {% if net_sent is not none and net_recv is not none %}
        <div class="card">
          <div class="metric"><span>{{ label_network }}</span><span class="val" style="font-size:12px">{{ (net_sent/1024/1024)|round(2) }} MB/s ↑ · {{ (net_recv/1024/1024)|round(2) }} MB/s ↓</span></div>
          <div class="bar"><div style="width: {{ net_bar_percent if net_bar_percent is not none else 0 }}%; background: {{ bar_color_net }};"></div></div>
        </div>
        {% endif %}
      </div>

      <div class="columns">
        <div class="col">
          <div class="card disk">
            <div class="card-title">{{ label_disk }}</div>
            {% if disk_total %}
            <div class="disk-item">
              <div class="disk-header">
                <span class="mount">{{ label_total }}</span>
                <span class="disk-val">{{ disk_total.percent }}% ({{ disk_total.used_h }}/{{ disk_total.total_h }})</span>
              </div>
              <div class="bar"><div style="width: {{ disk_total.percent }}%; background: {{ bar_color_disk }};"></div></div>
            </div>
            {% endif %}
            {% if disk_info and disk_info|length > 0 %}
              {% for d in disk_info %}
                <div class="disk-item">
                  <div class="disk-header">
                    <span class="mount" title="{{ d.mount }}">{{ d.mount }}</span>
                    <span class="disk-val">{{ d.percent }}% ({{ d.used_h }}/{{ d.total_h }})</span>
                  </div>
                  <div class="bar"><div style="width: {{ d.percent }}%; background: {{ bar_color_disk }};"></div></div>
                </div>
              {% endfor %}
            {% else %}
              <div class="disk-item">
                <div class="metric"><span class="mount">{{ label_no_part }}</span><span></span></div>
              </div>
            {% endif %}
          </div>
        </div>
        <div class="col">
          {% if bottom_right_panel == 'net_ifaces' and net_per and net_per|length > 0 %}
          <div class="card">
            <div class="card-title">{{ label_network }}</div>
            <table class="proc-table">
            {% for n in net_per %}
              <tr>
                <td class="p-name">
                  <div class="proc-main">{{ n.name }}</div>
                </td>
                <td class="p-val">
                  <div class="proc-val-main">{{ (n.up/1024/1024)|round(2) }} MB/s ↑</div>
                  <div class="proc-val-sub">{{ (n.down/1024/1024)|round(2) }} MB/s ↓</div>
                </td>
              </tr>
            {% endfor %}
            </table>
          </div>
          {% elif bottom_right_panel == 'processes' and top_procs and top_procs|length > 0 %}
          <div class="card">
            <div class="card-title">{{ label_top }}</div>
            <table class="proc-table">
            {% for p in top_procs %}
              <tr>
                  <td class="p-name">
                      <div class="proc-main">{{ p.name }}</div>
                      {% if process_show_user %}<div class="proc-sub">PID: {{ p.pid }} · {{ p.username }}</div>{% endif %}
                  </td>
                  <td class="p-val">
                      <div class="proc-val-main">{{ p.mem_h }}</div>
                      <div class="proc-val-sub">CPU: {{ p.cpu }}%</div>
                  </td>
              </tr>
            {% endfor %}
            </table>
          </div>
          {% elif bottom_right_panel == 'summary' %}
          <div class="card">
            <div class="card-title">System Summary</div>
            <div class="metric"><span>CPU Usage</span><span class="val">{{ cpu_percent }}%</span></div>
            {% if mem %}<div class="metric"><span>Memory Usage</span><span class="val">{{ mem.percent }}%</span></div>{% endif %}
            {% if swap %}<div class="metric"><span>Swap Usage</span><span class="val">{{ swap.percent }}%</span></div>{% endif %}
          </div>
          {% endif %}
        </div>
      </div>
      <div class="footer" style="{% if footer_position == 'left_bottom' %}left:24px{% else %}right:24px{% endif %}">{{ label_powered }}</div>
    </div>
  </div>
</body>
</html>
'''

TMPL_CUSTOM_DASHBOARD = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --bg-color: #111827;
            --text-main: #ffffff;
            --text-sub: #9ca3af;
            --card-bg: rgba(31, 41, 55, 0.85);
            --border-color: rgba(255, 255, 255, 0.1);
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --accent-yellow: #eab308;
            --accent-sky: #0ea5e9;
        }
        body {
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: system-ui, -apple-system, sans-serif;
            overflow: hidden;
            font-size: 24px;
            width: 100%;
            height: 100%;
        }
        .container {
            width: 100%;
            height: 100%;
            padding: 32px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            gap: 24px;
            position: relative;
            z-index: 10;
        }
        .bg-layer {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            z-index: 0;
            background-size: cover;
            background-position: center;
            filter: brightness(0.4);
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(16px);
        }
        .header-title {
            font-size: 48px;
            font-weight: 700;
            text-align: center;
            margin: 0 0 24px 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.6);
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(156, 163, 175, 0.2);
            margin-bottom: 12px;
        }
        .info-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        .info-label { color: var(--text-sub); font-size: 24px; font-weight: 500; }
        .info-value { font-family: monospace; font-size: 24px; font-weight: 600; }

        .circles-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 16px;
        }
        .circle-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 16px;
        }
        .circle-wrap {
            position: relative;
            width: 160px;
            height: 160px;
            margin-bottom: 12px;
        }
        .circle-text {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: monospace;
            font-size: 36px;
            font-weight: 700;
        }
        .circle-label {
            font-size: 20px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .section-title {
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 16px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .net-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        .net-box {
            background: rgba(31, 41, 55, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px;
            text-align: center;
        }
        .net-label { font-size: 16px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
        .net-val { font-family: monospace; font-size: 32px; font-weight: 700; }

        .proc-list { display: flex; flex-direction: column; gap: 16px; }
        .proc-item { position: relative; }
        .proc-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 4px;
            position: relative;
            z-index: 2;
        }
        .proc-info { display: flex; flex-direction: column; max-width: 65%; }
        .proc-name { font-size: 24px; font-weight: 700; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
        .proc-detail { font-size: 16px; color: var(--text-sub); font-family: monospace; }
        .proc-stats { display: flex; flex-direction: column; align-items: flex-end; }
        .proc-cpu { font-size: 24px; font-weight: 700; font-family: monospace; color: var(--accent-yellow); }
        .proc-mem { font-size: 16px; color: var(--text-sub); font-family: monospace; }
        .proc-bar-bg {
            height: 8px;
            background: rgba(55, 65, 81, 0.5);
            border-radius: 4px;
            overflow: hidden;
        }
        .proc-bar-fill {
            height: 100%;
            background: var(--accent-yellow);
            border-radius: 4px;
        }

        .disk-list { display: flex; flex-direction: column; gap: 16px; }
        .disk-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
        .disk-name { font-family: monospace; font-weight: 600; font-size: 20px; }
        .disk-usage { font-family: monospace; color: var(--text-sub); font-size: 18px; }
        .disk-bar-bg { height: 12px; background: rgba(55, 65, 81, 0.5); border-radius: 6px; overflow: hidden; }
        .disk-bar-fill { height: 100%; background: var(--accent-sky); border-radius: 6px; }

        .footer {
            text-align: center;
            color: rgba(156, 163, 175, 0.5);
            font-size: 16px;
            font-weight: 500;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: auto;
        }
    </style>
</head>
<body>
    {% if bg_image %}
    <div class="bg-layer" style="background-image: url('{{ bg_image }}'); background-size: {{ background_fit_css }};"></div>
    {% else %}
    <div class="bg-layer" style="background: linear-gradient(135deg, #111827 0%, #1e1b4b 100%);"></div>
    {% endif %}

    <div class="container">
        <!-- Header -->
        <div class="card">
            <h1 class="header-title">{{ title }}</h1>
            <div class="info-row">
                <span class="info-label">Host</span>
                <span class="info-value">{{ host }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">OS</span>
                <span class="info-value">{{ os_str }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Uptime</span>
                <span class="info-value">{{ uptime_str }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Time</span>
                <span class="info-value">{{ ts }}</span>
            </div>
        </div>

        <!-- Circles -->
        <div class="circles-row">
            <div class="card circle-card">
                <div class="circle-wrap">
                    <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width:100%; height:100%;">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10"/>
                        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--accent-purple)" stroke-width="10"
                            stroke-dasharray="264"
                            stroke-dashoffset="{{ 264 - (264 * cpu_percent / 100) }}"
                            stroke-linecap="round"/>
                    </svg>
                    <div class="circle-text">{{ cpu_percent }}<span style="font-size:18px">%</span></div>
                </div>
                <div class="circle-label" style="color: var(--accent-purple)">CPU</div>
            </div>
            <div class="card circle-card">
                <div class="circle-wrap">
                    <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width:100%; height:100%;">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10"/>
                        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--accent-green)" stroke-width="10"
                            stroke-dasharray="264"
                            stroke-dashoffset="{{ 264 - (264 * mem.percent / 100) }}"
                            stroke-linecap="round"/>
                    </svg>
                    <div class="circle-text">{{ mem.percent }}<span style="font-size:18px">%</span></div>
                </div>
                <div class="circle-label" style="color: var(--accent-green)">RAM</div>
            </div>
            <div class="card circle-card">
                <div class="circle-wrap">
                    <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width:100%; height:100%;">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10"/>
                        <circle cx="50" cy="50" r="42" fill="none" stroke="#6b7280" stroke-width="10"
                            stroke-dasharray="264"
                            stroke-dashoffset="{{ 264 - (264 * disk_total.percent / 100) if disk_total else 264 }}"
                            stroke-linecap="round"/>
                    </svg>
                    <div class="circle-text">{{ disk_total.percent if disk_total else 0 }}<span style="font-size:18px">%</span></div>
                </div>
                <div class="circle-label" style="color: #9ca3af">DISK</div>
            </div>
        </div>

        <!-- Network -->
        <div class="card">
            <div class="section-title" style="color: var(--accent-blue)">
                <!-- SVG Icon for Network -->
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
                Network
            </div>
            <div class="net-grid">
                <div class="net-box">
                    <div class="net-label" style="color: var(--accent-blue)">Upload</div>
                    <div class="net-val">{{ net_sent_str }}</div>
                </div>
                <div class="net-box">
                    <div class="net-label" style="color: var(--accent-green)">Download</div>
                    <div class="net-val">{{ net_recv_str }}</div>
                </div>
            </div>
        </div>

        <!-- Top Processes -->
        {% if top_procs %}
        <div class="card" style="flex-grow: 1;">
            <div class="section-title" style="color: var(--accent-yellow)">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M9 3L5 6.99h3V14h2V6.99h3L9 3zm7 14.01V10h-2v7.01h-3L15 21l4-3.99h-3z"/></svg>
                Top Processes
            </div>
            <div class="proc-list">
                {% for p in top_procs %}
                <div class="proc-item">
                    <div class="proc-row">
                        <div class="proc-info">
                            <div class="proc-name">{{ p.name }}</div>
                            <div class="proc-detail">PID: {{ p.pid }} · {{ p.username }}</div>
                        </div>
                        <div class="proc-stats">
                            <div class="proc-cpu">{{ p.cpu }}%</div>
                            <div class="proc-mem">{{ p.mem_h }}</div>
                        </div>
                    </div>
                    <div class="proc-bar-bg">
                        <div class="proc-bar-fill" style="width: {{ p.cpu }}%;"></div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Partitions -->
        {% if disk_info %}
        <div class="card">
            <div class="section-title" style="color: var(--text-sub)">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z"/></svg>
                Partitions
            </div>
            <div class="disk-list">
                {% for d in disk_info %}
                <div>
                    <div class="disk-row">
                        <span class="disk-name">{{ d.mount }}</span>
                        <span class="disk-usage">{{ d.used_h }} / {{ d.total_h }} ({{ d.percent }}%)</span>
                    </div>
                    <div class="disk-bar-bg">
                        <div class="disk-bar-fill" style="width: {{ d.percent }}%;"></div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="footer">
            Powered by AstrBot
        </div>
    </div>
</body>
</html>
'''

# ============================================================================
# Utilities
# ============================================================================

LABELS = {
    "zh": {
        "cpu": "CPU",
        "memory": "内存",
        "disk": "磁盘分区",
        "network": "网络",
        "swap": "交换内存",
        "total": "总览",
        "no_part": "无可用分区",
        "top": "进程榜单",
        "powered": "Powered by AstrBot"
    },
    "en": {
        "cpu": "CPU",
        "memory": "Memory",
        "disk": "Disk Partitions",
        "network": "Network",
        "swap": "Swap",
        "total": "Total",
        "no_part": "No partitions",
        "top": "Top Processes",
        "powered": "Powered by AstrBot"
    }
}

def get_labels(locale: str) -> Dict[str, str]:
    if locale not in LABELS:
        locale = "en"
    
    labels = {}
    for key in LABELS["en"].keys():
        if locale in LABELS and key in LABELS[locale]:
            labels[f"label_{key}"] = LABELS[locale][key]
        else:
            labels[f"label_{key}"] = LABELS[locale][key]
    
    return labels

def merge_config(plugin_config: Dict[str, Any], 
                 session_config: Optional[Dict[str, Any]] = None,
                 command_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    effective = dict(plugin_config)
    if session_config and isinstance(session_config, dict):
        for key in list(effective.keys()):
            if key in session_config:
                effective[key] = session_config[key]
    if command_params and isinstance(command_params, dict):
        for key, value in command_params.items():
            if value is not None:
                effective[key] = value
    return effective

def resolve_background(mode: str, 
                      url: str, 
                      file_path: str,
                      auto_background: bool,
                      fit: str) -> Tuple[str, str]:
    if auto_background and mode == "none":
        if url:
            mode = "url"
        elif file_path:
            mode = "file"
    
    bg_image = ""
    if mode == "url" and url:
        bg_image = url
    elif mode == "file" and file_path:
        try:
            fp = file_path
            if not os.path.isabs(fp):
                fp = os.path.join(os.path.dirname(__file__), fp)
            with open(fp, "rb") as f:
                data = f.read()
            ext = os.path.splitext(fp)[1][1:] or "jpeg"
            mime = f"image/{ext}"
            bg_image = "data:" + mime + ";base64," + base64.b64encode(data).decode()
        except Exception as e:
            logger.warning(f"Error loading background file: {file_path} - {str(e)}")
            bg_image = ""
    
    if fit == "fill":
        fit_css = "100% 100%"
    elif fit == "contain":
        fit_css = "contain"
    else:
        fit_css = "cover"
    
    return bg_image, fit_css

# ============================================================================
# Plugin
# ============================================================================

@register("sysinfoimg", "Binbim", "专注于系统硬件监控的插件，生成美观的系统状态图片，轻量高效", "2.0.0")
class ImgSysInfoPlugin(Star):
    CONFIG_NAMESPACE = "astrbot_plugin_sysinfoimg"
    
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    def _get_cfg(self, event_or_umo: Any, command_params: Optional[Dict[str, Any]] = None):
        plugin_config = dict(self.config)
        session_config = None
        if bool(plugin_config.get("enable_session_config", False)):
            try:
                # Handle both Event and UMO
                umo = event_or_umo.unified_msg_origin if hasattr(event_or_umo, "unified_msg_origin") else event_or_umo
                session_cfg = self.context.get_config(umo=umo)
                if isinstance(session_cfg, dict):
                    session_config = session_cfg
            except Exception:
                pass
        return merge_config(plugin_config, session_config, command_params)

    def _fmt_bytes(self, n: int):
        u = ["B","KB","MB","GB","TB"]
        s = 0
        v = float(n)
        while v >= 1024 and s < len(u)-1:
            v /= 1024
            s += 1
        return f"{v:.1f}{u[s]}"

    def _norm_mounts(self, parts_cfg):
        res = []
        for p in parts_cfg or []:
            if os.name == "nt":
                if len(p) == 2 and p[1] == ":":
                    res.append(p + "\\")
                else:
                    res.append(p)
            else:
                res.append(p)
        return res

    def _list_disks(self, parts_cfg):
        disks = []
        
        # Helper to add disk
        def add_disk(mp):
            try:
                du = psutil.disk_usage(mp)
                # Check if already added (by mountpoint)
                for d in disks:
                    if d["mount"] == mp: return
                
                disks.append({
                    "mount": mp,
                    "percent": int(du.percent),
                    "used_h": self._fmt_bytes(du.used),
                    "total_h": self._fmt_bytes(du.total),
                    "used_raw": du.used,
                    "total_raw": du.total
                })
            except Exception: pass

        if parts_cfg:
            for mp in parts_cfg:
                add_disk(mp)
            # Calculate totals
            t_used = sum(d["used_raw"] for d in disks)
            t_total = sum(d["total_raw"] for d in disks)
            return disks, t_used, t_total

        ignore_fstypes = {'squashfs', 'overlay', 'tmpfs', 'devtmpfs', 'iso9660', 'tracefs', 'cgroup', 'sysfs', 'proc', 'autofs', 'fuse.sshfs'}
        ignore_paths = {'/proc', '/sys', '/dev', '/run', '/boot', '/snap'}
        ignore_path_prefixes = ('/var/lib/docker', '/var/lib/kubelet', '/var/lib/containers', '/run/docker', '/run/user', '/etc/')

        try:
            partitions = psutil.disk_partitions(all=False)
            if os.name != 'nt':
                 partitions = psutil.disk_partitions(all=True)

            seen_devices = set()
            for p in partitions:
                # Force include root path /
                if p.mountpoint == '/':
                    pass
                elif p.fstype in ignore_fstypes: continue
                
                if p.mountpoint in ignore_paths: continue
                if any(p.mountpoint.startswith(prefix) for prefix in ignore_path_prefixes): continue
                if 'ro' in p.opts and 'loop' in p.device: continue
                if p.device.startswith('/dev/'):
                    if p.device in seen_devices: continue
                    seen_devices.add(p.device)

                mp = p.mountpoint
                try:
                    du = psutil.disk_usage(mp)
                    # Allow / even if small (unlikely)
                    if du.total < 100 * 1024 * 1024 and mp != '/': continue
                    add_disk(mp)
                except Exception:
                    pass
        except Exception:
            pass
            
        if len(disks) > 8:
            disks = disks[:8]

        if not disks and os.name == "nt":
            for code in range(ord('A'), ord('Z')+1):
                mp = chr(code) + ":\\"
                if os.path.exists(mp):
                    add_disk(mp)
        
        if not disks and os.name != "nt":
            for mp in ["/", "/home", "/data", "/mnt", "/var", "/opt"]:
                if os.path.exists(mp):
                    add_disk(mp)
        
        t_used = sum(d["used_raw"] for d in disks)
        t_total = sum(d["total_raw"] for d in disks)
        return disks, t_used, t_total

    async def _net_sample(self, interfaces, interval):
        pernic1 = psutil.net_io_counters(pernic=True)
        await asyncio.sleep(interval)
        pernic2 = psutil.net_io_counters(pernic=True)
        names = interfaces or [n for n in pernic2.keys() if n != "lo"]
        sent = 0
        recv = 0
        items = []
        for n in names:
            if n in pernic1 and n in pernic2:
                up = max(0, pernic2[n].bytes_sent - pernic1[n].bytes_sent) / interval
                down = max(0, pernic2[n].bytes_recv - pernic1[n].bytes_recv) / interval
                sent += up
                recv += down
                items.append({"name": n, "up": up, "down": down})
        return sent, recv, items

    def _fmt_duration(self, seconds):
        d = int(seconds // 86400)
        h = int((seconds % 86400) // 3600)
        m = int((seconds % 3600) // 60)
        if d > 0: return f"{d}d {h}h {m}m"
        if h > 0: return f"{h}h {m}m"
        return f"{m}m"

    def _top_processes(self, n, sort_key="memory"):
        def rss_fallback(pid):
            try:
                if os.name != "nt":
                    path = f"/proc/{pid}/status"
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if line.startswith("VmRSS:"):
                                    parts = line.split()
                                    if len(parts) >= 2:
                                        return int(float(parts[1]) * 1024)
            except Exception: pass
            return None

        procs = []
        try:
            for p in psutil.process_iter(attrs=["pid", "name", "username", "cmdline", "cpu_percent"]):
                pid = p.info.get("pid")
                name = p.info.get("name")
                if not name:
                    cmd = p.info.get("cmdline") or []
                    if isinstance(cmd, list) and len(cmd) > 0:
                        name = os.path.basename(cmd[0])
                    else:
                        name = f"pid:{pid}"
                mem = None
                try:
                    mem = p.memory_info().rss
                except Exception:
                    mem = rss_fallback(pid)
                if mem is None: continue
                percent = 0
                try:
                    percent = int(p.memory_percent())
                except Exception: percent = 0
                cpu = 0
                try:
                    cpu = p.info.get("cpu_percent") or 0
                except: pass

                procs.append({
                    "pid": pid,
                    "name": name,
                    "username": p.info.get("username") or "N/A",
                    "mem": mem,
                    "mem_h": self._fmt_bytes(mem),
                    "mem_percent": percent,
                    "cpu": cpu
                })
        except Exception: pass
        
        if sort_key == "cpu":
            procs.sort(key=lambda x: x["cpu"], reverse=True)
        else:
            procs.sort(key=lambda x: x["mem"], reverse=True)
        return procs[:max(1, n)]

    def _fmt_rate(self, b_per_sec: float) -> str:
        if b_per_sec < 1024:
            return f"{int(b_per_sec)} B/s"
        elif b_per_sec < 1024 * 1024:
            return f"{b_per_sec/1024:.1f} KB/s"
        else:
            return f"{b_per_sec/1024/1024:.1f} MB/s"

    @filter.command("sysinfo")
    async def sysinfo(self, event: AstrMessageEvent, title: str = ""):
        url = await self.get_sysinfo_url(event, title)
        yield event.image_result(url)

    async def get_sysinfo_url(self, event_or_umo, title: str = ""):
        cfg = self._get_cfg(event_or_umo)
        theme = str(cfg.get("theme", "custom_dashboard")) # Default to custom_dashboard
        bg_mode = str(cfg.get("background_mode", "none"))
        bg_url = str(cfg.get("background_url", ""))
        bg_file = str(cfg.get("background_file", ""))
        background_fit = str(cfg.get("background_fit", "cover"))
        auto_background = bool(cfg.get("auto_background", True))
        text_color_raw = str(cfg.get("text_color", "#ffffff"))
        accent_color = str(cfg.get("accent_color", "#6366f1"))
        
        # Determine dimensions
        w_cfg = cfg.get("width")
        h_cfg = cfg.get("height")
        
        # Default to vertical 720x1280 for ALL themes if not explicitly set
        if w_cfg is None: width = 720
        else: width = int(w_cfg)
        
        if h_cfg is None: height = 1280
        else: height = int(h_cfg)
        
        # Fix legacy default (1280x720) -> swap to vertical
        if width == 1280 and height == 720:
            width = 720
            height = 1280

        show_cpu = bool(cfg.get("show_cpu", True))
        show_memory = bool(cfg.get("show_memory", True))
        show_disk = bool(cfg.get("show_disk", True))
        parts_cfg = self._norm_mounts(cfg.get("disk_partitions", []) or [])
        force_show_empty_disk = bool(cfg.get("force_show_empty_disk", True))
        show_hostname = bool(cfg.get("show_hostname", True))
        show_time = bool(cfg.get("show_time", True))
        locale = str(cfg.get("locale", "zh"))
        show_network = bool(cfg.get("show_network", True))
        net_ifaces = cfg.get("network_interfaces", []) or []
        show_swap = bool(cfg.get("show_swap", True))
        show_top = bool(cfg.get("show_top_processes", True)) # Default True now
        top_n = int(cfg.get("top_n", 10)) # Default 10
        show_os = bool(cfg.get("show_os", True))
        show_uptime = bool(cfg.get("show_uptime", True))
        show_disk_total = bool(cfg.get("show_disk_total", True))
        show_network_per_iface = bool(cfg.get("show_network_per_iface", False))
        bottom_right_panel = str(cfg.get("bottom_right_panel", "net_ifaces"))
        process_sort_key = str(cfg.get("process_sort_key", "cpu")) # Default sort by CPU
        process_show_user = bool(cfg.get("process_show_user", True))

        t = title or str(cfg.get("title", "系统状态"))
        host = platform.node() if show_hostname else ""
        now = datetime.datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S") if show_time else ""
        os_str = f"{platform.system()} {platform.release()}" if show_os else ""
        uptime_str = self._fmt_duration(now.timestamp() - psutil.boot_time()) if show_uptime else ""

        # --- Phase 1: Initialization & Pre-heat ---
        
        # 1. CPU Pre-heat
        if show_cpu:
            psutil.cpu_percent(interval=None)

        # 2. Network Pre-heat
        net_start = None
        if show_network:
            try:
                net_start = psutil.net_io_counters(pernic=True)
            except Exception: pass

        # 3. Process Pre-heat
        procs_list = []
        if show_top:
            try:
                # Iterate once to get objects and initialize their CPU counters
                for p in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
                    try:
                        p.cpu_percent() # Init call
                        procs_list.append(p)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            except Exception: pass

        # --- Phase 2: Sampling Window ---
        # Sleep 1s to allow rates to be calculated accurately
        await asyncio.sleep(1.0)

        # --- Phase 3: Collection ---

        # 1. CPU
        cpu_p = psutil.cpu_percent(interval=None) if show_cpu else 0

        # 2. Memory
        mem = psutil.virtual_memory() if show_memory else None
        mem_data = None
        if mem:
            mem_data = {
                "percent": int(mem.percent),
                "used_h": self._fmt_bytes(mem.used),
                "total_h": self._fmt_bytes(mem.total),
            }

        # 3. Swap
        swap = psutil.swap_memory() if show_swap else None
        swap_data = None
        if swap:
            swap_data = {
                "percent": int(swap.percent),
                "used_h": self._fmt_bytes(swap.used),
                "total_h": self._fmt_bytes(swap.total),
            }

        # 4. Disk (Corrected)
        disk_info = []
        disk_total = None
        if show_disk:
            d_list, t_used, t_total = self._list_disks(parts_cfg)
            disk_info = d_list
            
            # Use calculated total if available and accurate
            if t_total > 0:
                 disk_total = {
                    "percent": int(t_used * 100 / t_total),
                    "used_h": self._fmt_bytes(t_used),
                    "total_h": self._fmt_bytes(t_total),
                 }
            # Fallback to global iteration if list_disks was empty or limited, ONLY if show_disk_total is forced and we have no data
            elif show_disk_total and not disk_total:
                 try:
                    used_b = 0
                    total_b = 0
                    for p in psutil.disk_partitions(all=True):
                        try:
                            du = psutil.disk_usage(p.mountpoint)
                            used_b += du.used
                            total_b += du.total
                        except: pass
                    if total_b > 0:
                        disk_total = {
                            "percent": int(used_b * 100 / total_b),
                            "used_h": self._fmt_bytes(used_b),
                            "total_h": self._fmt_bytes(total_b),
                        }
                 except: pass

        # 5. Network (Corrected)
        net_sent = 0
        net_recv = 0
        net_per = []
        net_sent_str = "0 B/s"
        net_recv_str = "0 B/s"
        if show_network and net_start:
            try:
                net_end = psutil.net_io_counters(pernic=True)
                # Calculate diff
                # Default to all non-lo if interfaces not specified
                names = net_ifaces or [n for n in net_end.keys() if n != "lo" and n in net_start]
                
                for n in names:
                    if n in net_start and n in net_end:
                        # 1.0s interval, so diff is bytes/sec
                        up = max(0, net_end[n].bytes_sent - net_start[n].bytes_sent)
                        down = max(0, net_end[n].bytes_recv - net_start[n].bytes_recv)
                        net_sent += up
                        net_recv += down
                        if show_network_per_iface:
                            net_per.append({"name": n, "up": up, "down": down})
                
                net_sent_str = self._fmt_rate(net_sent)
                net_recv_str = self._fmt_rate(net_recv)
            except Exception: pass

        # 6. Processes (Corrected)
        top_procs = []
        if show_top and procs_list:
            processed_procs = []
            for p in procs_list:
                try:
                    # Second call to cpu_percent returns usage since first call
                    cpu = p.cpu_percent()
                    
                    # Memory
                    mem_info = p.memory_info()
                    mem_rss = mem_info.rss
                    
                    name = p.info.get('name')
                    if not name:
                        cmd = p.info.get('cmdline')
                        if cmd: name = os.path.basename(cmd[0])
                        else: name = f"pid:{p.pid}"

                    processed_procs.append({
                        "pid": p.pid,
                        "name": name,
                        "username": p.info.get('username') or "N/A",
                        "mem": mem_rss,
                        "mem_h": self._fmt_bytes(mem_rss),
                        "cpu": cpu
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort with secondary key
            if process_sort_key == "cpu":
                processed_procs.sort(key=lambda x: (x["cpu"], x["mem"]), reverse=True)
            else:
                processed_procs.sort(key=lambda x: (x["mem"], x["cpu"]), reverse=True)
            
            top_procs = processed_procs[:top_n]

        bg_image, background_fit_css = resolve_background(bg_mode, bg_url, bg_file, auto_background, background_fit)
        
        if theme == "light_card" and text_color_raw.lower() == "#ffffff":
            text_color = "#111111"
        else:
            text_color = text_color_raw

        labels = get_labels(locale)
        
        sub_parts = []
        if host: sub_parts.append(host)
        if ts: sub_parts.append(ts)
        if os_str: sub_parts.append(os_str)
        if uptime_str: sub_parts.append(uptime_str)
        subline = " · ".join(sub_parts)

        footer_position = cfg.get("footer_position", "left_bottom")
        bar_color_cpu = cfg.get("bar_color_cpu", accent_color)
        bar_color_mem = cfg.get("bar_color_mem", accent_color)
        bar_color_swap = cfg.get("bar_color_swap", accent_color)
        bar_color_net = cfg.get("bar_color_net", accent_color)
        bar_color_disk = cfg.get("bar_color_disk", accent_color)

        net_bar_percent = None
        try:
            if net_recv is not None:
                # Simple scaling: 10MB/s = 100%
                net_bar_percent = max(0, min(100, (net_recv/1024/1024)*10))
        except Exception:
            net_bar_percent = 0

        data = {
            "title": t,
            "subline": subline,
            "text_color": text_color,
            "accent_color": accent_color,
            "footer_position": footer_position,
            "bar_color_cpu": bar_color_cpu,
            "bar_color_mem": bar_color_mem,
            "bar_color_swap": bar_color_swap,
            "bar_color_net": bar_color_net,
            "bar_color_disk": bar_color_disk,
            "cpu_percent": cpu_p,
            "mem": mem_data,
            "swap": swap_data,
            "disk_info": disk_info,
            "disk_total": disk_total,
            "net_sent": net_sent,
            "net_recv": net_recv,
            "net_sent_str": net_sent_str,
            "net_recv_str": net_recv_str,
            "net_bar_percent": net_bar_percent,
            "net_per": net_per,
            "top_procs": top_procs,
            "process_show_user": process_show_user,
            "bg_image": bg_image,
            "background_fit_css": background_fit_css,
            "bottom_right_panel": bottom_right_panel,
            "label_cpu": labels.get("label_cpu", "CPU"),
            "label_memory": labels.get("label_memory", "Memory"),
            "label_swap": labels.get("label_swap", "Swap"),
            "label_network": labels.get("label_network", "Network"),
            "label_disk": labels.get("label_disk", "Disk"),
            "label_total": labels.get("label_total", "Total"),
            "label_no_part": labels.get("label_no_part", "No partitions"),
            "label_top": labels.get("label_top", "Top Processes"),
            "label_powered": labels.get("label_powered", "Powered by AstrBot"),
            "host": host,
            "os_str": os_str,
            "uptime_str": uptime_str,
            "ts": ts,
        }

        if theme == "dark_glass":
            tmpl = TMPL_DARK_GLASS
        elif theme == "light_card":
            tmpl = TMPL_LIGHT_CARD
        elif theme == "custom_dashboard":
            tmpl = TMPL_CUSTOM_DASHBOARD
            if height < 1000:
                logger.warning(f"Height {height} might be too short for custom_dashboard")
        else:
            tmpl = TMPL_NEON

        logger.info({
            "theme": theme,
            "title": t,
            "width": width,
            "height": height,
            "cpu": cpu_p,
            "net_sent": net_sent_str,
            "top_procs": len(top_procs)
        })

        return await self.html_render(tmpl, data, options={"width": width, "height": height})

    @filter.command("sysinfo_auto")
    async def sysinfo_auto(self, event: AstrMessageEvent, interval: str = ""):
        '''设置自动发送间隔(分钟), 输入 off 关闭'''
        from astrbot.api.message_components import Plain
        
        if not interval:
            yield event.plain_result("请提供间隔分钟数，例如: /sysinfo_auto 60。输入 off 关闭。")
            return

        # Reload latest tasks
        self._reload_settings()

        # Ensure we are accessing the UMO object, not a string
        umo = event.unified_msg_origin
        umo_dict = None
        raw_umo_str = None
        
        if isinstance(umo, str):
            logger.warning(f"sysinfo_auto: UMO is string: {umo}")
            raw_umo_str = umo
            # Try parsing as JSON
            try:
                parsed = json.loads(umo)
                if isinstance(parsed, dict):
                    umo_dict = parsed
            except:
                pass
            
            # Fallback: Try parsing adapter_id:kind:session_id
            if not umo_dict and ":" in umo:
                parts = umo.split(":")
                if len(parts) >= 3:
                    # Construct a FULL UMO dict compatible with UnifiedMessageOrigin
                    umo_dict = {
                        "adapter_id": parts[0],
                        "message_type": parts[1], 
                        "session_id": parts[2],
                        "guild_id": None,
                        "channel_id": None,
                        "sender_id": None,
                        "group_id": None
                    }
                    
                    # Heuristic for GroupMessage
                    if "Group" in parts[1]:
                         umo_dict["group_id"] = parts[2]
                         # For some adapters, session_id IS group_id
                    
                    if len(parts) > 3:
                        umo_dict["guild_id"] = parts[3]
                        
            if not umo_dict:
                # If it's a string but not JSON, we can't use it for scheduler
                yield event.plain_result(f"无法获取有效的会话上下文。可能原因：Adapter返回了非标准UMO格式。")
                return
        elif umo is None:
             yield event.plain_result("无法获取会话上下文 (UMO is None)")
             return
        else:
            try:
                if hasattr(umo, "to_dict"):
                    umo_dict = umo.to_dict()
                else:
                    yield event.plain_result(f"无法获取会话上下文 (UMO has no to_dict: {type(umo)})")
                    return
            except Exception as e:
                logger.error(f"Error serializing UMO: {e}")
                yield event.plain_result(f"内部错误：无法序列化会话信息 ({e})")
                return
        
        try:
            umo_key = json.dumps(umo_dict, sort_keys=True)
        except Exception as e:
             yield event.plain_result(f"内部错误：无法生成会话键 ({e})")
             return
        
        if interval.lower() == "off":
            if umo_key in self.auto_tasks:
                del self.auto_tasks[umo_key]
                if umo_key in self.last_run:
                    del self.last_run[umo_key]
                self._save_tasks()
                yield event.plain_result("已关闭当前会话的自动发送。")
            else:
                yield event.plain_result("当前会话未开启自动发送。")
            return

        try:
            mins = int(interval)
            if mins < 1:
                yield event.plain_result("间隔必须大于 1 分钟。")
                return
            
            # Update configuration
            self.auto_tasks[umo_key] = {
                "interval": mins,
                "umo_dict": umo_dict,
                "raw_umo": raw_umo_str,
                "created_at": datetime.datetime.now().timestamp(),
                "enabled": True
            }
            # Mark last run as now to avoid immediate send
            self.last_run[umo_key] = datetime.datetime.now().timestamp()
            self._save_tasks() # Persist immediately
            
            # --- Immediate Test Send ---
            try:
                from astrbot.api.message_components import Image
                
                # Define a local dummy enum if import fails
                class DummyMessageEventType:
                    GROUP_MESSAGE = "group_message"
                    FRIEND_MESSAGE = "friend_message"
                    GUILD_MESSAGE = "guild_message"

                MessageEventType = DummyMessageEventType
                try:
                    from astrbot.api.event import MessageEventType
                except ImportError:
                    pass
                
                try:
                    from astrbot.core.platform.sources.unified_message_origin import UnifiedMessageOrigin
                except ImportError:
                    # Fallback for older versions or different structure
                    try:
                        from astrbot.api.event import UnifiedMessageOrigin
                    except ImportError:
                         # Fallback to dummy class
                        class UnifiedMessageOrigin:
                            def __init__(self, **kwargs):
                                for k, v in kwargs.items():
                                    setattr(self, k, v)
                                # Compatibility: Alias platform_name to adapter_id
                                if not hasattr(self, "platform_name"):
                                    self.platform_name = kwargs.get("adapter_id", "unknown")

                            @classmethod
                            def from_dict(cls, data):
                                return cls(**data)

                # Reconstruct UMO for test
                test_umo = UnifiedMessageOrigin.from_dict(umo_dict)
                # Manual fix for Enum
                if hasattr(test_umo, "message_type") and isinstance(test_umo.message_type, str):
                    mt = test_umo.message_type.lower()
                    if "group" in mt:
                        test_umo.message_type = MessageEventType.GROUP_MESSAGE
                    elif "private" in mt or "friend" in mt:
                        test_umo.message_type = MessageEventType.FRIEND_MESSAGE
                    elif "guild" in mt:
                        test_umo.message_type = MessageEventType.GUILD_MESSAGE
                
                # Generate and send
                url = await self.get_sysinfo_url(test_umo, "Test Report")
                try:
                    await self.context.send_message(test_umo, [Image.fromURL(url)])
                except AttributeError as e:
                    if "object has no attribute 'chain'" in str(e):
                        from astrbot.api.message_components import MessageChain
                        chain = MessageChain([Image.fromURL(url)])
                        await self.context.send_message(test_umo, chain)
                    else:
                        raise

                yield event.plain_result(f"✅ 已开启自动发送，每 {mins} 分钟发送一次。\n🎉 测试消息已发送成功！")
            except Exception as e:
                import traceback
                logger.error(f"Test send failed: {traceback.format_exc()}")
                yield event.plain_result(f"✅ 定时任务已保存，但测试发送失败。\n错误信息: {e}\n请检查日志获取详情。")
                
        except ValueError:
            yield event.plain_result("无效的分钟数。")

    async def _scheduler_loop(self):
        from astrbot.api.message_components import Image
        
        # Define a local dummy enum if import fails
        class DummyMessageEventType:
            GROUP_MESSAGE = "group_message"
            FRIEND_MESSAGE = "friend_message"
            GUILD_MESSAGE = "guild_message"

        MessageEventType = DummyMessageEventType
        try:
            from astrbot.api.event import MessageEventType
        except ImportError:
            pass

        try:
            from astrbot.core.platform.sources.unified_message_origin import UnifiedMessageOrigin
        except ImportError:
            try:
                from astrbot.api.event import UnifiedMessageOrigin
            except ImportError:
                # If still failing, define a minimal dummy class to satisfy runtime checks
                # This usually means AstrBot version is too old or structure is very different
                logger.warning("UnifiedMessageOrigin not found in known paths. Using dummy class.")
                class UnifiedMessageOrigin:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                        # Compatibility: Alias platform_name to adapter_id
                        if not hasattr(self, "platform_name"):
                            self.platform_name = kwargs.get("adapter_id", "unknown")

                    @classmethod
                    def from_dict(cls, data):
                        return cls(**data)
        
        logger.info("Sysinfo scheduler started")
        
        # Wait for AstrBot to initialize
        await asyncio.sleep(30)
        logger.info("Sysinfo scheduler: Initialization wait complete.")

        while True:
            # Main Loop
            try:
                self._load_tasks() # Reload tasks every loop to sync with file changes
                now = datetime.datetime.now().timestamp()
                
                if not self.auto_tasks:
                    await asyncio.sleep(60)
                    continue

                # Create a list to iterate safely
                for key, task in list(self.auto_tasks.items()):
                    interval_sec = task["interval"] * 60
                    last = self.last_run.get(key, 0)
                    
                    if now - last >= interval_sec:
                        # Time to send
                        try:
                            # Reconstruct UMO
                            umo_dict = task["umo_dict"]
                            umo = None
                            
                            # Ensure defaults for key fields if missing in legacy data
                            for f in ["guild_id", "channel_id", "sender_id", "group_id"]:
                                if f not in umo_dict:
                                    umo_dict[f] = None

                            try:
                                umo = UnifiedMessageOrigin.from_dict(umo_dict)
                            except Exception as e:
                                logger.error(f"UnifiedMessageOrigin.from_dict failed: {e}. Data: {umo_dict}")
                                continue
                            
                            # Manual fix for MessageEventType if it's a string (from JSON load)
                            if hasattr(umo, "message_type") and isinstance(umo.message_type, str):
                                mt = umo.message_type.lower()
                                if "group" in mt:
                                    umo.message_type = MessageEventType.GROUP_MESSAGE
                                elif "private" in mt or "friend" in mt:
                                    umo.message_type = MessageEventType.FRIEND_MESSAGE
                                elif "guild" in mt:
                                    umo.message_type = MessageEventType.GUILD_MESSAGE

                            if not umo:
                                logger.error("Failed to reconstruct UMO")
                                continue

                            # Generate image
                            try:
                                url = await self.get_sysinfo_url(umo, "Scheduled Report")
                            except Exception as e:
                                logger.error(f"Generate sysinfo image failed: {e}")
                                continue
                            
                            # Send message
                            logger.info(f"Sending scheduled sysinfo to {key}...")
                            try:
                                await self.context.send_message(umo, [Image.fromURL(url)])
                                # Update last run only if success
                                self.last_run[key] = now
                                logger.info(f"Sent scheduled sysinfo to {key}")
                            except AttributeError as e:
                                # Fix for list object has no attribute chain error in send_message
                                if "object has no attribute 'chain'" in str(e):
                                    logger.warning(f"AttributeError 'chain' caught. Retrying with direct list.")
                                    # Some versions of AstrBot/Adapter might expect just the list, not wrapped
                                    # But send_message expects MessageChain usually. 
                                    # If 'list' object has no attribute 'chain', it means send_message internal logic
                                    # received a list where it expected a MessageChain object.
                                    # Let's try constructing a MessageChain if possible
                                    try:
                                        from astrbot.api.message_components import MessageChain
                                        chain = MessageChain([Image.fromURL(url)])
                                        await self.context.send_message(umo, chain)
                                        self.last_run[key] = now
                                        logger.info(f"Sent scheduled sysinfo to {key} (Retry with MessageChain)")
                                    except ImportError:
                                         # If MessageChain not available, maybe we need to pass components directly?
                                         # The error suggests send_message implementation iterates over message_chain.chain
                                         # If we passed a list, list has no .chain
                                         pass
                            except Exception as e:
                                logger.error(f"Send message failed: {e}")
                                
                        except Exception as e:
                            logger.error(f"Failed to send scheduled sysinfo: {e}")
            except asyncio.CancelledError:
                logger.info("Sysinfo scheduler stopped.")
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            
            await asyncio.sleep(60) # Check every minute

    @filter.command("sysinfo_conf")
    async def sysinfo_conf(self, event: AstrMessageEvent):
        cfg = self._get_cfg(event)
        info = {
            "theme": cfg.get("theme"),
            "background_mode": cfg.get("background_mode"),
            "background_url_set": bool(cfg.get("background_url")),
            "background_file": cfg.get("background_file"),
            "title": cfg.get("title"),
            "locale": cfg.get("locale"),
            "width": cfg.get("width"),
            "height": cfg.get("height"),
            "background_fit": cfg.get("background_fit"),
            "auto_background": bool(cfg.get("auto_background", True)),
            "show_cpu": bool(cfg.get("show_cpu", True)),
            "show_memory": bool(cfg.get("show_memory", True)),
            "show_disk": bool(cfg.get("show_disk", True)),
            "disk_partitions": cfg.get("disk_partitions", []),
            "force_show_empty_disk": bool(cfg.get("force_show_empty_disk", True)),
        }
        yield event.plain_result(str(info))

    @filter.command("sysinfo_disks")
    async def sysinfo_disks(self, event: AstrMessageEvent):
        cfg = self._get_cfg(event)
        parts_cfg = self._norm_mounts(cfg.get("disk_partitions", []) or [])
        details = []
        errors = []
        found = []
        try:
            for p in psutil.disk_partitions(all=True):
                mp = p.mountpoint
                try:
                    du = psutil.disk_usage(mp)
                    found.append(mp)
                    details.append({
                        "mount": mp,
                        "percent": int(du.percent),
                        "used": self._fmt_bytes(du.used),
                        "total": self._fmt_bytes(du.total),
                    })
                except Exception as e:
                    errors.append({"mount": mp, "error": str(e)})
        except Exception as e:
            errors.append({"error": str(e)})

        if not found and os.name == "nt":
            for code in range(ord('A'), ord('Z')+1):
                mp = chr(code) + ":\\"
                if os.path.exists(mp):
                    try:
                        du = psutil.disk_usage(mp)
                        found.append(mp)
                        details.append({
                            "mount": mp,
                            "percent": int(du.percent),
                            "used": self._fmt_bytes(du.used),
                            "total": self._fmt_bytes(du.total),
                        })
                    except Exception as e:
                        errors.append({"mount": mp, "error": str(e)})

        if not found and os.name != "nt":
            for mp in ["/", "/home", "/data", "/mnt", "/var", "/opt"]:
                if os.path.exists(mp):
                    try:
                        du = psutil.disk_usage(mp)
                        found.append(mp)
                        details.append({
                            "mount": mp,
                            "percent": int(du.percent),
                            "used": self._fmt_bytes(du.used),
                            "total": self._fmt_bytes(du.total),
                        })
                    except Exception as e:
                        errors.append({"mount": mp, "error": str(e)})

        out = {
            "parts_cfg": parts_cfg,
            "found": found,
            "details": details,
            "errors": errors,
        }
        yield event.plain_result(json.dumps(out, ensure_ascii=False))
