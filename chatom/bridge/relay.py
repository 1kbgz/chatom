"""Message bridge for cross-backend message forwarding.

Forwards messages between chat backends with automatic format
conversion and mention translation via an IdentityMapper.
"""

import logging
from typing import Any, Dict, List, Optional

from chatom.base import Message
from chatom.format import FormattedMessage, Text, UserMention
from chatom.format.attachment import FormattedAttachment

from .identity import IdentityMapper

log = logging.getLogger(__name__)

__all__ = ("MessageBridge",)


class MessageBridge:
    """Forwards messages between two chat backends.

    Handles:
    - Format conversion (markdown ↔ HTML ↔ MessageML)
    - Mention translation via IdentityMapper
    - Sender attribution
    - Attachment forwarding

    Example::

        bridge = MessageBridge(
            source=slack_backend,
            dest=symphony_backend,
            identity_mapper=mapper,
            channels={"C123": "sym_stream_id"},
        )

        # Forward a single message
        await bridge.forward(message)

        # Forward with explicit target channel
        await bridge.forward(message, to_channel="sym_stream_id")
    """

    def __init__(
        self,
        source: Any,
        dest: Any,
        *,
        source_name: str = "",
        dest_name: str = "",
        identity_mapper: Optional[IdentityMapper] = None,
        channels: Optional[Dict[str, str]] = None,
        attribution: bool = True,
        attribution_format: str = "📨 {name} (via {source}):\n",
    ) -> None:
        """Initialize the bridge.

        Args:
            source: Source backend (BackendBase instance).
            dest: Destination backend (BackendBase instance).
            source_name: Name for the source backend (auto-detected if empty).
            dest_name: Name for the destination backend (auto-detected if empty).
            identity_mapper: Optional mapper for cross-backend user resolution.
            channels: Mapping of source channel IDs to dest channel IDs.
            attribution: Whether to prepend sender attribution to forwarded messages.
            attribution_format: Format string for attribution. Supports ``{name}``,
                ``{source}``, ``{email}``, ``{handle}``.
        """
        self.source = source
        self.dest = dest
        self.source_name = source_name or getattr(source, "name", "") or type(source).__name__
        self.dest_name = dest_name or getattr(dest, "name", "") or type(dest).__name__
        self.mapper = identity_mapper
        self.channels = channels or {}
        self.attribution = attribution
        self.attribution_format = attribution_format

    async def forward(
        self,
        message: Message,
        *,
        to_channel: Optional[str] = None,
        include_attachments: bool = True,
    ) -> Optional[Message]:
        """Forward a message from source to dest.

        1. Resolves the target channel
        2. Converts the message to a FormattedMessage
        3. Translates mentions via the IdentityMapper
        4. Prepends sender attribution (if enabled)
        5. Renders for the destination backend and sends

        Args:
            message: The source message to forward.
            to_channel: Explicit target channel ID (overrides channel map).
            include_attachments: Whether to include attachments.

        Returns:
            The sent message on the destination, or None on failure.
        """
        # Resolve target channel
        channel_id = to_channel
        if not channel_id and message.channel_id:
            channel_id = self.channels.get(message.channel_id)
        if not channel_id:
            log.warning("No target channel for message %s (source channel %s)", message.id, message.channel_id)
            return None

        # Build a FormattedMessage from the source message
        fm = await self._build_formatted(message, include_attachments=include_attachments)

        # Send via dest backend
        rendered = fm.render_for(self.dest_name)

        kwargs: Dict[str, Any] = {}
        if fm.attachments:
            kwargs["attachments"] = [_fa_to_base_attachment(a) for a in fm.attachments]
        if fm.embeds:
            kwargs["embeds"] = [fe.embed for fe in fm.embeds]

        try:
            result = await self.dest.send_message(
                channel=channel_id,
                content=rendered,
                **kwargs,
            )
            log.debug("Forwarded message %s to %s channel %s", message.id, self.dest_name, channel_id)
            return result
        except Exception:
            log.exception("Failed forwarding message %s", message.id)
            return None

    async def forward_many(
        self,
        messages: List[Message],
        *,
        to_channel: Optional[str] = None,
        include_attachments: bool = True,
    ) -> List[Message]:
        """Forward multiple messages in order.

        Args:
            messages: Source messages.
            to_channel: Target channel (uses channel map if not provided).
            include_attachments: Whether to include attachments.

        Returns:
            List of sent messages (None entries excluded).
        """
        results = []
        for msg in messages:
            result = await self.forward(msg, to_channel=to_channel, include_attachments=include_attachments)
            if result is not None:
                results.append(result)
        return results

    async def _build_formatted(
        self,
        message: Message,
        *,
        include_attachments: bool = True,
    ) -> FormattedMessage:
        """Convert a source message to a FormattedMessage with translated mentions."""
        fm = FormattedMessage()

        # Attribution prefix
        if self.attribution:
            attr_text = await self._build_attribution(message)
            if attr_text:
                fm.add_text(attr_text)

        # Convert content — parse platform mentions from raw text and
        # translate to UserMention nodes with target-backend user IDs
        if message.content:
            content_nodes = await self._translate_content(message.content, message.backend)
            fm.content.extend(content_nodes)

        # Carry over attachments
        if include_attachments:
            for att in message.attachments:
                fm.attachments.append(
                    FormattedAttachment(
                        filename=att.filename,
                        url=att.url,
                        data=getattr(att, "data", None),
                        content_type=att.content_type,
                        size=att.size,
                    )
                )

        # Carry over embeds
        if message.embeds:
            from chatom.format.embed import FormattedEmbed

            for embed in message.embeds:
                fm.embeds.append(FormattedEmbed(embed=embed))

        return fm

    async def _build_attribution(self, message: Message) -> str:
        """Build the attribution prefix for a forwarded message."""
        name = "Unknown"
        email = ""
        handle = ""

        if message.author:
            name = message.author.best_display_name
            email = message.author.email
            handle = message.author.handle

        return self.attribution_format.format(
            name=name,
            source=self.source_name,
            email=email,
            handle=handle,
        )

    async def _translate_content(
        self,
        content: str,
        source_backend: str,
    ) -> list:
        """Parse platform mentions from raw text and translate to target-backend UserMention nodes.

        Any text between mentions is preserved as Text nodes.
        """
        # Each backend declares its own mention regex on the class.
        # ``None`` means the backend doesn't embed user IDs inline
        # (e.g. Telegram uses MessageEntity) and we pass content through.
        pattern = getattr(self.source, "mention_pattern", None)
        if pattern is None or self.mapper is None:
            return [Text(content=content)]

        nodes: list = []
        last_end = 0

        for match in pattern.finditer(content):
            # Text before this mention
            if match.start() > last_end:
                nodes.append(Text(content=content[last_end : match.start()]))

            source_user_id = match.group(1)

            # Resolve to target backend
            target_user = await self.mapper.resolve(
                source_user_id,
                source=source_backend,
                target=self.dest_name,
            )

            if target_user:
                nodes.append(
                    UserMention(
                        user_id=target_user.id,
                        display_name=target_user.best_display_name,
                    )
                )
            else:
                # Could not resolve — try to get display name from source
                display_name = await self._get_source_display_name(source_user_id, source_backend)
                nodes.append(Text(content=f"@{display_name}"))

            last_end = match.end()

        # Remaining text
        if last_end < len(content):
            nodes.append(Text(content=content[last_end:]))

        return nodes if nodes else [Text(content=content)]

    async def _get_source_display_name(self, user_id: str, backend: str) -> str:
        """Fetch a display name from the source backend for an unresolved mention."""
        try:
            user = await self.source.fetch_user(user_id)
            if user:
                return user.best_display_name
        except Exception:
            pass
        return user_id


def _fa_to_base_attachment(fa: FormattedAttachment):
    """Convert a FormattedAttachment to a base Attachment for send_message kwargs."""
    from chatom.base.attachment import Attachment

    return Attachment(
        filename=fa.filename,
        url=fa.url,
        data=fa.data,
        content_type=fa.content_type,
        size=fa.size,
    )
