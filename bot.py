# ================================================================
#  Jack – Attribution de rôles via MP (24 énigmes)
#  Hébergement : Render
# ================================================================

import os
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands
from unidecode import unidecode

from keep_alive import start_web

# ------------------------------------------------
# Mini serveur web (Render)
# ------------------------------------------------
start_web()

# ------------------------------------------------
# (Optionnel) .env en local
# ------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ================================================================
# CONFIGURATION
# ================================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = int(os.environ.get("SERVER_ID", "0"))
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))  # 0 = désactivé

# ================================================================
# ÉNIGMES (numéro -> (réponse, role_id))
# ================================================================
ENIGMES = {
    "1": ("suis la lumiere", 1442871050487468142),
    "2": ("centrolenidae", 1442871095178035353),
    "3": ("tradition", 1442871100299280385),
    "4": ("passe", 1442871103574900826),
    "5": ("etincelle", 1442871105839698000),
    "6": ("anoure", 1442871107890708574),
    "7": ("trois", 1442871110168346826),
    "8": ("ovipare", 1442871112399589477),
    "9": ("minimum", 1442871114291482674),
    "10": ("kymz", 1442871116556271726),
    "11": ("quand la neige se tait les traces parlent encore", 1442871118313816185),
    "12": ("sept", 1442871120356442192),
    "13": ("boussole", 1442871122629627965),
    "14": ("craft", 1442871124013613108),
    "15": ("mouche", 1442871126484189264),
    "16": ("rond rond carre etoile carre", 1442871128396664872),
    "17": ("fais quelque chose", 1442871130158268426),
    "18": ("ranidae", 1442871132121333770),
    "19": ("shmouk yimb brel", 1442871133589209153),
    "20": ("?", 1442871136193871945),
    "21": ("cinq", 1442871138031112202),
    "22": ("reponse22", 1442871140228796476),
    "23": ("reponse23", 1442871141986205832),
    "24": ("reponse24", 1442871143609663511),
}

# ================================================================
# LOGS
# ================================================================
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")

console = logging.StreamHandler()
console.setFormatter(fmt)

file = RotatingFileHandler("logs/bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
file.setFormatter(fmt)

logger.addHandler(console)
logger.addHandler(file)

# ================================================================
# DISCORD
# ================================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Mémoire temporaire : user_id -> enigme choisie
current_enigme: dict[int, str] = {}

# ================================================================
# OUTILS
# ================================================================
def normalize(text: str) -> str:
    if not text:
        return ""
    t = unidecode(text).lower().strip()
    return " ".join(t.split())

# ================================================================
# EVENTS
# ================================================================
@bot.event
async def on_ready():
    logger.info(f"{bot.user} connecté ✅")
    logger.info(f"Énigmes actives : {', '.join(ENIGMES.keys())}")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # On ne traite QUE les MP
    if not isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return

    guild = bot.get_guild(SERVER_ID)
    if not guild:
        await message.channel.send("⚠️ Serveur introuvable.")
        return

    member = guild.get_member(message.author.id)
    if not member:
        await message.channel.send("❌ Tu dois être membre du serveur.")
        return

    content = normalize(message.content)
    logger.info(f"DM de {member}: {content!r}")

    # ------------------------------------------------
    # Étape 1 : choisir l’énigme
    # ------------------------------------------------
    if content.startswith("!enigme"):
        parts = content.split()
        if len(parts) != 2:
            await message.channel.send("❓ Utilisation : `!enigme <1-24>`")
            return

        enigme_num = parts[1]
        if enigme_num not in ENIGMES:
            await message.channel.send("⚠️ Enigme invalide (1 à 24).")
            return

        current_enigme[member.id] = enigme_num
        await message.channel.send(
            f"🔍 Tu réponds à l’énigme **{enigme_num}**. Envoie ta réponse."
        )
        return

    # ------------------------------------------------
    # Étape 2 : répondre
    # ------------------------------------------------
    enigme_en_cours = current_enigme.get(member.id)
    if not enigme_en_cours:
        await message.channel.send("❗ D’abord : `!enigme <numéro>`")
        return

    bonne_reponse, role_id = ENIGMES[enigme_en_cours]
    if normalize(content) != normalize(bonne_reponse):
        await message.channel.send("❌ Mauvaise réponse.")
        return

    role = guild.get_role(role_id)
    if not role:
        await message.channel.send("⚠️ Rôle introuvable.")
        return

    if role in member.roles:
        await message.channel.send("ℹ️ Rôle déjà obtenu.")
        return

    # ------------------------------------------------
    # Succès
    # ------------------------------------------------
    try:
        await member.add_roles(role, reason=f"Énigme {enigme_en_cours}")

        # Message spécial énigme 20
        if enigme_en_cours == "20":
            await message.channel.send("🎵 Écoute bien. Tout n’est pas terminé.")
        else:
            await message.channel.send(
                f"✅ Bravo {member.display_name} ! Rôle **{role.name}** attribué."
            )

        logger.info(f"{member} a résolu l’énigme {enigme_en_cours}")

        # Log serveur
        if LOG_CHANNEL_ID:
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"🧩 {member.mention} a résolu l’énigme {enigme_en_cours} "
                    f"→ **{role.name}**"
                )

        current_enigme.pop(member.id, None)

    except discord.Forbidden:
        await message.channel.send("⚠️ Permissions insuffisantes.")
    except discord.HTTPException as e:
        logger.error(e)
        await message.channel.send("⚠️ Erreur Discord.")

    await bot.process_commands(message)

# ================================================================
# DÉMARRAGE
# ================================================================
bot.run(TOKEN, log_handler=None)
