import cv2
import time
import os
import argparse

# ========================
# Configuration
# ========================
# For Tapo C113, you MUST create a "Camera Account" in the Tapo App:
# Settings -> Advanced Settings -> Camera Account
CAMERA_IP = "192.168.1.210"
USERNAME = "zhangyan612"
PASSWORD = "zymeng90612"

# RTSP URL Format: rtsp://username:password@IP:554/stream1 (main) or /stream2 (sub)
DEFAULT_STREAM = "stream2"
RTSP_URL = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/{DEFAULT_STREAM}"

from ultralytics import YOLO

def parse_args():
    parser = argparse.ArgumentParser(description="Tapo RTSP FPS test with YOLO")
    parser.add_argument("--stream", choices=["stream1", "stream2"], default=DEFAULT_STREAM)
    parser.add_argument("--transport", choices=["udp", "tcp"], default="udp")
    parser.add_argument("--frame-skip", type=int, default=1, help="Run YOLO every Nth frame")
    parser.add_argument("--infer-width", type=int, default=640, help="YOLO imgsz (smaller is faster)")
    parser.add_argument("--no-show", action="store_true", help="Run without opening a display window")
    parser.add_argument("--windowed", action="store_true", help="Disable fullscreen display")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO model path")
    return parser.parse_args()


def test_rtsp_connection(args):
    rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:554/{args.stream}"
    print(f"[*] STARTING YOLO TEST: {rtsp_url.replace(PASSWORD, '****')}")
    
    # Load YOLOv8 model
    print("[*] Loading YOLOv8 model...")
    model = YOLO(args.model)
    
    # To reduce latency in OpenCV for RTSP:
    # 1. Use FFMPEG backend
    # 2. Set buffer size to 0 or 1
    # 3. Disable internal buffering if possible
    # Low-latency options can improve freshness, but camera-side FPS caps still apply.
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        f"rtsp_transport;{args.transport}|fflags;nobuffer|flags;low_delay|reorder_queue_size;0|max_delay;0"
    )
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Keep buffer minimal
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    if not cap.isOpened():
        print("[-] FAILED: Could not open RTSP stream.")
        return False

    print("[+] SUCCESS: RTSP stream opened!")
    print("[*] Press 'q' to quit the live view.")
    print(f"[*] Camera reported: {cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f} @ {cap.get(cv2.CAP_PROP_FPS):.1f} FPS")

    window_name = "Tapo C113 - YOLOv8 Live"
    if not args.no_show:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        if not args.windowed:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    prev_time = time.time()
    frame_count = 0
    yolo_fps = 0.0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[-] WARNING: Failed to read frame")
            break
        frame_count += 1
            
        # Calculate FPS
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0.0
        prev_time = curr_time

        # Run YOLO every Nth frame to keep display/input loop responsive.
        run_yolo = (frame_count % max(1, args.frame_skip) == 0)
        annotated_frame = frame
        if run_yolo:
            t0 = time.time()
            # Keep display at original resolution, but run inference at lower imgsz.
            results = model.predict(source=frame, imgsz=args.infer_width, verbose=False)
            yolo_dt = time.time() - t0
            yolo_fps = 1.0 / yolo_dt if yolo_dt > 0 else 0.0
            annotated_frame = results[0].plot()
        
        # Add FPS text overlay
        cv2.putText(
            annotated_frame, 
            f"Read FPS: {fps:.1f}  YOLO FPS: {yolo_fps:.1f}", 
            (20, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.9, 
            (0, 255, 0), 
            2
        )
        
        if not args.no_show:
            # Display the live feed
            cv2.imshow(window_name, annotated_frame)
        
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
    cap.release()
    cv2.destroyAllWindows()
    print("[+] FINISHED: Live test complete.")
    return True

if __name__ == "__main__":
    args = parse_args()
    test_rtsp_connection(args)
