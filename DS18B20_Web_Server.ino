/*********
  Rui Santos
  Complete project details at https://RandomNerdTutorials.com/home-automation-using-esp8266/
  Credits :
    Ruis and Sara Santos
      DS18B20 Digital Temperature Sensor
      DS18B20 Temperature Sensor Web Server
    Mariuste
      Temperature Controlled 4-Pin PWM-Fan with Arduino Nano
      https://github.com/mariuste/Fan_Temp_Control
*********/

// Including the ESP8266 WiFi library
#include <ESP8266WiFi.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Replace with your network details
const char* ssid = "Yours";
const char* password = "Yours";
// PWM sur GPIO4 D2
const int ledPin = 4;

// PWM output pin
const byte OC1B_PIN = ledPin;

// how frequently the main loop runs
const int tempSetInterval = 5000;

// state on/off of Fan
bool fanState = HIGH;

// current duty cycle
byte duty = 100;

// new duty cycle
byte newDuty = 100;

// temperature settings
float tempLow = 25;
float tempHigh = 27;
float hyteresis = 2;
int minDuty = 50;
int maxDuty = 100;

String newHostname = "FanPlaque";

// Data wire is plugged into pin D1 on the ESP8266 12-E - GPIO 5
#define ONE_WIRE_BUS 5

// Setup a oneWire instance to communicate with any OneWire devices (not just Maxim/Dallas temperature ICs)
OneWire oneWire(ONE_WIRE_BUS);

// Pass our oneWire reference to Dallas Temperature.
DallasTemperature DS18B20(&oneWire);
char temperatureCString[6];
char temperatureFString[6];

String header;
String tempLowString;
String tempHighString;
String minDutyString;
String maxDutyString;
String hyteresisString;
String dutyString;

// Web Server on port 80
WiFiServer server(80);

// Current time
unsigned long currentTime = millis();
// Previous time
unsigned long previousTime = 0;
// Define timeout time in milliseconds (example: 2000ms = 2s)
const long timeoutTime = 2000;

void computeDuty(float temp) {
  // newDuty = map(temp, tempLow, tempHigh, minDuty, maxDuty);
  float deltaTemp = tempHigh - tempLow;
  float deltaDuty = maxDuty - minDuty;
  float coef = deltaDuty / deltaTemp;
  newDuty = minDuty + (temp - tempLow) * coef;
}

//equivalent of analogWrite on pin 10
void setFan(int fan){
  Serial.print("Set fan :  ");
  Serial.print(fan);
  Serial.println("%");
  analogWrite(ledPin, fan);
  //float f = fan;
  //f = f / 100;
  //  f=f<0?0:f>1?1:f;
  //  OCR1B = (uint16_t)(320*f);
}



// setting PWM ############################################
void setPwmDuty() {
  if (duty == 0) {
    fanState = LOW;
  } else if (duty > 0) {
    fanState = HIGH;
  }

  setFan(duty);

}


// calculate new PWM ######################################
void tempToPwmDuty() {
  
  DS18B20.requestTemperatures();
  float temp = DS18B20.getTempCByIndex(0);
  
  //sensors.requestTemperatures();

  //float temp = sensors.getTempCByIndex(0);

  Serial.print(temp);
  Serial.print("°C, ");

  if (temp < tempLow) {
    // distinguish two cases to consider hyteresis
    if (fanState == HIGH) {
      if (temp < tempLow - (hyteresis / 2) ) {
        // fan is on, temp below threshold minus hysteresis -> switch off
        Serial.print("a, ");
        newDuty = 0;
      } else {
        // fan is on, temp not below threshold minus hysteresis -> keep minimum speed
        Serial.print("b, ");
        newDuty = minDuty;
      }
    } else if (fanState == LOW) {
      // fan is off, temp below threshold -> keep off
      Serial.print("c, ");
      newDuty = 0;
    }

  } else if (temp < tempHigh) {
    // distinguish two cases to consider hyteresis
    if (fanState == HIGH) {
      // fan is on, temp above threshold > control fan speed
      Serial.print("d, ");
      // newDuty = map(temp, tempLow, tempHigh, minDuty, maxDuty);
      computeDuty(temp);
    } else if (fanState == LOW) {
      if (temp > tempLow + (hyteresis / 2) ) {
        // fan is off, temp above threshold plus hysteresis -> switch on
        Serial.print("e, ");
        newDuty = minDuty;
      } else {
        // fan is on, temp not above threshold plus hysteresis -> keep off
        Serial.print("f, ");
        newDuty = 0;
      }
    }
  } else if (temp >= tempHigh) {
    // fan is on, temp above maximum temperature -> maximum speed
    Serial.print("g, ");
    newDuty = maxDuty;
  } else {
    // any other temperature -> maximum speed (this case should never occur)
    Serial.print("h, ");
    newDuty = maxDuty;
  }

  //set new duty
  duty = newDuty;

  Serial.print(duty);
    Serial.print("%, ");

  if (fanState==0) {Serial.println("OFF");} else {Serial.println("ON");}
  setPwmDuty();
}

void initWiFi() {
  analogWrite(ledPin, 100);
  WiFi.mode(WIFI_STA);
  WiFi.hostname(newHostname.c_str());
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi ..");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print('.');
    delay(1000);
  }
  analogWrite(ledPin, 20);
  Serial.println(WiFi.localIP());
  //The ESP8266 tries to reconnect automatically when the connection is lost
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
}

// only runs once on boot
void setup() {
  // Initializing serial port for debugging purposes
  Serial.begin(115200);
  delay(10);
  analogWriteRange(100);  // welcome message
  
  Serial.println("## Start of Program ##");
  Serial.println();

  Serial.println("# Connections #");

  Serial.println(" Temperature Sensor (VCC, Data, GND)");
  Serial.print(  "            Arduino: 3V3, D");
  Serial.print(ONE_WIRE_BUS);
  Serial.println("  , GND");
  Serial.println("            *additionally 4k7 pullup between VCC and Data");
  Serial.println();

  Serial.println(" 4-Pin Fan (GND, VCC, Sense, Control)");
  Serial.print(  "   Arduino: GND, 12V, n/C  , D");
  Serial.println(OC1B_PIN);
  Serial.println();

  Serial.println("# Settings #");
  Serial.println(" Below this temperature (minus half hysteresis) the fan");
  Serial.println(" shuts off. It enables again at this temperature plus half hysteresis:");
  Serial.print("  tempLow: "); Serial.print(tempLow); Serial.println("°C");

  
  Serial.println(" At and above this temperature the fan is at maximum speed: ");
  Serial.print("  tempHigh: "); Serial.print(tempHigh); Serial.println("°C");
  Serial.println();
  
  Serial.println(" Between these two temperatures the fan is regulated from");
  Serial.println(" the minimum fan speed to maximum fan speed");
  Serial.println();
  
  Serial.println(" Hysteresis to prevent frequent on/off switching at the threshold");
  Serial.print("  hyteresis: "); Serial.print(hyteresis); Serial.println("°C");
  Serial.println();
  
  Serial.println(" Minimum fan speed to prevent stalling");
  Serial.print("  minDuty: "); Serial.print(minDuty); Serial.println(" %");
  Serial.println();

  Serial.println(" Maximum fan speed to limit noise");
  Serial.print("  maxDuty: "); Serial.print(maxDuty); Serial.println(" %");
  Serial.println();

  Serial.println(" The fan speed is adjusted at the following interval:");
  Serial.print("  tempSetInterval: "); Serial.print(tempSetInterval); Serial.println(" ms");


  Serial.println(); delay(100);
  Serial.println(); delay(100);
  Serial.println(); delay(100);
  Serial.println(); delay(100);
  Serial.println(); delay(100);
  Serial.println(); delay(100);
  Serial.println(); delay(100);

  Serial.println("# Main Loop");
  Serial.println("(temperature, state, Duty Cycle, Fan On/Off)");
  Serial.println();

  DS18B20.begin(); // IC Default 9 bit. If you have troubles consider upping it 12. Ups the delay giving the IC more time to process the temperature measurement

  // Connecting to WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  initWiFi();

  // Starting the web server
  server.begin();
  Serial.println("Web server running. Waiting for the ESP IP...");
  delay(10000);
  
  analogWrite(ledPin, 5);

  // Printing the ESP IP address
  Serial.println(WiFi.localIP());
}

void getTemperature() {
  float tempC;
  float tempF;
  // analogWrite(ledPin, 0);
  do {
    DS18B20.requestTemperatures();
    tempC = DS18B20.getTempCByIndex(0);
    dtostrf(tempC, 2, 2, temperatureCString);
    tempF = DS18B20.getTempFByIndex(0);
    dtostrf(tempF, 3, 2, temperatureFString);
    delay(100);
  } while (tempC == 85.0 || tempC == (-127.0));
}

String getParam(String name) {
  String result;
  result = "";
  result = header.substring(header.indexOf(name));
  result = result.substring(0, result.indexOf('\n'));
  // Serial.println(result);
  result = result.substring(0, result.indexOf(' '));
  // Serial.println(result);
  if(result.indexOf("&") >= 0) {
    result = result.substring(0, result.indexOf('&'));
    // Serial.println(result);
  }
  result = result.substring(result.indexOf('=')+1);
  // Serial.println(result);
  return result;
}

// runs over and over again
void loop() {
  // Listenning for new clients
  WiFiClient client = server.available();
  tempToPwmDuty();

  if (client) {
    currentTime = millis();
    previousTime = currentTime;
    Serial.println("New client");
    // bolean to locate when the http request ends
    boolean blank_line = true;
    while (client.connected() && currentTime - previousTime <= timeoutTime) {
      currentTime = millis();
      if (client.available()) {
        char c = client.read();
        header += c;

        if (c == '\n' && blank_line) {
            if(header.indexOf("templow") >= 0) {
                tempLow = getParam("templow").toFloat();
            }
            if(header.indexOf("temphigh") >= 0) {
                tempHigh = getParam("temphigh").toFloat();
            }
            if(header.indexOf("minduty") >= 0) {
                minDuty = getParam("minduty").toFloat();
            }
            if(header.indexOf("maxduty") >= 0) {
                maxDuty = getParam("maxduty").toFloat();
            }
            if(header.indexOf("hyster") >= 0) {
                hyteresis = getParam("hyster").toFloat();
            }
            getTemperature();
            client.println("HTTP/1.1 200 OK");
            client.println("Content-Type: text/html");
            client.println("Connection: close");
            client.println();
            // your actual web page that displays temperature
            client.println("<!DOCTYPE HTML>");
            client.println("<html><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"></head>");
            client.println("<body><h1>ESP8266 - Temperature</h1><h3>Temperature in Celsius: ");
            client.println(temperatureCString);
            client.println("&deg;C</h3><h3>Temperature in Fahrenheit: ");
            client.println(temperatureFString);
            client.println("&deg;F</h3><h3>Fan: ");
            client.println(String(duty));
            client.print("&percnt;");
            client.println("</h3><h3>tempLow: ");
            tempLowString = String(tempLow);
            client.println(tempLowString);
            client.println("&deg;C</h3><h3>tempHigh: ");
            tempHighString = String(tempHigh);
            client.println(tempHighString);
            client.println("&deg;C</h3><h3>minDuty: ");
            minDutyString = String(minDuty);
            client.println(minDutyString);
            client.println("&percnt;</h3><h3>maxDuty: ");
            maxDutyString = String(maxDuty);
            client.println(maxDutyString);
            client.println("&percnt;</h3><h3>hysteresis: ");
            hyteresisString = String(hyteresis);
            client.println(hyteresisString);
            client.println("&deg;C</h3></body></html>");
            header = "";
            break;
        }
        if (c == '\n') {
          // when starts reading a new line
          blank_line = true;
        }
        else if (c != '\r') {
          // when finds a character on the current line
          blank_line = false;
        }
      }
    }
    // closing the client connection
    delay(1);
    client.stop();
    Serial.println("Client disconnected.");
  }
}
