import geopandas as gpd
from shapely.geometry import Polygon


def point_to_polygon(points, out_filename):
    lon_list = []
    lat_list = []
    for idx in range(len(points)):
        lon_list.append(points[idx][0])
        lat_list.append(points[idx][1])

    polygon = gpd.GeoDataFrame(index=[0], crs={'init': 'epsg:4326'},
                               geometry=[Polygon(zip(lon_list, lat_list))])
    polygon.to_file(out_filename, driver="ESRI Shapefile")
    print("Succeed to write shapefile %s" % (out_filename))

    return


if __name__ == '__main__':
    points = ((122.943, 37.080), (128.737, 37.080), (128.737, 39.545), (122.943, 39.545), (122.943, 37.080))
    out_filename = 'C:/Users/USER/Downloads/test/out/sample.shp'
    point_to_polygon(points, out_filename)