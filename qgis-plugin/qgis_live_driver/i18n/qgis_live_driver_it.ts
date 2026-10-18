<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="it_IT">
    <context>
        <name>AiPanel</name>
        <message>
            <location filename="../ai_panel.py" line="206" />
            <source>API settings</source>
            <translation>Impostazioni API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="226" />
            <source>Model to use. Press "Fetch" to list models from the endpoint.
Values in parentheses are prices per 1M tokens (input/output, $).
Models in the "Text (image input)" group support sending screenshots.</source>
            <translation>Modello da utilizzare. Premere "Recupera" per elencare i modelli dall'endpoint.
I valori tra parentesi sono i prezzi per 1M di token (input/output, $).
I modelli del gruppo "Text (image input)" supportano l'invio di screenshot.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="230" />
            <source>Fetch</source>
            <translation>Recupera</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="233" />
            <source>Fetch the model list from the endpoint (GET {base}/models)</source>
            <translation>Recupera l'elenco dei modelli dall'endpoint (GET {base}/models)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="242" />
            <source>Confirm before running tools</source>
            <translation>Conferma prima dell'esecuzione degli strumenti</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="246" />
            <source>When ON, asks for approval before each tool call.
Use this if you do not want arbitrary code execution (pyeval) to run automatically.</source>
            <translation>Se attivo, chiede approvazione prima di ogni chiamata a uno strumento.
Usalo se non vuoi che l'esecuzione di codice arbitrario (pyeval) venga eseguita automaticamente.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="255" />
            <source>Instruction document (agent) injected on every request.
Lists ~/.qgis-live/agents/*.md. Use "Edit" to create or modify.</source>
            <translation>Documento di istruzioni (agente) iniettato a ogni richiesta.
Elenca ~/.qgis-live/agents/*.md. Usa "Modifica" per crearne o modificarne.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="256" />
            <location filename="../ai_panel.py" line="275" />
            <source>Edit</source>
            <translation>Modifica</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="258" />
            <source>Create, edit, or delete agent instructions (.md)</source>
            <translation>Crea, modifica o elimina istruzioni agente (.md)</translation>
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
            <translation>Documenti di istruzioni on-demand. Tutte le voci appaiono nell'elenco del prompt,
e il modello legge il contenuto tramite open() di qgis_pyeval quando necessario.
Elenca ~/.qgis-live/skills/*.md. Usa "Modifica" per crearne o modificarne.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="277" />
            <source>Create, edit, or delete skill instructions (.md)</source>
            <translation>Crea, modifica o elimina istruzioni skill (.md)</translation>
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
            <translation>Non configurato</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="287" />
            <source>Configure</source>
            <translation>Configura</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="292" />
            <source>Edit external MCP server settings (mcp_servers.json).
command=launch via stdio / url=Streamable HTTP.
Discovered tools become usable as mcp_&lt;server&gt;__&lt;tool&gt;.</source>
            <translation>Modifica le impostazioni dei server MCP esterni (mcp_servers.json).
command=avvio via stdio / url=Streamable HTTP.
Gli strumenti rilevati diventano utilizzabili come mcp_&lt;server&gt;__&lt;tool&gt;.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="301" />
            <source>Sign in with GitHub</source>
            <translation>Accedi con GitHub</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="307" />
            <source>Acquires a GitHub token via the OAuth device flow and sets it in the API key field.
Enter the displayed code in the browser (github.com/login/device).
Requires an account with a GitHub Copilot subscription.</source>
            <translation>Ottiene un token GitHub tramite il flusso dispositivo OAuth e lo imposta nel campo chiave API.
Inserisci il codice mostrato nel browser (github.com/login/device).
Richiede un account con abbonamento a GitHub Copilot.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="310" />
            <source>GitHub account with a Copilot subscription</source>
            <translation>Account GitHub con abbonamento Copilot</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="315" />
            <source>Provider</source>
            <translation>Provider</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="316" />
            <source>Endpoint</source>
            <translation>Endpoint</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="317" />
            <source>API key</source>
            <translation>Chiave API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="319" />
            <source>Key storage</source>
            <translation>Archivio chiavi</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="320" />
            <source>Model</source>
            <translation>Modello</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="332" />
            <source>Toggle visibility of the API settings</source>
            <translation>Attiva/disattiva la visibilità delle impostazioni API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="334" />
            <source>New chat</source>
            <translation>Nuova chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="337" />
            <source>Saves the current chat to history and starts a new one.
The context (conversation history) is also reset.</source>
            <translation>Salva la chat corrente nella cronologia e ne avvia una nuova.
Anche il contesto (cronologia della conversazione) viene reimpostato.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="341" />
            <source>Past chats. Select one to review it or continue the conversation.</source>
            <translation>Chat precedenti. Selezionane una per rivederla o continuare la conversazione.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="342" />
            <location filename="../ai_panel.py" line="1131" />
            <source>Current chat</source>
            <translation>Chat corrente</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="348" />
            <source>Save the displayed chat to a Markdown file</source>
            <translation>Salva la chat visualizzata in un file Markdown</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="354" />
            <source>Delete the displayed history chat (the current chat is excluded)</source>
            <translation>Elimina la chat di cronologia visualizzata (la chat corrente è esclusa)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="380" />
            <source>Enter instructions (Enter to send / Shift+Enter for a new line / Ctrl+V or drag &amp; drop to attach images).
Use /agent and /skill to edit instructions directly (/help)</source>
            <translation>Inserisci le istruzioni (Invio per inviare / Maiusc+Invio per una nuova riga / Ctrl+V o trascina e rilascia per allegare immagini).
Usa /agent e /skill per modificare direttamente le istruzioni (/help)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="390" />
            <location filename="../ai_panel.py" line="858" />
            <source>Attach and send an image file.
You can also paste (Ctrl+V) or drag &amp; drop into the input field.</source>
            <translation>Allega e invia un file immagine.
Puoi anche incollare (Ctrl+V) o trascinare e rilasciare nel campo di input.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="392" />
            <location filename="../ai_panel.py" line="939" />
            <source>Send</source>
            <translation>Invia</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="397" />
            <source>Enter also sends. While sending it changes to "Abort" and
stops the ongoing round trip (in-flight API responses/tool executions cannot be interrupted).</source>
            <translation>Invio invia allo stesso modo. Durante l'invio diventa "Annulla" e
interrompe il ciclo in corso (le risposte API/esecuzioni di strumenti in corso non possono essere interrotte).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="398" />
            <source>Retry</source>
            <translation>Riprova</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="401" />
            <source>Discard the last question and its response, then resend</source>
            <translation>Scarta l'ultima domanda e la sua risposta, quindi reinvia</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="402" />
            <source>Clear history</source>
            <translation>Cancella cronologia</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="416" />
            <source>ctx: context usage (measured prompt_tokens from the last API response;
if unavailable, an estimate marked with ~ using chars/3). The right value is the model limit.
Σ: total tokens for this chat. $: estimated cost (when pricing info is available)</source>
            <translation>ctx: utilizzo del contesto (prompt_tokens misurati dall'ultima risposta API;
se non disponibile, una stima contrassegnata con ~ usando caratteri/3). Il valore a destra è il limite del modello.
Σ: token totali di questa chat. $: costo stimato (quando sono disponibili le informazioni sui prezzi)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="499" />
            <location filename="../ai_panel.py" line="532" />
            <location filename="../ai_panel.py" line="1490" />
            <source>(none)</source>
            <translation>(nessuno)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="535" />
            <source> (bundled)</source>
            <translation> (incluso)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="608" />
            <source>Config error: {0}</source>
            <translation>Errore di configurazione: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="611" />
            <source>{0} server(s)</source>
            <translation>{0} server</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="642" />
            <source>MCP server not configured</source>
            <translation>Server MCP non configurato</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="645" />
            <source>Connecting to MCP servers…</source>
            <translation>Connessione ai server MCP…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="659" />
            <source>MCP '{0}' connection failed: {1}</source>
            <translation>Connessione MCP '{0}' non riuscita: {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="663" />
            <source>MCP connected: </source>
            <translation>MCP connesso: </translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="664" />
            <source>{0} ({1} tools)</source>
            <translation>{0} ({1} strumenti)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="748" />
            <source>Could not save the API key to the OS credential store (backend={0}). It is not saved in plain text. The entered key can be used in this session, but you will need to re-enter it next time.</source>
            <translation>Impossibile salvare la chiave API nell'archivio credenziali del SO (backend={0}). Non viene salvata in chiaro. La chiave inserita può essere usata in questa sessione, ma dovrai reinserirla la prossima volta.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="863" />
            <source>The selected model does not support image input, so attachments are unavailable.
Select a model from the "Text (image input)" group.</source>
            <translation>Il modello selezionato non supporta l'input di immagini, quindi gli allegati non sono disponibili.
Seleziona un modello del gruppo "Text (image input)".</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="875" />
            <source>ref</source>
            <translation>rif.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="879" />
            <source>context {0}</source>
            <translation>contesto {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="883" />
            <source>may not support image input (select a "Text (image input)" model to send images)</source>
            <translation>potrebbe non supportare l'input di immagini (seleziona un modello "Text (image input)" per inviare immagini)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="885" />
            <source>not usable for chat</source>
            <translation>non utilizzabile per la chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="901" />
            <source>you</source>
            <translation>tu</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="923" />
            <source>Running…</source>
            <translation>In esecuzione…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="934" />
            <source>■ Abort</source>
            <translation>■ Annulla</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="961" />
            <source>The selected model does not support image input, so attachments are unavailable (select a model from the "Text (image input)" group)</source>
            <translation>Il modello selezionato non supporta l'input di immagini, quindi gli allegati non sono disponibili (seleziona un modello del gruppo "Text (image input)")</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="972" />
            <source>Cannot read as an image: {0}</source>
            <translation>Impossibile leggere come immagine: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="973" />
            <source>(pasted image)</source>
            <translation>(immagine incollata)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="983" />
            <source>Failed to save the attached image: {0}</source>
            <translation>Salvataggio dell'immagine allegata non riuscito: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="998" />
            <source>Remove this image</source>
            <translation>Rimuovi questa immagine</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1032" />
            <source>Attach image</source>
            <translation>Allega immagine</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1034" />
            <source>Image files (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</source>
            <translation>File immagine (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</translation>
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
            <translation>Niente da salvare</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1202" />
            <source>Save chat</source>
            <translation>Salva chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1209" />
            <source>Chat saved: {0}</source>
            <translation>Chat salvata: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1212" />
            <source>Failed to save: {0}</source>
            <translation>Salvataggio non riuscito: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1243" />
            <source>Fetching model list…</source>
            <translation>Recupero dell'elenco dei modelli…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1260" />
            <source>Failed to fetch the model list: {0}</source>
            <translation>Recupero dell'elenco dei modelli non riuscito: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1264" />
            <source>Fetched {0} model(s)</source>
            <translation>Recuperati {0} modelli</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1285" />
            <source>Failed to get a device code for sign-in: {0}</source>
            <translation>Impossibile ottenere un codice dispositivo per l'accesso: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1292" />
            <source>GitHub sign-in: open {0} and enter code {1}</source>
            <translation>Accesso GitHub: apri {0} e inserisci il codice {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1295" />
            <source>Entering code {0} on GitHub…</source>
            <translation>Inserimento del codice {0} su GitHub…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1303" />
            <source>Aborted</source>
            <translation>Annullato</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1308" />
            <source>Polling failed: {0}</source>
            <translation>Sondaggio non riuscito: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1323" />
            <source>GitHub sign-in completed. The token was set in the API key field</source>
            <translation>Accesso GitHub completato. Il token è stato impostato nel campo chiave API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>GitHub sign-in: {0}</source>
            <translation>Accesso GitHub: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>Code expired</source>
            <translation>Codice scaduto</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1345" />
            <location filename="../ai_panel.py" line="1347" />
            <source>Aborting…</source>
            <translation>Annullamento in corso…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1388" />
            <source>Cannot send while running (retry after it completes)</source>
            <translation>Impossibile inviare durante l'esecuzione (riprova al termine)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1398" />
            <source>The selected model does not support image input, so images cannot be sent (select a model from the "Text (image input)" group)</source>
            <translation>Il modello selezionato non supporta l'input di immagini, quindi le immagini non possono essere inviate (seleziona un modello del gruppo "Text (image input)")</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1412" />
            <source>could not prepare the live driver</source>
            <translation>impossibile preparare il driver live</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1434" />
            <source>(image only)</source>
            <translation>(solo immagine)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1489" />
            <source>Selected: {0}</source>
            <translation>Selezionato: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1511" />
            <source>agent '{0}' not found (provide a body to save it as new)</source>
            <translation>agente '{0}' non trovato (fornisci un contenuto per salvarlo come nuovo)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1514" />
            <source>Switched agent to '{0}'</source>
            <translation>Passato all'agente '{0}'</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1524" />
            <source>skill '{0}' not found (provide a body to save it as new)</source>
            <translation>skill '{0}' non trovato (fornisci un contenuto per salvarlo come nuovo)</translation>
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
            <translation>{0} '{1}' salvato e selezionato
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1541" />
            <source>{0} '{1}' saved
{2}</source>
            <translation>{0} '{1}' salvato
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1571" />
            <source>(aborted)</source>
            <translation>(annullato)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1574" />
            <source>Waiting for API response…</source>
            <translation>In attesa della risposta API…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1613" />
            <source>(tool round-trip limit reached)</source>
            <translation>(raggiunto il limite di cicli degli strumenti)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1643" />
            <source>{0} → skipped by user</source>
            <translation>{0} → saltato dall'utente</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1660" />
            <location filename="../ai_panel.py" line="1683" />
            <location filename="../ai_panel.py" line="1715" />
            <source>{0} running…</source>
            <translation>{0} in esecuzione…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1746" />
            <source>Confirm tool execution</source>
            <translation>Conferma esecuzione strumento</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1747" />
            <source>Run {0}?

{1}</source>
            <translation>Eseguire {0}?

{1}</translation>
        </message>
    </context>
    <context>
        <name>_InstructionsDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1880" />
            <source>Edit instructions (agents/skills)</source>
            <translation>Modifica istruzioni (agenti/skill)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1893" />
            <source>Name (file name; saved as &lt;name&gt;.md. e.g. map-design)</source>
            <translation>Nome (nome file; salvato come &lt;nome&gt;.md. es. map-design)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1897" />
            <source>Edit (Markdown)</source>
            <translation>Modifica (Markdown)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1902" />
            <source>Preview</source>
            <translation>Anteprima</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1929" />
            <source>Edit instructions for the AI (Enter to send)</source>
            <translation>Modifica le istruzioni per l'IA (Invio per inviare)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1933" />
            <source>e.g. "Add a summary section" "Make the tone more concise"</source>
            <translation>es. "Aggiungi una sezione di riepilogo" "Rendi il tono più conciso"</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1935" />
            <source>Ask AI to revise</source>
            <translation>Chiedi all'IA di revisionare</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1941" />
            <source>Send the editor body and the instructions above to the chat AI.
When the AI saves, the result is reflected in the editor (not while there are unsaved manual edits)</source>
            <translation>Invia il contenuto dell'editor e le istruzioni sopra all'IA della chat.
Quando l'IA salva, il risultato viene riflesso nell'editor (non in presenza di modifiche manuali non salvate)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1946" />
            <source>Save</source>
            <translation>Salva</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1947" />
            <location filename="../ai_panel.py" line="2134" />
            <source>Delete</source>
            <translation>Elimina</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1949" />
            <source>Open folder</source>
            <translation>Apri cartella</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1950" />
            <source>Close</source>
            <translation>Chiudi</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2011" />
            <source>Agents: the selected one is injected into the system prompt on every request. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Agenti: quello selezionato viene iniettato nel prompt di sistema a ogni richiesta. Formato: "# Titolo" → descrizione → "use_when: quando usarlo" (opzionale)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2017" />
            <source>Skills: only the list of id+description+use_when appears in the prompt; the model reads the body via qgis_pyeval's open() when needed. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Skill: solo l'elenco di id+descrizione+use_when appare nel prompt; il modello legge il contenuto tramite open() di qgis_pyeval quando necessario. Formato: "# Titolo" → descrizione → "use_when: quando usarlo" (opzionale)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2027" />
            <source>+ New {0}</source>
            <translation>+ Nuovo {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2030" />
            <source> (bundled)</source>
            <translation> (incluso)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2116" />
            <source>Save failed</source>
            <translation>Salvataggio non riuscito</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2129" />
            <source>Cannot delete</source>
            <translation>Impossibile eliminare</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2131" />
            <source>Instructions bundled with the plugin cannot be deleted</source>
            <translation>Le istruzioni incluse nel plugin non possono essere eliminate</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2136" />
            <source>Delete {0} '{1}'?</source>
            <translation>Eliminare {0} '{1}'?</translation>
        </message>
    </context>
    <context>
        <name>_McpDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1765" />
            <source>External MCP server settings</source>
            <translation>Impostazioni server MCP esterni</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1780" />
            <source>Configure external MCP servers in {"mcpServers": {...}} format.
command=launch via stdio / url=Streamable HTTP. Discovered tools are usable as mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret is moved to the OS credential store on save, leaving only a $store: reference in the config file.
Saving an empty field disables MCP servers, and saving reconnects on the next send.</source>
            <translation>Configura server MCP esterni nel formato {"mcpServers": {...}}.
command=avvio via stdio / url=Streamable HTTP. Gli strumenti rilevati sono utilizzabili come mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret viene spostato nell'archivio credenziali del SO al salvataggio, lasciando solo un riferimento $store: nel file di configurazione.
Salvare un campo vuoto disabilita i server MCP; il salvataggio riconnette al prossimo invio.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1795" />
            <source>Connection examples</source>
            <translation>Esempi di connessione</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1809" />
            <source>Insert example into editor</source>
            <translation>Inserisci esempio nell'editor</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1813" />
            <source>Save</source>
            <translation>Salva</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1814" />
            <source>Close</source>
            <translation>Chiudi</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1828" />
            <location filename="../ai_panel.py" line="1847" />
            <location filename="../ai_panel.py" line="1856" />
            <source>MCP settings</source>
            <translation>Impostazioni MCP</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1830" />
            <source>Cannot read JSON: {0}</source>
            <translation>Impossibile leggere il JSON: {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1859" />
            <source>Moved client_secret to the OS credential store; only a $store: reference remains in the config file.</source>
            <translation>client_secret è stato spostato nell'archivio credenziali del SO; nel file di configurazione rimane solo un riferimento $store:.</translation>
        </message>
    </context>
    <context>
        <name>qgis_live_driver</name>
        <message>
            <location filename="../__init__.py" line="169" />
            <location filename="../ai_panel.py" line="173" />
            <source>AI Assistant</source>
            <translation>Assistente IA</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="176" />
            <source>Remote Control (localhost only)</source>
            <translation>Controllo remoto (solo localhost)</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="202" />
            <source>Hot Reload</source>
            <translation>Ricarica a caldo</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="221" />
            <source>Reload All</source>
            <translation>Ricarica tutto</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="326" />
            <source>Local (localhost) clients will be able to remotely control this QGIS process.
pyeval executes arbitrary Python inside QGIS.

Access is protected by a per-session token stored only in a user-private file, but only trusted processes should run under your account.

Enable it?</source>
            <translation>I client locali (localhost) potranno controllare da remoto questo processo QGIS.
pyeval esegue Python arbitrario dentro QGIS.

L'accesso è protetto da un token di sessione memorizzato solo in un file privato dell'utente, ma sotto il tuo account dovrebbero essere eseguiti solo processi attendibili.

Abilitare?</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="70" />
            <source>Press "Fetch" to list models from the endpoint. Values in parentheses are prices (input/output, $/1M tokens, reference only).</source>
            <translation>Premi "Recupera" per elencare i modelli dall'endpoint. I valori tra parentesi sono prezzi (input/output, $/1M di token, solo di riferimento).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="182" />
            <source>Current chat</source>
            <translation>Chat corrente</translation>
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
            <translation>Comandi di istruzioni (eseguiti localmente, non inviati all'API):
  /agent               Mostra l'agente corrente e l'elenco
  /agent &lt;nome&gt;        Cambia agente
  /agent &lt;nome&gt; &lt;contenuto&gt; Salva un agente e selezionalo
  /skill               Elenca le skill
  /skill &lt;nome&gt;        Mostra il contenuto di una skill
  /skill &lt;nome&gt; &lt;contenuto&gt; Salva una skill
(Il contenuto può estendersi su più righe a partire dalla riga 2)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1873" />
            <source>Agents</source>
            <translation>Agenti</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1875" />
            <source>Skills</source>
            <translation>Skill</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="67" />
            <source>Input {0} / Output {1} /1M tokens</source>
            <translation>Input {0} / Output {1} /1M token</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="69" />
            <source>{0} /image (image generation)</source>
            <translation>{0} /immagine (generazione di immagini)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="70" />
            <source>Kind: {0}</source>
            <translation>Tipo: {0}</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="71" />
            <source>Price: {0} ({1})</source>
            <translation>Prezzo: {0} ({1})</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="72" />
            <source>Context: {0} tokens</source>
            <translation>Contesto: {0} token</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="73" />
            <source>API value</source>
            <translation>Valore API</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="76" />
            <source>reference</source>
            <translation>riferimento</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="121" />
            <source>OpenAI-compatible</source>
            <translation>Compatibile con OpenAI</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="126" />
            <source>API key (may be empty for local servers)</source>
            <translation>Chiave API (può essere vuota per i server locali)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="129" />
            <source>https://api.openai.com/v1  or  http://localhost:11434/v1</source>
            <translation>https://api.openai.com/v1  o  http://localhost:11434/v1</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="137" />
            <source>Gemini API key (issued in AI Studio)</source>
            <translation>Chiave API Gemini (emessa in AI Studio)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="147" />
            <source>GitHub token (Copilot subscription required; can be acquired automatically via "Sign in with GitHub")</source>
            <translation>Token GitHub (richiesto abbonamento Copilot; ottenibile automaticamente tramite "Accedi con GitHub")</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="151" />
            <source>https://api.githubcopilot.com  (URL of a compatible proxy such as copilot-api)</source>
            <translation>https://api.githubcopilot.com  (URL di un proxy compatibile come copilot-api)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="160" />
            <source>Text (image input)</source>
            <translation>Testo (input immagine)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="161" />
            <source>Text</source>
            <translation>Testo</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="162" />
            <source>Image generation</source>
            <translation>Generazione di immagini</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="163" />
            <source>Embedding</source>
            <translation>Embedding</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="164" />
            <source>Audio/Other</source>
            <translation>Audio/Altro</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="44" />
            <source>Windows DPAPI (encrypted under the user account, same mechanism as browser password storage)</source>
            <translation>Windows DPAPI (crittografato sotto l'account utente, stesso meccanismo dell'archiviazione delle password del browser)</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="45" />
            <source>macOS Keychain</source>
            <translation>Portachiavi macOS</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="50" />
            <source>~/.qgis-live/ai-secrets.json (mode 600, plain text; no keyring available)</source>
            <translation>~/.qgis-live/ai-secrets.json (modalità 600, testo in chiaro; nessun keyring disponibile)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="58" />
            <source>Hot Reload: {0}</source>
            <translation>Ricarica a caldo: {0}</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="61" />
            <source> (dialog reopened)</source>
            <translation> (finestra di dialogo riaperta)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="64" />
            <source>Hot Reload failed: {0}</source>
            <translation>Ricarica a caldo non riuscita: {0}</translation>
        </message>
    </context>
</TS>
