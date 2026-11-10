export type RiasecDimension = "R" | "I" | "A" | "S" | "E" | "C";

export interface OnetMiniIpItem {
  code: string; // R1..R5, I1..I5, A1..A5, S1..S5, E1..E5, C1..C5
  dimension: RiasecDimension;
  round: 1 | 2 | 3 | 4 | 5;
  titleVi: string; // Concise 4-7 words for zero reading fatigue
  titleEn: string; // Authentic O*NET Mini-IP (Rounds et al., 2016)
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

export const RIASEC_META: Record<
  RiasecDimension,
  { label: string; tag: string; sampleHint: string }
> = {
  R: {
    label: "Thực tế · R",
    tag: "Realistic",
    sampleHint: "Lắp ráp, sửa chữa, vận hành thiết bị",
  },
  I: {
    label: "Nghiên cứu · I",
    tag: "Investigative",
    sampleHint: "Y sinh, thí nghiệm, mô hình dữ liệu",
  },
  A: {
    label: "Nghệ thuật · A",
    tag: "Artistic",
    sampleHint: "Viết lách, âm nhạc, kỹ xảo, thiết kế",
  },
  S: {
    label: "Xã hội · S",
    tag: "Social",
    sampleHint: "Tâm lý, hướng nghiệp, trị liệu, giảng dạy",
  },
  E: {
    label: "Quản lý · E",
    tag: "Enterprising",
    sampleHint: "Khởi nghiệp, đàm phán, tiếp thị, quản trị",
  },
  C: {
    label: "Hệ thống · C",
    tag: "Conventional",
    sampleHint: "Mạng hệ thống, số liệu, kho vận, lưu trữ",
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
 * Official O*NET Mini Interest Profiler (Mini-IP) 30-item set
 * Source: Rounds, J., Ming, C. W. J., Cao, M., Song, C., & Lewis, P. (2016)
 * Interleaved across 5 balanced rounds (R -> I -> A -> S -> E -> C) just like My Next Move.
 */
export const ONET_MINI_IP_ITEMS: OnetMiniIpItem[] = [
  // Round 1
  {
    code: "R1",
    dimension: "R",
    round: 1,
    titleVi: "Đóng & lắp ráp đồ gỗ nội thất",
    titleEn: "Build kitchen cabinets",
    iconKey: "hammer",
  },
  {
    code: "I1",
    dimension: "I",
    round: 1,
    titleVi: "Nghiên cứu phát triển thuốc mới",
    titleEn: "Develop a new medicine",
    iconKey: "pill",
  },
  {
    code: "A1",
    dimension: "A",
    round: 1,
    titleVi: "Viết sách hoặc kịch bản sân khấu",
    titleEn: "Write books or plays",
    iconKey: "book",
  },
  {
    code: "S1",
    dimension: "S",
    round: 1,
    titleVi: "Hỗ trợ người gặp vấn đề tâm lý",
    titleEn: "Help people with personal or emotional problems",
    iconKey: "heart",
  },
  {
    code: "E1",
    dimension: "E",
    round: 1,
    titleVi: "Quản lý phòng ban doanh nghiệp lớn",
    titleEn: "Manage a department within a large company",
    iconKey: "building",
  },
  {
    code: "C1",
    dimension: "C",
    round: 1,
    titleVi: "Cài phần mềm cho hệ thống mạng lớn",
    titleEn: "Install software across computers on a large network",
    iconKey: "network",
  },

  // Round 2
  {
    code: "R2",
    dimension: "R",
    round: 2,
    titleVi: "Sửa chữa thiết bị điện gia dụng",
    titleEn: "Repair household appliances",
    iconKey: "wrench",
  },
  {
    code: "I2",
    dimension: "I",
    round: 2,
    titleVi: "Nghiên cứu cách giảm ô nhiễm nước",
    titleEn: "Study ways to reduce water pollution",
    iconKey: "droplets",
  },
  {
    code: "A2",
    dimension: "A",
    round: 2,
    titleVi: "Sáng tác hoặc phối khí âm nhạc",
    titleEn: "Compose or arrange music",
    iconKey: "music",
  },
  {
    code: "S2",
    dimension: "S",
    round: 2,
    titleVi: "Tư vấn định hướng nghề nghiệp",
    titleEn: "Give career guidance to people",
    iconKey: "compass",
  },
  {
    code: "E2",
    dimension: "E",
    round: 2,
    titleVi: "Tự khởi nghiệp kinh doanh riêng",
    titleEn: "Start your own business",
    iconKey: "rocket",
  },
  {
    code: "C2",
    dimension: "C",
    round: 2,
    titleVi: "Tính toán & xử lý số liệu chính xác",
    titleEn: "Operate a calculator",
    iconKey: "calculator",
  },

  // Round 3
  {
    code: "R3",
    dimension: "R",
    round: 3,
    titleVi: "Nuôi trồng & chăm sóc thủy sản",
    titleEn: "Raise fish in a fish hatchery",
    iconKey: "fish",
  },
  {
    code: "I3",
    dimension: "I",
    round: 3,
    titleVi: "Thực hiện các thí nghiệm hóa học",
    titleEn: "Conduct chemical experiments",
    iconKey: "flask",
  },
  {
    code: "A3",
    dimension: "A",
    round: 3,
    titleVi: "Tạo kỹ xảo hình ảnh cho phim",
    titleEn: "Create special effects for movies",
    iconKey: "film",
  },
  {
    code: "S3",
    dimension: "S",
    round: 3,
    titleVi: "Thực hiện trị liệu & phục hồi thể chất",
    titleEn: "Perform rehabilitation therapy",
    iconKey: "activity",
  },
  {
    code: "E3",
    dimension: "E",
    round: 3,
    titleVi: "Đàm phán hợp đồng kinh doanh",
    titleEn: "Negotiate business contracts",
    iconKey: "handshake",
  },
  {
    code: "C3",
    dimension: "C",
    round: 3,
    titleVi: "Quản lý hồ sơ xuất nhập hàng hóa",
    titleEn: "Keep shipping and receiving records",
    iconKey: "clipboard",
  },

  // Round 4
  {
    code: "R4",
    dimension: "R",
    round: 4,
    titleVi: "Vận chuyển & giao nhận hàng hóa",
    titleEn: "Drive a truck to deliver packages to offices and homes",
    iconKey: "truck",
  },
  {
    code: "I4",
    dimension: "I",
    round: 4,
    titleVi: "Soi mẫu xét nghiệm bằng kính hiển vi",
    titleEn: "Examine blood samples using a microscope",
    iconKey: "microscope",
  },
  {
    code: "A4",
    dimension: "A",
    round: 4,
    titleVi: "Vẽ & thiết kế bối cảnh sân khấu",
    titleEn: "Paint sets for plays",
    iconKey: "palette",
  },
  {
    code: "S4",
    dimension: "S",
    round: 4,
    titleVi: "Tham gia tình nguyện tại tổ chức xã hội",
    titleEn: "Do volunteer work at a non-profit organization",
    iconKey: "handheart",
  },
  {
    code: "E4",
    dimension: "E",
    round: 4,
    titleVi: "Tiếp thị & quảng bá dòng sản phẩm mới",
    titleEn: "Market a new line of clothing",
    iconKey: "megaphone",
  },
  {
    code: "C4",
    dimension: "C",
    round: 4,
    titleVi: "Kiểm kê vật tư bằng thiết bị cầm tay",
    titleEn: "Inventory supplies using a hand-held computer",
    iconKey: "scan",
  },

  // Round 5
  {
    code: "R5",
    dimension: "R",
    round: 5,
    titleVi: "Kiểm tra chất lượng linh kiện kỹ thuật",
    titleEn: "Test the quality of parts before shipment",
    iconKey: "check",
  },
  {
    code: "I5",
    dimension: "I",
    round: 5,
    titleVi: "Xây dựng mô hình dự báo thời tiết",
    titleEn: "Develop a way to better predict the weather",
    iconKey: "cloud",
  },
  {
    code: "A5",
    dimension: "A",
    round: 5,
    titleVi: "Viết kịch bản phim hoặc truyền hình",
    titleEn: "Write scripts for movies or television shows",
    iconKey: "clapperboard",
  },
  {
    code: "S5",
    dimension: "S",
    round: 5,
    titleVi: "Giảng dạy một lớp học bậc THPT",
    titleEn: "Teach a high-school class",
    iconKey: "graduation",
  },
  {
    code: "E5",
    dimension: "E",
    round: 5,
    titleVi: "Tư vấn & bán hàng tại trung tâm thương mại",
    titleEn: "Sell merchandise at a department store",
    iconKey: "shopping",
  },
  {
    code: "C5",
    dimension: "C",
    round: 5,
    titleVi: "Phân loại, sắp xếp & luân chuyển văn thư",
    titleEn: "Stamp, sort, and distribute mail for an organization",
    iconKey: "mail",
  },
];
