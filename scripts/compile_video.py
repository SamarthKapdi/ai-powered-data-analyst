"""Compile captured screenshot frames into a high-quality demo MP4 video."""

import os
from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
FRAMES_DIR = ROOT_DIR / "docs" / "demo" / "frames"
OUTPUT_VIDEO = ROOT_DIR / "docs" / "demo" / "insightflow-demo.mp4"

def main():
    if not FRAMES_DIR.exists():
        print(f"Error: Frames directory not found: {FRAMES_DIR}")
        return

    frame_files = sorted(list(FRAMES_DIR.glob("frame_*.png")))
    if not frame_files:
        print("Error: No frames found in frames directory.")
        return

    print(f"Compiling {len(frame_files)} frames into {OUTPUT_VIDEO}...")

    # Read first frame to get dimensions
    first_frame = cv2.imread(str(frame_files[0]))
    height, width, _ = first_frame.shape

    # Video settings: ~6 FPS matches the capture interval of ~150ms
    fps = 6.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(OUTPUT_VIDEO), fourcc, fps, (width, height))

    for idx, f in enumerate(frame_files):
        img = cv2.imread(str(f))
        if img is not None:
            out.write(img)

    out.release()
    file_size_kb = OUTPUT_VIDEO.stat().st_size / 1024
    duration_sec = len(frame_files) / fps

    print(f"Success! Video created at: {OUTPUT_VIDEO}")
    print(f"Duration: {duration_sec:.1f} seconds | Size: {file_size_kb:.1f} KB | Resolution: {width}x{height}")

    # Clean up frames directory to save repository space
    for f in frame_files:
        try:
            f.unlink()
        except Exception:
            pass
    try:
        FRAMES_DIR.rmdir()
        print("Temporary frames cleaned up.")
    except Exception:
        pass

if __name__ == "__main__":
    main()
