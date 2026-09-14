"""Markdown 标题解析和有 token 预算的切分；不依赖文档类型或存储。"""
import re


def format_chunk(title: str, section: str, body: str) -> str:
    return f"文档标题：{title}\n章节标题：{section}\n\n{body}"


def headings(lines):
    """只识别正文标题，跳过围栏与缩进代码。"""
    fence_char, fence_size = "", 0
    for index, line in enumerate(lines):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence_char:
            if (fence and fence.group(1)[0] == fence_char
                    and len(fence.group(1)) >= fence_size and not fence.group(2).strip()):
                fence_char = ""
            continue
        if fence:
            fence_char, fence_size = fence.group(1)[0], len(fence.group(1))
            continue
        match = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            yield index, len(match.group(1)), match.group(2)


def split_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """按 H2 拆分，保留 H3 及以下标题；兼容原有项目文档切分。"""
    lines = body.splitlines()
    marks = list(headings(lines))
    first_title = next((mark for mark in marks if mark[1] == 1), None)
    if first_title is None:
        raise ValueError("文档必须有一级标题和非空章节正文")
    title = first_title[2]
    sections, pending, section = [], [], "概述"
    boundaries = {i: name for i, level, name in marks if level == 2}
    for index, line in enumerate(lines):
        if index == first_title[0]:
            continue
        if index in boundaries:
            content = "\n".join(pending).strip("\n")
            if content.strip():
                sections.append((section, content))
            pending, section = [], boundaries[index]
        else:
            pending.append(line)
    content = "\n".join(pending).strip("\n")
    if content.strip():
        sections.append((section, content))
    if not sections:
        raise ValueError("文档必须有一级标题和非空章节正文")
    return title, sections


def markdown_blocks(body):
    """优先以段落、列表项、完整代码块和表格作为边界。"""
    lines = body.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        start = index
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", lines[index])
        if fence:
            index += 1
            while index < len(lines):
                closing = re.match(r"^ {0,3}(`{3,}|~{3,})\s*$", lines[index])
                index += 1
                if closing and closing.group(1)[0] == fence.group(1)[0] and len(closing.group(1)) >= len(fence.group(1)):
                    break
            yield "code", "\n".join(lines[start:index])
            continue
        if lines[index].startswith(("    ", "\t")):
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith(("    ", "\t"))):
                index += 1
            yield "code", "\n".join(lines[start:index]).rstrip()
            continue
        if (index + 1 < len(lines) and "|" in lines[index]
                and re.fullmatch(r"\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*", lines[index + 1])):
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                index += 1
            yield "table", "\n".join(lines[start:index])
            continue
        index += 1
        while index < len(lines) and lines[index].strip():
            if re.match(r"^ {0,3}(?:`{3,}|~{3,}|[-+*]\s|\d+[.)]\s)", lines[index]) or lines[index].startswith(("    ", "\t")):
                break
            index += 1
        yield "text", "\n".join(lines[start:index])


def split_long_section(title, section, body, tokenizer, max_tokens, overlap_ratio=0.12):
    """仅细分超长章节；标题优先，其次块/句子，最终按字符边界兜底。"""
    if not 0 <= overlap_ratio < 0.5:
        raise ValueError("overlap_ratio 必须在 [0, 0.5) 范围内")

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=True, truncation=False, verbose=False))

    def fits(text):
        return count(format_chunk(title, section, text)) <= max_tokens

    if not fits(""):
        raise ValueError(f"标题本身超过 token 上限: {title} / {section}")
    if fits(body):
        return [(section, body)]

    lines = body.splitlines()
    marks = [mark for mark in headings(lines) if mark[1] >= 3]
    if marks:
        level = min(mark[1] for mark in marks)
        boundaries = [mark for mark in marks if mark[1] == level]
        pieces = []
        intro = "\n".join(lines[:boundaries[0][0]]).strip("\n")
        if intro.strip():
            pieces.extend(split_long_section(title, section, intro, tokenizer, max_tokens, overlap_ratio))
        for pos, (start, _, name) in enumerate(boundaries):
            end = boundaries[pos + 1][0] if pos + 1 < len(boundaries) else len(lines)
            content = "\n".join(lines[start + 1:end]).strip("\n")
            if content.strip():
                pieces.extend(split_long_section(title, f"{section} / {name}", content, tokenizer, max_tokens, overlap_ratio))
        return pieces

    def split_text(text):
        # 先保留完整句子；无标点的长段落逐字符寻找可容纳的前缀，不 decode token 切片。
        for sentence in re.split(r"(?<=[。！？；.!?;])", text):
            remaining = sentence.strip()
            while remaining and not fits(remaining):
                lo, hi = 0, len(remaining)
                while lo + 1 < hi:
                    mid = (lo + hi) // 2
                    if fits(remaining[:mid]):
                        lo = mid
                    else:
                        hi = mid
                if lo == 0:
                    raise ValueError(f"正文无可用 token 预算: {title} / {section}")
                yield remaining[:lo]
                remaining = remaining[lo:]
            if remaining:
                yield remaining

    atoms, protected = [], set()
    for kind, block in markdown_blocks(body):
        if fits(block):
            atoms.append(block)
            if kind != "text":
                protected.add(block)
        elif kind == "code":
            raise ValueError(f"代码块超过 token 上限，请人工拆分: {title} / {section}")
        elif kind == "table":
            rows = block.splitlines()
            header = "\n".join(rows[:2])
            current = header
            for row in rows[2:]:
                if not fits(header + "\n" + row):
                    raise ValueError(f"表头或单行超过 token 上限，请人工拆分: {title} / {section}")
                if not fits(current + "\n" + row):
                    atoms.append(current)
                    protected.add(current)
                    current = header
                current += "\n" + row
            if not fits(current):
                raise ValueError(f"表头超过 token 上限: {title} / {section}")
            atoms.append(current)
            protected.add(current)
        else:
            atoms.extend(split_text(block))

    output, current = [], []
    overlap_tokens = int((max_tokens - count(format_chunk(title, section, ""))) * overlap_ratio)
    for atom in atoms:
        if current and not fits("\n\n".join(current + [atom])):
            output.append((section, "\n\n".join(current)))
            tail = []
            for previous in reversed(current):
                candidate = [previous] + tail
                if count("\n\n".join(candidate)) > overlap_tokens:
                    # 完整段落放不下时，尝试保留它末尾的完整句子；不截断代码/表格。
                    if previous not in protected:
                        suffix = ""
                        for sentence in reversed(re.split(r"(?<=[。！？；.!?;])", previous)):
                            trial = sentence + suffix
                            if count("\n\n".join([trial] + tail)) > overlap_tokens:
                                break
                            suffix = trial
                        if suffix.strip():
                            tail.insert(0, suffix)
                    break
                tail = candidate
            while tail and not fits("\n\n".join(tail + [atom])):
                tail.pop(0)
            current = tail
        current.append(atom)
    if current:
        output.append((section, "\n\n".join(current)))
    return output
