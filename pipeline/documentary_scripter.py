"""
Documentary Scripter Module
Formats, validates, and prepares multi-act documentary scripts.
"""

import os
import argparse

class DocumentaryScripter:
    def __init__(self, topic: str):
        self.topic = topic
        self.slug = topic.lower().replace(" ", "_").replace("&", "and").replace("'", "")
        self.output_dir = os.path.join("companies", self.slug)
        self.script_path = os.path.join(self.output_dir, "script.txt")

    def audit_script(self) -> dict:
        """
        Audits an existing script for paragraph counts, word counts, and act structure.
        """
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"Script not found at: {self.script_path}")
            
        with open(self.script_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            
        acts = [l for l in lines if l.startswith("ACT ") or l.startswith("PROLOGUE:") or l.startswith("EPILOGUE:")]
        spoken_paras = [l for l in lines if not (l.startswith("ACT ") or l.startswith("PROLOGUE:") or l.startswith("EPILOGUE:"))]
        total_words = sum(len(p.split()) for p in spoken_paras)
        
        stats = {
            "topic": self.topic,
            "total_lines": len(lines),
            "acts_count": len(acts),
            "spoken_paragraphs": len(spoken_paras),
            "total_words": total_words,
            "est_runtime_minutes": round(total_words / 145.0, 2), # ~145 wpm narration speed
            "acts": acts
        }
        
        print("=== SCRIPT AUDIT SUMMARY ===")
        print(f"Topic:                {stats['topic']}")
        print(f"Acts / Sections:      {stats['acts_count']}")
        print(f"Spoken Paragraphs:    {stats['spoken_paragraphs']}")
        print(f"Total Spoken Words:   {stats['total_words']:,} words")
        print(f"Estimated Runtime:    ~{stats['est_runtime_minutes']} minutes")
        return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit or format documentary script.")
    parser.add_argument("--topic", required=True, help="Topic or Company name (e.g., 'Rockstar Games')")
    args = parser.parse_args()
    
    scripter = DocumentaryScripter(args.topic)
    scripter.audit_script()
