from openai import AsyncOpenAI
from typing import Optional
from core.config import settings


class RuntimeAnalysisService:
    """
    Service for getting code analysis from GPT-4o
    """

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key) if api_key != 'your_api_key_here' else None

    async def analyze_code(self, code: str) -> Optional[str]:
        """
        Get runtime analysis for the given code using GPT-4o

        :param code: The code to analyze
        :return: Runtime analysis or None if failed
        """
        if not self.client:
            return None

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a code analysis assistant. Analyze the user given code and ONLY provide a single time complexity rating e.g. O(n^2), O(log n), etc. Nothing else. Do not provide any other data or analysis."},
                    {"role": "user", "content": f"Analyze this code:\n\n```python\n{code}\n```"}
                ],
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting runtime analysis: {e}")
            return None


runtime_analysis_service = RuntimeAnalysisService(settings.OPENAI_API_KEY)
