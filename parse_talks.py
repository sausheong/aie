#!/usr/bin/env python3
"""Parse talks.md and emit sessions.json with interest scores."""

import re
import json

PRIMARY_KEYWORDS = [
    "agent runtime", "harness engineering", "harness", "mcp", "tool integration",
    "tool use", "context engineering", "context window", "compaction",
    "durable execution", "agent memory", "memory", "evaluation", "eval",
    "verification", "inference infrastructure", "inference engine", "vllm",
    "sglang", "trt-llm", "local llm", "local model", "computer-use",
    "computer use", "ai-native", "ai native", "autonomous agent", "agent loop",
    "agent architecture", "orchestration", "multi-agent", "multiagent",
    "tool calling", "function calling", "structured output", "tracing",
    "observability", "production agent", "scalable agent", "reliable agent",
    "kv cache", "continuous batching", "token", "throughput", "latency",
    "sandbox", "sandboxing", "code execution", "agentic workflow",
    "agent sdk", "agentic coding", "inference at scale", "gpu", "vram",
    "open-source inference", "tokenspeed", "agentic era", "agentic system",
    "workstation agent", "local inference", "quality gate", "eval anti-pattern",
    "lllm-as-judge", "llm judge", "trace", "span", "agent skill",
    "voice-coding", "hooks", "scheduled task", "ai-native engineer",
    "agent speedrun", "agent loop", "agent core", "bedrock",
    "context management", "retrieval", "reranking", "hybrid search",
    "synthetic data", "fine-tuning", "training pipeline",
]

ANTI_KEYWORDS = [
    "intro to", "introduction to", "getting started with", "basics of",
    "101", "beginner", "no-code", "low-code", "marketing",
    "sales", "go-to-market", "leadership", "executive",
    "vendor", "product launch", "announcing", "new product",
    "overview of", "what is ai", "what are llms",
    "prompt engineering basics", "basic rag", "simple rag",
    "ethical ai", "responsible ai",  # only as broad generic overviews
]

# Titles/descriptions that are clearly vendor pitches with no novel engineering
STRONG_ANTI = [
    "how to use arize", "get started with models in microsoft foundry",
    "from zero to deployed on azure",
]

BOOST_TITLES = [
    "harness", "mcp", "agent runtime", "inference engine", "inference at scale",
    "context engineering", "durable execution", "computer-use", "computer use",
    "local llm", "workstation agent", "quality gate", "agentic coding",
    "ai-native", "agent memory", "agent speedrun", "sandbox",
    "production ai", "production agent", "token", "kv cache", "vllm",
    "sglang", "trt-llm", "tokenspeed",
]


def score_session(title, description):
    combined = (title + " " + description).lower()
    title_lower = title.lower()

    # Strong anti: vendor pitches
    for phrase in STRONG_ANTI:
        if phrase in title_lower or phrase in combined[:200]:
            return 0, "skip"

    primary_hits = sum(1 for kw in PRIMARY_KEYWORDS if kw in combined)
    anti_hits = sum(1 for kw in ANTI_KEYWORDS if kw in combined)
    title_boost = sum(2 for kw in BOOST_TITLES if kw in title_lower)

    score = primary_hits * 2 + title_boost - anti_hits * 3

    # Bonus for description length (more detail = more technical)
    if len(description) > 400:
        score += 1

    if score >= 15:
        return score, "primary"
    elif score >= 9:
        return score, "backup"
    else:
        return score, "other"


def parse_talks(path):
    with open(path) as f:
        content = f.read()

    days = {}
    current_day = None

    # Split by day headers
    day_pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    session_pattern = re.compile(r'^### (.+)$', re.MULTILINE)

    day_splits = list(day_pattern.finditer(content))

    for i, day_match in enumerate(day_splits):
        day_name = day_match.group(1).strip()
        day_start = day_match.end()
        day_end = day_splits[i + 1].start() if i + 1 < len(day_splits) else len(content)
        day_text = content[day_start:day_end]

        sessions = []
        session_splits = list(session_pattern.finditer(day_text))

        for j, sess_match in enumerate(session_splits):
            title = sess_match.group(1).strip()
            sess_start = sess_match.end()
            sess_end = session_splits[j + 1].start() if j + 1 < len(session_splits) else len(day_text)
            sess_text = day_text[sess_start:sess_end].strip()

            # Extract fields
            time_m = re.search(r'\*\*Time:\*\* (.+)', sess_text)
            room_m = re.search(r'\*\*Room:\*\* (.+)', sess_text)
            type_m = re.search(r'\*\*Type:\*\* (.+)', sess_text)
            track_m = re.search(r'\*\*Track:\*\* (.+)', sess_text)
            speakers_m = re.search(r'\*\*Speakers:\*\* (.+)', sess_text)

            # Description: everything after the last metadata bullet (lines starting with "- **")
            last_bullet = list(re.finditer(r'^- \*\*.+$', sess_text, re.MULTILINE))
            if last_bullet:
                after_bullets = sess_text[last_bullet[-1].end():]
                description = after_bullets.lstrip('\n').strip()
            else:
                description = ""

            time = time_m.group(1).strip() if time_m else ""
            room = room_m.group(1).strip() if room_m else ""
            session_type = type_m.group(1).strip() if type_m else ""
            track = track_m.group(1).strip() if track_m else ""
            speakers = speakers_m.group(1).strip() if speakers_m else ""

            raw_score, interest = score_session(title, description)

            sessions.append({
                "title": title,
                "time": time,
                "room": room,
                "type": session_type,
                "track": track,
                "speakers": speakers,
                "description": description,
                "score": raw_score,
                "interest": interest,
            })

        days[day_name] = sessions

    return days


def main():
    days = parse_talks("talks.md")
    total = sum(len(s) for s in days.values())
    primaries = sum(1 for day in days.values() for s in day if s["interest"] == "primary")
    backups = sum(1 for day in days.values() for s in day if s["interest"] == "backup")
    print(f"Parsed {total} sessions: {primaries} primary, {backups} backup")
    with open("sessions.json", "w") as f:
        json.dump(days, f, indent=2)
    print("Written sessions.json")


if __name__ == "__main__":
    main()
