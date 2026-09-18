"""
Single-file HTML Builder for Taigi Activities Calendar
Compiles activities into an iPhone & Android optimized, clutter-free standalone index.html
"""
import json
import os
from html import escape
from typing import List
from datetime import datetime, timezone, timedelta
from crawler.models import Activity
from crawler.sources.google_workspace import GoogleWorkspaceSync


def generate_single_html(activities: List[Activity], output_path: str = "index.html", resources=None) -> str:
    activities_data = []
    g_sync = GoogleWorkspaceSync()

    for act in activities:
        d = act.to_dict()
        d["gcal_url"] = g_sync.generate_google_calendar_url(act)
        d["ics_event"] = g_sync.event_content(act)
        activities_data.append(d)

    activities_json = json.dumps(activities_data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    calendar_header_json = json.dumps(g_sync.HEADER, ensure_ascii=False)

    resource_cards = ''.join(
        '<article class="resource-card"><small>' + escape(r['city']) + ' · ' +
        {'audio_guide': '台語語音導覽', 'reservation_guide': '台語導覽預約', 'exhibition_resource': '台語相關展覽', 'reading_resource': '台語閱讀推廣'}[r['kind']] +
        '</small><h3>' + escape(r['title']) + '</h3><p>' + escape(r['description']) +
        '</p><a href="' + escape(r['url'], quote=True) + '" target="_blank" rel="noopener noreferrer">查看官方資訊 ↗</a>' +
        '<small>核對：' + escape(r['checked_at'][:10]) + '</small></article>' for r in (resources or []))
    resource_section = ('<section id="guideResources" class="container guide-resources"><h2>台語導覽、展覽與閱讀資訊</h2>'
                        '<p>語音導覽、預約服務、書展與閱讀推廣；請依館方公告確認開館日、費用及預約。以下不列入場次數或日曆下載。</p>'
                        '<div class="resource-grid">' + resource_cards + '</div></section>') if resources else ''

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>北北桃台語活動日曆 | 臺北・新北・桃園 台語舞台劇/表演/故事/繪本/體驗/導覽</title>
  <meta name="description" content="北北桃台語活動行事曆：收錄有官方公告且經人工核對的場次。彙整臺北市、新北市、桃園市的台語舞台劇、表演、故事屋、台語繪本共讀、文化體驗、文史走讀導覽活動。">
  
  <!-- Android Chrome & PWA 支援 -->
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="theme-color" content="#C84C32">
  <link rel="manifest" href="manifest.json">
  
  <!-- iOS iPhone Web App (PWA) 支援 -->
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="台語日曆">
  <meta name="format-detection" content="telephone=no">
  <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%23C84C32'/><text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-size='50'>🎭</text></svg>">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%23C84C32'/><text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-size='50'>🎭</text></svg>">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700;900&family=Outfit:wght@500;600;700;800&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
  
  <style>
    .guide-resources {{ padding: 1.5rem 1rem; }}
    .guide-resources > p {{ color: var(--text-muted); margin: .6rem 0 1rem; }}
    .resource-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 1rem; }}
    .resource-card {{ padding: 1.2rem; border: 1px solid var(--border-color); border-radius: 14px; background: var(--bg-card); }}
    .resource-card h3 {{ margin: .5rem 0; font-size: 1.05rem; }}
    .resource-card p {{ line-height: 1.7; margin-bottom: .8rem; }}
    .resource-card a {{ color: var(--primary); }}
    .resource-card small {{ display: block; color: var(--text-muted); margin-top: .4rem; }}
    :root {{
      --font-main: -apple-system, BlinkMacSystemFont, 'Roboto', 'Noto Sans TC', 'SF Pro Text', 'PingFang TC', sans-serif;
      --font-display: 'Outfit', 'Roboto', 'Noto Sans TC', sans-serif;
      
      /* Colors */
      --bg-main: #F8F9FA;
      --bg-card: #FFFFFF;
      --bg-surface: #FFFFFF;
      --bg-hover: #F1F3F5;
      --border-color: #E2E8F0;
      --border-focus: #C84C32;
      
      --text-main: #1E293B;
      --text-muted: #64748B;
      --text-light: #94A3B8;
      
      /* Brand Accents */
      --primary: #C84C32; /* 胭脂磚紅 */
      --primary-hover: #B03A22;
      --primary-light: #FDE8E4;
      --primary-glow: rgba(200, 76, 50, 0.18);
      
      --secondary: #1D3557;
      --secondary-light: #EBF2F7;
      
      --accent-tea: #0D9488;
      --accent-tea-light: #CCFBF1;
      
      --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
      --shadow-md: 0 4px 14px rgba(0,0,0,0.08);
      --shadow-lg: 0 12px 32px rgba(0,0,0,0.12);
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-full: 9999px;
      
      --sat: env(safe-area-inset-top, 0px);
      --sab: env(safe-area-inset-bottom, 0px);
    }}

    [data-theme="dark"] {{
      --bg-main: #0B1120;
      --bg-card: #1E293B;
      --bg-surface: #1E293B;
      --bg-hover: #334155;
      --border-color: #334155;
      --border-focus: #E05A47;
      
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --text-light: #64748B;
      
      --primary: #E05A47;
      --primary-hover: #F26E5C;
      --primary-light: rgba(224, 90, 71, 0.2);
      
      --secondary: #38BDF8;
      --secondary-light: rgba(56, 189, 248, 0.15);
      
      --accent-tea: #2DD4BF;
      --accent-tea-light: rgba(45, 212, 191, 0.15);
      
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
      --shadow-md: 0 4px 14px rgba(0,0,0,0.4);
      --shadow-lg: 0 12px 36px rgba(0,0,0,0.6);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }}

    body {{
      font-family: var(--font-main);
      background-color: var(--bg-main);
      color: var(--text-main);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      transition: background-color 0.25s ease, color 0.25s ease;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 1320px;
      margin: 0 auto;
      width: 100%;
    }}

    /* Desktop Header */
    header.hero-header {{
      background: linear-gradient(135deg, #1E293B 0%, #0F172A 60%, #1D3557 100%);
      color: #FFFFFF;
      padding: 2.25rem 1.5rem 1.75rem;
      position: relative;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }}

    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .brand-icon {{
      width: 44px;
      height: 44px;
      background: var(--primary);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.4rem;
      box-shadow: 0 4px 12px var(--primary-glow);
      flex-shrink: 0;
    }}

    .brand-titles h1 {{
      font-size: 1.55rem;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}

    .brand-titles p {{
      font-size: 0.88rem;
      color: #CBD5E1;
      font-weight: 500;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.5rem 1rem;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: var(--radius-full);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      text-decoration: none;
      user-select: none;
    }}

    .btn:active {{
      transform: scale(0.96);
    }}

    .btn-light {{
      background: rgba(255, 255, 255, 0.12);
      color: #FFFFFF;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border-color: rgba(255, 255, 255, 0.2);
    }}

    .btn-primary {{
      background: var(--primary);
      color: #FFFFFF;
      box-shadow: 0 4px 12px var(--primary-glow);
    }}

    .btn-share {{
      background: #25D366; /* LINE / Share green */
      color: #FFFFFF;
    }}

    .btn-icon {{
      width: 38px;
      height: 38px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
    }}

    .hero-stats {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 0.65rem;
    }}

    .stat-card {{
      background: rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: var(--radius-sm);
      padding: 0.65rem 0.85rem;
      display: flex;
      flex-direction: column;
    }}

    .stat-card .label {{
      font-size: 0.72rem;
      color: #94A3B8;
    }}

    .stat-card .val {{
      font-size: 1.35rem;
      font-weight: 800;
      color: #FFFFFF;
      font-family: var(--font-display);
    }}

    /* Compact Controls Bar (Slim on mobile) */
    .controls-wrapper {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 90;
      box-shadow: var(--shadow-sm);
    }}

    .controls-container {{
      padding: 0.65rem 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}

    .controls-row-1 {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}

    .search-box {{
      position: relative;
      flex: 1;
    }}

    .search-box input {{
      width: 100%;
      padding: 0.55rem 1rem 0.55rem 2.2rem;
      font-size: 0.88rem;
      border: 1.5px solid var(--border-color);
      border-radius: var(--radius-full);
      background: var(--bg-main);
      color: var(--text-main);
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}

    .search-box input:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 3px var(--primary-glow);
    }}

    .search-box svg {{
      position: absolute;
      left: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }}

    .btn-filter-toggle {{
      display: flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.52rem 0.85rem;
      font-size: 0.82rem;
      font-weight: 600;
      border-radius: var(--radius-full);
      border: 1.5px solid var(--border-color);
      background: var(--bg-main);
      color: var(--text-main);
      cursor: pointer;
      flex-shrink: 0;
    }}

    .btn-filter-toggle.has-filter {{
      border-color: var(--primary);
      color: var(--primary);
      background: var(--primary-light);
    }}

    .view-switchers {{
      display: flex;
      background: var(--bg-main);
      padding: 3px;
      border-radius: var(--radius-full);
      border: 1px solid var(--border-color);
      gap: 2px;
      flex-shrink: 0;
    }}

    .view-btn {{
      padding: 0.35rem 0.75rem;
      font-size: 0.82rem;
      font-weight: 600;
      border: none;
      background: transparent;
      color: var(--text-muted);
      border-radius: var(--radius-full);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.3rem;
      transition: all 0.2s;
    }}

    .view-btn.active {{
      background: var(--bg-card);
      color: var(--primary);
      box-shadow: var(--shadow-sm);
    }}

    .quick-strip-scroll {{
      display: flex;
      overflow-x: auto;
      gap: 0.4rem;
      align-items: center;
      padding-bottom: 2px;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
    }}

    .quick-strip-scroll::-webkit-scrollbar {{
      display: none;
    }}

    .strip-divider {{
      width: 1px;
      height: 18px;
      background: var(--border-color);
      margin: 0 0.15rem;
      flex-shrink: 0;
    }}

    .pill {{
      padding: 0.32rem 0.7rem;
      font-size: 0.78rem;
      font-weight: 600;
      border-radius: var(--radius-full);
      border: 1px solid var(--border-color);
      background: var(--bg-main);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;
      user-select: none;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      white-space: nowrap;
      flex-shrink: 0;
    }}

    .pill:active {{
      transform: scale(0.95);
    }}

    .pill.active {{
      background: var(--primary);
      color: #FFFFFF;
      border-color: var(--primary);
      box-shadow: 0 2px 6px var(--primary-glow);
    }}

    .pill-count {{
      background: rgba(0,0,0,0.08);
      padding: 1px 5px;
      border-radius: 10px;
      font-size: 0.68rem;
    }}

    .pill.active .pill-count {{
      background: rgba(255,255,255,0.25);
    }}

    .desktop-filters-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      align-items: center;
      font-size: 0.8rem;
    }}

    /* Main Content Area */
    main.main-content {{
      padding: 1.25rem 1.25rem;
      flex: 1;
    }}

    .filter-summary {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.85rem;
      color: var(--text-muted);
      font-size: 0.85rem;
    }}

    .filter-summary strong {{
      color: var(--text-main);
      font-weight: 700;
    }}

    /* Card Grid View */
    .events-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1.25rem;
    }}

    .event-card {{
      background: var(--bg-card);
      border-radius: var(--radius-md);
      border: 1px solid var(--border-color);
      overflow: hidden;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
    }}

    .event-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
      border-color: var(--primary);
    }}

    .event-card:active {{
      transform: scale(0.985);
    }}

    .card-cover {{
      height: 165px;
      width: 100%;
      background: #E2E8F0;
      position: relative;
      overflow: hidden;
    }}

    .card-cover img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}

    .card-badges-top {{
      position: absolute;
      top: 0.6rem;
      left: 0.6rem;
      display: flex;
      gap: 0.35rem;
      flex-wrap: wrap;
    }}

    .badge {{
      padding: 0.2rem 0.55rem;
      border-radius: var(--radius-full);
      font-size: 0.7rem;
      font-weight: 700;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      display: inline-flex;
      align-items: center;
      gap: 0.2rem;
    }}

    .badge-city {{
      background: rgba(30, 41, 59, 0.88);
      color: #FFFFFF;
    }}

    .badge-category {{
      background: var(--primary);
      color: #FFFFFF;
    }}

    .badge-platform {{
      position: absolute;
      top: 0.6rem;
      right: 0.6rem;
      background: rgba(255, 255, 255, 0.95);
      color: #1E293B;
      font-size: 0.68rem;
      box-shadow: var(--shadow-sm);
    }}

    .card-body {{
      padding: 1rem;
      display: flex;
      flex-direction: column;
      flex: 1;
    }}

    .card-date {{
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.3rem;
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }}

    .card-title {{
      font-size: 1.05rem;
      font-weight: 700;
      line-height: 1.35;
      margin-bottom: 0.4rem;
      color: var(--text-main);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .card-desc {{
      font-size: 0.82rem;
      color: var(--text-muted);
      line-height: 1.45;
      margin-bottom: 0.75rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .card-meta {{
      margin-top: auto;
      border-top: 1px solid var(--border-color);
      padding-top: 0.65rem;
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
      font-size: 0.78rem;
      color: var(--text-muted);
    }}

    .meta-item {{
      display: flex;
      align-items: center;
      gap: 0.35rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .meta-item svg {{
      flex-shrink: 0;
      color: var(--text-light);
    }}

    .card-footer {{
      padding: 0.65rem 1rem;
      background: var(--bg-main);
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .card-price {{
      font-weight: 700;
      font-size: 0.82rem;
      color: var(--text-main);
    }}

    .card-price.free {{
      color: var(--accent-tea);
    }}

    /* Agenda / List View */
    .agenda-list {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}

    .agenda-group-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 1rem;
      font-weight: 800;
      color: var(--text-main);
      padding-bottom: 0.35rem;
      border-bottom: 2px solid var(--primary);
    }}

    .agenda-item {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 0.85rem 1rem;
      display: grid;
      grid-template-columns: 110px 1fr auto;
      gap: 1rem;
      align-items: center;
      box-shadow: var(--shadow-sm);
      cursor: pointer;
    }}

    .agenda-time-box {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: var(--primary-light);
      color: var(--primary);
      border-radius: var(--radius-sm);
      padding: 0.55rem 0.4rem;
      text-align: center;
    }}

    .agenda-time-box .day-num {{
      font-size: 1.5rem;
      font-weight: 800;
      line-height: 1;
      font-family: var(--font-display);
    }}

    .agenda-time-box .month-name {{
      font-size: 0.72rem;
      font-weight: 700;
    }}

    .agenda-time-box .time-str {{
      font-size: 0.7rem;
      margin-top: 0.15rem;
      font-weight: 600;
    }}

    .agenda-content h3 {{
      font-size: 1rem;
      font-weight: 700;
      margin-bottom: 0.25rem;
      color: var(--text-main);
    }}

    .agenda-content-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.65rem;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 0.3rem;
    }}

    .agenda-actions {{
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      min-width: 110px;
    }}

    /* Calendar Grid View */
    .calendar-container {{
      background: var(--bg-card);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-color);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }}

    .cal-header {{
      padding: 0.85rem 1.15rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
    }}

    .cal-title {{
      font-size: 1.15rem;
      font-weight: 800;
      font-family: var(--font-display);
    }}

    .cal-nav {{
      display: flex;
      gap: 0.35rem;
    }}

    .cal-grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
    }}

    .cal-day-header {{
      padding: 0.55rem;
      text-align: center;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--text-muted);
      background: var(--bg-main);
      border-bottom: 1px solid var(--border-color);
    }}

    .cal-cell {{
      min-height: 85px;
      padding: 0.35rem;
      border-right: 1px solid var(--border-color);
      border-bottom: 1px solid var(--border-color);
      background: var(--bg-card);
      display: flex;
      flex-direction: column;
    }}

    .cal-cell:nth-child(7n) {{
      border-right: none;
    }}

    .cal-cell.other-month {{
      background: var(--bg-main);
      opacity: 0.4;
    }}

    .cal-cell.today {{
      background: rgba(200, 76, 50, 0.05);
    }}

    .cal-cell-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.25rem;
    }}

    .cal-date-num {{
      font-size: 0.78rem;
      font-weight: 700;
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
    }}

    .cal-cell.today .cal-date-num {{
      background: var(--primary);
      color: #FFFFFF;
    }}

    .cal-events-list {{
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      overflow-y: auto;
      max-height: 60px;
    }}

    .cal-event-pill {{
      font-size: 0.65rem;
      font-weight: 600;
      padding: 1px 4px;
      border-radius: 3px;
      background: var(--primary-light);
      color: var(--primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      cursor: pointer;
      border-left: 2px solid var(--primary);
    }}

    /* Mobile Bottom Navigation Bar */
    .ios-tab-bar {{
      display: none;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-top: 0.5px solid rgba(0, 0, 0, 0.15);
      z-index: 99;
      padding-bottom: max(6px, var(--sab));
    }}

    [data-theme="dark"] .ios-tab-bar {{
      background: rgba(15, 23, 42, 0.92);
      border-top: 0.5px solid rgba(255, 255, 255, 0.15);
    }}

    .ios-tab-bar-items {{
      display: flex;
      height: 52px;
      justify-content: space-around;
      align-items: center;
    }}

    .ios-tab-item {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex: 1;
      height: 100%;
      color: var(--text-muted);
      font-size: 0.68rem;
      font-weight: 600;
      text-decoration: none;
      border: none;
      background: transparent;
      cursor: pointer;
      gap: 2px;
    }}

    .ios-tab-item svg {{
      width: 20px;
      height: 20px;
      stroke-width: 2;
    }}

    .ios-tab-item.active {{
      color: var(--primary);
    }}

    /* Modals */
    .modal-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      opacity: 0;
      visibility: hidden;
      transition: all 0.25s ease;
    }}

    .modal-overlay.active {{
      opacity: 1;
      visibility: visible;
    }}

    .modal-dialog {{
      background: var(--bg-card);
      border-radius: var(--radius-lg);
      max-width: 650px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: var(--shadow-lg);
      position: relative;
      transform: translateY(20px);
      transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    .modal-overlay.active .modal-dialog {{
      transform: translateY(0);
    }}

    .modal-sheet-handle {{
      display: none;
      width: 36px;
      height: 5px;
      background: #CBD5E1;
      border-radius: 3px;
      margin: 8px auto 0;
    }}

    .modal-close {{
      position: absolute;
      top: 1rem;
      right: 1rem;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: rgba(0,0,0,0.5);
      color: #FFFFFF;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 10;
    }}

    .modal-hero-img {{
      height: 220px;
      width: 100%;
      background: #1E293B;
      position: relative;
    }}

    .modal-hero-img img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}

    .modal-content {{
      padding: 1.5rem;
    }}

    .modal-title {{
      font-size: 1.35rem;
      font-weight: 800;
      line-height: 1.35;
      margin: 0.75rem 0 0.85rem;
      color: var(--text-main);
    }}

    .modal-info-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
      background: var(--bg-main);
      padding: 1rem;
      border-radius: var(--radius-md);
      margin-bottom: 1.1rem;
    }}

    .info-row {{
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      font-size: 0.85rem;
    }}

    .info-row svg {{
      color: var(--primary);
      flex-shrink: 0;
      margin-top: 3px;
    }}

    .modal-desc {{
      font-size: 0.92rem;
      color: var(--text-main);
      line-height: 1.65;
      margin-bottom: 1.5rem;
      white-space: pre-wrap;
    }}

    .modal-actions-bar {{
      display: flex;
      gap: 0.65rem;
      flex-wrap: wrap;
      border-top: 1px solid var(--border-color);
      padding-top: 1.1rem;
    }}

    .empty-state {{
      text-align: center;
      padding: 3.5rem 1.25rem;
      color: var(--text-muted);
    }}

    footer {{
      background: var(--bg-card);
      border-top: 1px solid var(--border-color);
      padding: 2rem 1.25rem;
      text-align: center;
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-top: auto;
    }}

    /* =========================================================================
       RESPONSIVE MOBILE VIEW (iPhone & Android)
       ========================================================================= */
    @media (max-width: 768px) {{
      header.hero-header {{
        padding: calc(var(--sat) + 0.5rem) 1rem 0.5rem;
        box-shadow: none;
      }}
      .header-top {{
        margin-bottom: 0;
      }}
      .brand-titles h1 {{
        font-size: 1.15rem;
      }}
      .brand-titles p {{
        display: none;
      }}
      .brand-icon {{
        width: 32px;
        height: 32px;
        font-size: 1rem;
      }}
      .hero-stats {{
        display: none;
      }}
      .header-actions {{
        display: none;
      }}

      .desktop-filters-row {{
        display: none !important;
      }}
      .view-switchers {{
        display: none;
      }}

      .controls-container {{
        padding: 0.45rem 0.85rem;
        gap: 0.35rem;
      }}
      .search-box input {{
        padding: 0.45rem 0.85rem 0.45rem 2rem;
        font-size: 0.85rem;
      }}

      body {{
        padding-bottom: calc(var(--sab) + 55px);
      }}
      main.main-content {{
        padding: 0.75rem 0.85rem;
      }}
      .events-grid {{
        grid-template-columns: 1fr;
        gap: 0.85rem;
      }}
      .card-cover {{
        height: 155px;
      }}
      .agenda-item {{
        grid-template-columns: 1fr;
        gap: 0.65rem;
        padding: 0.75rem;
      }}
      .agenda-time-box {{
        flex-direction: row;
        justify-content: flex-start;
        gap: 0.65rem;
        padding: 0.4rem 0.75rem;
      }}
      .agenda-time-box .day-num {{
        font-size: 1.25rem;
      }}
      .agenda-actions {{
        flex-direction: row;
        width: 100%;
      }}
      .agenda-actions .btn {{
        flex: 1;
        justify-content: center;
      }}
      .cal-cell {{
        min-height: 55px;
        padding: 0.15rem;
      }}
      .cal-event-pill {{
        font-size: 0.6rem;
      }}

      .ios-tab-bar {{
        display: block;
      }}

      .modal-overlay {{
        align-items: flex-end;
        padding: 0;
      }}
      .modal-dialog {{
        border-radius: 20px 20px 0 0;
        max-height: 85vh;
        transform: translateY(100%);
        padding-bottom: var(--sab);
      }}
      .modal-sheet-handle {{
        display: block;
      }}
      .modal-actions-bar {{
        flex-direction: column;
      }}
      .modal-actions-bar .btn {{
        width: 100%;
        justify-content: center;
      }}
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header class="hero-header">
    <div class="container">
      <div class="header-top">
        <div class="brand">
          <div class="brand-icon">🎭</div>
          <div class="brand-titles">
            <h1>北北桃台語活動日曆</h1>
            <p>臺北市・新北市・桃園市 ｜ 舞台劇・表演・故事・繪本・體驗・導覽</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-light" onclick="exportCalendarFile()">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            下載 iCal (.ics)
          </button>
          <button class="btn btn-light" onclick="openSyncModal()">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24"><path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/></svg>
            手機/日曆串接
          </button>
          <button class="btn btn-light btn-icon" onclick="toggleTheme()" title="切換深淺模式">
            🌓
          </button>
        </div>
      </div>

      <!-- Desktop Hero Stats (Hidden on mobile) -->
      <div class="hero-stats">
        <div class="stat-card">
          <span class="label">活動總數</span>
          <span class="val" id="statTotal">--</span>
        </div>
        <div class="stat-card">
          <span class="label">臺北市</span>
          <span class="val" id="statTaipei">--</span>
        </div>
        <div class="stat-card">
          <span class="label">新北市</span>
          <span class="val" id="statNewTaipei">--</span>
        </div>
        <div class="stat-card">
          <span class="label">桃園市</span>
          <span class="val" id="statTaoyuan">--</span>
        </div>
        <div class="stat-card">
          <span class="label">免費活動</span>
          <span class="val" id="statFree">--</span>
        </div>
      </div>
    </div>
  </header>

  <div class="container" style="padding:0.75rem 1rem;color:var(--text-muted);font-size:0.85rem;">僅列已核對官方公告的場次；未核實資料暫不刊登。費用未公告時不列入免費或付費篩選。日期與時間均為臺灣時間。 <a href="#guideResources" style="color:var(--primary)">台語導覽、展覽與閱讀資訊 ↓</a></div>

  <!-- CONTROLS & FILTERS -->
  <div class="controls-wrapper">
    <div class="container controls-container">
      
      <div class="controls-row-1">
        <div class="search-box">
          <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" stroke-width="2"></circle><line x1="21" y1="21" x2="16.65" y2="16.65" stroke-width="2"></line></svg>
          <input type="text" id="searchInput" placeholder="搜尋劇名、故事屋、導覽、圖書館..." oninput="handleSearch(this.value)">
        </div>

        <button class="btn-filter-toggle" id="btnFilterSheet" onclick="openFilterSheet()">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" stroke-width="2"/></svg>
          <span id="filterBtnLabel">進階篩選</span>
        </button>

        <div class="view-switchers">
          <button class="view-btn active" data-view="grid" onclick="switchView('grid')">🗂️ 卡片</button>
          <button class="view-btn" data-view="agenda" onclick="switchView('agenda')">📋 清單</button>
          <button class="view-btn" data-view="calendar" onclick="switchView('calendar')">📅 月曆</button>
        </div>
      </div>

      <!-- Quick Strip for Mobile & Desktop -->
      <div class="quick-strip-scroll">
        <button class="pill active" data-filter-type="city" data-value="all" onclick="setCityFilter('all')">全部地區 <span class="pill-count" id="count-city-all"></span></button>
        <button class="pill" data-filter-type="city" data-value="臺北市" onclick="setCityFilter('臺北市')">🏛️ 臺北 <span class="pill-count" id="count-city-taipei"></span></button>
        <button class="pill" data-filter-type="city" data-value="新北市" onclick="setCityFilter('新北市')">🌊 新北 <span class="pill-count" id="count-city-newtaipei"></span></button>
        <button class="pill" data-filter-type="city" data-value="桃園市" onclick="setCityFilter('桃園市')">✈️ 桃園 <span class="pill-count" id="count-city-taoyuan"></span></button>
        
        <div class="strip-divider"></div>

        <button class="pill active" data-filter-type="category" data-value="all" onclick="setCategoryFilter('all')">全部類別</button>
        <button class="pill" data-filter-type="category" data-value="台語舞台劇" onclick="setCategoryFilter('台語舞台劇')">🎭 舞台劇</button>
        <button class="pill" data-filter-type="category" data-value="台語表演" onclick="setCategoryFilter('台語表演')">🎪 表演</button>
        <button class="pill" data-filter-type="category" data-value="台語故事" onclick="setCategoryFilter('台語故事')">📖 故事屋</button>
        <button class="pill" data-filter-type="category" data-value="台語繪本" onclick="setCategoryFilter('台語繪本')">📚 繪本</button>
        <button class="pill" data-filter-type="category" data-value="台語體驗" onclick="setCategoryFilter('台語體驗')">🎨 體驗</button>
        <button class="pill" data-filter-type="category" data-value="台語導覽" onclick="setCategoryFilter('台語導覽')">🚶 導覽</button>
      </div>

      <!-- Desktop Only Filter Row -->
      <div class="desktop-filters-row">
        <span style="color:var(--text-muted); font-weight:700;">來源：</span>
        <button class="pill active" data-filter-type="platform" data-value="all" onclick="setPlatformFilter('all')">全部來源</button>
        <button class="pill" data-filter-type="platform" data-value="美術館與博物館" onclick="setPlatformFilter('美術館與博物館')">🏛️ 美術館/博物館</button>
        <button class="pill" data-filter-type="platform" data-value="北北桃市府局處" onclick="setPlatformFilter('北北桃市府局處')">🏛️ 市府各局處</button>
        <button class="pill" data-filter-type="platform" data-value="李江却基金會" onclick="setPlatformFilter('李江却基金會')">📜 李江却</button>
        <button class="pill" data-filter-type="platform" data-value="樂暢親子共學" onclick="setPlatformFilter('樂暢親子共學')">🎈 樂暢共學</button>
        <button class="pill" data-filter-type="platform" data-value="北北桃市立圖書館" onclick="setPlatformFilter('北北桃市立圖書館')">📖 市立圖書館</button>
        <button class="pill" data-filter-type="platform" data-value="國立臺灣圖書館" onclick="setPlatformFilter('國立臺灣圖書館')">📚 國立臺灣圖書館</button>
        <button class="pill" data-filter-type="platform" data-value="OPENTIX 兩廳院" onclick="setPlatformFilter('OPENTIX 兩廳院')">🎭 兩廳院</button>
        <button class="pill" data-filter-type="platform" data-value="年代售票" onclick="setPlatformFilter('年代售票')">🎫 年代售票</button>
        <button class="pill" data-filter-type="platform" data-value="Accupass 活動通" onclick="setPlatformFilter('Accupass 活動通')">🎟️ Accupass</button>
        <button class="pill" data-filter-type="platform" data-value="Facebook" onclick="setPlatformFilter('Facebook')">📘 FB</button>
        <button class="pill" data-filter-type="platform" data-value="Instagram" onclick="setPlatformFilter('Instagram')">📸 IG</button>
        <button class="pill" data-filter-type="platform" data-value="Threads" onclick="setPlatformFilter('Threads')">🧵 Threads</button>
        
        <span style="color:var(--text-muted); font-weight:700; margin-left:0.5rem;">費用：</span>
        <button class="pill active" data-filter-type="price" data-value="all" onclick="setPriceFilter('all')">全部</button>
        <button class="pill" data-filter-type="price" data-value="free" onclick="setPriceFilter('free')">免費</button>
        <button class="pill" data-filter-type="price" data-value="paid" onclick="setPriceFilter('paid')">售票/付費</button>
      </div>

    </div>
  </div>

  <!-- MAIN EVENT DISPLAY -->
  <main class="main-content">
    <div class="container">
      <div class="filter-summary">
        <div>顯示 <strong id="visibleCount">0</strong> 場活動</div>
        <div id="activeFiltersSummary"></div>
      </div>

      <!-- VIEW 1: Grid Cards -->
      <div id="viewGrid" class="events-grid"></div>

      <!-- VIEW 2: Agenda List -->
      <div id="viewAgenda" class="agenda-list" style="display: none;"></div>

      <!-- VIEW 3: Interactive Month Calendar -->
      <div id="viewCalendar" class="calendar-container" style="display: none;">
        <div class="cal-header">
          <div class="cal-title" id="calCurrentMonthLabel">2026年 9月</div>
          <div class="cal-nav">
            <button class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color); padding:0.3rem 0.6rem;" onclick="prevMonth()">◀</button>
            <button class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color); padding:0.3rem 0.7rem;" onclick="goToToday()">今天</button>
            <button class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color); padding:0.3rem 0.6rem;" onclick="nextMonth()">▶</button>
          </div>
        </div>
        <div class="cal-grid" id="calGridHeader">
          <div class="cal-day-header">日</div>
          <div class="cal-day-header">一</div>
          <div class="cal-day-header">二</div>
          <div class="cal-day-header">三</div>
          <div class="cal-day-header">四</div>
          <div class="cal-day-header">五</div>
          <div class="cal-day-header">六</div>
        </div>
        <div class="cal-grid" id="calGridDays"></div>
      </div>
    </div>
  </main>
  {resource_section}

  <!-- MOBILE NATIVE BOTTOM TAB BAR (Android & iPhone) -->
  <nav class="ios-tab-bar">
    <div class="ios-tab-bar-items">
      <button class="ios-tab-item active" data-tab="grid" onclick="switchViewMobile('grid')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></svg>
        <span>活動探索</span>
      </button>
      <button class="ios-tab-item" data-tab="agenda" onclick="switchViewMobile('agenda')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
        <span>時間排程</span>
      </button>
      <button class="ios-tab-item" data-tab="calendar" onclick="switchViewMobile('calendar')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>月曆檢視</span>
      </button>
      <button class="ios-tab-item" onclick="openFilterSheet()">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" stroke-width="2"/></svg>
        <span>篩選</span>
      </button>
      <button class="ios-tab-item" onclick="openSyncModal()">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
        <span>同步/設定</span>
      </button>
    </div>
  </nav>

  <!-- MOBILE FILTER BOTTOM SHEET -->
  <div class="modal-overlay" id="filterSheetModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog" style="max-width: 500px;">
      <div class="modal-sheet-handle"></div>
      <button class="modal-close" onclick="closeFilterSheet()">✕</button>
      <div class="modal-content">
        <h3 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 1rem; color:var(--text-main);">🔍 進階活動篩選</h3>

        <div style="margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.85rem; font-weight: 700; color:var(--text-muted); margin-bottom: 0.5rem;">來源平台：</h4>
          <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
            <button class="pill active" data-filter-type="platform" data-value="all" onclick="setPlatformFilter('all')">全部來源</button>
            <button class="pill" data-filter-type="platform" data-value="美術館與博物館" onclick="setPlatformFilter('美術館與博物館')">🏛️ 美術館與博物館導覽</button>
            <button class="pill" data-filter-type="platform" data-value="北北桃市府局處" onclick="setPlatformFilter('北北桃市府局處')">🏛️ 臺北/新北/桃園市府各局處</button>
            <button class="pill" data-filter-type="platform" data-value="李江却基金會" onclick="setPlatformFilter('李江却基金會')">📜 李江却基金會</button>
            <button class="pill" data-filter-type="platform" data-value="樂暢親子共學" onclick="setPlatformFilter('樂暢親子共學')">🎈 樂暢共學</button>
            <button class="pill" data-filter-type="platform" data-value="北北桃市立圖書館" onclick="setPlatformFilter('北北桃市立圖書館')">📖 市立圖書館</button>
        <button class="pill" data-filter-type="platform" data-value="國立臺灣圖書館" onclick="setPlatformFilter('國立臺灣圖書館')">📚 國立臺灣圖書館</button>
            <button class="pill" data-filter-type="platform" data-value="OPENTIX 兩廳院" onclick="setPlatformFilter('OPENTIX 兩廳院')">🎭 兩廳院 OPENTIX</button>
            <button class="pill" data-filter-type="platform" data-value="年代售票" onclick="setPlatformFilter('年代售票')">🎫 年代售票</button>
            <button class="pill" data-filter-type="platform" data-value="Accupass 活動通" onclick="setPlatformFilter('Accupass 活動通')">🎟️ Accupass</button>
            <button class="pill" data-filter-type="platform" data-value="Facebook" onclick="setPlatformFilter('Facebook')">📘 Facebook</button>
            <button class="pill" data-filter-type="platform" data-value="Instagram" onclick="setPlatformFilter('Instagram')">📸 Instagram</button>
            <button class="pill" data-filter-type="platform" data-value="Threads" onclick="setPlatformFilter('Threads')">🧵 Threads</button>
            <button class="pill" data-filter-type="platform" data-value="Google 日曆" onclick="setPlatformFilter('Google 日曆')">📅 Google 日曆</button>
          </div>
        </div>

        <div style="margin-bottom: 1.5rem;">
          <h4 style="font-size: 0.85rem; font-weight: 700; color:var(--text-muted); margin-bottom: 0.5rem;">費用條件：</h4>
          <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
            <button class="pill active" data-filter-type="price" data-value="all" onclick="setPriceFilter('all')">全部費用</button>
            <button class="pill" data-filter-type="price" data-value="free" onclick="setPriceFilter('free')">免費入場</button>
            <button class="pill" data-filter-type="price" data-value="paid" onclick="setPriceFilter('paid')">售票 / 付費活動</button>
          </div>
        </div>

        <button class="btn btn-primary" onclick="closeFilterSheet()" style="width: 100%; justify-content: center; padding: 0.75rem;">
          套用篩選
        </button>
      </div>
    </div>
  </div>

  <!-- EVENT DETAIL MODAL (Android & iPhone Bottom Sheet) -->
  <div class="modal-overlay" id="eventModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog">
      <div class="modal-sheet-handle"></div>
      <button class="modal-close" onclick="closeModal()">✕</button>
      <div class="modal-hero-img">
        <img id="modalImg" src="" alt="活動海報">
      </div>
      <div class="modal-content">
        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
          <span class="badge badge-city" id="modalCity"></span>
          <span class="badge badge-category" id="modalCategory"></span>
          <span class="badge" style="background:var(--secondary); color:#fff;" id="modalPlatform"></span>
        </div>
        <h2 class="modal-title" id="modalTitle"></h2>

        <div class="modal-info-grid">
          <div class="info-row">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
            <div>
              <strong style="color:var(--text-main);">時間：</strong>
              <div id="modalTime" style="color:var(--text-muted);"></div>
            </div>
          </div>
          <div class="info-row">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
            <div>
              <strong style="color:var(--text-main);">場地/地址：</strong>
              <div id="modalVenue" style="color:var(--text-muted);"></div>
            </div>
          </div>
          <div class="info-row">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
            <div>
              <strong style="color:var(--text-main);">主辦單位：</strong>
              <div id="modalOrganizer" style="color:var(--text-muted);"></div>
            </div>
          </div>
          <div class="info-row">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41 0-.55-.23-1.06-.59-1.42zM5.5 7C4.67 7 4 6.33 4 5.5S4.67 4 5.5 4 7 4.67 7 5.5 6.33 7 5.5 7z"/></svg>
            <div>
              <strong style="color:var(--text-main);">票價/收費：</strong>
              <div id="modalPrice" style="color:var(--text-muted);"></div>
            </div>
          </div>
        </div>

        <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.4rem; color:var(--text-main);">活動內容介紹</h4>
        <div class="modal-desc" id="modalDesc"></div>

        <div class="modal-actions-bar">
          <a id="modalTicketLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="padding:0.75rem 1.25rem; font-size:0.92rem;">
            🌐 前往主辦/官方網站 ↗
          </a>
          <a id="modalGoogleSearchLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color); font-weight:600;">
            🔍 Google 搜尋此活動詳情 ↗
          </a>
          <!-- Dynamic Calendar CTA (Auto-adapted for Android Google Calendar vs iPhone Apple Calendar) -->
          <a id="modalGCalLink" href="#" target="_blank" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            📅 加到 Google 日曆 (Android 推薦)
          </a>
          <button id="modalSingleIcsBtn" onclick="downloadSingleIcs()" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            🍏 加到 Apple 日曆 (.ics)
          </button>
          <button id="modalShareBtn" onclick="shareCurrentActivity()" class="btn btn-light btn-share" style="border:none;">
            📤 分享到 LINE / 社群
          </button>
          <a id="modalMapLink" href="#" target="_blank" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            🗺️ Google 地圖導航
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- SYNC & SETTINGS MODAL -->
  <div class="modal-overlay" id="syncModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog" style="max-width: 550px;">
      <div class="modal-sheet-handle"></div>
      <button class="modal-close" onclick="closeSyncModal()">✕</button>
      <div class="modal-content">
        <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 0.5rem; color:var(--text-main);">📱 同步至 Android / iPhone 行事曆</h2>
        <p style="font-size: 0.88rem; color:var(--text-muted); margin-bottom: 1rem;">
          無論使用 Android 手機或 iPhone，皆可無縫同步日曆與安裝 App：
        </p>

        <!-- Android Section -->
        <div style="background:var(--bg-main); border-radius:var(--radius-md); padding:0.9rem; margin-bottom:1rem; font-size:0.85rem;">
          <h4 style="font-weight:700; color:var(--text-main); margin-bottom:0.35rem;">🤖 Android 手機 (Samsung / Pixel 等)</h4>
          <p style="color:var(--text-muted); margin-bottom:0.5rem;">
            1. <strong>加到 Google 日曆</strong>：任選活動點擊「加到 Google 日曆」，Android 系統會直接自動喚醒內建 Google Calendar App。<br>
            2. <strong>安裝為手機 App</strong>：在 Chrome 瀏覽器點擊右上角三點選單 ➔ <strong>「安裝應用程式」</strong> 或 <strong>「新增至主螢幕」</strong>，即可全螢幕使用！
          </p>
          <button class="btn btn-primary" onclick="exportCalendarFile()">📥 下載日曆檔 taigi_activities.ics</button>
        </div>

        <!-- iPhone Section -->
        <div style="background:var(--bg-main); border-radius:var(--radius-md); padding:0.9rem; margin-bottom:1rem; font-size:0.85rem;">
          <h4 style="font-weight:700; color:var(--text-main); margin-bottom:0.35rem;">🍏 iPhone 手機</h4>
          <p style="color:var(--text-muted);">
            在 Safari 點擊分享按鈕 ➔ <strong>「加入主畫面」</strong> 即可當作原生 App 使用。點擊「加到 Apple 日曆」可直接匯入 iPhone 行事曆。
          </p>
        </div>

        <div style="background:var(--bg-main); border-radius:var(--radius-md); padding:0.9rem; font-size:0.85rem;">
          <h4 style="font-weight:700; color:var(--text-main); margin-bottom:0.35rem;">🌓 主題切換</h4>
          <button class="btn btn-light" onclick="toggleTheme();" style="color:var(--text-main); border-color:var(--border-color); margin-top:0.25rem;">切換 深色 / 淺色 模式</button>
        </div>
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer>
    <div class="container">
      <p><strong>北北桃台語活動日曆 (Taigi Activities Hub)</strong></p>
      <p style="margin-top: 0.35rem; font-size: 0.78rem;">
        本頁僅收錄已核對官方公告的場次，不代表完整活動清單。各地收錄數以已核實資料為準；出發前請再次查看官方公告。
      </p>
      <p style="margin-top: 0.4rem; font-size: 0.75rem; color: var(--text-light);">
        頁面建置：{datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}（臺北時間；不代表重新核實） ｜ 咱做伙來講台語！
      </p>
    </div>
  </footer>

  <!-- EMBEDDED ACTIVITIES DATA -->
  <script>
    const ACTIVITIES_DATA = {activities_json};
  </script>

  <!-- APPLICATION JAVASCRIPT LOGIC -->
  <script>
    let currentView = 'grid';
    let currentCity = 'all';
    let currentCategory = 'all';
    let currentPlatform = 'all';
    let currentPrice = 'all';
    let searchQuery = '';
    let selectedActivity = null;
    let calDate = new Date();

    document.addEventListener('DOMContentLoaded', () => {{
      initTheme();
      adaptToDeviceOS();
      computeStats();
      renderAll();
    }});

    function adaptToDeviceOS() {{
      const isAndroid = /android/i.test(navigator.userAgent);
      if (isAndroid) {{
        // On Android, highlight Google Calendar as default
        const gcalBtn = document.getElementById('modalGCalLink');
        if (gcalBtn) {{
          gcalBtn.classList.remove('btn-light');
          gcalBtn.classList.add('btn-primary');
          gcalBtn.innerText = '📅 一鍵加到 Google 日曆 (Android 推薦)';
        }}
      }}
    }}

    function initTheme() {{
      const saved = localStorage.getItem('taigi_theme') || 'light';
      document.documentElement.setAttribute('data-theme', saved);
    }}

    function toggleTheme() {{
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('taigi_theme', next);
    }}

    function switchView(viewName) {{
      currentView = viewName;
      document.querySelectorAll('.view-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.view === viewName);
      }});
      document.querySelectorAll('.ios-tab-item').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.tab === viewName);
      }});

      document.getElementById('viewGrid').style.display = viewName === 'grid' ? 'grid' : 'none';
      document.getElementById('viewAgenda').style.display = viewName === 'agenda' ? 'flex' : 'none';
      document.getElementById('viewCalendar').style.display = viewName === 'calendar' ? 'block' : 'none';

      if (viewName === 'calendar') {{
        renderCalendar();
      }}
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function switchViewMobile(viewName) {{
      switchView(viewName);
    }}

    function setCityFilter(city) {{
      currentCity = city;
      updatePills('city', city);
      renderAll();
    }}

    function setCategoryFilter(category) {{
      currentCategory = category;
      updatePills('category', category);
      renderAll();
    }}

    function setPlatformFilter(platform) {{
      currentPlatform = platform;
      updatePills('platform', platform);
      updateFilterButtonState();
      renderAll();
    }}

    function setPriceFilter(price) {{
      currentPrice = price;
      updatePills('price', price);
      updateFilterButtonState();
      renderAll();
    }}

    function updatePills(filterType, val) {{
      document.querySelectorAll(`button[data-filter-type="${{filterType}}"]`).forEach(p => {{
        p.classList.toggle('active', p.dataset.value === val);
      }});
    }}

    function updateFilterButtonState() {{
      const hasCustom = (currentPlatform !== 'all' || currentPrice !== 'all');
      const btn = document.getElementById('btnFilterSheet');
      btn.classList.toggle('has-filter', hasCustom);
      document.getElementById('filterBtnLabel').innerText = hasCustom ? '已篩選 ⚙️' : '進階篩選';
    }}

    function handleSearch(val) {{
      searchQuery = val.trim().toLowerCase();
      renderAll();
    }}

    function openFilterSheet() {{
      document.getElementById('filterSheetModal').classList.add('active');
      document.body.style.overflow = 'hidden';
    }}

    function closeFilterSheet() {{
      document.getElementById('filterSheetModal').classList.remove('active');
      document.body.style.overflow = '';
    }}

    function getFilteredActivities() {{
      return ACTIVITIES_DATA.filter(act => {{
        if (currentCity !== 'all' && act.city !== currentCity) return false;
        if (currentCategory !== 'all' && act.category !== currentCategory) return false;
        if (currentPlatform !== 'all' && act.source_platform !== currentPlatform) return false;
        if (currentPrice === 'free' && act.is_free !== true) return false;
        if (currentPrice === 'paid' && act.is_free !== false) return false;
        if (searchQuery) {{
          const targetStr = `${{act.title}} ${{act.description}} ${{act.venue}} ${{act.address}} ${{act.organizer}} ${{act.tags.join(' ')}}`.toLowerCase();
          if (!targetStr.includes(searchQuery)) return false;
        }}
        return true;
      }});
    }}

    function computeStats() {{
      const total = ACTIVITIES_DATA.length;
      const taipei = ACTIVITIES_DATA.filter(a => a.city === '臺北市').length;
      const newTaipei = ACTIVITIES_DATA.filter(a => a.city === '新北市').length;
      const taoyuan = ACTIVITIES_DATA.filter(a => a.city === '桃園市').length;
      const free = ACTIVITIES_DATA.filter(a => a.is_free === true).length;

      document.getElementById('statTotal').innerText = total;
      document.getElementById('statTaipei').innerText = taipei;
      document.getElementById('statNewTaipei').innerText = newTaipei;
      document.getElementById('statTaoyuan').innerText = taoyuan;
      document.getElementById('statFree').innerText = free;

      document.getElementById('count-city-all').innerText = total;
      document.getElementById('count-city-taipei').innerText = taipei;
      document.getElementById('count-city-newtaipei').innerText = newTaipei;
      document.getElementById('count-city-taoyuan').innerText = taoyuan;
    }}

    function renderAll() {{
      const filtered = getFilteredActivities();
      document.getElementById('visibleCount').innerText = filtered.length;

      renderGrid(filtered);
      renderAgenda(filtered);
      if (currentView === 'calendar') {{
        renderCalendar();
      }}
    }}

    function formatDateDisplay(isoStr) {{
      if (!isoStr) return '時間未公告';
      return new Intl.DateTimeFormat('zh-TW', {{ timeZone: 'Asia/Taipei', year: 'numeric', month: 'numeric', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }}).format(new Date(isoStr));
    }}

    function renderGrid(events) {{
      const container = document.getElementById('viewGrid');
      if (events.length === 0) {{
        container.innerHTML = `
          <div class="empty-state" style="grid-column: 1/-1;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="44" height="44" style="margin-bottom:0.75rem;color:var(--text-light);"><circle cx="12" cy="12" r="10" stroke-width="2"/><line x1="8" y1="15" x2="16" y2="15" stroke-width="2"/><line x1="9" y1="9" x2="9.01" y2="9" stroke-width="2"/><line x1="15" y1="9" x2="15.01" y2="9" stroke-width="2"/></svg>
            <h3>查無符合條件的台語活動</h3>
            <p style="font-size:0.85rem;">此條件目前沒有已核實場次，不代表當地沒有活動。可調整篩選條件。</p>
          </div>
        `;
        return;
      }}

      container.innerHTML = events.map(act => {{
        const cover = act.cover_image;
        return `
          <div class="event-card" onclick="openModal('${{act.id}}')">
            <div class="card-cover">
              ${{cover ? `<img src="${{cover}}" alt="官方活動圖片" loading="lazy">` : '<div style="height:100%;display:flex;align-items:center;justify-content:center;background:var(--secondary-light);color:var(--secondary);font-weight:700;">台語活動・官方公告</div>'}}
              <div class="card-badges-top">
                <span class="badge badge-city">📍 ${{act.city}}</span>
                <span class="badge badge-category">${{act.category}}</span>
              </div>
              <span class="badge badge-platform">${{act.source_platform}}</span>
            </div>
            <div class="card-body">
              <div class="card-date">
                <svg width="13" height="13" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg>
                ${{formatDateDisplay(act.start_time)}}
              </div>
              <h3 class="card-title">${{act.title}}</h3>
              <p class="card-desc">${{act.description}}</p>
              <div class="card-meta">
                <div class="meta-item">
                  <svg width="13" height="13" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                  <span>${{act.venue}}</span>
                </div>
                <div class="meta-item">
                  <svg width="13" height="13" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
                  <span>${{act.organizer}}</span>
                </div>
              </div>
            </div>
            <div class="card-footer">
              <span class="card-price ${{act.is_free ? 'free' : ''}}">${{act.price_info}}</span>
              <button class="btn btn-primary" style="padding: 0.3rem 0.75rem; font-size:0.78rem;">查看詳情</button>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function renderAgenda(events) {{
      const container = document.getElementById('viewAgenda');
      if (events.length === 0) {{
        container.innerHTML = `
          <div class="empty-state">
            <h3>查無符合條件的台語活動</h3>
          </div>
        `;
        return;
      }}

      const groups = {{}};
      events.forEach(act => {{
        const dateKey = act.start_time.substring(0, 10);
        if (!groups[dateKey]) groups[dateKey] = [];
        groups[dateKey].push(act);
      }});

      let html = '';
      Object.keys(groups).sort().forEach(dateKey => {{
        const dt = new Date(dateKey);
        const days = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
        const groupLabel = `${{dt.getFullYear()}}年 ${{dt.getMonth() + 1}}月 ${{dt.getDate()}}日 (${{days[dt.getDay()]}})`;

        html += `
          <div>
            <div class="agenda-group-header">
              <span>📅 ${{groupLabel}}</span>
              <span style="font-size:0.75rem; font-weight:600; color:var(--text-muted);">${{groups[dateKey].length}} 場活動</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.75rem; margin-top:0.65rem;">
              ${{groups[dateKey].map(act => {{
                const d = new Date(act.start_time);
                const timeStr = d.toLocaleTimeString('zh-TW', {{ hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'Asia/Taipei' }});
                return `
                  <div class="agenda-item" onclick="openModal('${{act.id}}')">
                    <div class="agenda-time-box">
                      <div class="day-num">${{d.getDate()}}</div>
                      <div class="month-name">${{d.getMonth()+1}}月</div>
                      <div class="time-str">${{timeStr}}</div>
                    </div>
                    <div class="agenda-content">
                      <div style="display:flex; gap:0.3rem; margin-bottom:0.25rem; flex-wrap:wrap;">
                        <span class="badge badge-city">📍 ${{act.city}}</span>
                        <span class="badge badge-category">${{act.category}}</span>
                        <span class="badge" style="background:var(--secondary-light); color:var(--secondary);">${{act.source_platform}}</span>
                      </div>
                      <h3>${{act.title}}</h3>
                      <div class="agenda-content-meta">
                        <span>🏛️ ${{act.venue}}</span>
                        <span>🏷️ <strong style="color:var(--primary);">${{act.price_info}}</strong></span>
                      </div>
                      <p style="font-size:0.8rem; color:var(--text-muted); display:-webkit-box; -webkit-line-clamp:1; -webkit-box-orient:vertical; overflow:hidden;">${{act.description}}</p>
                    </div>
                    <div class="agenda-actions">
                      <button class="btn btn-primary" style="font-size:0.78rem; justify-content:center;">活動詳情</button>
                      <a href="${{act.gcal_url}}" target="_blank" class="btn btn-light" style="font-size:0.75rem; justify-content:center; color:var(--text-main); border-color:var(--border-color);" onclick="event.stopPropagation();">📅 加日曆</a>
                    </div>
                  </div>
                `;
              }}).join('')}}
            </div>
          </div>
        `;
      }});

      container.innerHTML = html;
    }}

    function renderCalendar() {{
      const year = calDate.getFullYear();
      const month = calDate.getMonth();
      document.getElementById('calCurrentMonthLabel').innerText = `${{year}}年 ${{month + 1}}月`;

      const firstDayIndex = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      const prevDaysInMonth = new Date(year, month, 0).getDate();

      const container = document.getElementById('calGridDays');
      let html = '';
      const filtered = getFilteredActivities();

      for (let i = firstDayIndex - 1; i >= 0; i--) {{
        const d = prevDaysInMonth - i;
        html += `<div class="cal-cell other-month"><div class="cal-cell-header"><span class="cal-date-num">${{d}}</span></div></div>`;
      }}

      const today = new Date();
      for (let day = 1; day <= daysInMonth; day++) {{
        const isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
        const dateStr = `${{year}}-${{String(month + 1).padStart(2, '0')}}-${{String(day).padStart(2, '0')}}`;
        const dayEvents = filtered.filter(a => a.start_time.startsWith(dateStr));

        html += `
          <div class="cal-cell ${{isToday ? 'today' : ''}}">
            <div class="cal-cell-header">
              <span class="cal-date-num">${{day}}</span>
              ${{dayEvents.length > 0 ? `<span style="font-size:0.65rem; font-weight:700; color:var(--primary);">${{dayEvents.length}}場</span>` : ''}}
            </div>
            <div class="cal-events-list">
              ${{dayEvents.map(ev => `
                <div class="cal-event-pill" onclick="openModal('${{ev.id}}')" title="${{ev.title}}">
                  ${{ev.title}}
                </div>
              `).join('')}}
            </div>
          </div>
        `;
      }}

      const totalCells = firstDayIndex + daysInMonth;
      const nextDays = (7 - (totalCells % 7)) % 7;
      for (let j = 1; j <= nextDays; j++) {{
        html += `<div class="cal-cell other-month"><div class="cal-cell-header"><span class="cal-date-num">${{j}}</span></div></div>`;
      }}

      container.innerHTML = html;
    }}

    function prevMonth() {{
      calDate.setMonth(calDate.getMonth() - 1);
      renderCalendar();
    }}

    function nextMonth() {{
      calDate.setMonth(calDate.getMonth() + 1);
      renderCalendar();
    }}

    function goToToday() {{
      calDate = new Date();
      renderCalendar();
    }}

    function openModal(actId) {{
      const act = ACTIVITIES_DATA.find(a => a.id === actId);
      if (!act) return;
      selectedActivity = act;

      document.getElementById('modalImg').src = act.cover_image || '';
      document.getElementById('modalImg').parentElement.style.display = act.cover_image ? '' : 'none';
      document.getElementById('modalCity').innerText = '📍 ' + act.city + (act.district ? ` (${{act.district}})` : '');
      document.getElementById('modalCategory').innerText = act.category;
      document.getElementById('modalPlatform').innerText = '🌐 ' + act.source_platform;
      document.getElementById('modalTitle').innerText = act.title;
      document.getElementById('modalTime').innerText = formatDateDisplay(act.start_time) + (act.end_time ? ' ～ ' + formatDateDisplay(act.end_time) : '（結束時間未公告）');
      document.getElementById('modalVenue').innerText = act.venue + (act.address ? ` (${{act.address}})` : '');
      document.getElementById('modalOrganizer').innerText = act.organizer;
      document.getElementById('modalPrice').innerText = act.price_info;
      document.getElementById('modalDesc').innerText = act.description + '\\n\\n官方資料核對：' + act.raw_metadata.verified_at.slice(0, 10) + '。出發前請再次確認官方最新公告。';

      const cleanTitle = act.title.replace(/[【】《》「」]/g, ' ').trim();
      const searchQuery = encodeURIComponent(`${{cleanTitle}} ${{act.organizer}} 台語 報名 售票`);
      const googleSearchUrl = `https://www.google.com/search?q=${{searchQuery}}`;

      const ticketBtn = document.getElementById('modalTicketLink');
      ticketBtn.href = act.source_url;
      ticketBtn.textContent = '🌐 查看官方活動公告／報名 ↗';

      document.getElementById('modalGoogleSearchLink').href = googleSearchUrl;
      document.getElementById('modalGoogleSearchLink').innerHTML = '🔍 Google 查詢本活動報名/購票 ↗';
      document.getElementById('modalGCalLink').href = act.gcal_url;
      document.getElementById('modalMapLink').href = `https://www.google.com/maps/search/?api=1&query=${{encodeURIComponent(act.venue + ' ' + act.address)}}`;

      document.getElementById('eventModal').classList.add('active');
      document.body.style.overflow = 'hidden';
    }}

    function closeModal() {{
      document.getElementById('eventModal').classList.remove('active');
      document.body.style.overflow = '';
      selectedActivity = null;
    }}

    function closeModalOnBackdrop(e) {{
      if (e.target.classList.contains('modal-overlay')) {{
        e.target.classList.remove('active');
        document.body.style.overflow = '';
      }}
    }}

    function openSyncModal() {{
      document.getElementById('syncModal').classList.add('active');
      document.body.style.overflow = 'hidden';
    }}

    function closeSyncModal() {{
      document.getElementById('syncModal').classList.remove('active');
      document.body.style.overflow = '';
    }}

    // Android & Mobile Share API
    function shareCurrentActivity() {{
      if (!selectedActivity) return;
      const act = selectedActivity;
      const shareData = {{
        title: act.title,
        text: `【${{act.category}}】${{act.title}}\\n時間：${{formatDateDisplay(act.start_time)}}\\n地點：${{act.venue}}\\n來做伙講台語！`,
        url: window.location.href
      }};

      if (navigator.share) {{
        navigator.share(shareData).catch(() => {{}});
      }} else {{
        // Fallback: Copy to clipboard
        navigator.clipboard.writeText(`${{shareData.title}}\\n${{shareData.url}}`);
        alert('活動資訊已複製到剪貼簿，可直接貼到 LINE 分享！');
      }}
    }}

    function saveCalendar(events, filename) {{
      const content = {calendar_header_json} + events.map(a => a.ics_event).join('') + 'END:VCALENDAR\\r\\n';
      const blob = new Blob([content], {{ type: 'text/calendar;charset=utf-8' }});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }}

    function exportCalendarFile() {{
      saveCalendar(getFilteredActivities(), 'taigi_activities.ics');
    }}

    function downloadSingleIcs() {{
      if (selectedActivity) saveCalendar([selectedActivity], selectedActivity.id + '.ics');
    }}
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
