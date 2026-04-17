"""Screenshot capture for Robot Framework OpenTelemetry traces.

Detects screenshots emitted by SeleniumLibrary and Browser (Playwright)
via log_message HTML output, and attaches them to the current span as
OTel span events.

Three modes:
  - "none"     → no screenshot processing (default)
  - "path"     → attach file path reference only
  - "embedded" → attach base64-encoded image data (with size guard + fallback)
"""

import base64
import hashlib
import mimetypes
import os
import re
import time
from typing import Optional

# Regex to extract src from <img> tags emitted by RF screenshot keywords.
# Handles both single and double quotes, and optional attributes before src.
_IMG_SRC_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)

# Allowed image extensions (lowercase, with dot)
_VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# Default config values
DEFAULT_MODE = "none"
DEFAULT_MAX_SIZE_KB = 200
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SEC = 0.05


class ScreenshotConfig:
    """Screenshot capture configuration.

    Integrated into TracerConfig via the 'screenshots' section
    of .rf-tracer.json or listener kwargs.
    """

    def __init__(
        self,
        mode: str = DEFAULT_MODE,
        max_size_kb: int = DEFAULT_MAX_SIZE_KB,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_delay_sec: float = DEFAULT_RETRY_DELAY_SEC,
    ):
        self.mode = mode if mode in ("none", "path", "embedded") else DEFAULT_MODE
        self.max_size_kb = max(0, int(max_size_kb))
        self.retry_attempts = max(1, int(retry_attempts))
        self.retry_delay_sec = max(0.0, float(retry_delay_sec))

    @classmethod
    def from_dict(cls, data: dict) -> "ScreenshotConfig":
        """Create from a config dict (e.g. from .rf-tracer.json screenshots section)."""
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            mode=data.get("mode", DEFAULT_MODE),
            max_size_kb=data.get("max_size_kb", DEFAULT_MAX_SIZE_KB),
            retry_attempts=data.get("retry_attempts", DEFAULT_RETRY_ATTEMPTS),
            retry_delay_sec=data.get("retry_delay_sec", DEFAULT_RETRY_DELAY_SEC),
        )


def extract_image_path(html: str) -> Optional[str]:
    """Extract image file path from an HTML log message.

    Returns the src value if the message contains an <img> tag
    pointing to a file with a valid image extension, else None.
    """
    match = _IMG_SRC_RE.search(html)
    if not match:
        return None
    src = match.group(1).strip()
    if not src:
        return None
    # Validate extension
    _, ext = os.path.splitext(src)
    if ext.lower() not in _VALID_EXTENSIONS:
        return None
    return src


def normalize_path(path: str, output_dir: str = "") -> str:
    """Resolve a potentially relative path to an absolute path.

    SeleniumLibrary and Browser log screenshot paths relative to the RF
    output directory, not the CWD. We try multiple base directories:
    1. As-is (already absolute and exists)
    2. Relative to RF output directory
    3. Relative to CWD (fallback)
    """
    if os.path.isabs(path) and os.path.isfile(path):
        return path

    # Try relative to RF output directory first (most common case)
    if output_dir:
        candidate = os.path.normpath(os.path.join(output_dir, path))
        if os.path.isfile(candidate):
            return candidate

    # Try relative to CWD
    abs_cwd = os.path.abspath(path)
    if os.path.isfile(abs_cwd):
        return abs_cwd

    # File may not exist yet (path mode) — prefer output_dir resolution
    if output_dir:
        return os.path.normpath(os.path.join(output_dir, path))
    return abs_cwd


def guess_mime_type(path: str) -> str:
    """Guess MIME type from file extension, with a safe fallback."""
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def read_with_retry(
    path: str,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    retry_delay_sec: float = DEFAULT_RETRY_DELAY_SEC,
) -> Optional[bytes]:
    """Read a file with retry logic for not-yet-flushed screenshots.

    Returns file bytes, or None if all attempts fail.
    """
    for attempt in range(retry_attempts):
        try:
            if not os.path.isfile(path):
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay_sec)
                continue
            size = os.path.getsize(path)
            if size == 0:
                # File exists but empty — not yet flushed
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay_sec)
                continue
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay_sec)
    return None


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of binary data."""
    return hashlib.sha256(data).hexdigest()


def build_event_attributes(
    config: ScreenshotConfig,
    abs_path: str,
) -> Optional[dict]:
    """Build the span event attribute dict for a screenshot.

    Returns None if mode is "none" or processing fails entirely.
    For "embedded" mode, falls back to "path" on read/size errors.
    """
    if config.mode == "none":
        return None

    filename = os.path.basename(abs_path)
    mime = guess_mime_type(abs_path)
    timestamp_ms = int(time.time() * 1000)

    if config.mode == "path":
        return {
            "rf.screenshot.mode": "path",
            "rf.screenshot.path": abs_path,
            "rf.screenshot.mime": mime,
            "rf.screenshot.name": filename,
            "rf.screenshot.timestamp": timestamp_ms,
        }

    # --- embedded mode ---
    data = read_with_retry(abs_path, config.retry_attempts, config.retry_delay_sec)

    if data is None:
        # File unreadable after retries → fallback to path
        return {
            "rf.screenshot.mode": "path_fallback",
            "rf.screenshot.path": abs_path,
            "rf.screenshot.mime": mime,
            "rf.screenshot.name": filename,
            "rf.screenshot.size": 0,
            "rf.screenshot.timestamp": timestamp_ms,
        }

    size_kb = len(data) / 1024.0
    if size_kb > config.max_size_kb:
        # Too large → fallback to path
        return {
            "rf.screenshot.mode": "path_fallback",
            "rf.screenshot.path": abs_path,
            "rf.screenshot.mime": mime,
            "rf.screenshot.name": filename,
            "rf.screenshot.size": len(data),
            "rf.screenshot.timestamp": timestamp_ms,
        }

    b64 = base64.b64encode(data).decode("ascii")
    sha = compute_sha256(data)

    return {
        "rf.screenshot.mode": "embedded",
        "rf.screenshot.path": abs_path,
        "rf.screenshot.data": b64,
        "rf.screenshot.mime": mime,
        "rf.screenshot.name": filename,
        "rf.screenshot.size": len(data),
        "rf.screenshot.sha256": sha,
        "rf.screenshot.timestamp": timestamp_ms,
    }


def process_log_message(
    config: ScreenshotConfig, span, message_html: str, output_dir: str = ""
) -> bool:
    """Check a log message for screenshot <img> tags and attach to span.

    Called from TracingListener.log_message(). Safe to call on every message;
    returns quickly if mode is "none" or no image is found.

    Args:
        config: Screenshot configuration.
        span: The current OTel span (must support add_event).
        message_html: The raw message.message string from Robot Framework.
        output_dir: RF output directory for resolving relative screenshot paths.

    Returns:
        True if a screenshot event was added, False otherwise.
    """
    if config.mode == "none":
        return False

    if not span or not message_html:
        return False

    raw_path = extract_image_path(message_html)
    if raw_path is None:
        return False

    abs_path = normalize_path(raw_path, output_dir)

    try:
        attrs = build_event_attributes(config, abs_path)
        if attrs is None:
            return False
        span.add_event("rf.screenshot", attrs)
        return True
    except Exception:
        # Never break the trace — silently skip
        return False
