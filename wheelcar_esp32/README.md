# ESP32 Wheelcar Controller

ESP32-WROVER based web controller for kids power wheel car.

## Features

- **4 Relay Control**: Forward, Backward, Left, Right
- **Camera Streaming**: MJPEG live video from OV2640
- **Servo Control**: PWM control for additional servo motor
- **Web Interface**: Responsive HTML5 interface, mobile-friendly

## Hardware Requirements

- ESP32-WROVER-DEV (with PSRAM for camera)
- OV2640 Camera Module
- 4x Relay Module (5V, active LOW)
- 1x Servo Motor (SG90 or similar)
- WiFi connection

## Pin Configuration

### Relays (Active LOW)
| Function | GPIO |
|----------|------|
| Forward  | 12   |
| Backward | 13   |
| Left     | 14   |
| Right    | 15   |

### Servo
| Function | GPIO |
|----------|------|
| Servo    | 2    |

### Camera (ESP32-WROVER-KIT)
| Pin  | GPIO |
|------|------|
| XCLK | 21   |
| SIOD | 26   |
| SIOC | 27   |
| Y9   | 35   |
| Y8   | 34   |
| Y7   | 39   |
| Y6   | 36   |
| Y5   | 19   |
| Y4   | 18   |
| Y3   | 5    |
| Y2   | 4    |
| VSYNC| 25   |
| HREF | 23   |
| PCLK | 22   |

## Arduino IDE Setup

1. Install ESP32 Board Support:
   - Open Arduino IDE
   - Go to File > Preferences
   - Add to "Additional Boards Manager URLs":
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Go to Tools > Board > Boards Manager
   - Search for "esp32" and install

2. Install Required Libraries:
   - ESP32Servo (by Kevin Harrington)

3. Board Selection:
   - Board: "ESP32 Wrover Module"
   - Partition Scheme: "Huge App (3MB No OTA)"
   - Upload Speed: 921600

4. Configure WiFi:
   - Edit `wheelcar_esp32.ino`
   - Update `ssid` and `password` for your WiFi

5. Upload:
   - Connect ESP32 via USB
   - Select correct COM port
   - Click Upload

## Usage

1. Power on ESP32
2. Open Serial Monitor (115200 baud) to see assigned IP
3. Open browser and navigate to `http://<ESP32_IP>`
4. Use the web interface to control the car

## API Endpoints

| Endpoint | Parameters | Description |
|----------|------------|-------------|
| `/` | - | Main web interface |
| `/control` | `action=forward/backward/left/right/stop` | Control relays |
| `/servo` | `angle=0-180` | Set servo angle |
| `/stream` | - | MJPEG video stream |
| `/capture` | - | Single JPEG capture |

## Wiring Diagram

```
                    ESP32-WROVER-DEV
                   +-----------------+
        Relay 1 <-| GPIO12    GPIO2 |-> Servo
        Relay 2 <-| GPIO13    GPIO14|-> Relay 3
        Relay 4 <-| GPIO15    GPIOxx|-> Camera
                   |                 |
        Camera  <--| GPIO21,26,27... |
                   +-----------------+
                          |
                          v
                    Relay Module
                   +-------------+
      Remote Fwd <-| IN1   OUT1  |
      Remote Bwd <-| IN2   OUT2  |
      Remote Left <-| IN3   OUT3  |
      Remote Right<-| IN4   OUT4  |
                   +-------------+
```

## Troubleshooting

1. **Camera not working**:
   - Ensure you have ESP32-WROVER (with PSRAM), not ESP32-WROOM
   - Check camera ribbon cable connection
   - Try different camera resolution in code

2. **Relays not responding**:
   - Check relay module is powered with 5V
   - Verify active-LOW vs active-HIGH for your relay module
   - If relays are inverted, swap HIGH/LOW in code

3. **Cannot connect to WiFi**:
   - Check SSID and password
   - Ensure WiFi signal is strong enough
   - Try static IP configuration

## License

MIT License
