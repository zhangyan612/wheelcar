#!/usr/bin/env python3
"""
MJPEG Camera Web Server for UP Board with Intel RealSense F200 Camera
The F200 is an older model - use OpenCV with DirectShow backend
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
CAMERA_BACKEND = None


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
    Try to find the one with color output.
    """
    global CAMERA_INDEX, CAMERA_BACKEND
    
    # Try DirectShow first (Windows), then V4L2 (Linux), then default
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_ANY, "Default"),
    ]
    
    for backend, backend_name in backends:
        for index in range(5):  # Try indices 0-4
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Check if it's a color image (3 channels)
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        # Check if image is not all green/monochrome (F200 depth/IR)
                        avg_color = np.mean(frame, axis=(0, 1))
                        # BGR: check if not dominated by green
                        if not (avg_color[1] > avg_color[0] * 2 and avg_color[1] > avg_color[2] * 2):
                            print(f"  Found color camera at index {index} using {backend_name}")
                            CAMERA_INDEX = index
                            CAMERA_BACKEND = backend
                            cap.release()
                            return True
                cap.release()
    
    # Fallback: just use index 0
    print("  Could not auto-detect camera, using index 0")
    CAMERA_INDEX = 0
    CAMERA_BACKEND = cv2.CAP_DSHOW
    return True


def generate_frames():
    """Generate MJPEG frames from camera"""
    camera = cv2.VideoCapture(CAMERA_INDEX, CAMERA_BACKEND)
    
    # Set camera resolution
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    
    if not camera.isOpened():
        print("Error: Cannot open camera")
        return
    
    print("  Camera stream started")
    
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
        h1 {
            color: #00d4ff;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .stream-container {
            background: #16213e;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2);
        }
        img {
            width: 100%;
            max-width: 640px;
            border-radius: 5px;
        }
        .info {
            margin-top: 20px;
            color: #888;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📷 UP Board Camera</h1>
        <div class="stream-container">
            <img src="/video_feed" alt="Camera Stream">
        </div>
        <div class="info">
            MJPEG Stream | Refresh page if stream stops
        </div>
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
    camera = cv2.VideoCapture(CAMERA_INDEX, CAMERA_BACKEND)
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
    print("  Detecting camera...")
    find_camera()
    
    print(f"\n  Access from browser:")
    print(f"  http://{local_ip}:{port}")
    print(f"  http://localhost:{port}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, threaded=True)
