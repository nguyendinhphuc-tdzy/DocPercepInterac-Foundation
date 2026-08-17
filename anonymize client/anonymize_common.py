# anonymize_common.py
# Logic dùng chung cho cả 3 script DOCX/XLSX/PDF — không tự chạy file này trực tiếp.

import re
import hashlib
from anonymize_config import NAME_MAP, MIN_DIGITS_TO_ANONYMIZE, RANDOM_SEED

# Sắp danh sách tên theo độ dài giảm dần — thay tên DÀI trước để tránh thay nhầm
# một phần của chuỗi dài hơn (vd: thay "ABC" trước "Công ty ABC" sẽ làm hỏng kết quả).
_SORTED_NAMES = sorted(NAME_MAP.keys(), key=len, reverse=True)

# Regex bắt số có định dạng tài chính: có dấu phân cách hàng nghìn, có thể có phần
# thập phân. Bắt cả kiểu 1,234,567 / 1.234.567 / 1234567 (tối thiểu MIN_DIGITS_TO_ANONYMIZE
# chữ số liên tục nếu không có dấu phân cách).
_NUMBER_PATTERN = re.compile(
    r"(?<![\d.,])"
    r"(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d{" + str(MIN_DIGITS_TO_ANONYMIZE) + r",})"
    r"(?![\d])"
)


def replace_names(text: str) -> str:
    """Thay toàn bộ tên thật bằng tên giả theo NAME_MAP, tên dài trước."""
    if not text:
        return text
    for real_name in _SORTED_NAMES:
        fake_name = NAME_MAP[real_name]
        text = text.replace(real_name, fake_name)
    return text


def _deterministic_fake_number(original_digits: str) -> str:
    """Sinh số giả CÙNG SỐ LƯỢNG CHỮ SỐ, tất định theo hash (seed cố định) —
    cùng 1 số thật luôn ra cùng 1 số giả, giữ đối chiếu chéo được giữa các file,
    và chạy lại nhiều lần vẫn ra kết quả giống nhau (reproducible)."""
    h = hashlib.sha256(f"{RANDOM_SEED}:{original_digits}".encode()).hexdigest()
    # Lấy đủ chữ số từ hash, giữ chữ số đầu khác 0 (không đổi độ lớn của số)
    digits = "".join(c for c in h if c.isdigit())
    while len(digits) < len(original_digits):
        digits += digits
    result = digits[: len(original_digits)]
    if result[0] == "0":
        result = str(int(digits[0]) % 9 + 1) + result[1:]
    return result


def replace_numbers(text: str) -> str:
    """Thay số liệu tài chính (đủ ngưỡng chữ số) bằng số giả cùng định dạng
    (giữ nguyên dấu phân cách, số chữ số, phần thập phân). KHÔNG đụng tới số
    nhỏ hơn ngưỡng (năm, số mục, số trang...)."""
    if not text:
        return text

    def _sub(match):
        original = match.group(0)
        digits_only = re.sub(r"[.,]", "", original)
        # bỏ qua nếu sau khi loại dấu phân cách vẫn dưới ngưỡng (dấu chấm thập phân)
        if len(digits_only) < MIN_DIGITS_TO_ANONYMIZE and "," not in original and "." not in original[:-3]:
            return original
        fake_digits = _deterministic_fake_number(digits_only)
        # ghép lại đúng vị trí dấu phân cách/thập phân như bản gốc
        out, di = [], 0
        for ch in original:
            if ch.isdigit():
                out.append(fake_digits[di] if di < len(fake_digits) else fake_digits[-1])
                di += 1
            else:
                out.append(ch)
        return "".join(out)

    return _NUMBER_PATTERN.sub(_sub, text)


def anonymize_text(text: str) -> str:
    """Áp dụng cả 2 bước: thay tên trước, thay số sau."""
    return replace_numbers(replace_names(text))
