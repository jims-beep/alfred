
# Auto-répondeur Telegram (refonte) / Telegram auto-reply userbot (refactor)

FR : Userbot qui répond automatiquement aux PV quand le mode absent est actif
     (image aléatoire + message aléatoire). L'état est persistant : le bot
     retrouve son mode après un redémarrage, même après une coupure réseau.
EN : Userbot that auto-replies to DMs while away mode is on (random image +
     random message). The state is persistent: the bot restores its mode
     after a restart, even after a network outage.

## ⚠️ Sécurité / Security

Ne JAMAIS committer : `.env`, `*.session*`, `data/state.json`, `logs/`.
NEVER commit: `.env`, `*.session*`, `data/state.json`, `logs/`.

## Prérequis / Requirements

- Python **≥ 3.10** (syntaxe `int | None` utilisée / `int | None` syntax used)
- Un compte Telegram + `API_ID`/`API_HASH` (https://my.telegram.org)

## Installation

```bash
cd ~/Documents/Mes_projets/Mon_usr_bot_telegram
rm -rf .venv                      # recréer le venv proprement / recreate venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # puis remplir les valeurs / then fill values
mkdir -p data logs
python3 bot.py
```

## Secret chiffré / Encrypted secret

`.env` n'est JAMAIS committé. Seul `.env.age` (chiffré avec `age`)
est versionné, pour retrouver la config sur une nouvelle machine :

```bash
age --decrypt -i ~/.config/age/keys.txt -o .env .env.age
# après modif du .env, re-chiffrer / after editing .env, re-encrypt :
age --encrypt -R ~/.config/age/recipient.txt -o .env.age .env
```

## Commandes (à taper dans tes Messages enregistrés / in your Saved Messages)

| Commande   | Effet / Effect                                                              |
|------------|-----------------------------------------------------------------------------|
| `.absent`  | Active l'auto-réponse (persisté sur disque) / Enable auto-reply (persisted) |
| `.present` | Désactive + vide le cooldown (persisté) / Disable + clear cooldown (persisted) |

## Checklist de tests avant mise en prod / Pre-production test checklist

1. **Persistance** : démarrer le bot, taper `.absent`, couper puis relancer le
   process → vérifier que le bot répond toujours sans retaper `.absent`
   (le log de démarrage doit afficher « Mode absent restauré depuis le
   disque : True »).
   *Persistence: start the bot, type `.absent`, kill and restart the process
   → the bot must still reply without retyping `.absent`.*

2. **Cooldown** : envoyer 3 messages rapprochés depuis un autre compte →
   vérifier qu'une seule réponse part (cooldown respecté).
   *Cooldown: send 3 quick messages from another account → only one reply
   must be sent.*

3. **Logs** : vérifier dans `logs/bot.log` que chaque redémarrage, chaque
   réponse envoyée et chaque erreur apparaissent avec un timestamp.
   *Logs: check `logs/bot.log` shows every restart, reply and error with a
   timestamp.*

4. **Résilience réseau** : couper le réseau localement quelques secondes
   pendant que le bot tourne → vérifier qu'il se reconnecte seul sans
   crasher.
   *Network resilience: cut the network for a few seconds while running →
   the bot must reconnect on its own without crashing.*
`````

