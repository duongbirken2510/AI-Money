---
name: facebook-group-posting
description: >-
  Verified Chrome CDP runbook and anti-filter rules for publishing Facebook Group posts
  and replying to Facebook Group comments with mandatory attached images (0 text links)
  for Deta AI Lab. Activate whenever posting to Facebook Groups, replying to Group comments,
  or modifying social_autopilot.py, numerology_comment_bot.py, or fb_poster.py.
---

# Kỹ Năng Đăng Bài & Trả Lời Bình Luận Facebook Group Kèm Ảnh (Deta AI Lab)

Bộ quy trình chuẩn chống mất ảnh và chống bộ lọc Admin Assist tự động từ chối bài/bình luận khi vận hành trên trình duyệt Bot Chrome (`127.0.0.1:9225`, hồ sơ `~/.config/deta-chrome-bot`).

## 1. Quy Tắc Bất Di Bất Dịch (Zero-Link + Mandatory Image Gate)

1. **Tuyệt đối `0` Link & `0` Tên miền trong chữ (Cả bài đăng Group lẫn bình luận Group)**:
   - Không bao giờ gắn `https://...` hoặc chuỗi tên miền `.vn` / `.com` (`kiemtien.deta.vn`) trong nội dung chữ của bài đăng Group hoặc phản hồi bình luận Group — Admin Assist của các nhóm lớn sẽ tự động chặn (`Bị từ chối`) ngay lập tức.
   - Luôn dẫn khách tinh tế về **dòng hướng dẫn/watermark in sẵn dưới chân tấm ảnh `.PNG` đính kèm** (ví dụ: *"xem dòng hướng dẫn dưới chân tấm ảnh mẫu bên dưới"*).
2. **Cổng Chặn Cứng Bắt Buộc Có Ảnh (Hard Image Gate)**:
   - Mọi bài đăng Group **bắt buộc phải đính kèm ảnh thật** (ảnh Bản đồ Thần Số Học `1080×1350` có watermark hoặc ảnh chụp trực tiếp phòng Lab).
   - **CẤM BẤM NÚT `Đăng`** nếu chưa kiểm chứng trong `[role="dialog"]` có ảnh xem trước thật (`img[src^="blob:"]` hoặc rộng `>= 150px`, hoặc thẻ `[aria-label]` chứa `File phương tiện đính kèm` / `Chỉnh sửa ảnh/video` / `Gỡ file đính kèm` — lưu ý không nhầm với `Chỉnh sửa quyền riêng tư`), `0` thanh tiến trình `[role="progressbar"]`, đồng thời ô chữ vẫn giữ nguyên nội dung (`textLen >= 20`). Nếu thiếu ảnh sau 2 lượt thử, phải hủy đăng và trả lỗi rõ ràng thay vì đăng bài chay không ảnh.

## 2. Quy Trình 5 Bước CDP Chuẩn Khi Đăng Bài Vào Group

Luôn thực hiện đúng thứ tự **Mở Tab Nổi (`bringToFront`) → Gõ Chữ Trước → Đính Kèm Ảnh Sau → Kiểm Chứng Kép Chữ + Ảnh → Bấm Đăng** (đã cài đặt tại [`post_group_safe_with_image`](../../../social_autopilot.py)):

1. **Kích hoạt Tab & Chặn Hộp Thoại File Hệ Điều Hành**:
   - Luôn gọi đủ `Target.activateTarget`, `Page.enable`, `Runtime.enable`, `DOM.enable`, **`Page.bringToFront`** và `Page.setInterceptFileChooserDialog({"enabled": True})`. Không dùng `Emulation.setDeviceMetricsOverride` làm lệch tọa độ chuột thực của cửa sổ Chrome `9225`.
   - Khi mở khung `"Bạn viết gì đi..."`, dùng `el.scrollIntoView({behavior: 'instant', block: 'center'})` và gọi trực tiếp `el.click()` trên phần tử `[role="button"]` (kèm fallback click tọa độ sau khi cuộn đã dừng hẳn).
2. **Gõ Toàn Bộ Nội Dung Chữ Trước (Text-First)**:
   - Khi lọc hộp thoại `[role="dialog"]`, bắt buộc lọc `dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]')` (vì Facebook có thể chèn thêm một thẻ `[role="dialog"]` phụ `aria-label="Tạo bài viết"` cao `60px` hoặc popup thông báo ở cuối DOM).
   - Ngay khi `[role="dialog"]` mở và khung Lexical `[contenteditable="true"]` còn trống thoáng (lưu ý thẻ `contenteditable` rỗng có thể có `height < 10px`, cần leo dần `parentElement` tới khi tìm được khung bao có `width > 40 && height >= 10`), click focus và gõ toàn bộ văn bản trước (xuống dòng bằng `Shift+Enter`, `modifiers: 8`).
   - Kiểm chứng `(box.innerText || '').trim().length >= 20`.
3. **Đính Kèm Ảnh Sau Với DOM Đầy Đủ (`depth: -1`) & Gắn Thẻ Đích Danh**:
   - Không bao giờ dùng `DOM.getDocument({"depth": 1})` vì React Portal của modal Group không nằm ở độ sâu 1.
   - Đánh dấu đúng thẻ `input[type="file"]` nhận `image/*` bên trong `[role="dialog"]` bằng thuộc tính `data-deta-group-file="1"`, sau đó gọi `DOM.getDocument({"depth": -1})` → `DOM.querySelectorAll('input[data-deta-group-file="1"]')` → `DOM.setFileInputFiles`.
   - Nếu lượt 1 chưa thấy ảnh xem trước (do một số nhóm ẩn `<input type="file">` cho đến khi bấm nút), gọi `.click()` vào nút `[aria-label*="Ảnh/video"]` bên trong `[role="dialog"]`, chờ `1.4s` rồi nạp file lượt 2.
4. **Kiểm Chứng Kép Chờ Upload Hoàn Tất Trước Khi Bấm `Đăng`**:
   - Lặp kiểm tra tối đa `15s` cho tới khi đồng thời thỏa mãn cả 4 điều kiện trong `[role="dialog"]`:
     - Có ảnh preview (`previewImgs > 0` hoặc xuất hiện nút `Chỉnh sửa` / `Gỡ ảnh`)
     - Đã tải xong hoàn toàn lên máy chủ Facebook (`[role="progressbar"]` bằng `0`)
     - Nội dung chữ vẫn còn nguyên (`textLen >= 20`)
     - Nút `Đăng` đã bật sáng (`aria-disabled !== 'true'`).
5. **Bấm `Đăng` & Chụp Ảnh Hậu Kiểm**:
   - Chỉ khi bước 4 đạt `True` mới bấm `Đăng`, chờ modal đóng hẳn rồi chụp ảnh hậu kiểm `/tmp/fb-group-<key>-done.png`.

## 3. Quy Trình Chuẩn Khi Trả Lời Bình Luận Trong Group

Đã chuẩn hóa tại [`scan_and_reply_my_tsh_posts`](../../../numerology_comment_bot.py):

1. Từ `/my_posted_content`, ưu tiên mở URL dạng `https://www.facebook.com/photo/?fbid=...&set=gm...` thay vì `/permalink/` để cột bình luận hiển thị trực tiếp (`width > 50`), không bị kẹt hộp thoại modal ẩn.
2. Luôn chuyển bộ lọc từ `"Phù hợp nhất"` sang `"Tất cả bình luận"`.
3. Đính kèm ảnh thẻ `.PNG` vào `input[type="file"]` của đúng khung phản hồi đang mở, gõ nội dung luận giải **0-link**, nhấn `Enter`, và **chờ tối thiểu `12.5s`** cho trạng thái `"Đang viết..."` biến mất hoàn toàn trước khi điều hướng hoặc đóng tab.

## 4. Lệnh Kiểm Chứng Nháp (Dry-Run Không Đăng Thật)

Trước khi bật lịch tự động hoặc sau khi sửa mã nguồn, luôn chạy kiểm chứng nháp (`publish=False`, không bấm `Đăng`) và mở xem ảnh chụp `/tmp/fb-group-<key>-preview.png` bằng `read_file`:

```bash
python3 social_autopilot.py --post-group tsh-113k
```

Kết quả hợp lệ bắt buộc có `"ok": true`, `"dinh_kem_anh": true`, và trên ảnh `/tmp/fb-group-tsh-113k-preview.png` nhìn thấy rõ **cả đoạn văn bản lẫn tấm ảnh xem trước** nằm chung trong hộp thoại `"Tạo bài viết"`.
