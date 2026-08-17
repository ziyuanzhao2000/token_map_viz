
Installation instruction

1. Install necessary packages first with `uv sync`.

2. To visualize the WSI and token maps with napari, run the script:
```
uv run python visualize_token_map.py --wsi_path PATH_TO_YOUR_WSI  --label_path PATH_TO_YOUR_LABEL
```