# -*- coding: utf8 -*-
import os, sys, json, traceback
from os.path import join
from TimeTableParser import TimeTableParser
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams
from multiprocessing import Pool, Value, Lock

# config
outfp = sys.stdout
codec = 'utf-8'
dataDir = 'fetchData/'
outputDir = 'output/'
outputCompact = join(outputDir, "Compact")
outputReadable = join(outputDir, "Readable")
threads = 4

laparams = LAParams()

counter = None

def ProcessTimeTable(station):
    global counter
    result = { 'StationName': station['Name'], 'StationCode': station['Code'], 'Timetables': [] }
    for direction in station['Directions']:
        if station['Name'] == '新北投' or '新北投' in direction['Text'] or \
            station['Name'] == '小碧潭' or '小碧潭' in direction['Text']:
            return
        print('Processing {} {}'.format(station['Name'], direction['Text']))
        fp = open(join(dataDir, direction['File']), 'rb')
        for page in PDFPage.get_pages(fp, None, maxpages=1):
            try:
                rsrcmgr = PDFResourceManager()
                device = PDFPageAggregator(rsrcmgr, laparams=laparams)
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                layout = device.get_result()
                tableParser = TimeTableParser(layout._objs, layout.bbox[3])
                (effectiveFrom, timetables) = tableParser.Parse()
                allTimeTables = { 'Direction': direction['Text'], 'EffectiveFrom': effectiveFrom, 'Schedule': timetables }
                result['Timetables'].append(allTimeTables)
            except:
                print("Error at {}".format(direction['File']) )
                traceback.print_exc(direction=sys.stdout)
        fp.close()
    with open(join(outputReadable, station['Code'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
    with open(join(outputCompact, station['Code'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

if __name__ == '__main__':
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    if not os.path.exists(outputCompact):
        os.makedirs(outputCompact)
    if not os.path.exists(outputReadable):
        os.makedirs(outputReadable)

    with open(join(dataDir, 'StationListWithPdf.json'), 'r', encoding='utf-8') as f:
        inputList = json.load(f)
    if threads > 1:
        pool = Pool(processes=4)
        pool.map(ProcessTimeTable, inputList)
        pool.close()
        pool.join()
    else:
        for station in inputList:
            ProcessTimeTable(station)
    print('Done!')
