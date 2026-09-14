import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
import html2text

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TARGET_DIR = Path(r"d:\ops-agent\rag-service\doc\technology\rabbitmq")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# 侧边栏按层级顺序组织的 59 个目标文档页面
DOCS = [
    ("如何管理 RabbitMQ", "https://rabbitmq.cn/docs/manage-rabbitmq"),
    ("CLI", "https://rabbitmq.cn/docs/cli"),
    ("rabbitmqadmin v2", "https://rabbitmq.cn/docs/management-cli"),
    ("配置", "https://rabbitmq.cn/docs/configure"),
    ("文件和目录位置", "https://rabbitmq.cn/docs/relocate"),
    ("日志记录", "https://rabbitmq.cn/docs/logging"),
    ("虚拟主机", "https://rabbitmq.cn/docs/vhosts"),
    ("认证与授权", "https://rabbitmq.cn/docs/access-control"),
    ("凭证和密码", "https://rabbitmq.cn/docs/passwords"),
    ("OAuth 2", "https://rabbitmq.cn/docs/oauth2"),
    ("OAuth 2 示例", "https://rabbitmq.cn/docs/oauth2-examples"),
    ("Auth0", "https://rabbitmq.cn/docs/oauth2-examples-auth0"),
    ("Microsoft Entra ID", "https://rabbitmq.cn/docs/oauth2-examples-entra-id"),
    ("Google", "https://rabbitmq.cn/docs/oauth2-examples-google"),
    ("Keycloak", "https://rabbitmq.cn/docs/oauth2-examples-keycloak"),
    ("Okta", "https://rabbitmq.cn/docs/oauth2-examples-okta"),
    ("多个 OAuth 2.0 服务器", "https://rabbitmq.cn/docs/oauth2-examples-multiresource"),
    ("带 Keycloak 的转发代理", "https://rabbitmq.cn/docs/oauth2-examples-forward-proxy"),
    ("带 Keycloak 的 OAuth2 代理", "https://rabbitmq.cn/docs/oauth2-examples-proxy"),
    ("身份提供商发起的登录", "https://rabbitmq.cn/docs/oauth2-examples-idp-initiated"),
    ("OAuth 2 故障排除", "https://rabbitmq.cn/docs/troubleshooting-oauth2"),
    ("LDAP", "https://rabbitmq.cn/docs/ldap"),
    ("缓存", "https://rabbitmq.cn/docs/auth-cache-backend"),
    ("认证失败通知", "https://rabbitmq.cn/docs/auth-notification"),
    ("每个用户的资源限制", "https://rabbitmq.cn/docs/user-limits"),
    ("AMQP 0-9-1 认证机制", "https://rabbitmq.cn/docs/authentication"),
    ("策略", "https://rabbitmq.cn/docs/policies"),
    ("运行时参数", "https://rabbitmq.cn/docs/parameters"),
    ("元数据存储", "https://rabbitmq.cn/docs/metadata-store"),
    ("如何启用 Khepri", "https://rabbitmq.cn/docs/metadata-store/how-to-enable-khepri"),
    ("集群与 Khepri", "https://rabbitmq.cn/docs/metadata-store/clustering"),
    ("Khepri 的日常操作", "https://rabbitmq.cn/docs/metadata-store/everyday-operations"),
    ("Khepri 的故障恢复", "https://rabbitmq.cn/docs/metadata-store/failure-recovery"),
    ("Khepri 的已知问题", "https://rabbitmq.cn/docs/metadata-store/known-issues"),
    ("Khepri FAQ", "https://rabbitmq.cn/docs/metadata-store/khepri-faq"),
    ("架构定义", "https://rabbitmq.cn/docs/definitions"),
    ("网络", "https://rabbitmq.cn/docs/networking"),
    ("TLS 支持", "https://rabbitmq.cn/docs/ssl"),
    ("客户端心跳", "https://rabbitmq.cn/docs/heartbeats"),
    ("故障排除连接", "https://rabbitmq.cn/docs/troubleshooting-networking"),
    ("故障排除 TLS", "https://rabbitmq.cn/docs/troubleshooting-ssl"),
    ("节点间心跳", "https://rabbitmq.cn/docs/nettick"),
    ("集群", "https://rabbitmq.cn/docs/clustering"),
    ("集群形成", "https://rabbitmq.cn/docs/cluster-formation"),
    ("网络分区", "https://rabbitmq.cn/docs/partitions"),
    ("使用 TLS 进行节点间通信", "https://rabbitmq.cn/docs/clustering-ssl"),
    ("Amazon EC2 上的 RabbitMQ", "https://rabbitmq.cn/docs/ec2"),
    ("资源管理", "https://rabbitmq.cn/docs/limits"),
    ("分析内存使用情况", "https://rabbitmq.cn/docs/memory-use"),
    ("内存和磁盘告警", "https://rabbitmq.cn/docs/alarms"),
    ("内存告警", "https://rabbitmq.cn/docs/memory"),
    ("磁盘告警", "https://rabbitmq.cn/docs/disk-alarms"),
    ("流控制", "https://rabbitmq.cn/docs/flow-control"),
    ("持久化配置", "https://rabbitmq.cn/docs/persistence-conf"),
    ("备份与恢复", "https://rabbitmq.cn/docs/backup"),
    ("调优", "https://rabbitmq.cn/docs/runtime"),
    ("部署指南", "https://rabbitmq.cn/docs/production-checklist"),
    ("Kubernetes 上的 RabbitMQ", "https://rabbitmq.cn/kubernetes/operator/operator-overview"),
    ("RabbitMQ 故障排除", "https://rabbitmq.cn/docs/troubleshooting"),
]

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = urllib3.util.ssl_.create_urllib3_context(ciphers="DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

def get_session():
    session = requests.Session()
    session.mount("https://", TLSAdapter())
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session

def sanitize_filename(title: str) -> str:
    title = re.sub(r'[\\/*?:"<>|]', "-", title)
    title = title.replace(" ", "-")
    title = re.sub(r"-+", "-", title)
    return title.strip("-")

def clean_html_to_markdown(article_elem, default_title: str) -> str:
    # 移除无用元素
    for tag in article_elem.find_all(["nav", "footer", "script", "style", "noscript"]):
        tag.decompose()
    for tag in article_elem.find_all(class_=lambda c: c and any(k in c for k in ["badge", "tocMobile", "theme-doc-toc", "theme-doc-footer"])):
        tag.decompose()

    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    md = h.handle(str(article_elem))

    # 去除不可见特殊字符 \u200b
    md = md.replace("\u200b", "")

    # 去除多余的目录区块（## 目录）
    lines = md.splitlines()
    cleaned_lines = []
    skip_toc = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 目录"):
            skip_toc = True
            continue
        if skip_toc:
            if stripped.startswith("## "):
                skip_toc = False
                cleaned_lines.append(line)
            elif stripped.startswith("* ") or not stripped:
                continue
            else:
                skip_toc = False
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    content = "\n".join(cleaned_lines).strip()

    # 规范化一级标题：如果正文中没有以 # 开头，则添加一级标题
    h1_match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
    if h1_match:
        # 如果 H1 前面有残存的杂质文本，将 H1 及以后的部分提取为正文主体
        start_idx = h1_match.start()
        content = content[start_idx:].strip()
    else:
        content = f"# {default_title}\n\n{content}"

    return content

def crawl_all():
    session = get_session()
    print("=" * 80)
    print(f"开始抓取 RabbitMQ 运维文档，共 {len(DOCS)} 篇...")
    print(f"目标目录: {TARGET_DIR}")
    print("=" * 80)

    success_count = 0

    for idx, (title, url) in enumerate(DOCS, 1):
        clean_name = sanitize_filename(title)
        filename = f"{idx:02d}-{clean_name}.md"
        filepath = TARGET_DIR / filename

        print(f"[{idx:02d}/{len(DOCS)}] 正在抓取: {title} ({url}) ...", flush=True)

        retry = 3
        html_text = None
        while retry > 0:
            try:
                resp = session.get(url, timeout=12)
                resp.encoding = "utf-8"
                if resp.status_code == 200:
                    html_text = resp.text
                    break
                else:
                    print(f"    状态码异常 {resp.status_code}，重试中...", flush=True)
            except Exception as e:
                print(f"    请求出错: {e}，重试中...", flush=True)
            retry -= 1
            time.sleep(1)

        if not html_text:
            print(f"    ❌ 抓取失败，跳过: {title}")
            continue

        soup = BeautifulSoup(html_text, "html.parser")
        article = soup.find("article") or soup.find("main")
        if not article:
            print(f"    ❌ 未找到文章正文容器，跳过: {title}")
            continue

        markdown_body = clean_html_to_markdown(article, title)

        file_content = f"""---
doc_type: technology
component: rabbitmq
source_url: {url}
---

{markdown_body}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(file_content)

        print(f"    ✅ 已保存: {filename} ({len(file_content)} 字符)", flush=True)
        success_count += 1
        time.sleep(0.15)

    print("\n" + "=" * 80)
    print(f"抓取完成！成功: {success_count}/{len(DOCS)} 篇文档已写入 {TARGET_DIR}")
    print("=" * 80)

if __name__ == "__main__":
    crawl_all()
