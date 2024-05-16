import numpy as np
from osgeo import gdal


def normalize(in_file):
    # read tiff
    img_ds = gdal.Open(in_file)
    img_arr = img_ds.ReadAsArray().transpose(1,2,0).astype(np.float32)

    # normalize to [0, 255]
    img_arr_reshape = img_arr.reshape(-1, img_arr.shape[2])

    img_arr_reshape_norm = np.empty(shape=img_arr_reshape.shape, dtype=np.float32)
    for idx in range(img_arr.shape[2]):
        img_arr_reshape_idx = img_arr_reshape[:, idx]
        image_reshape_idx_norm = np.uint8(255 * (img_arr_reshape_idx - np.min(img_arr_reshape_idx)) / (np.max(img_arr_reshape_idx) - np.min(img_arr_reshape_idx)))
        img_arr_reshape_norm[:, idx] = image_reshape_idx_norm

    img_arr_transform = img_arr_reshape_norm.reshape(img_arr.shape)

    # export result
    outname = in_file[:-4] + '_norm.tif'

    transform = img_ds.GetGeoTransform()
    projection = img_ds.GetProjection()

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(outname, ysize=int(img_arr.shape[0]), xsize=int(img_arr.shape[1]),
                           bands=int(img_arr.shape[2]), eType=gdal.GDT_Byte)
    for i in range(1, int(img_arr.shape[2]) + 1):
        out_ds.GetRasterBand(i).WriteArray(img_arr_transform[:, :, i-1])

    out_ds.SetProjection(projection)
    out_ds.SetGeoTransform(transform)
    out_ds = None

    return


if __name__ == '__main__':
    infile = 'C:/Users/USER/Downloads/site01_data.tif'

    normalize(infile)