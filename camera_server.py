#!/usr/bin/env python3
"""
MJPEG Camera Web Server for UP Board with Intel RealSense F200 Camera
Integrated with ESP32 Wheelcar Controller
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

# ESP32 Configuration - Change this to your ESP32's IP address
ESP32_IP = "192.168.1.206"  # Default ESP32 IP


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
    """Home page with camera stream and controls"""
    return f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Wheelcar Camera Controller</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }}
        .main-container {{
            display: flex;
            flex-wrap: wrap;
            height: 100vh;
        }}
        /* Left: Camera Section */
        .camera-section {{
            flex: 1;
            min-width: 400px;
            display: flex;
            flex-direction: column;
            padding: 15px;
        }}
        .camera-title {{
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            margin-bottom: 10px;
            font-size: 1.3em;
        }}
        .camera-title span {{
            color: #00d4ff;
        }}
        .stream-container {{
            flex: 1;
            background: #16213e;
            border-radius: 10px;
            padding: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2);
        }}
        .stream-container img {{
            width: 100%;
            height: auto;
            max-height: calc(100vh - 120px);
            object-fit: contain;
            border-radius: 5px;
        }}
        /* Right: Control Section */
        .control-section {{
            width: 320px;
            min-width: 280px;
            background: rgba(0,0,0,0.3);
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .control-title {{
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            font-size: 1.3em;
        }}
        .control-title span {{
            color: #00b894;
        }}
        /* Direction Controls */
        .direction-controls {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        }}
        .control-row {{
            display: flex;
            justify-content: center;
            gap: 8px;
        }}
        .btn {{
            width: 75px;
            height: 75px;
            font-size: 1.1em;
            font-weight: bold;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.15s;
            user-select: none;
            -webkit-user-select: none;
            touch-action: manipulation;
        }}
        .btn:active {{
            transform: scale(0.92);
            filter: brightness(1.2);
        }}
        .btn-forward {{ background: linear-gradient(145deg, #00b894, #00a085); color: white; }}
        .btn-backward {{ background: linear-gradient(145deg, #e17055, #d63031); color: white; }}
        .btn-left {{ background: linear-gradient(145deg, #0984e3, #0769b8); color: white; }}
        .btn-right {{ background: linear-gradient(145deg, #6c5ce7, #5b4cdb); color: white; }}
        .btn-stop {{ background: linear-gradient(145deg, #fdcb6e, #f39c12); color: #2d3436; }}
        .btn-empty {{ visibility: hidden; }}
        /* Servo Controls */
        .servo-controls {{
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            text-align: center;
        }}
        .servo-controls h3 {{
            margin-bottom: 15px;
            color: #00d4ff;
        }}
        .slider-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: center;
            margin-bottom: 10px;
        }}
        input[type="range"] {{
            width: 180px;
            height: 8px;
            -webkit-appearance: none;
            background: #0f3460;
            border-radius: 4px;
            outline: none;
        }}
        input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 24px;
            height: 24px;
            background: #00b894;
            border-radius: 50%;
            cursor: pointer;
        }}
        .angle-display {{
            font-size: 1.3em;
            font-weight: bold;
        }}
        .angle-display span {{
            color: #00d4ff;
        }}
        /* Status */
        .status {{
            padding: 12px;
            background: rgba(0,0,0,0.4);
            border-radius: 8px;
            text-align: center;
            font-size: 1em;
        }}
        .status-value {{
            color: #00d4ff;
            font-weight: bold;
        }}
        /* ESP32 IP Config */
        .esp-config {{
            padding: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            text-align: center;
        }}
        .esp-config input {{
            width: 140px;
            padding: 6px 10px;
            border: none;
            border-radius: 5px;
            background: #0f3460;
            color: #fff;
            text-align: center;
            font-size: 0.95em;
        }}
        /* Responsive */
        @media (max-width: 900px) {{
            .main-container {{
                flex-direction: column;
            }}
            .camera-section {{
                min-width: 100%;
                height: 50vh;
            }}
            .control-section {{
                width: 100%;
                min-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Left: Camera -->
        <div class="camera-section">
            <div class="camera-title"><span>📷</span> Camera Stream</div>
            <div class="stream-container">
                <img src="/video_feed" alt="Camera Stream">
            </div>
        </div>
        
        <!-- Right: Controls -->
        <div class="control-section">
            <div class="control-title"><span>🚗</span> Controls</div>
            
            <!-- ESP32 IP -->
            <div class="esp-config">
                <label>ESP32 IP: </label>
                <input type="text" id="espIp" value="{ESP32_IP}" placeholder="192.168.1.x">
            </div>
            
            <!-- Direction Controls -->
            <div class="direction-controls">
                <div class="control-row">
                    <button class="btn btn-empty"></button>
                    <button class="btn btn-forward" 
                        ontouchstart="control('forward')" ontouchend="control('stop')"
                        onmousedown="control('forward')" onmouseup="control('stop')"
                        onmouseleave="control('stop')">前进</button>
                    <button class="btn btn-empty"></button>
                </div>
                <div class="control-row">
                    <button class="btn btn-left"
                        ontouchstart="control('left')" ontouchend="control('stop')"
                        onmousedown="control('left')" onmouseup="control('stop')"
                        onmouseleave="control('stop')">左转</button>
                    <button class="btn btn-stop" onclick="control('stop')">停止</button>
                    <button class="btn btn-right"
                        ontouchstart="control('right')" ontouchend="control('stop')"
                        onmousedown="control('right')" onmouseup="control('stop')"
                        onmouseleave="control('stop')">右转</button>
                </div>
                <div class="control-row">
                    <button class="btn btn-empty"></button>
                    <button class="btn btn-backward"
                        ontouchstart="control('backward')" ontouchend="control('stop')"
                        onmousedown="control('backward')" onmouseup="control('stop')"
                        onmouseleave="control('stop')">后退</button>
                    <button class="btn btn-empty"></button>
                </div>
            </div>
            
            <!-- Servo Controls -->
            <div class="servo-controls">
                <h3>🎯 Servo Control</h3>
                <div class="slider-container">
                    <span>0°</span>
                    <input type="range" id="servoSlider" min="0" max="180" value="90" oninput="setServo(this.value)">
                    <span>180°</span>
                </div>
                <div class="angle-display">Angle: <span id="servoAngle">90</span>°</div>
            </div>
            
            <!-- Status -->
            <div class="status">
                Status: <span class="status-value" id="status">Ready</span>
            </div>
        </div>
    </div>
    
    <script>
        function getEspUrl() {{
            return 'http://' + document.getElementById('espIp').value;
        }}
        
        function control(action) {{
            document.getElementById('status').innerText = action;
            fetch(getEspUrl() + '/control?action=' + action)
                .catch(err => {{
                    console.log('ESP32 Error:', err);
                    document.getElementById('status').innerText = 'Connection Error';
                }});
        }}
        
        function setServo(angle) {{
            document.getElementById('servoAngle').innerText = angle;
            fetch(getEspUrl() + '/servo?angle=' + angle)
                .catch(err => console.log('ESP32 Error:', err));
        }}
    </script>
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
    print("  Wheelcar Camera Controller")
    print("=" * 50)
    find_camera()
    
    print(f"\n  Access from browser:")
    print(f"  http://{local_ip}:{port}")
    print(f"  http://localhost:{port}")
    print(f"\n  ESP32 IP: {ESP32_IP} (change in code if needed)")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, threaded=True)