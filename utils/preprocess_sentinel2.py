import os
import glob
import gc
import time
import snappy
from snappy import ProductIO, GPF, HashMap


# get snappy operators
GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
# get Hashmap key-value pairs
HashMap = snappy.jpy.get_type('java.util.HashMap')

# define vegetation indices
spi_list = {'ndvi': '(B4-B8)/(B4+B8)', 'nbr': '(B8-B12)/(B8+B12)'}


def resample(source, tarRes=20):
    params = HashMap()
    params.put('targetResolution', str(tarRes))

    return GPF.createProduct('S2Resampling', params, source)

def estimate_spi(source):
    BandDescriptor = snappy.jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    spis = snappy.jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', len(spi_list))
    for idx, spi in enumerate(spi_list):
        spi_band = BandDescriptor()
        spi_band.name = str(spi)
        spi_band.type = 'float32'
        spi_band.expression = str(spi_list[spi])

        spis[idx] = spi_band

    params = HashMap()
    params.put('targetBandDescriptors', spis)

    return GPF.createProduct('BandMaths', params, source)


class SpectralIndexS2:
    def __init__(self, s2_file, out_dir):
        self.s2_file = s2_file
        self.out_dir = out_dir

    def __process__(self):
        gc.enable()
        gc.collect()

        start_time = time.time()

        filename = os.path.basename(os.path.dirname(self.s2_file))[:-5]
        out_filename = os.path.join(self.out_dir, filename+'_indices')
        print("Start Sentinel-2 Spectral Index processing --- %s ---" % (filename))

        s2 = ProductIO.readProduct(self.s2_file)
        s2_res = resample(s2, tarRes=20)
        s2_res_spi = estimate_spi(s2_res)
        ProductIO.writeProduct(s2_res_spi, out_filename, 'GeoTIFF-BigTIFF')
        del s2_res, s2_res_spi

        s2.dispose()
        s2.closeIO()

        print("Complete Sentinel-2 Spectral Index processing --- %s : %s seconds ---" % (filename, time.time() - start_time))

        return out_filename


if __name__ == '__main__':
    in_dir = 'C:/Users/USER/Downloads/test/data'
    out_dir = 'C:/Users/USER/Downloads/test/out'
    s2_file = glob.glob(os.path.join(in_dir, 'S2*SAFE', 'MTD_*.xml'))[0]
    S2VI = SpectralIndexS2(s2_file, out_dir)
    s2_output = S2VI.__process__()

    print(s2_output)