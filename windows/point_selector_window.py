import numpy as np
import sys
from pathlib import Path
from dataclasses import dataclass, field

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QMessageBox, QFileDialog, QComboBox, QListWidget,
    QLineEdit, QDialog, QCheckBox, QMenu, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

from shapely.geometry import Point as shapelyPoint, box
import geopandas as gpd

import pickle
from shapely.ops import transform
from pyproj import Transformer

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas #type: ignore
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap

import pyvista as pv
from pyvistaqt import QtInteractor


# Local imports
import constants as gc

import geo_utils as geo

import line_of_sight as LOS_file
# import plot_region_boundaries as plt_regions
from windows.flight_level_window import FlightLevelWindow

from windows.popup_windows.input_window import InputWindow
from windows.popup_windows.checkable_dropdown import CheckableDropdown
from windows.popup_windows.integer_input_dialog import IntegerInputDialog
from windows.popup_windows.info_window import InfoWindow

import point_filters.constraints_filter as filter
from point_filters.LOS_filter import LOS_filter

@dataclass
class Point:
    lon: float
    lat: float
    alt: float
    name: str
    
    

@dataclass
class Map:
    name: str    
    file_path: str
    airport: Point
    ocean_threshold: int
    alt_scale: float
    points: list[Point] = field(default_factory=list)
    area_km2: float = field(init=False)
    resolution: float = field(init=False)
    max_lon: float = field(init=False)
    min_lon: float = field(init=False)
    max_lat: float = field(init=False)
    min_lat: float = field(init=False)
    
    def __post_init__(self):
        file = np.load(self.file_path)
                    
        lon = file["lon"]
        lat = file["lat"]
        # ter = file["ter"]
        
        self.min_lon, self.max_lon = lon.min(), lon.max()
        self.min_lat, self.max_lat = lat.min(), lat.max()
        self.area_km2 = geo.get_area(lon, lat)
        
        self.resolution = abs(lat[1]-lat[0])*111000
        
        # print(abs(lon[1]-lon[0])*np.sin(np.deg2rad(np.mean(lat)))*111000)
        # print(self.name, self.resolution)
    
class PointSelectorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terrain Data Plotter - 2D & 3D")
        self.setGeometry(100, 100, 1400, 900)
        self.lat, self.lon, self.ter = geo.get_geodetic_data()
        self.points: list[Point] = []

        if getattr(sys, "frozen", False):
            script_dir = Path(sys.executable).resolve().parent
        else:
            script_dir = Path(__file__).resolve().parent
        
        self.FL_LOS_folder = script_dir / ".." / "exports" / "FL_LOS"
        self.points_folder = script_dir / ".." / "exports" / "points"
        
                
        self.file_path_roads = "data/constraints_related/data_roads/roads_latlon.npz"
        self.file_path_elec_points = "data/constraints_related/data_elec/elec_points_latlon.npz"
        self.file_path_buildings = "data/constraints_related/data_buildings/buildings_latlon.npz"        
        self.road_mask_file_path = "data/constraints_related/filtering/masks/road_mask.npy"
        self.elec_mask_file_path = "data/constraints_related/filtering/masks/elec_mask.npy"
        self.building_mask_file_path = "data/constraints_related/filtering/masks/building_mask.npy"
        self.file_path_filter = "data/constraints_related/filtering/points/full_filter_points.npz"
        self.file_path_filter_and_LOS = "data/constraints_related/filtering/points/full_filter_and_airport_LOS_points.npz"
        
        file_full_filtered_and_LOS = np.load(self.file_path_filter_and_LOS, allow_pickle=True)
        self.filtered_and_airport_LOS_lats = file_full_filtered_and_LOS["lats"]
        self.filtered_and_airport_LOS_lons = file_full_filtered_and_LOS["lons"]
        self.filtered_and_airport_LOS_alts = file_full_filtered_and_LOS["alts"]
        
        self.ocean_threshold = 20
        self.radar_height_above_terrain = 20
        self.num_azi = 360
        self.ss_ray_casting = 90
        self.min_delta_horiz_dist_BS_cutoff = 90
        self.do_earth_curvature = 1
        
        self.max_dist_to_road = 500
        self.max_dist_to_elec = 500
        self.min_dist_to_building = 1000
        self.max_dist_to_airport = 50000
        
        
        # self.alt_scale = 1/10000


        self.airport_lon, self.airport_lat, self.airport_alt = gc.AIRPORT_LON, gc.AIRPORT_LAT, gc.AIRPORT_ALT
        self.points.append(Point(gc.AIRPORT_LON, gc.AIRPORT_LAT, gc.AIRPORT_ALT, "Airport"))

        map_names = ["Nice",
                     "Bhutan",
                     "Montreal",
                     "Barcelona",
                     "Hong Kong"]
                    #  "Mexico City",
                    #  "Everest"]
        
        map_alt_scales = [1/10000,
                          1/25000,
                          6e-5,
                          6e-5,
                          6e-5,
                          1/25000]
                        #   1/25000]
        map_paths = ["data/terrain/terrain_nice.npz",
                     "data/terrain/terrain_all_bhutan_90m_resol.npz",
                     "data/terrain/terrain_montreal.npz",
                     "data/terrain/terrain_barcelona.npz",
                     "data/terrain/terrain_hongkong.npz"]
                    #  "data/terrain/terrain_mex_city.npz",
                    #  "data/terrain/terrain_everest.npz"]
        
        map_airport = [Point(gc.AIRPORT_LON, gc.AIRPORT_LAT, gc.AIRPORT_ALT, "Airport"),
               Point(89.42105756116356, 27.40521006070443, 2235+10, "Airport"),
               Point(-73.74991, 45.45772, 36+10, "Airport"),      # Montreal (YUL)
               Point(2.07846, 41.29694, 4+10, "Airport"),         # Barcelona (BCN)
               Point(113.91452, 22.32722, 9+10, "Airport")]       # Hong Kong (HKG)
            #    Point(-99.07208, 19.43611, 2237+10, "Airport")]    # Mexico City (AICM)
        map_points = [[Point(gc.AIRPORT_LON, gc.AIRPORT_LAT, gc.AIRPORT_ALT, "Airport")],
                      [Point(89.42105756116356, 27.40521006070443, 2235+10, "Airport")],
               [Point(-73.74991, 45.45772, 36+10, "Airport")],      # Montreal (YUL)
               [Point(2.07846, 41.29694, 4+10, "Airport")],         # Barcelona (BCN)
               [Point(113.91452, 22.32722, 9+10, "Airport")]]      # Hong Kong (HKG)
            #    [Point(-99.07208, 19.43611, 2237+10, "Airport")]]    # Mexico City (AICM)
        map_ocean_threshold = [20,
                               0,
                               80,
                               2,
                               70,
                               0]
        
        self.maps: list[Map] = []
        for n, path, airport, thr, sc, p in zip(map_names, map_paths, map_airport, map_ocean_threshold, map_alt_scales, map_points):
            self.maps.append(Map(n, path, airport, thr, sc, p))
        
        self.curr_map = self.maps[0]
        
        self.cmap_name = 'terrain'
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side: tabs for 2D and 3D
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        main_layout.addWidget(left_widget, stretch=3)
        
        dropdown_layout = QHBoxLayout()
        dropdown_label = QLabel("Map Selection")
        dropdown_layout.addWidget(dropdown_label)
        
        
            
        self.view_selector_dropdown = QComboBox()
        self.view_selector_dropdown.addItems(map_names)
        self.view_selector_dropdown.currentTextChanged.connect(self.on_map_changed)
        dropdown_layout.addWidget(self.view_selector_dropdown)
        dropdown_layout.addStretch()  # Push dropdown to the left

        left_layout.addLayout(dropdown_layout)
        # Create main tab widget
        
        self.main_tab_widget = QTabWidget()
        left_layout.addWidget(self.main_tab_widget)
        
        # Create 2D and 3D tabs
        self.create_2d_tab()
        self.create_3d_tab()
        
        # Right side: points list (shared between both tabs)
        self.create_points_panel(main_layout)
        
        # Plot initial data
        self.plot_2d()
        self.plot_3d_pyvista()
        
        # Update points list if initial points provided
        if self.points:
            self.update_points_list()
    
    def set_all_checkboxes_unchecked(self):
        
        self.show_elec_points_checkbox.setChecked(False)
        self.show_roads_checkbox.setChecked(False)
        self.show_buildings_checkbox.setChecked(False)
        self.show_valid_points_checkbox.setChecked(False)
        self.show_valid_and_airport_LOS_points_checkbox.setChecked(False)
        self.show_max_dist_to_airport_boundary_checkbox.setChecked(False)
        self.show_sea_boundaries_checkbox.setChecked(False)
        self.show_nice_boundaries_checkbox.setChecked(False)
        self.show_country_boundaries_checkbox.setChecked(False)
        self.show_road_boundaries_checkbox.setChecked(False)
        self.show_elec_boundaries_checkbox.setChecked(False)
        self.show_road_boundaries_checkbox.setChecked(False)
        self.show_building_boundaries_checkbox.setChecked(False)

    def on_map_changed(self, map_name):
        
        self.set_all_checkboxes_unchecked()
        for map in self.maps:
            if map_name == map.name:
                
                self.curr_map = map
                break
            
        self.points = []
        file = np.load(self.curr_map.file_path)
            
        self.lon = file["lon"]
        self.lat = file["lat"]
        self.ter = file["ter"]
        
        self.ocean_threshold = self.curr_map.ocean_threshold
        # self.alt_scale = map.alt_scale
        self.alt_scale_input.setText(str(self.curr_map.alt_scale))
        self.airport_lon, self.airport_lat, self.airport_alt = self.curr_map.airport.lon, self.curr_map.airport.lat, self.curr_map.airport.alt
        
        self.curr_map = self.curr_map
        
        if self.curr_map.points:
            for p in self.curr_map.points:
                self.points.append(p)
        
        
        self.update_points_list()
                        
        self.replot_both()



    def on_canvas_resize(self, event):
        """Handle canvas resize to maintain proper layout"""
        if hasattr(self, 'figure_2d'):
            self.figure_2d.tight_layout(pad=1.0)
            self.canvas_2d.draw_idle()

    def on_threshold_changed_3D(self):
        self.ocean_threshold = float(self.ocean_threshold_input_3D.text())
        # self.ocean_threshold_input_2D.setText(str(self.ocean_threshold))
        self.plot_2d()
        self.plot_3d_pyvista()
    
    def on_alt_scale_changed(self):
        self.curr_map.alt_scale = float(self.alt_scale_input.text())
        self.plot_3d_pyvista()

    def on_threshold_changed_2D(self):
        # self.ocean_threshold = float(self.ocean_threshold_input_2D.text())
        self.ocean_threshold_input_3D.setText(str(self.ocean_threshold))
        self.plot_2d()
        self.plot_3d_pyvista()
        
    def on_click_2d(self, event):
        """Handle mouse click on the 2D plot"""
        
        if not self.add_points_mode_checkbox.isChecked():
            return
        
        if event.inaxes and event.button == 1:
            lon, lat = event.xdata, event.ydata
            self.add_point(lon, lat)
    


    
    def create_2d_tab(self):
        """Create the 2D terrain visualization tab"""
        tab_2d = QWidget()
        self.main_tab_widget.addTab(tab_2d, "2D Terrain")
        
        tab_layout = QVBoxLayout(tab_2d)
        
        # Control section
        control_layout = QHBoxLayout()
        
        self.plot_button_2d = QPushButton("Refresh Plot")
        self.plot_button_2d.clicked.connect(self.plot_2d)
        control_layout.addWidget(self.plot_button_2d)
        
        self.dropdown_constraints_layers_2d = CheckableDropdown("Constraints Layers")

        self.show_road_boundaries_checkbox = self.dropdown_constraints_layers_2d.add_item("Road Boundaries")
        self.show_building_boundaries_checkbox = self.dropdown_constraints_layers_2d.add_item("Building Boundaries")
        self.show_elec_boundaries_checkbox = self.dropdown_constraints_layers_2d.add_item("Electric Points Boundaries")
        self.show_country_boundaries_checkbox = self.dropdown_constraints_layers_2d.add_item("Country Boundaries")
        self.show_sea_boundaries_checkbox = self.dropdown_constraints_layers_2d.add_item("Sea Boundary")
        self.show_max_dist_to_airport_boundary_checkbox = self.dropdown_constraints_layers_2d.add_item("Max Distance to Airport Boundary")
        self.show_nice_boundaries_checkbox = self.dropdown_constraints_layers_2d.add_item("Nice Boundary")
        
        self.dropdown_constraints_layers_2d.item_checked_changed.connect(self.plot_2d)

        control_layout.addWidget(self.dropdown_constraints_layers_2d)
        
        self.dropdown_elements_layers_2d = CheckableDropdown("Elements Layers")
        self.show_valid_points_checkbox = self.dropdown_elements_layers_2d.add_item("Constraints Valid Points")
        self.show_valid_and_airport_LOS_points_checkbox = self.dropdown_elements_layers_2d.add_item("Constraints & Airport LOS Valid Points")
        self.show_elec_points_checkbox = self.dropdown_elements_layers_2d.add_item("Electrical Points")
        self.show_roads_checkbox = self.dropdown_elements_layers_2d.add_item("Roads")
        self.show_buildings_checkbox = self.dropdown_elements_layers_2d.add_item("Buildings")
        
        self.dropdown_elements_layers_2d.item_checked_changed.connect(self.plot_2d)
        
        control_layout.addWidget(self.dropdown_elements_layers_2d)
        
        self.plot_button_2d = QPushButton("Edit Constraints")
        self.plot_button_2d.clicked.connect(self.edit_constraints)
        control_layout.addWidget(self.plot_button_2d)
        
        self.add_points_mode_checkbox = QCheckBox("Add Points on Map")
        control_layout.addWidget(self.add_points_mode_checkbox)
        
        control_layout.addStretch()
        
        tab_layout.addLayout(control_layout)

        # Create matplotlib figure for 2D - only set DPI
        self.figure_2d = Figure(dpi=100)
        self.canvas_2d = FigureCanvas(self.figure_2d)
        # REMOVED: self.canvas_2d.setMinimumSize(800, 600)
        self.canvas_2d.setFocusPolicy(Qt.StrongFocus)#type: ignore
        self.canvas_2d.setFocus()
        
        # Add navigation toolbar for 2D
        self.toolbar_2d = NavigationToolbar(self.canvas_2d, self)
        tab_layout.addWidget(self.toolbar_2d)
        tab_layout.addWidget(self.canvas_2d)
        
        # Connect click event
        self.canvas_2d.mpl_connect('button_press_event', self.on_click_2d)
        
        # Connect resize event to adjust plot when window resizes
        self.canvas_2d.mpl_connect('resize_event', self.on_canvas_resize)

    def create_3d_tab(self):
        """Create the 3D terrain visualization tab using PyVista"""
        tab_3d = QWidget()
        self.main_tab_widget.addTab(tab_3d, "3D Terrain")
        
        tab_layout = QVBoxLayout(tab_3d)
        
        # Control section
        control_layout = QHBoxLayout()

        self.plot_button_3d = QPushButton("Refresh Plot")
        self.plot_button_3d.clicked.connect(self.plot_3d_pyvista)
        control_layout.addWidget(self.plot_button_3d)
        
        # Threshold input
        threshold_label = QLabel("Ocean Threshold (m):")
        control_layout.addWidget(threshold_label)
        
        self.ocean_threshold_input_3D = QLineEdit(str(self.ocean_threshold))
        self.ocean_threshold_input_3D.setMaximumWidth(100)
        
        validator = QDoubleValidator(np.min(self.ter), np.max(self.ter), 1)
        validator.setNotation(QDoubleValidator.StandardNotation)#type: ignore
        self.ocean_threshold_input_3D.setValidator(validator)
        
        self.ocean_threshold_input_3D.editingFinished.connect(self.on_threshold_changed_3D)
        control_layout.addWidget(self.ocean_threshold_input_3D)
        
        # Altitude scale input
        alt_scale_label = QLabel("Altitude scale:")
        control_layout.addWidget(alt_scale_label)
        
        self.alt_scale_input = QLineEdit(str(self.curr_map.alt_scale))
        
        self.alt_scale_input.setMaximumWidth(100)
        
        # validator_alt = QDoubleValidator(1000, 50000, 0)
        # validator_alt.setNotation(QDoubleValidator.StandardNotation)#type: ignore
        # self.alt_scale_input.setValidator(validator_alt)
                
        self.alt_scale_input.editingFinished.connect(self.on_alt_scale_changed)
        control_layout.addWidget(self.alt_scale_input)
        
        self.reset_camera_button = QPushButton("Reset Camera")
        self.reset_camera_button.clicked.connect(self.reset_camera_view)
        control_layout.addWidget(self.reset_camera_button)

        control_layout.addStretch()
        tab_layout.addLayout(control_layout)
        
        # Create PyVista QtInteractor
        self.plotter = QtInteractor(self)#type: ignore
        tab_layout.addWidget(self.plotter.interactor)

    def create_points_panel(self, main_layout):
        """Create the points management panel on the right side"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        main_layout.addWidget(right_widget, stretch=1)
        # Points section header
        show_point_labels_layout = QVBoxLayout()
        self.show_point_labels_checkbox = QCheckBox("Show Point Labels")
        self.show_point_labels_checkbox.setChecked(True)
        self.show_point_labels_checkbox.toggled.connect(self.replot_both)
        show_point_labels_layout.addWidget(self.show_point_labels_checkbox)
        
        right_layout.addLayout(show_point_labels_layout)
        
        points_label = QLabel("Saved Points (Lon, Lat, Alt)")
        points_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(points_label)
        
        # List widget to display points
        self.points_list = QListWidget()
        self.points_list.setContextMenuPolicy(Qt.CustomContextMenu)#type: ignore
        self.points_list.customContextMenuRequested.connect(self.show_options_menu_point)
        right_layout.addWidget(self.points_list)
        
        # Point management buttons
        point_buttons_layout = QVBoxLayout()
        
        
        self.get_LOS_airport_and_filter_points_button = QPushButton(f"Load Potential Radar Position Points ({len(self.filtered_and_airport_LOS_lons)} points)")
        self.get_LOS_airport_and_filter_points_button.clicked.connect(self.get_LOS_airport_and_filter_points)
        point_buttons_layout.addWidget(self.get_LOS_airport_and_filter_points_button)
        
        self.add_points_coordinates_button = QPushButton("Add Point using Coordinates")
        self.add_points_coordinates_button.clicked.connect(self.add_points_coordinates)
        point_buttons_layout.addWidget(self.add_points_coordinates_button)
        
        self.clear_points_button = QPushButton("Clear All Points")
        self.clear_points_button.clicked.connect(self.clear_all_points)
        point_buttons_layout.addWidget(self.clear_points_button)
        
        self.save_points_button = QPushButton("Save Points to File")
        self.save_points_button.clicked.connect(self.save_points)
        point_buttons_layout.addWidget(self.save_points_button)
        
        
        self.load_points_button = QPushButton("Load Points from File")
        self.load_points_button.clicked.connect(self.load_points)
        point_buttons_layout.addWidget(self.load_points_button)
        
        self.load_FL_LOS_button = QPushButton("Load Flight Level LOS from File")
        self.load_FL_LOS_button.clicked.connect(self.load_FL_LOS)
        point_buttons_layout.addWidget(self.load_FL_LOS_button)
        
        point_buttons_layout.addStretch()
        right_layout.addLayout(point_buttons_layout)
    




    def edit_constraints(self):
        fields = [("Max. Distance to Nearest Road:", 0, 100000, self.max_dist_to_road),
                  ("Max. Distance to Nearest Electric Post:", 0, 100000, self.max_dist_to_elec),
                  ("Min. Distance to Nearest Dwelling:", 0, 100000, self.min_dist_to_building),
                  ("Max. Distance from Nice Airport:", 0, 100000, self.max_dist_to_airport)]
        
        dialog = IntegerInputDialog(fields, "Edit Constraints", ok_button_text="Recalculate")
        
        vals = dialog.get_values()
        if vals is None:
            return
        
        if self.max_dist_to_road==vals[0] and self.max_dist_to_elec==vals[1] and self.min_dist_to_building==vals[2] and self.max_dist_to_airport==vals[3]:
            InfoWindow("Constraints Unchanged by User!").exec()
            return
            
        self.max_dist_to_road, self.max_dist_to_elec, self.min_dist_to_building, self.max_dist_to_airport = vals
        
        self.recompute_constraints()
    
    def show_options_menu_point(self, position):
        # Get the item at the clicked position
        item = self.points_list.itemAt(position)
        
        if not item:
            return
        
        menu = QMenu()
        
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        calc_action = menu.addAction("Calculate LoS")
        save_action = menu.addAction("Save Point")
        
        # FIXED: Use viewport().mapToGlobal() instead of mapToGlobal()
        action = menu.exec(self.points_list.viewport().mapToGlobal(position))
        
        if action == rename_action:
            self.rename_selected_point(item)
        elif action == delete_action:  
            self.delete_selected_point(item)
        elif action == calc_action:
            self.calc_FL_LOS_selected_point(item)
        elif action == save_action:  
            self.save_point(item)
    
    # ===== 2D Plotting Methods =====
    
    def replot_both(self):
        self.plot_2d()
        self.plot_3d_pyvista()

    def plot_2d(self):
        """Plot the 2D terrain data"""
        try:
            # data = self.ter
            
            # if data.ndim != 2:
            #     QMessageBox.warning(self, "Invalid Data", 
            #                     "Data must be a 2D array (n_lat x n_lon).")
            #     return
            
            # Clear previous plot
            self.figure_2d.clear()
            ax = self.figure_2d.add_subplot(111)
            
            # Plot terrain data with terrain colormap
            extent = [self.lon.min(), self.lon.max(), self.lat.min(), self.lat.max()]
            
            # Get selected colormap
            terrain_cmap = plt.get_cmap(self.cmap_name)
            
            # Use TwoSlopeNorm for better terrain visualization
            vmin = np.nanmin(self.ter)
            vmax = np.nanmax(self.ter)
            norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=max(vmin+1, self.ocean_threshold), vmax=vmax)
            
            im = ax.imshow(self.ter, cmap=terrain_cmap, norm=norm, aspect='auto', 
                        origin='lower', extent=extent)#type: ignore

            if self.show_elec_points_checkbox.checkState() == Qt.Checked:#type: ignore
                file_elec = np.load(self.file_path_elec_points)
                lats_elec=file_elec["lat"]
                lons_elec=file_elec["lon"]
                ax.scatter(lons_elec, lats_elec, s=0.5, color='red', alpha=1, label='Electrical Access Point', zorder=10)
            
            if self.show_roads_checkbox.checkState() == Qt.Checked:#type: ignore
                # plot_road
                file_roads = np.load(self.file_path_roads)
                lats_roads=file_roads["lat"]
                lons_roads=file_roads["lon"]

                ax.scatter(lons_roads, lats_roads, color='black', s=0.3, label='Road')
            
            if self.show_buildings_checkbox.checkState() == Qt.Checked:#type: ignore
                file_buildings = np.load(self.file_path_buildings)
                lats_buildings=file_buildings["lat"]
                lons_buildings=file_buildings["lon"]
                # plot buildings
                ax.scatter(lons_buildings, lats_buildings, color='magenta', s=0.5, label='Building')
            
            if self.show_valid_points_checkbox.checkState() == Qt.Checked:#type: ignore
                file_full_filtered = np.load(self.file_path_filter)#, allow_pickle=True)
                full_filtered_lats = self.lat[file_full_filtered["lats_idx"]]
                full_filtered_lons = self.lon[file_full_filtered["lons_idx"]]

                ax.scatter(full_filtered_lons, full_filtered_lats, color="magenta", s=1, label='Constraint-Valid Point', zorder=18)            
            
            if self.show_valid_and_airport_LOS_points_checkbox.checkState() == Qt.Checked:#type: ignore
                
                # file_full_filtered_and_LOS = np.load(self.file_path_filter_and_LOS, allow_pickle=True)

                # filtered_and_airport_LOS_lats = file_full_filtered_and_LOS["lats"]
                # filtered_and_airport_LOS_lons = file_full_filtered_and_LOS["lons"]
                # filtered_and_airport_LOS_alts = file_full_filtered_and_LOS["alts"]

                ax.scatter(self.filtered_and_airport_LOS_lons, self.filtered_and_airport_LOS_lats, color="darkblue", s=20, edgecolors="white", label='Candidate Radar Point', zorder=19)            
            
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            aspect = ax.get_aspect()
            if self.show_max_dist_to_airport_boundary_checkbox.checkState() == Qt.Checked:#type: ignore
                # transformers
                to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32632", always_xy=True).transform
                to_wgs = Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True).transform

                # --- Airport circle in meters ---
                airport_point_utm = transform(
                    to_utm,
                    shapelyPoint(gc.AIRPORT_LON, gc.AIRPORT_LAT)
                )
                airport_circle_utm = airport_point_utm.buffer(self.max_dist_to_airport)

                # --- Map bounding box (in WGS84 → UTM) ---
                map_bbox_wgs = box(xlim[0], ylim[0], xlim[1], ylim[1])
                map_bbox_utm = transform(to_utm, map_bbox_wgs)

                # --- Outside region ---
                outside_utm = map_bbox_utm.difference(airport_circle_utm)
                outside_wgs = transform(to_wgs, outside_utm)

                # --- Plot ---
                gpd.GeoSeries([outside_wgs], crs="EPSG:4326").plot(
                    ax=ax,
                    facecolor="red",
                    edgecolor="red",
                    hatch="///",
                    alpha=0.3,
                    linewidth=0,
                    zorder=8
                )
                
            if self.show_sea_boundaries_checkbox.checkState() == Qt.Checked:#type: ignore
                
                ax.contourf(
                    self.lon,
                    self.lat,
                    self.ter==0,
                    levels=[0.5, 1],
                    colors="red",        # no solid fill
                    hatches=["///"],      # hatch pattern
                    alpha=0.5,
                    linewidth=4,
                    zorder=20
                )
                

                # plt_regions.plot_sea_boundaries(ax)
            if self.show_nice_boundaries_checkbox.checkState() == Qt.Checked:#type: ignore
                with open('data/constraints_related/data_regions/nice_polygon.pkl', 'rb') as f:
                    nice_polygon = pickle.load(f)
                # Nice 
                nice_polygon.plot(
                    ax=ax,
                    facecolor="red",    
                    edgecolor="red",
                    hatch="///",
                    alpha=0.3,
                    linewidth=4
                )
                
            if self.show_country_boundaries_checkbox.checkState() == Qt.Checked:#type: ignore
                with open('data/constraints_related/data_regions/italy_polygon.pkl', 'rb') as f:
                    italy_polygon = pickle.load(f)
                # Italy
                italy_polygon.plot(
                    ax = ax,
                    facecolor = "red",
                    edgecolor="red",
                    hatch= "///",
                    linewidth=2,
                    alpha=0.3,
                    zorder= 12
                )
                
                with open('data/constraints_related/data_regions/monaco_polygon.pkl', 'rb') as f:
                    monaco_polygon = pickle.load(f)
                # Monaco
                
                monaco_polygon.plot(
                    ax = ax,
                    facecolor = "red",
                    edgecolor="red",
                    hatch= "///",
                    linewidth=2,
                    alpha=0.3,
                    zorder= 12
                )
                
                
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            ax.set_aspect(aspect)
            
            # masks_file = np.load(self.masks_file_path)
            lon_grid, lat_grid = np.meshgrid(self.lon, self.lat)
            if self.show_road_boundaries_checkbox.checkState() == Qt.Checked:#type: ignore
                
                invalid_road_mask = np.load(self.road_mask_file_path)
                
                ax.contourf(lon_grid, lat_grid, invalid_road_mask, levels=[0.5, 1.5],
                            colors='red',
                            hatches=["///"],
                            alpha=0.5)
            
            if self.show_elec_boundaries_checkbox.checkState() == Qt.Checked:   #type: ignore            
                invalid_elec_mask = np.load(self.elec_mask_file_path)
                ax.contourf(lon_grid, lat_grid, invalid_elec_mask, levels=[0.5, 1.5],
                            colors='red',
                            hatches=["///"],
                            alpha=0.5)
            
            if self.show_building_boundaries_checkbox.checkState() == Qt.Checked:    #type: ignore            
                invalid_building_mask = np.load(self.building_mask_file_path)
                ax.contourf(lon_grid, lat_grid, invalid_building_mask, levels=[0.5, 1.5],
                            colors='red',
                            hatches=["///"],
                            alpha=0.5)
                
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_title(f'Terrain')
            
            
            # Add colorbar
            self.figure_2d.colorbar(im, ax=ax, label='Elevation (m)')
            
            # Plot saved points
            if self.points:
                lons, lats = [p.lon for p in self.points], [p.lat for p in self.points]
                ax.plot(lons, lats, 'ro', markersize=6, markeredgecolor='white', 
                    markeredgewidth=1.5, label='Saved Points', zorder=21)
                
                # Add point labels
                if self.show_point_labels_checkbox.isChecked():
                    for i, p in enumerate(self.points):
                        ax.annotate(p.name, (p.lon, p.lat), 
                                xytext=(5, 5), textcoords='offset points',
                                color='white', fontweight='bold',
                                bbox=dict(boxstyle='round,pad=0.3', 
                                        facecolor='red', alpha=0.7), zorder=20)
            
            ax.legend(loc='lower right')
            
            # Set aspect ratio based on latitude
            ax.set_aspect(1 / np.cos(np.deg2rad(gc.AIRPORT_LAT)))
            
            # REPLACED: Use tight_layout instead of manual subplots_adjust
            self.figure_2d.tight_layout(pad=1.0)
            
            self.canvas_2d.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot 2D data:\n{str(e)}")
        
    # ===== 3D Plotting Methods =====
    
    def plot_3d_pyvista(self):
        """Plot the terrain in 3D using PyVista"""
        if self.ter is None:
            QMessageBox.warning(self, "No Data", "Please load terrain data first.")
            return
        
        try:
            # Clear the plotter
            self.plotter.clear()
            
            # Create coordinate grids
            lon_grid, lat_grid = np.meshgrid(self.lon, self.lat)
            
            # Scale altitude for display
            ter_scaled = self.ter * self.curr_map.alt_scale
            
            # Create structured grid for terrain
            grid = pv.StructuredGrid(lon_grid, lat_grid, ter_scaled)
            
            # Add original terrain data for coloring
            grid.point_data['Elevation'] = self.ter.ravel(order='F')
            
            # Create custom terrain colormap
            terrain_cmap = plt.get_cmap('terrain')
            vmin = np.nanmin(self.ter)
            vmax = np.nanmax(self.ter)
            
            # Create custom colormap with threshold
            n_colors = 256
            colors = np.zeros((n_colors, 4))
            
            for i in range(n_colors):
                ter_value = vmin + (vmax - vmin) * (i / (n_colors - 1))
                
                if ter_value <= self.ocean_threshold:
                    # Below threshold: use blue portion
                    if self.ocean_threshold > vmin:
                        ocean_norm = (ter_value - vmin) / (self.ocean_threshold - vmin)
                        cmap_pos = 0.35 * ocean_norm
                    else:
                        cmap_pos = 0.35
                else:
                    # Above threshold: use terrain portion
                    if vmax > self.ocean_threshold:
                        land_norm = (ter_value - self.ocean_threshold) / (vmax - self.ocean_threshold)
                        cmap_pos = 0.4 + 0.6 * land_norm
                    else:
                        cmap_pos = 1.0
                
                colors[i] = terrain_cmap(cmap_pos)
            
            custom_cmap = LinearSegmentedColormap.from_list('custom_terrain', colors)
            
            # Add terrain mesh
            self.plotter.add_mesh(
                grid,
                scalars='Elevation',
                cmap=custom_cmap,
                show_edges=False,
                scalar_bar_args={
                    'title': 'Elevation (m)',
                    'vertical': True,
                    'position_x':0.89,
                    'fmt': '%.0f'
                },
                clim=[vmin, vmax],
                lighting=True
            )
            
            
            # Plot saved points if available
            if self.points:
                for point in self.points:
                    lon, lat = point.lon, point.lat
                    
                    # Find closest indices in the grid
                    # lon_idx = np.argmin(np.abs(self.lon - lon))
                    # lat_idx = np.argmin(np.abs(self.lat - lat))
                    
                    # Get the terrain height at this point
                    z_value = (point.alt+self.radar_height_above_terrain) * self.curr_map.alt_scale #type: ignore
                    
                    # Add point sphere
                    point_sphere = pv.Sphere(
                        radius=0.001,
                        center=(lon, lat, z_value)
                    )
                    
                    self.plotter.add_mesh(point_sphere, color='red')
                    
                    # Add point label
                    self.plotter.add_point_labels(
                        [[lon, lat, z_value]],
                        [point.name],
                        font_size=12,
                        text_color='red',
                        bold=True,
                        always_visible=True,
                        shape_opacity=0.0
                    )
                    
                    #add LOS to airport
                    pointa = [lon, lat, z_value]
                    pointb = [self.airport_lon, self.airport_lat, self.airport_alt * self.curr_map.alt_scale]
                    line = pv.Line(pointa=pointa, pointb=pointb)
                    self.plotter.add_mesh(line, color='red', line_width=0.01)
            
            # Set up axes
            self.plotter.add_axes(xlabel='Longitude (°)', ylabel='Latitude (°)', zlabel='Elevation (m)')
            self.plotter.show_bounds(
                bounds=(self.lon.min(), self.lon.max(), self.lat.min(), self.lat.max(), ter_scaled.min(), ter_scaled.max()),
                xtitle="Longitude (°)",
                ytitle="Latitude (°)",
                # use_2d=True,
                # ztitle=" ",
                grid=False,
                location='outer',
                ticks='outside',
                # n_zlabels=0
                # font_size=5
                # all_edges=False
            )
            
            if hasattr(self.plotter.renderer, 'cube_axes_actor'):
                self.plotter.renderer.cube_axes_actor.SetZAxisVisibility(False)
                self.plotter.renderer.cube_axes_actor.SetZAxisLabelVisibility(False)
                self.plotter.renderer.cube_axes_actor.SetZAxisTickVisibility(False)
            
            # Reset camera to centered view
            self.reset_camera_view()
            
            # Enable interactive features
            self.plotter.enable_anti_aliasing()
            
        except Exception as e:
            print(f"Error plotting 3D: {e}")
            import traceback

            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to plot 3D data:\n{str(e)}")
        
    def reset_camera_view(self):
        """Reset camera to centered view"""
        if not hasattr(self, 'plotter'):
            return
        
        try:
            # Calculate center of terrain
            center_lon = (self.lon.min() + self.lon.max()) / 2
            center_lat = (self.lat.min() + self.lat.max()) / 2
            
            # Get elevation at center
            lon_idx = np.argmin(np.abs(self.lon - center_lon))
            lat_idx = np.argmin(np.abs(self.lat - center_lat))
            center_z = self.ter[lat_idx, lon_idx] * self.curr_map.alt_scale
            
            # Set focal point to center
            self.plotter.camera.focal_point = (center_lon, center_lat, center_z)
            
            # Calculate camera distance
            lat_range = np.ptp(self.lat)
            lon_range = np.ptp(self.lon)
            max_range = max(lat_range, lon_range)
            
            camera_distance = max_range * 2
            
            # Position camera at isometric angle
            self.plotter.camera.position = (
                center_lon + camera_distance * 0.7,
                center_lat + camera_distance * 0.7,
                center_z + camera_distance * 0.5
            )
            
            # Set up direction
            self.plotter.camera.up = (0, 0, 1)
            
            # Render
            self.plotter.render()
            
        except Exception as e:
            print(f"Error resetting camera: {e}")
    # ===== Points Management Methods (Shared) =====
    
    def add_point(self, lon, lat, alt=None, name=None):
        """Add a point to both maps"""
        
        if alt is None:
            # alt = geo.get_altitude(self.lat, self.lon, self.ter, lat, lon)
            alt = self.ter[np.argmin(np.abs(self.lat-lat)), np.argmin(np.abs(self.lon-lon))]
        if name is None:
            name = str(len(self.points)+1)
        self.points.append(Point(lon, lat, alt, name))
        self.update_points_list()
        self.plot_2d()
        self.plot_3d_pyvista()
    
    def update_points_list(self):
        """Update the points list widget"""
        self.points_list.clear()
        for i, p in enumerate(self.points):
            self.points_list.addItem(f"{p.name}: ({p.lon:.4f}, {p.lat:.4f}, {p.alt})")
    
    def delete_selected_point(self, item):  
        """Remove the selected point from the list"""
        current_row = self.points_list.row(item)  
        if current_row >= 0:
            del self.points[current_row] 
            self.update_points_list()
            self.plot_2d()
            self.plot_3d_pyvista()
    
    def rename_selected_point(self, item):
        """Rename the selected point"""
        current_row = self.points_list.row(item)  
        if current_row >= 0: 
            point = self.points[current_row]
            new_name, ok = QInputDialog.getText(
                self,
                "Rename Point",
                f"Enter new name for point '{point.name}'"
            )
            
            if ok and new_name:
                point.name = new_name
                # print('ba')
                self.update_points_list()
                self.plot_2d()
                self.plot_3d_pyvista()

    def get_LOS_airport_and_filter_points(self):
        
        
        for i, pos in enumerate(zip(self.filtered_and_airport_LOS_lons, self.filtered_and_airport_LOS_lats, self.filtered_and_airport_LOS_alts)):
            lon, lat, alt = pos
            self.add_point(lon, lat, alt, f"Potential {i+1}")
            
    def add_points_coordinates(self):
        try:
            lat, ok1 = QInputDialog.getDouble(self, "Add Point", f"Enter latitude ({gc.MAP_MIN_LAT:.4f} to {gc.MAP_MAX_LAT:.4f}):", decimals=6) #ok is a boolean to say if user clicked ok
            if not ok1:
                return
            lon, ok2 = QInputDialog.getDouble(self, "Add Point", f"Enter longitude ({gc.MAP_MIN_LON:.4f} to {gc.MAP_MAX_LON:.4f}):", decimals=6)
            if not ok2:
                return
            # Check if point is inside the map  
            # lat_min, lat_max = np.min(self.lat), np.max(self.lat)
            # lon_min, lon_max = np.min(self.lon), np.max(self.lon)
            
            if not (gc.MAP_MIN_LAT <= lat <= gc.MAP_MAX_LAT) or not (gc.MAP_MIN_LON <= lon <= gc.MAP_MAX_LON):
                QMessageBox.warning(self, "Out of Bounds", "Point is outside the terrain map bounds. Not added.")
                return
            
            self.add_point(lon, lat)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add point:\n{str(e)}")

    def clear_all_points(self):
        """Clear all points"""
        if self.points:
            reply = QMessageBox.question(self, 'Clear Points', 
                                        'Are you sure you want to clear all points?',
                                        QMessageBox.Yes | QMessageBox.No)#type: ignore
            if reply == QMessageBox.Yes:#type: ignore
                self.points.clear()
                self.update_points_list()
                self.plot_2d()
                self.plot_3d_pyvista()
    

    
    def calc_FL_LOS_selected_point(self, item): 
        current_row = self.points_list.row(item) 
        if current_row >= 0:  
            point = self.points[current_row]  
            
            tries = 0
            while tries < 5:
                try:
                    dialog_box = InputWindow(f"Enter flight levels (ex: 5,10,50) to find LOS for a radar at point '{point.name}':", 
                                                "[0-9,]*")
                    result = dialog_box.exec()
                    
                    if result == QDialog.Accepted:#type: ignore
                        user_output = dialog_box.get_input()
                    else:
                        return
                    
                    
                    flight_levels: list[str] = [FL.strip() for FL in user_output.split(",")]
                    
                    for FL in flight_levels:
                        assert 0 < len(FL) <= 3
                        assert FL.isdigit()
                    break
                except Exception as e:
                    print(e)
                    tries += 1
                    print("Please input valid flight levels. Example: 5,10,300")
                    pass
            else:
                print("Number of flight level prompts exceeded. Exiting FL display fct.")
                return
            
            flight_levels = ["FL"+FL for FL in flight_levels]
            # print(flight_levels)
            fields = [(f"Ray Casting Step Size (Grid Res: {self.curr_map.resolution}):", 10, 900, self.ss_ray_casting),
                  ("Radar Height:", 10, 100, self.radar_height_above_terrain),
                  ("N. of azimuthal samples:", 45, 720, self.num_azi),
                  ("LOS cutoff binary search distance delta:", 10, 900, self.min_delta_horiz_dist_BS_cutoff),
                  ("Account for Earth Curvature (0/1):", 0, 1, self.do_earth_curvature)]
                        
            dialog = IntegerInputDialog(fields, "Edit Line of Sight Parameters")
            
            vals = dialog.get_values()
            
            # ss_ray_casting = 90
            # self.n_azi = 360
            
            if vals is None:
                return
            
            
            self.ss_ray_casting, self.radar_height_above_terrain, self.num_azi, self.min_delta_horiz_dist_BS_cutoff, self.do_earth_curvature = vals
                
            InfoWindow(f"Calculating FL LOS for point '{point.name}'. See console for more info.").exec()
            
            LOS_class = LOS_file.LOS(ss_ray_casting=self.ss_ray_casting,
                                            radar_lat=point.lat,
                                            radar_lon=point.lon,
                                            radar_pos_terrain_altitude=point.alt,
                                            radar_height_above_terrain=self.radar_height_above_terrain,
                                            flight_levels=flight_levels,
                                            n_azi_angles=self.num_azi,
                                            min_delta_horiz_dist_BS_cutoff=self.min_delta_horiz_dist_BS_cutoff,
                                            do_earth_curvature=bool(self.do_earth_curvature),
                                            lat=self.lat, lon=self.lon, ter=self.ter, map=self.curr_map)
            data_obj = LOS_class.calc()
            
            self.LOS_window = FlightLevelWindow(point, self.ocean_threshold, self.lat, self.lon, self.ter, data_obj, self.curr_map, self.curr_map.alt_scale)
            self.LOS_window.showMaximized()

    def recompute_constraints(self):
        
        InfoWindow("Extracting valid points from new constraints. Check console for more info.").exec()

        lon_indices, lat_indices, info = filter.full_filter(self.lon, self.lat, self.ter,
                                                    max_distance_from_airport=self.max_dist_to_airport,
                                                    max_distance_from_elec=self.max_dist_to_elec,
                                                    max_distance_from_road=self.max_dist_to_road,
                                                    min_distance_from_building=self.min_dist_to_building)
        
        # self.full_filtered_lats = self.lat[lat_indices]
        # self.full_filtered_lons = self.lon[lon_indices]
        
        self.file_path_filter = "data/constraints_related/filtering/in_app_cache/full_filter_points"
        
        np.savez(self.file_path_filter, lats_idx=lat_indices,lons_idx=lon_indices)
        self.file_path_filter += ".npz"
        
        print(f"Obtained {len(lat_indices)} points after constraints filtering.")
        
        print("Starting airport LOS filtering...")
        self.filtered_and_airport_LOS_lons, self.filtered_and_airport_LOS_lats, self.filtered_and_airport_LOS_alts = LOS_filter(self.lon, self.lat, self.ter,
                                                                                                                                        lon_indices, lat_indices,
                                                                                                                                        self.radar_height_above_terrain,
                                                                                                                                        self.do_earth_curvature)
        print(f"Obtained {len(self.filtered_and_airport_LOS_lons)} points after constraints & airport LOS filtering.")
        
        
        self.get_LOS_airport_and_filter_points_button.setText(f"Load Potential Radar Position Points ({len(self.filtered_and_airport_LOS_lons)} points)")
        masks, info = filter.get_masks(self.lon, self.lat, self.ter,
                                max_distance_from_elec=self.max_dist_to_elec,
                                max_distance_from_road=self.max_dist_to_road,
                                min_distance_from_building=self.min_dist_to_building)
        
        self.elec_mask_file_path = "data/constraints_related/filtering/in_app_cache/elec_mask"
        self.road_mask_file_path = "data/constraints_related/filtering/in_app_cache/road_mask"
        self.building_mask_file_path = "data/constraints_related/filtering/in_app_cache/building_mask"
        np.save(self.elec_mask_file_path, masks["elec"])
        np.save(self.road_mask_file_path, masks["road"])
        np.save(self.building_mask_file_path, masks["building"])
        self.elec_mask_file_path += ".npy"
        self.road_mask_file_path += ".npy"
        self.building_mask_file_path += ".npy"
        # self.invalid_elec_mask = masks["elec"]
        # self.invalid_road_mask = masks["road"]
        # self.invalid_building_mask = masks["building"]
        
        
        InfoWindow("Successfully obtained new constraints data! Obtain potential radar position points from the points panel options.").exec()
        self.plot_3d_pyvista()
        
        # print(len(self.full_filtered_lons))
        

            
            
    def load_FL_LOS(self):
        """Load points from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load FL LOS",
            str(self.FL_LOS_folder),
            "NumPy Files (*.npy);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.npy'):
                    data_obj: LOS_file.DataPackage = np.load(file_path, allow_pickle=True)[0]
                else:
                    assert False
                lon, lat = data_obj.info.radar.GEO_pos.lon, data_obj.info.radar.GEO_pos.lat
                # alt = get_alt(self.lat, self.lon, self.ter, lat, lon)
                alt = self.ter[np.argmin(np.abs(self.lat-lat)), np.argmin(np.abs(self.lon-lon))]
                self.LOS_window = FlightLevelWindow((lon, lat, alt), self.ocean_threshold, self.lat, self.lon, self.ter, data_obj, self.curr_map, filename=str(file_path).split("/")[-1].split(".")[0])
                self.LOS_window.showMaximized()
                
                # QMessageBox.information(self, "Success", 
                #                        f"Loaded FL LOS")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load FL LOS file:\n{str(e)}")

    def save_point(self, item):
        current_row = self.points_list.row(item) 
        if current_row >= 0:  
            point = self.points[current_row] 
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Points",
                str(self.points_folder),
                "NumPy Files (*.npy);;CSV Files (*.csv);;Text Files (*.txt)"
            )
            
            if file_path:
                try:
                    points_array = np.array([point])
                    
                    if file_path.endswith('.npy'):
                        np.save(file_path, points_array)
                    elif file_path.endswith('.csv'):
                        np.savetxt(file_path, points_array, delimiter=',', 
                                header='Longitude,Latitude', comments='')
                    else:
                        np.savetxt(file_path, points_array, 
                                header='Longitude Latitude', comments='')
                    
                    QMessageBox.information(self, "Success", 
                                        f"Saved {len(self.points)} points to {file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save points:\n{str(e)}")
        
    def save_points(self):
        """Save points to a file"""
            
        if not self.points:
            QMessageBox.warning(self, "No Points", "No points to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Points",
            str(self.points_folder),
            "NumPy Files (*.npy);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if file_path:
            try:
                points_array = np.array(self.points)
                
                if file_path.endswith('.npy'):
                    np.save(file_path, points_array)
                elif file_path.endswith('.csv'):
                    np.savetxt(file_path, points_array, delimiter=',', 
                              header='Longitude,Latitude', comments='')
                else:
                    np.savetxt(file_path, points_array, 
                              header='Longitude Latitude', comments='')
                
                QMessageBox.information(self, "Success", 
                                       f"Saved {len(self.points)} points to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save points:\n{str(e)}")
    
    def load_points(self):
        """Load points from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Points",
            str(self.points_folder),
            "NumPy Files (*.npy);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.npy'):
                    points_array = np.load(file_path, allow_pickle=True)
                else:
                    points_array = np.loadtxt(file_path, delimiter=',')
                
                self.points += points_array.tolist()
                self.update_points_list()
                self.plot_2d()
                self.plot_3d_pyvista()
                QMessageBox.information(self, "Success", 
                                       f"Loaded {len(points_array)} points")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load points:\n{str(e)}")
    

    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'plotter'):
            self.plotter.close()
        event.accept()
        