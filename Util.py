# -*- coding: utf8 -*-
import json
import re


def ConvertToMinute(time):
    hour = int(time[:2])
    minute = int(time[-2:])
    if hour < 2:
        hour += 24
    return hour * 60 + minute


def ConvertToHourMinute(minute):
    hour = minute // 60
    minute = minute - hour * 60
    if hour >= 24:
        hour -= 24
    return '{0:02d}:{1:02d}'.format(hour, minute)


def ReadJson(file):
    with file.open(encoding='UTF-8') as f:
        return json.load(f)


def GetNumber(string):
    return int(re.findall('\d+', string)[0])


class StationMapping:
    codeToName = {}
    nameToCode = {}
    
    def __init__(self, fileName):
        with open(fileName, 'r', encoding='utf-8') as f:
            stationData = json.load(f)
        for station in stationData:
            self.codeToName[station['Code']] = station['Name']
            self.nameToCode[station['Name']] = station['Code']
    
    def CodeToName(self, code):
        return self.codeToName[code]

    def NameToCode(self, name):
        return self.nameToCode[name]
