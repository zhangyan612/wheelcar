#!/usr/bin/env python3
"""
Simple MJPEG Camera Web Server for UP Board
Works with Python 3.7+
Access from other computers: http://<UP_BOARD_IP>:5000
"""

from flask import Flask, Response
import cv2
import socket

app = Flask(__name__)

# Camera configuration
CAMERA_INDEX = 0  # Usually 0 for default camera


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


def generate_frames():
    """Generate MJPEG frames from camera"""
    camera = cv2.VideoCapture(CAMERA_INDEX)
    
    # Set camera resolution (adjust as needed)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not camera.isOpened():
        print("Error: Cannot open camera")
        return
    
    while True:
        success, frame = camera.read()
        if not success:
            print("Error: Cannot read frame")
            break
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue
        
        # Yield MJPEG frame
        frame_bytes = buffer.tobytes()
        yield (b'--frame
'
               b'Content-Type: image/jpeg

' + frame_bytes + b'\r\n')
    
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
    print(f"\n  Access from browser:")
    print(f"  http://{local_ip}:{port}")
    print(f"  http://localhost:{port}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50)
    
    # Run on all network interfaces (0.0.0.0)
    app.run(host='0.0.0.0', port=port, threaded=True)
