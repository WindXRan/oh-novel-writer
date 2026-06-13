"""
RAG 检索器：TF-IDF 向量化 + 跨书知识检索。

用法：
  python rag_retriever.py build [--base-dir .]    # 构建索引
  或 import 后调用 retrieve()
"""

import re
import json
import pickle
import sys
import os
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RAG_STORE_DIR = "_cache/rag_store"

# 不索引的文件（摘要类，不是分析正文）
SKIP_FILES = {"_opening_summary.md"}


def find_source_analyses(base_dir):
    """查找 projects/ 下所有拆书产出，返回列表。"""
    projects_dir = Path(base_dir) / "projects"
    if not projects_dir.exists():
        return []
    results = []
    for author_dir in sorted(projects_dir.iterdir()):
        if not author_dir.is_dir():
            continue
        for source_dir in sorted(author_dir.iterdir()):
            analysis_dir = source_dir / "_cache" / "source_analysis"
            if not analysis_dir.exists():
                continue
            # 尝试从 _version.json 或 evaluation.md 读取 genre
            genre = "未知"
            version_file = analysis_dir / "_version.json"
            if version_file.exists():
                try:
                    meta = json.loads(version_file.read_text(encoding="utf-8"))
                    genre = meta.get("genre", genre)
                except Exception:
                    pass
            if genre == "未知":
                eval_file = analysis_dir / "evaluation.md"
                if eval_file.exists():
                    eval_text = eval_file.read_text(encoding="utf-8")
                    # 匹配各种格式: **品类**：xxx 或 品类：xxx 等
                    for pat in [r'\*{0,2}品类\*{0,2}[：:]\s*(.+?)(?:\n|$)', 
                                r'\*{0,2}赛道\*{0,2}[：:]\s*(.+?)(?:\n|$)',
                                r'\*{0,2}类型\*{0,2}[：:]\s*(.+?)(?:\n|$)']:
                        m = re.search(pat, eval_text)
                        if m:
                            g = m.group(1).strip().split('、')[0]
                            if g:
                                genre = g
                                break
            results.append({
                "author": author_dir.name,
                "source_book": source_dir.name,
                "path": analysis_dir,
                "genre": genre,
            })
    return results


def chunk_markdown_file(file_path, base_metadata):
    """按 ## 二级标题分块，返回 [(text, metadata)]。"""
    text = file_path.read_text(encoding="utf-8")
    dim_name = file_path.stem

    chunks = []
    # 按 ## 标题分割（行首）
    sections = re.split(r'(?m)^(?=## )', text)
    for section in sections:
        section = section.strip()
        if not section or len(section) < 80:
            continue
        # 提取标题
        title_match = re.match(r'## (.+)', section)
        heading = title_match.group(1).strip() if title_match else "(无标题)"
        chunk_meta = dict(base_metadata)
        chunk_meta["dimension"] = dim_name
        chunk_meta["heading"] = heading
        chunk_meta["source_file"] = str(file_path)
        chunks.append((section, chunk_meta))

    return chunks


def build_index(base_dir="."):
    """扫描所有拆书产出，构建 TF-IDF 索引并持久化。"""
    base = Path(base_dir).resolve()
    analyses = find_source_analyses(base)

    if not analyses:
        print("[RAG] 未找到拆书产出，跳过索引")
        return

    all_texts = []
    all_metadata = []

    for item in analyses:
        analysis_dir = item["path"]
        md_files = sorted(analysis_dir.glob("*.md"))
        for md_file in md_files:
            if md_file.name in SKIP_FILES:
                continue
            meta_base = {
                "author": item["author"],
                "source_book": item["source_book"],
                "genre": item["genre"],
                "source_file": str(md_file),
            }
            chunks = chunk_markdown_file(md_file, meta_base)
            for text, meta in chunks:
                all_texts.append(text)
                all_metadata.append(meta)

    if not all_texts:
        print("[RAG] 无可索引内容")
        return

    vectorizer = TfidfVectorizer(
        max_features=10000,
        max_df=0.8,
        min_df=1,
        analyzer='char',
        ngram_range=(1, 3),
    )
    vectors = vectorizer.fit_transform(all_texts)
    vector_dim = vectors.shape[1]

    store_dir = base / RAG_STORE_DIR
    store_dir.mkdir(parents=True, exist_ok=True)

    with open(store_dir / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    np.save(store_dir / "vectors.npy", vectors.toarray())
    with open(store_dir / "chunks.pkl", "wb") as f:
        pickle.dump(all_texts, f)
    with open(store_dir / "metadata.pkl", "wb") as f:
        pickle.dump(all_metadata, f)

    sources = list(set(m["source_book"] for m in all_metadata))
    genres = list(set(m["genre"] for m in all_metadata))
    info = {
        "num_chunks": len(all_texts),
        "vector_dim": vector_dim,
        "sources": sources,
        "genres": genres,
    }
    with open(store_dir / "index_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"[RAG] 索引完成: {len(all_texts)} 个片段, {vector_dim} 维")
    print(f"      来源: {sources}")
    print(f"      品类: {genres}")

    return info


def retrieve(query, genre=None, top_k=3, base_dir="."):
    """检索最相关片段。

    Args:
        query: 查询文本（写章时传入 plot_guide 内容）
        genre: 按品类筛选（None=不限）
        top_k: 返回条数
        base_dir: 项目根目录

    Returns:
        list of dict: [{text, metadata, score}, ...]
    """
    base = Path(base_dir).resolve()
    store_dir = base / RAG_STORE_DIR
    if not store_dir.exists():
        return []

    with open(store_dir / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    vectors = np.load(store_dir / "vectors.npy")
    with open(store_dir / "chunks.pkl", "rb") as f:
        all_texts = pickle.load(f)
    with open(store_dir / "metadata.pkl", "rb") as f:
        all_metadata = pickle.load(f)

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, vectors)[0]

    # genre 过滤
    if genre:
        mask = np.array([m["genre"] == genre for m in all_metadata])
        scores[~mask] = -1

    top_k = min(top_k, len(scores))
    top_indices = np.argsort(scores)[-top_k:][::-1]

    results = []
    for idx in top_indices:
        if scores[idx] <= 0:
            continue
        results.append({
            "text": all_texts[idx],
            "metadata": all_metadata[idx],
            "score": float(scores[idx]),
        })
    return results


def format_retrieval_results(results):
    """将检索结果格式化为可注入的 markdown。"""
    if not results:
        return ""
    lines = ["\n【跨书参考（同类品类经验）】"]
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        header = f"{meta['source_book']} - {meta.get('dimension', '?')} - {meta.get('heading', '?')}"
        lines.append(f"")
        lines.append(f"参考 {i}：{header}")
        lines.append(r["text"][:800])  # 截断防止超长
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        base = sys.argv[2] if len(sys.argv) > 2 else "."
        build_index(base)
    else:
        print("用法: python rag_retriever.py build [--base-dir .]")
