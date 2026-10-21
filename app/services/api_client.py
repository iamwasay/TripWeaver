import logging
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
async def fetch_json(
    url: str,
    method: str = "GET",
    headers: dict = None,
    params: dict = None,
    json_data: dict = None,
) -> dict:
    """
    Standardized API caller with timeouts and retries.
    """
    # 15-second timeout so the app doesn't hang forever
    timeout = httpx.Timeout(15.0, connect=5.0)

    # Notice exactly 4 spaces before 'async'
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        logger.debug(f"API Request: {method} {url}")

        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(
                    url, headers=headers, params=params, json=json_data
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()  # Raises error for 4xx/5xx status codes
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP Error {e.response.status_code} from {url}: {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error requesting {url}: {str(e)}")
            raise
