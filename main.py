from dataclasses import dataclass
import math
import matplotlib.pyplot as plt
from drafter import *
from bakery import assert_equal


# =====================================================================
# 1. SITE CONFIGURATION & CONSTANTS
# =====================================================================

hide_debug_information()
set_website_title("Geospatial Field & Analytics Explorer")
set_website_framed(False)

add_website_css("h1", "font-size: 1rem; margin-bottom: 0.4rem;")
add_website_css("h3", "font-size: 0.75rem; margin-bottom: 0.25rem;")
set_site_information(
    "Evan Miller",
    "Interactive geospatial data mapping, distance analysis, and plotting.",
    "OpenStreetMap via Drafter; sample Newark field datasets.",
    "See planning.pdf in the GitHub repository.",
    ["https://github.com/your-username/your-repo-name"],
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
AG_FARM_LAT: float = 39.6695
AG_FARM_LON: float = -75.7441

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
    dataset_index: int | None
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


# =====================================================================
# 3. SHARED NAVIGATION & INITIAL STATE HELPERS
# =====================================================================


def build_nav_bar() -> Row:
    """Create the top navigation bar shared across all pages."""
    return Row(
        Link("Map Explorer", "index"),
        Link("Add Data Point", "add_point_page"),
        Link("Import File", "upload_file_page"),
        Link("View Graph", "view_graph_page"),
        Link("Graph Settings", "graph_settings_page"),
        Link("Data Table", "data_table_page"),
        style_gap="12px",
    )


def build_status_banner(state: State) -> Paragraph:
    """Render the current status message consistently across pages."""
    return Paragraph(f"Status: {state.status_message}")


def make_initial_state() -> State:
    """Build initial State with the four Newark AG Farm climate datasets."""
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
    ]
    for ds in datasets:
        ds.notes = "Newark AG Farm monthly climate normals"

    default_graph = GraphConfig(
        dataset_index=None,
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
        status_message="Welcome! Click a map marker or explore the tools.",
        last_distance=None,
        table_sort_by="name",
        table_sort_reverse=False,
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


def build_layer_toggles(datasets: list[Dataset]) -> list[PageContent]:
    """Build toggle buttons for showing or hiding each dataset layer."""
    controls: list[PageContent] = [Header("Dataset Layers", 3)]
    for idx, ds in enumerate(datasets):
        state_label = "ON" if ds.toggled else "OFF"
        btn_text = f"{ds.name}: {state_label}"
        controls.append(
            Button(btn_text, "toggle_dataset", Argument("dataset_idx", idx))
        )
    return controls


def build_side_panel(state: State) -> Div:
    """Build the right-hand panel containing title, nav, status, and toggles."""
    distance_box: list[PageContent] = []
    if state.last_distance is not None:
        dq = state.last_distance
        distance_box.append(
            Paragraph(
                f"Distance from {dq.start} to {dq.end}: {dq.distance} km"
            )
        )

    panel_items: list[PageContent] = [
        Header("Geospatial Field Explorer"),
        build_nav_bar(),
        HorizontalRule(),
        Paragraph(f"Status: {state.status_message}"),
        *distance_box,
        *build_layer_toggles(state.datasets),
    ]
    return Div(
        *panel_items,
        style_width="50%",
        style_padding="16px",
        style_box_sizing="border-box",
    )


@route
def index(state: State) -> Page:
    """Render the main Map Explorer with a 50/50 split layout."""
    markers = build_map_markers(state.datasets)
    map_view = Map(
        "field_map",
        markers=markers,
        center=(39.6812, -75.7519),
        zoom=13,
        on_marker_click="inspect_marker",
        on_click="handle_map_click",
        style_width="100%",
        style_height="85vh",
    )
    left_column = Div(
        map_view,
        style_width="50%",
        style_padding="8px",
        style_box_sizing="border-box",
    )
    right_column = build_side_panel(state)

    return Page(
        state,
        [
            Row(
                left_column,
                right_column,
                style_align_items="flex-start",
                style_width="100%",
            )
        ],
    )


@route
def toggle_dataset(state: State, dataset_idx: int) -> Page:
    """Toggle visibility on or off and report live visible counts."""
    target = state.datasets[dataset_idx]
    target.toggled = not target.toggled
    visible_sets = sum(1 for ds in state.datasets if ds.toggled)
    visible_pts = len(build_map_markers(state.datasets))
    if visible_sets == 0:
        state.status_message = (
            "All datasets hidden — toggle a layer ON to view markers."
        )
    else:
        state.status_message = (
            f"Showing {visible_sets} of {len(state.datasets)} datasets "
            f"({visible_pts} markers on map)."
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
    state: State, latitude: float, longitude: float
) -> Page:
    """Compute distance from the selected point to a clicked map spot."""
    if state.selected is None:
        state.status_message = (
            "Click a station marker first to measure distance from it."
        )
        return index(state)
    ds = state.datasets[state.selected.dataset_index]
    pt = ds.datapoints[state.selected.data_index]
    dist_km = haversine_km(pt.latitude, pt.longitude, latitude, longitude)
    end_label = f"Click ({round(latitude, 4)}, {round(longitude, 4)})"
    state.last_distance = DistanceQuery(pt.name, end_label, dist_km)
    state.status_message = f"Measured {dist_km} km from {pt.name}."
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
    """Locate clicked marker in state and render its detail page."""
    for d_idx, ds in enumerate(state.datasets):
        for p_idx, pt in enumerate(ds.datapoints):
            if pt.name == label:
                state.selected = SelectedPoint(d_idx, p_idx)
                state.status_message = (
    f"Inspecting '{pt.name}' ({pt.value}) — "
    "return to Map Explorer to measure distances from it."
)
                return point_detail_page(state)
    state.status_message = "Marker record could not be located."
    return index(state)


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
            Header(f"Station: {pt.name}"),
            build_nav_bar(),
            details,
            Paragraph("Click anywhere on the Map Explorer to measure from here."),
            Button("Return to Map", "index"),
        ],
    )


@route
def return_to_map(state: State) -> Page:
    """Return to the map dashboard with an updated anchor prompt."""
    if state.selected is not None:
        ds = state.datasets[state.selected.dataset_index]
        pt = ds.datapoints[state.selected.data_index]
        state.status_message = (
            f"Active anchor: {pt.name} ({pt.value}). "
            "Click map to measure distance."
        )
    else:
        state.status_message = "Map Explorer ready."
    return index(state)


@route
def add_point_page(state: State) -> Page:
    """Render the form to manually add a new Data point."""
    ds_names = [ds.name for ds in state.datasets]
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
            state.status_message = f"Saved '{new_pt.name}' to {ds.name}."
            return index(state)

    state.status_message = "Error: Target dataset not found."
    return index(state)


def parse_compact_row(line: str) -> tuple[str, list[float]]:
    """Parse a compact string without commas (e.g. 'Jan42.525.133.83.43')."""
    label = line[:3] if len(line) >= 3 else "Row"
    remainder = line[3:] if label in MONTH_NAMES else line
    nums: list[float] = []
    idx = 0
    while idx < len(remainder):
        dot_pos = remainder.find(".", idx)
        if dot_pos == -1:
            break
        decimals = 2 if remainder.find(".", dot_pos + 1) == -1 else 1
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

    date_val = (
        parts[date_col]
        if 0 <= date_col < len(parts) and parts[date_col]
        else "Unknown"
    )
    label_val = parts[0] if parts[0] else date_val
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
    for raw_line in raw_text.strip().splitlines():
        clean_line = raw_line.strip()
        if not clean_line:
            continue

        if "," in clean_line:
            parts = [token.strip() for token in clean_line.split(",")]
            pt = parse_csv_row(parts, date_col, value_col)
            if pt is not None:
                pt.name = f"{pt.name} ({dataset_name})"
                pt.latitude = lat
                pt.longitude = lon
                points.append(pt)
        else:
            label, nums = parse_compact_row(clean_line)
            if len(nums) > 0:
                # Compact format has Month at col 0 and numeric values starting at 1
                num_idx = max(0, value_col - 1)
                if num_idx >= len(nums):
                    num_idx = 0
                points.append(
                    Data(
                        name=f"{label} ({dataset_name})",
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
    column_options = [
        "Col 1",
        "Col 2",
        "Col 3",
        "Col 4",
        "Col 5",
    ]

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
            Paragraph("Which column should be assigned to Date:"),
            SelectBox("date_choice", column_options, column_options[0]),
            Paragraph("Which numeric column should be assigned to Value:"),
            SelectBox("metric_choice", column_options, column_options[1]),
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
    uploaded_file: bytes,
) -> Page:
    """Decode uploaded file bytes, parse into Data instances, and save."""
    try:
        num_lat = float(lat)
        num_lon = float(lon)
    except ValueError:
        state.status_message = "Error: Latitude and longitude must be numbers."
        return upload_file_page(state)

    if not is_valid_coords(num_lat, num_lon):
        state.status_message = "Error: Coordinates out of valid GPS bounds."
        return upload_file_page(state)

    if not uploaded_file:
        state.status_message = "Error: Please select a .csv or .txt file first."
        return upload_file_page(state)

    raw_text = (
        uploaded_file.decode("utf-8", errors="ignore")
        if isinstance(uploaded_file, bytes)
        else str(uploaded_file)
    )
    date_col = int(date_choice.replace("Col ", "")) - 1
    value_col = int(metric_choice.replace("Col ", "")) - 1
    clean_title = dataset_name.strip() or "Imported Dataset"
    new_ds = parse_text_to_dataset(
        raw_text, clean_title, date_col, value_col, num_lat, num_lon
    )

    if len(new_ds.datapoints) == 0:
        state.status_message = "Error: No valid numeric rows found in file."
        return upload_file_page(state)

    state.datasets.append(new_ds)
    state.status_message = (
        f"Imported '{new_ds.name}' with {len(new_ds.datapoints)} records."
    )
    return data_table_page(state)


# =====================================================================
# 6. GRAPH & ANALYTICS ACTION GROUP
# =====================================================================


def extract_axis_values(datapoints: list[Data], field: str) -> list:
    """Extract a list of values for a specific Data attribute."""
    if field == "value":
        return [pt.value for pt in datapoints]
    if field == "date":
        return [pt.date for pt in datapoints]
    if field == "latitude":
        return [pt.latitude for pt in datapoints]
    if field == "longitude":
        return [pt.longitude for pt in datapoints]
    if field == "name":
        return [pt.name for pt in datapoints]
    return list(range(len(datapoints)))


def build_analytics_figure(
    config: GraphConfig, datasets: list[Dataset]
) -> plt.Figure:
    """Generate a Matplotlib figure for the single configured Dataset."""
    plt.close("all")
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    ds = datasets[config.dataset_index]
    x_vals = extract_axis_values(ds.datapoints, config.x_field)
    y_vals = extract_axis_values(ds.datapoints, config.y_field)

    if config.plot_type == "scatter":
        ax.scatter(x_vals, y_vals, label=ds.name)
    elif config.plot_type == "histogram":
        ax.hist(y_vals, bins=5, alpha=0.7, label=ds.name)
    else:
        ax.plot(x_vals, y_vals, marker="o", label=ds.name)

    default_title = f"{ds.name}: {config.y_field} vs {config.x_field}"
    title = config.plot_title if config.plot_title else default_title
    x_label = (
        "Value Bins"
        if config.plot_type == "histogram"
        else config.x_field.capitalize()
    )
    y_label = (
        "Frequency"
        if config.plot_type == "histogram"
        else config.y_field.capitalize()
    )
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, linestyle="--", alpha=0.4)
    if config.show_legend:
        ax.legend()
    return fig


def build_dataset_summary(ds: Dataset, y_field: str) -> Table:
    """Build a summary stats table for the plotted numeric attribute."""
    vals = extract_axis_values(ds.datapoints, y_field)
    if len(vals) == 0:
        return Table([["Dataset", "Count"], [ds.name, "0"]])
    mean_val = round(sum(vals) / len(vals), 2)
    return Table(
        [
            ["Dataset", "Metric", "Count", "Min", "Max", "Mean"],
            [
                ds.name,
                y_field,
                str(len(vals)),
                str(min(vals)),
                str(max(vals)),
                str(mean_val),
            ],
        ]
    )


@route
def view_graph_page(state: State) -> Page:
    """Render the saved graph, or prompt the user to configure one first."""
    cfg = state.graph_config
    if not cfg.is_configured or cfg.dataset_index is None:
        return Page(
            state,
            [
                Header("Data Visualization"),
                build_nav_bar(),
                build_status_banner(state),
                Paragraph(
                    "No graph is currently loaded. Select a dataset and choose "
                    "which data attributes to plot on the X and Y axes."
                ),
                Button("Configure Graph & Select Dataset", "graph_settings_page"),
            ],
        )

    ds = state.datasets[cfg.dataset_index]
    build_analytics_figure(cfg, state.datasets)
    plot_component = MatPlotLibPlot()

    return Page(
        state,
        [
            Header("Data Visualization"),
            build_nav_bar(),
            build_status_banner(state),
            plot_component,
            build_dataset_summary(ds, cfg.y_field),
            Button("Edit Graph Settings", "graph_settings_page"),
        ],
    )


@route
def select_graph_dataset(state: State, dataset_idx: int) -> Page:
    """Set the single dataset index to be plotted."""
    state.graph_config.dataset_index = dataset_idx
    state.status_message = f"Selected dataset: {state.datasets[dataset_idx].name}"
    return graph_settings_page(state)


@route
def select_graph_axis(state: State, axis: str, field: str) -> Page:
    """Assign a Data attribute to either the X or Y axis."""
    if axis == "x":
        state.graph_config.x_field = field
    else:
        state.graph_config.y_field = field
    state.status_message = (
        f"Axis mapping set: X={state.graph_config.x_field}, "
        f"Y={state.graph_config.y_field}"
    )
    return graph_settings_page(state)


@route
def graph_settings_page(state: State) -> Page:
    """Render buttons to pick dataset/axes and inputs for chart styling."""
    cfg = state.graph_config

    dataset_buttons: list[PageContent] = [Header("1. Choose Dataset (Single)", 3)]
    for idx, ds in enumerate(state.datasets):
        prefix = "[Selected] " if cfg.dataset_index == idx else ""
        dataset_buttons.append(
            Button(
                f"{prefix}{ds.name} ({len(ds.datapoints)} pts)",
                "select_graph_dataset",
                Argument("dataset_idx", idx),
            )
        )

    x_buttons: list[PageContent] = [Header("2. Choose X-Axis Data", 3)]
    for field in X_AXIS_FIELDS:
        prefix = "[X] " if cfg.x_field == field else ""
        x_buttons.append(
            Button(
                f"{prefix}{field.capitalize()}",
                "select_graph_axis",
                [Argument("axis", "x"), Argument("field", field)],
            )
        )

    y_buttons: list[PageContent] = [Header("3. Choose Y-Axis Data", 3)]
    for field in Y_AXIS_FIELDS:
        prefix = "[Y] " if cfg.y_field == field else ""
        y_buttons.append(
            Button(
                f"{prefix}{field.capitalize()}",
                "select_graph_axis",
                [Argument("axis", "y"), Argument("field", field)],
            )
        )

    return Page(
        state,
        [
            Header("Graph Configuration"),
            build_nav_bar(),
            build_status_banner(state),
            *dataset_buttons,
            Row(*x_buttons, style_gap="8px"),
            Row(*y_buttons, style_gap="8px"),
            HorizontalRule(),
            Header("4. Chart Style & Save", 3),
            Paragraph("Plot Type:"),
            SelectBox("plot_type", PLOT_TYPES, cfg.plot_type),
            Paragraph("Custom Chart Title (leave blank for auto-title):"),
            TextBox("plot_title", cfg.plot_title),
            Row(
                CheckBox("show_legend", cfg.show_legend),
                Paragraph("Show Legend"),
            ),
            Button("Generate & Save Graph", "update_graph_settings"),
        ],
    )


@route
def update_graph_settings(
    state: State,
    plot_type: str,
    plot_title: str,
    show_legend: bool,
) -> Page:
    """Validate dataset selection and save persistent graph configuration."""
    if state.graph_config.dataset_index is None:
        state.status_message = (
            "Error: Please select a dataset before generating the graph."
        )
        return graph_settings_page(state)

    state.graph_config.plot_type = plot_type
    state.graph_config.plot_title = plot_title
    state.graph_config.show_legend = show_legend
    state.graph_config.is_configured = True
    ds_name = state.datasets[state.graph_config.dataset_index].name
    state.status_message = f"Saved graph for '{ds_name}'."
    return view_graph_page(state)


# =====================================================================
# 7. DATA TABLE ACTION GROUP
# =====================================================================

def get_sorted_rows(
    datasets: list[Dataset], sort_by: str, reverse: bool
) -> list[list[str]]:
    """Collect and sort rows from all visible datasets for Table display."""
    records: list[tuple[str, Data]] = []
    for ds in datasets:
        if ds.toggled:
            for pt in ds.datapoints:
                records.append((ds.name, pt))

    if sort_by == "value":
        records.sort(key=lambda item: item[1].value, reverse=reverse)
    elif sort_by == "date":
        records.sort(key=lambda item: item[1].date, reverse=reverse)
    else:
        records.sort(key=lambda item: item[1].name, reverse=reverse)

    rows: list[list[str]] = []
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
    """Build inline toggle buttons for showing or hiding datasets in the table."""
    buttons: list[PageContent] = []
    for idx, ds in enumerate(datasets):
        state_label = "ON" if ds.toggled else "OFF"
        buttons.append(
            Button(
                f"{ds.name}: {state_label}",
                "toggle_table_dataset",
                Argument("dataset_idx", idx),
            )
        )
    return Row(*buttons, style_gap="8px")


@route
def toggle_table_dataset(state: State, dataset_idx: int) -> Page:
    """Toggle dataset visibility from the Data Table page and refresh."""
    target = state.datasets[dataset_idx]
    target.toggled = not target.toggled
    visible_sets = sum(1 for ds in state.datasets if ds.toggled)
    total_rows = sum(
        len(ds.datapoints) for ds in state.datasets if ds.toggled
    )
    if visible_sets == 0:
        state.status_message = (
            "All datasets hidden — toggle a dataset ON to view rows."
        )
    else:
        state.status_message = (
            f"Showing {visible_sets} of {len(state.datasets)} datasets "
            f"({total_rows} rows in table)."
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
    header_row = ["Dataset", "Station", "Value", "Date", "Latitude", "Longitude"]

    table_display: PageContent
    if len(rows) == 0:
        table_display = Paragraph(
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
                f"Sorted by: {state.table_sort_by} "
                f"({'Desc' if state.table_sort_reverse else 'Asc'})"
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
assert_equal(len(test_state.datasets), 4)
assert_equal(len(build_map_markers(test_state.datasets)), 48)

toggle_dataset(test_state, 1)
assert_equal(test_state.datasets[1].toggled, False)
assert_equal(len(build_map_markers(test_state.datasets)), 36)

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
assert_equal(len(get_sorted_rows(test_state.datasets, "name", False)), 24)
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
assert_equal(test_state.graph_config.dataset_index, 0)

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

# --- Additional Route Coverage Tests ---

# 1. Test index route renders a Page
index_page = index(test_state)
assert_equal(isinstance(index_page, Page), True)

# 2. Test handle_map_click when no point is selected
test_state.selected = None
handle_map_click(test_state, 39.6900, -75.7500)
assert_equal(test_state.last_distance, None)
assert_equal(
    "Click a station marker first" in test_state.status_message, True
)

# 3. Test inspect_marker & point_detail_page
detail_pg = inspect_marker(
    test_state, AG_FARM_LAT, AG_FARM_LON, "Jan (NewarkAGFarm High Temps)"
)
assert_equal(isinstance(detail_pg, Page), True)
assert_equal(test_state.selected, SelectedPoint(0, 0))
assert_equal(isinstance(point_detail_page(test_state), Page), True)

# 4. Test handle_map_click with an active selected anchor
handle_map_click(test_state, 39.6900, -75.7500)
assert_equal(test_state.last_distance is not None, True)
assert_equal(test_state.last_distance.start, "Jan (NewarkAGFarm High Temps)")
assert_equal(test_state.last_distance.distance > 0, True)

# 5. Test add_point_page and save_point validation error branch
assert_equal(isinstance(add_point_page(test_state), Page), True)
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

# 6. Test upload_file_page & process_uploaded_file (valid + empty file)
assert_equal(isinstance(upload_file_page(test_state), Page), True)
process_uploaded_file(
    test_state, "Empty Upload", "Col 1", "Col 2", "39.68", "-75.75", b""
)
assert_equal(
    "Please select a .csv or .txt file" in test_state.status_message,
    True,
)

csv_bytes = b"Month,MAX,MIN,AVG,PRECIP\nMar,54.2,32.8,43.5,4.27\n"
count_before = len(test_state.datasets)
process_uploaded_file(
    test_state,
    "March Climate",
    "Col 1",
    "Col 5",
    "39.68",
    "-75.75",
    csv_bytes,
)
assert_equal(len(test_state.datasets), count_before + 1)
assert_equal(test_state.datasets[-1].name, "March Climate")
assert_equal(test_state.datasets[-1].datapoints[0].value, 4.27)

# 7. Test view_graph_page, graph_settings_page, and data_table_page
assert_equal(isinstance(graph_settings_page(test_state), Page), True)
assert_equal(isinstance(view_graph_page(test_state), Page), True)
assert_equal(isinstance(data_table_page(test_state), Page), True)

start_server(make_initial_state())


start_server(make_initial_state())
