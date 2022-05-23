# -*- coding: utf8 -*-
import json
from os.path import join
from pathlib import Path
from bisect import bisect
from collections import namedtuple
import Util
from Util import ConvertToHourMinute

# configuration
inputDir = 'output/Stations'
outputDir = 'output/Lines'

lineCodes = ['R', 'G', 'O', 'BL']
# 0: 小到大
directionMapping = {
    '往R22北投站、R28淡水站': ('淡水', 0),
    '往R28淡水站': ('淡水', 0),
    '往R05大安站、R02象山站': ('象山', 1),
    '往R02象山站': ('象山', 1),

    '往G19松山站': ('松山', 0),
    '往G08台電大樓站、G01新店站': ('新店', 1),
    '往G01新店站': ('新店', 1),

    '往O54蘆洲站': ('蘆洲、迴龍', 0),
    '往O54蘆洲站、O21迴龍站': ('蘆洲、迴龍', 0),
    '往O21迴龍站': ('蘆洲、迴龍', 0),
    '往O01南勢角站': ('南勢角', 1),

    '往BL23南港展覽館站': ('南港展覽館', 0),
    '往BL05亞東醫院站、BL01頂埔站': ('頂埔', 1),
    '往BL01頂埔站': ('頂埔', 1)
}

lastAppend = {
    'R27': ('R28', 3),  # 淡水
    'R03': ('R02', 2),  # 象山
    'R21': ('R22', 2),  # 北投
    'R06': ('R05', 2),  # 大安

    'BL22': ('BL23', 2),  # 南港展覽館
    'BL02': ('BL01', 3),  # 頂埔
    'BL20': ('BL21', 2),  # 昆陽
    'BL06': ('BL05', 3),  # 亞東醫院

    'G18': ('G19', 3),  # 松山
    'G02': ('G01', 2),  # 新店
    'G09': ('G08', 2),  # 台電大樓

    'O02': ('O01', 2),  # 南勢角
    'O53': ('O54', 2),  # 蘆洲
    'O20': ('O21', 3)  # 迴龍
}

additionalTimeThreshold = {
    ('O07', 'O06' ): (1, None),
    ('O06', 'O05' ): (2, None),
    ('O05', 'O04' ): (2, None),
    ('R08', 'R07' ): (2, None),
    ('BL04','BL05'): (1, set([483])),
    ('BL09','BL10'): (2, None),
    ('BL10','BL11'): (1, None),
    ('BL11','BL12'): (1, None),
    ('BL20','BL21'): (1, None),
    ('BL21','BL22'): (1, None),
    ('BL14','BL15'): (1, set([1200, 1243, 1286, 1329])),
}

SingleTrainStruct = namedtuple('SingleTrainStruct', ['Dst', 'Schedule'])


def ChainTimeTables(direction, timetables, day): # day for info only
    orderedStationList = sorted(timetables.keys())
    if direction[1]:
        orderedStationList.reverse()

    # 找出所有的終點站，並將其分離
    allDsts = set()
    for timetable in timetables.values():
        allDsts.update(map(lambda k: k['Dst'], timetable))

    # 按照目的地分離，加速搜尋
    for code, timetable in timetables.items():
        newTimetable = {}
        for dst in allDsts:
            newTimetable[dst] = []
        for d in timetable:
            # 同時先將時間都轉為數字，方便搜尋
            newTimetable[d['Dst']].append(Util.ConvertToMinute(d['Time']))
        # 以防萬一，還是先按照時間排序一次
        for schedule in newTimetable.values():
            schedule.sort()
        # 替換原先的時刻表
        timetables[code] = newTimetable
    if direction[0] == '南勢角' and direction[1] == 1:
        # 特別處理
        list1 = [code for code in orderedStationList if code <= 'O21']  # 迴龍
        list2 = [code for code in orderedStationList if code <= 'O12' or code >= 'O50']  # 蘆洲
        result1 = TraverseTimeTables(list1, timetables, day, specialHandle=1)
        result2 = TraverseTimeTables(list2, timetables, day)
        result = result1 + result2
    else:
        result = TraverseTimeTables(orderedStationList, timetables, day)
    return result


def appendLastStation(schedule):
    theLast = schedule[-1]
    (dstStation, additionMins) = lastAppend[theLast['StationCode']]
    schedule.append({'StationCode': dstStation, 'DepTime': Util.ConvertToHourMinute(Util.ConvertToMinute(theLast['DepTime']) + additionMins)})


def TraverseTimeTables(orderedStationList, timetables, day, specialHandle=0): # day for info only
    # 從第一個站開始，看第一筆時刻，然後接著每一個站去找
    result = []
    for idx, stationCode in enumerate(orderedStationList):
        if specialHandle == 1 and stationCode <= 'O12':
            continue
        for dst, departures in timetables[stationCode].items():
            for d in departures:
                singleTrain = SingleTrainStruct(Dst=dst, Schedule=[])
                singleTrain.Schedule.append({'StationCode': stationCode, 'DepTime': Util.ConvertToHourMinute(d)})
                timeThreshold = d
                for j in range(idx + 1, len(orderedStationList)):
                    currentTimetable = timetables[orderedStationList[j]][dst]
                    if not currentTimetable:
                        continue
                    # 找到下一個時間
                    addTime = additionalTimeThreshold.get((orderedStationList[j - 1], orderedStationList[j]))
                    if addTime is not None:
                        if addTime[1] is None:
                            timeThreshold += addTime[0]
                        else:
                            if timeThreshold not in addTime[1]:
                                timeThreshold += addTime[0]

                    foundIdx = bisect(currentTimetable, timeThreshold)
                    if foundIdx >= len(currentTimetable):
                        print('Error finding at {}->{} {} {} {} {}'.format(
                            orderedStationList[j - 1], orderedStationList[j], day, dst, ConvertToHourMinute(d), foundIdx))
                    foundTime = currentTimetable[foundIdx]
                    singleTrain.Schedule.append({'StationCode': orderedStationList[j], 'DepTime': Util.ConvertToHourMinute(foundTime)})
                    timeThreshold = foundTime
                    del currentTimetable[foundIdx]
                # 然後 append 最後一個站
                appendLastStation(singleTrain.Schedule)
                result.append({'Dst': singleTrain.Dst, 'Schedule': singleTrain.Schedule})
            del departures[:]
    return result


def ProcessLines(lineCode, stationFiles):
    # 讀進所有的時刻表資料
    timetableList = list(map(Util.ReadJson, stationFiles))
    # 先收集這個時刻表的編排是按照星期幾的，以及方向
    timetables = {}
    effectiveFromSet = set()
    for station in timetableList:
        for timetable in station['Timetables']:
            direction = directionMapping[timetable['Direction']]
            effectiveFromSet.add(timetable['EffectiveFrom'])
            for schedule in timetable['Schedule']:
                day = schedule['Days']
                key = (direction, day)
                if key not in timetables.keys():
                    timetables[key] = {}
                timetables[key][station['StationCode']] = schedule['Departures']
    directions = sorted(set([x[0] for x in timetables.keys()]))
    days = sorted(set([x[1] for x in timetables.keys()]))
    assert(len(effectiveFromSet) > 0)
    effectiveFrom = sorted(effectiveFromSet)[-1]

    # 現在得到的是依照方向及日期區分的時刻表 timetables
    result = []
    for direction in directions:
        directionResult = []
        for day in days:
#            if day != '7':
#                continue
            directionResult.append({ 'Days': day, 'Trains': ChainTimeTables(direction, timetables[(direction, day)], day) })
        result.append({'Direction': direction[0], 'EffectiveFrom': effectiveFrom, 'Timetables': directionResult})
    with open(join('output/Lines', lineCode + '.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)


if __name__ == '__main__':
    for lineCode in lineCodes:
        ProcessLines(lineCode, Path(inputDir).glob(lineCode + '*.json'))
