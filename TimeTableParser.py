# -*- coding: utf8 -*-
import re, pickle, os.path
from datetime import datetime
import pdfminer
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams

parseCacheDir = 'parseCache/'

laparams = LAParams()


class TimeTableParser:
    cidMapping = {
        '(cid:13884)': '松',
        '(cid:11055)': '山',
        '(cid:26041)': '電',
        '(cid:14545)': '樓',
        '(cid:10823)': '安',
        '(cid:8725)':  '南',
        '(cid:8608)':  '勢',
        '(cid:22672)': '角',
        '(cid:23327)': '象',
        '(cid:13422)': '新',
        '(cid:11605)': '店',
        '(cid:21700)': '蘆',
        '(cid:15344)': '洲',
        '(cid:24242)': '迴',
        '(cid:28235)': '龍'
    }
    
    def __init__(self, pdfFileName):
        self.RawData = { 'underlines': [], 'rectsInTable': [], 'chars': [], 'textlines': [] }
        self.__xRanges = []
        self.__yRanges = []
        self.__underlineDestination = None
        self.days = None
        self.hours = None
        self.matrix = None
        self.destinations = None
        self.directionText = None
        self.effectiveFrom = None
        self.pdfFileName = pdfFileName

    def Parse(self):
        # 先看是否有 cache，以及日期是否夠新
        if not os.path.exists(parseCacheDir):
            os.makedirs(parseCacheDir)
        cacheFile = os.path.join(parseCacheDir, os.path.basename(self.pdfFileName) + '.cache')
        foundCache = (os.path.isfile(cacheFile) and \
                      os.path.getsize(cacheFile) > 0 and \
                      os.path.getmtime(cacheFile) > os.path.getmtime(self.pdfFileName))
        if (foundCache):
            fp = open(cacheFile, 'rb')
            self.RawData = pickle.load(fp)
            fp.close()
        else:
            fp = open(self.pdfFileName, 'rb')
            for page in PDFPage.get_pages(fp, None, maxpages=1):
                rsrcmgr = PDFResourceManager()
                device = PDFPageAggregator(rsrcmgr, laparams=laparams)
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                layout = device.get_result()
                self.__readobj(layout._objs)
                for category in self.RawData.values():
                    self.__reverseYaxis(category, layout.bbox[3])
                cacheFp = open(cacheFile, 'wb')
                pickle.dump(self.RawData, cacheFp)
                cacheFp.close()
            fp.close()

        self.__calculateBoundary()
        self.__assignCharsAndLinesToCell()
        self.__processCells()
        return (self.effectiveFrom, self.__getResult())

    def __readobj(self, lt_objs):
        for obj in lt_objs:
            if isinstance(obj, pdfminer.layout.LTTextBox):
                for line in obj._objs:
                    if isinstance(line, pdfminer.layout.LTTextLine):
                        self.RawData['textlines'].append(line)
                        for c in line._objs:
                            if isinstance(c, pdfminer.layout.LTChar):
                                self.RawData['chars'].append(c)
            elif isinstance(obj, pdfminer.layout.LTRect):
                if 10 < obj.height < 60:  # 用時刻表內的四邊形來切分；首先先取得所有特定大小內的四邊形
                    self.RawData['rectsInTable'].append(obj)
                elif obj.height < 1:  # 這些是底線，也先存起來
                    self.RawData['underlines'].append(obj)
            elif isinstance(obj, pdfminer.layout.LTFigure):
                self.__readobj(obj._objs)

    def __reverseYaxis(self, objs, pageHeight):
        for o in objs:
            o.bbox = (o.bbox[0], pageHeight - o.bbox[1], o.bbox[2], pageHeight - o.bbox[3])

    def __getFrequentBoundaries(self, pos):
        newList = list(map(lambda i: i.bbox[pos], self.RawData['rectsInTable']))
        # 計算頻率，只取出現超過 1 次的
        d = {x: newList.count(x) for x in set(newList)}
        d = {k: v for k, v in d.items() if v > 1}
        return list(d.keys())

    def __calculateBoundary(self):
        """計算時刻表內的水平及垂直邊界"""
        # === 計算垂直格線 ===
        # 取得所有方形的左側垂直格線
        verticalBounds = self.__getFrequentBoundaries(0)
        # 接著取得右側格線中的最大值
        verticalBounds.append(max(list(map(lambda i: i.bbox[2], self.RawData['rectsInTable']))))
        verticalBounds.sort()
        # 我們得到的數值，可以兩兩組合出「分」的左右邊界 v[1]-v[2], v[3]-v[4], ... （不需要最左側）
        # 計算格子的 X 軸範圍
        i = 1
        self.__xRanges = []
        while i <= len(verticalBounds) - 2:
            self.__xRanges.append((verticalBounds[i], verticalBounds[i + 1]))
            i += 2

        # === 計算水平格線 ===
        # 取得所有方形的下側水平格線
        horizontalBounds = self.__getFrequentBoundaries(1)
        horizontalBounds.sort()
        # 計算格子的 Y 軸範圍
        i = 1
        self.__yRanges = []
        while i <= len(horizontalBounds) - 2:
            self.__yRanges.append((horizontalBounds[i], horizontalBounds[i + 1]))
            i += 1

        # 抓出天及小時的欄位
        hoursBoundaries = (verticalBounds[0], verticalBounds[1])
        days = []
        hours = []
        for line in self.RawData['textlines']:
            linetext = line.get_text().strip()
            if '週' in linetext:
                days.append(line)
            elif '底線' in linetext:
                matches = re.findall('加註底線.*?[往至](.+?站)', linetext)
                self.__underlineDestination = self.__normalizeStationName(matches[0])
            elif '站往' in linetext:
                matches = re.findall('站往(.+)時刻表', linetext)
                self.directionText = self.__normalizeStationName(matches[0])
            elif 'Effective' in linetext:
                matches = re.findall('Effective from (.+)', linetext)
                self.effectiveFrom = datetime.strptime(matches[0].replace('.', ''), '%b %d, %Y').date().isoformat()
            elif hoursBoundaries[0] <= line.bbox[0] and line.bbox[2] <= hoursBoundaries[1] and re.match('\d\d$', linetext):
                hours.append(line)
        hours.sort(key=lambda x: (x.bbox[1]))
        self.hours = list(map(lambda k: k.get_text().strip(), hours))
        days.sort(key=lambda x: x.bbox[0])
        self.days = self.__parseDays(list(map(lambda k: k.get_text().strip(), days)))
        self.__parseDestination()
        
    def __parseDestination(self):
        self.destinations = list(map(self.__normalizeStationName, self.directionText.split('、')))
        if len(self.destinations) == 1:
            if self.__underlineDestination is not None:
                self.destinations.append(self.__underlineDestination)
            return
        assert(len(self.destinations) == 2)
        if self.destinations[0] == self.__underlineDestination:
            self.destinations[0], self.destinations[1] = self.destinations[1], self.destinations[0]

    def __searchInRanges(self, num, ranges):
        for idx, range in enumerate(ranges):
            if  range[0] < num < range[1]:
                return idx

    def __normalizeStationName(self, name):
        if 'cid:' in name:
            for orig, after in self.cidMapping.items():
                name = name.replace(orig, after)
        if name == '臺北車站':
            name = '台北車站'
        if name != '台北車站':
            name = name.replace('站', '')
        return name

    def __assignObjToMatrix(self, obj):
        xIdx = self.__searchInRanges(obj.bbox[0], self.__xRanges)
        yIdx = self.__searchInRanges(obj.bbox[1], self.__yRanges)
        if xIdx is not None and yIdx is not None:
            self.matrix[xIdx][yIdx].append(obj)

    def __assignCharsAndLinesToCell(self):
        # 建立一個二維矩陣，內有 list
        self.matrix = [[[] for x in range(len(self.__yRanges))] for x in range(len(self.__xRanges))]
        # 將各個字元填入
        for c in self.RawData['chars']:
            self.__assignObjToMatrix(c)
        for l in self.RawData['underlines']:
            self.__assignObjToMatrix(l)

    def __processCells(self):
        for x in range(len(self.__xRanges)):
            for y in range(len(self.__yRanges)):
                self.__processCell(x, y)

    def __processCell(self, x, y):
        # 按照 Y 座標排序再按 X 座標排序
        self.matrix[x][y].sort(key=lambda x: (x.bbox[3], x.bbox[0]))
        # 在這階段我們會有一個列表裡面像這樣：
        # Text, Text, Text, Text, ... Line, Line, Text, Text
        # Line 就是附著在他之前的某段文字的
        # 在處理 Line 之前，先將文字作合併，同時對於 Line 尋找是符合哪一個文字並作標記
        i = 0
        tmpTime = []
        tmpLine = []
        result = []
        while i < len(self.matrix[x][y]):
            obj = self.matrix[x][y][i]
            if isinstance(obj, pdfminer.layout.LTRect):
                tmpLine.append(obj)
                if i == len(self.matrix[x][y]) - 1 or isinstance(self.matrix[x][y][i + 1], pdfminer.layout.LTChar):
                    result.extend(self.__tagUnderlined(tmpTime, tmpLine))
                    tmpTime = []
                    tmpLine = []
                i += 1
            elif isinstance(obj, pdfminer.layout.LTChar):  # Text，跟下一個 Text 合併
                nextObj = self.matrix[x][y][i + 1]
                obj._text = obj._text + nextObj._text
                obj.bbox = (obj.bbox[0], obj.bbox[1], nextObj.bbox[2], nextObj.bbox[3])
                tmpTime.append(obj)
                i += 2
        if len(result) == 0:
            self.matrix[x][y] = list(map(lambda k: (k.get_text(), 0), tmpTime))
        else:
            result.extend(map(lambda k: (k.get_text(), 0), tmpTime))
            self.matrix[x][y] = result

    def __tagUnderlined(self, time, line):
        if len(line) == 0:
            return time
        timeLen = len(time)
        lineLen = len(line)
        timeIdx = lineIdx = 0
        result = []
        while timeIdx < timeLen:
            if (lineIdx < lineLen and \
                    line[lineIdx].bbox[0] <= time[timeIdx].bbox[0] <= line[lineIdx].bbox[2] and\
                    line[lineIdx].bbox[1] - time[timeIdx].bbox[1] < 0.05):
                result.append((time[timeIdx].get_text(), 1))
                timeIdx += 1
                lineIdx += 1
            else:
                result.append((time[timeIdx].get_text(), 0))
                timeIdx += 1
        return result

    def __parseDay(self, day):
        weekdays = { '週一': 1, '週二': 2, '週三': 3, '週四': 4, '週五': 5, '週六': 6, '週日': 7 }
        foundDays = list(map(lambda x: weekdays[x], re.findall('週.', day)))
        if len(foundDays) == 1:
            return str(foundDays[0])
        if len(foundDays) == 2 and '至' in day:
            foundDays = ','.join(str(x) for x in list(range(foundDays[0], foundDays[1] + 1)))
        return foundDays

    def __parseDays(self, days):
        days = list(map(self.__parseDay, days))
        return days

    def __getResult(self):
        timetables = []
        for x in range(0, len(self.days)):
            departures = []
            for y in range(0, len(self.hours)):
                departures.extend(self.__getCellResult(self.hours[y], self.matrix[x][y]))
            timetable = { 'Days': self.days[x], 'Departures': departures }
            timetables.append(timetable)
        return timetables
    
    def __getCellResult(self, hour, minutes):
        return list(map(lambda m: { 'Time': '{}:{}'.format(hour, m[0]), 'Dst': self.destinations[m[1]]}, minutes))
