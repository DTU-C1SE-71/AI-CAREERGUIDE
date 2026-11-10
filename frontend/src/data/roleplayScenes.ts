export type RiasecGroup = "R" | "I" | "A" | "S" | "E" | "C";

export interface LootItemCard {
  id: string;
  questionCode: string; // Maps to R1..R5, I1..I5, A1..A5, S1..S5, E1..E5, C1..C5
  group: RiasecGroup;
  itemName: string;
  actionDesc: string;
  iconKey:
    | "wrench"
    | "cpu"
    | "palette"
    | "heart"
    | "rocket"
    | "shield"
    | "drone"
    | "dna"
    | "film"
    | "users"
    | "briefcase"
    | "database"
    | "compass"
    | "radar"
    | "pen"
    | "sparkles"
    | "scale"
    | "check"
    | "building"
    | "atom"
    | "music"
    | "globe"
    | "megaphone"
    | "truck";
}

export interface LootSituation {
  situationIndex: number; // 1..10
  title: string;
  contextPrompt: string;
  badge: string;
  items: LootItemCard[];
}

export const RIASEC_GROUP_LABELS: Record<
  RiasecGroup,
  { short: string; role: string }
> = {
  R: { short: "Kỹ thuật · R", role: "Chế tạo & Thực địa" },
  I: { short: "Nghiên cứu · I", role: "Giải mã & AI Lab" },
  A: { short: "Sáng tạo · A", role: "Thiết kế & Nghệ thuật" },
  S: { short: "Cộng đồng · S", role: "Y sinh & Đào tạo" },
  E: { short: "Chiến lược · E", role: "Kinh doanh & Lãnh đạo" },
  C: { short: "Hệ thống · C", role: "Tài chính & Vận hành" },
};

export const LOOT_SITUATIONS: LootSituation[] = [
  {
    situationIndex: 1,
    badge: "CHẶNG 01 / 10 · KHỞI ĐỘNG DỰ ÁN",
    title: "Trang bị bộ công cụ đầu tiên của bạn",
    contextPrompt: "Chọn tối đa 3 vật phẩm bạn muốn mang theo nhất (Click chọn = 4–5đ · Đúp chuột = ⭐ 5đ)",
    items: [
      {
        id: "S1_R1",
        questionCode: "R1",
        group: "R",
        itemName: "Bộ Đồ Nghề Cơ Điện Tử",
        actionDesc: "Tự tay tháo lắp, độ chế máy móc & mạch phần cứng",
        iconKey: "wrench",
      },
      {
        id: "S1_I1",
        questionCode: "I1",
        group: "I",
        itemName: "Siêu Máy Tính Giải Thuật",
        actionDesc: "Giải bài toán logic khó & viết thuật toán tối ưu",
        iconKey: "cpu",
      },
      {
        id: "S1_A1",
        questionCode: "A1",
        group: "A",
        itemName: "Bảng Vẽ Đồ Họa 3D & UI",
        actionDesc: "Thiết kế giao diện số, poster & nhận diện thương hiệu",
        iconKey: "palette",
      },
      {
        id: "S1_S1",
        questionCode: "S1",
        group: "S",
        itemName: "Cẩm Nang Cố Vấn Đào Tạo",
        actionDesc: "Truyền đạt kiến thức dễ hiểu & hướng dẫn mọi người",
        iconKey: "users",
      },
      {
        id: "S1_E1",
        questionCode: "E1",
        group: "E",
        itemName: "Huy Hiệu Chỉ Huy Chiến Dịch",
        actionDesc: "Dẫn dắt đội nhóm, phân công mục tiêu & điều phối dự án",
        iconKey: "rocket",
      },
      {
        id: "S1_C1",
        questionCode: "C1",
        group: "C",
        itemName: "Sổ Cái Tài Chính Chuẩn Xác",
        actionDesc: "Quản trị dòng tiền, ngân sách & kiểm toán minh bạch",
        iconKey: "database",
      },
    ],
  },
  {
    situationIndex: 2,
    badge: "CHẶNG 02 / 10 · KHÔNG GIAN TÁC NGHIỆP",
    title: "Trạm làm việc lý tưởng bạn muốn bước vào",
    contextPrompt: "Chọn 2–3 không gian khiến bạn hào hứng bắt tay làm việc ngay",
    items: [
      {
        id: "S2_R2",
        questionCode: "R2",
        group: "R",
        itemName: "Buồng Điều Khiển Drone & Robot",
        actionDesc: "Lập trình vi mạch, cảm biến IoT & thiết bị tự hành",
        iconKey: "drone",
      },
      {
        id: "S2_I2",
        questionCode: "I2",
        group: "I",
        itemName: "Phòng Lab Sinh Y & Công Nghệ Gen",
        actionDesc: "Thí nghiệm dược chất, di truyền & vật liệu thế hệ mới",
        iconKey: "dna",
      },
      {
        id: "S2_A2",
        questionCode: "A2",
        group: "A",
        itemName: "Phim Trường Kỹ Xảo & Điện Ảnh",
        actionDesc: "Đạo diễn hình ảnh, dựng phim & sản xuất truyền thông",
        iconKey: "film",
      },
      {
        id: "S2_S2",
        questionCode: "S2",
        group: "S",
        itemName: "Trung Tâm Y Khoa & Hồi Phục",
        actionDesc: "Chẩn đoán, chăm sóc sức khỏe & bảo vệ bệnh nhân",
        iconKey: "heart",
      },
      {
        id: "S2_E2",
        questionCode: "E2",
        group: "E",
        itemName: "Sàn Gọi Vốn Khởi Nghiệp",
        actionDesc: "Phát triển sản phẩm thương mại & mở rộng thị trường",
        iconKey: "briefcase",
      },
      {
        id: "S2_C2",
        questionCode: "C2",
        group: "C",
        itemName: "Kho Dữ Liệu Số Hóa Chuẩn Mực",
        actionDesc: "Cấu trúc hóa cơ sở dữ liệu & hồ sơ truy xuất tức thì",
        iconKey: "database",
      },
    ],
  },
  {
    situationIndex: 3,
    badge: "CHẶNG 03 / 10 · NHIỆM VỤ ĐỘT PHÁ",
    title: "Nhiệm vụ đặc biệt bạn muốn nhận lấy",
    contextPrompt: "Chọn tối đa 3 nhiệm vụ bạn tự tin giải quyết tốt nhất",
    items: [
      {
        id: "S3_R3",
        questionCode: "R3",
        group: "R",
        itemName: "Trạm Khảo Sát Sinh Thái Thực Địa",
        actionDesc: "Ươm tạo nông nghiệp công nghệ cao & bảo tồn thiên nhiên",
        iconKey: "compass",
      },
      {
        id: "S3_I3",
        questionCode: "I3",
        group: "I",
        itemName: "Radar Khai Phá Dữ Liệu Lớn",
        actionDesc: "Phân tích hàng triệu dữ liệu để dự báo xu hướng tương lai",
        iconKey: "radar",
      },
      {
        id: "S3_A3",
        questionCode: "A3",
        group: "A",
        itemName: "Bút Kịch Bản & Chiến Dịch Viral",
        actionDesc: "Sáng tác câu chuyện, nội dung truyền thông chạm cảm xúc",
        iconKey: "pen",
      },
      {
        id: "S3_S3",
        questionCode: "S3",
        group: "S",
        itemName: "Không Gian Thấu Cảm Tâm Lý",
        actionDesc: "Lắng nghe sâu, tham vấn tâm lý & tháo gỡ khủng hoảng",
        iconKey: "sparkles",
      },
      {
        id: "S3_E3",
        questionCode: "E3",
        group: "E",
        itemName: "Bàn Đàm Phán Thương Vụ Lớn",
        actionDesc: "Thuyết trình thuyết phục đối tác & chốt hợp đồng chiến lược",
        iconKey: "megaphone",
      },
      {
        id: "S3_C3",
        questionCode: "C3",
        group: "C",
        itemName: "Kính Lúp Kiểm Định Chất Lượng",
        actionDesc: "Rà soát QA/QC tỉ mỉ, phát hiện lỗi sai & tuân thủ ISO",
        iconKey: "check",
      },
    ],
  },
  {
    situationIndex: 4,
    badge: "CHẶNG 04 / 10 · SIÊU NĂNG LỰC CHUYÊN MÔN",
    title: "Kỹ năng chủ lực bạn muốn nâng cấp",
    contextPrompt: "Chọn 2–3 thẻ kỹ năng phản ánh đúng con người bạn",
    items: [
      {
        id: "S4_R4",
        questionCode: "R4",
        group: "R",
        itemName: "Mô Hình Kết Cấu & Kiến Trúc Đô Thị",
        actionDesc: "Dựng bản vẽ kỹ thuật, cầu đường & công trình thực tế",
        iconKey: "building",
      },
      {
        id: "S4_I4",
        questionCode: "I4",
        group: "I",
        itemName: "Lõi Nguyên Lý Vật Lý & Bán Dẫn",
        actionDesc: "Đào sâu bản chất khoa học, chip bán dẫn & năng lượng mới",
        iconKey: "atom",
      },
      {
        id: "S4_A4",
        questionCode: "A4",
        group: "A",
        itemName: "Phòng Thu Âm Thanh & Trình Diễn",
        actionDesc: "Phối khí âm nhạc, ánh sáng sân khấu & nghệ thuật thị giác",
        iconKey: "music",
      },
      {
        id: "S4_S4",
        questionCode: "S4",
        group: "S",
        itemName: "Cầu Nối Sự Kiện & Cộng Đồng",
        actionDesc: "Tổ chức dự án xã hội, du lịch & trải nghiệm hiếu khách",
        iconKey: "globe",
      },
      {
        id: "S4_E4",
        questionCode: "E4",
        group: "E",
        itemName: "Cán Cân Pháp Lý & Chính Sách",
        actionDesc: "Tranh biện sắc bén, bảo vệ quyền lợi & luật kinh tế",
        iconKey: "scale",
      },
      {
        id: "S4_C4",
        questionCode: "C4",
        group: "C",
        itemName: "Bản Đồ Điều Phối Logistics Toàn Cầu",
        actionDesc: "Tối ưu chuỗi cung ứng, xuất nhập khẩu & vận tải thông minh",
        iconKey: "truck",
      },
    ],
  },
  {
    situationIndex: 5,
    badge: "CHẶNG 05 / 10 · PHONG CÁCH HÀNH ĐỘNG",
    title: "Cách bạn tạo ra dấu ấn trong đội ngũ",
    contextPrompt: "Chọn 2–3 thẻ hành động bạn yêu thích nhất",
    items: [
      {
        id: "S5_R5",
        questionCode: "R5",
        group: "R",
        itemName: "Bộ Giáp Vận Hành Hiện Trường",
        actionDesc: "Trực tiếp điều khiển thiết bị tại công trường & phòng máy",
        iconKey: "wrench",
      },
      {
        id: "S5_I5",
        questionCode: "I5",
        group: "I",
        itemName: "Mô Hình Mô Phỏng Chiến Lược",
        actionDesc: "Nghiên cứu học thuật, phân tích kinh tế & hành vi xã hội",
        iconKey: "radar",
      },
      {
        id: "S5_A5",
        questionCode: "A5",
        group: "A",
        itemName: "Ấn Phẩm Sáng Tạo Độc Bản",
        actionDesc: "Tự do phá cách, thử nghiệm ý tưởng mới không theo lối mòn",
        iconKey: "sparkles",
      },
      {
        id: "S5_S5",
        questionCode: "S5",
        group: "S",
        itemName: "Hộ Chiếu Giao Lưu Đa Văn Hóa",
        actionDesc: "Kết nối quốc tế bằng ngoại ngữ & gắn kết tinh thần đồng đội",
        iconKey: "globe",
      },
      {
        id: "S5_E5",
        questionCode: "E5",
        group: "E",
        itemName: "Ngọn Cờ Tiên Phong Đột Phá",
        actionDesc: "Chấp nhận thử thách cạnh tranh cao để bứt phá dẫn đầu",
        iconKey: "rocket",
      },
      {
        id: "S5_C5",
        questionCode: "C5",
        group: "C",
        itemName: "Lá Chắn Bảo Mật & Quy Chuẩn",
        actionDesc: "Thiết lập quy tắc an toàn, quản trị rủi ro & vận hành 24/7",
        iconKey: "shield",
      },
    ],
  },
  {
    situationIndex: 6,
    badge: "CHẶNG 06 / 10 · THỬ THÁCH NÂNG CAO",
    title: "Dự án thực chiến bạn muốn đầu quân",
    contextPrompt: "Chọn tối đa 3 dự án cuốn hút bạn nhất",
    items: [
      {
        id: "S6_R1",
        questionCode: "R1",
        group: "R",
        itemName: "Dây Chuyền Tự Động Hóa Thông Minh",
        actionDesc: "Chế tạo cánh tay robot & hệ thống cơ khí chính xác",
        iconKey: "cpu",
      },
      {
        id: "S6_I1",
        questionCode: "I1",
        group: "I",
        itemName: "Trung Tâm Giải Mã Trí Tuệ Nhân Tạo",
        actionDesc: "Huấn luyện mô hình Deep Learning & giải toán tính toán",
        iconKey: "atom",
      },
      {
        id: "S6_A1",
        questionCode: "A1",
        group: "A",
        itemName: "Studio Thiết Kế Không Gian & Nội Thất",
        actionDesc: "Kiến tạo không gian sống thẩm mỹ, ánh sáng & vật liệu",
        iconKey: "palette",
      },
      {
        id: "S6_S1",
        questionCode: "S1",
        group: "S",
        itemName: "Học Viện Khai Phóng Tiềm Năng Trẻ",
        actionDesc: "Thiết kế bài giảng tương tác & đồng hành cùng học viên",
        iconKey: "users",
      },
      {
        id: "S6_E1",
        questionCode: "E1",
        group: "E",
        itemName: "Tập Đoàn Quản Trị & Đầu Tư",
        actionDesc: "Hoạch định chiến lược tăng trưởng & điều hành nhân sự",
        iconKey: "briefcase",
      },
      {
        id: "S6_C1",
        questionCode: "C1",
        group: "C",
        itemName: "Trung Tâm Phân Tích FinTech & Ngân Hàng",
        actionDesc: "Định giá tài sản, cân đối dòng vốn & kiểm soát rủi ro số",
        iconKey: "database",
      },
    ],
  },
  {
    situationIndex: 7,
    badge: "CHẶNG 07 / 10 · CÔNG NGHỆ TƯƠNG LAI",
    title: "Lĩnh vực công nghệ - xã hội bạn muốn làm chủ",
    contextPrompt: "Chọn 2–3 vật phẩm đại diện cho đam mê của bạn",
    items: [
      {
        id: "S7_R2",
        questionCode: "R2",
        group: "R",
        itemName: "Trạm Viễn Thám & Thiết Bị Bay",
        actionDesc: "Vận hành hệ thống điều khiển bay & mạng lưới cảm biến",
        iconKey: "drone",
      },
      {
        id: "S7_I2",
        questionCode: "I2",
        group: "I",
        itemName: "Viện Công Nghệ Sinh Học & Dược Lý",
        actionDesc: "Nghiên cứu vắc-xin, tế bào gốc & xét nghiệm y sinh",
        iconKey: "dna",
      },
      {
        id: "S7_A2",
        questionCode: "A2",
        group: "A",
        itemName: "Xưởng Game Art & Hoạt Hình 3D",
        actionDesc: "Xây dựng nhân vật, thế giới ảo & kỹ xảo chuyển động",
        iconKey: "film",
      },
      {
        id: "S7_S2",
        questionCode: "S2",
        group: "S",
        itemName: "Hệ Sinh Thái Chăm Sóc Sức Khỏe Cộng Đồng",
        actionDesc: "Điều dưỡng, phục hồi chức năng & dinh dưỡng lâm sàng",
        iconKey: "heart",
      },
      {
        id: "S7_E2",
        questionCode: "E2",
        group: "E",
        itemName: "Sàn Thương Mại Điện Tử Xuyên Biên Giới",
        actionDesc: "Kinh doanh số, phát triển thương hiệu & tăng trưởng doanh thu",
        iconKey: "rocket",
      },
      {
        id: "S7_C2",
        questionCode: "C2",
        group: "C",
        itemName: "Hệ Thống Thông Tin Quản Lý (MIS/ERP)",
        actionDesc: "Vận hành quy trình dữ liệu doanh nghiệp đồng bộ, chính xác",
        iconKey: "check",
      },
    ],
  },
  {
    situationIndex: 8,
    badge: "CHẶNG 08 / 10 · GIẢI QUYẾT THÁCH THỨC",
    title: "Khi thành phố tương lai cần bạn hỗ trợ",
    contextPrompt: "Bạn sẽ chọn 2–3 nhiệm vụ nào để đóng góp?",
    items: [
      {
        id: "S8_R3",
        questionCode: "R3",
        group: "R",
        itemName: "Khu Bảo Tồn & Nông Trại Xanh Thông Minh",
        actionDesc: "Ứng dụng cơ giới hóa bảo vệ rừng, biển & nguồn thực phẩm",
        iconKey: "compass",
      },
      {
        id: "S8_I3",
        questionCode: "I3",
        group: "I",
        itemName: "Trung Tâm Dự Báo Khí Hậu & Dữ Liệu Số",
        actionDesc: "Xây dựng mô hình toán học phân tích biến động toàn cầu",
        iconKey: "radar",
      },
      {
        id: "S8_A3",
        questionCode: "A3",
        group: "A",
        itemName: "Tạp Chí Nghệ Thuật & Truyền Thông Số",
        actionDesc: "Biên tập nội dung sáng tạo, nhiếp ảnh & báo chí hiện đại",
        iconKey: "pen",
      },
      {
        id: "S8_S3",
        questionCode: "S3",
        group: "S",
        itemName: "Đường Dây Nóng Tham Vấn & Trợ Giúp Xã Hội",
        actionDesc: "Bảo vệ trẻ em, hỗ trợ tâm lý học đường & cộng đồng yếu thế",
        iconKey: "sparkles",
      },
      {
        id: "S8_E3",
        questionCode: "E3",
        group: "E",
        itemName: "Chiến Dịch PR & Định Vị Thương Hiệu Quốc Gia",
        actionDesc: "Truyền cảm hứng trước công chúng & dẫn dắt truyền thông",
        iconKey: "megaphone",
      },
      {
        id: "S8_C3",
        questionCode: "C3",
        group: "C",
        itemName: "Trung Tâm Giám Sát An Toàn Thông Tin (SOC)",
        actionDesc: "Kiểm thử phần mềm, rà soát lỗ hổng & bảo vệ dữ liệu",
        iconKey: "shield",
      },
    ],
  },
  {
    situationIndex: 9,
    badge: "CHẶNG 09 / 10 · DẤU ẤN SỰ NGHIỆP",
    title: "Thành tựu khiến bạn tự hào nhất sau 5 năm",
    contextPrompt: "Chọn tối đa 3 thành tựu bạn khao khát chinh phục",
    items: [
      {
        id: "S9_R4",
        questionCode: "R4",
        group: "R",
        itemName: "Kỹ Sư Trưởng Công Trình Trọng Điểm",
        actionDesc: "Kiến tạo những tòa nhà, cầu cảng & hạ tầng bền vững",
        iconKey: "building",
      },
      {
        id: "S9_I4",
        questionCode: "I4",
        group: "I",
        itemName: "Nhà Khoa Học Phát Minh Công Nghệ Lõi",
        actionDesc: "Công bố nghiên cứu đột phá về chip, vật liệu & AI",
        iconKey: "atom",
      },
      {
        id: "S9_A4",
        questionCode: "A4",
        group: "A",
        itemName: "Giám Đốc Sáng Tạo (Creative Director)",
        actionDesc: "Định hình xu hướng thẩm mỹ, âm nhạc & điện ảnh",
        iconKey: "music",
      },
      {
        id: "S9_S4",
        questionCode: "S4",
        group: "S",
        itemName: "Chuyên Gia Quản Trị Dịch Vụ & Sự Kiện Quốc Tế",
        actionDesc: "Kiến tạo trải nghiệm du lịch, khách sạn & văn hóa đẳng cấp",
        iconKey: "globe",
      },
      {
        id: "S9_E4",
        questionCode: "E4",
        group: "E",
        itemName: "Luật Sư / Chuyên Gia Đàm Phán Cấp Cao",
        actionDesc: "Bảo vệ công lý, tư vấn pháp chế & thương thảo quốc tế",
        iconKey: "scale",
      },
      {
        id: "S9_C4",
        questionCode: "C4",
        group: "C",
        itemName: "Giám Đốc Vận Hành Chuỗi Cung Ứng (COO)",
        actionDesc: "Điều phối mạng lưới kho vận, cảng biển & xuất nhập khẩu",
        iconKey: "truck",
      },
    ],
  },
  {
    situationIndex: 10,
    badge: "CHẶNG 10 / 10 · MẢNH GHÉP HOÀN TẤT",
    title: "Chọn bộ vật phẩm tổng kết bản sắc của bạn",
    contextPrompt: "Lựa chọn cuối cùng để mở khóa Phễu Khuyến Nghị 435 Ngành",
    items: [
      {
        id: "S10_R5",
        questionCode: "R5",
        group: "R",
        itemName: "Huy Hiệu Thực Chiến Kỹ Thuật",
        actionDesc: "Luôn ưu tiên bắt tay làm thật, tạo sản phẩm hữu hình",
        iconKey: "wrench",
      },
      {
        id: "S10_I5",
        questionCode: "I5",
        group: "I",
        itemName: "La Bàn Tư Duy Học Thuật Sâu",
        actionDesc: "Luôn đặt câu hỏi “Vì sao?” và tìm quy luật bằng dữ liệu",
        iconKey: "cpu",
      },
      {
        id: "S10_A5",
        questionCode: "A5",
        group: "A",
        itemName: "Lăng Kính Sáng Tạo Tự Do",
        actionDesc: "Luôn tìm góc nhìn thẩm mỹ mới lạ, khác biệt đám đông",
        iconKey: "palette",
      },
      {
        id: "S10_S5",
        questionCode: "S5",
        group: "S",
        itemName: "Ngọn Đuốc Kết Nối Con Người",
        actionDesc: "Luôn lấy sự tiến bộ, sức khỏe & hạnh phúc cộng đồng làm gốc",
        iconKey: "heart",
      },
      {
        id: "S10_E5",
        questionCode: "E5",
        group: "E",
        itemName: "Vương Miện Bản Lĩnh Dẫn Đầu",
        actionDesc: "Luôn sẵn sàng đứng mũi chịu sào, thuyết phục & tạo giá trị",
        iconKey: "rocket",
      },
      {
        id: "S10_C5",
        questionCode: "C5",
        group: "C",
        itemName: "Đồng Hồ Chuẩn Mực & Kỷ Luật",
        actionDesc: "Luôn đảm bảo mọi kế hoạch, con số & quy trình chính xác 100%",
        iconKey: "shield",
      },
    ],
  },
];
