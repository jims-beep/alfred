# =============================================================================
# responder.py — Logique de réponse automatique / Auto-reply logic
# =============================================================================
# FR : Reprend send_auto_reply(), list_images() et list_messages() de
#      l'ancien bot.py, avec deux évolutions :
#      1) le délai avant réponse est ALÉATOIRE (random.uniform entre
#         REPLY_DELAY_MIN_SECONDS et REPLY_DELAY_MAX_SECONDS) au lieu d'être
#         fixe (10 s), pour ne pas créer de pattern détectable ;
#      2) toutes les erreurs sont LOGGÉES (plus aucun print()).
#      Le cooldown par utilisateur (last_reply) reste VOLONTAIREMENT en
#      mémoire uniquement : le perdre à un redémarrage n'est pas grave.
# EN : Carries over send_auto_reply(), list_images() and list_messages() from
#      the old bot.py, with two changes:
#      1) the reply delay is now RANDOM (random.uniform between
#         REPLY_DELAY_MIN_SECONDS and REPLY_DELAY_MAX_SECONDS) instead of a
#         fixed 10s, so no detectable pattern is created;
#      2) every error is LOGGED (no print() anymore).
#      The per-user cooldown (last_reply) stays IN MEMORY ONLY on purpose:
#      losing it on restart is harmless.
# =============================================================================

import asyncio
import random
import time
from pathlib import Path

from config import (
    COOLDOWN_SECONDS,
    IMAGES_DIR,
    MESSAGES_FILE,
    REPLY_DELAY_MAX_SECONDS,
    REPLY_DELAY_MIN_SECONDS,
)
from logger_setup import setup_logger

# FR : Logger de ce module.
# EN : This module's logger.
logger = setup_logger(__name__)

# FR : Extensions d'image/vidéo reconnues (insensibles à la casse), comme dans
#      la version originale.
# EN : Recognized image/video extensions (case-insensitive), as in the
#      original version.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp4", ".mov"}

# FR : Message de secours si messages.txt est vide ou absent — même texte que
#      l'original.
# EN : Fallback message if messages.txt is empty or missing — same text as
#      the original.
FALLBACK_MESSAGE = "Pas dispo là tout de suite, je te réponds dès que je peux 🙏"

# FR : Date de dernière réponse par utilisateur (clé = ID Telegram). En
#      mémoire uniquement, volontairement non persisté.
# EN : Last reply timestamp per user (key = Telegram ID). In memory only,
#      deliberately not persisted.
last_reply: dict[int, float] = {}


def list_images() -> list[Path]:
    """FR : Retourne la liste des fichiers image valides dans IMAGES_DIR
           (logique identique à l'original).
       EN : Returns the list of valid image files in IMAGES_DIR (same logic
           as the original)."""
    if not IMAGES_DIR.exists():
        return []
    return [
        p
        for p in IMAGES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]


def list_messages() -> list[str]:
    """FR : Lit messages.txt et renvoie chaque ligne non vide.
           NOTE : contrairement à l'original, qui envoyait aussi les lignes
           de commentaire, on ignore ici les lignes commençant par '#', comme
           le documente l'en-tête de messages.txt (petite correction assumée,
           voir note dans le README).
       EN : Reads messages.txt and returns each non-empty line. NOTE: unlike
           the original, which also sent comment lines, lines starting with
           '#' are ignored here, as documented in messages.txt's header
           (intentional small fix, see README note)."""
    if not MESSAGES_FILE.exists():
        return []
    return [
        line.strip()
        for line in MESSAGES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def try_acquire_cooldown(sender_id: int) -> bool:
    """FR : Vérifie le cooldown pour `sender_id` et le verrouille dans la
           même opération : renvoie True si on a le droit de répondre (et
           démarre immédiatement la fenêtre de cooldown), False si on a déjà
           répondu à cette personne il y a moins de COOLDOWN_SECONDS.
           Verrouiller TOUT DE SUITE garantit qu'un burst de messages ne
           déclenche qu'UNE seule réponse, même si un message arrive pendant
           le délai humain (comportement identique à l'original).
       EN : Checks the cooldown for `sender_id` and locks it in the same
           operation: returns True if replying is allowed (and immediately
           starts the cooldown window), False if we already replied to this
           person less than COOLDOWN_SECONDS ago. Locking RIGHT AWAY
           guarantees a burst of messages triggers only ONE reply, even if a
           message lands during the human delay (same behavior as the
           original)."""
    now = time.time()
    last = last_reply.get(sender_id)
    if last is not None and now - last < COOLDOWN_SECONDS:
        # FR : Encore dans la fenêtre de cooldown : on ne répond pas.
        # EN : Still inside the cooldown window: do not reply.
        return False
    # FR : On "pose" le cooldown immédiatement (avant le délai aléatoire).
    # EN : Set the cooldown immediately (before the random delay).
    last_reply[sender_id] = now
    return True


def reset_cooldowns() -> None:
    """FR : Vide l'historique de cooldown (appelé par la commande .present,
           comme l'original qui faisait last_reply.clear()).
       EN : Clears the cooldown history (called by the .present command, like
           the original's last_reply.clear())."""
    last_reply.clear()
    logger.info("Cooldowns remis à zéro / Cooldowns cleared.")


async def send_auto_reply(client, sender_id: int) -> None:
    """FR : Envoie la réponse automatique à `sender_id` : une image
           aléatoire de IMAGES_DIR avec un message aléatoire en légende, ou
           un texte seul si aucune image n'est disponible. Les erreurs
           (fichier illisible, réseau…) sont LOGGÉES sans faire planter le
           bot.
       EN : Sends the auto-reply to `sender_id`: a random image from
           IMAGES_DIR with a random message as caption, or text only if no
           image is available. Errors (unreadable file, network…) are LOGGED
           without crashing the bot."""
    images = list_images()
    messages = list_messages()

    # FR : Message aléatoire ; fallback humain si la liste est vide.
    # EN : Random message; human fallback if the list is empty.
    caption = random.choice(messages) if messages else FALLBACK_MESSAGE

    try:
        if images:
            # FR : Image aléatoire avec le message en légende.
            # EN : Random image with the message as caption.
            img = random.choice(images)
            await client.send_file(sender_id, str(img), caption=caption)
            logger.info("Réponse envoyée à %s (image : %s)", sender_id, img.name)
        else:
            # FR : Pas d'image disponible : envoi du texte seul.
            # EN : No image available: send text only.
            await client.send_message(sender_id, caption)
            logger.info("Réponse envoyée à %s (texte seul, aucune image trouvée)", sender_id)
    except Exception as e:
        # FR : On log l'erreur au lieu d'un print() : le bot continue de tourner.
        # EN : Log the error instead of a print(): the bot keeps running.
        logger.error("Erreur lors de l'envoi de la réponse à %s : %s", sender_id, e)


def schedule_reply(client, loop, sender_id: int) -> None:
    """FR : Calcule un délai humain ALÉATOIRE entre REPLY_DELAY_MIN_SECONDS
           et REPLY_DELAY_MAX_SECONDS, puis planifie send_auto_reply via
           loop.call_later (asyncio.ensure_future pour lancer la coroutine).
           Remplace l'ancien délai fixe de 10 s.
       EN : Computes a RANDOM human delay between REPLY_DELAY_MIN_SECONDS
           and REPLY_DELAY_MAX_SECONDS, then schedules send_auto_reply via
           loop.call_later (asyncio.ensure_future to run the coroutine).
           Replaces the old fixed 10 s delay."""
    delay = random.uniform(REPLY_DELAY_MIN_SECONDS, REPLY_DELAY_MAX_SECONDS)
    # FR : Log du délai : utile pour vérifier dans bot.log que la réponse est
    #      bien partie (checklist de test n°3).
    # EN : Log the delay: useful to check in bot.log that the reply was
    #      actually sent (test checklist item #3).
    logger.info(
        "Réponse programmée pour %s dans %.1f s (délai humain aléatoire)",
        sender_id, delay,
    )
    loop.call_later(
        delay,
        lambda: asyncio.ensure_future(send_auto_reply(client, sender_id)),
    )