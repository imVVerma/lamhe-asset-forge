# FPCP Project Archaeology

## Investigation Answers

1. **What is this project?** 
   A Python script for finding duplicate and near-duplicate photos, and intelligently picking the best one based on AI quality metrics (faces, smiles, sharpness).

2. **What problem was it intended to solve?** 
   Managing large photo libraries with many similar photos (e.g., photo bursts) and automatically deciding which ones to keep and which to delete based on visual quality, rather than just file size or date.

3. **What evidence in the code supports that interpretation?** 
   The main script is called `photo_duplicate_finder.py`, imports `imagehash` for perceptual hashing, and uses OpenCV Haar cascades to detect faces and smiles. It has a comprehensive `compute_quality_score` function that heavily weights smiling faces.

4. **What are the main technologies used?** 
   Python, OpenCV (`cv2`), Pillow (`PIL`), `imagehash`, and `numpy`.

5. **What is the architecture?** 
   It's a monolithic Python script designed as a CLI tool (using `argparse`). A central class `DuplicateFinder` handles everything from scanning to reporting and file deletion.

6. **What are the major components?**
   - **File Scanner**: Recursively finds image files based on extensions.
   - **Perceptual Hasher**: Generates average hashes (`imagehash`) to find near-matches.
   - **Image Quality Grader**: Uses OpenCV heuristics (Laplacian variance for sharpness, Haar cascades for faces/smiles/eyes, exposure, and composition).
   - **File Operation Engine**: Generates JSON reports, moves duplicates to a review folder, or permanently deletes them.

7. **What is the data flow?** 
   Scan directory for images -> Compute perceptual hash for each -> Compare hashes to group duplicates -> Compute quality scores for each image in a duplicate group -> Sort group by quality -> Recommend best to keep, tag others for move/delete.

8. **What can the current implementation actually do?** 
   It can successfully scan directories, find exact and near-duplicates, calculate their AI quality score, generate a structured JSON report (`duplicate_report.json`), and perform actual file moves or deletions (with a dry-run safety net).

9. **What appears unfinished?** 
   The `Trial` folder contains literal copies of the main script (`something.py`, `xyz.py`) and an `Untitled.ipynb`, suggesting abandoned refactoring or experimentation attempts. The project structure is messy.

10. **What appears broken?** 
    Nothing obviously broken in the logic, but it heavily relies on Haar cascade XML files being available in `cv2.data.haarcascades`. If these are missing in the user's environment, the AI ranking falls back to zero safely, but fails its primary purpose.

11. **What appears to be experimental/prototype code?** 
    The `Trial/` directory as a whole. Also, the `create_test_images.py` script is a basic synthetic test case generator to create colored squares with text to manually verify the hash threshold.

12. **What external APIs/services does it depend on?** 
    None. Everything runs locally on the machine.

13. **What configuration or environment variables does it require?** 
    None. All parameters are passed via CLI arguments (e.g., `--threshold`, `--action`, `--no-ai`).

14. **How would I run it locally?** 
    `python photo_duplicate_finder.py /path/to/photos --action report`

15. **What would I see if it runs successfully?** 
    A CLI progress bar (via `tqdm`) followed by a summary output like `DUPLICATE DETECTION REPORT`, and a `duplicate_report.json` file generated in the current working directory.

16. **What are the most important files and what does each do?**
    - `photo_duplicate_finder.py`: The core application logic and CLI entry point.
    - `create_test_images.py`: A helper script to quickly generate synthetic dummy images to test the duplicate finding logic.

17. **Is there evidence of the original motivation or design decisions?** 
    The inline comments (e.g., `# Smile score - HIGHEST WEIGHT`) heavily imply that the creator was frustrated with sorting through bursts of group photos where people might be blinking or not smiling, wanting to automate the subjective decision of "which burst photo is best."

18. **What technical concepts was I probably trying to learn?** 
    Perceptual hashing (identifying similar images without pixel-perfect matches) and basic computer vision with OpenCV (Haar cascades, image histograms, Laplacian variance for sharpness).

19. **What would be required to turn this into a clean, presentable project?** 
    Remove the `Trial` directory. Add a `requirements.txt` or `pyproject.toml`. Add a `README.md`. Move the class logic into a module folder, separating the CLI wrapper. Add standard unit tests (e.g., `pytest`) instead of a synthetic image generation script.

20. **What would you recommend I do with it:**
    **Extract an idea**. The concept of AI-ranking burst photos is excellent and highly practical. However, Haar cascades are very outdated and brittle. Extract the perceptual hashing and CLI workflow, but rewrite the image scoring using a modern, lightweight deep learning model (like MediaPipe) for vastly superior facial landmark and expression detection.

---

## Final Summaries

### A. 5-Sentence Explanation
This project is a command-line tool that scans your folders to find duplicate and near-duplicate photos. Instead of just picking a random duplicate to keep, it uses computer vision to look at the content of the photos. It checks for sharpness, good exposure, open eyes, and smiles to intelligently score which version of the photo is the best. It then generates a report or automatically moves/deletes the lower-quality duplicates. It's designed to solve the problem of hoarding dozens of slightly different burst photos from a smartphone.

### B. Suggested GitHub README Structure
1. **Title and Description**: "Photo Duplicate Finder" and a brief summary of the AI ranking feature.
2. **Features**: List perceptual hashing, AI quality ranking (smiles, eyes, sharpness), and dry-run safety.
3. **Installation**: Instructions for cloning and running `pip install -r requirements.txt`.
4. **Usage**: Examples of running the CLI with different flags (`--action report`, `--action move`, `--threshold`).
5. **How it Works**: A brief section explaining perceptual hashing and the OpenCV heuristics used for scoring.
6. **Disclaimer**: A warning to always run with `--action report` first to avoid accidental data loss.

### C. 5 Most Important Things to Understand
1. **Perceptual Hashing vs. Cryptographic Hashing**: Understand why `imagehash` is used instead of MD5/SHA (it allows for matching *similar* images like compressed/resized variants, not just exact byte copies).
2. **OpenCV Haar Cascades**: Know how the legacy face and smile detection works in this script and its limitations compared to modern CNNs.
3. **Laplacian Variance**: Understand that this mathematical operation is a standard, fast way to measure image blur/sharpness.
4. **The Scoring Weights**: Remember that smiles (`25%`) and sharpness (`20%`) are the most heavily weighted factors in the quality algorithm.
5. **Dry Run Logic**: Understand that the script is built defensively, defaulting to a report-only mode to prevent accidental deletion of family photos.

### D. Unanswered Questions
- Why are there multiple identical copies of the script in the `Trial` directory? Was an ambitious refactoring attempted and abandoned?
- Did the user ever actually use this on their real photo library, or did it stop at the synthetic `create_test_images.py` phase?
- How well do the Haar cascades actually perform on real-world smartphone photos with complex lighting?

### E. 5 Points to Make this Robust and Product Ready
1. **Upgrade the AI Model**: Replace the legacy OpenCV Haar cascades with a modern, lightweight deep learning library (e.g., MediaPipe or RetinaFace) for significantly better accuracy in detecting faces, landmarks, and expressions under varied lighting and angles.
2. **Implement Checkpointing & State Recovery**: For large photo libraries (e.g., 50,000+ images), the scanning and hashing process takes a long time. Implement a caching layer (like a local SQLite database) to save perceptual hashes and scores so the script can resume if interrupted without starting over.
3. **Multi-threading/Multiprocessing**: Reading and hashing large images is heavily I/O and CPU bound. Implement multiprocessing to compute hashes and quality scores in parallel across multiple CPU cores to dramatically speed up the scan time.
4. **GUI / Web Interface for Review**: Command-line output is intimidating for general users managing their personal photos. Build a simple local web interface (using Streamlit or Gradio) that allows users to visually compare the duplicate groups side-by-side and manually override the AI's "keep/delete" recommendations before executing.
5. **Add Robust Error Handling & Logging**: Implement proper logging (using Python's `logging` module) instead of `print()` statements. Handle edge cases like corrupted image files, permission denied errors, or unsupported file formats gracefully without crashing the entire run.


