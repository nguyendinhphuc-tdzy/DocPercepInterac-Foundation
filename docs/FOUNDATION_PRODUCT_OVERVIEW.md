# Foundation Product Overview

> Vai trò tài liệu: Product/Business overview cấp cao của Foundation. Tài liệu này mô tả problem, product logic, stakeholder direction, technology direction, current state và MVP scope. Nếu có xung đột về architecture hoặc contract, ưu tiên `docs/CURRENT_BASELINE.md`, accepted ADRs và Frozen Foundation Contract v0.1 theo `AGENTS.md`.

**FOUNDATION  |  Xử lý và chuyển đổi tài liệu có kiểm soát**

**Business Problem \- Product Logic \- Technology Direction \- MVP Scope**

**Định vị sản phẩm**

Foundation không phải AI Agent tự đọc rồi tự sửa tài liệu, và cũng không phải solution riêng cho Local File. Foundation là lớp xử lý tài liệu dùng chung để trích xuất dữ liệu, hiểu cấu trúc, áp business logic, tạo hoặc cập nhật output có kiểm soát, và giữ đầy đủ evidence, audit và validation. Local File là use case đại diện để stress-test các capability khó, không phải giới hạn của foundation.  
   
**WHY**  
**1\. Business Problem và pain point cốt lõi**

- Đối với đa số các function ở KPMG Vietnam, phần lớn các tác vụ đều liên quan đến Document Processing, và đây cũng là một trong những bước quan trọng nhất, ảnh hưởng đến nhiều các process về sau.  
- Và các nhân sự đều đang áp dụng AI tools/Copilot trong quá trình xử lý dữ liệu  
- Tuy nhiên, năng lực của các agent/tools hiện tại (Digital Gateway/ Copilot) chưa đáp ứng được về độ hoàn thiện cao trong Document Processing.

Vấn đề không nằm ở việc AI có đọc hay viết được text hay không, mà ở việc kết quả có đủ căn cứ, đúng vị trí, giữ đúng format và audit được hay không.

| Nhóm vấn đề | Pain point chung | Business impact |
| :---- | :---- | :---- |
| **Extraction** | Tài liệu khác format và cấu trúc; giá trị có thể nằm trong paragraph, table, formula hoặc nhiều source. Extraction thường mất nguồn hoặc business context. | Sai dữ liệu, reviewer phải đọc lại file gốc, khó chứng minh “giá trị này đến từ đâu”. |
| **Generation** | AI hoặc script có thể tạo đúng nội dung nhưng sửa nhầm vùng, phá format, bỏ sót nguồn chéo hoặc thay đổi ngoài scope. | Khối lượng xử lý lại cao, kết quả đầu ra thiếu độ tin cậy và khó sử dụng cho hồ sơ khách hàng hoặc các công việc có yêu cầu kiểm soát chặt chẽ. |
| **Evidence & Decision** | Có nguồn không đồng nghĩa nguồn đủ thẩm quyền; nhiều nguồn có thể xung đột/không chắc chắn/bị thiếu. | Chấp nhận kết quả sai hoặc tự động điền thông tin không chính xác khi chưa có đủ căn cứ. |
| **Operations** | Một thay đổi nhỏ thường buộc chạy lại hoặc review lại nhiều phần; trong khi đó trạng thái và cấu hình của document không được tái sử dụng tốt. | Thời gian xử lý kéo dài, mức độ sử dụng thấp và hiệu quả đầu tư suy giảm. |
| **AI / External tech** | Model/library có thể nhanh nhưng khó kiểm soát đầy đủ về nguồn gốc, bảo mật, licenses, thay đổi giữa các phiên bản và mức độ phụ thuộc vào vendor.  | Rủi ro về tuân thủ, vận hành và dependency dài hạn. |

 

**STAKEHOLDER INPUT**  
**2\. Insight đã thay đổi direction của Foundation**

**Từ anh Khang:** 

* Xây dựng một sản phẩm có cơ chế quản trị và audit rõ ràng, thay vì chỉ bổ sung AI vào quá trình chỉnh sửa tài liệu  
* Người dùng chỉ tập trung xử lý các ngoại lệ hoặc thay đổi cần đưa ra quyết định.   
* Khi các nguồn thông tin mâu thuẫn, hệ thống không được tự quyết định cách xử lý.   
* Khi chưa đủ căn cứ, hệ thống phải yêu cầu bổ sung nguồn hoặc chỉ đưa ra kết quả một phần trong phạm vi an toàn.   
* Khi nguồn dữ liệu hoặc cấu hình thay đổi, chỉ những phần bị ảnh hưởng mới được xử lý lại.   
* Đồng thời, mọi mô hình và công nghệ bên ngoài phải có khả năng truy vết và kiểm tra về nguồn gốc, bảo mật và tình trạng phê duyệt. 

**Từ hướng làm việc với anh Đạt:** 

* Tách phần lõi dùng chung của Foundation khỏi logic nghiệp vụ riêng của từng quy trình.   
* Các quy tắc xử lý và cấu hình mapping được quản lý theo từng quy trình và có kiểm soát phiên bản.   
* Ưu tiên xây dựng trước một luồng xử lý hoàn chỉnh, có quy tắc rõ ràng và tạo được kết quả đầu ra thực tế, trước khi mở rộng thêm các khả năng sử dụng AI.   
* Công nghệ bên ngoài chỉ được tiếp nhận hoặc điều chỉnh sau khi đã được đặt sau một lớp kết nối chuẩn. Không để bất kỳ thư viện riêng lẻ nào chi phối hoặc trở thành nền tảng của toàn bộ kiến trúc foundation. 

**Định hướng chung mới:** 

* Foundation dùng chung sẽ là hướng phát triển chính để chứng minh khả năng trích xuất thông tin và tạo đầu ra có kiểm soát.   
* Local File tiếp tục được sử dụng như một trường hợp kiểm chứng đại diện vì bài toán này bao gồm nhiều yếu tố phức tạp như tài liệu DOCX/XLSX, bảng biểu, công thức, mẫu tài liệu, thông tin mâu thuẫn và quy trình rà soát. 

 

**HOW**  
**3\. Product Logic tổng quát của Foundation**

* Foundation xử lý tài liệu theo từng mục tiêu nghiệp vụ hoặc nhu cầu thông tin cụ thể, thay vì xem toàn bộ tài liệu như một khối duy nhất.   
* Các cơ chế xử lý dùng chung được đặt tại phần lõi của Foundation, trong khi logic riêng của từng trường hợp sử dụng được xác định thông qua cấu hình quy trình, yêu cầu đối với từng nội dung cần xử lý và quy tắc ánh xạ dữ liệu.   
* AI chỉ được sử dụng để hỗ trợ những bước cần hiểu và diễn giải ý nghĩa nội dung, không có quyền tự thực hiện thay đổi hoặc đưa ra quyết định cuối cùng.

| 1\. Tiếp nhận & Quản lý phiên bản | 2\. Kiểm tra điều kiện xử lý | 3\. Nhận diện & Trích xuất | 4\. Workflow Profile | 5\. Căn cứ & Quyết định | 6\. Output & Kiểm tra |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Đăng ký file, role, hash, version | Khả năng đọc/xử lý an toàn | Cấu trúc, text, table, formula, provenance | Business target, rule, mapping, source requirement | Đánh giá mức độ đầy đủ của căn cứ, mâu thuẫn, trường hợp cần AI hỗ trợ và quyết định của người dùng  | Phạm vi đã phê duyệt → tạo hoặc áp dụng thay đổi có kiểm soát → kiểm tra kết quả |

**Nguyên tắc phân quyền xử lý:** 

* Nhận diện thông tin không đồng nghĩa với có đủ căn cứ, có đủ căn cứ không đồng nghĩa với được phê duyệt, và được phê duyệt cũng không đồng nghĩa với được phép thực hiện thay đổi.   
* Chỉ những nội dung đã được kiểm tra theo căn cứ và quy tắc, được người rà soát phê duyệt, đồng thời các điều kiện liên quan vẫn còn hiệu lực, mới được chuyển thành danh sách thay đổi đã được chấp thuận để tạo ra kết quả đầu ra.

**TECHNOLOGY → BUSINESS IMPACT**  
**4\. Technology direction**

| Năng lực / Công nghệ | Vai trò trong Foundation | Ý nghĩa đối với nghiệp vụ |
| :---- | :---- | :---- |
| **Kiểm tra tài liệu và định danh đối tượng theo cấu trúc OOXML**  | Đọc tài liệu DOCX/XLSX ở cấp cấu trúc và đối tượng; kiểm tra tính toàn vẹn, phiên bản, công thức và vị trí chính xác của từng thành phần. Dừng xử lý khi gặp trường hợp chưa được hỗ trợ.  | Giảm rủi ro hệ thống hiểu đúng nội dung nhưng thay đổi nhầm vị trí hoặc đối tượng; tạo nền tảng cho việc tạo và cập nhật tài liệu an toàn. |
| **Docling / Nhận diện ngữ nghĩa** | Công nghệ tiềm năng để chuẩn hóa cấu trúc và biểu diễn ý nghĩa của nội dung tài liệu. | Giảm chi phí tự xây dựng toàn bộ cơ chế phân tích ngữ nghĩa, nhưng phải được kiểm chứng trên các trường hợp đại diện trước khi đưa vào vận hành thực tế. |
| **Bộ máy quy tắc và kiểm tra Evidence.** | Kiểm tra vai trò và thẩm quyền của nguồn, kỳ dữ liệu, thông tin mâu thuẫn, các phần phụ thuộc và điều kiện trước hoặc sau khi xử lý. | Tăng khả năng audit và kiểm tra. Mức độ tin cậy do AI đưa ra không thể thay thế cho căn cứ thực tế. |
| **LLM / Lớp AI hỗ trợ hiểu ngữ nghĩa** | Hỗ trợ phân loại nội dung, mapping thông tin theo ý nghĩa, soạn thảo nội dung và giải thích các trường hợp chưa rõ trong phạm vi được giới hạn. | Tăng tốc những phần khó xử lý hoàn toàn bằng quy tắc, nhưng AI không được tự phê duyệt hoặc tự thay đổi tài liệu. |
| **Áp dụng thay đổi có kiểm soát** | Chỉ thực hiện đúng các thay đổi đã được phê duyệt, giới hạn tối đa phạm vi tác động, bảo vệ các phần không được phép thay đổi và có khả năng dừng hoặc hoàn tác khi có lỗi. | An toàn hơn so với tạo lại toàn bộ tài liệu. Kết quả chưa hoàn chỉnh nhưng an toàn được ưu tiên hơn kết quả đầy đủ nhưng làm sai hoặc hỏng tài liệu. |
| **Cấu hình quy trình và Mapping** | Đóng gói logic riêng của từng Use Case, có quản lý phiên bản và khả năng audit. Phần lõi dùng chung của Foundation không chứa các quy tắc riêng của GTPS. | Cho phép mở rộng sang các quy trình nghiệp vụ khác mà không phải tạo một Foundation riêng hoặc gắn cứng logic của từng lĩnh vực vào hệ thống. |

**Nguyên tắc sử dụng công nghệ bên ngoài**

Foundation có thể tham khảo hoặc tích hợp công nghệ bên ngoài thông qua một lớp kết nối chuẩn, nhưng phải kiểm soát chặt phiên bản sử dụng, giấy phép, yêu cầu bảo mật, nguồn gốc mô hình và có bằng chứng kiểm thử để bảo đảm các phiên bản mới không làm ảnh hưởng đến kết quả đã có. Đồng thời, công nghệ được lựa chọn phải có khả năng thay thế khi cần, tránh tạo sự phụ thuộc lâu dài vào một công cụ duy nhất.

Hiện tại, [**VI-Translate**](https://github.com/breslee1707/VI-Translate) phù hợp để tham khảo cách giới hạn phạm vi thay đổi, bảo vệ các đối tượng không được phép chỉnh sửa và dừng xử lý khi chưa đủ điều kiện an toàn. Tuy nhiên, chưa nên đưa trực tiếp mã nguồn hoặc cơ chế của VI-Translate vào Foundation trước khi hoàn tất đánh giá về pháp lý và bảo mật.

 

**WHERE WE ARE**  
**5\. Trạng thái hiện tại của Foundation**

**Thực tế hiện tại:** 

* Nhánh chính của kho mã nguồn vẫn đang ở phiên bản f29e218976b597100eb8e056055df647f3ab7305 sau lần hợp nhất tài liệu đặc tả phiên bản 2.1.   
* Hạng mục B1.2R hiện vẫn đang trong quá trình hoàn tất và được rà soát bởi Codex cùng chuyên gia nghiệp vụ.   
* Hạng mục này chỉ được xem là hoàn tất khi có đủ bằng chứng kiểm chứng trên trường hợp đại diện và kết quả rà soát thủ công xác nhận độ chính xác của đầu ra.

| Năng lực | Trạng thái | Ý nghĩa hiện tại |
| :---- | :---- | :---- |
| **Quản trị và quy ước hệ thống v0.1** | Đã xác lập | Các quyết định kiến trúc, mô hình nghiệp vụ, trạng thái xử lý, cơ chế truy vết và ranh giới quyền hạn đã được xác định. Giao diện người dùng không được phép tự làm thay đổi các quy ước này. |
| **B0 \+ B1.1 Kiểm tra điều kiện xử lý** | Đã chấp nhận | Cơ chế dừng xử lý khi chưa đủ điều kiện an toàn, kiểm soát tài nguyên khi đọc tài liệu OOXML và giới hạn xử lý dữ liệu nén hiện là nhóm năng lực hoàn thiện nhất. |
| **B1.2 Nhận diện ngữ nghĩa** | Đang hoàn tất bước kiểm chứng | Kiểm thử trên dữ liệu mô phỏng đã có thể tiếp tục. Kết quả chạy đại diện Run-002 và đánh giá của chuyên gia nghiệp vụ hiện là điều kiện quyết định để xác nhận năng lực này đạt yêu cầu. |
| **Định danh và liên kết đối tượng gốc**  | Chưa sẵn sàng vận hành thực tế | Đã có quy ước và điểm kết nối kỹ thuật, nhưng chưa có thành phần xử lý đủ khả năng liên kết một đối tượng đã được hiểu về mặt ngữ nghĩa với đúng vị trí hoặc đối tượng tương ứng trong tài liệu Office. |
| **Căn cứ, rà soát và quan hệ phụ thuộc** | Đặc tả đã rõ | Logic nghiệp vụ và các thành phần nền tảng của quy ước xử lý đã được xác định, nhưng dịch vụ vận hành và cơ chế điều phối, kiểm soát vẫn chưa hoàn chỉnh. |
| **Áp dụng thay đổi và kiểm tra có kiểm soát** | Chưa sẵn sàng vận hành thực tế | Hiện chưa thể xem bất kỳ tệp DOCX cuối cùng nào là kết quả do Foundation tạo ra hoàn toàn theo quy trình kiểm soát đã thiết kế. |
| **Giao diện người dùng**  | Bản thử nghiệm / U0 | Không gian làm việc và logic sản phẩm đang được kiểm chứng. Tuy nhiên, năng lực xử lý phía hệ thống vẫn phải là nguồn thông tin chuẩn để xác định trạng thái và kết quả thực tế. |

**WHAT WE BUILD**  
**6\. Phạm vi MVP mới: Ưu tiên Foundation dùng chung, sử dụng Local File để kiểm chứng các tình huống phức tạp**

**Mục tiêu kiểm chứng của MVP**

Chứng minh Foundation có thể trích xuất dữ liệu từ tài liệu với nguồn gốc rõ ràng, áp dụng quy tắc mapping nghiệp vụ có kiểm soát, tạo hoặc cập nhật tệp đầu ra thực tế trong đúng phạm vi đã được phê duyệt, phát hiện các trường hợp chưa đủ căn cứ và chỉ xử lý lại những phần bị ảnh hưởng, trên một nền tảng lõi có thể tái sử dụng cho nhiều quy trình khác nhau. 

| Hướng triển khai | Phạm vi MVP | Điều kiện cần chứng minh |
| :---- | :---- | :---- |
| **A. Foundation dùng chung \- HƯỚNG CHÍNH** | 1\) Trích xuất dữ liệu có kiểm soát từ DOCX/XLSX thành các thông tin có cấu trúc và truy vết được nguồn gốc;  2\) lựa chọn và ánh xạ thông tin theo cấu hình quy trình;  3\) tạo hoặc cập nhật tài liệu DOCX đích trong phạm vi được kiểm soát;  4\) nhận diện rõ các trường hợp thiếu thông tin, mâu thuẫn hoặc chưa đủ rõ ràng;  5\) hỗ trợ truy vết và chỉ xử lý lại phần bị ảnh hưởng. Bổ sung ít nhất một quy trình đại diện ngoài GTPS để kiểm chứng khả năng dùng chung. | Phần lõi có thể chạy xuyên suốt toàn bộ quy trình mà không gắn cứng logic của Local File; tạo được tệp đầu ra thực tế và vượt qua bước kiểm tra kết quả. |
| **B. Local File \- TRƯỜNG HỢP KIỂM CHỨNG ĐẠI DIỆN** | Sử dụng từ 3 đến 5 mục tiêu nghiệp vụ có độ phức tạp cao, gồm kỳ báo cáo, NCP, giá trị giao dịch với bên liên quan, nội dung bị ràng buộc theo mẫu và trường hợp mâu thuẫn liên quan đến Processing Services. | Kiểm chứng khả năng ánh xạ dữ liệu giữa nhiều định dạng, xử lý công thức và bảng biểu, mâu thuẫn giữa các căn cứ, luồng rà soát của người dùng và việc áp dụng thay đổi có kiểm soát. |
| **Ngoài phạm vi MVP** | Chưa hỗ trợ mọi định dạng và mọi cấu trúc trong Office; chưa tự động hóa hoàn toàn; không xây dựng tác nhân AI tự đưa ra quyết định; chưa hoàn thiện toàn bộ yêu cầu để vận hành ở quy mô thực tế. | Giữ phạm vi đủ nhỏ để kiểm chứng các giả định quan trọng trước khi mở rộng. |

**Các chỉ số ưu tiên đánh giá mức độ thành công:** 

* Độ chính xác khi trích xuất và ánh xạ thông tin, đồng thời bảo đảm truy vết được nguồn gốc;   
* Khả năng từ chối xử lý đúng khi chưa đủ căn cứ và hạn chế chấp nhận kết quả sai;   
* Thời gian người dùng cần để rà soát; phạm vi cần xử lý lại khi có thay đổi;   
* Tỷ lệ thay đổi ngoài phạm vi cho phép bằng 0 trong các trường hợp được hỗ trợ;   
* Tỷ lệ đối chiếu nghiệp vụ đạt yêu cầu; và mức độ sử dụng được của tệp đầu ra thực tế so với quy trình làm thủ công và quy trình sử dụng mô hình ngôn ngữ lớn thông thường. 
