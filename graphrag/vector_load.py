"""Chunk parsed sections, embed locally (bge-small), load into Chroma.

Chunking:
  ~500-token windows with ~50-token overlap, split at paragraph boundaries
  when possible.

Embedding:
  BAAI/bge-small-en-v1.5 — 384-dim, free, high MTEB rank, runs on CPU (uses
  Metal/MPS on Apple Silicon automatically if available).

Storage:
  Chroma persistent collection at graphrag/cache/chroma/. Each chunk gets
  metadata: ticker, cik, accession, form, filing_date, section_id,
  section_name, chunk_idx, char_offset.
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from graphrag.config import HERE, PARSED_DIR, UNIVERSE

CHROMA_PATH = HERE / "cache" / "chroma"
COLLECTION_NAME = "sec_sections"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

CIK_TO_TICKER = {u["cik"]: u["ticker"] for u in UNIVERSE}

CHUNK_SIZE_CHARS = 2000     # ~500 tokens at ~4 chars/token
CHUNK_OVERLAP = 200


def _chunk(text: str, size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP) -> list[tuple[int, str]]:
    """Return list of (char_offset, chunk_text). Splits at paragraph breaks when near size."""
    if len(text) <= size:
        return [(0, text)]
    chunks: list[tuple[int, str]] = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        # Try to end at a double-newline near the end
        if end < len(text):
            nl = text.rfind("\n\n", i + size // 2, end)
            if nl != -1:
                end = nl
        chunks.append((i, text[i:end]))
        if end >= len(text):
            break
        i = end - overlap
    return chunks


def load_all():
    print(f"loading embedding model: {EMBEDDING_MODEL}")
    # Use MPS (Metal) on Apple Silicon for ~3x speedup; falls back to CPU
    model = SentenceTransformer(EMBEDDING_MODEL)
    # Try MPS if available
    try:
        import torch
        if torch.backends.mps.is_available():
            model = model.to("mps")
            print("  using MPS (Apple Silicon GPU)")
    except Exception:
        pass

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Walk every parsed sections.jsonl
    files = sorted(PARSED_DIR.glob("*/*/sections.jsonl"))
    print(f"chunking {len(files)} filings...")

    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metas: list[dict] = []

    for p in files:
        cik = p.parent.parent.name
        acc = p.parent.name
        ticker = CIK_TO_TICKER.get(cik, cik)
        for line in p.read_text().splitlines():
            sec = json.loads(line)
            # Skip tiny sections (same threshold as extraction skipped)
            if sec.get("token_estimate", 0) < 200:
                continue
            for idx, (off, chunk) in enumerate(_chunk(sec["text"])):
                chunk_id = f"{cik}:{acc}:{sec['section_id']}:{idx}"
                all_ids.append(chunk_id)
                all_texts.append(chunk)
                all_metas.append({
                    "ticker": ticker,
                    "cik": cik,
                    "accession": acc,
                    "form": sec.get("form", ""),
                    "filing_date": sec.get("filing_date", ""),
                    "section_id": sec.get("section_id", ""),
                    "section_name": sec.get("section_name", ""),
                    "chunk_idx": idx,
                    "char_offset": off,
                })

    print(f"total chunks: {len(all_texts):,}")

    # Batch embed + insert (Chroma handles batching but we show progress)
    BATCH = 128
    for start in tqdm(range(0, len(all_texts), BATCH), desc="embedding+inserting", unit="batch"):
        end = min(start + BATCH, len(all_texts))
        batch_texts = all_texts[start:end]
        batch_embs = model.encode(batch_texts, convert_to_numpy=True,
                                  show_progress_bar=False, normalize_embeddings=True)
        collection.add(
            ids=all_ids[start:end],
            embeddings=batch_embs.tolist(),
            documents=batch_texts,
            metadatas=all_metas[start:end],
        )

    print(f"\n✓ Chroma collection '{COLLECTION_NAME}' loaded with {collection.count():,} chunks")
    return collection
