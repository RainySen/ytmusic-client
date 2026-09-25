import sys

from infra.auth_headers import session_id

ENGINE_FLAGS_VAR = "QTWEBENGINE_CHROMIUM_FLAGS"
NO_CLIENT_HINTS = "--disable-features=UserAgentClientHint"

_FIREFOX_VERSION = "139.0"
_PLATFORMS = {
    "win32": ("Windows NT 10.0; Win64; x64", "Windows NT 10.0; Win64; x64", "Win32"),
    "darwin": ("Macintosh; Intel Mac OS X 10.15", "Intel Mac OS X 10.15", "MacIntel"),
    "linux": ("X11; Linux x86_64", "Linux x86_64", "Linux x86_64"),
}


# login cookies chromium embebido
class WebSessionCookies:
    def __init__(self):
        self._youtube: dict[str, str] = {}

    @staticmethod
    def _is_youtube(domain: str) -> bool:
        domain = domain.lstrip(".").lower()
        return domain == "youtube.com" or domain.endswith(".youtube.com")

    def add(self, domain: str, name: str, value: str) -> None:
        if self._is_youtube(domain):
            self._youtube[name] = value

    def remove(self, domain: str, name: str) -> None:
        if self._is_youtube(domain):
            self._youtube.pop(name, None)

    def has_session(self) -> bool:
        return bool(session_id(self._youtube))

    def snapshot(self) -> dict[str, str]:
        return dict(self._youtube)


def _platform(platform: str) -> tuple[str, str, str]:
    key = "linux" if platform.startswith("linux") else platform
    return _PLATFORMS.get(key, _PLATFORMS["win32"])


# login google user agent firefox
def google_login_user_agent(platform: str = sys.platform) -> str:
    system = _platform(platform)[0]
    return f"Mozilla/5.0 ({system}; rv:{_FIREFOX_VERSION}) Gecko/20100101 Firefox/{_FIREFOX_VERSION}"


# login google ocultar huella chromium
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


# login google flags chromium
def configure_web_engine_environment(environ: dict) -> None:
    flags = environ.get(ENGINE_FLAGS_VAR, "")
    if NO_CLIENT_HINTS not in flags.split():
        environ[ENGINE_FLAGS_VAR] = (flags + " " + NO_CLIENT_HINTS).strip()
