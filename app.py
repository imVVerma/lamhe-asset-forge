import streamlit as st
import os
from PIL import Image
from photo_duplicate_finder import DuplicateFinder
from photo_compressor import run_compression

st.set_page_config(page_title="Photo Duplicate Finder", layout="wide")

st.title("Photo Duplicate Finder - Review & Clean")

# State management
if 'report' not in st.session_state:
    st.session_state.report = None
if 'user_decisions' not in st.session_state:
    st.session_state.user_decisions = {}

scan_dir = st.text_input("Enter directory path to scan:", "")
threshold = st.slider("Similarity Threshold (0=Exact, 5=Very Similar, 10=Similar)", 0, 15, 5)
use_ai = st.checkbox("Use AI Quality Ranking", value=True)

if st.button("Scan Directory"):
    if not scan_dir or not os.path.isdir(scan_dir):
        st.error("Please enter a valid directory path.")
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
            
            # Clear progress UI elements when done
            progress_bar.empty()
            status_text.empty()
            
            if not dup_groups:
                st.success("No duplicates found!")
                st.session_state.report = None
            else:
                # Generate report to get the AI recommendations
                report = finder.generate_report(dup_groups, output_file='streamlit_report.json')
                st.session_state.report = report
                
                # Initialize user decisions based on AI recommendation
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
                
                # Button to select this image to keep
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
        st.session_state.report = None # Reset after deletion
        st.rerun()

# Compression Section
st.divider()
st.header("📸 Shrink & Save")
st.write("After cleaning up your duplicates, compress the remaining photos to save space while keeping all the important camera data (EXIF).")

c_scan_dir = st.text_input(
    "Which folder do you want to compress?", 
    scan_dir,
    help="We will safely create a new '_compressed' folder inside this directory so your original files are never touched or modified."
)

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
    
if st.button("Start Compression", type="primary"):
    if not c_scan_dir or not os.path.isdir(c_scan_dir):
        st.error("Please enter a valid directory.")
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
                progress_callback=c_progress
            )
            
            c_prog_bar.empty()
            c_stat_text.empty()
            
            if success:
                st.success(msg)
            else:
                st.error(msg)
