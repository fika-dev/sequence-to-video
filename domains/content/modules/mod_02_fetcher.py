"""Module 2: Data Fetcher - YouTube, Google Search, S3."""

from typing import List
from ..core.llm_client import LLMClient
from ..domain.schema_data import (
    SearchQueries,
    ContentMaterial,
    VideoMetadata,
    Transcript,
    GossipItem,
    FactItem
)
from ..prompts.gossip_fetcher import get_gossip_fetching_prompt
from ..utils.youtube_api import YouTubeAPIClient
from ..utils.s3_client import S3Client
from ..domain.schema_data import TrendingKeyword, MacroTrend


class DataFetcher:
    """Fetches data from YouTube, Google Search, and S3 based on search queries."""

    def __init__(
        self,
        llm_client: LLMClient,
        youtube_client: YouTubeAPIClient = None,
        s3_client: S3Client = None
    ):
        """
        Initialize DataFetcher with API clients.

        Args:
            llm_client: LLMClient for processing search results (includes Gemini's Google Search grounding)
            youtube_client: YouTube API client instance
            s3_client: S3 client instance for trending keywords and macro trends
        """
        self.llm_client = llm_client
        self.youtube_client = youtube_client or YouTubeAPIClient()
        self.s3_client = s3_client or S3Client()
        self.model = "gemini-2.0-flash"
        self.temperature = 0.5

    async def fetch_content_material(
        self,
        search_queries: SearchQueries
    ) -> ContentMaterial:
        """
        Fetch content material from all sources based on search queries.

        Args:
            search_queries: Search queries organized by tracks

        Returns:
            ContentMaterial with transcripts, gossip, and facts
        """
        # Fetch YouTube videos and transcripts
        transcripts = await self._fetch_youtube_transcripts(search_queries)

        # Fetch gossip items
        gossip_items = await self._fetch_gossip_items(search_queries)

        # Fetch fact-based items
        fact_items = await self._fetch_fact_items(search_queries)

        # Fetch trending keywords and macro trends from S3
        trending_keywords = await self._fetch_trending_keywords()
        macro_trends = await self._fetch_macro_trends()

        return ContentMaterial(
            transcripts=transcripts,
            gossip_items=gossip_items,
            fact_items=fact_items,
            trending_keywords=trending_keywords,
            macro_trends=macro_trends
        )

    async def _fetch_youtube_transcripts(
        self,
        search_queries: SearchQueries
    ) -> List[Transcript]:
        """Fetch YouTube videos and their transcripts."""
        transcripts = []

        # Get all queries
        all_queries = search_queries.get_all_queries()

        if not all_queries:
            print("⚠️  Warning: No search queries available. Cannot fetch YouTube videos.")
            print("   This may be because query generation returned empty results.")
            return transcripts

        print(f"📺 Fetching YouTube videos for {len(all_queries)} queries...")

        # Fetch videos for each query
        for query in all_queries[:10]:  # Limit to avoid too many API calls
            videos = await self.youtube_client.search_videos(query, max_results=3)

            if not videos:
                print(f"   ⚠️  No videos found for query: '{query}' (YouTube API may not be implemented)")

            for video in videos:
                # Get transcript
                transcript_text = await self.youtube_client.get_transcript(video['video_id'])

                if transcript_text:
                    print(f"   ✅ Got transcript for video: {video.get('title', 'Unknown')[:50]}")
                else:
                    print(f"   ⚠️  No transcript available for video: {video.get('video_id', 'Unknown')}")

                if transcript_text:
                    # Create VideoMetadata
                    topics = video.get('topics', [])

                    # Ensure topics is a list
                    if not isinstance(topics, list):
                        topics = []

                    video_metadata = VideoMetadata(
                        video_id=video['video_id'],
                        title=video.get('title', ''),
                        topics=topics
                    )

                    # Segment into sentences (simple split for now)
                    sentences = [s.strip() for s in transcript_text.split('.') if s.strip()]

                    # Create Transcript
                    transcript = Transcript(
                        video_metadata=video_metadata,
                        text=transcript_text,
                        sentences=sentences
                    )
                    transcripts.append(transcript)

        return transcripts

    async def _fetch_gossip_items(
        self,
        search_queries: SearchQueries
    ) -> List[GossipItem]:
        """Fetch community gossip items using Gemini's Google Search grounding."""
        # Get queries (prioritize track2 for alternative angles)
        queries = search_queries.track2 + search_queries.track1[:3]

        if not queries:
            print("⚠️  Warning: No search queries available. Cannot fetch gossip items.")
            return []

        print(f"💬 Fetching gossip items for {len(queries)} queries using Gemini's Google Search grounding...")

        gossip_items = []
        for query in queries[:5]:  # Limit queries
            # Use LLM with Gemini's built-in Google Search grounding to extract gossip items
            prompt = get_gossip_fetching_prompt(
                search_results=None,  # No raw search results - Gemini will search
                topic=query,
                content_type="gossip"
            )

            # Use search=True to enable Gemini's Google Search grounding
            # json_mode=False because search tools don't work with JSON mode
            response = await self.llm_client.generate_gemini(
                content=prompt,
                model=self.model,
                temperature=self.temperature,
                json_mode=False,  # Can't use JSON mode with search tools
                search=True  # Use Gemini's Google Search grounding
            )

            # Parse JSON from response text (may be in markdown code blocks)
            response_text = response.text if hasattr(response, 'text') else str(response)
            parsed_data = self.llm_client.parse_and_get_result(response, key="result")

            # Extract gossip items from parsed data
            gossip_data = parsed_data.get("gossip_items", []) if isinstance(parsed_data, dict) else []

            if gossip_data:
                print(f"   ✅ Found {len(gossip_data)} gossip items for query: '{query}'")
                for item_data in gossip_data:
                    if isinstance(item_data, dict):
                        item = GossipItem(
                            title=item_data.get("title", ""),
                            source=item_data.get("source", ""),
                            summary=item_data.get("summary", "")
                        )
                        gossip_items.append(item)
                        # Display brief summary
                        title = item.title[:60] + "..." if len(item.title) > 60 else item.title
                        summary = item.summary[:100] + "..." if len(item.summary) > 100 else item.summary
                        print(f"      • {title}")
                        print(f"        {summary}")
            else:
                print(f"   ⚠️  No gossip items extracted for query: '{query}'")

        return gossip_items

    async def _fetch_fact_items(
        self,
        search_queries: SearchQueries
    ) -> List[FactItem]:
        """Fetch fact-based news/research items using Gemini's Google Search grounding."""
        # Get queries (prioritize track1 for mainstream facts)
        queries = search_queries.track1 + search_queries.track3[:3]

        if not queries:
            print("⚠️  Warning: No search queries available. Cannot fetch fact items.")
            return []

        print(f"📰 Fetching fact items for {len(queries)} queries using Gemini's Google Search grounding...")

        fact_items = []
        for query in queries[:5]:  # Limit queries
            # Use LLM with Gemini's built-in Google Search grounding to extract fact items
            prompt = get_gossip_fetching_prompt(
                search_results=None,  # No raw search results - Gemini will search
                topic=query,
                content_type="fact"
            )

            # Use search=True to enable Gemini's Google Search grounding
            # json_mode=False because search tools don't work with JSON mode
            response = await self.llm_client.generate_gemini(
                content=prompt,
                model=self.model,
                temperature=self.temperature,
                json_mode=False,  # Can't use JSON mode with search tools
                search=True  # Use Gemini's Google Search grounding
            )

            # Parse JSON from response text (may be in markdown code blocks)
            response_text = response.text if hasattr(response, 'text') else str(response)
            parsed_data = self.llm_client.parse_and_get_result(response, key="result")

            # Extract fact items from parsed data
            fact_data = parsed_data.get("fact_items", []) if isinstance(parsed_data, dict) else []

            if fact_data:
                print(f"   ✅ Found {len(fact_data)} fact items for query: '{query}'")
                for item_data in fact_data:
                    if isinstance(item_data, dict):
                        item = FactItem(
                            title=item_data.get("title", ""),
                            source=item_data.get("source", ""),
                            summary=item_data.get("summary", "")
                        )
                        fact_items.append(item)
                        # Display brief summary
                        title = item.title[:60] + "..." if len(item.title) > 60 else item.title
                        summary = item.summary[:100] + "..." if len(item.summary) > 100 else item.summary
                        print(f"      • {title}")
                        print(f"        {summary}")
            else:
                print(f"   ⚠️  No fact items extracted for query: '{query}'")

        return fact_items

    async def _fetch_trending_keywords(
        self,
        date_prefix: str = None,
        limit: int = 50
    ) -> List[TrendingKeyword]:
        """Fetch trending keywords from S3."""
        keywords_data = await self.s3_client.get_trending_keywords(
            date_prefix=date_prefix,
            limit=limit
        )

        trending_keywords = []
        for kw_data in keywords_data:
            if isinstance(kw_data, dict):
                keyword = TrendingKeyword(
                    keyword=kw_data.get("keyword", "")
                )
                trending_keywords.append(keyword)
            elif isinstance(kw_data, str):
                # If just a string, create simple keyword object
                keyword = TrendingKeyword(keyword=kw_data)
                trending_keywords.append(keyword)

        return trending_keywords

    async def _fetch_macro_trends(
        self,
        date_prefix: str = None
    ) -> List[MacroTrend]:
        """Fetch macro trends from S3."""
        trends_data = await self.s3_client.get_macro_trends(
            date_prefix=date_prefix
        )

        macro_trends = []
        for trend_data in trends_data:
            if isinstance(trend_data, dict):
                trend = MacroTrend(
                    trend_title=trend_data.get("trend_title", ""),
                    description=trend_data.get("description", "")
                )
                macro_trends.append(trend)

        return macro_trends

