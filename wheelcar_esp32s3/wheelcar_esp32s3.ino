/*
 * ESP32-S3-N8R2 Wheelcar Controller
 * Features:
 * - 4 Relay control (Forward, Backward, Left, Right)
 * - Servo control (PWM)
 * - Web interface (no camera)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// ===================
// WiFi Configuration
// ===================
const char* ssid = "Verizon_YGCW99";
const char* password = "yon4-ewer-holly";

// ===================
// Relay GPIO Pins (ESP32-S3 safe pins)
// ===================
#define RELAY_FORWARD  4   // 前进
#define RELAY_BACKWARD 5   // 后退
#define RELAY_LEFT     6   // 左转
#define RELAY_RIGHT    7   // 右转

// ===================
// Servo Configuration
// ===================
#define SERVO_PIN 8

// ===================
// Global Objects
// ===================
WebServer server(80);
Servo myServo;
int servoAngle = 90;

// ===================
// HTML Web Interface
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
        .control-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            margin-top: 30px;
        }
        .control-row {
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        .btn {
            width: 90px;
            height: 90px;
            font-size: 1.3em;
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
            margin-top: 30px;
            text-align: center;
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
        }
        .servo-section h3 {
            margin-bottom: 15px;
        }
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
            justify-content: center;
        }
        input[type="range"] {
            width: 250px;
            height: 10px;
            -webkit-appearance: none;
            background: #0f3460;
            border-radius: 5px;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 28px;
            height: 28px;
            background: #00b894;
            border-radius: 50%;
            cursor: pointer;
        }
        .angle-display {
            font-size: 1.4em;
            font-weight: bold;
            min-width: 70px;
            text-align: center;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            font-size: 1.1em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 Wheelcar Controller</h1>
        
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
    </script>
</body>
</html>
)rawliteral";

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
// Setup
// ===================
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println();
    Serial.println("Starting Wheelcar Controller...");
    
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
    delay(2);
}
