<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="es_ES">
    <context>
        <name>AiPanel</name>
        <message>
            <location filename="../ai_panel.py" line="206" />
            <source>API settings</source>
            <translation>Configuración de API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="226" />
            <source>Model to use. Press "Fetch" to list models from the endpoint.
Values in parentheses are prices per 1M tokens (input/output, $).
Models in the "Text (image input)" group support sending screenshots.</source>
            <translation>Modelo a utilizar. Pulse "Obtener" para listar los modelos del endpoint.
Los valores entre paréntesis son precios por 1M de tokens (entrada/salida, $).
Los modelos del grupo "Text (image input)" admiten el envío de capturas de pantalla.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="230" />
            <source>Fetch</source>
            <translation>Obtener</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="233" />
            <source>Fetch the model list from the endpoint (GET {base}/models)</source>
            <translation>Obtener la lista de modelos del endpoint (GET {base}/models)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="242" />
            <source>Confirm before running tools</source>
            <translation>Confirmar antes de ejecutar herramientas</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="246" />
            <source>When ON, asks for approval before each tool call.
Use this if you do not want arbitrary code execution (pyeval) to run automatically.</source>
            <translation>Si está activado, solicita aprobación antes de cada llamada a herramienta.
Úselo si no desea que la ejecución de código arbitrario (pyeval) se ejecute automáticamente.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="255" />
            <source>Instruction document (agent) injected on every request.
Lists ~/.qgis-live/agents/*.md. Use "Edit" to create or modify.</source>
            <translation>Documento de instrucciones (agente) inyectado en cada solicitud.
Lista ~/.qgis-live/agents/*.md. Use "Editar" para crear o modificar.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="256" />
            <location filename="../ai_panel.py" line="275" />
            <source>Edit</source>
            <translation>Editar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="258" />
            <source>Create, edit, or delete agent instructions (.md)</source>
            <translation>Crear, editar o eliminar instrucciones de agente (.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="261" />
            <source>Agent</source>
            <translation>Agente</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="274" />
            <source>On-demand instruction documents. All entries appear in the prompt list,
and the model reads the body via qgis_pyeval's open() when needed.
Lists ~/.qgis-live/skills/*.md. Use "Edit" to create or modify.</source>
            <translation>Documentos de instrucciones bajo demanda. Todas las entradas aparecen en la lista del prompt,
y el modelo lee el contenido mediante open() de qgis_pyeval cuando es necesario.
Lista ~/.qgis-live/skills/*.md. Use "Editar" para crear o modificar.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="277" />
            <source>Create, edit, or delete skill instructions (.md)</source>
            <translation>Crear, editar o eliminar instrucciones de skill (.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="280" />
            <source>Skill</source>
            <translation>Skill</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="285" />
            <location filename="../ai_panel.py" line="612" />
            <source>Not configured</source>
            <translation>No configurado</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="287" />
            <source>Configure</source>
            <translation>Configurar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="292" />
            <source>Edit external MCP server settings (mcp_servers.json).
command=launch via stdio / url=Streamable HTTP.
Discovered tools become usable as mcp_&lt;server&gt;__&lt;tool&gt;.</source>
            <translation>Editar la configuración de servidores MCP externos (mcp_servers.json).
command=inicio vía stdio / url=Streamable HTTP.
Las herramientas descubiertas se pueden usar como mcp_&lt;servidor&gt;__&lt;herramienta&gt;.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="301" />
            <source>Sign in with GitHub</source>
            <translation>Iniciar sesión con GitHub</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="307" />
            <source>Acquires a GitHub token via the OAuth device flow and sets it in the API key field.
Enter the displayed code in the browser (github.com/login/device).
Requires an account with a GitHub Copilot subscription.</source>
            <translation>Obtiene un token de GitHub mediante el flujo de dispositivo OAuth y lo establece en el campo de clave API.
Introduzca el código mostrado en el navegador (github.com/login/device).
Requiere una cuenta con suscripción a GitHub Copilot.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="310" />
            <source>GitHub account with a Copilot subscription</source>
            <translation>Cuenta de GitHub con suscripción a Copilot</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="315" />
            <source>Provider</source>
            <translation>Proveedor</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="316" />
            <source>Endpoint</source>
            <translation>Endpoint</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="317" />
            <source>API key</source>
            <translation>Clave API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="319" />
            <source>Key storage</source>
            <translation>Almacenamiento de claves</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="320" />
            <source>Model</source>
            <translation>Modelo</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="332" />
            <source>Toggle visibility of the API settings</source>
            <translation>Alternar la visibilidad de la configuración de API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="334" />
            <source>New chat</source>
            <translation>Nuevo chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="337" />
            <source>Saves the current chat to history and starts a new one.
The context (conversation history) is also reset.</source>
            <translation>Guarda el chat actual en el historial e inicia uno nuevo.
El contexto (historial de conversación) también se restablece.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="341" />
            <source>Past chats. Select one to review it or continue the conversation.</source>
            <translation>Chats anteriores. Seleccione uno para revisarlo o continuar la conversación.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="342" />
            <location filename="../ai_panel.py" line="1131" />
            <source>Current chat</source>
            <translation>Chat actual</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="348" />
            <source>Save the displayed chat to a Markdown file</source>
            <translation>Guardar el chat mostrado en un archivo Markdown</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="354" />
            <source>Delete the displayed history chat (the current chat is excluded)</source>
            <translation>Eliminar el chat del historial mostrado (el chat actual está excluido)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="380" />
            <source>Enter instructions (Enter to send / Shift+Enter for a new line / Ctrl+V or drag &amp; drop to attach images).
Use /agent and /skill to edit instructions directly (/help)</source>
            <translation>Introduzca instrucciones (Enter para enviar / Shift+Enter para nueva línea / Ctrl+V o arrastrar y soltar para adjuntar imágenes).
Use /agent y /skill para editar instrucciones directamente (/help)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="390" />
            <location filename="../ai_panel.py" line="858" />
            <source>Attach and send an image file.
You can also paste (Ctrl+V) or drag &amp; drop into the input field.</source>
            <translation>Adjuntar y enviar un archivo de imagen.
También puede pegar (Ctrl+V) o arrastrar y soltar en el campo de entrada.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="392" />
            <location filename="../ai_panel.py" line="939" />
            <source>Send</source>
            <translation>Enviar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="397" />
            <source>Enter also sends. While sending it changes to "Abort" and
stops the ongoing round trip (in-flight API responses/tool executions cannot be interrupted).</source>
            <translation>Enter también envía. Mientras envía cambia a "Abortar" y
detiene el ciclo en curso (las respuestas de API/ejecuciones de herramientas en curso no se pueden interrumpir).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="398" />
            <source>Retry</source>
            <translation>Reintentar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="401" />
            <source>Discard the last question and its response, then resend</source>
            <translation>Descartar la última pregunta y su respuesta, y reenviar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="402" />
            <source>Clear history</source>
            <translation>Borrar historial</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="416" />
            <source>ctx: context usage (measured prompt_tokens from the last API response;
if unavailable, an estimate marked with ~ using chars/3). The right value is the model limit.
Σ: total tokens for this chat. $: estimated cost (when pricing info is available)</source>
            <translation>ctx: uso de contexto (prompt_tokens medidos de la última respuesta de la API;
si no está disponible, una estimación marcada con ~ usando caracteres/3). El valor derecho es el límite del modelo.
Σ: tokens totales de este chat. $: coste estimado (cuando hay información de precios)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="499" />
            <location filename="../ai_panel.py" line="532" />
            <location filename="../ai_panel.py" line="1490" />
            <source>(none)</source>
            <translation>(ninguno)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="535" />
            <source> (bundled)</source>
            <translation> (incluido)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="608" />
            <source>Config error: {0}</source>
            <translation>Error de configuración: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="611" />
            <source>{0} server(s)</source>
            <translation>{0} servidor(es)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="642" />
            <source>MCP server not configured</source>
            <translation>Servidor MCP no configurado</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="645" />
            <source>Connecting to MCP servers…</source>
            <translation>Conectando con servidores MCP…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="659" />
            <source>MCP '{0}' connection failed: {1}</source>
            <translation>Falló la conexión MCP '{0}': {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="663" />
            <source>MCP connected: </source>
            <translation>MCP conectado: </translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="664" />
            <source>{0} ({1} tools)</source>
            <translation>{0} ({1} herramientas)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="748" />
            <source>Could not save the API key to the OS credential store (backend={0}). It is not saved in plain text. The entered key can be used in this session, but you will need to re-enter it next time.</source>
            <translation>No se pudo guardar la clave API en el almacén de credenciales del SO (backend={0}). No se guarda en texto plano. La clave introducida se puede usar en esta sesión, pero deberá volver a introducirla la próxima vez.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="863" />
            <source>The selected model does not support image input, so attachments are unavailable.
Select a model from the "Text (image input)" group.</source>
            <translation>El modelo seleccionado no admite entrada de imágenes, por lo que los adjuntos no están disponibles.
Seleccione un modelo del grupo "Text (image input)".</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="875" />
            <source>ref</source>
            <translation>ref.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="879" />
            <source>context {0}</source>
            <translation>contexto {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="883" />
            <source>may not support image input (select a "Text (image input)" model to send images)</source>
            <translation>puede no admitir entrada de imágenes (seleccione un modelo "Text (image input)" para enviar imágenes)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="885" />
            <source>not usable for chat</source>
            <translation>no utilizable para chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="901" />
            <source>you</source>
            <translation>usted</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="923" />
            <source>Running…</source>
            <translation>Ejecutando…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="934" />
            <source>■ Abort</source>
            <translation>■ Abortar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="961" />
            <source>The selected model does not support image input, so attachments are unavailable (select a model from the "Text (image input)" group)</source>
            <translation>El modelo seleccionado no admite entrada de imágenes, por lo que los adjuntos no están disponibles (seleccione un modelo del grupo "Text (image input)")</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="972" />
            <source>Cannot read as an image: {0}</source>
            <translation>No se puede leer como imagen: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="973" />
            <source>(pasted image)</source>
            <translation>(imagen pegada)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="983" />
            <source>Failed to save the attached image: {0}</source>
            <translation>Falló al guardar la imagen adjunta: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="998" />
            <source>Remove this image</source>
            <translation>Quitar esta imagen</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1032" />
            <source>Attach image</source>
            <translation>Adjuntar imagen</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1034" />
            <source>Image files (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</source>
            <translation>Archivos de imagen (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1088" />
            <source>Chat {0}</source>
            <translation>Chat {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1171" />
            <source>Chat</source>
            <translation>Chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1198" />
            <source>Nothing to save</source>
            <translation>Nada que guardar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1202" />
            <source>Save chat</source>
            <translation>Guardar chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1209" />
            <source>Chat saved: {0}</source>
            <translation>Chat guardado: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1212" />
            <source>Failed to save: {0}</source>
            <translation>Falló al guardar: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1243" />
            <source>Fetching model list…</source>
            <translation>Obteniendo lista de modelos…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1260" />
            <source>Failed to fetch the model list: {0}</source>
            <translation>Falló al obtener la lista de modelos: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1264" />
            <source>Fetched {0} model(s)</source>
            <translation>Se obtuvieron {0} modelo(s)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1285" />
            <source>Failed to get a device code for sign-in: {0}</source>
            <translation>Falló al obtener un código de dispositivo para iniciar sesión: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1292" />
            <source>GitHub sign-in: open {0} and enter code {1}</source>
            <translation>Inicio de sesión en GitHub: abra {0} e introduzca el código {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1295" />
            <source>Entering code {0} on GitHub…</source>
            <translation>Introduciendo el código {0} en GitHub…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1303" />
            <source>Aborted</source>
            <translation>Abortado</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1308" />
            <source>Polling failed: {0}</source>
            <translation>Falló el sondeo: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1323" />
            <source>GitHub sign-in completed. The token was set in the API key field</source>
            <translation>Inicio de sesión en GitHub completado. El token se estableció en el campo de clave API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>GitHub sign-in: {0}</source>
            <translation>Inicio de sesión en GitHub: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>Code expired</source>
            <translation>Código caducado</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1345" />
            <location filename="../ai_panel.py" line="1347" />
            <source>Aborting…</source>
            <translation>Abortando…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1388" />
            <source>Cannot send while running (retry after it completes)</source>
            <translation>No se puede enviar mientras está en ejecución (reintente cuando termine)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1398" />
            <source>The selected model does not support image input, so images cannot be sent (select a model from the "Text (image input)" group)</source>
            <translation>El modelo seleccionado no admite entrada de imágenes, por lo que no se pueden enviar imágenes (seleccione un modelo del grupo "Text (image input)")</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1412" />
            <source>could not prepare the live driver</source>
            <translation>no se pudo preparar el controlador live</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1434" />
            <source>(image only)</source>
            <translation>(solo imagen)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1489" />
            <source>Selected: {0}</source>
            <translation>Seleccionado: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1511" />
            <source>agent '{0}' not found (provide a body to save it as new)</source>
            <translation>agente '{0}' no encontrado (proporcione un cuerpo para guardarlo como nuevo)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1514" />
            <source>Switched agent to '{0}'</source>
            <translation>Cambiado al agente '{0}'</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1524" />
            <source>skill '{0}' not found (provide a body to save it as new)</source>
            <translation>skill '{0}' no encontrado (proporcione un cuerpo para guardarlo como nuevo)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1532" />
            <source>agent</source>
            <translation>agente</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1533" />
            <source>skill</source>
            <translation>skill</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1538" />
            <source>{0} '{1}' saved and selected
{2}</source>
            <translation>{0} '{1}' guardado y seleccionado
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1541" />
            <source>{0} '{1}' saved
{2}</source>
            <translation>{0} '{1}' guardado
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1571" />
            <source>(aborted)</source>
            <translation>(abortado)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1574" />
            <source>Waiting for API response…</source>
            <translation>Esperando respuesta de la API…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1613" />
            <source>(tool round-trip limit reached)</source>
            <translation>(se alcanzó el límite de ciclos de herramientas)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1643" />
            <source>{0} → skipped by user</source>
            <translation>{0} → omitido por el usuario</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1660" />
            <location filename="../ai_panel.py" line="1683" />
            <location filename="../ai_panel.py" line="1715" />
            <source>{0} running…</source>
            <translation>{0} ejecutando…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1746" />
            <source>Confirm tool execution</source>
            <translation>Confirmar ejecución de herramienta</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1747" />
            <source>Run {0}?

{1}</source>
            <translation>¿Ejecutar {0}?

{1}</translation>
        </message>
    </context>
    <context>
        <name>_InstructionsDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1880" />
            <source>Edit instructions (agents/skills)</source>
            <translation>Editar instrucciones (agentes/skills)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1893" />
            <source>Name (file name; saved as &lt;name&gt;.md. e.g. map-design)</source>
            <translation>Nombre (nombre de archivo; se guarda como &lt;nombre&gt;.md, p. ej. map-design)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1897" />
            <source>Edit (Markdown)</source>
            <translation>Editar (Markdown)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1902" />
            <source>Preview</source>
            <translation>Vista previa</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1929" />
            <source>Edit instructions for the AI (Enter to send)</source>
            <translation>Editar instrucciones para la IA (Enter para enviar)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1933" />
            <source>e.g. "Add a summary section" "Make the tone more concise"</source>
            <translation>p. ej. "Añadir una sección de resumen" "Hacer el tono más conciso"</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1935" />
            <source>Ask AI to revise</source>
            <translation>Pedir a la IA que lo revise</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1941" />
            <source>Send the editor body and the instructions above to the chat AI.
When the AI saves, the result is reflected in the editor (not while there are unsaved manual edits)</source>
            <translation>Enviar el cuerpo del editor y las instrucciones anteriores a la IA del chat.
Cuando la IA guarda, el resultado se refleja en el editor (no mientras haya ediciones manuales sin guardar)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1946" />
            <source>Save</source>
            <translation>Guardar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1947" />
            <location filename="../ai_panel.py" line="2134" />
            <source>Delete</source>
            <translation>Eliminar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1949" />
            <source>Open folder</source>
            <translation>Abrir carpeta</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1950" />
            <source>Close</source>
            <translation>Cerrar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2011" />
            <source>Agents: the selected one is injected into the system prompt on every request. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Agentes: el seleccionado se inyecta en el prompt del sistema en cada solicitud. Formato: "# Título" → descripción → "use_when: cuándo usarlo" (opcional)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2017" />
            <source>Skills: only the list of id+description+use_when appears in the prompt; the model reads the body via qgis_pyeval's open() when needed. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Skills: solo la lista de id+descripción+use_when aparece en el prompt; el modelo lee el cuerpo mediante open() de qgis_pyeval cuando es necesario. Formato: "# Título" → descripción → "use_when: cuándo usarlo" (opcional)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2027" />
            <source>+ New {0}</source>
            <translation>+ Nuevo {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2030" />
            <source> (bundled)</source>
            <translation> (incluido)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2116" />
            <source>Save failed</source>
            <translation>Falló al guardar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2129" />
            <source>Cannot delete</source>
            <translation>No se puede eliminar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2131" />
            <source>Instructions bundled with the plugin cannot be deleted</source>
            <translation>Las instrucciones incluidas con el plugin no se pueden eliminar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2136" />
            <source>Delete {0} '{1}'?</source>
            <translation>¿Eliminar {0} '{1}'?</translation>
        </message>
    </context>
    <context>
        <name>_McpDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1765" />
            <source>External MCP server settings</source>
            <translation>Configuración de servidores MCP externos</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1780" />
            <source>Configure external MCP servers in {"mcpServers": {...}} format.
command=launch via stdio / url=Streamable HTTP. Discovered tools are usable as mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret is moved to the OS credential store on save, leaving only a $store: reference in the config file.
Saving an empty field disables MCP servers, and saving reconnects on the next send.</source>
            <translation>Configure servidores MCP externos en formato {"mcpServers": {...}}.
command=inicio vía stdio / url=Streamable HTTP. Las herramientas descubiertas se pueden usar como mcp_&lt;servidor&gt;__&lt;herramienta&gt;.
oauth.client_secret se mueve al almacén de credenciales del SO al guardar, quedando solo una referencia $store: en el archivo de configuración.
Guardar un campo vacío deshabilita los servidores MCP, y al guardar se reconecta en el próximo envío.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1795" />
            <source>Connection examples</source>
            <translation>Ejemplos de conexión</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1809" />
            <source>Insert example into editor</source>
            <translation>Insertar ejemplo en el editor</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1813" />
            <source>Save</source>
            <translation>Guardar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1814" />
            <source>Close</source>
            <translation>Cerrar</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1828" />
            <location filename="../ai_panel.py" line="1847" />
            <location filename="../ai_panel.py" line="1856" />
            <source>MCP settings</source>
            <translation>Configuración MCP</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1830" />
            <source>Cannot read JSON: {0}</source>
            <translation>No se puede leer el JSON: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1859" />
            <source>Moved client_secret to the OS credential store; only a $store: reference remains in the config file.</source>
            <translation>client_secret se movió al almacén de credenciales del SO; solo queda una referencia $store: en el archivo de configuración.</translation>
        </message>
    </context>
    <context>
        <name>qgis_live_driver</name>
        <message>
            <location filename="../__init__.py" line="169" />
            <location filename="../ai_panel.py" line="173" />
            <source>AI Assistant</source>
            <translation>Asistente de IA</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="176" />
            <source>Remote Control (localhost only)</source>
            <translation>Control remoto (solo localhost)</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="202" />
            <source>Hot Reload</source>
            <translation>Recarga en caliente</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="221" />
            <source>Reload All</source>
            <translation>Recargar todo</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="326" />
            <source>Local (localhost) clients will be able to remotely control this QGIS process.
pyeval executes arbitrary Python inside QGIS.

Access is protected by a per-session token stored only in a user-private file, but only trusted processes should run under your account.

Enable it?</source>
            <translation>Los clientes locales (localhost) podrán controlar remotamente este proceso de QGIS.
pyeval ejecuta Python arbitrario dentro de QGIS.

El acceso está protegido por un token por sesión almacenado solo en un archivo privado del usuario, pero solo procesos de confianza deberían ejecutarse bajo su cuenta.

¿Habilitarlo?</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="70" />
            <source>Press "Fetch" to list models from the endpoint. Values in parentheses are prices (input/output, $/1M tokens, reference only).</source>
            <translation>Pulse "Obtener" para listar los modelos del endpoint. Los valores entre paréntesis son precios (entrada/salida, $/1M de tokens, solo de referencia).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="182" />
            <source>Current chat</source>
            <translation>Chat actual</translation>
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
            <translation>Comandos de instrucciones (se ejecutan localmente, no se envían a la API):
  /agent               Mostrar el agente actual y la lista
  /agent &lt;nombre&gt;        Cambiar de agente
  /agent &lt;nombre&gt; &lt;cuerpo&gt; Guardar un agente y seleccionarlo
  /skill               Listar skills
  /skill &lt;nombre&gt;        Mostrar el cuerpo de un skill
  /skill &lt;nombre&gt; &lt;cuerpo&gt; Guardar un skill
(El cuerpo puede abarcar varias líneas a partir de la línea 2)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1873" />
            <source>Agents</source>
            <translation>Agentes</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1875" />
            <source>Skills</source>
            <translation>Skills</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="67" />
            <source>Input {0} / Output {1} /1M tokens</source>
            <translation>Entrada {0} / Salida {1} /1M tokens</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="69" />
            <source>{0} /image (image generation)</source>
            <translation>{0} /imagen (generación de imágenes)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="70" />
            <source>Kind: {0}</source>
            <translation>Tipo: {0}</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="71" />
            <source>Price: {0} ({1})</source>
            <translation>Precio: {0} ({1})</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="72" />
            <source>Context: {0} tokens</source>
            <translation>Contexto: {0} tokens</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="73" />
            <source>API value</source>
            <translation>Valor de API</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="76" />
            <source>reference</source>
            <translation>referencia</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="121" />
            <source>OpenAI-compatible</source>
            <translation>Compatible con OpenAI</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="126" />
            <source>API key (may be empty for local servers)</source>
            <translation>Clave API (puede estar vacía para servidores locales)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="129" />
            <source>https://api.openai.com/v1  or  http://localhost:11434/v1</source>
            <translation>https://api.openai.com/v1  o  http://localhost:11434/v1</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="137" />
            <source>Gemini API key (issued in AI Studio)</source>
            <translation>Clave API de Gemini (emitida en AI Studio)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="147" />
            <source>GitHub token (Copilot subscription required; can be acquired automatically via "Sign in with GitHub")</source>
            <translation>Token de GitHub (se requiere suscripción a Copilot; se puede adquirir automáticamente mediante "Iniciar sesión con GitHub")</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="151" />
            <source>https://api.githubcopilot.com  (URL of a compatible proxy such as copilot-api)</source>
            <translation>https://api.githubcopilot.com  (URL de un proxy compatible como copilot-api)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="160" />
            <source>Text (image input)</source>
            <translation>Texto (entrada de imagen)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="161" />
            <source>Text</source>
            <translation>Texto</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="162" />
            <source>Image generation</source>
            <translation>Generación de imágenes</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="163" />
            <source>Embedding</source>
            <translation>Embedding</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="164" />
            <source>Audio/Other</source>
            <translation>Audio/Otros</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="44" />
            <source>Windows DPAPI (encrypted under the user account, same mechanism as browser password storage)</source>
            <translation>Windows DPAPI (cifrado bajo la cuenta de usuario, mismo mecanismo que el almacenamiento de contraseñas del navegador)</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="45" />
            <source>macOS Keychain</source>
            <translation>macOS Keychain</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="50" />
            <source>~/.qgis-live/ai-secrets.json (mode 600, plain text; no keyring available)</source>
            <translation>~/.qgis-live/ai-secrets.json (modo 600, texto plano; no hay keyring disponible)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="58" />
            <source>Hot Reload: {0}</source>
            <translation>Recarga en caliente: {0}</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="61" />
            <source> (dialog reopened)</source>
            <translation> (diálogo reabierto)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="64" />
            <source>Hot Reload failed: {0}</source>
            <translation>Falló la recarga en caliente: {0}</translation>
        </message>
    </context>
</TS>
