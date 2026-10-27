"""プラグイン配布ZIPビルダー。

qgis-plugin/<id>/ を <id>/ をトップレベルに持つZIPとして dist/ に出力する。
plugins.qgis.org へのアップロード用。

使い方:
    python scripts/build-plugin-zip.py geo_search            # 個別
    python scripts/build-plugin-zip.py geo_search geo_excel  # 複数
    python scripts/build-plugin-zip.py --all                 # 全プラグイン
    python scripts/build-plugin-zip.py --list                # 対象一覧
    python scripts/build-plugin-zip.py --check geo_search    # チェックのみ

git の追跡ファイルのみを同梱する(sync_bundle_plugins.py と同じ方式。
未追跡のキャッシュ・生成物は混入しない)。gitが使えない環境では
rglob + 除外リストにフォールバックする。

ビルド前に plugins.qgis.org のアップロード要件に基づくチェックを実行
(失敗時はZIPを作らない。`--force` で強行、`--skip-net` でリンク
疎通チェックを省略、`--check` でチェックのみ)。
QGISでの動作確認・email同意の2項目は機械判定不可のため手動確認項目。
"""

import argparse
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_ROOT = REPO_ROOT / "qgis-plugin"
DEFAULT_OUTDIR = REPO_ROOT / "dist"

# gitフォールバック時の除外パターン(ディレクトリ名/拡張子)
# "docs/" はドキュメントサイト(HTML)でありプラグイン配布物ではないため
# ZIPから除外する
EXCLUDE_DIRS = {"__pycache__", ".git", ".pytest_cache", "node_modules",
                "docs"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}

# plugins.qgis.org のスキャナが検出する開発者同梱設定ファイル。
# ZIPに含めると 'Validated (configured)' になり管理者レビュー対象になる
# ため同梱しない(ローカルでのスキャン/整形用としてのみrepoに残す)。
EXCLUDE_SCANNER_CONFIGS = {".bandit", ".flake8", ".secrets.baseline"}


def list_plugins() -> list[str]:
    """metadata.txt を持つ qgis-plugin 直下のフォルダ名を列挙。"""
    return sorted(
        d.name
        for d in PLUGINS_ROOT.iterdir()
        if d.is_dir() and (d / "metadata.txt").is_file()
    )


def plugin_version(plugin_dir: Path) -> str:
    """metadata.txt の version= を読む。"""
    for line in (plugin_dir / "metadata.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*version\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1)
    return "0.0.0"


def tracked_files(plugin_id: str) -> list[Path]:
    """git追跡ファイル(相対パス)。失敗時はrglobフォールバック。"""
    rel = f"qgis-plugin/{plugin_id}"
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", rel],
            cwd=REPO_ROOT, capture_output=True, check=True,
        ).stdout
        files = [Path(p.decode("utf-8")) for p in out.split(b"\0") if p]
        files = [
            p for p in files
            if p.name not in EXCLUDE_SCANNER_CONFIGS
            and not any(part in EXCLUDE_DIRS for part in p.parts)
            and p.suffix.lower() not in EXCLUDE_SUFFIXES
        ]
        if files:
            return files
    except Exception:
        pass
    plugin_dir = PLUGINS_ROOT / plugin_id
    return [
        p.relative_to(REPO_ROOT)
        for p in sorted(plugin_dir.rglob("*"))
        if p.is_file()
        and p.name not in EXCLUDE_SCANNER_CONFIGS
        and not any(part in EXCLUDE_DIRS for part in p.parts)
        and p.suffix.lower() not in EXCLUDE_SUFFIXES
    ]


def metadata_map(plugin_dir: Path) -> dict[str, str]:
    """metadata.txt を key=value の dict にパース(複数行セクションは無視)。"""
    fields: dict[str, str] = {}
    for line in (plugin_dir / "metadata.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z_\[\]]+)\s*=\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


def check_url(url: str, timeout: int = 10) -> bool:
    """URLが公開到達可能か(HEAD→GETフォールバック)。"""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(
                url, method=method, headers={"User-Agent": "build-plugin-zip"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status < 400
        except Exception:
            continue
    return False


def check_plugin(plugin_id: str, skip_net: bool = False) -> tuple[list[str], list[str]]:
    """plugins.qgis.org 要件の機械検証分。
    戻り値: (失敗メッセージ一覧, 手動確認の注意一覧)"""
    plugin_dir = PLUGINS_ROOT / plugin_id
    failures: list[str] = []
    notes: list[str] = []
    meta_path = plugin_dir / "metadata.txt"

    # 構造: トップレベル <id>/ + metadata.txt + __init__.py
    if not meta_path.is_file():
        return ([f"{plugin_id}: metadata.txt なし"], notes)
    if not (plugin_dir / "__init__.py").is_file():
        failures.append("__init__.py なし")

    fields = metadata_map(plugin_dir)

    # 英語 description
    desc = fields.get("description[en]") or fields.get("description") or ""
    if len(desc) < 20:
        failures.append("英語 description がない/短すぎる(20文字未満)")

    # email
    if "@" not in fields.get("email", ""):
        failures.append("metadata.txt に有効な email がない")

    # リンク(homepage/tracker/repository): 存在 + 公開到達性
    for key in ("homepage", "tracker", "repository"):
        url = fields.get(key, "")
        if not url:
            failures.append(f"metadata.txt に {key} がない")
        elif not skip_net and not check_url(url):
            failures.append(f"{key} に到達できない: {url}")

    # icon 指定があるのに実体がない
    icon = fields.get("icon")
    if icon and not (plugin_dir / icon).is_file():
        failures.append(f"icon ファイルがない: {icon}")

    # 同一ソース確認(git追跡ファイル=ZIPのソース)
    if not tracked_files(plugin_id):
        failures.append("git追跡ファイルが0件(ZIPのソースなし)")

    notes.append("実QGISでの動作確認済みか(機械判定不可)")
    notes.append("emailでプラグイン管理の連絡に応答できるか(利用者の同意項目)")
    return failures, notes


def run_checks(plugin_id: str, skip_net: bool) -> bool:
    """チェック実行して結果を表示。全パスならTrue。"""
    failures, notes = check_plugin(plugin_id, skip_net)
    for msg in failures:
        print(f"  [NG] {plugin_id}: {msg}")
    for msg in notes:
        print(f"  [確認] {plugin_id}: {msg}")
    if not failures:
        print(f"  [ok] {plugin_id}: チェック通過")
    return not failures


def build_zip(plugin_id: str, outdir: Path) -> Path | None:
    plugin_dir = PLUGINS_ROOT / plugin_id
    if not (plugin_dir / "metadata.txt").is_file():
        print(f"[skip] {plugin_id}: metadata.txt なし(プラグインではない)", file=sys.stderr)
        return None
    version = plugin_version(plugin_dir)
    files = tracked_files(plugin_id)
    if not files:
        print(f"[skip] {plugin_id}: 対象ファイルなし", file=sys.stderr)
        return None
    outdir.mkdir(parents=True, exist_ok=True)
    zip_path = outdir / f"{plugin_id}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            arc = Path(plugin_id) / Path(*rel.parts[2:])
            zf.write(REPO_ROOT / rel, arc.as_posix())
    print(f"[ok] {zip_path.name}  ({len(files)} files, {zip_path.stat().st_size / 1024:.0f} KB)")
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description="QGISプラグイン配布ZIPを dist/ に作成")
    ap.add_argument("plugins", nargs="*", help="プラグインID(qgis-plugin/のフォルダ名)")
    ap.add_argument("--all", action="store_true", help="全プラグインを対象にする")
    ap.add_argument("--list", action="store_true", help="対象プラグイン一覧を表示して終了")
    ap.add_argument("--check", action="store_true", help="チェックのみ実行(ZIPは作らない)")
    ap.add_argument("--force", action="store_true", help="チェック失敗時もZIPを作成する")
    ap.add_argument("--skip-net", action="store_true", help="リンク疎通チェックを省略する")
    ap.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="出力先(既定: dist/)")
    args = ap.parse_args()

    plugins = list_plugins()
    if args.list:
        for p in plugins:
            print(f"{p}  v{plugin_version(PLUGINS_ROOT / p)}")
        return 0

    targets = plugins if args.all else args.plugins
    if not targets:
        ap.error("プラグインIDまたは --all を指定してください")

    unknown = [p for p in targets if p not in plugins]
    for p in unknown:
        print(f"[warn] {p}: qgis-plugin/ にプラグインが見つかりません", file=sys.stderr)

    targets = [p for p in targets if p not in unknown]
    if args.check:
        ok = all(run_checks(p, args.skip_net) for p in targets)
        return 0 if ok else 1

    if not args.force:
        targets = [p for p in targets if run_checks(p, args.skip_net)]

    built = [build_zip(p, Path(args.outdir)) for p in targets]
    ok = [b for b in built if b]
    print(f"\n{len(ok)}/{len(targets)} 件のZIPを {Path(args.outdir).resolve()} に出力")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
