# =============================================================================
# config.py — Configuration centrale du bot / Central bot configuration
# =============================================================================
# FR : Ce module centralise le chargement du fichier .env et la validation des
#      variables d'environnement. Toute variable obligatoire manquante (ou
#      invalide) lève une exception explicite AU CHARGEMENT, avec un message
#      clair — jamais un simple KeyError plus tard au milieu du runtime.
# EN : This module centralizes .env loading and environment variable
#      validation. Any missing (or invalid) required variable raises an
#      explicit exception AT LOAD TIME, with a clear message — never a bare
#      KeyError in the middle of runtime.
#
# ⚠️  SÉCURITÉ / SECURITY :
# FR : Ne JAMAIS committer : .env, *.session*, data/state.json, logs/.
# EN : NEVER commit: .env, *.session*, data/state.json, logs/.
# =============================================================================

# --- Imports ------------------------------------------------------------------
# FR : `os` pour lire les variables d'environnement, `pathlib.Path` pour les
#      chemins, `dotenv` pour charger le fichier .env dans os.environ.
# EN : `os` to read environment variables, `pathlib.Path` for file paths,
#      `dotenv` to load the .env file into os.environ.
import os
from pathlib import Path

from dotenv import load_dotenv

# FR : Lecture du fichier .env (s'il existe) situé dans le dossier courant.
# EN : Reads the .env file (if present) located in the current directory.
load_dotenv()


# --- Exception dédiée / Dedicated exception -----------------------------------
class ConfigError(RuntimeError):
    """FR : Erreur de configuration : variable manquante ou invalide.
           Levée au chargement de ce module pour échouer tôt et fort.
       EN : Configuration error: missing or invalid variable. Raised when
           this module is loaded, to fail early and loudly."""


# --- Fonctions internes de lecture / Internal reading helpers -----------------

def _require(name: str) -> str:
    """FR : Retourne la variable d'env `name`, ou lève ConfigError si elle
           est absente ou vide. Utilisée pour les variables OBLIGATOIRES.
           NB : on n'affiche JAMAIS la valeur reçue (sécurité).
       EN : Returns env var `name`, or raises ConfigError if missing or
           empty. Used for REQUIRED variables. NB: the received value is
           NEVER displayed (security)."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Variable d'environnement manquante : {name} — complète ton "
            f"fichier .env (voir .env.example). / "
            f"Missing environment variable: {name} — fill in your .env file."
        )
    return value


def _get_int(name: str, default: int) -> int:
    """FR : Lit une variable d'env entière OPTIONNELLE avec sa valeur par
           défaut. Lève ConfigError si la valeur fournie n'est pas un entier.
       EN : Reads an OPTIONAL integer env var with its default value. Raises
           ConfigError if the provided value is not an integer."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise ConfigError(
            f"La variable {name} doit être un entier. / "
            f"Variable {name} must be an integer."
        ) from None


def _require_int(name: str) -> int:
    """FR : Variante OBLIGATOIRE de _get_int : la variable doit exister ET
           être un entier valide.
       EN : REQUIRED variant of _get_int: the variable must exist AND be a
           valid integer."""
    raw = _require(name)
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(
            f"La variable {name} doit être un entier. / "
            f"Variable {name} must be an integer."
        ) from None


# =============================================================================
# Constantes de configuration / Configuration constants
# =============================================================================

# FR : API_ID — identifiant numérique de ton application Telegram, obtenu sur
#      https://my.telegram.org (API development tools). OBLIGATOIRE.
# EN : API_ID — numeric ID of your Telegram application, obtained from
#      https://my.telegram.org (API development tools). REQUIRED.
API_ID: int = _require_int("API_ID")

# FR : API_HASH — clé secrète associée à API_ID. OBLIGATOIRE. Ne jamais la
#      partager, la logger ou la committer.
# EN : API_HASH — secret key tied to API_ID. REQUIRED. Never share it, log it
#      or commit it.
API_HASH: str = _require("API_HASH")

# FR : PHONE — numéro de téléphone du compte, format international (+33...).
#      OBLIGATOIRE : sert à la première connexion (code de vérification).
# EN : PHONE — account phone number, international format (+33...).
#      REQUIRED: used for the first login (verification code).
PHONE: str = _require("PHONE")

# FR : PASSWORD — mot de passe 2FA Telegram, OPTIONNEL (laisser vide si la
#      vérification en deux étapes est désactivée). Jamais loggé.
# EN : PASSWORD — Telegram 2FA password, OPTIONAL (leave empty if two-step
#      verification is disabled). Never logged.
PASSWORD: str = os.getenv("PASSWORD", "").strip()

# FR : IMAGES_DIR — dossier contenant les images/vidéos envoyées aléatoirement.
# EN : IMAGES_DIR — folder holding the images/videos sent randomly.
IMAGES_DIR: Path = Path(os.getenv("IMAGES_DIR", "images"))

# FR : MESSAGES_FILE — fichier texte des messages aléatoires (un par ligne).
# EN : MESSAGES_FILE — text file with the random messages (one per line).
MESSAGES_FILE: Path = Path(os.getenv("MESSAGES_FILE", "messages.txt"))

# FR : COOLDOWN_SECONDS — temps minimum entre deux réponses à la MÊME
#      personne (anti-spam). 300 s = 5 minutes, comme dans l'original.
# EN : COOLDOWN_SECONDS — minimum time between two replies to the SAME
#      person (anti-spam). 300s = 5 minutes, same as the original.
COOLDOWN_SECONDS: int = _get_int("COOLDOWN_SECONDS", 300)

# FR : REPLY_DELAY_MIN_SECONDS / REPLY_DELAY_MAX_SECONDS — fourchette (en
#      secondes) du délai AVANT de répondre, tiré au hasard à chaque fois
#      (random.uniform) pour paraître humain et éviter tout pattern
#      détectable. REMPLACE l'ancien délai fixe de 10 s.
# EN : REPLY_DELAY_MIN_SECONDS / REPLY_DELAY_MAX_SECONDS — range (in seconds)
#      of the delay BEFORE replying, drawn at random each time
#      (random.uniform), to look human and avoid any detectable pattern.
#      REPLACES the old fixed 10 s delay.
REPLY_DELAY_MIN_SECONDS: int = _get_int("REPLY_DELAY_MIN_SECONDS", 8)
REPLY_DELAY_MAX_SECONDS: int = _get_int("REPLY_DELAY_MAX_SECONDS", 25)

# FR : STATE_FILE — fichier JSON où persiste l'état du bot (mode_absent).
#      C'est LA correction du bug principal : l'état survit aux redémarrages.
#      Ne doit contenir QUE {"mode_absent": bool} — aucune donnée personnelle.
# EN : STATE_FILE — JSON file where the bot state (mode_absent) persists.
#      This IS the fix for the main bug: the state survives restarts. Must
#      contain ONLY {"mode_absent": bool} — no personal data.
STATE_FILE: Path = Path(os.getenv("STATE_FILE", "data/state.json"))

# FR : LOG_FILE — fichier de log principal (rotation gérée par logger_setup).
# EN : LOG_FILE — main log file (rotation handled by logger_setup).
LOG_FILE: Path = Path(os.getenv("LOG_FILE", "logs/bot.log"))

# FR : LOG_MAX_BYTES / LOG_BACKUP_COUNT — taille max d'un fichier de log et
#      nombre d'anciens fichiers conservés par RotatingFileHandler.
# EN : LOG_MAX_BYTES / LOG_BACKUP_COUNT — max size of one log file and number
#      of old files kept by RotatingFileHandler.
LOG_MAX_BYTES: int = _get_int("LOG_MAX_BYTES", 2_000_000)
LOG_BACKUP_COUNT: int = _get_int("LOG_BACKUP_COUNT", 5)

# FR : LOG_LEVEL — niveau de log (DEBUG, INFO, WARNING, ERROR). INFO par défaut.
# EN : LOG_LEVEL — log level (DEBUG, INFO, WARNING, ERROR). INFO by default.
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

# FR : CONNECTION_RETRIES — nombre de tentatives de reconnexion de Telethon.
#      -1 = illimité : le bot survit aux coupures réseau ("Network is
#      unreachable") au lieu d'abandonner après 5 tentatives.
# EN : CONNECTION_RETRIES — number of Telethon reconnection attempts.
#      -1 = unlimited: the bot survives network outages ("Network is
#      unreachable") instead of giving up after 5 attempts.
CONNECTION_RETRIES: int = _get_int("CONNECTION_RETRIES", -1)

# FR : RETRY_DELAY — délai en secondes entre deux tentatives de reconnexion.
# EN : RETRY_DELAY — delay in seconds between two reconnection attempts.
RETRY_DELAY: int = _get_int("RETRY_DELAY", 5)

# FR : Validation finale : la borne basse du délai humain ne peut pas dépasser
#      la borne haute (sinon random.uniform planterait au premier envoi).
# EN : Final validation: the human-delay lower bound cannot exceed the upper
#      bound (otherwise random.uniform would crash on the first reply).
if REPLY_DELAY_MIN_SECONDS > REPLY_DELAY_MAX_SECONDS:
    raise ConfigError(
        "REPLY_DELAY_MIN_SECONDS doit être <= REPLY_DELAY_MAX_SECONDS. / "
        "REPLY_DELAY_MIN_SECONDS must be <= REPLY_DELAY_MAX_SECONDS."
    )