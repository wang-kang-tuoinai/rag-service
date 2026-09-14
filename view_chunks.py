import math
from pathlib import Path
import streamlit as st
import chromadb

# 设置页面基本配置
st.set_page_config(
    page_title="Chroma 知识库切片查看器",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "my_chroma_data"
DEFAULT_COLLECTION = "ops_knowledge"


@st.cache_resource
def get_chroma_client(db_path: str):
    return chromadb.PersistentClient(path=db_path)


def load_all_chunks(client, collection_name: str):
    try:
        col = client.get_collection(collection_name)
    except Exception as e:
        return None, f"获取集合失败: {e}"

    # 一次性获取所有 chunk 的 id、文本和元数据
    res = col.get(include=["documents", "metadatas"])
    chunks = []
    for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
        chunks.append({
            "id": cid,
            "text": doc,
            "metadata": meta or {},
            "doc_id": (meta or {}).get("doc_id", "未知"),
            "component": (meta or {}).get("component", "未知"),
            "doc_type": (meta or {}).get("doc_type", "未知"),
            "title": (meta or {}).get("title", ""),
            "section": (meta or {}).get("section", ""),
            "chunk_index": (meta or {}).get("chunk_index", 0),
            "source": (meta or {}).get("source", ""),
            "source_url": (meta or {}).get("source_url", ""),
        })
    # 默认按 doc_id 和 chunk_index 排序
    chunks.sort(key=lambda x: (x["doc_id"], x["chunk_index"]))
    return chunks, None


def main():
    st.title("📚 Chroma 知识库切片分页查看器")

    # 侧边栏：数据库与集合配置
    st.sidebar.header("⚙️ 数据库配置")
    db_path_input = st.sidebar.text_input("Chroma 数据路径", value=str(DEFAULT_DB_PATH))
    collection_input = st.sidebar.text_input("Collection 名称", value=DEFAULT_COLLECTION)

    if not Path(db_path_input).exists():
        st.error(f"路径不存在: {db_path_input}")
        return

    client = get_chroma_client(db_path_input)

    # 刷新按钮
    if st.sidebar.button("🔄 重新载入数据"):
        st.cache_data.clear()
        st.rerun()

    # 读取数据
    chunks, err = load_all_chunks(client, collection_input)
    if err:
        st.error(err)
        return

    if not chunks:
        st.warning("集合为空，暂无切片数据。")
        return

    # 统计信息卡片
    all_doc_ids = sorted(list({c["doc_id"] for c in chunks}))
    all_components = sorted(list({c["component"] for c in chunks}))
    all_doc_types = sorted(list({c["doc_type"] for c in chunks}))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("切片总数 (Chunks)", len(chunks))
    c2.metric("独立文档数 (Documents)", len(all_doc_ids))
    c3.metric("组件类型 (Components)", len(all_components))
    c4.metric("文档类型 (Doc Types)", len(all_doc_types))

    st.markdown("---")

    # 侧边栏：检索与过滤
    st.sidebar.header("🔍 筛选与过滤")
    search_keyword = st.sidebar.text_input("全文关键字搜索", placeholder="输入关键词搜索正文或ID...")

    selected_doc_type = st.sidebar.selectbox("文档类型 (doc_type)", ["全部"] + all_doc_types)
    selected_component = st.sidebar.selectbox("技术组件 (component)", ["全部"] + all_components)
    selected_doc_id = st.sidebar.selectbox("指定文档 (doc_id)", ["全部"] + all_doc_ids)

    # 应用筛选逻辑
    filtered = chunks
    if search_keyword.strip():
        kw = search_keyword.strip().lower()
        filtered = [c for c in filtered if kw in c["text"].lower() or kw in c["id"].lower()]

    if selected_doc_type != "全部":
        filtered = [c for c in filtered if c["doc_type"] == selected_doc_type]

    if selected_component != "全部":
        filtered = [c for c in filtered if c["component"] == selected_component]

    if selected_doc_id != "全部":
        filtered = [c for c in filtered if c["doc_id"] == selected_doc_id]

    total_filtered = len(filtered)
    st.markdown(f"**当前筛选结果：共 `{total_filtered}` / `{len(chunks)}` 个切片**")

    if total_filtered == 0:
        st.info("没有匹配到符合条件的切片，请调整筛选条件。")
        return

    # 分页控制
    col_size, col_page, col_info = st.columns([2, 3, 3])
    with col_size:
        page_size = st.selectbox("每页切片数", [5, 10, 20, 50], index=1)

    total_pages = max(1, math.ceil(total_filtered / page_size))

    # 使用 session_state 记录当前页码
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = 1
    if st.session_state["current_page"] > total_pages:
        st.session_state["current_page"] = 1

    with col_page:
        current_page = st.number_input(
            f"跳转页码 (1 - {total_pages})",
            min_value=1,
            max_value=total_pages,
            value=st.session_state["current_page"],
            step=1,
        )
        st.session_state["current_page"] = current_page

    with col_info:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_filtered)
        st.write("")
        st.caption(f"当前显示第 **{start_idx + 1}** 到 **{end_idx}** 条切片（第 **{current_page}/{total_pages}** 页）")

    # 渲染当前页的切片
    page_chunks = filtered[start_idx:end_idx]

    for idx, c in enumerate(page_chunks):
        card_title = f"#{start_idx + idx + 1} | {c['id']}"
        with st.expander(card_title, expanded=True):
            # 顶部元数据标签栏
            tags = [
                f"🏷️ **类型**: `{c['doc_type']}`",
                f"🧩 **组件**: `{c['component']}`",
                f"📄 **文档**: `{c['doc_id']}`",
                f"🔢 **切片序号**: `#{c['chunk_index']}`",
            ]
            if c["section"]:
                tags.append(f"📌 **小节**: `{c['section']}`")
            st.markdown("  ·  ".join(tags))

            if c["source"]:
                st.caption(f"📁 **源文件**: `{c['source']}`")
            if c["source_url"]:
                st.caption(f"🌐 **来源网址**: [{c['source_url']}]({c['source_url']})")

            # 切片正文展示
            st.markdown("#### 📝 切片正文内容 (Markdown 渲染)：")
            st.markdown(c["text"])

            # 完整元数据展开查看
            with st.popover("🔍 查看完整元数据 (Metadata JSON)"):
                st.json(c["metadata"])

            with st.popover("📋 查看/复制原始纯文本 (Raw Text)"):
                st.code(c["text"], language="markdown")

    # 底部快捷翻页按钮
    col_prev, col_center, col_next = st.columns([1, 4, 1])
    with col_prev:
        if current_page > 1:
            if st.button("⬅️ 上一页"):
                st.session_state["current_page"] = current_page - 1
                st.rerun()
    with col_next:
        if current_page < total_pages:
            if st.button("下一页 ➡️"):
                st.session_state["current_page"] = current_page + 1
                st.rerun()


if __name__ == "__main__":
    main()
