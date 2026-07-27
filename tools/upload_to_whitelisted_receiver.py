#!/usr/bin/env python3
"""Upload keyed files to a temporary, server-side whitelist receiver."""

from __future__ import annotations

import argparse
import mimetypes
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def post_form(endpoint: str, token: str, fields: dict[str, str], file_path: Path | None = None) -> tuple[int, str]:
    if file_path is None:
        body = urllib.parse.urlencode({"token": token, **fields}).encode()
        content_type = "application/x-www-form-urlencoded"
    else:
        boundary = f"----codex-{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        for name, value in {"token": token, **fields}.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(), b"\r\n",
            ])
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            file_path.read_bytes(), b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        body = b"".join(chunks)
        content_type = f"multipart/form-data; boundary={boundary}"

    request = urllib.request.Request(endpoint, data=body, method="POST", headers={"Content-Type": content_type})
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, context=context, timeout=60) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--item", action="append", default=[], metavar="KEY=PATH")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    for item in args.item:
        key, separator, raw_path = item.partition("=")
        if not separator:
            print(f"INVALID_ITEM:{item}", file=sys.stderr)
            return 2
        path = Path(raw_path)
        if not path.is_file():
            print(f"MISSING:{key}:{path}", file=sys.stderr)
            return 2
        status, text = post_form(args.endpoint, args.token, {"key": key}, path)
        if status != 200 or (text.strip() != "OK" and '"ok":true' not in text.replace(" ", "")):
            print(f"FAILED:{key}:{status}:{text.strip()}", file=sys.stderr)
            return 1
        print(f"OK:{key}")

    if args.cleanup:
        status, text = post_form(args.endpoint, args.token, {"cleanup": "1"})
        if status != 200 or (text.strip() != "CLEANED" and '"ok":true' not in text.replace(" ", "")):
            print(f"CLEANUP_FAILED:{status}:{text.strip()}", file=sys.stderr)
            return 1
        print("CLEANED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
