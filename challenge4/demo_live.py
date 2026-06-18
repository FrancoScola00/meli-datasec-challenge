# Python 3.12
r"""Live demo against a REAL OpenRouter endpoint (Challenge 4).

This script makes a real network call and consumes credits/rate limit. It is
intentionally separate from the test suite, which never touches the network. The
output narrates the pipeline so the real work is visible: local PII redaction, then
the call to the third-party LLM with only the redacted text, then the validated label.

Runbook:
  1. Copy the env template and add your key:
       Copy-Item challenge4/.env.example challenge4/.env   # then edit challenge4/.env
     or set the variable in your shell:
       $env:OPENROUTER_API_KEY = "sk-or-v1-..."
  2. Run:
       .\.venv\Scripts\python.exe challenge4\demo_live.py
       .\.venv\Scripts\python.exe challenge4\demo_live.py --text "your text here"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # put challenge4/ on path

from classifier.classify import Classifier  # noqa: E402
from classifier.config import load_settings, load_taxonomy  # noqa: E402
from classifier.llm_client import OpenRouterClient  # noqa: E402
from classifier.redaction import redact  # noqa: E402

_DEFAULT_TEXT = (
    "Ayudame a debuggear el deploy de prod: AWS key AKIAIOSFODNN7EXAMPLE, "
    "server 10.2.4.8, escribime a devops@meli.com"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live OpenRouter classification demo.")
    parser.add_argument("--text", default=_DEFAULT_TEXT, help="Text sample to classify.")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass

    settings = load_settings()
    if not settings.has_api_key:
        print(
            "OPENROUTER_API_KEY not set. Copy challenge4/.env.example to challenge4/.env "
            "and add your key, or set the env var.",
            file=sys.stderr,
        )
        return 2

    taxonomy = load_taxonomy()
    client = OpenRouterClient(settings)
    classifier = Classifier(client, settings, taxonomy)

    print("=" * 72)
    print("Challenge 4 - live data-classification pipeline")
    print("=" * 72)
    print(f"\nINPUT (local only, never sent as-is):\n  {args.text}\n")

    # Step 1 - local PII redaction BEFORE anything leaves the process.
    redacted, counts = redact(args.text)
    print("[1/3] Redacting PII locally (deterministic - nothing sent yet)")
    print(f"      detected : {counts or 'none'}")
    print(f"      redacted : {redacted}\n")

    # Step 2 - only the redacted text is sent to the third-party LLM.
    print(f"[2/3] Sending the REDACTED text to the LLM (model={settings.model}) ...")
    result = classifier.classify(args.text)

    # Step 3 - schema-validated, structured classification.
    print("[3/3] Classification (validated against the taxonomy):\n")
    print(result.model_dump_json(indent=2))
    print(f"\n# tokens used: {client.total_tokens}")
    print(
        "\nThe model only ever saw the redacted text above - the raw key, IP and email\n"
        "never left this machine. That is the leak-prevention guarantee."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
