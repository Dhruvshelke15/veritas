import httpx

# USCIS blocks requests with no/bare User-Agent. A realistic browser UA
# string gets through; this was confirmed with a plain curl -A "Mozilla/5.0"
# from a residential IP. Datacenter IPs (e.g. GitHub Actions runners) may
# still be blocked regardless of User-Agent.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class FetchError(RuntimeError):
    pass


def fetch_html(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
) -> str:
    owns_client = client is None
    client = client or httpx.Client(follow_redirects=True, timeout=timeout)
    try:
        response = client.get(url, headers={"User-Agent": user_agent})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc
    finally:
        if owns_client:
            client.close()
    return response.text
