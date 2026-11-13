"""devin_tasks.py のテスト。stdlibのみで動くため実QGIS不要。

exeに [sys.executable, -c, ...] を渡すと実devin無しで
サブプロセス起動・ログ捕捉・状態追跡を実プロセスで検証できる。
"""

import os
import sys
import time

import pytest

from geo_driver import devin_tasks


def _wait(task_id, timeout=15.0):
    """タスク終了までstatusをポーリングして最終statusを返す。"""
    end = time.time() + timeout
    while time.time() < end:
        s = devin_tasks.status(task_id)
        if s["state"] != "running":
            return s
        time.sleep(0.1)
    pytest.fail(f"task {task_id} did not finish")


@pytest.fixture(autouse=True)
def _clean_tasks():
    devin_tasks._TASKS.clear()
    yield
    for t in list(devin_tasks._TASKS.values()):
        try:
            t["proc"].kill()
        except Exception:
            pass
    devin_tasks._TASKS.clear()


def test_build_argv():
    argv = devin_tasks._build_argv(
        "devin.exe", "pf.txt", session_id="s1", model="opus",
        permission_mode="smart")
    assert argv[:2] == ["devin.exe", "-p"]
    assert "--respect-workspace-trust" in argv
    i = argv.index("--permission-mode")
    assert argv[i + 1] == "smart"
    assert argv[argv.index("-r") + 1] == "s1"
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[-2:] == ["--prompt-file", "pf.txt"]
    with pytest.raises(devin_tasks.TaskError):
        devin_tasks._build_argv("devin.exe", "pf.txt",
                                permission_mode="bogus")


def test_find_exe(monkeypatch, tmp_path):
    monkeypatch.delenv("QGIS_LIVE_DEVIN_EXE", raising=False)
    monkeypatch.setattr(devin_tasks.shutil, "which", lambda n: None)
    monkeypatch.setattr(devin_tasks, "_DEFAULT_EXE", "")
    assert devin_tasks.find_exe() is None
    exe = tmp_path / "devin.exe"
    exe.write_bytes(b"x")
    assert devin_tasks.find_exe(str(exe)) == str(exe)
    monkeypatch.setenv("QGIS_LIVE_DEVIN_EXE", str(exe))
    assert devin_tasks.find_exe() == str(exe)


def test_run_requires_prompt(tmp_path):
    with pytest.raises(devin_tasks.TaskError):
        devin_tasks.run("  ", cwd=str(tmp_path), exe=["x"],
                        live_dir=str(tmp_path))


def test_run_bad_cwd(tmp_path):
    with pytest.raises(devin_tasks.TaskError):
        devin_tasks.run("hi", cwd=str(tmp_path / "nope"), exe=["x"],
                        live_dir=str(tmp_path))


def test_run_missing_devin(monkeypatch, tmp_path):
    monkeypatch.setattr(devin_tasks, "find_exe", lambda e=None: None)
    with pytest.raises(devin_tasks.TaskError, match="not found"):
        devin_tasks.run("hi", cwd=str(tmp_path), live_dir=str(tmp_path))


def test_run_status_result(tmp_path):
    r = devin_tasks.run(
        "do stuff", cwd=str(tmp_path),
        exe=[sys.executable, "-c",
             "import sys; print('OUT-LINE'); "
             "print('ERR-LINE', file=sys.stderr)"],
        live_dir=str(tmp_path))
    assert r["task_id"].startswith("devin-")
    s = _wait(r["task_id"])
    assert s["state"] == "exited"
    assert s["exit_code"] == 0
    res = devin_tasks.result(r["task_id"])
    assert "OUT-LINE" in res["output"]
    # stderrはstdoutへマージされてログに残る
    assert "ERR-LINE" in res["output"]
    # プロンプトがファイルへ保存されている
    assert os.path.isfile(r["log"])


def test_status_lists_all(tmp_path):
    r = devin_tasks.run("x", cwd=str(tmp_path),
                        exe=[sys.executable, "-c", "pass"],
                        live_dir=str(tmp_path))
    ids = {t["task_id"] for t in devin_tasks.status()["tasks"]}
    assert r["task_id"] in ids
    _wait(r["task_id"])


def test_status_unknown():
    with pytest.raises(devin_tasks.TaskError):
        devin_tasks.status("devin-nope")


def test_abort(tmp_path):
    r = devin_tasks.run(
        "x", cwd=str(tmp_path),
        exe=[sys.executable, "-c", "import time; time.sleep(60)"],
        live_dir=str(tmp_path))
    out = devin_tasks.abort(r["task_id"])
    assert out["aborted"] is True
    s = _wait(r["task_id"])
    assert s["state"] == "failed"
    assert s["exit_code"] != 0


# ---- ACPエンジン ----

def test_resolve_engine(monkeypatch):
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: "k")
    assert devin_tasks._resolve_engine("auto") == "acp"
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: None)
    assert devin_tasks._resolve_engine("auto") == "print"
    assert devin_tasks._resolve_engine("print") == "print"
    with pytest.raises(devin_tasks.TaskError):
        devin_tasks._resolve_engine("bogus")


# devin.exe acp の振る舞いを真似た最小JSON-RPCサーバ。
# session/prompt では request_permission を往復してから応答を返す。
_FAKE_ACP = r'''
import sys, json
def send(m):
    sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()
for line in sys.stdin:
    try: msg = json.loads(line)
    except Exception: continue
    mid, m, p = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if m == "initialize":
        res = {"protocolVersion": 1,
               "agentCapabilities": {"loadSession": True}}
    elif m == "authenticate": res = {}
    elif m == "session/new":
        res = {"sessionId": "fake-s1", "configOptions": []}
    elif m == "session/load": res = {"sessionId": p.get("sessionId")}
    elif m == "session/set_config_option": res = {}
    elif m == "session/prompt":
        send({"jsonrpc": "2.0", "id": 999,
              "method": "session/request_permission",
              "params": {"options": [{"optionId": "deny"},
                                     {"optionId": "allow_always"}]}})
        oid = None
        for l2 in sys.stdin:
            try: r = json.loads(l2)
            except Exception: continue
            if r.get("id") == 999:
                oid = ((r.get("result") or {}).get("outcome") or {}
                       ).get("optionId")
                break
        send({"jsonrpc": "2.0", "method": "session/update",
              "params": {"update": {
                  "sessionUpdate": "agent_message_chunk",
                  "content": {"text": "HELLO-ACP perm=" + str(oid)}}}})
        res = {"stopReason": "end_turn"}
    elif m == "session/close": res = {}
    else: res = {}
    if mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "result": res})
'''


def test_acp_session(monkeypatch, tmp_path):
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: "k")
    fake = tmp_path / "fake_acp.py"
    fake.write_text(_FAKE_ACP, encoding="utf-8")
    r = devin_tasks.run("hi", cwd=str(tmp_path), engine="acp",
                        exe=[sys.executable, str(fake)],
                        live_dir=str(tmp_path))
    s = _wait(r["task_id"])
    assert s["state"] == "exited"
    assert s["engine"] == "acp"
    assert s["session_id"] == "fake-s1"
    res = devin_tasks.result(r["task_id"])
    assert "HELLO-ACP" in res["output"]
    # dangerous既定なので allow_always が自動選択される
    assert "perm=allow_always" in res["output"]
    assert "end_turn" in res["output"]


def test_acp_session_load(monkeypatch, tmp_path):
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: "k")
    fake = tmp_path / "fake_acp.py"
    fake.write_text(_FAKE_ACP, encoding="utf-8")
    r = devin_tasks.run("hi", cwd=str(tmp_path), engine="acp",
                        session_id="prev-9",
                        exe=[sys.executable, str(fake)],
                        live_dir=str(tmp_path))
    s = _wait(r["task_id"])
    assert s["session_id"] == "prev-9"


def test_acp_requires_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: None)
    exe = tmp_path / "devin.exe"
    exe.write_bytes(b"x")
    with pytest.raises(devin_tasks.TaskError, match="credentials"):
        devin_tasks.run("hi", cwd=str(tmp_path), engine="acp",
                        exe=str(exe), live_dir=str(tmp_path))


def test_acp_persistent_session(monkeypatch, tmp_path):
    """AcpSession: promptを複数回送れる常駐セッション。"""
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: "k")
    fake = tmp_path / "fake_acp.py"
    fake.write_text(_FAKE_ACP, encoding="utf-8")
    s = devin_tasks.AcpSession(
        str(tmp_path), exe=[sys.executable, str(fake)], mode=None)
    try:
        got = []
        s.on_update = got.append
        r = s.prompt([{"type": "text", "text": "hello"}])
        assert r["stopReason"] == "end_turn"
        assert s.session_id == "fake-s1"
        assert any(u.get("sessionUpdate") == "agent_message_chunk"
                   for u in got)
        # 2回目のpromptも同じセッションで通る
        r2 = s.prompt([{"type": "text", "text": "again"}])
        assert r2["stopReason"] == "end_turn"
        # permission 自動応答(allow_always)が chunk テキストに反映
        txt = "".join((u.get("content") or {}).get("text", "")
                      for u in got)
        assert "perm=allow_always" in txt
        # cancelは通知なので例外にならない
        s.cancel()
    finally:
        s.close()
    assert s._closed


def test_acp_session_load_resume(monkeypatch, tmp_path):
    """AcpSession: session_id 指定で session/load による再開。"""
    monkeypatch.setattr(devin_tasks, "_ide_api_key", lambda: "k")
    fake = tmp_path / "fake_acp.py"
    fake.write_text(_FAKE_ACP, encoding="utf-8")
    s = devin_tasks.AcpSession(
        str(tmp_path), exe=[sys.executable, str(fake)],
        session_id="prev-9", mode=None)
    try:
        assert s.session_id == "prev-9"
    finally:
        s.close()


def test_acp_session_copilot_engine(tmp_path):
    """engine='copilot' ではIDE認証情報が無くてもセッションを張れる
    (認証はCLI側のghログインに委譲。fake serverはauthMethodsを
    返さないため authenticate もスキップされる)。"""
    fake = tmp_path / "fake_acp.py"
    fake.write_text(_FAKE_ACP, encoding="utf-8")
    s = devin_tasks.AcpSession(
        str(tmp_path), exe=[sys.executable, str(fake)],
        engine="copilot", mode=None)
    try:
        assert s.session_id == "fake-s1"
        r = s.prompt([{"type": "text", "text": "hi"}])
        assert r["stopReason"] == "end_turn"
    finally:
        s.close()


def test_copilot_argv(monkeypatch):
    """specが取れればそれ+--acp --stdio、無ければcmd経由のargv。"""
    monkeypatch.setattr(devin_tasks, "_copilot_exe_spec",
                        lambda: ["copilot.exe"])
    assert devin_tasks._copilot_argv() == [
        "copilot.exe", "--acp", "--stdio"]
    monkeypatch.setattr(devin_tasks, "_copilot_exe_spec",
                        lambda: None)
    argv = devin_tasks._copilot_argv()
    assert "copilot --acp --stdio" in argv


def test_build_copilot_argv(monkeypatch):
    """copilot -p のargv構築(権限・モデル・再開)。"""
    monkeypatch.setattr(devin_tasks, "_copilot_exe_spec",
                        lambda: ["node", "loader.js"])
    a = devin_tasks._build_copilot_argv("do it", model="m1")
    assert a[:4] == ["node", "loader.js", "-s", "-p"]
    assert a[4] == "do it" and "--model" in a
    a2 = devin_tasks._build_copilot_argv(
        "x", session_id="s9", permission_mode="accept-edits")
    assert "--allow-all-tools" in a2
    assert a2[a2.index("-r") + 1] == "s9"
    with pytest.raises(devin_tasks.TaskError, match="permission_mode"):
        devin_tasks._build_copilot_argv("x", permission_mode="smart")


def test_copilot_print_task(monkeypatch, tmp_path):
    """agent='copilot' のprintタスク(id接頭辞・cwd・環境)。"""
    fake = tmp_path / "say.py"
    fake.write_text("import sys; print('CP-OK')", encoding="utf-8")
    r = devin_tasks.run("hi", cwd=str(tmp_path), agent="copilot",
                        exe=[sys.executable, str(fake)],
                        live_dir=str(tmp_path))
    assert r["task_id"].startswith("copilot-")
    s = _wait(r["task_id"])
    assert s["state"] == "exited"
    assert s["agent"] == "copilot"
    assert "CP-OK" in devin_tasks.result(r["task_id"])["output"]


def test_copilot_acp_task(monkeypatch, tmp_path):
    """agent='copilot'+engine='acp' はIDE認証不要でACPワーカーが動く。"""
    fake = tmp_path / "fake_acp.py"
    fake.write_text(_FAKE_ACP, encoding="utf-8")
    r = devin_tasks.run("hi", cwd=str(tmp_path), agent="copilot",
                        engine="acp",
                        exe=[sys.executable, str(fake)],
                        live_dir=str(tmp_path))
    s = _wait(r["task_id"])
    assert s["state"] == "exited"
    assert "HELLO-ACP" in devin_tasks.result(r["task_id"])["output"]
