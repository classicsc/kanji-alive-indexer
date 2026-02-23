#!/usr/bin/env python3
"""Build AJT-style indexed ZIP files for Kanji Alive example audio.

Written in 2026 by Samuel Smoker <sam@samsmoker.net>
To the extent possible under law, the author(s) have dedicated all copyright and related and neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import string
import urllib.request
import zipfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


KA_DATA_URL = "https://raw.githubusercontent.com/kanjialive/kanji-data-media/master/language-data/ka_data.csv"
AUDIO_SOURCES = {
    "opus": "https://media.kanjialive.com/examples_audio/audio-opus.zip",
    "aac": "https://media.kanjialive.com/examples_audio/audio-aac.zip",
    "ogg": "https://media.kanjialive.com/examples_audio/audio-ogg.zip",
    "mp3": "https://media.kanjialive.com/examples_audio/audio-mp3.zip",
}
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class ExampleEntry:
    headword: str
    kana_reading: str
    stem: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Kanji Alive data and build AJT-style indexed audio ZIP files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Directory for generated indexed ZIP files (default: dist).",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path(".downloads"),
        help="Directory for downloaded source files (default: .downloads).",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=tuple(AUDIO_SOURCES),
        default=list(AUDIO_SOURCES),
        help="Audio formats to build (default: opus aac ogg mp3).",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download ka_data.csv and audio ZIPs even if files already exist.",
    )
    return parser.parse_args()


def download_file(url: str, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        print(f"Using cached file: {destination}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_destination = destination.with_suffix(destination.suffix + ".tmp")
    print(f"Downloading {url} -> {destination}")

    request = urllib.request.Request(url, headers={"User-Agent": "kanji-alive-indexer/1.0"})
    with urllib.request.urlopen(request) as response, tmp_destination.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)

    tmp_destination.replace(destination)


def split_example(example_text: str) -> tuple[str, str]:
    open_idx = example_text.find("（")
    close_idx = example_text.rfind("）")
    if open_idx == -1 or close_idx == -1 or close_idx <= open_idx:
        raise ValueError(f"Unexpected example format: {example_text}")
    headword = example_text[:open_idx]
    kana_reading = example_text[open_idx + 1 : close_idx]
    return headword, kana_reading


def load_examples(csv_path: Path) -> list[ExampleEntry]:
    entries: list[ExampleEntry] = []

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_number, row in enumerate(reader, start=2):
            kname = row["kname"]
            examples_raw = row["examples"]
            examples = json.loads(examples_raw)

            for index, item in enumerate(examples):
                if index >= len(string.ascii_lowercase):
                    raise ValueError(f"Too many examples in row {row_number} for {kname}")
                if not item or not isinstance(item, list):
                    raise ValueError(f"Unexpected example entry in row {row_number}: {item!r}")

                example_text = item[0]
                headword, kana_reading = split_example(example_text)
                suffix = string.ascii_lowercase[index]
                stem = f"{kname}_06_{suffix}"
                entries.append(ExampleEntry(headword=headword, kana_reading=kana_reading, stem=stem))

    return entries


def build_index(entries: list[ExampleEntry], extension: str) -> dict:
    headwords: OrderedDict[str, list[str]] = OrderedDict()
    files: OrderedDict[str, dict[str, str]] = OrderedDict()

    for entry in entries:
        filename = f"{entry.stem}.{extension}"
        if entry.headword not in headwords:
            headwords[entry.headword] = []
        headwords[entry.headword].append(filename)
        files[filename] = {"kana_reading": entry.kana_reading}

    return {
        "meta": {
            "name": "Kanji alive",
            "year": 2016,
            "version": 1,
            "media_dir": "media",
        },
        "headwords": headwords,
        "files": files,
    }


def write_zip_entry(zip_file: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(filename=arcname, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zip_file.writestr(info, data, compresslevel=9)


def build_indexed_zip(
    source_zip_path: Path,
    output_zip_path: Path,
    index_data: dict,
    extension: str,
) -> None:
    with zipfile.ZipFile(source_zip_path, "r") as source_zip:
        source_members: dict[str, str] = {}
        for info in source_zip.infolist():
            if info.is_dir():
                continue
            basename = Path(info.filename).name
            if not basename.endswith(f".{extension}"):
                continue
            if basename in source_members and source_members[basename] != info.filename:
                raise ValueError(f"Duplicate basename in source ZIP: {basename}")
            source_members[basename] = info.filename

        required_files = set(index_data["files"])
        missing_files = sorted(required_files - set(source_members))
        if missing_files:
            preview = ", ".join(missing_files[:10])
            raise ValueError(
                f"Missing {len(missing_files)} expected files in {source_zip_path.name}: {preview}"
            )

        output_zip_path.parent.mkdir(parents=True, exist_ok=True)
        index_json = (json.dumps(index_data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

        with zipfile.ZipFile(output_zip_path, "w") as output_zip:
            write_zip_entry(output_zip, "index.json", index_json)
            for basename in sorted(source_members):
                data = source_zip.read(source_members[basename])
                write_zip_entry(output_zip, f"media/{basename}", data)


def main() -> None:
    args = parse_args()

    csv_path = args.download_dir / "ka_data.csv"
    download_file(KA_DATA_URL, csv_path, force=args.force_download)
    entries = load_examples(csv_path)

    for audio_format in args.formats:
        source_zip_path = args.download_dir / f"audio-{audio_format}.zip"
        output_zip_path = args.output_dir / f"kanji-alive-{audio_format}-indexed.zip"

        download_file(AUDIO_SOURCES[audio_format], source_zip_path, force=args.force_download)
        index_data = build_index(entries, extension=audio_format)
        build_indexed_zip(source_zip_path, output_zip_path, index_data, extension=audio_format)
        print(f"Wrote {output_zip_path}")


if __name__ == "__main__":
    main()
