#!/usr/bin/env python3
"""
Photo Compressor for Photography Clubs
Compresses photos into 'archive' and 'web' tracks.
Resumable, never touches originals, keeps important EXIF metadata.
"""

import os
import argparse
import json
from pathlib import Path
from PIL import Image, ImageOps
import piexif
from tqdm import tqdm

def filter_exif(exif_bytes):
    if not exif_bytes:
        return b""
        
    try:
        exif_dict = piexif.load(exif_bytes)
        clean_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
        
        whitelist_0th = [271, 272, 306, 274]
        for tag in whitelist_0th:
            if tag in exif_dict.get("0th", {}):
                clean_dict["0th"][tag] = exif_dict["0th"][tag]
                
        whitelist_exif = [36867, 36868, 33434, 33437, 34855, 34850, 37386, 42036]
        for tag in whitelist_exif:
            if tag in exif_dict.get("Exif", {}):
                clean_dict["Exif"][tag] = exif_dict["Exif"][tag]
                
        return piexif.dump(clean_dict)
    except Exception:
        return b""

def process_image(src_path, archive_path, web_path, do_archive, do_web, archive_q, web_q):
    try:
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)
            exif_data = img.info.get('exif', b'')
            clean_exif = filter_exif(exif_data)
            
            if do_archive and not os.path.exists(archive_path):
                os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                img.save(archive_path, 'JPEG', quality=archive_q, optimize=True, exif=clean_exif)
                
            if do_web and not os.path.exists(web_path):
                os.makedirs(os.path.dirname(web_path), exist_ok=True)
                web_img = img.copy()
                web_img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                web_img.save(web_path, 'JPEG', quality=web_q, optimize=True, exif=clean_exif)
                
        return True, None
    except Exception as e:
        return False, str(e)

def run_compression(source_dir, output_dir=None, archive_quality=90, web_quality=75, do_archive=True, do_web=True, progress_callback=None):
    source_dir = Path(source_dir).resolve()
    if not source_dir.is_dir():
        return False, f"Source directory {source_dir} does not exist."
        
    if output_dir:
        output_dir = Path(output_dir).resolve()
    else:
        output_dir = source_dir / "_compressed"
        
    if not do_archive and not do_web:
        return False, "Both web and archive tracks are disabled."
        
    extensions = {'.jpg', '.jpeg'}
    all_files = []
    for p in source_dir.rglob("*"):
        if "_compressed" in p.parts:
            continue
        if p.is_file() and p.suffix.lower() in extensions:
            all_files.append(p)
            
    log_file = output_dir / "compression_log.json"
    processed_files = set()
    
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                state = json.load(f)
                processed_files = set(state.get('processed_files', []))
        except Exception:
            pass
            
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    error_count = 0
    total_files = len(all_files)
    
    iterable = all_files
    if not progress_callback:
        iterable = tqdm(all_files, desc="Compressing")
        
    for i, file_path in enumerate(iterable):
        file_str = str(file_path)
        
        if progress_callback:
            progress_callback(i, total_files, file_str)
            
        if file_str in processed_files:
            continue
            
        rel_path = file_path.relative_to(source_dir)
        archive_path = output_dir / "archive" / rel_path
        web_path = output_dir / "web" / rel_path
        
        success, err = process_image(
            file_path, str(archive_path), str(web_path), 
            do_archive, do_web, 
            archive_quality, web_quality
        )
        
        if success:
            processed_files.add(file_str)
            success_count += 1
        else:
            error_count += 1
            
        if (i + 1) % 50 == 0:
            with open(log_file, 'w') as f:
                json.dump({"processed_files": list(processed_files)}, f)
                
    with open(log_file, 'w') as f:
        json.dump({"processed_files": list(processed_files)}, f)
        
    if progress_callback:
        progress_callback(total_files, total_files, "Done!")
        
    return True, f"Successfully processed {success_count} images. Errors: {error_count}."

def main():
    parser = argparse.ArgumentParser(description="Photography Club Photo Compressor")
    parser.add_argument("source", help="/path/to/portfolio")
    parser.add_argument("--output", help="/path/to/output", default=None)
    parser.add_argument("--archive-quality", type=int, default=90)
    parser.add_argument("--web-quality", type=int, default=75)
    parser.add_argument("--no-web", action="store_true", help="Skip creating the web track")
    parser.add_argument("--no-archive", action="store_true", help="Skip creating the archive track")
    
    args = parser.parse_args()
    
    success, msg = run_compression(
        args.source, args.output,
        args.archive_quality, args.web_quality,
        not args.no_archive, not args.no_web
    )
    print(msg)

if __name__ == "__main__":
    main()
