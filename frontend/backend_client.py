"""Helpers for talking to a backend on a free host that goes to sleep (e.g. Render's free plan)."""

import time
import requests

STARTING_CODES = (
    502,
    503,
    504,
)  # what a host returns while the service is still booting


class BackendError(Exception):
    """Custom exception with a user-friendly message."""

    def __init__(self, message, is_retryable=True):
        super().__init__(message)
        self.is_retryable = is_retryable


def fetch_airports(url, attempts=2, timeout=45):
    """Return the airport list, or None if the backend never answered with real data."""
    for i in range(attempts):
        try:
            res = requests.get(url, timeout=timeout)
            if res.ok:
                data = res.json()
                if data:
                    return data
        except Exception:
            pass
        if i < attempts - 1:
            time.sleep(3)
    return None


def post_plan(url, payload, tries=3, timeout=180, wait=10):
    """POST the trip request and return the JSON.

    Raises BackendError with a friendly message on failure.
    """
    last_error = None

    for i in range(tries):
        try:
            res = requests.post(url, json=payload, timeout=timeout)
        except requests.ConnectionError as e:
            last_error = BackendError(
                "Cannot reach the server. It may be starting up. Please wait a moment and try again.",
                is_retryable=True,
            )
        except requests.Timeout as e:
            last_error = BackendError(
                "The server is taking too long to respond. Please try again in a few seconds.",
                is_retryable=True,
            )
        else:
            if res.status_code not in STARTING_CODES:
                # Check for specific error codes
                if res.status_code == 422:
                    # Validation error - not retryable
                    try:
                        detail = res.json().get("detail", "Invalid input")
                    except Exception:
                        detail = "Invalid input"
                    raise BackendError(
                        f"Invalid request: {detail}. Please check your trip details.",
                        is_retryable=False,
                    )
                if res.status_code >= 500:
                    raise BackendError(
                        f"Server error ({res.status_code}). The AI agents may be overloaded. Please try again.",
                        is_retryable=True,
                    )
                res.raise_for_status()
                return res.json()
            else:
                last_error = BackendError(
                    f"Server returned {res.status_code} while starting up.",
                    is_retryable=True,
                )

        if i < tries - 1:
            time.sleep(wait)

    if last_error:
        raise last_error
    raise BackendError("An unknown error occurred while planning your trip.")
