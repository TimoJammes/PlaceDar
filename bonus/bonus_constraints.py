import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from itertools import combinations
import zipfile

# Paths 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'constraints_related_code', 'filtering')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import geo_utils as gdf
from bonus.directivity_tools import load_gain_angle_csv, interp_gain_0_360, score_rx_pair, score_rx

# COMENTED CODE IS TO CREATE THE FILTERED DATA FILES 

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'constraints_related_code', 'filtering')))
# # import full_filtering as ff
# # sys.path.insert(0, os.path.abspath(os.path.join(<os.path.dirname(__file__), '../..')))
# # import geo_data_functions as gdf
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))#, 'LOS_calculator')))
# #import LOS_calculator.main as mn
# import constraints_related_code.filtering.full_filtering as ff
# import geo_data_functions as gdf
# import constraints_related_code.filtering.electrical_filtering as elec
# import constraints_related_code.filtering.road_filtering as road
# import constraints_related_code.filtering.building_filtering as building
# import constraints_related_code.filtering.country_filtering as country
# import constraints_related_code.filtering.nice_filtering as nice
# import constraints_related_code.filtering.ocean_filtering as ocean
# import constraints_related_code.filtering.airport_filtering as airport
# import constraints_related_code.Buildings as bld

# lats, lons, ter = gdf.get_geodetic_data()
# # lon_indices_filtered_idx, lat_indices_filtered_idx = ff.full_filter(lons, lats, ter,
# #                 max_distance_from_airport=10000,
# #                 max_distance_from_elec=500,
# #                 min_distance_from_building=50,
# #                 max_distance_from_road=500,
# #                 doElec=True,
# #                 doRoads=True,
# #                 doBuildings=True,
# #                 doMaxDistFromAirport=True,
# #                 doNoOcean=True,
# #                 doNoNice=False,
# #                 doOnlyFrance=True)

# # main(save_to= 'bonus/MontAlban', radar_lat=43.699167, radar_lon = 7.298889, radar_height_above_terrain=29, )

# # filtered_lon, filtered_lat = lons[lon_indices_filtered_idx], lats[lat_indices_filtered_idx]
# # np.savez("data/constraints_related/filtering/bonus_full_filtering",
# #              lons=filtered_lon, lats=filtered_lat)  

# file = np.load("data/constraints_related/filtering/bonus_full_filtering.npz")
# filtered_lon, filtered_lat = file['lons'], file['lats']
# print(len(filtered_lat))



if __name__ == "__main__":

    # 1) Load terrain
    lats, lons, ter = gdf.get_geodetic_data()

    # # load data
    # file_Alban = np.load("data/constraints_related/filtering/  NAMEEEEEE  .npz")
    # filtered_lon_Alban, filtered_lat_Alban = file_Alban['lons'], file_Alban['lats']
    
    # file_Vin = np.load("data/constraints_related/filtering/  NAMEEEEEE  .npz")
    # filtered_lon_Vin, filtered_lat_Vin = file_Vin['lons'], file_Vin['lats']
    
    # file_Pic = np.load("data/constraints_related/filtering/  NAMEEEEEE  .npz")
    # filtered_lon_Pic, filtered_lat_Pic = file_Pic['lons'], file_Pic['lats']
    

    # 3) Define the emitters (lat, lon, antenna height)
    emitters = [
        ("MontAlban",      43.699167, 7.298889, 29.0),
        ("MontVinaigrier", 43.714444, 7.307222, 6.0),
        ("PicDeLOurs",     43.476306, 6.905417, 62.0),
    ]

    directivity_files = {
        "MontAlban": "bonus/data/directivity/mont_alban.csv",
        "MontVinaigrier": "bonus/data/directivity/mont_vinaigrier.csv",
        "PicDeLOurs": "bonus/data/directivity/pic_de_lours.csv",
    }
    
    filtered_files = {
        "MontAlban": "bonus/data/valid_points/mont_alban_valid_points.npz",
        "MontVinaigrier": "bonus/data/valid_points/mont_vinaigrier_valid_points.npz",
        "PicDeLOurs": "bonus/data/valid_points/pic_ours_valid_points.npz"
    }

    # Load directivity patterns
    directivity_gain = {}
    for name in directivity_files:
        ang, gain = load_gain_angle_csv(directivity_files[name])
        directivity_gain[name] = interp_gain_0_360(ang, gain)
        print(f"[{name}] directivity loaded. gain@0°={directivity_gain[name][0]:.2f}")

    # # How many top candidates to consider for pair scoring
    TOP_N = 200

    results = {}  # Store top single-RX candidates per emitter
    best_pairs_per_emitter = {}  # Store best RX pair per emitter

    for name, tx_lat, tx_lon, h_tx in emitters:

   
        fil_file_path = filtered_files[name]
        fil_file = np.load(fil_file_path)
        filtered_lon, filtered_lat = fil_file['lons'], fil_file['lats']

        gains = directivity_gain[name]

        # 5) Compute single-RX scores
        scores_single = np.array([
            score_rx(tx_lat, tx_lon, la, lo, gains)
            for la, lo in zip(filtered_lat, filtered_lon)
        ])

        #  Keep only TOP_N candidates for pair evaluation
        idx_top = np.argsort(scores_single)[::-1][:TOP_N]
        lat_top = filtered_lat[idx_top]
        lon_top = filtered_lon[idx_top]
        scores_top = scores_single[idx_top]

        results[name] = (lat_top, lon_top, scores_top)
        results[name] = (lat_top, lon_top, scores_top)

        
        
        TOP_K_PAIRS = 10
        top_pairs = []  

        for i, j in combinations(range(len(lat_top)), 2):
            rx1_lat, rx1_lon = float(lat_top[i]), float(lon_top[i])
            rx2_lat, rx2_lon = float(lat_top[j]), float(lon_top[j])

            s = score_rx_pair(tx_lat, tx_lon,
                            rx1_lat, rx1_lon,
                            rx2_lat, rx2_lon,
                            gains)

            if s <= 0:   # skip invalid pairs if your score sets them to 0
                continue

            if len(top_pairs) < TOP_K_PAIRS:
                top_pairs.append((float(s), (rx1_lat, rx1_lon, rx2_lat, rx2_lon)))
                top_pairs.sort(key=lambda x: x[0], reverse=True)
            else:
                if s > top_pairs[-1][0]:
                    top_pairs[-1] = (float(s), (rx1_lat, rx1_lon, rx2_lat, rx2_lon))
                    top_pairs.sort(key=lambda x: x[0], reverse=True)

        best_pairs_per_emitter[name] = {
            "top_pairs": top_pairs  # sorted best -> worst
        }

        print(f"{name}: Top {TOP_K_PAIRS} pair scores =", [round(p[0], 2) for p in top_pairs])


   
# EXPORT BEST PAIRS TO KMZ



def kml_color_abgr(hex_rgb):
    rr = hex_rgb[0:2]
    gg = hex_rgb[2:4]
    bb = hex_rgb[4:6]
    return f"ff{bb}{gg}{rr}"

# rank colors best -> worst
RANK_COLORS = [
    "ff0000",  # 1 red
    "ff7f00",  # 2 orange
    "ffff00",  # 3 yellow
    "00ff00",  # 4 green
    "00ffff",  # 5 cyan
    "0000ff",  # 6 blue
    "8b00ff",  # 7 violet
    "ff1493",  # 8 pink
    "a52a2a",  # 9 brown
    "808080",  # 10 gray
]

def make_emitter_kmz(emitter_name, tx_lat, tx_lon, top_pairs, out_path, top_k=10):
    # Only export up to top_k (and only as many colors as we have)
    top_k = int(min(top_k, len(top_pairs), len(RANK_COLORS)))

    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
"""
    kml += f"<name>{emitter_name} Top {top_k} Pairs</name>\n"

    # ---- Styles (one per rank) ----
    for r in range(1, top_k + 1):
        rgb = RANK_COLORS[r - 1]
        col = kml_color_abgr(rgb)
        kml += f"""
<Style id="line{r}">
  <LineStyle><color>{col}</color><width>4</width></LineStyle>
</Style>
<Style id="rx{r}">
  <IconStyle>
    <scale>1.1</scale>
    <Icon><href>http://maps.google.com/mapfiles/kml/paddle/wht-circle.png</href></Icon>
  </IconStyle>
  <LabelStyle><scale>0.8</scale></LabelStyle>
</Style>
"""

    # ---- Emitter placemark ----
    kml += f"""
<Placemark>
  <name>{emitter_name} EMITTER</name>
  <Style>
    <IconStyle>
      <scale>1.3</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/purple-circle.png</href></Icon>
    </IconStyle>
  </Style>
  <Point><coordinates>{tx_lon},{tx_lat},0</coordinates></Point>
</Placemark>
"""

 

    # ---- Top pairs (ranked) ----
    for idx, (score, (rx1_lat, rx1_lon, rx2_lat, rx2_lon)) in enumerate(top_pairs[:top_k], start=1):
        kml += f"""
<Folder>
  <name>Rank {idx} (score {score:.2f})</name>

  <Placemark>
    <name>RX1 (rank {idx})</name>
    <styleUrl>#rx{idx}</styleUrl>
    <Point><coordinates>{rx1_lon},{rx1_lat},0</coordinates></Point>
  </Placemark>

  <Placemark>
    <name>RX2 (rank {idx})</name>
    <styleUrl>#rx{idx}</styleUrl>
    <Point><coordinates>{rx2_lon},{rx2_lat},0</coordinates></Point>
  </Placemark>

  <Placemark>
    <name>Baseline (rank {idx})</name>
    <styleUrl>#line{idx}</styleUrl>
    <LineString>
      <tessellate>1</tessellate>
      <coordinates>
        {rx1_lon},{rx1_lat},0
        {rx2_lon},{rx2_lat},0
      </coordinates>
    </LineString>
  </Placemark>
</Folder>
"""

    # ---- CLOSE KML ONCE ----
    kml += "</Document></kml>\n"

    # ---- WRITE KMZ ONCE ----
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)

    print("KMZ exported:", out_path)


# ---- Export KMZ files (one per emitter) ----
# Put this at TOP LEVEL (same indentation as your other main code, NOT inside the function)
TOP_K_PAIRS_EXPORT = 10 # change to 5 / 10 / etc.

for name, tx_lat, tx_lon, h_tx in emitters:
    top_pairs = best_pairs_per_emitter[name]["top_pairs"]
    out_kmz = "bonus/data/kmz_exports/"f"{name}_top{TOP_K_PAIRS_EXPORT}_pairs.kmz"
    make_emitter_kmz(name, tx_lat, tx_lon, top_pairs, out_kmz, top_k=TOP_K_PAIRS_EXPORT)
    










