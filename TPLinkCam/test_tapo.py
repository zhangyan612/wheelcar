import cv2
import time
import os

# ========================
# Configuration
# ========================
# For Tapo C113, you MUST create a "Camera Account" in the Tapo App:
# Settings -> Advanced Settings -> Camera Account
CAMERA_IP = "192.168.1.210"
USERNAME = "zhangyan612"
PASSWORD = "zymeng90612"

# RTSP URL Format: rtsp://username:password@IP:554/stream1
RTSP_URL = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/stream1"

from ultralytics import YOLO

def test_rtsp_connection():
    print(f"[*] STARTING YOLO TEST: {RTSP_URL.replace(PASSWORD, '****')}")
    
    # Load YOLOv8 model
    print("[*] Loading YOLOv8 model...")
    model = YOLO('yolov8n.pt') 
    
    # To reduce latency in OpenCV for RTSP:
    # 1. Use FFMPEG backend
    # 2. Set buffer size to 0 or 1
    # 3. Disable internal buffering if possible
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp" # Use UDP for lower latency
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Keep buffer minimal
    
    if not cap.isOpened():
        print("[-] FAILED: Could not open RTSP stream.")
        return False

    print("[+] SUCCESS: RTSP stream opened!")
    print("[*] Press 'q' to quit the live view.")
    
    prev_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[-] WARNING: Failed to read frame")
            break
            
        # Calculate FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time
        
        # Run YOLO inference
        results = model(frame, verbose=False)
        
        # Visualize the results
        annotated_frame = results[0].plot()
        
        # Add FPS text overlay
        cv2.putText(
            annotated_frame, 
            f"FPS: {fps:.1f}", 
            (20, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1.5, 
            (0, 255, 0), 
            3
        )
        
        # Display the live feed
        cv2.imshow("Tapo C113 - YOLOv8 Live", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("[+] FINISHED: Live test complete.")
    return True

if __name__ == "__main__":
    test_rtsp_connection()
