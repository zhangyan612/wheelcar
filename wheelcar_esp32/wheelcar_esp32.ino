/*
 * ESP32-WROVER Wheelcar Controller
 * Features:
 * - 4 Relay control (Forward, Backward, Left, Right)
 * - Camera streaming (OV2640)
 * - Servo control (PWM)
 * - Web interface
 */

#include <WiFi.h>
#include <WebServer.h>
#include <esp_camera.h>
#include <ESP32Servo.h>

// ===================
// WiFi Configuration
// ===================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// ===================
// Relay GPIO Pins
// ===================
#define RELAY_FORWARD  12  // 前进
#define RELAY_BACKWARD 13  // 后退
#define RELAY_LEFT     14  // 左转
#define RELAY_RIGHT    15  // 右转

// ===================
// Servo Configuration
// ===================
#define SERVO_PIN 2

// ===================
// Camera Pins (ESP32-WROVER-KIT with OV2640)
// ===================
#define PWDN_GPIO_NUM    -1
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM    21
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27

#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      19
#define Y4_GPIO_NUM      18
#define Y3_GPIO_NUM       5
#define Y2_GPIO_NUM       4
#define VSYNC_GPIO_NUM   25
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    22

// ===================
// Global Objects
// ===================
WebServer server(80);
Servo myServo;
int servoAngle = 90;

// ===================
// Camera Configuration
// ===================
camera_config_t camera_config = {
    .pin_pwdn = PWDN_GPIO_NUM,
    .pin_reset = RESET_GPIO_NUM,
    .pin_xclk = XCLK_GPIO_NUM,
    .pin_sscb_sda = SIOD_GPIO_NUM,
    .pin_sscb_scl = SIOC_GPIO_NUM,

    .pin_d7 = Y9_GPIO_NUM,
    .pin_d6 = Y8_GPIO_NUM,
    .pin_d5 = Y7_GPIO_NUM,
    .pin_d4 = Y6_GPIO_NUM,
    .pin_d3 = Y5_GPIO_NUM,
    .pin_d2 = Y4_GPIO_NUM,
    .pin_d1 = Y3_GPIO_NUM,
    .pin_d0 = Y2_GPIO_NUM,
    .pin_vsync = VSYNC_GPIO_NUM,
    .pin_href = HREF_GPIO_NUM,
    .pin_pclk = PCLK_GPIO_NUM,

    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,

    .pixel_format = PIXFORMAT_JPEG,
    .frame_size = FRAMESIZE_QVGA,    // 320x240
    .jpeg_quality = 12,
    .fb_count = 2,
    .fb_location = CAMERA_FB_IN_PSRAM
};

// ===================
// HTML Web Interface (embedded)
// ===================
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Wheelcar Controller</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 10px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .camera-section {
            text-align: center;
            margin-bottom: 15px;
        }
        .camera-section img {
            width: 100%;
            max-width: 400px;
            border-radius: 10px;
            border: 3px solid #0f3460;
        }
        .control-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        .control-row {
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        .btn {
            width: 80px;
            height: 80px;
            font-size: 1.2em;
            font-weight: bold;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.2s;
            user-select: none;
            -webkit-user-select: none;
            touch-action: manipulation;
        }
        .btn:active {
            transform: scale(0.95);
        }
        .btn-forward { background: linear-gradient(145deg, #00b894, #00a085); color: white; }
        .btn-backward { background: linear-gradient(145deg, #e17055, #d63031); color: white; }
        .btn-left { background: linear-gradient(145deg, #0984e3, #0769b8); color: white; }
        .btn-right { background: linear-gradient(145deg, #6c5ce7, #5b4cdb); color: white; }
        .btn-stop { background: linear-gradient(145deg, #fdcb6e, #f39c12); color: #2d3436; }
        .btn-empty { visibility: hidden; }
        .servo-section {
            margin-top: 20px;
            text-align: center;
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
        }
        .servo-section h3 {
            margin-bottom: 10px;
        }
        .slider-container {
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: center;
        }
        input[type="range"] {
            width: 200px;
            height: 8px;
            -webkit-appearance: none;
            background: #0f3460;
            border-radius: 4px;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 24px;
            height: 24px;
            background: #00b894;
            border-radius: 50%;
            cursor: pointer;
        }
        .angle-display {
            font-size: 1.2em;
            font-weight: bold;
            min-width: 50px;
        }
        .status {
            text-align: center;
            margin-top: 15px;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 Wheelcar Controller</h1>
        
        <div class="camera-section">
            <img id="camera" src="" alt="Camera Stream">
        </div>
        
        <div class="control-section">
            <div class="control-row">
                <button class="btn btn-empty"></button>
                <button class="btn btn-forward" ontouchstart="control('forward')" ontouchend="control('stop')" onmousedown="control('forward')" onmouseup="control('stop')">前进</button>
                <button class="btn btn-empty"></button>
            </div>
            <div class="control-row">
                <button class="btn btn-left" ontouchstart="control('left')" ontouchend="control('stop')" onmousedown="control('left')" onmouseup="control('stop')">左转</button>
                <button class="btn btn-stop" onclick="control('stop')">停止</button>
                <button class="btn btn-right" ontouchstart="control('right')" ontouchend="control('stop')" onmousedown="control('right')" onmouseup="control('stop')">右转</button>
            </div>
            <div class="control-row">
                <button class="btn btn-empty"></button>
                <button class="btn btn-backward" ontouchstart="control('backward')" ontouchend="control('stop')" onmousedown="control('backward')" onmouseup="control('stop')">后退</button>
                <button class="btn btn-empty"></button>
            </div>
        </div>
        
        <div class="servo-section">
            <h3>🎯 Servo Control</h3>
            <div class="slider-container">
                <span>0°</span>
                <input type="range" id="servoSlider" min="0" max="180" value="90" oninput="setServo(this.value)">
                <span>180°</span>
            </div>
            <div class="angle-display">Angle: <span id="servoAngle">90</span>°</div>
        </div>
        
        <div class="status">
            Status: <span id="status">Ready</span>
        </div>
    </div>
    
    <script>
        var cameraInterval;
        
        function startCamera() {
            document.getElementById('camera').src = '/stream';
        }
        
        function control(action) {
            fetch('/control?action=' + action)
                .then(response => response.text())
                .then(data => {
                    document.getElementById('status').innerText = action;
                })
                .catch(err => {
                    console.log('Error:', err);
                });
        }
        
        function setServo(angle) {
            document.getElementById('servoAngle').innerText = angle;
            fetch('/servo?angle=' + angle)
                .catch(err => console.log('Error:', err));
        }
        
        // Start camera on page load
        window.onload = function() {
            startCamera();
        };
    </script>
</body>
</html>
)rawliteral";

// ===================
// Initialize Camera
// ===================
bool initCamera() {
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x", err);
        return false;
    }
    return true;
}

// ===================
// Relay Control Functions
// ===================
void allRelaysOff() {
    digitalWrite(RELAY_FORWARD, HIGH);
    digitalWrite(RELAY_BACKWARD, HIGH);
    digitalWrite(RELAY_LEFT, HIGH);
    digitalWrite(RELAY_RIGHT, HIGH);
}

void controlRelay(String action) {
    allRelaysOff();  // Safety: turn off all first
    
    if (action == "forward") {
        digitalWrite(RELAY_FORWARD, LOW);
    } else if (action == "backward") {
        digitalWrite(RELAY_BACKWARD, LOW);
    } else if (action == "left") {
        digitalWrite(RELAY_LEFT, LOW);
    } else if (action == "right") {
        digitalWrite(RELAY_RIGHT, LOW);
    }
    // "stop" is handled by allRelaysOff()
}

// ===================
// Handle Root Page
// ===================
void handleRoot() {
    server.send(200, "text/html", index_html);
}

// ===================
// Handle Control Request
// ===================
void handleControl() {
    if (server.hasArg("action")) {
        String action = server.arg("action");
        controlRelay(action);
        Serial.println("Action: " + action);
        server.send(200, "text/plain", "OK: " + action);
    } else {
        server.send(400, "text/plain", "Missing action");
    }
}

// ===================
// Handle Servo Request
// ===================
void handleServo() {
    if (server.hasArg("angle")) {
        int angle = server.arg("angle").toInt();
        angle = constrain(angle, 0, 180);
        myServo.write(angle);
        servoAngle = angle;
        Serial.printf("Servo angle: %d\n", angle);
        server.send(200, "text/plain", "OK");
    } else {
        server.send(400, "text/plain", "Missing angle");
    }
}

// ===================
// Handle Camera Stream (Single JPEG capture)
// ===================
void handleStream() {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
        server.send(500, "text/plain", "Camera capture failed");
        return;
    }
    
    // Build HTTP response header
    String header = "HTTP/1.1 200 OK\r\n"
                    "Content-Type: image/jpeg\r\n"
                    "Content-Length: " + String(fb->len) + "\r\n"
                    "Connection: close\r\n\r\n";
    
    server.client().write(header.c_str());
    server.client().write((const char*)fb->buf, fb->len);
    
    esp_camera_fb_return(fb);
}

// ===================
// MJPEG Streaming (Continuous)
// ===================
void handleMJPEGStream() {
    camera_fb_t * fb = NULL;
    
    String response = "HTTP/1.1 200 OK\r\n"
                      "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
                      "Connection: close\r\n\r\n";
    
    server.client().write(response.c_str());
    
    while (server.client().connected()) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Camera capture failed");
            break;
        }
        
        String header = "--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + String(fb->len) + "\r\n\r\n";
        server.client().write(header.c_str());
        server.client().write((const char*)fb->buf, fb->len);
        server.client().write("\r\n");
        
        esp_camera_fb_return(fb);
        fb = NULL;
        
        delay(30);  // ~30fps
    }
}

// ===================
// Setup
// ===================
void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();
    
    // Initialize relay pins
    pinMode(RELAY_FORWARD, OUTPUT);
    pinMode(RELAY_BACKWARD, OUTPUT);
    pinMode(RELAY_LEFT, OUTPUT);
    pinMode(RELAY_RIGHT, OUTPUT);
    allRelaysOff();
    Serial.println("Relays initialized");
    
    // Initialize servo
    myServo.attach(SERVO_PIN);
    myServo.write(servoAngle);
    Serial.println("Servo initialized");
    
    // Initialize camera
    if (!initCamera()) {
        Serial.println("Camera initialization failed!");
    } else {
        Serial.println("Camera initialized");
    }
    
    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.print("Connected! IP: ");
    Serial.println(WiFi.localIP());
    
    // Setup web server routes
    server.on("/", handleRoot);
    server.on("/control", handleControl);
    server.on("/servo", handleServo);
    server.on("/stream", handleMJPEGStream);
    server.on("/capture", handleStream);
    
    // Start server
    server.begin();
    Serial.println("HTTP server started");
    Serial.printf("Open http://%s in your browser\n", WiFi.localIP().toString().c_str());
}

// ===================
// Loop
// ===================
void loop() {
    server.handleClient();
    delay(2);  // Small delay for stability
}
