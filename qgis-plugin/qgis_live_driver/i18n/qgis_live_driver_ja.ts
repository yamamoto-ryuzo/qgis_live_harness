<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="ja_JP">
<context>
    <name>AiPanel</name>
    <message>
        <location filename="../ai_panel.py" line="206" />
        <source>API settings</source>
        <translation>API設定</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="226" />
        <source>Model to use. Press "Fetch" to list models from the endpoint.
Values in parentheses are prices per 1M tokens (input/output, $).
Models in the "Text (image input)" group support sending screenshots.</source>
        <translation>使用するモデル。「取得」でエンドポイントの一覧を表示。
括弧内は1Mトークンあたりの価格(入力/出力, $)。
「画像入力可」グループのモデルはスクリーンショット送信に対応。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="230" />
        <source>Fetch</source>
        <translation>取得</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="233" />
        <source>Fetch the model list from the endpoint (GET {base}/models)</source>
        <translation>エンドポイントからモデル一覧を取得 (GET {base}/models)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="242" />
        <source>Confirm before running tools</source>
        <translation>ツール実行の前に確認する</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="246" />
        <source>When ON, asks for approval before each tool call.
Use this if you do not want arbitrary code execution (pyeval) to run automatically.</source>
        <translation>ONにするとツール呼び出しごとに実行可否を確認する。
任意コード実行(pyeval)を自動で回したくない場合に。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="255" />
        <source>Instruction document (agent) injected on every request.
Lists ~/.qgis-live/agents/*.md. Use "Edit" to create or modify.</source>
        <translation>常時注入する指示書(エージェント)。
~/.qgis-live/agents/*.md を列挙。「編集」で作成・修正</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="256" />
        <location filename="../ai_panel.py" line="275" />
        <source>Edit</source>
        <translation>編集</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="258" />
        <source>Create, edit, or delete agent instructions (.md)</source>
        <translation>エージェント指示書(.md)の作成・編集・削除</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="261" />
        <source>Agent</source>
        <translation>エージェント</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="274" />
        <source>On-demand instruction documents. All entries appear in the prompt list,
and the model reads the body via qgis_pyeval's open() when needed.
Lists ~/.qgis-live/skills/*.md. Use "Edit" to create or modify.</source>
        <translation>オンデマンドの手順書。全件がプロンプトの一覧に載り、
モデルが必要時に qgis_pyeval の open() で本文を読む。
~/.qgis-live/skills/*.md を列挙。「編集」で作成・修正</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="277" />
        <source>Create, edit, or delete skill instructions (.md)</source>
        <translation>スキル指示書(.md)の作成・編集・削除</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="280" />
        <source>Skill</source>
        <translation>スキル</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="285" />
        <location filename="../ai_panel.py" line="612" />
        <source>Not configured</source>
        <translation>未設定</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="287" />
        <source>Configure</source>
        <translation>設定</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="292" />
        <source>Edit external MCP server settings (mcp_servers.json).
command=launch via stdio / url=Streamable HTTP.
Discovered tools become usable as mcp_&lt;server&gt;__&lt;tool&gt;.</source>
        <translation>外部MCPサーバの設定(mcp_servers.json)を編集。
command=stdio起動 / url=Streamable HTTP。
発見したツールは mcp_&lt;サーバ&gt;__&lt;ツール&gt; として使える</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="301" />
        <source>Sign in with GitHub</source>
        <translation>GitHubでサインイン</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="307" />
        <source>Acquires a GitHub token via the OAuth device flow and sets it in the API key field.
Enter the displayed code in the browser (github.com/login/device).
Requires an account with a GitHub Copilot subscription.</source>
        <translation>OAuthデバイスフローでGitHubトークンを取得しAPIキー欄に設定。
表示されるコードをブラウザ(github.com/login/device)で入力。
GitHub Copilotの契約があるアカウントが必要。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="310" />
        <source>GitHub account with a Copilot subscription</source>
        <translation>Copilot契約のGitHubアカウント</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="315" />
        <source>Provider</source>
        <translation>プロバイダ</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="316" />
        <source>Endpoint</source>
        <translation>エンドポイント</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="317" />
        <source>API key</source>
        <translation>APIキー</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="319" />
        <source>Key storage</source>
        <translation>キー保存先</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="320" />
        <source>Model</source>
        <translation>モデル</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="332" />
        <source>Toggle visibility of the API settings</source>
        <translation>API設定の表示/非表示を切り替える</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="334" />
        <source>New chat</source>
        <translation>新しいチャット</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="337" />
        <source>Saves the current chat to history and starts a new one.
The context (conversation history) is also reset.</source>
        <translation>現在のチャットを履歴へ保存し、新規チャットを開始。
コンテキスト(会話履歴)もリセットされる。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="341" />
        <source>Past chats. Select one to review it or continue the conversation.</source>
        <translation>過去のチャット。選択で再表示・会話の継続ができる</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="342" />
        <location filename="../ai_panel.py" line="1131" />
        <source>Current chat</source>
        <translation>現在のチャット</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="348" />
        <source>Save the displayed chat to a Markdown file</source>
        <translation>表示中のチャットをMarkdownファイルに保存</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="354" />
        <source>Delete the displayed history chat (the current chat is excluded)</source>
        <translation>表示中の履歴チャットを削除(現在のチャットは対象外)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="380" />
        <source>Enter instructions (Enter to send / Shift+Enter for a new line / Ctrl+V or drag &amp; drop to attach images).
Use /agent and /skill to edit instructions directly (/help)</source>
        <translation>指示を入力 (Enterで送信 / Shift+Enterで改行 / Ctrl+Vやドラッグ&amp;ドロップで画像添付)。
/agent・/skill で指示書を直接編集 (/help)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="390" />
        <location filename="../ai_panel.py" line="858" />
        <source>Attach and send an image file.
You can also paste (Ctrl+V) or drag &amp; drop into the input field.</source>
        <translation>画像ファイルを添付して送信。
入力欄への貼付(Ctrl+V)・ドラッグ&amp;ドロップでも追加できる。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="392" />
        <location filename="../ai_panel.py" line="939" />
        <source>Send</source>
        <translation>送信</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="397" />
        <source>Enter also sends. While sending it changes to "Abort" and
stops the ongoing round trip (in-flight API responses/tool executions cannot be interrupted).</source>
        <translation>Enterでも送信できる。送信中は「中断」に変わり
実行中の往復を止める(進行中のAPI応答/ツール実行の
完了待ちは中断できない)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="398" />
        <source>Retry</source>
        <translation>再送</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="401" />
        <source>Discard the last question and its response, then resend</source>
        <translation>最後の質問とその応答を取り消して再送信する</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="402" />
        <source>Clear history</source>
        <translation>履歴クリア</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="416" />
        <source>ctx: context usage (measured prompt_tokens from the last API response;
if unavailable, an estimate marked with ~ using chars/3). The right value is the model limit.
Σ: total tokens for this chat. $: estimated cost (when pricing info is available)</source>
        <translation>ctx: コンテキスト使用量(直近API応答のprompt_tokens実測値、
未取得時は~付きで文字数÷3の推定)。右はモデルの上限。
Σ: このチャットの累計トークン。$: 推定コスト(価格情報時)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="499" />
        <location filename="../ai_panel.py" line="532" />
        <location filename="../ai_panel.py" line="1490" />
        <source>(none)</source>
        <translation>(なし)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="535" />
        <source> (bundled)</source>
        <translation> (同梱)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="608" />
        <source>Config error: {0}</source>
        <translation>設定エラー: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="611" />
        <source>{0} server(s)</source>
        <translation>{0}サーバ</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="642" />
        <source>MCP server not configured</source>
        <translation>MCPサーバ未設定</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="645" />
        <source>Connecting to MCP servers…</source>
        <translation>MCPサーバへ接続中…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="659" />
        <source>MCP '{0}' connection failed: {1}</source>
        <translation>MCP '{0}' 接続失敗: {1}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="663" />
        <source>MCP connected: </source>
        <translation>MCP接続: </translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="664" />
        <source>{0} ({1} tools)</source>
        <translation>{0}({1}ツール)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="748" />
        <source>Could not save the API key to the OS credential store (backend={0}). It is not saved in plain text. The entered key can be used in this session, but you will need to re-enter it next time.</source>
        <translation>APIキーをOS資格情報ストアに保存できませんでした (backend={0})。平文での保存はしません。このセッション内では入力中のキーを使えますが、次回起動時は再入力が必要です。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="863" />
        <source>The selected model does not support image input, so attachments are unavailable.
Select a model from the "Text (image input)" group.</source>
        <translation>選択中のモデルは画像入力に対応していないため添付できません。
「画像入力可」グループのモデルを選んでください。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="875" />
        <source>ref</source>
        <translation>参考</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="879" />
        <source>context {0}</source>
        <translation>コンテキスト {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="883" />
        <source>may not support image input (select a "Text (image input)" model to send images)</source>
        <translation>画像入力非対応の可能性(画像送信には「画像入力可」モデルを選択)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="885" />
        <source>not usable for chat</source>
        <translation>チャット用途には使えません</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="901" />
        <source>you</source>
        <translation>あなた</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="923" />
        <source>Running…</source>
        <translation>実行中…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="934" />
        <source>■ Abort</source>
        <translation>■ 中断</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="961" />
        <source>The selected model does not support image input, so attachments are unavailable (select a model from the "Text (image input)" group)</source>
        <translation>選択中のモデルは画像入力に対応していないため添付できません(「画像入力可」グループのモデルを選んでください)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="972" />
        <source>Cannot read as an image: {0}</source>
        <translation>画像として読めません: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="973" />
        <source>(pasted image)</source>
        <translation>(貼付画像)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="983" />
        <source>Failed to save the attached image: {0}</source>
        <translation>添付画像の保存に失敗: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="998" />
        <source>Remove this image</source>
        <translation>この画像を取り除く</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1032" />
        <source>Attach image</source>
        <translation>画像を添付</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1034" />
        <source>Image files (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</source>
        <translation>画像ファイル (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1088" />
        <source>Chat {0}</source>
        <translation>チャット{0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1171" />
        <source>Chat</source>
        <translation>チャット</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1198" />
        <source>Nothing to save</source>
        <translation>保存する内容がありません</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1202" />
        <source>Save chat</source>
        <translation>チャットを保存</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1209" />
        <source>Chat saved: {0}</source>
        <translation>チャットを保存しました: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1212" />
        <source>Failed to save: {0}</source>
        <translation>保存に失敗しました: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1243" />
        <source>Fetching model list…</source>
        <translation>モデル一覧取得中…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1260" />
        <source>Failed to fetch the model list: {0}</source>
        <translation>モデル一覧の取得に失敗: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1264" />
        <source>Fetched {0} model(s)</source>
        <translation>モデル一覧を{0}件取得しました</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1285" />
        <source>Failed to get a device code for sign-in: {0}</source>
        <translation>サインイン用デバイスコードの取得に失敗: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1292" />
        <source>GitHub sign-in: open {0} and enter code {1}</source>
        <translation>GitHubサインイン: {0} を開きコード {1} を入力</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1295" />
        <source>Entering code {0} on GitHub…</source>
        <translation>GitHubでコード {0} を入力中…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1303" />
        <source>Aborted</source>
        <translation>中止しました</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1308" />
        <source>Polling failed: {0}</source>
        <translation>ポーリング失敗: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1323" />
        <source>GitHub sign-in completed. The token was set in the API key field</source>
        <translation>GitHubサインイン完了。トークンをAPIキー欄に設定しました</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1327" />
        <source>GitHub sign-in: {0}</source>
        <translation>GitHubサインイン: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1327" />
        <source>Code expired</source>
        <translation>コードの有効期限切れ</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1345" />
        <location filename="../ai_panel.py" line="1347" />
        <source>Aborting…</source>
        <translation>中断中…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1388" />
        <source>Cannot send while running (retry after it completes)</source>
        <translation>実行中のため送信できません(完了後に再送)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1398" />
        <source>The selected model does not support image input, so images cannot be sent (select a model from the "Text (image input)" group)</source>
        <translation>選択中のモデルは画像入力に対応していないため画像を送信できません(「画像入力可」グループのモデルを選んでください)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1412" />
        <source>could not prepare the live driver</source>
        <translation>live driverを用意できませんでした</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1434" />
        <source>(image only)</source>
        <translation>(画像のみ)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1489" />
        <source>Selected: {0}</source>
        <translation>選択中: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1511" />
        <source>agent '{0}' not found (provide a body to save it as new)</source>
        <translation>エージェント '{0}' が見つかりません(本文付きなら新規保存します)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1514" />
        <source>Switched agent to '{0}'</source>
        <translation>エージェントを '{0}' に切替えました</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1524" />
        <source>skill '{0}' not found (provide a body to save it as new)</source>
        <translation>スキル '{0}' が見つかりません(本文付きなら新規保存します)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1532" />
        <source>agent</source>
        <translation>エージェント</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1533" />
        <source>skill</source>
        <translation>スキル</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1538" />
        <source>{0} '{1}' saved and selected
{2}</source>
        <translation>{0} '{1}' を保存して選択しました
{2}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1541" />
        <source>{0} '{1}' saved
{2}</source>
        <translation>{0} '{1}' を保存しました
{2}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1571" />
        <source>(aborted)</source>
        <translation>(中断しました)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1574" />
        <source>Waiting for API response…</source>
        <translation>API応答待ち…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1613" />
        <source>(tool round-trip limit reached)</source>
        <translation>(ツール往復の上限に達しました)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1643" />
        <source>{0} → skipped by user</source>
        <translation>{0} → ユーザーによりスキップ</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1660" />
        <location filename="../ai_panel.py" line="1683" />
        <location filename="../ai_panel.py" line="1715" />
        <source>{0} running…</source>
        <translation>{0} 実行中…</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1746" />
        <source>Confirm tool execution</source>
        <translation>ツール実行の確認</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1747" />
        <source>Run {0}?

{1}</source>
        <translation>{0} を実行しますか?

{1}</translation>
    </message>
</context>
<context>
    <name>_InstructionsDialog</name>
    <message>
        <location filename="../ai_panel.py" line="1880" />
        <source>Edit instructions (agents/skills)</source>
        <translation>指示書編集 (エージェント/スキル)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1893" />
        <source>Name (file name; saved as &lt;name&gt;.md. e.g. map-design)</source>
        <translation>名前 (ファイル名。&lt;名前&gt;.md で保存。例: map-design)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1897" />
        <source>Edit (Markdown)</source>
        <translation>編集 (Markdown)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1902" />
        <source>Preview</source>
        <translation>表示</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1929" />
        <source>Edit instructions for the AI (Enter to send)</source>
        <translation>AIへの修正指示 (Enterで送信)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1933" />
        <source>e.g. "Add a summary section" "Make the tone more concise"</source>
        <translation>例: 「要約の節を追加して」「トーンを簡潔に」</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1935" />
        <source>Ask AI to revise</source>
        <translation>AIに修正を依頼</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1941" />
        <source>Send the editor body and the instructions above to the chat AI.
When the AI saves, the result is reflected in the editor (not while there are unsaved manual edits)</source>
        <translation>編集欄の本文と上の指示をチャットのAIへ送る。
AIが保存すると編集欄へ反映される(未保存の手編集が
ある間は反映しない)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1946" />
        <source>Save</source>
        <translation>保存</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1947" />
        <location filename="../ai_panel.py" line="2134" />
        <source>Delete</source>
        <translation>削除</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1949" />
        <source>Open folder</source>
        <translation>フォルダを開く</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1950" />
        <source>Close</source>
        <translation>閉じる</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2011" />
        <source>Agents: the selected one is injected into the system prompt on every request. Format: "# Title" → description → "use_when: when to use" (optional)</source>
        <translation>エージェント: 選択中は毎回system promptに注入。書式: 「# タイトル」→説明文→「use_when: 使いどき」(省略可)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2017" />
        <source>Skills: only the list of id+description+use_when appears in the prompt; the model reads the body via qgis_pyeval's open() when needed. Format: "# Title" → description → "use_when: when to use" (optional)</source>
        <translation>スキル: id+説明+use_when の一覧のみプロンプトに載り、モデルが必要時に qgis_pyeval の open() で本文を読む。書式: 「# タイトル」→説明文→「use_when: 使いどき」(省略可)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2027" />
        <source>+ New {0}</source>
        <translation>＋ 新規{0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2030" />
        <source> (bundled)</source>
        <translation> (同梱)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2116" />
        <source>Save failed</source>
        <translation>保存失敗</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2129" />
        <source>Cannot delete</source>
        <translation>削除不可</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2131" />
        <source>Instructions bundled with the plugin cannot be deleted</source>
        <translation>プラグイン同梱の指示書は削除できません</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="2136" />
        <source>Delete {0} '{1}'?</source>
        <translation>{0} '{1}' を削除しますか?</translation>
    </message>
</context>
<context>
    <name>_McpDialog</name>
    <message>
        <location filename="../ai_panel.py" line="1765" />
        <source>External MCP server settings</source>
        <translation>外部MCPサーバ設定</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1780" />
        <source>Configure external MCP servers in {"mcpServers": {...}} format.
command=launch via stdio / url=Streamable HTTP. Discovered tools are usable as mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret is moved to the OS credential store on save, leaving only a $store: reference in the config file.
Saving an empty field disables MCP servers, and saving reconnects on the next send.</source>
        <translation>外部MCPサーバを {"mcpServers": {...}} 形式で設定します。
command=stdio起動 / url=Streamable HTTP。発見したツールは mcp_&lt;サーバ&gt;__&lt;ツール&gt; で使えます。
oauth.client_secret は保存時にOSの資格情報ストアへ移され、設定ファイルには $store: 参照だけが残ります。
空欄で保存するとMCPサーバなし(無効)になり、保存すると次の送信で再接続されます。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1795" />
        <source>Connection examples</source>
        <translation>接続例</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1809" />
        <source>Insert example into editor</source>
        <translation>例をエディタへ挿入</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1813" />
        <source>Save</source>
        <translation>保存</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1814" />
        <source>Close</source>
        <translation>閉じる</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1828" />
        <location filename="../ai_panel.py" line="1847" />
        <location filename="../ai_panel.py" line="1856" />
        <source>MCP settings</source>
        <translation>MCP設定</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1830" />
        <source>Cannot read JSON: {0}</source>
        <translation>JSONが読めません: {0}</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1859" />
        <source>Moved client_secret to the OS credential store; only a $store: reference remains in the config file.</source>
        <translation>client_secret をOSの資格情報ストアへ移し、設定ファイルには $store: 参照だけ残しました。</translation>
    </message>
</context>
<context>
    <name>qgis_live_driver</name>
    <message>
        <location filename="../__init__.py" line="169" />
        <location filename="../ai_panel.py" line="173" />
        <source>AI Assistant</source>
        <translation>AI アシスタント</translation>
    </message>
    <message>
        <location filename="../__init__.py" line="176" />
        <source>Remote Control (localhost only)</source>
        <translation>リモート制御 (localhostのみ)</translation>
    </message>
    <message>
        <location filename="../__init__.py" line="202" />
        <source>Hot Reload</source>
        <translation>ホットリロード</translation>
    </message>
    <message>
        <location filename="../__init__.py" line="221" />
        <source>Reload All</source>
        <translation>すべて再読込</translation>
    </message>
    <message>
        <location filename="../__init__.py" line="326" />
        <source>Local (localhost) clients will be able to remotely control this QGIS process.
pyeval executes arbitrary Python inside QGIS.

Access is protected by a per-session token stored only in a user-private file, but only trusted processes should run under your account.

Enable it?</source>
        <translation>ローカル(localhost)のクライアントからQGIS内部を遠隔操作できるようになります。
pyeval はQGISプロセス内で任意のPythonを実行します。

アクセスは起動ごとのセッショントークンで保護され、トークンはユーザ専用ファイルにのみ保存されますが、同一ユーザで動くプロセスは信頼できるものだけにしてください。

有効にしますか?</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="70" />
        <source>Press "Fetch" to list models from the endpoint. Values in parentheses are prices (input/output, $/1M tokens, reference only).</source>
        <translation>「取得」でエンドポイントのモデル一覧を表示。括弧内は価格(入力/出力, $/1Mトークン, 参考値)。</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="182" />
        <source>Current chat</source>
        <translation>現在のチャット</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1463" />
        <source>Instruction commands (run locally, not sent to the API):
  /agent               Show the current agent and list
  /agent &lt;name&gt;        Switch agent
  /agent &lt;name&gt; &lt;body&gt; Save an agent and select it
  /skill               List skills
  /skill &lt;name&gt;        Show a skill's body
  /skill &lt;name&gt; &lt;body&gt; Save a skill
(The body can span multiple lines starting from line 2)</source>
        <translation>指示書コマンド(APIへは送らずローカル実行):
  /agent               現在のエージェントと一覧
  /agent &lt;名前&gt;        エージェントを切替
  /agent &lt;名前&gt; &lt;本文&gt; エージェントを保存して選択
  /skill               スキル一覧
  /skill &lt;名前&gt;        スキル本文を表示
  /skill &lt;名前&gt; &lt;本文&gt; スキルを保存
(本文は2行目以降に改行して書ける)</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1873" />
        <source>Agents</source>
        <translation>エージェント</translation>
    </message>
    <message>
        <location filename="../ai_panel.py" line="1875" />
        <source>Skills</source>
        <translation>スキル</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="67" />
        <source>Input {0} / Output {1} /1M tokens</source>
        <translation>入力 {0} / 出力 {1} /1Mトークン</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="69" />
        <source>{0} /image (image generation)</source>
        <translation>{0} /枚(画像生成)</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="70" />
        <source>Kind: {0}</source>
        <translation>種別: {0}</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="71" />
        <source>Price: {0} ({1})</source>
        <translation>価格: {0} ({1})</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="72" />
        <source>Context: {0} tokens</source>
        <translation>コンテキスト: {0} tokens</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="73" />
        <source>API value</source>
        <translation>API応答値</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="76" />
        <source>reference</source>
        <translation>参考値</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="121" />
        <source>OpenAI-compatible</source>
        <translation>OpenAI互換</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="126" />
        <source>API key (may be empty for local servers)</source>
        <translation>APIキー (ローカルサーバ等では空可)</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="129" />
        <source>https://api.openai.com/v1  or  http://localhost:11434/v1</source>
        <translation>https://api.openai.com/v1  または  http://localhost:11434/v1</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="137" />
        <source>Gemini API key (issued in AI Studio)</source>
        <translation>Gemini APIキー (AI Studioで発行)</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="147" />
        <source>GitHub token (Copilot subscription required; can be acquired automatically via "Sign in with GitHub")</source>
        <translation>GitHubトークン (Copilot契約必須。「GitHubでサインイン」で自動取得可)</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="151" />
        <source>https://api.githubcopilot.com  (URL of a compatible proxy such as copilot-api)</source>
        <translation>https://api.githubcopilot.com  (copilot-api等の互換プロキシはそのURL)</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="160" />
        <source>Text (image input)</source>
        <translation>テキスト (画像入力可)</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="161" />
        <source>Text</source>
        <translation>テキスト</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="162" />
        <source>Image generation</source>
        <translation>画像生成</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="163" />
        <source>Embedding</source>
        <translation>埋め込み</translation>
    </message>
    <message>
        <location filename="../ai_client.py" line="164" />
        <source>Audio/Other</source>
        <translation>音声/その他</translation>
    </message>
    <message>
        <location filename="../credential_store.py" line="44" />
        <source>Windows DPAPI (encrypted under the user account, same mechanism as browser password storage)</source>
        <translation>Windows DPAPI (ユーザアカウントに紐付け暗号化。ブラウザのパスワード保存と同じ仕組み)</translation>
    </message>
    <message>
        <location filename="../credential_store.py" line="45" />
        <source>macOS Keychain</source>
        <translation>macOS キーチェーン</translation>
    </message>
    <message>
        <location filename="../credential_store.py" line="50" />
        <source>~/.qgis-live/ai-secrets.json (mode 600, plain text; no keyring available)</source>
        <translation>~/.qgis-live/ai-secrets.json (600権限・平文。キーリング未導入のため)</translation>
    </message>
    <message>
        <location filename="../hot_reload.py" line="58" />
        <source>Hot Reload: {0}</source>
        <translation>ホットリロード: {0}</translation>
    </message>
    <message>
        <location filename="../hot_reload.py" line="61" />
        <source> (dialog reopened)</source>
        <translation> (ダイアログ再表示)</translation>
    </message>
    <message>
        <location filename="../hot_reload.py" line="64" />
        <source>Hot Reload failed: {0}</source>
        <translation>ホットリロード失敗: {0}</translation>
    </message>
</context>
</TS>