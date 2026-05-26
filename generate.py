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
    # 🤖 AI 大模型
    "AI": ["openai", "chatgpt", "claude", "gemini", "bard", "copilot", "perplexity", "midjourney", "cursor", "anthropic", "cohere", "huggingface", "poe", "llm"],
    
    # 🎬 流媒体与视听娱乐
    "Media": ["netflix", "disney", "youtube", "spotify", "hulu", "hbo", "amazon", "prime", "appletv", "paramount", "peacock", "bilibiliintl", "tiktok", "twitch", "deezer", "soundcloud", "abc", "abema", "all4", "bbc", "danmu", "fox", "gaga", "jcom", "kktv", "mgtvintl", "mytv", "pandalive", "pbs", "pixiv", "plextv", "qobuz", "radiko", "viutv", "weetv"],
    
    # 🎮 游戏平台与加速
    "Game": ["steam", "epic", "ea", "uplay", "ubisoft", "origin", "nintendo", "playstation", "xbox", "blizzard", "riot", "pubg", "genshin", "apex", "gog", "pso2", "sony", "wargaming"],
    
    # 🛑 广告、追踪与隐私拦截
    "Reject": ["advertising", "privacy", "telemetry", "anti-ad", "stopad", "hijacking", "adblock", "spidertracking"],
    
    # 🇨🇳 中国大陆本土服务（物理网卡 IPv6 直连的核心主力）
    "China": ["china", "direct", "cn", "bilibili", "tencent", "ali", "baidu", "netease", "jd", "meituan", "weibo", "zhihu", "taobao", "douyin", "ximalaya", "iqiyi", "youku", "unionpay", "icbc", "ccb", "boc", "abcbank", "cmb", "spdb", "cib", "gdb", "pingan", "huawei", "xiaomi", "vivo", "oppo", "coolapk"],
    
    # 🍏 Apple 特殊直连（强力建议直连，保证国行设备系统功能和 IPv6 握手）
    "Apple": ["apple", "icloud", "testflight", "itunes", "macbook", "weather", "location", "maps"]
}

def get_all_rule_folders():
    """直接调用 GitHub API 遍历目录，百分之百捕获黑客全库的所有文件夹"""
    print("[*] 正在请求 GitHub API 实时同步不黑表全库目录树...")
    folders = []
    try:
        # 增加 headers 规避 GitHub 针对匿名请求的频控限制
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(API_URL, headers=headers, timeout=20)
        if res.status_code == 200:
            items = res.json()
            for item in items:
                if item["type"] == "dir":
                    folders.append(item["name"])
        else:
            print(f"[-] API 请求受阻 (Status: {res.status_code})，切换至高容错硬核保底库...")
            raise Exception("API Limit")
    except Exception:
        # 终极硬核容错名单（确保 API 被限制时依旧能高效率完成核心分类）
        return [
            "OpenAI", "Claude", "Gemini", "Copilot", "Telegram", "YouTube", "Netflix", 
            "Steam", "GitHub", "Microsoft", "China", "Apple", "Advertising", "Speedtest",
            "TikTok", "Spotify", "Developer", "Epic", "Nintendo", "GlobalMedia"
        ]
    
    print(f"[+] 动态捕获成功！当前不黑表库包含共计 {len(folders)} 个独立应用文件夹。")
    return folders

def download_and_extract_yaml(folder_name):
    """进入应用文件夹，精准下载同名 .yaml 规则并洗出数据行"""
    url = f"{RAW_BASE_URL}/{folder_name}/{folder_name}.yaml"
    rules = []
    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            return rules
        
        content = res.text
        # 如果包含标准的 payload 结构，用 yaml 库解析
        if "payload:" in content:
            try:
                parsed = yaml.safe_load(content)
                if parsed and "payload" in parsed and isinstance(parsed["payload"], list):
                    return parsed["payload"]
            except:
                pass
        
        # 强力降级解析：按行切分提取
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
    """统一重组，以最高兼容度的 yaml 格式向 ruleset/ 输出成果"""
    os.makedirs("ruleset", exist_ok=True)
    file_path = os.path.join("ruleset", filename)
    
    # 彻底清洗去重
    unique_items = sorted(list(set([str(i).strip("'\" ") for i in r_list if i])))
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# ===================================================\n")
        f.write("# 个人定制全矩阵大聚合规则包 (GitHub Actions 每日流式更新)\n")
        f.write(f"# 当前融合总条目: {len(unique_items)} 条\n")
        f.write("# ===================================================\n")
        f.write("payload:\n")
        for rule in unique_items:
            f.write(f"  - {rule}\n")
    print(f"[+] 成功编译大包: {file_path} (条目数: {len(unique_items)})")

def main():
    folders = get_all_rule_folders()
    
    # 建立分类容器
    pools = {
        "custom_ai": [],
        "custom_media": [],
        "custom_game": [],
        "custom_reject": [],
        "custom_china": [],
        "custom_apple": [],
        "custom_proxy_remain": []
    }

    print("[*] 正在跨矩阵下载上百个规则文件并启动分类流（请耐心等待）...")
    for idx, folder in enumerate(folders, 1):
        folder_lower = folder.lower()
        items = download_and_extract_yaml(folder)
        if not items:
            continue
            
        # 流式智能检索分类
        matched = False
        for category, keywords in CATEGORY_MAPPING.items():
            if any(kw in folder_lower for kw in keywords):
                pools[f"custom_{category.lower()}"].extend(items)
                matched = True
                break
        
        if not matched:
            # 其余既不属于直连也不属于媒体/游戏的，通通打入常规海外中转大包
            pools["custom_proxy_remain"].extend(items)

    # 补充并入 Loyalsoldier 与 17mon 的真传，死死捍卫国内直连和原生 IPv6 的准确度
    print("[*] 正在并入基线直连流控和 17mon 中国大陆地区 IP 路由表...")
    try:
        ls_direct = requests.get("https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt").text.splitlines()
        pools["custom_china"].extend([l.strip() for l in ls_direct if l.strip() and not l.startswith("#")])
        
        raw_ips = requests.get("https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt").text.splitlines()
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                pools["custom_china"].append(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 基线库附加失败（跳过）: {e}")

    # =================================================================
    # 开始向本地写入这六个完美的黄金大包
    # =================================================================
    write_to_ruleset("custom_ai.yaml", pools["custom_ai"])
    write_to_ruleset("custom_media.yaml", pools["custom_media"])
    write_to_ruleset("custom_game.yaml", pools["custom_game"])
    write_to_ruleset("custom_reject.yaml", pools["custom_reject"])
    write_to_ruleset("custom_china.yaml", pools["custom_china"])
    write_to_ruleset("custom_apple.yaml", pools["custom_apple"])
    write_to_ruleset("custom_proxy_remain.yaml", pools["custom_proxy_remain"])

if __name__ == "__main__":
    main()
