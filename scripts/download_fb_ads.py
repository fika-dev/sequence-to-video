#!/usr/bin/env python3
"""
Facebook Ads Library Downloader - uses yt-dlp-fb (PR branch with rd_challenge bypass).

Usage:
    python scripts/download_fb_ads.py links.txt
    python scripts/download_fb_ads.py links.txt -o assets/references -w 4
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse


def extract_ad_id(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "id" in params:
            return params["id"][0]
    except Exception:
        pass
    return None


def find_existing_video(ad_dir: Path) -> Optional[Path]:
    for ext in [".mp4", ".mov", ".webm", ".mkv"]:
        video_file = ad_dir / f"video{ext}"
        if video_file.exists():
            return video_file
    return None


def download_ad(url: str, output_dir: Path, verbose: bool = False, skip_existing: bool = True) -> dict:
    ad_id = extract_ad_id(url)
    if not ad_id:
        return {
            "url": url,
            "id": None,
            "status": "failed",
            "error": "Could not extract ad ID from URL",
        }

    ad_dir = output_dir / ad_id
    
    if skip_existing and ad_dir.exists():
        existing_video = find_existing_video(ad_dir)
        if existing_video:
            return {
                "url": url,
                "id": ad_id,
                "status": "skipped",
                "title": None,
                "uploader": None,
                "uploader_id": None,
                "timestamp": None,
                "video_path": str(existing_video),
                "metadata_path": str(ad_dir / "metadata.json") if (ad_dir / "metadata.json").exists() else None,
                "thumbnail_path": None,
                "error": None,
            }
    
    ad_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "url": url,
        "id": ad_id,
        "status": "success",
        "title": None,
        "uploader": None,
        "uploader_id": None,
        "timestamp": None,
        "video_path": None,
        "metadata_path": None,
        "thumbnail_path": None,
        "error": None,
    }

    try:
        metadata_cmd = ["yt-dlp-fb", "-J", url]
        proc = subprocess.run(metadata_cmd, capture_output=True, text=True, timeout=60)
        
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            if "No video formats found" in stderr:
                result["status"] = "failed"
                result["error"] = "Image-only ad (no video)"
            else:
                result["status"] = "failed"
                result["error"] = stderr or "Failed to fetch metadata"
            return result

        if not proc.stdout or proc.stdout.strip() == "null":
            result["status"] = "failed"
            result["error"] = "Empty response (ad may be expired)"
            return result

        metadata = json.loads(proc.stdout)
        
        if not metadata:
            result["status"] = "failed"
            result["error"] = "Empty metadata (ad may be expired)"
            return result
        
        is_single_video = metadata.get("formats") or metadata.get("url")
        is_carousel_video = metadata.get("entries")
        if not is_single_video and not is_carousel_video:
            result["status"] = "failed"
            result["error"] = "Image-only ad (no video formats)"
            return result
        
        metadata_path = ad_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        result["metadata_path"] = str(metadata_path)
        result["title"] = metadata.get("title")
        result["uploader"] = metadata.get("uploader")
        result["uploader_id"] = metadata.get("uploader_id")
        result["timestamp"] = metadata.get("timestamp")
        result["description"] = metadata.get("description", "")[:200]

    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["error"] = "Metadata fetch timeout"
        return result
    except json.JSONDecodeError as e:
        result["status"] = "failed"
        result["error"] = f"Invalid JSON response: {e}"
        return result
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        return result

    try:
        download_cmd = [
            "yt-dlp-fb",
            "--no-warnings",
            "-o", str(ad_dir / "video.%(ext)s"),
            "--write-thumbnail",
            "-o", f"thumbnail:{ad_dir}/thumbnail.%(ext)s",
            "--convert-thumbnails", "jpg",
            url,
        ]
        
        if verbose:
            print(f"  [{ad_id}] Downloading video...")
        
        proc = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)
        
        if proc.returncode != 0:
            result["status"] = "partial"
            result["error"] = proc.stderr.strip() or "Failed to download video"
        else:
            for f in ad_dir.iterdir():
                if f.name.startswith("video."):
                    result["video_path"] = str(f)
                elif f.name.startswith("thumbnail."):
                    result["thumbnail_path"] = str(f)

    except subprocess.TimeoutExpired:
        result["status"] = "partial"
        result["error"] = "Video download timeout"
    except Exception as e:
        result["status"] = "partial"
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Download Facebook Ads Library videos")
    parser.add_argument("links_file", type=Path, help="Text file with one URL per line")
    parser.add_argument("-o", "--output", type=Path, default=Path("assets/references"), help="Output directory")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Parallel downloads (default: 1)")
    parser.add_argument("-d", "--delay", type=float, default=5.0, help="Delay between downloads in seconds (default: 5)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.links_file.exists():
        print(f"Error: Links file not found: {args.links_file}")
        sys.exit(1)
    
    links = []
    with open(args.links_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)
    
    if not links:
        print("Error: No links found in file")
        sys.exit(1)
    
    print(f"Found {len(links)} links to download")
    
    args.output.mkdir(parents=True, exist_ok=True)
    
    results = []
    failed = []
    
    if args.workers == 1:
        for i, url in enumerate(links, 1):
            try:
                result = download_ad(url, args.output, args.verbose)
                results.append(result)
                
                status_map = {"success": "✓", "partial": "△", "skipped": "⊘", "failed": "✗"}
                status_icon = status_map.get(result["status"], "?")
                if result["status"] == "skipped":
                    display_text = "already downloaded"
                elif result["status"] == "failed":
                    display_text = result.get('error', '')
                else:
                    display_text = result.get('title', '')[:40]
                print(f"[{i}/{len(links)}] {status_icon} {result['id'] or 'unknown'}: {display_text}")
                
                if result["status"] == "failed":
                    failed.append(result)
                
                if i < len(links) and args.delay > 0 and result["status"] != "skipped":
                    time.sleep(args.delay)
                    
            except Exception as e:
                print(f"[{i}/{len(links)}] ✗ {url}: {e}")
                failed.append({
                    "url": url,
                    "id": extract_ad_id(url),
                    "status": "failed",
                    "error": str(e),
                })
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(download_ad, url, args.output, args.verbose): url
                for url in links
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                url = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    status_map = {"success": "✓", "partial": "△", "skipped": "⊘", "failed": "✗"}
                    status_icon = status_map.get(result["status"], "?")
                    if result["status"] == "skipped":
                        display_text = "already downloaded"
                    elif result["status"] == "failed":
                        display_text = result.get('error', '')
                    else:
                        display_text = result.get('title', '')[:40]
                    print(f"[{i}/{len(links)}] {status_icon} {result['id'] or 'unknown'}: {display_text}")
                    
                    if result["status"] == "failed":
                        failed.append(result)
                        
                except Exception as e:
                    print(f"[{i}/{len(links)}] ✗ {url}: {e}")
                    failed.append({
                        "url": url,
                        "id": extract_ad_id(url),
                        "status": "failed",
                        "error": str(e),
                    })
    
    summary_path = args.output / "summary.csv"
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "status", "title", "uploader", "uploader_id", 
            "timestamp", "description", "url", "video_path", "thumbnail_path", "error"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "id": r.get("id"),
                "status": r.get("status"),
                "title": r.get("title"),
                "uploader": r.get("uploader"),
                "uploader_id": r.get("uploader_id"),
                "timestamp": r.get("timestamp"),
                "description": r.get("description", ""),
                "url": r.get("url"),
                "video_path": r.get("video_path"),
                "thumbnail_path": r.get("thumbnail_path"),
                "error": r.get("error"),
            })
    
    print(f"\nSummary saved to: {summary_path}")
    
    if failed:
        failed_path = args.output / "failed.txt"
        with open(failed_path, "w", encoding="utf-8") as f:
            f.write(f"# Failed downloads - {datetime.now().isoformat()}\n")
            for r in failed:
                f.write(f"{r['url']}\t# {r.get('error', 'Unknown error')}\n")
        print(f"Failed links logged to: {failed_path}")
    
    success = sum(1 for r in results if r["status"] == "success")
    partial = sum(1 for r in results if r["status"] == "partial")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    fail = sum(1 for r in results if r["status"] == "failed")
    
    print(f"\nResults: {success} success, {partial} partial, {skipped} skipped, {fail} failed")


if __name__ == "__main__":
    main()
