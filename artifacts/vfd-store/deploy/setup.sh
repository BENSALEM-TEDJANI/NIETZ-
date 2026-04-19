#!/bin/bash
# ═══════════════════════════════════════════════════
#  سكريبت إعداد سيرفر Hetzner لموقع NIETZ
#  شغّله مرة واحدة فقط كـ root:
#      bash setup.sh
# ═══════════════════════════════════════════════════
set -e

REPO_URL="https://github.com/BENSALEM-TEDJANI/NIETZ-.git"
APP_DIR="/var/www/nietz"
DOMAIN="nietz.alllal.com"

echo "══ 1. تحديث النظام وتثبيت الحزم ══"
apt update -y && apt upgrade -y
apt install -y python3 python3-pip nginx git certbot python3-certbot-nginx ufw

echo "══ 2. إعداد جدار الحماية ══"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "══ 3. استنساخ المستودع ══"
if [ -d "$APP_DIR/.git" ]; then
    echo "المستودع موجود مسبقاً — سيتم التحديث"
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "══ 4. تثبيت متطلبات Python ══"
cd "$APP_DIR"
pip3 install -r requirements.txt -q

echo "══ 5. إعداد nginx ══"
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/nietz
ln -sf /etc/nginx/sites-available/nietz /etc/nginx/sites-enabled/nietz
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "══ 6. إعداد systemd service ══"
cp "$APP_DIR/deploy/nietz.service" /etc/systemd/system/nietz.service
systemctl daemon-reload
systemctl enable nietz
systemctl start nietz

echo "══ 7. SSL مع Let's Encrypt ══"
echo "تأكد أن DNS يشير إلى هذا السيرفر قبل تشغيل الأمر التالي:"
echo ""
echo "    certbot --nginx -d $DOMAIN"
echo ""

echo "══ الإعداد اكتمل ══"
echo "الموقع يعمل الآن على: http://$DOMAIN"
systemctl status nietz --no-pager
