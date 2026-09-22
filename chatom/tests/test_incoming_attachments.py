"""Tests for extracting incoming attachments into chatom Message.attachments.

Each backend converts platform-specific media on received messages into
chatom :class:`~chatom.base.Attachment` / :class:`~chatom.base.Image`
objects. These tests exercise the pure extraction helpers with lightweight
fakes so no platform SDK or network is required.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatom.backend import AttachmentDownloadLimitError
from chatom.base import Attachment, AttachmentType


class TestSlackIncomingAttachments:
    def test_image_and_document(self):
        from chatom.slack.backend import _slack_attachments

        files = [
            {
                "id": "F1",
                "name": "chart.png",
                "mimetype": "image/png",
                "size": 2048,
                "url_private": "https://files.slack.com/chart.png",
                "original_w": 800,
                "original_h": 600,
            },
            {
                "id": "F2",
                "name": "report.pdf",
                "mimetype": "application/pdf",
                "size": 9000,
                "url_private_download": "https://files.slack.com/report.pdf",
            },
        ]
        atts = _slack_attachments(files)
        assert len(atts) == 2
        img = atts[0]
        assert img.attachment_type == AttachmentType.IMAGE
        assert img.id == "F1"
        assert img.url == "https://files.slack.com/chart.png"
        assert img.width == 800 and img.height == 600
        doc = atts[1]
        assert doc.attachment_type == AttachmentType.DOCUMENT
        # prefers url_private_download
        assert doc.url == "https://files.slack.com/report.pdf"

    def test_empty(self):
        from chatom.slack.backend import _slack_attachments

        assert _slack_attachments([]) == []
        assert _slack_attachments(None) == []

    def test_download_forwards_limit_to_authenticated_url(self):
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        backend._download_url = AsyncMock(return_value=b"hello")
        attachment = Attachment(id="F1", url="https://files.slack.com/f.bin")

        assert asyncio.run(backend.download_attachment(attachment, max_bytes=5)) == b"hello"
        backend._download_url.assert_awaited_once_with(
            "https://files.slack.com/f.bin",
            headers=None,
            max_bytes=5,
        )

    def test_invalid_limit_fails_before_file_lookup(self):
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        backend.connected = True
        backend._async_client = SimpleNamespace(files_info=AsyncMock())

        with pytest.raises(ValueError, match="positive"):
            asyncio.run(backend.download_attachment(Attachment(id="F1"), max_bytes=0))

        backend._async_client.files_info.assert_not_awaited()


class TestDiscordIncomingAttachments:
    def test_image_and_file(self):
        from chatom.discord.backend import _discord_attachments

        msg = SimpleNamespace(
            attachments=[
                SimpleNamespace(
                    id=111,
                    filename="pic.jpg",
                    url="https://cdn.discord/pic.jpg",
                    content_type="image/jpeg",
                    size=1234,
                    width=640,
                    height=480,
                    description="a pic",
                ),
                SimpleNamespace(
                    id=222,
                    filename="data.csv",
                    url="https://cdn.discord/data.csv",
                    content_type="text/csv",
                    size=55,
                ),
            ]
        )
        atts = _discord_attachments(msg)
        assert len(atts) == 2
        assert atts[0].attachment_type == AttachmentType.IMAGE
        assert atts[0].id == "111"
        assert atts[0].url == "https://cdn.discord/pic.jpg"
        assert atts[0].alt_text == "a pic"
        # text/* maps to CODE per from_content_type
        assert atts[1].id == "222"
        assert atts[1].url == "https://cdn.discord/data.csv"

    def test_no_attachments(self):
        from chatom.discord.backend import _discord_attachments

        assert _discord_attachments(SimpleNamespace(attachments=[])) == []
        assert _discord_attachments(SimpleNamespace()) == []


class TestTelegramIncomingAttachments:
    def test_photo_largest_selected(self):
        from chatom.telegram.message import _telegram_attachments

        msg = SimpleNamespace(
            photo=[
                SimpleNamespace(file_id="small", width=90, height=90, file_size=100),
                SimpleNamespace(file_id="big", width=1280, height=1280, file_size=5000),
            ],
            document=None,
            video=None,
            audio=None,
            voice=None,
        )
        atts = _telegram_attachments(msg)
        assert len(atts) == 1
        assert atts[0].attachment_type == AttachmentType.IMAGE
        # Telegram has no URL — the file_id is stored as the id for getFile.
        assert atts[0].id == "big"
        assert atts[0].url == ""
        assert atts[0].width == 1280

    def test_document(self):
        from chatom.telegram.message import _telegram_attachments

        msg = SimpleNamespace(
            photo=None,
            document=SimpleNamespace(file_id="D1", file_name="notes.pdf", mime_type="application/pdf", file_size=900),
            video=None,
            audio=None,
            voice=None,
        )
        atts = _telegram_attachments(msg)
        assert len(atts) == 1
        assert atts[0].id == "D1"
        assert atts[0].filename == "notes.pdf"
        assert atts[0].attachment_type == AttachmentType.DOCUMENT

    def test_none(self):
        from chatom.telegram.message import _telegram_attachments

        msg = SimpleNamespace(photo=None, document=None, video=None, audio=None, voice=None)
        assert _telegram_attachments(msg) == []

    def test_download_rejects_reported_oversize_before_materializing(self):
        from chatom.telegram import TelegramBackend

        tg_file = SimpleNamespace(file_size=6, file_path="https://telegram/f.bin", download_as_bytearray=AsyncMock())
        backend = TelegramBackend()
        backend.connected = True
        backend._bot = SimpleNamespace(get_file=AsyncMock(return_value=tg_file))

        with pytest.raises(AttachmentDownloadLimitError) as exc_info:
            asyncio.run(backend.download_attachment(Attachment(id="F1"), max_bytes=5))

        assert exc_info.value.actual_size == 6
        tg_file.download_as_bytearray.assert_not_awaited()

    def test_invalid_limit_fails_before_file_lookup(self):
        from chatom.telegram import TelegramBackend

        backend = TelegramBackend()
        backend.connected = True
        backend._bot = SimpleNamespace(get_file=AsyncMock())

        with pytest.raises(ValueError, match="positive"):
            asyncio.run(backend.download_attachment(Attachment(id="F1"), max_bytes=0))

        backend._bot.get_file.assert_not_awaited()

    def test_bounded_download_uses_http_helper(self):
        from chatom.telegram import TelegramBackend

        tg_file = SimpleNamespace(file_size=1, file_path="https://telegram/f.bin", download_as_bytearray=AsyncMock())
        backend = TelegramBackend()
        backend.connected = True
        backend._bot = SimpleNamespace(get_file=AsyncMock(return_value=tg_file))
        backend._download_url = AsyncMock(return_value=b"hello")

        assert asyncio.run(backend.download_attachment(Attachment(id="F1"), max_bytes=5)) == b"hello"
        backend._download_url.assert_awaited_once_with("https://telegram/f.bin", max_bytes=5)
        tg_file.download_as_bytearray.assert_not_awaited()

    def test_bounded_download_without_http_path_fails_closed(self):
        from chatom.telegram import TelegramBackend

        tg_file = SimpleNamespace(file_size=None, file_path=None, download_as_bytearray=AsyncMock())
        backend = TelegramBackend()
        backend.connected = True
        backend._bot = SimpleNamespace(get_file=AsyncMock(return_value=tg_file))

        with pytest.raises(AttachmentDownloadLimitError) as exc_info:
            asyncio.run(backend.download_attachment(Attachment(id="F1"), max_bytes=5))

        assert exc_info.value.actual_size is None
        tg_file.download_as_bytearray.assert_not_awaited()

    def test_unbounded_download_retains_sdk_behavior(self):
        from chatom.telegram import TelegramBackend

        tg_file = SimpleNamespace(file_size=None, file_path=None, download_as_bytearray=AsyncMock(return_value=bytearray(b"hello")))
        backend = TelegramBackend()
        backend.connected = True
        backend._bot = SimpleNamespace(get_file=AsyncMock(return_value=tg_file))

        assert asyncio.run(backend.download_attachment(Attachment(id="F1"))) == b"hello"
        tg_file.download_as_bytearray.assert_awaited_once()


class TestSymphonyIncomingAttachments:
    def test_attachment_metadata_carries_ids(self):
        from chatom.symphony.backend import _symphony_attachments

        infos = [
            SimpleNamespace(id="A1", name="diagram.png", size=4000, images=None),
            SimpleNamespace(id="A2", name="spec.pdf", size=8000, images=None),
        ]
        atts = _symphony_attachments(infos, stream_id="STREAM1", message_id="MSG1")
        assert len(atts) == 2
        img = atts[0]
        assert img.attachment_type == AttachmentType.IMAGE
        assert img.id == "A1"
        # The stream/message IDs required to download are stored in metadata.
        assert img.metadata == {"stream_id": "STREAM1", "message_id": "MSG1"}
        doc = atts[1]
        assert doc.attachment_type == AttachmentType.DOCUMENT
        assert doc.metadata["message_id"] == "MSG1"

    def test_empty(self):
        from chatom.symphony.backend import _symphony_attachments

        assert _symphony_attachments(None, "s", "m") == []

    @pytest.mark.parametrize("size", [None, 4])
    def test_bounded_download_fails_before_bdk_call(self, size):
        from chatom.symphony import SymphonyBackend

        message_service = SimpleNamespace(get_attachment=AsyncMock())
        backend = SymphonyBackend()
        backend._bdk = SimpleNamespace(messages=MagicMock(return_value=message_service))
        attachment = Attachment(
            id="A1",
            size=size,
            metadata={"stream_id": "S1", "message_id": "M1"},
        )

        with pytest.raises(AttachmentDownloadLimitError) as exc_info:
            asyncio.run(backend.download_attachment(attachment, max_bytes=5))

        assert exc_info.value.actual_size == size
        message_service.get_attachment.assert_not_awaited()

    def test_unbounded_download_retains_bdk_behavior(self):
        import base64

        from chatom.symphony import SymphonyBackend

        message_service = SimpleNamespace(get_attachment=AsyncMock(return_value=base64.b64encode(b"hello")))
        backend = SymphonyBackend()
        backend._bdk = SimpleNamespace(messages=MagicMock(return_value=message_service))
        attachment = Attachment(id="A1", metadata={"stream_id": "S1", "message_id": "M1"})

        assert asyncio.run(backend.download_attachment(attachment)) == b"hello"
        message_service.get_attachment.assert_awaited_once()
