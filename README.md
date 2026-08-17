
#### Installation instruction

1. Make sure you have installed `uv` on your system first. Please see this [page](https://docs.astral.sh/uv/getting-started/installation/) for instructions on different systems. 

2. Clone the repository and then install necessary packages:
```
git clone https://github.com/ziyuanzhao2000/token_map_viz.git
cd token_map_viz
uv sync
```

3. To visualize the WSI and token maps with napari, run the script:
```
uv run python visualize_token_map.py --wsi_path PATH_TO_YOUR_WSI  --label_path PATH_TO_YOUR_LABEL
```

Note you may have to wait for ~10 seconds the first time running the script but should be faster later.

Napari display should look like ![this](demo_screenshot.png)