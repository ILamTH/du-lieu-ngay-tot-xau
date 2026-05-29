from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE = "https://www.xemlicham.com"
MONTH_URL = BASE + "/am-lich/nam/{year}/thang/{month}"
DAY_URL = BASE + "/am-lich/nam/{year}/thang/{month}/ngay/{day}"

FILE_PATTERN = re.compile(r"du_lieu_ngay_tot_xau_(\d{4})\.json$")
DAY_LINK_REGEX = r"/am-lich/nam/{year}/thang/{month}/ngay/(\d{{1,2}})"

EMPTY_CAN_CHI = {"ngay": "", "thang": "", "nam": ""}
DAY_QUALITY_VALUES = {"good", "bad", "normal"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

CAN_PATTERN = r"(?:Giáp|Ất|Bính|Đinh|Mậu|Kỷ|Kỉ|Canh|Tân|Nhâm|Quý)"
CHI_PATTERN = r"(?:Tý|Tí|Sửu|Dần|Mão|Thìn|Tỵ|Tị|Ngọ|Mùi|Thân|Dậu|Tuất|Hợi)"

CAN_CHI_VALUE = rf"{CAN_PATTERN}\s+{CHI_PATTERN}"
MONTH_CAN_CHI_VALUE = rf"{CAN_CHI_VALUE}(?:\s*\(\s*nhuận\s*\))?"

CAN_CHI_FULL_REGEX = re.compile(
    rf"\bNgày\s+({CAN_CHI_VALUE})\s+"
    rf"tháng\s+({MONTH_CAN_CHI_VALUE})\s+"
    rf"năm\s+({CAN_CHI_VALUE})\b",
    re.IGNORECASE,
)

VALID_CAN_CHI_REGEX = re.compile(rf"^{CAN_CHI_VALUE}$", re.IGNORECASE)
VALID_MONTH_CAN_CHI_REGEX = re.compile(rf"^{MONTH_CAN_CHI_VALUE}$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()

    p.add_argument("--input-dir", required=True)
    p.add_argument("--year", type=int)
    p.add_argument("--start-year", type=int)
    p.add_argument("--end-year", type=int)

    p.add_argument("--sleep", type=float, default=0.2)
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--max-retries", type=int, default=3)

    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--run-tests", action="store_true")

    p.add_argument(
        "--quiet",
        action="store_true",
        help="Tắt progress bar và log info. Warning/error vẫn được in.",
    )
    p.add_argument(
        "--no-progress",
        action="store_true",
        help="Không hiển thị tqdm progress bar.",
    )

    return p.parse_args()


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def clean_can_chi(value: str) -> str:
    value = normalize_spaces(value)

    value = re.sub(
        r"\s*\(\s*nhuận\s*\)\s*",
        " (nhuận)",
        value,
        flags=re.IGNORECASE,
    )
    value = normalize_spaces(value)

    replacements = {
        "Kỉ": "Kỷ",
        "kỉ": "Kỷ",
        "Tí": "Tý",
        "tí": "Tý",
        "Tị": "Tỵ",
        "tị": "Tỵ",
    }

    for src, dst in replacements.items():
        value = re.sub(rf"\b{re.escape(src)}\b", dst, value)

    return value


def is_valid_can_chi(value: object) -> bool:
    if not isinstance(value, str):
        return False

    value = clean_can_chi(value)
    return bool(VALID_CAN_CHI_REGEX.fullmatch(value))


def is_valid_month_can_chi(value: object) -> bool:
    if not isinstance(value, str):
        return False

    value = clean_can_chi(value)
    return bool(VALID_MONTH_CAN_CHI_REGEX.fullmatch(value))


def is_valid_can_chi_object(value: object) -> bool:
    if not isinstance(value, dict):
        return False

    return (
        is_valid_can_chi(value.get("ngay"))
        and is_valid_month_can_chi(value.get("thang"))
        and is_valid_can_chi(value.get("nam"))
    )


def build_can_chi(ngay: str, thang: str, nam: str) -> Dict[str, str]:
    ngay = clean_can_chi(ngay)
    thang = clean_can_chi(thang)
    nam = clean_can_chi(nam)

    if not (
        is_valid_can_chi(ngay)
        and is_valid_month_can_chi(thang)
        and is_valid_can_chi(nam)
    ):
        return dict(EMPTY_CAN_CHI)

    return {
        "ngay": ngay,
        "thang": thang,
        "nam": nam,
    }


def parse_can_chi_from_header_text(text: str) -> Dict[str, str]:
    """
    Parse can_chi từ text đã được giới hạn trong block:
      div.row.header-content

    Hỗ trợ:
      Ngày Giáp Tuất tháng Đinh Sửu năm Kỷ Hợi
      Ngày Tân Sửu tháng Ất Dậu (nhuận) năm Canh Tý
    """

    text = normalize_spaces(text)
    m = CAN_CHI_FULL_REGEX.search(text)

    if not m:
        return dict(EMPTY_CAN_CHI)

    return build_can_chi(
        ngay=m.group(1),
        thang=m.group(2),
        nam=m.group(3),
    )


def parse_can_chi_from_html(html: str) -> Dict[str, str]:
    """
    Chỉ lấy Can Chi trong block:
      <div class="row header-content">...</div>

    Không fallback sang block khác để tránh lấy sai dữ liệu.
    """

    soup = BeautifulSoup(html, "html.parser")
    header = soup.select_one("div.row.header-content")

    if header is None:
        return dict(EMPTY_CAN_CHI)

    header_text = header.get_text(" ", strip=True)
    return parse_can_chi_from_header_text(header_text)


def parse_day_quality_from_month_html(
    html: str,
    year: int,
    month: int,
) -> Tuple[Set[int], Set[int]]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    def section(pattern: str) -> str:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1) if m else ""

    good_block = section(
        rf"Ngày\s+tốt\s+tháng\s+{month}\s*\(Hoàng\s*Đạo\)"
        rf"(.*?)"
        rf"(?:Ngày\s+xấu\s+tháng\s+{month}\s*\(Hắc\s*Đạo\)|$)"
    )

    bad_block = section(
        rf"Ngày\s+xấu\s+tháng\s+{month}\s*\(Hắc\s*Đạo\)"
        rf"(.*?)"
        rf"(?:Lịch\s+âm|$)"
    )

    good_days: Set[int] = set()
    bad_days: Set[int] = set()

    href_re = re.compile(DAY_LINK_REGEX.format(year=year, month=month))
    text_re = re.compile(
        rf"Ngày\s+(\d{{1,2}})\s+tháng\s+{month}\s+năm\s+{year}",
        re.IGNORECASE,
    )

    for block, target in [(good_block, good_days), (bad_block, bad_days)]:
        for mm in href_re.finditer(block):
            target.add(int(mm.group(1)))

        for mm in text_re.finditer(block):
            target.add(int(mm.group(1)))

    for a in soup.find_all("a", href=True):
        href = a["href"]

        mm = href_re.search(href)
        if not mm:
            continue

        day = int(mm.group(1))
        parent_text = ""

        if a.parent:
            parent_text = a.parent.get_text(" ", strip=True)

        parent_text = normalize_spaces(parent_text)

        if "Ngày tốt" in parent_text or "Hoàng Đạo" in parent_text:
            good_days.add(day)

        if "Ngày xấu" in parent_text or "Hắc Đạo" in parent_text:
            bad_days.add(day)

    duplicated = good_days & bad_days

    if duplicated:
        tqdm.write(
            f"[WARN] duplicated good/bad days for {year}-{month:02d}: "
            f"{sorted(duplicated)}"
        )
        good_days -= duplicated

    return good_days, bad_days


class Logger:
    def __init__(self, quiet: bool = False):
        self.quiet = quiet

    def info(self, message: str) -> None:
        if not self.quiet:
            tqdm.write(message)

    def warn(self, message: str) -> None:
        tqdm.write(f"[WARN] {message}")

    def error(self, message: str) -> None:
        tqdm.write(f"[ERROR] {message}")


class Fetcher:
    def __init__(
        self,
        sleep_s: float,
        timeout: int,
        max_retries: int,
        logger: Logger,
    ):
        self.sleep_s = sleep_s
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger
        self.session = requests.Session()
        self.cache: Dict[str, Optional[str]] = {}
        self.request_count = 0
        self.cache_hit_count = 0
        self.failed_count = 0

    def get(self, url: str) -> Optional[str]:
        if url in self.cache:
            self.cache_hit_count += 1
            return self.cache[url]

        last_err = None

        for i in range(1, self.max_retries + 1):
            try:
                self.request_count += 1
                r = self.session.get(url, headers=HEADERS, timeout=self.timeout)

                if r.status_code == 200 and r.text:
                    self.cache[url] = r.text
                    time.sleep(self.sleep_s)
                    return r.text

                last_err = f"HTTP {r.status_code}"

            except Exception as e:
                last_err = repr(e)

            time.sleep(min(2, max(0.1, self.sleep_s * i)))

        self.failed_count += 1
        self.logger.warn(f"fetch failed {url}: {last_err}")
        self.cache[url] = None
        return None

    def print_summary(self) -> None:
        self.logger.info("")
        self.logger.info("[FETCH SUMMARY]")
        self.logger.info(f"  requests: {self.request_count}")
        self.logger.info(f"  cache_hits: {self.cache_hit_count}")
        self.logger.info(f"  failed: {self.failed_count}")
        self.logger.info(f"  cached_urls: {len(self.cache)}")


def iter_target_files(
    input_dir: Path,
    year: Optional[int],
    start_year: Optional[int],
    end_year: Optional[int],
) -> Iterable[Tuple[int, Path]]:
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


def get_day_quality(day: int, good_days: Set[int], bad_days: Set[int]) -> str:
    if day in good_days:
        return "good"

    if day in bad_days:
        return "bad"

    return "normal"


def should_update_day_quality(obj: dict, overwrite: bool) -> bool:
    return overwrite or obj.get("day_quality") not in DAY_QUALITY_VALUES


def should_write_parsed_can_chi(
    parsed_can_chi: dict,
    existing_obj: dict,
    overwrite: bool,
) -> bool:
    """
    Can chi từng crawl sai, nên nếu parse được can_chi hợp lệ từ header-content
    thì luôn ghi lại để sửa dữ liệu cũ.

    Nếu parse thất bại:
    - overwrite=True: ghi EMPTY_CAN_CHI
    - overwrite=False: chỉ ghi EMPTY_CAN_CHI nếu field hiện tại thiếu hoặc không hợp lệ.
    """

    if is_valid_can_chi_object(parsed_can_chi):
        return True

    return overwrite or not is_valid_can_chi_object(existing_obj.get("can_chi"))


def load_json_file(path: Path, logger: Logger) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"invalid JSON {path}: {e}")
        return None

    if not isinstance(data, dict):
        logger.error(f"JSON root is not object: {path}")
        return None

    return data


def collect_day_items(
    data: dict,
    year: int,
) -> list[tuple[datetime, str, dict]]:
    items: list[tuple[datetime, str, dict]] = []

    for day_key, day_obj in data.items():
        try:
            dt = datetime.strptime(day_key, "%Y-%m-%d")
        except ValueError:
            continue

        if dt.year != year:
            continue

        if not isinstance(day_obj, dict):
            continue

        items.append((dt, day_key, day_obj))

    items.sort(key=lambda item: item[0])
    return items


def enrich_year(
    path: Path,
    year: int,
    fetcher: Fetcher,
    overwrite: bool,
    dry_run: bool,
    logger: Logger,
    disable_progress: bool,
) -> None:
    started_at = time.time()

    data = load_json_file(path, logger)
    if data is None:
        return

    day_items = collect_day_items(data, year)

    stats = {
        "total_days": 0,
        "good_count": 0,
        "bad_count": 0,
        "normal_count": 0,
        "can_chi_success_count": 0,
        "can_chi_failed_count": 0,
    }

    month_quality_cache: Dict[int, Tuple[Set[int], Set[int]]] = {}

    day_bar = tqdm(
        day_items,
        desc=f"Crawling {year}",
        unit="day",
        leave=False,
        disable=disable_progress,
    )

    for dt, day_key, obj in day_bar:
        month = dt.month
        day = dt.day

        if month not in month_quality_cache:
            day_bar.set_postfix_str(f"loading month={month:02d}", refresh=True)

            month_html = fetcher.get(MONTH_URL.format(year=year, month=month))

            good_days: Set[int] = set()
            bad_days: Set[int] = set()

            if month_html:
                good_days, bad_days = parse_day_quality_from_month_html(
                    month_html,
                    year,
                    month,
                )
            else:
                logger.warn(f"cannot fetch month page: {year}-{month:02d}")

            month_quality_cache[month] = (good_days, bad_days)

        good_days, bad_days = month_quality_cache[month]
        day_quality = get_day_quality(day, good_days, bad_days)

        if should_update_day_quality(obj, overwrite):
            obj["day_quality"] = day_quality

        if day_quality == "good":
            stats["good_count"] += 1
        elif day_quality == "bad":
            stats["bad_count"] += 1
        else:
            stats["normal_count"] += 1

        parsed_can_chi = dict(EMPTY_CAN_CHI)
        day_html = fetcher.get(DAY_URL.format(year=year, month=month, day=day))

        if day_html:
            parsed_can_chi = parse_can_chi_from_html(day_html)
        else:
            logger.warn(f"cannot fetch day page: {day_key}")

        if should_write_parsed_can_chi(parsed_can_chi, obj, overwrite):
            obj["can_chi"] = parsed_can_chi

        final_can_chi = obj.get("can_chi")
        can_chi_ok = is_valid_can_chi_object(final_can_chi)

        if can_chi_ok:
            stats["can_chi_success_count"] += 1
        else:
            stats["can_chi_failed_count"] += 1
            logger.warn(
                f"can_chi parse failed or invalid: "
                f"{day_key} -> {final_can_chi}"
            )

        stats["total_days"] += 1

        day_bar.set_postfix(
            {
                "date": day_key,
                "q": day_quality,
                "can_chi": "ok" if can_chi_ok else "fail",
                "ok": stats["can_chi_success_count"],
                "fail": stats["can_chi_failed_count"],
            },
            refresh=False,
        )

    sorted_data = {k: data[k] for k in sorted(data.keys())}

    if dry_run:
        logger.info(f"[DRY RUN] skip writing file: {path.name}")
    else:
        path.write_text(
            json.dumps(sorted_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    elapsed_s = time.time() - started_at

    logger.info(
        f"[YEAR DONE] {year} | "
        f"days={stats['total_days']} "
        f"good={stats['good_count']} "
        f"bad={stats['bad_count']} "
        f"normal={stats['normal_count']} "
        f"can_chi_ok={stats['can_chi_success_count']} "
        f"can_chi_fail={stats['can_chi_failed_count']} "
        f"elapsed={elapsed_s:.2f}s"
    )


def run_tests() -> None:
    header_text = """
    Lịch âm ngày 1 tháng 1 năm 1900
    lịch vạn niên ngày 1 tháng 1 năm 1900
    Ngày Dương Lịch: 1-1-1900
    Ngày Âm Lịch: 1-12-1899
    Ngày trong tuần: Thứ Hai
    Ngày Giáp Tuất tháng Đinh Sửu năm Kỷ Hợi
    Ngày Chu Tước: xuất hành, cầu tài đều xấu
    ngày 1 tháng 1 năm 1900 ngày 1/1/1900 ngày tốt tháng 1 năm 1900
    """

    assert parse_can_chi_from_header_text(header_text) == {
        "ngay": "Giáp Tuất",
        "thang": "Đinh Sửu",
        "nam": "Kỷ Hợi",
    }

    leap_month_header_text = """
    Lịch âm ngày 10 tháng 10 năm 1960
    Ngày Dương Lịch: 10-10-1960
    Ngày Âm Lịch: 21-8-1960
    Ngày trong tuần: Thứ Hai
    Ngày Tân Sửu tháng Ất Dậu (nhuận) năm Canh Tý
    """

    assert parse_can_chi_from_header_text(leap_month_header_text) == {
        "ngay": "Tân Sửu",
        "thang": "Ất Dậu (nhuận)",
        "nam": "Canh Tý",
    }

    leap_month_no_space_header_text = """
    Ngày Tân Sửu tháng Ất Dậu(nhuận) năm Canh Tý
    """

    assert parse_can_chi_from_header_text(leap_month_no_space_header_text) == {
        "ngay": "Tân Sửu",
        "thang": "Ất Dậu (nhuận)",
        "nam": "Canh Tý",
    }

    html = """
    <html>
      <body>
        <div class="row header-content">
          <h1>Lịch âm ngày 1 tháng 1 năm 1900</h1>
          <p>Ngày Dương Lịch: 1-1-1900</p>
          <p>Ngày Âm Lịch: 1-12-1899</p>
          <p>Ngày trong tuần: Thứ Hai</p>
          <p>Ngày Giáp Tuất tháng Đinh Sửu năm Kỷ Hợi</p>
        </div>

        <div class="other-block">
          <p>Ngày: Quý Dậu - tức Chi sinh Can</p>
          <p>Ngày: Quý Dậu, Tháng: Mậu Tý</p>
        </div>
      </body>
    </html>
    """

    assert parse_can_chi_from_html(html) == {
        "ngay": "Giáp Tuất",
        "thang": "Đinh Sửu",
        "nam": "Kỷ Hợi",
    }

    leap_month_html = """
    <html>
      <body>
        <div class="row header-content">
          <h1>Lịch âm ngày 10 tháng 10 năm 1960</h1>
          <p>Ngày Dương Lịch: 10-10-1960</p>
          <p>Ngày Âm Lịch: 21-8-1960</p>
          <p>Ngày trong tuần: Thứ Hai</p>
          <p>Ngày Tân Sửu tháng Ất Dậu (nhuận) năm Canh Tý</p>
        </div>

        <div class="other-block">
          <p>Ngày: Quý Dậu, Tháng: Mậu Tý</p>
        </div>
      </body>
    </html>
    """

    assert parse_can_chi_from_html(leap_month_html) == {
        "ngay": "Tân Sửu",
        "thang": "Ất Dậu (nhuận)",
        "nam": "Canh Tý",
    }

    html_without_header = """
    <html>
      <body>
        <div class="other-block">
          <p>Ngày Giáp Tuất tháng Đinh Sửu năm Kỷ Hợi</p>
        </div>
      </body>
    </html>
    """

    assert parse_can_chi_from_html(html_without_header) == EMPTY_CAN_CHI

    header_without_can_chi = """
    <html>
      <body>
        <div class="row header-content">
          <h1>Lịch âm ngày 1 tháng 1 năm 1900</h1>
          <p>Ngày Dương Lịch: 1-1-1900</p>
        </div>
      </body>
    </html>
    """

    assert parse_can_chi_from_html(header_without_can_chi) == EMPTY_CAN_CHI

    wrong_title_only = "Lịch âm ngày 1 tháng 1 năm 1900"
    assert parse_can_chi_from_header_text(wrong_title_only) == EMPTY_CAN_CHI

    assert is_valid_can_chi("Giáp Tuất")
    assert is_valid_can_chi("Đinh Sửu")
    assert is_valid_can_chi("Kỷ Hợi")

    assert is_valid_month_can_chi("Ất Dậu")
    assert is_valid_month_can_chi("Ất Dậu (nhuận)")
    assert is_valid_month_can_chi("Ất Dậu(nhuận)")

    assert not is_valid_can_chi("Ất Dậu (nhuận)")
    assert not is_valid_can_chi("1")
    assert not is_valid_can_chi("1900")
    assert not is_valid_can_chi("ngày tốt")

    assert is_valid_can_chi_object(
        {
            "ngay": "Tân Sửu",
            "thang": "Ất Dậu (nhuận)",
            "nam": "Canh Tý",
        }
    )

    good_days = {1, 2, 6, 8, 13, 14, 18, 20, 25, 26, 30}
    bad_days = {4, 7, 10, 12, 16, 19, 22, 24, 28}

    for d in range(1, 32):
        q = get_day_quality(d, good_days, bad_days)

        if d in good_days:
            assert q == "good"
        elif d in bad_days:
            assert q == "bad"
        else:
            assert q == "normal"

    print("Tests passed")


def main() -> None:
    args = parse_args()

    logger = Logger(quiet=args.quiet)

    if args.run_tests:
        run_tests()
        return

    input_dir = Path(args.input_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"input-dir does not exist: {input_dir}")

    target_files = list(
        iter_target_files(
            input_dir,
            args.year,
            args.start_year,
            args.end_year,
        )
    )

    if not target_files:
        logger.warn(
            "No target files found. "
            "Check --input-dir, --year, --start-year, --end-year."
        )
        return

    disable_progress = args.quiet or args.no_progress

    logger.info(f"[START] input_dir={input_dir}")
    logger.info(f"[START] files={len(target_files)}")
    logger.info(f"[START] dry_run={args.dry_run} overwrite={args.overwrite}")
    logger.info(f"[START] progress={not disable_progress}")

    fetcher = Fetcher(
        sleep_s=args.sleep,
        timeout=args.timeout,
        max_retries=args.max_retries,
        logger=logger,
    )

    all_started_at = time.time()

    files_bar = tqdm(
        target_files,
        desc="Files",
        unit="file",
        disable=disable_progress,
    )

    for year, path in files_bar:
        files_bar.set_postfix({"year": year, "file": path.name}, refresh=False)

        enrich_year(
            path=path,
            year=year,
            fetcher=fetcher,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            logger=logger,
            disable_progress=disable_progress,
        )

    fetcher.print_summary()

    logger.info("")
    logger.info(f"[ALL DONE] elapsed={time.time() - all_started_at:.2f}s")


if __name__ == "__main__":
    main()