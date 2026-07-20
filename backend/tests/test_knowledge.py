"""Comprehensive tests for the RAG & Knowledge Engine — Phase IV."""
from __future__ import annotations

import asyncio
import math
import re
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine in a new event loop (no pytest-asyncio required)."""
    return asyncio.run(coro)


# ===========================================================================
# 1. Config
# ===========================================================================
class TestKnowledgeConfig(unittest.TestCase):
    def test_defaults(self):
        from services.knowledge.config import KnowledgeConfig
        c = KnowledgeConfig()
        self.assertTrue(c.enabled)
        self.assertTrue(c.rag_enabled)
        self.assertEqual(c.embedding_provider, "local")
        self.assertEqual(c.vector_backend, "mongodb")
        self.assertEqual(c.chunk_strategy, "section")

    def test_from_env(self):
        import os
        from services.knowledge.config import reload_knowledge_config
        os.environ["KNOWLEDGE_ENABLED"] = "0"
        os.environ["KNOWLEDGE_TOP_K"] = "12"
        c = reload_knowledge_config()
        self.assertFalse(c.enabled)
        self.assertEqual(c.retrieval_top_k, 12)
        # cleanup
        del os.environ["KNOWLEDGE_ENABLED"]
        del os.environ["KNOWLEDGE_TOP_K"]
        reload_knowledge_config()

    def test_from_env_rag_disabled(self):
        import os
        from services.knowledge.config import reload_knowledge_config
        os.environ["KNOWLEDGE_RAG_ENABLED"] = "0"
        c = reload_knowledge_config()
        self.assertFalse(c.rag_enabled)
        del os.environ["KNOWLEDGE_RAG_ENABLED"]
        reload_knowledge_config()


# ===========================================================================
# 2. Models
# ===========================================================================
class TestModels(unittest.TestCase):
    def test_document_metadata_to_dict(self):
        from services.knowledge.models import DocumentMetadata
        m = DocumentMetadata(title="Test", authors=["Smith, J."], doi="10.1234/x")
        d = m.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["doi"], "10.1234/x")

    def test_chunk_to_mongo_dict(self):
        from services.knowledge.models import Chunk
        c = Chunk(
            document_id="doc1", chunk_index=0, text="Hello world",
            user_id="u1", visibility="private",
        )
        d = c.to_mongo_dict()
        self.assertEqual(d["document_id"], "doc1")
        self.assertEqual(d["text"], "Hello world")
        self.assertEqual(d["visibility"], "private")

    def test_search_result_to_citation(self):
        from services.knowledge.models import SearchResult
        r = SearchResult(
            chunk_id="c1", document_id="d1", text="Some text",
            score=0.9, authors=["Jones, A.", "Smith, B."],
            title="A Study", publication_year=2022, section="Results",
        )
        cit = r.to_citation()
        self.assertIn("Jones", cit.format_short())
        self.assertIn("2022", cit.format_short())
        self.assertIn("Results", cit.format_short())

    def test_citation_format_short_single_author(self):
        from services.knowledge.models import SearchResult
        r = SearchResult(
            chunk_id="c1", document_id="d1", text="x",
            score=0.8, authors=["Doe, Jane"], publication_year=2021, section="",
        )
        short = r.to_citation().format_short()
        self.assertIn("Doe", short)
        self.assertIn("2021", short)

    def test_citation_format_short_no_author(self):
        from services.knowledge.models import SearchResult
        r = SearchResult(
            chunk_id="c1", document_id="d1", text="x",
            score=0.5, title="My Document",
        )
        short = r.to_citation().format_short()
        self.assertIn("My Document", short)

    def test_knowledge_document_to_dict(self):
        from services.knowledge.models import DocumentMetadata, KnowledgeDocument
        doc = KnowledgeDocument(
            document_id="abc", user_id="u1", filename="test.pdf",
            file_type="pdf", source_kind="upload", source_id="",
            workspace_id=None, visibility="private",
            metadata=DocumentMetadata(title="Test"), status="indexed",
        )
        d = doc.to_dict()
        self.assertEqual(d["filename"], "test.pdf")
        self.assertEqual(d["status"], "indexed")


# ===========================================================================
# 3. Telemetry
# ===========================================================================
class TestKnowledgeTelemetry(unittest.TestCase):
    def setUp(self):
        from services.knowledge.telemetry import KnowledgeTelemetry
        self.tel = KnowledgeTelemetry()

    def test_record_indexed(self):
        self.tel.record_indexed(15)
        stats = self.tel.get_stats()
        self.assertEqual(stats["documents_indexed"], 1)
        self.assertEqual(stats["chunks_indexed"], 15)

    def test_record_failed(self):
        self.tel.record_failed()
        self.assertEqual(self.tel.get_stats()["documents_failed"], 1)

    def test_record_retrieval(self):
        self.tel.record_retrieval(results=5, latency_ms=42, top_score=0.8)
        stats = self.tel.get_stats()
        self.assertEqual(stats["retrieval_requests"], 1)
        self.assertEqual(stats["avg_retrieval_latency_ms"], 42.0)

    def test_cache_hit_rate(self):
        self.tel.record_retrieval(results=3, latency_ms=10, from_cache=True)
        self.tel.record_retrieval(results=3, latency_ms=20, from_cache=False)
        stats = self.tel.get_stats()
        self.assertEqual(stats["retrieval_cache_hit_rate_pct"], 50.0)

    def test_reset(self):
        self.tel.record_indexed(5)
        self.tel.reset()
        self.assertEqual(self.tel.get_stats()["documents_indexed"], 0)

    def test_queue_size(self):
        self.tel.set_queue_size(7)
        self.assertEqual(self.tel.get_stats()["indexing_queue_size"], 7)

    def test_singleton(self):
        from services.knowledge.telemetry import get_knowledge_telemetry
        a = get_knowledge_telemetry()
        b = get_knowledge_telemetry()
        self.assertIs(a, b)


# ===========================================================================
# 4. PDF Extractor
# ===========================================================================
class TestPDFExtractor(unittest.TestCase):
    def test_extract_plain_text_fallback(self):
        from services.knowledge.ingestion.extractors.pdf_extractor import PDFExtractor
        # Create minimal fake PDF bytes containing Tj operators
        fake_pdf = b"(Hello world from PDF) Tj"
        ext = PDFExtractor()
        result = ext.extract(fake_pdf, "test.pdf")
        # Should fall back to heuristic
        self.assertTrue(len(result.text) > 0 or result.extraction_method == "heuristic")

    def test_supports_pdf(self):
        from services.knowledge.ingestion.extractors.pdf_extractor import PDFExtractor
        ext = PDFExtractor()
        self.assertTrue(ext.supports("pdf"))
        self.assertTrue(ext.supports(".pdf"))
        self.assertFalse(ext.supports("docx"))

    def test_detect_language_english(self):
        from services.knowledge.ingestion.extractors.pdf_extractor import _detect_language
        self.assertEqual(_detect_language("the and of to a in is that for the"), "en")

    def test_detect_language_unknown(self):
        from services.knowledge.ingestion.extractors.pdf_extractor import _detect_language
        self.assertEqual(_detect_language("lorem ipsum dolor sit amet consectetur"), "unknown")

    def test_extract_sections_with_heading(self):
        from services.knowledge.ingestion.extractors.pdf_extractor import _extract_sections
        text = "Introduction\nThis is the intro.\nMethods\nThis is methods."
        sections = _extract_sections(text)
        headings = [s["heading"] for s in sections]
        self.assertIn("Introduction", headings)
        self.assertIn("Methods", headings)


# ===========================================================================
# 5. DOCX Extractor
# ===========================================================================
class TestDOCXExtractor(unittest.TestCase):
    def test_supports_docx(self):
        from services.knowledge.ingestion.extractors.docx_extractor import DOCXExtractor
        ext = DOCXExtractor()
        self.assertTrue(ext.supports("docx"))
        self.assertTrue(ext.supports("doc"))

    def test_xml_fallback_invalid(self):
        from services.knowledge.ingestion.extractors.docx_extractor import DOCXExtractor
        ext = DOCXExtractor()
        result = ext._xml_fallback(b"not a zip")
        self.assertEqual(result[0], "")
        self.assertIn("failed", result[2])


# ===========================================================================
# 6. Text Extractors
# ===========================================================================
class TestTextExtractors(unittest.TestCase):
    def test_text_extractor(self):
        from services.knowledge.ingestion.extractors.text_extractor import TextExtractor
        ext = TextExtractor()
        result = ext.extract(b"Hello world\nSecond line", "test.txt")
        self.assertIn("Hello world", result.text)
        self.assertEqual(result.extraction_method, "plain")

    def test_markdown_extractor_title(self):
        from services.knowledge.ingestion.extractors.text_extractor import MarkdownExtractor
        ext = MarkdownExtractor()
        result = ext.extract(b"# My Title\n\nSome content here.", "test.md")
        self.assertEqual(result.metadata.title, "My Title")

    def test_markdown_extractor_strips_markup(self):
        from services.knowledge.ingestion.extractors.text_extractor import MarkdownExtractor
        ext = MarkdownExtractor()
        result = ext.extract(b"**bold** and *italic* text", "test.md")
        self.assertNotIn("**", result.text)
        self.assertNotIn("*", result.text)

    def test_html_extractor_strips_tags(self):
        from services.knowledge.ingestion.extractors.text_extractor import HTMLExtractor
        ext = HTMLExtractor()
        html = b"<html><body><p>Hello <b>world</b></p></body></html>"
        result = ext.extract(html, "test.html")
        self.assertIn("Hello", result.text)
        self.assertNotIn("<p>", result.text)

    def test_html_extractor_title(self):
        from services.knowledge.ingestion.extractors.text_extractor import HTMLExtractor
        ext = HTMLExtractor()
        html = b"<html><head><title>My Page</title></head><body>content</body></html>"
        result = ext.extract(html, "test.html")
        self.assertEqual(result.metadata.title, "My Page")

    def test_csv_extractor(self):
        from services.knowledge.ingestion.extractors.text_extractor import CSVExtractor
        ext = CSVExtractor()
        csv_data = b"name,age,city\nAlice,30,New York\nBob,25,London"
        result = ext.extract(csv_data, "data.csv")
        self.assertIn("name", result.text.lower())
        self.assertIn("Alice", result.text)

    def test_csv_keywords_from_header(self):
        from services.knowledge.ingestion.extractors.text_extractor import CSVExtractor
        ext = CSVExtractor()
        csv_data = b"doi,title,authors\n10.1234/x,Paper,Smith"
        result = ext.extract(csv_data, "papers.csv")
        self.assertIn("doi", result.metadata.keywords)

    def test_csv_empty(self):
        from services.knowledge.ingestion.extractors.text_extractor import CSVExtractor
        ext = CSVExtractor()
        result = ext.extract(b"", "empty.csv")
        self.assertEqual(result.text, "")


# ===========================================================================
# 7. Chunkers
# ===========================================================================
class TestChunkerBase(unittest.TestCase):
    def test_count_tokens_fallback(self):
        # tiktoken may or may not be installed; test that function returns int
        from services.knowledge.ingestion.chunkers.base import _count_tokens
        result = _count_tokens("This is a test sentence.")
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_sentence_split(self):
        from services.knowledge.ingestion.chunkers.base import ChunkerBase, _count_tokens
        from services.knowledge.models import DocumentMetadata

        class DummyChunker(ChunkerBase):
            def chunk(self, sections, metadata, document_id, **kwargs):
                return []

        chunker = DummyChunker(max_tokens=10, overlap_tokens=2, min_tokens=1)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        parts = chunker._split_long_text(text, "", None)
        self.assertIsInstance(parts, list)
        self.assertGreater(len(parts), 0)


class TestSectionChunker(unittest.TestCase):
    def _make_sections(self):
        return [
            {"heading": "Abstract", "text": "This paper presents a novel approach.", "page": 1},
            {"heading": "Introduction", "text": " ".join(["word"] * 600), "page": 2},
            {"heading": "Methods", "text": "We used method X.", "page": 3},
        ]

    def test_produces_chunks(self):
        from services.knowledge.ingestion.chunkers.section_chunker import SectionChunker
        from services.knowledge.models import DocumentMetadata
        chunker = SectionChunker(max_tokens=500, overlap_tokens=50, min_tokens=5)
        chunks = chunker.chunk(
            self._make_sections(),
            DocumentMetadata(title="Test"),
            "doc1", "user1",
        )
        self.assertGreater(len(chunks), 0)

    def test_long_section_is_split(self):
        from services.knowledge.ingestion.chunkers.section_chunker import SectionChunker
        from services.knowledge.models import DocumentMetadata
        chunker = SectionChunker(max_tokens=20, overlap_tokens=2, min_tokens=1)
        # 10 sentences × ~6 tokens each = ~60 tokens >> max_tokens=20
        sentences = " ".join([f"Sentence number {i} discusses machine learning techniques." for i in range(10)])
        sections = [{"heading": "Intro", "text": sentences, "page": 1}]
        chunks = chunker.chunk(sections, DocumentMetadata(), "doc1", "user1")
        self.assertGreater(len(chunks), 1)

    def test_chunk_metadata_inherited(self):
        from services.knowledge.ingestion.chunkers.section_chunker import SectionChunker
        from services.knowledge.models import DocumentMetadata
        meta = DocumentMetadata(title="My Paper", doi="10.1234/x", authors=["Smith"])
        chunker = SectionChunker(max_tokens=500, min_tokens=1)
        sections = [{"heading": "Methods", "text": "text here", "page": 1}]
        chunks = chunker.chunk(sections, meta, "doc1", "user1")
        self.assertEqual(chunks[0].doi, "10.1234/x")
        self.assertEqual(chunks[0].title, "My Paper")

    def test_empty_section_skipped(self):
        from services.knowledge.ingestion.chunkers.section_chunker import SectionChunker
        from services.knowledge.models import DocumentMetadata
        chunker = SectionChunker(min_tokens=1)
        sections = [{"heading": "Empty", "text": "", "page": 1}]
        chunks = chunker.chunk(sections, DocumentMetadata(), "doc1", "user1")
        self.assertEqual(len(chunks), 0)


class TestParagraphChunker(unittest.TestCase):
    def test_produces_chunks(self):
        from services.knowledge.ingestion.chunkers.paragraph_chunker import ParagraphChunker
        from services.knowledge.models import DocumentMetadata
        sections = [{"heading": "", "text": "Para one.\n\nPara two.\n\nPara three.", "page": None}]
        chunker = ParagraphChunker(max_tokens=500, min_tokens=1)
        chunks = chunker.chunk(sections, DocumentMetadata(), "doc1", "user1")
        self.assertGreater(len(chunks), 0)

    def test_overlap_preserved(self):
        from services.knowledge.ingestion.chunkers.paragraph_chunker import ParagraphChunker
        from services.knowledge.models import DocumentMetadata
        # Force split with tiny max_tokens
        paras = "\n\n".join([f"Paragraph {i} with some text content." for i in range(20)])
        sections = [{"heading": "", "text": paras, "page": None}]
        chunker = ParagraphChunker(max_tokens=30, overlap_tokens=10, min_tokens=1)
        chunks = chunker.chunk(sections, DocumentMetadata(), "doc1", "user1")
        self.assertGreater(len(chunks), 1)


# ===========================================================================
# 8. Embedding Providers
# ===========================================================================
class TestTFIDFProvider(unittest.TestCase):
    def test_embed_returns_correct_dim(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        emb = _run(p.embed("neural network deep learning"))
        self.assertEqual(len(emb), p.dimension)

    def test_embed_batch(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        texts = ["machine learning", "natural language processing", "computer vision"]
        embs = _run(p.embed_batch(texts))
        self.assertEqual(len(embs), 3)
        for e in embs:
            self.assertEqual(len(e), p.dimension)

    def test_is_normalized(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        emb = _run(p.embed("word frequency inverse document frequency"))
        norm = math.sqrt(sum(v * v for v in emb))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_similar_texts_higher_score(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        texts = [
            "machine learning neural network",
            "deep learning artificial intelligence",
            "baking bread flour yeast",
        ]
        embs = _run(p.embed_batch(texts))
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            return dot / (na * nb) if na * nb > 0 else 0.0
        sim_ai = cosine(embs[0], embs[1])
        sim_bread = cosine(embs[0], embs[2])
        self.assertGreater(sim_ai, sim_bread)

    def test_empty_text(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        emb = _run(p.embed(""))
        self.assertEqual(len(emb), p.dimension)
        self.assertEqual(sum(emb), 0.0)

    def test_always_available(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        self.assertTrue(p.is_available())

    def test_name(self):
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        p = TFIDFEmbeddingProvider()
        self.assertEqual(p.name, "tfidf")


# ===========================================================================
# 9. Embedding Cache
# ===========================================================================
class TestEmbeddingCache(unittest.TestCase):
    def test_set_get(self):
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache(ttl=60.0)
        emb = [0.1, 0.2, 0.3]
        key = c.make_key("tfidf", "hello world")
        c.set(key, emb)
        result = c.get(key)
        self.assertEqual(result, emb)

    def test_miss_returns_none(self):
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache()
        self.assertIsNone(c.get("nonexistent"))

    def test_ttl_expiry(self):
        import time
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache(ttl=0.01)  # 10ms TTL
        key = c.make_key("tfidf", "test")
        c.set(key, [1.0])
        time.sleep(0.05)
        self.assertIsNone(c.get(key))

    def test_lru_eviction(self):
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache(max_size=3, ttl=60.0)
        for i in range(4):
            key = c.make_key("tfidf", f"text {i}")
            c.set(key, [float(i)])
        self.assertEqual(c.size(), 3)

    def test_clear(self):
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache()
        c.set(c.make_key("x", "y"), [1.0])
        c.clear()
        self.assertEqual(c.size(), 0)

    def test_make_key_deterministic(self):
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache()
        k1 = c.make_key("tfidf", "same text")
        k2 = c.make_key("tfidf", "same text")
        self.assertEqual(k1, k2)

    def test_make_key_different_provider(self):
        from services.knowledge.embeddings.cache import EmbeddingCache
        c = EmbeddingCache()
        k1 = c.make_key("tfidf", "text")
        k2 = c.make_key("openai", "text")
        self.assertNotEqual(k1, k2)


# ===========================================================================
# 10. Retrieval Cache
# ===========================================================================
class TestRetrievalCache(unittest.TestCase):
    def test_set_get(self):
        from services.knowledge.retrieval.retrieval_cache import RetrievalCache
        c = RetrievalCache(ttl=60.0)
        key = c.make_key("machine learning", "user1", 5, None)
        c.set(key, ["result1", "result2"])
        self.assertEqual(c.get(key), ["result1", "result2"])

    def test_miss(self):
        from services.knowledge.retrieval.retrieval_cache import RetrievalCache
        c = RetrievalCache()
        self.assertIsNone(c.get("missing"))

    def test_ttl_expiry(self):
        import time
        from services.knowledge.retrieval.retrieval_cache import RetrievalCache
        c = RetrievalCache(ttl=0.01)
        key = c.make_key("q", "u", 5, None)
        c.set(key, ["r"])
        time.sleep(0.05)
        self.assertIsNone(c.get(key))

    def test_key_includes_workspace(self):
        from services.knowledge.retrieval.retrieval_cache import RetrievalCache
        c = RetrievalCache()
        k1 = c.make_key("q", "u", 5, "ws1")
        k2 = c.make_key("q", "u", 5, "ws2")
        self.assertNotEqual(k1, k2)


# ===========================================================================
# 11. Retrieval Filters
# ===========================================================================
class TestRetrievalFilters(unittest.TestCase):
    def test_build_private_filter(self):
        from services.knowledge.retrieval.filters import RetrievalFilter, build_mongo_filter
        f = RetrievalFilter(user_id="u1")
        mf = build_mongo_filter(f)
        self.assertIn("$or", mf)
        clauses = mf["$or"]
        has_private = any(c.get("user_id") == "u1" and c.get("visibility") == "private" for c in clauses)
        self.assertTrue(has_private)

    def test_build_workspace_filter(self):
        from services.knowledge.retrieval.filters import RetrievalFilter, build_mongo_filter
        f = RetrievalFilter(user_id="u1", workspace_id="ws1")
        mf = build_mongo_filter(f)
        clauses = mf["$or"]
        has_workspace = any(c.get("workspace_id") == "ws1" for c in clauses)
        self.assertTrue(has_workspace)

    def test_year_filter(self):
        from services.knowledge.retrieval.filters import RetrievalFilter, build_mongo_filter
        f = RetrievalFilter(user_id="u1", filter_year_min=2020, filter_year_max=2024)
        mf = build_mongo_filter(f)
        self.assertIn("publication_year", mf)
        self.assertEqual(mf["publication_year"]["$gte"], 2020)


# ===========================================================================
# 12. Hybrid Retriever — BM25 keyword scoring
# ===========================================================================
class TestHybridRetrieverKeyword(unittest.TestCase):
    def test_bm25_scores_relevant_higher(self):
        from services.knowledge.retrieval.hybrid_retriever import _bm25_score
        query = ["machine", "learning", "neural"]
        doc_relevant = ["machine", "learning", "deep", "neural", "network"]
        doc_irrelevant = ["baking", "bread", "flour", "yeast", "oven"]
        df = {"machine": 1, "learning": 1, "neural": 1, "baking": 1}
        avgdl = 5.0
        s_rel = _bm25_score(query, doc_relevant, avgdl, df, 2)
        s_irr = _bm25_score(query, doc_irrelevant, avgdl, df, 2)
        self.assertGreater(s_rel, s_irr)

    def test_bm25_zero_for_no_overlap(self):
        from services.knowledge.retrieval.hybrid_retriever import _bm25_score
        s = _bm25_score(["machine"], ["bread", "butter"], 5.0, {}, 10)
        self.assertEqual(s, 0.0)

    def test_rrf_merge(self):
        from services.knowledge.models import SearchResult
        from services.knowledge.retrieval.hybrid_retriever import _rrf_merge

        def make_result(cid, score):
            return SearchResult(chunk_id=cid, document_id="d", text="t", score=score)

        sem = [make_result("a", 0.9), make_result("b", 0.7), make_result("c", 0.5)]
        kw = [make_result("b", 0.8), make_result("a", 0.6), make_result("d", 0.4)]
        merged = _rrf_merge(sem, kw, sem_weight=0.65, kw_weight=0.35, top_k=4)
        ids = [r.chunk_id for r in merged]
        # "b" appears in both lists → should rank highly
        self.assertIn("b", ids[:2])

    def test_rrf_top_k_respected(self):
        from services.knowledge.models import SearchResult
        from services.knowledge.retrieval.hybrid_retriever import _rrf_merge

        def make_result(cid):
            return SearchResult(chunk_id=cid, document_id="d", text="t", score=0.5)

        sem = [make_result(str(i)) for i in range(10)]
        kw = [make_result(str(i)) for i in range(10)]
        merged = _rrf_merge(sem, kw, 0.65, 0.35, top_k=3)
        self.assertEqual(len(merged), 3)


# ===========================================================================
# 13. Context Builder
# ===========================================================================
class TestContextBuilder(unittest.TestCase):
    def _make_result(self, chunk_id, text, score=0.8, author="Smith, J.", year=2023):
        from services.knowledge.models import SearchResult
        return SearchResult(
            chunk_id=chunk_id, document_id="doc1", text=text,
            score=score, semantic_score=score,
            authors=[author], publication_year=year,
            section="Methods",
        )

    def test_build_returns_context_and_citations(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder(max_tokens=2000, max_chunks=5)
        results = [self._make_result("c1", "This is relevant content about machine learning.")]
        context, citations = builder.build(results)
        self.assertIn("Source 1", context)
        self.assertEqual(len(citations), 1)

    def test_empty_results(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder()
        context, citations = builder.build([])
        self.assertEqual(context, "")
        self.assertEqual(citations, [])

    def test_deduplication(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder(dedup_threshold=0.5)
        # Two nearly identical results
        text = "This paper describes a novel approach to machine learning classification."
        results = [
            self._make_result("c1", text),
            self._make_result("c2", text + " Additional words."),
        ]
        context, citations = builder.build(results)
        # The duplicate should be removed
        self.assertEqual(len(citations), 1)

    def test_token_budget_respected(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder(max_tokens=50, max_chunks=10)
        results = [
            self._make_result(f"c{i}", " ".join(["word"] * 40))
            for i in range(5)
        ]
        _, citations = builder.build(results)
        # Should include fewer chunks due to token budget
        self.assertLessEqual(len(citations), 2)

    def test_max_chunks_respected(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder(max_tokens=100000, max_chunks=2)
        # Make texts genuinely distinct so deduplication doesn't fire
        distinct_texts = [
            "Quantum entanglement describes correlations between particles that exceed classical physics.",
            "Renaissance painting techniques relied heavily on oil glazing over tempera underpaint.",
            "The lymphatic system returns interstitial fluid to the bloodstream via thoracic duct.",
            "Graph neural networks aggregate neighborhood features for node classification tasks.",
            "Hydrothermal vents support chemosynthetic ecosystems deep below the ocean surface.",
        ]
        results = [self._make_result(f"c{i}", distinct_texts[i]) for i in range(5)]
        _, citations = builder.build(results)
        self.assertEqual(len(citations), 2)

    def test_citation_format_in_context(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder()
        results = [self._make_result("c1", "Important research finding.", author="Doe, Jane")]
        context, _ = builder.build(results)
        self.assertIn("Doe", context)

    def test_separator_present(self):
        from services.knowledge.context.context_builder import ContextBuilder
        builder = ContextBuilder(max_tokens=100000, max_chunks=10)
        distinct_texts = [
            "Stellar nucleosynthesis produces heavy elements inside massive stars.",
            "Byzantine architecture is characterized by large central domes and gold mosaics.",
            "Ribosomal RNA catalyzes peptide bond formation during protein synthesis.",
        ]
        results = [self._make_result(f"c{i}", distinct_texts[i]) for i in range(3)]
        context, _ = builder.build(results)
        self.assertIn("---", context)


# ===========================================================================
# 14. NumpyVectorStore
# ===========================================================================
class TestNumpyVectorStore(unittest.TestCase):
    def _mock_db(self, existing_chunks=None):
        """Create a mock async MongoDB db object."""
        db = MagicMock()
        coll = AsyncMock()

        # Mock insert_many
        insert_result = MagicMock()
        insert_result.inserted_ids = [f"id_{i}" for i in range(10)]
        coll.insert_many = AsyncMock(return_value=insert_result)

        # Mock count_documents
        coll.count_documents = AsyncMock(return_value=len(existing_chunks or []))

        # Mock find → to_list
        find_result = MagicMock()
        find_result.to_list = AsyncMock(return_value=existing_chunks or [])
        coll.find = MagicMock(return_value=find_result)

        db.__getitem__ = MagicMock(return_value=coll)
        return db, coll

    def test_add_and_search(self):
        from services.knowledge.models import Chunk
        from services.knowledge.vector_store.numpy_store import NumpyVectorStore

        db, coll = self._mock_db()

        async def run():
            store = NumpyVectorStore(db)
            store._loaded = True  # skip DB load
            chunk = Chunk(
                document_id="doc1", chunk_index=0,
                text="machine learning neural networks",
                user_id="u1", visibility="private",
                embedding=[0.1, 0.8, 0.1],
            )
            await store.add_chunks([chunk])
            results = await store.search([0.1, 0.8, 0.1], top_k=5, filter_user_id="u1")
            return results

        results = _run(run())
        self.assertGreater(len(results), 0)
        self.assertGreater(results[0].semantic_score, 0.9)

    def test_permission_filter_private(self):
        from services.knowledge.models import Chunk
        from services.knowledge.vector_store.numpy_store import NumpyVectorStore

        db, _ = self._mock_db()

        async def run():
            store = NumpyVectorStore(db)
            store._loaded = True
            # Add private chunk belonging to user2
            chunk = Chunk(
                document_id="doc1", chunk_index=0,
                text="private document",
                user_id="u2", visibility="private",
                embedding=[0.0, 1.0, 0.0],
            )
            await store.add_chunks([chunk])
            # user1 should not see it
            results = await store.search([0.0, 1.0, 0.0], top_k=5, filter_user_id="u1")
            return results

        results = _run(run())
        self.assertEqual(len(results), 0)

    def test_permission_filter_public(self):
        from services.knowledge.models import Chunk
        from services.knowledge.vector_store.numpy_store import NumpyVectorStore

        db, _ = self._mock_db()

        async def run():
            store = NumpyVectorStore(db)
            store._loaded = True
            chunk = Chunk(
                document_id="doc1", chunk_index=0,
                text="public document",
                user_id="u2", visibility="public",
                embedding=[0.0, 1.0, 0.0],
            )
            await store.add_chunks([chunk])
            results = await store.search([0.0, 1.0, 0.0], top_k=5, filter_user_id="u1")
            return results

        results = _run(run())
        self.assertEqual(len(results), 1)

    def test_empty_store_returns_empty(self):
        from services.knowledge.vector_store.numpy_store import NumpyVectorStore
        db, _ = self._mock_db()

        async def run():
            store = NumpyVectorStore(db)
            store._loaded = True
            return await store.search([1.0, 0.0], top_k=5)

        self.assertEqual(_run(run()), [])

    def test_cosine_similarity_computation(self):
        """Verify cosine similarity math directly."""
        import numpy as np
        # Manual cosine: orthogonal vectors → 0, identical → 1
        q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        m = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32)
        q_norm = np.linalg.norm(q)
        m_norms = np.linalg.norm(m, axis=1)
        scores = (m @ q) / (m_norms * q_norm)
        self.assertAlmostEqual(float(scores[0]), 0.0, places=5)
        self.assertAlmostEqual(float(scores[1]), 1.0, places=5)


# ===========================================================================
# 15. Integration: EmbeddingService with TF-IDF fallback
# ===========================================================================
class TestEmbeddingServiceTFIDFFallback(unittest.TestCase):
    def test_embeds_with_tfidf_when_no_providers(self):
        from services.knowledge.config import KnowledgeConfig
        from services.knowledge.embeddings.service import EmbeddingService

        cfg = KnowledgeConfig(embedding_provider="tfidf", openai_api_key="")
        svc = EmbeddingService(cfg)
        # Force TF-IDF path
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        svc._provider = TFIDFEmbeddingProvider()

        async def run():
            return await svc.embed("quantum computing algorithms")

        emb = _run(run())
        self.assertIsInstance(emb, list)
        self.assertGreater(len(emb), 0)

    def test_batch_embed(self):
        from services.knowledge.config import KnowledgeConfig
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        from services.knowledge.embeddings.service import EmbeddingService

        cfg = KnowledgeConfig(embedding_provider="tfidf")
        svc = EmbeddingService(cfg)
        svc._provider = TFIDFEmbeddingProvider()

        async def run():
            return await svc.embed_batch(["text one", "text two", "text three"])

        embs = _run(run())
        self.assertEqual(len(embs), 3)

    def test_embedding_cache_works(self):
        from services.knowledge.config import KnowledgeConfig
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        from services.knowledge.embeddings.service import EmbeddingService

        cfg = KnowledgeConfig()
        svc = EmbeddingService(cfg)
        svc._provider = TFIDFEmbeddingProvider()

        async def run():
            e1 = await svc.embed("cached text")
            e2 = await svc.embed("cached text")
            return e1, e2

        e1, e2 = _run(run())
        self.assertEqual(e1, e2)
        self.assertGreater(svc.cache_size(), 0)


# ===========================================================================
# 16. Integration: IngestionPipeline (mocked embedding + store)
# ===========================================================================
class TestIngestionPipeline(unittest.TestCase):
    def _make_pipeline(self):
        from services.knowledge.config import KnowledgeConfig
        from services.knowledge.embeddings.service import EmbeddingService
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        from services.knowledge.ingestion.pipeline import IngestionPipeline

        cfg = KnowledgeConfig(chunk_min_tokens=1)
        svc = EmbeddingService(cfg)
        svc._provider = TFIDFEmbeddingProvider()

        mock_store = AsyncMock()
        mock_store.add_chunks = AsyncMock()

        pipeline = IngestionPipeline(cfg, svc, mock_store)
        return pipeline, mock_store

    def test_ingest_txt(self):
        from services.knowledge.models import IndexingJob, DocumentMetadata
        pipeline, store = self._make_pipeline()
        job = IndexingJob(
            job_id="j1", document_id="d1", user_id="u1",
            filename="test.txt", file_type="txt",
            content_bytes=b"This is a test document with enough content to chunk properly.",
        )

        async def run():
            return await pipeline.ingest(job)

        doc = _run(run())
        self.assertEqual(doc.status, "indexed")
        self.assertGreater(doc.chunk_count, 0)
        store.add_chunks.assert_called_once()

    def test_ingest_markdown(self):
        from services.knowledge.models import IndexingJob
        pipeline, _ = self._make_pipeline()
        content = b"# Introduction\n\nThis is the intro.\n\n## Methods\n\nWe used method X."
        job = IndexingJob(
            job_id="j2", document_id="d2", user_id="u1",
            filename="paper.md", file_type="md",
            content_bytes=content,
        )
        doc = _run(pipeline.ingest(job))
        self.assertEqual(doc.status, "indexed")

    def test_ingest_csv(self):
        from services.knowledge.models import IndexingJob
        pipeline, _ = self._make_pipeline()
        content = b"name,score\nAlice,95\nBob,87\nCharlie,92"
        job = IndexingJob(
            job_id="j3", document_id="d3", user_id="u1",
            filename="grades.csv", file_type="csv",
            content_bytes=content,
        )
        doc = _run(pipeline.ingest(job))
        self.assertEqual(doc.status, "indexed")

    def test_ingest_html(self):
        from services.knowledge.models import IndexingJob
        pipeline, _ = self._make_pipeline()
        html = b"<html><body><h1>Title</h1><p>Content paragraph here.</p></body></html>"
        job = IndexingJob(
            job_id="j4", document_id="d4", user_id="u1",
            filename="page.html", file_type="html",
            content_bytes=html,
        )
        doc = _run(pipeline.ingest(job))
        self.assertEqual(doc.status, "indexed")

    def test_unsupported_type_raises(self):
        from services.knowledge.models import IndexingJob
        pipeline, _ = self._make_pipeline()
        job = IndexingJob(
            job_id="j5", document_id="d5", user_id="u1",
            filename="file.xyz", file_type="xyz",
            content_bytes=b"data",
        )
        with self.assertRaises(ValueError):
            _run(pipeline.ingest(job))


# ===========================================================================
# 17. KnowledgeEngine high-level (mocked DB)
# ===========================================================================
class TestKnowledgeEngine(unittest.TestCase):
    def _make_engine(self):
        from services.knowledge.config import KnowledgeConfig
        from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
        from services.knowledge.embeddings.service import EmbeddingService
        from services.knowledge.engine import KnowledgeEngine

        cfg = KnowledgeConfig(chunk_min_tokens=1)

        # Build a mock async db
        db = MagicMock()
        coll = AsyncMock()
        coll.count_documents = AsyncMock(return_value=0)
        coll.find_one = AsyncMock(return_value=None)
        find_mock = MagicMock()
        find_mock.sort = MagicMock(return_value=find_mock)
        find_mock.limit = MagicMock(return_value=find_mock)
        find_mock.to_list = AsyncMock(return_value=[])
        coll.find = MagicMock(return_value=find_mock)
        coll.insert_many = AsyncMock(return_value=MagicMock(inserted_ids=[]))
        coll.update_one = AsyncMock()
        coll.delete_one = AsyncMock()
        coll.delete_many = AsyncMock(return_value=MagicMock(deleted_count=0))
        db.__getitem__ = MagicMock(return_value=coll)

        engine = KnowledgeEngine(cfg, db)
        engine._emb._provider = TFIDFEmbeddingProvider()
        engine._indexer._running = False  # don't actually start worker
        return engine, db

    def test_submit_document(self):
        engine, db = self._make_engine()
        doc_id = _run(engine.submit_document(
            content_bytes=b"Test document content for indexing.",
            filename="test.txt",
            user_id="u1",
        ))
        self.assertIsInstance(doc_id, str)
        self.assertEqual(len(doc_id), 36)  # UUID format

    def test_retrieve_empty_returns_empty(self):
        engine, _ = self._make_engine()
        # Ensure store has no chunks
        engine._vs._loaded = True
        results = _run(engine.retrieve("machine learning", user_id="u1"))
        self.assertEqual(results, [])

    def test_build_context_empty(self):
        engine, _ = self._make_engine()
        engine._vs._loaded = True
        context, citations = _run(engine.build_context("test query", "u1"))
        self.assertEqual(context, "")
        self.assertEqual(citations, [])

    def test_rag_eligible_feature(self):
        engine, _ = self._make_engine()
        self.assertTrue(_run(engine.is_rag_eligible("literature_review")))
        self.assertTrue(_run(engine.is_rag_eligible("manuscript_review")))

    def test_rag_ineligible_feature(self):
        engine, _ = self._make_engine()
        self.assertFalse(_run(engine.is_rag_eligible("create_presentation")))

    def test_clear_caches(self):
        engine, _ = self._make_engine()
        # Should not raise
        engine.clear_caches()

    def test_get_stats(self):
        engine, _ = self._make_engine()
        engine._vs._loaded = True
        stats = _run(engine.get_stats())
        self.assertIn("enabled", stats)
        self.assertIn("total_documents", stats)
        self.assertIn("total_chunks", stats)


# ===========================================================================
# 18. RAG feature set completeness
# ===========================================================================
class TestRAGFeatureSet(unittest.TestCase):
    def test_known_features_are_eligible(self):
        from services.knowledge.engine import _RAG_FEATURES
        expected = {
            "research_gap_finder", "literature_review", "manuscript_review",
            "statistical_review", "research_design_advisor", "ai_assistant",
            "ai_chat", "teaching_lesson_generation", "teaching_assessment_generation",
        }
        self.assertTrue(expected.issubset(_RAG_FEATURES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
