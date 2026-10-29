import os
import re
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import numpy as np
from scipy.optimize import linear_sum_assignment

print("=" * 80)
print("[*] SONY PLAYSTATION: INGESTING & NORMALIZING 297 SCENES")
print("=" * 80)

prompts_file = r"companies/sony_playstation/master_prompts.txt"
with open(prompts_file, "r", encoding="utf-8") as f:
    text = f.read()

chunks = re.split(r'(?=SCENE \d+ / 297)', text)

scenes = {}
for i in range(1, len(chunks)):
    b = chunks[i]
    m = re.search(r'SCENE (\d+)', b)
    if not m: continue
    num = int(m.group(1))
    
    vo_m = re.search(r'VOICEOVER:\s*"(.*?)"', b)
    vo = vo_m.group(1) if vo_m else ""
    
    label_m = re.search(r'IN-IMAGE LABEL:\s*"(.*?)"', b)
    label = label_m.group(1) if label_m else ""
    
    vc_m = re.search(r'Visual Concept:\s*(.*?)(?=\.\s*Characters:|\.\s*Environment:|\.\s*In-Image|\Z)', b, re.DOTALL)
    vc = vc_m.group(1).replace('\n', ' ').strip() if vc_m else ""
    
    corpus = f"{b.lower()} {vc.lower()} {vo.lower()} {label.lower()}"
    tokens = set(re.findall(r'\b\w+\b', corpus))
    vc_tokens = set(re.findall(r'\b\w+\b', vc.lower()))
    label_tokens = set(re.findall(r'\b\w+\b', label.lower()))
    
    scenes[num] = {
        'num': num,
        'vo': vo,
        'label': label,
        'vc': vc,
        'corpus': corpus,
        'tokens': tokens,
        'vc_tokens': vc_tokens,
        'label_tokens': label_tokens
    }

img_dir = r"C:\Users\Emmanuel\Downloads\Oct 29 - 07_42"
files = [f for f in sorted(os.listdir(img_dir)) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
print(f"[+] Loaded {len(scenes)} scenes and {len(files)} download images.")

def clean_filename(fname):
    base = re.sub(r'_[0-9a-fA-F]{8}\.(jpg|png|jpeg|webp)$', '', fname)
    base = base.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    base = re.sub(r'\s+', ' ', base).strip().lower()
    return base

def compute_affinity(clean, s_num):
    sc = scenes[s_num]
    words = [w for w in re.findall(r'\b\w+\b', clean) if len(w) > 2]
    words_set = set(words)
    if not words_set: return 0.0
    
    score = 0.0
    if clean in sc['vc'].lower(): score += 250.0
    vc_overlap = words_set.intersection(sc['vc_tokens'])
    score += len(vc_overlap) * 40.0
    label_overlap = words_set.intersection(sc['label_tokens'])
    score += len(label_overlap) * 30.0
    
    for i in range(len(words)-1):
        bigram = f"{words[i]} {words[i+1]}"
        if bigram in sc['vc'].lower(): score += 50.0
        elif bigram in sc['corpus']: score += 25.0
        
    corpus_overlap = words_set.intersection(sc['tokens'])
    score += len(corpus_overlap) * 10.0
    return max(0.0, score)

num_files = len(files)
num_scenes = len(scenes)

affinity = np.zeros((num_files, num_scenes), dtype=np.float32)
for f_idx, fname in enumerate(files):
    clean = clean_filename(fname)
    for s_idx in range(num_scenes):
        affinity[f_idx, s_idx] = compute_affinity(clean, s_idx + 1)

cost = affinity.max() - affinity
row_ind, col_ind = linear_sum_assignment(cost)

matched_scenes = {}
for f_idx, s_idx in zip(row_ind, col_ind):
    s_num = int(s_idx + 1)
    fname = files[f_idx]
    full_path = os.path.join(img_dir, fname)
    aff = float(affinity[f_idx, s_idx])
    matched_scenes[s_num] = {
        'scene_id': s_num,
        'source_path': full_path,
        'filename': fname,
        'affinity': aff,
        'label': scenes[s_num]['label'],
        'vo': scenes[s_num]['vo']
    }

# Save match manifest
OUT_DIR = Path(r"output/sony_playstation")
OUT_DIR.mkdir(parents=True, exist_ok=True)
manifest_path = OUT_DIR / "matched_297_scenes.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump([matched_scenes[i] for i in range(1, 298)], f, indent=2)

print(f"[+] 297/297 scenes matched and saved to {manifest_path}")

# Normalize to 1080p
OUT_FRAMES = OUT_DIR / "norm_frames_297"
OUT_FRAMES.mkdir(parents=True, exist_ok=True)

TARGET_W, TARGET_H = 1920, 1080
CANVAS_COLOR = (250, 249, 246)

def normalize_frame(s_num):
    info = matched_scenes[s_num]
    dst_path = OUT_FRAMES / f"scene_{s_num:03d}.jpg"
    if dst_path.exists() and dst_path.stat().st_size > 50000:
        return True
    try:
        with Image.open(info['source_path']) as im:
            im = im.convert("RGB")
            scale = min(TARGET_W / im.width, TARGET_H / im.height)
            nw = int(round(im.width * scale))
            nh = int(round(im.height * scale))
            resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (TARGET_W, TARGET_H), CANVAS_COLOR)
            canvas.paste(resized, ((TARGET_W - nw) // 2, (TARGET_H - nh) // 2))
            canvas.save(dst_path, "JPEG", quality=95)
            return True
    except Exception as e:
        print(f"Error scene {s_num}: {e}")
        return False

t0 = time.time()
print(f"[*] Normalizing 297 images to 1080p #FAF9F6...")
with ThreadPoolExecutor(max_workers=12) as executor:
    results = list(executor.map(normalize_frame, range(1, 298)))

elapsed = time.time() - t0
print(f"[+] All 297 frames normalized in {elapsed:.2f}s into {OUT_FRAMES}!")
