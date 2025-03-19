#!/usr/bin/env python3
import asyncio
from loguru import logger

from src.config import get_config
from src.deep_research import deep_research_stream


async def run_demo():
    """
    演示如何使用 deep_research 模块进行研究
    """
    # 加载配置
    config = get_config()

    # 定义研究问题
    query = "中国元朝的货币制度改革的影响意义？"

    # 定义进度回调函数
    def progress_callback(progress):
        depth = progress.get("currentDepth", 0)
        total_depth = progress.get("totalDepth", 0)
        completed = progress.get("completedQueries", 0)
        total = progress.get("totalQueries", 0)
        current = progress.get("currentQuery", "")

        logger.info(f"进度: 深度 {depth}/{total_depth}, 查询 {completed}/{total} - 当前: {current}")

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


if __name__ == "__main__":
    # 运行异步演示
    asyncio.run(run_demo())
