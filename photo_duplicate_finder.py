#!/usr/bin/env python3
"""
Photo Duplicate Finder with AI Quality Assessment
Detects duplicates and intelligently selects the best version based on content
Now upgraded with MediaPipe Deep Learning models and Multiprocessing
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
from PIL import Image, UnidentifiedImageError
import imagehash
from tqdm import tqdm
import json
import shutil
from datetime import datetime
import cv2
import numpy as np
import logging
import concurrent.futures

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("photo_duplicate_finder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DuplicateFinder")

# Module-level models for multiprocessing
_cv2_face_cascade = None

def get_face_detector():
    global _cv2_face_cascade
    if _cv2_face_cascade is None:
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            _cv2_face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            _cv2_face_cascade = False
    return _cv2_face_cascade

def compute_image_metrics(img_path, hash_size=8, use_ai=True):
    """Module-level function so it can be pickled for multiprocessing"""
    result = {
        'path': img_path,
        'hash': None,
        'score': 0.0,
        'mtime': os.path.getmtime(img_path),
        'error': None
    }
    try:
        # Compute Hash
        with Image.open(img_path) as img:
            result['hash'] = str(imagehash.average_hash(img, hash_size=hash_size))
            
        if not use_ai:
            return result
            
        # AI Quality Scoring
        cv_img = cv2.imread(img_path)
        if cv_img is None:
            return result
            
        # 1. Sharpness
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(sharpness / 500.0, 1.0)
        
        # 2. Exposure
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        dark_ratio = np.sum(hist[:30]) / gray.size
        bright_ratio = np.sum(hist[225:]) / gray.size
        exposure_score = max(0.0, 1.0 - (dark_ratio + bright_ratio))
        
        # 3. Deep Learning Face Detection (OpenCV Haar Cascade)
        face_detector = get_face_detector()
        face_score = 0.0
        if face_detector:
            # OpenCV cascades run natively on grayscale images
            faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            face_count = len(faces)
            face_score = min(face_count / 5.0, 1.0)
                
        # Total
        total_score = (sharpness_score * 0.4) + (exposure_score * 0.3) + (face_score * 0.3)
        file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
        size_bonus = min(file_size_mb / 20.0, 0.1)
        
        result['score'] = min(total_score + size_bonus, 1.0)
        
    except Exception as e:
        result['error'] = str(e)
        
    return result

class DuplicateFinder:
    def __init__(self, root_dir, hash_size=8, similarity_threshold=5, use_ai_ranking=True, cache_file='hash_cache.json', progress_callback=None):
        self.root_dir = Path(root_dir)
        self.hash_size = hash_size
        self.similarity_threshold = similarity_threshold
        self.use_ai_ranking = use_ai_ranking
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
        
        self.file_hashes = {}
        self.image_scores = {}
        self.cache_file = cache_file
        self.progress_callback = progress_callback
        self.cache = self._load_cache()

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
        return {}
        
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Could not save cache: {e}")
            
    def find_all_images(self):
        images = []
        try:
            for root, _, files in os.walk(self.root_dir):
                for file in files:
                    # Check extension quickly without upper/lower passes
                    if os.path.splitext(file)[1].lower() in self.image_extensions:
                        images.append(Path(root) / file)
            logger.info(f"Discovered {len(images)} potential image files in {self.root_dir}")
        except PermissionError as e:
            logger.error(f"Permission denied while scanning directory {self.root_dir}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while scanning directory: {e}")
        return images
    
    def scan_images(self):
        logger.info(f"Scanning directory: {self.root_dir}")
        images = [str(p) for p in self.find_all_images()]
        if not images:
            logger.warning("No images found to process.")
            return

        logger.info(f"Processing {len(images)} images using multiprocessing...")
        
        to_process = []
        
        # Check cache first
        for img_str in images:
            try:
                mtime = os.path.getmtime(img_str)
            except Exception:
                continue
                
            cached_data = self.cache.get(img_str)
            if cached_data and cached_data.get('mtime') == mtime:
                phash_val = cached_data.get('hash')
                if phash_val:
                    self.file_hashes[img_str] = imagehash.hex_to_hash(phash_val)
                if self.use_ai_ranking and 'quality_score' in cached_data:
                    self.image_scores[img_str] = cached_data['quality_score']
            else:
                to_process.append(img_str)
                
        if to_process:
            logger.info(f"{len(to_process)} images need computation. Starting process pool...")
            
            # ProcessPoolExecutor for CPU-bound tasks
            max_workers = max(1, os.cpu_count() - 1)
            
            completed = 0
            total = len(to_process)
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Process in chunks to prevent OOM on 50,000+ files
                chunk_size = 1000
                
                with tqdm(total=total, desc="Computing...") as pbar:
                    for i in range(0, total, chunk_size):
                        chunk = to_process[i:i + chunk_size]
                        future_to_img = {
                            executor.submit(compute_image_metrics, img, self.hash_size, self.use_ai_ranking): img 
                            for img in chunk
                        }
                    
                        for future in concurrent.futures.as_completed(future_to_img):
                            result = future.result()
                            img_str = result['path']
                            
                            pbar.update(1)
                            
                            if result.get('error'):
                                logger.error(f"Error processing {img_str}: {result['error']}")
                                continue
                                
                            if result.get('hash'):
                                self.file_hashes[img_str] = imagehash.hex_to_hash(result['hash'])
                                self.image_scores[img_str] = result['score']
                                
                                self.cache[img_str] = {
                                    'mtime': result['mtime'],
                                    'hash': result['hash'],
                                    'quality_score': result['score']
                                }
                            
                            completed += 1
                            if self.progress_callback:
                                self.progress_callback(completed, total, img_str)
                        
                    if completed > 0 and completed % 50 == 0:
                        self._save_cache()
                        
            self._save_cache()
        
        logger.info(f"Successfully processed {len(self.file_hashes)} out of {len(images)} images.")
    
    def find_duplicates(self):
        logger.info(f"Finding duplicates with similarity threshold {self.similarity_threshold}...")
        
        duplicate_groups = []
        processed = set()
        files = list(self.file_hashes.keys())
        
        try:
            for i, file1 in enumerate(tqdm(files, desc="Comparing images")):
                if file1 in processed:
                    continue
                
                hash1 = self.file_hashes[file1]
                group = [file1]
                
                for file2 in files[i+1:]:
                    if file2 in processed:
                        continue
                    
                    hash2 = self.file_hashes[file2]
                    distance = hash1 - hash2
                    
                    if distance <= self.similarity_threshold:
                        group.append(file2)
                        processed.add(file2)
                
                if len(group) > 1:
                    duplicate_groups.append(group)
                    processed.add(file1)
            
            logger.info(f"Found {len(duplicate_groups)} groups of duplicates.")
            return duplicate_groups
        except Exception as e:
            logger.error(f"Error during duplicate finding phase: {e}")
            return []
    
    def get_file_info(self, file_path):
        try:
            stat = os.stat(file_path)
            info = {
                'path': file_path,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024*1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
            if file_path in self.image_scores:
                info['quality_score'] = round(self.image_scores[file_path], 4)
            return info
        except Exception as e:
            return {'path': file_path, 'size': 0, 'size_mb': 0.0, 'modified': '', 'created': ''}
    
    def generate_report(self, duplicate_groups, output_file='duplicate_report.json'):
        report = {
            'scan_date': datetime.now().isoformat(),
            'root_directory': str(self.root_dir),
            'total_images_scanned': len(self.file_hashes),
            'duplicate_groups_found': len(duplicate_groups),
            'total_duplicates': sum(len(group)-1 for group in duplicate_groups),
            'groups': []
        }
        
        total_wasted_space = 0
        for idx, group in enumerate(duplicate_groups, 1):
            group_info = {'group_id': idx, 'duplicate_count': len(group), 'files': []}
            files_with_info = [self.get_file_info(f) for f in group]
            
            if self.use_ai_ranking and 'quality_score' in files_with_info[0]:
                files_with_info.sort(key=lambda x: (x.get('quality_score', 0), x['size']), reverse=True)
            else:
                files_with_info.sort(key=lambda x: x['size'], reverse=True)
            
            keep_file = files_with_info[0]
            group_info['recommended_keep'] = keep_file['path']
            
            for file_info in files_with_info:
                file_info['action'] = 'KEEP' if file_info['path'] == keep_file['path'] else 'DELETE'
                group_info['files'].append(file_info)
            
            wasted = sum(f['size'] for f in files_with_info[1:])
            total_wasted_space += wasted
            group_info['wasted_space_mb'] = round(wasted / (1024*1024), 2)
            report['groups'].append(group_info)
        
        report['total_wasted_space_mb'] = round(total_wasted_space / (1024*1024), 2)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        return report

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Photo Duplicate Finder')
    parser.add_argument('directory', help='Root directory to scan')
    parser.add_argument('--threshold', type=int, default=5)
    args = parser.parse_args()
    
    finder = DuplicateFinder(args.directory, similarity_threshold=args.threshold)
    finder.scan_images()
    groups = finder.find_duplicates()
    finder.generate_report(groups)

if __name__ == '__main__':
    main()