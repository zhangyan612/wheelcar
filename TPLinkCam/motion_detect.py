#!/usr/bin/env python3
"""
TP-Link Kasa Camera — Motion Detection & Clip Saver

Connects to one or more TP-Link Kasa cameras, runs background motion
detection, and saves detected motion as JPEG frames + short video clips.

Latency is NOT an issue here — we just want to capture & save every
motion event, not view them in real time.

Usage:
    # Monitor both cameras with defaults
    python motion_detect.py

    # Monitor a single camera
    python motion_detect.py --cameras 192.168.1.209

    # Custom sensitivity
    python motion_detect.py --threshold 30 --min-area 3000

    # Custom output directory
    python motion_detect.py --output D:/SecurityFootage
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
import datetime
import urllib3
import requests.adapters
from collections import deque
import queue
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================
# Default Configuration
# ========================
DEFAULT_CAMERAS = ["192.168.1.209", "192.168.1.201"]
DEFAULT_PORT = 19443
DEFAULT_USERNAME = "zhangyan612@gmail.com"
DEFAULT_PASSWORD = "zymeng90612"

# Motion detection settings
DEFAULT_THRESHOLD = 25       # Pixel difference threshold (0-255)
DEFAULT_MIN_AREA = 1500      # Lowered to be more sensitive to end-of-event motion
DEFAULT_COOLDOWN = 5         # Seconds of quiet before finalising a clip
DEFAULT_PRE_RECORD = 5       # Seconds of footage to keep BEFORE motion
DEFAULT_POST_RECORD = 3      # Reduced to 3s to avoid large files and potential overhead
DEFAULT_DECODE_INTERVAL = 10 # Decode every N H.264 frames (~3 decoded fps)


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
# H.264 Stream Parser
# ========================
def connect_camera_stream(ip, port, username, password):
    """Connect to a TP-Link camera and return the streaming response."""
    password_b64 = base64.b64encode(password.encode()).decode()
    session = requests.Session()
    session.mount("https://", TLSAdapter())

    url = (
        f"https://{ip}:{port}"
        f"/https/stream/mixed?video=h264&audio=g711&resolution=hd"
    )

    try:
        response = session.get(
            url,
            auth=(username, password_b64),
            verify=False,
            timeout=15,
            stream=True,
        )
        if response.status_code == 200:
            return response
        else:
            print(f"  [{ip}] HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  [{ip}] Connection error: {e}")
        return None


def parse_h264_frames(response):
    """Generator yielding raw H.264 frame bytes from multipart stream."""
    boundary = b"--data-boundary--"
    buffer = b""

    for chunk in response.iter_content(chunk_size=65536):
        buffer += chunk

        while True:
            idx = buffer.find(boundary)
            if idx == -1:
                if len(buffer) > 200000:
                    buffer = buffer[-100000:]
                break

            after = buffer[idx + len(boundary):]
            header_end = after.find(b"\r\n\r\n")
            if header_end == -1:
                break

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
                break

            frame_data = after[body_start : body_start + content_length]
            buffer = after[body_start + content_length:]

            if "h264" in content_type.lower() or "video" in content_type.lower():
                yield frame_data


def decode_latest_frame(h264_data, tmp_path):
    """
    Write accumulated H.264 data to a temp file and decode the last frame.
    Returns the decoded frame (numpy array) or None.
    """
    with open(tmp_path, "wb") as f:
        f.write(h264_data)

    cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return None

    last_frame = None
    while True:
        ok, frm = cap.read()
        if not ok:
            break
        last_frame = frm
    cap.release()
    return last_frame


# ========================
# Motion Detector
# ========================
class MotionDetector:
    """
    Simple frame-differencing motion detector.
    Compares consecutive decoded frames and triggers when enough
    pixels have changed beyond a threshold.
    """

    def __init__(self, threshold=DEFAULT_THRESHOLD, min_area=DEFAULT_MIN_AREA):
        self.threshold = threshold
        self.min_area = min_area
        self.prev_gray = None

    def detect(self, frame):
        """
        Check for motion between this frame and the previous one.

        Returns:
            (motion_detected: bool, motion_area: int, diff_frame: ndarray)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return False, 0, None

        delta = cv2.absdiff(self.prev_gray, gray)
        thresh = cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        total_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area > self.min_area:
                total_area += area

        self.prev_gray = gray
        return total_area > 0, total_area, thresh


# ========================
# Per-Camera Monitor
# ========================
class CameraMonitor(threading.Thread):
    """
    Monitors a single camera in a background thread.
    Decodes H.264 frames, runs motion detection, and saves clips.

    Uses a **ring buffer** so that when motion triggers, the clip
    already contains `pre_record` seconds of footage leading up to
    the event.  After motion stops, recording continues for
    `post_record` seconds so the clip has context on both sides.
    """

    def __init__(self, ip, output_dir, port=DEFAULT_PORT,
                 username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD,
                 threshold=DEFAULT_THRESHOLD, min_area=DEFAULT_MIN_AREA,
                 cooldown=DEFAULT_COOLDOWN, decode_interval=DEFAULT_DECODE_INTERVAL,
                 pre_record=DEFAULT_PRE_RECORD, post_record=DEFAULT_POST_RECORD):
        super().__init__(daemon=True)
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.output_dir = output_dir
        self.threshold = threshold
        self.min_area = min_area
        self.cooldown = cooldown
        self.decode_interval = decode_interval
        self.pre_record = pre_record
        self.post_record = post_record

        self.running = False
        self.frames_received = 0
        self.frames_decoded = 0
        self.motions_saved = 0
        self.last_motion_time = 0
        self.status = "starting"

        # Create output directory for this camera
        cam_dir = os.path.join(output_dir, ip.replace(".", "_"))
        os.makedirs(cam_dir, exist_ok=True)
        self.cam_dir = cam_dir

        # Temp file for H.264 decoding
        self.tmp_path = os.path.join(cam_dir, "_decode_buffer.h264")

        # Estimated decoded FPS  (camera ~30 raw fps / decode_interval)
        self._decoded_fps = max(1.0, 30.0 / decode_interval)

    def run(self):
        """Main loop: starts receiver and processor threads."""
        self.running = True
        self.frame_queue = queue.Queue(maxsize=2000)

        # Start the processing thread
        processor = threading.Thread(target=self._processor_loop, daemon=True)
        processor.start()

        # Receiver loop (runs in this thread)
        while self.running:
            try:
                self._receiver_loop()
            except Exception as e:
                self.status = f"error: {e}"
                print(f"  [{self.ip}] Receiver Error: {e}")

            if self.running:
                self.status = "reconnecting"
                print(f"  [{self.ip}] Reconnecting in 10s...")
                time.sleep(10)

    def _receiver_loop(self):
        """Dedicated loop for pulling data from the network as fast as possible."""
        self.status = "connecting"
        print(f"  [{self.ip}] Connecting...")

        response = connect_camera_stream(
            self.ip, self.port, self.username, self.password
        )
        if not response:
            self.status = "connection failed"
            return

        self.status = "streaming"
        print(f"  [{self.ip}] Connected! Receiver started.")

        for h264_frame in parse_h264_frames(response):
            if not self.running:
                break
            
            try:
                # Use a small timeout so we can check self.running regularly
                self.frame_queue.put(h264_frame, timeout=0.1)
                self.frames_received += 1
            except queue.Full:
                # If queue is full, we are lagging significantly. 
                # Drop frames to keep the network connection alive?
                # Actually, dropping H.264 frames mid-stream causes corruption.
                # But blocking the network causes disconnect.
                # We'll wait a bit and try again, but if it stays full, we're in trouble.
                pass

    def _processor_loop(self):
        """Dedicated loop for decoding, detecting motion, and saving clips."""
        detector = MotionDetector(
            threshold=self.threshold, min_area=self.min_area
        )
        
        # --- Decoder buffer management ---
        h264_buf = b""
        h264_header = b""  # Store SPS/PPS so resets don't break decoding
        h264_count = 0

        # --- Ring buffer: always keeps the last `pre_record` seconds ---
        ring_size = max(10, int(self._decoded_fps * self.pre_record))
        ring_buffer = deque(maxlen=ring_size)

        # --- Recording state ---
        recording = False           # currently saving a clip?
        motion_clip_frames = []     # frames collected for current clip
        last_motion_at = 0.0        # timestamp of most recent motion frame
        clip_start_time = None      # when recording started (for logging)

        print(f"  [{self.ip}] Processor started. Pre-record: {self.pre_record}s | Post-record: {self.post_record}s")

        while self.running:
            try:
                # Get frame from queue
                try:
                    h264_frame = self.frame_queue.get(timeout=1.0)
                except queue.Empty:
                    # If we are recording and no frames arrive for a while, finalize the clip
                    if recording and (time.time() - last_motion_at >= self.post_record):
                        print(f"  [{self.ip}] Finalizing clip due to inactivity/disconnect.")
                        total_seconds = time.time() - clip_start_time
                        self._save_motion_event(motion_clip_frames, total_seconds)
                        recording = False
                        motion_clip_frames = []
                        h264_buf = h264_header
                        h264_count = 0
                    continue

                # Capture SPS/PPS header
                if not h264_header and len(h264_frame) > 4:
                    nal_type = h264_frame[4] & 0x1F
                    if nal_type in (7, 8):
                        h264_header += h264_frame

                h264_buf += h264_frame
                h264_count += 1

                # Reset buffer periodically
                if h264_count > 300 and not recording:
                    h264_buf = h264_header + h264_frame
                    h264_count = 1

                # Decode periodically
                if h264_count % self.decode_interval != 0:
                    continue

                frame = decode_latest_frame(h264_buf, self.tmp_path)
                if frame is None:
                    continue

                self.frames_decoded += 1
                now = time.time()

                # Always push into ring buffer
                ring_buffer.append((now, frame.copy()))

                # Run motion detection
                motion, area, _ = detector.detect(frame)

                if motion:
                    self.last_motion_time = now
                    last_motion_at = now

                    if not recording:
                        recording = True
                        clip_start_time = now
                        motion_clip_frames = [f.copy() for (_, f) in ring_buffer]
                        print(
                            f"  [{self.ip}] >>> STARTING CLIP: Motion detected (Area={area:.0f}) "
                            f"at {datetime.datetime.now():%H:%M:%S}"
                        )
                    else:
                        motion_clip_frames.append(frame.copy())

                elif recording:
                    motion_clip_frames.append(frame.copy())
                    silence_duration = now - last_motion_at
                    if silence_duration >= self.post_record:
                        total_seconds = now - clip_start_time
                        self._save_motion_event(motion_clip_frames, total_seconds)
                        recording = False
                        motion_clip_frames = []
                        h264_buf = h264_header
                        h264_count = 0
                
                self.frame_queue.task_done()
            except Exception as e:
                print(f"  [{self.ip}] Processor loop error: {e}")
                time.sleep(1)

    def _save_motion_event(self, frames, clip_duration=0):
        """
        Save collected motion frames as:
          - A JPEG snapshot (first frame with actual motion = after pre-buffer)
          - An AVI video clip of all frames
        """
        if not frames:
            return

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        date_dir = os.path.join(self.cam_dir, now.strftime("%Y-%m-%d"))
        os.makedirs(date_dir, exist_ok=True)

        # Snapshot — pick the frame roughly at the pre-buffer boundary
        snap_idx = min(int(self._decoded_fps * self.pre_record), len(frames) - 1)
        jpg_path = os.path.join(date_dir, f"motion_{timestamp}.jpg")
        cv2.imwrite(jpg_path, frames[snap_idx], [cv2.IMWRITE_JPEG_QUALITY, 90])

        # Video clip
        h, w = frames[0].shape[:2]
        clip_path = os.path.join(date_dir, f"clip_{timestamp}.avi")
        writer = cv2.VideoWriter(
            clip_path,
            cv2.VideoWriter_fourcc(*"XVID"),
            self._decoded_fps,
            (w, h),
        )
        for f in frames:
            writer.write(f)
        writer.release()

        self.motions_saved += 1
        est_seconds = len(frames) / self._decoded_fps
        print(
            f"  [{self.ip}] Saved clip: {len(frames)} frames "
            f"(~{est_seconds:.1f}s) -> {clip_path}"
        )

    def stop(self):
        self.running = False


# ========================
# Main Monitor Manager
# ========================
def status_printer(monitors, interval=30):
    """Periodically print status of all camera monitors."""
    while True:
        time.sleep(interval)
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\n--- Status at {now} ---")
        for m in monitors:
            elapsed = time.time() - m.last_motion_time if m.last_motion_time else 0
            last_motion = (
                f"{elapsed:.0f}s ago" if m.last_motion_time else "none"
            )
            print(
                f"  [{m.ip}] {m.status} | "
                f"recv={m.frames_received} decoded={m.frames_decoded} | "
                f"motions_saved={m.motions_saved} | "
                f"last_motion={last_motion}"
            )
        print()


def parse_args():
    p = argparse.ArgumentParser(
        description="TP-Link Camera Motion Detection & Clip Saver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python motion_detect.py
  python motion_detect.py --cameras 192.168.1.209 192.168.1.201
  python motion_detect.py --threshold 20 --min-area 1500
  python motion_detect.py --pre-record 10 --post-record 15
  python motion_detect.py --output D:/SecurityFootage
        """,
    )
    p.add_argument(
        "--cameras", nargs="+", default=DEFAULT_CAMERAS,
        help=f"Camera IP addresses (default: {DEFAULT_CAMERAS})",
    )
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--user", default=DEFAULT_USERNAME)
    p.add_argument("--password", default=DEFAULT_PASSWORD)
    p.add_argument(
        "--output", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion_clips"),
        help="Root directory for saved clips (default: ./motion_clips)",
    )
    p.add_argument(
        "--threshold", type=int, default=DEFAULT_THRESHOLD,
        help=f"Pixel diff threshold 0-255 (default: {DEFAULT_THRESHOLD})",
    )
    p.add_argument(
        "--min-area", type=int, default=DEFAULT_MIN_AREA,
        help=f"Minimum contour area in pixels (default: {DEFAULT_MIN_AREA})",
    )
    p.add_argument(
        "--cooldown", type=int, default=DEFAULT_COOLDOWN,
        help=f"Seconds of quiet before finalizing clip (default: {DEFAULT_COOLDOWN})",
    )
    p.add_argument(
        "--pre-record", type=int, default=DEFAULT_PRE_RECORD,
        help=f"Seconds of footage to keep BEFORE motion (default: {DEFAULT_PRE_RECORD})",
    )
    p.add_argument(
        "--post-record", type=int, default=DEFAULT_POST_RECORD,
        help=f"Seconds to keep recording AFTER motion stops (default: {DEFAULT_POST_RECORD})",
    )
    p.add_argument(
        "--decode-interval", type=int, default=DEFAULT_DECODE_INTERVAL,
        help=f"Decode every N H.264 frames (default: {DEFAULT_DECODE_INTERVAL})",
    )
    p.add_argument(
        "--status-interval", type=int, default=60,
        help="Print status every N seconds (default: 60)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("  TP-Link Camera — Motion Detection Monitor")
    print("=" * 60)
    print(f"  Cameras     : {', '.join(args.cameras)}")
    print(f"  Output dir  : {args.output}")
    print(f"  Threshold   : {args.threshold}")
    print(f"  Min area    : {args.min_area}")
    print(f"  Pre-record  : {args.pre_record}s")
    print(f"  Post-record : {args.post_record}s")
    print(f"  Decode every: {args.decode_interval} frames")
    print("=" * 60)

    os.makedirs(args.output, exist_ok=True)

    # Start a monitor thread for each camera
    monitors = []
    for ip in args.cameras:
        m = CameraMonitor(
            ip=ip,
            output_dir=args.output,
            port=args.port,
            username=args.user,
            password=args.password,
            threshold=args.threshold,
            min_area=args.min_area,
            cooldown=args.cooldown,
            decode_interval=args.decode_interval,
            pre_record=args.pre_record,
            post_record=args.post_record,
        )
        monitors.append(m)
        m.start()
        print(f"  Started monitor for {ip}")
        time.sleep(2)  # Stagger connections

    # Status printer thread
    status_thread = threading.Thread(
        target=status_printer, args=(monitors, args.status_interval), daemon=True
    )
    status_thread.start()

    print(f"\n[+] Monitoring {len(monitors)} cameras. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping monitors...")
        for m in monitors:
            m.stop()
        time.sleep(2)
        print("[+] Done.")


if __name__ == "__main__":
    main()
