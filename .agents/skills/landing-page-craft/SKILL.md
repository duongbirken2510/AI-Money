---
name: landing-page-craft
description: High-converting Vietnamese single-file HTML5 landing page design system and conversion architecture for Deta AI Lab. Use whenever creating, upgrading, or showcasing landing pages (F&B, specialty products, SaaS, courses, B2B services).
---

# Kỹ Năng Thiết Kế Landing Page Chuyển Đổi Cao (Deta AI Craft)

Bộ tiêu chuẩn thiết kế & kiến trúc chuyển đổi giúp Deta AI tạo ra các trang Landing Page 1 file `.html` độc lập, tải tức thì (<50KB HTML/CSS thuần), thẩm mỹ ngang tầm studio thiết kế và tối ưu thói quen mua hàng qua Zalo / Điện thoại tại Việt Nam.

## 1. Hai Hệ Thẩm Mỹ Chủ Đạo (Design Archetypes)

Không dùng một khuôn tối màu đơn điệu cho mọi ngành hàng. Luôn chọn đúng hệ thẩm mỹ theo bản chất sản phẩm:

1. **Warm Editorial Craft (Sáng Tinh Tế & Thủ Công — F&B, Đặc sản, Mỹ phẩm thiên nhiên, Tiệm bánh, Thời trang, Quà tặng)**:
   - **Bảng màu**: Nền giấy kem ấm (`#FBF7F0` hoặc `#FFF8F2`), thẻ trắng ngà (`#FFFFFF`), chữ nâu trầm/than ấm (`#2C1E18` hoặc `#1F2933`), điểm nhấn hổ phách/đất nung/xanh trà (`#C87D32`, `#2F5D50`, `#D97757`), đường viền mảnh ấm (`rgba(44, 30, 24, 0.10)`).
   - **Cặp phông chữ (Typography Pairing)**: Tiêu đề `Lora` hoặc `Playfair Display` (chữ có chân sang trọng, dùng *in nghiêng màu nhấn* cho 2–3 từ đắt giá nhất trong `<h1>`) kết hợp thân chữ `Be Vietnam Pro` dễ đọc tuyệt đối tiếng Việt.
2. **Dark Aurora SaaS (Tối Hiện Đại & Công Nghệ — Phần mềm, AI, Khóa học, Tư vấn B2B, Tài chính)**:
   - **Bảng màu**: Nền Obsidian sâu (`#070D19`) kèm 2 quầng sáng radial-gradient mờ ở góc trên, thẻ kính mờ (`rgba(255,255,255,0.05)` + viền `rgba(255,255,255,0.11)`), điểm nhấn Emerald-Cyan (`#10B981` → `#38BDF8`) hoặc Violet-Rose (`#8B5CF6` → `#EC4899`).
   - **Cặp phông chữ**: Tiêu đề `Plus Jakarta Sans` / `Be Vietnam Pro` (`font-weight: 800–900`, `letter-spacing: -0.025em`) + số liệu `JetBrains Mono`.

## 2. Cấu Trúc 8 Khối Chốt Đơn Chuẩn (8-Section Conversion Flow)

Mỗi trang Landing Page hoàn chỉnh cần đủ 8 nhịp tâm lý từ chạm mắt đến bấm nút Zalo:

1. **Sticky Frosted Topbar**: Thanh điều hướng cố định (`backdrop-filter: blur(12px)`), bên trái có biểu tượng thương hiệu, ở giữa 3 mục neo (`#uu-diem`, `#bang-gia`, `#hoi-dap` — tự ẩn gọn trên màn hình hẹp), bên phải nút CTA nổi bật.
2. **Split Asymmetric Hero (`1.08fr : 0.92fr`)**:
   - *Cột trái*: Nhãn Kicker nhỏ viết hoa → Tiêu đề chính `<h1>` đánh thẳng kết quả khách nhận được (có từ khóa nhấn màu) → Đoạn dẫn 2–3 câu → Cụm 2 nút (`Đặt mua / Nhắn Zalo` + `Xem bảng giá`) → Dải 3 con số chứng thực nhanh.
   - *Cột phải*: Khung hình ảnh/mockup trực quan bo góc lớn (`border-radius: 26px`) kèm **Nhãn nổi chứng thực (Floating Stamp)** đè nhẹ ở góc dưới bên trái (ví dụ: `⭐ 4.9/5 · Giao tận tay 24h`).
3. **3 Lý Do Khác Biệt (`#uu-diem`)**: Đặt trên nền tương phản nhẹ để tách nhịp thị giác; mỗi thẻ chỉ nói 1 cam kết thật cụ thể (nguyên liệu/công nghệ, tốc độ, bảo hành).
4. **Thực Đơn / Bảng Gói Sản Phẩm 3 Mức Giá (`#bang-gia`)**:
   - Thẻ giữa luôn là **Gói Bán Chạy Nhất (Featured)** có viền nhấn nổi bật và nhãn `🔥 Được chọn nhiều nhất`.
   - Ghi rõ giá bán, danh sách quyền lợi gạch đầu dòng `✓` và nút chọn mua chuyển thẳng tới Zalo/Form.
5. **Quy Trình 3 Bước Đơn Giản (`#quy-trinh`)**: Xóa bỏ tâm lý ngại thủ tục (Bước 1 → Bước 2 → Bước 3 nhận hàng/kích hoạt).
6. **Khách Hàng Nói Gì (Social Proof)**: 2–3 trích dẫn chân thực có tên, vai trò/khu vực và số sao `★★★★★`.
7. **Hỏi Đáp Gập Mở (`<details>` FAQ `#hoi-dap`)**: Giải tỏa 3 băn khoăn lớn nhất trước khi mua (phí giao/bảo hành, đối tượng phù hợp, đổi trả).
8. **Khối Chốt Đơn Cuối Trang + Nút Zalo Nổi Góc Phải (Floating Mobile CTA)**:
   - Luôn có nút tròn/viên thuốc nổi cố định ở góc dưới bên phải (`position: fixed; right: 18px; bottom: 18px; z-index: 40`) để khách dùng điện thoại bấm gọi/nhắn Zalo ở bất kỳ vị trí cuộn nào.

## 3. Quy Tắc Kỹ Thuật Bắt Buộc

- **Độc lập 100% (Zero Build Step)**: Toàn bộ CSS & JS nằm gọn trong 1 file `index.html` sạch, mở trực tiếp hoặc đẩy lên bất kỳ hosting tĩnh nào (Cloudflare Pages, GitHub Pages, Vercel, cPanel) đều chạy ngay.
- **Responsive Thực Chiến**: Dưới `860px` tự xếp lưới 2–3 cột thành 1 cột thoáng mắt, chữ `<h1>` dùng `clamp(32px, 5vw, 54px)` không bao giờ tràn màn hình điện thoại `360px`.
- **An Toàn XSS**: Khi sinh từ dữ liệu người dùng nhập, mọi chuỗi phải qua `html.escape()` trước khi đưa vào template.

## 4. Chuẩn Hình Ảnh Chân Thực & Không Gian 3D Tương Tác

- **Sapo Bright Visual Showcase (Dành cho SaaS, Tài liệu số, Khóa học, Chatbot)**:
  - Ưu tiên nền sáng tươi (`#F4F9FF` → `#FFFFFF`), bố cục Zig-Zag xen kẽ giữa **Nội dung lợi ích** và **Khung hình ảnh thực tế / Giao diện chat sống động có ảnh sản phẩm thật** (`/mau-landing/assets/...`) thay vì chỉ hiển thị chữ khô khan.
- **Không Gian 3D WebGL Chân Thực (`threejs-3d-vietnam-craft`)**:
  - Khi trang web hoặc dự án có không gian 3D tương tác (như `/chua-online`), bắt buộc kích hoạt thêm skill [`.agents/skills/threejs-3d-vietnam-craft/SKILL.md`](../threejs-3d-vietnam-craft/SKILL.md) để áp dụng: vật liệu `CanvasTexture` nét cao (gạch Bát Tràng, ngói mũi hài, gỗ lim, đá xanh), kiến trúc đa tầng có đầu đao cong, nhân vật 3D có khớp tay chắp lễ Phật, đổ bóng mềm `PCFSoftShadowMap`, bầu trời 4 thời khắc (`Bình minh / Ban ngày / Hoàng hôn / Đêm hoa đăng`) và Camera xoay 360° mượt mà.
- **Hình Tượng Hóa & Biểu Đồ Phần Mềm Ít Chữ (`visual-infographic-craft`)**:
  - Khi thiết kế Landing Page hoặc Poster giới thiệu phần mềm/ứng dụng, bắt buộc kích hoạt thêm skill [`.agents/skills/visual-infographic-craft/SKILL.md`](../visual-infographic-craft/SKILL.md) để áp dụng quy tắc **80% Hình Tượng & Biểu Đồ SVG / 20% Từ Khóa Đắt Giá**: cắt cúp cận cảnh giao diện (`Focal Crop 1.8x`), dùng biểu đồ sóng âm/vòng đồng tâm/thanh so sánh RAM trực quan thay cho các đoạn văn dài.
