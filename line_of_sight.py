import numpy as np
np.seterr(all='raise')

from time import time

import geo_utils as geo
from pyproj import Geod

import constants as gc
from typing import Callable

from dataclasses import dataclass

@dataclass
class Point3D:
    x: float = -np.inf
    y: float = -np.inf
    z: float = -np.inf
    
    
    @property
    def norm(self):
        return np.linalg.norm([self.x, self.y, self.z])
    
    def dist(self, other):
        return np.sqrt((self.x-other.x)**2+(self.y-other.y)**2+(self.z-other.z)**2)
    
    def __add__(self, other):
        if isinstance(other, Point3D):
            return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)
        return Point3D(self.x + other, self.y + other, self.z + other)

    def __sub__(self, other):
        if isinstance(other, Point3D):
            return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)
        return Point3D(self.x - other, self.y - other, self.z - other)

    def __mul__(self, other):
        return Point3D(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        # print(self.x, self.y, self.z)
        # try:
        #     print(other.x, other.y, other.z)
        # except:
        #     print(other)
        return Point3D(self.x / other, self.y / other, self.z / other)

    def __eq__(self, other):
        if isinstance(other, Point3D):
            return self.x == other.x and self.y == other.y and self.z == other.z
        return False

    def __lt__(self, other):
        if isinstance(other, Point3D):
            return (self.x, self.y, self.z) < (other.x, other.y, other.z)
        return False

    def __le__(self, other):
        if isinstance(other, Point3D):
            return (self.x, self.y, self.z) <= (other.x, other.y, other.z)
        return False

    def __getitem__(self, index):
        return [self.x, self.y, self.z][index]
    
    def __repr__(self):
        return f"({round(self.x, 3)},{round(self.y, 3)},{round(self.z, 3)})"
@dataclass
class GeodeticPos:
    lat: float
    lon: float
    alt: float
    
    def __iter__(self):
        yield self.lat
        yield self.lon
        yield self.alt
@dataclass
class Radar:
    ENU_pos: Point3D
    GEO_pos: GeodeticPos
    height_above_terrain: float
    terrain_altitude_at_pos: float
@dataclass
class FL_INFO_FOR_COMPUTATION:
    FL: str
    FL_meters: float
    min_theta_viewable: float
    ENU_FL_at_origin: float
    # get_FL_height: Callable
    
@dataclass
class FL_RES:
    FL: str
    FL_meters: float
    LOS: np.ndarray
    area_km: float | None = None
    coverage: float | None = None
    
    # def __post_init__(self):
    #     # self.area_km, self.coverage = compute_FL_coverage(self.LOS)
        
    #     print(self.FL, self.area_km, self.c?overage)
        
    def __repr__(self):
        return f"FL_RES({self.FL})"
    
    def get_geodetic_LOS(self, radar_lat, radar_lon, radar_alt):
        # print(self.LOS.shape)
        E_points = self.LOS[:, 0]
        N_points = self.LOS[:, 1]
        U_points = np.zeros_like(E_points)
        
        # Convert back to lat/lon using your conversion function
        lat_points, lon_points, _ = geo.enu_to_geodetic_vectorized(
            radar_lat, radar_lon, radar_alt, E_points, N_points, U_points
        )
        # print(lat_points.shape, lon_points.shape)
        return np.column_stack([lon_points, lat_points, np.ones_like(lon_points)*self.FL_meters])

@dataclass
class Info:
    step_size: float
    radar: Radar
    # radar_height: float
    # radar_pos_terrain_alt: float
    # radar_pos_geodetic: GeodeticPos
    flight_levels: list[str]
    n_azi_angles: int
    min_delta_horiz_dist_BS_cutoff: int
    do_earth_curvature: bool
    
@dataclass
class DataPackage:
    info: Info
    FL_data: list[FL_RES]


class LOS:

    def __init__(self,
            ss_ray_casting: int,
            radar_lat: float,
            radar_lon: float,
            radar_pos_terrain_altitude: float,
            radar_height_above_terrain: float,
            flight_levels: list[str],
            n_azi_angles: int,
            min_delta_horiz_dist_BS_cutoff: int,
            do_earth_curvature: bool,
            lat, lon, ter, map):
        
        
        self.map = map
        #to set user vars if main() called from elsewhere (GUI for example)
        # if ss_ray_casting is not None:
        self.STEP_SIZE_RAY_CASTING = ss_ray_casting
        # if radar_lat is not None:
        self.radar_lat = radar_lat
        # if radar_lon is not None:
        self.radar_lon = radar_lon
        # if radar_pos_terrain_altitude is not None:
        self.radar_pos_terrain_altitude = radar_pos_terrain_altitude
        # if radar_height_above_terrain is not None:
        self.RADAR_HEIGHT_ABOVE_TERRAIN = radar_height_above_terrain
        # if flight_levels is not None:
        self.flight_levels = flight_levels
        # if n_azi_angles is not None:
        self.n_azimuth_angles = n_azi_angles
        # if min_delta_horiz_dist_BS_cutoff is not None:
        self.min_delta_horiz_dist_BS_cutoff = min_delta_horiz_dist_BS_cutoff
        # if do_earth_curvature is not None:
        self.do_earth_curvature = do_earth_curvature
        # if min_delta_theta is not None:
        #     UV.min_delta_theta = min_delta_theta
        
        self.setup(lat, lon, ter)
        
    def setup(self, lat, lon, ter):#, geodetic_data_file: str):
    
        self.lat, self.lon, self.ter = lat, lon, ter
        
        self.lat0 = self.radar_lat
        self.lon0 = self.radar_lon
        self.alt0 = self.radar_pos_terrain_altitude + self.RADAR_HEIGHT_ABOVE_TERRAIN
        # print(f"Terrain altitude at radar pos: {self.radar_pos_terrain_altitude}.")
        
        self.radar = Radar(Point3D(0, 0, 0),
                        GeodeticPos(self.lat0, self.lon0, self.alt0),
                        self.RADAR_HEIGHT_ABOVE_TERRAIN,
                        self.radar_pos_terrain_altitude)
        
        self.OPTICAL_HORIZON_RADAR_PART = np.sqrt(2*gc.EARTH_RADIUS_M*(self.alt0))
        
        print("Converting geodetic data to local ENU...")
        
        self.E, self.N, self.U = self.to_ENU(self.lat0, self.lon0, self.alt0, self.lat, self.lon, self.ter)
        # print(np.min(self.U), np.max(self.U))
        self.U += (self.E**2+self.N**2)/(2*gc.EARTH_RADIUS_M)
        
        # print('ba')
        self.min_E, self.max_E = self.E.min(), self.E.max()
        self.min_N, self.max_N = self.N.min(), self.N.max()
        # print(np.min(self.U), np.max(self.U))
        # assert False
        self.get_terrain_height = self.create_grid_interpolator(self.E, self.N, self.U, self.lon0, self.lat0, self.alt0)
        
        self.U_flat = self.U.ravel()
        

        # self.FL_list: list[FlightLevel] = []
        # fix shit vectorized ENU doesnt work??
        self.FL_list = []
        
        for FL in self.flight_levels:
            FL_meters = self.FL_to_meters(FL)
            flight_level_grid = np.ones_like(self.ter) * FL_meters
            FL_E, FL_N, FL_U = self.to_ENU(self.lat0, self.lon0, self.alt0, self.lat, self.lon, flight_level_grid)
            
            # get_FL_height = self.create_grid_interpolator(FL_E, FL_N, FL_U, self.lon0, self.lat0, self.alt0)
            
            curr_FL_ENU_FL_at_origin = FL_U[np.unravel_index(np.argmin(np.abs(FL_N)), self.N.shape)[0],np.unravel_index(np.argmin(np.abs(FL_E)), self.E.shape)[1]]
            #minimum value for theta such that if no obstacles, radar can see to flight level
            curr_FL_min_theta_viewable = np.pi/2 - np.arccos(curr_FL_ENU_FL_at_origin/gc.MAX_RADAR_DISTANCE_METERS)
            
            self.FL_list.append(FL_INFO_FOR_COMPUTATION(FL, FL_meters, curr_FL_min_theta_viewable, curr_FL_ENU_FL_at_origin))#, get_FL_height))




    def calc(self):
        
        start_time = time()
        print("Finding line of sight...")
        
        # self.setup()#, UV.geodetic_data_file)
        
        # print(self.radar)
        FL_LOS_list: list[FL_RES] = []
        
        for FL in self.FL_list:

            print()
            print()
            print(FL.FL)
            self.current_FL = FL #to use the correct min_theta_viewable, ENU_FL_at_origin and get_FL_height
                    
            LOS_curr_FL: list[Point3D] = self.get_LOS_single_FL(self.n_azimuth_angles)#, UV.min_delta_theta)

            LOS_arr = np.array([[p.x, p.y, p.z] for p in LOS_curr_FL])

            FL_RES_obj = FL_RES(FL.FL, FL.FL_meters, LOS_arr)
            FL_RES_obj.area_km, FL_RES_obj.coverage = self.compute_FL_coverage(FL_RES_obj)
            FL_RES_obj.area_km = min(FL_RES_obj.area_km, self.map.area_km2)
            FL_RES_obj.coverage = round(min(FL_RES_obj.coverage, 100), 2)
            # print()
            # print(FL_RES_obj.area_km, FL_RES_obj.coverage)
            FL_LOS_list.append(FL_RES_obj)
        
        # FL_LOS_arr = np.array(FL_LOS_list)

        data_package = self.get_data_package_obj(FL_LOS_list)
        # if save_to is not None:
        #     print(f"Saving DataPackage object to {save_to}")
        #     np.save(save_to, np.array([data_package]))
            
        print()
        print()
        print(f"Done! Took {self.format_duration(round(time()-start_time))} to run.")
        
        return data_package

    def get_LOS_single_FL(self, num_azimuth: int):#, delta_theta_stopping_point: float) -> list[Point3D]:
        
        points: list[Point3D] = []
        for i, azi in enumerate(np.linspace(0, 2*np.pi, num_azimuth, endpoint=False)):
            # print((num_azimuth/20) % (i+1))
            if i % (round(num_azimuth/20)) == 0:
                
                print(f"AZI%:{round(azi/(2*np.pi)*100, 1)}", end='\r')
            # points.append(clip_to_optical_horizon(clip_to_map(find_obstacle_binary_search2(azi, delta_theta_stopping_point))))
            points.append(self.clip_to_optical_horizon(self.clip_to_map(self.find_obstacle_binary_search_distance2(azi))))
            # points.append(clip_to_map(find_obstacle_binary_search(azi, delta_theta_stopping_point)))
            
            # assert False
        
        print(f"AZI%:100.0", end='\r')
        
        return points


    def find_obstacle_binary_search_distance2(self, azi) -> Point3D:
        
        # Calculate max horizontal distance before hitting map boundary
        max_horiz_dist = self.calculate_max_distance_in_azimuth(azi)
        
        # print(max_horiz_dist)
        
        l_dist = 0  # minimum distance (at radar)
        r_dist = max_horiz_dist  # maximum distance (map boundary)
        
        furthest_viewable_point = None #type: ignore
        furthest_viewable_point_dist_squared = None #type: ignore
        
        while (r_dist - l_dist) > self.min_delta_horiz_dist_BS_cutoff:
            m_dist = (l_dist + r_dist) / 2
            
            # Calculate end point at this horizontal distance
            end_point = self.radar.ENU_pos + Point3D(
                np.cos(azi) * m_dist, 
                np.sin(azi) * m_dist, 
                0
            )
            
            # Get flight level height at this point (handles curvature)
            # end_point_FL_ENU = self.current_FL.get_FL_height(end_point.x, end_point.y)
            end_point_FL_ENU = self.current_FL.FL_meters
            end_point.z = end_point_FL_ENU
            
            # Shoot ray from radar to this point
            
            if end_point_FL_ENU < 0:
                ss = self.STEP_SIZE_RAY_CASTING
            else:
                ss = self.STEP_SIZE_RAY_CASTING / np.cos(self.elevation_angle(self.radar.ENU_pos, end_point))

                # ss = np.sqrt(STEP_SIZE_RAY_CASTING**2+end_point_FL_ENU**2)
            # ss = STEP_SIZE_RAY_CASTING
            # print(self.min_E)
            
            end_point_lat, end_point_lon, _ = geo.enu_to_geodetic_vectorized(self.radar.GEO_pos.lat, self.radar.GEO_pos.lon, self.radar.GEO_pos.alt,
                                    end_point.x, end_point.y, end_point.z)
            
            end_point_alt = self.current_FL.FL_meters
            
            if self.los_radar_rx_fast(
                            end_point_lat, end_point_lon,
                            h_rx=0,
                            step_m=ss,
                            alt_rx=end_point_alt
                            ):
                
            # if is_LOS(self.radar.ENU_pos, end_point, step_size=ss):

                if furthest_viewable_point is None or end_point.x**2+end_point.y**2 > furthest_viewable_point_dist_squared:
                    furthest_viewable_point: Point3D = end_point
                    furthest_viewable_point_dist_squared: float = furthest_viewable_point.x**2+furthest_viewable_point.y**2
                l_dist = m_dist
            else:
                r_dist = m_dist
                
            # hit_point: Point3D = shoot_ray(self.radar.ENU_pos, end_point, step_size=ss)
            
            # # Check if ray reached the flight level without hitting terrain
            # if hit_point.z >= end_point_FL_ENU - 1:  # small tolerance
            #     # No obstacle - can see further, search further out
            #     last_viewable_point = hit_point
            #     l_dist = m_dist
            # else:
            #     # Hit obstacle - need to look closer, search closer in
            #     r_dist = m_dist
        
        # Return the furthest viewable point found
        if furthest_viewable_point is not None:
            return furthest_viewable_point
        else:
            # If we never found a viewable point, return the closest we got
            print("BABABABABABABABABA")
            assert False
            return self.radar.ENU_pos
        

    def los_radar_rx_fast(self,
                    rx_lat, rx_lon,
                    h_rx,
                    step_m,
                    alt_rx):
        """
        Terrain LOS test between TX and RX.
        Vectorized along the ray (no inner Python loop).
        Returns True if NOT blocked by terrain.
        """

        # Endpoint terrain + antenna heights
        # if alt_tx is None:
        #     alt_tx = terrain_height_nn(lats, lons, ter, tx_lat, tx_lon) + h_tx
        # if alt_rx is None:
        #     alt_rx = terrain_height_nn(lats, lons, ter, rx_lat, rx_lon) + h_rx

        dist = self.haversine_m(self.radar.GEO_pos.lat, self.radar.GEO_pos.lon, rx_lat, rx_lon)
        if dist < 1.0:
            return True

        n = int(dist // step_m)
        if n < 2:
            return True

        s = np.linspace(0.0, 1.0, n)

        lat_s = self.radar.GEO_pos.lat + s * (rx_lat - self.radar.GEO_pos.lat)
        lon_s = self.radar.GEO_pos.lon + s * (rx_lon - self.radar.GEO_pos.lon)
        z_line = self.radar.GEO_pos.alt + s * (alt_rx - self.radar.GEO_pos.alt)


        if self.do_earth_curvature:
            # print('ba')
            # Curvature correction
            x = s * dist
            curv_drop = (x * (dist - x)) / (2.0 * gc.EARTH_RADIUS_EFF)

            z_line -= curv_drop
        
        # **OPTIMIZED**: Pre-compute indices once instead of twice per sample
        i = np.searchsorted(self.lat, lat_s)
        j = np.searchsorted(self.lon, lon_s)
        
        # Clamp indices to valid range
        i = np.clip(i, 0, len(self.lat) - 1)
        j = np.clip(j, 0, len(self.lon) - 1)
        
        z_terr = self.ter[i, j]

        return not np.any(z_terr > z_line)
                
    def haversine_m(self, lat1, lon1, lat2, lon2):
        """Great-circle distance in meters (fast, good enough for this scale)."""
        # **OPTIMIZED**: Use faster approximation for small distances
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

    def calculate_max_distance_in_azimuth(self, azi):
        """
        Find maximum horizontal distance in given azimuth before leaving map bounds.
        Assumes map bounds are defined by [E_min, E_max] x [N_min, N_max]
        """
        
        # Starting position (radar location)
        x0 = self.radar.ENU_pos.x
        y0 = self.radar.ENU_pos.y
        
        # Direction vector (unit vector in azimuth direction)
        dx = np.cos(azi)
        dy = np.sin(azi)
        
        # E_min = self.min_E
        # E_max = self.max_E
        # N_min = self.min_N
        # N_max = self.max_N
        
        # Calculate distance to intersection with each boundary
        t_values = []
        
        # East boundary (x = E_max)
        if dx > 1e-10:  # moving east
            t_e_max = (self.max_E - x0) / dx
            t_values.append(t_e_max)
        
        # West boundary (x = E_min)
        if dx < -1e-10:  # moving west
            t_e_min = (self.min_E - x0) / dx
            t_values.append(t_e_min)
        
        # North boundary (y = N_max)
        if dy > 1e-10:  # moving north
            t_n_max = (self.max_N - y0) / dy
            t_values.append(t_n_max)
        
        # South boundary (y = N_min)
        if dy < -1e-10:  # moving south
            t_n_min = (self.min_N - y0) / dy
            t_values.append(t_n_min)
        
        # Return the minimum positive distance
        # (the first boundary we hit in this direction)
        valid_t = [t for t in t_values if t > 0]
        
        if not valid_t:
            # This shouldn't happen if radar is inside map bounds
            # But as a safeguard, return a reasonable large value
            assert False
            # return 100000  # or some max distance you care about
        
        return min(valid_t)

    def to_ENU(self, lat0, lon0, alt0, lat, lon, ter):
    
        E, N, U = geo.data_converter_to_ENU_vectorized(lat0, lon0, alt0, lat, lon, ter)

        return E, N, U

    def compute_FL_coverage(self, FL: FL_RES):
        
        FL_area = self.compute_polygon_area(FL.get_geodetic_LOS(self.lat0, self.lon0, self.alt0))
            
        # print(FL_area)
        
        coverage_pct = (FL_area / self.map.area_km2) * 100
            
        return FL_area, coverage_pct

    def compute_polygon_area(self, points_latlon):

        
        # Initialize geodesic calculator (WGS84 ellipsoid)
        geod = Geod(ellps='WGS84')
        
        # Extract lon, lat arrays
        lons = points_latlon[:, 0]
        lats = points_latlon[:, 1]
        
        # print(lons)
        # print(lats)
        
        # Calculate polygon area (returns area in m², perimeter in m)
        area, _perimeter = geod.polygon_area_perimeter(lons, lats)
        
        # Convert to km² and take absolute value
        area_km2 = abs(area) / 1e6
        
        return area_km2

    def clip_to_map(self, point: Point3D) -> Point3D:
        """
        Clip a point to map boundaries along the line from origin to point.
        If point is in bounds, return it unchanged.
        Otherwise, return the intersection with the map boundary.
        """
        if self.is_in_bound(point):
            return point
        
        # Calculate t values for intersection with each boundary
        t_values = []
        
        # East boundaries
        if point.x != 0:
            if point.x < self.min_E:
                t_values.append(self.min_E / point.x)
            elif point.x > self.max_E:
                t_values.append(self.max_E / point.x)
        
        # North boundaries
        if point.y != 0:
            if point.y < self.min_N:
                t_values.append(self.min_N / point.y)
            elif point.y > self.max_N:
                t_values.append(self.max_N / point.y)
        
        # Find smallest positive t that brings us to boundary
        valid_t = [t for t in t_values if 0 < t < 1]
        
        if not valid_t:
            # Point is at origin or no valid intersection
            return Point3D(0, 0, 0)
        
        t = min(valid_t)
        
        # Calculate clipped point
        clipped_x = point.x * t
        clipped_y = point.y * t
        
        clipped_z = self.get_terrain_height(clipped_x, clipped_y)
        
        return Point3D(clipped_x, clipped_y, clipped_z)


    def clip_to_optical_horizon(self, point: Point3D):#, max_distance: float) -> Point3D:
        """
        Clip a point to a maximum distance from origin along the line from origin to point.
        If point is within max_distance, return it unchanged.
        Otherwise, return the point at max_distance along the line.
        """
        
        # max_distance = OPTICAL_HORIZON
        
        optical_horiz = self.OPTICAL_HORIZON_RADAR_PART + np.sqrt(2*gc.EARTH_RADIUS_M*self.current_FL.FL_meters)
        
        max_distance = optical_horiz
        
        distance = np.sqrt(point.x**2 + point.y**2)# + point.z**2)
        # print(point.z)
        # print(distance)
        # print(max_distance)
        if distance <= max_distance:
            return point
        
        # Scale point to be at max_distance
        scale = max_distance / distance
        
        clipped_x = point.x * scale
        clipped_y = point.y * scale
        # print(point.x, point.y)
        # print(clipped_x, clipped_y)
        clipped_z = self.get_terrain_height(clipped_x, clipped_y)
        
        return Point3D(clipped_x, clipped_y, clipped_z)

    def is_in_bound(self, pos):
    
        return self.min_E <= pos.x <= self.max_E and self.min_N <= pos.y <= self.max_N

    def elevation_angle(self, p1:Point3D, p2:Point3D):
        
        dx, dy, dz = np.array([p2.x, p2.y, p2.z]) - np.array([p1.x, p1.y, p1.z])
        
        return abs(np.arctan2(dz, np.hypot(dx, dy)))

    def create_grid_interpolator(self, E, N, U, lon0, lat0, alt0):
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
            
            lat, lon, _ = geo.enu_to_geodetic_vectorized(lat0, lon0, alt0, x, y, 0)
            
            x, y, z = geo.convert_to_ENU_vectorized(lat0, lon0, alt0, lat, lon, 0)
            z += (x**2+y**2)/(2*gc.EARTH_RADIUS_M)
            
            return z
                
        return get_terrain_height

    def FL_to_meters(self, FL: str):
        return int(FL[2:]) * 100 / 3.281 

    def get_info_obj(self) -> Info:
        
        return Info(self.STEP_SIZE_RAY_CASTING,
                    self.radar,
                    # UV.RADAR_HEIGHT_ABOVE_TERRAIN,
                    # self.radar_pos_terrain_altitude,
                    # GeodeticPos(self.lat0, self.lon0, self.alt0),
                    self.flight_levels,
                    self.n_azimuth_angles,
                    self.min_delta_horiz_dist_BS_cutoff,
                    self.do_earth_curvature)
        
    def get_data_package_obj(self, FL_LIST: list[FL_RES]) -> DataPackage:
        
        return DataPackage(self.get_info_obj(), FL_LIST)

    def format_duration(self, seconds: float) -> str:
        seconds = float(seconds)

        if seconds > 60:
            return f"{round(seconds//60)}m {seconds%60}s"
        return f"{seconds}s"
