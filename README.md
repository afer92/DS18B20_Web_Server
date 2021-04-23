# DS18B20_Web_Server
Fan control with ESP-12E NodeMCU board, updatable parameters by web server.

## Description
This code was written to control the temperature under an induction hob. A basic web server is used to adjust control parameters.

Base code : [Temperature Controlled 4-Pin PWM-Fan with Arduino Nano](https://github.com/mariuste/Fan_Temp_Control)

## Install
Set variables :

```
float tempLow = 25; // lowest temperature
float tempHigh = 27; // max fan above this temperature
float hyteresis = 2; // fan start and stop at tempLow +- 1/2 hyteresis
int minDuty = 50; // lowest fan speed %
int maxDuty = 100; // highest fan speed %
```

## Usage
To display temperature and parameters:

```
http://module_IP
ESP8266 - Temperature
Temperature in Celsius: 22.75 °C
Temperature in Fahrenheit: 72.95 °F
Fan: 0 %
tempLow: 22.00 °C
tempHigh: 27.00 °C
minDuty: 20 %
maxDuty: 100 %
hysteresis: 2.00 °C
```

To set parameters:

```
http://module_IP/templow=22&temphigh=27&minduty=20&maxduty=100&&hyster=2
```

## Schema