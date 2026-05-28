"""
Blocklist Manager for xray
==========================

يدير قائمة الدومينات المحظورة، يطبّقها على إعدادات xray، ويعيد تشغيله.
يُستخدم من طرف بوت التيليجرام أو يدوياً من سطر الأوامر.

Usage (CLI):
    python3 -m xray_core.blocklist_manager apply
    python3 -m xray_core.blocklist_manager add ipinfo.io
    python3 -m xray_core.blocklist_manager remove ipinfo.io
    python3 -m xray_core.blocklist_manager list
"""

import json
import os
import subprocess
import sys
import time

# --- Paths --------------------------------------------------------------

XRAY_HOME = os.path.expanduser("~/xray_core")
CONFIG_PATH = os.path.join(XRAY_HOME, "config.json")
BLOCKLIST_PATH = os.path.join(XRAY_HOME, "blocked_sites.json")
XRAY_BIN = os.path.join(XRAY_HOME, "xray")
STARTUP_LOG = os.path.join(XRAY_HOME, "startup.log")

# --- Default seed list (شامل) ------------------------------------------
# يُستخدم فقط لو ملف blocked_sites.json غير موجود

DEFAULT_BLOCKED_DOMAINS = [
    # === Top IP info services ===
    "ipinfo.io", "ip-api.com", "ipapi.co", "ipapi.com",
    "ipgeolocation.io", "ipgeolocationapi.com",
    "ipify.org", "ipdata.co", "ipstack.com",
    "ip2location.io", "ip2location.com", "ip2location.net",
    "iplocation.net", "iplocation.com", "iplocation.io",
    # === What is my IP family ===
    "whatismyipaddress.com", "whatismyip.com", "whatismyip.host",
    "whatismyip.live", "whatismyip.us", "whatismyip.net",
    "whatismyip.org", "whatsmyip.org", "whatsmyip.net",
    "whatismybrowser.com", "whatismyipv6.com",
    "whatismyipaddress.net", "myip.is", "myip.host",
    # === My IP family ===
    "myip.com", "myip.ms", "myip.la", "myip.dk", "myip.es",
    "myipaddress.com", "myipaddress.net", "myipaddress.io",
    "showmyipaddress.com", "showmyip.com", "showmyip.gr",
    "showip.net",
    # === ipaddress.* family ===
    "ipaddress.my", "ipaddress.com", "ipaddress.net",
    "ipaddress.org", "ip-address.com", "ip-address.org",
    # === icanhazip family ===
    "icanhazip.com", "ifconfig.me", "ifconfig.co", "ifconfig.io",
    "ifconfig.net", "wtfismyip.com",
    # === Chinese / Asian IP sites ===
    "ip138.com", "ip.cn", "ip.sb", "ip.tool.lu", "ip.gs",
    "ip.fm", "ip.skk.moe",
    # === Loggers ===
    "iplogger.org", "iplogger.com", "iplogger.ru", "iplogger.co",
    "iplogger.info", "iplogger.io", "grabify.link",
    "yip.su", "iplis.ru",
    # === WHOIS ===
    "ipwhois.app", "ipwhois.io", "ipwho.is", "ipwhois.net",
    "whoer.net", "whoer.com", "whois.com", "who.is",
    "whois.net", "whois.domaintools.com",
    "ipinfo.info", "domaintools.com",
    # === AWS/Other API ===
    "checkip.amazonaws.com", "checkip.dyndns.org",
    "checkmyip.com", "checkmyip.org",
    "yourip.us", "yourip.io", "freeipapi.com",
    # === Track/Geo ===
    "ip-track.com", "iptrack.io", "ip-tracker.org",
    "geoip.com", "geoiptool.com", "geoiplookup.io",
    "geoiplookup.net", "geolocation-db.com",
    "iplist.cc", "ip-score.com", "ipscoring.com",
    # === Browser fingerprinting ===
    "browserleaks.com", "ipleak.net", "ipleak.com",
    "dnsleaktest.com", "dnsleak.com", "dns-leak.com",
    "amiunique.org", "fingerprint.com", "fingerprintjs.com",
    "panopticlick.eff.org", "coveryourtracks.eff.org",
    "deviceinfo.me", "browserspy.dk",
    # === Threat / Abuse ===
    "abuseipdb.com", "iphub.info", "ipqualityscore.com",
    "scamalytics.com", "spur.us", "vpnapi.io",
    "getipintel.net", "proxycheck.io", "fraudguard.io",
    "ipdetective.io", "ipthreat.net",
    # === APIs / Backend ===
    "api.bigdatacloud.net", "bigdatacloud.com", "bigdatacloud.net",
    "api.ip.sb", "api.ipify.org", "api.myip.com",
    "api.ipgeolocation.io", "api.ipapi.com",
    "api.ipdata.co", "api.ip2location.io",
    "freegeoip.app", "freegeoip.net", "freegeoip.io",
    # === Regional / other ===
    "2ip.ru", "2ip.io", "spys.one", "spys.me",
    "extreme-ip-lookup.com",
]

# Catch-all keywords (يطابق أي دومين يحتوي على هذي الكلمات)
DEFAULT_KEYWORDS = [
    "whatismyip",
    "whatsmyip",
    "myipaddress",
    "checkmyip",
    "showmyip",
    "ipchecker",
    "ip-checker",
    "ipgeolocation",
    "ip-lookup",
    "iplookup",
    "geoiplookup",
]

# --- Storage ------------------------------------------------------------


def load_blocklist():
    """Load blocklist from JSON, seeding defaults if file missing."""
    if not os.path.exists(BLOCKLIST_PATH):
        data = {
            "domains": list(DEFAULT_BLOCKED_DOMAINS),
            "keywords": list(DEFAULT_KEYWORDS),
        }
        save_blocklist(data)
        return data
    try:
        with open(BLOCKLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {"domains": [], "keywords": []}
    # Ensure required keys
    data.setdefault("domains", [])
    data.setdefault("keywords", [])
    return data


def save_blocklist(data):
    """Persist blocklist to JSON (atomic write)."""
    os.makedirs(os.path.dirname(BLOCKLIST_PATH), exist_ok=True)
    tmp = BLOCKLIST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, BLOCKLIST_PATH)


# --- Mutations ---------------------------------------------------------


def _normalize_domain(d):
    """Strip whitespace, lowercase, drop scheme/path."""
    if not d:
        return ""
    d = d.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    if "/" in d:
        d = d.split("/", 1)[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def add_domain(domain):
    """Add a domain to the blocklist. Returns (ok, message)."""
    domain = _normalize_domain(domain)
    if not domain or "." not in domain:
        return False, "❌ دومين غير صالح."
    data = load_blocklist()
    if domain in data["domains"]:
        return False, f"⚠️ الدومين `{domain}` موجود بالفعل."
    data["domains"].append(domain)
    data["domains"].sort()
    save_blocklist(data)
    return True, f"✅ تم إضافة `{domain}` (الإجمالي: {len(data['domains'])})."


def remove_domain(domain):
    """Remove a domain. Returns (ok, message)."""
    domain = _normalize_domain(domain)
    data = load_blocklist()
    if domain not in data["domains"]:
        return False, f"⚠️ الدومين `{domain}` غير موجود في القائمة."
    data["domains"].remove(domain)
    save_blocklist(data)
    return True, f"✅ تم حذف `{domain}` (المتبقي: {len(data['domains'])})."


def list_domains():
    """Return the sorted list of blocked domains."""
    data = load_blocklist()
    return sorted(data["domains"])


def list_keywords():
    """Return the keyword list."""
    data = load_blocklist()
    return list(data["keywords"])


def search_domains(query):
    """Return domains containing the query string."""
    query = (query or "").strip().lower()
    if not query:
        return []
    return [d for d in list_domains() if query in d]


# --- xray config rebuild -----------------------------------------------


def _build_routing_rules(data):
    """Build xray routing rules from blocklist data."""
    domain_rules = [f"domain:{d}" for d in data.get("domains", [])]
    keyword_rules = [f"keyword:{k}" for k in data.get("keywords", [])]
    rules = []
    # 1) Block QUIC (UDP 443) to force TCP/TLS so sniffing works
    rules.append({
        "type": "field",
        "network": "udp",
        "port": "443",
        "outboundTag": "block",
    })
    # 2) Block IP-check domains
    if domain_rules or keyword_rules:
        rules.append({
            "type": "field",
            "domain": domain_rules + keyword_rules,
            "outboundTag": "block",
        })
    return rules


def apply_to_config():
    """Rewrite xray config.json with current blocklist. Returns (ok, message)."""
    if not os.path.exists(CONFIG_PATH):
        return False, f"❌ ملف الإعدادات غير موجود: {CONFIG_PATH}"

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            c = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"❌ فشل قراءة config.json: {e}"

    data = load_blocklist()

    # 1) Enable sniffing on every inbound
    for ib in c.get("inbounds", []):
        ib["sniffing"] = {
            "enabled": True,
            "destOverride": ["http", "tls", "quic"],
            "metadataOnly": False,
            "routeOnly": False,
        }

    # 2) Ensure outbounds include direct + block
    outbounds = c.get("outbounds") or []
    tags = {o.get("tag") for o in outbounds}
    if "direct" not in tags:
        outbounds.insert(0, {"protocol": "freedom", "tag": "direct"})
    if "block" not in tags:
        outbounds.append({"protocol": "blackhole", "tag": "block"})
    c["outbounds"] = outbounds

    # 3) Routing rules
    c["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": _build_routing_rules(data),
    }

    # 4) Logging
    c.setdefault("log", {})
    c["log"].setdefault("access", "access.log")
    c["log"].setdefault("error", "error.log")
    c["log"].setdefault("loglevel", "warning")

    # Atomic write
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)

    return True, (
        f"✅ تم تطبيق الإعدادات: "
        f"{len(data['domains'])} دومين، "
        f"{len(data['keywords'])} keyword."
    )


# --- xray process management -------------------------------------------


def restart_xray():
    """Kill and relaunch xray detached. Returns (ok, message)."""
    if not os.path.exists(XRAY_BIN):
        return False, f"❌ ملف xray غير موجود: {XRAY_BIN}"

    # Kill any existing xray processes
    subprocess.run(["pkill", "-9", "xray"], capture_output=True)
    time.sleep(2)

    # Truncate logs
    for f in ("error.log", "access.log"):
        path = os.path.join(XRAY_HOME, f)
        try:
            open(path, "w").close()
        except OSError:
            pass

    # Launch detached
    try:
        with open(STARTUP_LOG, "w") as logf:
            subprocess.Popen(
                [XRAY_BIN, "run", "-c", CONFIG_PATH],
                cwd=XRAY_HOME,
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as e:
        return False, f"❌ فشل تشغيل xray: {e}"

    time.sleep(4)

    # Verify
    result = subprocess.run(
        ["pgrep", "-f", "xray run"],
        capture_output=True, text=True
    )
    pids = [p for p in result.stdout.strip().split("\n") if p]
    if pids:
        return True, f"✅ xray يعمل (PID: {', '.join(pids)})."
    # Failed — return tail of startup log
    try:
        with open(STARTUP_LOG, "r") as f:
            log_tail = f.read()[-500:]
    except OSError:
        log_tail = "(no log)"
    return False, f"❌ xray فشل في البدء.\n```\n{log_tail}\n```"


def apply_and_restart():
    """Apply blocklist to config and restart xray. Returns (ok, summary)."""
    ok, msg = apply_to_config()
    if not ok:
        return False, msg
    config_msg = msg
    ok, restart_msg = restart_xray()
    if not ok:
        return False, f"{config_msg}\n{restart_msg}"
    return True, f"{config_msg}\n{restart_msg}"


# --- CLI ---------------------------------------------------------------


def _cli():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "apply":
        ok, msg = apply_and_restart()
        print(msg)
        sys.exit(0 if ok else 1)
    elif cmd == "add" and len(sys.argv) >= 3:
        ok, msg = add_domain(sys.argv[2])
        print(msg)
        if ok:
            ok2, msg2 = apply_and_restart()
            print(msg2)
        sys.exit(0 if ok else 1)
    elif cmd == "remove" and len(sys.argv) >= 3:
        ok, msg = remove_domain(sys.argv[2])
        print(msg)
        if ok:
            ok2, msg2 = apply_and_restart()
            print(msg2)
        sys.exit(0 if ok else 1)
    elif cmd == "list":
        for d in list_domains():
            print(d)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
