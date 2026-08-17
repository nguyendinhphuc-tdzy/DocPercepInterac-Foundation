# run_all.py
# Dùng: python run_all.py /đường/dẫn/folder_goc /đường/dẫn/folder_output
#
# Tự động quét folder gốc, chạy đúng script theo từng định dạng, xuất ra folder_output
# với cùng tên file (thêm hậu tố "_anon"). PDF chỉ chạy chế độ 'detect' (an toàn) —
# không tự động redact hàng loạt, vì PDF cần bạn xác nhận tay từng vị trí trước.

import sys
import shutil
from pathlib import Path

from anonymize_docx import anonymize_docx
from anonymize_xlsx import anonymize_xlsx
from anonymize_pdf import detect as pdf_detect


def run_all(src_dir: str, out_dir: str):
    src = Path(src_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    docx_files = list(src.glob("*.docx"))
    xlsx_files = list(src.glob("*.xlsx"))
    pdf_files = list(src.glob("*.pdf"))

    print(f"Tìm thấy: {len(docx_files)} DOCX, {len(xlsx_files)} XLSX, {len(pdf_files)} PDF\n")

    for f in docx_files:
        out_path = out / f"{f.stem}_anon.docx"
        anonymize_docx(str(f), str(out_path))

    for f in xlsx_files:
        out_path = out / f"{f.stem}_anon.xlsx"
        anonymize_xlsx(str(f), str(out_path))

    print("\n--- PDF: chỉ chạy chế độ DETECT (an toàn) — xem báo cáo bên dưới, tự redact tay ---")
    for f in pdf_files:
        print(f"\n=== {f.name} ===")
        pdf_detect(str(f))
        # copy nguyên file gốc sang out_dir kèm hậu tố "_CẦN_REDACT_TAY" để không
        # nhầm với file đã xử lý xong
        shutil.copy(f, out / f"{f.stem}_CẦN_REDACT_TAY.pdf")

    print(f"\nXong. Kết quả nằm ở: {out.resolve()}")
    print("PDF cần bạn tự redact tay theo báo cáo detect ở trên trước khi dùng làm fixture.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Dùng: python run_all.py /đường/dẫn/folder_goc /đường/dẫn/folder_output")
        sys.exit(1)
    run_all(sys.argv[1], sys.argv[2])
