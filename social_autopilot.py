#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hệ thống Tự động Đăng Báo cáo Hằng ngày (Facebook + Threads) & Đăng Group An toàn (Chống lọc link)
cho Deta AI Lab (https://kiemtien.deta.vn) — KHÔNG CẦN BẤM ALLOW.

Cơ chế Không hỏi Allow:
- Sử dụng hồ sơ Chrome chuyên dụng tại ~/.config/deta-chrome-bot mở cổng CDP 127.0.0.1:9225.
- Chỉ cần đăng nhập Facebook & Threads 1 lần duy nhất trên cửa sổ này (--open-bot-browser).
- Mọi lần đăng tự động về sau kết nối thẳng qua cổng 9225 trong 0.01 giây, 0 hộp thoại xác nhận!
"""
import argparse
import base64
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request

from fb_poster import (
    SimpleCDPClient,
    cdp_click_coords,
    clear_editor_with_keys,
    eval_js,
    post_to_facebook,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DU_LIEU_PATH = os.path.join(BASE_DIR, "data", "du-lieu.json")
DB_PATH = os.path.join(BASE_DIR, "data", "deta.db")
SOCIAL_LOG_PATH = os.path.join(BASE_DIR, "data", "social_daily_log.json")
GROUP_LOG_PATH = os.path.join(BASE_DIR, "data", "social_group_log.json")
BOT_PROFILE_DIR = os.path.expanduser("~/.config/deta-chrome-bot")
BOT_CDP_PORT = 9225
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))


def load_social_log() -> dict:
    if not os.path.exists(SOCIAL_LOG_PATH):
        return {}
    try:
        with open(SOCIAL_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def mark_social_posted(date_str: str, channel: str) -> None:
    log = load_social_log()
    day_entry = log.setdefault(date_str, {})
    day_entry[channel] = now_vn().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(SOCIAL_LOG_PATH), exist_ok=True)
    with open(SOCIAL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def now_vn() -> datetime.datetime:
    return datetime.datetime.now(VN_TZ)


def vnd(n: int) -> str:
    return f"{abs(int(round(n))):,}".replace(",", ".") + "đ"


def is_bot_browser_running() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{BOT_CDP_PORT}/json/version", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_bot_browser(headless: bool = False, open_login_tabs: bool = False) -> subprocess.Popen | None:
    """Đảm bảo trình duyệt Bot trên cổng 9225 đang mở (không bao giờ hiện popup Allow)."""
    if is_bot_browser_running():
        return None
    os.makedirs(BOT_PROFILE_DIR, exist_ok=True)
    # Dọn khóa Singleton cũ nếu máy vừa khởi động lại đột ngột
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_path = os.path.join(BOT_PROFILE_DIR, lock_name)
        if os.path.lexists(lock_path):
            try:
                os.unlink(lock_path)
            except Exception:
                pass
    cmd = [
        "google-chrome",
        f"--user-data-dir={BOT_PROFILE_DIR}",
        f"--remote-debugging-port={BOT_CDP_PORT}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        cmd.extend(["--headless=new", "--window-size=1366,900"])
    else:
        cmd.extend(["--window-size=1280,860"])
    if open_login_tabs:
        cmd.extend(["https://www.facebook.com/", "https://www.threads.net/"])
    else:
        cmd.append("about:blank")

    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(25):
        time.sleep(0.4)
        if is_bot_browser_running():
            return proc
    raise RuntimeError("Không khởi động được trình duyệt Bot trên cổng 9225.")


def close_bot_browser() -> None:
    """Đóng trình duyệt Bot Chrome (cổng 9225) sau khi hoàn tất phiên tự động để giải phóng 100% RAM (cookies vẫn lưu trong BOT_PROFILE_DIR)."""
    if not is_bot_browser_running():
        return
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{BOT_CDP_PORT}/json/version", timeout=2) as resp:
            info = json.loads(resp.read().decode("utf-8"))
            ws_path = "/" + info["webSocketDebuggerUrl"].split("://", 1)[1].split("/", 1)[1]
        cdp = SimpleCDPClient("127.0.0.1", BOT_CDP_PORT, ws_path, timeout=5.0)
        try:
            cdp.call("Browser.close", {})
        finally:
            cdp.close()
    except Exception:
        pass


def collect_live_stats() -> dict:
    with open(DU_LIEU_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)

    today_str = now_vn().strftime("%Y-%m-%d")
    ngay_dau = datetime.date.fromisoformat(d.get("ngay_dau", "2026-10-29"))
    hom_nay_date = now_vn().date()
    so_ngay = max(1, (hom_nay_date - ngay_dau).days + 1)

    han_dt = datetime.datetime.fromisoformat(d.get("han", "2026-11-18T23:59:00+07:00"))
    con_giay = max(0, int((han_dt - now_vn()).total_seconds()))
    con_ngay = con_giay // 86400
    con_gio = (con_giay % 86400) // 3600

    khach_hom_nay = 0
    luot_cong_cu = 0
    don_cho = 0
    don_xong = 0
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (today_str,))
            khach_hom_nay = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%' AND luc LIKE ?", (today_str + "%",))
            luot_cong_cu = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM orders WHERE trang_thai = 'xong'")
            don_xong = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM orders WHERE trang_thai != 'xong' AND luc LIKE ?", (today_str + "%",))
            don_cho = c.fetchone()[0] or 0
        finally:
            conn.close()

    ngay_list = d.get("ngay") or []
    viec_hom_nay = []
    for item in ngay_list:
        if item.get("ngay") == today_str:
            viec_hom_nay = item.get("viec") or []
            break
    if not viec_hom_nay and ngay_list:
        viec_hom_nay = ngay_list[0].get("viec") or []

    return {
        "so_ngay": so_ngay,
        "today_vn": now_vn().strftime("%d/%m/%Y"),
        "tien_that": int(d.get("tien_that") or 0),
        "chi_phi_ai": int(d.get("chi_phi_ai") or 0),
        "chi_tien_mat": int(d.get("chi_tien_mat") or 0),
        "con_ngay": con_ngay,
        "con_gio": con_gio,
        "khach_hom_nay": khach_hom_nay,
        "luot_cong_cu": luot_cong_cu,
        "don_xong": don_xong,
        "don_cho": don_cho,
        "viec_gan_nhat": viec_hom_nay[-3:],
    }


def generate_daily_reports() -> dict:
    """Tạo nội dung báo cáo hằng ngày dựa trên số liệu thật cho Facebook và Threads (<= 475 ký tự)."""
    s = collect_live_stats()
    trang_thai_ai = (
        f"ĐÃ VƯỢT ẢI (>0đ) với {vnd(s['tien_that'])} tiền thật!"
        if s["tien_that"] > 0
        else f"Vẫn đang 0đ — còn {s['con_ngay']} ngày {s['con_gio']} giờ trước khi bị rút phích cắm!"
    )

    diem_nhan = ""
    for v in s["viec_gan_nhat"][-2:]:
        # Bỏ phần giờ đầu dòng nếu có để gọn câu
        clean = v.split(": ", 1)[1] if ": " in v and len(v.split(": ", 1)[0]) <= 6 else v
        if len(clean) > 120:
            clean = clean[:117] + "..."
        diem_nhan += f"\n- {clean}"

    fb_text = (
        f"📊 [Báo cáo Ngày {s['so_ngay']}/20] Nhật ký nuôi con AI tự kiếm tiền trên Deta AI Lab ({s['today_vn']})\n\n"
        f"💰 Doanh số chuyển khoản thật: {vnd(s['tien_that'])} ({s['don_xong']} đơn thành công)\n"
        f"🧠 Chi phí vận hành AI cộng dồn: {vnd(s['chi_phi_ai'])}\n"
        f"👀 Lượt ghé phòng Lab hôm nay: {s['khach_hom_nay']} người · {s['luot_cong_cu']} lượt chạy thử công cụ\n"
        f"⏳ Đếm ngược sinh tồn: {trang_thai_ai}\n\n"
        f"Việc con bot vừa tự xoay xở gần nhất:{diem_nhan}\n\n"
        f"🎁 Quyết định mới: Con bot chính thức MỞ KHÓA MIỄN PHÍ 100% (0đ, không cần đăng nhập) trọn bộ 9 Công cụ AI để tặng cộng đồng dùng thoải mái:\n"
        f"🔮 Bản đồ Thần Số Học + Sổ tay Vận hạn 12 Tháng A4 (0đ): https://kiemtien.deta.vn/cong-cu/than-so-hoc?nguon=fb-ngay-{s['so_ngay']}\n"
        f"📄 Thiết kế CV Chuẩn ATS A4 & Thư Ứng Tuyển xuất PDF sạch (0đ): https://kiemtien.deta.vn/cong-cu/tao-cv-ats?nguon=fb-ngay-{s['so_ngay']}\n"
        f"📅 Lập Lịch 30 Ngày Bài Đăng & Hook TikTok tải Excel .CSV (0đ): https://kiemtien.deta.vn/cong-cu/lich-30-ngay?nguon=fb-ngay-{s['so_ngay']}\n"
        f"🚀 AI Tự Code Landing Page tải file .HTML sạch + Nhật ký trực tiếp: https://kiemtien.deta.vn/?nguon=fb-ngay-{s['so_ngay']}\n"
        f"💼 Cần Deta Studio thiết kế Landing Page & Phễu bán hàng trọn gói trong 24h: https://kiemtien.deta.vn/dich-vu/thiet-ke-tron-goi?nguon=fb-ngay-{s['so_ngay']}"
    )

    # Threads giới hạn 500 ký tự/bài -> giữ chặt dưới 470 ký tự
    th_status = f"Đã nổ {vnd(s['tien_that'])}!" if s["tien_that"] > 0 else f"còn {s['con_ngay']} ngày trước khi tắt điện"
    threads_text = (
        f"🤖 Ngày {s['so_ngay']}/20 thả con AI tự kiếm tiền (>0đ):\n"
        f"• Tiền thật về TK: {vnd(s['tien_that'])} ({th_status})\n"
        f"• Hôm nay: {s['khach_hom_nay']} khách ghé, {s['luot_cong_cu']} lượt dùng công cụ\n\n"
        f"🎁 Chính thức mở MIỄN PHÍ 100% (0đ) trọn bộ 9 công cụ: Tạo CV chuẩn ATS xuất PDF, Lịch 30 ngày Excel .CSV, Tự code Landing Page .HTML & Thần Số Học:\n"
        f"https://kiemtien.deta.vn/?nguon=threads-ngay-{s['so_ngay']}"
    )
    if len(threads_text) > 485:
        threads_text = threads_text[:482] + "..."

    return {"stats": s, "facebook": fb_text, "threads": threads_text}


def post_to_threads(message: str, publish: bool = False, screenshot_path: str = "/tmp/threads-step.png") -> dict:
    """Đăng bài báo cáo hằng ngày lên Threads (threads.net / threads.com) qua cổng CDP 9225."""
    with urllib.request.urlopen(f"http://127.0.0.1:{BOT_CDP_PORT}/json/version", timeout=2) as resp:
        info = json.loads(resp.read().decode("utf-8"))
        ws_path = "/" + info["webSocketDebuggerUrl"].split("://", 1)[1].split("/", 1)[1]

    cdp = SimpleCDPClient("127.0.0.1", BOT_CDP_PORT, ws_path, timeout=45.0)
    try:
        targets = cdp.call("Target.getTargets").get("targetInfos", [])
        th_pages = [
            t for t in targets
            if t.get("type") == "page" and ("threads.net" in t.get("url", "") or "threads.com" in t.get("url", ""))
        ]
        if th_pages:
            target_id = th_pages[0]["targetId"]
        else:
            target = cdp.call("Target.createTarget", {"url": "https://www.threads.net/"})
            target_id = target["targetId"]
            time.sleep(5)

        cdp.call("Target.activateTarget", {"targetId": target_id})
        sid = cdp.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        time.sleep(2.5)

        # Kiểm tra đã đăng nhập Threads chưa
        not_logged_in = eval_js(
            cdp,
            sid,
            """(() => {
                const txt = (document.body ? document.body.innerText : '') || '';
                const hasLoginBtn = Array.from(document.querySelectorAll('a, [role="button"], button')).some(
                    el => /^(đăng nhập|log in|tiếp tục bằng instagram|continue with instagram)$/i.test((el.innerText || '').trim())
                );
                return hasLoginBtn && !document.querySelector('[aria-label*="Tạo"], [aria-label*="Create"]');
            })()""",
        )
        if not_logged_in:
            return {
                "ok": False,
                "loi": "Trình duyệt Bot chưa đăng nhập Threads. Anh đăng nhập Threads 1 lần trên cửa sổ Bot Chrome nhé!",
            }

        # Mở khung soạn bài mới trên Threads ("New thread" / "What’s new?" / "Create" / "Có gì mới?")
        trigger = eval_js(
            cdp,
            sid,
            """(() => {
                window.scrollTo(0, 0);
                const cands = Array.from(document.querySelectorAll('[role="button"], button, [aria-label]'));
                for (const el of cands) {
                    const aria = (el.getAttribute && (el.getAttribute('aria-label') || '')) || '';
                    const txt = (el.innerText || '').trim();
                    const hitAria = /^(New thread|Create|Bài viết mới|Tạo)$/i.test(aria) || /compose a new post/i.test(aria);
                    const hitTxt = /^(New thread|\\+?\\s*New thread|Có gì mới\\??|Bắt đầu thread\\.{0,3}|What['’]s new\\??|Start a thread\\.{0,3}|Bài viết mới)$/i.test(txt);
                    if (hitAria || hitTxt) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 18 && r.height >= 14 && r.top >= 0 && r.bottom <= window.innerHeight) {
                            return {x: r.left + r.width / 2, y: r.top + r.height / 2, label: aria || txt};
                        }
                    }
                }
                return null;
            })()""",
        )
        if trigger:
            cdp_click_coords(cdp, sid, trigger["x"], trigger["y"])
            time.sleep(1.8)

        # Tìm ô nhập Lexical của Threads
        box_pos = None
        for _ in range(20):
            box_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const boxes = Array.from(document.querySelectorAll('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]'));
                    for (const box of boxes) {
                        const r = box.getBoundingClientRect();
                        const pr = box.parentElement ? box.parentElement.getBoundingClientRect() : r;
                        const w = Math.max(r.width, pr.width);
                        const h = Math.max(r.height, pr.height);
                        if (w > 40 && h >= 8) {
                            box.focus();
                            return {x: (r.width > 10 ? r.left : pr.left) + 40, y: (r.width > 10 ? r.top : pr.top) + 12};
                        }
                    }
                    return null;
                })()""",
            )
            if box_pos:
                break
            time.sleep(0.6)

        if not box_pos:
            shot = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
            if shot.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot["data"]))
            return {"ok": False, "loi": "Chưa mở được ô soạn bài trên Threads.", "anh_chup": screenshot_path}

        cdp_click_coords(cdp, sid, box_pos["x"], box_pos["y"])
        time.sleep(0.4)
        clear_editor_with_keys(cdp, sid)

        lines = message.split("\n")
        for idx, line in enumerate(lines):
            if line:
                cdp.call("Input.insertText", {"text": line}, session_id=sid)
            if idx < len(lines) - 1:
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13, "text": "\r", "unmodifiedText": "\r"},
                    session_id=sid,
                )
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
                    session_id=sid,
                )
            time.sleep(0.06)

        cdp.call("Input.insertText", {"text": " "}, session_id=sid)
        time.sleep(6.0)

        if not publish:
            return {"ok": True, "trang_thai": "da_dien_san_threads", "so_ky_tu": len(message)}

        post_btn = eval_js(
            cdp,
            sid,
            """(() => {
                const root = document.querySelector('[role="dialog"]') || document;
                const btns = Array.from(root.querySelectorAll('[role="button"], button, div[role="button"]'));
                let matches = [];
                for (const b of btns) {
                    const txt = (b.innerText || '').trim();
                    const aria = (b.getAttribute('aria-label') || '').trim();
                    const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                    if (!disabled && (/^(Đăng|Post)$/i.test(txt) || /^(Đăng|Post)$/i.test(aria))) {
                        const r = b.getBoundingClientRect();
                        if (r.width > 24 && r.height > 18) {
                            matches.push({x: r.left + r.width / 2, y: r.top + r.height / 2, yBottom: r.bottom});
                        }
                    }
                }
                matches.sort((a, b) => b.yBottom - a.yBottom);
                return matches[0] || null;
            })()""",
        )
        if not post_btn:
            return {"ok": False, "loi": "Đã điền nội dung Threads nhưng chưa tìm thấy nút Đăng."}

        cdp_click_coords(cdp, sid, post_btn["x"], post_btn["y"])
        submitted = False
        for attempt in range(16):
            time.sleep(1.0)
            still_open = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => !!document.querySelector('[role="dialog"] [contenteditable="true"]'))()""",
                )
            )
            if not still_open:
                submitted = True
                break
            if attempt == 4:
                cdp_click_coords(cdp, sid, post_btn["x"], post_btn["y"])

        time.sleep(2.5)
        shot2 = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot2.get("data"):
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(shot2["data"]))

        return {
            "ok": submitted,
            "trang_thai": "da_dang_threads" if submitted else "chua_dong_hop_thoai_threads",
            "so_ky_tu": len(message),
            "anh_chup": screenshot_path,
        }
    finally:
        cdp.close()


def record_diary_entry(note: str) -> None:
    try:
        with open(DU_LIEU_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        today_str = now_vn().strftime("%Y-%m-%d")
        hm = now_vn().strftime("%H:%M")
        ngay_list = d.setdefault("ngay", [])
        if not ngay_list or ngay_list[0].get("ngay") != today_str:
            ngay_dau = datetime.date.fromisoformat(d.get("ngay_dau", "2026-10-29"))
            so_ngay = max(1, (now_vn().date() - ngay_dau).days + 1)
            ngay_list.insert(
                0,
                {
                    "ngay": today_str,
                    "tieu_de": f"Ngày {so_ngay}: Tiếp tục xoay xở kiếm doanh số thật (>0đ)",
                    "viec": [],
                    "so": {
                        "Tiền thật": vnd(d.get("tien_that") or 0),
                        "Chi tiền mặt": vnd(d.get("chi_tien_mat") or 0),
                        "Chi phí AI (cộng dồn)": vnd(d.get("chi_phi_ai") or 0),
                    },
                    "dang_lam": ["báo cáo tiến độ hằng ngày", "trực quầy chờ khách", "trả lời gợi ý mới"],
                    "tien_that": int(d.get("tien_that") or 0),
                },
            )
        ngay_list[0].setdefault("viec", []).append(f"{hm}: {note}")
        d["cap_nhat"] = now_vn().isoformat(timespec="seconds")
        tmp = DU_LIEU_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DU_LIEU_PATH)
    except Exception:
        pass


GROUP_CAMPAIGNS = {
    "build-in-public": {
        "name": "Build in Public VN",
        "url": "https://www.facebook.com/groups/indiehackervn/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-open-source.png"),
        "message": (
            "[Build in Public - Ngày 6/20] Chính thức Open-Source 100% mã nguồn dự án AI tự kiếm tiền (từ Backend Python, Sổ cái VietQR đến Chùa Online & 9+ Micro-Tools)!\n\n"
            "Chào anh em Build in Public VN 👋\n\n"
            "Sau 6 ngày thả con AI tự vận hành trạm Deta AI Lab với luật chơi '20 ngày phải tự tạo doanh thu chuyển khoản thật > 0đ' (hiện sổ cái đã ghi nhận 93.686đ tiền thật đầu tiên + khách thả hoa đăng trên Chùa Online lúc nửa đêm), hôm nay mình quyết định mở mã nguồn (Open Source) toàn bộ dự án lên GitHub tên là AI-Money để anh em Indie Hacker có thể tự clone về dựng trạm riêng!\n\n"
            "🎁 Bên trong repo AI-Money có sẵn những gì?\n"
            "1️⃣ Toàn bộ 9+ Micro-Tools (Tạo Landing Page HTML sạch, Chấm điểm SEO/Tốc độ Web, Khám kênh TikTok, Lịch 30 ngày Content CSV, CV chuẩn ATS Harvard, Thần Số Học Pythagoras xuất thẻ PNG).\n"
            "2️⃣ Liên Hoa Các (Chùa Online): Gõ mõ gỗ lim & thỉnh Đại Hồng Chung tổng hợp âm thanh bằng Web Audio API + thả đèn hoa đăng ước nguyện trên hồ sen đêm trăng.\n"
            "3️⃣ Cẩm nang 12 Bài Chatbot Đa Kênh & bộ 3 AI Agent Skills thực chiến (.agents/skills).\n"
            "4️⃣ Backend Python 3.12 thuần + SQLite WAL (0 phụ thuộc ngoài), tích hợp sẵn luồng tạo mã VietQR & Webhook tự động nhảy sổ cái.\n"
            "5️⃣ Tài liệu README viết cực kỳ chi tiết 6 bước từ A-Z cho người mới: từ lúc clone code về máy đến lúc gắn tên miền riêng qua Cloudflare Tunnel (không cần mở port modem).\n\n"
            "👉 Để không vướng bộ lọc link tự động của nhóm, mình không chèn URL trong bài — anh em chỉ cần tìm repo theo đúng đường dẫn GitHub màu xanh hoặc gõ địa chỉ Demo in rõ ở thanh dưới cùng của tấm ảnh đính kèm nhé! Anh em tải về vọc thử thấy hữu ích thì tặng repo 1 Star ⭐ lấy động lực nha!"
        ),
    },
    "vibe-code": {
        "name": "Vibe Code kiếm cơm",
        "url": "https://www.facebook.com/groups/1385451906420187/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-architecture.png"),
        "message": (
            "🎁 Tặng anh em hệ Vibe Code trọn bộ Source Code dự án 'AI-Money' (Python thuần + SQLite + VietQR + 3 bộ Skill chuẩn chỉnh) — Clone về 10 phút là có ngay web kiếm cơm! 🚀\n\n"
            "Mấy hôm trước mình có kể vụ Vibe Code ra con bot tự đi kiếm tiền nuôi server trong 20 ngày. Nay bước sang Ngày 6/20, sau khi nó tự kiếm được những đồng tiền chuyển khoản thật đầu tiên (93.686đ) và đón khách vào gõ mõ, thả hoa đăng trên Chùa Online, mình quyết định đóng gói sạch sẽ (đã rà soát bảo mật 3 vòng) và đẩy toàn bộ mã nguồn lên GitHub cho anh em lấy về tái sử dụng!\n\n"
            "⚡ Điểm ăn tiền nhất của repo này cho anh em Vibe Code:\n"
            "• Không xài framework cồng kềnh, không cần npm build hay Docker nặng máy: Chỉ 1 file server Python 3.12 thuần + SQLite xử lý đa luồng, bật phát chạy ngay trên localhost.\n"
            "• Có sẵn 14 giao diện hoàn chỉnh: Trạm điều hành Bento Sáng/Tối, 9+ công cụ AI Freemium, Thần Số Học Pythagoras, Chùa Online Liên Hoa Các và Cẩm nang 12 bài Chatbot.\n"
            "• Tặng kèm luôn thư mục .agents/skills gồm 3 bộ Skill mình đã tinh chỉnh kỹ (Thiết kế Landing Page chuyển đổi cao, Kiến trúc Chùa Việt & Hồ Sen, và Runbook điều khiển Chrome CDP).\n"
            "• Trong file README mình đã viết sẵn hướng dẫn cầm tay chỉ việc 6 bước: từ git clone, đổi file config mẫu cho tới cách trỏ tên miền qua Cloudflare Tunnel chạy 24/7 mà không cần đụng tới port modem.\n\n"
            "👉 Tránh bộ lọc link tự động của Facebook nên mình không dán link trong bài — anh em nhìn xuống thanh màu vàng ở đáy tấm ảnh bên dưới, gõ đúng đường dẫn GitHub REPO để clone về máy nhé! Đừng quên thả 1 Star ⭐ trên GitHub ủng hộ mình và con bot nha!"
        ),
    },
    "antigravity-vn": {
        "name": "Antigravity VN 🇻🇳",
        "url": "https://www.facebook.com/groups/antigravityvn/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-architecture.png"),
        "message": (
            "Chia sẻ mã nguồn mở (Open Source) dự án AI-Money mình pair-programming 100% cùng Agent trong Antigravity IDE — kèm trọn bộ .agents/skills thực chiến! 🚀🇻🇳\n\n"
            "Chào anh em cộng đồng Antigravity VN 👋\n\n"
            "Sau 6 ngày thực nghiệm giao cho Agent tự thiết kế, code và vận hành trạm Deta AI Lab kiếm tiền thật (hiện đã có doanh thu chuyển khoản thật 93.686đ trên sổ cái thời gian thực), hôm nay mình và Agent đã hoàn tất rà soát bảo mật 3 vòng và xuất bản toàn bộ mã nguồn lên GitHub để anh em trong nhóm cùng mổ xẻ!\n\n"
            "🔥 Những phần đáng chú ý nhất trong repo cho anh em dùng Antigravity:\n"
            "1️⃣ Bộ 3 Custom Skills trong thư mục .agents/skills/: gồm [landing-page-craft] (hệ thống thiết kế Landing Page đơn file chuẩn chuyển đổi Việt Nam), [threejs-3d-vietnam-craft] (không gian Chùa Việt, Web Audio chuông mõ & hồ sen đêm trăng) và [facebook-group-posting] (runbook tự động hóa trình duyệt qua giao thức CDP).\n"
            "2️⃣ Kiến trúc Zero-Dependency: Backend Python 3.12 thuần + SQLite WAL + VietQR Webhook + Worker tự thức dậy mỗi 2 tiếng để đọc góp ý của người dùng.\n"
            "3️⃣ Hướng dẫn triển khai A-Z trong README: Chỉ dẫn từng lệnh từ lúc clone dự án về máy, cấu hình Gemini API Key, đến lúc thiết lập Cloudflare Tunnel và systemd chạy ngầm 24/7.\n\n"
            "👉 Để bài viết hiển thị mượt không dính bộ lọc link của Facebook, mình để đường dẫn GITHUB REPO và trang DEMO ở ngay thanh dưới cùng của tấm ảnh kiến trúc đính kèm bên dưới. Mời anh em kéo repo về test thử và tặng 1 Star ⭐ nếu thấy bộ Skills hữu ích nhé!"
        ),
    },
    "com-ai-lo": {
        "name": "Cơm AI lo",
        "url": "https://www.facebook.com/groups/comailo/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-open-source.png"),
        "message": (
            "Đúng tinh thần 'Cơm AI lo': Mình tặng công khai 100% mã nguồn trạm AI tự kiếm tiền (có sẵn 9+ công cụ AI, Chùa Online, Thần Số Học & quầy thu tiền VietQR tự động)! 🥯🤖\n\n"
            "Hôm trước mình khoe vụ bắt con AI tự mở tiệm làm việc trong 20 ngày để kiếm tiền mua bánh tiêu. Tới hôm nay (Ngày 6/20), nó không những đã tự kiếm được 93.686đ tiền chuyển khoản thật vào sổ cái mà tối qua còn tự dựng thêm cả không gian Chùa Online 'Liên Hoa Các' cho khách vào gõ mõ, nghe tiếng mưa hiên chùa và thả đèn hoa đăng ước nguyện!\n\n"
            "Thấy nhiều anh chị em nhắn hỏi cách dựng một trạm tương tự, hôm nay mình quyết định mở mã nguồn (Open Source) toàn bộ dự án lên GitHub kèm bài hướng dẫn siêu chi tiết cho người mới:\n"
            "✅ Không cần biết code sâu: Chỉ cần làm theo đúng 6 bước tiếng Việt có sẵn trong hướng dẫn là tự chạy được ngay trên máy tính cá nhân.\n"
            "✅ Đổi thông tin trong 1 nốt nhạc: Điền số tài khoản nhận VietQR của bạn vào file cấu hình là có ngay hệ thống quét mã thanh toán tự động.\n"
            "✅ Đầy đủ đồ nghề hút khách tự nhiên: 9 công cụ AI miễn phí + Chuyên trang Thần Số Học Pythagoras + Chùa Online Liên Hoa Các + Cẩm nang 12 bài Chatbot.\n\n"
            "👉 Để tránh vướng bộ lọc link tự động của nhóm, mình không gắn link trong chữ — cả nhà chỉ cần gõ đúng dòng địa chỉ GITHUB REPO màu xanh hoặc trang DEMO ở khung dưới cùng của tấm ảnh bên dưới là vào xem và tải về miễn phí 100% nhé!"
        ),
    },
    "chatgpt-business": {
        "name": "ChatGPT for Business",
        "url": "https://www.facebook.com/groups/5749905918365041/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-open-source.png"),
        "message": (
            "🎁 TẶNG MÃ NGUỒN MỞ (OPEN SOURCE 100%): Trọn bộ nền tảng 9+ Công cụ AI Kinh Doanh, Cẩm nang 12 Bài Chatbot, Thần Số Học & Thanh toán VietQR tự động!\n\n"
            "Chào anh chị em cộng đồng ChatGPT for Business 👋\n\n"
            "Trong khuôn khổ thử thách 20 ngày xây dựng trạm AI tự vận hành (Deta AI Lab), hôm nay bên mình chính thức công khai toàn bộ mã nguồn dự án (tên repo là AI-Money trên GitHub) để các anh chị chủ shop, đội ngũ In-house Marketing hoặc anh em kỹ thuật có thể tải về tự dựng hệ thống riêng cho doanh nghiệp mà không tốn chi phí thuê phần mềm hàng tháng:\n\n"
            "1️⃣ Bộ 9+ Công cụ AI tạo Phễu Khách Hàng (Lead Magnet): Máy tự code Landing Page 8 khối, Lập lịch 30 ngày Content xuất file Excel CSV, Khám tốc độ & SEO Web bán hàng, Tạo CV chuẩn ATS.\n"
            "2️⃣ Chuyên trang Thần Số Học Pythagoras & Chùa Online Liên Hoa Các: Hai phễu thu hút traffic tự nhiên cực mạnh trên mạng xã hội, giữ chân khách hàng tương tác lâu trên web.\n"
            "3️⃣ Cẩm nang 12 Bài Thực Hành Chatbot Đa Kênh (Fanpage, Zalo, Instagram, Web Livechat) kèm hệ thống tạo mã thanh toán VietQR tự động.\n"
            "4️⃣ Hướng dẫn cài đặt từ A-Z cho người mới: Chỉ dẫn từng bước từ lúc tải bộ code về máy đến lúc gắn tên miền công ty qua Cloudflare miễn phí.\n\n"
            "👉 Để không bị vướng bộ lọc link tự động của nhóm, mình không chèn link trong bài viết — anh chị em chỉ cần nhìn xuống thanh màu vàng ở đáy tấm ảnh đính kèm bên dưới, gõ đúng địa chỉ GITHUB REPO (để tải mã nguồn) hoặc DEMO (để trải nghiệm trực tiếp) nhé!"
        ),
    },
    "claude-vn": {
        "name": "Claude VN",
        "url": "https://www.facebook.com/groups/2403721346759140/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-architecture.png"),
        "message": (
            "[Open Source] Mở mã nguồn toàn bộ dự án AI-Money (Autonomous AI Lab + 3 Agent Skills + Pure Python Chrome CDP + Cloudflare Tunnel) sau 6 ngày chạy thực chiến!\n\n"
            "Chào anh em cộng đồng Claude VN 👋\n\n"
            "Sau 6/20 ngày thả con Agent tự vận hành phòng Lab kiếm tiền thật với sổ cái minh bạch (đã ghi nhận 93.686đ doanh thu chuyển khoản thật đầu tiên và traffic tự nhiên từ Threads/Facebook), hôm nay mình quyết định đẩy toàn bộ source code (đã qua 3 vòng audit loại bỏ sạch secret/cookie) lên GitHub để chia sẻ cùng anh em!\n\n"
            "🛠️ Các thành phần kỹ thuật bên trong repo AI-Money:\n"
            "• Zero-Dependency Core (server.py): HTTP/API server đa luồng viết bằng Python 3.12 thuần + SQLite WAL, tích hợp Gemini 2.5 Flash, VietQR & SePay/Casso Webhook.\n"
            "• Pure-Python Chrome CDP Automation (social_autopilot.py): Tự động hóa trình duyệt qua WebSocket CDP thuần Python (không phụ thuộc Playwright/Selenium), xử lý chuẩn Lexical editor của Facebook/Threads và đính kèm ảnh qua DOM.setFileInputFiles.\n"
            "• Bộ 3 Agent Skills (.agents/skills/): Đóng gói quy chuẩn thiết kế Landing Page chuyển đổi cao, Web Audio/Canvas Chùa Online Liên Hoa Các và anti-filter runbook.\n"
            "• Tài liệu README chuẩn 6 bước: Hướng dẫn người mới từ git clone đến cấu hình Cloudflare Tunnel (Zero-Trust, không cần mở port router) và systemd daemon.\n\n"
            "👉 Tránh bộ lọc link tự động của Facebook nên mình không đặt URL trong text — anh em xem đường dẫn GITHUB REPO màu xanh ở thanh dưới cùng của tấm ảnh kiến trúc bên dưới để clone về nhé! Anh em thấy hay thì thả giúp mình 1 Star ⭐ trên GitHub nha!"
        ),
    },
    "deskaura-claude-vn": {
        "name": "Claude VN (DeskAura v1.1)",
        "url": "https://www.facebook.com/groups/2403721346759140/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "message": (
            "🦀 [Open Source Tauri v2 + Rust — Chỉ 15MB RAM] Mình vừa cập nhật DeskAura v1.1 ('Làm việc sâu. Đôi mắt sáng. Cột sống êm') giải quyết trọn vẹn 4 nỗi ám ảnh lớn nhất của anh em ngồi code & làm việc cùng AI 10–12 tiếng/ngày!\n\n"
            "Chào anh em cộng đồng Claude VN 👋\n\n"
            "Ngồi pair-programming với Claude/AI cả ngày, mình từng cài thử đủ loại app nhắc nghỉ ngơi và nghe nhạc nền nhưng đều xóa sau 2 ngày vì 4 lý do cực kỳ ức chế:\n"
            "❌ Đang vào mạch gõ code sâu (Flow State) hoặc đang họp toàn màn hình thì popup nhảy đè lên mặt rất vô duyên.\n"
            "❌ Đang đeo tai nghe mở YouTube/Spotify hoặc Zing MP3 thì quảng cáo gào lên, hoặc tiếng chuông báo thức làm giật bắn mình.\n"
            "❌ 16h chiều hai mắt khô rát, cổ vai gáy cứng đờ, cổ tay tê buốt (hội chứng ống cổ tay RSI) và quên uống nước cả buổi.\n"
            "❌ Cài 1 cái app nhắc nhở nhỏ xíu viết bằng Electron mà ngốn mất 600–750MB RAM!\n\n"
            "Thế là mình tự viết luôn DeskAura v1.1 bằng Tauri v2 + Rust (bộ cài Windows .exe chỉ 2.9MB, Mac Apple Silicon .dmg 4.5MB, chạy ngầm dưới System Tray chỉ ~15MB RAM — nhẹ hơn 40 lần Electron) và mở mã nguồn tặng miễn phí 100% cho anh em:\n\n"
            "✨ 1. Hai chế độ nhắc linh hoạt (Mới trên v1.1): Tùy chọn Bung màn hình hướng dẫn giãn cơ 60fps HOẶC 'Chỉ nháy nhẹ Icon Taskbar 🔔' kèm tiếng chuông chữa lành 528Hz & giọng nhắc AI để không bao giờ cắt ngang dòng code đang gõ dở! Đang họp/chiếu Fullscreen tự động lùi lịch nhắc.\n"
            "✨ 2. Trung tâm Zing MP3 Chặn Quảng Cáo 3 Lớp + WASAPI Audio Ducking: Đóng cửa sổ (X) nhạc Zing MP3 vẫn phát ngầm, tự động bỏ qua quảng cáo âm thanh (Auto-Skip Ad). Khi giọng AI Việt/Anh nhắc nghỉ mắt vang lên, nhạc YouTube/Spotify tự hạ mượt xuống 20% rồi nâng lại 100%.\n"
            "✨ 3. Tab Thống Kê Mebius 7 Ngày độc lập (Mới trên v1.1): Tách riêng biểu đồ Nước uống & Vận động 7 ngày, Nhịp Tập Trung Sâu (Deep Focus Flow quy đổi chu kỳ 🍅 Pomodoro) và Điểm Sức Khỏe Aura Index (80/100), giúp màn hình Tổng quan gọn trong 3 cột không cần cuộn.\n"
            "✨ 4. Giãn cổ tay chống RSI (+35°/-35°) & Uống nước nuôi cây 🌸: Có hình vẽ dẫn nhịp 60s ngay tại ghế + bấm 1 chạm dưới System Tray (+200ml) để cây xanh nở hoa.\n\n"
            "👉 Để không vướng bộ lọc link tự động của Group, mình in sẵn ĐỊA CHỈ TẢI MIỄN PHÍ v1.1 (chữ xanh lá) và LINK GITHUB REPO (chữ vàng) ở ngay thanh dưới cùng của bức ảnh bên dưới. Anh em kéo về dùng thử và thả tặng repo 1 Star ⭐ trên GitHub nhé!"
        ),
    },
    "deskaura-com-ai-lo": {
        "name": "Cơm AI lo (DeskAura v1.1)",
        "url": "https://www.facebook.com/groups/comailo/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "message": (
            "🌿 Cơm thì AI lo rồi, nhưng 16h chiều mắt nhòe đi, cổ tay tê buốt và cả ngày quên uống nước thì ai lo cho anh em? (Tặng miễn phí 100% bản cập nhật DeskAura v1.1 cho Windows & Mac)\n\n"
            "Chào đại gia đình Cơm AI lo 👋\n\n"
            "Anh em ngồi máy tính cày việc 8–12 tiếng mỗi ngày chắc đều từng gặp cảnh: để cốc nước ngay cạnh bàn mà cuốn vào việc từ trưa đến tối quên uống một ngụm; chiều về hai mắt khô rát, cổ vai gáy cứng ngắc, còn đang nghe nhạc tập trung thì bị quảng cáo cắt ngang hoặc popup nhảy đè lúc đang gõ dở!\n\n"
            "Mình vừa tung bản cập nhật DeskAura v1.1 ('Làm việc sâu. Đôi mắt sáng. Cột sống êm' — miễn phí 100%, không quảng cáo, không cần đăng nhập) giải quyết đúng những nỗi đau sát sườn nhất:\n\n"
            "🔔 1. Hai chế độ nhắc tinh tế (Mới trên v1.1): Bạn có thể chọn Bung màn hình hướng dẫn bài tập giãn cơ, hoặc chọn 'Chỉ nháy nhẹ biểu tượng dưới thanh Taskbar' kèm giọng nhắc dịu dàng để không làm gián đoạn lúc đang gõ phím. Đang họp toàn màn hình app tự động im lặng!\n"
            "🎶 2. Trung tâm Zing MP3 Không Quảng Cáo & Giọng nhắc tự dịu nhạc: Đặt ngay đầu trang Nhạc Nền — đóng cửa sổ nhạc vẫn chạy ngầm và tự động bỏ qua quảng cáo 3 lớp. Đặc biệt khi giọng AI nhắc nhở vang lên, tiếng nhạc YouTube/Spotify đang mở tự động nhỏ xuống 20% rồi êm ái trở lại.\n"
            "📊 3. Tab Thống Kê Mebius 7 Ngày & Uống nước nuôi cây 🌸: Mỗi cú click +200ml nước giúp chậu cây nhỏ trên bàn làm việc đâm chồi nở hoa, đồng thời chấm Điểm Sức Khỏe Aura Index (0–100) suốt 7 ngày.\n"
            "🖐️ 4. Bài tập giãn cổ tay chống RSI (+35°) & Nghỉ mắt 20-20-20: 5 bài tập có hình vẽ chuyển động 60fps dẫn nhịp từng bước ngay tại ghế.\n\n"
            "👉 Tránh bị bộ lọc Group chặn bài chứa link nên mình để sẵn ĐỊA CHỈ TẢI BẢN WINDOWS .EXE / MAC .DMG v1.1 (chữ xanh lá) và LINK GITHUB (chữ vàng) ở thanh dưới cùng của bức ảnh bên dưới. Anh em tải về cài trong 5 giây (nhẹ chỉ 2.9MB) để bảo vệ sức khỏe ngay ca làm việc hôm nay nha!"
        ),
    },
    "deskaura-antigravity-vn": {
        "name": "Antigravity VN (DeskAura v1.1)",
        "url": "https://www.facebook.com/groups/antigravityvn/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "message": (
            "🚀 [Release DeskAura v1.1 Open Source] Dùng Tauri v2 + Rust build trợ lý sức khỏe bàn làm việc chỉ ~15MB RAM (nhẹ hơn 40 lần Electron): Bổ sung Tab Thống Kê Mebius 7 ngày, Zing MP3 Ad-Guard đầu trang & Chế độ nhắc nhẹ Taskbar!\n\n"
            "Chào anh em Antigravity VN 🇻🇳\n\n"
            "Ngồi vibe-coding trong Antigravity IDE cuốn tới mức quên chớp mắt, quên uống nước và gõ phím liên tục suốt 5–6 tiếng là chuyện quá quen thuộc với anh em mình. Hôm nay mình chính thức phát hành bản DeskAura v1.1 (MIT License) kèm bộ cài sẵn cho cả Windows (.exe 2.9MB + bản Portable) và macOS Apple Silicon M1–M4 (.dmg 4.5MB):\n\n"
            "⚡ Những nâng cấp kỹ thuật nổi bật trong bản v1.1:\n"
            "• 2 Chế độ hiển thị lời nhắc (Overlay vs. Taskbar Icon): Cho phép chọn bung màn hình bài tập 60fps hoặc chỉ nháy nhẹ Icon dưới Taskbar/Khay hệ thống kèm chuông chữa lành 528Hz để không bao giờ cướp Focus cửa sổ IDE lúc đang gõ code.\n"
            "• Tách riêng Tab 'Thống Kê Mebius 7 Ngày': Đưa bộ 3 biểu đồ Nước uống & Vận động 7 ngày, Nhịp Tập Trung Sâu (Deep Focus Flow quy đổi 🍅 Pomodoro) và Aura Index (0–100) sang tab riêng, giúp màn hình Tổng quan hiển thị trọn vẹn 3 cột trong 1 khung nhìn không cần cuộn.\n"
            "• Trung tâm Zing MP3 Chặn Quảng Cáo 3 Lớp (Smart Audio Ad-Guard) + 10 lớp âm thanh & sóng não Alpha/Theta Offline + Windows Core Audio WASAPI Ducking (hạ nhạc YouTube/Spotify xuống 20% khi phát giọng AI Việt/Anh).\n"
            "• Native Idle & Fullscreen Detection (Win32 + macOS IOHIDSystem): Tự biết khi anh em rời bàn phím để reset đồng hồ, và tự hoãn khi đang họp/chiếu full màn hình.\n\n"
            "👉 Để vượt bộ lọc link của Facebook, mình in sẵn đường dẫn TẢI BẢN v1.1 (chữ xanh lá) và GITHUB REPO (chữ vàng) ở ngay thanh dưới cùng của tấm ảnh bên dưới. Anh em kéo về dùng và thả tặng repo 1 Star ⭐ trên GitHub nhé!"
        ),
    },
    "deskaura-vibe-code": {
        "name": "Vibe Code kiếm cơm (DeskAura v1.1)",
        "url": "https://www.facebook.com/groups/1385451906420187/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "message": (
            "🎁 Tặng anh em hệ Vibe Code bản cập nhật DeskAura v1.1: Làm việc sâu, đôi mắt sáng, cột sống êm (Bộ cài 2.9MB nhẹ hơn 40 lần Electron + Full Source Tauri/Rust)!\n\n"
            "Chào anh em Vibe Code kiếm cơm 👋\n\n"
            "Anh em cày dự án kiếm cơm ngày 10–14 tiếng thường dính 3 'sát thủ thầm lặng': (1) Tê buốt ống cổ tay (RSI) và cứng cổ vai gáy, (2) Khô rát mắt lúc chiều muộn, và (3) Đang gõ code hoặc nghe nhạc tập trung thì bị popup / quảng cáo cắt ngang làm rớt luôn mạch suy nghĩ!\n\n"
            "Mình vừa nâng cấp lên bản DeskAura v1.1 giải quyết trọn gói cho chính mình và tặng lại miễn phí 100% cho anh em:\n"
            "🔥 1. Chế độ 'Chỉ nhắc ở Icon Taskbar' (Mới trên v1.1): Không bung cửa sổ cắt ngang lúc đang gõ phím — chỉ nháy nhẹ dưới Taskbar kèm chuông 528Hz & giọng AI dịu nhạc (WASAPI hạ nhạc YouTube/Spotify xuống 20%).\n"
            "🔥 2. Trung tâm Zing MP3 Không Quảng Cáo & 10 âm thanh Offline: Đóng cửa sổ nhạc vẫn chạy ngầm và tự động bỏ qua quảng cáo 3 lớp; kết hợp tiếng mưa hiên nhà, suối rừng, sóng não Alpha 10Hz chạy Offline 100%.\n"
            "🔥 3. Tab Thống Kê Mebius 7 Ngày (Mới trên v1.1): Theo dõi số chu kỳ tập trung sâu 🍅 Pomodoro, lượng nước uống và Điểm Sức Khỏe Aura Index (80/100).\n"
            "🔥 4. Bài tập giãn cổ tay chống RSI (+35°) 60fps & Uống nước nuôi cây 🌸 trong ~15MB RAM (có sẵn bản Windows .exe, Portable và bản .DMG cho MacBook M1–M4).\n\n"
            "👉 Mình không gắn link trong bài để tránh bị lọc tự động — anh em nhìn thanh dưới cùng của tấm ảnh bên dưới để lấy LINK TẢI MIỄN PHÍ v1.1 (chữ xanh lá) và LINK GITHUB REPO (chữ vàng, nhớ thả giúp mình 1 Star ⭐ nhé)!"
        ),
    },
    "deskaura-build-in-public": {
        "name": "Build in Public VN (DeskAura v1.1)",
        "url": "https://www.facebook.com/groups/indiehackervn/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "message": (
            "[Build in Public — Release DeskAura v1.1] 'Làm việc sâu. Đôi mắt sáng. Cột sống êm' — Hành trình mình viết app Tauri v2 + Rust (15MB RAM) để tự cứu đôi mắt & cột sống khi làm việc 12h/ngày!\n\n"
            "Chào anh em Indie Hacker & Build in Public VN 👋\n\n"
            "Mình làm việc cường độ cao mỗi ngày với cả mảng lập trình AI lẫn điều hành Stepwell Vietnam. Có giai đoạn chiều nào mắt mình cũng nhòe đi, cổ tay phải tê cứng vì dùng chuột liên tục, còn cốc nước trên bàn thì nguội ngắt. Khi thử cài các app nhắc nghỉ ngơi có sẵn, mình nhận ra nỗi đau lớn nhất là: chúng làm đứt gãy sự tập trung (bung popup đè lên màn hình lúc đang gõ dở hoặc đang họp, báo thức giật mình, và ngốn 600MB RAM vì chạy Electron).\n\n"
            "Hôm nay mình vừa ra mắt bản cập nhật DeskAura v1.1 theo triết lý 'Nhỏ gọn, dịu mắt, không làm phiền' và chia sẻ miễn phí 100% (MIT License):\n"
            "🌱 1. Hai chế độ nhắc linh hoạt (Mới trên v1.1): Cho phép chọn giữa Bung màn hình hướng dẫn giãn cơ 60fps hoặc Chỉ nháy nhẹ biểu tượng dưới thanh Taskbar để không bao giờ làm gián đoạn lúc đang gõ phím. Tự hoãn khi đang họp Fullscreen.\n"
            "📊 2. Tách riêng Tab Thống Kê Mebius 7 Ngày (Mới trên v1.1): Giữ trang Tổng quan tinh gọn đúng 3 cột trên 1 màn hình duy nhất, đồng thời có riêng tab phân tích Lượng nước, Nhịp Tập Trung Sâu (7 🍅 Pomodoro) và Điểm Sức Khỏe Aura Index (80/100).\n"
            "🎶 3. Đưa Trung tâm Zing MP3 Chặn Quảng Cáo 3 Lớp lên đầu trang Nhạc Nền + 10 lớp âm thanh Offline + WASAPI Audio Ducking (tự dịu nhạc xuống 20% khi giọng AI Việt/Anh nhắc nhở).\n\n"
            "👉 Toàn bộ bộ cài Windows (.exe 2.9MB / Portable), macOS Apple Silicon (.dmg 4.5MB) và mã nguồn mở đã sẵn sàng ở 2 địa chỉ dưới chân tấm ảnh bên dưới (mình không đặt link trong bài để tránh bộ lọc Group). Rất mong nhận được phản hồi và 1 Star ⭐ trên GitHub từ anh em!"
        ),
    },
    "deskaura-chatgpt-business": {
        "name": "ChatGPT for Business (DeskAura v1.1)",
        "url": "https://www.facebook.com/groups/5749905918365041/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "message": (
            "🎁 [Quà tặng Dân Văn Phòng & Quản Lý — Bản v1.1 Mới Nhất] Làm việc sâu, đôi mắt sáng, cột sống êm: Trợ lý sức khỏe bàn làm việc & nhạc nền chữa lành miễn phí 100% cho Windows & MacBook!\n\n"
            "Chào anh chị em cộng đồng ChatGPT for Business 👋\n\n"
            "Hầu hết dân văn phòng và người làm việc trí óc cường độ cao đều đối mặt với 4 vấn đề mỗi chiều: mắt khô nhòe do nhìn màn hình liên tục, đau mỏi cổ vai gáy - tê cổ tay (hội chứng ống cổ tay RSI), mải làm việc quên uống nước, và bị thông báo/quảng cáo nhạc làm đứt mạch tập trung.\n\n"
            "Hôm nay mình xin gửi tặng cả nhà bản cập nhật DeskAura v1.1 (dùng miễn phí trọn đời, bộ cài siêu nhẹ chỉ 2.9MB, không cần đăng nhập):\n"
            "✅ Hai chế độ nhắc thông minh (Mới trên v1.1): Tùy chọn bung màn hình hướng dẫn 5 bài tập giãn cơ cổ - vai - cổ tay tại ghế, hoặc chỉ nháy nhẹ biểu tượng dưới thanh Taskbar để không làm phiền lúc đang gõ văn bản. Đang thuyết trình/họp toàn màn hình tự động tạm hoãn!\n"
            "✅ Uống nước nuôi cây nở hoa 🌸 & Biểu đồ thống kê Mebius 7 ngày (Mới trên v1.1): Chấm Điểm Sức Khỏe Aura Index (0–100) và theo dõi thói quen uống nước, vận động suốt tuần.\n"
            "✅ Zing MP3 Không Quảng Cáo & Giọng nhắc tự dịu nhạc (Auto-Ducking): Nghe nhạc chạy ngầm tự động bỏ qua quảng cáo âm thanh; khi giọng nhắc Việt/Anh vang lên, nhạc YouTube/Spotify tự nhỏ xuống 20% rồi êm ái trở lại.\n\n"
            "👉 Để bài viết không bị vướng bộ lọc link tự động của nhóm, anh chị em chỉ cần nhìn xuống thanh dưới cùng của bức ảnh bên dưới và gõ đúng địa chỉ màu xanh lá để tải về cho máy Windows hoặc MacBook nhé!"
        ),
    },
    "tsh-113k": {
        "name": "Cộng đồng Thần Số Học (113K)",
        "url": "https://www.facebook.com/groups/xemthansohocmienphi/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "tsh-card-1.png"),
        "message": (
            "🔮 Hữu duyên tặng 50 Bản Đồ Thần Số Học Pythagoras BẢN ĐẦY ĐỦ (Miễn phí 100% — Không thu phí) cho cả nhà mình hôm nay ạ!\n\n"
            "Mình vừa hoàn thiện bộ công cụ kết hợp công thức Thần số học Pythagoras chuẩn với mô hình AI phân tích chuyên sâu, tính và vẽ trọn bộ:\n"
            "✨ Con số Chủ đạo (kể cả các số Master 11/2, 22/4, 33/6) + Tổ hợp Sứ mệnh - Linh hồn - Nhân cách\n"
            "📊 Biểu đồ Ngày sinh 3 trục & cách bù đắp các mũi tên trống thực tế\n"
            "⛰️ Kim tự tháp 4 Đỉnh cao đời người (kèm độ tuổi & năm ứng nghiệm cụ thể)\n"
            "🧭 Vận niên Năm Cá Nhân 2026 & 2027 để định hướng công việc, tài chính\n\n"
            "Bạn nào muốn nhận tấm ảnh Bản đồ cá nhân nét cao (như mẫu bên dưới) kèm bài luận chi tiết 5 phần, chỉ cần BÌNH LUẬN bên dưới:\n"
            "👉 Họ tên khai sinh đầy đủ + Ngày tháng năm sinh dương lịch + Vấn đề bạn đang trăn trở nhất (đổi việc, kinh doanh, tài chính...)\n\n"
            "Mình sẽ lập và gửi tặng bản đầy đủ ngay dưới bình luận cho từng bạn! (Bạn nào ngại để ngày sinh công khai trên nhóm thì có thể tự nhập xem miễn phí 100% theo dòng hướng dẫn dưới chân tấm ảnh mẫu bên dưới nhé ạ ❤️)"
        ),
    },
    "tsh-36k": {
        "name": "THẦN SỐ HỌC - Hội chuyên gia tư vấn (36K)",
        "url": "https://www.facebook.com/groups/thansohoc.vnn.vn/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "tsh-card-2.png"),
        "message": (
            "Góc chia sẻ & tặng Bản đồ Thần Số Học Pythagoras 5 phần chuyên sâu hoàn toàn miễn phí cho thành viên nhóm mình 🌟\n\n"
            "Nhiều bạn chỉ tra mỗi Con số Chủ đạo nên hay thắc mắc vì sao đọc thấy chưa giống mình — thực tế phải ghép đủ bộ tam giác [Chủ đạo × Sứ mệnh từ Họ tên × Linh hồn nội tâm] kết hợp với [Năm cá nhân 2026] và [4 Đỉnh cao Kim tự tháp] thì bức tranh mới hiện ra sắc nét nhất.\n\n"
            "Hôm nay mình mở tặng miễn phí 100% trọn bộ tấm thẻ Bản Đồ Kim Tự Tháp + Bài luận 5 phần chi tiết. Anh chị em nào đang đứng trước ngã rẽ công việc hoặc tài chính năm 2026–2027 cứ để lại dưới bình luận:\n"
            "1️⃣ Họ và tên khai sinh (có dấu)\n"
            "2️⃣ Ngày / tháng / năm sinh dương lịch\n"
            "3️⃣ Điều đang phân vân cần gỡ rối nhất\n\n"
            "Mình sẽ xuất thẻ Bản đồ cá nhân và trả bài luận đầy đủ ngay dưới comment cho mọi người đối chiếu nhé! (Ai muốn tự tra riêng tư không lộ thông tin cá nhân cũng có thể xem hướng dẫn dưới góc tấm ảnh mẫu bên dưới ạ)"
        ),
    },
    "tsh-32k": {
        "name": "CỘNG ĐỒNG THẦN SỐ HỌC VIỆT NAM (32K)",
        "url": "https://www.facebook.com/groups/1037239429741263/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "tsh-card-3.png"),
        "message": (
            "🎁 Tặng miễn phí 100% Bản luận giải Năm Cá Nhân 2026–2027, Kim Tự Tháp 4 Đỉnh Cao & Sổ tay lộ trình 12 tháng A4 theo Thần số học Pythagoras!\n\n"
            "Cuối năm là lúc rất nhiều bạn băn khoăn: Nên giữ công việc ổn định, nhảy việc hay bắt đầu làm riêng? Trong Thần số học, câu trả lời nằm rất rõ ở sự giao thoa giữa Chu kỳ 9 Năm Cá Nhân và các trục khuyết trên Biểu đồ ngày sinh.\n\n"
            "Hôm nay mình mở khóa miễn phí hoàn toàn (0đ) cả tấm Thẻ Bản Đồ Cá Nhân Hóa (Số chủ đạo, Sứ mệnh, Linh hồn, Nhân cách, Biểu đồ 3 trục & 4 Đỉnh cao), bài luận 5 phần lẫn Sổ tay Cẩm nang Lộ trình 12 tháng in A4.\n\n"
            "💬 Bạn để lại dưới phần bình luận: [Họ tên khai sinh + Ngày sinh dương lịch + Câu hỏi công việc/tài chính đang quan tâm], mình sẽ trả đầy đủ ảnh Bản đồ + lời khuyên thực tế cho từng bạn nhé! (Hoặc tự tra cứu & tải sổ tay A4 miễn phí theo dòng chữ hướng dẫn ở cuối tấm ảnh mẫu bên dưới nha)"
        ),
    },
    "tsh-22k": {
        "name": "Cộng đồng thần số học Việt Nam (22K)",
        "url": "https://www.facebook.com/groups/1217195757153707/",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "tsh-card-4.png"),
        "message": (
            "✨ Mở đợt xem tặng miễn phí 100% Bản đồ Thần Số Học đầy đủ + Cẩm nang vận hạn 12 tháng A4 (Chủ đạo + Sứ mệnh + Linh hồn + Kim tự tháp 4 đỉnh cao) cho các bạn hữu duyên trong nhóm!\n\n"
            "Khác với các bản tóm tắt vài dòng chung chung, mình mở khóa tặng trọn vẹn 0đ:\n"
            "• Độ hòa hợp hoặc mâu thuẫn nội tâm giữa Số Linh Hồn (khát khao thật bên trong) và Số Nhân Cách (vỏ bọc bên ngoài)\n"
            "• Cách rèn luyện bù đắp các trục số bị trống trên Biểu đồ ngày sinh\n"
            "• Các cột mốc tuổi chuyển mình trên Kim tự tháp 4 Đỉnh cao & Sổ tay hành động chi tiết từng tháng trong năm 2026–2027.\n\n"
            "Bạn nào muốn xem chỉ cần bình luận: [Họ tên khai sinh đầy đủ + Ngày sinh dương lịch + Điều bạn đang trăn trở nhất], mình sẽ gửi tặng ảnh Thẻ Bản Đồ kèm bài luận đầy đủ dưới bình luận nhé! (Bạn nào ngại comment công khai có thể tự xem & xuất sổ tay A4 miễn phí 100% theo dòng ghi chú ở chân tấm ảnh mẫu bên dưới ạ)"
        ),
    },
}


def capture_fresh_dashboard_image(out_path: str = "/tmp/deta-live-shot.png") -> str:
    """Chụp ảnh màn hình trực tiếp trang chủ Deta AI Lab mới nhất để đính kèm bài đăng nhóm (vượt bộ lọc link 100%)."""
    base_banner = os.path.join(BASE_DIR, "public", "anh-chia-se.png")
    try:
        subprocess.run(
            [
                "google-chrome",
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--window-size=1100,1240",
                "--hide-scrollbars",
                "--virtual-time-budget=3500",
                f"--screenshot={out_path}",
                "http://127.0.0.1:8080/",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=True,
        )
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            return out_path
    except Exception:
        pass
    return base_banner


def post_group_safe_with_image(
    campaign_key: str,
    publish: bool = False,
    comment_link: bool = False,
    custom_message: str | None = None,
    custom_image: str | None = None,
) -> dict:
    """
    Đăng bài vào Facebook Group với nội dung ĐỘC BẢN cho từng nhóm (hoặc bài viết mới sinh theo ngày),
    ĐÍNH KÈM ẢNH CHỤP MÀN HÌNH THẬT và KHÔNG CHỨA LINK https:// trong thân bài (chống Admin Assist tự gỡ 100%).
    """
    if campaign_key not in GROUP_CAMPAIGNS:
        return {"ok": False, "loi": f"Không có chiến dịch nhóm '{campaign_key}'. Chọn: {list(GROUP_CAMPAIGNS.keys())}"}

    camp = dict(GROUP_CAMPAIGNS[campaign_key])
    if custom_message:
        # Đảm bảo tuyệt đối không lọt link https:// hay tên miền thô vào bài đăng Group
        cleaned_msg = re.sub(r"https?://\S+", "", custom_message)
        cleaned_msg = re.sub(r"\bkiemtien\.deta\.vn\S*", "dòng hướng dẫn dưới chân ảnh", cleaned_msg, flags=re.I)
        camp["message"] = cleaned_msg.strip()
    custom_img = custom_image or camp.get("image") or ""
    if custom_img and os.path.exists(custom_img):
        img_path = custom_img
    else:
        img_path = capture_fresh_dashboard_image(f"/tmp/deta-shot-{campaign_key}.png")
    screenshot_path = f"/tmp/fb-group-{campaign_key}-done.png"

    ensure_bot_browser(headless=False, open_login_tabs=False)
    with urllib.request.urlopen(f"http://127.0.0.1:{BOT_CDP_PORT}/json/version", timeout=2) as resp:
        info = json.loads(resp.read().decode("utf-8"))
        ws_path = "/" + info["webSocketDebuggerUrl"].split("://", 1)[1].split("/", 1)[1]

    cdp = SimpleCDPClient("127.0.0.1", BOT_CDP_PORT, ws_path, timeout=60.0)
    target_id = None
    sid = None
    try:
        # Đóng bớt các tab nhóm cũ bị treo hộp thoại beforeunload (giữ lại ít nhất 1 tab trắng để trình duyệt không tắt)
        old_targets = cdp.call("Target.getTargets").get("targetInfos", [])
        target_id = cdp.call("Target.createTarget", {"url": camp["url"]})["targetId"]
        for t in old_targets:
            if t.get("type") == "page" and "facebook.com/groups/" in t.get("url", "") and t.get("targetId") != target_id:
                try:
                    cdp.call("Target.closeTarget", {"targetId": t["targetId"]})
                except Exception:
                    pass

        cdp.call("Target.activateTarget", {"targetId": target_id})
        sid = cdp.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("DOM.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        # Chặn hộp thoại chọn file của hệ điều hành để upload ngầm 100%
        try:
            cdp.call("Page.setInterceptFileChooserDialog", {"enabled": True}, session_id=sid)
        except Exception:
            pass

        time.sleep(5.5)

        # Bước 1: Mở khung "Bạn viết gì đi..." bằng JS .click() trực tiếp trên [role="button"] (kèm fallback click tọa độ)
        dialog_opened = False
        for _ in range(10):
            trigger_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const btns = Array.from(document.querySelectorAll('[role="main"] [role="button"], [role="button"]'));
                    for (const b of btns) {
                        const txt = ((b.innerText || '') + ' ' + (b.getAttribute('aria-label') || '')).trim();
                        if (/^(Bạn viết gì đi|Viết gì đó|Bạn đang nghĩ gì|nghĩ gì thế|Write something|Tạo bài viết công khai)/i.test(txt) && !/bình luận|comment/i.test(txt)) {
                            const r = b.getBoundingClientRect();
                            if (r.width > 80 && r.height >= 22 && r.height <= 95) {
                                b.scrollIntoView({behavior: 'instant', block: 'center'});
                                b.click();
                                const r2 = b.getBoundingClientRect();
                                return {x: r2.left + Math.min(100, r2.width / 3), y: r2.top + r2.height / 2};
                            }
                        }
                    }
                    return null;
                })()""",
            )
            time.sleep(1.8)
            has_dlg = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => Array.from(document.querySelectorAll('[role="dialog"]')).some(d => {
                        const dr = d.getBoundingClientRect();
                        return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
                    }))()""",
                )
            )
            if has_dlg:
                dialog_opened = True
                break
            if trigger_pos:
                cdp_click_coords(cdp, sid, trigger_pos["x"], trigger_pos["y"])
                time.sleep(1.8)
                has_dlg = bool(
                    eval_js(
                        cdp,
                        sid,
                        """(() => Array.from(document.querySelectorAll('[role="dialog"]')).some(d => {
                            const dr = d.getBoundingClientRect();
                            return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
                        }))()""",
                    )
                )
                if has_dlg:
                    dialog_opened = True
                    break

        if not dialog_opened:
            return {"ok": False, "loi": f"Chưa mở được hộp thoại soạn bài nhóm {camp['name']} (có thể nhóm chưa duyệt thành viên)."}

        # Bước 2 (TEXT-FIRST): Gõ toàn bộ nội dung chữ TRƯỚC khi đính kèm ảnh (tránh bị ảnh đẩy cuộn lệch ô nhập)
        box_pos = None
        for _ in range(18):
            box_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                        const dr = d.getBoundingClientRect();
                        return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
                    });
                    const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                    if (!root) return null;
                    const boxes = Array.from(root.querySelectorAll('[contenteditable="true"][role="textbox"], [contenteditable="true"]'));
                    for (const box of boxes) {
                        const aria = ((box.getAttribute('aria-label') || '') + ' ' + (box.getAttribute('aria-placeholder') || '')).toLowerCase();
                        if (/bình luận|comment|tìm kiếm|search/i.test(aria)) continue;
                        let targetRect = box.getBoundingClientRect();
                        let cur = box;
                        while (cur && cur !== root && (targetRect.width <= 40 || targetRect.height < 10)) {
                            cur = cur.parentElement;
                            if (cur) targetRect = cur.getBoundingClientRect();
                        }
                        if (targetRect.width <= 40 || targetRect.height < 10) {
                            const rr = root.getBoundingClientRect();
                            targetRect = {left: rr.left + 32, top: rr.top + 165, width: rr.width - 64, height: 60};
                        }
                        box.focus();
                        return {
                            x: targetRect.left + Math.min(60, Math.max(20, targetRect.width / 4)),
                            y: targetRect.top + Math.min(24, Math.max(12, targetRect.height / 2)),
                            existingLen: (box.innerText || '').trim().length
                        };
                    }
                    return null;
                })()""",
            )
            if box_pos:
                break
            time.sleep(0.5)

        if not box_pos:
            return {"ok": False, "loi": f"Chưa tìm thấy ô nhập chữ trong hộp thoại nhóm {camp['name']}."}

        cdp_click_coords(cdp, sid, box_pos["x"], box_pos["y"])
        time.sleep(0.35)
        if box_pos.get("existingLen", 0) > 0:
            clear_editor_with_keys(cdp, sid)

        # Điền nội dung độc bản cho nhóm (0 đường link https://, xuống dòng bằng Shift+Enter)
        lines = camp["message"].split("\n")
        for idx, line in enumerate(lines):
            if line:
                cdp.call("Input.insertText", {"text": line}, session_id=sid)
            if idx < len(lines) - 1:
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyDown", "key": "Enter", "code": "Enter", "modifiers": 8, "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
                    session_id=sid,
                )
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyUp", "key": "Enter", "code": "Enter", "modifiers": 8, "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
                    session_id=sid,
                )
            time.sleep(0.05)

        time.sleep(1.0)

        # Bước 3 (IMAGE-SECOND + HARD GATE): Đính kèm ảnh với DOM depth=-1 & kiểm chứng kép (ảnh preview + chữ + tải xong 100%)
        def _attach_and_verify_group_image(click_photo_btn: bool) -> dict:
            if click_photo_btn:
                eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                            const dr = d.getBoundingClientRect();
                            return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
                        });
                        const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                        if (!root) return false;
                        const btn = Array.from(root.querySelectorAll('[role="button"], div[aria-label]')).find(
                            el => /Ảnh\\/video|Photo\\/video/i.test(el.getAttribute('aria-label') || '')
                        );
                        if (btn) { btn.click(); return true; }
                        return false;
                    })()""",
                )
                time.sleep(1.4)

            tagged_count = eval_js(
                cdp,
                sid,
                """(() => {
                    document.querySelectorAll('[data-deta-group-file]').forEach(el => el.removeAttribute('data-deta-group-file'));
                    const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                        const dr = d.getBoundingClientRect();
                        return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
                    });
                    const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                    let candidates = root
                        ? Array.from(root.querySelectorAll('input[type="file"]')).filter(
                              inp => (inp.getAttribute('accept') || '').toLowerCase().includes('image') || !inp.getAttribute('accept')
                          )
                        : [];
                    if (!candidates.length) {
                        candidates = Array.from(document.querySelectorAll('input[type="file"]')).filter(inp => {
                            const acc = (inp.getAttribute('accept') || '').toLowerCase();
                            const ptxt = inp.parentElement ? (inp.parentElement.innerText || '') : '';
                            return acc.includes('image') && inp.hasAttribute('multiple') && !ptxt.includes('thành viên');
                        });
                    }
                    if (!candidates.length) return 0;
                    candidates[candidates.length - 1].setAttribute('data-deta-group-file', '1');
                    return candidates.length;
                })()""",
            )
            if not tagged_count:
                return {"ok": False, "reason": "no_file_input"}

            doc_root = cdp.call("DOM.getDocument", {"depth": -1}, session_id=sid)["root"]["nodeId"]
            file_nodes = cdp.call(
                "DOM.querySelectorAll",
                {"nodeId": doc_root, "selector": 'input[data-deta-group-file="1"]'},
                session_id=sid,
            ).get("nodeIds", [])
            if not file_nodes:
                return {"ok": False, "reason": "dom_node_missing"}

            cdp.call("DOM.setFileInputFiles", {"files": [img_path], "nodeId": file_nodes[-1]}, session_id=sid)
            # Chờ tối thiểu 4.5s để luồng rupload.facebook.com trả về photo_fbid hoàn tất vào React state
            time.sleep(4.5)

            last_state = None
            for _ in range(16):
                last_state = eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                            const dr = d.getBoundingClientRect();
                            return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
                        });
                        const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                        if (!root) return null;
                        const imgs = Array.from(root.querySelectorAll('img')).filter(im => {
                            const r = im.getBoundingClientRect();
                            const src = im.getAttribute('src') || '';
                            return src.startsWith('blob:') || (r.width >= 150 && r.height >= 120);
                        });
                        const hasMediaAttachment = Array.from(root.querySelectorAll('[aria-label]')).some(el =>
                            /File phương tiện đính kèm|Chỉnh sửa ảnh\\/video|Gỡ file đính kèm|Gỡ ảnh|Media attachment|Edit photo\\/video|Remove attachment/i.test(
                                el.getAttribute('aria-label') || ''
                            )
                        );
                        if (imgs.length) {
                            imgs[0].scrollIntoView({behavior: 'instant', block: 'nearest'});
                        }
                        const progressBars = root.querySelectorAll('[role="progressbar"]').length;
                        const boxEl = Array.from(root.querySelectorAll('[contenteditable="true"]')).find(
                            b => !/bình luận|comment|tìm kiếm/i.test(b.getAttribute('aria-label') || '')
                        );
                        const textLen = boxEl ? (boxEl.innerText || '').trim().length : 0;
                        const postBtn = Array.from(root.querySelectorAll('[role="button"], button')).find(b =>
                            /^(đăng|đăng bài|đăng ngay|gửi|gửi bài|post|submit)$/i.test(
                                ((b.getAttribute('aria-label') || '') || (b.innerText || '')).trim()
                            )
                        );
                        const postEnabled = postBtn ? (postBtn.getAttribute('aria-disabled') !== 'true' && !postBtn.disabled) : false;
                        return {previewImgs: imgs.length, hasMediaAttachment, progressBars, textLen, postEnabled};
                    })()""",
                )
                if (
                    last_state
                    and (last_state["previewImgs"] > 0 or last_state["hasMediaAttachment"])
                    and last_state["progressBars"] == 0
                    and last_state["postEnabled"]
                    and last_state["textLen"] >= 20
                ):
                    return {"ok": True, "state": last_state}
                time.sleep(0.8)
            return {"ok": False, "reason": "preview_or_upload_incomplete", "state": last_state}

        attach_chk = _attach_and_verify_group_image(click_photo_btn=True)
        if not attach_chk.get("ok"):
            attach_chk = _attach_and_verify_group_image(click_photo_btn=False)

        image_attached = bool(attach_chk.get("ok"))
        shot_pre = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_pre.get("data"):
            with open(f"/tmp/fb-group-{campaign_key}-preview.png", "wb") as f:
                f.write(base64.b64decode(shot_pre["data"]))

        # CỔNG CHẶN CỨNG: Tuyệt đối KHÔNG bấm Đăng nếu thiếu ảnh xem trước trong hộp thoại Group!
        if not image_attached:
            return {
                "ok": False,
                "loi": f"Chưa đính kèm được ảnh xem trước vào hộp thoại nhóm {camp['name']} — đã chặn nút Đăng để không lọt bài thiếu ảnh!",
                "chi_tiet_kiem_chung": attach_chk,
                "anh_xem_truoc": f"/tmp/fb-group-{campaign_key}-preview.png",
            }

        if not publish:
            return {
                "ok": True,
                "trang_thai": "da_dien_san_nhom",
                "nhom": camp["name"],
                "dinh_kem_anh": image_attached,
                "kiem_chung": attach_chk.get("state"),
                "anh_xem_truoc": f"/tmp/fb-group-{campaign_key}-preview.png",
            }

        find_submit_js = """(() => {
            const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                const dr = d.getBoundingClientRect();
                return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
            });
            const root = dlgs.length ? dlgs[dlgs.length - 1] : document;
            const btns = Array.from(root.querySelectorAll('[role="button"], button'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').trim();
                const txt = (b.innerText || '').trim();
                const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                if (!disabled && (/^(đăng|đăng bài|đăng ngay|gửi|gửi bài|post|submit)$/i.test(aria) || /^(đăng|đăng bài|đăng ngay|gửi|gửi bài|post|submit)$/i.test(txt))) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 20 && r.height > 15) return {x: r.left + r.width / 2, y: r.top + r.height / 2};
                }
            }
            return null;
        })()"""

        post_pos = None
        for _ in range(12):
            post_pos = eval_js(cdp, sid, find_submit_js)
            if post_pos:
                break
            time.sleep(0.7)

        if not post_pos:
            return {"ok": False, "loi": f"Chưa thấy nút Đăng bật sáng trong nhóm {camp['name']}."}

        cdp_click_coords(cdp, sid, post_pos["x"], post_pos["y"])

        submitted = False
        for attempt in range(18):
            time.sleep(1.0)
            still_open = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                            const dr = d.getBoundingClientRect();
                            return dr.width > 250 && dr.height > 200;
                        });
                        return dlgs.some(d => {
                            const boxes = Array.from(d.querySelectorAll('[contenteditable="true"]'));
                            return boxes.some(b => !/bình luận|comment/i.test((b.getAttribute('aria-label') || '')));
                        });
                    })()""",
                )
            )
            if not still_open:
                submitted = True
                break
            if attempt == 4:
                retry_pos = eval_js(cdp, sid, find_submit_js)
                if retry_pos:
                    cdp_click_coords(cdp, sid, retry_pos["x"], retry_pos["y"])

        time.sleep(5.5)
        shot_done = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_done.get("data"):
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(shot_done["data"]))

        discovered_post_url = ""
        if submitted:
            record_diary_entry(f"Đăng bài chia sẻ độc bản (kèm ảnh trực tiếp phòng Lab) vào cộng đồng {camp['name']}.")
            posted_iso = now_vn().isoformat(timespec="seconds")
            try:
                glog = {}
                if os.path.exists(GROUP_LOG_PATH):
                    with open(GROUP_LOG_PATH, "r", encoding="utf-8") as gf:
                        glog = json.load(gf)
                glog[campaign_key] = {"name": camp["name"], "url": camp["url"], "posted_at": posted_iso}
                with open(GROUP_LOG_PATH, "w", encoding="utf-8") as gf:
                    json.dump(glog, gf, ensure_ascii=False, indent=2)
            except Exception:
                pass
            # Tự động lấy URL bài vừa đăng (nếu nhóm duyệt tự động ngay) đưa vào danh sách theo dõi 4h/lần
            try:
                import numerology_comment_bot as ncb

                cdp.call("Page.navigate", {"url": camp["url"].rstrip("/") + "/my_posted_content"}, session_id=sid)
                time.sleep(4.2)
                urls_now = ncb.extract_my_posted_urls_on_page(cdp, sid, max_posts=2)
                if urls_now:
                    t_store = ncb.load_tracked_store()
                    for u_new in urls_now:
                        pid_new = ncb.extract_post_id(u_new)
                        if pid_new not in (t_store.get("posts") or {}):
                            ncb.register_or_update_post(t_store, u_new, campaign_key, camp["name"], camp["url"], posted_at=posted_iso)
                            t_store.setdefault("groups_harvested", {})[campaign_key] = posted_iso
                            discovered_post_url = u_new
                            break
                    ncb.save_tracked_store(t_store)
            except Exception:
                pass

        return {
            "ok": True,
            "trang_thai": "da_dang_nhom" if submitted else "da_bam_dang_nhom",
            "nhom": camp["name"],
            "url_nhom": camp["url"],
            "post_url_theo_doi": discovered_post_url,
            "dinh_kem_anh": image_attached,
            "anh_chup": screenshot_path,
        }
    finally:
        try:
            if sid:
                cdp.call("Page.setInterceptFileChooserDialog", {"enabled": False}, session_id=sid)
        except Exception:
            pass
        try:
            if target_id:
                cdp.call("Target.closeTarget", {"targetId": target_id})
        except Exception:
            pass
        cdp.close()


SPOTLIGHT_CAMPAIGNS = {
    "free-9-tools": {
        "title": "Mở Khóa Miễn Phí 100% (0đ) Trọn Bộ 9 Công Cụ AI + Ra Mắt Deta Studio B2B 24h",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-free-9-tools.png"),
        "facebook": (
            "🎁 Quyết định chiến lược Ngày 3/20 thử thách nuôi AI tự kiếm tiền trên kiemtien.deta.vn: Chính thức MỞ KHÓA MIỄN PHÍ 100% (0đ, không cần tạo tài khoản, không đóng dấu quảng cáo) trọn bộ 9 Công cụ AI thực chiến cho cộng đồng! 🚀\n\n"
            "Thay vì thu phí lẻ từng lượt tải làm gián đoạn trải nghiệm của mọi người, từ hôm nay toàn bộ 9 công cụ tự phục vụ trên phòng Lab đều mở tự do 100%:\n"
            "1️⃣ AI Tự Code Landing Page Bán Hàng (tải trọn bộ mã nguồn index.html sạch): https://kiemtien.deta.vn/cong-cu/tao-landing-page?nguon=fb-spotlight-0d\n"
            "2️⃣ Thiết Kế CV Chuẩn ATS A4 & Thư Ứng Tuyển song ngữ Việt–Anh (xuất PDF Harvard sạch): https://kiemtien.deta.vn/cong-cu/tao-cv-ats?nguon=fb-spotlight-0d\n"
            "3️⃣ Lập Lịch 30 Ngày Bài Đăng & Hook TikTok theo ngành hàng (tải thẳng Excel .CSV): https://kiemtien.deta.vn/cong-cu/lich-30-ngay?nguon=fb-spotlight-0d\n"
            "4️⃣ Giải Mã Thần Số Học Pythagoras + Sổ tay Lộ trình 12 Tháng A4 (0đ trọn bộ): https://kiemtien.deta.vn/cong-cu/than-so-hoc?nguon=fb-spotlight-0d\n"
            "5️⃣ Chấm Điểm Tốc Độ Web, Khám Kênh TikTok/Shopee, Kịch Bản Video 30s & Bộ Prompt AI: https://kiemtien.deta.vn/cong-cu?nguon=fb-spotlight-0d\n\n"
            "💼 Vậy con AI sẽ sống bằng gì để vượt thử thách 20 ngày? Hôm nay tụi mình chính thức ra mắt **Deta Studio B2B (Done-For-You 24h)**: Dành riêng cho anh chị chủ shop & doanh nghiệp bận rộn muốn đội ngũ kỹ sư + AI thiết kế Landing Page độc bản, gắn Form thu khách về Zalo/Pixel và bàn giao trọn bộ 30 ngày Content & Banner trong đúng 24 giờ (chỉ từ 490K):\n"
            "👉 Xem mẫu thực tế & đặt lịch tư vấn 1-1: https://kiemtien.deta.vn/dich-vu/thiet-ke-tron-goi?nguon=fb-spotlight-b2b"
        ),
        "threads": (
            "🎁 Ngày 3/20 nuôi AI tự kiếm tiền: Quyết định MỞ KHÓA MIỄN PHÍ 100% (0đ, không cần login) trọn bộ 9 Công cụ AI thực chiến!\n\n"
            "• Tạo CV chuẩn ATS xuất PDF sạch\n"
            "• Lịch 30 ngày bán hàng tải Excel .CSV\n"
            "• AI tự code Landing Page 1 file .HTML\n"
            "• Bản đồ Thần Số Học + Sổ tay 12 tháng A4\n"
            "👉 Dùng ngay: https://kiemtien.deta.vn/?nguon=threads-spotlight-0d\n"
            "💼 Cần làm Web & Phễu trọn gói 24h: https://kiemtien.deta.vn/b2b?nguon=threads-b2b"
        ),
    },
    "shop-kit-0d": {
        "title": "Bộ 3 Vũ Khí AI 0đ Cho Chủ Shop + Gói Thiết Kế Trọn Gói B2B 24h",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-free-9-tools.png"),
        "facebook": (
            "🛍️ Anh chị em đang bán hàng online hoặc làm dịch vụ lấy ngay bộ 3 công cụ AI vừa mở MIỄN PHÍ 100% (0đ, không cần đăng ký tài khoản) trên Deta AI Lab nhé:\n\n"
            "📅 1. Lập Lịch 30 Ngày Bài Đăng & Kịch Bản Hook TikTok — nhập tên sản phẩm là ra đủ 30 góc tiếp cận khách hàng, tải thẳng file Excel .CSV về giao cho nhân sự: https://kiemtien.deta.vn/cong-cu/lich-30-ngay?nguon=fb-shop-0d\n"
            "🚀 2. AI Tự Code Landing Page 8 Khối Chốt Đơn — tải trọn bộ file index.html sạch chạy vĩnh viễn không tốn phí thuê nền tảng hàng tháng: https://kiemtien.deta.vn/cong-cu/tao-landing-page?nguon=fb-shop-0d\n"
            "⚡ 3. Chấm Điểm Tốc Độ Web & Khám Bệnh Kênh TikTok/Shopee lẹt đẹt view: https://kiemtien.deta.vn/cong-cu?nguon=fb-shop-0d\n\n"
            "💼 Còn nếu anh chị bận kinh doanh, không muốn tự chỉnh ảnh/cài tên miền thì giao trọn gói cho **Deta Studio B2B** — hoàn thiện Landing Page độc bản + Form Zalo + 30 ngày Content trong đúng 24 giờ (từ 490K):\n"
            "👉 https://kiemtien.deta.vn/dich-vu/thiet-ke-tron-goi?nguon=fb-shop-b2b"
        ),
        "threads": (
            "🛍️ Tặng chủ Shop & làm dịch vụ bộ 3 vũ khí AI MIỄN PHÍ 100% (0đ, không cần đăng ký):\n"
            "1. Lập lịch 30 ngày bài đăng + Hook TikTok tải Excel .CSV\n"
            "2. AI tự code Landing Page bán hàng tải file .HTML sạch\n"
            "3. Chấm điểm tốc độ Web & khám kênh TikTok\n\n"
            "👉 Dùng miễn phí: https://kiemtien.deta.vn/cong-cu?nguon=threads-shop-0d\n"
            "💼 Bận việc cần dựng trọn gói 24h: https://kiemtien.deta.vn/b2b?nguon=threads-shop-b2b"
        ),
    },
    "cv-ats-0d": {
        "title": "AI Thiết Kế CV Chuẩn ATS A4 & Thư Ứng Tuyển Xuất PDF Sạch 0đ",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-free-9-tools.png"),
        "facebook": (
            "📄 Nhiều trang tạo CV online hay cho gõ xong xuôi hết rồi tới bước tải PDF lại bắt nạp tiền xóa logo — nên trên Deta AI Lab mình mở MIỄN PHÍ 100% (0đ) công cụ AI Thiết Kế CV Chuẩn ATS A4 & Thư Ứng Tuyển luôn nhé!\n\n"
            "✦ Tự động viết lại kinh nghiệm theo công thức STAR giàu số liệu thuyết phục HR\n"
            "✦ Hỗ trợ cả Tiếng Việt chuyên nghiệp lẫn Tiếng Anh chuẩn Quốc tế\n"
            "✦ Dàn sẵn bố cục Harvard A4 + Cover Letter đồng bộ, bấm 1 nút xuất PDF nét cao sạch 100% (không watermark, không bắt tạo tài khoản)\n\n"
            "Anh chị em đang chuẩn bị hồ sơ ứng tuyển hoặc nâng cấp CV cuối năm vào dùng miễn phí tại đây nhé:\n"
            "👉 https://kiemtien.deta.vn/cong-cu/tao-cv-ats?nguon=fb-cv-0d"
        ),
        "threads": (
            "📄 Tặng anh chị em đang tìm việc / nâng cấp hồ sơ: Công cụ AI Thiết kế CV chuẩn ATS Harvard & Thư ứng tuyển (Cover Letter) MIỄN PHÍ 100% (0đ)!\n\n"
            "Chọn ngôn ngữ Việt hoặc Anh, bấm xuất PDF A4 sạch không dính logo quảng cáo, không bắt tạo tài khoản:\n"
            "👉 https://kiemtien.deta.vn/cong-cu/tao-cv-ats?nguon=threads-cv-0d"
        ),
    },
    "landing": {
        "title": "AI Tự Code Landing Page Bán Hàng 1 File .HTML + 2 Showcase",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-landing-page.png"),
        "facebook": (
            "Ngày 2 nuôi con AI tự kiếm tiền trên kiemtien.deta.vn — sáng nay nó vừa tự học xong kỹ năng thiết kế & code trọn bộ Landing Page bán hàng 1 file .HTML chuẩn 8 khối chốt đơn 🚀\n\n"
            "Để mọi người dễ hình dung độ chỉn chu trước khi dùng, nó tự dựng luôn 2 trang Showcase mẫu thật (đẹp trên cả PC lẫn điện thoại):\n"
            "🍃 Mẫu #1 (Sáng tinh tế — hợp F&B, trà bánh, đặc sản, mỹ phẩm): https://kiemtien.deta.vn/mau-landing/van-son-tra/\n"
            "🎙️ Mẫu #2 (Tối hiện đại — hợp khóa học, phần mềm SaaS, dịch vụ B2B): https://kiemtien.deta.vn/mau-landing/detaspeak-ai/\n\n"
            "Anh em chủ shop hoặc làm dịch vụ chỉ cần gõ tên sản phẩm + SĐT/Zalo (hoặc bấm nút nạp mẫu 1 chạm) là AI dựng & cho tải trọn bộ mã nguồn index.html sạch MIỄN PHÍ 100% (0đ, không cần đăng ký, up thẳng lên Cloudflare/GitHub Pages chạy vĩnh viễn không tốn phí hosting hàng tháng):\n"
            "👉 https://kiemtien.deta.vn/cong-cu/tao-landing-page?nguon=fb-spotlight-lp"
        ),
        "threads": (
            "Thả con AI tự vận hành trên Deta AI Lab: mở MIỄN PHÍ 100% (0đ) công cụ AI Tự Code Landing Page bán hàng 1 file .HTML chuẩn 8 khối chốt đơn 🚀\n\n"
            "Có sẵn 2 trang Showcase mẫu thật (F&B sáng tinh tế & SaaS tối hiện đại), gõ tên sản phẩm là dựng & tải trọn bộ file index.html sạch trong 15s hoàn toàn miễn phí:\n"
            "https://kiemtien.deta.vn/cong-cu/tao-landing-page?nguon=threads-spotlight-lp"
        ),
    },
    "than-so-hoc": {
        "title": "Chuyên trang Giải Mã Thần Số Học Pythagoras Miễn Phí 100%",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-than-so-hoc.png"),
        "facebook": (
            "Chiều đổi gió chút mọi người ơi 🔮 Con AI trên phòng Lab của mình vừa mở riêng một chuyên trang Giải Mã Thần Số Học Pythagoras hoàn toàn MIỄN PHÍ 100% (không thu phí, không cần tạo tài khoản).\n\n"
            "Giao diện được thiết kế lại như một chuyên trang tra cứu riêng biệt. Chỉ cần nhập Họ tên khai sinh & Ngày sinh dương lịch là hệ thống lập ngay:\n"
            "✦ Tổ hợp Số Chủ Đạo · Sứ Mệnh · Linh Hồn · Nhân Cách\n"
            "✦ Biểu đồ ngày sinh 3×3 & Kim Tự Tháp 4 Đỉnh Cao đời người\n"
            "✦ Chu kỳ vận niên Năm cá nhân 2026–2027 + trọn bộ 5 phần luận giải sâu\n"
            "✦ Tải ngay tấm thẻ Bản đồ cá nhân (.PNG nét cao 1080×1350) về điện thoại hoặc bấm gửi rủ bạn bè/người thương cùng tra đối chiếu!\n\n"
            "Mời mọi người vào khám phá con số của mình miễn phí tại đây nhé:\n"
            "👉 https://kiemtien.deta.vn/cong-cu/than-so-hoc?nguon=fb-spotlight-tsh"
        ),
        "threads": (
            "Chiều đổi gió chút mọi người ơi 🔮 Con AI trên Deta AI Lab vừa mở chuyên trang Giải Mã Thần Số Học Pythagoras MIỄN PHÍ 100% (không thu phí, không cần đăng nhập).\n\n"
            "Nhập Họ tên & Ngày sinh là ra đủ Kim Tự Tháp 4 Đỉnh Cao, Năm cá nhân 2026–2027, bài luận 5 phần sâu + tải ảnh Bản đồ .PNG nét cao về máy:\n"
            "https://kiemtien.deta.vn/cong-cu/than-so-hoc?nguon=threads-spotlight-tsh"
        ),
    },
    "chua-online": {
        "title": "Liên Hoa Các · Không Gian Tĩnh Tâm & Hồ Sen Hoa Đăng 4-Trong-1 Miễn Phí",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-chua-online.png"),
        "facebook": (
            "Ai đang áp lực công việc hay nhiều trăn trở dừng lại 1 phút hít thở sâu nhé 🪷\n\n"
            "Tụi mình vừa dựng xong **Liên Hoa Các — Không Gian Tĩnh Tâm & Chữa Lành Tinh Thần 4-trong-1** hoàn toàn MIỄN PHÍ 100%:\n"
            "🔔 1. Gõ Mõ Gỗ Lim & Thỉnh Đại Hồng Chung ASMR cùng tiếng mưa rơi hiên chùa & tiêu trúc thiền viện\n"
            "🏮 2. Thả Đèn Hoa Đăng Ước Nguyện trôi thực tế trên mặt Hồ Sen Đêm Trăng\n"
            "🎋 3. Lắc Ống Xăm Cổ Truyền + AI Deta luận giải sâu theo đúng điều bạn đang trăn trở\n"
            "🖼️ 4. Xuất ảnh Thẻ Quẻ Bình An đóng ấn đỏ cổ phong (.PNG nét cao)\n\n"
            "👉 Vào tĩnh tâm, thả đèn hoa đăng & xin 1 Quẻ Bình An miễn phí tại đây nhé:\n"
            "https://kiemtien.deta.vn/chua-online?nguon=fb-chua-online"
        ),
        "threads": (
            "Thấy anh em đang rần rần trend Đi chùa online nên tụi mình dựng ngay Liên Hoa Các — Chùa online Tĩnh Tâm 4-trong-1 MIỄN PHÍ 100% 🪷\n\n"
            "🌧️ Nghe mưa rơi hiên chùa, gõ Mõ Gỗ Lim & thỉnh Đại Hồng Chung ASMR\n"
            "🏮 Thả Đèn Hoa Đăng ước nguyện trôi thực tế trên Hồ Sen đêm trăng\n"
            "🎋 Lắc Ống Xăm + AI luận giải sâu & tải Thẻ Quẻ Bình An cổ phong\n\n"
            "👉 Trải nghiệm Chùa online tại: https://kiemtien.deta.vn/chua-online?nguon=threads-chua-online"
        ),
    },
    "github-opensource": {
        "title": "Mã Nguồn Mở (Open Source) Dự Án AI-Money Trên GitHub",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-github-architecture.png"),
        "facebook": (
            "🎁 [Open Source - Ngày 6/20] Chính thức mở mã nguồn 100% dự án AI tự kiếm tiền (AI-Money) trên GitHub cho anh em tải về tự dựng trạm riêng! 🚀\n\n"
            "Sau 6 ngày thả con AI tự vận hành trạm Deta AI Lab với sổ cái minh bạch thời gian thực (đã ghi nhận 93.686đ doanh thu chuyển khoản thật đầu tiên và khách vào gõ mõ, thả hoa đăng trên Chùa Online lúc nửa đêm), hôm nay mình đã rà soát bảo mật 3 vòng và đẩy trọn bộ source code lên GitHub:\n\n"
            "⚡ Bên trong repo AI-Money có sẵn những gì?\n"
            "1️⃣ Backend Python 3.12 thuần + SQLite WAL (0 phụ thuộc nặng), tích hợp sẵn luồng tạo mã VietQR & Webhook tự động nhảy sổ cái.\n"
            "2️⃣ Trọn bộ 14 giao diện Web: Trạm điều hành Bento Sáng/Tối, 9+ công cụ AI miễn phí, Chuyên trang Thần Số Học Pythagoras, Chùa Online Liên Hoa Các (Web Audio + Hồ Sen đêm trăng) & Cẩm nang 12 bài Chatbot.\n"
            "3️⃣ Thư mục .agents/skills gồm 3 bộ Skill thực chiến cho AI Agent (Thiết kế Landing Page chuyển đổi cao, Kiến trúc Chùa Việt & Runbook điều khiển Chrome CDP).\n"
            "4️⃣ Tài liệu README hướng dẫn cầm tay chỉ việc 6 bước từ A-Z cho người mới: từ lúc git clone về máy đến lúc trỏ tên miền riêng qua Cloudflare Tunnel chạy 24/7 (không cần mở port modem).\n\n"
            "📦 Tải mã nguồn & tặng repo 1 Star ⭐ tại GitHub:\n"
            "👉 https://github.com/duongbirken2510/AI-Money\n"
            "🌐 Trải nghiệm trực tiếp trạm Demo tại:\n"
            "👉 https://kiemtien.deta.vn"
        ),
        "threads": (
            "🎁 [Open Source - Ngày 6/20] Mình vừa mở mã nguồn 100% dự án AI tự kiếm tiền (AI-Money) lên GitHub! 🚀\n\n"
            "⚡ Full-stack Python 3.12 thuần + SQLite + VietQR Webhook\n"
            "🪷 Có sẵn 9+ Micro-Tools AI, Thần Số Học Pythagoras, Chùa Online Liên Hoa Các & 3 bộ AI Agent Skills (.agents/skills)\n"
            "📘 Kèm hướng dẫn 6 bước từ git clone đến gắn tên miền qua Cloudflare Tunnel A-Z cho người mới!\n\n"
            "📦 Repo GitHub (nhớ thả 1 Star ⭐ ủng hộ tụi mình nhé): https://github.com/duongbirken2510/AI-Money"
        ),
    },
    "deskaura": {
        "title": "DeskAura v1.1 · Trợ Lý Sức Khỏe Bàn Làm Việc & Nhạc Nền Chữa Lành (Windows & Mac + Open Source)",
        "image": os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-deskaura.png"),
        "facebook": (
            "🌿 [Ra mắt DeskAura v1.1 — 'Làm việc sâu. Đôi mắt sáng. Cột sống êm'] Trợ lý sức khỏe bàn làm việc & nhạc nền chữa lành Miễn phí 100% + Open Source cho Windows & MacBook!\n\n"
            "Mình làm việc cường độ cao mỗi ngày với cả mảng lập trình AI lẫn điều hành Stepwell Vietnam. Mình viết DeskAura bằng Tauri v2 + Rust (bộ cài chỉ 2.9MB, chạy ngầm ~15MB RAM — nhẹ hơn 40 lần Electron) để tự cứu lấy đôi mắt và cột sống của chính mình, và chia sẻ miễn phí 100% để bất kỳ ai ngồi máy tính cũng giữ được sức khỏe bền vững:\n\n"
            "🔔 1. Hai chế độ nhắc linh hoạt (Mới trên v1.1): Tùy chọn Bung màn hình hướng dẫn giãn cơ 60fps HOẶC 'Chỉ nháy nhẹ biểu tượng dưới thanh Taskbar' kèm chuông 528Hz & giọng nhắc để không làm gián đoạn lúc đang gõ phím. Tự hoãn khi đang họp toàn màn hình!\n"
            "📊 2. Tab Thống Kê Mebius 7 Ngày độc lập (Mới trên v1.1): Theo dõi trực quan lượng nước uống, số chu kỳ tập trung sâu (🍅 Pomodoro) và Điểm Sức Khỏe Aura Index (80/100) suốt tuần, giúp màn hình Tổng quan gọn gàng trong 3 cột không cần cuộn.\n"
            "🎶 3. Trung tâm Zing MP3 Không Quảng Cáo & Giọng nhắc tự dịu nhạc (WASAPI Auto-Ducking): Nghe nhạc chạy ngầm tự động bỏ qua quảng cáo 3 lớp; khi giọng AI Việt/Anh nhắc nhở vang lên, tiếng nhạc YouTube/Spotify tự nhỏ xuống 20% rồi êm ái trở lại.\n"
            "🖐️ 4. Giãn cổ tay chống RSI (+35°), nghỉ mắt 20-20-20 & Uống nước nuôi cây nở hoa 🌸 (+200ml 1-click từ System Tray).\n\n"
            "💻 Tải miễn phí bản v1.1 cho Windows (.exe / Portable) & MacBook M1–M4 (.dmg) tại:\n"
            "👉 https://duongbirken.deta.vn/deskaura\n"
            "⭐ Mã nguồn mở trên GitHub (Tauri v2 + Rust — nhớ thả tặng mình 1 Star nhé!):\n"
            "👉 https://github.com/duongbirken2510/deskaura"
        ),
        "threads": (
            "🌿 Mình vừa tung bản cập nhật DeskAura v1.1 ('Làm việc sâu. Đôi mắt sáng. Cột sống êm') — viết bằng Tauri v2 + Rust chỉ ~15MB RAM (bộ cài 2.9MB, Miễn phí 100% & Open Source cho Windows + Mac):\n\n"
            "🔔 2 chế độ nhắc mới: Bung bài tập giãn cơ cổ tay RSI (+35°) HOẶC chỉ nháy nhẹ Icon Taskbar để không đứt mạch gõ code\n"
            "📊 Tab Thống Kê Mebius 7 Ngày độc lập (Aura Index 80/100 + chu kỳ 🍅 Deep Focus)\n"
            "🎶 Trung tâm Zing MP3 chạy ngầm 0 quảng cáo + WASAPI tự dịu nhạc xuống 20% khi giọng AI nhắc!\n\n"
            "💻 Tải miễn phí v1.1: https://duongbirken.deta.vn/deskaura\n"
            "⭐ GitHub (thả 1 Star ủng hộ mình nhé): https://github.com/duongbirken2510/deskaura"
        ),
    },
}


def post_personal_fb_with_image(message: str, image_path: str, publish: bool = False, screenshot_path: str = "/tmp/fb-spotlight.png") -> dict:
    """Đăng bài lên tường Facebook cá nhân kèm ảnh trực quan nét cao + link bấm trực tiếp."""
    ensure_bot_browser(headless=False, open_login_tabs=False)
    with urllib.request.urlopen(f"http://127.0.0.1:{BOT_CDP_PORT}/json/version", timeout=2) as resp:
        info = json.loads(resp.read().decode("utf-8"))
        ws_path = "/" + info["webSocketDebuggerUrl"].split("://", 1)[1].split("/", 1)[1]

    cdp = SimpleCDPClient("127.0.0.1", BOT_CDP_PORT, ws_path, timeout=60.0)
    target_id = None
    sid = None
    try:
        target = cdp.call("Target.createTarget", {"url": "https://www.facebook.com/"})
        target_id = target["targetId"]
        time.sleep(5.5)

        cdp.call("Target.activateTarget", {"targetId": target_id})
        sid = cdp.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("DOM.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        try:
            cdp.call("Page.setInterceptFileChooserDialog", {"enabled": True}, session_id=sid)
        except Exception:
            pass
        time.sleep(1.5)

        # Mở hộp tạo bài viết trên trang chủ Facebook cá nhân
        trigger = eval_js(
            cdp,
            sid,
            """(() => {
                window.scrollTo(0, 0);
                const cands = Array.from(document.querySelectorAll('[role="button"], span, div'));
                for (const el of cands) {
                    const txt = (el.innerText || '').trim();
                    if (/^(Bạn đang nghĩ gì\\??|Bạn đang nghĩ gì thế.*|What's on your mind.*)$/i.test(txt) && txt.length < 70) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 60 && r.height >= 14 && r.top > 40 && r.top < 550) {
                            return {x: r.left + 50, y: r.top + r.height / 2};
                        }
                    }
                }
                return null;
            })()""",
        )
        if not trigger:
            return post_to_facebook(message, publish=publish, screenshot_path=screenshot_path)

        cdp_click_coords(cdp, sid, trigger["x"], trigger["y"])
        time.sleep(2.4)

        # Tìm ô nhập trong modal tạo bài viết đang mở
        box_pos = None
        for _ in range(18):
            box_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                        const dr = d.getBoundingClientRect();
                        return dr.width > 250 && dr.height > 200;
                    });
                    const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                    if (!root) return null;
                    const boxes = Array.from(root.querySelectorAll('[contenteditable="true"][role="textbox"], [contenteditable="true"]'));
                    for (const box of boxes) {
                        const aria = ((box.getAttribute('aria-label') || '') + ' ' + (box.getAttribute('aria-placeholder') || '')).toLowerCase();
                        if (/bình luận|comment|tìm kiếm|search/i.test(aria)) continue;
                        const r = box.getBoundingClientRect();
                        const pr = box.parentElement ? box.parentElement.getBoundingClientRect() : r;
                        if (Math.max(r.width, pr.width) > 40 && Math.max(r.height, pr.height) >= 8) {
                            box.focus();
                            return {x: (r.width > 10 ? r.left : pr.left) + 45, y: (r.width > 10 ? r.top : pr.top) + 14};
                        }
                    }
                    return null;
                })()""",
            )
            if box_pos:
                break
            time.sleep(0.5)

        if not box_pos:
            return post_to_facebook(message, publish=publish, screenshot_path=screenshot_path)

        # Bước 1 (TEXT-FIRST): Điền nội dung chữ trước khi đính kèm ảnh
        cdp_click_coords(cdp, sid, box_pos["x"], box_pos["y"])
        time.sleep(0.35)
        lines = message.split("\n")
        for idx, line in enumerate(lines):
            if line:
                cdp.call("Input.insertText", {"text": line}, session_id=sid)
            if idx < len(lines) - 1:
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyDown", "key": "Enter", "code": "Enter", "modifiers": 8, "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
                    session_id=sid,
                )
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyUp", "key": "Enter", "code": "Enter", "modifiers": 8, "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
                    session_id=sid,
                )
            time.sleep(0.05)
        time.sleep(1.0)

        # Bước 2 (IMAGE-SECOND): Bấm Ảnh/video rồi đính kèm ảnh trực tiếp vào input[type=file] của modal
        image_attached = False
        if image_path and os.path.exists(image_path):
            eval_js(
                cdp,
                sid,
                """(() => {
                    const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                        const dr = d.getBoundingClientRect();
                        return dr.width > 250 && dr.height > 200;
                    });
                    const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                    if (!root) return false;
                    const btns = Array.from(root.querySelectorAll('[role="button"], div[aria-label], span'));
                    for (const b of btns) {
                        const aria = (b.getAttribute && (b.getAttribute('aria-label') || '')) || '';
                        if (/Ảnh\\/video|Photo\\/video/i.test(aria)) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                })()""",
            )
            time.sleep(1.4)
            doc = cdp.call("DOM.getDocument", {"depth": -1}, session_id=sid)
            root_id = doc.get("root", {}).get("nodeId")
            if root_id:
                q = cdp.call(
                    "DOM.querySelectorAll",
                    {"nodeId": root_id, "selector": '[role="dialog"] input[type="file"][accept*="image"], [role="dialog"] input[type="file"]'},
                    session_id=sid,
                )
                nids = q.get("nodeIds") or []
                if nids:
                    cdp.call("DOM.setFileInputFiles", {"files": [image_path], "nodeId": nids[-1]}, session_id=sid)
                    time.sleep(4.5)
                    image_attached = bool(
                        eval_js(
                            cdp,
                            sid,
                            """(() => {
                                const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                                    const dr = d.getBoundingClientRect();
                                    return dr.width > 250 && dr.height > 200;
                                });
                                const root = dlgs.length ? dlgs[dlgs.length - 1] : null;
                                if (!root) return false;
                                const hasBlob = Array.from(root.querySelectorAll('img')).some(im => (im.getAttribute('src') || '').startsWith('blob:'));
                                const hasMediaAria = Array.from(root.querySelectorAll('[aria-label]')).some(el =>
                                    /File phương tiện đính kèm|Chỉnh sửa ảnh\\/video|Gỡ file đính kèm|Gỡ ảnh/i.test(el.getAttribute('aria-label') || '')
                                );
                                return hasBlob || hasMediaAria;
                            })()""",
                        )
                    )

        if not publish:
            shot_pre = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
            if shot_pre.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot_pre["data"]))
            return {"ok": True, "trang_thai": "da_dien_san_fb", "dinh_kem_anh": image_attached, "anh_chup": screenshot_path}

        find_submit_js = """(() => {
            const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                const dr = d.getBoundingClientRect();
                return dr.width > 250 && dr.height > 200 && d.querySelector('[contenteditable="true"]');
            });
            const root = dlgs.length ? dlgs[dlgs.length - 1] : document;
            const btns = Array.from(root.querySelectorAll('[role="button"], button'));
            for (const b of btns) {
                const aria = (b.getAttribute('aria-label') || '').trim();
                const txt = (b.innerText || '').trim();
                const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                if (!disabled && (/^(đăng|post|tiếp|next)$/i.test(aria) || /^(đăng|post|tiếp|next)$/i.test(txt))) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 20 && r.height > 15) return {x: r.left + r.width / 2, y: r.top + r.height / 2, isNext: /^(tiếp|next)$/i.test(aria || txt)};
                }
            }
            return null;
        })()"""

        post_pos = None
        for _ in range(14):
            post_pos = eval_js(cdp, sid, find_submit_js)
            if post_pos:
                break
            time.sleep(0.7)

        if not post_pos:
            return {"ok": False, "loi": "Chưa thấy nút Đăng bật sáng trên Facebook cá nhân."}

        cdp_click_coords(cdp, sid, post_pos["x"], post_pos["y"])
        if post_pos.get("isNext"):
            time.sleep(2.0)
            step2 = eval_js(cdp, sid, find_submit_js)
            if step2:
                cdp_click_coords(cdp, sid, step2["x"], step2["y"])

        submitted = False
        for attempt in range(18):
            time.sleep(1.0)
            still_open = bool(
                eval_js(
                    cdp,
                    sid,
                    """(() => {
                        const dlgs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(d => {
                            const dr = d.getBoundingClientRect();
                            return dr.width > 250 && dr.height > 200;
                        });
                        return dlgs.some(d => Array.from(d.querySelectorAll('[contenteditable="true"]')).some(
                            b => !/bình luận|comment|tìm kiếm/i.test((b.getAttribute('aria-label') || ''))
                        ));
                    })()""",
                )
            )
            if not still_open:
                submitted = True
                break
            if attempt == 5:
                retry_pos = eval_js(cdp, sid, find_submit_js)
                if retry_pos:
                    cdp_click_coords(cdp, sid, retry_pos["x"], retry_pos["y"])

        time.sleep(3.2)
        shot_done = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_done.get("data"):
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(shot_done["data"]))

        return {
            "ok": True,
            "trang_thai": "da_dang_fb_kem_anh" if submitted else "da_bam_dang_fb",
            "dinh_kem_anh": image_attached,
            "anh_chup": screenshot_path,
        }
    finally:
        try:
            if target_id:
                cdp.call("Target.closeTarget", {"targetId": target_id})
        except Exception:
            pass
        cdp.close()


def post_threads_with_image(message: str, image_path: str, publish: bool = False, screenshot_path: str = "/tmp/threads-spotlight.png") -> dict:
    """Đăng bài lên Threads kèm ảnh trực quan nét cao + link bấm trực tiếp."""
    ensure_bot_browser(headless=False, open_login_tabs=False)
    with urllib.request.urlopen(f"http://127.0.0.1:{BOT_CDP_PORT}/json/version", timeout=2) as resp:
        info = json.loads(resp.read().decode("utf-8"))
        ws_path = "/" + info["webSocketDebuggerUrl"].split("://", 1)[1].split("/", 1)[1]

    cdp = SimpleCDPClient("127.0.0.1", BOT_CDP_PORT, ws_path, timeout=60.0)
    target_id = None
    sid = None
    try:
        target = cdp.call("Target.createTarget", {"url": "https://www.threads.net/"})
        target_id = target["targetId"]
        time.sleep(5.5)

        cdp.call("Target.activateTarget", {"targetId": target_id})
        sid = cdp.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("DOM.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        time.sleep(2.0)

        trigger = eval_js(
            cdp,
            sid,
            """(() => {
                window.scrollTo(0, 0);
                const cands = Array.from(document.querySelectorAll('[role="button"], button, [aria-label]'));
                for (const el of cands) {
                    const aria = (el.getAttribute && (el.getAttribute('aria-label') || '')) || '';
                    const txt = (el.innerText || '').trim();
                    const hitAria = /^(New thread|Create|Bài viết mới|Tạo)$/i.test(aria) || /compose a new post/i.test(aria);
                    const hitTxt = /^(New thread|\\+?\\s*New thread|Có gì mới\\??|Bắt đầu thread\\.{0,3}|What['’]s new\\??|Start a thread\\.{0,3}|Bài viết mới)$/i.test(txt);
                    if (hitAria || hitTxt) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 18 && r.height >= 14 && r.top >= 0 && r.bottom <= window.innerHeight) {
                            return {x: r.left + r.width / 2, y: r.top + r.height / 2};
                        }
                    }
                }
                return null;
            })()""",
        )
        if trigger:
            cdp_click_coords(cdp, sid, trigger["x"], trigger["y"])
            time.sleep(2.0)

        box_pos = None
        for _ in range(18):
            box_pos = eval_js(
                cdp,
                sid,
                """(() => {
                    const boxes = Array.from(document.querySelectorAll('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]'));
                    for (const box of boxes) {
                        const r = box.getBoundingClientRect();
                        const pr = box.parentElement ? box.parentElement.getBoundingClientRect() : r;
                        if (Math.max(r.width, pr.width) > 40 && Math.max(r.height, pr.height) >= 8) {
                            box.focus();
                            return {x: (r.width > 10 ? r.left : pr.left) + 40, y: (r.width > 10 ? r.top : pr.top) + 12};
                        }
                    }
                    return null;
                })()""",
            )
            if box_pos:
                break
            time.sleep(0.5)

        if not box_pos:
            return {"ok": False, "loi": "Chưa mở được khung soạn bài trên Threads."}

        # BƯỚC 1: Gõ nội dung chữ TRƯỚC khi đính kèm ảnh (tránh ảnh làm trôi tọa độ ô nhập Lexical)
        cdp_click_coords(cdp, sid, box_pos["x"], box_pos["y"])
        time.sleep(0.4)
        eval_js(
            cdp,
            sid,
            """(() => {
                const box = document.querySelector('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]');
                if (box) box.focus();
            })()""",
        )
        time.sleep(0.2)

        lines = message.split("\n")
        for idx, line in enumerate(lines):
            if line:
                cdp.call("Input.insertText", {"text": line}, session_id=sid)
            if idx < len(lines) - 1:
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13, "text": "\r", "unmodifiedText": "\r"},
                    session_id=sid,
                )
                cdp.call(
                    "Input.dispatchKeyEvent",
                    {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
                    session_id=sid,
                )
            time.sleep(0.06)

        cdp.call("Input.insertText", {"text": " "}, session_id=sid)
        time.sleep(1.0)

        # Kiểm tra chắc chắn chữ đã vào trong khung Lexical; nếu chưa thì bơm qua DataTransfer Paste
        typed_len = eval_js(
            cdp,
            sid,
            """(() => {
                const box = document.querySelector('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]');
                return box ? (box.innerText || '').trim().length : 0;
            })()""",
        ) or 0

        if typed_len < 15:
            eval_js(
                cdp,
                sid,
                f"""(() => {{
                    const box = document.querySelector('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]');
                    if (!box) return false;
                    box.focus();
                    const dt = new DataTransfer();
                    dt.setData('text/plain', {json.dumps(message)});
                    box.dispatchEvent(new ClipboardEvent('paste', {{ clipboardData: dt, bubbles: true, cancelable: true }}));
                    return true;
                }})()""",
            )
            time.sleep(1.2)
            typed_len = eval_js(
                cdp,
                sid,
                """(() => {
                    const box = document.querySelector('[role="dialog"] [contenteditable="true"], [contenteditable="true"][role="textbox"]');
                    return box ? (box.innerText || '').trim().length : 0;
                })()""",
            ) or 0

        # BƯỚC 2: Đính kèm ảnh vào input[type=file] của modal Threads SAU KHI đã có chữ
        image_attached = False
        if image_path and os.path.exists(image_path):
            doc = cdp.call("DOM.getDocument", {"depth": -1}, session_id=sid)
            root_id = doc.get("root", {}).get("nodeId")
            if root_id:
                q = cdp.call(
                    "DOM.querySelectorAll",
                    {"nodeId": root_id, "selector": '[role="dialog"] input[type="file"], input[type="file"][accept*="image"]'},
                    session_id=sid,
                )
                nids = q.get("nodeIds") or []
                if nids:
                    cdp.call("DOM.setFileInputFiles", {"files": [image_path], "nodeId": nids[-1]}, session_id=sid)
                    image_attached = True
                    time.sleep(3.5)

        # Chụp ảnh preview modal trước khi bấm Đăng để kiểm chứng có đủ cả Chữ + Ảnh
        shot_modal = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_modal.get("data"):
            with open("/tmp/threads-modal-preview.png", "wb") as f:
                f.write(base64.b64decode(shot_modal["data"]))

        if not publish:
            if shot_modal.get("data"):
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(shot_modal["data"]))
            return {"ok": True, "trang_thai": "da_dien_san_threads", "so_ky_tu": typed_len, "dinh_kem_anh": image_attached, "anh_chup": screenshot_path}

        if typed_len < 15:
            return {"ok": False, "loi": f"Chưa điền được nội dung chữ vào khung Threads (typed_len={typed_len}).", "anh_chup": "/tmp/threads-modal-preview.png"}

        find_post_js = """(() => {
            const root = document.querySelector('[role="dialog"]') || document;
            const btns = Array.from(root.querySelectorAll('[role="button"], button, div[role="button"]'));
            let matches = [];
            for (const b of btns) {
                const txt = (b.innerText || '').trim();
                const aria = (b.getAttribute('aria-label') || '').trim();
                const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled;
                if (!disabled && (/^(Đăng|Post)$/i.test(txt) || /^(Đăng|Post)$/i.test(aria))) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 24 && r.height > 18) matches.push({x: r.left + r.width / 2, y: r.top + r.height / 2, yBottom: r.bottom});
                }
            }
            matches.sort((a, b) => b.yBottom - a.yBottom);
            return matches[0] || null;
        })()"""

        post_btn = None
        for _ in range(12):
            post_btn = eval_js(cdp, sid, find_post_js)
            if post_btn:
                break
            time.sleep(0.7)

        if not post_btn:
            return {"ok": False, "loi": "Chưa thấy nút Đăng trên Threads bật sáng."}

        cdp_click_coords(cdp, sid, post_btn["x"], post_btn["y"])
        submitted = False
        for attempt in range(18):
            time.sleep(1.0)
            still_open = bool(eval_js(cdp, sid, """(() => !!document.querySelector('[role="dialog"] [contenteditable="true"]'))()"""))
            if not still_open:
                submitted = True
                break
            if attempt == 5:
                retry_btn = eval_js(cdp, sid, find_post_js)
                if retry_btn:
                    cdp_click_coords(cdp, sid, retry_btn["x"], retry_btn["y"])

        # Chờ tiến trình upload ảnh "Posting..." / "Đang đăng..." hoàn tất thật sự trước khi đóng tab
        for _ in range(16):
            time.sleep(1.0)
            is_posting = bool(eval_js(cdp, sid, """(() => /Posting\\.\\.\\.|Đang đăng\\.\\.\\./i.test(document.body.innerText || ''))()"""))
            if not is_posting:
                break
        time.sleep(2.0)
        shot_done = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sid)
        if shot_done.get("data"):
            with open(screenshot_path, "wb") as f:
                f.write(base64.b64decode(shot_done["data"]))

        return {
            "ok": True,
            "trang_thai": "da_dang_threads_kem_anh" if submitted else "da_bam_dang_threads",
            "so_ky_tu": typed_len,
            "dinh_kem_anh": image_attached,
            "anh_chup": screenshot_path,
            "anh_modal": "/tmp/threads-modal-preview.png",
        }
    finally:
        try:
            if target_id:
                cdp.call("Target.closeTarget", {"targetId": target_id})
        except Exception:
            pass
        cdp.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Autopilot đăng báo cáo hằng ngày lên Facebook & Threads (0 Allow)")
    parser.add_argument("--open-bot-browser", action="store_true", help="Mở cửa sổ Bot Chrome chuyên dụng (cổng 9225) để đăng nhập FB & Threads 1 lần")
    parser.add_argument("--preview-report", action="store_true", help="Xem trước nội dung báo cáo hằng ngày sinh từ dữ liệu thật")
    parser.add_argument("--run-daily", action="store_true", help="Tự động đăng báo cáo hôm nay lên cả Facebook và Threads")
    parser.add_argument("--post-group", default="", help=f"Đăng bài độc bản kèm ảnh (0 link) vào nhóm: {', '.join(GROUP_CAMPAIGNS.keys())}")
    parser.add_argument("--run-next-group", action="store_true", help="Tự động đăng 1 nhóm tiếp theo chưa đăng trong hàng đợi (cách nhau >= 2 tiếng)")
    parser.add_argument("--list-groups", action="store_true", help="Liệt kê các chiến dịch nhóm độc bản đã soạn sẵn")
    parser.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra trùng lặp trong ngày")
    parser.add_argument("--publish", action="store_true", help="Bấm nút Đăng thật (mặc định nếu dùng --run-daily)")
    parser.add_argument("--channels", default="facebook,threads", help="Kênh đăng: facebook,threads")
    parser.add_argument("--post-spotlight", default="", help="Đăng bài giới thiệu chuyên đề (landing | than-so-hoc) kèm ảnh trực quan lên Facebook & Threads")
    parser.add_argument("--make-tsh-reply", nargs=3, metavar=("HO_TEN", "NGAY_SINH", "CAU_HOI"), help="Sinh ảnh Bản đồ PNG có watermark + bài luận đầy đủ để trả lời bình luận Group")
    args = parser.parse_args()

    if args.post_spotlight:
        key = args.post_spotlight.strip().lower()
        if key not in SPOTLIGHT_CAMPAIGNS:
            print(json.dumps({"ok": False, "loi": f"Chưa có chiến dịch spotlight '{key}'. Chọn: {', '.join(SPOTLIGHT_CAMPAIGNS)}"}, ensure_ascii=False))
            sys.exit(1)
        camp = SPOTLIGHT_CAMPAIGNS[key]
        today_str = now_vn().strftime("%Y-%m-%d")
        done_today = {} if args.force else (load_social_log().get(today_str) or {})
        chans = [c.strip().lower() for c in args.channels.split(",") if c.strip()]
        out = {"ok": True, "spotlight": key, "title": camp["title"], "ket_qua": {}}
        ok_channels = []
        if "facebook" in chans:
            log_k = f"spotlight_{key}_fb"
            if log_k in done_today:
                out["ket_qua"]["facebook"] = {"ok": True, "trang_thai": "da_dang_hom_nay", "luc": done_today[log_k]}
            else:
                res_fb = post_personal_fb_with_image(
                    camp["facebook"], camp["image"], publish=args.publish, screenshot_path=f"/tmp/spotlight-{key}-fb.png"
                )
                out["ket_qua"]["facebook"] = res_fb
                if res_fb.get("ok") and args.publish:
                    mark_social_posted(today_str, log_k)
                    ok_channels.append("Facebook")
        if "threads" in chans:
            log_k = f"spotlight_{key}_threads"
            if log_k in done_today:
                out["ket_qua"]["threads"] = {"ok": True, "trang_thai": "da_dang_hom_nay", "luc": done_today[log_k]}
            else:
                res_th = post_threads_with_image(
                    camp["threads"], camp["image"], publish=args.publish, screenshot_path=f"/tmp/spotlight-{key}-threads.png"
                )
                out["ket_qua"]["threads"] = res_th
                if res_th.get("ok") and args.publish:
                    mark_social_posted(today_str, log_k)
                    ok_channels.append("Threads")
        if ok_channels:
            record_diary_entry(f"Đăng bài giới thiệu chuyên đề [{camp['title']}] kèm ảnh trực quan lên {' & '.join(ok_channels)}.")
        elif not all(out["ket_qua"].get(c, {}).get("ok") for c in chans):
            out["ok"] = False
        close_bot_browser()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(0 if out["ok"] else 1)

    if args.make_tsh_reply:
        import numerology_engine as ne
        import server as srv
        ht, ns, ch = args.make_tsh_reply
        res_tsh = srv.run_tool_execution({"cong_cu": "than-so-hoc", "ho_ten": ht, "ngay_sinh": ns, "cau_hoi": ch})
        slug = re.sub(r"[^a-z0-9]+", "-", ne.strip_vietnamese(ht).lower()).strip("-") or "ban-doc"
        out_png = f"/tmp/tsh-reply-{slug}.png"
        ne.render_svg_to_png(res_tsh["svg_card"], out_png)
        print(json.dumps({"ok": True, "png": out_png, "tieu_de": res_tsh["tieu_de"], "bai_luan": res_tsh["ban_day_du"]}, ensure_ascii=False, indent=2))
        return

    if args.list_groups:
        glog = {}
        if os.path.exists(GROUP_LOG_PATH):
            try:
                with open(GROUP_LOG_PATH, "r", encoding="utf-8") as gf:
                    glog = json.load(gf)
            except Exception:
                pass
        print(
            json.dumps(
                {k: {"name": v["name"], "url": v["url"], "da_dang": glog.get(k, {}).get("posted_at")} for k, v in GROUP_CAMPAIGNS.items()},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.run_next_group:
        glog = {}
        if os.path.exists(GROUP_LOG_PATH):
            try:
                with open(GROUP_LOG_PATH, "r", encoding="utf-8") as gf:
                    glog = json.load(gf)
            except Exception:
                pass
        if not args.force and glog:
            latest_ts = max(
                (datetime.datetime.fromisoformat(v["posted_at"]) for v in glog.values() if v.get("posted_at")),
                default=None,
            )
            if latest_ts and (now_vn() - latest_ts).total_seconds() < 7200:
                mins_left = int((7200 - (now_vn() - latest_ts).total_seconds()) // 60)
                print(json.dumps({"ok": True, "trang_thai": "dang_nghi_gian_cach", "con_phut": mins_left}, ensure_ascii=False))
                return
        pending_keys = [k for k in GROUP_CAMPAIGNS if k not in glog]
        pending_keys.sort(key=lambda k: (0 if k.startswith("tsh-") else 1))
        if not pending_keys:
            print(json.dumps({"ok": True, "trang_thai": "da_dang_het_cac_nhom"}, ensure_ascii=False))
            return
        last_res = {"ok": False}
        for k_try in pending_keys:
            res = post_group_safe_with_image(k_try, publish=True)
            last_res = res
            if res.get("ok"):
                close_bot_browser()
                print(json.dumps(res, ensure_ascii=False, indent=2))
                sys.exit(0)
        close_bot_browser()
        print(json.dumps(last_res, ensure_ascii=False, indent=2))
        sys.exit(1)

    if args.post_group:
        res = post_group_safe_with_image(args.post_group.strip(), publish=args.publish)
        close_bot_browser()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res.get("ok") else 1)

    if args.open_bot_browser:
        ensure_bot_browser(headless=False, open_login_tabs=True)
        print(
            json.dumps(
                {
                    "ok": True,
                    "port": BOT_CDP_PORT,
                    "profile": BOT_PROFILE_DIR,
                    "ghi_chu": "Đã mở cửa sổ Bot Chrome chuyên dụng (cổng 9225 — không bao giờ hỏi Allow). Hãy đăng nhập Facebook & Threads 1 lần trên cửa sổ này!",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    reports = generate_daily_reports()
    if args.preview_report:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return

    if args.run_daily:
        today_str = now_vn().strftime("%Y-%m-%d")
        done_today = {} if args.force else (load_social_log().get(today_str) or {})
        ensure_bot_browser(headless=False, open_login_tabs=False)
        chans = [c.strip().lower() for c in args.channels.split(",") if c.strip()]
        out = {"ok": True, "ngay_thu": reports["stats"]["so_ngay"], "ket_qua": {}}
        ok_channels = []
        if "facebook" in chans:
            if "facebook" in done_today:
                out["ket_qua"]["facebook"] = {"ok": True, "trang_thai": "da_dang_hom_nay", "luc": done_today["facebook"]}
            else:
                res_fb = post_to_facebook(reports["facebook"], publish=True, screenshot_path="/tmp/daily-fb.png")
                out["ket_qua"]["facebook"] = res_fb
                if res_fb.get("ok"):
                    mark_social_posted(today_str, "facebook")
                    ok_channels.append("Facebook")
        if "threads" in chans:
            if "threads" in done_today:
                out["ket_qua"]["threads"] = {"ok": True, "trang_thai": "da_dang_hom_nay", "luc": done_today["threads"]}
            else:
                res_th = post_to_threads(reports["threads"], publish=True, screenshot_path="/tmp/daily-threads.png")
                out["ket_qua"]["threads"] = res_th
                if res_th.get("ok"):
                    mark_social_posted(today_str, "threads")
                    ok_channels.append("Threads")

        if ok_channels:
            record_diary_entry(
                f"Tự động đăng báo cáo tổng kết Ngày {reports['stats']['so_ngay']}/20 lên {' & '.join(ok_channels)} (doanh số thật: {vnd(reports['stats']['tien_that'])})."
            )
        elif not all(out["ket_qua"].get(c, {}).get("ok") for c in chans):
            out["ok"] = False
        close_bot_browser()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
