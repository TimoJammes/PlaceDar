AIRPORT_RADAR_LAT = 43.6701
AIRPORT_RADAR_LON = 7.213

AIRPORT_LAT, AIRPORT_LON = 43.65986322992161, 7.214175668283692
AIRPORT_ALT = 3

MAP_AREA_KM2 = 14396.63694615332

MAP_MIN_LAT, MAP_MAX_LAT = 43.12166666666667, 44.20166666666667
MAP_MIN_LON, MAP_MAX_LON = 6.460833333333333, 7.948333333333334

#elipse radii of earth
a = 6378137.0
b = 6356752.314245

e2 = 1 - (b*b)/(a*a)

EARTH_RADIUS_M = 6371000

EARTH_RADIUS_EFF = EARTH_RADIUS_M * 4/3


MAX_RADAR_DISTANCE_METERS = 474.112 * 1000


# if __name__ == "__main__":
#     import numpy as np
#     # import constants as c
#     from geo_utils import get_geodetic_data

#     lat, lon, ter = get_geodetic_data()
    
#     print(area/1000000)
