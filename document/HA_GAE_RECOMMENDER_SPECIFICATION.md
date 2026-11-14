# HA-GAE v3.1: ĐỘNG CƠ ĐỀ XUẤT NGHỀ NGHIỆP THÍCH ỨNG THEO KHỐI LỚP VÀ MÔI TRƯỜNG CÔNG THÁI HỌC GIỚI TÍNH
## (Horizon-Adaptive & Gender-Aware Ergonomic Career Recommendation Engine - Architecture Specification)

---

## 1. TỔNG QUAN VÀ TRIẾT LÝ THIẾT KẾ (CORE PHILOSOPHY)

Hệ thống tư vấn tuyển sinh và định hướng nghề nghiệp `AI_CAREERGUIDE` vận hành trên nền tảng **Mô hình Đề xuất 3 Trụ cột Tất định (Three-Pillar Scoring Architecture)**:
- **Trụ cột 1: RIASEC Holland (45%)** – Khớp vector sở thích nghề nghiệp 6 chiều $(R, I, A, S, E, C)$ chuẩn hóa từ trắc nghiệm O*NET Mini-IP.
- **Trụ cột 2: Học lực & Chuẩn hóa Tuyển sinh Z-Score (35%)** – Khớp điểm tổ hợp môn thi tốt nghiệp THPT so với điểm chuẩn tuyển sinh lịch sử của 435 ngành đào tạo cấp IV (Thông tư 74/2026/TT-BGDĐT).
- **Trụ cột 3: Nhận thức & Nguyện vọng Học tập (20%)** – Khớp phong cách tư duy logic, mức độ tương thích môi trường và phân tích ngữ nghĩa nguyện vọng nghề nghiệp mơ ước.
- **Cơ chế Phân tầng Phễu Nguyện vọng (Two-Tier Aspiration Funnel):**
  * `REACH`: Ngành vươn lên (điểm chuẩn cao hơn điểm hiện tại từ $+1.0$ đến $+2.5$ điểm).
  * `TARGET`: Ngành vừa sức, an toàn (điểm hiện tại bằng hoặc cao hơn chuẩn đến $+2.0$ điểm).
  * `SAFETY`: Ngành dự phòng an toàn cao (điểm hiện tại vượt chuẩn trên $+2.0$ điểm).

Nhằm nâng cao tính cá nhân hóa vượt trội cho học sinh THPT và thí sinh tự do, hệ thống tích hợp 2 thuộc tính nhân khẩu học cốt lõi từ `User Profile`:
- `grade_level` (Khối lớp hiện tại): `"Lớp 10"`, `"Lớp 11"`, `"Lớp 12"`, `"Đã tốt nghiệp cấp 3"`.
- `gender` (Giới tính): `"Nam"`, `"Nữ"`, `"Khác"`.

Giải pháp **HA-GAE v3.1 (Horizon-Adaptive & Gender-Aware Ergonomic Engine)** là kiến trúc quán quân của Đấu trường Arena 8 Agent, vận hành trên hai trục công nghệ nền tảng:

```
                       ┌──────────────────────────────────────────────┐
                       │     HỒ SƠ HỌC SINH: GIỚI TÍNH & KHỐI LỚP     │
                       └──────────────────────┬───────────────────────┘
                                              │
                 ┌────────────────────────────┴────────────────────────────┐
                 ▼                                                         ▼
   ┌───────────────────────────┐                             ┌───────────────────────────┐
   │ TRỤC 1: CHÂN TRỜI THỜI    │                             │ TRỤC 2: CÔNG THÁI HỌC 4D  │
   │   GIAN & CỔNG CHẶN RỦI RO │                             │   & NUDGE BÌNH ĐẲNG GIỚI  │
   ├───────────────────────────┤                             ├───────────────────────────┤
   │ Khối lớp = Thời gian tau  │                             │ 100% Điểm cốt lõi         │
   │ Lớp 10: Chấp nhận thiếu   │                             │   GENDER-BLIND (bình đẳng)│
   │   tới 3.5đ (DREAM/REACH)  │                             │ Tương thích thể lực 4D    │
   │ Lớp 12: Siết chặt an toàn,│                             │   (phys, haz, mob, gap)   │
   │   thiếu >1.2đ loại bỏ ngay│                             │ Zero-Penalty Invariant    │
   │ Đã tốt nghiệp: Ưu tiên    │                             │   (tuyệt đối không trừ đ) │
   │   ngành thực hành/ứng dụng│                             │ Khuyến khích Nữ STEM,     │
   │   và cơ hội việc làm nhanh│                             │   Nam Điều dưỡng/Giáo dục │
   └─────────────┬─────────────┘                             └─────────────┬─────────────┘
                 │                                                         │
                 └────────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │      ĐIỀU PHỐI TÁI XẾP HẠNG 4 TẦNG           │
                       │  - Trọng số Simplex thích ứng thời gian      │
                       │  - Cổng chặn tích cực tách rời (Gatekeeper)  │
                       │  - Phân bổ phễu REACH/TARGET/SAFETY theo lớp │
                       │  - Hoán đổi nguyên tử bảo toàn đa dạng 40%   │
                       └──────────────────────────────────────────────┘
```

---

## 2. TRỤC 1: CHÂN TRỜI THỜI GIAN THI CỬ (TIME-TO-EXAM HORIZON)

### 2.1. Lượng hóa Hệ số Thời gian Tích lũy $\tau$
Định nghĩa hệ số thời gian tích lũy $\tau \in [0.15, 1.00]$ tương ứng với khoảng cách thời gian tới kỳ thi tốt nghiệp THPT:

$$\tau(g) = \begin{cases} 
1.00 & \text{khi } g = \text{"Lớp 10"} \quad (\approx 28 - 30 \text{ tháng tích lũy}) \\
0.65 & \text{khi } g = \text{"Lớp 11"} \quad (\approx 15 - 18 \text{ tháng tích lũy}) \\
0.25 & \text{khi } g = \text{"Lớp 12"} \quad (\approx 3 - 6 \text{ tháng nước rút}) \\
0.15 & \text{khi } g = \text{"Đã tốt nghiệp cấp 3"} \quad (\text{Thí sinh tự do / Xét tuyển thực tế})
\end{cases}$$

### 2.2. Dung sai Điểm Bứt phá Tối đa ($\delta_{max}(\tau)$) làm Cổng Lọc Tích cực
$$\delta_{max}(\tau) = \begin{cases}
3.5 & \text{khi } \tau = 1.00 \quad (\text{Lớp 10: Chấp nhận ngành mơ ước thiếu tối đa 3.5 điểm}) \\
2.6 & \text{khi } \tau = 0.65 \quad (\text{Lớp 11: Cho phép bứt phá tối đa 2.6 điểm}) \\
1.2 & \text{khi } \tau = 0.25 \quad (\text{Lớp 12: Siết chặt thực chiến: Thiếu } > 1.2\text{đ bị loại bỏ vĩnh viễn}) \\
1.0 & \text{khi } \tau = 0.15 \quad (\text{Đã tốt nghiệp: Ưu tiên điểm số thực tế có sẵn})
\end{cases}$$

### 2.3. Ma trận Phân bổ Phễu Nguyện vọng Mục tiêu ($\Phi(\tau)$)
$$\Phi(\tau) = \begin{bmatrix}
Q_{REACH}(\tau) \\
Q_{TARGET}(\tau) \\
Q_{SAFETY}(\tau)
\end{bmatrix} = \begin{cases}
[40\%, 40\%, 20\%]^T & \text{với Lớp 10 (Khám phá & Đặt mục tiêu bứt phá)} \\
[30\%, 50\%, 20\%]^T & \text{với Lớp 11 (Tăng tốc & Định hình trọng tâm)} \\
[15\%, 65\%, 20\%]^T & \text{với Lớp 12 (Thực chiến & Tối đa hóa tỷ lệ đỗ)} \\
[10\%, 60\%, 30\%]^T & \text{với Đã tốt nghiệp (An toàn & Thực tế việc làm)}
\end{cases}$$

### 2.4. Trọng số 3 Trụ cột Bảo toàn Đơn diện (Simplex Constraint)
$$S_{core}(u, m) = w_R(\tau) \cdot S_{RIASEC}(u, m) + w_A(\tau) \cdot S_{Acad}(u, m) + w_C(\tau) \cdot S_{Cogn}(u, m)$$

- $w_R(\tau) = 0.40 + 0.10 \cdot \tau(g)$
- $w_A(\tau) = 0.45 - 0.20 \cdot \tau(g)$
- $w_C(\tau) = 1.0 - [w_R(\tau) + w_A(\tau)] = 0.15 + 0.10 \cdot \tau(g)$

| Khối lớp | RIASEC ($w_R$) | Học lực ($w_A$) | Nhận thức ($w_C$) | Tỷ lệ Phễu (REACH : TARGET : SAFETY) |
| :--- | :---: | :---: | :---: | :---: |
| **Lớp 10** | **50.0%** | 25.0% | 25.0% | **40% REACH** : 40% TARGET : 20% SAFETY |
| **Lớp 11** | **46.5%** | 32.0% | 21.5% | **30% REACH** : 50% TARGET : 20% SAFETY |
| **Lớp 12** | **42.5%** | **40.0%** | 17.5% | 15% REACH : **65% TARGET** : 20% SAFETY |
| **Đã tốt nghiệp** | **41.5%** | **42.0%** | 16.5% | 10% REACH : **60% TARGET** : **30% SAFETY** |

*Nguyên tắc bảo toàn đơn diện:* $\forall \tau, w_R + w_A + w_C \equiv 1.0000$.

---

## 3. TRỤC 2: CÔNG THÁI HỌC 4D & BÌNH ĐẲNG GIỚI (GENDER & ERGONOMIC AI)

### 3.1. Nguyên tắc Bất biến: 100% Core Scoring Gender-Blind
- Điểm nền tảng 3 trụ cột $S_{core}$ hoàn toàn trung lập với giới tính.
- **Bất biến Zero-Penalty:** Tuyệt đối không trừ điểm hoặc cấm đoán bất kỳ ngành nào dựa vào giới tính ($\Delta S_{boost} \ge 0.0$).

### 3.2. Vector Công thái học 4D ($V_{env}$) trên 23 Khối Ngành (TT74/2026/TT-BGDĐT)
Vector $V_{env} = (e_{phys}, e_{haz}, e_{mob}, e_{gap}) \in [0, 1]^4$:
- $e_{phys}$: Mức độ đòi hỏi thể lực và vận động cơ bắp ($0.1$ tại CNTT $\to 0.7$ tại Vận tải).
- $e_{haz}$: Mức độ phơi nhiễm môi trường đặc thù ($0.1$ tại Văn phòng $\to 0.5$ tại Kỹ thuật mỏ / Hóa chất).
- $e_{mob}$: Cường độ di chuyển và thay đổi địa bàn công tác ($0.1$ tại Sư phạm $\to 0.8$ tại Hàng hải).
- $e_{gap}$: Chênh lệch đại diện giới tính lịch sử trong ngành.

**Độ tương thích Thể lực - Sở thích Thực tế ($S_{ergo\_match}$):**
$$S_{ergo\_match} = 1.0 - 0.20 \cdot |e_{phys} - R_{user}|$$
Vi điều chỉnh công thái học tích cực:
$$\Delta S_{ergo} = \max(0.0, 0.01 \cdot (S_{ergo\_match} - 0.70))$$

### 3.3. Cảnh báo Môi trường Lao động Thông minh (Thông tư 10/2020/TT-BLĐTBXH)
Đối với các ngành có điều kiện làm việc hầm lò đặc thù (Kỹ thuật Mỏ `7520601`), viễn dương (Điều khiển tàu biển `7840101`), hoặc hơi khí độc (Kỹ thuật Hóa học `7520301`):
- Hệ thống **KHÔNG CẤM ĐOÁN**, giữ nguyên điểm xếp hạng.
- Tự động bổ sung thẻ cảnh báo công thái học và định hướng chuyên môn an toàn (ví dụ: Nữ sinh theo học ngành Hóa học/Mỏ được khuyến nghị hướng chuyên sâu về Thiết kế mỏ, R&D vật liệu mới, Kiểm nghiệm phòng thí nghiệm QA/QC).

### 3.4. Nudge Đạo đức & Bình đẳng Cơ hội (Affirmative Action Nudge)
- **Nữ sinh có tố chất STEM:** Khi nữ sinh có năng lực hoặc đam mê Kỹ thuật/Công nghệ ($I \ge 0.60$ hoặc $R \ge 0.60$), hệ thống cấp Nudge khuyến khích $+0.025$ đến $+0.04$ điểm và đảm bảo có ngành STEM phù hợp trong đề xuất.
- **Nam sinh có tố chất Chăm sóc:** Khi nam sinh có năng lực Xã hội/Giao tiếp ($S \ge 0.60$), hệ thống cấp Nudge khuyến khích trong các ngành Sư phạm mầm non, Điều dưỡng, Y tế cộng đồng.
- **Thí sinh Đã tốt nghiệp cấp 3:** Cấp ưu tiên $+0.03$ điểm và đảm bảo hạn ngạch 30% cho khối ngành Công nghệ Kỹ thuật thực hành (`751`) và các chương trình thực nghiệm/liên thông.

### 3.5. Kiểm toán Đoàn hệ Ngoại tuyến (Cohort Four-Fifths DIR Audit)
$$DIR(STEM) = \frac{\text{Tỷ lệ Nữ sinh được đề xuất ít nhất 1 ngành STEM}}{\text{Tỷ lệ Nam sinh được đề xuất ít nhất 1 ngành STEM}}$$
Quy định kiểm toán trong CI/CD: $0.80 \le DIR \le 1.25$.

---

## 4. BỘ ĐIỀU PHỐI TÁI XẾP HẠNG 4 TẦNG & PHỄU 2 TẦNG (TWO-TIER FUNNEL)

1. **Cổng chặn Tích cực Tách rời (Decoupled Deficit Active Gatekeeper):**
   Mọi ngành có khoảng thiếu hụt $|Score_{gap}| > \delta_{max}(\tau)$ đều bị cách ly vĩnh viễn vào `pool_unrealistic` và loại trừ tuyệt đối khỏi danh sách đề xuất.
2. **Xử lý Mượt mà khi Chưa có Điểm (Graceful No-Grade Fallback):**
   Khi học sinh Lớp 10 chưa nhập điểm thi tốt nghiệp THPT, hệ thống kích hoạt `pool_other` làm ứng viên hợp lệ, bảo đảm các chính sách Ngành Xu Hướng và Affirmative Nudge vẫn hoạt động trọn vẹn 100%.
3. **Lắp ráp Theo Điểm Mục tiêu (Score-Ordered Quota Assembly):**
   Sau khi trích xuất đủ số lượng chỉ tiêu từng tầng theo ma trận $\Phi(\tau)$, toàn bộ tập hợp được sắp xếp theo hàm mục tiêu tổng hợp $(overall\_score, score\_riasec)$, triệt tiêu hoàn toàn lỗi đảo trật tự xếp hạng.
4. **Hoán đổi Nguyên tử (Atomic Replacement):**
   Hàm hoán đổi `_replace_item` cập nhật đồng bộ hai chiều mã ngành và số đếm nhóm ngành, bảo đảm trần đa dạng không vượt quá 40% (Top 5: max 2 ngành; Top 10: max 4 ngành) và bảo vệ chỉ tiêu ngành an toàn `SAFETY`.

---

## 5. MÔ HÌNH XAI 3 CÂU TINH GỌN & CHIẾN THUẬT NGUYỆN VỌNG BỘ GD&ĐT

Mỗi ngành đề xuất đi kèm lời giải thích minh bạch đúng 3 câu:
- **Câu 1 (Đam mê & Năng lực):** Khớp độ tương thích sở thích Holland và phong cách tư duy.
- **Câu 2 (Tuyển sinh & Môi trường):** Phân tích tính khả thi theo tổ hợp xét tuyển thực tế kèm tên môn học cụ thể (ví dụ: *Khối A00 (Toán, Vật lý, Hóa học)*), đối chiếu điểm số với điểm chuẩn tham chiếu và lưu ý an toàn lao động / cơ hội học bổng.
- **Câu 3 (Chiến thuật Đăng ký Nguyện vọng):**
  * Ngành `REACH` (Thử thách/Bứt phá): **Nguyện vọng 1 - 2**.
  * Ngành `TARGET` (Vừa sức/An toàn): **Nguyện vọng 3 - 5**.
  * Ngành `SAFETY` (Dự phòng vững chắc): **Nguyện vọng 6 trở đi**.
