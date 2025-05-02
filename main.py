import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
import json
import openai
import asyncio
from keep_alive import keep_alive

# Global variables
WELCOME_CHANNEL_ID = None
LEAVE_CHANNEL_ID = None
MOD_LOG_CHANNEL_ID = None
WELCOME_MESSAGE = "Welcome {member} to {server}!"
LEAVE_MESSAGE = "Goodbye {member} from {server}!"
WELCOME_IMAGE_URL = None

# Load config
with open("config.json") as f:
    config = json.load(f)

# Initialize intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix=config["prefix"], intents=intents)
tree = bot.tree

# Basic commands
@bot.command()
async def say(ctx, *, message: str):
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    required_role_id = config.get('say_command_role')
    if required_role_id is None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Only administrators can use this command!")
            return
    else:
        role = ctx.guild.get_role(required_role_id)
        if role not in ctx.author.roles:
            await ctx.send(f"❌ You need the {role.name} role to use this command!")
            return
    
    await ctx.message.delete()
    await ctx.send(message)

@tree.command(name="set_say_role", description="Set which role can use the !say command")
@app_commands.describe(role="Role that can use the !say command")
async def slash_set_say_role(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only administrators can use this command!", ephemeral=True)
        return
    
    with open('config.json', 'r+') as f:
        config = json.load(f)
        config['say_command_role'] = role.id
        f.seek(0)
        json.dump(config, f, indent=2)
        f.truncate()
    
    await interaction.response.send_message(f"✅ The !say command can now be used by members with the {role.mention} role")

@tree.command(name="set_logs", description="Set up different types of logging channels")
@app_commands.describe(
    log_type="Type of logs to set up",
    channel="Channel to send logs to"
)
async def slash_set_logs(
    interaction: discord.Interaction,
    log_type: Literal["message", "image", "mod"],
    channel: discord.TextChannel
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    with open('config.json', 'r+') as f:
        config = json.load(f)
        config['logging'][f'{log_type}_logs'] = channel.id
        f.seek(0)
        json.dump(config, f, indent=2)
        f.truncate()
    
    await interaction.response.send_message(f"✅ {log_type.title()} logs will now be sent to {channel.mention}")

@tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")
    await log_command(interaction, 'ping')

@tree.command(name="clear", description="Clear messages")
@app_commands.describe(amount="Number of messages to clear")
async def slash_clear(interaction: discord.Interaction, amount: int = 5):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    
    try:
        # Need to defer since purge might take time
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Cleared {len(deleted)} messages!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to delete messages!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

@tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick", reason="Reason for kick")
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        await log_command(interaction, 'kick', False)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention} for: {reason}")
    await log_command(interaction, 'kick')

@tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban", reason="Reason for ban")
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        await log_command(interaction, 'ban', False)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member.mention} for: {reason}")
    await log_command(interaction, 'ban')

@tree.command(name="autorole", description="Set the automatic role for new members")
@app_commands.describe(role="Role to automatically assign")
async def slash_autorole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    with open("config.json", "r+") as f:
        config = json.load(f)
        config["autorole"] = role.id
        f.seek(0)
        json.dump(config, f, indent=2)
        f.truncate()
    await interaction.response.send_message(f"✅ Auto-role set to {role.mention}")

@tree.command(name="addrole", description="Add a role to a member")
@app_commands.describe(member="Member to add role to", role="Role to add")
async def slash_addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
        
    try:
        # Check if bot's role is higher than the role to be added
        if interaction.guild.me.top_role <= role:
            await interaction.response.send_message("❌ I can't add this role as it's higher than or equal to my highest role!", ephemeral=True)
            return
            
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ Added {role.mention} to {member.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@tree.command(name="set_welcome", description="Set up the welcome system")
@app_commands.describe(
    channel="Channel to send welcome messages",
    message="Custom welcome message (use {member} and {server} as placeholders)"
)
async def slash_set_welcome(
    interaction: discord.Interaction, 
    channel: discord.TextChannel,
    message: str = None,
    attachment: discord.Attachment = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
        
    global WELCOME_CHANNEL_ID, WELCOME_MESSAGE, WELCOME_IMAGE_URL
    WELCOME_CHANNEL_ID = channel.id
    if message:
        WELCOME_MESSAGE = message
    if attachment:
        try:
            WELCOME_IMAGE_URL = attachment.url
            await interaction.response.send_message(f"✅ Welcome messages will be sent to {channel.mention}\nMessage: {WELCOME_MESSAGE}\nImage/GIF has been set!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error setting image/GIF: {str(e)}", ephemeral=True)
            return
    else:
        await interaction.response.send_message(f"✅ Welcome messages will be sent to {channel.mention}\nMessage: {WELCOME_MESSAGE}")

@tree.command(name="remove_welcome", description="Remove welcome message system from a channel")
async def slash_remove_welcome(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
        
    global WELCOME_CHANNEL_ID, WELCOME_IMAGE_URL
    if WELCOME_CHANNEL_ID is None:
        await interaction.response.send_message("❌ Welcome system is not currently set up!", ephemeral=True)
        return
        
    WELCOME_CHANNEL_ID = None
    WELCOME_IMAGE_URL = None
    await interaction.response.send_message("✅ Welcome system has been removed!")

@tree.command(name="set_leave", description="Set up the leave message and channel")
@app_commands.describe(
    channel="Channel to send leave messages",
    message="Custom leave message (use {member} and {server} as placeholders)"
)
async def slash_set_leave(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
        
    global LEAVE_CHANNEL_ID, LEAVE_MESSAGE
    LEAVE_CHANNEL_ID = channel.id
    if message:
        LEAVE_MESSAGE = message
    await interaction.response.send_message(f"✅ Leave messages will be sent to {channel.mention}\nMessage: {LEAVE_MESSAGE}")

@tree.command(name="remove_leave", description="Remove leave message system from a channel")
async def slash_remove_leave(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
        
    global LEAVE_CHANNEL_ID
    if LEAVE_CHANNEL_ID is None:
        await interaction.response.send_message("❌ Leave system is not currently set up!", ephemeral=True)
        return
        
    LEAVE_CHANNEL_ID = None
    await interaction.response.send_message("✅ Leave system has been removed!")

@tree.command(name="removerole", description="Remove a role from a member")
@app_commands.describe(member="Member to remove role from", role="Role to remove")
async def slash_removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
        
    try:
        # Check if bot's role is higher than the role to be removed
        if interaction.guild.me.top_role <= role:
            await interaction.response.send_message("❌ I can't remove this role as it's higher than or equal to my highest role!", ephemeral=True)
            return
            
        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ Removed {role.mention} from {member.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@tree.command(name="warn", description="Warn a member")
@app_commands.describe(member="Member to warn", reason="Reason for warning")
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    await interaction.response.send_message(f"⚠️ Warned {member.mention} for: {reason}")

    if MOD_LOG_CHANNEL_ID:
        channel = interaction.guild.get_channel(MOD_LOG_CHANNEL_ID)
        embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.yellow())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Moderator", value=interaction.user.mention)
        embed.add_field(name="Reason", value=reason)
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot is ready as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

async def log_command(interaction: discord.Interaction, command_name: str, success: bool = True):
    try:
        try:
            with open('command_logs.json', 'r') as f:
                logs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logs = []
        
        log_entry = {
            'timestamp': str(discord.utils.utcnow()),
            'command': command_name,
            'user': str(interaction.user),
            'user_id': str(interaction.user.id),
            'guild': str(interaction.guild),
            'channel': str(interaction.channel),
            'success': success
        }
        
        logs.append(log_entry)
        
        with open('command_logs.json', 'w') as f:
            json.dump(logs, f, indent=2)

        if MOD_LOG_CHANNEL_ID:
            channel = interaction.guild.get_channel(MOD_LOG_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="Command Executed",
                    color=discord.Color.green() if success else discord.Color.red()
                )
                embed.add_field(name="Command", value=command_name)
                embed.add_field(name="User", value=interaction.user.mention)
                embed.add_field(name="Channel", value=interaction.channel.mention)
                embed.timestamp = discord.utils.utcnow()
                await channel.send(embed=embed)
    except Exception as e:
        print(f"Error logging command: {e}")

@bot.event
async def on_message_delete(message):
    if MOD_LOG_CHANNEL_ID:
        channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red())
        embed.add_field(name="Author", value=message.author.mention)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Content", value=message.content[:1024] if message.content else "No content")
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if MOD_LOG_CHANNEL_ID and before.content != after.content:
        channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.blue())
        embed.add_field(name="Author", value=before.author.mention)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Before", value=before.content[:512] if before.content else "No content")
        embed.add_field(name="After", value=after.content[:512] if after.content else "No content")
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

@bot.event
async def on_member_join(member):
    try:
        # Autorole
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        if config['autorole']:
            role = member.guild.get_role(config['autorole'])
            if role:
                await member.add_roles(role)
                if MOD_LOG_CHANNEL_ID:
                    log_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
                    await log_channel.send(f"✅ Added {role.name} role to {member.mention}")
        
        # Welcome message
        if WELCOME_CHANNEL_ID:
            channel = bot.get_channel(WELCOME_CHANNEL_ID)
            if channel:
                welcome_msg = WELCOME_MESSAGE.format(member=member.mention, server=member.guild.name)
                
                embed = discord.Embed(
                    title="Welcome!",
                    description=welcome_msg,
                    color=discord.Color.green()
                )
                
                if WELCOME_IMAGE_URL:
                    embed.set_image(url=WELCOME_IMAGE_URL)
                
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)
                
                # Log successful welcome message
                print(f"Sent welcome message for {member.name}")
    except Exception as e:
        print(f"Error in welcome message: {e}")
    
    # Mod log
    if MOD_LOG_CHANNEL_ID:
        channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        embed = discord.Embed(title="👋 Member Joined", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    # Leave message
    if LEAVE_CHANNEL_ID:
        channel = bot.get_channel(LEAVE_CHANNEL_ID)
        leave_msg = LEAVE_MESSAGE.format(member=member.name, server=member.guild.name)
        
        embed = discord.Embed(
            title="Goodbye!",
            description=leave_msg,
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)
    
    # Mod log
    if MOD_LOG_CHANNEL_ID:
        channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        embed = discord.Embed(title="👋 Member Left", color=discord.Color.orange())
        embed.add_field(name="Member", value=f"{member.name}")
        embed.add_field(name="Joined At", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

# Keep bot alive
keep_alive()
bot.run(config["token"])