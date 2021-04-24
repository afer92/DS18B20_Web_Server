#!/usr/bin/python3
# Get room temperature and adjust parameters accordingly

import requests
from time import sleep
from datetime import datetime
import json
import math

# Fan parameters
fanIp = u'192.168.0.109'
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


def getDomoticz(url):
    response = requests.get(url)
    if response.status_code == 200:
        content = response.content.decode(u'utf8')
        return json.loads(content)[u'result']
    else:
        return None


def getRoomTemp(url):
    """
    Get room temperature from Domoticz
    """
    data = getDomoticz(url)
    if data:
        return data[0]
    else:
        return None


def getTempHisto(url):
    """
    Get fan temperature history from Domoticz
    """
    data = getDomoticz(url)
    if data:
        return data[-1:][0]
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


def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper


def main():
    nowTime = datetime.now()
    nowTimeStr = u'{}'.format(nowTime)[:19]
    newTemplow = None

    # get room temperature
    url = u'http://{}:{}/json.htm?type=devices&rid={}'.format(
        domoIp, domoPort, roomSensor)
    data = getRoomTemp(url)
    if data:
        roomTemp = data[u'Temp']
        newTemplow = float(roomTemp) + deltaTlow
    else:
        roomTemp = 0

    # get fan temperature last day min
    url = u'http://{}:{}/json.htm?type=graph&sensor=temp&idx={}&range=month'.format(
        domoIp, domoPort, tempIdx)
    data = getTempHisto(url)
    tempMoyToday = None
    if data:
        tempHistoMin = data[u'tm']
        url = u'http://{}:{}/json.htm?type=graph&sensor=temp&idx={}&range=day'.format(
            domoIp, domoPort, tempIdx)
        data = getDomoticz(url)
        if data:
            te = 0.0
            for info in data:
                te += info[u'te']
            tempMoyToday = truncate(te / len(data), 2)
    else:
        tempHistoMin = 0

    if tempHistoMin and roomTemp and tempMoyToday:
        newTemplow = ((roomTemp + 3 * tempHistoMin +
                      tempMoyToday) / 5) + deltaTlow
    elif tempHistoMin and tempMoyToday:
        newTemplow = ((3 * tempHistoMin + tempMoyToday) / 4) + deltaTlow
    elif tempHistoMin:
        newTemplow = float(tempHistoMin) + deltaTlow
    elif tempMoyToday:
        newTemplow = float(newTemplow) + deltaTlow

    if newTemplow:
        newTemplow = truncate(newTemplow, 2)

    print(u'{} Room temp: {} tempHistoMin : {} tempMoyToday: {} New templow: {}'.format(
        nowTimeStr, roomTemp, tempHistoMin, tempMoyToday, newTemplow))

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
