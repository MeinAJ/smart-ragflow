"""
命令行工具。

提供文档解析的命令行接口。
"""

import argparse
import asyncio
import logging
import sys

from backend_parser.service import DocumentParseService


# 配置日志
def setup_logging(verbose: bool = False):
    """配置日志级别。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def parse_single(file_url: str, doc_id: str = None, skip_embedding: bool = False, skip_indexing: bool = False, force_update: bool = True):
    """解析单个文件 URL。"""
    async with DocumentParseService() as service:
        result = await service.process(
            file_url=file_url,
            doc_id=doc_id,
            skip_embedding=skip_embedding,
            skip_indexing=skip_indexing,
            force_update=force_update
        )

        if result.success:
            print(f"✓ Successfully parsed: {result.document.title}")
            print(f"  - File: {result.document.file_name}")
            print(f"  - URL: {result.document.file_path}")
            print(f"  - Doc ID: {result.document.id}")
            print(f"  - Size: {result.document.file_size} bytes")
            print(f"  - Sections: {len(result.document.sections)}")
            print(f"  - Chunks: {len(result.chunks)}")
            if result.error_message == "Document already exists":
                print(f"  - Note: Document already exists, skipped")
        else:
            print(f"✗ Failed to parse: {file_url}")
            print(f"  Error: {result.error_message}")

        return result.success


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="Document Parser CLI - Parse documents from MinIO URLs and index to OpenSearch"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # parse 命令
    parse_parser = subparsers.add_parser("parse", help="Parse a single file from URL")
    parse_parser.add_argument("--file_url", dest="file_url", help="File URL (e.g., http://localhost:9000/bucket/file.pdf)")
    parse_parser.add_argument(
        "--doc_id",
        dest="doc_id",
        help="Custom document ID (default: auto-generated UUID)"
    )
    parse_parser.add_argument(
        "--skip-embedding",
        action="store_true",
        help="Skip embedding generation"
    )
    parse_parser.add_argument(
        "--skip-indexing",
        action="store_true",
        help="Skip indexing to OpenSearch"
    )
    parse_parser.add_argument(
        "--no-update",
        action="store_true",
        help="Skip if document already exists (default: force update)"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.command == "parse":
        success = asyncio.run(parse_single(
            file_url=args.file_url,
            doc_id=args.doc_id,
            skip_embedding=args.skip_embedding,
            skip_indexing=args.skip_indexing,
            force_update=not args.no_update
        ))
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
