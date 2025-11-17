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
    "1": ("suis la lumiere", 1433953119435231302),
    "2": ("centrolenidae", 1433953164528193576),
    "3": ("tradition", 1434140907829198910),
    "4": ("réponse4", 1434140930373582870),
    "5": ("réponse5", 1434140933103947826),
    "6": ("réponse6", 1434140935607943229),
    "7": ("réponse7", 1434140936518242324),
    "8": ("réponse8", 1434140937310834688),
    "9": ("réponse9", 1434140937650700428),
    "10": ("réponse10", 1434140938111946792),
    "11": ("réponse11", 1434140938682372146),
    "12": ("réponse12", 1434141040130002994),
    "13": ("réponse13", 1434141044395741204),
    "14": ("réponse14", 1434141046538899607),
    "15": ("réponse15", 1434141048141250610),
    "16": ("réponse16", 1434141049932087397),
    "17": ("réponse17", 1434141051790168154),
    "18": ("réponse18", 1434141053581135882),
    "19": ("réponse19", 1434141055405523045),
    "20": ("réponse20", 1434141056626331738),
    "21": ("réponse21", 1434141058102591498),
    "22": ("réponse22", 1434141059784380527),
    "23": ("réponse23", 1434143585212567562),
    "24": ("réponse24", 1434141061336272896),
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
        await message.channel.send(f"ℹ️ Tu as déjà le rôle **{role.name}**.")
        return

    try:
        await member.add_roles(role, reason=f"Bonne réponse à l’énigme {enigme_en_cours}")
        await message.channel.send(f"✅ Bravo {member.display_name} ! Tu gagnes le rôle **{role.name}** 🎉")
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
