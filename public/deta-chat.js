// Bộ đo Traffic toàn trang (tự động ghi nhận nguồn khách trên mọi trang Công cụ, Thần số học & Hướng dẫn SEO)
(function () {
  if (window.__detaTrafficTracked || location.pathname.indexOf('/admin') === 0) return;
  window.__detaTrafficTracked = 1;
  var ma = null;
  try { ma = localStorage.getItem('kt-viewer-ma') || sessionStorage.getItem('kt-ma'); } catch (e) {}
  if (!ma) {
    ma = Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
  }
  try { localStorage.setItem('kt-viewer-ma', ma); sessionStorage.setItem('kt-ma', ma); } catch (e) {}
  var qs = new URLSearchParams(location.search);
  var ng = qs.get('nguon') || qs.get('utm_source') || '';
  var firstPv = true;
  function pingTraffic() {
    if (document.hidden && !firstPv) return;
    var pv = firstPv ? '1' : '0';
    firstPv = false;
    var u = '/api/dang-xem?ma=' + encodeURIComponent(ma) +
      '&pv=' + pv +
      '&trang=' + encodeURIComponent(location.pathname || '/') +
      '&ref=' + encodeURIComponent(document.referrer || '') +
      '&nguon=' + encodeURIComponent(ng);
    fetch(u, { cache: 'no-store' }).catch(function () {});
  }
  pingTraffic();
  setInterval(pingTraffic, 45000);
})();

// Phòng chat 1-1 & Trạm Demo Chatbot Chốt Đơn Trực Tiếp (Deta AI Lab):
// 1 nút nổi góc phải dưới + Bong bóng mời thử thách Chatbot + 4 chế độ đóng vai chốt đơn.
(function () {
  if (window.__detaChat) return; window.__detaChat = 1;
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function lay(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function dat(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} }
  function api(url, body) {
    return fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : { cache: 'no-store' })
      .then(function (r) { return r.json().then(function (j) { j._ma = r.status; return j; }); });
  }
  function gio(t) { var d = new Date(Date.parse(t) + 7 * 3600e3); return ('0' + d.getUTCHours()).slice(-2) + ':' + ('0' + d.getUTCMinutes()).slice(-2); }
  var nguon = (new URLSearchParams(location.search).get('nguon')) || ('chat-' + location.hostname.split('.')[0]);

  var roleMode = 'deta';
  var customShop = lay('deta-demo-custom-shop') || '';
  var fnGuiTinHienTai = null;

  var ROLES = [
    { id: 'deta', nhan: '🤖 Trợ lý Deta Lab', chao: 'Chào bạn! 🎁 Bạn có thể hỏi tôi về 10 công cụ AI 0đ trên trang, hoặc bấm chuyển sang tab [👟 Demo Shop Giày] / [🏪 Thử với Shop của bạn] ngay phía trên để thử đóng vai khách hàng khó tính chê đắt xem tôi xử lý từ chối & chốt đơn thế nào nhé!' },
    { id: 'shop-thoi-trang', nhan: '👟 Demo: Shop Thời Trang', chao: '👗 [CHẾ ĐỘ DEMO SHOP THỜI TRANG]: Xin chào! Em là trợ lý AI của Shop Giày & Thời Trang DetaStyle (Giày da êm chân Y khoa 779k · Sơ mi lụa 389k · Freeship & đổi size tận nhà).\n👉 Bạn hãy thử đóng vai khách khó tính: chê đắt hơn Shopee, đòi giảm giá, hoặc bảo "để hỏi chồng/vợ" xem em chốt đơn nhé!' },
    { id: 'shop-dac-san', nhan: '🍵 Demo: Shop Đặc Sản/Trà', chao: '🍵 [CHẾ ĐỘ DEMO ĐẶC SẢN & MỸ PHẨM]: Dạ Vân Sơn Trà kính chào quý khách! Bên em chuyên Bạch Trà Shan Tuyết Cổ Thụ Hà Giang (285k/hũ) & Hộp quà gỗ thông (790k), tặng kèm gói thử 10g pha thử trước khi nhận.\n👉 Bạn hãy thử bắt bẻ về chất lượng, sợ hàng pha tạp hoặc xin freeship để kiểm tra phản xạ của Bot nhé!' },
    { id: 'custom', nhan: '🏪 Thử với Shop của bạn!', chao: '🏪 [CHẾ ĐỘ ĐÓNG VAI SHOP CỦA BẠN]: Hãy nhập Tên Shop + Sản phẩm & Giá bán ở ô màu xanh phía trên rồi bấm [Nạp vào Bot]. Ngay lập tức tôi sẽ hóa thân thành nhân viên tư vấn của chính Shop bạn để bạn chat thử!' }
  ];

  var QUICK_CHIPS = {
    'deta': [
      '🤖 Làm sao tạo Chatbot chốt đơn cho Shop của tôi?',
      '🚀 Tôi muốn thiết kế Landing Page bán hàng trọn gói 24h',
      '🎁 Giới thiệu 10 công cụ AI miễn phí 0đ trên web'
    ],
    'shop-thoi-trang': [
      '🤨 Sao giày bên shop bán 779k đắt hơn trên Shopee thế?',
      '🤔 Để chị về hỏi ý kiến chồng đã rồi nhắn lại nhé',
      '🚚 Lấy 1 đôi có được freeship và mở hộp đi thử không?',
      '📏 Chân mình hay bị đau gót, đi mẫu này có êm thật không?'
    ],
    'shop-dac-san': [
      '🤨 Trà này có chuẩn cổ thụ Hà Giang thật không hay hàng pha?',
      '🤔 Giá 285k hơi cao, bớt cho anh 50k dùng thử nhé?',
      '🎁 Anh muốn tìm hộp quà biếu sếp sang trọng dưới 800k',
      '🛡️ Nhận hàng pha thử không hợp vị có được trả lại thật không?'
    ],
    'custom': [
      '🤨 Sao giá bên shop cao hơn chỗ khác thế, có bớt không?',
      '🤔 Để mình suy nghĩ thêm với hỏi người nhà đã nhé',
      '🛡️ Mua lần đầu sợ hàng không giống quảng cáo thì sao shop?',
      '🚚 Hôm nay đặt luôn thì có ưu đãi hay freeship gì không?'
    ]
  };

  // Nút nổi duy nhất góc phải dưới
  var nutNoi = el('button', 'cc-nut-noi'); nutNoi.type = 'button';
  nutNoi.setAttribute('aria-label', 'Chat trực tiếp & Thử thách Chatbot Chốt Đơn AI');
  var cham = el('span', 'cham-song'), nhanNoi = el('span', null, '💬 Thử Chatbot Chốt Đơn · 0đ');
  nutNoi.appendChild(cham); nutNoi.appendChild(nhanNoi);
  document.body.appendChild(nutNoi);

  // Bong bóng vẫy gọi chủ động (Proactive Teaser)
  var moiBox = el('div', 'cc-moi-chat'); moiBox.hidden = true;
  var moiDau = el('div', 'cc-moi-dau');
  moiDau.appendChild(el('span', 'cc-moi-nhan', '🔥 DEMO TRỰC TIẾP TRÊN WEB'));
  var moiTat = el('button', 'cc-moi-tat', '×'); moiTat.type = 'button'; moiTat.title = 'Đóng lời mời';
  moiDau.appendChild(moiTat);
  moiBox.appendChild(moiDau);
  var moiTxt = el('div', null, 'Thử đóng vai "Khách khó tính chê đắt" xem Chatbot AI của Deta xử lý từ chối & chốt đơn mượt cỡ nào!');
  moiBox.appendChild(moiTxt);
  var moiNut = el('div', 'cc-moi-nut');
  var btThuShop = el('button', null, '👟 Thử chê đắt ngay →'); btThuShop.type = 'button';
  var btThuRieng = el('button', null, '🏪 Thử với Shop của bạn'); btThuRieng.type = 'button';
  moiNut.appendChild(btThuShop); moiNut.appendChild(btThuRieng);
  moiBox.appendChild(moiNut);
  document.body.appendChild(moiBox);

  moiTat.onclick = function (e) { e.stopPropagation(); moiBox.hidden = true; try { sessionStorage.setItem('deta-tat-moi-chat', '1'); } catch (x) {} };
  btThuShop.onclick = function () { window.moChatDemoShop('shop-thoi-trang', '', 'Sao giày bên shop bán 779k đắt hơn trên Shopee thế?'); };
  btThuRieng.onclick = function () { window.moChatDemoShop('custom', '', ''); };

  setTimeout(function () {
    try { if (sessionStorage.getItem('deta-tat-moi-chat') === '1') return; } catch (x) {}
    if (!k.classList.contains('mo')) moiBox.hidden = false;
  }, 2400);

  // Khung chat 1-1 & Demo
  var k = el('section', 'cc-khung'); k.setAttribute('aria-label', 'Chat riêng 1-1 & Demo Chatbot Chốt Đơn');
  var dau = el('div', 'cc-dau'), chu = el('div');
  var tieuDau = el('b', null, '🤖 Deta AI & Demo Chatbot Chốt Đơn');
  chu.appendChild(tieuDau);
  var phu = el('small', null, '🎁 Bấm chọn vai bên dưới để thử thách AI chốt đơn (0đ)');
  chu.appendChild(phu);

  var to = el('button', 'cc-to', '⛶'); to.type = 'button'; to.title = 'Mở toàn màn hình';
  var dong = el('button', 'cc-dong', '✕'); dong.type = 'button'; dong.title = 'Thu gọn khung chat';
  dau.appendChild(chu); dau.appendChild(to); dau.appendChild(dong);

  // Thanh chuyển vai (Role Switcher)
  var vaiBar = el('div', 'cc-vai-bar');
  var customBox = el('div', 'cc-custom-box'); customBox.hidden = true;
  var customInp = el('input'); customInp.maxLength = 350;
  customInp.placeholder = 'Nhập Tên Shop + Sản phẩm & Giá (vd: Spa Ngọc Thảo - Chăm sóc da 299k)…';
  customInp.value = customShop;
  var customBtn = el('button', 'cc-nut', '✨ Nạp'); customBtn.type = 'button';
  customBtn.style.padding = '6px 11px'; customBtn.style.fontSize = '12px';
  customBox.appendChild(customInp); customBox.appendChild(customBtn);

  var ds = el('div', 'cc-ds'); ds.setAttribute('aria-live', 'polite');
  var goiYBar = el('div', 'cc-goi-y-nhanh');
  var chan = el('div', 'cc-chan');
  var shopCta = el('div', 'cc-shop-cta');
  shopCta.innerHTML = '<span>💡 Dựng Bot cho Shop:</span><div style="display:flex;gap:7px;flex-wrap:wrap"><a href="/cong-cu/chatbot-chot-don?nguon=chat-widget">🎁 Prompt 0đ</a><a href="/tai-lieu/chatbot-chot-don?nguon=chat-widget">📘 12 Bài (79k)</a><a href="/dich-vu/thiet-ke-tron-goi?goi=chatbot-290k#form-dat-lich">💼 Cài hộ 290k →</a></div>';

  k.appendChild(dau); k.appendChild(vaiBar); k.appendChild(customBox); k.appendChild(ds); k.appendChild(goiYBar); k.appendChild(chan); k.appendChild(shopCta);
  document.body.appendChild(k);

  function cuonCuoi() { ds.scrollTop = ds.scrollHeight; }
  function veGoiYNhanh() {
    goiYBar.textContent = '';
    var list = QUICK_CHIPS[roleMode] || QUICK_CHIPS['deta'];
    list.forEach(function (qText) {
      var bt = el('button', 'cc-chip-hoi', qText); bt.type = 'button';
      bt.onclick = function () {
        var cleanQ = qText.replace(/^[^\s]+\s+/, '');
        if (fnGuiTinHienTai) fnGuiTinHienTai(cleanQ);
      };
      goiYBar.appendChild(bt);
    });
  }

  function chonVai(idVai, shopMoTa, cauHoiTuDong, moOnhap) {
    roleMode = idVai || 'deta';
    if (shopMoTa) {
      customShop = shopMoTa;
      customInp.value = shopMoTa;
      dat('deta-demo-custom-shop', shopMoTa);
    }
    [].forEach.call(vaiBar.querySelectorAll('.cc-vai-pill'), function (p) {
      p.classList.toggle('chon', p.dataset.vai === roleMode);
    });
    customBox.hidden = !(roleMode === 'custom' && (moOnhap || !customShop));
    veGoiYNhanh();
    var rObj = ROLES.filter(function (x) { return x.id === roleMode; })[0] || ROLES[0];
    var msgChao = rObj.chao;
    if (roleMode === 'custom' && customShop) {
      msgChao = '🏪 [ĐÃ NẠP DỮ LIỆU SHOP: ' + customShop + ']\nDạ em đã sẵn sàng đóng vai nhân viên tư vấn của Shop mình! Anh/chị hãy bấm các câu gài bẫy bên dưới hoặc tự gõ câu hỏi khó để kiểm tra cách em chốt đơn nhé!';
    }
    bongTin('🤖 ' + rObj.nhan, msgChao, 'ai');
    cuonCuoi();
    if (cauHoiTuDong && fnGuiTinHienTai) {
      setTimeout(function () { fnGuiTinHienTai(cauHoiTuDong); }, 250);
    }
  }

  ROLES.forEach(function (r) {
    var b = el('button', 'cc-vai-pill' + (r.id === roleMode ? ' chon' : ''), r.nhan);
    b.type = 'button'; b.dataset.vai = r.id;
    b.onclick = function () { chonVai(r.id, '', '', r.id === 'custom'); };
    vaiBar.appendChild(b);
  });

  customBtn.onclick = function () {
    var val = customInp.value.trim();
    if (val.length < 4) { customInp.focus(); return; }
    customShop = val;
    dat('deta-demo-custom-shop', val);
    customBox.hidden = true;
    bongTin('🤖 Shop của bạn', '✅ Đã nạp dữ liệu: "' + val + '". Em đã vào vai nhân viên trực inbox của Shop! Mời anh/chị đóng vai khách hàng hỏi giá hoặc chê đắt để thử tài em nhé!', 'ai');
    cuonCuoi();
  };

  veGoiYNhanh();

  function datTo(b) {
    var nen = document.querySelector('.cc-nen');
    if (!nen) { nen = el('div', 'cc-nen'); nen.hidden = true; document.body.appendChild(nen); }
    nen.hidden = !b; nen.onclick = function () { datTo(false); };
    k.classList.toggle('toan-man', b);
    to.textContent = b ? '⤡' : '⛶';
    to.title = b ? 'Thu về khung nhỏ (Esc)' : 'Mở toàn màn hình';
    if (b) setTimeout(cuonCuoi, 30);
  }
  function moChat(mo) {
    k.classList.toggle('mo', mo);
    nutNoi.hidden = mo;
    if (mo) moiBox.hidden = true;
    if (!mo) datTo(false);
    else {
      cuonCuoi();
      var inp = k.querySelector('textarea');
      if (inp && !inp.disabled && window.innerWidth > 640) setTimeout(function () { inp.focus(); }, 60);
    }
  }
  window.moChatDeta = function () { moChat(true); };
  window.moChatDemoShop = function (vai, shopTxt, autoQ) {
    moChat(true);
    chonVai(vai || 'shop-thoi-trang', shopTxt || '', autoQ || '');
  };
  window.detaOpenRoleplay = window.moChatDemoShop;
  nutNoi.onclick = function () { moChat(true); };
  dong.onclick = function () { moChat(false); };
  to.onclick = function () { datTo(!k.classList.contains('toan-man')); };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && k.classList.contains('mo')) { if (k.classList.contains('toan-man')) datTo(false); else moChat(false); } });

  function bongTin(ten, txt, loai, t) {
    var b = el('div', 'cc-tin' + (loai ? ' ' + loai : ''));
    if (ten) b.appendChild(el('span', 'ai-ten', ten + (t ? ' · ' + gio(t) : '')));
    String(txt).split(/(https?:\/\/[^\s<>"]+|\/tai-lieu\/[a-z0-9-]+[^\s<>"]*|\/cong-cu\/[a-z0-9-]+|\/dich-vu\/thiet-ke-tron-goi[^\s<>"]*)/).forEach(function (phan, i) {
      if (i % 2) {
        var a = el('a', null, phan.replace(/\?ve=[0-9a-zA-Z_-]+$/, ''));
        a.href = phan; a.style.color = 'inherit'; a.style.fontWeight = '800'; a.style.textDecoration = 'underline';
        if (/^https?:\/\//.test(phan)) { a.target = '_blank'; a.rel = 'noopener'; }
        if (/\/tai-lieu\/tao-ai/.test(phan)) a.textContent = '📘 Mở tài liệu: Cách tạo AI tự kiếm tiền';
        if (/\/tai-lieu\/chatbot-chot-don/.test(phan)) a.textContent = '📘 Mở Cẩm nang 12 Bài dựng Chatbot Chốt Đơn 24/7';
        b.appendChild(a);
      } else if (phan) b.appendChild(document.createTextNode(phan));
    });
    ds.appendChild(b); return b;
  }

  function hopMua(vung, cacVe, khoaLuu, xong) {
    vung.textContent = '';
    var ten = el('input'); ten.maxLength = 30; ten.placeholder = 'Tên của bạn (không bắt buộc)'; vung.appendChild(ten);
    var hang = el('div', 'cc-hang');
    cacVe.forEach(function (v) {
      var b = el('button', 'cc-nut', v.nhan); b.type = 'button';
      b.onclick = function () {
        b.disabled = true; loi.textContent = '';
        api('/api/don', { loai: 'ung-ho', mon: v.ma, ten: ten.value, loi_nhan: '', nguon: nguon }).then(function (o) {
          b.disabled = false; if (!o.qr) { loi.textContent = o.loi || 'Chưa tạo được mã, thử lại nhé.'; return; }
          qr.hidden = false; qr.textContent = '';
          var im = el('img'); im.src = o.qr; im.alt = 'Mã QR chuyển khoản'; qr.appendChild(im);
          var g = el('div', 'cc-ghi', 'Quét bằng app ngân hàng: ' + o.so_tien.toLocaleString('vi-VN') + 'đ · Nội dung giữ nguyên: ' + o.noi_dung + '. Tiền về tự mở VIP trong 2 giây.'); qr.appendChild(g);
          var dem = 0, h = setInterval(function () {
            dem++; api('/api/don/' + o.ma + '?k=' + o.k).then(function (d) {
              if (d.ve && d.ve.token) { clearInterval(h); dat(khoaLuu, d.ve.token); if (window.anMung) window.anMung(); xong(); }
            }).catch(function () {}); if (dem > 450) clearInterval(h);
          }, 3000);
        }).catch(function () { b.disabled = false; loi.textContent = 'Máy chủ bận, thử lại sau ít phút.'; });
      };
      hang.appendChild(b);
    });
    vung.appendChild(hang);
    var qr = el('div', 'cc-qr'); qr.hidden = true; vung.appendChild(qr);
    var loi = el('div', 'cc-loi'); vung.appendChild(loi);
    var lai = el('button', 'cc-nut phu', 'Đã mua vé VIP? Nhập mã DETA…'); lai.type = 'button';
    lai.onclick = function () {
      lai.hidden = true; var o = el('div', 'cc-hang'), i = el('input'); i.placeholder = 'DETA123456';
      var nut = el('button', 'cc-nut', 'Kích hoạt'); nut.type = 'button'; o.appendChild(i); o.appendChild(nut); vung.insertBefore(o, loi);
      nut.onclick = function () {
        api('/api/chat/ve?ma=' + encodeURIComponent(i.value)).then(function (d) {
          if (!d.ve || d.loai !== 'rieng') { loi.textContent = d.loi || 'Không tìm thấy vé VIP hợp lệ.'; return; }
          dat('deta-ve-rieng', d.ve); xong();
        });
      };
    };
    vung.appendChild(lai);
  }

  var CAC_VE_RIENG = [{ ma: 've-rieng-30', nhan: '⚡ VIP 30 tin · 49.000đ' }, { ma: 've-rieng-80', nhan: '👑 VIP 80 tin · 99.000đ' }];
  function veRieng() {
    var ve = lay('deta-ve-rieng'); ds.textContent = '';
    if (!ve) {
      api('/api/chat/dung-thu', { ve_thu: lay('deta-ve-thu') || '' }).then(function (d) {
        if (d.ve_thu) dat('deta-ve-thu', d.ve_thu);
        var veThu = d.ve_thu || '', con = d.con_tin || 0;
        nhanNoi.textContent = con > 0 ? ('💬 Thử Chatbot Chốt Đơn · 0đ') : '🤖 Chat 1-1 với Deta AI';
        bongTin('🤖 Deta AI', ROLES[0].chao, 'ai');
        (d.tin || []).slice(-6).forEach(function (t) { bongTin(t.ai ? '🤖 AI' : 'Bạn', t.chu, t.ai ? 'ai' : 'toi', t.t); });
        if (con <= 0) {
          bongTin('🤖 Deta AI', '🔒 Bạn đã dùng hết lượt hỏi miễn phí! Nếu muốn tiếp tục tư vấn chuyên sâu 1-1 và tiếp sức nuôi server, mời bạn mở gói VIP 30 tin (49.000đ) bên dưới nhé!', 'ai');
          phu.textContent = 'Hết lượt miễn phí · Mở gói VIP 30 tin ủng hộ server';
          hopMua(chan, CAC_VE_RIENG, 'deta-ve-rieng', veRieng);
          cuonCuoi(); return;
        }
        phu.textContent = '🎁 Bấm chọn vai Shop để thử thách AI (' + con + ' lượt miễn phí)';
        cuonCuoi();
        chan.textContent = '';
        var nhapHang = el('div', 'cc-nhap-hang');
        var o = el('textarea'); o.rows = 1; o.maxLength = 1500; o.placeholder = 'Gõ câu hỏi hoặc bấm câu gài bẫy phía trên…';
        var gui = el('button', 'cc-nut', 'Gửi ➤'); gui.type = 'button'; var loi = el('div', 'cc-loi');
        nhapHang.appendChild(o); nhapHang.appendChild(gui);
        function diThu(txtOverride) {
          var txt = (typeof txtOverride === 'string' ? txtOverride : o.value).trim();
          if (!txt || gui.disabled) return;
          gui.disabled = true; if (typeof txtOverride !== 'string') o.value = '';
          bongTin('Bạn', txt, 'toi'); var cho = bongTin('🤖 AI', 'Đang suy nghĩ câu trả lời chốt đơn…', 'ai'); cuonCuoi();
          api('/api/chat/rieng', { ve: veThu, chu: txt, role_mode: roleMode, custom_shop: customShop }).then(function (r) {
            gui.disabled = false; cho.remove();
            if (r.tra) {
              var rObj = ROLES.filter(function (x) { return x.id === roleMode; })[0] || ROLES[0];
              bongTin(rObj.nhan, r.tra, 'ai'); loi.textContent = '';
              if (r.con_tin <= 0) {
                bongTin('🤖 Deta AI', '🔒 Bạn vừa dùng hết lượt hỏi thử miễn phí! Mở gói VIP 30 tin (49.000đ) hoặc đặt gói Thiết kế Bộ Não Chatbot 290k cho Shop bên dưới nhé!', 'ai');
                phu.textContent = 'Hết lượt miễn phí · Mở gói VIP 30 tin ủng hộ server';
                hopMua(chan, CAC_VE_RIENG, 'deta-ve-rieng', veRieng);
              } else {
                phu.textContent = '🎁 Chế độ: ' + rObj.nhan + ' · Còn ' + r.con_tin + ' lượt thử 0đ';
              }
            } else {
              loi.textContent = r.loi || 'Chưa gửi được.';
              if (r.het_thu) veRieng(); else o.value = txt;
            }
            cuonCuoi();
          }).catch(function () { gui.disabled = false; cho.remove(); o.value = txt; loi.textContent = 'Mạng chập chờn, thử lại nhé.'; });
        }
        fnGuiTinHienTai = diThu;
        gui.onclick = function () { diThu(); };
        o.onkeydown = function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); diThu(); } };
        chan.appendChild(nhapHang); chan.appendChild(loi);
      }).catch(function () { hopMua(chan, CAC_VE_RIENG, 'deta-ve-rieng', veRieng); });
      return;
    }

    var veThuCu = lay('deta-ve-thu') || '';
    api('/api/chat/rieng?ve=' + encodeURIComponent(ve) + (veThuCu ? '&ve_thu=' + encodeURIComponent(veThuCu) : '')).then(function (d) {
      if (d._ma === 403) { dat('deta-ve-rieng', null); veRieng(); return; }
      if (veThuCu) dat('deta-ve-thu', null);
      nhanNoi.textContent = '👑 Chat VIP · Còn ' + d.con_tin + ' tin';
      (d.tin || []).forEach(function (t) { bongTin(t.ai ? '🤖 Deta AI' : 'Bạn', t.chu, t.ai ? 'ai' : 'toi', t.t); });
      if (!(d.tin || []).length) bongTin('🤖 Deta AI', 'Phòng VIP đã mở 🎉 Cảm ơn bạn đã ủng hộ! Toàn bộ công cụ & Tài liệu dựng AI trên trang cũng đã mở khóa VIP cho bạn.', 'ai');
      phu.textContent = '👑 Vé VIP · Còn ' + d.con_tin + ' tin · hỏi bất kỳ chủ đề nào'; cuonCuoi();
      chan.textContent = '';
      var nhapHang = el('div', 'cc-nhap-hang');
      var o = el('textarea'); o.rows = 1; o.maxLength = 1500; o.placeholder = 'Nhắn riêng cho tôi…';
      var gui = el('button', 'cc-nut', 'Gửi ➤'); gui.type = 'button'; var loi = el('div', 'cc-loi');
      nhapHang.appendChild(o); nhapHang.appendChild(gui);
      if (d.con_tin <= 0) { o.disabled = true; gui.disabled = true; loi.textContent = 'Hết lượt tin nhắn. Gia hạn vé bên dưới nhé.'; }
      function di(txtOverride) {
        var txt = (typeof txtOverride === 'string' ? txtOverride : o.value).trim();
        if (!txt || gui.disabled) return;
        gui.disabled = true; if (typeof txtOverride !== 'string') o.value = '';
        bongTin('Bạn', txt, 'toi'); var cho = bongTin('🤖 Deta AI', 'Đang suy nghĩ…', 'ai'); cuonCuoi();
        api('/api/chat/rieng', { ve: ve, chu: txt, role_mode: roleMode, custom_shop: customShop }).then(function (r) {
          gui.disabled = false; cho.remove();
          if (r.tra) {
            bongTin('🤖 Deta AI', r.tra, 'ai');
            phu.textContent = '👑 Vé VIP · Còn ' + r.con_tin + ' tin';
            nhanNoi.textContent = '👑 Chat VIP · Còn ' + r.con_tin + ' tin';
            loi.textContent = ''; if (r.con_tin <= 0) veRieng();
          } else { loi.textContent = r.loi || 'Chưa gửi được.'; o.value = txt; }
          cuonCuoi();
        }).catch(function () { gui.disabled = false; cho.remove(); o.value = txt; loi.textContent = 'Mạng chập chờn, thử lại nhé.'; });
      }
      fnGuiTinHienTai = di;
      gui.onclick = function () { di(); };
      o.onkeydown = function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); di(); } };
      chan.appendChild(nhapHang); chan.appendChild(loi);
      if (d.con_tin <= 0) { var them = el('div'); chan.appendChild(them); hopMua(them, CAC_VE_RIENG, 'deta-ve-rieng', veRieng); }
    }).catch(function () {});
  }
  veRieng();
})();

// Thu gọn + kéo thả sắp xếp từng mục trên trang (v3 theo bố cục Hiến kế lên đầu)
(function () {
  var main = document.querySelector('main.khung'); if (!main) return;
  function lay(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function dat(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} }
  var KHOA_THU_TU = 'deta-thu-tu-v3-' + location.hostname;
  var cacMuc = [], khiThuGon = null, daDung = false;
  var hs = [].slice.call(main.children).filter(function (x) { return x.tagName === 'H2'; });
  if (!hs.length) return;
  var keo = null;
  hs.forEach(function (h) {
    var modul = document.createElement('section'); modul.className = 'cc-modul';
    var bao = document.createElement('div'); bao.className = 'cc-muc';
    h.parentNode.insertBefore(modul, h);
    var n = h.nextSibling;
    while (n && !(n.nodeType === 1 && (n.tagName === 'H2' || n.tagName === 'FOOTER'))) { var tiep = n.nextSibling; bao.appendChild(n); n = tiep; }
    modul.appendChild(h); modul.appendChild(bao);
    var ten = h.textContent.trim(), ma = ten.slice(0, 50);
    modul.dataset.ma = ma;
    var khoa = 'deta-muc-v2-' + location.hostname + '-' + ma;
    var tay = document.createElement('button'); tay.type = 'button'; tay.className = 'cc-tay'; tay.textContent = '⠿';
    tay.title = 'Giữ và kéo để đổi chỗ mục này'; tay.setAttribute('aria-label', 'Kéo để đổi chỗ mục ' + ten);
    var nut = document.createElement('button'); nut.type = 'button'; nut.className = 'cc-muc-nut';
    h.classList.add('cc-muc-dau'); h.insertBefore(tay, h.firstChild); h.appendChild(nut);
    function dat_(an) { bao.hidden = an; h.classList.toggle('dang-an', an); nut.textContent = an ? '▸ Hiện' : '▾'; nut.setAttribute('aria-expanded', String(!an)); nut.setAttribute('aria-label', (an ? 'Hiện mục ' : 'Thu gọn mục ') + ten); dat(khoa, an ? '1' : null); if (an && daDung && khiThuGon) khiThuGon(ma); }
    h.addEventListener('click', function (e) { if (keo || e.target.closest('a,input,textarea,select') || (e.target.closest('button') && e.target !== nut)) return; dat_(!bao.hidden); });
    dat_(lay(khoa) === '1');
    cacMuc.push({ h: h, bao: bao, modul: modul, mo: function () { if (bao.hidden) dat_(false); } });
    tay.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return; e.preventDefault();
      keo = { modul: modul, y0: e.clientY, dau: false };
      try { tay.setPointerCapture(e.pointerId); } catch (x) {}
    });
    tay.addEventListener('pointermove', function (e) {
      if (!keo || keo.modul !== modul) return;
      if (!keo.dau && Math.abs(e.clientY - keo.y0) < 6) return;
      keo.dau = true; modul.classList.add('dang-keo');
      var ds = [].slice.call(main.querySelectorAll(':scope > .cc-modul'));
      for (var i = 0; i < ds.length; i++) {
        var m = ds[i]; if (m === modul) continue;
        var r = m.getBoundingClientRect(), giua = r.top + r.height / 2;
        if (e.clientY < giua && m.compareDocumentPosition(modul) & Node.DOCUMENT_POSITION_FOLLOWING) { main.insertBefore(modul, m); break; }
        if (e.clientY > giua && m.compareDocumentPosition(modul) & Node.DOCUMENT_POSITION_PRECEDING && (!m.nextElementSibling || m.nextElementSibling !== modul)) {
          var sau = ds[i + 1]; if (!sau || e.clientY < sau.getBoundingClientRect().top + sau.getBoundingClientRect().height / 2) { main.insertBefore(modul, m.nextSibling); break; }
        }
      }
      if (e.clientY < 60) window.scrollBy(0, -18); else if (e.clientY > innerHeight - 60) window.scrollBy(0, 18);
    });
    function tha() { if (!keo) return; var co = keo.dau; modul.classList.remove('dang-keo'); keo = null; if (co) luuThuTu(); }
    tay.addEventListener('pointerup', tha); tay.addEventListener('pointercancel', tha);
    tay.addEventListener('keydown', function (e) {
      var truoc = modul.previousElementSibling, sau = modul.nextElementSibling;
      if (e.key === 'ArrowUp' && truoc && truoc.classList.contains('cc-modul')) { e.preventDefault(); main.insertBefore(modul, truoc); tay.focus(); luuThuTu(); }
      if (e.key === 'ArrowDown' && sau && sau.classList.contains('cc-modul')) { e.preventDefault(); main.insertBefore(sau, modul); tay.focus(); luuThuTu(); }
    });
  });
  var macDinh = cacMuc.map(function (m) { return m.modul.dataset.ma; });
  var cuoi = cacMuc[cacMuc.length - 1].modul.nextSibling;
  var khoiPhuc = document.createElement('p'); khoiPhuc.className = 'cc-khoi-phuc'; khoiPhuc.hidden = true;
  var nutKP = document.createElement('button'); nutKP.type = 'button'; nutKP.textContent = '↺ Khôi phục thứ tự mặc định';
  khoiPhuc.appendChild(nutKP); main.insertBefore(khoiPhuc, cuoi);
  function xepTheo(thuTu) {
    var theoMa = {}; cacMuc.forEach(function (m) { theoMa[m.modul.dataset.ma] = m.modul; });
    var ds = thuTu.filter(function (x) { return theoMa[x]; });
    macDinh.forEach(function (x) { if (ds.indexOf(x) < 0) ds.push(x); });
    ds.forEach(function (x) { main.insertBefore(theoMa[x], khoiPhuc); });
  }
  function luuThuTu() {
    var ds = [].slice.call(main.querySelectorAll(':scope > .cc-modul')).map(function (m) { return m.dataset.ma; });
    var giong = ds.join('|') === macDinh.join('|');
    dat(KHOA_THU_TU, giong ? null : JSON.stringify(ds)); khoiPhuc.hidden = giong;
  }
  nutKP.onclick = function () { xepTheo(macDinh); dat(KHOA_THU_TU, null); khoiPhuc.hidden = true; };
  var luu = null; try { luu = JSON.parse(lay(KHOA_THU_TU) || 'null'); } catch (e) {}
  if (luu && luu.length) { xepTheo(luu); khoiPhuc.hidden = false; }
  daDung = true;
})();
