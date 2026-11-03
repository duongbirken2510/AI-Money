#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ máy tính toán Thần Số Học Pythagoras chuẩn xác + Dựng Thẻ Bản Đồ SVG/PNG có Watermark kiemtien.deta.vn.
Phục vụ chiến dịch kéo traffic tự nhiên 100% miễn phí cho Deta AI Lab.
"""

import datetime
import html
import os
import re
import subprocess
import unicodedata

# Bảng quy đổi chữ cái Pythagoras chuẩn (A=1..I=9, J=1..R=9, S=1..Z=8)
PYTHAGORAS_MAP = {chr(65 + i): (i % 9) + 1 for i in range(26)}
VOWELS_BASE = set("AEIOU")

MEANING_HEADLINES = {
    2: ("Người Kết Nối & Hòa Giải Tinh Tế", "Trực giác nhạy bén, giàu lòng thấu cảm, giỏi lắng nghe và gắn kết tập thể."),
    3: ("Người Truyền Cảm Hứng & Sáng Tạo", "Hoạt ngôn, giàu năng lượng tích cực, tư duy nghệ thuật và khả năng biểu đạt cuốn hút."),
    4: ("Người Kiến Tạo Kỷ Luật & Thực Tế", "Chắc chắn, nguyên tắc, giỏi tổ chức hệ thống và xây nền móng bền vững."),
    5: ("Người Tự Do & Bứt Phá Đổi Mới", "Linh hoạt, yêu trải nghiệm, nhạy bén cơ hội mới và ghét sự gò bó lặp lại."),
    6: ("Người Chăm Sóc & Phụng Sự Yêu Thương", "Trách nhiệm cao, giàu tình cảm gia đình, có gu thẩm mỹ và uy tín cộng đồng."),
    7: ("Nhà Chiến Lược & Chiều Sâu Tri Thức", "Tư duy phân tích sắc sảo, thích tự chiêm nghiệm, học qua trải nghiệm thực tế."),
    8: ("Nhà Điều Hành & Làm Chủ Tài Chính", "Nhạy bén kinh doanh, quyết đoán, tham vọng lớn và năng lực quản trị mạnh mẽ."),
    9: ("Người Dẫn Đường & Lý Tưởng Nhân Văn", "Tầm nhìn rộng, bao dung, khát khao cống hiến giá trị tốt đẹp cho cộng đồng."),
    10: ("Người Tiên Phong Độc Lập & Thích Nghi", "Bản lĩnh dẫn đầu, dám nghĩ dám làm, tự tin xoay chuyển mọi hoàn cảnh."),
    11: ("Bậc Thầy Trực Giác & Truyền Lửa (Master 11/2)", "Tâm thức nhạy bén đặc biệt, khả năng thấu thị vấn đề và dẫn dắt tinh thần."),
    22: ("Kiến Trúc Sư Đại Tài (Master 22/4)", "Kết hợp tầm nhìn lớn của số 11 và óc thực thi kỷ luật của số 4 để dựng nghiệp lớn."),
    33: ("Người Chữa Lành & Dẫn Dắt Bằng Tình Thương (Master 33/6)", "Tần số thấu cảm cao, truyền động lực và nâng đỡ con người vượt nghịch cảnh."),
}

PERSONAL_YEAR_THEMES = {
    1: "Năm số 1 — Gieo hạt & Khởi đầu chu kỳ 9 năm mới: Thời điểm vàng để mở dự án mới, đổi hướng đi và tự chủ quyết định.",
    2: "Năm số 2 — Kết nối & Chậm lại lắng nghe: Ưu tiên bồi đắp quan hệ đối tác, học hỏi sâu, tránh nóng vội đầu tư lướt sóng.",
    3: "Năm số 3 — Mở rộng & Tỏa sáng thương hiệu cá nhân: Thuận lợi cho học tập, truyền thông, bán hàng và mở rộng tệp khách.",
    4: "Năm số 4 — Củng cố nền móng & Kỷ luật tài chính: Năm rà soát quy trình, siết chi phí thừa, tập trung chuyên môn cốt lõi.",
    5: "Năm số 5 — Bước ngoặt tự do & Thay đổi mạnh mẽ: Năng lượng dịch chuyển cao, dễ có cơ hội mới bất ngờ xuất hiện.",
    6: "Năm số 6 — Trách nhiệm, Gia đình & Chăm sóc uy tín: Cân bằng công việc - tổ ấm, thu hút lộc từ sự tận tâm và chữ tín.",
    7: "Năm số 7 — Trầm lắng nội lực & Nâng cấp trí tuệ: Tránh đầu cơ mạo hiểm; càng đầu tư vào kỹ năng chuyên sâu càng thắng lớn ở năm 8.",
    8: "Năm số 8 — Thu hoạch Tài chính & Bứt phá Vị thế: Đỉnh sóng gặt hái thành quả tiền bạc, mở rộng quy mô nếu đã chuẩn bị kỹ.",
    9: "Năm số 9 — Hoàn tất, Thanh lọc & Chuẩn bị Chương mới: Buông bỏ việc/mối quan hệ cũ không còn phù hợp để dọn đường cho chu kỳ mới.",
}

ARROWS_DEF = [
    ((1, 2, 3), "Mũi tên Kế hoạch (1-2-3)", "Giỏi lập kế hoạch có trật tự", "Cần rèn thói quen viết checklist từng bước để tránh làm theo ngẫu hứng"),
    ((4, 5, 6), "Mũi tên Ý chí (4-5-6)", "Ý chí kiên cường vượt áp lực", "Dễ nản hoặc sốt ruột khi kết quả đến chậm, cần chia nhỏ mục tiêu"),
    ((7, 8, 9), "Mũi tên Hoạt động (7-8-9)", "Năng nổ, thực thi nhanh ngoài thực địa", "Cần chủ động bắt tay hành động thực tế thay vì suy nghĩ quá lâu"),
    ((1, 4, 7), "Mũi tên Thực tế (1-4-7)", "Thực dụng, giỏi việc tay nghề & tài chính", "Đôi khi bay bổng thiếu thực tiễn, cần bám sát con số đo lường thật"),
    ((2, 5, 8), "Mũi tên Cân bằng Cảm xúc (2-5-8)", "Làm chủ cảm xúc và thấu hiểu lòng người", "Nhạy cảm ngầm, dễ bị ảnh hưởng tâm trạng bởi lời nói xung quanh"),
    ((3, 6, 9), "Mũi tên Trí tuệ (3-6-9)", "Tư duy logic sắc bén, nhớ lâu", "Cần chủ động rèn trí nhớ và tư duy hệ thống hóa kiến thức"),
    ((1, 5, 9), "Mũi tên Quyết tâm (1-5-9)", "Đã đặt mục tiêu là theo đuổi đến cùng", "Hay trì hoãn bước khởi đầu, cần đặt deadline ngắn 24h-48h để dứt điểm"),
    ((3, 5, 7), "Mũi tên Nhạy bén Tâm thức (3-5-7)", "Trực giác sâu sắc, nhìn thấu bản chất", "Dễ hoài nghi khi thiếu dữ kiện, nên lắng nghe trực giác kết hợp trải nghiệm"),
]


def strip_vietnamese(text: str) -> str:
    s = (text or "").strip()
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_str = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z\s]", " ", ascii_str).upper()


def reduce_num(n: int, keep_master: bool = True, keep_10_for_lp: bool = False) -> int:
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        if keep_10_for_lp and n == 10:
            return 10
        n = sum(int(d) for d in str(n))
    return n


def reduce_single(n: int) -> int:
    while n > 9:
        n = sum(int(d) for d in str(n))
    return max(1, n)


def is_vowel_in_word(word: str, idx: int) -> bool:
    ch = word[idx]
    if ch in VOWELS_BASE:
        return True
    if ch == "Y":
        prev_v = idx > 0 and word[idx - 1] in VOWELS_BASE
        next_v = idx + 1 < len(word) and word[idx + 1] in VOWELS_BASE
        return not (prev_v or next_v)
    return False


def parse_dob(dob_raw: str) -> tuple[int, int, int]:
    """Hỗ trợ DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY."""
    s = (dob_raw or "").strip()
    m_iso = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if m_iso:
        y, mo, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
    else:
        nums = [int(x) for x in re.findall(r"\d+", s)]
        if len(nums) >= 3:
            if nums[0] > 31:
                y, mo, d = nums[0], nums[1], nums[2]
            else:
                d, mo, y = nums[0], nums[1], nums[2]
        else:
            d, mo, y = 15, 8, 1996
    if y < 100:
        y += 1900 if y >= 35 else 2000
    y = min(2025, max(1930, y))
    mo = min(12, max(1, mo))
    d = min(31, max(1, d))
    try:
        datetime.date(y, mo, d)
    except ValueError:
        d = 28
    return d, mo, y


def compute_numerology(ho_ten: str, ngay_sinh: str, current_year: int = 2026) -> dict:
    clean_display_name = " ".join((ho_ten or "").strip().split()) or "Bạn Đọc Deta"
    d, mo, y = parse_dob(ngay_sinh)
    dob_display = f"{d:02d}/{mo:02d}/{y:04d}"

    # 1. Con số chủ đạo (cộng rút gọn từng thành phần Ngày + Tháng + Năm theo chuẩn Pythagoras)
    r_d = reduce_num(d, keep_master=True)
    r_m = reduce_num(mo, keep_master=True)
    r_y = reduce_num(sum(int(x) for x in f"{y:04d}"), keep_master=True)
    total_raw = sum(int(x) for x in f"{d:02d}{mo:02d}{y:04d}")

    lp = reduce_num(r_d + r_m + r_y, keep_master=True, keep_10_for_lp=True)
    if lp == 1:
        lp = 10
    lp_label = "22/4" if lp == 22 else ("33/6" if lp == 33 else ("11/2" if lp == 11 else str(lp)))
    title_lp, short_lp = MEANING_HEADLINES.get(lp, MEANING_HEADLINES[10])

    # 2. Họ tên: Sứ mệnh, Linh hồn, Nhân cách
    norm_name = strip_vietnamese(clean_display_name)
    words = [w for w in norm_name.split() if w]
    word_sums, vowel_sums, cons_sums = [], [], []
    for w in words:
        ws, vs, cs = 0, 0, 0
        for idx, ch in enumerate(w):
            val = PYTHAGORAS_MAP.get(ch, 0)
            ws += val
            if is_vowel_in_word(w, idx):
                vs += val
            else:
                cs += val
        word_sums.append(reduce_num(ws, keep_master=True))
        vowel_sums.append(reduce_num(vs, keep_master=True))
        cons_sums.append(reduce_num(cs, keep_master=True))

    su_menh = reduce_num(sum(word_sums), keep_master=True) if word_sums else 5
    linh_hon = reduce_num(sum(vowel_sums), keep_master=True) if vowel_sums else 2
    nhan_cach = reduce_num(sum(cons_sums), keep_master=True) if cons_sums else 4

    # 3. Thái độ, Ngày sinh, Trưởng thành & Năm cá nhân
    thai_do = reduce_single(d + mo)
    chi_so_ngay_sinh = reduce_num(d, keep_master=True)
    truong_thanh = reduce_num(reduce_single(lp) + reduce_single(su_menh), keep_master=True)
    nam_ca_nhan = reduce_single(reduce_single(d) + reduce_single(mo) + reduce_single(sum(int(x) for x in str(current_year))))
    nam_ca_nhan_sau = reduce_single(reduce_single(d) + reduce_single(mo) + reduce_single(sum(int(x) for x in str(current_year + 1))))

    # 4. Biểu đồ ngày sinh 3x3 (1..9) + Mũi tên
    digits_dob = [int(ch) for ch in f"{d:02d}{mo:02d}{y:04d}" if ch != "0"]
    grid_counts = {i: digits_dob.count(i) for i in range(1, 10)}
    mui_ten_manh = []
    mui_ten_trong = []
    for trip, name_ar, desc_strong, desc_empty in ARROWS_DEF:
        if all(grid_counts[k] > 0 for k in trip):
            mui_ten_manh.append({"ten": name_ar, "mo_ta": desc_strong})
        elif all(grid_counts[k] == 0 for k in trip):
            mui_ten_trong.append({"ten": name_ar.replace("Mũi tên", "Trống trục"), "mo_ta": desc_empty})

    # 5. Kim tự tháp 4 Đỉnh cao đời người
    base_m = reduce_single(mo)
    base_d = reduce_single(d)
    base_y = reduce_single(sum(int(x) for x in f"{y:04d}"))

    p1 = reduce_single(base_m + base_d)
    p2 = reduce_single(base_d + base_y)
    p3 = reduce_num(p1 + p2, keep_master=True, keep_10_for_lp=True)
    p4 = reduce_num(base_m + base_y, keep_master=True, keep_10_for_lp=True)

    # Tuổi đỉnh 1 = 36 - số chủ đạo rút gọn (chuẩn David Phillips: nếu LP=10 -> 36-10=26 hoặc 36-4=32 cho 22/4; chuẩn phổ biến nhất 36 - base_lp_for_age)
    lp_for_age = 4 if lp == 22 else (2 if lp == 11 else (6 if lp == 33 else lp))
    age1 = 36 - lp_for_age
    peaks = [
        {"dinh": 1, "so": p1, "tuoi": age1, "nam": y + age1},
        {"dinh": 2, "so": p2, "tuoi": age1 + 9, "nam": y + age1 + 9},
        {"dinh": 3, "so": p3, "tuoi": age1 + 18, "nam": y + age1 + 18},
        {"dinh": 4, "so": p4, "tuoi": age1 + 27, "nam": y + age1 + 27},
    ]

    return {
        "ho_ten": clean_display_name,
        "ngay_sinh": dob_display,
        "tong_chu_so": total_raw,
        "so_chu_dao": lp,
        "so_chu_dao_nhan": lp_label,
        "danh_xung": title_lp,
        "mo_ta_ngan": short_lp,
        "su_menh": su_menh,
        "linh_hon": linh_hon,
        "nhan_cach": nhan_cach,
        "thai_do": thai_do,
        "ngay_sinh_so": chi_so_ngay_sinh,
        "truong_thanh": truong_thanh,
        "nam_hien_tai": current_year,
        "nam_ca_nhan": nam_ca_nhan,
        "thong_diep_nam": PERSONAL_YEAR_THEMES[nam_ca_nhan],
        "nam_ca_nhan_sau": nam_ca_nhan_sau,
        "thong_diep_nam_sau": PERSONAL_YEAR_THEMES[nam_ca_nhan_sau],
        "bieu_do": grid_counts,
        "mui_ten_manh": mui_ten_manh,
        "mui_ten_trong": mui_ten_trong,
        "chan_de": [base_m, base_d, base_y],
        "dinh_cao": peaks,
    }


def _wrap_svg_lines(text: str, max_chars: int = 58, max_lines: int = 3) -> list[str]:
    words = (text or "").strip().split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(10, max_chars - 3)].rstrip() + "…"
    return lines


CARD_THEMES = [
    # 0: Ngọc Lục Bảo - Xanh Biển Sâu (Mặc định)
    {"bg1": "#050B16", "bg2": "#0B172A", "bg3": "#071E22", "orb1": "#10B981", "orb2": "#0EA5E9", "acc": "#34D399", "wm1": "#059669", "wm2": "#0EA5E9", "wm3": "#D97706"},
    # 1: Vàng Hoàng Gia - Đêm Huyền Học
    {"bg1": "#070B17", "bg2": "#121C34", "bg3": "#1E160A", "orb1": "#F59E0B", "orb2": "#F5C84C", "acc": "#F5C84C", "wm1": "#B45309", "wm2": "#D97706", "wm3": "#0EA5E9"},
    # 2: Tím Tinh Vân - Hồng Ngọc
    {"bg1": "#090618", "bg2": "#1A1033", "bg3": "#220C24", "orb1": "#A855F7", "orb2": "#EC4899", "acc": "#C084FC", "wm1": "#7E22CE", "wm2": "#DB2777", "wm3": "#F59E0B"},
    # 3: Lam Ngọc Sapphire - Hổ Phách
    {"bg1": "#040D1A", "bg2": "#0A223D", "bg3": "#0E1D2F", "orb1": "#38BDF8", "orb2": "#6366F1", "acc": "#38BDF8", "wm1": "#0284C7", "wm2": "#4F46E5", "wm3": "#10B981"},
    # 4: Đỏ Hồng Ngọc - Vàng Kim Cổ Điển
    {"bg1": "#12060B", "bg2": "#240E18", "bg3": "#1D150B", "orb1": "#F43F5E", "orb2": "#F59E0B", "acc": "#FB7185", "wm1": "#BE123C", "wm2": "#D97706", "wm3": "#059669"},
]


def build_numerology_svg(prof: dict, core_advice: str = "", theme_idx: int = 0, include_watermark: bool = True) -> str:
    """Sinh thẻ SVG 1080x1350 sắc nét (mặc định có đóng dấu Watermark kiemtien.deta.vn; bản Cẩm nang VIP tắt watermark)."""
    th = CARD_THEMES[int(theme_idx) % len(CARD_THEMES)]
    esc = lambda s: html.escape(str(s or ""))
    name_up = prof["ho_ten"].upper()[:34]
    dob = prof["ngay_sinh"]
    lp_lbl = prof["so_chu_dao_nhan"]
    danh_xung = prof["danh_xung"]
    yr = prof["nam_hien_tai"]

    # Biểu đồ 3x3 Pythagoras: Hàng trên (3, 6, 9), Hàng giữa (2, 5, 8), Hàng dưới (1, 4, 7)
    rows_3x3 = [(3, 6, 9), (2, 5, 8), (1, 4, 7)]
    cells_svg = []
    gx0, gy0, cell_w, cell_h = 84, 650, 118, 96
    for r_idx, row_nums in enumerate(rows_3x3):
        for c_idx, num in enumerate(row_nums):
            cx = gx0 + c_idx * (cell_w + 10)
            cy = gy0 + r_idx * (cell_h + 10)
            cnt = prof["bieu_do"].get(num, 0)
            val_txt = str(num) * min(cnt, 4) if cnt > 0 else "—"
            fill_bg = "rgba(16,185,129,0.20)" if cnt > 0 else "rgba(255,255,255,0.03)"
            stroke_c = "#34D399" if cnt > 0 else "rgba(148,163,184,0.22)"
            txt_c = "#F8FAFC" if cnt > 0 else "rgba(148,163,184,0.38)"
            cells_svg.append(
                f'<rect x="{cx}" y="{cy}" width="{cell_w}" height="{cell_h}" rx="16" fill="{fill_bg}" stroke="{stroke_c}" stroke-width="2"/>'
                f'<text x="{cx + 14}" y="{cy + 24}" fill="rgba(148,163,184,0.55)" font-size="15" font-weight="700">{num}</text>'
                f'<text x="{cx + cell_w/2}" y="{cy + 62}" text-anchor="middle" fill="{txt_c}" font-size="30" font-weight="900">{val_txt}</text>'
            )

    # Kim tự tháp 4 đỉnh cao bên phải (x từ 540 đến 996)
    b_m, b_d, b_y = prof["chan_de"]
    p1, p2, p3, p4 = prof["dinh_cao"]
    pyr_svg = f"""
    <g stroke="#F59E0B" stroke-width="2.4" fill="none" opacity="0.82">
      <!-- Đỉnh 4 ngoài cùng -->
      <path d="M580 946 L780 680 L980 946"/>
      <!-- Đỉnh 3 giữa -->
      <path d="M635 946 L780 756 L925 946"/>
      <!-- Đỉnh 1 & Đỉnh 2 -->
      <path d="M580 946 L680 842 L780 946 L880 842 L980 946"/>
    </g>
    <!-- 3 Chân đế -->
    <circle cx="580" cy="946" r="21" fill="#0F172A" stroke="#38BDF8" stroke-width="2.2"/>
    <text x="580" y="953" text-anchor="middle" fill="#38BDF8" font-size="19" font-weight="800">{b_m}</text>
    <text x="580" y="980" text-anchor="middle" fill="#94A3B8" font-size="13" font-weight="600">Tháng</text>

    <circle cx="780" cy="946" r="21" fill="#0F172A" stroke="#38BDF8" stroke-width="2.2"/>
    <text x="780" y="953" text-anchor="middle" fill="#38BDF8" font-size="19" font-weight="800">{b_d}</text>
    <text x="780" y="980" text-anchor="middle" fill="#94A3B8" font-size="13" font-weight="600">Ngày</text>

    <circle cx="980" cy="946" r="21" fill="#0F172A" stroke="#38BDF8" stroke-width="2.2"/>
    <text x="980" y="953" text-anchor="middle" fill="#38BDF8" font-size="19" font-weight="800">{b_y}</text>
    <text x="980" y="980" text-anchor="middle" fill="#94A3B8" font-size="13" font-weight="600">Năm</text>

    <!-- 4 Đỉnh cao -->
    <circle cx="680" cy="842" r="23" fill="#172554" stroke="#FBBF24" stroke-width="2.5"/>
    <text x="680" y="849" text-anchor="middle" fill="#FEF08A" font-size="20" font-weight="900">{p1['so']}</text>
    <text x="680" y="809" text-anchor="middle" fill="#CBD5E1" font-size="13.5" font-weight="700">{p1['tuoi']}t ({p1['nam']})</text>

    <circle cx="880" cy="842" r="23" fill="#172554" stroke="#FBBF24" stroke-width="2.5"/>
    <text x="880" y="849" text-anchor="middle" fill="#FEF08A" font-size="20" font-weight="900">{p2['so']}</text>
    <text x="880" y="809" text-anchor="middle" fill="#CBD5E1" font-size="13.5" font-weight="700">{p2['tuoi']}t ({p2['nam']})</text>

    <circle cx="780" cy="756" r="24" fill="#064E3B" stroke="#34D399" stroke-width="2.6"/>
    <text x="780" y="764" text-anchor="middle" fill="#A7F3D0" font-size="21" font-weight="900">{p3['so']}</text>
    <text x="844" y="761" text-anchor="start" fill="#CBD5E1" font-size="13.5" font-weight="700">{p3['tuoi']}t ({p3['nam']})</text>

    <circle cx="780" cy="680" r="25" fill="#78350F" stroke="#F59E0B" stroke-width="3"/>
    <text x="780" y="688" text-anchor="middle" fill="#FEF3C7" font-size="22" font-weight="900">{p4['so']}</text>
    <text x="846" y="685" text-anchor="start" fill="#FDE68A" font-size="14" font-weight="800">{p4['tuoi']}t ({p4['nam']})</text>
    """

    advice_text = (core_advice or prof["thong_diep_nam"]).strip()
    advice_lines = _wrap_svg_lines(advice_text, max_chars=66, max_lines=3)
    advice_tspans = "".join(
        f'<tspan x="92" dy="{0 if i == 0 else 32}">{esc(line)}</tspan>' for i, line in enumerate(advice_lines)
    )

    badges = [
        ("SỨ MỆNH", str(prof["su_menh"]), "#10B981"),
        ("LINH HỒN", str(prof["linh_hon"]), "#38BDF8"),
        ("NHÂN CÁCH", str(prof["nhan_cach"]), "#A78BFA"),
        (f"NĂM CÁ NHÂN {yr}", str(prof["nam_ca_nhan"]), "#F59E0B"),
    ]
    badge_svg = []
    for idx, (lbl, val, col) in enumerate(badges):
        bx = 64 + idx * 244
        badge_svg.append(
            f'<rect x="{bx}" y="468" width="224" height="114" rx="20" fill="rgba(255,255,255,0.05)" stroke="{col}" stroke-opacity="0.55" stroke-width="1.8"/>'
            f'<text x="{bx + 112}" y="502" text-anchor="middle" fill="#94A3B8" font-size="14" font-weight="800" letter-spacing="1.2">{esc(lbl)}</text>'
            f'<text x="{bx + 112}" y="558" text-anchor="middle" fill="{col}" font-size="44" font-weight="900">{esc(val)}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1350" width="1080" height="1350" style="font-family:'Be Vietnam Pro',system-ui,-apple-system,sans-serif">
  <defs>
    <linearGradient id="bgG" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{th['bg1']}"/>
      <stop offset="52%" stop-color="{th['bg2']}"/>
      <stop offset="100%" stop-color="{th['bg3']}"/>
    </linearGradient>
    <radialGradient id="orbG" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{th['orb1']}" stop-opacity="0.42"/>
      <stop offset="60%" stop-color="{th['orb2']}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{th['bg1']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="ringG" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{th['acc']}"/>
      <stop offset="50%" stop-color="{th['orb2']}"/>
      <stop offset="100%" stop-color="#F59E0B"/>
    </linearGradient>
    <linearGradient id="wmG" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{th['wm1']}"/>
      <stop offset="55%" stop-color="{th['wm2']}"/>
      <stop offset="100%" stop-color="{th['wm3']}"/>
    </linearGradient>
  </defs>

  <rect width="1080" height="1350" fill="url(#bgG)"/>
  <circle cx="540" cy="285" r="320" fill="url(#orbG)"/>
  <rect x="28" y="28" width="1024" height="1294" rx="34" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>

  <!-- Header -->
  <text x="540" y="78" text-anchor="middle" fill="{th['acc']}" font-size="17" font-weight="800" letter-spacing="3.5">BẢN ĐỒ THẦN SỐ HỌC PYTHAGORAS · DETA AI LAB</text>
  <text x="540" y="128" text-anchor="middle" fill="#F8FAFC" font-size="38" font-weight="900">{esc(name_up)}</text>
  <text x="540" y="164" text-anchor="middle" fill="#94A3B8" font-size="20" font-weight="600">Ngày sinh dương lịch: {esc(dob)}</text>

  <!-- Vòng hào quang Số Chủ Đạo -->
  <circle cx="540" cy="288" r="98" fill="rgba(15,23,42,0.85)" stroke="url(#ringG)" stroke-width="6"/>
  <circle cx="540" cy="288" r="112" fill="none" stroke="rgba(255,255,255,0.22)" stroke-width="2" stroke-dasharray="7 7"/>
  <text x="540" y="246" text-anchor="middle" fill="#94A3B8" font-size="14" font-weight="800" letter-spacing="2">SỐ CHỦ ĐẠO</text>
  <text x="540" y="324" text-anchor="middle" fill="#FFFFFF" font-size="78" font-weight="900">{esc(lp_lbl)}</text>

  <text x="540" y="426" text-anchor="middle" fill="#FDE68A" font-size="25" font-weight="800">{esc(danh_xung)}</text>

  <!-- 4 Chỉ số cốt lõi -->
  {"".join(badge_svg)}

  <!-- Khối Biểu đồ ngày sinh & Kim tự tháp 4 đỉnh cao -->
  <rect x="64" y="602" width="414" height="392" rx="24" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.10)" stroke-width="1.5"/>
  <text x="86" y="634" fill="{th['acc']}" font-size="17" font-weight="800">📊 BIỂU ĐỒ NGÀY SINH (3 TRỤC)</text>
  {"".join(cells_svg)}

  <rect x="502" y="602" width="514" height="392" rx="24" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.10)" stroke-width="1.5"/>
  <text x="526" y="634" fill="#FBBF24" font-size="17" font-weight="800">⛰️ KIM TỰ THÁP 4 ĐỈNH CAO ĐỜI NGƯỜI</text>
  {pyr_svg}

  <!-- Thông điệp định hướng Năm Cá Nhân -->
  <rect x="64" y="1018" width="952" height="174" rx="24" fill="rgba(255,255,255,0.05)" stroke="{th['acc']}" stroke-opacity="0.45" stroke-width="2"/>
  <text x="92" y="1056" fill="{th['acc']}" font-size="17" font-weight="800" letter-spacing="1">✨ ĐỊNH HƯỚNG TRỌNG TÂM &amp; NĂM CÁ NHÂN {yr}:</text>
  <text x="92" y="1096" fill="#F1F5F9" font-size="21" font-weight="600">{advice_tspans}</text>

  <!-- Thanh chân thẻ: Watermark kéo traffic (bản miễn phí) hoặc Ấn dấu Độc bản (bản Cẩm nang VIP) -->
  {f'''<rect x="64" y="1216" width="952" height="78" rx="22" fill="url(#wmG)"/>
  <text x="540" y="1250" text-anchor="middle" fill="#FFFFFF" font-size="20" font-weight="900" letter-spacing="0.6">🔮 XEM BẢN ĐẦY ĐỦ MIỄN PHÍ 100% TẠI: KIEMTIEN.DETA.VN</text>
  <text x="540" y="1278" text-anchor="middle" fill="rgba(255,255,255,0.94)" font-size="15.5" font-weight="700">Gõ kiemtien.deta.vn/cong-cu/than-so-hoc · Miễn phí 100% không cần đăng nhập</text>''' if include_watermark else f'''<rect x="64" y="1216" width="952" height="78" rx="22" fill="rgba(245,158,11,0.14)" stroke="#F59E0B" stroke-opacity="0.55" stroke-width="1.8"/>
  <text x="540" y="1250" text-anchor="middle" fill="#FDE68A" font-size="19" font-weight="900" letter-spacing="1.4">✦ ẤN BẢN HỒ SƠ CÁ NHÂN ĐỘC BẢN · PYTHAGORAS VIP ✦</text>
  <text x="540" y="1277" text-anchor="middle" fill="#CBD5E1" font-size="15" font-weight="600">Lập riêng cho {esc(prof["ho_ten"])} ({esc(dob)}) · Bản sạch lưu trữ &amp; in ấn cá nhân</text>'''}
</svg>"""


PERSONAL_MONTH_GUIDE = {
    1: {
        "ten": "Tháng Khởi Đầu & Mở Lối Mới",
        "cong_viec": "Chủ động đề xuất ý tưởng mới, mở dự án/kênh bán hàng mới hoặc tiếp cận tệp khách hàng chưa từng khai thác.",
        "tai_chinh": "Thuận lợi để gieo khoản đầu tư nhỏ vào công cụ/kỹ năng tạo dòng tiền dài hạn.",
        "can_tranh": "Tránh chần chừ chờ người khác quyết hộ hoặc ôm đồm quá 2 mục tiêu lớn cùng lúc.",
        "ngay_dep": (1, 10, 19, 28),
    },
    2: {
        "ten": "Tháng Kết Nối & Đàm Phán Mềm",
        "cong_viec": "Chăm sóc lại khách hàng cũ, tìm người đồng hành bổ trợ khuyết điểm, lắng nghe kỹ trước khi chốt hợp đồng.",
        "tai_chinh": "Giữ nhịp dòng tiền an toàn, rà soát các điều khoản chia sẻ quyền lợi rõ ràng.",
        "can_tranh": "Tránh nóng nảy tranh cãi hơn thua hoặc quyết định chi tiền theo cảm xúc nhất thời.",
        "ngay_dep": (2, 11, 20, 29),
    },
    3: {
        "ten": "Tháng Tỏa Sáng & Bùng Nổ Giao Tiếp",
        "cong_viec": "Đẩy mạnh xuất hiện trước công chúng, viết bài chia sẻ, livestream, thuyết trình hoặc ra mắt sản phẩm mới.",
        "tai_chinh": "Lộc đến từ lời nói, thương hiệu cá nhân và các mối quan hệ xã hội mở rộng.",
        "can_tranh": "Tránh phân tán năng lượng vào các cuộc vui vô bổ hoặc mua sắm quá tay vì hứng thú.",
        "ngay_dep": (3, 12, 21, 30),
    },
    4: {
        "ten": "Tháng Kỷ Luật & Gia Cố Nền Móng",
        "cong_viec": "Chuẩn hóa quy trình làm việc, dọn dẹp giấy tờ tồn đọng, tập trung hoàn thành dứt điểm việc đang dang dở.",
        "tai_chinh": "Lập bảng kiểm soát thu chi chặt chẽ, cắt giảm các khoản rò rỉ nhỏ hằng tháng.",
        "can_tranh": "Tránh đầu cơ lướt sóng rủi ro cao hoặc nhảy việc bốc đồng khi chưa có phương án dự phòng.",
        "ngay_dep": (4, 13, 22, 31),
    },
    5: {
        "ten": "Tháng Dịch Chuyển & Cơ Hội Bất Ngờ",
        "cong_viec": "Thử nghiệm cách làm mới, đi công tác/gặp gỡ môi trường mới, linh hoạt xoay trục khi thị trường đổi chiều.",
        "tai_chinh": "Dễ xuất hiện nguồn thu phụ hoặc đơn hàng bất ngờ từ kênh mới mở.",
        "can_tranh": "Tránh cả thèm chóng chán, bỏ dở kế hoạch cốt lõi chỉ vì một lời rủ rê hào nhoáng.",
        "ngay_dep": (5, 14, 23),
    },
    6: {
        "ten": "Tháng Uy Tín, Tổ Ấm & Chăm Sóc Giá Trị",
        "cong_viec": "Nâng cấp chất lượng dịch vụ hậu mãi, xây dựng niềm tin sâu với đồng đội và khách hàng trung thành.",
        "tai_chinh": "Thuận lợi cho các khoản chi nâng cấp không gian sống, sức khỏe gia đình hoặc sản phẩm chăm sóc con người.",
        "can_tranh": "Tránh ôm hết trách nhiệm của người khác vào mình dẫn tới quá tải tinh thần.",
        "ngay_dep": (6, 15, 24),
    },
    7: {
        "ten": "Tháng Chiều Sâu & Nâng Cấp Nội Lực",
        "cong_viec": "Học sâu một kỹ năng chuyên môn khó, nghiên cứu dữ liệu, hoạch định chiến lược dài hơi cho quý tới.",
        "tai_chinh": "Ưu tiên phòng thủ, giữ tiền mặt/tích sản an toàn; tuyệt đối không cho vay mượn mù mờ.",
        "can_tranh": "Tránh hùn hạp làm ăn vội vàng hoặc thức khuya suy nghĩ tiêu cực một mình.",
        "ngay_dep": (7, 16, 25),
    },
    8: {
        "ten": "Tháng Thu Hoạch Tài Chính & Quyết Đoán",
        "cong_viec": "Tăng tốc chốt mục tiêu doanh số, đàm phán tăng lương/giá trị gói dịch vụ, mở rộng quy mô vận hành.",
        "tai_chinh": "Tháng đỉnh sóng về tiền bạc nếu các tháng trước đã gieo hạt nghiêm túc; thu hồi công nợ tốt.",
        "can_tranh": "Tránh độc đoán áp đặt cấp dưới hoặc dùng đòn bẩy nợ vượt quá khả năng kiểm soát.",
        "ngay_dep": (8, 17, 26),
    },
    9: {
        "ten": "Tháng Tổng Kết, Thanh Lọc & Chuyển Giao",
        "cong_viec": "Đóng lại các dự án kém hiệu quả, hoàn tất lời hứa cũ, chia sẻ giá trị cho cộng đồng để lấy đà chu kỳ mới.",
        "tai_chinh": "Thu gom công nợ cũ, thanh lý đồ đạc/tồn kho không dùng đến để giải phóng vốn.",
        "can_tranh": "Tránh khởi sự dự án lớn tốn nhiều vốn ngay cuối chu kỳ khi chưa thanh lọc xong việc cũ.",
        "ngay_dep": (9, 18, 27),
    },
}

CAREER_WEALTH_MATRIX = {
    2: ("Cố vấn khách hàng, Nhân sự (HR), Ngoại giao, Trợ lý điều hành, Dịch vụ chăm sóc tinh tế", "Giữ vai trò người kết nối & hậu phương chiến lược bên cạnh một người tiên phong quyết đoán.", "Hay cả nể cho vay hoặc ngại đòi quyền lợi xứng đáng cho mình."),
    3: ("Truyền thông, Marketing, Sáng tạo nội dung, Đào tạo, Thiết kế, Kinh doanh thương hiệu cá nhân", "Kiếm tiền mạnh nhất khi đứng ở tuyến đầu truyền cảm hứng, bán hàng bằng câu chuyện và sự hoạt ngôn.", "Chi tiêu theo cảm hứng, dễ mua sắm giải tỏa cảm xúc mà quên quỹ tích sản."),
    4: ("Quản trị vận hành, Tài chính - Kế toán, Kỹ thuật, Bất động sản thực, Xây dựng hệ thống quy trình", "Tích lũy tài sản bền vững nhờ chuyên môn sâu, sự chuẩn xác và kỷ luật tích sản đều đặn.", "Đôi khi quá cầu toàn nên bỏ lỡ cơ hội nhân rộng quy mô khi thị trường đang lên."),
    5: ("Thương mại điện tử, Du lịch, Kinh doanh đa kênh, Sales thực chiến, Công nghệ mới & Tự doanh", "Tạo đột phá dòng tiền nhờ nhạy bén xu hướng mới, xoay vòng vốn nhanh và mạng lưới quan hệ rộng.", "Dễ phân tán vốn vào nhiều kèo nhỏ cùng lúc nhưng thiếu người giữ kỷ luật hậu cần."),
    6: ("Y tế - Sức khỏe, Giáo dục, Thẩm mỹ - Làm đẹp, F&B gia đình, Dịch vụ tư vấn & Chăm sóc cao cấp", "Khách hàng tự tìm đến nhờ chữ Tín và sự tận tâm; rất hợp xây thương hiệu dịch vụ có khách quay lại lâu dài.", "Hay chi tiền lo cho người thân/đồng đội quá mức mà quên dự phòng riêng."),
    7: ("Công nghệ/IT, Phân tích dữ liệu, Nghiên cứu chuyên sâu, Cố vấn chiến lược, Đầu tư giá trị dựa trên phân tích", "Bán chất xám độc quyền ở phân khúc chuyên gia sâu thay vì cạnh tranh giá rẻ đại trà.", "Ngại tự quảng bá bản thân nên nhiều khi năng lực giỏi nhưng ít người biết tới."),
    8: ("Điều hành doanh nghiệp, Tài chính - Đầu tư, Thương mại quy mô lớn, Quản lý dự án, Nhượng quyền", "Làm chủ bài toán dòng tiền, đòn bẩy nhân sự và đóng gói mô hình kinh doanh có khả năng nhân bản.", "Khi thắng lớn dễ chủ quan mở rộng quá nóng; cần tách biệt quỹ an toàn gia đình."),
    9: ("Giáo dục cộng đồng, Nghệ thuật, Y dược nhân văn, Quản trị tổ chức xã hội, Huấn luyện phát triển con người", "Thu hút nguồn lực và tài chính lớn khi gắn sản phẩm kinh doanh với sứ mệnh giúp ích thật cho nhiều người.", "Dễ mủi lòng hỗ trợ sai người hoặc ngại nói chuyện tiền bạc thẳng thắn từ đầu."),
    10: ("Khởi nghiệp độc lập, Giám đốc điều hành, Tiên phong mở thị trường mới, Tư vấn độc lập, Công nghệ", "Đứng mũi chịu sào, tự quyết định cuộc chơi và dẫn dắt đội nhóm chinh phục mục tiêu rõ ràng.", "Cái tôi lớn dễ tự gánh vác một mình, cần học cách trao quyền để không bị kiệt sức."),
    11: ("Huấn luyện (Coaching), Cố vấn tâm lý/thương hiệu, Truyền thông chiều sâu, Nghệ thuật, Giáo dục khai phóng", "Chạm tới niềm tin sâu của khách hàng nhờ trực giác sắc bén và khả năng truyền lửa chân thành.", "Tâm trạng lên xuống ảnh hưởng hiệu suất kiếm tiền; cần một cộng sự giỏi vận hành số liệu."),
    22: ("Kiến tạo hệ thống doanh nghiệp lớn, Hạ tầng - Công nghệ lõi, Chuỗi cung ứng, Giáo dục & Đầu tư dài hạn", "Biến ý tưởng tầm vóc lớn thành bộ máy vận hành thực tế có quy trình chuẩn mực.", "Áp lực tự đặt quá cao; cần chia lộ trình lớn thành từng chặng thu tiền ngắn hạn rõ ràng."),
    33: ("Giáo dục nhân bản, Chăm sóc sức khỏe toàn diện, Trị liệu & Phát triển cộng đồng bền vững", "Tạo sức hút tự nhiên nhờ tần số chữa lành, uy tín đạo đức và sự tin yêu tuyệt đối của cộng đồng.", "Cần đặt ranh giới tài chính minh bạch để vừa phụng sự vừa đảm bảo đời sống sung túc."),
}

COMPATIBILITY_MATRIX = {
    2: ("2, 6, 8, 9", "4, 8, 10", "5 (cần tôn trọng không gian tự do của nhau)"),
    3: ("3, 5, 6, 9", "10, 8, 22/4", "4, 7 (tránh chê bai thẳng thừng làm tụt cảm hứng)"),
    4: ("2, 4, 6, 8", "8, 10, 22/4", "3, 5 (cần thống nhất khung kỷ luật chung từ đầu)"),
    5: ("3, 5, 7, 10", "3, 8, 10", "2, 4 (tránh kiểm soát giờ giấc quá khắt khe)"),
    6: ("2, 3, 6, 9", "4, 8, 11/2", "5, 7 (tránh nhân danh sự quan tâm để áp đặt)"),
    7: ("5, 7, 9, 11/2", "4, 8, 10", "3, 8 (cần tôn trọng khoảng lặng suy ngẫm riêng)"),
    8: ("2, 4, 6, 8", "4, 10, 22/4", "7, 9 (cần mềm mỏng lắng nghe thay vì chỉ nói lý lẽ)"),
    9: ("2, 3, 6, 9, 11/2", "4, 8, 10", "4, 5 (cần rõ ràng ranh giới tiền bạc và cam kết)"),
    10: ("3, 5, 6, 10", "2, 4, 8", "8, 10 khác (hai người dẫn đầu cần chia rõ lãnh địa quyết định)"),
    11: ("2, 6, 7, 9", "4, 8, 22/4", "5, 8 (cần giao tiếp nhẹ nhàng, tránh môi trường xung đột gắt)"),
    22: ("4, 6, 8, 11/2", "8, 10, 4", "3, 5 (cần kiên nhẫn giải thích tầm nhìn từng bước)"),
    33: ("2, 6, 9, 11/2", "4, 8, 10", "5, 7 (cần cân bằng giữa cho đi và lắng nghe nhu cầu bản thân)"),
}


def compute_12_months_roadmap(prof: dict, start_year: int | None = None, start_month: int | None = None) -> list[dict]:
    """Tính lịch trình 12 Tháng Cá Nhân liên tiếp theo chuẩn Pythagoras từ tháng hiện tại."""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    sy = start_year or now.year
    sm = start_month or now.month
    d, mo, _ = parse_dob(prof["ngay_sinh"])
    rd_d = reduce_single(d)
    rd_m = reduce_single(mo)

    roadmap = []
    for offset in range(12):
        cal_m = ((sm - 1 + offset) % 12) + 1
        cal_y = sy + ((sm - 1 + offset) // 12)
        py = reduce_single(rd_d + rd_m + reduce_single(sum(int(x) for x in str(cal_y))))
        pm = reduce_single(py + reduce_single(cal_m))
        g = PERSONAL_MONTH_GUIDE[pm]
        max_day = 28 if cal_m == 2 else (30 if cal_m in (4, 6, 9, 11) else 31)
        lucky_days = [f"{day:02d}/{cal_m:02d}" for day in g["ngay_dep"] if day <= max_day]
        roadmap.append(
            {
                "thu_tu": offset + 1,
                "thang_nam": f"Tháng {cal_m:02d}/{cal_y}",
                "nam_ca_nhan": py,
                "thang_ca_nhan": pm,
                "tieu_de": g["ten"],
                "cong_viec": g["cong_viec"],
                "tai_chinh": g["tai_chinh"],
                "can_tranh": g["can_tranh"],
                "ngay_dep": ", ".join(lucky_days),
            }
        )
    return roadmap


def build_vip_booklet_html(prof: dict, core_advice: str, reading_5_parts: str) -> str:
    """Xuất Ấn bản Cẩm Nang A4 Cá Nhân Hóa (Không Watermark quảng cáo, sẵn sàng In / Lưu PDF chuẩn A4)."""
    esc = lambda s: html.escape(str(s or ""))
    clean_svg = build_numerology_svg(prof, core_advice=core_advice, theme_idx=1, include_watermark=False)
    months = compute_12_months_roadmap(prof)
    lp = prof["so_chu_dao"]
    cw_jobs, cw_role, cw_leak = CAREER_WEALTH_MATRIX.get(lp, CAREER_WEALTH_MATRIX[10])
    cp_love, cp_biz, cp_note = COMPATIBILITY_MATRIX.get(lp, COMPATIBILITY_MATRIX[10])

    # Tách bài luận 5 phần thành từng khối rõ đẹp
    cleaned_read = re.sub(r"^THÔNG ĐIỆP CỐT LÕI:.*$", "", reading_5_parts or "", flags=re.M).replace("**", "").strip()
    paras_html = "".join(
        f"<p>{esc(line.strip())}</p>" for line in cleaned_read.splitlines() if line.strip()
    )

    months_cards = []
    for m in months:
        months_cards.append(
            f"""<div class="m-item">
              <div class="m-head">
                <span class="m-time">📅 {esc(m['thang_nam'])}</span>
                <span class="m-num">Tháng cá nhân số {m['thang_ca_nhan']} · (Năm CN {m['nam_ca_nhan']})</span>
              </div>
              <h4>{esc(m['tieu_de'])}</h4>
              <p><b>💼 Sự nghiệp:</b> {esc(m['cong_viec'])}</p>
              <p><b>💰 Dòng tiền:</b> {esc(m['tai_chinh'])}</p>
              <p class="warn"><b>⚠️ Lưu ý tránh:</b> {esc(m['can_tranh'])}</p>
              <div class="lucky">✦ Ngày năng lượng đỉnh: <b>{esc(m['ngay_dep'])}</b></div>
            </div>"""
        )

    manh_html = "".join(f"<li><b>{esc(x['ten'])}:</b> {esc(x['mo_ta'])}</li>" for x in (prof.get("mui_ten_manh") or [])) or "<li>Năng lượng phân bổ linh hoạt đa trục, dễ thích nghi nhiều môi trường.</li>"
    trong_html = "".join(f"<li><b>{esc(x['ten'])}:</b> {esc(x['mo_ta'])}</li>" for x in (prof.get("mui_ten_trong") or [])) or "<li>Biểu đồ ngày sinh cân đối, không bị trống hoàn toàn trục 3 số nào.</li>"

    slug = re.sub(r"[^a-z0-9]+", "-", strip_vietnamese(prof["ho_ten"]).lower()).strip("-") or "ho-so"
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cẩm Nang Thần Số Học 12 Tháng — {esc(prof['ho_ten'])} ({esc(prof['ngay_sinh'])})</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700;800&family=Lora:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
<style>
  :root{{--ink:#172033;--muted:#4B5565;--gold:#A16207;--gold-bg:#FEF9C3;--emerald:#047857;--border:#E2E8F0;--paper:#FAF8F5}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--paper);color:var(--ink);font:400 15px/1.68 "Be Vietnam Pro",system-ui,sans-serif}}
  .toolbar{{position:sticky;top:0;z-index:30;background:#0B1324;color:#F8FAFC;padding:12px 20px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;box-shadow:0 8px 24px rgba(0,0,0,.22)}}
  .toolbar b{{font-size:14.5px;color:#FDE68A}}
  .tb-btns{{display:flex;flex-wrap:wrap;gap:8px}}
  .btn{{border:0;border-radius:999px;padding:9px 16px;font:700 13.5px/1 "Be Vietnam Pro",sans-serif;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px}}
  .btn-gold{{background:linear-gradient(135deg,#F59E0B,#D97706);color:#fff}}
  .btn-sub{{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.22)}}
  .booklet{{max-width:860px;margin:24px auto 60px;padding:0 16px}}
  .sheet{{background:#FFFFFF;border:1px solid var(--border);border-radius:20px;padding:34px 38px;margin-bottom:24px;box-shadow:0 12px 32px -12px rgba(15,23,42,.08)}}
  .eyebrow{{font-size:11.5px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);display:block;margin-bottom:6px}}
  h1,h2,h3{{font-family:"Lora",Georgia,serif;color:#0F172A;margin:0 0 10px}}
  h1{{font-size:30px;line-height:1.25}}
  h2{{font-size:23px;border-bottom:2px solid #FDE68A;padding-bottom:8px;margin-bottom:16px}}
  .quote{{background:#FFFBEB;border-left:4px solid #D97706;padding:13px 16px;border-radius:0 12px 12px 0;font-family:"Lora",serif;font-style:italic;font-size:16px;margin:14px 0 20px}}
  .svg-wrap{{max-width:520px;margin:16px auto;border-radius:18px;overflow:hidden;box-shadow:0 12px 28px rgba(15,23,42,.16)}}
  .svg-wrap svg{{width:100%;height:auto;display:block}}
  .reading-prose p{{margin:0 0 11px;text-align:justify}}
  .months-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
  .m-item{{border:1px solid var(--border);border-radius:14px;padding:14px 16px;background:#FCFDFE;break-inside:avoid}}
  .m-head{{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:5px;flex-wrap:wrap}}
  .m-time{{font-weight:800;font-size:13.5px;color:#0F172A;background:#FEF3C7;padding:3px 10px;border-radius:999px}}
  .m-num{{font-size:12px;font-weight:700;color:var(--emerald)}}
  .m-item h4{{margin:4px 0 8px;font-size:15.5px;color:#B45309}}
  .m-item p{{margin:0 0 6px;font-size:13.6px;line-height:1.52}}
  .m-item p.warn{{color:#991B1B}}
  .lucky{{margin-top:7px;padding-top:6px;border-top:1px dashed var(--border);font-size:12.8px;color:var(--emerald)}}
  .matrix-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:12px}}
  .mx-box{{border:1px solid var(--border);border-radius:14px;padding:16px;background:#F8FAFC;break-inside:avoid}}
  .mx-box h3{{font-size:17px;margin-bottom:8px;color:#0F172A}}
  .mx-box ul{{margin:0;padding-left:18px;font-size:14px}}
  .mx-box li{{margin-bottom:6px}}
  @media (max-width:680px){{.sheet{{padding:22px 18px}}.months-grid,.matrix-grid{{grid-template-columns:1fr}}}}
  @media print{{
    body{{background:#fff;font-size:12.5pt}}
    .toolbar{{display:none!important}}
    .booklet{{max-width:100%;margin:0;padding:0}}
    .sheet{{box-shadow:none;border:0;padding:0;margin:0 0 18pt;page-break-after:always}}
    .sheet:last-child{{page-break-after:auto}}
  }}
</style>
</head>
<body>
<div class="toolbar">
  <div><b>📖 Ấn Bản Cẩm Nang Cá Nhân Độc Bản — {esc(prof['ho_ten'])}</b> <span style="font-size:12.5px;opacity:.8">(Không Watermark · Chuẩn khổ A4)</span></div>
  <div class="tb-btns">
    <button type="button" class="btn btn-gold" onclick="window.print()">🖨️ In A4 / Lưu thành File PDF</button>
    <button type="button" class="btn btn-sub" id="bt-save-html">⬇️ Tải File Cẩm Nang (.HTML)</button>
  </div>
</div>

<main class="booklet">
  <section class="sheet">
    <span class="eyebrow">Ấn bản Hồ sơ Thần Số Học Pythagoras Độc bản</span>
    <h1>{esc(prof['ho_ten'])} <span style="font-weight:400;font-size:.7em;color:var(--muted)">({esc(prof['ngay_sinh'])})</span></h1>
    <div style="font-weight:700;color:var(--gold);font-size:16.5px">Số Chủ Đạo {esc(prof['so_chu_dao_nhan'])} — {esc(prof['danh_xung'])} · Sứ mệnh {prof['su_menh']} · Linh hồn {prof['linh_hon']} · Nhân cách {prof['nhan_cach']}</div>
    <div class="quote">“{esc(core_advice)}”</div>
    <div class="svg-wrap">{clean_svg}</div>
  </section>

  <section class="sheet">
    <span class="eyebrow">Phần I · Giải Mã Chiều Sâu Bản Thể</span>
    <h2>5 Trụ Cột Luận Giải Cá Nhân Hóa</h2>
    <div class="reading-prose">{paras_html}</div>
  </section>

  <section class="sheet">
    <span class="eyebrow">Phần II · Lộ Trình Vận Niên 12 Tháng Tới</span>
    <h2>Lịch Hành Động &amp; Ngày Năng Lượng Đỉnh 12 Tháng Liên Tiếp</h2>
    <p style="color:var(--muted);margin-top:-6px;margin-bottom:16px">Tính chính xác từ Ngày sinh {esc(prof['ngay_sinh'])} kết hợp chu kỳ Năm Cá Nhân {prof['nam_hien_tai']} (Số {prof['nam_ca_nhan']}) chuyển giao sang Năm {prof['nam_hien_tai']+1} (Số {prof['nam_ca_nhan_sau']}).</p>
    <div class="months-grid">{"".join(months_cards)}</div>
  </section>

  <section class="sheet">
    <span class="eyebrow">Phần III · Chiến Lược Sự Nghiệp, Giữ Tiền &amp; Tương Hợp</span>
    <h2>Ma Trận Nghề Nghiệp, Tài Chính &amp; Đối Tác Hợp Số</h2>
    <div class="matrix-grid">
      <div class="mx-box">
        <h3>💼 Nhóm Nghề &amp; Vai Trò Kiếm Tiền Tốt Nhất</h3>
        <p style="margin:0 0 8px"><b>Lĩnh vực vượng khí (Số {esc(prof['so_chu_dao_nhan'])}):</b> {esc(cw_jobs)}.</p>
        <p style="margin:0 0 8px"><b>Vị thế phát huy tối đa:</b> {esc(cw_role)}</p>
        <p style="margin:0;color:#991B1B"><b>🛡️ Điểm rò rỉ tài chính cần khóa:</b> {esc(cw_leak)}</p>
      </div>
      <div class="mx-box">
        <h3>💞 Tương Hợp Tình Duyên &amp; Cộng Sự Làm Ăn</h3>
        <ul>
          <li><b>Nhóm số tri kỷ / hôn nhân êm ấm:</b> Con số <b>{esc(cp_love)}</b></li>
          <li><b>Nhóm số ăn ý khi hùn hạp kinh doanh:</b> Con số <b>{esc(cp_biz)}</b></li>
          <li><b>Nhóm số cần tinh tế dung hòa:</b> {esc(cp_note)}</li>
        </ul>
      </div>
      <div class="mx-box">
        <h3>✦ Thế Mạnh Bẩm Sinh Trên Biểu Đồ Ngày Sinh</h3>
        <ul>{manh_html}</ul>
      </div>
      <div class="mx-box">
        <h3>⚡ Phác Đồ Rèn Luyện Bù Đắp Trục Trống (30 Ngày)</h3>
        <ul>{trong_html}</ul>
      </div>
    </div>
  </section>
</main>
<script>
document.getElementById('bt-save-html').onclick = function(){{
  var blob = new Blob([document.documentElement.outerHTML], {{type:'text/html;charset=utf-8'}});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'cam-nang-than-so-hoc-12-thang-{slug}.html';
  a.click();
}};
</script>
</body>
</html>"""


def render_svg_to_png(svg_content: str, out_png_path: str) -> bool:
    """Xuất file SVG 1080x1350 thành ảnh PNG nét cao bằng Google Chrome headless (dùng đăng Group / trả lời Comment)."""
    tmp_html = out_png_path + ".tmp.html"
    html_doc = f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@600;700;800;900&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{width:1080px;height:1350px;overflow:hidden;background:#050B16}}</style>
</head><body>{svg_content}</body></html>"""
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html_doc)
    try:
        subprocess.run(
            [
                "google-chrome",
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1080,1350",
                f"--screenshot={out_png_path}",
                f"file://{os.path.abspath(tmp_html)}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        return os.path.exists(out_png_path)
    except Exception:
        return False
    finally:
        if os.path.exists(tmp_html):
            try:
                os.remove(tmp_html)
            except Exception:
                pass
