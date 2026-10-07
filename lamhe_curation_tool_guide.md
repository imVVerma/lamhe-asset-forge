# Lamhe Photo Curation Utility: How-To Guide

Welcome to the official workflow guide for the **Lamhe** media curation utility. This computer-vision tool is designed to automate duplicate removal, blur filtering, quality scoring, and image compression for event photography.

---

## 📸 The Lamhe Event Workflow

To maximize storage efficiency and keep our OneDrive portfolios organized, insert the Streamlit app **after** staging your photos locally from the memory card, but **before** uploading to the cloud.

```text
[1. Camera SD Card] 
       ↓
[2. Card Reader & Local Temp Folder] 
       ↓
[3. 🚀 Streamlit App (Curate, Deduplicate, Compress)]  <-- Insert Here
       ↓
[4. Final Cleaned Output Folder] 
       ↓
[5. Official OneDrive Portfolio]
```

---

## 🚀 Getting Started & Running the App

Depending on your role and what you are trying to test, there are two ways to access the app:

### Option A: Cloud Testing (For general testers & mobile users)
Simply click the public link below to access the live app. No installation required!
👉 **[lamhe-asset-forge-fpcp.streamlit.app](https://lamhe-asset-forge-fpcp.streamlit.app/)**
*(Note: You must use the "Cloud / Mobile" mode to upload files here. Do not try to type `C:\` paths).*

### Option B: Local Heavy-Duty Mode (For processing 160GB portfolios)
If you need to process massive folders directly from your hard drive, you must run the app locally:
1. Open your terminal or command prompt inside the project directory.
2. Launch the application using Python's module runner:
   ```bash
   python -m streamlit run app.py
   ```
3. The local web interface will automatically open in your default browser at `http://localhost:8501`.

---

## 🛠️ Application Features & Operational Guardrails

### 1. Upload & Processing Options
* **Local Folder / Bulk Upload:** Select or drag-and-drop your batched event photos directly into the interface.
* **Cloud / Mobile Uploads:** If uploading via alternative pathways, note that files must first be saved or staged on the server before downstream processing can occur.
* **Workflow Dependency Rule:** 
  > ⚠️ **Important:** The **Scan for Duplicates** button is locked until you successfully complete the **Save Upload to Server** action. This prevents scanning errors on un-indexed files.

### 2. Local vs. Cloud Architectures (Why `C:\` paths fail online)
It is critical to understand *where* the Python code is running to avoid "Directory Not Found" errors.

* **💻 Local Machine Mode (Running `python -m streamlit run app.py`):** 
  When you launch the app directly on your laptop, the code runs natively on your machine. This mode allows you to type direct paths like `C:\Users\Name\Pictures` because the app has full access to your Windows hard drive. This is **required** for processing the massive 160GB portfolio, as it bypasses upload limits.
  
* **☁️ Cloud / Mobile Mode (Accessing via `lamhe-asset-forge.streamlit.app`):** 
  When you access the app via a public internet link, the Python code is executing on a remote Linux server. That cloud server **cannot** see your laptop's `C:\` drive or your phone's photo gallery due to browser security walls. If you try to use "Local Machine Mode" on the public website and type a `C:\` path, it will throw a 404/Not Found error. You **must** use the Cloud/Mobile Mode radio button on the website, which provides an `Upload Photos` button to securely transfer a batch of photos (up to ~200MB) from your device to the cloud server for processing.

---

## 🔮 Roadmap & Future Features

The following computer-vision extensions are planned for upcoming releases to further streamline Lamhe's event sorting:
* **Smart Grouping by People:** Automatically cluster images by recurring faces to organize event albums by specific members or speakers.
* **Group Photo Expression Checker:** Scan group shots to catch blinks, closed eyes, or awkward expressions.
* **VIP & Key Member Tagging:** Seed reference photos of core leads to automatically surface every frame they appear in.
* **Crowd Engagement Metrics:** Estimate crowd size and orientation toward the stage to score high-energy event moments.