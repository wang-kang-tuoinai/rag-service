import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TARGET_DIR = BASE_DIR / "doc" / "technology" / "mysql"

FILES_CONFIG = [
    {
        "file": BASE_DIR / "mysql_进阶.md",
        "prefix": "advanced",
        "source_url": "https://github.com/AlibabaP8Developer/knowledge/blob/master/docs/database/MySQL%E8%BF%9B%E9%98%B6%E7%AF%87/MySQL%E8%BF%9B%E9%98%B6%E7%AF%87.md",
    },
    {
        "file": BASE_DIR / "mysql_ops.md",
        "prefix": "ops",
        "source_url": "https://github.com/AlibabaP8Developer/knowledge/blob/master/docs/database/MySQL%E8%BF%90%E7%BB%B4%E7%AF%87/MySQL%E8%BF%90%E7%BB%B4%E7%AF%87.md",
    },
]


def clean_markdown_content(lines: list[str]) -> list[str]:
    """清理图片和超链接，跳过代码块内部内容。"""
    cleaned = []
    fence_char = ""
    fence_len = 0

    for line in lines:
        # 检测代码块围栏
        fence_match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence_char:
            if (
                fence_match
                and fence_match.group(1)[0] == fence_char
                and len(fence_match.group(1)) >= fence_len
            ):
                fence_char = ""
            cleaned.append(line)
            continue
        elif fence_match:
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            cleaned.append(line)
            continue

        # 1. 移除图片链接 ![alt](url)
        processed = re.sub(r"!\[.*?\]\(.*?\)", "", line)
        # 2. 提取超链接文字，删除链接 [text](url) -> text
        processed = re.sub(r"(?<!!)\[(.*?)\]\(.*?\)", r"\1", processed)

        cleaned.append(processed)

    return cleaned


def split_by_h1(text: str) -> list[tuple[str, str]]:
    """按一级标题 (# 标题) 切分文档，返回 [(title, content), ...]"""
    lines = text.splitlines()
    h1_indices = []
    fence_char = ""
    fence_len = 0

    for idx, line in enumerate(lines):
        # 检查代码围栏以避免代码注释中的 # 被误判为一级标题
        fence_match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence_char:
            if (
                fence_match
                and fence_match.group(1)[0] == fence_char
                and len(fence_match.group(1)) >= fence_len
            ):
                fence_char = ""
            continue
        elif fence_match:
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            continue

        # 匹配一级标题: 行首 0~3 空格，紧接一个 # 和空白字符
        h1_match = re.match(r"^ {0,3}#\s+(.+?)\s*#*$", line)
        if h1_match:
            h1_indices.append((idx, h1_match.group(1).strip()))

    sections = []
    for pos, (start_line, title) in enumerate(h1_indices):
        end_line = h1_indices[pos + 1][0] if pos + 1 < len(h1_indices) else len(lines)
        section_lines = lines[start_line:end_line]
        cleaned_lines = clean_markdown_content(section_lines)
        
        # 规整连续空行
        content = "\n".join(cleaned_lines).strip()
        content = re.sub(r"\n{3,}", "\n\n", content)
        sections.append((title, content))

    return sections


def sanitize_filename(name: str) -> str:
    """去除文件名中的非法字符，斜杠转短横线"""
    name = re.sub(r"[/\\:*?\"<>|]", "-", name)
    name = re.sub(r"-+", "-", name).strip("- ")
    return name


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {TARGET_DIR}")

    global_index = 1
    total_written = 0

    for cfg in FILES_CONFIG:
        src_file = cfg["file"]
        if not src_file.exists():
            print(f"警告: 源文件不存在: {src_file}")
            continue

        text = src_file.read_text(encoding="utf-8-sig")
        sections = split_by_h1(text)
        print(f"\n正在处理 [{src_file.name}]，共切分出 {len(sections)} 个一级章节：")

        for title, body in sections:
            clean_title = sanitize_filename(title)
            filename = f"{global_index:02d}-{cfg['prefix']}-{clean_title}.md"
            target_path = TARGET_DIR / filename

            # 按照规范拼接 YAML Front Matter 与正文（空一行）
            front_matter = (
                f"---\n"
                f"doc_type: technology\n"
                f"component: mysql\n"
                f"source_url: {cfg['source_url']}\n"
                f"---\n\n"
            )

            file_content = front_matter + body + "\n"
            target_path.write_text(file_content, encoding="utf-8")
            print(f"  -> 生成文件: {filename} (标题: '{title}', 大小: {len(file_content)} 字符)")
            global_index += 1
            total_written += 1

    print(f"\n全部完成！共成功生成 {total_written} 个切分后的技术文档到: {TARGET_DIR}")


if __name__ == "__main__":
    main()
