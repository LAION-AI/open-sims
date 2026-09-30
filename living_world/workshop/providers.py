"""Small REST adapters. No SDK dependency, key persistence, arbitrary base URLs
or fallback to another model/account. Nothing calls a provider at import time.
"""
from dataclasses import dataclass
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


class ProviderError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a credential to a redirect destination.
        return None


def http_json(url, headers, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json", **headers})
    try:
        with build_opener(NoRedirect).open(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ProviderError("Provider response exceeds 2 MB limit")
        return json.loads(raw)
    except HTTPError as exc:
        # Vendor error bodies can echo requests or credentials. Never store them.
        raise ProviderError(f"Provider HTTP {exc.code}; no automatic paid retry") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise ProviderError("Provider network/JSON failure; no automatic paid retry") from None


ENV_KEYS = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    max_output_tokens: int = 4096
    timeout_seconds: int = 90

    def __post_init__(self):
        if self.provider not in ENV_KEYS:
            raise ValueError("Supported API providers: openai, gemini, openrouter")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{1,150}", self.model):
            raise ValueError("Use the exact provider model ID")
        if not 512 <= self.max_output_tokens <= 16384 or not 10 <= self.timeout_seconds <= 180:
            raise ValueError("Output/timeout budget outside supported range")


class ApiProvider:
    external = True

    def __init__(self, config, *, allow_external=False, transport=http_json):
        if not allow_external:
            raise ProviderError("External calls require explicit --allow-external opt-in")
        self.config = config
        self.name = config.provider
        self.model = config.model
        self.transport = transport

    def _headers(self):
        value = os.environ.get(ENV_KEYS[self.name])
        if not value:
            raise ProviderError(f"Set {ENV_KEYS[self.name]} in the process environment; do not paste it into chat")
        return {"x-goog-api-key": value} if self.name == "gemini" else {"Authorization": "Bearer " + value}

    def complete(self, prompt, schema):
        if len(prompt.encode("utf-8")) > 60000:
            raise ProviderError("Authoring context exceeds 60 KB input limit")
        # JSON mode plus independent strict validation supports more models than
        # vendor-specific schema subsets. Incompatible models fail, never reroute.
        instruction = "Return one JSON object only, conforming to this JSON Schema. No markdown or code execution.\n" + json.dumps(schema)
        total_prompt = instruction + "\n" + prompt
        if len(total_prompt.encode("utf-8")) > 80000:
            raise ProviderError("Prompt plus schema exceeds 80 KB input limit")
        cap = self.config.max_output_tokens
        if self.name == "openai":
            url = "https://api.openai.com/v1/responses"
            body = {"model": self.model, "input": total_prompt, "max_output_tokens": cap,
                    "store": False, "text": {"format": {"type": "json_object"}}}
        elif self.name == "gemini":
            slug = self.model.removeprefix("models/")
            url = "https://generativelanguage.googleapis.com/v1beta/models/" + quote(slug, safe="-._") + ":generateContent"
            body = {"contents": [{"role": "user", "parts": [{"text": total_prompt}]}],
                    "generationConfig": {"maxOutputTokens": cap, "responseMimeType": "application/json"}}
        else:
            url = "https://openrouter.ai/api/v1/chat/completions"
            body = {"model": self.model, "messages": [{"role": "user", "content": total_prompt}],
                    "max_tokens": cap, "response_format": {"type": "json_object"},
                    "provider": {"allow_fallbacks": False, "require_parameters": True}}
        data = self.transport(url, self._headers(), body, self.config.timeout_seconds)
        try:
            if self.name == "openai":
                if data.get("status") != "completed":
                    raise ProviderError("OpenAI result incomplete; output budget/refusal must be reviewed")
                content = "".join(c["text"] for item in data["output"] if item.get("type") == "message"
                                  for c in item["content"] if c.get("type") == "output_text")
            elif self.name == "gemini":
                choice = data["candidates"][0]
                if choice.get("finishReason") != "STOP":
                    raise ProviderError("Gemini result incomplete or blocked")
                content = "".join(p.get("text", "") for p in choice["content"]["parts"] if not p.get("thought"))
            else:
                choice = data["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ProviderError("OpenRouter result incomplete or blocked")
                content = choice["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("Expected object")
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Provider did not return a complete JSON object") from None
        usage = data.get("usage", data.get("usageMetadata", {}))
        # Only numeric token counts, not arbitrary provider response fields.
        usage = {k: v for k, v in usage.items() if isinstance(v, (int, float)) and "token" in k.lower()}
        return parsed, usage

    def models(self):
        headers = self._headers()
        if self.name == "gemini":
            result, token = [], None
            for _ in range(20):
                params = {"pageSize": 1000}
                if token:
                    params["pageToken"] = token
                data = self.transport("https://generativelanguage.googleapis.com/v1beta/models?" + urlencode(params), headers)
                result += [{"id": m["name"].removeprefix("models/"), "name": m.get("displayName", m["name"])}
                           for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
                token = data.get("nextPageToken")
                if not token:
                    return result
            raise ProviderError("Model list pagination exceeded bound")
        url = "https://api.openai.com/v1/models" if self.name == "openai" else "https://openrouter.ai/api/v1/models"
        data = self.transport(url, headers)
        return [{"id": m["id"], "name": m.get("name", m["id"]),
                 "pricing": m.get("pricing"), "supported_parameters": m.get("supported_parameters", [])}
                for m in data["data"]]

    def verify_model(self):
        selected = self.model.removeprefix("models/") if self.name == "gemini" else self.model
        if selected not in {m["id"] for m in self.models()}:
            raise ProviderError("Selected model is absent from the provider's current model list; no substitution made")


class DemoProvider:
    """Deterministic integration fixture, explicitly NOT a language model."""
    external = False
    name = "offline-fixture"
    model = "not-an-llm"

    def complete(self, prompt, schema):
        task = json.loads(prompt.split("TASK_JSON\n", 1)[1])
        suffix = re.sub(r"[^a-z0-9_]", "_", task["task_id"])[-20:]
        if schema.get("title") == "GapProposal":
            return {"title": "Leseplatz im Quartier", "missing": ["Kompakter Zeitschriftentisch"],
                    "rationale": "Eine kleine Leseecke ergänzt die Bibliothek mit einer erreichbaren Ablage.",
                    "acceptance": ["Bedienkante frei", "In vier Türorientierungen platzierbar"]}, {}
        obj, room = "ext_reading_table_" + suffix, "ext_reading_corner_" + suffix
        return {"schema_version": 1, "id": "pack_reading_" + suffix, "title": "Leseecke · Offline-Prüfbeispiel",
                "rationale": "Deterministische Testdaten zum Erproben der Pipeline, kein KI-Entwurf.",
                "objects": [{"id": obj, "name": "Zeitschriftentisch", "w": 2, "h": 1,
                             "wall": False, "tall": False, "front": True, "extra_access": [],
                             "actions": ["read", "inspect"], "note": "Niedrige Ablage mit freier Vorderkante.",
                             "pixels": [{"x": 1, "y": 2, "w": 46, "h": 20, "color": "#ad8c64"},
                                        {"x": 3, "y": 3, "w": 42, "h": 15, "color": "#dcc397"},
                                        {"x": 8, "y": 6, "w": 13, "h": 9, "color": "#f4ecd4"},
                                        {"x": 26, "y": 6, "w": 12, "h": 8, "color": "#92aaa0"}]}],
                "rooms": [{"id": room, "name": "Kleine Leseecke", "width": 7, "height": 7,
                           "min_width": 6, "min_height": 6, "required": [obj, "armchair", "bookshelf"],
                           "optional": ["plant", "floor_lamp"], "note": "Bücher, Sitzplatz, freie Wege."}],
                "buildings": []}, {}
