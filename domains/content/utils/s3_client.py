"""S3 client for retrieving trending keywords and macro trends."""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class S3Client:
    """Client for interacting with AWS S3 to retrieve trending keywords and macro trends."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        base_prefix: str = "analysis_results/trending_topics/"
    ):
        """
        Initialize S3 client.

        Args:
            bucket_name: S3 bucket name (defaults to S3_BUCKET_NAME env var or 'kor-trends-results')
            aws_access_key_id: AWS access key (defaults to AWS_ACCESS_KEY_ID env var)
            aws_secret_access_key: AWS secret key (defaults to AWS_SECRET_ACCESS_KEY env var)
            region_name: AWS region (defaults to us-east-1)
            base_prefix: Base S3 prefix for trending topics (defaults to 'analysis_results/trending_topics/')
        """
        load_dotenv()
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', 'kor-trends-results')
        self.aws_access_key_id = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.base_prefix = base_prefix

        if not BOTO3_AVAILABLE:
            print("⚠️  boto3 not installed. S3 functionality will be limited.")
            self.s3_client = None
            return

        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
        except (NoCredentialsError, Exception) as e:
            print(f"⚠️  Failed to initialize S3 client: {e}")
            self.s3_client = None

    async def get_trending_keywords(
        self,
        date_prefix: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Retrieve trending keywords from S3.

        Args:
            date_prefix: Optional date prefix in format YYYYMMDD_HHMMSS (e.g., "20251228_001801")
                        If None, fetches the most recent file
            limit: Maximum number of keywords to return

        Returns:
            List of dictionaries containing trending keyword data
        """
        if not self.s3_client or not self.bucket_name:
            print("⚠️  S3 client not configured. Returning empty list.")
            return []

        # Find the file to fetch
        if date_prefix is None:
            # Get the most recent file
            available_files = await self.list_available_files()
            if not available_files:
                print("⚠️  No trending topic files found in S3.")
                return []
            # Sort by date/time (newest first) and get the first one
            available_files.sort(reverse=True)
            date_prefix = available_files[0]

        # Construct S3 key path: analysis_results/trending_topics/20251228_001801/...
        # The date_prefix might be a directory or part of filename
        # Try different patterns
        s3_key_patterns = [
            f"{self.base_prefix}{date_prefix}/",  # Directory pattern
            f"{self.base_prefix}{date_prefix}.json",  # Direct file pattern
            f"{self.base_prefix}{date_prefix}_trends.json",  # With suffix
        ]

        # Try to find the JSON file for this date prefix
        s3_key = None
        try:
            # List objects with the date prefix (could be directory or file)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=f"{self.base_prefix}{date_prefix}"
            )

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith('.json'):
                            s3_key = key
                            print(f"✅ Found S3 file: {s3_key}")
                            break
                    if s3_key:
                        break
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code != 'NoSuchKey':  # NoSuchKey is expected if prefix doesn't exist
                print(f"⚠️  Error listing S3 objects with prefix {date_prefix}: {e}")

        # If no file found, try direct patterns (for backward compatibility)
        if s3_key is None:
            for pattern in s3_key_patterns:
                try:
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=pattern)
                    s3_key = pattern
                    print(f"✅ Found S3 file (direct): {s3_key}")
                    break
                except ClientError:
                    continue

        if s3_key is None:
            print(f"⚠️  No JSON file found for date prefix: {date_prefix}")
            print(f"   Searched prefix: {self.base_prefix}{date_prefix}")
            return []

        try:
            # Fetch the file
            print(f"📥 Fetching S3 object: s3://{self.bucket_name}/{s3_key}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            print(f"✅ Successfully loaded JSON from S3 ({len(content)} bytes)")

            # Parse the Korean trends JSON structure
            # Structure: {"analysis_timestamp_kst": ..., "analyzed_post_count": ..., "trends": [...]}
            trends = data.get("trends", [])

            # Extract all keywords from all trends
            all_keywords = []
            seen_keywords = set()

            for trend in trends:
                if isinstance(trend, dict):
                    topic = trend.get("topic", "")
                    keywords = trend.get("keywords", [])
                    trend_report = trend.get("trend_report", "")

                    # Add each keyword with its context
                    for keyword in keywords:
                        if keyword and keyword not in seen_keywords:
                            seen_keywords.add(keyword)
                            all_keywords.append({
                                "keyword": keyword,
                                "topic": topic,
                                "trend_report": trend_report,
                                "category": "kpop" if any(k in topic.lower() for k in ["k팝", "아이돌", "아티스트"]) else "general",
                                "date": date_prefix[:8] if len(date_prefix) >= 8 else None,
                                "analysis_timestamp": data.get("analysis_timestamp_kst")
                            })

                            if len(all_keywords) >= limit:
                                break

                    if len(all_keywords) >= limit:
                        break

            return all_keywords[:limit]

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"⚠️  S3 Bucket '{self.bucket_name}' does not exist.")
                print(f"   Please check your .env file: S3_BUCKET_NAME={self.bucket_name}")
                print(f"   Or ensure the bucket exists and your AWS credentials have access.")
            elif error_code == 'NoSuchKey':
                print(f"⚠️  No trending keywords found at s3://{self.bucket_name}/{s3_key}")
            elif error_code == 'AccessDenied':
                print(f"⚠️  Access denied to bucket '{self.bucket_name}'. Check your AWS credentials.")
            else:
                print(f"⚠️  Error retrieving trending keywords: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️  Error parsing JSON from S3: {e}")
            return []

    async def get_macro_trends(
        self,
        date_prefix: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve macro trends from S3.

        Args:
            date_prefix: Optional date prefix in format YYYYMMDD_HHMMSS (e.g., "20251228_001801")
                        If None, fetches the most recent file

        Returns:
            List of dictionaries containing macro trend data
        """
        if not self.s3_client or not self.bucket_name:
            print("⚠️  S3 client not configured. Returning empty list.")
            return []

        # Find the file to fetch (same logic as get_trending_keywords)
        if date_prefix is None:
            available_files = await self.list_available_files()
            if not available_files:
                print("⚠️  No trending topic files found in S3.")
                return []
            available_files.sort(reverse=True)
            date_prefix = available_files[0]

        # Find the file (reuse same logic as get_trending_keywords)
        s3_key = None
        try:
            # List objects with the date prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=f"{self.base_prefix}{date_prefix}"
            )

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith('.json'):
                            s3_key = key
                            print(f"✅ Found S3 file: {s3_key}")
                            break
                    if s3_key:
                        break
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code != 'NoSuchKey':
                print(f"⚠️  Error listing S3 objects with prefix {date_prefix}: {e}")

        if s3_key is None:
            print(f"⚠️  No JSON file found for date prefix: {date_prefix}")
            return []

        try:
            # Fetch the file
            print(f"📥 Fetching S3 object: s3://{self.bucket_name}/{s3_key}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            print(f"✅ Successfully loaded JSON from S3 ({len(content)} bytes)")

            # Parse the Korean trends JSON structure
            # The "trends" array contains the macro trends
            trends = data.get("trends", [])

            if not trends:
                print(f"⚠️  Warning: JSON file has no 'trends' array. Keys found: {list(data.keys())}")

            # Transform to macro trend format
            macro_trends = []
            for trend in trends:
                if isinstance(trend, dict):
                    macro_trend = {
                        "trend_title": trend.get("topic", ""),
                        "description": trend.get("summary_from_posts", ""),
                        "category": "kpop" if any(k in trend.get("topic", "").lower() for k in ["k팝", "아이돌", "아티스트"]) else "general",
                        "trend_type": "social",  # Can be inferred from content
                        "date": date_prefix[:8] if len(date_prefix) >= 8 else None,
                        "related_keywords": trend.get("keywords", []),
                        "web_search_summary": trend.get("web_search_summary", ""),
                        "trend_report": trend.get("trend_report", ""),
                        "analysis_timestamp": data.get("analysis_timestamp_kst"),
                        "analyzed_post_count": data.get("analyzed_post_count")
                    }
                    macro_trends.append(macro_trend)

            return macro_trends

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"⚠️  S3 Bucket '{self.bucket_name}' does not exist.")
                print(f"   Please check your .env file: S3_BUCKET_NAME={self.bucket_name}")
                print(f"   Or ensure the bucket exists and your AWS credentials have access.")
            elif error_code == 'NoSuchKey':
                print(f"⚠️  No macro trends found at s3://{self.bucket_name}/{s3_key}")
            elif error_code == 'AccessDenied':
                print(f"⚠️  Access denied to bucket '{self.bucket_name}'. Check your AWS credentials.")
            else:
                print(f"⚠️  Error retrieving macro trends: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️  Error parsing JSON from S3: {e}")
            return []

    async def list_available_files(self) -> List[str]:
        """
        List available date prefixes for trending topic files.

        Returns:
            List of date prefixes in YYYYMMDD_HHMMSS format (e.g., ["20251228_001801", ...])
        """
        if not self.s3_client or not self.bucket_name:
            return []

        try:
            date_prefixes = set()

            # First, try with delimiter to get "directories"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.base_prefix,
                Delimiter='/'
            )

            # Check for common prefixes (directories like "20251228_001801/")
            if 'CommonPrefixes' in response:
                for prefix_info in response['CommonPrefixes']:
                    prefix = prefix_info['Prefix']
                    # Extract date prefix from path like "analysis_results/trending_topics/20251228_001801/"
                    relative_path = prefix.replace(self.base_prefix, '').strip('/')
                    if relative_path:
                        # Extract the date prefix (could be "20251228_001801" or "20251228_001801/subfolder")
                        date_prefix = relative_path.split('/')[0]
                        # Validate format: YYYYMMDD_HHMMSS (15 characters with underscore)
                        if len(date_prefix) == 15 and '_' in date_prefix and date_prefix.replace('_', '').isdigit():
                            date_prefixes.add(date_prefix)

            # Also check all objects directly (in case files are directly under base prefix)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.base_prefix
            )

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith('.json'):
                            # Extract from various path patterns:
                            # - analysis_results/trending_topics/20251228_001801/file.json
                            # - analysis_results/trending_topics/20251228_001801.json
                            relative_key = key.replace(self.base_prefix, '').strip('/')
                            if relative_key:
                                parts = relative_key.split('/')
                                # First part should be the date prefix
                                potential_prefix = parts[0].replace('.json', '')  # Remove .json if it's a direct file

                                # Validate format: YYYYMMDD_HHMMSS
                                if len(potential_prefix) == 15 and '_' in potential_prefix and potential_prefix.replace('_', '').isdigit():
                                    date_prefixes.add(potential_prefix)

            result = sorted(date_prefixes, reverse=True)  # Most recent first
            if result:
                print(f"📂 Found {len(result)} date prefixes in S3: {result[:5]}..." if len(result) > 5 else f"📂 Found {len(result)} date prefixes in S3: {result}")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"⚠️  S3 Bucket '{self.bucket_name}' does not exist.")
                print(f"   Please check your .env file: S3_BUCKET_NAME={self.bucket_name}")
                print(f"   Or ensure the bucket exists and your AWS credentials have access.")
            elif error_code == 'AccessDenied':
                print(f"⚠️  Access denied to bucket '{self.bucket_name}'. Check your AWS credentials.")
            else:
                print(f"⚠️  Error listing S3 objects: {e}")
            return []

    async def list_available_dates(self) -> List[str]:
        """
        List available dates (YYYY-MM-DD format) for which trending data exists.

        Returns:
            List of date strings in YYYY-MM-DD format
        """
        date_prefixes = await self.list_available_files()

        # Extract unique dates (first 8 characters: YYYYMMDD)
        dates = set()
        for prefix in date_prefixes:
            if len(prefix) >= 8:
                date_str = prefix[:8]  # YYYYMMDD
                # Convert to YYYY-MM-DD format
                try:
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    datetime.strptime(formatted_date, "%Y-%m-%d")
                    dates.add(formatted_date)
                except ValueError:
                    pass

        return sorted(dates, reverse=True)  # Most recent first

