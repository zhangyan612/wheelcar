#include "AudioTools.h"
#include "AudioTools/AudioCodecs/CodecMP3Helix.h"
#include "AudioTools/Communication/A2DPStream.h"
#include "SPIFFS.h"

// --- USER SETTINGS ---
const char *startFilePath = "/Meow.mp3"; 
const char* bt_speaker_name = "Polaroid P1"; 
// ---------------------

A2DPStream out;
MP3DecoderHelix decoder;
EncodedAudioStream dec(&out, &decoder);
File audioFile;

void setup() {
  Serial.begin(115200);
  delay(1000);

  // 1. Initialize SPIFFS
  if(!SPIFFS.begin(true)){
    Serial.println("!!! SPIFFS Mount Failed !!!");
    return;
  }
  Serial.println("\n--- SPIFFS Mounted ---");

  // 2. CHECK FILES ON CHIP
  Serial.println("Listing files on ESP32:");
  File root = SPIFFS.open("/");
  File file = root.openNextFile();
  bool fileFound = false;
  
  while(file){
    Serial.print("  FILE: ");
    Serial.print(file.name());
    Serial.print(" \t SIZE: ");
    Serial.println(file.size());
    
    if(String(file.name()) == String(startFilePath) || 
       String(file.name()) == String(startFilePath).substring(1)) {
      fileFound = true;
    }
    file = root.openNextFile();
  }
  Serial.println("----------------------");

  if(!fileFound) {
    Serial.println("!!! ERROR: Your MP3 file was NOT found!");
    Serial.println("Did you run 'ESP32 Sketch Data Upload'?");
    while(1);
  } else {
    Serial.println("SUCCESS: File found!");
  }

  // 3. Open the audio file
  audioFile = SPIFFS.open(startFilePath, "r");
  if(!audioFile || audioFile.isDirectory()){
    Serial.println("!!! Failed to open audio file for reading !!!");
    while(1);
  }
  Serial.print("File opened successfully, size: ");
  Serial.println(audioFile.size());

  // 4. Enable Audio Logging
  AudioLogger::instance().begin(Serial, AudioLogger::Warning);

  // 5. Start Bluetooth
  Serial.println("Starting A2DP...");
  auto cfg = out.defaultConfig(TX_MODE);
  cfg.name = bt_speaker_name;
  out.begin(cfg);

  // Wait for connection
  delay(3000);
  Serial.println("Bluetooth connected!");

  // 6. Configure decoder output
  dec.begin();
  
  Serial.println("Starting playback...");
}

void loop() {
  if(audioFile.available()){
    // Read data from file and write to decoder
    uint8_t buffer[512];
    int bytesRead = audioFile.read(buffer, sizeof(buffer));
    if(bytesRead > 0){
      dec.write(buffer, bytesRead);
    }
  } else {
    // File finished, rewind to loop
    Serial.println("Restarting playback...");
    audioFile.seek(0);
    delay(500);
  }
}
