"""Ekran sınırı, CPS format uyumu ve akıl sağlığı kontrolü için testler.

Bu üçü kırılırsa telsiz tarafında sessizce bozuk çıktı oluşur:
- 16 karakter sınırı aşılırsa isim ekranda taşar,
- sütun sırası kayarsa CPS dosyayı reddeder,
- sayı kontrolü kaçarsa bozuk indirme sağlam listelerin üzerine yazar.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generator as g


# --- 16 karakter kesme sınırı -------------------------------------------------

def test_short_name_untouched():
    assert g.truncate_name("Ahmet Yilmaz") == "Ahmet Yilmaz"


def test_name_exactly_at_limit_untouched():
    name = "A" * g.NAME_MAX_LEN
    assert g.truncate_name(name) == name


def test_long_name_cut_at_word_boundary():
    # "Mehmet Emin Kara" 16, 17. karakter boşluk sonrası -> son kelime düşer
    assert g.truncate_name("Mehmet Emin Karaoglu") == "Mehmet Emin"


def test_single_long_word_cut_hard():
    # Tek kelimede kesilecek boşluk yok, sert kesiliyor
    assert g.truncate_name("Abdurrahmanoglullari") == "Abdurrahmanoglul"


def test_early_space_does_not_leave_stub():
    # Boşluk sınırın ilk yarısındaysa ("Ali " -> 3. karakter) kelimeden kesmek
    # ekranda "Ali" gibi işe yaramaz bir kalıntı bırakır; onun yerine sert kes.
    assert g.truncate_name("Ali Abdurrahmanoglu") == "Ali Abdurrahmano"


@pytest.mark.parametrize("first,last", [
    ("Abdurrahmanoglullarindan", "Mehmetoglu"),
    ("Ali", "Abdurrahmanoglullari"),
    ("Cok Uzun Bir Isim", "Daha Da Uzun Soyisim"),
    ("Дмитрий", "Александрович"),
])
def test_clean_name_never_exceeds_limit(first, last):
    assert len(g.clean_name(first, last)) <= g.NAME_MAX_LEN


# --- ASCII harf çevirisi ------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Çetin", "Cetin"),
    ("Güneş", "Gunes"),
    ("Müller", "Muller"),
    ("José", "Jose"),
])
def test_clean_name_transliterates(raw, expected):
    assert g.clean_name(raw, "") == expected


def test_clean_name_collapses_whitespace():
    assert g.clean_name("  Ali   ", "  Veli  ") == "Ali Veli"


def test_clean_name_is_ascii_for_cyrillic():
    assert g.clean_name("Дмитрий", "").isascii()


# --- Ülke eşleşmesi -----------------------------------------------------------

@pytest.mark.parametrize("spelling", [
    "Bosnia and Hercegovina",  # radioid.net bu yazımı kullanıyor
    "Bosnia and Herzegovina",
    "Luxemburg",
    "Luxembourg",
    "Macedonia",
    "North Macedonia",
    "Corsica",
    "Gibraltar",
    "Faroe Islands",
    "Aaland Islands",
    "TURKIYE",
    " Germany ",
])
def test_known_european_spellings_match(spelling):
    assert g.is_european_country(spelling)


@pytest.mark.parametrize("country", ["United States", "China", "Brazil", "", "Japan"])
def test_non_european_countries_do_not_match(country):
    assert not g.is_european_country(country)


def test_turkey_spellings():
    assert g.is_turkish_country("Turkiye")
    assert g.is_turkish_country("Turkey")
    assert not g.is_turkish_country("Turkmenistan")


# --- MCC ön eki ---------------------------------------------------------------

@pytest.mark.parametrize("radio_id", ["2860001", "2620123", "2350001", "2500001"])
def test_european_mcc_ids(radio_id):
    assert g.is_european_id(radio_id)


@pytest.mark.parametrize("radio_id", ["3100001", "5050001", "7220001", "286", "28600012"])
def test_non_european_mcc_ids(radio_id):
    assert not g.is_european_id(radio_id)


def test_turkish_mcc_id():
    assert g.is_turkish_id("2860001")
    assert not g.is_turkish_id("2620001")
    assert not g.is_turkish_id("286000")  # 7 haneden kısa


def test_country_gap_report_finds_unknown_spelling():
    records = [
        {"radio_id": "2990001", "country": "Ruritania"},
        {"radio_id": "2990002", "country": "Ruritania"},
        {"radio_id": "2860001", "country": "Turkiye"},
        {"radio_id": "3100001", "country": "United States"},
    ]
    assert g.find_country_gaps(records) == {"Ruritania": 2}


# --- CPS format uyumu ---------------------------------------------------------

def test_dmr_header_is_exact():
    # Sütun sırası veya başlık değişirse CPS dosyayı reddeder.
    assert g.DMR_HEADER == [
        "No.", "Radio ID", "Callsign", "Name", "City", "State", "Country",
        "Remarks", "Call Type", "Call Alert",
    ]


def test_nxdn_header_is_exact():
    assert g.NXDN_HEADER == [
        "RADIO_ID", "CALLSIGN", "FIRST_NAME", "LAST_NAME", "CITY", "STATE",
        "COUNTRY", "Attr", "TxForbid", "Ring",
    ]


def _dmr_record(**over):
    base = {"radio_id": "2860001", "callsign": "TA3HRJ", "name": "Erhan",
            "city": "Izmir", "state": "", "country": "Turkiye"}
    base.update(over)
    return base


def test_dmr_csv_layout(tmp_path):
    path = tmp_path / "dmr.csv"
    g.write_dmr_csv([_dmr_record(), _dmr_record(radio_id="2860002")], path)
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == g.DMR_HEADER
    assert rows[1] == ["1", "2860001", "TA3HRJ", "Erhan", "Izmir", "", "Turkiye",
                       "", "Private Call", "None"]
    assert rows[2][0] == "2"  # No. sütunu 1'den artıyor


def test_dmr_csv_quotes_every_field(tmp_path):
    path = tmp_path / "dmr.csv"
    g.write_dmr_csv([_dmr_record()], path)
    first_line = path.read_text(encoding="utf-8").splitlines()[1]
    assert first_line.startswith('"1","2860001"')
    assert first_line.count('"') == 20  # 10 sütun x 2 tırnak


def test_nxdn_csv_layout(tmp_path):
    path = tmp_path / "nx.csv"
    g.write_nxdn_csv([{"radio_id": "615", "callsign": "TA1SA", "first_name": "Yener",
                       "last_name": "", "city": "Istanbul", "state": "Marmara",
                       "country": "Turkiye"}], path)
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == g.NXDN_HEADER
    assert rows[1] == ["615", "TA1SA", "Yener", "", "Istanbul", "Marmara",
                       "Turkiye", "0", "0", "0"]


def test_csv_uses_crlf(tmp_path):
    # CPS satır sonu olarak CRLF bekliyor; newline="" + csv modülü bunu üretir.
    path = tmp_path / "dmr.csv"
    g.write_dmr_csv([_dmr_record()], path)
    assert path.read_bytes().count(b"\r\n") == 2


# --- Akıl sağlığı kontrolü ----------------------------------------------------

GOOD = {"dmr_turkey": 8342, "dmr_europe": 112901, "dmr_world": 311401,
        "nxdn_turkey": 629, "nxdn_europe": 5965, "nxdn_world": 17434}


def test_sanity_passes_on_normal_growth():
    grown = {k: v + 100 for k, v in GOOD.items()}
    assert g.check_sanity(grown, GOOD) == []


def test_sanity_passes_on_small_drop():
    # Silinen ID'ler yüzünden küçük düşüşler normal
    slightly_lower = {k: int(v * 0.95) for k, v in GOOD.items()}
    assert g.check_sanity(slightly_lower, GOOD) == []


def test_sanity_catches_empty_download():
    empty = {k: 0 for k in GOOD}
    problems = g.check_sanity(empty, GOOD)
    assert problems
    assert any("dmr_world" in p for p in problems)


def test_sanity_catches_half_sized_list():
    halved = dict(GOOD, dmr_europe=GOOD["dmr_europe"] // 2)
    assert any("dmr_europe" in p for p in g.check_sanity(halved, GOOD))


def test_absolute_floor_applies_without_baseline():
    assert g.check_sanity({k: 0 for k in GOOD}, None)
    assert g.check_sanity(GOOD, None) == []


def test_baseline_with_unexpected_keys_is_ignored():
    # Taban ileride yeni anahtar kazanırsa kontrol patlamamalı
    baseline = dict(GOOD, generated_at="2026-09-07")
    assert g.check_sanity(GOOD, baseline) == []


# --- Girdi doğrulama ----------------------------------------------------------

def test_require_csv_accepts_real_header():
    raw = "RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n1,TA3HRJ,,,,,\n"
    assert g.require_csv(raw, "test", ["RADIO_ID", "CALLSIGN", "COUNTRY"]) == raw


def test_require_csv_rejects_html_error_page():
    # radioid.net 200 ile HTML dönebiliyor; bu durum sessizce 0 kayda dönüşmemeli
    with pytest.raises(SystemExit):
        g.require_csv("<!DOCTYPE html><html><body>503</body></html>", "test",
                      ["RADIO_ID", "CALLSIGN", "COUNTRY"])


def test_require_csv_rejects_empty_body():
    with pytest.raises(SystemExit):
        g.require_csv("", "test", ["RADIO_ID"])


# --- Ayrıştırma ---------------------------------------------------------------

DMR_SAMPLE = (
    "RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n"
    "2860001,TA3HRJ,Erhan,Özkan,İzmir,,Turkiye\n"
    "2860001,TA3HRJ,Erhan,Özkan,İzmir,,Turkiye\n"       # yinelenen ID
    "notanid,XX0XXX,Bad,Row,,,Nowhere\n"                # geçersiz ID
    "2621234,DL1ABC,Jürgen,Müller,München,,Germany\n"
)


def test_parse_dmr_drops_duplicates_and_invalid_rows():
    records = g.parse_dmr(DMR_SAMPLE)
    assert [r["radio_id"] for r in records] == ["2860001", "2621234"]


def test_parse_dmr_transliterates_all_fields():
    records = g.parse_dmr(DMR_SAMPLE)
    assert records[0]["name"] == "Erhan Ozkan"
    assert records[0]["city"] == "Izmir"
    assert records[1]["city"] == "Munchen"
    assert all(v.isascii() for r in records for v in r.values())


def test_nameless_record_falls_back_to_callsign():
    # radioid.net'te ismi boş kayıtlar var; ekranda boş satır görünmesin
    raw = ("RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n"
           "2021682,SZ1GRC,,,Athens,,Greece\n")
    assert g.parse_dmr(raw)[0]["name"] == "SZ1GRC"


def test_callsign_fallback_respects_display_limit():
    raw = ("RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n"
           "2021683,ABCDEFGHIJKLMNOPQRSTU,,,Athens,,Greece\n")
    assert len(g.parse_dmr(raw)[0]["name"]) <= g.NAME_MAX_LEN


def test_real_name_wins_over_callsign():
    raw = ("RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n"
           "2860001,TA3HRJ,Erhan,,Izmir,,Turkiye\n")
    assert g.parse_dmr(raw)[0]["name"] == "Erhan"


def test_parse_nxdn_keeps_first_and_last_separate():
    raw = ("RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n"
           "615,TA1SA,Yener,Güneş,İstanbul,Marmara Region,Turkiye\n")
    records = g.parse_nxdn(raw)
    assert records[0]["first_name"] == "Yener"
    assert records[0]["last_name"] == "Gunes"
    assert records[0]["city"] == "Istanbul"
