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
    | "clapperboard"
    | "heart"
    | "compass"
    | "activity"
    | "handheart"
    | "graduation"
    | "building"
    | "rocket"
    | "handshake"
    | "megaphone"
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
    imageUrl:
      "https://images.unsplash.com/photo-1581783898377-1c85bf937427?auto=format&fit=crop&w=900&q=80",
    iconKey: "wrench",
  },
  {
    code: "I1",
    dimension: "I",
    round: 1,
    titleVi:
      "Giải các bài toán khó, câu đố suy luận logic hoặc tự mày mò hiểu vì sao một công thức lại đúng",
    titleEn: "Solve hard math problems, logic puzzles, or understand why a formula works",
    imageUrl:
      "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=900&q=80",
    iconKey: "flask",
  },
  {
    code: "A1",
    dimension: "A",
    round: 1,
    titleVi:
      "Vẽ minh họa, phối màu trang trí poster, bài thuyết trình đẹp mắt hoặc tự phác thảo kiểu trang phục, đồ trang trí riêng",
    titleEn: "Draw illustrations, design posters and slides, or sketch outfits and decor",
    imageUrl:
      "https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&w=900&q=80",
    iconKey: "palette",
  },
  {
    code: "S1",
    dimension: "S",
    round: 1,
    titleVi:
      "Kiên nhẫn giảng lại bài khó cho bạn bè hoặc em nhỏ bằng cách giải thích thật dễ hiểu",
    titleEn: "Patiently explain difficult lessons to classmates or younger students",
    imageUrl:
      "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=900&q=80",
    iconKey: "graduation",
  },
  {
    code: "E1",
    dimension: "E",
    round: 1,
    titleVi:
      "Đứng ra làm nhóm trưởng, phân chia công việc và thúc đẩy cả nhóm hoàn thành mục tiêu đúng hạn",
    titleEn: "Act as team leader, delegate tasks, and keep the group on schedule",
    imageUrl:
      "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?auto=format&fit=crop&w=900&q=80",
    iconKey: "building",
  },
  {
    code: "C1",
    dimension: "C",
    round: 1,
    titleVi:
      "Ghi chép cẩn thận tiền tiêu vặt, giữ quỹ lớp hoặc tính toán các khoản thu chi của nhóm chính xác từng con số",
    titleEn: "Track pocket money, manage the class fund, or calculate group budgets accurately",
    imageUrl:
      "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=900&q=80",
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
    imageUrl:
      "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=900&q=80",
    iconKey: "hammer",
  },
  {
    code: "I2",
    dimension: "I",
    round: 2,
    titleVi:
      "Tò mò cách một ứng dụng, trò chơi hay AI được lập trình bên trong hoặc thích tìm quy luật từ bảng số liệu, biểu đồ",
    titleEn: "Explore how apps, games, or AI are coded, or find patterns in charts and data",
    imageUrl:
      "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=900&q=80",
    iconKey: "network",
  },
  {
    code: "A2",
    dimension: "A",
    round: 2,
    titleVi:
      "Phối màu, bài trí lại góc học tập, phòng ở cho có gu hoặc thích phác họa không gian nhà cửa, quán xá đẹp mắt",
    titleEn: "Style and arrange your study corner or room, or sketch appealing spaces",
    imageUrl:
      "https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=900&q=80",
    iconKey: "palette",
  },
  {
    code: "S2",
    dimension: "S",
    round: 2,
    titleVi:
      "Tìm hiểu cách sơ cứu vết thương, chăm sóc sức khỏe cho mọi người hoặc xây dựng chế độ dinh dưỡng, ăn uống khoa học",
    titleEn: "Learn first aid, healthcare basics, or how to build a scientific nutrition plan",
    imageUrl:
      "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=900&q=80",
    iconKey: "activity",
  },
  {
    code: "E2",
    dimension: "E",
    round: 2,
    titleVi:
      "Làm gian hàng hội chợ ở trường, tập mua bán nhỏ online hoặc nghĩ ý tưởng kinh doanh để tạo ra tiền lãi",
    titleEn: "Run a school fair booth, try small online selling, or brainstorm profitable ideas",
    imageUrl:
      "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?auto=format&fit=crop&w=900&q=80",
    iconKey: "rocket",
  },
  {
    code: "C2",
    dimension: "C",
    round: 2,
    titleVi:
      "Sắp xếp thư mục máy tính, vở ghi và tài liệu học tập ngăn nắp theo từng mục để cần là tìm thấy ngay",
    titleEn: "Organize computer folders, notebooks, and study materials neatly by category",
    imageUrl:
      "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=900&q=80",
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
    imageUrl:
      "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=900&q=80",
    iconKey: "fish",
  },
  {
    code: "I3",
    dimension: "I",
    round: 3,
    titleVi:
      "Tìm hiểu cơ thể sống và di truyền hoạt động thế nào, vì sao ta bị ốm và cách thuốc giúp cơ thể khỏe lại",
    titleEn: "Explore how living bodies and genetics work, why illness happens, and how medicine heals",
    imageUrl:
      "https://images.unsplash.com/photo-1582719471384-894fbb16e074?auto=format&fit=crop&w=900&q=80",
    iconKey: "pill",
  },
  {
    code: "A3",
    dimension: "A",
    round: 3,
    titleVi:
      "Viết truyện, viết bài chia sẻ cảm nhận hoặc chụp ảnh, quay dựng video kể lại một câu chuyện theo ý mình",
    titleEn: "Write stories or reflections, or shoot and edit photos and videos to tell a story",
    imageUrl:
      "https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=900&q=80",
    iconKey: "film",
  },
  {
    code: "S3",
    dimension: "S",
    round: 3,
    titleVi:
      "Kiên nhẫn ngồi lắng nghe người khác tâm sự chuyện buồn, thấu cảm và giúp họ tháo gỡ khúc mắc trong lòng",
    titleEn: "Listen patiently when others confide in you, empathize, and help ease their worries",
    imageUrl:
      "https://images.unsplash.com/photo-1573497620053-ea5300f94f21?auto=format&fit=crop&w=900&q=80",
    iconKey: "heart",
  },
  {
    code: "E3",
    dimension: "E",
    round: 3,
    titleVi:
      "Tham gia tranh biện, đưa ra dẫn chứng và lý lẽ chặt chẽ để thuyết phục người khác hoặc phân xử khi nhóm có bất đồng",
    titleEn: "Debate with clear evidence and reasoning to persuade others or resolve group disagreements",
    imageUrl:
      "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=900&q=80",
    iconKey: "handshake",
  },
  {
    code: "C3",
    dimension: "C",
    round: 3,
    titleVi:
      "Rà soát tỉ mỉ từng dòng bài làm, con số hay lỗi chính tả nhỏ để chắc chắn không sót lỗi trước khi nộp",
    titleEn: "Carefully proofread every line, number, and spelling detail before submitting work",
    imageUrl:
      "https://images.unsplash.com/photo-1553413077-190dd305871c?auto=format&fit=crop&w=900&q=80",
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
    imageUrl:
      "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=900&q=80",
    iconKey: "microscope",
  },
  {
    code: "I4",
    dimension: "I",
    round: 4,
    titleVi:
      "Tìm hiểu nguyên lý đằng sau các hiện tượng tự nhiên, dòng điện, biến đổi chất hay thời tiết, khí hậu quanh mình",
    titleEn: "Explore principles behind natural phenomena, electricity, chemical reactions, and weather",
    imageUrl:
      "https://images.unsplash.com/photo-1504608524841-42fe6f032b4b?auto=format&fit=crop&w=900&q=80",
    iconKey: "cloud",
  },
  {
    code: "A4",
    dimension: "A",
    round: 4,
    titleVi:
      "Ca hát, tập chơi nhạc cụ, bắt nhịp làm nhạc hoặc tham gia nhảy múa, diễn kịch trong các buổi văn nghệ",
    titleEn: "Sing, practice musical instruments, make beats, or perform dance and drama on stage",
    imageUrl:
      "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=900&q=80",
    iconKey: "music",
  },
  {
    code: "S4",
    dimension: "S",
    round: 4,
    titleVi:
      "Tham gia hoạt động tình nguyện, giúp đỡ cộng đồng hoặc nhiệt tình đón tiếp, hỗ trợ mọi người trong sự kiện lớp, trường",
    titleEn: "Join community volunteering or warmly welcome and assist people at school events",
    imageUrl:
      "https://images.unsplash.com/photo-1559027615-cd4628902d4a?auto=format&fit=crop&w=900&q=80",
    iconKey: "handheart",
  },
  {
    code: "E4",
    dimension: "E",
    round: 4,
    titleVi:
      "Đứng lên thuyết trình trước lớp, trước đám đông hoặc nghĩ cách quảng bá hoạt động, sản phẩm sao cho thật thu hút",
    titleEn: "Present in front of a class or crowd, or plan catchy promotions for school activities",
    imageUrl:
      "https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&w=900&q=80",
    iconKey: "megaphone",
  },
  {
    code: "C4",
    dimension: "C",
    round: 4,
    titleVi:
      "Lên lịch trình chi tiết về giờ giấc, đường đi và danh sách đồ đạc cần mang để chuyến đi hay kế hoạch nhóm diễn ra đúng giờ",
    titleEn: "Plan detailed schedules, routes, and packing checklists so group trips run on time",
    imageUrl:
      "https://images.unsplash.com/photo-1519003722824-194d4455a60c?auto=format&fit=crop&w=900&q=80",
    iconKey: "truck",
  },

  // Round 5
  {
    code: "R5",
    dimension: "R",
    round: 5,
    titleVi:
      "Tập luyện các môn sức bền, võ thuật, kỹ năng vận động ngoài trời hoặc rèn tác phong kỷ luật như giờ Quốc phòng",
    titleEn: "Train in endurance sports, martial arts, outdoor skills, or disciplined drills",
    imageUrl:
      "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=900&q=80",
    iconKey: "check",
  },
  {
    code: "I5",
    dimension: "I",
    round: 5,
    titleVi:
      "Đọc và suy ngẫm vì sao con người có tâm lý, hành vi khác nhau hoặc tìm hiểu sâu về lịch sử, văn hóa, xã hội",
    titleEn: "Read and reflect on human psychology, behavior, history, culture, and society",
    imageUrl:
      "https://images.unsplash.com/photo-1576086213369-97a306d36557?auto=format&fit=crop&w=900&q=80",
    iconKey: "book",
  },
  {
    code: "A5",
    dimension: "A",
    round: 5,
    titleVi:
      "Nghĩ ra cách thể hiện mới lạ, phá cách cho bài tập hay sản phẩm sáng tạo thay vì làm theo khuôn mẫu quen thuộc",
    titleEn: "Invent fresh, unconventional approaches for assignments instead of following templates",
    imageUrl:
      "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=900&q=80",
    iconKey: "clapperboard",
  },
  {
    code: "S5",
    dimension: "S",
    round: 5,
    titleVi:
      "Trò chuyện, giao lưu bằng ngoại ngữ hoặc tìm hiểu phong tục, đời sống văn hóa của nhiều vùng miền, quốc gia",
    titleEn: "Converse in foreign languages or learn about customs and cultures across regions",
    imageUrl:
      "https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=900&q=80",
    iconKey: "compass",
  },
  {
    code: "E5",
    dimension: "E",
    round: 5,
    titleVi:
      "Đứng ra tổ chức buổi liên hoan lớp, sự kiện câu lạc bộ hoặc sắp xếp công việc cho từng bạn để mọi khâu diễn ra suôn sẻ",
    titleEn: "Organize class parties or club events and coordinate roles so every step runs smoothly",
    imageUrl:
      "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=900&q=80",
    iconKey: "shopping",
  },
  {
    code: "C5",
    dimension: "C",
    round: 5,
    titleVi:
      "Học tập và làm việc theo danh sách từng bước rõ ràng, có quy tắc và biểu mẫu cụ thể để thực hiện thật chuẩn xác",
    titleEn: "Study and work using clear step-by-step checklists, rules, and structured templates",
    imageUrl:
      "https://images.unsplash.com/photo-1450133064473-71024230f91b?auto=format&fit=crop&w=900&q=80",
    iconKey: "mail",
  },
];
