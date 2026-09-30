import sys
from datetime import date

from infra.auth_headers import session_id

ENGINE_FLAGS_VAR = "QTWEBENGINE_CHROMIUM_FLAGS"
NO_CLIENT_HINTS = "--disable-features=UserAgentClientHint"

# firefox ships every 4 weeks; outdated user agents get flagged insecure
_FIREFOX_ANCHOR = (139, date(2025, 5, 27))
_FIREFOX_CYCLE_DAYS = 28


def firefox_version(today: date | None = None) -> str:
    anchor_version, anchor_day = _FIREFOX_ANCHOR
    elapsed = ((today or date.today()) - anchor_day).days
    return f"{anchor_version + max(0, elapsed) // _FIREFOX_CYCLE_DAYS}.0"
_PLATFORMS = {
    "win32": ("Windows NT 10.0; Win64; x64", "Windows NT 10.0; Win64; x64", "Win32"),
    "darwin": ("Macintosh; Intel Mac OS X 10.15", "Intel Mac OS X 10.15", "MacIntel"),
    "linux": ("X11; Linux x86_64", "Linux x86_64", "Linux x86_64"),
}


class WebSessionCookies:
    def __init__(self):
        self._youtube: dict[str, str] = {}
        self._google: dict[str, str] = {}

    @staticmethod
    def _is_site(domain: str, site: str) -> bool:
        domain = domain.lstrip(".").lower()
        return domain == site or domain.endswith("." + site)

    def _bucket(self, domain: str) -> dict[str, str] | None:
        if self._is_site(domain, "youtube.com"):
            return self._youtube
        if self._is_site(domain, "google.com"):
            return self._google
        return None

    def add(self, domain: str, name: str, value: str) -> None:
        bucket = self._bucket(domain)
        if bucket is not None:
            bucket[name] = value

    def remove(self, domain: str, name: str) -> None:
        bucket = self._bucket(domain)
        if bucket is not None:
            bucket.pop(name, None)

    def has_session(self) -> bool:
        return bool(session_id(self._youtube))

    def has_google_session(self) -> bool:
        return bool(session_id(self._google))

    def snapshot(self) -> dict[str, str]:
        return dict(self._youtube)


def _platform(platform: str) -> tuple[str, str, str]:
    key = "linux" if platform.startswith("linux") else platform
    return _PLATFORMS.get(key, _PLATFORMS["win32"])


def google_login_user_agent(platform: str = sys.platform) -> str:
    system = _platform(platform)[0]
    version = firefox_version()
    return f"Mozilla/5.0 ({system}; rv:{version}) Gecko/20100101 Firefox/{version}"


# hide chromium fingerprint from google login
def firefox_disguise_script(platform: str = sys.platform) -> str:
    _, oscpu, navigator_platform = _platform(platform)
    return f"""
(() => {{
  const define = (target, name, value) => {{
    try {{ Object.defineProperty(target, name, {{get: () => value, configurable: true}}); }} catch (e) {{}}
  }};
  define(Navigator.prototype, 'userAgentData', undefined);
  define(Navigator.prototype, 'vendor', '');
  define(Navigator.prototype, 'productSub', '20100101');
  define(Navigator.prototype, 'oscpu', '{oscpu}');
  define(Navigator.prototype, 'platform', '{navigator_platform}');
  define(Navigator.prototype, 'buildID', '20181001000000');
  define(Navigator.prototype, 'webdriver', false);
  try {{ Object.defineProperty(window, 'chrome', {{value: undefined, configurable: true}}); }} catch (e) {{}}
  try {{ Object.defineProperty(window, 'PublicKeyCredential', {{value: undefined, configurable: true}}); }} catch (e) {{}}
}})();
"""


# client hints would reveal chromium
def configure_web_engine_environment(environ: dict) -> None:
    flags = environ.get(ENGINE_FLAGS_VAR, "")
    if NO_CLIENT_HINTS not in flags.split():
        environ[ENGINE_FLAGS_VAR] = (flags + " " + NO_CLIENT_HINTS).strip()
