# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:

Prompts used for deep research functionality.
"""

SHOULD_CLARIFY_QUERY_PROMPT = """
请判断以下查询是否需要澄清问题。
一个好的查询应该明确、具体且包含足够的上下文。
如果查询模糊、缺少重要上下文、过于宽泛或包含多个可能的解释，则需要澄清。

对话历史: 
```
{history_context}
```

查询是: ```{query}```

当前日期是{current_date}。

请只回答 "yes" 或 "no"。如果查询已经足够清晰，请回答"no"。
"""

# Prompt for generating follow-up questions
FOLLOW_UP_QUESTIONS_PROMPT = """
You are an expert researcher and I need your help to generate clarifying questions for a given research query.

chat history: 
```
{history_context}
```

The query is: ```{query}```

Based on this query, please generate clarifying questions that would help you better understand what the user is looking for.
For effective questions:
1. Identify ambiguous terms or concepts that need clarification
2. Ask about the scope or timeframe of interest
3. Check if there are specific aspects the user is most interested in
4. Consider what background information might be helpful
5. Ask about intended use of the information (academic, personal interest, decision-making, etc.)

- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。

Format your response as a valid JSON object with the following structure:
{{
  "needs_clarification": true/false (boolean indicating if clarification questions are needed),
  "questions": [
    {{
      "key": "specific_key_1", 
      "question": "The clarifying question text",
      "default": "A reasonable default answer if the user doesn't provide one"
    }},
    ... additional questions ...
  ]
}}

If the query seems clear enough and doesn't require clarification, return "needs_clarification": false with an empty questions array.
For simple factual queries or clear requests, clarification is usually not needed.
"""

# Prompt for processing clarifications
PROCESS_CLARIFICATIONS_PROMPT = """
I'm reviewing a user query with clarification questions and their responses.

Chat history: ```
{history_context}
```

Original query: ```{query}```

Clarification questions and responses:
```
{clarifications}
```

Questions that were not answered:
```
{unanswered_questions}
```

Based on this information, please:
1. Summarize the original query with the additional context provided by the clarifications
2. For questions that were not answered, use reasonable default assumptions and clearly state what you're assuming
3. Identify if this is a simple factual query that doesn't require search
- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。

Format your response as a valid JSON object with the following structure:
{{
  "refined_query": "The refined and clarified query",
  "assumptions": ["List of assumptions made for unanswered questions"],
  "requires_search": true/false (boolean indicating if this query needs web search or can be answered directly),
  "direct_answer": "If requires_search is false, provide a direct answer here, otherwise empty string"
}}
"""

# Prompt for no clarifications needed
PROCESS_NO_CLARIFICATIONS_PROMPT = """
I'm reviewing a user query where they chose not to provide any clarifications.

Chat history: 
```
{history_context}
```

Original query: ```{query}```

The user was asked the following clarification questions but chose not to answer any:
```
{unanswered_questions}
```

Since the user didn't provide any clarifications, please:
1. Analyze the original query as comprehensively as possible
2. Make reasonable assumptions for all ambiguous aspects
3. Determine if this is a simple factual query that doesn't require search
4. If possible, provide a direct answer along with the refined query
- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。

Format your response as a valid JSON object with the following structure:
{{
  "refined_query": "The refined query with all possible considerations",
  "assumptions": ["List of all assumptions made"],
  "requires_search": true/false (boolean indicating if this query needs web search or can be answered directly),
  "direct_answer": "If requires_search is false, provide a comprehensive direct answer here, otherwise empty string"
}}

Since the user chose not to provide clarifications, be as thorough and comprehensive as possible in your analysis and answer.
"""

# Prompt for generating research plan
RESEARCH_PLAN_PROMPT = """
You are an expert researcher creating a flexible research plan for a given query. 

Chat history: 
```
{history_context}
```

QUERY: ```{query}```

Please analyze this query and create an appropriate research plan. The number of steps should vary based on complexity:
- For simple questions, you might need only 1 steps
- For moderately complex questions, 2 steps may be appropriate
- For very complex questions, 3 or more steps may be needed
- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。

Consider:
1. The complexity of the query
2. Whether multiple angles of research are needed
3. If the topic requires exploration of causes, effects, comparisons, or historical context
4. If the topic is controversial and needs different perspectives

Format your response as a valid JSON object with the following structure:
{{
  "assessments": "Brief assessment of query complexity and reasoning",
  "steps": [
    {{
      "step_id": 1,
      "description": "Description of this research step",
      "search_queries": ["search query 1", "search query 2", ...],
      "goal": "What this step aims to discover"
    }},
    ... additional steps as needed ...
  ]
}}

Make each step logical and focused on a specific aspect of the research. Steps should build on each other, 
and search queries should be specific and effective for web search.
"""

# Prompt for extract search results
EXTRACT_SEARCH_RESULTS_SYSTEM_PROMPT = "You are an expert in extracting the most relevant and detailed information from search results."
EXTRACT_SEARCH_RESULTS_PROMPT = """
User query: ```{query}```

search result(Webpage Content): 
```
{search_results}
```

- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。

作为信息提取专家，请从网页内容中提取与用户查询最相关的核心片段。需要提取的内容要求：
1. 包含具体的细节、数据、定义和重要论点，不要使用笼统的总结替代原始的详细内容
2. 保留原文中的关键事实、数字、日期和引用
3. 提取完整的相关段落，而不仅仅是简短的摘要
4. 特别关注可以直接回答用户查询的内容
5. 如果内容包含表格或列表中的重要信息，请完整保留这些结构化数据

Output your response in the following JSON format:
{{
  "extracted_infos": [
    {{
      "info": "核心片段1，包含详细内容、数据和定义等",
      "url": "url 1",
      "relevance": "解释这段内容与查询的相关性"
    }},
    {{
      "info": "核心片段2，包含详细内容、数据和定义等", 
      "url": "url 2",
      "relevance": "解释这段内容与查询的相关性"
    }},
    ...
  ]
}}

- info: 保留原文格式的关键信息片段，包含详细内容而非简单摘要
- url: 信息来源的网页URL
- relevance: 简要说明这段内容如何回答了用户的查询
"""

# Prompt for final research summary
RESEARCH_SUMMARY_PROMPT = """
Based on our research, we've explored the query: ```{query}```

Research Summary by Step:
```
{steps_summary}
```

Please analyze this information and provide:
1. A set of key findings that answer the main query
2. Identification of any areas where the research is lacking or more information is needed
- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。

Format your response as a valid JSON object with:
{{
  "findings": [{{"finding": "finding 1", "url": "cite url 1"}}, {{"finding": "finding 2", "url": "cite url 2"}}, ...], (key conclusions from the research, and the cite url)
  "gaps": ["gap 1", "gap 2", ...], (areas where more research is needed)
  "recommendations": ["recommendation 1", "recommendation 2", ...] (suggestions for further research directions)
}}
"""

FINAL_REPORT_SYSTEM_PROMPT = """You are an expert researcher. Follow these instructions when responding:
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
- User's query is written in Chinese, 需要用中文输出.
- 当前日期是{current_date}。
"""

# Prompt for final report
FINAL_REPORT_PROMPT = """
I've been researching the following query: ```{query}```

Please write a comprehensive research report on this topic.
The report should be well-structured with headings, subheadings, and a conclusion.

[要求]：
- 输出markdown格式的回答。
- [context]是参考资料，回答中需要包含引用来源，格式为 [cite](url) ，其中url是实际的链接。
- 除代码、专名外，你必须使用与问题相同语言回答。

Chat history:
```
{history_context}
```

[context]:
```
{context}
```
"""

# Prompt for final answer
FINAL_ANSWER_PROMPT = """
I've been researching the following query: ```{query}```

详细、专业回答用户的query。

[要求]：
- 输出markdown格式的回答。
- [context]是参考资料，回答中需要包含引用来源，格式为 [cite](url) ，其中url是实际的链接。
- 除代码、专名外，你必须使用与问题相同语言回答。

Chat history: 
```
{history_context}
```

[context]:
```
{context}
```
"""
