"""Interactive first-run setup for tutr."""

import getpass

from tutr.config import PROVIDERS, TutrConfig, save_config

PROVIDER_MODELS = {
    "gemini": [
        ("gemini/gemini-3-flash-preview", "Gemini 3 Flash (recommended)"),
        ("gemini/gemini-2.0-flash", "Gemini 2.0 Flash"),
        ("gemini/gemini-2.5-pro-preview-06-05", "Gemini 2.5 Pro"),
    ],
    "anthropic": [
        ("anthropic/claude-haiku-4-5-20251001", "Claude Haiku 4.5 (recommended)"),
        ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"),
    ],
    "openai": [
        ("openai/gpt-4o-mini", "GPT-4o Mini (recommended)"),
        ("openai/gpt-4o", "GPT-4o"),
        ("openai/o3-mini", "o3-mini"),
    ],
    "ollama": [
        ("ollama/llama3", "Llama 3"),
        ("ollama/mistral", "Mistral"),
        ("ollama/codellama", "Code Llama"),
    ],
}


def run_setup() -> TutrConfig:
    """Run interactive setup and return the saved config."""
    print("\nWelcome to tutr! Let's get you set up.\n")

    # 1. Select provider
    providers = list(PROVIDERS.keys())
    print("Select your LLM provider:")
    for i, key in enumerate(providers, 1):
        print(f"  {i}. {PROVIDERS[key]['label']}")

    provider = providers[_prompt_choice(len(providers)) - 1]

    # 2. API key (skip for ollama)
    api_key = None
    env_key = PROVIDERS[provider]["env_key"]
    if env_key:
        print(f"\nEnter your {PROVIDERS[provider]['label']} API key:")
        api_key = getpass.getpass("  API key: ").strip()
        if not api_key:
            print("  No API key provided. You can set it later via")
            print(f'  export {env_key}="..."')

    # 3. Select model
    models = PROVIDER_MODELS[provider]
    print("\nSelect a model:")
    for i, (_, label) in enumerate(models, 1):
        print(f"  {i}. {label}")

    model = models[_prompt_choice(len(models)) - 1][0]

    # 4. Save
    config = TutrConfig(provider=provider, model=model, api_key=api_key or None)

    save_config(config)
    print("\nConfiguration saved to ~/.tutr/config.json\n")

    return config


def _prompt_choice(max_val: int) -> int:
    """Prompt user for a numeric choice."""
    while True:
        try:
            raw = input(f"\n  Enter choice (1-{max_val}): ")
            val = int(raw)
            if 1 <= val <= max_val:
                return val
        except (ValueError, EOFError):
            pass
        print(f"  Please enter a number between 1 and {max_val}.")
