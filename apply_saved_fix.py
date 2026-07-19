#!/usr/bin/env python3
"""Apply all /saved fixes directly to your hermes-agent checkout."""
from pathlib import Path

HERMES = Path("/home/olly/.hermes/hermes-agent")

# ── 1. Recreate save_summarized.py (user accidentally reversed it) ───────────
save_summarized = '''"""Shared helper for /saved slash command.

Parses arguments, summarises a list of messages via the auxiliary LLM,
and writes the result to a file (overwrite or append mode).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.auxiliary_client import call_llm

logger = logging.getLogger(__name__)


def parse_saved_args(raw: str) -> Dict[str, Any]:
    """Parse /saved arguments: filename and mode flags.

    Returns {"file": str, "mode": str} or {"error": str}.
    """
    if not raw:
        return {"error": "Usage: /saved <filename> [--overwrite|--append]"}

    mode = "append"  # default
    args = raw

    if "--overwrite" in args:
        mode = "overwrite"
        args = args.replace("--overwrite", "").strip()

    if "--append" in args:
        mode = "append"
        args = args.replace("--append", "").strip()

    file_path = args.strip()
    if not file_path:
        return {"error": "Please specify a filename: /saved filename.md"}

    return {"file": file_path, "mode": mode}


def summarize_conversation(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Send conversation messages to the auxiliary LLM for summarisation."""
    if not messages:
        logger.warning("summarize_conversation called with empty messages")
        return None

    system_prompt = (
        "You are a concise summariser. Produce a clear, structured summary "
        "of a conversation. Include key topics, decisions, code snippets or "
        "commands that were important, and any action items or follow-ups. "
        "Omit filler and repetitive exchanges. Use markdown formatting. "
        "Do NOT include preamble — start directly with the summary."
    )

    try:
        resp = call_llm(
            task="compression",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(messages)},
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Summarisation failed: %s", e)
        return None


def write_summary(file_path: str, summary: str, mode: str = "append") -> Optional[str]:
    """Write summary to file, overwriting or appending."""
    try:
        path = Path(file_path).expanduser()

        if mode == "overwrite":
            path.write_text(summary)
        else:
            # Append mode: add a separator header before the summary
            if path.exists():
                with path.open("a") as f:
                    f.write("\\n\\n--- Summarised ---\\n\\n")
                    f.write(summary)
            else:
                path.write_text(summary)

        return None
    except Exception as e:
        return str(e)
'''

(filepath := HERMES / "hermes_cli" / "save_summarized.py").write_text(save_summarized)
print("✓ save_summarized.py written")

# ── 2. Check commands.py (should already be patched) ─────────────────────────
filepath = HERMES / "hermes_cli" / "commands.py"
content = filepath.read_text()
if 'CommandDef("saved"' not in content:
    marker = 'CommandDef("save", "Save the current conversation", "Session",\n               cli_only=True),'
    saved_def = '''    CommandDef("saved", "Summarise and save the current conversation to a file", "Session",
               args_hint="<filename> [--overwrite|--append]"),'''
    content = content.replace(marker, marker + "\n" + saved_def)
    filepath.write_text(content)
    print("✓ commands.py — registered 'saved'")
else:
    print("✓ commands.py — already registered")

# ── 3. Check slash_commands.py (should already be patched) ───────────────────
filepath = HERMES / "gateway" / "slash_commands.py"
content = filepath.read_text()
if "async def _handle_saved_command" not in content:
    print("⚠ slash_commands.py handler missing — manual fix needed")
else:
    print("✓ slash_commands.py — handler present")

# ── 4. Fix run.py manually (patch failed) ────────────────────────────────────
filepath = HERMES / "gateway" / "run.py"
content = filepath.read_text()

# Find the exact context around compress -> usage
# Look for the compress dispatch and insert saved after it
lines = content.split("\n")
new_lines = []
i = 0
while i < len(lines):
    new_lines.append(lines[i])
    # Check if this is the compress dispatch line
    if 'if canonical == "compress":' in lines[i]:
        # Add the next line (return statement)
        i += 1
        if i < len(lines):
            new_lines.append(lines[i])
        # Now check if next non-empty line is "if canonical == "usage":"
        # Insert "saved" dispatch before it
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            new_lines.append(lines[j])
            j += 1
        if j < len(lines) and 'if canonical == "usage"' in lines[j]:
            # Insert saved dispatch here
            new_lines.append("")
            new_lines.append("        if canonical == \"saved\":")
            new_lines.append("            return await self._handle_saved_command(event)")
        i = j
        continue
    i += 1

if 'if canonical == "saved"' not in "\n".join(new_lines):
    filepath.write_text("\n".join(new_lines))
    print("✓ run.py — added 'saved' dispatch")
else:
    print("✓ run.py — already has dispatch")

print("\nAll fixes applied!")
