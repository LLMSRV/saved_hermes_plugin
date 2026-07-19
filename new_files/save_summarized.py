"""
/save_summarized helper
=======================

Shared logic for the ``/saved slash command: summarise the current
conversation via the auxiliary LLM and write the result to a user-
specified file.

Used by both the CLI (cli.py) and the gateway (gateway/run.py).
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

def parse_saved_args(raw_args: str) -> Dict[str, Any]:
    """Parse ``/saved <file> [--overwrite|--append] arguments."""
    if not raw_args.strip():
        return {"error": "Usage: /saved <file_name> [--overwrite|--append]"}

    try:
        parser = argparse.ArgumentParser(prog="/saved")
        parser.add_argument("file", help="Output file path")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--overwrite", action="store_true",
                           help="Replace existing file contents")
        group.add_argument("--append", action="store_true",
                           help="Append to existing file (default)")
        args = parser.parse_args(raw_args.strip().split())
        mode = "overwrite" if args.overwrite else "append"
        return {"file": args.file, "mode": mode, "error": None}
    except SystemExit:
        return {"error": "Usage: /saved <file_name> [--overwrite|--append]"}

def _extract_user_assistant(messages: List[Dict[str, Any]]) -> List[str]:
    """Extract user/assistant turns as readable text, skipping tool calls."""
    lines = []
    for msg in messages:
        role = msg.get("role", "")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = [p.get("text", "") for p in content if p.get("type") == "text"]
            content = " ".join(parts)
        if content:
            lines.append(f"{role}: {content}")
    return lines

def build_summary_prompt(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the LLM prompt for summarising a conversation."""
    turns = _extract_user_assistant(messages)
    transcript = "\n".join(turns)

    system_prompt = (
        "You are a concise summariser. Your job is to produce a clear, "
        "structured summary of a conversation between a user and an AI "
        "assistant. Include the key topics discussed, decisions made, "
        "code snippets or commands that were important, and any action "
        "items or follow-ups. Omit filler and repetitive exchanges. "
        "Use markdown formatting. Do NOT include preamble — start "
        "directly with the summary."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript},
    ]

def summarize_conversation(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Call the auxiliary LLM to summarise the conversation."""
    try:
        from agent.auxiliary_client import call_llm
        prompt = build_summary_prompt(messages)
        resp = call_llm(
            task="compression",
            messages=prompt,
            max_tokens=4096,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return None

def write_summary(file_path: str, summary: str, mode: str) -> Optional[str]:
    """Write the summary to ``file_path.

    ``mode is "overwrite" (replace) or "append" (add with header).
    Returns an error string on failure, or ``None on success.
    """
    try:
        path = Path(file_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        if mode == "overwrite":
            path.write_text(summary + "\n", encoding="utf-8")
        else:
            header = (
                f"\n{'='*60}\n"
                f"Appended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'='*60}\n"
            )
            if path.exists() and path.stat().st_size > 0:
                existing = path.read_text(encoding="utf-8")
                content = existing + header + summary + "\n"
            else:
                content = summary + "\n"
            path.write_text(content, encoding="utf-8")

        return None
    except Exception as e:
        return str(e)
