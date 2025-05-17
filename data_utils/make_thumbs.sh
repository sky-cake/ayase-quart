#!/bin/bash

process_video() {
    local file="$1"
    local jpg_file="${file/$IMAGE_DIR/$THUMB_DIR}"
    jpg_file="${jpg_file%.webm}s.jpg"

    if [ "$DRY_RUN" = true ]; then
        echo "$jpg_file"
        return
    fi

    if [ -f "$jpg_file" ]; then
        echo "Skipping $file: JPG already exists"
    else
        mkdir -p "$(dirname "$jpg_file")"

        ffmpeg -nostdin -hide_banner -loglevel panic -i "$file" -ss 00:00:01.000 -vframes 1 -q:v 32 "$jpg_file" >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo "Processed video: $file -> $jpg_file"
        else
            echo "Failed to process video: $file"
        fi
    fi
}

process_image() {
    local file="$1"
    local jpg_file="${file/$IMAGE_DIR/$THUMB_DIR}"
    jpg_file="${jpg_file%.*}.jpg"

    if [ "$DRY_RUN" = true ]; then
        echo "$jpg_file"
        return
    fi

    if [ -f "$jpg_file" ]; then
        echo "Skipping $file: Compressed JPG already exists"
    else
        mkdir -p "$(dirname "$jpg_file")"

        convert "$file" -resize 70% -quality 50 "$jpg_file"

        if [ $? -eq 0 ]; then
            echo "Compressed image: $file -> $jpg_file"
        else
            echo "Failed to compress image: $file"
        fi
    fi
}

interrupt_handler() {
    echo "Interrupted. Exiting..."
    exit 1
}

trap interrupt_handler INT

# Default settings
DRY_RUN=false
TYPES="webm,jpg,png"

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --types)
            TYPES="$2"
            shift 2
            ;;
        *)
            START_DIR="$1"
            shift
            ;;
    esac
done

# Ensure START_DIR is absolute
START_DIR="${START_DIR:-$(pwd)}"
START_DIR="$(realpath "$START_DIR")"

# Identify IMAGE_DIR and THUMB_DIR
if [[ "$START_DIR" == */image* ]]; then
    IMAGE_DIR="${START_DIR%%/image*}/image"
    THUMB_DIR="${IMAGE_DIR/image/thumb}"
else
    echo "Error: The specified directory must be inside an 'image/' directory."
    exit 1
fi

# Build file search patterns based on TYPES
IFS=',' read -ra TYPE_ARRAY <<< "$TYPES"
FIND_PATTERNS=()
for TYPE in "${TYPE_ARRAY[@]}"; do
    FIND_PATTERNS+=("-name \"*.$TYPE\"")
done
FIND_CMD="find \"$START_DIR\" -type f \\( ${FIND_PATTERNS[*]} \\) 2>/dev/null"

# Get the list of files
eval "files=(\$( $FIND_CMD ))"

if [ ${#files[@]} -eq 0 ]; then
    echo "No matching files found in $START_DIR"
    exit 1
fi

# Dry run: Print up to 5 JPG paths and exit
if [ "$DRY_RUN" = true ]; then
    echo "Dry run mode: Showing up to 5 new JPG paths..."
    count=0
    for file in "${files[@]}"; do
        case "${file##*.}" in
            "webm") process_video "$file" ;;
            "jpg"|"png") process_image "$file" ;;
        esac
        ((count++))
        if [ "$count" -ge 5 ]; then break; fi
    done
    exit 0
fi

# Process files
for file in "${files[@]}"; do
    case "${file##*.}" in
        "webm") process_video "$file" ;;
        "jpg"|"png") process_image "$file" ;;
    esac
done


# Usage
# ./make_thumbs.sh --dry-run --types jpg /mnt/dl/jp/image/1739/
# ./make_thumbs.sh --dry-run --types webm /mnt/dl/jp/image/
# ./make_thumbs.sh --dry-run --types png /mnt/dl/ck/image/
