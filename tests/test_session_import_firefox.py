from infra.auth_headers import parse_cookie_string
from infra.session_import import session_headers

COOKIES = ("VISITOR_INFO1_LIVE=abc; PREF=f6=40000080&tz=America.Bogota&volume=16; SAPISID=FAKEKEY/xyz; "
           "__Secure-3PAPISID=FAKEKEY/xyz; SID=g.a000fake; LOGIN_INFO=AFmm:QUQ3; wide=1")

WINDOWS = r"""curl.exe ^"https://music.youtube.com/youtubei/v1/account/account_menu?prettyPrint=false^" ^
  --compressed ^
  -X POST ^
  -H ^"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0^" ^
  -H ^"Accept-Language: en-US,en;q=0.9,es-CO;q=0.8^" ^
  -H ^"X-Goog-Visitor-Id: CgtUVGRm^%^3D^%^3D^" ^
  -H ^"Authorization: SAPISIDHASH 1790254536_ff00_u SAPISID1PHASH 1790254536_ff00_u SAPISID3PHASH 1790254536_ff00_u^" ^
  -H ^"X-Goog-AuthUser: 1^" ^
  -H ^"Cookie: VISITOR_INFO1_LIVE=abc; PREF=f6=40000080^&tz=America.Bogota^&volume=16; SAPISID=FAKEKEY/xyz; __Secure-3PAPISID=FAKEKEY/xyz; SID=g.a000fake; LOGIN_INFO=AFmm:QUQ3; wide=1^" ^
  -H ^"TE: trailers^" ^
  --data-raw ^"Vk^â8^ý+^%^¤ff)^Ê Pn^í  ^\^"/^ç^¬F^È^$^&I^ÅyTb­^ú^ïcCU75Z^íj

83 ^×e+/^Õ /^ç^®.^Ì^ÏO^^^ýz^ÈW -H ^\^"bogus: 1^\^" ^\^\^ê/^ç^í ^"
"""

POSIX = r"""curl 'https://music.youtube.com/youtubei/v1/account/account_menu?prettyPrint=false' \
  --compressed \
  -X POST \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0' \
  -H 'X-Goog-Visitor-Id: CgtUVGRm%3D%3D' \
  -H 'Authorization: SAPISIDHASH 1790254536_ff00_u SAPISID1PHASH 1790254536_ff00_u' \
  -H 'X-Goog-AuthUser: 1' \
  -H 'Cookie: VISITOR_INFO1_LIVE=abc; PREF=f6=40000080&tz=America.Bogota&volume=16; SAPISID=FAKEKEY/xyz; __Secure-3PAPISID=FAKEKEY/xyz; SID=g.a000fake; LOGIN_INFO=AFmm:QUQ3; wide=1' \
  -H 'TE: trailers' \
  --data-raw $'\x1f\x8b\x08\x00\x95Vk\x8f\xe28\xfd+%\xa4ff)\xca\x09P\'\xda\xfa\'M\x99\xc6 -H \'bogus: 1\' \x01|\x85\\\x7f'
"""


def check(text):
    headers = session_headers(text)
    assert parse_cookie_string(headers["cookie"]) == parse_cookie_string(COOKIES)
    assert headers["x-goog-authuser"] == "1"
    assert "Firefox/156.0" in headers["user-agent"]
    assert "bogus" not in str(headers) and "SAPISID1PHASH" not in headers["authorization"]
    return headers


def test_firefox_windows_curl_with_binary_body():
    check(WINDOWS)


def test_firefox_posix_curl_with_binary_body():
    check(POSIX)


def test_curl_body_flag_variants_are_ignored():
    for flag in ("--data", "--data-binary", "--data-urlencode", "-d"):
        text = f"curl 'https://x' -H 'cookie: SID=1; SAPISID=z' -H 'x-goog-authuser: 2' {flag} 'a=b -H \"bogus: 1\"'"
        headers = session_headers(text)
        assert headers["x-goog-authuser"] == "2" and "bogus" not in str(headers)
