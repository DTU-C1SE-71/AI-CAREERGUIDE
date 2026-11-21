export type RiasecDimension = "R" | "I" | "A" | "S" | "E" | "C";

export interface Question {
  code: string; // R1..R5, I1..I5, A1..A5, S1..S5, E1..E5, C1..C5
  dimension: RiasecDimension;
  round: 1 | 2 | 3 | 4 | 5;
  titleVi: string;
  titleEn: string;
  imageUrl: string;
  iconKey:
    | "hammer"
    | "wrench"
    | "sprout"
    | "dumbbell"
    | "fish"
    | "truck"
    | "check"
    | "pill"
    | "droplets"
    | "flask"
    | "microscope"
    | "cloud"
    | "book"
    | "music"
    | "film"
    | "palette"
    | "home"
    | "sparkles"
    | "clapperboard"
    | "heart"
    | "compass"
    | "globe"
    | "activity"
    | "handheart"
    | "graduation"
    | "building"
    | "rocket"
    | "handshake"
    | "megaphone"
    | "calendar"
    | "shopping"
    | "network"
    | "calculator"
    | "clipboard"
    | "scan"
    | "mail";
}

export type OnetMiniIpItem = Question;

export const RIASEC_META: Record<
  RiasecDimension,
  { label: string; tag: string; sampleHint: string }
> = {
  R: {
    label: "Thực tế · R",
    tag: "Realistic",
    sampleHint: "Tháo lắp, dựng mô hình, chăm cây, thực hành",
  },
  I: {
    label: "Nghiên cứu · I",
    tag: "Investigative",
    sampleHint: "Toán logic, công nghệ, sinh học, khám phá nguyên lý",
  },
  A: {
    label: "Nghệ thuật · A",
    tag: "Artistic",
    sampleHint: "Vẽ thiết kế, trang trí, viết lách, âm nhạc",
  },
  S: {
    label: "Xã hội · S",
    tag: "Social",
    sampleHint: "Giảng bài, chăm sóc sức khỏe, lắng nghe, tình nguyện",
  },
  E: {
    label: "Quản lý · E",
    tag: "Enterprising",
    sampleHint: "Nhóm trưởng, hội chợ, tranh biện, thuyết trình",
  },
  C: {
    label: "Hệ thống · C",
    tag: "Conventional",
    sampleHint: "Giữ quỹ lớp, ngăn nắp, soát lỗi, lên lịch trình",
  },
};

export const ONET_REACTION_SCALE = [
  { value: 1, emoji: "😣", label: "Rất ghét", key: "1" },
  { value: 2, emoji: "🙁", label: "Không thích", key: "2" },
  { value: 3, emoji: "😐", label: "Phân vân", key: "3" },
  { value: 4, emoji: "🙂", label: "Thích", key: "4" },
  { value: 5, emoji: "🤩", label: "Rất thích", key: "5" },
] as const;

/**
 * Adolescent-adapted 30-item RIASEC Interest Profiler (High School Context, Circular 74/2026/TT-BGDĐT)
 * 100% anchored in everyday high school, home, and club experiences.
 * Complete with curated contextual visual illustrations (`imageUrl`).
 */
export const ONET_MINI_IP_ITEMS: Question[] = [
  // Round 1
  {
    code: "R1",
    dimension: "R",
    round: 1,
    titleVi:
      "Tự tay tháo lắp, sửa đồ đạc hỏng trong nhà hoặc mày mò lắp mạch điện, mô hình máy móc",
    titleEn: "Repair household items or assemble electronic circuits and mechanical models",
    imageUrl: "/images/assessment/R1.jpg",
    iconKey: "wrench",
  },
  {
    code: "I1",
    dimension: "I",
    round: 1,
    titleVi:
      "Giải các bài toán khó, câu đố suy luận logic hoặc tự mày mò hiểu vì sao một công thức lại đúng",
    titleEn: "Solve hard math problems, logic puzzles, or understand why a formula works",
    imageUrl: "/images/assessment/I1.jpg",
    iconKey: "calculator",
  },
  {
    code: "A1",
    dimension: "A",
    round: 1,
    titleVi:
      "Vẽ minh họa, phối màu trang trí poster, bài thuyết trình đẹp mắt hoặc tự phác thảo kiểu trang phục, đồ trang trí riêng",
    titleEn: "Draw illustrations, design posters and slides, or sketch outfits and decor",
    imageUrl: "/images/assessment/A1.jpg",
    iconKey: "palette",
  },
  {
    code: "S1",
    dimension: "S",
    round: 1,
    titleVi:
      "Kiên nhẫn giảng lại bài khó cho bạn bè hoặc em nhỏ bằng cách giải thích thật dễ hiểu",
    titleEn: "Patiently explain difficult lessons to classmates or younger students",
    imageUrl: "/images/assessment/S1.jpg",
    iconKey: "graduation",
  },
  {
    code: "E1",
    dimension: "E",
    round: 1,
    titleVi:
      "Đứng ra làm nhóm trưởng, phân chia công việc và thúc đẩy cả nhóm hoàn thành mục tiêu đúng hạn",
    titleEn: "Act as team leader, delegate tasks, and keep the group on schedule",
    imageUrl: "/images/assessment/E1.jpg",
    iconKey: "building",
  },
  {
    code: "C1",
    dimension: "C",
    round: 1,
    titleVi:
      "Ghi chép cẩn thận tiền tiêu vặt, giữ quỹ lớp hoặc tính toán các khoản thu chi của nhóm chính xác từng con số",
    titleEn: "Track pocket money, manage the class fund, or calculate group budgets accurately",
    imageUrl: "/images/assessment/C1.jpg",
    iconKey: "calculator",
  },

  // Round 2
  {
    code: "R2",
    dimension: "R",
    round: 2,
    titleVi:
      "Đo đạc kích thước, kẻ vẽ sơ đồ mặt bằng hoặc tự tay dựng mô hình nhà cửa, kết cấu vững chắc",
    titleEn: "Measure dimensions, draw floor plans, or build sturdy architectural models",
    imageUrl: "/images/assessment/R2.jpg",
    iconKey: "hammer",
  },
  {
    code: "I2",
    dimension: "I",
    round: 2,
    titleVi:
      "Tò mò cách một ứng dụng, trò chơi hay AI được lập trình bên trong hoặc thích tìm quy luật từ bảng số liệu, biểu đồ",
    titleEn: "Explore how apps, games, or AI are coded, or find patterns in charts and data",
    imageUrl: "/images/assessment/I2.jpg",
    iconKey: "network",
  },
  {
    code: "A2",
    dimension: "A",
    round: 2,
    titleVi:
      "Phối màu, bài trí lại góc học tập, phòng ở cho có gu hoặc thích phác họa không gian nhà cửa, quán xá đẹp mắt",
    titleEn: "Style and arrange your study corner or room, or sketch appealing spaces",
    imageUrl: "/images/assessment/A2.jpg",
    iconKey: "home",
  },
  {
    code: "S2",
    dimension: "S",
    round: 2,
    titleVi:
      "Tìm hiểu cách sơ cứu vết thương, chăm sóc sức khỏe cho mọi người hoặc xây dựng chế độ dinh dưỡng, ăn uống khoa học",
    titleEn: "Learn first aid, healthcare basics, or how to build a scientific nutrition plan",
    imageUrl: "/images/assessment/S2.jpg",
    iconKey: "activity",
  },
  {
    code: "E2",
    dimension: "E",
    round: 2,
    titleVi:
      "Làm gian hàng hội chợ ở trường, tập mua bán nhỏ online hoặc nghĩ ý tưởng kinh doanh để tạo ra tiền lãi",
    titleEn: "Run a school fair booth, try small online selling, or brainstorm profitable ideas",
    imageUrl: "/images/assessment/E2.jpg",
    iconKey: "rocket",
  },
  {
    code: "C2",
    dimension: "C",
    round: 2,
    titleVi:
      "Sắp xếp thư mục máy tính, vở ghi và tài liệu học tập ngăn nắp theo từng mục để cần là tìm thấy ngay",
    titleEn: "Organize computer folders, notebooks, and study materials neatly by category",
    imageUrl: "/images/assessment/C2.jpg",
    iconKey: "clipboard",
  },

  // Round 3
  {
    code: "R3",
    dimension: "R",
    round: 3,
    titleVi:
      "Tự tay trồng trọt, chăm bẵm cây cối, vật nuôi hoặc tham gia cải tạo vườn tược, không gian xanh ngoài trời",
    titleEn: "Grow plants, care for animals, or help improve outdoor gardens and green spaces",
    imageUrl: "/images/assessment/R3.jpg",
    iconKey: "sprout",
  },
  {
    code: "I3",
    dimension: "I",
    round: 3,
    titleVi:
      "Tìm hiểu cơ thể sống và di truyền hoạt động thế nào, vì sao ta bị ốm và cách thuốc giúp cơ thể khỏe lại",
    titleEn: "Explore how living bodies and genetics work, why illness happens, and how medicine heals",
    imageUrl: "/images/assessment/I3.jpg",
    iconKey: "pill",
  },
  {
    code: "A3",
    dimension: "A",
    round: 3,
    titleVi:
      "Viết truyện, viết bài chia sẻ cảm nhận hoặc chụp ảnh, quay dựng video kể lại một câu chuyện theo ý mình",
    titleEn: "Write stories or reflections, or shoot and edit photos and videos to tell a story",
    imageUrl: "/images/assessment/A3.jpg",
    iconKey: "film",
  },
  {
    code: "S3",
    dimension: "S",
    round: 3,
    titleVi:
      "Kiên nhẫn ngồi lắng nghe người khác tâm sự chuyện buồn, thấu cảm và giúp họ tháo gỡ khúc mắc trong lòng",
    titleEn: "Listen patiently when others confide in you, empathize, and help ease their worries",
    imageUrl: "/images/assessment/S3.jpg",
    iconKey: "heart",
  },
  {
    code: "E3",
    dimension: "E",
    round: 3,
    titleVi:
      "Tham gia tranh biện, đưa ra dẫn chứng và lý lẽ chặt chẽ để thuyết phục người khác hoặc phân xử khi nhóm có bất đồng",
    titleEn: "Debate with clear evidence and reasoning to persuade others or resolve group disagreements",
    imageUrl: "/images/assessment/E3.jpg",
    iconKey: "handshake",
  },
  {
    code: "C3",
    dimension: "C",
    round: 3,
    titleVi:
      "Rà soát tỉ mỉ từng dòng bài làm, con số hay lỗi chính tả nhỏ để chắc chắn không sót lỗi trước khi nộp",
    titleEn: "Carefully proofread every line, number, and spelling detail before submitting work",
    imageUrl: "/images/assessment/C3.jpg",
    iconKey: "scan",
  },

  // Round 4
  {
    code: "R4",
    dimension: "R",
    round: 4,
    titleVi:
      "Tự tay sử dụng ống nghiệm, kính hiển vi trong giờ thực hành hoặc tỉ mỉ cân đo, pha chế mẫu thử đúng chuẩn",
    titleEn: "Use test tubes and microscopes in lab practice or measure and mix samples accurately",
    imageUrl: "/images/assessment/R4.jpg",
    iconKey: "microscope",
  },
  {
    code: "I4",
    dimension: "I",
    round: 4,
    titleVi:
      "Tìm hiểu nguyên lý đằng sau các hiện tượng tự nhiên, dòng điện, biến đổi chất hay thời tiết, khí hậu quanh mình",
    titleEn: "Explore principles behind natural phenomena, electricity, chemical reactions, and weather",
    imageUrl: "/images/assessment/I4.jpg",
    iconKey: "cloud",
  },
  {
    code: "A4",
    dimension: "A",
    round: 4,
    titleVi:
      "Ca hát, tập chơi nhạc cụ, bắt nhịp làm nhạc hoặc tham gia nhảy múa, diễn kịch trong các buổi văn nghệ",
    titleEn: "Sing, practice musical instruments, make beats, or perform dance and drama on stage",
    imageUrl: "/images/assessment/A4.jpg",
    iconKey: "music",
  },
  {
    code: "S4",
    dimension: "S",
    round: 4,
    titleVi:
      "Tham gia hoạt động tình nguyện, giúp đỡ cộng đồng hoặc nhiệt tình đón tiếp, hỗ trợ mọi người trong sự kiện lớp, trường",
    titleEn: "Join community volunteering or warmly welcome and assist people at school events",
    imageUrl: "/images/assessment/S4.jpg",
    iconKey: "handheart",
  },
  {
    code: "E4",
    dimension: "E",
    round: 4,
    titleVi:
      "Đứng lên thuyết trình trước lớp, trước đám đông hoặc nghĩ cách quảng bá hoạt động, sản phẩm sao cho thật thu hút",
    titleEn: "Present in front of a class or crowd, or plan catchy promotions for school activities",
    imageUrl: "/images/assessment/E4.jpg",
    iconKey: "megaphone",
  },
  {
    code: "C4",
    dimension: "C",
    round: 4,
    titleVi:
      "Lên lịch trình chi tiết về giờ giấc, đường đi và danh sách đồ đạc cần mang để chuyến đi hay kế hoạch nhóm diễn ra đúng giờ",
    titleEn: "Plan detailed schedules, routes, and packing checklists so group trips run on time",
    imageUrl: "/images/assessment/C4.jpg",
    iconKey: "calendar",
  },

  // Round 5
  {
    code: "R5",
    dimension: "R",
    round: 5,
    titleVi:
      "Tập luyện các môn sức bền, võ thuật, kỹ năng vận động ngoài trời hoặc rèn tác phong kỷ luật như giờ Quốc phòng",
    titleEn: "Train in endurance sports, martial arts, outdoor skills, or disciplined drills",
    imageUrl: "/images/assessment/R5.jpg",
    iconKey: "dumbbell",
  },
  {
    code: "I5",
    dimension: "I",
    round: 5,
    titleVi:
      "Đọc và suy ngẫm vì sao con người có tâm lý, hành vi khác nhau hoặc tìm hiểu sâu về lịch sử, văn hóa, xã hội",
    titleEn: "Read and reflect on human psychology, behavior, history, culture, and society",
    imageUrl: "/images/assessment/I5.jpg",
    iconKey: "book",
  },
  {
    code: "A5",
    dimension: "A",
    round: 5,
    titleVi:
      "Nghĩ ra cách thể hiện mới lạ, phá cách cho bài tập hay sản phẩm sáng tạo thay vì làm theo khuôn mẫu quen thuộc",
    titleEn: "Invent fresh, unconventional approaches for assignments instead of following templates",
    imageUrl: "/images/assessment/A5.jpg",
    iconKey: "sparkles",
  },
  {
    code: "S5",
    dimension: "S",
    round: 5,
    titleVi:
      "Trò chuyện, giao lưu bằng ngoại ngữ hoặc tìm hiểu phong tục, đời sống văn hóa của nhiều vùng miền, quốc gia",
    titleEn: "Converse in foreign languages or learn about customs and cultures across regions",
    imageUrl: "/images/assessment/S5.jpg",
    iconKey: "globe",
  },
  {
    code: "E5",
    dimension: "E",
    round: 5,
    titleVi:
      "Đứng ra tổ chức buổi liên hoan lớp, sự kiện câu lạc bộ hoặc sắp xếp công việc cho từng bạn để mọi khâu diễn ra suôn sẻ",
    titleEn: "Organize class parties or club events and coordinate roles so every step runs smoothly",
    imageUrl: "/images/assessment/E5.jpg",
    iconKey: "calendar",
  },
  {
    code: "C5",
    dimension: "C",
    round: 5,
    titleVi:
      "Học tập và làm việc theo danh sách từng bước rõ ràng, có quy tắc và biểu mẫu cụ thể để thực hiện thật chuẩn xác",
    titleEn: "Study and work using clear step-by-step checklists, rules, and structured templates",
    imageUrl: "/images/assessment/C5.jpg",
    iconKey: "check",
  },
];
