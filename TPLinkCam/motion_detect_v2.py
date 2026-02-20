#!/usr/bin/env python3
"""
TP-Link Kasa Camera — Motion Detection & Object Tracking (V2)

Identifies motion using pixel diff, then confirms with AI (torchvision SSD)
to filter for People and Animals. This significantly reduces false positives
from wind, trees, and small lighting changes.

Features:
- Dual-thread architecture (Receiver/Processor)
- Torchvision-based Object Detection (Person, Dog, Cat)
- Higher sensitivity thresholds for outdoor/noisy environments
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
import queue
from collections import deque
from urllib3.util.ssl_ import create_urllib3_context

# Optional AI imports
try:
    import torch
    import torchvision
    from torchvision.models.detection import ssdlite320_mobilenet_v3_large, SSDLite320_MobileNet_V3_Large_Weights
    HAS_AI = True
except ImportError:
    HAS_AI = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================
# Default Configuration
# ========================
DEFAULT_CAMERAS = ["192.168.1.209", "192.168.1.201"]
DEFAULT_PORT = 19443
DEFAULT_USERNAME = "zhangyan612@gmail.com"
DEFAULT_PASSWORD = "zymeng90612"

# Motion detection settings (Increased for V2)
DEFAULT_THRESHOLD = 35       # Higher pixel difference threshold
DEFAULT_MIN_AREA = 5000      # Larger area required for motion
DEFAULT_COOLDOWN = 5         # Seconds of quiet before finalising a clip
DEFAULT_PRE_RECORD = 5       # Seconds of footage to keep BEFORE motion
DEFAULT_POST_RECORD = 3      # Seconds of footage to keep AFTER motion
DEFAULT_DECODE_INTERVAL = 15 # Decode every N H.264 frames (~2 decoded fps)

# AI Object Filtering
DEFAULT_AI_CLASSES = [1, 17, 18] # 1: person, 17: cat, 18: dog (COCO indices)
DEFAULT_AI_THRESHOLD = 0.45      # Minimum confidence for AI detection


# ========================
# TLS Adapter
# ========================
class TLSAdapter(requests.adapters.HTTPAdapter):
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
# AI Object Detector
# ========================
class ObjectDetector:
    """
    Lightweight SSD-Mobilenet detector to filter motion events.
    """
    def __init__(self, confidence=DEFAULT_AI_THRESHOLD, classes=DEFAULT_AI_CLASSES):
        self.confidence = confidence
        self.classes = classes
        
        if HAS_AI:
            print("[*] Loading AI models (Torch + SSD-Mobilenet)...")
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = ssdlite320_mobilenet_v3_large(weights=SSDLite320_MobileNet_V3_Large_Weights.DEFAULT)
            self.model.to(self.device)
            self.model.eval()
            print(f"[*] AI ready on {self.device}")
        else:
            print("[!] AI imports failed. Falling back to basic motion detection.")

    def detect_relevant_object(self, frame):
        """Returns True if a relevant object (Person/Animal) is found."""
        if not HAS_AI:
            return True # If AI is missing, we don't filter
        
        # Preprocess
        img_tensor = torchvision.transforms.functional.to_tensor(frame).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            predictions = self.model(img_tensor)[0]
        
        # Filter by class and confidence
        for i in range(len(predictions['labels'])):
            label = int(predictions['labels'][i])
            score = float(predictions['scores'][i])
            
            if score >= self.confidence and label in self.classes:
                return True, label, score
                
        return False, None, 0


# ========================
# Motion Detector
# ========================
class MotionDetector:
    def __init__(self, threshold=DEFAULT_THRESHOLD, min_area=DEFAULT_MIN_AREA):
        self.threshold = threshold
        self.min_area = min_area
        self.prev_gray = None

    def detect(self, frame):
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
    def __init__(self, ip, output_dir, port=DEFAULT_PORT,
                 username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD,
                 threshold=DEFAULT_THRESHOLD, min_area=DEFAULT_MIN_AREA,
                 cooldown=DEFAULT_COOLDOWN, decode_interval=DEFAULT_DECODE_INTERVAL,
                 pre_record=DEFAULT_PRE_RECORD, post_record=DEFAULT_POST_RECORD,
                 use_ai=True):
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
        self.use_ai = use_ai

        self.running = False
        self.frames_received = 0
        self.frames_decoded = 0
        self.motions_saved = 0
        self.last_motion_time = 0
        self.status = "starting"

        cam_dir = os.path.join(output_dir, ip.replace(".", "_"))
        os.makedirs(cam_dir, exist_ok=True)
        self.cam_dir = cam_dir
        self.tmp_path = os.path.join(cam_dir, f"_decode_{ip.replace('.','_')}.h264")

        self._decoded_fps = max(1.0, 30.0 / decode_interval)
        self.frame_queue = queue.Queue(maxsize=1000)

    def run(self):
        self.running = True
        
        # Start the processing thread
        processor = threading.Thread(target=self._processor_loop, daemon=True)
        processor.start()

        while self.running:
            try:
                self._receiver_loop()
            except Exception as e:
                self.status = f"error: {e}"
                print(f"  [{self.ip}] Receiver Error: {e}")

            if self.running:
                self.status = "reconnecting"
                time.sleep(10)

    def _receiver_loop(self):
        self.status = "connecting"
        response = connect_camera_stream(self.ip, self.port, self.username, self.password)
        if not response:
            self.status = "failed"
            return

        self.status = "streaming"
        for h264_frame in parse_h264_frames(response):
            if not self.running: break
            try:
                self.frame_queue.put(h264_frame, timeout=0.1)
                self.frames_received += 1
            except queue.Full:
                pass

    def _processor_loop(self):
        detector = MotionDetector(threshold=self.threshold, min_area=self.min_area)
        ai_detector = ObjectDetector() if self.use_ai else None

        h264_buf = b""
        h264_header = b""
        h264_count = 0
        
        ring_size = max(10, int(self._decoded_fps * self.pre_record))
        ring_buffer = deque(maxlen=ring_size)

        recording = False
        ai_confirmed = False
        motion_clip_frames = []
        last_motion_at = 0.0
        clip_start_time = None

        print(f"  [{self.ip}] Processor started (AI={self.use_ai})")

        while self.running:
            try:
                try:
                    h264_frame = self.frame_queue.get(timeout=1.0)
                except queue.Empty:
                    if recording and (time.time() - last_motion_at >= self.post_record):
                        self._finish_recording(motion_clip_frames, ai_confirmed, clip_start_time)
                        recording = False
                        motion_clip_frames = []
                    continue

                if not h264_header and len(h264_frame) > 4:
                    if (h264_frame[4] & 0x1F) in (7, 8):
                        h264_header += h264_frame

                h264_buf += h264_frame
                h264_count += 1

                if h264_count > 300 and not recording:
                    h264_buf = h264_header + h264_frame
                    h264_count = 1

                if h264_count % self.decode_interval != 0:
                    continue

                frame = decode_latest_frame(h264_buf, self.tmp_path)
                if frame is None: continue

                self.frames_decoded += 1
                now = time.time()
                ring_buffer.append((now, frame.copy()))

                # 1. Detect Motion
                motion, area, _ = detector.detect(frame)

                if motion:
                    last_motion_at = now
                    self.last_motion_time = now
                    
                    if not recording:
                        recording = True
                        ai_confirmed = False
                        clip_start_time = now
                        motion_clip_frames = [f.copy() for (_, f) in ring_buffer]
                        print(f"  [{self.ip}] >>> Suspected Motion (Area={area:.0f})")
                    
                    motion_clip_frames.append(frame.copy())
                    
                    # 2. Confirm with AI (if not already confirmed)
                    if self.use_ai and not ai_confirmed:
                        found, label, conf = ai_detector.detect_relevant_object(frame)
                        if found:
                            ai_confirmed = True
                            label_name = {1:'person', 17:'cat', 18:'dog'}.get(label, f'obj_{label}')
                            print(f"  [{self.ip}] AI CONFIRMED: Found {label_name} ({conf:.2f})")

                elif recording:
                    motion_clip_frames.append(frame.copy())
                    if now - last_motion_at >= self.post_record:
                        self._finish_recording(motion_clip_frames, ai_confirmed, clip_start_time)
                        recording = False
                        motion_clip_frames = []
                        h264_buf = h264_header
                        h264_count = 0

            except Exception as e:
                print(f"  [{self.ip}] Processor error: {e}")
                time.sleep(1)

    def _finish_recording(self, frames, ai_confirmed, start_time):
        if not frames: return
        
        # If AI is used but never confirmed a person/animal, we drop the clip to save space
        if self.use_ai and not ai_confirmed:
            # print(f"  [{self.ip}] Clip dropped (No Person/Animal detected).")
            return

        duration = time.time() - start_time
        self._save_motion_event(frames, duration)

    def _save_motion_event(self, frames, clip_duration=0):
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        date_dir = os.path.join(self.cam_dir, now.strftime("%Y-%m-%d"))
        os.makedirs(date_dir, exist_ok=True)

        snap_idx = min(int(self._decoded_fps * self.pre_record), len(frames) - 1)
        jpg_path = os.path.join(date_dir, f"motion_{timestamp}.jpg")
        cv2.imwrite(jpg_path, frames[snap_idx], [cv2.IMWRITE_JPEG_QUALITY, 90])

        h, w = frames[0].shape[:2]
        clip_path = os.path.join(date_dir, f"clip_{timestamp}.avi")
        writer = cv2.VideoWriter(clip_path, cv2.VideoWriter_fourcc(*"XVID"), self._decoded_fps, (w, h))
        for f in frames: writer.write(f)
        writer.release()

        self.motions_saved += 1
        print(f"  [{self.ip}] DONE: Saved {len(frames)} frames (~{clip_duration:.1f}s) -> {clip_path}")

    def stop(self):
        self.running = False


def status_printer(monitors, interval=60):
    while True:
        time.sleep(interval)
        print(f"\n--- Status at {datetime.datetime.now():%H:%M:%S} ---")
        for m in monitors:
            elapsed = time.time() - m.last_motion_time if m.last_motion_time else 0
            ago = f"{elapsed:.0f}s ago" if m.last_motion_time else "never"
            print(f"  [{m.ip}] {m.status} | saved={m.motions_saved} | last={ago}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cameras", nargs="+", default=DEFAULT_CAMERAS)
    p.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    p.add_argument("--min-area", type=int, default=DEFAULT_MIN_AREA)
    p.add_argument("--no-ai", action="store_true", help="Disable AI filtering")
    p.add_argument("--output", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion_clips_v2"))
    args = p.parse_args()

    print("=" * 60)
    print("  TP-Link Camera — AI-Filtered Motion Monitor (V2)")
    print("=" * 60)
    print(f"  AI Filtering: {'OFF' if args.no_ai else 'ON (Person/Cat/Dog)'}")
    print(f"  Threshold   : {args.threshold} | Min Area: {args.min_area}")
    print("=" * 60)

    monitors = []
    for ip in args.cameras:
        m = CameraMonitor(ip=ip, output_dir=args.output, threshold=args.threshold, min_area=args.min_area, use_ai=not args.no_ai)
        monitors.append(m)
        m.start()
        time.sleep(2)

    threading.Thread(target=status_printer, args=(monitors,), daemon=True).start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        for m in monitors: m.stop()

if __name__ == "__main__":
    main()
