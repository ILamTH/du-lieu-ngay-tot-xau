import argparse
import json
from pathlib import Path


def split_by_date(input_dir: Path, output_dir: Path, indent: int | None) -> tuple[int, int]:
    year_files = sorted(input_dir.glob("du_lieu_ngay_tot_xau_*.json"))
    if not year_files:
        raise FileNotFoundError(f"No yearly JSON files found in {input_dir}")

    year_count = 0
    day_count = 0

    for year_file in year_files:
        year = year_file.stem.rsplit("_", 1)[-1]
        if not (year.isdigit() and len(year) == 4):
            raise ValueError(f"Cannot parse year from file name: {year_file.name}")

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
        "--compact",
        action="store_true",
        help="Write compact JSON instead of pretty-printed JSON.",
    )
    args = parser.parse_args()

    indent = None if args.compact else 2
    year_count, day_count = split_by_date(args.input_dir, args.output_dir, indent)
    print(f"Split {day_count} day records from {year_count} yearly files into {args.output_dir}")


if __name__ == "__main__":
    main()
