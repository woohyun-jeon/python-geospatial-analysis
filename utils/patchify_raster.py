import os
import glob
import rasterio
from rasterio.windows import Window
import warnings
from rasterio.errors import NotGeoreferencedWarning
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

def patchify(img_file, out_dir, msk_file=None, msk_proportion=0.05, crop_size=256, stride_size=128, keep_crs=True):
    with rasterio.open(img_file) as src:
        img = src.read()
        img_meta = src.meta.copy()
        original_transform = src.transform

    if msk_file is not None:
        with rasterio.open(msk_file) as src:
            msk = src.read(1)
    else:
        msk = None

    height, width = img.shape[1:]

    if width < crop_size or height < crop_size:
        print('Insufficient size -- ', img_file, 'Size should be larger than ', crop_size)
        return

    idx = 0
    for col_i in range(0, height - crop_size + 1, stride_size):
        for row_i in range(0, width - crop_size + 1, stride_size):
            img_crop = img[:, col_i:col_i + crop_size, row_i:row_i + crop_size]

            if msk_file is not None:
                msk_crop = msk[col_i:col_i + crop_size, row_i:row_i + crop_size]
                if msk_crop.sum() >= int(crop_size * crop_size * msk_proportion):
                    save_patch(img_crop, msk_crop, img_meta, original_transform, out_dir, idx, keep_crs, col_i, row_i, crop_size)
            else:
                save_patch(img_crop, None, img_meta, original_transform, out_dir, idx, keep_crs, col_i, row_i, crop_size)

            idx += 1

def save_patch(img_crop, msk_crop, img_meta, original_transform, out_dir, idx, keep_crs, col_i, row_i, crop_size):
    if keep_crs:
        transform = rasterio.windows.transform(Window(row_i, col_i, crop_size, crop_size), original_transform)
    else:
        transform = None

    img_meta.update({
        'height': img_crop.shape[1],
        'width': img_crop.shape[2],
        'transform': transform,
        'crs': img_meta['crs'] if keep_crs else None
    })

    img_file_name = os.path.join(out_dir, f'img_{str(idx).zfill(4)}.tif')
    with rasterio.open(img_file_name, 'w', **img_meta) as dest:
        dest.write(img_crop)

    if msk_crop is not None:
        msk_file_name = os.path.join(out_dir, f'msk_{str(idx).zfill(4)}.tif')
        msk_meta = img_meta.copy()
        msk_meta.update({
            'count': 1,
            'dtype': msk_crop.dtype
        })
        with rasterio.open(msk_file_name, 'w', **msk_meta) as dest:
            dest.write(msk_crop, 1)

if __name__ == '__main__':
    imgfiles = glob.glob("D:/oil/origin/S1*/site*_norm.tif")
    out_dir = "D:/oil/patch"
    for imgfile in imgfiles:
        mskfile = imgfile.replace('_data_norm', '_oil')
        out_dir_updated = os.path.join(out_dir, os.path.basename(os.path.dirname(imgfile)))
        # os.makedirs(out_dir_updated, exist_ok=True)
        keep_crs = True

        patchify(img_file=imgfile, out_dir=out_dir, msk_file=mskfile, msk_proportion=0, keep_crs=keep_crs)