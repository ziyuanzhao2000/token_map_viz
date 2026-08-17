
Installation instruction

0. Make sure you installed `uv` on your system first. Please see this [page](https://docs.astral.sh/uv/getting-started/installation/) for instructions.

1. Install necessary packages first with `uv sync`.

2. To visualize the WSI and token maps with napari, run the script:
```
uv run python visualize_token_map.py --wsi_path PATH_TO_YOUR_WSI  --label_path PATH_TO_YOUR_LABEL
```

Note you may have to wait for ~10 seconds the first time running the script but should be faster later.

Napari display should look like ![this](demo_screenshot.png)