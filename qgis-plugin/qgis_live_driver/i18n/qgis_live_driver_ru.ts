<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="ru_RU">
    <context>
        <name>AiPanel</name>
        <message>
            <location filename="../ai_panel.py" line="206" />
            <source>API settings</source>
            <translation>Настройки API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="226" />
            <source>Model to use. Press "Fetch" to list models from the endpoint.
Values in parentheses are prices per 1M tokens (input/output, $).
Models in the "Text (image input)" group support sending screenshots.</source>
            <translation>Используемая модель. Нажмите "Получить", чтобы вывести список моделей с конечной точки.
Значения в скобках — цены за 1 млн токенов (ввод/вывод, $).
Модели группы "Text (image input)" поддерживают отправку снимков экрана.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="230" />
            <source>Fetch</source>
            <translation>Получить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="233" />
            <source>Fetch the model list from the endpoint (GET {base}/models)</source>
            <translation>Получить список моделей с конечной точки (GET {base}/models)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="242" />
            <source>Confirm before running tools</source>
            <translation>Подтверждать перед запуском инструментов</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="246" />
            <source>When ON, asks for approval before each tool call.
Use this if you do not want arbitrary code execution (pyeval) to run automatically.</source>
            <translation>Если включено, запрашивает одобрение перед каждым вызовом инструмента.
Используйте, если не хотите, чтобы произвольный код (pyeval) выполнялся автоматически.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="255" />
            <source>Instruction document (agent) injected on every request.
Lists ~/.qgis-live/agents/*.md. Use "Edit" to create or modify.</source>
            <translation>Документ инструкций (агент), внедряемый в каждый запрос.
Список ~/.qgis-live/agents/*.md. Используйте "Изменить" для создания или изменения.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="256" />
            <location filename="../ai_panel.py" line="275" />
            <source>Edit</source>
            <translation>Изменить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="258" />
            <source>Create, edit, or delete agent instructions (.md)</source>
            <translation>Создать, изменить или удалить инструкции агента (.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="261" />
            <source>Agent</source>
            <translation>Агент</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="274" />
            <source>On-demand instruction documents. All entries appear in the prompt list,
and the model reads the body via qgis_pyeval's open() when needed.
Lists ~/.qgis-live/skills/*.md. Use "Edit" to create or modify.</source>
            <translation>Документы инструкций по требованию. Все записи отображаются в списке промпта,
а модель при необходимости читает содержимое через open() qgis_pyeval.
Список ~/.qgis-live/skills/*.md. Используйте "Изменить" для создания или изменения.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="277" />
            <source>Create, edit, or delete skill instructions (.md)</source>
            <translation>Создать, изменить или удалить инструкции навыка (.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="280" />
            <source>Skill</source>
            <translation>Навык</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="285" />
            <location filename="../ai_panel.py" line="612" />
            <source>Not configured</source>
            <translation>Не настроено</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="287" />
            <source>Configure</source>
            <translation>Настроить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="292" />
            <source>Edit external MCP server settings (mcp_servers.json).
command=launch via stdio / url=Streamable HTTP.
Discovered tools become usable as mcp_&lt;server&gt;__&lt;tool&gt;.</source>
            <translation>Изменить настройки внешних MCP-серверов (mcp_servers.json).
command=запуск через stdio / url=Streamable HTTP.
Обнаруженные инструменты становятся доступны как mcp_&lt;сервер&gt;__&lt;инструмент&gt;.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="301" />
            <source>Sign in with GitHub</source>
            <translation>Войти через GitHub</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="307" />
            <source>Acquires a GitHub token via the OAuth device flow and sets it in the API key field.
Enter the displayed code in the browser (github.com/login/device).
Requires an account with a GitHub Copilot subscription.</source>
            <translation>Получает токен GitHub через OAuth device flow и помещает его в поле ключа API.
Введите отображаемый код в браузере (github.com/login/device).
Требуется учётная запись с подпиской GitHub Copilot.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="310" />
            <source>GitHub account with a Copilot subscription</source>
            <translation>Учётная запись GitHub с подпиской Copilot</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="315" />
            <source>Provider</source>
            <translation>Провайдер</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="316" />
            <source>Endpoint</source>
            <translation>Конечная точка</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="317" />
            <source>API key</source>
            <translation>Ключ API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="319" />
            <source>Key storage</source>
            <translation>Хранилище ключей</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="320" />
            <source>Model</source>
            <translation>Модель</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="332" />
            <source>Toggle visibility of the API settings</source>
            <translation>Переключить видимость настроек API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="334" />
            <source>New chat</source>
            <translation>Новый чат</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="337" />
            <source>Saves the current chat to history and starts a new one.
The context (conversation history) is also reset.</source>
            <translation>Сохраняет текущий чат в историю и начинает новый.
Контекст (история переписки) также сбрасывается.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="341" />
            <source>Past chats. Select one to review it or continue the conversation.</source>
            <translation>Прошлые чаты. Выберите один для просмотра или продолжения разговора.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="342" />
            <location filename="../ai_panel.py" line="1131" />
            <source>Current chat</source>
            <translation>Текущий чат</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="348" />
            <source>Save the displayed chat to a Markdown file</source>
            <translation>Сохранить отображаемый чат в файл Markdown</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="354" />
            <source>Delete the displayed history chat (the current chat is excluded)</source>
            <translation>Удалить отображаемый чат истории (текущий чат исключён)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="380" />
            <source>Enter instructions (Enter to send / Shift+Enter for a new line / Ctrl+V or drag &amp; drop to attach images).
Use /agent and /skill to edit instructions directly (/help)</source>
            <translation>Введите инструкции (Enter — отправить / Shift+Enter — новая строка / Ctrl+V или перетаскивание для вложения изображений).
Используйте /agent и /skill для прямого редактирования инструкций (/help)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="390" />
            <location filename="../ai_panel.py" line="858" />
            <source>Attach and send an image file.
You can also paste (Ctrl+V) or drag &amp; drop into the input field.</source>
            <translation>Прикрепить и отправить файл изображения.
Можно также вставить (Ctrl+V) или перетащить в поле ввода.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="392" />
            <location filename="../ai_panel.py" line="939" />
            <source>Send</source>
            <translation>Отправить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="397" />
            <source>Enter also sends. While sending it changes to "Abort" and
stops the ongoing round trip (in-flight API responses/tool executions cannot be interrupted).</source>
            <translation>Enter также отправляет. Во время отправки меняется на "Прервать" и
останавливает текущий цикл (выполняющиеся ответы API/вызовы инструментов не прерываются).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="398" />
            <source>Retry</source>
            <translation>Повторить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="401" />
            <source>Discard the last question and its response, then resend</source>
            <translation>Отбросить последний вопрос и его ответ, затем отправить снова</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="402" />
            <source>Clear history</source>
            <translation>Очистить историю</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="416" />
            <source>ctx: context usage (measured prompt_tokens from the last API response;
if unavailable, an estimate marked with ~ using chars/3). The right value is the model limit.
Σ: total tokens for this chat. $: estimated cost (when pricing info is available)</source>
            <translation>ctx: использование контекста (измеренные prompt_tokens последнего ответа API;
если недоступно — оценка с пометкой ~ по символам/3). Правое значение — лимит модели.
Σ: всего токенов этого чата. $: оценочная стоимость (при наличии данных о ценах)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="499" />
            <location filename="../ai_panel.py" line="532" />
            <location filename="../ai_panel.py" line="1490" />
            <source>(none)</source>
            <translation>(нет)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="535" />
            <source> (bundled)</source>
            <translation> (в комплекте)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="608" />
            <source>Config error: {0}</source>
            <translation>Ошибка конфигурации: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="611" />
            <source>{0} server(s)</source>
            <translation>серверов: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="642" />
            <source>MCP server not configured</source>
            <translation>MCP-сервер не настроен</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="645" />
            <source>Connecting to MCP servers…</source>
            <translation>Подключение к MCP-серверам…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="659" />
            <source>MCP '{0}' connection failed: {1}</source>
            <translation>Сбой подключения MCP '{0}': {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="663" />
            <source>MCP connected: </source>
            <translation>MCP подключён: </translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="664" />
            <source>{0} ({1} tools)</source>
            <translation>{0} (инструментов: {1})</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="748" />
            <source>Could not save the API key to the OS credential store (backend={0}). It is not saved in plain text. The entered key can be used in this session, but you will need to re-enter it next time.</source>
            <translation>Не удалось сохранить ключ API в хранилище учётных данных ОС (backend={0}). В открытом виде он не сохраняется. Введённый ключ можно использовать в этой сессии, но в следующий раз его придётся ввести снова.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="863" />
            <source>The selected model does not support image input, so attachments are unavailable.
Select a model from the "Text (image input)" group.</source>
            <translation>Выбранная модель не поддерживает ввод изображений, поэтому вложения недоступны.
Выберите модель из группы "Text (image input)".</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="875" />
            <source>ref</source>
            <translation>справ.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="879" />
            <source>context {0}</source>
            <translation>контекст {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="883" />
            <source>may not support image input (select a "Text (image input)" model to send images)</source>
            <translation>может не поддерживать ввод изображений (выберите модель "Text (image input)" для отправки изображений)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="885" />
            <source>not usable for chat</source>
            <translation>непригодна для чата</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="901" />
            <source>you</source>
            <translation>вы</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="923" />
            <source>Running…</source>
            <translation>Выполняется…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="934" />
            <source>■ Abort</source>
            <translation>■ Прервать</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="961" />
            <source>The selected model does not support image input, so attachments are unavailable (select a model from the "Text (image input)" group)</source>
            <translation>Выбранная модель не поддерживает ввод изображений, поэтому вложения недоступны (выберите модель из группы "Text (image input)")</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="972" />
            <source>Cannot read as an image: {0}</source>
            <translation>Не удаётся прочитать как изображение: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="973" />
            <source>(pasted image)</source>
            <translation>(вставленное изображение)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="983" />
            <source>Failed to save the attached image: {0}</source>
            <translation>Не удалось сохранить вложенное изображение: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="998" />
            <source>Remove this image</source>
            <translation>Удалить это изображение</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1032" />
            <source>Attach image</source>
            <translation>Прикрепить изображение</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1034" />
            <source>Image files (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</source>
            <translation>Файлы изображений (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1088" />
            <source>Chat {0}</source>
            <translation>Чат {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1171" />
            <source>Chat</source>
            <translation>Чат</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1198" />
            <source>Nothing to save</source>
            <translation>Нечего сохранять</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1202" />
            <source>Save chat</source>
            <translation>Сохранить чат</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1209" />
            <source>Chat saved: {0}</source>
            <translation>Чат сохранён: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1212" />
            <source>Failed to save: {0}</source>
            <translation>Не удалось сохранить: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1243" />
            <source>Fetching model list…</source>
            <translation>Получение списка моделей…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1260" />
            <source>Failed to fetch the model list: {0}</source>
            <translation>Не удалось получить список моделей: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1264" />
            <source>Fetched {0} model(s)</source>
            <translation>Получено моделей: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1285" />
            <source>Failed to get a device code for sign-in: {0}</source>
            <translation>Не удалось получить код устройства для входа: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1292" />
            <source>GitHub sign-in: open {0} and enter code {1}</source>
            <translation>Вход в GitHub: откройте {0} и введите код {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1295" />
            <source>Entering code {0} on GitHub…</source>
            <translation>Ввод кода {0} на GitHub…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1303" />
            <source>Aborted</source>
            <translation>Прервано</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1308" />
            <source>Polling failed: {0}</source>
            <translation>Сбой опроса: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1323" />
            <source>GitHub sign-in completed. The token was set in the API key field</source>
            <translation>Вход в GitHub завершён. Токен установлен в поле ключа API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>GitHub sign-in: {0}</source>
            <translation>Вход в GitHub: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>Code expired</source>
            <translation>Срок действия кода истёк</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1345" />
            <location filename="../ai_panel.py" line="1347" />
            <source>Aborting…</source>
            <translation>Прерывание…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1388" />
            <source>Cannot send while running (retry after it completes)</source>
            <translation>Нельзя отправить во время выполнения (повторите после завершения)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1398" />
            <source>The selected model does not support image input, so images cannot be sent (select a model from the "Text (image input)" group)</source>
            <translation>Выбранная модель не поддерживает ввод изображений, поэтому изображения нельзя отправить (выберите модель из группы "Text (image input)")</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1412" />
            <source>could not prepare the live driver</source>
            <translation>не удалось подготовить live-драйвер</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1434" />
            <source>(image only)</source>
            <translation>(только изображение)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1489" />
            <source>Selected: {0}</source>
            <translation>Выбрано: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1511" />
            <source>agent '{0}' not found (provide a body to save it as new)</source>
            <translation>агент '{0}' не найден (укажите содержимое, чтобы сохранить как новый)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1514" />
            <source>Switched agent to '{0}'</source>
            <translation>Переключено на агента '{0}'</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1524" />
            <source>skill '{0}' not found (provide a body to save it as new)</source>
            <translation>навык '{0}' не найден (укажите содержимое, чтобы сохранить как новый)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1532" />
            <source>agent</source>
            <translation>агент</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1533" />
            <source>skill</source>
            <translation>навык</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1538" />
            <source>{0} '{1}' saved and selected
{2}</source>
            <translation>{0} '{1}' сохранён и выбран
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1541" />
            <source>{0} '{1}' saved
{2}</source>
            <translation>{0} '{1}' сохранён
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1571" />
            <source>(aborted)</source>
            <translation>(прервано)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1574" />
            <source>Waiting for API response…</source>
            <translation>Ожидание ответа API…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1613" />
            <source>(tool round-trip limit reached)</source>
            <translation>(достигнут лимит циклов инструментов)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1643" />
            <source>{0} → skipped by user</source>
            <translation>{0} → пропущено пользователем</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1660" />
            <location filename="../ai_panel.py" line="1683" />
            <location filename="../ai_panel.py" line="1715" />
            <source>{0} running…</source>
            <translation>{0} выполняется…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1746" />
            <source>Confirm tool execution</source>
            <translation>Подтвердить выполнение инструмента</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1747" />
            <source>Run {0}?

{1}</source>
            <translation>Запустить {0}?

{1}</translation>
        </message>
    </context>
    <context>
        <name>_InstructionsDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1880" />
            <source>Edit instructions (agents/skills)</source>
            <translation>Редактировать инструкции (агенты/навыки)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1893" />
            <source>Name (file name; saved as &lt;name&gt;.md. e.g. map-design)</source>
            <translation>Имя (имя файла; сохраняется как &lt;имя&gt;.md, напр. map-design)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1897" />
            <source>Edit (Markdown)</source>
            <translation>Редактировать (Markdown)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1902" />
            <source>Preview</source>
            <translation>Предпросмотр</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1929" />
            <source>Edit instructions for the AI (Enter to send)</source>
            <translation>Редактировать инструкции для ИИ (Enter — отправить)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1933" />
            <source>e.g. "Add a summary section" "Make the tone more concise"</source>
            <translation>напр. "Добавить раздел сводки" "Сделать тон более лаконичным"</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1935" />
            <source>Ask AI to revise</source>
            <translation>Попросить ИИ переработать</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1941" />
            <source>Send the editor body and the instructions above to the chat AI.
When the AI saves, the result is reflected in the editor (not while there are unsaved manual edits)</source>
            <translation>Отправить содержимое редактора и инструкции выше чат-ИИ.
Когда ИИ сохраняет, результат отражается в редакторе (не при наличии несохранённых ручных правок)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1946" />
            <source>Save</source>
            <translation>Сохранить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1947" />
            <location filename="../ai_panel.py" line="2134" />
            <source>Delete</source>
            <translation>Удалить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1949" />
            <source>Open folder</source>
            <translation>Открыть папку</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1950" />
            <source>Close</source>
            <translation>Закрыть</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2011" />
            <source>Agents: the selected one is injected into the system prompt on every request. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Агенты: выбранный внедряется в системный промпт при каждом запросе. Формат: "# Заголовок" → описание → "use_when: когда использовать" (необязательно)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2017" />
            <source>Skills: only the list of id+description+use_when appears in the prompt; the model reads the body via qgis_pyeval's open() when needed. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Навыки: в промпте отображается только список id+описание+use_when; модель читает содержимое через open() qgis_pyeval при необходимости. Формат: "# Заголовок" → описание → "use_when: когда использовать" (необязательно)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2027" />
            <source>+ New {0}</source>
            <translation>+ Новый {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2030" />
            <source> (bundled)</source>
            <translation> (в комплекте)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2116" />
            <source>Save failed</source>
            <translation>Не удалось сохранить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2129" />
            <source>Cannot delete</source>
            <translation>Невозможно удалить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2131" />
            <source>Instructions bundled with the plugin cannot be deleted</source>
            <translation>Инструкции, поставляемые с плагином, нельзя удалить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2136" />
            <source>Delete {0} '{1}'?</source>
            <translation>Удалить {0} '{1}'?</translation>
        </message>
    </context>
    <context>
        <name>_McpDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1765" />
            <source>External MCP server settings</source>
            <translation>Настройки внешних MCP-серверов</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1780" />
            <source>Configure external MCP servers in {"mcpServers": {...}} format.
command=launch via stdio / url=Streamable HTTP. Discovered tools are usable as mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret is moved to the OS credential store on save, leaving only a $store: reference in the config file.
Saving an empty field disables MCP servers, and saving reconnects on the next send.</source>
            <translation>Настройте внешние MCP-серверы в формате {"mcpServers": {...}}.
command=запуск через stdio / url=Streamable HTTP. Обнаруженные инструменты доступны как mcp_&lt;сервер&gt;__&lt;инструмент&gt;.
oauth.client_secret при сохранении перемещается в хранилище учётных данных ОС, в файле конфигурации остаётся только ссылка $store:.
Сохранение пустого поля отключает MCP-серверы; при сохранении подключение восстанавливается при следующей отправке.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1795" />
            <source>Connection examples</source>
            <translation>Примеры подключения</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1809" />
            <source>Insert example into editor</source>
            <translation>Вставить пример в редактор</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1813" />
            <source>Save</source>
            <translation>Сохранить</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1814" />
            <source>Close</source>
            <translation>Закрыть</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1828" />
            <location filename="../ai_panel.py" line="1847" />
            <location filename="../ai_panel.py" line="1856" />
            <source>MCP settings</source>
            <translation>Настройки MCP</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1830" />
            <source>Cannot read JSON: {0}</source>
            <translation>Не удаётся прочитать JSON: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1859" />
            <source>Moved client_secret to the OS credential store; only a $store: reference remains in the config file.</source>
            <translation>client_secret перемещён в хранилище учётных данных ОС; в файле конфигурации остаётся только ссылка $store:.</translation>
        </message>
    </context>
    <context>
        <name>qgis_live_driver</name>
        <message>
            <location filename="../__init__.py" line="169" />
            <location filename="../ai_panel.py" line="173" />
            <source>AI Assistant</source>
            <translation>ИИ-ассистент</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="176" />
            <source>Remote Control (localhost only)</source>
            <translation>Удалённое управление (только localhost)</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="202" />
            <source>Hot Reload</source>
            <translation>Горячая перезагрузка</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="221" />
            <source>Reload All</source>
            <translation>Перезагрузить всё</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="326" />
            <source>Local (localhost) clients will be able to remotely control this QGIS process.
pyeval executes arbitrary Python inside QGIS.

Access is protected by a per-session token stored only in a user-private file, but only trusted processes should run under your account.

Enable it?</source>
            <translation>Локальные клиенты (localhost) смогут удалённо управлять этим процессом QGIS.
pyeval выполняет произвольный Python внутри QGIS.

Доступ защищён токеном сеанса, хранящимся только в личном файле пользователя, но под вашей учётной записью должны работать только доверенные процессы.

Включить?</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="70" />
            <source>Press "Fetch" to list models from the endpoint. Values in parentheses are prices (input/output, $/1M tokens, reference only).</source>
            <translation>Нажмите "Получить", чтобы вывести список моделей с конечной точки. Значения в скобках — цены (ввод/вывод, $/1 млн токенов, только для справки).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="182" />
            <source>Current chat</source>
            <translation>Текущий чат</translation>
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
            <translation>Команды инструкций (выполняются локально, не отправляются в API):
  /agent               Показать текущего агента и список
  /agent &lt;имя&gt;        Сменить агента
  /agent &lt;имя&gt; &lt;текст&gt; Сохранить агента и выбрать его
  /skill               Список навыков
  /skill &lt;имя&gt;        Показать содержимое навыка
  /skill &lt;имя&gt; &lt;текст&gt; Сохранить навык
(Текст может занимать несколько строк, начиная со строки 2)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1873" />
            <source>Agents</source>
            <translation>Агенты</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1875" />
            <source>Skills</source>
            <translation>Навыки</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="67" />
            <source>Input {0} / Output {1} /1M tokens</source>
            <translation>Ввод {0} / Вывод {1} /1 млн токенов</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="69" />
            <source>{0} /image (image generation)</source>
            <translation>{0} /изображение (генерация изображений)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="70" />
            <source>Kind: {0}</source>
            <translation>Тип: {0}</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="71" />
            <source>Price: {0} ({1})</source>
            <translation>Цена: {0} ({1})</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="72" />
            <source>Context: {0} tokens</source>
            <translation>Контекст: {0} токенов</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="73" />
            <source>API value</source>
            <translation>Значение API</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="76" />
            <source>reference</source>
            <translation>справочно</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="121" />
            <source>OpenAI-compatible</source>
            <translation>Совместимый с OpenAI</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="126" />
            <source>API key (may be empty for local servers)</source>
            <translation>Ключ API (для локальных серверов может быть пустым)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="129" />
            <source>https://api.openai.com/v1  or  http://localhost:11434/v1</source>
            <translation>https://api.openai.com/v1  или  http://localhost:11434/v1</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="137" />
            <source>Gemini API key (issued in AI Studio)</source>
            <translation>Ключ API Gemini (выдаётся в AI Studio)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="147" />
            <source>GitHub token (Copilot subscription required; can be acquired automatically via "Sign in with GitHub")</source>
            <translation>Токен GitHub (требуется подписка Copilot; можно получить автоматически через "Войти через GitHub")</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="151" />
            <source>https://api.githubcopilot.com  (URL of a compatible proxy such as copilot-api)</source>
            <translation>https://api.githubcopilot.com  (URL совместимого прокси, например copilot-api)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="160" />
            <source>Text (image input)</source>
            <translation>Текст (ввод изображений)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="161" />
            <source>Text</source>
            <translation>Текст</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="162" />
            <source>Image generation</source>
            <translation>Генерация изображений</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="163" />
            <source>Embedding</source>
            <translation>Эмбеддинг</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="164" />
            <source>Audio/Other</source>
            <translation>Аудио/Прочее</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="44" />
            <source>Windows DPAPI (encrypted under the user account, same mechanism as browser password storage)</source>
            <translation>Windows DPAPI (шифрование под учётной записью пользователя, тот же механизм, что у хранилища паролей браузера)</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="45" />
            <source>macOS Keychain</source>
            <translation>Связка ключей macOS</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="50" />
            <source>~/.qgis-live/ai-secrets.json (mode 600, plain text; no keyring available)</source>
            <translation>~/.qgis-live/ai-secrets.json (режим 600, открытый текст; связка ключей недоступна)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="58" />
            <source>Hot Reload: {0}</source>
            <translation>Горячая перезагрузка: {0}</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="61" />
            <source> (dialog reopened)</source>
            <translation> (диалог открыт повторно)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="64" />
            <source>Hot Reload failed: {0}</source>
            <translation>Сбой горячей перезагрузки: {0}</translation>
        </message>
    </context>
</TS>
