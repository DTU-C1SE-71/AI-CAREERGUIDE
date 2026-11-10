export interface RoleplayScene {
  code: string;
  group: "R" | "I" | "A" | "S" | "E" | "C";
  stationTitle: string;
  sceneBadge: string;
  actionTitle: string;
  subHint: string;
  visualType:
    | "robotics"
    | "circuit"
    | "eco_lab"
    | "architecture"
    | "field_ops"
    | "ai_code"
    | "biotech"
    | "data_radar"
    | "quantum_math"
    | "strategy_lab"
    | "ui_studio"
    | "cinema_stage"
    | "sound_wave"
    | "creative_story"
    | "spatial_3d"
    | "mentor_hub"
    | "med_care"
    | "mind_listen"
    | "community_event"
    | "team_harmony"
    | "startup_pitch"
    | "negotiation"
    | "growth_chart"
    | "legal_debate"
    | "venture_launch"
    | "fintech_vault"
    | "data_grid"
    | "supply_chain"
    | "cyber_shield"
    | "audit_precision";
  isCore18: boolean;
}

export interface StationMeta {
  group: "R" | "I" | "A" | "S" | "E" | "C";
  codeLabel: string;
  name: string;
  shortName: string;
  zoneSubtitle: string;
}

export const STATIONS_META: StationMeta[] = [
  {
    group: "R",
    codeLabel: "CHẶNG 01 · R",
    name: "Xưởng Chế Tạo & Thực Địa",
    shortName: "Xưởng Kỹ Thuật",
    zoneSubtitle: "Cơ khí · Phần cứng · Kiến trúc · Vận hành",
  },
  {
    group: "I",
    codeLabel: "CHẶNG 02 · I",
    name: "Viện Giải Mã & AI Lab",
    shortName: "Viện AI & R&D",
    zoneSubtitle: "Thuật toán · Dữ liệu · Y sinh · Khoa học",
  },
  {
    group: "A",
    codeLabel: "CHẶNG 03 · A",
    name: "Studio Sáng Tạo Không Gian",
    shortName: "Studio Sáng Tạo",
    zoneSubtitle: "Thiết kế · Điện ảnh · Âm thanh · Nội dung",
  },
  {
    group: "S",
    codeLabel: "CHẶNG 04 · S",
    name: "Trạm Kết Nối & Y Sinh",
    shortName: "Trạm Cộng Đồng",
    zoneSubtitle: "Đào tạo · Chăm sóc · Tâm lý · Cộng đồng",
  },
  {
    group: "E",
    codeLabel: "CHẶNG 05 · E",
    name: "Đấu Trường Khởi Nghiệp",
    shortName: "Sàn Chiến Lược",
    zoneSubtitle: "Kinh doanh · Đàm phán · Luật · Lãnh đạo",
  },
  {
    group: "C",
    codeLabel: "CHẶNG 06 · C",
    name: "Trung Tâm Điều Hành Số",
    shortName: "Trung Tâm Số",
    zoneSubtitle: "FinTech · Kiểm toán · Logistics · Hệ thống",
  },
];

export const ROLEPLAY_SCENES: RoleplayScene[] = [
  // R1 - R5
  {
    code: "R1",
    group: "R",
    stationTitle: "Xưởng Chế Tạo & Thực Địa",
    sceneBadge: "Bàn Lắp Ráp Cơ Điện",
    actionTitle: "Tự tay tháo lắp, độ chế máy móc & thiết bị thông minh",
    subHint: "Biến linh kiện rời rạc thành cỗ máy vận hành mượt mà",
    visualType: "robotics",
    isCore18: true,
  },
  {
    code: "R2",
    group: "R",
    stationTitle: "Xưởng Chế Tạo & Thực Địa",
    sceneBadge: "Buồng Điều Khiển Vi Mạch",
    actionTitle: "Lập trình điều khiển Robot, Drone & mạng lưới cảm biến IoT",
    subHint: "Kết nối phần cứng vật lý với trí tuệ nhân tạo",
    visualType: "circuit",
    isCore18: true,
  },
  {
    code: "R3",
    group: "R",
    stationTitle: "Xưởng Chế Tạo & Thực Địa",
    sceneBadge: "Trạm Sinh Thái Tự Nhiên",
    actionTitle: "Khảo sát thực địa, bảo tồn sinh thái & nông nghiệp công nghệ cao",
    subHint: "Làm việc giữa thiên nhiên, rừng biển và sinh vật sống",
    visualType: "eco_lab",
    isCore18: false,
  },
  {
    code: "R4",
    group: "R",
    stationTitle: "Xưởng Chế Tạo & Thực Địa",
    sceneBadge: "Phòng Mô Hình Công Trình",
    actionTitle: "Dựng bản vẽ kỹ thuật, kết cấu cầu đường & kiến trúc đô thị",
    subHint: "Nhìn thấy công trình thực tế vươn lên từ bản thiết kế",
    visualType: "architecture",
    isCore18: true,
  },
  {
    code: "R5",
    group: "R",
    stationTitle: "Xưởng Chế Tạo & Thực Địa",
    sceneBadge: "Tổ Hợp Vận Hành Thực Chiến",
    actionTitle: "Trực tiếp điều khiển thiết bị tại công trường hoặc phòng máy",
    subHint: "Hành động thực tế thay vì ngồi bàn giấy cả ngày",
    visualType: "field_ops",
    isCore18: false,
  },

  // I1 - I5
  {
    code: "I1",
    group: "I",
    stationTitle: "Viện Giải Mã & AI Lab",
    sceneBadge: "Lõi Thuật Toán",
    actionTitle: "Giải mã thuật toán khó, tìm quy luật ẩn & viết code tối ưu",
    subHint: "Chinh phục những bài toán logic hóc búa nhất",
    visualType: "ai_code",
    isCore18: true,
  },
  {
    code: "I2",
    group: "I",
    stationTitle: "Viện Giải Mã & AI Lab",
    sceneBadge: "Phòng Lab Phân Tử",
    actionTitle: "Thí nghiệm công nghệ gen, dược phẩm & vật liệu thế hệ mới",
    subHint: "Khám phá cơ chế sự sống và phản ứng hóa sinh",
    visualType: "biotech",
    isCore18: true,
  },
  {
    code: "I3",
    group: "I",
    stationTitle: "Viện Giải Mã & AI Lab",
    sceneBadge: "Đài Quan Sát Dữ Liệu",
    actionTitle: "Khai phá dữ liệu lớn (Big Data) để dự báo xu hướng tương lai",
    subHint: "Tìm ra sự thật đằng sau hàng triệu điểm dữ liệu",
    visualType: "data_radar",
    isCore18: true,
  },
  {
    code: "I4",
    group: "I",
    stationTitle: "Viện Giải Mã & AI Lab",
    sceneBadge: "Thư Viện Nguyên Lý",
    actionTitle: "Đào sâu nguyên lý gốc rễ: vì sao một hệ thống hoạt động?",
    subHint: "Không chấp nhận học vẹt, luôn tìm bản chất khoa học",
    visualType: "quantum_math",
    isCore18: false,
  },
  {
    code: "I5",
    group: "I",
    stationTitle: "Viện Giải Mã & AI Lab",
    sceneBadge: " Trung Tâm R&D Chiến Lược",
    actionTitle: "Xây dựng mô hình mô phỏng kinh tế, tài chính & công nghệ",
    subHint: "Thử nghiệm các kịch bản tương lai bằng mô hình toán",
    visualType: "strategy_lab",
    isCore18: false,
  },

  // A1 - A5
  {
    code: "A1",
    group: "A",
    stationTitle: "Studio Sáng Tạo Không Gian",
    sceneBadge: "Bàn Thiết Kế Thị Giác",
    actionTitle: "Thiết kế giao diện UI/UX, đồ họa 3D & nhận diện thương hiệu",
    subHint: "Định hình thẩm mỹ số hiện đại và tinh tế",
    visualType: "ui_studio",
    isCore18: true,
  },
  {
    code: "A2",
    group: "A",
    stationTitle: "Studio Sáng Tạo Không Gian",
    sceneBadge: "Phim Trường Đa Phương Tiện",
    actionTitle: "Đạo diễn hình ảnh, dựng phim kỹ xảo & sản xuất truyền thông",
    subHint: "Kể chuyện bằng ngôn ngữ điện ảnh và chuyển động",
    visualType: "cinema_stage",
    isCore18: true,
  },
  {
    code: "A3",
    group: "A",
    stationTitle: "Studio Sáng Tạo Không Gian",
    sceneBadge: "Xưởng Nội Dung Sáng Tạo",
    actionTitle: "Sáng tác kịch bản, chiến dịch truyền thông & ngôn từ cuốn hút",
    subHint: "Chạm tới cảm xúc người đọc bằng ý tưởng độc bản",
    visualType: "creative_story",
    isCore18: true,
  },
  {
    code: "A4",
    group: "A",
    stationTitle: "Studio Sáng Tạo Không Gian",
    sceneBadge: "Không Gian Nghệ Thuật Mở",
    actionTitle: "Tự do phá cách, thử nghiệm ý tưởng mới không theo lối mòn",
    subHint: "Sáng tạo vượt khỏi những khuôn mẫu cứng nhắc",
    visualType: "spatial_3d",
    isCore18: false,
  },
  {
    code: "A5",
    group: "A",
    stationTitle: "Studio Sáng Tạo Không Gian",
    sceneBadge: "Gallery Kiến Trúc & Âm Thanh",
    actionTitle: "Phối hợp màu sắc, ánh sáng, âm nhạc & không gian nội thất",
    subHint: "Đánh thức mọi giác quan trong không gian nghệ thuật",
    visualType: "sound_wave",
    isCore18: false,
  },

  // S1 - S5
  {
    code: "S1",
    group: "S",
    stationTitle: "Trạm Kết Nối & Y Sinh",
    sceneBadge: "Học Viện Truyền Cảm Hứng",
    actionTitle: "Hướng dẫn, cố vấn & truyền đạt kiến thức dễ hiểu cho mọi người",
    subHint: "Giúp người khác tiến bộ và mở khóa tiềm năng",
    visualType: "mentor_hub",
    isCore18: true,
  },
  {
    code: "S2",
    group: "S",
    stationTitle: "Trạm Kết Nối & Y Sinh",
    sceneBadge: "Trung Tâm Y Khoa & Hồi Phục",
    actionTitle: "Chẩn đoán, điều trị & chăm sóc sức khỏe thể chất cho cộng đồng",
    subHint: "Bảo vệ sự sống và mang lại nụ cười bình phục",
    visualType: "med_care",
    isCore18: true,
  },
  {
    code: "S3",
    group: "S",
    stationTitle: "Trạm Kết Nối & Y Sinh",
    sceneBadge: "Không Gian Thấu Cảm",
    actionTitle: "Lắng nghe sâu, tham vấn tâm lý & tháo gỡ khủng hoảng tinh thần",
    subHint: "Điểm tựa tin cậy khi người khác cần sẻ chia",
    visualType: "mind_listen",
    isCore18: true,
  },
  {
    code: "S4",
    group: "S",
    stationTitle: "Trạm Kết Nối & Y Sinh",
    sceneBadge: "Quảng Trường Sự Kiện",
    actionTitle: "Tổ chức dự án xã hội, giao lưu quốc tế & dịch vụ hiếu khách",
    subHint: "Lan tỏa năng lượng tích cực tới hàng ngàn người",
    visualType: "community_event",
    isCore18: false,
  },
  {
    code: "S5",
    group: "S",
    stationTitle: "Trạm Kết Nối & Y Sinh",
    sceneBadge: "Vòng Tròn Đồng Đội",
    actionTitle: "Hòa giải bất đồng, gắn kết đội nhóm & phát triển con người",
    subHint: "Xây dựng tập thể đoàn kết và giàu văn hóa sẻ chia",
    visualType: "team_harmony",
    isCore18: false,
  },

  // E1 - E5
  {
    code: "E1",
    group: "E",
    stationTitle: "Đấu Trường Khởi Nghiệp",
    sceneBadge: "Bàn Chỉ Huy Chiến Dịch",
    actionTitle: "Dẫn dắt đội nhóm, phân công mục tiêu & điều phối dự án lớn",
    subHint: "Đứng mũi chịu sào đưa cả đội về đích đúng hạn",
    visualType: "startup_pitch",
    isCore18: true,
  },
  {
    code: "E2",
    group: "E",
    stationTitle: "Đấu Trường Khởi Nghiệp",
    sceneBadge: "Sàn Gọi Vốn & Thương Mại",
    actionTitle: "Khởi nghiệp kinh doanh, gọi vốn đầu tư & mở rộng thị trường",
    subHint: "Biến ý tưởng táo bạo thành doanh nghiệp tăng trưởng",
    visualType: "growth_chart",
    isCore18: true,
  },
  {
    code: "E3",
    group: "E",
    stationTitle: "Đấu Trường Khởi Nghiệp",
    sceneBadge: "Phòng Đàm Phán Cấp Cao",
    actionTitle: "Thuyết trình trước đám đông, đàm phán thương vụ & chốt hợp đồng",
    subHint: "Thuyết phục đối tác bằng lập luận sắc bén",
    visualType: "negotiation",
    isCore18: true,
  },
  {
    code: "E4",
    group: "E",
    stationTitle: "Đấu Trường Khởi Nghiệp",
    sceneBadge: "Hội Đồng Pháp Lý & Chính Sách",
    actionTitle: "Tranh biện pháp luật, bảo vệ quyền lợi & hoạch định chính sách",
    subHint: "Giữ vững cán cân công lý và khung pháp lý minh bạch",
    visualType: "legal_debate",
    isCore18: false,
  },
  {
    code: "E5",
    group: "E",
    stationTitle: "Đấu Trường Khởi Nghiệp",
    sceneBadge: "Đường Đua Mạo Hiểm",
    actionTitle: "Chấp nhận thử thách cạnh tranh cao để bứt phá dẫn đầu",
    subHint: "Bản lĩnh quyết đoán giữa môi trường biến động nhanh",
    visualType: "venture_launch",
    isCore18: false,
  },

  // C1 - C5
  {
    code: "C1",
    group: "C",
    stationTitle: "Trung Tâm Điều Hành Số",
    sceneBadge: "Lõi Tài Chính & Kiểm Toán",
    actionTitle: "Quản trị dòng tiền, ngân sách, thuế & báo cáo tài chính chuẩn xác",
    subHint: "Đảm bảo từng con số minh bạch, khớp 100%",
    visualType: "fintech_vault",
    isCore18: true,
  },
  {
    code: "C2",
    group: "C",
    stationTitle: "Trung Tâm Điều Hành Số",
    sceneBadge: "Kho Lưu Trữ Hệ Thống",
    actionTitle: "Cấu trúc hóa cơ sở dữ liệu, hồ sơ số & quy trình vận hành chuẩn",
    subHint: "Mọi thông tin đều ngăn nắp, truy xuất tức thì",
    visualType: "data_grid",
    isCore18: true,
  },
  {
    code: "C3",
    group: "C",
    stationTitle: "Trung Tâm Điều Hành Số",
    sceneBadge: "Trạm Kiểm Định Chất Lượng",
    actionTitle: "Rà soát chất lượng (QA/QC), phát hiện sai lệch & tuân thủ ISO",
    subHint: "Chốt chặn an toàn không để lọt bất kỳ lỗi nhỏ nào",
    visualType: "audit_precision",
    isCore18: true,
  },
  {
    code: "C4",
    group: "C",
    stationTitle: "Trung Tâm Điều Hành Số",
    sceneBadge: "Bản Đồ Logistics Toàn Cầu",
    actionTitle: "Điều phối chuỗi cung ứng, xuất nhập khẩu & kho vận thông minh",
    subHint: "Vận hành dòng chảy hàng hóa xuyên biên giới đúng giờ",
    visualType: "supply_chain",
    isCore18: false,
  },
  {
    code: "C5",
    group: "C",
    stationTitle: "Trung Tâm Điều Hành Số",
    sceneBadge: "Lá Chắn An Ninh Mạng",
    actionTitle: "Thiết lập quy tắc bảo mật, quản trị rủi ro & vận hành ổn định",
    subHint: "Giữ cho hệ thống doanh nghiệp vận hành an toàn 24/7",
    visualType: "cyber_shield",
    isCore18: false,
  },
];

export const REACTION_CARDS = [
  {
    value: 1,
    keyHint: "1",
    shortLabel: "Bỏ qua",
    xp: "+10 XP",
    emoji: "💤",
  },
  {
    value: 2,
    keyHint: "2",
    shortLabel: "Ít hứng thú",
    xp: "+15 XP",
    emoji: "🫧",
  },
  {
    value: 3,
    keyHint: "3",
    shortLabel: "Thử xem sao",
    xp: "+20 XP",
    emoji: "✨",
  },
  {
    value: 4,
    keyHint: "4",
    shortLabel: "Rất cuốn",
    xp: "+25 XP",
    emoji: "🚀",
  },
  {
    value: 5,
    keyHint: "5",
    shortLabel: "Đúng chất tôi",
    xp: "+30 XP",
    emoji: "⚡",
  },
];
