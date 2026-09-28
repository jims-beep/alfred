# =============================================================================
# logger_setup.py — Configuration du logging rotatif / Rotating logging setup
# =============================================================================
# FR : Remplace TOUS les print() du projet par le module `logging` standard :
#      logs horodatés dans logs/bot.log (avec rotation) ET dans la console.
# EN : Replaces ALL print() calls in the project with the standard `logging`
#      module: timestamped logs to logs/bot.log (rotated) AND to the console.
#
# ⚠️  SÉCURITÉ / SECURITY : ne JAMAIS logger API_HASH, PASSWORD ou le contenu
#     d'un fichier .session. Never log API_HASH, PASSWORD or .session content.
# =============================================================================

import logging
from logging.handlers import RotatingFileHandler

from config import LOG_BACKUP_COUNT, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES

# FR : Crée le dossier des logs s'il n'existe pas (sinon RotatingFileHandler
#      échouerait au démarrage).
# EN : Creates the logs folder if missing (otherwise RotatingFileHandler
#      would fail at startup).
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# FR : Format commun à tous les handlers, demandé par le cahier des charges.
# EN : Format shared by every handler, as required by the specification.
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logger(name: str) -> logging.Logger:
    """FR : Configure et retourne un logger nommé `name` avec :
           - un RotatingFileHandler vers LOG_FILE (taille max LOG_MAX_BYTES,
             LOG_BACKUP_COUNT fichiers de sauvegarde),
           - un StreamHandler pour la console,
           - le format LOG_FORMAT, au niveau LOG_LEVEL (INFO par défaut).
           À utiliser dans chaque module : `logger = setup_logger(__name__)`.
       EN : Configures and returns a logger named `name` with:
           - a RotatingFileHandler to LOG_FILE (max size LOG_MAX_BYTES,
             LOG_BACKUP_COUNT backup files),
           - a StreamHandler for the console,
           - the LOG_FORMAT format, at LOG_LEVEL level (INFO by default).
           Use in every module: `logger = setup_logger(__name__)`."""
    logger = logging.getLogger(name)

    # FR : Garde-fou : si ce logger a déjà été configuré (réimport, tests…),
    #      on ne rajoute PAS de handlers en double.
    # EN : Safety net: if this logger was already configured (re-import,
    #      tests…), do NOT add duplicate handlers.
    if logger.handlers:
        return logger

    # FR : Traduit le nom de niveau ("INFO", "DEBUG"…) en constante logging.
    #      Retombe sur INFO si la variable est invalide.
    # EN : Maps the level name ("INFO", "DEBUG"…) to the logging constant.
    #      Falls back to INFO if the variable is invalid.
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT)

    # FR : Handler fichier avec rotation : quand bot.log atteint
    #      LOG_MAX_BYTES, il est renommé en bot.log.1, bot.log.2, etc.
    # EN : Rotating file handler: when bot.log reaches LOG_MAX_BYTES, it is
    #      renamed to bot.log.1, bot.log.2, and so on.
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # FR : Handler console pour le suivi en direct dans le terminal.
    # EN : Console handler for live monitoring in the terminal.
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # FR : Empêche les messages de remonter au logger racine (évite tout
    #      double affichage si un handler racine est ajouté un jour).
    # EN : Prevents records from bubbling up to the root logger (avoids any
    #      double output if a root handler is ever added).
    logger.propagate = False

    return logger