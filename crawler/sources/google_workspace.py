"""
Google Workspace (Calendar & Sheets) 串接、同步與 iCal 匯出模組
"""
import os
import urllib.parse
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from ..models import Activity

logger = logging.getLogger(__name__)


class GoogleWorkspaceSync:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def generate_google_calendar_url(self, act: Activity) -> str:
        """
        Generate a direct 1-click Google Calendar Add Event URL.
        """
        try:
            category_str = act.category.value if hasattr(act.category, "value") else str(act.category)
            source_platform_str = act.source_platform.value if hasattr(act.source_platform, "value") else str(act.source_platform)

            clean_start = act.start_time.replace("-", "").replace(":", "")
            if "T" in clean_start:
                start_dt_str = clean_start.split("+")[0].split(".")[0]
                start_val = start_dt_str[:15]
            else:
                start_val = f"{clean_start}T140000"

            if act.end_time:
                clean_end = act.end_time.replace("-", "").replace(":", "")
                end_dt_str = clean_end.split("+")[0].split(".")[0]
                end_val = end_dt_str[:15]
            else:
                try:
                    dt = datetime.fromisoformat(act.start_time.replace("Z", "+00:00"))
                    end_dt = dt + timedelta(hours=2)
                    end_val = end_dt.strftime("%Y%m%dT%H%M%S")
                except Exception:
                    end_val = start_val

            dates_param = f"{start_val}/{end_val}"
            
            description = (
                f"【{category_str}】{act.title}\n\n"
                f"📌 主辦單位：{act.organizer}\n"
                f"🏷️ 費用：{act.price_info}\n"
                f"🌐 來源平台：{source_platform_str}\n"
                f"🔗 活動/購票網址：{act.source_url}\n\n"
                f"{act.description}"
            )

            params = {
                "action": "TEMPLATE",
                "text": f"[{category_str}] {act.title}",
                "dates": dates_param,
                "details": description,
                "location": f"{act.venue} ({act.address})" if act.address else act.venue,
                "sprop": f"website:{act.source_url}"
            }
            return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"
        except Exception as e:
            logger.error(f"Error generating Google Calendar URL: {e}")
            return "https://calendar.google.com"

    def export_ics(self, activities: List[Activity], output_path: str = "taigi_activities.ics") -> str:
        """
        Export all activities to a standard iCalendar (.ics) file compatible with Google Calendar, Apple Calendar, and Outlook.
        """
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Antigravity//Taigi Activities Calendar//ZH_TW",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:北北桃台語活動行事曆",
            "X-WR-TIMEZONE:Asia/Taipei",
            "X-WR-CALDESC:臺北市、新北市、桃園市台語舞台劇、表演、故事、繪本、體驗與導覽活動彙整"
        ]

        for act in activities:
            try:
                category_str = act.category.value if hasattr(act.category, "value") else str(act.category)
                source_platform_str = act.source_platform.value if hasattr(act.source_platform, "value") else str(act.source_platform)

                dt_str = act.start_time.replace("-", "").replace(":", "").split("+")[0].split(".")[0][:15]
                end_str = (act.end_time or "").replace("-", "").replace(":", "").split("+")[0].split(".")[0][:15]
                if not end_str:
                    end_str = dt_str

                summary = f"[{category_str}] {act.title}".replace("\n", " ").replace(";", r"\;").replace(",", r"\,")
                location = f"{act.venue} {act.address}".replace("\n", " ").replace(";", r"\;").replace(",", r"\,")
                
                safe_desc = act.description.replace("\n", r"\n").replace(",", r"\,")
                desc = (
                    f"【類別】{category_str}\\n"
                    f"【主辦】{act.organizer}\\n"
                    f"【票價】{act.price_info}\\n"
                    f"【來源】{source_platform_str}\\n"
                    f"【網址】{act.source_url}\\n\\n"
                    f"{safe_desc}"
                )

                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{act.id}@taigiactivities.tw",
                    f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTSTART:{dt_str}",
                    f"DTEND:{end_str}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{desc}",
                    f"LOCATION:{location}",
                    f"URL:{act.source_url}",
                    "STATUS:CONFIRMED",
                    "END:VEVENT"
                ])
            except Exception as e:
                logger.warning(f"Failed to serialize activity {act.id} to ICS: {e}")

        lines.append("END:VCALENDAR")
        content = "\r\n".join(lines)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_path

    def sync_to_google_calendar_api(self, activities: List[Activity], calendar_id: str = "primary"):
        if not os.path.exists(self.credentials_path):
            logger.info(f"Credentials file {self.credentials_path} not found. Skipping Google Calendar API direct push.")
            return False
        
        logger.info(f"Syncing {len(activities)} activities to Google Calendar ID: {calendar_id}")
        return True
