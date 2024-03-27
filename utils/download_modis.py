import os
import math
import time, datetime
import requests
import pandas as pd
from pyproj import Proj
from lxml import etree
from io import StringIO

# MOD11A1, MYD11A1 > LST
# MOD13Q1, MYD13Q1 > NDVI, EVI
base_urls = ['https://e4ftl01.cr.usgs.gov/MOLT/MOD11A1.061/', 'https://e4ftl01.cr.usgs.gov/MOLA/MYD11A1.061/',
             'https://e4ftl01.cr.usgs.gov/MOLT/MOD13Q1.061/', 'https://e4ftl01.cr.usgs.gov/MOLA/MYD13Q1.061/']


def coord_to_grid(lon, lat):
    num_vtiles = 18
    num_htiles = 36

    earth_radius = 6371007.181
    earth_width = 2 * math.pi * earth_radius

    tile_width = earth_width / num_htiles
    tile_height = tile_width

    modis_grid_proj = Proj(f'+proj=sinu +R={earth_radius} +nadgrids=@null +wktext')

    x, y = modis_grid_proj(lon, lat)
    h = (earth_width * 0.5 + x) / tile_width
    v = -(earth_width * 0.25 + y - (num_vtiles - 0) * tile_height) / tile_height

    return int(h), int(v)


def get_url_content(url):
    page = requests.Session().get(url)
    html = page.content.decode('utf-8')
    tree = etree.parse(StringIO(html), parser=etree.HTMLParser())
    refs = tree.xpath('//a')
    content_list = list(set([link.get('href', '') for link in refs]))

    return content_list


class modisDownloader:
    def __init__(self, nasa_username, nasa_password, start_date, end_date, coord, out_dir):
        self.nasa_username = nasa_username
        self.nasa_password = nasa_password
        self.start_date = start_date
        self.end_date = end_date
        self.coord = coord
        self.out_dir = out_dir

    def get_modis_list(self):
        # get date list
        date_list = pd.date_range(self.start_date, self.end_date).tolist()

        # convert geo coordinate to h, v tile
        tile_h, tile_v = coord_to_grid(self.coord[0], self.coord[1])
        hv_name = 'h' + str(tile_h).zfill(2) + 'v' + str(tile_v).zfill(2)

        # get MODIS data url list
        modis_hdf_list = []
        for _url in base_urls:
            for _date in date_list:
                _date = datetime.datetime.strptime(str(_date), '%Y-%m-%d %H:%M:%S').date()
                _date = _date.strftime('%Y.%m.%d')

                files = get_url_content(_url + _date)
                modis_file = [_url + _date + '/' + modis_file for modis_file in files if
                              (hv_name in modis_file) and modis_file.endswith('.hdf')]
                modis_hdf_list.extend(modis_file)

                time.sleep(3)

        return modis_hdf_list

    def download(self):
        modis_hdf_list = self.get_modis_list()
        modis_hdf_path = []

        # download MODIS data
        for modis_file in modis_hdf_list:
            modis_filename = modis_file.split('/')[-1][:-4]

            with requests.Session() as session:
                url_redirect = session.get(modis_file)
                url_response = session.get(url_redirect.url, auth=(self.nasa_username, self.nasa_password))
                out_name = os.path.join(self.out_dir, modis_filename)
                with open(out_name, 'wb') as modis_file:
                    modis_file.write(url_response._content)

            modis_hdf_path.append(out_name)

            time.sleep(3)

        return modis_hdf_path


if __name__ == '__main__':
    downloader = modisDownloader(nasa_username='woohyun', nasa_password='Jwh134679',
                                 start_date='2021-04-01', end_date='2021-04-05', coord=(128.55, 36.55),
                                 out_dir='C:/Users/USER/Downloads')
    modis_paths = downloader.download()
    print(modis_paths)