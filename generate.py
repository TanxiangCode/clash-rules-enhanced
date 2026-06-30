import os
import re
import requests
import tldextract

# =================================================================
# 🌟 1. 核心数据源配置 (极简补丁架构)
# =================================================================
README_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/README.md"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"
MOLI_X_BASE_URL = "https://raw.githubusercontent.com/Moli-X/Resources/main/Ruleset"

# 剔除了 Advertising，将负担彻底交还给底层的 GEOSITE 数据库
TABLE_HEADER_MAP = {
    "Mainland": "MatrixChina",
    "MainlandMedia": "MatrixChina",
    "GlobalMedia": "GlobalMedia",
    "Media": "GlobalMedia",
    "Game": "ArcadeGame",
    "Apple": "AppleDirect",
}

AI_COMPONENTS = ["OpenAI", "Claude", "Gemini", "Copilot", "Anthropic", "BardAI"]

# 🌟 Moli-X 精确映射 (去除了几十万行的 Ads 巨无霸包)
MOLI_X_MAP = {
    "AI": "NexusAI",
    "OpenAI": "NexusAI",
    "Gemini": "NexusAI",
    "Claude": "NexusAI",
    
    "ChinaDomain": "MatrixChina",
    "Bilibili": "MatrixChina",
    "Tencent": "MatrixChina",
    "WeChat": "MatrixChina",
    
    "Apple": "AppleDirect",
    "AppleID": "AppleDirect",
    "AppStore": "AppleDirect",
    
    "YouTube": "GlobalMedia",
    "Netflix": "GlobalMedia",
    "Disney": "GlobalMedia",
    "Spotify": "GlobalMedia",
    "TikTok": "GlobalMedia",
    "HBO": "GlobalMedia",
    "PrimeVideo": "GlobalMedia",
    
    "Steam": "ArcadeGame",
    "Epic": "ArcadeGame",
    "Game": "ArcadeGame",
    
    "GitHub": "OverseaProxy",
    "GitLab": "OverseaProxy",
    "Telegram": "OverseaProxy",
    "Microsoft": "OverseaProxy",
    "OneDrive": "OverseaProxy",
    "Google": "OverseaProxy",
    "Twitter": "OverseaProxy",
    "Facebook": "OverseaProxy",
    "Instagram": "OverseaProxy"
}

http_session = requests.Session()
http_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) clash-rules-enhanced"})
domain_extractor = tldextract.TLDExtract()

# =================================================================
# 🌟 2. 智能语法格式化引擎
# =================================================================
def normalize_rule(item):
    item = item.strip("'\" ").lstrip("+.")
    if not item: return ""
    if re.match(r"^(DOMAIN|DOMAIN-SUFFIX|DOMAIN-KEYWORD|IP-CIDR|IP-CIDR6|GEOIP|URL-REGEX|PROCESS-NAME|IP-ASN),", item, re.I):
        return item
    if ":" in item: return f"IP-CIDR6,{item}"
    elif re.match(r"^\d{1,3}(\.\d{1,3}){3}(/\d+)?$", item): return f"IP-CIDR,{item}"
    else: return f"DOMAIN-SUFFIX,{item}"

def extract_pure_domain(rule_string):
    rule_string = str(rule_string).strip()
    if rule_string.startswith("DOMAIN,") or rule_string.startswith("DOMAIN-SUFFIX,"):
        parts = rule_string.split(",", 1)
        if len(parts) >= 2: return parts[1].strip().lower()
    return ""

def get_base_domain_safe(domain):
    if not domain or re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain) or ":" in domain: return domain
    ext = domain_extractor(domain)
    target_domain = getattr(ext, "top_domain_under_public_suffix", None) or getattr(ext, "registered_domain", None)
    return target_domain if target_domain else domain

# =================================================================
# 🌟 3. 数据拉取引擎
# =================================================================
def parse_blackmatrix7():
    print("[*] 正在拉取不黑表 README 账本...", flush=True)
    dynamic_registry = {}
    try:
        res = http_session.get(README_URL, timeout=10)
        if res.status_code == 200:
            current_package = None
            is_global_table = False
            for line in res.text.splitlines():
                line = line.strip()
                if not line or not line.startswith("|"): continue
                if "[" not in line:
                    words = re.findall(r"[A-Za-z]+", line)
                    if words:
                        current_package = TABLE_HEADER_MAP.get(words[0], None)
                        is_global_table = words[0] == "Global"
                    continue
                if current_package or is_global_table:
                    folders = re.findall(r"rule/Loon/([^)\s/]+)", line)
                    for folder in folders:
                        if is_global_table:
                            if folder in AI_COMPONENTS: dynamic_registry[folder] = "NexusAI"
                            elif folder in ["YouTube", "YouTubeMusic", "Netflix", "TikTok", "Disney", "Spotify"]: dynamic_registry[folder] = "GlobalMedia"
                            elif folder in ["GitHub", "OneDrive", "Microsoft", "Proxy"]: dynamic_registry[folder] = "OverseaProxy"
                        elif current_package:
                            dynamic_registry[folder] = current_package
    except Exception as e:
        print(f"[-] 动态扫描中断: {e}", flush=True)
    return dynamic_registry

def download_and_extract_any(folder_name):
    rules = []
    for file_item in [f"{folder_name}.yaml", f"{folder_name}_Domain.txt", f"{folder_name}.list"]:
        try:
            res = http_session.get(f"{RAW_BASE_URL}/{folder_name}/{file_item}", timeout=5)
            if res.status_code == 200:
                for line in res.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//") or line.startswith("payload:"): continue
                    if line.startswith("- "): line = line[2:]
                    normalized = normalize_rule(line)
                    if normalized: rules.append(normalized)
                return rules  # 成功提取一种格式即可返回
        except Exception: pass
    return rules

def fetch_moli_x_rules(raw_pools):
    print("\n[*] 开始拉取 Moli-X 高频更新规则库...", flush=True)
    for file_name, target_pkg in MOLI_X_MAP.items():
        try:
            res = http_session.get(f"{MOLI_X_BASE_URL}/{file_name}.list", timeout=5)
            if res.status_code == 200:
                for line in res.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"): continue
                    normalized = normalize_rule(line)
                    if normalized: raw_pools[target_pkg].add(normalized)
        except Exception: pass

# =================================================================
# 🌟 4. 主控与双轨哈希清洗流水线 (极速版)
# =================================================================
def main():
    # 彻底移除了 PurifyReject 的初始化
    raw_pools = {k: set() for k in ["MatrixChina", "NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy", "AppleDirect"]}
    
    official_registry = parse_blackmatrix7()
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        for item in items: raw_pools[target_package].add(item)

    fetch_moli_x_rules(raw_pools)

    # ⛔ 核心优化点：删除了 Loyalsoldier 和 17mon 百万级数据的下载汇入 ⛔
    
    print("\n[*] 启动主权防误杀保护引擎...", flush=True)
    china_root_registry = set()
    for rule in raw_pools["MatrixChina"]:
        pure_dom = extract_pure_domain(rule)
        if pure_dom: china_root_registry.add(get_base_domain_safe(pure_dom))

    for pkg_name in ["NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy"]:
        purified_set = set()
        for rule in raw_pools[pkg_name]:
            pure_dom = extract_pure_domain(rule)
            if pure_dom and get_base_domain_safe(pure_dom) in china_root_registry:
                continue # 只要根域名在国内补丁包里，禁止流出海外
            purified_set.add(rule)
        raw_pools[pkg_name] = purified_set

    os.makedirs("ruleset", exist_ok=True)
    print("\n[*] =========================================", flush=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 暴瘦极速版 (L1 专属补丁)\n")
            f.write(f"# 📊 精简条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译轻量包: {file_path:<25} (仅 {len(unique_items)} 条)", flush=True)

if __name__ == "__main__":
    main()
