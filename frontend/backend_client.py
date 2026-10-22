"""Helpers for talking to a backend on a free host that goes to sleep (e.g. Render's free plan)."""

import time
import requests

STARTING_CODES = (
    502,
    503,
    504,
)  # what a host returns while the service is still booting


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

    Retries on connection errors, timeouts and 502/503/504 (server still starting).
    Other errors, such as a 422 for a bad request, are raised straight away.
    """
    last = None
    for i in range(tries):
        try:
            res = requests.post(url, json=payload, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
        else:
            if res.status_code not in STARTING_CODES:
                res.raise_for_status()
                return res.json()
            last = RuntimeError(f"Server returned {res.status_code} while starting up")
        if i < tries - 1:
            time.sleep(wait)
    raise last
