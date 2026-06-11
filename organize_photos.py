#!/usr/bin/env python3
"""
organize_photos.py — Sort photos into Activity/Year-Month folders.

Detects likely activity from filename keywords, then groups by date within
each activity folder. Falls back to "Misc" if no activity is detected.

Usage:
    python organize_photos.py <source_folder> [--dest <destination_folder>] [--dry-run]

Examples:
    python organize_photos.py ~/Pictures
    python organize_photos.py ~/Downloads/photos --dest ~/Pictures/sorted
    python organize_photos.py ~/Pictures --dry-run
"""

import os
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".tiff", ".tif", ".raw", ".cr2", ".nef"}

# Keyword → Activity folder name
ACTIVITY_KEYWORDS = {
    "Beach":        ["beach", "sea", "ocean", "sand", "surf", "waves", "shore", "coast", "bay"],
    "Hiking":       ["hike", "hiking", "trail", "mountain", "summit", "trekking", "trek", "peak", "cliff"],
    "Birthday":     ["birthday", "bday", "cake", "party", "celebration", "celebrate", "candle"],
    "Wedding":      ["wedding", "bride", "groom", "ceremony", "reception", "bridal"],
    "Travel":       ["travel", "trip", "vacation", "holiday", "tour", "abroad", "flight", "airport"],
    "Food":         ["food", "lunch", "dinner", "breakfast", "restaurant", "meal", "eat", "brunch", "cafe"],
    "Sports":       ["sport", "game", "match", "soccer", "football", "basketball", "tennis", "run", "race", "gym"],
    "Family":       ["family", "dad", "mom", "sister", "brother", "grandma", "grandpa", "kid", "children", "baby"],
    "Friends":      ["friends", "friend", "squad", "crew", "group", "hangout"],
    "Graduation":   ["graduation", "graduate", "grad", "diploma", "ceremony", "convocation"],
    "Christmas":    ["christmas", "xmas", "holiday", "santa", "tree", "noel"],
    "Halloween":    ["halloween", "costume", "trick", "treat", "spooky"],
    "Nature":       ["nature", "flower", "garden", "forest", "lake", "river", "sunset", "sunrise", "landscape", "tree"],
    "Pets":         ["dog", "cat", "pet", "puppy", "kitten", "bird", "rabbit"],
    "Concert":      ["concert", "festival", "music", "band", "show", "gig", "stage", "live"],
    "Screenshot":   ["screenshot", "screen", "capture", "snap"],
}


def detect_activity(filename: str) -> str:
    name = filename.lower()
    name = re.sub(r"[_\-\.\s]+", " ", name)
    for activity, keywords in ACTIVITY_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            return activity
    return "Misc"


def get_file_date(path: Path) -> datetime:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        with Image.open(path) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    if TAGS.get(tag_id) == "DateTimeOriginal":
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def organize(source: Path, dest: Path, dry_run: bool):
    photos = [f for f in source.rglob("*") if f.is_file() and f.suffix.lower() in PHOTO_EXTENSIONS]

    if not photos:
        print("No photos found.")
        return

    print(f"Found {len(photos)} photo(s). {'[DRY RUN] ' if dry_run else ''}Destination: {dest}\n")

    moved, skipped = 0, 0
    for photo in sorted(photos):
        date = get_file_date(photo)
        activity = detect_activity(photo.stem)
        month_label = f"{date.year}-{date.month:02d} {date.strftime('%B')}"
        target_dir = dest / activity / month_label
        target = target_dir / photo.name

        # Avoid overwriting
        counter = 1
        while target.exists() and target.resolve() != photo.resolve():
            target = target_dir / f"{photo.stem}_{counter}{photo.suffix}"
            counter += 1

        if target.resolve() == photo.resolve():
            print(f"  SKIP  (already in place): {photo.name}")
            skipped += 1
            continue

        action = "[DRY RUN] " if dry_run else ""
        rel_dest = f"{activity}/{month_label}/{target.name}"
        print(f"  {action}MOVE  {photo.name:40s} → {rel_dest}")

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(photo), target)
            moved += 1
        else:
            moved += 1

    print(f"\nDone. {moved} photo(s) organized, {skipped} skipped.")
    print("\nFolder structure:")
    print("  <dest>/")
    print("    <Activity>/")
    print("      <YYYY-MM Month>/")
    print("        photo.jpg")


def main():
    parser = argparse.ArgumentParser(description="Organize photos by activity and date.")
    parser.add_argument("source", help="Folder containing your photos")
    parser.add_argument("--dest", help="Destination folder (default: same as source)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving any files")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve() if args.dest else source

    if not source.is_dir():
        print(f"Error: '{source}' is not a valid directory.")
        return

    organize(source, dest, args.dry_run)


if __name__ == "__main__":
    main()
