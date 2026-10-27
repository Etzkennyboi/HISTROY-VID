"""
Master CLI: Entire History Documentary Pipeline
End-to-End Orchestrator for 20-30 Minute High-Retention History Videos.
"""

import sys
import os
import argparse

# Ensure utf-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pipeline.history_researcher import HistoryResearcher
from pipeline.documentary_scripter import DocumentaryScripter
from pipeline.beat_decomposer import BeatDecomposer
from pipeline.prompt_builder import PromptBuilder
from pipeline.whisper_aligner import WhisperAligner
from pipeline.motion_renderer import MotionRenderer

def main():
    parser = argparse.ArgumentParser(description="Entire History Documentary Creation Engine")
    parser.add_argument("--topic", required=True, help="Topic name (e.g. 'Rockstar Games', 'Apple', 'Nintendo')")
    parser.add_argument("--step", choices=["research", "script", "beats", "prompts", "align", "render", "all"], default="all", help="Pipeline step to execute")
    args = parser.parse_args()

    topic = args.topic
    print("=" * 80)
    print(f"[*] ENTIRE HISTORY DOCUMENTARY ENGINE: {topic.upper()}")
    print("=" * 80)

    slug = topic.lower().replace(" ", "_").replace("&", "and").replace("'", "")
    company_dir = os.path.join("companies", slug)
    os.makedirs(company_dir, exist_ok=True)

    # Step 1: Research
    if args.step in ["research", "all"]:
        print("\n[Step 1/6] Running Investigative Research Framework...")
        researcher = HistoryResearcher(topic)
        researcher.generate_research_framework()

    # Step 2: Script Audit & Formatting
    if args.step in ["script", "all"]:
        print("\n[Step 2/6] Auditing Multi-Act Documentary Script...")
        scripter = DocumentaryScripter(topic)
        if os.path.exists(scripter.script_path):
            scripter.audit_script()
        else:
            print(f"[!] Place your narrative script at: {scripter.script_path}")

    # Step 3: Beat Decomposition
    if args.step in ["beats", "all"]:
        print("\n[Step 3/6] Running Phrase-Level Micro-Beat Decomposition...")
        decomposer = BeatDecomposer(topic)
        if os.path.exists(decomposer.beats_path):
            decomposer.verify_purity()
            decomposer.calculate_stats()
        else:
            print(f"[!] visual_beats.txt not yet generated. Please construct beats from script.")

    # Step 4: Prompt Building
    if args.step in ["prompts", "all"]:
        print("\n[Step 4/6] Compiling Master Prompts & Render Manifest...")
        builder = PromptBuilder(topic)
        if os.path.exists(builder.beats_path):
            builder.build_all()
        else:
            print(f"[!] Missing {builder.beats_path}")

    # Step 5: Audio Alignment
    if args.step in ["align", "all"]:
        print("\n[Step 5/6] Aligning Voiceover to Manifest...")
        aligner = WhisperAligner(topic)
        if os.path.exists(aligner.manifest_path):
            aligner.align_audio()

    # Step 6: Motion Rendering
    if args.step in ["render", "all"]:
        print("\n[Step 6/6] Launching Ken Burns Motion Renderer...")
        renderer = MotionRenderer(topic)
        if os.path.exists(renderer.manifest_path):
            renderer.render()

    print("\n" + "=" * 80)
    print("[+] PIPELINE EXECUTION FINISHED")
    print("=" * 80)

if __name__ == "__main__":
    main()
