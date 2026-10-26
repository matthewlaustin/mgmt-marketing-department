from __future__ import annotations

import gzip
import logging
import time
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests

log = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "PoolGeekProductNamer/0.1 (+https://poolgeek.com)"


def normalize_site(website: str) -> str:
    """Turn 'hayward.com' or 'https://hayward.com/pool' into 'https://hayward.com'."""
    if "://" not in website:
        website = "https://" + website
    parsed = urlparse(website)
    return f"{parsed.scheme}://{parsed.netloc}"


class Fetcher:
    """A polite HTTP client: obeys robots.txt, rate-limits, retries transient errors."""

    def __init__(
        self,
        base_url: str,
        delay: float = 0.5,
        timeout: float = 20.0,
        retries: int = 2,
        user_agent: str = DEFAULT_USER_AGENT,
        respect_robots: bool = True,
        session: requests.Session | None = None,
    ):
        self.base_url = normalize_site(base_url)
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._last_request = 0.0
        self._robots: robotparser.RobotFileParser | None = None
        self.robots_sitemaps: list[str] = []
        if respect_robots:
            self._load_robots()

    def _load_robots(self) -> None:
        resp = self._request(urljoin(self.base_url, "/robots.txt"), check_robots=False)
        if resp is None or resp.status_code != 200:
            return
        rp = robotparser.RobotFileParser()
        rp.parse(resp.text.splitlines())
        self._robots = rp
        self.robots_sitemaps = list(rp.site_maps() or [])
        crawl_delay = rp.crawl_delay(self.user_agent)
        if crawl_delay:
            self.delay = max(self.delay, float(crawl_delay))

    def allowed(self, url: str) -> bool:
        return self._robots is None or self._robots.can_fetch(self.user_agent, url)

    def _throttle(self) -> None:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _request(self, url: str, check_robots: bool = True, **kwargs) -> requests.Response | None:
        if check_robots and not self.allowed(url):
            log.debug("robots.txt disallows %s", url)
            return None
        for attempt in range(self.retries + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                log.debug("GET %s failed: %s", url, exc)
                if attempt < self.retries:
                    time.sleep(2**attempt)
                    continue
                return None
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                retry_after = resp.headers.get("Retry-After", "")
                time.sleep(float(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1))
                continue
            return resp
        return None

    def get(self, url: str, **kwargs) -> requests.Response | None:
        return self._request(urljoin(self.base_url, url), **kwargs)

    def get_json(self, url: str, **kwargs):
        resp = self.get(url, headers={"Accept": "application/json"}, **kwargs)
        if resp is None or resp.status_code != 200:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    def get_text(self, url: str) -> str | None:
        resp = self.get(url)
        if resp is None or resp.status_code != 200:
            return None
        content = resp.content
        if url.endswith(".gz") or content[:2] == b"\x1f\x8b":
            try:
                content = gzip.decompress(content)
            except OSError:
                pass
            return content.decode("utf-8", errors="replace")
        return resp.text
