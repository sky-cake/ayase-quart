#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess
import signal
from pathlib import Path
from tqdm import tqdm
from PIL import Image
import shutil


def process_video(file_path, image_dir, thumb_dir, dry_run):
    relative_path = os.path.relpath(file_path, image_dir)
    jpg_file = os.path.join(thumb_dir, os.path.splitext(relative_path)[0] + "s.jpg")
    if dry_run:
        print(jpg_file)
        return
    if not os.path.exists(jpg_file):
        os.makedirs(os.path.dirname(jpg_file), exist_ok=True)
        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "panic",
            "-i", str(file_path), "-ss", "00:00:01.000", "-vframes", "1",
            "-q:v", "32", str(jpg_file)
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print(f"\nFailed to process video: {file_path}")


def process_image(file_path, image_dir, thumb_dir, dry_run):
    relative_path = os.path.relpath(file_path, image_dir)
    jpg_file = os.path.join(thumb_dir, os.path.splitext(relative_path)[0] + "s.jpg")
    if dry_run:
        print(jpg_file)
        return
    if not os.path.exists(jpg_file):
        os.makedirs(os.path.dirname(jpg_file), exist_ok=True)
        try:
            with Image.open(file_path) as img:
                img = img.convert("RGB")
                img.thumbnail((400, 400))
                img.save(jpg_file, "JPEG", quality=25)
        except Exception as e:
            print(f"\nFailed to compress image: {file_path} ({e})")


def process_gif(file_path, image_dir, thumb_dir, dry_run):
    relative_path = os.path.relpath(file_path, image_dir)
    jpg_file = os.path.join(thumb_dir, os.path.splitext(relative_path)[0] + "s.jpg")
    if dry_run:
        print(jpg_file)
        return
    if not os.path.exists(jpg_file):
        os.makedirs(os.path.dirname(jpg_file), exist_ok=True)
        try:
            with Image.open(file_path) as img:
                img = img.convert("RGB")
                img.thumbnail((400, 400))
                img.save(jpg_file, "JPEG", quality=25)
        except Exception as e:
            print(f"\nFailed to process GIF: {file_path} ({e})")


def interrupt_handler(sig, frame):
    print("\nInterrupted. Exiting...")
    sys.exit(1)


def check_dependencies():
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found. Please install ffmpeg.", file=sys.stderr)
        sys.exit(1)


def main():
    signal.signal(signal.SIGINT, interrupt_handler)
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="Create thumbnails for images and videos.",
        usage="%(prog)s <path-to-image-folder> [--types jpg,png,...] [--dry-run]"
    )
    parser.add_argument("path", help="Path to the image folder")
    parser.add_argument("--types", default="webm,jpg,png,gif", help="Comma-separated list of file types")
    parser.add_argument("--dry-run", action="store_true", help="Show thumbnail paths without processing")
    args = parser.parse_args()

    start_dir = Path(args.path).resolve()
    if not start_dir.is_dir():
        print(f"Error: Directory '{start_dir}' does not exist or is not accessible")
        sys.exit(1)

    image_dir = None
    if "image" in str(start_dir):
        for parent in start_dir.parents:
            if (parent / "image").exists():
                image_dir = parent / "image"
                thumb_dir = parent / "thumb"
                break
    if not image_dir:
        print("Error: The specified directory must be inside an 'image/' directory.")
        sys.exit(1)

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    if not types:
        print("Error: No valid file types specified")
        sys.exit(1)

    files = []
    for ext in types:
        pattern = f"**/*.{ext}"
        files.extend(start_dir.glob(pattern))
    files = [f for f in files if f.is_file()]

    if not files:
        print(f"No matching files found in {start_dir}")
        sys.exit(1)

    if args.dry_run:
        print("Dry run mode: Showing up to 5 new JPG paths...")
        for file in files[:5]:
            ext = file.suffix.lower()[1:]
            if ext in ("webm", "mp4"):
                process_video(file, image_dir, thumb_dir, True)
            elif ext in ("jpg", "jpeg", "png"):
                process_image(file, image_dir, thumb_dir, True)
            elif ext == "gif":
                process_gif(file, image_dir, thumb_dir, True)
        sys.exit(0)

    for file in tqdm(files, desc="Processing", unit="file"):
        ext = file.suffix.lower()[1:]
        if ext in ("webm", "mp4"):
            process_video(file, image_dir, thumb_dir, False)
        elif ext in ("jpg", "jpeg", "png"):
            process_image(file, image_dir, thumb_dir, False)
        elif ext == "gif":
            process_gif(file, image_dir, thumb_dir, False)

    print()


if __name__ == "__main__":
    """Examples:

    ./make_thumbs.py /mnt/dl/g/image --types gif,webm,mp4,jpg,png --dry-run
    ./make_thumbs.py /mnt/dl/biz/image --types gif --dry-run

    These will make thumbnails for files in the corresponding thumb folders, likeso

    /mnt/dl/g/thumb/..../../<filename>s.jpg
    """
    main()
