"""Interactive setup and configuration flows for tutr."""

import getpass

from tutr.config import DEFAULT_OLLAMA_HOST, PROVIDERS, TutrConfig, save_config

PROVIDER_MODELS: dict[str, list[tuple[str, str]]] = {
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
    "xai": [
        ("xai/grok-3-mini", "Grok 3 Mini (recommended)"),
        ("xai/grok-3", "Grok 3"),
    ],
    "ollama": [
        ("ollama/llama3", "Llama 3"),
        ("ollama/mistral", "Mistral"),
        ("ollama/codellama", "Code Llama"),
    ],
}


def run_setup() -> TutrConfig:
    """Run first-time interactive setup and return the saved config."""
    print("\nWelcome to tutr! Let's get you set up.\n")
    return run_configure(TutrConfig(), interactive=True)


def run_configure(
    config: TutrConfig,
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    clear_api_key: bool = False,
    ollama_host: str | None = None,
    clear_ollama_host: bool = False,
    show_explanation: bool | None = None,
    update_check_enabled: bool | None = None,
    no_execute: bool | None = None,
    interactive: bool = False,
) -> TutrConfig:
    """Configure tutr interactively or through explicit options."""
    updated = config.model_copy(deep=True)

    if provider is not None:
        _validate_provider(provider)
        updated.provider = provider

    if model is not None:
        updated.model = model

    if provider is None and model is not None and "/" in model:
        inferred_provider = model.split("/", 1)[0]
        if inferred_provider in PROVIDERS:
            updated.provider = inferred_provider

    if updated.provider:
        _validate_provider(updated.provider)

    if updated.provider and (model is not None or provider is not None):
        if not updated.model.startswith(f"{updated.provider}/"):
            updated.model = PROVIDER_MODELS[updated.provider][0][0]

    if clear_api_key:
        updated.api_key = None
    elif api_key is not None:
        stripped = api_key.strip()
        updated.api_key = stripped or None

    if clear_ollama_host:
        updated.ollama_host = None
    elif ollama_host is not None:
        updated.ollama_host = _normalize_ollama_host(ollama_host)

    if show_explanation is not None:
        updated.show_explanation = show_explanation
    if update_check_enabled is not None:
        updated.update_check_enabled = update_check_enabled
    if no_execute is not None:
        updated.no_execute = no_execute

    if updated.provider == "ollama" and not updated.ollama_host:
        updated.ollama_host = DEFAULT_OLLAMA_HOST

    if interactive:
        updated = _run_interactive_configure(updated)

    save_config(updated)
    return updated


def _validate_provider(provider: str) -> None:
    if provider not in PROVIDERS:
        allowed = ", ".join(sorted(PROVIDERS.keys()))
        raise ValueError(f"Unknown provider '{provider}'. Expected one of: {allowed}")


def _run_interactive_configure(config: TutrConfig) -> TutrConfig:
    providers = list(PROVIDERS.keys())
    current_provider = config.provider if config.provider in PROVIDERS else providers[0]

    print("Select your LLM provider:")
    for i, key in enumerate(providers, 1):
        current_marker = " (current)" if key == current_provider else ""
        print(f"  {i}. {PROVIDERS[key]['label']}{current_marker}")

    provider = providers[_prompt_choice(len(providers)) - 1]

    api_key = config.api_key
    env_key = PROVIDERS[provider]["env_key"]
    if env_key:
        print(f"\nEnter your {PROVIDERS[provider]['label']} API key:")
        if api_key:
            print("  Press Enter to keep existing key, or type '-' to clear it.")
            entered = getpass.getpass("  API key: ").strip()
            if entered == "-":
                api_key = None
            elif entered:
                api_key = entered
        else:
            entered = getpass.getpass("  API key: ").strip()
            if entered:
                api_key = entered
            else:
                print("  No API key provided. You can set it later via")
                print(f'  export {env_key}="..."')
    else:
        api_key = None

    ollama_host = config.ollama_host
    if provider == "ollama":
        current_host = ollama_host or DEFAULT_OLLAMA_HOST
        entered_host = input(f"\nOllama host URL [{current_host}] (type '-' to clear): ").strip()
        if entered_host == "-":
            ollama_host = None
        elif entered_host:
            ollama_host = _normalize_ollama_host(entered_host)
        else:
            ollama_host = current_host
    else:
        ollama_host = None

    models = PROVIDER_MODELS[provider]
    print("\nSelect a model:")
    for i, (_, label) in enumerate(models, 1):
        print(f"  {i}. {label}")

    model = models[_prompt_choice(len(models)) - 1][0]

    current_show = bool(config.show_explanation)
    show_explanation = _prompt_yes_no(
        f"\nShow explanations by default? [{'Y/n' if current_show else 'y/N'}]: ",
        default=current_show,
    )

    return TutrConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        ollama_host=ollama_host,
        show_explanation=show_explanation,
        update_check_enabled=config.update_check_enabled,
        no_execute=config.no_execute,
    )


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


def _prompt_yes_no(prompt: str, *, default: bool) -> bool:
    """Prompt user for yes/no with an explicit default."""
    while True:
        try:
            raw = input(prompt).strip().lower()
        except EOFError:
            return default
        if raw == "":
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("  Please enter y or n.")


def _normalize_ollama_host(host: str) -> str:
    normalized = host.strip()
    if not normalized:
        return DEFAULT_OLLAMA_HOST
    if "://" not in normalized:
        normalized = f"http://{normalized}"
    return normalized.rstrip("/")
