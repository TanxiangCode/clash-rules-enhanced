import os
import re
import requests
import yaml

# 使用你提供的真实文本上游链接
README_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/README.md"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"

# =================================================================
# 🎯 核心映射：精准 1:1 对接不黑表 Markdown 真实表头关键字
# =================================================================
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

# 针对 AI 类的特殊提取名单
AI_COMPONENTS = ["OpenAI", "Claude", "Gemini", "Copilot", "Anthropic", "BardAI"]

def parse_markdown_tables_robust():
    """采用极其稳健的逐行状态机扫描法，彻底规避 Emoji 干扰与空格陷阱"""
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
            if not line:
                continue
                
            # 1. 状态机：捕获表头行 (形如 |📵Advertising| 或 |🇨🇳Mainland|)
            # 只要这一行是表格行，且不含 [ (说明不是链接行)，并且里面含有关键英文大项
            if line.startswith("|") and "[" not in line:
                # 用正则把这行所有的英文单词洗出来
                words = re.findall(r'[A-Za-z]+', line)
                if words:
                    header_word = words[0] # 拿到类似 Advertising, Mainland, Global
                    current_package = TABLE_HEADER_MAP.get(header_word, None)
                    is_global_table = (header_word == "Global")
                continue
            
            # 2. 数据提取：在当前分类状态下，抓取这一行所有的组件链接
            if (current_package or is_global_table) and line.startswith("|"):
                # 精准抽取链接中 Loon/ 后面直到右括号 ) 之间的非空白组件名
                folders = re.findall(r'https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon/([^)\s/]+)', line)
                
                for folder in folders:
                    folder = folder.strip()
                    if not folder:
                        continue
                    
                    if is_global_table:
                        # 细分 Global 表格中的组件
                        if folder in AI_COMPONENTS:
                            dynamic_registry[folder] = "NexusAI"
                        elif folder in ["YouTube", "YouTubeMusic", "Netflix", "TikTok", "Disney", "Spotify"]:
                            dynamic_registry[folder] = "GlobalMedia"
                        elif folder in ["GitHub", "OneDrive", "Microsoft", "Proxy"]:
                            dynamic_registry[folder] = "OverseaProxy"
                    elif current_package:
                        dynamic_registry[folder] = current_package

    except Exception as e:
        print(f"[-] 动态扫描中断: {e}。触发保底基线。")
        return {"OpenAI": "NexusAI", "Claude": "NexusAI", "Gemini": "NexusAI", "Copilot": "NexusAI", "China": "MatrixChina", "JianGuoYun": "MatrixChina", "Apple": "AppleDirect", "Advertising": "PurifyReject", "YouTube": "GlobalMedia", "Netflix": "GlobalMedia", "Steam": "ArcadeGame"}

    print(f"[+] 扫描成功！已动态拉取并归类了 {len(dynamic_registry)} 个不黑表表格组件。")
    return dynamic_registry

def download_and_extract_any(folder_name):
    """多轨扫描：依次尝试解析 .yaml, _Domain.txt, .list"""
    rules = []
    possible_files = [
        f"{folder_name}.yaml",
        f"{folder_name}_Domain.txt",
        f"{folder_name}.list"
    ]
    
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

def write_to_ruleset(filename, r_list):
    """写出标准分流大包"""
    os.makedirs("ruleset", exist_ok=True)
    file_path = os.path.join("ruleset", f"{filename}.yaml")
    
    cleaned_items = []
    for item in r_list:
        item = str(item).strip("'\" ")
        if not item or item.startswith("#") or item.lower().startswith("payload"):
            continue
        if not item.startswith("DOMAIN") and not item.startswith("IP-IDR") and not item.startswith("GEOIP"):
            if ":" in item or (item.replace('.', '').isdigit() and '/' in item):
                item = f"IP-CIDR6,{item}" if ":" in item else f"IP-CIDR,{item}"
            else:
                item = f"DOMAIN-SUFFIX,{item}"
        cleaned_items.append(item)
        
    unique_items = sorted(list(set(cleaned_items)))
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# ===================================================\n")
        f.write(f"# 🛡️ clash-rules-enhanced 状态机解析版\n")
        f.write(f"# 📊 融合总条目: {len(unique_items)} 条\n")
        f.write("# ===================================================\n")
        f.write("payload:\n")
        for rule in unique_items:
            f.write(f"  - {rule}\n")
    print(f"[+] 成功编译高端大包: {file_path} (条目数: {len(unique_items)})")

def main():
    # 动用多容错状态机去扫描账本
    official_registry = parse_markdown_tables_robust()
    
    pools = {
        "NexusAI": [],
        "GlobalMedia": [],
        "ArcadeGame": [],
        "PurifyReject": [],
        "MatrixChina": [],
        "AppleDirect": [],
        "OverseaProxy": []
    }

    print("[*] 开始流式清洗不黑表全库核心分类数据...")
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        if not items:
            continue
        pools[target_package].extend(items)

    try:
        extra_proxy = download_and_extract_any("Proxy")
        pools["OverseaProxy"].extend(extra_proxy)
    except:
        pass

    print("[*] 正在并入基线核心直连流和 17mon 中国大陆 IP 路由表...")
    try:
        ls_direct = requests.get("https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt").text.splitlines()
        pools["MatrixChina"].extend([l.strip() for l in ls_direct if l.strip() and not l.startswith("#")])
        
        raw_ips = requests.get("https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt").text.splitlines()
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                pools["MatrixChina"].append(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 基线并入跳过: {e}")

    for key, value in pools.items():
        write_to_ruleset(key, value)

if __name__ == "__main__":
    main()
