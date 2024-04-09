import os
import time
import requests
import pandas as pd
import geopandas as gpd


class S2Downloader:
    def __init__(self, cdes_username, cdes_password, start_date, end_date, shp_dir, out_dir):
        self.cdes_username = cdes_username
        self.cdes_password = cdes_password
        self.start_date = start_date
        self.end_date = end_date
        self.shp_dir = shp_dir
        self.out_dir = out_dir

    def get_token(self):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = 'username=' + self.cdes_username + '&password=' + self.cdes_password + '&grant_type=password&client_id=cdse-public'

        response = requests.post(
            'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
            headers=headers,
            data=data,
        )

        access_token = response.text.split('"')[3]

        return access_token

    def download(self):
        gdf_aoi = gpd.read_file(self.shp_dir)
        s2_json = requests.get(
            f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{'SENTINEL-2'}' and contains(Name, 'L2A') \
            and OData.CSC.Intersects(area=geography'SRID=4326;{str(gdf_aoi['geometry'][0])}') \
            and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le 10.00) \
            and ContentDate/Start gt {self.start_date}T00:00:00.000Z \
            and ContentDate/Start lt {self.end_date}T00:00:00.000Z"
        ).json()

        s2_json_value = s2_json['value']
        s2_metadata = pd.DataFrame.from_dict(s2_json_value)
        print("Total %s images can be acquired" % (len(s2_metadata)))

        s2_paths = []
        for idx in range(len(s2_metadata)):
            target_id = s2_metadata['Id'][idx]
            target_name = s2_metadata['Name'][idx]

            print('Download start : %s' % (target_name))

            start_time = time.time()

            url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({target_id})/$value"
            headers = {"Authorization": f"Bearer {self.get_token()}"}

            session = requests.Session()
            session.headers.update(headers)
            response = session.get(url, headers=headers, stream=True)

            out_name = os.path.join(self.out_dir, target_name+".zip")
            with open(out_name, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

            print('Download complete --- %s: %s seconds' % (target_name, time.time() - start_time))

            s2_paths.append(out_name)

            time.sleep(10)

        return s2_paths


if __name__ == '__main__':
    downloader = S2Downloader(cdes_username='****', cdes_password='****',
                              start_date='2022-06-01', end_date='2022-06-30',
                              shp_dir='C:/Users/USER/Downloads/test/aoi/aoi.shp',
                              out_dir='C:/Users/USER/Downloads/test/data')

    s2_paths = downloader.download()
    print(s2_paths)