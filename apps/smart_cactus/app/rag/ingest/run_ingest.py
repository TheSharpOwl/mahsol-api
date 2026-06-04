"""
Standalone PDF ingestion script — run once to populate the Qdrant collection.

Usage:
    python -m app.rag.ingest.run_ingest
    python -m app.rag.ingest.run_ingest --pdf data/tomato_knowledge.pdf
    python -m app.rag.ingest.run_ingest --pdf data/tomato_knowledge.pdf --batch-size 64

What it does:
    1. Parse PDF → extract text + table chunks with metadata
    2. Batch-embed all chunks via BAAI/bge-m3
    3. Upsert all points into the Qdrant collection
    4. Print a summary

Run this BEFORE starting the API server (or whenever you update the PDF).
It is safe to re-run — Qdrant upsert uses UUIDs so duplicates create new points.
If you want a clean re-index, delete the collection first via the Qdrant dashboard
at http://localhost:6333/dashboard.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Make sure the project root is on the path when run as a module
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from app.core.config import settings
from app.core.logging import setup_logging
from app.rag.embeddings.embedding_model import BGEEmbedder
from app.rag.ingest.pdf_ingest import PDFIngestor
from app.rag.vectordb.qdrant_client import QdrantVectorDB

logger = logging.getLogger(__name__)


async def run_ingestion(pdf_path: str, batch_size: int = 32) -> None:
    setup_logging()

    logger.info("=" * 60)
    logger.info("Mahsoul RAG — PDF Ingestion Pipeline")
    logger.info("=" * 60)
    logger.info("PDF:        %s", pdf_path)
    logger.info("Collection: %s", settings.QDRANT_COLLECTION)
    logger.info("Qdrant:     %s", settings.QDRANT_URL)
    logger.info("Model:      %s", settings.EMBEDDING_MODEL)
    logger.info("=" * 60)

    # Step 1 — Parse PDF
    t0 = time.perf_counter()
    ingestor = PDFIngestor()
    chunks = ingestor.load_and_chunk(pdf_path)
    t_parse = time.perf_counter() - t0
    logger.info("Step 1 complete: %d chunks extracted in %.1f s", len(chunks), t_parse)

    if not chunks:
        logger.error("No chunks extracted — check if the PDF is readable.")
        sys.exit(1)

    # Step 2 — Load embedding model
    t1 = time.perf_counter()
    embedder = BGEEmbedder.get_instance()
    t_load = time.perf_counter() - t1
    logger.info("Step 2 complete: BGE-M3 loaded in %.1f s", t_load)

    # Step 3 — Embed in batches
    t2 = time.perf_counter()
    all_embeddings = []
    texts = [c["content"] for c in chunks]

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_vectors = await embedder.embed_batch(batch)
        all_embeddings.extend(batch_vectors)
        logger.info(
            "  Embedded batch %d/%d (%d chunks)",
            i // batch_size + 1,
            (len(texts) + batch_size - 1) // batch_size,
            len(batch),
        )

    t_embed = time.perf_counter() - t2
    logger.info(
        "Step 3 complete: %d embeddings in %.1f s (%.0f chunks/s)",
        len(all_embeddings),
        t_embed,
        len(all_embeddings) / t_embed if t_embed > 0 else 0,
    )

    # Step 4 — Upsert to Qdrant
    t3 = time.perf_counter()
    vector_db = QdrantVectorDB.get_instance()
    upserted = await vector_db.upsert(chunks, all_embeddings)
    t_upsert = time.perf_counter() - t3
    logger.info("Step 4 complete: %d points upserted in %.1f s", upserted, t_upsert)

    # Summary
    total = time.perf_counter() - t0
    info = await vector_db.collection_info()
    logger.info("=" * 60)
    logger.info("Ingestion complete in %.1f s total", total)
    logger.info("Collection '%s': %s vectors", info["name"], info["vectors_count"])
    logger.info("Qdrant dashboard: http://localhost:6333/dashboard")
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a PDF into the Qdrant knowledge base")
    parser.add_argument(
        "--pdf",
        default=settings.PDF_PATH,
        help=f"Path to PDF file (default: {settings.PDF_PATH})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (default: 32)",
    )
    args = parser.parse_args()

    asyncio.run(run_ingestion(pdf_path=args.pdf, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
