# Runtime Hooks

This plugin maps ECC hook semantics into Agent0 extension points and executes configured ECC hook commands via:

- `python/helpers/ecc_sync/transform_hooks.py`
- `python/helpers/ecc_sync/hook_runtime.py`

Installed hook bridge files are generated under:

- `usr/extensions/agent_init/_80_ecc_*.py`
- `usr/extensions/tool_execute_before/_80_ecc_*.py`
- `usr/extensions/tool_execute_after/_80_ecc_*.py`
- `usr/extensions/message_loop_end/_80_ecc_*.py`
- `usr/extensions/message_loop_prompts_before/_80_ecc_*.py`
