"""Inspect supplied Overleaf PDFs without invoking a TeX engine."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

try:
    import fitz
    from pypdf import PdfReader
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit("Requires Python PDF inspection libraries (PyMuPDF, pypdf, Pillow); no TeX engine is used") from exc

ROOT = Path(__file__).resolve().parents[1]

JOBS = {
    "main": {"pdf": ROOT / "verification/overleaf_import/main_overleaf.pdf", "tex": ROOT / "paper/sn-article.tex", "pages": 20},
    "esm1": {"pdf": ROOT / "verification/overleaf_import/ESM_1_overleaf.pdf", "tex": ROOT / "paper/supplemental.tex", "pages": 7},
}

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def norm(s: str) -> str:
    s = s.replace("−", "-").replace("–", "-").replace("×", "x").replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = re.sub(r"\\(?:textbf|textit|emph|mathrm|operatorname)\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\[A-Za-z]+|[{}$~_^]", " ", s)
    return re.sub(r"[^a-z0-9.-]+", " ", s.lower()).strip()

def tex_structure(tex: str) -> dict:
    return {
        "documentclass": re.findall(r"\\documentclass(?:\[[^]]+\])?\{([^}]+)\}", tex),
        "packages": [x for group in re.findall(r"\\usepackage(?:\[[^]]+\])?\{([^}]+)\}", tex) for x in group.split(",")],
        "sections": re.findall(r"\\(?:sub)*section\*?\{([^}]+)\}", tex),
        "figures": re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", tex),
        "figure_captions": re.findall(r"\\caption\{([^}]*(?:\{[^}]*\}[^}]*)*)\}", tex),
        "table_count": len(re.findall(r"\\begin\{table\*?\}", tex)),
        "figure_count": len(re.findall(r"\\begin\{figure\*?\}", tex)),
        "bibliography": re.findall(r"\\bibliography\{([^}]+)\}", tex),
        "bibliographystyle": re.findall(r"\\bibliographystyle\{([^}]+)\}", tex),
        "inputs": re.findall(r"\\(?:input|include)\{([^}]+)\}", tex),
    }

def contact_sheet(images: list[Path], out: Path, cols: int = 4) -> None:
    thumbs=[]
    for p in images:
        im=Image.open(p).convert("RGB"); im.thumbnail((360,510)); thumbs.append((p.name,im.copy()))
    cell_w,cell_h=380,550; rows=(len(thumbs)+cols-1)//cols
    sheet=Image.new("RGB",(cell_w*cols,cell_h*rows),"white"); draw=ImageDraw.Draw(sheet)
    for i,(name,im) in enumerate(thumbs):
        x=(i%cols)*cell_w+(cell_w-im.width)//2; y=(i//cols)*cell_h+24
        sheet.paste(im,(x,y)); draw.text(((i%cols)*cell_w+8,(i//cols)*cell_h+5),name,fill="black")
    sheet.save(out)

def audit(label: str, cfg: dict) -> dict:
    pdf, tex_path = cfg["pdf"], cfg["tex"]
    review = ROOT / "verification/pdf_review" / label
    review.mkdir(parents=True, exist_ok=True)
    doc=fitz.open(pdf); reader=PdfReader(str(pdf)); tex=tex_path.read_text(encoding="utf-8")
    page_text=[]; page_png=[]; fonts={}; type3=[]; unembedded=[]; images=[]; links=0
    for ix,page in enumerate(doc):
        text=page.get_text("text"); page_text.append(text)
        pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
        png=review/f"page-{ix+1:02d}.png"; pix.save(png); page_png.append(png)
        links += len(page.get_links())
        for f in page.get_fonts(full=True):
            xref,ext,ftype,basefont,name,encoding,*rest=f
            key=f"{basefont}|{ftype}|{xref}"; fonts[key]={"basefont":basefont,"type":ftype,"xref":xref,"encoding":encoding,"pages":[]}
            fonts[key]["pages"].append(ix+1)
            if ftype == "Type3": type3.append({"font":basefont,"page":ix+1})
            try: embedded=bool(doc.extract_font(xref)[-1])
            except Exception: embedded=False
            fonts[key]["embedded"]=embedded
            if not embedded: unembedded.append({"font":basefont,"page":ix+1})
        for info in page.get_image_info(xrefs=True):
            rect=info.get("bbox"); w,h=info.get("width",0),info.get("height",0)
            dpi_x=dpi_y=None
            if rect and rect[2]>rect[0] and rect[3]>rect[1]:
                dpi_x=round(w*72/(rect[2]-rect[0]),1); dpi_y=round(h*72/(rect[3]-rect[1]),1)
            images.append({"page":ix+1,"width_px":w,"height_px":h,"effective_dpi_x":dpi_x,"effective_dpi_y":dpi_y})
    full_text="\n\f\n".join(page_text)
    (review/"extracted_text.txt").write_text(full_text,encoding="utf-8")
    contact_sheet(page_png,review/"contact_sheet.png")
    structure=tex_structure(tex); normalized_pdf=norm(full_text)
    section_checks={s:norm(s) in normalized_pdf for s in structure["sections"]}
    required = (["Purpose", "Methods", "Results", "Conclusion", "Brandon Shen", "0009-0002-3545-2106"] if label=="main" else ["Online Resource 1", "Corrected primary family", "Conditional exact-gradient indices"])
    required_checks={x:norm(x) in normalized_pdf for x in required}
    result={
        "status":"pass" if len(doc)==cfg["pages"] and all(required_checks.values()) and not type3 and not unembedded else "review",
        "pdf":str(pdf.relative_to(ROOT)).replace("\\","/"),"sha256":sha(pdf),"pages":len(doc),
        "page_size_points":[round(doc[0].rect.width,3),round(doc[0].rect.height,3)],
        "encrypted":bool(reader.is_encrypted),"metadata":doc.metadata,"text_characters":len(full_text),
        "links":links,"fonts":list(fonts.values()),"type3_fonts":type3,"unembedded_fonts":unembedded,
        "images":images,"minimum_effective_dpi":min([min(x["effective_dpi_x"],x["effective_dpi_y"]) for x in images if x["effective_dpi_x"]] or [None]),
        "source":str(tex_path.relative_to(ROOT)).replace("\\","/"),"source_sha256":sha(tex_path),"source_lines":len(tex.splitlines()),
        "structure":structure,"section_heading_checks":section_checks,"identity_checks":required_checks,
        "render_directory":str(review.relative_to(ROOT)).replace("\\","/"),
    }
    return result

def main() -> None:
    results={k:audit(k,v) for k,v in JOBS.items()}
    out=ROOT/"verification/pdf_automated_audit.json"; out.write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:{x:r[x] for x in ["status","pages","type3_fonts","unembedded_fonts","minimum_effective_dpi"]} for k,r in results.items()},indent=2))

if __name__=="__main__": main()
