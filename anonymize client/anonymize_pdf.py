# anonymize_pdf.py
#
# PDF khó ẩn danh tự động an toàn hơn hẳn DOCX/XLSX — sửa text bên trong PDF
# đòi hỏi viết lại content stream, dễ sót hoặc dễ vỡ file. Script này có 2 chế độ,
# CHỌN 1 TRONG 2, không chạy cả hai cùng lúc:
#
#   Chế độ 1 — detect (KHUYẾN NGHỊ DÙNG TRƯỚC):
#     python anonymize_pdf.py detect input.pdf
#     Chỉ DÒ và IN RA vị trí (trang, tọa độ) của từng tên/số liệu khớp với
#     NAME_MAP hoặc ngưỡng số liệu — không sửa gì cả. Bạn dùng kết quả này để
#     tự redact tay bằng Acrobat/Preview (chậm hơn nhưng chắc chắn không sót,
#     không có rủi ro tự động làm hỏng file).
#
#   Chế độ 2 — redact (TỰ ĐỘNG, CẦN TỰ KIỂM TRA LẠI KẾT QUẢ):
#     python anonymize_pdf.py redact input.pdf output_anonymized.pdf
#     Tự động vẽ khối che (redaction box) đè lên đúng vị trí từng match, có thể
#     kèm chữ thay thế đè lên trên. CẢNH BÁO: sau bước này, phần trang có redact
#     sẽ mất text layer gốc tại đúng vùng đó (bị "flatten" cục bộ) — nghĩa là
#     Geometry Layer khi test trên file này sẽ đọc vùng đó như PDF scan, không
#     phải PDF digital nữa. Chấp nhận được cho mục đích ẩn danh, nhưng cần biết
#     trước để không hiểu nhầm kết quả test Geometry Layer sau này.
#
# Cần cài thêm ngoài các package đã duyệt CRADL: `pdfplumber` (đang chờ duyệt,
# nhưng đây là script TIỆN ÍCH CÁ NHÂN chạy cục bộ để CHUẨN BỊ fixture, không
# phải một phần của sản phẩm Foundation — không nằm trong phạm vi CRADL áp dụng
# cho code sản phẩm. Vẫn nên xác nhận với IT nếu máy bạn có giới hạn cài pip
# package tùy ý.

import sys
import re
from anonymize_config import NAME_MAP, MIN_DIGITS_TO_ANONYMIZE


def _find_matches_on_page(page, targets):
    """Tìm mọi từ (word) trên trang khớp với danh sách targets (tên hoặc số),
    trả về list (text, bbox) — dùng chung cho cả 2 chế độ."""
    words = page.extract_words()
    matches = []
    full_text = page.extract_text() or ""
    for target in targets:
        if target in full_text:
            # Tìm word-level bbox gần đúng bằng cách quét cụm từ liên tiếp
            target_tokens = target.split()
            for i in range(len(words) - len(target_tokens) + 1):
                candidate = " ".join(w["text"] for w in words[i : i + len(target_tokens)])
                if candidate == target or target in candidate:
                    group = words[i : i + len(target_tokens)]
                    x0 = min(w["x0"] for w in group)
                    x1 = max(w["x1"] for w in group)
                    top = min(w["top"] for w in group)
                    bottom = max(w["bottom"] for w in group)
                    matches.append((target, (x0, top, x1, bottom)))
    return matches


def _find_number_matches_on_page(page):
    pattern = re.compile(
        r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d{"
        + str(MIN_DIGITS_TO_ANONYMIZE) + r",})(?![\d])"
    )
    matches = []
    for word in page.extract_words():
        if pattern.search(word["text"]):
            matches.append((word["text"], (word["x0"], word["top"], word["x1"], word["bottom"])))
    return matches


def detect(input_path: str):
    import pdfplumber

    real_names = list(NAME_MAP.keys())
    total = 0
    with pdfplumber.open(input_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            name_matches = _find_matches_on_page(page, real_names)
            number_matches = _find_number_matches_on_page(page)
            for text, bbox in name_matches:
                print(f"[Trang {page_num}] TÊN: {text!r} tại bbox={tuple(round(b, 1) for b in bbox)}")
                total += 1
            for text, bbox in number_matches:
                print(f"[Trang {page_num}] SỐ:  {text!r} tại bbox={tuple(round(b, 1) for b in bbox)}")
                total += 1
    print(f"\nTổng số vị trí cần xem lại: {total}")
    print("Dùng danh sách này để tự redact tay bằng Acrobat/Preview, hoặc chạy chế độ 'redact' để tự động.")


def redact(input_path: str, output_path: str):
    import pdfplumber
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas as rl_canvas
    from io import BytesIO
    from pypdf import Transformation

    real_names = list(NAME_MAP.keys())
    reader = PdfReader(input_path)
    writer = PdfWriter()

    with pdfplumber.open(input_path) as pdf:
        for page_num, (plumber_page, pypdf_page) in enumerate(zip(pdf.pages, reader.pages), start=1):
            matches = _find_matches_on_page(plumber_page, real_names) + _find_number_matches_on_page(plumber_page)

            if matches:
                page_w = float(pypdf_page.mediabox.width)
                page_h = float(pypdf_page.mediabox.height)
                buf = BytesIO()
                c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))
                c.setFillColorRGB(1, 1, 1)  # khối che màu trắng
                for text, (x0, top, x1, bottom) in matches:
                    # pdfplumber tọa độ gốc trên-trái, reportlab gốc dưới-trái — cần đổi trục Y
                    y0 = page_h - bottom
                    y1 = page_h - top
                    c.rect(x0 - 1, y0 - 1, (x1 - x0) + 2, (y1 - y0) + 2, fill=1, stroke=0)
                c.save()
                buf.seek(0)
                overlay_reader = PdfReader(buf)
                pypdf_page.merge_page(overlay_reader.pages[0])
                print(f"[Trang {page_num}] đã che {len(matches)} vị trí")

            writer.add_page(pypdf_page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"\nĐã ẩn danh: {input_path} -> {output_path}")
    print("⚠️  BẮT BUỘC tự mở file output và kiểm tra lại bằng mắt trước khi dùng —")
    print("    script này che bằng khối trắng đè lên, không xóa hẳn text gốc khỏi")
    print("    content stream. Nếu cần chắc chắn tuyệt đối, nên dùng chế độ 'detect'")
    print("    và redact tay bằng công cụ PDF chuyên dụng (Acrobat Redact Tool).")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Dùng: python anonymize_pdf.py detect input.pdf")
        print("  hoặc: python anonymize_pdf.py redact input.pdf output_anonymized.pdf")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "detect":
        detect(sys.argv[2])
    elif mode == "redact":
        if len(sys.argv) != 4:
            print("Dùng: python anonymize_pdf.py redact input.pdf output_anonymized.pdf")
            sys.exit(1)
        redact(sys.argv[2], sys.argv[3])
    else:
        print("Chế độ không hợp lệ — chỉ nhận 'detect' hoặc 'redact'")
        sys.exit(1)
