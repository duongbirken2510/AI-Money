---
name: visual-infographic-craft
description: Iconic software showcase posters, visual metaphors, SVG charts (radial rings, audio waveforms, benchmark bars, pain-vs-relief split), and zoomed UI focal-crop design system with minimal text (80% visual / 20% punchy keywords). Activate whenever designing software posters, infographics, feature diagrams, or upgrading landing page visuals.
---

# Kỹ Năng Thiết Kế Ảnh Hình Tượng & Biểu Đồ Phần Mềm (Visual Infographic Craft)

Bộ quy chuẩn giúp AI thiết kế các tấm Poster giới thiệu phần mềm (`1440×960` / `1200×900`) và các khối đồ họa trên Landing Page mang **tính hình tượng cao, nhìn 2 giây hiểu ngay giá trị cốt lõi mà không cần đọc nhiều chữ**.

---

## 1. Quy Tắc Vàng: "80% Hình Tượng & Biểu Đồ — Tối Đa 20% Chữ"

1. **Cấm nhồi chữ & Cấm để ảnh chụp màn hình nguyên khổ chữ nhỏ li ti**:
   - Người lướt Facebook/Threads hoặc đọc Landing Page chỉ dừng lại **1.5 – 2 giây**. Nếu ảnh chứa toàn chữ nhỏ hoặc bảng biểu dày đặc, mắt người xem sẽ lướt qua ngay.
   - **Focal Crop (Cắt cúp cận cảnh `1.6x – 2.2x`)**: Chỉ cắt lấy đúng phần giao diện có hình vẽ đẹp nhất (ví dụ: *Hình vẽ bàn tay giãn cơ `+35°`*, *Chậu cây nở hoa*, *Vòng tròn đếm ngược 44:59*) thay vì thu nhỏ cả cửa sổ ứng dụng rộng `2560px`.
2. **Giới hạn độ dài nhãn (Strict Word Cap)**:
   - Tiêu đề chính trên ảnh: tối đa **8 – 10 từ**, cỡ chữ cực lớn (`44px – 54px`).
   - Mỗi thẻ hình tượng / nhánh biểu đồ: chỉ gồm **1 Biểu Tượng Lớn (Icon/Vector/Chart) + 1 Con Số Đắt Giá + Nhãn tối đa 4–5 từ** (ví dụ: `👀 20-20-20 · Nghỉ mắt đúng nhịp`, `🪶 15 MB RAM · Tauri Rust`).

---

## 2. Bốn Mẫu Biểu Đồ & Hình Tượng Hóa Phần Mềm Chuẩn Studio

Khi giới thiệu bất kỳ phần mềm hay công cụ nào, luôn chuyển hóa câu chữ thành **4 dạng đồ họa trực quan** sau:

### Mẫu A: Sơ Đồ Chuyển Hóa "Nỗi Đau Đỏ 🔴 $\rightarrow$ Giải Pháp Xanh 🟢" (Pain-to-Relief Visual Split)
- Đặt các biểu tượng nỗi đau của người dùng (mắt khô rát, cổ vai gáy bó cứng, cổ tay tê RSI, quảng cáo cắt ngang mạch code) đối lập trực tiếp với hình tượng giải phóng của phần mềm.
- Dùng màu sắc dẫn hướng cảm xúc tức thì: Đỏ cam mờ (`#F43F5E`) cho nỗi đau $\rightarrow$ Xanh ngọc phát sáng (`#10B981` / `#38BDF8`) cho trạng thái cân bằng.

### Mẫu B: Biểu Đồ Vòng Tròn Nhịp Sinh Học & Sóng Âm (`SVG Radial Rings & Audio Ducking Waveforms`)
- Thay vì viết câu dài *"Khi giọng nhắc vang lên, nhạc YouTube tự nhỏ xuống 20%"*, hãy vẽ **Biểu đồ Sóng Âm Hạ Nhịp (`Audio Ducking Waveform SVG`)**: Sóng nhạc `100%` tự động võng mượt xuống `20%` ngay tại điểm có biểu tượng `🔊 Giọng nhắc AI`, rồi nâng lên `100%`!
- Thay vì liệt kê các tính năng rời rạc, hãy vẽ **Vòng Đếm Đồng Tâm (`Dual Activity Rings`)** nối ra các bong bóng hình tượng lớn.

### Mẫu C: Thanh So Sánh Hiệu Năng Trực Giác (`Visual Benchmark Bar`)
- Khi phần mềm có ưu thế kỹ thuật (như viết bằng Tauri/Rust hoặc Python thuần), luôn vẽ **2 thanh ngang so sánh tỷ lệ thật**:
  - `App Electron thường`: Thanh đỏ dài hết khung (`~650 MB RAM · Nặng máy`)
  - `DeskAura (Tauri v2 + Rust)`: Chấm xanh siêu nhỏ (`~15 MB RAM · Bộ cài 2.9 MB — Nhẹ hơn 40 lần!`)

### Mẫu D: Kính Lúp Phóng To Điểm Nhấn (`Magnified UI Focal Cards`)
- Ghép **2–3 thẻ giao diện đã cắt cúp cận cảnh (Focal-Cropped Cards)** xếp lớp có chiều sâu (`box-shadow`, viền phát sáng), mỗi thẻ đại diện cho 1 khoảnh khắc trải nghiệm đắt giá nhất của người dùng.

---

## 3. Quy Trình Kết Xuất Ảnh Nét Căng (Retina Headless Rendering)

1. Dựng bố cục bằng HTML5 + CSS Grid + **Inline SVG Charts** ở kích thước chuẩn `1440×960` (tỷ lệ `3:2` hiển thị trọn vẹn không bị cắt trên cả Desktop lẫn Mobile Feed của Facebook/Threads).
2. Luôn giữ thanh **Footer Watermark Bar** контраст cao ở đáy ảnh ghi rõ **Tên miền tải nhanh** (chữ vàng `#FBBF24`) và **GitHub Repo** (chữ xanh `#38BDF8`) để tuân thủ quy tắc **0 Link Text** khi đăng Group Facebook.
3. Kết xuất bằng `google-chrome --headless=new --window-size=1440,960 --screenshot` và kiểm tra trực tiếp bằng `read_file` để đảm bảo mọi biểu đồ, icon và hình cắt cúp đều rõ nét từ khoảng cách nhìn lướt 1 giây.
