# AnyTone D890UV Contact List Generator

Generate screen-character-compliant DMR and NXDN contact list CSV files for AnyTone D890UV (also compatible with D878UV) from [radioid.net](https://radioid.net) database dumps.

## Download

**→ [contacts.aprsagent.com](https://contacts.aprsagent.com/)**

Ready-to-import CSV files, regenerated automatically once a day. No need to run
anything yourself — just pick your region and import into the CPS.

## Features

- **DMR & NXDN support** — generates both `DMR Digital Contact List` and `NX Digital Contact List` CSV files
- **ASCII transliteration** — converts all non-ASCII characters (Turkish ÇİĞÖŞÜ, German äöü, Cyrillic, CJK, etc.) to their closest ASCII equivalents so they display correctly on the radio screen
- **Regional filtering** — produces separate Turkey, Europe, and World files; DMR regions are
  selected by the MCC country code embedded in the Radio ID (`2xx` = Europe, `286` = Turkey),
  not by the free-text country name, so a spelling change at the source cannot silently drop records
- **D890UV CPS compatible** — output format matches the CPS import/export format exactly
- **Duplicate removal** — removes duplicate Radio ID entries
- **Smart name truncation** — respects the 16-character display limit, avoids cutting words in half
- **Refuses to publish bad data** — if a download is not valid CSV, or the record counts fall below
  80% of the previous run, the script exits with an error instead of overwriting good output

## Output Files

| File | Description |
|------|-------------|
| `DMR Digital Contact List - Turkey.csv` | DMR contacts registered in Turkey |
| `DMR Digital Contact List - Europe.csv` | DMR contacts registered in Europe |
| `DMR Digital Contact List - World.csv` | All DMR contacts worldwide |
| `NX Digital Contact List - Turkey.csv` | NXDN contacts registered in Turkey |
| `NX Digital Contact List - Europe.csv` | NXDN contacts registered in Europe |
| `NX Digital Contact List - World.csv` | All NXDN contacts worldwide |

## Requirements

- Python 3.10+
- `unidecode` package

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Only needed if you want to build the lists yourself — otherwise grab them from the
[download page](https://contacts.aprsagent.com/).

```bash
python generator.py
```

The script will:
1. Download the latest DMR and NXDN dumps from radioid.net
2. Process and transliterate all names and fields
3. Verify the record counts against the previous run before writing anything
4. Generate 6 CSV files in the `output/` directory (Turkey, Europe, World for each protocol)

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

The tests cover the three things that break silently on the radio: the 16-character display
limit, the exact CPS column layout, and the record-count guard.

### Importing to D890UV

1. Open AnyTone CPS software
2. Go to **DMR > Digital Contact List**
3. Use **Tool > Import** and select the DMR CSV file
4. Go to **NX > NX Digital Contact List**
5. Use **Tool > Import** and select the NX CSV file
6. Write the codeplug to the radio

## Data Source

All contact data is sourced from [radioid.net](https://radioid.net/database/dumps) database dumps, updated regularly by the ham radio community.

## Character Transliteration Examples

| Original | Transliterated |
|----------|---------------|
| Çetin | Cetin |
| İbrahim | Ibrahim |
| Güneş | Gunes |
| Ölçer | Olcer |
| Şükrü | Sukru |
| Müller | Muller |
| José | Jose |
| Дмитрий | Dmitrij |

## License

Code: MIT License — see [LICENSE](LICENSE) file. The contact data belongs to radioid.net and is
subject to its terms. The licence grants no rights in the trademarks named in this project.

## Trademarks and disclaimer

Brand, product, organisation and company names in this project are trademarks or registered
trademarks of their respective owners and are used only for identification. APRS® is a
registered trademark of APRS Software and Bob Bruninga, WB4APR (SK). AnyTone, D890UV and D878UV
may also be trademarks or registered trademarks of their owner. This project is not affiliated
with, endorsed, approved or sponsored by any organisation or manufacturer named, including
radioid.net.

- The lists are compiled automatically from radioid.net's public database dumps. Names are
  transliterated to ASCII and shortened to 16 characters, so they can differ from the source,
  and the source may change without notice.
- Accuracy and currency depend on radioid.net. Its terms govern the personal data in these
  lists; the lists are for amateur radio use only.
- External links lead to third-party sites; this project is not responsible for their content.
- Everything is provided "as is", without any warranty of accuracy, completeness or fitness for
  a particular purpose, and no liability is accepted for any damage arising from its use.

## Credits

Developed by TA3HX (formerly TA3HRJ)
