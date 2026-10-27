"""
Beat Decomposer Module
Decomposes 20-30 minute master scripts into phrase-level micro-beats
targeting strictly 2.0s to 3.2s per cut (~5 to 8 words per cut) with 100% verbatim verification.
"""

import os
import re
import argparse

class BeatDecomposer:
    def __init__(self, topic: str):
        self.topic = topic
        self.slug = topic.lower().replace(" ", "_").replace("&", "and").replace("'", "")
        self.output_dir = os.path.join("companies", self.slug)
        self.script_path = os.path.join(self.output_dir, "script.txt")
        self.beats_path = os.path.join(self.output_dir, "visual_beats.txt")

    def verify_purity(self) -> bool:
        """
        Performs character-by-character string comparison between spoken script
        and joined visual beat voiceover clauses to guarantee zero dropped words.
        """
        if not os.path.exists(self.script_path) or not os.path.exists(self.beats_path):
            raise FileNotFoundError("Both script.txt and visual_beats.txt must exist.")

        with open(self.script_path, "r", encoding="utf-8") as f:
            script_paras = [
                line.strip() for line in f 
                if line.strip() 
                and not line.startswith("ACT ") 
                and not line.startswith("PROLOGUE:") 
                and not line.startswith("EPILOGUE:")
                and not line.startswith("THE HISTORY OF")
                and not line.startswith("===")
            ]

        with open(self.beats_path, "r", encoding="utf-8") as f:
            beats_text = f.read()

        # Parse blocks safely
        blocks = beats_text.split("-" * 80)
        beat_vos = []
        for b in blocks:
            lines = [l.strip() for l in b.strip().split("\n") if l.strip()]
            for i, l in enumerate(lines):
                if l == "VOICEOVER:" and i + 1 < len(lines):
                    vo_line = lines[i+1]
                    if vo_line.startswith('"') and vo_line.endswith('"'):
                        vo_line = vo_line[1:-1]
                    beat_vos.append(vo_line)
                    break
        
        full_script = " ".join(script_paras)
        full_beats = " ".join(b.strip() for b in beat_vos)

        is_equal = (full_script == full_beats)
        print("=== VERBATIM PURITY AUDIT ===")
        print(f"Script Characters: {len(full_script):,}")
        print(f"Beats Characters:  {len(full_beats):,}")
        print(f"100% Equal:        {is_equal}")
        
        if not is_equal:
            import difflib
            diff = list(difflib.unified_diff(full_script.split(), full_beats.split(), n=2))
            print(f"Discrepancies found ({len(diff)} diff lines):")
            print("\n".join(diff[:20]))
            
        return is_equal

    def calculate_stats(self) -> dict:
        """
        Calculates pacing statistics: total beats, average duration, word count per beat.
        """
        with open(self.beats_path, "r", encoding="utf-8") as f:
            text = f.read()

        timings = [float(m) for m in re.findall(r'Est\. Timing: ~([\d\.]+)s', text)]
        words_list = [int(m) for m in re.findall(r'Words: (\d+) words', text)]
        
        stats = {
            "total_beats": len(timings),
            "total_words": sum(words_list),
            "avg_words_per_beat": round(sum(words_list) / len(words_list), 2) if words_list else 0,
            "avg_cut_duration_sec": round(sum(timings) / len(timings), 2) if timings else 0,
            "max_duration_sec": max(timings) if timings else 0,
            "beats_over_3_5s": len([t for t in timings if t > 3.5])
        }
        
        print("\n=== BEAT DENSITY & RETENTION STATS ===")
        print(f"Total Visual Cuts:      {stats['total_beats']}")
        print(f"Average Words / Cut:    {stats['avg_words_per_beat']} words")
        print(f"Average Cut Duration:   ~{stats['avg_cut_duration_sec']} seconds")
        print(f"Max Hold Duration:      {stats['max_duration_sec']}s")
        print(f"Long Beats (>3.5s):     {stats['beats_over_3_5s']} ({stats['beats_over_3_5s']/stats['total_beats']*100:.1f}%)")
        return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decompose and verify visual beats.")
    parser.add_argument("--topic", required=True, help="Topic or Company name (e.g., 'Rockstar Games')")
    parser.add_argument("--verify", action="store_true", help="Verify verbatim purity")
    args = parser.parse_args()
    
    decomposer = BeatDecomposer(args.topic)
    decomposer.verify_purity()
    decomposer.calculate_stats()
