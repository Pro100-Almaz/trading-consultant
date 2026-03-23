import anthropic
from app.config import settings

_client = anthropic.Anthropic(api_key=settings.claude_api_key)


def complete(prompt: str, max_tokens: int = 2000) -> str:
    response = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
