#!/usr/bin/env python3
"""
scripts/transcode_video.py — Transcodes Playwright WebM recordings to standard MP4 (H.264/MP4V).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import cv2

OUTPUT_DIR = Path("demo_output").resolve()
INPUT_WEBM = OUTPUT_DIR / "aivara_v1_demo.webm"
OUTPUT_MP4 = OUTPUT_DIR / "aivara_v1_demo.mp4"


def transcode(input_file: Path, output_file: Path) -> Path:
    if not input_file.exists():
        raise FileNotFoundError(f"Source video not found: {input_file}")

    print(f"🎬 Transcoding {input_file.name} to universal MP4 format...")
    cap = cv2.VideoCapture(str(input_file))

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"📊 Video stream details: {width}x{height} @ {fps:.1f} fps ({total_frames} frames)")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_file), fourcc, fps, (width, height))

    count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        count += 1
        if count % 300 == 0:
            pct = (count / total_frames) * 100 if total_frames > 0 else 0
            print(f"  Processed {count}/{total_frames} frames ({pct:.1f}%)...")

    cap.release()
    out.release()

    size_mb = output_file.stat().st_size / (1024 * 1024)
    duration_s = count / fps if fps > 0 else 0
    print(f"✅ Transcode complete: {output_file} ({size_mb:.2f} MB, {duration_s:.1f}s)")
    return output_file


if __name__ == "__main__":
    transcode(INPUT_WEBM, OUTPUT_MP4)
