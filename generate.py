import os
import re
import requests
import yaml

# 使用你提供的这个真实文本的上游基础链接
README_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/README.md"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"

# =================================================================
# 🎯 核心映射：将不黑表 Markdown 表格的 Header 1:1 映射到你的黄金大包
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

# 针对 AI 类的特殊提取名单（因为黑客把它们全部混在了 Global 大表格中，我们单独捞出来）
AI_COMPONENTS = ["OpenAI", "Claude", "Gemini", "Copilot", "Anthropic", "BardAI"]

def parse_markdown_tables():
    """解析不黑表独特的 Markdown 表格账本，实现 100% 完美的动态组件分类记录"""
    print("[*] 开始深度解构不黑表最新的 Markdown 表格账本...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 初始化动态账本：{ "JianGuoYun": "MatrixChina", "OpenAI": "NexusAI" }
    dynamic_registry = {}
    
    try:
        res = requests.get(README_URL, headers=headers, timeout=20)
        if res.status_code != 200:
            raise Exception(f"HTTP {res.status_code}")
            
        content = res.text
        
        # 1. 使用正则把每一个独立的表格和它的 Header 拆分出来
        # 匹配形如 |📵Advertising| ... 和接下来的表格块
        table_blocks = re.split(r'\|\s*[^|\n]*?(?:[A-Za-z]+)[^|\n]*?\|', content)
        headers_found = re.findall(r'\|\s*[^|\n]*?([A-Za-z]+)[^|\n]*?\|', content)
        
        # 2. 逐个表格块解析内部的超链接
        for idx, raw_header in enumerate(headers_found):
            header_clean = raw_header.strip()
            # 判断该表格属于哪个目标大包
            target_package = TABLE_HEADER_MAP.get(header_clean, None)
            
            # 特殊情况处理：如果是 Global 表格，我们要在里面筛选 AI 组件，其余不属于大厂的默认丢给兜底包
            is_global_table = (header_clean == "Global")
            
            # 获取对应的表格文本块
            if idx + 1 < len(table_blocks):
                block_content = table_blocks[idx + 1]
                # 正则捞出所有形如 [组件名](链接) 里的组件文件夹名字
                links = re.findall(r'\[.*?\]\(https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon/(.*?)\)', block_content)
                
                for folder in links:
                    folder = folder.strip()
                    if not folder:
                        continue
                    
                    # 划分逻辑：
                    if is_global_table:
                        if folder in AI_COMPONENTS:
                            dynamic_registry[folder] = "NexusAI"
                        elif folder in ["YouTube", "YouTubeMusic", "Netflix", "TikTok", "Disney", "Spotify"]:
                            dynamic_registry[folder] = "GlobalMedia"
                        elif folder in ["GitHub", "OneDrive", "Microsoft"]:
                            dynamic_registry[folder] = "OverseaProxy"
                    elif target_package:
                        dynamic_registry[folder] = target_package

    except Exception as e:
        print(f"[-] 动态表格解析中断: {e}。触发保底高频白名单。")
        return {"OpenAI": "NexusAI", "Claude": "NexusAI", "Gemini": "NexusAI", "Copilot": "NexusAI", "China": "MatrixChina", "JianGuoYun": "MatrixChina", "Apple": "AppleDirect", "Advertising": "PurifyReject", "YouTube": "GlobalMedia", "Netflix": "GlobalMedia", "Steam": "ArcadeGame"}

    print(f"[+] 账本动态解析大获成功！已精准归类 {len(dynamic_registry)} 个官方主线表格组件。")
    return dynamic_registry

def download_and_extract_any(folder_name):
    """高弹性多轨扫描：依次尝试解析 .yaml, _Domain.txt, .list"""
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
        f.write(f"# 🛡️ clash-rules-enhanced 真实表格数据驱动版\n")
        f.write(f"# 📊 融合总条目: {len(unique_items)} 条\n")
        f.write("# ===================================================\n")
        f.write("payload:\n")
        for rule in unique_items:
            f.write(f"  - {rule}\n")
    print(f"[+] 成功编译大包: {file_path} (条目数: {len(unique_items)})")

def main():
    # 1. 动用表格清洗爬虫机制去剥离分类
    official_registry = parse_markdown_tables()
    
    pools = {
        "NexusAI": [],
        "GlobalMedia": [],
        "ArcadeGame": [],
        "PurifyReject": [],
        "MatrixChina": [],
        "AppleDirect": [],
        "OverseaProxy": []
    }

    # 2. 流式注入下载
    print("[*] 开始流式清洗不黑表全库核心分类数据...")
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        if not items:
            continue
        pools[target_package].extend(items)

    # 3. 稳固提取基础 Proxy 大包放入 OverseaProxy 兜底
    try:
        extra_proxy = download_and_extract_any("Proxy")
        pools["OverseaProxy"].extend(extra_proxy)
    except:
        pass

    # 4. 融合 Loyalsoldier 与 17mon 路由表
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
        print(f"[-] 附加库并入跳过: {e}")

    # 5. 发布
    for key, value in pools.items():
        write_to_ruleset(key, value)

if __name__ == "__main__":
    main()
