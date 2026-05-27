import os
import re
import requests
import yaml

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

def parse_markdown_tables_robust():
    """通过逐行状态机扫描账本表格"""
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
    """
    🌟【语义提取器核心】：从任意类型的规则字符串中强行榨取出核心域名
    输入: 'DOMAIN,www.bilibili.com'       -> 输出: 'www.bilibili.com'
    输入: 'DOMAIN-SUFFIX,bilibili.com'  -> 输出: 'bilibili.com'
    """
    rule_string = str(rule_string).strip()
    if "," in rule_string:
        parts = rule_string.split(",")
        if len(parts) >= 2:
            return parts[1].strip().lower()
    return rule_string.lower()

def main():
    official_registry = parse_markdown_tables_robust()
    
    # 建立原始名单容器（存储带前缀的原始文本，方便最后输出）
    raw_pools = {k: set() for k in TABLE_HEADER_MAP.values()}
    raw_pools["NexusAI"] = set()
    raw_pools["OverseaProxy"] = set()

    print("[*] 开始流式清洗不黑表全库核心分类数据...")
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        if not items:
            continue
        
        # 统一格式规整化
        for item in items:
            item = str(item).strip("'\" ")
            if not item or item.startswith("#") or item.lower().startswith("payload"):
                continue
            if not item.startswith("DOMAIN") and not item.startswith("IP-IDR") and not item.startswith("GEOIP"):
                if ":" in item or (item.replace('.', '').isdigit() and '/' in item):
                    item = f"IP-CIDR6,{item}" if ":" in item else f"IP-CIDR,{item}"
                else:
                    item = f"DOMAIN-SUFFIX,{item}"
            raw_pools[target_package].add(item)

    # 1. 优先构筑你最高主权的中国大陆直连大包基线
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
    # 2. 🔥【语义化高精去重引擎】：彻底破解 DOMAIN 与 DOMAIN-SUFFIX 字面错位陷阱
    # =================================================================
    print("[*] 启动语义化多维清洗引擎，开始深度格式剥离比对...")
    
    # 第一步：把 MatrixChina（国内包）里所有的纯域名和基础域名特征全部提炼成一个语义索引库
    china_domain_registry = set()
    for rule in china_set:
        pure_dom = extract_pure_domain(rule)
        china_domain_registry.add(pure_dom)

    # 第二步：对海外大包进行像素级的差集清洗
    for pkg_name in ["NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy"]:
        purified_set = set()
        
        for rule in raw_pools[pkg_name]:
            pure_dom = extract_pure_domain(rule)
            
            # 语义阻断核心：
            # 1. 如果海外包里的具体域名（如 www.bilibili.com）直接撞上了国内包里的基础索引
            # 2. 或者海外包里的具体域名（如 api.bilibili.com）其后缀（bilibili.com）存在于国内包中
            # 那么这行规则将被彻底视为“叛徒规则”，无条件进行抹除（不并入 purified_set）
            is_traitor = False
            if pure_dom in china_domain_registry:
                is_traitor = True
            else:
                # 针对 DOMAIN 与 DOMAIN-SUFFIX 的交叉边界防御
                # 检查当前海外域名是否以国内包里的任何一个直连域名后缀结尾
                for c_dom in china_domain_registry:
                    if pure_dom.endswith(f".{c_dom}"):
                        is_traitor = True
                        break
            
            if not is_traitor:
                purified_set.add(rule)
                
        raw_pools[pkg_name] = purified_set

    # 3. 序列化全量输出
    os.makedirs("ruleset", exist_ok=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 语义层像素级去重版\n")
            f.write(f"# 📊 融合纯净总条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译纯净化大包: {file_path} (条目数: {len(unique_items)})")

if __name__ == "__main__":
    main()
