from __future__ import annotations

import json
import re
import shlex

from infra.auth_headers import headers_from_cookies, parse_cookie_string, session_id

_GOOGLE_DOMAIN = re.compile(r"youtube|google", re.IGNORECASE)
_HEADER_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s?(.*)$")
_BARE_COOKIE = re.compile(r"^[\w.%-]+=[^\r\n]*$")
_CURL_STRING_ESCAPE = re.compile(r"\$'")
_CURL_BODY = re.compile(r"\s(?:--data(?:-raw|-binary|-ascii|-urlencode)?|-d)[\s=]")

NO_COOKIE = ("No se encontró ninguna cookie en lo que pegaste. Copia la petición completa (cURL) de una "
             "solicitud a music.youtube.com con tu sesión iniciada, o exporta tus cookies con la extensión "
             "Cookie-Editor (JSON).")
NO_SESSION = ("Las cookies no incluyen tu sesión de YouTube (falta «__Secure-3PAPISID»). Asegúrate de haber "
              "iniciado sesión en music.youtube.com y copia de nuevo.")


class SessionImportError(Exception):
    pass


def _wanted_domain(domain: str | None) -> bool:
    return not domain or bool(_GOOGLE_DOMAIN.search(domain))


def _cookie_header(cookies: dict[str, str]) -> dict[str, str]:
    return {"cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())} if cookies else {}


# login cookies json
def _from_json(text: str) -> dict[str, str] | None:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, dict):
        data = data.get("cookies")
    if not isinstance(data, list):
        return None
    return _cookie_header({c["name"]: str(c["value"]) for c in data
                           if isinstance(c, dict) and "name" in c and "value" in c
                           and _wanted_domain(c.get("domain"))})


# login cookies txt
def _from_netscape(text: str) -> dict[str, str] | None:
    cookies: dict[str, str] = {}
    for line in text.splitlines():
        line = line.rstrip("\r")
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 7 and _wanted_domain(fields[0]):
            cookies[fields[5]] = fields[6]
    return _cookie_header(cookies) or None


# login powershell
def _from_powershell(text: str) -> dict[str, str] | None:
    if "Invoke-WebRequest" not in text and "System.Net.Cookie" not in text:
        return None

    def unescape(value: str) -> str:
        return re.sub(r"`(.)", r"\1", value)

    headers: dict[str, str] = {}
    block = re.search(r"-Headers\s+@\{(.*?)\}", text, re.DOTALL)
    for key, value in re.findall(r'"([^"]+)"\s*=\s*"((?:[^"`]|`.)*)"', block.group(1) if block else ""):
        headers[key.strip().lower()] = unescape(value)
    cookies = {}
    for name, value, domain in re.findall(
            r'System\.Net\.Cookie\(\s*"([^"]+)"\s*,\s*"((?:[^"`]|`.)*)"(?:\s*,\s*"[^"]*"\s*,\s*"([^"]*)")?', text):
        if _wanted_domain(domain):
            cookies[name] = unescape(value)
    if cookies:
        headers.setdefault("cookie", _cookie_header(cookies)["cookie"])
    return headers


# login curl bash cmd
def _from_curl(text: str) -> dict[str, str] | None:
    if "curl" not in text.lower():
        return None
    flat = re.sub(r"\^\r?\n", " ", text)
    flat = re.sub(r"\\\r?\n", " ", flat)
    if '^"' in flat:
        flat = re.sub(r"\^(.)", r"\1", flat)
    body = _CURL_BODY.search(flat)
    if body:
        flat = flat[:body.start()]
    flat = _CURL_STRING_ESCAPE.sub("'", flat)
    headers: dict[str, str] = {}

    def add(raw: str) -> None:
        key, sep, value = raw.partition(":")
        if sep and key.strip():
            headers[key.strip().lower()] = value.strip()

    try:
        tokens = shlex.split(flat)
    except ValueError:
        for _, raw in re.findall(r"(?:-H|--header)\s+(['\"])(.*?)\1", flat):
            add(raw)
        cookie = re.search(r"(?:--cookie|-b)\s+(['\"])(.*?)\1", flat)
        if cookie:
            headers["cookie"] = cookie.group(2)
        return headers
    for position, token in enumerate(tokens[:-1]):
        following = tokens[position + 1]
        if token in ("-H", "--header"):
            add(following)
        elif token in ("-b", "--cookie"):
            headers["cookie"] = following
    return headers


def _from_header_block(text: str) -> dict[str, str] | None:
    headers: dict[str, str] = {}
    lines = [line.strip() for line in text.splitlines()]
    position = 0
    while position < len(lines):
        match = _HEADER_LINE.match(lines[position])
        if match:
            key, value = match.group(1).lower(), match.group(2)
            if not value and position + 1 < len(lines) and lines[position + 1] and \
                    not _HEADER_LINE.match(lines[position + 1]):
                position += 1
                value = lines[position]
            headers[key] = value
        position += 1
    return headers or None


def _from_bare_cookie(text: str) -> dict[str, str] | None:
    return {"cookie": text} if _BARE_COOKIE.match(text) else None


_READERS = (_from_json, _from_netscape, _from_powershell, _from_curl, _from_header_block, _from_bare_cookie)


def cookies_to_headers(cookies: dict[str, str], *, user_agent: str | None = None, authuser: str = "0") -> dict[str, str]:
    if not session_id(cookies):
        raise SessionImportError(NO_SESSION)
    return headers_from_cookies(cookies, user_agent=user_agent, authuser=authuser)


# login pegar curl cookies
def session_headers(text: str | None) -> dict[str, str]:
    text = (text or "").strip()
    if not text:
        raise SessionImportError("No pegaste nada.")
    headers: dict[str, str] = {}
    for reader in _READERS:
        found = reader(text)
        if found and found.get("cookie"):
            headers = found
            break
    cookie = headers.get("cookie", "")
    if not cookie:
        raise SessionImportError(NO_COOKIE)
    return cookies_to_headers(parse_cookie_string(cookie), user_agent=headers.get("user-agent"),
                              authuser=headers.get("x-goog-authuser") or "0")
