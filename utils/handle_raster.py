import os
import glob
import numpy as np
from osgeo import gdal


def read_geotiff(in_file):
    in_ds = gdal.Open(in_file)
    in_arr = in_ds.ReadAsArray().transpose(1,2,0)
    in_proj = {'SpatialRef': in_ds.GetProjectionRef(), 'GeoTransform': in_ds.GetGeoTransform()}

    return in_arr, in_proj


def write_geotiff(in_arr, out_filename, in_proj=None):
    driver = gdal.GetDriverByName('GTiff')

    # set data type
    if in_arr.type == np.uint8:
        gdal_type = gdal.GDT_Byte
    elif in_arr.dtype == np.float32:
        gdal_type = gdal.GDT_Float32
    elif in_arr.dtype == np.uint16:
        gdal_type = gdal.GDT_UInt16

    # set data channels
    if np.ndim(in_arr) == 2:
        dst_ds = driver.Create(out_filename, ysize=in_arr.shape[0], xsize=in_arr.shape[1], bands=1, eType=gdal_type)
        dst_ds.GetRasterBand(1).WriteArray(in_arr)
    elif np.ndim(in_arr) == 3:
        dst_ds = driver.Create(out_filename, ysize=in_arr.shape[0], xsize=in_arr.shape[1], bands=in_arr.shape[2], eType=gdal_type)
        for idx in range(1, in_arr.shape[2] + 1):
            dst_ds.GetRasterBand(idx).WriteArray(in_arr[:,:, idx - 1])
    else:
        print("Please check dimension of input geotiff file")
        return

    # set data projection
    if in_proj is not None:
        dst_ds.SetGeoTransform(in_proj['GeoTransform'])
        dst_ds.SetProjection(in_proj['SpatialRef'])
    else:
        print("Please check the projection of input geotiff file")

    dst_ds.FlushCache()
    dst_ds = None

    print("Succeed to write geotiff -- %s" % (out_filename))

    return


def translate_geotiff(in_gdalfile, out_filename, epsg_code='4326', res=None, geobound=None):
    params = {}
    params['dstSRS'] = f"EPSG:{epsg_code}"
    params['format'] = 'GTiff'

    # set output spatial resolution
    if res is not None:
        params['xRes'] = res[0]
        params['yRes'] = res[1]
        params['resampleAlg'] = gdal.GRA_Bilinear

    # set boundary
    if geobound is not None and len(geobound) == 4:
        params['outputBounds'] = geobound

    # translate
    gdal.Warp(out_filename, in_gdalfile, **params)

    print("Succeed to translate geotiff -- %s to coordinate %s" % (out_filename, "EPSG:{epsg_code}"))

    return


if __name__ == '__main__':
    in_dir = 'C:/Users/USER/Downloads/test/out'
    in_file = glob.glob(os.path.join(in_dir, '*.tif'))[0]
    write_file = in_file[:-4] + '_test_write.tif'
    warp_file = in_file[:-4] + '_test_warp.tif'

    in_arr, in_proj = read_geotiff(in_file)
    print(in_arr.shape, in_proj)

    write_geotiff(in_arr, write_file, in_proj)

    in_gdalfile = gdal.Open(in_file)
    translate_geotiff(in_gdalfile, warp_file)