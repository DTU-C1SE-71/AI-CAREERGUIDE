export interface CognitiveOption {
  option_key: string
  trait_code?: string
  title: string
  description: string
}

export interface CognitiveQuestionItem {
  code: string
  dimension?: string
  dimension_badge?: string
  title: string
  subtitle?: string
  options: CognitiveOption[]
}

export const defaultCognitiveQuestions: CognitiveQuestionItem[] = [
  {
    "code": "COG_1",
    "dimension": "learning_style",
    "dimension_badge": "Phong cách Tiếp thu Kiến thức",
    "title": "1. Phong cách Tiếp thu Kiến thức",
    "subtitle": "Bạn hiểu sâu và nhớ lâu một kiến thức mới nhất khi được tiếp cận theo cách nào?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "LEARN_VISUAL_SPATIAL",
        "title": "Trực quan & Mô hình hóa",
        "description": "Học nhanh qua sơ đồ tư duy, bản vẽ 3D, hình ảnh minh họa, bản đồ và video mô phỏng."
      },
      {
        "option_key": "B",
        "trait_code": "LEARN_THEORETICAL_ANALYTICAL",
        "title": "Đọc hiểu & Suy luận Nguyên lý",
        "description": "Thích đọc giáo trình chuyên sâu, phân tích định lý, công thức và hiểu rõ căn nguyên lý thuyết."
      },
      {
        "option_key": "C",
        "trait_code": "LEARN_HANDS_ON_PRACTICAL",
        "title": "Thực hành & Thao tác Thực tế",
        "description": "Phải tự tay làm thí nghiệm, lắp ráp, viết code, thực hành lâm sàng hoặc ra thực địa mới nắm chắc."
      },
      {
        "option_key": "D",
        "trait_code": "LEARN_INTERACTIVE_CASE",
        "title": "Thảo luận & Phân tích Tình huống",
        "description": "Học hiệu quả nhất khi trao đổi nhóm, tranh biện, đóng vai và giải quyết các tình huống (Case Study) thực tiễn."
      }
    ]
  },
  {
    "code": "COG_2",
    "dimension": "work_environment",
    "dimension_badge": "Môi trường Học tập & Làm việc Ưa thích",
    "title": "2. Môi trường Học tập & Làm việc Ưa thích",
    "subtitle": "Không gian nào giúp bạn phát huy tối đa sự tập trung và cảm hứng mỗi ngày?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "ENV_LAB_DIGITAL_QUIET",
        "title": "Phòng Lab, Trung tâm Dữ liệu & Không gian Yên tĩnh",
        "description": "Môi trường hiện đại, yên tĩnh để tập trung sâu vào máy tính, thiết bị nghiên cứu hoặc sáng tác cá nhân."
      },
      {
        "option_key": "B",
        "trait_code": "ENV_DYNAMIC_CORPORATE",
        "title": "Văn phòng Năng động & Giao thương Mở",
        "description": "Môi trường doanh nghiệp, truyền thông, sự kiện, thường xuyên kết nối đối tác và khách hàng."
      },
      {
        "option_key": "C",
        "trait_code": "ENV_FIELD_INDUSTRIAL",
        "title": "Công trường, Nhà máy & Thực địa Ngoài trời",
        "description": "Không thích ngồi yên một chỗ; thích di chuyển tại công trình, nhà máy thông minh, nông trại hoặc cảng vận tải."
      },
      {
        "option_key": "D",
        "trait_code": "ENV_INSTITUTIONAL_SERVICE",
        "title": "Trường học, Bệnh viện & Cơ quan Chuẩn mực",
        "description": "Môi trường có tính chuyên môn và kỷ luật cao như giảng đường, cơ sở y tế, tòa án hoặc tổ chức xã hội."
      }
    ]
  },
  {
    "code": "COG_3",
    "dimension": "problem_solving",
    "dimension_badge": "Phương pháp Giải quyết Vấn đề",
    "title": "3. Phương pháp Giải quyết Vấn đề",
    "subtitle": "Khi đứng trước một thử thách phức tạp, phản xạ tự nhiên đầu tiên của bạn là gì?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "SOLVE_QUANTITATIVE_LOGIC",
        "title": "Phân tích Định lượng & Logic Khoa học",
        "description": "Thu thập dữ liệu, đo lường thông số, lập mô hình toán học hoặc kiểm chứng bằng thực nghiệm."
      },
      {
        "option_key": "B",
        "trait_code": "SOLVE_CREATIVE_DIVERGENT",
        "title": "Tư duy Sáng tạo & Đột phá Thẩm mỹ",
        "description": "Tìm kiếm góc nhìn mới lạ, vượt qua lối mòn để tạo ra giải pháp giàu tính nghệ thuật và cảm xúc."
      },
      {
        "option_key": "C",
        "trait_code": "SOLVE_HUMAN_EMPATHY",
        "title": "Thấu cảm & Đặt Con người làm Trung tâm",
        "description": "Lắng nghe nhu cầu, cân nhắc tác động tâm lý, sức khỏe và sự phát triển bền vững của cộng đồng."
      },
      {
        "option_key": "D",
        "trait_code": "SOLVE_PROCEDURAL_STRATEGIC",
        "title": "Chiếu theo Quy chuẩn, Pháp lý & Hiệu quả Kinh tế",
        "description": "Áp dụng quy định pháp luật, tiêu chuẩn quản trị rủi ro và bài toán tối ưu chi phí - nguồn lực."
      }
    ]
  },
  {
    "code": "COG_4",
    "dimension": "interaction_target",
    "dimension_badge": "Đối tượng Tương tác Chính trong Công việc",
    "title": "4. Đối tượng Tương tác Chính trong Công việc",
    "subtitle": "Bạn muốn làm việc trực tiếp với đối tượng nào nhiều nhất trong sự nghiệp tương lai?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "TARGET_SYSTEMS_MACHINES",
        "title": "Hệ thống Phần mềm, Máy móc & Công trình",
        "description": "Tương tác với mã nguồn, vi mạch, robot, dây chuyền công nghiệp hoặc kết cấu hạ tầng."
      },
      {
        "option_key": "B",
        "trait_code": "TARGET_DATA_FINANCE_LAW",
        "title": "Dữ liệu, Báo cáo Tài chính & Văn bản Pháp lý",
        "description": "Tương tác với con số thống kê, dòng tiền, hồ sơ kiểm toán, hợp đồng và quy định nhà nước."
      },
      {
        "option_key": "C",
        "trait_code": "TARGET_PEOPLE_COMMUNITY",
        "title": "Con người, Học sinh, Bệnh nhân & Khách hàng",
        "description": "Trực tiếp giảng dạy, khám chữa bệnh, tư vấn tâm lý, truyền thông hoặc chăm sóc khách hàng."
      },
      {
        "option_key": "D",
        "trait_code": "TARGET_NATURE_BIO_ART",
        "title": "Sinh vật Sống, Tự nhiên & Tác phẩm Nghệ thuật",
        "description": "Tương tác với công nghệ sinh học, cây trồng, thú y, môi trường tự nhiên hoặc sáng tạo nghệ thuật."
      }
    ]
  },
  {
    "code": "COG_5",
    "dimension": "gardner_intelligence",
    "dimension_badge": "Thế mạnh Trí thông minh Đa diện (Howard Gardner)",
    "title": "5. Thế mạnh Trí thông minh Đa diện (Howard Gardner)",
    "subtitle": "Khả năng bẩm sinh nào dưới đây giúp bạn tự tin nhất khi học tập?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "GARDNER_LOGICAL_MATH",
        "title": "Trí thông minh Logic - Toán học",
        "description": "Nhạy bén với con số, thuật toán, suy luận nhân quả và cấu trúc hệ thống chặt chẽ."
      },
      {
        "option_key": "B",
        "trait_code": "GARDNER_LINGUISTIC_INTERPERSONAL",
        "title": "Trí thông minh Ngôn ngữ & Tương tác Xã hội",
        "description": "Giỏi diễn đạt, viết lách, học ngoại ngữ, thuyết phục và đọc vị cảm xúc của người đối diện."
      },
      {
        "option_key": "C",
        "trait_code": "GARDNER_SPATIAL_MUSICAL",
        "title": "Trí thông minh Không gian - Thị giác & Âm nhạc",
        "description": "Tưởng tượng hình học 3D sắc nét, nhạy cảm với màu sắc, bố cục hình ảnh, âm thanh và nhịp điệu."
      },
      {
        "option_key": "D",
        "trait_code": "GARDNER_NATURALIST_KINESTHETIC",
        "title": "Trí thông minh Tự nhiên - Sinh học & Vận động",
        "description": "Quan sát tinh tế thế giới sinh vật, hóa sinh, y học hoặc có đôi tay khéo léo, thể chất dẻo dai."
      }
    ]
  },
  {
    "code": "COG_6",
    "dimension": "pressure_tolerance",
    "dimension_badge": "Khả năng Thích ứng với Áp lực Đặc thù",
    "title": "6. Khả năng Thích ứng với Áp lực Đặc thù",
    "subtitle": "Kiểu thử thách nào bạn sẵn sàng chấp nhận để đánh đổi lấy thành tựu nghề nghiệp?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "PRESSURE_HIGH_STAKES_VITAL",
        "title": "Trách nhiệm Sinh mạng & Tình huống Khẩn cấp",
        "description": "Bình tĩnh, chính xác tuyệt đối khi trực cấp cứu y tế, điều tra an ninh hoặc vận hành an toàn bay/hàng hải."
      },
      {
        "option_key": "B",
        "trait_code": "PRESSURE_MARKET_DEADLINE",
        "title": "Áp lực Thương trường, Doanh số & Truyền thông",
        "description": "Hứng khởi trước nhịp độ nhanh, cạnh tranh thị trường, chỉ số KPI kinh doanh và thời hạn sự kiện."
      },
      {
        "option_key": "C",
        "trait_code": "PRESSURE_DEEP_RND_COMPLEXITY",
        "title": "Áp lực Giải quyết Bài toán Kỹ thuật & Học thuật Khó",
        "description": "Kiên trì nhiều tuần liền để tìm lỗi phần mềm, thiết kế vi mạch, giải bài toán khoa học hoặc đồ án kiến trúc."
      },
      {
        "option_key": "D",
        "trait_code": "PRESSURE_STABLE_SUSTAINABLE",
        "title": "Ưu tiên Sự Bền vững, Chuẩn mực & Có Kế hoạch",
        "description": "Phát huy tốt nhất trong công việc có lộ trình rõ ràng như giảng dạy, kế toán, hành chính, nông lâm và môi trường."
      }
    ]
  },
  {
    "code": "COG_7",
    "dimension": "output_preference",
    "dimension_badge": "Thành quả Đầu ra Mang lại Động lực Lớn nhất",
    "title": "7. Thành quả Đầu ra Mang lại Động lực Lớn nhất",
    "subtitle": "Bạn tự hào nhất khi nhìn thấy kết quả công việc của mình hiển thị dưới dạng nào?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "OUTPUT_TANGIBLE_TECH_SYSTEM",
        "title": "Sản phẩm Công nghệ, Máy móc & Công trình Vật lý",
        "description": "Một ứng dụng phần mềm chạy mượt, hệ thống robot, thiết bị điện tử hoặc tòa nhà hiện hữu ngoài đời thực."
      },
      {
        "option_key": "B",
        "trait_code": "OUTPUT_ECONOMIC_LEGAL_VALUE",
        "title": "Tăng trưởng Kinh tế, Hợp đồng & Quyết sách Quản trị",
        "description": "Doanh thu tăng trưởng, thương vụ thành công, vụ kiện thắng lợi hoặc chuỗi cung ứng vận hành trơn tru."
      },
      {
        "option_key": "C",
        "trait_code": "OUTPUT_HUMAN_WELLBEING",
        "title": "Sự Tiến bộ, Sức khỏe & Hạnh phúc của Con người",
        "description": "Học trò trưởng thành, bệnh nhân bình phục, cộng đồng an toàn và môi trường sống xanh sạch hơn."
      },
      {
        "option_key": "D",
        "trait_code": "OUTPUT_CREATIVE_SCIENTIFIC_WORK",
        "title": "Tác phẩm Nghệ thuật, Truyền thông & Công trình Khoa học",
        "description": "Bộ nhận diện thương hiệu, tác phẩm điện ảnh/âm nhạc, bài báo chất lượng hoặc phát minh khoa học mới."
      }
    ]
  },
  {
    "code": "COG_8",
    "dimension": "team_role",
    "dimension_badge": "Vai trò Tự nhiên trong Dự án Tập thể",
    "title": "8. Vai trò Tự nhiên trong Dự án Tập thể",
    "subtitle": "Khi làm dự án chung ở trường, bạn thường đảm nhận vị trí nào tốt nhất?",
    "options": [
      {
        "option_key": "A",
        "trait_code": "ROLE_TECHNICAL_SPECIALIST",
        "title": "Chuyên gia Nghiên cứu & Kỹ thuật Độc lập",
        "description": "Tập trung giải quyết các phần việc đòi hỏi chuyên môn sâu, tính toán hoặc kỹ thuật phức tạp nhất."
      },
      {
        "option_key": "B",
        "trait_code": "ROLE_STRATEGIC_LEADER",
        "title": "Người Dẫn dắt, Thuyết trình & Định hướng",
        "description": "Lập kế hoạch tổng thể, phân công nhiệm vụ, đại diện nhóm thuyết trình và đàm phán."
      },
      {
        "option_key": "C",
        "trait_code": "ROLE_CREATIVE_COMMUNICATOR",
        "title": "Người Sáng tạo Nội dung & Kết nối Thành viên",
        "description": "Đưa ra ý tưởng mới, thiết kế trình bày đẹp mắt, truyền cảm hứng và gắn kết mọi người."
      },
      {
        "option_key": "D",
        "trait_code": "ROLE_QUALITY_CONTROLLER",
        "title": "Người Kiểm soát Chất lượng, Quy trình & Hậu cần",
        "description": "Theo dõi tiến độ, quản lý ngân sách, chuẩn bị thiết bị và kiểm tra tỉ mỉ từng chi tiết trước khi nộp."
      }
    ]
  }
];
