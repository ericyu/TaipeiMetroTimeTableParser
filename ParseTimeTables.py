# -*- coding: utf8 -*-
import os, sys, io, json, traceback
from os.path import join
from TimeTableParser import TimeTableParser
from multiprocessing import Pool, Value, Lock

# config
outfp = sys.stdout
codec = 'utf-8'
dataDir = 'fetchData/'
outputDir = 'output/Stations/'
threads = 4

counter = None


def ProcessTimeTable(station):
    global counter
    result = { 'StationName': station['Name'], 'StationCode': station['Code'], 'Timetables': [] }
    for direction in station['Directions']:
        if station['Name'] == '新北投' or '新北投' in direction['Text'] or \
            station['Name'] == '小碧潭' or '小碧潭' in direction['Text']:
            continue
        print('Processing {} {}'.format(station['Name'], direction['Text']))
        try:
            tableParser = TimeTableParser(join(dataDir, direction['File']))
            (effectiveFrom, timetables) = tableParser.Parse()
            allTimeTables = { 'Direction': direction['Text'], 'EffectiveFrom': effectiveFrom, 'Schedule': timetables }
            result['Timetables'].append(allTimeTables)
        except:
            print("Error at {}".format(direction['File']))
            traceback.print_exc(file=sys.stdout)

    if len(result['Timetables']) > 0:
        with io.open(join(outputDir, station['Code'] + '.json'), 'w', encoding='utf8') as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)


if __name__ == '__main__':
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)

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
