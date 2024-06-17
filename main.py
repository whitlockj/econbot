import nextcord
from nextcord import SelectOption, Interaction, ButtonStyle, Embed, ui
from nextcord.ext import commands, tasks
from nextcord.ui import View, Button, Select # Import View and Button for interaction components
import math
import matplotlib.pyplot as plt
import io
from datetime import datetime
import random
import asyncio
import time
import logging
import aiohttp
import fakestories
import shopping_system  # Assuming this is correctly using nextcord in its implementation
from itertools import cycle
import json
import os
from randomfeatures import feature_concepts
from custom_classes import DatabaseTable, ListWithTTL


# Configure intents
intents = nextcord.Intents.default()
intents.messages = True  # If you need to read message content
intents.message_content = True  # Only necessary for commands that explicitly require the content of messages
intents.guilds = True
intents.members = True  # If you need member-related data, such as seeing member joins, updates, etc.

# Initialize the bot with these intents
bot = commands.Bot(command_prefix='/', intents=intents)


############# Define global variables #############


last_active_time = {}
token_gains = {}
active_bets = {}
minute_message_tracker = {}
user_reacted_messages = {}
last_message_time = time.time()  # Initialize last_message_time
work_command_count = {}
traders_with_gains = {}  # This will be a dictionary where the key is the user ID and the value is the gain/loss
user_tokens = {}
user_cooldowns = {}  # This should be your actual dictionary of user cooldowns for stealing


############# Random colors for User Names #############
COLORS = [nextcord.Color.green(), nextcord.Color.blue(), nextcord.Color.orange(), nextcord.Color.gold()]


############# Constants #############
trade_count = 0
last_claim_time = 0
claim_pot = 10
total_message_count = 0  # Initialize total_message_count
daily_message_count = 0  # Initialize daily_message_count
DAILY_REWARD = 20 # Daily reward for the most active user
lottery_pot = 0  # Initialize the lottery pot



############# Mis Role IDs #############
RAINBOWS_ROLE_ID = 1232180510227169410  # Role ID that changes color
#BIRTHDAY_ROLE_ID = 1232180510227169410  # Role ID for birthday role
HALLUCINATIONS_ROLE_ID = 1236948886157787177 # Role ID for hallucinations
DELUSIONS_ROLE_ID = 1236949060418539581 # Role ID for delusions
PARANOIA_ROLE_ID = 1236949576951529603 # Role ID for paranoia
INCOHERENT_SPEAKING_ROLE_ID = 1236949347136966697   # Role ID for incoherent speaking
NEGATIVE_SYMPTOMS_ROLE_ID = 1236949236088569886 # Role ID for negative symptoms


############# Guild ID #############
GUILD_ID = 1229582044187852913  # Replace with your guild


############# Mis Channel IDs #############
news = 1229582044187852916  # ECONOMY NEWS Channel ID and for General Reports. This channel ID is for "General chat" in the server
daily_token_gain = 1229682309699993620  # Daily announcement token gain channel
approv_announcement_chan = 1232195381341978694  # Mod Channel
announcement_chan = 1232195437205782528  # Announcement Channel
ALERT_CHANNEL_ID = 1236947951759261736

############# Recession Constants and Features #############


RECESSION_END_TIMEFRAME = 14400  # Timeframe in seconds in which the required messages must be sent to end a recession
RECESSION_END_REQ_MESSAGES = 10  # Number of messages needed to end a recession
RECESSION_TRIGGER_TIMEFRAME = 14400 # Timeframe in seconds in which the required messages must be sent to prevent triggering a recession
RECESSION_TRIGGER_REQ_MESSAGES = 10 # Number of messages needed to trigger a recession
RECESSION_PUNISHMENT_MULTIPLIER = 0.1  # Rate of token decrease during recession, where 1 means 100% of tokens are lost
RECESSION_PUNISHMENT_FREQUENCY = 7200 # How often the punishment is applied
RECESSION_COOLDOWN_TIMER = 7200  # Time in seconds before a recession can be triggered after starup
RECESSION_CHAN = news

bot_in_recession = False
_RECESSION_immune_timer = RECESSION_COOLDOWN_TIMER + time.time()
total_message_count = 0
last_token_deduction_time = 0

message_list: list[nextcord.Message] = ListWithTTL(default_ttl=RECESSION_TRIGGER_TIMEFRAME)
recession_message_list: list[nextcord.Message] = []

############# Stealing Features #############
steal_percentage = .2  # Percentage of tokens to steal
steal_chance = .3  # Chance of successful steal
lost_percentage = 0.1  # Percentage of tokens lost by the stealer if the steal fails
JAIL_ROLE = 1230522342480937084  # Jail role ID
JAIL_CHAN = 1230521150455414897  # Jail channel ID
jail_time = 60  # Time in seconds for jail


############# Gambling Features #############
WIN_MULTIPLIER_COIN_FLIP = 2
LOSE_MULTIPLIER_COIN_FLIP = 1
WIN_MULTIPLIER_ROULETTE = 3
LOSE_MULTIPLIER_ROULETTE = 1
WIN_MULTIPLIER_HIGHER_LOWER = 2
LOSE_MULTIPLIER_HIGHER_LOWER = 1
WIN_MULTIPLIER_ODD_EVEN = 2
LOSE_MULTIPLIER_ODD_EVEN = 1


# Set up basic logging configuration
logging.basicConfig(level=logging.INFO)

@tasks.loop(hours=24)
async def reset_daily_counters():
    global trade_count, traders_with_gains
    trade_count = 0  # Reset trade count every day
    traders_with_gains.clear()  # Reset traders' gains every da
    

@bot.event
async def on_ready():
    global user_balances, user_tickets, stock_prices, price_histories, user_stocks
    user_balances = DatabaseTable(loop=bot.loop, db_table="user_balances", schema=("user_id", int, {"balance": int}))
    user_tickets = DatabaseTable(loop=bot.loop, db_table="user_tickets", schema=("user_id", int, {"ticket_count": int}))
    stock_prices = DatabaseTable(loop=bot.loop, db_table="stock_prices", schema=("user_id", int, {"price": int}))
    price_histories = DatabaseTable(loop=bot.loop, db_table="price_histories", schema=("user_id", int, {"history": list}))
    user_stocks = DatabaseTable(loop=bot.loop, db_table="user_stocks", schema=("user_id", int, {"stocks": dict}))

    print(f'Logged in as {bot.user.name}')
    daily_token_gainers.start()
    change_rainbows_role_color.start()  # Start the role color change loop
    print("Role color change loop started.")
    bot.loop.create_task(handle_recession())  # Start the recession check task
    economic_report_task.start()  # Start the economic report task
    reset_daily_counters.start()  # Start the reset counters task
    award_most_active_user.start()
    channel = bot.get_channel(STATUS_CHANNEL_ID)
    embed = nextcord.Embed(title="Role Selection", description="Click a button to get the corresponding role.", color=nextcord.Color.blue())
    view = RoleSelectView()
    await channel.send(embed=embed, view=view)
    print("All scheduled tasks started.")




# Helper function to append the help command note to messages
def append_help_note(message):
    help_note = "\n\nℹ️ Need help with the economy bot? Use the /econhelp slash command for more information."
    return message + help_note


@bot.slash_command(guild_ids=[GUILD_ID],
                   description="Get information about the economy commands")
async def econhelp(interaction: nextcord.Interaction):
    help_message = ("\n"
                    "This bot manages a virtual economy within the nextcord server. It allows users to earn tokens, buy and sell stocks of other users to try and make more tokens, and engage in economic simulations that include market fluctuations and recessions. You get 1 token per message and 1 token per reaction to a message as the most basic way to get tokens other than gambling, trading, etc\n"
                    "\n"
                    "**Complete Commands List:**\n"
                    "- `/work`: Earn tokens and help end recessions. Your activity boosts the server's economy.\n"
                    "- `/gambling`: Play your luck with 4 different games for different prizes of tokens!\n"
                    "- `/stock_price <user>`: Displays the current stock price of a specified user along with a historical graph.\n"
                    "- `/stock_buy <user> <amount>`: Buy stocks of a user.\n"
                    "- `/stock_sell <user> <amount>`: Sell stocks of a user you own.\n"
                    "- `/stock`: View all stocks you own.\n"
                    "- `/leader`: See the top 5 token holders in the server.\n"
                    "- `/balance`: Check your current token balance.\n"
                    "- `/store`: Browse and purchase items from the store.\n"
                    "- `/steal <user>`: Attempt to steal 20% of someone's tokens. There's an 70% chance of losing 10% of yours giving it to them and going to jail for 1 minute.\n"
                    "- `/claim`: Claim a pot of 10 tokens once a day. Only one user can claim the pot in a 24-hour period.\n"
                    "- `/name_change <name>`: Change your nickname (Can only see this when you buy it from the store).\n"
                    "- `/announcement <message>`: Create an announcement (Can only see this when you buy it from the store).\n"
                    "- `/tip <user> <tokens> <message>`: Tip another user with tokens.\n"
                    "- `/recession`: Get information about the current economic state.\n"
                    "\n")

    help_message_part2 = """
**Economic Mechanics:**
**How do recessions work?**
The server enters a recession if there's a lull in activity. During a recession, all token gains are halted, and you lose 10% of your tokens every so often. The recession can end with sufficient activity and 1 separate person using the `/work` command.

**How do stocks work?**
- **Stock Pricing:** Each user has a stock price that is influenced by token balance.
- **Buying and Selling Stocks:** Invest in other users by buying their stocks and sell them at the market price for a profit... Or experience a loss ;)
- **Market Fluctuations:** Stock prices update regularly based on user activities and can fluctuate significantly during recessions or periods of high activity.

**Additional Features:**
- **Lottery System:** Play the lottery! Buy tickets and see if you win. Tickets add up in a pool and are worth 10 tokens each. When enough tickets are in the pool, a draw is triggered. The more tickets you have the higher chance of wining.
- **Store:** The store has items you can buy with your tokens! Take a look!
- **Tip System:** Use the `/tip` command to tip other users with a message.
- **Stealing Mechanism:** Use the `/steal` command to attempt to steal 30% of someone's tokens.
- **Nickname Changing:** Use the `/name_change` command to change your nickname after purchasing it from the store.
- **Announcement Creation:** Use the `/announcement` command to create an announcement after purchasing it from the store.

**Tips:**
- Natueral Gains: You get 1 token per message and 1 token per reaction to a message as the most basic way to get tokens other than gambling, trading, etc
- Stay active to boost the economy and prevent recessions.
- To end a recession, 1 person must use this command (/work) and a total of 5 messages messages need to be sent.
- Monitor stock prices and market trends to make informed investment decisions.
- Explore the store (`/store`) for exciting items and boosts to enhance your experience.

Thank you and I hope you enjoy our custom bot! -OverratedAardvark

For further assistance or if you encounter any issues, please reach out to the server owners.
"""

    # Create embeds for both help message parts using nextcord
    embed1 = nextcord.Embed(title="🤖 Help & Information - ScizoEcon Bot 🤖", description=help_message, color=nextcord.Color.blue())
    embed2 = nextcord.Embed(title="🤖 Help & Information - ScizoEcon Bot 🤖", description=help_message_part2, color=nextcord.Color.blue())

    # Send both embeds in the response to the interaction
    await interaction.response.send_message(embeds=[embed1, embed2], ephemeral=True)


########################################################################################################################
##############  MIS GAIN TRIGGERS AND FUNTIONS  ########################################################################
########################################################################################################################



@tasks.loop(hours=24)
async def daily_token_gainers():
    # Fetch the top 5 users with the highest token balances
    top_users: dict[int, int] = {k:v["balance"] for k, v in sorted(user_balances.items(), key=lambda item: item["balance"], reverse=True)}[:5]

    # Fetch the top 5 users who have sent the most messages since the last message
    if minute_message_tracker:  # Check if minute_message_tracker is not empty
        most_active_users = sorted(minute_message_tracker.items(), key=lambda x: x[1], reverse=True)[:5]
    else:
        most_active_users = []

    # Fetch the top 5 users who have gained the most tokens
    top_token_gainers = sorted(token_gains.items(), key=lambda x: x[1], reverse=True)[:5]

    # Create an embed message
    embed = nextcord.Embed(title="🏆 Top Users 🏆", color=nextcord.Color.gold())

    # Add the richest users to the embed
    richest_users_text = "\n".join(
        [f"💰 {await get_username(user_id)}: {balance} tokens" for user_id, balance in top_users])
    embed.add_field(name="Richest Users", value=richest_users_text or "None", inline=False)

    # Add the most active users to the embed
    most_active_users_text = "\n".join(
        [f"📨 {await get_username(user_id)}: {messages} messages" for user_id, messages in most_active_users])
    embed.add_field(name="Most Active Users", value=most_active_users_text or "None", inline=False)

    # Add the top token gainers to the embed
    top_gainers_text = "\n".join(
        [f"🚀 {await get_username(user_id)}: {gain} tokens gained" for user_id, gain in top_token_gainers])
    embed.add_field(name="Top Token Gainers", value=top_gainers_text or "None", inline=False)

    # Send the embed message to a specific channel
    channel = bot.get_channel(news)  # Replace 'news' with the ID of the channel where you want to send the message
    await channel.send(embed=embed)

    # Reset the message tracker for the next 5 minutes
    minute_message_tracker.clear()

    # Reset token_gains
    token_gains.clear()


async def get_username(user_id):
    user = await bot.fetch_user(user_id)
    return user.display_name


@tasks.loop(hours=24)
async def award_most_active_user():
    if not minute_message_tracker:  # If no messages have been sent, skip this iteration
        return

    # Find the user who has sent the most messages
    most_active_user_id = max(minute_message_tracker, key=minute_message_tracker.get)

    # Award the user with DAILY_REWARD tokens
    award_tokens = DAILY_REWARD
    user_balances[most_active_user_id]["balance"] += award_tokens

    # Update token gains
    token_gains[most_active_user_id] = token_gains.get(most_active_user_id, 0) + award_tokens

    # Logging the token gain
    logging.info(f"{most_active_user_id} gains {award_tokens} tokens for being the most active user.")

    # Fetch the user
    most_active_user = await bot.fetch_user(most_active_user_id)

    # Print the username and the new balance
    print(f"User {most_active_user.name} was awarded. New balance: {user_balances[most_active_user_id]["balance"]}")

    # Reset the message tracker for the next day
    minute_message_tracker.clear()

@bot.listen()
async def on_raw_reaction_add(payload: nextcord.RawReactionActionEvent):
    # Check if the reaction is from the bot itself
    if payload.user_id != bot.user.id:
        # Fetch the message
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Check if the user who reacted is not the author of the message
        if payload.user_id != message.author.id:
            # Check if the user has already reacted to this message
            if payload.message_id in user_reacted_messages.get(payload.user_id, set()):
                return  # If they have, don't give them a token

            # If they haven't, give them a token and record that they've reacted to this message
            user_balances[payload.user_id]["balance"] += 1
            token_gains[payload.user_id] = token_gains.get(payload.user_id, 0) + 1  # Update token gains
            user_reacted_messages.setdefault(payload.user_id, set()).add(payload.message_id)
            logging.info(f"{payload.user_id} gains 1 token from reacting to a message.")

@bot.listen()
async def on_raw_reaction_remove(payload: nextcord.RawReactionActionEvent):
    # Check if the reaction is from the bot itself
    if payload.user_id != bot.user.id:
        # Fetch the message
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Check if the user who unreacted is not the author of the message
        if payload.user_id != message.author.id:
            # Check if the user has already reacted to this message
            if payload.message_id in user_reacted_messages.get(payload.user_id, set()):
                # If they have, remove a token and remove the message from their reacted messages
                user_balances[payload.user_id]["balance"] -= 1
                token_gains[payload.user_id] = token_gains.get(payload.user_id, 0) - 1  # Update token gains
                user_reacted_messages[payload.user_id].remove(payload.message_id)
                logging.info(f"{payload.user_id} loses 1 token from unreacting to a message.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, I can't find that command. Try `/econhelp` for a list of available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("It looks like you missed some required arguments.")
    else:
        await ctx.send("Oops! Something went wrong. Please try again.")
        logging.error(f"Error from {ctx.author}: {error}")

########################################################################################################################
##################  RECESSION CHECK AND FUNCTION  ######################################################################
########################################################################################################################


@tasks.loop(seconds=5)
async def handle_recession(): # Responsible for starting a recession and handling the punishment, on_message is responsible for ending it
    global bot_in_recession, message_list, recession_message_list

    if _RECESSION_immune_timer < time.time():
        return
        
    if (len(message_list) <= RECESSION_TRIGGER_REQ_MESSAGES) and (not apply_recession_punishment.is_running()):
        bot_in_recession = True
        apply_recession_punishment.start()
        
        message_list = ListWithTTL(default_ttl=RECESSION_TRIGGER_TIMEFRAME)
        recession_message_list = []

        channel = bot.get_channel(RECESSION_CHAN)
        embed = nextcord.Embed(title="📉 Economy in Recession 📉", description=f"The server has entered a recession due to inactivity. {RECESSION_END_REQ_MESSAGES} messages must be sent within a 2 hour timeframe in order to exit the Recession. Starting in {RECESSION_END_TIMEFRAME / 3600} hours, every {RECESSION_PUNISHMENT_FREQUENCY / 3600} hours {RECESSION_PUNISHMENT_MULTIPLIER*10}% of tokens will be lost.", color=nextcord.Color.red())
        await channel.send(embed=embed)
        print("Recession started and the message list has been wiped.")

@bot.listen()
async def on_message(message: nextcord.Message):
    global bot_in_recession, message_list, total_message_count, recession_message_list

    if message.author.bot or message.guild is None:
        return

    message_list.append(message)

    total_message_count += 1
    
    if bot_in_recession:
        recession_message_list.append(message)
        
        if len(message_list) >= RECESSION_END_REQ_MESSAGES: #  Check if the recession has ended due to sufficient message activity
            bot_in_recession = False
            recession_message_list = []

        if not bot_in_recession:
            apply_recession_punishment.stop()
            user_balances[message.author.id]["balance"] += 1
            channel = bot.get_channel(RECESSION_CHAN)
            embed = nextcord.Embed(title="🚀💰 End of Recession 💰🚀",
                                description="The server has exited the recession. Token gains are reinstated.",
                                color=nextcord.Color.green())
            await channel.send(embed=embed)
            print("Recession ended due to sufficient message activity.")
    else:
        user_balances[message.author.id]["balance"] += 1
                

@tasks.loop(seconds=RECESSION_PUNISHMENT_FREQUENCY)
async def apply_recession_punishment():
    global user_balances, last_token_deduction_time
    for user_id, balance in user_balances.items():
        user_balances[user_id]["balance"] = max(int(balance["balance"] - int(balance["balance"] * RECESSION_PUNISHMENT_MULTIPLIER)), 1)
    


@bot.slash_command(guild_ids=[GUILD_ID], description="Get information about the current economic state")  # type: ignore
async def recession(interaction: nextcord.Interaction):
    global bot_in_recession, last_token_deduction_time


    if bot_in_recession:
        messages_needed = RECESSION_END_REQ_MESSAGES - len(recession_message_list)
        time_till_next_deduction = max(0, RECESSION_PUNISHMENT_FREQUENCY - time.time() - last_token_deduction_time)  # Time in seconds
        recession_info = (f"📉 We are currently in a recession.\n"
                          f"📬 {messages_needed} more messages need to be sent to end the recession.\n"
                          f"⏰ The next token deduction will happen in {time_till_next_deduction} seconds.")
    else:
        s = RECESSION_TRIGGER_TIMEFRAME
        hours = s // 3600
        s = s - (hours * 3600)
        minutes = s // 60
        seconds = s - (minutes * 60)
        recession_info = (f"📈 We are not currently in a recession.\n"
                          f"⏳ {len(recession_message_list)} have been sent in the last {int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds, if this number goes below {RECESSION_TRIGGER_REQ_MESSAGES}, a recession will start.")

    embed = nextcord.Embed(title="🏦 Economic State", description=recession_info, color=nextcord.Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)


########################################################################################################################
##################  STOCK FUNCTIONS  ###################################################################################
########################################################################################################################


def update_stock_price(user_id: int):
    balance = user_balances[user_id].get("balance", 100)

    # Define the price calculation logic based on balance thresholds
    if balance < 1000:
        new_price = max(1, math.ceil(0.1 * balance))  # Ensure stock price doesn't fall below 1
    elif balance < 5000:
        new_price = max(1, math.ceil(0.05 * balance))
    else:
        new_price = max(1, math.ceil(0.02 * balance))

    # Update the stock price
    stock_prices[user_id]["price"] = new_price

    # Record the price change in the history
    now = datetime.now()
    
    price_histories[user_id]["history"].append((now, new_price))

    # Debug print to check the updated stock price
    print(f"Stock price for user {user_id} updated to {new_price}.")


def plot_stock_history(prices, max_points=500):
    # Plot for the last 30 days
    if len(prices) > max_points:
        prices_30 = prices[-max_points:]
    else:
        prices_30 = prices

    times_30 = [price[0] for price in prices_30]
    values_30 = [price[1] for price in prices_30]
    plt.figure(figsize=(10, 5))
    plt.plot(times_30, values_30, marker='o', linestyle='-', color='blue')
    plt.title('Stock Price History Over the Last 30 Days')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer_30 = io.BytesIO()
    plt.savefig(buffer_30, format='png')
    buffer_30.seek(0)
    plt.close()

    # Plot for the last 7 days
    if len(prices) > 7 * 24:  # Assuming hourly data for simplicity
        prices_7 = prices[-7 * 24:]
    else:
        prices_7 = prices

    times_7 = [price[0] for price in prices_7]
    values_7 = [price[1] for price in prices_7]
    plt.figure(figsize=(10, 5))
    plt.plot(times_7, values_7, marker='o', linestyle='-', color='red')
    plt.title('Stock Price History Over the Last 7 Days')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer_7 = io.BytesIO()
    plt.savefig(buffer_7, format='png')
    buffer_7.seek(0)
    plt.close()

    return buffer_30, buffer_7


@bot.slash_command(guild_ids=[GUILD_ID], description="Display the stock price of a user with history graph")
async def stock_price(interaction: nextcord.Interaction, user: nextcord.User):
    # Defer the interaction to give time for processing (especially since you might generate images)
    await interaction.response.defer(ephemeral=True)

    # Update the stock price to ensure it's current
    update_stock_price(user.id)

    # Fetch the updated stock price
    if stock_prices[user.id]["price"] == 0:
        price = 0.1 * user_balances[user.id].get("balance", 100)
    else:
        price = stock_prices[user.id]["price"]
    price_message = f"The current stock price of {user.display_name} is {price:.2f} tokens."
    price_history = price_histories[user.id]["history"]

    # Check if there's a price history to display
    if price_history:
        graph_30, graph_7 = plot_stock_history(price_history)
        if graph_30 and graph_7:
            with io.BytesIO() as image_binary_30, io.BytesIO() as image_binary_7:
                image_binary_30.write(graph_30.getbuffer())
                image_binary_7.write(graph_7.getbuffer())
                image_binary_30.seek(0)
                image_binary_7.seek(0)
                files = [nextcord.File(image_binary_30, '30_day_stock_history.png'),
                         nextcord.File(image_binary_7, '7_day_stock_history.png')]
                embed = nextcord.Embed(title="Stock Price and History", description=price_message,
                                       color=nextcord.Color.blue())
                embed.set_image(url="attachment://30_day_stock_history.png")
                await interaction.followup.send(embed=embed, files=files)
        else:
            embed = nextcord.Embed(title="Stock Price", description=price_message, color=nextcord.Color.blue())
            await interaction.followup.send(embed=embed)
    else:
        embed = nextcord.Embed(title="Stock Price", description=price_message, color=nextcord.Color.blue())
        await interaction.followup.send(embed=embed)


@bot.slash_command(guild_ids=[GUILD_ID], description="Buy stock of a user")
async def stock_buy(interaction: nextcord.Interaction, user: nextcord.User, amount: int):
    global trade_count
    await interaction.response.defer(ephemeral=True)

    buyer_id = interaction.user.id
    seller_id = user.id

    # Ensure both buyer and seller are initialized in the balance system
    if buyer_id not in user_balances:
        user_balances[buyer_id]["balance"] = 100  # Assuming a default start balance
    if seller_id not in user_balances:
        user_balances[seller_id]["balance"] = 100  # Assuming a default start balance

    # Fetch the buyer's current balance
    buyer_balance = user_balances[buyer_id]["balance"]

    # Fetch the current stock price of the user whose stock is being bought

    if stock_prices[seller_id]["price"] == 0:
        stock_price_of_user = 0.1 * user_balances[seller_id]["balance"]
    else:
        stock_price_of_user = stock_prices[seller_id]["price"]

    # Calculate the total cost of the transaction
    total_cost = stock_price_of_user * amount

    # Check if the buyer has sufficient funds
    if buyer_balance < total_cost:
        await interaction.followup.send("Insufficient funds to complete this transaction.", ephemeral=True)
        return

    # Update the buyer's balance after the purchase
    buyer_balance -= total_cost
    user_balances[buyer_id]["balance"] = buyer_balance
    print(f"New balance after purchase for user {buyer_id}: {user_balances[buyer_id]["balance"]}")
    update_stock_price(buyer_id)

    # Update the seller's stock price
    update_stock_price(seller_id)

    # Update the buyer's stock ownership
    
    if seller_id not in user_stocks[buyer_id]["stocks"]:
        user_stocks[buyer_id]["stocks"][seller_id] = {'amount': 0, 'purchase_price': stock_price_of_user}


    user_stocks[buyer_id]["stocks"][seller_id]['amount'] += amount
    trade_count += 1

    await interaction.followup.send(
        f"You've successfully bought {amount} stocks of {user.display_name} at {stock_price_of_user:.2f} tokens each!",
        ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Sell stock of a user")
async def stock_sell(interaction: nextcord.Interaction, user: nextcord.User, amount: int):
    global trade_count, traders_with_gains, token_gains
    await interaction.response.defer(ephemeral=True)

    stock_to_sell = user_stocks[interaction.user.id]["stocks"].get(user.id, None)
    if stock_to_sell is None or stock_to_sell['amount'] < amount:
        await interaction.followup.send("You do not own enough stock to complete this sale.", ephemeral=True)
        return

    # Calculate the current stock price based on the seller's balance

    if stock_prices[user.id]["price"] == 0:
        current_stock_price = 0.1 * user_balances[user.id].get("balance", 100)
    else:
        current_stock_price = stock_prices[user.id]["price"]
        
    # Calculate total revenue from the sale
    total_revenue = current_stock_price * amount
    # Calculate the gain or loss
    purchase_price = stock_to_sell['purchase_price']
    total_cost = purchase_price * amount
    gain_loss = total_revenue - total_cost

    # Update the seller's balance
    seller_balance = user_balances[interaction.user.id]["balance"] + total_revenue
    user_balances[interaction.user.id]["balance"] = seller_balance

    # Update token gains
    token_gains[interaction.user.id] = token_gains.get(interaction.user.id, 0) + gain_loss

    # Update stock ownership details
    stock_to_sell['amount'] -= amount
    if stock_to_sell['amount'] == 0:
        del user_stocks[interaction.user.id]["stocks"][user.id]

    # Increment trade count
    trade_count += 1

    # Record this transaction in traders with gains if there was a gain
    if gain_loss > 0:
        traders_with_gains[interaction.user.id] = traders_with_gains.get(interaction.user.id, 0) + gain_loss

    # Prepare the response message with the transaction details
    result_message = f"You've sold {amount} stocks of {user.display_name} at {current_stock_price:.2f} tokens each. Total revenue: {total_revenue} tokens. Gain/Loss from this transaction: {gain_loss} tokens."
    await interaction.followup.send(result_message, ephemeral=True)

    # Logging the transaction
    logging.info(f"User {interaction.user.id} sold stocks. Gain/Loss: {gain_loss} tokens.")

@bot.slash_command(guild_ids=[GUILD_ID], description="View all stocks owned")
async def stock(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    stocks_owned = user_stocks[interaction.user.id]["stocks"]
    if not stocks_owned:
        embed = nextcord.Embed(title="Stocks Owned", description="You do not own any stocks.",
                               color=nextcord.Color.blue())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    lines = []
    total_gain_loss = 0

    for user_id, stock_info in stocks_owned.items():
        amount = stock_info['amount']
        purchase_price = stock_info['purchase_price']
        current_price = stock_prices[user_id]["price"]
        total_purchase_price = purchase_price * amount
        total_current_value = current_price * amount
        gain_loss = total_current_value - total_purchase_price
        total_gain_loss += gain_loss

        gain_loss_str = f"+{gain_loss:.2f} tokens" if gain_loss >= 0 else f"{gain_loss:.2f} tokens"

        lines.append(
            f"You own {amount} shares of <@{user_id}> purchased at {purchase_price:.2f} tokens each (Current Value: {total_current_value:.2f} tokens, Gain/Loss: {gain_loss_str})")

    response = '\n'.join(lines)
    embed = nextcord.Embed(title="Stocks Owned", description=response, color=nextcord.Color.blue())
    total_gain_loss_str = f"Total Gain/Loss: {total_gain_loss:.2f} tokens"
    embed.set_footer(text=total_gain_loss_str)
    await interaction.followup.send(embed=embed, ephemeral=True)

########################################################################################################################
##################  LEADER AND BALACE ###################################################################################
########################################################################################################################

@bot.slash_command(guild_ids=[GUILD_ID], description="See the top 5 token holders")
async def leader(interaction: nextcord.Interaction):
    top_users: dict[int, int] = {k:v["balance"] for k, v in sorted(user_balances.items(), key=lambda item: item["balance"], reverse=True)}[:5]
    
    # Create an embed to send as a response
    embed = nextcord.Embed(
        title="🏆 Server's Wealthiest Tycoons 🏆",
        description="Here are the top 5 token holders in the server:",
        color=nextcord.Color.gold()
    )

    for user_id, balance in top_users:
        # Fetch the user
        user = await bot.fetch_user(user_id)
        embed.add_field(name=user.display_name, value=f"{balance} tokens", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="Check your token balance")
async def balance(interaction: nextcord.Interaction):
    user_id = interaction.user.id
    current_balance = user_balances[user_id]["balance"]  # Default to 100 if no balance exists
    embed = nextcord.Embed(
        title="Token Balance",  # Title of the embed
        description=f"💰 Your treasure chest contains **{current_balance} tokens**. 💰",  # Main text
        color=nextcord.Color.gold()  # Color of the embed sidebar
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

########################################################################################################################
##################  NAME CHANGE  ###################################################################################
########################################################################################################################

@bot.slash_command(guild_ids=[GUILD_ID], description="Change your nickname")
async def name_change(interaction: nextcord.Interaction, name: str):
    # ID of the group that has permission to use this command and from which users will be removed after using the command
    group_id = 1232169888911724544
    member = interaction.guild.get_member(interaction.user.id)

    # Check if the user is part of the group
    if any(role.id == group_id for role in member.roles):
        try:
            # Change the nickname
            await member.edit(nick=name)
            await interaction.response.send_message(f"Nickname changed to: {name}", ephemeral=False)

            # Get the role object by ID
            role_to_remove = interaction.guild.get_role(group_id)
            if role_to_remove:
                # Remove the role from the user
                await member.remove_roles(role_to_remove)
                await interaction.followup.send(f"You have been removed from the group after changing your nickname.",
                                                ephemeral=True)
            else:
                await interaction.followup.send("Failed to find the role to remove.", ephemeral=True)
        except nextcord.errors.Forbidden:
            await interaction.response.send_message("I don't have permission to change nicknames or remove roles.",
                                                    ephemeral=False)
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

########################################################################################################################
##################  ECON REPORT  ###################################################################################
########################################################################################################################


@tasks.loop(minutes=120)
async def economic_report_task():
    global trade_count, traders_with_gains, total_message_count

    # Calculate the total number of messages since the last report
    messages_since_last_report = total_message_count
    messages_report = f"A total of {messages_since_last_report} messages have been sent since the last report."

    # Calculate who sent the most messages
    if minute_message_tracker:
        most_active_user_id = max(minute_message_tracker, key=minute_message_tracker.get)
        most_messages_count = minute_message_tracker.get(most_active_user_id, 0)
        most_messages_user = await bot.fetch_user(most_active_user_id)
        most_messages_report = f"The most messages were sent by {most_messages_user.display_name} with {most_messages_count} messages."
    else:
        most_messages_report = "No messages have been sent since the last report."

    # Logging the report generation and message count
    logging.info(f"Report generated. Messages since last report: {messages_since_last_report}")

    # Generate the stock market update
    trade_report = f"A total of {trade_count} stock trades have been made since the last report."

    # Generate the economic report embed
    embed = nextcord.Embed(title="📰 PSYCHOSIS SUPPORT NEWS 10! 🎉",
                           description="In this saga of our flourishing economy:", color=nextcord.Color.gold())
    embed.add_field(name="This just in!", value=messages_report, inline=False)
    embed.add_field(name="Most Active User", value=most_messages_report, inline=False)
    embed.add_field(name="Stock Market Update", value=trade_report, inline=False)

    # Pick a random feature from feature_concepts and add it to the store section
    random_feature = random.choice(feature_concepts)
    embed.add_field(name="🛒 Explore the Bot 🛍️",
                    value=f"{random_feature}",
                    inline=False)

    # Include a fake news story or additional context
    random_story = random.choice(fakestories.fake_news_stories)
    embed.add_field(name="Breaking News! 📰", value=random_story, inline=False)

    # Determine the economic state message based on the recession state
    if not bot_in_recession:
        economic_saga = "**Prosperity Prevails 🌟**"
        economic_saga_description = "In the radiant glow of economic prosperity, our domain stands strong! We're not in a recession, rejoice!"
    else:
        economic_saga = "**The Gloom of Recession 📉**"
        economic_saga_description = "In the shroud of uncertainty, our realm stands resolute! Only you can get the server back on track!"
    embed.add_field(name=economic_saga, value=economic_saga_description, inline=False)

    # Select a random user as the 'messenger' for this report
    random_member = random.choice(list(bot.get_all_members()))
    tag_message = f"Unveiled by the illustrious {random_member.display_name}, whose valor resonates throughout the hallowed halls of legend."
    embed.set_footer(text=tag_message)

    # Send the report to a specific channel
    channel_id = news
    channel = bot.get_channel(news)

    # Retrieve and send the GIF
    gif_url = "https://c.tenor.com/jLT65PQ1OCQAAAAd/tenor.gif"
    async with aiohttp.ClientSession() as session:
        async with session.get(gif_url) as resp:
            if resp.status == 200:
                gif_bytes = await resp.read()

                # Set the GIF as the image in the embed
                embed.set_image(url="attachment://cat_vibing.gif")

                # Send the embed with the GIF as an attachment
                await channel.send(embed=embed, file=nextcord.File(io.BytesIO(gif_bytes), "cat_vibing.gif"))

    # Reset the message tracker and counters after the report uses the data
    minute_message_tracker.clear()
    trade_count = 0
    traders_with_gains.clear()
    total_message_count = 0  # Reset total message count after including it in the report
    logging.info("Counters reset after report.")

########################################################################################################################
##################  STORE  ###################################################################################
########################################################################################################################


@bot.slash_command(guild_ids=[GUILD_ID], description="Embark on a grand quest to acquire treasures!")
async def store(interaction: nextcord.Interaction):
    # Pass interaction.client to show_shop_items
    await shopping_system.show_shop_items(interaction, lottery_pot, user_balances, user_tickets, interaction.client)


@bot.event
async def on_component(interaction: nextcord.Interaction):
    # Check for the type of component interacted with, here it's likely a button or select menu
    if interaction.type == nextcord.InteractionType.component:
        if interaction.custom_id == 'name_color_choice':
            # Assuming 'change_name_color' function exists and is properly set to handle nextcord interactions
            await change_name_color(interaction, interaction.user, interaction.data['values'][0])


class ApprovalView(View):
    def __init__(self, content, approval_channel_id, announcement_channel_id, user):
        super().__init__(timeout=180)  # Timeout for button response (in seconds)
        self.content = content
        self.approval_channel_id = approval_channel_id
        self.announcement_channel_id = announcement_channel_id
        self.user = user  # Pass the user who initiated the command
        self.approval_message = None  # Placeholder for the verification message

    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.green)
    async def confirm(self, button: Button, interaction: nextcord.Interaction):
        announcement_embed = nextcord.Embed(
            title="📣 Announcement 📣",
            description=self.content,
            color=0x00ff00  # Green color for the embed
        )
        announcement_embed.set_footer(
            text=f"Brought to you by the majestic magnificent and almighty {self.user.display_name}! Seriously they spent tokens on this, pretty cool of them right? :)")

        channel = bot.get_channel(self.announcement_channel_id)

        if channel:
            await channel.send(embed=announcement_embed)  # Send the announcement embed
            await interaction.response.edit_message(
                content="Announcement posted successfully!")  # Edit the original message to show success

            # Remove the Server Announcement role after the announcement is approved
            role = nextcord.utils.get(interaction.guild.roles, id=1232196345851412512)
            if role:
                try:
                    await self.user.remove_roles(role)
                    await self.user.send(
                        f"The {role.name} role has been removed from you. Your announcement was approved.")
                except Exception as e:
                    print(f"An error occurred while removing the role: {e}")
            else:
                print("Role not found.")  # For debugging purposes

            # Delete the verification message
            if self.approval_message:
                await self.approval_message.delete()
        else:
            await interaction.response.edit_message(
                content="Failed to find the announcement channel.")  # Edit the original message to show failure

    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.red)
    async def cancel(self, button: Button, interaction: nextcord.Interaction):
        await interaction.message.delete()  # Delete the original message
        # Send a cancellation message to the user
        if self.user:
            try:
                await self.user.send("Your announcement was canceled by a staff member.")
            except nextcord.HTTPException:
                print("Could not send a private message to the user.")

        # Delete the verification message
        if self.approval_message:
            await self.approval_message.delete()


@bot.slash_command(guild_ids=[GUILD_ID], description="Create an announcement (Admin Only)")
async def announcement(interaction: nextcord.Interaction, message: str):
    # Check if user has the Server Announcement role
    role = nextcord.utils.get(interaction.guild.roles, id=1232196345851412512)
    if role in interaction.user.roles:
        approval_channel_id = approv_announcement_chan  # Correct approval channel ID
        announcement_channel_id = announcement_chan
        view = ApprovalView(message, approval_channel_id, announcement_channel_id, interaction.user)
        approval_channel = bot.get_channel(approval_channel_id)
        if approval_channel:
            approval_embed = nextcord.Embed(
                title="📣 New Announcement Approval 📣",
                description=f"Approve this message for announcement? \"{message}\"",
                color=0xffa500  # Orange color for the embed
            )
            approval_embed.set_footer(text=f"Submitted by {interaction.user.display_name}")

            approval_message = await approval_channel.send(embed=approval_embed, view=view)
            view.approval_message = approval_message  # Store the verification message in the view
            await interaction.response.send_message("Your message has been sent for approval.", ephemeral=True)
        else:
            await interaction.response.send_message("Approval channel not found.", ephemeral=True)
    else:
        await interaction.response.send_message("You do not have the required role to use this command.",
                                                ephemeral=True)


color_cycle = cycle(COLORS)  # Create a cycle object from the colors list


@tasks.loop(minutes=1)
async def change_rainbows_role_color():
    guild = bot.get_guild(GUILD_ID)
    if guild:
        role = nextcord.utils.get(guild.roles, id=RAINBOWS_ROLE_ID)
        if role:
            new_color = next(color_cycle)  # Get the next color from the cycle
            try:
                await role.edit(color=new_color)  # Change the role's color
                print(f"Changed Rainbow Role color to {new_color}")
            except nextcord.Forbidden:
                print("I don't have permission to edit this role.")
            except nextcord.HTTPException as e:
                print(f"Failed to change role color due to HTTP error: {e}")
        else:
            print("Role not found.")
    else:
        print("Guild not found. Ensure the bot is in the guild with the specified ID.")

########################################################################################################################
##################  GIVE TOKENS  ###################################################################################
########################################################################################################################


@bot.slash_command(guild_ids=[GUILD_ID], description="Give a user a specified amount of tokens")
async def give_tokens(interaction: nextcord.Interaction, user: nextcord.User, tokens: int):
    # Add the specified amount of tokens to the user's balance
    user_balances[user.id]["balance"] += tokens

    # Send a confirmation message
    await interaction.response.send_message(f"Successfully gave {tokens} tokens to {user.name}.", ephemeral=True)

########################################################################################################################
##################  STEALING  ###################################################################################
########################################################################################################################

@bot.slash_command(guild_ids=[GUILD_ID], description="Try and steal tokens from a user. If you fail you lose 10% and go to jail for 1 min")
async def steal(interaction: nextcord.Interaction, target: nextcord.User):
    stealer_id = interaction.user.id
    target_id = target.id
    original_channel = interaction.channel  # Define original_channel right here

    # Define the embed for attempting to steal
    attempt_embed = nextcord.Embed(title="🔒 Attempting to Steal",
                                   description=f"Attempting to steal tokens from {target.display_name}...",
                                   color=nextcord.Color.blurple())

    # Send the embed indicating the attempt to steal
    await interaction.response.send_message(embed=attempt_embed, ephemeral=True)

    # Pause for 2 seconds before continuing
    await asyncio.sleep(2)

    # Check if the user is on cooldown
    if stealer_id in user_cooldowns and user_cooldowns[stealer_id] > time.time():
        embed = nextcord.Embed(title="⏳ Cooldown Active",
                               description=f"{interaction.user.mention}, you can only use this command once every 24 hours. 🕒",
                               color=nextcord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Check if the target has enough tokens to steal
    if user_balances[target_id]["balance"] < 1:
        embed = nextcord.Embed(title="😔 Not Enough Tokens",
                               description=f"{interaction.user.mention}, {target.display_name} does not have enough tokens to steal. 🚫",
                               color=nextcord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Define embed_jail here
    embed_jail = nextcord.Embed(
        title="🏛️ Courtroom Verdict Announcement",
        description=(
            f"**Hearing of the Digital Tribunal of {interaction.guild.name}**\n\n"
            f"In the matter of the attempted theft (unlawful appropriation) of tokens,\n\n"
            f"**Accused:** {interaction.user.mention}\n"
            f"**Victim:** {target.display_name}\n\n"
            f"The digital tribunal, having duly considered the evidence, hereby finds the accused **Guilty**.\n\n"
            f"**Sentence:** Temporary confinement within the virtual detention facility for a duration of 1 minute. This sentence is to be served immediately. The accused is ordered to reflect on their actions during this period.\n\n"
            f"Let this serve as a deterrent to all members within this community. Justice has been upheld."
        ),
        color=nextcord.Color.red()
    )

    # Generate a random number for the 30% chance
    if random.random() < steal_chance:
        stolen_tokens = round(user_balances[target_id]["balance"] * steal_percentage)
        user_balances[target_id]["balance"] -= stolen_tokens
        user_balances[stealer_id]["balance"] += stolen_tokens
        embed_success = nextcord.Embed(title="🎉 Steal Successful",
                                       description=f"{interaction.user.mention}, you successfully stole {stolen_tokens} tokens from {target.display_name}!",
                                       color=nextcord.Color.green())
        await interaction.followup.send(embed=embed_success, ephemeral=True)
        await target.send(f"{interaction.user.display_name} has stolen {stolen_tokens} tokens from you. 🎊")
    else:
        lost_tokens = round(user_balances[stealer_id]["balance"] * lost_percentage)
        # Subtract lost tokens from the stealer's balance
        user_balances[stealer_id]["balance"] -= lost_tokens
        # Add lost tokens to the target's balance
        user_balances[target_id]["balance"] += lost_tokens

        role = interaction.guild.get_role(JAIL_ROLE)
        jail_channel = interaction.guild.get_channel(JAIL_CHAN)
        if role and jail_channel:
            await interaction.user.add_roles(role)
            # Set channel permissions for the jailed user and deny others
            await jail_channel.set_permissions(interaction.user, read_messages=True, send_messages=False)
            await jail_channel.set_permissions(interaction.guild.default_role, read_messages=False)

            # Attach the GIF
            gif_path = os.path.join(os.path.dirname(__file__), "steal.gif")
            embed_jail.set_image(url=f"attachment://steal.gif")

            # Send the embed with the GIF in the jail channel
            message = await jail_channel.send(embed=embed_jail, file=nextcord.File(gif_path))

            # Send the same embed with the GIF in the original channel
            await original_channel.send(embed=embed_jail, file=nextcord.File(gif_path))

            # Send the message only to the user who was attempted to be robbed
            await target.send("Someone attempted to steal tokens from you but failed. 😲")
            bot.loop.create_task(
                remove_role_after_delay(interaction.user, role, jail_time, interaction.guild, jail_channel,
                                        original_channel, message))
        else:
            embed_error = nextcord.Embed(title="⚠️ Error",
                                         description="Failed to assign the role or find the jail channel. ❗",
                                         color=nextcord.Color.red())
            await interaction.followup.send(embed=embed_error, ephemeral=True)

async def remove_role_after_delay(user, role, delay, guild, jail_channel, original_channel,
                                  message):  # Jail time remove role
    await asyncio.sleep(delay)
    await user.remove_roles(role)
    # Reset channel permissions
    await jail_channel.set_permissions(user, overwrite=None)
    await jail_channel.set_permissions(guild.default_role, overwrite=None)
    embed_release = nextcord.Embed(title="🔓 Jail Time Over",
                                   description=f"{user.mention} has been released from jail. Freedom! 🎉",
                                   color=nextcord.Color.green())
    await original_channel.send(embed=embed_release)  # Send the release message to the original channel

    # Delete all messages in the jail channel
    await jail_channel.purge()



@bot.slash_command(guild_ids=[GUILD_ID], description="Claim a pot of 10 tokens once a day")
async def claim(interaction: nextcord.Interaction):
    global last_claim_time, claim_pot, token_gains

    user_id = interaction.user.id
    # Check if 24 hours have passed since the last claim
    if time.time() - last_claim_time >= 24 * 60 * 60:
        # Give the user 10 tokens
        user_balances[user_id]["balance"] += claim_pot
        # Update token gains
        token_gains[user_id] = token_gains.get(user_id, 0) + claim_pot

        # Update the last claim time and reset the pot
        last_claim_time = time.time()
        claim_pot = 0

        # Create an embed to send as a response
        embed = nextcord.Embed(
            title="🎉 You've claimed the pot! 🎉",
            description=f"You now have {user_balances[user_id]['balance']} tokens. 💰",
            color=nextcord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"{interaction.user.display_name} claimed the daily pot of {claim_pot} tokens.")
    else:
        # Calculate remaining time until the pot can be claimed again
        hours_remaining = 24 - (time.time() - last_claim_time) / 60 / 60

        # Create an embed to send as a response
        embed = nextcord.Embed(
            title="🚫 The pot has already been claimed. 🚫",
            description=f"It will be available again in {hours_remaining:.2f} hours. ⏰",
            color=nextcord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GamblingView(nextcord.ui.View):
    def __init__(self, user_id, bet_amount):
        super().__init__()
        self.user_id = user_id
        self.bet_amount = bet_amount

    def create_result_embed(self, title, description, color=nextcord.Color.green()):
        embed = nextcord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=f"Bet Amount: {self.bet_amount} tokens")
        return embed

    async def check_balance(self, interaction):
        global user_balances
        user_balance = user_balances[self.user_id]["balance"]
        if user_balance < self.bet_amount:
            await interaction.response.send_message("You don't have enough tokens to place this bet!", ephemeral=True)
            return False
        return True

    @nextcord.ui.button(label="Coin Flip 🪙", style=nextcord.ButtonStyle.green)
    async def coin_flip(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        global user_balances, token_gains
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not the one gambling!", ephemeral=True)
            return

        if not await self.check_balance(interaction):
            return

        view = nextcord.ui.View()
        view.add_item(nextcord.ui.Button(label="Heads", style=nextcord.ButtonStyle.green, custom_id="heads"))
        view.add_item(nextcord.ui.Button(label="Tails", style=nextcord.ButtonStyle.green, custom_id="tails"))
        await interaction.response.send_message("🔮 Choose Heads or Tails:", view=view, ephemeral=True)

        def check(m):
            return m.user.id == self.user_id and m.data.get('custom_id') in ["heads", "tails"]

        try:
            choice_interaction = await bot.wait_for("interaction", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Timed out! Please try again.", ephemeral=True)
            return

        result = "Heads" if random.choice([True, False]) else "Tails"
        if choice_interaction.data['custom_id'] == result.lower():
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) + self.bet_amount * WIN_MULTIPLIER_COIN_FLIP
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) + self.bet_amount * WIN_MULTIPLIER_COIN_FLIP
            total_balance = user_balances[self.user_id]["balance"]
            embed = self.create_result_embed("🎉 Coin Flip Victory!",
                                             f"You won {self.bet_amount * WIN_MULTIPLIER_COIN_FLIP} tokens! The result was {result}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.green())
        else:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) - self.bet_amount * LOSE_MULTIPLIER_COIN_FLIP
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) - self.bet_amount * LOSE_MULTIPLIER_COIN_FLIP
            total_balance = user_balances[self.user_id]["balance"]
            embed = self.create_result_embed("👎 Coin Flip Loss",
                                             f"You lost {self.bet_amount * LOSE_MULTIPLIER_COIN_FLIP} tokens. The result was {result}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.red())
        await choice_interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="Roulette 🎰", style=nextcord.ButtonStyle.green)
    async def roulette(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        global user_balances, token_gains
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not the one gambling!", ephemeral=True)
            return

        if not await self.check_balance():
            return

        select = nextcord.ui.Select(placeholder="Choose a number range...",
                                    options=[
                                        nextcord.SelectOption(label="1-3", value="1-3"),
                                        nextcord.SelectOption(label="4-6", value="4-6"),
                                        nextcord.SelectOption(label="7-9", value="7-9"),
                                        nextcord.SelectOption(label="10-12", value="10-12"),
                                        nextcord.SelectOption(label="13-15", value="13-15")
                                    ])

        view = nextcord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("🔄 Spin the Roulette Wheel!", view=view, ephemeral=True)

        def check(m):
            return m.user.id == self.user_id and 'values' in m.data

        try:
            choice_interaction = await bot.wait_for("interaction", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Timed out! Please try again.", ephemeral=True)
            return

        chosen_range = choice_interaction.data['values'][0]
        low, high = map(int, chosen_range.split('-'))
        result = random.randint(1, 15)
        if low <= result <= high:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) + self.bet_amount * WIN_MULTIPLIER_ROULETTE
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) + self.bet_amount * WIN_MULTIPLIER_ROULETTE
            total_balance = user_balances[self.user_id]
            embed = self.create_result_embed("🎉 Roulette Jackpot!",
                                             f"You won {self.bet_amount * WIN_MULTIPLIER_ROULETTE} tokens! The wheel landed on {result}, within the range {chosen_range}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.green())
        else:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) - self.bet_amount * LOSE_MULTIPLIER_ROULETTE
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) - self.bet_amount * LOSE_MULTIPLIER_ROULETTE
            total_balance = user_balances[self.user_id]["balance"]
            embed = self.create_result_embed("👎 Roulette Misfortune",
                                             f"You lost {self.bet_amount * LOSE_MULTIPLIER_ROULETTE} tokens. The wheel landed on {result}, not within the range {chosen_range}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.red())
        await choice_interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="Higher or Lower ↕️", style=nextcord.ButtonStyle.green)
    async def higher_or_lower(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        global user_balances, token_gains
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not the one gambling!", ephemeral=True)
            return

        if not await self.check_balance():
            return

        initial_number = random.randint(2, 9)
        view = nextcord.ui.View()
        view.add_item(nextcord.ui.Button(label="Higher", style=nextcord.ButtonStyle.green, custom_id="higher"))
        view.add_item(nextcord.ui.Button(label="Lower", style=nextcord.ButtonStyle.green, custom_id="lower"))

        await interaction.response.send_message(
            f"🔢 The mystic number is {initial_number}. Will fate be Higher or Lower?", view=view, ephemeral=True)

        def check(m):
            return m.user.id == self.user_id and m.data.get('custom_id') in ["higher", "lower"]

        try:
            choice_interaction = await bot.wait_for("interaction", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Timed out! Please try again.", ephemeral=True)
            return

        next_number = random.randint(1, 10)
        win = False
        if (next_number > initial_number and choice_interaction.data['custom_id'] == "higher") or \
                (next_number < initial_number and choice_interaction.data['custom_id'] == "lower"):
            win = True

        if win:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) + self.bet_amount * WIN_MULTIPLIER_HIGHER_LOWER
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) + self.bet_amount * WIN_MULTIPLIER_HIGHER_LOWER
            total_balance = user_balances[self.user_id]["balance"]
            embed = self.create_result_embed("🎉 Higher or Lower Triumph!",
                                             f"You won {self.bet_amount * WIN_MULTIPLIER_HIGHER_LOWER} tokens! The number was {next_number}, which is {choice_interaction.data['custom_id']} than {initial_number}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.green())
        else:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) - self.bet_amount * LOSE_MULTIPLIER_HIGHER_LOWER
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) - self.bet_amount * LOSE_MULTIPLIER_HIGHER_LOWER
            total_balance = user_balances[self.user_id]["balance"]
            embed = self.create_result_embed("👎 Higher or Lower Defeat",
                                             f"You lost {self.bet_amount * LOSE_MULTIPLIER_HIGHER_LOWER} tokens. The number was {next_number}, which is not {choice_interaction.data['custom_id']} than {initial_number}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.red())
        await choice_interaction.followup.send(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="Odd or Even 🔢", style=nextcord.ButtonStyle.green)
    async def odd_or_even(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        global user_balances, token_gains
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not the one gambling!", ephemeral=True)
            return

        if not await self.check_balance():
            return

        view = nextcord.ui.View()
        view.add_item(nextcord.ui.Button(label="Odd", style=nextcord.ButtonStyle.green, custom_id="odd"))
        view.add_item(nextcord.ui.Button(label="Even", style=nextcord.ButtonStyle.green, custom_id="even"))

        await interaction.response.send_message("🔄 Cast your guess: Odd or Even?", view=view, ephemeral=True)

        def check(m):
            return m.user.id == self.user_id and m.data.get('custom_id') in ["odd", "even"]

        try:
            choice_interaction = await bot.wait_for("interaction", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Timed out! Please try again.", ephemeral=True)
            return

        next_number = random.randint(1, 10)
        is_odd = next_number % 2 != 0
        win = (is_odd and choice_interaction.data['custom_id'] == "odd") or (
                    not is_odd and choice_interaction.data['custom_id'] == "even")

        if win:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) + self.bet_amount * WIN_MULTIPLIER_ODD_EVEN
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) + self.bet_amount * WIN_MULTIPLIER_ODD_EVEN
            total_balance = user_balances[self.user_id]["balance"]
            embed = self.create_result_embed("🎉 Odd or Even Victory!",
                                             f"You won {self.bet_amount * WIN_MULTIPLIER_ODD_EVEN} tokens! The cosmic number was {next_number} and it is {'Odd' if is_odd else 'Even'}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.green())
        else:
            user_balances[self.user_id]["balance"] = max(user_balances[self.user_id]["balance"], 0) - self.bet_amount * LOSE_MULTIPLIER_ODD_EVEN
            token_gains[self.user_id] = token_gains.get(self.user_id, 0) - self.bet_amount * LOSE_MULTIPLIER_ODD_EVEN
            total_balance = user_balances[self.user_id]
            embed = self.create_result_embed("👎 Odd or Even Loss",
                                             f"You lost {self.bet_amount * LOSE_MULTIPLIER_ODD_EVEN} tokens. The cosmic number was {next_number} and it is {'Odd' if is_odd else 'Even'}. Your total balance is now {total_balance} tokens.",
                                             nextcord.Color.red())
        await choice_interaction.followup.send(embed=embed, ephemeral=True)

@bot.slash_command(guild_ids=[GUILD_ID], description="Start gambling by betting tokens")
async def gambling(interaction: nextcord.Interaction, tokens: int):
    user_id = interaction.user.id
    if tokens > user_balances[user_id]["balance"]:
        await interaction.response.send_message("You do not have enough tokens to gamble this amount.", ephemeral=True)
        return

    view = GamblingView(user_id, tokens)
    games_description = f"🎲 Choose your game:\n\n" \
                        f"🪙 Coin Flip - 50/50 chance. Payout: {WIN_MULTIPLIER_COIN_FLIP}x. Loss Multiplier: {LOSE_MULTIPLIER_COIN_FLIP}x.\n" \
                        f"🎰 Roulette - Chance to win based on selected range. Payout: up to {WIN_MULTIPLIER_ROULETTE}x. Loss Multiplier: {LOSE_MULTIPLIER_ROULETTE}x.\n" \
                        f"↕️ Higher or Lower - Odds vary. Payout: {WIN_MULTIPLIER_HIGHER_LOWER}x. Loss Multiplier: {LOSE_MULTIPLIER_HIGHER_LOWER}x.\n" \
                        f"🎯 Odd or Even - 50/50 chance. Payout: {WIN_MULTIPLIER_ODD_EVEN}x. Loss Multiplier: {LOSE_MULTIPLIER_ODD_EVEN}x."

    await interaction.response.send_message(embed=nextcord.Embed(title="Let the Games Begin!", description=games_description, color=nextcord.Color.blurple()), view=view, ephemeral=True)


@bot.slash_command(guild_ids=[GUILD_ID], description="Tip a user with tokens")
async def tip(interaction: nextcord.Interaction, user: nextcord.User, tokens: int, message: str = ''):
    # Check if the user has enough tokens
    if user_balances[interaction.user.id]["balance"] < tokens:
        await interaction.response.send_message("🚫 You don't have enough tokens to tip!", ephemeral=True)
        return

    # Subtract tokens from the tipper's balance
    user_balances[interaction.user.id]["balance"] -= tokens
    
    # Add tokens to the recipient's balance
    user_balances[user.id]["balance"] += tokens
    
    # Update token gains for the recipient
    token_gains[user.id] = token_gains.get(user.id, 0) + tokens

    # Create an embed message to announce the tip
    embed = nextcord.Embed(
        title=f"💸 {interaction.user.display_name} tipped {user.display_name} 💸",
        description=f"🎉 {interaction.user.display_name} has tipped {tokens} tokens to {user.display_name}! 🎉",
        color=nextcord.Color.green()
    )

    # Add the optional message to the embed if provided
    if message:
        embed.add_field(name="💌 Message from the tipper 💌", value=message, inline=False)

    # Send the embed message to the channel
    await interaction.response.send_message(embed=embed)

bot.run("")
