import argparse
import os
import numpy as np
from napari.utils import DirectLabelColormap
from qtpy.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget
import wsidata
import ezslide
from ezslide import pyramid_options

# Force napari to load chunks on a background worker thread
os.environ["NAPARI_ASYNC"] = "1"
os.environ["NAPARI_OCTREE"] = "1"
import napari


COLORS = [
    (1.0, 1.0, 1.0, 1.0),
    (1.0, 1.0, 1.0, 1.0),
    (0.0, 0.5, 1.0, 1.0),
    (1.0, 0.5, 0.0, 1.0),
    (0.5, 0.75, 0.5, 1.0),
    (0.369, 0.026, 0.646, 1.0),
    (0.916, 0.005, 0.222, 1.0),
    (0.828, 0.998, 0.036, 1.0),
    (0.0, 1.0, 1.0, 1.0),
    (0.759, 0.468, 0.972, 1.0),
    (0.015, 0.44, 0.293, 1.0),
    (0.505, 0.261, 0.032, 1.0),
    (0.0, 1.0, 0.5, 1.0),
    (0.0, 0.0, 1.0, 1.0),
    (0.983, 0.737, 0.46, 1.0),
    (0.543, 0.91, 0.995, 1.0),
    (0.796, 0.377, 0.46, 1.0),
    (0.356, 0.666, 0.017, 1.0),
    (0.0, 0.0, 0.0, 1.0),
    (0.5, 0.0, 0.5, 1.0),
    (1.0, 0.75, 0.8, 1.0),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Visualize a WSI with a token map overlay in napari."
    )
    parser.add_argument("--wsi_path", help="Path to the whole-slide image")
    parser.add_argument("--label_path", help="Path to the label/token map")
    parser.add_argument(
        "--annots_path",
        default=None,
        help="Optional path to save an Annotations shapes layer (black edges, "
        "transparent fill) as a geopandas-readable file (e.g. GeoJSON) when the "
        "napari window is closed.",
    )
    return parser.parse_args()


def build_colormap():
    napari_colormap = {i: list(color) for i, color in enumerate(COLORS)}
    return DirectLabelColormap(color_dict=napari_colormap)


def geodataframe_from_shapes(shapes_data, names=None):
    """Convert napari shapes layer data ((row, col) arrays) into a GeoDataFrame of polygons."""
    from shapely.geometry import Polygon
    import geopandas as gpd

    polygons = []
    for shape in shapes_data:
        # napari stores vertices as (row, col) = (y, x); shapely expects (x, y)
        xy = [(x, y) for y, x in shape]
        if len(xy) >= 3:
            polygons.append(Polygon(xy))
    data = {"name": list(names)} if names is not None else {}
    return gpd.GeoDataFrame(data, geometry=polygons)


def get_names(layer):
    return list(layer.properties.get("name", []))


def set_names(layer, names):
    """Write names back to the layer and refresh the on-canvas text."""
    layer.properties = {"name": np.array(list(names), dtype=object)}
    layer.refresh_text()


def make_annotations_layer(viewer, scale):
    layer = viewer.add_shapes(
        shape_type="polygon",
        name="Annotations",
        edge_color="black",
        edge_width=50,
        face_color="transparent",
        scale=scale,
        properties={"name": np.empty(0, dtype=object)},
        text={"string": "{name}", "size": 10, 
              "color": "black", "anchor": "center",
              'scaling': False},
    )

    # napari grows the feature table itself when a shape is drawn, filling the new
    # row with the last used name, so track the count to tell which shapes are new.
    seen = {"count": 0}

    def _on_data_change(event=None):
        n_shapes = len(layer.data)
        if n_shapes > seen["count"]:
            names = (get_names(layer) + [None] * n_shapes)[:n_shapes]
            for i in range(seen["count"], n_shapes):
                names[i] = f"Annotation {i + 1}"
            set_names(layer, names)
        seen["count"] = n_shapes

    layer.events.data.connect(_on_data_change)
    return layer


class AnnotationEditor(QWidget):
    """Dock widget to rename the currently selected annotation in real time."""

    PROMPT = "Click a single annotation to rename it"

    def __init__(self, layer):
        super().__init__()
        self.layer = layer

        self.label = QLabel(self.PROMPT)
        self.line_edit = QLineEdit()
        self.line_edit.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        layout.addStretch()
        self.setLayout(layout)

        self.line_edit.textChanged.connect(self._on_text_changed)
        # Selection lives on a psygnal Selection object, not on layer.events.
        layer.selected_data.events.items_changed.connect(self._on_selection_changed)

    def _selected_index(self):
        selected = list(self.layer.selected_data)
        if len(selected) != 1 or selected[0] >= len(self.layer.data):
            return None
        return selected[0]

    def _on_selection_changed(self, *_):
        index = self._selected_index()
        names = get_names(self.layer)
        self.line_edit.blockSignals(True)
        if index is None:
            self.label.setText(self.PROMPT)
            self.line_edit.setText("")
            self.line_edit.setEnabled(False)
        else:
            self.label.setText(f"Renaming annotation #{index + 1}")
            self.line_edit.setText(str(names[index]) if index < len(names) else "")
            self.line_edit.setEnabled(True)
        self.line_edit.blockSignals(False)

    def _on_text_changed(self, text):
        index = self._selected_index()
        names = get_names(self.layer)
        if index is None or index >= len(names):
            return
        names[index] = text
        set_names(self.layer, names)


def main():
    args = parse_args()

    if not os.path.exists(args.wsi_path):
        print(f"WSI path does not exist: {args.wsi_path}")
        return
    if not os.path.exists(args.label_path):
        print(f"Label path does not exist: {args.label_path}")
        return

    napari_colormap = build_colormap()

    wsi_pyramid_ = wsidata.open_wsi(args.wsi_path, reader="tifffile_zarr").reader[0].data
    wsi_pyramid = [np.transpose(arr, (1, 0, 2)) for arr in wsi_pyramid_]
    
    with pyramid_options(how="mode"):
        label = wsidata.open_wsi(args.label_path, reader="tifffile_zarr_pyramid").reader[0].data

    viewer = napari.Viewer()

    viewer.add_image(
        wsi_pyramid,
        name="WSI",
        multiscale=True,
        blending="translucent",
    )
    H, W, _ = wsi_pyramid[0].shape
    H2, W2 = label[0].shape
    scale = (H / H2, W / W2)

    labels_layer = viewer.add_labels(
        label,
        name="Token map",
        multiscale=True,
        opacity=0.6,
        scale=scale,
    )
    labels_layer.colormap = napari_colormap

    annotations_layer = None
    if args.annots_path is not None:
        annotations_layer = make_annotations_layer(viewer, scale)
        viewer.window.add_dock_widget(
            AnnotationEditor(annotations_layer), name="Annotation editor"
        )

    napari.run()

    if annotations_layer is not None:
        gdf = geodataframe_from_shapes(
            annotations_layer.data, get_names(annotations_layer)
        )
        gdf.to_file(args.annots_path, driver="GeoJSON")
        print(f"Saved {len(gdf)} annotation(s) to {args.annots_path}")


if __name__ == "__main__":
    main()
