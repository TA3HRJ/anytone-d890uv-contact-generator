# AnyTone D890UV Contact List Generator

Generate screen-character-compliant DMR and NXDN contact list CSV files for AnyTone D890UV (also compatible with D878UV) from [radioid.net](https://radioid.net) database dumps.

## Features

- **DMR & NXDN support** — generates both `DMR Digital Contact List` and `NX Digital Contact List` CSV files
- **ASCII transliteration** — converts all non-ASCII characters (Turkish ÇİĞÖŞÜ, German äöü, Cyrillic, CJK, etc.) to their closest ASCII equivalents so they display correctly on the radio screen
- **Regional filtering** — produces separate Turkey and World files
- **D890UV CPS compatible** — output format matches the CPS import/export format exactly
- **Duplicate removal** — removes duplicate Radio ID entries
- **Smart name truncation** — respects the 16-character display limit, avoids cutting words in half

## Output Files

| File | Description |
|------|-------------|
| `DMR Digital Contact List - Turkey.csv` | DMR contacts registered in Turkey |
| `DMR Digital Contact List - World.csv` | All DMR contacts worldwide |
| `NX Digital Contact List - Turkey.csv` | NXDN contacts registered in Turkey |
| `NX Digital Contact List - World.csv` | All NXDN contacts worldwide |

## Requirements

- Python 3.10+
- `unidecode` package

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python generator.py
```

The script will:
1. Download the latest DMR and NXDN dumps from radioid.net
2. Process and transliterate all names and fields
3. Generate 4 CSV files in the `output/` directory

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

MIT License — see [LICENSE](LICENSE) file.

## Credits

Developed by TA3HRJ & TA3PKS
