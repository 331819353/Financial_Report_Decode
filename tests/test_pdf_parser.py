from financial_report_decode.services.pdf_parser import PdfParser


def test_should_use_ocr_when_text_is_empty() -> None:
    parser = PdfParser(ocr_enabled=True, min_text_length=10, garbled_ratio_threshold=0.1)
    assert parser._should_use_ocr("") is True


def test_should_use_ocr_when_text_is_garbled() -> None:
    parser = PdfParser(ocr_enabled=True, min_text_length=10, garbled_ratio_threshold=0.05)
    garbled_text = "正常文本" + "ஂ" * 10 + "更多内容"
    assert parser._should_use_ocr(garbled_text) is True


def test_should_not_use_ocr_when_text_is_good() -> None:
    parser = PdfParser(ocr_enabled=True, min_text_length=10, garbled_ratio_threshold=0.2)
    good_text = "这是可读的中文财报文本。" * 50
    assert parser._should_use_ocr(good_text) is False
