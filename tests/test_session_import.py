import json

import pytest

from infra.browser_cookies import headers_from_cookies, parse_cookie_string, session_id
from infra.concurrency import TaskRunner
from infra.session_import import NO_COOKIE, NO_SESSION, SessionImportError, session_headers
from infra.ytmusic_gateway import GatewayError
from services.auth_service import AuthService

COOKIE = "SID=1; __Secure-3PAPISID=abc123; HSID=x"

CHROME_BASH = """curl 'https://music.youtube.com/youtubei/v1/browse?prettyPrint=false' \\
  -H 'accept: */*' \\
  -H 'cookie: SID=1; __Secure-3PAPISID=abc123; HSID=x' \\
  -H 'x-goog-authuser: 1' \\
  -H 'user-agent: Mozilla/5.0 OperaGX' \\
  --data-raw '{"context":{"client":{"hl":"es"}}}'"""

WINDOWS_CMD = """curl ^"https://music.youtube.com/youtubei/v1/browse?prettyPrint=false^" ^
  -H ^"accept: */*^" ^
  -H ^"cookie: SID=1; __Secure-3PAPISID=abc123; PREF=f6=40000000^&tz=Europe^%^2FMadrid^" ^
  -H ^"x-goog-authuser: 0^" ^
  -H ^"user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge^" ^
  --data-raw ^"^{^\\^"context^\\^":^{^}^}^"
"""

FIREFOX_POSIX = ("curl 'https://music.youtube.com/youtubei/v1/browse' -X POST -H 'User-Agent: Mozilla/5.0 Firefox' "
                 "-H 'Accept: */*' -H 'Cookie: SID=1; __Secure-3PAPISID=abc123' -H 'X-Goog-AuthUser: 0' "
                 "--data-raw '{}'")

POWERSHELL = """$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$session.UserAgent = "Mozilla/5.0"
$session.Cookies.Add((New-Object System.Net.Cookie("SID", "1", "/", ".youtube.com")))
$session.Cookies.Add((New-Object System.Net.Cookie("__Secure-3PAPISID", "abc123", "/", ".youtube.com")))
$session.Cookies.Add((New-Object System.Net.Cookie("elsewhere", "zzz", "/", ".example.com")))
Invoke-WebRequest -UseBasicParsing -Uri "https://music.youtube.com/youtubei/v1/browse" `
-Method "POST" `
-WebSession $session `
-Headers @{
"authority"="music.youtube.com"
  "x-goog-authuser"="2"
  "accept"="*/*"
}"""

HEADER_BLOCK = """POST /youtubei/v1/browse?prettyPrint=false HTTP/2
Host: music.youtube.com
User-Agent: Mozilla/5.0 Firefox
Cookie: SID=1; __Secure-3PAPISID=abc123
X-Goog-AuthUser: 3
"""

CHROME_PAIRS = "cookie:\nSID=1; __Secure-3PAPISID=abc123\nx-goog-authuser:\n2\n"

NETSCAPE = "\n".join([
    "# Netscape HTTP Cookie File",
    ".youtube.com\tTRUE\t/\tTRUE\t1893456000\t__Secure-3PAPISID\tabc123",
    "#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\t1",
    ".example.com\tTRUE\t/\tFALSE\t0\tnope\t1",
    "",
])

COOKIE_EDITOR = json.dumps([
    {"name": "SID", "value": "1", "domain": ".youtube.com"},
    {"name": "__Secure-3PAPISID", "value": "abc123", "domain": ".youtube.com"},
    {"name": "nope", "value": "1", "domain": "example.com"},
])


def cookies_of(headers):
    return parse_cookie_string(headers["cookie"])


def test_chrome_style_bash_curl_keeps_the_browsers_identity():
    headers = session_headers(CHROME_BASH)
    assert cookies_of(headers) == {"SID": "1", "__Secure-3PAPISID": "abc123", "HSID": "x"}
    assert headers["x-goog-authuser"] == "1" and headers["user-agent"] == "Mozilla/5.0 OperaGX"


def test_windows_cmd_curl_with_caret_escapes():
    headers = session_headers(WINDOWS_CMD)
    assert cookies_of(headers) == {"SID": "1", "__Secure-3PAPISID": "abc123", "PREF": "f6=40000000&tz=Europe%2FMadrid"}
    assert headers["user-agent"].endswith("Edge")


def test_firefox_curl_with_mixed_case_headers():
    headers = session_headers(FIREFOX_POSIX)
    assert cookies_of(headers)["__Secure-3PAPISID"] == "abc123"
    assert headers["x-goog-authuser"] == "0" and headers["user-agent"] == "Mozilla/5.0 Firefox"


def test_powershell_copy_only_takes_google_cookies_and_the_account_index():
    headers = session_headers(POWERSHELL)
    assert cookies_of(headers) == {"SID": "1", "__Secure-3PAPISID": "abc123"}
    assert headers["x-goog-authuser"] == "2"


def test_request_headers_copied_as_text():
    headers = session_headers(HEADER_BLOCK)
    assert cookies_of(headers)["SID"] == "1" and headers["x-goog-authuser"] == "3"
    assert headers["user-agent"] == "Mozilla/5.0 Firefox"
    paired = session_headers(CHROME_PAIRS)
    assert cookies_of(paired)["__Secure-3PAPISID"] == "abc123" and paired["x-goog-authuser"] == "2"


def test_a_bare_cookie_string_or_header_line():
    assert cookies_of(session_headers(COOKIE)) == {"SID": "1", "__Secure-3PAPISID": "abc123", "HSID": "x"}
    assert cookies_of(session_headers("Cookie: " + COOKIE))["HSID"] == "x"
    assert cookies_of(session_headers("  \n" + COOKIE + "\n  "))["SID"] == "1"


def test_cookies_txt_and_json_exports_drop_other_sites():
    for text in (NETSCAPE, COOKIE_EDITOR, json.dumps({"cookies": json.loads(COOKIE_EDITOR)})):
        assert cookies_of(session_headers(text)) == {"__Secure-3PAPISID": "abc123", "SID": "1"} or \
            cookies_of(session_headers(text)) == {"SID": "1", "__Secure-3PAPISID": "abc123"}
        assert "nope" not in session_headers(text)["cookie"]


def test_plain_sapisid_cookie_also_signs_in():
    assert session_headers("SID=1; SAPISID=zzz")["cookie"].endswith("SAPISID=zzz")


def test_curl_with_unbalanced_quotes_falls_back_to_a_plain_scan():
    text = "curl 'https://x' -H 'cookie: SID=1; __Secure-3PAPISID=abc123' -H 'x-goog-authuser: 1' --data-raw 'oops"
    headers = session_headers(text)
    assert cookies_of(headers)["__Secure-3PAPISID"] == "abc123" and headers["x-goog-authuser"] == "1"
    assert cookies_of(session_headers("curl 'https://x' -b 'SID=1; __Secure-3PAPISID=q' --data 'unbalanced"))["SID"] == "1"


def test_curl_cookie_flag_and_ansi_c_quoting():
    assert cookies_of(session_headers("curl 'https://x' -b 'SID=1; SAPISID=q'"))["SAPISID"] == "q"
    assert cookies_of(session_headers("curl 'https://x' -H $'cookie: SID=1; SAPISID=q'"))["SID"] == "1"
    assert cookies_of(session_headers("curl https://x --cookie 'SID=1; SAPISID=q' --header 'accept: */*'"))["SID"] == "1"


def test_result_is_a_complete_header_set_even_when_the_paste_had_only_cookies():
    headers = session_headers(COOKIE)
    assert headers["x-goog-authuser"] == "0" and headers["origin"] == "https://music.youtube.com"
    assert headers["authorization"].startswith("SAPISIDHASH ") and "Mozilla" in headers["user-agent"]
    assert headers["content-type"] == "application/json"


def test_session_helpers():
    assert parse_cookie_string("a=1; b=x=y;  ;c") == {"a": "1", "b": "x=y"}
    assert session_id({"__Secure-3PAPISID": "a", "SAPISID": "b"}) == "a" and session_id({"SAPISID": "b"}) == "b"
    assert session_id({}) == ""
    built = headers_from_cookies({"SAPISID": "k"}, user_agent="UA", authuser="4")
    assert built["user-agent"] == "UA" and built["x-goog-authuser"] == "4"


@pytest.mark.parametrize("text, message", [
    ("", "No pegaste nada."),
    (None, "No pegaste nada."),
    ("   \n ", "No pegaste nada."),
    ("hola, esto no es nada útil", NO_COOKIE),
    ("curl 'https://music.youtube.com/x' -H 'accept: */*'", NO_COOKIE),
    ("[]", NO_COOKIE),
    ('{"cookies": "no"}', NO_COOKIE),
    ("SID=1; HSID=x", NO_SESSION),
    ("curl 'https://x' -H 'cookie: SID=1'", NO_SESSION),
])
def test_bad_pastes_get_a_specific_message(text, message):
    with pytest.raises(SessionImportError) as error:
        session_headers(text)
    assert str(error.value) == message


class FakeGateway:
    def __init__(self):
        self.received = []
        self.error = None
        self.is_authenticated = False

    def authenticate(self, headers):
        if self.error:
            raise GatewayError(self.error)
        self.received.append(headers)


@pytest.fixture
def auth(qapp):
    runner = TaskRunner("auth-test", 2)
    gateway = FakeGateway()
    yield AuthService(gateway, runner), gateway
    runner.shutdown()


def test_signing_in_with_pasted_text_authenticates_with_the_normalised_headers(auth, wait_until):
    service, gateway = auth
    seen, changed = [], []
    service.auth_changed.connect(changed.append)
    service.login_with_text(WINDOWS_CMD, lambda ok, error: seen.append((ok, error)))
    assert wait_until(lambda: seen)
    assert seen == [(True, "")] and changed == [True]
    assert cookies_of(gateway.received[0])["__Secure-3PAPISID"] == "abc123"


def test_a_bad_paste_reports_why_without_touching_the_gateway(auth, wait_until):
    service, gateway = auth
    seen = []
    service.login_with_text("nada", lambda ok, error: seen.append((ok, error)))
    assert wait_until(lambda: seen)
    assert seen == [(False, NO_COOKIE)] and gateway.received == []


def test_youtube_refusing_the_session_is_reported(auth, wait_until):
    service, gateway = auth
    gateway.error = "HTTP 401: sesión caducada"
    seen = []
    service.login_with_text(COOKIE, lambda ok, error: seen.append((ok, error)))
    assert wait_until(lambda: seen)
    assert seen == [(False, "HTTP 401: sesión caducada")]
