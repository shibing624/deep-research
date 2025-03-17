#!/usr/bin/env python3
import argparse

from src.config import load_config, get_config
from src.deep_research import deep_research_sync, write_final_report_sync, write_final_answer_sync
from loguru import logger


def run_api(port):
    """Run the FastAPI server"""
    import uvicorn
    config = get_config()
    port = port or config["api"]["port"]
    logger.info(f"Starting API server on port {port}")
    uvicorn.run("src.api:app", host="0.0.0.0", port=port, reload=False)

def run_research(args):
    """Run research directly from command line"""
    logger.info(f"Starting research on query: {args.query}")
    logger.info(f"Parameters: breadth={args.breadth}, depth={args.depth}")

    # Define progress callback
    def progress_callback(progress):
        # Check if this is a step update
        if "step" in progress:
            step = progress["step"]
            message = progress.get("message", "")
            
            if step == "clarification":
                logger.info(f"Step: Clarification - {message}")
            elif step == "planning":
                logger.info(f"Step: Planning - {message}")
            elif step == "direct_answer":
                logger.info(f"Step: Direct Answer - {message}")
            else:
                logger.info(f"Step: {step} - {message}")
            return
        
        # Regular progress update
        depth = progress.get("currentDepth", 0)
        total_depth = progress.get("totalDepth", 1)
        completed = progress.get("completedQueries", 0)
        total = progress.get("totalQueries", 0)
        current = progress.get("currentQuery", "")

        logger.info(f"Progress: Depth {depth}/{total_depth}, Queries {completed}/{total} - Current: {current}")

    # Start the research process
    result = deep_research_sync(
        query=args.query,
        breadth=args.breadth,
        depth=args.depth,
        on_progress=progress_callback
    )
    
    # Check if we need clarification
    if result.get("awaiting_clarification", False):
        questions = result.get("questions", [])
        
        print("\n" + "=" * 50)
        print("CLARIFICATION QUESTIONS")
        print("=" * 50)
        print("\nTo provide more accurate results, please answer these questions:")
        print("(Press Enter to skip a question and use the default assumption)\n")
        
        # Collect user responses
        user_clarifications = {}
        for q in questions:
            key = q.get("key", "")
            question = q.get("question", "")
            default = q.get("default", "")
            
            print(f"\nQ: {question}")
            print(f"Default: {default}")
            
            answer = input("Your answer (or press Enter to skip): ").strip()
            if answer:
                user_clarifications[key] = answer
        
        print("\nProcessing your answers...\n")
        
        # Option to skip all questions
        if not user_clarifications:
            print("You skipped all questions. Proceeding with default assumptions.")
        
        # Continue research with clarifications
        result = deep_research_sync(
            query=args.query,
            breadth=args.breadth,
            depth=args.depth,
            on_progress=progress_callback,
            user_clarifications=user_clarifications
        )

    # Check for error
    if "error" in result:
        logger.error(f"Research error: {result['error']}")
        return
    
    # Check if this was a direct answer (no search needed)
    if not result.get("requires_search", True) and "direct_answer" in result:
        direct_answer = result["direct_answer"]
        
        print("\n" + "=" * 50)
        print(f"DIRECT ANSWER FOR: {args.query}")
        print("=" * 50 + "\n")
        print(direct_answer)
        print("\n" + "=" * 50)
        
        # Save output to file
        output_file = "answer.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(direct_answer)
        
        logger.info(f"Answer saved to {output_file}")
        return

    learnings = result.get("learnings", [])
    visited_urls = result.get("visitedUrls", [])

    logger.info(f"\nResearch complete! Found {len(learnings)} learnings and {len(visited_urls)} sources.")

    # Generate report or answer based on mode
    if args.mode == "report":
        output = write_final_report_sync(
            query=args.query,
            learnings=learnings,
            visited_urls=visited_urls
        )
        output_file = "report.md"
    else:  # answer mode
        output = write_final_answer_sync(
            query=args.query,
            learnings=learnings
        )
        output_file = "answer.txt"

    # Save output to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    logger.info(f"Output saved to {output_file}")

    # Print output to console
    print("\n" + "=" * 50)
    print(f"RESEARCH RESULTS FOR: {args.query}")
    print("=" * 50 + "\n")
    print(output)
    print("\n" + "=" * 50)


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

    # API server command
    api_parser = subparsers.add_parser("api", help="Run the API server")
    api_parser.add_argument(
        "--port", type=int, default=None,
        help="Port to run the API server on (default from config)"
    )

    # Frontend server command
    frontend_parser = subparsers.add_parser("frontend", help="Run the frontend web interface")
    frontend_parser.add_argument(
        "--port", type=int, default=None,
        help="Port to run the frontend server on (default from config: 3000)"
    )

    # Research command
    research_parser = subparsers.add_parser("research", help="Run research directly")
    research_parser.add_argument(
        "query", type=str,
        help="Research query"
    )

    config = get_config()
    default_breadth = config["research"]["default_breadth"]
    default_depth = config["research"]["default_depth"]

    research_parser.add_argument(
        "--breadth", type=int, default=default_breadth,
        help=f"Research breadth - number of search queries per iteration (default: {default_breadth})"
    )
    research_parser.add_argument(
        "--depth", type=int, default=default_depth,
        help=f"Research depth - number of recursive iterations (default: {default_depth})"
    )
    research_parser.add_argument(
        "--mode", choices=["report", "answer"], default="report",
        help="Output mode: detailed report or concise answer (default: report)"
    )

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run the Gradio demo interface")

    # Parse arguments
    args = parser.parse_args()

    # Load configuration
    if args.config:
        load_config(args.config)

    # Execute command
    if args.command == "api":
        run_api(args.port)
    elif args.command == "research":
        run_research(args)
    elif args.command == "demo":
        from src.gradio_chat import run_gradio_demo
        run_gradio_demo()
    else:
        # Default to showing help if no command specified
        parser.print_help()


if __name__ == "__main__":
    main()
