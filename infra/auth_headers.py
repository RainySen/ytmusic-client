import time
from hashlib import sha1

YTM_ORIGIN = "https://music.youtube.com"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def session_id(cookies: dict[str, str]) -> str:
    return cookies.get("__Secure-3PAPISID") or cookies.get("SAPISID", "")


def parse_cookie_string(value: str) -> dict[str, str]:
    cookies = {}
    for pair in value.split(";"):
        name, sep, val = pair.strip().partition("=")
        if sep and name:
            cookies[name] = val
    return cookies


# login cabeceras sesion
def headers_from_cookies(cookies: dict[str, str], *, user_agent: str | None = None, authuser: str = "0") -> dict[str, str]:
    sapisid = session_id(cookies)
    timestamp = str(int(time.time()))
    digest = sha1(f"{timestamp} {sapisid} {YTM_ORIGIN}".encode()).hexdigest()
    return {
        "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        "x-goog-authuser": authuser,
        "authorization": f"SAPISIDHASH {timestamp}_{digest}",
        "user-agent": user_agent or _USER_AGENT,
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "content-type": "application/json",
        "content-encoding": "gzip",
        "origin": YTM_ORIGIN,
    }
