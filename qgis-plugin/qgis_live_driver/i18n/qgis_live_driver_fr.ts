<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="fr_FR">
    <context>
        <name>AiPanel</name>
        <message>
            <location filename="../ai_panel.py" line="206" />
            <source>API settings</source>
            <translation>Paramètres API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="226" />
            <source>Model to use. Press "Fetch" to list models from the endpoint.
Values in parentheses are prices per 1M tokens (input/output, $).
Models in the "Text (image input)" group support sending screenshots.</source>
            <translation>Modèle à utiliser. Appuyez sur « Récupérer » pour lister les modèles du point de terminaison.
Les valeurs entre parenthèses sont les prix par million de tokens (entrée/sortie, $).
Les modèles du groupe « Text (image input) » prennent en charge l'envoi de captures d'écran.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="230" />
            <source>Fetch</source>
            <translation>Récupérer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="233" />
            <source>Fetch the model list from the endpoint (GET {base}/models)</source>
            <translation>Récupérer la liste des modèles depuis le point de terminaison (GET {base}/models)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="242" />
            <source>Confirm before running tools</source>
            <translation>Confirmer avant l'exécution des outils</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="246" />
            <source>When ON, asks for approval before each tool call.
Use this if you do not want arbitrary code execution (pyeval) to run automatically.</source>
            <translation>Quand activé, demande une approbation avant chaque appel d'outil.
Utilisez cette option si vous ne voulez pas que l'exécution de code arbitraire (pyeval) se lance automatiquement.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="255" />
            <source>Instruction document (agent) injected on every request.
Lists ~/.qgis-live/agents/*.md. Use "Edit" to create or modify.</source>
            <translation>Document d'instructions (agent) injecté à chaque requête.
Liste ~/.qgis-live/agents/*.md. Utilisez « Modifier » pour créer ou modifier.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="256" />
            <location filename="../ai_panel.py" line="275" />
            <source>Edit</source>
            <translation>Modifier</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="258" />
            <source>Create, edit, or delete agent instructions (.md)</source>
            <translation>Créer, modifier ou supprimer des instructions d'agent (.md)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="261" />
            <source>Agent</source>
            <translation>Agent</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="274" />
            <source>On-demand instruction documents. All entries appear in the prompt list,
and the model reads the body via qgis_pyeval's open() when needed.
Lists ~/.qgis-live/skills/*.md. Use "Edit" to create or modify.</source>
            <translation>Documents d'instructions à la demande. Toutes les entrées apparaissent dans la liste du prompt,
et le modèle lit le contenu via open() de qgis_pyeval si nécessaire.
Liste ~/.qgis-live/skills/*.md. Utilisez « Modifier » pour créer ou modifier.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="277" />
            <source>Create, edit, or delete skill instructions (.md)</source>
            <translation>Créer, modifier ou supprimer des instructions de skill (.md)</translation>
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
            <translation>Non configuré</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="287" />
            <source>Configure</source>
            <translation>Configurer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="292" />
            <source>Edit external MCP server settings (mcp_servers.json).
command=launch via stdio / url=Streamable HTTP.
Discovered tools become usable as mcp_&lt;server&gt;__&lt;tool&gt;.</source>
            <translation>Modifier les paramètres des serveurs MCP externes (mcp_servers.json).
command=lancement via stdio / url=Streamable HTTP.
Les outils découverts deviennent utilisables comme mcp_&lt;serveur&gt;__&lt;outil&gt;.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="301" />
            <source>Sign in with GitHub</source>
            <translation>Se connecter avec GitHub</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="307" />
            <source>Acquires a GitHub token via the OAuth device flow and sets it in the API key field.
Enter the displayed code in the browser (github.com/login/device).
Requires an account with a GitHub Copilot subscription.</source>
            <translation>Obtient un jeton GitHub via le flux d'appareil OAuth et le définit dans le champ de clé API.
Saisissez le code affiché dans le navigateur (github.com/login/device).
Nécessite un compte avec un abonnement GitHub Copilot.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="310" />
            <source>GitHub account with a Copilot subscription</source>
            <translation>Compte GitHub avec abonnement Copilot</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="315" />
            <source>Provider</source>
            <translation>Fournisseur</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="316" />
            <source>Endpoint</source>
            <translation>Point de terminaison</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="317" />
            <source>API key</source>
            <translation>Clé API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="319" />
            <source>Key storage</source>
            <translation>Stockage des clés</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="320" />
            <source>Model</source>
            <translation>Modèle</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="332" />
            <source>Toggle visibility of the API settings</source>
            <translation>Basculer la visibilité des paramètres API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="334" />
            <source>New chat</source>
            <translation>Nouveau chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="337" />
            <source>Saves the current chat to history and starts a new one.
The context (conversation history) is also reset.</source>
            <translation>Enregistre le chat actuel dans l'historique et en démarre un nouveau.
Le contexte (historique de conversation) est également réinitialisé.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="341" />
            <source>Past chats. Select one to review it or continue the conversation.</source>
            <translation>Chats précédents. Sélectionnez-en un pour le consulter ou poursuivre la conversation.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="342" />
            <location filename="../ai_panel.py" line="1131" />
            <source>Current chat</source>
            <translation>Chat actuel</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="348" />
            <source>Save the displayed chat to a Markdown file</source>
            <translation>Enregistrer le chat affiché dans un fichier Markdown</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="354" />
            <source>Delete the displayed history chat (the current chat is excluded)</source>
            <translation>Supprimer le chat d'historique affiché (le chat actuel est exclu)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="380" />
            <source>Enter instructions (Enter to send / Shift+Enter for a new line / Ctrl+V or drag &amp; drop to attach images).
Use /agent and /skill to edit instructions directly (/help)</source>
            <translation>Saisir des instructions (Entrée pour envoyer / Maj+Entrée pour une nouvelle ligne / Ctrl+V ou glisser-déposer pour joindre des images).
Utilisez /agent et /skill pour modifier directement les instructions (/help)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="390" />
            <location filename="../ai_panel.py" line="858" />
            <source>Attach and send an image file.
You can also paste (Ctrl+V) or drag &amp; drop into the input field.</source>
            <translation>Joindre et envoyer un fichier image.
Vous pouvez aussi coller (Ctrl+V) ou glisser-déposer dans le champ de saisie.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="392" />
            <location filename="../ai_panel.py" line="939" />
            <source>Send</source>
            <translation>Envoyer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="397" />
            <source>Enter also sends. While sending it changes to "Abort" and
stops the ongoing round trip (in-flight API responses/tool executions cannot be interrupted).</source>
            <translation>Entrée envoie aussi. Pendant l'envoi, il devient « Abandonner » et
arrête le cycle en cours (les réponses API/exécutions d'outils en vol ne peuvent pas être interrompues).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="398" />
            <source>Retry</source>
            <translation>Réessayer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="401" />
            <source>Discard the last question and its response, then resend</source>
            <translation>Abandonner la dernière question et sa réponse, puis renvoyer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="402" />
            <source>Clear history</source>
            <translation>Effacer l'historique</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="416" />
            <source>ctx: context usage (measured prompt_tokens from the last API response;
if unavailable, an estimate marked with ~ using chars/3). The right value is the model limit.
Σ: total tokens for this chat. $: estimated cost (when pricing info is available)</source>
            <translation>ctx : utilisation du contexte (prompt_tokens mesurés de la dernière réponse API ;
si indisponible, une estimation marquée ~ basée sur caractères/3). La valeur de droite est la limite du modèle.
Σ : tokens totaux de ce chat. $ : coût estimé (quand les tarifs sont disponibles)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="499" />
            <location filename="../ai_panel.py" line="532" />
            <location filename="../ai_panel.py" line="1490" />
            <source>(none)</source>
            <translation>(aucun)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="535" />
            <source> (bundled)</source>
            <translation> (inclus)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="608" />
            <source>Config error: {0}</source>
            <translation>Erreur de configuration : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="611" />
            <source>{0} server(s)</source>
            <translation>{0} serveur(s)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="642" />
            <source>MCP server not configured</source>
            <translation>Serveur MCP non configuré</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="645" />
            <source>Connecting to MCP servers…</source>
            <translation>Connexion aux serveurs MCP…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="659" />
            <source>MCP '{0}' connection failed: {1}</source>
            <translation>Échec de la connexion MCP « {0} » : {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="663" />
            <source>MCP connected: </source>
            <translation>MCP connecté : </translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="664" />
            <source>{0} ({1} tools)</source>
            <translation>{0} ({1} outils)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="748" />
            <source>Could not save the API key to the OS credential store (backend={0}). It is not saved in plain text. The entered key can be used in this session, but you will need to re-enter it next time.</source>
            <translation>Impossible d'enregistrer la clé API dans le magasin d'identifiants de l'OS (backend={0}). Elle n'est pas enregistrée en clair. La clé saisie peut être utilisée dans cette session, mais vous devrez la ressaisir la prochaine fois.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="863" />
            <source>The selected model does not support image input, so attachments are unavailable.
Select a model from the "Text (image input)" group.</source>
            <translation>Le modèle sélectionné ne prend pas en charge l'entrée d'images, les pièces jointes sont donc indisponibles.
Sélectionnez un modèle du groupe « Text (image input) ».</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="875" />
            <source>ref</source>
            <translation>réf.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="879" />
            <source>context {0}</source>
            <translation>contexte {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="883" />
            <source>may not support image input (select a "Text (image input)" model to send images)</source>
            <translation>peut ne pas prendre en charge l'entrée d'images (sélectionnez un modèle « Text (image input) » pour envoyer des images)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="885" />
            <source>not usable for chat</source>
            <translation>non utilisable pour le chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="901" />
            <source>you</source>
            <translation>vous</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="923" />
            <source>Running…</source>
            <translation>En cours…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="934" />
            <source>■ Abort</source>
            <translation>■ Abandonner</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="961" />
            <source>The selected model does not support image input, so attachments are unavailable (select a model from the "Text (image input)" group)</source>
            <translation>Le modèle sélectionné ne prend pas en charge l'entrée d'images, les pièces jointes sont donc indisponibles (sélectionnez un modèle du groupe « Text (image input) »)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="972" />
            <source>Cannot read as an image: {0}</source>
            <translation>Impossible de lire comme image : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="973" />
            <source>(pasted image)</source>
            <translation>(image collée)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="983" />
            <source>Failed to save the attached image: {0}</source>
            <translation>Échec de l'enregistrement de l'image jointe : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="998" />
            <source>Remove this image</source>
            <translation>Supprimer cette image</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1032" />
            <source>Attach image</source>
            <translation>Joindre une image</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1034" />
            <source>Image files (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</source>
            <translation>Fichiers image (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff)</translation>
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
            <translation>Rien à enregistrer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1202" />
            <source>Save chat</source>
            <translation>Enregistrer le chat</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1209" />
            <source>Chat saved: {0}</source>
            <translation>Chat enregistré : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1212" />
            <source>Failed to save: {0}</source>
            <translation>Échec de l'enregistrement : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1243" />
            <source>Fetching model list…</source>
            <translation>Récupération de la liste des modèles…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1260" />
            <source>Failed to fetch the model list: {0}</source>
            <translation>Échec de la récupération de la liste des modèles : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1264" />
            <source>Fetched {0} model(s)</source>
            <translation>{0} modèle(s) récupéré(s)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1285" />
            <source>Failed to get a device code for sign-in: {0}</source>
            <translation>Échec de l'obtention d'un code d'appareil pour la connexion : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1292" />
            <source>GitHub sign-in: open {0} and enter code {1}</source>
            <translation>Connexion GitHub : ouvrez {0} et saisissez le code {1}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1295" />
            <source>Entering code {0} on GitHub…</source>
            <translation>Saisie du code {0} sur GitHub…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1303" />
            <source>Aborted</source>
            <translation>Abandonné</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1308" />
            <source>Polling failed: {0}</source>
            <translation>Échec de l'interrogation : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1323" />
            <source>GitHub sign-in completed. The token was set in the API key field</source>
            <translation>Connexion GitHub terminée. Le jeton a été défini dans le champ de clé API</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>GitHub sign-in: {0}</source>
            <translation>Connexion GitHub : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1327" />
            <source>Code expired</source>
            <translation>Code expiré</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1345" />
            <location filename="../ai_panel.py" line="1347" />
            <source>Aborting…</source>
            <translation>Abandon en cours…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1388" />
            <source>Cannot send while running (retry after it completes)</source>
            <translation>Impossible d'envoyer pendant l'exécution (réessayez une fois terminé)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1398" />
            <source>The selected model does not support image input, so images cannot be sent (select a model from the "Text (image input)" group)</source>
            <translation>Le modèle sélectionné ne prend pas en charge l'entrée d'images, les images ne peuvent donc pas être envoyées (sélectionnez un modèle du groupe « Text (image input) »)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1412" />
            <source>could not prepare the live driver</source>
            <translation>impossible de préparer le pilote live</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1434" />
            <source>(image only)</source>
            <translation>(image uniquement)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1489" />
            <source>Selected: {0}</source>
            <translation>Sélectionné : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1511" />
            <source>agent '{0}' not found (provide a body to save it as new)</source>
            <translation>agent « {0} » introuvable (fournissez un contenu pour l'enregistrer comme nouveau)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1514" />
            <source>Switched agent to '{0}'</source>
            <translation>Agent changé pour « {0} »</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1524" />
            <source>skill '{0}' not found (provide a body to save it as new)</source>
            <translation>skill « {0} » introuvable (fournissez un contenu pour l'enregistrer comme nouveau)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1532" />
            <source>agent</source>
            <translation>agent</translation>
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
            <translation>{0} « {1} » enregistré et sélectionné
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1541" />
            <source>{0} '{1}' saved
{2}</source>
            <translation>{0} « {1} » enregistré
{2}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1571" />
            <source>(aborted)</source>
            <translation>(abandonné)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1574" />
            <source>Waiting for API response…</source>
            <translation>En attente de la réponse API…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1613" />
            <source>(tool round-trip limit reached)</source>
            <translation>(limite de cycles d'outils atteinte)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1643" />
            <source>{0} → skipped by user</source>
            <translation>{0} → ignoré par l'utilisateur</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1660" />
            <location filename="../ai_panel.py" line="1683" />
            <location filename="../ai_panel.py" line="1715" />
            <source>{0} running…</source>
            <translation>{0} en cours…</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1746" />
            <source>Confirm tool execution</source>
            <translation>Confirmer l'exécution de l'outil</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1747" />
            <source>Run {0}?

{1}</source>
            <translation>Exécuter {0} ?

{1}</translation>
        </message>
    </context>
    <context>
        <name>_InstructionsDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1880" />
            <source>Edit instructions (agents/skills)</source>
            <translation>Modifier les instructions (agents/skills)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1893" />
            <source>Name (file name; saved as &lt;name&gt;.md. e.g. map-design)</source>
            <translation>Nom (nom de fichier ; enregistré comme &lt;nom&gt;.md, ex. map-design)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1897" />
            <source>Edit (Markdown)</source>
            <translation>Modifier (Markdown)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1902" />
            <source>Preview</source>
            <translation>Aperçu</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1929" />
            <source>Edit instructions for the AI (Enter to send)</source>
            <translation>Modifier les instructions pour l'IA (Entrée pour envoyer)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1933" />
            <source>e.g. "Add a summary section" "Make the tone more concise"</source>
            <translation>ex. « Ajouter une section de résumé » « Rendre le ton plus concis »</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1935" />
            <source>Ask AI to revise</source>
            <translation>Demander à l'IA de réviser</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1941" />
            <source>Send the editor body and the instructions above to the chat AI.
When the AI saves, the result is reflected in the editor (not while there are unsaved manual edits)</source>
            <translation>Envoyer le contenu de l'éditeur et les instructions ci-dessus à l'IA du chat.
Quand l'IA enregistre, le résultat est reflété dans l'éditeur (pas en présence de modifications manuelles non enregistrées)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1946" />
            <source>Save</source>
            <translation>Enregistrer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1947" />
            <location filename="../ai_panel.py" line="2134" />
            <source>Delete</source>
            <translation>Supprimer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1949" />
            <source>Open folder</source>
            <translation>Ouvrir le dossier</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1950" />
            <source>Close</source>
            <translation>Fermer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2011" />
            <source>Agents: the selected one is injected into the system prompt on every request. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Agents : celui sélectionné est injecté dans le prompt système à chaque requête. Format : « # Titre » → description → « use_when : quand l'utiliser » (optionnel)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2017" />
            <source>Skills: only the list of id+description+use_when appears in the prompt; the model reads the body via qgis_pyeval's open() when needed. Format: "# Title" → description → "use_when: when to use" (optional)</source>
            <translation>Skills : seule la liste id+description+use_when apparaît dans le prompt ; le modèle lit le contenu via open() de qgis_pyeval si nécessaire. Format : « # Titre » → description → « use_when : quand l'utiliser » (optionnel)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2027" />
            <source>+ New {0}</source>
            <translation>+ Nouveau {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2030" />
            <source> (bundled)</source>
            <translation> (inclus)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2116" />
            <source>Save failed</source>
            <translation>Échec de l'enregistrement</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2129" />
            <source>Cannot delete</source>
            <translation>Suppression impossible</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2131" />
            <source>Instructions bundled with the plugin cannot be deleted</source>
            <translation>Les instructions fournies avec le plugin ne peuvent pas être supprimées</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="2136" />
            <source>Delete {0} '{1}'?</source>
            <translation>Supprimer {0} « {1} » ?</translation>
        </message>
    </context>
    <context>
        <name>_McpDialog</name>
        <message>
            <location filename="../ai_panel.py" line="1765" />
            <source>External MCP server settings</source>
            <translation>Paramètres des serveurs MCP externes</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1780" />
            <source>Configure external MCP servers in {"mcpServers": {...}} format.
command=launch via stdio / url=Streamable HTTP. Discovered tools are usable as mcp_&lt;server&gt;__&lt;tool&gt;.
oauth.client_secret is moved to the OS credential store on save, leaving only a $store: reference in the config file.
Saving an empty field disables MCP servers, and saving reconnects on the next send.</source>
            <translation>Configurez des serveurs MCP externes au format {"mcpServers": {...}}.
command=lancement via stdio / url=Streamable HTTP. Les outils découverts sont utilisables comme mcp_&lt;serveur&gt;__&lt;outil&gt;.
oauth.client_secret est déplacé vers le magasin d'identifiants de l'OS lors de l'enregistrement, ne laissant qu'une référence $store: dans le fichier de configuration.
Un champ vide désactive les serveurs MCP ; l'enregistrement reconnecte au prochain envoi.</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1795" />
            <source>Connection examples</source>
            <translation>Exemples de connexion</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1809" />
            <source>Insert example into editor</source>
            <translation>Insérer l'exemple dans l'éditeur</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1813" />
            <source>Save</source>
            <translation>Enregistrer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1814" />
            <source>Close</source>
            <translation>Fermer</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1828" />
            <location filename="../ai_panel.py" line="1847" />
            <location filename="../ai_panel.py" line="1856" />
            <source>MCP settings</source>
            <translation>Paramètres MCP</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1830" />
            <source>Cannot read JSON: {0}</source>
            <translation>Impossible de lire le JSON : {0}</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1859" />
            <source>Moved client_secret to the OS credential store; only a $store: reference remains in the config file.</source>
            <translation>client_secret a été déplacé vers le magasin d'identifiants de l'OS ; seule une référence $store: subsiste dans le fichier de configuration.</translation>
        </message>
    </context>
    <context>
        <name>qgis_live_driver</name>
        <message>
            <location filename="../__init__.py" line="169" />
            <location filename="../ai_panel.py" line="173" />
            <source>AI Assistant</source>
            <translation>Assistant IA</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="176" />
            <source>Remote Control (localhost only)</source>
            <translation>Contrôle à distance (localhost uniquement)</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="202" />
            <source>Hot Reload</source>
            <translation>Rechargement à chaud</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="221" />
            <source>Reload All</source>
            <translation>Tout recharger</translation>
        </message>
        <message>
            <location filename="../__init__.py" line="326" />
            <source>Local (localhost) clients will be able to remotely control this QGIS process.
pyeval executes arbitrary Python inside QGIS.

Access is protected by a per-session token stored only in a user-private file, but only trusted processes should run under your account.

Enable it?</source>
            <translation>Les clients locaux (localhost) pourront contrôler à distance ce processus QGIS.
pyeval exécute du Python arbitraire dans QGIS.

L'accès est protégé par un jeton de session stocké uniquement dans un fichier privé de l'utilisateur, mais seuls des processus de confiance devraient s'exécuter sous votre compte.

L'activer ?</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="70" />
            <source>Press "Fetch" to list models from the endpoint. Values in parentheses are prices (input/output, $/1M tokens, reference only).</source>
            <translation>Appuyez sur « Récupérer » pour lister les modèles du point de terminaison. Les valeurs entre parenthèses sont des prix (entrée/sortie, $/million de tokens, à titre indicatif).</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="182" />
            <source>Current chat</source>
            <translation>Chat actuel</translation>
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
            <translation>Commandes d'instructions (exécutées localement, non envoyées à l'API) :
  /agent               Afficher l'agent actuel et la liste
  /agent &lt;nom&gt;        Changer d'agent
  /agent &lt;nom&gt; &lt;contenu&gt; Enregistrer un agent et le sélectionner
  /skill               Lister les skills
  /skill &lt;nom&gt;        Afficher le contenu d'un skill
  /skill &lt;nom&gt; &lt;contenu&gt; Enregistrer un skill
(Le contenu peut s'étendre sur plusieurs lignes à partir de la ligne 2)</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1873" />
            <source>Agents</source>
            <translation>Agents</translation>
        </message>
        <message>
            <location filename="../ai_panel.py" line="1875" />
            <source>Skills</source>
            <translation>Skills</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="67" />
            <source>Input {0} / Output {1} /1M tokens</source>
            <translation>Entrée {0} / Sortie {1} /million de tokens</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="69" />
            <source>{0} /image (image generation)</source>
            <translation>{0} /image (génération d'images)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="70" />
            <source>Kind: {0}</source>
            <translation>Type : {0}</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="71" />
            <source>Price: {0} ({1})</source>
            <translation>Prix : {0} ({1})</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="72" />
            <source>Context: {0} tokens</source>
            <translation>Contexte : {0} tokens</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="73" />
            <source>API value</source>
            <translation>Valeur API</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="76" />
            <source>reference</source>
            <translation>référence</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="121" />
            <source>OpenAI-compatible</source>
            <translation>Compatible OpenAI</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="126" />
            <source>API key (may be empty for local servers)</source>
            <translation>Clé API (peut être vide pour les serveurs locaux)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="129" />
            <source>https://api.openai.com/v1  or  http://localhost:11434/v1</source>
            <translation>https://api.openai.com/v1  ou  http://localhost:11434/v1</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="137" />
            <source>Gemini API key (issued in AI Studio)</source>
            <translation>Clé API Gemini (délivrée dans AI Studio)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="147" />
            <source>GitHub token (Copilot subscription required; can be acquired automatically via "Sign in with GitHub")</source>
            <translation>Jeton GitHub (abonnement Copilot requis ; peut être obtenu automatiquement via « Se connecter avec GitHub »)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="151" />
            <source>https://api.githubcopilot.com  (URL of a compatible proxy such as copilot-api)</source>
            <translation>https://api.githubcopilot.com  (URL d'un proxy compatible comme copilot-api)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="160" />
            <source>Text (image input)</source>
            <translation>Texte (entrée d'image)</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="161" />
            <source>Text</source>
            <translation>Texte</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="162" />
            <source>Image generation</source>
            <translation>Génération d'images</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="163" />
            <source>Embedding</source>
            <translation>Embedding</translation>
        </message>
        <message>
            <location filename="../ai_client.py" line="164" />
            <source>Audio/Other</source>
            <translation>Audio/Autre</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="44" />
            <source>Windows DPAPI (encrypted under the user account, same mechanism as browser password storage)</source>
            <translation>Windows DPAPI (chiffré sous le compte utilisateur, même mécanisme que le stockage des mots de passe du navigateur)</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="45" />
            <source>macOS Keychain</source>
            <translation>Trousseau macOS</translation>
        </message>
        <message>
            <location filename="../credential_store.py" line="50" />
            <source>~/.qgis-live/ai-secrets.json (mode 600, plain text; no keyring available)</source>
            <translation>~/.qgis-live/ai-secrets.json (mode 600, texte clair ; aucun trousseau disponible)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="58" />
            <source>Hot Reload: {0}</source>
            <translation>Rechargement à chaud : {0}</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="61" />
            <source> (dialog reopened)</source>
            <translation> (boîte de dialogue rouverte)</translation>
        </message>
        <message>
            <location filename="../hot_reload.py" line="64" />
            <source>Hot Reload failed: {0}</source>
            <translation>Échec du rechargement à chaud : {0}</translation>
        </message>
    </context>
</TS>
