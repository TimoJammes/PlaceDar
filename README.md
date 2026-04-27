Data and Modelling Weeks - Radar Placement Project

Authors:
    Jeanne Baldini, Gabrielle Boussidan, Chloé Hurabielle-Claverie, Timothé Jammes, Selen Sahin.

To launch the GUI, make sure you are in the project's parent directory in your terminal and create a new virtual environment by entering: 
    Windows/Linux: python -m venv .venv
    macOS: python3 -m venv .venv

Then:
    Windows:
        if in PowerShell, enter: .\.venv\Scripts\Activate.ps1
        if in CMD, enter: .venv\Scripts\activate.bat
    Linux/macOS:
        enter: source .venv/bin/activate

(If errors persist with both methods in Windows, try entering:
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
    then entering either of the commands specified above or .\.venv\Scripts\Activate. If all else fails,
    you can always pip install each required python library manually using pip install <module name>.)
You may check that you have properly created and entered the virtual environment by entering:
    Windows/Linux: python -c "import sys; print(sys.executable)"
    macOS: python3 -c "import sys; print(sys.executable)"

The output should point to .venv

Then:
    enter: pip install -r requirements.txt
    (this may take up to a few minutes, there are many dependencies.)

You may then run main.py (staying in the parent directory) and after a short moment the GUI will open.

You may exit the virtual environment by deleting the hidden .venv file in the parent directory.

WARNING: Unfortunately, it seems that the integrated version of pyvista, used for the 3D terrain rendering in the GUI, is unstable on macOS. Trying to switch to the 3D tabs in either window may result in the program crashing/presenting unpredictable behavior. We did not test the program on Linux. Good luck!

You may change maps in the top left corner of the main window (currently Nice and Bhutan have been implemented) to view terrain, place points and visualize lines of sight.

See PlaceDAR-User-Manual.pdf for more launch information, and for information as to how to use the app.

Contents of project:
    -bonus: folder containg code related to the bonus receiver placement task & bonus pairs of receiver points for each transmitter. To recompute pairs and export to kmz files, run bonus_constraints.py having modified TOP_K_PAIRS and TOP_K_PAIRS_EXPORT (number of best pairs kept for visualization on kmz files) making sure that TOP_K_PAIRS is not bigger than TOP_K_PAIRS_EXPORT.
    -data: folder containing all necessary data to run the GUI. Also contains different terrain maps for current use (Bhutan and Nice) and future development.
    -exports: folder to import, export and save flight level files (DataObject in np.array) & coordinate points from GUI.
    -point filters: contains code related to filtering out points based on the different distance-based constraints (roads, buildings, electrical points, regions) (constraints_filter.py) and filtering out points based on if they have a direct line of sight (LOS) to the airport (LOS_filter.py).
    -windows: folder containing code related to the GUI windows, using the PySide6 python library. The primary window code is contained in point_selector_window.py, including point selection and filtering, map/airport LOS/constraints visualization (2D/3D) and import/export of data. flight_level_window.py contains the code for the secondary window to visualize flight levels for a chosen radar location in 2D/3D and export data. The subfolder popup_windows contains smaller utility window code (e.g. info/input boxes).
    -constants.py: contains global constants related to Earth and the Nice map.
    -geo_utils.py: contains various geo-related functions, notably to convert points between different coordinate systems.
    -line_of_sight.py: contains all the code related to computing the line of sight of a radar once chosen in the GUI. 
    -main.py:main file responsible for starting the GUI. This is the only file that should be ran.
    -requirements.txt: venv-related text file to install all python library dependencies with ease.


