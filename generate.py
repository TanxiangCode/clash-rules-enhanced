import os
import re
import requests
import yaml

# 不黑表 Clash 规则在 GitHub 的基础路径
BASE_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash"
# 通过不黑表的 README.md 来动态捕获所有规则项
README_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/README.md"

# =================================================================
# ⚙️ 核心：分类关键词映射矩阵 (脚本将根据规则名称自动流式分类)
# =================================================================
CATEGORY_MAPPING = {
    # 🤖 AI 大模型大聚合大包
    "AI": ["openai", "chatgpt", "claude", "gemini", "bard", "copilot", "perplexity", "midjourney", "cursor", "anthropic", "cohere", "huggingface", "poe"],
    
    # 🎬 全球主流海外流媒体/媒体大包
    "Media": ["netflix", "disney", "youtube", "spotify", "hulu", "hbo", "amazonprime", "appletv", "paramount", "peacock", "bilibiliintl", "tiktok", "twitch", "deezer", "soundcloud"],
    
    # 🎮 全球游戏平台大包
    "Game": ["steam", "epic", "ea", "uplay", "ubisoft", "origin", "nintendo", "playstation", "xbox", "blizzard", "riot", "pubg", "genshin"],
    
    # 🛑 广告、追踪与隐私拦截大包
    "Reject": ["advertising", "privacy", "telemetry", "anti-ad", "stopad", "hijacking"],
    
    # 🇨🇳 中国大陆专属服务/直连大包 (触发物理网卡原生 IPv6 的绝对主力)
    "China": ["china", "direct", "cn", "bilibili", "tencent", "ali", "baidu", "netease", "jd", "meituan", "weibo", "zhihu", "taobao", "douyin", "ximalaya", "iqiyi", "youku", "unionpay", "招商银行", "icbc", "ccb"],
    
    # 🍏 Apple 特殊服务直连 (通常建议直连以提升 IPv6 握手机率)
    "Apple": ["apple", "icloud", "testflight", "itunes", "macbook"]
}

def get_all_rule_names():
    """解析不黑表的 README.md，动态榨取里面包含的所有服务组件名称"""
    print("[*] 正在向 GitHub 请求不黑表最新 README 目录树...")
    rule_names = set()
    try:
        res = requests.get(README_URL, timeout=20)
        if res.status_code == 200:
            # 使用正则匹配不黑表 README 中类似 [OpenAI](OpenAI/OpenAI.yaml) 的链接结构
            matches = re.findall(r'\[(.*?)\]\((.*?)/(.*?)\.yaml\)', res.text)
            for match in matches:
                # match[1] 就是具体的文件夹名字 (如 OpenAI)
                folder_name = match[1].strip()
                if folder_name and "/" not in folder_name:
                    rule_names.add(folder_name)
    except Exception as e:
        print(f"[-] 解析 README 失败: {e}，将启用硬编码高频核心包进行降级保底。")
        # 降级保底名单，防止 GitHub 网络波动导致全盘皆空
        return ["OpenAI", "Claude", "Gemini", "Copilot", "Telegram", "YouTube", "Netflix", "Steam", "GitHub", "Microsoft", "China", "Apple", "Advertising"]
    
    print(f"[+] 成功捕获不黑表全库共计 {len(rule_names)} 个独立细分规则项！")
    return list(rule_names)

def download_and_extract(rule_name):
    """前往 GitHub 动态下载单个细分规则的 yaml，提取其 payload 内部条目"""
    url = f"{BASE_URL}/{rule_name}/{rule_name}.yaml"
    rules = []
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = yaml.safe_load(res.text)
            if data and "payload" in data and isinstance(data["payload"], list):
                return data["payload"]
    except Exception:
        pass
    return rules

def main():
    all_available_rules = get_all_rule_names()
    
    # 初始化我们最终要输出的五个黄金聚合容器
    pools = {
        "custom_ai": [],
        "custom_media": [],
        "custom_game": [],
        "custom_reject": [],
        "custom_china": [],
        "custom_apple": [],
        "custom_proxy_remain": [] # 兜底：既不属于国内，也不属于AI/流媒体/游戏的其余国外未知服务
    }

    print("[*] 正在对全库规则启动流式自动化分类清洗 (这可能需要 1~2 分钟)...")
    for name in all_available_rules:
        name_lower = name.lower()
        payload_data = download_and_extract(name)
        if not payload_data:
            continue
            
        # 智能化分流归类逻辑
        is_classified = False
        for cat_key, keywords in CATEGORY_MAPPING.items():
            if any(kw in name_lower for kw in keywords):
                pools[f"custom_{cat_key.lower()}"].extend(payload_data)
                is_classified = True
                break
        
        # 如果上游的名字不包含任何关键词，且不属于 China/Apple/Reject，则统统丢进“国外常规代理”大包
        if not is_classified:
            pools["custom_proxy_remain"].extend(payload_data)

    # 追加整合第三方源 (补充 Loyalsoldier 和 17mon 的真传，强化国内 IPv6 路由表的抗打能力)
    print("[*] 正在并入 Loyalsoldier 与 17mon 核心基线数据...")
    try:
        ls_direct = requests.get("https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt").text.splitlines()
        pools["custom_china"].extend([l.strip() for l in ls_direct if l.strip() and not l.startswith("#")])
        
        raw_ips = requests.get("https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt").text.splitlines()
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                pools["custom_china"].append(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 附加源整合有部分跳过: {e}")

    # =================================================================
    # 🖨️ 规范化写出为标准的 behavior: classical 的大聚合 YAML 文件
    # =================================================================
    os.makedirs("ruleset", exist_ok=True)
    for filename, raw_items in pools.items():
        out_path = os.path.join("ruleset", f"{filename}.yaml")
        
        # 高级清洗：去重、去空行、确保格式统一
        cleaned_items = []
        for item in raw_items:
            item = item.strip("'\" ")
            if not item or item.startswith("#") or item.startswith("payload:"):
                continue
            if item.startswith("- "):
                item = item[2:]
            cleaned_items.append(item)
            
        unique_items = sorted(list(set(cleaned_items)))
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 全自动全矩阵无缝大聚合规则包\n")
            f.write(f"# 总计条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(f"[+] 成功编译大包: {out_path} (条目数: {len(unique_items)})")

if __name__ == "__main__":
    main()
