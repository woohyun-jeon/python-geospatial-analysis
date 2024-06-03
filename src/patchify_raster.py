import os
import glob
import rasterio
from rasterio.windows import Window
import warnings
from rasterio.errors import NotGeoreferencedWarning
warnings.filterwarnings('ignore', category=NotGeoreferencedWarning)

def patchify(img_file, out_dir, msk_file=None, msk_proportion=0.05, crop_size=256, stride_size=128, keep_crs=True):
    src_img = rasterio.open(img_file)
    arr_img = src_img.read()
    meta_img = src_img.meta.copy()
    original_transform = src_img.transform

    if msk_file is not None:
        src_msk = rasterio.open(msk_file)
        arr_msk = src_msk.read(1)
    else:
        arr_msk = None

    height, width = arr_img.shape[1:]

    if width < crop_size or height < crop_size:
        print('Insufficient size -- ', img_file, 'Size should be larger than ', crop_size)
        return

    os.makedirs(os.path.join(out_dir, 'image'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'label'), exist_ok=True)

    idx = 0
    for col_i in range(0, height - crop_size + 1, stride_size):
        for row_i in range(0, width - crop_size + 1, stride_size):
            arr_img_crop = arr_img[:, col_i:col_i + crop_size, row_i:row_i + crop_size]

            if msk_file is not None:
                arr_msk_crop = arr_msk[col_i:col_i + crop_size, row_i:row_i + crop_size]
                if arr_msk_crop.sum() >= int(crop_size * crop_size * msk_proportion):
                    save_patch(arr_img_crop, arr_msk_crop, meta_img, original_transform, out_dir, idx, keep_crs, col_i, row_i, crop_size)
            else:
                save_patch(arr_img_crop, None, meta_img, original_transform, out_dir, idx, keep_crs, col_i, row_i, crop_size)

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

    img_file_name = os.path.join(out_dir, 'image', f'{str(idx).zfill(4)}.tif')
    with rasterio.open(img_file_name, 'w', **img_meta) as dest:
        dest.write(img_crop)

    if msk_crop is not None:
        msk_file_name = os.path.join(out_dir, 'label', f'{str(idx).zfill(4)}.tif')
        msk_meta = img_meta.copy()
        msk_meta.update({
            'count': 1,
            'dtype': msk_crop.dtype
        })
        with rasterio.open(msk_file_name, 'w', **msk_meta) as dest:
            dest.write(msk_crop, 1)

if __name__ == '__main__':
    imgfiles = glob.glob('C:/Users/USER/Desktop/test/*_norm.tif')
    out_dir = 'C:/Users/USER/Desktop/test/patch'
    for imgfile in imgfiles:
        mskfile = imgfile.replace('_norm', '_label')
        out_dir_updated = os.path.join(out_dir, os.path.basename(imgfile)[:-4])
        os.makedirs(out_dir_updated, exist_ok=True)
        keep_crs = True

        if not os.path.isfile(mskfile):
            mskfile = None

        patchify(img_file=imgfile, out_dir=out_dir_updated, msk_file=mskfile, msk_proportion=0, keep_crs=keep_crs)