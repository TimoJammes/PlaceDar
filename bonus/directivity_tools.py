import numpy as np

def load_gain_angle_csv(path):
    # col0=gain_db, col1=angle_deg
    data = np.loadtxt(path, delimiter=";", skiprows=1)
    gain = data[:, 0].astype(float)
    ang = (data[:, 1].astype(float) % 360.0)

    idx = np.argsort(ang)
    return ang[idx], gain[idx]

def interp_gain_0_360(angle_deg, gain_db):
    # wrap-around for interpolation
    ang2 = np.concatenate([angle_deg, angle_deg[:1] + 360.0])
    gain2 = np.concatenate([gain_db, gain_db[:1]])

    deg = np.arange(0, 361, 1, dtype=float)
    gdeg = np.interp(deg, ang2, gain2)
    gdeg[360] = gdeg[0]
    return gdeg



def haversine_km(lat1, lon1, lat2, lon2): #Great-circle distance in km between two points.
    
    R = 6371.0  # Earth radius in km
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def bearing_deg(lat1, lon1, lat2, lon2): #Azimuth from point 1 to point 2 in degrees [0,360)
    
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlon = np.radians(lon2 - lon1)
    x = np.sin(dlon) * np.cos(phi2)
    y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlon)
    brng = np.degrees(np.arctan2(x, y))
    return (brng + 360.0) % 360.0



def gain_at(gain_0_360, az_deg):
    d = int(np.round(az_deg)) % 360
    return float(gain_0_360[d])

def score_rx(tx_lat, tx_lon, rx_lat, rx_lon, gain_0_360):
    
    az = bearing_deg(tx_lat, tx_lon, rx_lat, rx_lon)
    g = gain_at(gain_0_360, az)
    d_km = max(haversine_km(tx_lat, tx_lon, rx_lat, rx_lon), 1e-6)
    return g - 20.0 * np.log10(d_km)



def score_rx_pair(tx_lat, tx_lon, rx1_lat, rx1_lon, rx2_lat, rx2_lon, gain_0_360, min_sep_km=1.0, min_dist_from_tx_km=1):

    # Individual receiver scores
    s1 = score_rx(tx_lat, tx_lon, rx1_lat, rx1_lon, gain_0_360)
    s2 = score_rx(tx_lat, tx_lon, rx2_lat, rx2_lon, gain_0_360)
    
    # geometry
    baseline_km = haversine_km(rx1_lat, rx1_lon, rx2_lat, rx2_lon)

    geom_penalty = (baseline_km >= min_sep_km)
    if geom_penalty == True:
        geom_penalty = 1
    else:
        geom_penalty = 0
    
    d1 = haversine_km(tx_lat, tx_lon, rx1_lat, rx1_lon)
    d2 = haversine_km(tx_lat, tx_lon, rx2_lat, rx2_lon)
    if d1 < min_dist_from_tx_km or d2 < min_dist_from_tx_km:
        geom_penalty = 0
    
#we decided to jusy multiply by 0 or 1 since we dont know ideal separation 

    # total score for pairr
    S_total = (s1 + s2 ) * geom_penalty
    return S_total