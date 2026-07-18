# Integration APIs

Cross-platform bridging, interaction dispatch, agent tools, MCP servers, and CSP adapters.

## Bridging

```{eval-rst}
.. autoclass:: chatom.bridge.IdentityMapper
   :members:
   :member-order: bysource

.. autoclass:: chatom.bridge.MessageBridge
   :members:
   :member-order: bysource
```

## Interaction dispatch

```{eval-rst}
.. automodule:: chatom.handlers
   :members:
   :member-order: bysource
```

## Agents

Requires `chatom[agent]`.

```{eval-rst}
.. autoclass:: chatom.agent.AccessDeniedError

.. autoclass:: chatom.agent.AccessPolicy
   :members:

.. autoclass:: chatom.agent.BackendToolset
   :members:
   :member-order: bysource

.. autoclass:: chatom.agent.ToolBudgetExceededError

.. autoclass:: chatom.agent.ChannelContext
   :members:
   :member-order: bysource

.. autofunction:: chatom.agent.build_channel_context
```

## Model Context Protocol

Requires `chatom[mcp]`.

```{eval-rst}
.. autofunction:: chatom.mcp.build_mcp_server
```

## CSP

Requires `csp`.

```{eval-rst}
.. autoclass:: chatom.csp.BackendAdapter
   :members:
   :member-order: bysource

.. autofunction:: chatom.csp.message_reader

.. autofunction:: chatom.csp.message_writer

.. autofunction:: chatom.csp.interaction_reader
```
