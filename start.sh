#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "🚀 Đang khởi động toàn bộ hệ thống Deta AI Lab (kiemtien.deta.vn)..."
systemctl --user daemon-reload
systemctl --user disable --now deta-group-queue.timer >/dev/null 2>&1 || true
systemctl --user enable --now deta-ai.service deta-tunnel.service deta-morning-strategy.timer deta-social.timer deta-tsh-reply.timer
python3 ./social_autopilot.py --open-bot-browser >/dev/null 2>&1 || true

echo "✅ Trạng thái dịch vụ:"
systemctl --user is-active deta-ai.service deta-tunnel.service deta-morning-strategy.timer deta-social.timer deta-tsh-reply.timer | paste - <(printf "deta-ai.service (Web + AI Worker 8080)\ndeta-tunnel.service (Cloudflare HTTPS)\ndeta-morning-strategy.timer (Chiến lược 06:00 sáng)\ndeta-social.timer (Báo cáo 20:30 hằng ngày)\ndeta-tsh-reply.timer (10:00 sáng: Check comment + Đăng 1 bài Thần Số Học mới)")
echo ""
echo "🌐 Web trực tiếp: https://kiemtien.deta.vn"
echo "⚙️ Trang quản trị: https://kiemtien.deta.vn/admin"
