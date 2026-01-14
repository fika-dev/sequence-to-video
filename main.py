import argparse
import sys
from pathlib import Path

from domains.editing.composer import SequenceComposer
from domains.editing.renderer import FFmpegRenderer
from domains.library.analyzer import VideoContentAnalyzer
from domains.library.repository import AssetRepository
from domains.library.selector import FootageSelector
from domains.planning.parser import ScenarioParser
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

    if sequence_file_path and new_clip_id:
        _update_scene_clip_in_file(sequence_file_path, scene_id, new_clip_id)
        if verbose:
            print(f"Sequence updated: {scene_id} -> {new_clip_id}")

    print(f"\nScene re-rendered: {output_path}")
    return output_path


def _update_scene_clip_in_file(file_path: Path, scene_id: str, clip_id: str) -> None:
    import json

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for scene in data.get("scenes", []):
        if scene.get("scene_id") == scene_id:
            scene["selected_clip_id"] = clip_id
            break

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
                composer.recompose_scene(scenario, scene_id)

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
    verbose: bool = False,
) -> Path:
    if config is None:
        config = load_config()

    generator = SequenceGenerator(
        project=config.api.google_project_id,
        location="global",
        model="gemini-3-flash-preview",
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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
