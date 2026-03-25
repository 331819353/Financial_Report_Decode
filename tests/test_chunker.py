from financial_report_decode.services.chunker import ContextualChunker


def test_chunker_preserves_context_window() -> None:
    text = "A" * 25000
    chunks = ContextualChunker(core_size=20000, context_size=1000).split(text)

    assert len(chunks) == 2
    assert chunks[0].start == 0
    assert chunks[0].end == 21000
    assert chunks[1].start == 19000
    assert chunks[1].end == 25000

