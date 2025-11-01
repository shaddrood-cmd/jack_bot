# ================================================================
#  Jack – Attribution de rôles via MP
#  Hébergement: Render (Web Service) + mini serveur Flask (bind du port)
#  Python 3.10+ / 3.13 OK (audioop.py stub présent à la racine)
# ================================================================

import os
import json
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

# --- Mini serveur web pour Render (bind du port, évite l’endormissement) ---
from keep_alive import start_web
start_web()

# --- (Optionnel en local) charge .env si présent ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ================================================================
#                    ZONE CONFIGURATION GÉNÉRALE
# ================================================================

# 1) OBLIGATOIRE : variables dans Render → Environment
TOKEN = os.environ.get("DISCORD_TOKEN")               # Token du bot
SERVER_ID = int(os.environ.get("SERVER_ID", "0"))     # ID du serveur

# 2) (FACULTATIF) – Config “à distance” depuis Render via JSON :
#    Dans Render → Environment, ajoute KEYWORDS_JSON avec une valeur:
#    {"mot1": 111111111111111111, "mot2": 222222222222222222, ...}
#KEYWORDS_JSON_RAW = os.environ.get("KEYWORDS_JSON", "").strip()

# 3) (FACULTATIF) – Fallback simple si tu préfères garder un seul mot:
#    si tu ne mets pas KEYWORDS_JSON, mais que tu veux "test" -> rôle X:
#ROLE_ID_TEST = int(os.environ.get("ROLE_ID_TEST", "0"))

# ================================================================
#        ZONE À MODIFIER LIBREMENT : MOTS → RÔLES (MANUEL)
# ---------------------------------------------------------------
# Ajoute autant de lignes que tu veux ci-dessous.
# Format: ("mot-à-envoyer-en-MP", ID_DU_ROLE_ENTIER)
# - Le mot est insensible à la casse et aux espaces multiples ("  TeSt  " = "test")
# - L’ID de rôle doit être un INT (clic droit → Copier l’ID dans Discord)
# - Exemple:
#   ("avalon", 222222222222222222),
#   ("camelot", 333333333333333333),

MANUAL_KEYWORDS: list[tuple[str, int]] = [
    ("test", 1433953119435231302),
    ("pomme", 1433953164528193576),
    # ("camelot", 333333333333333333),
]
# ================================================================


# ================================================================
#                         LOGGING PROPRE
# ================================================================
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")

ch = logging.StreamHandler(); ch.setLevel(logging.INFO); ch.setFormatter(fmt)
fh = RotatingFileHandler("logs/bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
fh.setLevel(logging.INFO); fh.setFormatter(fmt)
logger.addHandler(ch); logger.addHandler(fh)


# ================================================================
#                  CONSTRUCTION DU MAPPAGE FINAL
# ================================================================
def normalize(text: str) -> str:
    """Normalise l’entrée utilisateur : trim + minuscule + compaction des espaces."""
    t = (text or "").strip().lower()
    return " ".join(t.split())

KEYWORDS_MAP: dict[str, int] = {}

# A) JSON depuis Render (si fourni)
#if KEYWORDS_JSON_RAW:
#    try:
#        parsed = json.loads(KEYWORDS_JSON_RAW)
#        for k, v in parsed.items():
#            key = normalize(str(k))
#            KEYWORDS_MAP[key] = int(v)
#    except Exception as e:
#        logger.error(f"KEYWORDS_JSON invalide (JSON) : {e}")

# B) Section MANUELLE (prioritaire : écrase le JSON si même clé)
for key, role_id in MANUAL_KEYWORDS:
    KEYWORDS_MAP[normalize(key)] = int(role_id)

# C) Fallback simple si rien d’autre n’est défini et que ROLE_ID_TEST existe
#if not KEYWORDS_MAP and ROLE_ID_TEST:
#    KEYWORDS_MAP["test"] = ROLE_ID_TEST


# ================================================================
#                      VALIDATION CONFIG CRITIQUE
# ================================================================
missing = []
if not TOKEN: missing.append("DISCORD_TOKEN")
if not SERVER_ID: missing.append("SERVER_ID")
if not KEYWORDS_MAP: missing.append("KEYWORDS_JSON ou MANUAL_KEYWORDS ou ROLE_ID_TEST")
if missing:
    logger.error("Configuration manquante : " + ", ".join(missing))
    raise SystemExit(1)


# ================================================================
#                             DISCORD
# ================================================================
intents = discord.Intents.default()
intents.members = True            # nécessaire pour get_member / add_roles
intents.message_content = True    # lire le contenu des MP
intents.dm_messages = True        # recevoir les DM

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"{bot.user} connecté. Prêt à recevoir des MP.")
    logger.info("Mots-clés actifs : " + ", ".join(sorted(KEYWORDS_MAP.keys())))


@bot.event
async def on_message(message: discord.Message):
    """Réagit uniquement aux MP. Compare le message au mappage mots→rôles puis attribue le rôle."""
    if message.author == bot.user:
        return

    # On traite UNIQUEMENT les DM
    if isinstance(message.channel, discord.DMChannel):
        guild = bot.get_guild(SERVER_ID)
        if guild is None:
            await message.channel.send("⚠️ Serveur introuvable. Vérifie l'invitation du bot et SERVER_ID.")
            logger.warning("Guild introuvable (mauvais SERVER_ID ou bot non invité).")
            return

        member = guild.get_member(message.author.id)
        if member is None:
            await message.channel.send("❌ Tu dois être membre du serveur pour participer.")
            return

        raw = message.content
        key = normalize(raw)
        logger.info(f"DM de {message.author} : {raw!r} → {key!r}")

        role_id = KEYWORDS_MAP.get(key)
        if not role_id:
            await message.channel.send("❌ Mauvaise réponse, essaie encore !")
            return

        role = guild.get_role(role_id)
        if not role:
            await message.channel.send("⚠️ Rôle introuvable sur le serveur (vérifie l’ID).")
            logger.error(f"Rôle introuvable: role_id={role_id}")
            return

        if role in getattr(member, "roles", []):
            await message.channel.send(f"ℹ️ Tu as déjà le rôle **{role.name}**.")
            return

        try:
            await member.add_roles(role, reason=f"Réponse d'énigme ({key})")
            await message.channel.send(f"✅ Bravo {member.display_name}, rôle **{role.name}** attribué.")
            logger.info(f"Rôle '{role.name}' attribué à {member} ({member.id}) pour mot-clé '{key}'")
        except discord.Forbidden:
            await message.channel.send("⚠️ Permission insuffisante (Manage Roles / hiérarchie).")
            logger.error("Permission manquante: Manage Roles ou rôle du bot trop bas.")
        except discord.HTTPException as e:
            await message.channel.send("⚠️ Erreur Discord lors de l'attribution du rôle. Réessaie plus tard.")
            logger.exception(f"HTTPException add_roles : {e}")

    # Laisser passer d’éventuelles commandes (!help, etc.)
    await bot.process_commands(message)


# ================================================================
#                           DÉMARRAGE
# ================================================================
bot.run(TOKEN, log_handler=None)
