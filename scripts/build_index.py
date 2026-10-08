#!/usr/bin/env python3
"""Build a validated, deduplicated Mangayomi anime extension index."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "MangayomiCuratedIndex/1.0 (+https://github.com/mrandhawa14/mangayomi-curated-extensions)"
REQUIRED_FIELDS = ("id", "name", "baseUrl", "lang", "version", "sourceCodeUrl")


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    status: int | None
    detail: str
    compatibility_warnings: tuple[str, ...] = ()


def fetch_bytes(url: str, timeout: float, limit: int = 1_000_000) -> tuple[int, bytes]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Range": f"bytes=0-{limit - 1}",
        },
    )
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            return response.status, response.read(limit)
    except HTTPError as error:
        return error.code, error.read(min(limit, 4096))


def load_remote_json(url: str, timeout: float) -> list[dict[str, Any]]:
    status, body = fetch_bytes(url, timeout)
    if status not in (200, 206):
        raise RuntimeError(f"HTTP {status}")
    value = json.loads(body.decode("utf-8-sig"))
    if not isinstance(value, list):
        raise ValueError("index root must be a JSON array")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError("every index entry must be an object")
    return value


def check_source(url: str, timeout: float) -> CheckResult:
    try:
        status, body = fetch_bytes(url, timeout)
    except (URLError, TimeoutError, OSError) as error:
        return CheckResult(False, None, str(error))
    text = body.decode("utf-8", errors="replace").lstrip()
    looks_like_html = text.lower().startswith(("<!doctype html", "<html"))
    ok = status in (200, 206) and len(text) >= 20 and not looks_like_html
    detail = "source file loaded" if ok else "empty, missing, or HTML response"
    return CheckResult(ok, status, detail, source_compatibility_warnings(text) if ok else ())


def source_compatibility_warnings(text: str) -> tuple[str, ...]:
    warnings: list[str] = []
    code = re.sub(r"/\*.*?\*/|//[^\r\n]*", "", text, flags=re.DOTALL)
    if re.search(r"\.replace\s*\(\s*queryParameters\s*:", code, flags=re.DOTALL):
        warnings.append(
            "Uses Uri.replace(queryParameters: ...), which fails with bridged maps in Mangayomi 0.8.9"
        )
    if re.search(r"https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?", text, flags=re.IGNORECASE):
        warnings.append(
            "References a loopback HTTP service; mobile users need that service on the same device"
        )
    return tuple(warnings)


def check_site(url: str, timeout: float, has_cloudflare: bool) -> CheckResult:
    try:
        status, _ = fetch_bytes(url, timeout, limit=4096)
    except (URLError, TimeoutError, OSError) as error:
        return CheckResult(False, None, str(error))
    if 200 <= status < 400:
        return CheckResult(True, status, "site responded")
    if status == 403 and has_cloudflare:
        return CheckResult(True, status, "Cloudflare challenge detected")
    return CheckResult(False, status, f"HTTP {status}")


def normalized_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def version_key(value: Any) -> tuple[int, ...]:
    numbers = [int(part) for part in re.findall(r"\d+", str(value))]
    return tuple(numbers or [0])


def exclusion_for(entry: dict[str, Any], exclusions: list[dict[str, str]]) -> str | None:
    for rule in exclusions:
        if normalized_name(rule.get("name", "")) != normalized_name(str(entry.get("name", ""))):
            continue
        if rule.get("lang") and rule["lang"].casefold() != str(entry.get("lang", "")).casefold():
            continue
        return rule.get("reason", "manually excluded")
    return None


def override_key(entry: dict[str, Any]) -> tuple[str, str]:
    return normalized_name(str(entry.get("name", ""))), str(entry.get("lang", "")).casefold()


def apply_overrides(entry: dict[str, Any], overrides: list[dict[str, Any]]) -> None:
    for rule in overrides:
        if normalized_name(str(rule.get("name", ""))) != normalized_name(str(entry.get("name", ""))):
            continue
        if rule.get("lang") and str(rule["lang"]).casefold() != str(entry.get("lang", "")).casefold():
            continue
        entry.update(rule.get("set", {}))


def validate_shape(entry: dict[str, Any]) -> str | None:
    missing = [field for field in REQUIRED_FIELDS if entry.get(field) in (None, "")]
    if missing:
        return "missing required field(s): " + ", ".join(missing)
    if not isinstance(entry["id"], int):
        return "id must be an integer"
    if not str(entry["baseUrl"]).startswith(("http://", "https://")):
        return "baseUrl must be HTTP(S)"
    if not str(entry["sourceCodeUrl"]).startswith(("http://", "https://")):
        return "sourceCodeUrl must be HTTP(S)"
    return None


def build(
    config_path: Path,
    selection_path: Path,
    output_path: Path,
    report_path: Path,
    timeout: float,
    workers: int,
    minimum_selected: int,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    exclusions = selection.get("exclude", [])
    overrides = selection.get("overrides", [])
    allowed_unreachable = {
        (normalized_name(item["name"]), item.get("lang", "").casefold())
        for item in selection.get("allowUnreachable", [])
    }

    entries: list[dict[str, Any]] = []
    feeds: list[dict[str, Any]] = []
    for priority, source in enumerate(config["sources"]):
        try:
            remote_entries = load_remote_json(source["indexUrl"], timeout)
            feeds.append({"name": source["name"], "ok": True, "entries": len(remote_entries)})
        except (ValueError, RuntimeError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            feeds.append({"name": source["name"], "ok": False, "error": str(error)})
            continue
        for remote_entry in remote_entries:
            entry = dict(remote_entry)
            apply_overrides(entry, overrides)
            entry["_origin"] = source["name"]
            entry["_priority"] = priority
            entries.append(entry)

    for added in selection.get("add", []):
        entry = dict(added)
        apply_overrides(entry, overrides)
        entry["_origin"] = "Curated addition"
        entry["_priority"] = -1
        entries.append(entry)

    loaded_feeds = sum(1 for feed in feeds if feed["ok"])
    if loaded_feeds != len(config["sources"]):
        raise RuntimeError(f"only {loaded_feeds} of {len(config['sources'])} upstream feeds loaded")

    source_urls = sorted({str(entry.get("sourceCodeUrl", "")) for entry in entries if entry.get("sourceCodeUrl")})
    site_inputs = {
        str(entry.get("baseUrl", "")): bool(entry.get("hasCloudflare", False))
        for entry in entries
        if entry.get("baseUrl")
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        source_checks = dict(
            zip(source_urls, executor.map(lambda url: check_source(url, timeout), source_urls))
        )
        site_urls = sorted(site_inputs)
        site_checks = dict(
            zip(
                site_urls,
                executor.map(lambda url: check_site(url, timeout, site_inputs[url]), site_urls),
            )
        )

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for entry in entries:
        reason = validate_shape(entry)
        if not reason and entry.get("isActive") is False:
            reason = "upstream marked inactive"
        if not reason:
            reason = exclusion_for(entry, exclusions)
        source_check = source_checks.get(str(entry.get("sourceCodeUrl", "")))
        site_check = site_checks.get(str(entry.get("baseUrl", "")))
        override = override_key(entry) in allowed_unreachable
        if not reason and (not source_check or not source_check.ok):
            reason = "extension source file did not load"
        if not reason and not override and (not site_check or not site_check.ok):
            reason = "website did not respond successfully"

        audit = {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "lang": entry.get("lang"),
            "version": entry.get("version"),
            "origin": entry.get("_origin"),
            "baseUrl": entry.get("baseUrl"),
            "sourceCodeUrl": entry.get("sourceCodeUrl"),
            "siteStatus": site_check.status if site_check else None,
            "sourceStatus": source_check.status if source_check else None,
            "compatibilityWarnings": list(source_check.compatibility_warnings)
            if source_check
            else [],
        }
        if str(entry.get("baseUrl", "")).startswith("http://"):
            audit["compatibilityWarnings"].append(
                "Uses an unencrypted HTTP base URL, which may be blocked by platform network security"
            )
        if reason:
            audit["reason"] = reason
            rejected.append(audit)
        else:
            candidates.append({"entry": entry, "audit": audit})

    candidates.sort(
        key=lambda item: (
            version_key(item["entry"].get("version")),
            -int(item["entry"].get("_priority", 0)),
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    duplicate_rejections: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    seen_names: set[tuple[str, str]] = set()
    for item in candidates:
        entry = item["entry"]
        name_key = override_key(entry)
        entry_id = entry["id"]
        if entry_id in seen_ids or name_key in seen_names:
            duplicate = dict(item["audit"])
            duplicate["reason"] = "lower-priority duplicate"
            duplicate_rejections.append(duplicate)
            continue
        seen_ids.add(entry_id)
        seen_names.add(name_key)
        clean_entry = {key: value for key, value in entry.items() if not key.startswith("_")}
        selected.append(clean_entry)

    selected.sort(key=lambda entry: (str(entry.get("lang", "")), str(entry.get("name", "")).casefold()))
    rejected.extend(duplicate_rejections)
    rejected.sort(key=lambda entry: (str(entry.get("reason", "")), str(entry.get("name", ""))))

    if len(selected) < minimum_selected:
        raise RuntimeError(
            f"selected source count {len(selected)} is below safety minimum {minimum_selected}"
        )

    output_path.write_text(json.dumps(selected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    selected_audits = [
        next(
            item["audit"]
            for item in candidates
            if item["entry"]["id"] == entry["id"]
            and override_key(item["entry"]) == override_key(entry)
        )
        for entry in selected
    ]
    report = {
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "feedsConfigured": len(config["sources"]),
            "feedsLoaded": sum(1 for feed in feeds if feed["ok"]),
            "entriesSeen": len(entries),
            "entriesSelected": len(selected),
            "entriesRejected": len(rejected),
            "compatibilityWarnings": sum(
                len(item["compatibilityWarnings"]) for item in selected_audits
            ),
        },
        "feeds": feeds,
        "selected": selected_audits,
        "rejected": rejected,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "sources.json")
    parser.add_argument("--selection", type=Path, default=root / "selection.json")
    parser.add_argument("--output", type=Path, default=root / "anime_index.json")
    parser.add_argument("--report", type=Path, default=root / "health_report.json")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--minimum-selected", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build(
            args.config,
            args.selection,
            args.output,
            args.report,
            args.timeout,
            args.workers,
            args.minimum_selected,
        )
    except (KeyError, ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], indent=2))
    return 0 if report["summary"]["feedsLoaded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
