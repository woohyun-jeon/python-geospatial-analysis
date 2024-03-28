import os, glob
from osgeo import gdal


class georeferenceMODIS:
    def __init__(self, modis_file, out_dir):
        self.modis_file = modis_file
        self.out_dir = out_dir

    def __process__(self):
        modis_output = []

        hdf_data = gdal.Open(self.modis_file, gdal.GA_ReadOnly)
        hdf_name = os.path.basename(self.modis_file)
        if hdf_name.startswith('MOD11A1') or hdf_name.startswith('MYD11A1'):
            target_list = {'day': '0', 'night': '4'}
            for target_name, target_idx in target_list.items():
                ds_hdf = gdal.Open(hdf_data.GetSubDatasets()[int(target_idx)][0], gdal.GA_ReadOnly)
                output = os.path.join(self.out_dir, hdf_name + '_lst_' + target_name + '.tif')

                gdal.Warp(output, ds_hdf, dstSRS='EPSG:4326')

                modis_output.append(output)

        elif hdf_name.startswith('MOD13Q1') or hdf_name.startswith('MYD13Q1'):
            target_list = {'ndvi': '0', 'evi': '1'} # 'red': '3', 'nir': '4', 'blue': '5', 'mir': '6'
            for target_name, target_idx in target_list.items():
                ds_hdf = gdal.Open(hdf_data.GetSubDatasets()[int(target_idx)][0], gdal.GA_ReadOnly)
                output = os.path.join(self.out_dir, hdf_name + '_' + target_name + '.tif')

                gdal.Warp(output, ds_hdf, dstSRS='EPSG:4326')

                modis_output.append(output)

        return modis_output


if __name__ == '__main__':
    root_dir = 'C:/Users/USER/Downloads/modis'
    lst_file = glob.glob(os.path.join(root_dir, 'MOD11A1*'))[0]
    vi_file = glob.glob(os.path.join(root_dir, 'MOD13Q1*'))[0]

    lstGeoreference = georeferenceMODIS(lst_file, root_dir)
    viGeoreference = georeferenceMODIS(vi_file, root_dir)

    lst_output = lstGeoreference.__process__()
    print(lst_output)
    vi_output = viGeoreference.__process__()
    print(vi_output)