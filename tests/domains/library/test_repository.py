import json
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from domains.library.models import VideoClip, VideoIndex
from domains.library.repository import AssetRepository


class TestAssetRepositoryCosineSimilarity:
    def test_identical_vectors_return_1(self):
        repo = AssetRepository.__new__(AssetRepository)
        vec = [1.0, 0.0, 0.0]

        similarity = repo._cosine_similarity(vec, vec)

        assert abs(similarity - 1.0) < 1e-6

    def test_orthogonal_vectors_return_0(self):
        repo = AssetRepository.__new__(AssetRepository)
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]

        similarity = repo._cosine_similarity(vec_a, vec_b)

        assert abs(similarity) < 1e-6

    def test_opposite_vectors_return_negative_1(self):
        repo = AssetRepository.__new__(AssetRepository)
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0]

        similarity = repo._cosine_similarity(vec_a, vec_b)

        assert abs(similarity - (-1.0)) < 1e-6

    def test_similar_vectors_return_high_similarity(self):
        repo = AssetRepository.__new__(AssetRepository)
        vec_a = [0.9, 0.1, 0.0]
        vec_b = [0.8, 0.2, 0.0]

        similarity = repo._cosine_similarity(vec_a, vec_b)

        assert similarity > 0.9

    def test_empty_vectors_return_0(self):
        repo = AssetRepository.__new__(AssetRepository)

        similarity = repo._cosine_similarity([], [])

        assert similarity == 0.0

    def test_mismatched_lengths_return_0(self):
        repo = AssetRepository.__new__(AssetRepository)
        vec_a = [1.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]

        similarity = repo._cosine_similarity(vec_a, vec_b)

        assert similarity == 0.0

    def test_zero_vector_returns_0(self):
        repo = AssetRepository.__new__(AssetRepository)
        vec_a = [0.0, 0.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]

        similarity = repo._cosine_similarity(vec_a, vec_b)

        assert similarity == 0.0


class TestAssetRepositoryClipToText:
    def test_includes_description(self):
        repo = AssetRepository.__new__(AssetRepository)
        clip = VideoClip(
            clip_id="c1",
            source_file=Path("/fake.mp4"),
            start_time=0,
            end_time=5,
            description="Woman applying cream",
        )

        text = repo._clip_to_text(clip)

        assert "Woman applying cream" in text

    def test_includes_appeal_point_when_present(self):
        repo = AssetRepository.__new__(AssetRepository)
        clip = VideoClip(
            clip_id="c1",
            source_file=Path("/fake.mp4"),
            start_time=0,
            end_time=5,
            description="Product shot",
            appeal_point="Shows texture clearly",
        )

        text = repo._clip_to_text(clip)

        assert "Shows texture clearly" in text

    def test_includes_tags_when_present(self):
        repo = AssetRepository.__new__(AssetRepository)
        clip = VideoClip(
            clip_id="c1",
            source_file=Path("/fake.mp4"),
            start_time=0,
            end_time=5,
            description="Product shot",
            tags=["skincare", "closeup", "studio"],
        )

        text = repo._clip_to_text(clip)

        assert "skincare" in text
        assert "closeup" in text
        assert "studio" in text


class TestAssetRepositoryFindByEmbedding:
    def test_returns_clips_sorted_by_similarity(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        clips = [
            VideoClip(
                clip_id="far",
                source_file=Path("/fake1.mp4"),
                start_time=0,
                end_time=5,
                description="Distant content",
                embedding=[0.0, 0.0, 1.0],
            ),
            VideoClip(
                clip_id="close",
                source_file=Path("/fake2.mp4"),
                start_time=0,
                end_time=5,
                description="Close content",
                embedding=[0.9, 0.1, 0.0],
            ),
            VideoClip(
                clip_id="mid",
                source_file=Path("/fake3.mp4"),
                start_time=0,
                end_time=5,
                description="Mid content",
                embedding=[0.5, 0.5, 0.0],
            ),
        ]

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {
            "test": VideoIndex(
                source_file=Path("/test.mp4"),
                total_duration=15.0,
                analyzed_at="2025-01-01",
                clips=clips,
            )
        }
        repo.project = None
        repo.embedding_model = "text-embedding-005"

        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = [1.0, 0.0, 0.0]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]
        mock_client.models.embed_content.return_value = mock_response
        repo._embedding_client = mock_client

        results = repo.find_by_embedding("similar to first", max_results=3)

        assert results[0].clip_id == "close"
        assert results[1].clip_id == "mid"
        assert results[2].clip_id == "far"

    def test_respects_min_duration_filter(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        clips = [
            VideoClip(
                clip_id="short",
                source_file=Path("/fake1.mp4"),
                start_time=0,
                end_time=2,
                description="Short clip",
                embedding=[1.0, 0.0, 0.0],
            ),
            VideoClip(
                clip_id="long",
                source_file=Path("/fake2.mp4"),
                start_time=0,
                end_time=10,
                description="Long clip",
                embedding=[0.9, 0.1, 0.0],
            ),
        ]

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {
            "test": VideoIndex(
                source_file=Path("/test.mp4"),
                total_duration=12.0,
                analyzed_at="2025-01-01",
                clips=clips,
            )
        }
        repo.project = None
        repo.embedding_model = "text-embedding-005"

        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = [1.0, 0.0, 0.0]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]
        mock_client.models.embed_content.return_value = mock_response
        repo._embedding_client = mock_client

        results = repo.find_by_embedding("query", min_duration=5.0)

        assert len(results) == 1
        assert results[0].clip_id == "long"

    def test_respects_max_results_limit(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        clips = [
            VideoClip(
                clip_id=f"clip_{i}",
                source_file=Path(f"/fake{i}.mp4"),
                start_time=0,
                end_time=5,
                description=f"Clip {i}",
                embedding=[float(i) / 10, 0.0, 0.0],
            )
            for i in range(10)
        ]

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {
            "test": VideoIndex(
                source_file=Path("/test.mp4"),
                total_duration=50.0,
                analyzed_at="2025-01-01",
                clips=clips,
            )
        }
        repo.project = None
        repo.embedding_model = "text-embedding-005"

        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = [1.0, 0.0, 0.0]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]
        mock_client.models.embed_content.return_value = mock_response
        repo._embedding_client = mock_client

        results = repo.find_by_embedding("query", max_results=3)

        assert len(results) == 3

    def test_falls_back_to_all_clips_when_embedding_fails(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        clips = [
            VideoClip(
                clip_id="c1",
                source_file=Path("/fake1.mp4"),
                start_time=0,
                end_time=5,
                description="Clip 1",
                embedding=[1.0, 0.0, 0.0],
            ),
        ]

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {
            "test": VideoIndex(
                source_file=Path("/test.mp4"),
                total_duration=5.0,
                analyzed_at="2025-01-01",
                clips=clips,
            )
        }
        repo.project = None
        repo.embedding_model = "text-embedding-005"

        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = Exception("API error")
        repo._embedding_client = mock_client

        results = repo.find_by_embedding("query", max_results=5)

        assert len(results) == 1


class TestAssetRepositoryGetClipById:
    def test_finds_clip_in_indexes(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        target_clip = VideoClip(
            clip_id="target_123",
            source_file=Path("/fake.mp4"),
            start_time=5,
            end_time=10,
            description="Target clip",
        )

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {
            "video1": VideoIndex(
                source_file=Path("/video1.mp4"),
                total_duration=30.0,
                analyzed_at="2025-01-01",
                clips=[
                    VideoClip(
                        clip_id="other",
                        source_file=Path("/fake.mp4"),
                        start_time=0,
                        end_time=5,
                        description="Other clip",
                    ),
                    target_clip,
                ],
            )
        }

        result = repo.get_clip_by_id("target_123")

        assert result is not None
        assert result.clip_id == "target_123"
        assert result.start_time == 5

    def test_returns_none_when_not_found(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {}

        result = repo.get_clip_by_id("nonexistent")

        assert result is None


class TestAssetRepositoryGetAllClips:
    def test_aggregates_clips_from_all_indexes(self, tmp_path: Path):
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        repo = AssetRepository.__new__(AssetRepository)
        repo.raw_footage_dir = raw_dir
        repo.index_dir = index_dir
        repo._indexes = {
            "video1": VideoIndex(
                source_file=Path("/video1.mp4"),
                total_duration=10.0,
                analyzed_at="2025-01-01",
                clips=[
                    VideoClip(
                        clip_id="c1",
                        source_file=Path("/v1.mp4"),
                        start_time=0,
                        end_time=5,
                        description="Clip 1",
                    )
                ],
            ),
            "video2": VideoIndex(
                source_file=Path("/video2.mp4"),
                total_duration=10.0,
                analyzed_at="2025-01-01",
                clips=[
                    VideoClip(
                        clip_id="c2",
                        source_file=Path("/v2.mp4"),
                        start_time=0,
                        end_time=5,
                        description="Clip 2",
                    ),
                    VideoClip(
                        clip_id="c3",
                        source_file=Path("/v2.mp4"),
                        start_time=5,
                        end_time=10,
                        description="Clip 3",
                    ),
                ],
            ),
        }

        all_clips = repo.get_all_clips()

        assert len(all_clips) == 3
        clip_ids = {c.clip_id for c in all_clips}
        assert clip_ids == {"c1", "c2", "c3"}
