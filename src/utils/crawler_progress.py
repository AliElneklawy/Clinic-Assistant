"""
Module for tracking website crawler progress
"""

import time
from threading import Lock

# Global dictionary to store crawler progress for different crawl sessions
_crawler_progress = {}
_lock = Lock()


class CrawlerProgress:
    """
    Manages tracking of website crawler progress
    """

    @staticmethod
    def init_progress(crawl_id: str, url: str) -> None:
        """Initialize progress tracking for a new crawl session"""
        with _lock:
            _crawler_progress[crawl_id] = {
                "url": url,
                "status": "initializing",
                "total_urls": 0,
                "crawled_urls": 0,
                "current_url": "",
                "start_time": time.time(),
                "last_update": time.time(),
                "estimated_remaining": None,
                "error": None,
                "logs": [],
            }

    @staticmethod
    def update_progress(
        crawl_id: str,
        status: str = None,
        total_urls: int = None,
        crawled_urls: int = None,
        current_url: str = None,
        error: str = None,
        log_message: str = None,
    ) -> None:
        """Update the progress of a crawl session"""
        if crawl_id not in _crawler_progress:
            return

        with _lock:
            progress = _crawler_progress[crawl_id]

            if status is not None:
                progress["status"] = status

            if total_urls is not None:
                progress["total_urls"] = total_urls

            if crawled_urls is not None:
                progress["crawled_urls"] = crawled_urls

            if current_url is not None:
                progress["current_url"] = current_url

            if error is not None:
                progress["error"] = error
                progress["status"] = "error"

            if log_message is not None:
                progress["logs"].append({"time": time.time(), "message": log_message})
                if len(progress["logs"]) > 100:  # Keep only last 100 logs
                    progress["logs"] = progress["logs"][-100:]

            # Update last_update time
            progress["last_update"] = time.time()

            # Calculate estimated remaining time if we have enough info
            if progress["total_urls"] > 0 and progress["crawled_urls"] > 0:
                elapsed = progress["last_update"] - progress["start_time"]
                urls_per_second = (
                    progress["crawled_urls"] / elapsed if elapsed > 0 else 0
                )
                remaining_urls = progress["total_urls"] - progress["crawled_urls"]

                if urls_per_second > 0:
                    progress["estimated_remaining"] = remaining_urls / urls_per_second
                else:
                    progress["estimated_remaining"] = None

    @staticmethod
    def get_progress(crawl_id: str) -> dict:
        """Get the current progress of a crawl session"""
        with _lock:
            if crawl_id in _crawler_progress:
                progress = _crawler_progress[crawl_id].copy()

                # Calculate percentage
                if progress["total_urls"] > 0:
                    progress["percentage"] = (
                        progress["crawled_urls"] / progress["total_urls"]
                    ) * 100
                else:
                    progress["percentage"] = 0

                # Check for stalled crawl (no updates in 60 seconds)
                if (
                    progress["status"] not in ["completed", "error"]
                    and time.time() - progress["last_update"] > 60
                ):
                    progress["status"] = "stalled"

                return progress
            return None

    @staticmethod
    def cleanup_old_progress(max_age_seconds: int = 3600) -> None:
        """Clean up old progress records to prevent memory leaks"""
        with _lock:
            current_time = time.time()
            to_remove = []

            for crawl_id, progress in _crawler_progress.items():
                if (current_time - progress["last_update"]) > max_age_seconds:
                    to_remove.append(crawl_id)

            for crawl_id in to_remove:
                del _crawler_progress[crawl_id]

    @staticmethod
    def complete_progress(crawl_id: str, success: bool = True) -> None:
        """Mark a crawl session as completed"""
        with _lock:
            if crawl_id in _crawler_progress:
                _crawler_progress[crawl_id]["status"] = (
                    "completed" if success else "error"
                )
                _crawler_progress[crawl_id]["last_update"] = time.time()

                # If successful, ensure crawled_urls equals total_urls
                if success and _crawler_progress[crawl_id]["total_urls"] > 0:
                    _crawler_progress[crawl_id]["crawled_urls"] = _crawler_progress[
                        crawl_id
                    ]["total_urls"]
