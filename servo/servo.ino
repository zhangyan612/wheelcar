/*
 * ESP32 Dual Servo Web Server
 * Controls two servo motors via a web-based slider interface.
 * 
 * Dependencies:
 * - ESP32Servo library
 * - WiFi library (built-in)
 * - WebServer library (built-in)
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
// GPIO Configuration
// ===================
#define SERVO1_PIN 3
#define SERVO2_PIN 4

// ===================
// Global Objects
// ===================
WebServer server(80);
Servo servo1;
Servo servo2;

int angle1 = 100;
int angle2 = 90;

// Trigger State Machine Variables
bool triggerActive = false;
unsigned long triggerStartTime = 0;

// Torque Release Variables
unsigned long servo2MoveTime = 0;
bool servo2IsAttached = true;
const unsigned long RELEASE_DELAY = 3000; // 3 seconds

// Timing for Trigger (ms)
int triggerMoveTime = 800;   // Variable time to reach trigger position
int triggerPosition = 130;   // Single trigger position

// ===================
// HTML Web Interface
// ===================
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Servo Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #121212;
            color: #e0e0e0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: #1e1e1e;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            width: 90%;
            max-width: 400px;
            text-align: center;
        }
        h1 { color: #03dac6; margin-bottom: 2rem; }
        .control-group { margin-bottom: 2rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; }
        .slider {
            -webkit-appearance: none;
            width: 100%;
            height: 10px;
            border-radius: 5px;
            background: #333;
            outline: none;
            margin: 15px 0;
        }
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            background: #03dac6;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(3, 218, 198, 0.5);
        }
        .value-display {
            font-size: 1.2rem;
            font-weight: bold;
            color: #bb86fc;
        }
        .control-group { 
            margin-bottom: 2rem; 
            background: rgba(255,255,255,0.03); 
            padding: 1rem; 
            border-radius: 12px;
        }
        label { display: block; margin-bottom: 0.5rem; font-weight: bold; color: #a0a0a0; }
        .trigger-btn {
            background: linear-gradient(135deg, #03dac6 0%, #018786 100%);
            color: #121212;
            border: none;
            padding: 1.2rem;
            border-radius: 12px;
            font-size: 1.2rem;
            font-weight: 800;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 6px 20px rgba(3, 218, 198, 0.3);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 1rem 0;
        }
        .time-input-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 10px;
            background: #252525;
            padding: 8px 15px;
            border-radius: 8px;
        }
        .time-input {
            background: transparent;
            border: 1px solid #444;
            color: #03dac6;
            width: 60px;
            text-align: center;
            border-radius: 4px;
            font-size: 1rem;
            padding: 4px;
        }
        .trigger-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(3, 218, 198, 0.5);
        }
        .trigger-btn:active {
            transform: scale(0.92);
        }
        .status-small {
            font-size: 0.75rem;
            color: #707070;
            margin-top: 5px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>Advanced Servo Panel</h1>
        
        <div class="control-group">
            <label>Servo 1: Trigger & Position (Both Servos Move)</label>
            <input type="range" min="60" max="139" value="100" class="slider" id="servo1" oninput="updateServo(1, this.value)">
            <div class="value-display"><span id="val1">100</span>&deg;</div>
            
            <button class="trigger-btn" id="btn1" onclick="triggerServo1()">Fire Trigger</button>
            
            <div class="time-input-container">
                <span>Move Duration (ms):</span>
                <input type="number" id="triggerTime" class="time-input" value="800" onchange="updateTriggerTime(this.value)">
            </div>
            <div class="time-input-container">
                <span>Trigger Position (&deg;):</span>
                <input type="number" id="triggerPos" class="time-input" value="130" min="60" max="130" onchange="updateTriggerPosition(this.value)">
            </div>
            <div class="status-small">Moves both servos to trigger position</div>
        </div>

        <div class="status" id="status">System Online - Servo 2 Auto-Release Active</div>
    </div>

    <script>
        function updateTriggerTime(ms) {
            fetch(`/setTriggerTime?ms=${ms}`)
                .then(r => console.log("Time updated to " + ms));
        }

        function updateTriggerPosition(pos) {
            fetch(`/setTriggerPosition?pos=${pos}`)
                .then(r => console.log("Trigger position updated to " + pos));
        }

        function triggerServo1() {
            const btn = document.getElementById('btn1');
            btn.style.opacity = '0.7';
            btn.innerText = 'Firing...';
            
            fetch('/trigger')
                .then(response => {
                    setTimeout(() => {
                        btn.style.opacity = '1';
                        btn.innerText = 'Fire Trigger';
                    }, 1000);
                });
        }

        function updateServo(id, angle) {
            document.getElementById('val' + id).innerText = angle;
            fetch(`/servo?id=${id}&angle=${angle}`);
        }
    </script>
</body>
</html>
)rawliteral";

// ===================
// Request Handlers
// ===================
void handleRoot() {
    server.send(200, "text/html", index_html);
}

void handleTrigger() {
    triggerActive = true;
    triggerStartTime = millis();
    server.send(200, "text/plain", "Trigger Started");
    Serial.println("Trigger requested via web.");
}

void handleSetTriggerTime() {
    if (server.hasArg("ms")) {
        triggerMoveTime = server.arg("ms").toInt();
        server.send(200, "text/plain", "OK");
        Serial.printf("Trigger move time updated to: %d ms\n", triggerMoveTime);
    } else {
        server.send(400, "text/plain", "Missing MS");
    }
}

void handleSetTriggerPosition() {
    if (server.hasArg("pos")) {
        triggerPosition = constrain(server.arg("pos").toInt(), 0, 180);
        server.send(200, "text/plain", "OK");
        Serial.printf("Trigger position updated to: %d degrees\n", triggerPosition);
    } else {
        server.send(400, "text/plain", "Missing POS");
    }
}

void handleServo() {
    if (server.hasArg("id") && server.hasArg("angle")) {
        int id = server.arg("id").toInt();
        int angle = server.arg("angle").toInt();
        angle = constrain(angle, 0, 180);

        if (id == 1) {
            if (triggerActive) {
                server.send(409, "text/plain", "Trigger busy");
                return;
            }
            // Move both servos together when Servo 1 is adjusted
            servo1.write(angle);
            servo2.write(angle);
            angle1 = angle;
            angle2 = angle;
            
            // Reset servo2 release timer since it moved
            if (!servo2IsAttached) {
                servo2.attach(SERVO2_PIN, 500, 2400);
                servo2IsAttached = true;
                Serial.println("Servo 2 re-attached for movement.");
            }
            servo2MoveTime = millis();
            
            Serial.printf("Both servos moved to -> %d\n", angle);
        }
        server.send(200, "text/plain", "OK");
    } else {
        server.send(400, "text/plain", "Bad Request");
    }
}

// ===================
// Setup & Loop
// ===================
void setup() {
    Serial.begin(115200);
    // Wait for Serial Monitor to be ready (up to 5 seconds)
    // This is important for ESP32-S3 native USB
    while (!Serial && millis() < 5000) {
        delay(100);
    }
    Serial.println("\n--- ESP32-S3 Servo Controller Starting ---");
    
    // Attach servos
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    servo1.setPeriodHertz(50); // Standard 50hz servo
    servo2.setPeriodHertz(50);
    
    servo1.attach(SERVO1_PIN, 500, 2400); // Attach with typical pulse width range
    servo2.attach(SERVO2_PIN, 500, 2400);
    
    // Initial position
    servo1.write(angle1);
    servo2.write(angle2);

    // WiFi Connection
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Routes
    server.on("/", handleRoot);
    server.on("/servo", handleServo);
    server.on("/trigger", handleTrigger);
    server.on("/setTriggerTime", handleSetTriggerTime);
    server.on("/setTriggerPosition", handleSetTriggerPosition);

    server.begin();
    Serial.println("HTTP Server Started");
    
    // Initialize move time for Servo 2
    servo2MoveTime = millis();
}

void loop() {
    server.handleClient();
    
    unsigned long now = millis();

    // ===========================
    // Servo 1: Trigger Logic
    // ===========================
    if (triggerActive) {
        // Use the same logic as the slider for reliability
        // Move both servos together using the same approach as handleServo()
        
        // Re-attach servo2 if needed (same as slider logic)
        if (!servo2IsAttached) {
            servo2.attach(SERVO2_PIN, 500, 2400);
            servo2IsAttached = true;
            Serial.println("Servo 2 re-attached for trigger.");
        }
        
        // Send commands 5 times for reliability
        for (int i = 0; i < 5; i++) {
            servo1.write(triggerPosition);
            servo2.write(triggerPosition);
            delay(10); // Small delay between commands
        }
        
        // Update angle variables (same as slider logic)
        angle1 = triggerPosition;
        angle2 = triggerPosition;
        
        // Reset servo2 release timer (same as slider logic)
        servo2MoveTime = millis();
        
        triggerActive = false;
        Serial.printf("Trigger: Both servos moved to %d degrees (5x commands sent)\n", triggerPosition);
    }

    // ===========================
    // Servo 2: Torque Release Logic
    // ===========================
    if (servo2IsAttached && (now - servo2MoveTime > RELEASE_DELAY)) {
        servo2.detach();
        servo2IsAttached = false;
        Serial.println("Servo 2: Torque released (detach) after timeout.");
    }

    delay(2);
}