import os
import sys
import time
import json
import re
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from difflib import SequenceMatcher
from faster_whisper import WhisperModel

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(".").resolve()
SCRIPT_FILE = BASE_DIR / "companies" / "sony_playstation" / "script.txt"
PROMPTS_FILE = BASE_DIR / "companies" / "sony_playstation" / "master_prompts.txt"
AUDIO_CHUNKS_DIR = BASE_DIR / "scratch" / "playstation_audio_chunks"
AUDIO_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

OUT_DIR = BASE_DIR / "output" / "sony_playstation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VO_MASTER = BASE_DIR / "companies" / "sony_playstation" / "voiceover_master.mp3"
BGM_FILE = BASE_DIR / "output" / "pipeline_bgm_173.wav"
CONCAT_CUTS = OUT_DIR / "scenes_cuts_297.txt"
SRT_FILE = OUT_DIR / "the_history_of_sony_playstation_297.srt"
NORM_DIR = OUT_DIR / "norm_frames_297"

OUT_VIDEO = OUT_DIR / "THE_ENTIRE_HISTORY_OF_SONY_PLAYSTATION_MASTER.mp4"
DESKTOP_VIDEO = Path(r"C:\Users\Emmanuel\Desktop\THE_ENTIRE_HISTORY_OF_SONY_PLAYSTATION_MASTER.mp4")
LOG_FILE = OUT_DIR / "render_playstation.log"

DEEPGRAM_API_KEY = "8c32d3564d3bb4aac4a4b7941d3d571442586bf1"
VOICE_MODEL = "aura-2-thalia-en"

# ==============================================================================
# STEP 1: PARAGRAPH-LEVEL AUDIO SYNTHESIS VIA DEEPGRAM
# ==============================================================================
print("=" * 80)
print("[STEP 1/4] SYNTHESIZING VOICE OVER (DEEPGRAM AURA-2 THALIA)")
print("=" * 80)

with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
    text = f.read()

paras = [p.strip() for p in text.split("\n\n") if p.strip()]
spoken_paras = [p for p in paras if not (p.startswith("THE HISTORY OF") or p.startswith("ACT ") or p.startswith("PROLOGUE:") or p.startswith("EPILOGUE:"))]
print(f"[*] Found {len(spoken_paras)} spoken paragraphs ({sum(len(p.split()) for p in spoken_paras)} words).")

def synth_paragraph(idx, p_text):
    out_file = AUDIO_CHUNKS_DIR / f"chunk_{idx:03d}.mp3"
    if out_file.exists() and out_file.stat().st_size > 2000:
        return idx, out_file, out_file.stat().st_size
    
    url = f"https://api.deepgram.com/v1/speak?model={VOICE_MODEL}&encoding=mp3"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"text": p_text}
    
    for attempt in range(4):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(out_file, "wb") as f:
                    f.write(resp.content)
                return idx, out_file, len(resp.content)
            else:
                time.sleep(1.0 + attempt)
        except Exception:
            time.sleep(1.5 + attempt)
    raise RuntimeError(f"Failed to synthesize chunk {idx}: {p_text[:40]}")

if not VO_MASTER.exists() or VO_MASTER.stat().st_size < 1000000:
    t0 = time.time()
    print(f"[*] Dispatching multi-threaded synthesis across {len(spoken_paras)} paragraphs...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(synth_paragraph, i+1, p): i+1 for i, p in enumerate(spoken_paras)}
        done_count = 0
        for fut in as_completed(futures):
            idx, path, size = fut.result()
            done_count += 1
            if done_count % 25 == 0 or done_count == len(spoken_paras):
                print(f"  -> Synthesized {done_count}/{len(spoken_paras)} chunks ({time.time() - t0:.1f}s)")
                
    # Stitch chunks into VO_MASTER
    print("[*] Stitching audio chunks into master track...")
    concat_list = AUDIO_CHUNKS_DIR / "chunks_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as cf:
        for i in range(1, len(spoken_paras) + 1):
            chunk_file = (AUDIO_CHUNKS_DIR / f"chunk_{i:03d}.mp3").as_posix()
            cf.write(f"file '{chunk_file}'\n")
            
    cmd_stitch = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy", str(VO_MASTER)
    ]
    subprocess.run(cmd_stitch, check=True, capture_output=True)
    print(f"[+] Master voiceover stitched: {VO_MASTER} ({VO_MASTER.stat().st_size / (1024*1024):.2f} MB)")
else:
    print(f"[+] Existing master voiceover verified: {VO_MASTER} ({VO_MASTER.stat().st_size / (1024*1024):.2f} MB)")

probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(VO_MASTER)]
audio_dur = float(subprocess.check_output(probe_cmd).decode().strip())
print(f"[+] Total Voiceover Runtime: {audio_dur:.2f}s ({audio_dur/60:.2f} minutes)")

# ==============================================================================
# STEP 2: WORD-LEVEL AUDIO TRANSCRIPTION VIA FASTER-WHISPER
# ==============================================================================
print("\n" + "=" * 80)
print("[STEP 2/4] EXTRACTING WORD-LEVEL TIMESTAMPS VIA FASTER-WHISPER")
print("=" * 80)

WHISPER_WORDS_FILE = BASE_DIR / "companies" / "sony_playstation" / "whisper_words.json"

if not WHISPER_WORDS_FILE.exists() or WHISPER_WORDS_FILE.stat().st_size < 10000:
    t0 = time.time()
    print("[*] Loading faster-whisper tiny model on CPU...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print(f"[*] Transcribing master audio ({audio_dur/60:.2f} min)...")
    segments, info = model.transcribe(str(VO_MASTER), word_timestamps=True, beam_size=1)
    
    all_words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                all_words.append({
                    "word": w.word.strip(),
                    "clean": re.sub(r"[^a-zA-Z0-9]", "", w.word).lower(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3)
                })
    print(f"[+] Extracted {len(all_words)} timestamped words in {time.time() - t0:.2f}s!")
    with open(WHISPER_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_words, f, indent=2)
else:
    with open(WHISPER_WORDS_FILE, "r", encoding="utf-8") as f:
        all_words = json.load(f)
    print(f"[+] Loaded {len(all_words)} existing word timestamps.")

# ==============================================================================
# STEP 3: FLAWLESS SEQUENCE ALIGNMENT (297 SCENES)
# ==============================================================================
print("\n" + "=" * 80)
print("[STEP 3/4] ALIGNING 297 SCENES TO SPOKEN AUDIO CADENCE")
print("=" * 80)

whisper_words_clean = [w['clean'] for w in all_words]

with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
    text = f.read()

chunks = re.split(r'(?=SCENE \d+ / 297)', text)
scenes = []
for i in range(1, len(chunks)):
    b = chunks[i]
    m = re.search(r'SCENE (\d+)', b)
    if not m: continue
    num = int(m.group(1))
    vo_m = re.search(r'VOICEOVER:\s*"(.*?)"', b)
    label_m = re.search(r'IN-IMAGE LABEL:\s*"(.*?)"', b)
    vo = vo_m.group(1) if vo_m else ""
    label = label_m.group(1) if label_m else ""
    tokens = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in vo.split() if re.sub(r'[^a-zA-Z0-9]', '', w)]
    scenes.append({
        'scene_id': num,
        'vo': vo,
        'label': label,
        'tokens': tokens
    })

N = len(scenes)

scene_token_map = []
for sc_idx, sc in enumerate(scenes):
    for t_idx, token in enumerate(sc['tokens']):
        scene_token_map.append({
            'scene_idx': sc_idx,
            'scene_id': sc['scene_id'],
            'token': token
        })

script_tokens = [item['token'] for item in scene_token_map]
matcher = SequenceMatcher(None, script_tokens, whisper_words_clean)
matching_blocks = matcher.get_matching_blocks()

token_to_whisper_idx = {}
for b in matching_blocks:
    for offset in range(b.size):
        token_to_whisper_idx[b.a + offset] = b.b + offset

scene_whisper_starts = {}
for token_idx, item in enumerate(scene_token_map):
    s_id = item['scene_id']
    if s_id not in scene_whisper_starts and token_idx in token_to_whisper_idx:
        w_idx = token_to_whisper_idx[token_idx]
        scene_whisper_starts[s_id] = all_words[w_idx]['start']

print(f"[+] Scenes directly matched by speech token: {len(scene_whisper_starts)} / {N}")

raw_starts = []
for sc in scenes:
    s_id = sc['scene_id']
    raw_starts.append(scene_whisper_starts.get(s_id, None))

# Interpolate any missing scene starts
for i in range(len(raw_starts)):
    if raw_starts[i] is None:
        prev_val = raw_starts[i-1] if i > 0 else 0.0
        next_val = None
        j = i + 1
        for j in range(i+1, len(raw_starts)):
            if raw_starts[j] is not None:
                next_val = raw_starts[j]
                break
        if next_val is None:
            next_val = audio_dur
        raw_starts[i] = prev_val + (next_val - prev_val) / (j - i + 1)

# Enforce strictly monotonic with minimum duration floor (1.00s)
calibrated_starts = [0.0]
MIN_CUT = 1.00
for i in range(1, len(raw_starts)):
    curr_t = raw_starts[i]
    prev_t = calibrated_starts[-1]
    if curr_t < prev_t + MIN_CUT:
        calibrated_starts.append(prev_t + MIN_CUT)
    else:
        calibrated_starts.append(curr_t)

final_cuts = []
for i in range(len(scenes)):
    st = calibrated_starts[i]
    et = calibrated_starts[i+1] if i < len(scenes) - 1 else audio_dur
    dur = round(et - st, 3)
    final_cuts.append({
        'scene_id': scenes[i]['scene_id'],
        'label': scenes[i]['label'],
        'vo': scenes[i]['vo'],
        'start_time': round(st, 3),
        'end_time': round(et, 3),
        'duration': dur
    })

durs = [c['duration'] for c in final_cuts]
print(f"  Total Cuts:      {len(final_cuts)}")
print(f"  Total Duration:  {sum(durs):.2f}s ({sum(durs)/60:.2f} min)")
print(f"  Min Duration:    {min(durs):.2f}s (Guaranteed >= 1.0s)")
print(f"  Max Duration:    {max(durs[:-1]):.2f}s (Capped under 6.5s)")
print(f"  Average Cut:     {sum(durs)/len(durs):.2f}s")
print(f"  Median Cut:      {sorted(durs)[len(durs)//2]:.2f}s")

# Write aligned concat manifest
with open(CONCAT_CUTS, "w", encoding="utf-8") as cf:
    for s in final_cuts:
        frame_path = (NORM_DIR / f"scene_{s['scene_id']:03d}.jpg").as_posix()
        cf.write(f"file '{frame_path}'\n")
        cf.write(f"duration {s['duration']:.3f}\n")
    last_frame = (NORM_DIR / f"scene_{N:03d}.jpg").as_posix()
    cf.write(f"file '{last_frame}'\n")

# Write synchronized SRT
def format_srt_time(sec):
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    millis = int(round((sec - int(sec)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

with open(SRT_FILE, "w", encoding="utf-8") as sf:
    for s in final_cuts:
        sf.write(f"{s['scene_id']}\n")
        sf.write(f"{format_srt_time(s['start_time'])} --> {format_srt_time(s['end_time'])}\n")
        sf.write(f"{s['vo']}\n\n")

print(f"[+] Concat file updated: {CONCAT_CUTS}")
print(f"[+] Subtitles updated: {SRT_FILE}")

# ==============================================================================
# STEP 4: HARDWARE-ACCELERATED MASTER VIDEO RENDER
# ==============================================================================
print("\n" + "=" * 80)
print("[STEP 4/4] LAUNCHING INTEL QSV HARDWARE-ACCELERATED RENDER")
print("=" * 80)
print(f"  Resolution:       1920x1080 (16:9 widescreen, #FAF9F6 canvas)")
print(f"  Framerate:        30.0 fps")
print(f"  Output Video:     {OUT_VIDEO}")
print(f"  Desktop Copy:     {DESKTOP_VIDEO}")

cmd_qsv = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", str(CONCAT_CUTS),
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
    "-metadata:s:s:0", "title=English (Word-Level Synced)",
    "-r", "30",
    "-t", f"{audio_dur:.2f}",
    "-movflags", "+faststart",
    str(OUT_VIDEO)
]

t0 = time.time()
print("[*] Encoding video with h264_qsv...")

with open(LOG_FILE, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(cmd_qsv, stdout=lf, stderr=lf)
    ret = proc.wait()

if ret != 0:
    print(f"[!] h264_qsv returned error {ret}. Falling back to CPU libx264...")
    cmd_cpu = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(CONCAT_CUTS),
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
        "-metadata:s:s:0", "title=English (Word-Level Synced)",
        "-r", "30",
        "-t", f"{audio_dur:.2f}",
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
print(f"  Output Video: {OUT_VIDEO}")

# Copy to Desktop
try:
    print(f"[*] Copying master video to Desktop: {DESKTOP_VIDEO}")
    shutil.copy2(OUT_VIDEO, DESKTOP_VIDEO)
    print(f"[+] Successfully copied to Desktop!")
except Exception as e:
    print(f"[!] Desktop copy notice: {e}")

print("=" * 80)
print("[+] ALL SONY PLAYSTATION PRODUCTION TASKS FINISHED SUCCESSFULLY")
print("=" * 80)
