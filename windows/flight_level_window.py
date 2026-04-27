import numpy as np
import simplekml
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas#type: ignore
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar#type: ignore

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QMessageBox, QCheckBox, QScrollArea,
                               QDialog, QTabWidget, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

import pyvista as pv
from pyvistaqt import QtInteractor

import geo_utils as geo
from windows.popup_windows.input_window import InputWindow
from windows.popup_windows.info_window import InfoWindow
import constants as gc

class FlightLevelWindow(QMainWindow):
    def __init__(self, point, threshold, lat, lon, ter, data_obj, map, filename=None):
        """
        Initialize Flight Level Visibility Window
        
        Parameters:
        -----------
        point : Point or tuple
            Point object with .lon, .lat, .name or tuple (lon, lat)
        lat : np.ndarray
            Latitude grid array
        lon : np.ndarray
            Longitude grid array
        ter : np.ndarray
            Terrain elevation data
        data_obj : DataPackage, optional
            Pre-loaded data object. If None, will need to be loaded separately
        """
        super().__init__()
        
        # Extract point coordinates
        if hasattr(point, 'lon') and hasattr(point, 'lat'):
            self.point_lon = point.lon
            self.point_lat = point.lat
            self.point_alt = data_obj.info.radar.GEO_pos.alt
            self.point_name = point.name if hasattr(point, 'name') else "Loaded Point"
            
        else:
            self.point_lon, self.point_lat, self.point_alt = point
            self.point_name = filename
        
        self.lat = lat
        self.lon = lon
        self.ter = ter
        self.data_obj = data_obj
        self.threshold = threshold
        
        
        self.map = map
        
        # self.alt_scale = 1/10000 #div scale
        # self.alt_scale = alt_scale
        
        self.point_z_scaled = self.point_alt * self.map.alt_scale
                
        # Initialize visibility tracking
        self.fl_visible = {}
        self.fl_patches = {}
        self.fl_checkboxes = {}
        self.fl_mesh_actors = {}  # Store PyVista mesh actors
        
        # Setup window
        self.setWindowTitle(f"Flight Level Visibility - {self.point_name} | "
            f"Lon: {self.point_lon:.4f}° | "
            f"Lat: {self.point_lat:.4f}°")

        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Control layout
        control_layout = QHBoxLayout()
        
    
        
        self.save_FL_info_button = QPushButton("Save")
        self.save_FL_info_button.clicked.connect(self.save_FL_info)
        control_layout.addWidget(self.save_FL_info_button)
        
        self.export_kmlkmz_FL_button = QPushButton("Export as kml/kmz")
        self.export_kmlkmz_FL_button.clicked.connect(self.export_FL_kml_kmz)
        control_layout.addWidget(self.export_kmlkmz_FL_button)
        
        self.see_info_button = QPushButton("See Info")
        self.see_info_button.clicked.connect(self.show_data_info)
        control_layout.addWidget(self.see_info_button)
        control_layout.addStretch()
        
        main_layout.addLayout(control_layout)
        
        # Create tab widget for 2D and 3D views
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create 2D and 3D tabs
        self.create_2d_tab()
        self.create_3d_tab()
        
        # Load and plot data if available
        if self.data_obj is not None:
            self.plot_flight_levels_2D()
            self.plot_3d_pyvista()
        else:
            assert False
    

    ###dynamic update functions###
    def on_alt_scale_changed(self):
        # self.alt_scale = 1/int(self.alt_scale_input.text())
        self.map.alt_scale = float(self.alt_scale_input.text())
        self.plot_3d_pyvista()

    def on_canvas_resize_2d(self, event):
        """Handle canvas resize to maintain proper layout"""
        if hasattr(self, 'figure'):
            self.figure.tight_layout()
            self.canvas.draw_idle()

    def update_checkboxes(self, FL_obj_list, order):
        """Update checkboxes based on current flight levels"""
        # Clear existing checkboxes
        while self.checkbox_layout.count() > 1:
            item = self.checkbox_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()#type: ignore
        
        self.fl_checkboxes = {}
        
        # Create checkbox for each flight level (in sorted order)
        for rank, i in enumerate(order):
            FL = FL_obj_list[i]
            checkbox = QCheckBox(f"{FL.FL}: {FL.coverage}% Coverage")
            checkbox.setChecked(self.fl_visible.get(i, True))
            checkbox.stateChanged.connect(lambda state, idx=i: self.toggle_fl(idx, state))
            self.checkbox_layout.insertWidget(rank, checkbox)
            self.fl_checkboxes[i] = checkbox
    
    def toggle_fl(self, fl_idx, state):
        """Toggle flight level visibility"""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.fl_visible[fl_idx] = is_checked
        
        if fl_idx in self.fl_checkboxes_3d:
            self.fl_checkboxes_3d[fl_idx].setChecked(is_checked)
        
        # Update PyVista actor visibility
        if fl_idx in self.fl_mesh_actors:
            surface_actor, line_actor, label_actor = self.fl_mesh_actors[fl_idx]
            surface_actor.SetVisibility(is_checked)
            line_actor.SetVisibility(is_checked)
            label_actor.SetVisibility(is_checked)
            self.plotter.render()
        
        # Redraw 2D view
        self.redraw_flight_levels_2D()

    def update_checkboxes_3d(self, FL_names, order):
        """Update 3D checkboxes based on current flight levels"""
        # Clear existing checkboxes
        while self.checkbox_layout_3d.count() > 1:
            item = self.checkbox_layout_3d.takeAt(0)
            if item.widget():
                item.widget().deleteLater()#type: ignore
        
        self.fl_checkboxes_3d = {}
        
        # Create checkbox for each flight level (in sorted order)
        for rank, i in enumerate(order):
            checkbox = QCheckBox(FL_names[i])
            checkbox.setChecked(self.fl_visible.get(i, True))
            checkbox.stateChanged.connect(lambda state, idx=i: self.toggle_fl_3d(idx, state))
            self.checkbox_layout_3d.insertWidget(rank, checkbox)
            self.fl_checkboxes_3d[i] = checkbox

    def toggle_fl_3d(self, fl_idx, state):
        """Toggle flight level visibility in 3D view"""
        is_checked = (state == Qt.CheckState.Checked.value)
        self.fl_visible[fl_idx] = is_checked
        
        # Also update 2D checkbox if it exists
        if fl_idx in self.fl_checkboxes:
            self.fl_checkboxes[fl_idx].setChecked(is_checked)
        
        # Update PyVista actor visibility
        if fl_idx in self.fl_mesh_actors:
            surface_actor, line_actor, label_actor = self.fl_mesh_actors[fl_idx]
            surface_actor.SetVisibility(is_checked)
            line_actor.SetVisibility(is_checked)
            label_actor.SetVisibility(is_checked)
            self.plotter.render()
        
        # Redraw 2D view
        self.redraw_flight_levels_2D()

    def reset_camera_view(self):
        """Reset camera to centered view on radar position"""
        if not hasattr(self, 'plotter') or self.data_obj is None:
            return
        
        try:
            # Get radar position and terrain elevation at radar
            
            
            # lon_idx = np.argmin(np.abs(self.lon - self.point_lon))
            # lat_idx = np.argmin(np.abs(self.lat - self.point_lat))
            # z_value = self.ter[lat_idx, lon_idx] * self.alt_scale
            
            # Set the focal point to the radar position
            self.plotter.camera.focal_point = (self.point_lon, self.point_lat, self.point_z_scaled)
            
            # Calculate a good camera position
            lat_range = np.ptp(self.lat)
            lon_range = np.ptp(self.lon)
            max_range = max(lat_range, lon_range)
            
            # Position camera at an isometric-style angle
            camera_distance = max_range * 3
            self.plotter.camera.position = (
                self.point_lon + camera_distance * 0.7,
                self.point_lat + camera_distance * 0.7,
                self.point_z_scaled + camera_distance * 0.5
            )
            
            # Set the "up" direction
            self.plotter.camera.up = (0, 0, 1)
            
            # Render the updated view
            self.plotter.render()
            
        except Exception as e:
            print(f"Error resetting camera: {e}")        
    ##############################


    ###initial window setup and element creation###    
    def create_checkbox_panel(self):
        """Create the checkbox panel for toggling flight levels"""
        panel = QWidget()
        panel.setMaximumWidth(200)
        panel_layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Flight Levels (2D)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        panel_layout.addWidget(title)
        
        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)#type: ignore
        
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.addStretch()
        
        scroll.setWidget(self.checkbox_container)
        panel_layout.addWidget(scroll)
        
        return panel
     
    def create_2d_tab(self):
        """Create the 2D flight level visualization tab"""
        tab_2d = QWidget()
        self.tab_widget.addTab(tab_2d, "2D Flight Levels")
        
        tab_layout = QHBoxLayout(tab_2d)
        
        # Left side - matplotlib plot
        plot_layout = QVBoxLayout()
        
        # Create matplotlib figure - only set DPI
        self.figure = Figure(dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.StrongFocus)#type: ignore
        self.canvas.setFocus()
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        tab_layout.addLayout(plot_layout, stretch=4)
        
        # Right side - checkbox panel
        self.checkbox_panel = self.create_checkbox_panel()
        tab_layout.addWidget(self.checkbox_panel, stretch=1)
        
        # Connect resize event to adjust plot when window resizes
        self.canvas.mpl_connect('resize_event', self.on_canvas_resize_2d)

    def create_3d_tab(self):
        """Create the 3D terrain visualization tab using PyVista"""
        tab_3d = QWidget()
        self.tab_widget.addTab(tab_3d, "3D Flight Levels")
        
        # Main horizontal layout for 3D plot and checkboxes
        main_h_layout = QHBoxLayout(tab_3d)
        
        # Left side - plot area
        plot_container = QWidget()
        tab_layout = QVBoxLayout(plot_container)
        
        # Control section
        control_layout = QHBoxLayout()
        
        self.plot_button_3d = QPushButton("Refresh Plot")
        self.plot_button_3d.clicked.connect(self.plot_3d_pyvista)
        control_layout.addWidget(self.plot_button_3d)
        
        alt_scale_label = QLabel("Altitude scale:")
        control_layout.addWidget(alt_scale_label)
        
        self.alt_scale_input = QLineEdit(str(self.map.alt_scale))
        self.alt_scale_input.setMaximumWidth(100)
        
        # validator = QDoubleValidator(0.00000, 0.001, 5)
        # validator.setNotation(QDoubleValidator.StandardNotation)#type: ignore
        # self.alt_scale_input.setValidator(validator)
        
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
        
        main_h_layout.addWidget(plot_container, stretch=4)
        
        # Right side - checkbox panel for 3D
        self.checkbox_panel_3d = self.create_checkbox_panel_3d()
        main_h_layout.addWidget(self.checkbox_panel_3d, stretch=1)

    def create_checkbox_panel_3d(self):
        """Create the checkbox panel for toggling flight levels in 3D view"""
        panel = QWidget()
        panel.setMaximumWidth(200)
        panel_layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Flight Levels (3D)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        panel_layout.addWidget(title)
        
        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)#type: ignore
        
        self.checkbox_container_3d = QWidget()
        self.checkbox_layout_3d = QVBoxLayout(self.checkbox_container_3d)
        self.checkbox_layout_3d.addStretch()
        
        scroll.setWidget(self.checkbox_container_3d)
        panel_layout.addWidget(scroll)
        
        return panel    
    ###############################################


    ###plotting functions###
    def plot_flight_levels_2D(self):
        """Plot flight level visibility maps"""
        try:
            if self.data_obj is None:
                return
            
            # Extract flight level data from data_obj
            FL_obj_list = self.data_obj.FL_data
            info = self.data_obj.info
            
            # Get radar position
            radar_pos = info.radar.GEO_pos
            radar_lat, radar_lon, radar_alt = radar_pos.lat, radar_pos.lon, radar_pos.alt
            
            # Extract FL arrays and names
            FL_array = []
            FL_names = []
            for FL in FL_obj_list:
                FL_array.append(FL.LOS)
                FL_names.append(FL.FL)
            
            # Initialize visibility state if not exists
            if not self.fl_visible:
                self.fl_visible = {i: True for i in range(len(FL_names))}
            
            # Convert FL boundary points from ENU to lat/lon
            FL_array_latlon = []
            for points_enu in FL_array:
                E_points = points_enu[:, 0]
                N_points = points_enu[:, 1]
                U_points = np.zeros_like(E_points)
                
                # Convert back to lat/lon using your conversion function
                lat_points, lon_points, _ = geo.enu_to_geodetic_vectorized(
                    radar_lat, radar_lon, radar_alt, E_points, N_points, U_points
                )
                
                points_latlon = np.column_stack([lon_points, lat_points])
                FL_array_latlon.append(points_latlon)
            
            # Create meshgrid for terrain
            lon_grid, lat_grid = np.meshgrid(self.lon, self.lat)
            
            # Setup flight level colors
            N = len(FL_names)
            cmap = plt.get_cmap("Blues", N)
            
            # Define hatching patterns (cycles through if more FLs than patterns)
            hatch_patterns = ['///', '\\\\\\', '|||', '---', '+++', 'xxx', '...', '***']
            
            # Plot visibility zones (sorted by flight level)
            order = np.argsort([int(fl.replace("FL", "")) for fl in FL_names])[::-1]
            
            # Update checkboxes
            self.update_checkboxes(FL_obj_list, order)
            
            # Clear and create plot
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Plot terrain with custom colormap
            vmin = np.nanmin(self.ter)
            vmax = np.nanmax(self.ter)
            
            if self.map.name == "Nice":
                terrain_cmap = plt.get_cmap('terrain')
                norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=self.threshold, vmax=vmax)
            elif self.map.name == "Bhutan":
                terrain_cmap = plt.get_cmap('gist_earth')
                norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            
            pcm = ax.pcolormesh(lon_grid, lat_grid, self.ter, 
                            cmap=terrain_cmap, shading="auto", norm=norm)
            cbar1 = self.figure.colorbar(pcm, ax=ax, pad=0.02)
            cbar1.set_label("Elevation (m)")
            
            # Store patches for toggling
            self.fl_patches = {}
            
            # Plot visible flight levels
            for rank, i in enumerate(order):
                if self.fl_visible.get(i, True):
                    hatch = hatch_patterns[rank % len(hatch_patterns)]
                    patch = self.plot_visibility_fill_2D(ax, FL_array_latlon[i], cmap(rank), 
                                            alpha=0.3, hatch=hatch)
                    self.fl_patches[i] = patch
            
            # Mark radar position and create legend with hatching
            from matplotlib.patches import Patch
            sorted_FL_names = [FL_names[i] for i in order]
            legend_elements = [
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='r', #type: ignore
                        markersize=10, label='Radar'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='pink', #type: ignore
                        markersize=5, label='Airport')
            ]
            for rank, i in enumerate(order):
                hatch = hatch_patterns[rank % len(hatch_patterns)]
                patch = Patch(facecolor=cmap(rank), edgecolor='black', 
                            hatch=hatch, alpha=0.3, label=sorted_FL_names[rank])
                legend_elements.append(patch)#type: ignore
            
            ax.plot(radar_lon, radar_lat, "or", markersize=10, zorder=10)
            ax.plot(self.map.airport.lon, self.map.airport.lat, marker="o", color="pink", markersize=5, zorder=10)
            ax.legend(handles=legend_elements, title="Flight Level", 
                    loc='upper right', framealpha=0.9)
            
            # Store data for toggling
            self.fl_plot_data = {
                'ax': ax,
                'FL_array_latlon': FL_array_latlon,
                'cmap': cmap,
                'order': order,
                'FL_names': FL_names,
                'hatch_patterns': hatch_patterns,
                'radar_lat': radar_lat,
                'radar_lon': radar_lon
            }
            
            # Labels and styling
            ax.set_xlabel("Longitude (°)")
            ax.set_ylabel("Latitude (°)")
            ax.set_title(f"Radar Visibility Maps - {self.point_name}")
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='box')
            
            # REPLACED: Use tight_layout instead of manual subplots_adjust
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot flight levels:\n{str(e)}")

    def plot_3d_pyvista(self):
        """Plot the terrain in 3D using PyVista with radar point and flight level rays"""
        if self.ter is None or self.data_obj is None:
            return
        
        try:
            # Clear the plotter
            self.plotter.clear()
            self.fl_mesh_actors = {}
            # self.fl_label_actors = {}
            
            # Create coordinate grids
            lon_grid, lat_grid = np.meshgrid(self.lon, self.lat)
            
            # Scale altitude for display
            ter_scaled = self.ter * self.map.alt_scale
            
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
                
                if ter_value <= self.threshold:
                    # Below threshold: use blue portion
                    if self.threshold > vmin:
                        ocean_norm = (ter_value - vmin) / (self.threshold - vmin)
                        cmap_pos = 0.35 * ocean_norm
                    else:
                        cmap_pos = 0.35
                else:
                    # Above threshold: use terrain portion
                    if vmax > self.threshold:
                        land_norm = (ter_value - self.threshold) / (vmax - self.threshold)
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
                    'fmt': '%.0f'
                },
                clim=[vmin, vmax],
                lighting=True
            )
            
            
            radar_sphere = pv.Sphere(
                radius=0.001,
                center=(self.point_lon, self.point_lat, self.point_z_scaled)
            )
            self.plotter.add_mesh(radar_sphere, color='red', label='Radar', )
            
            airport_sphere = pv.Sphere(
                radius=0.003,
                center=(self.map.airport.lon, self.map.airport.lat, self.map.airport.alt*self.map.alt_scale)
            )
            
            self.plotter.add_mesh(airport_sphere, color='orange', label='Airport')
            
            pointa = [self.point_lon, self.point_lat, self.point_z_scaled]
            pointb = [self.map.airport.lon, self.map.airport.lat, self.map.airport.alt*self.map.alt_scale]
            
            line = pv.Line(pointa=pointa, pointb=pointb)
            self.plotter.add_mesh(line, color='red', line_width=0.01)
            
            
            self.plotter.add_point_labels(
                        [[self.map.airport.lon, self.map.airport.lat, self.map.airport.alt*self.map.alt_scale]],
                        ["Airport"],
                        font_size=12,
                        text_color='red',
                        bold=True,
                        always_visible=True,
                        shape_opacity=0.0
                    )
                
            self.plotter.add_point_labels(
                        [[self.point_lon, self.point_lat, self.point_z_scaled]],
                        [self.point_name],
                        font_size=12,
                        text_color='red',
                        bold=True,
                        always_visible=True,
                        shape_opacity=0.0
                    )
            
                        
            # Radar position for rays
            radar_pos = np.array([self.point_lon, self.point_lat, self.point_z_scaled])
            
            # Get flight level data
            FL_obj_list = self.data_obj.FL_data
            FL_names = [FL.FL for FL in FL_obj_list]
            
            # Sort by flight level
            order = np.argsort([int(fl.replace("FL", "")) for fl in FL_names])[::-1]
            
            # Update 3D checkboxes
            self.update_checkboxes_3d(FL_names, order)
            
            # Setup colors for flight levels
            N = len(FL_names)
            reds_cmap = plt.get_cmap("Reds", N)
            
            # Plot each visible flight level
            for rank, i in enumerate(order):
                FL = FL_obj_list[i]
                LOS = FL.get_geodetic_LOS(*self.data_obj.info.radar.GEO_pos)
                lon_points = LOS[:, 0]
                lat_points = LOS[:, 1]
                alt_points = LOS[:, 2] * self.map.alt_scale
                
                # Create points array for boundary
                n_points = len(lon_points)
                surface_points = np.column_stack([lon_points, lat_points, alt_points])
                
                # For boundary line, create closed polygon
                boundary_points = np.vstack([surface_points, surface_points[0]])
                
                # Create polyline for the boundary
                poly_line = pv.PolyData(boundary_points)
                poly_line.lines = np.hstack([[len(boundary_points)] + list(range(len(boundary_points)))])
                
                color = reds_cmap(0.5 + 0.5 * rank / max(N-1, 1))
                color_rgb = color[:3]
                
                # Add boundary line
                line_actor = self.plotter.add_mesh(
                    poly_line,
                    color=color_rgb,
                    line_width=10,
                    render_lines_as_tubes=True
                )
                
                # Draw rays from radar to each point on the flight level boundary
                ray_points = []
                ray_lines = []
                point_offset = 0
                
                for j in range(n_points):
                    fl_point = surface_points[j]
                    # Add radar position and FL point
                    ray_points.append(radar_pos)
                    ray_points.append(fl_point)
                    # Line connecting them: [2, start_idx, end_idx]
                    ray_lines.extend([2, point_offset, point_offset + 1])
                    point_offset += 2
                
                # Create PolyData for all rays
                ray_points = np.array(ray_points)
                rays_poly = pv.PolyData(ray_points)
                rays_poly.lines = np.array(ray_lines)
                
                # Add rays with transparency
                rays_actor = self.plotter.add_mesh(
                    rays_poly,
                    color=color_rgb,
                    line_width=3,
                    opacity=0.3
                )
                
                label_actor = self.plotter.add_point_labels(
                    [[self.map.max_lon, self.map.min_lat, alt_points[0]]],
                    [FL.FL],
                    font_size=15,
                    text_color='black',
                    bold=True,
                    always_visible=True,
                    render_points_as_spheres=False,
                    shape_opacity=0.0)
                    
                
                # Store actors for toggling (rays and boundary line)
                self.fl_mesh_actors[i] = (rays_actor, line_actor, label_actor)
                
                # Set initial visibility
                is_visible = self.fl_visible.get(i, True)
                rays_actor.SetVisibility(is_visible)
                line_actor.SetVisibility(is_visible)
                label_actor.SetVisibility(is_visible)
                
            
            # Set up axes
            self.plotter.add_axes(xlabel='Longitude (°)', ylabel='Latitude (°)', zlabel='Elevation (m)')
            
            self.reset_camera_view()
            self.plotter.render()
            
            # Enable interactive features
            self.plotter.enable_anti_aliasing()
            
        except Exception as e:
            print(f"Error plotting 3D: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to plot 3D terrain:\n{str(e)}")
            
    def redraw_flight_levels_2D(self):
        """Redraw only the flight level patches without regenerating everything"""
        if not hasattr(self, 'fl_plot_data'):
            return
        
        data = self.fl_plot_data
        ax = data['ax']
        
        # Remove ALL existing FL patches (even invisible ones)
        for i, patch in list(self.fl_patches.items()):
            if patch in ax.patches:
                patch.remove()
        self.fl_patches = {}
        
        # Redraw ALL flight levels based on current visibility state
        for rank, i in enumerate(data['order']):
            if self.fl_visible.get(i, True):
                hatch = data['hatch_patterns'][rank % len(data['hatch_patterns'])]
                patch = self.plot_visibility_fill_2D(ax, data['FL_array_latlon'][i], 
                                         data['cmap'](rank), alpha=0.3, hatch=hatch)
                self.fl_patches[i] = patch
        
        self.canvas.draw()
    
        """Load and plot both 2D and 3D views"""
        self.plot_flight_levels_2D()
        self.plot_3d_pyvista()
    
    def plot_visibility_fill_2D(self, ax, points, colour, alpha=1.0, hatch=None):
        """Fill visibility polygon on the map"""
        poly = Polygon(points[:, :2], closed=True,
                      facecolor=colour, edgecolor=colour,
                      alpha=alpha, hatch=hatch)
        
        ax.add_patch(poly)
        return poly
    ########################
    
    
    ###other###
    def show_data_info(self):
        """Display comprehensive information about the data_obj"""
        if self.data_obj is None:
            QMessageBox.warning(self, "No Data", "No data object available.")
            return
        
        try:
            # Build info string
            info_text = self.format_data_info()
            
            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Flight Level LOS Data Information")
            dialog.setMinimumSize(500, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Create scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            
            # Create label with info
            info_label = QLabel(info_text)
            info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)#type: ignore
            info_label.setWordWrap(True)
            
            scroll.setWidget(info_label)
            layout.addWidget(scroll)
            
            # Add close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display info:\n{str(e)}")

    def format_data_info(self):
        

        """Format all data_obj information into a readable string"""
        lines = []
        
        # Radar Information
        radar_info = self.data_obj.info.radar
        lines.append(f"Radar Latitude: {radar_info.GEO_pos.lat:.6f}°")
        lines.append(f"Radar Longitude: {radar_info.GEO_pos.lon:.6f}°")
        lines.append(f"Radar Altitude: {radar_info.GEO_pos.alt:.2f} m")
        lines.append(f"Height Above Terrain: {radar_info.height_above_terrain:.2f} m")
        
        lines.append("")
        # Calculation Parameters
        calc_info = self.data_obj.info
        if hasattr(calc_info, 'n_azi_angles'):
            lines.append(f"Number of Azimuth Angles: {calc_info.n_azi_angles}")
        if hasattr(calc_info, 'ss_ray_casting'):
            lines.append(f"Ray Casting Step Size: {calc_info.ss_ray_casting} m")
        if hasattr(calc_info, 'min_delta_horiz_dist_BS_cutoff'):
            lines.append(f"Binary Search Delta Distance Cutoff: {calc_info.min_delta_horiz_dist_BS_cutoff} m")
        if hasattr(calc_info, 'do_earth_curvature'):
            lines.append(f"Earth Curvature Enabled: {bool(calc_info.do_earth_curvature)}")
        
        lines.append("")
        # Flight Level Data
        for i, FL in enumerate(self.data_obj.FL_data):
            lines.append(f"{FL.FL} Altitude: {FL.FL_meters:.2f} m")
            lines.append(f"{FL.FL} Coverage: {FL.coverage}%")
        
        lines.append("")
        
        # Summary Statistics
        lines.append(f"Total Flight Levels: {len(self.data_obj.FL_data)}")
        lines.append(f"Altitude Range: {min(fl.FL_meters for fl in self.data_obj.FL_data):.0f} - "
                    f"{max(fl.FL_meters for fl in self.data_obj.FL_data):.0f} m")
        avg_coverage = np.mean([fl.coverage for fl in self.data_obj.FL_data])
        lines.append(f"Average Coverage: {avg_coverage:.2f}%")
        
        return "\n".join(lines)
    ###########


    ###exports/saving###
    def save_FL_info(self):
        """Save flight level LOS information"""
        try:
            dialog_box = InputWindow(f"Enter file name to save FL LOS info (as DataPackage Object) as:",
                                    "[A-Za-z0-9_]*")
            result = dialog_box.exec()
            
            if result == QDialog.Accepted:#type: ignore
                user_output = dialog_box.get_input()
                
                assert user_output[0].isalnum()
            else:
                return
        except:
            InfoWindow("First character of filename must be alphanumeric!").exec()
            # print("First character of filename must be alphanumeric!")
            return
        
        try:
            np.save("exports/FL_LOS/"+user_output, np.array([self.data_obj]))
            InfoWindow(f"Successful file save at exports/FL_LOS/{user_output}!").exec()
        except Exception as e:
            print(e)
            InfoWindow("Unsuccessful file save! See console for error.").exec()
    
    def export_FL_kml_kmz(self,
        # data_obj: DataPackage,
        # output_path: str = "exports/kmz/"
    ):

        output_path = "exports/kmz/"
        try:
            dialog_box = InputWindow(f"Enter file name to save FL LOS as kmz file to:",
                                    "[A-Za-z0-9_]*")
            result = dialog_box.exec()
            
            if result == QDialog.Accepted:#type: ignore
                
                user_output = dialog_box.get_input()
                # print(user_output)
                assert user_output[0].isalnum()
            else:
                return
        except Exception as e:
            # print(e)
            InfoWindow("First character of filename must be alphanumeric!").exec()
            # print("First character of filename must be alphanumeric!")
            return
        
        user_output += ".kmz"
        
        kml = simplekml.Kml()

        # Radar point ( red pin)

        radar = self.data_obj.info.radar
        radar_pt = kml.newpoint(
            name="Radar",
            coords=[(radar.GEO_pos.lon,
                    radar.GEO_pos.lat,
                    radar.GEO_pos.alt)]
        )
        radar_pt.style.iconstyle.icon.href = ""  #  dot
        radar_pt.style.iconstyle.color = simplekml.Color.red
        radar_pt.style.iconstyle.scale = 1.5

        # Flight level folders

        teal_color = simplekml.Color.changealphaint(100, simplekml.Color.teal)  # semi-transparent

        for fl_res in self.data_obj.FL_data:
            fl_folder = kml.newfolder(name=fl_res.FL)

            # Convert ENU LOS to geodetic
            geo_pts = fl_res.get_geodetic_LOS(
                radar_lat=radar.GEO_pos.lat,
                radar_lon=radar.GEO_pos.lon,
                radar_alt=radar.GEO_pos.alt,
            )

            # Ensure closed polygon
            if not np.allclose(geo_pts[0], geo_pts[-1]):
                geo_pts = np.vstack([geo_pts, geo_pts[0]])

            coords = [(lon, lat, alt) for lon, lat, alt in geo_pts]

            # Create  style for   flight level

            fl_style = simplekml.Style()
            fl_style.linestyle.color = simplekml.Color.teal
            fl_style.linestyle.width = 2
            fl_style.polystyle.color = teal_color


            # Flight level boundary line

            line = fl_folder.newlinestring(#type: ignore
                name=f"{fl_res.FL} LOS Boundary",
                coords=coords
            )
            line.altitudemode = simplekml.AltitudeMode.absolute
            line.style = fl_style  # assign explicit style

            poly = fl_folder.newpolygon(#type: ignore
                name=f"{fl_res.FL} Coverage Area",
                outerboundaryis=coords
            )
            poly.altitudemode = simplekml.AltitudeMode.absolute
            poly.style = fl_style  # assign same style explicitly


        kml.savekmz(output_path+user_output)
        InfoWindow(f"KMZ exported to: {output_path+user_output}").exec()

    def closeEvent(self, event):
        if self.plotter is not None:
            self.plotter.close() 
            self.plotter = None
        event.accept()
