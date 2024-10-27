import discord
from discord.ext import commands
import logging
import os
from datetime import datetime

# Set up logging directory and format
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create a timestamped log file
log_filename = os.path.join(log_dir, f"bot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Dictionary to hold player data and bidding sessions
player_data = {}
bidding_sessions = {}

# Define the roles for each rank
general_role = "General"
super_admin_role = "Commander"  # Super Admin role (Commander only)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Enable voice state tracking for attendance

# Initialize bot with case-insensitivity
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

# Utility functions for role checks
def is_general_or_super_admin(ctx):
    """Checks if the user is either a General or the Commander."""
    role_names = [role.name for role in ctx.author.roles]
    return general_role in role_names or super_admin_role in role_names

def is_super_admin(ctx):
    """Checks if the user is the Commander (Super Admin)."""
    role_names = [role.name for role in ctx.author.roles]
    return super_admin_role in role_names

class Player:
    def __init__(self, name, dkp=0):
        self.name = name
        self.dkp = dkp

    def add_dkp(self, points):
        self.dkp += points

    def deduct_dkp(self, points):
        self.dkp = max(self.dkp - points, 0)  # Avoid negative DKP

class Bid:
    def __init__(self, item_name):
        self.item_name = item_name
        self.highest_bid = 0
        self.highest_bidder = None

    def place_bid(self, player, bid_amount):
        if bid_amount > self.highest_bid:
            self.highest_bid = bid_amount
            self.highest_bidder = player
            return True
        return False

# Command to add or subtract DKP from a player (Generals and Commander)
@bot.command(name="addDkp")
@commands.check(is_general_or_super_admin)
async def add_dkp(ctx, player: discord.Member, dkp_award: int):
    # Log command usage
    logging.info(f"{ctx.author} executed addDkp with args: player={player.name}, dkp_award={dkp_award}")

    # Check if player has existing DKP data, if not, initialize it
    if player.id not in player_data:
        player_data[player.id] = Player(player.name)

    # Add or subtract the specified DKP amount
    player_data[player.id].add_dkp(dkp_award)
    logging.info(f"{ctx.author} adjusted {player.name}'s DKP by {dkp_award}. Total DKP is now {player_data[player.id].dkp}.")

    # Inform the user of the updated DKP total
    await ctx.send(f"{player.name} now has {player_data[player.id].dkp} DKP.")

# Error handler for add_dkp command
@add_dkp.error
async def add_dkp_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "**Incorrect Usage of `!adddkp`!**\n"
            "Correct usage: `!adddkp @player dkp_amount`\n"
            "Example: `!adddkp @Player 20`"
        )
    else:
        await ctx.send("An error occurred. Please check your command and try again.")
    logging.error(f"Error in addDkp command: {error}")

# Command to check DKP balance (open to everyone)
@bot.command(name="checkDkp")
async def check_dkp(ctx, player: discord.Member = None):
    # Log command usage
    logging.info(f"{ctx.author} executed checkDkp with args: player={player.name if player else 'self'}")

    if player is None:
        player = ctx.author

    if player.id not in player_data:
        await ctx.send(f"{player.name} has no recorded DKP.")
        return

    await ctx.send(f"{player.name} has {player_data[player.id].dkp} DKP.")

# Error handler for check_dkp command
@check_dkp.error
async def check_dkp_error(ctx, error):
    await ctx.send("**Usage:** `!checkdkp [@player]`\nExample: `!checkdkp @Player`")
    logging.error(f"Error in checkDkp command: {error}")

# Command to start a bidding session (Generals and Commander)
@bot.command(name="startBid")
@commands.check(is_general_or_super_admin)
async def start_bid(ctx, item_name: str):
    # Log command usage
    logging.info(f"{ctx.author} executed startBid with args: item_name={item_name}")

    if ctx.channel.id in bidding_sessions:
        await ctx.send("A bidding session is already active in this channel.")
        return

    bidding_sessions[ctx.channel.id] = Bid(item_name)
    logging.info(f"{ctx.author} started a bidding session for {item_name}.")
    await ctx.send(f"Bidding started for **{item_name}**! Type `!bid <amount>` to place your bid (maximum 30 DKP).")

# Error handler for start_bid command
@start_bid.error
async def start_bid_error(ctx, error):
    await ctx.send("**Usage:** `!startbid item_name`\nExample: `!startbid Epic Sword`")
    logging.error(f"Error in startBid command: {error}")

# DKP Help command (open to everyone)
@bot.command(name="dkpHelp")
async def dkp_help(ctx):
    # Log command usage
    logging.info(f"{ctx.author} executed dkpHelp")

    help_message = """
    **DKP System Commands:**

    1. Add DKP (`!adddkp @player dkp_amount`):
       - Adds or subtracts DKP to/from a player (e.g., `!adddkp @player 20` or `!adddkp @player -5`).
    
    2. Check DKP (`!checkdkp [@player]`):
       - Check the DKP balance of a player.
    
    3. Start Bid (`!startbid item_name`):
       - Start a DKP bidding session for loot (restricted to Generals and Commanders).
    
    4. Place Bid (`!bid amount`):
       - Place a bid in an active bidding session (maximum 30 DKP).
    
    5. End Bid (`!endbid`):
       - End a bidding session and declare the winner (restricted to Generals and Commanders).
    
    6. Log Attendance (`!attendance`):
       - Logs all users in your current voice channel to text (restricted to Generals and Commanders).
    
    7. Wipe Data (`!ifyourenteringthisyouaredoingthisonpurposeass True`):
       - Wipes all DKP data with confirmation (restricted to Commander only).

    **Follow Mako Rehaps:**
    - YouTube: https://www.youtube.com/@MakoRehaps-_-_-/featured
    - SoundCloud: https://soundcloud.com/mako_rehaps
    - X (Twitter): https://x.com/MakoRehaps
    """
    await ctx.send(help_message)
    logging.info("Displayed DKP help message with socials.")

# Prompt for bot token at runtime and start the bot
token = input("Enter your Discord bot token: ")
bot.run(token)
