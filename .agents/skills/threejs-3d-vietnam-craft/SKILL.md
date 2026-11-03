---
name: threejs-3d-vietnam-craft
description: Realistic browser 3D WebGL (Three.js) architecture, procedural PBR Canvas textures, Vietnamese cultural heritage geometry (chùa cổ, mái đao cong, sân gạch Bát Tràng, hồ sen), 4-phase atmospheric sky domes, soft shadows, and articulated 3D human avatars. Activate whenever creating or upgrading 3D web experiences, virtual spaces, or chua-online.html.
---

# Kỹ Năng Thiết Kế Không Gian 3D WebGL Chân Thực & Kiến Trúc Cổ Truyền Việt Nam (`Three.js Craft`)

Bộ quy chuẩn kỹ thuật bắt buộc giúp Deta AI Lab dựng không gian 3D ngay trên trình duyệt (1 file `.html` độc lập, tải tức thì dưới 1 giây, không phụ thuộc file `.glb` nặng hàng chục MB) nhưng đạt độ **chân thật, có chiều sâu vật liệu, ánh sáng điện ảnh và tỷ lệ kiến trúc Á Đông / Việt Nam chuẩn xác**.

---

## 1. Tuyệt Đối Cấm ("Anti-Primitive Rules" — Lý Do Cảnh 3D Trông Giả/Xấu)

1. **CẤM dùng hình khối cơ bản trần trụi (`ConeGeometry`, `BoxGeometry`, `CylinderGeometry` tô 1 màu hex phẳng)** để làm mái chùa, sân gạch hoặc nhân vật người.
2. **CẤM đặt nền đen kịt (`#110b07`) làm mặc định duy nhất**: Nền tối đen nuốt mất toàn bộ chi tiết kiến trúc, cây cối và mặt nước. Phải có **Bầu trời chuyển sắc đa tầng (Sky Dome)** và bộ chuyển đổi **4 Thời Khắc (`🌅 Bình Minh` · `☀️ Ban Ngày` · `🌇 Hoàng Hôn Vàng` · `🌙 Đêm Hoa Đăng`)**, mặc định mở ở **🌇 Hoàng Hôn Vàng Ấm** hoặc **☀️ Ban Ngày Nắng Trong** để kiến trúc nổi khối rực rỡ ngay giây đầu tiên.
3. **CẤM nhân vật "Hình Nón + Hình Cầu" (2 khối)**: Nhân vật 3D bắt buộc phải có cấu trúc khớp nối (Đầu + Tóc/Khăn + Thân áo tràng vạt chéo + 2 Cánh tay áo rộng + Đôi bàn tay chắp trước ngực `chắp tay` + Chân bước đi nhịp nhàng).
4. **CẤM tắt đổ bóng (`shadowMap`)**: Không có bóng đổ dưới chân công trình, tán cây và nhân vật sẽ khiến mọi vật thể trông như đang "trôi lơ lửng" trên mặt sàn.

---

## 2. Bảng Màu Vật Liệu Kiến Trúc Cổ Truyền Việt Nam (Heritage Material Palette)

Sử dụng hệ màu vật liệu PBR (`MeshStandardMaterial` với `roughness` và `metalness` chuẩn thực tế):

| Vật liệu | Mã màu chuẩn | Roughness | Metalness | Ứng dụng |
| :--- | :--- | :---: | :---: | :--- |
| **Gạch Bát Tràng cổ (`brickCourtyard`)** | `#9A5B36` → `#7C4324` | `0.86` | `0.04` | Sân chùa, lối đi lát gạch chữ Công / vảy cá |
| **Ngói mũi hài rêu phong (`roofTile`)** | `#7A3E26` / `#5C4332` | `0.78` | `0.08` | Mái Chánh Điện 2 tầng chồng diêm, Gác Chuông, Tam Quan |
| **Gỗ lim / Sơn son (`ironwoodLacquer`)** | `#7A2822` / `#4A2E1B` | `0.55` | `0.12` | Hàng cột cái, cột quân, cửa bức bàn, lan can cầu |
| **Tường vôi vàng hoàng thổ (`ochreWall`)** | `#E6DEC8` / `#D8C398` | `0.90` | `0.02` | Tường hồi Chánh Điện, trụ biểu Cổng Tam Quan |
| **Đá xanh Thanh Hóa (`bluestone`)** | `#8E8A7E` / `#68645B` | `0.82` | `0.08` | Bậc tam cấp, lan can đá chạm rồng/mây, chân tảng cột |
| **Đồng vàng thếp kim (`gildedBronze`)** | `#E5B55C` / `#F3D382` | `0.26` | `0.78` | Tượng Phật, Đại Hồng Chung, Lư Hương, viền hoành phi |
| **Ngọc bạch sứ (`whiteJadePorcelain`)** | `#F7F5F0` | `0.22` | `0.10` | Tượng Phật Bà Quan Âm đứng trên đài sen giữa hồ |
| **Nước hồ sen xanh ngọc (`lotusWater`)** | `#1E5B5E` | `0.16` | `0.45` | Mặt nước Ao Sen phản chiếu bầu trời và đèn hoa đăng |

---

## 3. Bộ Sinh Vân Bề Mặt Thủ Tục Nét Cao (`512×512 Procedural CanvasTexture`)

Để không phải tải ảnh ngoài nhưng bề mặt vẫn có vân gạch, vân ngói, vân gỗ và vân đá chân thật, luôn khởi tạo 4 `THREE.CanvasTexture` với `repeatWrapping` và `anisotropy = 4`:

1. **`createBatTrangTileTexture()`**: Vẽ lưới gạch vuông/chữ nhật so le màu đỏ đất nung (`#9A5B36`), đường mạch vữa xám ấm (`#523828`), điểm các hạt nhiễu rêu phong và độ đậm nhạt ngẫu nhiên từng viên.
2. **`createTraditionalRoofTileTexture()`**: Vẽ các hàng ngói mũi hài xếp lớp vảy cá cong đều, có bóng đổ tối ở chân hàng ngói và ánh sáng hắt nhẹ ở mũi ngói.
3. **`createCarvedWoodTexture()`**: Vẽ sọc vân gỗ lim dọc kết hợp khung pano cửa bức bàn chạm hoa văn chữ Thọ / hoa sen vàng kim.
4. **`createBluestoneTexture()`**: Vẽ hạt đá granite xanh xám li ti cho bậc tam cấp, chân tảng đá và thành giếng/bờ hồ.

---

## 4. Kiến Trúc Chùa Việt Nam Đa Tầng (Multi-Tiered Vietnamese Pagoda Geometry)

Một công trình Chùa Việt Nam chân thật trên 3D phải được ghép từ các bộ phận kiến trúc đúng truyền thống thay vì 1 khối nón:

1. **Nền Đá Tam Cấp & Lan Can Chạm Rồng (`Stone Terrace & Steps`)**:
   - Đế nền cao `0.75m` ốp đá xanh, phía trước mở bậc tam cấp 7 bậc có 2 dải thành bậc đá chạm vân mây dẫn lên hiên Chánh Điện.
2. **Hàng Cột Gỗ Lim Trên Chân Tảng Đá Sen (`Pillars & Plinths`)**:
   - Mỗi cột gồm: Đế chân tảng đá tròn chạm cánh sen ở dưới + Thân cột gỗ lim/sơn son tròn thuôn nhẹ lên trên (`CylinderGeometry(0.20, 0.24, 3.8, 16)`) + Đầu cột đấu củng đỡ mái.
3. **Tường Vôi Hoàng Thổ & Hệ Cửa Bức Bàn (`Ochre Walls & Lattice Doors`)**:
   - Mặt tiền Chánh Điện có bộ cửa gỗ bức bàn 5 gian mở rộng ở gian giữa để nhìn rõ tôn tượng Phật A Di Đà / Thích Ca thếp vàng rực sáng bên trong cùng hoành phi *"Liên Hoa Các"* và đôi câu đối đỏ chữ vàng.
4. **Mái Chồng Diêm 2 Tầng & 8 Đầu Đao Cong Vút (`Double-Tiered Curved Roof & Upturned Eaves`)**:
   - Ghép 2 tầng mái (`Tầng mái hạ` rộng bên dưới + `Cổ diêm` + `Tầng mái thượng` bên trên).
   - Bờ nóc đắp nổi lưỡng long chầu mặt nguyệt / bánh xe Pháp luân vàng.
   - **8 góc mái có Đầu Đao uốn cong vút lên trời** kèm đèn lồng đỏ tua rua vàng treo rủ dưới hiên.
5. **Đài Quan Âm Giữa Hồ Sen & Cầu Gỗ Đỏ (`Lotus Pond Pavilion & Bridge`)**:
   - Hồ nước viền đá cuội và bụi trúc, mặt nước có lá sen xanh nhiều kích cỡ, búp sen hồng và đèn hoa đăng phản chiếu ánh sáng xuống mặt nước.
   - Giữa hồ dựng đài lục giác / đài sen 3 tầng đỡ tôn tượng **Quan Thế Âm Bồ Tát bạch ngọc** đứng uy nghi, nối với bờ bằng nhịp cầu gỗ sơn đỏ cong nhẹ.

---

## 5. Nhân Vật 3D Có Khớp Tay Chân & Động Tác Lễ Phật (`Articulated Human Avatar Rig`)

Mỗi đạo hữu / Phật tử trong sân chùa phải là một `THREE.Group` gồm đủ 8 bộ phận:
- **Đầu (`head`)**: Khối cầu da hồng hào ấm áp + đôi mắt hiền hòa.
- **Tóc / Búi tóc (`hair`)**: Tóc đen gọn gàng hoặc mũ nâu chú tiểu.
- **Thân Áo Tràng (`torso` + `robeSkirt`)**: Áo tràng cổ chéo chữ V có viền vạt áo thanh lịch (Áo Lam `#5B7083`, Áo Nâu `#8C4A27`, Áo Vàng `#D9822B`, Áo Ngọc `#2A7B76`).
- **2 Cánh Tay Áo Rộng & Đôi Bàn Tay (`leftArm`, `rightArm`, `hands`)**:
  - Khi đứng lễ / cầu nguyện: Hai tay đưa lên **chắp trước ngực (`chắp tay búp sen`)**, thân trên cúi vái nhịp nhàng (`bowing`).
  - Khi đi dạo: Hai tay và bước chân đung đưa tự nhiên theo hàm `Math.sin(walkPhase)`, nhân vật xoay mặt mượt mà (`lerpAngle`) về hướng di chuyển.
  - Khi ngồi thiền / gõ mõ trên bồ đoàn: Nhân vật hạ thấp độ cao, xếp bằng tĩnh tại trên đệm bồ đoàn thêu hoa sen.

---

## 6. Hệ Thống Ánh Sáng Điện Ảnh & Camera Góc Nhìn Thứ Ba (`Camera & Lighting`)

1. **Renderer Chuẩn Phim Ảnh**:
   - Bật `renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;`
   - Bật `renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;`
2. **Bầu Trời 4 Thời Khắc (`Time-of-Day Switcher`)**:
   - Cho phép người dùng bấm chuyển ngay trên thanh HUD:
     - `🌅 Bình Minh`: Trời hồng đào pha tím sương mai, nắng sớm dịu.
     - `☀️ Ban Ngày`: Trời xanh ngọc bích sáng rõ, nắng vàng tươi, thấy rõ từng viên ngói, viên gạch Bát Tràng và bóng cây Bồ Đề.
     - `🌇 Hoàng Hôn` *(Mặc định ấn tượng nhất)*: Bầu trời cam hổ phách chuyển tím hoàng hôn, nắng chiều xiên ấm áp kết hợp đèn lồng và hoa đăng bắt đầu rực sáng.
     - `🌙 Đêm Hoa Đăng`: Trời đêm xanh thẫm đầy sao lấp lánh, trăng rằm tỏa sáng, tôn bật hàng chục ngọn đèn hoa đăng vàng và ánh sáng ấm từ Chánh Điện.
3. **Camera Góc Nhìn Thứ 3 Mượt Mà + Xoay 360° & Thu Phóng (`Orbit + Follow Camera`)**:
   - Hỗ trợ **kéo chuột / vuốt ngón tay để xoay góc nhìn 360° quanh sân chùa**, **lăn chuột / chụm tay để phóng to nhìn cận cảnh nhân vật & tượng Phật hoặc thu nhỏ ngắm toàn cảnh chùa**, và tự động đi theo nhân vật nhẹ nhàng khi bước đi.
