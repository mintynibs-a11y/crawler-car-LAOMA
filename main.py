#!/usr/bin/env python3
"""
汽车外饰设计评论爬虫 – 主入口
Car Exterior Design Comment Crawler – Main Entry Point

Usage:
    python main.py                            # crawl all platforms with default keywords
    python main.py --keyword "汽车外饰改装"   # custom keyword
    python main.py --platforms jd bilibili    # specific platforms only
    python main.py --max-pages 3              # limit pages per keyword
    python main.py --output-dir ./my_output   # custom output directory
    python main.py --format csv               # save as CSV (default: json)
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.crawlers import BilibiliCrawler, JDCrawler, XiaohongshuCrawler, ZhihuCrawler
from src.utils import save_csv, save_json

# Default car-exterior-design keywords (汽车外饰相关关键词)
DEFAULT_KEYWORDS = [
    "汽车外饰",
    "车身改色膜",
    "汽车外观改装",
    "汽车贴膜",
    "汽车外饰设计",
]

CRAWLER_MAP = {
    "xiaohongshu": XiaohongshuCrawler,
    "xhs": XiaohongshuCrawler,
    "jd": JDCrawler,
    "bilibili": BilibiliCrawler,
    "bili": BilibiliCrawler,
    "zhihu": ZhihuCrawler,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="汽车外饰设计评论爬虫 – 小红书 / 京东 / Bilibili / 知乎"
    )
    parser.add_argument(
        "--keyword",
        "-k",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="One or more search keywords (default: %(default)s)",
    )
    parser.add_argument(
        "--platforms",
        "-p",
        nargs="+",
        choices=list(CRAWLER_MAP.keys()),
        default=["xiaohongshu", "jd", "bilibili", "zhihu"],
        help="Platforms to crawl (default: all four)",
    )
    parser.add_argument(
        "--max-pages",
        "-m",
        type=int,
        default=5,
        help="Maximum pages / items per keyword per platform (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="Directory to write result files (default: output/)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "csv", "both"],
        default="json",
        help="Output file format (default: json)",
    )
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Deduplicate platform keys (e.g. "xhs" and "xiaohongshu" both map to XHS)
    seen_classes: set = set()
    crawlers = []
    for name in args.platforms:
        cls = CRAWLER_MAP[name]
        if cls not in seen_classes:
            seen_classes.add(cls)
            crawlers.append((name, cls(max_pages=args.max_pages)))

    all_comments: list[dict] = []
    summary: list[dict] = []

    for name, crawler in crawlers:
        for kw in args.keyword:
            result = crawler.crawl(kw)
            comment_dicts = [c.to_dict() if hasattr(c, "to_dict") else c for c in result.comments]
            all_comments.extend(comment_dicts)

            summary.append(
                {
                    "platform": result.platform,
                    "keyword": kw,
                    "total": result.total,
                    "success": result.success,
                    "error": result.error,
                    "crawled_at": result.crawled_at,
                }
            )
            logger.info(
                "[%s] keyword='%s' → %d comments (success=%s)",
                result.platform,
                kw,
                result.total,
                result.success,
            )

            # Per-platform per-keyword file
            stem = f"{result.platform}_{kw}_{timestamp}"
            if args.format in ("json", "both"):
                save_json(comment_dicts, output_dir / f"{stem}.json")
            if args.format in ("csv", "both"):
                save_csv(comment_dicts, output_dir / f"{stem}.csv")

    # Combined output
    if args.format in ("json", "both"):
        save_json(all_comments, output_dir / f"all_comments_{timestamp}.json")
        save_json(summary, output_dir / f"summary_{timestamp}.json")
    if args.format in ("csv", "both"):
        save_csv(all_comments, output_dir / f"all_comments_{timestamp}.csv")
        save_csv(summary, output_dir / f"summary_{timestamp}.csv")

    logger.info(
        "Done. Total comments collected: %d across %d platform(s) / %d keyword(s).",
        len(all_comments),
        len(crawlers),
        len(args.keyword),
    )


if __name__ == "__main__":
    run(parse_args())
