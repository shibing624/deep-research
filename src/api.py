from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from .config import get_config
from .deep_research import deep_research, write_final_answer
from loguru import logger

app = FastAPI(title="Deep Research API")


class ResearchRequest(BaseModel):
    query: str
    depth: Optional[int] = None
    breadth: Optional[int] = None


class ResearchResponse(BaseModel):
    success: bool
    answer: str
    learnings: List[str]
    visitedUrls: List[str]


@app.post("/api/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """
    Perform deep research on a topic and return the results.
    """
    try:
        logger.info("\nStarting research...\n")

        # Get default values from config if not provided
        config = get_config()
        depth = request.depth or config["research"]["default_depth"]
        breadth = request.breadth or config["research"]["default_breadth"]

        # Run the deep research - now using the async version directly
        result = await deep_research(
            query=request.query,
            breadth=breadth,
            depth=depth
        )

        learnings = result["learnings"]
        visited_urls = result["visitedUrls"]

        logger.info(f"\n\nLearnings:\n\n{' '.join(learnings)}")
        logger.info(f"\n\nVisited URLs ({len(visited_urls)}):\n\n{' '.join(visited_urls)}")

        # Generate the final answer - now using the async version directly
        answer = await write_final_answer(
            prompt=request.query,
            learnings=learnings
        )

        return {
            "success": True,
            "answer": answer,
            "learnings": learnings,
            "visitedUrls": visited_urls
        }

    except Exception as e:
        logger.error(f"Error in research API: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during research: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    port = config["api"]["port"]
    uvicorn.run("src.api:app", host="0.0.0.0", port=port, reload=True)
