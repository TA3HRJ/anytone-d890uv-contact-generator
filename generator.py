"""Anytone D890UV Contact List Generator — radioid.net to CPS-compatible CSV."""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from unidecode import unidecode

DMR_URL = "https://radioid.net/static/user.csv"
NXDN_URL = "https://radioid.net/static/nxdn.csv"

# Bir önceki başarılı çalışmanın sayıları; kaynak bozulduğunda karşılaştırma tabanı.
BASELINE_STATS_URL = "https://ta3hrj.github.io/anytone-d890uv-contact-generator/stats.json"

DOWNLOAD_TIMEOUT = 120
BASELINE_TIMEOUT = 30

# Listeler bir gecede bu oranın altına düşmez; düşüyorsa kaynak bozulmuştur.
MIN_RATIO = 0.80

# Taban yoksa (ilk çalışma, Pages erişilemiyor) mutlak alt sınır.
ABSOLUTE_FLOORS = {"dmr_world": 200_000, "nxdn_world": 10_000}

NAME_MAX_LEN = 16
OUTPUT_DIR = Path(__file__).parent / "output"

# radioid.net'te aynı ülke birden çok yazımla geçiyor; hepsi burada olmak zorunda.
# Karşılaştırma normalize edilerek yapılır (bkz. normalize_country).
EUROPE_COUNTRIES = {
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
    "Bosnia and Herzegovina", "Bosnia and Hercegovina", "Bulgaria", "Corsica",
    "Croatia", "Cyprus", "Czech Republic", "Czechia", "Denmark", "Estonia",
    "Faroe Islands", "Finland", "France", "Georgia", "Germany", "Gibraltar",
    "Greece", "Greenland", "Hungary", "Iceland", "Ireland", "Isle of Man", "Italy",
    "Kazakhstan", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg",
    "Luxemburg", "Macedonia", "Malta", "Moldova", "Monaco", "Montenegro",
    "Netherlands", "North Macedonia", "Norway", "Poland", "Portugal", "Romania",
    "Russia", "Aland Islands", "Aaland Islands", "San Marino", "Serbia", "Slovakia",
    "Slovenia", "Spain", "Sweden", "Switzerland", "Turkiye", "Turkey", "Ukraine",
    "United Kingdom", "Vatican City",
}

TURKEY_COUNTRIES = {"Turkey", "Turkiye"}

DMR_HEADER = ["No.", "Radio ID", "Callsign", "Name", "City", "State", "Country",
              "Remarks", "Call Type", "Call Alert"]
NXDN_HEADER = ["RADIO_ID", "CALLSIGN", "FIRST_NAME", "LAST_NAME", "CITY", "STATE",
               "COUNTRY", "Attr", "TxForbid", "Ring"]


def normalize_country(value: str) -> str:
    return " ".join(unidecode(value).lower().replace(".", " ").split())


EUROPE_NORMALIZED = {normalize_country(c) for c in EUROPE_COUNTRIES}
TURKEY_NORMALIZED = {normalize_country(c) for c in TURKEY_COUNTRIES}


def is_european_country(country: str) -> bool:
    return normalize_country(country) in EUROPE_NORMALIZED


def is_turkish_country(country: str) -> bool:
    return normalize_country(country) in TURKEY_NORMALIZED


def is_european_id(radio_id: str) -> bool:
    """DMR ID'sinin ilk üç hanesi MCC ülke kodudur; 2xx bloğu tamamen Avrupa'ya ayrılmış.

    Ülke adına bakmaktan sağlam: radioid.net yazımı değiştirince kırılmıyor.
    """
    return len(radio_id) == 7 and radio_id.startswith("2")


def is_turkish_id(radio_id: str) -> bool:
    """MCC 286 = Türkiye."""
    return len(radio_id) == 7 and radio_id.startswith("286")


def download(url: str, label: str, timeout: int = DOWNLOAD_TIMEOUT) -> str:
    print(f"Downloading {label}...", end=" ", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "AnytoneContactGen/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print("FAILED.")
        sys.exit(f"ERROR: {label} could not be downloaded: {exc}")
    print("done.")
    return data


def require_csv(raw: str, label: str, required_columns: list[str]) -> str:
    """radioid.net 200 ile HTML hata sayfası döndürebiliyor; öyleyse burada dur."""
    header = raw.split("\n", 1)[0] if raw else ""
    missing = [c for c in required_columns if c not in header]
    if missing:
        preview = header[:120].replace("\r", "")
        sys.exit(f"ERROR: {label} is not the expected CSV "
                 f"(missing columns: {', '.join(missing)}; got: {preview!r})")
    return raw


def truncate_name(name: str) -> str:
    if len(name) <= NAME_MAX_LEN:
        return name
    truncated = name[:NAME_MAX_LEN]
    last_space = truncated.rfind(" ")
    if last_space > NAME_MAX_LEN // 2:
        return truncated[:last_space]
    return truncated


def normalize_case(value: str) -> str:
    """CAPS LOCK ile ya da tamamen küçük harfle girilmiş parçaları düzeltir.

    radioid.net kayıtlarının bir kısmı "ESMERALDO", bir kısmı "adriano" biçiminde;
    telsiz listesinde bunlar yan yana durunca dağınık görünüyor.

    Dokunulmayanlar, ikisi de gerçek veride ölçüldü:
    - Karışık kutulu parçalar (McDonald, MacKenzie, LaSalle) — zaten doğru yazılmış,
      düzleştirmek bozardı.
    - Rakam içeren parçalar — isim alanına yazılmış çağrı işaretleri (K2BSA, SV8JNL).

    Baş harfler ayrı bir kural istemiyor: title() tek harfi olduğu gibi bırakıyor,
    "J W SMITH" -> "J W Smith".

    Tamamı büyük yazılmış bir ad zaten kendi iç kutulamasını kaybetmiş durumda;
    "MCDONALD" buradan "Mcdonald" çıkar, "McDonald" değil. Bilgi kaynakta yok.
    """
    parts = []
    for token in value.split():
        letters = [c for c in token if c.isalpha()]
        uniform = (all(c.isupper() for c in letters)
                   or all(c.islower() for c in letters))
        if uniform and not any(c.isdigit() for c in token):
            parts.append(token.title())
        else:
            parts.append(token)
    return " ".join(parts)


def clean_name(first: str, last: str) -> str:
    parts = []
    if first.strip():
        parts.append(first.strip())
    if last.strip():
        parts.append(last.strip())
    combined = " ".join(parts)
    combined = " ".join(combined.split())
    combined = normalize_case(unidecode(combined))
    return truncate_name(combined)


def transliterate_field(value: str) -> str:
    """Ülke adı için kullanılmaz — bölge filtresi ham değere bakıyor."""
    return unidecode(value.strip()) if value.strip() else ""


def clean_place(value: str) -> str:
    """Şehir ve bölge alanları da karışık kutulu geliyor (FORTALEZA, osasco)."""
    return normalize_case(transliterate_field(value))


def parse_dmr(raw: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw))
    seen_ids: set[str] = set()
    records = []
    transliterated = 0
    skipped_dup = 0
    skipped_invalid = 0
    named_from_callsign = 0

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
        if not name:
            # Telsiz ekranında boş satır yerine çağrı işareti görünsün.
            name = truncate_name(unidecode(callsign))
            named_from_callsign += 1

        records.append({
            "radio_id": radio_id,
            "callsign": callsign,
            "name": name,
            "city": clean_place(row.get("CITY", "")),
            "state": clean_place(row.get("STATE", "")),
            "country": transliterate_field(row.get("COUNTRY", "")),
        })

    print(f"  Parsed {len(records):,} DMR records")
    print(f"  Removed {skipped_dup:,} duplicates, {skipped_invalid:,} invalid")
    print(f"  Rewrote {transliterated:,} names (transliteration and capitalisation)")
    print(f"  Used callsign as name for {named_from_callsign:,} records")
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
        first = truncate_name(normalize_case(unidecode(first_raw))) if first_raw else ""
        last = truncate_name(normalize_case(unidecode(last_raw))) if last_raw else ""
        if first != first_raw or last != last_raw:
            transliterated += 1

        records.append({
            "radio_id": radio_id,
            "callsign": row.get("CALLSIGN", "").strip(),
            "first_name": first,
            "last_name": last,
            "city": clean_place(row.get("CITY", "")),
            "state": clean_place(row.get("STATE", "")),
            "country": transliterate_field(row.get("COUNTRY", "")),
        })

    print(f"  Parsed {len(records):,} NXDN records")
    print(f"  Removed {skipped_dup:,} duplicates, {skipped_invalid:,} invalid")
    print(f"  Rewrote {transliterated:,} names (transliteration and capitalisation)")
    return records


def find_country_gaps(dmr_records: list[dict]) -> dict[str, int]:
    """MCC'ye göre Avrupa ama adı listede olmayan ülkeler.

    Bunlar EUROPE_COUNTRIES'e eklenmesi gereken yazımlar. NXDN'de MCC yok,
    orada tek ölçüt ad; bu rapor oradaki sessiz kaybı da haber verir.
    """
    gaps: dict[str, int] = {}
    for r in dmr_records:
        if is_european_id(r["radio_id"]) and not is_european_country(r["country"]):
            gaps[r["country"]] = gaps.get(r["country"], 0) + 1
    return gaps


def report_country_gaps(dmr_records: list[dict]) -> None:
    gaps = find_country_gaps(dmr_records)
    if not gaps:
        return
    print("  WARNING: MCC says Europe but the country name is unknown "
          "(add these spellings to EUROPE_COUNTRIES):")
    for name, count in sorted(gaps.items(), key=lambda kv: -kv[1])[:10]:
        print(f"    {name or '(empty)'}: {count:,}")


def load_baseline() -> dict | None:
    """Karşılaştırma tabanı: önce yerel stats.json, yoksa yayındaki Pages kopyası."""
    local = OUTPUT_DIR / "stats.json"
    if local.exists():
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    try:
        req = urllib.request.Request(BASELINE_STATS_URL,
                                     headers={"User-Agent": "AnytoneContactGen/1.0"})
        with urllib.request.urlopen(req, timeout=BASELINE_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # taban isteğe bağlı; yoksa mutlak sınırlarla devam
        print(f"  Note: baseline stats unavailable ({exc}); using absolute floors only")
        return None


def check_sanity(stats: dict, baseline: dict | None) -> list[str]:
    problems = []
    for key, floor in ABSOLUTE_FLOORS.items():
        if stats.get(key, 0) < floor:
            problems.append(f"{key}={stats.get(key, 0):,} is below the absolute "
                            f"floor {floor:,}")
    if baseline:
        for key, previous in baseline.items():
            if key not in stats or not isinstance(previous, int) or previous <= 0:
                continue
            minimum = int(previous * MIN_RATIO)
            if stats[key] < minimum:
                problems.append(f"{key}={stats[key]:,} dropped below {MIN_RATIO:.0%} "
                                f"of the previous run ({previous:,}, minimum {minimum:,})")
    return problems


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

    dmr_raw = require_csv(download(DMR_URL, "user.csv (DMR)"), "user.csv (DMR)",
                          ["RADIO_ID", "CALLSIGN", "COUNTRY"])
    nxdn_raw = require_csv(download(NXDN_URL, "nxdn.csv (NXDN)"), "nxdn.csv (NXDN)",
                           ["RADIO_ID", "CALLSIGN", "COUNTRY"])

    print("\nProcessing DMR...")
    dmr_records = parse_dmr(dmr_raw)
    report_country_gaps(dmr_records)

    print("\nProcessing NXDN...")
    nxdn_records = parse_nxdn(nxdn_raw)

    # DMR'de birincil ölçüt MCC; ad eşleşmesi yalnızca MCC 2xx dışında kalan
    # Avrupa ülkeleri (Azerbaycan 400, Kazakistan 401) için yedek.
    dmr_turkey = [r for r in dmr_records
                  if is_turkish_id(r["radio_id"]) or is_turkish_country(r["country"])]
    dmr_europe = [r for r in dmr_records
                  if is_european_id(r["radio_id"]) or is_european_country(r["country"])]
    # NXDN ID'leri MCC taşımıyor (1-5 hane), burada tek ölçüt ülke adı.
    nxdn_turkey = [r for r in nxdn_records if is_turkish_country(r["country"])]
    nxdn_europe = [r for r in nxdn_records if is_european_country(r["country"])]

    stats = {
        "dmr_turkey": len(dmr_turkey),
        "dmr_europe": len(dmr_europe),
        "dmr_world": len(dmr_records),
        "nxdn_turkey": len(nxdn_turkey),
        "nxdn_europe": len(nxdn_europe),
        "nxdn_world": len(nxdn_records),
    }

    # Kontrol yazmadan önce: bozuk indirme sağlam dosyaların üzerine yazmasın.
    print("\nChecking record counts...")
    problems = check_sanity(stats, load_baseline())
    if problems:
        for p in problems:
            print(f"  FAIL: {p}")
        sys.exit("ERROR: record counts look wrong; refusing to overwrite existing output.")
    print("  OK")

    print("\nWriting CSV files...")
    write_dmr_csv(dmr_turkey, OUTPUT_DIR / "DMR Digital Contact List - Turkey.csv")
    write_dmr_csv(dmr_europe, OUTPUT_DIR / "DMR Digital Contact List - Europe.csv")
    write_dmr_csv(dmr_records, OUTPUT_DIR / "DMR Digital Contact List - World.csv")
    write_nxdn_csv(nxdn_turkey, OUTPUT_DIR / "NX Digital Contact List - Turkey.csv")
    write_nxdn_csv(nxdn_europe, OUTPUT_DIR / "NX Digital Contact List - Europe.csv")
    write_nxdn_csv(nxdn_records, OUTPUT_DIR / "NX Digital Contact List - World.csv")

    # Üretim tarihi de sayılarla aynı dosyada duruyor; sayfa ikisini tek istekte
    # aldığı için taze tarihin eski sayılarla eşleşmesi artık mümkün değil.
    payload = dict(stats, generated_at=datetime.now(timezone.utc)
                   .strftime("%Y-%m-%d %H:%M UTC"))
    with open(OUTPUT_DIR / "stats.json", "w") as f:
        json.dump(payload, f)

    print("\nDone!")


if __name__ == "__main__":
    main()
