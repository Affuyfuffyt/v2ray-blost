import json
import os
import requests
from dotenv import load_dotenv
import time

# 🔥 مسار ديناميكي ذكي يستخرج اسم اليوزر ومسار الكونفيك تلقائياً 🔥
HOME_DIR = os.path.expanduser("~")
CONFIG_PATH = f'{HOME_DIR}/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')

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

            # الإضافة للمسار الخاص بالبروتوكول (WS)
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
        os.system("pkill -9 xray")
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
