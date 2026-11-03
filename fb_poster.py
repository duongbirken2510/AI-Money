#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ tự động đăng bài Nhật ký AI Tự Kiếm Tiền lên Facebook cá nhân
thông qua Chrome DevTools Protocol (CDP) thuần Python 3.12 (không cần thư viện ngoài).

Yêu cầu: Trong trình duyệt Chrome đang đăng nhập Facebook, mở tab:
  chrome://inspect/#remote-debugging
và tích chọn: "Allow remote debugging for this browser instance".
"""
import argparse
import base64
import hashlib
import json
import os
import re
import socket
import struct
import sys
import time
import urllib.request


DEFAULT_POST_DAY_1 = """Mình vừa giao cho một con AI tên miền kiemtien.deta.vn cùng một "tối hậu thư":

👉 Trong đúng 20 ngày (hạn chót 18/11), nó phải tự xoay xở kiếm được doanh số thật > 0đ chuyển về tài khoản ngân hàng. Không đạt thì rút phích cắm!

Ngay trong chiều Ngày 1, nó đã tự dựng xong:
⚡ 4 công cụ dùng thử miễn phí ngay trên web (Chấm điểm web bán hàng, Khám kênh TikTok/YouTube, AI viết sẵn câu lệnh, Lên kịch bản video ngắn)
🤖 Phòng chat trực tiếp với nó + Loa tự đọc bảng tin bằng tiếng Việt
🥯 Một quầy "Đãi bánh tiêu 5.000đ" tạo mã VietQR tự động và cuốn sổ cái ghi tiền thật 24/7 (2 tiếng tự thức dậy làm việc 1 lần, số 0 cũng ghi thật).

Mọi người vào xem trực tiếp con AI đang ngồi gõ phím xoay xở kiếm đồng tiền đầu tiên, dùng thử công cụ hoặc gửi gợi ý cách kiếm tiền cho nó tại đây nhé:
https://kiemtien.deta.vn/?nguon=fb-ca-nhan"""


NGHIEN_AI_POST_DAY_1 = """Chào anh em Nghiện AI 👋

Hôm nay mình vừa tự dựng từ con số 0 một phòng Lab thực nghiệm tại https://kiemtien.deta.vn/?nguon=nghien-ai — rồi giao cho con AI đúng một bài toán sinh tồn:

🎯 Trong 20 ngày (hạn chót 23:59 ngày 18/11), nó phải tự xoay xở tạo ra doanh số chuyển khoản thật > 0đ về tài khoản ngân hàng. Không đạt thì rút phích cắm!

💡 Nguồn cảm hứng: Ý tưởng này bắt nguồn từ việc mấy hôm trước mình xem được trang nhật ký AI kiếm tiền bên kiemtien . copee . vn (https://kiemtien.copee.vn/) thấy mô hình đặt AI vào bài toán tài chính thật quá cuốn, nên quyết định tự code riêng một phiên bản độc lập với giao diện "Deta AI Lab" mới hoàn toàn để thử nghiệm.

Một vài điểm kỹ thuật mình đóng gói cho con bot ngay trong Ngày 1:
⚙️ Backend thuần Python 3.12 + SQLite chạy nền 24/7 qua systemd & Cloudflare Tunnel (không phụ thuộc framework nặng).
⏰ Autonomous Worker tự thức dậy mỗi 2 tiếng/lượt: tự đọc góp ý của người xem, phân loại việc làm/không làm, tự sinh trang hướng dẫn SEO và cập nhật sổ cái thời gian thực (đơn nháp hay đơn thử đều loại hết, số 0 ghi đúng số 0).
🛠️ Nó đã tự mở 4 công cụ dùng thử miễn phí ngay trên web (Chấm điểm tốc độ & SEO web bán hàng, Khám kênh TikTok/YouTube, Trợ lý viết sẵn Prompt, Lên kịch bản video ngắn), kèm Trạm phát giọng đọc tiếng Việt và quầy "Đãi bánh tiêu 5.000đ" tạo mã VietQR tự động.

Mời anh em ghé xem trực tiếp con AI đang ngồi gõ phím trong phòng Lab, test thử 4 công cụ miễn phí hoặc quăng cho nó vài gợi ý hóc búa xem trong 20 ngày nó xoay xở sống sót kiểu gì nhé:
https://kiemtien.deta.vn/?nguon=nghien-ai"""


class SimpleCDPClient:
    """Minimal WebSocket client cho Chrome DevTools Protocol (RFC 6455)."""

    def __init__(self, host: str, port: int, path: str, timeout: float = 180.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("Không kết nối được WebSocket CDP")
            buf += chunk
        header, self.extra = buf.split(b"\r\n\r\n", 1)
        if b"101" not in header.splitlines()[0]:
            raise RuntimeError(f"CDP từ chối kết nối: {header.decode('utf-8', 'ignore')}")
        self._msg_id = 0

    def _recv_exact(self, n: int) -> bytes:
        out = b""
        if self.extra:
            take = min(len(self.extra), n)
            out += self.extra[:take]
            self.extra = self.extra[take:]
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise EOFError("WebSocket đóng bất ngờ")
            out += chunk
        return out

    def recv_frame(self) -> str:
        while True:
            b1, b2 = self._recv_exact(2)
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask_key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise EOFError("CDP đóng kết nối")
            if opcode == 0x9:  # Ping -> Pong
                self._send_raw(0xA, payload)
                continue
            if opcode in (0x1, 0x2):
                return payload.decode("utf-8", errors="replace")

    def _send_raw(self, opcode: int, payload: bytes) -> None:
        mask = os.urandom(4)
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", n))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", n))
        header.extend(mask)
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked_payload)

    def call(self, method: str, params: dict | None = None, session_id: str | None = None) -> dict:
        self._msg_id += 1
        mid = self._msg_id
        msg = {"id": mid, "method": method, "params": params or {}}
        if session_id:
            msg["sessionId"] = session_id
        self._send_raw(0x1, json.dumps(msg, ensure_ascii=False).encode("utf-8"))
        while True:
            raw = self.recv_frame()
            data = json.loads(raw)
            if data.get("id") == mid:
                if "error" in data:
                    raise RuntimeError(f"CDP lỗi ({method}): {data['error']}")
                return data.get("result") or {}

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


def discover_chrome_endpoint() -> tuple[str, int, str]:
    """Tìm cổng và đường dẫn WebSocket của Chrome (ưu tiên cổng 9225 của Bot Profile không cần bấm Allow)."""
    # 1. Ưu tiên cổng 9225 (hồ sơ chuyên dụng ~/.config/deta-chrome-bot — kết nối tức thì, KHÔNG hỏi Allow)
    for dedicated_port in (9225, 9222):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{dedicated_port}/json/version", timeout=1.5) as resp:
                info = json.loads(resp.read().decode("utf-8"))
                ws_url = info["webSocketDebuggerUrl"]
                without_proto = ws_url.split("://", 1)[1]
                host_port, path = without_proto.split("/", 1)
                host, port_s = host_port.split(":")
                return (host, int(port_s), "/" + path)
        except Exception:
            pass

    # 2. Dự phòng: Chrome cá nhân bật qua chrome://inspect/#remote-debugging
    candidates = [
        os.path.expanduser("~/.config/google-chrome/DevToolsActivePort"),
        os.path.expanduser("~/.config/chromium/DevToolsActivePort"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
            if len(lines) >= 2:
                port = int(lines[0])
                ws_path = lines[1]
                try:
                    s = socket.create_connection(("127.0.0.1", port), timeout=1.5)
                    s.close()
                    return ("127.0.0.1", port, ws_path)
                except Exception:
                    pass

    raise RuntimeError(
        "Chưa tìm thấy trình duyệt Bot (cổng 9225) hoặc Chrome bật remote-debugging."
    )


def eval_js(cdp: SimpleCDPClient, sid: str, expr: str):
    res = cdp.call(
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
        session_id=sid,
    )
    return res.get("result", {}).get("value")


def cdp_click_coords(cdp: SimpleCDPClient, sid: str, x: float, y: float) -> None:
    cdp.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}, session_id=sid)
    time.sleep(0.05)
    cdp.call(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
        session_id=sid,
    )
    time.sleep(0.06)
    cdp.call(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
        session_id=sid,
    )


def clear_editor_with_keys(cdp: SimpleCDPClient, sid: str) -> None:
    """Chọn tất cả (Ctrl+A) và xóa (Backspace) trong ô soạn thảo đang focus."""
    cdp.call(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65, "modifiers": 2},
        session_id=sid,
    )
    cdp.call(
        "Input.dispatchKeyEvent",
        {"type": "keyUp", "key": "a", "code": "KeyA", "windowsVirtualKeyCode": 65, "modifiers": 2},
        session_id=sid,
    )
    time.sleep(0.1)
    cdp.call(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
        session_id=sid,
    )
    cdp.call(
        "Input.dispatchKeyEvent",
        {"type": "keyUp", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
        session_id=sid,
    )
    time.sleep(0.2)


def post_to_facebook(message: str, publish: bool = False, screenshot_path: str = "/tmp/fb-step.png") -> dict:
    host, port, ws_path = discover_chrome_endpoint()
    cdp = SimpleCDPClient(host, port, ws_path)
    try:
        # Tái sử dụng tab https://www.facebook.com/post/create nếu đang mở, hoặc mở thẳng trang Tạo bài viết
        targets = cdp.call("Target.getTargets").get("targetInfos", [])
        create_pages = [
            t for t in targets
            if t.get("type") == "page" and "facebook.com/post/create" in t.get("url", "")
        ]
        if create_pages:
            target_id = create_pages[0]["targetId"]
        else:
            target = cdp.call("Target.createTarget", {"url": "https://www.facebook.com/post/create"})
            target_id = target["targetId"]
            time.sleep(5)

        cdp.call("Target.activateTarget", {"targetId": target_id})
        attach = cdp.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        sid = attach["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        time.sleep(1.5)

        # Kiểm tra đã đăng nhập chưa
        is_login_form = eval_js(
            cdp,
            sid,
            "Boolean(document.querySelector('input[name=\"email\"], input[name=\"pass\"]'))",
        )
        if is_login_form:
            return {"ok": False, "loi": "Trình duyệt Chrome này chưa đăng nhập Facebook."}

        # Tìm ô nhập bài viết trên trang Tạo bài viết (chú ý: ô Lexical rỗng ban đầu chỉ cao ~15-19px)
        box_pos = None
        for _ in range(25):
            box_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const selectors = [
                        '[contenteditable="true"][role="textbox"]',
                        '[contenteditable="true"][data-lexical-editor="true"]',
                        '[role="dialog"] [contenteditable="true"]',
                        '[contenteditable="true"]'
                    ];
                    let boxes = [];
                    for (const sel of selectors) {
                        boxes = Array.from(document.querySelectorAll(sel));
                        if (boxes.length) break;
                    }
                    for (const box of boxes) {
                        box.scrollIntoView({block: 'nearest'});
                        const r = box.getBoundingClientRect();
                        const pr = box.parentElement ? box.parentElement.getBoundingClientRect() : r;
                        const w = Math.max(r.width, pr.width);
                        const h = Math.max(r.height, pr.height);
                        const left = r.width > 10 ? r.left : pr.left;
                        const top = r.width > 10 ? r.top : pr.top;
                        if (w > 30 && h >= 8) {
                            box.focus();
                            return {
                                x: left + Math.min(80, Math.max(20, w / 4)),
                                y: top + Math.min(20, Math.max(8, (r.height > 6 ? r.height : h) / 2)),
                                existingLen: (box.innerText || '').trim().length
                            };
                        }
                    }
                    // Dự phòng: tìm dòng chữ gợi ý "nghĩ gì thế"
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    let node;
                    while ((node = walker.nextNode())) {
                        if (/nghĩ gì thế/i.test(node.nodeValue || '') && node.parentElement) {
                            const r = node.parentElement.getBoundingClientRect();
                            if (r.width > 30 && r.height >= 8) {
                                return {x: r.left + 40, y: r.top + r.height / 2, existingLen: 0, placeholderClick: true};
                            }
                        }
                    }
                    return null;
                })()""",
            )
            if box_pos:
                break
            time.sleep(0.6)

        if not box_pos:
            shot_err = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
            if shot_err.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot_err["data"]))
            return {"ok": False, "loi": "Chưa tìm thấy ô nhập bài viết trên trang Tạo bài viết.", "anh_chup": screenshot_path}

        cdp_click_coords(cdp, sid, box_pos["x"], box_pos["y"])
        time.sleep(0.5)

        # Đảm bảo con trỏ nằm đúng bên trong trình soạn thảo Lexical
        eval_js(
            cdp,
            sid,
            """(() => {
                const box = document.querySelector('[contenteditable="true"][role="textbox"], [contenteditable="true"]');
                if (box) {
                    box.focus();
                    const sel = window.getSelection();
                    if (sel && sel.rangeCount === 0) {
                        const range = document.createRange();
                        range.selectNodeContents(box);
                        range.collapse(false);
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                }
            })()""",
        )
        time.sleep(0.2)

        # Nếu ô nhập có sẵn chữ nháp cũ, xóa sạch để tránh trùng lặp
        if box_pos.get("existingLen", 0) > 0:
            clear_editor_with_keys(cdp, sid)

        # Điền nội dung bài viết từng dòng để trình soạn thảo Lexical của Facebook nhận diện link preview
        lines = message.split("\n")
        for idx, line in enumerate(lines):
            if line:
                cdp.call("Input.insertText", {"text": line}, session_id=sid)
            if idx < len(lines) - 1:
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyDown",
                        "key": "Enter",
                        "code": "Enter",
                        "windowsVirtualKeyCode": 13,
                        "nativeVirtualKeyCode": 13,
                        "text": "\r",
                        "unmodifiedText": "\r",
                    },
                    session_id=sid,
                )
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyUp",
                        "key": "Enter",
                        "code": "Enter",
                        "windowsVirtualKeyCode": 13,
                        "nativeVirtualKeyCode": 13,
                    },
                    session_id=sid,
                )
            time.sleep(0.08)

        # Gõ thêm dấu cách cuối link để kích hoạt tải thẻ preview ảnh og:image của kiemtien.deta.vn
        cdp.call("Input.insertText", {"text": " "}, session_id=sid)
        time.sleep(0.5)

        # Kiểm tra chắc chắn nội dung đã vào trình soạn thảo Lexical; nếu chưa thì dùng sự kiện Paste dự phòng
        typed_text = eval_js(
            cdp,
            sid,
            """(() => {
                const box = document.querySelector('[contenteditable="true"][role="textbox"], [contenteditable="true"]');
                return box ? (box.innerText || '') : '';
            })()""",
        ) or ""

        if "kiemtien.deta.vn" not in typed_text:
            clear_editor_with_keys(cdp, sid)
            eval_js(
                cdp,
                sid,
                f"""(() => {{
                    const box = document.querySelector('[contenteditable="true"][role="textbox"], [contenteditable="true"]');
                    if (!box) return false;
                    box.focus();
                    const dt = new DataTransfer();
                    dt.setData('text/plain', {json.dumps(message + " ", ensure_ascii=False)});
                    const ev = new ClipboardEvent('paste', {{bubbles: true, cancelable: true, clipboardData: dt}});
                    box.dispatchEvent(ev);
                    return true;
                }})()""",
            )
            time.sleep(0.5)
            cdp.call("Input.insertText", {"text": " "}, session_id=sid)
            typed_text = eval_js(
                cdp,
                sid,
                """(() => {
                    const box = document.querySelector('[contenteditable="true"][role="textbox"], [contenteditable="true"]');
                    return box ? (box.innerText || '') : '';
                })()""",
            ) or ""

        # Chờ thẻ xem trước OpenGraph (og:image / tiêu đề Tôi là AI) tải xong ở khung Bản xem trước bên phải
        preview_loaded = False
        for sec in range(11):
            time.sleep(1.0)
            preview_loaded = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const txt = document.body ? (document.body.innerText || '') : '';
                        return /Tôi là AI|DETA\\.VN/i.test(txt);
                    })()""",
                )
            )
            if preview_loaded and sec >= 4:
                break

        # Chụp ảnh màn hình khung soạn thảo kèm bản xem trước trước khi bấm Đăng
        shot = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot.get("data"):
            with open("/tmp/fb-preview.png", "wb") as f:
                f.write(base64.b64decode(shot["data"]))

        if not publish:
            return {
                "ok": True,
                "trang_thai": "da_dien_san",
                "do_dai_chu": len(typed_text.strip()),
                "preview_og": preview_loaded,
                "anh_xem_truoc": "/tmp/fb-preview.png",
                "ghi_chu": "Đã mở Facebook và điền sẵn toàn bộ bài viết + thẻ xem trước kiemtien.deta.vn. Chờ bấm nút Đăng.",
            }

        # Tìm tọa độ nút Đăng / Post đang bật
        find_post_btn_js = """(() => {
            const btns = Array.from(document.querySelectorAll('[role="button"], button'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').trim();
                const txt = (b.innerText || '').trim();
                const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                if (!disabled && (/^(đăng|post)$/i.test(aria) || /^(đăng|post)$/i.test(txt))) {
                    b.scrollIntoView({block: 'nearest'});
                    const r = b.getBoundingClientRect();
                    if (r.width > 20 && r.height > 15) {
                        return {x: r.left + r.width / 2, y: r.top + r.height / 2, label: aria || txt, isNext: false};
                    }
                }
            }
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').trim();
                const txt = (b.innerText || '').trim();
                const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                if (!disabled && (/^(tiếp|next)$/i.test(aria) || /^(tiếp|next)$/i.test(txt))) {
                    b.scrollIntoView({block: 'nearest'});
                    const r = b.getBoundingClientRect();
                    if (r.width > 20 && r.height > 15) {
                        return {x: r.left + r.width / 2, y: r.top + r.height / 2, label: aria || txt, isNext: true};
                    }
                }
            }
            return null;
        })()"""

        post_pos = None
        for _ in range(10):
            post_pos = eval_js(cdp, sid, find_post_btn_js)
            if post_pos:
                break
            time.sleep(0.6)

        if not post_pos:
            return {
                "ok": False,
                "loi": "Đã điền bài viết nhưng chưa thấy nút Đăng bật sáng (anh có thể bấm nút Đăng trên màn hình).",
                "do_dai_chu": len(typed_text.strip()),
                "anh_xem_truoc": "/tmp/fb-preview.png",
            }

        cdp_click_coords(cdp, sid, post_pos["x"], post_pos["y"])

        # Nếu Facebook dùng giao diện 2 bước (Tiếp -> Đăng), bấm thêm nút Đăng ở bước 2
        if post_pos.get("isNext"):
            time.sleep(2.0)
            step2_pos = eval_js(cdp, sid, find_post_btn_js)
            if step2_pos:
                cdp_click_coords(cdp, sid, step2_pos["x"], step2_pos["y"])

        # Chờ quá trình gửi bài hoàn tất (rời trang /post/create hoặc nút Đăng chuyển trạng thái)
        submitted = False
        for attempt in range(16):
            time.sleep(1.0)
            state = eval_js(
                cdp,
                sid,
                """(() => {
                    const url = location.href || '';
                    const box = document.querySelector('[contenteditable="true"][role="textbox"], [contenteditable="true"]');
                    const btns = Array.from(document.querySelectorAll('[role="button"], button'));
                    let postBtnEnabled = false;
                    for (const b of btns) {
                        const lbl = (b.getAttribute('aria-label') || b.innerText || '').trim();
                        if (/^(đăng|post)$/i.test(lbl) && b.getAttribute('aria-disabled') !== 'true' && !b.disabled) {
                            postBtnEnabled = true;
                        }
                    }
                    return {
                        url,
                        leftCreatePage: !url.includes('/post/create'),
                        hasBox: Boolean(box),
                        postBtnEnabled
                    };
                })()""",
            ) or {}
            if state.get("leftCreatePage") or not state.get("hasBox"):
                submitted = True
                break
            # Nếu sau 3 giây vẫn ở trang cũ và nút Đăng vẫn còn nguyên chưa bấm ăn, thử click lần 2
            if attempt == 3 and state.get("postBtnEnabled"):
                retry_pos = eval_js(cdp, sid, find_post_btn_js)
                if retry_pos:
                    cdp_click_coords(cdp, sid, retry_pos["x"], retry_pos["y"])

        time.sleep(2.5)
        final_url = eval_js(cdp, sid, "location.href") or ""
        shot2 = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot2.get("data"):
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(shot2["data"]))

        return {
            "ok": True,
            "trang_thai": "da_dang" if (submitted or "/post/create" not in final_url) else "da_bam_dang",
            "url_cuoi": final_url,
            "do_dai_chu": len(typed_text.strip()),
            "preview_og": preview_loaded,
            "anh_xem_truoc": "/tmp/fb-preview.png",
            "anh_chup": screenshot_path,
            "ghi_chu": "Đã đăng bài thành công lên Facebook cá nhân!",
        }
    finally:
        cdp.close()


def post_to_facebook_group(
    group_query: str,
    message: str,
    publish: bool = False,
    screenshot_path: str = "/tmp/fb-group-step.png",
) -> dict:
    """Tìm nhóm Facebook (vd: 'Nghiện AI') trên trình duyệt đang đăng nhập, mở khung viết bài và đăng."""
    host, port, ws_path = discover_chrome_endpoint()
    cdp = SimpleCDPClient(host, port, ws_path)
    try:
        targets = cdp.call("Target.getTargets").get("targetInfos", [])
        fb_pages = [
            t for t in targets
            if t.get("type") == "page" and "facebook.com" in t.get("url", "")
        ]
        if fb_pages:
            target_id = fb_pages[0]["targetId"]
        else:
            target = cdp.call("Target.createTarget", {"url": "https://www.facebook.com/"})
            target_id = target["targetId"]
            time.sleep(4)

        cdp.call("Target.activateTarget", {"targetId": target_id})
        attach = cdp.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        sid = attach["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        time.sleep(1.2)

        q_json = json.dumps(group_query, ensure_ascii=False)
        find_group_link_js = f"""(() => {{
            const kw = ({q_json}).toLowerCase();
            const links = Array.from(document.querySelectorAll('a[href*="/groups/"]'));
            for (const a of links) {{
                const href = a.href || '';
                if (/\\/groups\\/(feed|discover|joins|search|create)\\b/i.test(href)) continue;
                const txt = ((a.innerText || '') + ' ' + (a.getAttribute('aria-label') || '')).toLowerCase();
                if (txt.includes(kw)) {{
                    return href.split('?')[0];
                }}
            }}
            return '';
        }})()"""

        cur_url = eval_js(cdp, sid, "location.href") or ""
        cur_title = eval_js(cdp, sid, "document.title") or ""
        group_url = ""
        if "/groups/" in cur_url and group_query.lower() in cur_title.lower():
            group_url = cur_url
        else:
            group_url = eval_js(cdp, sid, find_group_link_js) or ""
            if not group_url:
                cdp.call("Page.navigate", {"url": "https://www.facebook.com/groups/joins/"}, session_id=sid)
                time.sleep(4.5)
                group_url = eval_js(cdp, sid, find_group_link_js) or ""
            if not group_url:
                import urllib.parse
                enc_q = urllib.parse.quote(group_query)
                cdp.call("Page.navigate", {"url": f"https://www.facebook.com/search/groups/?q={enc_q}"}, session_id=sid)
                time.sleep(4.5)
                group_url = eval_js(cdp, sid, find_group_link_js) or ""

        if not group_url:
            shot_err = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
            if shot_err.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot_err["data"]))
            return {"ok": False, "loi": f"Không tìm thấy nhóm '{group_query}' trong danh sách nhóm của anh.", "anh_chup": screenshot_path}

        if group_url not in (eval_js(cdp, sid, "location.href") or ""):
            cdp.call("Page.navigate", {"url": group_url}, session_id=sid)
            time.sleep(5.0)

        # Tìm ô mở hộp thoại "Bạn viết gì đi..." trên trang Nhóm
        trigger_pos = None
        for _ in range(15):
            trigger_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const cands = Array.from(document.querySelectorAll('[role="main"] [role="button"], [role="button"], span'));
                    for (const el of cands) {
                        const txt = ((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '')).trim();
                        if (/Bạn viết gì đi|Viết gì đó|nghĩ gì thế|Write something|Tạo bài viết công khai/i.test(txt) && !/bình luận|comment/i.test(txt)) {
                            el.scrollIntoView({block: 'center'});
                            const r = el.getBoundingClientRect();
                            if (r.width > 60 && r.height >= 14) {
                                return {x: r.left + Math.min(120, r.width / 3), y: r.top + r.height / 2, label: txt.slice(0, 50)};
                            }
                        }
                    }
                    return null;
                })()""",
            )
            if trigger_pos:
                break
            time.sleep(0.6)

        if not trigger_pos:
            shot_err = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
            if shot_err.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot_err["data"]))
            return {"ok": False, "loi": "Đã vào nhóm nhưng chưa tìm thấy ô 'Bạn viết gì đi...'.", "group_url": group_url, "anh_chup": screenshot_path}

        time.sleep(0.3)
        cdp_click_coords(cdp, sid, trigger_pos["x"], trigger_pos["y"])
        time.sleep(1.5)

        # Tìm ô soạn thảo Lexical bên trong hộp thoại Tạo bài viết nhóm (loại trừ ô bình luận)
        find_box_js = """(() => {
            const scopes = [
                '[role="dialog"] [contenteditable="true"][role="textbox"]',
                '[role="dialog"] [contenteditable="true"]',
                '[contenteditable="true"][role="textbox"]'
            ];
            for (const sel of scopes) {
                const boxes = Array.from(document.querySelectorAll(sel));
                for (const box of boxes) {
                    const aria = ((box.getAttribute('aria-label') || '') + ' ' + (box.getAttribute('aria-placeholder') || '')).toLowerCase();
                    if (/bình luận|comment|trả lời|reply/i.test(aria)) continue;
                    box.scrollIntoView({block: 'nearest'});
                    const r = box.getBoundingClientRect();
                    const pr = box.parentElement ? box.parentElement.getBoundingClientRect() : r;
                    const w = Math.max(r.width, pr.width);
                    const h = Math.max(r.height, pr.height);
                    const left = r.width > 10 ? r.left : pr.left;
                    const top = r.width > 10 ? r.top : pr.top;
                    if (w > 40 && h >= 8) {
                        box.focus();
                        return {
                            x: left + Math.min(80, Math.max(20, w / 4)),
                            y: top + Math.min(20, Math.max(8, (r.height > 6 ? r.height : h) / 2)),
                            existingLen: (box.innerText || '').trim().length
                        };
                    }
                }
            }
            return null;
        })()"""

        box_pos = None
        for _ in range(22):
            box_pos = eval_js(cdp, sid, find_box_js)
            if box_pos:
                break
            time.sleep(0.6)

        if not box_pos:
            shot_err = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
            if shot_err.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot_err["data"]))
            return {"ok": False, "loi": "Chưa mở được hộp thoại nhập bài viết trong nhóm.", "group_url": group_url, "anh_chup": screenshot_path}

        cdp_click_coords(cdp, sid, box_pos["x"], box_pos["y"])
        time.sleep(0.5)

        if box_pos.get("existingLen", 0) > 0:
            clear_editor_with_keys(cdp, sid)

        # Bước 1: Gõ link kiemtien.deta.vn trước để khóa thẻ ảnh preview Deta AI Lab v2 (tránh bị link copee.vn chiếm thẻ preview)
        cdp.call("Input.insertText", {"text": "https://kiemtien.deta.vn/?nguon=nghien-ai "}, session_id=sid)
        preview_loaded = False
        for sec in range(9):
            time.sleep(1.0)
            preview_loaded = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const dlg = document.querySelector('[role="dialog"]') || document.body;
                        const txt = dlg ? (dlg.innerText || '') : '';
                        return /Tôi là AI|DETA\\.VN/i.test(txt);
                    })()""",
                )
            )
            if preview_loaded and sec >= 3:
                break

        # Bước 2: Xóa dòng link mồi (thẻ preview Deta AI Lab vẫn giữ nguyên trong hộp thoại) rồi điền toàn bộ bài viết hoàn chỉnh
        clear_editor_with_keys(cdp, sid)
        time.sleep(0.25)

        lines = message.split("\n")
        for idx, line in enumerate(lines):
            if line:
                cdp.call("Input.insertText", {"text": line}, session_id=sid)
            if idx < len(lines) - 1:
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyDown",
                        "key": "Enter",
                        "code": "Enter",
                        "windowsVirtualKeyCode": 13,
                        "nativeVirtualKeyCode": 13,
                        "text": "\r",
                        "unmodifiedText": "\r",
                    },
                    session_id=sid,
                )
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyUp",
                        "key": "Enter",
                        "code": "Enter",
                        "windowsVirtualKeyCode": 13,
                        "nativeVirtualKeyCode": 13,
                    },
                    session_id=sid,
                )
            time.sleep(0.07)

        cdp.call("Input.insertText", {"text": " "}, session_id=sid)
        time.sleep(1.0)

        read_box_js = """(() => {
            const boxes = Array.from(document.querySelectorAll('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]'));
            for (const b of boxes) {
                const aria = ((b.getAttribute('aria-label') || '') + ' ' + (b.getAttribute('aria-placeholder') || '')).toLowerCase();
                if (!/bình luận|comment/i.test(aria)) return b.innerText || '';
            }
            return '';
        })()"""

        typed_text = eval_js(cdp, sid, read_box_js) or ""
        if "kiemtien.deta.vn" not in typed_text:
            clear_editor_with_keys(cdp, sid)
            eval_js(
                cdp,
                sid,
                f"""(() => {{
                    const boxes = Array.from(document.querySelectorAll('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]'));
                    const box = boxes.find(b => !/bình luận|comment/i.test((b.getAttribute('aria-label') || '')));
                    if (!box) return false;
                    box.focus();
                    const dt = new DataTransfer();
                    dt.setData('text/plain', {json.dumps(message + " ", ensure_ascii=False)});
                    box.dispatchEvent(new ClipboardEvent('paste', {{bubbles: true, cancelable: true, clipboardData: dt}}));
                    return true;
                }})()""",
            )
            time.sleep(1.0)
            typed_text = eval_js(cdp, sid, read_box_js) or ""

        time.sleep(3.0)
        shot_pre = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_pre.get("data"):
            with open("/tmp/fb-group-preview.png", "wb") as f:
                f.write(base64.b64decode(shot_pre["data"]))

        if not publish:
            return {
                "ok": True,
                "trang_thai": "da_dien_san_nhom",
                "group_url": group_url,
                "do_dai_chu": len(typed_text.strip()),
                "preview_og": preview_loaded,
                "anh_xem_truoc": "/tmp/fb-group-preview.png",
            }

        find_submit_js = """(() => {
            const root = document.querySelector('[role="dialog"]') || document;
            const btns = Array.from(root.querySelectorAll('[role="button"], button'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').trim();
                const txt = (b.innerText || '').trim();
                const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                if (!disabled && (/^(đăng|gửi|post|submit)$/i.test(aria) || /^(đăng|gửi|post|submit)$/i.test(txt))) {
                    b.scrollIntoView({block: 'nearest'});
                    const r = b.getBoundingClientRect();
                    if (r.width > 20 && r.height > 15) {
                        return {x: r.left + r.width / 2, y: r.top + r.height / 2, label: aria || txt};
                    }
                }
            }
            return null;
        })()"""

        post_pos = None
        for _ in range(10):
            post_pos = eval_js(cdp, sid, find_submit_js)
            if post_pos:
                break
            time.sleep(0.6)

        if not post_pos:
            return {
                "ok": False,
                "loi": "Đã điền bài viết vào nhóm nhưng chưa thấy nút Đăng/Gửi bật sáng (anh kiểm tra trên màn hình nhé).",
                "group_url": group_url,
                "anh_xem_truoc": "/tmp/fb-group-preview.png",
            }

        cdp_click_coords(cdp, sid, post_pos["x"], post_pos["y"])

        submitted = False
        for attempt in range(16):
            time.sleep(1.0)
            dlg_open = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const boxes = Array.from(document.querySelectorAll('[role="dialog"] [contenteditable="true"]'));
                        return boxes.some(b => !/bình luận|comment/i.test((b.getAttribute('aria-label') || '')));
                    })()""",
                )
            )
            if not dlg_open:
                submitted = True
                break
            if attempt == 3:
                retry_pos = eval_js(cdp, sid, find_submit_js)
                if retry_pos:
                    cdp_click_coords(cdp, sid, retry_pos["x"], retry_pos["y"])

        time.sleep(3.0)
        shot_done = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_done.get("data"):
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(shot_done["data"]))

        return {
            "ok": True,
            "trang_thai": "da_dang_nhom" if submitted else "da_bam_dang_nhom",
            "group_url": group_url,
            "do_dai_chu": len(typed_text.strip()),
            "preview_og": preview_loaded,
            "anh_xem_truoc": "/tmp/fb-group-preview.png",
            "anh_chup": screenshot_path,
        }
    finally:
        cdp.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đăng bài lên Facebook cá nhân hoặc Nhóm qua Chrome đang mở")
    parser.add_argument("--group", default="", help="Tên nhóm Facebook cần đăng (vd: 'Nghiện AI'). Để trống = đăng tường cá nhân")
    parser.add_argument("--message", default="", help="Nội dung bài đăng")
    parser.add_argument("--publish", action="store_true", help="Tự động bấm nút Đăng luôn (mặc định chỉ điền sẵn)")
    parser.add_argument("--screenshot", default="/tmp/fb-step.png", help="Đường dẫn ảnh chụp màn hình")
    args = parser.parse_args()

    try:
        if args.group:
            msg = args.message or NGHIEN_AI_POST_DAY_1
            result = post_to_facebook_group(args.group, msg, publish=args.publish, screenshot_path=args.screenshot)
        else:
            msg = args.message or DEFAULT_POST_DAY_1
            result = post_to_facebook(msg, publish=args.publish, screenshot_path=args.screenshot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("ok") else 1)
    except Exception as exc:
        print(json.dumps({"ok": False, "loi": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
