"""Rasterize lecture PDF to PNGs (one per page)."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def rasterize_pdf_to_pngs(pdf_path: Path, out_dir: Path, zoom: float = 2.0) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    matrix = fitz.Matrix(zoom, zoom)
    paths: list[Path] = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out = out_dir / f"slide_{i + 1:03d}.png"
        pix.save(out.as_posix())
        paths.append(out)
    doc.close()
    return paths
