# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:
"""
import argparse
import asyncio
from src.config import load_config, get_config
from src.deep_research import deep_research_stream
from loguru import logger


async def run_research(args):
    # 加载配置
    config = get_config()

    # 定义研究问题
    query = args.query

    # 定义进度回调函数
    def progress_callback(progress):
        current = progress.get("currentQuery", "")

        logger.info(f"进度: 当前查询: {current}")

    # 运行研究
    logger.info(f"开始研究: {query}")

    # 使用流式研究，通过user_clarifications跳过澄清步骤
    async for result in deep_research_stream(
            query=query,
            on_progress=progress_callback,
            user_clarifications={'all': 'skip'},  # 使用特殊标记跳过澄清
            history_context=""  # 添加空的history_context
    ):
        # 处理状态更新
        if result.get("status_update"):
            logger.info(f"状态更新: {result['status_update']}")

        # 如果研究完成，获取最终报告
        if result.get("stage") == "completed":
            learnings = result.get("learnings", [])
            visited_urls = result.get("visitedUrls", [])
            final_report = result.get("final_report", "")

            logger.info(f"研究完成! 发现 {len(learnings)} 条学习内容和 {len(visited_urls)} 个来源。")

            # 保存结果到文件
            with open("report.md", "w", encoding="utf-8") as f:
                f.write(final_report)

            logger.info("报告已保存到 report.md")

            print("\n" + "=" * 50)
            print(f"研究问题: {query}")
            print("=" * 50)
            print("\n研究报告:")
            print(final_report)
            print("\n" + "=" * 50)

            break


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Deep Research - AI-powered research assistant"
    )

    # Add config file argument
    parser.add_argument(
        "--config", type=str,
        help="Path to YAML configuration file"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # demo command
    demo_parser = subparsers.add_parser("demo", help="Run the gradio demo server")
    demo_parser.add_argument(
        "--host", type=str, default='0.0.0.0', help="Host ip"
    )

    # Research command
    research_parser = subparsers.add_parser("research", help="Run research directly")
    research_parser.add_argument(
        "query", type=str,
        help="Research query"
    )
    args = parser.parse_args()

    # Load configuration
    if args.config:
        load_config(args.config)

    # Execute command
    if args.command == "research":
        asyncio.run(run_research(args))
    elif args.command == "demo":
        from src.gradio_chat import run_gradio_demo
        run_gradio_demo()
    else:
        # Default to showing help if no command specified
        parser.print_help()


if __name__ == "__main__":
    main()
