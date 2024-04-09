import os
import glob
import numpy as np
import pandas as pd
from urllib.request import urlopen
import xmltodict, json


# get nifos station temperature data
# station information are available on https://know.nifos.go.kr/main/main.do#AC=/main/viewPage.do&VA=content&view_nm=detail
def get_nifos_temp(search_date, service_key, csv_dir):
    # get xml file
    _url = 'http://apis.data.go.kr/1400377/mtweather/mountListSearch' + \
           '?serviceKey=' + str(service_key) + \
           '&pageNo=1&numOfRows=1000' + \
           '&_type=xml' + \
           '&tm=' + str(search_date)
    _req = urlopen(_url)
    resp_body = _req.read().decode('utf-8')
    xml_parse = xmltodict.parse(resp_body)
    xml_dict = json.loads(json.dumps(xml_parse))

    # get temperature information
    obsname_list = []
    obsid_list = []
    tm2m_list = []
    for xml_info in xml_dict['response']['body']['items']['item']:
        obsname_list.append(xml_info['obsname'])
        obsid_list.append(xml_info['obsid'])
        try:
            tm2m_list.append(xml_info['tm2m'])
        except:
            print('-- No available temperatue information --')
            tm2m_list.append(np.NaN)

    df_temp_mt = pd.DataFrame({'산이름': obsname_list, '지점번호': obsid_list, '기온(2m)': tm2m_list}).dropna(axis=0)

    # merge with NIFOS station information
    df_nifos_station = pd.read_csv(csv_dir, encoding='cp949')
    df_nifos_temp = pd.merge(df_nifos_station, df_temp_mt, on='산이름').drop(['지점번호_x','지점번호_y'], axis=1)

    return df_nifos_temp


if __name__ == '__main__':
    csv_dir = 'C:/Users/USER/Downloads/mtweatherInfo.csv'
    search_date = '202306301809'
    service_key = '****'

    df_nifos_temp = get_nifos_temp(search_date, service_key, csv_dir)
    print(df_nifos_temp)