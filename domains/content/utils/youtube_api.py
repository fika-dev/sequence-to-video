"""YouTube API client for fetching videos and transcripts."""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import aiohttp

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        TooManyRequests,
        YouTubeRequestFailed,
    )
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    # Define error classes for type checking even if library not available
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
    VideoUnavailable = Exception


class YouTubeAPIClient:
    """Client for interacting with YouTube Data API."""

    def __init__(self, api_key: Optional[str] = None, transcript_api_url: Optional[str] = None):
        """
        Initialize YouTube API client.

        Args:
            api_key: YouTube Data API key (defaults to YOUTUBE_API_KEY env var)
            transcript_api_url: Custom transcript API URL (defaults to gen-staging.fikad.boo)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.transcript_api_url = transcript_api_url or os.getenv(
            'TRANSCRIPT_API_URL',
            'https://gen-staging.fikad.boo/util/get-video-script'
        )

        if not self.api_key:
            print("⚠️  YOUTUBE_API_KEY not found in environment variables.")
            print("   YouTube search and metadata will not work.")
            self.youtube = None
        elif not YOUTUBE_API_AVAILABLE:
            print("⚠️  google-api-python-client not installed. YouTube API will not work.")
            self.youtube = None
        else:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                print(f"⚠️  Failed to initialize YouTube API client: {e}")
                self.youtube = None

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        video_type: str = "short"
    ) -> List[Dict]:
        """
        Search for YouTube videos.

        Args:
            query: Search query
            max_results: Maximum number of results
            video_type: Type of video ("short", "long", "any")
                       - "short": Only YouTube Shorts (≤60 seconds)
                       - "long": Only long-form videos (>240 seconds)
                       - "any": All video durations
                       Defaults to "short" for short-form content analysis.

        Returns:
            List of video dictionaries with metadata
        """
        if not self.youtube:
            print(f"⚠️  YouTube API not initialized. Cannot search for: {query}")
            return []

        try:
            # Prepare search parameters
            search_params = {
                'part': 'id,snippet',
                'q': query,
                'type': 'video',
                'maxResults': min(max_results, 50),  # YouTube API limit is 50
                'order': 'relevance',
                'videoDefinition': 'any',
                'videoCaption': 'any',
            }

            # Filter for shorts if requested
            if video_type == "short":
                search_params['videoDuration'] = 'short'
            elif video_type == "long":
                search_params['videoDuration'] = 'long'

            # Execute search
            request = self.youtube.search().list(**search_params)
            response = request.execute()

            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']

                # Get additional video details
                video_details = await self.get_video_metadata(video_id)

                video_data = {
                    'video_id': video_id,
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'channel': snippet.get('channelTitle', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                }

                # Add details from metadata if available
                if video_details:
                    video_data.update({
                        'topics': video_details.get('topics', [])
                    })

                videos.append(video_data)

            return videos

        except HttpError as e:
            error_content = e.error_details[0] if e.error_details else {}
            error_reason = error_content.get('reason', 'unknown')

            if error_reason == 'quotaExceeded':
                print(f"⚠️  YouTube API quota exceeded. Cannot search for: {query}")
            elif error_reason == 'invalidApiKey':
                print(f"⚠️  Invalid YouTube API key.")
            else:
                print(f"⚠️  YouTube API error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Error searching YouTube: {e}")
            return []

    async def get_transcript(self, video_id: str) -> Optional[str]:
        """
        Get transcript for a YouTube video using custom API endpoint.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript text or None if not available
        """
        # Try custom API endpoint first
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"videoId": video_id}

                async with session.post(
                    self.transcript_api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        video_script = data.get("videoScript", [])

                        if not video_script:
                            print(f"⚠️  Custom API returned no videoScript for {video_id}")
                        else:
                            # videoScript is an array of transcript segments
                            # Each segment represents a portion of the video transcript:
                            # - Time-segmented chunks (e.g., "0:00-0:05: Hello world")
                            # - Sentence-level segments
                            # - Or continuous text blocks
                            # We combine all segments into a single transcript string
                            transcript_parts = []
                            for entry in video_script:
                                if isinstance(entry, dict):
                                    # Try common transcript field names
                                    text = (
                                        entry.get('text') or
                                        entry.get('transcript') or
                                        entry.get('content') or
                                        entry.get('sentence') or
                                        entry.get('line')
                                    )
                                    if text:
                                        transcript_parts.append(str(text).strip())
                                    else:
                                        # If no standard field, collect all string values
                                        # (handles cases where structure might vary)
                                        string_values = [str(v).strip() for v in entry.values()
                                                       if isinstance(v, str) and len(str(v).strip()) > 0]
                                        transcript_parts.extend(string_values)
                                elif isinstance(entry, str):
                                    if entry.strip():
                                        transcript_parts.append(entry.strip())

                            if transcript_parts:
                                transcript_text = ' '.join(transcript_parts)
                                print(f"✅ Retrieved transcript from custom API ({len(transcript_text)} chars, {len(video_script)} segments)")
                                # Note: "segments" are individual pieces of the transcript (sentences, time chunks, etc.)
                                # that are combined into the full transcript text
                                return transcript_text
                            else:
                                print(f"⚠️  Custom API returned videoScript with no extractable text for {video_id}")
                                print(f"   Sample entry structure: {video_script[0] if video_script else 'N/A'}")
                    else:
                        error_text = await response.text()
                        print(f"⚠️  Custom transcript API returned status {response.status}: {error_text[:200]}")

        except aiohttp.ClientError as e:
            print(f"⚠️  Error calling custom transcript API for {video_id}: {e}")
        except json.JSONDecodeError as e:
            print(f"⚠️  Error parsing JSON from custom transcript API: {e}")
        except Exception as e:
            print(f"⚠️  Unexpected error calling custom transcript API: {e}")

        # Fallback to youtube-transcript-api if custom API fails
        if TRANSCRIPT_API_AVAILABLE:
            try:
                print(f"   Trying fallback: youtube-transcript-api for {video_id}")
                
                # Try to get transcript directly (simpler approach)
                # First try Korean, then English, then any available language
                transcript_data = None
                for lang_codes in [['ko', 'en'], ['en'], ['ko']]:
                    try:
                        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=lang_codes)
                        break
                    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
                        continue
                    except Exception:
                        # Try next language set
                        continue
                
                if transcript_data:
                    # Combine all text
                    transcript_text = ' '.join([entry['text'] for entry in transcript_data])
                    print(f"✅ Retrieved transcript from fallback API ({len(transcript_text)} chars)")
                    return transcript_text
                else:
                    print(f"⚠️  No transcript available via fallback for {video_id}")

            except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, TooManyRequests, YouTubeRequestFailed) as e:
                print(f"⚠️  Transcript not available via fallback for {video_id}: {type(e).__name__}")
            except Exception as e:
                print(f"⚠️  Error fetching transcript via fallback: {e}")
        else:
            print(f"⚠️  youtube-transcript-api not available as fallback")

        return None

    async def get_video_metadata(self, video_id: str) -> Optional[Dict]:
        """
        Get metadata for a YouTube video.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video metadata
        """
        if not self.youtube:
            return None

        try:
            request = self.youtube.videos().list(
                part='statistics,contentDetails,snippet',
                id=video_id
            )
            response = request.execute()

            if not response.get('items'):
                return None

            item = response['items'][0]
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            snippet = item.get('snippet', {})

            # Parse duration (ISO 8601 format: PT1H2M10S)
            duration_str = content_details.get('duration', '')
            duration = self._parse_duration(duration_str)

            # Extract tags/topics
            topics = snippet.get('tags', [])[:10]  # Limit to 10 tags

            return {
                'topics': topics,
            }

        except HttpError as e:
            print(f"⚠️  Error fetching video metadata for {video_id}: {e}")
            return None
        except Exception as e:
            print(f"⚠️  Error getting video metadata: {e}")
            return None

    def _parse_duration(self, duration_str: str) -> Optional[str]:
        """
        Parse ISO 8601 duration to human-readable format.

        Args:
            duration_str: ISO 8601 duration (e.g., "PT1H2M10S")

        Returns:
            Human-readable duration (e.g., "1:02:10")
        """
        if not duration_str:
            return None

        import re

        # Extract hours, minutes, seconds
        hours_match = re.search(r'(\d+)H', duration_str)
        minutes_match = re.search(r'(\d+)M', duration_str)
        seconds_match = re.search(r'(\d+)S', duration_str)

        hours = int(hours_match.group(1)) if hours_match else 0
        minutes = int(minutes_match.group(1)) if minutes_match else 0
        seconds = int(seconds_match.group(1)) if seconds_match else 0

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
