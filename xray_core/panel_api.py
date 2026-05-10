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

    # 🔥 دالة سحرية تسأل النظام عن بورت فارغ تماماً وغير محجوز
    def get_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    # 🔥 دالة الفحص والضبط التلقائي للبورتات المتضاربة
    def optimize_ports(self):
        try:
            if not os.path.exists(CONFIG_PATH):
                return
                
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)

            # إذا كان البورت الرئيسي 8100 (الافتراضي)، معناه يحتاج تغيير لمنع التضارب
            if config['inbounds'][0].get('port') == 8100:
                print("⚠️ جاري سحب بورتات جديدة غير مستخدمة من السيرفر...")

                # سحب بورتات نظيفة
                p_main = self.get_free_port()
                p_vless = self.get_free_port()
                p_vmess = self.get_free_port()
                p_trojan = self.get_free_port()
                p_api = self.get_free_port()

                # تحديث البوابة الرئيسية (0.0.0.0) وتوجيهاتها الداخلية
                config['inbounds'][0]['port'] = p_main
                config['inbounds'][0]['settings']['fallbacks'][0]['dest'] = p_vless
                config['inbounds'][0]['settings']['fallbacks'][1]['dest'] = p_vmess
                config['inbounds'][0]['settings']['fallbacks'][2]['dest'] = p_trojan

                # تحديث البوابات الداخلية (127.0.0.1)
                config['inbounds'][1]['port'] = p_vless
                config['inbounds'][2]['port'] = p_vmess
                config['inbounds'][3]['port'] = p_trojan

                # تحديث بورت واجهة API
                if len(config['inbounds']) > 4:
                    config['inbounds'][4]['port'] = p_api

                # حفظ التعديلات
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
                
                # حفظ البورت الرئيسي بملف نصي حتى المستخدم يكدر يشوفه
                with open(f'{HOME_DIR}/active_port.txt', 'w') as f:
                    f.write(str(p_main))

                print(f"✅ تم ضبط البورتات بنجاح! بورت الاتصال الرئيسي هو: {p_main}")
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
            if "log" in config:
                expected_access = f"/home/{local_user}/xray_core/access.log"
                expected_error = f"/home/{local_user}/xray_core/error.log"
                if config["log"].get("access") != expected_access:
                    config["log"]["access"] = expected_access
                if config["log"].get("error") != expected_error:
                    config["log"]["error"] = expected_error

            main_inbound = 0
            
            if protocol == "vless" or protocol == "vmess":
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "trojan":
                new_client = {"password": uuid, "email": email, "level": 0} 
            else:
                new_client = {"id": uuid, "email": email, "level": 0}

            # الإضافة للبوابة الرئيسية
            clients_main = config['inbounds'][main_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_main):
                clients_main.append(new_client)

            # الإضافة للمسار الخاص بالبروتوكول
            target_map = {"vless": 1, "vmess": 2, "trojan": 3}
            target_inbound = target_map.get(protocol.lower(), 1)
            
            clients_ws = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_ws):
                clients_ws.append(new_client)
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # تم تحديث مسار إعادة التشغيل ليكون ديناميكي ومتوافق مع مسارك
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
            for i in range(4): 
                try:
                    clients = config['inbounds'][i]['settings']['clients']
                    if not enable:
                        original_len = len(clients)
                        config['inbounds'][i]['settings']['clients'] = [c for c in clients if c.get('email') != email]
                        if len(config['inbounds'][i]['settings']['clients']) != original_len:
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
