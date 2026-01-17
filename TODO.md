# Chatom Roadmap & TODO

## Additional Backends to Implement

### High Priority - Enterprise/Popular Platforms

| Backend | Description | Key Considerations |
|---------|-------------|-------------------|
| **Microsoft Teams** | Dominant enterprise platform | Rich Graph API, extensive bot framework, SSO integration |
| **Telegram** | 800M+ users, excellent bot API | MTProto protocol, inline bots, payments API |
| **WhatsApp Business** | 2B+ users, growing business API | Cloud API, templates, media support |
| **Mattermost** | Open-source Slack alternative | Self-hosted, similar API patterns to Slack |
| **Zulip** | Topic-based threading | Unique threading model, great for async teams |

### Medium Priority - Niche/Growing

| Backend | Description | Key Considerations |
|---------|-------------|-------------------|
| **Rocket.Chat** | Open-source, self-hosted | REST + Realtime API, good enterprise adoption |
| **Google Chat** | Growing enterprise use | Google Workspace integration, cards UI |
| **Webex** | Enterprise video/chat | Cisco ecosystem, meetings integration |
| **Twilio Conversations** | Omnichannel messaging | SMS/MMS bridge, programmable |
| **LINE** | Dominant in Asia (Japan, Taiwan) | Rich messaging, LIFF apps |
| **WeChat Work** | Enterprise messaging (China) | WeChat ecosystem, mini-programs |

### Specialized/Emerging

| Backend | Description | Key Considerations |
|---------|-------------|-------------------|
| **Mastodon/ActivityPub** | Federated social | Decentralized, multiple instances |
| **Mumble** | Voice + text for gaming | Low-latency, self-hosted |
| **XMPP/Jabber** | Federated open standard | Extensible via XEPs |
| **Keybase** | Encrypted team chat | End-to-end encryption, Git integration |

---

## Additional Functionality

### Message Features

| Feature | Description |
|---------|-------------|
| **Scheduled Messages** | Queue messages for future delivery across backends |
| **Message Templates** | Reusable templates with variable substitution |
| **Message Translation** | Auto-translate between languages using LLM/translation APIs |
| **Message Deduplication** | Detect and handle duplicate messages across backends |
| **Read Receipts** | Track message read status where supported |

### Rich Content

| Feature | Description |
|---------|-------------|
| **Interactive Components** | Buttons, dropdowns, modals (Slack Block Kit, Discord Components) |
| **Cards/Adaptive Cards** | Rich card layouts for structured data |
| **Polls/Surveys** | Native poll creation and aggregation |
| **Forms** | Multi-field input collection |
| **Calendar Events** | Create/share calendar invites from chat |

### Cross-Backend Features

| Feature | Description |
|---------|-------------|
| **Message Bridging** | Forward/sync messages between different backends |
| **Unified Inbox** | Aggregate messages from multiple backends |
| **Cross-Platform Threads** | Maintain thread context across backends |
| **Universal User Identity** | Map users across backends (email-based linking) |
| **Presence Aggregation** | Unified presence status across platforms |

### Bot/Automation

| Feature | Description |
|---------|-------------|
| **Command Framework** | Unified slash command handling across backends |
| **Webhook Ingestion** | Generic webhook-to-message conversion |
| **Scheduled Tasks** | Cron-like scheduling for automated messages |
| **Event Routing** | Route events to handlers based on rules |
| **Rate Limiting** | Unified rate limit handling across backends |

### Analytics & Monitoring

| Feature | Description |
|---------|-------------|
| **Message Analytics** | Track message volume, response times, engagement |
| **Sentiment Analysis** | Analyze message sentiment via LLM |
| **Audit Logging** | Compliance-ready logging of all actions |
| **Health Monitoring** | Backend connectivity and latency monitoring |
| **Metrics Export** | Prometheus/OpenTelemetry integration |

### Security & Compliance

| Feature | Description |
|---------|-------------|
| **Message Encryption** | End-to-end encryption layer |
| **Content Filtering** | PII detection, profanity filtering |
| **DLP Integration** | Data loss prevention hooks |
| **Retention Policies** | Configurable message retention |
| **Access Control** | Role-based permissions across backends |

### Developer Experience

| Feature | Description |
|---------|-------------|
| **Backend Simulator** | Mock backends for testing without real connections |
| **Message Recorder** | Record/replay message sequences for testing |
| **Schema Validation** | Validate messages against backend constraints |
| **Migration Tools** | Export/import message history between backends |
| **CLI Tool** | Command-line interface for chatom operations |

---

## Quick Wins (Based on Current Architecture)

These can be added incrementally using the existing mixin architecture:

- [ ] `SCHEDULED_MESSAGES` capability + `schedule_message()` mixin method
- [ ] `INTERACTIVE_COMPONENTS` capability + new `components/` format nodes
- [ ] `WEBHOOKS` capability + webhook ingestion backend mixin
- [ ] `MESSAGE_SEARCH` capability + `search_messages()` across backends

---

## Notes

- The modular mixin architecture in `backend_mixins.py` makes adding new functionality straightforward
- New capabilities should be added to `base/capabilities.py`
- Backend-specific implementations go in their respective directories (e.g., `slack/`, `discord/`)
