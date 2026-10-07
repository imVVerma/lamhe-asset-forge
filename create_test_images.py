import os
from PIL import Image, ImageDraw
from pathlib import Path

def create_test_images(target_dir='test_photos'):
    path = Path(target_dir)
    path.mkdir(exist_ok=True)
    
    # 1. Base Image
    img1 = Image.new('RGB', (800, 600), color=(73, 109, 137))
    d = ImageDraw.Draw(img1)
    d.text((10,10), "Base Image", fill=(255,255,0))
    img1.save(path / 'image1.jpg')
    print("Created image1.jpg")
    
    # 2. Exact Copy (different name)
    img1.save(path / 'image1_copy.jpg')
    print("Created image1_copy.jpg")
    
    # 3. Resized version (should be detected by perceptual hash)
    img1_small = img1.resize((400, 300))
    img1_small.save(path / 'image1_small.jpg')
    print("Created image1_small.jpg")
    
    # 4. Modified version (slight change, should still be similar)
    img1_mod = img1.copy()
    d_mod = ImageDraw.Draw(img1_mod)
    d_mod.rectangle([200, 200, 300, 300], fill=(255, 0, 0))
    img1_mod.save(path / 'image1_modified.jpg')
    print("Created image1_modified.jpg")
    
    # 5. Completely different image
    img2 = Image.new('RGB', (800, 600), color=(137, 73, 109))
    d2 = ImageDraw.Draw(img2)
    d2.text((10,10), "Different Image", fill=(255,255,255))
    img2.save(path / 'image2.jpg')
    print("Created image2.jpg")

if __name__ == '__main__':
    create_test_images()
