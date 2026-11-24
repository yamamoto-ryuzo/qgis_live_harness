"""plugins.qgis.org へプラグイン ZIP を XML-RPC (plugin.upload) でアップロードする。

使い方:
    set QGIS_PLUGINS_USER=<OSGeo ID>
    set QGIS_PLUGINS_PASS=<password>
    python scripts/upload-plugin-zip.py [zip ...]

引数なしの場合は dist/ の最新バージョン ZIP を全てアップロードする。
"""

import getpass
import os
import sys
import xmlrpc.client  # nosec B411  # 接続先は plugins.qgis.org 固定の運用スクリプト
from pathlib import Path

import requests

RPC_URL = "https://plugins.qgis.org/plugins/RPC2/"
DIST = Path(__file__).resolve().parent.parent / "dist"


class _Rpc:
    """requests ベースの最小 XML-RPC クライアント（Basic認証）。

    Python 標準の xmlrpc.client.Transport がサイトの 301 で失敗する
    ため、requests で POST する実装に切り替え。
    """

    def __init__(self, url, user, password):
        self._url = url
        self._auth = (user, password)

    def call(self, method, *params):
        payload = xmlrpc.client.dumps(
            params, method, encoding="utf-8", allow_none=True)
        r = requests.post(
            self._url, data=payload.encode("utf-8"),
            auth=self._auth,
            headers={
                "Content-Type": "text/xml",
                "User-Agent": "qgis-plugin-uploader/1.0",
            },
            timeout=120, allow_redirects=True)
        r.raise_for_status()
        return xmlrpc.client.loads(r.content)[0][0]


def latest_zips():
    """dist/ からプラグインIDごとの最新 ZIP を返す。"""
    zips = {}
    for z in DIST.glob("*.zip"):
        name, _, ver = z.stem.rpartition("-")
        if not name or not ver:
            continue
        key = tuple(int(p) if p.isdigit() else 0 for p in ver.split("."))
        if name not in zips or key > zips[name][0]:
            zips[name] = (key, z)
    return [p for _, p in sorted(zips.values(), key=lambda t: t[1].name)]


def upload(server, path):
    data = path.read_bytes()
    print(f"uploading {path.name} ({len(data)} bytes) ... ", end="", flush=True)
    result = server.call(
        "plugin.upload", xmlrpc.client.Binary(data), True)
    print("OK ->", result)
    return result


def main():
    user = os.environ.get("QGIS_PLUGINS_USER")
    password = os.environ.get("QGIS_PLUGINS_PASS")
    if not user:
        user = input("OSGeo user ID: ").strip()
    if not password:
        password = getpass.getpass("OSGeo password: ")

    server = _Rpc(RPC_URL, user, password)

    zips = [Path(a) for a in sys.argv[1:]] or latest_zips()
    if not zips:
        print("no zips found")
        return 1

    results = {}
    for z in zips:
        try:
            upload(server, z)
            results[z.name] = "OK"
        except xmlrpc.client.Fault as e:
            print(f"FAULT {e.faultCode}: {e.faultString}")
            results[z.name] = f"FAULT: {e.faultString}"
        except Exception as e:
            print(f"ERROR: {e}")
            results[z.name] = f"ERROR: {e}"

    print("\n=== summary ===")
    for name, r in results.items():
        print(f"{name}: {r}")
    return 0 if all(r == "OK" for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
