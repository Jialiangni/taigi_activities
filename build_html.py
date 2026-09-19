"""
Single-file HTML Builder for Taigi Activities Calendar
Compiles activities into an iPhone & Android optimized, clutter-free standalone index.html
"""
import json
from pathlib import Path
from html import escape
from typing import List
from datetime import datetime, timezone, timedelta
from crawler.models import Activity
from crawler.presentation import session_title
from crawler.sources.google_workspace import GoogleWorkspaceSync


def generate_single_html(activities: List[Activity], output_path: str = "index.html", resources=None) -> str:
    root = Path(__file__).resolve().parent
    translations = json.loads((root / 'data/ui_taigi.json').read_text(encoding='utf-8'))
    price_translations = json.loads((root / 'data/ui_price_taigi.json').read_text(encoding='utf-8'))
    styles = (root / 'assets/site.css').read_text(encoding='utf-8')
    activities_data = []
    g_sync = GoogleWorkspaceSync()

    for act in activities:
        d = act.to_dict()
        # Exact source-text keys prevent stale translations after an official correction.
        d['description_taigi'] = translations.get(d['description'], '')
        d['price_info_taigi'] = price_translations.get(d['price_info'], '')
        d['title_taigi'] = session_title(d['title'])
        d["gcal_url"] = g_sync.generate_google_calendar_url(act)
        d["ics_event"] = g_sync.event_content(act)
        d["ics_path"] = 'calendar-events/' + g_sync.single_event_filename(act)
        activities_data.append(d)

    source_names = sorted({a.source_platform for a in activities})
    platform_options = '<option value="all">攏總</option>' + ''.join(
        '<option value="' + escape(name, quote=True) + '">' + escape(name) +
        '（' + str(sum(a.source_platform == name for a in activities)) + '）</option>' for name in source_names)
    activities_json = json.dumps(activities_data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    calendar_header_json = json.dumps(g_sync.HEADER, ensure_ascii=False)

    resource_cards = ''.join(
        '<article class="resource-card"><small>' + escape(r['city']) + ' · ' +
        {'audio_guide': '台語語音導覽', 'reservation_guide': '台語導覽預約', 'exhibition_resource': '台語相關展覽',
         'reading_resource': '台語閱讀推廣', 'traditional_performance_resource': '傳統表演資訊（語言依當日節目）'}[r['kind']] +
        '</small><h3 lang="zh-Hant">' + escape(r['title']) + '</h3><p>' + escape(translations.get(r['description'], r['description'])) +
        '</p><a href="' + escape(r['url'], quote=True) + '" target="_blank" rel="noopener noreferrer">看官方的資料 ↗</a>' +
        '<small>核對：' + escape(r['checked_at'][:10]) + '</small></article>' for r in (resources or []))
    resource_section = ('<section id="guideResources" class="container guide-resources"><h2>台語導覽、展覽、閱讀佮傳統表演資訊</h2>'
                        '<p>語音導覽、預約服務、書展、閱讀推廣佮相關傳統表演；開館日、節目語言、所費佮預約，請照主辦公告。下跤這寡無算入已核實的台語活動場次，也無囥入下載的日曆。</p>'
                        '<div class="resource-grid">' + resource_cards + '</div></section>') if resources else ''

    html_content = f"""<!DOCTYPE html>
<html lang="nan-Hant-TW" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>北北桃台語活動日曆 | 臺北・新北・桃園 台語舞台劇/表演/故事/繪本/體驗/導覽</title>
  <meta name="description" content="北北桃台語活動行事曆：收錄有官方公告且經核實的場次。彙整臺北市、新北市、桃園市的台語舞台劇、表演、故事屋、台語繪本共讀、文化體驗、文史走讀導覽活動。">
  
  <!-- Android Chrome & PWA 支援 -->
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="theme-color" content="#1d1d1f">
  <link rel="manifest" href="manifest.json">
  
  <!-- iOS iPhone Web App (PWA) 支援 -->
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="台語日曆">
  <meta name="format-detection" content="telephone=no">
  <script>
    // Apply an explicit saved preference before paint; otherwise start dark.
    try {{
      if (localStorage.getItem('taigi_theme') === 'light') document.documentElement.setAttribute('data-theme', 'light');
    }} catch (_) {{}}
  </script>
  <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%231d1d1f'/><text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-size='50'>台</text></svg>">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%231d1d1f'/><text x='50%' y='55%' dominant-baseline='middle' text-anchor='middle' font-size='50'>台</text></svg>">

  <style>
{styles}
  </style>
</head>
<body>

  <header class="hero-header">
    <div class="container header-top">
      <div class="brand">北北桃台語活動</div>
      <div class="header-actions">
        <button class="btn download-top" onclick="exportCalendarFile()">下載日曆</button>
        <button class="btn" onclick="openSyncModal()">日曆佮設定</button>
        <button class="btn btn-icon" onclick="toggleTheme()" aria-label="換深色抑是淺色">◐</button>
      </div>
    </div>
  </header>
  <section class="container intro">
    <h1>後一場，台語相見。</h1>
    <p>臺北、新北、桃園，做伙來講台語。</p>
    <details class="source-note"><summary>活動資料按怎收錄</summary><p>干焦列有核對官方公告的場次；猶未核實的資料暫時無刊。所費猶未公告的，無算入毋免錢抑是愛納錢的篩選。日期佮時間攏是臺灣時間，出門進前請閣看一擺官方公告。 <a href="#guideResources">導覽、展覽、閱讀佮傳統表演資訊 ↓</a></p></details>
    <div hidden><span id="statTotal"></span><span id="statTaipei"></span><span id="statNewTaipei"></span><span id="statTaoyuan"></span><span id="statFree"></span></div>
  </section>
  <div class="controls-wrapper">
    <div class="container controls-container">
      <div class="controls-row-1">
        <div class="search-box"><span aria-hidden="true">⌕</span><input type="search" id="searchInput" aria-label="揣活動抑是地點" placeholder="揣活動抑是地點" oninput="handleSearch(this.value)"></div>
        <div class="view-switchers" role="group" aria-label="欲按怎看">
          <button class="view-btn active" data-view="grid" aria-pressed="true" onclick="switchView('grid')">活動</button>
          <button class="view-btn" data-view="agenda" aria-pressed="false" onclick="switchView('agenda')">清單</button>
          <button class="view-btn" data-view="calendar" aria-pressed="false" onclick="switchView('calendar')">看一禮拜</button>
        </div>
      </div>
      <div class="filter-row" role="group" aria-label="揀地區">
        <span class="filter-label">佗位</span>
        <div class="city-options">
        <button class="pill active" data-filter-type="city" data-value="all" aria-pressed="true" onclick="setCityFilter('all')">攏總 <span class="pill-count" id="count-city-all"></span></button>
        <button class="pill" data-filter-type="city" data-value="臺北市" aria-pressed="false" onclick="setCityFilter('臺北市')"><span class="badge-city city-taipei">臺北</span><span class="pill-count" id="count-city-taipei"></span></button>
        <button class="pill" data-filter-type="city" data-value="新北市" aria-pressed="false" onclick="setCityFilter('新北市')"><span class="badge-city city-newtaipei">新北</span><span class="pill-count" id="count-city-newtaipei"></span></button>
        <button class="pill" data-filter-type="city" data-value="桃園市" aria-pressed="false" onclick="setCityFilter('桃園市')"><span class="badge-city city-taoyuan">桃園</span><span class="pill-count" id="count-city-taoyuan"></span></button>
        </div>
      </div>
      <div class="month-filter" role="group" aria-label="揀月份，會當揀幾若个月"><span class="month-filter-label">幾月</span><div class="month-options" id="monthFilterOptions"></div><span class="month-help">會當揀幾若个月</span></div>
      <button class="mobile-filter-button" id="mobileFilterButton" onclick="openFilterModal()" aria-haspopup="dialog" aria-controls="filterModal">來源・種類・所費 <span id="mobileFilterCount"></span><span aria-hidden="true">☷</span></button>
      <div class="select-filters" id="advancedFilters">
        <label for="sourceFilter">來源 <select id="sourceFilter" data-filter-select="platform" onchange="setPlatformFilter(this.value)">{platform_options}</select></label>
        <label for="categoryFilter">種類 <select id="categoryFilter" data-filter-select="category" onchange="setCategoryFilter(this.value)"><option value="all">攏總</option><option value="台語舞台劇">舞台劇</option><option value="台語表演">表演</option><option value="台語故事">講古</option><option value="台語繪本">繪本</option><option value="台語體驗">體驗</option><option value="台語導覽">導覽</option><option value="台語活動">其他活動</option></select></label>
        <label for="priceFilter">所費 <select id="priceFilter" data-filter-select="price" onchange="setPriceFilter(this.value)"><option value="all">攏總</option><option value="free">毋免錢</option><option value="paid">愛納錢</option></select></label>
      </div>
    </div>
  </div>

  <dialog class="modal-overlay filter-modal" id="filterModal" aria-labelledby="filterTitle" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog">
      <div class="modal-sheet-handle" aria-hidden="true"></div>
      <button class="modal-close" onclick="closeFilterModal()" aria-label="關起來" autofocus>×</button>
      <div class="modal-content">
        <h2 id="filterTitle">來源・種類・所費</h2>
        <div id="mobileFilterHost"></div>
        <div class="filter-sheet-actions"><button class="btn" onclick="resetExtraFilters()" aria-label="來源、種類、所費攏總">攏總</button><button class="btn btn-primary" onclick="closeFilterModal()">看活動 <span id="filterResultCount"></span></button></div>
      </div>
    </div>
  </dialog>

  <!-- MAIN EVENT DISPLAY -->
  <main class="main-content">
    <div class="container">
      <div class="filter-summary">
        <div>攏總 <strong id="visibleCount">0</strong> 場活動</div>
        <div id="activeFiltersSummary"></div>
      </div>

      <!-- VIEW 1: Grid Cards -->
      <div id="viewGrid" class="events-grid"></div>

      <!-- VIEW 2: Agenda List -->
      <div id="viewAgenda" class="agenda-list" style="display: none;"></div>

      <!-- VIEW 3: Weekly calendar (Monday–Sunday, Asia/Taipei) -->
      <div id="viewCalendar" class="calendar-container" style="display: none;">
        <div class="cal-header">
          <div class="cal-title" id="calCurrentWeekLabel" aria-live="polite"></div>
          <div class="cal-nav">
            <button class="btn btn-light" onclick="prevWeek()" aria-label="頂禮拜">‹ 頂禮拜</button>
            <button class="btn btn-light" onclick="goToToday()">這禮拜</button>
            <button class="btn btn-light" onclick="nextWeek()" aria-label="後禮拜">後禮拜 ›</button>
          </div>
        </div>
        <div class="cal-legend" aria-label="城市顏色圖例">
          <span class="badge badge-city city-taipei">臺北市</span>
          <span class="badge badge-city city-newtaipei">新北市</span>
          <span class="badge badge-city city-taoyuan">桃園市</span>
          <span class="cal-summary" id="calWeekSummary" aria-live="polite"></span>
        </div>
        <div class="week-strip" id="calWeekDays"></div>
        <div class="cal-grid" id="calGridDays"></div>
      </div>
    </div>
  </main>
  {resource_section}

  <!-- EVENT DETAIL MODAL (Android & iPhone Bottom Sheet) -->
  <dialog class="modal-overlay" lang="zh-Hant" id="eventModal" aria-labelledby="modalTitle" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog">
      <div class="modal-sheet-handle"></div>
      <button class="modal-close" onclick="closeModal()" aria-label="關起活動詳情" autofocus>✕</button>
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
              <strong style="color:var(--text-main);">所在：</strong>
              <div id="modalVenue" style="color:var(--text-muted);"></div>
            </div>
          </div>
          <div class="info-row">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
            <div>
              <strong style="color:var(--text-main);">主辦：</strong>
              <div id="modalOrganizer" style="color:var(--text-muted);"></div>
            </div>
          </div>
          <div class="info-row">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41 0-.55-.23-1.06-.59-1.42zM5.5 7C4.67 7 4 6.33 4 5.5S4.67 4 5.5 4 7 4.67 7 5.5 6.33 7 5.5 7z"/></svg>
            <div>
              <strong style="color:var(--text-main);">所費：</strong>
              <div id="modalPrice" style="color:var(--text-muted);"></div>
            </div>
          </div>
        </div>

        <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.4rem; color:var(--text-main);">活動紹介</h4>
        <div class="modal-desc" id="modalDesc"></div>

        <div class="modal-actions-bar">
          <a id="modalRegistrationLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="padding:0.75rem 1.25rem; font-size:0.92rem;" hidden>
            ✍️ 報名／買票 ↗
          </a>
          <a id="modalTicketLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="padding:0.75rem 1.25rem; font-size:0.92rem;">
            🌐 活動公告 ↗
          </a>
          <a id="modalGoogleSearchLink" href="#" target="_blank" rel="noopener noreferrer" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color); font-weight:600;">
            🔍 Google 揣報名／買票 ↗
          </a>
          <!-- Dynamic Calendar CTA (Auto-adapted for Android Google Calendar vs iPhone Apple Calendar) -->
          <a id="modalGCalLink" href="#" target="_blank" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            📅 加到 Google 日曆 (Android 推薦)
          </a>
          <a id="modalSingleIcsBtn" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            🍏 加到 Apple 日曆 (.ics)
          </a>
          <p id="lineCalendarHelp" class="line-calendar-help" hidden>
            LINE 內建瀏覽器無法直接開 Apple 日曆。請點右上角「⋯」→「用預設瀏覽器開啟」，轉去 Safari 了後閣點一擺。
          </p>
          <button id="modalShareBtn" onclick="shareCurrentActivity()" class="btn btn-light btn-share">
            📤 分享到 LINE / 社群
          </button>
          <a id="modalMapLink" href="#" target="_blank" class="btn btn-light" style="color:var(--text-main); border-color:var(--border-color);">
            🗺️ Google 地圖導航
          </a>
        </div>
      </div>
    </div>
  </dialog>

  <dialog class="modal-overlay" id="syncModal" aria-labelledby="syncTitle" onclick="closeModalOnBackdrop(event)">
    <div class="modal-dialog" style="max-width:550px">
      <div class="modal-sheet-handle" aria-hidden="true"></div>
      <button class="modal-close" onclick="closeSyncModal()" aria-label="關起來" autofocus>×</button>
      <div class="modal-content settings-options">
        <h2 id="syncTitle">日曆佮設定</h2>
        <div><h3>共活動囥入日曆</h3><p>下載的日曆干焦有你揀的活動，會當匯入 Apple、Google 抑是其他支援 ICS 的日曆。若欲加一場，請開「活動詳情」。</p><button class="btn btn-primary" onclick="exportCalendarFile()">下載揀好的日曆</button></div>
        <div><h3>囥佇手機的主畫面</h3><p>iPhone 用 Safari 的分享選單揀「加入主畫面」；Android 用 Chrome 的選單揀「新增至主螢幕」。</p></div>
        <div><h3>畫面的色水</h3><button class="btn" onclick="toggleTheme()">換深色抑是淺色</button></div>
        <details class="source-note"><summary>活動資料按怎收錄</summary><p>干焦列有核對官方公告的場次；猶未核實的資料暫時無刊。所費猶未公告的，無算入毋免錢抑是愛納錢的篩選。日期佮時間攏是臺灣時間，出門進前請閣看一擺官方公告。</p></details>
      </div>
    </div>
  </dialog>

  <nav class="ios-tab-bar" aria-label="活動導覽">
    <button class="ios-tab-item active" data-tab="grid" aria-pressed="true" onclick="switchViewMobile('grid')"><svg aria-hidden="true" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg><span>活動</span></button>
    <button class="ios-tab-item" data-tab="agenda" aria-pressed="false" onclick="switchViewMobile('agenda')"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M9 5h12M9 12h12M9 19h12M3 5h1M3 12h1M3 19h1"/></svg><span>清單</span></button>
    <button class="ios-tab-item" data-tab="calendar" aria-pressed="false" onclick="switchViewMobile('calendar')"><svg aria-hidden="true" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 11h18M8 16h2M14 16h2"/></svg><span>看一禮拜</span></button>
    <button class="ios-tab-item" aria-haspopup="dialog" aria-controls="syncModal" onclick="openSyncModal()"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/></svg><span>日曆佮設定</span></button>
  </nav>

  <!-- FOOTER -->
  <footer>
    <div class="container">
      <p><strong>北北桃台語活動日曆 (Taigi Activities Hub)</strong></p>
      <p style="margin-top: 0.35rem; font-size: 0.78rem;">
        這頁干焦收有核對官方公告的場次，毋是所有的活動。各地的數目照已核實的資料來算；出門進前請閣看一擺官方公告。
      </p>
      <p style="margin-top: 0.4rem; font-size: 0.75rem; color: var(--text-light);">
        頁面做好的時間：{datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}（臺北時間；毋代表有閣核對過） ｜ 咱做伙來講台語！
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
    const selectedMonths = new Set();
    let searchQuery = '';
    let selectedActivity = null;
    let calDate = new Date(taipeiDateKey() + 'T00:00:00Z');

    document.addEventListener('DOMContentLoaded', () => {{
      initTheme();
      adaptToDeviceOS();
      computeStats();
      renderMonthFilters();
      renderAll();
      const requestedActivity = new URLSearchParams(location.search).get('activity');
      if (requestedActivity) openModal(requestedActivity);
      document.querySelectorAll('dialog.modal-overlay').forEach(dialog => {{
        dialog.addEventListener('cancel', event => {{ event.preventDefault(); closeOverlay(dialog.id); }});
      }});
      window.matchMedia('(max-width: 700px)').addEventListener('change', () => {{
        if (document.getElementById('filterModal').open) closeFilterModal();
      }});
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

    function isLineIOSBrowser() {{
      return /iPhone|iPad|iPod/i.test(navigator.userAgent) && /Line\//i.test(navigator.userAgent);
    }}

    function externalPageForActivity(actId) {{
      const pageUrl = location.protocol === 'file:'
        ? 'https://jialiangni.github.io/taigi_activities/'
        : location.origin + location.pathname;
      return pageUrl + '?activity=' + encodeURIComponent(actId) + '&openExternalBrowser=1';
    }}

    function initTheme() {{
      let saved = 'dark';
      try {{ if (localStorage.getItem('taigi_theme') === 'light') saved = 'light'; }} catch (_) {{}}
      document.documentElement.setAttribute('data-theme', saved);
    }}

    function toggleTheme() {{
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try {{ localStorage.setItem('taigi_theme', next); }} catch (_) {{}}
    }}

    function switchView(viewName) {{
      currentView = viewName;
      document.querySelectorAll('.view-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.view === viewName);
        btn.setAttribute('aria-pressed', String(btn.dataset.view === viewName));
      }});
      document.querySelectorAll('.ios-tab-item[data-tab]').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.tab === viewName);
        btn.setAttribute('aria-pressed', String(btn.dataset.tab === viewName));
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
      renderAll();
    }}

    function setPriceFilter(price) {{
      currentPrice = price;
      updatePills('price', price);
      renderAll();
    }}

    function monthLabel(key) {{
      const [year, month] = key.split('-');
      return `${{year}}∙${{month}}`;
    }}

    function renderMonthFilters() {{
      const months = [...new Set(ACTIVITIES_DATA.map(act => taipeiDateKey(new Date(act.start_time)).slice(0, 7)))].sort();
      document.getElementById('monthFilterOptions').innerHTML =
        `<button class="pill ${{selectedMonths.size ? '' : 'active'}}" data-month="all" aria-pressed="${{!selectedMonths.size}}" onclick="toggleMonth('all')">攏總</button>` +
        months.map(month => `<button class="pill ${{selectedMonths.has(month) ? 'active' : ''}}" data-month="${{month}}" aria-pressed="${{selectedMonths.has(month)}}" onclick="toggleMonth('${{month}}')">${{monthLabel(month)}}</button>`).join('');
    }}

    function toggleMonth(month) {{
      if (month === 'all') selectedMonths.clear();
      else if (selectedMonths.has(month)) selectedMonths.delete(month);
      else selectedMonths.add(month);
      // Keep buttons in place so keyboard focus and mobile horizontal scroll survive toggling.
      document.querySelectorAll('[data-month]').forEach(button => {{
        const active = button.dataset.month === 'all' ? !selectedMonths.size : selectedMonths.has(button.dataset.month);
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      }});
      if (selectedMonths.size) {{
        const first = weekStart(calDate).toISOString().slice(0, 10);
        const end = new Date(weekStart(calDate));
        end.setUTCDate(end.getUTCDate() + 6);
        const last = end.toISOString().slice(0, 10);
        const filtered = getFilteredActivities().slice().sort((a,b) => new Date(a.start_time) - new Date(b.start_time));
        const inWeek = filtered.some(a => {{
          const key = taipeiDateKey(new Date(a.start_time));
          return key >= first && key <= last;
        }});
        if (!inWeek) calDate = new Date((filtered.length ? taipeiDateKey(new Date(filtered[0].start_time)) : [...selectedMonths].sort()[0] + '-01') + 'T00:00:00Z');
      }}
      renderAll();
    }}

    function updatePills(filterType, val) {{
      document.querySelectorAll(`[data-filter-select="${{filterType}}"]`).forEach(select => {{ select.value = val; }});
      document.querySelectorAll(`button[data-filter-type="${{filterType}}"]`).forEach(p => {{
        p.classList.toggle('active', p.dataset.value === val);
        p.setAttribute('aria-pressed', String(p.dataset.value === val));
      }});
    }}

    function handleSearch(val) {{
      searchQuery = val.trim().toLowerCase();
      renderAll();
    }}

    function getFilteredActivities() {{
      return ACTIVITIES_DATA.filter(act => {{
        if (selectedMonths.size && !selectedMonths.has(taipeiDateKey(new Date(act.start_time)).slice(0, 7))) return false;
        if (currentCity !== 'all' && act.city !== currentCity) return false;
        if (currentCategory !== 'all' && act.category !== currentCategory) return false;
        if (currentPlatform !== 'all' && act.source_platform !== currentPlatform) return false;
        if (currentPrice === 'free' && act.is_free !== true) return false;
        if (currentPrice === 'paid' && act.is_free !== false) return false;
        if (searchQuery) {{
          const targetStr = `${{act.title}} ${{act.title_taigi || ''}} ${{act.description_taigi || ''}} ${{act.source_platform}} ${{act.description}} ${{act.venue}} ${{act.address}} ${{act.organizer}} ${{act.tags.join(' ')}}`.toLowerCase();
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
      document.getElementById('activeFiltersSummary').innerText = selectedMonths.size ? [...selectedMonths].sort().map(monthLabel).join('、') : '攏總';
      const extraCount = [currentPlatform, currentCategory, currentPrice].filter(value => value !== 'all').length;
      document.getElementById('mobileFilterCount').innerText = extraCount ? String(extraCount) : '';
      document.getElementById('filterResultCount').innerText = `（${{filtered.length}}）`;

      renderGrid(filtered);
      renderAgenda(filtered);
      if (currentView === 'calendar') {{
        renderCalendar();
      }}
    }}

    function formatCalendarDate(dateKey, withWeekday = true) {{
      const label = dateKey.replace(/-/g, '∙');
      const days = ['禮拜', '拜一', '拜二', '拜三', '拜四', '拜五', '拜六'];
      return withWeekday ? `${{label}} ${{days[new Date(dateKey + 'T00:00:00Z').getUTCDay()]}}` : label;
    }}

    function formatDateDisplay(isoStr) {{
      if (!isoStr) return '時間猶未公告';
      const date = new Date(isoStr);
      const time = new Intl.DateTimeFormat('zh-TW', {{ timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }}).format(date);
      return `${{formatCalendarDate(taipeiDateKey(date))}} ${{time}}`;
    }}

    function formatEventTime(startIso, endIso) {{
      const start = formatDateDisplay(startIso);
      if (!endIso) return start + '（結束時間猶未公告）';
      const end = new Date(endIso);
      if (taipeiDateKey(new Date(startIso)) !== taipeiDateKey(end)) return start + ' - ' + formatDateDisplay(endIso);
      const endTime = new Intl.DateTimeFormat('zh-TW', {{ timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }}).format(end);
      return start + ' - ' + endTime;
    }}

    function sourceLabel(source) {{
      return {{'Accupass 活動通':'Accupass','北北桃市立圖書館':'市立圖書館','OPENTIX 兩廳院':'OPENTIX'}}[source] || source;
    }}
    function categoryLabel(category) {{
      return {{'台語故事':'台語講古','台語導覽':'台語導覽'}}[category] || category;
    }}
    function feeLabel(act) {{
      return act.is_free === true ? '毋免錢' : act.is_free === false ? '愛納錢' : '所費猶未公告';
    }}
    function taigiDate(iso) {{
      return formatDateDisplay(iso);
    }}
    function activityCard(act) {{
      const text = escapeCalendarText;
      return `<article class="event-card" data-event-id="${{text(act.id)}}">
        <div class="card-labels"><span class="badge badge-city ${{cityClass(act.city)}}">${{text(act.city)}}</span><span class="badge badge-category">${{text(categoryLabel(act.category))}}</span><span class="badge badge-platform">${{text(sourceLabel(act.source_platform))}}</span></div>
        <div class="card-date">${{taigiDate(act.start_time)}}</div>
        <h3 class="card-title" lang="zh-Hant">${{text(act.title_taigi || act.title)}}</h3>
        <p class="card-desc">${{text(act.description_taigi || ('簡介原文：' + act.description))}}</p>
        <p class="card-venue" lang="zh-Hant">${{text(act.venue)}}</p>
        <div class="card-footer"><span class="card-price">${{feeLabel(act)}}</span><button class="card-detail" lang="zh-Hant" data-activity-id="${{text(act.id)}}" onclick="openModal(this.dataset.activityId)">活動詳情 ›</button></div>
      </article>`;
    }}
    function renderGrid(events) {{
      document.getElementById('viewGrid').innerHTML = events.length ? events.map(activityCard).join('') : '<div class="empty-state"><h3>揣無合條件的台語活動</h3><p>這个條件猶無核實的場次，毋代表當地無活動。會當改揀別个條件。</p></div>';
    }}

    function renderAgenda(events) {{
      const container = document.getElementById('viewAgenda');
      if (events.length === 0) {{
        container.innerHTML = `
          <div class="empty-state">
            <h3>揣無合條件的台語活動</h3>
          </div>
        `;
        return;
      }}

      const groups = {{}};
      events.forEach(act => {{
        const dateKey = taipeiDateKey(new Date(act.start_time));
        if (!groups[dateKey]) groups[dateKey] = [];
        groups[dateKey].push(act);
      }});

      let html = '';
      Object.keys(groups).sort().forEach(dateKey => {{
        const dt = new Date(dateKey + 'T00:00:00Z');
        const groupLabel = formatCalendarDate(dateKey);

        html += `
          <div>
            <div class="agenda-group-header">
              <span>${{groupLabel}}</span>
              <span style="font-size:0.75rem; font-weight:600; color:var(--text-muted);">${{groups[dateKey].length}} 場活動</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.75rem; margin-top:0.65rem;">
              ${{groups[dateKey].map(act => {{
                const d = new Date(act.start_time);
                const timeStr = d.toLocaleTimeString('zh-TW', {{ hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'Asia/Taipei' }});
                return `
                  <div class="agenda-item" onclick="openModal('${{act.id}}')">
                    <div class="agenda-time-box">
                      <div class="day-num">${{dt.getUTCDate()}}</div>
                      <div class="month-name">${{dt.getUTCMonth()+1}}月</div>
                      <div class="time-str">${{timeStr}}</div>
                    </div>
                    <div class="agenda-content">
                      <div style="display:flex; gap:0.3rem; margin-bottom:0.25rem; flex-wrap:wrap;">
                        <span class="badge badge-city ${{cityClass(act.city)}}">${{act.city}}</span>
                        <span class="badge badge-category">${{categoryLabel(act.category)}}</span>
                        <span class="badge" style="background:var(--secondary-light); color:var(--secondary);">${{sourceLabel(act.source_platform)}}</span>
                      </div>
                      <h3>${{escapeCalendarText(act.title_taigi || act.title)}}</h3>
                      <div class="agenda-content-meta">
                        <span>${{act.venue}}</span>
                        <span><strong style="color:var(--primary);">${{feeLabel(act)}}</strong></span>
                      </div>
                      <p style="font-size:0.8rem; color:var(--text-muted); display:-webkit-box; -webkit-line-clamp:1; -webkit-box-orient:vertical; overflow:hidden;">${{escapeCalendarText(act.description_taigi || ('簡介原文：' + act.description))}}</p>
                    </div>
                    <div class="agenda-actions">
                      <button class="btn btn-primary" style="font-size:0.78rem; justify-content:center;">活動詳情</button>
                      <a href="${{act.gcal_url}}" target="_blank" class="btn btn-light" style="font-size:0.75rem; justify-content:center; color:var(--text-main); border-color:var(--border-color);" onclick="event.stopPropagation();">加日曆</a>
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

    function cityClass(city) {{
      return {{ '臺北市': 'city-taipei', '新北市': 'city-newtaipei', '桃園市': 'city-taoyuan' }}[city] || '';
    }}

    function escapeCalendarText(value) {{
      return String(value ?? '').replace(/[&<>"']/g, ch => ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }}[ch]));
    }}

    function taipeiDateKey(date = new Date()) {{
      const parts = new Intl.DateTimeFormat('en-CA', {{ timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit' }}).formatToParts(date);
      const part = type => parts.find(p => p.type === type).value;
      return `${{part('year')}}-${{part('month')}}-${{part('day')}}`;
    }}

    function weekStart(date) {{
      const start = new Date(date);
      start.setUTCDate(start.getUTCDate() - (start.getUTCDay() + 6) % 7);
      return start;
    }}

    function renderCalendar() {{
      const start = weekStart(calDate);
      const end = new Date(start);
      end.setUTCDate(end.getUTCDate() + 6);
      const label = date => formatCalendarDate(date.toISOString().slice(0, 10), false);
      document.getElementById('calCurrentWeekLabel').innerText = `${{label(start)}} – ${{label(end)}}`;
      const filtered = getFilteredActivities().slice().sort((a, b) => new Date(a.start_time) - new Date(b.start_time) || a.id.localeCompare(b.id));
      const today = taipeiDateKey();
      const weekdays = ['拜一', '拜二', '拜三', '拜四', '拜五', '拜六', '禮拜'];
      const time = iso => new Intl.DateTimeFormat('zh-TW', {{ timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }}).format(new Date(iso));
      let html = '';
      let strip = '';
      let weekCount = 0;
      for (let i = 0; i < 7; i++) {{
        const day = new Date(start);
        day.setUTCDate(day.getUTCDate() + i);
        const dateKey = day.toISOString().slice(0, 10);
        strip += `<div>${{weekdays[i]}}<strong>${{day.getUTCDate()}}</strong></div>`;
        const dayEvents = filtered.filter(a => taipeiDateKey(new Date(a.start_time)) === dateKey);
        weekCount += dayEvents.length;
        html += `
          <section class="cal-cell ${{dateKey === today ? 'today' : ''}}" data-date="${{dateKey}}" aria-label="${{dateKey}} ${{weekdays[i]}}">
            <div class="cal-cell-header">
              <h3 class="cal-date-num">${{formatCalendarDate(dateKey)}}</h3>
              <span class="cal-day-count">${{dayEvents.length}} 場</span>
              ${{dateKey === today ? '<span class="cal-today-label">今仔日</span>' : ''}}
            </div>
            <div class="cal-events-list">
              ${{dayEvents.length ? dayEvents.map(activityCard).join('') : '<p class="cal-empty">這工猶無合條件的核實場次</p>'}}
            </div>
          </section>`;
      }}
      document.getElementById('calWeekDays').innerHTML = strip;
      document.getElementById('calGridDays').innerHTML = html;
      document.getElementById('calWeekSummary').innerText = weekCount ? `這禮拜 ${{weekCount}} 場・臺北時間` : '這禮拜猶無合條件的核實場次，會當換禮拜抑是改揀條件';
    }}

    function prevWeek() {{
      calDate.setUTCDate(calDate.getUTCDate() - 7);
      renderCalendar();
    }}

    function nextWeek() {{
      calDate.setUTCDate(calDate.getUTCDate() + 7);
      renderCalendar();
    }}

    function goToToday() {{
      calDate = new Date(taipeiDateKey() + 'T00:00:00Z');
      renderCalendar();
    }}

    function openModal(actId) {{
      const act = ACTIVITIES_DATA.find(a => a.id === actId);
      if (!act) return;
      selectedActivity = act;

      document.getElementById('modalImg').src = act.cover_image || '';
      document.getElementById('modalImg').parentElement.style.display = act.cover_image ? '' : 'none';
      document.getElementById('modalCity').className = 'badge badge-city ' + cityClass(act.city);
      document.getElementById('modalCity').innerText = '📍 ' + act.city + (act.district ? ` (${{act.district}})` : '');
      document.getElementById('modalCategory').innerText = categoryLabel(act.category);
      document.getElementById('modalPlatform').innerText = '🌐 ' + act.source_platform;
      document.getElementById('modalTitle').innerText = act.title_taigi || act.title;
      document.getElementById('modalTime').innerText = formatEventTime(act.start_time, act.end_time);
      document.getElementById('modalVenue').innerText = act.venue + (act.address ? ` (${{act.address}})` : '');
      document.getElementById('modalOrganizer').innerText = act.organizer;
      document.getElementById('modalPrice').innerText = act.price_info_taigi || '所費說明猶待整理';
      document.getElementById('modalDesc').innerText = (act.description_taigi || '活動紹介猶待整理') + '\\n\\n官方資料確認：' + act.raw_metadata.verified_at.slice(0, 10) + '。欲出門進前，請閣看一擺官方最新公告。';

      const cleanTitle = act.title.replace(/[【】《》「」]/g, ' ').trim();
      const searchQuery = encodeURIComponent(`${{cleanTitle}} ${{act.organizer}} 台語 報名 售票`);
      const googleSearchUrl = `https://www.google.com/search?q=${{searchQuery}}`;

      const ticketBtn = document.getElementById('modalTicketLink');
      ticketBtn.href = act.source_url;
      ticketBtn.textContent = '🌐 活動公告 ↗';
      const registrationBtn = document.getElementById('modalRegistrationLink');
      if (act.registration_url && act.registration_url !== act.source_url) {{
        registrationBtn.href = act.registration_url;
        registrationBtn.hidden = false;
      }} else {{
        registrationBtn.href = '#';
        registrationBtn.hidden = true;
      }}

      document.getElementById('modalGoogleSearchLink').href = googleSearchUrl;
      document.getElementById('modalGoogleSearchLink').innerHTML = '🔍 Google 揣報名／買票 ↗';
      document.getElementById('modalGCalLink').href = act.gcal_url;
      // A real calendar URL lets iPhone Safari hand off to Calendar instead of
      // trying to download a temporary blob. The standalone HTML uses the live site.
      const appleBtn = document.getElementById('modalSingleIcsBtn');
      const lineCalendarHelp = document.getElementById('lineCalendarHelp');
      if (isLineIOSBrowser()) {{
        appleBtn.href = externalPageForActivity(act.id);
        appleBtn.textContent = '🍏 用 Safari 加到 Apple 日曆';
        lineCalendarHelp.hidden = false;
      }} else {{
        appleBtn.href =
          (location.protocol === 'file:' ? 'https://jialiangni.github.io/taigi_activities/' : '') + act.ics_path + '?v=plain-notes-2';
        appleBtn.textContent = '🍏 加到 Apple 日曆 (.ics)';
        lineCalendarHelp.hidden = true;
      }}
      document.getElementById('modalMapLink').href = `https://www.google.com/maps/search/?api=1&query=${{encodeURIComponent(act.venue + ' ' + act.address)}}`;

      openOverlay('eventModal');
    }}

    function closeModal() {{
      closeOverlay('eventModal');
    }}

    function closeModalOnBackdrop(e) {{
      if (e.target.classList.contains('modal-overlay')) closeOverlay(e.target.id);
    }}

    function openSyncModal() {{
      openOverlay('syncModal');
    }}

    function closeSyncModal() {{
      closeOverlay('syncModal');
    }}

    function openOverlay(id) {{
      const dialog = document.getElementById(id);
      dialog.showModal();
      dialog.classList.add('active');
      dialog.querySelector('.modal-dialog').scrollTop = 0;
      document.body.style.overflow = 'hidden';
    }}

    function closeOverlay(id) {{
      const dialog = document.getElementById(id);
      dialog.classList.remove('active');
      dialog.close();
      document.body.style.overflow = '';
      if (id === 'eventModal') selectedActivity = null;
      if (id === 'filterModal') {{
        document.querySelector('.controls-container').appendChild(document.getElementById('advancedFilters'));
      }}
    }}

    function openFilterModal() {{
      document.getElementById('mobileFilterHost').appendChild(document.getElementById('advancedFilters'));
      openOverlay('filterModal');
    }}

    function closeFilterModal() {{ closeOverlay('filterModal'); }}

    function resetExtraFilters() {{
      currentPlatform = currentCategory = currentPrice = 'all';
      for (const id of ['sourceFilter', 'categoryFilter', 'priceFilter']) document.getElementById(id).value = 'all';
      renderAll();
    }}

    // Android & Mobile Share API
    function shareCurrentActivity() {{
      if (!selectedActivity) return;
      const act = selectedActivity;
      const shareData = {{
        title: act.title_taigi || act.title,
        text: `【${{categoryLabel(act.category)}}】${{act.title_taigi || act.title}}\\n時間：${{formatDateDisplay(act.start_time)}}\\n所在：${{act.venue}}\\n來做伙講台語！`,
        url: window.location.href
      }};

      if (navigator.share) {{
        navigator.share(shareData).catch(() => {{}});
      }} else {{
        // Fallback: Copy to clipboard
        navigator.clipboard.writeText(`${{shareData.title}}\\n${{shareData.url}}`);
        alert('活動資訊已經複製到剪貼簿，會當直接貼到 LINE 分享！');
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

  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
