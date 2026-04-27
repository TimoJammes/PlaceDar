# PlaceDAR — Radar Placement Project
**Data and Modelling Weeks**

**Authors:** Jeanne Baldini, Gabrielle Boussidan, Chloé Hurabielle-Claverie, Timothé Jammes, Selen Sahin

---

## Setup

Make sure you are in the project's parent directory, then create a virtual environment:

```bash
# Windows / Linux
python -m venv .venv

# macOS
python3 -m venv .venv
```

Activate it:

```bash
# PowerShell
.\.venv\Scripts\Activate.ps1

# CMD
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

> **Windows troubleshooting:** If activation fails, try running:
> ```
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> then retry. As a last resort, manually `pip install` each required library.

Verify the virtual environment is active (output should point to `.venv`):

```bash
# Windows / Linux
python -c "import sys; print(sys.executable)"

# macOS
python3 -c "import sys; print(sys.executable)"
```

Install dependencies (may take a few minutes):

```bash
pip install -r requirements.txt
```

Then run `main.py` from the parent directory — the GUI will open shortly after.

To exit the virtual environment, delete the `.venv` folder from the parent directory.

---

## Usage

- Change maps in the **top left corner** of the main window (Nice and Bhutan are currently implemented) to view terrain, place points, and visualize lines of sight.
- See `PlaceDAR-User-Manual.pdf` for detailed launch and usage instructions.

> ⚠️ **macOS warning:** The 3D terrain rendering (powered by PyVista) is unstable on macOS. Switching to 3D tabs may cause crashes or unpredictable behavior. Linux has not been tested.

---

## Project Structure

| Path | Description |
|---|---|
| `bonus/` | Code for the bonus receiver placement task. To recompute pairs and export to KMZ, run `bonus_constraints.py` after setting `TOP_K_PAIRS` and `TOP_K_PAIRS_EXPORT` (ensure `TOP_K_PAIRS ≤ TOP_K_PAIRS_EXPORT`). |
| `data/` | All data required to run the GUI, including terrain maps for Nice and Bhutan and additional maps for future development. |
| `exports/` | Import, export, and save flight level files and coordinate points from the GUI. |
| `point_filters/` | Filtering logic: `constraints_filter.py` filters by distance-based constraints (roads, buildings, electrical points, regions); `LOS_filter.py` filters by direct line of sight to the airport. |
| `windows/` | GUI code using PySide6. `point_selector_window.py` handles point selection, filtering, map/LOS/constraints visualization (2D & 3D), and data import/export. `flight_level_window.py` handles the secondary window for flight level visualization and export. `popup_windows/` contains utility dialogs. |
| `constants.py` | Global constants for Earth and the Nice map. |
| `geo_utils.py` | Geo-related utility functions, notably for converting between coordinate systems. |
| `line_of_sight.py` | All logic for computing radar line of sight. |
| `main.py` | **Entry point.** The only file that should be run directly. |
| `requirements.txt` | Python dependency list for `pip install -r`. |
