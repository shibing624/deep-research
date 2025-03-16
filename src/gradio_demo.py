import gradio as gr
import asyncio
import time
from loguru import logger

from .config import get_config
from .deep_research import deep_research_sync, write_final_report, write_final_answer
from .providers import get_model


def run_gradio_demo():
    """Run the Gradio demo interface"""

    def research_and_generate(
            query: str,
            breadth: int,
            depth: int,
            output_mode: str,
            progress=gr.Progress()
    ):
        """
        Run research and generate report/answer
        
        Args:
            query: Research query
            breadth: Research breadth
            depth: Research depth
            output_mode: "report" or "answer"
            progress: Gradio progress indicator
        """
        progress(0, desc="Starting research...")

        # Progress callback for updating the UI
        def progress_callback(progress_data):
            current_depth = progress_data["currentDepth"]
            total_depth = progress_data["totalDepth"]
            completed = progress_data["completedQueries"]
            total = progress_data["totalQueries"] or 1  # Avoid division by zero
            current = progress_data["currentQuery"]

            # Calculate overall progress (0-1)
            depth_progress = (total_depth - current_depth) / total_depth
            query_progress = completed / total
            overall = (depth_progress + query_progress) / 2

            progress(overall, desc=f"Depth {current_depth}/{total_depth}, Query {completed}/{total}: {current}")

        # Run the research
        try:
            result = deep_research_sync(
                query=query,
                breadth=breadth,
                depth=depth,
                on_progress=progress_callback
            )

            learnings = result["learnings"]
            visited_urls = result["visitedUrls"]

            progress(0.9, desc="Generating final output...")

            # Generate the final output based on mode
            if output_mode == "report":
                # Use the synchronous wrapper for the final report
                final_output = asyncio.run(write_final_report(
                    prompt=query,
                    learnings=learnings,
                    visited_urls=visited_urls
                ))
            else:
                # Use the synchronous wrapper for the final answer
                final_output = asyncio.run(write_final_answer(
                    prompt=query,
                    learnings=learnings
                ))

            progress(1.0, desc="Complete!")

            return final_output, "\n\n".join([f"- {learning}" for learning in learnings]), "\n".join(
                [f"- {url}" for url in visited_urls])

        except Exception as e:
            logger.error(f"Error in research: {str(e)}")
            return f"Error: {str(e)}", "", ""

    # Create the Gradio interface with custom CSS
    with gr.Blocks(
        title="Deep Research", 
        theme=gr.themes.Soft(),
        css="""
        .header-container {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        .header-icon {
            font-size: 2.5rem;
        }
        .title {
            text-align: center;
            margin-bottom: 1rem;
        }
        .subtitle {
            text-align: center;
            margin-bottom: 2rem;
            color: #666;
        }
        .footer {
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-size: 0.8rem;
            opacity: 0.7;
        }
        .icon-text {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        """
    ) as demo:
        with gr.Row():
            with gr.Column():
                gr.HTML("""
                <div class="header-container">
                    <div class="header-icon">🔍</div>
                    <div>
                        <h1 style="margin: 0;">Deep Research</h1>
                        <p style="margin: 0;">AI-powered research assistant that performs iterative, deep research on any topic.</p>
                    </div>
                </div>
                """)
        with gr.Row():
            with gr.Column(scale=1):
                query_input = gr.Textbox(
                    label="📝 研究问题",
                    placeholder="输入您想要研究的问题...",
                    lines=3
                )

                with gr.Row():
                    config = get_config()
                    default_breadth = config["research"]["default_breadth"]
                    default_depth = config["research"]["default_depth"]

                    breadth_input = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=default_breadth,
                        step=1,
                        label="🔄 广度 (每次迭代的搜索查询数量)"
                    )

                    depth_input = gr.Slider(
                        minimum=1,
                        maximum=5,
                        value=default_depth,
                        step=1,
                        label="📊 深度 (递归迭代次数)"
                    )

                with gr.Row():
                    output_mode = gr.Radio(
                        choices=["report", "answer"],
                        value="report",
                        label="📄 输出模式",
                        info="报告 (详细) 或 回答 (简洁)"
                    )

                    stream_mode = gr.Checkbox(
                        label="⚡ 流式输出",
                        value=True,
                        info="启用流式输出以实时查看结果"
                    )

                    search_source = gr.Radio(
                        choices=["serper", "mp_search"],
                        value="serper",
                        label="🔍 搜索源",
                        info="选择搜索引擎 (Serper 或 MP Search)"
                    )

                research_button = gr.Button("🚀 开始研究", variant="primary", size="lg")

            with gr.Column(scale=3):
                output = gr.Markdown(label="📋 研究结果")

                with gr.Accordion("🔑 关键发现", open=False):
                    learnings_output = gr.Markdown()

                with gr.Accordion("📚 来源", open=False):
                    sources_output = gr.Markdown()

        # Define the click event with streaming support
        @research_button.click(
            inputs=[query_input, breadth_input, depth_input, output_mode, stream_mode, search_source],
            outputs=[output, learnings_output, sources_output]
        )
        def on_research_click(query, breadth, depth, output_mode, stream, search_source):
            if not query:
                return "⚠️ 请输入研究问题", "", ""

            # 设置搜索源
            config = get_config()
            config["research"]["search_source"] = search_source

            if not stream:
                return research_and_generate(query, breadth, depth, output_mode)

            # For streaming mode, we need to use a generator
            progress_state = {
                "currentDepth": 0,
                "totalDepth": depth,
                "completedQueries": 0,
                "totalQueries": 0,
                "currentQuery": None
            }

            learnings_text = ""
            sources_text = ""

            # Yield initial state
            yield "🔍 正在开始研究...", "", ""

            # Progress callback for updating the UI
            def progress_callback(progress_data):
                nonlocal progress_state
                progress_state.update(progress_data)

            # Run the research (non-streaming part)
            try:
                result = deep_research_sync(
                    query=query,
                    breadth=breadth,
                    depth=depth,
                    on_progress=progress_callback
                )

                learnings = result["learnings"]
                visited_urls = result["visitedUrls"]

                # Format learnings and sources
                learnings_text = "\n\n".join([f"- {learning}" for learning in learnings])
                sources_text = "\n".join([f"- {url}" for url in visited_urls])

                # Yield progress update
                yield "✅ 研究完成，正在生成最终报告...", learnings_text, sources_text

                # Generate the final output based on mode
                model_config = get_model()

                if output_mode == "report":
                    prompt_text = f"""I've been researching the following topic: {query}

Here are the key learnings from my research:
{' '.join(learnings)}

Here are the sources I've consulted:
{' '.join(visited_urls)}

Please write a comprehensive research report on this topic, incorporating the learnings and citing the sources where appropriate. The report should be well-structured with headings, subheadings, and a conclusion.
- User's question is written in Chinese, 需要用中文输出.
"""
                else:
                    prompt_text = f"""I've been researching the following topic: {query}

Here are the key learnings from my research:
{' '.join(learnings)}

Please provide a concise answer to the original query based on these learnings.
- User's question is written in Chinese, 需要用中文输出.
"""

                # Stream the response
                streamed_content = ""

                # Create streaming completion
                response = model_config["client"].chat.completions.create(
                    model=model_config["model"],
                    messages=[
                        {"role": "system",
                         "content": "You are an expert researcher providing detailed, well-structured reports in Chinese."},
                        {"role": "user", "content": prompt_text}
                    ],
                    temperature=0.7,
                    stream=True
                )

                # Process streaming response
                for chunk in response:
                    if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content') and \
                            chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        streamed_content += content_chunk

                        # Yield updated content
                        yield streamed_content, learnings_text, sources_text

                        # Small delay to make streaming visible
                        time.sleep(0.01)

                # Final yield with complete content
                yield streamed_content, learnings_text, sources_text

            except Exception as e:
                logger.error(f"Error in streaming research: {str(e)}")
                yield f"❌ 错误: {str(e)}", "", ""

        # Add examples
        gr.Examples(
            examples=[
                ["中国历史上最伟大的发明是什么？", 3, 2, "report", True, "serper"],
                ["人工智能会在未来十年内取代哪些工作？", 4, 2, "report", True, "serper"],
                ["如何有效学习一门新语言？", 3, 2, "answer", True, "serper"],
            ],
            inputs=[query_input, breadth_input, depth_input, output_mode, stream_mode, search_source]
        )
        
        # Add footer
        gr.HTML("""
        <div class="footer">
            <p>Powered by <a href="https://github.com/shibing624/deep-research" target="_blank">Deep Research</a> | 
            Made with ❤️ by <a href="https://github.com/shibing624" target="_blank">shibing624</a></p>
        </div>
        """)

    # Launch the demo
    demo.launch(server_name="0.0.0.0", share=False)
