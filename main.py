from dotenv import load_dotenv
import discord
from discord import app_commands
import json
import os
import subprocess

load_dotenv()

# ---------------- CONFIG ----------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # Discord bot token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub personal access token
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")  # GitHub username
REPO_PATH = os.getcwd()  # Local repo path (current folder)
GUILD_ID = 1358207512238882967  # Replace with your server ID
ALLOWED_ROLES = [
    1433955314356584540, 1358207768351473970, 1434243145813463120
]  # Allowed role IDs
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
    if not (GITHUB_TOKEN and GITHUB_USERNAME and REPO_PATH):
        print("⚠️ GitHub credentials missing.")
        return

    repo_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/vrchat-whitelist.git"

    try:
        result = subprocess.run(
            ["git", "-C", REPO_PATH, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True)
        current_branch = result.stdout.strip()
        print(f"Current branch: {current_branch}")

        subprocess.run(["git", "-C", REPO_PATH, "add", JSON_FILE], check=True)

        try:
            subprocess.run(
                ["git", "-C", REPO_PATH, "commit", "-m", "Update whitelist"],
                check=True)
        except subprocess.CalledProcessError:
            print("⚠️ Nothing to commit, skipping commit.")

        subprocess.run(
            ["git", "-C", REPO_PATH, "push", repo_url, current_branch],
            check=True)
        print("✅ whitelist.json successfully uploaded to GitHub!")

    except subprocess.CalledProcessError as e:
        print(f"❌ GitHub upload failed: {e}")


# ---------------- DISCORD BOT ----------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot connected as {client.user}")


# ---------------- SLASH COMMANDS ----------------
@tree.command(name="register",
              description="Register your VRChat username",
              guild=discord.Object(id=GUILD_ID))
async def register(interaction: discord.Interaction, username: str):
    member = interaction.user

    if not any(role.id in ALLOWED_ROLES for role in member.roles):
        await interaction.response.send_message(
            "❌ You do not have permission to register.", ephemeral=True)
        return

    data = load_json()
    if any(u["discord_id"] == str(member.id) for u in data):
        existing = next(u for u in data if u["discord_id"] == str(member.id))
        await interaction.response.send_message(
            f"❌ Already registered as `{existing['vrchat_username']}`! Use `/unregister` first.",
            ephemeral=True)
        return

    # Only store allowed roles
    allowed_roles = [r.id for r in member.roles if r.id in ALLOWED_ROLES]

    data.append({
        "discord_id": str(member.id),
        "vrchat_username": username,
        "roles": allowed_roles
    })

    save_json(data)
    upload_to_github()
    await interaction.response.send_message(
        f"✅ VRChat username `{username}` registered successfully!",
        ephemeral=True)


@tree.command(name="unregister",
              description="Unregister your VRChat username",
              guild=discord.Object(id=GUILD_ID))
async def unregister(interaction: discord.Interaction):
    member = interaction.user
    data = load_json()

    if not any(u["discord_id"] == str(member.id) for u in data):
        await interaction.response.send_message(
            "❌ You are not registered yet!", ephemeral=True)
        return

    data = [u for u in data if u["discord_id"] != str(member.id)]
    save_json(data)
    upload_to_github()
    await interaction.response.send_message("✅ You have been unregistered.",
                                            ephemeral=True)


# ---------------- MEMBER ROLE UPDATE ----------------
@client.event
async def on_member_update(before: discord.Member, after: discord.Member):
    data = load_json()
    entry = next((u for u in data if u["discord_id"] == str(after.id)), None)
    if entry is None:
        return  # not registered

    # Only keep allowed roles in JSON
    allowed_roles_now = [r.id for r in after.roles if r.id in ALLOWED_ROLES]

    if allowed_roles_now:
        # Update roles if still has allowed roles
        entry["roles"] = allowed_roles_now
    else:
        # Remove from JSON if no allowed roles
        data = [u for u in data if u["discord_id"] != str(after.id)]

    save_json(data)
    upload_to_github()


# ---------------- RUN BOT ----------------
client.run(DISCORD_TOKEN)
