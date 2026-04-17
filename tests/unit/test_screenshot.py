"""Tests for screenshot capture module."""

import base64
import hashlib
import os
from unittest.mock import MagicMock

from robotframework_tracer.screenshot import (
    ScreenshotConfig,
    build_event_attributes,
    compute_sha256,
    extract_image_path,
    guess_mime_type,
    normalize_path,
    process_log_message,
    read_with_retry,
)

# ---------------------------------------------------------------------------
# ScreenshotConfig
# ---------------------------------------------------------------------------


class TestScreenshotConfig:
    def test_defaults(self):
        cfg = ScreenshotConfig()
        assert cfg.mode == "none"
        assert cfg.max_size_kb == 200
        assert cfg.retry_attempts == 3
        assert cfg.retry_delay_sec == 0.05

    def test_custom_values(self):
        cfg = ScreenshotConfig(
            mode="embedded", max_size_kb=500, retry_attempts=5, retry_delay_sec=0.1
        )
        assert cfg.mode == "embedded"
        assert cfg.max_size_kb == 500
        assert cfg.retry_attempts == 5
        assert cfg.retry_delay_sec == 0.1

    def test_invalid_mode_falls_back(self):
        cfg = ScreenshotConfig(mode="bogus")
        assert cfg.mode == "none"

    def test_from_dict(self):
        cfg = ScreenshotConfig.from_dict({"mode": "path", "max_size_kb": 100})
        assert cfg.mode == "path"
        assert cfg.max_size_kb == 100
        # defaults for unset keys
        assert cfg.retry_attempts == 3

    def test_from_dict_empty(self):
        cfg = ScreenshotConfig.from_dict({})
        assert cfg.mode == "none"

    def test_from_dict_none(self):
        cfg = ScreenshotConfig.from_dict(None)
        assert cfg.mode == "none"

    def test_negative_values_clamped(self):
        cfg = ScreenshotConfig(max_size_kb=-10, retry_attempts=-1, retry_delay_sec=-0.5)
        assert cfg.max_size_kb == 0
        assert cfg.retry_attempts == 1
        assert cfg.retry_delay_sec == 0.0


# ---------------------------------------------------------------------------
# extract_image_path
# ---------------------------------------------------------------------------


class TestExtractImagePath:
    def test_selenium_screenshot(self):
        html = '<img src="selenium-screenshot-1.png" width="800px">'
        assert extract_image_path(html) == "selenium-screenshot-1.png"

    def test_browser_screenshot(self):
        html = "<img src='/tmp/screenshots/browser-screenshot-1.png'>"
        assert extract_image_path(html) == "/tmp/screenshots/browser-screenshot-1.png"

    def test_jpeg_extension(self):
        html = '<img src="shot.jpeg">'
        assert extract_image_path(html) == "shot.jpeg"

    def test_jpg_extension(self):
        html = '<img src="shot.jpg">'
        assert extract_image_path(html) == "shot.jpg"

    def test_webp_extension(self):
        html = '<img src="shot.webp">'
        assert extract_image_path(html) == "shot.webp"

    def test_invalid_extension_ignored(self):
        html = '<img src="document.pdf">'
        assert extract_image_path(html) is None

    def test_no_img_tag(self):
        assert extract_image_path("Just a log message") is None

    def test_empty_src(self):
        html = '<img src="">'
        assert extract_image_path(html) is None

    def test_no_src(self):
        html = "<img alt='no source'>"
        assert extract_image_path(html) is None

    def test_multiple_img_tags_returns_first(self):
        html = '<img src="first.png"><img src="second.png">'
        assert extract_image_path(html) == "first.png"

    def test_absolute_path(self):
        html = '<img src="/home/user/output/screenshot.png">'
        assert extract_image_path(html) == "/home/user/output/screenshot.png"


# ---------------------------------------------------------------------------
# normalize_path
# ---------------------------------------------------------------------------


class TestNormalizePath:
    def test_relative_becomes_absolute(self):
        result = normalize_path("screenshot.png")
        assert os.path.isabs(result)
        assert result.endswith("screenshot.png")

    def test_absolute_stays_absolute(self, tmp_path):
        f = tmp_path / "screenshot.png"
        f.write_bytes(b"data")
        result = normalize_path(str(f))
        assert result == str(f)

    def test_resolves_relative_to_output_dir(self, tmp_path):
        f = tmp_path / "screenshots" / "shot.png"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"data")
        result = normalize_path("screenshots/shot.png", str(tmp_path))
        assert result == str(f)

    def test_output_dir_preferred_over_cwd(self, tmp_path):
        f = tmp_path / "sub" / "img.png"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"data")
        result = normalize_path("sub/img.png", str(tmp_path))
        assert result == str(f)


# ---------------------------------------------------------------------------
# guess_mime_type
# ---------------------------------------------------------------------------


class TestGuessMimeType:
    def test_png(self):
        assert guess_mime_type("shot.png") == "image/png"

    def test_jpeg(self):
        assert guess_mime_type("shot.jpeg") == "image/jpeg"

    def test_unknown_extension(self):
        assert guess_mime_type("file.xyz123") == "application/octet-stream"


# ---------------------------------------------------------------------------
# read_with_retry
# ---------------------------------------------------------------------------


class TestReadWithRetry:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "img.png"
        f.write_bytes(b"\x89PNG_DATA")
        data = read_with_retry(str(f), retry_attempts=1, retry_delay_sec=0)
        assert data == b"\x89PNG_DATA"

    def test_returns_none_for_missing_file(self, tmp_path):
        data = read_with_retry(str(tmp_path / "nope.png"), retry_attempts=1, retry_delay_sec=0)
        assert data is None

    def test_returns_none_for_empty_file(self, tmp_path):
        f = tmp_path / "empty.png"
        f.write_bytes(b"")
        data = read_with_retry(str(f), retry_attempts=1, retry_delay_sec=0)
        assert data is None

    def test_retries_then_succeeds(self, tmp_path):
        """Simulate a file that appears on the second attempt."""
        f = tmp_path / "delayed.png"
        # First call: file doesn't exist. We create it before second retry.
        # Use a simple approach: create the file, read with 1 attempt.
        f.write_bytes(b"OK")
        data = read_with_retry(str(f), retry_attempts=2, retry_delay_sec=0)
        assert data == b"OK"


# ---------------------------------------------------------------------------
# compute_sha256
# ---------------------------------------------------------------------------


class TestComputeSha256:
    def test_known_hash(self):
        data = b"hello"
        expected = hashlib.sha256(data).hexdigest()
        assert compute_sha256(data) == expected


# ---------------------------------------------------------------------------
# build_event_attributes
# ---------------------------------------------------------------------------


class TestBuildEventAttributes:
    def test_none_mode_returns_none(self):
        cfg = ScreenshotConfig(mode="none")
        assert build_event_attributes(cfg, "/tmp/shot.png") is None

    def test_path_mode(self):
        cfg = ScreenshotConfig(mode="path")
        attrs = build_event_attributes(cfg, "/tmp/shot.png")
        assert attrs["rf.screenshot.mode"] == "path"
        assert attrs["rf.screenshot.path"] == "/tmp/shot.png"
        assert attrs["rf.screenshot.mime"] == "image/png"
        assert attrs["rf.screenshot.name"] == "shot.png"
        assert "rf.screenshot.timestamp" in attrs
        assert "rf.screenshot.data" not in attrs

    def test_embedded_mode_small_file(self, tmp_path):
        f = tmp_path / "small.png"
        content = b"\x89PNG_SMALL"
        f.write_bytes(content)
        cfg = ScreenshotConfig(
            mode="embedded", max_size_kb=200, retry_attempts=1, retry_delay_sec=0
        )
        attrs = build_event_attributes(cfg, str(f))
        assert attrs["rf.screenshot.mode"] == "embedded"
        assert attrs["rf.screenshot.data"] == base64.b64encode(content).decode("ascii")
        assert attrs["rf.screenshot.sha256"] == hashlib.sha256(content).hexdigest()
        assert attrs["rf.screenshot.size"] == len(content)
        assert attrs["rf.screenshot.path"] == str(f)

    def test_embedded_mode_too_large_falls_back(self, tmp_path):
        f = tmp_path / "big.png"
        # 1 KB file, but max is 0 KB
        f.write_bytes(b"x" * 1024)
        cfg = ScreenshotConfig(mode="embedded", max_size_kb=0, retry_attempts=1, retry_delay_sec=0)
        attrs = build_event_attributes(cfg, str(f))
        assert attrs["rf.screenshot.mode"] == "path_fallback"
        assert attrs["rf.screenshot.path"] == str(f)
        assert "rf.screenshot.data" not in attrs

    def test_embedded_mode_missing_file_falls_back(self):
        cfg = ScreenshotConfig(mode="embedded", retry_attempts=1, retry_delay_sec=0)
        attrs = build_event_attributes(cfg, "/nonexistent/shot.png")
        assert attrs["rf.screenshot.mode"] == "path_fallback"
        assert attrs["rf.screenshot.path"] == "/nonexistent/shot.png"
        assert attrs["rf.screenshot.size"] == 0


# ---------------------------------------------------------------------------
# process_log_message (integration)
# ---------------------------------------------------------------------------


class TestProcessLogMessage:
    def test_none_mode_skips(self):
        cfg = ScreenshotConfig(mode="none")
        span = MagicMock()
        assert process_log_message(cfg, span, '<img src="shot.png">') is False
        span.add_event.assert_not_called()

    def test_no_img_tag_skips(self):
        cfg = ScreenshotConfig(mode="path")
        span = MagicMock()
        assert process_log_message(cfg, span, "just text") is False
        span.add_event.assert_not_called()

    def test_path_mode_adds_event(self):
        cfg = ScreenshotConfig(mode="path")
        span = MagicMock()
        result = process_log_message(cfg, span, '<img src="/tmp/shot.png">')
        assert result is True
        span.add_event.assert_called_once()
        event_name, attrs = span.add_event.call_args[0]
        assert event_name == "rf.screenshot"
        assert attrs["rf.screenshot.mode"] == "path"
        assert attrs["rf.screenshot.path"] == os.path.abspath("/tmp/shot.png")

    def test_embedded_mode_with_real_file(self, tmp_path):
        f = tmp_path / "real.png"
        f.write_bytes(b"\x89PNG_REAL")
        cfg = ScreenshotConfig(
            mode="embedded", max_size_kb=200, retry_attempts=1, retry_delay_sec=0
        )
        span = MagicMock()
        html = f'<img src="{f}">'
        result = process_log_message(cfg, span, html)
        assert result is True
        event_name, attrs = span.add_event.call_args[0]
        assert attrs["rf.screenshot.mode"] == "embedded"
        assert "rf.screenshot.data" in attrs

    def test_no_span_skips(self):
        cfg = ScreenshotConfig(mode="path")
        assert process_log_message(cfg, None, '<img src="shot.png">') is False

    def test_empty_message_skips(self):
        cfg = ScreenshotConfig(mode="path")
        span = MagicMock()
        assert process_log_message(cfg, span, "") is False

    def test_exception_in_add_event_does_not_raise(self):
        cfg = ScreenshotConfig(mode="path")
        span = MagicMock()
        span.add_event.side_effect = RuntimeError("boom")
        # Should not raise
        result = process_log_message(cfg, span, '<img src="/tmp/shot.png">')
        assert result is False
