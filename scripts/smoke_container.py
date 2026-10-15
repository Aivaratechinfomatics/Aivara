#!/usr/bin/env python3
"""
scripts/smoke_container.py — Container deployment smoke test script.

Validates that an Aivara container instance is up, healthy, and serving requests:
1. Pings Streamlit core health endpoint: http://<host>:<port>/_stcore/health
2. Verifies HTTP 200 status code and expected health response.
3. Performs root page fetch checking HTTP 200 availability.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request


def check_health(base_url: str, timeout: float = 5.0) -> bool:
    """Check the /_stcore/health endpoint."""
    health_url = f"{base_url.rstrip('/')}/_stcore/health"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "AivaraSmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="ignore").strip()
            if status == 200 and body == "ok":
                print(f"✅ Health check PASSED: {health_url} -> {status} (body='{body}')")
                return True
            print(f"⚠️ Health check unexpected response: {health_url} -> {status} (body='{body}')")
            return False
    except urllib.error.URLError as exc:
        print(f"❌ Health check FAILED: {health_url} -> {exc}")
        return False


def check_app_page(base_url: str, timeout: float = 5.0) -> bool:
    """Verify root page is reachable and serving HTTP 200."""
    try:
        req = urllib.request.Request(base_url, headers={"User-Agent": "AivaraSmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                print(f"✅ App root page reachable: {base_url} -> HTTP 200")
                return True
            print(f"⚠️ App root page status: {base_url} -> HTTP {resp.status}")
            return False
    except urllib.error.URLError as exc:
        print(f"❌ App root page unreachable: {base_url} -> {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Aivara Container Smoke Verification")
    parser.add_argument(
        "--url", default="http://localhost:8501", help="Base URL of Aivara application"
    )
    parser.add_argument("--retries", type=int, default=5, help="Number of retry attempts")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay in seconds between retries")
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="HTTP request timeout in seconds"
    )
    args = parser.parse_args()

    print(f"🚀 Starting Aivara container smoke test against {args.url} (retries={args.retries})...")

    for attempt in range(1, args.retries + 1):
        print(f"Attempt {attempt}/{args.retries}...")
        healthy = check_health(args.url, timeout=args.timeout)
        app_ok = check_app_page(args.url, timeout=args.timeout)

        if healthy and app_ok:
            print("🎉 Smoke verification SUCCEEDED! Application is healthy and responsive.")
            return 0

        if attempt < args.retries:
            time.sleep(args.delay)

    print("💥 Smoke verification FAILED: Container did not become healthy.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
