import os
import glob
import time
import asf_search as asf
import geopandas as gpd
import pandas as pd


class S1Downloader:
    def __init__(self, asf_username, asf_password, start_date, end_date, shp_dir, out_dir, prod_type='GRD'):
        self.asf_username = asf_username
        self.asf_password = asf_password
        self.start_date = start_date
        self.end_date = end_date
        self.shp_dir = shp_dir
        self.out_dir = out_dir
        self.prod_type = prod_type

    def search_data(self, gdf, start_date, end_date, prod_type='GRD'):
        if prod_type == 'SLC':
            prod_level = asf.PRODUCT_TYPE.SLC
        elif prod_type == 'GRD':
            prod_level = asf.PRODUCT_TYPE.GRD_HD

        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=prod_level,
            beamMode=asf.BEAMMODE.IW,
            start=start_date,
            end=end_date,
            intersectsWith=str(gdf['geometry'][0])
        )

        metadata = results.geojson()

        df_s1info = pd.DataFrame()

        for file in metadata['features']:
            df_geom = pd.DataFrame(file['geometry'].items())
            df_geom.columns = ['properties', 'value']
            df_parm = pd.DataFrame(file['properties'].items())
            df_parm.columns = ['properties', 'value']
            df_tot = df_geom.append(df_parm).reset_index(drop=True)
            df_tot = df_tot.set_index('properties')
            df_s1info = pd.concat([df_s1info, df_tot], axis=1, ignore_index=True)

        return df_s1info

    def sort_data(self, df_s1info, path, frame, out_dir):
        df_s1list = df_s1info.T[(df_s1info.loc['pathNumber'] == path) & (df_s1info.loc['frameNumber'] == frame)]

        orb_info = str(path) + '_' + str(frame)
        out_dir_updated = os.path.join(out_dir, orb_info)
        os.makedirs(out_dir_updated, exist_ok=True)

        df_s1list.to_csv(os.path.join(out_dir_updated, 's1_list.csv'), index=True, encoding='utf-8-sig')

        return df_s1list, out_dir_updated

    def download(self):
        start_time = time.time()

        session = asf.ASFSession().auth_with_creds(self.asf_username, self.asf_password)

        # get aoi info
        gdf_aoi = gpd.read_file(self.shp_dir)
        # search Sentinel-1 data
        df_s1info = self.search_data(gdf_aoi, self.start_date, self.end_date, self.prod_type)

        # get path, frame number of Sentinel-1 data
        path_list = list(set(df_s1info.loc['pathNumber']))
        frame_list = list(set(df_s1info.loc['frameNumber']))

        s1_paths = []
        for _path in path_list:
            for _frame in frame_list:
                df_s1list, out_dir_updated = self.sort_data(df_s1info, _path, _frame, self.out_dir)

                print("Start Sentinel-1 download processing --- Path: %s, Frame: %s"
                      % (_path, _frame))

                asf.download_urls(urls=df_s1list['url'], path=out_dir_updated, session=session)
                s1_paths += glob.glob(os.path.join(out_dir_updated, 'S1*.zip'))

                print("Complete Sentinel-1 download processing --- Path: %s, Frame: %s --- %s seconds ---"
                      % (_path, _frame, time.time() - start_time))

        return s1_paths


if __name__ == '__main__':
    downloader = S1Downloader(asf_username='****', asf_password='****',
                              start_date='2023-01-01', end_date='2023-01-30',
                              shp_dir='C:/Users/USER/Downloads/test/aoi/aoi.shp', out_dir='C:/Users/USER/Downloads/test/data',
                              prod_type='SLC')
    s1_paths = downloader.download()
    print(s1_paths)