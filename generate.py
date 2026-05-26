import os
import requests
import yaml

# 不黑表 Clash 规则在 GitHub 的真实基础路径
API_URL = "https://api.github.com/repos/blackmatrix7/ios_rule_script/contents/rule/Clash"
RAW_BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"

# =================================================================
# ⚙️ 核心：分类关键词映射矩阵（全自动流式智能分类）
# =================================================================
CATEGORY_MAPPING = {
    "NexusAI": ["openai", "chatgpt", "claude", "gemini", "bard", "copilot", "perplexity", "midjourney", "cursor", "anthropic", "cohere", "huggingface", "poe", "llm"],
    "GlobalMedia": ["netflix", "disney", "youtube", "spotify", "hulu", "hbo", "amazon", "prime", "appletv", "paramount", "peacock", "bilibiliintl", "tiktok", "twitch", "deezer", "soundcloud", "abc", "abema", "all4", "bbc", "danmu", "fox", "gaga", "jcom", "kktv", "mgtvintl", "mytv", "pandalive", "pbs", "pixiv", "plextv", "qobuz", "radiko", "viutv", "weetv"],
    "ArcadeGame": ["steam", "epic", "ea", "uplay", "ubisoft", "origin", "nintendo", "playstation", "xbox", "blizzard", "riot", "pubg", "genshin", "apex", "gog", "pso2", "sony", "wargaming"],
    "PurifyReject": ["advertising", "privacy", "telemetry", "anti-ad", "stopad", "hijacking", "adblock", "spidertracking"],
    "MatrixChina": ["china", "direct", "cn", "bilibili", "tencent", "ali", "baidu", "netease", "jd", "meituan", "weibo", "zhihu", "taobao", "douyin", "ximalaya", "iqiyi", "youku", "unionpay", "icbc", "ccb", "boc", "abcbank", "cmb", "spdb", "cib", "gdb", "pingan", "huawei", "xiaomi", "vivo", "oppo", "coolapk"],
    "AppleDirect": ["apple", "icloud", "testflight", "itunes", "macbook", "weather", "location", "maps"]
}

def get_all_rule_folders():
    """调用 GitHub API 遍历目录，百分之百捕获黑客全库的所有文件夹"""
    print("[*] 正在请求 GitHub API 实时同步不黑表全库目录树...")
    folders = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(API_URL, headers=headers, timeout=20)
        if res.status_code == 200:
            items = res.json()
            for item in items:
                if item["type"] == "dir":
                    folders.append(item["name"])
        else:
            raise Exception("API Limit")
    except Exception:
        # 终极硬核容错保底名单
        return ["OpenAI", "Claude", "Gemini", "Copilot", "Telegram", "YouTube", "Netflix", "Steam", "GitHub", "Microsoft", "China", "Apple", "Advertising", "TikTok", "Spotify", "Epic", "Nintendo"]
    return folders

def download_and_extract_yaml(folder_name):
    """提取单个细分规则的 yaml 内部 payload 数据行"""
    url = f"{RAW_BASE_URL}/{folder_name}/{folder_name}.yaml"
    rules = []
    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            return rules
        content = res.text
        if "payload:" in content:
            try:
                parsed = yaml.safe_load(content)
                if parsed and "payload" in parsed and isinstance(parsed["payload"], list):
                    return parsed["payload"]
            except:
                pass
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//") or line.startswith("payload:"):
                continue
            if line.startswith("- "):
                line = line[2:]
            rules.append(line.strip("'\" "))
    except:
        pass
    return rules

def write_to_ruleset(filename, r_list):
    """统一写出为优雅的、高级的专属 YAML 大包"""
    os.makedirs("ruleset", exist_ok=True)
    file_path = os.path.join("ruleset", f"{filename}.yaml")
    
    unique_items = sorted(list(set([str(i).strip("'\" ") for i in r_list if i])))
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# ===================================================\n")
        f.write(f"# 🛡️ clash-rules-enhanced 高级矩阵分流大包\n")
        f.write(f"# 🔄 GitHub Actions 每日流式洗盐自动更新\n")
        f.write(f"# 📊 融合总条目: {len(unique_items)} 条\n")
        f.write("# ===================================================\n")
        f.write("payload:\n")
        for rule in unique_items:
            f.write(f"  - {rule}\n")
    print(f"[+] 成功编译高端大包: {file_path} (条目数: {len(unique_items)})")

def main():
    folders = get_all_rule_folders()
    
    # 容器初始化
    pools = {
        "NexusAI": [],
        "GlobalMedia": [],
        "ArcadeGame": [],
        "PurifyReject": [],
        "MatrixChina": [],
        "AppleDirect": [],
        "OverseaProxy": []
    }

    print(f"[*] 成功连接，检测到共计 {len(folders)} 个细分上游组件，开始深度重组...")
    for folder in folders:
        folder_lower = folder.lower()
        items = download_and_extract_yaml(folder)
        if not items:
            continue
            
        matched = False
        for category, keywords in CATEGORY_MAPPING.items():
            if any(kw in folder_lower for kw in keywords):
                pools[category].extend(items)
                matched = True
                break
        
        if not matched:
            pools["OverseaProxy"].extend(items)

    # 并入基线流控数据与 17mon 权威中国大陆 IP 路由表
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
        print(f"[-] 附加库并入由于网络原因跳过: {e}")

    # 循环写入文件
    for key, value in pools.items():
        write_to_ruleset(key, value)

if __name__ == "__main__":
    main()
