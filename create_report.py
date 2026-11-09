from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
OUT = ROOT / "report" / "Bao_cao_do_an_Nhap_mon_Toi_uu_hoa.docx"

NAVY = "17365D"
BLUE = "2F5597"
LIGHT_BLUE = "DCE6F1"
PALE = "F3F6FA"
DARK = "202833"
GREY = "667085"
ACCENT = "8A2432"
WHITE = "FFFFFF"


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, **kwargs) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if edge in kwargs:
            tag = "w:" + edge
            element = borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                borders.append(element)
            for key in ["val", "sz", "space", "color"]:
                if key in kwargs[edge]:
                    element.set(qn("w:" + key), str(kwargs[edge][key]))


def set_cell_margins(cell, top=80, start=90, bottom=80, end=90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in [("top", top), ("start", start), ("bottom", bottom), ("end", end)]:
        node = tc_mar.find(qn("w:" + m))
        if node is None:
            node = OxmlElement("w:" + m)
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_font(run, name="Times New Roman", size=11, color=DARK, bold=False, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.bold = bold
    run.italic = italic
    return run


def format_paragraph(p, before=0, after=5, line=1.22, alignment=None, first_indent=0.65):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if first_indent is not None:
        pf.first_line_indent = Cm(first_indent)
    if alignment is not None:
        p.alignment = alignment
    return p


def add_para(doc, text="", *, bold_prefix=None, align=None, size=11, color=DARK,
             italic=False, before=0, after=5, first_indent=0.65, line=1.22):
    p = doc.add_paragraph()
    format_paragraph(p, before, after, line, align, first_indent)
    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        set_font(r, size=size, color=color, bold=True)
        r = p.add_run(text[len(bold_prefix):])
        set_font(r, size=size, color=color, italic=italic)
    else:
        r = p.add_run(text)
        set_font(r, size=size, color=color, italic=italic)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(8 if level == 1 else 5)
    p.paragraph_format.space_after = Pt(5 if level == 1 else 3)
    r = p.add_run(text)
    if level == 1:
        set_font(r, size=15, color=NAVY, bold=True)
    elif level == 2:
        set_font(r, size=12.5, color=BLUE, bold=True)
    else:
        set_font(r, size=11.5, color=DARK, bold=True)
    return p


def add_bookmark(paragraph, name: str, bookmark_id: int) -> None:
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def add_hyperlink(paragraph, text: str, anchor: str):
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), anchor)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), BLUE)
    rpr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(underline)
    run.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return hyperlink


def add_page_field(paragraph):
    r = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    r._r.append(fld_char1)
    r._r.append(instr)
    r._r.append(fld_char2)


def add_table(doc, headers, rows, widths=None, font_size=9.2, alignments=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, label in enumerate(headers):
        cell = hdr.cells[i]
        if widths:
            cell.width = Cm(widths[i])
        shade_cell(cell, NAVY)
        set_cell_margins(cell, 80, 75, 80, 75)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        set_font(p.add_run(str(label)), size=font_size, color=WHITE, bold=True)
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            if widths:
                cell.width = Cm(widths[i])
            if ridx % 2 == 1:
                shade_cell(cell, PALE)
            set_cell_margins(cell, 70, 75, 70, 75)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.02
            if alignments and i < len(alignments):
                p.alignment = alignments[i]
            elif i > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(p.add_run(str(value)), size=font_size, color=DARK)
    # Avoid rows splitting between pages.
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        tr_pr.append(cant)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(5)
    set_font(p.add_run(text), size=9.2, color=GREY, italic=True)
    return p


def add_picture(doc, path, width=6.15):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(str(path), width=Inches(width))
    return p


def add_page_break(doc):
    doc.add_page_break()


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.left_indent = Cm(0.65 + 0.45 * level)
    p.paragraph_format.first_line_indent = Cm(-0.25)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    set_font(p.add_run(text), size=10.8)
    return p


def add_number(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.left_indent = Cm(0.65)
    p.paragraph_format.first_line_indent = Cm(-0.25)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    set_font(p.add_run(text), size=10.8)
    return p


def add_code_box(doc, text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    shade_cell(cell, "F3F6FA")
    set_cell_border(cell,
        top={"val":"single","sz":"5","color":"B7C9D6"},
        bottom={"val":"single","sz":"5","color":"B7C9D6"},
        left={"val":"single","sz":"5","color":"B7C9D6"},
        right={"val":"single","sz":"5","color":"B7C9D6"},
    )
    set_cell_margins(cell, 110, 140, 110, 140)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.1
    set_font(p.add_run(text), name="Consolas", size=9.5, color=NAVY)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def main():
    method_summary = pd.read_csv(RESULTS / "search_method_summary.csv")
    final_metrics = pd.read_csv(RESULTS / "final_model_metrics.csv")
    pareto = pd.read_csv(RESULTS / "pareto_front.csv").sort_values("trial")
    baseline = pd.read_csv(RESULTS / "baseline_cv.csv")
    seed_summary = pd.read_csv(RESULTS / "search_seed_summary.csv")
    knee = json.loads((RESULTS / "pareto_knee_selection.json").read_text(encoding="utf-8"))
    selected = json.loads((RESULTS / "selected_configs.json").read_text(encoding="utf-8"))
    best_hpo = selected["best_hpo"]

    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.4)
    sec.right_margin = Cm(2.2)
    sec.header_distance = Cm(1.0)
    sec.footer_distance = Cm(1.0)
    sec.different_first_page_header_footer = True

    # Document properties
    doc.core_properties.title = "Tối ưu siêu tham số Random Forest và phân tích Pareto"
    doc.core_properties.subject = "Báo cáo đồ án cá nhân - Nhập môn Tối ưu hóa"
    doc.core_properties.author = "Dương Quốc Trọng"
    doc.core_properties.keywords = "Random Forest, HPO, Optuna, TPE, NSGA-II, Pareto"

    # Default style and headings
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.line_spacing = 1.22
    normal.paragraph_format.space_after = Pt(5)
    for style_name in ["Heading 1", "Heading 2", "Heading 3"]:
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.paragraph_format.keep_with_next = True

    # Header and footer
    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header.paragraph_format.space_after = Pt(3)
    set_font(header.add_run("TRƯỜNG ĐẠI HỌC VĂN LANG  |  KHOA CÔNG NGHỆ THÔNG TIN"), size=8.5, color=GREY, bold=True)
    pPr = header._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), "B7C9D6")
    pBdr.append(bottom)
    pPr.append(pBdr)

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(2)
    set_font(footer.add_run("DƯƠNG QUỐC TRỌNG  •  MSSV 2274802010932  |  Trang "), size=8.5, color=GREY)
    add_page_field(footer)

    # --------- COVER PAGE ---------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(3)
    set_font(p.add_run("TRƯỜNG ĐẠI HỌC VĂN LANG"), size=16, color=NAVY, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    set_font(p.add_run("KHOA CÔNG NGHỆ THÔNG TIN"), size=13, color=BLUE, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(74)
    p.paragraph_format.space_after = Pt(8)
    set_font(p.add_run("BÁO CÁO BÀI TẬP LỚN CÁ NHÂN"), size=14, color=ACCENT, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.line_spacing = 1.18
    set_font(p.add_run("TỐI ƯU SIÊU THAM SỐ RANDOM FOREST\nVÀ PHÂN TÍCH PARETO GIỮA ĐỘ CHÍNH XÁC,\nĐỘ TRỄ VÀ ĐỘ PHỨC TẠP MÔ HÌNH"), size=20, color=NAVY, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    set_font(p.add_run("MÔN HỌC: NHẬP MÔN TỐI ƯU HÓA"), size=12, color=BLUE, bold=True)

    # Thin accent line via single-cell table
    line_table = doc.add_table(rows=1, cols=1)
    line_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    line_cell = line_table.cell(0, 0)
    line_cell.height = Cm(0.06)
    shade_cell(line_cell, ACCENT)
    set_cell_margins(line_cell, 0, 0, 0, 0)
    line_cell.text = ""

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(42)
    p.paragraph_format.left_indent = Cm(3.0)
    p.paragraph_format.right_indent = Cm(2.0)
    p.paragraph_format.space_after = Pt(8)
    set_font(p.add_run("Sinh viên thực hiện:  "), size=12, color=GREY, bold=True)
    set_font(p.add_run("DƯƠNG QUỐC TRỌNG"), size=13, color=NAVY, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(3.0)
    p.paragraph_format.space_after = Pt(8)
    set_font(p.add_run("Mã số sinh viên:  "), size=12, color=GREY, bold=True)
    set_font(p.add_run("2274802010932"), size=12, color=NAVY, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(3.0)
    p.paragraph_format.space_after = Pt(8)
    set_font(p.add_run("Lớp / Giảng viên:  "), size=12, color=GREY, bold=True)
    set_font(p.add_run("Theo thông tin lớp học phần"), size=11, color=DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(68)
    set_font(p.add_run("TP. HỒ CHÍ MINH - THÁNG 11 NĂM 2026"), size=11, color=GREY, bold=True)

    add_page_break(doc)

    # --------- ABSTRACT PAGE ---------
    h = add_heading(doc, "TÓM TẮT ĐỒ ÁN", 1)
    add_bookmark(h, "abstract", 1)
    add_para(doc,
        "Đồ án tập trung nghiên cứu một vấn đề thường gặp khi xây dựng mô hình học máy: cùng một thuật toán có thể cho kết quả khác nhau khi thay đổi các siêu tham số. Không chỉ cần tìm cấu hình có độ chính xác cao, người phát triển còn phải cân nhắc tốc độ dự đoán và độ phức tạp của mô hình khi đưa vào sử dụng.")
    add_para(doc,
        "Trên bộ dữ liệu Breast Cancer Wisconsin (Diagnostic) được tích hợp trong scikit-learn, đồ án xây dựng mô hình Random Forest và đánh giá cấu hình mặc định làm baseline. Ba phương pháp Grid Search, Random Search và Optuna/TPE được so sánh trên cùng search space, cùng 5-fold cross-validation và cùng evaluation budget. Tiếp đó, NSGA-II trong Optuna được sử dụng để tìm các cấu hình không bị dominate khi đồng thời tối đa hóa accuracy, tối thiểu hóa inference latency và tổng số node của các cây.")
    add_para(doc,
        "Kết quả thực nghiệm cho thấy baseline đạt mean CV accuracy 0,9597. Grid Search và Random Search cùng đạt 0,9648 ± 0,0022; Optuna/TPE đạt 0,9641 ± 0,0025. NSGA-II tạo được sáu nghiệm Pareto trong 20 trial. Trên test set đã khóa, baseline và cấu hình HPO tốt nhất cùng đạt accuracy 0,9561, nhưng cấu hình HPO có latency và số node thấp hơn. Nghiệm knee của Pareto front giảm thêm độ trễ và dung lượng mô hình, đổi lại accuracy giảm nhẹ xuống 0,9474.")
    add_para(doc,
        "Kết quả cho thấy không có một cấu hình tốt nhất trong mọi bối cảnh. Lựa chọn cuối cùng cần gắn với yêu cầu triển khai: ưu tiên accuracy, thiết bị hạn chế tài nguyên hay hệ thống cần phản hồi nhanh. Các số đo latency trong đồ án chỉ phản ánh môi trường thực nghiệm và cần được kiểm tra lại trên phần cứng triển khai thực tế.")

    add_heading(doc, "Từ khóa", 2)
    add_para(doc, "Hyperparameter Optimization (HPO); Random Forest; Grid Search; Random Search; Optuna; TPE; NSGA-II; Pareto front; Accuracy; Latency; Complexity.", first_indent=0)
    add_heading(doc, "Lời ghi nhận về công cụ hỗ trợ", 2)
    add_para(doc,
        "AI được sử dụng để hỗ trợ khởi tạo cấu trúc mã, diễn giải các khái niệm và biên tập bản thảo. Toàn bộ số liệu trong báo cáo được sinh từ chương trình và các tệp log đi kèm. Sinh viên cần tự chạy lại, đọc hiểu mã nguồn và chịu trách nhiệm về nội dung khi nộp cũng như khi bảo vệ.")

    add_page_break(doc)

    # --------- MANUAL CONTENTS PAGE ---------
    toc_h = add_heading(doc, "MỤC LỤC", 1)
    add_bookmark(toc_h, "toc", 2)
    toc_entries = [
        ("1. Đặt vấn đề", "s1", "4"),
        ("2. Cơ sở lý thuyết", "s2", "5"),
        ("3. Mô hình hóa bài toán tối ưu", "s3", "6"),
        ("4. Dữ liệu và thiết kế thực nghiệm", "s4", "7"),
        ("5. Phương pháp và cài đặt", "s5", "8"),
        ("6. Kết quả thực nghiệm", "s6", "9"),
        ("   6.1. So sánh HPO đơn mục tiêu", "s61", "9"),
        ("   6.2. NSGA-II và Pareto front", "s62", "11"),
        ("   6.3. Đánh giá cuối trên test set", "s63", "13"),
        ("7. Thảo luận và quyết định triển khai", "s7", "14"),
        ("8. Kết luận và hướng phát triển", "s8", "15"),
        ("Tài liệu tham khảo", "refs", "16"),
        ("Phụ lục A. Cài đặt và chạy chương trình", "appa", "17"),
        ("Phụ lục B. Giải thích ngắn gọn để bảo vệ", "appb", "18"),
    ]
    for label, anchor, page in toc_entries:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.35 if label.startswith("   ") else 0)
        p.paragraph_format.space_after = Pt(5 if not label.startswith("   ") else 3)
        p.paragraph_format.line_spacing = 1.1
        text = label.strip()
        add_hyperlink(p, text, anchor)
        tab = p.add_run(" " + "." * max(4, 46 - len(text)) + " " + page)
        set_font(tab, size=9.5, color=GREY)
    add_para(doc,
        "Lưu ý: mục lục có liên kết nội bộ; có thể bấm vào tên chương để chuyển nhanh đến phần tương ứng.",
        first_indent=0, size=9.5, color=GREY, italic=True, before=8)

    add_page_break(doc)

    # --------- 1. INTRODUCTION ---------
    h = add_heading(doc, "1. ĐẶT VẤN ĐỀ", 1)
    add_bookmark(h, "s1", 3)
    add_heading(doc, "1.1. Bối cảnh", 2)
    add_para(doc,
        "Trong một bài toán phân loại, việc chọn đúng thuật toán mới chỉ là bước đầu. Ngay cả khi đã chọn Random Forest, người xây dựng vẫn phải quyết định số lượng cây, độ sâu tối đa, số mẫu tối thiểu để chia một node và số đặc trưng được xét ở mỗi lần tách. Những lựa chọn này được gọi là hyperparameter. Chúng ảnh hưởng đến độ chính xác, chi phí huấn luyện, tốc độ dự đoán và dung lượng mô hình.")
    add_para(doc,
        "Nếu thử từng cấu hình bằng cảm tính, người thực hiện khó biết cấu hình nào thực sự tốt hơn và đã bỏ lỡ những vùng nào trong không gian tìm kiếm. Hyperparameter Optimization (HPO) giải quyết vấn đề đó bằng một quy trình tìm kiếm có ngân sách, metric và phương pháp đánh giá rõ ràng.")
    add_heading(doc, "1.2. Vấn đề cần giải quyết", 2)
    add_para(doc,
        "Đồ án đặt câu hỏi: với cùng bộ dữ liệu và cùng ngân sách đánh giá, Grid Search, Random Search và Optuna/TPE tìm được cấu hình Random Forest tốt đến mức nào? Khi đồng thời quan tâm đến accuracy, latency và complexity, có thể tìm ra những phương án đánh đổi nào và nên chọn phương án nào cho từng nhu cầu triển khai?")
    add_heading(doc, "1.3. Mục tiêu và phạm vi", 2)
    for item in [
        "Phân biệt baseline, model parameter và hyperparameter; chuyển bài toán thành mô hình tối ưu có biến quyết định, objective và miền khả thi.",
        "So sánh ba phương pháp HPO theo cùng dataset, 5-fold CV, 24 trial mỗi seed và ba random seed.",
        "Dùng NSGA-II để xác định tập nghiệm non-dominated trên ba mục tiêu Accuracy - Latency - Complexity.",
        "Lưu trial history, CSV/SQLite, biểu đồ, mô hình đã fit và hướng dẫn tái lập trong một repository có cấu trúc rõ ràng."
    ]:
        add_bullet(doc, item)
    add_para(doc,
        "Phạm vi được giới hạn ở một dataset và một họ mô hình Random Forest. Đây là lựa chọn vừa sức với một sinh viên trong thời gian 5 tuần, đồng thời trùng với case study và bài thực hành tự học được nêu trong tài liệu Chương 6.")

    add_page_break(doc)

    # --------- 2. THEORY ---------
    h = add_heading(doc, "2. CƠ SỞ LÝ THUYẾT", 1)
    add_bookmark(h, "s2", 4)
    add_heading(doc, "2.1. Parameter và hyperparameter", 2)
    add_para(doc,
        "Model parameters là các đại lượng được mô hình học trực tiếp từ dữ liệu, chẳng hạn trọng số và bias. Hyperparameters là các lựa chọn nằm ngoài quá trình học nội tại, do người thiết kế hoặc thuật toán HPO quyết định. Trong Random Forest, các ngưỡng chia node được học từ dữ liệu, còn n_estimators và max_depth là hyperparameter.")
    add_heading(doc, "2.2. HPO là bài toán tối ưu lồng", 2)
    add_para(doc,
        "Với một vector hyperparameter λ cố định, quá trình training tìm bộ model parameter θ tốt nhất trên tập train. Sau đó, HPO đánh giá mô hình bằng validation hoặc cross-validation để chọn λ. Có thể mô tả ngắn gọn như sau:", first_indent=0)
    add_code_box(doc,
        "θ*(λ) = arg min_θ L_train(θ; λ)\nλ*    = arg min_λ L_val(θ*(λ); λ)"
    )
    add_para(doc,
        "Do mỗi lần đánh giá một λ có thể phải huấn luyện mô hình trên nhiều fold, HPO tốn chi phí hơn một phép tối ưu hàm số thông thường. Search space và evaluation budget vì vậy cần được thiết kế có lý do.")
    add_heading(doc, "2.3. Các phương pháp tìm kiếm", 2)
    add_para(doc,
        "Grid Search thử toàn bộ tổ hợp giá trị được định trước. Cách này dễ giải thích và tái lập, phù hợp khi không gian nhỏ, nhưng số tổ hợp tăng nhanh theo số chiều. Random Search lấy mẫu cấu hình theo một ngân sách xác định; thường hữu ích khi chỉ một vài chiều ảnh hưởng mạnh. Bayesian Optimization sử dụng kết quả trial trước để đề xuất điểm tiếp theo. TPE là một cách tiếp cận thuộc nhóm này, mô hình hóa phân bố của trial tốt và trial còn lại để ưu tiên vùng có triển vọng.")
    add_heading(doc, "2.4. Tối ưu đa mục tiêu và Pareto", 2)
    add_para(doc,
        "Khi cần tăng accuracy nhưng đồng thời giảm latency và model size, không nhất thiết tồn tại một nghiệm thắng ở mọi mặt. Nghiệm A dominate nghiệm B nếu A không kém B ở tất cả mục tiêu và tốt hơn ở ít nhất một mục tiêu. Nghiệm không bị nghiệm khả thi khác dominate được gọi là Pareto-optimal; tập các giá trị mục tiêu tương ứng tạo thành Pareto front.")
    add_para(doc,
        "NSGA-II duy trì nhiều nghiệm thay vì chỉ một nghiệm. Hai ý tưởng quan trọng là non-dominated sorting để phân tầng nghiệm theo dominance và crowding distance để giữ độ đa dạng trên Pareto front. Sau khi có front, người sử dụng vẫn phải chọn nghiệm theo yêu cầu triển khai.")

    add_page_break(doc)

    # --------- 3. FORMULATION ---------
    h = add_heading(doc, "3. MÔ HÌNH HÓA BÀI TOÁN TỐI ƯU", 1)
    add_bookmark(h, "s3", 5)
    add_heading(doc, "3.1. Biến quyết định", 2)
    add_para(doc,
        "Vector quyết định của bài toán HPO đơn mục tiêu gồm bốn hyperparameter của Random Forest. Miền giá trị được giới hạn để số cấu hình vừa đủ cho thí nghiệm và có thể chạy trên máy tính cá nhân.", first_indent=0)
    add_table(doc,
        ["Biến", "Kiểu", "Miền tìm kiếm đơn mục tiêu", "Ý nghĩa"],
        [
            ["n_estimators", "Integer / categorical", "{20, 40, 60}", "Số cây trong rừng"],
            ["max_depth", "Categorical", "{None, 10}", "Độ sâu tối đa của cây"],
            ["min_samples_split", "Categorical", "{2, 5}", "Số mẫu tối thiểu để tách node"],
            ["max_features", "Categorical", "{sqrt, log2}", "Số/nhóm đặc trưng xét khi chia node"],
        ],
        widths=[3.0, 3.1, 4.5, 5.0], font_size=8.7,
    )
    add_para(doc,
        "Tổng số cấu hình của grid là 3 × 2 × 2 × 2 = 24. Mỗi phương pháp HPO được cấp đúng 24 trial ở mỗi seed. Với ba seed 17, 42 và 73, tổng ngân sách là 72 evaluations cho mỗi phương pháp.")
    add_heading(doc, "3.2. Hàm mục tiêu đơn mục tiêu", 2)
    add_code_box(doc,
        "maximize  f1(x) = mean 5-fold CV accuracy(x)\nsubject to  x thuộc search space đã định nghĩa\n            24 trial / seed, 3 seed"
    )
    add_para(doc,
        "Accuracy được tính ở từng fold rồi lấy trung bình. Độ lệch chuẩn giữa các fold được lưu kèm để thể hiện mức biến động của cấu hình, không chỉ lưu một con số tốt nhất.")
    add_heading(doc, "3.3. Bài toán tối ưu đa mục tiêu", 2)
    add_code_box(doc,
        "maximize  f1(x) = CV accuracy(x)\nminimize  f2(x) = median inference latency(x)\nminimize  f3(x) = total tree nodes(x)"
    )
    add_para(doc,
        "Latency được đo bằng mili giây cho một mẫu đầu vào. Complexity được đại diện bằng tổng số node của tất cả cây trong Random Forest; đây là proxy trực quan cho độ lớn cấu trúc cây, không phải phép đo đầy đủ mọi chi phí bộ nhớ. Dung lượng file joblib được ghi thêm ở bước đánh giá cuối.")
    add_heading(doc, "3.4. Quy tắc chọn nghiệm cuối", 2)
    add_para(doc,
        "Sau khi lọc nghiệm bị dominate, đồ án chuẩn hóa error (1 - accuracy), latency và total nodes về cùng thang [0, 1]. Nghiệm gần điểm lý tưởng (0, 0, 0) nhất được chọn làm knee đại diện cho phương án cân bằng. Đây là quy tắc quyết định của đồ án, không phải một lựa chọn tối ưu phổ quát cho mọi thiết bị.")

    add_page_break(doc)

    # --------- 4. DATA & EXPERIMENT ---------
    h = add_heading(doc, "4. DỮ LIỆU VÀ THIẾT KẾ THỰC NGHIỆM", 1)
    add_bookmark(h, "s4", 6)
    add_heading(doc, "4.1. Dataset", 2)
    add_para(doc,
        "Breast Cancer Wisconsin (Diagnostic) là bộ dữ liệu benchmark được cung cấp sẵn trong scikit-learn. Dataset gồm 569 mẫu, 30 đặc trưng số và hai lớp phân loại. Chương trình gọi load_breast_cancer() trực tiếp, vì vậy không cần tải dữ liệu ngoài hoặc phụ thuộc Internet khi chạy.")
    add_heading(doc, "4.2. Chia dữ liệu và chống data leakage", 2)
    add_para(doc,
        "Dữ liệu được chia phân tầng thành 80% development set (455 mẫu) và 20% test set (114 mẫu), dùng random_state=42. Tất cả baseline và HPO chỉ được đánh giá trên development set bằng StratifiedKFold 5 fold. X_test và y_test không xuất hiện trong objective hoặc hàm chọn hyperparameter.")
    add_para(doc,
        "Random Forest làm việc trực tiếp với đặc trưng số của dataset và không yêu cầu chuẩn hóa thang đo trong thí nghiệm này. Do đó đồ án không thêm StandardScaler. Điều quan trọng là không fit bất kỳ bước tiền xử lý dựa trên thống kê dữ liệu ngoài train fold; với pipeline có tiền xử lý, bước đó phải nằm bên trong Pipeline/CV.")
    add_heading(doc, "4.3. Protocol công bằng", 2)
    for item in [
        "Dùng cùng development set, cùng 5-fold CV và cùng accuracy scoring cho Grid, Random và TPE.",
        "Mỗi phương pháp có 24 trial/seed, lặp với ba seed 17, 42, 73; ghi toàn bộ lịch sử trial.",
        "Baseline là RandomForestClassifier với cấu hình mặc định, được đánh giá trên cùng các fold.",
        "Sau khi chốt cấu hình bằng CV và Pareto front, refit trên toàn development set rồi đánh giá test ở giai đoạn cuối.",
        "Latency có warm-up và đo lặp; final model dùng 100 lần đo sau 10 warm-up. Complexity lưu cả tổng node và file size."
    ]:
        add_bullet(doc, item)
    add_heading(doc, "4.4. Ngân sách thực nghiệm", 2)
    add_table(doc,
        ["Hạng mục", "Ngân sách", "Mục đích"],
        [
            ["Baseline", "5-fold CV × 3 seed", "Mốc so sánh ban đầu"],
            ["Grid / Random / TPE", "24 trial × 3 seed / phương pháp", "So sánh HPO đơn mục tiêu"],
            ["NSGA-II", "20 trial; population size 10", "Tạo tập nghiệm Pareto"],
            ["Final evaluation", "3 cấu hình đã khóa; test 114 mẫu", "Báo cáo accuracy và chi phí triển khai"],
        ], widths=[4.2, 5.0, 6.4], font_size=8.8,
    )

    add_page_break(doc)

    # --------- 5. METHODS ---------
    h = add_heading(doc, "5. PHƯƠNG PHÁP VÀ CÀI ĐẶT", 1)
    add_bookmark(h, "s5", 7)
    add_heading(doc, "5.1. Baseline", 2)
    add_para(doc,
        "Baseline dùng RandomForestClassifier mặc định. Mục đích không phải tạo một đối thủ yếu, mà thiết lập mốc thực tế để đo mức cải thiện khi tuning. Baseline được đánh giá bằng cùng 5-fold CV qua ba seed.")
    add_heading(doc, "5.2. Grid Search và Random Search", 2)
    add_para(doc,
        "Grid Search sinh toàn bộ 24 tổ hợp từ search space. Random Search dùng ParameterSampler với n_iter=24 trên cùng tập giá trị rời rạc. Vì số lượt lấy mẫu bằng đúng số tổ hợp có thể có, Random Search đã lấy đủ toàn bộ 24 cấu hình, chỉ khác thứ tự. Đây là lý do quan trọng khiến hai phương pháp có kết quả trùng nhau trong thí nghiệm.")
    add_heading(doc, "5.3. Optuna/TPE", 2)
    add_para(doc,
        "Mỗi Study là một chiến dịch HPO; mỗi Trial là một lần đánh giá cấu hình. TPESampler đề xuất các hyperparameter tiếp theo dựa trên lịch sử trial, với tám trial đầu làm giai đoạn khởi tạo. Hàm objective trả về mean CV accuracy; kết quả và tham số được lưu lại để phân tích.")
    add_heading(doc, "5.4. NSGA-II và Optuna multi-objective", 2)
    add_para(doc,
        "Study đa mục tiêu khai báo directions = [maximize, minimize, minimize]. Mỗi trial trả về bộ ba (CV accuracy, median latency, total nodes). NSGA-II dùng non-dominated sorting và crowding distance để giữ các nghiệm có chất lượng và độ đa dạng. SQLite storage được đặt tại results/nsga2_study.db; các trial và Pareto front cũng được xuất ra CSV để xem bằng bảng tính.")
    add_heading(doc, "5.5. Lý do không dùng pruning", 2)
    add_para(doc,
        "Pruning có ích khi một trial cung cấp intermediate metric theo epoch, iteration hoặc resource step. Trong quy trình Random Forest này, mỗi trial đánh giá bằng cross-validation và chỉ có kết quả sau khi hoàn tất các fold; không có learning curve theo epoch để pruner so sánh một cách hợp lý. Vì vậy đồ án không bật pruning, tránh tạo cảm giác có tối ưu tài nguyên khi không có tín hiệu trung gian phù hợp.")
    add_heading(doc, "5.6. Cấu trúc chương trình", 2)
    add_para(doc,
        "Toàn bộ quy trình nằm trong src/experiment.py. run_project.py là điểm bắt đầu. Chương trình tạo các tệp baseline_cv.csv, cv_search_history.csv, search_method_summary.csv, nsga2_all_trials.csv, pareto_front.csv và final_model_metrics.csv; các hình được lưu riêng trong figures/. Ba mô hình đã fit được lưu bằng joblib trong models/. Cách bố trí này giúp phân biệt mã nguồn, dữ liệu, kết quả và mô hình đã huấn luyện.")

    add_page_break(doc)

    # --------- 6. RESULTS PAGE 1 ---------
    h = add_heading(doc, "6. KẾT QUẢ THỰC NGHIỆM", 1)
    add_bookmark(h, "s6", 8)
    h2 = add_heading(doc, "6.1. So sánh HPO đơn mục tiêu", 2)
    add_bookmark(h2, "s61", 9)
    baseline_mean = baseline["cv_accuracy"].mean()
    baseline_std = baseline["cv_accuracy"].std(ddof=1)
    add_para(doc,
        f"Baseline đạt mean CV accuracy {baseline_mean:.4f} ± {baseline_std:.4f} qua ba seed. Kết quả tổng hợp của ba phương pháp HPO được trình bày ở Bảng 6.1. Độ lệch chuẩn trong bảng là độ biến động của best CV accuracy giữa ba lần chạy có seed khác nhau.")
    method_rows=[]
    for _, row in method_summary.iterrows():
        method_rows.append([
            row["method"],
            f"{row['best_cv_accuracy_mean']:.4f}",
            f"{row['best_cv_accuracy_std']:.4f}",
            f"{row['search_time_mean_sec']:.2f}",
            f"{int(row['total_evaluations'])}",
        ])
    add_table(doc,
        ["Phương pháp", "Best CV mean", "Std", "Thời gian / seed (s)", "Tổng trial"],
        method_rows, widths=[3.1, 2.6, 1.8, 3.5, 2.0], font_size=8.6,
    )
    add_caption(doc, "Bảng 6.1. So sánh HPO theo cùng evaluation budget.")
    add_para(doc,
        "Grid Search và Random Search cùng đạt 0,9648 ± 0,0022. Hai phương pháp đã xét cùng 24 cấu hình nên cùng tìm được kết quả tốt nhất ở mỗi seed. Optuna/TPE đạt 0,9641 ± 0,0025; mức chênh lệch nhỏ và không đủ cơ sở để kết luận TPE kém hơn nói chung. Trong không gian nhỏ, TPE có thể lặp lại một số cấu hình đã thử và chưa tận dụng hết các trial để mở rộng vùng tìm kiếm.")
    add_picture(doc, FIGURES / "01_best_so_far.png", width=6.1)
    add_caption(doc, "Hình 6.1. Best-so-far CV accuracy theo số trial; vùng tô thể hiện độ biến động giữa các seed.")
    add_picture(doc, FIGURES / "04_method_comparison.png", width=5.2)
    add_caption(doc, "Hình 6.2. Best CV accuracy trung bình của Grid, Random và TPE.")

    add_page_break(doc)

    # --------- 6. RESULTS PAGE 2 ---------
    h2 = add_heading(doc, "6.2. NSGA-II và Pareto front", 2)
    add_bookmark(h2, "s62", 10)
    add_para(doc,
        f"NSGA-II được chạy với 20 trial và population size 10. Trong lần thực nghiệm này, có {len(pareto)} trial không bị dominate. Các điểm này đại diện cho nhiều cách đánh đổi giữa độ chính xác, độ trễ và độ phức tạp; không có điểm nào tốt hơn tất cả điểm còn lại ở cả ba mục tiêu.")
    pareto_rows=[]
    for _, row in pareto.sort_values("trial").iterrows():
        mark = "Knee" if int(row["trial"]) == int(knee["trial"]) else ""
        pareto_rows.append([
            int(row["trial"]),
            f"{row['cv_accuracy']:.4f}",
            f"{row['latency_median_ms']:.3f}",
            f"{int(row['total_nodes']):,}",
            mark,
        ])
    add_table(doc,
        ["Trial", "CV accuracy", "Median latency (ms)", "Total nodes", "Ghi chú"],
        pareto_rows, widths=[1.6, 2.6, 3.4, 2.7, 2.3], font_size=8.7,
    )
    add_caption(doc, "Bảng 6.2. Sáu nghiệm non-dominated thu được từ NSGA-II.")
    add_para(doc,
        f"Theo quy tắc đã xác định trước, trial {knee['trial']} được chọn làm knee: CV accuracy = {knee['cv_accuracy']:.4f}, median latency = {knee['latency_median_ms']:.3f} ms/mẫu và tổng số node = {knee['total_nodes']:,}. Điểm này không có accuracy cao nhất trong front, nhưng nằm gần điểm lý tưởng hơn sau khi chuẩn hóa các mục tiêu.")
    add_picture(doc, FIGURES / "02_pareto_accuracy_latency.png", width=5.75)
    add_caption(doc, "Hình 6.3. Quan hệ đánh đổi giữa CV accuracy và median inference latency.")
    add_picture(doc, FIGURES / "03_pareto_accuracy_complexity.png", width=5.75)
    add_caption(doc, "Hình 6.4. Quan hệ đánh đổi giữa CV accuracy và tổng số node.")

    add_page_break(doc)

    # --------- 6. RESULTS PAGE 3 ---------
    h2 = add_heading(doc, "6.3. Đánh giá cuối trên test set", 2)
    add_bookmark(h2, "s63", 11)
    add_para(doc,
        "Sau khi chốt baseline, cấu hình HPO có CV accuracy cao nhất và nghiệm knee của NSGA-II bằng development CV/Pareto front, ba mô hình được fit lại trên toàn bộ development set. Test set gồm 114 mẫu được dùng ở bước đánh giá cuối. Các metric này không được dùng để quay lại điều chỉnh hyperparameter.")
    metric_rows=[]
    for _, row in final_metrics.iterrows():
        metric_rows.append([
            row["model"],
            f"{row['test_accuracy']:.4f}",
            f"{row['test_f1']:.4f}",
            f"{row['latency_median_ms']:.3f}",
            f"{row['latency_p95_ms']:.3f}",
            f"{int(row['total_nodes']):,}",
            f"{row['model_size_mb']:.3f}",
        ])
    add_table(doc,
        ["Mô hình", "Accuracy", "F1", "Median ms", "P95 ms", "Nodes", "Size MB"],
        metric_rows, widths=[3.4, 1.5, 1.2, 1.8, 1.6, 1.5, 1.4], font_size=7.7,
    )
    add_caption(doc, "Bảng 6.3. Kết quả test và các chỉ số triển khai của ba cấu hình đã chốt.")

    h3 = add_heading(doc, "Nhận xét từ kết quả", 2)
    add_para(doc,
        "Cấu hình HPO có CV accuracy tốt nhất đạt test accuracy 0,9561, bằng baseline. Tuy nhiên, thời gian dự đoán median giảm từ 4,244 ms xuống 1,785 ms; tổng node giảm từ 3.556 xuống 1.392 và file model giảm từ 0,309 MB xuống 0,122 MB. Như vậy tuning không chỉ cải thiện điểm CV mà còn tìm được một cấu hình gọn hơn trong lần chạy này.")
    add_para(doc,
        "Nghiệm knee đạt test accuracy 0,9474, thấp hơn baseline khoảng 0,0088, nhưng có median latency 0,970 ms, tổng node 552 và dung lượng 0,051 MB. Đây là phương án phù hợp hơn khi tốc độ và độ gọn được ưu tiên, với điều kiện mức accuracy đó đáp ứng yêu cầu của ứng dụng. Không nên dùng kết quả này cho chẩn đoán y khoa; dataset chỉ là benchmark học tập.")
    add_para(doc,
        "Các phép đo latency là đo inference cho một mẫu, sau warm-up và lặp lại trên môi trường chạy hiện tại. Kết quả có thể thay đổi theo CPU, hệ điều hành, tải nền, batch size và cách triển khai. Khi chuyển sang thiết bị Edge hoặc hệ thống real-time, cần benchmark lại bằng workload thực tế và theo dõi cả p95/p99.")

    add_page_break(doc)

    # --------- 7. DISCUSSION ---------
    h = add_heading(doc, "7. THẢO LUẬN VÀ QUYẾT ĐỊNH TRIỂN KHAI", 1)
    add_bookmark(h, "s7", 12)
    add_heading(doc, "7.1. Chọn mô hình theo bối cảnh", 2)
    add_table(doc,
        ["Bối cảnh", "Ưu tiên", "Cấu hình nên xem xét"],
        [
            ["Cloud / batch", "Accuracy và throughput", "Best HPO; chấp nhận mô hình lớn hơn nếu chi phí phù hợp"],
            ["Edge / thiết bị hạn chế", "Latency, RAM, model size", "Pareto knee nếu accuracy 0,9474 đáp ứng yêu cầu"],
            ["Real-time", "Latency p95/p99 và ổn định", "Chỉ quyết định sau benchmark trên đúng thiết bị và workload"],
        ], widths=[3.0, 4.0, 7.0], font_size=8.6,
    )
    add_para(doc,
        "Pareto front không tự đưa ra một mô hình cuối cùng. Với nhu cầu accuracy-first, best HPO có kết quả test tương đương baseline nhưng chi phí thấp hơn. Với thiết bị cần giảm dung lượng và phản hồi nhanh, nghiệm knee là ứng viên đáng thử, nhưng cần đặt ngưỡng accuracy tối thiểu theo yêu cầu thực tế trước khi triển khai.")
    add_heading(doc, "7.2. Vì sao các phương pháp cho kết quả như vậy?", 2)
    add_para(doc,
        "Grid và Random cho kết quả bằng nhau vì search space chỉ có 24 cấu hình và Random Search được cấp đúng 24 lần lấy mẫu, tức đã thử hết các cấu hình. Đây là một ví dụ cụ thể cho thấy cần đọc kỹ miền tìm kiếm và budget trước khi so sánh thuật toán. TPE sử dụng lịch sử trial nhưng search space categorical nhỏ; khi budget không lớn, việc lặp cấu hình có thể làm giảm số điểm mới được khám phá.")
    add_para(doc,
        "NSGA-II tạo được sáu nghiệm non-dominated trong 20 trial, cho thấy có nhiều cấu hình đánh đổi. Tuy nhiên, 20 trial là ngân sách thăm dò; front có thể thay đổi khi tăng population, số generation, mở rộng search space hoặc lặp seed. Kết quả này nên được xem là Pareto front xấp xỉ của một thực nghiệm nhỏ.")
    add_heading(doc, "7.3. Hạn chế", 2)
    for item in [
        "Chỉ sử dụng một dataset benchmark nhỏ và một cách chia development/test; nested CV chưa được triển khai.",
        "Search space đơn mục tiêu được giới hạn ở 24 cấu hình và số cây 20/40/60 để giữ chi phí chạy phù hợp với đồ án cá nhân. Đây không phải miền tham số tối ưu cho mọi Random Forest.",
        "NSGA-II chỉ có 20 trial; số nghiệm Pareto chưa đủ để khẳng định đã bao phủ toàn bộ trade-off có thể có.",
        "Latency đo batch một mẫu trên máy chạy thí nghiệm; chưa đo điện năng, RAM đỉnh, throughput batch hoặc độ trễ trên thiết bị Edge thực tế.",
        "Dataset y tế chỉ dùng minh họa kỹ thuật; kết quả không có ý nghĩa chẩn đoán hoặc thay thế ý kiến chuyên môn."
    ]:
        add_bullet(doc, item)
    add_heading(doc, "7.4. Hướng hoàn thiện", 2)
    add_para(doc,
        "Có thể mở rộng miền n_estimators, max_depth và min_samples_leaf; tăng số trial NSGA-II; lặp nhiều seed cho multi-objective; bổ sung nested CV khi cần ước lượng generalization khách quan hơn; đo p95/p99, RAM và throughput trên máy đích. Những bước này nên thực hiện khi có thêm budget và yêu cầu triển khai cụ thể.")

    add_page_break(doc)

    # --------- 8. CONCLUSION ---------
    h = add_heading(doc, "8. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", 1)
    add_bookmark(h, "s8", 13)
    add_para(doc,
        "Đồ án đã triển khai một quy trình HPO và tối ưu đa mục tiêu hoàn chỉnh ở quy mô nhập môn: mô tả biến quyết định và hàm mục tiêu; xây dựng baseline; tách development/test; so sánh Grid Search, Random Search và Optuna/TPE theo cùng evaluation budget; dùng NSGA-II tìm nghiệm non-dominated; lưu lịch sử chạy và đánh giá các cấu hình đã chốt.")
    add_para(doc,
        "Trong thí nghiệm đơn mục tiêu, Grid Search và Random Search cùng đạt best CV accuracy trung bình 0,9648, cao hơn baseline 0,9597. Optuna/TPE đạt 0,9641. Trên test set, cấu hình HPO tốt nhất đạt accuracy 0,9561 như baseline nhưng có latency, số node và dung lượng file thấp hơn. Nghiệm Pareto knee giảm thêm latency và complexity, đổi lại accuracy giảm xuống 0,9474.")
    add_para(doc,
        "Kết luận quan trọng nhất là việc chọn mô hình cần dựa trên nhiều tiêu chí. Nếu chỉ nhìn accuracy, ta có thể bỏ qua chi phí vận hành. Nếu chỉ chọn mô hình nhanh nhất, độ chính xác có thể không còn phù hợp. Pareto front làm rõ phần đánh đổi, còn yêu cầu của hệ thống mới quyết định nghiệm nào nên được dùng.")
    add_para(doc,
        "Về mặt học tập, đồ án giúp minh họa sự khác nhau giữa parameter và hyperparameter, cách thiết kế search space, vai trò của validation/test, TPE, Optuna Study/Trial, dominance và Pareto optimality. Repository đi kèm có mã nguồn, notebook phân tích, file CSV/SQLite, hình vẽ và các mô hình đã fit, giúp người đọc kiểm tra kết quả thay vì chỉ dựa vào một con số trong báo cáo.")
    add_heading(doc, "Quyết định cuối cùng", 2)
    add_para(doc,
        "Với dữ liệu và protocol hiện tại, best HPO là lựa chọn cân bằng khi cần giữ test accuracy ngang baseline nhưng giảm chi phí mô hình. Pareto knee là lựa chọn tham khảo cho kịch bản ưu tiên tốc độ và dung lượng, với điều kiện ngưỡng accuracy tối thiểu được chấp nhận. Không có một mô hình thắng tuyệt đối cho mọi bối cảnh.")

    add_page_break(doc)

    # --------- REFERENCES ---------
    h = add_heading(doc, "TÀI LIỆU THAM KHẢO", 1)
    add_bookmark(h, "refs", 14)
    refs = [
        "[1] Trường Đại học Văn Lang, Khoa Công nghệ thông tin. Tài liệu học tập Nhập môn Tối ưu hóa - Chương 6: Hyperparameter Optimization và tối ưu đa mục tiêu trong AI, 29 trang.",
        "[2] Trường Đại học Văn Lang, Khoa Công nghệ thông tin. Hướng dẫn phạm vi đề bài tập lớn cá nhân - Nhập môn Tối ưu hóa, 5 trang.",
        "[3] Trường Đại học Văn Lang, Khoa Công nghệ thông tin. Bài tập lớn cá nhân - Nhập môn Tối ưu hóa, thời gian thực hiện 05 tuần, 6 trang.",
        "[4] Bergstra, J., & Bengio, Y. (2012). Random Search for Hyper-Parameter Optimization. Journal of Machine Learning Research, 13, 281-305.",
        "[5] Snoek, J., Larochelle, H., & Adams, R. P. (2012). Practical Bayesian Optimization of Machine Learning Algorithms. NeurIPS.",
        "[6] Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A Next-generation Hyperparameter Optimization Framework. KDD.",
        "[7] Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II. IEEE Transactions on Evolutionary Computation.",
        "[8] Scikit-learn User Guide. Dataset loading utilities; model selection and cross-validation; tuning the hyperparameters of an estimator.",
        "[9] Optuna Documentation. Efficient Optimization Algorithms; Pythonic Search Space; Multi-objective Optimization."
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.65)
        p.paragraph_format.first_line_indent = Cm(-0.65)
        p.paragraph_format.space_after = Pt(7)
        p.paragraph_format.line_spacing = 1.18
        set_font(p.add_run(ref), size=10.4)
    add_para(doc,
        "Các tài liệu [1]-[3] là ba PDF hướng dẫn được sử dụng làm cơ sở xác định phạm vi, nội dung và tiêu chí thực nghiệm của đồ án. Các tài liệu [4]-[9] được liệt kê theo phần tham khảo trong tài liệu Chương 6 và tài liệu kỹ thuật của các thư viện sử dụng.",
        first_indent=0, size=9.7, italic=True, color=GREY, before=8)

    add_page_break(doc)

    # --------- APPENDIX A ---------
    h = add_heading(doc, "PHỤ LỤC A. CÀI ĐẶT VÀ CHẠY CHƯƠNG TRÌNH", 1)
    add_bookmark(h, "appa", 15)
    add_heading(doc, "A.1. Cách chạy trên Windows", 2)
    add_para(doc,
        "Giải nén rf_hpo_pareto_optimization_project.zip vào một thư mục không dấu, ví dụ D:\\DoAnToiUuHoa. Máy cần cài Python 3.11 trở lên và có lệnh py trong PowerShell hoặc Command Prompt.")
    add_number(doc, "Mở thư mục dự án sau khi giải nén.")
    add_number(doc, "Nhấp đúp setup_windows.bat để tạo .venv và cài thư viện trong requirements.txt.")
    add_number(doc, "Sau khi cài xong, nhấp đúp run_windows.bat để chạy toàn bộ thí nghiệm.")
    add_number(doc, "Khi chương trình kết thúc, mở results/ để xem CSV/JSON/SQLite và figures/ để xem biểu đồ.")
    add_heading(doc, "A.2. Cách chạy bằng PowerShell", 2)
    add_code_box(doc,
        "py -3.11 -m venv .venv\n.venv\\Scripts\\activate\npython -m pip install --upgrade pip\npip install -r requirements.txt\npython run_project.py"
    )
    add_heading(doc, "A.3. Xem notebook", 2)
    add_code_box(doc,
        "pip install -r requirements-notebook.txt\njupyter notebook\n# Mở notebooks/01_hpo_pareto_walkthrough.ipynb"
    )
    add_heading(doc, "A.4. Những tệp nên mở khi thuyết trình", 2)
    add_table(doc,
        ["Tệp", "Nội dung"],
        [
            ["src/experiment.py", "Toàn bộ quy trình dữ liệu, CV, HPO, NSGA-II và Pareto."],
            ["results/cv_search_history.csv", "Lịch sử từng trial và best-so-far."],
            ["results/pareto_front.csv", "Danh sách nghiệm non-dominated."],
            ["results/final_model_metrics.csv", "Kết quả đánh giá cuối trên test set."],
            ["results/nsga2_study.db", "SQLite storage của Optuna Study."],
            ["figures/", "Các biểu đồ hỗ trợ giải thích convergence và trade-off."],
        ], widths=[5.3, 8.3], font_size=8.8,
    )
    add_heading(doc, "A.5. Hoàn thiện GitHub Portfolio trước khi nộp", 2)
    add_para(doc,
        "Repository chưa được xuất bản lên tài khoản GitHub của sinh viên trong phiên tạo bộ đồ án này. Trước khi nộp, cần tạo repository public, tải mã nguồn lên, bổ sung tối thiểu 5 commit có ý nghĩa theo tiến độ thực tế của 5 tuần và cập nhật đường dẫn GitHub tại đây. Không sử dụng URL giả hoặc tạo commit không phản ánh quá trình làm bài.", first_indent=0)
    add_para(doc, "URL GitHub: [Sinh viên bổ sung sau khi xuất bản repository public]", first_indent=0, italic=True)

    add_page_break(doc)

    # --------- APPENDIX B ---------
    h = add_heading(doc, "PHỤ LỤC B. GIẢI THÍCH NGẮN GỌN ĐỂ BẢO VỆ", 1)
    add_bookmark(h, "appb", 16)
    qa = [
        ("1. Đồ án đang tối ưu cái gì?", "Đồ án thay đổi bốn hyperparameter của Random Forest. Ở phần HPO đơn mục tiêu, mục tiêu là tăng mean accuracy của 5-fold CV. Ở phần đa mục tiêu, đồng thời tăng accuracy, giảm latency và giảm tổng số node."),
        ("2. Baseline để làm gì?", "Baseline là cấu hình mặc định, dùng làm mốc để biết tuning có cải thiện gì và có xứng đáng với chi phí tìm kiếm hay không."),
        ("3. Vì sao phải tách test set?", "Nếu dùng test để chọn hyperparameter thì test bị biến thành validation. Điểm số test cuối sẽ không còn là đánh giá độc lập."),
        ("4. Study và Trial khác nhau thế nào?", "Study là toàn bộ chiến dịch tối ưu; Trial là một lần thử một cấu hình cụ thể."),
        ("5. TPE hoạt động ra sao?", "TPE dùng lịch sử trial tốt và trial còn lại để ước lượng vùng hyperparameter có triển vọng, sau đó ưu tiên lấy mẫu ở vùng đó."),
        ("6. Dominance và Pareto front là gì?", "Một nghiệm dominate nghiệm khác nếu không kém ở mọi mục tiêu và tốt hơn ở ít nhất một mục tiêu. Pareto front gồm các nghiệm không bị nghiệm khác dominate."),
        ("7. Vì sao accuracy cao nhất chưa chắc được chọn?", "Mô hình accuracy cao hơn có thể lớn hoặc chậm hơn. Nếu chạy trên Edge hoặc real-time, latency và model size có thể quan trọng không kém."),
        ("8. Vì sao không dùng pruning?", "Trial Random Forest không sinh metric theo epoch. Không có intermediate metric phù hợp thì pruner không có tín hiệu đáng tin cậy để dừng sớm."),
    ]
    for question, answer in qa:
        add_heading(doc, question, 2)
        add_para(doc, answer, first_indent=0)
    add_heading(doc, "Một câu kết khi demo", 2)
    add_para(doc,
        "Điểm chính của đồ án không phải là tìm ra một con số accuracy cao nhất, mà là chứng minh cách lựa chọn mô hình bằng một quy trình tối ưu có baseline, budget, đánh giá công bằng và phân tích trade-off. Khi yêu cầu triển khai thay đổi, nghiệm được chọn cũng có thể thay đổi.",
        first_indent=0, italic=True)

    # Save
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Created: {OUT}")
    print(f"Tables: {len(doc.tables)}, paragraphs: {len(doc.paragraphs)}")


if __name__ == "__main__":
    main()
