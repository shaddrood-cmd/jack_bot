# ================================================================
#  Jack – Attribution de rôles via MP (version 24 énigmes)
# ================================================================

import os
import logging
from logging.handlers import RotatingFileHandler
import discord
from discord.ext import commands
from keep_alive import start_web

# Démarre le mini serveur pour Render
start_web()

# Charge les variables d'environnement si .env présent (optionnel local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ================================================================
#  CONFIGURATION DE BASE
# ================================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
SERVER_ID = int(os.environ.get("SERVER_ID", "0"))

# ================================================================
#  TABLE DES 24 ÉNIGMES
# ------------------------------------------------
# Format : "numéro": ("réponse", ID_DU_ROLE)
# ================================================================
ENIGMES = {
    "1": ("suis la lumiere", 1442871050487468142),
    "2": ("centrolenidae", 1442871095178035353),
    "3": ("tradition", 1442871100299280385),
    "4": ("passé", 1442871103574900826),
    "5": ("bonus", 1442871105839698000),
    "6": ("aprem", 1442871107890708574),
    "7": ("echo", 1442871110168346826),
    "8": ("réponse8", 1442871112399589477),
    "9": ("réponse9", 1442871114291482674),
    "10": ("réponse10", 1442871116556271726),
    "11": ("réponse11", 1442871118313816185),
    "12": ("réponse12", 1442871120356442192),
    "13": ("réponse13", 1442871122629627965),
    "14": ("réponse14", 1442871124013613108),
    "15": ("réponse15", 1442871126484189264),
    "16": ("réponse16", 1442871128396664872),
    "17": ("réponse17", 1442871130158268426),
    "18": ("réponse18", 1442871132121333770),
    "19": ("réponse19", 1442871133589209153),
    "20": ("réponse20", 1442871136193871945),
    "21": ("réponse21", 1442871138031112202),
    "22": ("réponse22", 1442871140228796476),
    "23": ("réponse23", 1442871141986205832),
    "24": ("réponse24", 1442871143609663511),
}

# ================================================================
#  LOGGING
# ================================================================
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
ch = logging.StreamHandler(); ch.setFormatter(fmt)
fh = RotatingFileHandler("logs/bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(ch); logger.addHandler(fh)

# ================================================================
#  DISCORD CONFIG
# ================================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionnaire temporaire {user_id: numéro_énigme}
current_enigme = {}

# ================================================================
#  OUTILS
# ================================================================
def normalize(txt: str) -> str:
    """Met en minuscule et supprime les espaces superflus."""
    return " ".join((txt or "").lower().strip().split())

# ================================================================
#  ÉVÈNEMENTS DU BOT
# ================================================================
@bot.event
async def on_ready():
    logger.info(f"{bot.user} connecté et opérationnel ✅")
    logger.info(f"Énigmes actives : {', '.join(sorted(ENIGMES.keys()))}")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # Ignorer les messages hors DM
    if not isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return

    guild = bot.get_guild(SERVER_ID)
    if not guild:
        await message.channel.send("⚠️ Serveur introuvable ou bot mal configuré.")
        return

    member = guild.get_member(message.author.id)
    if not member:
        await message.channel.send("❌ Tu dois être membre du serveur pour participer.")
        return

    content = normalize(message.content)
    logger.info(f"DM de {message.author}: {content!r}")

    # Étape 1 : choix de l’énigme
    if content.startswith("!enigme"):
        parts = content.split()
        if len(parts) < 2:
            await message.channel.send("❓ Utilisation : `!enigme <numéro>` (ex: `!enigme 3`)")
            return

        enigme_num = parts[1]
        if enigme_num not in ENIGMES:
            await message.channel.send("⚠️ Cette énigme n’existe pas (choisis entre 1 et 24).")
            return

        current_enigme[message.author.id] = enigme_num
        await message.channel.send(f"🔍 Tu veux répondre à l’énigme **{enigme_num}**. Envoie ta réponse maintenant.")
        return

    # Étape 2 : réponse
    enigme_en_cours = current_enigme.get(message.author.id)
    if not enigme_en_cours:
        await message.channel.send("❗ Dis d’abord quelle énigme tu veux tenter : `!enigme <numéro>`")
        return

    bonne_reponse, role_id = ENIGMES[enigme_en_cours]
    if normalize(content) != normalize(bonne_reponse):
        await message.channel.send("❌ Mauvaise réponse pour cette énigme.")
        return

    role = guild.get_role(role_id)
    if not role:
        await message.channel.send("⚠️ Rôle introuvable sur le serveur.")
        return

    if role in member.roles:
        await message.channel.send(f"ℹ️ Tu as déjà réussi l'énigme **{role.name}**.")
        return

    try:
        await member.add_roles(role, reason=f"Bonne réponse à l’énigme {enigme_en_cours}")
        await message.channel.send(f"✅ Bravo {member.display_name} ! Tu as réussi l'énigme **{role.name}** !")
        logger.info(f"{member} a résolu l’énigme {enigme_en_cours}")
        del current_enigme[message.author.id]
    except discord.Forbidden:
        await message.channel.send("⚠️ Permission insuffisante pour attribuer le rôle.")
    except discord.HTTPException:
        await message.channel.send("⚠️ Erreur Discord. Réessaie plus tard.")

# ================================================================
#  DÉMARRAGE
# ================================================================
bot.run(TOKEN, log_handler=None)


##  await message.channel.send(f"✅ Bravo {member.display_name} ! Tu gagnes le rôle **{role.name} 🎉")
## await message.channel.send(f"ℹ️ Tu as déjà le rôle **{role.name}**.") 
