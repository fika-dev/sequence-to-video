import argparse
import sys
from pathlib import Path

from domains.editing.composer import SequenceComposer
from domains.editing.renderer import FFmpegRenderer
from domains.library.analyzer import VideoContentAnalyzer
from domains.library.reference_store import (
    GCSSyncManager,
    MigrationHelper,
    ReferenceStore,
    SourceType,
)
from domains.library.repository import AssetRepository
from domains.library.selector import FootageSelector
from domains.planning.parser import ScenarioParser
from domains.reviewing.reviewer import review_sequence
from domains.sequencing.generator import SequenceGenerator
from domains.studio.image_generator import ImageGenerator
from domains.studio.text_renderer import TextAnimationRenderer
from domains.studio.tts_generator import TTSGenerator
from domains.studio.video_generator import VideoGenerator
from infrastructure.cache import AssetCache
from infrastructure.config import Config, load_config


def create_video_from_sequence(
    sequence_data: str | Path | dict,
    config: Config | None = None,
    output_filename: str | None = None,
    use_cache: bool = True,
    verbose: bool = False,
) -> Path:
    if config is None:
        config = load_config()
    config.ensure_directories()

    if verbose:
        print(
            f"Config: locale={config.generation.locale}, context={config.generation.context or '(none)'}"
        )
        print(f"Cache: {'enabled' if use_cache else 'disabled'}")

    cache = AssetCache(cache_dir=config.paths.generated / ".cache") if use_cache else None

    parser = ScenarioParser()

    sequence_file_path: Path | None = None
    if isinstance(sequence_data, dict):
        scenario = parser.parse_dict(sequence_data)
    elif isinstance(sequence_data, Path) or (
        isinstance(sequence_data, str) and Path(sequence_data).exists()
    ):
        sequence_file_path = Path(sequence_data)
        scenario = parser.parse_file(sequence_data)
    else:
        scenario = parser.parse_json(sequence_data)

    tts = TTSGenerator(output_dir=config.paths.generated / "audio", cache=cache)
    image_gen = ImageGenerator(
        output_dir=config.paths.generated / "images",
        project=config.api.google_project_id,
        location="global",
        cache=cache,
        locale=config.generation.locale,
        context=config.generation.context,
    )
    video_gen = VideoGenerator(
        output_dir=config.paths.generated / "videos",
        project=config.api.google_project_id,
        location="us-central1",
        cache=cache,
    )
    text_renderer = TextAnimationRenderer(
        output_dir=config.paths.generated / "text_overlays",
        cache=cache,
        max_font_size=config.generation.text_overlay.max_font_size,
    )

    analyzer = VideoContentAnalyzer(
        project=config.api.google_project_id,
        location=config.api.google_location,
        gcs_bucket=config.api.gcs_bucket,
    )
    asset_repo = AssetRepository(
        raw_footage_dir=config.paths.raw_footage,
        index_dir=config.paths.library_index,
        analyzer=analyzer,
        project=config.api.google_project_id,
    )

    footage_selector = FootageSelector(
        project=config.api.google_project_id,
        location="global",
    )

    renderer = FFmpegRenderer(output_dir=config.paths.review_output)

    composer = SequenceComposer(
        tts_generator=tts,
        image_generator=image_gen,
        video_generator=video_gen,
        text_renderer=text_renderer,
        asset_repository=asset_repo,
        footage_selector=footage_selector,
        renderer=renderer,
        verbose=verbose,
        max_tts_speed=config.generation.tts.max_speed,
        min_tts_speed=config.generation.tts.min_speed,
    )

    output_path, _ = composer.compose(scenario, output_filename)

    if sequence_file_path:
        _save_scenario_to_file(scenario, sequence_file_path)
        if verbose:
            print(f"Sequence updated with selected clips: {sequence_file_path}")

    print(f"\nVideo created: {output_path}")
    return output_path


def _save_scenario_to_file(scenario, file_path: Path) -> None:
    import json

    with open(file_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    for scene in scenario.scenes:
        for orig_scene in original_data.get("scenes", []):
            if orig_scene.get("scene_id") == scene.scene_id:
                if scene.selected_clip_id:
                    orig_scene["selected_clip_id"] = scene.selected_clip_id
                if scene.prepared:
                    orig_scene["prepared"] = scene.prepared.model_dump(exclude_none=True)
                break

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(original_data, f, ensure_ascii=False, indent=2)


def rerender_single_scene(
    sequence_data: str | Path | dict,
    scene_id: str,
    config: Config | None = None,
    use_cache: bool = True,
    verbose: bool = False,
) -> Path:
    if config is None:
        config = load_config()
    config.ensure_directories()

    cache = AssetCache(cache_dir=config.paths.generated / ".cache") if use_cache else None

    parser = ScenarioParser()
    sequence_file_path: Path | None = None
    if isinstance(sequence_data, dict):
        scenario = parser.parse_dict(sequence_data)
    elif isinstance(sequence_data, Path) or (
        isinstance(sequence_data, str) and Path(sequence_data).exists()
    ):
        sequence_file_path = Path(sequence_data)
        scenario = parser.parse_file(sequence_data)
    else:
        scenario = parser.parse_json(sequence_data)

    tts = TTSGenerator(output_dir=config.paths.generated / "audio", cache=cache)
    image_gen = ImageGenerator(
        output_dir=config.paths.generated / "images",
        project=config.api.google_project_id,
        location="global",
        cache=cache,
        locale=config.generation.locale,
        context=config.generation.context,
    )
    video_gen = VideoGenerator(
        output_dir=config.paths.generated / "videos",
        project=config.api.google_project_id,
        location="us-central1",
        cache=cache,
    )
    text_renderer = TextAnimationRenderer(
        output_dir=config.paths.generated / "text_overlays",
        cache=cache,
        max_font_size=config.generation.text_overlay.max_font_size,
    )

    analyzer = VideoContentAnalyzer(
        project=config.api.google_project_id,
        location=config.api.google_location,
        gcs_bucket=config.api.gcs_bucket,
    )
    asset_repo = AssetRepository(
        raw_footage_dir=config.paths.raw_footage,
        index_dir=config.paths.library_index,
        analyzer=analyzer,
        project=config.api.google_project_id,
    )

    footage_selector = FootageSelector(
        project=config.api.google_project_id,
        location="global",
    )

    renderer = FFmpegRenderer(output_dir=config.paths.review_output)

    composer = SequenceComposer(
        tts_generator=tts,
        image_generator=image_gen,
        video_generator=video_gen,
        text_renderer=text_renderer,
        asset_repository=asset_repo,
        footage_selector=footage_selector,
        renderer=renderer,
        verbose=verbose,
        max_tts_speed=config.generation.tts.max_speed,
        min_tts_speed=config.generation.tts.min_speed,
    )

    output_path, new_clip_id = composer.recompose_scene(scenario, scene_id)

    if sequence_file_path:
        _save_scenario_to_file(scenario, sequence_file_path)
        if verbose:
            if new_clip_id:
                print(f"Sequence updated: {scene_id} -> {new_clip_id}")
            print(f"Prepared assets saved to: {sequence_file_path}")

    print(f"\nScene re-rendered: {output_path}")
    return output_path


def reassemble_video(
    sequence_data: str | Path | dict,
    config: Config | None = None,
    output_filename: str | None = None,
    verbose: bool = False,
    use_cache: bool = True,
) -> Path:
    if config is None:
        config = load_config()
    config.ensure_directories()

    parser = ScenarioParser()
    sequence_file_path: Path | None = None
    if isinstance(sequence_data, dict):
        scenario = parser.parse_dict(sequence_data)
    elif isinstance(sequence_data, Path) or (
        isinstance(sequence_data, str) and Path(sequence_data).exists()
    ):
        sequence_file_path = Path(sequence_data)
        scenario = parser.parse_file(sequence_data)
    else:
        scenario = parser.parse_json(sequence_data)

    renderer = FFmpegRenderer(output_dir=config.paths.review_output)
    scenes_dir = config.paths.review_output / scenario.project_id / "scenes"

    scene_ids = [scene.scene_id for scene in scenario.scenes]
    missing_scene_ids = []
    for scene_id in scene_ids:
        scene_path = scenes_dir / f"{scene_id}.mp4"
        if not scene_path.exists():
            missing_scene_ids.append(scene_id)

    if missing_scene_ids:
        if verbose:
            print(f"Missing {len(missing_scene_ids)} scene(s): {missing_scene_ids}")
            print("Rendering missing scenes...")

        composer = _create_composer_for_reassemble(config, renderer, use_cache, verbose)

        for scene_id in missing_scene_ids:
            scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
            if scene:
                if verbose:
                    print(f"\n  Rendering scene: {scene_id}")
                output_path, _ = composer.recompose_scene(scenario, scene_id)
                if not output_path.exists():
                    raise RuntimeError(
                        f"Failed to render scene {scene_id}: file not created at {output_path}"
                    )
                if verbose:
                    print(f"  Created: {output_path}")

        if sequence_file_path:
            _save_scenario_to_file(scenario, sequence_file_path)

    if verbose:
        print(f"\nReassembling {len(scene_ids)} scenes for project: {scenario.project_id}")

    output_path = renderer.reassemble_from_scene_ids(
        project_id=scenario.project_id,
        scene_ids=scene_ids,
        output_filename=output_filename,
    )
    print(f"\nVideo reassembled: {output_path}")
    return output_path


def _create_composer_for_reassemble(
    config: Config,
    renderer: FFmpegRenderer,
    use_cache: bool,
    verbose: bool,
) -> SequenceComposer:
    cache = AssetCache(cache_dir=config.paths.generated / ".cache") if use_cache else None

    tts = TTSGenerator(output_dir=config.paths.generated / "audio", cache=cache)
    image_gen = ImageGenerator(
        output_dir=config.paths.generated / "images",
        project=config.api.google_project_id,
        location="global",
        cache=cache,
        locale=config.generation.locale,
        context=config.generation.context,
    )
    video_gen = VideoGenerator(
        output_dir=config.paths.generated / "videos",
        project=config.api.google_project_id,
        location="us-central1",
        cache=cache,
    )
    text_renderer = TextAnimationRenderer(
        output_dir=config.paths.generated / "text_overlays",
        cache=cache,
        max_font_size=config.generation.text_overlay.max_font_size,
    )

    analyzer = VideoContentAnalyzer(
        project=config.api.google_project_id,
        location=config.api.google_location,
        gcs_bucket=config.api.gcs_bucket,
    )
    asset_repo = AssetRepository(
        raw_footage_dir=config.paths.raw_footage,
        index_dir=config.paths.library_index,
        analyzer=analyzer,
        project=config.api.google_project_id,
    )

    footage_selector = FootageSelector(
        project=config.api.google_project_id,
        location="global",
    )

    return SequenceComposer(
        tts_generator=tts,
        image_generator=image_gen,
        video_generator=video_gen,
        text_renderer=text_renderer,
        asset_repository=asset_repo,
        footage_selector=footage_selector,
        renderer=renderer,
        verbose=verbose,
        max_tts_speed=config.generation.tts.max_speed,
        min_tts_speed=config.generation.tts.min_speed,
    )


def index_single_file(
    file_path: str,
    config: Config | None = None,
    footage_type: str = "generic",
    context_file: str | None = None,
    verbose: bool = False,
) -> None:
    if config is None:
        config = load_config()
    config.ensure_directories()

    product_context = None
    if context_file:
        context_path = Path(context_file)
        if context_path.exists():
            product_context = context_path.read_text(encoding="utf-8").strip()
            if verbose:
                print(f"Loaded context from: {context_file}")

    if verbose:
        print(f"Indexing single file: {file_path}")
        print(f"Footage type: {footage_type}")

    analyzer = VideoContentAnalyzer(
        project=config.api.google_project_id,
        location=config.api.google_location,
        gcs_bucket=config.api.gcs_bucket,
    )

    index = analyzer.analyze_footage(
        file_path,
        footage_type=footage_type,
        product_context=product_context,
        verbose=verbose,
    )
    print(f"\nIndexed: {index.source_file.name}")
    print(f"  Duration: {index.total_duration}s")
    print(f"  Footage type: {index.footage_type}")
    print(f"  Clips: {len(index.clips)}")
    for clip in index.clips:
        print(f"    - {clip.start_time:.1f}s-{clip.end_time:.1f}s: {clip.description[:60]}...")
        if clip.appeal_point:
            print(f"      Appeal: {clip.appeal_point[:50]}...")


def generate_sequence(
    script_path: str,
    config: Config | None = None,
    output_path: str | None = None,
    strategy: str = "default",
    scene_count: int = 10,
    verbose: bool = False,
) -> Path:
    if config is None:
        config = load_config()

    generator = SequenceGenerator(
        project=config.api.google_project_id,
        location="global",
        model="gemini-3-flash-preview",
        strategy=strategy,
        scene_count=scene_count,
    )

    script_file = Path(script_path)
    output_file = Path(output_path) if output_path else script_file.with_suffix(".sequence.json")

    sequence_data, metadata = generator.generate_from_file(
        script_path=script_file,
        output_path=output_file,
        verbose=verbose,
    )

    print(f"\nSequence generated:")
    print(f"  Locale: {metadata.locale}")
    print(f"  Context: {metadata.context}")
    print(f"  Title: {metadata.title}")
    print(f"  Scenes: {len(sequence_data.get('scenes', []))}")
    print(f"  Saved to: {output_file}")

    return output_file


def index_footage(
    config: Config | None = None,
    force: bool = False,
    footage_type: str = "generic",
    context_file: str | None = None,
    verbose: bool = False,
) -> None:
    if config is None:
        config = load_config()
    config.ensure_directories()

    product_context = None
    if context_file:
        context_path = Path(context_file)
        if context_path.exists():
            product_context = context_path.read_text(encoding="utf-8").strip()
            if verbose:
                print(f"Loaded context from: {context_file}")

    if verbose:
        print(f"Project: {config.api.google_project_id}")
        print(f"Location: {config.api.google_location}")
        print(f"GCS Bucket: {config.api.gcs_bucket}")
        print(f"Raw footage dir: {config.paths.raw_footage}")
        print(f"Index dir: {config.paths.library_index}")
        print(f"Footage type: {footage_type}")
        print()

    analyzer = VideoContentAnalyzer(
        project=config.api.google_project_id,
        location=config.api.google_location,
        gcs_bucket=config.api.gcs_bucket,
    )
    asset_repo = AssetRepository(
        raw_footage_dir=config.paths.raw_footage,
        index_dir=config.paths.library_index,
        analyzer=analyzer,
    )

    indexes = asset_repo.index_all(
        force=force,
        footage_type=footage_type,
        product_context=product_context,
        verbose=verbose,
    )
    print(f"\nIndexed {len(indexes)} video files")
    for idx in indexes:
        print(f"  - {idx.source_file.name}: {len(idx.clips)} clips")


def regenerate_embeddings(
    config: Config | None = None,
    verbose: bool = False,
) -> None:
    if config is None:
        config = load_config()
    config.ensure_directories()

    if verbose:
        print(f"Regenerating embeddings for existing indexes...")
        print(f"Index dir: {config.paths.library_index}")
        print()

    asset_repo = AssetRepository(
        raw_footage_dir=config.paths.raw_footage,
        index_dir=config.paths.library_index,
        project=config.api.google_project_id,
    )

    updated = asset_repo.regenerate_embeddings(verbose=verbose)
    print(f"\nGenerated {updated} embeddings")


def review_sequence_cmd(
    sequence_path: str,
    output_path: str | None = None,
    config: Config | None = None,
    with_references: bool = False,
    with_visuals: bool = True,
    verbose: bool = False,
) -> Path:
    if config is None:
        config = load_config()

    sequence_file = Path(sequence_path)
    if output_path is None:
        output_path = str(sequence_file.with_suffix(".review.json"))

    review = review_sequence(
        sequence_path=sequence_file,
        output_path=output_path,
        project=config.api.google_project_id,
        with_references=with_references,
        with_visuals=with_visuals,
        verbose=verbose,
    )

    print(f"\nSequence Review:")
    print(f"  Overall Score: {review.persuasion_score.overall}/10")
    print(f"  - Attention: {review.persuasion_score.attention}/10")
    print(f"  - Branding: {review.persuasion_score.branding}/10")
    print(f"  - Connection: {review.persuasion_score.connection}/10")
    print(f"  - Direction: {review.persuasion_score.direction}/10")
    print(f"  - Problem Clarity: {review.persuasion_score.problem_clarity}/10")
    print(f"  - Proof Strength: {review.persuasion_score.proof_strength}/10")
    print(f"  - Pacing: {review.persuasion_score.pacing}/10")
    print(f"\n  Reasoning: {review.persuasion_score.reasoning}")

    if review.deterministic_issues:
        print(f"\n  Deterministic Issues ({len(review.deterministic_issues)}):")
        for issue in review.deterministic_issues:
            print(f"    - {issue}")

    if review.visual_fixes:
        print(f"\n  Visual Fixes ({len(review.visual_fixes)}):")
        for fix in review.visual_fixes[:3]:
            print(f"    - [{fix.severity}] {fix.scene_id}: {fix.issue}")

    if review.script_fixes:
        print(f"\n  Script Fixes ({len(review.script_fixes)}):")
        for fix in review.script_fixes[:3]:
            print(f"    - {fix.scene_id}: {fix.issue}")

    if review.flow_fixes:
        print(f"\n  Flow Fixes ({len(review.flow_fixes)}):")
        for fix in review.flow_fixes[:3]:
            print(f"    - {fix.issue.issue_type}: {fix.suggestion[:60]}...")

    if review.action_items:
        print(f"\n  Top Action Items:")
        for item in review.action_items[:5]:
            scene_info = f"[{item.scene_id}] " if item.scene_id else ""
            print(f"    {item.priority}. {scene_info}{item.action}")

    print(f"\n  Review saved to: {output_path}")

    return Path(output_path)


def reference_download(
    links_file: str,
    title: str,
    domain: str,
    source: str = "facebook",
    tags: list[str] | None = None,
    config: Config | None = None,
    verbose: bool = False,
) -> None:
    import subprocess
    import json as json_module
    from urllib.parse import parse_qs, urlparse

    if config is None:
        config = load_config()

    refs_dir = Path("assets/references")
    store = ReferenceStore(refs_dir)

    source_type: SourceType = "facebook" if source == "facebook" else "youtube"
    collection = store.create_collection(
        title=title,
        domain=domain,
        source_type=source_type,
        tags=tags or [],
    )

    if verbose:
        print(f"Created collection: {collection.id}")
        print(f"  Title: {collection.title}")
        print(f"  Domain: {collection.domain}")
        print(f"  Source: {collection.source_type}")

    links_path = Path(links_file)
    if not links_path.exists():
        print(f"Error: Links file not found: {links_file}")
        return

    links = []
    with open(links_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)

    if verbose:
        print(f"\nFound {len(links)} links to download")

    collection_dir = store.get_collection_path(collection.id)
    source_links_path = collection_dir / "source_links.txt"
    with open(source_links_path, "w", encoding="utf-8") as f:
        f.write(f"# Source: {links_file}\n")
        for link in links:
            f.write(f"{link}\n")

    success_count = 0
    fail_count = 0

    yt_dlp_cmd = "yt-dlp-fb" if source == "facebook" else "yt-dlp"

    for i, url in enumerate(links, 1):
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if source == "facebook" and "id" in params:
                source_id = params["id"][0]
            elif source == "youtube":
                source_id = parsed.path.split("/")[-1]
            else:
                source_id = url.split("/")[-1].split("?")[0]

            if verbose:
                print(f"\n[{i}/{len(links)}] Downloading {source_id}...")

            metadata_cmd = [yt_dlp_cmd, "-J", url]
            proc = subprocess.run(metadata_cmd, capture_output=True, text=True, timeout=60)

            if proc.returncode != 0 or not proc.stdout:
                print(f"  [FAIL] Could not fetch metadata")
                fail_count += 1
                continue

            metadata = json_module.loads(proc.stdout)
            original_title = metadata.get("title", "")

            item = store.add_item(
                collection_id=collection.id,
                source_id=source_id,
                original_title=original_title,
            )

            item_dir = store.get_item_path(collection.id, item.reference_id)

            download_cmd = [
                yt_dlp_cmd,
                "--no-warnings",
                "-o", str(item_dir / "video.%(ext)s"),
                "--write-thumbnail",
                "-o", f"thumbnail:{item_dir}/thumbnail.%(ext)s",
                url,
            ]

            proc = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)

            if proc.returncode != 0:
                print(f"  [FAIL] Download failed")
                fail_count += 1
                continue

            store._write_json_atomic(item_dir / "source_meta.json", metadata)

            for f in item_dir.iterdir():
                if f.name.startswith("video.") and f.suffix != ".mp4":
                    f.rename(item_dir / "video.mp4")
                    break

            success_count += 1
            if verbose:
                print(f"  [OK] {original_title[:50]}...")

        except Exception as e:
            print(f"  [FAIL] {e}")
            fail_count += 1

    print(f"\nDownload complete: {success_count} success, {fail_count} failed")
    print(f"Collection: {collection.id} ({collection.to_slug()})")


def reference_analyze(
    collection_id: str,
    config: Config | None = None,
    force: bool = False,
    verbose: bool = False,
) -> None:
    from domains.library.reference_analyzer import ReferenceAdAnalyzer
    import numpy as np

    if config is None:
        config = load_config()

    refs_dir = Path("assets/references")
    store = ReferenceStore(refs_dir)

    collection = store.get_collection(collection_id)
    if collection is None:
        for col in store.list_collections():
            full_col = store.get_collection(col.id)
            if full_col and (col.title == collection_id or full_col.to_slug() == collection_id):
                collection = full_col
                collection_id = col.id
                break

    if collection is None:
        print(f"Error: Collection not found: {collection_id}")
        return

    if verbose:
        print(f"Analyzing collection: {collection.title}")
        print(f"  ID: {collection.id}")
        print(f"  Domain: {collection.domain}")

    analyzer = ReferenceAdAnalyzer(
        project=config.api.google_project_id,
        gcs_bucket=config.api.gcs_bucket,
    )

    items = store.list_items(collection_id)
    items_to_analyze = [
        item for item in items
        if force or item.status != "analyzed"
    ]

    if not items_to_analyze:
        print("No items to analyze")
        return

    if verbose:
        print(f"\nAnalyzing {len(items_to_analyze)} items...")

    success_count = 0
    fail_count = 0

    for i, item in enumerate(items_to_analyze, 1):
        item_dir = store.get_item_path(collection_id, item.reference_id)
        video_path = store.get_video_path(collection_id, item.reference_id)

        if not video_path.exists():
            for ext in [".mov", ".webm", ".mkv"]:
                alt_path = item_dir / f"video{ext}"
                if alt_path.exists():
                    video_path = alt_path
                    break

        if not video_path.exists():
            if verbose:
                print(f"[{i}/{len(items_to_analyze)}] [SKIP] No video: {item.reference_id}")
            continue

        try:
            if verbose:
                print(f"[{i}/{len(items_to_analyze)}] Analyzing {item.reference_id}...")

            source_meta = None
            source_meta_path = item_dir / "source_meta.json"
            if source_meta_path.exists():
                import json as json_module
                with open(source_meta_path, encoding="utf-8") as f:
                    source_meta = json_module.load(f)

            analysis = analyzer.analyze_reference_ad(
                video_path=video_path,
                ad_id=item.source_id,
                fb_metadata=source_meta,
                verbose=verbose,
            )

            analysis = analyzer.generate_embeddings(analysis)

            analysis_dict = analysis.model_dump(mode="json")
            analysis_dict["source_file"] = str(video_path)
            store._write_json_atomic(item_dir / "analysis.json", analysis_dict)

            if analysis.ad_fingerprint_embedding:
                np.save(item_dir / "fingerprint.npy", np.array(analysis.ad_fingerprint_embedding))

            for beat in analysis.beats:
                if beat.embedding:
                    np.save(item_dir / f"{beat.beat_id}.npy", np.array(beat.embedding))

            from datetime import datetime
            store.update_item_status(
                collection_id,
                item.reference_id,
                status="analyzed",
                analyzed_at=datetime.now().isoformat(),
            )

            success_count += 1
            if verbose:
                print(f"  -> {analysis.framework}, {len(analysis.beats)} beats")

        except Exception as e:
            fail_count += 1
            store.update_item_status(collection_id, item.reference_id, status="failed")
            if verbose:
                print(f"  [FAIL] {e}")

    print(f"\nAnalysis complete: {success_count} success, {fail_count} failed")


def reference_list(
    domain: str | None = None,
    verbose: bool = False,
) -> None:
    refs_dir = Path("assets/references")

    if not refs_dir.exists():
        print("No references directory found")
        return

    store = ReferenceStore(refs_dir)
    collections = store.list_collections(domain=domain)

    if not collections:
        print("No collections found")
        return

    print(f"Found {len(collections)} collection(s):\n")

    for col in collections:
        print(f"  {col.id}")
        print(f"    Title: {col.title}")
        print(f"    Domain: {col.domain}")
        print(f"    Source: {col.source_type}")
        print(f"    Items: {col.item_count} ({col.analyzed_count} analyzed)")
        if col.gcs_synced:
            print(f"    GCS: synced")
        print()


def reference_sync(
    push: bool = False,
    pull: bool = False,
    config: Config | None = None,
    verbose: bool = False,
) -> None:
    from google.cloud import storage

    if config is None:
        config = load_config()

    if not config.api.gcs_bucket:
        print("Error: GCS_BUCKET not configured")
        return

    refs_dir = Path("assets/references")
    store = ReferenceStore(refs_dir)

    try:
        storage_client = storage.Client(project=config.api.google_project_id)
    except Exception as e:
        print(f"Error: Could not create storage client: {e}")
        return

    sync_manager = GCSSyncManager(
        store=store,
        storage_client=storage_client,
        bucket_name=config.api.gcs_bucket,
    )

    if push or (not push and not pull):
        if verbose:
            print(f"Pushing to GCS bucket: {config.api.gcs_bucket}")

        result = sync_manager.push()

        if result.success:
            print(f"Push complete: {result.files_uploaded} files uploaded")
        else:
            print(f"Push failed: {result.files_uploaded} uploaded, {result.files_failed} failed")
            if result.errors:
                for error in result.errors[:5]:
                    print(f"  - {error}")

    if pull:
        print("Pull not yet implemented (push-only for now)")


def reference_migrate(
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    legacy_refs_dir = Path("assets/references")
    legacy_index_dir = Path("assets/reference_index")
    new_refs_dir = Path("assets/references_new")

    helper = MigrationHelper(
        legacy_refs_dir=legacy_refs_dir,
        legacy_index_dir=legacy_index_dir,
        new_refs_dir=new_refs_dir,
    )

    if not helper.needs_migration():
        print("No legacy data to migrate")
        return

    if verbose:
        print("Migrating legacy reference data...")
        print(f"  From: {legacy_refs_dir} + {legacy_index_dir}")
        print(f"  To: {new_refs_dir}")

    if dry_run:
        print("\n[DRY RUN] Would migrate:")

    result = helper.migrate(dry_run=dry_run)

    if result.dry_run:
        print(f"  {result.items_migrated} items would be migrated")
    elif result.success:
        print(f"\nMigration complete!")
        print(f"  Collection: {result.collection_id}")
        print(f"  Items migrated: {result.items_migrated}")
        print(f"\nNext steps:")
        print(f"  1. Verify new structure: ls {new_refs_dir}/collections/")
        print(f"  2. If OK, replace old: mv {legacy_refs_dir} {legacy_refs_dir}.bak && mv {new_refs_dir} {legacy_refs_dir}")
        print(f"  3. Remove backup: rm -rf {legacy_refs_dir}.bak {legacy_index_dir}")
    else:
        print(f"\nMigration failed: {result.items_migrated} migrated, {result.items_failed} failed")
        if result.errors:
            for error in result.errors[:10]:
                print(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(description="Generate videos from sequence planning data")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    render_parser = subparsers.add_parser("render", help="Render video from sequence JSON")
    render_parser.add_argument("input", help="Path to sequence JSON file")
    render_parser.add_argument("-o", "--output", help="Output filename")
    render_parser.add_argument("--env", help="Path to .env file")
    render_parser.add_argument("--no-cache", action="store_true", help="Disable asset caching")
    render_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    index_parser = subparsers.add_parser("index", help="Index raw footage videos")
    index_parser.add_argument("file", nargs="?", help="Single file to index (optional)")
    index_parser.add_argument("--force", action="store_true", help="Re-index all videos")
    index_parser.add_argument(
        "--type",
        dest="footage_type",
        default="generic",
        choices=["generic", "product_ugc"],
        help="Footage type for analysis (default: generic)",
    )
    index_parser.add_argument(
        "--context", dest="context_file", help="Path to product context file (for product_ugc type)"
    )
    index_parser.add_argument("--env", help="Path to .env file")
    index_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    sequence_parser = subparsers.add_parser("sequence", help="Generate sequence JSON from script")
    sequence_parser.add_argument("script", help="Path to script/scenario text file")
    sequence_parser.add_argument("-o", "--output", help="Output JSON path")
    sequence_parser.add_argument(
        "--strategy",
        default="default",
        choices=["default", "footage_aware", "appeal_first", "reference_guided"],
        help="Sequencing strategy (default: default)",
    )
    sequence_parser.add_argument(
        "--scene-count",
        type=int,
        default=10,
        help="Target number of scenes (default: 10)",
    )
    sequence_parser.add_argument("--env", help="Path to .env file")
    sequence_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    rerender_parser = subparsers.add_parser("rerender-scene", help="Re-render a single scene")
    rerender_parser.add_argument("input", help="Path to sequence JSON file")
    rerender_parser.add_argument("scene_id", help="Scene ID to re-render")
    rerender_parser.add_argument("--env", help="Path to .env file")
    rerender_parser.add_argument("--no-cache", action="store_true", help="Disable asset caching")
    rerender_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    reassemble_parser = subparsers.add_parser(
        "reassemble", help="Reassemble video from existing scene files"
    )
    reassemble_parser.add_argument("input", help="Path to sequence JSON file")
    reassemble_parser.add_argument("-o", "--output", help="Output filename")
    reassemble_parser.add_argument("--env", help="Path to .env file")
    reassemble_parser.add_argument(
        "--no-cache", action="store_true", help="Disable asset caching for missing scenes"
    )
    reassemble_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    embed_parser = subparsers.add_parser("embed", help="Generate embeddings for existing indexes")
    embed_parser.add_argument("--env", help="Path to .env file")
    embed_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    review_parser = subparsers.add_parser("review", help="Review sequence for persuasion effectiveness")
    review_parser.add_argument("input", help="Path to sequence JSON file")
    review_parser.add_argument("-o", "--output", help="Output review JSON path")
    review_parser.add_argument(
        "--with-references",
        action="store_true",
        help="Include reference ad benchmarks in review",
    )
    review_parser.add_argument(
        "--no-visuals",
        action="store_true",
        help="Skip thumbnail grid generation (text-only review)",
    )
    review_parser.add_argument("--env", help="Path to .env file")
    review_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    viewer_parser = subparsers.add_parser("viewer", help="Launch web viewer for sequence preview")
    viewer_parser.add_argument("input", nargs="?", help="Path to sequence JSON file (optional)")
    viewer_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    viewer_parser.add_argument(
        "--port", type=int, default=8765, help="Port to bind (default: 8765)"
    )

    # Reference management commands
    ref_download_parser = subparsers.add_parser(
        "reference-download", help="Download reference ads from links file"
    )
    ref_download_parser.add_argument("links_file", help="Path to file with ad URLs (one per line)")
    ref_download_parser.add_argument("--title", required=True, help="Collection title")
    ref_download_parser.add_argument(
        "--domain", required=True, help="Domain category (e.g., ads/supplements)"
    )
    ref_download_parser.add_argument(
        "--source",
        default="facebook",
        choices=["facebook", "youtube"],
        help="Source platform (default: facebook)",
    )
    ref_download_parser.add_argument(
        "--tags", nargs="*", help="Tags for the collection"
    )
    ref_download_parser.add_argument("--env", help="Path to .env file")
    ref_download_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    ref_analyze_parser = subparsers.add_parser(
        "reference-analyze", help="Analyze reference ads in a collection"
    )
    ref_analyze_parser.add_argument(
        "collection", help="Collection ID, title, or slug"
    )
    ref_analyze_parser.add_argument(
        "--force", action="store_true", help="Re-analyze already analyzed items"
    )
    ref_analyze_parser.add_argument("--env", help="Path to .env file")
    ref_analyze_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    ref_list_parser = subparsers.add_parser(
        "reference-list", help="List reference collections"
    )
    ref_list_parser.add_argument(
        "--domain", help="Filter by domain (e.g., ads/supplements)"
    )
    ref_list_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    ref_sync_parser = subparsers.add_parser(
        "reference-sync", help="Sync references with GCS"
    )
    ref_sync_parser.add_argument(
        "--push", action="store_true", help="Push local changes to GCS"
    )
    ref_sync_parser.add_argument(
        "--pull", action="store_true", help="Pull changes from GCS (not yet implemented)"
    )
    ref_sync_parser.add_argument("--env", help="Path to .env file")
    ref_sync_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    ref_migrate_parser = subparsers.add_parser(
        "reference-migrate", help="Migrate legacy reference structure"
    )
    ref_migrate_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be migrated without making changes"
    )
    ref_migrate_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.command == "render":
        config = load_config(args.env)
        create_video_from_sequence(
            sequence_data=args.input,
            config=config,
            output_filename=args.output,
            use_cache=not args.no_cache,
            verbose=args.verbose,
        )
    elif args.command == "index":
        config = load_config(args.env)
        if args.file:
            index_single_file(
                args.file,
                config=config,
                footage_type=args.footage_type,
                context_file=args.context_file,
                verbose=args.verbose,
            )
        else:
            index_footage(
                config=config,
                force=args.force,
                footage_type=args.footage_type,
                context_file=args.context_file,
                verbose=args.verbose,
            )
    elif args.command == "sequence":
        config = load_config(args.env)
        generate_sequence(
            script_path=args.script,
            config=config,
            output_path=args.output,
            strategy=args.strategy,
            scene_count=args.scene_count,
            verbose=args.verbose,
        )
    elif args.command == "rerender-scene":
        config = load_config(args.env)
        rerender_single_scene(
            sequence_data=args.input,
            scene_id=args.scene_id,
            config=config,
            use_cache=not args.no_cache,
            verbose=args.verbose,
        )
    elif args.command == "reassemble":
        config = load_config(args.env)
        reassemble_video(
            sequence_data=args.input,
            config=config,
            output_filename=args.output,
            verbose=args.verbose,
            use_cache=not args.no_cache,
        )
    elif args.command == "embed":
        config = load_config(args.env)
        regenerate_embeddings(config=config, verbose=args.verbose)
    elif args.command == "review":
        config = load_config(args.env)
        review_sequence_cmd(
            sequence_path=args.input,
            output_path=args.output,
            config=config,
            with_references=args.with_references,
            with_visuals=not args.no_visuals,
            verbose=args.verbose,
        )
    elif args.command == "viewer":
        from viewer.server import run_viewer

        run_viewer(sequence_path=args.input, host=args.host, port=args.port)
    elif args.command == "reference-download":
        config = load_config(args.env)
        reference_download(
            links_file=args.links_file,
            title=args.title,
            domain=args.domain,
            source=args.source,
            tags=args.tags,
            config=config,
            verbose=args.verbose,
        )
    elif args.command == "reference-analyze":
        config = load_config(args.env)
        reference_analyze(
            collection_id=args.collection,
            config=config,
            force=args.force,
            verbose=args.verbose,
        )
    elif args.command == "reference-list":
        reference_list(domain=args.domain, verbose=args.verbose)
    elif args.command == "reference-sync":
        config = load_config(args.env)
        reference_sync(
            push=args.push,
            pull=args.pull,
            config=config,
            verbose=args.verbose,
        )
    elif args.command == "reference-migrate":
        reference_migrate(dry_run=args.dry_run, verbose=args.verbose)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
