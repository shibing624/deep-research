# Open Deep Research (Python)

Python implementation of AI-powered research assistant that performs iterative, deep research on any topic by combining search engines, web scraping, and large language models.

## Setup

1. Clone the repository: 

```bash
git clone https://github.com/shibing624/deep-research.git
```
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a configuration file:

```bash
# Copy the example configuration
cp config.example.yaml config.yaml
```

The configuration file allows you to set:
- API keys for OpenAI, Fireworks, and Firecrawl
- Model preferences
- Research parameters (breadth, depth, concurrency)
- API server settings

## Usage

### Command Line Interface

The main.py script provides several ways to use the research assistant:

```bash
# Show help
python main.py --help

# Run research directly from command line
python main.py research "Your research query" --breadth 3 --depth 2 --mode report

# Start the API server
python main.py api --port 3051

# Launch the Gradio demo interface
python main.py demo

# Use a specific configuration file
python main.py --config my-config.yaml research "Your query"
```

### Demo Script

Run演示脚本，查看完整的研究流程：

```bash
python deep_research_demo.py
```

这将执行一个示例研究，生成详细报告和简洁回答，并保存到文件中。

### Gradio Demo

For a user-friendly interface, run the Gradio demo:

```bash
python main.py demo
```

This will start a web interface where you can enter your research query, adjust parameters, and view results.

### API

Run the research assistant API:

```bash
uvicorn src.api:app --reload
```

Then you can use API via HTTP request:

```bash
curl -X POST "http://localhost:3051/api/research" \
  -H "Content-Type: application/json" \
  -d '{"query": "中国历史上最伟大的发明是什么？", "depth": 2, "breadth": 3}'
```

output:

[report.md](https://github.com/shibing624/deep-research/blob/main/report.md)


### Python Module

Or use the module directly:

```python
import asyncio
from src.deep_research import deep_research, write_final_report

async def run_research():
    # Run research
    result = await deep_research(query="Your research query", breadth=3, depth=2)
    
    # Generate report
    report = await write_final_report(
        prompt="Your research query", 
        learnings=result["learnings"], 
        visited_urls=result["visitedUrls"]
    )
    
    print(report)

# Run asynchronous function
asyncio.run(run_research())
```

Note: Since asynchronous functions are used, you need to use `asyncio.run()` or use `await` in an asynchronous context. 