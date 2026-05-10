#!/bin/bash
clear
echo "=================================================="
echo "  🚀 أداة إدارة V2Ray (النسخة الاحترافية بـ API) "
echo "=================================================="

# 1. تنظيف وإيقاف العمليات
pkill -9 xray
pkill -9 -f run.py

# 2. أخذ البيانات المطلوبة
read -p "🔑 أدخل توكن البوت: " BOT_TOKEN
read -p "👑 أدخل الآيدي الخاص بك: " ADMIN_ID
read -p "🛠️ أدخل Alwaysdata API Key: " AD_API_KEY
read -p "🆔 أدخل Site ID الخاص بك: " AD_SITE_ID
read -p "🌐 أدخل الدومين الخاص بك (مثال: google.com): " AD_DOMAIN
read -p "👤 أدخل FTP User (اسم حسابك في Alwaysdata): " FTP_USER

# 3. تجهيز المجلدات
WORK_DIR="$HOME/v2ray_manager"
XRAY_DIR="$HOME/xray_core"
mkdir -p $XRAY_DIR
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# 4. تحميل المحرك Xray (إذا لم يكن موجوداً)
if [ ! -f "$XRAY_DIR/xray" ]; then
    echo "[+] جاري تحميل محرك Xray..."
    cd $XRAY_DIR
    wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
    unzip -q Xray-linux-64.zip
    rm Xray-linux-64.zip
    chmod +x xray
fi

# 5. سحب ملفات البوت من كيت هب
echo "[+] جاري سحب ملفات البوت..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR

# 6. نقل ملف config.json للمكان الصحيح وتصحيح المسارات 🔥
cp xray_core/config.json $XRAY_DIR/config.json

echo "[+] جاري تصحيح مسارات السيرفر المحلي لتعمل مع حساب: $FTP_USER"
# 🔥 التحديث الجذري: مسح أي مسار قديم وكتابة المسار المطلق الصحيح بقوة 🔥
sed -i 's|"access":.*|"access": "/home/'"$FTP_USER"'/xray_core/access.log",|g' $XRAY_DIR/config.json
sed -i 's|"error":.*|"error": "/home/'"$FTP_USER"'/xray_core/error.log",|g' $XRAY_DIR/config.json

# 7. تخزين كل المفاتيح في ملف البيئة المخفي
echo "BOT_TOKEN=$BOT_TOKEN" > .env
echo "ADMIN_ID=$ADMIN_ID" >> .env
echo "AD_API_KEY=$AD_API_KEY" >> .env
echo "AD_SITE_ID=$AD_SITE_ID" >> .env
echo "AD_DOMAIN=$AD_DOMAIN" >> .env
echo "FTP_USER=$FTP_USER" >> .env

# 🔥 الإضافة الذكية: تجهيز ملف الريستارت التلقائي والدومين العالمي
echo "$AD_SITE_ID" > $HOME/alwaysdata_keys.txt
echo "$AD_API_KEY" >> $HOME/alwaysdata_keys.txt
echo "$AD_DOMAIN" >> $HOME/alwaysdata_keys.txt

# 8. تثبيت المكاتب
echo "[+] جاري تثبيت المتطلبات..."
pip install -r requirements.txt

# 🔥 9. إنشاء ملف المراقب الأبدي (Keep Alive) 🔥
cat << 'EOF' > $HOME/keep_alive.sh
#!/bin/bash
if ! pgrep -f "run.py" > /dev/null
then
    echo "البوت كان متوقف... جاري إعادة تشغيله."
    cd $HOME/v2ray_manager
    nohup python3 run.py > system.log 2>&1 &
fi
EOF
chmod +x $HOME/keep_alive.sh

# تشغيل البوت لأول مرة
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "✅ تم التثبيت والربط بـ API المنصة وتصحيح المسارات بنجاح!"
echo "⚠️ خطوة أخيرة مهمة: قم بإضافة $HOME/keep_alive.sh إلى Scheduled Tasks في لوحة Alwaysdata ليعمل كل 5 دقائق."
echo "=================================================="
