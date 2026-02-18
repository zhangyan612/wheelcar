#!/usr/bin/env python3
"""
MJPEG Camera Web Server for UP Board with Intel RealSense F200 Camera
Works with Python 3.7+
Access from other computers: http://<UP_BOARD_IP>:5000
"""

from flask import Flask, Response
import socket
import cv2
import numpy as np

app = Flask(__name__)

# Camera configuration - will be auto-detected
CAMERA_INDEX = None


def get_local_ip():
    """Get the local IP address of this device"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_camera():
    """
    Auto-detect working camera.
    F200 has multiple streams (RGB, depth, IR) on different indices.
    """
    global CAMERA_INDEX
    
    print("  Scanning for cameras...")
    
    for index in range(6):  # Try indices 0-5
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                channels = frame.shape[2] if len(frame.shape) == 3 else 1
                
                print(f"    Index {index}: {w}x{h}, {channels} channels")
                
                # Check if it's a color image (3 channels)
                if channels == 3:
                    # Check if image is not all green (depth/IR from F200)
                    avg_color = np.mean(frame, axis=(0, 1))
                    green_ratio = avg_color[1] / (avg_color[0] + avg_color[2] + 1)
                    
                    if green_ratio < 1.5:  # Not dominated by green
                        print(f"    -> Selected (color camera)")
                        CAMERA_INDEX = index
                        cap.release()
                        return True
                    else:
                        print(f"    -> Skipping (appears to be depth/IR stream)")
            cap.release()
    
    # Fallback: just use index 0
    print("  Could not find color camera, using index 0")
    CAMERA_INDEX = 0
    return True


def generate_frames():
    """Generate MJPEG frames from camera"""
    camera = cv2.VideoCapture(CAMERA_INDEX)
    
    # Set camera resolution (higher resolution)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not camera.isOpened():
        print("Error: Cannot open camera")
        return
    
    print("  Stream started")
    
    while True:
        success, frame = camera.read()
        if not success:
            print("Error: Cannot read frame")
            break
        
        # Encode as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    camera.release()


@app.route('/')
def index():
    """Home page with camera stream"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>UP Board Camera</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a2e;
            color: #eee;
            text-align: center;
        }
        h1 { color: #00d4ff; }
        .container { max-width: 100%; margin: 0 auto; }
        .stream-container {
            background: #16213e;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2);
        }
        img { width: 100%; max-width: 1280px; border-radius: 5px; }
        .info { margin-top: 20px; color: #888; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📷 UP Board Camera</h1>
        <div class="stream-container">
            <img src="/video_feed" alt="Camera Stream">
        </div>
        <div class="info">MJPEG Stream | Refresh if stream stops</div>
    </div>
</body>
</html>
'''


@app.route('/video_feed')
def video_feed():
    """MJPEG video stream endpoint"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/snapshot')
def snapshot():
    """Single snapshot endpoint"""
    camera = cv2.VideoCapture(CAMERA_INDEX)
    success, frame = camera.read()
    camera.release()
    
    if success:
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if ret:
            return Response(buffer.tobytes(), mimetype='image/jpeg')
    
    return "Camera error", 500


if __name__ == '__main__':
    local_ip = get_local_ip()
    port = 5000
    
    print("=" * 50)
    print("  UP Board Camera Web Server")
    print("=" * 50)
    find_camera()
    
    print(f"\n  Access from browser:")
    print(f"  http://{local_ip}:{port}")
    print(f"  http://localhost:{port}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, threaded=True)