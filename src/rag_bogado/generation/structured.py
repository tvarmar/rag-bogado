"""Bounded local JSON calls for query rewriting and evidence review."""

import json
import time

from rag_bogado.generation.generator import GenerationError


def request_json(generator, prompt, data, schema, *, output_tokens=1024):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
    ]
    if sum(len(m["content"].encode()) for m in messages) + 256 + output_tokens > 8192:
        raise ValueError("Structured request exceeds the context budget")
    started = time.perf_counter()
    response = generator.request(
        "/api/chat",
        {
            "model": generator.model,
            "messages": messages,
            "stream": False,
            "format": schema,
            "keep_alive": "10m",
            "options": {
                "num_ctx": 8192,
                "num_predict": output_tokens,
                "temperature": 0,
                "seed": 42,
            },
        },
    )
    try:
        if not response.get("done") or response.get("done_reason") != "stop":
            raise ValueError("Structured response did not finish")
        parsed = json.loads(response["message"]["content"])
    except (ValueError, KeyError, TypeError) as error:
        raise GenerationError(str(error), response) from error
    return parsed, {
        "wall_seconds": time.perf_counter() - started,
        **{
            key: response[key]
            for key in ("prompt_eval_count", "eval_count", "total_duration")
            if key in response
        },
    }
