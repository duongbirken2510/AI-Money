#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ máy Micro-Tools Chuyển Đổi Cao (Cách 5) cho Deta AI Lab (kiemtien.deta.vn):
1. Thiết kế CV Chuẩn ATS A4 & Thư Ứng Tuyển (Tiếng Việt / Tiếng Anh / Song ngữ) — 15.000đ
2. Lập Lịch 30 Ngày Bài Đăng Bán Hàng & Kịch Bản Hook TikTok (Xuất File Excel .CSV chuẩn UTF-8 BOM) — 19.000đ
"""

import csv
import html
import io
import json
import re
import unicodedata


def _slugify(text: str) -> str:
    s = (text or "").strip().replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    asc = "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", "-", asc).strip("-")[:28] or "deta"


def _extract_json_obj(raw: str):
    if not raw:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I | re.M)
    for opener, closer in (("{", "}"), ("[", "]")):
        i1 = cleaned.find(opener)
        i2 = cleaned.rfind(closer)
        if i1 != -1 and i2 > i1:
            try:
                return json.loads(cleaned[i1 : i2 + 1])
            except Exception:
                continue
    return None


# ==============================================================================
# 1. CÔNG CỤ TẠO CV CHUẨN ATS A4 + THƯ ỨNG TUYỂN (15.000đ)
# ==============================================================================
def generate_ats_cv(
    ho_ten_lien_he: str,
    vi_tri: str,
    kinh_nghiem_tho: str,
    ngon_ngu: str,
    call_gemini_fn,
) -> dict:
    raw_contact = (ho_ten_lien_he or "Nguyễn Minh Tuấn | 0909 123 456 | minhtuan.work@gmail.com | TP.HCM").strip()
    parts_c = [p.strip() for p in re.split(r"[|·•\n]+", raw_contact) if p.strip()]
    full_name = parts_c[0] if parts_c else "Nguyễn Minh Tuấn"
    contact_line = "  •  ".join(parts_c[1:]) if len(parts_c) > 1 else "0909.xxx.xxx  •  email@domain.com  •  Việt Nam"
    target_role = (vi_tri or "Chuyên viên Phát triển Kinh doanh").strip()
    raw_exp = (kinh_nghiem_tho or "").strip()
    lang_mode = (ngon_ngu or "vi").strip()

    lang_instruction = {
        "en": "Viết TOÀN BỘ nội dung CV và Cover Letter bằng TIẾNG ANH chuyên nghiệp chuẩn ATS quốc tế (Harvard Action Verbs).",
        "song-ngu": "Viết bản CV chuẩn ATS Kết hợp Song Ngữ (Tiêu đề mục Song ngữ Việt/Anh, phần Tóm tắt và Thư ứng tuyển có cả đoạn Tiếng Việt lẫn Tiếng Anh chuyên nghiệp).",
    }.get(lang_mode, "Viết TOÀN BỘ nội dung CV và Thư ứng tuyển bằng TIẾNG VIỆT chuyên nghiệp, súc tích, giàu số liệu đo lường.")

    prompt = (
        f"Đóng vai Chuyên gia Tuyển dụng Nhân sự Cấp cao (Headhunter) tối ưu hệ thống lọc hồ sơ ATS.\n"
        f"Hãy nâng cấp thông tin thô dưới đây thành bản CV chuẩn Harvard ATS + Thư ứng tuyển (Cover Letter) sắc bén:\n"
        f"- Ứng viên: {full_name} ({contact_line})\n"
        f"- Vị trí ứng tuyển mục tiêu: {target_role}\n"
        f"- Dữ liệu kinh nghiệm/học vấn/kỹ năng thô: {raw_exp}\n"
        f"- Yêu cầu ngôn ngữ: {lang_instruction}\n\n"
        "Trả về ĐÚNG 1 JSON hợp lệ (không bọc giải thích ngoài JSON) theo cấu trúc:\n"
        "{\n"
        '  "chuc_danh": "Chức danh chuyên nghiệp khớp từ khóa ATS",\n'
        '  "tom_tat": "Đoạn tóm tắt 3-4 câu nêu bật giá trị cốt lõi & năm kinh nghiệm",\n'
        '  "kinh_nghiem": [\n'
        '    {"cong_ty": "Tên công ty / Tổ chức", "vai_tro": "Vị trí đảm nhiệm", "thoi_gian": "2023 - Hiện tại", "thanh_tich": ["Gạch đầu dòng 1 theo công thức Động từ mạnh + Hành động + Kết quả đo lường %/số liệu", "Gạch đầu dòng 2...", "Gạch đầu dòng 3..."]}\n'
        "  ],\n"
        '  "ky_nang": ["Nhóm kỹ năng 1: ...", "Nhóm kỹ năng 2: ...", "Công cụ & Ngoại ngữ: ..."],\n'
        '  "hoc_van": "Trường / Chuyên ngành / Chứng chỉ nổi bật",\n'
        '  "thu_ung_tuyen": "Bài Thư ứng tuyển (Cover Letter) 3 đoạn ngắn gọn, thuyết phục gửi Nhà tuyển dụng"\n'
        "}"
    )

    ai_raw = call_gemini_fn(
        prompt,
        "Bạn là chuyên gia viết CV chuẩn ATS Harvard. Chỉ trả về JSON hợp lệ 100%, không bịa bằng cấp sai lệch nhưng tối ưu hóa cách diễn đạt chuyên nghiệp.",
    )
    data = _extract_json_obj(ai_raw)
    if not isinstance(data, dict) or not data.get("kinh_nghiem"):
        raw_lines = [ln.strip(" -•*\t") for ln in raw_exp.splitlines() if ln.strip(" -•*\t")]
        if not raw_lines:
            raw_lines = [
                f"Trực tiếp triển khai kế hoạch chuyên môn cho vị trí {target_role}, hoàn thành vượt 115% chỉ tiêu quý.",
                "Tối ưu hóa quy trình phối hợp liên phòng ban giúp rút ngắn 25% thời gian xử lý công việc.",
                "Chủ động phân tích phản hồi khách hàng và đề xuất giải pháp cải thiện tỷ lệ giữ chân khách hàng.",
            ]
        data = {
            "chuc_danh": target_role,
            "tom_tat": f"Ứng viên định hướng kết quả ứng tuyển vị trí {target_role}, tập trung vào hiệu suất thực thi đo lường được, tư duy giải quyết vấn đề hệ thống và khả năng thích nghi nhanh với mục tiêu tăng trưởng của doanh nghiệp.",
            "kinh_nghiem": [
                {
                    "cong_ty": "Kinh nghiệm Thực chiến & Dự án Trọng điểm",
                    "vai_tro": target_role,
                    "thoi_gian": "Giai đoạn gần nhất",
                    "thanh_tich": raw_lines[:5],
                }
            ],
            "ky_nang": [
                f"Chuyên môn cốt lõi: Hoạch định & Thực thi nghiệp vụ {target_role}",
                "Kỹ năng làm việc: Phân tích số liệu, Đàm phán, Quản lý tiến độ dự án",
                "Công cụ số: Thành thạo bộ công cụ văn phòng, AI tăng năng suất & báo cáo dữ liệu",
            ],
            "hoc_van": raw_lines[-1] if len(raw_lines) > 3 else "Đại học / Cao đẳng chuyên ngành liên quan & Các khóa đào tạo nghiệp vụ thực chiến",
            "thu_ung_tuyen": (
                f"Kính gửi Anh/Chị Bộ phận Tuyển dụng,\n\n"
                f"Tôi viết thư này để bày tỏ sự quan tâm sâu sắc tới vị trí {target_role}. Với nền tảng kinh nghiệm thực chiến và tư duy bám sát hiệu quả đo lường, tôi tin tưởng mình có thể đóng góp giá trị thực tế ngay từ tháng đầu tiên nhận việc.\n\n"
                f"Rất mong có cơ hội trao đổi trực tiếp cùng Quý Công ty để trình bày cụ thể hơn kế hoạch hành động của tôi cho vị trí này.\n\nTrân trọng,\n{full_name}"
            ),
        }

    esc = lambda s: html.escape(str(s or ""))
    is_en = lang_mode == "en"
    lbl_sum = "EXECUTIVE SUMMARY" if is_en else ("EXECUTIVE SUMMARY / TÓM TẮT NĂNG LỰC" if lang_mode == "song-ngu" else "TÓM TẮT NĂNG LỰC CHUYÊN MÔN")
    lbl_exp = "PROFESSIONAL EXPERIENCE" if is_en else ("EXPERIENCE / KINH NGHIỆM LÀM VIỆC" if lang_mode == "song-ngu" else "KINH NGHIỆM LÀM VIỆC & THÀNH TÍCH")
    lbl_skl = "CORE COMPETENCIES & SKILLS" if is_en else ("SKILLS / KỸ NĂNG CHUYÊN MÔN" if lang_mode == "song-ngu" else "KỸ NĂNG & CÔNG CỤ CHUYÊN MÔN")
    lbl_edu = "EDUCATION & CERTIFICATIONS" if is_en else ("EDUCATION / HỌC VẤN & CHỨNG CHỈ" if lang_mode == "song-ngu" else "HỌC VẤN & CHỨNG CHỈ")
    lbl_cl = "TAILORED COVER LETTER" if is_en else "THƯ ỨNG TUYỂN ĐI KÈM (COVER LETTER)"

    exp_blocks = []
    for job in (data.get("kinh_nghiem") or [])[:5]:
        if not isinstance(job, dict):
            continue
        bullets = "".join(f"<li>{esc(b)}</li>" for b in (job.get("thanh_tich") or []) if b)
        exp_blocks.append(
            f"""<div class="job">
              <div class="job-head">
                <div><b>{esc(job.get('vai_tro') or target_role)}</b> · <span class="comp">{esc(job.get('cong_ty') or '')}</span></div>
                <span class="time">{esc(job.get('thoi_gian') or '')}</span>
              </div>
              <ul>{bullets}</ul>
            </div>"""
        )

    skills_html = "".join(f"<li>{esc(sk)}</li>" for sk in (data.get("ky_nang") or []) if sk)
    cl_paras = "".join(f"<p>{esc(p.strip())}</p>" for p in str(data.get("thu_ung_tuyen") or "").splitlines() if p.strip())
    slug = _slugify(full_name + "-" + target_role)

    def _render_cv(is_preview: bool) -> str:
        wm_css = ""
        wm_div = ""
        toolbar = ""
        cl_section = ""
        if is_preview:
            wm_css = """
            .wm-overlay{position:fixed;inset:0;pointer-events:none;z-index:20;display:grid;place-items:center;overflow:hidden}
            .wm-overlay span{transform:rotate(-26deg);font:900 24px/1.4 'Be Vietnam Pro',sans-serif;color:rgba(15,23,42,.08);text-align:center;letter-spacing:.12em;white-space:nowrap;user-select:none}
            .locked-cl{filter:blur(4.5px);user-select:none;opacity:.55;pointer-events:none}
            """
            wm_div = '<div class="wm-overlay"><span>BẢN XEM TRƯỚC MIỄN PHÍ · KIEMTIEN.DETA.VN<br>MỞ KHÓA BẢN IN A4 / PDF SẠCH 15.000Đ</span></div>'
            toolbar = '<div class="tb preview-tb">👀 <b>Bản xem trước CV chuẩn ATS Harvard</b> — Quét <b>15.000đ</b> bên dưới để xóa watermark, sửa chữ trực tiếp &amp; xuất PDF A4 sạch!</div>'
            cl_section = f'<section class="sec"><h2 class="sec-t">{esc(lbl_cl)} (Mở khóa cùng bản đầy đủ)</h2><div class="locked-cl">{cl_paras}</div></section>'
        else:
            toolbar = f"""<div class="tb">
              <div><b>📄 CV Chuẩn ATS A4 — {esc(full_name)}</b> <span style="font-size:12px;opacity:.82">(Bản sạch 100% · Nhấn "Sửa chữ" nếu muốn tinh chỉnh trước khi Lưu PDF)</span></div>
              <div class="tb-act">
                <button type="button" class="btn btn-edit" id="bt-edit">✏️ Bật sửa chữ trực tiếp</button>
                <button type="button" class="btn btn-main" onclick="window.print()">🖨️ In A4 / Lưu thành File PDF</button>
                <button type="button" class="btn btn-edit" id="bt-dl">⬇️ Tải file .HTML</button>
              </div>
            </div>"""
            cl_section = f'<section class="sheet cl-sheet"><h2 class="sec-t">{esc(lbl_cl)}</h2><div class="cl-body">{cl_paras}</div></section>'

        script_edit = "" if is_preview else f"""<script>
        (function(){{
          var ed = false, bt = document.getElementById('bt-edit'), areas = document.querySelectorAll('.sheet');
          if(bt) bt.onclick = function(){{
            ed = !ed;
            areas.forEach(function(a){{ a.contentEditable = ed ? 'true' : 'false'; a.style.outline = ed ? '2px dashed #10B981' : 'none'; }});
            bt.textContent = ed ? '✅ Đang bật sửa chữ (Bấm để khóa)' : '✏️ Bật sửa chữ trực tiếp';
          }};
          var dl = document.getElementById('bt-dl');
          if(dl) dl.onclick = function(){{
            areas.forEach(function(a){{ a.contentEditable = 'false'; a.style.outline = 'none'; }});
            var blob = new Blob([document.documentElement.outerHTML], {{type:'text/html;charset=utf-8'}});
            var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'cv-ats-{slug}.html'; a.click();
          }};
        }})();
        </script>"""

        return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CV ATS — {esc(full_name)} — {esc(data.get('chuc_danh') or target_role)}</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;background:#E2E8F0;color:#0F172A;font:400 13.8px/1.58 "Be Vietnam Pro",system-ui,sans-serif}}
  .tb{{position:sticky;top:0;z-index:30;background:#0F172A;color:#F8FAFC;padding:10px 18px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;font-size:13px}}
  .preview-tb{{background:linear-gradient(90deg,#065F46,#0F172A);justify-content:center;text-align:center}}
  .tb-act{{display:flex;gap:8px;flex-wrap:wrap}}
  .btn{{border:0;border-radius:999px;padding:8px 14px;font:700 12.5px/1 "Be Vietnam Pro",sans-serif;cursor:pointer}}
  .btn-main{{background:#10B981;color:#fff}}
  .btn-edit{{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.24)}}
  .wrap{{max-width:810px;margin:20px auto 48px;padding:0 12px}}
  .sheet{{background:#FFFFFF;padding:38px 44px;border-radius:6px;box-shadow:0 12px 30px rgba(15,23,42,.12);margin-bottom:20px}}
  .cv-head{{border-bottom:2.2px solid #0F172A;padding-bottom:12px;margin-bottom:16px}}
  .cv-head h1{{margin:0;font-size:25px;font-weight:800;letter-spacing:-.01em;text-transform:uppercase;color:#0F172A}}
  .cv-role{{font-size:15px;font-weight:700;color:#047857;margin:3px 0 6px}}
  .cv-contact{{font-size:12.6px;color:#334155}}
  .sec{{margin-bottom:15px}}
  .sec-t{{font-size:12.5px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#0F172A;border-bottom:1px solid #CBD5E1;padding-bottom:4px;margin:0 0 9px}}
  .job{{margin-bottom:12px}}
  .job-head{{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:4px}}
  .comp{{font-weight:600;color:#1E293B}}
  .time{{font-size:12.4px;font-weight:700;color:#475569}}
  ul{{margin:4px 0 0;padding-left:18px}}
  li{{margin-bottom:4px}}
  .cl-body p{{margin:0 0 11px;text-align:justify}}
  {wm_css}
  @media (max-width:600px){{.sheet{{padding:22px 18px}}}}
  @media print{{
    body{{background:#fff;font-size:11pt}}
    .tb,.wm-overlay{{display:none!important}}
    .wrap{{max-width:100%;margin:0;padding:0}}
    .sheet{{box-shadow:none;padding:0;margin:0;border-radius:0}}
    .cl-sheet{{page-break-before:always;padding-top:12pt}}
  }}
</style>
</head>
<body>
{toolbar}
{wm_div}
<div class="wrap">
  <article class="sheet">
    <header class="cv-head">
      <h1>{esc(full_name)}</h1>
      <div class="cv-role">{esc(data.get('chuc_danh') or target_role)}</div>
      <div class="cv-contact">{esc(contact_line)}</div>
    </header>
    <section class="sec">
      <h2 class="sec-t">{esc(lbl_sum)}</h2>
      <p style="margin:0;text-align:justify">{esc(data.get('tom_tat') or '')}</p>
    </section>
    <section class="sec">
      <h2 class="sec-t">{esc(lbl_exp)}</h2>
      {"".join(exp_blocks)}
    </section>
    <section class="sec">
      <h2 class="sec-t">{esc(lbl_skl)}</h2>
      <ul>{skills_html}</ul>
    </section>
    <section class="sec" style="margin-bottom:0">
      <h2 class="sec-t">{esc(lbl_edu)}</h2>
      <p style="margin:0">{esc(data.get('hoc_van') or '')}</p>
    </section>
    {cl_section if is_preview else ''}
  </article>
  {'' if is_preview else cl_section}
</div>
{script_edit}
</body>
</html>"""

    return {
        "full_name": full_name,
        "target_role": target_role,
        "slug": slug,
        "preview_html": _render_cv(is_preview=True),
        "clean_html": _render_cv(is_preview=False),
    }


# ==============================================================================
# 2. CÔNG CỤ LỊCH 30 NGÀY BÀI ĐĂNG BÁN HÀNG & HOOK TIKTOK (.CSV EXCEL — 19.000đ)
# ==============================================================================
PILLAR_CYCLE = [
    ("🎯 Chạm nỗi đau khách hàng", "20:00"),
    ("💡 Giải pháp & Giá trị khác biệt", "11:45"),
    ("⭐ Bằng chứng & Feedback thật", "19:30"),
    ("🎬 Hậu trường / Quy trình uy tín", "12:15"),
    ("🛡️ Giải đáp & Xóa rào cản mua", "20:15"),
    ("🔥 Chốt đơn & Ưu đãi giới hạn", "20:30"),
]


def _fallback_30_days(ten_shop: str, khach_hang: str, kenh_chinh: str) -> list[dict]:
    angles = [
        ("Sai lầm khiến 80% người mua mất tiền oan", "Mở đầu bằng 1 hiểu lầm phổ biến nhất khi khách chọn mua; chỉ ra 3 dấu hiệu nhận biết hàng chuẩn tại {shop}."),
        ("3 lý do {shop} được khách cũ quay lại", "So sánh trực quan trước & sau khi trải nghiệm; nhấn mạnh điểm mạnh cốt lõi: {kh}."),
        ("Câu chuyện khách hàng thật tuần qua", "Kể lại 1 tình huống khách từng đắn đo, sau khi dùng đã phản hồi tích cực thế nào."),
        ("Bên trong quy trình chuẩn bị mỗi đơn hàng", "Quay cận cảnh 15 giây khâu kiểm tra chất lượng / đóng gói tỉ mỉ trước khi giao tới tay khách."),
        ("Đắt hay rẻ? Bài toán chia nhỏ chi phí mỗi ngày", "Phân tích chi phí sử dụng thực tế mỗi ngày cực tiết kiệm so với giá trị bền bỉ nhận được."),
        ("Ưu đãi mở hàng cho 15 khách nhắn tin sớm nhất", "Tóm tắt combo bán chạy nhất + quà tặng kèm khi để lại bình luận hoặc nhắn Zalo hôm nay."),
    ]
    rows = []
    for d in range(1, 31):
        pil, hr = PILLAR_CYCLE[(d - 1) % len(PILLAR_CYCLE)]
        ang_title, ang_body = angles[(d - 1) % len(angles)]
        week_no = ((d - 1) // 7) + 1
        rows.append(
            {
                "ngay": f"Ngày {d:02d}",
                "tru_cot": pil,
                "kenh": kenh_chinh,
                "tieu_de": f"[Tuần {week_no}] {ang_title.format(shop=ten_shop)} — {ten_shop}",
                "hook_dan_y": ang_body.format(shop=ten_shop, kh=khach_hang[:90]),
                "cta": f"Nhắn ngay cho {ten_shop} hoặc bấm link đầu trang để nhận tư vấn & ưu đãi hôm nay!",
                "gio_dang": hr,
            }
        )
    return rows


def generate_30day_calendar(
    ten_shop: str,
    khach_hang: str,
    kenh_chinh: str,
    call_gemini_fn,
) -> dict:
    shop = (ten_shop or "Thương hiệu của bạn").strip()
    kh = (khach_hang or "Khách hàng quan tâm chất lượng thật, giá hợp lý và dịch vụ tận tâm").strip()
    kenh_label = {
        "tiktok": "TikTok / Reels ngắn",
        "facebook": "Fanpage & Facebook cá nhân",
    }.get((kenh_chinh or "").strip(), "Fanpage Facebook + TikTok")

    prompt = (
        f"Đóng vai Giám đốc Nội dung Chuyển đổi cao (Growth Content Strategist).\n"
        f"Hãy lập BẢNG LỊCH 30 NGÀY ĐĂNG BÀI BÁN HÀNG & KỊCH BẢN HOOK 3 GIÂY (từ Ngày 01 đến Ngày 30, không trùng lặp ý) cho:\n"
        f"- Tên Shop / Sản phẩm: {shop}\n"
        f"- Khách hàng mục tiêu, điểm mạnh & giá bán: {kh}\n"
        f"- Kênh triển khai: {kenh_label}\n\n"
        "Trả về ĐÚNG 1 mảng JSON gồm 30 phần tử (không bọc lời dẫn ngoài JSON), mỗi phần tử có cấu trúc:\n"
        '{"ngay":"Ngày 01","tru_cot":"Chạm nỗi đau / Hậu trường / Feedback / Chốt đơn...","tieu_de":"Tiêu đề giật tít cụ thể gắn đúng sản phẩm","hook_dan_y":"Câu Hook 3 giây đầu giữ chân + 3 ý triển khai bài viết/video","cta":"Câu kêu gọi hành động ra đơn","gio_dang":"20:00"}'
    )
    ai_raw = call_gemini_fn(
        prompt,
        "Bạn là chuyên gia lập kế hoạch nội dung 30 ngày thực chiến tại Việt Nam. Trả về đúng mảng JSON 30 phần tử.",
    )
    parsed = _extract_json_obj(ai_raw)
    fb_rows = _fallback_30_days(shop, kh, kenh_label)

    final_rows = []
    if isinstance(parsed, list) and len(parsed) >= 6:
        for i in range(30):
            if i < len(parsed) and isinstance(parsed[i], dict) and parsed[i].get("tieu_de"):
                it = parsed[i]
                final_rows.append(
                    {
                        "ngay": f"Ngày {i+1:02d}",
                        "tru_cot": str(it.get("tru_cot") or fb_rows[i]["tru_cot"]).strip(),
                        "kenh": kenh_label,
                        "tieu_de": str(it.get("tieu_de") or fb_rows[i]["tieu_de"]).strip(),
                        "hook_dan_y": str(it.get("hook_dan_y") or it.get("dan_y") or fb_rows[i]["hook_dan_y"]).strip(),
                        "cta": str(it.get("cta") or fb_rows[i]["cta"]).strip(),
                        "gio_dang": str(it.get("gio_dang") or fb_rows[i]["gio_dang"]).strip(),
                    }
                )
            else:
                final_rows.append(fb_rows[i])
    else:
        final_rows = fb_rows

    # 1. Xuất CSV chuẩn UTF-8 BOM mở trực tiếp trên Microsoft Excel & Google Sheets không lỗi dấu tiếng Việt
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Ngày",
            "Trụ cột chuyển đổi",
            "Kênh triển khai",
            "Tiêu đề bài đăng / Video",
            "Câu Hook 3 giây đầu & Dàn ý triển khai chi tiết",
            "Kêu gọi hành động (CTA)",
            "Khung giờ vàng",
            "Trạng thái đăng",
        ]
    )
    def _safe_csv_cell(v) -> str:
        s = str(v or "")
        if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + s
        return s

    for r in final_rows:
        writer.writerow(
            [
                _safe_csv_cell(r["ngay"]),
                _safe_csv_cell(r["tru_cot"]),
                _safe_csv_cell(r["kenh"]),
                _safe_csv_cell(r["tieu_de"]),
                _safe_csv_cell(r["hook_dan_y"]),
                _safe_csv_cell(r["cta"]),
                _safe_csv_cell(r["gio_dang"]),
                "[ ] Chưa đăng",
            ]
        )
    csv_utf8_bom = "\ufeff" + buf.getvalue()

    esc = lambda s: html.escape(str(s or ""))

    def _render_table_html(is_preview: bool) -> str:
        visible = final_rows[:6] if is_preview else final_rows
        trs = []
        for r in visible:
            trs.append(
                f"""<tr>
                  <td style="font-weight:800;white-space:nowrap;color:#10B981">{esc(r['ngay'])}<div style="font-size:11px;color:#64748B;font-weight:600">⏰ {esc(r['gio_dang'])}</div></td>
                  <td><span class="pill">{esc(r['tru_cot'])}</span></td>
                  <td><b>{esc(r['tieu_de'])}</b><div class="hook">{esc(r['hook_dan_y'])}</div><div class="cta">👉 CTA: {esc(r['cta'])}</div></td>
                </tr>"""
            )
        if is_preview:
            for r in final_rows[6:10]:
                trs.append(
                    f"""<tr class="blur-row">
                      <td style="font-weight:800">{esc(r['ngay'])}</td>
                      <td><span class="pill">{esc(r['tru_cot'])}</span></td>
                      <td><b>{esc(r['tieu_de'][:38])}…</b><div class="hook">Nội dung chi tiết Ngày 07 → Ngày 30 &amp; File Excel (.CSV) mở khóa tự động sau khi quét 19.000đ…</div></td>
                    </tr>"""
                )
        return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lịch 30 Ngày Nội Dung Bán Hàng — {esc(shop)}</title>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;background:#080F1E;color:#F1F5F9;font:400 13.8px/1.55 "Be Vietnam Pro",system-ui,sans-serif;padding:16px}}
  .head{{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px;padding:12px 16px;border-radius:14px;background:#111C30;border:1px solid rgba(16,185,129,.35)}}
  table{{width:100%;border-collapse:collapse;background:#0D1628;border-radius:14px;overflow:hidden;border:1px solid rgba(148,163,184,.18)}}
  th,td{{padding:11px 13px;text-align:left;vertical-align:top;border-bottom:1px solid rgba(148,163,184,.14)}}
  th{{background:#132038;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#94A3B8}}
  .pill{{display:inline-block;padding:4px 9px;border-radius:999px;background:rgba(16,185,129,.14);color:#34D399;font-size:12px;font-weight:700;white-space:nowrap}}
  .hook{{margin-top:4px;color:#CBD5E1;font-size:13.2px}}
  .cta{{margin-top:4px;color:#FBBF24;font-size:12.4px;font-weight:600}}
  .blur-row{{filter:blur(3.8px);opacity:.55;user-select:none}}
</style>
</head>
<body>
  <div class="head">
    <div><b style="color:#34D399">📅 Kế Hoạch 30 Ngày Nội Dung &amp; Kịch Bản Hook — {esc(shop)}</b><div style="font-size:12px;color:#94A3B8">Kênh: {esc(kenh_label)} · {'Đang hiển thị miễn phí 6/30 ngày đầu' if is_preview else 'Trọn bộ 30/30 ngày đã mở khóa'}</div></div>
  </div>
  <table>
    <thead><tr><th>Ngày</th><th>Trụ cột</th><th>Tiêu đề, Hook 3s &amp; Dàn ý triển khai</th></tr></thead>
    <tbody>{"".join(trs)}</tbody>
  </table>
</body>
</html>"""

    return {
        "shop": shop,
        "slug": _slugify(shop),
        "rows_count": len(final_rows),
        "preview_html": _render_table_html(is_preview=True),
        "full_board_html": _render_table_html(is_preview=False),
        "csv_utf8_bom": csv_utf8_bom,
    }
