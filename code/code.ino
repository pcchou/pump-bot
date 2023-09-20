#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid     = "";
const char* password = "";
const char* host = "";

const int ledPin = 5;
bool ledState = LOW;
const int switchPin = 19;
bool switchState = LOW;

const unsigned long ontime = 1000 * (60 * 15 + 40);
unsigned long lastOn = 0;
int issueCount = 0;

WiFiServer server(8087);

bool onlineMsg() {
  HTTPClient http;

  char URL[40];
  sprintf(URL, "http://%s/online", host);
  http.begin(URL);
  int httpCode = http.GET();
  if (httpCode > 0) {
    Serial.println("Online message sent!");

    String payload = http.getString();
    Serial.println(httpCode);
    Serial.println(payload);
    http.end();

    if (payload == "False")
      return false;
    else
      return true;
  } else {
    Serial.println("Error on HTTP request");
  }

  return false;
}

void setup() {
    Serial.begin(115200);
    pinMode(ledPin, OUTPUT);      // set the LED pin mode

    delay(10);

    // We start by connecting to a WiFi network

    Serial.println();
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.persistent(false);
    WiFi.begin(ssid, password);

    int connCount = 0;
    int chars = 0;
    while (WiFi.status() != WL_CONNECTED && connCount < 50) {
        delay(200);
        Serial.print(".");
        chars++; connCount++;
        if (chars == 30) {
          Serial.print("\n");
          chars = 0;
        }
    }
    if (connCount >= 150) {
      Serial.println("Too many retries!");
      ESP.restart();
    }

    Serial.println("");
    Serial.println("WiFi connected.");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());

    ledState = onlineMsg();
    digitalWrite(ledPin, ledState);
    if (ledState == HIGH) {
      lastOn = millis();
      Serial.println("Previous on, recovering state.");
    } else {
      Serial.println("Previously off, nothing to do.");
    }

    if(WiFi.getSleep() == true) {
      WiFi.setSleep(false);
      Serial.println("WiFi Sleep is now deactivated.");
    }
    WiFi.setAutoReconnect(true);

    server.begin();

  switchState = digitalRead(switchPin);
  Serial.print("Switch initial state: ");
  Serial.println(switchState);
}

void timesUpMsg() {
  HTTPClient http;

  char URL[40];
  sprintf(URL, "http://%s/timesup", host);
  http.begin(URL);
  int httpCode = http.GET();
  if (httpCode > 0) {
    Serial.println("Time's up message sent!");
    String payload = http.getString();
    Serial.println(httpCode);
    Serial.println(payload);
  } else {
    Serial.println("Error on HTTP request");
  }

  http.end();
}

void switchMsg(bool status) {
  HTTPClient http;

  if (status == HIGH) {
    char URL[40];
    sprintf(URL, "http://%s/switchon", host);
    http.begin(URL);
  } else {
    char URL[40];
    sprintf(URL, "http://%s/switchoff", host);
    http.begin(URL);
  }
  int httpCode = http.GET();
  if (httpCode > 0) {
    Serial.println("Switch message sent!");
    String payload = http.getString();
    Serial.println(httpCode);
    Serial.println(payload);
  } else {
    Serial.println("Error on HTTP request");
  }

  http.end();

}

void loop() {
  if (millis() > lastOn + ontime && ledState == HIGH) {
    ledState = LOW;
    digitalWrite(ledPin, ledState);
    timesUpMsg();
    Serial.println("Time's up! State set to OFF.");
  }

  if ( WiFi.status() ==  WL_CONNECTED ){
    issueCount = 0;

    WiFiClient client = server.available();   // listen for incoming clients
    if (client) {                             // if you get a client,
      Serial.println("New Client.");           // print a message out the serial port
      String currentLine = "";                // make a String to hold incoming data from the client
      while (client.connected()) {            // loop while the client's connected
        if (client.available()) {             // if there's bytes to read from the client,
          char c = client.read();             // read a byte, then
          //Serial.write(c);                    // print it out the serial monitor
          if (c == '\n') {                    // if the byte is a newline character

            // if the current line is blank, you got two newline characters in a row.
            // that's the end of the client HTTP request, so send a response:
            if (currentLine.length() == 0) {
              // HTTP headers always start with a response code (e.g. HTTP/1.1 200 OK)
              // and a content-type so the client knows what's coming, then a blank line:
              client.println("HTTP/1.1 200 OK");
              client.println("Content-type:text/html");
              client.println();

              // the content of the HTTP response follows the header:
              //client.print("Click <a href=\"/H\">here</a> to turn the LED on pin 5 on.<br>");
              //client.print("Click <a href=\"/L\">here</a> to turn the LED on pin 5 off.<br>");
              if (ledState == HIGH) {
                char msg[20];
                sprintf(msg, "%d", millis() - lastOn);
                client.print(msg);
              } else {
                client.print("OFF");
              }
              // The HTTP response ends with another blank line:
              client.println();
              // break out of the while loop:
              break;
            } else {    // if you got a newline, then clear currentLine:
              currentLine = "";
            }
          } else if (c != '\r') {  // if you got anything else but a carriage return character,
            currentLine += c;      // add it to the end of the currentLine
          }

          // Check to see if the client request was "GET /H" or "GET /L":
          if (currentLine.endsWith("GET /H")) {
            ledState = HIGH;
            lastOn = millis();
            digitalWrite(ledPin, ledState);
            Serial.println(currentLine);
            Serial.println("Set pump to HIGH by HTTP request.");
          }
          if (currentLine.endsWith("GET /L")) {
            ledState = LOW;
            digitalWrite(ledPin, ledState);
            Serial.println(currentLine);
            Serial.println("Set pump to LOW by HTTP request.");
          }
        }
      }
      // close the connection:
      client.stop();
      Serial.println("Client Disconnected.");
    }
  } else {
    int retryCount = 0;
    WiFi.begin();
    Serial.println("Trying to reconnect to WiFi network...");
    while (WiFi.status() != WL_CONNECTED && retryCount < 20 ){
      delay( 100 );
      Serial.printf(".");
      ++retryCount;
    }
    if (WiFi.status() != WL_CONNECTED) {
      issueCount++;
      if (issueCount >= 15) {
        Serial.println("Impossible reconnecting to WiFi, rebooting device!");
        ESP.restart();
      }
    } else {
       Serial.println("CONNECTED!");
    }
  }

  if (digitalRead(switchPin) != switchState) {
    switchState = !switchState;
    if (ledState == HIGH) {
      ledState = LOW;
      digitalWrite(ledPin, ledState);
      switchMsg(ledState);
      Serial.println("Set pump to OFF by switch.");
    } else {
      ledState = LOW;
      //lastOn = millis();
      digitalWrite(ledPin, ledState);
      switchMsg(ledState);
      Serial.println("Set pump to OFF by switch.");
    }
    delay(1000);
  }
  delay(50);
}
