from crewai.tools import tool
from langchain_community.utilities import SearchApiAPIWrapper
from llm_config import TOOLS_EMBEDDER, STUDENT_INFO_SEARCH

class ProjectTools:

    # search api tool
    @tool("Google Search API Tool")
    def google_search(question: str) -> str:
        """Use this tool to research any information about a given question"""
        search = SearchApiAPIWrapper(engine="google")
        return search.run(question)


    @tool("Google News Search Tool")
    def google_news_search(news_topic: str, locale: str) -> str:
        """Use this tool to find news articles about a given locale"""
        search = SearchApiAPIWrapper(engine="google_news", sort_by='most_recent')
        return search.run(query=news_topic, location=locale)


    @tool("Question Tool")
    def ask_questions(questions: list) -> dict:
        """Use this tool to collect answers for 1 to many questions from the user. Include an explanation for why this question is important, and some examples."""
        responses = {}
        try:
            print("\nPlease answer the following questions:")
            for question in questions:
                response = input(f"\n{question}\nYour response: ")
                responses[question] = response
            return responses
        except Exception as e:
            return f"Error collecting user input: {str(e)}"
