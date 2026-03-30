/*
 * ESP32 WROVER Feetech Servo Web Controller
 * Controls two Feetech serial servos (ID 1 and 2) via web interface
 * 
 * Hardware:
 * - ESP32 WROVER Dev Module
 * - Feetech Serial Servos (SCS/STS series)
 * - TX/RX connection at 1M baud
 * 
 * No external libraries needed - implements Feetech protocol directly
 */

#include <WiFi.h>
#include <WebServer.h>

// ===================
// WiFi Configuration
// ===================
const char* ssid = "Verizon_YGCW99";
const char* password = "yon4-ewer-holly";

// ===================
// Serial Configuration
// ===================
#define S_RXD 16  // Connect to servo TX
#define S_TXD 17  // Connect to servo RX
#define SERVO_BAUD 1000000  // 1M baud

// ===================
// Servo Configuration
// ===================
#define SERVO_ID_1 1
#define SERVO_ID_2 2

// ===================
// Global Objects
// ===================
WebServer server(80);

int currentAngle = 512;  // Feetech servos typically use 0-1023 range (512 = center)

// ===================
// Feetech Protocol Functions
// ===================

// Calculate checksum for Feetech protocol
byte calculateChecksum(byte* packet, int length) {
    int sum = 0;
    for(int i = 2; i < length - 1; i++) {
        sum += packet[i];
    }
    return ~(sum & 0xFF);
}

// Write position to a single servo
void writeServoPosition(byte id, int position, int speed = 2400, byte acc = 50) {
    byte packet[13];
    packet[0] = 0xFF;  // Header
    packet[1] = 0xFF;  // Header
    packet[2] = id;    // Servo ID
    packet[3] = 9;     // Length (parameters + checksum)
    packet[4] = 0x03;  // Write instruction
    packet[5] = 0x2A;  // Goal position address (42 decimal)
    
    // Position (2 bytes, little endian)
    packet[6] = position & 0xFF;
    packet[7] = (position >> 8) & 0xFF;
    
    // Speed (2 bytes, little endian)
    packet[8] = speed & 0xFF;
    packet[9] = (speed >> 8) & 0xFF;
    
    // Acceleration
    packet[10] = acc;
    
    // Checksum
    packet[11] = calculateChecksum(packet, 12);
    
    // Send packet
    Serial1.write(packet, 12);
    delay(2);
}

// Sync write to multiple servos (both move simultaneously)
void syncWritePosition(int position, int speed = 2400, byte acc = 50) {
    // Sync Write packet for 2 servos
    byte packet[20];
    packet[0] = 0xFF;  // Header
    packet[1] = 0xFF;  // Header
    packet[2] = 0xFE;  // Broadcast ID
    packet[3] = 16;    // Length
    packet[4] = 0x83;  // Sync Write instruction
    packet[5] = 0x2A;  // Starting address (Goal Position)
    packet[6] = 5;     // Data length per servo (pos_L, pos_H, speed_L, speed_H, acc)
    
    // Servo 1 data
    packet[7] = SERVO_ID_1;
    packet[8] = position & 0xFF;
    packet[9] = (position >> 8) & 0xFF;
    packet[10] = speed & 0xFF;
    packet[11] = (speed >> 8) & 0xFF;
    packet[12] = acc;
    
    // Servo 2 data
    packet[13] = SERVO_ID_2;
    packet[14] = position & 0xFF;
    packet[15] = (position >> 8) & 0xFF;
    packet[16] = speed & 0xFF;
    packet[17] = (speed >> 8) & 0xFF;
    packet[18] = acc;
    
    // Checksum
    packet[19] = calculateChecksum(packet, 20);
    
    // Send packet
    Serial1.write(packet, 20);
    delay(2);
}

// ===================
// HTML Web Interface
// ===================
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>Feetech Servo Control</title>
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
        .control-group { 
            margin-bottom: 2rem;
            background: rgba(255,255,255,0.03); 
            padding: 1.5rem; 
            border-radius: 12px;
        }
        label { 
            display: block; 
            margin-bottom: 1rem; 
            font-weight: bold; 
            color: #a0a0a0;
            font-size: 1.1rem;
        }
        .slider {
            -webkit-appearance: none;
            width: 100%;
            height: 12px;
            border-radius: 6px;
            background: #333;
            outline: none;
            margin: 20px 0;
        }
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: linear-gradient(135deg, #03dac6 0%, #018786 100%);
            cursor: pointer;
            box-shadow: 0 0 15px rgba(3, 218, 198, 0.6);
        }
        .value-display {
            font-size: 2rem;
            font-weight: bold;
            color: #03dac6;
            margin: 1rem 0;
            text-shadow: 0 0 10px rgba(3, 218, 198, 0.3);
        }
        .info {
            font-size: 0.85rem;
            color: #707070;
            margin-top: 1rem;
        }
        .status {
            margin-top: 2rem;
            padding: 1rem;
            background: rgba(3, 218, 198, 0.1);
            border-radius: 8px;
            color: #03dac6;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🤖 Feetech Servo Control</h1>
        
        <div class="control-group">
            <label>Dual Servo Position</label>
            <input type="range" min="0" max="1023" value="512" class="slider" id="servo" oninput="updateServos(this.value)">
            <div class="value-display"><span id="val">512</span></div>
            <div class="info">Range: 0-1023 (512 = center)</div>
            <div class="info">Both servos move simultaneously</div>
        </div>

        <div class="status" id="status">System Online - Servos ID 1 & 2</div>
    </div>

    <script>
        function updateServos(position) {
            document.getElementById('val').innerText = position;
            fetch(`/servo?pos=${position}`)
                .then(response => response.text())
                .then(data => {
                    console.log('Servo response:', data);
                })
                .catch(err => console.error('Error:', err));
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
    if (server.hasArg("pos")) {
        int position = server.arg("pos").toInt();
        position = constrain(position, 0, 1023);
        
        // Move both servos simultaneously using sync write
        syncWritePosition(position, 2400, 50);
        
        currentAngle = position;
        
        Serial.printf("Servos moved to position: %d\n", position);
        server.send(200, "text/plain", "OK");
    } else {
        server.send(400, "text/plain", "Missing position parameter");
    }
}

// ===================
// Setup & Loop
// ===================
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n--- ESP32 Feetech Servo Controller ---");
    
    // Initialize servo serial communication
    Serial1.begin(SERVO_BAUD, SERIAL_8N1, S_RXD, S_TXD);
    delay(500);
    
    Serial.println("Servo serial initialized at 1M baud");
    Serial.printf("TX Pin: %d, RX Pin: %d\n", S_TXD, S_RXD);
    
    // Move servos to center position
    Serial.println("Moving servos to center position (512)...");
    syncWritePosition(512, 1500, 50);
    delay(1000);
    
    // WiFi Connection
    Serial.println("\nInitializing WiFi...");
    Serial.printf("SSID: %s\n", ssid);
    
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);
    
    WiFi.begin(ssid, password);
    Serial.print("Connecting");
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n\n========================================");
        Serial.println("WiFi Connected!");
        Serial.print("Web Interface: http://");
        Serial.println(WiFi.localIP());
        Serial.println("========================================\n");
    } else {
        Serial.println("\n\n========================================");
        Serial.println("WiFi Connection FAILED!");
        Serial.println("Check credentials and signal strength");
        Serial.printf("WiFi Status: %d\n", WiFi.status());
        Serial.println("========================================\n");
        Serial.println("Continuing without WiFi...");
    }

    // Setup web server routes
    server.on("/", handleRoot);
    server.on("/servo", handleServo);

    server.begin();
    Serial.println("✓ Web server ready");
    Serial.println("✓ Servo control available");
}

void loop() {
    server.handleClient();
    delay(2);
}
