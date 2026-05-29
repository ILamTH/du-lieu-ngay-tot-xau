import argparse
import json
from pathlib import Path


def parse_year_from_file(year_file: Path) -> int:
    year = year_file.stem.rsplit("_", 1)[-1]

    if not (year.isdigit() and len(year) == 4):
        raise ValueError(f"Cannot parse year from file name: {year_file.name}")

    return int(year)


def should_process_year(
    year: int,
    start_year: int | None,
    end_year: int | None,
) -> bool:
    if start_year is not None and year < start_year:
        return False

    if end_year is not None and year > end_year:
        return False

    return True


def split_by_date(
    input_dir: Path,
    output_dir: Path,
    indent: int | None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> tuple[int, int]:
    year_files = sorted(input_dir.glob("du_lieu_ngay_tot_xau_*.json"))

    if not year_files:
        raise FileNotFoundError(f"No yearly JSON files found in {input_dir}")

    selected_year_files: list[tuple[int, Path]] = []

    for year_file in year_files:
        year = parse_year_from_file(year_file)

        if should_process_year(year, start_year, end_year):
            selected_year_files.append((year, year_file))

    if not selected_year_files:
        raise FileNotFoundError(
            f"No yearly JSON files found in range "
            f"start_year={start_year}, end_year={end_year}"
        )

    year_count = 0
    day_count = 0

    for year_int, year_file in selected_year_files:
        print(year_file)

        year = str(year_int)

        with year_file.open("r", encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, dict):
            raise ValueError(f"Expected object at top level: {year_file}")

        for date_key, record in records.items():
            parts = date_key.split("-")

            if len(parts) != 3:
                raise ValueError(f"Invalid date key {date_key!r} in {year_file}")

            date_year, month, day = parts

            if date_year != year:
                raise ValueError(
                    f"Date key {date_key!r} does not match file year {year} in {year_file}"
                )

            target = output_dir / date_year / month / f"{day}.json"
            target.parent.mkdir(parents=True, exist_ok=True)

            with target.open("w", encoding="utf-8", newline="\n") as f:
                json.dump(record, f, ensure_ascii=False, indent=indent)
                f.write("\n")

            day_count += 1

        year_count += 1

    return year_count, day_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split yearly ngay tot xau JSON files into one JSON file per date."
    )

    parser.add_argument("--input-dir", default="output_by_year", type=Path)
    parser.add_argument("--output-dir", default="output_by_date", type=Path)

    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Only process files from this year, inclusive.",
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Only process files up to this year, inclusive.",
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write compact JSON instead of pretty-printed JSON.",
    )

    args = parser.parse_args()

    if args.start_year is not None and args.end_year is not None:
        if args.start_year > args.end_year:
            raise ValueError(
                f"--start-year must be <= --end-year, got "
                f"{args.start_year} > {args.end_year}"
            )

    indent = None if args.compact else 2

    year_count, day_count = split_by_date(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        indent=indent,
        start_year=args.start_year,
        end_year=args.end_year,
    )

    print(
        f"Split {day_count} day records from {year_count} yearly files "
        f"into {args.output_dir}"
    )


if __name__ == "__main__":
    main()