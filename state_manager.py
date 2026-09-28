# =============================================================================
# state_manager.py — État persistant du bot / Persistent bot state
# =============================================================================
# FR : Corrige LE bug principal de l'ancienne version : mode_absent repartait
#      à False à chaque redémarrage. Désormais l'état est stocké dans
#      data/state.json (JSON) et rechargé au démarrage. L'écriture est
#      ATOMIQUE (fichier .tmp puis os.replace) pour ne jamais corrompre
#      l'état si le process crashe pendant l'écriture.
#      Le fichier ne contient QUE {"mode_absent": bool} — aucune donnée
#      personnelle.
# EN : Fixes THE main bug of the old version: mode_absent reset to False on
#      every restart. The state is now stored in data/state.json (JSON) and
#      reloaded at startup. Writes are ATOMIC (.tmp file then os.replace) so
#      the state is never corrupted if the process crashes mid-write.
#      The file contains ONLY {"mode_absent": bool} — no personal data.
#
# ⚠️  Ne jamais committer data/state.json. Never commit data/state.json.
# =============================================================================

import json
import os

from config import STATE_FILE
from logger_setup import setup_logger

# FR : Logger de ce module (remplace les print de l'ancienne version).
# EN : This module's logger (replaces the old version's print calls).
logger = setup_logger(__name__)

# FR : État par défaut utilisé si le fichier n'existe pas ou est illisible.
# EN : Default state used when the file does not exist or is unreadable.
DEFAULT_STATE: dict = {"mode_absent": False}

# FR : Copie de l'état gardée en mémoire pour éviter de relire le disque à
#      chaque message. None = pas encore chargé.
# EN : In-memory copy of the state to avoid hitting the disk on every
#      message. None = not loaded yet.
_state: dict | None = None


def load_state() -> dict:
    """FR : Lit data/state.json s'il existe et le charge en mémoire. S'il
           n'existe pas, crée le fichier avec l'état par défaut
           {"mode_absent": False}. S'il est corrompu, repart du défaut
           (avec un warning) au lieu de planter le bot.
           À appeler UNE FOIS au démarrage, AVANT d'enregistrer le handler.
       EN : Reads data/state.json if it exists and loads it in memory. If
           missing, creates the file with the default state
           {"mode_absent": False}. If corrupted, falls back to the default
           (with a warning) instead of crashing the bot. Call ONCE at
           startup, BEFORE registering the event handler."""
    global _state

    # FR : S'assure que le dossier data/ existe avant toute écriture.
    # EN : Make sure the data/ folder exists before any write.
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists():
        # FR : Premier lancement : état par défaut, écrit immédiatement.
        # EN : First run: default state, written immediately.
        state = dict(DEFAULT_STATE)
        save_state(state)
        logger.info("Fichier d'état absent : créé avec l'état par défaut (%s)", STATE_FILE)
        _state = state
        return state

    try:
        # FR : On normalise : le fichier ne doit contenir QUE la clé
        #      mode_absent, coercée en booléen (rien d'autre n'est conservé).
        # EN : Normalizing: the file must contain ONLY the mode_absent key,
        #      coerced to bool (nothing else is kept).
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        state = {"mode_absent": bool(raw.get("mode_absent", False))}
    except (json.JSONDecodeError, OSError, AttributeError) as e:
        # FR : JSON invalide ou fichier illisible : on repart du défaut.
        # EN : Invalid JSON or unreadable file: fall back to the default.
        logger.warning("Fichier d'état illisible (%s) : état par défaut réécrit.", e)
        state = dict(DEFAULT_STATE)
        save_state(state)

    _state = state
    logger.info("État chargé depuis %s : mode_absent=%s", STATE_FILE, state["mode_absent"])
    return state


def save_state(state: dict) -> None:
    """FR : Écrit l'état sur disque de façon ATOMIQUE : on écrit d'abord dans
           un fichier temporaire `<state.json>.tmp`, puis os.replace() le
           renomme en une seule opération. Ainsi, un crash pendant l'écriture
           laisse l'ancien fichier intact au lieu d'un JSON à moitié écrit.
       EN : Writes the state to disk ATOMICALLY: first write to a temporary
           `<state.json>.tmp` file, then os.replace() renames it in a single
           operation. A crash mid-write therefore leaves the previous file
           intact instead of a half-written JSON."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    tmp_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp_path, STATE_FILE)


def _ensure_loaded() -> dict:
    """FR : Garantit que l'état est chargé en mémoire (appel paresseux de
           load_state() au premier accès si bot.py n'a pas encore chargé).
       EN : Guarantees the state is loaded in memory (lazy load_state() call
           on first access if bot.py has not loaded it yet)."""
    global _state
    if _state is None:
        load_state()
    return _state  # FR : non-None garanti ici / EN: guaranteed non-None here


def get_mode_absent() -> bool:
    """FR : Retourne la valeur actuelle de mode_absent.
       EN : Returns the current value of mode_absent."""
    return bool(_ensure_loaded().get("mode_absent", False))


def set_mode_absent(value: bool) -> None:
    """FR : Met à jour mode_absent en mémoire ET persiste immédiatement sur
           disque, pour survivre à n'importe quel redémarrage (coupure
           réseau, reboot, crash). Remplace l'ancien `global mode_absent`.
       EN : Updates mode_absent in memory AND persists it to disk right away,
           to survive any restart (network outage, reboot, crash). Replaces
           the old `global mode_absent`."""
    state = _ensure_loaded()
    state["mode_absent"] = bool(value)
    save_state(state)
    logger.info("mode_absent = %s (état persisté sur disque)", state["mode_absent"])