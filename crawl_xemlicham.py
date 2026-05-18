"""
Crawler dữ liệu lịch âm từ xemlicham.com cho giai đoạn 1900-2200.

Cài thư viện:
    pip install requests beautifulsoup4 tqdm

Chạy:
    python crawl_xemlicham_by_year_random.py

Output:
    output_by_year/lunar_calendar_xemlicham_1900.json
    output_by_year/lunar_calendar_xemlicham_1901.json
    ...
    output_by_year/lunar_calendar_xemlicham_2200.json

Checkpoint:
    crawl_checkpoint.jsonl

Điểm khác biệt:
- Output mỗi năm một file JSON.
- Trong mỗi năm, thứ tự ngày/tháng crawl được random để không crawl tuần tự 01/01 -> 31/12.
- Vẫn có delay, retry, checkpoint/resume.
"""

from __future__ import annotations

import json
import random
import re
import time
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE_URL = "https://www.xemlicham.com/am-lich/nam/{year}/thang/{month}/ngay/{day}"

START_YEAR = 1901
END_YEAR = 2200

OUTPUT_DIR = Path("output_by_year")
CHECKPOINT_JSONL = Path("crawl_checkpoint.jsonl")
ERROR_LOG = Path("crawl_errors.jsonl")

REQUEST_TIMEOUT = 25
MIN_DELAY_SECONDS = 0.8
MAX_DELAY_SECONDS = 1.8
MAX_RETRIES = 3

# Set None để random khác nhau mỗi lần chạy.
# Set số cố định, ví dụ 20260506, nếu muốn thứ tự random có thể lặp lại.
RANDOM_SEED = None

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

TARGET_FIELDS = {
    "Giờ Hoàng Đạo": "gio_hoang_dao",
    "Giờ Hắc Đạo": "gio_hac_dao",
    "Các Ngày Kỵ": "cac_ngay_ky",
    "Ngũ Hành": "ngu_hanh",
    "Bành Tổ Bách Kỵ Nhật": "banh_to_bach_ky_nhat",
    "Khổng Minh Lục Diệu": "khong_minh_luc_dieu",
    "Nhị Thập Bát Tú": "nhi_thap_bat_tu",
    "Thập Nhị Kiến Trừ": "thap_nhi_kien_tru",
    "Ngọc Hạp Thông Thư": "ngoc_hap_thong_thu",
    "Hướng xuất hành": "huong_xuat_hanh",
    "Giờ xuất hành Theo Lý Thuần Phong": "gio_xuat_hanh_theo_ly_thuan_phong",
}

EMPTY_RECORD = {
    "gio_hoang_dao": "",
    "gio_hac_dao": "",
    "cac_ngay_ky": "",
    "ngu_hanh": "",
    "banh_to_bach_ky_nhat": "",
    "khong_minh_luc_dieu": "",
    "nhi_thap_bat_tu": "",
    "thap_nhi_kien_tru": "",
    "ngoc_hap_thong_thu": "",
    "huong_xuat_hanh": "",
    "gio_xuat_hanh_theo_ly_thuan_phong": "",
}


def dates_of_year(year: int) -> List[date]:
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)

    random.shuffle(days)
    return days


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def year_output_path(year: int) -> Path:
    return OUTPUT_DIR / f"lunar_calendar_xemlicham_{year}.json"


def load_year_json(year: int) -> Dict[str, Dict[str, str]]:
    path = year_output_path(year)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_year_json(year: int, data: Dict[str, Dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sorted_data = {key: data[key] for key in sorted(data.keys())}
    path = year_output_path(year)

    temp_path = path.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def fetch_html(session: requests.Session, target_date: date) -> Optional[str]:
    url = BASE_URL.format(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200 and response.text:
                return response.text

            last_error = {
                "date": target_date.isoformat(),
                "url": url,
                "attempt": attempt,
                "status_code": response.status_code,
                "message": response.text[:300],
            }

        except Exception as exc:
            last_error = {
                "date": target_date.isoformat(),
                "url": url,
                "attempt": attempt,
                "error": repr(exc),
            }

        time.sleep(1.5 * attempt)

    log_error(last_error or {"date": target_date.isoformat(), "url": url})
    return None


def extract_detail_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    detail = soup.select_one(".vncal-detail")
    if detail:
        detail_text = normalize_text(detail.get_text("\n", strip=True))
        if detail_text:
            return detail_text

    body_text = normalize_text(soup.get_text("\n", strip=True))

    start_markers = [
        "XEM TỐT XẤU NGÀY",
        "Giờ Hoàng Đạo",
    ]

    start_index = -1
    for marker in start_markers:
        start_index = body_text.find(marker)
        if start_index != -1:
            break

    if start_index == -1:
        return ""

    end_markers = [
        "LỊCH ÂM",
        "TIỆN ÍCH ONLINE",
        "VỀ CHÚNG TÔI",
    ]

    end_index = len(body_text)
    for marker in end_markers:
        idx = body_text.find(marker, start_index + 1)
        if idx != -1:
            end_index = min(end_index, idx)

    return normalize_text(body_text[start_index:end_index])


def split_sections(detail_text: str) -> Dict[str, str]:
    record = deepcopy(EMPTY_RECORD)
    if not detail_text:
        return record

    detail_text = re.sub(r"^XEM TỐT XẤU NGÀY[^\n]*\n*", "", detail_text).strip()

    positions = []
    for heading, key in TARGET_FIELDS.items():
        match = re.search(re.escape(heading), detail_text, flags=re.IGNORECASE)
        if match:
            positions.append((match.start(), match.end(), heading, key))

    positions.sort(key=lambda x: x[0])

    for i, (_, end, heading, key) in enumerate(positions):
        next_start = positions[i + 1][0] if i + 1 < len(positions) else len(detail_text)
        value = detail_text[end:next_start]
        value = normalize_text(value)
        value = re.sub(r"^[:\-\s]+", "", value).strip()
        record[key] = value

    return record


def parse_page(html: str) -> Dict[str, str]:
    detail_text = extract_detail_text(html)
    return split_sections(detail_text)


def load_existing_checkpoint() -> Dict[str, Dict[str, str]]:
    data = {}
    if not CHECKPOINT_JSONL.exists():
        return data

    with CHECKPOINT_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                data[item["date"]] = item["data"]
            except Exception:
                continue

    return data


def append_checkpoint(day: str, record: Dict[str, str]) -> None:
    with CHECKPOINT_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"date": day, "data": record}, ensure_ascii=False) + "\n")


def log_error(error: dict) -> None:
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(error, ensure_ascii=False) + "\n")


def rebuild_year_files_from_checkpoint() -> None:
    existing = load_existing_checkpoint()
    grouped: Dict[int, Dict[str, Dict[str, str]]] = {}

    for day_key, record in existing.items():
        year = int(day_key[:4])
        grouped.setdefault(year, {})[day_key] = record

    for year, year_data in grouped.items():
        current_data = load_year_json(year)
        current_data.update(year_data)
        save_year_json(year, current_data)


def main() -> None:
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rebuild_year_files_from_checkpoint()
    existing = load_existing_checkpoint()

    session = requests.Session()

    years = list(range(START_YEAR, END_YEAR + 1))

    # Giữ năm theo thứ tự để output/check dễ theo dõi.
    # Bên trong từng năm, ngày/tháng được random.
    for year in tqdm(years, desc="Years"):
        year_data = load_year_json(year)
        days = dates_of_year(year)

        for current_date in tqdm(days, desc=f"Crawling {year}", leave=False):
            day_key = current_date.isoformat()

            if day_key in year_data or day_key in existing:
                continue

            html = fetch_html(session, current_date)
            if html is None:
                record = deepcopy(EMPTY_RECORD)
            else:
                record = parse_page(html)

            year_data[day_key] = record
            existing[day_key] = record

            append_checkpoint(day_key, record)
            save_year_json(year, year_data)

            time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

        save_year_json(year, year_data)

    print("Done.")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")
    print(f"Checkpoint: {CHECKPOINT_JSONL.resolve()}")
    print(f"Errors: {ERROR_LOG.resolve()}")


if __name__ == "__main__":
    main()
