#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def post_form(url, fields, timeout):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url, token, body, timeout):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_content(payload):
    choices = payload.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(parts)
    results = payload.get("results") or []
    if results and isinstance(results[0], dict):
        return str(results[0].get("generated_text", ""))
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--fallback-model", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--system-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    api_key = sys.stdin.read().strip()
    if not api_key:
        raise SystemExit("IBM API key was not provided on stdin")

    system_text = Path(args.system_file).read_text(encoding="utf-8")
    prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")

    token_data = post_form(
        "https://iam.cloud.ibm.com/identity/token",
        {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        args.timeout,
    )
    token = token_data.get("access_token")
    if not token:
        raise SystemExit("IBM IAM response did not contain access_token")

    endpoint = args.url.rstrip("/") + "/ml/v1/text/chat?version=" + urllib.parse.quote(args.version)
    errors = []
    for model in [args.model, args.fallback_model]:
        body = {
            "model_id": model,
            "project_id": args.project_id,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": 0,
            "max_completion_tokens": args.max_tokens,
        }
        try:
            payload = post_json(endpoint, token, body, args.timeout)
            content = extract_content(payload)
            result = {
                "ok": True,
                "model_id": model,
                "content": content,
                "usage": payload.get("usage"),
                "raw": payload,
            }
            Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(content)
            return
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            errors.append({"model": model, "status": exc.code, "detail": detail[:4000]})
        except Exception as exc:
            errors.append({"model": model, "error": repr(exc)})

    Path(args.output).write_text(
        json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    raise SystemExit("All watsonx model attempts failed")


if __name__ == "__main__":
    main()
