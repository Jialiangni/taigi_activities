"""
Single-file HTML Builder for Taigi Activities Calendar
Compiles activities into a self-contained index.html with ultra-rich UI
"""
import json
import os
from typing import List
from datetime import datetime
from crawler.models import Activity
from crawler.sources.google_workspace import GoogleWorkspaceSync


def generate_single_html(activities: List[Activity], output_path: str = "index.html") -> str:
    activities_data = []
    g_sync = GoogleWorkspaceSync()

    for act in activities:
        d = act.to_dict()
        d["gcal_url"] = g_sync.generate_google_calendar_url(act)
        activities_data.append(d)

    activities_json = json.dumps(activities_data, ensure_ascii=False, indent=2)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>北北桃台語活動行事曆 | 臺北・新北・桃園 台語舞台劇/表演/故事/繪本/體驗/導覽</title>
  <meta name="description" content="全台最完整的北北桃台語活動行事曆！彙整臺北市、新北市、桃園市的台語舞台劇、表演、故事屋、台語繪本共讀、文化體驗、文史走讀導覽活動。整合李江却基金會、樂暢、市立圖書館、OPENTIX 兩廳院、年代售票、Accupass、FB、IG、Threads 與 Google 日曆。">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700;900&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  
  <style>
    :root {{
      --font-main: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-display: 'Outfit', 'Noto Sans TC', sans-serif;
      
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
      --primary: #C84C32; /* 磚紅 / 胭脂紅 */
      --primary-hover: #B03A22;
      --primary-light: #FDE8E4;
      --primary-glow: rgba(200, 76, 50, 0.18);
      
      --secondary: #1D3557; /* 台灣海島青藍 */
      --secondary-light: #EBF2F7;
      
      --accent-tea: #0D9488; /* 台灣茶綠 */
      --accent-tea-light: #CCFBF1;
      
      --accent-amber: #D97706; /* 陽光金橙 */
      --accent-amber-light: #FEF3C7;
      
      --accent-violet: #7C3AED; /* 藝文紫 */
      --accent-violet-light: #EDE9FE;

      --accent-blue: #2563EB;
      --accent-blue-light: #DBEAFE;
      
      --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
      --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
      --shadow-lg: 0 12px 32px rgba(0,0,0,0.12);
      --radius-sm: 8px;
      --radius-md: 12px;
      --radius-lg: 20px;
      --radius-full: 9999px;
    }}

    [data-theme="dark"] {{
      --bg-main: #0F172A;
      --bg-card: #1E293B;
      --bg-surface: #1E293B;
      --bg-hover: #334155;
      --border-color: #334155;
      --border-focus: #E05A47;
      
      --text-main: #F1F5F9;
      --text-muted: #94A3B8;
      --text-light: #64748B;
      
      --primary: #E05A47;
      --primary-hover: #F26E5C;
      --primary-light: rgba(224, 90, 71, 0.2);
      
      --secondary: #38BDF8;
      --secondary-light: rgba(56, 189, 248, 0.15);
      
      --accent-tea: #2DD4BF;
      --accent-tea-light: rgba(45, 212, 191, 0.15);
      
      --accent-amber: #FBBF24;
      --accent-amber-light: rgba(251, 191, 36, 0.15);
      
      --accent-violet: #A78BFA;
      --accent-violet-light: rgba(167, 139, 250, 0.15);
      
      --accent-blue: #60A5FA;
      --accent-blue-light: rgba(96, 165, 250, 0.15);
      
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
      --shadow-md: 0 4px 14px rgba(0,0,0,0.4);
      --shadow-lg: 0 12px 36px rgba(0,0,0,0.6);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: var(--font-main);
      background-color: var(--bg-main);
      color: var(--text-main);
      line-height: 1.6;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      transition: background-color 0.25s ease, color 0.25s ease;
    }}

    header.hero-header {{
      background: linear-gradient(135deg, #1E293B 0%, #0F172A 60%, #1D3557 100%);
      color: #FFFFFF;
      padding: 2.5rem 1.5rem 2rem;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }}

    header.hero-header::before {{
      content: "";
      position: absolute;
      top: -50%;
      right: -10%;
      width: 500px;
      height: 500px;
      background: radial-gradient(circle, rgba(200, 76, 50, 0.25) 0%, transparent 70%);
      pointer-events: none;
    }}

    .container {{
      max-width: 1320px;
      margin: 0 auto;
      width: 100%;
    }}

    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }}

    .brand-icon {{
      width: 48px;
      height: 48px;
      background: var(--primary);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      box-shadow: 0 4px 12px var(--primary-glow);
    }}

    .brand-titles h1 {{
      font-size: 1.65rem;
      font-weight: 800;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .brand-titles p {{
      font-size: 0.92rem;
      color: #CBD5E1;
      font-weight: 500;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.55rem 1.1rem;
      font-size: 0.88rem;
      font-weight: 600;
      border-radius: var(--radius-full);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      text-decoration: none;
    }}

    .btn-light {{
      background: rgba(255, 255, 255, 0.12);
      color: #FFFFFF;
      backdrop-filter: blur(8px);
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .btn-light:hover {{
      background: rgba(255, 255, 255, 0.22);
      transform: translateY(-1px);
    }}

    .btn-primary {{
      background: var(--primary);
      color: #FFFFFF;
      box-shadow: 0 4px 12px var(--primary-glow);
    }}
    .btn-primary:hover {{
      background: var(--primary-hover);
      transform: translateY(-1px);
    }}

    .btn-icon {{
      width: 40px;
      height: 40px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
    }}

    /* Stat Badges */
    .hero-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 0.75rem;
      margin-top: 1.25rem;
    }}

    .stat-card {{
      background: rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: var(--radius-md);
      padding: 0.75rem 1rem;
      display: flex;
      flex-direction: column;
    }}

    .stat-card .label {{
      font-size: 0.75rem;
      color: #94A3B8;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .stat-card .val {{
      font-size: 1.4rem;
      font-weight: 800;
      color: #FFFFFF;
      font-family: var(--font-display);
    }}

    /* Controls Bar */
    .controls-wrapper {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 90;
      box-shadow: var(--shadow-sm);
    }}

    .controls-container {{
      padding: 1rem 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }}

    .controls-row-1 {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .search-box {{
      position: relative;
      flex: 1;
      min-width: 280px;
      max-width: 500px;
    }}

    .search-box input {{
      width: 100%;
      padding: 0.65rem 1rem 0.65rem 2.6rem;
      font-size: 0.92rem;
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
      left: 0.9rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }}

    .view-switchers {{
      display: flex;
      background: var(--bg-main);
      padding: 4px;
      border-radius: var(--radius-full);
      border: 1px solid var(--border-color);
      gap: 2px;
    }}

    .view-btn {{
      padding: 0.4rem 0.9rem;
      font-size: 0.85rem;
      font-weight: 600;
      border: none;
      background: transparent;
      color: var(--text-muted);
      border-radius: var(--radius-full);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s;
    }}

    .view-btn.active {{
      background: var(--bg-card);
      color: var(--primary);
      box-shadow: var(--shadow-sm);
    }}

    /* Filters Pill Group */
    .filter-pills-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
    }}

    .filter-label {{
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-muted);
      margin-right: 0.25rem;
    }}

    .pill {{
      padding: 0.35rem 0.8rem;
      font-size: 0.82rem;
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
      gap: 0.3rem;
    }}

    .pill:hover {{
      border-color: var(--primary);
      color: var(--primary);
    }}

    .pill.active {{
      background: var(--primary);
      color: #FFFFFF;
      border-color: var(--primary);
      box-shadow: 0 2px 8px var(--primary-glow);
    }}

    .pill-count {{
      background: rgba(0,0,0,0.1);
      padding: 1px 6px;
      border-radius: 10px;
      font-size: 0.72rem;
      margin-left: 2px;
    }}

    .pill.active .pill-count {{
      background: rgba(255,255,255,0.25);
    }}

    /* Main Content Area */
    main.main-content {{
      padding: 2rem 1.5rem;
      flex: 1;
    }}

    .filter-summary {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      color: var(--text-muted);
      font-size: 0.9rem;
    }}

    .filter-summary strong {{
      color: var(--text-main);
      font-weight: 700;
    }}

    /* Card Grid View */
    .events-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 1.5rem;
    }}

    .event-card {{
      background: var(--bg-card);
      border-radius: var(--radius-md);
      border: 1px solid var(--border-color);
      overflow: hidden;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
      cursor: pointer;
    }}

    .event-card:hover {{
      transform: translateY(-4px);
      box-shadow: var(--shadow-md);
      border-color: var(--primary);
    }}

    .card-cover {{
      height: 180px;
      width: 100%;
      background: #E2E8F0;
      position: relative;
      overflow: hidden;
    }}

    .card-cover img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.4s ease;
    }}

    .event-card:hover .card-cover img {{
      transform: scale(1.05);
    }}

    .card-badges-top {{
      position: absolute;
      top: 0.75rem;
      left: 0.75rem;
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
    }}

    .badge {{
      padding: 0.25rem 0.65rem;
      border-radius: var(--radius-full);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.3px;
      backdrop-filter: blur(8px);
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
    }}

    .badge-city {{
      background: rgba(30, 41, 59, 0.85);
      color: #FFFFFF;
    }}

    .badge-category {{
      background: var(--primary);
      color: #FFFFFF;
    }}

    .badge-platform {{
      position: absolute;
      top: 0.75rem;
      right: 0.75rem;
      background: rgba(255, 255, 255, 0.95);
      color: #1E293B;
      font-size: 0.72rem;
      box-shadow: var(--shadow-sm);
    }}

    .card-body {{
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      flex: 1;
    }}

    .card-date {{
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.4rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }}

    .card-title {{
      font-size: 1.12rem;
      font-weight: 700;
      line-height: 1.4;
      margin-bottom: 0.6rem;
      color: var(--text-main);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .card-desc {{
      font-size: 0.88rem;
      color: var(--text-muted);
      line-height: 1.5;
      margin-bottom: 1rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .card-meta {{
      margin-top: auto;
      border-top: 1px solid var(--border-color);
      padding-top: 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      font-size: 0.82rem;
      color: var(--text-muted);
    }}

    .meta-item {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .meta-item svg {{
      flex-shrink: 0;
      color: var(--text-light);
    }}

    .card-footer {{
      padding: 0.85rem 1.25rem;
      background: var(--bg-main);
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .card-price {{
      font-weight: 700;
      font-size: 0.88rem;
      color: var(--text-main);
    }}

    .card-price.free {{
      color: var(--accent-tea);
    }}

    /* Agenda / List View */
    .agenda-list {{
      display: flex;
      flex-direction: column;
      gap: 1.75rem;
    }}

    .agenda-group-header {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--text-main);
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--primary);
    }}

    .agenda-item {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      display: grid;
      grid-template-columns: 140px 1fr auto;
      gap: 1.5rem;
      align-items: center;
      box-shadow: var(--shadow-sm);
      transition: all 0.2s;
      cursor: pointer;
    }}

    .agenda-item:hover {{
      border-color: var(--primary);
      box-shadow: var(--shadow-md);
      transform: translateX(4px);
    }}

    .agenda-time-box {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: var(--primary-light);
      color: var(--primary);
      border-radius: var(--radius-sm);
      padding: 0.75rem 0.5rem;
      text-align: center;
    }}

    .agenda-time-box .day-num {{
      font-size: 1.75rem;
      font-weight: 800;
      line-height: 1;
      font-family: var(--font-display);
    }}

    .agenda-time-box .month-name {{
      font-size: 0.8rem;
      font-weight: 700;
    }}

    .agenda-time-box .time-str {{
      font-size: 0.75rem;
      margin-top: 0.25rem;
      font-weight: 600;
    }}

    .agenda-content h3 {{
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 0.35rem;
      color: var(--text-main);
    }}

    .agenda-content-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.85rem;
      font-size: 0.84rem;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }}

    .agenda-actions {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      min-width: 140px;
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
      padding: 1.25rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
    }}

    .cal-title {{
      font-size: 1.35rem;
      font-weight: 800;
      font-family: var(--font-display);
    }}

    .cal-nav {{
      display: flex;
      gap: 0.5rem;
    }}

    .cal-grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
    }}

    .cal-day-header {{
      padding: 0.75rem;
      text-align: center;
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--text-muted);
      background: var(--bg-main);
      border-bottom: 1px solid var(--border-color);
    }}

    .cal-cell {{
      min-height: 110px;
      padding: 0.5rem;
      border-right: 1px solid var(--border-color);
      border-bottom: 1px solid var(--border-color);
      background: var(--bg-card);
      transition: background-color 0.15s;
      display: flex;
      flex-direction: column;
    }}

    .cal-cell:nth-child(7n) {{
      border-right: none;
    }}

    .cal-cell.other-month {{
      background: var(--bg-main);
      opacity: 0.45;
    }}

    .cal-cell.today {{
      background: rgba(200, 76, 50, 0.04);
    }}

    .cal-cell-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.4rem;
    }}

    .cal-date-num {{
      font-size: 0.85rem;
      font-weight: 700;
      width: 24px;
      height: 24px;
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
      gap: 0.25rem;
      overflow-y: auto;
      max-height: 85px;
    }}

    .cal-event-pill {{
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--primary-light);
      color: var(--primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      cursor: pointer;
      border-left: 3px solid var(--primary);
      transition: transform 0.1s;
    }}

    .cal-event-pill:hover {{
      transform: scale(1.02);
      box-shadow: var(--shadow-sm);
    }}

    /* Modal */
    .modal-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(6px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
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
      max-width: 680px;
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

    .modal-close {{
      position: absolute;
      top: 1rem;
      right: 1rem;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(0,0,0,0.5);
      color: #FFFFFF;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 10;
      transition: background 0.2s;
    }}

    .modal-close:hover {{
      background: rgba(0,0,0,0.8);
    }}

    .modal-hero-img {{
      height: 240px;
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
      padding: 1.75rem;
    }}

    .modal-title {{
      font-size: 1.45rem;
      font-weight: 800;
      line-height: 1.35;
      margin: 0.85rem 0 1rem;
      color: var(--text-main);
    }}

    .modal-info-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 0.85rem;
      background: var(--bg-main);
      padding: 1.2rem;
      border-radius: var(--radius-md);
      margin-bottom: 1.25rem;
    }}

    .info-row {{
      display: flex;
      align-items: flex-start;
      gap: 0.6rem;
      font-size: 0.88rem;
    }}

    .info-row svg {{
      color: var(--primary);
      flex-shrink: 0;
      margin-top: 3px;
    }}

    .modal-desc {{
      font-size: 0.95rem;
      color: var(--text-main);
      line-height: 1.7;
      margin-bottom: 1.75rem;
      white-space: pre-wrap;
    }}

    .modal-actions-bar {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      border-top: 1px solid var(--border-color);
      padding-top: 1.25rem;
    }}

    .empty-state {{
      text-align: center;
      padding: 4rem 1.5rem;
      color: var(--text-muted);
    }}

    footer {{
      background: var(--bg-card);
      border-top: 1px solid var(--border-color);
      padding: 2rem 1.5rem;
      text-align: center;
      font-size: 0.88rem;
      color: var(--text-muted);
      margin-top: auto;
    }}

    @media (max-width: 768px) {{
      header.hero-header {{
        padding: 1.5rem 1rem;
      }}
      .brand-titles h1 {{
        font-size: 1.3rem;
      }}
      .agenda-item {{
        grid-template-columns: 1fr;
        gap: 1rem;
      }}
      .agenda-time-box {{
        flex-direction: row;
        gap: 0.75rem;
        padding: 0.5rem 1rem;
      }}
      .cal-cell {{
        min-height: 70px;
        padding: 0.25rem;
      }}
      .cal-event-pill {{
        font-size: 0.65rem;
      }}
    }}
  </style>
</head>
<body>

  <!-- HERO HEADER -->
  <header class="hero-header">
    <div class="container">
      <div class="header-top">
        <div class="brand">
          <div class="brand-icon">🎭</div>
          <div class="brand-titles">
            <h1>北北桃台語活動行事曆</h1>
            <p>臺北市・新北市・桃園市 ｜ 舞台劇・表演・故事・繪本・體驗・導覽</p>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-light" id="btnExportIcs" onclick="exportCalendarFile()">
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            下載 iCal 行事曆 (.ics)
          </button>
          <button class="btn btn-light" id="btnSyncModal" onclick="openSyncModal()">
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/></svg>
            Google 行事曆串接
          </button>
          <button class="btn btn-light btn-icon" id="themeToggleBtn" onclick="toggleTheme()" title="切換深淺模式">
            🌓
          </button>
        </div>
      </div>

      <div class="hero-stats">
        <div class="stat-card">
          <span class="label">未來活動總數</span>
          <span class="val" id="statTotal">--</span>
        </div>
        <div class="stat-card">
          <span class="label">臺北市活動</span>
          <span class="val" id="statTaipei">--</span>
        </div>
        <div class="stat-card">
          <span class="label">新北市活動</span>
          <span class="val" id="statNewTaipei">--</span>
        </div>
        <div class="stat-card">
          <span class="label">桃園市活動</span>
          <span class="val" id="statTaoyuan">--</span>
        </div>
        <div class="stat-card">
          <span class="label">免費入場</span>
          <span class="val" id="statFree">--</span>
        </div>
      </div>
    </div>
  </header>

  <!-- CONTROLS & FILTERS -->
  <div class="controls-wrapper">
    <div class="container controls-container">
      <div class="controls-row-1">
        <div class="search-box">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" stroke-width="2"></circle><line x1="21" y1="21" x2="16.65" y2="16.65" stroke-width="2"></line></svg>
          <input type="text" id="searchInput" placeholder="搜尋劇名、故事屋、文史導覽、圖書館、李江却、樂暢、劇團..." oninput="handleSearch(this.value)">
        </div>

        <div class="view-switchers">
          <button class="view-btn active" data-view="grid" onclick="switchView('grid')">
            🗂️ 圖文卡片
          </button>
          <button class="view-btn" data-view="agenda" onclick="switchView('agenda')">
            📋 清單時間軸
          </button>
          <button class="view-btn" data-view="calendar" onclick="switchView('calendar')">
            📅 月曆檢視
          </button>
        </div>
      </div>

      <!-- City Filters -->
      <div class="filter-pills-row">
        <span class="filter-label">📍 地區：</span>
        <button class="pill active" data-filter-type="city" data-value="all" onclick="setCityFilter('all')">全部地區 <span class="pill-count" id="count-city-all"></span></button>
        <button class="pill" data-filter-type="city" data-value="臺北市" onclick="setCityFilter('臺北市')">🏛️ 臺北市 <span class="pill-count" id="count-city-taipei"></span></button>
        <button class="pill" data-filter-type="city" data-value="新北市" onclick="setCityFilter('新北市')">🌊 新北市 <span class="pill-count" id="count-city-newtaipei"></span></button>
        <button class="pill" data-filter-type="city" data-value="桃園市" onclick="setCityFilter('桃園市')">✈️ 桃園市 <span class="pill-count" id="count-city-taoyuan"></span></button>
      </div>

      <!-- Category Filters -->
      <div class="filter-pills-row">
        <span class="filter-label">🏷️ 類別：</span>
        <button class="pill active" data-filter-type="category" data-value="all" onclick="setCategoryFilter('all')">全部類別</button>
        <button class="pill" data-filter-type="category" data-value="台語舞台劇" onclick="setCategoryFilter('台語舞台劇')">🎭 台語舞台劇</button>
        <button class="pill" data-filter-type="category" data-value="台語表演" onclick="setCategoryFilter('台語表演')">🎪 台語表演</button>
        <button class="pill" data-filter-type="category" data-value="台語故事" onclick="setCategoryFilter('台語故事')">📖 台語故事</button>
        <button class="pill" data-filter-type="category" data-value="台語繪本" onclick="setCategoryFilter('台語繪本')">📚 台語繪本</button>
        <button class="pill" data-filter-type="category" data-value="台語體驗" onclick="setCategoryFilter('台語體驗')">🎨 台語體驗</button>
        <button class="pill" data-filter-type="category" data-value="台語導覽" onclick="setCategoryFilter('台語導覽')">🚶 台語導覽</button>
      </div>

      <!-- Platform Filters -->
      <div class="filter-pills-row">
        <span class="filter-label">🌐 來源：</span>
        <button class="pill active" data-filter-type="platform" data-value="all" onclick="setPlatformFilter('all')">全部來源</button>
        <button class="pill" data-filter-type="platform" data-value="李江却基金會" onclick="setPlatformFilter('李江却基金會')">📜 李江却基金會</button>
        <button class="pill" data-filter-type="platform" data-value="樂暢親子共學" onclick="setPlatformFilter('樂暢親子共學')">🎈 樂暢共學</button>
        <button class="pill" data-filter-type="platform" data-value="北北桃市立圖書館" onclick="setPlatformFilter('北北桃市立圖書館')">📖 市立圖書館</button>
        <button class="pill" data-filter-type="platform" data-value="OPENTIX 兩廳院" onclick="setPlatformFilter('OPENTIX 兩廳院')">🏛️ OPENTIX 兩廳院</button>
        <button class="pill" data-filter-type="platform" data-value="年代售票" onclick="setPlatformFilter('年代售票')">🎫 年代售票</button>
        <button class="pill" data-filter-type="platform" data-value="Accupass 活動通" onclick="setPlatformFilter('Accupass 活動通')">🎟️ Accupass</button>
        <button class="pill" data-filter-type="platform" data-value="Facebook" onclick="setPlatformFilter('Facebook')">📘 Facebook</button>
        <button class="pill" data-filter-type="platform" data-value="Instagram" onclick="setPlatformFilter('Instagram')">📸 Instagram</button>
        <button class="pill" data-filter-type="platform" data-value="Threads" onclick="setPlatformFilter('Threads')">🧵 Threads</button>
        <button class="pill" data-filter-type="platform" data-value="Google 日曆" onclick="setPlatformFilter('Google 日曆')">📅 Google 日曆</button>
      </div>

      <!-- Price Filters -->
      <div class="filter-pills-row">
        <span class="filter-label">💰 費用：</span>
        <button class="pill active" data-filter-type="price" data-value="all" onclick="setPriceFilter('all')">全部費用</button>
        <button class="pill" data-filter-type="price" data-value="free" onclick="setPriceFilter('free')">免費活動</button>
        <button class="pill" data-filter-type="price" data-value="paid" onclick="setPriceFilter('paid')">售票/付費活動</button>
      </div>
    </div>
  </div>

  <!-- MAIN EVENT DISPLAY -->
  <main class="main-content">
    <div class="container">
      <div class="filter-summary">
        <div>目前顯示 <strong id="visibleCount">0</strong> 場台語活動</div>
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
            <button class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);" onclick="prevMonth()">◀ 上個月</button>
            <button class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);" onclick="goToToday()">今天</button>
            <button class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);" onclick="nextMonth()">下個月 ▶</button>
          </div>
        </div>
        <div class="cal-grid" id="calGridHeader">
          <div class="cal-day-header">週日</div>
          <div class="cal-day-header">週一</div>
          <div class="cal-day-header">週二</div>
          <div class="cal-day-header">週三</div>
          <div class="cal-day-header">週四</div>
          <div class="cal-day-header">週五</div>
          <div class="cal-day-header">週六</div>
        </div>
        <div class="cal-grid" id="calGridDays"></div>
      </div>
    </div>
  </main>

  <!-- EVENT DETAIL MODAL -->
  <div class="modal-overlay" id="eventModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog">
      <button class="modal-close" onclick="closeModal()">✕</button>
      <div class="modal-hero-img">
        <img id="modalImg" src="" alt="活動海報">
      </div>
      <div class="modal-content">
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
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

        <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.5rem; color:var(--text-main);">活動內容介紹</h4>
        <div class="modal-desc" id="modalDesc"></div>

        <div class="modal-actions-bar">
          <a id="modalTicketLink" href="#" target="_blank" class="btn btn-primary" style="flex:1; justify-content:center; padding:0.75rem 1.5rem; font-size:0.95rem;">
            🎟️ 前往官方購票 / 活動頁面
          </a>
          <a id="modalGCalLink" href="#" target="_blank" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            📅 加入 Google 行事曆
          </a>
          <button id="modalSingleIcsBtn" onclick="downloadSingleIcs()" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            💾 匯出 .ics
          </button>
          <a id="modalMapLink" href="#" target="_blank" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            🗺️ Google 地圖
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- SYNC & GOOGLE WORKSPACE MODAL -->
  <div class="modal-overlay" id="syncModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog" style="max-width: 550px;">
      <button class="modal-close" onclick="closeSyncModal()">✕</button>
      <div class="modal-content">
        <h2 style="font-size: 1.35rem; font-weight: 800; margin-bottom: 0.75rem; color:var(--text-main);">📅 串接 Google Workspace 行事曆</h2>
        <p style="font-size: 0.9rem; color:var(--text-muted); margin-bottom: 1.25rem;">
          您可以透過以下方式將北北桃台語活動同步至您的 Google 行事曆、Apple 日曆或 Outlook：
        </p>

        <div style="background:var(--bg-main); border-radius:var(--radius-md); padding:1rem; margin-bottom:1.25rem; font-size:0.88rem;">
          <h4 style="font-weight:700; color:var(--text-main); margin-bottom:0.4rem;">方法 1：一鍵下載 iCalendar (.ics) 檔案</h4>
          <p style="color:var(--text-muted); margin-bottom:0.75rem;">點擊下方按鈕下載完整日曆檔，可直接拖入 Google Calendar、Mac 日曆或手機中自動匯入。</p>
          <button class="btn btn-primary" onclick="exportCalendarFile()">📥 下載 taigi_activities.ics</button>
        </div>

        <div style="background:var(--bg-main); border-radius:var(--radius-md); padding:1rem; margin-bottom:1.25rem; font-size:0.88rem;">
          <h4 style="font-weight:700; color:var(--text-main); margin-bottom:0.4rem;">方法 2：單場活動一鍵加入</h4>
          <p style="color:var(--text-muted);">在任一活動卡片或彈窗中，點擊「加入 Google 行事曆」，系統會自動帶入活動主題、時間、地址與購票資訊。</p>
        </div>

        <div style="background:var(--bg-main); border-radius:var(--radius-md); padding:1rem; font-size:0.88rem;">
          <h4 style="font-weight:700; color:var(--text-main); margin-bottom:0.4rem;">方法 3：Python 後端自動同步</h4>
          <p style="color:var(--text-muted);">使用專案內建的 <code>crawler/sources/google_workspace.py</code> 與 <code>credentials.json</code>，即可設定定時 Cron 自動將最新活動同步至指定 Google 日曆 ID。</p>
        </div>
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer>
    <div class="container">
      <p><strong>北北桃台語活動行事曆 (Taigi Activities Hub)</strong></p>
      <p style="margin-top: 0.35rem; font-size: 0.8rem;">
        資料來源涵蓋：李江却台語文教基金會、樂暢親子共學、臺北市立圖書館、新北市立圖書館、桃園市立圖書館、OPENTIX 兩廳院、年代售票、Accupass、Facebook、Instagram、Threads 與 Google Workspace。
      </p>
      <p style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-light);">
        更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ 咱做伙來講台語！
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
      computeStats();
      renderAll();
    }});

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

      document.getElementById('viewGrid').style.display = viewName === 'grid' ? 'grid' : 'none';
      document.getElementById('viewAgenda').style.display = viewName === 'agenda' ? 'flex' : 'none';
      document.getElementById('viewCalendar').style.display = viewName === 'calendar' ? 'block' : 'none';

      if (viewName === 'calendar') {{
        renderCalendar();
      }}
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
      renderAll();
    }}

    function setPriceFilter(price) {{
      currentPrice = price;
      updatePills('price', price);
      renderAll();
    }}

    function updatePills(filterType, val) {{
      document.querySelectorAll(`button[data-filter-type="${{filterType}}"]`).forEach(p => {{
        p.classList.toggle('active', p.dataset.value === val);
      }});
    }}

    function handleSearch(val) {{
      searchQuery = val.trim().toLowerCase();
      renderAll();
    }}

    function getFilteredActivities() {{
      return ACTIVITIES_DATA.filter(act => {{
        if (currentCity !== 'all' && act.city !== currentCity) return false;
        if (currentCategory !== 'all' && act.category !== currentCategory) return false;
        if (currentPlatform !== 'all' && act.source_platform !== currentPlatform) return false;
        if (currentPrice === 'free' && !act.is_free) return false;
        if (currentPrice === 'paid' && act.is_free) return false;
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
      const free = ACTIVITIES_DATA.filter(a => a.is_free).length;

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
      if (!isoStr) return '';
      const dt = new Date(isoStr);
      if (isNaN(dt)) return isoStr;
      const y = dt.getFullYear();
      const m = dt.getMonth() + 1;
      const d = dt.getDate();
      const days = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
      const dayName = days[dt.getDay()];
      const time = dt.toLocaleTimeString('zh-TW', {{ hour: '2-digit', minute: '2-digit', hour12: false }});
      return `${{y}}/${{m}}/${{d}} (${{dayName}}) ${{time}}`;
    }}

    function renderGrid(events) {{
      const container = document.getElementById('viewGrid');
      if (events.length === 0) {{
        container.innerHTML = `
          <div class="empty-state" style="grid-column: 1/-1;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="48" height="48" style="margin-bottom:1rem;color:var(--text-light);"><circle cx="12" cy="12" r="10" stroke-width="2"/><line x1="8" y1="15" x2="16" y2="15" stroke-width="2"/><line x1="9" y1="9" x2="9.01" y2="9" stroke-width="2"/><line x1="15" y1="9" x2="15.01" y2="9" stroke-width="2"/></svg>
            <h3>查無符合條件的台語活動</h3>
            <p>請嘗試清除篩選條件或縮小搜尋字詞</p>
          </div>
        `;
        return;
      }}

      container.innerHTML = events.map(act => {{
        const cover = act.cover_image || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80';
        return `
          <div class="event-card" onclick="openModal('${{act.id}}')">
            <div class="card-cover">
              <img src="${{cover}}" alt="${{act.title}}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80'">
              <div class="card-badges-top">
                <span class="badge badge-city">📍 ${{act.city}}</span>
                <span class="badge badge-category">${{act.category}}</span>
              </div>
              <span class="badge badge-platform">${{act.source_platform}}</span>
            </div>
            <div class="card-body">
              <div class="card-date">
                <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg>
                ${{formatDateDisplay(act.start_time)}}
              </div>
              <h3 class="card-title">${{act.title}}</h3>
              <p class="card-desc">${{act.description}}</p>
              <div class="card-meta">
                <div class="meta-item">
                  <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                  <span>${{act.venue}}</span>
                </div>
                <div class="meta-item">
                  <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
                  <span>${{act.organizer}}</span>
                </div>
              </div>
            </div>
            <div class="card-footer">
              <span class="card-price ${{act.is_free ? 'free' : ''}}">${{act.price_info}}</span>
              <button class="btn btn-primary" style="padding: 0.35rem 0.85rem; font-size:0.8rem;">查看詳情</button>
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
              <span style="font-size:0.82rem; font-weight:600; color:var(--text-muted);">${{groups[dateKey].length}} 場活動</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:1rem; margin-top:0.85rem;">
              ${{groups[dateKey].map(act => {{
                const d = new Date(act.start_time);
                const timeStr = d.toLocaleTimeString('zh-TW', {{ hour:'2-digit', minute:'2-digit', hour12:false }});
                return `
                  <div class="agenda-item" onclick="openModal('${{act.id}}')">
                    <div class="agenda-time-box">
                      <div class="day-num">${{d.getDate()}}</div>
                      <div class="month-name">${{d.getMonth()+1}}月</div>
                      <div class="time-str">${{timeStr}}</div>
                    </div>
                    <div class="agenda-content">
                      <div style="display:flex; gap:0.4rem; margin-bottom:0.35rem; flex-wrap:wrap;">
                        <span class="badge badge-city">📍 ${{act.city}}</span>
                        <span class="badge badge-category">${{act.category}}</span>
                        <span class="badge" style="background:var(--secondary-light); color:var(--secondary);">${{act.source_platform}}</span>
                      </div>
                      <h3>${{act.title}}</h3>
                      <div class="agenda-content-meta">
                        <span>🏛️ ${{act.venue}}</span>
                        <span>👥 ${{act.organizer}}</span>
                        <span>🏷️ <strong style="color:var(--primary);">${{act.price_info}}</strong></span>
                      </div>
                      <p style="font-size:0.85rem; color:var(--text-muted); display:-webkit-box; -webkit-line-clamp:1; -webkit-box-orient:vertical; overflow:hidden;">${{act.description}}</p>
                    </div>
                    <div class="agenda-actions">
                      <button class="btn btn-primary" style="font-size:0.82rem; justify-content:center;">活動詳情</button>
                      <a href="${{act.gcal_url}}" target="_blank" class="btn btn-light" style="font-size:0.8rem; justify-content:center; color:var(--text-main); border-color:var(--border-color);" onclick="event.stopPropagation();">📅 加日曆</a>
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
              ${{dayEvents.length > 0 ? `<span style="font-size:0.7rem; font-weight:700; color:var(--primary);">${{dayEvents.length}}場</span>` : ''}}
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

      document.getElementById('modalImg').src = act.cover_image || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=800&q=80';
      document.getElementById('modalCity').innerText = '📍 ' + act.city + (act.district ? ` (${{act.district}})` : '');
      document.getElementById('modalCategory').innerText = act.category;
      document.getElementById('modalPlatform').innerText = '🌐 ' + act.source_platform;
      document.getElementById('modalTitle').innerText = act.title;
      document.getElementById('modalTime').innerText = formatDateDisplay(act.start_time);
      document.getElementById('modalVenue').innerText = `${{act.venue}} (${{act.address}})`;
      document.getElementById('modalOrganizer').innerText = act.organizer;
      document.getElementById('modalPrice').innerText = act.price_info;
      document.getElementById('modalDesc').innerText = act.description;

      document.getElementById('modalTicketLink').href = act.source_url;
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

    function exportCalendarFile() {{
      let icsContent = "BEGIN:VCALENDAR\\r\\nVERSION:2.0\\r\\nPRODID:-//Antigravity//Taigi Calendar//ZH_TW\\r\\nX-WR-CALNAME:北北桃台語活動行事曆\\r\\n";
      
      const filtered = getFilteredActivities();
      filtered.forEach(act => {{
        const dt = act.start_time.replace(/[-:]/g, "").split(".")[0];
        const formattedDt = dt.includes("T") ? dt : dt + "T140000";
        icsContent += "BEGIN:VEVENT\\r\\n";
        icsContent += `UID:${{act.id}}@taigiactivities.tw\\r\\n`;
        icsContent += `DTSTART:${{formattedDt}}\\r\\n`;
        icsContent += `DTEND:${{formattedDt}}\\r\\n`;
        icsContent += `SUMMARY:[${{act.category}}] ${{act.title.replace(/,/g, '\\\\,')}}\\r\\n`;
        icsContent += `DESCRIPTION:${{act.description.replace(/\\n/g, '\\\\n').replace(/,/g, '\\\\,')}}\\r\\n`;
        icsContent += `LOCATION:${{act.venue.replace(/,/g, '\\\\,')}}\\r\\n`;
        icsContent += `URL:${{act.source_url}}\\r\\n`;
        icsContent += "END:VEVENT\\r\\n";
      }});

      icsContent += "END:VCALENDAR";

      const blob = new Blob([icsContent], {{ type: 'text/calendar;charset=utf-8' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'taigi_activities.ics';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    function downloadSingleIcs() {{
      if (!selectedActivity) return;
      const act = selectedActivity;
      const dt = act.start_time.replace(/[-:]/g, "").split(".")[0];
      const formattedDt = dt.includes("T") ? dt : dt + "T140000";

      let icsContent = "BEGIN:VCALENDAR\\r\\nVERSION:2.0\\r\\nPRODID:-//Antigravity//Taigi Calendar//ZH_TW\\r\\n";
      icsContent += "BEGIN:VEVENT\\r\\n";
      icsContent += `UID:${{act.id}}@taigiactivities.tw\\r\\n`;
      icsContent += `DTSTART:${{formattedDt}}\\r\\n`;
      icsContent += `DTEND:${{formattedDt}}\\r\\n`;
      icsContent += `SUMMARY:[${{act.category}}] ${{act.title.replace(/,/g, '\\\\,')}}\\r\\n`;
      icsContent += `DESCRIPTION:${{act.description.replace(/\\n/g, '\\\\n').replace(/,/g, '\\\\,')}}\\r\\n`;
      icsContent += `LOCATION:${{act.venue.replace(/,/g, '\\\\,')}}\\r\\n`;
      icsContent += `URL:${{act.source_url}}\\r\\n`;
      icsContent += "END:VEVENT\\r\\n";
      icsContent += "END:VCALENDAR";

      const blob = new Blob([icsContent], {{ type: 'text/calendar;charset=utf-8' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${{act.title.substring(0, 20)}}.ics`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
