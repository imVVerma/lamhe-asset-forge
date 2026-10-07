# 📸 Lamhe Asset Forge

**A computer-vision utility built for Lamhe to automate duplicate detection, blur filtering, and quality scoring for club event photography.**

## What does this do?

If you've ever come back from a club event with thousands of photos and felt overwhelmed trying to sort through them, **Lamhe Asset Forge** is for you. It uses modern AI and Computer Vision to do the heavy lifting:

1. **🧹 Smart Duplicate Detection**: It scans your folders and finds similar photos using perceptual hashing.
2. **🤖 AI Quality Scoring**: When it finds duplicates, it uses Google's MediaPipe Deep Learning models to analyze which photo is actually *better*. It checks for sharpness, exposure, and the number of clear faces/smiles to automatically recommend the best shot to keep.
3. **📦 Shrink & Save (Dual-Track Compression)**: Once your portfolio is clean, you can compress it into two tracks without losing important camera data (EXIF):
   - **Archive Track**: Keeps full resolution but gently compresses the file for long-term storage.
   - **Web/Social Track**: Resizes the photos perfectly for WhatsApp, Instagram, or your club's website, saving massive amounts of space.
4. **🎨 Beautiful Web Interface**: You don't need to be a programmer to use it! The entire process is wrapped in a clean, interactive web app where you can visually review the AI's recommendations before deleting anything.

## How to run it

### 1. Install Requirements
Make sure you have Python installed, then install the required libraries:
```bash
pip install streamlit opencv-python Pillow imagehash mediapipe piexif tqdm
```

### 2. Launch the Web App
Open your terminal in the project folder and run:
```bash
python -m streamlit run app.py
```

This will automatically open the beautiful web interface in your browser where you can start cleaning your event photos!

## Under the Hood
- **Multiprocessing**: Built from the ground up to utilize all of your CPU cores. It can chew through gigabytes of photos incredibly fast.
- **Resumable**: If the app is closed or crashes midway through a 100GB scan, don't panic. It checkpoints its progress and will pick up exactly where it left off!
- **Non-Destructive**: The compression tool safely creates a `_compressed` folder and *never* modifies your original raw photos.
