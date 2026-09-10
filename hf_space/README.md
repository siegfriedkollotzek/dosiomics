---
title: MFI Cell Analysis
emoji: 🔬
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.26.0
app_file: app.py
pinned: false
---

# MFI Cell Analysis

Upload an RGB TIF microscopy image with a scale bar. The app segments the largest cell,
computes the mean fluorescence intensity (MFI) per channel, reads the scale bar length
with EasyOCR (models shipped in `easyocr_models/`, no downloads at runtime) and returns
an Excel report with the numbers and the intermediate images.

## Deploy

The EasyOCR models are not tracked in the GitHub repo inside this folder – copy them first:

```powershell
Copy-Item ..\mfi\easyocr_models\*.pth .\easyocr_models\
```

Then upload the folder to the Space (needs `hf auth login` once):

```powershell
hf upload <hf-user>/mfi-cell-analysis . . --repo-type space
```

Run locally: `python app.py` → http://localhost:7860
