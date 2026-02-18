#!/usr/bin/env python3
"""
MJPEG Camera Web Server for UP Board with Intel RealSense Camera
Works with Python 3.7+
Access from other computers: http://<UP_BOARD_IP>:5000
"""

from flask import Flask, Response
import socket
import numpy as np

# Try to use RealSense SDK first, fallback to OpenCV
USE_REALSENSE = False
try:
    import pyrealsense2 as rs
    USE_REALSENSE = True
    print("Using Intel RealSense SDK")
except ImportError:
    import cv2
    print("RealSense SDK not found, falling back to OpenCV")

app = Flask(__name__)

# Global RealSense objects
pipeline = None
config = None


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


def init_realsense():
    """Initialize RealSense pipeline for RGB stream"""
    global pipeline, config
    pipeline = rs.pipeline()
    config = rs.config()
    
    # Configure RGB stream only
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    
    # Start pipeline
    profile = pipeline.start(config)
    return True


def generate_frames_realsense():
    """Generate MJPEG frames from RealSense camera"""
    try:
        while True:
            # Wait for frames
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            
            if not color_frame:
                continue
            
            # Convert to numpy array (BGR format for JPEG encoding)
            frame = np.asanyarray(color_frame.get_data())
            
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        if pipeline:
            pipeline.stop()


def generate_frames_opencv():
    """Fallback: Generate MJPEG frames using OpenCV"""
    import cv2
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not camera.isOpened():
        print("Error: Cannot open camera")
        return
    
    try:
        while True:
            success, frame = camera.read()
            if not success:
                print("Error: Cannot read frame")
                break
            
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
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
    if USE_REALSENSE:
        return Response(generate_frames_realsense(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return Response(generate_frames_opencv(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    local_ip = get_local_ip()
    port = 5000
    
    print("=" * 50)
    print("  UP Board Camera Web Server")
    print("=" * 50)
    
    if USE_REALSENSE:
        print("  Camera: Intel RealSense")
        init_realsense()
    else:
        print("  Camera: OpenCV fallback")
    
    print(f"\n  Access from browser:")
    print(f"  http://{local_ip}:{port}")
    print(f"  http://localhost:{port}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, threaded=True)