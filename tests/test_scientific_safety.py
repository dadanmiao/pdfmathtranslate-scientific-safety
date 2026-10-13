import io
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_support import OUTPUT, font_path as asset_font_path
root = OUTPUT
import fitz
from babeldoc.format.pdf.document_il import Box, PdfCharacter, PdfStyle, PdfParagraph, PdfParagraphComposition, VisualBbox
from babeldoc.format.pdf.document_il.utils.scientific_text import (
    protected_character_indices, merge_detached_units, character_is_protected_layout,
    validate_model_text, TranslationIntegrityError,
)
from babeldoc.format.pdf.document_il.utils.font_preservation import subset_added_fonts, repair_added_font_unicode
from babeldoc.format.pdf.document_il.midend.il_translator import ILTranslator, FormulaPlaceholder, RichTextPlaceholder


def chars(text, x=0, y=0, size=10, xobj=None):
    return [PdfCharacter(char_unicode=c, pdf_character_id=ord(c),
            pdf_style=PdfStyle(font_id="F1", font_size=size),
            box=Box(x+i*5, y, x+i*5+5, y+size),
            visual_bbox=VisualBbox(Box(x+i*5, y, x+i*5+5, y+size)),
            xobj_id=xobj) for i,c in enumerate(text)]


def paragraph(characters):
    return PdfParagraph(pdf_paragraph_composition=[PdfParagraphComposition(pdf_character=c) for c in characters])


class ScientificSafetyTests(unittest.TestCase):
    def test_added_font_text_map_preserves_ascii_hyphen_and_pixels(self):
        from collections import Counter
        doc = fitz.open()
        page = doc.new_page()
        path = asset_font_path("SourceHanSansCN-Regular.ttf")
        font = fitz.Font(fontfile=str(path))
        text = "ABC-DEF 中文µm²"
        page.insert_font(fontname="addedfont", fontfile=str(path))
        page.insert_text((50, 80), text, fontname="addedfont", fontsize=12)
        before = page.get_pixmap().samples
        mappings = {}
        for char in text:
            if char == " ":
                continue  # Whitespace outside the IL must retain its old cmap.
            mappings.setdefault(font.has_glyph(ord(char)), Counter()).update([char])
        repair_added_font_unicode(doc, {"addedfont": mappings})
        from babeldoc.format.pdf.document_il.backend.pdf_creater import reproduce_one_font
        reproduce_one_font(doc, page.get_fonts()[0][0])
        reopened = fitz.open(stream=doc.tobytes(), filetype="pdf")
        self.assertEqual(reopened[0].get_text().strip().replace("\u00a0", " "), text)
        self.assertEqual(before, reopened[0].get_pixmap().samples)
    def test_latest_official_deepseek_alias_respects_thinking_toggle(self):
        from pdf2zh_next.config.translate_engine_model import DeepSeekSettings
        value=DeepSeekSettings(deepseek_model="deepseek-flash",deepseek_api_key="test-key",deepseek_thinking_mode="disabled").transform()
        self.assertEqual(value._openai_extra_body,{"thinking":{"type":"disabled"}})
        self.assertEqual(value.openai_base_url,"https://api.deepseek.com/v1")
        self.assertEqual(value.openai_timeout,"120.0")
    def test_measurements_identifiers_and_numbers_are_protected(self):
        text = "Area 0.11mm2, process 0.18μm; CMD_PROCESS and CLK_BLF_CMD use 1.92 MHz and CRC16."
        items = chars(text)
        protected = protected_character_indices(items)
        for token in ("0.11mm2", "0.18μm", "CMD_PROCESS", "CLK_BLF_CMD", "1.92 MHz", "CRC16"):
            start = text.index(token)
            self.assertTrue(set(range(start,start+len(token))) <= protected, token)
        self.assertFalse(set(range(4)) & protected)

    def test_form_unit_attaches_to_value_without_losing_its_font_scope(self):
        main = chars("area 0.11.")
        # The PDF stream writes exponent first, then the letters.
        unit_chars = chars("mm", x=45, xobj=7) + chars("2",x=55,y=5,size=6,xobj=7)
        unit = paragraph([unit_chars[2], unit_chars[0], unit_chars[1]])
        host = paragraph(main)
        main[-1].box.x = 60
        main[-1].box.x2 = 65
        result = merge_detached_units([unit, host])
        self.assertEqual(result, [host])
        merged = [c.pdf_character for c in host.pdf_paragraph_composition]
        self.assertEqual("".join(c.char_unicode for c in merged), "area 0.11mm2.")
        self.assertEqual([c.xobj_id for c in merged[-4:-1]], [7,7,7])

    def test_unit_without_adjacent_numeric_value_stays_separate(self):
        body, unit = paragraph(chars("hello")), paragraph(chars("mm",x=100))
        self.assertEqual(len(merge_detached_units([body,unit])), 2)

    def test_figure_text_is_protected_and_table_setting_is_respected(self):
        char = chars("A",x=10,y=10)[0]
        layout = SimpleNamespace(class_name="figure",box=Box(0,0,30,30))
        self.assertTrue(character_is_protected_layout(char,[layout],.9,True))
        layout.class_name="table"
        self.assertTrue(character_is_protected_layout(char,[layout],.9,False))
        self.assertFalse(character_is_protected_layout(char,[layout],.9,True))

    def test_missing_or_duplicate_formula_is_rejected(self):
        translator = ILTranslator.__new__(ILTranslator)
        placeholder = FormulaPlaceholder(1, None, "{v1}", r"\{v1\}")
        translate_input = SimpleNamespace(placeholders=[placeholder])
        for output in ("公式被丢弃", "{v1} {v1}"):
            with self.assertRaises(TranslationIntegrityError):
                translator.parse_translate_output(translate_input, output)

    def test_invalid_unicode_response_is_rejected(self):
        for text in ("", "bad\x00text", "bad\ufffdtext"):
            with self.assertRaises(TranslationIntegrityError):
                validate_model_text(text)
        validate_model_text("正常中文，电压1V。")

    def test_multiple_styles_can_share_the_standard_closing_tag(self):
        translator = ILTranslator.__new__(ILTranslator)
        translator._formula_placeholder_pattern = re.compile(r"\{v\d+\}")
        translator._style_left_placeholder_pattern = re.compile(r"<style id='\d+'>")
        translator._style_right_placeholder_pattern = re.compile(r"</style>")
        style = PdfStyle(font_id="F1", font_size=10)
        from babeldoc.format.pdf.document_il import PdfSameStyleCharacters
        composition = PdfSameStyleCharacters(pdf_style=style,pdf_character=chars("hello"))
        placeholders=[]
        for i in (1,2):
            placeholders.append(RichTextPlaceholder(i,composition,f"<style id='{i}'>","</style>",re.escape(f"<style id='{i}'>"),r"</style>"))
        value=SimpleNamespace(placeholders=placeholders,base_style=style,original_placeholder_tokens=set())
        output="正文<style id='1'>术语</style><style id='2'>内容</style>"
        self.assertEqual(len(translator.parse_translate_output(value,output)),3)

    def test_unrequested_placeholder_is_rejected_even_in_plain_text(self):
        translator = ILTranslator.__new__(ILTranslator)
        translator._formula_placeholder_pattern=re.compile(r"\{v\d+\}")
        translator._style_left_placeholder_pattern=re.compile(r"<style id='\d+'>")
        translator._style_right_placeholder_pattern=re.compile(r"</style>")
        value=SimpleNamespace(placeholders=[],original_placeholder_tokens=set())
        with self.assertRaises(TranslationIntegrityError):
            translator.parse_translate_output(value,"正文{v9}")

    def test_original_fonts_are_not_changed_by_font_optimization(self):
        doc=fitz.open()
        original_page=doc.new_page()
        original_page.insert_text((50,80), "Original formula P = C x V2 x f", fontsize=12)
        original=[p.get_pixmap(matrix=fitz.Matrix(1,1)).samples for p in doc]
        subset_added_fonts(doc,{})
        reopened=fitz.open(stream=doc.tobytes(garbage=4,deflate=True),filetype="pdf")
        for i,page in enumerate(reopened):
            self.assertEqual(original[i],page.get_pixmap(matrix=fitz.Matrix(1,1)).samples)

    def test_added_font_optimization_preserves_cjk_and_superscripts(self):
        doc=fitz.open()
        page=doc.new_page()
        font_path=asset_font_path("SourceHanSansCN-Regular.ttf")
        font=fitz.Font(fontfile=str(font_path))
        text="面积0.11mm²，功耗2.7μW，锁存器。"
        page.insert_font(fontname="addedfont",fontfile=str(font_path))
        page.insert_text((50,80),text,fontname="addedfont",fontsize=12)
        before=page.get_pixmap().samples
        subset_added_fonts(doc,{"addedfont":{font.has_glyph(ord(c)) for c in text}})
        reopened=fitz.open(stream=doc.tobytes(garbage=4,deflate=True),filetype="pdf")
        self.assertEqual(before,reopened[0].get_pixmap().samples)
        self.assertLess(len(reopened.tobytes()),500000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
