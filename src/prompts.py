# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:

Prompts used for deep research functionality.
"""
from datetime import datetime

now = datetime.now().isoformat()

SHOULD_CLARIFY_QUERY_PROMPT = """
请判断以下查询是否需要澄清问题。
一个好的查询应该明确、具体且包含足够的上下文。
如果查询模糊、缺少重要上下文、过于宽泛或包含多个可能的解释，则需要澄清。

对话历史: 
```
{history_context}
```

查询是: ```{query}```

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
- User's question is written in Chinese, 需要用中文输出.
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

- User's question is written in Chinese, 需要用中文输出.

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
- User's question is written in Chinese, 需要用中文输出.

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
- User's question is written in Chinese, 需要用中文输出.

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
EXTRACT_SEARCH_RESULTS_SYSTEM_PROMPT = "You are an expert in extracting relevant information."
EXTRACT_SEARCH_RESULTS_PROMPT = """
User query: ```{query}```

search result(Webpage Content): 
```
{search_results}
```

You are an expert information extractor. Given the user's query, the search query that led to this page,
and the webpage content, extract all pieces of information that are useful for answering the user's query.
User's question is written in Chinese, 需要用中文输出.

Output your response in the following JSON format:
{{
  "extracted_infos": [{{"info": "The extracted content1", "url": "url 1"}}, {{"info": "The extracted content 2", "url": "url 2"}}, ...]
}}

- extracted_infos: The extract content from the webpage contains information that is useful for addressing the query.
- info: The extracted relevant context as plain text.
- url: The URL of the webpage where the information was found.
"""

# Prompt for determining next research steps
RESEARCH_FROM_CONTENT_PROMPT = """
Given the context of a search query and some content that was found based on that query, 
determine what we should search next to further the research. The goal is to identify knowledge 
gaps in the current findings, or to explore other related areas/questions that would provide 
a more complete understanding of the topic.

Query: ```{query}```

Search Plan Step: 
```
{current_step}
```

Current Search Results:
```
{content}
```

What should we search for next? Reply with a JSON object containing the following:
- "nextQueries": a list of up to {next_queries_count} search queries that would help continue the research.
- "learnings": a list of key facts or insights we have learned from the content that help answer the original query, include cite url.

For the next queries, make sure they:
1. Address aspects of the topic that haven't been covered yet
2. Dive deeper into promising subtopics or related areas
3. Are specific enough to yield good search results
4. Build upon what we've learned so far
- User's question is written in Chinese, 需要用中文输出.

Output your response in the following JSON format:
{{
  "nextQueries": ["query 1", "query 2", ...],
  "learnings": [{{"insight": "learning 1", "url": "url 1"}}, {{"insight": "learning 2", "url": "url 2"}}, ...]
}}
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
- User's question is written in Chinese, 需要用中文输出.

Format your response as a valid JSON object with:
{{
  "findings": [{{"finding": "finding 1", "url": "cite url 1"}}, {{"finding": "finding 2", "url": "cite url 2"}}, ...], (key conclusions from the research, and the cite url)
  "gaps": ["gap 1", "gap 2", ...], (areas where more research is needed)
  "recommendations": ["recommendation 1", "recommendation 2", ...] (suggestions for further research directions)
}}
"""

FINAL_REPORT_SYSTEM_PROMPT = f"""You are an expert researcher. Today is {now}. Follow these instructions when responding:
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
- User's question is written in Chinese, 需要用中文输出.
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
