#!/usr/bin/env python3
"""
TP-Link Kasa Camera Stream Client (Reusable)

Connects to TP-Link Kasa cameras via their HTTPS streaming endpoint on port 19443.
Receives H.264 video via multipart HTTP, decodes, and displays live feed.

Usage:
    # Default camera (192.168.1.209)
    python tplink_camera.py

    # Specify camera IP
    python tplink_camera.py --ip 192.168.1.201

    # Specify credentials
    python tplink_camera.py --ip 192.168.1.210 --user me@email.com --password mypass

    # Save H.264 recording
    python tplink_camera.py --ip 192.168.1.209 --save --duration 30

    # Serve as web MJPEG feed
    python tplink_camera.py --ip 192.168.1.209 --web --port 5001
"""

import cv2
import numpy as np
import requests
import base64
import ssl
import threading
import time
import sys
import os
import argparse
import urllib3
import requests.adapters
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================
# Default Configuration
# ========================
DEFAULT_CAMERA_IP = "192.168.1.209"
DEFAULT_CAMERA_PORT = 19443
DEFAULT_USERNAME = "zhangyan612@gmail.com"
DEFAULT_PASSWORD = "zymeng90612"


# ========================
# TLS Adapter
# ========================
class TLSAdapter(requests.adapters.HTTPAdapter):
    """Custom TLS adapter for cameras using older/self-signed SSL."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("ALL:@SECLEVEL=0")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


# ========================
# Camera Client
# ========================
class TPLinkCamera:
    """
    TP-Link Kasa camera client.

    Connects to the camera's HTTPS endpoint, authenticates with Kasa
    credentials (base64-encoded password), and streams H.264 video.

    Args:
        ip: Camera IP address on local network
        port: HTTPS port (default 19443)
        username: TP-Link Kasa account email
        password: TP-Link Kasa account password
    """

    def __init__(self, ip, port=DEFAULT_CAMERA_PORT,
                 username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.password_b64 = base64.b64encode(password.encode()).decode()

        self.session = requests.Session()
        self.session.mount("https://", TLSAdapter())

        self.stream_url = (
            f"https://{self.ip}:{self.port}"
            f"/https/stream/mixed?video=h264&audio=g711&resolution=hd"
        )

        self._running = False
        self._latest_frame = None
        self._frame_lock = threading.Lock()

    # --------------------------------------------------
    # Connection helpers
    # --------------------------------------------------
    def test_connection(self):
        """Test TCP connectivity to the camera. Returns True if reachable."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((self.ip, self.port))
        sock.close()
        if result == 0:
            print(f"[+] Camera {self.ip}:{self.port} is reachable")
            return True
        else:
            print(f"[-] Camera {self.ip}:{self.port} is NOT reachable")
            return False

    def connect_stream(self):
        """Open the HTTPS stream. Returns a streaming requests.Response."""
        print(f"[*] Connecting to camera at {self.ip}:{self.port}...")

        try:
            response = self.session.get(
                self.stream_url,
                auth=(self.username, self.password_b64),
                verify=False,
                timeout=15,
                stream=True,
            )
        except requests.exceptions.ConnectionError as e:
            print(f"[-] Connection failed: {e}")
            return None
        except requests.exceptions.Timeout:
            print(f"[-] Connection timed out")
            return None

        if response.status_code == 200:
            ct = response.headers.get("Content-Type", "")
            print(f"[+] Connected! Content-Type: {ct}")
            return response

        print(f"[-] HTTP {response.status_code}")
        return None

    # --------------------------------------------------
    # Multipart H.264 parser
    # --------------------------------------------------
    @staticmethod
    def parse_h264_frames(response):
        """
        Generator that yields raw H.264 frame bytes from the camera's
        multipart/x-mixed-replace stream.
        """
        boundary = b"--data-boundary--"
        buffer = b""

        for chunk in response.iter_content(chunk_size=65536):
            buffer += chunk

            while True:
                idx = buffer.find(boundary)
                if idx == -1:
                    # Trim buffer to avoid unbounded growth
                    if len(buffer) > 200000:
                        buffer = buffer[-100000:]
                    break

                after = buffer[idx + len(boundary):]
                header_end = after.find(b"\r\n\r\n")
                if header_end == -1:
                    break  # need more data for headers

                headers_raw = after[:header_end].decode("latin-1")
                body_start = header_end + 4

                content_length = 0
                content_type = ""
                for line in headers_raw.split("\r\n"):
                    lo = line.lower().strip()
                    if lo.startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())
                    elif lo.startswith("content-type:"):
                        content_type = line.split(":", 1)[1].strip()

                if content_length == 0:
                    buffer = after[body_start:]
                    continue

                if len(after) < body_start + content_length:
                    break  # need more data for body

                frame_data = after[body_start : body_start + content_length]
                buffer = after[body_start + content_length:]

                if "h264" in content_type.lower() or "video" in content_type.lower():
                    yield frame_data

    # --------------------------------------------------
    # Live display (OpenCV window)
    # --------------------------------------------------
    def live_display(self, decode_interval=10):
        """
        Show a live OpenCV window with decoded H.264 frames.

        The camera streams H.264 via HTTP multipart.  We accumulate raw
        NAL units into a temp file and periodically ask OpenCV (FFMPEG
        backend) to decode the latest frame.

        Args:
            decode_interval: Decode after every N received frames.
                             Lower = fresher image but more CPU.
        """
        response = self.connect_stream()
        if not response:
            return

        self._running = True
        tmp_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_live_buffer.h264"
        )
        window_name = f"TP-Link Camera ({self.ip})"

        print(f"\n[*] Streaming live from {self.ip} ...")
        print(f"    Resolution: 1920x1080 (H.264)")
        print(f"    Decode every {decode_interval} frames")
        print(f"    Press 'q' in the window to quit\n")

        h264_buf = b""
        count = 0
        t0 = time.time()

        try:
            for frame_data in self.parse_h264_frames(response):
                if not self._running:
                    break

                h264_buf += frame_data
                count += 1

                if count % decode_interval == 0:
                    # Write accumulated H.264 to temp file
                    with open(tmp_path, "wb") as f:
                        f.write(h264_buf)

                    cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
                    if cap.isOpened():
                        last = None
                        while True:
                            ok, frm = cap.read()
                            if not ok:
                                break
                            last = frm
                        cap.release()

                        if last is not None:
                            with self._frame_lock:
                                self._latest_frame = last.copy()

                            # Add overlay
                            disp = last.copy()
                            elapsed = time.time() - t0
                            fps = count / elapsed if elapsed > 0 else 0
                            cv2.putText(
                                disp,
                                f"FPS: {fps:.1f} | Frames: {count}",
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0, 255, 0),
                                2,
                            )
                            cv2.putText(
                                disp,
                                f"{self.ip} | 1080p H.264",
                                (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 200, 255),
                                1,
                            )
                            cv2.imshow(window_name, disp)

                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                    # Reset buffer periodically to keep memory bounded
                    if count > 300:
                        h264_buf = b""
                        count = 0
                        t0 = time.time()

        except KeyboardInterrupt:
            print("\n[*] Interrupted")
        finally:
            self._running = False
            cv2.destroyAllWindows()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # --------------------------------------------------
    # Save H.264 recording
    # --------------------------------------------------
    def save_recording(self, output_path="recording.h264", duration_seconds=10):
        """
        Save raw H.264 stream to a file.

        Args:
            output_path: File path for the H.264 output.
            duration_seconds: How long to record.
        """
        response = self.connect_stream()
        if not response:
            return

        print(f"[*] Recording {duration_seconds}s to {output_path} ...")
        t0 = time.time()
        count = 0

        with open(output_path, "wb") as f:
            for frame_data in self.parse_h264_frames(response):
                f.write(frame_data)
                count += 1
                if count % 30 == 0:
                    elapsed = time.time() - t0
                    print(f"    {count} frames ({elapsed:.1f}s)")
                if time.time() - t0 >= duration_seconds:
                    break

        print(f"[+] Saved {count} frames to {output_path}")

    # --------------------------------------------------
    # Web MJPEG server (Flask)
    # --------------------------------------------------
    def serve_web(self, host="0.0.0.0", port=5001, decode_interval=10):
        """
        Start a Flask web server that converts the H.264 stream to MJPEG
        for browser viewing.

        Args:
            host: Bind address.
            port: HTTP port.
            decode_interval: Decode every N H.264 frames.
        """
        from flask import Flask, Response
        import socket

        app = Flask(__name__)
        camera = self

        # Start background decoder thread
        def _decoder():
            response = camera.connect_stream()
            if not response:
                return

            tmp_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "_web_buffer.h264"
            )
            h264_buf = b""
            count = 0

            for frame_data in camera.parse_h264_frames(response):
                h264_buf += frame_data
                count += 1

                if count % decode_interval == 0:
                    with open(tmp_path, "wb") as f:
                        f.write(h264_buf)

                    cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
                    if cap.isOpened():
                        last = None
                        while True:
                            ok, frm = cap.read()
                            if not ok:
                                break
                            last = frm
                        cap.release()

                        if last is not None:
                            with camera._frame_lock:
                                camera._latest_frame = last.copy()

                    if count > 300:
                        h264_buf = b""
                        count = 0

        threading.Thread(target=_decoder, daemon=True).start()

        def _mjpeg_gen():
            while True:
                with camera._frame_lock:
                    frame = camera._latest_frame
                if frame is not None:
                    ok, jpeg = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80]
                    )
                    if ok:
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n"
                            + jpeg.tobytes()
                            + b"\r\n"
                        )
                time.sleep(0.1)

        @app.route("/")
        def index():
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>TP-Link Camera — {camera.ip}</title>
            <style>
                body {{ background:#111827; color:#e5e7eb; font-family:system-ui;
                        display:flex; flex-direction:column; align-items:center;
                        padding:24px; }}
                h1 {{ color:#60a5fa; }}
                img {{ border:2px solid #3b82f6; border-radius:12px; max-width:100%; }}
                .info {{ color:#9ca3af; margin-top:8px; }}
            </style></head>
            <body>
                <h1>TP-Link Kasa Camera</h1>
                <p class="info">IP: {camera.ip} &mdash; 1080p H.264 &rarr; MJPEG</p>
                <img src="/video_feed" alt="Camera Feed">
            </body>
            </html>
            """

        @app.route("/video_feed")
        def video_feed():
            return Response(
                _mjpeg_gen(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

        # Detect local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        finally:
            s.close()

        print(f"\n[+] Web feed at  http://{local_ip}:{port}")
        print(f"    Camera IP:   {camera.ip}")
        print(f"    Press Ctrl+C to stop\n")
        app.run(host=host, port=port, threaded=True)


# ========================
# CLI
# ========================
def parse_args():
    p = argparse.ArgumentParser(
        description="TP-Link Kasa Camera Stream Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tplink_camera.py                          # live view, default camera
  python tplink_camera.py --ip 192.168.1.210       # live view, different camera
  python tplink_camera.py --ip 192.168.1.209 --save --duration 30
  python tplink_camera.py --ip 192.168.1.209 --web --port 5001
        """,
    )
    p.add_argument("--ip", default=DEFAULT_CAMERA_IP,
                   help=f"Camera IP address (default: {DEFAULT_CAMERA_IP})")
    p.add_argument("--port", type=int, default=DEFAULT_CAMERA_PORT,
                   help=f"Camera HTTPS port (default: {DEFAULT_CAMERA_PORT})")
    p.add_argument("--user", default=DEFAULT_USERNAME,
                   help="TP-Link Kasa account email")
    p.add_argument("--password", default=DEFAULT_PASSWORD,
                   help="TP-Link Kasa account password")
    p.add_argument("--save", action="store_true",
                   help="Save H.264 recording instead of live display")
    p.add_argument("--duration", type=int, default=10,
                   help="Recording duration in seconds (with --save)")
    p.add_argument("--output", default="recording.h264",
                   help="Output file path (with --save)")
    p.add_argument("--web", action="store_true",
                   help="Start web MJPEG server instead of OpenCV window")
    p.add_argument("--web-port", type=int, default=5001,
                   help="Web server port (with --web)")
    p.add_argument("--decode-interval", type=int, default=10,
                   help="Decode every N frames (lower = fresher, more CPU)")
    p.add_argument("--test", action="store_true",
                   help="Only test connectivity, do not stream")
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("  TP-Link Kasa Camera Client")
    print("=" * 60)
    print(f"  Camera : {args.ip}:{args.port}")
    print(f"  User   : {args.user}")
    print("=" * 60)

    cam = TPLinkCamera(
        ip=args.ip,
        port=args.port,
        username=args.user,
        password=args.password,
    )

    if args.test:
        cam.test_connection()
    elif args.save:
        cam.save_recording(output_path=args.output, duration_seconds=args.duration)
    elif args.web:
        cam.serve_web(port=args.web_port, decode_interval=args.decode_interval)
    else:
        cam.live_display(decode_interval=args.decode_interval)


if __name__ == "__main__":
    main()
