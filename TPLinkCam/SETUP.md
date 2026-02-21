# TP-Link Kasa Camera Streaming Setup

## Overview

This project enables streaming video from **TP-Link Kasa** indoor cameras (tested on **EC60**) to a PC.  
These cameras do **NOT** support native RTSP — instead, they expose an HTTPS endpoint on **port 19443** that delivers raw **H.264** video via a multipart HTTP stream.

We reverse-engineered the authentication and stream protocol and built a Python client that:

- Connects over HTTPS with a custom TLS adapter (camera uses old/self-signed certs)
- Authenticates using the TP-Link Kasa account (email + base64-encoded password)
- Parses the `multipart/x-mixed-replace` stream to extract H.264 NAL units
- Decodes H.264 frames using OpenCV's FFMPEG backend
- Displays live video or serves it as a browser-viewable MJPEG web feed

## New: Tapo C113 Support (Native RTSP)

The **Tapo C113** (and other Tapo models like C200, C210) supports **native RTSP**. This is much more efficient and has < 1 second latency.

- **Status**: Tested and Working
- **IP**: `192.168.1.210`
- **Port**: `554` (Standard RTSP)
- **URL**: `rtsp://<camera_user>:<camera_pass>@192.168.1.210:554/stream1`
- **Setup**: You MUST create a "Camera Account" in the Tapo App (Settings -> Advanced Settings -> Camera Account). This is separate from your TP-Link ID.

---

## What Was Done

### 1. Network Discovery
- **Camera 1 (Kasa EC60)**: `192.168.1.209`
  - Port **19443** (HTTPS) is open.
  - No RTSP support.
- **Camera 2 (Tapo C113)**: `192.168.1.210`
  - Port **554** (RTSP) is open.
  - Native RTSP support enabled via Camera Account.

### 2. Authentication
The camera uses **HTTP Basic Auth** over HTTPS:
- **Username**: Your TP-Link Kasa account email  
- **Password**: Your Kasa password, **base64-encoded** before being sent as the Basic Auth password

```
Authorization: Basic base64(email:base64(password))
```

### 3. Stream Protocol
- **URL**: `https://<camera_ip>:19443/https/stream/mixed?video=h264&audio=g711&resolution=hd`
- **Response**: `Content-Type: multipart/x-mixed-replace;boundary=data-boundary--`
- Each part has headers:
  ```
  --data-boundary--
  Content-Type: video/x-h264
  Content-Length: <bytes>
  X-UtcTime: <unix_timestamp>
  X-Timestamp: <timestamp>
  
  <raw H.264 NAL data>
  ```
- **Resolution**: 1920×1080 (Full HD)
- **Codec**: H.264

### 4. TLS Workaround
The camera uses older SSL/TLS that modern Python `requests` rejects.  
We use a custom `TLSAdapter` that:
- Disables hostname checking
- Disables certificate verification  
- Sets cipher suite to `ALL:@SECLEVEL=0` to allow legacy ciphers

### 5. Decoding Approach
Since FFmpeg CLI was not initially available, we use a **file-buffer** strategy:
1. Accumulate H.264 NAL units into a temp `.h264` file
2. Periodically open it with `cv2.VideoCapture(path, cv2.CAP_FFMPEG)`
3. Seek to the last decoded frame and display it

This works but introduces **10–40 seconds of latency** due to buffering and re-decoding.

---

## Known Limitations

| Issue | Cause | Possible Fix |
|-------|-------|-------------|
| **High latency (10-40s)** | H.264 buffering + file re-decode | Use FFmpeg pipe or RTSP camera |
| **No native RTSP** | TP-Link Kasa EC60 design | Buy a camera with RTSP support |
| **CPU usage** | Re-decoding H.264 file every N frames | Use FFmpeg subprocess pipe |
| **Single stream** | Camera may limit concurrent connections | Use one client, re-stream via RTSP/MJPEG |

---

## Recommended Alternative: RTSP Camera

For **low-latency** live streaming, use a camera with **native RTSP support**.  
RTSP cameras work directly with OpenCV in ~2 lines of code:

```python
cap = cv2.VideoCapture("rtsp://user:pass@192.168.1.xxx:554/stream1")
while True:
    ret, frame = cap.read()
    cv2.imshow("Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

**Latency**: typically < 1 second.

### Good RTSP cameras to consider:
- **Tapo C113 / C200 / C210** (TP-Link's newer line, supports RTSP natively! Tested at `192.168.1.210`)
- **Reolink E1 / RLC-510A** (reliable RTSP, good quality)
- **Wyze Cam v3** (with RTSP firmware)
- **Amcrest IP cameras** (excellent RTSP support)
- **Hikvision / Dahua** (pro-grade, full RTSP)

---

## Installation

```bash
# Using the ultrarag conda environment, make sure to switch to the env before installing anything
pip install opencv-python requests numpy flask ultralytics
```

FFmpeg should also be installed for H.264 decoding:
```bash
winget install ffmpeg
```

---

## Usage

### Live Display (Default Camera)
```bash
python tplink_camera.py
```

### Live Display (Different Camera IP)
```bash
python tplink_camera.py --ip 192.168.1.210
```

### Custom Credentials
```bash
python tplink_camera.py --ip 192.168.1.210 --user other@email.com --password otherpass
```

### Test Connectivity Only
```bash
python tplink_camera.py --ip 192.168.1.210 --test
```

### Save H.264 Recording
```bash
python tplink_camera.py --save --duration 30 --output my_recording.h264
```

### Web MJPEG Server (View in Browser)
```bash
python tplink_camera.py --web --web-port 5001
# Then open http://<your_pc_ip>:5001 in a browser
```

### Live Display (Tapo Camera with YOLOv8)
```bash
python test_tapo.py
```

### Reduce Latency (More CPU)
```bash
python tplink_camera.py --decode-interval 5
```

---

## File Structure

```
TPLinkCam/
├── SETUP.md                 # This document
├── tplink_camera.py         # Main reusable camera client
├── test_connection.py       # Connection test script (Kasa)
├── test_connection2.py      # Detailed connection logger (Kasa)
├── test_tapo.py             # RTSP connection test (Tapo)
├── connection_log.txt       # Sample connection log
├── readme.md                # Original research notes
└── camera_stream.h264       # Sample saved H.264 recording (gitignored)
```

---

## API Reference (for Programmatic Use)

```python
from tplink_camera import TPLinkCamera

# Create a camera client
cam = TPLinkCamera(
    ip="192.168.1.209",
    port=19443,
    username="your@email.com",
    password="yourpassword"
)

# Test connectivity
cam.test_connection()  # Returns True/False

# Live display (blocking, opens OpenCV window)
cam.live_display(decode_interval=10)

# Save recording
cam.save_recording(output_path="clip.h264", duration_seconds=10)

# Web server (blocking, starts Flask)
cam.serve_web(port=5001)
```

---

## Architecture

```
┌──────────────┐    HTTPS/19443     ┌──────────────┐
│  TP-Link     │ ──────────────────>│  Python      │
│  EC60 Camera │  multipart H.264   │  Client      │
│  (Kasa)      │ <──────────────────│              │
└──────────────┘    Basic Auth      └──────┬───────┘
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                         ┌────▼────┐  ┌────▼────┐  ┌───▼────┐
                         │ OpenCV  │  │ Flask   │  │ .h264  │
                         │ Window  │  │ Web     │  │ File   │
                         │ Display │  │ MJPEG   │  │ Save   │
                         └─────────┘  └─────────┘  └────────┘
```
### AI-Powered Motion Detection (V2)
```bash
python motion_detect_v2.py
```
This version adds **AI Filtering** (using Torch + SSD-Mobilenet) to verify motion events. It specifically looks for **People, Cats, and Dogs**, automatically dropping clips caused by wind, trees, or shadows. It also uses higher default thresholds to reduce "frequent" triggers.
