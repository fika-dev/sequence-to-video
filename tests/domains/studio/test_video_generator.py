import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.studio.video_generator import VideoGenerator
from domains.studio.models import VideoAsset


class TestVideoGeneratorGetAspectRatio:
    @pytest.fixture
    def generator(self, tmp_path):
        with patch("domains.studio.video_generator.genai.Client"):
            with patch("domains.studio.video_generator.storage.Client"):
                return VideoGenerator(
                    output_dir=tmp_path, project="test-project", gcs_bucket="test-bucket"
                )

    def test_portrait_returns_9_16(self, generator):
        result = generator._get_aspect_ratio(720, 1280)
        assert result == "9:16"

    def test_landscape_returns_16_9(self, generator):
        result = generator._get_aspect_ratio(1920, 1080)
        assert result == "16:9"

    def test_square_returns_1_1(self, generator):
        result = generator._get_aspect_ratio(1080, 1080)
        assert result == "1:1"


class TestVideoGeneratorDownloadFromGcs:
    def test_raises_on_invalid_gcs_uri(self, tmp_path):
        mock_storage = MagicMock()
        with patch("domains.studio.video_generator.genai.Client"):
            with patch("domains.studio.video_generator.storage.Client") as mock_storage_class:
                mock_storage_class.return_value = mock_storage
                generator = VideoGenerator(
                    output_dir=tmp_path, project="test-project", gcs_bucket="test-bucket"
                )
                with pytest.raises(ValueError, match="Invalid GCS URI"):
                    generator._download_from_gcs("invalid-uri", tmp_path / "output.mp4")

    def test_parses_bucket_and_blob_from_uri(self, tmp_path):
        mock_storage = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        with patch("domains.studio.video_generator.genai.Client"):
            with patch("domains.studio.video_generator.storage.Client") as mock_storage_class:
                mock_storage_class.return_value = mock_storage
                generator = VideoGenerator(
                    output_dir=tmp_path, project="test-project", gcs_bucket="test-bucket"
                )

                output_path = tmp_path / "output.mp4"
                generator._download_from_gcs("gs://my-bucket/path/to/video.mp4", output_path)

                mock_storage.bucket.assert_called_with("my-bucket")
                mock_bucket.blob.assert_called_with("path/to/video.mp4")
                mock_blob.download_to_filename.assert_called_with(str(output_path))

    def test_raises_when_storage_client_not_initialized(self, tmp_path):
        with patch("domains.studio.video_generator.genai.Client"):
            generator = VideoGenerator(output_dir=tmp_path, project="test-project")

            with pytest.raises(RuntimeError, match="Storage client not initialized"):
                generator._download_from_gcs("gs://bucket/blob", tmp_path / "out.mp4")


class TestVideoGeneratorGenerate:
    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.get.return_value = None
        return cache

    def test_returns_cached_result_when_available(self, tmp_path, mock_cache):
        cached_path = tmp_path / "cached.mp4"
        cached_path.touch()
        mock_cache.get.return_value = cached_path
        mock_cache.get_metadata.return_value = {"duration": 5.0}

        with patch("domains.studio.video_generator.genai.Client"):
            with patch("domains.studio.video_generator.storage.Client"):
                generator = VideoGenerator(
                    output_dir=tmp_path,
                    project="test-project",
                    gcs_bucket="test-bucket",
                    cache=mock_cache,
                )

        result = generator.generate("test prompt")

        assert result.file_path == cached_path
        assert result.duration == 5.0
        assert result.prompt == "test prompt"

    def test_raises_without_gcs_bucket(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.video_generator.genai.Client"):
            generator = VideoGenerator(
                output_dir=tmp_path, project="test-project", cache=mock_cache
            )

            with pytest.raises(RuntimeError, match="GCS bucket is required"):
                generator.generate("test prompt")

    def test_polls_for_operation_completion(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.video_generator.genai.Client") as mock_client_class:
            with patch("domains.studio.video_generator.storage.Client") as mock_storage_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_operation = MagicMock()
                mock_operation.done = True
                mock_operation.error = None

                mock_video = MagicMock()
                mock_video.uri = "gs://bucket/video.mp4"
                mock_generated_video = MagicMock()
                mock_generated_video.video = mock_video
                mock_result = MagicMock()
                mock_result.generated_videos = [mock_generated_video]
                mock_operation.result = mock_result

                mock_client.models.generate_videos.return_value = mock_operation

                mock_storage = MagicMock()
                mock_storage_class.return_value = mock_storage
                mock_bucket = MagicMock()
                mock_storage.bucket.return_value = mock_bucket
                mock_blob = MagicMock()
                mock_bucket.blob.return_value = mock_blob

                generator = VideoGenerator(
                    output_dir=tmp_path,
                    project="test-project",
                    gcs_bucket="test-bucket",
                    cache=mock_cache,
                )

                result = generator.generate("test prompt", duration=5)

                mock_client.models.generate_videos.assert_called_once()
                assert isinstance(result, VideoAsset)

    def test_raises_on_timeout(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.video_generator.genai.Client") as mock_client_class:
            with patch("domains.studio.video_generator.storage.Client"):
                with patch("domains.studio.video_generator.time.time") as mock_time:
                    with patch("domains.studio.video_generator.time.sleep"):
                        mock_client = MagicMock()
                        mock_client_class.return_value = mock_client

                        mock_operation = MagicMock()
                        mock_operation.done = False
                        mock_client.models.generate_videos.return_value = mock_operation
                        mock_client.operations.get.return_value = mock_operation

                        mock_time.side_effect = [0, 601]

                        generator = VideoGenerator(
                            output_dir=tmp_path,
                            project="test-project",
                            gcs_bucket="test-bucket",
                            cache=mock_cache,
                        )

                        with pytest.raises(TimeoutError, match="timed out"):
                            generator.generate("test prompt", timeout=600)

    def test_raises_on_operation_error(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.video_generator.genai.Client") as mock_client_class:
            with patch("domains.studio.video_generator.storage.Client"):
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_operation = MagicMock()
                mock_operation.done = True
                mock_operation.error = "Generation failed"
                mock_client.models.generate_videos.return_value = mock_operation

                generator = VideoGenerator(
                    output_dir=tmp_path,
                    project="test-project",
                    gcs_bucket="test-bucket",
                    cache=mock_cache,
                )

                with pytest.raises(RuntimeError, match="Video generation failed"):
                    generator.generate("test prompt")

    def test_raises_on_no_generated_videos(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.video_generator.genai.Client") as mock_client_class:
            with patch("domains.studio.video_generator.storage.Client"):
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_operation = MagicMock()
                mock_operation.done = True
                mock_operation.error = None
                mock_result = MagicMock()
                mock_result.generated_videos = []
                mock_operation.result = mock_result
                mock_client.models.generate_videos.return_value = mock_operation

                generator = VideoGenerator(
                    output_dir=tmp_path,
                    project="test-project",
                    gcs_bucket="test-bucket",
                    cache=mock_cache,
                )

                with pytest.raises(RuntimeError, match="No video generated"):
                    generator.generate("test prompt")

    def test_stores_in_cache_after_generation(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.video_generator.genai.Client") as mock_client_class:
            with patch("domains.studio.video_generator.storage.Client") as mock_storage_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_operation = MagicMock()
                mock_operation.done = True
                mock_operation.error = None
                mock_video = MagicMock()
                mock_video.uri = "gs://bucket/video.mp4"
                mock_generated_video = MagicMock()
                mock_generated_video.video = mock_video
                mock_result = MagicMock()
                mock_result.generated_videos = [mock_generated_video]
                mock_operation.result = mock_result
                mock_client.models.generate_videos.return_value = mock_operation

                mock_storage = MagicMock()
                mock_storage_class.return_value = mock_storage

                generator = VideoGenerator(
                    output_dir=tmp_path,
                    project="test-project",
                    gcs_bucket="test-bucket",
                    cache=mock_cache,
                )
                generator.generate("test prompt")

                mock_cache.put.assert_called_once()
