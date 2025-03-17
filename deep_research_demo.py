#!/usr/bin/env python3
import asyncio
from loguru import logger

from src.config import load_config
from src.deep_research import deep_research, write_final_report, write_final_answer


async def run_demo():
    """
    演示如何使用 deep_research 模块进行研究
    """
    # 加载配置
    load_config()

    # 定义研究问题
    query = "中国历史上最伟大的发明是什么？"

    # 定义进度回调函数
    def progress_callback(progress):
        depth = progress["currentDepth"]
        total_depth = progress["totalDepth"]
        completed = progress["completedQueries"]
        total = progress["totalQueries"]
        current = progress["currentQuery"]

        logger.info(f"进度: 深度 {depth}/{total_depth}, 查询 {completed}/{total} - 当前: {current}")

    # 运行研究
    logger.info(f"开始研究: {query}")
    result = await deep_research(
        query=query,
        breadth=3,  # 每次迭代的搜索查询数量
        depth=2,  # 递归迭代次数
        on_progress=progress_callback
    )

    # 获取研究结果
    learnings = result["learnings"]
    visited_urls = result["visitedUrls"]

    logger.info(f"研究完成! 发现 {len(learnings)} 条学习内容和 {len(visited_urls)} 个来源。")

    # 生成详细报告
    logger.info("生成详细报告...")
    report = await write_final_report(
        query=query,
        learnings=learnings,
        visited_urls=visited_urls
    )

    # 生成简洁回答
    logger.info("生成简洁回答...")
    answer = await write_final_answer(
        query=query,
        learnings=learnings
    )

    # 保存结果到文件
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report)

    with open("answer.txt", "w", encoding="utf-8") as f:
        f.write(answer)

    logger.info("报告已保存到 report.md")
    logger.info("回答已保存到 answer.txt")

    # 打印简洁回答
    print("\n" + "=" * 50)
    print(f"研究问题: {query}")
    print("=" * 50 + "\n")
    print(answer)
    print("\n" + "=" * 50)


if __name__ == "__main__":
    # 运行异步演示
    asyncio.run(run_demo())
