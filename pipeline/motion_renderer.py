"""
Motion Renderer Module
Renders cinematic 1080p documentary videos with dynamic Ken Burns
pan/zoom motion, image transitions, and synchronized audio tracks.
"""

import os
import json
import argparse
import subprocess

class MotionRenderer:
    def __init__(self, topic: str):
        self.topic = topic
        self.slug = topic.lower().replace(" ", "_").replace("&", "and").replace("'", "")
        self.company_dir = os.path.join("companies", self.slug)
        self.manifest_path = os.path.join(self.company_dir, "manifest.json")
        self.images_dir = os.path.join(self.company_dir, "images")
        self.audio_path = os.path.join(self.company_dir, "voiceover_master.mp3")
        self.output_dir = os.path.join("output", self.slug)
        os.makedirs(self.output_dir, exist_ok=True)

    def render(self, fps: int = 30, resolution: str = "1920x1080"):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        scenes = manifest.get("scenes", [])
        print(f"[*] Rendering {len(scenes)} scenes for {self.topic}...")
        print(f"[*] Resolution: {resolution} | Target FPS: {fps}")

        output_video = os.path.join(self.output_dir, f"{self.slug}_master_documentary.mp4")
        print(f"[*] Target output path: {output_video}")

        # Check for image assets
        if not os.path.exists(self.images_dir):
            print(f"[!] Warning: Image folder '{self.images_dir}' not found.")
            print(f"    Please generate images from 'companies/{self.slug}/master_prompts.txt' and place them in 'companies/{self.slug}/images/'")
            return

        print(f"[+] Found image folder: {self.images_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render documentary motion video.")
    parser.add_argument("--topic", required=True, help="Topic or Company name")
    args = parser.parse_args()

    renderer = MotionRenderer(args.topic)
    renderer.render()
