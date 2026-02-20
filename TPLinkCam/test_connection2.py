#!/usr/bin/env python3
"""Test connection and log results to a file for readability."""

import requests
import urllib3
import base64
import ssl
import requests.adapters
from urllib3.util.ssl_ import create_urllib3_context
import sys

urllib3.disable_warnings()

CAMERA_IP = "192.168.1.209"
KASA_USERNAME = "zhangyan612@gmail.com"
KASA_PASSWORD = "zymeng90612"


class TLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def main():
    password_b64 = base64.b64encode(KASA_PASSWORD.encode()).decode()

    session = requests.Session()
    session.mount("https://", TLSAdapter())

    log = open("connection_log.txt", "w")

    def log_print(msg):
        print(msg)
        log.write(msg + "\n")
        log.flush()

    # Test stream URL with auth
    log_print("=== Stream URL with auth ===")
    url = f"https://{CAMERA_IP}:19443/https/stream/mixed?video=h264&audio=g711&resolution=hd"
    log_print(f"URL: {url}")

    try:
        r = session.get(url, auth=(KASA_USERNAME, password_b64), verify=False, timeout=15, stream=True)
        log_print(f"Status: {r.status_code}")
        for k, v in r.headers.items():
            log_print(f"  Header: {k} = {v}")

        total = 0
        chunks = 0
        for chunk in r.iter_content(chunk_size=4096):
            total += len(chunk)
            chunks += 1
            if chunks <= 3:
                log_print(f"Chunk {chunks}: {len(chunk)} bytes")
                log_print(f"  Hex: {chunk[:100].hex()}")
                try:
                    text = chunk[:300].decode("latin-1")
                    log_print(f"  Text: {repr(text)}")
                except:
                    pass
            if total > 100000:
                log_print(f"Received {total} bytes in {chunks} chunks - STREAM IS WORKING!")
                break

        log_print(f"\nTotal received: {total} bytes in {chunks} chunks")

    except Exception as e:
        log_print(f"Error: {type(e).__name__}: {e}")

    log.close()
    print("\nLog saved to connection_log.txt")


if __name__ == "__main__":
    main()
