import os
import glob
import gc
import time
import geopandas as gpd
import snappy
from snappy import ProductIO, GPF, HashMap, WKTReader


# get snappy operators
GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
# get Hashmap key-value pairs
HashMap = snappy.jpy.get_type('java.util.HashMap')


# functions for SLC data
def split_swath(source, subswath, polarization='VV'):
    params = HashMap()
    params.put('subswath', subswath)
    params.put('selectedPolarisations', polarization)

    return GPF.createProduct('TOPSAR-Split', params, source)

def apply_calibration(source, polarization='VV', out_complex='False', out_sigma='True'):
    params = HashMap()
    params.put('outputImageInComplex', out_complex)
    params.put('outputSigmaBand', out_sigma)
    params.put('selectedPolarisations', polarization)

    return GPF.createProduct('Calibration', params, source)

def apply_deburst(source, polarization='VV'):
    params = HashMap()
    params.put('selectedPolarisations', polarization)

    return GPF.createProduct('TOPSAR-Deburst', params, source)

def apply_speckle_filter(source):
    params = HashMap()
    params.put('filter', 'Lee Sigma')
    params.put('numLooksStr', '1')
    params.put('windowSize', '7x7')
    params.put('targetWindowSizeStr', '3x3')
    params.put('sigmaStr', '0.9')

    return GPF.createProduct('Speckle-Filter', params, source)

def estimate_polarimetric_matrix(source):
    params = HashMap()
    params.put('matrix', 'C2')

    return GPF.createProduct('Polarimetric-Matrices', params, source)

def apply_polarimetric_speckle_filter(source):
    params = HashMap()
    params.put('filter', 'Refined Lee Filter')
    params.put('numLooksStr', '3')
    params.put('windowSize', '5x5')

    return GPF.createProduct('Polarimetric-Speckle-Filter', params, source)

def apply_polarimetric_decomposition(source):
    params = HashMap()
    params.put('decomposition', 'H-Alpha Dual Pol Decomposition')
    params.put('windowSize', '5')
    params.put('outputHAAlpha', True)

    return GPF.createProduct('Polarimetric-Decomposition', params, source)

# functions for GRD data
def apply_orbit(source):
    params = HashMap()
    params.put('orbitType', 'Sentinel Precise (Auto Download)')
    params.put('polyDegree', 3)
    params.put('continueOnFail', True)

    return GPF.createProduct('Apply-Orbit-File', params, source)

def remove_border_noise(source):
    params = HashMap()
    params.put('borderLimit', '2000')
    params.put('trimThreshold', '0.5')

    return GPF.createProduct('Remove-GRD-Border-Noise', params, source)

def remove_thermal_noise(source):
    params = HashMap()
    params.put('removeThermalNoise', True)

    return GPF.createProduct('ThermalNoiseRemoval', params, source)

# common functions
def apply_subset(source, wkt):
    geom = WKTReader().read(wkt)

    params = HashMap()
    params.put('copyMetadata', True)
    params.put('geoRegion', geom)

    return GPF.createProduct('Subset', params, source)

def apply_terrain_correction(source, out_resolution=20):
    params = HashMap()
    params.put('demName', 'SRTM 1Sec HGT')
    params.put('demResamplingMethod', 'BILINEAR_INTERPOLATION')
    params.put('imgResamplingMethod', 'BILINEAR_INTERPOLATION')
    params.put('pixelSpacingInMeter', str(out_resolution))
    params.put('mapProjection', 'AUTO:42001')  # UTM >> 'AUTO:42001', EPSG:4326 >> 'WGS84(DD)'
    params.put('nodataValueAtSea', 'False')
    params.put('maskOutAreaWithoutElevation', 'False')
    params.put('saveDEM', 'False')
    params.put('saveLatLon', 'False')
    params.put('saveIncidenceAngleFromEllipsoid', 'False')
    params.put('saveLocalIncidenceAngle', 'False')
    params.put('saveProjectedLocalIncidenceAngle', 'False')
    params.put('saveSelectedSourceBand', 'True')
    params.put('saveLayoverShadowMask', 'False')
    params.put('outputComplex', 'False')
    params.put('applyRadiometricNormalization', 'False')
    params.put('saveSigmaNought', 'False')
    params.put('saveGammaNought', 'False')
    params.put('saveBetaNought', 'False')

    return GPF.createProduct('Terrain-Correction', params, source)

def convert_db(source):
    params = HashMap()

    return GPF.createProduct('LinearToFromdB', params, source)


# get snappy module information
class SnappyInfo:
    def get_snappy_op_list(self):
        func_iter = GPF.getDefaultInstance().getOperatorSpiRegistry().getOperatorSpis().iterator()
        func_list = []
        while func_iter.hasNext():
            func = func_iter.next()
            func_list.append(func.getOperatorAlias())

        return func_list

    def get_snappy_op_help(self, operator):
        funcs = GPF.getDefaultInstance().getOperatorSpiRegistry().getOperatorSpi(operator)
        print('operator name : {}\n'.format(funcs.getOperatorDescriptor().getAlias()))
        print('operator parameters :\n')
        param_list = funcs.getOperatorDescriptor().getParameterDescriptors()
        param_summary = {}
        for param in param_list:
            print('{}: {}\ndefault value: {}\nvalue list: {}\n'.format(param.getName(), param.getDescription(),
                                                                       param.getDefaultValue(),
                                                                       list(param.getValueSet())))
            param_summary[param.getName()] = [param.getDefaultValue(), list(param.getValueSet())]

        return param_summary


# get intensity feature of GRD data
class IntensityGRD:
    def __init__(self, s1_file, polarization, out_dir, shp_file=None):
        self.s1_file = s1_file
        self.polarization = polarization
        self.out_dir = out_dir
        self.shp_file = shp_file

    def __process__(self):
        gc.enable()
        gc.collect()

        start_time = time.time()

        filename = os.path.basename(self.s1_file)[:-5]
        out_filename = os.path.join(self.out_dir, filename + '_int_' + 'aoi')
        print("Start Sentinel-1 GRD intensity processing --- %s ---" % (filename))

        s1_output = []

        s1 = ProductIO.readProduct(self.s1_file)

        s1_orb = apply_orbit(s1)
        s1_orb_bdr = remove_border_noise(s1_orb)
        s1_orb_bdr_tnr = remove_thermal_noise(s1_orb_bdr)
        s1_orb_bdr_tnr_cal = apply_calibration(s1_orb_bdr_tnr, polarization=self.polarization, out_complex='False', out_sigma='True')
        s1_orb_bdr_tnr_cal_spk = apply_speckle_filter(s1_orb_bdr_tnr_cal)
        s1_orb_bdr_tnr_cal_spk_tc = apply_terrain_correction(s1_orb_bdr_tnr_cal_spk, out_resolution=10)
        output = convert_db(s1_orb_bdr_tnr_cal_spk_tc)

        if self.shp_file is not None:
            gdf_aoi = gpd.read_file(self.shp_file)
            output = apply_subset(output, str(gdf_aoi['geometry'][0]))

        ProductIO.writeProduct(output, out_filename, 'GeoTIFF-BigTIFF')
        del s1_orb, s1_orb_bdr, s1_orb_bdr_tnr, s1_orb_bdr_tnr_cal, s1_orb_bdr_tnr_cal_spk, s1_orb_bdr_tnr_cal_spk_tc, output

        s1.dispose()
        s1.closeIO()

        print("Complete Sentinel-1 GRD intensity processing --- %s : %s seconds ---"
              % (filename, time.time() - start_time))

        s1_output.append(out_filename)

        return s1_output


# get intensity feature of SLC data
class IntensitySLC:
    def __init__(self, s1_file, polarization, out_dir):
        self.s1_file = s1_file
        self.polarization = polarization
        self.out_dir = out_dir

    def __process__(self):
        gc.enable()
        gc.collect()

        start_time = time.time()

        filename = os.path.basename(self.s1_file)[:-5]
        print("Start Sentinel-1 SLC intensity processing --- %s ---" % (filename))

        s1_output = []

        s1 = ProductIO.readProduct(self.s1_file)

        swath_list = ['IW1', 'IW2', 'IW3']
        for swath in swath_list:
            out_filename = os.path.join(self.out_dir, filename + '_int_' + swath)
            s1_sub = split_swath(s1, swath, polarization=self.polarization)
            s1_sub_cal = apply_calibration(s1_sub, polarization=self.polarization, out_complex='False', out_sigma='True')
            s1_sub_cal_deb = apply_deburst(s1_sub_cal, polarization=self.polarization)
            s1_sub_cal_deb_spk = apply_speckle_filter(s1_sub_cal_deb)
            s1_sub_cal_deb_spk_tc = apply_terrain_correction(s1_sub_cal_deb_spk, out_resolution=20)
            output = convert_db(s1_sub_cal_deb_spk_tc)
            ProductIO.writeProduct(output, out_filename, 'GeoTIFF-BigTIFF')

            s1_output.append(out_filename)

            del s1_sub, s1_sub_cal, s1_sub_cal_deb, s1_sub_cal_deb_spk, s1_sub_cal_deb_spk_tc, output

            break

        s1.dispose()
        s1.closeIO()

        print("Complete Sentinel-1 SLC intensity processing --- %s : %s seconds ---"
              % (filename, time.time() - start_time))

        return s1_output


# get polarimetric features of SLC data
class PolarimetricSLC:
    def __init__(self, s1_file, out_dir):
        self.s1_file = s1_file
        self.out_dir = out_dir

    def __process__(self):
        gc.enable()
        gc.collect()

        start_time = time.time()

        filename = os.path.basename(self.s1_file)[:-5]
        print("Start Sentinel-1 SLC dual polarimetric decomposition processing --- %s ---" % (filename))

        s1_output = []

        s1 = ProductIO.readProduct(self.s1_file)

        swath_list = ['IW1', 'IW2', 'IW3']
        for swath in swath_list:
            out_filename = os.path.join(self.out_dir, filename + '_pol_' + swath)
            s1_sub = split_swath(s1, swath, polarization='VV,VH')
            s1_sub_cal = apply_calibration(s1_sub, polarization='VV,VH', out_complex='True', out_sigma='False')
            s1_sub_cal_deb = apply_deburst(s1_sub_cal, polarization='VV,VH')
            s1_sub_cal_deb_mat = estimate_polarimetric_matrix(s1_sub_cal_deb)
            s1_sub_cal_deb_mat_spk = apply_polarimetric_speckle_filter(s1_sub_cal_deb_mat)
            s1_sub_cal_deb_mat_spk_decomp = apply_polarimetric_decomposition(s1_sub_cal_deb_mat_spk)
            output = apply_terrain_correction(s1_sub_cal_deb_mat_spk_decomp, out_resolution=20)
            ProductIO.writeProduct(output, out_filename, 'GeoTIFF-BigTIFF')

            s1_output.append(out_filename)

            del s1_sub, s1_sub_cal, s1_sub_cal_deb, s1_sub_cal_deb_mat, s1_sub_cal_deb_mat_spk, s1_sub_cal_deb_mat_spk_decomp, output

            break

        s1.dispose()
        s1.closeIO()

        print("Complete Sentinel-1 SLC dual polarimetric decomposition processing --- %s : %s seconds ---"
              % (filename, time.time() - start_time))

        return s1_output


if __name__ == '__main__':
    # snappy_info = SnappyInfo()
    # func_list = snappy_info.get_snappy_op_list()
    # print(func_list)
    # params_summary = snappy_info.get_snappy_op_help('Polarimetric-Speckle-Filter')
    # print(params_summary)

    in_dir = 'C:/Users/USER/Downloads/test/data/127_120'
    out_dir = 'C:/Users/USER/Downloads/test/out'
    shp_dir = 'C:/Users/USER/Downloads/test/aoi'
    grd_file = glob.glob(os.path.join(in_dir, 'S1*.SAFE'))[0]
    slc_file = glob.glob(os.path.join(in_dir, 'S1*.SAFE'))[-1]
    shp_file = glob.glob(os.path.join(shp_dir, '*.shp'))[0]

    intS1GRD = IntensityGRD(grd_file, 'VV', out_dir, shp_file)
    s1_grd = intS1GRD.__process__()
    print(s1_grd)

    # intS1SLC = IntensitySLC(slc_file, 'VV', out_dir)
    # s1_slc = intS1SLC.__process__()
    # print(s1_slc)

    # polS1SLC = PolarimetricSLC(slc_file, out_dir)
    # s1_pol = polS1SLC.__process__()
    # print(s1_pol)