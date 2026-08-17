# anonymize_config.py
# ĐIỀN TAY danh sách tên thật cần thay thế — KHÔNG tự động dò tên bằng NLP/model.
# Lý do: tự động dò tên (NER) cần một model đã train sẵn — đúng loại "model bên ngoài"
# mà cả dự án Foundation đang tránh dùng. Điền tay chậm hơn nhưng an toàn và chắc chắn
# không sót tên nào bạn không kiểm soát được.
#
# QUY TẮC:
# - Liệt kê MỌI biến thể cách viết của cùng 1 thực thể (có dấu / không dấu, viết tắt,
#   "Công ty TNHH X" và chỉ "X"...) — script chỉ thay đúng chuỗi bạn liệt kê ra.
# - Tên giả phải nhất quán — dùng đúng 1 tên giả cho mỗi thực thể xuyên suốt cả 23 file.
# - Thứ tự trong danh sách quan trọng: đặt tên DÀI/CỤ THỂ hơn lên TRƯỚC tên ngắn, để
#   tránh thay nhầm một phần của chuỗi dài hơn.

# Ví dụ mẫu — XÓA và điền dữ liệu thật của bạn vào đây:
NAME_MAP = {
    "HESTRA Matsuoka Vietnam LLC": "Công ty TNHH Alpha Việt Nam",
    "HESTRA Hungary Kft": "HS Hungary",
    "HESTRA": "Công ty Alpha",
    "Eurogane Universal Ltd": "EU Ltd",
    "Zhejang Pinghu Huashen Leather Co., Ltd": "ZPH Leather",
    "Martin Magnusson & Co AB": "MM & Co",
    "HESTRA Handschuhe GmbH": "HS Handschuhe",
    "HESTRA Cambodia AB" : "HS Cambodia",
    "Martin Magnusson HK Ltd": "MM HK",
    "AB Hugo Nordstrom": "ABH Nordstrom",
    "HESTRA Finland Oy": "HS Finland",
    "HESTRA Norge AS": "HS Norge",
    "HESTRA Danmark ApS": "HS Danmark",
    "Guang Zhou Chon Hing Glove Enterprise Ltd": "GZCHGlove Enterprise",
    "HESTRA Gloves LLC USA": "HSGloves USA",
    
    
    # "0123456789": "0000000001",   # mã số thuế nếu có xuất hiện dạng text
}

# Ngưỡng để coi một dãy số là "số liệu tài chính cần ẩn danh" — KHÔNG áp dụng cho
# năm (2023/2024/2025), số trang, số mục (4.1, 4.2...). Mặc định: số có từ 6 chữ số
# trở lên (phù hợp quy mô doanh thu/lợi nhuận tính bằng VND), hoặc số có dấu phân
# cách hàng nghìn (1,234,567 hoặc 1.234.567).
MIN_DIGITS_TO_ANONYMIZE = 6

# Seed cố định — đảm bảo chạy lại nhiều lần vẫn ra cùng 1 kết quả (reproducible),
# và cùng 1 số liệu thật luôn map ra cùng 1 số liệu giả xuyên suốt các file
# (giữ tính đối chiếu chéo được giữa các file khi bạn test).
RANDOM_SEED = 42
