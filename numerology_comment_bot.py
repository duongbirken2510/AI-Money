#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hệ thống Theo dõi Vòng đời Bài viết MXH & Trực Bình luận Định kỳ 4h/lần (Deta AI Lab):
- Lưu danh sách từng bài viết đã đăng vào `data/tracked_posts.json` (Post Watchlist).
- Tự động đo lường tương tác (cảm xúc, số bình luận khách, số phản hồi đã trả) mỗi 4 giờ/lần:
  + Bài viết tốt (>= 2 bình luận khách hoặc >= 5 cảm xúc, hoặc được ghim trên /admin) -> Đánh dấu ⭐ Bài tốt (`is_good=True`) để ưu tiên kiểm tra đầu tiên.
  + Bài viết sau 2 ngày (48h) từ lúc đăng không có tương tác nào, hoặc sau 3 ngày (72h) từ tương tác cuối cùng không phát sinh tương tác mới -> Tự động chuyển sang `archived` (bỏ khỏi danh sách theo dõi).
- Luôn chuyển bộ lọc sang "Tất cả bình luận" trước khi quét, đính kèm ảnh PNG có watermark `kiemtien.deta.vn` và trả lời 0-link tuyệt đối.
"""

import datetime
import hashlib
import json
import os
import re
import time
import urllib.request

import agent_worker
import numerology_engine as ne
import social_autopilot as sa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPLIED_LOG_PATH = os.path.join(BASE_DIR, "data", "tsh_replied_comments.json")
TRACKED_POSTS_PATH = os.path.join(BASE_DIR, "data", "tracked_posts.json")

# Ngưỡng tự động đánh dấu Bài Tốt & tự động bỏ theo dõi bài nguội sau 2-3 ngày
GOOD_POST_MIN_COMMENTS = 2
GOOD_POST_MIN_REACTIONS = 5
NO_INTERACTION_EXPIRE_HOURS = 48.0       # 2 ngày (48h) không có bất kỳ tương tác nào -> bỏ theo dõi
IDLE_AFTER_ACTIVE_EXPIRE_HOURS = 72.0    # 3 ngày (72h) kể từ tương tác gần nhất không có thêm tương tác -> bỏ theo dõi

DOB_REGEX = re.compile(r"\b(\d{1,2})\s*[-/.\stháng]+\s*(\d{1,2})\s*[-/.\snăm]+\s*(19\d{2}|20[0-2]\d|\d{2})\b", re.I)
TOOL_QUESTION_REGEX = re.compile(
    r"\b(xin link|link đâu|link ở đâu|web gì|trang nào|tên web|địa chỉ|vào đâu|dùng thử|dùng thế nào|dùng sao|"
    r"miễn phí thật|có free|b2b|làm trọn gói|thiết kế web|làm landing|giá sao|báo giá|tư vấn giúp|cho mình xin)\b",
    re.I,
)


def load_replied() -> dict:
    if os.path.exists(REPLIED_LOG_PATH):
        try:
            with open(REPLIED_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_replied(data: dict) -> None:
    os.makedirs(os.path.dirname(REPLIED_LOG_PATH), exist_ok=True)
    with open(REPLIED_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_tracked_store() -> dict:
    default = {"posts": {}, "groups_harvested": {}, "last_scan_at": ""}
    if os.path.exists(TRACKED_POSTS_PATH):
        try:
            with open(TRACKED_POSTS_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict) and "posts" in raw:
                    raw.setdefault("groups_harvested", {})
                    raw.setdefault("last_scan_at", "")
                    return raw
        except Exception:
            pass
    return default


def save_tracked_store(store: dict) -> None:
    os.makedirs(os.path.dirname(TRACKED_POSTS_PATH), exist_ok=True)
    with open(TRACKED_POSTS_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def extract_post_id(post_url: str) -> str:
    m = re.search(r"(?:set=gm\.|permalink/|posts/|multi_permalinks=)(\d+)", post_url or "")
    if m:
        return m.group(1)
    return hashlib.sha1((post_url or "").encode("utf-8")).hexdigest()[:14]


def parse_iso_vn(ts_str: str) -> datetime.datetime | None:
    if not ts_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
        return dt
    except Exception:
        return None


def register_or_update_post(
    store: dict,
    post_url: str,
    group_key: str,
    group_name: str,
    group_url: str,
    posted_at: str = "",
) -> dict:
    """Đăng ký bài viết mới vào sổ theo dõi (ưu tiên giữ URL dạng /photo/?fbid=...&set=gm... nếu có)."""
    pid = extract_post_id(post_url)
    now_iso = sa.now_vn().isoformat(timespec="seconds")
    posts = store.setdefault("posts", {})
    loai = "than-so-hoc" if group_key.startswith("tsh-") else "cong-cu-b2b"
    if pid in posts:
        entry = posts[pid]
        if "/photo/" in post_url and "/photo/" not in entry.get("post_url", ""):
            entry["post_url"] = post_url
        return entry

    # Kiểm tra lịch sử trả lời cũ (nếu có) để khởi tạo đúng số phản hồi & thời điểm tương tác
    replied_db = load_replied()
    prev_replies = []
    seen_authors = set()
    for v in replied_db.values():
        if extract_post_id(v.get("post_url", "")) == pid:
            author_k = (v.get("author_fb") or v.get("ho_ten") or "").strip().lower()
            if author_k and author_k not in seen_authors:
                seen_authors.add(author_k)
                prev_replies.append(v.get("luc") or "")

    p_at = posted_at or now_iso
    last_inter = max([p_at] + [t for t in prev_replies if t])
    init_replies = len(seen_authors)
    is_good = init_replies >= GOOD_POST_MIN_COMMENTS

    entry = {
        "post_id": pid,
        "group_key": group_key,
        "group_name": group_name,
        "group_url": group_url,
        "loai": loai,
        "post_url": post_url,
        "posted_at": p_at,
        "discovered_at": now_iso,
        "last_checked_at": "",
        "last_interaction_at": last_inter,
        "comments_khach": init_replies,
        "replies_da_gui": init_replies,
        "reactions": 0,
        "is_good": is_good,
        "pinned": False,
        "status": "active",
        "ly_do_ngung": "",
    }
    posts[pid] = entry
    return entry


def evaluate_post_lifecycle(entry: dict, now_dt: datetime.datetime | None = None) -> dict:
    """
    Cập nhật nhãn ⭐ Bài tốt và tự động bỏ theo dõi nếu bài nguội sau 2-3 ngày:
    - Đánh dấu `is_good = True` nếu bài có >= 2 bình luận khách hoặc >= 5 cảm xúc (hoặc được ghim `pinned`).
    - Nếu không ghim tay (`not pinned`):
      + Chưa có tương tác (0 bình luận khách & < 3 cảm xúc) sau 48h (2 ngày) từ lúc đăng -> `archived`.
      + Đã có tương tác nhưng suốt 72h (3 ngày) từ `last_interaction_at` không có thêm tương tác mới -> `archived`.
    """
    now_dt = now_dt or sa.now_vn()
    c_cnt = int(entry.get("comments_khach") or 0)
    r_cnt = int(entry.get("reactions") or 0)

    if entry.get("pinned") or c_cnt >= GOOD_POST_MIN_COMMENTS or r_cnt >= GOOD_POST_MIN_REACTIONS:
        entry["is_good"] = True

    if entry.get("pinned"):
        entry["status"] = "active"
        entry["ly_do_ngung"] = ""
        return entry

    if entry.get("status") == "manual_archived":
        return entry

    posted_dt = parse_iso_vn(entry.get("posted_at") or "") or now_dt
    last_inter_dt = parse_iso_vn(entry.get("last_interaction_at") or "") or posted_dt

    age_hours = max(0.0, (now_dt - posted_dt).total_seconds() / 3600.0)
    idle_hours = max(0.0, (now_dt - last_inter_dt).total_seconds() / 3600.0)
    has_meaningful_engagement = (c_cnt > 0) or (r_cnt >= 3)

    if not has_meaningful_engagement and age_hours >= NO_INTERACTION_EXPIRE_HOURS:
        entry["status"] = "archived"
        entry["ly_do_ngung"] = f"Tự động bỏ theo dõi sau {int(age_hours)}h (>2 ngày) không có tương tác"
    elif has_meaningful_engagement and idle_hours >= IDLE_AFTER_ACTIVE_EXPIRE_HOURS:
        entry["status"] = "archived"
        entry["ly_do_ngung"] = f"Tự động bỏ theo dõi sau {int(idle_hours)}h (>3 ngày) không phát sinh tương tác mới"
    else:
        entry["status"] = "active"
        entry["ly_do_ngung"] = ""
    return entry


def get_tracked_posts_for_admin() -> dict:
    """Trả về danh sách bài viết đã sắp xếp & tổng hợp thống kê cho trang /admin."""
    store = load_tracked_store()
    posts_list = list((store.get("posts") or {}).values())

    def _sort_key(p: dict):
        st_rank = 0 if p.get("status") == "active" else 1
        good_rank = 0 if (p.get("pinned") or p.get("is_good")) else 1
        return (st_rank, good_rank, -(parse_iso_vn(p.get("last_interaction_at") or p.get("posted_at") or "") or sa.now_vn()).timestamp())

    posts_list.sort(key=_sort_key)
    active_cnt = sum(1 for p in posts_list if p.get("status") == "active")
    good_cnt = sum(1 for p in posts_list if p.get("status") == "active" and (p.get("is_good") or p.get("pinned")))
    archived_cnt = sum(1 for p in posts_list if p.get("status") != "active")
    replies_cnt = sum(int(p.get("replies_da_gui") or 0) for p in posts_list)

    return {
        "last_scan_at": store.get("last_scan_at") or "",
        "interval_hours": 4,
        "summary": {
            "total": len(posts_list),
            "active": active_cnt,
            "good": good_cnt,
            "archived": archived_cnt,
            "total_replies": replies_cnt,
        },
        "posts": posts_list,
    }


def extract_person_from_comment(author_fb: str, text: str) -> tuple[str, str, str] | None:
    """Trích xuất (ho_ten, ngay_sinh, cau_hoi) từ nội dung bình luận. Nếu không có ngày sinh -> bỏ qua."""
    clean_txt = text or ""
    if author_fb:
        clean_txt = re.sub(
            r"^\s*" + re.escape(author_fb) + r"(?:\s*·\s*(?:\d+\s*(?:phút|giờ|ngày|tuần|giây)|Vừa xong|Theo dõi))*\s*",
            "",
            clean_txt,
            flags=re.I,
        )
    clean_txt = re.sub(r"(?:Thích\s*)?(?:Phản hồi|Trả lời)(?:\s*Gửi tin nhắn)?(?:\s*Chia sẻ)?(?:\s*\d+)?\s*$", "", clean_txt, flags=re.I).strip()

    m = DOB_REGEX.search(clean_txt)
    if not m:
        return None
    d, mo, y = m.group(1), m.group(2), m.group(3)
    if len(y) == 2:
        y = ("19" + y) if int(y) >= 40 else ("20" + y)
    dob_str = f"{int(d):02d}/{int(mo):02d}/{y}"

    before = (clean_txt[: m.start()] or "").strip(" ,.-:\n\t+👉1234567890️⃣")
    before = re.sub(r"^(mình tên là|em tên là|em là|họ và tên|họ tên|tên|cho mình xin|cho em xin|nhờ bạn xem giúp|xem giúp mình)\s*[:,-]?\s*", "", before, flags=re.I).strip()
    before = re.sub(r"[\s,.-]+(sinh ngày|ngày sinh dương lịch|ngày sinh|dương lịch|sn|ns|dob|sinh)\s*[:,-]?\s*$", "", before, flags=re.I).strip()
    words = [w for w in re.split(r"[\s,.;|\n]+", before) if w]
    after = (clean_txt[m.end() :] or "").strip(" ,.-:\n\t")

    if 2 <= len(words) <= 6 and all(not any(ch.isdigit() for ch in w) for w in words):
        ho_ten = " ".join(w[:1].upper() + w[1:].lower() for w in words)
    else:
        first_seg = re.split(r"[.!?\n,;]+|\b(?:xin xem|nhờ xem|xem giúp|mình muốn|mình đang|trăn trở|cho mình)\b", after, maxsplit=1, flags=re.I)[0].strip()
        seg_words = [w for w in first_seg.split() if w]
        if 2 <= len(seg_words) <= 5 and all(not any(ch.isdigit() for ch in w) for w in seg_words):
            ho_ten = " ".join(w[:1].upper() + w[1:].lower() for w in seg_words)
            after = after[len(first_seg) :].strip(" ,.-:\n\t")
        else:
            ho_ten = (author_fb or "Bạn Hữu Duyên").strip()

    cau_hoi = after[:220] if len(after) >= 5 else "Định hướng công việc, tài chính và vận niên 2026 - 2027"
    return ho_ten, dob_str, cau_hoi


def extract_tool_question_from_comment(author_fb: str, text: str) -> str | None:
    """Nhận diện bình luận hỏi thông tin công cụ 0đ / xin link / hỏi dịch vụ B2B trên các nhóm Công nghệ & Kinh doanh."""
    clean_txt = text or ""
    if author_fb:
        clean_txt = re.sub(
            r"^\s*" + re.escape(author_fb) + r"(?:\s*·\s*(?:\d+\s*(?:phút|giờ|ngày|tuần|giây)|Vừa xong|Theo dõi))*\s*",
            "",
            clean_txt,
            flags=re.I,
        )
    clean_txt = re.sub(r"(?:Thích\s*)?(?:Phản hồi|Trả lời)(?:\s*Gửi tin nhắn)?(?:\s*Chia sẻ)?(?:\s*\d+)?\s*$", "", clean_txt, flags=re.I).strip()
    if len(clean_txt) < 6 or re.search(r"https?://|zalo\.me|t\.me", clean_txt, re.I):
        return None
    if "?" in clean_txt or TOOL_QUESTION_REGEX.search(clean_txt):
        return clean_txt[:240]
    return None


def sanitize_zero_link_text(txt: str) -> str:
    out = re.sub(r"https?://\S+", "", txt or "")
    out = re.sub(r"\b[a-z0-9.-]+\.(?:vn|com|net|io|ai)\S*", "dòng địa chỉ màu vàng dưới chân ảnh", out, flags=re.I)
    out = re.sub(r"\bkiemtien\b", "dòng hướng dẫn dưới chân ảnh", out, flags=re.I)
    return out.replace("**", "").replace("__", "").strip()


def build_tool_b2b_reply_package(author_fb: str, question_txt: str) -> tuple[str, str]:
    """Tạo câu trả lời tư vấn ngắn gọn 0-link + đính kèm poster 9 công cụ 0đ cho bài đăng nhóm AI/Kinh doanh."""
    poster_path = os.path.join(BASE_DIR, "public", "mau-landing", "assets", "spotlight-free-9-tools.png")
    ai_ans = agent_worker.call_gemini(
        f"Viết phản hồi bình luận Facebook ngắn gọn (55-90 chữ), thân thiện, đúng trọng tâm cho bạn '{author_fb}' vừa hỏi: '{question_txt}'.\n"
        "- Thông tin thật: Toàn bộ 9 công cụ AI (Tự code Landing Page tải file HTML, Tạo CV chuẩn ATS xuất PDF, Lập lịch 30 ngày bán hàng Excel CSV, Thần số học + sổ tay 12 tháng A4, Chấm điểm Web...) đều mở MIỄN PHÍ 100% (0đ, không cần tạo tài khoản). Ngoài ra có gói Deta Studio B2B thiết kế Landing Page & Phễu bán hàng trọn gói trong 24h (từ 490K).\n"
        "- QUY TẮC SỐNG CÒN: TUYỆT ĐỐI KHÔNG viết bất kỳ đường link https:// hay tên miền .vn/.com nào trong chữ để không bị Admin Assist xóa bình luận. Hãy chỉ bạn ấy nhìn vào khung địa chỉ màu vàng ở góc dưới cùng tấm ảnh mình đính kèm ngay bên dưới.",
        "Kỹ sư Deta AI Lab nhiệt tình, chân thành, thực tế.",
    )
    body = sanitize_zero_link_text(ai_ans) if ai_ans else ""
    if len(body) < 35:
        body = (
            f"Chào {author_fb or 'bạn'} 👋 Hiện toàn bộ 9 công cụ AI (Tự code Landing Page xuất HTML sạch, Tạo CV chuẩn ATS xuất PDF, "
            f"Lịch 30 ngày bán hàng Excel CSV & Thần số học) đều mở miễn phí 100% (0đ, không cần đăng nhập), kèm mục đăng ký làm Web trọn gói 24h nếu bạn cần đội mình dựng giúp nhé. "
            f"Để không vướng bộ lọc link của nhóm, bạn gõ đúng dòng địa chỉ màu vàng in ở góc dưới tấm ảnh mình đính kèm ngay dưới đây là vào dùng được liền nha!"
        )
    return body, poster_path


def build_comment_reply_package(ho_ten: str, dob_str: str, cau_hoi: str) -> tuple[str, str]:
    """Tạo (reply_text_0_link, png_card_path) cá nhân hóa có kèm watermark kiemtien.deta.vn."""
    prof = ne.compute_numerology(ho_ten, dob_str, current_year=sa.now_vn().year)
    peaks = prof["dinh_cao"]
    peaks_txt = ", ".join(f"Đỉnh {p['dinh']} số {p['so']} ({p['tuoi']} tuổi - {p['nam']})" for p in peaks)
    manh = ", ".join(x["ten"] for x in prof["mui_ten_manh"]) or "Phân bổ linh hoạt đa trục"
    trong = ", ".join(x["ten"] for x in prof["mui_ten_trong"]) or "Không trống hoàn toàn trục nào"

    ai_text = agent_worker.call_gemini(
        f"Viết lời luận giải Thần số học Pythagoras ấm áp, sắc bén (khoảng 160-220 chữ, KHÔNG gắn link https://) trả lời bình luận Facebook cho:\n"
        f"- Họ tên: {prof['ho_ten']} ({prof['ngay_sinh']})\n"
        f"- Số Chủ đạo: {prof['so_chu_dao_nhan']} ({prof['danh_xung']}) | Sứ mệnh: {prof['su_menh']} | Linh hồn: {prof['linh_hon']} | Nhân cách: {prof['nhan_cach']}\n"
        f"- Năm cá nhân {prof['nam_hien_tai']}: Số {prof['nam_ca_nhan']} ({prof['thong_diep_nam']})\n"
        f"- Biểu đồ ngày sinh: Mạnh [{manh}], Cần bù [{trong}] | 4 Đỉnh cao: {peaks_txt}\n"
        f"- Mong muốn của bạn ấy: {cau_hoi}\n\n"
        "Dòng 1 bắt đầu bằng 'THÔNG ĐIỆP: ' (1 câu <25 từ để in lên ảnh Bản đồ). Sau đó chia 3 ý ngắn gọn dễ đọc trên Facebook: "
        "(1) Điểm mạnh cốt lõi Chủ đạo × Sứ mệnh × Linh hồn, (2) Hóa giải trục trống & Lời khuyên thẳng vào câu hỏi trong Năm cá nhân hiện tại, (3) Cột mốc Đỉnh cao gần nhất.",
        "Chuyên gia Thần số học thực tế, truyền cảm hứng tích cực.",
    )
    core_msg = prof["thong_diep_nam"]
    body_reading = ""
    if ai_text:
        m_c = re.search(r"THÔNG ĐIỆP:\s*(.+)", ai_text)
        if m_c:
            core_msg = m_c.group(1).strip().strip('"“”*')
            body_reading = re.sub(r"^.*THÔNG ĐIỆP:.*\n*", "", ai_text).strip()
        else:
            body_reading = ai_text.strip()

    if not body_reading:
        body_reading = (
            f"✨ Tổ hợp cốt lõi: Bạn mang Số Chủ đạo {prof['so_chu_dao_nhan']} ({prof['danh_xung']}), Sứ mệnh {prof['su_menh']}, Linh hồn {prof['linh_hon']}, Nhân cách {prof['nhan_cach']}.\n"
            f"📊 Biểu đồ & Đỉnh cao: Thế mạnh [{manh}], cần lưu ý rèn thêm [{trong}]. Lộ trình 4 đỉnh: {peaks_txt}.\n"
            f"🧭 Định hướng {prof['nam_hien_tai']}: {prof['thong_diep_nam']}"
        )

    svg = ne.build_numerology_svg(prof, core_advice=core_msg)
    slug = hashlib.md5(f"{ho_ten}|{dob_str}".encode("utf-8")).hexdigest()[:10]
    png_path = f"/tmp/tsh-card-{slug}.png"
    ne.render_svg_to_png(svg, png_path)

    body_reading = sanitize_zero_link_text(body_reading)

    final_reply = (
        f"🔮 Gửi tặng {prof['ho_ten']} ({prof['ngay_sinh']}) Bản đồ Thần Số Học đầy đủ nhé!\n"
        f"• Chủ đạo: {prof['so_chu_dao_nhan']} ({prof['danh_xung']}) | Sứ mệnh: {prof['su_menh']} | Linh hồn: {prof['linh_hon']} | Nhân cách: {prof['nhan_cach']} | Năm cá nhân {prof['nam_hien_tai']}: Số {prof['nam_ca_nhan']}\n\n"
        f"{body_reading}\n\n"
        f"📌 Mình đính kèm tấm Thẻ Bản Đồ Kim Tự Tháp 4 Đỉnh Cao nét cao của riêng bạn ngay bên dưới (bạn muốn xem bản chi tiết dài 5 phần & sổ tay lộ trình 12 tháng A4 miễn phí 100% thì xem dòng hướng dẫn dưới chân tấm ảnh nhé ❤️)"
    )
    return final_reply, png_path


def extract_my_posted_urls_on_page(cdp, sid, max_posts: int = 3) -> list[str]:
    """Lấy danh sách URL bài đã được duyệt bên trong [role="main"] của trang /my_posted_content (loại bỏ tuyệt đối link thông báo ref=notif)."""
    return (
        sa.eval_js(
            cdp,
            sid,
            f"""(() => {{
                const mainEl = document.querySelector('[role="main"]') || document.body;
                const grpSeg = ((location.pathname.split('/groups/')[1] || '').split('/')[0] || '').toLowerCase();
                const byId = new Map();
                const photoLinks = Array.from(mainEl.querySelectorAll('a[href*="/photo/"][href*="set=gm."]'));
                for (const a of photoLinks) {{
                    const href = a.href || '';
                    if (href.includes('notif_id=') || href.includes('ref=notif')) continue;
                    const m = href.match(/^(https:\\/\\/www\\.facebook\\.com\\/photo\\/\\?fbid=\\d+&set=gm\\.(\\d+)(?:&idorvanity=\\d+)?)/);
                    if (m && !byId.has(m[2])) byId.set(m[2], m[1]);
                }}
                const links = Array.from(mainEl.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"]'));
                for (const a of links) {{
                    const href = a.href || '';
                    if (!href || href.includes('comment_id') || href.includes('notif_id=') || href.includes('ref=notif') || href.includes('notif_t=') || href.includes('pending') || href.includes('declined')) continue;
                    if (grpSeg && !href.toLowerCase().includes('/groups/' + grpSeg + '/')) continue;
                    const clean = href.split('&__cft__')[0].split('?__cft__')[0];
                    const m = clean.match(/(?:permalink\\/|posts\\/)(\\d+)/);
                    if (m && !byId.has(m[1])) byId.set(m[1], clean);
                }}
                return Array.from(byId.values()).slice(0, {int(max_posts)});
            }})()""",
        )
        or []
    )


def harvest_untracked_group_posts(cdp, sid, store: dict, glog: dict) -> int:
    """
    Thu hoạch URL bài viết thật từ `/my_posted_content` của các nhóm đã đăng nhưng chưa có trong `tracked_posts.json`
    (hoặc nhóm mới đăng bài mới / đang chờ Admin duyệt trong vòng 48h).
    """
    harvested = store.setdefault("groups_harvested", {})
    posts = store.setdefault("posts", {})
    now_dt = sa.now_vn()
    added = 0

    for g_key, g_info in glog.items():
        g_url = (g_info.get("url") or "").strip()
        posted_at = (g_info.get("posted_at") or "").strip()
        if not g_url:
            continue
        has_posts_for_group = any(p.get("group_key") == g_key for p in posts.values())
        last_harv = harvested.get(g_key, "")

        # Cần vào /my_posted_content nếu:
        # 1. Nhóm này mới đăng bài mới sau lần thu hoạch trước (`posted_at > last_harv`), HOẶC
        # 2. Nhóm đăng trong vòng 48h gần đây nhưng lúc trước bài còn chờ duyệt nên chưa thu hoạch được URL nào
        posted_dt = parse_iso_vn(posted_at) or now_dt
        age_h = max(0.0, (now_dt - posted_dt).total_seconds() / 3600.0)
        needs_harvest = (posted_at > last_harv) or (not has_posts_for_group and last_harv != "expired_no_post" and age_h <= 72.0)
        if not needs_harvest and has_posts_for_group:
            continue
        if not needs_harvest and not has_posts_for_group and last_harv:
            continue

        my_posts_url = g_url.rstrip("/") + "/my_posted_content"
        cdp.call("Page.navigate", {"url": my_posts_url}, session_id=sid)
        time.sleep(5.2)

        urls = extract_my_posted_urls_on_page(cdp, sid, max_posts=3)
        group_added = 0
        if urls:
            for u in urls:
                pid = extract_post_id(u)
                existed = pid in posts
                entry = register_or_update_post(store, u, g_key, g_info.get("name") or g_key, g_url, posted_at=posted_at if not existed else "")
                if entry.get("last_checked_at"):
                    evaluate_post_lifecycle(entry, now_dt)
                if not existed:
                    added += 1
                    group_added += 1
            if group_added > 0 or not has_posts_for_group or age_h >= NO_INTERACTION_EXPIRE_HOURS:
                harvested[g_key] = posted_at or now_dt.isoformat(timespec="seconds")
        else:
            # Nếu đã quá 48h mà vẫn không có bài được duyệt trên /my_posted_content -> đánh dấu hết hạn để không quét lại mãi
            if age_h >= NO_INTERACTION_EXPIRE_HOURS:
                harvested[g_key] = "expired_no_post"

    return added


def switch_comment_filter_to_all(cdp, sid) -> bool:
    """Chuyển bộ lọc bình luận từ 'Phù hợp nhất' sang 'Tất cả bình luận' (SKILL.md mục 3.2)."""
    pos_filter = sa.eval_js(
        cdp,
        sid,
        """(() => {
            const els = Array.from(document.querySelectorAll('[role="button"], span'));
            for (const el of els) {
                const t = (el.innerText || '').trim();
                if (/^(Phù hợp nhất|Bình luận liên quan nhất|Most relevant)$/i.test(t)) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 30 && r.height > 10 && r.top > 40) {
                        el.scrollIntoView({block: 'center'});
                        const r2 = el.getBoundingClientRect();
                        return {x: r2.left + r2.width / 2, y: r2.top + r2.height / 2};
                    }
                }
            }
            return null;
        })()""",
    )
    if not pos_filter:
        return False
    sa.cdp_click_coords(cdp, sid, pos_filter["x"], pos_filter["y"])
    time.sleep(1.2)
    picked = sa.eval_js(
        cdp,
        sid,
        """(() => {
            const items = Array.from(document.querySelectorAll('[role="menuitem"], [role="menuitemradio"], [role="option"], span'));
            for (const it of items) {
                const t = (it.innerText || '').trim();
                if (/^(Tất cả bình luận|All comments)/i.test(t)) {
                    const r = it.getBoundingClientRect();
                    if (r.width > 30 && r.height > 10) {
                        it.click();
                        return {x: r.left + r.width / 2, y: r.top + r.height / 2};
                    }
                }
            }
            return null;
        })()""",
    )
    if picked:
        sa.cdp_click_coords(cdp, sid, picked["x"], picked["y"])
        time.sleep(2.0)
        return True
    return False


def send_inline_reply_with_image(cdp, sid, post_url: str, author_name: str, reply_msg: str, png_path: str) -> bool:
    """Cuộn tới bình luận của `author_name`, đính kèm ảnh PNG có watermark và gửi phản hồi 0-link."""
    pos_reply = sa.eval_js(
        cdp,
        sid,
        f"""(() => {{
            const arts = Array.from(document.querySelectorAll('[role="article"]')).filter(a => a.getBoundingClientRect().width > 50);
            for (const art of arts) {{
                const aria = art.getAttribute('aria-label') || '';
                if (!/^(Bình luận dưới tên|Comment by)/i.test(aria)) continue;
                if (!aria.toLowerCase().includes({json.dumps(author_name.lower())})) continue;
                art.scrollIntoView({{block: 'center'}});
                const btns = Array.from(art.querySelectorAll('[role="button"], span'));
                for (const b of btns) {{
                    if (/^(Phản hồi|Trả lời|Reply)$/i.test((b.textContent || '').trim()) && b.children.length <= 2) {{
                        const r = b.getBoundingClientRect();
                        if (r.width > 6 && r.height > 6) return {{x: r.left + r.width/2, y: r.top + r.height/2}};
                    }}
                }}
            }}
            return null;
        }})()""",
    )
    if not pos_reply:
        return False
    sa.cdp_click_coords(cdp, sid, pos_reply["x"], pos_reply["y"])
    time.sleep(1.8)

    reply_box_pos = sa.eval_js(
        cdp,
        sid,
        f"""(() => {{
            document.querySelectorAll('[data-deta-active-reply]').forEach(el => el.removeAttribute('data-deta-active-reply'));
            document.querySelectorAll('[data-deta-reply-file]').forEach(el => el.removeAttribute('data-deta-reply-file'));
            const arts = Array.from(document.querySelectorAll('[role="article"]')).filter(a => a.getBoundingClientRect().width > 50);
            const target = arts.find(a => /^(Bình luận dưới tên|Comment by)/i.test(a.getAttribute('aria-label') || '') && (a.getAttribute('aria-label') || '').toLowerCase().includes({json.dumps(author_name.lower())}));
            const targetBottom = target ? target.getBoundingClientRect().bottom : 0;
            const boxes = Array.from(document.querySelectorAll('[contenteditable="true"][role="textbox"]')).filter(b => {{
                const aria = ((b.getAttribute('aria-label') || '') + ' ' + (b.getAttribute('aria-placeholder') || '')).toLowerCase();
                return b.getBoundingClientRect().width > 30 && /phản hồi|trả lời|reply/i.test(aria);
            }});
            if (!boxes.length) return null;
            boxes.sort((a, b) => Math.abs(a.getBoundingClientRect().top - targetBottom) - Math.abs(b.getBoundingClientRect().top - targetBottom));
            const b = boxes[0];
            b.setAttribute('data-deta-active-reply', '1');
            let cur = b;
            for (let d = 0; d < 10 && cur && cur !== document.body; d++, cur = cur.parentElement) {{
                const inp = cur.querySelector('input[type="file"]');
                if (inp) {{ inp.setAttribute('data-deta-reply-file', '1'); break; }}
            }}
            const r = b.getBoundingClientRect();
            return {{x: r.left + Math.max(30, r.width - 20), y: r.top + r.height / 2}};
        }})()""",
    )
    if not reply_box_pos:
        return False

    if png_path and os.path.exists(png_path):
        doc_root = cdp.call("DOM.getDocument", {"depth": -1}, session_id=sid)["root"]["nodeId"]
        f_nodes = cdp.call("DOM.querySelectorAll", {"nodeId": doc_root, "selector": 'input[type="file"][data-deta-reply-file="1"]'}, session_id=sid).get("nodeIds", [])
        if f_nodes:
            try:
                cdp.call("DOM.setFileInputFiles", {"files": [png_path], "nodeId": f_nodes[0]}, session_id=sid)
                time.sleep(6.5)
            except Exception:
                pass

    refocus = sa.eval_js(
        cdp,
        sid,
        """(() => {
            const b = document.querySelector('[data-deta-active-reply="1"]');
            if (!b) return null;
            b.scrollIntoView({block: 'center'});
            b.focus();
            const r = b.getBoundingClientRect();
            return {x: r.left + Math.max(30, r.width - 20), y: r.top + r.height / 2};
        })()""",
    )
    if refocus:
        sa.cdp_click_coords(cdp, sid, refocus["x"], refocus["y"])
        time.sleep(0.3)
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "End", "code": "End", "windowsVirtualKeyCode": 35, "nativeVirtualKeyCode": 35}, session_id=sid)
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "End", "code": "End", "windowsVirtualKeyCode": 35, "nativeVirtualKeyCode": 35}, session_id=sid)
    time.sleep(0.15)
    cdp.call("Input.insertText", {"text": " "}, session_id=sid)

    lines = reply_msg.split("\n")
    for i_ln, ln in enumerate(lines):
        if ln:
            cdp.call("Input.insertText", {"text": ln}, session_id=sid)
        if i_ln < len(lines) - 1:
            cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "modifiers": 8, "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13}, session_id=sid)
            cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "modifiers": 8, "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13}, session_id=sid)
        time.sleep(0.05)
    time.sleep(1.5)
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13, "text": "\r"}, session_id=sid)
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13}, session_id=sid)
    time.sleep(12.5)
    return True


def scan_tracked_posts_and_reply(max_replies_per_run: int = 15) -> dict:
    """
    Quét định kỳ 4h/lần trên danh sách bài viết đang theo dõi (`data/tracked_posts.json`):
    1. Thu hoạch bài mới đã duyệt từ các Group vừa đăng.
    2. Ưu tiên kiểm tra `⭐ Bài tốt` trước, sau đó tới các bài `🟢 Đang theo dõi`.
    3. Đo tương tác thật (cảm xúc + bình luận khách), gắn sao `⭐ Bài tốt`, trả lời bình luận mới kèm ảnh 0-link.
    4. Tự động loại bài không có tương tác sau 2-3 ngày (`48h` nếu 0 tương tác, `72h` sau tương tác cuối) khỏi danh sách theo dõi.
    """
    glog = {}
    if os.path.exists(sa.GROUP_LOG_PATH):
        try:
            with open(sa.GROUP_LOG_PATH, "r", encoding="utf-8") as f:
                glog = json.load(f)
        except Exception:
            pass

    store = load_tracked_store()
    replied_db = load_replied()
    replied_count = 0
    newly_archived = []
    good_marked = []

    sa.ensure_bot_browser(headless=False, open_login_tabs=False)
    with urllib.request.urlopen(f"http://127.0.0.1:{sa.BOT_CDP_PORT}/json/version", timeout=3) as resp:
        info = json.loads(resp.read().decode("utf-8"))
        ws_path = "/" + info["webSocketDebuggerUrl"].split("://", 1)[1].split("/", 1)[1]

    cdp = sa.SimpleCDPClient("127.0.0.1", sa.BOT_CDP_PORT, ws_path, timeout=60.0)
    tid = None
    sid = None
    try:
        tid = cdp.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        sid = cdp.call("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        cdp.call("Page.enable", {}, session_id=sid)
        cdp.call("Runtime.enable", {}, session_id=sid)
        cdp.call("DOM.enable", {}, session_id=sid)
        cdp.call("Page.bringToFront", {}, session_id=sid)
        try:
            cdp.call("Page.setInterceptFileChooserDialog", {"enabled": True}, session_id=sid)
        except Exception:
            pass

        # Bước A: Thu hoạch URL bài mới từ các nhóm chưa có trong danh sách theo dõi
        harvested_new = harvest_untracked_group_posts(cdp, sid, store, glog)
        save_tracked_store(store)

        # Bước B: Lọc danh sách bài đang active, ưu tiên ⭐ Bài tốt & Ghim kiểm tra trước
        now_dt = sa.now_vn()
        active_entries = []
        for entry in (store.get("posts") or {}).values():
            if entry.get("status") != "active":
                continue
            # Kiểm tra hạn trước khi mở trang nếu đã từng được quét ít nhất 1 lần
            if entry.get("last_checked_at"):
                evaluate_post_lifecycle(entry, now_dt)
                if entry.get("status") != "active":
                    newly_archived.append(f"{entry.get('group_name')} ({entry.get('post_id')})")
                    continue
            active_entries.append(entry)

        active_entries.sort(
            key=lambda e: (
                0 if (e.get("pinned") or e.get("is_good")) else 1,
                -(parse_iso_vn(e.get("posted_at") or "") or now_dt).timestamp(),
            )
        )

        checked_posts = 0
        for entry in active_entries:
            post_url = entry["post_url"]
            post_key = entry["post_id"]
            was_first_check = not bool(entry.get("last_checked_at"))
            was_good_before = bool(entry.get("is_good"))

            cdp.call("Page.navigate", {"url": post_url}, session_id=sid)
            time.sleep(5.2)
            checked_posts += 1

            # Kiểm tra bài viết còn tồn tại không
            unavailable = bool(
                sa.eval_js(
                    cdp,
                    sid,
                    """(() => /Bạn hiện không xem được nội dung này|This content isn't available right now/i.test(document.body ? document.body.innerText : ''))()""",
                )
            )
            if unavailable:
                if not entry.get("pinned"):
                    entry["status"] = "archived"
                    entry["ly_do_ngung"] = "Bài viết không còn hiển thị trên nhóm"
                    newly_archived.append(f"{entry.get('group_name')} ({post_key})")
                entry["last_checked_at"] = sa.now_vn().isoformat(timespec="seconds")
                save_tracked_store(store)
                continue

            # Chuyển sang "Tất cả bình luận" để không sót bình luận mới
            switch_comment_filter_to_all(cdp, sid)

            # Đo cảm xúc & thu thập danh sách bình luận thật của khách
            page_data = sa.eval_js(
                cdp,
                sid,
                """(() => {
                    let reactions = 0;
                    const rxEls = Array.from(document.querySelectorAll('[aria-label*="cảm xúc"], [aria-label*="Thích:"], [aria-label*="reactions"], span'));
                    for (const el of rxEls) {
                        const aria = (el.getAttribute('aria-label') || '').trim();
                        const m = aria.match(/(\\d+[.,]?\\d*)\\s*(?:lượt bày tỏ cảm xúc|người|reactions)/i);
                        if (m) {
                            reactions = Math.max(reactions, parseInt(m[1].replace(/[.,]/g, ''), 10) || 0);
                        }
                    }
                    const arts = Array.from(document.querySelectorAll('[role="article"]'));
                    const out = [];
                    const seenAuthors = new Set();
                    let myRepliesDom = 0;
                    arts.forEach((art, idx) => {
                        if (art.getBoundingClientRect().width < 50) return;
                        const aria = art.getAttribute('aria-label') || '';
                        if (/Dương Birken/i.test(aria)) { myRepliesDom += 1; return; }
                        if (!/^(Bình luận dưới tên|Comment by|Phản hồi dưới tên|Reply by)/i.test(aria)) return;
                        const author = aria.replace(/^(Bình luận dưới tên|Comment by|Phản hồi dưới tên|Reply by)\\s+/i, '').split(/\\s+vào\\s+|\\s+lúc\\s+|\\s+\\d+\\s+/)[0].trim();
                        if (!author || /Dương Birken/i.test(author)) return;
                        seenAuthors.add(author.toLowerCase());
                        const txt = (art.innerText || '').trim();
                        const btns = Array.from(art.querySelectorAll('[role="button"], span'));
                        let hasReply = false;
                        for (const b of btns) {
                            if (/^(Phản hồi|Trả lời|Reply)$/i.test((b.textContent || '').trim())) { hasReply = true; break; }
                        }
                        if (hasReply && txt.length >= 6) out.push({idx, author, text: txt.slice(0, 450)});
                    });
                    return {reactions, uniqueCommenters: seenAuthors.size, myRepliesDom, comments: out};
                })()""",
            ) or {"reactions": 0, "uniqueCommenters": 0, "myRepliesDom": 0, "comments": []}

            prev_c = int(entry.get("comments_khach") or 0)
            prev_r = int(entry.get("reactions") or 0)
            new_c = max(prev_c, int(page_data.get("uniqueCommenters") or 0), len(page_data.get("comments") or []))
            new_r = max(prev_r, int(page_data.get("reactions") or 0))

            now_iso = sa.now_vn().isoformat(timespec="seconds")
            entry["comments_khach"] = new_c
            entry["reactions"] = new_r
            entry["replies_da_gui"] = max(int(entry.get("replies_da_gui") or 0), int(page_data.get("myRepliesDom") or 0))
            entry["last_checked_at"] = now_iso

            # Cập nhật thời điểm tương tác gần nhất khi phát hiện bình luận mới hoặc cảm xúc tăng thêm
            if not was_first_check and (new_c > prev_c or new_r > prev_r):
                entry["last_interaction_at"] = now_iso
            elif was_first_check and (new_c > prev_c):
                # Lần đầu đưa bài cũ vào sổ: nếu có bình luận mới chưa trả lời -> coi như vừa tương tác để trả lời & giữ theo dõi
                entry["last_interaction_at"] = now_iso

            # Trả lời bình luận mới trên bài viết
            comments = page_data.get("comments") or []
            for cm in comments:
                if replied_count >= max_replies_per_run:
                    break
                cid = hashlib.sha1(f"{post_key}|{cm['author']}".encode("utf-8")).hexdigest()[:16]
                cid_legacy = hashlib.sha1(f"{post_url}|{cm['author']}|{cm['text'][:120]}".encode("utf-8")).hexdigest()[:16]
                if cid in replied_db or cid_legacy in replied_db:
                    continue

                reply_msg, png_path, log_meta = "", "", {}
                if entry.get("loai") == "than-so-hoc":
                    parsed = extract_person_from_comment(cm["author"], cm["text"])
                    if not parsed:
                        continue
                    ho_ten, dob_str, cau_hoi = parsed
                    reply_msg, png_path = build_comment_reply_package(ho_ten, dob_str, cau_hoi)
                    log_meta = {"ho_ten": ho_ten, "ngay_sinh": dob_str, "author_fb": cm["author"]}
                else:
                    q_txt = extract_tool_question_from_comment(cm["author"], cm["text"])
                    if not q_txt:
                        continue
                    reply_msg, png_path = build_tool_b2b_reply_package(cm["author"], q_txt)
                    log_meta = {"author_fb": cm["author"], "cau_hoi_b2b": q_txt}

                sent_ok = send_inline_reply_with_image(cdp, sid, post_url, cm["author"], reply_msg, png_path)
                if not sent_ok:
                    continue

                rep_iso = sa.now_vn().isoformat(timespec="seconds")
                replied_db[cid] = {
                    **log_meta,
                    "post_url": post_url,
                    "luc": rep_iso,
                }
                save_replied(replied_db)
                replied_count += 1
                entry["replies_da_gui"] = int(entry.get("replies_da_gui") or 0) + 1
                entry["last_interaction_at"] = rep_iso
                save_tracked_store(store)

                # Tải lại trang để đóng khung reply inline cũ trước khi sang bình luận kế tiếp
                cdp.call("Page.navigate", {"url": post_url}, session_id=sid)
                time.sleep(5.0)
                switch_comment_filter_to_all(cdp, sid)

            # Đánh giá lại nhãn ⭐ Bài tốt & quy tắc bỏ theo dõi sau 2-3 ngày không tương tác
            evaluate_post_lifecycle(entry, sa.now_vn())
            if entry.get("is_good") and not was_good_before:
                good_marked.append(f"{entry.get('group_name')} ({post_key})")
            if entry.get("status") != "active":
                newly_archived.append(f"{entry.get('group_name')} ({post_key})")
            save_tracked_store(store)

        store["last_scan_at"] = sa.now_vn().isoformat(timespec="seconds")
        save_tracked_store(store)

        if replied_count > 0:
            sa.record_diary_entry(
                f"Trực bình luận định kỳ (4h/lần): Đã kiểm tra {checked_posts} bài đang theo dõi và gửi {replied_count} phản hồi kèm ảnh (0-link)."
            )

        summary = get_tracked_posts_for_admin()["summary"]
        return {
            "ok": True,
            "harvested_new_posts": harvested_new,
            "checked_posts": checked_posts,
            "replied": replied_count,
            "good_marked": good_marked,
            "newly_archived": newly_archived,
            "watchlist_summary": summary,
        }
    finally:
        try:
            if sid:
                cdp.call("Page.setInterceptFileChooserDialog", {"enabled": False}, session_id=sid)
        except Exception:
            pass
        try:
            if tid:
                cdp.call("Target.closeTarget", {"targetId": tid})
        except Exception:
            pass
        cdp.close()


# Giữ tên hàm tương thích ngược với các script gọi cũ
def scan_and_reply_my_tsh_posts(max_replies_per_run: int = 15) -> dict:
    return scan_tracked_posts_and_reply(max_replies_per_run=max_replies_per_run)


DAILY_CYCLE_LOG_PATH = os.path.join(BASE_DIR, "data", "tsh_daily_cycle_log.json")

# Kho 12 chủ đề & hồ sơ mẫu xoay vòng mỗi ngày (mỗi ngày 1 nhân vật mới, 1 bảng màu mới, 1 góc luận giải sâu mới)
DAILY_TSH_TOPICS = [
    ("Trần Ngọc Minh Châu", "14/08/1995", "Góc khuất giữa Số Chủ Đạo và Chỉ Số Linh Hồn: Vì sao nhiều người làm lương cao vẫn thấy trống rỗng?", 1),
    ("Lê Hoàng Gia Bảo", "22/11/1992", "Giải mã tần số Master 11/2 & 22/4: Áp lực tâm thức lớn đi kèm sứ mệnh kiến tạo như thế nào?", 2),
    ("Phạm Thuỳ Linh", "06/03/1997", "Cách đọc Chu kỳ 9 Năm Cá Nhân 2026–2027 để chọn đúng thời điểm nhảy việc hoặc mở kinh doanh riêng", 3),
    ("Nguyễn Đức Thịnh", "19/05/1991", "Hóa giải trục trống 4-5-6 (Mũi tên Uất hận / Ý chí) trên Biểu đồ ngày sinh bằng thói quen thực tế", 4),
    ("Vũ Hà Phương", "28/09/1998", "Bí mật 4 Đỉnh Cao Kim Tự Tháp đời người: Nhận diện cột mốc chuyển mình tuổi 27–36", 0),
    ("Đặng Quốc Khánh", "09/12/1990", "Sự xung đột hay bổ trợ giữa Số Nhân Cách (vỏ bọc bên ngoài) và Số Linh Hồn (khao khát thật bên trong)", 1),
    ("Hoàng Mai Anh", "17/04/1996", "Người mang Năm Cá Nhân số 4 & số 7 trong năm 2026 cần tránh sai lầm tài chính nào?", 2),
    ("Bùi Tuấn Kiệt", "25/07/1993", "Vì sao 2 người cùng Số Chủ Đạo nhưng đường đời và tài vận khác hẳn nhau? Vai trò của Chỉ số Sứ mệnh từ Họ tên", 3),
    ("Ngô Thanh Trúc", "03/10/1999", "Độ chín của Chỉ số Trưởng Thành sau tuổi 35: Khi Số Chủ Đạo và Sứ Mệnh hợp nhất", 4),
    ("Đỗ Minh Quân", "11/01/1994", "Cách phát huy trục Trí tuệ (3-6-9) và trục Thực tế (1-4-7) trong công việc & quản lý dòng tiền", 0),
    ("Phan Khánh Vy", "30/06/2000", "Định hướng nghề nghiệp chuẩn xác từ tam giác vàng: Chủ đạo × Sứ mệnh × Linh hồn", 1),
    ("Trịnh Hải Nam", "08/02/1989", "Năm cá nhân số 8 & số 9 giai đoạn 2026–2027: Khi nào nên bung sức gặt hái, khi nào nên thanh lọc buông bỏ?", 2),
]


def load_daily_cycle_log() -> dict:
    if os.path.exists(DAILY_CYCLE_LOG_PATH):
        try:
            with open(DAILY_CYCLE_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_daily_cycle_log(data: dict) -> None:
    os.makedirs(os.path.dirname(DAILY_CYCLE_LOG_PATH), exist_ok=True)
    with open(DAILY_CYCLE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pick_next_tsh_group() -> str:
    """Chọn 1 nhóm Thần Số Học ưu tiên chưa đăng bao giờ hoặc đăng cách đây lâu nhất (xoay vòng 4 ngày/nhóm)."""
    tsh_keys = [k for k in sa.GROUP_CAMPAIGNS if k.startswith("tsh-")]
    glog = {}
    if os.path.exists(sa.GROUP_LOG_PATH):
        try:
            with open(sa.GROUP_LOG_PATH, "r", encoding="utf-8") as f:
                glog = json.load(f)
        except Exception:
            pass
    never_posted = [k for k in tsh_keys if k not in glog or not glog[k].get("posted_at")]
    if never_posted:
        return never_posted[0]
    tsh_keys.sort(key=lambda k: glog.get(k, {}).get("posted_at", ""))
    return tsh_keys[0]


def build_fresh_daily_post_and_image(seed_idx: int, group_key: str) -> tuple[str, str, dict]:
    """Sinh 1 tấm ảnh Bản đồ mẫu mới tinh (nhân vật mới + màu mới) VÀ 1 bài viết chia sẻ Thần Số Học mới hoàn toàn (0 link)."""
    sample_name, sample_dob, topic_angle, theme_idx = DAILY_TSH_TOPICS[seed_idx % len(DAILY_TSH_TOPICS)]
    prof = ne.compute_numerology(sample_name, sample_dob, current_year=sa.now_vn().year)
    svg = ne.build_numerology_svg(prof, core_advice=prof["thong_diep_nam"], theme_idx=theme_idx)

    today_str = sa.now_vn().strftime("%Y-%m-%d")
    out_png = os.path.join(BASE_DIR, "public", "mau-landing", "assets", f"tsh-daily-{today_str}-{group_key}.png")
    ne.render_svg_to_png(svg, out_png)

    prompt = (
        f"Viết 1 bài đăng chia sẻ sâu sắc & tặng Bản đồ Thần Số Học miễn phí 100% trên Group Facebook Thần Số Học (khoảng 180-240 chữ).\n"
        f"- Chủ đề chuyên môn mới hôm nay: '{topic_angle}'.\n"
        f"- Lấy ví dụ minh họa ngắn gọn ngay từ tấm ảnh Bản đồ mẫu đính kèm bên dưới của bạn '{prof['ho_ten']}' ({prof['ngay_sinh']}): "
        f"Số Chủ Đạo {prof['so_chu_dao_nhan']} ({prof['danh_xung']}), Sứ mệnh {prof['su_menh']}, Linh hồn {prof['linh_hon']}, Năm cá nhân {prof['nam_hien_tai']} là Số {prof['nam_ca_nhan']}.\n"
        f"- QUY TẮC TUYỆT ĐỐI: KHÔNG chứa bất kỳ đường link https:// hay tên miền dạng .vn/.com nào trong bài chữ để không bị Facebook bóp tương tác.\n"
        f"- Cuối bài mời thành viên để lại bình luận [Họ tên khai sinh đầy đủ + Ngày tháng năm sinh dương lịch + Điều đang trăn trở nhất] để mình gửi tặng tấm ảnh Bản đồ Kim Tự Tháp cá nhân hóa kèm bài luận 5 phần miễn phí; đồng thời nhắn nhẹ ai ngại để ngày sinh công khai có thể tự tra riêng tư & tải sổ tay 12 tháng A4 miễn phí 100% theo dòng hướng dẫn dưới chân tấm ảnh mẫu bên dưới."
    )
    ai_post = agent_worker.call_gemini(prompt, "Chuyên gia Thần số học Pythagoras ấm áp, sâu sắc, thực tế.")
    clean_post = sanitize_zero_link_text(ai_post) if ai_post else ""

    if len(clean_post) < 120:
        clean_post = (
            f"🔮 Góc chia sẻ hôm nay: {topic_angle}\n\n"
            f"Như trên tấm Bản đồ mẫu bên dưới của bạn {prof['ho_ten']} ({prof['ngay_sinh']}), khi ghép đồng thời "
            f"Số Chủ Đạo {prof['so_chu_dao_nhan']} ({prof['danh_xung']}) với Sứ mệnh {prof['su_menh']}, Linh hồn {prof['linh_hon']} "
            f"và Năm cá nhân {prof['nam_hien_tai']} (Số {prof['nam_ca_nhan']}), hướng đi công việc và cách bù đắp trục trống hiện ra rõ ràng hơn rất nhiều so với chỉ xem lẻ 1 con số.\n\n"
            f"Hôm nay mình tiếp tục mở tặng MIỄN PHÍ 100% trọn bộ tấm thẻ Bản Đồ Kim Tự Tháp 4 Đỉnh Cao + Bài luận 5 phần & Sổ tay 12 tháng A4 cho cả nhà mình. Bạn nào muốn nhận bản riêng chỉ cần bình luận bên dưới:\n"
            f"👉 Họ tên khai sinh đầy đủ (có dấu) + Ngày tháng năm sinh dương lịch + Vấn đề bạn đang phân vân nhất năm nay\n\n"
            f"Mình sẽ lập và trả ảnh Bản đồ đầy đủ dưới bình luận cho từng bạn! (Ai ngại để thông tin cá nhân công khai trên nhóm thì có thể tự tra cứu riêng tư miễn phí 100% theo dòng hướng dẫn ở chân tấm ảnh mẫu bên dưới nhé ạ ❤️)"
        )

    meta = {
        "topic": topic_angle,
        "sample_name": prof["ho_ten"],
        "sample_dob": prof["ngay_sinh"],
        "life_path": prof["so_chu_dao_nhan"],
        "theme_idx": theme_idx,
        "image": out_png,
    }
    return clean_post, out_png, meta


def run_daily_tsh_cycle(reply_only: bool = False, preview_only: bool = False, force_post: bool = False) -> dict:
    """
    Chu trình định kỳ 4h/lần (`02:00 · 06:00 · 10:00 · 14:00 · 18:00 · 22:00`):
    1. Mọi khung 4h: Kiểm tra danh sách bài viết đang theo dõi (`tracked_posts.json`), ưu tiên ⭐ Bài tốt,
       trả lời bình luận mới và loại bỏ các bài không có tương tác sau 2-3 ngày.
    2. Khung >= 10:00 sáng (đúng 1 lần/ngày): Sinh 1 bài viết Thần Số Học mới + ảnh mới đăng lên 1 nhóm xoay vòng.
    """
    now_dt = sa.now_vn()
    today_str = now_dt.strftime("%Y-%m-%d")
    cycle_log = load_daily_cycle_log()
    day_seed = (now_dt.date() - sa.datetime.date(2026, 10, 29)).days + len(cycle_log)

    if preview_only:
        g_key = pick_next_tsh_group()
        msg, img_p, meta = build_fresh_daily_post_and_image(day_seed, g_key)
        return {"ok": True, "che_do": "xem_truoc_bai_moi", "group_key": g_key, "meta": meta, "noi_dung_moi": msg}

    # Bước 1 (Chạy mỗi 4 giờ): Kiểm tra danh sách bài theo dõi & trả lời bình luận
    reply_res = scan_tracked_posts_and_reply(max_replies_per_run=15)
    if reply_only:
        return {"ok": True, "buoc_1_check_binh_luan": reply_res, "buoc_2_dang_bai_moi": "bo_qua_do_reply_only"}

    # Bước 2 (Đúng 1 lần/ngày từ khung 10:00 sáng): Đăng 1 bài Thần Số Học mới xoay vòng nhóm
    if not force_post:
        if today_str in cycle_log:
            return {
                "ok": True,
                "buoc_1_check_binh_luan": reply_res,
                "buoc_2_dang_bai_moi": {"trang_thai": "da_dang_bai_moi_hom_nay", "chi_tiet": cycle_log[today_str]},
            }
        if now_dt.hour < 10:
            return {
                "ok": True,
                "buoc_1_check_binh_luan": reply_res,
                "buoc_2_dang_bai_moi": {"trang_thai": "cho_khung_10h_sang", "gio_hien_tai": now_dt.hour},
            }

    g_key = pick_next_tsh_group()
    fresh_msg, fresh_img, meta = build_fresh_daily_post_and_image(day_seed, g_key)
    post_res = sa.post_group_safe_with_image(
        g_key,
        publish=True,
        custom_message=fresh_msg,
        custom_image=fresh_img,
    )
    if post_res.get("ok"):
        cycle_log[today_str] = {
            "luc": sa.now_vn().isoformat(timespec="seconds"),
            "group_key": g_key,
            "nhom": post_res.get("nhom"),
            "replied_before_post": reply_res.get("replied", 0),
            "meta": meta,
        }
        save_daily_cycle_log(cycle_log)

    return {
        "ok": bool(post_res.get("ok")),
        "buoc_1_check_binh_luan": reply_res,
        "buoc_2_dang_bai_moi": post_res,
        "bai_moi_meta": meta,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Theo dõi bài viết MXH & trực bình luận định kỳ 4h/lần (Deta AI Lab)")
    p.add_argument("--reply-only", action="store_true", help="Chỉ quét danh sách bài theo dõi & trả lời bình luận, không đăng bài mới")
    p.add_argument("--list-tracked", action="store_true", help="Xem danh sách bài viết đang theo dõi / bài tốt / đã bỏ theo dõi")
    p.add_argument("--preview-new-post", action="store_true", help="Sinh thử bài viết mới + ảnh mẫu mới để xem trước")
    p.add_argument("--force", action="store_true", help="Bắt buộc tạo & đăng thêm 1 bài mới ngay cả khi hôm nay đã đăng")
    args = p.parse_args()
    if args.list_tracked:
        print(json.dumps(get_tracked_posts_for_admin(), ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                run_daily_tsh_cycle(reply_only=args.reply_only, preview_only=args.preview_new_post, force_post=args.force),
                ensure_ascii=False,
                indent=2,
            )
        )
