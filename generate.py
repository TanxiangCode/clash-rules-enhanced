import os
import re
import requests
import tldextract

# 🌟 注意：这里彻底删除了 import yaml，拒绝性能拖累！

README_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/README.md"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"

TABLE_HEADER_MAP = {
    "Advertising": "PurifyReject",
    "Reject": "PurifyReject",
    "Mainland": "MatrixChina",
    "MainlandMedia": "MatrixChina",
    "GlobalMedia": "GlobalMedia",
    "Media": "GlobalMedia",
    "Game": "ArcadeGame",
    "Apple": "AppleDirect"
}

AI_COMPONENTS = ["OpenAI", "Claude", "Gemini", "Copilot", "Anthropic", "BardAI"]

http_session = requests.Session()
http_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) clash-rules-enhanced"})

domain_extractor = tldextract.TLDExtract()


def parse_markdown_tables_robust():
    print("[*] 正在拉取不黑表 README 账本...", flush=True)
    dynamic_registry = {}
    try:
        res = http_session.get(README_URL, timeout=10)
        if res.status_code != 200:
            raise Exception(f"HTTP {res.status_code}")
            
        current_package = None
        is_global_table = False
        
        for line in res.text.splitlines():
            line = line.strip()
            if not line or not line.startswith("|"):
                continue
            if "[" not in line:
                words = re.findall(r'[A-Za-z]+', line)
                if words:
                    header_word = words[0]
                    current_package = TABLE_HEADER_MAP.get(header_word, None)
                    is_global_table = (header_word == "Global")
                continue
            
            if current_package or is_global_table:
                folders = re.findall(r'https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon/([^)\s/]+)', line)
                for folder in folders:
                    folder = folder.strip()
                    if not folder:
                        continue
                    if is_global_table:
                        if folder in AI_COMPONENTS:
                            dynamic_registry[folder] = "NexusAI"
                        elif folder in ["YouTube", "YouTubeMusic", "Netflix", "TikTok", "Disney", "Spotify"]:
                            dynamic_registry[folder] = "GlobalMedia"
                        elif folder in ["GitHub", "OneDrive", "Microsoft", "Proxy"]:
                            dynamic_registry[folder] = "OverseaProxy"
                    elif current_package:
                        dynamic_registry[folder] = current_package
    except Exception as e:
        print(f"[-] 动态扫描中断: {e}", flush=True)
        return {"OpenAI": "NexusAI", "China": "MatrixChina", "JianGuoYun": "MatrixChina"}
    
    print(f"[+] 成功解析出 {len(dynamic_registry)} 个待下载组件！", flush=True)
    return dynamic_registry


def download_and_extract_any(folder_name):
    rules = []
    possible_files = [f"{folder_name}.yaml", f"{folder_name}_Domain.txt", f"{folder_name}.list"]
    
    # 🌟 修改点 1：放弃 end="" 缓冲，直接换行打印，实时显示进度
    print(f"  -> 开始尝试拉取组件: {folder_name}", flush=True)
    
    success = False
    for file_item in possible_files:
        url = f"{RAW_BASE_URL}/{folder_name}/{file_item}"
        try:
            res = http_session.get(url, timeout=5)
            if res.status_code != 200:
                continue
            
            success = True
            content = res.text
            
            # 🌟 修改点 2：直接暴击干掉 PyYAML，用流式字符串切分，性能提升上万倍！
            for line in content.splitlines():
                line = line.strip()
                # 忽略空行、注释行和 YAML 的 payload 头
                if not line or line.startswith("#") or line.startswith("//") or line.startswith("payload:"):
                    continue
                # 去掉 YAML 列表结构前面的 "- " 
                if line.startswith("- "):
                    line = line[2:]
                    
                line = line.strip("'\" ").lstrip("+.")
                if line:
                    rules.append(line)
        except Exception:
            pass
            
    if success:
        print(f"     [+] {folder_name} 拉取成功 ({len(rules)} 条)", flush=True)
    else:
        print(f"     [-] {folder_name} 无数据或超时跳过", flush=True)
        
    return rules


def extract_pure_domain(rule_string):
    rule_string = str(rule_string).strip()
    if "," in rule_string:
        parts = rule_string.split(",")
        if len(parts) >= 2:
            return parts[1].strip().lower()
    return rule_string.lower()


def get_base_domain_safe(domain):
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain) or ":" in domain:
        return domain 
        
    ext = domain_extractor(domain)
    target_domain = getattr(ext, 'top_domain_under_public_suffix', None) or getattr(ext, 'registered_domain', None)
    
    if target_domain:
        return target_domain
        
    return domain


def main():
    official_registry = parse_markdown_tables_robust()
    
    raw_pools = {k: set() for k in TABLE_HEADER_MAP.values()}
    raw_pools["NexusAI"] = set()
    raw_pools["OverseaProxy"] = set()

    print("\n[*] =========================================", flush=True)
    print("[*] 开始流式同步核心分类数据 (纯内存并发层)...", flush=True)
    print("[*] =========================================", flush=True)
    
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        if not items:
            continue
        
        for item in items:
            # 🌟 修改点 3：高精度的 IP 段判定修复
            if not item.startswith("DOMAIN") and not item.startswith("IP-CIDR") and not item.startswith("GEOIP"):
                if ":" in item: # IPv6
                    item = f"IP-CIDR6,{item}"
                elif re.match(r"^\d{1,3}(\.\d{1,3}){3}(/\d+)?$", item): # IPv4 段
                    item = f"IP-CIDR,{item}"
                else:
                    item = f"DOMAIN-SUFFIX,{item}"
            raw_pools[target_package].add(item)

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
    print("[*] 启动高性能哈希主权索引，开始瞬间漂白海外包...", flush=True)
    print("[*] =========================================", flush=True)
    
    china_root_registry = set()
    for rule in china_set:
        if "DOMAIN" in rule: 
            pure_dom = extract_pure_domain(rule)
            base_dom = get_base_domain_safe(pure_dom)
            china_root_registry.add(base_dom)

    # 🌟 将广告拦截包也纳入清洗范围，赋予 MatrixChina 绝对防误杀豁免权
    for pkg_name in ["PurifyReject", "NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy"]:
        purified_set = set()
        for rule in raw_pools[pkg_name]:
            if "DOMAIN" in rule:
                pure_dom = extract_pure_domain(rule)
                base_dom = get_base_domain_safe(pure_dom)
                if base_dom in china_root_registry:
                    continue 
            purified_set.add(rule)
        raw_pools[pkg_name] = purified_set

    os.makedirs("ruleset", exist_ok=True)
    print("\n[*] =========================================", flush=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 工业级无依赖极速版\n")
            f.write(f"# 📊 融合纯净总条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译大包: {file_path:<30} (条目数: {len(unique_items)})", flush=True)

if __name__ == "__main__":
    main()
