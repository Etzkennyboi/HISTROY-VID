"""
Prompt Builder Module
Compiles visual beats into ready-to-copy master prompts (for Midjourney/Flux)
and generates the automated render manifest.json.
"""

import os
import json
import re
import argparse

class PromptBuilder:
    def __init__(self, topic: str):
        self.topic = topic
        self.slug = topic.lower().replace(" ", "_").replace("&", "and").replace("'", "")
        self.output_dir = os.path.join("companies", self.slug)
        self.beats_path = os.path.join(self.output_dir, "visual_beats.txt")
        self.master_prompts_path = os.path.join(self.output_dir, "master_prompts.txt")
        self.manifest_path = os.path.join(self.output_dir, "manifest.json")

    def infer_scale(self, concept: str, label: str) -> str:
        c = (concept + " " + label).lower()
        if any(k in c for k in ['document', 'letter', 'form', 'contract', 'headline', 'paper', 'check', 'ledger', 'memo', 'exhibit']):
            return "DOCUMENT"
        elif any(k in c for k in ['diagram', 'chart', 'map', 'pie chart', 'network', 'blueprint', 'topographical', 'scale', 'timeline']):
            return "DIAGRAM"
        elif any(k in c for k in ['portrait', 'silhouette of', 'sam houser', 'dan houser', 'leslie benzies', 'jobs', 'wozniak', 'steve jobs', 'scully']):
            return "PORTRAIT"
        elif any(k in c for k in ['smashing', 'slamming', 'exploding', 't-bone', 'ramming', 'running', 'shooting', 'chase', 'racing', 'fireball']):
            return "ACTION"
        elif any(k in c for k in ['skyline', 'street', 'city', 'building', 'store', 'office', 'studio', 'headquarters', 'harbor', 'desert', 'room', 'entrance']):
            return "ENVIRONMENT"
        else:
            return "METAPHOR"

    def build_all(self):
        with open(self.beats_path, "r", encoding="utf-8") as f:
            text = f.read()

        pattern = r'BEAT (\d+) \| (.*?)\nEst\. Timing: ~([\d\.]+)s.*?Words: (\d+) words.*?\nIN-IMAGE LABEL: \[(.*?)\]\nVOICEOVER:\n  "(.*?)"\nVISUAL CONCEPT:\n  (.*?)\n-{80}'
        matches = re.findall(pattern, text, re.DOTALL)

        total_scenes = len(matches)
        print(f"[*] Compiling prompts for {total_scenes} scenes in {self.topic}...")

        scenes_data = []
        master_lines = [
            "=" * 80,
            f"THE ENTIRE HISTORY OF {self.topic.upper()} — MASTER PROMPT PACKAGE",
            "STYLE: STYLE 4 (INK VIGNETTE / MINIMALIST 2D CARTOON WEBCOMIC)",
            f"TOTAL SCENES: {total_scenes} | RETENTION PACING: HYPER-GRANULAR (~2.5s PER CUT)",
            "STRICT 100% CHRONOLOGICAL & SCRIPT PURITY — ZERO INVENTED WORDS",
            "=" * 80,
            ""
        ]

        cum_time = 0.0

        for m in matches:
            b_num = int(m[0])
            act = m[1].strip()
            est_dur = float(m[2])
            words = int(m[3])
            label = m[4].strip()
            vo = m[5].strip()
            concept_raw = m[6].strip()
            
            clean_concept = concept_raw.replace("Style 4: ", "").strip()
            scale = self.infer_scale(clean_concept, label)
            
            start_time = round(cum_time, 2)
            cum_time += est_dur
            end_time = round(cum_time, 2)
            
            filename = f"scene_{b_num:03d}.png"
            
            prompt = (
                f"Scene {b_num:03d} of The History of {self.topic}: "
                f"16:9 widescreen minimalist 2D cartoon webcomic illustration on off-white (#FAF9F6) background "
                f"with a soft, hand-drawn charcoal and watercolor brush vignette border around the edges. "
                f"Visual Concept: {clean_concept} "
                f"Characters: Minimalist 2D cartoon stick figures with solid white filled circular heads, "
                f"simple expressive curved black ink eyes and mouths, dark thin single-line stick limbs, "
                f"wearing authentic era-appropriate clothing. "
                f"Environment: Detailed, atmospheric 2D background in muted cinematic tones with clean comic line art, "
                f"subtle cross-hatching, high-contrast focal lighting, and zero glossy 3D rendering. "
                f'In-Image Label: Distinct hand-lettered comic text in bold quotes in upper frame reading "{label}". '
                f"Composition: Cinematic 16:9 landscape framing, high visual clarity, perfectly balanced for smooth Ken Burns camera pan and zoom."
            )
            
            scenes_data.append({
                "scene_num": b_num,
                "total_scenes": total_scenes,
                "filename": filename,
                "act": act,
                "scale": scale,
                "label": label,
                "vo": vo,
                "words": words,
                "duration": est_dur,
                "start_time": start_time,
                "end_time": end_time,
                "prompt": prompt,
                "concept": clean_concept
            })
            
            master_lines.append("=" * 80)
            master_lines.append(f"SCENE {b_num:03d} / {total_scenes} | DOWNLOAD AS: {filename}")
            master_lines.append(f"CUT WINDOW: {start_time:7.2f}s -> {end_time:7.2f}s (Duration: {est_dur:4.2f}s) | ACT: {act} | SCALE: {scale}")
            master_lines.append(f'IN-IMAGE LABEL: "{label}"')
            master_lines.append(f'VOICEOVER: "{vo}"')
            master_lines.append("=" * 80)
            master_lines.append("COPY & PASTE PROMPT (Midjourney / Ideogram / Flux):")
            master_lines.append(prompt)
            master_lines.append("")

        with open(self.master_prompts_path, "w", encoding="utf-8") as f:
            f.write("\n".join(master_lines))

        manifest_data = {
            "project": f"The History of {self.topic}",
            "version": "2.0",
            "total_scenes": total_scenes,
            "total_duration_seconds": round(cum_time, 2),
            "total_duration_minutes": round(cum_time / 60.0, 2),
            "total_words": sum(s['words'] for s in scenes_data),
            "average_cut_duration": round(cum_time / total_scenes, 2),
            "scenes": scenes_data
        }

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        print(f"[+] Master Prompts written: {self.master_prompts_path}")
        print(f"[+] Manifest JSON written:   {self.manifest_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build master prompts and manifest.")
    parser.add_argument("--topic", required=True, help="Topic or Company name")
    args = parser.parse_args()
    
    builder = PromptBuilder(args.topic)
    builder.build_all()
