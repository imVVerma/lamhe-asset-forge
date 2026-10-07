#!/usr/bin/env python3
"""
Photo Duplicate Finder with AI Quality Assessment
Detects duplicates and intelligently selects the best version based on content
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
from PIL import Image
import imagehash
from tqdm import tqdm
import json
import shutil
from datetime import datetime
import cv2
import numpy as np

class DuplicateFinder:
    def __init__(self, root_dir, hash_size=8, similarity_threshold=5, use_ai_ranking=True):
        """
        Initialize duplicate finder with AI-powered quality assessment
        
        Args:
            root_dir: Root directory to scan
            hash_size: Size of perceptual hash (8 is standard, higher = more strict)
            similarity_threshold: Hamming distance threshold (0=exact, 5=very similar, 10=similar)
            use_ai_ranking: Use AI to rank image quality (faces, smiles, sharpness, composition)
        """
        self.root_dir = Path(root_dir)
        self.hash_size = hash_size
        self.similarity_threshold = similarity_threshold
        self.use_ai_ranking = use_ai_ranking
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
        
        # Storage for hashes
        self.file_hashes = {}  # {file_path: hash}
        self.image_scores = {}  # {file_path: quality_score}
        
        # Load face detection model
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            print("[+] Face detection models loaded")
        except Exception as e:
            print(f"[!] Warning: Could not load face detection models: {e}")
            self.face_cascade = None
            self.smile_cascade = None
            self.eye_cascade = None
        
    def find_all_images(self):
        """Recursively find all image files"""
        images = []
        for ext in self.image_extensions:
            images.extend(self.root_dir.rglob(f'*{ext}'))
            images.extend(self.root_dir.rglob(f'*{ext.upper()}'))
        return images
    
    def compute_hash(self, img_path):
        """Compute perceptual hash for an image"""
        try:
            with Image.open(img_path) as img:
                return imagehash.average_hash(img, hash_size=self.hash_size)
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            return None
    
    def compute_sharpness(self, img):
        """Compute image sharpness using Laplacian variance"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian_var
    
    def detect_faces_and_smiles(self, img):
        """Detect faces, smiles, and open eyes in image"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = []
        if self.face_cascade is not None:
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        smile_count = 0
        open_eyes_count = 0
        
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            
            # Detect smiles
            if self.smile_cascade is not None:
                smiles = self.smile_cascade.detectMultiScale(roi_gray, 1.8, 20)
                smile_count += len(smiles)
            
            # Detect eyes (open eyes indicator)
            if self.eye_cascade is not None:
                eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10)
                open_eyes_count += len(eyes)
        
        return len(faces), smile_count, open_eyes_count
    
    def compute_exposure_quality(self, img):
        """Assess exposure quality (not too dark or blown out)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Check histogram distribution
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        
        # Penalize images with too many dark or bright pixels
        dark_pixels = np.sum(hist[:30])
        bright_pixels = np.sum(hist[225:])
        total_pixels = gray.size
        
        dark_ratio = dark_pixels / total_pixels
        bright_ratio = bright_pixels / total_pixels
        
        # Good exposure should have low ratios
        exposure_score = 1.0 - (dark_ratio + bright_ratio)
        return max(0, exposure_score)
    
    def compute_composition_score(self, img, faces):
        """Evaluate composition using rule of thirds and face placement"""
        height, width = img.shape[:2]
        
        # Rule of thirds points
        third_x = width / 3
        third_y = height / 3
        
        composition_score = 0.5  # Base score
        
        if len(faces) > 0:
            # Check if main subject (first face) is near rule of thirds
            for (x, y, w, h) in faces[:1]:  # Consider primary face
                face_center_x = x + w/2
                face_center_y = y + h/2
                
                # Distance from rule of thirds intersections
                distances = [
                    abs(face_center_x - third_x) + abs(face_center_y - third_y),
                    abs(face_center_x - 2*third_x) + abs(face_center_y - third_y),
                    abs(face_center_x - third_x) + abs(face_center_y - 2*third_y),
                    abs(face_center_x - 2*third_x) + abs(face_center_y - 2*third_y),
                ]
                
                min_distance = min(distances)
                max_distance = width + height
                
                # Closer to rule of thirds = better composition
                composition_score += (1 - min_distance / max_distance) * 0.3
        
        return min(composition_score, 1.0)
    
    def compute_quality_score(self, img_path):
        """
        Compute comprehensive quality score for an image
        
        Factors:
        - Sharpness (20%)
        - Face count (15%)
        - Smile detection (25%) - HIGHEST PRIORITY
        - Open eyes (15%)
        - Exposure quality (15%)
        - Composition (10%)
        """
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                return 0.0
            
            # Get image metrics
            sharpness = self.compute_sharpness(img)
            face_count, smile_count, open_eyes = self.detect_faces_and_smiles(img)
            exposure = self.compute_exposure_quality(img)
            
            # Normalize sharpness (typical range 0-1000, good images > 100)
            sharpness_score = min(sharpness / 500, 1.0)
            
            # Face score (more faces = better, up to 5)
            face_score = min(face_count / 5, 1.0)
            
            # Smile score - HIGHEST WEIGHT
            # If there are faces, ratio of smiling faces
            smile_score = 0
            if face_count > 0:
                smile_score = min(smile_count / face_count, 1.0)
            
            # Open eyes score
            eyes_score = 0
            if face_count > 0:
                # Expect 2 eyes per face
                eyes_score = min(open_eyes / (face_count * 2), 1.0)
            
            # Composition score
            composition = self.compute_composition_score(img, 
                self.face_cascade.detectMultiScale(
                    cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.3, 5
                ) if self.face_cascade else [])
            
            # Weighted total score
            total_score = (
                sharpness_score * 0.20 +      # Sharpness
                face_score * 0.15 +            # Faces present
                smile_score * 0.25 +           # Smiles - HIGHEST
                eyes_score * 0.15 +            # Open eyes
                exposure * 0.15 +              # Good exposure
                composition * 0.10             # Composition
            )
            
            # Get file size bonus (larger = higher quality, but minor factor)
            file_size_mb = os.path.getsize(img_path) / (1024 * 1024)
            size_bonus = min(file_size_mb / 20, 0.1)  # Max 0.1 bonus
            
            final_score = min(total_score + size_bonus, 1.0)
            
            return final_score
            
        except Exception as e:
            print(f"Error computing quality for {img_path}: {e}")
            return 0.0
    
    def scan_images(self):
        """Scan all images and compute hashes"""
        print(f"Scanning directory: {self.root_dir}")
        images = self.find_all_images()
        print(f"Found {len(images)} images to process")
        
        for img_path in tqdm(images, desc="Computing hashes and quality scores"):
            phash = self.compute_hash(img_path)
            if phash:
                self.file_hashes[str(img_path)] = phash
                
                # Compute quality score if AI ranking is enabled
                if self.use_ai_ranking:
                    score = self.compute_quality_score(img_path)
                    self.image_scores[str(img_path)] = score
        
        print(f"Successfully processed {len(self.file_hashes)} images")
    
    def find_duplicates(self):
        """Find duplicate and near-duplicate images"""
        print(f"Finding duplicates (threshold: {self.similarity_threshold})...")
        
        duplicate_groups = []
        processed = set()
        
        files = list(self.file_hashes.keys())
        
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
        
        return duplicate_groups
    
    def get_file_info(self, file_path):
        """Get file metadata"""
        stat = os.stat(file_path)
        info = {
            'path': file_path,
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024*1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
        }
        
        # Add quality score if available
        if file_path in self.image_scores:
            info['quality_score'] = round(self.image_scores[file_path], 4)
        
        return info
    
    def generate_report(self, duplicate_groups, output_file='duplicate_report.json'):
        """Generate detailed JSON report with quality rankings"""
        report = {
            'scan_date': datetime.now().isoformat(),
            'root_directory': str(self.root_dir),
            'total_images_scanned': len(self.file_hashes),
            'duplicate_groups_found': len(duplicate_groups),
            'total_duplicates': sum(len(group)-1 for group in duplicate_groups),
            'similarity_threshold': self.similarity_threshold,
            'ai_ranking_enabled': self.use_ai_ranking,
            'groups': []
        }
        
        total_wasted_space = 0
        
        for idx, group in enumerate(duplicate_groups, 1):
            group_info = {
                'group_id': idx,
                'duplicate_count': len(group),
                'files': []
            }
            
            # Get file info for all in group
            files_with_info = [self.get_file_info(f) for f in group]
            
            # Sort by quality score (if available), then size, then date
            if self.use_ai_ranking and 'quality_score' in files_with_info[0]:
                files_with_info.sort(
                    key=lambda x: (x.get('quality_score', 0), x['size'], x['modified']), 
                    reverse=True
                )
            else:
                files_with_info.sort(
                    key=lambda x: (x['size'], x['modified']), 
                    reverse=True
                )
            
            keep_file = files_with_info[0]
            duplicate_files = files_with_info[1:]
            
            group_info['recommended_keep'] = keep_file['path']
            if 'quality_score' in keep_file:
                group_info['keep_quality_score'] = keep_file['quality_score']
            
            for file_info in files_with_info:
                file_info['action'] = 'KEEP' if file_info['path'] == keep_file['path'] else 'DELETE'
                group_info['files'].append(file_info)
            
            wasted = sum(f['size'] for f in duplicate_files)
            total_wasted_space += wasted
            group_info['wasted_space_mb'] = round(wasted / (1024*1024), 2)
            
            report['groups'].append(group_info)
        
        report['total_wasted_space_mb'] = round(total_wasted_space / (1024*1024), 2)
        report['total_wasted_space_gb'] = round(total_wasted_space / (1024*1024*1024), 2)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"DUPLICATE DETECTION REPORT")
        print(f"{'='*60}")
        print(f"Total images scanned: {report['total_images_scanned']}")
        print(f"Duplicate groups found: {report['duplicate_groups_found']}")
        print(f"Total duplicate files: {report['total_duplicates']}")
        print(f"Wasted space: {report['total_wasted_space_gb']} GB")
        print(f"AI quality ranking: {'ENABLED [+]' if self.use_ai_ranking else 'DISABLED'}")
        print(f"\nDetailed report saved to: {output_file}")
        print(f"{'='*60}\n")
        
        return report
    
    def move_duplicates(self, duplicate_groups, review_folder='_duplicates_review'):
        """Move duplicate files to review folder"""
        review_path = self.root_dir / review_folder
        review_path.mkdir(exist_ok=True)
        
        moved_count = 0
        
        for idx, group in enumerate(duplicate_groups, 1):
            group_folder = review_path / f"group_{idx:04d}"
            group_folder.mkdir(exist_ok=True)
            
            files_with_info = [self.get_file_info(f) for f in group]
            
            # Sort by quality score (if available)
            if self.use_ai_ranking and 'quality_score' in files_with_info[0]:
                files_with_info.sort(
                    key=lambda x: (x.get('quality_score', 0), x['size'], x['modified']), 
                    reverse=True
                )
            else:
                files_with_info.sort(
                    key=lambda x: (x['size'], x['modified']), 
                    reverse=True
                )
            
            # Keep the first (best quality), move others
            for file_info in files_with_info[1:]:
                src = Path(file_info['path'])
                dst = group_folder / src.name
                
                # Handle name conflicts
                counter = 1
                while dst.exists():
                    dst = group_folder / f"{src.stem}_{counter}{src.suffix}"
                    counter += 1
                
                shutil.move(str(src), str(dst))
                moved_count += 1
        
        print(f"Moved {moved_count} duplicate files to {review_path}")
        
    def delete_duplicates(self, duplicate_groups, dry_run=True):
        """Delete duplicate files (keeps highest quality)"""
        if dry_run:
            print("\n=== DRY RUN MODE (no files will be deleted) ===\n")
        
        deleted_count = 0
        freed_space = 0
        
        for group in duplicate_groups:
            files_with_info = [self.get_file_info(f) for f in group]
            
            # Sort by quality score (if available)
            if self.use_ai_ranking and 'quality_score' in files_with_info[0]:
                files_with_info.sort(
                    key=lambda x: (x.get('quality_score', 0), x['size'], x['modified']), 
                    reverse=True
                )
            else:
                files_with_info.sort(
                    key=lambda x: (x['size'], x['modified']), 
                    reverse=True
                )
            
            keep_file = files_with_info[0]
            print(f"\n[KEEP] Keeping: {keep_file['path']}")
            if 'quality_score' in keep_file:
                print(f"   Quality Score: {keep_file['quality_score']:.3f}")
            
            # Delete all except the first (best quality)
            for file_info in files_with_info[1:]:
                if not dry_run:
                    os.remove(file_info['path'])
                deleted_count += 1
                freed_space += file_info['size']
                
                score_info = f" (Quality: {file_info.get('quality_score', 'N/A'):.3f})" if 'quality_score' in file_info else ""
                print(f"   {'[DRY RUN] Would delete' if dry_run else '[DELETE] Deleted'}: {Path(file_info['path']).name}{score_info}")
        
        freed_gb = freed_space / (1024*1024*1024)
        print(f"\n{'Would delete' if dry_run else 'Deleted'} {deleted_count} files")
        print(f"{'Would free' if dry_run else 'Freed'} {freed_gb:.2f} GB")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Find and manage duplicate photos with AI quality ranking')
    parser.add_argument('directory', help='Root directory to scan')
    parser.add_argument('--threshold', type=int, default=5, 
                       help='Similarity threshold (0=exact, 5=very similar, 10=similar)')
    parser.add_argument('--action', choices=['report', 'move', 'delete'], default='report',
                       help='Action to take: report only, move to review folder, or delete')
    parser.add_argument('--no-dry-run', action='store_true',
                       help='Actually delete files (use with --action delete)')
    parser.add_argument('--no-ai', action='store_true',
                       help='Disable AI quality ranking (use file size/date only)')
    
    args = parser.parse_args()
    
    finder = DuplicateFinder(
        args.directory, 
        similarity_threshold=args.threshold,
        use_ai_ranking=not args.no_ai
    )
    finder.scan_images()
    duplicate_groups = finder.find_duplicates()
    
    if not duplicate_groups:
        print("\nNo duplicates found!")
        return
    
    report = finder.generate_report(duplicate_groups)
    
    if args.action == 'move':
        finder.move_duplicates(duplicate_groups)
    elif args.action == 'delete':
        finder.delete_duplicates(duplicate_groups, dry_run=not args.no_dry_run)

if __name__ == '__main__':
    main()