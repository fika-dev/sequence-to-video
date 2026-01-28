"""Data schemas for intermediate processing."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class SearchQueries(BaseModel):
    """Search queries organized by tracks."""

    track1: List[str] = Field(default_factory=list, description="First track of search queries")
    track2: List[str] = Field(default_factory=list, description="Second track of search queries")
    track3: List[str] = Field(default_factory=list, description="Third track of search queries")

    def get_all_queries(self) -> List[str]:
        """Get all queries across all tracks."""
        return self.track1 + self.track2 + self.track3


class VideoMetadata(BaseModel):
    """Metadata for a YouTube video."""

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    topics: List[str] = Field(default_factory=list, description="Video topics/tags")


class Transcript(BaseModel):
    """Transcript data with metadata."""

    video_metadata: VideoMetadata = Field(..., description="Associated video metadata")
    text: str = Field(..., description="Transcript text content")
    sentences: List[str] = Field(default_factory=list, description="Sentence-segmented transcript")


class GossipItem(BaseModel):
    """Community gossip item from Google Search."""

    title: str = Field(..., description="Gossip item title")
    source: str = Field(..., description="Source URL or site name")
    summary: str = Field(..., description="Gossip summary")


class FactItem(BaseModel):
    """Fact-based news or research item from Google Search."""

    title: str = Field(..., description="Fact item title")
    source: str = Field(..., description="Source URL or site name")
    summary: str = Field(..., description="Fact summary")


class TrendingKeyword(BaseModel):
    """Trending keyword from S3."""

    keyword: str = Field(..., description="The trending keyword")


class MacroTrend(BaseModel):
    """Macro trend from S3."""

    trend_title: str = Field(..., description="Title of the macro trend")
    description: str = Field(..., description="Description of the trend")


class ContentMaterial(BaseModel):
    """Aggregated content material for script generation."""

    transcripts: List[Transcript] = Field(default_factory=list, description="Video transcripts")
    gossip_items: List[GossipItem] = Field(default_factory=list, description="Community gossip items")
    fact_items: List[FactItem] = Field(default_factory=list, description="Fact-based news/research items")
    trending_keywords: List[TrendingKeyword] = Field(default_factory=list, description="Trending keywords from S3")
    macro_trends: List[MacroTrend] = Field(default_factory=list, description="Macro trends from S3")

    class Config:
        json_schema_extra = {
            "example": {
                "transcripts": [],
                "gossip_items": [],
                "fact_items": [],
                "trending_keywords": [],
                "macro_trends": []
            }
        }
