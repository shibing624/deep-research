import asyncio
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from .config import get_config
from .providers import get_model, trim_prompt, generate_object

from .serper_client import SerperClient

# Initialize Serper client
search_client = SerperClient()


def system_prompt():
    now = datetime.now().isoformat()
    return f"""You are an expert researcher. Today is {now}. Follow these instructions when responding:
  - You may be asked to research subjects that is after your knowledge cutoff, assume the user is right when presented with news.
  - The user is a highly experienced analyst, no need to simplify it, be as detailed as possible and make sure your response is correct.
  - Be highly organized.
  - Suggest solutions that I didn't think about.
  - Be proactive and anticipate my needs.
  - Treat me as an expert in all subject matter.
  - Mistakes erode my trust, so be accurate and thorough.
  - Provide detailed explanations, I'm comfortable with lots of detail.
  - Value good arguments over authorities, the source is irrelevant.
  - Consider new technologies and contrarian ideas, not just the conventional wisdom.
  - You may use high levels of speculation or prediction, just flag it for me.
  - User's question is written in Chinese, 需要用中文输出."""


async def generate_serp_queries(
        query: str,
        num_queries: int = 3,
        learnings: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """Generate SERP queries based on the user query and previous learnings."""
    model_config = get_model()

    prompt_text = f"""Given the following prompt from the user, generate a list of SERP queries to research the topic. Return a maximum of {num_queries} queries, but feel free to return less if the original prompt is clear. answer in json. Make sure each query is unique and not similar to each other: <prompt>{query}</prompt>\n\n"""

    if learnings:
        prompt_text += f"Here are some learnings from previous research, use them to generate more specific queries: {' '.join(learnings)}"

    result = generate_object(
        model_config=model_config,
        system=system_prompt(),
        prompt=prompt_text,
        schema={
            "queries": [
                {
                    "query": "string",
                    "researchGoal": "string"
                }
            ]
        }
    )

    queries = result.get("queries", [])
    return queries[:num_queries]


async def process_serp_result(
        query: str,
        result: Dict[str, Any],
        num_follow_up_questions: int = 2
) -> Dict[str, Any]:
    """Process SERP result to extract learnings and follow-up questions."""
    model_config = get_model()

    # Extract content from search results
    content_items = []
    for item in result.get("data", []):
        if item.get("content"):
            content_items.append(
                f"Title: {item.get('title', 'No Title')}\nURL: {item.get('url', 'No URL')}\nContent: {item.get('content')}")

    content_text = "\n\n---\n\n".join(content_items)

    # Trim content if too long
    content_text = trim_prompt(content_text)

    prompt_text = f"""I'm researching the following topic: {query}
    
Here are some search results:

{content_text}

Based on these search results, please provide:
1. A list of key learnings or facts (at least 3, maximum 10)
2. A list of {num_follow_up_questions} follow-up questions to research next

Format your response as JSON with "learnings" and "followUpQuestions" arrays.
User's question is written in Chinese, 需要用中文输出."""

    result = generate_object(
        model_config=model_config,
        system=system_prompt(),
        prompt=prompt_text,
        schema={
            "learnings": ["string"],
            "followUpQuestions": ["string"]
        }
    )

    return {
        "learnings": result.get("learnings", []),
        "followUpQuestions": result.get("followUpQuestions", [])
    }


async def write_final_report(
        prompt: str,
        learnings: List[str],
        visited_urls: List[str]
) -> str:
    """Generate a final research report based on learnings and sources."""
    model_config = get_model()

    prompt_text = f"""I've been researching the following topic: {prompt}

Here are the key learnings from my research:
{' '.join(learnings)}

Here are the sources I've consulted:
{' '.join(visited_urls)}

Please write a comprehensive research report on this topic, incorporating the learnings and citing the sources where appropriate. The report should be well-structured with headings, subheadings, and a conclusion. 
- User's question is written in Chinese, 需要用中文输出.
"""

    response = model_config["client"].chat.completions.create(
        model=model_config["model"],
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content


async def write_final_answer(
        prompt: str,
        learnings: List[str]
) -> str:
    """Generate a concise answer based on learnings."""
    model_config = get_model()

    prompt_text = f"""I've been researching the following topic: {prompt}

Here are the key learnings from my research:
{' '.join(learnings)}

Please provide a concise but comprehensive answer to the original query."""

    response = model_config["client"].chat.completions.create(
        model=model_config["model"],
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content


async def deep_research(
        query: str,
        breadth: int,
        depth: int,
        learnings: List[str] = None,
        visited_urls: List[str] = None,
        on_progress: Callable = None,
) -> Dict[str, List[str]]:
    """
    Perform deep research on a topic by iteratively generating queries,
    processing results, and diving deeper based on findings.
    """
    config = get_config()
    concurrency_limit = config["research"]["concurrency_limit"]

    if learnings is None:
        learnings = []
    if visited_urls is None:
        visited_urls = []

    progress = {
        "currentDepth": depth,
        "totalDepth": depth,
        "currentBreadth": breadth,
        "totalBreadth": breadth,
        "totalQueries": 0,
        "completedQueries": 0,
        "currentQuery": None
    }

    def report_progress(update):
        progress.update(update)
        if on_progress:
            on_progress(progress)

    # Generate SERP queries
    serp_queries = await generate_serp_queries(
        query=query,
        num_queries=breadth,
        learnings=learnings
    )
    report_progress({
        "totalQueries": len(serp_queries),
        "currentQuery": serp_queries[0]['query'] if serp_queries else None
    })

    # Process each query with concurrency limit
    executor = ThreadPoolExecutor(max_workers=concurrency_limit)
    loop = asyncio.get_event_loop()

    async def process_query(serp_query):
        try:
            # Run search in a thread to avoid blocking
            result = await loop.run_in_executor(
                executor,
                lambda: search_client.search(serp_query["query"])
            )

            # Collect URLs from this search
            new_urls = [item.get("url") for item in result.get("data", []) if item.get("url")]
            new_breadth = max(1, breadth // 2)
            new_depth = depth - 1

            # Process search results
            new_learnings_data = await process_serp_result(
                query=serp_query["query"],
                result=result,
                num_follow_up_questions=new_breadth
            )

            all_learnings = learnings + new_learnings_data["learnings"]
            all_urls = visited_urls + new_urls

            # If we have depth remaining, continue research
            if new_depth > 0:
                logger.info(f"Researching deeper, breadth: {new_breadth}, depth: {new_depth}")

                report_progress({
                    "currentDepth": new_depth,
                    "currentBreadth": new_breadth,
                    "completedQueries": progress["completedQueries"] + 1,
                    "currentQuery": serp_query["query"]
                })

                next_query = f"""
                Previous research goal: {serp_query["researchGoal"]}
                Follow-up research directions: {' '.join(new_learnings_data["followUpQuestions"])}
                """.strip()

                return await deep_research(
                    query=next_query,
                    breadth=new_breadth,
                    depth=new_depth,
                    learnings=all_learnings,
                    visited_urls=all_urls,
                    on_progress=on_progress
                )
            else:
                report_progress({
                    "currentDepth": 0,
                    "completedQueries": progress["completedQueries"] + 1,
                    "currentQuery": serp_query["query"]
                })

                return {
                    "learnings": all_learnings,
                    "visitedUrls": all_urls
                }
        except Exception as e:
            logger.error(f"Error running query: {serp_query['query']}: {str(e)}")
            return {
                "learnings": [],
                "visitedUrls": []
            }

    # Process all queries concurrently
    tasks = [process_query(query) for query in serp_queries]
    results = await asyncio.gather(*tasks)

    # Combine results
    all_learnings = []
    all_urls = []

    for result in results:
        all_learnings.extend(result.get("learnings", []))
        all_urls.extend(result.get("visitedUrls", []))

    # Remove duplicates
    unique_learnings = list(dict.fromkeys(all_learnings))
    unique_urls = list(dict.fromkeys(all_urls))

    return {
        "learnings": unique_learnings,
        "visitedUrls": unique_urls
    }


# Synchronous wrapper functions for easier use
def deep_research_sync(query, breadth, depth, learnings=None, visited_urls=None, on_progress=None):
    """Synchronous wrapper for deep_research."""
    return asyncio.run(deep_research(
        query=query,
        breadth=breadth,
        depth=depth,
        learnings=learnings,
        visited_urls=visited_urls,
        on_progress=on_progress
    ))


def write_final_report_sync(prompt, learnings, visited_urls):
    """Synchronous wrapper for write_final_report."""
    return asyncio.run(write_final_report(
        prompt=prompt,
        learnings=learnings,
        visited_urls=visited_urls
    ))


def write_final_answer_sync(prompt, learnings):
    """Synchronous wrapper for write_final_answer."""
    return asyncio.run(write_final_answer(
        prompt=prompt,
        learnings=learnings
    ))
