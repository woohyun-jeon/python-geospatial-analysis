import numpy as np
from osgeo import gdal


def normalize(in_file):
    # read tiff
    img_ds = gdal.Open(in_file)
    img_arr = img_ds.ReadAsArray()
    if np.ndim(img_arr) == 2:
        img_arr = np.expand_dims(img_arr, axis=0)
    img_arr = img_arr.transpose(1, 2, 0).astype(np.float32)

    # normalize to 0-255 range
    img_arr_reshape = img_arr.reshape(-1, img_arr.shape[2])

    img_arr_reshape_norm = np.empty(shape=img_arr_reshape.shape, dtype=np.float32)
    for idx in range(img_arr.shape[2]):
        img_arr_reshape_idx = img_arr_reshape[:, idx]
        image_reshape_idx_norm = np.uint8(255 * (img_arr_reshape_idx - np.min(img_arr_reshape_idx)) / (np.max(img_arr_reshape_idx) - np.min(img_arr_reshape_idx)))
        # ensure the values are within 0-255 range
        image_reshape_idx_norm = np.clip(image_reshape_idx_norm, 0, 255)
        image_reshape_idx_norm = np.round(image_reshape_idx_norm).astype(np.uint8)
        img_arr_reshape_norm[:, idx] = image_reshape_idx_norm

    if int(img_arr.shape[2]) == 1:
        img_arr_transform = img_arr_reshape_norm.reshape(img_arr.shape[:2])
    else:
        img_arr_transform = img_arr_reshape_norm.reshape(img_arr.shape)

    # export result
    outname = in_file[:-4] + '_norm.tif'

    transform = img_ds.GetGeoTransform()
    projection = img_ds.GetProjection()

    driver = gdal.GetDriverByName('GTiff')
    if np.ndim(img_arr_transform) == 2:
        out_ds = driver.Create(outname, ysize=int(img_arr.shape[0]), xsize=int(img_arr.shape[1]), bands=1, eType=gdal.GDT_Byte)
        out_ds.GetRasterBand(1).WriteArray(img_arr_transform)
    else:
        out_ds = driver.Create(outname, ysize=int(img_arr.shape[0]), xsize=int(img_arr.shape[1]),
                               bands=int(img_arr.shape[2]), eType=gdal.GDT_Byte)
        for i in range(1, int(img_arr.shape[2]) + 1):
            out_ds.GetRasterBand(i).WriteArray(img_arr_transform[:, :, i - 1])

    out_ds.SetProjection(projection)
    out_ds.SetGeoTransform(transform)
    out_ds = None

    return


if __name__ == '__main__':
    infile = 'C:/Users/USER/Desktop/test/single_channel.tif'

    normalize(infile)