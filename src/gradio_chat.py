# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:

A simplified Gradio demo for Deep Research with basic conversation interface.
"""

import time
import gradio as gr
from loguru import logger
from .config import get_config
from .deep_research import (
    deep_research_stream,
    generate_followup_questions,
    process_clarifications,
    write_final_report,
    should_clarify_query
)

# Load configuration
config = get_config()


def run_gradio_demo():
    """Run a modern Gradio demo for Deep Research using ChatInterface"""
    enable_clarification = config.get("research", {}).get("enable_clarification", False)
    search_source = config.get("research", {}).get("search_source", "tavily")

    # Conversation state (shared across functions)
    conversation_state = {
        "current_query": "",
        "needs_clarification": False,
        "questions": [],
        "waiting_for_clarification": False,
        "clarification_answers": {},
        "last_status": "",  # 跟踪最后一个状态更新
        "history": [],  # 保存当前聊天历史
        "search_source": search_source,  # 存储搜索提供商
        "enable_clarification": enable_clarification  # 存储是否启用澄清
    }

    async def research_with_thinking(message, history):
        """处理查询，展示研究过程并返回结果"""
        if not message:
            yield history  # 空消息，直接返回
            return  # 无值返回是允许的

        # 重置状态，确保多次查询之间状态不混淆
        conversation_state["last_status"] = ""
        conversation_state["current_query"] = ""
        conversation_state["questions"] = []

        # 判断是否是澄清回答，如果是则不重置waiting_for_clarification
        if not conversation_state["waiting_for_clarification"]:
            conversation_state["waiting_for_clarification"] = False
            conversation_state["clarification_answers"] = {}

        logger.debug(
            f"Starting research, message: {message}, search_source: {search_source}, enable_clarification: {enable_clarification}")

        # 构建历史上下文 - 直接使用history即可
        history_context = ''
        for msg in history:
            if isinstance(msg, dict) and msg.get("role") == "user":
                q = 'Q:' + msg.get("content", "") + '\n'
                history_context += q

        # 3. 检查是否是对澄清问题的回答
        if conversation_state["waiting_for_clarification"]:
            async for msg in handle_clarification_answer(message, history, history_context):
                yield msg
            return  # 无值返回是允许的

        # 4. 创建研究过程消息并将其添加到历史记录
        messages = []
        messages.append({"role": "assistant", "content": "正在进行研究...", "metadata": {"title": "研究过程"}})
        yield messages

        # 5. 处理澄清环节
        if not enable_clarification:
            messages[-1]["content"] = "跳过澄清环节，直接开始研究..."
            yield messages
        else:
            # 分析查询是否需要澄清
            messages[-1]["content"] = "分析查询需求中..."
            yield messages

            needs_clarification = await should_clarify_query(message, history_context)
            if needs_clarification:
                messages[-1]["content"] = "生成澄清问题..."
                yield messages

                followup_result = await generate_followup_questions(message, history_context)
                questions = followup_result.get("questions", [])

                if questions:
                    # 保存问题和状态
                    conversation_state["current_query"] = message
                    conversation_state["questions"] = questions
                    conversation_state["waiting_for_clarification"] = True

                    # 显示问题给用户
                    clarification_msg = "请回答以下问题，帮助我更好地理解您的查询:"
                    for i, q in enumerate(questions, 1):
                        clarification_msg += f"\n{i}. {q.get('question', '')}"

                    # 替换研究过程消息为澄清问题
                    messages[-1] = {"role": "assistant", "content": clarification_msg}
                    yield messages
                    return  # 等待用户回答
                else:
                    messages[-1]["content"] = "无法生成有效的澄清问题，继续研究..."
                    yield messages
            else:
                messages[-1]["content"] = "查询已足够清晰，开始研究..."
                yield messages

        # 6. 开始搜索
        messages[-1]["content"] = f"使用 {search_source} 搜索相关信息中..."
        yield messages

        # 7. 执行研究过程
        final_result = None
        research_log = []

        async for partial_result in deep_research_stream(
                query=message,
                search_source=search_source,
                history_context=history_context,
                enable_clarification=enable_clarification
        ):
            # 更新研究进度
            if partial_result.get("status_update"):
                status = partial_result.get("status_update")
                stage = partial_result.get("stage", "")

                # 检查状态是否有变化
                if status != conversation_state["last_status"]:
                    conversation_state["last_status"] = status

                    # 更新研究进度消息
                    timestamp = time.strftime('%H:%M:%S')
                    status_line = f"[{timestamp}] {status}"
                    research_log.append(status_line)

                    # 显示当前研究计划步骤
                    if partial_result.get("current_step"):
                        current_step = partial_result.get("current_step")
                        step_id = current_step.get("step_id", "")
                        description = current_step.get("description", "")
                        step_line = f"当前步骤 {step_id}: {description}"
                        research_log.append(step_line)

                    # 显示当前查询
                    if partial_result.get("current_queries"):
                        queries = partial_result.get("current_queries")
                        queries_lines = ["**当前并行查询**:"]
                        for i, q in enumerate(queries, 1):
                            queries_lines.append(f"{i}. {q}")
                        research_log.append("\n".join(queries_lines))

                    # 对于特定阶段，添加更多信息
                    if stage == "plan_generated" and partial_result.get("research_plan"):
                        research_plan = partial_result.get("research_plan")
                        plan_lines = ["**研究计划**:"]
                        for i, step in enumerate(research_plan):
                            step_id = step.get("step_id", i + 1)
                            description = step.get("description", "")
                            plan_lines.append(f"步骤 {step_id}: {description}")
                        research_log.append("\n".join(plan_lines))

                    # 添加阶段详细信息
                    if stage == "insights_found" and partial_result.get("formatted_new_learnings"):
                        if partial_result.get("formatted_new_urls") and len(
                                partial_result.get("formatted_new_urls")) > 0:
                            research_log.append("\n**来源**:\n" + "\n".join(
                                partial_result.get("formatted_new_urls", [])[:3]))

                    elif stage == "step_completed" and partial_result.get("formatted_step_learnings"):
                        research_log.append("\n**步骤总结**:\n" + "\n".join(
                            partial_result.get("formatted_step_learnings", [])))

                    elif stage == "analysis_completed" and partial_result.get("formatted_final_findings"):
                        research_log.append("\n**主要发现**:\n" + "\n".join(
                            partial_result.get("formatted_final_findings", [])))

                        if partial_result.get("gaps"):
                            research_log.append("\n\n**研究空白**:\n- " + "\n- ".join(partial_result.get("gaps", [])))

                    # 合并所有日志并更新研究过程消息
                    messages[-1]["content"] = "\n\n".join(research_log)
                    yield messages

            # 保存最后一个结果用于生成报告
            final_result = partial_result

            # 如果有最终报告，跳出循环
            if "final_report" in partial_result:
                break

        # 8. 生成报告
        if final_result:
            # 如果直接在结果中有final_report，直接使用
            if "final_report" in final_result:
                report = final_result["final_report"]
                # 标记研究过程消息已完成
                research_process = messages[-1]["content"]
                messages[-1]["content"] = "研究完成，报告已生成。\n\n" + research_process
                yield messages
            else:
                # 否则，使用收集到的信息生成报告
                research_process = messages[-1]["content"]
                messages[-1]["content"] = "正在整合研究结果并生成报告...\n\n" + research_process
                yield messages

                learnings = final_result.get("learnings", [])

                try:
                    report = await write_final_report(
                        query=message,
                        context=str(learnings),
                        history_context=history_context
                    )
                    # 确保report不为None
                    if report is None:
                        report = "抱歉，无法生成研究报告。"
                        logger.error(f"write_final_report returned None for query: {message}")
                except Exception as e:
                    report = f"生成报告时出错: {str(e)}"
                    logger.error(f"Error in write_final_report: {str(e)}")

                # 保留研究过程信息
                messages[-1]["content"] = "研究完成，报告已生成。\n\n" + research_process
                yield messages

            # 添加最终报告消息，但保留研究过程消息
            messages.append({"role": "assistant", "content": report})
            yield messages
        else:
            messages.append(
                {"role": "assistant", "content": "抱歉，我无法为您的查询生成研究报告。请尝试其他问题或稍后再试。"})
            yield messages

    async def handle_clarification_answer(message, history, history_context):
        """处理用户对澄清问题的回答"""
        # 重置等待标志
        conversation_state["waiting_for_clarification"] = False

        # 获取原始查询和问题
        query = conversation_state["current_query"]
        questions = conversation_state["questions"]

        # 重置状态，确保多次查询之间状态不混淆
        conversation_state["last_status"] = ""

        # 1. 创建消息列表并添加研究过程消息
        messages = []
        messages.append({"role": "assistant", "content": "解析您的澄清回答...", "metadata": {"title": "研究过程"}})
        yield messages

        # 2. 解析用户回答
        lines = [line.strip() for line in message.split('\n') if line.strip()]
        if len(lines) < len(questions):
            # 尝试逗号分隔
            if ',' in message:
                lines = [ans.strip() for ans in message.split(',')]

        # 3. 创建响应字典
        user_responses = {}
        for i, q in enumerate(questions):
            key = q.get("key", f"q{i}")
            if i < len(lines) and lines[i]:
                user_responses[key] = lines[i]

        # 4. 处理澄清内容
        messages[-1]["content"] = "处理您的澄清内容..."
        yield messages

        # 5. 处理澄清并优化查询
        clarification_result = await process_clarifications(
            query=query,
            user_responses=user_responses,
            all_questions=questions,
            history_context=history_context
        )

        # 6. 获取优化后的查询
        refined_query = clarification_result.get("refined_query", query)
        messages[-1]["content"] = f"已优化查询: {refined_query}"
        yield messages

        # 7. 检查是否可以直接回答
        if not clarification_result.get("requires_search", True) and clarification_result.get("direct_answer"):
            direct_answer = clarification_result.get("direct_answer", "")

            # 保留研究过程消息，并添加直接回答
            research_process = messages[-1]["content"]
            messages[-1]["content"] = "提供直接回答，无需搜索。\n\n" + research_process
            yield messages

            # 添加最终回答，但保留研究过程
            messages.append({"role": "assistant", "content": direct_answer})
            yield messages

        # 8. 开始搜索
        messages[-1]["content"] = "基于您的澄清开始搜索信息..."
        yield messages

        # 9. 执行研究过程
        final_result = None
        research_log = []

        async for partial_result in deep_research_stream(
                query=refined_query,
                user_clarifications=user_responses,
                search_source=search_source,
                history_context=history_context
        ):
            # 更新研究进度
            if partial_result.get("status_update"):
                status = partial_result.get("status_update")
                stage = partial_result.get("stage", "")

                # 检查状态是否有变化
                if status != conversation_state["last_status"]:
                    conversation_state["last_status"] = status

                    # 更新研究进度消息
                    timestamp = time.strftime('%H:%M:%S')
                    status_line = f"[{timestamp}] {status}"
                    research_log.append(status_line)

                    # 显示当前研究计划步骤
                    if partial_result.get("current_step"):
                        current_step = partial_result.get("current_step")
                        step_id = current_step.get("step_id", "")
                        description = current_step.get("description", "")
                        step_line = f"当前步骤 {step_id}: {description}"
                        research_log.append(step_line)

                    # 显示当前查询
                    if partial_result.get("current_queries"):
                        queries = partial_result.get("current_queries")
                        queries_lines = ["当前并行查询:"]
                        for i, q in enumerate(queries, 1):
                            queries_lines.append(f"{i}. {q}")
                        research_log.append("\n".join(queries_lines))

                    # 对于特定阶段，添加更多信息
                    if stage == "plan_generated" and partial_result.get("research_plan"):
                        research_plan = partial_result.get("research_plan")
                        plan_lines = ["研究计划:"]
                        for i, step in enumerate(research_plan):
                            step_id = step.get("step_id", i + 1)
                            description = step.get("description", "")
                            plan_lines.append(f"步骤 {step_id}: {description}")
                        research_log.append("\n".join(plan_lines))

                    # 添加阶段详细信息
                    if stage == "insights_found" and partial_result.get("formatted_new_learnings"):
                        if partial_result.get("formatted_new_urls") and len(
                                partial_result.get("formatted_new_urls")) > 0:
                            research_log.append("\n**来源**:\n" + "\n".join(
                                partial_result.get("formatted_new_urls", [])[:3]))

                    elif stage == "step_completed" and partial_result.get("formatted_step_learnings"):
                        research_log.append("\n**步骤总结**:\n" + "\n".join(
                            partial_result.get("formatted_step_learnings", [])))

                    elif stage == "analysis_completed" and partial_result.get("formatted_final_findings"):
                        research_log.append("\n**主要发现**:\n" + "\n".join(
                            partial_result.get("formatted_final_findings", [])))

                        if partial_result.get("gaps"):
                            research_log.append("\n\n**研究空白**:\n- " + "\n- ".join(partial_result.get("gaps", [])))

                    # 合并所有日志并更新研究过程消息
                    messages[-1]["content"] = "\n\n".join(research_log)
                    yield messages

            # 保存最后一个结果用于生成报告
            final_result = partial_result

            # 如果有最终报告，跳出循环
            if "final_report" in partial_result:
                break

        # 10. 生成报告
        if final_result:
            # 如果直接在结果中有final_report，直接使用
            if "final_report" in final_result:
                report = final_result["final_report"]
                # 标记研究过程消息已完成
                research_process = messages[-1]["content"]
                messages[-1]["content"] = "研究完成，报告已生成。\n\n" + research_process
                yield messages
            else:
                # 否则，使用收集到的信息生成报告
                research_process = messages[-1]["content"]
                messages[-1]["content"] = "正在整合研究结果并生成报告...\n\n" + research_process
                yield messages

                learnings = final_result.get("learnings", [])

                try:
                    report = await write_final_report(
                        query=refined_query,
                        context=str(learnings),
                        history_context=history_context
                    )
                    # 确保report不为None
                    if report is None:
                        report = "抱歉，无法生成研究报告。"
                        logger.error(f"returned None for query: {refined_query}")
                except Exception as e:
                    report = f"生成报告时出错: {str(e)}"
                    logger.error(f"Error in write_final_report: {str(e)}")

                # 保留研究过程信息
                messages[-1]["content"] = "研究完成，报告已生成。\n\n" + research_process
                yield messages

            # 添加最终报告消息，但保留研究过程消息
            messages.append({"role": "assistant", "content": report})
            yield messages
        else:
            messages.append(
                {"role": "assistant", "content": "抱歉，我无法为您的查询生成研究报告。请尝试其他问题或稍后再试。"})
            yield messages

    # 创建 ChatInterface
    demo = gr.ChatInterface(
        research_with_thinking,
        type='messages',
        title="🔍 Deep Research",
        description="使用此工具进行深度研究，我将搜索互联网为您找到回答。Powered by [Deep Research](https://github.com/shibing624/deep-research) Made with ❤️ by [shibing624](https://github.com/shibing624)",
        examples=[
            ["特斯拉股票的最新行情?"],
            ["介绍一下最近的人工智能技术发展趋势"],
            ["中国2024年GDP增长了多少?"],
            ["Explain the differences between supervised and unsupervised machine learning."]
        ]
    )

    # 启动界面
    demo.queue()
    demo.launch(server_name="0.0.0.0", share=False, server_port=7860, show_api=False)


if __name__ == "__main__":
    run_gradio_demo()
