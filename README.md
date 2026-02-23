# kanji-alive-indexer

Indexed ZIP archives for Kanji Alive example audio, for use with [AJT Japanese](https://ankiweb.net/shared/info/1344485230) and other programs that use this format. Download prebuilt archives from Releases.

## What the script does

`build_indexed_zips.py`:
- Downloads `ka_data.csv` from `kanjialive/kanji-data-media` on GitHub.
- Downloads Kanji Alive audio ZIP files for Opus, AAC, Ogg, and MP3.
- Builds an `index.json` (with `meta`, `headwords`, and `files` sections) from `ka_data.csv`.
- Writes one ZIP per format containing `index.json` and `media/*`.

## Usage

```bash
python3 build_indexed_zips.py
```

Optional flags:

```bash
python3 build_indexed_zips.py --output-dir dist --download-dir .downloads --formats opus aac ogg mp3 --force-download
```

## Licensing

- Script and repository code: **CC0 1.0 Universal**.
- Kanji Alive language data and audio are from **Kanji Alive** under **CC BY 4.0**.
  - Attribute to **Harumi Hibino Lory** and **Arno Bosse** (Kanji Alive team), and the Kanji Alive project.
