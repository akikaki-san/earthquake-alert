'''
@author: Yuto Watanabe
@version: 1.0.0

Copyright (c) 2020 Earthquake alert
'''
import datetime
import os
from typing import Any, List

import requests
import xmltodict

try:
    from json_operation import json_write, json_read
except ModuleNotFoundError:
    from src.json_operation import json_write, json_read

# Too many variables, branches and statements is specifications
# pylint: disable=R0914
# pylint: disable=R0912
# pylint: disable=R0915


def convert_xml_infomation(links: List[str]) -> List[Any]:
    '''
    XML data of "information about the epicenter and seismic intensity"
    is acquired from the link and converted and extracted.

    Args:
        links (List[str]): A link with XML data of information about the epicenter and seismic intensity.
    Returns:
        List[Any]: Formatted and extracted elements.
    '''
    output = []

    for link in links:
        try:
            xml = requests.get(link)
        except requests.exceptions.ConnectionError:
            continue

        xml.encoding = 'UTF-8'

        try:
            earthquake = xmltodict.parse(xml.text)
        except xmltodict.expat.ExpartError:
            continue

        output.append(convert_infomation(earthquake))

    return output


def convert_xml_report(links: List[str], cache_dir: str) -> List[Any]:
    '''
    XML data of "Seismic intensity bulletin" is acquired from the link and converted and extracted.

    Args:
        links (List[str]): A link with XML data of Seismic intensity bulletin.
        cache_dir (str): A directory for cache file.

    Returns:
        List[Any]: Formatted and extracted elements.
    '''
    output = []
    cache_file_path = os.path.join(cache_dir, 'repot_duplication.json')

    for link in links:
        try:
            xml = requests.get(link)
        except requests.exceptions.ConnectionError:
            continue

        xml.encoding = 'UTF-8'

        try:
            earthquake = xmltodict.parse(xml.text)
        except xmltodict.expat.ExpartError:
            continue

        output.append(convert_report(earthquake, cache_file_path))

    return output


def convert_infomation(earthquake: Any) -> Any:
    '''
    Extract the XML of "information about epicenter and seismic intensity" to json.

    Args:
        earthquake (Any): XML data.

    Returns:
        Any: The extracted data.
    '''
    if earthquake['Report']['Head']['InfoType'] != '発表':
        return {
            'title': f"{earthquake['Report']['Head']['Title']} {earthquake['Report']['Head']['InfoType']}",
            'max_seismic_intensity': 'None',
            'magnitude': 'None',
            'explanation': [earthquake['Report']['Head']['Headline']['Text']],
            'epicenter': {
                "name": "None",
                "lon": 0,
                "lat": 0
            },
            'areas': {}
        }

    si_7 = set()
    si_over_6 = set()
    si_under_6 = set()
    si_over_5 = set()
    si_under_5 = set()
    si_4 = set()
    si_3 = set()
    si_2 = set()
    si_1 = set()

    explanation = []
    explanation.append(earthquake['Report']['Head']['Headline']['Text'])
    explanation += earthquake['Report']['Body']['Comments']['ForecastComment']['Text'].split('\n\n')

    try:
        location = earthquake['Report']['Body']['Earthquake']['Hypocenter']['Area']['jmx_eb:Coordinate']['#text']

        lat = float(location[:5])
        lon = float(location[5:11])
    except KeyError:
        lat = 0
        lon = 0

    epicenter = {
        'name': earthquake['Report']['Body']['Earthquake']['Hypocenter']['Area']['Name'],
        'lat': lat,
        'lon': lon
    }

    title = earthquake['Report']['Head']['Title']
    serial = str(earthquake['Report']['Head']['Serial'])
    if serial != '1':
        title += f' 第{serial}報'

    def pref(areas_1):
        def area(areas_2):
            def city(areas_3):
                def intensity_station(areas_4):
                    sint = areas_4['Int']

                    if sint == '7':
                        si_7.add(areas_4['Code'])
                    elif sint == '6+':
                        si_over_6.add(areas_4['Code'])
                    elif sint == '6-':
                        si_under_6.add(areas_4['Code'])
                    elif sint == '5+':
                        si_over_5.add(areas_4['Code'])
                    elif sint == '5-':
                        si_under_5.add(areas_4['Code'])
                    elif sint == '4':
                        si_4.add(areas_4['Code'])
                    elif sint == '3':
                        si_3.add(areas_4['Code'])
                    elif sint == '2':
                        si_2.add(areas_4['Code'])
                    elif sint == '1':
                        si_1.add(areas_4['Code'])

                if isinstance(areas_3['IntensityStation'], list):
                    for element in areas_3['IntensityStation']:
                        intensity_station(element)
                else:
                    intensity_station(areas_3['IntensityStation'])

            if isinstance(areas_2['City'], list):
                for element in areas_2['City']:
                    city(element)
            else:
                city(areas_2['City'])

        if isinstance(areas_1['Area'], list):
            for element in areas_1['Area']:
                area(element)
        else:
            area(areas_1['Area'])

    formated_areas = {}
    try:
        areas = earthquake['Report']['Body']['Intensity']['Observation']['Pref']
        if isinstance(areas, list):
            for element in areas:
                pref(element)
        else:
            pref(areas)

        if len(si_7) != 0:
            formated_areas['7'] = list(si_7)
        if len(si_over_6) != 0:
            formated_areas['6+'] = list(si_over_6)
        if len(si_under_6) != 0:
            formated_areas['6-'] = list(si_under_6)
        if len(si_over_5) != 0:
            formated_areas['5+'] = list(si_over_5)
        if len(si_under_5) != 0:
            formated_areas['5-'] = list(si_under_5)
        if len(si_4) != 0:
            formated_areas['4'] = list(si_4)
        if len(si_3) != 0:
            formated_areas['3'] = list(si_3)
        if len(si_2) != 0:
            formated_areas['2'] = list(si_2)
        if len(si_1) != 0:
            formated_areas['1'] = list(si_1)
    except KeyError:
        pass

    try:
        max_seismic_intensity = str(earthquake['Report']['Body']['Intensity']['Observation']['MaxInt'])
    except KeyError:
        max_seismic_intensity = 'NoN'

    output = ({
        'title': title,
        'max_seismic_intensity': max_seismic_intensity,
        'magnitude': earthquake['Report']['Body']['Earthquake']['jmx_eb:Magnitude']['#text'],
        'explanation': explanation,
        'epicenter': epicenter,
        'areas': formated_areas
    })

    return output


def convert_report(earthquake: Any, cache_file_path: str) -> Any:
    '''
    Extract the XML of "Seismic intensity bulletin" to json.

    Args:
        earthquake (Any): XML data.
        cache_file_path (str): cache file path.

    Returns:
        Any: The extracted data.
    '''
    title = earthquake['Report']['Head']['Title']
    duplication = duplication_report(earthquake['Report']['Head']['EventID'], cache_file_path)

    if duplication != 1:
        title = f'{title} 第{duplication}報'

    explanation = []
    explanation.append(earthquake['Report']['Head']['Headline']['Text'])
    try:
        explanation.append(earthquake['Report']['Body']['Comments']['ForecastComment']['Text'])
    except KeyError:
        pass

    areas = earthquake['Report']['Head']['Headline']['Information']
    if isinstance(areas, list):
        information = areas[0]['Item']
    else:
        information = areas['Item']

    formated_areas = {}
    if isinstance(information, list):
        max_seismic_intensity = information[0]['Kind']['Name']
        for individual in information:
            seismic_intensity = individual['Kind']['Name']
            areas = []
            if isinstance(individual['Areas']['Area'], list):
                for area in individual['Areas']['Area']:
                    areas.append(area['Name'])
            else:
                areas.append(individual['Areas']['Area']['Name'])
            formated_areas[seismic_intensity] = areas
    else:
        max_seismic_intensity = information['Kind']['Name']
        seismic_intensity = information['Kind']['Name']
        areas = []
        if isinstance(information['Areas']['Area'], list):
            for area in information['Areas']['Area']:
                areas.append(area['Name'])
        else:
            areas.append(information['Areas']['Area']['Name'])
        formated_areas[seismic_intensity] = areas

    if max_seismic_intensity in {'震度1', '震度１'}:
        formated_seismic_intensity = '1'
    elif max_seismic_intensity in {'震度2', '震度２'}:
        formated_seismic_intensity = '2'
    elif max_seismic_intensity in {'震度3', '震度３'}:
        formated_seismic_intensity = '3'
    elif max_seismic_intensity in {'震度4', '震度４'}:
        formated_seismic_intensity = '4'
    elif max_seismic_intensity in {'震度5弱', '震度５弱'}:
        formated_seismic_intensity = '5-'
    elif max_seismic_intensity in {'震度5強', '震度５強'}:
        formated_seismic_intensity = '5+'
    elif max_seismic_intensity in {'震度6弱', '震度６弱'}:
        formated_seismic_intensity = '6-'
    elif max_seismic_intensity in {'震度6強', '震度６強'}:
        formated_seismic_intensity = '6+'
    elif max_seismic_intensity in {'震度7', '震度7'}:
        formated_seismic_intensity = '7'
    else:
        formated_seismic_intensity = '0'

    output = {
        'title': title,
        'max_seismic_intensity': formated_seismic_intensity,
        'explanation': explanation,
        'areas': formated_areas
    }

    return output


def duplication_report(event_id: str, save_file_path: str) -> int:
    '''
    Check out the follow-up to "Seismic Intensity Bulletin".

    Args:
        event_id (str): Id of the event
        save_file_path: The path of the cache file to save.
    Returns:
        int: What is the report?
    '''
    now = datetime.datetime.now()

    if os.path.isfile(save_file_path):
        previous_data = json_read(save_file_path)
    else:
        previous_data = []

    # delete old element
    if previous_data != []:
        delete_data = []
        for index, element in enumerate(previous_data):
            date = datetime.datetime.strptime(str(element['date']), r'%Y%m%d%H%M%S')
            diff_date = now - date
            if diff_date.seconds > 3600:
                delete_data.append(index)

        delete_data.sort(reverse=True)
        for element in delete_data:
            del previous_data[element]

    # check report
    is_existence = False
    report = 1
    for element in previous_data:
        if str(event_id) == element['id']:
            is_existence = True
            element['report'] += 1
            report = element['report']
            element['date'] = now.strftime(r'%Y%m%d%H%M%S')
            break
    if not is_existence:
        report = 1
        data = {
            'date': now.strftime(r'%Y%m%d%H%M%S'),
            'id': str(event_id),
            'report': report
        }
        previous_data.append(data)

    json_write(save_file_path, previous_data)

    return report