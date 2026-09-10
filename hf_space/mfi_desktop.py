"""
Desktop front-end for the MFI analysis (built into a Windows exe with PyInstaller).

Pick one or more TIF images → each gets a Cell_Analysis_Report.xlsx saved next to it.
"""
import shutil
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk, scrolledtext, END, DISABLED, NORMAL

from analysis import run_analysis, get_reader


class App:
    def __init__(self, root):
        self.root = root
        root.title("MFI Cell Analysis")
        root.geometry("720x480")
        root.minsize(560, 360)

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="TIF-Bilder (RGB, mit Maßstabsbalken) auswählen – "
                              "der Excel-Report wird neben jedes Bild gespeichert.",
                  wraplength=680).pack(anchor="w")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(10, 6))
        self.btn = ttk.Button(row, text="Bilder auswählen und analysieren…", command=self.pick_files)
        self.btn.pack(side="left")
        self.status = ttk.Label(row, text="Bereit.")
        self.status.pack(side="left", padx=12)

        self.log = scrolledtext.ScrolledText(frame, height=18, state=DISABLED, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

    def write(self, text):
        def _append():
            self.log.configure(state=NORMAL)
            self.log.insert(END, text + "\n")
            self.log.see(END)
            self.log.configure(state=DISABLED)
        self.root.after(0, _append)

    def set_status(self, text):
        self.root.after(0, lambda: self.status.configure(text=text))

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="TIF-Bilder auswählen",
            filetypes=[("TIF-Bilder", "*.tif *.tiff"), ("Alle Dateien", "*.*")],
        )
        if not paths:
            return
        self.btn.configure(state=DISABLED)
        threading.Thread(target=self.process, args=(paths,), daemon=True).start()

    def process(self, paths):
        ok, failed = 0, 0
        try:
            self.set_status("Lade OCR-Modell (beim ersten Mal ein paar Sekunden)…")
            get_reader()
            for i, p in enumerate(paths, 1):
                src = Path(p)
                self.set_status(f"Analysiere {i}/{len(paths)}: {src.name}")
                self.write(f"── {src.name}")
                run_dir = Path(tempfile.mkdtemp(prefix="mfi_"))
                try:
                    work_copy = run_dir / src.name
                    shutil.copy(src, work_copy)
                    report_path, results, _ = run_analysis(work_copy)
                    target = src.with_name(f"{src.stem}_Cell_Analysis_Report.xlsx")
                    shutil.copy(report_path, target)

                    scale = results["scale_bar_length_um"]
                    if results["ocr_ok"]:
                        self.write(f"   Maßstab per OCR: {scale} µm (gelesen: „{results['ocr_raw']}“)")
                    else:
                        self.write(f"   ⚠ OCR konnte den Maßstab nicht lesen (gelesen: „{results['ocr_raw']}“) "
                                   f"– Standardwert {scale} µm verwendet, µm-Werte bitte prüfen!")
                    self.write(f"   MFI R/G/B: {results['MFI R']:.2f} / {results['MFI G']:.2f} / {results['MFI B']:.2f}"
                               f"   Zellfläche: {results['cell_Area_um']:.1f} µm²")
                    self.write(f"   ✔ Report: {target}")
                    ok += 1
                except Exception as e:
                    failed += 1
                    self.write(f"   ✖ Fehler: {e}")
                    traceback.print_exc()
                finally:
                    shutil.rmtree(run_dir, ignore_errors=True)
        finally:
            self.set_status(f"Fertig: {ok} ok, {failed} fehlgeschlagen.")
            self.root.after(0, lambda: self.btn.configure(state=NORMAL))
            if failed:
                self.root.after(0, lambda: messagebox.showwarning(
                    "MFI Cell Analysis", f"{failed} Bild(er) konnten nicht analysiert werden – Details im Log."))


def run_headless(paths):
    """`MFI-Cell-Analysis.exe bild1.tif bild2.tif` – no window, reports next to the images."""
    for p in paths:
        src = Path(p)
        run_dir = Path(tempfile.mkdtemp(prefix="mfi_"))
        try:
            work_copy = run_dir / src.name
            shutil.copy(src, work_copy)
            report_path, _, _ = run_analysis(work_copy)
            shutil.copy(report_path, src.with_name(f"{src.stem}_Cell_Analysis_Report.xlsx"))
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)


def main():
    if len(sys.argv) > 1:
        run_headless(sys.argv[1:])
        return
    root = Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
