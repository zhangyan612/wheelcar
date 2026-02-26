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
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// ===================
// GPIO Configuration
// ===================
#define SERVO1_PIN 1
#define SERVO2_PIN 2

// ===================
// Global Objects
// ===================
WebServer server(80);
Servo servo1;
Servo servo2;

int angle1 = 90;
int angle2 = 90;

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
        .status {
            margin-top: 1rem;
            font-size: 0.8rem;
            color: #757575;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>Servo Control</h1>
        
        <div class="control-group">
            <label>Servo 1</label>
            <input type="range" min="0" max="180" value="90" class="slider" id="servo1" oninput="updateServo(1, this.value)">
            <div class="value-display"><span id="val1">90</span>&deg;</div>
        </div>

        <div class="control-group">
            <label>Servo 2</label>
            <input type="range" min="0" max="180" value="90" class="slider" id="servo2" oninput="updateServo(2, this.value)">
            <div class="value-display"><span id="val2">90</span>&deg;</div>
        </div>

        <div class="status" id="status">Connected to ESP32</div>
    </div>

    <script>
        function updateServo(id, angle) {
            document.getElementById('val' + id).innerText = angle;
            fetch(`/servo?id=${id}&angle=${angle}`)
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                })
                .catch(error => {
                    document.getElementById('status').innerText = 'Error: ' + error.message;
                    document.getElementById('status').style.color = '#cf6679';
                });
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

void handleServo() {
    if (server.hasArg("id") && server.hasArg("angle")) {
        int id = server.arg("id").toInt();
        int angle = server.arg("angle").toInt();
        angle = constrain(angle, 0, 180);

        if (id == 1) {
            servo1.write(angle);
            angle1 = angle;
            Serial.printf("Servo 1 -> %d\n", angle);
        } else if (id == 2) {
            servo2.write(angle);
            angle2 = angle;
            Serial.printf("Servo 2 -> %d\n", angle);
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

    server.begin();
    Serial.println("HTTP Server Started");
}

void loop() {
    server.handleClient();
    delay(2);
}
