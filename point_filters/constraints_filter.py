# import matplotlib.pyplot as plt
from time import time

import numpy as np

# import sys, os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shapely.geometry import Point

import geopandas as gpd

import geo_utils as geo

import constants as gc
from sklearn.neighbors import KDTree
from scipy.spatial import cKDTree #type: ignore
from scipy.interpolate import RegularGridInterpolator

import pickle
import os
# import constraints_related_code.filtering.electrical_filtering as elec
# import constraints_related_code.filtering.road_filtering as road
# import constraints_related_code.filtering.building_filtering as building
# import constraints_related_code.filtering.country_filtering as country
# import constraints_related_code.filtering.nice_filtering as nice
# import constraints_related_code.filtering.ocean_filtering as ocean
# import constraints_related_code.filtering.airport_filtering as airport


def max_dist_from_airport_filter(lon_idx, lat_idx, lons, lats, ter, max_dist):
    
    lon_indices_filtered, lat_indices_filtered = [], []    
    for lon_idx, lat_idx in zip(lon_idx, lat_idx):
        X1, Y1, Z1 = geo.convert_to_ecef_vectorized(gc.AIRPORT_LAT, gc.AIRPORT_LON, gc.AIRPORT_ALT)
        lat, lon = lats[lat_idx], lons[lon_idx]
        
        X2, Y2, Z2 = geo.convert_to_ecef_vectorized(lat, lon,
                                            ter[np.argmin(np.abs(lats-lat)), np.argmin(np.abs(lons-lon))])
        
        distance = np.sqrt((X2-X1)**2 + (Y2-Y1)**2 + (Z2-Z1)**2)
        
        if distance <= max_dist:
            lon_indices_filtered.append(lon_idx)
            lat_indices_filtered.append(lat_idx)
    
    return np.array(lon_indices_filtered, dtype=int), np.array(lat_indices_filtered, dtype=int)


def ocean_filter(lon_idxs, lat_idxs, lon, lat, ter):
    
    assert len(lon_idxs) == len(lat_idxs)

    ocean_mask = ter == 0
    mask = ~ocean_mask[lat_idxs, lon_idxs]
    lon_filt = lon_idxs[mask]
    lat_filt = lat_idxs[mask]
    # filtered_lon_idxs = []
    # filtered_lat_idxs = []
    
    # for (lon_idx, lat_idx) in zip(lon_idxs, lat_idxs):
    #     if ocean_mask[lat_idx, lon_idx]:
    #          filtered_lon_idxs.append(lon_idx)
    #          filtered_lat_idxs.append(lat_idx)
    
    
    return lon_filt, lat_filt


def nice_filter(lon_indices, lat_indices, lon, lat):
    """
    Filter terrain points that are OUTSIDE Italy.
    
    Parameters:
    -----------
    lat_indices : array-like
        Indices into the global lat array for terrain points
    lon_indices : array-like
        Indices into the global lon array for terrain points
    lat : array-like
        1D array of latitude values
    lon : array-like
        1D array of longitude values
    
    Returns:
    --------
    lat_idx_filtered : array
        Filtered indices into the lat array (points outside Italy)
    lon_idx_filtered : array
        Filtered indices into the lon array (points outside Italy)
    """
    
    # Get coordinate values from indices
    lat_values = lat[lat_indices]
    lon_values = lon[lon_indices]
    
    # Create points GeoDataFrame
    geometry = [Point(lon_val, lat_val) for lon_val, lat_val in zip(lon_values, lat_values)]
    points_geo = gpd.GeoDataFrame(geometry=geometry, crs="EPSG:4326")
    
    # Spatial join to find points within Italy
    with open('data/constraints_related/data_regions/nice_polygon_gdf.pkl', 'rb') as f:
        nice_polygon_gdf = pickle.load(f)

    points_in_italy = gpd.sjoin(points_geo, nice_polygon_gdf, predicate='within')
    
    # Get mask of which points are NOT in Italy (flip with ~)
    mask = ~points_geo.index.isin(points_in_italy.index)
    
    # Filter indices
    lat_idx_filtered = lat_indices[mask]
    lon_idx_filtered = lon_indices[mask]
    
    return lon_idx_filtered, lat_idx_filtered 


def italy_filter(lon_indices, lat_indices, lon, lat):
    """
    Filter terrain points that are OUTSIDE Italy.
    
    Parameters:
    -----------
    lat_indices : array-like
        Indices into the global lat array for terrain points
    lon_indices : array-like
        Indices into the global lon array for terrain points
    lat : array-like
        1D array of latitude values
    lon : array-like
        1D array of longitude values
    
    Returns:
    --------
    lat_idx_filtered : array
        Filtered indices into the lat array (points outside Italy)
    lon_idx_filtered : array
        Filtered indices into the lon array (points outside Italy)
    """
    
    # Get coordinate values from indices
    lat_values = lat[lat_indices]
    lon_values = lon[lon_indices]
    
    # Create points GeoDataFrame
    geometry = [Point(lon_val, lat_val) for lon_val, lat_val in zip(lon_values, lat_values)]
    points_geo = gpd.GeoDataFrame(geometry=geometry, crs="EPSG:4326")
    
    # Spatial join to find points within Italy
    with open('data/constraints_related/data_regions/italy_polygon.pkl', 'rb') as f:
        italy_polygon = pickle.load(f)
        
    points_in_italy = gpd.sjoin(points_geo, italy_polygon, predicate='within')
    
    # Get mask of which points are NOT in Italy (flip with ~)
    mask = ~points_geo.index.isin(points_in_italy.index)
    
    # Filter indices
    lat_idx_filtered = lat_indices[mask]
    lon_idx_filtered = lon_indices[mask]
    
    return lon_idx_filtered, lat_idx_filtered 

def  monaco_filter(lon_indices, lat_indices, lon, lat):
    """
    Filter terrain points that are OUTSIDE Italy.
    
    Parameters:
    -----------
    lat_indices : array-like
        Indices into the global lat array for terrain points
    lon_indices : array-like
        Indices into the global lon array for terrain points
    lat : array-like
        1D array of latitude values
    lon : array-like
        1D array of longitude values
    
    Returns:
    --------
    lat_idx_filtered : array
        Filtered indices into the lat array (points outside Italy)
    lon_idx_filtered : array
        Filtered indices into the lon array (points outside Italy)
    """
    
    # Get coordinate values from indices
    lat_values = lat[lat_indices]
    lon_values = lon[lon_indices]
    
    # Create points GeoDataFrame
    geometry = [Point(lon_val, lat_val) for lon_val, lat_val in zip(lon_values, lat_values)]
    points_geo = gpd.GeoDataFrame(geometry=geometry, crs="EPSG:4326")
    
    # Spatial join to find points within Italy
    with open('data/constraints_related/data_regions/monaco_polygon.pkl', 'rb') as f:
        monaco_polygon = pickle.load(f)
    points_in_monaco = gpd.sjoin(points_geo, monaco_polygon, predicate='within')
    
    # Get mask of which points are NOT in Italy (flip with ~)
    mask = ~points_geo.index.isin(points_in_monaco.index)
    
    # Filter indices
    lat_idx_filtered = lat_indices[mask]
    lon_idx_filtered = lon_indices[mask]
    
    return lon_idx_filtered, lat_idx_filtered 



def building_filter_idx(lon_indices, lat_indices, lon, lat, ter, min_dist):
    """
    Filter terrain points outside min_dist of buildings (exclude points too close to buildings).
    
    Parameters:
    -----------
    lat_indices : array-like
        Indices into the global lat array for terrain points
    lon_indices : array-like
        Indices into the global lon array for terrain points
    lat : array-like
        1D array of latitude values
    lon : array-like
        1D array of longitude values
    ter : 2D array
        Terrain altitudes where ter[i, j] is altitude at lat[i], lon[j]
    min_dist : float
        Minimum distance in meters from buildings (exclusion zone radius)
    
    Returns:
    --------
    lat_idx_filtered : array
        Filtered indices into the lat array (points outside exclusion zone)
    lon_idx_filtered : array
        Filtered indices into the lon array (points outside exclusion zone)
    """
    
    # Get coordinate and terrain values from indices
    lat_values = lat[lat_indices]
    lon_values = lon[lon_indices]
    ter_values = ter[lat_indices, lon_indices]
    
    # Get building coordinates
    file_buildings = np.load("data/constraints_related/data_buildings/buildings_latlon.npz")
    lats_buildings=file_buildings["lat"]
    lons_buildings=file_buildings["lon"]
    
    idx_lat = np.searchsorted(lat, lats_buildings)
    idx_lon = np.searchsorted(lon, lons_buildings)    
    building_alt = ter[idx_lat, idx_lon]
    
    # Convert terrain points to ECEF
    X_flat, Y_flat, Z_flat = geo.convert_to_ecef_vectorized(lat_values, lon_values, ter_values)
    terrain_XYZ = np.column_stack((X_flat, Y_flat, Z_flat))
    
    # Convert buildings to ECEF
    X_building, Y_building, Z_building = geo.convert_to_ecef_vectorized(lats_buildings, lons_buildings, building_alt)
    building_XYZ = np.column_stack((X_building, Y_building, Z_building))
    
    # Build KDTree and find points within exclusion zone
    tree = KDTree(building_XYZ)
    distances, _ = tree.query(terrain_XYZ, k=1)
    distances = distances.ravel() 
    # indices = tree.query_radius(elec_XYZ, r=max_dist)
    # terrain_idx = np.unique(np.concatenate(indices))
    mask = distances >= min_dist
    
    # Return filtered indices
    lat_idx_filtered = lat_indices[mask]
    lon_idx_filtered = lon_indices[mask]
    
    return lon_idx_filtered, lat_idx_filtered 


def road_filter_idx_alt(lon_indices, lat_indices, lon, lat, ter, max_dist, sample_distance_m=50):
    """
    Filter terrain points within max_dist of roads using 3D distances (including altitude).

    Args:
        lon_indices: indices into global lon array
        lat_indices: indices into global lat array
        lon: 1D array of longitude grid
        lat: 1D array of latitude grid
        ter: 2D terrain altitude array (n_lat, n_lon)
        max_dist: maximum 3D distance in meters
        sample_distance_m: spacing for road point sampling

    Returns:
        lon_idx_filtered, lat_idx_filtered: filtered terrain indices
    """
    # Load roads GeoPackage

    # Slice terrain points
    lat_vals = lat[lat_indices]
    lon_vals = lon[lon_indices]
    alt_vals = ter[lat_indices, lon_indices]

    # --- Convert terrain to projected CRS once ---
    # Create 3D terrain points in meters
    terrain_points_3d = lon_lat_alt_to_utm(lon_vals, lat_vals, alt_vals)

    # --- Sample road points ---
    # road_points_3d = get_road_points_with_altitude_optimized(roads, lon, lat, ter, sample_distance_m)
    
    road_points_3d = np.load("data/constraints_related/data_roads/road_points_sampled_3D.npy")
    # np.save("data/constraints_related/data_roads/road_points_sampled_3D", road_points_3d)
    # assert False
    # if road_points_3d.size == 0:
    #     return np.array([]), np.array([])

    # --- KDTree proximity check with upper bound ---
    tree = cKDTree(road_points_3d)
    distances, _ = tree.query(terrain_points_3d, distance_upper_bound=max_dist)
    mask = distances != np.inf  # True for points within max_dist

    # Filter terrain indices
    lon_idx_filtered = lon_indices[mask]
    lat_idx_filtered = lat_indices[mask]

    return lon_idx_filtered, lat_idx_filtered


def lon_lat_alt_to_utm(lon_vals, lat_vals, alt_vals, utm_epsg="EPSG:32632"):
    """
    Convert lon/lat/alt arrays to projected meters in specified UTM CRS.
    Returns Nx3 array of [X, Y, Z] in meters.
    """
    import pyproj
    proj = pyproj.Transformer.from_crs("EPSG:4326", utm_epsg, always_xy=True)
    X, Y = proj.transform(lon_vals, lat_vals)
    Z = alt_vals
    return np.column_stack([X, Y, Z])


def get_road_points_with_altitude_optimized(roads_geo, lon_grid, lat_grid, ter, sample_distance_m=50):
    """
    Sample road points and get their altitudes from terrain efficiently.

    Returns Nx3 array of [X, Y, Z] in meters (projected CRS).
    """
    # Project roads once
    utm_epsg = "EPSG:32632"
    roads_proj = roads_geo.to_crs(utm_epsg)

    # Precompute RegularGridInterpolator for terrain
    interpolator = RegularGridInterpolator(
        (lat_grid, lon_grid), ter, bounds_error=False, fill_value=0
    )

    road_points = []
    for geom in roads_proj.geometry:
        length = geom.length
        num_points = max(int(length / sample_distance_m), 2)
        distances = np.linspace(0, length, num_points)
        points = [geom.interpolate(d) for d in distances]
        road_points.extend(points)

    if not road_points:
        return np.array([])

    # Convert points back to lon/lat
    points_geo: gpd.GeoDataFrame = gpd.GeoDataFrame(geometry=road_points, crs=utm_epsg).to_crs("EPSG:4326")
    coords = np.array([[p.x, p.y] for p in points_geo.geometry]) #type: ignore

    # Interpolate altitudes
    altitudes = interpolator(np.column_stack([coords[:, 1], coords[:, 0]]))  # lat, lon order

    # Convert to projected CRS for KDTree
    road_points_3d = lon_lat_alt_to_utm(coords[:, 0], coords[:, 1], altitudes, utm_epsg)
    return road_points_3d



def electrical_filter_idx(lon_indices, lat_indices, lon, lat, ter, max_dist):
    """
    Filter terrain points within max_dist of electrical infrastructure.
    
    Parameters:
    -----------
    lat_indices : array-like
        Indices into the global lat array for terrain points
    lon_indices : array-like
        Indices into the global lon array for terrain points
    ter : 2D array
        Terrain altitudes where ter[i, j] is altitude at lat[i], lon[j]
    max_dist : float
        Maximum distance in meters from electrical posts
    
    Returns:
    --------
    lon_idx_filtered : array
        Filtered indices into the lon array
    lat_idx_filtered : array
        Filtered indices into the lat array
    """
    
    # Get terrain values from indices
    ter_values = ter[lat_indices, lon_indices]
    
    # Need to get lat/lon values - assuming they're available in scope
    # or you need to pass lat and lon arrays as well
    lat_values = lat[lat_indices]
    lon_values = lon[lon_indices]
    
    # Get electrical infrastructure coordinates
    file_elec = np.load("data/constraints_related/data_elec/elec_points_latlon.npz")
    lats_elec=file_elec["lat"]
    lons_elec=file_elec["lon"]

    # elec_lat = elec.all_coords_df_in["latitude"].values
    # elec_lon = elec.all_coords_df_in["longitude"].values
    # elec_alt = np.empty_like(elec_lat, dtype=float)
    
    # for i, (el_lat, el_lon) in enumerate(zip(elec_lat, elec_lon)):
    #     idx_lat = np.argmin(np.abs(lat - el_lat))
    #     idx_lon = np.argmin(np.abs(lon - el_lon))
    
    idx_lat = np.searchsorted(lat, lats_elec)
    idx_lon = np.searchsorted(lon, lons_elec)    
    elec_alt = ter[idx_lat, idx_lon]

    # Convert terrain to ECEF
    X_flat, Y_flat, Z_flat = geo.convert_to_ecef_vectorized(lat_values, lon_values, ter_values)
    terrain_XYZ = np.column_stack((X_flat, Y_flat, Z_flat))
    
    # Convert electrical infrastructure to ECEF
    X_elec, Y_elec, Z_elec = geo.convert_to_ecef_vectorized(lats_elec, lons_elec, elec_alt)
    elec_XYZ = np.column_stack((X_elec, Y_elec, Z_elec))
    
    # Build KDTree and query
    tree = KDTree(elec_XYZ)
    distances, _ = tree.query(terrain_XYZ, k=1)
    distances = distances.ravel() 
    # indices = tree.query_radius(elec_XYZ, r=max_dist)
    # terrain_idx = np.unique(np.concatenate(indices))
    mask = distances <= max_dist
    # Return filtered indices
    lat_idx_filtered = lat_indices[mask]
    lon_idx_filtered = lon_indices[mask]
    
    return lon_idx_filtered, lat_idx_filtered 
 

def full_filter(lons, lats, ter,
                max_distance_from_airport=50000,
                max_distance_from_elec=500,
                min_distance_from_building=1000,
                max_distance_from_road=500,
                doElec=True,
                doRoads=True,
                doBuildings=True,
                doMaxDistFromAirport=True,
                doNoOcean=True,
                doNoNice=True,
                doOnlyFrance=True):
    
    info = {"max_distance_from_airport":max_distance_from_airport,
            "max_distance_from_elec": max_distance_from_elec,
            "min_distance_from_building": min_distance_from_building,
            "max_distance_from_road": max_distance_from_road,
            "doElec": doElec,
            "doRoads": doRoads,
            "doBuildings": doBuildings,
            "doMaxDistFromAirport": doMaxDistFromAirport,
            "doNoOcean": doNoOcean,
            "doNoNice": doNoNice,
            "doOnlyFrance": doOnlyFrance
            }
    
    info = {k: np.array(v) for k, v in info.items()}
        
    start = time()
    
    n_lat, n_lon = ter.shape
    lat_indices_filtered = np.repeat(np.arange(n_lat), n_lon)
    lon_indices_filtered = np.tile(np.arange(n_lon), n_lat)

    # lons_filtered = lons
    # lats_filtered = lats
    
    if doElec:
        print("Starting Electric filtering...")
        s = time()
        # lons_filtered, lats_filtered = elec.electrical_filter(lons, lats, ter, 500)
        lon_indices_filtered, lat_indices_filtered = electrical_filter_idx(lon_indices_filtered, lat_indices_filtered,
                                                                                lons, lats, ter,
                                                                                max_distance_from_elec)
        
        print(f"Electric filtering took {round(time()-s, 1)} seconds.")
    
    if doRoads:
        print("Starting Road filtering...")
        s = time()
        lon_indices_filtered, lat_indices_filtered = road_filter_idx_alt(lon_indices_filtered, lat_indices_filtered,
                                                            lons, lats, ter,
                                                            max_distance_from_road)
        print(f"Road filtering took {round(time()-s, 1)} seconds.")
    
    if doBuildings:
        print("Starting Building filtering...")
        s = time()
        lon_indices_filtered, lat_indices_filtered = building_filter_idx(lon_indices_filtered, lat_indices_filtered,
                                                                    lons, lats, ter,
                                                                    min_distance_from_building)
        print(f"Building filtering took {round(time()-s, 1)} seconds.")
    
    if doMaxDistFromAirport:
        print("Starting Airport Distance filtering...")
        s = time()
        lon_indices_filtered, lat_indices_filtered = max_dist_from_airport_filter(lon_indices_filtered, lat_indices_filtered, lons, lats, ter, max_distance_from_airport)
        print(f"Airport Distance filtering took {round(time()-s, 1)} seconds.")
        
    if doNoOcean:
        print("Starting Ocean filtering...")
        s = time()
        lon_indices_filtered, lat_indices_filtered = ocean_filter(lon_indices_filtered, lat_indices_filtered,
                                                                        lons, lats, ter)
        print(f"Ocean filtering took {round(time()-s, 1)} seconds.")
    if doOnlyFrance:
        print("Starting Country filtering...")
        s = time()
        lon_indices_filtered, lat_indices_filtered = italy_filter(lon_indices_filtered, lat_indices_filtered,
                                                                        lons, lats)
        lon_indices_filtered, lat_indices_filtered = monaco_filter(lon_indices_filtered, lat_indices_filtered,
                                                                        lons, lats)
        print(f"Country filtering took {round(time()-s, 1)} seconds.")
    if doNoNice:
        print("Starting Nice filtering...")
        s = time()
        lon_indices_filtered, lat_indices_filtered = nice_filter(lon_indices_filtered, lat_indices_filtered,
                                                                        lons, lats)
        print(f"Nice filtering took {round(time()-s, 1)} seconds.")
        
    
    
                
        
    if not(doElec or doRoads or doBuildings or doMaxDistFromAirport or doNoOcean or doNoNice or doOnlyFrance):
        print("WARNING: RETURNING ORIGINAL LONS AND LATS!")
        
    print(f"Filtering finished! Took {round(time()-start, 1)} seconds overall.\n")

    
    return lon_indices_filtered, lat_indices_filtered, info

def get_masks(lons, lats, ter,
                max_distance_from_elec=500,
                min_distance_from_building=1000,
                max_distance_from_road=500,
                ):
    
    info = {"max_distance_from_elec": max_distance_from_elec,
            "min_distance_from_building": min_distance_from_building,
            "max_distance_from_road": max_distance_from_road,
            }
    
    info = {k: np.array(v) for k, v in info.items()}
    
    masks = {}
    
    start = time()
    
    n_lat, n_lon = ter.shape
    
    lat_indices = np.repeat(np.arange(n_lat), n_lon)
    lon_indices = np.tile(np.arange(n_lon), n_lat)

    # lons_filtered = lons
    # lats_filtered = lats
    
    print("Getting Electric mask...")
    s = time()
    # lons_filtered, lats_filtered = elec.electrical_filter(lons, lats, ter, 500)
    valid_elec_lon_indices, valid_elec_lat_indices = electrical_filter_idx(lon_indices, lat_indices,
                                                                            lons, lats, ter,
                                                                            max_distance_from_elec)
    elec_mask = np.zeros((len(lats), len(lons)), dtype=np.int8)
    print(f"Getting electric mask took {round(time()-s, 1)} seconds.")

    # # Step 2: Find indices of your points in the full grid
    # for i in range(len(valid_elec_lon_indices)):
    #     lon_idx = np.where(lons == lons[valid_elec_lon_indices][i])[0][0]
    #     lat_idx = np.where(lats == lats[valid_elec_lat_indices][i])[0][0]
    #     elec_mask[lat_idx, lon_idx] = 1
    elec_mask[valid_elec_lat_indices, valid_elec_lon_indices] = 1
    # np.save("data/constraints_related/data_roads/valid_region_mask", mask)
    masks["elec"] = 1-elec_mask
    
    
    # if doRoads:
    print("Getting road mask...")
    s = time()
    valid_road_lon_indices, valid_road_lat_indices = road_filter_idx_alt(lon_indices, lat_indices,
                                                        lons, lats, ter,
                                                        max_distance_from_road)
    print(f"Getting road mask took {round(time()-s, 1)} seconds.")
    road_mask = np.zeros((len(lats), len(lons)), dtype=np.int8)

    # # Step 2: Find indices of your points in the full grid
    # for i in range(len(valid_road_lon_indices)):
    #     lon_idx = np.where(lons == lons[valid_road_lon_indices][i])[0][0]
    #     lat_idx = np.where(lats == lats[valid_road_lat_indices][i])[0][0]
    #     road_mask[lat_idx, lon_idx] = 1
    road_mask[valid_road_lat_indices, valid_road_lon_indices] = 1

    # np.save("data/constraints_related/data_roads/valid_region_mask", mask)
    masks["road"] = 1-road_mask

    # if doBuildings:
    print("Getting building mask...")
    s = time()
    valid_building_lon_indices, valid_building_lat_indices = building_filter_idx(lon_indices, lat_indices,
                                                                lons, lats, ter,
                                                                min_distance_from_building)
    print(f"Getting building mask took {round(time()-s, 1)} seconds.")
    building_mask = np.zeros((len(lats), len(lons)), dtype=np.int8)

    # # Step 2: Find indices of your points in the full grid
    # for i in range(len(valid_building_lon_indices)):
    #     lon_idx = np.where(lons == lons[valid_building_lon_indices][i])[0][0]
    #     lat_idx = np.where(lats == lats[valid_building_lat_indices][i])[0][0]
    #     building_mask[lat_idx, lon_idx] = 1
    building_mask[valid_building_lat_indices, valid_building_lon_indices] = 1

    # np.save("data/constraints_related/data_roads/valid_region_mask", mask)
    masks["building"] = 1-building_mask
    
        
    
    
                
        
    # if not(doElec or doRoads or doBuildings or doMaxDistFromAirport or doNoOcean or doNoNice or doOnlyFrance):
    #     print("WARNING: RETURNING ORIGINAL LONS AND LATS!")
        
    print(f"Finished getting masks! Took {round(time()-start, 1)} seconds overall.\n")

    
    return masks, info
