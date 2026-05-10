import time
import subprocess
import json
import os

API_SERVER = '127.0.0.1:10086'
XRAY_BIN = '/home/wathfor/xray_core/xray'
STATS_FILE = '/home/wathfor/v2ray_manager/global_stats.json'

# الأرقام التراكمية
total_down = 0
total_up = 0

# قراءة الاستهلاك القديم إذا كان السيرفر مطفي واشتغل
if os.path.exists(STATS_FILE):
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            total_down = data.get('total_down', 0)
            total_up = data.get('total_up', 0)
    except:
        pass

print("🚀 بدء نظام المراقبة الشامل (الاستهلاك الكلي للسيرفر)...")

while True:
    try:
        # سحب وتصفير العداد من المحرك
        cmd = f"{XRAY_BIN} api statsquery -server={API_SERVER} -reset=true"
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=2).decode('utf-8')
        
        if result.strip():
            stats = json.loads(result)
            stat_list = stats.get('stat', [])
            
            for stat in stat_list:
                name = stat.get('name', '')
                value = int(stat.get('value', 0))
                
                # 🎯 السر هنا: نراقب مخرج الـ freedom حصراً لأنه يمثل الإنترنت الفعلي
                if 'outbound>>>freedom' in name:
                    if 'downlink' in name:
                        total_down += value
                    elif 'uplink' in name:
                        total_up += value
            
            # حفظ الاستهلاك الكلي بالملف كل ثانية
            with open(STATS_FILE, 'w') as f:
                json.dump({'total_down': total_down, 'total_up': total_up}, f)
            
            # طباعة الأرقام بالميجا بايت بالشاشة
            mb_down = total_down / 1024 / 1024
            mb_up = total_up / 1024 / 1024
            print(f"📊 الاستهلاك الكلي: تحميل ({mb_down:.2f} MB) | رفع ({mb_up:.2f} MB)")
            
    except Exception as e:
        pass
        
    time.sleep(1) # التحديث كل ثانية واحدة
