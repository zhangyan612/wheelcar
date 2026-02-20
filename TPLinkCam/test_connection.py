#!/usr/bin/env python3
"""Test connection to TP-Link EC60 camera on port 19443."""

import requests
import urllib3
import base64
import ssl
import requests.adapters
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings()

CAMERA_IP = "192.168.1.209"
KASA_USERNAME = "zhangyan612@gmail.com"
KASA_PASSWORD = "zymeng90612"


class TLSAdapter(requests.adapters.HTTPAdapter):
    """Custom TLS adapter to allow older SSL protocols."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def main():
    password_b64 = base64.b64encode(KASA_PASSWORD.encode()).decode()
    print(f"Password (b64): {password_b64}")

    session = requests.Session()
    session.mount("https://", TLSAdapter())

    # Test 1: Root URL (no auth)
    print("\n=== Test 1: Root URL ===")
    url = f"https://{CAMERA_IP}:19443/"
    try:
        r = session.get(url, verify=False, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        print(f"Body: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

    # Test 2: Stream URL with auth
    print("\n=== Test 2: Stream URL with auth ===")
    url2 = f"https://{CAMERA_IP}:19443/https/stream/mixed?video=h264&audio=g711&resolution=hd"
    try:
        r = session.get(url2, auth=(KASA_USERNAME, password_b64), verify=False, timeout=15, stream=True)
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")

        total = 0
        chunks = 0
        for chunk in r.iter_content(chunk_size=4096):
            total += len(chunk)
            chunks += 1
            if chunks == 1:
                print(f"First bytes (hex): {chunk[:80].hex()}")
                text_preview = chunk[:200].decode("utf-8", errors="replace")
                print(f"First bytes (text): {text_preview}")
            if total > 50000:
                print(f"Received {total} bytes in {chunks} chunks - stream is working!")
                break

        if total > 0:
            print(f"\nTotal received: {total} bytes")
        else:
            print("No data received")

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

    # Test 3: Try without audio parameter
    print("\n=== Test 3: Stream URL (video only) ===")
    url3 = f"https://{CAMERA_IP}:19443/https/stream/mixed?video=h264&resolution=hd"
    try:
        r = session.get(url3, auth=(KASA_USERNAME, password_b64), verify=False, timeout=15, stream=True)
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")

        total = 0
        for chunk in r.iter_content(chunk_size=4096):
            total += len(chunk)
            if total > 10000:
                print(f"Received {total} bytes - stream working!")
                break
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
