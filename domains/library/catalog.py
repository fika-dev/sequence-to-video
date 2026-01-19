from collections import defaultdict
from pathlib import Path

from domains.library.models import VideoClip, VideoIndex


class FootageCatalog:
    def __init__(self, indexes: list[VideoIndex]):
        self.indexes = indexes
        self._clips_by_type: dict[str, list[VideoClip]] = defaultdict(list)
        self._build_index()

    def _build_index(self) -> None:
        for index in self.indexes:
            for clip in index.clips:
                content_type = clip.content_type or "uncategorized"
                self._clips_by_type[content_type].append(clip)

    @property
    def all_clips(self) -> list[VideoClip]:
        clips = []
        for index in self.indexes:
            clips.extend(index.clips)
        return clips

    @property
    def content_types(self) -> list[str]:
        return sorted(self._clips_by_type.keys())

    def get_product_context(self) -> str | None:
        for index in self.indexes:
            if index.product_context:
                return index.product_context
        return None

    def to_prompt_format(self) -> str:
        lines = []

        for content_type in self.content_types:
            clips = self._clips_by_type[content_type]
            type_label = self._format_content_type(content_type)
            lines.append(f"### {type_label}")

            for clip in clips:
                lines.append(self._format_clip(clip))

            lines.append("")

        return "\n".join(lines)

    def _format_content_type(self, content_type: str) -> str:
        type_labels = {
            "product_showcase": "Product Showcase",
            "usage_demo": "Usage Demo",
            "unboxing": "Unboxing",
            "before_after": "Before/After",
            "testimonial": "Testimonial",
            "lifestyle": "Lifestyle",
            "texture_detail": "Texture Detail",
            "result_reveal": "Result Reveal",
            "uncategorized": "Other",
        }
        return type_labels.get(content_type, content_type.replace("_", " ").title())

    def _format_clip(self, clip: VideoClip) -> str:
        parts = [f"- [{clip.clip_id}] {clip.duration:.1f}s | {clip.content_type or 'unknown'}"]
        parts.append(f"  {clip.description[:100]}{'...' if len(clip.description) > 100 else ''}")

        if clip.appeal_point:
            appeal_short = (
                clip.appeal_point[:80] + "..." if len(clip.appeal_point) > 80 else clip.appeal_point
            )
            parts.append(f"  Appeal: {appeal_short}")

        if clip.tags:
            tags_str = ", ".join(clip.tags[:6])
            if len(clip.tags) > 6:
                tags_str += f" (+{len(clip.tags) - 6} more)"
            parts.append(f"  Tags: {tags_str}")

        return "\n".join(parts)


def load_catalog_from_directory(index_dir: Path) -> FootageCatalog:
    import json

    indexes = []
    for json_file in index_dir.glob("*.json"):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        index = VideoIndex(
            source_file=Path(data.get("source_file", "")),
            total_duration=data.get("total_duration", 0.0),
            analyzed_at=data.get("analyzed_at", ""),
            clips=[VideoClip(**c) for c in data.get("clips", [])],
            raw_response=data.get("raw_response"),
            footage_type=data.get("footage_type", "generic"),
            product_context=data.get("product_context"),
        )
        indexes.append(index)

    return FootageCatalog(indexes)
