import os
import math
import pandas as pd
import geopandas as gpd
from urllib.request import urlopen
import xmltodict, json
import matplotlib.pyplot as plt


# KMA LCC coordinate KMA <-> EPSG:4326
# [reference] https://gist.github.com/fronteer-kr/14d7f779d52a21ac2f16
class KMAcoordConverter(object):
    # set projection parameter
    RE = 6371.00877  # earth radius near mid latitude (unit: km)
    GRID = 5.0  # grid spacing (unit: km)
    SLAT1 = 30.0  # projection latitude 1 (unit : degree)
    SLAT2 = 60.0  # projection latitude 2 (unit : degree)
    OLON = 126.0  # standard longitude (unit : degree)
    OLAT = 38.0  # standard latitude (unit : degree)
    XO = 43  # standard x grid (unit : -)
    YO = 136  # standard y grid (unit : -)

    def __init__(self):
        self._DEGRAD = math.pi / 180.0
        self._RADDEG = 180.0 / math.pi
        self._base = self.get_parameters()

    def get_parameters(self):
        re = self.RE / self.GRID
        _slat1 = self.SLAT1 * self._DEGRAD
        _slat2 = self.SLAT2 * self._DEGRAD
        olon = self.OLON * self._DEGRAD
        olat = self.OLAT * self._DEGRAD

        sn = math.tan(math.pi*0.25 + _slat2*0.5) / math.tan(math.pi*0.25 + _slat1*0.5)
        sn = math.log(math.cos(_slat1) / math.cos(_slat2)) / math.log(sn)
        sf = math.tan(math.pi*0.25 + _slat1*0.5)
        sf = math.pow(sf,sn) * math.cos(_slat1) / sn
        ro = math.tan(math.pi*0.25 + olat*0.5)
        ro = re * sf / math.pow(ro,sn)

        return {
            're': re,
            'olon': olon,
            'sn': sn,
            'sf': sf,
            'ro': ro
        }

    # EPSG:4326 to KMA LCC coordinate
    def LatLontoGridXY(self, latitude, longitude):
        ra = math.tan((math.pi*0.25) + (latitude*self._DEGRAD*0.5))
        ra = self._base['re'] * self._base['sf'] / math.pow(ra, self._base['sn'])
        theta = longitude * self._DEGRAD - self._base['olon']
        if theta > math.pi:
            theta -= 2.0 * math.pi
        elif theta < -math.pi:
            theta += 2.0 * math.pi
        theta *= self._base['sn']

        return {
            'x': math.floor(ra * math.sin(theta) + self.XO + 0.5),
            'y': math.floor(self._base['ro'] - ra * math.cos(theta) + self.YO + 0.5)
        }

    # KMA LCC coordinate to EPSG:4326
    def GridXYtoLatLon(self, x, y):
        base = self.get_parameters()

        xn = x - self.XO
        yn = base['ro'] - y + self.YO
        ra = math.sqrt(xn*xn + yn*yn)
        if base['sn'] < 0.0:
            ra = -ra
        alat = math.pow(base['re'] * base['sf'] / ra, 1.0 / base['sn'])
        alat = 2.0 * math.atan(alat) - math.pi*0.5

        if math.fabs(xn) <= 0.0:
            theta = 0.0
        else:
            if math.fabs(yn) <= 0.0:
                theta = math.pi * 0.5
                if xn < 0.0:
                    theta = -theta
            else:
                theta = math.atan2(xn, yn)
        alon = theta / base['sn'] + base['olon']

        return {
            'latitude': alat * self._RADDEG,
            'longitude': alon * self._RADDEG
        }


# get KMA grid coordinate within target shapefile
def get_points(gdf_shp):
    # set the number of grid
    nx = 149
    ny = 253

    # get KMA coordinate points
    converter = KMAcoordConverter()
    points_list = pd.DataFrame()
    for x in range(1,nx+1):
        for y in range(1,ny+1):
            points_checklist = converter.GridXYtoLatLon(x,y)
            df_points = pd.DataFrame(
                {'Grid': [(x, y)],
                 'Latitude': [points_checklist['latitude']],
                 'Longitude': [points_checklist['longitude']]}
            )
            gdf_points = gpd.GeoDataFrame(
                df_points, geometry=gpd.points_from_xy(df_points.Longitude, df_points.Latitude)
            )
            gdf_points.crs = {'init':'epsg:4326'}

            if gdf_points.geometry[0].within(gdf_shp.geometry[0]):
                points_list = points_list.append(df_points, ignore_index=True)

    gdf_result = gpd.GeoDataFrame(points_list,
                                  geometry=gpd.points_from_xy(points_list.Longitude, points_list.Latitude))

    return gdf_result


# get KMA weather forecast
# API specification : https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15084084
def get_weather_forecasts(search_time, service_key, kma_grid):
    x, y = kma_grid

    _url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst' + \
           '?serviceKey=' + str(service_key) + \
           '&numOfRows=100000&pageNo=1' + \
           '&base_date=' + str(search_time)[:8] + '&base_time=' + str(search_time)[8:] + \
           '&nx=' + str(x) + '&ny=' + str(y)

    _req = urlopen(_url)
    resp_body = _req.read().decode('utf-8')
    xml_parse = xmltodict.parse(resp_body)
    xml_dict = json.loads(json.dumps(xml_parse))

    obs_category = []
    obs_value = []
    for xml_item in xml_dict['response']['body']['items']['item']:
        obs_category.append(xml_item['category'])
        obs_value.append(xml_item['obsrValue'])

    df_obs = pd.DataFrame({'ObsCategory': obs_category, 'ObsValue': obs_value})

    return df_obs


if __name__ == '__main__':
    # get shapefile
    shp_dir = 'C:/Users/USER/Downloads/test/aoi/JB_GEO.shp'
    shp_file = gpd.GeoDataFrame.from_file(shp_dir, encoding='cp949')
    gdf_result = get_points(shp_file)

    # get weather forecast information
    kma_grid = gdf_result['Grid'][0]
    service_key = 'U1Bl19qagt1pBELd3mw%2FkExqUSxl5hmwiJ99Scpz0REN4OCW889DYcrnfGrIFreZKlUYOP7mR2vKfu48RqV4Sw%3D%3D'
    search_time = '202404081600'

    df_obs = get_weather_forecasts(search_time, service_key, kma_grid)

    print(df_obs)

    # save results
    out_dir = 'C:/Users/USER/Downloads/test/result'
    fig, ax = plt.subplots(figsize=(15,15))
    shp_file.plot(ax=ax, color='white', edgecolor='black')
    gdf_result.plot(ax=ax, color='red', markersize=15)
    ax.set_xlabel('Longitude', fontsize=10)
    ax.set_ylabel('Latitude', fontsize=10)
    plt.savefig(os.path.join(out_dir, 'result.png'), bbox_inches='tight', pad_inches=0, dpi=300)

    gdf_result.to_csv(os.path.join(out_dir, 'result.csv'))