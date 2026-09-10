import shutil
import tempfile
import time
from pathlib import Path

import gradio as gr
from PIL import Image

from analysis import run_analysis

WORK_ROOT = Path(tempfile.gettempdir()) / "mfi_runs"
WORK_ROOT.mkdir(exist_ok=True)
KEEP_SECONDS = 60 * 60  # outputs are removed one hour after the run


def cleanup_old_runs():
    now = time.time()
    for d in WORK_ROOT.iterdir():
        try:
            if d.is_dir() and now - d.stat().st_mtime > KEEP_SECONDS:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def analyze(upload):
    if upload is None:
        raise gr.Error("Bitte zuerst ein TIF-Bild auswählen.")

    cleanup_old_runs()
    run_dir = Path(tempfile.mkdtemp(dir=WORK_ROOT))
    src = Path(upload)
    dst = run_dir / src.name
    shutil.copy(src, dst)

    try:
        report_path, results, mask_path = run_analysis(dst)
    except Exception as e:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise gr.Error(f"Analyse fehlgeschlagen: {e}")

    table = [[k, f"{v:.4f}" if isinstance(v, float) else str(v)]
             for k, v in results.items() if k not in ("ocr_raw", "ocr_ok")]

    if results["ocr_ok"]:
        status = f"✅ Maßstab per OCR erkannt: **{results['scale_bar_length_um']} µm** (gelesen: „{results['ocr_raw']}“)"
    else:
        status = (f"⚠️ OCR konnte den Maßstab nicht lesen (gelesen: „{results['ocr_raw']}“) – "
                  f"Standardwert **{results['scale_bar_length_um']} µm** verwendet. "
                  f"Bitte die µm-Werte im Report prüfen.")

    mask_preview = Image.open(mask_path).convert("L")
    return report_path, status, table, mask_preview


with gr.Blocks(title="MFI Cell Analysis") as demo:
    gr.Markdown(
        "# MFI Cell Analysis\n"
        "TIF-Bild (RGB, mit Maßstabsbalken) hochladen → größte Zelle wird segmentiert, "
        "MFI pro Kanal berechnet und als Excel-Report ausgegeben."
    )
    with gr.Row():
        with gr.Column():
            inp = gr.File(label="TIF-Bild", file_types=[".tif", ".tiff"], type="filepath")
            btn = gr.Button("Analysieren", variant="primary")
        with gr.Column():
            out_file = gr.File(label="Excel-Report")
            out_status = gr.Markdown()
    with gr.Row():
        out_table = gr.Dataframe(headers=["Messwert", "Wert"], label="Ergebnisse", interactive=False)
        out_mask = gr.Image(label="Größte Zelle (Maske)", type="pil")

    btn.click(analyze, inputs=inp, outputs=[out_file, out_status, out_table, out_mask])

if __name__ == "__main__":
    demo.launch()
