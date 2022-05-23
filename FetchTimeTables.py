# -*- coding: utf8 -*-
import os, json, re
from os.path import basename, join, splitext
from bs4 import BeautifulSoup
from urllib import request
from urllib.parse import urljoin, urlparse
import filecmp
import requests

urlBase = 'https://web.metro.taipei/img/ALL/timetables/'
apiUrl = 'https://web.metro.taipei/apis/metrostationapi/timetableinfo'
dataDir = 'fetchData/'
downloadPDF = True

if not os.path.exists(dataDir):
    os.makedirs(dataDir)

with open('StationList.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

lineNumberCodeMapping = {'1': 'BR', '2': 'R', '3': 'G', '4': 'O', '5': 'BL'}

newData = []
for item in data:
    if item['TimeTableId'] == 0:
        continue
    newItem = item
    newItem['Directions'] = []
    lineCode = re.sub(r'\d.+', '', item['Code'])
    print('Fetching {} {}'.format(item['Code'], item['Name']))
    r = requests.post(apiUrl, json={"SID": item['TimeTableId'], "Lang": "tw"})
    retJson = r.json()

    for record in retJson:
        lineNumber = record['LineID']
        if lineNumberCodeMapping[lineNumber] != lineCode:
            continue
        downloadLink = (urljoin(urlBase, record['FileName']))
        fileName = basename(urlparse(downloadLink).path)

        newItem['Directions'].append({'Text': record['Direction'], 'File': fileName})
        if downloadPDF:
            pdf = request.urlopen(downloadLink)
            outputName = join(dataDir, fileName)
            tmpName = "download.tmp"
            with open(tmpName, 'b+w') as f:
                f.write(pdf.read())
            if not os.path.isfile(outputName) or not filecmp.cmp(tmpName, outputName, shallow=False):
                try:
                    os.remove(outputName)
                except OSError:
                    pass
                os.rename(tmpName, outputName)
            else:
                os.remove(tmpName)
    del newItem['TimeTableId']
    newData.append(newItem)

with open(join(dataDir, 'StationListWithPdf.json'), 'w', encoding='utf-8') as f:
    json.dump(newData, f, ensure_ascii=False, sort_keys=True, indent=2)

print('Done!')
