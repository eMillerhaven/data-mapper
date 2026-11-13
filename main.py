from dataclasses import dataclass
import math
import matplotlib.pyplot as plt
from drafter import *


# =====================================================================
# 1. SITE CONFIGURATION & CONSTANTS
# =====================================================================

set_website_title("Data Mapper")
set_website_framed(True)

# Used AI to learn about Drafter's CSS styling functions and style arguments and implement them for page layout
add_website_css("h1", "font-size: 1rem; margin-bottom: 0.4rem;")
add_website_css("h3", "font-size: 0.75rem; margin-bottom: 0.25rem;")
add_website_css("#drafter-debug-panel", "display: none;")

set_site_information(
    "Evan Miller",
    "Interactive data mapping, distance analysis, and plotting.",
    "OpenStreetMap via Drafter; sample Newark AG Farm and Wilmington climate datasets.",
    "See planning.pdf in the GitHub repository.",
    ["https://emillerhaven.github.io/data-mapper/"],
)

EARTH_RADIUS_KM: float = 6371.0
MIN_LAT: float = -90.0
MAX_LAT: float = 90.0
MIN_LON: float = -180.0
MAX_LON: float = 180.0
PLOT_TYPES: list[str] = ["scatter", "line", "histogram"]
X_AXIS_FIELDS: list[str] = ["index", "date", "latitude", "longitude", "name"]
Y_AXIS_FIELDS: list[str] = ["value", "latitude", "longitude"]
DEFAULT_LAT: float = 39.6812
DEFAULT_LON: float = -75.7519
MONTH_NAMES: list[str] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
AG_FARM_LAT: float = 39.6682
AG_FARM_LON: float = -75.7457

NEWARK_AG_FARM_CSV: str = (
    "Month,MAX TEMP (F),MIN TEMP (F),AVG TEMP (F),PRECIP (IN)\n"
    "Jan,42.5,25.1,33.8,3.43\n"
    "Feb,45.6,25.4,35.5,2.91\n"
    "Mar,54.2,32.8,43.5,4.27\n"
    "Apr,66.9,42.1,54.5,3.71\n"
    "May,75.6,51.9,63.8,3.63\n"
    "Jun,83.8,61.5,72.6,3.95\n"
    "Jul,88.6,66.4,77.5,4.84\n"
    "Aug,86.8,64.7,75.7,3.95\n"
    "Sep,79.4,58.4,68.9,4.87\n"
    "Oct,69.1,46.2,57.7,4.00\n"
    "Nov,56.9,35.9,46.4,3.36\n"
    "Dec,47.0,29.8,38.4,4.04\n"
)

WILMINGTON_LAT: float = 39.6787
WILMINGTON_LON: float = -75.6065

WILMINGTON_CSV: str = (
    "Month,MAX TEMP (F),MIN TEMP (F),AVG TEMP (F),PRECIP (IN),SNOW (IN)\n"
    "Jan,41.4,25.6,33.5,3.23,6.1\n"
    "Feb,44.1,27.0,35.5,2.83,7.8\n"
    "Mar,52.5,33.9,43.2,4.16,3.1\n"
    "Apr,64.2,43.5,53.9,3.51,0.1\n"
    "May,73.5,53.4,63.5,3.57,0.0\n"
    "Jun,82.2,63.0,72.6,4.67,0.0\n"
    "Jul,86.8,68.3,77.6,4.41,0.0\n"
    "Aug,84.9,66.6,75.8,3.98,0.0\n"
    "Sep,78.5,59.3,68.9,4.38,0.0\n"
    "Oct,67.0,47.3,57.2,3.68,0.0\n"
    "Nov,55.9,37.4,46.6,3.06,0.2\n"
    "Dec,46.0,30.3,38.2,3.85,2.9\n"
)

# =====================================================================
# 2. DATACLASSES (DATA MODEL & APPLICATION STATE)
# =====================================================================

@dataclass
class Data:
    name: str
    value: float
    date: str
    latitude: float
    longitude: float


@dataclass
class Dataset:
    name: str
    datapoints: list[Data]
    toggled: bool
    notes: str


@dataclass
class SelectedPoint:
    dataset_index: int
    data_index: int


@dataclass
class GraphConfig:
    dataset_indices: list[int]
    x_field: str
    y_field: str
    plot_type: str
    plot_title: str
    show_legend: bool
    is_configured: bool


@dataclass
class DistanceQuery:
    start: str
    end: str
    distance: float


@dataclass
class State:
    datasets: list[Dataset]
    selected: SelectedPoint | None
    graph_config: GraphConfig
    status_message: str
    last_distance: DistanceQuery | None
    table_sort_by: str
    table_sort_reverse: bool
    pending_delete_index: int | None


# =====================================================================
# 3. SHARED NAVIGATION & INITIAL STATE HELPERS
# =====================================================================

def build_nav_bar() -> Div:
    """Create the top navigation bar split across two clean rows."""
    row_one = Row(
        Link("Map Explorer", "index"),
        Link("Add Data Point", "add_point_page"),
        Link("Import File", "upload_file_page"),
        Link("View Graph", "view_graph_page"),
        style_gap="12px",
    )
    row_two = Row(
        Link("Graph Settings", "graph_settings_page"),
        Link("Data Table", "data_table_page"),
        Link("Remove Datasets", "remove_datasets_page"),
        style_gap="12px",
    )
    return Div(row_one, row_two)


def build_status_banner(state: State) -> Paragraph:
    """Render the current status message consistently across pages."""
    return Paragraph("Status: " + state.status_message)


def make_initial_state() -> State:
    """Build initial State with Newark AG Farm and Wilmington datasets."""
    datasets = [
        parse_text_to_dataset(
            NEWARK_AG_FARM_CSV,
            "NewarkAGFarm High Temps",
            0,
            1,
            AG_FARM_LAT,
            AG_FARM_LON,
        ),
        parse_text_to_dataset(
            NEWARK_AG_FARM_CSV,
            "NewarkAGFarm Low Temps",
            0,
            2,
            AG_FARM_LAT,
            AG_FARM_LON,
        ),
        parse_text_to_dataset(
            NEWARK_AG_FARM_CSV,
            "NewarkAGFarm Average Temps",
            0,
            3,
            AG_FARM_LAT,
            AG_FARM_LON,
        ),
        parse_text_to_dataset(
            NEWARK_AG_FARM_CSV,
            "NewarkAGFarm Precipitation(in)",
            0,
            4,
            AG_FARM_LAT,
            AG_FARM_LON,
        ),
        parse_text_to_dataset(
            WILMINGTON_CSV,
            "Wilmington High Temps",
            0,
            1,
            WILMINGTON_LAT,
            WILMINGTON_LON,
        ),
        parse_text_to_dataset(
            WILMINGTON_CSV,
            "Wilmington Low Temps",
            0,
            2,
            WILMINGTON_LAT,
            WILMINGTON_LON,
        ),
        parse_text_to_dataset(
            WILMINGTON_CSV,
            "Wilmington Average Temps",
            0,
            3,
            WILMINGTON_LAT,
            WILMINGTON_LON,
        ),
        parse_text_to_dataset(
            WILMINGTON_CSV,
            "Wilmington Precipitation(in)",
            0,
            4,
            WILMINGTON_LAT,
            WILMINGTON_LON,
        ),
        parse_text_to_dataset(
            WILMINGTON_CSV,
            "Wilmington Snow(in)",
            0,
            5,
            WILMINGTON_LAT,
            WILMINGTON_LON,
        ),
    ]
    for idx in range(len(datasets)):
        if idx < 4:
            datasets[idx].notes = "Newark AG Farm monthly climate normals"
        else:
            datasets[idx].notes = "Wilmington monthly climate normals"

    default_graph = GraphConfig(
        dataset_indices=[],
        x_field="date",
        y_field="value",
        plot_type="line",
        plot_title="",
        show_legend=True,
        is_configured=False,
    )
    return State(
        datasets=datasets,
        selected=None,
        graph_config=default_graph,
        status_message=(
            "Welcome! Loaded example NewarkAGFarm and Wilmington datasets — "
            "click a map marker or explore the tools."
        ),
        last_distance=None,
        table_sort_by="name",
        table_sort_reverse=False,
        pending_delete_index=None,
    )


# =====================================================================
# 4. MAP & DISTANCE ACTION GROUP
# =====================================================================

def haversine_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate great-circle distance in km between two coordinates."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(EARTH_RADIUS_KM * c, 3)


def build_map_markers(datasets: list[Dataset]) -> list[MapMarker]:
    """Extract MapMarker objects from all toggled datasets."""
    markers: list[MapMarker] = []
    for ds in datasets:
        if ds.toggled:
            for pt in ds.datapoints:
                markers.append(MapMarker(pt.latitude, pt.longitude, pt.name))
    return markers


def build_layer_toggles(datasets: list[Dataset]) -> list[Component]:
    """Build toggle buttons for showing or hiding each dataset layer."""
    controls: list[Component] = [Header("Dataset Layers", 3)]
    for idx in range(len(datasets)):
        ds = datasets[idx]
        if ds.toggled:
            state_label = "ON"
        else:
            state_label = "OFF"
        btn_text = ds.name + ": " + state_label
        controls.append(
            Button(btn_text, "toggle_dataset", Argument("dataset_idx", idx))
        )
    return controls


def build_side_panel(state: State) -> Div:
    """Build the right-hand panel containing title, nav, and status."""
    panel_items: list[Component] = [
        Header("Data Mapper"),
        build_nav_bar(),
        HorizontalRule(),
        Paragraph("Status: " + state.status_message),
    ]
    if state.last_distance is not None:
        dq = state.last_distance
        dist_text = (
            "Distance from "
            + dq.start
            + " to "
            + dq.end
            + ": "
            + str(dq.distance)
            + " km"
        )
        panel_items.append(Paragraph(dist_text))

    return Div(
        panel_items,
        style_width="50%",
        style_padding="16px",
    )


@route
def index(state: State) -> Page:
    """Render the main Map Explorer with layer toggles below the map."""
    markers = build_map_markers(state.datasets)
    map_view = Map(
        "field_map",
        markers=markers,
        center=(39.6812, -75.7519),
        zoom=13,
        on_marker_click="inspect_marker",
        on_click="handle_map_click",
        style_width="100%",
        style_height="450px",
    )
    left_items: list[Component] = [map_view]
    toggles = build_layer_toggles(state.datasets)
    for item in toggles:
        left_items.append(item)

    left_column = Div(
        left_items,
        style_width="50%",
        style_padding="8px",
    )
    right_column = build_side_panel(state)

    return Page(
        state,
        [
            Row(
                left_column,
                right_column,
                style_width="100%",
                style_align_items="flex-start",
            )
        ],
    )


@route
def toggle_dataset(state: State, dataset_idx: int) -> Page:
    """Toggle visibility on or off and report live visible counts."""
    target = state.datasets[dataset_idx]
    target.toggled = not target.toggled

    visible_sets = 0
    for ds in state.datasets:
        if ds.toggled:
            visible_sets += 1

    visible_pts = len(build_map_markers(state.datasets))
    if visible_sets == 0:
        state.status_message = (
            "All datasets hidden — toggle a layer ON to view markers."
        )
    else:
        state.status_message = (
            "Showing "
            + str(visible_sets)
            + " of "
            + str(len(state.datasets))
            + " datasets ("
            + str(visible_pts)
            + " markers on map)."
        )
    return index(state)


@route
def clear_selection(state: State) -> Page:
    """Clear the active selected point and last distance query."""
    state.selected = None
    state.last_distance = None
    state.status_message = "Selection cleared. Click a marker to inspect."
    return index(state)


@route
def handle_map_click(
    state: State, lat: float = 0.0, lon: float = 0.0
) -> Page:
    """Compute distance from the selected point to a clicked map spot."""
    if state.selected is None:
        state.status_message = (
            "Click a station marker first to measure distance from it."
        )
        return index(state)
    ds = state.datasets[state.selected.dataset_index]
    pt = ds.datapoints[state.selected.data_index]
    dist_km = haversine_km(pt.latitude, pt.longitude, lat, lon)
    end_label = (
        "Click ("
        + str(round(lat, 4))
        + ", "
        + str(round(lon, 4))
        + ")"
    )
    state.last_distance = DistanceQuery(pt.name, end_label, dist_km)
    state.status_message = (
        "Measured " + str(dist_km) + " km from " + pt.name + "."
    )
    return index(state)


# =====================================================================
# 5. POINT DISPLAY & DATA ENTRY ACTION GROUP
# =====================================================================

def is_valid_coords(lat: float, lon: float) -> bool:
    """Verify latitude and longitude fall within standard GPS bounds."""
    return (MIN_LAT <= lat <= MAX_LAT) and (MIN_LON <= lon <= MAX_LON)


@route
def inspect_marker(
    state: State, latitude: float, longitude: float, label: str
) -> Page:
    """Open Data Table if multiple points share coordinates, else Detail Page."""
    clicked_pt: Data | None = None
    clicked_loc: SelectedPoint | None = None

    for d_idx in range(len(state.datasets)):
        ds = state.datasets[d_idx]
        for p_idx in range(len(ds.datapoints)):
            pt = ds.datapoints[p_idx]
            if pt.name == label and clicked_pt is None:
                clicked_pt = pt
                clicked_loc = SelectedPoint(d_idx, p_idx)

    if clicked_pt is None or clicked_loc is None:
        state.status_message = "Marker record could not be located."
        return index(state)

    state.selected = clicked_loc
    matching_datasets: list[int] = []
    match_count = 0

    for d_idx in range(len(state.datasets)):
        ds = state.datasets[d_idx]
        for pt in ds.datapoints:
            if (
                pt.latitude == clicked_pt.latitude
                and pt.longitude == clicked_pt.longitude
            ):
                if d_idx not in matching_datasets:
                    matching_datasets.append(d_idx)
                match_count += 1

    if match_count > 1:
        for d_idx in range(len(state.datasets)):
            state.datasets[d_idx].toggled = d_idx in matching_datasets
        state.status_message = (
            "Found "
            + str(match_count)
            + " points at ("
            + str(clicked_pt.latitude)
            + ", "
            + str(clicked_pt.longitude)
            + ") — showing matching dataset(s) in table."
        )
        return data_table_page(state)

    state.status_message = (
        "Inspecting '"
        + clicked_pt.name
        + "' ("
        + str(clicked_pt.value)
        + ") — return to Map Explorer to measure distances from it."
    )
    return point_detail_page(state)


@route
def point_detail_page(state: State) -> Page:
    """Display all attributes of the currently selected Data point."""
    if state.selected is None:
        return Page(
            state,
            [
                Header("Point Details"),
                build_nav_bar(),
                Paragraph("No point currently selected."),
            ],
        )
    ds = state.datasets[state.selected.dataset_index]
    pt = ds.datapoints[state.selected.data_index]
    details = DefinitionList(
        [
            ("Dataset", ds.name),
            ("Station Name", pt.name),
            ("Measured Value", str(pt.value)),
            ("Date Recorded", pt.date),
            ("Latitude", str(pt.latitude)),
            ("Longitude", str(pt.longitude)),
        ]
    )
    return Page(
        state,
        [
            Header("Station: " + pt.name),
            build_nav_bar(),
            details,
            Paragraph("Click anywhere on the Map Explorer to measure from here."),
            Button("Return to Map", "return_to_map"),
        ],
    )


@route
def return_to_map(state: State) -> Page:
    """Return to the map dashboard with an updated anchor prompt."""
    if state.selected is not None:
        ds = state.datasets[state.selected.dataset_index]
        pt = ds.datapoints[state.selected.data_index]
        state.status_message = (
            "Active anchor: "
            + pt.name
            + " ("
            + str(pt.value)
            + "). Click map to measure distance."
        )
    else:
        state.status_message = "Map Explorer ready."
    return index(state)


@route
def add_point_page(state: State) -> Page:
    """Render the form to manually add a new Data point."""
    ds_names: list[str] = []
    for ds in state.datasets:
        ds_names.append(ds.name)

    return Page(
        state,
        [
            Header("Add New Field Observation"),
            build_nav_bar(),
            Paragraph("Target Dataset:"),
            SelectBox("dataset_name", ds_names),
            Paragraph("Station / Point Name:"),
            TextBox("name", "Station Alpha"),
            Paragraph("Measured Value (numeric):"),
            TextBox("value", "20.0"),
            Paragraph("Date (YYYY-MM-DD):"),
            TextBox("date", "2026-11-12"),
            Paragraph("Latitude (-90 to 90):"),
            TextBox("lat", "39.6800"),
            Paragraph("Longitude (-180 to 180):"),
            TextBox("lon", "-75.7500"),
            Button("Save Observation", "save_point"),
        ],
    )


@route
def save_point(
    state: State,
    dataset_name: str,
    name: str,
    value: str,
    date: str,
    lat: str,
    lon: str,
) -> Page:
    """Validate inputs, instantiate Data, and append to target Dataset."""
    try:
        num_val = float(value)
        num_lat = float(lat)
        num_lon = float(lon)
    except ValueError:
        state.status_message = (
            "Error: Value, latitude, and longitude must be numbers."
        )
        return index(state)

    if not is_valid_coords(num_lat, num_lon):
        state.status_message = "Error: Coordinates out of valid GPS bounds."
        return index(state)

    new_pt = Data(name.strip(), num_val, date.strip(), num_lat, num_lon)
    for ds in state.datasets:
        if ds.name == dataset_name:
            ds.datapoints.append(new_pt)
            state.status_message = (
                "Saved '" + new_pt.name + "' to " + ds.name + "."
            )
            return index(state)

    state.status_message = "Error: Target dataset not found."
    return index(state)


def parse_compact_row(line: str) -> tuple[str, list[float]]:
    """Parse a compact string without commas (e.g. 'Jan42.525.133.83.43')."""
    if len(line) >= 3:
        label = line[:3]
    else:
        label = "Row"

    if label in MONTH_NAMES:
        remainder = line[3:]
    else:
        remainder = line

    nums: list[float] = []
    idx = 0
    while idx < len(remainder):
        dot_pos = remainder.find(".", idx)
        if dot_pos == -1:
            break
        if remainder.find(".", dot_pos + 1) == -1:
            decimals = 2
        else:
            decimals = 1
        end_pos = min(dot_pos + 1 + decimals, len(remainder))
        try:
            nums.append(float(remainder[idx:end_pos]))
        except ValueError:
            pass
        idx = end_pos
    return label, nums


def parse_csv_row(
    parts: list[str], date_col: int, value_col: int
) -> Data | None:
    """Convert a comma-separated list of tokens into a Data object."""
    if value_col < 0 or value_col >= len(parts):
        return None
    try:
        num_val = float(parts[value_col])
    except ValueError:
        return None

    if 0 <= date_col < len(parts) and parts[date_col] != "":
        date_val = parts[date_col]
    else:
        date_val = "Unknown"

    if parts[0] != "":
        label_val = parts[0]
    else:
        label_val = date_val

    return Data(
        name=label_val,
        value=num_val,
        date=date_val,
        latitude=DEFAULT_LAT,
        longitude=DEFAULT_LON,
    )


def parse_text_to_dataset(
    raw_text: str,
    dataset_name: str,
    date_col: int,
    value_col: int,
    lat: float,
    lon: float,
) -> Dataset:
    """Convert raw CSV or compact text rows into a Dataset of Data objects."""
    points: list[Data] = []
    lines = raw_text.strip().splitlines()
    for raw_line in lines:
        clean_line = raw_line.strip()
        if clean_line == "":
            continue

        if "," in clean_line:
            raw_parts = clean_line.split(",")
            parts: list[str] = []
            for token in raw_parts:
                parts.append(token.strip())
            pt = parse_csv_row(parts, date_col, value_col)
            if pt is not None:
                pt.name = pt.name + " (" + dataset_name + ")"
                pt.latitude = lat
                pt.longitude = lon
                points.append(pt)
        else:
            label, nums = parse_compact_row(clean_line)
            if len(nums) > 0:
                num_idx = max(0, value_col - 1)
                if num_idx >= len(nums):
                    num_idx = 0
                points.append(
                    Data(
                        name=label + " (" + dataset_name + ")",
                        value=nums[num_idx],
                        date=label,
                        latitude=lat,
                        longitude=lon,
                    )
                )

    return Dataset(
        name=dataset_name,
        datapoints=points,
        toggled=True,
        notes="Imported from uploaded file",
    )


@route
def upload_file_page(state: State) -> Page:
    """Render the page to upload a .csv or .txt file into a new Dataset."""
    return Page(
        state,
        [
            Header("Import Dataset from File"),
            build_nav_bar(),
            build_status_banner(state),
            Paragraph(
                "Upload a .csv or .txt file (supports comma-separated rows "
                "like 'Jan,42.5,25.1,33.8,3.43' or compact climate rows)."
            ),
            Paragraph("New Dataset Name:"),
            TextBox("dataset_name", "Newark Monthly Climate"),
            Paragraph("Column Number for Date (1 = first column):"),
            TextBox("date_choice", "1"),
            Paragraph("Column Number for Value (e.g. 2, 3, 4, 5):"),
            TextBox("metric_choice", "2"),
            Paragraph("Default Latitude for points without coordinates:"),
            TextBox("lat", str(DEFAULT_LAT)),
            Paragraph("Default Longitude for points without coordinates:"),
            TextBox("lon", str(DEFAULT_LON)),
            Paragraph("Select Text / CSV File:"),
            FileUpload("uploaded_file", accept=".csv,.txt"),
            Button("Parse & Import Dataset", "process_uploaded_file"),
        ],
    )


@route
def process_uploaded_file(
    state: State,
    dataset_name: str,
    date_choice: str,
    metric_choice: str,
    lat: str,
    lon: str,
    uploaded_file: str,
) -> Page:
    """Parse an uploaded text/CSV file into Data instances and save."""
    try:
        num_lat = float(lat)
        num_lon = float(lon)
        date_col = int(date_choice.strip()) - 1
        value_col = int(metric_choice.strip()) - 1
    except ValueError:
        state.status_message = (
            "Error: Coordinates and column numbers must be valid numbers."
        )
        return upload_file_page(state)

    if date_col < 0 or value_col < 0:
        state.status_message = "Error: Column numbers must be 1 or greater."
        return upload_file_page(state)

    if not is_valid_coords(num_lat, num_lon):
        state.status_message = "Error: Coordinates out of valid GPS bounds."
        return upload_file_page(state)

    if uploaded_file == "":
        state.status_message = "Error: Please select a .csv or .txt file first."
        return upload_file_page(state)

    clean_title = dataset_name.strip()
    if clean_title == "":
        clean_title = "Imported Dataset"

    new_ds = parse_text_to_dataset(
        uploaded_file, clean_title, date_col, value_col, num_lat, num_lon
    )

    if len(new_ds.datapoints) == 0:
        state.status_message = "Error: No valid numeric rows found in file."
        return upload_file_page(state)

    for ds in state.datasets:
        ds.toggled = False

    new_ds.toggled = True
    state.datasets.append(new_ds)
    state.status_message = (
        "Imported '"
        + new_ds.name
        + "' with "
        + str(len(new_ds.datapoints))
        + " records (showing only this dataset)."
    )
    return data_table_page(state)


@route
def remove_datasets_page(state: State) -> Page:
    """Render all datasets with single-click selection and confirmation."""
    page_items: list[Component] = [
        Header("Remove Datasets"),
        build_nav_bar(),
        build_status_banner(state),
        Paragraph("Click a dataset below once to select it for removal:"),
    ]

    if len(state.datasets) == 0:
        page_items.append(Paragraph("No datasets currently loaded."))
        return Page(state, page_items)

    for idx in range(len(state.datasets)):
        ds = state.datasets[idx]
        if state.pending_delete_index == idx:
            prefix = "[Selected to Remove] "
        else:
            prefix = ""
        btn_label = (
            prefix
            + ds.name
            + " ("
            + str(len(ds.datapoints))
            + " pts)"
        )
        page_items.append(
            Button(
                btn_label,
                "select_dataset_to_remove",
                Argument("dataset_idx", idx),
            )
        )

    if state.pending_delete_index is not None:
        idx = state.pending_delete_index
        if 0 <= idx < len(state.datasets):
            target_name = state.datasets[idx].name
            page_items.append(HorizontalRule())
            page_items.append(
                Paragraph(
                    "Are you sure you want to permanently remove '"
                    + target_name
                    + "'?"
                )
            )
            page_items.append(
                Row(
                    Button("Confirm Removal", "confirm_remove_dataset"),
                    Button("Cancel", "cancel_remove_dataset"),
                    style_gap="8px",
                )
            )

    return Page(state, page_items)


@route
def select_dataset_to_remove(state: State, dataset_idx: int) -> Page:
    """Mark a dataset as pending removal on first click."""
    state.pending_delete_index = dataset_idx
    ds_name = state.datasets[dataset_idx].name
    state.status_message = (
        "Selected '" + ds_name + "' — click Confirm Removal to delete."
    )
    return remove_datasets_page(state)


@route
def cancel_remove_dataset(state: State) -> Page:
    """Cancel the pending dataset removal."""
    state.pending_delete_index = None
    state.status_message = "Dataset removal canceled."
    return remove_datasets_page(state)


@route
def confirm_remove_dataset(state: State) -> Page:
    """Remove the selected dataset from state and clean up saved indices."""
    idx = state.pending_delete_index
    if idx is None or idx < 0 or idx >= len(state.datasets):
        state.pending_delete_index = None
        state.status_message = "Error: No valid dataset selected to remove."
        return remove_datasets_page(state)

    removed_ds = state.datasets.pop(idx)
    state.pending_delete_index = None

    # Clean up active map anchor if its dataset was removed or shifted
    if state.selected is not None:
        if state.selected.dataset_index == idx:
            state.selected = None
            state.last_distance = None
        elif state.selected.dataset_index > idx:
            state.selected.dataset_index -= 1

    # Clean up saved graph dataset indices if shifted or removed
    updated_graph_indices: list[int] = []
    for g_idx in state.graph_config.dataset_indices:
        if g_idx < idx:
            updated_graph_indices.append(g_idx)
        elif g_idx > idx:
            updated_graph_indices.append(g_idx - 1)
    state.graph_config.dataset_indices = updated_graph_indices
    if len(updated_graph_indices) == 0:
        state.graph_config.is_configured = False

    state.status_message = "Removed dataset '" + removed_ds.name + "'."
    return remove_datasets_page(state)


# =====================================================================
# 6. GRAPH & ANALYTICS ACTION GROUP
# =====================================================================

def extract_axis_values(datapoints: list[Data], field: str) -> list:
    """Extract a list of values for a specific Data attribute."""
    results: list = []
    for idx in range(len(datapoints)):
        pt = datapoints[idx]
        if field == "value":
            results.append(pt.value)
        elif field == "date":
            results.append(pt.date)
        elif field == "latitude":
            results.append(pt.latitude)
        elif field == "longitude":
            results.append(pt.longitude)
        elif field == "name":
            results.append(pt.name)
        else:
            results.append(idx)
    return results


def build_analytics_figure(
    config: GraphConfig, datasets: list[Dataset]
) -> plt.Figure:
    """Generate a Matplotlib figure for all selected datasets."""
    plt.close("all")
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")

    names: list[str] = []
    for idx in config.dataset_indices:
        if 0 <= idx < len(datasets):
            ds = datasets[idx]
            names.append(ds.name)
            x_vals = extract_axis_values(ds.datapoints, config.x_field)
            y_vals = extract_axis_values(ds.datapoints, config.y_field)

            if config.plot_type == "scatter":
                ax.scatter(x_vals, y_vals, label=ds.name)
            elif config.plot_type == "histogram":
                ax.hist(y_vals, bins=5, alpha=0.6, label=ds.name)
            else:
                ax.plot(x_vals, y_vals, marker="o", label=ds.name)

    if config.plot_title != "":
        title = config.plot_title
    elif len(names) == 1:
        title = names[0] + ": " + config.y_field + " vs " + config.x_field
    else:
        title = (
            "Dataset Comparison: "
            + config.y_field
            + " vs "
            + config.x_field
        )

    if config.plot_type == "histogram":
        x_label = "Value Bins"
        y_label = "Frequency"
    else:
        x_label = config.x_field.capitalize()
        y_label = config.y_field.capitalize()

    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, linestyle="--", alpha=0.4)
    if config.show_legend:
        ax.legend()
    return fig


def build_dataset_summary(
    config: GraphConfig, datasets: list[Dataset]
) -> Table:
    """Build a summary stats table with one row per plotted dataset."""
    rows: list[list[Component | str | int | float | bool]] = [
        ["Dataset", "Metric", "Count", "Min", "Max", "Mean"]
    ]
    for idx in config.dataset_indices:
        if 0 <= idx < len(datasets):
            ds = datasets[idx]
            vals = extract_axis_values(ds.datapoints, config.y_field)
            if len(vals) == 0:
                rows.append([ds.name, config.y_field, "0", "-", "-", "-"])
            else:
                mean_val = round(sum(vals) / len(vals), 2)
                rows.append(
                    [
                        ds.name,
                        config.y_field,
                        str(len(vals)),
                        str(min(vals)),
                        str(max(vals)),
                        str(mean_val),
                    ]
                )
    return Table(rows)


@route
def view_graph_page(state: State) -> Page:
    """Render the saved graph, or prompt the user to configure one first.

    Note: MatPlotLibPlot pixel output cannot be deeply compared in unit
    tests, so tests verify Page creation and GraphConfig state instead.
    """
    cfg = state.graph_config
    if not cfg.is_configured or len(cfg.dataset_indices) == 0:
        return Page(
            state,
            [
                Header("Data Visualization"),
                build_nav_bar(),
                build_status_banner(state),
                Paragraph(
                    "No graph is currently loaded. Select one or more datasets "
                    "and choose which attributes to plot on the X and Y axes."
                ),
                Button("Configure Graph & Select Datasets", "graph_settings_page"),
            ],
        )

    build_analytics_figure(cfg, state.datasets)
    plot_component = MatPlotLibPlot()

    return Page(
        state,
        [
            Header("Data Visualization"),
            build_nav_bar(),
            build_status_banner(state),
            plot_component,
            build_dataset_summary(cfg, state.datasets),
            Button("Edit Graph Settings", "graph_settings_page"),
        ],
    )


@route
def select_graph_dataset(state: State, dataset_idx: int) -> Page:
    """Toggle a dataset index on or off in the multi-dataset graph list."""
    selected_list = state.graph_config.dataset_indices
    ds_name = state.datasets[dataset_idx].name
    if dataset_idx in selected_list:
        selected_list.remove(dataset_idx)
        state.status_message = "Removed '" + ds_name + "' from graph."
    else:
        selected_list.append(dataset_idx)
        state.status_message = "Added '" + ds_name + "' to graph."
    return graph_settings_page(state)


@route
def select_graph_axis(state: State, axis: str, field: str) -> Page:
    """Assign a Data attribute to either the X or Y axis."""
    if axis == "x":
        state.graph_config.x_field = field
    else:
        state.graph_config.y_field = field
    state.status_message = (
        "Axis mapping set: X="
        + state.graph_config.x_field
        + ", Y="
        + state.graph_config.y_field
    )
    return graph_settings_page(state)


@route
def graph_settings_page(state: State) -> Page:
    """Render buttons to pick datasets/axes and inputs for chart styling."""
    cfg = state.graph_config

    page_items: list[Component] = [
        Header("Graph Configuration"),
        build_nav_bar(),
        build_status_banner(state),
        Header("1. Toggle Datasets to Plot (Select One or More)", 3),
    ]

    for idx in range(len(state.datasets)):
        ds = state.datasets[idx]
        if idx in cfg.dataset_indices:
            prefix = "[Selected] "
        else:
            prefix = ""
        label = (
            prefix
            + ds.name
            + " ("
            + str(len(ds.datapoints))
            + " pts)"
        )
        page_items.append(
            Button(
                label,
                "select_graph_dataset",
                Argument("dataset_idx", idx),
            )
        )

    x_buttons: list[Component] = [Header("2. Choose X-Axis Data", 3)]
    for field in X_AXIS_FIELDS:
        if cfg.x_field == field:
            prefix = "[X] "
        else:
            prefix = ""
        x_buttons.append(
            Button(
                prefix + field.capitalize(),
                "select_graph_axis",
                (Argument("axis", "x"), Argument("field", field)),
            )
        )

    y_buttons: list[Component] = [Header("3. Choose Y-Axis Data", 3)]
    for field in Y_AXIS_FIELDS:
        if cfg.y_field == field:
            prefix = "[Y] "
        else:
            prefix = ""
        y_buttons.append(
            Button(
                prefix + field.capitalize(),
                "select_graph_axis",
                (Argument("axis", "y"), Argument("field", field)),
            )
        )

    page_items.append(Row(x_buttons, style_gap="8px"))
    page_items.append(Row(y_buttons, style_gap="8px"))
    page_items.append(HorizontalRule())
    page_items.append(Header("4. Chart Style & Save", 3))
    page_items.append(Paragraph("Plot Type:"))
    page_items.append(SelectBox("plot_type", PLOT_TYPES, cfg.plot_type))
    page_items.append(
        Paragraph("Custom Chart Title (leave blank for auto-title):")
    )
    page_items.append(TextBox("plot_title", cfg.plot_title))
    page_items.append(
        Row(
            CheckBox("show_legend", cfg.show_legend),
            Paragraph("Show Legend"),
        )
    )
    page_items.append(Button("Generate & Save Graph", "update_graph_settings"))

    return Page(state, page_items)


@route
def update_graph_settings(
    state: State,
    plot_type: str,
    plot_title: str,
    show_legend: bool,
) -> Page:
    """Validate dataset selection and save persistent graph configuration."""
    if len(state.graph_config.dataset_indices) == 0:
        state.status_message = (
            "Error: Please select at least one dataset before generating."
        )
        return graph_settings_page(state)

    state.graph_config.plot_type = plot_type
    state.graph_config.plot_title = plot_title
    state.graph_config.show_legend = show_legend
    state.graph_config.is_configured = True
    count = len(state.graph_config.dataset_indices)
    state.status_message = (
        "Saved graph with " + str(count) + " dataset(s)."
    )
    return view_graph_page(state)


# =====================================================================
# 7. DATA TABLE ACTION GROUP
# =====================================================================

def get_record_value(item: tuple[str, Data]) -> float:
    """Return the numeric value of a (dataset_name, Data) record for sorting."""
    return item[1].value


def get_record_date(item: tuple[str, Data]) -> str:
    """Return the date string of a (dataset_name, Data) record for sorting."""
    return item[1].date


def get_record_name(item: tuple[str, Data]) -> str:
    """Return the station name of a (dataset_name, Data) record for sorting."""
    return item[1].name


def get_sorted_rows(
    datasets: list[Dataset], sort_by: str, reverse: bool
) -> list[list[Component | str | int | float | bool]]:
    """Collect and sort rows from all visible datasets for Table display."""
    records: list[tuple[str, Data]] = []
    for ds in datasets:
        if ds.toggled:
            for pt in ds.datapoints:
                records.append((ds.name, pt))

    # Pass helper function to .sort(key=...) so Python sorts tuples by the chosen Data field
    if sort_by == "value":
        records.sort(key=get_record_value, reverse=reverse)
    elif sort_by == "date":
        records.sort(key=get_record_date, reverse=reverse)
    else:
        records.sort(key=get_record_name, reverse=reverse)

    rows: list[list[Component | str | int | float | bool]] = []
    for ds_name, pt in records:
        rows.append(
            [
                ds_name,
                pt.name,
                str(pt.value),
                pt.date,
                str(pt.latitude),
                str(pt.longitude),
            ]
        )
    return rows


def build_table_layer_toggles(datasets: list[Dataset]) -> Row:
    """Build wrapping toggle buttons for showing or hiding datasets in the table."""
    buttons: list[Component] = []
    for idx in range(len(datasets)):
        ds = datasets[idx]
        if ds.toggled:
            state_label = "ON"
        else:
            state_label = "OFF"
        buttons.append(
            Button(
                ds.name + ": " + state_label,
                "toggle_table_dataset",
                Argument("dataset_idx", idx),
            )
        )
    return Row(
        buttons,
        style_gap="8px",
        style_flex_wrap="wrap",
        style_max_width="100%",
    )


@route
def toggle_table_dataset(state: State, dataset_idx: int) -> Page:
    """Toggle dataset visibility from the Data Table page and refresh."""
    target = state.datasets[dataset_idx]
    target.toggled = not target.toggled

    visible_sets = 0
    total_rows = 0
    for ds in state.datasets:
        if ds.toggled:
            visible_sets += 1
            total_rows += len(ds.datapoints)

    if visible_sets == 0:
        state.status_message = (
            "All datasets hidden — toggle a dataset ON to view rows."
        )
    else:
        state.status_message = (
            "Showing "
            + str(visible_sets)
            + " of "
            + str(len(state.datasets))
            + " datasets ("
            + str(total_rows)
            + " rows in table)."
        )
    return data_table_page(state)


@route
def data_table_page(state: State) -> Page:
    """Render a sortable, filterable table of points in visible datasets."""
    rows = get_sorted_rows(
        state.datasets, state.table_sort_by, state.table_sort_reverse
    )
    sort_controls = Row(
        Button("Sort by Name", "sort_table", Argument("column", "name")),
        Button("Sort by Value", "sort_table", Argument("column", "value")),
        Button("Sort by Date", "sort_table", Argument("column", "date")),
        style_gap="8px",
    )
    header_row: list[Component | str | int | float | bool] = [
        "Dataset", "Station", "Value", "Date", "Latitude", "Longitude"
    ]

    if state.table_sort_reverse:
        order_label = "Desc"
    else:
        order_label = "Asc"

    if len(rows) == 0:
        table_display: Component = Paragraph(
            "No rows to display — toggle at least one dataset ON above."
        )
    else:
        table_display = Table([header_row] + rows)

    return Page(
        state,
        [
            Header("Field Data Audit Table"),
            build_nav_bar(),
            build_status_banner(state),
            Header("Dataset Layers", 3),
            build_table_layer_toggles(state.datasets),
            HorizontalRule(),
            Paragraph(
                "Sorted by: " + state.table_sort_by + " (" + order_label + ")"
            ),
            sort_controls,
            table_display,
        ],
    )


@route
def sort_table(state: State, column: str) -> Page:
    """Update table sorting column or flip ascending/descending order."""
    if state.table_sort_by == column:
        state.table_sort_reverse = not state.table_sort_reverse
    else:
        state.table_sort_by = column
        state.table_sort_reverse = False
    return data_table_page(state)


# =====================================================================
# 8. UNIT TESTS & SERVER STARTUP
# =====================================================================

assert_equal(haversine_km(39.6812, -75.7519, 39.6812, -75.7519), 0.0)
assert_equal(is_valid_coords(39.68, -75.75), True)
assert_equal(is_valid_coords(95.0, -75.75), False)

test_state = make_initial_state()
assert_equal(len(test_state.datasets), 9)
assert_equal(len(build_map_markers(test_state.datasets)), 108)

toggle_dataset(test_state, 1)
assert_equal(test_state.datasets[1].toggled, False)
assert_equal(len(build_map_markers(test_state.datasets)), 96)

save_point(
    test_state,
    "NewarkAGFarm High Temps",
    "Test Point",
    "72.5",
    "2026-11-12",
    "39.67",
    "-75.74",
)
assert_equal(len(test_state.datasets[0].datapoints), 13)

sort_table(test_state, "value")
assert_equal(test_state.table_sort_by, "value")
assert_equal(test_state.table_sort_reverse, False)

toggle_table_dataset(test_state, 0)
assert_equal(test_state.datasets[0].toggled, False)
assert_equal(len(get_sorted_rows(test_state.datasets, "name", False)), 84)
toggle_table_dataset(test_state, 0)
assert_equal(test_state.datasets[0].toggled, True)

test_state.selected = SelectedPoint(0, 0)
return_to_map(test_state)
assert_equal(
    "Active anchor: Jan (NewarkAGFarm High Temps)"
    in test_state.status_message,
    True,
)

clear_selection(test_state)
assert_equal(test_state.selected, None)
assert_equal(test_state.last_distance, None)

assert_equal(test_state.graph_config.is_configured, False)
select_graph_dataset(test_state, 0)
select_graph_dataset(test_state, 1)
assert_equal(test_state.graph_config.dataset_indices, [0, 1])

select_graph_dataset(test_state, 1)
assert_equal(test_state.graph_config.dataset_indices, [0])
select_graph_dataset(test_state, 1)
assert_equal(test_state.graph_config.dataset_indices, [0, 1])

select_graph_axis(test_state, "x", "date")
select_graph_axis(test_state, "y", "value")
assert_equal(test_state.graph_config.x_field, "date")
assert_equal(test_state.graph_config.y_field, "value")

update_graph_settings(test_state, "scatter", "New Title", False)
assert_equal(test_state.graph_config.plot_type, "scatter")
assert_equal(test_state.graph_config.show_legend, False)
assert_equal(test_state.graph_config.is_configured, True)

sample_csv = (
    "Month,MAX TEMP,MIN TEMP,AVG TEMP,PRECIP\n"
    "Jan,42.5,25.1,33.8,3.43\n"
    "Feb,45.6,25.4,35.5,2.91\n"
)
parsed_csv_ds = parse_text_to_dataset(
    sample_csv, "CSV Test", 0, 4, DEFAULT_LAT, DEFAULT_LON
)
assert_equal(len(parsed_csv_ds.datapoints), 2)
assert_equal(parsed_csv_ds.datapoints[0].date, "Jan")
assert_equal(parsed_csv_ds.datapoints[0].value, 3.43)

sample_compact = "Jan42.525.133.83.43\nFeb45.625.435.52.91\n"
parsed_compact_ds = parse_text_to_dataset(
    sample_compact, "Compact Test", 0, 1, DEFAULT_LAT, DEFAULT_LON
)
assert_equal(len(parsed_compact_ds.datapoints), 2)
assert_equal(parsed_compact_ds.datapoints[0].date, "Jan")
assert_equal(parsed_compact_ds.datapoints[0].value, 42.5)

# Route tests verifying state updates
index(test_state)
assert_equal(len(test_state.datasets), 9)

test_state.selected = None
handle_map_click(test_state, 39.6900, -75.7500)
assert_equal(test_state.last_distance, None)
assert_equal(
    "Click a station marker first" in test_state.status_message, True
)

save_point(
    test_state,
    "NewarkAGFarm High Temps",
    "Unique Station",
    "70.0",
    "2026-11-13",
    "39.6850",
    "-75.7550",
)
inspect_marker(
    test_state, AG_FARM_LAT, AG_FARM_LON, "Jan (NewarkAGFarm High Temps)"
)
assert_equal(test_state.selected, SelectedPoint(0, 0))
assert_equal("Found " in test_state.status_message, True)

inspect_marker(test_state, 39.6850, -75.7550, "Unique Station")
assert_equal(
    "Inspecting 'Unique Station'" in test_state.status_message, True
)
point_detail_page(test_state)

handle_map_click(test_state, 39.6900, -75.7500)
assert test_state.last_distance is not None
assert_equal(test_state.last_distance.start, "Unique Station")
assert_equal(test_state.last_distance.distance > 0, True)

add_point_page(test_state)
save_point(
    test_state,
    "NewarkAGFarm High Temps",
    "Bad Coords",
    "15.0",
    "2026-11-12",
    "999.0",
    "-75.75",
)
assert_equal(
    "Coordinates out of valid GPS bounds" in test_state.status_message,
    True,
)

upload_file_page(test_state)
process_uploaded_file(
    test_state, "Empty Upload", "1", "2", "39.68", "-75.75", ""
)
assert_equal(
    "Please select a .csv or .txt file" in test_state.status_message,
    True,
)

csv_text = "Month,MAX,MIN,AVG,PRECIP\nMar,54.2,32.8,43.5,4.27\n"
count_before = len(test_state.datasets)
process_uploaded_file(
    test_state,
    "March Climate",
    "1",
    "5",
    "39.68",
    "-75.75",
    csv_text,
)
assert_equal(len(test_state.datasets), count_before + 1)
assert_equal(test_state.datasets[-1].name, "March Climate")
assert_equal(test_state.datasets[-1].datapoints[0].value, 4.27)

assert_equal(test_state.datasets[0].toggled, False)
assert_equal(test_state.datasets[-1].toggled, True)
assert_equal(len(get_sorted_rows(test_state.datasets, "name", False)), 1)

graph_settings_page(test_state)
view_graph_page(test_state)
data_table_page(test_state)

remove_datasets_page(test_state)
before_delete_count = len(test_state.datasets)
select_dataset_to_remove(test_state, 0)
assert_equal(test_state.pending_delete_index, 0)

cancel_remove_dataset(test_state)
assert_equal(test_state.pending_delete_index, None)
assert_equal(len(test_state.datasets), before_delete_count)

select_dataset_to_remove(test_state, 0)
confirm_remove_dataset(test_state)
assert_equal(test_state.pending_delete_index, None)
assert_equal(len(test_state.datasets), before_delete_count - 1)


start_server(make_initial_state())

