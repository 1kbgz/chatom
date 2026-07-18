# Expose a backend to agents and MCP clients

Chatom can expose the same backend contract through pydantic-ai or FastMCP. Both integrations derive available operations from backend capabilities.

## Add a backend to a pydantic-ai agent

Install the optional dependency:

```bash
pip install 'chatom[agent]'
```

Create a toolset and pass it to an agent:

```python
from chatom.agent import AccessPolicy, BackendToolset
from pydantic_ai import Agent

policy = AccessPolicy(
    requesting_user=requesting_user,
    invoking_channel_id=channel.id,
    restrict_to_invoking_channel=True,
    require_membership=True,
    block_dm_reads=True,
    max_messages_per_request=50,
)

toolset = BackendToolset(
    backend,
    read_only=True,
    access_policy=policy,
    max_tool_calls=8,
    per_tool_limits={"read_channel_history": 3},
)
agent = Agent("provider:model", toolsets=[toolset])
result = await agent.run("Summarize recent discussion in this channel")
```

Create a new {class}`chatom.agent.BackendToolset` for each agent run when using call budgets.

## Run the MCP server

Install the MCP extra and select a gateway preset:

```bash
pip install 'chatom[mcp]'
export SLACK_BOT_TOKEN='xoxb-...'
chatom-mcp +gateway=slack
```

Built-in presets are `discord`, `slack`, `symphony`, `symphony_dev`, and `telegram`. The default transport is stdio.

Run a read-only HTTP server:

```bash
chatom-mcp +gateway=slack \
  server.transport=http \
  server.host=127.0.0.1 \
  server.port=8080 \
  server.read_only=true
```

Filter tools with Hydra list overrides:

```bash
chatom-mcp +gateway=slack \
  'server.enabled_tools=[read_channel_history,search_messages,lookup_user]'
```

`delete_message` and `set_presence` are disabled by default. With multiple programmatic backends, tool names receive a backend prefix such as `slack__send_message`.

## Build an MCP server in Python

```python
from chatom.mcp import build_mcp_server

mcp = build_mcp_server(
    {"slack": slack_backend, "discord": discord_backend},
    read_only=True,
    disabled_tools={"download_attachment"},
)
mcp.run(transport="stdio")
```
