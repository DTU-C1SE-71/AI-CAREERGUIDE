import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def create_proposal_docx(output_path: str):
    doc = Document()

    # Base page settings
    section_cover = doc.sections[0]
    section_cover.page_width = Inches(8.5)
    section_cover.page_height = Inches(11.0)
    section_cover.top_margin = Inches(1.0)
    section_cover.bottom_margin = Inches(1.0)
    section_cover.left_margin = Inches(1.0)
    section_cover.right_margin = Inches(1.0)
    section_cover.different_first_page_header_footer = True

    # Colors
    COLOR_PRIMARY = RGBColor(163, 0, 0)      # DTU Red
    COLOR_TEXT = RGBColor(30, 41, 59)        # Slate 800
    COLOR_NAVY = RGBColor(15, 23, 42)        # Navy 900
    COLOR_MUTED = RGBColor(100, 116, 139)    # Slate 500

    # Styles
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(11)
    style_normal.font.color.rgb = COLOR_TEXT
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(4)

    image_dir = r"E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\Document\image"
    logo_path = os.path.join(image_dir, "image1.png")
    fig1_path = os.path.join(image_dir, "Figure 1. Overall student journey in AI CareerGuide.png")
    fig2_path = os.path.join(image_dir, "AI-CareerGuide-Use-Case-Diagram-Simple.png")
    fig3_path = os.path.join(image_dir, "Figure 3. Explainable major recommendation workflow.png")
    fig4_path = os.path.join(image_dir, "Figure 4. AI CareerGuide system context and logical architecture.png")

    # Helper: Set table borders & header styling
    def format_table(table, col_widths=None, header_bg="F1F5F9"):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for r_idx, row in enumerate(table.rows):
            # prevent split across pages
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            if r_idx == 0:
                trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

            for c_idx, cell in enumerate(row.cells):
                if col_widths and c_idx < len(col_widths):
                    cell.width = Inches(col_widths[c_idx])
                
                tcPr = cell._tc.get_or_add_tcPr()
                # cell margins
                tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="150" w:type="dxa"/><w:right w:w="150" w:type="dxa"/></w:tcMar>')
                tcPr.append(tcMar)
                
                # header formatting
                if r_idx == 0:
                    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{header_bg}"/>')
                    tcPr.append(shd)
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.space_before = Pt(2)
                        for run in p.runs:
                            run.font.bold = True
                            run.font.size = Pt(10)
                            run.font.color.rgb = COLOR_NAVY
                else:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.space_before = Pt(2)
                        for run in p.runs:
                            run.font.size = Pt(9.5)

    def add_heading_1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13.5)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
        return p

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = COLOR_NAVY
        return p

    def add_heading_3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.italic = True
        run.font.color.rgb = COLOR_NAVY
        return p

    def add_caption(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(10)
        run = p.add_run(text)
        run.font.size = Pt(9.5)
        run.font.italic = True
        run.font.bold = True
        run.font.color.rgb = COLOR_MUTED

    # ==========================================
    # COVER PAGE
    # ==========================================
    p_logo = doc.add_paragraph()
    p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if os.path.exists(logo_path):
        run_logo = p_logo.add_run()
        run_logo.add_picture(logo_path, width=Inches(2.5))
    p_logo.paragraph_format.space_after = Pt(4)

    p_school = doc.add_paragraph()
    run_school = p_school.add_run("International School\nCAPSTONE PROJECT 1\nCMU-SE 450 – C1SE.71")
    run_school.font.size = Pt(12)
    run_school.font.bold = True
    run_school.font.color.rgb = COLOR_PRIMARY
    p_school.paragraph_format.space_after = Pt(16)

    p_doc_title = doc.add_paragraph()
    p_doc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_prop = p_doc_title.add_run("Project Proposal\n")
    run_prop.font.size = Pt(18)
    run_prop.font.bold = True
    run_prop.font.color.rgb = COLOR_NAVY

    run_ver = p_doc_title.add_run("Version 1.1\n")
    run_ver.font.size = Pt(16)
    run_ver.font.bold = True
    run_ver.font.color.rgb = COLOR_PRIMARY

    run_date = p_doc_title.add_run("Date: November 04, 2026\n\n")
    run_date.font.size = Pt(11)
    run_date.font.italic = True

    run_title = p_doc_title.add_run("AI CAREERGUIDE\n")
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = COLOR_PRIMARY

    run_sub = p_doc_title.add_run("Personalized Major Guidance for Vietnamese High School Students")
    run_sub.font.size = Pt(13)
    run_sub.font.bold = True
    run_sub.font.color.rgb = COLOR_NAVY
    p_doc_title.paragraph_format.space_after = Pt(24)

    # Submitted by block
    p_team = doc.add_paragraph()
    p_team.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_team.add_run("Submitted by C1SE.71\n")
    r_sub.font.bold = True
    r_sub.font.size = Pt(11)
    team_members = [
        "Duy, Nguyen Tan (29211142148)",
        "Trung, Nguyen Tam (29212736855)",
        "Cuong, Nguyen Tu (29214360592)",
        "Hieu, Nguyen Thai Hoang (29219030682)",
        "Hien, Nguyen Thanh Long (29219065409)"
    ]
    p_team.add_run("\n".join(team_members) + "\n\n")
    p_team.paragraph_format.space_after = Pt(12)

    # Approved by block
    p_app = doc.add_paragraph()
    p_app.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_app = p_app.add_run("Approved by\nMSc. Son, Phan Van\n")
    r_app.font.bold = True
    p_app.paragraph_format.space_after = Pt(20)

    # Signature blocks
    table_sig = doc.add_table(rows=3, cols=2)
    table_sig.style = 'Table Grid'
    format_table(table_sig, [3.2, 3.2])
    table_sig.rows[0].cells[0].paragraphs[0].text = "Proposal Review Panel Representative:"
    table_sig.rows[0].cells[1].paragraphs[0].text = "Capstone Project 1 - Mentor:"
    table_sig.rows[1].cells[0].paragraphs[0].text = "\n\n_________________________________"
    table_sig.rows[1].cells[1].paragraphs[0].text = "\n\n_________________________________"
    table_sig.rows[2].cells[0].paragraphs[0].text = "Date: ___ / ___ / 2026"
    table_sig.rows[2].cells[1].paragraphs[0].text = "Date: ___ / ___ / 2026"

    p_city = doc.add_paragraph()
    p_city.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_city.paragraph_format.space_before = Pt(24)
    r_city = p_city.add_run("Da Nang, 2026")
    r_city.font.bold = True

    # ==========================================
    # SECTION BREAK & HEADER/FOOTER
    # ==========================================
    section_body = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    section_body.top_margin = Inches(1.0)
    section_body.bottom_margin = Inches(1.0)
    section_body.left_margin = Inches(1.0)
    section_body.right_margin = Inches(1.0)
    section_body.different_first_page_header_footer = False

    header_para = section_body.header.paragraphs[0]
    header_para.text = "AI CareerGuide | Capstone Project Proposal Version 1.1"
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_para.style.font.size = Pt(8.5)
    header_para.style.font.italic = True
    header_para.style.font.color.rgb = COLOR_MUTED

    footer_para = section_body.footer.paragraphs[0]
    footer_para.text = "International School, Duy Tan University — CMU-SE 450 Capstone 1 (C1SE.71)"
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_para.style.font.size = Pt(8.5)
    footer_para.style.font.color.rgb = COLOR_MUTED

    # ==========================================
    # PRELIMINARY TABLES
    # ==========================================
    add_heading_1("PROJECT INFORMATION")
    proj_info = [
        ("Project acronym", "AI CareerGuide"),
        ("Project title", "AI CareerGuide: Personalized Major Guidance for Vietnamese High School Students"),
        ("Project type", "Responsive web application, Explainable AI (XAI) decision-support system, grounded self-study guidance platform"),
        ("Proposed start date", "July 28, 2026"),
        ("Proposed end date", "December 26, 2026"),
        ("Lead institution", "International School, Duy Tan University"),
        ("Project mentor", "MSc. Son, Phan Van – sonpvs@duytan.edu.vn – 0905042413"),
        ("Project leader", "Duy, Nguyen Tan – nguyentduy.025@gmail.com – 0396157802"),
        ("Repository URL", "https://github.com/ntanduy25/AI-CAREERGUIDE.git"),
        ("Implementation window", "15 Weeks (September 14, 2026 – December 26, 2026)"),
        ("Document baseline", "Proposal Version 1.1 (Comprehensive Project Alignment & Implementation Baseline)")
    ]
    t_proj = doc.add_table(rows=len(proj_info) + 1, cols=2)
    t_proj.style = 'Table Grid'
    format_table(t_proj, [2.2, 4.3])
    t_proj.rows[0].cells[0].paragraphs[0].text = "Field"
    t_proj.rows[0].cells[1].paragraphs[0].text = "Information"
    for idx, (f, v) in enumerate(proj_info):
        t_proj.rows[idx+1].cells[0].paragraphs[0].text = f
        t_proj.rows[idx+1].cells[0].paragraphs[0].runs[0].font.bold = True
        t_proj.rows[idx+1].cells[1].paragraphs[0].text = v

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Student List table
    stud_list = [
        ("29211142148", "Duy, Nguyen Tan", "nguyentduy.025@gmail.com", "Project Leader; Backend / Integration / DevOps"),
        ("29212736855", "Trung, Nguyen Tam", "tamtrung3666@gmail.com", "System Architect; Full-stack Developer"),
        ("29214360592", "Cuong, Nguyen Tu", "tucuong37k5@gmail.com", "Business Analyst; QA Engineer"),
        ("29219030682", "Hieu, Nguyen Thai Hoang", "nguyenthaihoanghieu3012005@gmail.com", "Frontend Developer; UI/UX Specialist"),
        ("29219065409", "Hien, Nguyen Thanh Long", "hiennguyen05102005@gmail.com", "AI, Recommendation & Data Engineer")
    ]
    t_stud = doc.add_table(rows=len(stud_list) + 1, cols=4)
    t_stud.style = 'Table Grid'
    format_table(t_stud, [1.1, 1.8, 1.8, 1.8])
    t_stud.rows[0].cells[0].paragraphs[0].text = "Student ID"
    t_stud.rows[0].cells[1].paragraphs[0].text = "Name"
    t_stud.rows[0].cells[2].paragraphs[0].text = "Email"
    t_stud.rows[0].cells[3].paragraphs[0].text = "Primary Role"
    for idx, row in enumerate(stud_list):
        for c_idx, val in enumerate(row):
            t_stud.rows[idx+1].cells[c_idx].paragraphs[0].text = val

    add_heading_1("DOCUMENT APPROVALS")
    approvals = [
        ("MSc. Son, Phan Van", "Academic Mentor", "Approved / Nov 04, 2026"),
        ("Duy, Nguyen Tan", "Project Leader", "Signed / Nov 04, 2026"),
        ("Trung, Nguyen Tam", "System Architect", "Signed / Nov 04, 2026"),
        ("Cuong, Nguyen Tu", "Quality Assurance", "Signed / Nov 04, 2026"),
        ("Hieu, Nguyen Thai Hoang", "Frontend Lead", "Signed / Nov 04, 2026"),
        ("Hien, Nguyen Thanh Long", "AI & Data Lead", "Signed / Nov 04, 2026")
    ]
    t_app = doc.add_table(rows=len(approvals) + 1, cols=3)
    t_app.style = 'Table Grid'
    format_table(t_app, [2.2, 2.2, 2.1])
    t_app.rows[0].cells[0].paragraphs[0].text = "Name"
    t_app.rows[0].cells[1].paragraphs[0].text = "Role"
    t_app.rows[0].cells[2].paragraphs[0].text = "Approval / Date"
    for idx, (n, r, a) in enumerate(approvals):
        t_app.rows[idx+1].cells[0].paragraphs[0].text = n
        t_app.rows[idx+1].cells[1].paragraphs[0].text = r
        t_app.rows[idx+1].cells[2].paragraphs[0].text = a

    add_heading_1("REVISION HISTORY")
    revisions = [
        ("v1.0", "Aug 18, 2026", "Initial proposal draft and domain concept outline.", "C1SE.71 Team"),
        ("v1.1", "Nov 04, 2026", "Comprehensive Project Alignment & Technical Evolution (Current Baseline): Pure guidance scope eliminating tuition/geographic bias; 5 theoretical foundations (RIASEC, Gardner, MBTI, Phoenix Ho, Locke & Latham); deterministic 3-pillar XAI mathematical formulas; Solution B admission feasibility tiering (High/Medium/Standard competition; Target vs. Reach); 435 Level-IV MOET majors from TT09 and TT74/2026; Two-stream ingestion (Qwen3-VL OCR & Tavily discovery) with HITL review; high-efficiency major_code study roadmap caching in PostgreSQL (JSONB + pgvector); Argon2id password hashing & Google OAuth 2.0; Zero-PII sanitization under Law 91/2025/QH15; 69 Pytest unit/integration test cases (100% PASS).", "C1SE.71 Team")
    ]
    t_rev = doc.add_table(rows=len(revisions) + 1, cols=4)
    t_rev.style = 'Table Grid'
    format_table(t_rev, [0.8, 1.0, 3.7, 1.0])
    t_rev.rows[0].cells[0].paragraphs[0].text = "Version"
    t_rev.rows[0].cells[1].paragraphs[0].text = "Date"
    t_rev.rows[0].cells[2].paragraphs[0].text = "Comments / Key Modifications"
    t_rev.rows[0].cells[3].paragraphs[0].text = "Author"
    for idx, (v, d, c, a) in enumerate(revisions):
        t_rev.rows[idx+1].cells[0].paragraphs[0].text = v
        t_rev.rows[idx+1].cells[1].paragraphs[0].text = d
        t_rev.rows[idx+1].cells[2].paragraphs[0].text = c
        t_rev.rows[idx+1].cells[3].paragraphs[0].text = a

    doc.add_page_break()

    # ==========================================
    # TABLE OF CONTENTS, TABLES, FIGURES
    # ==========================================
    add_heading_1("TABLE OF CONTENTS")
    toc_items = [
        "1. Project Title",
        "2. Team Members & Responsibilities",
        "3. Supervisor(s)",
        "4. Problem Statement",
        "5. Survey / Existing Solutions",
        "    5.1. International Career Guidance Platforms",
        "    5.2. Domestic Admission Portals and Tools",
        "    5.3. Identified Critical Gaps",
        "    5.4. Comparative Analysis Matrix",
        "6. Objectives and Scope",
        "    6.1. General Objective",
        "    6.2. Specific and Measurable Objectives",
        "    6.3. In Scope (MVP Baseline)",
        "    6.4. Out of Scope (MVP Baseline)",
        "7. Key Features & Requirements",
        "    7.1. Functional Requirements (FR01 – FR07)",
        "    7.2. Non-Functional Requirements (NFR01 – NFR06)",
        "    7.3. Recommendation Logic, Theoretical Grounding, and XAI Formulations",
        "    7.4. Two-Stream Knowledge Ingestion and Dual RAG Pipeline",
        "    7.5. Architectural Boundary Isolation Matrix",
        "8. Constraints and Assumptions",
        "    8.1. System Constraints",
        "    8.2. Operational Assumptions",
        "9. Target Users & Stakeholders",
        "10. Technology Stack Architecture",
        "11. Methodology & Development Plan",
        "    11.1. Agile Scrum Framework",
        "    11.2. 15-Week Sprint Implementation Roadmap",
        "    11.3. Quality Gates & Definition of Done",
        "12. System Architecture Overview",
        "    12.1. 3-Tier Modular Monolith Architecture",
        "    12.2. System Context & Component Interaction",
        "    12.3. Principal Data Flows",
        "    12.4. Security, Zero-PII Sanitization, and Legal Compliance",
        "13. Potential Risks and Mitigation Strategies",
        "14. Expected Outcomes & Deliverables",
        "15. References"
    ]
    for item in toc_items:
        p_t = doc.add_paragraph(item)
        p_t.paragraph_format.space_after = Pt(2)

    add_heading_1("LIST OF TABLES")
    tables_list = [
        "Table 1. Team members and responsibilities",
        "Table 2. Project supervisor",
        "Table 3. Existing solution comparison and identified gaps",
        "Table 4. Functional requirements catalog (FR01 – FR07)",
        "Table 5. Non-functional quality requirements (NFR01 – NFR06)",
        "Table 6. Architectural component responsibility and boundary isolation matrix",
        "Table 7. Project constraints and engineering responses",
        "Table 8. Target user profiles and stakeholder mapping",
        "Table 9. Unified technology stack architecture",
        "Table 10. Fifteen-week agile sprint development plan",
        "Table 11. Principal system data flow definitions",
        "Table 12. Risk register and mitigation matrix",
        "Table 13. Project deliverables catalog"
    ]
    for item in tables_list:
        doc.add_paragraph(item).paragraph_format.space_after = Pt(2)

    add_heading_1("LIST OF FIGURES")
    figures_list = [
        "Figure 1. End-to-end student guidance journey across 7 theoretical stages",
        "Figure 2. AI CareerGuide system use case diagram",
        "Figure 3. Explainable 3-pillar recommendation and feasibility tiering workflow",
        "Figure 4. AI CareerGuide system context and logical architecture"
    ]
    for item in figures_list:
        doc.add_paragraph(item).paragraph_format.space_after = Pt(2)

    doc.add_page_break()

    # ==========================================
    # BODY SECTIONS 1 - 15
    # ==========================================
    # SECTION 1
    add_heading_1("1. Project Title")
    p = doc.add_paragraph()
    r = p.add_run("Project Title: AI CareerGuide: Personalized Major Guidance for Vietnamese High School Students\n")
    r.font.bold = True
    p.add_run(
        "AI CareerGuide is an Explainable AI (XAI) decision-support and personalized career guidance platform engineered specifically "
        "for Vietnamese high school students (particularly grades 11 and 12). The system synthesizes vocational interest assessments, "
        "cognitive learning preferences, and standardized academic performance across national university admission subject blocks "
        "(e.g., A00, A01, B00, D01). Built upon official Ministry of Education and Training (MOET) Level-IV major taxonomies "
        "(Circular 09/2022/TT-BGDĐT and Circular 74/2026/TT-BGDĐT), the platform generates transparent, reproducible major recommendations "
        "and provides structured, actionable 4-week self-directed study roadmaps without exposing students to generative AI hallucinations "
        "or recurring token cost inflation."
    )

    # SECTION 2
    add_heading_1("2. Team Members")
    doc.add_paragraph(
        "The project is executed by a cross-functional engineering team of five software engineering students from Duy Tan University. "
        "Every member actively contributes code, tests, and documentation in every sprint, led by specific domain owners. Coding effort "
        "is balanced through task rotation, pair review, and shared acceptance criteria. Table 1 defines the team composition and responsibility breakdown."
    )
    t1_data = [
        ("Duy, Nguyen Tan", "29211142148", "Project Leader; Backend / Integration / DevOps", "Backlog coordination, REST API gateway architecture, Argon2id security implementation, Google OAuth 2.0 flow, Docker orchestration, Render/Vercel CI/CD release management, and API integration testing."),
        ("Trung, Nguyen Tam", "29212736855", "System Architect; Full-stack Developer", "Software architecture design, PostgreSQL 16 schema modeling, pgvector indexing, SQLAlchemy 2.0 Async migrations, identity/taxonomy database services, and OWASP security compliance."),
        ("Cuong, Nguyen Tu", "29214360592", "Business Analyst; QA Engineer", "Requirements engineering, user stories, acceptance criteria, Pytest automated testing suite (69 test cases), Playwright E2E testing, data validation, and Zero-PII privacy audit verification."),
        ("Hieu, Nguyen Thai Hoang", "29219030682", "Frontend Developer; UI/UX Specialist", "Responsive React 18 + TypeScript SPA, Tailwind CSS design system, WCAG 2.1 AA accessibility, mobile viewport optimization (≥ 360px), student assessment wizards, and interactive guidance dashboards."),
        ("Hien, Nguyen Thanh Long", "29219065409", "AI, Recommendation & Data Engineer", "Mathematical 3-pillar XAI scoring engine (Cosine Similarity, Z-score CDF, Cognitive trait rules), admission feasibility tiering (Solution B), LlamaIndex Dual RAG, Tavily Search discovery, and Qwen3-VL OCR pipeline.")
    ]
    t1 = doc.add_table(rows=len(t1_data) + 1, cols=4)
    t1.style = 'Table Grid'
    format_table(t1, [1.5, 1.0, 1.6, 2.4])
    t1.rows[0].cells[0].paragraphs[0].text = "Name"
    t1.rows[0].cells[1].paragraphs[0].text = "Student ID"
    t1.rows[0].cells[2].paragraphs[0].text = "Primary Role"
    t1.rows[0].cells[3].paragraphs[0].text = "Main Responsibilities & Sprint Coding Focus"
    for idx, (n, sid, r, resp) in enumerate(t1_data):
        t1.rows[idx+1].cells[0].paragraphs[0].text = n
        t1.rows[idx+1].cells[1].paragraphs[0].text = sid
        t1.rows[idx+1].cells[2].paragraphs[0].text = r
        t1.rows[idx+1].cells[3].paragraphs[0].text = resp
    add_caption("Table 1. Team members and responsibilities")

    # SECTION 3
    add_heading_1("3. Supervisor(s)")
    t2_data = [
        ("MSc. Son, Phan Van", "Faculty of Information Technology / International School, Duy Tan University", "sonpvs@duytan.edu.vn", "Academic Capstone Mentor")
    ]
    t2 = doc.add_table(rows=len(t2_data) + 1, cols=4)
    t2.style = 'Table Grid'
    format_table(t2, [1.6, 2.5, 1.5, 0.9])
    t2.rows[0].cells[0].paragraphs[0].text = "Name"
    t2.rows[0].cells[1].paragraphs[0].text = "Faculty / Unit"
    t2.rows[0].cells[2].paragraphs[0].text = "Email"
    t2.rows[0].cells[3].paragraphs[0].text = "Role"
    for idx, (n, u, e, r) in enumerate(t2_data):
        t2.rows[idx+1].cells[0].paragraphs[0].text = n
        t2.rows[idx+1].cells[1].paragraphs[0].text = u
        t2.rows[idx+1].cells[2].paragraphs[0].text = e
        t2.rows[idx+1].cells[3].paragraphs[0].text = r
    add_caption("Table 2. Project supervisor")

    # SECTION 4
    add_heading_1("4. Problem Statement")
    doc.add_paragraph(
        "Vietnamese high school students, especially those in Grades 11 and 12 facing the National High School Graduation and "
        "University Entrance Examinations, confront a critical life decision: selecting a university major. However, this decision-making "
        "process is hindered by fundamental systemic issues:\n\n"
        "1. Information Fragmentation and Noise: Information regarding university majors, admission subject combinations, benchmark scores, "
        "and career competencies is dispersed across hundreds of individual university websites, social media channels, and annual regulatory documents.\n"
        "2. Generic, Uncontextualized Quizzes: Commercial personality tests (e.g., generic online MBTI quizzes) output abstract personality "
        "descriptions without connecting traits to the Vietnamese National Curriculum, specific admission subject blocks (A00, A01, D01, C00), or MOET training codes.\n"
        "3. Socio-Economic Bias from Premature Filtering: Existing tools frequently filter major recommendations based on tuition fees or geographic location. "
        "This premature filtering actively discourages qualified students from discovering high-potential academic programs, disregarding national student "
        "credit funds, enterprise scholarships, and institutional financial aid policies.\n"
        "4. The 'Guidance-Action' Chasm: Even when students identify a potential major, they receive no actionable guidance on what prerequisite knowledge "
        "or foundational skills they should self-study during high school to succeed in university.\n"
        "5. Generative AI Hallucinations and Insecurity: Pure LLM chatbots often invent non-existent university majors, provide unverified admission advice, "
        "and leak sensitive student personal identifiable information (PII) to foreign third-party API providers.\n\n"
        "AI CareerGuide establishes a Pure Vocational Career Guidance platform founded on Explainable AI (XAI) and theoretical models. "
        "It evaluates three intrinsic dimensions: (1) vocational interests, (2) cognitive learning preferences, and (3) standardized academic performance. "
        "Recommendations are 100% deterministic, transparently explained, mapped directly to official MOET circulars (covering 435 Level-IV majors across 22 disciplines), "
        "and paired with cached 4-week self-study roadmaps with Zero PII leakage."
    )

    # SECTION 5
    add_heading_1("5. Survey / Existing Solutions")
    add_heading_2("5.1. International Career Guidance Platforms")
    doc.add_paragraph(
        "International solutions such as the O*NET Interest Profiler (U.S. Department of Labor) and official MBTI Career Assessments provide "
        "established psychometric foundations. However, they lack native integration with Vietnamese admission subject combinations, "
        "MOET major codes, and Vietnamese high school grading systems."
    )
    add_heading_2("5.2. Domestic Admission Portals and Tools")
    doc.add_paragraph(
        "Domestic university portals and the Ministry of Education and Training admission portal (tuyensinh.moet.gov.vn) serve strictly as "
        "administrative registries and historical cutoff score repositories. They offer zero personalized decision support, psychometric compatibility modeling, "
        "or individualized learning roadmaps."
    )
    add_heading_2("5.3. Identified Critical Gaps")
    doc.add_paragraph(
        "Existing products either lack objective grade evaluations or introduce socio-economic bias by prematurely filtering majors by tuition and geography, "
        "rather than focusing purely on student aptitude and career fit. Furthermore, static portals do not bridge the gap between choosing a major and knowing "
        "which prerequisite skills to self-study before entering university."
    )
    t3_data = [
        ("Official MBTI Career Test", "Recognized personality typology and deep qualitative descriptions.", "Does not measure academic ability; proprietary license; no Vietnamese admission block mapping.", "Clear educational preference mapping combined with objective grade normalization."),
        ("O*NET Interest Profiler", "Robust empirical RIASEC taxonomy linking interests to occupations.", "Western labor market focus; no mapping to Vietnamese Level-IV major codes.", "Adopts Holland RIASEC as core vector, mapped directly to MOET circular catalogs."),
        ("16Personalities / CareerExplorer", "Engaging user interface and consumer-grade visual reports.", "Disconnected from national curricula, admission blocks, and verified educational syllabi.", "Binds profile assessments to national subject combinations (A00, A01, D01) and MOET codes."),
        ("MOET Admission Portal", "Authoritative data source for institutional lists and regulatory circulars.", "Static registry; dense tabular benchmarks; no personalized compatibility or roadmaps.", "Ingests official circulars (TT09 & TT74) into structured knowledge base with XAI scoring and study roadmaps.")
    ]
    t3 = doc.add_table(rows=len(t3_data) + 1, cols=4)
    t3.style = 'Table Grid'
    format_table(t3, [1.4, 1.7, 1.8, 1.6])
    t3.rows[0].cells[0].paragraphs[0].text = "Solution"
    t3.rows[0].cells[1].paragraphs[0].text = "Strength"
    t3.rows[0].cells[2].paragraphs[0].text = "Limitation for this use case"
    t3.rows[0].cells[3].paragraphs[0].text = "AI CareerGuide Response"
    for idx, (s, st, l, r) in enumerate(t3_data):
        t3.rows[idx+1].cells[0].paragraphs[0].text = s
        t3.rows[idx+1].cells[1].paragraphs[0].text = st
        t3.rows[idx+1].cells[2].paragraphs[0].text = l
        t3.rows[idx+1].cells[3].paragraphs[0].text = r
    add_caption("Table 3. Existing solution comparison and identified gaps")

    # SECTION 6
    add_heading_1("6. Objectives and Scope")
    add_heading_2("6.1. General Objective")
    doc.add_paragraph(
        "To architect, implement, evaluate, and deploy a responsive, web-based Explainable AI decision-support platform that guides Vietnamese "
        "Grade 11–12 students in analyzing their vocational interests, standardizing their academic competencies, discovering well-matched university majors "
        "grounded in official MOET circulars, and completing actionable self-directed study roadmaps without incurring unsustainable AI token expenses or privacy compromises."
    )
    add_heading_2("6.2. Specific and Measurable Objectives")
    doc.add_paragraph(
        "1. Complete Platform Delivery: Deliver a functional responsive web application covering user authentication, vocational testing, academic grade standardization, "
        "major recommendation, career role exploration, and study roadmap tracking within the 15-week Capstone 1 timeframe.\n"
        "2. Deterministic 3-Pillar XAI Engine: Implement a deterministic mathematical scoring model achieving 100% unit test coverage (Pytest), guaranteeing that identical student inputs produce identical recommendation rankings.\n"
        "3. Authoritative Major Taxonomy: Ingest and normalize official MOET Level-IV major catalogs (Circular 09/2022/TT-BGDĐT and Circular 74/2026/TT-BGDĐT) comprising 435 distinct Level-IV majors across 22 educational disciplines.\n"
        "4. Realistic Admission Feasibility (Solution B): Integrate dynamic academic clustering (High, Medium, Standard competition) and feasibility tiering (Target vs. Reach) to prevent unrealistic recommendations.\n"
        "5. Two-Stream Ingestion & Reusable Roadmap Caching: Deploy a two-stream ingestion architecture with Human-in-the-Loop (HITL) staging review, caching verified roadmaps in PostgreSQL (JSONB + pgvector) indexed by major_code with retrieval latency ≤ 1s.\n"
        "6. Dual RAG System: Configure LlamaIndex Dual RAG (Ingestion RAG for document processing + Guidance RAG for personalized task planning) backed by OpenAI embeddings and deterministic fallback templates.\n"
        "7. Security & Privacy Compliance: Enforce OWASP ASVS Level 2 security, Argon2id password hashing, Google OAuth 2.0 authentication, and Zero-PII sanitization adhering to Vietnam Personal Data Protection Law (Law No. 91/2025/QH15).\n"
        "8. Evaluation Thresholds: Attain ≥ 80% task completion and an average usability rating ≥ 3.5/5.0 in usability pilots with target high school cohorts."
    )
    add_heading_2("6.3. In Scope (MVP Baseline)")
    doc.add_paragraph(
        "• Responsive web client supporting desktop, tablet, and mobile viewports (≥ 360px).\n"
        "• User account management with Argon2id password hashing, Google OAuth 2.0, and age-appropriate data consent.\n"
        "• Standardized Holland RIASEC assessment (30 questions) and educational cognitive preference questionnaire (12 questions).\n"
        "• High school academic grade recording across semesters with national Z-score Gaussian CDF standardization.\n"
        "• Deterministic 3-pillar major compatibility scoring with component breakdowns and top supporting factors.\n"
        "• Level-IV MOET major catalog browser with career pathways, prerequisite competencies, and industry outlooks.\n"
        "• 4-week structured self-study roadmaps with milestones, curated learning resources, and progress tracking.\n"
        "• Administrative portal featuring Human-in-the-Loop (HITL) staging review for circular ingestion and AI-collected roadmaps.\n"
        "• Zero-PII sanitizer stripping emails, phone numbers, and names prior to external AI API invocation.\n"
        "• Deterministic fallback templates ensuring complete system availability during external AI API outages."
    )
    if os.path.exists(fig1_path):
        p_f1 = doc.add_paragraph()
        p_f1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_f1.add_run().add_picture(fig1_path, width=Inches(4.5))
        add_caption("Figure 1. End-to-end student guidance journey across 7 theoretical stages")

    add_heading_2("6.4. Out of Scope (MVP Baseline)")
    doc.add_paragraph(
        "• Native mobile applications (iOS/Android); responsive web is the sole deployment client.\n"
        "• Commercial billing, payment gateways, and subscription monetization.\n"
        "• Premature filtering or ranking bias based on tuition fees or geographic location.\n"
        "• Unconstrained web scraping of unverified websites.\n"
        "• End-to-end black-box neural networks for direct recommendation ranking.\n"
        "• Clinical psychological or psychiatric diagnostic evaluations."
    )

    # SECTION 7
    add_heading_1("7. Key Features & Requirements")
    add_heading_2("7.1. Functional Requirements")
    t4_data = [
        ("FR01", "Account, Consent & Identity", "System registers and authenticates users via Argon2id password hashing or official Google OAuth 2.0 flow; captures explicit personal data processing consent under Law 91/2025/QH15; manages user profiles and provides account deletion capabilities."),
        ("FR02", "Vocational & Cognitive Assessment", "Delivers versioned Holland RIASEC (30 items) and cognitive learning preference (12 items) questionnaires; calculates sub-scores deterministically; records assessment history; prevents re-submission tampering."),
        ("FR03", "Academic Grade Standardization", "Captures multi-semester 10-point scale high school grades; normalizes scores via national mean and standard deviation parameters into standard Z-scores and cumulative probabilities Φ(Z); computes composite aptitude for admission subject blocks (A00, A01, B00, C00, D01)."),
        ("FR04", "Explainable Major Recommendation", "Computes composite compatibility score across 435 Level-IV MOET majors using the 3-pillar formula; applies Solution B admission feasibility tiering (High/Medium/Standard competition; Target vs. Reach); outputs deterministic top supporting factors and competency gaps without LLM dependency."),
        ("FR05", "Major Taxonomy & Career Exploration", "Provides interactive search, multi-category filtering, and detailed exploration for 435 Level-IV majors across 22 disciplines; displays related career titles, required competencies, and industry outlooks based on Phoenix Ho Career Tree model."),
        ("FR06", "Study Roadmap & Guidance RAG", "Retrieves pre-cached 4-week structured study roadmaps indexed by major_code from PostgreSQL (JSONB + pgvector) in ≤ 1s; identifies missing competency gaps; personalizes learning tasks via Guidance RAG; serves deterministic static fallback templates if AI APIs time out; tracks student completion progress."),
        ("FR07", "Admin Ingestion & HITL Governance", "Enables authorized administrators to ingest official MOET circulars (PDF/Excel) using Qwen3-VL OCR and regex parsers (Stream A); triggers whitelisted web roadmap discovery via Tavily API and LlamaIndex (Stream B); provides a Human-in-the-Loop staging review interface to audit, approve, or reject records before knowledge-base publication.")
    ]
    t4 = doc.add_table(rows=len(t4_data) + 1, cols=3)
    t4.style = 'Table Grid'
    format_table(t4, [0.8, 1.8, 3.9])
    t4.rows[0].cells[0].paragraphs[0].text = "ID"
    t4.rows[0].cells[1].paragraphs[0].text = "Feature Module"
    t4.rows[0].cells[2].paragraphs[0].text = "System Functional Requirement"
    for idx, (fid, m, r) in enumerate(t4_data):
        t4.rows[idx+1].cells[0].paragraphs[0].text = fid
        t4.rows[idx+1].cells[1].paragraphs[0].text = m
        t4.rows[idx+1].cells[2].paragraphs[0].text = r
    add_caption("Table 4. Functional requirements catalog (FR01 – FR07)")

    if os.path.exists(fig2_path):
        p_f2 = doc.add_paragraph()
        p_f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_f2.add_run().add_picture(fig2_path, width=Inches(5.0))
        add_caption("Figure 2. AI CareerGuide system use case diagram")

    add_heading_2("7.2. Non-Functional Requirements")
    t5_data = [
        ("NFR01", "Performance & Latency", "Standard API responses ≤ 3.0s; 3-pillar recommendation scoring loop across 435 majors ≤ 2.0s; cached roadmap retrieval ≤ 1.0s; personalized Guidance RAG synthesis ≤ 8.0s with automatic fallback."),
        ("NFR02", "Security & Data Privacy", "Compliance with OWASP ASVS Level 2; TLS 1.3 encryption in transit; Argon2id password hashing (t=3, m=64MiB, p=2); JWT session tokens; Zero PII regex filtering before external AI API calls; compliance with Vietnam Law No. 91/2025/QH15."),
        ("NFR03", "Usability & Accessibility", "Fully responsive UI across viewports ≥ 360px; WCAG 2.1 AA color contrast compliance (≥ 4.5:1 for regular text); clear Vietnamese typography and intuitive step wizards."),
        ("NFR04", "Determinism & XAI Rigor", "100% reproducibility: identical profile inputs yield identical recommendation rankings and top supporting factors; scoring logic completely decoupled from non-deterministic LLMs."),
        ("NFR05", "Reliability & Resilience", "Target 99% uptime during evaluation; write-once/read-many caching minimizes external API failures; built-in static fallback templates maintain system operation during LLM outages."),
        ("NFR06", "Testability & Maintainability", "Modular monolith with clean separation of concerns; automated Pytest test suite covering 100% of scoring math and gap logic; 69 passing test cases.")
    ]
    t5 = doc.add_table(rows=len(t5_data) + 1, cols=3)
    t5.style = 'Table Grid'
    format_table(t5, [0.8, 1.8, 3.9])
    t5.rows[0].cells[0].paragraphs[0].text = "ID"
    t5.rows[0].cells[1].paragraphs[0].text = "Quality Attribute"
    t5.rows[0].cells[2].paragraphs[0].text = "Measurable Requirement Specification"
    for idx, (nid, c, r) in enumerate(t5_data):
        t5.rows[idx+1].cells[0].paragraphs[0].text = nid
        t5.rows[idx+1].cells[1].paragraphs[0].text = c
        t5.rows[idx+1].cells[2].paragraphs[0].text = r
    add_caption("Table 5. Non-functional quality requirements (NFR01 – NFR06)")

    add_heading_2("7.3. Recommendation Logic, Theoretical Grounding, and XAI Formulations")
    doc.add_paragraph(
        "The system grounds all guidance in 5 established theoretical models:\n"
        "1. Holland RIASEC Theory (1997): Evaluates congruence between student personality types (Realistic, Investigative, Artistic, Social, Enterprising, Conventional) and university training environments.\n"
        "2. Gardner's Multiple Intelligences (1983) & MBTI Dimensions: Informs cognitive preference evaluation (abstract thinking, analytical reasoning, spatial perception, linguistic ability, learning environment, teamwork intensity).\n"
        "3. Phoenix Ho Career Tree Model (2020): Connects roots (personality, values, interests), trunk (academic readiness, core competencies), and branches/fruits (majors, careers, societal contribution).\n"
        "4. Locke & Latham Goal-Setting Theory (2002): Drives the 4-week structured roadmap with specific, challenging, and measurable learning milestones.\n\n"
        "Mathematical 3-Pillar Formulation:\n"
        "S(u, m) = 100 × [ w1 · S_RIASEC(u, m) + w2 · S_Academic(u, m) + w3 · S_Cognitive(u, m) ]\n"
        "Baseline weights are configured as: w1 = 0.45, w2 = 0.35, w3 = 0.20 (constrained to w1 + w2 + w3 = 1.0).\n\n"
        "• Pillar 1 (RIASEC Cosine Similarity, 45%): S_RIASEC = (V_student · V_major) / (||V_student|| × ||V_major||)\n"
        "• Pillar 2 (Academic Readiness via Z-Score & Gaussian CDF, 35%): Z = (X - μ) / σ; Φ(Z) = 0.5 * [1 + erf(Z / sqrt(2))]. S_Academic is evaluated on the highest-performing admitted subject combination accepted by the major.\n"
        "• Pillar 3 (Cognitive Trait Matching, 20%): Evaluates ordinal traits and categorical traits (learning environment, teamwork intensity) via deterministic rule matrices.\n\n"
        "Solution B: Dynamic Academic Clustering & Admission Feasibility Tiering\n"
        "To avoid misleading students (e.g. suggesting Medicine for a 15-point student), the engine dynamically evaluates major competition:\n"
        "• High Competition (≥ 24.5 pts): Medicine, Dentistry, Computer Science, AI, International Business.\n"
        "• Medium Competition (≥ 19.5 pts): Software Engineering, Finance, Marketing, Law, English Studies.\n"
        "• Standard Competition (≥ 15.0 pts): Biotechnology, Agriculture, Environmental Science, Sociology.\n"
        "Students are classified into TARGET (Khả thi cao, safe zone) or REACH (Thử thách cao, score gap) with encouraging and honest educational advice."
    )
    if os.path.exists(fig3_path):
        p_f3 = doc.add_paragraph()
        p_f3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_f3.add_run().add_picture(fig3_path, width=Inches(5.0))
        add_caption("Figure 3. Explainable 3-pillar recommendation and feasibility tiering workflow")

    add_heading_2("7.4. Two-Stream Knowledge Ingestion and Dual RAG Pipeline")
    doc.add_paragraph(
        "AI CareerGuide employs a Two-Stream Knowledge Ingestion Architecture:\n"
        "• Stream A – Core Major Profiles (Official MOET Circulars): Ingests official regulatory PDF/Excel circulars (Circular 09/2022 and Circular 74/2026). "
        "Utilizes multimodal AI Vision (Qwen3-VL) and regex parsers to extract Level-IV codes, standardized names, disciplines, and admission blocks directly into staging.\n"
        "• Stream B – Automated Roadmap Discovery & Reusable Caching: Discovers syllabi and learning roadmaps strictly from whitelisted academic domains "
        "(edu.vn, mit.edu, stanford.edu, coursera.org, roadmap.sh) using Tavily Search API and Jina Reader. LlamaIndex and Pydantic v2 schemas normalize learning milestones and competencies.\n"
        "• Human-in-the-Loop (HITL) Review: Staged roadmaps undergo mandatory administrator verification. Approved roadmaps are committed to PostgreSQL (JSONB) "
        "and indexed with OpenAI vector embeddings (pgvector) by major_code. Subsequent student requests retrieve cached roadmaps in milliseconds (≤ 1s), "
        "eliminating redundant external search and LLM costs."
    )

    add_heading_2("7.5. Architectural Boundary Isolation Matrix")
    t6_data = [
        ("Backend (FastAPI)", "Calculates 3-pillar compatibility scores; identifies missing skills (gap analysis); validates prerequisites and diagnostic test results; validates LLM outputs; serves static fallback roadmaps.", "Never delegates mathematical scoring or prerequisite logic to external LLMs."),
        ("PostgreSQL (Relational + JSONB)", "Stores the 435 official MOET major profiles, skill taxonomies, normalized roadmap structures (JSONB keyed by major_code), source citations/URLs, moderation statuses, and student progress records.", "Never exposes unapproved (PENDING) staging records to student-facing endpoints."),
        ("pgvector + LlamaIndex", "Manages document chunking, vector indexing, metadata filtering (by major_code and skill ID), and semantic retrieval strictly from the approved knowledge base.", "Never retrieves from unverified external web sources during live student ranking flows."),
        ("External AI API + Tavily", "Assists in initial resource discovery from whitelisted domains (Ingestion phase); explains academic concepts, personalizes study schedules, and formats actionable self-study tasks based on retrieved context.", "Prohibited from treating unverified documents as fact, fabricating citations, generating detailed roadmaps without grounded data, or altering major rankings."),
        ("Administrator", "Audits staged major records and AI-collected roadmaps, verifies source credibility and prerequisite links, and approves content before publication to the official knowledge base.", "Does not manually author full curriculums for all 435 majors from scratch.")
    ]
    t6 = doc.add_table(rows=len(t6_data) + 1, cols=3)
    t6.style = 'Table Grid'
    format_table(t6, [1.5, 2.7, 2.3])
    t6.rows[0].cells[0].paragraphs[0].text = "System Component"
    t6.rows[0].cells[1].paragraphs[0].text = "Designated Technical Responsibilities"
    t6.rows[0].cells[2].paragraphs[0].text = "Strict Prohibitions & Guardrails"
    for idx, (c, r, p) in enumerate(t6_data):
        t6.rows[idx+1].cells[0].paragraphs[0].text = c
        t6.rows[idx+1].cells[1].paragraphs[0].text = r
        t6.rows[idx+1].cells[2].paragraphs[0].text = p
    add_caption("Table 6. Architectural component responsibility and boundary isolation matrix")

    # SECTION 8
    add_heading_1("8. Constraints and Assumptions")
    add_heading_2("8.1. System Constraints")
    t7_data = [
        ("Pure Guidance Scope", "Functional", "Tuition fees and geographical location filters are strictly excluded to avoid socio-economic bias."),
        ("Time and Team", "Schedule", "Five students and a 15-week academic schedule limit the number of roles, platforms, integrations, and evaluation cycles. Managed via 2-week Agile sprints."),
        ("Assessment Validity / Licensing", "Domain / Legal", "An unofficial questionnaire cannot be represented as the licensed official MBTI instrument. Clear educational preference naming and disclaimers."),
        ("AI Cost & Latency", "Operational", "Write-once/read-many caching in PostgreSQL eliminates redundant external API calls; free-tier/low-cost providers utilized with deterministic fallback templates."),
        ("Privacy and Minors", "Legal", "Academic and assessment data about minors require enhanced protection under Vietnamese Data Protection Law (Law No. 91/2025/QH15) and OWASP ASVS Level 2.")
    ]
    t7 = doc.add_table(rows=len(t7_data) + 1, cols=3)
    t7.style = 'Table Grid'
    format_table(t7, [1.5, 1.2, 3.8])
    t7.rows[0].cells[0].paragraphs[0].text = "Constraint Domain"
    t7.rows[0].cells[1].paragraphs[0].text = "Category"
    t7.rows[0].cells[2].paragraphs[0].text = "Description & Engineering Response"
    for idx, (d, c, resp) in enumerate(t7_data):
        t7.rows[idx+1].cells[0].paragraphs[0].text = d
        t7.rows[idx+1].cells[1].paragraphs[0].text = c
        t7.rows[idx+1].cells[2].paragraphs[0].text = resp
    add_caption("Table 7. Project constraints and engineering responses")

    add_heading_2("8.2. Operational Assumptions")
    doc.add_paragraph(
        "1. Primary users have access to a modern browser and an internet connection; the interface remains usable on a smartphone screen (≥ 360px width).\n"
        "2. Students provide reasonably accurate self-reported academic grades; the system will not independently verify school transcripts in the MVP.\n"
        "3. Official MOET admission circulars (Circular 09/2022 and Circular 74/2026) remain publicly accessible for administrative ingestion.\n"
        "4. Standardized national Z-score parameters effectively represent grading distributions across high schools."
    )

    # SECTION 9
    add_heading_1("9. Target Users / Stakeholders")
    t8_data = [
        ("Grade 11-12 students", "Primary user", "Takes assessments, inputs grades, explores major fit, views gap analyses, and executes personalized self-study roadmaps.", "Full student journey"),
        ("Parents / guardians", "Supporting stakeholder", "Reviews exported summary reports and understands evidence without replacing student agency.", "Student-shared report; no dedicated account in MVP"),
        ("Career counselors / teachers", "Domain stakeholder", "Review reasoning, discuss alternatives, validate recommendations using objective breakdowns.", "Reviewer feedback and counselor guidance mode"),
        ("System administrator", "Operational user", "Maintain questions, upload circulars, trigger roadmap ingestion, and approve records in HITL UI.", "Role-restricted admin module")
    ]
    t8 = doc.add_table(rows=len(t8_data) + 1, cols=4)
    t8.style = 'Table Grid'
    format_table(t8, [1.4, 1.3, 2.5, 1.3])
    t8.rows[0].cells[0].paragraphs[0].text = "Group"
    t8.rows[0].cells[1].paragraphs[0].text = "Role"
    t8.rows[0].cells[2].paragraphs[0].text = "Primary Need / Benefit"
    t8.rows[0].cells[3].paragraphs[0].text = "MVP Relationship"
    for idx, (g, r, n, rel) in enumerate(t8_data):
        t8.rows[idx+1].cells[0].paragraphs[0].text = g
        t8.rows[idx+1].cells[1].paragraphs[0].text = r
        t8.rows[idx+1].cells[2].paragraphs[0].text = n
        t8.rows[idx+1].cells[3].paragraphs[0].text = rel
    add_caption("Table 8. Target user profiles and stakeholder mapping")

    # SECTION 10
    add_heading_1("10. Technology Stack")
    t9_data = [
        ("Frontend SPA", "React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons", "Delivers accessible, high-performance responsive user interface down to 360px screen width."),
        ("Backend REST API", "Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 Async", "Asynchronous API execution, strict schema validation, deterministic gap/prerequisite logic."),
        ("Security & Auth", "Argon2id (argon2-cffi), PyJWT, Google OAuth 2.0, Zero-PII Regex Sanitizer", "OWASP ASVS Level 2 compliant password hashing, secure session management, and regulatory privacy compliance (Law 91/2025/QH15)."),
        ("Database & Cache", "PostgreSQL 16 + pgvector extension + JSONB", "Unified storage for relational major profiles, reusable major_code-indexed study roadmaps (JSONB), and vector embeddings (pgvector)."),
        ("RAG Framework", "LlamaIndex, OpenAI text-embedding-3-small, Pydantic v2", "Single unified framework for document parsing, semantic chunking, vector indexing, metadata-filtered retrieval, and managing Dual RAG pipelines."),
        ("LLM & Search", "OpenAI API (gpt-4o-mini), DeepSeek V4.1, Qwen3-VL OCR, Tavily Search API", "Generates 1536-dimensional vector embeddings, performs whitelisted web discovery, and personalizes study plans from cached DB context."),
        ("DevOps & Testing", "Docker, Docker Compose, GitHub Actions, Pytest, Playwright, Vercel, Render", "Containerized deployment, automated CI pipelines, 69 Pytest automated tests (100% pass), and cloud deployment.")
    ]
    t9 = doc.add_table(rows=len(t9_data) + 1, cols=3)
    t9.style = 'Table Grid'
    format_table(t9, [1.5, 2.2, 2.8])
    t9.rows[0].cells[0].paragraphs[0].text = "Layer"
    t9.rows[0].cells[1].paragraphs[0].text = "Selected Technology"
    t9.rows[0].cells[2].paragraphs[0].text = "Rationale & Purpose"
    for idx, (l, t, p) in enumerate(t9_data):
        t9.rows[idx+1].cells[0].paragraphs[0].text = l
        t9.rows[idx+1].cells[1].paragraphs[0].text = t
        t9.rows[idx+1].cells[2].paragraphs[0].text = p
    add_caption("Table 9. Unified technology stack architecture")

    # SECTION 11
    add_heading_1("11. Methodology & Development Plan")
    add_heading_2("11.1. Agile Scrum Framework")
    doc.add_paragraph(
        "The project applies Scrum with 2-week iterations; the final release window is aligned with the official Capstone schedule. "
        "The project uses a prioritized Product Backlog, Sprint Planning, short daily coordination, Sprint Review, and Retrospective. "
        "Each feature is accepted only when its code, tests, documentation, and privacy/data checks meet the Definition of Done."
    )
    add_heading_2("11.2. 15-Week Sprint Implementation Roadmap")
    t10_data = [
        ("Sprint 0", "Wk 1–2", "Problem validation, architecture design, PostgreSQL + pgvector schema definition, UI wireframing.", "Approved scope, prototype, schema, evaluation plan"),
        ("Sprint 1", "Wk 3–4", "FR01 Authentication with Argon2id, Google OAuth 2.0, Law 91/2025 consent tracking, student profile, base CI/CD.", "Secure profile flow and deployment skeleton"),
        ("Sprint 2", "Wk 5–6", "FR02 RIASEC and preference questionnaires, deterministic scoring implementation, result visualization.", "Versioned assessments with unit tests"),
        ("Sprint 3", "Wk 7–8", "FR03 Academic input, Z-score standardization, FR04 3-pillar XAI hybrid recommender, Solution B feasibility tiering.", "Top-major ranking with related careers/skills and component explanations"),
        ("Sprint 4", "Wk 9–10", "FR07 Two-stream ingestion (MOET PDF parser via Qwen3-VL + Tavily search discovery), staging DB, and HITL review UI.", "Verified pilot catalogue and HITL review pipeline"),
        ("Sprint 5", "Wk 11–12", "FR05 MOET Level-IV taxonomy (435 majors), FR06 roadmap engine, cached JSONB roadmap lookup (≤ 1s), Guidance RAG.", "End-to-end student journey and cached guidance"),
        ("Sprint 6", "Wk 13–14", "Integration, Zero-PII sanitizer verification, static fallback testing, usability pilot evaluation, and bug fixes.", "Release candidate and evaluation results"),
        ("Release", "Wk 15", "Production deployment on Vercel & Render, final documentation, demo video, and Capstone 1 defense presentation.", "MVP, source code, reports, final demonstration")
    ]
    t10 = doc.add_table(rows=len(t10_data) + 1, cols=4)
    t10.style = 'Table Grid'
    format_table(t10, [0.9, 0.8, 3.2, 1.6])
    t10.rows[0].cells[0].paragraphs[0].text = "Iteration"
    t10.rows[0].cells[1].paragraphs[0].text = "Time"
    t10.rows[0].cells[2].paragraphs[0].text = "Key Deliverables & Technical Objectives"
    t10.rows[0].cells[3].paragraphs[0].text = "Exit Deliverable"
    for idx, (it, ti, f, e) in enumerate(t10_data):
        t10.rows[idx+1].cells[0].paragraphs[0].text = it
        t10.rows[idx+1].cells[1].paragraphs[0].text = ti
        t10.rows[idx+1].cells[2].paragraphs[0].text = f
        t10.rows[idx+1].cells[3].paragraphs[0].text = e
    add_caption("Table 10. Fifteen-week agile sprint development plan")

    add_heading_2("11.3. Quality Gates & Definition of Done")
    doc.add_paragraph(
        "A user story is accepted as Done only when: (1) Code passes all automated Pytest unit and integration tests with zero failures; "
        "(2) Code passes ESLint / TypeScript type compilation checks with zero errors; (3) Security, Zero-PII sanitization, and authorization boundaries "
        "are verified; (4) Peer code review is completed and approved by the System Architect or Project Leader."
    )

    # SECTION 12
    add_heading_1("12. System Architecture Overview")
    add_heading_2("12.1. 3-Tier Modular Monolith Architecture")
    doc.add_paragraph(
        "AI CareerGuide uses a 3-Tier Modular Monolith architecture: a responsive React 18 client, a FastAPI application divided into 6 domain modules "
        "(identity, assessment, recommender, taxonomy, gap_roadmap_engine, llamaindex_rag_orchestrator), and a unified PostgreSQL 16 persistence layer "
        "(Relational tables + JSONB Roadmap Cache + pgvector extension)."
    )
    if os.path.exists(fig4_path):
        p_f4 = doc.add_paragraph()
        p_f4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_f4.add_run().add_picture(fig4_path, width=Inches(5.2))
        add_caption("Figure 4. AI CareerGuide system context and logical architecture")

    add_heading_2("12.3. Principal Data Flows")
    t11_data = [
        ("DF01: Assessment flow", "Student answers -> validation -> deterministic dimension scoring -> versioned result -> profile evidence"),
        ("DF02: Recommendation flow", "Profile and scores -> feature normalization -> 3-pillar weighted ranking -> Solution B feasibility -> top supporting factors & competency gaps -> student dashboard"),
        ("DF03: Ingestion flow", "Official MOET circulars (Stream A via Qwen3-VL OCR) and whitelisted web syllabi (Stream B via Tavily/Jina) -> LlamaIndex chunking -> Staging DB (status: PENDING)"),
        ("DF04: HITL Review flow", "Admin audits staged records in HITL UI -> validates citations/deduplication -> approves publication (status: APPROVED) -> saved to PostgreSQL (JSONB + pgvector) indexed by major_code"),
        ("DF05: Roadmap & Guidance flow", "Selected target major_code -> instant cached JSONB lookup (≤ 1s) -> Guidance RAG personalizes study tasks -> student progress tracking (with static fallback templates on timeout)")
    ]
    t11 = doc.add_table(rows=len(t11_data) + 1, cols=2)
    t11.style = 'Table Grid'
    format_table(t11, [2.0, 4.5])
    t11.rows[0].cells[0].paragraphs[0].text = "Flow ID & Name"
    t11.rows[0].cells[1].paragraphs[0].text = "Data Payload & Processing Sequence"
    for idx, (f, s) in enumerate(t11_data):
        t11.rows[idx+1].cells[0].paragraphs[0].text = f
        t11.rows[idx+1].cells[1].paragraphs[0].text = s
    add_caption("Table 11. Principal system data flow definitions")

    add_heading_2("12.4. Security, Zero-PII Sanitization, and Legal Compliance")
    doc.add_paragraph(
        "1. Zero-PII Architecture: To guarantee total compliance with Vietnam's Law No. 91/2025/QH15 on Personal Data Protection and Decree 13/2023/NĐ-CP, "
        "no student names, email addresses, phone numbers, or academic transcripts are ever transmitted to external AI APIs. A dedicated regex sanitization filter "
        "automatically redacts sensitive tokens before prompt dispatch.\n"
        "2. OWASP ASVS Level 2 Security: User passwords are encrypted with Argon2id (memory-hard against GPU brute-force attacks). Stateless JWT tokens with strict "
        "expiration validate authorization across role boundaries.\n"
        "3. Deterministic Resilience: The core recommendation engine operates without external API dependencies. If external LLMs or search APIs become unreachable, "
        "the system seamlessly serves pre-cached JSONB roadmaps and deterministic static fallback templates."
    )

    # SECTION 13
    add_heading_1("13. Potential Risks and Mitigation Strategies")
    t12_data = [
        ("AI Hallucinations", "Generative models invent non-existent majors or inaccurate admission advice.", "High", "Medium", "Decouple recommendation scoring 100% from LLMs; ground Guidance RAG strictly in verified PostgreSQL data; implement static fallback templates."),
        ("PDF & OCR Parsing Errors", "Formatting irregularities in official circular PDFs degrade data extraction.", "High", "Medium", "Integrate multimodal Qwen3-VL OCR combined with mandatory Human-in-the-Loop (HITL) admin review before publishing."),
        ("High AI Token & Latency Costs", "Repeated external LLM and search calls cause budget overruns and slow UI response.", "Medium", "High", "Implement write-once/read-many caching in PostgreSQL (JSONB + pgvector) indexed by major_code (≤ 1s retrieval)."),
        ("External API Outages", "OpenAI, DeepSeek, or Tavily APIs experience temporary downtime.", "Medium", "Medium", "Implement timeout handlers (8s) and serve deterministic pre-cached roadmaps and static guidance templates."),
        ("Privacy Breach of Minor Data", "Unauthorized access to high school student academic or psychometric records.", "High", "Low", "Enforce Argon2id hashing, least-privilege RBAC, Zero-PII sanitization, and automated privacy testing.")
    ]
    t12 = doc.add_table(rows=len(t12_data) + 1, cols=5)
    t12.style = 'Table Grid'
    format_table(t12, [1.3, 1.8, 0.7, 0.7, 2.0])
    t12.rows[0].cells[0].paragraphs[0].text = "Risk Domain"
    t12.rows[0].cells[1].paragraphs[0].text = "Risk Description"
    t12.rows[0].cells[2].paragraphs[0].text = "Severity"
    t12.rows[0].cells[3].paragraphs[0].text = "Likelihood"
    t12.rows[0].cells[4].paragraphs[0].text = "Mitigation & Contingency Strategy"
    for idx, (c, r, p, i, m) in enumerate(t12_data):
        t12.rows[idx+1].cells[0].paragraphs[0].text = c
        t12.rows[idx+1].cells[1].paragraphs[0].text = r
        t12.rows[idx+1].cells[2].paragraphs[0].text = p
        t12.rows[idx+1].cells[3].paragraphs[0].text = i
        t12.rows[idx+1].cells[4].paragraphs[0].text = m
    add_caption("Table 12. Risk register and mitigation matrix")

    # SECTION 14
    add_heading_1("14. Expected Outcomes / Deliverables")
    t13_data = [
        ("D1", "Production Web Application", "Fully deployed responsive web application on Vercel (Frontend) and Render (Backend) supporting desktop and mobile viewports (≥ 360px)."),
        ("D2", "Deterministic XAI Engine", "Python scoring engine implementing RIASEC Cosine Similarity, Z-score Gaussian CDF, cognitive trait rules, and Solution B feasibility tiering (100% unit test pass)."),
        ("D3", "MOET Major Knowledge Base", "Structured PostgreSQL database containing 435 Level-IV major profiles across 22 disciplines (Circulars 09/2022 and 74/2026), career paths, and skill taxonomies."),
        ("D4", "Reusable Roadmap Cache & Dual RAG", "Cached study roadmaps indexed by major_code in JSONB and pgvector, supported by LlamaIndex Ingestion & Guidance RAG pipelines with HITL staging UI."),
        ("D5", "Source Code & Test Suite", "Clean Git repository containing frontend and backend codebases, Docker Compose files, and 69 automated Pytest test cases (100% pass)."),
        ("D6", "Engineering Documentation", "Comprehensive Capstone documentation including SRS, System Architecture Document, Test Reports, and Operations Manual."),
        ("D7", "Evaluation Assets", "Usability pilot evaluation report (≥ 20 participants, target rating ≥ 3.5/5.0), demonstration script, and presentation slides.")
    ]
    t13 = doc.add_table(rows=len(t13_data) + 1, cols=3)
    t13.style = 'Table Grid'
    format_table(t13, [0.6, 2.1, 3.8])
    t13.rows[0].cells[0].paragraphs[0].text = "ID"
    t13.rows[0].cells[1].paragraphs[0].text = "Deliverable"
    t13.rows[0].cells[2].paragraphs[0].text = "Acceptance Content & Deliverable Scope"
    for idx, (did, d, c) in enumerate(t13_data):
        t13.rows[idx+1].cells[0].paragraphs[0].text = did
        t13.rows[idx+1].cells[1].paragraphs[0].text = d
        t13.rows[idx+1].cells[2].paragraphs[0].text = c
    add_caption("Table 13. Project deliverables catalog")

    # SECTION 15
    add_heading_1("15. References")
    refs = [
        "[1] National Center for O*NET Development, \"O*NET Interest Profiler,\" O*NET Resource Center, 2026. https://www.onetcenter.org/IP.html",
        "[2] J. L. Holland, \"Making Vocational Choices: A Theory of Vocational Personalities and Work Environments,\" 3rd ed., Psychological Assessment Resources, Odessa, FL, 1997.",
        "[3] H. Gardner, \"Frames of Mind: The Theory of Multiple Intelligences,\" Basic Books, New York, 1983.",
        "[4] Phoenix Ho, \"Dung Ngoi Cho Co Hoi Den (Career Tree Guidance Framework),\" Tre Publishing House, Ho Chi Minh City, 2020.",
        "[5] Ministry of Education and Training of Vietnam, \"Circular 09/2022/TT-BGDĐT: Regulations on the List of Higher Education Training Programs,\" MOET, Hanoi, 2022.",
        "[6] Ministry of Education and Training of Vietnam, \"Circular 74/2026/TT-BGDĐT: Promulgating the List of Level-IV Higher Education Training Programs,\" MOET, Hanoi, 2026.",
        "[7] National Assembly of Vietnam, \"Law No. 91/2025/QH15 on Personal Data Protection,\" Hanoi, 2025.",
        "[8] Government of Vietnam, \"Decree No. 13/2023/NĐ-CP on Personal Data Protection,\" Hanoi, 2023.",
        "[9] OWASP Foundation, \"Application Security Verification Standard (ASVS), Version 5.0,\" OWASP, 2025. https://owasp.org/www-project-application-security-verification-standard/",
        "[10] ISO/IEC 25010:2023, \"Systems and Software Engineering – Systems and Software Quality Requirements and Evaluation (SQuaRE) – Product Quality Model,\" ISO, 2023.",
        "[11] K. Schwaber and J. Sutherland, \"The Scrum Guide,\" Scrum.org, 2020. https://scrumguides.org/docs/scrumguide/v2020/2020-Scrum-Guide-US.pdf",
        "[12] E. A. Locke and G. P. Latham, \"Building a Practically Useful Theory of Goal Setting and Task Motivation,\" American Psychologist, vol. 57, no. 9, pp. 705–717, 2002.",
        "[13] P. Lewis et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" Advances in Neural Information Processing Systems (NeurIPS), 2020.",
        "[14] PostgreSQL Global Development Group, \"pgvector: Open-source Vector Similarity Search for PostgreSQL,\" 2026. https://github.com/pgvector/pgvector",
        "[15] J. Liu, \"LlamaIndex: Data Framework for LLM Applications,\" 2026. https://www.llamaindex.ai/"
    ]
    for r in refs:
        p_ref = doc.add_paragraph(r)
        p_ref.paragraph_format.space_after = Pt(3)

    doc.save(output_path)
    print(f"Successfully generated proposal document at: {output_path}")

if __name__ == "__main__":
    out_file = r"E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\Document\C1SE71_Proposal_ver1.1.docx"
    create_proposal_docx(out_file)
