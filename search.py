import asyncio
import random
from difflib import SequenceMatcher
from typing import Iterable

from googlesearch import search as google_search


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
]


async def randomized_delay() -> None:
    await asyncio.sleep(random.uniform(0.8, 1.8))


def generate_username_variants(full_name: str) -> list[str]:
    parts = [part.strip().lower() for part in full_name.split() if part.strip()]
    if not parts:
        return []
    variants = set()
    first = parts[0]
    last = parts[-1]
    variants.add("".join(parts))
    variants.add(f"{first}{last}")
    variants.add(f"{first}.{last}")
    variants.add(f"{first}_{last}")
    variants.add(f"{first}{last[0]}")
    variants.add(f"{first[0]}{last}")
    for part in parts:
        variants.add(part)
    return sorted(variants)


def score_match(name: str, username: str) -> float:
    return SequenceMatcher(None, name.lower(), username.lower()).ratio()


def _run_google_search(query: str, max_results: int) -> Iterable[str]:
    return google_search(
        query,
        num_results=max_results,
        lang="en",
        user_agent=random.choice(USER_AGENTS),
    )


def _extract_instagram_profiles(results: Iterable[str]) -> list[str]:
    links = []
    for url in results:
        if "instagram.com" not in url:
            continue
        if "/p/" in url or "/reel/" in url or "/tv/" in url:
            continue
        if url.rstrip("/") == "https://www.instagram.com":
            continue
        if "instagram.com/" in url:
            links.append(url.split("?")[0])
    return list(dict.fromkeys(links))


def _extract_instagram_posts(results: Iterable[str]) -> list[str]:
    links = []
    for url in results:
        if "instagram.com/p/" not in url:
            continue
        links.append(url.split("?")[0])
    return list(dict.fromkeys(links))


def _get_username_from_url(url: str) -> str:
    cleaned = url.rstrip("/")
    return cleaned.split("instagram.com/")[-1].split("/")[0]


def search_profiles_sync(full_name: str, max_results: int = 15) -> list[dict]:
    query = f'site:instagram.com "{full_name}"'
    results = _run_google_search(query, max_results)
    profile_links = _extract_instagram_profiles(results)
    scored = []
    for link in profile_links:
        username = _get_username_from_url(link)
        scored.append({
            "link": link,
            "username": username,
            "score": score_match(full_name, username),
        })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def search_posts_sync(keyword: str, max_results: int = 15) -> list[str]:
    query = f'site:instagram.com/p/ "{keyword}"'
    results = _run_google_search(query, max_results)
    return _extract_instagram_posts(results)


async def search_profiles(full_name: str, max_results: int = 15) -> list[dict]:
    await randomized_delay()
    return await asyncio.to_thread(search_profiles_sync, full_name, max_results)


async def search_posts(keyword: str, max_results: int = 15) -> list[str]:
    await randomized_delay()
    return await asyncio.to_thread(search_posts_sync, keyword, max_results)
