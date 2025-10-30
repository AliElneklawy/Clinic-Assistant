import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

from scripts import create_folder, get_api_key
from settings.logger import get_logger
from settings.paths import DATA_DIR

logger = get_logger(__name__)


class AsyncCrawler:
    def __init__(
        self,
        base_url,
        domain_name: str = "medical_data",
        client: str = "crawl4ai",
        output_folder: Optional[str] = None,
        max_concurrent_requests: int = 10,
    ):
        """
        Initialize the AsyncCrawler instance.

        Args:
            base_url (str): The starting URL to begin crawling from.
            domain_name (str): The domain name extracted from the base URL, used for naming output files.
            output_folder (Optional[str]): Directory to save the crawled content. Defaults to WEB_CONTENT_DIR if None.
            client (str): The crawling client to use ("crawl4ai" or "scrapegraph"). Defaults to "crawl4ai".
            max_concurrent_requests (int): Maximum number of concurrent URL extraction requests.
        """
        output_folder = (
            Path(output_folder) if output_folder else create_folder.create(DATA_DIR)
        )
        self.output_file = output_folder / f"{domain_name}.txt"
        self.client = client
        self.max_concurrent_requests = max_concurrent_requests

        self.session = None
        self.visited_urls: Set[str] = set()
        self.urls_to_visit: List[tuple[str, int]] = [(base_url, 0)]
        self.base_domain = urlparse(base_url).netloc
        self.crawl_id = str(uuid.uuid4())

        # URL cache for avoiding duplicate processing
        self.url_cache: Set[str] = set()

        if self.client not in ["crawl4ai", "scrapegraph"]:
            logger.warning(
                f"Invalid client type: {self.client}. Defaulting to Crawl4AI."
            )
            self.client = "crawl4ai"

        if self.client == "crawl4ai":
            from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
            from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

            self.browser_config = BrowserConfig()
            self.run_config = CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(),
                exclude_external_images=True,
                exclude_all_images=True,
                exclude_external_links=True,
                exclude_social_media_links=True,
                only_text=True,
                wait_for_images=False,
            )
            self.crawler = None
        elif self.client == "scrapegraph":
            from scrapegraph_py import Client

            self.sgai_client = Client(api_key=get_api_key.get_key("SGAI"))

    async def _init_session(self):
        """Initialize aiohttp session if not already created"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=20)
            connector = aiohttp.TCPConnector(limit=self.max_concurrent_requests)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    async def extract_content(
        self, link: str, webpage_only: bool = False, max_depth: int = None
    ) -> str | Path:
        """
        Scrape content from a URL or list of URLs with fallback between clients.
        """
        await self._init_session()

        url_list = (
            [link]
            if webpage_only
            else await self._extract_urls_fast(max_depth=max_depth)
        )

        with open(self.output_file, "w", encoding="utf-8") as file:
            if self.client == "crawl4ai":
                success_content_dict = await self._batch_crawl4ai(url_list)

                for url, (success, content) in success_content_dict.items():
                    if success:
                        file.write(content)
                        file.write("\n\n")
                    else:
                        logger.debug(f"Falling back to scrapegraph for {url}")
                        success, content = self._sgai_crawler_client(url)
                        if success:
                            file.write(content)
                            file.write("\n\n")
                        else:
                            logger.error(f"Both crawlers failed for {url}")
            else:  # scrapegraph
                for url in url_list:
                    success, content = self._sgai_crawler_client(url)
                    if not success:
                        logger.debug(f"Falling back to crawl4ai for {url}")
                        success, content = await self._crawl4ai_crawler_client(url)

                    if success:
                        file.write(content)
                        file.write("\n\n")
                    else:
                        logger.error(f"Both crawlers failed for {url}")

        return self.output_file

    async def _extract_urls_fast(self, max_pages: int = None, max_depth: int = None):
        """
        Fast URL extraction using concurrent requests and batching.
        """
        await self._init_session()
        pages_crawled = 0

        while self.urls_to_visit and (max_pages is None or pages_crawled < max_pages):
            current_batch = []
            batch_size = min(self.max_concurrent_requests, len(self.urls_to_visit))

            for _ in range(batch_size):
                if not self.urls_to_visit:
                    break

                current_url, current_depth = self.urls_to_visit.pop(0)

                if current_url in self.visited_urls:
                    continue
                if max_depth is not None and current_depth >= max_depth:
                    continue
                if max_pages is not None and pages_crawled >= max_pages:
                    break

                current_batch.append((current_url, current_depth))

            if not current_batch:
                break

            logger.info(f"Processing batch of {len(current_batch)} URLs")

            tasks = [
                self._crawl_page_async(url, depth + 1) for url, depth in current_batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, (url, depth) in enumerate(current_batch):
                result = batch_results[i]

                if isinstance(result, Exception):
                    logger.error(f"Failed to crawl {url}: {result}")
                    continue

                self.visited_urls.add(url)
                pages_crawled += 1

                for link, link_depth in result:
                    if (
                        link not in self.visited_urls
                        and link not in self.url_cache
                        and (link, link_depth) not in self.urls_to_visit
                    ):
                        self.urls_to_visit.append((link, link_depth))
                        self.url_cache.add(link)

        logger.info(
            f"Fast crawling finished. Total pages crawled: {len(self.visited_urls)}"
        )
        return self.visited_urls

    async def _crawl_page_async(self, url: str, depth: int) -> List[tuple[str, int]]:
        """
        Asynchronously crawl a single page to extract linked URLs.
        """
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return []

                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return []

        links = []
        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"])

            if not next_url.startswith(("http://", "https://")):
                continue
            if not self._is_same_domain(next_url):
                continue

            clean_url = self._clean_url(next_url)
            if clean_url not in self.visited_urls and clean_url not in self.url_cache:
                links.append((clean_url, depth))

        logger.debug(f"Found {len(links)} links on {url}")
        return links

    async def _batch_crawl4ai(self, urls: Iterable[str]) -> Dict[str, tuple[bool, str]]:
        """Batch process multiple URLs using Crawl4AI to take advantage of caching."""
        if self.crawler is None:
            self.crawler = AsyncWebCrawler(config=self.browser_config)
            await self.crawler.start()

        result_dict = {}
        session_id = "batch_session"

        try:
            url_list = list(urls)
            batch_size = 10

            for i in range(0, len(url_list), batch_size):
                batch_urls = url_list[i : i + batch_size]

                for url in batch_urls:
                    try:
                        result = await self.crawler.arun(
                            url=url, config=self.run_config, session_id=session_id
                        )
                        if result.success:
                            result_dict[url] = (True, result.markdown.raw_markdown)
                        else:
                            logger.error(
                                f"Crawl4ai failed for {url}: {result.error_message}"
                            )
                            result_dict[url] = (False, "")
                    except Exception as e:
                        logger.error(f"Crawl4ai failed for {url}: {e}")
                        result_dict[url] = (False, "")

            return result_dict
        except Exception as e:
            logger.error(f"Batch crawling failed: {e}")
            return {url: (False, "") for url in urls}

    def _sgai_crawler_client(self, url: str) -> tuple[bool, str]:
        """Scrape a URL using the Scrapegraph client synchronously."""
        try:
            response = self.sgai_client.markdownify(website_url=url)
            if response and "result" in response:
                return True, response["result"]

            logger.error(f"Scrapegraph failed: {url} - Error: couldn't parse url.")
            return False, ""
        except Exception as e:
            logger.error(f"Scrapegraph failed: {url} - Error: {e}")
            return False, ""

    async def _crawl4ai_crawler_client(self, url: str) -> tuple[bool, str]:
        """Scrape a URL using the Crawl4AI client asynchronously."""
        if self.crawler is None:
            self.crawler = AsyncWebCrawler(config=self.browser_config)
            await self.crawler.start()

        try:
            session_id = "session"
            result = await self.crawler.arun(
                url=url, config=self.run_config, session_id=session_id
            )
            if result.success:
                return True, result.markdown.raw_markdown

            logger.error(f"Crawl4ai failed: {url} - Error: {result.error_message}")
            return False, ""
        except Exception as e:
            logger.error(f"Crawl4ai failed: {url} - Error: {e}")
            return False, ""

    def _is_same_domain(self, url: str) -> bool:
        """Check if a URL belongs to the same domain as the base URL."""
        try:
            return urlparse(url).netloc == self.base_domain
        except:
            return False

    def _clean_url(self, url: str) -> str:
        """Clean URL by removing fragments and query parameters."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def get_crawl_id(self) -> str:
        """Get the unique ID for this crawl session"""
        return self.crawl_id

    async def close(self):
        """Close any open connections and resources."""
        if self.session:
            await self.session.close()
        if self.client == "crawl4ai" and self.crawler is not None:
            await self.crawler.close()
        elif self.client == "scrapegraph":
            if hasattr(self.sgai_client, "close"):
                self.sgai_client.close()


async def test():
    link = "https://www.news-medical.net/"

    crawler = AsyncCrawler(link, max_concurrent_requests=15)
    try:
        content_path = await crawler.extract_content(link, max_depth=3)
    finally:
        await crawler.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
