from financial_report_decode.clients.network_search_client import NetworkSearchClient


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_search_by_query_returns_top_three_by_score(monkeypatch) -> None:
    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "pageItems": [
                    {"link": "https://a.example.com", "mainText": "A", "rerankScore": 0.72},
                    {"link": "https://b.example.com", "mainText": "B", "rerankScore": 0.95},
                    {"link": "https://c.example.com", "mainText": "C", "rerankScore": 0.88},
                    {"link": "https://d.example.com", "mainText": "D", "rerankScore": 0.31},
                ]
            }
        )

    monkeypatch.setattr("financial_report_decode.clients.network_search_client.requests.post", fake_post)

    result = NetworkSearchClient(token="token", base_url="https://search.example.com").search_by_query("测试问题")

    assert [item.source for item in result] == [
        "https://b.example.com",
        "https://c.example.com",
        "https://a.example.com",
    ]
    assert [item.content for item in result] == ["B", "C", "A"]
