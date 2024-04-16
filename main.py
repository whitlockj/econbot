import discord
from discord.ext import commands, tasks
from discord.commands import Option, slash_command
import random
from datetime import datetime, timedelta

# Bot setup
intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# In-memory storage
STARTING_TOKENS = 100
token_balances = {}
weekly_token_earnings = {}
active_bets = {}
user_opt_in = {}
user_stocks = {}
user_last_active = {}
previous_token_balances = {}
last_message_id = None

# Constants for price adjustment
PRICE_INCREASE_FACTOR = 0.05  # 5% increase per unit bought
PRICE_DECREASE_FACTOR = 0.05  # 5% decrease per unit sold

# Constants for lottery
LOTTERY_PRIZE = 1000

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    decay_tokens.start()
    pay_dividends.start()
    market_event.start()
    weekly_update.start()
    post_daily_updates.start()
    monthly_lottery.start()

@tasks.loop(hours=168)
async def weekly_update():
    global weekly_token_earnings
    weekly_token_earnings = {}

@tasks.loop(minutes=60)
async def decay_tokens():
    for user_id, last_active in list(user_last_active.items()):
        if datetime.now() - last_active > timedelta(hours=1):
            if user_id in token_balances and token_balances[user_id] > 10:
                token_balances[user_id] -= 10

@tasks.loop(hours=24)
async def pay_dividends():
    for owner, stocks in user_stocks.items():
        for user_id, shares in stocks.items():
            total_shares = sum(user_stocks.get(user_id, {}).values()) if user_id in user_stocks else 0
            if total_shares > 0 and user_id in token_balances:
                dividend = (0.02 * token_balances[user_id]) * (shares / total_shares)
                token_balances[owner] += dividend

@tasks.loop(hours=72)
async def market_event():
    event_type = random.choice(['bull', 'bear'])
    change_factor = random.uniform(0.1, 0.2)
    for user_id in token_balances:
        if event_type == 'bull':
            token_balances[user_id] *= (1 + change_factor)
        else:
            token_balances[user_id] *= (1 - change_factor)
        token_balances[user_id] = max(100, token_balances[user_id])

@tasks.loop(hours=720)  # Once a month
async def monthly_lottery():
    winner_id = random.choice(list(token_balances.keys()))
    token_balances[winner_id] += LOTTERY_PRIZE
    channel = bot.get_channel(CHANNEL_ID)  # Replace CHANNEL_ID with the ID of the economy channel
    await channel.send(f"🎉 Congratulations to <@{winner_id}> for winning the monthly lottery and receiving {LOTTERY_PRIZE} tokens! 🎉")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)
    tokens_awarded = len(message.content) * 0.1
    token_balances.setdefault(user_id, STARTING_TOKENS)
    token_balances[user_id] += tokens_awarded
    weekly_token_earnings.setdefault(user_id, 0)
    weekly_token_earnings[user_id] += tokens_awarded
    user_last_active[user_id] = datetime.now()

    await message.channel.send(f"You've earned {tokens_awarded} tokens! Total balance: {token_balances[user_id]}")

@slash_command(name="gamble", description="Gamble your tokens on odd or even dice rolls.")
async def gamble(ctx, bet_type: Option(str, "Choose bet type", choices=["odd", "even"]), amount: Option(int, "Enter the amount to bet", min_value=1)):
    user_id = str(ctx.author.id)
    current_balance = token_balances.get(user_id, STARTING_TOKENS)
    if amount > current_balance:
        await ctx.respond("You do not have enough tokens to make this bet.", ephemeral=True)
        return

    dice_roll = random.randint(1, 6)
    dice_result = "odd" if dice_roll % 2 != 0 else "even"
    if bet_type == dice_result:
        token_balances[user_id] += amount
        await ctx.respond(f"You won! The dice rolled {dice_roll} ({dice_result}). Your new balance is {token_balances[user_id]}.", ephemeral=True)
    else:
        token_balances[user_id] -= amount
        await ctx.respond(f"You lost! The dice rolled {dice_roll} ({dice_result}). Your new balance is {token_balances[user_id]}.", ephemeral=True)

@slash_command(name="bet_on_user", description="Bet on a user to earn the most tokens this week.")
async def bet_on_user(ctx, user: discord.User, amount: int):
    bettor_id = str(ctx.author.id)
    target_id = str(user.id)
    if bettor_id in token_balances and token_balances[bettor_id] >= amount:
        token_balances[bettor_id] -= amount
        active_bets[bettor_id] = {'target': target_id, 'amount': amount, 'time': datetime.now() + timedelta(days=7)}
        await ctx.respond(f"Betting {amount} tokens on {user.display_name}.", ephemeral=True)
    else:
        await ctx.respond("You do not have enough tokens to place this bet.", ephemeral=True)

@slash_command(name="balance", description="Show your current balance.")
async def balance(ctx):
    user_id = str(ctx.author.id)
    balance = token_balances.get(user_id, STARTING_TOKENS)
    await ctx.respond(f"Your current balance is {balance} tokens.", ephemeral=True)

@slash_command(name="stock_prices", description="Show the top users and their token balances (stock prices).")
async def stock_prices(ctx):
    sorted_users = sorted(token_balances.items(), key=lambda item: item[1], reverse=True)[:10]
    message = "Top Stock Prices:\n"
    for idx, (user_id, balance) in enumerate(sorted_users, 1):
        user = bot.get_user(int(user_id))
        if user:
            message += f"{idx}. {user.display_name}: {balance} tokens\n"
        else:
            message += f"{idx}. Unknown User: {balance} tokens\n"
    await ctx.respond(message, ephemeral=True)

@slash_command(name="steal", description="Attempt to steal tokens from another user.")
async def steal(ctx, target: discord.User):
    thief_id = str(ctx.author.id)
    target_id = str(target.id)
    if target_id not in token_balances:
        await ctx.respond("The target has no tokens to steal!", ephemeral=True)
        return

    success_rate = 0.1  # 10% chance of success
    if random.random() < success_rate:
        stolen_amount = random.randint(1, token_balances[target_id])
        token_balances[thief_id] += stolen_amount
        token_balances[target_id] -= stolen_amount
        await ctx.respond(f"You successfully stole {stolen_amount} tokens from {target.display_name}!", ephemeral=True)
    else:
        await ctx.respond("You failed to steal any tokens!", ephemeral=True)

@slash_command(name="tokenhelp", description="Show all available commands.")
async def tokenhelp(ctx):
    embed = discord.Embed(title="Command List", description="Here are all the available commands:")
    for command in bot.commands:
        embed.add_field(name=command.name, value=command.description, inline=False)
    await ctx.send(embed=embed)

# Replace 'your_token_here' with your bot's token
bot.run('your_token_here')
