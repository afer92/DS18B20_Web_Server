#!/usr/bin/python3
# Get room temperature and adjust parameters accordingly

import requests
from time import sleep
from datetime import datetime
import json
import math
import re

# Fan parameters

# Temperature for device 0 283C7407D6013C6B: Temp C: 25.31 controlleur
# Temperature for device 1 28569EED4F2001B2: Temp C: 22.69 plaques
# Temperature for device 2 2813F307D6013C63: Temp C: 22.44 cuisine
# fanIp = u'192.168.0.109'
fanIp = u'192.168.0.58'
fanPort = u'80'
tPlaques = u'28569EED4F2001B2'
tCuisine = u'2813F307D6013C63'
tControl = u'283C7407D6013C6B'

deltaTlow = 1  # tempLow = roomTemp + deltaTlow
deltaThigh = 2  # (tempHigh - tempLow) >= deltaThigh
minDuty2set = 20
maxDuty2set = 100
hyster2set = 0.5

# Domoticz parameters


domoIp = u'192.168.0.50'
domoPort = u'8080'
tempPlaquesIdx = 977  # Temperature sous plaques
fanDutyIdx = 976  # Commande du ventilateur en %
fanRPMIdx = 978  # Vitesse du ventilateur
tempCuIdx = 979  # Temperature cuisine
tempNodeIdx = 980  # Temperature controleur
tempRoomIdx = 844  # Temperature autre piece

dataDictDomo = {u'tempPlaques': tempPlaquesIdx,
                u'fanDuty': fanDutyIdx,
                u'fanRPM': fanRPMIdx,
                u'tempCu': tempCuIdx,
                u'tempNode': tempNodeIdx,
                u'tempRoom': tempRoomIdx,
                }

#
#  Node Mcu
#


def getDataNode(url):
    '''
    Get Node Mcu infos
    '''
    dataDict = {u'Temperature in Celsius': u'temp',
                u'Fan': u'percentFan',
                u'tempLow': u'tempLow',
                u'tempHigh': u'tempHigh',
                u'minDuty': u'minDuty',
                u'maxDuty': u'maxDuty',
                u'hysteresis': u'hysteresis',
                u'RPM': u'rpmFan',
                u'addressCtrl': u'addressCtrl',
                }

    def getOneData(line, str2find) -> dict:
        if str2find in line:
            return line.split(str2find)[1].split(u'\r\n')[0]
        else:
            return None

    data = {}
    regTemp = re.compile(
        '.*Temperature for device ([0-9]+) ([0-9a-fA-F]+): Temp C: ([0-9]+\.[0-9]+).*')
    # regTemp = re.compile('.*Temperature for device ([0-9]+) ([0-9a-fA-F]+).*')
    response = requests.get(url)
    if response.status_code == 200:
        data = {}
        data[u'sensors'] = {}
        html = response.content.decode(u'utf8')
        paragraphs = html.split(u'</h3>')
        for paragraph in paragraphs:
            for key, name in dataDict.items():
                oneData = getOneData(paragraph, key + u': \r\n')
                if oneData:
                    if name in ('rpmFan', 'addressCtrl'):
                        data[name] = int(oneData)
                    else:
                        data[name] = float(oneData)
            # Temperature for device 0 283C7407D6013C6B: Temp C: 34.00
            regFind = regTemp.findall(paragraph)
            if len(regFind) > 0:
                data[u'sensors'][regFind[0][1]] = {}
                data[u'sensors'][regFind[0][1]][u'num'] = int(regFind[0][0])
                data[u'sensors'][regFind[0][1]][u'temp'] = float(regFind[0][2])
        return data
    else:
        return None


def computeSetpoints(node: dict, domo: dict) -> dict:
    """
    Compute setpoints from node and domoticz data
    """
    # url = u'http://{}:{}/templow={}&temphigh={}&minduty={}&maxduty={}&hyster={}&addressCtrl={}'
    data = {}
    if node is None:
        return {}
    sensors = node['sensors']
    if len(sensors) == 0:
        return {}
    if len(sensors) == 1:
        addressCtrl = 0
    else:
        if tPlaques in sensors.keys():
            addressCtrl = sensors[tPlaques][u'num']
    data[u'addressCtrl'] = addressCtrl
    data[u'minduty'] = minDuty2set
    data[u'maxduty'] = maxDuty2set
    data[u'hyster'] = hyster2set

    # compute templow

    if tCuisine in sensors.keys():
        templow = sensors[tCuisine][u'temp'] + 0.5
        temphigh = templow + deltaThigh
        data[u'templow'] = truncate(templow, 2)
        data[u'temphigh'] = truncate(temphigh, 2)
    elif domo is not None:
        if 'tempHistoMin' in domo.keys():
            templow = domo['tempHistoMin'] + 2.0
            temphigh = templow + deltaThigh
            data[u'templow'] = truncate(templow, 2)
            data[u'temphigh'] = truncate(temphigh, 2)
        elif 'tempRoom' in domo.keys():
            templow = domo['tempRoom'] + 2.0
            temphigh = templow + deltaThigh
            data[u'templow'] = truncate(templow, 2)
            data[u'temphigh'] = truncate(temphigh, 2)

    return data


def sendSetpoints(setpoints):
    print(u'setpoints:\r\n', setpoints)
    if setpoints:
        params = []
        for key, value in setpoints.items():
            params.append(u'{}={}'.format(key, value))
        paramsStr = u'&'.join(params)
        url = u'http://{}:{}/{}'.format(fanIp, fanPort, paramsStr)
        response = requests.get(url)
        if response.status_code == 200:
            return True
    return False


#
#  Domoticz
#


def getDomoticz(url):
    response = requests.get(url)
    if response.status_code == 200:
        content = response.content.decode(u'utf8')
        return json.loads(content)[u'result']
    else:
        return None


def getDataDomo(domoIp, domoPort):
    '''
    Get domoticz infos
    '''
    data = {}

    if domoIp:
        urlbase = u'http://{}:{}/json.htm?type=devices&rid={}'
        for name, idx in dataDictDomo.items():
            if idx:
                url = urlbase.format(domoIp, domoPort, idx)
                value = getDomoticz(url)
                if value:
                    if name in (u'fanDuty', u'fanRPM'):
                        if name == u'fanDuty':
                            data[name] = float(value[0]['Data'][:-1])
                        else:
                            data[name] = int(value[0]['Data'].split(u' ')[0])
                    else:
                        data[name] = value[0][u'Temp']

        # get fan temperature last day min
        if tempPlaquesIdx is None:
            return data
        url = u'http://{}:{}/json.htm?type=graph&sensor=temp&idx={}&range=month'.format(
            domoIp, domoPort, tempPlaquesIdx)
        dataHisto = getDomoticz(url)
        if dataHisto:
            dataHisto = dataHisto[-1:][0]
        tempMoyToday = None
        if dataHisto:
            tempHistoMin = dataHisto[u'tm']
            url = u'http://{}:{}/json.htm?type=graph&sensor=temp&idx={}&range=day'.format(
                domoIp, domoPort, tempPlaquesIdx)
            dataHisto = getDomoticz(url)
            if dataHisto:
                te = 0.0
                for info in dataHisto:
                    te += info[u'te']
                tempMoyToday = truncate(te / len(dataHisto), 2)
        else:
            tempHistoMin = 0
        data[u'tempHistoMin'] = tempHistoMin
        return data
    else:
        return None


def updateDomo(data):
    """
    Set infos in Domoticz for logging
    """
    if data:
        # /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=PERCENTAGE
        # /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=TEMP
        urlBase = u'http://{}:{}/'.format(domoIp, domoPort)
        for name, idx in dataDictDomo.items():
            if name in (u'tempPlaques', u'tempCu', u'tempNode') and idx:
                url = u'{}json.htm?type=command&param=udevice&idx={}&nvalue=0&svalue={}'
                if name == u'tempPlaques':
                    value = data['sensors'][tPlaques]['temp']
                elif name == u'tempCu':
                    value = data['sensors'][tCuisine]['temp']
                elif name == u'tempNode':
                    value = data['sensors'][tControl]['temp']
                url = url.format(urlBase, idx, value)
            elif name in (u'fanDuty', u'fanRPM') and idx:
                url = u'{}json.htm?type=command&param=udevice&idx={}&nvalue=0&svalue={}'
                if name == u'fanDuty':
                    value = data['percentFan']
                elif name == u'fanRPM':
                    value = data['rpmFan']
                url = url.format(urlBase, idx, value)
            else:
                url = None
            if url:
                response = requests.get(url)
                if response.status_code != 200:
                    print(url)
                    print(response)

#
#  Utils
#


def truncate(number, digits) -> float:
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

#
#  Main
#


def main():
    nowTime = datetime.now()
    nowTimeStr = u'{}'.format(nowTime)[:19]
    tempControl = 0.0
    tempCuisine = 0.0
    tempPlaques = 0.0
    addressCtrl2set = 0

    # get data fan
    url = u'http://{}:{}/'.format(fanIp, fanPort)
    data = getDataNode(url)
    if data:
        print(u'node:\r\n', data)
        if tPlaques in data[u'sensors'].keys():
            tempPlaques = float(data[u'sensors'][tPlaques][u'temp'])
            addressCtrl2set = int(data[u'sensors'][tPlaques][u'num'])
        if tCuisine in data[u'sensors'].keys():
            tempCuisine = float(data[u'sensors'][tCuisine][u'temp'])
        if tControl in data[u'sensors'].keys():
            tempControl = float(data[u'sensors'][tControl][u'temp'])
        print(u'\r\nPlaques({}): {} °C Cuisine: {} °C Controleur: {} °C\r\n'.format(addressCtrl2set,
                                                                                    tempPlaques,
                                                                                    tempCuisine,
                                                                                    tempControl))
    else:
        return

    # get data domoticz
    dataDz = getDataDomo(domoIp, domoPort)
    print(u'domoticz:\r\n', dataDz)

    # Calculation of setpoints
    setpoints = computeSetpoints(data, dataDz)
    # print(setpoints)

    # Send setpoints
    if sendSetpoints(setpoints):
        print(nowTimeStr, 'set parameters ok')
    else:
        print(nowTimeStr, 'set parameters error')

    # Update sensors into domoticz
    updateDomo(data)


if __name__ == '__main__':
    main()
    exit(0)
