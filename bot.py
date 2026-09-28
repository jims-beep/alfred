# =============================================================================
# Auto-répondeur Telegram  /  Telegram auto-reply userbot  —  bot.py
# =============================================================================
# FR : Point d'entrée du bot. Ce fichier se veut COURT : il assemble les
#      modules (config, state_manager, logger_setup, responder), crée le
#      client Telethon et branche le handler d'événements. La logique métier
#      vit dans les modules.
#      Nouveautés de la refonte :
#      - mode_absent est PERSISTANT (data/state.json) : il survit aux
#        redémarrages, y compris les coupures réseau qui relancent le bot ;
#      - le client se RECONNECTE seul indéfiniment (connection_retries=-1)
#        au lieu d'abandonner après 5 tentatives ;
#      - les logs passent par logging (logs/bot.log) au lieu de print() ;
#      - la fonctionnalité .brain est RETIRÉE (plus aucune dépendance à
#        Obsidian ni au vault SecondBrain).
# EN : Bot entry point. This file stays SHORT: it assembles the modules
#      (config, state_manager, logger_setup, responder), creates the Telethon
#      client and wires the event handler. Business logic lives in modules.
#      What's new in this refactor:
#      - mode_absent is PERSISTENT (data/state.json): it survives restarts,
#        including the network outages that restart the bot;
#      - the client reconnects on its own forever (connection_retries=-1)
#        instead of giving up after 5 attempts;
#      - logging goes through the logging module (logs/bot.log), not print();
#      - the .brain feature is REMOVED (no Obsidian/SecondBrain dependency).
#
# ⚠️  SÉCURITÉ / SECURITY :
# FR : Ne JAMAIS committer : .env, *.session*, data/state.json, logs/.
# EN : NEVER commit: .env, *.session*, data/state.json, logs/.
# =============================================================================

from telethon import TelegramClient, events

import config
import responder
import state_manager
from logger_setup import setup_logger

# FR : Logger de ce module (remplace les print() de démarrage de l'original).
# EN : This module's logger (replaces the original's startup print() calls).
logger = setup_logger(__name__)

# FR : Création du client Telegram, session "autorepondeur" (fichier
#      autorepondeur.session, identique à l'original).
#      connection_retries=-1 (CONNECTION_RETRIES) = réessayer de se
#      reconnecter indéfiniment ; retry_delay=5 s (RETRY_DELAY) entre chaque
#      tentative. C'est ce qui rend le bot résilient aux coupures réseau du
#      poste ("Network is unreachable") sans crasher le process.
# EN : Telegram client creation, session "autorepondeur" (autorepondeur.session
#      file, same as the original). connection_retries=-1
#      (CONNECTION_RETRIES) = keep retrying forever; retry_delay=5 s
#      (RETRY_DELAY) between attempts. This is what makes the bot resilient
#      to the machine's network outages ("Network is unreachable") without
#      crashing the process.
client = TelegramClient(
    "autorepondeur",
    config.API_ID,
    config.API_HASH,
    connection_retries=config.CONNECTION_RETRIES,
    retry_delay=config.RETRY_DELAY,
)

# FR : ID de mon propre compte, rempli au démarrage (main()). Sert à détecter
#      les Messages enregistrés (event.chat_id == ME_ID).
# EN : My own account ID, filled at startup (main()). Used to detect Saved
#      Messages (event.chat_id == ME_ID).
ME_ID: int | None = None

# FR : IMPORTANT — on recharge l'état persistant AVANT d'enregistrer le
#      handler : mode_absent reprend donc sa dernière valeur connue sur le
#      disque au lieu de repartir à False. C'est la correction du bug
#      principal ("bot muet après chaque redémarrage").
# EN : IMPORTANT — the persistent state is reloaded BEFORE registering the
#      handler: mode_absent therefore resumes its last known value from disk
#      instead of resetting to False. This fixes the main bug ("bot silent
#      after every restart").
state_manager.load_state()


# --- Gestionnaire d'événements / Event handler --------------------------------
@client.on(events.NewMessage())
async def handler(event):
    """FR : Appelé à chaque nouveau message. Gère :
            1. Les commandes .absent / .present tapées par MOI-MÊME dans mes
               Messages enregistrés (activer/désactiver le bot) ;
            2. Les messages privés entrants : répond si le mode absent est
               actif et si le cooldown par utilisateur est respecté.
           (La commande .brain a été retirée lors de la refonte.)
       EN : Called on every new message. Handles:
            1. The .absent / .present commands typed by MYSELF in my Saved
               Messages (toggle the bot on/off);
            2. Incoming private messages: replies if away mode is active and
               the per-user cooldown has elapsed.
           (The .brain command was removed in this refactor.)"""
    # FR : Texte brut du message, en minuscules, pour la comparaison.
    # EN : Raw message text, lowercased, for comparison.
    text = (event.raw_text or "").strip().lower()

    # FR : event.out = True si le message sort de mon propre compte. On n'y
    #      traite que les commandes, et uniquement dans les Messages
    #      enregistrés (event.chat_id == ME_ID).
    # EN : event.out = True if the message is outgoing from my own account.
    #      Only commands are handled there, and only within Saved Messages
    #      (event.chat_id == ME_ID).
    if event.out:
        if event.chat_id == ME_ID and text == ".absent":
            # FR : J'ai tapé .absent -> on active le mode absent ET on le
            #      persiste immédiatement sur disque (set_mode_absent).
            # EN : I typed .absent -> enable away mode AND persist it to disk
            #      right away (set_mode_absent).
            state_manager.set_mode_absent(True)
            await event.reply("✅ Mode absent ACTIVÉ. Je réponds à tes PV.")
        elif event.chat_id == ME_ID and text == ".present":
            # FR : J'ai tapé .present -> on désactive, on persiste, et on
            #      vide le cooldown pour repartir propre (comme l'original).
            # EN : I typed .present -> disable, persist, and clear the
            #      cooldown to start fresh (like the original).
            state_manager.set_mode_absent(False)
            responder.reset_cooldowns()
            await event.reply("🛑 Mode absent DÉSACTIVÉ. Je ne réponds plus.")
        # FR : Tout autre message sortant est ignoré.
        # EN : Any other outgoing message is ignored.
        return

    # FR : Mode absent inactif -> on ignore complètement les PV.
    # EN : Away mode off -> ignore DMs entirely.
    if not state_manager.get_mode_absent():
        return

    # FR : On ne répond qu'aux conversations privées (1-to-1), pas aux groupes.
    # EN : Only reply to private (1-to-1) chats, not group chats.
    if not event.is_private:
        return

    sender_id = event.sender_id

    # FR : Vérifie ET verrouille le cooldown en une seule opération : un
    #      burst de messages ne déclenchera qu'une seule réponse.
    # EN : Checks AND locks the cooldown in one operation: a burst of
    #      messages triggers only one reply.
    if not responder.try_acquire_cooldown(sender_id):
        return

    # FR : Réponse différée avec un délai HUMAIN ALÉATOIRE (au lieu de
    #      l'ancien délai fixe de 10 s) : schedule_reply tire le délai au
    #      hasard et planifie l'envoi.
    # EN : Deferred reply with a RANDOM HUMAN delay (instead of the old fixed
    #      10s delay): schedule_reply draws the delay at random and schedules
    #      the send.
    responder.schedule_reply(client, client.loop, sender_id)


# --- Démarrage / Startup ------------------------------------------------------
async def main():
    """FR : Récupère les infos de mon compte, remplit ME_ID et affiche le
           récapitulatif de démarrage VIA LE LOGGER (plus aucun print()).
       EN : Fetches my account info, fills ME_ID and logs the startup recap
           THROUGH THE LOGGER (no print() anymore)."""
    global ME_ID
    me = await client.get_me()
    ME_ID = me.id

    # FR : Récap de démarrage, horodaté et retrouvable dans logs/bot.log
    #      (checklist de test n°3).
    # EN : Startup recap, timestamped and searchable in logs/bot.log (test
    #      checklist item #3).
    logger.info("Connecté en tant que @%s (%s)", me.username or me.id, me.first_name)
    logger.info("Commandes (Messages enregistrés / Saved Messages) : .absent | .present")
    logger.info("Mode absent restauré depuis le disque : %s", state_manager.get_mode_absent())
    logger.info(
        "Images : %d fichier(s) | Messages : %d ligne(s)",
        len(responder.list_images()), len(responder.list_messages()),
    )
    logger.info("Cooldown : %d s par utilisateur", config.COOLDOWN_SECONDS)
    logger.info(
        "Délai de réponse : %d à %d s (aléatoire)",
        config.REPLY_DELAY_MIN_SECONDS, config.REPLY_DELAY_MAX_SECONDS,
    )
    logger.info("Bot en attente...")


# FR : __main__ garantit que ce bloc ne s'exécute que si on lance directement
#      ce fichier (pas si on l'importe comme module).
# EN : __main__ ensures this block only runs when the file is launched
#      directly (not when imported as a module).
if __name__ == "__main__":
    # FR : Double filet de sécurité : config.py lève déjà une exception
    #      explicite au chargement si une variable obligatoire manque, mais on
    #      garde la vérification historique ici (exigée par la spec, §4.5).
    # EN : Double safety net: config.py already raises an explicit exception
    #      at load time if a required variable is missing, but the original
    #      check is kept here (required by the spec, §4.5).
    if not config.API_ID or not config.API_HASH:
        raise SystemExit(
            "Renseigne API_ID et API_HASH dans .env "
            "(https://my.telegram.org -> API development tools)."
        )
    if not config.PHONE:
        raise SystemExit("Renseigne PHONE dans .env (ex: +33612345678).")

    # FR : client.start() ouvre la session Telegram (crée autorepondeur.session
    #      au besoin) et demande le code de connexion la première fois.
    #      password=None si la 2FA n'est pas configurée.
    # EN : client.start() opens the Telegram session (creating
    #      autorepondeur.session if needed) and asks for the login code on
    #      first run. password=None if 2FA is not configured.
    client.start(phone=config.PHONE, password=config.PASSWORD or None)

    # FR : main() est async : on l'exécute sur la boucle de Telethon.
    # EN : main() is async: run it on Telethon's loop.
    client.loop.run_until_complete(main())

    # FR : run_until_disconnected() maintient le bot actif jusqu'à Ctrl+C.
    #      En cas de coupure réseau, Telethon se reconnecte seul grâce à
    #      connection_retries=-1.
    # EN : run_until_disconnected() keeps the bot alive until Ctrl+C. On
    #      network outages, Telethon reconnects on its own thanks to
    #      connection_retries=-1.
    client.run_until_disconnected()