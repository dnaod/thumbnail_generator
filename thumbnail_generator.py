#!/usr/bin/env python3
"""
NAS Thumbnail Generator
Recursively generates .thumbnails folders for images and videos following Android/freedesktop.org standards
"""

import os
import hashlib
import argparse
from pathlib import Path
from PIL import Image
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg'}

# Thumbnail sizes (freedesktop.org standard)
THUMBNAIL_SIZES = {
    'normal': 128,
    'large': 256
}


def get_file_uri(file_path: Path) -> str:
    """Convert file path to URI format for MD5 hashing"""
    absolute_path = file_path.resolve()
    uri = f"file://{absolute_path}"
    return uri


def get_thumbnail_filename(file_path: Path) -> str:
    """Generate MD5 hash of file URI for thumbnail filename"""
    uri = get_file_uri(file_path)
    md5_hash = hashlib.md5(uri.encode('utf-8')).hexdigest()
    return f"{md5_hash}.png"


def create_thumbnail_dirs(directory: Path) -> dict:
    """Create .thumbnails directory structure"""
    thumbnail_base = directory / '.thumbnails'
    dirs = {}
    
    for size_name in THUMBNAIL_SIZES.keys():
        size_dir = thumbnail_base / size_name
        size_dir.mkdir(parents=True, exist_ok=True)
        dirs[size_name] = size_dir
    
    return dirs


def generate_image_thumbnail(image_path: Path, output_path: Path, size: int) -> bool:
    """Generate thumbnail for an image file"""
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Generate thumbnail maintaining aspect ratio
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            
            # Save as PNG
            img.save(output_path, 'PNG')
            return True
    except Exception as e:
        logger.error(f"Error generating image thumbnail for {image_path}: {e}")
        return False


def generate_video_thumbnail(video_path: Path, output_path: Path, size: int) -> bool:
    """Generate thumbnail for a video file using ffmpeg"""
    try:
        # Extract frame at 1 second (or 10% of duration)
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-ss', '00:00:01.000',
            '-vframes', '1',
            '-vf', f'scale={size}:{size}:force_original_aspect_ratio=decrease',
            '-y',  # Overwrite output file
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout generating video thumbnail for {video_path}")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg to generate video thumbnails.")
        return False
    except Exception as e:
        logger.error(f"Error generating video thumbnail for {video_path}: {e}")
        return False


def should_generate_thumbnail(file_path: Path, thumbnail_path: Path, force: bool) -> bool:
    """Check if thumbnail needs to be generated"""
    if force:
        return True
    
    if not thumbnail_path.exists():
        return True
    
    # Check if source file is newer than thumbnail
    if file_path.stat().st_mtime > thumbnail_path.stat().st_mtime:
        return True
    
    return False


def process_file(file_path: Path, force: bool = False) -> tuple:
    """Process a single file and generate thumbnails"""
    extension = file_path.suffix.lower()
    
    if extension not in IMAGE_EXTENSIONS and extension not in VIDEO_EXTENSIONS:
        return (file_path, 'skipped', 'unsupported')
    
    # Create thumbnail directories in the same directory as the file
    thumbnail_dirs = create_thumbnail_dirs(file_path.parent)
    thumbnail_filename = get_thumbnail_filename(file_path)
    
    results = []
    for size_name, size in THUMBNAIL_SIZES.items():
        output_path = thumbnail_dirs[size_name] / thumbnail_filename
        
        if not should_generate_thumbnail(file_path, output_path, force):
            results.append(f"{size_name}:cached")
            continue
        
        # Generate thumbnail based on file type
        if extension in IMAGE_EXTENSIONS:
            success = generate_image_thumbnail(file_path, output_path, size)
        else:  # VIDEO_EXTENSIONS
            success = generate_video_thumbnail(file_path, output_path, size)
        
        results.append(f"{size_name}:{'ok' if success else 'failed'}")
    
    status = 'success' if any('ok' in r for r in results) else 'failed'
    return (file_path, status, ','.join(results))


def find_media_files(root_dir: Path, exclude_dirs: Set[str] = None) -> list:
    """Recursively find all media files"""
    if exclude_dirs is None:
        exclude_dirs = {'.thumbnails', '@eaDir', '.DS_Store', 'Thumbs.db'}
    
    media_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Remove excluded directories from the search
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        root_path = Path(root)
        for file in files:
            file_path = root_path / file
            extension = file_path.suffix.lower()
            
            if extension in IMAGE_EXTENSIONS or extension in VIDEO_EXTENSIONS:
                media_files.append(file_path)
    
    return media_files


def main():
    parser = argparse.ArgumentParser(
        description='Generate thumbnails for images and videos in a directory tree'
    )
    parser.add_argument(
        'directory',
        type=str,
        help='Top-level directory to scan'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regeneration of existing thumbnails'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without generating thumbnails'
    )
    
    args = parser.parse_args()
    
    root_dir = Path(args.directory)
    
    if not root_dir.exists():
        logger.error(f"Directory does not exist: {root_dir}")
        return 1
    
    if not root_dir.is_dir():
        logger.error(f"Not a directory: {root_dir}")
        return 1
    
    logger.info(f"Scanning for media files in {root_dir}...")
    media_files = find_media_files(root_dir)
    logger.info(f"Found {len(media_files)} media files")
    
    if args.dry_run:
        for file_path in media_files:
            print(f"Would process: {file_path}")
        return 0
    
    # Process files in parallel
    successful = 0
    failed = 0
    cached = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_file, file_path, args.force): file_path
            for file_path in media_files
        }
        
        for future in as_completed(futures):
            file_path, status, details = future.result()
            
            if status == 'success':
                successful += 1
                logger.info(f"✓ {file_path.name} - {details}")
            elif status == 'failed':
                failed += 1
                logger.warning(f"✗ {file_path.name} - {details}")
            elif 'cached' in details:
                cached += 1
                logger.debug(f"⊙ {file_path.name} - {details}")
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"Processing complete!")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Cached: {cached}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total: {len(media_files)}")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit(main())