"""Google Search client for fetching web search results."""

import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SEARCH_API_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_API_AVAILABLE = False


class GoogleSearchClient:
    """Client for performing Google searches using Custom Search API."""

    def __init__(self, api_key: Optional[str] = None, search_engine_id: Optional[str] = None):
        """
        Initialize Google Search client.

        Args:
            api_key: Google Custom Search API key (defaults to GOOGLE_SEARCH_API_KEY env var)
            search_engine_id: Custom Search Engine ID (defaults to GOOGLE_SEARCH_ENGINE_ID env var)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('GOOGLE_SEARCH_API_KEY')
        self.search_engine_id = search_engine_id or os.getenv('GOOGLE_SEARCH_ENGINE_ID')

        if not self.api_key or not self.search_engine_id:
            print("⚠️  GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_ENGINE_ID not found in environment variables.")
            print("   Google Search will not work.")
            self.service = None
            return

        if not GOOGLE_SEARCH_API_AVAILABLE:
            print("⚠️  google-api-python-client not installed. Google Search will not work.")
            self.service = None
            return

        try:
            self.service = build('customsearch', 'v1', developerKey=self.api_key)
        except Exception as e:
            print(f"⚠️  Failed to initialize Google Search API client: {e}")
            self.service = None

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_type: str = "web"
    ) -> List[Dict]:
        """
        Perform Google search.

        Args:
            query: Search query
            max_results: Maximum number of results (max 10 per request, API will paginate if needed)
            search_type: Type of search (web, image, video) - currently only web is supported

        Returns:
            List of search result dictionaries with 'title', 'url', 'snippet' keys
        """
        if not self.service:
            print(f"⚠️  Google Search API not initialized. Cannot search for: {query}")
            return []

        try:
            results = []
            num_pages = (max_results + 9) // 10  # Google Custom Search returns max 10 per page

            for page in range(min(num_pages, 10)):  # API limit: 100 results max (10 pages)
                start_index = (page * 10) + 1

                request = self.service.cse().list(
                    q=query,
                    cx=self.search_engine_id,
                    num=min(10, max_results - len(results)),
                    start=start_index,
                    safe='active'  # Safe search: active, off, or medium
                )

                response = request.execute()

                # Extract results
                items = response.get('items', [])
                for item in items:
                    result = {
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'display_url': item.get('displayLink', ''),
                    }
                    results.append(result)

                # Break if we have enough results or no more pages
                if len(results) >= max_results or len(items) < 10:
                    break

                # Check if there are more pages
                search_info = response.get('searchInformation', {})
                total_results = int(search_info.get('totalResults', 0))
                if start_index + 10 > total_results:
                    break

            return results[:max_results]

        except HttpError as e:
            error_content = e.error_details[0] if e.error_details else {}
            error_reason = error_content.get('reason', 'unknown')

            if error_reason == 'dailyLimitExceeded':
                print(f"⚠️  Google Custom Search API daily limit exceeded. Cannot search for: {query}")
            elif error_reason == 'invalidApiKey':
                print(f"⚠️  Invalid Google Search API key.")
            elif error_reason == 'invalid':
                print(f"⚠️  Invalid search engine ID: {self.search_engine_id}")
            else:
                print(f"⚠️  Google Search API error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Error searching Google: {e}")
            return []

    async def search_gossip(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Search for gossip/community discussions.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of gossip-related search results
        """
        gossip_query = f"{query} gossip discussion community forum"
        return await self.search(query=gossip_query, max_results=max_results)

    async def search_facts(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Search for fact-based news/research.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of fact-based search results
        """
        fact_query = f"{query} research study news facts"
        return await self.search(query=fact_query, max_results=max_results)
