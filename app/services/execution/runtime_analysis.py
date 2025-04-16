from typing import Optional

from core.config import settings
from openai import AsyncOpenAI
from pydantic import BaseModel, Field


class RuntimeAnalysis(BaseModel):
    complexity: str = Field(
        description="Time complexity in Big O notation only (e.g. O(n), O(n^2), O(log n)). "
        "Do not include any additional text or explanations."
    )


class RuntimeAnalysisService:
    """
    Service for getting code analysis from GPT-4o
    """

    def __init__(self, api_key: str):
        self.client = (
            AsyncOpenAI(api_key=api_key) if api_key != "your_api_key_here" else None
        )

    async def analyze_code(self, code: str) -> Optional[str]:
        """
        Get runtime analysis for the given code using GPT-4o

        :param code: The code to analyze
        :return: Runtime analysis or None if failed
        """
        if not self.client:
            return None

        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code analysis assistant. Analyze the code and provide ONLY the time complexity in Big O notation (e.g. O(n), O(n^2)). No other text or explanations.",
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this code:\n\n```\n{code}\n```",
                    },
                ],
                response_format=RuntimeAnalysis,
                temperature=0,
            )
            return completion.choices[0].message.parsed.complexity
        except Exception as e:
            print(f"Error getting runtime analysis: {e}")
            return None


runtime_analysis_service = RuntimeAnalysisService(settings.OPENAI_API_KEY)
