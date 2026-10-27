"""
History Researcher Module
Intakes a company or historical subject and compiles an investigative research brief.
"""

import os
import json
import argparse

class HistoryResearcher:
    def __init__(self, topic: str):
        self.topic = topic
        self.slug = topic.lower().replace(" ", "_").replace("&", "and").replace("'", "")
        self.output_dir = os.path.join("companies", self.slug)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_research_framework(self) -> dict:
        """
        Builds the 7-pillar investigative framework for a high-retention documentary.
        """
        framework = {
            "topic": self.topic,
            "slug": self.slug,
            "pillars": {
                "prologue_hook": {
                    "focus": "The opening shock metric or financial paradox",
                    "prompts": [
                        f"What is the single most staggering financial or cultural number {self.topic} achieved?",
                        "What unlikely accident or failure initially birthed this empire?"
                    ]
                },
                "act_1_origins": {
                    "focus": "The Genesis & The Outlaws (Founders, early prototypes, first breakthrough)",
                    "prompts": [
                        f"Who were the original founding architects of {self.topic}?",
                        "What was the gritty, unpolished reality before corporate fame?"
                    ]
                },
                "act_2_expansion": {
                    "focus": "The Technical Leap & Cultural Dominance",
                    "prompts": [
                        "What technological breakthrough made the impossible possible?",
                        "How did they out-innovate or conquer the market leaders?"
                    ]
                },
                "act_3_crisis": {
                    "focus": "The Scandal, The Culture War & The Resistance",
                    "prompts": [
                        "What scandal, legal battle, or government pushback almost destroyed them?",
                        "Who were the chief antagonists (politicians, rival CEOs, regulators)?"
                    ]
                },
                "act_4_gamble": {
                    "focus": "The All-In Gamble & The Internal Toll",
                    "prompts": [
                        "What massive project risked everything the company owned?",
                        "What was the human cost behind closed doors (crunch, burnout, obsession)?"
                    ]
                },
                "act_5_empire": {
                    "focus": "The Modern Monolith, Betrayals & Hackers",
                    "prompts": [
                        "How did commercial success fracture the founding brotherhood?",
                        "What modern threats (lawsuits, leaks, departures) shook the foundation?"
                    ]
                },
                "epilogue_truth": {
                    "focus": "The Cultural Mirror & Ultimate Parable",
                    "prompts": [
                        f"What does {self.topic} reveal about human nature and the digital age?",
                        "What is the lasting takeaway that makes viewers remember this story?"
                    ]
                }
            }
        }
        
        brief_path = os.path.join(self.output_dir, "research_brief.json")
        with open(brief_path, "w", encoding="utf-8") as f:
            json.dump(framework, f, indent=2)
            
        print(f"[*] Research framework established: {brief_path}")
        return framework

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate research framework for a company/topic.")
    parser.add_argument("--topic", required=True, help="Topic or Company name (e.g., 'Rockstar Games')")
    args = parser.parse_args()
    
    researcher = HistoryResearcher(args.topic)
    researcher.generate_research_framework()
