<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="zh_CN">
    <context>
        <name>AiPanel</name>
        <message>
            <location filename="../ai_panel.py" line="206" />
            <source>API settings</source>
            <translation>API 设置</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="226" />
            <source>Model to use. Press "Fetch" to list models from the endpoint.
Values in parentheses are prices per 1M tokens (input/output, $).
Models in the "Text (image input)" group support sending screenshots.</source>
            <translation>要使用的模型。按“获取”从端点列出模型。
括号内的值为每 100 万 token 的价格(输入/输出,美元)。
“Text (image input)”组中的模型支持发送屏幕截图。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="230" />
            <source>Fetch</source>
            <translation>获取</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="233" />
            <source>Fetch the model list from the endpoint (GET {base}/models)</source>
            <translation>从端点获取模型列表(GET {base}/models)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="242" />
            <source>Confirm before running tools</source>
            <translation>运行工具前确认</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="246" />
            <source>When ON, asks for approval before each tool call.
Use this if you do not want arbitrary code execution (pyeval) to run automatically.</source>
            <translation>开启时,每次工具调用前都会请求批准。
如果您不希望任意代码执行(pyeval)自动运行,请使用此选项。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="255" />
            <source>Instruction document (agent) injected on every request.
Lists ~/.qgis-live/agents/*.md. Use "Edit" to create or modify.</source>
            <translation>每次请求时注入的指示文档(代理)。
列出 ~/.qgis-live/agents/*.md。使用“编辑”创建或修改。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="256" />
            <location filename="../ai_panel.py" line="275" />
            <source>Edit</source>
            <translation>编辑</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="258" />
            <source>Create, edit, or delete agent instructions (.md)</source>
            <translation>创建、编辑或删除代理指示(.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="261" />
            <source>Agent</source>
            <translation>代理</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="274" />
            <source>On-demand instruction documents. All entries appear in the prompt list,
and the model reads the body via qgis_pyeval's open() when needed.
Lists ~/.qgis-live/skills/*.md. Use "Edit" to create or modify.</source>
            <translation>按需指示文档。所有条目都会出现在提示列表中,
模型在需要时通过 qgis_pyeval 的 open() 读取内容。
列出 ~/.qgis-live/skills/*.md。使用“编辑”创建或修改。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="277" />
            <source>Create, edit, or delete skill instructions (.md)</source>
            <translation>创建、编辑或删除技能指示(.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="280" />
            <source>Skill</source>
            <translation>技能</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="285" />
            <location filename="../ai_panel.py" line="612" />
            <source>Not configured</source>
            <translation>未配置</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="287" />
            <source>Configure</source>
            <translation>配置</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="292" />
            <source>Edit external MCP server settings (mcp_servers.json).
command=launch via stdio / url=Streamable HTTP.
Discovered tools become usable as mcp_&lt;server&gt;__&lt;tool&gt;.</source>
            <translation>编辑外部 MCP 服务器设置(mcp_servers.json)。
command=通过 stdio 启动 / url=Streamable HTTP。
发现的工具可作为 mcp_&lt;服务器&gt;__&lt;工具&gt; 使用。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="301" />
            <source>Sign in with GitHub</source>
            <translation>使用 GitHub 登录</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="307" />
            <source>Acquires a GitHub token via the OAuth device flow and sets it in the API key field.
Enter the displayed code in the browser (github.com/login/device).
Requires an account with a GitHub Copilot subscription.</source>
            <translation>通过 OAuth 设备流程获取 GitHub 令牌并填入 API 密钥字段。
在浏览器中输入显示的代码(github.com/login/device)。
需要拥有 GitHub Copilot 订阅的账户。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="310" />
            <source>GitHub account with a Copilot subscription</source>
            <translation>拥有 Copilot 订阅的 GitHub 账户</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="315" />
            <source>Provider</source>
            <translation>提供商</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="316" />
            <source>Endpoint</source>
            <translation>端点</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="317" />
            <source>API key</source>
            <translation>API 密钥</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="319" />
            <source>Key storage</source>
            <translation>密钥存储</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="320" />
            <source>Model</source>
            <translation>模型</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="332" />
            <source>Toggle visibility of the API settings</source>
            <translation>切换 API 设置的可见性</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="334" />
            <source>New chat</source>
            <translation>新聊天</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="337" />
            <source>Saves the current chat to history and starts a new one.
The context (conversation history) is also reset.</source>
            <translation>将当前聊天保存到历史记录并开始新聊天。
上下文(对话历史)也会被重置。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="341" />
            <source>Past chats. Select one to review it or continue the conversation.</source>
            <translation>过去的聊天。选择一个以查看或继续对话。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="342" />
            <location filename="../ai_panel.py" line="1131" />
            <source>Current chat</source>
            <translation>当前聊天</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="348" />
            <source>Save the displayed chat to a Markdown file</source>
            <translation>将显示的聊天保存为 Markdown 文件</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="354" />
            <source>Delete the displayed history chat (the current chat is excluded)</source>
            <translation>删除显示的历史聊天(不包括当前聊天)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="380" />
            <source>Enter instructions (Enter to send / Shift+Enter for a new line / Ctrl+V or drag &amp; drop to attach images).
Use /agent and /skill to edit instructions directly (/help)</source>
            <translation>输入指示(Enter 发送 / Shift+Enter 换行 / Ctrl+V 或拖放以附加图片)。
使用 /agent 和 /skill 直接编辑指示(/help)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="390" />
            <location filename="../ai_panel.py" line="858" />
            <source>Attach and send an image file.
You can also paste (Ctrl+V) or drag &amp; drop into the input field.</source>
            <translation>附加并发送图片文件。
也可以粘贴(Ctrl+V)或拖放到输入框中。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="392" />
            <location filename="../ai_panel.py" line="939" />
            <source>Send</source>
            <translation>发送</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="397" />
            <source>Enter also sends. While sending it changes to "Abort" and
stops the ongoing round trip (in-flight API responses/tool executions cannot be interrupted).</source>
            <translation>Enter 也可发送。发送时会变为“中止”并
停止正在进行的往返(进行中的 API 响应/工具执行无法中断)。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="398" />
            <source>Retry</source>
            <translation>重试</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="401" />
            <source>Discard the last question and its response, then resend</source>
            <translation>放弃最后一个问题及其回答,然后重新发送</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="402" />
            <source>Clear history</source>
            <translation>清除历史记录</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="416" />
            <source>ctx: context usage (measured prompt_tokens from the last API response;
if unavailable, an estimate marked with ~ using chars/3). The right value is the model limit.
Σ: total tokens for this chat. $: estimated cost (when pricing info is available)</source>
            <translation>ctx: 上下文用量(最近一次 API 响应实测的 prompt_tokens;
不可用时为以字符数/3 估算、带 ~ 标记的数值)。右侧数值为模型上限。
Σ: 本聊天的总 token。$: 估算费用(有价格信息时)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="499" />
            <location filename="../ai_panel.py" line="532" />
            <location filename="../ai_panel.py" line="1490" />
            <source>(none)</source>
            <translation>(无)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="535" />
            <source> (bundled)</source>
            <translation>(内置)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="608" />
            <source>Config error: {0}</source>
            <translation>配置错误: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="611" />
            <source>{0} server(s)</source>
            <translation>{0} 个服务器</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="642" />
            <source>MCP server not configured</source>
            <translation>未配置 MCP 服务器</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="645" />
            <source>Connecting to MCP servers…</source>
            <translation>正在连接 MCP 服务器…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="659" />
            <source>MCP '{0}' connection failed: {1}</source>
            <translation>MCP '{0}' 连接失败: {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="663" />
            <source>MCP connected: </source>
            <translation>MCP 已连接: </translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="664" />
            <source>{0} ({1} tools)</source>
            <translation>{0}({1} 个工具)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="748" />
            <source>Could not save the API key to the OS credential store (backend={0}). It is not saved in plain text. The entered key can be used in this session, but you will need to re-enter it next time.</source>
            <translation>无法将 API 密钥保存到操作系统凭据存储(backend={0})。它不会以明文保存。输入的密钥可在本次会话中使用,但下次需要重新输入。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="863" />
            <source>The selected model does not support image input, so attachments are unavailable.
Select a model from the "Text (image input)" group.</source>
            <translation>所选模型不支持图像输入,因此附件不可用。
请从“Text (image input)”组中选择模型。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="875" />
            <source>ref</source>
            <translation>参考</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="879" />
            <source>context {0}</source>
            <translation>上下文 {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="883" />
            <source>may not support image input (select a "Text (image input)" model to send images)</source>
            <translation>可能不支持图像输入(请选择“Text (image input)”模型以发送图片)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="885" />
            <source>not usable for chat</source>
            <translation>不可用于聊天</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="901" />
            <source>you</source>
            <translation>您</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="923" />
            <source>Running…</source>
            <translation>正在运行…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="934" />
            <source>■ Abort</source>
            <translation>■ 中止</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="961" />
            <source>The selected model does not support image input, so attachments are unavailable (select a model from the "Text (image input)" group)</source>
            <translation>所选模型不支持图像输入,因此附件不可用(请从“Text (image input)”组中选择模型)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="972" />
            <source>Cannot read as an image: {0}</source>
            <translation>无法作为图像读取: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="973" />
            <source>(pasted image)</source>
            <translation>(粘贴的图片)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="983" />
            <source>Failed to save the attached image: {0}</source>
            <translation>保存附加图片失败: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="998" />
            <source>Remove this image</source>
            <translation>移除此图片</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1032" />
            <source>Attach image</source>
            <translation>附加图片</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1034" />
            <source>Image files (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</source>
            <translation>图像文件(*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1088" />
            <source>Chat {0}</source>
            <translation>聊天 {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1171" />
            <source>Chat</source>
            <translation>聊天</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1198" />
            <source>Nothing to save</source>
            <translation>没有可保存的内容</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1202" />
            <source>Save chat</source>
            <translation>保存聊天</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1209" />
            <source>Chat saved: {0}</source>
            <translation>聊天已保存: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1212" />
            <source>Failed to save: {0}</source>
            <translation>保存失败: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1243" />
            <source>Fetching model list…</source>
            <translation>正在获取模型列表…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1260" />
            <source>Failed to fetch the model list: {0}</source>
            <translation>获取模型列表失败: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1264" />
            <source>Fetched {0} model(s)</source>
            <translation>已获取 {0} 个模型</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1285" />
            <source>Failed to get a device code for sign-in: {0}</source>
            <translation>获取登录设备代码失败: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1292" />
            <source>GitHub sign-in: open {0} and enter code {1}</source>
            <translation>GitHub 登录: 打开 {0} 并输入代码 {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1295" />
            <source>Entering code {0} on GitHub…</source>
            <translation>正在 GitHub 上输入代码 {0}…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1303" />
            <source>Aborted</source>
            <translation>已中止</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1308" />
            <source>Polling failed: {0}</source>
            <translation>轮询失败: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1323" />
            <source>GitHub sign-in completed. The token was set in the API key field</source>
            <translation>GitHub 登录完成。令牌已填入 API 密钥字段</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>GitHub sign-in: {0}</source>
            <translation>GitHub 登录: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>Code expired</source>
            <translation>代码已过期</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1345" />
            <location filename="../ai_panel.py" line="1347" />
            <source>Aborting…</source>
            <translation>正在中止…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1388" />
            <source>Cannot send while running (retry after it completes)</source>
            <translation>运行时无法发送(完成后请重试)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1398" />
            <source>The selected model does not support image input, so images cannot be sent (select a model from the "Text (image input)" group)</source>
            <translation>所选模型不支持图像输入,因此无法发送图片(请从“Text (image input)”组中选择模型)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1412" />
            <source>could not prepare the live driver</source>
            <translation>无法准备实时驱动程序</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1434" />
            <source>(image only)</source>
            <translation>(仅图片)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1489" />
            <source>Selected: {0}</source>
            <translation>已选择: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1511" />
            <source>agent '{0}' not found (provide a body to save it as new)</source>
            <translation>未找到代理 '{0}'(提供内容以将其另存为新代理)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1514" />
            <source>Switched agent to '{0}'</source>
            <translation>已切换到代理 '{0}'</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1524" />
            <source>skill '{0}' not found (provide a body to save it as new)</source>
            <translation>未找到技能 '{0}'(提供内容以将其另存为新技能)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1532" />
            <source>agent</source>
            <translation>代理</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1533" />
            <source>skill</source>
            <translation>技能</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1538" />
            <source>{0} '{1}' saved and selected
{2}</source>
            <translation>{0} '{1}' 已保存并选中
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1541" />
            <source>{0} '{1}' saved
{2}</source>
            <translation>{0} '{1}' 已保存
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1571" />
            <source>(aborted)</source>
            <translation>(已中止)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1574" />
            <source>Waiting for API response…</source>
            <translation>正在等待 API 响应…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1613" />
            <source>(tool round-trip limit reached)</source>
            <translation>(已达到工具往返上限)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1643" />
            <source>{0} → skipped by user</source>
            <translation>{0} → 已被用户跳过</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1660" />
            <location filename="../ai_panel.py" line="1683" />
            <location filename="../ai_panel.py" line="1715" />
            <source>{0} running…</source>
            <translation>{0} 正在运行…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1746" />
            <source>Confirm tool execution</source>
            <translation>确认工具执行</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1747" />
            <source>Run {0}?

{1}</source>
            <translation>运行 {0}?

{1}</translation>
        </message>
    </context>
    <context>
        <name>_InstructionsDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1880" />
            <source>Edit instructions (agents/skills)</source>
            <translation>编辑指示(代理/技能)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1893" />
            <source>Name (file name; saved as &lt;name&gt;.md. e.g. map-design)</source>
            <translation>名称(文件名;保存为 &lt;名称&gt;.md。例如 map-design)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1897" />
            <source>Edit (Markdown)</source>
            <translation>编辑(Markdown)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1902" />
            <source>Preview</source>
            <translation>预览</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1929" />
            <source>Edit instructions for the AI (Enter to send)</source>
            <translation>编辑给 AI 的指示(Enter 发送)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1933" />
            <source>e.g. "Add a summary section" "Make the tone more concise"</source>
            <translation>例如 “添加摘要部分” “让语气更简洁”</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1935" />
            <source>Ask AI to revise</source>
            <translation>请 AI 修改</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1941" />
            <source>Send the editor body and the instructions above to the chat AI.
When the AI saves, the result is reflected in the editor (not while there are unsaved manual edits)</source>
            <translation>将编辑器内容和上述指示发送给聊天 AI。
当 AI 保存时,结果会反映到编辑器中(存在未保存的手动编辑时除外)</translation>
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
            <translation>删除</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1949" />
            <source>Open folder</source>
            <translation>打开文件夹</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1950" />
            <source>Close</source>
            <translation>关闭</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2011" />
            <source>Agents: the selected one is injected into the system prompt on every request. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>代理: 所选代理会在每次请求时注入系统提示。格式:“# 标题” → 描述 → “use_when: 何时使用”(可选)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2017" />
            <source>Skills: only the list of id+description+use_when appears in the prompt; the model reads the body via qgis_pyeval's open() when needed. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>技能: 提示中只显示 id+描述+use_when 列表;模型在需要时通过 qgis_pyeval 的 open() 读取内容。格式:“# 标题” → 描述 → “use_when: 何时使用”(可选)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2027" />
            <source>+ New {0}</source>
            <translation>+ 新建{0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2030" />
            <source> (bundled)</source>
            <translation>(内置)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2116" />
            <source>Save failed</source>
            <translation>保存失败</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2129" />
            <source>Cannot delete</source>
            <translation>无法删除</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2131" />
            <source>Instructions bundled with the plugin cannot be deleted</source>
            <translation>插件内置的指示无法删除</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2136" />
            <source>Delete {0} '{1}'?</source>
            <translation>删除 {0} '{1}'?</translation>
        </message>
    </context>
    <context>
        <name>_McpDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1765" />
            <source>External MCP server settings</source>
            <translation>外部 MCP 服务器设置</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1780" />
            <source>Configure external MCP servers in {"mcpServers": {...}} format.
command=launch via stdio / url=Streamable HTTP. Discovered tools are usable as mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret is moved to the OS credential store on save, leaving only a $store: reference in the config file.
Saving an empty field disables MCP servers, and saving reconnects on the next send.</source>
            <translation>以 {"mcpServers": {...}} 格式配置外部 MCP 服务器。
command=通过 stdio 启动 / url=Streamable HTTP。发现的工具可作为 mcp_&lt;服务器&gt;__&lt;工具&gt; 使用。
oauth.client_secret 在保存时会移入操作系统凭据存储,配置文件中仅保留 $store: 引用。
保存空字段将禁用 MCP 服务器,保存后会在下次发送时重新连接。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1795" />
            <source>Connection examples</source>
            <translation>连接示例</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1809" />
            <source>Insert example into editor</source>
            <translation>将示例插入编辑器</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1813" />
            <source>Save</source>
            <translation>保存</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1814" />
            <source>Close</source>
            <translation>关闭</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1828" />
            <location filename="../ai_panel.py" line="1847" />
            <location filename="../ai_panel.py" line="1856" />
            <source>MCP settings</source>
            <translation>MCP 设置</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1830" />
            <source>Cannot read JSON: {0}</source>
            <translation>无法读取 JSON: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1859" />
            <source>Moved client_secret to the OS credential store; only a $store: reference remains in the config file.</source>
            <translation>client_secret 已移入操作系统凭据存储;配置文件中仅保留 $store: 引用。</translation>
        </message>
    </context>
    <context>
        <name>qgis_live_driver</name>
        <message>
            <location filename="../__init__.py" line="169" />
            <location filename="../ai_panel.py" line="173" />
            <source>AI Assistant</source>
            <translation>AI 助手</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="176" />
            <source>Remote Control (localhost only)</source>
            <translation>远程控制(仅限 localhost)</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="202" />
            <source>Hot Reload</source>
            <translation>热重载</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="221" />
            <source>Reload All</source>
            <translation>全部重载</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="326" />
            <source>Local (localhost) clients will be able to remotely control this QGIS process.
pyeval executes arbitrary Python inside QGIS.

Access is protected by a per-session token stored only in a user-private file, but only trusted processes should run under your account.

Enable it?</source>
            <translation>本地(localhost)客户端将能够远程控制此 QGIS 进程。
pyeval 会在 QGIS 内执行任意 Python。

访问受每会话令牌保护,该令牌仅存储在用户私有文件中,但您的账户下只应运行受信任的进程。

要启用吗?</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="70" />
            <source>Press "Fetch" to list models from the endpoint. Values in parentheses are prices (input/output, $/1M tokens, reference only).</source>
            <translation>按“获取”从端点列出模型。括号内的值为价格(输入/输出,美元/100 万 token,仅供参考)。</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="182" />
            <source>Current chat</source>
            <translation>当前聊天</translation>
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
            <translation>指示命令(在本地运行,不发送到 API):
  /agent               显示当前代理和列表
  /agent &lt;名称&gt;        切换代理
  /agent &lt;名称&gt; &lt;内容&gt; 保存代理并选中
  /skill               列出技能
  /skill &lt;名称&gt;        显示技能内容
  /skill &lt;名称&gt; &lt;内容&gt; 保存技能
(内容从第 2 行起可跨多行)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1873" />
            <source>Agents</source>
            <translation>代理</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1875" />
            <source>Skills</source>
            <translation>技能</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="67" />
            <source>Input {0} / Output {1} /1M tokens</source>
            <translation>输入 {0} / 输出 {1} /100 万 token</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="69" />
            <source>{0} /image (image generation)</source>
            <translation>{0} /图像(图像生成)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="70" />
            <source>Kind: {0}</source>
            <translation>类型: {0}</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="71" />
            <source>Price: {0} ({1})</source>
            <translation>价格: {0}({1})</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="72" />
            <source>Context: {0} tokens</source>
            <translation>上下文: {0} token</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="73" />
            <source>API value</source>
            <translation>API 值</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="76" />
            <source>reference</source>
            <translation>参考</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="121" />
            <source>OpenAI-compatible</source>
            <translation>兼容 OpenAI</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="126" />
            <source>API key (may be empty for local servers)</source>
            <translation>API 密钥(本地服务器可为空)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="129" />
            <source>https://api.openai.com/v1  or  http://localhost:11434/v1</source>
            <translation>https://api.openai.com/v1  或  http://localhost:11434/v1</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="137" />
            <source>Gemini API key (issued in AI Studio)</source>
            <translation>Gemini API 密钥(在 AI Studio 中签发)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="147" />
            <source>GitHub token (Copilot subscription required; can be acquired automatically via "Sign in with GitHub")</source>
            <translation>GitHub 令牌(需要 Copilot 订阅;可通过“使用 GitHub 登录”自动获取)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="151" />
            <source>https://api.githubcopilot.com  (URL of a compatible proxy such as copilot-api)</source>
            <translation>https://api.githubcopilot.com  (copilot-api 等兼容代理的 URL)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="160" />
            <source>Text (image input)</source>
            <translation>文本(图像输入)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="161" />
            <source>Text</source>
            <translation>文本</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="162" />
            <source>Image generation</source>
            <translation>图像生成</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="163" />
            <source>Embedding</source>
            <translation>嵌入</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="164" />
            <source>Audio/Other</source>
            <translation>音频/其他</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="44" />
            <source>Windows DPAPI (encrypted under the user account, same mechanism as browser password storage)</source>
            <translation>Windows DPAPI(在用户账户下加密,与浏览器密码存储机制相同)</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="45" />
            <source>macOS Keychain</source>
            <translation>macOS 钥匙串</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="50" />
            <source>~/.qgis-live/ai-secrets.json (mode 600, plain text; no keyring available)</source>
            <translation>~/.qgis-live/ai-secrets.json(权限 600,明文;无可用密钥环)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="58" />
            <source>Hot Reload: {0}</source>
            <translation>热重载: {0}</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="61" />
            <source> (dialog reopened)</source>
            <translation>(对话框已重新打开)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="64" />
            <source>Hot Reload failed: {0}</source>
            <translation>热重载失败: {0}</translation>
        </message>
    </context>
</TS>
