import numpy as np
import constants as gc

def convert_to_ecef_vectorized(lat_deg, lon_deg, alt_m):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    
    N = gc.a / np.sqrt(1 - gc.e2 * np.sin(lat)**2)
    
    X = (N + alt_m) * np.cos(lat) * np.cos(lon)
    Y = (N + alt_m) * np.cos(lat) * np.sin(lon)
    Z = (N * (gc.b**2/(gc.a**2)) + alt_m) * np.sin(lat)
    
    return X, Y, Z

def convert_to_ENU_vectorized(lat_degR, lon_degR, alt_mR, lat_deg, lon_deg, alt_m):
    # Convert points to ECEF
    Xp, Yp, Zp = convert_to_ecef_vectorized(lat_deg, lon_deg, alt_m)
    Xr, Yr, Zr = convert_to_ecef_vectorized(lat_degR, lon_degR, alt_mR)
    
    # Reference point angles (scalars)
    latR = np.radians(lat_degR)
    lonR = np.radians(lon_degR)
    
    # Precompute trig functions
    sin_latR = np.sin(latR)
    cos_latR = np.cos(latR)
    sin_lonR = np.sin(lonR)
    cos_lonR = np.cos(lonR)
    
    # Difference vectors
    dX = Xp - Xr
    dY = Yp - Yr
    dZ = Zp - Zr
    
    # Apply transformation (manual matrix multiplication for speed)
    x = -sin_lonR * dX + cos_lonR * dY
    y = -sin_latR * cos_lonR * dX - sin_latR * sin_lonR * dY + cos_latR * dZ
    z = cos_latR * cos_lonR * dX + cos_latR * sin_lonR * dY + sin_latR * dZ
    
    return x, y, z

def data_converter_to_ENU_vectorized(lat_degR, lon_degR, alt_mR, latitudes, longitudes, terrain):
    # Create 2D grids from 1D arrays
    lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing='ij')
    
    # Flatten for batch processing
    lat_flat = lat_grid.flatten()
    lon_flat = lon_grid.flatten()
    alt_flat = terrain.flatten()
    
    # Convert all points at once
    result = convert_to_ENU_vectorized(lat_degR, lon_degR, alt_mR, 
                                       lat_flat, lon_flat, alt_flat)
    
    # Reshape back to original grid shape
    converted_latitudes = result[0].reshape(terrain.shape)
    converted_longitudes = result[1].reshape(terrain.shape)
    converted_terrain = result[2].reshape(terrain.shape)
    
    return converted_latitudes, converted_longitudes, converted_terrain

def ecef_to_geodetic_vectorized(X, Y, Z):
    """Convert ECEF coordinates to geodetic (lat, lon, alt)"""
    # Iterative algorithm for geodetic conversion
    p = np.sqrt(X**2 + Y**2)
    lon = np.arctan2(Y, X)
    
    # Initial estimate for latitude
    lat = np.arctan2(Z, p * (1 - gc.e2))
    
    # Iterate to refine latitude and altitude
    for _ in range(5):  # Usually converges in 2-3 iterations
        N = gc.a / np.sqrt(1 - gc.e2 * np.sin(lat)**2)
        alt = p / np.cos(lat) - N
        lat = np.arctan2(Z, p * (1 - gc.e2 * N / (N + alt)))
    
    # Final altitude calculation
    N = gc.a / np.sqrt(1 - gc.e2 * np.sin(lat)**2)
    alt = p / np.cos(lat) - N
    
    lat_deg = np.degrees(lat)
    lon_deg = np.degrees(lon)
    
    return lat_deg, lon_deg, alt

def enu_to_geodetic_vectorized(lat_degR, lon_degR, alt_mR, e, n, u):
    """Convert ENU coordinates back to geodetic (lat, lon, alt)"""
    # Reference point angles
    latR = np.radians(lat_degR)
    lonR = np.radians(lon_degR)
    
    # Precompute trig functions
    sin_latR = np.sin(latR)
    cos_latR = np.cos(latR)
    sin_lonR = np.sin(lonR)
    cos_lonR = np.cos(lonR)
    
    # Inverse transformation matrix (transpose of ENU transformation)
    # This converts ENU back to ECEF delta
    dX = -sin_lonR * e - sin_latR * cos_lonR * n + cos_latR * cos_lonR * u
    dY = cos_lonR * e - sin_latR * sin_lonR * n + cos_latR * sin_lonR * u
    dZ = cos_latR * n + sin_latR * u
    
    # Get reference point in ECEF
    Xr, Yr, Zr = convert_to_ecef_vectorized(lat_degR, lon_degR, alt_mR)
    
    # Add delta to get target point in ECEF
    Xp = Xr + dX
    Yp = Yr + dY
    Zp = Zr + dZ
    
    # Convert ECEF back to geodetic
    lat_deg, lon_deg, alt_m = ecef_to_geodetic_vectorized(Xp, Yp, Zp)
    
    return lat_deg, lon_deg, alt_m

def get_ENU_data_airport_radar(height_above_terrain=20, geodetic_data_file="data/terrain/terrain_nice.npz"):
    
    lat0, lon0, alt0 = 43.6701, 7.2131, height_above_terrain+6
    
    
    lat, lon, ter = get_geodetic_data(geodetic_data_file)
    
    print("Converting geodetic data to local ENU...")
    
    E, N, U = data_converter_to_ENU_vectorized(lat0, lon0, alt0, lat, lon, ter)
    
    print("Done!")
    
    return E, N, U

def get_ENU_data(lon0, lat0, height_above_terrain=0.0, geodetic_data_file="data/terrain/terrain_nice.npz"):
    
    lat, lon, ter = get_geodetic_data(geodetic_data_file)
    
    alt0 = ter[np.argmin(np.abs(lat-lat0)), np.argmin(np.abs(lon-lon0))]
    
    
    E, N, U = data_converter_to_ENU_vectorized(lat0, lon0, alt0, lat, lon, ter)
    
    return E, N, U

def get_geodetic_data(geodetic_data_file="data/terrain/terrain_nice.npz"):
    
    """
    returns lat, lon, ter
    lon.shape = (n_lon,)
    lat.shape = (n_lat,)
    ter.shape = (n_lat, n_lon)
    """
    
    file = np.load(geodetic_data_file)
    
    lat = file["lat"]
    lon = file["lon"]
    ter = file["ter"]
    
    return lat, lon, ter

def get_altitude(lat: np.ndarray, lon: np.ndarray, ter: np.ndarray, pos_lat: float, pos_lon: float) -> float:
    
    return ter[np.argmin(np.abs(lat-pos_lat)), np.argmin(np.abs(lon-pos_lon))]

def isOnMap(point):
    
    """
    point: (lon, lat)
    """
    
    lon, lat = point
    
    return gc.MAP_MIN_LON <= lon <= gc.MAP_MAX_LON and gc.MAP_MIN_LAT <= lat <= gc.MAP_MAX_LAT


def get_area(lon, lat):
    
    lat_rad = np.deg2rad(lat)
    lon_rad = np.deg2rad(lon)

    area = (
        gc.EARTH_RADIUS_M**2
        * (lon_rad[-1] - lon_rad[0])
        * (np.sin(lat_rad[-1]) - np.sin(lat_rad[0]))
    )
    
    return area/1000000
