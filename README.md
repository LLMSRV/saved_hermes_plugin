/saved slash command
Usage: /saved <file_name> [--overwrite|--append]

How it works:

Extracts user/assistant turns from the current conversation
Sends them to the auxiliary LLM (same provider used for compression) with a system prompt to produce a concise markdown summary
Writes the summary to the specified file
Modes:

Default 
- (--append) — appends to the file with a timestamped ===== Appended: 2026-07-19 14:32:01 ===== header separator. Preserves existing content.
- --overwrite — replaces the entire file contents with the new summary.

## Changes:
hermes_cli/commands.py	Registered /saved in COMMAND_REGISTRY
hermes_cli/save_summarized.py	New — shared helper: arg parsing, LLM summarization, file writing
cli.py	Added _handle_saved_command() method + dispatch in process_command()
gateway/slash_commands.py	Added _handle_saved_command() async method
gateway/run.py	Added dispatch entry for canonical == "saved"
