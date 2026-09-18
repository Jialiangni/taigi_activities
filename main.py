"""
北北桃台語活動行事曆 (Taigi Activities Calendar) 主執行程式
自動從 10 大來源抓取活動，並生成單檔 HTML 行事曆與 iCal 檔案
"""
import sys
import logging
from typing import List
from crawler.models import Activity
from crawler.processor import ActivityProcessor
from crawler.sample_data import get_curated_taigi_activities
from crawler.sources.accupass import AccupassCrawler
from crawler.sources.opentix import OpentixCrawler
from crawler.sources.eraticket import EraTicketCrawler
from crawler.sources.li_kang_khiok import LiKangKhiokCrawler
from crawler.sources.le_chang import LeChangCrawler
from crawler.sources.public_libraries import PublicLibrariesCrawler
from crawler.sources.facebook import FacebookCrawler
from crawler.sources.instagram import InstagramCrawler
from crawler.sources.threads import ThreadsCrawler
from crawler.sources.google_workspace import GoogleWorkspaceSync
from build_html import generate_single_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TaigiActivities")


def main():
    logger.info("🚀 開始執行北北桃台語活動資料收集與整合流程...")

    all_activities: List[Activity] = []

    # 1. 載入精選與歷史活動種子資料集 (Taipei, New Taipei, Taoyuan)
    logger.info("📦 載入精選北北桃台語活動資料庫 (李江却、樂暢、公立圖書館、兩廳院等)...")
    sample_activities = get_curated_taigi_activities()
    all_activities.extend(sample_activities)
    logger.info(f"   已載入 {len(sample_activities)} 筆示範/精選台語活動。")

    # 2. 爬取 李江却台語文教基金會
    logger.info("📜 正在查詢 李江却台語文教基金會 活動...")
    try:
        likang_crawler = LiKangKhiokCrawler()
        likang_events = likang_crawler.fetch_activities()
        all_activities.extend(likang_events)
    except Exception as e:
        logger.debug(f"   李江却基金會抓取通知: {e}")

    # 3. 爬取 樂暢親子共學
    logger.info("🎈 正在查詢 樂暢親子共學 台語繪本與體驗...")
    try:
        lechang_crawler = LeChangCrawler()
        lechang_events = lechang_crawler.fetch_activities()
        all_activities.extend(lechang_events)
    except Exception as e:
        logger.debug(f"   樂暢親子共學抓取通知: {e}")

    # 4. 爬取 北北桃市立圖書館 (臺北市立圖書館、新北市立圖書館、桃園市立圖書館)
    logger.info("📖 正在查詢 臺北/新北/桃園 市立圖書館活動...")
    try:
        lib_crawler = PublicLibrariesCrawler()
        lib_events = lib_crawler.fetch_activities()
        all_activities.extend(lib_events)
    except Exception as e:
        logger.debug(f"   市立圖書館抓取通知: {e}")

    # 5. 爬取 Accupass 活動通
    logger.info("🎟️ 正在查詢 Accupass 活動通台語活動...")
    try:
        accupass_crawler = AccupassCrawler()
        acc_events = accupass_crawler.fetch_activities()
        all_activities.extend(acc_events)
        logger.info(f"   Accupass 抓取完成，取得 {len(acc_events)} 筆活動。")
    except Exception as e:
        logger.debug(f"   Accupass 抓取通知: {e}")

    # 6. 爬取 OPENTIX 兩廳院文化生活
    logger.info("🏛️ 正在查詢 OPENTIX 兩廳院文化生活台語劇目...")
    try:
        opentix_crawler = OpentixCrawler()
        opentix_events = opentix_crawler.fetch_activities()
        all_activities.extend(opentix_events)
        logger.info(f"   OPENTIX 抓取完成，取得 {len(opentix_events)} 筆活動。")
    except Exception as e:
        logger.debug(f"   OPENTIX 抓取通知: {e}")

    # 7. 爬取 年代售票
    logger.info("🎫 正在查詢 年代售票表演...")
    try:
        era_crawler = EraTicketCrawler()
        era_events = era_crawler.fetch_activities()
        all_activities.extend(era_events)
    except Exception as e:
        logger.debug(f"   年代售票抓取通知: {e}")

    # 8. 爬取 Facebook, Instagram, Threads
    logger.info("📘 正在查詢 Facebook、📸 Instagram、🧵 Threads 社群活動...")
    try:
        fb_crawler = FacebookCrawler()
        all_activities.extend(fb_crawler.fetch_activities())

        ig_crawler = InstagramCrawler()
        all_activities.extend(ig_crawler.fetch_activities())

        threads_crawler = ThreadsCrawler()
        all_activities.extend(threads_crawler.fetch_activities())
    except Exception as e:
        logger.debug(f"   社群抓取通知: {e}")

    # 9. 資料清洗、去重、地區判定與台語分類器
    logger.info("🧹 進行資料正規化、去重與分類判定...")
    cleaned_activities = ActivityProcessor.clean_and_normalize(all_activities)
    logger.info(f"✨ 彙整完成！共計 {len(cleaned_activities)} 筆有效北北桃台語活動。")

    # 10. 匯出 iCal (.ics) 日曆檔案
    g_sync = GoogleWorkspaceSync()
    ics_path = g_sync.export_ics(cleaned_activities, output_path="taigi_activities.ics")
    logger.info(f"📅 iCal 日曆檔案已產出：{ics_path}")

    # 11. 編譯產出單檔互動式 HTML 行事曆
    logger.info("🎨 正在編譯單檔 HTML 視覺化行事曆 index.html...")
    html_path = generate_single_html(cleaned_activities, output_path="index.html")
    logger.info(f"🎉 成功產出單檔 HTML 行事曆：{html_path}")

    print("\n" + "="*55)
    print("✅ 北北桃台語活動行事曆建置完成！")
    print(f"📄 單檔 HTML 檔案：{html_path}")
    print(f"📆 iCal 訂閱檔案：{ics_path}")
    print(f"📊 總活動數：{len(cleaned_activities)} 場")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
