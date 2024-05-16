import os
import glob
import numpy as np
from tifffile import tifffile


def patchify(img_file, out_dir, msk_file=None, msk_proportion=0.05, crop_size=256, stride_size=256):
    img = tifffile.imread(img_file)
    if msk_file is not None:
        msk = tifffile.imread(msk_file)
    else:
        msk = None

    width, height = img.shape[:2]
    if width < crop_size or height < crop_size:
        print('Insufficient size -- ', img_file, 'Size should be larger than ', crop_size)
        pass

    idx = 0
    for col_i in range(0, width, stride_size):
        for row_i in range(0, height, stride_size):
            if col_i + crop_size > width or row_i + crop_size > height:
                pass
            else:
                img_crop = img[col_i:col_i + crop_size, row_i:row_i + crop_size, :]

                if msk_file is not None:
                    msk_crop = msk[col_i:col_i + crop_size, row_i:row_i + crop_size]
                    if msk_crp.sum() >= int(crop_size * crop_size * msk_proportion):
                        tifffile.imsave(os.path.join(out_dir, 'img_' + str(idx).zfill(4) + '.tif'), img_crop)
                        tifffile.imsave(os.path.join(out_dir, 'msk_' + str(idx).zfill(4) + '.tif'), msk_crop)
                else:
                    tifffile.imsave(os.path.join(out_dir, 'img_' + str(idx).zfill(4) + '.tif'), img_crop)

                idx += 1

    return


if __name__ == '__main__':
    img_file = 'C:/Users/USER/Downloads/site01_data_norm.tif'
    out_dir = 'C:/Users/USER/Downloads'

    patchify(img_file=img_file, out_dir=out_dir)