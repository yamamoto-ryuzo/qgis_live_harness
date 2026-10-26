# -*- coding: utf-8 -*-
import socket
import threading
import time
import urllib.parse
import json
import os
import re
import concurrent.futures
from collections import deque
from datetime import datetime
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY, QgsMessageLog, Qgis
from .i18n_json import lang_code
# lazy import http_server inside methods to avoid circular import during QGIS plugin init


class GeoWebViewServerManager:
    """geo_webview用HTTPサーバー管理クラス

    内蔵HTTPサーバーの起動・停止・リクエスト処理を担当します。
    提供エンドポイント: /kasugai(.kascエクスポート)、/export-data/、
    /present・/present/state・/screenshot(画面共有)、/received(受領履歴)、
    /<engine>/(KASUGAI Canvas web/ 静的フォールバック)。
    /qgis-map・旧形式/wms のパーマリンクURLは受領履歴とExternal Control
    ナビゲートのトリガとしてのみ扱います。
    """

    @staticmethod
    def _calculate_optimal_workers():
        """PCのCPUコア数に基づいて最適なワーカー数を計算

        Returns:
            int: 最適なワーカー数 (最小4、最大32)

        計算式:
        - CPUコア数+4を基本とする（I/O待ちを考慮）
        - 最小4: 低スペックPCでも基本的な並列処理を確保
        - 最大32: メモリ使用量とコンテキストスイッチのオーバーヘッドを抑制

        例:
        - 4コアPC: min(32, 4+4) = 8ワーカー
        - 8コアPC: min(32, 8+4) = 12ワーカー
        - 16コアPC: min(32, 16+4) = 20ワーカー
        - 32コアPC: min(32, 32+4) = 32ワーカー（上限）
        """
        try:
            cpu_count = os.cpu_count()
            if cpu_count is None:
                # cpu_count()がNoneを返す場合のフォールバック
                return 6  # デフォルト値（ブラウザの典型的な並列リクエスト数）

            # CPUコア数+4（I/O待ちを考慮）、最小4、最大32
            workers = min(32, max(4, cpu_count + 4))

            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(
                f"💻 Detected: CPU cores={cpu_count}, HTTP parallel workers={workers}",
                "geo_webview", Qgis.MessageLevel.Info
            )

            return workers
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(
                f"⚠️ Worker count auto-calculation failed, using default 6: {e}",
                "geo_webview", Qgis.MessageLevel.Warning
            )
            return 6

    def __init__(self, iface, navigation_signals, main_plugin):
        """サーバーマネージャーを初期化

        Args:
            iface: QGISインターフェース
            navigation_signals: ナビゲーション用シグナル
            main_plugin: メインプラグインクラスのインスタンス（共通メソッド呼び出し用）
        """
        self.iface = iface
        self.navigation_signals = navigation_signals
        self.main_plugin = main_plugin

        # HTTPサーバー関連の状態
        self.http_server = None
        self.server_thread = None
        self.server_port = 8089  # デフォルトポート
        self.preferred_port = 8089  # ユーザー指定の優先ポート
        self._http_running = False
        self._last_request_text = ""

        # HTTP並列処理用スレッドプール（PCのCPU性能に応じて自動調整）
        optimal_workers = self._calculate_optimal_workers()
        self._http_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=optimal_workers,
            thread_name_prefix='HTTP-Handler'
        )

        # プラグインバージョン情報
        self.plugin_version = self._get_plugin_version()
        # クライアントから受領したパーマリンク履歴(最新10件)
        # 要素: {'url','client','ua','time'}
        self.received_history = deque(maxlen=10)
        # MACアドレス解決キャッシュ {ip: (set_of_macs, epoch)}
        self._mac_cache = {}
        # 独立レンダラ(QgsMapRendererParallelJob)の同時実行はQGISクラッシュを
        # 引き起こすため直列化する(/screenshot の複製描画で使用)
        self._render_lock = threading.Lock()
        # KASUGAIエクスポートは同一出力先へ書き込むため同時実行を直列化する
        self._kasugai_lock = threading.Lock()

    def _safe_int(self, value, default):
        """文字列から安全にintに変換する。NaNや不正値は default を返す。"""
        try:
            # floatを経由して 'NaN' をはじく
            v = float(value)
            if v != v:  # NaN check
                return int(default)
            return int(v)
        except Exception:
            return int(default)

    def _get_plugin_version(self):
        """metadata.txtからプラグインバージョンを取得"""
        try:
            plugin_dir = os.path.dirname(__file__)
            metadata_path = os.path.join(plugin_dir, 'metadata.txt')

            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                    # 各行をチェック（スペースを無視）
                    for line in lines:
                        # スペースを削除して "version=" で始まるかチェック
                        clean_line = line.replace(' ', '').replace('\t', '').lower()
                        if clean_line.startswith('version='):
                            # 元の行から値を抽出
                            if '=' in line:
                                version = line.split('=')[1].strip()
                                return version

        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"❌ Version detection error: {e}", "geo_webview", Qgis.MessageLevel.Warning)

        # デフォルトバージョン（metadata.txtから読み取れない場合）
        return "UNKNOWN"

    def start_http_server(self, preferred_port=None):
        """HTTPサーバーを起動

        Args:
            preferred_port: 優先的に使用したいポート番号（指定がない場合は8089から検索）
        """
        try:
            if self._http_running:
                return

            # 優先ポートが指定されていればそれを使用
            if preferred_port is not None:
                self.preferred_port = preferred_port

            # 使用可能なポートを探す
            # 標準ポート(80, 443)の場合はそのまま使用、それ以外は指定ポートから+10の範囲で検索
            if self.preferred_port in (80, 443):
                # 標準ポートの場合はそのポートのみを試行
                start_port = self.preferred_port
                end_port = self.preferred_port
            else:
                # その他のポートの場合は±10の範囲で検索（下限は80）
                start_port = max(80, self.preferred_port)
                end_port = min(65535, self.preferred_port + 10)

            self.server_port = self.find_available_port(start_port, end_port)

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._set_reuse_socketopt(server_socket)
            # bind to all interfaces so non-localhost access is possible
            server_socket.bind(('0.0.0.0', self.server_port))  # nosec B104  # LAN共有は本機能の仕様
            server_socket.listen(5)
            server_socket.settimeout(1.0)

            self.http_server = server_socket
            self._http_running = True

            self.server_thread = threading.Thread(
                target=self.run_server,
                name="QMapPermalinkHTTP",
                daemon=True,
            )
            self.server_thread.start()

            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"🚀 geo_webview v{self.plugin_version} HTTP server started: http://localhost:{self.server_port}", "geo_webview", Qgis.MessageLevel.Info)
            self.iface.messageBar().pushMessage(
                "QMap Permalink",
                QCoreApplication.translate("geo_webview", "HTTP server started (port: {0})").format(self.server_port),
                duration=3
            )

        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"Failed to start HTTP server: {e}", "geo_webview", Qgis.MessageLevel.Critical)
            self.iface.messageBar().pushMessage(
                QCoreApplication.translate("geo_webview", "QMap Permalink Error"),
                QCoreApplication.translate("geo_webview", "Failed to start HTTP server: {0}").format(e),
                duration=5
            )
            self._http_running = False
            if self.http_server:
                try:
                    self.http_server.close()
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                self.http_server = None

    def run_server(self):
        """サーバーを安全に実行（並列処理版）"""
        try:
            while self._http_running and self.http_server:
                try:
                    conn, addr = self.http_server.accept()
                except socket.timeout:  # nosec B112  # 設計上の許容
                    continue
                except OSError:
                    break

                # リクエストをスレッドプールで並列処理（ブラウザの6タイル同時取得に対応）
                try:
                    # スレッドプールが有効かチェック
                    if hasattr(self, '_http_executor') and self._http_executor and not getattr(self._http_executor, '_shutdown', False):
                        self._http_executor.submit(self._handle_client_connection_safe, conn, addr)
                    else:
                        # スレッドプールが使えない場合は接続を閉じる
                        try:
                            conn.close()
                        except Exception:  # nosec B110  # 設計上の許容
                            pass
                except Exception as e:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(f"Failed to dispatch HTTP request to thread pool: {e}", "geo_webview", Qgis.MessageLevel.Critical)
                    try:
                        conn.close()
                    except Exception:  # nosec B110  # 設計上の許容
                        pass

        finally:
            self._http_running = False
            if self.http_server:
                try:
                    self.http_server.close()
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                self.http_server = None
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage("HTTP server stopped", "geo_webview", Qgis.MessageLevel.Info)

    def stop_http_server(self):
        """HTTPサーバーを停止"""
        try:
            self._http_running = False

            # ソケットを先に閉じてacceptループを終了
            if self.http_server:
                try:
                    self.http_server.close()
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                self.http_server = None

            # スレッドの終了を待つ
            if self.server_thread and self.server_thread.is_alive():
                try:
                    self.server_thread.join(timeout=3.0)
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                self.server_thread = None

            # スレッドプールをシャットダウン（最後に実行）
            if hasattr(self, '_http_executor') and self._http_executor:
                try:
                    self._http_executor.shutdown(wait=True, cancel_futures=True)
                except TypeError:
                    # Python 3.8以前はcancel_futures引数がない
                    self._http_executor.shutdown(wait=True)
                except Exception:  # nosec B110  # 設計上の許容
                    pass
                # 新しいエグゼキュータを作成（次回起動用）
                optimal_workers = self._calculate_optimal_workers()
                self._http_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=optimal_workers,
                    thread_name_prefix='HTTP-Handler'
                )

            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage("QMap Permalink HTTP server stopped", "geo_webview", Qgis.MessageLevel.Info)

        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"An error occurred while stopping the HTTP server: {e}", "geo_webview", Qgis.MessageLevel.Critical)

    def _handle_client_connection_safe(self, conn, addr):
        """HTTPリクエストを安全に処理（エラーハンドリング付き）"""
        try:
            self._handle_client_connection(conn, addr)
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"Error while handling HTTP request: {e}", "geo_webview", Qgis.MessageLevel.Warning)
        finally:
            try:
                conn.close()
            except Exception:  # nosec B110  # 設計上の許容
                pass

    def _handle_client_connection(self, conn, addr):
        """HTTPリクエストを解析して各エンドポイントへ振り分ける"""
        # 初期タイムアウト設定（リクエスト読み取り用）
        conn.settimeout(10.0)

        with conn:
            from . import http_server
            request_bytes = http_server.read_http_request(conn)
            if not request_bytes:
                return

            request_text = request_bytes.decode('iso-8859-1', errors='replace')
            self._last_request_text = request_text

            from qgis.core import QgsMessageLog, Qgis
            try:
                request_line = request_text.splitlines()[0]
            except IndexError:
                from . import http_server
                http_server.send_http_response(conn, 400, "Bad Request", "Invalid HTTP request line.")
                return

            parts = request_line.split()
            if len(parts) < 3:
                from . import http_server
                http_server.send_http_response(conn, 400, "Bad Request", "Malformed HTTP request line.")
                return

            method, target, _ = parts

            # OPTIONS: CORS + Private Network Access プリフライト
            # (ホスト版エンジン https → localhost への fetch 用)
            if method.upper() == 'OPTIONS':
                from . import http_server
                http_server.send_options_response(conn)
                return

            # HEAD はエクスポート用ランチャーHTMLのエンジン自動探索
            # (fetch HEAD で <engine>/index.html を探す)が使うため受け付ける。
            # 静的配信(export-data / Canvas web/)のみを対象とする
            head_only = method.upper() == 'HEAD'
            if method.upper() not in ('GET', 'HEAD'):
                from . import http_server
                http_server.send_http_response(conn, 405, "Method Not Allowed", "Only GET, HEAD and OPTIONS are supported.")
                return

            # MACアドレス認証モード(設定で有効時のみ): 未登録MACのクライアントは403
            if not self._mac_auth_check(addr[0] if addr else ''):
                from . import http_server
                http_server.send_http_response(
                    conn, 403, "Forbidden",
                    "Access denied: client MAC address is not registered.",
                    "text/plain; charset=utf-8")
                return

            parsed_url = urllib.parse.urlparse(target)
            params = urllib.parse.parse_qs(parsed_url.query)
            # パラメータ名は大小区別なしで受け付ける(小写で送る
            # クライアント対応のため大写エイリアスを補完)。既存キーは上書きしない
            for key in list(params):
                key_up = key.upper()
                if key_up != key and key_up not in params:
                    params[key_up] = params[key]
            # Manually unquote parameter values to handle UTF-8 encoding issues
            for key in params:
                params[key] = [urllib.parse.unquote_plus(val) for val in params[key]]
            # Extract Host header for use in generated URLs (used for OnlineResource)
            host = None
            for line in request_text.splitlines():
                if line.lower().startswith('host:'):
                    host = line.split(':', 1)[1].strip()
                    break

            # HEAD は静的配信のみ応答する(エンジン自動探索プローブ用)
            if head_only:
                try:
                    served = False
                    if parsed_url.path.startswith('/export-data/'):
                        served = True
                        self._handle_export_data(
                            conn, parsed_url.path[len('/export-data/'):],
                            head_only=True)
                    else:
                        served = self._handle_canvas_web(
                            conn, parsed_url.path, head_only=True)
                    if not served:
                        from . import http_server
                        http_server.send_http_response(
                            conn, 404, 'Not Found', 'not found',
                            'text/plain; charset=utf-8')
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'❌ HEAD handler error: {e}',
                        'geo_webview', Qgis.MessageLevel.Warning)
                return

            # ブラウザ/外部クライアントからパーマリンクURL（/qgis-map、
            # 旧形式の /wms パーマリンクも互換のため含む）を受け取ったときだけ
            # パネルのナビゲート欄に表示するためにemitする。
            # ただしパネル側から生成した自前のページ遷移(internal=1付与)は
            # ナビゲート欄の上書き・受領履歴の対象外とする。
            try:
                is_internal = 'internal' in params
                if parsed_url.path in ('/qgis-map', '/wms'):
                    server_port = None
                    try:
                        server_port = self.http_server.getsockname()[1] if self.http_server else self.server_port
                    except Exception:
                        server_port = self.server_port

                    if not host:
                        host = f'localhost:{server_port}'

                    # target が absolute URI の場合はそのまま使う
                    if target.startswith('http://') or target.startswith('https://'):
                        full_url = target
                    else:
                        full_url = f'http://{host}{target}'

                    if not is_internal:
                        # 受領履歴に記録(クライアントIP・User-Agent・時刻つき、最大10件)
                        try:
                            ua = ''
                            for hline in request_text.splitlines():
                                if hline.lower().startswith('user-agent:'):
                                    ua = hline.split(':', 1)[1].strip()
                                    break
                            self.received_history.appendleft({
                                'url': full_url,
                                'client': addr[0] if addr else '',
                                'ua': ua,
                                'time': datetime.now().isoformat(timespec='seconds'),
                            })
                        except Exception:  # nosec B110  # 設計上の許容
                            pass

                        # Emit the full URL for UI if signal available
                        if hasattr(self, 'navigation_signals') and self.navigation_signals:
                            try:
                                if hasattr(self.navigation_signals, 'request_origin_changed'):
                                    self.navigation_signals.request_origin_changed.emit(full_url)
                            except Exception:  # nosec B110  # 設計上の許容
                                pass

                        # main_plugin にも保持（パネル未作成時のフォールバック）
                        try:
                            if hasattr(self, 'main_plugin'):
                                setattr(self.main_plugin, '_last_request_origin', full_url)
                        except Exception:  # nosec B110  # 設計上の許容
                            pass
            except Exception:  # nosec B110  # 設計上の許容
                pass

            if parsed_url.path == '/debug-bookmarks':
                try:
                    if hasattr(self, '_handle_debug_bookmarks') and callable(getattr(self, '_handle_debug_bookmarks')):
                        self._handle_debug_bookmarks(conn)
                    else:
                        # Handler not implemented in this instance
                        from . import http_server
                        http_server.send_http_response(conn, 501, 'Not Implemented', 'debug-bookmarks handler not available')
                except Exception as e:
                    QgsMessageLog.logMessage(f"❌ debug-bookmarks handler error: {e}", "geo_webview", Qgis.MessageLevel.Critical)
                    import traceback
                    QgsMessageLog.logMessage(f"❌ Error traceback: {traceback.format_exc()}", "geo_webview", Qgis.MessageLevel.Critical)
                    from . import http_server
                    http_server.send_http_response(conn, 500, "Internal Server Error", f"debug-bookmarks failed: {str(e)}")
                return

            # クライアントから受領したパーマリンク履歴(JSON)
            if parsed_url.path == '/received':
                try:
                    payload = json.dumps(
                        {'received': list(self.received_history)},
                        ensure_ascii=False)
                    from . import http_server
                    http_server.send_http_response(
                        conn, 200, 'OK', payload,
                        'application/json; charset=utf-8')
                except Exception as e:
                    from . import http_server
                    http_server.send_http_response(
                        conn, 500, 'Internal Server Error',
                        f'received failed: {e}', 'text/plain; charset=utf-8')
                return

            # 現在のキャンバス状態(JSON)。プレゼンテーション追従用
            if parsed_url.path == '/present/state':
                try:
                    payload = json.dumps(
                        self._canvas_state_dict(), ensure_ascii=False)
                    from . import http_server
                    http_server.send_http_response(
                        conn, 200, 'OK', payload,
                        'application/json; charset=utf-8')
                except Exception as e:
                    from . import http_server
                    http_server.send_http_response(
                        conn, 500, 'Internal Server Error',
                        f'present/state failed: {e}', 'text/plain; charset=utf-8')
                return

            # 現在のキャンバス表示と同等のPNG(プレゼンテーション共有用)
            if parsed_url.path == '/screenshot':
                try:
                    self._handle_screenshot(conn, params)
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'❌ screenshot handler error: {e}',
                        'geo_webview', Qgis.MessageLevel.Critical)
                    from . import http_server
                    http_server.send_http_response(
                        conn, 500, 'Internal Server Error',
                        f'screenshot failed: {e}', 'text/plain; charset=utf-8')
                return

            # プレゼンテーションページ(地図キャンバスのウィンドウ共有表示)
            if parsed_url.path == '/present':
                try:
                    self._handle_present_page(conn, params)
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'❌ present handler error: {e}',
                        'geo_webview', Qgis.MessageLevel.Critical)
                    from . import http_server
                    http_server.send_http_response(
                        conn, 500, 'Internal Server Error',
                        f'present failed: {e}', 'text/plain; charset=utf-8')
                return

            # KASUGAI Canvas 連携: 表示中レイヤを .kasc プロジェクトに出力し、
            # 起動中のKASUGAIへ登録してプロジェクトURLをJSONで返す
            # (?engine=cesium|maplibre|openlayers|leaflet で起動エンジン指定可)
            if parsed_url.path == '/kasugai':
                try:
                    self._handle_kasugai(conn, params)
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'❌ kasugai handler error: {e}',
                        'geo_webview', Qgis.MessageLevel.Critical)
                    from . import http_server
                    http_server.send_http_response(
                        conn, 500, 'Internal Server Error',
                        f'kasugai failed: {e}', 'text/plain; charset=utf-8')
                return

            # /export-data/<rel>: KASUGAI/Re:Earth エクスポート産物(out_dir配下)の配信
            if parsed_url.path.startswith('/export-data/'):
                try:
                    self._handle_export_data(
                        conn, parsed_url.path[len('/export-data/'):])
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'❌ export-data error: {e}',
                        'geo_webview', Qgis.MessageLevel.Critical)
                    from . import http_server
                    http_server.send_http_response(
                        conn, 500, 'Internal Server Error', str(e),
                        'text/plain; charset=utf-8')
                return

            # --- 静的ファイル配信: favicon.ico ---
            import os
            static_files = ["/favicon.ico"]
            if parsed_url.path in static_files:
                plugin_dir = os.path.dirname(os.path.abspath(__file__))
                fname = parsed_url.path.lstrip("/")
                fpath = os.path.join(plugin_dir, fname)
                if os.path.exists(fpath):
                    content_type = "image/x-icon" if fname.endswith(".ico") \
                        else "application/octet-stream"
                    with open(fpath, "rb") as f:
                        data = f.read()
                    http_server.send_binary_response(conn, 200, "OK", data, content_type)
                    return
                http_server.send_http_response(conn, 404, "Not Found", f"File not found: {fname}", "text/plain; charset=utf-8")
                return

            # --- KASUGAI Canvas web/ 静的配信(フォールバック) ---
            # Canvas サーバ(8510)未起動時に、インストール済みCanvasの
            # エンジンHTMLをこのサーバが代わりに配信する。全エンドポイントに
            # 一致しなかったパスのみ web/ 配下へ解決する
            try:
                if self._handle_canvas_web(conn, parsed_url.path):
                    return
            except Exception as e:
                QgsMessageLog.logMessage(
                    f'❌ canvas web handler error: {e}',
                    'geo_webview', Qgis.MessageLevel.Critical)

            # 未対応のエンドポイントは404エラー
            QgsMessageLog.logMessage(f"❌ Unknown endpoint: {parsed_url.path}", "geo_webview", Qgis.MessageLevel.Warning)
            from . import http_server
            http_server.send_http_response(
                conn,
                404,
                "Not Found",
                "Available endpoints: /present (shared canvas view), /present/state (canvas JSON), /screenshot (canvas PNG), /received (permalink history), /kasugai (KASUGAI Canvas export), /export-data/<rel> (export files), /<engine>/ (KASUGAI Canvas web static fallback)"
            )
            return

    # ---------- MACアドレス認証 ----------

    @staticmethod
    def _norm_mac(value):
        """MAC表記を 'AA:BB:CC:DD:EE:FF' 大文字に正規化。不正値はNone。"""
        m = re.sub(r'[^0-9A-Fa-f]', '', str(value))
        if len(m) != 12:
            return None
        return ':'.join(m[i:i + 2] for i in range(0, 12, 2)).upper()

    def _local_macs(self):
        """このマシンのMACアドレス集合を返す(best-effort)。"""
        macs = set()
        try:
            import uuid
            n = self._norm_mac(format(uuid.getnode(), '012x'))
            if n:
                macs.add(n)
        except Exception:  # nosec B110  # 設計上の許容
            pass
        try:
            import subprocess  # nosec B404  # 意図的なOSコマンド呼出し
            if os.name == 'nt':
                out = subprocess.check_output(  # nosec B603 B607
                    ['getmac', '/fo', 'csv', '/nh'], timeout=5)
                text = out.decode('mbcs', errors='replace')
                for token in re.findall(
                        r'(?:[0-9A-Fa-f]{2}[-:]){5}[0-9A-Fa-f]{2}', text):
                    n = self._norm_mac(token)
                    if n:
                        macs.add(n)
            else:
                sysd = '/sys/class/net'
                if os.path.isdir(sysd):
                    for dev in os.listdir(sysd):
                        try:
                            with open(os.path.join(sysd, dev, 'address')) as fh:
                                n = self._norm_mac(fh.read())
                                if n:
                                    macs.add(n)
                        except Exception:  # nosec B112  # 設計上の許容
                            continue
        except Exception:  # nosec B110  # 設計上の許容
            pass
        return macs

    def _arp_lookup(self, ip):
        """ARPテーブルからリモートIPのMACアドレス集合を返す。"""
        macs = set()
        try:
            import subprocess  # nosec B404  # 意図的なOSコマンド呼出し
            if os.name == 'nt':
                out = subprocess.check_output(['arp', '-a'], timeout=5)  # nosec B603 B607
                text = out.decode('mbcs', errors='replace')
            else:
                try:
                    out = subprocess.check_output(  # nosec B603 B607
                        ['ip', 'neigh', 'show'], timeout=5)
                    text = out.decode(errors='replace')
                except Exception:
                    out = subprocess.check_output(['arp', '-a'], timeout=5)  # nosec B603 B607
                    text = out.decode(errors='replace')
            for line in text.splitlines():
                if ip in line:
                    for token in re.findall(
                            r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line):
                        n = self._norm_mac(token)
                        if n:
                            macs.add(n)
        except Exception:  # nosec B110  # 設計上の許容
            pass
        return macs

    def _resolve_client_macs(self, ip):
        """クライアントIPのMACアドレス集合(30秒キャッシュ)。"""
        now = time.time()
        ent = self._mac_cache.get(ip)
        if ent and now - ent[1] < 30:
            return ent[0]
        macs = set()
        try:
            if ip in ('127.0.0.1', '::1') or ip.startswith('::ffff:127.'):
                macs |= self._local_macs()
            else:
                macs |= self._arp_lookup(ip)
        except Exception:  # nosec B110  # 設計上の許容
            pass
        self._mac_cache[ip] = (macs, now)
        return macs

    def _mac_auth_check(self, client_ip):
        """MAC認証モードの判定。無効時は常にTrue。

        有効時(QSettings geo_webview.mac_auth_enabled)は、クライアントの
        MACアドレスが mac_auth_allowed(空白/カンマ区切り)に登録済みか判定。
        """
        try:
            from qgis.PyQt.QtCore import QSettings
            s = QSettings('GeoWebView', 'geo_webview')
            enabled = str(
                s.value('mac_auth_enabled', 'false')).lower() in (
                    '1', 'true', 'yes', 'on')
            if not enabled:
                return True
            raw = s.value('mac_auth_allowed', '') or ''
            allowed = {
                self._norm_mac(m) for m in re.split(r'[\s,;]+', str(raw))
                if self._norm_mac(m)}
            if not allowed:
                return False
            client_macs = {
                self._norm_mac(m) for m in self._resolve_client_macs(client_ip)
                if self._norm_mac(m)}
            return bool(allowed & client_macs)
        except Exception:
            # 認証判定で例外が出た場合は安全側(拒否)
            return False

    # ---------- キャンバス状態 / プレゼンテーション ----------

    def _canvas_state_dict(self):
        """現在の地図キャンバス状態をJSON化可能なdictで返す。

        x/y/crs はキャンバスCRS、x3857/y3857 はEPSG:3857、lon/lat は
        EPSG:4326 にそれぞれ変換した中心座標。zoom はscaleからの推定。
        """
        canvas = self.iface.mapCanvas()
        ms = canvas.mapSettings()
        c = canvas.center()
        scale = canvas.scale()
        crs_auth = ms.destinationCrs().authid()
        rotation = 0.0
        try:
            rotation = float(canvas.rotation())
        except Exception:  # nosec B110  # 設計上の許容
            pass
        zoom = None
        try:
            from .scale_zoom import estimate_zoom_from_scale_maplibre
            zoom = estimate_zoom_from_scale_maplibre(scale)
        except Exception:
            try:
                from .scale_zoom import estimate_zoom_from_scale
                zoom = estimate_zoom_from_scale(scale)
            except Exception:
                zoom = None
        lon = lat = x3857 = y3857 = None
        try:
            src = QgsCoordinateReferenceSystem(crs_auth)
            if src.isValid():
                proj = QgsProject.instance()
                p4326 = QgsCoordinateTransform(
                    src, QgsCoordinateReferenceSystem('EPSG:4326'), proj
                ).transform(QgsPointXY(c.x(), c.y()))
                lon, lat = p4326.x(), p4326.y()
                p3857 = QgsCoordinateTransform(
                    src, QgsCoordinateReferenceSystem('EPSG:3857'), proj
                ).transform(QgsPointXY(c.x(), c.y()))
                x3857, y3857 = p3857.x(), p3857.y()
        except Exception:  # nosec B110  # 設計上の許容
            pass
        return {
            'x': c.x(), 'y': c.y(), 'scale': scale, 'crs': crs_auth,
            'rotation': rotation, 'zoom': zoom,
            'lon': lon, 'lat': lat, 'x3857': x3857, 'y3857': y3857,
            'time': datetime.now().isoformat(timespec='seconds'),
        }

    def _handle_screenshot(self, conn, params):
        """現在の地図キャンバス表示と同等内容のPNGを返す(回転も反映)。

        QgsMapRendererParallelJob でキャンバスのMapSettingsを複製描画するため
        GUIスレッドをブロックしない。w/h(またはwidth/height)で出力サイズ指定可。
        """
        from . import http_server
        canvas = self.iface.mapCanvas()
        from qgis.core import QgsMapSettings
        from qgis.PyQt.QtCore import QSize, QBuffer, QIODevice, QByteArray
        ms = QgsMapSettings(canvas.mapSettings())
        w = self._safe_int(
            params.get('w', params.get('width', [0]))[0], 0)
        h = self._safe_int(
            params.get('h', params.get('height', [0]))[0], 0)
        if w <= 0 or h <= 0:
            try:
                w = int(canvas.width())
                h = int(canvas.height())
            except Exception:
                w, h = 0, 0
        if w <= 0 or h <= 0:
            w, h = 800, 600
        w = min(w, 4096)
        h = min(h, 4096)
        ms.setOutputSize(QSize(w, h))
        image = None
        try:
            with self._render_lock:
                image = self._render_map_settings(ms)
        except Exception:
            image = None
        if image is None or image.isNull():
            http_server.send_http_response(
                conn, 500, 'Internal Server Error', 'render failed',
                'text/plain; charset=utf-8')
            return
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        try:
            image.save(buf, 'PNG')
        finally:
            try:
                buf.close()
            except Exception:  # nosec B110  # 設計上の許容
                pass
        data = bytes(ba)
        http_server.send_binary_response(
            conn, 200, 'OK', data, 'image/png')

    def _render_map_settings(self, map_settings, timeout_s=30):
        """QgsMapRendererParallelJob で map_settings を複製描画して QImage を返す。

        /screenshot 用。GUIスレッドをブロックしないようイベントループで
        待機し、timeout_s 秒でタイムアウトする。呼び出し側で
        self._render_lock を取得して直列化すること。
        """
        from qgis.core import QgsMapRendererParallelJob
        from qgis.PyQt.QtCore import QEventLoop, QTimer

        render_job = QgsMapRendererParallelJob(map_settings)
        loop = QEventLoop()
        render_job.finished.connect(loop.quit)
        render_job.start()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.setSingleShot(True)
        timer.start(int(timeout_s * 1000))
        loop.exec()
        if render_job.isActive():
            render_job.cancel()
            return None
        image = render_job.renderedImage()
        if image is None or image.isNull():
            return None
        return image

    def _handle_present_page(self, conn, params):
        """地図キャンバスのウィンドウ共有ページ(/screenshot定期更新)を返す。"""
        from . import http_server
        interval = self._safe_int(params.get('interval', [1500])[0], 1500)
        if interval < 250:
            interval = 250
        lang = lang_code() or 'en'
        html_page = u'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="initial-scale=1"/>
<title>geo_webview - Presentation</title>
<style>
html,body{{margin:0;padding:0;height:100%;background:#111;color:#eee;font-family:sans-serif}}
#wrap{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;overflow:hidden}}
#shot{{max-width:100%;max-height:100%}}
#info{{position:fixed;left:0;right:0;bottom:0;padding:4px 10px;background:rgba(0,0,0,.55);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
</style>
</head>
<body>
<div id="wrap"><img id="shot" alt="loading..."/></div>
<div id="info">geo_webview presentation</div>
<script>
(function(){{
  var img = document.getElementById('shot');
  var info = document.getElementById('info');
  var timer = {interval};
  function reload(){{
    var im = new Image();
    im.onload = function(){{ img.src = im.src; }};
    im.src = 'screenshot?ts=' + Date.now();
  }}
  async function state(){{
    try{{
      var r = await fetch('present/state'); var s = await r.json();
      if(s) info.textContent =
        'center: ' + (s.lon!=null? s.lon.toFixed(6)+','+s.lat.toFixed(6) : s.x.toFixed(1)+','+s.y.toFixed(1)) +
        '  scale: 1:' + Math.round(s.scale) +
        '  rotation: ' + (s.rotation||0).toFixed(1) + '°  crs: ' + s.crs +
        '  (' + s.time + ')';
    }}catch(e){{}}
  }}
  setInterval(reload, timer);
  setInterval(state, timer);
  reload(); state();
}})();
</script>
</body>
</html>'''.format(lang=lang, interval=interval)
        http_server.send_http_response(
            conn, 200, 'OK', html_page, 'text/html; charset=utf-8')

    # 静的配信用 Content-Type 対応表。mimetypes モジュールは
    # Windows レジストリ依存で .js が text/plain になる環境があるため
    # 主要型は固定する
    _STATIC_MIME = {
        '.html': 'text/html; charset=utf-8',
        '.htm': 'text/html; charset=utf-8',
        '.js': 'text/javascript; charset=utf-8',
        '.mjs': 'text/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.geojson': 'application/geo+json; charset=utf-8',
        '.kasc': 'application/json; charset=utf-8',
        '.qml': 'application/xml; charset=utf-8',
        '.xml': 'application/xml; charset=utf-8',
        '.csv': 'text/csv; charset=utf-8',
        '.tsv': 'text/tab-separated-values; charset=utf-8',
        '.txt': 'text/plain; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.ico': 'image/x-icon',
        '.wasm': 'application/wasm',
        '.map': 'application/json; charset=utf-8',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.parquet': 'application/octet-stream',
        '.fgb': 'application/octet-stream',
        '.b3dm': 'application/octet-stream',
        '.gpkg': 'application/octet-stream',
    }

    @classmethod
    def _static_content_type(cls, path):
        return cls._STATIC_MIME.get(
            os.path.splitext(path)[1].lower(), 'application/octet-stream')

    def _handle_export_data(self, conn, rel, head_only=False):
        """KASUGAI/Re:Earth エクスポート産物(直近の出力先配下)を配信。

        パストラバーサル防止のため出力ディレクトリ外は拒否する。
        Re:Earth inspector の絶対URL参照や Canvas プロジェクト登録時の
        DATA/ 直接参照に使う。インストール先 projects/<id>/ に出力した
        場合も last_export_dir() でそちらを配信する。
        .html/.js/.css 等も正しい Content-Type で返すため、出力された
        エンジンランチャーHTMLをこのサーバ経由でブラウザ表示できる。
        """
        import os
        import urllib.parse
        from . import http_server, kasugai_export
        root = os.path.abspath(kasugai_export.last_export_dir())
        rel_path = urllib.parse.unquote(rel or '').replace('\\', '/')
        target = os.path.abspath(os.path.join(root, rel_path))
        if not target.startswith(root + os.sep) or not os.path.isfile(target):
            http_server.send_http_response(
                conn, 404, 'Not Found', 'not found',
                'text/plain; charset=utf-8')
            return
        ctype = self._static_content_type(target)
        if head_only:
            http_server.send_head_response(
                conn, 200, 'OK', os.path.getsize(target), ctype)
            return
        with open(target, 'rb') as f:
            data = f.read()
        http_server.send_binary_response(conn, 200, 'OK', data, ctype)

    def _handle_canvas_web(self, conn, rel_path, head_only=False):
        """インストール済み KASUGAI Canvas の ``web/`` を静的配信する。

        Canvas サーバ(8510)未起動時に、エクスポート済み .kasc+DATA/ を
        開くための最小HTTPサーバとして本サーバを使うためのフォールバック。
        全エンドポイントに一致しなかったパスを web/ 配下へ解決する
        (例: /cesium/index.html → <install>/web/cesium/index.html)。
        配信できれば True、見つからなければ False。
        """
        from . import http_server, kasugai_export
        web_root = kasugai_export.find_kasugai_web_dir()
        if not web_root:
            return False
        web_root = os.path.normcase(os.path.abspath(web_root))
        rel = urllib.parse.unquote(rel_path or '').replace('\\', '/')
        target = os.path.abspath(
            os.path.join(web_root, *rel.lstrip('/').split('/')))
        target_nc = os.path.normcase(target)
        if target_nc != web_root and \
                not target_nc.startswith(web_root + os.sep):
            return False
        if os.path.isdir(target):
            target = os.path.join(target, 'index.html')
        if not os.path.isfile(target):
            return False
        ctype = self._static_content_type(target)
        if head_only:
            http_server.send_head_response(
                conn, 200, 'OK', os.path.getsize(target), ctype)
            return True
        with open(target, 'rb') as f:
            data = f.read()
        http_server.send_binary_response(conn, 200, 'OK', data, ctype)
        return True

    def _handle_kasugai(self, conn, params=None):
        """表示中レイヤをKASUGAI Canvasプロジェクトとして出力し、
        起動中のKASUGAIローカルサーバへ登録してプロジェクトURLを返す。

        params['engine'] で起動エンジンを指定できる
        (cesium|maplibre|openlayers|leaflet、既定 cesium)。

        応答JSON:
          成功 {ok:true, url:<開くURL|null>, via, dir, layers, tiles, engine}
          失敗 {ok:false, error}
        via は url の供給元: 'kasugai'=Canvasサーバ登録、
        'qgis-http'=本サーバのCanvas web/静的配信フォールバック、
        'hosted'=ホスト版エンジン(kasugai-canvas-web)+本サーバの
        データ配信(Canvas未インストール向け・要インターネット)、
        null=未起動かつフォールバック不可(出力のみ成功)。
        """
        from . import http_server, kasugai_export
        engine = kasugai_export.DEFAULT_ENGINE
        try:
            requested = (params or {}).get('engine', [None])[0]
            if requested:
                engine = kasugai_export.normalize_engine(requested) \
                    or kasugai_export.DEFAULT_ENGINE
        except Exception:  # nosec B110  # 設計上の許容
            pass
        with self._kasugai_lock:
            result = kasugai_export.export_kasugai_project(
                self.iface,
                out_dir=kasugai_export.preferred_output_dir(),
                reearth_port=self.get_server_port())
            n_layers = len(result.get('layers') or [])
            n_tiles = len(result.get('tiles') or [])
            if not n_layers and not n_tiles:
                http_server.send_http_response(
                    conn, 200, 'OK',
                    json.dumps(
                        {'ok': False, 'error': 'no visible vector/tile layers'},
                        ensure_ascii=False),
                    'application/json; charset=utf-8')
                return
            url = None
            via = None
            # ?route= で再生経路を明示できる: kasugai / local|qgis-http /
            # hosted。未指定(auto)は従来どおり3段フォールバック
            route = str(
                (params or {}).get('route', ['auto'])[0] or 'auto'
                ).strip().lower()
            if route == 'qgis-http':
                route = 'local'
            if route not in ('auto', 'kasugai', 'local', 'hosted'):
                route = 'auto'
            try:
                caps = None
                _launched = False
                if route in ('auto', 'kasugai'):
                    caps, _launched = kasugai_export.ensure_kasugai_running(
                        result['kasc'], pump_events=False)
                if not caps and route in ('auto', 'kasugai') and str(
                        (params or {}).get('install', [''])[0]
                        ).lower() in ('1', 'true', 'yes'):
                    # ?install=1: 未検出なら配布ZIPを取得・展開して再試行
                    kasugai_export.install_kasugai()
                    caps, _launched = kasugai_export.ensure_kasugai_running(
                        result['kasc'], pump_events=False)
                if caps:
                    reg = kasugai_export.register_kasugai_project(
                        result['kasc'], engine=engine)
                    if reg.get('ok'):
                        kasugai_export.kasugai_command(
                            'switchProject', {'projectId': reg['id']})
                        url = reg.get('url')
                        via = 'kasugai'
            except Exception as e:
                QgsMessageLog.logMessage(
                    f'⚠️ KASUGAI registration failed: {e}',
                    'geo_webview', Qgis.MessageLevel.Warning)
            if not url and route in ('auto', 'local'):
                # Canvas未起動/未検出のフォールバック: このHTTPサーバ自体を
                # 最小配信サーバとして使い、インストール済みCanvasの web/ と
                # /export-data/ 配下の .kasc+DATA/ でエンジンを開く
                try:
                    # 旧単一エンジン構成のインストールは ?kasc= 非対応のため
                    # <engine>/ の存在まで確認する
                    if kasugai_export.find_kasugai_engine_dir(engine):
                        url = kasugai_export.build_local_view_url(
                            result['kasc'], engine=engine,
                            port=self.get_server_port() or self.server_port)
                        if url:
                            via = 'qgis-http'
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'⚠️ KASUGAI static fallback failed: {e}',
                        'geo_webview', Qgis.MessageLevel.Warning)
            if not url and route in ('auto', 'hosted'):
                # 最終フォールバック: ホスト版エンジン(kasugai-canvas-web)
                # + 本サーバの /export-data/ データ配信。Canvas未インストール
                # 環境でもブラウザで開ける(要インターネット)
                try:
                    url = kasugai_export.build_hosted_view_url(
                        result['kasc'], engine=engine,
                        port=self.get_server_port() or self.server_port)
                    if url:
                        via = 'hosted'
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f'⚠️ KASUGAI hosted fallback failed: {e}',
                        'geo_webview', Qgis.MessageLevel.Warning)
            http_server.send_http_response(
                conn, 200, 'OK',
                json.dumps(
                    {'ok': True, 'url': url, 'via': via,
                     'dir': result.get('dir'),
                     'layers': n_layers, 'tiles': n_tiles,
                     'engine': engine},
                    ensure_ascii=False),
                'application/json; charset=utf-8')

    def _handle_debug_bookmarks(self, conn):
        """Return a JSON list of collected bookmarks (for debugging)."""
        from qgis.core import QgsProject
        try:
            bookmarks_list = []
            mgr = None
            try:
                mgr = QgsProject.instance().bookmarkManager()
            except Exception:
                try:
                    mgr = QgsProject.instance().bookmarks()
                except Exception:
                    mgr = None

            raw = None
            if mgr is not None:
                try:
                    raw = mgr.bookmarks()
                except Exception:
                    try:
                        raw = mgr.getBookmarks()
                    except Exception:
                        raw = None

            if raw:
                for b in raw:
                    name = ''
                    try:
                        if hasattr(b, 'name'):
                            name = b.name()
                        else:
                            name = str(getattr(b, 'displayName', '') or '')
                    except Exception:
                        try:
                            if isinstance(b, dict) and 'name' in b:
                                name = str(b.get('name'))
                        except Exception:
                            name = ''

                    bx = None
                    by = None
                    try:
                        if hasattr(b, 'point'):
                            p = b.point()
                            bx = p.x()
                            by = p.y()
                    except Exception:
                        bx = None
                        by = None

                    if (bx is None or by is None) and hasattr(b, 'center'):
                        try:
                            p = b.center()
                            bx = p.x()
                            by = p.y()
                        except Exception:  # nosec B110  # 設計上の許容
                            pass

                    if (bx is None or by is None) and hasattr(b, 'extent'):
                        try:
                            ext = b.extent()
                            bx = (ext.xMinimum() + ext.xMaximum()) / 2.0
                            by = (ext.yMinimum() + ext.yMaximum()) / 2.0
                        except Exception:  # nosec B110  # 設計上の許容
                            pass

                    if (bx is None or by is None) and isinstance(b, dict):
                        try:
                            if 'x' in b and 'y' in b:
                                bx = float(b.get('x'))
                                by = float(b.get('y'))
                            elif 'lon' in b and 'lat' in b:
                                bx = float(b.get('lon'))
                                by = float(b.get('lat'))
                        except Exception:  # nosec B110  # 設計上の許容
                            pass

                    if bx is None or by is None:
                        continue

                    # Attempt to determine source CRS id
                    src_crs_id = None
                    try:
                        if hasattr(b, 'crs'):
                            src_crs_id = b.crs()
                    except Exception:
                        src_crs_id = None

                    # Provide orig coords and placeholder for transformed values (transformation done elsewhere)
                    bookmarks_list.append({
                        'name': str(name),
                        'x': bx,
                        'y': by,
                        'src_crs': src_crs_id,
                        'orig_x': bx,
                        'orig_y': by
                    })

            import json
            payload = json.dumps({'bookmarks': bookmarks_list}, ensure_ascii=False)
            from . import http_server
            http_server.send_http_response(conn, 200, 'OK', payload, 'application/json; charset=utf-8')
        except Exception as e:
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f'❌ debug-bookmarks error: {e}', 'QMapPermalink', Qgis.MessageLevel.Warning)
            except Exception:  # nosec B110  # 設計上の許容
                pass
            from . import http_server
            http_server.send_http_response(conn, 500, 'Internal Server Error', f'{{"error": "{str(e)}"}}', 'application/json; charset=utf-8')

    def _build_navigation_data_from_params(self, params):
        """互換性用: HTTPパラメータ(dict of lists)から navigation_data を構築して返す

        params: dict where values are lists (urllib.parse.parse_qs形式)

        Returns:
            dict: navigation_data. Examples:
                {'type': 'location', 'location': '<encoded json>'}
                {'type': 'coordinates', 'x': x, 'y': y, 'scale': scale, 'crs': crs, 'zoom': zoom, 'rotation': rotation, 'theme_info': theme}

        Raises:
            ValueError: 必要なパラメータが不足している場合
        """
        from qgis.core import QgsMessageLog, Qgis

        try:
            # location パラメータがあれば location タイプ
            if 'location' in params and params['location']:
                location_val = params['location'][0]
                return {'type': 'location', 'location': location_val}

            # coordinates ベース: x, y が必須
            if 'x' in params and 'y' in params:
                x_val = params.get('x', [None])[0]
                y_val = params.get('y', [None])[0]
                if x_val is None or y_val is None:
                    raise ValueError('x or y parameter missing')

                # optional params
                scale_val = params.get('scale', [None])[0]
                zoom_val = params.get('zoom', [None])[0]
                crs_val = params.get('crs', [None])[0]
                rotation_val = params.get('rotation', [None])[0]
                theme_val = params.get('theme', [None])[0]

                navigation_data = {
                    'type': 'coordinates',
                    'x': float(x_val) if x_val is not None else None,
                    'y': float(y_val) if y_val is not None else None,
                    'scale': float(scale_val) if scale_val is not None else None,
                    'zoom': float(zoom_val) if zoom_val is not None else None,
                    'crs': str(crs_val) if crs_val is not None else None,
                    'rotation': float(rotation_val) if rotation_val is not None else None,
                    'theme_info': theme_val
                }

                return navigation_data

            # フォールバック: 不明なパラメータ
            raise ValueError('No navigation parameters found')

        except Exception as e:
            QgsMessageLog.logMessage(f"Error building navigation_data from params: {e}", "geo_webview", Qgis.MessageLevel.Warning)
            raise

    def _guess_bind_ip(self):
        """サーバの外向きIPv4アドレスを推定して返す（簡易）"""
        try:
            import socket as _socket
            # 外部に到達可能なダミー接続を作って自IPを取得
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 53))
                ip = s.getsockname()[0]
            except Exception:
                ip = '127.0.0.1'
            finally:
                try:
                    s.close()
                except Exception:  # nosec B110  # 設計上の許容
                    pass
            return ip
        except Exception:
            return '127.0.0.1'

    @staticmethod
    def _set_reuse_socketopt(sock):
        """WindowsではSO_EXCLUSIVEADDRUSEでポートの占有を排他化する。

        SO_REUSEADDR はWindowsでは他プロセスによる同一ポートの多重
        バインド(ポート横取り)を許してしまうため、複数QGISインスタンスが
        同居する環境で接続が別プロセスへ分散し無応答になる。
        UnixではSO_REUSEADDR(TIME_WAIT再利用)を維持する。
        """
        try:
            excl = getattr(socket, 'SO_EXCLUSIVEADDRUSE', None)
            if excl is not None:  # Windows
                sock.setsockopt(socket.SOL_SOCKET, excl, 1)
            else:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except OSError:  # nosec B110  # 設計上の許容
            pass

    def find_available_port(self, start_port, end_port):
        """使用可能なポートを探す

        Args:
            start_port: 開始ポート番号
            end_port: 終了ポート番号

        Returns:
            使用可能なポート番号
        """
        for port in range(start_port, end_port + 1):
            try:
                # test bind on all interfaces
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    self._set_reuse_socketopt(s)
                    s.bind(('0.0.0.0', port))  # nosec B104  # 実bind(上記)と同じIFで空き確認する必要がある
                    return port
            except OSError as e:
                # ポート80, 443は管理者権限が必要な場合がある
                if port in (80, 443):
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(
                        f"Failed to bind port {port} (administrator rights may be required): {e}",
                        "geo_webview", Qgis.MessageLevel.Warning
                    )
                continue
        raise RuntimeError(f"No available port found in range {start_port}-{end_port}")

    def is_server_running(self):
        """サーバーが稼働中かどうかを確認"""
        return self._http_running and self.http_server is not None

    def get_server_port(self):
        """現在のサーバーポートを取得"""
        return self.server_port if self.is_server_running() else None

    def check_external_access(self):
        """外部からのアクセス可能性を診断

        Returns:
            dict: 診断結果を含む辞書
                {
                    'server_running': bool,
                    'port': int,
                    'local_ip': str,
                    'all_ips': list,
                    'localhost_url': str,
                    'local_network_url': str,
                    'firewall_warning': bool,
                    'message': str
                }
        """
        result = {
            'server_running': False,
            'port': None,
            'local_ip': '127.0.0.1',
            'all_ips': [],
            'localhost_url': '',
            'local_network_url': '',
            'firewall_warning': True,
            'message': ''
        }

        try:
            # サーバー稼働状態チェック
            result['server_running'] = self.is_server_running()
            result['port'] = self.get_server_port()

            if not result['server_running']:
                result['message'] = QCoreApplication.translate('geo_webview', 'The HTTP server is not running')
                return result

            # ローカルIPアドレスを取得
            import socket
            hostname = socket.gethostname()

            # すべてのIPアドレスを取得
            try:
                all_addresses = socket.getaddrinfo(hostname, None)
                ipv4_addresses = []
                for addr in all_addresses:
                    if addr[0] == socket.AF_INET:  # IPv4のみ
                        ip = addr[4][0]
                        if ip not in ipv4_addresses and not ip.startswith('127.'):
                            ipv4_addresses.append(ip)
                result['all_ips'] = ipv4_addresses
            except Exception:  # nosec B110  # 設計上の許容
                pass

            # プライマリローカルIP（外向き）を取得
            result['local_ip'] = self._guess_bind_ip()

            # URLを生成
            result['localhost_url'] = f"http://localhost:{result['port']}"
            if result['local_ip'] != '127.0.0.1':
                result['local_network_url'] = f"http://{result['local_ip']}:{result['port']}"

            # ファイアウォール警告の判定（Windowsの場合）
            allowed_ports = []
            try:
                import platform
                if platform.system() == 'Windows':
                    # Windowsファイアウォールルールの確認を試みる
                    import subprocess  # nosec B404  # 意図的なOSコマンド呼出し
                    try:
                        # netshコマンドでファイアウォールルールを確認
                        import re
                        output = subprocess.run(  # nosec B603 B607
                            ['netsh', 'advfirewall', 'firewall', 'show',
                             'rule', 'name=all'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        # ルールが見つかれば警告なし
                        if output.returncode == 0 and re.search(
                                r'LocalPort.*{0}'.format(result["port"]),
                                output.stdout, re.IGNORECASE):
                            result['firewall_warning'] = False
                        else:
                            result['firewall_warning'] = True

                        # 許可されているポートを検出（範囲1024-65535で確認）
                        try:
                            allowed_ports = self._scan_firewall_allowed_ports()
                        except Exception:  # nosec B110  # 設計上の許容
                            pass
                    except Exception:
                        # コマンド実行失敗時は警告を表示
                        result['firewall_warning'] = True
                else:
                    # Windows以外は警告なし（確認方法が異なるため）
                    result['firewall_warning'] = False
            except Exception:
                result['firewall_warning'] = True

            # メッセージ生成
            messages = []
            messages.append(QCoreApplication.translate('geo_webview', "✅ Server is running on port {0}").format(result['port']))
            messages.append(QCoreApplication.translate('geo_webview', "🏠 Local: {0}").format(result['localhost_url']))

            if result['local_network_url']:
                messages.append(QCoreApplication.translate('geo_webview', "🌐 Network: {0}").format(result['local_network_url']))

            if result['all_ips']:
                messages.append(QCoreApplication.translate('geo_webview', "📡 Available IPs: {0}").format(', '.join(result['all_ips'])))

            if result['firewall_warning']:
                messages.append(QCoreApplication.translate('geo_webview', "\n⚠️ The firewall may be blocking port {0}").format(result['port']))
                messages.append(QCoreApplication.translate('geo_webview', "   To allow external access, permit"))
                messages.append(QCoreApplication.translate('geo_webview', "   port {0} (TCP) in Windows Firewall").format(result['port']))

                # 許可されているポートがあれば表示
                if allowed_ports:
                    messages.append(QCoreApplication.translate('geo_webview', "\n🔓 Ports allowed in the firewall: {0}").format(', '.join(map(str, allowed_ports[:10]))))
                    if len(allowed_ports) > 10:
                        messages.append(QCoreApplication.translate('geo_webview', "   ({0} more)").format(len(allowed_ports) - 10))
                else:
                    messages.append(QCoreApplication.translate('geo_webview', "\n❌ No ports allowed in the firewall were found"))
                    messages.append(QCoreApplication.translate('geo_webview', "   To enable external access, create a new rule"))
                    messages.append(QCoreApplication.translate('geo_webview', "   in Windows Firewall to allow the port"))
            else:
                messages.append(QCoreApplication.translate('geo_webview', "\n✅ A firewall rule is configured"))

            result['message'] = '\n'.join(messages)

        except Exception as e:
            result['message'] = QCoreApplication.translate('geo_webview', 'An error occurred during diagnostics: {0}').format(e)

        return result

    def _scan_firewall_allowed_ports(self):
        """Windowsファイアウォールで許可されているポートをスキャン

        Returns:
            list: 許可されているポート番号のリスト
        """
        allowed_ports = []
        try:
            import subprocess  # nosec B404  # 意図的なOSコマンド呼出し
            import re

            # netshコマンドでファイアウォールルールを取得
            output = subprocess.run(  # nosec B603 B607
                ['netsh', 'advfirewall', 'firewall', 'show',
                 'rule', 'name=all'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if output.returncode == 0:
                lines = output.stdout.split('\n')
                current_rule_enabled = False
                current_rule_action = None

                for line in lines:
                    line_lower = line.lower().strip()

                    # ルールが有効かチェック
                    if 'enabled:' in line_lower:
                        current_rule_enabled = 'yes' in line_lower

                    # アクションがAllowかチェック
                    if 'action:' in line_lower:
                        current_rule_action = 'allow' in line_lower

                    # LocalPortを探す
                    if 'localport:' in line_lower and current_rule_enabled and current_rule_action:
                        # ポート番号を抽出
                        match = re.search(r'localport:\s*(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)', line_lower)
                        if match:
                            port_spec = match.group(1)
                            # カンマ区切りのポートを処理
                            for port_part in port_spec.split(','):
                                if '-' in port_part:
                                    # 範囲の場合（例: 8000-8100）
                                    start, end = port_part.split('-')
                                    try:
                                        start_port = int(start.strip())
                                        end_port = int(end.strip())
                                        # 範囲が広すぎる場合は最初の10個だけ追加
                                        for p in range(start_port, min(end_port + 1, start_port + 10)):
                                            if 1024 <= p <= 65535 and p not in allowed_ports:
                                                allowed_ports.append(p)
                                    except ValueError:  # nosec B110  # 設計上の許容
                                        pass
                                else:
                                    # 単一ポートの場合
                                    try:
                                        port = int(port_part.strip())
                                        if 1024 <= port <= 65535 and port not in allowed_ports:
                                            allowed_ports.append(port)
                                    except ValueError:  # nosec B110  # 設計上の許容
                                        pass

                    # 空行で次のルールに移行
                    if not line.strip():
                        current_rule_enabled = False
                        current_rule_action = None

            # ソートして返す
            allowed_ports.sort()
            return allowed_ports

        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"Firewall port scan error: {e}", "geo_webview", Qgis.MessageLevel.Warning)
            return []

    def add_firewall_rule(self, port, rule_name=None, request_elevation=True):
        """Windowsファイアウォールにポートを許可するルールを追加

        Args:
            port: 許可するポート番号
            rule_name: ルール名(省略時は自動生成)
            request_elevation: 管理者権限昇格を要求するか(デフォルトTrue)

        Returns:
            dict: 結果を含む辞書
                {
                    'success': bool,
                    'message': str,
                    'admin_required': bool,
                    'elevated': bool  # 昇格を試みたか
                }
        """
        result = {
            'success': False,
            'message': '',
            'admin_required': False,
            'elevated': False
        }

        try:
            import platform
            import subprocess  # nosec B404  # 意図的なOSコマンド呼出し

            if platform.system() != 'Windows':
                result['message'] = QCoreApplication.translate('geo_webview', 'This feature is only available on Windows')
                return result

            # ルール名の生成
            if not rule_name:
                rule_name = f"QMapPermalink-Port-{port}"

            # netshコマンドでファイアウォールルールを追加
            cmd = (
                f'netsh advfirewall firewall add rule '
                f'name="{rule_name}" '
                f'dir=in '
                f'action=allow '
                f'protocol=TCP '
                f'localport={port} '
                f'enable=yes'
            )

            try:
                # まず通常権限で試す
                output = subprocess.run(  # nosec B603 B607
                    ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                     'name={0}'.format(rule_name), 'dir=in',
                     'action=allow', 'protocol=TCP',
                     'localport={0}'.format(port), 'enable=yes'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if output.returncode == 0:
                    result['success'] = True
                    result['message'] = QCoreApplication.translate('geo_webview', 'Firewall rule "{0}" has been added').format(rule_name)
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(result['message'], "geo_webview", Qgis.MessageLevel.Info)
                else:
                    # 通常権限で失敗した場合、管理者権限で再試行
                    if request_elevation:
                        result['elevated'] = True

                        try:
                            # PowerShellの完全パスを取得
                            import os
                            ps_path = os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')

                            # PowerShellが見つからない場合は代替パスを試す
                            if not os.path.exists(ps_path):
                                ps_path = 'powershell.exe'

                            # netshの完全パスを取得
                            netsh_path = os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'System32', 'netsh.exe')
                            if not os.path.exists(netsh_path):
                                netsh_path = 'netsh.exe'

                            # PowerShellのStart-Processで直接netshを管理者権限で実行
                            # ArgumentListを配列形式で構築
                            args = [
                                'advfirewall',
                                'firewall',
                                'add',
                                'rule',
                                f'name={rule_name}',
                                'dir=in',
                                'action=allow',
                                'protocol=TCP',
                                f'localport={port}',
                                'enable=yes'
                            ]

                            # ArgumentListを文字列として結合
                            args_str = ','.join([f"'{arg}'" for arg in args])

                            # PowerShellコマンドを構築
                            ps_cmd = f'Start-Process -FilePath "{netsh_path}" -ArgumentList {args_str} -Verb RunAs -Wait -WindowStyle Hidden'

                            _ = subprocess.run(  # nosec B603
                                [ps_path, '-NoProfile', '-Command', ps_cmd],
                                capture_output=True,
                                text=True,
                                timeout=60,  # UAC待ち時間を考慮
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )

                            # 少し待機してからルールを確認
                            import time
                            time.sleep(1)

                            # 結果を確認(成功の場合、元のnetshコマンドをもう一度チェック)
                            verify_output = subprocess.run(  # nosec B603 B607
                                ['netsh', 'advfirewall', 'firewall', 'show',
                                 'rule', 'name={0}'.format(rule_name)],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )

                            if verify_output.returncode == 0 and rule_name in verify_output.stdout:
                                result['success'] = True
                                result['message'] = QCoreApplication.translate('geo_webview', 'Firewall rule "{0}" has been added with administrator rights').format(rule_name)
                                from qgis.core import QgsMessageLog, Qgis
                                QgsMessageLog.logMessage(result['message'], "geo_webview", Qgis.MessageLevel.Info)
                            else:
                                # ユーザーがUACをキャンセルした可能性
                                result['admin_required'] = True
                                result['message'] = QCoreApplication.translate(
                                    'geo_webview', 'Administrator elevation was cancelled or adding the rule failed.\n\nTo run manually, execute the following command in an administrator command prompt:\n\n{0}').format(cmd)
                                result['command'] = cmd
                        except subprocess.TimeoutExpired:
                            result['message'] = QCoreApplication.translate('geo_webview', 'Adding the firewall rule timed out (60 seconds)')
                            result['command'] = cmd
                        except Exception as elev_e:
                            result['message'] = QCoreApplication.translate(
                                'geo_webview', 'Execution with administrator rights failed: {0}\n\nTo run manually, execute the following command in an administrator command prompt:\n\n{1}').format(elev_e, cmd)
                            result['command'] = cmd
                            result['admin_required'] = True
                    else:
                        result['admin_required'] = True
                        result['message'] = QCoreApplication.translate(
                            'geo_webview', 'Administrator rights are required.\n\nExecute the following command in an administrator command prompt:\n\n{0}').format(cmd)
                        result['command'] = cmd
                        from qgis.core import QgsMessageLog, Qgis
                        QgsMessageLog.logMessage(f"Administrator rights required to add firewall rule: {output.stderr}", "geo_webview", Qgis.MessageLevel.Warning)

            except subprocess.TimeoutExpired:
                result['message'] = QCoreApplication.translate('geo_webview', 'Adding the firewall rule timed out')
            except Exception as e:
                if request_elevation:
                    result['message'] = QCoreApplication.translate(
                        'geo_webview', 'Execution with administrator rights failed: {0}\n\nTo run manually, execute the following command in an administrator command prompt:\n\n{1}').format(e, cmd)
                    result['command'] = cmd
                else:
                    result['admin_required'] = True
                    result['message'] = QCoreApplication.translate(
                        'geo_webview', 'Administrator rights are required.\n\nError: {0}\n\nExecute the following command in an administrator command prompt:\n\n{1}').format(e, cmd)
                    result['command'] = cmd

        except Exception as e:
            result['message'] = QCoreApplication.translate('geo_webview', 'Failed to add the firewall rule: {0}').format(e)
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(result['message'], "geo_webview", Qgis.MessageLevel.Critical)

        return result
