import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def create_tech_stack_docx(output_path: str):
    doc = Document()

    # Base page settings (A4 / Standard)
    section = doc.sections[0]
    section.page_width = Inches(8.27)   # A4 width
    section.page_height = Inches(11.69) # A4 height
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    # Colors
    COLOR_PRIMARY = RGBColor(14, 116, 144)   # Cyan / Ocean 700 (#0E7490)
    COLOR_NAVY = RGBColor(15, 23, 42)        # Navy / Slate 900 (#0F172A)
    COLOR_TEXT = RGBColor(51, 65, 85)        # Slate 700 (#334155)
    COLOR_MUTED = RGBColor(100, 116, 139)    # Slate 500 (#64748B)
    COLOR_ACCENT = RGBColor(2, 132, 199)     # Sky 600 (#0284C7)

    # Styles
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Arial'
    style_normal.font.size = Pt(10.5)
    style_normal.font.color.rgb = COLOR_TEXT
    style_normal.paragraph_format.line_spacing = 1.2
    style_normal.paragraph_format.space_after = Pt(4)

    def add_title(text: str, subtitle: str = ""):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.bold = True
        run.font.size = Pt(20)
        run.font.color.rgb = COLOR_PRIMARY

        if subtitle:
            p_sub = doc.add_paragraph()
            p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_sub.paragraph_format.space_after = Pt(18)
            run_sub = p_sub.add_run(subtitle)
            run_sub.font.italic = True
            run_sub.font.size = Pt(11)
            run_sub.font.color.rgb = COLOR_MUTED

    def add_h1(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = COLOR_PRIMARY

    def add_h2(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = COLOR_NAVY

    def add_h3(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = COLOR_ACCENT

    def add_bullet(bold_prefix: str, text: str):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            run_b = p.add_run(bold_prefix + ": ")
            run_b.font.bold = True
            run_b.font.color.rgb = COLOR_NAVY
        run_t = p.add_run(text)
        run_t.font.color.rgb = COLOR_TEXT

    def add_callout(text: str, title: str = "LƯU Ý / GHI CHÚ"):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        cell.width = Inches(6.47)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F9FF"/>')
        borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="24" w:space="0" w:color="0284C7"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
        tcPr.append(shd)
        tcPr.append(borders)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        run_title = p.add_run(f"📌 {title}: ")
        run_title.font.bold = True
        run_title.font.size = Pt(10)
        run_title.font.color.rgb = COLOR_ACCENT
        run_text = p.add_run(text)
        run_text.font.size = Pt(10)
        run_text.font.color.rgb = COLOR_TEXT
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def format_table(table, col_widths=None, header_bg="E0F2FE"):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for r_idx, row in enumerate(table.rows):
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            if r_idx == 0:
                trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

            for c_idx, cell in enumerate(row.cells):
                if col_widths and c_idx < len(col_widths):
                    cell.width = Inches(col_widths[c_idx])
                
                tcPr = cell._tc.get_or_add_tcPr()
                tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="150" w:type="dxa"/><w:right w:w="150" w:type="dxa"/></w:tcMar>')
                tcPr.append(tcMar)
                
                borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/><w:left w:val="none"/><w:right w:val="none"/></w:tcBorders>')
                tcPr.append(borders)

                if r_idx == 0:
                    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{header_bg}"/>')
                    tcPr.append(shd)
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.space_before = Pt(2)
                        for run in p.runs:
                            run.font.bold = True
                            run.font.size = Pt(9.5)
                            run.font.color.rgb = COLOR_NAVY
                else:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.space_before = Pt(2)
                        for run in p.runs:
                            run.font.size = Pt(9)

    # ---------------- DOCUMENT CONTENT ----------------
    add_title(
        "BÁO CÁO CÔNG NGHỆ & KIẾN TRÚC HỆ THỐNG",
        "Dự án: Nền tảng Hướng nghiệp Thông minh Cá nhân hóa AI CareerGuide\nPhiên bản tài liệu: v1.8 (Cập nhật Q4/2026)"
    )

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run("Mã đề tài: C1SE.71 | Ngành: Kỹ thuật phần mềm (CMU Standard)\nTiêu chuẩn áp dụng: OWASP ASVS Level 2 | Nghị định 13/2023/NĐ-CP & Luật 91/2025/QH15")
    r_meta.font.size = Pt(9.5)
    r_meta.font.color.rgb = COLOR_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # SECTION 1
    add_h1("1. TỔNG QUAN HỆ THỐNG & NGUYÊN TẮC THIẾT KẾ")
    p1 = doc.add_paragraph(
        "Hệ thống AI CareerGuide là nền tảng hướng nghiệp thông minh dành cho học sinh THPT Việt Nam, "
        "giúp giải quyết triệt để vấn đề chọn ngành cảm tính, thiếu căn cứ dữ liệu thực tế và nguy cơ vi phạm bảo mật "
        "thông tin học sinh. Hệ thống được xây dựng trên kiến trúc hướng dịch vụ mô-đun hóa (Service-Oriented Modular Architecture), "
        "kết hợp hài hòa giữa thuật toán tất định (Deterministic Scoring) và trí tuệ nhân tạo tạo sinh giải thích được (Explainable AI / Dual RAG)."
    )
    
    add_callout(
        "Hệ thống thiết lập nguyên tắc 'Zero-PII Sanitization' trước mọi lệnh gọi AI bên ngoài, "
        "tuyệt đối không truyền thông tin định danh cá nhân (họ tên, CCCD, SĐT, trường lớp) sang các mô hình LLM. "
        "Đồng thời tuân thủ nguyên tắc 'Pure Guidance Scope': nghiêm cấm mọi yếu tố định kiến học phí hay vị trí địa lý làm sai lệch thứ hạng ngành nghề.",
        "RÀNG BUỘC PHÁP LÝ & ĐẠO ĐỨC NGHỀ NGHIỆP"
    )

    # SECTION 2
    add_h1("2. CÔNG NGHỆ GIAO DIỆN NGƯỜI DÙNG (FRONTEND STACK)")
    p_fe = doc.add_paragraph(
        "Giao diện người dùng được tối ưu hóa theo chuẩn Responsive Web hiện đại, hỗ trợ mượt mà từ thiết bị di động "
        "đến màn hình máy tính lớn, áp dụng phong cách thiết kế Glassmorphism & Bento Grid trực quan:"
    )
    add_bullet("Ngôn ngữ & Runtime", "TypeScript (đảm bảo tính an toàn kiểu tĩnh ở quy mô doanh nghiệp), React 19 (tận dụng tối đa server components, action hooks và compiler mới nhất).")
    add_bullet("Build System", "Vite 6 với plugin @tailwindcss/vite giúp biên dịch và hot-reload cực nhanh (< 100ms).")
    add_bullet("Thiết kế & Giao diện (CSS)", "Tailwind CSS v4 kết hợp hệ thống màu tùy chỉnh (Sky, Cyan, Emerald, Slate) tạo cảm giác công nghệ cao, thân thiện với học sinh lứa tuổi 15-18.")
    add_bullet("Hiệu ứng chuyển động (Motion)", "Framer Motion điều phối các chuyển cảnh mượt mà trong Wizard khảo sát 4 bước, bảng điều khiển Profile Popover và cửa sổ AI Chat Advisor.")
    add_bullet("Hệ thống Icon", "Lucide React cung cấp hơn 100 icon vector hiện đại, chuẩn hóa độ phân giải.")
    add_bullet("Trực quan hóa dữ liệu (Visualization)", "Recharts kết hợp SVG/HTML5 Canvas vẽ biểu đồ Radar 6 chiều Holland RIASEC, đồ thị phân phối xác suất Z-Score tổ hợp môn xét tuyển.")
    add_bullet("Trình bày nội dung giàu (Rich Content)", "React-Markdown & Remark-GFM biên dịch mượt mà các bảng phân tích, công thức và đề cương học tập do AI phản hồi.")

    table_fe = doc.add_table(rows=6, cols=3)
    table_fe.rows[0].cells[0].paragraphs[0].text = "Thành phần Frontend"
    table_fe.rows[0].cells[1].paragraphs[0].text = "Công nghệ / Thư viện"
    table_fe.rows[0].cells[2].paragraphs[0].text = "Vai trò & Giá trị kỹ thuật"
    
    fe_data = [
        ("Core UI Framework", "React 19 + TypeScript", "Đảm bảo Type-safety, tái sử dụng component linh hoạt."),
        ("Styling & UX", "Tailwind CSS v4 + Glassmorphism", "Giao diện hiện đại, tối ưu dung lượng CSS tải trang."),
        ("State & Storage", "React Hooks + Local Storage Sync", "Lưu trữ trạng thái làm bài offline, phục hồi phiên tức thì."),
        ("Data Visualization", "Recharts (Radar, Bar, Line)", "Biểu diễn trực quan hồ sơ năng lực học sinh và phổ điểm."),
        ("AI Interaction", "Framer Motion + Markdown Parser", "Trải nghiệm trò chuyện AI Advisor tương tác thời gian thực."),
    ]
    for idx, (c1, c2, c3) in enumerate(fe_data, start=1):
        table_fe.rows[idx].cells[0].paragraphs[0].text = c1
        table_fe.rows[idx].cells[1].paragraphs[0].text = c2
        table_fe.rows[idx].cells[2].paragraphs[0].text = c3
    format_table(table_fe, [1.8, 2.0, 2.67])

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # SECTION 3
    add_h1("3. CÔNG NGHỆ MÁY CHỦ & DỊCH VỤ MODULAR (BACKEND CORE)")
    doc.add_paragraph(
        "Backend của hệ thống được kiến trúc theo chuẩn RESTful API hiện đại dựa trên mô hình 6 dịch vụ mô-đun độc lập (6 Modular Services):"
    )
    add_bullet("Ngôn ngữ & Framework", "Python 3.11 chạy trên máy chủ bất đồng bộ ASGI Uvicorn và FastAPI Framework.")
    add_bullet("Cấu hình & Data Validation", "Pydantic v2 và Pydantic-Settings (hỗ trợ kiểm tra schema chặt chẽ, tự động chuyển đổi kiểu dữ liệu).")
    add_bullet("Database Access Layer", "SQLAlchemy 2.0 với kiến trúc Async Session kết hợp driver 'asyncpg' cho PostgreSQL và 'aiosqlite' cho môi trường kiểm thử.")
    add_bullet("Trích xuất tài liệu đào tạo", "PyMuPDF (fitz) và pypdf phân tích cấu trúc văn bản Thông tư; openpyxl xử lý biểu mẫu Excel (.xlsx); RapidOCR quét tài liệu ảnh.")

    add_h2("Kiến trúc 6 Dịch vụ Mô-đun (6 Modular Backend Services):")
    services_data = [
        ("1. identity", "Quản lý người dùng, phân quyền RBAC (ADMIN, STUDENT), mã hóa mật khẩu Argon2id và xác thực Token JWT."),
        ("2. assessment", "Quản trị bộ 30 câu hỏi Holland RIASEC (v1.8) và 8 câu hỏi phong cách nhận thức; tính điểm thô và chuẩn hóa Z-Score học bạ."),
        ("3. recommender", "Bộ máy suy luận 3 trụ cột (45% RIASEC, 35% Academic, 20% Cognitive); thuật toán phân tầng Target-Anchored và Hard Cutoff."),
        ("4. taxonomy", "Quản lý danh mục 108 ngành cấp IV theo Thông tư 09/2022 và 74/2026/TT-BGDĐT, tổ hợp xét tuyển (A00, A01, D01...) và Cây nghề nghiệp Phoenix Ho."),
        ("5. gap_roadmap_engine", "Bộ máy phát hiện lỗ hổng kỹ năng tiên quyết, cấp phát lộ trình học tập 4 tuần và mẫu lộ trình chuẩn hóa dự phòng."),
        ("6. llamaindex_rag_orchestrator", "Điều phối Dual RAG (Stream A - Ingest Thông tư, Stream B - Discovery đề cương đại học), hàng đợi Human-in-the-Loop và Cố vấn AI.")
    ]
    for name, desc in services_data:
        add_bullet(name, desc)

    # SECTION 4
    add_h1("4. HỆ THỐNG CƠ SỞ DỮ LIỆU & VECTOR EMBEDDING")
    doc.add_paragraph(
        "Hệ thống sử dụng cơ sở dữ liệu đối tượng - quan hệ PostgreSQL 16 kết hợp tiện ích mở rộng pgvector:"
    )
    add_bullet("PostgreSQL 16", "Lưu trữ toàn bộ các bảng nghiệp vụ quan hệ (users, student_assessments, student_grades, majors, subject_blocks, staging_records). Đảm bảo tính toàn vẹn giao dịch ACID tuyệt đối.")
    add_bullet("pgvector Extension", "Hỗ trợ trường dữ liệu kiểu vector(1536). Cho phép tính toán khoảng cách vector (Cosine Distance `<=>`) trực tiếp bằng chỉ mục HNSW/IVFFlat trong cơ sở dữ liệu.")
    add_bullet("Mô hình Vector Embedding", "Sử dụng text-embedding-3-small (1536 chiều) để biểu diễn ngữ nghĩa các đoạn đề cương môn học, tiêu chuẩn đầu ra và câu hỏi thắc mắc của học sinh.")

    # SECTION 5
    add_h1("5. TRÍ TUỆ NHÂN TẠO & THUẬT TOÁN ĐỀ XUẤT CỐT LÕI")
    
    add_h2("5.1. Bộ máy Khuyến nghị 3 Trụ cột (3-Pillar Recommendation Engine)")
    doc.add_paragraph(
        "Khác với các ứng dụng hướng nghiệp thông thường chỉ dựa vào bảng hỏi sở thích, AI CareerGuide tích hợp "
        "mô hình toán học định lượng 3 trụ cột kết hợp cơ chế kiểm soát ngưỡng năng lực học thuật:"
    )
    add_bullet("Trụ cột 1: 45% RIASEC Fit", "Tính độ tương đồng góc Cosine giữa vector sở thích 6 chiều của học sinh với ma trận chuẩn hóa của ngành đào tạo (Holland Vocational Hexagon).")
    add_bullet("Trụ cột 2: 35% Academic Z-Score Fit", "Điểm học bạ THPT được chuẩn hóa thành giá trị Z-Score so với kỳ thi tốt nghiệp THPT Quốc gia theo từng tổ hợp xét tuyển. Hệ thống chia thành 3 phân tầng: Safety (An toàn), Target (Mục tiêu), Reach (Vươn tới).")
    add_bullet("Trụ cột 3: 20% Cognitive Trait Fit", "Đối sánh bất đối xứng 8 câu hỏi phong cách nhận thức (Hệ thống, Trực giác, Phân tích, Trừu tượng...) với yêu cầu phương pháp học bậc đại học.")
    add_bullet("Hard Academic Cutoff & Sibling Substitution", "Nếu điểm của học sinh thấp hơn ngưỡng an toàn của ngành Reach, hệ thống kích hoạt 'Hard Cutoff' cảnh báo rủi ro trượt tuyển sinh và tự động đề xuất 'Ngành anh em' (Sibling Major) có ngưỡng tuyển sinh vừa sức hơn.")

    add_h2("5.2. Kiến trúc Dual RAG & Cố vấn AI Giải thích được (XAI)")
    add_bullet("Stream A (Ingestion RAG)", "Nhập tài liệu Thông tư Bộ GD&ĐT (PDF/Excel), bóc tách danh mục ngành tự động đưa vào hàng đợi Human-in-the-Loop để Admin kiểm duyệt trước khi xuất bản.")
    add_bullet("Stream B (Discovery RAG)", "Thu thập đề cương đào tạo từ cổng thông tin các trường đại học đối tác qua Tavily API & Jina Reader (giới hạn nghiêm ngặt tên miền .edu.vn).")
    add_bullet("Gateway Mô hình Ngôn ngữ Lớn", "Kết nối qua xKiro API Gateway (chuẩn OpenAI/Anthropic SDK), tích hợp mô hình Mistral Large (mistralai/mistral-large-2512), Qwen VL Vision và Gemini.")
    add_bullet("Cơ chế Deterministic Fallback", "Nếu kết nối AI bị gián đoạn hoặc thời gian xử lý vượt quá 8.0 giây, hệ thống tự động chuyển sang bộ giải trình toán học tất định (Deterministic Fallback), đảm bảo tính sẵn sàng 100% cho người dùng.")

    # SECTION 6
    add_h1("6. AN NINH BẢO MẬT & BẢO VỆ DỮ LIỆU CÁ NHÂN")
    doc.add_paragraph(
        "Hệ thống đạt tiêu chuẩn bảo mật OWASP ASVS Level 2 và tuân thủ nghiêm ngặt Luật Bảo vệ Dữ liệu Cá nhân số 91/2025/QH15:"
    )
    add_bullet("Bộ lọc Zero-PII Sanitization", "Tất cả văn bản câu hỏi và ngữ cảnh học sinh đều đi qua bộ lọc biểu thức chính quy (Regex Engine) để khử khuẩn họ tên, số điện thoại Việt Nam (+84/09x), số CCCD (12 chữ số), địa chỉ, trường lớp.")
    add_bullet("Mã hóa mật khẩu Argon2id", "Áp dụng thuật toán băm Argon2id (bộ nhớ 64MB, parallelism=2, time_cost=3) chống tấn công vét cạn bằng GPU/ASIC.")
    add_bullet("Xác thực & Ủy quyền", "Sử dụng JSON Web Token (JWT) mã hóa HS256 với thời gian sống có kiểm soát; hỗ trợ đăng nhập một chạm qua Google OAuth 2.0.")
    add_bullet("Phân quyền nghiêm ngặt (RBAC)", "Tách biệt hoàn toàn quyền giữa Quản trị viên (ADMIN - kiểm duyệt tài liệu, xem logs) và Học sinh (STUDENT - làm bài test, xem lộ trình).")

    # SECTION 7
    add_h1("7. DEVOPS & MÔI TRƯỜNG VẬN HÀNH (DOCKER ENVIRONMENT)")
    doc.add_paragraph(
        "Toàn bộ dự án được đóng gói hoàn chỉnh bằng Docker và Docker Compose, cho phép khởi chạy đồng bộ chỉ với 1 câu lệnh duy nhất:"
    )

    table_docker = doc.add_table(rows=4, cols=3)
    table_docker.rows[0].cells[0].paragraphs[0].text = "Container Service"
    table_docker.rows[0].cells[1].paragraphs[0].text = "Hình ảnh cơ sở (Base Image)"
    table_docker.rows[0].cells[2].paragraphs[0].text = "Cổng kết nối & Chức năng"

    docker_data = [
        ("ai_careerguide_db", "pgvector/pgvector:pg16", "Cổng 5432: Lưu trữ cơ sở dữ liệu quan hệ và vector embedding 1536 chiều."),
        ("ai_careerguide_backend", "python:3.11-slim", "Cổng 8000: Khởi chạy FastAPI Core, tự động seed dữ liệu Thông tư và chạy uvicorn."),
        ("ai_careerguide_frontend", "nginx:1.27-alpine", "Cổng 5173 / 3000: Nginx reverse-proxy các request /api sang backend và phục vụ SPA.")
    ]
    for idx, (c1, c2, c3) in enumerate(docker_data, start=1):
        table_docker.rows[idx].cells[0].paragraphs[0].text = c1
        table_docker.rows[idx].cells[1].paragraphs[0].text = c2
        table_docker.rows[idx].cells[2].paragraphs[0].text = c3
    format_table(table_docker, [2.0, 1.8, 2.67])

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # CONCLUSION
    add_h1("8. KẾT LUẬN")
    doc.add_paragraph(
        "Ngăn xếp công nghệ của dự án AI CareerGuide được tuyển chọn kỹ lưỡng, cân bằng giữa tốc độ phát triển "
        "sản phẩm, tính an toàn thông tin theo pháp luật Việt Nam và khả năng mở rộng quy mô phục vụ hàng trăm ngàn "
        "học sinh THPT trên toàn quốc trong các kỳ tuyển sinh đại học hàng năm."
    )

    doc.save(output_path)
    print(f"Document saved successfully at: {output_path}")

if __name__ == "__main__":
    out_dir = r"E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE\document"
    out_file = os.path.join(out_dir, "Bao_Cao_Cong_Nghe_AI_CareerGuide.docx")
    create_tech_stack_docx(out_file)
