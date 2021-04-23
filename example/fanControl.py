#!/usr/bin/python3
# Get room temperature and adjust parameters accordingly

import requests
from time import sleep
from datetime import datetime
import json

# Fan parameters
fanIp = u'192.168.0.115'
fanPort = u'80'
# Domoticz parameters
domoIp = u'192.168.0.50'
domoPort = u'8080'
tempIdx = 977
fanIdx = 976
roomSensor = 844
# Control parameters
deltaTlow = 1  # tempLow = roomTemp + deltaTlow
deltaThigh = 2  # (tempHigh - tempLow) >= deltaThigh


def getData(url):
    '''
    Get fan infos
    '''
    response = requests.get(url)
    if response.status_code == 200:
        html = response.content.decode(u'utf8')
        parts = html.split(u'Temperature in Celsius: \r\n')[1]
        temp = parts.split(u'\r\n')[0]
        parts = html.split(u'Fan: \r\n')[1]
        fan = parts.split(u'\r\n')[0]
        parts = html.split(u'tempLow: \r\n')[1]
        tempLow = parts.split(u'\r\n')[0]
        parts = html.split(u'tempHigh: \r\n')[1]
        tempHigh = parts.split(u'\r\n')[0]
        parts = html.split(u'minDuty: \r\n')[1]
        minDuty = parts.split(u'\r\n')[0]
        parts = html.split(u'maxDuty: \r\n')[1]
        maxDuty = parts.split(u'\r\n')[0]
        parts = html.split(u'hysteresis: \r\n')[1]
        hysteresis = parts.split(u'\r\n')[0]
        return {'temp': temp, 'fan': fan,
                'tempLow': tempLow, 'tempHigh': tempHigh,
                'minDuty': minDuty, 'maxDuty': maxDuty,
                'hysteresis': hysteresis}
    else:
        return None


def getRoomTemp(url):
    """
    Get room temperature from Domoticz
    """
    response = requests.get(url)
    if response.status_code == 200:
        content = response.content.decode(u'utf8')
        return json.loads(content)[u'result'][0]
    else:
        return None


def setsensors(data):
    """
    Set infos in Domoticz for logging
    """
    # /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=PERCENTAGE
    # /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=TEMP
    urlBase = u'http://{}:{}/'.format(domoIp, domoPort)
    urlTemp = u'{}json.htm?type=command&param=udevice&idx={}&nvalue=0&svalue={}'
    urlTemp = urlTemp.format(urlBase, tempIdx, data[u'temp'])
    urlPercent = u'{}json.htm?type=command&param=udevice&idx={}&nvalue=0&svalue={}'
    urlPercent = urlPercent.format(urlBase, fanIdx, data[u'fan'])
    response = requests.get(urlTemp)
    if response.status_code != 200:
        print(response)
    response = requests.get(urlPercent)
    if response.status_code != 200:
        print(response)
    # print(urlTemp)
    # print(urlPercent)


def main():
    nowTime = datetime.now()
    nowTimeStr = u'{}'.format(nowTime)[:19]

    # get room temperature
    url = u'http://{}:{}/json.htm?type=devices&rid={}'.format(
        domoIp, domoPort, roomSensor)
    data = getRoomTemp(url)
    if data:
        roomTemp = data[u'Temp']
        newTemplow = float(roomTemp) + deltaTlow
        print(u'{} Room temp: {} New templow: {}'.format(
            nowTimeStr, roomTemp, newTemplow))
    else:
        roomTemp = 0

    # get data fan
    url = u'http://{}:{}/'.format(fanIp, fanPort)
    data = getData(url)
    if data:
        if roomTemp > 0:
            tempHigh = float(data[u'tempHigh'])
            if newTemplow > tempHigh:
                tempHigh = newTemplow + deltaThigh

            url = u'http://{}:{}/templow={}&temphigh={}'.format(
                fanIp, fanPort, newTemplow, tempHigh)
            getData(url)

        # set domoticz sensors
        setsensors(data)
        print(u'{} {}'.format(nowTimeStr, data))


if __name__ == '__main__':
    main()
    exit(0)
