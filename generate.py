import os
import re
import requests
import tldextract

# =================================================================
# 🌟 1. 核心数据源配置 (支持多源聚合)
# =================================================================
# 不黑表源
README_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/README.md"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"

# Moli-X 源
MOLI_X_BASE_URL = "https://raw.githubusercontent.com/Moli-X/Resources/main/Ruleset"

# 不黑表映射字典
TABLE_HEADER_MAP = {
    "Advertising": "PurifyReject",
    "Reject": "PurifyReject",
    "Mainland": "MatrixChina",
    "MainlandMedia": "MatrixChina",
    "GlobalMedia": "GlobalMedia",
    "Media": "GlobalMedia",
    "Game": "ArcadeGame",
    "Apple": "AppleDirect",
}

AI_COMPONENTS = ["OpenAI", "Claude", "Gemini", "Copilot", "Anthropic", "BardAI"]

# 🌟 Moli-X 精确映射字典 (覆盖了你上传的所有核心列表)
MOLI_X_MAP = {
    "AI": "NexusAI",
    "OpenAI": "NexusAI",
    "Gemini": "NexusAI",
    "Claude": "NexusAI",
    
    "Ads_AWAvenue": "PurifyReject",
    "Anti-Ad": "PurifyReject",
    "Reject": "PurifyReject",
    "Ads_EasyListChina": "PurifyReject",
    "Ads_Dlerio": "PurifyReject",
    "Ads_SukkaW": "PurifyReject",
    
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
    """智能嗅探并规范化 Clash 语法，支持高级正则与原生前缀"""
    item = item.strip("'\" ").lstrip("+.")
    if not item:
        return ""
        
    # 如果 Moli-X 的规则自带了这些标准前缀 (如 DOMAIN-KEYWORD, URL-REGEX)，直接放行
    if re.match(r"^(DOMAIN|DOMAIN-SUFFIX|DOMAIN-KEYWORD|IP-CIDR|IP-CIDR6|GEOIP|URL-REGEX|PROCESS-NAME|IP-ASN),", item, re.I):
        return item
        
    # 如果是纯文本，进行自动补全
    if ":" in item:
        return f"IP-CIDR6,{item}"
    elif re.match(r"^\d{1,3}(\.\d{1,3}){3}(/\d+)?$", item):
        return f"IP-CIDR,{item}"
    else:
        return f"DOMAIN-SUFFIX,{item}"


def extract_pure_domain(rule_string):
    """仅从明确的 DOMAIN 和 DOMAIN-SUFFIX 中剥离纯域名供哈希引擎使用"""
    rule_string = str(rule_string).strip()
    if rule_string.startswith("DOMAIN,") or rule_string.startswith("DOMAIN-SUFFIX,"):
        parts = rule_string.split(",", 1)
        if len(parts) >= 2:
            return parts[1].strip().lower()
    # 对于 URL-REGEX 或 DOMAIN-KEYWORD，返回空字符串，让它们绕过哈希清洗直接存活
    return ""

def get_base_domain_safe(domain):
    if not domain or re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain) or ":" in domain:
        return domain
    ext = domain_extractor(domain)
    target_domain = getattr(ext, "top_domain_under_public_suffix", None) or getattr(ext, "registered_domain", None)
    return target_domain if target_domain else domain

# =================================================================
# 🌟 3. 数据拉取引擎 (不黑表 + Moli-X)
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
    possible_files = [f"{folder_name}.yaml", f"{folder_name}_Domain.txt", f"{folder_name}.list"]
    print(f"  -> 开始尝试拉取不黑表组件: {folder_name}", flush=True)
    success = False
    for file_item in possible_files:
        try:
            res = http_session.get(f"{RAW_BASE_URL}/{folder_name}/{file_item}", timeout=5)
            if res.status_code == 200:
                success = True
                for line in res.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//") or line.startswith("payload:"): continue
                    if line.startswith("- "): line = line[2:]
                    normalized = normalize_rule(line)
                    if normalized: rules.append(normalized)
        except Exception:
            pass
    if success: print(f"     [+] {folder_name} 拉取成功 ({len(rules)} 条)", flush=True)
    return rules

def fetch_moli_x_rules(raw_pools):
    print("\n[*] =========================================", flush=True)
    print("[*] 开始拉取 Moli-X 高频更新规则库...", flush=True)
    print("[*] =========================================", flush=True)
    
    for file_name, target_pkg in MOLI_X_MAP.items():
        url = f"{MOLI_X_BASE_URL}/{file_name}.list"
        print(f"  -> 尝试拉取 Moli-X 组件: {file_name}.list", flush=True)
        try:
            res = http_session.get(url, timeout=5)
            if res.status_code == 200:
                count = 0
                for line in res.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("//"): continue
                    normalized = normalize_rule(line)
                    if normalized:
                        raw_pools[target_pkg].add(normalized)
                        count += 1
                print(f"     [+] {file_name} 成功汇入 {target_pkg} ({count} 条)", flush=True)
        except Exception:
            print(f"     [-] {file_name} 拉取超时跳过", flush=True)

# =================================================================
# 🌟 4. 主控与双轨哈希清洗流水线
# =================================================================
def main():
    raw_pools = {k: set() for k in set(TABLE_HEADER_MAP.values()) | {"NexusAI", "OverseaProxy"}}
    
    print("\n[*] =========================================", flush=True)
    print("[*] 开始拉取不黑表基础规则库...", flush=True)
    print("[*] =========================================", flush=True)
    official_registry = parse_blackmatrix7()
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        for item in items:
            raw_pools[target_package].add(item)

    # 汇入 Moli-X 新源
    fetch_moli_x_rules(raw_pools)

    print("\n[*] 正在并入 Loyalsoldier 与 17mon 基线数据...", flush=True)
    china_set = raw_pools["MatrixChina"]
    try:
        ls_direct = http_session.get("https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt", timeout=10).text.splitlines()
        for l in ls_direct:
            l = l.strip()
            if l and not l.startswith("#"):
                china_set.add(f"DOMAIN-SUFFIX,{l.lstrip('+.')}" if not l.startswith("DOMAIN") else l)
        
        raw_ips = http_session.get("https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt", timeout=10).text.splitlines()
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                china_set.add(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 基线并入跳过: {e}", flush=True)

    print("\n[*] =========================================", flush=True)
    print("[*] 启动双轨制哈希主权索引，开始智能清洗...", flush=True)
    print("[*] =========================================", flush=True)

    china_root_registry = set()
    china_exact_registry = set()

    for rule in china_set:
        pure_dom = extract_pure_domain(rule)
        if pure_dom:
            china_root_registry.add(get_base_domain_safe(pure_dom))
            china_exact_registry.add(pure_dom)

    for pkg_name in ["PurifyReject", "NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy"]:
        purified_set = set()
        for rule in raw_pools[pkg_name]:
            pure_dom = extract_pure_domain(rule)
            
            if pure_dom: # 只有标准的 DOMAIN 和 DOMAIN-SUFFIX 才参与哈希比对
                if pkg_name == "PurifyReject":
                    if pure_dom in china_exact_registry:
                        continue 
                else:
                    if get_base_domain_safe(pure_dom) in china_root_registry:
                        continue 
            
            # 存活下来的域名、或是 URL-REGEX、DOMAIN-KEYWORD 等高级正则，直接放行
            purified_set.add(rule)
            
        raw_pools[pkg_name] = purified_set

    os.makedirs("ruleset", exist_ok=True)
    print("\n[*] =========================================", flush=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 多源聚合极速版 (Moli-X 融合)\n")
            f.write(f"# 📊 融合纯净总条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译大包: {file_path:<30} (条目数: {len(unique_items)})", flush=True)

if __name__ == "__main__":
    main()
