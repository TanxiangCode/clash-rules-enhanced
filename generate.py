import os
import re
import requests
import yaml
import tldextract  # 引入工业级公共后缀(PSL)解析库

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

# 🌟 全局初始化提取器（提取时会自动去网络同步/读取本地最新的 Mozilla PSL 数据库）
# 仅消耗一次初始化时间，后续百万次提取都是纯内存极速操作
domain_extractor = tldextract.TLDExtract()


def parse_markdown_tables_robust():
    """逐行状态机扫描账本"""
    print("[*] 正在通过逐行扫描流深度解构不黑表表格账本...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    dynamic_registry = {}
    try:
        res = requests.get(README_URL, headers=headers, timeout=20)
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
        print(f"[-] 动态扫描中断: {e}。触发保底。")
        return {"OpenAI": "NexusAI", "China": "MatrixChina", "JianGuoYun": "MatrixChina", "Apple": "AppleDirect", "Advertising": "PurifyReject", "YouTube": "GlobalMedia", "Steam": "ArcadeGame"}
    return dynamic_registry


def download_and_extract_any(folder_name):
    """高弹性多轨扫描：依次尝试解析 .yaml, _Domain.txt, .list"""
    rules = []
    possible_files = [f"{folder_name}.yaml", f"{folder_name}_Domain.txt", f"{folder_name}.list"]
    for file_item in possible_files:
        url = f"{RAW_BASE_URL}/{folder_name}/{file_item}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                continue
            content = res.text
            if "payload:" in content and file_item.endswith(".yaml"):
                try:
                    parsed = yaml.safe_load(content)
                    if parsed and "payload" in parsed and isinstance(parsed["payload"], list):
                        rules.extend(parsed["payload"])
                        continue
                except:
                    pass
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//") or line.startswith("payload:"):
                    continue
                if line.startswith("- "):
                    line = line[2:]
                line = line.lstrip("+.")
                rules.append(line.strip("'\" "))
        except:
            pass
    return rules


def extract_pure_domain(rule_string):
    """从规则字符串中剥离出纯域名文本"""
    rule_string = str(rule_string).strip()
    if "," in rule_string:
        parts = rule_string.split(",")
        if len(parts) >= 2:
            return parts[1].strip().lower()
    return rule_string.lower()


def get_base_domain_safe(domain):
    """
    🛡️【安全级根主权提取算法】
    依靠 Mozilla Public Suffix List 确保绝对的边界安全，防雪崩！
    """
    # 规避纯 IP 地址被当成域名解析的风险
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain) or ":" in domain:
        return domain 
        
    ext = domain_extractor(domain)
    # registered_domain 会安全地返回：
    # api.bilibili.com -> bilibili.com
    # a.b.co.uk -> b.co.uk
    # tanxiang.github.io -> tanxiang.github.io (完美规避 SaaS 误杀)
    if ext.registered_domain:
        return ext.registered_domain
    
    # 如果是 local, localhost 等极其特殊的无后缀域名，原样返回
    return domain


def main():
    official_registry = parse_markdown_tables_robust()
    
    raw_pools = {k: set() for k in TABLE_HEADER_MAP.values()}
    raw_pools["NexusAI"] = set()
    raw_pools["OverseaProxy"] = set()

    print("[*] 开始流式同步不黑表全库核心分类数据...")
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        if not items:
            continue
        
        for item in items:
            item = str(item).strip("'\" ")
            if not item or item.startswith("#") or item.lower().startswith("payload"):
                continue
            # 统一规整前缀格式
            if not item.startswith("DOMAIN") and not item.startswith("IP-IDR") and not item.startswith("GEOIP"):
                if ":" in item or (item.replace('.', '').isdigit() and '/' in item):
                    item = f"IP-CIDR6,{item}" if ":" in item else f"IP-CIDR,{item}"
                else:
                    item = f"DOMAIN-SUFFIX,{item}"
            raw_pools[target_package].add(item)

    print("[*] 正在并入 Loyalsoldier 与 17mon 基线数据...")
    china_set = raw_pools["MatrixChina"]
    try:
        ls_direct = requests.get("https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt").text.splitlines()
        for l in ls_direct:
            l = l.strip()
            if l and not l.startswith("#"):
                china_set.add(f"DOMAIN-SUFFIX,{l.lstrip('+.')}" if not l.startswith("DOMAIN") else l)
        
        raw_ips = requests.get("https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt").text.splitlines()
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                china_set.add(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 基线并入跳过: {e}")

    # =================================================================
    # 2. 🛡️【安全哈希去重引擎】：基于 PSL 数据库的防雪崩清洗，极速 O(1) 查表
    # =================================================================
    print("[*] 启动高性能哈希主权索引，开始瞬间漂白海外包...")
    
    # 建立中国区绝对主权的哈希索引库
    china_root_registry = set()
    for rule in china_set:
        if "DOMAIN" in rule: 
            pure_dom = extract_pure_domain(rule)
            base_dom = get_base_domain_safe(pure_dom)
            china_root_registry.add(base_dom)

    # 查表过滤海外包，O(1) 复杂度绝杀
    for pkg_name in ["NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy"]:
        purified_set = set()
        for rule in raw_pools[pkg_name]:
            if "DOMAIN" in rule:
                pure_dom = extract_pure_domain(rule)
                base_dom = get_base_domain_safe(pure_dom)
                
                # 如果这个海外规则的根主权已经被划归中国直连，直接物理剔除！
                if base_dom in china_root_registry:
                    continue 
            purified_set.add(rule)
        raw_pools[pkg_name] = purified_set

    # 3. 序列化全量输出
    os.makedirs("ruleset", exist_ok=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 工业级安全极速清洗版\n")
            f.write(f"# 📊 融合纯净总条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译纯净化大包: {file_path} (条目数: {len(unique_items)})")


if __name__ == "__main__":
    main()
