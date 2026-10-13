"""End-to-end renderer checks with a deterministic offline model, not a translation deliverable."""
import json
import logging
import multiprocessing
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_support import OUTPUT, font_path as asset_font_path
root = OUTPUT
import fitz
from babeldoc.format.pdf.high_level import translate
from babeldoc.format.pdf.translation_config import TranslationConfig, WatermarkOutputMode
from babeldoc.format.pdf.document_il.utils.scientific_text import TranslationIntegrityError


class RecordedTestModel:
    name="offline-regression"
    lang_in="en"
    lang_out="zh-CN"
    model="test-only"
    def __init__(self,invalid=False): self.invalid=invalid
    def do_llm_translate(self,text): return None
    def get_formular_placeholder(self,i): return "{v"+str(i)+"}",r"\{\s*v\s*"+str(i)+r"\s*\}"
    def get_rich_text_left_placeholder(self,i): return f"<style id='{i}'>",r"<style id='"+str(i)+r"'>"
    def get_rich_text_right_placeholder(self,i): return "</style>",r"</style>"
    def _response(self,text):
        tokens=re.findall(r"\{\s*v\s*\d+\s*\}|<style id='\d+'>|</style>",text)
        if self.invalid: tokens=[]
        return "测试译文。"*max(1,len(text)//22)+" ".join(tokens)
    def llm_translate(self,prompt,**kwargs):
        marker="## Here is the input:"
        if marker in prompt:
            items=json.loads(prompt.rsplit(marker,1)[1].strip())
            return json.dumps([{"id":p["id"],"output":self._response(p["input"])} for p in items],ensure_ascii=False)
        return self._response(prompt.rsplit("Now translate the following text:",1)[1].strip())
    def translate(self,text,**kwargs): return self._response(text)


def fixture():
    path=root / "scientific-fixture.pdf"
    doc=fitz.open()
    unit=fitz.open()
    p=unit.new_page(width=23,height=15)
    font_path=str(asset_font_path("NotoSerif-Regular.ttf"))
    p.insert_font(fontname="F1",fontfile=font_path)
    p.insert_text((0,12),"mm",fontname="F1",fontsize=11)
    p.insert_text((18.5,7),"2",fontname="F1",fontsize=7)
    math=fitz.open()
    p=math.new_page(width=220,height=20)
    p.insert_font(fontname="F1",fontfile=str(asset_font_path("NotoSans-Regular.ttf")))
    p.insert_text((2,14),"P = C × V² × f; α < β + μ",fontname="F1",fontsize=10)
    for i in range(2):
        p=doc.new_page(width=612,height=792)
        helv=p.insert_font(fontname="helv")
        resource_xref=int(doc.xref_get_key(p.xref,"Resources")[1].split()[0])
        kind,fonts=doc.xref_get_key(resource_xref,"Font")
        if kind=="xref":
            doc.xref_set_key(int(fonts.split()[0]),"F1",f"{helv} 0 R")
        else:
            doc.xref_set_key(resource_xref,"Font/F1",f"{helv} 0 R")
        p.insert_text((50,60),"Scientific text regression",fontsize=17)
        value="The area is 0.11"
        p.insert_text((50,130),value,fontsize=11)
        x=50+fitz.get_text_length(value,fontsize=11)+2
        p.show_pdf_page(fitz.Rect(x,118,x+23,133),unit,0)
        p.insert_text((x+25,130),".",fontsize=11)
        p.insert_text((50,180),"A 0.18 µm process consumes 2.7 µW at 1 V.",fontsize=11)
        p.insert_text((50,220),"CLK_BLF_CMD and DATA_OUT are technical signal names.",fontsize=11)
        p.show_pdf_page(fitz.Rect(120,350,470,385),math,0,keep_proportion=False)
        p.insert_text((50,740),f"Regression page {i+1}",fontsize=8)
    doc.save(path,garbage=4,deflate=True)
    return path


def run(input_file,invalid=False):
    tag=input_file.stem+("-invalid" if invalid else "-valid")
    out=root / "pipeline" / tag
    cfg=TranslationConfig(translator=RecordedTestModel(invalid),input_file=input_file,
        lang_in="en",lang_out="zh-CN",doc_layout_model=None,output_dir=out,
        working_dir=out / "ir",no_dual=False,auto_extract_glossary=False,
        disable_rich_text_translate=True,primary_font_family="sans-serif",
        skip_scanned_detection=True,
        watermark_output_mode=WatermarkOutputMode.NoWatermark,
        pages="1" if invalid else None,only_include_translated_page=invalid)
    try:
        result=translate(cfg)
    except TranslationIntegrityError:
        if not invalid: raise
        assert not list(out.glob("*.mono.pdf")), "Unsafe translation was saved"
        print("PASS invalid response blocked before PDF output",flush=True)
        return
    assert not invalid,"Invalid response unexpectedly passed"
    output=fitz.open(result.mono_pdf_path)
    assert len(output)==len(fitz.open(input_file))
    assert all("\x00" not in p.get_text() and "\ufffd" not in p.get_text() for p in output)
    if input_file.stem=="source":
        before=fitz.open(input_file)
        pattern=r"(?<![A-Za-z])mm(?![A-Za-z])"
        assert sum(len(re.findall(pattern,p.get_text())) for p in output)==sum(len(re.findall(pattern,p.get_text())) for p in before),"A square-millimetre unit was lost"
    print("PASS pipeline",input_file.name,len(output),"pages",flush=True)
    for i,page in enumerate(output):
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(out / f"preview-{i+1}.png")


if __name__=="__main__":
    logging.basicConfig(level=logging.CRITICAL)
    multiprocessing.set_executable(sys.executable)
    path=fixture()
    run(path)
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-pdf", type=Path)
    args=parser.parse_args()
    if args.source_pdf:
        run(args.source_pdf)
    run(path,invalid=True)
