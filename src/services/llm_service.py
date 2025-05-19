# src/services/llm_service.py

import re
import json
from typing import List, Dict, Any

from openai import OpenAI
import openai  # nur, um ggf. Exceptions abzufangen

class LLMService:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        timeout: float = 60.0,
        system_prompt: str = (
            "You are an assistant helping to match user requests to EPDs. "
            "Respond ONLY with a valid JSON object. The object must contain "
            "a key 'matches' which is a list of up to 3 match objects, each "
            "with 'uuid', 'name' and 'begruendung'."
        ),
    ):
        # setze global (falls du openai.* direkt nutzt)
        openai.api_key = api_key

        # dedizierter HTTP-Client
        self.client        = OpenAI(api_key=api_key, timeout=timeout)
        self.model         = model
        self.system_prompt = system_prompt

    def call(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.5
    ) -> str:
        """
        Sendet den Prompt zusammen mit der system_message an die OpenAI-API
        und gibt den rohen String zurück.
        """
        messages = [
            {"role": "system",  "content": self.system_prompt},
            {"role": "user",    "content": prompt}
        ]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            # choices[0] sollte immer da sein
            return resp.choices[0].message.content.strip()


        except openai.AuthenticationError:  # Direkt die importierte Klasse verwenden

            return json.dumps({"error": "OpenAI Authentifizierung fehlgeschlagen. API Key prüfen!"})

        except openai.RateLimitError:  # Direkt die importierte Klasse verwenden

            return json.dumps({"error": "OpenAI Rate Limit erreicht."})

        except openai.BadRequestError as e:  # Direkt die importierte Klasse verwenden

            # `e.body` könnte nützliche Details enthalten, falls vorhanden

            detail = getattr(e, "body", {}).get("message", str(e)) if hasattr(e, "body") and isinstance(e.body,
                                                                                                        dict) else str(
                e)

            return json.dumps({"error": f"OpenAI Bad Request: {detail}"})

        except openai.APIConnectionError as e:  # Direkt die importierte Klasse verwenden

            return json.dumps({"error": f"Verbindung zur OpenAI API fehlgeschlagen: {e}"})

        except openai.APITimeoutError:  # Direkt die importierte Klasse verwenden

            return json.dumps({"error": "OpenAI API Anfrage Timeout."})

        except openai.APIError as e:  # Oberklasse für andere API-Fehler

            return json.dumps({"error": f"Allgemeiner OpenAI API Fehler: {e}"})

        except Exception as e:  # Für alle anderen, unerwarteten Fehler

            # Optional: Hier den vollen Traceback loggen für Debugging-Zwecke

            # import traceback

            # traceback.print_exc()

            return json.dumps({"error": f"Unerwarteter Fehler bei der LLM-Kommunikation: {type(e).__name__} - {e}"})

    def parse_matches(self, llm_raw: str) -> List[Dict[str, Any]]:
        """
        Extrahiert die Liste unter 'matches' aus dem rohen LLM-Output.
        Unterstützt sowohl:
          {"matches": [ {...}, ... ]}
        als auch numerisch indizierte Objekte:
          {"0": {...}, "1": {...}, ...}
        """
        # Falls mit ```json …``` gefencet
        m = re.search(r"```json\s*([\s\S]*?)```", llm_raw)
        payload = m.group(1).strip() if m else llm_raw

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ungültiges JSON im LLM-Output: {e}")

        if isinstance(data, dict) and "matches" in data and isinstance(data["matches"], list):
            return data["matches"]

        if isinstance(data, dict) and all(k.isdigit() for k in data.keys()):
            return [data[k] for k in sorted(data, key=int)]

        # Fallback: nichts gefunden
        return []
