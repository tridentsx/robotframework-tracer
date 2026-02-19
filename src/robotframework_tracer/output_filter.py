"""Output filter for trace JSON files.

Loads a filter configuration and applies it to OTLP JSON dicts
before they are written to the output file.
"""

import fnmatch
import json
import os

import jsonschema

CURRENT_SCHEMA_VERSION = "1.0.0"

# Sentinel lists that mean "include everything"
_ALL = ["*"]
_ALL_KW_TYPES = ["KEYWORD", "SETUP", "TEARDOWN"]

_SCHEMA_CACHE = None


def _load_schema():
    """Load and cache the JSON Schema for output filter validation."""
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        schema_path = os.path.join(os.path.dirname(__file__), "schemas", "output-filter-v1.json")
        with open(schema_path) as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


def _validate_filter(cfg):
    """Validate filter config against JSON Schema. Returns list of error messages."""
    schema = _load_schema()
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(cfg), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors


def load_filter(path):
    """Load a filter config from a JSON file. Returns None if path is empty."""
    if not path:
        return None
    # Resolve built-in preset names (e.g. "minimal" -> bundled preset)
    if not os.path.isfile(path):
        preset_dir = os.path.join(os.path.dirname(__file__), "presets")
        candidate = os.path.join(preset_dir, f"{path}.json")
        if os.path.isfile(candidate):
            path = candidate
        else:
            print(f"Warning: Output filter file not found: {path}")
            return None
    with open(path) as f:
        cfg = json.load(f)
    v = cfg.get("version", "")
    if not v.startswith("1."):
        print(f"Warning: Unsupported output filter version '{v}', ignoring filter")
        return None
    errors = _validate_filter(cfg)
    if errors:
        print(f"Warning: Output filter validation errors in '{path}':")
        for err in errors:
            print(f"  - {err}")
        print("Filter will be ignored.")
        return None
    return cfg


def _match_any(key, patterns):
    """Return True if key matches any of the glob patterns."""
    return any(fnmatch.fnmatch(key, p) for p in patterns)


def _filter_attributes(attrs, include, exclude):
    """Filter an OTLP attribute list by include/exclude glob patterns.

    Empty include list means include all. Empty exclude list means exclude nothing.
    """
    if not attrs:
        return attrs
    result = []
    for a in attrs:
        key = a.get("key", "")
        if exclude and _match_any(key, exclude):
            continue
        if include:
            if not _match_any(key, include):
                continue
        result.append(a)
    return result


def _span_type(span):
    """Determine span type from attributes: suite, test, or keyword."""
    for a in span.get("attributes", []):
        k = a.get("key", "")
        if k == "rf.suite.name":
            return "suite"
        if k == "rf.test.name":
            return "test"
        if k == "rf.keyword.type":
            return "keyword"
    return "keyword"


def _keyword_type(span):
    """Get keyword type (KEYWORD, SETUP, TEARDOWN) from span attributes."""
    for a in span.get("attributes", []):
        if a.get("key") == "rf.keyword.type":
            return a.get("value", {}).get("string_value", "KEYWORD")
    return "KEYWORD"


def _compute_depths(parent_map, depth_map):
    """Compute depth for each span_id based on parent relationships."""

    def _depth(sid):
        if sid in depth_map:
            return depth_map[sid]
        pid = parent_map.get(sid, "")
        if not pid or pid not in parent_map:
            depth_map[sid] = 0
            return 0
        depth_map[sid] = _depth(pid) + 1
        return depth_map[sid]

    for sid in parent_map:
        _depth(sid)


def _or_default(val, default):
    """Return default if val is None or empty list."""
    if val is None or val == []:
        return default
    return val


def apply_filter(d, cfg):
    """Apply filter config to an OTLP JSON dict (one ExportTraceServiceRequest).

    Empty lists and null values mean "include everything" (no filtering).
    Modifies and returns d in-place.
    """
    if cfg is None:
        return d

    spans_cfg = cfg.get("spans", {})
    resource_cfg = cfg.get("resource", {})
    scope_cfg = cfg.get("scope", {})

    include_suites = spans_cfg.get("include_suites", True)
    include_tests = spans_cfg.get("include_tests", True)
    include_keywords = spans_cfg.get("include_keywords", True)
    keyword_types = _or_default(spans_cfg.get("keyword_types"), _ALL_KW_TYPES)
    max_depth = spans_cfg.get("max_depth", None)
    allowed_fields = _or_default(spans_cfg.get("fields"), None)
    include_events = spans_cfg.get("include_events", True)
    attr_include = _or_default(spans_cfg.get("attributes", {}).get("include"), [])
    attr_exclude = _or_default(spans_cfg.get("attributes", {}).get("exclude"), [])

    res_include_attrs = resource_cfg.get("include_attributes", True)
    res_attr_keys = _or_default(resource_cfg.get("attribute_keys"), [])

    include_scope = scope_cfg.get("include", True)

    # Build depth map: span_id -> depth (root=0)
    depth_map = {}
    if max_depth is not None:
        for rs in d.get("resource_spans", []):
            for ss in rs.get("scope_spans", []):
                parent_map = {}
                for span in ss.get("spans", []):
                    parent_map[span.get("span_id", "")] = span.get("parent_span_id", "")
                _compute_depths(parent_map, depth_map)

    for rs in d.get("resource_spans", []):
        # Filter resource attributes
        if not res_include_attrs:
            rs.get("resource", {}).pop("attributes", None)
        elif res_attr_keys:
            res = rs.get("resource", {})
            if "attributes" in res:
                res["attributes"] = [
                    a for a in res["attributes"] if _match_any(a.get("key", ""), res_attr_keys)
                ]

        for ss in rs.get("scope_spans", []):
            if not include_scope:
                ss.pop("scope", None)

            filtered = []
            for span in ss.get("spans", []):
                st = _span_type(span)

                if st == "suite" and not include_suites:
                    continue
                if st == "test" and not include_tests:
                    continue
                if st == "keyword" and not include_keywords:
                    continue
                if st == "keyword" and _keyword_type(span) not in keyword_types:
                    continue

                if max_depth is not None:
                    if depth_map.get(span.get("span_id", ""), 0) > max_depth:
                        continue

                if "attributes" in span and (attr_include or attr_exclude):
                    span["attributes"] = _filter_attributes(
                        span["attributes"], attr_include, attr_exclude
                    )

                if not include_events:
                    span.pop("events", None)

                if allowed_fields is not None:
                    for k in list(span.keys()):
                        if k not in allowed_fields:
                            del span[k]

                filtered.append(span)

            ss["spans"] = filtered

    return d
