"""Phase 0.80: RAG 索引构建。将拆书产出向量化，供写章时跨书检索。"""

import os
from pathlib import Path
from rag_retriever import build_index


def phase_rag_index(config):
    """构建 RAG 索引。扫描所有拆书产出 → TF-IDF 向量化 → 保存到 _cache/rag_store/。"""
    base_dir = config.get("base_dir", os.getcwd())
    print(f"\n{'=' * 50}")
    print("Phase 0.80: RAG 索引构建")
    print("=" * 50)

    info = build_index(base_dir)
    if not info:
        print("[RAG] 无拆书产出可索引，跳过")
        return

    print(f"[OK] RAG 索引: {info['num_chunks']} 片段, {info['vector_dim']} 维")
    print(f"     来源: {', '.join(info['sources'])}")
