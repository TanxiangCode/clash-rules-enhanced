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

def standardize_rules(r_list):
    """规范化并洗净单条规则行格式"""
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
    return set(cleaned_items) # 🌟 核心改动：返回集合（Set）以便进行高级数学交差集运算

def main():
    official_registry = parse_markdown_tables_robust()
    
    # 建立独立容器，先用集合（Set）承载
    raw_pools = {k: set() for k in TABLE_HEADER_MAP.values()}
    raw_pools["NexusAI"] = set()
    raw_pools["OverseaProxy"] = set()

    print("[*] 开始流式清洗不黑表全库核心分类数据...")
    for folder, target_package in official_registry.items():
        items = download_and_extract_any(folder)
        if not items:
            continue
        # 将清洗规整后的规则线，直接合并（Union）进集合
        raw_pools[target_package].update(standardize_rules(items))

    try:
        extra_proxy = download_and_extract_any("Proxy")
        raw_pools["OverseaProxy"].update(standardize_rules(extra_proxy))
    except:
        pass

    # 1. 优先构筑你最高主权的中国大陆直连大包
    print("[*] 正在构筑中国大陆直连包基线（并入 Loyalsoldier 与 17mon）...")
    china_set = raw_pools["MatrixChina"]
    try:
        ls_direct = requests.get("https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt").text.splitlines()
        china_set.update(standardize_rules([l.strip() for l in ls_direct if l.strip() and not l.startswith("#")]))
        
        raw_ips = requests.get("https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt").text.splitlines()
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                china_set.add(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 基线并入跳过: {e}")

    # 2. 🌟【终极净化算法】：利用集合差集，让所有海外包无条件剔除直连包里的重叠条目！
    # 作用：只要一个域名被 MatrixChina 判定为直连，它在国外包里就必须被瞬间物理抹除
    for pkg_name in ["NexusAI", "GlobalMedia", "ArcadeGame", "OverseaProxy"]:
        raw_pools[pkg_name] = raw_pools[pkg_name] - china_set

    # 3. 序列化全量写出
    os.makedirs("ruleset", exist_ok=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 集合算法净化版\n")
            f.write(f"# 📊 融合纯净总条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译高端大包: {file_path} (条目数: {len(unique_items)})")

if __name__ == "__main__":
    main()
