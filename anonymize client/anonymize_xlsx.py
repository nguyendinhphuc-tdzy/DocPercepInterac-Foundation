# anonymize_xlsx.py
# Dùng: python anonymize_xlsx.py input.xlsx output_anonymized.xlsx
#
# Chạy CỤC BỘ trên máy bạn. Chỉ dùng openpyxl (đã duyệt CRADL).
#
# QUAN TRỌNG: script CHỦ ĐỘNG BỎ QUA các ô có công thức (formula) — không đụng
# vào công thức, chỉ thay giá trị nhập tay (hardcoded value). Lý do: nếu 1 ô là
# công thức tính từ ô khác, và ô khác đó đã được ẩn danh, Excel sẽ TỰ ĐỘNG tính
# lại đúng số liệu giả nhất quán khi mở file — không cần script tự tính lại.

import sys
import openpyxl
from anonymize_common import anonymize_text


def anonymize_xlsx(input_path: str, output_path: str):
    wb = openpyxl.load_workbook(input_path, data_only=False)  # giữ formula, không giữ cached value

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                # Bỏ qua ô công thức — để Excel tự tính lại khi mở, không phá công thức
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    continue
                if isinstance(cell.value, str):
                    cell.value = anonymize_text(cell.value)
                elif isinstance(cell.value, (int, float)):
                    # Số trong ô Excel — thay bằng cùng logic số giả tất định,
                    # áp dụng qua chuỗi rồi convert lại đúng kiểu gốc
                    original_str = str(cell.value)
                    fake_str = anonymize_text(original_str)
                    try:
                        cell.value = type(cell.value)(fake_str) if fake_str != original_str else cell.value
                    except ValueError:
                        pass  # không convert được thì giữ nguyên, an toàn hơn là làm hỏng ô

        # Merged cells, named ranges — KHÔNG cần xử lý gì thêm, openpyxl tự giữ
        # nguyên cấu trúc merge khi save, không bị mất khi ta chỉ sửa .value

    wb.save(output_path)
    print(f"Đã ẩn danh: {input_path} -> {output_path}")
    print("Lưu ý: các ô công thức đã được GIỮ NGUYÊN — mở file bằng Excel để nó tự tính lại giá trị.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Dùng: python anonymize_xlsx.py input.xlsx output_anonymized.xlsx")
        sys.exit(1)
    anonymize_xlsx(sys.argv[1], sys.argv[2])
