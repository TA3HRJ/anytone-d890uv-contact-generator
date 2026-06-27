"""Anytone D890UV Contact List Generator — radioid.net to CPS-compatible CSV."""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

from unidecode import unidecode

DMR_URL = "https://radioid.net/static/user.csv"
NXDN_URL = "https://radioid.net/static/nxdn.csv"

NAME_MAX_LEN = 16
OUTPUT_DIR = Path(__file__).parent / "output"

EUROPE_COUNTRIES = {
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
    "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Czechia", "Denmark", "Estonia", "Finland", "France", "Georgia", "Germany",
    "Greece", "Hungary", "Iceland", "Ireland", "Italy", "Kazakhstan", "Kosovo",
    "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta", "Moldova",
    "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway", "Poland",
    "Portugal", "Romania", "Russia", "San Marino", "Serbia", "Slovakia", "Slovenia",
    "Spain", "Sweden", "Switzerland", "Turkiye", "Turkey", "Ukraine",
    "United Kingdom", "Vatican City",
}

DMR_HEADER = ["No.", "Radio ID", "Callsign", "Name", "City", "State", "Country",
              "Remarks", "Call Type", "Call Alert"]
NXDN_HEADER = ["RADIO_ID", "CALLSIGN", "FIRST_NAME", "LAST_NAME", "CITY", "STATE",
               "COUNTRY", "Attr", "TxForbid", "Ring"]


def download(url: str, label: str) -> str:
    print(f"Downloading {label}...", end=" ", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "AnytoneContactGen/1.0"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    print("done.")
    return data


def truncate_name(name: str) -> str:
    if len(name) <= NAME_MAX_LEN:
        return name
    truncated = name[:NAME_MAX_LEN]
    last_space = truncated.rfind(" ")
    if last_space > NAME_MAX_LEN // 2:
        return truncated[:last_space]
    return truncated


def clean_name(first: str, last: str) -> str:
    parts = []
    if first.strip():
        parts.append(first.strip())
    if last.strip():
        parts.append(last.strip())
    combined = " ".join(parts)
    combined = " ".join(combined.split())
    combined = unidecode(combined)
    return truncate_name(combined)


def transliterate_field(value: str) -> str:
    return unidecode(value.strip()) if value.strip() else ""


def parse_dmr(raw: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw))
    seen_ids: set[str] = set()
    records = []
    transliterated = 0
    skipped_dup = 0
    skipped_invalid = 0

    for row in reader:
        radio_id = row.get("RADIO_ID", "").strip()
        if not radio_id.isdigit():
            skipped_invalid += 1
            continue

        if radio_id in seen_ids:
            skipped_dup += 1
            continue
        seen_ids.add(radio_id)

        callsign = row.get("CALLSIGN", "").strip()
        first = row.get("FIRST_NAME", "")
        last = row.get("LAST_NAME", "")
        name_raw = f"{first.strip()} {last.strip()}".strip()
        name = clean_name(first, last)
        if name != name_raw:
            transliterated += 1

        records.append({
            "radio_id": radio_id,
            "callsign": callsign,
            "name": name,
            "city": transliterate_field(row.get("CITY", "")),
            "state": transliterate_field(row.get("STATE", "")),
            "country": transliterate_field(row.get("COUNTRY", "")),
        })

    print(f"  Parsed {len(records):,} DMR records")
    print(f"  Removed {skipped_dup:,} duplicates, {skipped_invalid:,} invalid")
    print(f"  Transliterated {transliterated:,} names")
    return records


def parse_nxdn(raw: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw))
    seen_ids: set[str] = set()
    records = []
    transliterated = 0
    skipped_dup = 0
    skipped_invalid = 0

    for row in reader:
        radio_id = row.get("RADIO_ID", "").strip()
        if not radio_id.isdigit():
            skipped_invalid += 1
            continue

        if radio_id in seen_ids:
            skipped_dup += 1
            continue
        seen_ids.add(radio_id)

        first_raw = row.get("FIRST_NAME", "").strip()
        last_raw = row.get("LAST_NAME", "").strip()
        first = truncate_name(unidecode(first_raw)) if first_raw else ""
        last = truncate_name(unidecode(last_raw)) if last_raw else ""
        if first != first_raw or last != last_raw:
            transliterated += 1

        records.append({
            "radio_id": radio_id,
            "callsign": row.get("CALLSIGN", "").strip(),
            "first_name": first,
            "last_name": last,
            "city": transliterate_field(row.get("CITY", "")),
            "state": transliterate_field(row.get("STATE", "")),
            "country": transliterate_field(row.get("COUNTRY", "")),
        })

    print(f"  Parsed {len(records):,} NXDN records")
    print(f"  Removed {skipped_dup:,} duplicates, {skipped_invalid:,} invalid")
    print(f"  Transliterated {transliterated:,} names")
    return records


def write_dmr_csv(records: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(DMR_HEADER)
        for i, r in enumerate(records, 1):
            writer.writerow([
                str(i), r["radio_id"], r["callsign"], r["name"],
                r["city"], r["state"], r["country"],
                "", "Private Call", "None",
            ])
    print(f"  Generated: {path.name} ({len(records):,} records)")


def write_nxdn_csv(records: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(NXDN_HEADER)
        for r in records:
            writer.writerow([
                r["radio_id"], r["callsign"], r["first_name"], r["last_name"],
                r["city"], r["state"], r["country"],
                "0", "0", "0",
            ])
    print(f"  Generated: {path.name} ({len(records):,} records)")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dmr_raw = download(DMR_URL, "user.csv (DMR)")
    nxdn_raw = download(NXDN_URL, "nxdn.csv (NXDN)")

    print("\nProcessing DMR...")
    dmr_records = parse_dmr(dmr_raw)

    print("\nProcessing NXDN...")
    nxdn_records = parse_nxdn(nxdn_raw)

    turkey_names = {"Turkey", "Turkiye"}
    dmr_turkey = [r for r in dmr_records if r["country"] in turkey_names]
    dmr_europe = [r for r in dmr_records if r["country"] in EUROPE_COUNTRIES]
    nxdn_turkey = [r for r in nxdn_records if r["country"] in turkey_names]
    nxdn_europe = [r for r in nxdn_records if r["country"] in EUROPE_COUNTRIES]

    print("\nWriting CSV files...")
    write_dmr_csv(dmr_turkey, OUTPUT_DIR / "DMR Digital Contact List - Turkey.csv")
    write_dmr_csv(dmr_europe, OUTPUT_DIR / "DMR Digital Contact List - Europe.csv")
    write_dmr_csv(dmr_records, OUTPUT_DIR / "DMR Digital Contact List - World.csv")
    write_nxdn_csv(nxdn_turkey, OUTPUT_DIR / "NX Digital Contact List - Turkey.csv")
    write_nxdn_csv(nxdn_europe, OUTPUT_DIR / "NX Digital Contact List - Europe.csv")
    write_nxdn_csv(nxdn_records, OUTPUT_DIR / "NX Digital Contact List - World.csv")

    print("\nDone!")


if __name__ == "__main__":
    main()
