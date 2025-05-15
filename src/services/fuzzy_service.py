# src/services/fuzzy_service.py

from difflib import SequenceMatcher
from typing import List, Dict, Any

def fuzzy_search(
    user_input: str,
    epds: List[Dict[str, Any]],
    columns: List[str],
    top_n: int = 10,
    cutoff: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Sucht in `epds` (Liste von dicts) nach Strings, die `user_input` ähnlich sind.
    columns gibt zusätzliche Felder an, die in den Suchtext mit eingebunden werden.
    Liefert die besten `top_n` EPD-Dictionaries zurück, bei denen die Ähnlichkeit >= cutoff.
    """
    if not user_input or not isinstance(user_input, str):
        return []

    ui = user_input.lower()
    hits = []

    for epd in epds:
        # Baue den zu matchenden Text
        parts = [str(epd.get("name", "") or "")]
        for col in columns:
            parts.append(str(epd.get(col, "") or ""))
        text = " \u23AF ".join(parts).lower()

        # Score berechnen
        try:
            m = SequenceMatcher(None, ui, text, autojunk=False)
            match = m.find_longest_match(0, len(ui), 0, len(text))
            score = match.size / len(ui) if ui else 0.0
        except Exception:
            continue

        if score >= cutoff:
            hits.append((score, epd))

    # sortiere absteigend nach Score und gib nur das Dict zurück
    hits.sort(key=lambda x: x[0], reverse=True)
    return [epd for _, epd in hits[:top_n]]
