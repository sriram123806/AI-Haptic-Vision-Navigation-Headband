/*
  =====================================================================================
  AI Haptic Vision Navigation Headband — Phase 2: Dual Vibration Motor Control
  =====================================================================================
  Target Board : Arduino Nano (ATmega328P / CH340 clone)
  Upload FQBN  : arduino:avr:nano:cpu=atmega328   ← standard bootloader (NOT old)
  Baud Rate    : 115200 bps

  WIRING (do NOT connect D0/D1 during upload — disconnect after upload is done):
  ┌────────────┬────────────────────────────────────────────────────────────────────┐
  │ Arduino D5 │ → 470Ω resistor → 2N2222 Base (Left Motor transistor)             │
  │ Arduino D6 │ → 470Ω resistor → 2N2222 Base (Right Motor transistor)            │
  │ 2N2222 Col │ ← Left / Right vibration motor negative lead                      │
  │ Motor +    │ → Arduino 5V (or external 5V rail, shared GND with Arduino)       │
  │ 1N4001     │ Across each motor (cathode to 5V, anode to Collector) — flyback   │
  │ 2N2222 Emit│ → GND (shared with Arduino GND)                                   │
  │ Pin 13 LED │ Built-in LED — quick blink on every command receipt                │
  └────────────┴────────────────────────────────────────────────────────────────────┘

  LED-FIRST TEST (safe — no motors needed):
    Wire an LED + 220Ω resistor from D5 → GND and another from D6 → GND.
    Send L / R / S / C via test_arduino.py and watch the LEDs before adding motors.

  COMMAND PROTOCOL (unchanged from Phase 1 — Python side sends these):
  ┌─────┬──────────────────────────────────┬───────────────────────────────────┐
  │ CMD │ Python Navigation Command        │ Motor Action (Phase 2)            │
  ├─────┼──────────────────────────────────┼───────────────────────────────────┤
  │  L  │ move_left                        │ RIGHT motor pulses (obstacle left)│
  │  R  │ move_right                       │ LEFT motor pulses (obstacle right)│
  │  S  │ stop / slow_down / hazard        │ BOTH motors rapid-pulse (alert)   │
  │  C  │ move_straight / start_walking    │ ALL motors OFF (clear path)       │
  └─────┴──────────────────────────────────┴───────────────────────────────────┘

  NOTE: "obstacle on LEFT → steer RIGHT → RIGHT wrist vibrates (CMD=L)"
        This is intentional: the vibration tells the user WHICH WAY to turn.

  OUTGOING ACKNOWLEDGEMENTS (identical to Phase 1 — Python expects these):
    "HAPTIC_READY"  → sent on boot / reset
    "ACK:L"         → after processing L
    "ACK:R"         → after processing R
    "ACK:S"         → after processing S
    "ACK:C"         → after processing C
  =====================================================================================
*/

// ── Pin Definitions ──────────────────────────────────────────────────────────────────
const int LED_PIN        = 13;  // Built-in LED (visual feedback, always available)
const int LEFT_MOTOR_PIN = 5;   // D5 → 2N2222 → Left vibration motor
const int RIGHT_MOTOR_PIN= 6;   // D6 → 2N2222 → Right vibration motor

// ── Timing & Power Constants ─────────────────────────────────────────────────────────
const int SINGLE_PULSE_ON  = 250;   // 250 ms: Crisp, distinct haptic buzz (standard assistive duration)
const int SINGLE_PULSE_OFF = 60;    // 60 ms settle time between commands

const int ALERT_PULSE_ON   = 120;   // 120 ms burst for alert pulses
const int ALERT_PULSE_OFF  = 80;    // 80 ms gap between alert pulses
const int ALERT_REPEATS    = 2;     // 2 distinct alert bursts for S command

const int LED_BLINK_MS     = 60;    // Visual confirmation duration

// ─────────────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(LED_PIN,         OUTPUT);
  pinMode(LEFT_MOTOR_PIN,  OUTPUT);
  pinMode(RIGHT_MOTOR_PIN, OUTPUT);

  // Ensure everything starts OFF
  digitalWrite(LED_PIN,         LOW);
  digitalWrite(LEFT_MOTOR_PIN,  LOW);
  digitalWrite(RIGHT_MOTOR_PIN, LOW);

  // Startup blink sequence (3 quick blinks → board is alive)
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(80);
    digitalWrite(LED_PIN, LOW);
    delay(80);
  }

  // Announce ready — Python ArduinoController waits for this line
  Serial.println("HAPTIC_READY");
}

// ─────────────────────────────────────────────────────────────────────────────────────
void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    // Discard whitespace and line-terminator characters
    if (cmd == '\r' || cmd == '\n' || cmd == ' ') {
      return;
    }

    blinkLed(); // Visual confirmation on every valid command

    switch (cmd) {

      // ── L: Obstacle on LEFT → steer RIGHT → RIGHT wrist vibrates ──────────────
      case 'L':
        Serial.println("ACK:L");
        digitalWrite(LED_PIN, HIGH);
        pulseMotor(RIGHT_MOTOR_PIN, SINGLE_PULSE_ON);
        digitalWrite(LED_PIN, LOW);
        break;

      // ── R: Obstacle on RIGHT → steer LEFT → LEFT wrist vibrates ───────────────
      case 'R':
        Serial.println("ACK:R");
        digitalWrite(LED_PIN, HIGH);
        pulseMotor(LEFT_MOTOR_PIN, SINGLE_PULSE_ON);
        digitalWrite(LED_PIN, LOW);
        break;

      // ── S: STOP / Hazard → Alternating dual pulses (distinct alert, avoids current spike) ──
      case 'S':
        Serial.println("ACK:S");
        alertBothMotors();
        digitalWrite(LED_PIN, LOW);
        break;

      // ── C: Clear / Straight / Start walking → ALL motors OFF ───────────────────
      case 'C':
        Serial.println("ACK:C");
        stopAllMotors();
        digitalWrite(LED_PIN, LOW);
        break;

      default:
        Serial.print("ERR:UNKNOWN_");
        Serial.println(cmd);
        break;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────
// pulseMotor(): turn ONE motor ON firmly with full transistor saturation drive
// ─────────────────────────────────────────────────────────────────────────────────────
void pulseMotor(int pin, int durationMs) {
  digitalWrite(LED_PIN, HIGH);  // Turn on onboard Pin 13 LED
  digitalWrite(pin, HIGH);      // Full 5V drive to base resistor for maximum torque
  delay(durationMs);
  digitalWrite(pin, LOW);       // Turn motor OFF
  digitalWrite(LED_PIN, LOW);   // Turn off onboard Pin 13 LED
  delay(SINGLE_PULSE_OFF);      // Settle time
}

// ─────────────────────────────────────────────────────────────────────────────────────
// alertBothMotors(): alternating solid pulses between Left & Right
// ─────────────────────────────────────────────────────────────────────────────────────
void alertBothMotors() {
  for (int i = 0; i < ALERT_REPEATS; i++) {
    // Pulse Left Motor
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(LEFT_MOTOR_PIN, HIGH);
    delay(ALERT_PULSE_ON);
    digitalWrite(LEFT_MOTOR_PIN, LOW);
    digitalWrite(LED_PIN, LOW);

    delay(40);

    // Pulse Right Motor
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(RIGHT_MOTOR_PIN, HIGH);
    delay(ALERT_PULSE_ON);
    digitalWrite(RIGHT_MOTOR_PIN, LOW);
    digitalWrite(LED_PIN, LOW);

    delay(ALERT_PULSE_OFF);
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────
// stopAllMotors(): immediately cut power to both motors
// ─────────────────────────────────────────────────────────────────────────────────────
void stopAllMotors() {
  digitalWrite(LEFT_MOTOR_PIN, LOW);
  digitalWrite(RIGHT_MOTOR_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
}

// ─────────────────────────────────────────────────────────────────────────────────────
// blinkLed(): quick LED flash on pin 13 — visual command receipt confirmation
// ─────────────────────────────────────────────────────────────────────────────────────
void blinkLed() {
  digitalWrite(LED_PIN, HIGH);
  delay(LED_BLINK_MS);
  digitalWrite(LED_PIN, LOW);
}
