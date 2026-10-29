import re
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from app.core.logging import setup_logging

logger = setup_logging()

ENVIRONMENT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "environment"
TIMETABLE_DOCX = ENVIRONMENT_DIR / "Weekly_Timetable.docx"
ROOMS_DOCX = ENVIRONMENT_DIR / "Meeting_Room_Facilities.docx"

XML_NAMESPACES = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

ROLE_EMAIL_MAP: dict[str, list[str]] = {
    "students": [
        "aniket@university.com",
        "sujal@university.com",
        "viraj@university.com",
        "sarvesh@university.com",
    ],
    "hod": ["hod@university.com"],
    "principal": ["principal@university.com"],
    "chairman": ["chairman@university.com"],
    "teacher": ["teacher@university.com"],
}


def _extract_text_elements(element: ET.Element) -> list[str]:
    return [t.text for t in element.findall(".//w:t", XML_NAMESPACES) if t.text]


def _parse_time_range(time_str: str) -> tuple[time, time] | None:
    """Parse time string like '9-10 AM', '11 AM-12 PM', '12-1 PM', '1-2 PM', '2-3 PM'."""
    clean = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uff0d-]", "-", time_str).strip()
    match = re.search(r"(\d+)(?::(\d+))?\s*(AM|PM)?\s*-\s*(\d+)(?::(\d+))?\s*(AM|PM)", clean, re.IGNORECASE)
    if not match:
        return None
    start_h, start_m, start_merid, end_h, end_m, end_merid = match.groups()
    sh = int(start_h)
    sm = int(start_m or 0)
    eh = int(end_h)
    em = int(end_m or 0)
    end_merid = end_merid.upper()
    start_merid = start_merid.upper() if start_merid else end_merid

    if start_merid == "PM" and sh != 12:
        sh += 12
    elif start_merid == "AM" and sh == 12:
        sh = 0

    if end_merid == "PM" and eh != 12:
        eh += 12
    elif end_merid == "AM" and eh == 12:
        eh = 0

    return time(sh, sm), time(eh, em)


class EnvironmentDataService:
    """Extracts timetable and room configurations directly from the environment .docx files."""

    def __init__(
        self,
        timetable_path: Path = TIMETABLE_DOCX,
        rooms_path: Path = ROOMS_DOCX,
    ):
        self.timetable_path = timetable_path
        self.rooms_path = rooms_path
        self._timetable_cache: dict[str, list[dict[str, Any]]] | None = None
        self._rooms_cache: list[dict[str, Any]] | None = None

    def get_room_facilities(self) -> list[dict[str, Any]]:
        """Parse Meeting_Room_Facilities.docx to get room list with capabilities."""
        if self._rooms_cache is not None:
            return self._rooms_cache

        if not self.rooms_path.exists():
            logger.warning("Room facilities docx missing at %s, using defaults", self.rooms_path)
            return [
                {"name": "Auditorium", "capacity": 200, "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage", "seating"]},
                {"name": "IoT Lab", "capacity": 40, "equipment": ["projector", "mic", "whiteboard", "stage"]},
                {"name": "STEP Hall", "capacity": 100, "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage"]},
                {"name": "MB 104", "capacity": 60, "equipment": ["projector", "mic", "whiteboard", "stage"]},
            ]

        try:
            with zipfile.ZipFile(self.rooms_path) as z:
                tree = ET.fromstring(z.read("word/document.xml"))
            
            tables = tree.findall(".//w:tbl", XML_NAMESPACES)
            rooms: list[dict[str, Any]] = []
            
            # Default capacities for known rooms per university facilities spec
            default_capacities = {
                "Auditorium": 200,
                "IoT Lab": 40,
                "STEP Hall": 100,
                "MB 104": 60,
            }

            for tbl in tables:
                rows = tbl.findall(".//w:tr", XML_NAMESPACES)
                for tr in rows[1:]:  # Skip header
                    cells = tr.findall(".//w:tc", XML_NAMESPACES)
                    if len(cells) >= 2:
                        name = "".join(_extract_text_elements(cells[0])).strip()
                        raw_fac = "".join(_extract_text_elements(cells[1])).strip()
                        if not name:
                            continue
                        
                        # Normalize equipment tags
                        eq_list: list[str] = []
                        fac_lower = raw_fac.lower()
                        if "projector" in fac_lower:
                            eq_list.append("projector")
                        if "mic" in fac_lower:
                            eq_list.append("mic")
                        if "whiteboard" in fac_lower:
                            eq_list.append("whiteboard")
                        if "video" in fac_lower or "conferencing" in fac_lower:
                            eq_list.append("video_conf")
                        if "stage" in fac_lower:
                            eq_list.append("stage")
                        if "seating" in fac_lower:
                            eq_list.append("seating")

                        rooms.append({
                            "name": name,
                            "capacity": default_capacities.get(name, 50),
                            "equipment": eq_list,
                            "raw_facilities": raw_fac,
                        })

            if not rooms:
                rooms = [
                    {"name": "Auditorium", "capacity": 200, "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage", "seating"]},
                    {"name": "IoT Lab", "capacity": 40, "equipment": ["projector", "mic", "whiteboard", "stage"]},
                    {"name": "STEP Hall", "capacity": 100, "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage"]},
                    {"name": "MB 104", "capacity": 60, "equipment": ["projector", "mic", "whiteboard", "stage"]},
                ]

            self._rooms_cache = rooms
            return rooms
        except Exception as exc:
            logger.exception("Failed to parse rooms docx: %s", exc)
            return [
                {"name": "Auditorium", "capacity": 200, "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage", "seating"]},
                {"name": "IoT Lab", "capacity": 40, "equipment": ["projector", "mic", "whiteboard", "stage"]},
                {"name": "STEP Hall", "capacity": 100, "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage"]},
                {"name": "MB 104", "capacity": 60, "equipment": ["projector", "mic", "whiteboard", "stage"]},
            ]

    def get_weekly_timetable(self) -> dict[str, list[dict[str, Any]]]:
        """Parse Weekly_Timetable.docx into day-based schedules.
        
        Returns:
            dict mapping day name ('MONDAY', etc.) to list of slot dicts:
            [{ 'start_time': time(9, 0), 'end_time': time(10, 0),
               'students': 'Cryptography', 'hod': 'Department Class', ... }]
        """
        if self._timetable_cache is not None:
            return self._timetable_cache

        if not self.timetable_path.exists():
            logger.warning("Weekly timetable docx missing at %s", self.timetable_path)
            return {}

        try:
            with zipfile.ZipFile(self.timetable_path) as z:
                tree = ET.fromstring(z.read("word/document.xml"))

            days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
            tables = tree.findall(".//w:tbl", XML_NAMESPACES)
            result: dict[str, list[dict[str, Any]]] = {}

            for idx, tbl in enumerate(tables):
                if idx >= len(days):
                    break
                day_name = days[idx]
                day_slots: list[dict[str, Any]] = []

                rows = tbl.findall(".//w:tr", XML_NAMESPACES)
                if not rows:
                    continue

                for tr in rows[1:]:  # skip header
                    cells = tr.findall(".//w:tc", XML_NAMESPACES)
                    if len(cells) < 5:
                        continue
                    time_raw = "".join(_extract_text_elements(cells[0])).strip()
                    trange = _parse_time_range(time_raw)
                    if not trange:
                        continue

                    students_act = "".join(_extract_text_elements(cells[1])).strip()
                    hod_act = "".join(_extract_text_elements(cells[2])).strip()
                    principal_act = "".join(_extract_text_elements(cells[3])).strip()
                    chairman_act = "".join(_extract_text_elements(cells[4])).strip()

                    day_slots.append({
                        "start_time": trange[0],
                        "end_time": trange[1],
                        "time_raw": time_raw,
                        "students": students_act,
                        "hod": hod_act,
                        "principal": principal_act,
                        "chairman": chairman_act,
                    })

                result[day_name] = day_slots

            self._timetable_cache = result
            return result
        except Exception as exc:
            logger.exception("Failed to parse weekly timetable docx: %s", exc)
            return {}

    def get_busy_intervals_for_date(
        self,
        target_date: datetime,
        emails: list[str],
    ) -> dict[str, list[dict[str, datetime]]]:
        """Calculate busy intervals for given emails on a specific calendar date using the weekly timetable."""
        # 0 = Monday, ..., 5 = Saturday, 6 = Sunday
        weekday_num = target_date.weekday()
        days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
        busy_result: dict[str, list[dict[str, datetime]]] = {e.lower(): [] for e in emails}

        # Sunday is a complete non-working holiday
        if weekday_num == 6:
            full_day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            full_day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
            for email in emails:
                busy_result[email.lower()].append({
                    "start": full_day_start,
                    "end": full_day_end,
                    "title": "Sunday Holiday (Non-working day)",
                })
            return busy_result

        day_name = days[weekday_num]
        timetable = self.get_weekly_timetable()
        day_schedule = timetable.get(day_name, [])

        date_clean = target_date.date()

        for slot in day_schedule:
            st = datetime.combine(date_clean, slot["start_time"], tzinfo=timezone.utc)
            et = datetime.combine(date_clean, slot["end_time"], tzinfo=timezone.utc)

            for email in emails:
                em = email.lower().strip()
                activity = None

                if em in ROLE_EMAIL_MAP["students"] or "student" in em:
                    activity = slot["students"]
                elif em in ROLE_EMAIL_MAP["hod"]:
                    activity = slot["hod"]
                elif em in ROLE_EMAIL_MAP["principal"]:
                    activity = slot["principal"]
                elif em in ROLE_EMAIL_MAP["chairman"]:
                    activity = slot["chairman"]
                elif em in ROLE_EMAIL_MAP["teacher"]:
                    # Teachers coordinate with HOD / Department classes
                    activity = slot["hod"]

                if activity and activity.upper() != "FREE":
                    busy_result[em].append({
                        "start": st,
                        "end": et,
                        "title": activity,
                    })

        return busy_result


environment_data_service = EnvironmentDataService()
