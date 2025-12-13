# ================================================================
#  Jack – Attribution de rôles via MP (version 24 énigmes)
# ================================================================

import os
import logging
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

from keep_alive import start_web
from unidecode import unidecode

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
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))  # Salon où le bot annonce les réussites

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
    "5": ("étincelle", 1442871105839698000),
    "6": ("anoure", 1442871107890708574),
    "7": ("trois", 1442871110168346826),
    "8": ("ovipare", 1442871112399589477),
    "9": ("minimum", 1442871114291482674),
    "10": ("kymz", 1442871116556271726),
    "11": ("QUAND LA NEIGE SE TAIT LES TRACES PARLENT ENCORE", 1442871118313816185),
    "12": ("sept", 1442871120356442192),
    "13": ("waza", 1442871122629627965),
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
ch = logging.StreamHandler()
ch.setFormatter(fmt)
fh = RotatingFileHandler("logs/bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(ch)
logger.addHandler(fh)

# ================================================================
#  DISCORD CONFIG
# ================================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionnaire temporaire {user_id: numéro_énigme}
current_enigme: dict[int, str] = {}

# ================================================================
#  OUTILS
# ================================================================
def normalize(text: str) -> str:
    """
    Normalise le texte :
    - convertit en minuscules
    - enlève les accents (é → e, è → e, etc.)
    - supprime les espaces en trop
    """
    if not text:
        return ""
    t = unidecode(text).lower().strip()
    return " ".join(t.split())

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
        await message.channel.send(
            f"🔍 Tu veux répondre à l’énigme **{enigme_num}**. Envoie ta réponse maintenant."
        )
        return

    # Étape 2 : réponse
    enigme_en_cours = current_enigme.get(message.author.id)
    if not enigme_en_cours:
        await message.channel.send(
            "❗ Dis d’abord quelle énigme tu veux tenter : `!enigme <numéro>`"
        )
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

    # ------------------------------------------------------------
    # Ajout du rôle + message joueur + log dans le canal dédié
    # ------------------------------------------------------------
    try:
        # 1) Ajout du rôle
        await member.add_roles(role, reason=f"Bonne réponse à l'énigme {enigme_en_cours}")

        # 2) Réponse au joueur (DM)
        await message.channel.send(
            f"✅ Bravo {member.display_name} ! Tu as réussi l'énigme **{role.name}** !"
        )
        logger.info(f"{member} a résolu l'énigme {enigme_en_cours}")

        # 3) Log dans le canal dédié
        if LOG_CHANNEL_ID:
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel is not None:
                try:
                    await log_channel.send(
                        f"🧩 {member.mention} a réussi l'énigme {enigme_en_cours} "
                       # f"et a reçu le rôle **{role.name}**."
                    )
                except discord.Forbidden:
                    logger.warning(
                        "Impossible d'envoyer le message dans le salon de log (permissions)."
                    )
                except discord.HTTPException as e:
                    logger.warning(f"Erreur HTTP lors de l'envoi dans le salon de log: {e}")

        # 4) On nettoie l'état
        if message.author.id in current_enigme:
            del current_enigme[message.author.id]

    except discord.Forbidden:
        await message.channel.send("⚠️ Permission insuffisante pour attribuer le rôle.")
    except discord.HTTPException:
        await message.channel.send("⚠️ Erreur Discord. Réessaie plus tard.")

    # Laisse passer d’éventuelles autres commandes
    await bot.process_commands(message)


# ================================================================
#  DÉMARRAGE
# ================================================================
bot.run(TOKEN, log_handler=None)
