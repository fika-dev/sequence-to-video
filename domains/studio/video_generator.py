import time
import uuid
from pathlib import Path

from google import genai
from google.cloud import storage
from google.genai import types

from domains.studio.models import VideoAsset
from infrastructure.cache import AssetCache
from infrastructure.metadata import MetadataManager


class VideoGenerator:
    def __init__(
        self,
        output_dir: Path | None = None,
        project: str | None = None,
        location: str = "us-central1",
        gcs_bucket: str | None = None,
        cache: AssetCache | None = None,
        metadata_manager: MetadataManager | None = None,
    ):
        self.project = project
        self.location = location
        self.gcs_bucket = gcs_bucket
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self.storage_client = storage.Client(project=project) if gcs_bucket else None
        self.output_dir = Path(output_dir) if output_dir else Path("assets/generated/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache = cache
        self.metadata = metadata_manager or MetadataManager()

    def generate(
        self,
        prompt: str,
        width: int = 720,
        height: int = 1280,
        duration: int | None = None,
        model: str = "veo-3.1-generate-preview",
        output_filename: str | None = None,
        poll_interval: int = 10,
        timeout: int = 600,
    ) -> VideoAsset:
        cache_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "model": model,
        }

        if self.cache:
            cached_path = self.cache.get("video", cache_params)
            if cached_path:
                metadata = self.cache.get_metadata("video", cache_params)
                return VideoAsset(
                    file_path=cached_path,
                    duration=metadata.get("duration", 8.0) if metadata else 8.0,
                    width=width,
                    height=height,
                    fps=24.0,
                    prompt=prompt,
                )

        if not self.gcs_bucket:
            raise RuntimeError("GCS bucket is required for Vertex AI video generation")

        gcs_output_prefix = f"gs://{self.gcs_bucket}/generated_videos/{uuid.uuid4().hex}"

        if duration is not None:
            config = types.GenerateVideosConfig(
                aspect_ratio=self._get_aspect_ratio(width, height),
                output_gcs_uri=gcs_output_prefix,
                duration_seconds=duration,
            )
        else:
            config = types.GenerateVideosConfig(
                aspect_ratio=self._get_aspect_ratio(width, height),
                output_gcs_uri=gcs_output_prefix,
            )

        operation = self.client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=config,
        )

        start_time = time.time()
        while not operation.done:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Video generation timed out after {timeout}s")
            time.sleep(poll_interval)
            operation = self.client.operations.get(operation)

        if hasattr(operation, "error") and operation.error:
            raise RuntimeError(f"Video generation failed: {operation.error}")

        result = operation.result
        if not result or not result.generated_videos:
            raise RuntimeError(f"No video generated for prompt: {prompt}")

        generated_video = result.generated_videos[0]
        if not generated_video.video or not generated_video.video.uri:
            raise RuntimeError(f"Generated video has no URI for prompt: {prompt}")

        gcs_uri = generated_video.video.uri

        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"vid_{hash(prompt) & 0xFFFFFFFF:08x}.mp4"

        self._download_from_gcs(gcs_uri, output_path)

        actual_duration = float(duration) if duration else 8.0

        if self.cache:
            self.cache.put("video", cache_params, output_path, metadata={"duration": actual_duration})

        self.metadata.save(
            asset_type="video",
            asset_path=output_path,
            prompt=prompt,
            params={
                "width": width,
                "height": height,
                "duration": actual_duration,
                "model": model,
            },
        )

        return VideoAsset(
            file_path=output_path,
            duration=actual_duration,
            width=width,
            height=height,
            fps=24.0,
            prompt=prompt,
        )

    def _download_from_gcs(self, gcs_uri: str, output_path: Path) -> None:
        if not self.storage_client:
            raise RuntimeError("Storage client not initialized")

        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: {gcs_uri}")

        path_without_prefix = gcs_uri[5:]
        bucket_name, blob_name = path_without_prefix.split("/", 1)

        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(str(output_path))

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        ratio = width / height
        if ratio < 0.7:
            return "9:16"
        if ratio > 1.4:
            return "16:9"
        return "1:1"
