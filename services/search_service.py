from duckduckgo_search import DDGS

class SearchService:
    def __init__(self):
        self.ddgs = DDGS()

    def search_web(self, query, max_results=5):
        try:
            results = self.ddgs.text(query, max_results=max_results)
            return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except Exception as e:
            return {"error": f"Search Error: {e}"}