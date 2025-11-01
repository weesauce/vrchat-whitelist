import discord
from discord import app_commands
import json
import os
import subprocess

# ---------------- CONFIG ----------------
TOKEN = os.getenv("DISCORD_TOKEN")  # Replace with your Discord bot token
GUILD_ID = 1358207512238882967  # Replace with your server ID
ALLOWED_ROLES = [1433955314356584540, 1358207768351473970]  # Role IDs allowed to register
JSON_FILE = "whitelist.json"
# ----------------------------------------

# ---------------- JSON HELPERS ----------------
def load_json():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_json(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- GITHUB UPLOAD ----------------
def upload_to_github():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("⚠️ GITHUB_TOKEN not found in environment variables.")
        return

    repo_url = f"https://{token}@github.com/weesauce/vrchat-whitelist.git"  # Replace YOUR_USERNAME/REPO

    try:
        subprocess.run(["git", "add", "whitelist.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Update whitelist"], check=True)
        subprocess.run(["git", "push", repo_url, "main"], check=True)
        print("✅ whitelist.json successfully uploaded to GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git upload failed: {e}")

# ---------------- DISCORD BOT ----------------
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot connected as {client.user}")

# ---------------- SLASH COMMANDS ----------------
@tree.command(name="register", description="Register your VRChat username", guild=discord.Object(id=GUILD_ID))
async def register(interaction: discord.Interaction, username: str):
    member = interaction.user

    # Check if member has allowed role
    if not any(role.id in ALLOWED_ROLES for role in member.roles):
        await interaction.response.send_message("❌ You do not have permission to register.", ephemeral=True)
        return

    data = load_json()
    if any(u["discord_id"] == str(member.id) for u in data):
        existing = next(u for u in data if u["discord_id"] == str(member.id))
        await interaction.response.send_message(
            f"❌ Already registered as `{existing['vrchat_username']}`! Use `/unregister` first.", ephemeral=True
        )
        return

    # Add user
    data.append({"discord_id": str(member.id), "vrchat_username": username})
    save_json(data)
    upload_to_github()
    await interaction.response.send_message(f"✅ VRChat username `{username}` registered successfully!", ephemeral=True)

@tree.command(name="unregister", description="Unregister your VRChat username", guild=discord.Object(id=GUILD_ID))
async def unregister(interaction: discord.Interaction):
    member = interaction.user
    data = load_json()

    if not any(u["discord_id"] == str(member.id) for u in data):
        await interaction.response.send_message("❌ You are not registered yet!", ephemeral=True)
        return

    # Remove user
    data = [u for u in data if u["discord_id"] != str(member.id)]
    save_json(data)
    upload_to_github()
    await interaction.response.send_message("✅ You have been unregistered.", ephemeral=True)

# ---------------- RUN BOT ----------------
client.run(TOKEN)
