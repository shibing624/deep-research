# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:

Deep research functionality for comprehensive research.
"""

import asyncio
import json
import traceback
import inspect
import platform
from typing import Optional, Callable, Dict, List, Any, Union, Tuple, AsyncGenerator
from loguru import logger

from .config import get_config
from .providers import get_search_provider
from .prompts import (
    SHOULD_CLARIFY_QUERY_PROMPT,
    FOLLOW_UP_QUESTIONS_PROMPT,
    PROCESS_NO_CLARIFICATIONS_PROMPT,
    PROCESS_CLARIFICATIONS_PROMPT,
    RESEARCH_PLAN_PROMPT,
    EXTRACT_SEARCH_RESULTS_SYSTEM_PROMPT,
    EXTRACT_SEARCH_RESULTS_PROMPT,
    RESEARCH_SUMMARY_PROMPT,
    FINAL_REPORT_SYSTEM_PROMPT,
    FINAL_REPORT_PROMPT,
    FINAL_ANSWER_PROMPT
)
from .model_utils import generate_completion, generate_json_completion
from .search_utils import search_with_query


def add_event_loop_policy():
    """Add event loop policy for Windows if needed."""
    if platform.system() == "Windows":
        try:
            # Set event loop policy for Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception as e:
            print(f"Error setting event loop policy: {e}")


def limit_context_size(text: str, max_size: int) -> str:
    """
    Limit the context size to prevent LLM token limit errors.
    
    Args:
        text: Text to limit
        max_size: Approximate maximum character count (rough estimate for tokens)
        
    Returns:
        Limited text
    """
    # Simple character-based truncation (rough approximation)
    # On average, 1 token is roughly 4 characters for English text
    # For Chinese, the ratio is 2
    char_limit = max_size * 2
    
    if len(text) <= char_limit:
        return text
    
    logger.warning(f"Truncating context from {len(text)} chars to ~{char_limit} chars")
    
    # For JSON strings, try to preserve structure
    if text.startswith('{') and text.endswith('}'):
        try:
            # Try to parse as JSON
            data = json.loads(text)
            # If it's a list of items, truncate the list
            if isinstance(data, list):
                # Calculate approx chars per item
                if len(data) > 0:
                    chars_per_item = len(text) / len(data)
                    items_to_keep = int(char_limit / chars_per_item)
                    items_to_keep = max(1, min(items_to_keep, len(data)))
                    return json.dumps(data[:items_to_keep], ensure_ascii=False)
            # If it contains a list property, truncate that
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    chars_per_item = len(json.dumps(value, ensure_ascii=False)) / len(value)
                    items_to_keep = int(char_limit / 2 / chars_per_item)  # Use half for lists
                    items_to_keep = max(1, min(items_to_keep, len(value)))
                    data[key] = value[:items_to_keep]
            return json.dumps(data, ensure_ascii=False)
        except:
            # Not valid JSON, use simple truncation
            pass
    
    # Simple truncation with indicator
    return text[:char_limit-50] + "... [content truncated due to token limit]"


async def should_clarify_query(query: str, history_context: str = '') -> bool:
    """
    Use the language model to determine if a query needs clarification.
    """
    try:
        prompt = SHOULD_CLARIFY_QUERY_PROMPT.format(query=query, history_context=history_context)
        result = await generate_completion(prompt, temperature=0)
        logger.debug(f"query: {query}, should clarify query result: {result}")

        # 检查结果是否包含肯定回答（yes/y）
        needs_clarification = "yes" in result.lower() or 'y' in result.lower()
        return needs_clarification
    except Exception as e:
        logger.error(f"error: {str(e)}")
        return True


async def generate_followup_questions(query: str, history_context: str = '') -> Dict[str, Any]:
    """
    Generate clarifying follow-up questions for the given query.

    Args:
        query: The user's research query
        history_context: Chat history context

    Returns:
        Dict containing whether clarification is needed and questions
    """
    try:
        # Format the prompt
        prompt = FOLLOW_UP_QUESTIONS_PROMPT.format(query=query, history_context=history_context)

        # Generate the followup questions
        result = await generate_json_completion(prompt, temperature=0.7)

        # Ensure the expected structure
        if "needs_clarification" not in result:
            result["needs_clarification"] = False

        if "questions" not in result:
            result["questions"] = []

        logger.debug(f"Follow-up questions: {result}")
        return result

    except Exception as e:
        logger.error(f"Error generating followup questions: {str(e)}")
        return {
            "needs_clarification": False,
            "questions": []
        }


async def process_clarifications(
        query: str,
        user_responses: Dict[str, str],
        all_questions: List[Dict[str, Any]],
        history_context: str = ''
) -> Dict[str, Any]:
    """
    Process user responses to clarification questions and refine the query.

    Args:
        query: The original query
        user_responses: Dict mapping question keys to user responses
        all_questions: List of all questions that were asked
        history_context: Chat history context

    Returns:
        Dict with refined query and other information
    """
    try:
        # Format the questions and responses for the prompt
        clarifications = []
        unanswered = []

        for question in all_questions:
            key = question.get("key", "")
            question_text = question.get("question", "")
            default = question.get("default", "")

            if key in user_responses and user_responses[key]:
                clarifications.append(f"Q: {question_text}\nA: {user_responses[key]}")
            else:
                clarifications.append(f"Q: {question_text}\nA: [Not answered by user]")
                unanswered.append(f"Q: {question_text}\nDefault: {default}")

        # Check if all questions were unanswered - if so, modify the prompt
        all_unanswered = len(unanswered) == len(all_questions) and len(all_questions) > 0

        # Format the prompt
        if all_unanswered:
            prompt = PROCESS_NO_CLARIFICATIONS_PROMPT.format(
                query=query,
                unanswered_questions="\n\n".join(unanswered) if unanswered else "None",
                history_context=history_context
            )
        else:
            prompt = PROCESS_CLARIFICATIONS_PROMPT.format(
                query=query,
                clarifications="\n\n".join(clarifications),
                unanswered_questions="\n\n".join(unanswered) if unanswered else "None",
                history_context=history_context
            )

        # Generate the clarifications processing
        result = await generate_json_completion(prompt, temperature=0.7)

        # Ensure the expected structure
        if "refined_query" not in result:
            result["refined_query"] = query

        if "assumptions" not in result:
            result["assumptions"] = []

        if "requires_search" not in result:
            result["requires_search"] = True

        if "direct_answer" not in result:
            result["direct_answer"] = ""

        logger.debug(f"Processed clarifications: {result}")
        return result

    except Exception as e:
        logger.error(f"Error processing clarifications: {str(e)}")
        return {
            "refined_query": query,
            "assumptions": [],
            "requires_search": True,
            "direct_answer": ""
        }


async def generate_research_plan(query: str, history_context: str = "") -> Dict[str, Any]:
    """
    Generate a research plan with a variable number of steps based on the query complexity.

    Args:
        query: The research query
        history_context: Chat history context

    Returns:
        Dict containing the research plan with steps
    """
    try:
        # Format the prompt
        prompt = RESEARCH_PLAN_PROMPT.format(query=query, history_context=history_context)

        # Generate the research plan
        result = await generate_json_completion(prompt, temperature=0.7)

        # Ensure the expected structure
        if "steps" not in result or not result["steps"]:
            # Create a default single-step plan if none was provided
            result["steps"] = [{
                "step_id": 1,
                "description": "Research the query",
                "search_queries": [query],
                "goal": "Find information about the query"
            }]

        if "assessments" not in result:
            result["assessments"] = "No complexity assessment provided"

        logger.debug(f"Research plan: {result}")
        return result

    except Exception as e:
        logger.error(f"Error generating research plan: {str(e)}")
        # Return a simple default plan
        return {
            "assessments": "Error occurred, using default plan",
            "steps": [{
                "step_id": 1,
                "description": "Research the query",
                "search_queries": [query],
                "goal": "Find information about the query"
            }]
        }


async def extract_search_results(query: str, search_results: str) -> str:
    """
    Extract search results for a query.

    Args:
        query: The search query
        search_results: Formatted search results text

    Returns:
        extracted search results with detailed content and relevance information
    """
    try:
        # Get context size limit from config
        config = get_config()
        context_size = config.get("research", {}).get("context_size", 128000)
        
        # Limit search results size
        limited_search_results = limit_context_size(search_results, context_size // 2)
        
        # Format the prompt
        prompt = EXTRACT_SEARCH_RESULTS_PROMPT.format(
            query=query,
            search_results=limited_search_results
        )

        # Generate the extracted_contents
        extracted_contents = await generate_json_completion(
            prompt=prompt, 
            system_message=EXTRACT_SEARCH_RESULTS_SYSTEM_PROMPT,
            temperature=0
        )
        
        # Process and enrich the extracted content
        if "extracted_infos" in extracted_contents:
            # Make sure all entries have a relevance field (for backward compatibility)
            for info in extracted_contents["extracted_infos"]:
                if "relevance" not in info:
                    info["relevance"] = "与查询相关的信息"
        
        # Convert to string for storage and transfer
        extracted_contents_str = json.dumps(extracted_contents, ensure_ascii=False)
        return extracted_contents_str

    except Exception as e:
        logger.error(f"Error extract search results: {str(e)}")
        return f"Error extract results for '{query}': {str(e)}"


async def write_final_report_stream(query: str, context: str,
                                    history_context: str = '') -> AsyncGenerator[str, None]:
    """
    Streaming version of write_final_report that yields chunks of the report.

    Args:
        query: The original research query
        context: List of key learnings/facts discovered with their sources
        history_context: str

    Yields:
        Chunks of the final report
    """
    # Get context size limit from config
    config = get_config()
    context_size = config.get("research", {}).get("context_size", 128000)
    
    # Limit context sizes
    limited_context = limit_context_size(context, context_size // 2)
    limited_history = limit_context_size(history_context, context_size // 4)
    
    formatted_prompt = FINAL_REPORT_PROMPT.format(
        query=query,
        context=limited_context,
        history_context=limited_history
    )

    response_generator = await generate_completion(
        prompt=formatted_prompt,
        system_message="You are an expert researcher providing detailed, well-structured reports in Chinese.",
        temperature=0.7,
        stream=True
    )

    # Stream the response chunks
    async for chunk in response_generator:
        yield chunk


async def write_final_report(query: str, context: str, history_context: str = '') -> str:
    """
    Generate a final research report based on learnings and sources.

    Args:
        query: The original research query
        context: List of key learnings/facts discovered with their sources
        history_context: chat history

    Returns:
        A formatted research report
    """
    # Get context size limit from config
    config = get_config()
    context_size = config.get("research", {}).get("context_size", 128000)
    
    # Limit context sizes
    limited_context = limit_context_size(context, context_size // 2)
    limited_history = limit_context_size(history_context, context_size // 4)

    formatted_prompt = FINAL_REPORT_PROMPT.format(
        query=query,
        context=limited_context,
        history_context=limited_history
    )

    report = await generate_completion(
        prompt=formatted_prompt,
        system_message=FINAL_REPORT_SYSTEM_PROMPT,
        temperature=0.7
    )

    return report


async def write_final_answer(query: str, context: str, history_context: str = '') -> str:
    """
    Generate a final concise answer based on the research.

    Args:
        query: The original research query
        context: List of key learnings/facts discovered with their sources
        history_context: chat history

    Returns:
        A concise answer to the query
    """
    # Get context size limit from config
    config = get_config()
    context_size = config.get("research", {}).get("context_size", 128000)
    
    # Limit context sizes
    limited_context = limit_context_size(context, context_size // 2)
    limited_history = limit_context_size(history_context, context_size // 4)
    
    formatted_prompt = FINAL_ANSWER_PROMPT.format(
        query=query,
        context=limited_context,
        history_context=limited_history
    )

    answer = await generate_completion(
        prompt=formatted_prompt,
        system_message=FINAL_REPORT_SYSTEM_PROMPT,
        temperature=0.7
    )

    return answer


def write_final_report_sync(query: str, context: str, history_context: str = '') -> str:
    """
    Synchronous wrapper for the write_final_report function.

    Args:
        query: The original research query
        context: List of key learnings/facts discovered with their sources
        history_context: chat history

    Returns:
        A formatted research report
    """
    # Add event loop policy for Windows if needed
    add_event_loop_policy()

    # Run the async function in the event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        write_final_report(
            query=query,
            context=context,
            history_context=history_context
        )
    )


def write_final_answer_sync(query: str, context: str, history_context: str = '') -> str:
    """
    Synchronous wrapper for the write_final_answer function.

    Args:
        query: The original research query
        context: List of key learnings/facts discovered with their sources
        history_context: chat history

    Returns:
        A concise answer to the query
    """
    # Add event loop policy for Windows if needed
    add_event_loop_policy()

    # Run the async function in the event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        write_final_answer(
            query=query,
            context=context,
            history_context=history_context
        )
    )


async def research_step(
        query: str,
        config: Dict[str, Any],
        on_progress: Optional[Callable] = None,
        search_provider=None,
) -> Dict[str, Any]:
    """
    Perform a single step of the research process.

    Args:
        query: The query to research
        config: Configuration dictionary
        on_progress: Optional callback for progress updates
        search_provider: Search provider instance

    Returns:
        Dict with research results
    """
    if search_provider is None:
        search_provider = get_search_provider()

    # Progress update
    if on_progress:
        progress_data = {
            "currentQuery": query
        }

        # Check if on_progress is a coroutine function
        if inspect.iscoroutinefunction(on_progress):
            await on_progress(progress_data)
        else:
            on_progress(progress_data)

    # Get the search results
    search_result = await search_with_query(query, config, search_provider)
    search_results_text = search_result["summary"]
    urls = search_result["urls"]

    enable_refine_search_result = config.get("research", {}).get("enable_refine_search_result", False)
    if enable_refine_search_result:
        extracted_content = await extract_search_results(query, search_results_text)
    else:
        extracted_content = search_results_text

    return {
        "extracted_content": extracted_content,
        "urls": urls,
    }


async def deep_research_stream(
        query: str,
        on_progress: Optional[Callable] = None,
        user_clarifications: Dict[str, str] = None,
        search_source: Optional[str] = None,
        history_context: Optional[str] = None,
        skip_clarification: bool = False,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streaming version of deep research that yields partial results.

    Args:
        query: The research query
        on_progress: Optional callback function for progress updates
        user_clarifications: User responses to clarification questions
        search_source: Optional search provider to use
        history_context: history chat content
        skip_clarification: Whether to skip the clarification step

    Yields:
        Dict with partial research results and status updates
    """
    # Load configuration
    config = get_config()
    logger.debug(f"query: {query}, config: {config}")

    # Initialize tracking variables
    visited_urls = []
    all_learnings = []

    # Initialize search provider
    search_provider = get_search_provider(search_source=search_source)

    try:
        # Step 1: Yield initial status
        yield {
            "status_update": f"开始研究查询: '{query}'...",
            "learnings": all_learnings,
            "visitedUrls": visited_urls,
            "current_query": query,
            "stage": "initial"
        }

        # Step 1.5: 先判断是否需要生成澄清问题
        needs_clarification = False

        # 如果没有提供用户澄清，且不跳过澄清环节，则判断是否需要澄清
        if not user_clarifications and not skip_clarification:
            yield {
                "status_update": f"分析查询是否需要澄清...",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "current_query": query,
                "stage": "analyzing_query"
            }

            # 修复重复调用问题 - 使用缓存变量存储结果
            _clarification_cache_key = f"should_clarify_{query}"
            if _clarification_cache_key not in globals():
                needs_clarification = await should_clarify_query(query, history_context)
                globals()[_clarification_cache_key] = needs_clarification
            else:
                needs_clarification = globals()[_clarification_cache_key]
                logger.debug(f"使用缓存的澄清结果: {query}, result: {needs_clarification}")

            if not needs_clarification:
                yield {
                    "status_update": f"查询已足够清晰，跳过澄清步骤",
                    "learnings": all_learnings,
                    "visitedUrls": visited_urls,
                    "current_query": query,
                    "stage": "clarification_skipped"
                }
        elif skip_clarification:
            # 如果配置为跳过澄清环节，直接显示状态
            yield {
                "status_update": f"配置为跳过澄清环节，直接开始研究",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "current_query": query,
                "stage": "clarification_skipped"
            }

        # 如果LLM判断需要澄清，或者已经有用户澄清，且未配置跳过澄清环节，则继续生成或处理澄清问题
        questions = []
        if (needs_clarification or user_clarifications) and not skip_clarification:
            # Step 2: Generate clarification questions if needed
            if needs_clarification:
                yield {
                    "status_update": f"生成澄清问题...",
                    "learnings": all_learnings,
                    "visitedUrls": visited_urls,
                    "current_query": query,
                    "stage": "generating_questions"
                }

                followup_result = await generate_followup_questions(query, history_context)
                questions = followup_result.get("questions", [])

                if questions:
                    # If clarification is needed, update status
                    yield {
                        "status_update": f"查询需要澄清，生成了 {len(questions)} 个问题",
                        "learnings": all_learnings,
                        "visitedUrls": visited_urls,
                        "current_query": query,
                        "questions": questions,
                        "stage": "clarification_needed"
                    }

                    # If we don't have user responses yet, wait for them
                    if not user_clarifications:
                        yield {
                            "status_update": "等待用户回答澄清问题...",
                            "learnings": all_learnings,
                            "visitedUrls": visited_urls,
                            "current_query": query,
                            "questions": questions,
                            "awaiting_clarification": True,
                            "stage": "awaiting_clarification"
                        }
                        return

        # Step 3: Process user clarifications if provided
        refined_query = query
        user_responses = user_clarifications or {}

        if questions and user_clarifications and not skip_clarification:
            # Track which questions were answered vs. which use defaults
            answered_questions = []
            unanswered_questions = []

            for q in questions:
                key = q.get("key", "")
                question_text = q.get("question", "")
                if key in user_responses and user_responses[key]:
                    answered_questions.append(question_text)
                else:
                    unanswered_questions.append(question_text)

            yield {
                "status_update": f"处理用户的澄清回答 ({len(answered_questions)}/{len(questions)} 已回答)",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "current_query": query,
                "answered_questions": answered_questions,
                "unanswered_questions": unanswered_questions,
                "stage": "processing_clarifications"
            }

            # Process the clarifications
            clarification_result = await process_clarifications(query, user_responses, questions, history_context)
            refined_query = clarification_result.get("refined_query", query)

            yield {
                "status_update": f"查询已优化: '{refined_query}'",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "original_query": query,
                "current_query": refined_query,
                "assumptions": clarification_result.get("assumptions", []),
                "stage": "query_refined"
            }

            # Check if this is a simple query that can be answered directly
            if not clarification_result.get("requires_search", True):
                direct_answer = clarification_result.get("direct_answer", "")
                if direct_answer:
                    yield {
                        "status_update": "查询可以直接回答，无需搜索",
                        "requires_search": False,
                        "direct_answer": direct_answer,
                        "final_report": direct_answer,  # 直接使用direct_answer作为最终报告
                        "learnings": ["直接回答: " + direct_answer],
                        "visitedUrls": [],
                        "stage": "completed"
                    }
                    return  # 不再需要继续执行查询流程

        # Step 4: Generate research plan with variable steps
        yield {
            "status_update": f"为查询生成研究计划: '{refined_query}'",
            "learnings": all_learnings,
            "visitedUrls": visited_urls,
            "current_query": refined_query,
            "stage": "planning"
        }

        plan_result = await generate_research_plan(refined_query, history_context)
        steps = plan_result.get("steps", [])

        yield {
            "status_update": f"生成了 {len(steps)} 步研究计划: {plan_result.get('assessments', '无评估')}",
            "learnings": all_learnings,
            "visitedUrls": visited_urls,
            "current_query": refined_query,
            "research_plan": steps,
            "stage": "plan_generated"
        }

        # Track step summaries for the final analysis
        step_summaries = []

        # Iterate through each step in the research plan
        for step_idx, step in enumerate(steps):
            step_id = step.get("step_id", step_idx + 1)
            description = step.get("description", f"Research step {step_id}")
            search_queries = step.get("search_queries", [refined_query])

            yield {
                "status_update": f"开始研究步骤 {step_id}/{len(steps)}: {description}",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "current_query": refined_query,
                "search_queries": search_queries,
                "current_step": step,
                "progress": {
                    "current_step": step_id,
                    "total_steps": len(steps)
                },
                "stage": "step_started"
            }

            # Create a queue of queries to process for this step
            step_urls = []
            step_learnings = []

            current_queries = search_queries.copy()
            # Research these queries concurrently
            yield {
                "status_update": f"步骤 {step_id}/{len(steps)}: 并行研究 {len(current_queries)} 个查询",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "current_queries": current_queries,
                "progress": {
                    "current_step": step_id,
                    "total_steps": len(steps),
                    "processed_queries": len(current_queries),
                },
                "stage": "processing_queries"
            }

            # Process each query in the current batch
            research_tasks = []
            for current_query in current_queries:
                task = research_step(
                    query=current_query,
                    config=config,
                    on_progress=on_progress,
                    search_provider=search_provider,
                )
                research_tasks.append(task)

            # Execute tasks with concurrency
            results = await asyncio.gather(*research_tasks)

            # Process the results
            for result in results:
                # Update tracking variables
                urls = result["urls"]
                content = result["extracted_content"]
                step_urls.extend(urls)
                step_learnings.append(content)

            # Format learnings and URLs for display
            formatted_learnings = []
            for i, learning in enumerate(step_learnings):
                formatted_learnings.append(f"[{i + 1}] {learning}")

            formatted_urls = []
            for i, url in enumerate(step_urls):
                formatted_urls.append(f"[{i + 1}] {url}")

            # Truncate longer learnings for display
            new_learnings = [str(i)[:400] for i in step_learnings]
            yield {
                "status_update": f"步骤 {step_id}/{len(steps)}: 发现 {len(new_learnings)} 个新见解",
                "learnings": all_learnings + step_learnings,
                "visitedUrls": visited_urls + step_urls,
                "new_learnings": new_learnings,
                "formatted_new_learnings": formatted_learnings,
                "new_urls": step_urls,
                "formatted_new_urls": formatted_urls,
                "progress": {
                    "current_step": step_id,
                    "total_steps": len(steps),
                    "processed_queries": len(current_queries)
                },
                "stage": "insights_found"
            }

            # Update visited URLs and learnings
            visited_urls.extend(step_urls)
            all_learnings.extend(step_learnings)

            # Save step summary
            step_summaries.append({
                "step_id": step_id,
                "description": description,
                "learnings": step_learnings,
                "urls": step_urls
            })

            # Format all step learnings for display
            formatted_step_learnings = []
            for i, learning in enumerate(step_learnings):
                formatted_step_learnings.append(f"[{i + 1}] {learning}")

            # Step completion update
            yield {
                "status_update": f"完成研究步骤 {step_id}/{len(steps)}: {description}，获得 {len(step_learnings)} 个见解",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "step_learnings": step_learnings,
                "formatted_step_learnings": formatted_step_learnings,
                "step_urls": step_urls,
                "progress": {
                    "current_step": step_id,
                    "total_steps": len(steps),
                    "completed": True
                },
                "stage": "step_completed"
            }

        enable_next_plan = config.get("research", {}).get("enable_next_plan", False)
        if enable_next_plan:
            # Perform final analysis
            yield {
                "status_update": "分析所有已收集的信息...",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "stage": "final_analysis"
            }

            steps_summary_text = "\n\n".join([
                f"步骤 {s['step_id']}: {s['description']}\n发现: {json.dumps(s['learnings'], ensure_ascii=False)}"
                for s in step_summaries
            ])

            future_research = RESEARCH_SUMMARY_PROMPT.format(
                query=refined_query,
                steps_summary=steps_summary_text
            )

            future_research_result = await generate_json_completion(future_research, temperature=0.7)

            # Add final findings to learnings
            findings = []
            if "findings" in future_research_result:
                all_learnings.extend(future_research_result["findings"])
                findings = future_research_result["findings"]

            # Format final findings
            formatted_findings = []
            for i, finding in enumerate(findings):
                formatted_findings.append(f"[{i + 1}] {finding}")

            yield {
                "status_update": f"分析完成，得出 {len(findings)} 个主要发现",
                "learnings": all_learnings,
                "visitedUrls": visited_urls,
                "final_findings": findings,
                "formatted_final_findings": formatted_findings,
                "gaps": future_research_result.get("gaps", []),
                "recommendations": future_research_result.get("recommendations", []),
                "stage": "analysis_completed"
            }
        else:
            future_research_result = ""
            # No need to modify all_learnings when skipping summary

        yield {
            "status_update": "生成详细研究报告...",
            "learnings": all_learnings,
            "visitedUrls": visited_urls,
            "stage": "generating_report"
        }

        # Generate report (non-streaming for now)
        context = str(all_learnings) + '\n\n' + str(future_research_result)
        final_report = await write_final_report(refined_query, context, history_context)

        # Return compiled results
        yield {
            "status_update": "研究完成!",
            "query": refined_query,
            "originalQuery": query,
            "learnings": all_learnings,
            "visitedUrls": list(set(visited_urls)),
            "summary": future_research_result,
            "final_report": final_report,
            "stage": "completed"
        }

    except Exception as e:
        logger.error(f"Error in deep research stream: {str(e)}")
        logger.error(traceback.format_exc())

        yield {
            "status_update": f"错误: {str(e)}",
            "error": str(e),
            "learnings": all_learnings,
            "visitedUrls": visited_urls,
            "stage": "error"
        }
