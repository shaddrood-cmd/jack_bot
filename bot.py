import os
import json
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

# --- mini serveur web pour Render (bind du port pour Web Service) ---
from keep_alive import start_web
start_web()  # indispensable en Web Service sur Render

# (optionnel local) charger .env si présent
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ============================== CONFIG ===============================
TOKEN = os.environ.get("DISCORD_TOKEN")              # OBLIGATOIRE
SERVER_ID = int(os.environ.get("SERVER_ID", "0"))    # OBLIGATOIRE

# Mappage multi-mots -> rôles via JSON (recommandé)
# Exemple Render > Environment:
# KEYWORDS_JSON = {"test":111111111111111111,"avalon":222222222222222222}
KEYWORDS_JSON_RAW = os.environ.get("KEYWORDS_JSON", "").strip()

# Fallback possible si tu veux garder un seul mot:
ROLE_ID_TEST = int(os.environ.get("ROLE_ID_TEST", "0"))

# ============================== LOGGING ==============================
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")

ch = logging.StreamHandler(); ch.setLevel(logging.INFO); ch.setFormatter(fmt)
fh = RotatingFileHandler("logs/bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
fh.setLevel(logging.INFO); fh.setFormatter(fmt)

logger.addHandler(ch); logger.addHandler(fh)

# =========================== LECTURE MAPPING =========================
KEYWORDS_MAP: dict[str, int] = {}

if KEYWORDS_JSON_RAW:
    try:
        parsed = json.loads(KEYWORDS_JSON_RAW)
        KEYWORDS_MAP = {str(k).lower().strip(): int(v) for k, v in parsed.items()}
    except Exception as e:
        logger.error(f"KEYWORDS_JSON invalide (JSON) : {e}")
        KEYWORDS_MAP = {}

if not KEYWORDS_MAP and ROLE_ID_TEST:
    # Fallback: le mot "test" attribue ROLE_ID_TEST
    KEYWORDS_MAP = {"test": ROLE_ID_TEST}

# ======================= VERIF CONFIG CRITIQUE =======================
missing = []
if not TOKEN: missing.append("DISCORD_TOKEN")
if not SERVER_ID: missing.append("SERVER_ID")
if not KEYWORDS_MAP: missing.append("KEYWORDS_JSON ou ROLE_ID_TEST")
if missing:
    logger.error("Configuration manquante : " + ", ".join(missing))
    raise SystemExit(1)

# ============================== DISCORD ==============================
intents = discord.Intents.default()
intents.members = True           # nécessaire pour get_member / add_roles
intents.message_content = True   # lire le contenu des MP
intents.dm_messages = True       # recevoir les DM

bot = commands.Bot(command_prefix="!", intents=intents)

def normalize(s: str) -> str:
    s = (s or "").strip().lower()
    return " ".join(s.split())

@bot.event
async def on_ready():
    logger.info(f"{bot.user} connecté. Prêt à recevoir des MP.")
    logger.info(f"Mots-clés actifs : {', '.join(KEYWORDS_MAP.keys())}")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # On traite UNIQUEMENT les MP
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

        content_raw = message.content
        content = normalize(content_raw)
        logger.info(f"DM de {message.author}: {content_raw!r} → {content!r}")

        role_id = KEYWORDS_MAP.get(content)
        if not role_id:
            await message.channel.send("❌ Mauvaise réponse, essaie encore !")
            return

        role = guild.get_role(role_id)
        if not role:
            await message.channel.send("⚠️ Rôle introuvable sur le serveur.")
            logger.error(f"Rôle introuvable: role_id={role_id}")
            return

        if role in getattr(member, "roles", []):
            await message.channel.send(f"ℹ️ Tu as déjà le rôle **{role.name}**.")
            return

        try:
            await member.add_roles(role, reason=f"Réponse d'énigme ({content})")
            await message.channel.send(f"✅ Bravo {member.display_name}, rôle **{role.name}** attribué.")
            logger.info(f"Rôle '{role.name}' attribué à {member} ({member.id})")
        except discord.Forbidden:
            await message.channel.send("⚠️ Permission insuffisante (Manage Roles / hiérarchie).")
            logger.error("Permission manquante: Manage Roles ou rôle du bot trop bas.")
        except discord.HTTPException as e:
            await message.channel.send("⚠️ Erreur Discord lors de l'attribution du rôle. Réessaie plus tard.")
            logger.exception(f"HTTPException add_roles : {e}")

    await bot.process_commands(message)

# ============================== RUN BOT =============================
bot.run(TOKEN, log_handler=None)
