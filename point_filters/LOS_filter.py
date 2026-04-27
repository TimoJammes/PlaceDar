import numpy as np

import geo_utils as geo

import constants as gc

from typing import Callable

# from constraints_related_code.filtering.valid_points_latlon import los_tx_rx_fast

from dataclasses import dataclass

@dataclass
class Point3D:
    x: float
    y: float
    z: float
    
    def distance_to(self, other: 'Point3D') -> float:
        """Calculate Euclidean distance to another point."""
        return np.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )
    
    def interpolate(self, other: 'Point3D', t: float) -> 'Point3D':
        """Linearly interpolate between this point and another (t in [0,1])."""
        return Point3D(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
            self.z + (other.z - self.z) * t
        )
        
def create_grid_interpolator(E, N, U, lon0, lat0, alt0):
    """Create fast grid lookup"""
    dE = E[0, 1] - E[0, 0]  # Assuming uniform grid
    dN = N[1, 0] - N[0, 0]
    E_min, N_min = E[0, 0], N[0, 0]
    
    def get_terrain_height(x, y):
        """Fast terrain lookup with bounds checking"""
        idx_E = int(round((x - E_min) / dE))
        idx_N = int(round((y - N_min) / dN))
        
        if 0 <= idx_N < U.shape[0] and 0 <= idx_E < U.shape[1]:
            return U[idx_N, idx_E]
        
        # print("OUT OF BOUNDS")
        # assert False
        lat, lon, _ = geo.enu_to_geodetic_vectorized(lat0, lon0, alt0, x, y, 0)
        
        x, y, z = geo.convert_to_ENU_vectorized(lat0, lon0, alt0, lat, lon, 0)
        # print(x, y, z)
        # assert False
        z += (x**2+y**2)/(2*gc.EARTH_RADIUS_M)
        
        return z
    
        # return -np.inf  # Out of bounds
    
    return get_terrain_height

def has_line_of_sight(
    start: Point3D,
    end: Point3D,
    get_terrain_height: Callable[[float, float], float],
    E,N,U,
    grid_resolution: float = 90.0,
    clearance: float = 0.0,
) -> bool:
    """
    Test if there's a clear line of sight between two 3D points.
    
    Args:
        start: Starting point
        end: Ending point
        get_terrain_height: Function that returns terrain height at (x, y)
        grid_resolution: Terrain grid resolution in meters (default 90.0)
        clearance: Minimum height above terrain required (default 0.0)
    
    Returns:
        True if line of sight is clear, False if terrain blocks it
    """
    # Calculate 2D horizontal distance
    horizontal_distance = np.sqrt(
        (end.x - start.x)**2 + (end.y - start.y)**2
    )
    
    # Sample at least every grid cell, plus a minimum of 2 samples
    # We sample at half the grid resolution to ensure we don't miss terrain features
    sample_count = max(2, int(np.ceil(horizontal_distance / (grid_resolution / 2))))
    
    # print(sample_count)
    # Sample points along the line between start and end
    for i in range(1, sample_count):
        t = i / sample_count
        sample_point = start.interpolate(end, t)
        
        # Get terrain height at this x,y position
        terrain_height = get_terrain_height(sample_point.x, sample_point.y)
        
        # idx_E, idx_N = np.unravel_index(np.argmin(np.abs(E-sample_point.x)), E.shape)[1], np.unravel_index(np.argmin(np.abs(N-sample_point.y)), N.shape)[0]
        # terrain_height = U[idx_N, idx_E]
        # Check if the line passes below the terrain (plus clearance)
        if sample_point.z < terrain_height + clearance:
            return False
    
    return True


def terrain_height_nn(lats, lons, ter, lat, lon):
    """Nearest-neighbor terrain height lookup from (lats, lons, ter)."""
    i = np.argmin(np.abs(lats - lat))
    j = np.argmin(np.abs(lons - lon))
    return float(ter[i, j])

def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters (fast, good enough for this scale)."""
    R = 6371000.0
    
    # Quick check for very small distances (avoid trig)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    if abs(dlat) < 0.001 and abs(dlon) < 0.001:  # ~100m at equator
        # Flat earth approximation
        dx = R * np.radians(dlon) * np.cos(np.radians((lat1 + lat2) / 2))
        dy = R * np.radians(dlat)
        return np.sqrt(dx*dx + dy*dy)
    
    # Full haversine for larger distances
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(dlat)
    dlam = np.radians(dlon)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
    
    return 2 * R * np.arcsin(np.sqrt(a))

def los_radar_rx_fast(lats, lons, ter,
                      tx_lat, tx_lon, tx_alt,
                      rx_lat, rx_lon, rx_alt,
                      step_m=40.0,
                      do_earth_curvature=True):
    """
    Optimized terrain LOS test between TX (radar) and RX.
    Vectorized along the ray (no inner Python loop).
    Returns True if NOT blocked by terrain.
    
    Args:
        lats: 1D array of latitude grid
        lons: 1D array of longitude grid
        ter: 2D terrain elevation array
        tx_lat, tx_lon, tx_alt: Transmitter position and altitude
        rx_lat, rx_lon, rx_alt: Receiver position and altitude
        step_m: Step size in meters for sampling along the ray
        do_earth_curvature: Whether to account for Earth curvature
    
    Returns:
        True if line of sight is clear, False if blocked
    """
    dist = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)
    if dist < 1.0:
        return True

    n = int(dist // step_m)
    if n < 2:
        return True

    s = np.linspace(0.0, 1.0, n)

    lat_s = tx_lat + s * (rx_lat - tx_lat)
    lon_s = tx_lon + s * (rx_lon - tx_lon)
    z_line = tx_alt + s * (rx_alt - tx_alt)

    if do_earth_curvature:
        # Curvature correction
        x = s * dist
        curv_drop = (x * (dist - x)) / (2.0 * gc.EARTH_RADIUS_EFF)
        z_line -= curv_drop
    
    # **OPTIMIZED**: Pre-compute indices once using searchsorted
    i = np.searchsorted(lats, lat_s)
    j = np.searchsorted(lons, lon_s)
    
    # Clamp indices to valid range
    i = np.clip(i, 0, len(lats) - 1)
    j = np.clip(j, 0, len(lons) - 1)
    
    z_terr = ter[i, j]

    return not np.any(z_terr > z_line)

def LOS_filter(lon, lat, alt,
               lons_idx, lats_idx,
               radar_height, do_earth_curvature, airport_height=10.0,
               lat0=float(gc.AIRPORT_LAT),
               lon0=float(gc.AIRPORT_LON),
               alt0=float(gc.AIRPORT_ALT)
               ):
    
        
    E, N, U = geo.get_ENU_data(lon0, lat0, alt0)
    
    get_terrain_height = create_grid_interpolator(E, N, U, lon0, lat0, alt0)
    
    airport_pos = Point3D(0, 0, 0)
    
    filtered_lats = []
    filtered_lons = []
    filtered_alts = []
        
    for i, idx in enumerate(zip(lats_idx, lons_idx)):
                
        idx_lat, idx_lon = idx
        
        pos_alt = alt[idx_lat, idx_lon]
        x, y, z = geo.convert_to_ENU_vectorized(lat0, lon0, alt0, lat[idx_lat], lon[idx_lon], pos_alt)
        # z += (x**2+y**2)/(2*gc.EARTH_RADIUS_M)
        
        
        pos = Point3D(x, y, z+radar_height)
        
        if has_line_of_sight(pos, airport_pos, get_terrain_height, E, N, U, grid_resolution=90, clearance=-200):
            filtered_lats.append(lat[idx_lat])
            filtered_lons.append(lon[idx_lon])
            filtered_alts.append(pos_alt)
        
    
        if i % (len(lats_idx)//100) == 0:
            print(f"{round(i/len(lats_idx)*100)}%", end="\r")
            
    
    print(len(filtered_lats))
    filtered_filtered_lats = []
    filtered_filtered_lons = []
    filtered_filtered_alts = []

    for i, pos in enumerate(zip(filtered_lons, filtered_lats, filtered_alts)):
        if i % (len(filtered_lons)//100) == 0:
            print(f"{round(i/len(filtered_lons)*100)}%", end="\r")
        
        lo, la, a = pos
        
        # Use optimized radar LOS function
        tx_alt = a + radar_height
        rx_alt = alt0 + airport_height
        
        if los_radar_rx_fast(lat, lon, alt, 
                            la, lo, tx_alt,
                            lat0, lon0, rx_alt,
                            step_m=40.0,
                            do_earth_curvature=do_earth_curvature):
            filtered_filtered_lats.append(la)
            filtered_filtered_lons.append(lo)
            filtered_filtered_alts.append(a)
            

    filtered_alts = filtered_filtered_alts
    filtered_lons = filtered_filtered_lons
    filtered_lats = filtered_filtered_lats
    
    return filtered_lons, filtered_lats, filtered_alts
