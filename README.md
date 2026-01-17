# NAS Thumbnail Generator

A Python utility that recursively generates thumbnail images for photos and videos, following the [freedesktop.org thumbnail standard](https://specifications.freedesktop.org/thumbnail-spec/thumbnail-spec-latest.html). Designed for use with NAS devices and media servers.

## Features

- Generates thumbnails in standard sizes (128px normal, 256px large)
- Supports common image formats: JPEG, PNG, GIF, BMP, WebP, TIFF
- Supports common video formats: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MPEG
- Creates `.thumbnails` folder structure compatible with Android and freedesktop.org standards
- Parallel processing for faster thumbnail generation
- Incremental updates - only regenerates thumbnails when source files change
- Dry-run mode to preview what would be processed

## Requirements

- Python 3.8+
- [Pillow](https://pillow.readthedocs.io/) - for image processing
- [FFmpeg](https://ffmpeg.org/) - for video thumbnail extraction (must be installed separately)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/dnaod/thumbnail_generator.git
   cd thumbnail_generator
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg (for video support):
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg

   # macOS (using Homebrew)
   brew install ffmpeg

   # Windows (using Chocolatey)
   choco install ffmpeg
   ```

## Usage

Basic usage:
```bash
python thumbnail_generator.py /path/to/media/folder
```

### Options

| Option | Description |
|--------|-------------|
| `--force` | Force regeneration of all thumbnails, even if they exist |
| `--workers N` | Number of parallel workers (default: 4) |
| `--dry-run` | Show what would be processed without generating thumbnails |

### Examples

Generate thumbnails for all media in a directory:
```bash
python thumbnail_generator.py /mnt/nas/photos
```

Force regeneration with 8 parallel workers:
```bash
python thumbnail_generator.py /mnt/nas/photos --force --workers 8
```

Preview what would be processed:
```bash
python thumbnail_generator.py /mnt/nas/photos --dry-run
```

## Output Structure

For each directory containing media files, a `.thumbnails` folder is created with the following structure:

```
/your/media/folder/
├── image1.jpg
├── video1.mp4
└── .thumbnails/
    ├── normal/      # 128x128 thumbnails
    │   ├── <md5hash>.png
    │   └── ...
    └── large/       # 256x256 thumbnails
        ├── <md5hash>.png
        └── ...
```

Thumbnail filenames are MD5 hashes of the source file URI, following the freedesktop.org specification.

## License

MIT License - see [LICENSE](LICENSE) for details.
