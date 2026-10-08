import streamlit as st
import os
import shutil
import uuid
import zipfile
from PIL import Image
from photo_duplicate_finder import DuplicateFinder
from photo_compressor import run_compression

st.set_page_config(page_title="Lamhe Asset Forge", layout="wide")

st.title("📸 Lamhe Asset Forge")

# State management
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'report' not in st.session_state:
    st.session_state.report = None
if 'user_decisions' not in st.session_state:
    st.session_state.user_decisions = {}

mode = st.radio("Operation Mode", ["Local Machine (Folder Path)", "Cloud / Mobile (Upload Photos)"])
threshold = st.slider("Similarity Threshold (0=Exact, 5=Very Similar, 10=Similar)", 0, 15, 5)
use_ai = st.checkbox("Use AI Quality Ranking", value=True)

scan_dir = ""
scan_ready = False

if mode == "Cloud / Mobile (Upload Photos)":
    st.warning("☁️ **Cloud / Mobile Mode**: Upload capacity limited to ~200MB (approx 50-100 photos) per batch to prevent server crashes. Perfect for quick event cleanups from your phone.")
    cloud_dir = os.path.join("cloud_sessions", st.session_state.session_id)
    os.makedirs(cloud_dir, exist_ok=True)
    scan_dir = cloud_dir
    
    uploaded_files = st.file_uploader("Upload Event Photos", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    if st.button("Save Uploads to Server"):
        if not uploaded_files:
            st.error("Please upload some photos first.")
        else:
            with st.spinner("Saving uploads..."):
                for f in os.listdir(cloud_dir):
                    fp = os.path.join(cloud_dir, f)
                    if os.path.isfile(fp):
                        try:
                            os.remove(fp)
                        except:
                            pass
                        
                for uploaded_file in uploaded_files:
                    file_path = os.path.join(cloud_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                st.success(f"Saved {len(uploaded_files)} photos ready for scanning!")
                st.rerun() # Force UI refresh to unlock the scan button
                
    has_images = len([f for f in os.listdir(cloud_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]) > 0
    scan_ready = has_images
    if not has_images:
        st.info("Please upload and save your photos before scanning.")
else:
    st.info("💻 **Local Machine Mode (Host Environment)**: Reads directly from the server's hard drive where this app is currently hosted. (If you are accessing this via a cloud URL, this will look at the cloud server's files, not your personal laptop.)")
    
    with st.form("local_path_form"):
        col1, col2 = st.columns([4, 1])
        with col1:
            raw_scan_dir = st.text_input("Enter directory path to scan:", "", placeholder="e.g., C:/Users/YourName/Pictures/Portfolio")
        with col2:
            st.write("") # spacing
            st.write("") # spacing
            confirm_path = st.form_submit_button("Confirm Path")
            
    if raw_scan_dir:
        # Strip spaces, quotes, and hidden Windows unicode characters
        scan_dir = raw_scan_dir.strip(' "\'\u202a\u202b\u202c')
        if os.path.isdir(scan_dir):
            st.success(f"✅ Folder verified! Ready to scan.")
            scan_ready = True
        else:
            if scan_dir.lower().startswith("c:\\") and os.name != 'nt':
                st.error("⚠️ **Cloud Environment Detected**: You are trying to enter a Windows `C:\\` path, but this app is currently hosted on a Linux cloud server. Please switch to **Cloud / Mobile (Upload Photos)** mode above to upload your local files.")
            else:
                st.error("❌ Directory not found on the host machine. Please check the path.")
            scan_ready = False
    else:
        scan_dir = ""
        scan_ready = False

if not scan_ready:
    st.caption("Enter a valid directory path or upload files above to enable scanning.")

if st.button("Scan for Duplicates", type="primary", disabled=not scan_ready):
    if not scan_dir or not os.path.isdir(scan_dir):
        st.error(f"Please provide a valid directory or upload files first.")
    else:
        progress_text = "Scanning directory... (Cache is active)"
        progress_bar = st.progress(0, text=progress_text)
        status_text = st.empty()
        
        def update_progress(current, total, current_file):
            if current % 5 == 0 or current == total - 1:
                progress = (current + 1) / total
                progress_bar.progress(progress, text=f"Scanning {current + 1}/{total}")
                status_text.text(f"Processing: {os.path.basename(current_file)}")

        with st.spinner("Compiling results..."):
            finder = DuplicateFinder(
                scan_dir, 
                similarity_threshold=threshold, 
                use_ai_ranking=use_ai,
                progress_callback=update_progress
            )
            finder.scan_images()
            
            status_text.text("Finding duplicates among hashes...")
            dup_groups = finder.find_duplicates()
            
            progress_bar.empty()
            status_text.empty()
            
            if not dup_groups:
                st.success("No duplicates found!")
                st.session_state.report = None
            else:
                report = finder.generate_report(dup_groups, output_file=os.path.join(scan_dir, 'streamlit_report.json'))
                st.session_state.report = report
                
                st.session_state.user_decisions = {}
                for group in report['groups']:
                    group_id = group['group_id']
                    recommended_keep = group.get('recommended_keep')
                    st.session_state.user_decisions[group_id] = recommended_keep

if st.session_state.report:
    report = st.session_state.report
    st.header(f"Found {report['duplicate_groups_found']} Duplicate Groups")
    st.info(f"Total potential wasted space: {report['total_wasted_space_mb']} MB")
    
    for group in report['groups']:
        group_id = group['group_id']
        st.subheader(f"Group {group_id}")
        
        files = group['files']
        cols = st.columns(len(files))
        
        for i, file_info in enumerate(files):
            filepath = file_info['path']
            filename = os.path.basename(filepath)
            
            with cols[i]:
                try:
                    with Image.open(filepath) as img:
                        img.thumbnail((300, 300))
                        st.image(img, caption=filename, use_container_width=True)
                except Exception as e:
                    st.error(f"Cannot load image: {e}")
                
                size_mb = file_info['size_mb']
                st.write(f"Size: {size_mb} MB")
                if 'quality_score' in file_info:
                    st.write(f"**AI Score: {file_info['quality_score']:.3f}**")
                
                if st.button(f"Keep {filename}", key=f"btn_{group_id}_{i}"):
                    st.session_state.user_decisions[group_id] = filepath
                    st.rerun()

                if st.session_state.user_decisions.get(group_id) == filepath:
                    st.success("✅ Selected to Keep")
                else:
                    st.error("🗑️ Marked for Deletion")
        
        st.divider()
    
    if st.button("Execute Deletions", type="primary"):
        deleted_count = 0
        freed_mb = 0
        
        for group in report['groups']:
            group_id = group['group_id']
            keep_path = st.session_state.user_decisions.get(group_id)
            
            for file_info in group['files']:
                if file_info['path'] != keep_path:
                    try:
                        os.remove(file_info['path'])
                        deleted_count += 1
                        freed_mb += file_info['size_mb']
                    except Exception as e:
                        st.error(f"Failed to delete {file_info['path']}: {e}")
        
        st.success(f"Successfully deleted {deleted_count} files and freed {freed_mb:.2f} MB!")
        st.session_state.report = None 
        st.rerun()

# Compression Section
st.divider()
st.header("📸 Shrink & Save")
st.write("After cleaning up your duplicates, compress the remaining photos to save space while keeping all the important camera data (EXIF).")

if mode == "Cloud / Mobile (Upload Photos)":
    c_scan_dir = scan_dir
    st.info("☁️ Files will be compressed directly from your cloud uploads. The download link will appear below when finished.")
else:
    raw_c_scan_dir = st.text_input(
        "Which folder do you want to compress?", 
        scan_dir,
        placeholder="e.g., C:/Users/YourName/Pictures/Portfolio",
        help="We will safely create a new '_compressed' folder inside this directory so your original files are never touched or modified."
    )
    c_scan_dir = raw_c_scan_dir.strip(' "\'\u202a\u202b\u202c') if raw_c_scan_dir else ""

st.subheader("Compression Options")
col1, col2 = st.columns(2)
with col1:
    do_archive = st.checkbox(
        "Create High-Quality Backup (Archive)", 
        value=True,
        help="Keeps the full, original resolution of your photos but applies gentle compression to save space. Perfect for long-term storage."
    )
    arch_q = st.slider(
        "Backup Quality", 
        10, 100, 90,
        help="90 is the sweet spot. It drastically reduces file size while remaining visually indistinguishable from the original."
    )
with col2:
    do_web = st.checkbox(
        "Create Small Versions (Web/Social)", 
        value=True,
        help="Resizes the photos to fit perfectly on standard screens (max 1920px). Excellent for quickly sharing on WhatsApp, Instagram, or a website."
    )
    web_q = st.slider(
        "Web/Social Quality", 
        10, 100, 75,
        help="75 provides a very small file size (~500KB) while still looking crisp on phones and web browsers."
    )
    strip_exif = st.checkbox(
        "Strip EXIF Data (Privacy)",
        value=False,
        help="Removes camera model, GPS, and timestamp metadata. Check this if sharing publicly online. Uncheck to preserve original metadata."
    )
    
if st.button("Start Compression", type="primary"):
    if not c_scan_dir or not os.path.isdir(c_scan_dir):
        if c_scan_dir.lower().startswith("c:\\") and os.name != 'nt':
            st.error("⚠️ **Cloud Environment Detected**: You are trying to enter a Windows `C:\\` path, but this app is currently hosted on a Linux cloud server. Please switch to **Cloud / Mobile (Upload Photos)** mode above to upload your local files.")
        else:
            st.error("Please enter a valid directory.")
    elif do_web and do_archive and web_q > arch_q:
        st.error("⚠️ **Conflicting Settings**: Your Web Quality is set higher than your Backup Quality! Please ensure Web Quality is less than or equal to Backup Quality.")
    else:
        c_prog_text = "Starting compression..."
        c_prog_bar = st.progress(0, text=c_prog_text)
        c_stat_text = st.empty()
        
        def c_progress(current, total, current_file):
            if total > 0 and (current % 5 == 0 or current == total):
                prog = min(current / total, 1.0)
                c_prog_bar.progress(prog, text=f"Compressing {current}/{total}")
                c_stat_text.text(f"Processing: {os.path.basename(current_file)}")

        with st.spinner("Compressing images..."):
            success, msg = run_compression(
                c_scan_dir, 
                archive_quality=arch_q, 
                web_quality=web_q, 
                do_archive=do_archive, 
                do_web=do_web,
                strip_exif=strip_exif,
                progress_callback=c_progress
            )
            
            c_prog_bar.empty()
            c_stat_text.empty()
            
            if success:
                st.success(msg)
                
                # If Cloud Mode, zip and offer download
                if mode == "Cloud / Mobile (Upload Photos)":
                    zip_path = os.path.join(c_scan_dir, "compressed_photos.zip")
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        compressed_dir = os.path.join(c_scan_dir, "_compressed")
                        for root, _, files in os.walk(compressed_dir):
                            for file in files:
                                f_path = os.path.join(root, file)
                                arcname = os.path.relpath(f_path, compressed_dir)
                                zipf.write(f_path, arcname)
                                
                    with open(zip_path, "rb") as f:
                        st.download_button("📥 Download Compressed Photos (ZIP)", f, file_name="compressed_photos.zip", type="primary")
            else:
                st.error(msg)
