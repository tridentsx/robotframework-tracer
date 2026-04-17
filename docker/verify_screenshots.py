#!/usr/bin/env python3
"""Verify screenshot events in trace output JSON.

Usage:
    # Expect screenshots present (embedded or path mode)
    python3 verify_screenshots.py trace_embedded.json

    # Expect NO screenshots (none mode)
    python3 verify_screenshots.py trace_none.json --expect-none

    # Expect only path mode (no base64 data)
    python3 verify_screenshots.py trace_path.json --expect-path-only

    # Expect at least one path_fallback (oversized file)
    python3 verify_screenshots.py trace_embedded.json --expect-fallback
"""

import argparse
import json
import sys


def find_screenshot_events(trace_data):
    """Extract all rf.screenshot events from OTLP trace JSON."""
    events = []
    for rs in trace_data.get("resource_spans", []):
        for ss in rs.get("scope_spans", []):
            for span in ss.get("spans", []):
                span_name = span.get("name", "")
                for event in span.get("events", []):
                    if event.get("name") == "rf.screenshot":
                        attrs = {}
                        for a in event.get("attributes", []):
                            key = a.get("key", "")
                            val = a.get("value", {})
                            for vtype in ("stringValue", "string_value",
                                        "intValue", "int_value",
                                        "boolValue", "bool_value"):
                                if vtype in val:
                                    attrs[key] = val[vtype]
                                    break
                        events.append({"span": span_name, "attrs": attrs})
    return events


def load_trace_file(path):
    """Load a trace file that may contain multiple concatenated JSON objects."""
    all_events = []
    with open(path) as f:
        content = f.read().strip()
    if not content:
        return all_events
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(content):
        while pos < len(content) and content[pos] in " \t\n\r":
            pos += 1
        if pos >= len(content):
            break
        try:
            obj, end = decoder.raw_decode(content, pos)
            all_events.extend(find_screenshot_events(obj))
            pos = end
        except json.JSONDecodeError:
            break
    return all_events


def print_events(events):
    for i, ev in enumerate(events, 1):
        attrs = ev["attrs"]
        mode = attrs.get("rf.screenshot.mode", "?")
        name = attrs.get("rf.screenshot.name", "?")
        mime = attrs.get("rf.screenshot.mime", "?")
        ts = attrs.get("rf.screenshot.timestamp", "?")
        has_data = "rf.screenshot.data" in attrs
        has_path = "rf.screenshot.path" in attrs
        sha = attrs.get("rf.screenshot.sha256", "")
        size = attrs.get("rf.screenshot.size", "")

        print(f"  [{i}] {name}")
        print(f"      span:  {ev['span']}")
        print(f"      mode:  {mode}")
        print(f"      mime:  {mime}")
        if has_path:
            print(f"      path:  {attrs['rf.screenshot.path']}")
        if has_data:
            print(f"      data:  {len(attrs['rf.screenshot.data'])} chars (base64)")
        if size:
            print(f"      size:  {size} bytes")
        if sha:
            print(f"      sha256: {sha[:16]}...")
        print(f"      ts:    {ts}")
        print()


def validate_common(events):
    """Validate required fields on all events."""
    errors = []
    for ev in events:
        attrs = ev["attrs"]
        for field in ("rf.screenshot.mode", "rf.screenshot.name",
                       "rf.screenshot.mime", "rf.screenshot.timestamp"):
            if field not in attrs:
                errors.append(f"Missing {field} on span '{ev['span']}'")
        mode = attrs.get("rf.screenshot.mode", "")
        if mode == "embedded":
            if "rf.screenshot.data" not in attrs:
                errors.append(f"embedded mode but no data on span '{ev['span']}'")
            if "rf.screenshot.sha256" not in attrs:
                errors.append(f"embedded mode but no sha256 on span '{ev['span']}'")
            if "rf.screenshot.size" not in attrs:
                errors.append(f"embedded mode but no size on span '{ev['span']}'")
        if mode in ("path", "path_fallback"):
            if "rf.screenshot.path" not in attrs:
                errors.append(f"{mode} mode but no path on span '{ev['span']}'")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Verify screenshot trace events")
    parser.add_argument("trace_file", help="Path to trace JSON file")
    parser.add_argument("--expect-none", action="store_true",
                        help="Expect zero screenshot events (none mode)")
    parser.add_argument("--expect-path-only", action="store_true",
                        help="Expect only path mode events (no embedded data)")
    parser.add_argument("--expect-fallback", action="store_true",
                        help="Expect at least one path_fallback event")
    parser.add_argument("--min-events", type=int, default=0,
                        help="Minimum number of screenshot events expected")
    args = parser.parse_args()

    events = load_trace_file(args.trace_file)

    print(f"\n{'='*60}")
    print(f"  Screenshot Trace Verification")
    print(f"{'='*60}")
    print(f"  File:   {args.trace_file}")
    print(f"  Events: {len(events)}")
    print(f"{'='*60}\n")

    errors = []

    # --- expect-none: should have zero events ---
    if args.expect_none:
        if len(events) > 0:
            errors.append(f"Expected 0 screenshot events but found {len(events)}")
            print_events(events)
        if not errors:
            print("  ✅ Correctly: no screenshot events in trace (none mode)")
            sys.exit(0)
        else:
            for e in errors:
                print(f"  ❌ {e}")
            sys.exit(1)

    # --- expect events present ---
    if len(events) == 0:
        print("  ❌ NO screenshot events found!")
        sys.exit(1)

    print_events(events)

    # Common validation
    errors.extend(validate_common(events))

    # --expect-path-only
    if args.expect_path_only:
        for ev in events:
            mode = ev["attrs"].get("rf.screenshot.mode", "")
            if mode == "embedded":
                errors.append(f"Expected path-only but found embedded on span '{ev['span']}'")
            if "rf.screenshot.data" in ev["attrs"]:
                errors.append(f"Expected no data but found base64 on span '{ev['span']}'")

    # --expect-fallback
    if args.expect_fallback:
        has_fallback = any(
            ev["attrs"].get("rf.screenshot.mode") == "path_fallback" for ev in events
        )
        if not has_fallback:
            errors.append("Expected at least one path_fallback event but found none")

    # --min-events
    if args.min_events and len(events) < args.min_events:
        errors.append(f"Expected at least {args.min_events} events but found {len(events)}")

    if errors:
        print(f"  ❌ Validation errors:")
        for e in errors:
            print(f"     - {e}")
        sys.exit(1)
    else:
        print(f"  ✅ All {len(events)} screenshot events are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
