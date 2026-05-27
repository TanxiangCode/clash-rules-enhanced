import os
import re
import requests

# 彻底摆脱 PyYAML 依赖，采用全流式字符串处理，速度快上万倍
# 引入工业级公共后缀(PSL)解析库，防止对 SaaS 平台（如 .github.io）的雪崩误杀
import tldextract

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
    "Apple": "AppleDirect",
}

AI_COMPONENTS = ["OpenAI", "Claude", "Gemini", "Copilot", "Anthropic", "BardAI"]

# 全局共享的 TCP 连接池，复用 TLS 握手，极大提高请求速度，物理抗 GitHub 限流
http_session = requests.Session()
http_session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) clash-rules-enhanced"
    }
)

# 全局初始化 TLD 提取器（内存常驻，避免在循环中重复加载）
domain_extractor = tldextract.TLDExtract()


def parse_markdown_tables_robust():
    """逐行状态机扫描不黑表官方 README 账本"""
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
                words = re.findall(r"[A-Za-z]+", line)
                if words:
                    header_word = words[0]
                    current_package = TABLE_HEADER_MAP.get(header_word, None)
                    is_global_table = header_word == "Global"
                continue

            if current_package or is_global_table:
                folders = re.findall(
                    r"https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon/([^)\s/]+)",
                    line,
                )
                for folder in folders:
                    folder = folder.strip()
                    if not folder:
                        continue
                    if is_global_table:
                        if folder in AI_COMPONENTS:
                            dynamic_registry[folder] = "NexusAI"
                        elif folder in [
                            "YouTube",
                            "YouTubeMusic",
                            "Netflix",
                            "TikTok",
                            "Disney",
                            "Spotify",
                        ]:
                            dynamic_registry[folder] = "GlobalMedia"
                        elif folder in [
                            "GitHub",
                            "OneDrive",
                            "Microsoft",
                            "Proxy",
                        ]:
                            dynamic_registry[folder] = "OverseaProxy"
                    elif current_package:
                        dynamic_registry[folder] = current_package
    except Exception as e:
        print(f"[-] 动态扫描中断: {e}，触发保底机制。", flush=True)
        return {
            "OpenAI": "NexusAI",
            "China": "MatrixChina",
            "JianGuoYun": "MatrixChina",
        }

    print(f"[+] 成功解析出 {len(dynamic_registry)} 个待下载组件！", flush=True)
    return dynamic_registry


def download_and_extract_any(folder_name):
    """高弹性多轨文件流扫描，实时冲刷日志显示"""
    rules = []
    possible_files = [
        f"{folder_name}.yaml",
        f"{folder_name}_Domain.txt",
        f"{folder_name}.list",
    ]

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

            # 纯文本流式切片解析，秒杀 YAML 语法树解析地狱
            for line in content.splitlines():
                line = line.strip()
                if (
                    not line
                    or line.startswith("#")
                    or line.startswith("//")
                    or line.startswith("payload:")
                ):
                    continue
                if line.startswith("- "):
                    line = line[2:]

                line = line.strip("'\" ").lstrip("+.")
                if line:
                    rules.append(line)
        except Exception:
            pass

    if success:
        print(
            f"     [+] {folder_name} 拉取成功 ({len(rules)} 条)", flush=True
        )
    else:
        print(f"     [-] {folder_name} 无数据或超时跳过", flush=True)

    return rules


def extract_pure_domain(rule_string):
    """从 Clash 语法系字符串（如 DOMAIN-SUFFIX,google.com）中剥离纯域名"""
    rule_string = str(rule_string).strip()
    if "," in rule_string:
        parts = rule_string.split(",")
        if len(parts) >= 2:
            return parts[1].strip().lower()
    return rule_string.lower()


def get_base_domain_safe(domain):
    """
    🛡️【安全级根主权提取算法】
    依靠 Mozilla Public Suffix List 确保绝对的边界安全，修复 DeprecationWarning
    """
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain) or ":" in domain:
        return domain

    ext = domain_extractor(domain)

    # 优先采用最新的无争议属性名，向下兼容老版本
    target_domain = getattr(
        ext, "top_domain_under_public_suffix", None
    ) or getattr(ext, "registered_domain", None)

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
            # 严格规范前缀，防止 IP 格式发生逻辑错位
            if (
                not item.startswith("DOMAIN")
                and not item.startswith("IP-CIDR")
                and not item.startswith("GEOIP")
            ):
                if ":" in item:
                    item = f"IP-CIDR6,{item}"
                elif re.match(r"^\d{1,3}(\.\d{1,3}){3}(/\d+)?$", item):
                    item = f"IP-CIDR,{item}"
                else:
                    item = f"DOMAIN-SUFFIX,{item}"
            raw_pools[target_package].add(item)

    print("\n[*] 正在并入 Loyalsoldier 与 17mon 基线数据...", flush=True)
    china_set = raw_pools["MatrixChina"]
    try:
        ls_direct = (
            http_session.get(
                "https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/direct.txt",
                timeout=10,
            )
            .text.splitlines()
        )
        for l in ls_direct:
            l = l.strip()
            if l and not l.startswith("#"):
                china_set.add(
                    f"DOMAIN-SUFFIX,{l.lstrip('+.')}"
                    if not l.startswith("DOMAIN")
                    else l
                )

        raw_ips = (
            http_session.get(
                "https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt",
                timeout=10,
            )
            .text.splitlines()
        )
        for ip in raw_ips:
            ip = ip.strip()
            if ip and not ip.startswith("#"):
                china_set.add(f"IP-CIDR6,{ip}" if ":" in ip else f"IP-CIDR,{ip}")
    except Exception as e:
        print(f"[-] 基线并入跳过: {e}", flush=True)

    # =================================================================
    # 2. 🛡️【核心重构：双轨制哈希去重引擎】 O(1) 绝杀
    # =================================================================
    print("\n[*] =========================================", flush=True)
    print("[*] 启动双轨制哈希主权索引，开始智能清洗...", flush=True)
    print("[*] =========================================", flush=True)

    china_root_registry = set()  # 存放根主权域名（用于大锤清洗海外包）
    china_exact_registry = set()  # 存放精确规则域名（用于手术刀清洗广告包）

    for rule in china_set:
        if "DOMAIN" in rule:
            pure_dom = extract_pure_domain(rule)
            base_dom = get_base_domain_safe(pure_dom)
            china_root_registry.add(base_dom)
            china_exact_registry.add(pure_dom)

    for pkg_name in [
        "PurifyReject",
        "NexusAI",
        "GlobalMedia",
        "ArcadeGame",
        "OverseaProxy",
    ]:
        purified_set = set()
        for rule in raw_pools[pkg_name]:
            if "DOMAIN" in rule:
                pure_dom = extract_pure_domain(rule)

                # 🌟 策略一：针对广告拦截包进行“手术刀”精确防误杀豁免
                if pkg_name == "PurifyReject":
                    if pure_dom in china_exact_registry:
                        continue  # 只有主业务域名字面量100%重叠时，才判定为广告误杀并踢出

                # 🌟 策略二：针对海外代理包进行“大锤”根域名连根拔起
                else:
                    base_dom = get_base_domain_safe(pure_dom)
                    if base_dom in china_root_registry:
                        continue  # 只要主根域名属于国内直连，旗下所有子域名禁止流向海外

            purified_set.add(rule)
        raw_pools[pkg_name] = purified_set

    # 3. 序列化文件高质量本地写出
    os.makedirs("ruleset", exist_ok=True)
    print("\n[*] =========================================", flush=True)
    for filename, r_set in raw_pools.items():
        file_path = os.path.join("ruleset", f"{filename}.yaml")
        unique_items = sorted(list(r_set))

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# ===================================================\n")
            f.write(f"# 🛡️ clash-rules-enhanced 工业级双轨安全极速版\n")
            f.write(f"# 📊 融合纯净总条目: {len(unique_items)} 条\n")
            f.write("# ===================================================\n")
            f.write("payload:\n")
            for rule in unique_items:
                f.write(f"  - {rule}\n")
        print(
            f"[+] 成功编译大包: {file_path:<30} (条目数: {len(unique_items)})",
            flush=True,
        )


if __name__ == "__main__":
    main()
