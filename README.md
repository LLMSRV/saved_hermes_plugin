# /saved Slash Command

Usage: `/saved <file_name> [--overwrite|--append]`

## How it works:

1. Extracts user/assistant/tool messages from the current conversation via the session store
2. Sends them to the auxiliary LLM (same provider used for compression) with a system prompt to produce a concise markdown summary
3. Writes the summary to the specified file
4. Modes:
   - **Default (`--append`)** — appends to the file with a separator header. Preserves existing content.
   - **`--overwrite`** — replaces the entire file contents with the new summary.

## Changes Required:

These patches apply to the `nousresearch/hermes-agent` main branch. Apply in order:

### 1. `0001-saved-command-registry.patch`
- **File:** `hermes_cli/commands.py`
- **Change:** Registers `/saved` in `COMMAND_REGISTRY` so the gateway recognizes it as a valid slash command

### 2. `0002-save-summarized-module.patch`
- **File:** `hermes_cli/save_summarized.py` (NEW)
- **Change:** Shared helper module with:
  - `parse_saved_args()` — parses filename and mode flags
  - `summarize_conversation()` — calls auxiliary LLM via `call_llm(task="compression")`
  - `write_summary()` — writes to file in overwrite or append mode

### 3. `0003-gateway-handler.patch`
- **File:** `gateway/slash_commands.py`
- **Change:** Adds `_handle_saved_command()` async method to `GatewaySlashCommandsMixin`
  - Loads conversation from session store (`async_session_store.load_transcript()`)
  - Calls `summarize_conversation()` and `write_summary()` from the helper module

### 4. `0004-run-dispatch.patch`
- **File:** `gateway/run.py`
- **Change:** Adds dispatch entry `if canonical == "saved"` in the command router

## How to Apply:

```bash
# From the root of the hermes-agent checkout
cd ~/.hermes/hermes-agent

# Apply patches in order
for patch in patches/0001*.patch patches/0002*.patch patches/0003*.patch patches/0004*.patch; do
  patch -p1 < "$patch"
done

# Restart Hermes
hermes gateway restart
```

## Alternative:

Pull this branch and cherry-pick the commits, or apply the patches manually to your `~/.hermes/hermes-agent` installation.

## Troubleshooting:

- **Error: `"not a quick/plugin/bundle/skill command: saved"`** — This means the patches haven't been applied yet. The command isn't registered in the gateway's command router.
- **Error: `"No conversation to summarise"` —** Send a message first, then run `/saved`. The command needs at least one message in the session.
- **Summarisation fails** — Check your model/provider config. The command uses `call_llm(task="compression")` which resolves via the same auto-detection chain as context compression.
