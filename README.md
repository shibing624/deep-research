<div align="center">
  <a href="https://github.com/shibing624/deep-research">
    <img src="https://raw.githubusercontent.com/shibing624/deep-research/main/docs/logo.png" height="150" alt="Logo">
  </a>
</div>

-----------------

# Open Deep Research (Python)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![python_version](https://img.shields.io/badge/Python-3.8%2B-green.svg)](requirements.txt)
[![GitHub issues](https://img.shields.io/github/issues/shibing624/deep-research.svg)](https://github.com/shibing624/deep-research/issues)
[![Wechat Group](https://img.shields.io/badge/wechat-group-green.svg?logo=wechat)](#Contact)


**Deep Research**: Python implementation of AI-powered research assistant that performs iterative, deep research on any topic by combining search engines, web scraping, and large language models.


## Features

- **多步深度搜索**：支持可配置的深度（迭代次数）和广度（搜索查询量）
- **智能查询生成**：基于初始问题和已获取的信息自动生成后续查询
- **多种输出格式**：支持简洁回答和详细报告两种输出模式
- **多语言支持**：完全支持中文输入和输出
- **多种使用方式**：
  - 命令行界面
  - Gradio 网页界面（支持流式输出）
  - RESTful API
  - Python 模块直接调用

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

这将执行一个示例研究，生成 query: {中国历史上最伟大的发明是什么？} 的详细报告，并保存到文件[report.md](https://github.com/shibing624/deep-research/blob/main/report.md)中。

output:

![report](https://github.com/shibing624/deep-research/blob/main/docs/report.png)

### Gradio Demo

For a user-friendly interface, run the Gradio demo:

```bash
python main.py demo
```

This will start a web interface where you can enter your research query, adjust parameters, and view results.

![gradio](https://github.com/shibing624/deep-research/blob/main/docs/gradio.png)
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

### Python Module

Or use the module directly:

```python
import asyncio
from src.deep_research import deep_research, write_final_report

async def run_research():
    # Run research
    result = await deep_research(query="特斯拉股票走势分析", breadth=3, depth=2)
    
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

## 后续计划

- 添加更多搜索引擎支持
- 改进查询生成策略
- 增强结果可视化
- 支持更多大语言模型
- 添加文档嵌入和向量搜索功能

## Contact

- Issue(建议)
  ：[![GitHub issues](https://img.shields.io/github/issues/shibing624/deep-research.svg)](https://github.com/shibing624/deep-research/issues)
- 邮件我：xuming: xuming624@qq.com
- 微信我： 加我*微信号：xuming624, 备注：姓名-公司-NLP* 进NLP交流群。

<img src="https://github.com/shibing624/deep-research/blob/main/docs/wechat.jpeg" width="200" />

## Citation

如果你在研究中使用了`deep-research`，请按如下格式引用：

APA:

```
Xu, M. deep-research: Deep Research with LLM (Version 0.0.1) [Computer software]. https://github.com/shibing624/deep-research
```

BibTeX:

```
@misc{Xu_deep_research,
  title={deep-research: Deep Research with LLM},
  author={Xu Ming},
  year={2025},
  howpublished={\url{https://github.com/shibing624/deep-research}},
}
```

## License

授权协议为 [The Apache License 2.0](/LICENSE)，可免费用做商业用途。请在产品说明中附加`deep-research`的链接和授权协议。
## Contribute

项目代码还很粗糙，如果大家对代码有所改进，欢迎提交回本项目，在提交之前，注意以下两点：

- 在`tests`添加相应的单元测试
- 使用`python -m pytest`来运行所有单元测试，确保所有单测都是通过的

之后即可提交PR。

## Acknowledgements

- [dzhng/deep-research](https://github.com/dzhng/deep-research)

Thanks for their great work!