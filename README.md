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

---

## 🧑‍🤝‍🧑 Advanced Tool: People Grouper (CLI)

The repository also includes `people_grouper.py`, an advanced script that uses facial recognition to automatically group your entire portfolio into folders by person (e.g., `person_01/`, `person_02/`). 

### Installation (Requires C++)
`face_recognition` uses dlib under the hood which needs a C++ build step. This must be run on your local laptop, not the cloud:

```bash
# Windows
pip install cmake
pip install dlib
pip install face_recognition tqdm Pillow

# Mac
brew install cmake
pip install face_recognition tqdm Pillow

# Linux
sudo apt install cmake build-essential
pip install face_recognition tqdm Pillow
```

### Usage
Run this directly from your terminal on your massive local folders:
```bash
# Default run
python people_grouper.py /path/to/portfolio

# Stricter matching (fewer false merges)
python people_grouper.py /path/to/portfolio --tolerance 0.5

# More lenient (same person across different lighting/angles)
python people_grouper.py /path/to/portfolio --tolerance 0.65

# Raise min appearances (only give folders to people in 5+ photos)
python people_grouper.py /path/to/portfolio --min-appearances 5

# Use CNN model if you have a GPU (significantly better accuracy)
python people_grouper.py /path/to/portfolio --model cnn
```

### Output
```text
portfolio_by_person/
├── person_01/    ← 84 photos  (your most photographed person)
├── person_02/    ← 61 photos
├── person_03/    ← 47 photos
│   ...
├── person_unknown/   ← one-off appearances, randoms
└── people_grouping_report.json
```
*Note: A UI for Streamlit to easily rename `person_01` → `Arjun` is on our project roadmap!*
