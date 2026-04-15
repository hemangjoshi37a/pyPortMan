from typing import Any
from dataclasses import dataclass
from providers.nvidia_nim.request import build_request_body
from config.nim import NimSettings

@dataclass
class MockMessage:
    role: str
    content: str

@dataclass
class MockRequest:
    model: str
    messages: list[MockMessage]
    max_tokens: int = 1024
    extra_body: dict[str, Any] = None
    system: str = None
    stop_sequences: list[str] = None
    temperature: float = None
    top_p: float = None
    top_k: int = None

def test_glm():
    print("Testing GLM 4.7 (should NOT have thinking)")
    req = MockRequest(model="z-ai/glm4.7", messages=[MockMessage(role="user", content="hi")])
    nim = NimSettings()
    body = build_request_body(req, nim)
    extra = body.get("extra_body", {})
    if "thinking" in extra or "reasoning_split" in extra:
        print("FAIL: GLM has thinking parameters!")
        print(extra)
    else:
        print("SUCCESS: GLM clean of thinking parameters.")

def test_r1():
    print("\nTesting DeepSeek R1 (SHOULD have thinking)")
    req = MockRequest(model="deepseek-ai/deepseek-r1", messages=[MockMessage(role="user", content="hi")])
    nim = NimSettings()
    body = build_request_body(req, nim)
    extra = body.get("extra_body", {})
    if "thinking" in extra and "reasoning_split" in extra:
        print("SUCCESS: R1 has thinking parameters.")
    else:
        print("FAIL: R1 missing thinking parameters!")
        print(extra)

if __name__ == "__main__":
    test_glm()
    test_r1()
