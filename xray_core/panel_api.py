import json
import os
import requests
import socket
from dotenv import load_dotenv
import time

# 🔥 مسار ديناميكي ذكي يستخرج اسم اليوزر ومسار الكونفيك تلقائياً
HOME_DIR = os.path.expanduser("~")
CONFIG_PATH = f'{HOME_DIR}/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')
        # تشغيل فحص البورتات التلقائي فور تشغيل البوت
        self.optimize_ports()

    # 🔥 دالة الضبط التلقائي (VLESS فقط على بورت 8100)
    def optimize_ports(self):
        try:
            if not os.path.exists(CONFIG_PATH):
                return
                
            active_port_file = f'{HOME_DIR}/active_port.txt'
            
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)

            # تثبيت البورت الرئيسي على 8100 وحذف أي بوابات زائدة لمنع التعارض
            if 'inbounds' in config and len(config['inbounds']) > 0:
                config['inbounds'][0]['port'] = 8100
                config['inbounds'][0]['protocol'] = "vless"
                # الإبقاء على البوابة الأولى فقط (VLESS)
                config['inbounds'] = [config['inbounds'][0]]

            # حفظ التعديلات
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            # حفظ البورت بملف نصي لضمان معرفته
            with open(active_port_file, 'w') as f:
                f.write("8100")

            print("✅ تم ضبط السيرفر بنجاح! بورت الاتصال الرئيسي هو: 8100 (VLESS فقط)")
            self.restart_xray()
        except Exception as e:
            print(f"Error optimizing ports: {e}")

    def create_client(self, email, uuid, protocol="vless"):
        try:
            if not os.path.exists(CONFIG_PATH):
                print(f"❌ Error: Config file not found at {CONFIG_PATH}")
                return False

            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # تصحيح مسار اللوكات التلقائي
            local_user = os.path.basename(HOME_DIR)
            if "log" not in config:
                config["log"] = {}
            config["log"]["access"] = f"/home/{local_user}/xray_core/access.log"
            config["log"]["error"] = f"/home/{local_user}/xray_core/error.log"

            # إنشاء العميل لـ VLESS
            new_client = {"id": uuid, "email": email, "level": 0}

            # الإضافة للبوابة الوحيدة (رقم 0)
            clients_main = config['inbounds'][0]['settings']['clients']
            if not any(c.get('email') == email for c in clients_main):
                clients_main.append(new_client)

            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # مسار ديناميكي متوافق 100%
        os.system(f"pkill -9 xray ; nohup {HOME_DIR}/xray_core/xray run -c {HOME_DIR}/xray_core/config.json > {HOME_DIR}/xray_core/xray.log 2>&1 &")
        time.sleep(0.5)
        return True

    def get_client_traffic(self, email):
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            changed = False
            # البحث في كل البوابات (وهي بوابة واحدة فقط الآن)
            for inbound in config.get('inbounds', []): 
                try:
                    clients = inbound['settings'].get('clients', [])
                    if not enable:
                        original_len = len(clients)
                        inbound['settings']['clients'] = [c for c in clients if c.get('email') != email]
                        if len(inbound['settings']['clients']) != original_len:
                            changed = True
                except Exception:
                    continue
            
            if changed:
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
                return self.restart_xray()
                
            return True
        except Exception as e:
            print(f"Error changing status: {e}")
            return False
