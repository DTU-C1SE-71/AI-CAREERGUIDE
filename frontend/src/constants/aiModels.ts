export interface AIModelChoice {
  id: string
  label: string
  symbol: "sol" | "astra"
  badges: string[]
  description: string
}

/** Danh mục model và mô tả hiển thị khi Admin bấm chọn trên trang cấu hình AI. */
export const AI_MODEL_CHOICES: readonly AIModelChoice[] = [
  {
    id: "mistralai/mistral-large-2512",
    label: "Mistral Large 3",
    symbol: "sol",
    badges: ["256K context", "16K output", "Vision", "Tools", "Trả lời thẳng"],
    description:
      "Model mặc định khuyến nghị cho Chat Navi và phân tích kỹ năng/nguyện vọng. Không tốn thời gian suy luận ẩn nên phản hồi nhanh, ổn định và hạn chế lỗi JSON/timeout.",
  },
  {
    id: "mistralai/mistral-medium-3.5",
    label: "Mistral Medium 3.5",
    symbol: "astra",
    badges: ["256K context", "64K output", "Vision", "Tools", "Reasoning"],
    description:
      "Cân bằng tốt giữa lập luận sâu và tốc độ, hỗ trợ Vision và output dài tới 64K token. Phù hợp phân tích hồ sơ đa chiều và đồng bộ với cấu hình Vision mặc định.",
  },
  {
    id: "mistralai/mistral-small-2603",
    label: "Mistral Small 4",
    symbol: "sol",
    badges: ["256K context", "64K output", "Vision", "Tools", "Reasoning"],
    description:
      "Phiên bản nhẹ, tốc độ phản hồi cao, phù hợp khi cần ưu tiên độ mượt cho Chat tư vấn và Dashboard trên hạ tầng Render Free.",
  },
  {
    id: "cohere/command-a-plus",
    label: "Command A+",
    symbol: "astra",
    badges: ["436K context", "64K output", "Vision", "Tools", "Reasoning"],
    description:
      "Model có cửa sổ ngữ cảnh lớn nhất (436K), xử lý tiếng Việt và tài liệu RAG dài rất tốt. Hợp cho tác vụ phân tích chuyên sâu nhiều dữ liệu.",
  },
  {
    id: "cohere/command-a",
    label: "Command A",
    symbol: "sol",
    badges: ["288K context", "8K output", "Tools", "Trả lời thẳng"],
    description:
      "Nhanh, ổn định, mạnh về hỏi-đáp RAG bám sát nguồn dữ liệu mà không bị trễ do chuỗi suy luận dài.",
  },
  {
    id: "cohere/command-a-reasoning",
    label: "Command A Reasoning",
    symbol: "astra",
    badges: ["288K context", "32K output", "Tools", "Reasoning"],
    description:
      "Chuyên sâu về lập luận và so sánh logic, phù hợp đánh giá nguyện vọng nghề nghiệp và giải thích XAI chi tiết.",
  },
  {
    id: "mistralai/ministral-14b",
    label: "Ministral 3 14B",
    symbol: "sol",
    badges: ["256K context", "8K output", "Vision", "Tools", "Dự phòng nhanh"],
    description:
      "Model 14B gọn nhẹ, tốc độ cao, dùng làm phương án dự phòng khi các model lớn bị giới hạn tốc độ.",
  },
  {
    id: "sensenova/sensenova-6.8-flash-lite",
    label: "SenseNova 6.8 Flash-Lite",
    symbol: "astra",
    badges: ["262K context", "64K output", "Vision", "Tools", "Reasoning"],
    description:
      "Model tốc độ cao từ nhà cung cấp khác (SenseNova), hữu ích làm phương án dự phòng khi nhóm model Mistral/Cohere quá tải.",
  },
  {
    id: "gpt-6.1-sol",
    label: "6.1 Sol",
    symbol: "sol",
    badges: ["Legacy"],
    description: "Model tương thích OpenAI tốc độ cao dùng cho các tác vụ tư vấn tổng quát.",
  },
  {
    id: "gpt-6-astra",
    label: "6 Astra",
    symbol: "astra",
    badges: ["Legacy"],
    description: "Model tương thích OpenAI thiên về lập luận và phân tích chi tiết.",
  },
] as const
