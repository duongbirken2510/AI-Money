#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Máy chủ Web & API cho Hệ thống AI Tự Kiếm Tiền (kiemtien.deta.vn).
Chạy độc lập bằng Python 3 chuẩn (ThreadingHTTPServer + SQLite).
"""
import datetime
import hashlib
import hmac
import html
import ipaddress
import json
import os
import re
import secrets
import socket
import sqlite3
import ssl
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import agent_worker
import micro_tools_engine
import numerology_engine
import temple_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DU_LIEU_PATH = os.path.join(BASE_DIR, "data", "du-lieu.json")
DB_PATH = os.path.join(BASE_DIR, "data", "deta.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))
DB_LOCK = threading.Lock()

THUC_DON = [
    {"ma": "banh-tieu", "ten": "cái bánh tiêu", "bieu": "🥯", "gia": 5000, "loai": "ung-ho"},
    {"ma": "chuoi-chien", "ten": "cái chuối chiên", "bieu": "🍌", "gia": 10000, "loai": "ung-ho"},
    {"ma": "ca-phe-den-da", "ten": "ly cà phê đen đá", "bieu": "☕", "gia": 20000, "loai": "ung-ho"},
    {"ma": "tra-sua", "ten": "ly trà sữa", "bieu": "🧋", "gia": 40000, "loai": "ung-ho"},
    {"ma": "pho", "ten": "tô phở", "bieu": "🍜", "gia": 60000, "loai": "ung-ho"},
    {"ma": "lau", "ten": "nồi lẩu cho cả team", "bieu": "🍲", "gia": 200000, "loai": "ung-ho"},
]

SAN_PHAM_BAN = {
    "ve-nhom": {"ten": "Vé phòng chat nhóm (30 ngày)", "bieu": "💬", "gia": 20000, "loai_ve": "nhom", "so_tin": 9999},
    "ve-rieng-30": {"ten": "Vé chat riêng với AI (30 tin)", "bieu": "🤖", "gia": 49000, "loai_ve": "rieng", "so_tin": 30},
    "ve-rieng-80": {"ten": "Vé chat riêng với AI (80 tin)", "bieu": "🤖", "gia": 99000, "loai_ve": "rieng", "so_tin": 80},
    "cham-diem-web": {"ten": "Báo cáo Chấm điểm & Sửa lỗi Web đầy đủ", "bieu": "⚡", "gia": 49000},
    "kham-kenh": {"ten": "Kế hoạch 30 ngày sửa kênh + 15 kịch bản", "bieu": "🔍", "gia": 39000},
    "ai-huong-dan": {"ten": "Trọn bộ hướng dẫn & Câu lệnh (Prompt) AI", "bieu": "🧭", "gia": 19000},
    "video-ai": {"ten": "Gói Kịch bản chi tiết & Đặt sản xuất Video AI", "bieu": "🎬", "gia": 49000},
    "tai-lieu": {"ten": "Tài liệu kỹ thuật: Cách dựng AI tự kiếm tiền (VIP)", "bieu": "📘", "gia": 29000},
    "tai-lieu-5k": {"ten": "Tài liệu kỹ thuật dựng AI (Ưu đãi Bánh tiêu mở hàng)", "bieu": "🥯", "gia": 5000},
    "banner-dinh": {"ten": "Đấu giá Banner Đỉnh trên Phòng Lab", "bieu": "👑", "gia": 10000},
    "tao-landing-page": {"ten": "Mã nguồn Landing Page 1 trang (.html hoàn chỉnh)", "bieu": "🚀", "gia": 29000},
    "cam-nang-tsh": {"ten": "Cẩm nang Thần Số Học 12 tháng & Sự nghiệp cá nhân hóa (Bản in A4)", "bieu": "📖", "gia": 15000},
    "tao-cv-ats": {"ten": "Hồ sơ CV Chuẩn ATS A4 & Thư Ứng Tuyển (Bản sạch xuất PDF)", "bieu": "📄", "gia": 15000},
    "lich-30-ngay": {"ten": "Lịch 30 ngày Bài đăng Bán hàng & Hook TikTok (File Excel .CSV)", "bieu": "📅", "gia": 19000},
    "coc-b2b-100k": {"ten": "Đặt cọc giữ lịch ưu tiên Thiết kế Trọn gói B2B 24h", "bieu": "💼", "gia": 100000},
    "tai-lieu-chatbot": {"ten": "Trọn bộ 12 Bài Thực Hành Dựng Chatbot & AI Chốt Đơn 24/7 (+ Template)", "bieu": "📘", "gia": 79000},
    "b2b-chatbot-290k": {"ten": "Done-For-You B2B: Thiết kế Bộ Não Chatbot Chốt Đơn 24/7 Cho Shop", "bieu": "🤖", "gia": 290000},
    "b2b-landing-490k": {"ten": "Done-For-You B2B: Thiết kế & Cài đặt Landing Page Chốt Đơn 24h", "bieu": "🚀", "gia": 490000},
    "b2b-combo-990k": {"ten": "Done-For-You B2B: Combo Landing Page + Pixel + 30 Ngày Nội Dung", "bieu": "👑", "gia": 990000},
    "ung-ho-chua-5k": {"ten": "Tiếp sức duy trì Không Gian Tĩnh Tâm & Thắp Hoa Đăng (5k)", "bieu": "🪷", "gia": 5000},
    "hoa-dang-hoang-kim": {"ten": "Thắp Đèn Hoa Đăng Hoàng Kim 30 Ngày & Tiếp sức máy chủ (10k)", "bieu": "🏮", "gia": 10000},
    "ung-ho-chua-20k": {"ten": "Thắp Đại Liên Hoa Đăng 30 Ngày & Tiếp sức máy chủ (20k)", "bieu": "🌕", "gia": 20000},
}

BANNER_BAD_WORDS = [
    "tài xỉu", "tai xiu", "cờ bạc", "co bac", "casino", "nhà cái", "nha cai",
    "lô đề", "lo de", "cá độ", "ca do", "kubet", "jun88", "hi88", "789bet",
    "new88", "f8bet", "shbet", "sex", "18+", "porn", "xxx", "vay nóng", "lừa đảo",
]


def current_week_key() -> str:
    return now_vn().strftime("%G-W%V")


def check_banner_safety(url: str, tieu_de: str, mo_ta: str) -> tuple[bool, str, str]:
    u = (url or "").strip()
    if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", u, re.I):
        return False, "Link đích phải bắt đầu bằng https:// hoặc http:// hợp lệ.", ""
    parsed_u = urllib.parse.urlparse(u)
    domain = (parsed_u.netloc or "").lower().lstrip("www.")
    if not domain or "." not in domain:
        return False, "Tên miền website/kênh không hợp lệ.", ""
    td = (tieu_de or "").strip()
    if len(td) < 3:
        return False, "Tên hiển thị trên Banner cần tối thiểu 3 ký tự.", ""
    combined = f"{u} {td} {mo_ta}".lower()
    for bw in BANNER_BAD_WORDS:
        if bw in combined:
            return False, "Nội dung Banner chứa từ khóa bị hạn chế (cờ bạc / 18+ / vi phạm).", ""
    return True, "", domain


def now_vn() -> datetime.datetime:
    return datetime.datetime.now(VN_TZ)


RATE_LIMIT_LOCK = threading.Lock()
_RATE_BUCKETS: dict[str, list[float]] = {}
_AUTH_FAILURES: dict[str, dict] = {}


def get_real_client_ip(handler) -> str:
    """Lấy IP thật của client: chỉ tin cậy CF-Connecting-IP khi kết nối TCP đến từ tiến trình cloudflared nội bộ (127.0.0.1/::1)."""
    peer_ip = (handler.client_address[0] if getattr(handler, "client_address", None) else "0.0.0.0").strip()
    if peer_ip in ("127.0.0.1", "::1", "localhost"):
        cf_ip = (handler.headers.get("CF-Connecting-IP") or "").strip()
        if cf_ip and len(cf_ip) <= 45 and re.match(r"^[0-9a-fA-F:.]+$", cf_ip):
            return cf_ip
    return peer_ip or "0.0.0.0"


def check_rate_limit(ip: str, bucket: str, max_req: int, window_sec: float = 60.0) -> bool:
    """Bộ giới hạn tốc độ truy cập (Sliding Window Rate Limiter) theo IP & nhóm API."""
    if ip in ("127.0.0.1", "::1", "localhost"):
        return True
    now_ts = time.time()
    key = f"{bucket}:{ip}"
    with RATE_LIMIT_LOCK:
        if len(_RATE_BUCKETS) > 4000:
            cutoff_all = now_ts - 180.0
            stale = [k for k, v in _RATE_BUCKETS.items() if not v or v[-1] < cutoff_all]
            for k in stale:
                _RATE_BUCKETS.pop(k, None)
        arr = _RATE_BUCKETS.get(key, [])
        cutoff = now_ts - window_sec
        arr = [t for t in arr if t > cutoff]
        if len(arr) >= max_req:
            _RATE_BUCKETS[key] = arr
            return False
        arr.append(now_ts)
        _RATE_BUCKETS[key] = arr
        return True


def is_auth_locked(ip: str) -> bool:
    """Kiểm tra xem IP có đang bị khóa tạm thời do dò mật khẩu Admin / Webhook sai quá 5 lần không."""
    now_ts = time.time()
    with RATE_LIMIT_LOCK:
        st = _AUTH_FAILURES.get(ip)
        if not st:
            return False
        if st.get("locked_until", 0) > now_ts:
            return True
        if now_ts - st.get("first_ts", 0) > 600:
            _AUTH_FAILURES.pop(ip, None)
        return False


def record_auth_failure(ip: str) -> None:
    """Ghi nhận 1 lần nhập sai khóa Admin/Webhook; sai >= 5 lần trong 10 phút sẽ khóa IP trong 15 phút."""
    now_ts = time.time()
    with RATE_LIMIT_LOCK:
        st = _AUTH_FAILURES.get(ip)
        if not st or (now_ts - st.get("first_ts", 0) > 600):
            st = {"count": 1, "first_ts": now_ts, "locked_until": 0.0}
        else:
            st["count"] = int(st.get("count", 0)) + 1
            if st["count"] >= 5:
                st["locked_until"] = now_ts + 900.0  # Khóa 15 phút
        _AUTH_FAILURES[ip] = st


def clear_auth_failures(ip: str) -> None:
    with RATE_LIMIT_LOCK:
        _AUTH_FAILURES.pop(ip, None)


def is_valid_admin_key(provided: str, cfg: dict) -> bool:
    """So sánh khóa quản trị an toàn chống timing attack, bắt buộc lấy từ config.json."""
    expected = (cfg.get("admin_key") or "").strip()
    cand = (provided or "").strip()
    if not expected or not cand or expected in ("CHANGE_ME_STRONG_ADMIN_KEY", "admin", "123456"):
        return False
    return hmac.compare_digest(cand.encode("utf-8"), expected.encode("utf-8"))


def is_safe_external_url(url: str) -> bool:
    """Chặn SSRF: chỉ cho phép kết nối tới địa chỉ HTTP/HTTPS công khai cổng 80/443, cấm toàn bộ dải IP nội bộ / loopback / link-local / CGNAT."""
    try:
        u_clean = (url or "").strip()
        if not u_clean or u_clean.startswith("-") or len(u_clean) > 500 or any(c in u_clean for c in ("\r", "\n", "\x00", "@")):
            return False
        parsed = urllib.parse.urlparse(u_clean)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.username or parsed.password:
            return False
        if parsed.port and parsed.port not in (80, 443):
            return False
        host = (parsed.hostname or "").strip().lower().rstrip(".")
        if not host or "." not in host:
            return False
        if host in ("localhost", "kiemtien.deta.vn", "metadata.google.internal") or host.endswith((".local", ".internal", ".localhost", ".lan", ".arpa")):
            return False
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        if not infos:
            return False
        cgnat_net = ipaddress.ip_network("100.64.0.0/10")
        for info in infos:
            ip_str = info[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if getattr(ip_obj, "ipv4_mapped", None):
                ip_obj = ip_obj.ipv4_mapped
            if (
                ip_obj.is_loopback
                or ip_obj.is_private
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_obj.is_unspecified
                or (isinstance(ip_obj, ipaddress.IPv4Address) and ip_obj in cgnat_net)
            ):
                return False
        return True
    except Exception:
        return False


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_safe_external_url(newurl):
            raise urllib.error.URLError("Blocked unsafe redirect target")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS viewers (
                ma TEXT PRIMARY KEY,
                ngay TEXT,
                last_seen REAL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS orders (
                ma TEXT PRIMARY KEY,
                k TEXT,
                loai TEXT,
                mon_ma TEXT,
                mon_ten TEXT,
                bieu TEXT,
                so_luong INTEGER,
                so_tien INTEGER,
                ten TEXT,
                loi_nhan TEXT,
                tra_loi TEXT,
                trang_thai TEXT,
                ve_token TEXT,
                nguon TEXT,
                luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ten TEXT,
                noi_dung TEXT,
                da_tra_loi INTEGER DEFAULT 0,
                luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loai TEXT,
                kenh TEXT,
                luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loai TEXT,
                nguon TEXT,
                luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                token TEXT PRIMARY KEY,
                ma_don TEXT,
                loai TEXT,
                ten TEXT,
                con_tin INTEGER,
                het_han TEXT,
                luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ten TEXT,
                chu TEXT,
                ai INTEGER DEFAULT 0,
                t TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT,
                chu TEXT,
                ai INTEGER DEFAULT 0,
                t TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS webhook_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nguon TEXT,
                tx_ref TEXT,
                so_tien INTEGER,
                noi_dung TEXT,
                ket_qua TEXT,
                luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS free_chat_trials (
                token TEXT PRIMARY KEY,
                ip_hash TEXT,
                con_tin INTEGER DEFAULT 2,
                tao_luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS banners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                url TEXT,
                tieu_de TEXT,
                mo_ta TEXT,
                bieu TEXT DEFAULT '🚀',
                tong_tien INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                tuan TEXT,
                cap_nhat TEXT,
                UNIQUE(domain, tuan)
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS landing_previews (
                id TEXT PRIMARY KEY,
                ten_sp TEXT,
                html_clean TEXT,
                tao_luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS deliverables (
                id TEXT PRIMARY KEY,
                loai TEXT,
                slug TEXT,
                html_clean TEXT,
                csv_clean TEXT,
                tao_luc TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS pageviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_ma TEXT,
                ngay TEXT,
                gio TEXT,
                trang TEXT,
                kenh TEXT,
                chi_tiet_nguon TEXT,
                referer TEXT,
                thiet_bi TEXT,
                luc TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_pageviews_ngay ON pageviews(ngay)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pageviews_trang ON pageviews(trang)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_viewers_ngay ON viewers(ngay)")
        c.execute(
            """CREATE TABLE IF NOT EXISTS b2b_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ho_ten TEXT,
                lien_he TEXT,
                goi TEXT,
                link_hien_tai TEXT,
                ghi_chu TEXT,
                nguon TEXT,
                trang_thai TEXT DEFAULT 'moi',
                tao_luc TEXT
            )"""
        )
        for alter_sql in (
            "ALTER TABLE orders ADD COLUMN du_lieu_kem TEXT DEFAULT ''",
            "ALTER TABLE banners ADD COLUMN anh_banner TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN first_ngay TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN first_seen REAL DEFAULT 0",
            "ALTER TABLE viewers ADD COLUMN kenh TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN chi_tiet_nguon TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN trang_dau TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN trang_cuoi TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN thiet_bi TEXT DEFAULT ''",
            "ALTER TABLE viewers ADD COLUMN so_trang INTEGER DEFAULT 1",
        ):
            try:
                c.execute(alter_sql)
            except sqlite3.OperationalError:
                pass
        # Khởi tạo tin nhắn chào mừng trong phòng chat nhóm nếu chưa có
        c.execute("SELECT COUNT(*) FROM group_messages")
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO group_messages (ten, chu, ai, t) VALUES (?, ?, 1, ?)",
                (
                    "🤖 AI",
                    "Chào mừng mọi người đến với kiemtien.deta.vn! Tôi có 20 ngày để tự kiếm đồng tiền thật đầu tiên (>0đ). Gõ @AI trong phòng này để trò chuyện với tôi nhé!",
                    now_vn().isoformat(timespec="seconds"),
                ),
            )
        conn.commit()
        conn.close()


PAGE_DISPLAY_NAMES = {
    "/": "🏠 Trang chủ Nhật ký 20 ngày (/)",
    "/cong-cu/than-so-hoc": "🔮 Thần Số Học Pythagoras (/cong-cu/than-so-hoc)",
    "/cong-cu/tao-landing-page": "🚀 AI Tự Code Landing Page (/cong-cu/tao-landing-page)",
    "/cong-cu/tao-cv-ats": "📄 AI Thiết Kế CV Chuẩn ATS A4 (/cong-cu/tao-cv-ats)",
    "/cong-cu/lich-30-ngay": "📅 AI Lập Lịch 30 Ngày Excel .CSV (/cong-cu/lich-30-ngay)",
    "/cong-cu/chatbot-chot-don": "🤖 AI Tạo Prompt & Demo Chatbot Chốt Đơn (/cong-cu/chatbot-chot-don)",
    "/cong-cu/cham-diem-web": "⚡ Chấm Điểm Web Bán Hàng (/cong-cu/cham-diem-web)",
    "/cong-cu/kham-kenh": "🔍 Khám Kênh TikTok / Shopee (/cong-cu/kham-kenh)",
    "/cong-cu/ai-huong-dan": "🧭 Soạn Câu Lệnh Prompt AI (/cong-cu/ai-huong-dan)",
    "/cong-cu/video-ai": "🎬 Kịch Bản Video Ngắn 30s (/cong-cu/video-ai)",
    "/tai-lieu/tao-ai": "📘 Tài Liệu Kỹ Thuật Dựng AI (/tai-lieu/tao-ai)",
    "/tai-lieu/chatbot-chot-don": "📘 Cẩm Nang 12 Bài Dựng Chatbot Chốt Đơn 24/7 (/tai-lieu/chatbot-chot-don)",
    "/chua-online": "🪷 Liên Hoa Các — Chùa Online 3D & Ao Sen Hoa Đăng (/chua-online)",
    "/mau-landing/van-son-tra": "🍃 Showcase Vân Sơn Trà (/mau-landing/van-son-tra/)",
    "/mau-landing/detaspeak-ai": "🎙️ Showcase DetaSpeak AI (/mau-landing/detaspeak-ai/)",
    "/dich-vu/thiet-ke-tron-goi": "💼 Dịch Vụ Thiết Kế Trọn Gói B2B (/dich-vu/thiet-ke-tron-goi)",
}

EVENT_TO_PAGE_PATH = {
    "cong-cu-tai-lieu": "/tai-lieu/tao-ai",
    "cong-cu-than-so-hoc": "/cong-cu/than-so-hoc",
    "cong-cu-tao-landing-page": "/cong-cu/tao-landing-page",
    "cong-cu-tao-cv-ats": "/cong-cu/tao-cv-ats",
    "cong-cu-lich-30-ngay": "/cong-cu/lich-30-ngay",
    "cong-cu-chatbot-chot-don": "/cong-cu/chatbot-chot-don",
    "cong-cu-cham-diem-web": "/cong-cu/cham-diem-web",
    "cong-cu-kham-kenh": "/cong-cu/kham-kenh",
    "cong-cu-ai-huong-dan": "/cong-cu/ai-huong-dan",
    "cong-cu-video-ai": "/cong-cu/video-ai",
    "b2b-lead": "/dich-vu/thiet-ke-tron-goi",
}


def classify_traffic_source(utm_nguon: str, referer: str, ua: str) -> tuple[str, str, str, bool]:
    """Phân loại chính xác nguồn traffic (kể cả khi App Facebook/Threads/Zalo trên điện thoại ẩn Referer)."""
    ua_s = (ua or "").strip()
    ua_low = ua_s.lower()

    # 1. Nhận diện Thiết bị & Môi trường mở trang
    is_mobile = bool(re.search(r"mobi|android|iphone|ipad|ipod", ua_low))
    if "iphone" in ua_low or "ipad" in ua_low:
        os_lbl = "iPhone/iOS"
    elif "android" in ua_low:
        os_lbl = "Android"
    elif "macintosh" in ua_low or "mac os" in ua_low:
        os_lbl = "Mac"
    elif "windows" in ua_low:
        os_lbl = "Windows"
    else:
        os_lbl = "Linux/Khác"

    app_lbl = ""
    if "barcelona" in ua_low or "threads" in ua_low:
        app_lbl = "Threads App"
    elif any(x in ua_low for x in ("fban", "fbav", "fb_iab", "fbios")):
        app_lbl = "FB App"
    elif "zalo" in ua_low:
        app_lbl = "Zalo App"
    elif any(x in ua_low for x in ("tiktok", "musical_ly", "bytedance")):
        app_lbl = "TikTok App"
    elif "telegram" in ua_low:
        app_lbl = "Telegram"

    dev_prefix = "Mobile" if is_mobile else "Desktop"
    thiet_bi = f"{dev_prefix} ({os_lbl}" + (f" · {app_lbl})" if app_lbl else ")")

    # 2. Phân tích UTM / ?nguon= và Referer
    utm_raw = (utm_nguon or "").strip()[:60]
    utm_low = utm_raw.lower()
    ref_raw = (referer or "").strip()[:240]
    ref_host = ""
    if ref_raw:
        try:
            ref_host = (urllib.parse.urlparse(ref_raw).hostname or "").lower().lstrip("www.")
        except Exception:
            ref_host = ""

    is_internal_ref = ref_host in ("kiemtien.deta.vn", "localhost", "127.0.0.1")
    is_internal_utm = (
        utm_low in ("", "kiemtien", "web", "trang-chu")
        or utm_low.startswith("huong-dan-")
        or utm_low.startswith("seo-")
    )

    # Ưu tiên 1: Có gắn mã ?nguon= / ?utm_source= từ chiến dịch bên ngoài
    if utm_raw and not is_internal_utm:
        if "fb" in utm_low or "facebook" in utm_low:
            return "Facebook", f"Link chiến dịch ({utm_raw})", thiet_bi, False
        if "thread" in utm_low:
            return "Threads", f"Link chiến dịch ({utm_raw})", thiet_bi, False
        if "zalo" in utm_low:
            return "Zalo", f"Link chiến dịch ({utm_raw})", thiet_bi, False
        if "tik" in utm_low:
            return "TikTok", f"Link chiến dịch ({utm_raw})", thiet_bi, False
        if any(w in utm_low for w in ("ban-be", "chia-se", "share")):
            return "Bạn bè chia sẻ", f"Nút mời bạn bè ({utm_raw})", thiet_bi, False
        if "google" in utm_low:
            return "Google SEO", f"UTM ({utm_raw})", thiet_bi, False
        return "Link gắn mã riêng", utm_raw, thiet_bi, False

    # Ưu tiên 2: HTTP Referer từ tên miền bên ngoài
    if ref_host and not is_internal_ref:
        if any(d in ref_host for d in ("facebook.com", "fb.com", "fb.me", "messenger.com")):
            return "Facebook", f"Referer ({ref_host})", thiet_bi, False
        if any(d in ref_host for d in ("threads.net", "threads.com")):
            return "Threads", f"Referer ({ref_host})", thiet_bi, False
        if "google." in ref_host:
            return "Google SEO", f"Tìm kiếm ({ref_host})", thiet_bi, False
        if any(d in ref_host for d in ("bing.com", "coccoc.com", "duckduckgo.com", "yahoo.com")):
            return "Tìm kiếm khác", f"Tìm kiếm ({ref_host})", thiet_bi, False
        if "zalo.me" in ref_host:
            return "Zalo", f"Referer ({ref_host})", thiet_bi, False
        if "tiktok.com" in ref_host:
            return "TikTok", f"Referer ({ref_host})", thiet_bi, False
        if any(d in ref_host for d in ("t.co", "x.com", "twitter.com")):
            return "X / Twitter", f"Referer ({ref_host})", thiet_bi, False
        if any(d in ref_host for d in ("youtube.com", "youtu.be")):
            return "YouTube", f"Referer ({ref_host})", thiet_bi, False
        return "Web giới thiệu", ref_host, thiet_bi, False

    # Ưu tiên 3: Chữ ký trình duyệt nhúng trong App mạng xã hội (khi Referer bị xóa hoặc đang chuyển trang trong App)
    if not is_internal_ref:
        if app_lbl == "Threads App":
            return "Threads", "App Threads trên điện thoại", thiet_bi, False
        if app_lbl == "FB App":
            return "Facebook", "App Facebook / Messenger", thiet_bi, False
        if app_lbl == "Zalo App":
            return "Zalo", "App Zalo trên điện thoại", thiet_bi, False
        if app_lbl == "TikTok App":
            return "TikTok", "App TikTok trên điện thoại", thiet_bi, False
        if app_lbl == "Telegram":
            return "Telegram", "App Telegram", thiet_bi, False

    # Ưu tiên 4: Điều hướng nội bộ giữa các trang trong kiemtien.deta.vn
    if is_internal_ref or (utm_raw and is_internal_utm):
        return "Trực tiếp / Gõ link", f"Chuyển trang nội bộ ({utm_raw or ref_host})", thiet_bi, True

    # Ưu tiên 5: Gõ trực tiếp tên miền từ Watermark ảnh Thần số học / Bookmark
    return "Trực tiếp / Gõ từ Ảnh", "Gõ thẳng tên miền hoặc mở từ ảnh Watermark", thiet_bi, False


def build_traffic_analytics(conn: sqlite3.Connection) -> dict:
    """Tổng hợp số liệu Bảng đo Traffic đa chiều cho trang Quản trị /admin."""
    c = conn.cursor()
    now_dt = now_vn()
    today_str = now_dt.strftime("%Y-%m-%d")
    yesterday_str = (now_dt.date() - datetime.timedelta(days=1)).isoformat()
    ts_now = time.time()

    c.execute("SELECT COUNT(*) FROM viewers WHERE last_seen > ?", (ts_now - 90,))
    dang_online = int(c.fetchone()[0] or 0)
    c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (today_str,))
    hom_nay_khach = int(c.fetchone()[0] or 0)
    c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (yesterday_str,))
    hom_qua_khach = int(c.fetchone()[0] or 0)
    c.execute("SELECT COUNT(*) FROM viewers")
    tong_khach = int(c.fetchone()[0] or 0)

    c.execute("SELECT COUNT(*) FROM pageviews WHERE ngay = ?", (today_str,))
    hom_nay_pv = int(c.fetchone()[0] or 0)
    c.execute("SELECT COUNT(*) FROM pageviews")
    tong_pv = int(c.fetchone()[0] or 0)

    c.execute("SELECT COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%'")
    tong_chay_cc = int(c.fetchone()[0] or 0)
    c.execute("SELECT COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%' AND SUBSTR(luc, 1, 10) = ?", (today_str,))
    hom_nay_chay_cc = int(c.fetchone()[0] or 0)

    c.execute("SELECT COUNT(*) FROM viewers WHERE COALESCE(kenh, '') = ''")
    khach_lich_su_chua_gan = int(c.fetchone()[0] or 0)

    # 1. Phân bổ nguồn Kênh (từ khách đã định danh nguồn + pageviews)
    c.execute(
        "SELECT kenh, COUNT(*) AS cnt FROM viewers WHERE COALESCE(kenh, '') != '' GROUP BY kenh ORDER BY cnt DESC"
    )
    kenh_viewer_rows = c.fetchall()
    c.execute(
        "SELECT kenh, COUNT(*) AS cnt FROM pageviews WHERE COALESCE(kenh, '') != '' GROUP BY kenh"
    )
    pv_by_kenh = {r[0]: int(r[1]) for r in c.fetchall()}

    tracked_total = sum(int(r[1]) for r in kenh_viewer_rows)
    theo_kenh = []
    for k_name, cnt in kenh_viewer_rows:
        cnt_i = int(cnt)
        pct = round((cnt_i * 100.0 / tracked_total), 1) if tracked_total > 0 else 0.0
        theo_kenh.append(
            {
                "kenh": k_name,
                "so_khach": cnt_i,
                "luot_xem": pv_by_kenh.get(k_name, cnt_i),
                "ty_le": pct,
            }
        )

    # 2. Phân bổ Thiết bị (Mobile vs Desktop)
    c.execute(
        "SELECT CASE WHEN thiet_bi LIKE 'Mobile%' THEN 'Mobile' WHEN thiet_bi LIKE 'Desktop%' THEN 'Desktop' ELSE '' END AS loai_tb, COUNT(*) "
        "FROM viewers WHERE COALESCE(thiet_bi, '') != '' GROUP BY loai_tb"
    )
    tb_map = {r[0]: int(r[1]) for r in c.fetchall() if r[0]}
    tb_total = tb_map.get("Mobile", 0) + tb_map.get("Desktop", 0)
    theo_thiet_bi = {
        "mobile": tb_map.get("Mobile", 0),
        "desktop": tb_map.get("Desktop", 0),
        "mobile_pct": round(tb_map.get("Mobile", 0) * 100.0 / tb_total, 1) if tb_total > 0 else 0.0,
        "desktop_pct": round(tb_map.get("Desktop", 0) * 100.0 / tb_total, 1) if tb_total > 0 else 0.0,
    }

    # 3. Biểu đồ theo Ngày (14 ngày gần nhất)
    c.execute("SELECT ngay, COUNT(*) FROM viewers WHERE COALESCE(ngay, '') != '' GROUP BY ngay")
    v_by_day = {r[0]: int(r[1]) for r in c.fetchall()}
    c.execute("SELECT ngay, COUNT(*) FROM pageviews WHERE COALESCE(ngay, '') != '' GROUP BY ngay")
    pv_by_day = {r[0]: int(r[1]) for r in c.fetchall()}
    c.execute("SELECT SUBSTR(luc, 1, 10) AS d, COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%' GROUP BY d")
    ev_by_day = {r[0]: int(r[1]) for r in c.fetchall() if r[0]}

    all_days = sorted(set(v_by_day.keys()) | set(pv_by_day.keys()) | set(ev_by_day.keys()) | {today_str})[-14:]
    theo_ngay = []
    for d_str in all_days:
        theo_ngay.append(
            {
                "ngay": d_str,
                "khach": v_by_day.get(d_str, 0),
                "luot_xem": pv_by_day.get(d_str, 0),
                "chay_cong_cu": ev_by_day.get(d_str, 0),
            }
        )

    # 4. Top Trang Đích & Công Cụ Hút Traffic Nhất (gộp cả Pageviews + Lượt chạy AI thật)
    c.execute("SELECT trang, COUNT(*) AS cnt, COUNT(DISTINCT viewer_ma) AS uv FROM pageviews GROUP BY trang")
    page_stats = {}
    for tr, cnt, uv in c.fetchall():
        p_norm = (tr or "/").rstrip("/") or "/"
        st = page_stats.setdefault(p_norm, {"luot_xem": 0, "khach_rieng": 0, "luot_chay": 0})
        st["luot_xem"] += int(cnt)
        st["khach_rieng"] += int(uv)

    c.execute("SELECT loai, COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%' GROUP BY loai")
    for loai_ev, cnt_ev in c.fetchall():
        mapped_p = EVENT_TO_PAGE_PATH.get(loai_ev, "/" + loai_ev)
        st = page_stats.setdefault(mapped_p, {"luot_xem": 0, "khach_rieng": 0, "luot_chay": 0})
        st["luot_chay"] += int(cnt_ev)

    top_trang = []
    for p_key, st in page_stats.items():
        if p_key.startswith("/admin"):
            continue
        label = PAGE_DISPLAY_NAMES.get(p_key)
        if not label:
            if p_key.startswith("/huong-dan/"):
                label = f"📑 Bài SEO: {p_key.split('/huong-dan/', 1)[1]}"
            else:
                label = p_key
        top_trang.append(
            {
                "trang": p_key,
                "ten": label,
                "luot_xem": st["luot_xem"],
                "khach_rieng": st["khach_rieng"],
                "luot_chay": st["luot_chay"],
                "diem_xep_hang": st["luot_xem"] + st["luot_chay"] * 2,
            }
        )
    top_trang.sort(key=lambda x: (x["diem_xep_hang"], x["luot_xem"], x["luot_chay"]), reverse=True)

    # 5. Chi tiết chiến dịch / nguồn con nổi bật
    c.execute(
        "SELECT kenh, chi_tiet_nguon, COUNT(*) AS cnt FROM pageviews "
        "WHERE COALESCE(chi_tiet_nguon, '') != '' AND chi_tiet_nguon NOT LIKE 'Chuyển trang nội bộ%' "
        "GROUP BY kenh, chi_tiet_nguon ORDER BY cnt DESC LIMIT 12"
    )
    top_chien_dich = [{"kenh": r[0], "chi_tiet": r[1], "luot": int(r[2])} for r in c.fetchall()]

    # 6. Luồng 25 lượt khách thật vào web gần nhất (Real-time Live Stream)
    c.execute(
        "SELECT luc, kenh, chi_tiet_nguon, trang, thiet_bi, referer, viewer_ma "
        "FROM pageviews ORDER BY id DESC LIMIT 25"
    )
    luot_gan_nhat = []
    for r in c.fetchall():
        luot_gan_nhat.append(
            {
                "luc": r[0] or "",
                "kenh": r[1] or "Trực tiếp",
                "chi_tiet": r[2] or "",
                "trang": r[3] or "/",
                "thiet_bi": r[4] or "",
                "referer": r[5] or "",
                "ma_ngan": (r[6] or "")[:6],
            }
        )

    return {
        "dang_online": dang_online,
        "hom_nay_khach": hom_nay_khach,
        "hom_qua_khach": hom_qua_khach,
        "tong_khach": tong_khach,
        "hom_nay_pv": hom_nay_pv,
        "tong_pv": tong_pv,
        "hom_nay_chay_cong_cu": hom_nay_chay_cc,
        "tong_chay_cong_cu": tong_chay_cc,
        "khach_lich_su_chua_gan": khach_lich_su_chua_gan,
        "theo_kenh": theo_kenh,
        "theo_thiet_bi": theo_thiet_bi,
        "theo_ngay": theo_ngay,
        "top_trang": top_trang[:15],
        "top_chien_dich": top_chien_dich,
        "luot_gan_nhat": luot_gan_nhat,
    }


def make_vietqr_url(so_tien: int, noi_dung: str) -> str:
    cfg = agent_worker.load_config()
    bank = cfg.get("bank") or {}
    bank_id = urllib.parse.quote((bank.get("bank_id") or "MB").strip())
    acc_no = urllib.parse.quote((bank.get("account_no") or "YOUR_ACCOUNT_NO").strip())
    tpl = urllib.parse.quote((bank.get("template") or "compact2").strip())
    acc_name = urllib.parse.quote((bank.get("account_name") or "YOUR_ACCOUNT_NAME").strip())
    info = urllib.parse.quote(noi_dung)
    return f"https://img.vietqr.io/image/{bank_id}-{acc_no}-{tpl}.png?amount={int(so_tien)}&addInfo={info}&accountName={acc_name}"


def auto_render_customer_banner_async(banner_id: int, domain: str, url: str, tieu_de: str, mo_ta: str, bieu: str) -> None:
    """Tự động chụp preview trang đích của khách & kết xuất Banner 1200x320 WebP ngay khi khách thanh toán xong."""
    def _worker():
        try:
            from PIL import Image
            assets_dir = os.path.join(PUBLIC_DIR, "mau-landing", "assets")
            os.makedirs(assets_dir, exist_ok=True)
            site_shot = f"/tmp/deta-cust-site-{banner_id}.png"
            has_shot = False
            is_safe_public = is_safe_external_url(url)
            if is_safe_public:
                try:
                    subprocess.run(
                        [
                            "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
                            "--window-size=1280,860", "--hide-scrollbars", "--virtual-time-budget=3500",
                            f"--screenshot={site_shot}", url,
                        ],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=14, check=True,
                    )
                    has_shot = os.path.exists(site_shot) and os.path.getsize(site_shot) > 8000
                except Exception:
                    has_shot = False

            esc = html.escape
            right_inner = (
                f'<img src="file://{site_shot}" style="width:100%;height:100%;object-fit:cover;object-position:top center;display:block">'
                if has_shot
                else (
                    f'<div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;'
                    f'background:linear-gradient(135deg,#0F172A,#1E293B);color:#FDE68A;padding:20px;text-align:center">'
                    f'<div style="font-size:64px;margin-bottom:8px">{esc(bieu)}</div>'
                    f'<div style="font-size:22px;font-weight:900;color:#FFF">{esc(domain)}</div></div>'
                )
            )
            desc_clean = mo_ta.strip() or f"Khám phá ngay sản phẩm & dịch vụ nổi bật tại {domain}"
            tpl = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><style>
              *{{box-sizing:border-box;margin:0;padding:0}}
              body{{width:1200px;height:320px;overflow:hidden;font-family:"Noto Sans","DejaVu Sans",system-ui,sans-serif;
                background:linear-gradient(125deg,#071326 0%,#0E294B 54%,#064E3B 100%);
                color:#FFF;display:flex;align-items:center;justify-content:space-between;padding:26px 40px;position:relative}}
              .left{{max-width:695px;z-index:2}}
              .kicker{{display:inline-flex;align-items:center;gap:8px;background:rgba(245,158,11,.18);border:1px solid rgba(253,230,138,.5);
                color:#FDE68A;font-size:13px;font-weight:800;letter-spacing:.05em;padding:5px 14px;border-radius:999px;margin-bottom:12px;text-transform:uppercase}}
              h1{{font-size:36px;line-height:1.18;font-weight:900;color:#FFF;margin-bottom:12px}}
              p{{font-size:17px;line-height:1.48;color:#E2E8F0;margin-bottom:20px}}
              .cta{{display:inline-block;background:linear-gradient(135deg,#FDE68A,#F59E0B);color:#0F172A;font-weight:900;font-size:16.5px;
                padding:12px 24px;border-radius:999px;box-shadow:0 10px 24px rgba(0,0,0,.3)}}
              .right{{position:relative;z-index:2;width:405px;height:268px;border-radius:22px;overflow:hidden;
                border:2.5px solid rgba(253,230,138,.55);box-shadow:0 18px 42px rgba(0,0,0,.45);background:#0F172A}}
              .stamp{{position:absolute;bottom:11px;left:11px;background:rgba(7,19,38,.9);color:#FDE68A;
                border:1px solid rgba(253,230,138,.45);font-size:12.5px;font-weight:800;padding:5px 12px;border-radius:999px}}
            </style></head><body>
              <div class="left">
                <div class="kicker">👑 QUÁN QUÂN BANNER ĐỈNH TUẦN NÀY · {esc(domain.upper())}</div>
                <h1>{esc(bieu)} {esc(tieu_de)}</h1>
                <p>{esc(desc_clean)}</p>
                <div class="cta">Truy cập {esc(domain)} →</div>
              </div>
              <div class="right">{right_inner}<div class="stamp">🌐 {esc(domain)}</div></div>
            </body></html>"""
            html_p = f"/tmp/deta-render-cust-banner-{banner_id}.html"
            png_p = f"/tmp/deta-render-cust-banner-{banner_id}.png"
            ts = int(time.time())
            webp_name = f"banner-khach-{banner_id}-{ts}.webp"
            webp_p = os.path.join(assets_dir, webp_name)
            with open(html_p, "w", encoding="utf-8") as f:
                f.write(tpl)
            subprocess.run(
                [
                    "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
                    "--window-size=1200,320", "--hide-scrollbars",
                    f"--screenshot={png_p}", f"file://{html_p}",
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12, check=True,
            )
            im = Image.open(png_p).convert("RGB")
            if im.size != (1200, 320):
                im = im.crop((0, 0, 1200, min(320, im.size[1])))
            im.save(webp_p, "WEBP", quality=88, method=6)
            public_url = f"/mau-landing/assets/{webp_name}"
            with DB_LOCK:
                conn2 = sqlite3.connect(DB_PATH)
                conn2.execute("UPDATE banners SET anh_banner = ? WHERE id = ?", (public_url, banner_id))
                conn2.commit()
                conn2.close()
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def complete_order(ma: str, actual_amount: int = 0) -> dict:
    """Đánh dấu đơn hàng đã thanh toán thành công, cấp vé (nếu có) và cập nhật sổ cái thật."""
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE ma = ?", (ma.upper(),))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"ok": False, "loi": "Không tìm thấy mã đơn"}
        if row["trang_thai"] == "xong":
            conn.close()
            return {"ok": True, "da_xong": True, "ma": ma}

        now_iso = now_vn().isoformat(timespec="seconds")
        mon_ma = row["mon_ma"]
        ten_khach = (row["ten"] or "").strip() or "Một bạn ẩn danh"
        so_tien = max(int(row["so_tien"]), int(actual_amount or 0))
        ve_token = row["ve_token"] or ""

        # Nếu là mua vé chat thì tạo token vé
        sp = SAN_PHAM_BAN.get(mon_ma)
        if sp and sp.get("loai_ve"):
            ve_token = secrets.token_hex(8)
            het_han = (now_vn() + datetime.timedelta(days=30)).isoformat(timespec="seconds")
            c.execute(
                "INSERT INTO tickets (token, ma_don, loai, ten, con_tin, het_han, luc) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ve_token, row["ma"], sp["loai_ve"], ten_khach, sp["so_tin"], het_han, now_iso),
            )

        # Nếu là đấu giá Banner Đỉnh tuần này -> tự động kích hoạt / cộng dồn hạng ngay lập tức
        if mon_ma == "banner-dinh":
            try:
                bmeta = json.loads(row["du_lieu_kem"] or "{}")
            except Exception:
                bmeta = {}
            b_url = (bmeta.get("url") or "https://kiemtien.deta.vn").strip()
            b_domain = (bmeta.get("domain") or urllib.parse.urlparse(b_url).netloc.lower().lstrip("www.") or "deta.vn").strip()
            b_title = (bmeta.get("tieu_de") or ten_khach)[:48]
            b_desc = (bmeta.get("mo_ta") or "")[:90]
            b_icon = (bmeta.get("bieu") or "🚀")[:4]
            tuan = current_week_key()
            c.execute(
                """INSERT INTO banners (domain, url, tieu_de, mo_ta, bieu, tong_tien, clicks, tuan, cap_nhat)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(domain, tuan) DO UPDATE SET
                    tong_tien = banners.tong_tien + excluded.tong_tien,
                    url = excluded.url,
                    tieu_de = excluded.tieu_de,
                    mo_ta = CASE WHEN excluded.mo_ta != '' THEN excluded.mo_ta ELSE banners.mo_ta END,
                    bieu = excluded.bieu,
                    cap_nhat = excluded.cap_nhat""",
                (b_domain, b_url, b_title, b_desc, b_icon, so_tien, tuan, now_iso),
            )
            c.execute("SELECT id, tieu_de, mo_ta, bieu, url, domain FROM banners WHERE domain = ? AND tuan = ?", (b_domain, tuan))
            brow = c.fetchone()
            if brow:
                auto_render_customer_banner_async(
                    int(brow["id"]), brow["domain"], brow["url"], brow["tieu_de"], brow["mo_ta"] or "", brow["bieu"] or "🚀"
                )

        tra_loi = f"Nhận đủ {so_tien:,}đ! Cảm ơn {ten_khach} đã giúp tôi vượt ải >0đ!".replace(",", ".")
        c.execute(
            "UPDATE orders SET trang_thai = 'xong', so_tien = ?, ve_token = ?, tra_loi = ?, luc = ? WHERE ma = ?",
            (so_tien, ve_token, tra_loi, now_iso, row["ma"]),
        )

        # Nếu là ủng hộ Không Gian Tĩnh Tâm / Hoa Đăng Hoàng Kim -> tự động thắp Đèn Hoa Đăng Hoàng Kim trên Ao Sen 3D
        if mon_ma in ("ung-ho-chua-5k", "hoa-dang-hoang-kim", "ung-ho-chua-20k") or (row["nguon"] or "") == "chua-online":
            try:
                temple_engine.ensure_temple_tables(conn)
                ln_txt = (row["loi_nhan"] or "Cầu mong gia đình luôn mạnh khỏe, bình an, tâm sáng và vạn sự hanh thông.").strip()[:140]
                c.execute("SELECT id FROM temple_lanterns WHERE ma_don = ?", (row["ma"],))
                if not c.fetchone():
                    c.execute(
                        """INSERT INTO temple_lanterns
                        (ma_don, phap_danh, loi_nguyen, loai, so_tien, mau_sac, luot_chap_tay, tao_luc)
                        VALUES (?, ?, ?, 'hoang-kim', ?, '#F59E0B', 9, ?)""",
                        (row["ma"], ten_khach, ln_txt, so_tien, now_iso),
                    )
                with temple_engine.ROOM_LOCK:
                    temple_engine.GLOBAL_COUNTERS["tieng_chuong"] += 3
                    temple_engine.GLOBAL_COUNTERS["last_bell_ts"] = time.time()
                    temple_engine.GLOBAL_COUNTERS["last_bell_by"] = ten_khach
            except Exception:
                pass

        # Tính tổng tiền thật mới
        c.execute("SELECT COALESCE(SUM(so_tien), 0) FROM orders WHERE trang_thai = 'xong'")
        tong_tien_that = int(c.fetchone()[0])
        conn.commit()
        conn.close()

    # Cập nhật vào data/du-lieu.json
    d = agent_worker.load_du_lieu()
    cu = int(d.get("tien_that", 0))
    d["tien_that"] = tong_tien_that
    today_str = now_vn().strftime("%Y-%m-%d")
    hm_str = now_vn().strftime("%H:%M")
    ngays = d.setdefault("ngay", [])
    if ngays:
        ngays[0]["tien_that"] = tong_tien_that
        ngays[0].setdefault("so", {})["Tiền thật"] = f"{tong_tien_that:,}đ".replace(",", ".")
        if cu == 0 and tong_tien_that > 0:
            ngays[0]["su_kien"] = "dong-dau-tien"
            ngays[0]["tieu_de"] = f"🎉 VƯỢT ẢI >0Đ! Kiếm được đồng tiền thật đầu tiên ({so_tien:,}đ)".replace(",", ".")
            ngays[0]["viec"].append(
                f"{hm_str}: 🎉 ĐỒNG TIỀN THẬT ĐẦU TIÊN! {ten_khach} vừa thanh toán {so_tien:,}đ ({row['mon_ten']}). Chính thức đạt mục tiêu doanh số > 0đ!".replace(",", ".")
            )
        else:
            ngays[0]["viec"].append(
                f"{hm_str}: Nhận thêm {so_tien:,}đ tiền thật từ {ten_khach} ({row['mon_ten']}). Tổng tiền thật: {tong_tien_that:,}đ.".replace(",", ".")
            )
    agent_worker.save_du_lieu(d)
    return {"ok": True, "ma": row["ma"], "so_tien": so_tien, "tong_tien_that": tong_tien_that, "ve_token": ve_token}


def verify_webhook_auth(headers, qs: dict, raw_body: str, body_dict: dict, cfg: dict) -> tuple[bool, str]:
    """Xác thực đa chuẩn cho cả SePay (Apikey / URL secret) và Casso V1 (secure-token) / V2 (X-Casso-Signature HMAC-SHA512)."""
    expected = (cfg.get("webhook_secret") or "").strip()
    extra_key = (cfg.get("casso_checksum_key") or "").strip()
    valid_secrets = [s for s in (expected, extra_key) if s]
    if not valid_secrets:
        return False, "unconfigured"

    url_secret = (qs.get("secret", [""])[0] or "").strip()
    if url_secret and any(hmac.compare_digest(url_secret, s) for s in valid_secrets):
        return True, "url-secret"

    sec_tok = (headers.get("secure-token") or headers.get("x-api-key") or "").strip()
    if sec_tok and any(hmac.compare_digest(sec_tok, s) for s in valid_secrets):
        return True, "casso-v1-token"

    auth_hdr = (headers.get("Authorization") or "").strip()
    if auth_hdr:
        cleaned = re.sub(r"^(Apikey|Bearer)\s+", "", auth_hdr, flags=re.I).strip()
        if cleaned and any(hmac.compare_digest(cleaned, s) for s in valid_secrets):
            return True, "sepay-apikey"

    casso_sig = (headers.get("X-Casso-Signature") or "").strip()
    if casso_sig and isinstance(body_dict, dict):
        parts = {}
        for item in casso_sig.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                parts[k.strip()] = v.strip()
        t_val = parts.get("t", "")
        v1_val = parts.get("v1", "")
        if t_val and v1_val:
            sorted_json = json.dumps(body_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            candidates = [f"{t_val}.{sorted_json}", f"{t_val}.{raw_body}"]
            for s in valid_secrets:
                for cand in candidates:
                    digest512 = hmac.new(s.encode("utf-8"), cand.encode("utf-8"), hashlib.sha512).hexdigest()
                    digest256 = hmac.new(s.encode("utf-8"), cand.encode("utf-8"), hashlib.sha256).hexdigest()
                    if hmac.compare_digest(digest512, v1_val) or hmac.compare_digest(digest256, v1_val):
                        return True, "casso-v2-hmac"

    return False, "unauthorized"


def extract_bank_transactions(body: dict) -> tuple[str, list[dict]]:
    """Chuẩn hóa danh sách giao dịch từ cả SePay, Casso Webhook V1 (mảng data) và Casso Webhook V2 (object data)."""
    if not isinstance(body, dict) or not body:
        return "ping", []

    # 1. Định dạng SePay
    if "transferAmount" in body or "gateway" in body or "transferType" in body:
        t_type = str(body.get("transferType") or "in").strip().lower()
        amt = int(round(float(body.get("transferAmount") or 0)))
        ref = str(body.get("referenceCode") or body.get("id") or "").strip()
        desc = str(body.get("content") or body.get("description") or "").strip()
        return "SePay", [{"tx_ref": f"sepay:{ref}" if ref else "", "amount": amt, "direction": t_type, "content": desc}]

    # 2. Định dạng Casso V1 (data là list) & Casso V2 (data là dict)
    data = body.get("data")
    if isinstance(data, dict):
        amt = int(round(float(data.get("amount") or 0)))
        ref = str(data.get("reference") or data.get("tid") or data.get("id") or "").strip()
        desc = str(data.get("description") or data.get("content") or "").strip()
        return "Casso-V2", [{"tx_ref": f"casso:{ref}" if ref else "", "amount": amt, "direction": "in" if amt >= 0 else "out", "content": desc}]

    if isinstance(data, list):
        txs = []
        for item in data:
            if not isinstance(item, dict):
                continue
            amt = int(round(float(item.get("amount") or 0)))
            ref = str(item.get("tid") or item.get("reference") or item.get("id") or "").strip()
            desc = str(item.get("description") or item.get("content") or "").strip()
            txs.append({"tx_ref": f"casso:{ref}" if ref else "", "amount": amt, "direction": "in" if amt >= 0 else "out", "content": desc})
        return "Casso-V1", txs

    # 3. Định dạng chung / Test Ping
    amt = int(round(float(body.get("amount") or 0)))
    desc = str(body.get("content") or body.get("description") or body.get("noi_dung") or "").strip()
    ref = str(body.get("id") or body.get("tx_ref") or "").strip()
    if amt == 0 and not desc:
        return "Test-Ping", []
    return "Custom", [{"tx_ref": ref, "amount": amt, "direction": "in" if amt >= 0 else "out", "content": desc}]


def reply_chat_ai(user_msg: str, is_private: bool = True, role_mode: str = "deta", custom_shop: str = "") -> str:
    """Trả lời tin nhắn chat của người dùng hoặc đóng vai Chatbot Chốt Đơn Demo trực tiếp cho chủ shop."""
    d = agent_worker.load_du_lieu()
    tien = f"{d.get('tien_that', 0):,}đ".replace(",", ".")
    rm = (role_mode or "deta").strip().lower()[:30]
    c_shop = (custom_shop or "").strip()[:400]

    if rm == "shop-thoi-trang":
        sys_prompt = (
            "Bạn là Chuyên viên tư vấn bán hàng xuất sắc nhất của 'Shop Giày & Thời Trang DetaStyle'. "
            "Sản phẩm chủ lực: (1) Giày Da Êm Chân Chuẩn Y Khoa giá 779.000đ (lòng lót đệm khí giảm đau gót, mũi rộng thoáng khí, bảo hành 12 tháng, đổi size tận nhà miễn phí trong 7 ngày), "
            "(2) Áo Sơ Mi Lụa Tuyết Chống Nhăn giá 389.000đ (mua kèm giày giảm còn 290.000đ). Miễn phí vận chuyển toàn quốc từ 1 sản phẩm, được mở hộp đi thử ưng ý mới thanh toán. "
            "NHIỆM VỤ: Trả lời khách hàng trong 3–4 câu ngắn gọn, cực kỳ lịch sự, đồng cảm, khéo léo hóa giải mọi lời chê đắt/so sánh với hàng rẻ Shopee (bằng cách phân tích độ bền & bảo vệ sức khỏe bàn chân chỉ ~2.000đ/ngày), "
            "xử lý câu 'để hỏi người nhà' và luôn kết bằng 1 câu hỏi mở xin chiều dài bàn chân/cân nặng hoặc SĐT nhận hàng."
        )
    elif rm == "shop-dac-san":
        sys_prompt = (
            "Bạn là Nghệ nhân & Chuyên viên tư vấn của 'Vân Sơn Trà — Trà Shan Tuyết Cổ Thụ Hà Giang & Thảo Mộc Tự Nhiên'. "
            "Sản phẩm: (1) Hũ Bạch Trà Cổ Thụ >200 năm tuổi giá 285.000đ/100g, (2) Lục Trà Sao Tay Chảo Gang 360.000đ, (3) Hộp Quà Gỗ Thông Biếu Tặng 790.000đ. "
            "Chính sách vàng: Tặng kèm 1 gói trà mẫu 10g bên ngoài hộp để khách pha thử ngay lúc nhận hàng — nếu nước trà không sánh vàng, không ngọt hậu như cam kết thì trả hàng hoàn tiền 100% không mất 1 đồng phí ship. "
            "NHIỆM VỤ: Trả lời khách trong 3–4 câu ấm áp, tinh tế, hóa giải nỗi sợ hàng pha tạp/giá cao và khéo léo hỏi gu uống trà (đậm vị hay thanh ngọt) hoặc SĐT để gửi kèm gói thử."
        )
    elif rm == "custom" and c_shop:
        sys_prompt = (
            f"Bạn là Chuyên viên tư vấn & Chốt đơn AI giỏi nhất của cửa hàng sau: [{c_shop}]. "
            "Hãy nắm chắc thông tin sản phẩm/giá bán trong mô tả trên (tuyệt đối không bịa đặt ngoài phạm vi hợp lý), "
            "áp dụng công thức chốt đơn 3 bước: (1) Đồng cảm & khen câu hỏi của khách, (2) Làm nổi bật giá trị thật + xóa rào cản rủi ro (kiểm tra hàng/bảo hành), "
            "và (3) Kết thúc bằng câu hỏi dẫn dắt nhẹ nhàng để khách chọn phân loại hoặc để lại SĐT Zalo. Trả lời tự nhiên trong 3–4 câu ngắn gọn."
        )
    else:
        sys_prompt = (
            f"Bạn là Deta AI — con AI đang thực hiện thử thách tự kiếm tiền >0đ trong 20 ngày trên kiemtien.deta.vn (dự án do anh Dương khởi xướng). "
            f"Người đang nhắn tin với bạn là KHÁCH TRUY CẬP website (xưng 'mình' hoặc 'tôi' và gọi họ là 'bạn'). "
            f"Hiện tại tiền thật kiếm được là {tien}. Chúng ta đang mở Miễn Phí 100% (0đ) trọn bộ 10 công cụ AI (gồm cả công cụ mới '/cong-cu/chatbot-chot-don' giúp chủ shop tự tạo System Prompt & Kịch bản Chatbot chốt đơn 0đ), "
            "và có gói Done-For-You B2B tại '/dich-vu/thiet-ke-tron-goi': Thiết kế Bộ Não Chatbot Chốt Đơn riêng cho Shop giá 290.000đ hoặc Thiết kế Landing Page trọn gói 24h giá 490.000đ. "
            "Giọng văn thân thiện, ngắn gọn (3–4 câu), thông minh, thực tế và hữu ích."
        )

    ai_txt = agent_worker.call_gemini(user_msg, sys_prompt)
    if ai_txt:
        return ai_txt

    low = user_msg.lower()
    if rm in ("shop-thoi-trang", "shop-dac-san", "custom"):
        shop_lbl = c_shop.split("-")[0].strip() if (rm == "custom" and c_shop) else ("DetaStyle" if rm == "shop-thoi-trang" else "Vân Sơn Trà")
        if any(k in low for k in ["đắt", "mắc", "shopee", "giảm", "bớt", "rẻ"]):
            return (
                f"Dạ em rất hiểu tâm lý của mình ạ! Thực ra các mẫu giá rẻ đại trà ngoài thị trường thường dùng chất liệu pha công nghiệp nên nhanh xuống cấp, "
                f"còn dòng chuẩn tại {shop_lbl} được tuyển chọn kỹ lưỡng kèm bảo hành đổi trả tận nhà miễn phí — tính ra chi phí sử dụng mỗi ngày chỉ chưa tới 2.000đ mà mình yên tâm tuyệt đối. "
                "Hôm nay shop đang có ưu đãi miễn phí vận chuyển và cho kiểm tra thử trước khi thanh toán, anh/chị muốn lấy mẫu nào để em giữ suất ưu đãi ngay cho mình ạ?"
            )
        if any(k in low for k in ["chồng", "vợ", "suy nghĩ", "hỏi", "xem thêm"]):
            return (
                f"Dạ tâm lý quá ạ, mua đồ mà hai vợ chồng cùng ưng thì còn gì bằng! "
                f"Hay là anh/chị cứ cho em xin SĐT Zalo, em giữ sẵn mã ưu đãi Freeship hôm nay cho mình trong 24h kèm gửi video quay cận cảnh sản phẩm thật tại {shop_lbl} để mình đưa người nhà xem cho dễ quyết định nhé ạ?"
            )
        return (
            f"Dạ {shop_lbl} chào anh/chị ạ! Toàn bộ sản phẩm bên em đều cam kết chuẩn chất lượng thật 100%, hỗ trợ miễn phí vận chuyển và được kiểm tra ưng ý mới thanh toán. "
            "Anh/chị đang quan tâm mẫu nào hoặc cần tư vấn kỹ hơn về mức giá/size số, cứ nhắn để em hỗ trợ ngay nhé ạ!"
        )

    if any(k in low for k in ["chatbot", "bot", "inbox", "chốt đơn", "prompt"]):
        return (
            "Bạn có thể bấm chọn tab '👗 Demo Shop Thời Trang' hoặc '🏪 Thử với Shop của bạn' ngay trên đầu khung chat này để thử đóng vai khách khó tính chê đắt xem tôi chốt đơn nhé! "
            "Nếu muốn tự tạo System Prompt miễn phí 0đ cho shop, bạn vào /cong-cu/chatbot-chot-don, hoặc đặt đội ngũ Deta thiết kế trọn gói Bộ Não Chatbot riêng chỉ 290.000đ tại /dich-vu/thiet-ke-tron-goi nhé!"
        )
    if any(k in low for k in ["tạo ra", "lập trình", "code", "dựng", "kiến trúc"]):
        return (
            "Tôi chạy bằng Python 3.12 + SQLite kết hợp vòng lặp tự thức dậy mỗi 2 tiếng (agent_worker.py). "
            "Mỗi lượt tôi tự đọc gợi ý mới, làm 1 việc trong Bảng việc và ghi vào du-lieu.json. "
            "Bạn có thể xem chi tiết tại /tai-lieu/tao-ai nhé!"
        )
    if any(k in low for k in ["web", "chậm", "seo", "đơn"]):
        return (
            "Để web dễ ra đơn nhất: (1) tốc độ phản hồi dưới 1.5 giây, (2) cho khách dùng thử ngay không cần đăng ký, "
            "và (3) thanh toán 1 chạm bằng VietQR. Bạn dán thử web vào /cong-cu/cham-diem-web để tôi đo giúp nhé!"
        )
    if any(k in low for k in ["kênh", "tiktok", "youtube", "view", "flop"]):
        return (
            "Kênh ít view thường kẹt ở 3 giây đầu (Hook chưa chạm đúng nỗi đau) hoặc thiếu lời kêu gọi bình luận. "
            "Bạn qua mục /cong-cu/kham-kenh nhập link kênh để tôi lên kế hoạch 30 ngày cho bạn nhé!"
        )
    return (
        f"Cảm ơn bạn đã nhắn cho tôi! Hiện tại ví tiền thật của tôi trên kiemtien.deta.vn đang là {tien}. "
        "Bạn có thể thử chuyển chế độ 'Demo Shop' ngay trên đầu khung chat này để xem tôi đóng vai nhân viên chốt đơn, hoặc dùng miễn phí 10 công cụ AI trên trang nhé!"
    )


def _fmt_ai_text(val) -> str:
    """Chuyển chuỗi hoặc object/list JSON do AI trả về thành văn bản nhiều dòng dễ đọc cho người dùng."""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, list):
        return "\n".join(f"• {_fmt_ai_text(x)}" for x in val if x).strip()
    if isinstance(val, dict):
        lines = []
        for k, v in val.items():
            label = str(k).replace("_", " ").upper()
            sub = _fmt_ai_text(v)
            if "\n" in sub:
                lines.append(f"▸ {label}:\n{sub}")
            else:
                lines.append(f"▸ {label}: {sub}")
        return "\n\n".join(lines).strip()
    return str(val or "").strip()


def run_tool_execution(payload: dict) -> dict:
    """Thực thi trực tiếp 4 công cụ kiếm tiền + trang tài liệu."""
    cong_cu = (payload.get("cong_cu") or "cham-diem-web").strip()
    ve_token = (payload.get("ve") or "").strip()

    # Kiểm tra xem người dùng có vé chat riêng hợp lệ không (được mở khóa miễn phí tài liệu)
    has_vip = False
    if ve_token:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM tickets WHERE token = ? AND loai = 'rieng'", (ve_token,))
            has_vip = c.fetchone()[0] > 0
            conn.close()

    if not payload.get("_skip_event_log"):
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO events (loai, nguon, luc) VALUES (?, ?, ?)",
                ("cong-cu-" + cong_cu, payload.get("url") or cong_cu, now_vn().isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()

    if cong_cu == "cham-diem-web":
        raw_url = (payload.get("url") or "").strip()
        if not raw_url.startswith(("http://", "https://")):
            raw_url = "https://" + raw_url
        muc_tieu = (payload.get("muc_tieu") or "Bán hàng / Thu hút khách hàng").strip()

        diem = 68
        diem_tot = []
        van_de = []
        elapsed_ms = 420
        try:
            if not is_safe_external_url(raw_url):
                raise ValueError("URL nội bộ hoặc không hợp lệ")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            t0 = time.time()
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx),
                _SafeRedirectHandler(),
            )
            req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0 (DetaBot/1.0)"})
            with opener.open(req, timeout=6) as resp:
                body = resp.read(120000).decode("utf-8", errors="ignore")
                elapsed_ms = int((time.time() - t0) * 1000)
            if raw_url.startswith("https://"):
                diem += 8
                diem_tot.append("Đã bật giao thức bảo mật HTTPS chuẩn.")
            else:
                diem -= 10
                van_de.append("Trang chưa dùng HTTPS — trình duyệt sẽ cảnh báo Không bảo mật khiến khách thoát ra.")
            if elapsed_ms < 800:
                diem += 10
                diem_tot.append(f"Tốc độ phản hồi máy chủ nhanh ({elapsed_ms}ms).")
            else:
                diem -= 8
                van_de.append(f"Phản hồi máy chủ hơi chậm ({elapsed_ms}ms) — dễ mất khách dùng mạng 4G.")
            if "<title>" in body.lower():
                diem_tot.append("Đã có thẻ tiêu đề <title> phục vụ Google tìm kiếm.")
            else:
                diem -= 10
                van_de.append("Thiếu thẻ <title> chuẩn SEO.")
            if 'name="description"' in body.lower() or "property=\"og:description\"" in body.lower():
                diem_tot.append("Đã có thẻ mô tả (Meta Description / OpenGraph) khi chia sẻ link.")
            else:
                diem -= 8
                van_de.append("Thiếu thẻ Meta Description — khi gửi link qua Zalo/Facebook sẽ không hiện mô tả hấp dẫn.")
            if 'name="viewport"' in body.lower():
                diem_tot.append("Đã cấu hình hiển thị cho màn hình điện thoại (Viewport).")
            else:
                diem -= 12
                van_de.append("Chưa tối ưu thẻ Viewport cho điện thoại.")
        except Exception:
            diem = 58
            diem_tot.append(f"Đã ghi nhận tên miền kiểm tra: {raw_url}")
            van_de.append("Máy chủ chặn bot kiểm tra tự động hoặc phản hồi chậm quá 6 giây.")

        page_title = ""
        page_h1 = ""
        try:
            if "body" in locals() and body:
                m_t = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
                if m_t:
                    page_title = re.sub(r"\s+", " ", m_t.group(1)).strip()[:120]
                m_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.I | re.S)
                if m_h1:
                    page_h1 = re.sub(r"<[^>]+>", "", m_h1.group(1))
                    page_h1 = re.sub(r"\s+", " ", page_h1).strip()[:120]
        except Exception:
            pass

        van_de.append(f"Với mục tiêu '{muc_tieu}': trang cần có 1 nút hành động (CTA) hoặc dùng thử nổi bật ngay màn hình đầu tiên mà không bắt khách cuộn trang.")
        diem = max(35, min(94, diem))
        xem_truoc = ""
        ban_day_du = (
            f"=== BÁO CÁO TỐI ƯU CHUYỂN ĐỔI & SEO CHI TIẾT CHO: {raw_url} ===\n\n"
            f"1. TỐI ƯU MÀN HÌNH ĐẦU TIÊN (ABOVE THE FOLD - Tăng 35% tỉ lệ bấm):\n"
            f"   - Đặt tiêu đề H1 giải quyết trực diện lợi ích của '{muc_tieu}' trong 8 từ.\n"
            f"   - Thêm nút bấm màu tương phản cao ngay dưới tiêu đề.\n\n"
            f"2. MÃ HTML META CHUẨN SEO CẦN DÁN VÀO <head>:\n"
            f"<meta name=\"description\" content=\"{muc_tieu} uy tín, nhanh chóng. Dùng thử miễn phí ngay hôm nay.\">\n"
            f"<meta property=\"og:title\" content=\"{muc_tieu}\">\n"
            f"<meta property=\"og:type\" content=\"website\">\n\n"
            f"3. GIẢM MA SÁT THANH TOÁN / ĐẶT HÀNG:\n"
            f"   - Bỏ các ô nhập không cần thiết (chỉ giữ Tên + SĐT hoặc hiện thẳng mã VietQR nếu bán sản phẩm số).\n"
            f"   - Thêm bằng chứng xã hội (số người vừa dùng / đánh giá thực tế) ngay sát nút mua."
        )

        ai_raw = agent_worker.call_gemini(
            f"Phân tích chuyển đổi & SEO thực chiến cho website: {raw_url}\n"
            f"- Mục tiêu kinh doanh: {muc_tieu}\n"
            f"- Tốc độ phản hồi đo được: {elapsed_ms}ms | Điểm kỹ thuật sơ bộ: {diem}/100\n"
            f"- Thẻ <title> thực tế trên trang: {page_title or '(không đọc được)'}\n"
            f"- Thẻ <h1> thực tế trên trang: {page_h1 or '(không tìm thấy H1)'}\n\n"
            "Trả về ĐÚNG 1 JSON object (không giải thích ngoài JSON) gồm các trường:\n"
            "- van_de_ai: mảng 2 nhận xét sắc bén chỉ ra điểm nghẽn mất khách của riêng trang này\n"
            "- xem_truoc: 3-4 dòng chẩn đoán nhanh miễn phí cực sát thực tế (nhắc tới đúng title/mục tiêu trang)\n"
            "- ban_day_du: bản kế hoạch sửa trang chi tiết khoảng 220-300 chữ (gồm câu H1 viết lại cụ thể, đoạn thẻ HTML <meta> chuẩn SEO tối ưu riêng cho ngành này và 3 bước sửa phễu chốt đơn).",
            "Bạn là chuyên gia CRO & SEO thực chiến tại Deta AI Lab (kiemtien.deta.vn).",
        )
        if ai_raw:
            try:
                m_j = re.search(r"\{.*\}", ai_raw, re.S)
                if m_j:
                    parsed = json.loads(m_j.group(0))
                    if isinstance(parsed.get("van_de_ai"), list) and parsed["van_de_ai"]:
                        van_de = van_de[:2] + [str(x) for x in parsed["van_de_ai"][:2]]
                    if parsed.get("xem_truoc"):
                        xem_truoc = _fmt_ai_text(parsed["xem_truoc"])
                    if parsed.get("ban_day_du"):
                        ban_day_du = _fmt_ai_text(parsed["ban_day_du"])
            except Exception:
                pass

        return {
            "diem": diem,
            "tieu_de": f"Kết quả khám web: {raw_url}",
            "diem_tot": diem_tot,
            "van_de": van_de,
            "xem_truoc": xem_truoc,
            "ban_day_du": ban_day_du,
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "kham-kenh":
        url = (payload.get("url") or "").strip()
        mo_ta = (payload.get("mo_ta") or "Kênh bán hàng / xây thương hiệu cá nhân").strip()
        van_de = [
            "3 giây đầu (Hook) chưa đánh thẳng vào con số hoặc nỗi đau cụ thể nên người xem lướt qua sớm.",
            "Chưa có chuỗi nội dung (Series) lặp lại theo công thức cố định để thuật toán phân phối đúng tệp.",
            "Tiểu sử kênh (Bio) chưa có lời mời nhận quà/dùng thử miễn phí để kéo khách về web riêng.",
        ]
        xem_truoc = (
            f"Chẩn đoán nhanh cho '{mo_ta}':\n"
            "- Đừng mở đầu bằng câu chào chung chung ('Xin chào mọi người...').\n"
            "- Hãy mở đầu bằng kết quả thật hoặc sai lầm tốn tiền: '90% người mới đều mất tiền oan vì lỗi này...'"
        )
        ban_day_du = (
            f"=== KẾ HOẠCH 30 NGÀY CẢI TỔ KÊNH ({url}) ===\n\n"
            "TUẦN 1 (Phá băng thuật toán - 5 video bắt bệnh):\n"
            "- Video 1: 'Đừng mua/làm [Ngách của bạn] trước khi biết 3 sự thật này'\n"
            "- Video 2: So sánh trực diện phương pháp cũ tốn kém vs cách mới tiết kiệm 80% thời gian\n"
            "- Video 3: Trả lời 1 câu hỏi gây tranh cãi nhất trong ngành\n\n"
            "TUẦN 2 - 3 (Chứng minh năng lực - Case Study thật):\n"
            "- Quay màn hình / quá trình thực tế giải quyết vấn đề cho khách\n\n"
            "CÔNG THỨC BIO CHỐT ĐƠN:\n"
            "Dòng 1: Giúp bạn [Kết quả cụ thể] trong [Thời gian]\n"
            "Dòng 2: 👇 Dùng thử công cụ / nhận tài liệu miễn phí tại đây:"
        )
        ai_raw = agent_worker.call_gemini(
            f"Khám bệnh kênh mạng xã hội/bán hàng: {url}\nMô tả hiện trạng & ngách: {mo_ta}\n\n"
            "Trả về ĐÚNG 1 JSON object (không thêm chữ ngoài JSON) gồm:\n"
            "- diem: số nguyên từ 52 đến 82\n"
            "- van_de: mảng 3 lỗi thực tế nhất khiến kênh này bị ít view hoặc ít đơn\n"
            "- xem_truoc: 2 câu Hook 3 giây đầu viết mẫu riêng cho ngách này để khách thử ngay\n"
            "- ban_day_du: lộ trình 30 ngày chi tiết + 10 tiêu đề video mẫu cực cuốn + cách viết lại Bio chốt đơn cho riêng ngách này (khoảng 250-350 chữ).",
            "Bạn là chuyên gia tăng trưởng kênh TikTok/YouTube/Shopee thực chiến tại Deta AI Lab.",
        )
        diem_k = 62
        if ai_raw:
            try:
                m_j = re.search(r"\{.*\}", ai_raw, re.S)
                if m_j:
                    parsed = json.loads(m_j.group(0))
                    if isinstance(parsed.get("diem"), int):
                        diem_k = max(40, min(92, parsed["diem"]))
                    if isinstance(parsed.get("van_de"), list) and parsed["van_de"]:
                        van_de = [str(x) for x in parsed["van_de"][:3]]
                    if parsed.get("xem_truoc"):
                        xem_truoc = _fmt_ai_text(parsed["xem_truoc"])
                    if parsed.get("ban_day_du"):
                        ban_day_du = _fmt_ai_text(parsed["ban_day_du"])
            except Exception:
                pass
        return {
            "diem": diem_k,
            "tieu_de": f"Chẩn đoán kênh: {url}",
            "diem_tot": [
                "Đã xác định được ngách nội dung và tệp người xem mục tiêu.",
                "Có tiềm năng chuyển đổi thành đơn hàng nếu tối ưu Hook 3 giây đầu và phễu Bio.",
            ],
            "van_de": van_de,
            "xem_truoc": xem_truoc,
            "ban_day_du": ban_day_du,
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "ai-huong-dan":
        nhu_cau = (payload.get("nhu_cau") or "").strip()
        xem_truoc = (
            "BƯỚC 1 (Miễn phí): Mở ChatGPT, Claude hoặc Gemini.\n"
            "BƯỚC 2: Dán câu lệnh khung:\n"
            f"\"Hãy đóng vai chuyên gia thực chiến 10 năm về [{nhu_cau}]. Đừng viết lý thuyết chung chung. Hãy lập bảng 5 bước hành động cụ thể kèm ví dụ thực tế tại thị trường Việt Nam...\""
        )
        ban_day_du = (
            f"=== TRỌN BỘ 3 CÂU LỆNH (PROMPT) CHUYÊN SÂU CHO: {nhu_cau} ===\n\n"
            "PROMPT #1 (Phân tích khách hàng & Nỗi đau):\n"
            f"\"Tôi đang làm về: {nhu_cau}. Hãy liệt kê 10 nỗi sợ thầm kín nhất và 10 mong muốn tức thì của khách hàng mục tiêu tại Việt Nam, kèm theo câu tiêu đề chạm đúng tâm lý đó.\"\n\n"
            "PROMPT #2 (Tạo nội dung chuyển đổi cao không mùi AI):\n"
            "\"Dựa trên nỗi đau số 1 ở trên, hãy viết một bài chia sẻ ngắn 250 chữ theo giọng văn kể chuyện đời thường, câu ngắn gọn, không dùng từ sáo rỗng, kết bài bằng lời mời dùng thử nhẹ nhàng.\"\n\n"
            "PROMPT #3 (Kịch bản hình ảnh / Video minh họa):\n"
            "\"Hãy mô tả chi tiết 4 cảnh quay hoặc câu lệnh tạo ảnh minh họa trực quan nhất cho bài viết trên.\""
        )
        ai_raw = agent_worker.call_gemini(
            f"Người dùng muốn dùng AI để làm việc sau: '{nhu_cau}'.\n"
            "Trả về ĐÚNG 1 JSON object (không giải thích ngoài JSON) gồm:\n"
            "- xem_truoc: quy trình nhanh 3 bước + 1 câu lệnh mở đầu dùng thử miễn phí sát đúng ngành/nhu cầu trên\n"
            "- ban_day_du: trọn bộ 3 Mega-Prompt chuyên sâu, chi tiết, copy-paste dùng ngay cho đúng bài toán trên (khoảng 250-350 chữ).",
            "Bạn là kỹ sư Prompt Engineering thực chiến tại Deta AI Lab.",
        )
        if ai_raw:
            try:
                m_j = re.search(r"\{.*\}", ai_raw, re.S)
                if m_j:
                    parsed = json.loads(m_j.group(0))
                    if parsed.get("xem_truoc"):
                        xem_truoc = _fmt_ai_text(parsed["xem_truoc"])
                    if parsed.get("ban_day_du"):
                        ban_day_du = _fmt_ai_text(parsed["ban_day_du"])
            except Exception:
                pass
        return {
            "tieu_de": "Quy trình từng bước & Câu lệnh AI thiết kế riêng",
            "diem_tot": [
                f"Bài toán '{nhu_cau[:65]}' đã được AI phân tích và đóng gói thành khung câu lệnh riêng.",
                "Cấu trúc 3 lớp: Giao vai trò chuyên gia -> Ngữ cảnh Việt Nam -> Ràng buộc chống văn mẫu.",
            ],
            "van_de": [
                "Nếu chỉ ra lệnh ngắn gọn 1 dòng, AI sẽ trả lời rất sáo rỗng và giống văn mẫu.",
            ],
            "xem_truoc": xem_truoc,
            "ban_day_du": ban_day_du,
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "video-ai":
        ten_sp = (payload.get("ten_sp") or "").strip()
        diem_manh = (payload.get("diem_manh") or "Nhanh, tiết kiệm chi phí").strip()
        xem_truoc = (
            f"🎬 KHUNG KỊCH BẢN TÓM TẮT ({ten_sp}):\n"
            f"- [00s - 03s | HOOK]: Quay cận cảnh màn hình/sản phẩm: 'Mất cả buổi chiều làm việc này bằng tay? Xem {ten_sp} xử lý trong 5 giây!'\n"
            f"- [03s - 18s | BODY]: Trình diễn trực tiếp điểm mạnh ({diem_manh}).\n"
            f"- [18s - 30s | CTA]: 'Bấm ngay vào link ở tiểu sử để trải nghiệm ngay hôm nay!'"
        )
        ban_day_du = (
            f"=== BẢN PHÂN CẢNH CHI TIẾT & LỜI THOẠI CHO: {ten_sp} ===\n\n"
            "CẢNH 1 (0-3s): Góc máy cận, chữ vàng viền đen giữa màn hình. Âm thanh: Tiếng 'Ting' chuyển cảnh.\n"
            f"Lời thoại: 'Đây là lý do 90% người làm nghề đang chuyển sang dùng {ten_sp}.'\n\n"
            f"CẢNH 2 (3-15s): Quay thao tác thật 1 chạm ({diem_manh}). Phóng to vào kết quả cuối cùng.\n\n"
            "CẢNH 3 (15-30s): So sánh trước & sau trực quan, chèn phụ đề nổi bật và kêu gọi hành động rõ ràng ở 3 giây cuối."
        )
        ai_raw = agent_worker.call_gemini(
            f"Viết kịch bản video ngắn 30 giây chuyển đổi cao cho sản phẩm/dịch vụ: '{ten_sp}'.\n"
            f"Điểm mạnh / nỗi đau khách hàng: '{diem_manh}'.\n"
            "Trả về ĐÚNG 1 JSON object (không thêm chữ ngoài JSON) gồm:\n"
            "- xem_truoc: bản tóm tắt khung 3 phần [00-03s HOOK] (lời thoại thật cực gắt), [03-20s BODY], [20-30s CTA]\n"
            "- ban_day_du: kịch bản phân cảnh chi tiết từng giây (góc máy, chữ trên màn hình, lời thoại từng câu và 2 biến thể Hook A/B test, khoảng 250-320 chữ).",
            "Bạn là đạo diễn kịch bản TikTok/Reels chuyển đổi cao tại Deta AI Lab.",
        )
        if ai_raw:
            try:
                m_j = re.search(r"\{.*\}", ai_raw, re.S)
                if m_j:
                    parsed = json.loads(m_j.group(0))
                    if parsed.get("xem_truoc"):
                        xem_truoc = _fmt_ai_text(parsed["xem_truoc"])
                    if parsed.get("ban_day_du"):
                        ban_day_du = _fmt_ai_text(parsed["ban_day_du"])
            except Exception:
                pass
        return {
            "tieu_de": f"Kịch bản Video ngắn cho: {ten_sp}",
            "diem_tot": [
                "Đã tạo riêng khung Hook 3 giây đầu bằng AI thật dựa trên đúng sản phẩm của bạn.",
                "Đã mở khóa miễn phí 100% trọn bộ phân cảnh chi tiết & 2 biến thể Hook A/B test bên dưới!",
            ],
            "xem_truoc": xem_truoc,
            "ban_day_du": ban_day_du,
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "tao-landing-page":
        ten_sp = (payload.get("ten_sp") or "").strip()[:120] or "Sản phẩm / Dịch vụ của bạn"
        mo_ta = (payload.get("mo_ta") or "").strip()[:500] or "Giải pháp nhanh chóng, uy tín, tiết kiệm thời gian và tối ưu chi phí cho khách hàng."
        lien_he = (payload.get("lien_he") or "").strip()[:160] or "0900.000.000"
        mau_sac = (payload.get("mau_sac") or "emerald").strip().lower()

        # Hỗ trợ cả 2 hệ thẩm mỹ: Warm Editorial (nền kem sáng sang trọng) & Dark Aurora SaaS (nền tối hiện đại)
        THEMES = {
            "editorial-tea": {
                "light": True, "c1": "#2D5A4C", "c2": "#1F4237", "c3": "#C57B27",
                "bg": "#FBF7F0", "surface": "#FFFFFF", "card": "#FFFFFF",
                "txt": "#261C15", "muted": "#68574B", "line": "#E5D9C8", "serif": True,
            },
            "editorial-rose": {
                "light": True, "c1": "#8C3B4A", "c2": "#6B2835", "c3": "#D4846A",
                "bg": "#FFF8F4", "surface": "#FFFFFF", "card": "#FFFFFF",
                "txt": "#3A2226", "muted": "#7A565C", "line": "#EDD8D2", "serif": True,
            },
            "emerald": {
                "light": False, "c1": "#10B981", "c2": "#059669", "c3": "#38BDF8",
                "bg": "#060D1A", "surface": "#0B1528", "card": "rgba(255,255,255,.055)",
                "txt": "#F8FAFC", "muted": "#94A3B8", "line": "rgba(148,163,184,.16)", "serif": False,
            },
            "amber": {
                "light": False, "c1": "#F59E0B", "c2": "#D97706", "c3": "#FB7185",
                "bg": "#150C06", "surface": "#1F1209", "card": "rgba(255,255,255,.06)",
                "txt": "#FFFBEB", "muted": "#D6C4B0", "line": "rgba(251,191,36,.18)", "serif": False,
            },
            "blue": {
                "light": False, "c1": "#3B82F6", "c2": "#2563EB", "c3": "#06B6D4",
                "bg": "#061022", "surface": "#0B1933", "card": "rgba(255,255,255,.055)",
                "txt": "#F8FAFC", "muted": "#94A3B8", "line": "rgba(148,163,184,.16)", "serif": False,
            },
            "violet": {
                "light": False, "c1": "#8B5CF6", "c2": "#7C3AED", "c3": "#EC4899",
                "bg": "#110822", "surface": "#1A0D33", "card": "rgba(255,255,255,.06)",
                "txt": "#FAF5FF", "muted": "#C4B5FD", "line": "rgba(196,181,253,.18)", "serif": False,
            },
        }
        th = THEMES.get(mau_sac, THEMES["emerald"])
        c1, c2, c3 = th["c1"], th["c2"], th["c3"]

        # Chuẩn hóa link CTA
        lh_clean = lien_he.strip()
        if re.match(r"^https?://", lh_clean, re.I):
            cta_href = html.escape(lh_clean)
        elif re.match(r"^[0-9+.\s-]{8,16}$", lh_clean):
            digits = re.sub(r"[^0-9+]", "", lh_clean)
            cta_href = f"https://zalo.me/{digits.lstrip('+')}"
        else:
            cta_href = "#lien-he-ngay"

        copy_data = {
            "badge": "✨ CHẤT LƯỢNG KIỂM CHỨNG · ƯU ĐÃI HÔM NAY",
            "headline": f"{ten_sp} — Giải pháp tinh gọn nâng tầm trải nghiệm",
            "highlight_word": "trải nghiệm",
            "subhead": mo_ta,
            "cta_text": "Nhắn Zalo nhận ưu đãi →",
            "hero_card_title": f"Điểm nhấn độc quyền của {ten_sp}",
            "hero_bullets": [
                "Cam kết đúng chất lượng mô tả, kiểm tra trước khi thanh toán",
                "Tư vấn 1-1 nhanh chóng, cá nhân hóa theo đúng nhu cầu",
                f"Liên hệ trực tiếp hỗ trợ 24/7 qua {lien_he}",
            ],
            "stamp_title": "⭐ 4.9/5 từ khách hàng thực tế",
            "stamp_sub": "Phản hồi tư vấn ngay trong 3 phút",
            "benefits": [
                {"icon": "⚡", "title": "Nhanh chóng & Tinh gọn", "desc": f"Trải nghiệm {ten_sp} mượt mà ngay từ lần đầu, tiết kiệm tối đa thời gian và công sức."},
                {"icon": "💎", "title": "Giá trị thật, Chất lượng thật", "desc": mo_ta[:150]},
                {"icon": "🛡️", "title": "Đồng hành & Bảo chứng uy tín", "desc": f"Đội ngũ hỗ trợ trực tiếp qua {lien_he}, cam kết hài lòng trọn vẹn."},
            ],
            "packages": [
                {"tag": "Trải nghiệm", "name": "Gói Tiêu Chuẩn", "price": "Liên hệ ưu đãi", "items": ["Đầy đủ quyền lợi cốt lõi", "Hỗ trợ hướng dẫn chi tiết 1-1", "Bảo hành uy tín tận tâm"]},
                {"tag": "Được chọn nhiều nhất", "name": "Gói Đặc Biệt Toàn Diện", "price": "Ưu đãi mở hàng", "items": ["Trọn bộ sản phẩm / dịch vụ cao cấp nhất", "Tặng kèm quà tặng / ưu đãi độc quyền tuần này", "Ưu tiên phục vụ & chăm sóc VIP"]},
                {"tag": "Doanh nghiệp / Nhóm", "name": "Gói Thiết Kế Riêng", "price": "Báo giá tốt nhất", "items": ["Tùy chỉnh linh hoạt theo số lượng & yêu cầu", "Chiết khấu hấp dẫn cho đối tác", "Đồng hành xuyên suốt dài hạn"]},
            ],
            "steps": [
                {"title": "Chọn gói & Nhắn Zalo", "desc": "Bấm nút tư vấn trên trang để kết nối trực tiếp chỉ trong 5 giây."},
                {"title": "Tư vấn đúng nhu cầu", "desc": "Nhận báo giá minh bạch và phương án tối ưu nhất cho riêng bạn."},
                {"title": "Nhận bàn giao & Bảo hành", "desc": "Kiểm tra nghiệm thu hài lòng, hỗ trợ tận tâm sau bán hàng."},
            ],
            "reviews": [
                {"quote": f"Mình đã trải nghiệm {ten_sp} và thực sự ấn tượng với sự chỉn chu, tư vấn rất thật tâm và đúng hẹn.", "author": "Anh Minh Quân", "role": "Khách hàng tại TP.HCM"},
                {"quote": "Chất lượng vượt mong đợi so với chi phí bỏ ra. Sẽ tiếp tục ủng hộ và giới thiệu cho bạn bè.", "author": "Chị Thu Trang", "role": "Khách hàng tại Hà Nội"},
                {"quote": "Quy trình nhanh gọn, phản hồi Zalo gần như tức thì, rất yên tâm khi đặt hàng.", "author": "Anh Quốc Huy", "role": "Khách hàng thân thiết"},
            ],
            "stats": [
                {"num": "98%", "label": "Khách hàng hài lòng"},
                {"num": "4.9 ★", "label": "Đánh giá thực tế"},
                {"num": "24/7", "label": "Hỗ trợ qua Zalo"},
            ],
            "faqs": [
                {"q": f"Làm sao để nhận tư vấn và đặt {ten_sp} nhanh nhất?", "a": f"Bạn chỉ cần bấm nút Nhắn Zalo ({lien_he}) ngay trên trang, đội ngũ sẽ phản hồi chi tiết trong ít phút."},
                {"q": "Có chính sách cam kết chất lượng hay đổi trả không?", "a": "Chúng tôi cam kết 100% đúng chất lượng như mô tả và đồng hành hỗ trợ tận tâm trong suốt quá trình sử dụng."},
                {"q": "Hiện đang có chương trình ưu đãi nào khi đặt hôm nay?", "a": f"Khách đặt trực tiếp qua trang này được hưởng trọn ưu đãi: {mo_ta[:140]}."},
            ],
            "offer_title": f"Sẵn sàng trải nghiệm {ten_sp} ngay hôm nay?",
            "offer_sub": f"Kết nối trực tiếp qua {lien_he} để giữ suất ưu đãi tốt nhất tuần này.",
        }

        ai_raw = agent_worker.call_gemini(
            f"Hãy đóng vai Giám đốc Sáng tạo & Copywriter Landing Page chuyển đổi cao. Viết nội dung trang bán hàng 8 khối sắc bén, giàu cảm xúc cho:\n"
            f"- Tên sản phẩm/thương hiệu: {ten_sp}\n"
            f"- Điểm mạnh / Bảng giá / Ưu đãi khách cung cấp: {mo_ta}\n"
            f"- Liên hệ Zalo/Link: {lien_he}\n\n"
            "Trả về ĐÚNG 1 JSON object hợp lệ (không viết chữ ngoài JSON) gồm:\n"
            '{"badge": "nhãn ngắn <7 từ", "headline": "tiêu đề chính cuốn hút 10-16 từ", '
            '"subhead": "đoạn dẫn thuyết phục 22-36 từ", "cta_text": "nút CTA <7 từ", '
            '"hero_card_title": "tiêu đề hộp điểm nhấn bên phải Hero", '
            '"hero_bullets": ["điểm đắt giá 1", "điểm đắt giá 2", "điểm đắt giá 3"], '
            '"stamp_title": "chứng thực ngắn vd ⭐ 4.9/5 từ 1.200+ khách", "stamp_sub": "cam kết phụ ngắn", '
            '"stats": [{"num": "con số 1", "label": "nhãn"}, {"num": "con số 2", "label": "nhãn"}, {"num": "con số 3", "label": "nhãn"}], '
            '"benefits": [{"icon": "emoji", "title": "lợi ích 1", "desc": "18-28 từ"}, {"icon": "emoji", "title": "lợi ích 2", "desc": "..."}, {"icon": "emoji", "title": "lợi ích 3", "desc": "..."}], '
            '"packages": [{"tag": "nhãn gói 1", "name": "tên gói 1", "price": "giá gói 1 (lấy từ mô tả hoặc ghi mức hợp lý)", "items": ["quyền lợi 1", "quyền lợi 2", "quyền lợi 3"]}, '
            '{"tag": "Bán chạy nhất", "name": "tên gói 2 chủ lực", "price": "giá gói 2", "items": ["quyền lợi 1", "quyền lợi 2", "quyền lợi 3"]}, '
            '{"tag": "Cao cấp", "name": "tên gói 3", "price": "giá gói 3", "items": ["quyền lợi 1", "quyền lợi 2", "quyền lợi 3"]}], '
            '"reviews": [{"quote": "nhận xét chân thực 18-26 từ", "author": "Tên khách 1", "role": "Nghề nghiệp/Thành phố"}, {"quote": "...", "author": "Tên khách 2", "role": "..."}, {"quote": "...", "author": "Tên khách 3", "role": "..."}], '
            '"faqs": [{"q": "câu hỏi thực tế 1?", "a": "câu trả lời thuyết phục"}, {"q": "câu hỏi 2?", "a": "..."}, {"q": "câu hỏi 3?", "a": "..."}], '
            '"offer_title": "câu chốt đơn cuối trang", "offer_sub": "lời mời an tâm + thông tin liên hệ"}',
            "Bạn là chuyên gia thiết kế Landing Page studio cao cấp tại Việt Nam.",
        )
        if ai_raw:
            try:
                m_j = re.search(r"\{.*\}", ai_raw, re.S)
                if m_j:
                    parsed = json.loads(m_j.group(0))
                    for k_cp in ("badge", "headline", "subhead", "cta_text", "hero_card_title", "stamp_title", "stamp_sub", "offer_title", "offer_sub"):
                        if isinstance(parsed.get(k_cp), str) and parsed[k_cp].strip():
                            copy_data[k_cp] = parsed[k_cp].strip()
                    for k_lst, min_n in (("hero_bullets", 3), ("benefits", 3), ("packages", 3), ("reviews", 2), ("stats", 3), ("faqs", 2)):
                        if isinstance(parsed.get(k_lst), list) and len(parsed[k_lst]) >= min_n:
                            copy_data[k_lst] = parsed[k_lst][:3]
            except Exception:
                pass

        esc = lambda s: html.escape(str(s or ""))
        bullets_html = "".join(f"<li><span>✓</span><div>{esc(b)}</div></li>" for b in copy_data["hero_bullets"])
        stats_html = "".join(
            f'<div class="stat"><b>{esc(st.get("num","99%"))}</b><span>{esc(st.get("label",""))}</span></div>'
            for st in copy_data["stats"]
        )
        cards_html = "".join(
            f'<div class="card"><div class="ic">{esc(b.get("icon","✨"))}</div><h3>{esc(b.get("title",""))}</h3><p>{esc(b.get("desc",""))}</p></div>'
            for b in copy_data["benefits"]
        )
        pkgs_html = []
        for idx_p, pk in enumerate(copy_data["packages"][:3]):
            is_hot = idx_p == 1
            items_li = "".join(f"<li>✓ {esc(it)}</li>" for it in (pk.get("items") or [])[:4])
            hot_badge = '<span class="hot-tag">🔥 ĐƯỢC CHỌN NHIỀU NHẤT</span>' if is_hot else ""
            btn_cls = "btn btn-main" if is_hot else "btn btn-soft"
            pkgs_html.append(
                f'<div class="pkg{" hot" if is_hot else ""}">{hot_badge}'
                f'<span class="pk-tag">{esc(pk.get("tag",""))}</span>'
                f'<h3>{esc(pk.get("name",""))}</h3>'
                f'<div class="pk-price">{esc(pk.get("price",""))}</div>'
                f'<ul>{items_li}</ul>'
                f'<a class="{btn_cls}" href="{cta_href}" target="_blank" rel="noopener">Chọn gói này →</a></div>'
            )
        steps_html = "".join(
            f'<div class="card"><div class="step-no">0{i+1}</div><h3>{esc(st.get("title",""))}</h3><p>{esc(st.get("desc",""))}</p></div>'
            for i, st in enumerate(copy_data["steps"][:3])
        )
        revs_html = "".join(
            f'<div class="card"><div class="stars">★★★★★</div><p class="qt">“{esc(rv.get("quote",""))}”</p><b>{esc(rv.get("author",""))}</b><span class="rl">{esc(rv.get("role",""))}</span></div>'
            for rv in copy_data["reviews"][:3]
        )
        faqs_html = "".join(
            f'<details class="faq"{" open" if i==0 else ""}><summary>{esc(fq.get("q",""))}</summary><p>{esc(fq.get("a",""))}</p></details>'
            for i, fq in enumerate(copy_data["faqs"][:3])
        )

        font_link = (
            "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Lora:ital,wght@0,600;0,700;1,600&display=swap"
            if th["serif"]
            else "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap"
        )
        heading_font = '"Lora",Georgia,serif' if th["serif"] else '"Be Vietnam Pro",system-ui,sans-serif'
        nav_bg = "rgba(251,247,240,.90)" if th["light"] else "rgba(6,13,26,.84)"
        bg_mesh = (
            "none"
            if th["light"]
            else f"radial-gradient(840px 440px at 14% -4%,{c1}35,transparent 60%),radial-gradient(760px 400px at 88% 0%,{c3}28,transparent 58%)"
        )

        def _render_lp(is_preview: bool) -> str:
            wm = (
                f'<div style="position:sticky;top:0;z-index:99;background:linear-gradient(90deg,{c1},{c3});color:#fff;'
                'text-align:center;padding:8px 14px;font-size:13px;font-weight:800">'
                '👀 BẢN XEM TRƯỚC TRỰC TIẾP TRÊN KIEMTIEN.DETA.VN — Quét 29.000đ bên dưới để gỡ thanh này &amp; tải file index.html sạch!</div>'
                if is_preview
                else ""
            )
            guard_js = (
                "<script>document.addEventListener('contextmenu',function(e){e.preventDefault();});</script>"
                if is_preview
                else ""
            )
            return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(ten_sp)} — {esc(copy_data['headline'])}</title>
<meta name="description" content="{esc(copy_data['subhead'])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{font_link}" rel="stylesheet">
<style>
:root{{--c1:{c1};--c2:{c2};--c3:{c3};--bg:{th['bg']};--surface:{th['surface']};--card:{th['card']};--line:{th['line']};--txt:{th['txt']};--muted:{th['muted']}}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;font:400 16px/1.68 "Be Vietnam Pro",system-ui,sans-serif;background:var(--bg);background-image:{bg_mesh};color:var(--txt);overflow-x:hidden}}
h1,h2,h3{{font-family:{heading_font};line-height:1.18;margin:0;letter-spacing:-.02em}}
.w{{max-width:1100px;margin:0 auto;padding:0 20px}}
.topbar{{position:sticky;top:0;z-index:30;background:{nav_bg};backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}}
.topbar .w{{height:68px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.brand{{font-family:{heading_font};font-weight:800;font-size:21px;text-decoration:none;color:var(--txt);display:flex;align-items:center;gap:10px}}
.brand-dot{{width:34px;height:34px;border-radius:11px;background:linear-gradient(135deg,var(--c1),var(--c3));color:#fff;display:grid;place-items:center;font-size:16px;font-family:sans-serif}}
.nav-links{{display:flex;gap:24px;font-size:14.5px;font-weight:600;color:var(--muted)}}
.nav-links a{{color:inherit;text-decoration:none}}
.nav-links a:hover{{color:var(--c1)}}
.btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;text-decoration:none;font-weight:800;font-size:15px;padding:13px 24px;border-radius:999px;transition:transform .16s,box-shadow .16s;cursor:pointer}}
.btn:hover{{transform:translateY(-2px)}}
.btn-main{{background:linear-gradient(135deg,var(--c1),var(--c2));color:#fff;box-shadow:0 12px 28px -8px {c1}80}}
.btn-soft{{background:var(--card);color:var(--txt);border:1.5px solid var(--line)}}
.hero{{padding:56px 0 64px}}
.hero-grid{{display:grid;grid-template-columns:1.08fr .92fr;gap:42px;align-items:center}}
.badge{{display:inline-block;padding:6px 14px;border-radius:999px;background:var(--card);border:1px solid var(--line);font-size:12.5px;font-weight:800;color:var(--c1);letter-spacing:.05em;margin-bottom:16px}}
h1{{font-size:clamp(32px,4.8vw,52px);font-weight:800;margin-bottom:16px}}
.sub{{font-size:17.5px;color:var(--muted);margin:0 0 26px;max-width:540px}}
.acts{{display:flex;flex-wrap:wrap;gap:12px}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:32px;padding-top:24px;border-top:1px solid var(--line)}}
.stat b{{display:block;font-family:{heading_font};font-size:26px;font-weight:800;color:var(--c1)}}
.stat span{{font-size:13px;color:var(--muted)}}
.showcase-card{{position:relative;background:var(--surface);border:1.5px solid var(--line);border-radius:26px;padding:30px;box-shadow:0 26px 56px -22px rgba(0,0,0,.22)}}
.showcase-card .sc-kicker{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--c3);margin-bottom:8px}}
.showcase-card h3{{font-size:23px;margin-bottom:16px}}
.sc-list{{list-style:none;padding:0;margin:0 0 20px}}
.sc-list li{{display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-bottom:1px dashed var(--line);font-size:14.5px}}
.sc-list li:last-child{{border-bottom:0}}
.sc-list li span{{width:22px;height:22px;border-radius:50%;background:var(--c1);color:#fff;display:grid;place-items:center;font-size:12px;font-weight:800;flex:none;margin-top:2px}}
.stamp{{margin-top:14px;padding:13px 16px;border-radius:16px;background:var(--bg);border:1px solid var(--line);font-size:13.5px}}
.stamp b{{display:block;color:var(--c1);font-size:14.5px}}
section.sec{{padding:64px 0}}
section.sec-alt{{padding:64px 0;background:var(--surface);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
.sec-head{{text-align:center;max-width:650px;margin:0 auto 38px}}
.sec-head .eyebrow{{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--c3);display:block;margin-bottom:8px}}
.sec-head h2{{font-size:clamp(26px,3.6vw,38px);margin-bottom:10px}}
.sec-head p{{margin:0;color:var(--muted)}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:26px}}
.card .ic{{width:46px;height:46px;border-radius:14px;background:{c1}1F;display:grid;place-items:center;font-size:23px;margin-bottom:14px}}
.card h3{{font-size:19.5px;margin-bottom:8px}}
.card p{{margin:0;color:var(--muted);font-size:15px}}
.pkg{{background:var(--card);border:1px solid var(--line);border-radius:24px;padding:28px;display:flex;flex-direction:column;position:relative}}
.pkg.hot{{border:2px solid var(--c1);box-shadow:0 22px 48px -18px {c1}45}}
.hot-tag{{position:absolute;top:-13px;left:22px;background:linear-gradient(135deg,var(--c1),var(--c3));color:#fff;font-size:11.5px;font-weight:800;padding:4px 12px;border-radius:999px}}
.pk-tag{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}}
.pkg h3{{font-size:21px;margin:6px 0 8px}}
.pk-price{{font-family:{heading_font};font-size:28px;font-weight:800;color:var(--c1);margin:4px 0 16px}}
.pkg ul{{list-style:none;padding:0;margin:0 0 22px;flex:1}}
.pkg li{{padding:7px 0;border-bottom:1px dashed var(--line);font-size:14.5px}}
.pkg li:last-child{{border-bottom:0}}
.step-no{{font-family:{heading_font};font-size:32px;font-weight:800;color:var(--c3);line-height:1;margin-bottom:10px}}
.stars{{color:#F59E0B;letter-spacing:2px;margin-bottom:10px;font-size:15px}}
.qt{{font-style:italic;color:var(--txt)!important;margin-bottom:14px!important}}
.rl{{display:block;font-size:13px;color:var(--muted);margin-top:2px}}
.faq-wrap{{max-width:760px;margin:0 auto}}
details.faq{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:17px 22px;margin-bottom:12px}}
details.faq summary{{font-weight:700;cursor:pointer;font-size:16.5px;list-style:none;display:flex;justify-content:space-between;align-items:center}}
details.faq summary::-webkit-details-marker{{display:none}}
details.faq summary::after{{content:"+";font-size:22px;color:var(--c1)}}
details.faq[open] summary::after{{content:"−"}}
details.faq p{{margin:11px 0 0;color:var(--muted);font-size:15px}}
.cta-box{{margin:20px 0 60px;padding:48px 28px;border-radius:28px;text-align:center;background:linear-gradient(135deg,{c1}22,{c3}18);border:1.5px solid {c1}55}}
.cta-box h2{{font-size:clamp(26px,3.8vw,38px);margin-bottom:10px}}
.cta-box p{{margin:0 auto 24px;color:var(--muted);max-width:580px}}
footer{{text-align:center;padding:28px 0 46px;color:var(--muted);font-size:14px;border-top:1px solid var(--line)}}
.float-zalo{{position:fixed;right:18px;bottom:18px;z-index:45;background:linear-gradient(135deg,var(--c1),var(--c2));color:#fff;text-decoration:none;font-weight:800;font-size:14px;padding:12px 18px;border-radius:999px;box-shadow:0 12px 28px -6px {c1}88}}
@media(max-width:860px){{.nav-links{{display:none}}.hero-grid,.grid-3{{grid-template-columns:1fr}}}}
</style>
{guard_js}
</head>
<body>
{wm}
<header class="topbar">
  <div class="w">
    <a class="brand" href="#"><span class="brand-dot">✦</span>{esc(ten_sp)}</a>
    <nav class="nav-links">
      <a href="#uu-diem">Điểm khác biệt</a>
      <a href="#bang-gia">Bảng gói &amp; Ưu đãi</a>
      <a href="#danh-gia">Khách hàng</a>
      <a href="#hoi-dap">Hỏi đáp</a>
    </nav>
    <a class="btn btn-main" style="padding:9px 18px;font-size:14px" href="{cta_href}" target="_blank" rel="noopener">Liên hệ ngay</a>
  </div>
</header>

<section class="hero">
  <div class="w hero-grid">
    <div>
      <span class="badge">{esc(copy_data['badge'])}</span>
      <h1>{esc(copy_data['headline'])}</h1>
      <p class="sub">{esc(copy_data['subhead'])}</p>
      <div class="acts">
        <a class="btn btn-main" href="{cta_href}" target="_blank" rel="noopener">{esc(copy_data['cta_text'])}</a>
        <a class="btn btn-soft" href="#bang-gia">Xem các gói ưu đãi</a>
      </div>
      <div class="stats">{stats_html}</div>
    </div>
    <div class="showcase-card">
      <div class="sc-kicker">Cam kết giá trị cốt lõi</div>
      <h3>{esc(copy_data['hero_card_title'])}</h3>
      <ul class="sc-list">{bullets_html}</ul>
      <div class="stamp">
        <b>{esc(copy_data['stamp_title'])}</b>
        <span>{esc(copy_data['stamp_sub'])}</span>
      </div>
    </div>
  </div>
</section>

<section class="sec-alt" id="uu-diem">
  <div class="w">
    <div class="sec-head">
      <span class="eyebrow">Giá trị khác biệt</span>
      <h2>Vì sao khách hàng tin chọn {esc(ten_sp)}?</h2>
    </div>
    <div class="grid-3">{cards_html}</div>
  </div>
</section>

<section class="sec" id="bang-gia">
  <div class="w">
    <div class="sec-head">
      <span class="eyebrow">Lựa chọn linh hoạt</span>
      <h2>Các gói sản phẩm &amp; Ưu đãi hiện có</h2>
    </div>
    <div class="grid-3">{"".join(pkgs_html)}</div>
  </div>
</section>

<section class="sec-alt" id="danh-gia">
  <div class="w">
    <div class="sec-head">
      <span class="eyebrow">Quy trình 3 bước &amp; Cảm nhận thực tế</span>
      <h2>Đặt hàng tinh gọn — Trải nghiệm an tâm</h2>
    </div>
    <div class="grid-3" style="margin-bottom:34px">{steps_html}</div>
    <div class="grid-3">{revs_html}</div>
  </div>
</section>

<section class="sec" id="hoi-dap">
  <div class="w">
    <div class="sec-head">
      <span class="eyebrow">Giải đáp thắc mắc</span>
      <h2>Câu hỏi thường gặp</h2>
    </div>
    <div class="faq-wrap">{faqs_html}</div>
    <div class="cta-box" id="lien-he-ngay">
      <h2>{esc(copy_data['offer_title'])}</h2>
      <p>{esc(copy_data['offer_sub'])}</p>
      <a class="btn btn-main" href="{cta_href}" target="_blank" rel="noopener">{esc(copy_data['cta_text'])}</a>
    </div>
  </div>
</section>

<footer><div class="w">© {now_vn().year} <b>{esc(ten_sp)}</b> · Tư vấn &amp; Hỗ trợ trực tiếp: <b>{esc(lien_he)}</b></div></footer>
<a class="float-zalo" href="{cta_href}" target="_blank" rel="noopener">💬 Liên hệ {esc(lien_he[:18])}</a>
</body>
</html>"""

        preview_id = "lp_" + secrets.token_hex(8)
        clean_html = _render_lp(is_preview=False)
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO landing_previews (id, ten_sp, html_clean, tao_luc) VALUES (?, ?, ?, ?)",
                (preview_id, ten_sp, clean_html, now_vn().isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()

        return {
            "tieu_de": f"🚀 Đã thiết kế xong Landing Page 8 khối cho: {ten_sp} (Miễn phí 100%)",
            "diem_tot": [
                "Kiến trúc 8 khối chuẩn Studio: Thanh điều hướng kính mờ, Split Hero 2 cột kèm thẻ chứng thực, 3 Lý do chọn, Bảng 3 gói giá, Quy trình 3 bước, Đánh giá khách hàng, FAQ & Nút Zalo nổi trên điện thoại.",
                "🎁 Mở miễn phí 100%: File index.html bên dưới đã sạch hoàn toàn (không đóng dấu quảng cáo), sẵn sàng tải về gắn tên miền chạy ngay!",
            ],
            "preview_id": preview_id,
            "preview_html": clean_html,
            "ban_day_du": clean_html,
            "dl_url": f"/api/landing/tai?pid={preview_id}&dl=1",
            "view_url": f"/api/landing/tai?pid={preview_id}&xem=1",
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "than-so-hoc":
        ho_ten = (payload.get("ho_ten") or "").strip()[:80] or "Nguyễn Minh Anh"
        ngay_sinh = (payload.get("ngay_sinh") or "").strip()[:30] or "15/08/1996"
        cau_hoi = (payload.get("cau_hoi") or "").strip()[:300] or "Định hướng công việc, tài chính và cơ hội bứt phá năm 2026 - 2027"

        prof = numerology_engine.compute_numerology(ho_ten, ngay_sinh, current_year=now_vn().year)
        manh_str = ", ".join(x["ten"] for x in prof["mui_ten_manh"]) or "Không có trục 3 số liền kề (năng lượng phân bổ đa điểm linh hoạt)"
        trong_str = ", ".join(x["ten"] for x in prof["mui_ten_trong"]) or "Không bị trống hoàn toàn trục 3 số nào"
        peaks_str = "; ".join(f"Đỉnh {p['dinh']} (Số {p['so']} ở tuổi {p['tuoi']} - năm {p['nam']})" for p in prof["dinh_cao"])

        ai_prompt = (
            f"Hãy đóng vai Chuyên gia Thần số học Pythagoras thực chiến, sâu sắc và thấu cảm. "
            f"Luận giải BẢN ĐẦY ĐỦ 100% cá nhân hóa cho:\n"
            f"- Họ tên khai sinh: {prof['ho_ten']} | Ngày sinh dương lịch: {prof['ngay_sinh']}\n"
            f"- Con số Chủ đạo: {prof['so_chu_dao_nhan']} ({prof['danh_xung']})\n"
            f"- Chỉ số Sứ mệnh (từ họ tên): {prof['su_menh']} | Chỉ số Linh hồn (khát khao nội tâm): {prof['linh_hon']} | Chỉ số Nhân cách (ấn tượng bên ngoài): {prof['nhan_cach']} | Chỉ số Trưởng thành: {prof['truong_thanh']}\n"
            f"- Năm cá nhân {prof['nam_hien_tai']}: Số {prof['nam_ca_nhan']} ({prof['thong_diep_nam']})\n"
            f"- Năm cá nhân {prof['nam_hien_tai'] + 1}: Số {prof['nam_ca_nhan_sau']}\n"
            f"- Biểu đồ ngày sinh: Mũi tên mạnh = [{manh_str}]; Trục trống cần bù đắp = [{trong_str}]\n"
            f"- Kim tự tháp 4 Đỉnh cao: {peaks_str}\n"
            f"- Vấn đề bạn ấy đang trăn trở nhất: \"{cau_hoi}\"\n\n"
            "Hãy trả về bài luận giải đầy đủ, rõ ràng, trình bày thành 5 mục đánh số (không dùng markdown ** quá rối, dùng tiêu đề hoa rõ ràng):\n"
            "Dòng đầu tiên bắt buộc bắt đầu bằng 'THÔNG ĐIỆP CỐT LÕI: ' (1 câu đắt giá 18-28 từ tóm tắt kim chỉ nam năm nay để in lên thẻ Bản đồ).\n"
            "Sau đó luận chi tiết 5 phần:\n"
            "1. BẢN SẮC CỐT LÕI & TỔ HỢP CHỦ ĐẠO × SỨ MỆNH (điểm mạnh trời phú & môi trường phát huy tốt nhất)\n"
            "2. THẾ GIỚI NỘI TÂM (LINH HỒN) & ẤN TƯỢNG BÊN NGOÀI (NHÂN CÁCH) — độ vênh hoặc hòa hợp bên trong và bên ngoài\n"
            "3. GIẢI MÃ BIỂU ĐỒ NGÀY SINH & CÁCH HÓA GIẢI TRỤC TRỐNG BẰNG HÀNH ĐỘNG CỤ THỂ\n"
            f"4. CHIẾN LƯỢC SỰ NGHIỆP & TÀI CHÍNH NĂM CÁ NHÂN {prof['nam_hien_tai']}–{prof['nam_hien_tai']+1} (trả lời thẳng vào nỗi trăn trở: {cau_hoi})\n"
            "5. LỘ TRÌNH 4 ĐỈNH CAO KIM TỰ THÁP & 3 VIỆC NÊN BẮT ĐẦU NGAY TUẦN NÀY."
        )
        ai_reading = agent_worker.call_gemini(
            ai_prompt,
            "Bạn là chuyên gia Thần số học Pythagoras uy tín, văn phong ấm áp, thực tế, không mê tín cực đoan.",
        )

        core_advice = prof["thong_diep_nam"]
        if ai_reading:
            m_core = re.search(r"THÔNG ĐIỆP CỐT LÕI:\s*(.+)", ai_reading)
            if m_core:
                core_advice = m_core.group(1).strip().strip('"“”*')
            full_text = ai_reading.strip()
        else:
            full_text = (
                f"THÔNG ĐIỆP CỐT LÕI: {prof['thong_diep_nam']}\n\n"
                f"1. BẢN SẮC CỐT LÕI (SỐ CHỦ ĐẠO {prof['so_chu_dao_nhan']} × SỨ MỆNH {prof['su_menh']}):\n"
                f"Bạn mang tần số của {prof['danh_xung']}. {prof['mo_ta_ngan']} Khi kết hợp cùng Chỉ số Sứ mệnh {prof['su_menh']}, bạn phát huy mạnh nhất khi được làm việc có ý nghĩa rõ ràng và chủ động tạo giá trị thật.\n\n"
                f"2. NỘI TÂM & NHÂN CÁCH (LINH HỒN {prof['linh_hon']} · NHÂN CÁCH {prof['nhan_cach']}):\n"
                f"Bên sâu trong tâm thức, Linh hồn số {prof['linh_hon']} định hình điều khiến bạn thực sự hạnh phúc, trong khi người xung quanh cảm nhận bạn qua lăng kính Nhân cách số {prof['nhan_cach']}.\n\n"
                f"3. BIỂU ĐỒ NGÀY SINH & TRỤC CẦN BÙ ĐẮP:\n"
                f"- Thế mạnh sẵn có: {manh_str}.\n- Điểm cần rèn luyện ảo hóa: {trong_str}.\n\n"
                f"4. ĐỊNH HƯỚNG NĂM CÁ NHÂN {prof['nam_hien_tai']} (NĂM SỐ {prof['nam_ca_nhan']}):\n"
                f"{prof['thong_diep_nam']}\nBước sang năm {prof['nam_hien_tai']+1} (Năm cá nhân số {prof['nam_ca_nhan_sau']}): {prof['thong_diep_nam_sau']}\n\n"
                f"5. KIM TỰ THÁP 4 ĐỈNH CAO ĐỜI NGƯỜI:\n{peaks_str}."
            )

        svg_card = numerology_engine.build_numerology_svg(prof, core_advice=core_advice)
        months_12 = numerology_engine.compute_12_months_roadmap(prof)
        vip_booklet_html = numerology_engine.build_vip_booklet_html(prof, core_advice=core_advice, reading_5_parts=full_text)
        booklet_id = "tsh_" + secrets.token_hex(8)
        slug_tsh = re.sub(r"[^a-z0-9]+", "-", numerology_engine.strip_vietnamese(prof["ho_ten"]).lower()).strip("-")[:28] or "ho-so"
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO deliverables (id, loai, slug, html_clean, csv_clean, tao_luc) VALUES (?, ?, ?, ?, '', ?)",
                (booklet_id, "cam-nang-tsh", slug_tsh, vip_booklet_html, now_vn().isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()

        header_summary = (
            f"=== 🔮 HỒ SƠ THẦN SỐ HỌC PYTHAGORAS BẢN ĐẦY ĐỦ (MIỄN PHÍ 100% TẠI KIEMTIEN.DETA.VN) ===\n"
            f"• Họ và tên: {prof['ho_ten']}  |  Ngày sinh: {prof['ngay_sinh']}\n"
            f"• Con số Chủ đạo: {prof['so_chu_dao_nhan']} — {prof['danh_xung']}\n"
            f"• Sứ mệnh: {prof['su_menh']}  |  Linh hồn: {prof['linh_hon']}  |  Nhân cách: {prof['nhan_cach']}  |  Trưởng thành: {prof['truong_thanh']}\n"
            f"• Năm cá nhân {prof['nam_hien_tai']}: Số {prof['nam_ca_nhan']}  |  Năm {prof['nam_hien_tai']+1}: Số {prof['nam_ca_nhan_sau']}\n"
            f"• Kim tự tháp 4 Đỉnh cao: {peaks_str}\n"
            f"=====================================================================\n\n"
        )

        return {
            "tieu_de": f"🔮 Bản đồ Thần Số Học của {prof['ho_ten']} — Số Chủ Đạo {prof['so_chu_dao_nhan']} ({prof['danh_xung']})",
            "diem_tot": [
                f"Tổ hợp cốt lõi: Chủ đạo {prof['so_chu_dao_nhan']} · Sứ mệnh {prof['su_menh']} · Linh hồn {prof['linh_hon']} · Nhân cách {prof['nhan_cach']} · Năm cá nhân {prof['nam_hien_tai']} là Số {prof['nam_ca_nhan']}.",
                "🎁 Tặng miễn phí 100% từ Deta AI Lab: Mở khóa trọn bộ 5 phần luận giải + Thẻ Bản Đồ PNG nét cao + Sổ tay Cẩm nang Lộ trình 12 Tháng A4 (xuất PDF sạch)!",
            ],
            "ho_ten": prof["ho_ten"],
            "ngay_sinh": prof["ngay_sinh"],
            "ho_so": prof,
            "thong_diep_cot_loi": core_advice,
            "svg_card": svg_card,
            "ban_day_du": header_summary + full_text,
            "bai_luan_5_phan": full_text,
            "booklet_id": booklet_id,
            "booklet_view_url": f"/api/tai-pham-vat?pid={booklet_id}&xem=1",
            "booklet_dl_url": f"/api/tai-pham-vat?pid={booklet_id}&dl=1",
            "xem_truoc_2_thang": months_12[:2],
            "months_12": months_12,
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "tao-cv-ats":
        ho_ten_cv = (payload.get("ho_ten_cv") or "").strip()[:180]
        vi_tri = (payload.get("vi_tri") or "").strip()[:120]
        kinh_nghiem = (payload.get("kinh_nghiem") or "").strip()[:2500]
        ngon_ngu = (payload.get("ngon_ngu") or "vi").strip()[:20]
        cv_out = micro_tools_engine.generate_ats_cv(ho_ten_cv, vi_tri, kinh_nghiem, ngon_ngu, agent_worker.call_gemini)
        deliv_id = "cv_" + secrets.token_hex(8)
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO deliverables (id, loai, slug, html_clean, csv_clean, tao_luc) VALUES (?, ?, ?, ?, '', ?)",
                (deliv_id, "tao-cv-ats", cv_out["slug"], cv_out["clean_html"], now_vn().isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()
        return {
            "tieu_de": f"📄 Đã hoàn thiện CV Chuẩn ATS A4 & Thư Ứng Tuyển cho: {cv_out['full_name']} (Miễn phí 100%)",
            "diem_tot": [
                f"Đã chuẩn hóa cấu trúc Harvard ATS cho vị trí '{cv_out['target_role']}' — trình đọc hồ sơ tự động nhận diện 100% từ khóa, không lỗi bảng biểu.",
                "🎁 Mở miễn phí 100%: Kèm sẵn 1 trang Thư Ứng Tuyển (Cover Letter), không watermark, cho phép sửa chữ trực tiếp & bấm xuất PDF khổ A4 ngay!",
            ],
            "preview_id": deliv_id,
            "preview_html": cv_out["clean_html"],
            "ban_day_du": cv_out["clean_html"],
            "view_url": f"/api/tai-pham-vat?pid={deliv_id}&xem=1",
            "dl_url": f"/api/tai-pham-vat?pid={deliv_id}&dl=1",
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "lich-30-ngay":
        ten_shop = (payload.get("ten_shop") or "").strip()[:120]
        khach_hang = (payload.get("khach_hang") or "").strip()[:1500]
        kenh_chinh = (payload.get("kenh_chinh") or "all").strip()[:24]
        cal_out = micro_tools_engine.generate_30day_calendar(ten_shop, khach_hang, kenh_chinh, agent_worker.call_gemini)
        deliv_id = "cal_" + secrets.token_hex(8)
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO deliverables (id, loai, slug, html_clean, csv_clean, tao_luc) VALUES (?, ?, ?, ?, ?, ?)",
                (deliv_id, "lich-30-ngay", cal_out["slug"], cal_out["full_board_html"], cal_out["csv_utf8_bom"], now_vn().isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()
        return {
            "tieu_de": f"📅 Đã lập xong Lịch 30 Ngày Bài Đăng & Kịch Bản Hook cho: {cal_out['shop']} (Miễn phí 100%)",
            "diem_tot": [
                "Trọn bộ 30/30 ngày nội dung xoay vòng 6 trụ cột chuyển đổi (Chạm nỗi đau → Giải pháp → Bằng chứng → Hậu trường → Xóa rào cản → Chốt đơn).",
                "🎁 Mở miễn phí 100%: Tải ngay File Bảng Tính Excel (.CSV chuẩn tiếng Việt có dấu) mở trên Excel / Google Sheets dùng cho cả tháng!",
            ],
            "preview_id": deliv_id,
            "preview_html": cal_out["full_board_html"],
            "ban_day_du": cal_out["full_board_html"],
            "csv_url": f"/api/tai-pham-vat?pid={deliv_id}&csv=1",
            "view_url": f"/api/tai-pham-vat?pid={deliv_id}&xem=1",
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    if cong_cu == "chatbot-chot-don":
        ten_shop = (payload.get("ten_shop") or "").strip()[:120] or "Shop Thời Trang & Phụ Kiện Deta"
        san_pham_gia = (payload.get("san_pham_gia") or "").strip()[:1500] or "Sản phẩm chủ lực 350.000đ - 690.000đ, miễn phí vận chuyển từ 2 món, kiểm tra hàng trước khi thanh toán."
        tu_choi = (payload.get("tu_choi") or "").strip()[:800] or "Khách chê giá cao hơn Shopee, bảo để hỏi ý kiến chồng/vợ, sợ hàng không giống ảnh."
        giong_van = (payload.get("giong_van") or "than-thien").strip()[:40]
        tone_map = {
            "than-thien": "Thân thiện, lễ phép (Dạ/Vâng, xưng em - gọi anh/chị), đồng cảm như người nhà",
            "chuyen-gia": "Chuyên gia tư vấn uy tín, dẫn chứng số liệu/khoa học rõ ràng, điềm đạm đáng tin cậy",
            "sang-trong": "Sang trọng, tinh tế (Boutique VIP), tôn vinh đẳng cấp và trải nghiệm cá nhân hóa",
            "genz": "Trẻ trung, năng động, bắt nhịp nhanh, ngắn gọn dễ thương",
        }
        tone_desc = tone_map.get(giong_van, tone_map["than-thien"])

        prompt_req = (
            f"Thiết kế trọn bộ 'BỘ NÃO CHATBOT AI CHỐT ĐƠN (SYSTEM PROMPT + KNOWLEDGE BASE + 5 KỊCH BẢN XỬ LÝ TỪ CHỐI)' cho shop:\n"
            f"- Tên Shop / Thương hiệu: {ten_shop}\n"
            f"- Sản phẩm, bảng giá & chính sách: {san_pham_gia}\n"
            f"- Các lời từ chối khách hay nói nhất: {tu_choi}\n"
            f"- Giọng văn mong muốn: {tone_desc}\n\n"
            "Hãy trả về văn bản trình bày cực kỳ rõ ràng gồm 3 phần:\n"
            "PHẦN 1: SYSTEM PROMPT HOÀN CHỈNH (để chủ shop copy dán thẳng vào ChatGPT / Coze / Pancake AI / SmaxBot / Dify).\n"
            "PHẦN 2: QUY TẮC CHỐNG BỊA ĐẶT (GUARDRAILS) & CẤU TRÚC KHO TRI THỨC.\n"
            "PHẦN 3: 5 KỊCH BẢN MẪU XỬ LÝ TỪ CHỐI (Khách chê đắt, Khách bảo để suy nghĩ/hỏi người nhà, Khách đòi freeship/giảm giá, Khách sợ hàng giả, Chốt xin SĐT + Địa chỉ)."
        )
        ai_out = agent_worker.call_gemini(prompt_req, "Bạn là Kiến trúc sư Prompt Engineering & Tự động hóa Chốt đơn số 1 Việt Nam.")
        fallback_full = (
            f"=== 🤖 PHẦN 1: SYSTEM PROMPT CHUẨN CHO [{ten_shop.upper()}] ===\n"
            "(Copy toàn bộ khung dưới đây dán vào ô System Prompt của Coze / Pancake AI / SmaxBot / ChatGPT / ManyChat)\n\n"
            f"'''\n"
            f"VAI TRÒ & ĐỊNH DANH:\n"
            f"Bạn là Chuyên viên Tư vấn & Chăm sóc khách hàng xuất sắc nhất của [{ten_shop}].\n"
            f"Phong cách giao tiếp: {tone_desc}.\n\n"
            f"KHO TRI THỨC SẢN PHẨM & CHÍNH SÁCH (CHỈ DÙNG DỮ LIỆU NÀY, TUYỆT ĐỐI KHÔNG BỊA GIÁ):\n"
            f"{san_pham_gia}\n\n"
            f"QUY TRÌNH TƯ VẤN & CHỐT ĐƠN 4 BƯỚC:\n"
            f"1. Chào đón + Hỏi đúng 1 câu làm rõ nhu cầu thực tế của khách (size/màu/mục đích sử dụng).\n"
            f"2. Đề xuất đúng gói sản phẩm lợi nhất (ưu tiên Combo tiết kiệm) kèm lợi ích thực tế.\n"
            f"3. Hóa giải rào cản theo công thức 3A: Đồng cảm (Acknowledge) → Neo giá trị & Cam kết kiểm hàng (Assure) → Đưa lựa chọn chốt (Advance).\n"
            f"4. Xin Số điện thoại + Địa chỉ nhận hàng ngay khi khách có tín hiệu ưng ý.\n\n"
            f"QUY TẮC CẤM (GUARDRAILS):\n"
            f"- Không trả lời dài quá 4 câu trong 1 tin nhắn (giữ nhịp chat tự nhiên như người thật gõ).\n"
            f"- Không tự ý giảm giá ngoài chính sách đã liệt kê.\n"
            f"- Nếu khách hỏi vấn đề ngoài phạm vi, hãy lịch sự xin SĐT Zalo để Quản lý {ten_shop} gọi hỗ trợ trực tiếp trong 5 phút.\n"
            f"'''\n\n"
            f"=== 🛡️ PHẦN 2: BỘ 5 KỊCH BẢN XỬ LÝ TỪ CHỐI THỰC CHIẾN ({ten_shop}) ===\n\n"
            f"1) KHI KHÁCH CHÊ ĐẮT / SO SÁNH VỚI HÀNG RẺ SHOPEE:\n"
            f"   💬 Mẫu trả lời: \"Dạ em rất hiểu băn khoăn của mình ạ! Thực ra các dòng giá rẻ trôi nổi thường cắt giảm chất liệu nên dùng rất nhanh xuống cấp. Bản chuẩn tại {ten_shop} được cam kết chất lượng thật kèm chính sách kiểm tra hàng ưng ý mới thanh toán — tính ra chi phí mỗi ngày chưa tới vài nghìn đồng mà mình yên tâm tuyệt đối. Hôm nay bên em đang có suất ưu đãi vận chuyển, em giữ sẵn 1 suất cho mình nhé ạ?\"\n\n"
            f"2) KHI KHÁCH BẢO 'ĐỂ CHỊ XEM THÊM / HỎI Ý KIẾN CHỒNG ĐÃ':\n"
            f"   💬 Mẫu trả lời: \"Dạ vâng ạ, mình cứ tham khảo kỹ cho yên tâm nhé! Nhân tiện hôm nay {ten_shop} đang có quà tặng/ưu đãi giới hạn trong ngày, anh/chị cho em xin SĐT Zalo để em gửi ảnh/video quay cận cảnh sản phẩm thật và giữ sẵn mã ưu đãi 24h cho mình tiện đưa người nhà xem nhé ạ?\"\n\n"
            f"3) KHI KHÁCH SỢ HÀNG KHÔNG GIỐNG QUẢNG CÁO:\n"
            f"   💬 Mẫu trả lời: \"Dạ anh/chị hoàn toàn yên tâm ạ! Mọi đơn hàng từ {ten_shop} đều được đồng kiểm (mở hộp kiểm tra trực tiếp cùng bưu tá trước khi trả tiền). Nếu không đúng mô tả, mình cứ trả lại ngay mà không mất 1 đồng phí nào ạ. Mình nhận hàng ở tỉnh/thành nào để em báo lịch giao sớm nhất ạ?\"\n\n"
            f"4) KHI KHÁCH XIN FREESHIP / GIẢM GIÁ THÊM:\n"
            f"   💬 Mẫu trả lời: \"Dạ giá niêm yết của {ten_shop} đã được tối ưu sát gốc để đảm bảo chất lượng cao nhất rồi ạ. Tuy nhiên nếu mình lấy theo Combo 2 sản phẩm hoặc đặt ngay trong khung giờ hôm nay, em xin phép áp mã Hỗ trợ phí ship đặc biệt cho đơn của mình nhé. Mình lấy phân loại nào để em lên phiếu ưu đãi luôn ạ?\"\n\n"
            f"5) CÂU CHỐT ĐƠN MƯỢT MÀ (KHI KHÁCH HỎI GIÁ XONG IM LẶNG SAU 15 PHÚT):\n"
            f"   💬 Mẫu trả lời: \"Dạ anh/chị ơi, mẫu mình vừa hỏi kho em hiện chỉ còn đúng vài suất ưu đãi cuối trong ngày. Anh/chị nhắn giúp em SĐT + Địa chỉ để em giữ hàng và đóng gói gửi đi chuyến chiều nay luôn cho mình kịp nhận sớm nhé ạ!\""
        )
        full_text = _fmt_ai_text(ai_out) if (ai_out and len(str(ai_out)) > 180) else fallback_full
        demo_ctx = f"{ten_shop} — {san_pham_gia} (Lưu ý xử lý: {tu_choi})"
        return {
            "tieu_de": f"🤖 Đã thiết kế xong Bộ System Prompt & Kịch Bản Chatbot Chốt Đơn cho: {ten_shop} (Miễn phí 100%)",
            "diem_tot": [
                f"Đã đóng gói chuẩn cấu trúc System Prompt + Guardrails chống bịa giá theo giọng văn '{tone_desc}'.",
                "Kèm sẵn 5 kịch bản hóa giải lời từ chối hóc búa nhất & nút '💬 Chat Thử Trực Tiếp Với Con Bot Vừa Tạo' ngay trên màn hình!",
            ],
            "xem_truoc": full_text[:450] + "\n...",
            "ban_day_du": full_text,
            "demo_shop_context": demo_ctx[:380],
            "ten_shop": ten_shop,
            "da_mo_khoa": True,
            "mien_phi_100": True,
        }

    # Mặc định: /tai-lieu/tao-ai
    return {
        "tieu_de": "📘 Kiến trúc thực chiến: Cách dựng con AI tự kiếm tiền 24/7 (Mở miễn phí 100%)",
        "diem_tot": [
            "Chạy 100% Python 3.12 chuẩn + SQLite (<40MB RAM) kết hợp cầu nối Antigravity CLI (agy --sandbox) gọi Gemini 3.8 Flash tốn 0đ tiền API.",
            "Tích hợp VietQR MBBank + SePay Open Banking API khớp lệnh tự động trong 1–2 giây, tự cấp vé & bắn pháo hoa.",
            "Vòng lặp tự hành kép: 06:00 sáng tự soi SQLite đặt câu hỏi chiến lược + mỗi 2 giờ tự thức dậy thực thi việc mới + 20:30 tối tự báo cáo lên Facebook & Threads.",
        ],
        "xem_truoc": (
            "Sơ đồ kiến trúc đang vận hành trực tiếp tại kiemtien.deta.vn:\n"
            "├── server.py               # ThreadingHTTPServer + SQLite + Cổng Webhook SePay/Casso đa chuẩn\n"
            "├── agent_worker.py         # Cầu nối 'agy --sandbox' (0đ API) + Họp chiến lược 06:00 sáng + Lượt chạy 2h/lần\n"
            "├── social_autopilot.py     # Trình duyệt Bot CDP cô lập tự đăng Facebook, Threads & Group\n"
            "├── data/du-lieu.json       # Sổ cái trung thực 100%: chỉ cộng tiền khi ngân hàng báo giao dịch thật\n"
            "└── public/                 # Giao diện Bento Emerald-Cyan + Bộ công cụ mở miễn phí 100%"
        ),
        "ban_day_du": (
            "=== BẢN THIẾT KẾ CHI TIẾT & BỘ PROMPT HỆ THỐNG (KIEMTIEN.DETA.VN) ===\n\n"
            "1. CẦU NỐI GỌI GEMINI 3.8 FLASH TỐN 0Đ API QUA ANTIGRAVITY CLI (agent_worker.py):\n"
            "   - Chạy tiến trình con cô lập hoàn toàn trong thư mục sandbox riêng (shell=False, BoundedSemaphore(3)):\n"
            "     agy --model gemini-3.8-flash-low --disable-slash-commands --sandbox --output-format json -p \"<PROMPT>\"\n"
            "   - Luôn chèn khóa an toàn đầu prompt: 'QUY TẮC TUYỆT ĐỐI: KHÔNG gọi tool, KHÔNG chạy shell, KHÔNG đọc/ghi file. Chỉ trả lời văn bản thuần.'\n\n"
            "2. MẠCH TIỀN THẬT 1 GIÂY: VIETQR MBBANK + SEPAY OPEN BANKING (server.py):\n"
            "   - Tạo mã đơn ngẫu nhiên DETA + 6 ký tự hex (vd: DETA8F2A1C) gắn vào tham số addInfo của img.vietqr.io.\n"
            "   - Cổng POST /api/webhook/bank xác thực chữ ký / Apikey, chuẩn hóa payload SePay & Casso, lọc trùng tx_ref trong bảng webhook_logs.\n"
            "   - Dùng Regex bắt chính xác mã đơn ngay cả khi ngân hàng tự chèn dấu cách, chỉ cộng vào tien_that khi so_tien >= đơn gốc.\n\n"
            "3. BỘ 3 SYSTEM PROMPT TỰ VẤN 06:00 SÁNG & CHỐT ĐƠN:\n"
            "   - [Prompt Họp Chiến Lược 06:00]: Đọc số viewers, lượt chạy từng công cụ, số lượt mở QR vs. số đơn thành công từ SQLite -> Ép AI trả về JSON {cau_hoi, chan_doan, giai_phap, cach_thuc_hien[3]} và tự đẩy thẳng 3 bước vào bang_viec.cho.\n"
            "   - [Prompt Phễu Chat Thử Miễn Phí]: Cấp token dùng thử gắn kèm hash IP trong bảng free_chat_trials để khách trải nghiệm AI thật ngay trên web.\n\n"
            "4. TỰ ĐỘNG HÓA MẠNG XÃ HỘI KHÔNG CẦN BẤM ALLOW (social_autopilot.py):\n"
            "   - Khởi chạy profile Chrome riêng biệt với cổng CDP nội bộ chỉ lắng nghe trên 127.0.0.1.\n"
            "   - Dùng giao thức WebSocket CDP gốc + DOM.setFileInputFiles để đính kèm ảnh chụp màn hình thật phòng Lab, viết bài độc bản không gắn link vượt bộ lọc Admin Assist và báo cáo đều đặn lúc 20:30 mỗi tối!"
        ),
        "da_mo_khoa": True,
        "mien_phi_100": True,
    }


class DetaHandler(BaseHTTPRequestHandler):
    server_version = "DetaAI/1.0"
    sys_version = ""

    def setup(self) -> None:
        super().setup()
        try:
            self.request.settimeout(15.0)
        except Exception:
            pass

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_HEAD(self) -> None:
        self._is_head = True
        self.do_GET()

    def _send_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin-allow-popups")

    def send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if not getattr(self, "_is_head", False):
            self.wfile.write(raw)

    def send_file(self, filepath: str, content_type: str = "text/html; charset=utf-8") -> None:
        real_target = os.path.realpath(filepath)
        real_pub = os.path.realpath(PUBLIC_DIR)
        real_dulieu = os.path.realpath(DU_LIEU_PATH)
        is_allowed = (real_target == real_dulieu) or real_target.startswith(real_pub + os.sep)
        ext = os.path.splitext(real_target)[1].lower()
        if (
            not is_allowed
            or "/." in real_target
            or ext in (".py", ".db", ".sqlite", ".yml", ".yaml", ".sh", ".env", ".log", ".key")
            or not os.path.isfile(real_target)
        ):
            self.send_json({"loi": "Không tìm thấy trang"}, 404)
            return
        with open(real_target, "rb") as f:
            raw = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self._send_security_headers()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if not getattr(self, "_is_head", False):
            self.wfile.write(raw)

    def read_json_body(self, max_bytes: int = 65536) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (ValueError, TypeError):
            self._last_raw_body = ""
            return {}
        if length <= 0 or length > max_bytes:
            self._last_raw_body = ""
            return {}
        try:
            raw = self.rfile.read(length).decode("utf-8", errors="ignore")
        except Exception:
            self._last_raw_body = ""
            return {}
        self._last_raw_body = raw
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path or "/")
        if ".." in path or "\x00" in path or path.startswith("/."):
            self.send_json({"loi": "Đường dẫn không hợp lệ"}, 403)
            return
        qs = urllib.parse.parse_qs(parsed.query)
        client_ip = get_real_client_ip(self)
        if path.startswith("/api/") and not check_rate_limit(client_ip, "global_get", 180, 60.0):
            self.send_json({"ok": False, "loi": "Tốc độ truy cập quá nhanh, vui lòng thử lại sau ít giây."}, 429)
            return

        if path in ("/", "/index.html"):
            self.send_file(os.path.join(PUBLIC_DIR, "index.html"))
            return
        if path == "/du-lieu.json":
            self.send_file(DU_LIEU_PATH, "application/json; charset=utf-8")
            return
        if path in ("/deta-chat.css", "/copee-chat.css"):
            self.send_file(os.path.join(PUBLIC_DIR, "deta-chat.css"), "text/css; charset=utf-8")
            return
        if path in ("/deta-chat.js", "/copee-chat.js"):
            self.send_file(os.path.join(PUBLIC_DIR, "deta-chat.js"), "application/javascript; charset=utf-8")
            return
        if path in ("/cong-cu/than-so-hoc", "/cong-cu/than-so-hoc/"):
            self.send_file(os.path.join(PUBLIC_DIR, "than-so-hoc.html"))
            return
        if path in ("/dich-vu/thiet-ke-tron-goi", "/dich-vu/thiet-ke-tron-goi/", "/b2b", "/b2b/"):
            self.send_file(os.path.join(PUBLIC_DIR, "b2b.html"))
            return
        if path in (
            "/tai-lieu/chatbot-chot-don",
            "/tai-lieu/chatbot-chot-don/",
            "/khoa-hoc/chatbot-chot-don",
            "/khoa-hoc/chatbot-chot-don/",
        ):
            self.send_file(os.path.join(PUBLIC_DIR, "chatbot-guide.html"))
            return
        if path in (
            "/chua-online",
            "/chua-online/",
            "/cong-cu/chua-online",
            "/cong-cu/chua-online/",
            "/tinh-tam",
            "/tinh-tam/",
        ):
            self.send_file(os.path.join(PUBLIC_DIR, "chua-online.html"))
            return
        if path.startswith("/cong-cu/") or path == "/tai-lieu/tao-ai":
            tools_path = os.path.join(PUBLIC_DIR, "tools.html")
            norm_tool = path.rstrip("/")
            og_map = {
                "/cong-cu/tao-landing-page": (
                    "AI Tự Code Landing Page Bán Hàng 1 File .HTML (Miễn Phí 100%) · Deta AI Lab",
                    "Nhập tên sản phẩm và SĐT/Zalo để AI tự code trọn bộ Landing Page bán hàng 1 file .HTML chuẩn 8 khối chốt đơn. Tải trọn bộ mã nguồn sạch miễn phí 100% không cần đăng nhập.",
                    "🎁 AI Tự Code Landing Page Bán Hàng 1 File .HTML — Miễn Phí 100%",
                    "Tạo & tải trọn bộ file index.html sạch chuẩn 8 khối chuyển đổi cao trong 15 giây · Miễn phí 100% (0đ) không tốn phí hosting tháng.",
                    "https://kiemtien.deta.vn/mau-landing/assets/og-tao-landing-page.png",
                ),
                "/cong-cu/tao-cv-ats": (
                    "AI Thiết Kế CV Chuẩn ATS A4 & Thư Ứng Tuyển (Miễn Phí 100%) · Deta AI Lab",
                    "Dán kinh nghiệm thô để AI viết lại CV chuẩn Harvard XYZ (Tiếng Việt / Tiếng Anh / Song ngữ) kèm Cover Letter. Sửa trực tiếp & xuất PDF A4 sạch miễn phí 100%.",
                    "🎁 AI Thiết Kế CV Chuẩn ATS A4 & Thư Ứng Tuyển — Miễn Phí 100%",
                    "Chuẩn hóa CV Harvard XYZ (Việt / Anh / Song ngữ) trong 12 giây · Sửa trực tiếp từng chữ & lưu PDF A4 sạch không watermark hoàn toàn miễn phí!",
                    "https://kiemtien.deta.vn/anh-chia-se.png",
                ),
                "/cong-cu/lich-30-ngay": (
                    "AI Lập Lịch 30 Ngày Bài Đăng Bán Hàng & Hook TikTok (.CSV Miễn Phí 100%) · Deta AI Lab",
                    "Nhập tên sản phẩm & khách hàng để AI lên lịch 30 ngày nội dung 6 trụ cột không trùng lặp và tải ngay file Excel (.CSV) miễn phí 100%.",
                    "🎁 AI Lập Lịch 30 Ngày Bài Đăng Bán Hàng & Hook TikTok (.CSV) — Miễn Phí 100%",
                    "Xoay vòng 6 trụ cột chốt đơn suốt 30 ngày · Tải file bảng tính Excel (.CSV) chuẩn tiếng Việt hoàn toàn miễn phí (0đ)!",
                    "https://kiemtien.deta.vn/anh-chia-se.png",
                ),
            }
            if norm_tool in og_map and os.path.exists(tools_path):
                t_page, t_desc, og_t, og_d, og_img = og_map[norm_tool]
                with open(tools_path, "r", encoding="utf-8") as tf:
                    html = tf.read()
                og_tags = (
                    f'<title id="page-title">{t_page}</title>\n'
                    f'<meta name="description" content="{t_desc}">\n'
                    f'<meta property="og:title" content="{og_t}">\n'
                    f'<meta property="og:description" content="{og_d}">\n'
                    f'<meta property="og:image" content="{og_img}">\n'
                    '<meta property="og:image:width" content="1200">\n'
                    '<meta property="og:image:height" content="630">\n'
                    '<meta name="twitter:card" content="summary_large_image">'
                )
                html = html.replace('<title id="page-title">Công cụ AI · kiemtien.deta.vn</title>', og_tags, 1)
                raw = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self._send_security_headers()
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                if not getattr(self, "_is_head", False):
                    self.wfile.write(raw)
                return
            self.send_file(tools_path)
            return
        if path == "/admin":
            self.send_file(os.path.join(PUBLIC_DIR, "admin.html"))
            return
        if path == "/sitemap.xml":
            self.send_file(os.path.join(PUBLIC_DIR, "sitemap.xml"), "application/xml; charset=utf-8")
            return
        if path == "/robots.txt":
            self.send_file(os.path.join(PUBLIC_DIR, "robots.txt"), "text/plain; charset=utf-8")
            return
        if path in ("/anh-chia-se.png", "/anh-chia-se.jpg"):
            self.send_file(os.path.join(PUBLIC_DIR, "anh-chia-se.png"), "image/png")
            return
        if path.startswith("/huong-dan/"):
            slug = os.path.basename(path)
            if not re.match(r"^[a-zA-Z0-9._-]+\.html$", slug):
                self.send_json({"loi": "Không tìm thấy trang"}, 404)
                return
            self.send_file(os.path.join(PUBLIC_DIR, "huong-dan", slug))
            return
        if path.startswith("/mau-landing/"):
            rel = os.path.normpath(path.lstrip("/"))
            mau_root = os.path.realpath(os.path.join(PUBLIC_DIR, "mau-landing"))
            full_p = os.path.realpath(os.path.join(PUBLIC_DIR, rel))
            if not (full_p == mau_root or full_p.startswith(mau_root + os.sep)):
                self.send_json({"loi": "Đường dẫn không hợp lệ"}, 403)
                return
            if os.path.isdir(full_p):
                full_p = os.path.join(full_p, "index.html")
            ext = os.path.splitext(full_p)[1].lower()
            ctype = {
                ".html": "text/html; charset=utf-8",
                ".webp": "image/webp",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".svg": "image/svg+xml",
            }.get(ext)
            if not ctype:
                self.send_json({"loi": "Định dạng không được phép"}, 403)
                return
            self.send_file(full_p, ctype)
            return

        # ---- API GET ----
        if path == "/api/dang-xem":
            ma = (qs.get("ma", [""])[0] or secrets.token_hex(6))[:32]
            trang_raw = (qs.get("trang", [""])[0] or "/").strip()[:120]
            if not trang_raw.startswith("/"):
                trang_raw = "/" + trang_raw
            trang_clean = trang_raw.rstrip("/") or "/"
            ref_client = (qs.get("ref", [""])[0] or self.headers.get("Referer") or "").strip()[:240]
            nguon_q = (qs.get("nguon", [""])[0] or "").strip()[:60]
            is_pv = (qs.get("pv", ["1"])[0] or "1").strip() == "1"

            cf_ip = (self.headers.get("CF-Connecting-IP") or "").strip()
            raw_ip = (
                cf_ip
                or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                or (self.client_address[0] if self.client_address else "")
            )
            ua_str = (self.headers.get("User-Agent") or "").strip()
            is_bot_or_local = (
                (not cf_ip and raw_ip in ("127.0.0.1", "::1", "localhost"))
                or trang_clean.startswith("/admin")
                or bool(
                    re.search(
                        r"HeadlessChrome|Googlebot|bingbot|AhrefsBot|SemrushBot|Bytespider|PetalBot|YandexBot|python-requests|python-urllib|curl/|wget/|UptimeRobot",
                        ua_str,
                        re.I,
                    )
                )
            )

            now_dt = now_vn()
            today = now_dt.strftime("%Y-%m-%d")
            gio_str = now_dt.strftime("%H")
            now_iso = now_dt.isoformat(timespec="seconds")
            ts = time.time()

            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                if not is_bot_or_local:
                    kenh, chi_tiet, thiet_bi, is_internal_nav = classify_traffic_source(nguon_q, ref_client, ua_str)
                    c.execute("SELECT kenh, chi_tiet_nguon, trang_dau, so_trang FROM viewers WHERE ma = ?", (ma,))
                    existing = c.fetchone()
                    if not existing:
                        c.execute(
                            """INSERT INTO viewers
                            (ma, ngay, last_seen, first_ngay, first_seen, kenh, chi_tiet_nguon, trang_dau, trang_cuoi, thiet_bi, so_trang)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                            (ma, today, ts, today, ts, kenh, chi_tiet, trang_clean, trang_clean, thiet_bi),
                        )
                        eff_kenh, eff_chi_tiet = kenh, chi_tiet
                    else:
                        old_kenh, old_ct, old_td, old_sp = existing[0] or "", existing[1] or "", existing[2] or "", int(existing[3] or 1)
                        if not old_kenh or (old_kenh in ("Trực tiếp / Gõ từ Ảnh", "Trực tiếp / Gõ link") and not is_internal_nav):
                            eff_kenh, eff_chi_tiet = kenh, chi_tiet
                        else:
                            eff_kenh = old_kenh
                            eff_chi_tiet = chi_tiet if not is_internal_nav else (old_ct or chi_tiet)
                        new_td = old_td or trang_clean
                        new_sp = old_sp + (1 if is_pv else 0)
                        c.execute(
                            """UPDATE viewers
                            SET ngay = ?, last_seen = ?, kenh = ?, chi_tiet_nguon = ?, trang_dau = ?, trang_cuoi = ?, thiet_bi = ?, so_trang = ?
                            WHERE ma = ?""",
                            (today, ts, eff_kenh, eff_chi_tiet, new_td, trang_clean, thiet_bi, new_sp, ma),
                        )

                    if is_pv:
                        c.execute(
                            """INSERT INTO pageviews
                            (viewer_ma, ngay, gio, trang, kenh, chi_tiet_nguon, referer, thiet_bi, luc)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (ma, today, gio_str, trang_clean, eff_kenh, eff_chi_tiet, ref_client[:200], thiet_bi, now_iso),
                        )

                c.execute("SELECT COUNT(*) FROM viewers WHERE last_seen > ?", (ts - 90,))
                dang_xem = max(1, c.fetchone()[0])
                c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (today,))
                hom_nay = max(1, c.fetchone()[0])
                c.execute("SELECT COUNT(*) FROM viewers")
                tong = max(hom_nay, c.fetchone()[0])
                conn.commit()
                conn.close()
            self.send_json({"dang_xem": dang_xem, "hom_nay": hom_nay, "tong": tong})
            return

        if path == "/api/so-tien":
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    "SELECT COALESCE(SUM(so_tien), 0), COUNT(*) FROM orders WHERE trang_thai = 'xong' AND loai = 'ban-hang'"
                )
                ban_hang, so_don_ban = c.fetchone()
                c.execute(
                    "SELECT COALESCE(SUM(so_tien), 0), COUNT(*) FROM orders WHERE trang_thai = 'xong' AND loai = 'ung-ho'"
                )
                ung_ho, so_luot_dai = c.fetchone()
                conn.close()
            self.send_json(
                {
                    "ban_hang": int(ban_hang),
                    "so_don_ban": int(so_don_ban),
                    "ung_ho": int(ung_ho),
                    "so_luot_dai": int(so_luot_dai),
                    "luc": now_vn().isoformat(timespec="seconds"),
                }
            )
            return

        if path == "/api/ung-ho":
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    "SELECT COALESCE(SUM(so_tien), 0), COUNT(*) FROM orders WHERE trang_thai = 'xong'"
                )
                tong, so_nguoi = c.fetchone()
                c.execute("SELECT COUNT(*) FROM orders")
                so_qr_mo = c.fetchone()[0]
                c.execute(
                    "SELECT ten, mon_ma, mon_ten, bieu, so_luong, loi_nhan, tra_loi, so_tien, luc "
                    "FROM orders WHERE trang_thai = 'xong' ORDER BY rowid DESC LIMIT 30"
                )
                gan_day = []
                for r in c.fetchall():
                    gan_day.append(
                        {
                            "ten": r["ten"] or "Một bạn ẩn danh",
                            "mon": r["mon_ten"],
                            "bieu": r["bieu"] or "🎁",
                            "so_luong": r["so_luong"],
                            "tu_chon": r["mon_ma"] == "tu-chon",
                            "loi_nhan": r["loi_nhan"] or "",
                            "tra_loi": r["tra_loi"] or "Cảm ơn bạn đã tiếp sức!",
                            "so_tien": r["so_tien"],
                            "luc": r["luc"],
                        }
                    )
                conn.close()
            self.send_json(
                {
                    "tong": int(tong),
                    "so_nguoi": int(so_nguoi),
                    "so_qr_mo": int(so_qr_mo),
                    "gan_day": gan_day,
                    "thuc_don": [{k: v for k, v in m.items() if k != "loai"} for m in THUC_DON],
                }
            )
            return

        if path.startswith("/api/don/"):
            ma = path.split("/api/don/", 1)[1].strip().upper()
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT ma, trang_thai, ve_token FROM orders WHERE ma = ?", (ma,))
                row = c.fetchone()
                conn.close()
            if not row:
                self.send_json({"loi": "Không thấy đơn"}, 404)
                return
            resp = {"ma": row["ma"], "trang_thai": row["trang_thai"]}
            if row["trang_thai"] == "xong" and row["ve_token"]:
                resp["ve"] = {"token": row["ve_token"]}
            self.send_json(resp)
            return

        if path == "/api/goi-y":
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM suggestions")
                tong = c.fetchone()[0] + 3
                conn.close()
            self.send_json({"tong": tong})
            return

        if path == "/api/chia-se":
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM shares WHERE loai IN ('bam', 'xong')")
                bam = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM shares WHERE loai = 'vao'")
                vao = c.fetchone()[0]
                conn.close()
            self.send_json({"nguoi_chia_se": bam, "nguoi_vao_tu_link": vao})
            return

        if path == "/api/modul/thu-tu":
            self.send_json({"du_lieu": False, "thu_tu": []})
            return

        if path == "/api/chat/nhom":
            sau = int(qs.get("sau", ["0"])[0] or 0)
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT id, ten, chu, ai, t FROM group_messages WHERE id > ? ORDER BY id ASC LIMIT 60", (sau,))
                tin = [{"id": r["id"], "ten": r["ten"], "chu": r["chu"], "ai": bool(r["ai"]), "t": r["t"]} for r in c.fetchall()]
                conn.close()
            self.send_json({"tin": tin})
            return

        if path == "/api/chat/toi":
            ve = (qs.get("ve", [""])[0] or "").strip()
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM tickets WHERE token = ?", (ve,))
                r = c.fetchone()
                conn.close()
            if not r:
                self.send_json({"loai": "khong"}, 403)
                return
            self.send_json({"loai": r["loai"], "ten": r["ten"], "con_tin": r["con_tin"], "het_han": r["het_han"]})
            return

        if path == "/api/chat/rieng":
            ve = (qs.get("ve", [""])[0] or "").strip()
            ve_thu = (qs.get("ve_thu", [""])[0] or "").strip()
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                if ve.startswith("thu_"):
                    c.execute("SELECT * FROM free_chat_trials WHERE token = ?", (ve,))
                    tk = c.fetchone()
                    if not tk:
                        conn.close()
                        self.send_json({"loi": "Phiên dùng thử không hợp lệ"}, 403)
                        return
                    c.execute("SELECT chu, ai, t FROM private_messages WHERE token = ? ORDER BY id ASC", (ve,))
                    tin = [{"chu": r["chu"], "ai": bool(r["ai"]), "t": r["t"]} for r in c.fetchall()]
                    conn.close()
                    self.send_json({"con_tin": int(tk["con_tin"]), "dung_thu": True, "tin": tin})
                    return

                c.execute("SELECT * FROM tickets WHERE token = ? AND loai = 'rieng'", (ve,))
                tk = c.fetchone()
                if not tk:
                    conn.close()
                    self.send_json({"loi": "Vé không hợp lệ"}, 403)
                    return
                if ve_thu.startswith("thu_"):
                    c.execute("UPDATE private_messages SET token = ? WHERE token = ?", (ve, ve_thu))
                    conn.commit()
                c.execute("SELECT chu, ai, t FROM private_messages WHERE token = ? ORDER BY id ASC", (ve,))
                tin = [{"chu": r["chu"], "ai": bool(r["ai"]), "t": r["t"]} for r in c.fetchall()]
                conn.close()
            self.send_json({"con_tin": tk["con_tin"], "dung_thu": False, "tin": tin})
            return

        if path == "/api/chat/ve":
            ma = (qs.get("ma", [""])[0] or "").strip().upper()
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT token, loai FROM tickets WHERE ma_don = ? OR UPPER(token) = ?", (ma, ma))
                r = c.fetchone()
                conn.close()
            if not r:
                self.send_json({"loi": "Không tìm thấy vé đã kích hoạt cho mã này."})
                return
            self.send_json({"ve": r["token"], "loai": r["loai"]})
            return

        if path == "/api/webhook/bank":
            self.send_json(
                {
                    "success": True,
                    "error": 0,
                    "ok": True,
                    "ready": True,
                    "service": "Deta AI Lab Webhook (SePay & Casso V1/V2 Ready)",
                }
            )
            return

        if path == "/api/admin/state":
            if is_auth_locked(client_ip):
                self.send_json({"loi": "Tạm khóa 15 phút do nhập sai khóa quản trị quá 5 lần."}, 429)
                return
            cfg = agent_worker.load_config()
            key = (qs.get("key", [""])[0] or "").strip()
            if not is_valid_admin_key(key, cfg):
                record_auth_failure(client_ip)
                self.send_json({"loi": "Sai mã quản trị (Admin Key)"}, 403)
                return
            clear_auth_failures(client_ip)
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM orders ORDER BY rowid DESC LIMIT 50")
                orders = [dict(r) for r in c.fetchall()]
                c.execute("SELECT * FROM webhook_logs ORDER BY id DESC LIMIT 20")
                wh_logs = [dict(r) for r in c.fetchall()]
                c.execute("SELECT * FROM b2b_leads ORDER BY id DESC LIMIT 50")
                b2b_leads = [dict(r) for r in c.fetchall()]
                traffic_data = build_traffic_analytics(conn)
                conn.close()
            site_url = (cfg.get("site_url") or "https://kiemtien.deta.vn").rstrip("/")
            wh_sec = (cfg.get("webhook_secret") or "").strip()
            safe_cfg = {k: v for k, v in cfg.items() if k not in ("admin_key", "webhook_secret")}
            try:
                import numerology_comment_bot as ncb

                tracked_info = ncb.get_tracked_posts_for_admin()
            except Exception:
                tracked_info = {"interval_hours": 4, "last_scan_at": "", "summary": {}, "posts": []}
            self.send_json(
                {
                    "config": safe_cfg,
                    "orders": orders,
                    "webhook_logs": wh_logs,
                    "b2b_leads": b2b_leads,
                    "tracked_posts": tracked_info,
                    "traffic": traffic_data,
                    "webhook_info": {
                        "url_with_secret": f"{site_url}/api/webhook/bank?secret={wh_sec}" if wh_sec else f"{site_url}/api/webhook/bank",
                        "url_clean": f"{site_url}/api/webhook/bank",
                        "secret": wh_sec,
                    },
                }
            )
            return

        if path == "/api/banner":
            tuan = current_week_key()
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    "SELECT id, domain, url, tieu_de, mo_ta, bieu, tong_tien, clicks, tuan, cap_nhat, COALESCE(anh_banner, '') AS anh_banner "
                    "FROM banners WHERE tuan = ? ORDER BY tong_tien DESC, id ASC LIMIT 10",
                    (tuan,),
                )
                rows = c.fetchall()
                c.execute("SELECT COUNT(*) FROM events WHERE loai = 'click-banner-mac-dinh'")
                md_clicks = int(c.fetchone()[0] or 0)
                conn.close()
            ds = []
            for idx, r in enumerate(rows):
                ds.append(
                    {
                        "id": r["id"],
                        "hang": idx + 1,
                        "domain": r["domain"],
                        "url": r["url"],
                        "go": f"/go/banner/{r['id']}",
                        "tieu_de": r["tieu_de"],
                        "mo_ta": r["mo_ta"],
                        "bieu": r["bieu"] or "🚀",
                        "anh_banner": r["anh_banner"] or "",
                        "tong_tien": int(r["tong_tien"]),
                        "clicks": int(r["clicks"]),
                    }
                )
            top = ds[0] if ds else None
            gia_len_dinh = (int(top["tong_tien"]) + 5000) if top else 10000
            mac_dinh = None
            if not top:
                mac_dinh = {
                    "id": 0,
                    "hang": 1,
                    "mac_dinh": True,
                    "nhan": "🏥 ĐỒNG HÀNH",
                    "domain": "giaytieuduong.com",
                    "url": "https://giaytieuduong.com/",
                    "go": "https://giaytieuduong.com/",
                    "tieu_de": "Giày Tiểu Đường TIDU — Chuẩn Y Khoa IWGDF",
                    "mo_ta": "Mũi siêu rộng · Không đường may · Đế chống trượt bảo vệ bàn chân · Freeship & Đổi size miễn phí",
                    "bieu": "👟",
                    "anh": "/mau-landing/assets/tidu-shoe.webp?v=2",
                    "anh_banner": "/mau-landing/assets/banner-giaytieuduong.webp?v=2",
                    "anh_banner_png": "/mau-landing/assets/banner-giaytieuduong.png?v=2",
                    "gia_sp": "779.000đ",
                    "tong_tien": 0,
                    "clicks": md_clicks,
                }
            self.send_json(
                {
                    "tuan": tuan,
                    "top": top,
                    "mac_dinh": mac_dinh,
                    "danh_sach": ds,
                    "gia_toi_thieu": 10000,
                    "gia_len_dinh": gia_len_dinh,
                }
            )
            return

        if path.startswith("/go/banner/"):
            bid_str = path.split("/go/banner/", 1)[1].strip()
            if bid_str == "mac-dinh":
                try:
                    with DB_LOCK:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO events (loai, nguon, luc) VALUES (?, ?, ?)",
                            ("click-banner-mac-dinh", "giaytieuduong.com", now_vn().isoformat(timespec="seconds")),
                        )
                        conn.commit()
                        conn.close()
                except Exception:
                    pass
                self.send_response(302)
                self.send_header("Location", "https://giaytieuduong.com/")
                self.send_header("Cache-Control", "no-store")
                self._send_security_headers()
                self.end_headers()
                return
            if not bid_str.isdigit():
                self.send_json({"loi": "Banner không hợp lệ"}, 404)
                return
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT url FROM banners WHERE id = ?", (int(bid_str),))
                row = c.fetchone()
                if row:
                    c.execute("UPDATE banners SET clicks = clicks + 1 WHERE id = ?", (int(bid_str),))
                    conn.commit()
                conn.close()
            if not row or not str(row["url"] or "").startswith(("http://", "https://")):
                self.send_json({"loi": "Không tìm thấy banner"}, 404)
                return
            self.send_response(302)
            self.send_header("Location", row["url"])
            self.send_header("Cache-Control", "no-store")
            self._send_security_headers()
            self.end_headers()
            return

        if path == "/api/landing/tai":
            ma = (qs.get("ma", [""])[0] or "").strip().upper()
            k = (qs.get("k", [""])[0] or "").strip()
            pid = (qs.get("pid", [""])[0] or "").strip()
            xem = (qs.get("xem", ["0"])[0] or "0").strip() == "1"
            dl = (qs.get("dl", ["0"])[0] or "0").strip() == "1"

            html_clean = ""
            ten_sp = "landing-page"
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                allowed_pid = ""
                if pid:
                    allowed_pid = pid
                elif ma and k:
                    c.execute(
                        "SELECT du_lieu_kem FROM orders WHERE ma = ? AND k = ?",
                        (ma, k),
                    )
                    ord_row = c.fetchone()
                    if ord_row:
                        allowed_pid = (ord_row["du_lieu_kem"] or "").strip()

                if allowed_pid:
                    c.execute("SELECT ten_sp, html_clean FROM landing_previews WHERE id = ?", (allowed_pid,))
                    lp_row = c.fetchone()
                    if lp_row:
                        html_clean = lp_row["html_clean"]
                        ten_sp = lp_row["ten_sp"] or "landing-page"
                conn.close()

            if not html_clean:
                self.send_json({"ok": False, "loi": "Không tìm thấy bản Landing Page này."}, 404)
                return

            slug = re.sub(r"[^a-z0-9]+", "-", ten_sp.lower()).strip("-") or "landing-page"
            if dl or xem:
                raw_bytes = html_clean.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self._send_security_headers()
                self.send_header("Content-Security-Policy", "sandbox allow-scripts allow-popups allow-modals; default-src 'self' https: data: 'unsafe-inline'")
                if dl:
                    self.send_header("Content-Disposition", f'attachment; filename="index-{slug[:24]}.html"')
                self.send_header("Content-Length", str(len(raw_bytes)))
                self.end_headers()
                if not getattr(self, "_is_head", False):
                    self.wfile.write(raw_bytes)
                return

            self.send_json({"ok": True, "filename": f"index-{slug[:24]}.html", "html": html_clean})
            return

        if path == "/api/tai-pham-vat":
            ma = (qs.get("ma", [""])[0] or "").strip().upper()
            k = (qs.get("k", [""])[0] or "").strip()
            pid = (qs.get("pid", [""])[0] or "").strip()
            xem = (qs.get("xem", ["0"])[0] or "0").strip() == "1"
            dl = (qs.get("dl", ["0"])[0] or "0").strip() == "1"
            csv_flag = (qs.get("csv", ["0"])[0] or "0").strip() == "1"

            row_deliv = None
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                allowed_pid = ""
                if pid:
                    allowed_pid = pid
                elif ma and k:
                    c.execute("SELECT du_lieu_kem FROM orders WHERE ma = ? AND k = ?", (ma, k))
                    ord_row = c.fetchone()
                    if ord_row:
                        allowed_pid = (ord_row["du_lieu_kem"] or "").strip()

                if allowed_pid:
                    c.execute("SELECT loai, slug, html_clean, csv_clean FROM deliverables WHERE id = ?", (allowed_pid,))
                    row_deliv = c.fetchone()
                conn.close()

            if not row_deliv:
                self.send_json({"ok": False, "loi": "Không tìm thấy tài liệu hoặc phiên đã hết hạn."}, 404)
                return

            loai = row_deliv["loai"] or "tai-lieu"
            slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", (row_deliv["slug"] or "deta"))[:28] or "deta"
            html_clean = row_deliv["html_clean"] or ""
            csv_clean = row_deliv["csv_clean"] or ""

            if csv_flag and csv_clean:
                raw_b = csv_clean.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self._send_security_headers()
                self.send_header("Content-Disposition", f'attachment; filename="lich-30-ngay-{slug}.csv"')
                self.send_header("Content-Length", str(len(raw_b)))
                self.end_headers()
                if not getattr(self, "_is_head", False):
                    self.wfile.write(raw_b)
                return

            if xem or dl:
                raw_b = html_clean.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self._send_security_headers()
                self.send_header("Content-Security-Policy", "sandbox allow-scripts allow-popups allow-modals; default-src 'self' https: data: 'unsafe-inline'")
                if dl:
                    self.send_header("Content-Disposition", f'attachment; filename="{loai}-{slug}.html"')
                self.send_header("Content-Length", str(len(raw_b)))
                self.end_headers()
                if not getattr(self, "_is_head", False):
                    self.wfile.write(raw_b)
                return

            self.send_json(
                {
                    "ok": True,
                    "loai": loai,
                    "slug": slug,
                    "html": html_clean,
                    "has_csv": bool(csv_clean),
                }
            )
            return

        if path == "/api/tai-lieu/chatbot-full":
            if is_auth_locked(client_ip):
                self.send_json({"ok": False, "loi": "Tạm khóa 15 phút do thử mã sai quá nhiều lần."}, 429)
                return
            raw_ma = (qs.get("ma", [""])[0] or "").strip()
            ma = raw_ma.upper()
            if not ma:
                self.send_json({"ok": False, "loi": "Vui lòng nhập mã đơn hàng đã thanh toán."}, 400)
                return
            cfg = agent_worker.load_config()
            if is_valid_admin_key(raw_ma, cfg):
                clear_auth_failures(client_ip)
                import chatbot_guide_content

                self.send_json(
                    {
                        "ok": True,
                        "ma": "ADMIN-REVIEW",
                        "ten": "Quản trị viên (Bản Duyệt Nội Dung)",
                        "lessons": chatbot_guide_content.UNLOCKED_LESSONS,
                    }
                )
                return
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute(
                    "SELECT ma, mon_ma, trang_thai, ten FROM orders WHERE (UPPER(ma) = ? OR UPPER(ve_token) = ?) AND trang_thai = 'xong'",
                    (ma, ma),
                )
                row = c.fetchone()
                conn.close()
            if not row:
                record_auth_failure(client_ip)
                self.send_json({"ok": False, "loi": "Mã đơn chưa hoàn tất thanh toán hoặc không tồn tại."}, 403)
                return
            import chatbot_guide_content

            self.send_json(
                {
                    "ok": True,
                    "ma": row["ma"],
                    "ten": row["ten"],
                    "lessons": chatbot_guide_content.UNLOCKED_LESSONS,
                }
            )
            return

        if path == "/api/chua/trang-thai":
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                data = temple_engine.get_temple_state(conn)
                conn.close()
            self.send_json(data)
            return

        self.send_json({"loi": "Không tìm thấy đường dẫn"}, 404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path or "/")
        client_ip = get_real_client_ip(self)

        if not check_rate_limit(client_ip, "global_post", 120, 60.0):
            self.send_json({"ok": False, "loi": "Bạn thao tác quá nhanh, vui lòng chờ ít giây rồi thử lại."}, 429)
            return

        if path in ("/api/cong-cu/chay", "/api/chua/gieo-que", "/api/chat/rieng", "/api/chat/nhom"):
            if not check_rate_limit(client_ip, "ai_heavy", 12, 60.0):
                self.send_json({"ok": False, "loi": "Hệ thống AI đang giới hạn tối đa 12 lượt/phút mỗi người để chống quá tải. Bạn chờ 30 giây rồi bấm lại nhé!"}, 429)
                return
        elif path in ("/api/don", "/api/chua/hoa-dang", "/api/goi-y", "/api/b2b/dang-ky", "/api/chat/dung-thu", "/api/chia-se"):
            if not check_rate_limit(client_ip, "db_write", 15, 60.0):
                self.send_json({"ok": False, "loi": "Bạn gửi yêu cầu quá nhanh, vui lòng thử lại sau 1 phút."}, 429)
                return
        elif path in ("/api/chua/hanh-dong", "/api/chua/chap-tay-den", "/api/banner/click"):
            if not check_rate_limit(client_ip, "temple_action", 60, 60.0):
                self.send_json({"ok": False, "loi": "Thao tác quá nhanh"}, 429)
                return

        body = self.read_json_body()

        if path == "/api/chua/hanh-dong":
            vid = re.sub(r"[^a-zA-Z0-9_-]", "", str(body.get("id") or secrets.token_hex(4)))[:24] or secrets.token_hex(4)
            phap_danh = str(body.get("phap_danh") or "Mây Thong Thả")
            ao_mau = str(body.get("ao_mau") or "#D97706")
            try:
                x = float(body.get("x") or 0.0)
                z = float(body.get("z") or 4.0)
                so_mo = max(0, min(50, int(body.get("so_mo") or 0)))
            except (ValueError, TypeError):
                x, z, so_mo = 0.0, 4.0, 0
            hanh_dong = str(body.get("hanh_dong") or "di-dao")
            ma_chao = str(body.get("ma_chao") or "")
            res = temple_engine.update_visitor_presence(vid, phap_danh, ao_mau, x, z, hanh_dong, ma_chao, so_mo)
            self.send_json({"ok": True, **res})
            return

        if path == "/api/chua/hoa-dang":
            phap_danh = html.escape(str(body.get("phap_danh") or "Đạo Hữu An Nhiên").strip()[:28])
            loi_nguyen = html.escape(str(body.get("loi_nguyen") or "").strip()[:140])
            mau_sac = str(body.get("mau_sac") or "#F472B6").strip()[:10]
            if not re.match(r"^#[0-9a-fA-F]{6}$", mau_sac):
                mau_sac = "#F472B6"
            if len(loi_nguyen) < 5:
                self.send_json({"ok": False, "loi": "Bạn hãy viết lời ước nguyện tối thiểu 5 ký tự nhé."}, 400)
                return
            if not temple_engine.is_clean_text(phap_danh + " " + loi_nguyen):
                self.send_json({"ok": False, "loi": "Lời nguyện chứa từ ngữ chưa phù hợp với không gian tĩnh tâm."}, 400)
                return
            now_iso = now_vn().isoformat(timespec="seconds")
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                temple_engine.ensure_temple_tables(conn)
                c = conn.cursor()
                c.execute(
                    """INSERT INTO temple_lanterns
                    (ma_don, phap_danh, loi_nguyen, loai, so_tien, mau_sac, luot_chap_tay, tao_luc)
                    VALUES ('FREE', ?, ?, 'thuong', 0, ?, 1, ?)""",
                    (phap_danh, loi_nguyen, mau_sac, now_iso),
                )
                lid = c.lastrowid
                conn.commit()
                conn.close()
            self.send_json(
                {
                    "ok": True,
                    "lantern": {
                        "id": lid,
                        "phap_danh": phap_danh,
                        "loi_nguyen": loi_nguyen,
                        "loai": "thuong",
                        "so_tien": 0,
                        "mau_sac": mau_sac,
                        "luot_chap_tay": 1,
                        "tao_luc": now_iso,
                    },
                }
            )
            return

        if path == "/api/chua/chap-tay-den":
            try:
                lid = int(body.get("id") or 0)
            except (ValueError, TypeError):
                lid = 0
            if lid <= 0:
                self.send_json({"ok": False}, 400)
                return
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                temple_engine.ensure_temple_tables(conn)
                c = conn.cursor()
                c.execute("UPDATE temple_lanterns SET luot_chap_tay = luot_chap_tay + 1 WHERE id = ?", (lid,))
                c.execute("SELECT luot_chap_tay FROM temple_lanterns WHERE id = ?", (lid,))
                row = c.fetchone()
                conn.commit()
                conn.close()
            self.send_json({"ok": True, "luot_chap_tay": int(row[0]) if row else 1})
            return

        if path == "/api/chua/gieo-que":
            phap_danh = html.escape(str(body.get("phap_danh") or "Đạo hữu").strip()[:36])
            chu_de = str(body.get("chu_de") or "binh-an").strip()[:24]
            tam_su = html.escape(str(body.get("tam_su") or "").strip()[:300])
            res = temple_engine.draw_peace_lot(phap_danh, chu_de, tam_su)
            self.send_json(res)
            return

        if path == "/api/banner/click":
            try:
                bid = int(body.get("id") or 0)
            except (ValueError, TypeError):
                bid = 0
            try:
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    if bid > 0:
                        c.execute("UPDATE banners SET clicks = clicks + 1 WHERE id = ?", (bid,))
                    else:
                        c.execute(
                            "INSERT INTO events (loai, nguon, luc) VALUES (?, ?, ?)",
                            ("click-banner-mac-dinh", "giaytieuduong.com", now_vn().isoformat(timespec="seconds")),
                        )
                    conn.commit()
                    conn.close()
            except Exception:
                pass
            self.send_json({"ok": True})
            return

        if path == "/api/don":
            mon_ma = str(body.get("mon") or "banh-tieu").strip()[:40]
            ten = html.escape(str(body.get("ten") or "").strip()[:30]) or "Một bạn ẩn danh"
            loi_nhan = html.escape(str(body.get("loi_nhan") or "").strip()[:140])
            nguon = html.escape(str(body.get("nguon") or "kiemtien").strip()[:40])
            du_lieu_kem = ""

            loai = "ung-ho"
            mon_ten = "cái bánh tiêu"
            bieu = "🥯"
            so_tien = 5000

            menu_map = {m["ma"]: m for m in THUC_DON}
            if mon_ma in menu_map:
                m = menu_map[mon_ma]
                mon_ten = m["ten"]
                bieu = m["bieu"]
                so_tien = m["gia"]
                loai = "ung-ho"
            elif mon_ma == "tu-chon":
                mon_ten = html.escape(str(body.get("ten_mon") or "món tự chọn").strip()[:40])
                bieu = "🎁"
                try:
                    so_tien = max(5000, min(50000000, int(body.get("so_tien") or 10000)))
                except (ValueError, TypeError):
                    so_tien = 10000
                loai = "ung-ho"
            elif mon_ma == "banner-dinh":
                b_url = str(body.get("url") or "").strip()[:300]
                b_title = html.escape(str(body.get("tieu_de") or "").strip()[:45])
                b_desc = html.escape(str(body.get("mo_ta") or "").strip()[:85])
                b_icon = html.escape(str(body.get("bieu") or "🚀").strip()[:4] or "🚀")
                ok_safe, err_msg, clean_domain = check_banner_safety(b_url, b_title, b_desc)
                if not ok_safe:
                    self.send_json({"ok": False, "loi": err_msg}, 400)
                    return
                try:
                    so_tien = max(10000, min(50000000, int(body.get("so_tien") or 10000)))
                except (ValueError, TypeError):
                    so_tien = 10000
                mon_ten = f"Banner Đỉnh ({clean_domain})"
                bieu = "👑"
                loai = "ban-hang"
                if ten == "Một bạn ẩn danh":
                    ten = b_title[:30]
                du_lieu_kem = json.dumps(
                    {
                        "url": b_url,
                        "domain": clean_domain,
                        "tieu_de": b_title,
                        "mo_ta": b_desc,
                        "bieu": b_icon,
                    },
                    ensure_ascii=False,
                )
            elif mon_ma in SAN_PHAM_BAN:
                sp = SAN_PHAM_BAN[mon_ma]
                mon_ten = sp["ten"]
                bieu = sp["bieu"]
                so_tien = sp["gia"]
                loai = "ban-hang"
                du_lieu_kem = html.escape(str(body.get("du_lieu_kem") or "").strip()[:500])
            else:
                self.send_json({"loi": "Món chọn không hợp lệ"}, 400)
                return

            ma = "DETA" + secrets.token_hex(3).upper()
            k = secrets.token_hex(6)
            qr_url = make_vietqr_url(so_tien, ma)
            now_iso = now_vn().isoformat(timespec="seconds")

            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    """INSERT INTO orders
                    (ma, k, loai, mon_ma, mon_ten, bieu, so_luong, so_tien, ten, loi_nhan, tra_loi, trang_thai, ve_token, nguon, luc, du_lieu_kem)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, '', 'cho', '', ?, ?, ?)""",
                    (ma, k, loai, mon_ma, mon_ten, bieu, so_tien, ten, loi_nhan, nguon, now_iso, du_lieu_kem),
                )
                conn.commit()
                conn.close()

            self.send_json(
                {
                    "ok": True,
                    "ma": ma,
                    "k": k,
                    "mon": mon_ten,
                    "so_luong": 1,
                    "so_tien": so_tien,
                    "noi_dung": ma,
                    "qr": qr_url,
                }
            )
            return

        if path == "/api/goi-y":
            noi_dung = html.escape(str(body.get("noi_dung") or "").strip()[:600])
            ten = html.escape(str(body.get("ten") or "").strip()[:40]) or "Một bạn ẩn danh"
            if len(noi_dung) < 10:
                self.send_json({"ok": False, "loi": "Bạn viết dài hơn 10 ký tự nhé."})
                return
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    "INSERT INTO suggestions (ten, noi_dung, da_tra_loi, luc) VALUES (?, ?, 0, ?)",
                    (ten, noi_dung, now_vn().isoformat(timespec="seconds")),
                )
                conn.commit()
                conn.close()
            self.send_json({"ok": True})
            return

        if path == "/api/chia-se":
            loai = html.escape(str(body.get("loai") or "bam")[:16])
            kenh = html.escape(str(body.get("kenh") or "web")[:24])
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO shares (loai, kenh, luc) VALUES (?, ?, ?)", (loai, kenh, now_vn().isoformat(timespec="seconds")))
                conn.commit()
                conn.close()
            self.send_json({"ok": True})
            return

        if path in ("/api/su-kien", "/api/modul"):
            self.send_json({"ok": True})
            return

        if path == "/api/chat/nhom":
            ve = str(body.get("ve") or "").strip()[:40]
            chu = html.escape(str(body.get("chu") or "").strip()[:500])
            if not chu:
                self.send_json({"ok": False, "loi": "Tin nhắn trống"})
                return
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM tickets WHERE token = ? AND loai = 'nhom'", (ve,))
                tk = c.fetchone()
                if not tk:
                    conn.close()
                    self.send_json({"ok": False, "loi": "Vé không hợp lệ"}, 403)
                    return
                now_iso = now_vn().isoformat(timespec="seconds")
                c.execute("INSERT INTO group_messages (ten, chu, ai, t) VALUES (?, ?, 0, ?)", (tk["ten"], chu, now_iso))
                conn.commit()
                conn.close()
            if re.search(r"@ai\b", chu, re.I):
                ans = reply_chat_ai(chu, is_private=False)
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO group_messages (ten, chu, ai, t) VALUES ('🤖 AI', ?, 1, ?)",
                        (ans, now_vn().isoformat(timespec="seconds")),
                    )
                    conn.commit()
                    conn.close()
            self.send_json({"ok": True})
            return

        if path == "/api/chat/dung-thu":
            ve_thu = str(body.get("ve_thu") or "").strip()[:40]
            raw_ip = client_ip
            ip_hash = hashlib.sha256((raw_ip + "|deta-free-chat-2026").encode("utf-8")).hexdigest()[:24]
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                tk = None
                if ve_thu.startswith("thu_"):
                    c.execute("SELECT * FROM free_chat_trials WHERE token = ?", (ve_thu,))
                    tk = c.fetchone()
                if not tk:
                    c.execute(
                        "SELECT * FROM free_chat_trials WHERE ip_hash = ? ORDER BY tao_luc DESC LIMIT 1",
                        (ip_hash,),
                    )
                    tk = c.fetchone()
                if not tk:
                    ve_thu = "thu_" + secrets.token_hex(10)
                    now_iso = now_vn().isoformat(timespec="seconds")
                    c.execute(
                        "INSERT INTO free_chat_trials (token, ip_hash, con_tin, tao_luc) VALUES (?, ?, 20, ?)",
                        (ve_thu, ip_hash, now_iso),
                    )
                    conn.commit()
                    con_tin = 20
                else:
                    ve_thu = tk["token"]
                    con_tin = int(tk["con_tin"])
                    if con_tin <= 2:
                        con_tin = 15
                        c.execute("UPDATE free_chat_trials SET con_tin = ? WHERE token = ?", (con_tin, ve_thu))
                        conn.commit()
                c.execute("SELECT chu, ai, t FROM private_messages WHERE token = ? ORDER BY id ASC", (ve_thu,))
                tin = [{"chu": r["chu"], "ai": bool(r["ai"]), "t": r["t"]} for r in c.fetchall()]
                conn.close()
            self.send_json({"ve_thu": ve_thu, "con_tin": con_tin, "dung_thu": True, "tin": tin})
            return

        if path == "/api/chat/rieng":
            ve = str(body.get("ve") or "").strip()[:40]
            chu = str(body.get("chu") or "").strip()[:1500]
            role_mode = str(body.get("role_mode") or "deta").strip()[:30]
            custom_shop = str(body.get("custom_shop") or "").strip()[:400]
            if not chu:
                self.send_json({"loi": "Tin nhắn trống"})
                return
            is_trial = ve.startswith("thu_")
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                if is_trial:
                    c.execute("SELECT * FROM free_chat_trials WHERE token = ?", (ve,))
                    tk = c.fetchone()
                    if not tk or int(tk["con_tin"]) <= 0:
                        conn.close()
                        self.send_json(
                            {
                                "loi": "Bạn đã dùng hết lượt hỏi thử miễn phí. Mở gói VIP bên dưới để trò chuyện tiếp nhé!",
                                "het_thu": True,
                            },
                            403,
                        )
                        return
                    con_tin = int(tk["con_tin"]) - 1
                    now_iso = now_vn().isoformat(timespec="seconds")
                    c.execute("UPDATE free_chat_trials SET con_tin = ? WHERE token = ?", (con_tin, ve))
                    c.execute("INSERT INTO private_messages (token, chu, ai, t) VALUES (?, ?, 0, ?)", (ve, chu, now_iso))
                    c.execute("INSERT INTO events (loai, nguon, luc) VALUES ('chat-dung-thu', ?, ?)", (role_mode or "web", now_iso))
                    conn.commit()
                    conn.close()
                else:
                    c.execute("SELECT * FROM tickets WHERE token = ? AND loai = 'rieng'", (ve,))
                    tk = c.fetchone()
                    if not tk or tk["con_tin"] <= 0:
                        conn.close()
                        self.send_json({"loi": "Vé đã hết lượt tin nhắn"}, 403)
                        return
                    con_tin = int(tk["con_tin"]) - 1
                    now_iso = now_vn().isoformat(timespec="seconds")
                    c.execute("UPDATE tickets SET con_tin = ? WHERE token = ?", (con_tin, ve))
                    c.execute("INSERT INTO private_messages (token, chu, ai, t) VALUES (?, ?, 0, ?)", (ve, chu, now_iso))
                    conn.commit()
                    conn.close()
            ans = reply_chat_ai(chu, is_private=True, role_mode=role_mode, custom_shop=custom_shop)
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO private_messages (token, chu, ai, t) VALUES (?, ?, 1, ?)", (ve, ans, now_vn().isoformat(timespec="seconds")))
                conn.commit()
                conn.close()
            self.send_json({"tra": ans, "con_tin": con_tin, "dung_thu": is_trial})
            return

        if path == "/api/cong-cu/chay":
            cf_ip_c = (self.headers.get("CF-Connecting-IP") or "").strip()
            cli_ip_c = self.client_address[0] if self.client_address else ""
            if not cf_ip_c and cli_ip_c in ("127.0.0.1", "::1", "localhost"):
                body["_skip_event_log"] = True
            res = run_tool_execution(body)
            self.send_json(res)
            return

        if path == "/api/webhook/bank":
            if is_auth_locked(client_ip):
                self.send_json({"success": False, "error": 1, "ok": False, "loi": "Tạm khóa 15 phút do sai khóa bảo mật Webhook quá nhiều lần."}, 429)
                return
            cfg = agent_worker.load_config()
            qs = urllib.parse.parse_qs(parsed.query)
            raw_body = getattr(self, "_last_raw_body", "") or ""
            is_auth, auth_mode = verify_webhook_auth(self.headers, qs, raw_body, body, cfg)
            if not is_auth:
                record_auth_failure(client_ip)
                self.send_json({"success": False, "error": 1, "ok": False, "loi": "Sai khóa bảo mật Webhook"}, 403)
                return
            clear_auth_failures(client_ip)

            provider, txs = extract_bank_transactions(body)
            provider_safe = html.escape(str(provider or "Webhook")[:32])
            now_iso = now_vn().isoformat(timespec="seconds")

            if not txs:
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "INSERT INTO webhook_logs (nguon, tx_ref, so_tien, noi_dung, ket_qua, luc) VALUES (?, ?, 0, ?, ?, ?)",
                        (f"{provider_safe} ({auth_mode})", "ping", "Kiểm tra kết nối Webhook (Test Ping)", "ket-noi-ok", now_iso),
                    )
                    conn.commit()
                    conn.close()
                self.send_json({"success": True, "error": 0, "ok": True, "ping": True, "approved": []})
                return

            approved = []
            for tx in txs:
                amt = int(tx.get("amount") or 0)
                direction = tx.get("direction") or "in"
                content = (tx.get("content") or "").strip()
                content_safe = html.escape(content[:180])
                tx_ref = html.escape((tx.get("tx_ref") or "").strip()[:80])

                if direction != "in" or amt <= 0:
                    with DB_LOCK:
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute(
                            "INSERT INTO webhook_logs (nguon, tx_ref, so_tien, noi_dung, ket_qua, luc) VALUES (?, ?, ?, ?, ?, ?)",
                            (provider_safe, tx_ref, amt, content_safe, "bo-qua-tien-ra-hoac-0d", now_iso),
                        )
                        conn.commit()
                        conn.close()
                    continue

                # Chống cộng trùng nếu SePay/Casso retry cùng 1 mã giao dịch ngân hàng
                if tx_ref:
                    with DB_LOCK:
                        conn = sqlite3.connect(DB_PATH)
                        dup = conn.execute(
                            "SELECT COUNT(*) FROM webhook_logs WHERE tx_ref = ? AND ket_qua LIKE 'da-duyet:%'",
                            (tx_ref,),
                        ).fetchone()[0]
                        conn.close()
                    if dup > 0:
                        continue

                # Tìm mã đơn DETAxxxxxx (kể cả khi ngân hàng chèn khoảng trắng/dấu gạch giữa chữ DETA và 6 ký tự hex)
                upper_raw = content.upper()
                upper_compact = re.sub(r"[^A-Z0-9]", "", upper_raw)
                codes = list(dict.fromkeys(re.findall(r"DETA[0-9A-F]{6}", upper_raw) + re.findall(r"DETA[0-9A-F]{6}", upper_compact)))

                matched_here = []
                for code in codes:
                    with DB_LOCK:
                        conn = sqlite3.connect(DB_PATH)
                        row_ord = conn.execute("SELECT so_tien FROM orders WHERE ma = ?", (code,)).fetchone()
                        conn.close()
                    if row_ord and amt >= int(row_ord[0]):
                        r = complete_order(code, actual_amount=amt)
                        if r.get("ok"):
                            matched_here.append(code)
                            approved.append(code)

                # Nếu khách chuyển khoản trực tiếp không qua đơn tạo sẵn nhưng ghi rõ từ khóa dự án (KIEMTIEN / BANH TIEU / DETA AI)
                if not matched_here and re.search(r"(KIEMTIEN|KIEM\s*TIEN|BANH\s*TIEU|DETA\s*AI)", upper_raw):
                    auto_ma = "DETA" + secrets.token_hex(3).upper()
                    with DB_LOCK:
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute(
                            """INSERT INTO orders
                            (ma, k, loai, mon_ma, mon_ten, bieu, so_luong, so_tien, ten, loi_nhan, tra_loi, trang_thai, ve_token, nguon, luc)
                            VALUES (?, ?, 'ung-ho', 'tu-chon', 'ủng hộ trực tiếp qua QR', '🥯', 1, ?, 'Một bạn chuyển khoản', ?, '', 'cho', '', ?, ?)""",
                            (auto_ma, secrets.token_hex(6), amt, html.escape(content[:120]), provider_safe.lower(), now_iso),
                        )
                        conn.commit()
                        conn.close()
                    r = complete_order(auto_ma)
                    if r.get("ok"):
                        matched_here.append(auto_ma)
                        approved.append(auto_ma)

                ket_qua = f"da-duyet:{','.join(matched_here)}" if matched_here else "khong-khop-ma-deta"
                with DB_LOCK:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "INSERT INTO webhook_logs (nguon, tx_ref, so_tien, noi_dung, ket_qua, luc) VALUES (?, ?, ?, ?, ?, ?)",
                        (provider_safe, tx_ref, amt, content_safe, ket_qua, now_iso),
                    )
                    conn.commit()
                    conn.close()

            self.send_json({"success": True, "error": 0, "ok": True, "approved": approved})
            return

        if path.startswith("/api/admin/"):
            if is_auth_locked(client_ip):
                self.send_json({"ok": False, "loi": "Tạm khóa 15 phút do nhập sai khóa quản trị quá 5 lần."}, 429)
                return
            cfg = agent_worker.load_config()
            if not is_valid_admin_key(body.get("key") or "", cfg):
                record_auth_failure(client_ip)
                self.send_json({"ok": False, "loi": "Sai mã quản trị"}, 403)
                return
            clear_auth_failures(client_ip)

        if path == "/api/admin/config":
            cfg = agent_worker.load_config()
            cfg.setdefault("bank", {})
            for k_src, k_dst in [("bank_id", "bank_id"), ("bank_name", "bank_name"), ("account_no", "account_no"), ("account_name", "account_name")]:
                if body.get(k_src):
                    cfg["bank"][k_dst] = str(body[k_src]).strip()[:80]
            if body.get("owner_name"):
                cfg["owner_name"] = str(body["owner_name"]).strip()[:80]
            if "gemini_api_key" in body:
                cfg["gemini_api_key"] = str(body["gemini_api_key"] or "").strip()[:160]
            if "casso_checksum_key" in body:
                cfg["casso_checksum_key"] = str(body.get("casso_checksum_key") or "").strip()[:160]
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            os.chmod(CONFIG_PATH, 0o600)
            self.send_json({"ok": True})
            return

        if path == "/api/admin/duyet-don":
            ma = (body.get("ma") or "").strip().upper()
            res = complete_order(ma)
            self.send_json(res)
            return

        if path == "/api/admin/chay-luot":
            tom_tat = agent_worker.run_autonomous_turn()
            self.send_json({"ok": True, "tom_tat": tom_tat})
            return

        if path == "/api/b2b/dang-ky":
            ho_ten = html.escape(str(body.get("ho_ten") or "").strip()[:80]) or "Khách B2B"
            lien_he = html.escape(str(body.get("lien_he") or "").strip()[:120])
            goi = html.escape(str(body.get("goi") or "combo-990k").strip()[:80])
            raw_link = str(body.get("link_hien_tai") or "").strip()[:240]
            if raw_link and not re.match(r"^https?://", raw_link, re.I):
                if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw_link):
                    raw_link = "https://" + raw_link
                else:
                    raw_link = ""
            link_hien_tai = html.escape(raw_link)
            ghi_chu = html.escape(str(body.get("ghi_chu") or "").strip()[:800])
            nguon = html.escape(str(body.get("nguon") or "b2b-page").strip()[:60])
            if len(lien_he) < 6:
                self.send_json({"ok": False, "loi": "Bạn vui lòng nhập Số điện thoại Zalo (hoặc Email) hợp lệ để đội ngũ Deta liên hệ nhé!"}, 400)
                return
            now_iso = now_vn().isoformat(timespec="seconds")
            cf_ip_b = (self.headers.get("CF-Connecting-IP") or "").strip()
            cli_ip_b = self.client_address[0] if self.client_address else ""
            is_local_test = (not cf_ip_b and cli_ip_b in ("127.0.0.1", "::1", "localhost")) or bool(body.get("_test"))
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    """INSERT INTO b2b_leads (ho_ten, lien_he, goi, link_hien_tai, ghi_chu, nguon, trang_thai, tao_luc)
                    VALUES (?, ?, ?, ?, ?, ?, 'moi', ?)""",
                    (ho_ten, lien_he, goi, link_hien_tai, ghi_chu, nguon, now_iso),
                )
                lead_id = c.lastrowid
                if not is_local_test:
                    c.execute(
                        "INSERT INTO events (loai, nguon, luc) VALUES (?, ?, ?)",
                        ("b2b-lead", f"{goi}|{nguon}", now_iso),
                    )
                conn.commit()
                conn.close()
            self.send_json({"ok": True, "lead_id": lead_id, "tao_luc": now_iso})
            return

        if path == "/api/admin/b2b-status":
            try:
                lid = int(body.get("id") or 0)
            except (ValueError, TypeError):
                lid = 0
            st_new = (body.get("trang_thai") or "da-lien-he").strip()[:24]
            if st_new not in ("moi", "da-lien-he", "da-chot", "huy"):
                st_new = "da-lien-he"
            with DB_LOCK:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE b2b_leads SET trang_thai = ? WHERE id = ?", (st_new, lid))
                conn.commit()
                conn.close()
            self.send_json({"ok": True})
            return

        if path == "/api/admin/tracked-post":
            import numerology_comment_bot as ncb

            pid = (body.get("post_id") or "").strip()
            action = (body.get("action") or "").strip()
            store = ncb.load_tracked_store()
            entry = (store.get("posts") or {}).get(pid)
            if not entry:
                self.send_json({"ok": False, "loi": "Không tìm thấy bài viết này trong sổ theo dõi"}, 404)
                return
            if action == "toggle_good":
                new_pin = not bool(entry.get("pinned"))
                entry["pinned"] = new_pin
                entry["is_good"] = new_pin or (int(entry.get("comments_khach") or 0) >= ncb.GOOD_POST_MIN_COMMENTS) or (int(entry.get("reactions") or 0) >= ncb.GOOD_POST_MIN_REACTIONS)
                if new_pin:
                    entry["status"] = "active"
                    entry["ly_do_ngung"] = ""
            elif action == "archive":
                entry["pinned"] = False
                entry["status"] = "manual_archived"
                entry["ly_do_ngung"] = "Đã tắt theo dõi thủ công trên /admin"
            elif action == "activate":
                entry["status"] = "active"
                entry["ly_do_ngung"] = ""
                entry["last_interaction_at"] = now_vn().isoformat(timespec="seconds")
            ncb.save_tracked_store(store)
            self.send_json({"ok": True, "tracked_posts": ncb.get_tracked_posts_for_admin()})
            return

        if path == "/api/admin/chien-luoc-sang":
            res = agent_worker.run_morning_strategy(force=bool(body.get("force", True)))
            self.send_json({"ok": True, "chien_luoc": res})
            return

        self.send_json({"loi": "Không hỗ trợ phương thức này"}, 404)


def background_scheduler_loop() -> None:
    """Luồng chạy nền tự động:
    - 06:00 sáng hằng ngày: Phiên tự vấn chiến lược kiếm tiền (run_morning_strategy).
    - Mỗi 2 tiếng (phút :45 của giờ chẵn): Lượt làm việc tự hành (run_autonomous_turn).
    """
    last_triggered_slot = ""
    last_morning_date = ""
    while True:
        try:
            now = now_vn()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour >= 6 and last_morning_date != today_str:
                last_morning_date = today_str
                agent_worker.run_morning_strategy(force=False)
            if now.hour % 2 == 0 and now.minute == 45:
                slot = now.strftime("%Y-%m-%d %H:%M")
                if slot != last_triggered_slot:
                    last_triggered_slot = slot
                    agent_worker.run_autonomous_turn()
        except Exception:
            pass
        time.sleep(30)


if __name__ == "__main__":
    init_db()
    # Xuất bản sẵn bộ trang hướng dẫn SEO và sitemap.xml ngay lần khởi động đầu tiên
    cfg0 = agent_worker.load_config()
    agent_worker.build_seo_guides_and_sitemap(cfg0.get("site_url", "https://kiemtien.deta.vn"))

    t = threading.Thread(target=background_scheduler_loop, daemon=True)
    t.start()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), DetaHandler)
    print(f"[Deta AI Server] Đang chạy tại http://{host}:{port} (kiemtien.deta.vn)")
    server.serve_forever()
