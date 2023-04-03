# -*- coding: utf8 -*-
import json
import io
from os.path import join, basename, splitext
from pathlib import Path
from itertools import *
from Util import *
from Util import StationMapping
from bdb import effective
from collections import Counter

lineTimetablesDir = 'output/Lines'
outputDir = 'output/web'
stationMapping = StationMapping('StationList.json')
GATrackingCode = '[TRACKING_CODE]'

sortKeyStations = {
     '象山': 'R06',  # 大安森林公園
     '淡水': 'R21',  # 奇岩
     '新店': 'G09',  # 古亭
     '松山': 'G18',  # 南京三民
     '南勢角': 'O02',  # 景安
     '蘆洲、迴龍': 'O12',  # 大橋頭
     '頂埔': 'BL06',  # 府中
     '南港展覽館': 'BL20'  # 後山埤
}

lineCodeToName = {
    'R': '淡水信義線',
    'G': '松山新店線',
    'O': '中和新蘆線',
    'BL': '板南線'
}

PatternToText = {
    '1,2,3,4': '平常日（週一至週四）',
    '1,2,3,4,5': '平常日（週一至週五）',
    '5': '平常日（週五）',
    '6': '週六',
    '7': '週日'
}

BaseToOtherStationTime = {
    'R06': {
        'R05': 2  # 大安
    },
    'R21': {
        'R24': 7,  # 忠義
        'R27': 14  # 紅樹林
    },
    'G09': {
        'G03': 14,  # 七張
        'G08': 7  # 台電大樓
    },
    'O12': {
        'O13': 2,  # 台北橋
        'O14': 4,  # 菜寮
        'O18': 13,  # 新莊
        'O20': 18,  # 丹鳳
        'O52': 7  # 徐匯中學
    },
    'BL20': {
        'BL22': 4  # 南港
    },
    'BL06': {
        'BL02': 9,  # 永寧
        'BL05': 2  # 亞東醫院
    }
}

DirectionToCode = {
    '淡水': 'a',
    '象山': 'b',
    '松山': 'a',
    '新店': 'b',
    '蘆洲、迴龍': 'a',
    '南勢角': 'b',
    '南港展覽館': 'a',
    '頂埔': 'b'
}

currentSortDirection = None

summaryByStation = {}

def getTrainSortKey(train):
    keyStation = sortKeyStations[currentSortDirection]
    searchResult = next(filter(lambda x: x[0] == keyStation, train), None)
    if searchResult is None:
        # 利用第一站的時間，倒推應該是什麼時間
        return ConvertToMinute(train[0][1]) - BaseToOtherStationTime[keyStation][train[0][0]]
    else:
        return ConvertToMinute(searchResult[1])


def getHtmlFileHeader(title):
    result = '''\
<!doctype html>
<html class="no-js" lang="zh-Hant-TW">
<head>
    <meta charset="utf-8">\n\
    '''
    result += GetGAScript(GATrackingCode)
    result += ('<title>' + title + '</title>')
    result += '''\
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/purecss@1.0.0/build/pure-min.css" integrity="sha384-nn4HPE8lTHyVtfCBi5yW9d20FjT8BJwUXyWZT9InLYax14RDjBj46LmSztkmNP9w" crossorigin="anonymous">
    <link rel="stylesheet" href="../css/metro-color.css">
    <link rel="stylesheet" href="../css/dia.css">
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js" integrity="sha512-bLT0Qm9VnAYZDflyKcBaQ2gg0hSYNQrJ8RilYldYQ1FxQYoCLtUjuuRuZo+fjqhx/qtq/1itJ0C2ejDxltZVFg==" crossorigin="anonymous"></script>
    <script src="../js/dia.js"></script>
</head>
<body>\
    '''
    return result


def getHtmlFileFooter():
    result = '</body></html>'
    return result


def getPageHeaderWithSwitchTable(code, codeText, effectiveFrom, allDaysPatterns, allDirections, currentDaysPattern, currentDirection):
    isStation = False
    if re.search(r'\d', code): # 站別時刻表的話
        lineCode = re.sub(r'\d+', '', code)
        isStation = True

    result = '<div class="header-wrapper"><div id="header-left"><div id="main-header">'
    if isStation:
        result += '<span class="route-box route-box-larger {}">{}</span> {} 時刻表'.format(lineCode.lower(), code, codeText)
    else:
        result += '<span class="route-box {}">{}</span> {}時刻表'.format(code.lower(), code, codeText)

    result += '</div><div id="effective-from">{} 生效</div>'.format(effectiveFrom)

    if isStation: # 站別時刻表的話
        result += '<div id="go-back"><a href="../lines/{}-{}-{}.html">回路線時刻表</a></div>'.format(
            lineCode, DirectionToCode[currentDirection], currentDaysPattern)
    else:
        result += '<div id="go-back"><a href="..">回主畫面</a></div>'
    result += '</div>'

    result += '<div id="header-right">'
    result += getSwitchPatternDirectionTable(code, allDaysPatterns, allDirections, currentDaysPattern, currentDirection)
    result += '</div></div>'
    return result


def getSwitchPatternDirectionTable(code, allDaysPatterns, allDirections, currentDaysPattern, currentDirection):
    result = '<div class="pure-button-group" role="group">'
    for pattern in allDaysPatterns:
        if currentDaysPattern == pattern:
            result += '<button class="pure-button pure-button-active pure-button-primary">{}</button>'.format(PatternToText[pattern])
        else:
            result += '<a class="pure-button" href="{}-{}-{}.html">{}</a>\n'.format(
                code, DirectionToCode[currentDirection], pattern, PatternToText[pattern])

    result += '</div><div class="pure-button-group" role="group">'

    for direction in allDirections:
        if re.search(r'\d', code) and stationMapping.CodeToName(code) == direction:
            continue
        if currentDirection == direction:
            result += '<button class="pure-button pure-button-active pure-button-primary">{}方向</button>'.format(direction)
        else:
            result += '<a class="pure-button" href="{}-{}-{}.html">{}方向</a>\n'.format(
                code, DirectionToCode[direction], currentDaysPattern, direction)

    result += "</div>"
    return result


def getLineTimetable(stations, data, direction, daysPattern):
    result = '<div id="outer-timetable-container"><div id="station-container"><table id="stations"><tbody>'
    rows = [''] * len(stations)
    idx = 0
    for (i, station) in enumerate(stations):
        if i != len(stations) - 1:
            appendLink = True
        else:
            appendLink = False
        url = '../stations/{}-{}-{}.html'.format(station, DirectionToCode[direction], daysPattern)
        result += '<tr><td>'
        if appendLink:
            result += '<a class="station-link" href="{}">'.format(url)
        result += '<span class="station-code">{}</span> {}'.format(
            station, stationMapping.CodeToName(station))
        if appendLink:
            result += '</a>'
        result += '</td></tr>\n'
        idx += 1
    result += '</tbody></table></div>\n'

    result += '<div id="timetable-container" class="dia"><table id="timetable"><tbody>'
    rows = [s + '<tr>' for s in rows]
    for train in data:
        # 加上 ==
        if train[-1] == '':
            for i, time in reversed(list(enumerate(train))):
                if time != '':
                    train[i+1] = '=='
                    break

        idx = 0
        for dep in train:
            rows[idx] += '<td>' + dep + '</td>'
            idx += 1
    rows = [s + '</tr>\n' for s in rows]
    result += ''.join(rows) + '</tbody></table></div></div>'
    return result


def printLineFile(allStations, allDaysPatterns, allDirections,
                  lineCode, currentDaysPattern, currentDirection, data, effectiveFrom):
    sortReversed = (GetNumber(data[10][1][0]) - GetNumber(data[10][0][0])) == -1
    stations = list(allStations)
    stations.sort(reverse=sortReversed)
    stationLookup = {val: idx for (idx, val) in enumerate(stations)}

    fileName = '{}/lines/{}-{}-{}.html'.format(
        outputDir, lineCode, DirectionToCode[currentSortDirection], currentDaysPattern)

    trains = []
    f = io.open(fileName, "w", encoding="utf8")

    # Print header
    f.write(getHtmlFileHeader(lineCodeToName[lineCode] + '時刻表'))

    f.write(getPageHeaderWithSwitchTable(lineCode, lineCodeToName[lineCode], effectiveFrom, allDaysPatterns, allDirections, currentDaysPattern, currentDirection))

    for train in data:
        toLuzhou = any(map(lambda x: x[0] == 'O50', train))
        if toLuzhou:
            train.extend(map(lambda x: ('O' + str(x), '||'), range(13, 22)))
        deps = [''] * len(stations)
        for dep in train:
            (station, time) = dep
            index = stationLookup.get(station, None)
            if index is not None:
                deps[index] = time
        trains.append(deps)

    # 檢查時間合理性（每一站的時間都是排序好的）
    stationCount = len(stations)
    for i in range(stationCount):
        checkValues = [ConvertToMinute(t[i]) for t in trains if t[i] != '' and t[i] != '==' and t[i] != '||']
        sortedValues = sorted(checkValues)
        for a in range(len(checkValues)):
            if checkValues[a] != sortedValues[a]:
                print("Warning at {} {} {} {}".format(
                    currentDaysPattern, stations[i], ConvertToHourMinute(checkValues[a]), ConvertToHourMinute(sortedValues[a])))
                break

    f.write(getLineTimetable(stations, trains, currentDirection, currentDaysPattern))
    f.write(getHtmlFileFooter())


def getStationTimetable(data):
    # Group data by hour
    byHourData = {}
    for record in data:
        minute = record['DepTime']
        hour = minute // 60
        minute = minute - hour * 60
        if hour not in byHourData:
            byHourData[hour] = list()
        byHourData[hour].append({'Min': minute, 'Dst': record['Dst'], 'First': record['First']})

    # Gather destinations
    dstList = [x['Dst'] for x in data]
    dstStat = Counter(dstList)
    dstByCount = sorted(dstStat, key=dstStat.get, reverse=True)
    assert(len(dstByCount) <= 2)

    firstMarkUsed = False

    result = '<div><table id="station-timetable-table"><tbody><tr><th>時</th><th>分</th></tr>'
    for hour in sorted(byHourData.keys()):
        minData = sorted(byHourData[hour], key=lambda k: k['Min'])
        if hour >= 24:
            hour -= 24
        result += '<td>{:02d}</td><td>'.format(hour)
        for minRec in minData:
            if minRec['Dst'] != dstByCount[0]:
                dstAbbr = minRec['Dst'][0]
            else:
                dstAbbr = ''
            result += '<div class="departure"><div class="departure-attr">'
            result += '<div class="dst">{}</div>'.format(dstAbbr)
            if minRec['First']:
                result += '<div class="first-station">●</div>'
                firstMarkUsed = True
            result += '</div><div class="minute">{:02d}</div></div>'.format(minRec['Min'])
        result += '</td></tr>'
    result += '</tbody></table></div>'

    if len(dstByCount) > 1 or firstMarkUsed:
        result += '<div id="note-box"><div id="note-header">備註</div><ol>'
        if len(dstByCount) > 1:
            dst = dstByCount[1]
            result += '<li>{}・・・終點站為 {}</li>'.format(dst[0], dst)
        if firstMarkUsed:
            result += '<li>● 表示本站為該列車首站</li>'
        result += '</ol></div>'

    return result


def printStationFile(allDaysPatterns, allDirections, lineCode, stationCode, currentDirection, currentDaysPattern, timetableData, effectiveFrom):
    fileName = '{}/stations/{}-{}-{}.html'.format(outputDir, stationCode, DirectionToCode[currentDirection], currentDaysPattern)
    f = codecs.open(fileName, "w", "utf-8-sig")

    # Print header
    f.write(getHtmlFileHeader('{} {}時刻表'.format(stationCode, stationMapping.CodeToName(stationCode))))
    f.write(getPageHeaderWithSwitchTable(stationCode, stationMapping.CodeToName(stationCode),
                          effectiveFrom, allDaysPatterns, allDirections,
                          currentDaysPattern, currentDirection))

    f.write(getStationTimetable(timetableData))

    f.write(getHtmlFileFooter())


def printStationSummaryPage(stationName, data):
    fileName = '{}/stationPage/{}.html'.format(outputDir, stationName.replace('/', ''))
    f = codecs.open(fileName, "w", "utf-8-sig")

    # Print header
    f.write(getHtmlFileHeader('{} 時刻表'.format(stationName)))
    f.write('<div class="header-wrapper"><div id="main-header">{} 時刻表</div></div>'.format(stationName))

    # group by lines
    byLine = {}
    allDirections = set()
    for rec in data:
        key = (rec['LineCode'], rec['StationCode'])
        if key not in byLine.keys():
            byLine[key] = list()
        byLine[key].append((rec['Direction'], rec['DaysPattern']))

    for (lineCode, stationCode), value in byLine.items():
        f.write('<div class="line-header"><span class="route-box summary-line-name {}">{}</span> <span class="route-box route-box-larger {}">{}</span></div>'.format(
            lineCode.lower(), lineCodeToName[lineCode], lineCode.lower(), stationCode))
        f.write('<table class="pure-table" id="station-summary-table"><thead><tr>')
        allDaysPatterns = sorted(list(set([x[1] for x in value])))
        for pattern in allDaysPatterns:
            f.write('<th>{}</th>'.format(PatternToText[pattern]))
        f.write('</tr></thead><tbody><tr>');
        for pattern in allDaysPatterns:
            f.write('<td>');
            directions = sorted(list(set([x[0] for x in value])), key=lambda k: DirectionToCode[k])
            for direction in directions:
                f.write('<p><a href="../stations/{}-{}-{}.html">{}方向</a></p>'.format(
                    stationCode, DirectionToCode[direction], pattern, direction))
            f.write('</td>');
        f.write('</tr>');
        f.write('</tbody></table>')

    f.write(getHtmlFileFooter())


def processLineTimeTable(inputFile):
    global currentSortDirection
    data = ReadJson(inputFile)
    lineCode = inputFile.stem
    # 先收集所有的站
    allStations = set()
    allDirections = set()
    allDaysPatterns = set()
    for direction in data:
        allDirections.add(direction['Direction'])
        for timetable in (direction['Timetables']):
            allDaysPatterns.add(timetable['Days'])
            for train in timetable['Trains']:
                allStations.update(map(lambda k: k['StationCode'], train['Schedule']))

    allDirections = sorted(allDirections, key=lambda k: DirectionToCode[k])
    allDaysPatterns = sorted(allDaysPatterns)

    # 處理路線時刻表
    for direction in data:
        effective = direction['EffectiveFrom']
        keys = sortKeyStations[direction['Direction']]
        for timetable in (direction['Timetables']):
            tableData = []
            for train in timetable['Trains']:
                tableData.append(list(map(lambda k: (k['StationCode'], k['DepTime']), train['Schedule'])))
            currentSortDirection = direction['Direction']
            tableData.sort(key=getTrainSortKey)
            printLineFile(allStations, allDaysPatterns, allDirections,
                          lineCode, timetable['Days'], currentSortDirection, tableData, effective)

    # 處理站別時刻表
    # 從路線時刻表來處理，以得到該班車出發站的資訊
    # 分配資料到各個資料去： stationData[(station, direction, pattern)] = [ {time, attributes}, ... ]
    # 各車站頁面則用 summaryByStation[stationName] = [ {lineCode, direction, daysPattern}, ... ]
    stationData = {}

    for directionTimeTable in data:
        direction = directionTimeTable['Direction']
        for timetable in (directionTimeTable['Timetables']):
            daysPattern = timetable['Days']
            for train in timetable['Trains']:
                dst = train['Dst']
                isFirst = True
                for departure in train['Schedule'][:-1]:
                    station = departure['StationCode']
                    depTime = departure['DepTime']
                    key = (station, direction, daysPattern)
                    if key not in stationData:
                        stationData[key] = list()
                    stationData[key].append({'DepTime': ConvertToMinute(depTime), 'Dst': dst, 'First': isFirst})
                    isFirst = False

    for key in stationData.keys():
        if stationMapping.CodeToName(key[0]) == key[1]:
            continue
        printStationFile(allDaysPatterns, allDirections, lineCode,
                         key[0], key[1], key[2], stationData[key], effective)
        stationName = stationMapping.CodeToName(key[0])
        if stationName not in summaryByStation:
            summaryByStation[stationName] = list()
        summaryByStation[stationName].append({'LineCode': lineCode, 'StationCode': key[0], 'Direction': key[1], 'DaysPattern': key[2]})


if __name__ == '__main__':
    for file in Path(lineTimetablesDir).glob('*.json'):
        processLineTimeTable(file)
        print('Done ' + str(file))

    print('Print summary page...')
    for stationName, data in summaryByStation.items():
        printStationSummaryPage(stationName, data)
    print('Done')
