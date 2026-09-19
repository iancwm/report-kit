# OpenAI-style adapter

`reportkit_tools.py` generates `tools.json` from the live argparse parser and
`COMMAND_CONTRACT`. The bundle uses the Responses API function-tool shape and
omits `--json` because the adapter always requests and validates JSON output.

Regenerate it after changing the CLI contract:

```bash
python3 adapters/openai/reportkit_tools.py
```

The `write_minimal_publication()` proof uses only `reportkit context --json`
and `reportkit check --json`, plus the published schemas. It does not read
`SKILL.md` or any host-specific reference.
