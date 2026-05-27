from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

BASE = "https://www.xemlicham.com"
MONTH_URL = BASE + "/am-lich/nam/{year}/thang/{month}"
DAY_URL = BASE + "/am-lich/nam/{year}/thang/{month}/ngay/{day}"
FILE_PATTERN = re.compile(r"du_lieu_ngay_tot_xau_(\d{4})\.json$")
CAN_CHI_REGEX = re.compile(r"Ngày\s+(.+?)\s+tháng\s+(.+?)\s+năm\s+(.+?)(?:\n|$)", re.IGNORECASE)
DAY_LINK_REGEX = r"/am-lich/nam/{year}/thang/{month}/ngay/(\d{{1,2}})"

EMPTY_CAN_CHI = {"ngay": "", "thang": "", "nam": ""}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True)
    p.add_argument("--year", type=int)
    p.add_argument("--start-year", type=int)
    p.add_argument("--end-year", type=int)
    p.add_argument("--sleep", type=float, default=0.2)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--run-tests", action="store_true")
    return p.parse_args()


def parse_can_chi_from_text(text: str) -> Dict[str, str]:
    m = CAN_CHI_REGEX.search(text)
    if not m:
        return dict(EMPTY_CAN_CHI)
    return {"ngay": m.group(1).strip(), "thang": m.group(2).strip(), "nam": m.group(3).strip()}


def parse_day_quality_from_month_html(html: str, year: int, month: int) -> Tuple[Set[int], Set[int]]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    def section(pattern: str) -> str:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1) if m else ""

    good_block = section(rf"Ngày\s+tốt\s+tháng\s+{month}\s*\(Hoàng\s*Đạo\)(.*?)(?:Ngày\s*xấu\s+tháng\s+{month}\s*\(Hắc\s*Đạo\)|$)")
    bad_block = section(rf"Ngày\s*xấu\s+tháng\s+{month}\s*\(Hắc\s*Đạo\)(.*?)(?:Lịch\s+âm|$)")

    good_days: Set[int] = set()
    bad_days: Set[int] = set()

    href_re = re.compile(DAY_LINK_REGEX.format(year=year, month=month))
    text_re = re.compile(rf"Ngày\s+(\d{{1,2}})\s+tháng\s+{month}\s+năm\s+{year}", re.IGNORECASE)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "Ngày tốt" in (a.parent.get_text(" ", strip=True) if a.parent else "") or "Hoàng Đạo" in (a.parent.get_text(" ", strip=True) if a.parent else ""):
            mm = href_re.search(href)
            if mm:
                good_days.add(int(mm.group(1)))
        if "Ngày xấu" in (a.parent.get_text(" ", strip=True) if a.parent else "") or "Hắc Đạo" in (a.parent.get_text(" ", strip=True) if a.parent else ""):
            mm = href_re.search(href)
            if mm:
                bad_days.add(int(mm.group(1)))

    for block, target in [(good_block, good_days), (bad_block, bad_days)]:
        for mm in href_re.finditer(block):
            target.add(int(mm.group(1)))
        for mm in text_re.finditer(block):
            target.add(int(mm.group(1)))

    return good_days, bad_days


class Fetcher:
    def __init__(self, sleep_s: float, timeout: int, max_retries: int):
        self.sleep_s = sleep_s
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.cache: Dict[str, Optional[str]] = {}

    def get(self, url: str) -> Optional[str]:
        if url in self.cache:
            return self.cache[url]
        last_err = None
        for i in range(1, self.max_retries + 1):
            try:
                r = self.session.get(url, headers=HEADERS, timeout=self.timeout)
                if r.status_code == 200 and r.text:
                    self.cache[url] = r.text
                    time.sleep(self.sleep_s)
                    return r.text
                last_err = f"HTTP {r.status_code}"
            except Exception as e:
                last_err = repr(e)
            time.sleep(min(2, self.sleep_s * i))
        print(f"[WARN] fetch failed {url}: {last_err}")
        self.cache[url] = None
        return None


def iter_target_files(input_dir: Path, year: Optional[int], start_year: Optional[int], end_year: Optional[int]) -> Iterable[Tuple[int, Path]]:
    files = sorted(input_dir.glob("du_lieu_ngay_tot_xau_*.json"))
    for path in files:
        m = FILE_PATTERN.search(path.name)
        if not m:
            continue
        y = int(m.group(1))
        if year is not None and y != year:
            continue
        if start_year is not None and y < start_year:
            continue
        if end_year is not None and y > end_year:
            continue
        yield y, path


def enrich_year(path: Path, year: int, fetcher: Fetcher, overwrite: bool, dry_run: bool) -> None:
    print(f"Processing year: {year}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] invalid JSON {path}: {e}")
        return
    if not isinstance(data, dict):
        print(f"[ERROR] JSON root is not object: {path}")
        return

    by_month: Dict[int, list[Tuple[str, dict]]] = defaultdict(list)
    for day_key, day_obj in data.items():
        try:
            dt = datetime.strptime(day_key, "%Y-%m-%d")
        except ValueError:
            continue
        if dt.year != year or not isinstance(day_obj, dict):
            continue
        by_month[dt.month].append((day_key, day_obj))

    stats = {"total_days": 0, "good_count": 0, "bad_count": 0, "normal_count": 0, "can_chi_success_count": 0, "can_chi_failed_count": 0}

    for month, items in sorted(by_month.items()):
        month_html = fetcher.get(MONTH_URL.format(year=year, month=month))
        good_days, bad_days = (set(), set())
        if month_html:
            good_days, bad_days = parse_day_quality_from_month_html(month_html, year, month)
        for day_key, obj in items:
            dt = datetime.strptime(day_key, "%Y-%m-%d")
            d = dt.day
            q = "good" if d in good_days else "bad" if d in bad_days else "normal"
            if overwrite or "day_quality" not in obj:
                obj["day_quality"] = q
            if q == "good":
                stats["good_count"] += 1
            elif q == "bad":
                stats["bad_count"] += 1
            else:
                stats["normal_count"] += 1

            can_chi = dict(EMPTY_CAN_CHI)
            day_html = fetcher.get(DAY_URL.format(year=year, month=month, day=d))
            if day_html:
                can_chi = parse_can_chi_from_text(BeautifulSoup(day_html, "html.parser").get_text("\n", strip=True) + "\n")
            if overwrite or "can_chi" not in obj:
                obj["can_chi"] = can_chi
            if can_chi == EMPTY_CAN_CHI:
                stats["can_chi_failed_count"] += 1
            else:
                stats["can_chi_success_count"] += 1
            stats["total_days"] += 1

    sorted_data = {k: data[k] for k in sorted(data.keys())}
    if not dry_run:
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(json.dumps(sorted_data, ensure_ascii=False, indent=2), encoding="utf-8")

    for k, v in stats.items():
        print(f"{k}: {v}")


def run_tests() -> None:
    s = "Ngày Giáp Tuất tháng Đinh Sửu năm Kỷ Hợi"
    assert parse_can_chi_from_text(s + "\n") == {"ngay": "Giáp Tuất", "thang": "Đinh Sửu", "nam": "Kỷ Hợi"}
    good_days = {1, 2, 6, 8, 13, 14, 18, 20, 25, 26, 30}
    bad_days = {4, 7, 10, 12, 16, 19, 22, 24, 28}
    for d in range(1, 32):
        q = "good" if d in good_days else "bad" if d in bad_days else "normal"
        if d not in good_days and d not in bad_days:
            assert q == "normal"
    print("Tests passed")


def main() -> None:
    args = parse_args()
    if args.run_tests:
        run_tests()
        return
    inp = Path(args.input_dir)
    fetcher = Fetcher(args.sleep, args.timeout, args.max_retries)
    for year, path in iter_target_files(inp, args.year, args.start_year, args.end_year):
        enrich_year(path, year, fetcher, args.overwrite, args.dry_run)


if __name__ == "__main__":
    main()
