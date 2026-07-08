import pytest
from linerun.providers import get_provider, MockProvider, OpenAIProvider, AnthropicProvider, GeminiProvider

def test_provider_factory():
    # Test Mock Provider
    prov = get_provider("mock")
    assert isinstance(prov, MockProvider)
    
    # Test OpenAI Provider
    prov_openai = get_provider("openai", api_key="sk-1234")
    assert isinstance(prov_openai, OpenAIProvider)
    assert prov_openai.api_key == "sk-1234"
    assert prov_openai.model == "gpt-4o-mini"
    
    # Test Anthropic Provider
    prov_anthropic = get_provider("anthropic", api_key="sk-ant-1234", model="claude-3")
    assert isinstance(prov_anthropic, AnthropicProvider)
    assert prov_anthropic.api_key == "sk-ant-1234"
    assert prov_anthropic.model == "claude-3"

    # Test Gemini Provider
    prov_gemini = get_provider("gemini", api_key="AIzaSy-1234", model="gemini-1.5-flash")
    assert isinstance(prov_gemini, GeminiProvider)
    assert prov_gemini.api_key == "AIzaSy-1234"
    assert prov_gemini.model == "gemini-1.5-flash"
    
    # Test case insensitivity
    prov_case = get_provider("OpenAI", api_key="sk-1234")
    assert isinstance(prov_case, OpenAIProvider)

    # Test unknown provider raises ValueError
    with pytest.raises(ValueError):
        get_provider("unsupported-llm")

def test_mock_provider_responses():
    # Test preset responses
    prov = MockProvider(responses=["Resp 1", "Resp 2"])
    assert prov.send([]) == "Resp 1"
    assert prov.send([]) == "Resp 2"
    assert prov.send([]) == "Resp 2"  # Repeats last if list exhausted
    
    # Test dynamic responses
    prov_dyn = MockProvider()
    resp = prov_dyn.send([{"role": "user", "content": "Write Hello.txt"}])
    assert "<write_file" in resp
    assert "hello.txt" in resp
