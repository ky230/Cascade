from cascade.bootstrap.setup import detect_environment
from cascade.bootstrap.system_prompt import build_system_prompt

def test_detect_environment():
    env = detect_environment()
    assert 'python_version' in env
    assert 'platform' in env
    assert 'has_root' in env
    assert isinstance(env['has_root'], bool)

def test_build_system_prompt():
    prompt = build_system_prompt(custom_prompt="Be concise.")
    assert "High-Energy Physics" in prompt
    assert "Be concise." in prompt
