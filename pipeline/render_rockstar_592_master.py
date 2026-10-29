import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(".").resolve()
OUT_DIR = BASE_DIR / "output" / "rockstar_games"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONCAT_FILE = OUT_DIR / "scenes_cuts_592.txt"
VO_MASTER = BASE_DIR / "companies" / "rockstar_games" / "voiceover_master.mp3"
BGM_FILE = BASE_DIR / "output" / "pipeline_bgm_173.wav"
SRT_FILE = OUT_DIR / "the_history_of_rockstar_games_592.srt"

OUT_VIDEO = OUT_DIR / "THE_ENTIRE_HISTORY_OF_ROCKSTAR_GAMES_592_BEATS_MASTER.mp4"
DESKTOP_VIDEO = Path(r"C:\Users\Emmanuel\Desktop\THE_ENTIRE_HISTORY_OF_ROCKSTAR_GAMES_592_BEATS_MASTER.mp4")
LOG_FILE = OUT_DIR / "render_592.log"

assert CONCAT_FILE.exists(), f"Missing concat file: {CONCAT_FILE}"
assert VO_MASTER.exists(), f"Missing voiceover: {VO_MASTER}"
assert BGM_FILE.exists(), f"Missing BGM: {BGM_FILE}"
assert SRT_FILE.exists(), f"Missing SRT: {SRT_FILE}"

probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(VO_MASTER)]
total_dur = float(subprocess.check_output(probe_cmd).decode().strip())

print("=" * 80)
print("=== LAUNCHING ACCELERATED 592-BEAT MASTER DOCUMENTARY RENDER ===")
print("=" * 80)
print(f"  Target Duration:  {total_dur:.2f}s ({total_dur/60:.2f} minutes)")
print(f"  Visual Cuts:      592 scenes (Average 2.75s per cut)")
print(f"  Resolution:       1920x1080 (16:9 widescreen, #FAF9F6 canvas)")
print(f"  Primary Encoder:  Intel Quick Sync Video (h264_qsv)")
print(f"  Output Video:     {OUT_VIDEO}")
print(f"  Desktop Copy:     {DESKTOP_VIDEO}")
print(f"  Log File:         {LOG_FILE}")
print("=" * 80)

cmd_qsv = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(CONCAT_FILE),
    "-i", str(VO_MASTER),
    "-i", str(BGM_FILE),
    "-i", str(SRT_FILE),
    "-filter_complex",
    (
        "[0:v]format=nv12[v_clean];"
        "[2:a]aloop=loop=-1:size=2e+09,volume=0.14[bgm_loop];"
        "[bgm_loop][1:a]sidechaincompress=threshold=0.03:ratio=4:attack=50:release=350[bgm_ducked];"
        "[1:a][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[a_final]"
    ),
    "-map", "[v_clean]",
    "-map", "[a_final]",
    "-map", "3:s",
    "-c:v", "h264_qsv",
    "-b:v", "5500k",
    "-c:a", "aac",
    "-b:a", "192k",
    "-c:s", "mov_text",
    "-metadata:s:s:0", "language=eng",
    "-metadata:s:s:0", "title=English (592-Beat Word-Level)",
    "-r", "30",
    "-t", f"{total_dur:.2f}",
    "-movflags", "+faststart",
    str(OUT_VIDEO)
]

t0 = time.time()
print("[*] Encoding with h264_qsv hardware acceleration...")

with open(LOG_FILE, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(cmd_qsv, stdout=lf, stderr=lf)
    ret = proc.wait()

if ret != 0:
    print(f"[!] h264_qsv returned error code {ret}. Falling back to CPU libx264...")
    cmd_cpu = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(CONCAT_FILE),
        "-i", str(VO_MASTER),
        "-i", str(BGM_FILE),
        "-i", str(SRT_FILE),
        "-filter_complex",
        (
            "[0:v]format=yuv420p[v_clean];"
            "[2:a]aloop=loop=-1:size=2e+09,volume=0.14[bgm_loop];"
            "[bgm_loop][1:a]sidechaincompress=threshold=0.03:ratio=4:attack=50:release=350[bgm_ducked];"
            "[1:a][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[a_final]"
        ),
        "-map", "[v_clean]",
        "-map", "[a_final]",
        "-map", "3:s",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng",
        "-metadata:s:s:0", "title=English (592-Beat Word-Level)",
        "-r", "30",
        "-t", f"{total_dur:.2f}",
        "-movflags", "+faststart",
        str(OUT_VIDEO)
    ]
    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        proc2 = subprocess.Popen(cmd_cpu, stdout=lf, stderr=lf)
        ret2 = proc2.wait()
    if ret2 != 0:
        print(f"[ERROR] Render failed. See log: {LOG_FILE}")
        sys.exit(1)

elapsed = time.time() - t0
file_size_mb = OUT_VIDEO.stat().st_size / (1024 * 1024)

print("=" * 80)
print(f"[+] RENDER COMPLETE IN {elapsed:.2f}s ({elapsed/60:.2f} minutes)!")
print(f"  File Size: {file_size_mb:.2f} MB")
print(f"  Video Path: {OUT_VIDEO}")
print("=" * 80)

# Copy to Desktop
try:
    print(f"[*] Copying master video to Desktop: {DESKTOP_VIDEO}")
    shutil.copy2(OUT_VIDEO, DESKTOP_VIDEO)
    print(f"[+] Copied to Desktop successfully!")
except Exception as e:
    print(f"[!] Desktop copy notice: {e}")

# Verification snapshots at key timestamps
print("[*] Generating verification snapshot frames...")
snap_times = [
    ("prologue_hook", 1.0),
    ("cash_explosion", 9.0),
    ("dma_scottish_garage", 125.0),
    ("houser_brothers_soho", 340.0),
    ("gta3_revolution", 580.0),
    ("hot_coffee_crisis", 820.0),
    ("crunch_and_lawsuits", 1100.0),
    ("rdr2_peak", 1350.0),
    ("epilogue_mirror", 1610.0)
]

SNAP_DIR = OUT_DIR / "verification_snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)

for name, ts in snap_times:
    snap_out = SNAP_DIR / f"snap_{name}_{int(ts)}s.jpg"
    cmd_snap = [
        "ffmpeg", "-y", "-ss", f"{ts:.2f}",
        "-i", str(OUT_VIDEO),
        "-frames:v", "1", "-q:v", "2",
        str(snap_out)
    ]
    subprocess.run(cmd_snap, capture_output=True)
    if snap_out.exists():
        print(f"  [+] Snapshot at {ts}s: {snap_out.name}")

print("=" * 80)
print("[+] ALL TASKS FINISHED SUCCESSFULLY")
print("=" * 80)
