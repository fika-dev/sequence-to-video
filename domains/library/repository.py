import json
import math
from pathlib import Path

from google import genai

from domains.library.analyzer import VideoContentAnalyzer
from domains.library.models import VideoClip, VideoIndex


class AssetRepository:
    def __init__(
        self,
        raw_footage_dir: Path,
        index_dir: Path,
        analyzer: VideoContentAnalyzer | None = None,
        project: str | None = None,
        embedding_model: str = "text-embedding-005",
    ):
        self.raw_footage_dir = Path(raw_footage_dir)
        self.index_dir = Path(index_dir)
        self.analyzer = analyzer
        self._indexes: dict[str, VideoIndex] = {}
        self._load_existing_indexes()

        self.project = project
        self.embedding_model = embedding_model
        self._embedding_client: genai.Client | None = None

    @property
    def embedding_client(self) -> genai.Client:
        if self._embedding_client is None:
            self._embedding_client = genai.Client(
                vertexai=True,
                project=self.project,
                location="global",
            )
        return self._embedding_client

    def _load_existing_indexes(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        for index_file in self.index_dir.glob("*.json"):
            with open(index_file, encoding="utf-8") as f:
                data = json.load(f)
            index = VideoIndex(**data)
            self._indexes[index.source_file.name] = index

    def index_video(
        self,
        video_path: Path,
        force: bool = False,
        footage_type: str = "generic",
        product_context: str | None = None,
        verbose: bool = False,
    ) -> VideoIndex:
        video_path = Path(video_path)

        if not force and video_path.name in self._indexes:
            if verbose:
                print(f"  [SKIP] {video_path.name} (already indexed)")
            return self._indexes[video_path.name]

        if not self.analyzer:
            raise RuntimeError("No analyzer configured for indexing")

        if verbose:
            print(f"  [ANALYZING] {video_path.name}...")

        index = self.analyzer.analyze_footage(
            video_path,
            footage_type=footage_type,
            product_context=product_context,
            verbose=verbose,
        )
        self._save_index(index)
        self._indexes[video_path.name] = index

        if verbose:
            print(f"  [DONE] {video_path.name}: {len(index.clips)} clips found")

        return index

    def index_all(
        self,
        force: bool = False,
        footage_type: str = "generic",
        product_context: str | None = None,
        verbose: bool = False,
    ) -> list[VideoIndex]:
        video_patterns = ["**/*.mp4", "**/*.mov", "**/*.avi", "**/*.mkv", "**/*.webm"]
        indexes = []
        indexed_files: set[Path] = set()

        all_videos = []
        for pattern in video_patterns:
            for video_file in self.raw_footage_dir.glob(pattern):
                if video_file not in indexed_files:
                    indexed_files.add(video_file)
                    all_videos.append(video_file)

        if verbose:
            print(f"Found {len(all_videos)} video files in {self.raw_footage_dir}")
            print(f"Footage type: {footage_type}")

        for i, video_file in enumerate(all_videos, 1):
            if verbose:
                print(f"\n[{i}/{len(all_videos)}] Processing {video_file.name}")
            index = self.index_video(
                video_file,
                force=force,
                footage_type=footage_type,
                product_context=product_context,
                verbose=verbose,
            )
            indexes.append(index)

        return indexes

    def find_clips(
        self,
        query_tags: list[str],
        min_duration: float = 0.0,
        max_results: int = 10,
    ) -> list[VideoClip]:
        all_matches: list[VideoClip] = []

        for index in self._indexes.values():
            matches = index.find_by_tags(query_tags, min_duration)
            all_matches.extend(matches)

        all_matches.sort(key=lambda c: c.duration, reverse=True)
        return all_matches[:max_results]

    def find_by_description(
        self,
        description: str,
        min_duration: float = 0.0,
    ) -> list[VideoClip]:
        keywords = description.lower().split()
        scored_matches: list[tuple[int, VideoClip]] = []

        for index in self._indexes.values():
            for clip in index.clips:
                if clip.duration < min_duration:
                    continue
                clip_desc_lower = clip.description.lower()
                score = sum(1 for kw in keywords if kw in clip_desc_lower)
                if score > 0:
                    scored_matches.append((score, clip))

        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return [clip for _, clip in scored_matches]

    def _save_index(self, index: VideoIndex) -> None:
        index_path = self.index_dir / f"{index.source_file.stem}.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

    def get_all_clips(self) -> list[VideoClip]:
        all_clips = []
        for index in self._indexes.values():
            all_clips.extend(index.clips)
        return all_clips

    def regenerate_embeddings(self, verbose: bool = False) -> int:
        updated_count = 0
        for name, index in self._indexes.items():
            clips_needing_embedding = [c for c in index.clips if not c.embedding]
            if not clips_needing_embedding:
                if verbose:
                    print(f"  [SKIP] {name} - all clips have embeddings")
                continue

            if verbose:
                print(f"  [EMBEDDING] {name} - {len(clips_needing_embedding)} clips...")

            texts = [self._clip_to_text(c) for c in clips_needing_embedding]
            embeddings = self._generate_embeddings_batch(texts)

            for clip, emb in zip(clips_needing_embedding, embeddings):
                clip.embedding = emb

            self._save_index(index)
            updated_count += len(clips_needing_embedding)

            if verbose:
                print(f"  [DONE] {name} - {len(clips_needing_embedding)} embeddings generated")

        return updated_count

    def _clip_to_text(self, clip: VideoClip) -> str:
        parts = [clip.description]
        if clip.appeal_point:
            parts.append(clip.appeal_point)
        if clip.tags:
            parts.append(" ".join(clip.tags))
        return " ".join(parts)

    def _generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self.embedding_client.models.embed_content(
                model=self.embedding_model,
                contents=texts,
            )
            return [emb.values for emb in response.embeddings]
        except Exception:
            return [[] for _ in texts]

    def find_by_embedding(
        self,
        query: str,
        max_results: int = 20,
        min_duration: float = 0.0,
    ) -> list[VideoClip]:
        query_embedding = self._generate_query_embedding(query)
        if not query_embedding:
            return self.get_all_clips()[:max_results]

        scored_clips: list[tuple[float, VideoClip]] = []
        for index in self._indexes.values():
            for clip in index.clips:
                if clip.duration < min_duration:
                    continue
                if not clip.embedding:
                    continue
                similarity = self._cosine_similarity(query_embedding, clip.embedding)
                scored_clips.append((similarity, clip))

        scored_clips.sort(key=lambda x: x[0], reverse=True)
        return [clip for _, clip in scored_clips[:max_results]]

    def _generate_query_embedding(self, text: str) -> list[float]:
        try:
            response = self.embedding_client.models.embed_content(
                model=self.embedding_model,
                contents=[text],
            )
            return response.embeddings[0].values
        except Exception:
            return []

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
