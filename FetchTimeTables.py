# -*- coding: utf8 -*-
import os, json, re
from os.path import basename, join, splitext
from bs4 import BeautifulSoup
from urllib import request
from urllib.parse import urljoin, urlparse

urlBase = 'http://web.metro.taipei/c/timetables.asp?id='
dataDir = 'fetchData/'
downloadPDF = False

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
    html = request.urlopen(urlBase + str(item['TimeTableId'])).read()
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', attrs={'width':'50%'})
    for tr in table.findAll("tr"):
        tds = tr.findAll("td")
        lineNumber = splitext(basename(tds[0].find("img")['src']))[0]
        if lineNumberCodeMapping[lineNumber] != lineCode:
            continue
        link = tds[1].find("a")
        downloadLink = (urljoin(urlBase, link['href']))
        fileName = basename(urlparse(downloadLink).path)
        newItem['Directions'].append({'Text': link.text, 'File': fileName})
        if downloadPDF:
            pdf = request.urlopen(downloadLink)
            with open(join(dataDir, fileName), 'b+w') as f:
                f.write(pdf.read())
    del newItem['TimeTableId']
    newData.append(newItem)

with open(join(dataDir, 'StationListWithPdf.json'), 'w', encoding='utf-8') as f:
    json.dump(newData, f, ensure_ascii=False, sort_keys=True, indent=2)

print('Done!')
