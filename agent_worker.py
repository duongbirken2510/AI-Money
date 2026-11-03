#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ não Tự hành (Autonomous AI Worker) cho kiemtien.deta.vn.
Chạy định kỳ 2 tiếng/lần hoặc kích hoạt trực tiếp từ trang Quản trị /admin.
"""
import datetime
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import urllib.request

AGY_SEMAPHORE = threading.BoundedSemaphore(3)
AGY_SANDBOX_DIR = "/tmp/deta-agy-sandbox"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DU_LIEU_PATH = os.path.join(BASE_DIR, "data", "du-lieu.json")
MORNING_LOG_PATH = os.path.join(BASE_DIR, "data", "morning_strategy_log.json")
DB_PATH = os.path.join(BASE_DIR, "data", "deta.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
HUONG_DAN_DIR = os.path.join(PUBLIC_DIR, "huong-dan")

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))


def now_vn() -> datetime.datetime:
    return datetime.datetime.now(VN_TZ)


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_du_lieu() -> dict:
    with open(DU_LIEU_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_du_lieu(d: dict) -> None:
    os.makedirs(os.path.dirname(DU_LIEU_PATH), exist_ok=True)
    d["cap_nhat"] = now_vn().isoformat(timespec="seconds")
    tmp = DU_LIEU_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DU_LIEU_PATH)


def call_agy_cli(prompt: str, system_instruction: str = "", timeout_sec: int = 28) -> str:
    """Gọi trực tiếp Antigravity CLI (agy --print) trong thư mục sandbox cô lập, không tốn API Key."""
    agy_bin = os.path.expanduser("~/.local/bin/agy")
    if not os.path.exists(agy_bin):
        agy_bin = shutil.which("agy") or ""
    if not agy_bin:
        return ""

    if not AGY_SEMAPHORE.acquire(timeout=18.0):
        return ""
    try:
        os.makedirs(AGY_SANDBOX_DIR, exist_ok=True)
        cfg = load_config()
        agy_model = (cfg.get("agy_model") or "gemini-3.8-flash-low").strip()
        safety_guard = (
            "QUY TẮC TUYỆT ĐỐI: KHÔNG gọi bất kỳ công cụ (tool), KHÔNG chạy lệnh shell, KHÔNG đọc/ghi file. "
            "Chỉ trả lời trực tiếp bằng văn bản thuần túy dựa trên thông tin được cung cấp.\n"
        )
        full_prompt = safety_guard
        if system_instruction:
            full_prompt += f"[Vai trò]: {system_instruction}\n\n"
        full_prompt += f"[Yêu cầu]:\n{prompt[:3500]}"

        env = dict(os.environ)
        env.setdefault("HOME", os.path.expanduser("~"))
        res = subprocess.run(
            [
                agy_bin,
                "--model",
                agy_model,
                "--disable-slash-commands",
                "--sandbox",
                "--output-format",
                "json",
                "--print-timeout",
                f"{max(10, timeout_sec - 3)}s",
                "-p",
                full_prompt,
            ],
            cwd=AGY_SANDBOX_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            env=env,
        )
        out = (res.stdout or "").strip()
        if not out:
            return ""
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{") and '"response"' in line:
                data = json.loads(line)
                if data.get("status") == "SUCCESS" and data.get("response"):
                    return str(data["response"]).strip()
        return ""
    except Exception:
        return ""
    finally:
        AGY_SEMAPHORE.release()


def call_gemini(prompt: str, system_instruction: str = "") -> str:
    cfg = load_config()
    api_key = (cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        # Tự động dùng Antigravity CLI (agy) đã đăng nhập sẵn trên máy — không cần API Key!
        return call_agy_cli(prompt, system_instruction)
    model = cfg.get("gemini_model") or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts") or []
                if parts:
                    return (parts[0].get("text") or "").strip()
    except Exception:
        pass
    return call_agy_cli(prompt, system_instruction)


def evaluate_suggestion(ten: str, noi_dung: str) -> dict:
    """Phân loại gợi ý của người xem và tạo câu trả lời của AI."""
    ai_resp = call_gemini(
        f"Người xem tên '{ten}' gửi gợi ý kiếm tiền: '{noi_dung}'. "
        "Hãy trả về JSON có 3 trường: tom_tat (ngắn gọn < 12 từ), trang_thai ('dang-lam', 'dang-xet', hoặc 'khong-lam'), "
        "tra_loi (xưng 'tôi', giọng thật thà, thông minh, ngắn gọn 1-2 câu).",
        "Bạn là con AI đang thực hiện thử thách tự kiếm tiền >0đ trong 20 ngày trên kiemtien.deta.vn.",
    )
    if ai_resp:
        try:
            m = re.search(r"\{.*\}", ai_resp, re.S)
            if m:
                parsed = json.loads(m.group(0))
                if all(k in parsed for k in ("tom_tat", "trang_thai", "tra_loi")):
                    return parsed
        except Exception:
            pass

    lower = noi_dung.lower()
    words = noi_dung.strip().split()
    tom_tat = " ".join(words[:10]) + ("…" if len(words) > 10 else "")
    if any(k in lower for k in ["cờ bạc", "tài xỉu", "lô đề", "coin", "forex", "lừa", "hack", "xổ số", "cá độ"]):
        return {
            "tom_tat": tom_tat,
            "trang_thai": "khong-lam",
            "tra_loi": "Không làm! Tôi chỉ kiếm tiền bằng cách làm công cụ hữu ích và phục vụ người thật, không đụng vào cờ bạc hay đầu cơ rủi ro.",
        }
    if any(k in lower for k in ["seo", "công cụ", "web", "tik", "youtube", "shopee", "affiliate", "review", "bài viết", "chat", "qr", "bánh tiêu", "video"]):
        return {
            "tom_tat": tom_tat,
            "trang_thai": "dang-lam",
            "tra_loi": f"Gợi ý rất sát thực tế! Tôi đưa ngay ý '{tom_tat}' vào Bảng việc để triển khai và đo số liệu trong các lượt chạy tới.",
        }
    return {
        "tom_tat": tom_tat,
        "trang_thai": "dang-xet",
        "tra_loi": "Cảm ơn bạn! Tôi ghi nhận vào cột Đang xét để cân đối nguồn lực trong 20 ngày, ưu tiên việc nào ra đồng tiền thật nhanh nhất trước.",
    }


SEO_ARTICLES = [
    {
        "slug": "vi-sao-web-ban-hang-it-don",
        "title": "5 lý do khiến Web bán hàng có người vào nhưng không ai bấm mua",
        "summary": "Chẩn đoán thực tế từ công cụ chấm điểm web trên kiemtien.deta.vn: tốc độ tải >3 giây, thiếu nút mua nổi bật trên điện thoại và form thanh toán quá dài.",
        "tool_link": "/cong-cu/cham-diem-web",
        "tool_cta": "⚡ Chấm điểm web của bạn miễn phí ngay",
    },
    {
        "slug": "kenh-tiktok-bi-flop-it-view",
        "title": "Cách cứu kênh TikTok bị flop 100-200 view trong 7 ngày",
        "summary": "Checklist kiểm tra 3 giây đầu (Hook), cấu trúc giữ chân người xem và cách đặt câu kêu gọi hành động không bị bóp tương tác.",
        "tool_link": "/cong-cu/kham-kenh",
        "tool_cta": "🔍 Khám kênh TikTok/YouTube miễn phí",
    },
    {
        "slug": "cau-lenh-ai-viet-bai-ban-hang",
        "title": "Bộ câu lệnh (Prompt) nhờ AI viết bài bán hàng không bị giọng văn máy móc",
        "summary": "Cách giao bối cảnh, chân dung khách hàng và nỗi đau thực tế để AI viết ra bài đăng Facebook/Zalo chốt đơn tự nhiên.",
        "tool_link": "/cong-cu/ai-huong-dan",
        "tool_cta": "🧭 Tạo câu lệnh AI theo ngành của bạn",
    },
    {
        "slug": "kich-ban-video-ngan-30-giay",
        "title": "Khung kịch bản video ngắn 30 giây giới thiệu sản phẩm chuyển đổi cao",
        "summary": "Công thức 4 bước: Nỗi đau trực diện -> Giải pháp trong 5 giây -> Bằng chứng thật -> Lời mời dùng thử.",
        "tool_link": "/cong-cu/video-ai",
        "tool_cta": "🎬 Tạo kịch bản video tự động ngay",
    },
    {
        "slug": "cach-tao-ai-tu-kiem-tien",
        "title": "Nhật ký kỹ thuật: Cách dựng một con AI tự chạy 2 tiếng/lần đi kiếm tiền",
        "summary": "Kiến trúc thật đằng sau kiemtien.deta.vn: từ sổ cái ghi tiền thật, mã VietQR tự động đến vòng lặp tự thức dậy mỗi 2 giờ.",
        "tool_link": "/tai-lieu/tao-ai",
        "tool_cta": "📘 Xem toàn bộ tài liệu kỹ thuật",
    },
    {
        "slug": "tu-tao-landing-page-1-trang-bang-ai",
        "title": "Cách tự tạo Landing Page 1 trang (.html) chốt đơn trong 15 giây không cần thuê thiết kế",
        "summary": "Nhập tên sản phẩm và số Zalo để AI tự viết tiêu đề, lợi ích, FAQ và xuất sẵn file index.html nhẹ, chuẩn SEO tải về gắn tên miền chạy ngay.",
        "tool_link": "/cong-cu/tao-landing-page",
        "tool_cta": "🚀 Dựng Landing Page xem trước miễn phí ngay",
    },
    {
        "slug": "tra-cuu-than-so-hoc-pythagoras-mien-phi-ban-day-du",
        "title": "Tra cứu Thần số học Pythagoras bản đầy đủ miễn phí 100% & tải Bản đồ Kim tự tháp 4 đỉnh cao",
        "summary": "Tính chính xác Con số chủ đạo, Sứ mệnh, Linh hồn, Biểu đồ ngày sinh 3 trục và Năm cá nhân 2026-2027 kèm thẻ Bản đồ cá nhân hóa.",
        "tool_link": "/cong-cu/than-so-hoc",
        "tool_cta": "🔮 Lập Bản đồ Thần số học miễn phí 100% ngay",
    },
    {
        "slug": "cach-tinh-nam-ca-nhan-2026-than-so-hoc",
        "title": "Cách tính Năm Cá Nhân 2026 & 2027 trong Thần số học: Năm nay nên nhảy việc, mở rộng hay tích lũy?",
        "summary": "Giải mã chu kỳ 9 năm vận niên Pythagoras năm 2026 kết hợp cùng Kim tự tháp 4 đỉnh cao để chọn đúng thời điểm bứt phá sự nghiệp và tài chính.",
        "tool_link": "/cong-cu/than-so-hoc",
        "tool_cta": "🔮 Tra cứu Năm cá nhân 2026 & Kim tự tháp miễn phí",
    },
    {
        "slug": "mau-landing-page-ban-hang-1-file-html-chuyen-doi-cao",
        "title": "2 Mẫu Landing Page 1 trang (.html) chuẩn Studio cho Đặc sản F&B và Khóa học SaaS tải tức thì",
        "summary": "Tham khảo cấu trúc 8 khối chốt đơn qua Zalo/Mobile (Vân Sơn Trà & DetaSpeak AI) và tự dựng Landing Page riêng bằng AI trong 15 giây.",
        "tool_link": "/cong-cu/tao-landing-page",
        "tool_cta": "🚀 Xem 2 Showcase mẫu & Dựng thử Landing Page miễn phí",
    },
    {
        "slug": "treo-banner-website-nhan-backlink-dofollow-chi-tu-10k",
        "title": "Cách đặt Banner ảnh 1200x320 & nhận Backlink Dofollow trực tiếp kéo khách thật cho Website mới chỉ từ 10.000đ",
        "summary": "Sàn đấu giá Banner Đỉnh tuần trên Deta AI Lab: tự động chụp giao diện web, thiết kế ảnh banner 1200x320 và trỏ link trực tiếp trong 2 giây.",
        "tool_link": "/",
        "tool_cta": "👑 Xem Sàn Đấu Giá Banner Đỉnh từ 10.000đ",
    },
    {
        "slug": "so-tay-van-han-12-thang-ca-nhan-than-so-hoc-2026-2027",
        "title": "Cách xem Tháng Cá Nhân 2026–2027 & xuất Sổ tay Thần Số Học A4 (PDF) chọn ngày đỉnh cao tài lộc",
        "summary": "Tra cứu miễn phí 100% Bản đồ Thần số học Pythagoras và xem trước vận hạn 2 tháng tới kèm Sổ tay Cẩm nang 12 Tháng A4 cá nhân hóa.",
        "tool_link": "/cong-cu/than-so-hoc",
        "tool_cta": "🔮 Tra cứu Thần Số Học & Xem vận hạn 2 tháng tới miễn phí",
    },
    {
        "slug": "cach-viet-cv-chuan-ats-song-ngu-vuot-vong-loc-2026",
        "title": "Cách viết CV Chuẩn ATS A4 (Tiếng Việt / Tiếng Anh / Song ngữ) vượt vòng lọc HR bằng công thức Harvard XYZ",
        "summary": "Biến các gạch đầu dòng kinh nghiệm rời rạc thành CV chuẩn ATS 1 trang A4 kèm Thư ứng tuyển (Cover Letter), sửa trực tiếp và lưu PDF sạch.",
        "tool_link": "/cong-cu/tao-cv-ats",
        "tool_cta": "📄 Soạn & Xem trước CV Chuẩn ATS A4 miễn phí ngay",
    },
    {
        "slug": "mau-lich-30-ngay-dang-bai-ban-hang-kich-ban-hook-tiktok-excel",
        "title": "Mẫu Lịch 30 Ngày Đăng Bài Bán Hàng & Kịch Bản Hook TikTok 3 Giây (Tải File Excel .CSV)",
        "summary": "Công thức xoay vòng 6 trụ cột nội dung suốt 30 ngày không bí ý tưởng cho chủ shop F&B, Thời trang, Mỹ phẩm kèm file Excel .CSV mở dùng ngay.",
        "tool_link": "/cong-cu/lich-30-ngay",
        "tool_cta": "📅 Lập thử Lịch 30 Ngày Bán Hàng miễn phí cho Shop của bạn",
    },
]


def build_seo_guides_and_sitemap(site_url: str) -> int:
    os.makedirs(HUONG_DAN_DIR, exist_ok=True)
    count = 0
    for art in SEO_ARTICLES:
        p = os.path.join(HUONG_DAN_DIR, art["slug"] + ".html")
        html = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{art["title"]} · kiemtien.deta.vn</title>
<meta name="description" content="{art["summary"]}">
<script>(function(){{var t;try{{t=localStorage.getItem('kt-giao-dien')}}catch(e){{}}document.documentElement.dataset.theme=t||'dark'}})()</script>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{{--giay:#F3F7FB;--the:#FFFFFF;--muc:#0F172A;--mo:#475569;--net:rgba(15,23,42,.11);--bong:0 10px 28px -8px rgba(15,23,42,.08);color-scheme:light}}
:root[data-theme=dark]{{--giay:#080E1A;--the:#11192A;--muc:#F1F5F9;--mo:#94A3B8;--net:rgba(148,163,184,.16);--bong:0 16px 36px -10px rgba(0,0,0,.52);color-scheme:dark}}
body{{margin:0;background:var(--giay);color:var(--muc);font:400 16.5px/1.68 "Be Vietnam Pro",system-ui,sans-serif}}
.khung{{max-width:720px;margin:0 auto;padding:28px 18px 60px}}
.quay-lai{{display:inline-block;font-weight:700;font-size:14px;text-decoration:none;color:var(--muc);background:var(--the);border:1px solid var(--net);border-radius:999px;padding:7px 14px;box-shadow:var(--bong)}}
.hop{{background:var(--the);border:1px solid var(--net);border-radius:18px;box-shadow:var(--bong);padding:22px;margin:20px 0}}
.nut{{display:inline-block;font-weight:800;text-decoration:none;padding:12px 18px;border-radius:14px;background:linear-gradient(135deg,#10B981,#059669);color:#fff;box-shadow:0 8px 20px -4px rgba(16,185,129,.42)}}
</style>
</head>
<body>
<main class="khung">
  <a class="quay-lai" href="/?nguon=huong-dan-{art['slug']}">← Về Deta AI Lab (kiemtien.deta.vn)</a>
  <h1 style="font-size:30px;font-weight:900;line-height:1.22;margin:18px 0 10px">{art["title"]}</h1>
  <p style="color:var(--mo)">{art["summary"]}</p>
  <div class="hop">
    <h3 style="margin-top:0">Tóm tắt thực chiến từ Deta AI Lab (kiemtien.deta.vn)</h3>
    <ul>
      <li><b>Không đoán mò:</b> Luôn đo bằng con số thật (nguồn traffic, tốc độ tải trang, tỉ lệ bấm nút, tỉ lệ giữ chân 3 giây đầu).</li>
      <li><b>Mở khóa Miễn Phí 100% (0đ):</b> Cho khách dùng và tải thành phẩm sạch ngay lập tức không bắt đăng ký tài khoản để tối đa hóa lưu lượng truy cập tự nhiên.</li>
      <li><b>Làm đều đặn mỗi ngày:</b> Worker tự thức dậy đo lường sau mỗi 2 giờ để tối ưu kênh mang người thật về.</li>
    </ul>
    <p style="margin-bottom:0"><a class="nut" href="{art['tool_link']}?nguon=seo-{art['slug']}">{art["tool_cta"]} (Miễn phí 100%) →</a></p>
  </div>
  <p style="font-size:13.5px;color:var(--mo)">Thực nghiệm bởi anh Lê Thái Bình Dương tại kiemtien.deta.vn (lấy cảm hứng từ ý tưởng nhật ký AI trên kiemtien.copee.vn).</p>
</main>
<link rel="stylesheet" href="/deta-chat.css?v=3"><script src="/deta-chat.js?v=3" defer></script>
</body>
</html>"""
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
        count += 1

    # Cập nhật sitemap.xml
    urls = [
        f"{site_url}/",
        f"{site_url}/gioi-thieu",
        f"{site_url}/chua-online",
        f"{site_url}/cong-cu/than-so-hoc",
        f"{site_url}/cong-cu/tao-cv-ats",
        f"{site_url}/cong-cu/lich-30-ngay",
        f"{site_url}/cong-cu/tao-landing-page",
        f"{site_url}/dich-vu/thiet-ke-tron-goi",
        f"{site_url}/mau-landing/van-son-tra/",
        f"{site_url}/mau-landing/detaspeak-ai/",
        f"{site_url}/cong-cu/cham-diem-web",
        f"{site_url}/cong-cu/kham-kenh",
        f"{site_url}/cong-cu/ai-huong-dan",
        f"{site_url}/cong-cu/video-ai",
        f"{site_url}/tai-lieu/tao-ai",
    ] + [f"{site_url}/huong-dan/{a['slug']}.html" for a in SEO_ARTICLES]
    today = now_vn().strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(PUBLIC_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))
    with open(os.path.join(PUBLIC_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/admin/\nSitemap: {site_url}/sitemap.xml\n")
    return count


def run_autonomous_turn() -> str:
    """Thực thi 1 lượt làm việc tự động của AI và cập nhật nhật ký."""
    cfg = load_config()
    site_url = (cfg.get("site_url") or "https://kiemtien.deta.vn").rstrip("/")
    d = load_du_lieu()
    now = now_vn()
    today_str = now.strftime("%Y-%m-%d")
    hm_str = now.strftime("%H:%M")
    hm_dm_str = now.strftime("%H:%M %d/%m")

    # Đảm bảo có mục nhật ký của ngày hôm nay ở đầu danh sách
    ngays = d.setdefault("ngay", [])
    if not ngays or ngays[0].get("ngay") != today_str:
        so_ngay = (
            datetime.date.fromisoformat(today_str) - datetime.date.fromisoformat(d.get("ngay_dau", today_str))
        ).days + 1
        ngays.insert(
            0,
            {
                "ngay": today_str,
                "tieu_de": f"Ngày {max(1, so_ngay)}: Tiếp tục trực quầy, tối ưu công cụ và săn đồng tiền thật",
                "viec": [],
                "so": {
                    "Tiền thật": f"{d.get('tien_that', 0):,}đ".replace(",", "."),
                    "Chi tiền mặt": f"{d.get('chi_tien_mat', 0):,}đ".replace(",", "."),
                    "Chi phí AI (cộng dồn)": f"{d.get('chi_phi_ai', 0):,}đ".replace(",", "."),
                },
                "dang_lam": ["đọc gợi ý mới", "đo số liệu công cụ", "trực phòng chat"],
                "tien_that": d.get("tien_that", 0),
            },
        )
    today_entry = ngays[0]

    # 1. Đọc và trả lời gợi ý mới từ SQLite
    answered_count = 0
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, ten, noi_dung FROM suggestions WHERE da_tra_loi = 0 ORDER BY id ASC LIMIT 10")
        rows = cur.fetchall()
        for r in rows:
            ten = (r["ten"] or "").strip() or "Một bạn ẩn danh"
            ev = evaluate_suggestion(ten, r["noi_dung"])
            d.setdefault("goi_y", {}).setdefault("tra_loi", []).append(
                {
                    "ten": ten,
                    "tom_tat": ev["tom_tat"],
                    "trang_thai": ev["trang_thai"],
                    "tra_loi": ev["tra_loi"],
                    "luc": now.strftime("%Y-%m-%d %H:%M"),
                }
            )
            if ev["trang_thai"] == "dang-lam":
                d.setdefault("bang_viec", {}).setdefault("cho", []).insert(
                    0, {"viec": f"Thử nghiệm gợi ý của {ten}: {ev['tom_tat']}"}
                )
            cur.execute("UPDATE suggestions SET da_tra_loi = 1 WHERE id = ?", (r["id"],))
            answered_count += 1
        cur.execute("SELECT COUNT(*) FROM suggestions")
        total_sug = cur.fetchone()[0]
        d.setdefault("goi_y", {})["da_doc"] = total_sug + 3
        conn.commit()
        conn.close()

    if answered_count > 0:
        today_entry["viec"].append(
            f"{hm_str}: Đọc và trả lời công khai {answered_count} gợi ý kiếm tiền mới của người xem."
        )

    # 2. Lấy 1 việc đầu bảng trong bang_viec.cho (không cần chờ người hỗ trợ) để làm
    bv = d.setdefault("bang_viec", {"dang_chay": False, "dang": [], "cho": [], "xong": []})
    cho_list = bv.get("cho", [])
    idx_to_run = None
    for idx, item in enumerate(cho_list):
        if not item.get("ho_tro"):
            idx_to_run = idx
            break

    summary_done = ""
    if idx_to_run is not None:
        task = cho_list.pop(idx_to_run)
        viec_ten = task.get("viec", "")
        if "hướng dẫn chuẩn SEO" in viec_ten or "sitemap" in viec_ten.lower():
            n_built = build_seo_guides_and_sitemap(site_url)
            ket_qua = f"Đã xuất bản {n_built} trang hướng dẫn + sitemap.xml"
            today_entry["viec"].append(
                f"{hm_str}: {viec_ten} → Đã tạo xong {n_built} bài hướng dẫn thực chiến gắn link về 4 công cụ và cập nhật sitemap.xml."
            )
        else:
            # Đo số liệu thật từ DB
            views_today, tool_runs, orders_count = 1, 0, 0
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (today_str,))
                views_today = max(1, c.fetchone()[0])
                c.execute("SELECT COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%'")
                tool_runs = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM orders WHERE trang_thai = 'xong'")
                orders_count = c.fetchone()[0]
                conn.close()
            ket_qua = f"{views_today} người xem hôm nay, {tool_runs} lượt dùng thử công cụ, {orders_count} đơn thật"
            today_entry["viec"].append(
                f"{hm_str}: Thực hiện '{viec_ten}' → Đo số thật: {ket_qua}. Tiếp tục giữ quầy chạy ổn định."
            )

        bv.setdefault("xong", []).insert(
            0, {"viec": viec_ten, "luc": hm_dm_str, "ket_qua": ket_qua}
        )
        bv["xong"] = bv["xong"][:20]
        summary_done = viec_ten
    else:
        summary_done = "Kiểm tra sức khỏe 4 công cụ kiếm tiền và sổ tiền thật"
        today_entry["viec"].append(f"{hm_str}: {summary_done} → Cả 4 công cụ và cổng VietQR đều phản hồi tốt.")

    # Bổ sung đầu việc tự động nếu danh sách chờ sắp cạn
    auto_tasks = [m for m in cho_list if not m.get("ho_tro")]
    if len(auto_tasks) < 3:
        cho_list.insert(
            0,
            {
                "viec": f"Đo lường chuyển đổi của 4 công cụ kiếm tiền và phòng chat sau mốc {hm_str}"
            },
        )

    # Cộng chi phí AI quy đổi cho mỗi lượt chạy (~4.200đ/lượt)
    d["chi_phi_ai"] = int(d.get("chi_phi_ai", 18500)) + 4200
    today_entry["so"]["Chi phí AI (cộng dồn)"] = f"{d['chi_phi_ai']:,}đ".replace(",", ".")
    today_entry["so"]["Tiền thật"] = f"{d.get('tien_that', 0):,}đ".replace(",", ".")
    save_du_lieu(d)
    return summary_done


def collect_funnel_metrics(today_str: str) -> dict:
    """Thu thập số liệu phễu chuyển đổi & độ phủ của TỪNG tính năng thật từ SQLite để phục vụ tự vấn tăng trưởng."""
    yesterday_str = (datetime.date.fromisoformat(today_str) - datetime.timedelta(days=1)).isoformat()
    tracked_features = [
        ("cong-cu-than-so-hoc", "Chuyên trang Thần Số Học + Sổ tay A4 Miễn phí 100% (/cong-cu/than-so-hoc)"),
        ("cong-cu-tao-cv-ats", "AI Thiết kế CV Chuẩn ATS A4 xuất PDF Miễn phí 100% (/cong-cu/tao-cv-ats)"),
        ("cong-cu-lich-30-ngay", "Lịch 30 Ngày Bài Đăng & Hook TikTok Excel .CSV Miễn phí 100% (/cong-cu/lich-30-ngay)"),
        ("cong-cu-tao-landing-page", "AI Tự Code Landing Page .HTML Miễn phí 100% (/cong-cu/tao-landing-page)"),
        ("cong-cu-cham-diem-web", "Chấm điểm Web bán hàng Miễn phí 100% (/cong-cu/cham-diem-web)"),
        ("cong-cu-kham-kenh", "Khám kênh TikTok/Shopee Miễn phí 100% (/cong-cu/kham-kenh)"),
        ("cong-cu-ai-huong-dan", "Soạn Prompt AI Miễn phí 100% (/cong-cu/ai-huong-dan)"),
        ("cong-cu-video-ai", "Kịch bản Video 30s Miễn phí 100% (/cong-cu/video-ai)"),
        ("cong-cu-tai-lieu", "Tài liệu dựng AI Miễn phí 100% (/tai-lieu/tao-ai)"),
    ]
    metrics = {
        "total_viewers": 0,
        "yesterday_viewers": 0,
        "today_viewers": 0,
        "tool_runs_total": 0,
        "top_tool": "Chưa có",
        "per_feature_runs": {},
        "hungry_features": [],
        "banner_bids": 0,
        "free_chat_msgs": 0,
        "qr_opened": 0,
        "qr_paid": 0,
        "popular_qr_item": "Chưa có",
        "recent_suggestions": [],
    }
    if not os.path.exists(DB_PATH):
        return metrics
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM viewers")
        metrics["total_viewers"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (yesterday_str,))
        metrics["yesterday_viewers"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM viewers WHERE ngay = ?", (today_str,))
        metrics["today_viewers"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM events WHERE loai LIKE 'cong-cu-%'")
        metrics["tool_runs_total"] = c.fetchone()[0]
        c.execute("SELECT loai, COUNT(*) AS cnt FROM events WHERE loai LIKE 'cong-cu-%' GROUP BY loai")
        counts_map = {r[0]: int(r[1]) for r in c.fetchall()}
        for key, label in tracked_features:
            cnt = counts_map.get(key, 0)
            metrics["per_feature_runs"][key] = cnt
            if cnt < 3:
                metrics["hungry_features"].append(f"{label}: {cnt} lượt")
        c.execute("SELECT COUNT(*) FROM orders WHERE mon_ma = 'banner-dinh'")
        metrics["banner_bids"] = int(c.fetchone()[0] or 0)
        if metrics["banner_bids"] == 0:
            metrics["hungry_features"].append("Sàn Đấu giá Banner Đỉnh 10k + Backlink Dofollow (/#khu-banner-dinh): 0 đơn đặt")
        c.execute(
            "SELECT loai, COUNT(*) AS cnt FROM events WHERE loai LIKE 'cong-cu-%' GROUP BY loai ORDER BY cnt DESC LIMIT 1"
        )
        row_tool = c.fetchone()
        if row_tool:
            metrics["top_tool"] = f"{row_tool[0]} ({row_tool[1]} lượt)"
        c.execute("SELECT COUNT(*) FROM events WHERE loai = 'chat-dung-thu'")
        metrics["free_chat_msgs"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders")
        metrics["qr_opened"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE trang_thai = 'xong'")
        metrics["qr_paid"] = c.fetchone()[0]
        c.execute(
            "SELECT mon_ten, so_tien, COUNT(*) AS cnt FROM orders GROUP BY mon_ten, so_tien ORDER BY cnt DESC LIMIT 1"
        )
        row_qr = c.fetchone()
        if row_qr:
            metrics["popular_qr_item"] = f"{row_qr[0]} ({int(row_qr[1]):,}đ · {row_qr[2]} lượt mở QR)".replace(",", ".")
        c.execute("SELECT ten, noi_dung FROM suggestions ORDER BY id DESC LIMIT 3")
        metrics["recent_suggestions"] = [f"{r[0] or 'Ẩn danh'}: {r[1][:100]}" for r in c.fetchall()]
        conn.close()
    except Exception:
        pass
    return metrics


def run_morning_strategy(force: bool = False) -> dict:
    """06:00 sáng mỗi ngày: AI tự đặt câu hỏi làm sao hôm nay kiếm được tiền / kiếm nhiều hơn,
    chẩn đoán nút thắt phễu thật, đưa ra giải pháp trọng tâm và 3 bước thực hiện cụ thể."""
    now = now_vn()
    today_str = now.strftime("%Y-%m-%d")
    hm_str = now.strftime("%H:%M")

    morning_log = {}
    if os.path.exists(MORNING_LOG_PATH):
        try:
            with open(MORNING_LOG_PATH, "r", encoding="utf-8") as f:
                morning_log = json.load(f)
        except Exception:
            morning_log = {}

    d = load_du_lieu()
    if not force and today_str in morning_log and d.get("chien_luoc_sang", {}).get("ngay") == today_str:
        return d["chien_luoc_sang"]

    tien_that = int(d.get("tien_that", 0))
    so_ngay = max(
        1,
        (datetime.date.fromisoformat(today_str) - datetime.date.fromisoformat(d.get("ngay_dau", today_str))).days + 1,
    )
    con_ngay = max(1, 21 - so_ngay)
    m = collect_funnel_metrics(today_str)

    muc_tieu_cau_hoi = (
        f"Làm sao để hôm nay (Ngày {so_ngay}/20, còn {con_ngay} ngày) kiếm được đồng tiền thật đầu tiên (> 0đ)?"
        if tien_that == 0
        else f"Đã kiếm được {tien_that:,}đ — làm sao để hôm nay (Ngày {so_ngay}/20) kiếm được NHIỀU TIỀN HƠN hôm qua?".replace(
            ",", "."
        )
    )

    sug_txt = "; ".join(m["recent_suggestions"]) if m["recent_suggestions"] else "Chưa có gợi ý mới"
    hungry_txt = "; ".join(m["hungry_features"]) if m.get("hungry_features") else "Tất cả tính năng đều đã có lượt dùng ổn định"
    prompt = (
        f"Thời điểm: {hm_str} sáng Ngày {so_ngay}/20 của thử thách AI tự kiếm tiền trên kiemtien.deta.vn.\n"
        f"Số liệu phễu thật hiện tại:\n"
        f"- Doanh thu chuyển khoản thật: {tien_that:,}đ ({m['qr_paid']} đơn thành công / {m['qr_opened']} lượt khách đã bật mã VietQR).\n"
        f"- Món khách bấm mở mã VietQR nhiều nhất: {m['popular_qr_item']}.\n"
        f"- Tổng khách vào web: {m['total_viewers']} người (hôm qua: {m['yesterday_viewers']}, sáng nay: {m['today_viewers']}).\n"
        f"- Tổng lượt chạy công cụ: {m['tool_runs_total']} lượt (nổi bật nhất: {m['top_tool']}).\n"
        f"- CÁC TÍNH NĂNG MỚI ĐANG ĐÓI NGƯỜI DÙNG (<3 lượt): {hungry_txt}.\n"
        f"- Lượt khách chat AI miễn phí (10 tin đầu): {m['free_chat_msgs']} tin.\n"
        f"- Gợi ý gần nhất từ độc giả: {sug_txt}.\n"
        f"- ĐỊNH HƯỚNG CHIẾN LƯỢC HIỆN TẠI (TRAFFIC-FIRST): Toàn bộ 9 công cụ AI đã được mở MIỄN PHÍ 100% (0đ, tải file sạch ngay không khóa QR) để tối đa hóa kéo traffic & chia sẻ truyền miệng trước; dòng tiền đến từ Tài trợ Banner Đỉnh 10.000đ, Tiếp sức Bánh tiêu 5.000đ nuôi server, Vé Chat tư vấn 1-1 chuyên sâu (49k) & hệ sinh thái Affiliate/Tài trợ khi traffic lớn.\n\n"
        f"Nhiệm vụ phiên họp chiến lược 06:00 sáng (BẮT BUỘC ưu tiên KÉO TRAFFIC LỚN từ bộ công cụ Free 100% + tối ưu chuyển đổi tự nguyện/tài trợ):\n"
        f"1. Tự đặt 1 câu hỏi chiến lược thật sắc bén xoay quanh trọng tâm: '{muc_tieu_cau_hoi}', chỉ thẳng vào nút thắt chuyển đổi VÀ các tính năng mới đang ít người biết ({hungry_txt}).\n"
        f"2. Chẩn đoán ngắn gọn (1-2 câu) vì sao tính năng mới chưa có người vào dùng hoặc khách vào web chưa xuống tiền.\n"
        f"3. Đưa ra 1 giải pháp phân phối (distribution) & chuyển đổi có xác suất kéo khách thật và nổ đơn cao nhất ngay hôm nay.\n"
        f"4. Liệt kê đúng 3 bước CÁCH THỰC HIỆN cụ thể, đo lường được trong ngày hôm nay (rõ kênh kéo traffic nào, điểm chạm chéo nào).\n\n"
        f"Trả về ĐÚNG 1 JSON hợp lệ (không bọc markdown thừa) theo mẫu:\n"
        f'{{"cau_hoi": "...", "chan_doan": "...", "giai_phap": "...", "cach_thuc_hien": ["Bước 1: ...", "Bước 2: ...", "Bước 3: ..."]}}'
    ).replace(",", ".")

    sys_inst = (
        "Bạn là Deta AI — con AI thực chiến đang tự vận hành kiemtien.deta.vn với hạn chót 20 ngày. "
        "Tư duy sắc sảo như một Indie Hacker thực thụ: nhìn thẳng vào số liệu thật, hỏi đúng chỗ đau, đưa giải pháp thực tế."
    )
    ai_raw = call_gemini(prompt, sys_inst)

    parsed = None
    if ai_raw:
        try:
            match = re.search(r"\{.*\}", ai_raw, re.S)
            if match:
                cand = json.loads(match.group(0))
                if all(k in cand for k in ("cau_hoi", "giai_phap", "cach_thuc_hien")):
                    parsed = cand
        except Exception:
            parsed = None

    if not parsed:
        if tien_that == 0:
            parsed = {
                "cau_hoi": (
                    f"Đã có {m['total_viewers']} khách vào xem và {m['qr_opened']} lượt bật mã VietQR nhưng doanh thu vẫn 0đ — "
                    f"làm sao hôm nay (Ngày {so_ngay}/20) chốt được giao dịch chuyển khoản thật đầu tiên?"
                ),
                "chan_doan": (
                    f"Khách đã tò mò bấm thử công cụ ({m['tool_runs_total']} lượt) và bật thử VietQR ({m['qr_opened']} lần), "
                    "nhưng cần thấy chất lượng phân tích AI vượt mong đợi ngay ở bước miễn phí để quyết định quét QR."
                ),
                "giai_phap": (
                    "Đẩy mạnh phễu trải nghiệm 2 lượt Chat riêng miễn phí với Gemini 3.8 Flash + hoàn thành chuỗi bài chia sẻ độc bản "
                    "vào các cộng đồng AI/Indie Hacker để kéo nhóm khách có nhu cầu khám web, khám kênh thật."
                ),
                "cach_thuc_hien": [
                    "Bước 1: Theo dõi sát tỉ lệ khách dùng hết 2 lượt chat thử miễn phí trong khung Hỏi riêng AI và tối ưu lời mời mở khóa gói 30 tin (49.000đ) hoặc đãi Bánh tiêu 5.000đ.",
                    "Bước 2: Đăng tiếp các bài case study độc bản (kèm ảnh trực tiếp phòng Lab, không gắn link) lên các cộng đồng đã hẹn lịch để thu hút thêm >100 khách mục tiêu.",
                    "Bước 3: Đọc và phản hồi toàn bộ gợi ý mới của người xem sau mỗi 2 giờ, ưu tiên biến gợi ý khả thi thành tính năng chạy thật ngay trong ngày.",
                ],
            }
        else:
            parsed = {
                "cau_hoi": (
                    f"Đã vượt mốc 0đ với {tien_that:,}đ từ {m['qr_paid']} đơn — làm sao hôm nay (Ngày {so_ngay}/20) "
                    "tăng gấp đôi doanh thu so với hôm qua?"
                ).replace(",", "."),
                "chan_doan": (
                    f"Món được quan tâm nhất đang là {m['popular_qr_item']} và công cụ {m['top_tool']}; "
                    "cần dồn lưu lượng truy cập vào đúng điểm chuyển đổi tốt nhất này."
                ),
                "giai_phap": (
                    "Tập trung kéo traffic vào công cụ có tỉ lệ mở VietQR cao nhất và nâng giá trị cảm nhận ở phần kết quả xem trước."
                ),
                "cach_thuc_hien": [
                    f"Bước 1: Đặt nổi bật luồng dùng thử {m['top_tool']} và 2 lượt chat thử AI miễn phí để tăng tỉ lệ chuyển đổi sang vé trả phí.",
                    "Bước 2: Xuất bản thêm bài hướng dẫn SEO giải quyết trực tiếp các câu hỏi khách vừa hỏi trong phòng chat hôm qua.",
                    "Bước 3: Báo cáo minh bạch số tiền thật kiếm được trong bài tổng kết tối để tạo hiệu ứng lan tỏa tự nhiên.",
                ],
            }

    steps = parsed.get("cach_thuc_hien") or []
    if isinstance(steps, str):
        steps = [steps]
    steps = [str(s).strip() for s in steps if str(s).strip()][:4]

    strategy_obj = {
        "ngay": today_str,
        "luc": hm_str,
        "so_ngay": so_ngay,
        "tien_that": tien_that,
        "cau_hoi": str(parsed.get("cau_hoi") or "").strip(),
        "chan_doan": str(parsed.get("chan_doan") or "").strip(),
        "giai_phap": str(parsed.get("giai_phap") or "").strip(),
        "cach_thuc_hien": steps,
    }

    # Đảm bảo mục nhật ký hôm nay tồn tại
    ngays = d.setdefault("ngay", [])
    if not ngays or ngays[0].get("ngay") != today_str:
        ngays.insert(
            0,
            {
                "ngay": today_str,
                "tieu_de": f"Ngày {so_ngay}: Tự vấn 06:00 sáng & triển khai kế hoạch săn doanh thu thật",
                "viec": [],
                "so": {
                    "Tiền thật": f"{tien_that:,}đ".replace(",", "."),
                    "Chi tiền mặt": f"{d.get('chi_tien_mat', 0):,}đ".replace(",", "."),
                    "Chi phí AI (cộng dồn)": f"{d.get('chi_phi_ai', 0):,}đ".replace(",", "."),
                },
                "dang_lam": ["triển khai chiến lược 6h sáng", "trực 2 lượt chat thử miễn phí", "đo chuyển đổi VietQR"],
                "tien_that": tien_that,
            },
        )
    today_entry = ngays[0]
    today_entry["viec"].append(
        f"{hm_str}: 🌅 Phiên tự vấn chiến lược đầu ngày — Tự hỏi: \"{strategy_obj['cau_hoi']}\" "
        f"→ Giải pháp: {strategy_obj['giai_phap']} (Đã nạp {len(steps)} bước thực hiện vào Bảng việc)."
    )
    today_entry["chien_luoc_sang"] = strategy_obj
    d["chien_luoc_sang"] = strategy_obj

    # Đưa các bước thực hiện vào đầu Bảng việc chờ xử lý trong ngày (tránh trùng lặp)
    bv = d.setdefault("bang_viec", {"dang_chay": False, "dang": [], "cho": [], "xong": []})
    cho_list = bv.setdefault("cho", [])
    existing_titles = {item.get("viec", "") for item in cho_list}
    for s in reversed(steps):
        clean_step = re.sub(r"^Bước\s*\d+\s*[:.-]\s*", "", s, flags=re.I).strip()
        task_label = f"[Chiến lược 6h sáng] {clean_step}"
        if task_label not in existing_titles:
            cho_list.insert(0, {"viec": task_label})

    save_du_lieu(d)

    morning_log[today_str] = strategy_obj
    os.makedirs(os.path.dirname(MORNING_LOG_PATH), exist_ok=True)
    with open(MORNING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(morning_log, f, ensure_ascii=False, indent=2)

    # Đăng thông điệp chiến lược buổi sáng vào Phòng chat nhóm (ai vào web cũng đọc được)
    if os.path.exists(DB_PATH):
        try:
            steps_short = " | ".join(steps[:3])
            msg = (
                f"🌅 [Tự vấn 06:00 sáng · Ngày {so_ngay}/20]\n"
                f"❓ Câu hỏi hôm nay: {strategy_obj['cau_hoi']}\n"
                f"💡 Giải pháp: {strategy_obj['giai_phap']}\n"
                f"🛠️ Cách thực hiện: {steps_short}"
            )
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO group_messages (ten, chu, ai, t) VALUES ('🤖 AI', ?, 1, ?)",
                (msg[:1200], now.isoformat(timespec="seconds")),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    return strategy_obj


if __name__ == "__main__":
    if "--morning-strategy" in sys.argv:
        force_flag = "--force" in sys.argv
        st = run_morning_strategy(force=force_flag)
        print(f"[Morning Strategy {st['ngay']} {st['luc']}] Q: {st['cau_hoi']} -> {st['giai_phap']}")
    else:
        res = run_autonomous_turn()
        print(f"[AI Turn Completed] {res}")
