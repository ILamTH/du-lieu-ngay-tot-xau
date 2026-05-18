"""
Fill empty xemlicham records from web sources.

Workflow:
1. Find days whose 11 target fields are all empty in output_by_year/*.json.
2. Read the lunar date from xemlicham.com for cross-checking.
3. Fetch matching day details from lichamngay.com and map sections into the
   existing output schema.
4. Update only records that are still empty and whose replacement has data.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

from crawl_xemlicham import (
    BASE_URL as XEMLICHAM_URL,
    EMPTY_RECORD,
    HEADERS,
    normalize_text,
    save_year_json,
    year_output_path,
)


OUTPUT_DIR = Path("output_by_year")
SOURCE_NAME = "lichamngay.com"
SOURCE_URL = "https://lichamngay.com/nam-{year}/thang-{month}/lich-am-ngay-{day}-{month}-{year}.html"
LOG_PATH = Path("fill_empty_days_from_web.log.jsonl")
TARGET_KEYS = tuple(EMPTY_RECORD.keys())


def is_empty_record(record: Dict[str, str]) -> bool:
    return all(record.get(key, None) == "" for key in TARGET_KEYS)


def has_enough_data(record: Dict[str, str]) -> bool:
    required = (
        "gio_hoang_dao",
        "gio_hac_dao",
        "cac_ngay_ky",
        "ngu_hanh",
        "banh_to_bach_ky_nhat",
        "khong_minh_luc_dieu",
        "nhi_thap_bat_tu",
        "thap_nhi_kien_tru",
        "ngoc_hap_thong_thu",
        "huong_xuat_hanh",
        "gio_xuat_hanh_theo_ly_thuan_phong",
    )
    return all(record.get(key, "").strip() for key in required)


def clean_section(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"^\s*[:\-\|]+\s*", "", text)
    text = re.sub(r"\n\s*-\s*\n", "\n- ", text)
    text = re.sub(r"\n:\s*", ": ", text)
    return text.strip()


def section_between(text: str, start: str, end_markers: Iterable[str]) -> str:
    start_index = text.find(start)
    if start_index == -1:
        return ""

    content_start = start_index + len(start)
    content_end = len(text)
    for marker in end_markers:
        marker_index = text.find(marker, content_start)
        if marker_index != -1:
            content_end = min(content_end, marker_index)

    return clean_section(text[content_start:content_end])


def get_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return normalize_text(soup.get_text("\n", strip=True))


def find_lunar_date_from_text(text: str) -> Optional[str]:
    match = re.search(
        r"Ngày\s*Âm\s*Lịch\s*:\s*(\d{1,2})-(\d{1,2})-(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    day, month, year = match.groups()
    return f"{int(day)}-{int(month)}-{year}"


def fetch_lunar_date_from_xemlicham(session: requests.Session, target: date) -> Optional[str]:
    url = XEMLICHAM_URL.format(year=target.year, month=target.month, day=target.day)
    response = session.get(url, headers=HEADERS, timeout=25, verify=False)
    response.raise_for_status()
    return find_lunar_date_from_text(get_text(response.text))


def format_hour_section(value: str) -> str:
    value = value.replace(";", " ;")
    value = re.sub(r"\s*;\s*", " ; ", value)
    return clean_section(value).rstrip(" ;")


def parse_lichamngay_record(html: str) -> Tuple[Dict[str, str], Optional[str]]:
    text = get_text(html)
    record = dict(EMPTY_RECORD)

    detail_marker = "CHI TIẾT LỊCH ÂM DƯƠNG"
    detail_start = text.find(detail_marker)
    detail_text = text[detail_start:] if detail_start != -1 else text

    record["gio_hoang_dao"] = format_hour_section(
        section_between(detail_text, "Giờ Hoàng Đạo", ["Giờ Hắc Đạo"])
    )
    record["gio_hac_dao"] = format_hour_section(
        section_between(detail_text, "Giờ Hắc Đạo", ["Chi tiết khung giờ tốt", "Ngày Kỵ"])
    )
    record["cac_ngay_ky"] = section_between(
        detail_text,
        "Ngày Kỵ",
        ["Sao Tốt - Xấu", "Sao Tốt Xấu", "Ngũ hành"],
    )
    record["ngoc_hap_thong_thu"] = section_between(
        detail_text,
        "Sao Tốt - Xấu",
        ["Ngũ hành"],
    ).replace("SAO TỐT", "Sao tốt").replace("SAO XẤU", "Sao xấu")
    record["ngu_hanh"] = section_between(
        detail_text,
        "Ngũ hành",
        ["Bành Tổ Bách Kỵ Nhật"],
    )
    record["banh_to_bach_ky_nhat"] = section_between(
        detail_text,
        "Bành Tổ Bách Kỵ Nhật",
        ["Khổng Minh Lục Diệu"],
    )
    record["khong_minh_luc_dieu"] = section_between(
        detail_text,
        "Khổng Minh Lục Diệu",
        ["Thập Nhị Trực"],
    )
    record["thap_nhi_kien_tru"] = section_between(
        detail_text,
        "Thập Nhị Trực",
        ["Nhị Thập Bát Tú"],
    )
    record["nhi_thap_bat_tu"] = section_between(
        detail_text,
        "Nhị Thập Bát Tú",
        ["Xuất Hành"],
    )

    xuat_hanh = section_between(
        detail_text,
        "Xuất Hành",
        ["Giờ xuất hành theo Lý Thuần Phong", "Việc nên và không nên làm"],
    )
    gio_xuat_hanh = section_between(
        detail_text,
        "Giờ xuất hành theo Lý Thuần Phong",
        ["Cách tính giờ xuất hành", "Việc nên và không nên làm"],
    )
    record["huong_xuat_hanh"] = xuat_hanh
    record["gio_xuat_hanh_theo_ly_thuan_phong"] = gio_xuat_hanh

    return record, find_lunar_date_from_text(text)


def iter_year_files() -> Iterable[Tuple[int, Path]]:
    for path in sorted(OUTPUT_DIR.glob("lunar_calendar_xemlicham_*.json")):
        try:
            year = int(path.stem.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            continue
        yield year, path


def load_year(path: Path) -> Dict[str, Dict[str, str]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_empty_days() -> List[Tuple[int, str]]:
    days: List[Tuple[int, str]] = []
    for year, path in iter_year_files():
        year_data = load_year(path)
        for day_key, record in sorted(year_data.items()):
            if is_empty_record(record):
                days.append((year, day_key))
    return days


def parse_day_key(day_key: str) -> date:
    year, month, day = (int(part) for part in day_key.split("-"))
    return date(year, month, day)


def log_event(event: Dict[str, object]) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


def fill_empty_days(limit: Optional[int], dry_run: bool, delay: float) -> None:
    empty_days = find_empty_days()
    if limit is not None:
        empty_days = empty_days[:limit]

    print(f"Found {len(empty_days)} empty days to fill.")
    if dry_run:
        for _, day_key in empty_days[:50]:
            print(day_key)
        if len(empty_days) > 50:
            print(f"... and {len(empty_days) - 50} more")
        return

    session = requests.Session()
    cache: Dict[int, Dict[str, Dict[str, str]]] = {}
    fixed = 0
    skipped = 0
    failed = 0
    mismatched_lunar = 0

    for year, day_key in tqdm(empty_days, desc="Filling empty days"):
        target = parse_day_key(day_key)
        year_data = cache.get(year)
        if year_data is None:
            year_data = load_year(year_output_path(year))
            cache[year] = year_data

        url = SOURCE_URL.format(year=target.year, month=target.month, day=target.day)
        try:
            xemlicham_lunar = fetch_lunar_date_from_xemlicham(session, target)
            response = session.get(url, headers=HEADERS, timeout=25)
            response.raise_for_status()
            record, source_lunar = parse_lichamngay_record(response.text)

            if xemlicham_lunar and source_lunar and xemlicham_lunar != source_lunar:
                mismatched_lunar += 1
                log_event(
                    {
                        "date": day_key,
                        "status": "lunar_mismatch",
                        "xemlicham_lunar": xemlicham_lunar,
                        "source_lunar": source_lunar,
                        "source": SOURCE_NAME,
                        "url": url,
                    }
                )

            if has_enough_data(record):
                year_data[day_key] = record
                save_year_json(year, year_data)
                fixed += 1
                log_event(
                    {
                        "date": day_key,
                        "status": "fixed",
                        "xemlicham_lunar": xemlicham_lunar,
                        "source_lunar": source_lunar,
                        "source": SOURCE_NAME,
                        "url": url,
                    }
                )
            else:
                skipped += 1
                missing = [key for key in TARGET_KEYS if not record.get(key, "").strip()]
                log_event(
                    {
                        "date": day_key,
                        "status": "missing_fields",
                        "missing": missing,
                        "xemlicham_lunar": xemlicham_lunar,
                        "source_lunar": source_lunar,
                        "source": SOURCE_NAME,
                        "url": url,
                    }
                )
        except Exception as exc:
            failed += 1
            log_event(
                {
                    "date": day_key,
                    "status": "error",
                    "error": repr(exc),
                    "source": SOURCE_NAME,
                    "url": url,
                }
            )

        if delay > 0:
            time.sleep(delay)

    for year, year_data in cache.items():
        save_year_json(year, year_data)

    print("Done.")
    print(f"Fixed: {fixed}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Lunar mismatches: {mismatched_lunar}")
    print(f"Log: {LOG_PATH.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=0.2)
    args = parser.parse_args()

    fill_empty_days(limit=args.limit, dry_run=args.dry_run, delay=args.delay)


if __name__ == "__main__":
    main()
