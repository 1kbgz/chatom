# Tutorials

Start with the unified frontend tutorial. It runs without platform credentials and shows Chatom's central idea: application code constructs one message, while each backend receives its own native markup.

```{toctree}
:maxdepth: 1

Tutorial: one message for four backends <tutorial-unified-frontend>
Tutorial: model a conversation <tutorial-conversation>
```

## Runnable examples

The package includes complete command-line examples for live backends:

- `python -m chatom.examples.basic_connection --backend slack`
- `python -m chatom.examples.send_message --backend slack --message "Hello"`
- `python -m chatom.examples.formatted_messages --backend slack`
- `python -m chatom.examples.message_history --backend slack --limit 10`
- `python -m chatom.examples.mentions_and_reactions --backend slack`
- `python -m chatom.examples.threads_and_replies --backend slack`
- `python -m chatom.examples.direct_messages --backend slack`
- `python -m chatom.examples.listen_for_messages --backend slack --timeout 60`
- `python -m chatom.examples.cross_platform_bot`

The backend-specific modules accept `--help`. The cross-platform bot reads its enabled backends and destinations from environment variables documented in the module.
