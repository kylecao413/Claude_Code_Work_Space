import os
import sys
import argparse
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

# Load environment variables from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=API_KEY)

MAX_FILE_SIZE_MB = 10

GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

SYSTEM_INSTRUCTION = """
You are a Principal Software Architect and QA Lead.
Your role is to review code, architecture, and logs with extreme scrutiny.
Focus on:
1. Security vulnerabilities (SQLi, XSS, sensitive data exposure).
2. Robustness (error handling, retries, timeout management).
3. Logic flaws (race conditions, infinite loops, edge cases).
4. Best practices (DRY, SOLID, clean code).

Do not be polite. Be precise, critical, and constructive.
If the code is acceptable, confirm it with "LGTM (Looks Good To Me)" but still list potential improvements.
"""


def exit_with_error(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def validate_path(file_path):
    """Resolve path and ensure it stays within the project directory."""
    resolved = Path(file_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise PermissionError(f"Access denied: path is outside the project directory.")
    size_mb = resolved.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Limit is {MAX_FILE_SIZE_MB} MB.")
    return resolved


def read_text_file(resolved_path):
    """Read a text/code file and return its content."""
    try:
        return resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError("Binary file detected. Please provide a text code file or an image.")


def upload_image(resolved_path):
    """Upload an image to Gemini File API and return the file object."""
    print(f"Uploading image: {resolved_path.name}...", file=sys.stderr)
    return genai.upload_file(path=str(resolved_path), display_name=resolved_path.name)


def ask_senior(file_path, question, model_name="gemini-2.5-pro"):
    resolved = validate_path(file_path)

    mime_type, _ = mimetypes.guess_type(str(resolved))
    is_image = mime_type and mime_type.startswith("image")

    if is_image:
        uploaded = upload_image(resolved)
        prompt_parts = [question, uploaded]
    else:
        content = read_text_file(resolved)
        prompt_parts = [question, f"\n\n--- FILE CONTENT ({resolved.name}) ---\n{content}"]

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=GENERATION_CONFIG,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    response = model.generate_content(prompt_parts)
    if not response.text:
        try:
            feedback = response.prompt_feedback
            block_reason = feedback.block_reason.name
            ratings = {r.category.name: r.probability.name for r in feedback.safety_ratings}
            exit_with_error(f"Model returned empty response. Block reason: {block_reason}. Safety: {ratings}")
        except (AttributeError, IndexError):
            exit_with_error("Model returned empty response with no additional feedback.")
    print(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask the Senior Architect (Gemini) for review.")
    parser.add_argument("file_path", help="Path to the code file or image to review")
    parser.add_argument("question", help="The specific question or review instruction")
    parser.add_argument("--model", default="gemini-2.5-pro",
                        help="Model name (default: gemini-2.5-pro; use gemini-2.5-flash for high-volume/low-priority)")

    args = parser.parse_args()

    try:
        ask_senior(args.file_path, args.question, model_name=args.model)
    except FileNotFoundError as e:
        exit_with_error(str(e))
    except PermissionError as e:
        exit_with_error(str(e))
    except ValueError as e:
        exit_with_error(str(e))
    except google_exceptions.GoogleAPICallError as e:
        exit_with_error(f"API call failed: {e.message}")
    except google_exceptions.RetryError as e:
        exit_with_error(f"API retry exhausted: {e}")
