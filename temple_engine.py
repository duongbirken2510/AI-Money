#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Động cơ phụ trợ cho Không Gian Tĩnh Tâm 3D — Liên Hoa Các (/chua-online).
Bao gồm:
1. Quản lý phòng trực tuyến (Multiplayer Presence tối đa 100 người/phòng, chỉ chào bằng 4 câu có sẵn).
2. Hồ Sen Hoa Đăng Ước Nguyện (Miễn phí 0đ & Đèn Hoa Đăng Hoàng Kim qua SePay).
3. Gieo Quẻ Bình An & Tỉnh Thức (Kết hợp thơ quẻ cổ truyền + lời khuyên chữa lành cá nhân hóa).
4. Tính ngày Âm lịch & đếm ngược Rằm / Mùng 1.
"""
import datetime
import html
import math
import random
import re
import sqlite3
import threading
import time

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))
ROOM_LOCK = threading.Lock()

# Lưu trạng thái người đang ở trong sân chùa (tự dọn sau 120 giây không hoạt động)
ACTIVE_VISITORS: dict[str, dict] = {}
GLOBAL_COUNTERS = {
    "tieng_chuong": 1284,
    "nhip_mo": 18420,
    "luot_thap_huong": 946,
    "last_bell_ts": 0.0,
    "last_bell_by": "Mây Thong Thả",
}

PRESET_GREETINGS = {
    "adidaphat": "🙏 A Di Đà Phật",
    "binhan": "🪷 Chúc đạo hữu thân tâm thường an lạc",
    "taman": "✨ Tâm an vạn sự an",
    "hoanhy": "🍃 Hoan hỷ hữu duyên gặp nhau nơi cửa thiền",
}

BAD_WORDS_FILTER = [
    "tài xỉu", "cờ bạc", "casino", "nhà cái", "lô đề", "cá độ", "kubet", "sex", "18+", "porn",
    "địt", "đụ", "lồn", "cặc", "ngu", "chết", "giết", "lừa đảo", "vay nóng",
]

# Các đạo hữu tĩnh lặng mặc định trong sân chùa để không gian luôn ấm áp kể cả lúc nửa đêm
AMBIENT_PRACTITIONERS = [
    {"id": "npc_1", "phap_danh": "Mây Thong Thả", "ao_mau": "#D97706", "x": -2.4, "z": -4.5, "hanh_dong": "ngoi-thien", "loi_chao": "🙏 A Di Đà Phật"},
    {"id": "npc_2", "phap_danh": "Lá Bồ Đề", "ao_mau": "#64748B", "x": 1.4, "z": -0.6, "hanh_dong": "thap-huong", "loi_chao": "✨ Tâm an vạn sự an"},
    {"id": "npc_3", "phap_danh": "Trăng Tĩnh Lặng", "ao_mau": "#8B5CF6", "x": -3.4, "z": 1.8, "hanh_dong": "ngam-sen", "loi_chao": "🪷 Chúc đạo hữu thân tâm thường an lạc"},
    {"id": "npc_4", "phap_danh": "Sương Mai", "ao_mau": "#0D9488", "x": 4.5, "z": 1.5, "hanh_dong": "thinh-chuong", "loi_chao": "🍃 Hoan hỷ hữu duyên gặp nhau nơi cửa thiền"},
]

SEED_LANTERNS = [
    {
        "phap_danh": "Tâm An Nhiên",
        "loi_nguyen": "Cầu mong cha mẹ hai bên luôn mạnh khỏe, bình an, tâm trí minh mẫn mỗi ngày.",
        "loai": "hoang-kim",
        "so_tien": 20000,
        "mau_sac": "#F59E0B",
        "luot_chap_tay": 48,
    },
    {
        "phap_danh": "Mây Thong Thả",
        "loi_nguyen": "Nguyện cho công việc tháng mới hanh thông, gặp người tử tế, giữ tâm sáng trước mọi thử thách.",
        "loai": "hoang-kim",
        "so_tien": 10000,
        "mau_sac": "#F59E0B",
        "luot_chap_tay": 35,
    },
    {
        "phap_danh": "Lá Bồ Đề",
        "loi_nguyen": "Mong mọi người ghé qua không gian tĩnh tâm này đều buông bỏ được muộn phiền và ngủ một giấc thật sâu.",
        "loai": "thuong",
        "so_tien": 0,
        "mau_sac": "#F472B6",
        "luot_chap_tay": 29,
    },
    {
        "phap_danh": "Hạt Nắng Sớm",
        "loi_nguyen": "Cầu bình an cho gia đình nhỏ, con cái ngoan ngoãn khỏe mạnh, thuận vợ thuận chồng.",
        "loai": "thuong",
        "so_tien": 0,
        "mau_sac": "#38BDF8",
        "luot_chap_tay": 19,
    },
    {
        "phap_danh": "Khói Lam Chiều",
        "loi_nguyen": "Nguyện học cách thở sâu, bớt nóng giận, biết trân trọng những điều giản dị đang có.",
        "loai": "thuong",
        "so_tien": 0,
        "mau_sac": "#A78BFA",
        "luot_chap_tay": 22,
    },
]

# Bộ 16 Quẻ Bình An & Tỉnh Thức (Cổ phong + Chữa lành)
QUE_BINH_AN = [
    {
        "so": 1,
        "ten": "Quẻ Số 01 · Liên Hoa Khai Nở (Thượng Thượng Cát)",
        "cap": "Thượng Thượng Cát",
        "tho": "Sen vươn khỏi bùn tối,\nĐón nắng sớm tinh khôi.\nBao ngày dài kiên nhẫn,\nHoa thơm nở giữa đời.",
        "y_nghia": "Mọi nỗ lực âm thầm và sự lương thiện của bạn trong thời gian qua đang bước vào mùa kết trái. Giống như hoa sen vượt qua tầng nước lạnh để chạm ánh mặt trời, khó khăn hiện tại chỉ là bước đệm cuối cùng trước khi vận hội sáng mở ra.",
        "hanh_dong": [
            "Giữ vững kế hoạch đang làm, không cần hoang mang trước lời bàn ra tán vào.",
            "Dành 10 phút tối nay dọn dẹp bàn làm việc sạch thoáng để đón năng lượng mới.",
            "Nói một lời cảm ơn hoặc hỏi thăm người thân đã luôn âm thầm ủng hộ bạn."
        ]
    },
    {
        "so": 8,
        "ten": "Quẻ Số 08 · Thuận Thủy Hành Chu (Thượng Cát)",
        "cap": "Thượng Cát",
        "tho": "Thuyền xuôi theo dòng biếc,\nGió mát đẩy buồm căng.\nChẳng cần gồng ngược sóng,\nBến bình yên đã gần.",
        "y_nghia": "Bạn đang tự gây áp lực quá lớn vì muốn kiểm soát mọi thứ theo ý mình. Quẻ này nhắc bạn hãy học tính mềm mại của nước: cái gì hợp tự nhiên thì giữ, cái gì quá gượng ép hãy nhẹ nhàng buông xuống, tự khắc quý nhân và lối ra sẽ xuất hiện.",
        "hanh_dong": [
            "Tạm gác lại 1 việc chưa thực sự cấp bách để cho tâm trí được nghỉ ngơi tối nay.",
            "Khi giao tiếp trong công việc ngày mai, hãy lắng nghe nhiều hơn phản biện.",
            "Uống một cốc nước ấm và hít thở sâu 5 nhịp trước khi bắt đầu ngày mới."
        ]
    },
    {
        "so": 12,
        "ten": "Quẻ Số 12 · Vân Khai Kiến Nguyệt (Thượng Cát)",
        "cap": "Thượng Cát",
        "tho": "Mây mù dần tan biến,\nTrăng sáng tỏ giữa trời.\nLòng người thôi bối rối,\nĐường trước mắt thảnh thơi.",
        "y_nghia": "Sự hiểu lầm, bế tắc hoặc cảm giác mông lung mà bạn đang trăn trở sắp được tháo gỡ rõ ràng. Ánh trăng vốn vẫn luôn ở đó, chỉ bị mây che tạm thời. Khi tâm bạn lắng lại như mặt hồ không gợn sóng, câu trả lời đúng đắn nhất sẽ tự hiện ra.",
        "hanh_dong": [
            "Viết 3 điều đang làm bạn lo lắng nhất ra giấy — bạn sẽ thấy chúng nhỏ hơn khi nằm trong đầu.",
            "Chủ động mở lời hòa giải hoặc làm rõ thông tin thay vì tự suy đoán.",
            "Đi ngủ trước 23h30 tối nay để trí não phục hồi sự minh mẫn."
        ]
    },
    {
        "so": 18,
        "ten": "Quẻ Số 18 · Tùng Bách Vững Vàng (Cát Lành)",
        "cap": "Cát Lành",
        "tho": "Gió sương lay chẳng đổ,\nRễ bám chặt đá xanh.\nĐợi xuân về ấm áp,\nLộc biếc trổ đầy cành.",
        "y_nghia": "Giai đoạn này đòi hỏi ở bạn sự bền bỉ và tĩnh tại như cây tùng trên núi. Chưa phải lúc vội vàng chạy theo lợi ích ngắn hạn hay thay đổi đột ngột; hãy củng cố sức khỏe, rèn kỹ năng gốc và tích lũy nội lực.",
        "hanh_dong": [
            "Tập trung hoàn thành trọn vẹn từng việc nhỏ thay vì ôm đồm nhiều việc cùng lúc.",
            "Kiểm soát chi tiêu hợp lý trong tuần này, ưu tiên tích lũy an toàn.",
            "Dành 15 phút đi bộ hoặc vận động nhẹ để giải phóng năng lượng ứ đọng."
        ]
    },
    {
        "so": 24,
        "ten": "Quẻ Số 24 · Xuân Vũ Nhuận Mộc (Thượng Cát)",
        "cap": "Thượng Cát",
        "tho": "Mưa xuân rơi thấm đất,\nMầm khô bỗng hóa xanh.\nQuý nhân từ phương tới,\nViệc khó hóa việc lành.",
        "y_nghia": "Bạn sắp nhận được một sự trợ giúp quý giá hoặc một tin vui bất ngờ từ người có kinh nghiệm. Những thiện cảm bạn từng gieo trồng trước đây nay quay trở lại nâng đỡ bạn đúng lúc cần thiết nhất.",
        "hanh_dong": [
            "Đừng ngại mở lời xin lời khuyên từ người đi trước mà bạn tin tưởng.",
            "Giữ thái độ khiêm tốn, chân thành trong mọi cuộc gặp gỡ tuần này.",
            "Gieo một hạt giống thiện lành nhỏ: giúp đỡ một người đang lúng túng quanh bạn."
        ]
    },
    {
        "so": 33,
        "ten": "Quẻ Số 33 · Minh Châu Xuất Hải (Đại Cát)",
        "cap": "Thượng Thượng Cát",
        "tho": "Ngọc sáng nơi biển thẳm,\nĐến ngày tỏa hào quang.\nTâm thành trời chẳng phụ,\nPhúc lộc tự tìm sang.",
        "y_nghia": "Giá trị thực sự và sự tận tâm của bạn sắp được ghi nhận xứng đáng. Dù trước đó bạn có cảm giác công sức mình bỏ ra chưa ai thấy, thì sắp tới chính năng lực thật sẽ giúp bạn tỏa sáng bền vững.",
        "hanh_dong": [
            "Tự tin trình bày ý tưởng hoặc sản phẩm tâm huyết của bạn ra ánh sáng.",
            "Giữ chữ tín tuyệt đối trong từng lời hứa nhỏ nhất với khách hàng và đồng nghiệp.",
            "Dành thời gian buổi tối tĩnh tâm đọc vài trang sách hoặc nghe tiếng chuông thiền."
        ]
    },
    {
        "so": 42,
        "ten": "Quẻ Số 42 · Thanh Phong Tẩy Trần (Bình An Chuyển Hóa)",
        "cap": "Thượng Bình An",
        "tho": "Gió thanh lay trúc biếc,\nBụi trần nhẹ bay đi.\nChuyện qua đừnguyến tiếc,\nAn nhiên bước xuân thì.",
        "y_nghia": "Quẻ nhắc bạn hãy tha thứ cho những thiếu sót đã qua của bản thân và người khác. Đừng mang chiếc ba-lô chứa đầy chuyện cũ của ngày hôm qua để bước vào ngày mai tươi sáng.",
        "hanh_dong": [
            "Thở ra thật chậm và tự nhủ: 'Mình cho phép bản thân được bình an ngay lúc này'.",
            "Tắt thông báo mạng xã hội 30 phút trước khi ngủ để tâm không bị xao động.",
            "Trân trọng sức khỏe hiện tại — có sức khỏe và sự bình tĩnh là có tất cả."
        ]
    },
    {
        "so": 56,
        "ten": "Quẻ Số 56 · Bách Điểu Quy Lâm (Gia Đạo & Tâm An)",
        "cap": "Thượng Cát",
        "tho": "Chim mỏi cánh về tổ,\nĐèn ấm sáng hiên nhà.\nNgoài kia bao giông bão,\nVề đây hóa thuận hòa.",
        "y_nghia": "Năng lượng may mắn lớn nhất của bạn lúc này nằm ở sự gắn kết gia đình và không gian sống ấm áp. Khi hậu phương và nội tâm yên ổn, mọi việc bên ngoài dù phức tạp đến đâu cũng sẽ tự khắc đi vào quỹ đạo.",
        "hanh_dong": [
            "Ăn một bữa cơm trọn vẹn, không nhìn màn hình điện thoại cùng người thân.",
            "Lắng nghe tâm sự của người nhà bằng sự kiên nhẫn và bao dung.",
            "Thắp một nén hương tâm hoặc thả một chiếc đèn hoa đăng cầu an cho gia đình."
        ]
    },
]


def ensure_temple_tables(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS temple_lanterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_don TEXT DEFAULT '',
            phap_danh TEXT,
            loi_nguyen TEXT,
            loai TEXT DEFAULT 'thuong',
            so_tien INTEGER DEFAULT 0,
            mau_sac TEXT DEFAULT '#F472B6',
            luot_chap_tay INTEGER DEFAULT 1,
            tao_luc TEXT
        )"""
    )
    c.execute("SELECT COUNT(*) FROM temple_lanterns")
    if (c.fetchone()[0] or 0) == 0:
        now_str = datetime.datetime.now(VN_TZ).isoformat(timespec="seconds")
        for s in SEED_LANTERNS:
            c.execute(
                """INSERT INTO temple_lanterns
                (ma_don, phap_danh, loi_nguyen, loai, so_tien, mau_sac, luot_chap_tay, tao_luc)
                VALUES ('SEED', ?, ?, ?, ?, ?, ?, ?)""",
                (s["phap_danh"], s["loi_nguyen"], s["loai"], s["so_tien"], s["mau_sac"], s["luot_chap_tay"], now_str),
            )
    conn.commit()


def is_clean_text(txt: str) -> bool:
    low = (txt or "").lower()
    for bw in BAD_WORDS_FILTER:
        if bw in low:
            return False
    return True


def get_lunar_info_today() -> dict:
    """Tính xấp xỉ chính xác ngày Âm lịch Việt Nam theo chu kỳ Giao hội Mặt Trăng (Synodic Month 29.530588 ngày)."""
    now = datetime.datetime.now(VN_TZ)
    # Mốc chuẩn: 2026-02-17 là Mùng 1 Tết Bính Ngọ (1/1 Âm lịch)
    anchor = datetime.datetime(2026, 2, 17, 0, 0, 0, tzinfo=VN_TZ)
    diff_days = (now - anchor).total_seconds() / 86400.0
    synodic = 29.530588853
    lunations = int(math.floor(diff_days / synodic))
    day_in_month = int(math.floor(diff_days - lunations * synodic)) + 1
    day_in_month = max(1, min(30, day_in_month))
    lunar_month = ((lunations) % 12) + 1

    if day_in_month == 1:
        dip_dac_biet = "🌕 Hôm nay là ngày Mùng 1 đầu tháng Âm lịch — Ngày đại cát để thắp hương, thả hoa đăng & cầu bình an!"
    elif day_in_month == 15:
        dip_dac_biet = "🌕 Hôm nay là ngày Rằm (15 Âm lịch) — Trăng tròn viên mãn, rất tốt để tụng kinh, gõ mõ & cầu an!"
    elif day_in_month < 15:
        con = 15 - day_in_month
        dip_dac_biet = f"🌙 Còn {con} ngày nữa là tới ngày Rằm (15/{lunar_month} Âm lịch)"
    else:
        con = 30 - day_in_month + 1
        dip_dac_biet = f"🌙 Còn khoảng {con} ngày nữa là tới Mùng 1 tháng sau"

    can_chi_nam = "Bính Ngọ"
    return {
        "duong_lich": now.strftime("%d/%m/%Y"),
        "am_lich": f"Ngày {day_in_month} tháng {lunar_month} năm {can_chi_nam} (Âm lịch)",
        "ngay_am": day_in_month,
        "thang_am": lunar_month,
        "dip_dac_biet": dip_dac_biet,
    }


def update_visitor_presence(
    vid: str,
    phap_danh: str,
    ao_mau: str,
    x: float,
    z: float,
    hanh_dong: str,
    ma_chao: str,
    so_mo_cong_them: int = 0,
) -> dict:
    now_ts = time.time()
    clean_pd = html.escape((phap_danh or "Mây Thong Thả").strip()[:26])
    if not is_clean_text(clean_pd):
        clean_pd = "Đạo Hữu An Nhiên"
    clean_ao = ao_mau if re.match(r"^#[0-9a-fA-F]{6}$", ao_mau or "") else "#D97706"
    x_clamped = max(-14.0, min(14.0, float(x or 0.0)))
    z_clamped = max(-14.0, min(14.0, float(z or 4.0)))
    hd = (hanh_dong or "di-dao").strip()[:24]
    loi_chao = PRESET_GREETINGS.get(ma_chao, "")

    with ROOM_LOCK:
        # Dọn người rời đi quá 120s
        expired = [k for k, v in ACTIVE_VISITORS.items() if now_ts - v.get("ts", 0) > 120]
        for k in expired:
            ACTIVE_VISITORS.pop(k, None)
        if len(ACTIVE_VISITORS) >= 250 and vid not in ACTIVE_VISITORS:
            oldest_k = min(ACTIVE_VISITORS.keys(), key=lambda k: ACTIVE_VISITORS[k].get("ts", 0))
            ACTIVE_VISITORS.pop(oldest_k, None)

        prev = ACTIVE_VISITORS.get(vid, {})
        if not loi_chao and (now_ts - prev.get("chao_ts", 0) < 25):
            loi_chao = prev.get("loi_chao", "")
        chao_ts = now_ts if ma_chao in PRESET_GREETINGS else prev.get("chao_ts", 0)

        if hd == "thinh-chuong" and (now_ts - GLOBAL_COUNTERS["last_bell_ts"] > 2.0):
            GLOBAL_COUNTERS["tieng_chuong"] += 1
            GLOBAL_COUNTERS["last_bell_ts"] = now_ts
            GLOBAL_COUNTERS["last_bell_by"] = clean_pd
        elif hd == "thap-huong" and prev.get("hanh_dong") != "thap-huong":
            GLOBAL_COUNTERS["luot_thap_huong"] += 1

        if so_mo_cong_them > 0:
            GLOBAL_COUNTERS["nhip_mo"] += min(50, int(so_mo_cong_them))

        ACTIVE_VISITORS[vid] = {
            "id": vid,
            "phap_danh": clean_pd,
            "ao_mau": clean_ao,
            "x": round(x_clamped, 2),
            "z": round(z_clamped, 2),
            "hanh_dong": hd,
            "loi_chao": loi_chao,
            "chao_ts": chao_ts,
            "ts": now_ts,
        }

        online = list(ACTIVE_VISITORS.values())[:90]
        # Luôn ghép cùng các đạo hữu tĩnh lặng trong sân chùa
        all_avatars = AMBIENT_PRACTITIONERS + online
        return {
            "avatars": all_avatars,
            "so_nguoi_trong_chua": len(all_avatars),
            "counters": dict(GLOBAL_COUNTERS),
        }


def get_temple_state(conn: sqlite3.Connection) -> dict:
    ensure_temple_tables(conn)
    c = conn.cursor()
    c.execute(
        """SELECT id, phap_danh, loi_nguyen, loai, so_tien, mau_sac, luot_chap_tay, tao_luc
        FROM temple_lanterns
        ORDER BY CASE WHEN loai = 'hoang-kim' THEN 0 ELSE 1 END, id DESC
        LIMIT 40"""
    )
    rows = c.fetchall()
    lanterns = [
        {
            "id": r[0],
            "phap_danh": r[1],
            "loi_nguyen": r[2],
            "loai": r[3],
            "so_tien": int(r[4] or 0),
            "mau_sac": r[5] or "#F472B6",
            "luot_chap_tay": int(r[6] or 1),
            "tao_luc": r[7] or "",
        }
        for r in rows
    ]
    c.execute("SELECT COUNT(*) FROM temple_lanterns")
    tong_den = int(c.fetchone()[0] or len(lanterns))

    now_ts = time.time()
    with ROOM_LOCK:
        expired = [k for k, v in ACTIVE_VISITORS.items() if now_ts - v.get("ts", 0) > 120]
        for k in expired:
            ACTIVE_VISITORS.pop(k, None)
        online = list(ACTIVE_VISITORS.values())[:90]
        all_avatars = AMBIENT_PRACTITIONERS + online
        counters = dict(GLOBAL_COUNTERS)

    counters["tong_hoa_dang"] = tong_den
    return {
        "ok": True,
        "lich_am": get_lunar_info_today(),
        "avatars": all_avatars,
        "so_nguoi_trong_chua": len(all_avatars),
        "lanterns": lanterns,
        "counters": counters,
    }


def draw_peace_lot(phap_danh: str, chu_de: str, tam_su: str) -> dict:
    """Rút quẻ bình an & cá nhân hóa lời khuyên chữa lành."""
    clean_pd = html.escape((phap_danh or "Đạo hữu").strip()[:30])
    clean_ts = html.escape((tam_su or "").strip()[:200])
    chu_de_map = {
        "binh-an": "Gia đạo & Sức khỏe Bình an",
        "cong-viec": "Sự nghiệp & Công việc Hanh thông",
        "tai-loc": "Tài chính & Cơ hội Kinh doanh",
        "tinh-duyen": "Nhân duyên & Sự thấu hiểu",
        "tinh-tam": "Buông bỏ áp lực & Chữa lành tâm hồn",
    }
    ten_chu_de = chu_de_map.get(chu_de, "Thân tâm Bình an & Vạn sự Hanh thông")

    q = random.choice(QUE_BINH_AN)
    luan_giai_rieng = q["y_nghia"]
    if clean_ts:
        luan_giai_rieng = (
            f"Về điều {clean_pd} đang trăn trở (\"{clean_ts}\"): {q['y_nghia']} "
            f"Trong phương diện {ten_chu_de.lower()}, chỉ cần bạn giữ tâm bình khí hòa, không nóng vội quyết định trong lúc mệt mỏi thì mọi việc đều chuyển hóa theo hướng lành."
        )
    else:
        luan_giai_rieng = f"Ứng với tâm nguyện về {ten_chu_de} của {clean_pd}: {q['y_nghia']}"

    return {
        "ok": True,
        "phap_danh": clean_pd,
        "chu_de": ten_chu_de,
        "so_que": q["so"],
        "ten_que": q["ten"],
        "cap_que": q["cap"],
        "tho_que": q["tho"],
        "luan_giai": luan_giai_rieng,
        "hanh_dong": q["hanh_dong"],
        "ngay_gieo": datetime.datetime.now(VN_TZ).strftime("%d/%m/%Y"),
    }
