# -*- coding: utf8 -*-
import os, sys, io, json, traceback
from datetime import datetime
from os.path import join
from TimeTableParser import TimeTableParser
from multiprocessing import Pool, Value, Lock
from Util import ConvertToHourMinute, ConvertToMinute

# config
outfp = sys.stdout
codec = 'utf-8'
dataDir = 'fetchData/'
outputDir = 'output/Stations/'

service_day_mapping = {
    '平日': '1,2,3,4,5',
    '週六': '6',
    '週日': '7',
    '假日': '6,7'
    }

direction_mapping = {
    ('R', 0): "往R22北投站、R28淡水站",
    ('R', 1): "往R02象山站",
    ('G', 0): "往G19松山站",
    ('G', 1): "往G01新店站",
    ('O', 0): "往O54蘆洲站、O21迴龍站",
    ('O', 1): "往O01南勢角站",
    ('BL', 0): "往BL23南港展覽館站",
    ('BL', 1): "往BL01頂埔站",
}

line_common_data = {}

def ProcessTimeTable(station_id, all_data):
    # 從完整資料中，先濾出相關車站的部分
    station_data = list(filter(lambda x: x["StationID"] == station_id, all_data))
    effectiveFrom = set(map(lambda x: x["SrcUpdateTime"], station_data))
    assert(len(effectiveFrom) == 1)
    effectiveFrom = datetime.fromisoformat(list(effectiveFrom)[0]).strftime("%Y-%m-%d")

    all_timetables = []
    directions = [0, 1]
    line_id = station_data[0]["LineID"]
    for direction in [0, 1]:
        schedules = []
        for service_day in line_common_data[line_id]["service_day_patterns"]:
            departures = []
            raw_schedule_data = list(filter(lambda x: x["Direction"] == direction and x["ServiceDay"]["ServiceTag"] == service_day, station_data))
            if not raw_schedule_data:
                continue
        
            for single_destination_timetable in raw_schedule_data:
                destination_station_id = single_destination_timetable["DestinationStaionID"]
                if destination_station_id.endswith("A"):
                    continue
                destination_station_name = single_destination_timetable["DestinationStationName"]["Zh_tw"]
                for time_record in single_destination_timetable["Timetables"]:
                    departures.append({"Dst": destination_station_name, "Time": time_record["DepartureTime"]})

            departures.sort(key=lambda k: ConvertToMinute(k["Time"]))
            schedules.append({
                "Days": service_day_mapping[service_day],
                "Departures": departures
                })
            schedules.sort(key=lambda k: k["Days"])
        if(schedules):
            all_timetables.append({
                'Direction': direction_mapping[(line_id, direction)],
                'EffectiveFrom': effectiveFrom,
                'Schedule': schedules
                })

    #result['Timetables'] = sorted(result['Timetables'], key=lambda k: k["Direction"], reverse=True)

    if len(all_timetables) > 0:
        result = {
            'StationName': station_data[0]["StationName"]["Zh_tw"],
            'StationCode': station_id,
            'Timetables': all_timetables
            }

        with io.open(join(outputDir, station_id + '.json'), 'w', encoding='utf8') as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)


if __name__ == '__main__':
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)

    with open('scheduledata.json', encoding='utf-8') as f:
        all_data = json.load(f)

    # 根據 LineID (R, O, G, BL) 找出不同的營運模式並存成 dict
    line_ids = set(map(lambda x: x["LineID"], all_data))

    for line_id in line_ids:
        line_datas = list(filter(lambda x: x["LineID"] == line_id, all_data))
        patterns = set(map(lambda x: x["ServiceDay"]["ServiceTag"], line_datas))

        line_common_data[line_id] = {
                "service_day_patterns": list(patterns)
            }
        
    station_ids = {s["StationID"] for s in all_data}
    
    for station_id in station_ids:
        if station_id.endswith('A'):
            continue
        ProcessTimeTable(station_id, all_data)

    print('Done!')
