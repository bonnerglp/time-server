#include "config.h"
#include "version.h"
#include "../../generated/git_version.h"

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("Teensy telemetry firmware starting");
  Serial.print("Firmware version: ");
  Serial.println(FW_VERSION);
  Serial.print("Git version: ");
  Serial.println(GIT_VERSION);
}

void loop() {
  delay(1000);
}
