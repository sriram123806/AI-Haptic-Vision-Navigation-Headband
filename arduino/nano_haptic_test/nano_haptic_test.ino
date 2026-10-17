/*
  =====================================================================================
  AI Haptic Vision Navigation Headband — Phase 1: Arduino Nano Serial Receiver Test
  =====================================================================================
  Target Board: Arduino Nano (ATmega328P / CH340 / FTDI)
  Baud Rate:    115200 bps
  
  PHASE 1 OBJECTIVE:
  - Test and verify bidirectional USB serial communication with the Python AI pipeline.
  - NO MOTORS OR TRANSISTORS CONNECTED in this phase.
  - Built-in LED (Pin 13) blinks briefly to give visual feedback on received commands.
  
  COMMAND PROTOCOL:
  Incoming (ASCII, newline-terminated):
    'L' -> Move Left Command
    'R' -> Move Right Command
    'S' -> Stop / Slow Down / Hazard Command
    'C' -> Clear / Move Straight / System Ready Command
    
  Outgoing Acknowledgement:
    "HAPTIC_READY" -> Broadcasted on board startup/reset
    "ACK:L"        -> Acknowledging Left command
    "ACK:R"        -> Acknowledging Right command
    "ACK:S"        -> Acknowledging Stop command
    "ACK:C"        -> Acknowledging Clear / Straight command
  =====================================================================================
*/

const int LED_PIN = 13; // Built-in LED on Arduino Nano (for visual status only)

void setup() {
  // Initialize USB serial at 115200 baud (must match Python config)
  Serial.begin(115200);
  
  // Set built-in LED as output for visual status
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Brief startup blink sequence (indicates boot)
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(60);
    digitalWrite(LED_PIN, LOW);
    delay(60);
  }

  // Announce ready status to the Python host
  Serial.println("HAPTIC_READY");
}

void loop() {
  // Check if serial data has arrived from Python
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    // Ignore carriage return or newline characters
    if (cmd == '\r' || cmd == '\n' || cmd == ' ') {
      return;
    }

    // Process single-character protocol commands
    switch (cmd) {
      case 'L': // Move Left
        blinkLed();
        Serial.println("ACK:L");
        break;

      case 'R': // Move Right
        blinkLed();
        Serial.println("ACK:R");
        break;

      case 'S': // Stop / Slow down / Hazard
        blinkLed();
        Serial.println("ACK:S");
        break;

      case 'C': // Clear path / Move straight / System ready
        blinkLed();
        Serial.println("ACK:C");
        break;

      default:
        // Report unrecognized character for debugging
        Serial.print("ERR:UNKNOWN_");
        Serial.println(cmd);
        break;
    }
  }
}

// Quick 25ms blink on pin 13 to visually confirm command receipt
void blinkLed() {
  digitalWrite(LED_PIN, HIGH);
  delay(25);
  digitalWrite(LED_PIN, LOW);
}
