# Bộ script ẩn danh fixture — chạy CỤC BỘ trên máy bạn

**Nguyên tắc quan trọng nhất: không có file thật nào rời khỏi máy bạn khi chạy bộ
script này. Toàn bộ xử lý diễn ra local, không có network call.**

## Bước 1 — Cài đặt (chạy 1 lần)

```bash
pip install python-docx openpyxl pdfplumber pypdf reportlab
```

`python-docx` và `openpyxl` đã nằm trong danh sách CRADL đã duyệt (đúng thư viện
Foundation đang dùng). `pdfplumber`, `pypdf`, `reportlab` chỉ dùng cho **script tiện
ích cá nhân này** để chuẩn bị fixture — không phải một phần của sản phẩm Foundation,
nên không thuộc phạm vi CRADL áp dụng cho code sản phẩm. Nếu máy bạn giới hạn cài pip
package, xác nhận với IT trước.

## Bước 2 — Điền danh sách tên thật cần ẩn danh

Mở `anonymize_config.py`, điền `NAME_MAP` với **mọi biến thể cách viết** của tên
client/đối tác/người liên quan xuất hiện trong 23 file — đặt tên dài/cụ thể lên trước.

## Bước 3 — Chạy hàng loạt

```bash
python run_all.py /đường/dẫn/folder_23_file /đường/dẫn/folder_output
```

- DOCX, XLSX → tự động ẩn danh hoàn toàn, xuất thẳng ra `folder_output`.
- PDF → chỉ **dò và báo cáo vị trí** (an toàn), chưa tự sửa. Đọc kết quả in ra màn
  hình, dùng nó để tự redact tay bằng Acrobat/Preview cho từng file PDF.

## Nếu muốn PDF tự động redact thay vì tự redact tay (nhanh hơn, rủi ro cao hơn)

```bash
python anonymize_pdf.py redact input.pdf output_anonymized.pdf
```

**Bắt buộc tự mở lại file output và kiểm tra bằng mắt** trước khi dùng làm fixture —
đây là bước tự động, không đảm bảo tuyệt đối không sót, đặc biệt với PDF có font/encoding
đặc biệt.

## Sau khi xong

1. Mở lại **toàn bộ** 23 file đã ẩn danh, tự kiểm tra bằng mắt — đặc biệt các bảng,
   header/footer, và ghi chú (comment) nếu có (script hiện KHÔNG xử lý comment trong
   DOCX — nếu file có comment, cần kiểm tra riêng).
2. Xác nhận số liệu tài chính đã đổi (không còn số thật), nhưng **định dạng giữ nguyên**
   (số chữ số, dấu phân cách) — để vẫn dùng được cho việc test parser.
3. Kiểm tra file XLSX: mở bằng Excel, các ô công thức phải tự tính lại đúng theo số liệu
   giả (vì script không đụng công thức, chỉ đụng input value).
4. Chỉ sau khi kiểm tra xong mới đưa vào source code / Claude Code / bất kỳ công cụ nào khác.

## Giới hạn đã biết — đọc trước khi dùng

- Script không xử lý: text box tự do trong DOCX (WordArt, shape có chữ), comment/track-changes,
  metadata file (Author, Company trong Properties — cần xóa riêng qua File > Info > Ẩn danh
  trong Word/Excel).
- Chế độ PDF `redact` làm mất text layer tại đúng vùng bị che — Geometry Layer khi test
  trên các vùng đó sẽ đọc như PDF scan, không phải digital nữa. Vùng còn lại của trang
  vẫn giữ nguyên text layer thật.
- Số liệu giả sinh ra tất định theo hash — chạy lại script nhiều lần trên cùng file gốc
  sẽ luôn ra cùng 1 kết quả, không đổi mỗi lần chạy.
