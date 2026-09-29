import pytest

from app.config import Settings
from app.integrations.llm.groq_client import GroqLeadClient
from app.integrations.llm.openai_client import OpenAILeadClient
from app.services.factory import build_llm_client


def test_blank_secrets_are_treated_as_unconfigured() -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key=" ",
        openai_api_key="",
        hubspot_access_token="  ",
    )
    assert settings.groq_api_key is None
    assert settings.openai_api_key is None
    assert settings.hubspot_access_token is None


@pytest.mark.asyncio
async def test_llm_provider_switch_builds_selected_adapter() -> None:
    groq = build_llm_client(Settings(_env_file=None, llm_provider="groq", groq_api_key="test-key"))
    openai = build_llm_client(
        Settings(_env_file=None, llm_provider="openai", openai_api_key="test-key")
    )
    assert isinstance(groq, GroqLeadClient)
    assert isinstance(openai, OpenAILeadClient)
    await groq.aclose()
    await openai.aclose()
