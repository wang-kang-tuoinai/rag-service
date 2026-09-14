import os
import re
import ssl
import sys
from pathlib import Path
from urllib.parse import urljoin
import urllib3
from urllib3.util import Retry
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import html2text

# 确保 Windows 终端打印中文不乱码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 针对 redis.com.cn 兼容 Python 3.13 下的 SSL 握手密码套件
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = urllib3.util.ssl_.create_urllib3_context(ciphers="DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = TLSAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    })
    return session

def extract_management_links(session: requests.Session, index_url: str = "https://redis.com.cn/management.html") -> list[dict]:
    """提取目录页中所有的管理运维指南超链接"""
    resp = session.get(index_url, timeout=10)
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)

        if "/management/" in href and title:
            full_url = urljoin(index_url, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            desc = ""
            parent = a.find_parent(["li", "div", "p"])
            if parent:
                sibling_p = parent.find_next_sibling("p")
                if sibling_p:
                    desc = sibling_p.get_text(strip=True)

            articles.append({
                "title": title,
                "url": full_url,
                "description": desc,
                "slug": href.split("/")[-1].replace(".html", "")
            })

    return articles

def clean_html_article(article_soup: BeautifulSoup):
    """清洗正文 DOM：移除噪音标签、锚点链接"""
    # 1. 移除目录锚点标记（例如 <a class="anchor-link">*</a>）
    for anchor in article_soup.find_all("a", class_="anchor-link"):
        anchor.decompose()

    # 2. 移除脚本、样式、导航、广告等无关内容
    for noise in article_soup(["script", "style", "nav", "footer", "iframe"]):
        noise.decompose()

def convert_to_markdown(article_soup: BeautifulSoup) -> str:
    """将清洗后的文章 HTML 节点转换为规范 Markdown（去除超链接，仅保留文字）"""
    h = html2text.HTML2Text()
    h.ignore_links = True      # 去除超链接 URL，仅保留链接文本
    h.ignore_images = True     # RAG 检索不需要嵌入图片链接
    h.body_width = 0           # 保持段落不折行
    h.ignore_emphasis = False  # 保留粗体代码等格式
    h.protect_content = True

    raw_md = h.handle(str(article_soup))

    # 清理多余空行并统一换行符为 \n
    cleaned_md = re.sub(r"\n{3,}", "\n\n", raw_md).strip()
    cleaned_md = cleaned_md.replace("\r\n", "\n")
    return cleaned_md

def download_article_as_markdown(session: requests.Session, article_url: str) -> tuple[str, str]:
    """抓取单篇文章并转换为 Markdown，返回 (title, markdown_content)"""
    resp = session.get(article_url, timeout=10)
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    article_node = soup.find("article") or soup.find("main") or soup.body

    # 获取文章标题
    h1 = article_node.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # 清洗正文
    clean_html_article(article_node)

    # 转换为 Markdown
    md_content = convert_to_markdown(article_node)
    return title, md_content

def crawl_all_articles(output_dir: Path = Path("doc/technology/redis")):
    """批量下载所有文章并在头部添加指定元数据后保存为 Markdown 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    session = create_session()

    index_url = "https://redis.com.cn/management.html"
    print(f"1. 正在获取文章目录: {index_url}")
    articles = extract_management_links(session, index_url)
    print(f"   共获取到 {len(articles)} 篇文章链接\n")

    print(f"2. 开始逐篇下载并转换为 Markdown（保存目录: {output_dir.resolve()}）:")
    print("=" * 70)

    for idx, item in enumerate(articles, 1):
        url = item["url"]
        slug = item["slug"]
        print(f"[{idx:02d}/{len(articles):02d}] 正在抓取: {item['title']} ...", end=" ", flush=True)

        try:
            title, md_content = download_article_as_markdown(session, url)

            # 按要求构造头部元数据，换一行后再写正文
            frontmatter = (
                "---\n"
                "doc_type: technology\n"
                "component: redis\n"
                f"source_url: {url}\n"
                "---\n\n"
            )
            full_content = frontmatter + md_content

            # 保存为本地 .md 文件到 doc/technology/redis/ 目录
            save_file = output_dir / f"{slug}.md"
            save_file.write_text(full_content, encoding="utf-8")
            print(f"✓ 已保存 ({len(full_content)} 字符) -> {save_file.name}")
        except Exception as e:
            print(f"✗ 失败: {e}")

    print("=" * 70)
    print(f"全部抓取完成！所有 Markdown 文件已保存至: {output_dir.resolve()}\n")

if __name__ == "__main__":
    # 下载目录设置为 doc/technology/redis
    crawl_all_articles(output_dir=Path("doc/technology/redis"))
