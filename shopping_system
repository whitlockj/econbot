import nextcord
import random
import logging
import re

# Configure logging to both file and console
logging.basicConfig(filename='bot.log', level=logging.ERROR, format='%(levelname)s: %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
# Color role IDs
color_role_ids = {
    'yellow': 1231339290118590564,
    'red': 1231339404736598208,
    'green': 1231339344661577769,
    'blue': 1234712908357701682,
    'pink': 1234741878264692806,
    'purple': 1234713935928885290,
    'orange': 1234713487150940240,
}

# Special color roles
special_color_ids = {
    'rainbows': 1232180510227169410  # Rainbows role ID
}

# Non-color role IDs (special roles, admin roles, etc.)
special_role_ids = {
    'epic_member': 1231326698809589770,  # EPIC member role
    'name_change': 1232169888911724544,  # Role for name change
    'server_announcement': 1232196345851412512  # Role for server announcement
}

emoji_cost = 200  # Cost to add an emoji to the end of the name
color_cost = 100  # Cost to change color
name_change = 350  # Cost to change name
server_announcement_cost = 500  # Cost to make a server-wide announcement
month_of_nitro_cost = 2000  # Cost to buy a month of Nitro
rainbows_cost = 200  # Cost to get the Rainbows role
epic_member_role_cost = 500  # Cost to get the EPIC member role
ticket_pot_threshold = 15  # Threshold for the lottery pot
lottery_announcement_channel_id = 1229582044187852916


class ItemSelectView(nextcord.ui.View):
    def __init__(self, interaction, author, guild, lottery_pot, user_balances, user_tickets, client):
        super().__init__()
        self.interaction = interaction
        self.author = author
        self.guild = guild
        self.lottery_pot = lottery_pot
        self.user_balances = user_balances
        self.user_tickets = user_tickets
        self.client = client

    @nextcord.ui.select(
        placeholder="Select an item to purchase...",
        min_values=1,
        max_values=1,
        options=[
            nextcord.SelectOption(label=f"EPIC member Role - {epic_member_role_cost} tokens", value="1",
                                  description="Join and become a prestigious EPIC member!"),
            nextcord.SelectOption(label=f"Color Change Role - {color_cost} tokens", value="2",
                                  description="Change your username color."),
            nextcord.SelectOption(label=f"Name Change - {name_change} tokens", value="3",
                                  description="Buy this item to change your nickname once."),
            nextcord.SelectOption(label=f"Fuckin' Rainbows - {rainbows_cost} tokens", value='4',
                                  description='Watch your name color change every few minutes!'),
            nextcord.SelectOption(label=f"Server Announcement - {server_announcement_cost} tokens", value='5',
                                  description='Make a server-wide announcement.'),
            nextcord.SelectOption(label="Lottery Tickets - 10 tokens each", value='6',
                                  description='Try your luck with lottery tickets!'),
            nextcord.SelectOption(label=f"Month of Nitro - {month_of_nitro_cost} tokens", value='7',
                                  description='Buy a month of Niro. Gift from OverratedAardvark ;)!'),
            nextcord.SelectOption(label=f"Name Emoji Modifier - {emoji_cost} tokens", value="8",
                                  description="Add an emoji to the end of your name!")

        ]
    )
    async def select_callback(self, select, interaction):
        item_id = int(select.values[0])
        await buy_item(interaction, self.author, self.guild, item_id, self.lottery_pot, self.user_balances,
                       self.user_tickets, self.client)
        self.stop()


class ColorSelectView(nextcord.ui.View):
    def __init__(self, interaction, author, guild, user_balances):
        super().__init__()
        self.interaction = interaction
        self.author = author
        self.guild = guild
        self.user_balances = user_balances  # Pass user balances into the view

    @nextcord.ui.select(
        placeholder="Choose your color...",
        min_values=1,
        max_values=1,
        options=[nextcord.SelectOption(label=color.title(), value=color) for color in color_role_ids.keys()]
    )
    async def select_callback(self, select, interaction):
        selected_color = select.values[0]
        new_role = self.guild.get_role(color_role_ids[selected_color])

        # Check user balance and deduct tokens
        token_cost = color_cost
        user_balance = self.user_balances.get(self.author.id, 0)
        if user_balance < token_cost:
            await interaction.response.send_message("Insufficient tokens to purchase this color change.", ephemeral=True)
            return

        # Proceed with role assignment if balance is sufficient
        if new_role is None:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return

        current_color_roles = [role for role in self.author.roles if role.id in color_role_ids.values()]
        rainbows_role = self.guild.get_role(special_color_ids['rainbows'])

        # Check if user has the Rainbows role and is trying to switch to a different color
        if rainbows_role in self.author.roles:
            # If selecting a new color while having Rainbows, confirm the change
            confirm_view = ConfirmView(self.author, new_role, [rainbows_role], self.user_balances)
            await interaction.response.send_message(
                "You currently have the Rainbows role. Switch to the selected color?", view=confirm_view,
                ephemeral=True)
            return
        elif new_role in self.author.roles:
            await interaction.response.send_message("You already have this role!", ephemeral=True)
            return
        else:
            roles_to_remove = [role for role in current_color_roles if role in self.author.roles]
            try:
                await self.author.remove_roles(*roles_to_remove, reason="Changing color role")
                await self.author.add_roles(new_role, reason="Adding new color role")
                self.user_balances[self.author.id] -= token_cost  # Deduct the token cost
                await interaction.response.edit_message(
                    content="Your role color has been updated and 100 tokens have been deducted!", view=None)
            except nextcord.Forbidden:
                await interaction.response.send_message("I do not have permission to manage roles.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Failed to update role: {str(e)}", ephemeral=True)

class ConfirmView(nextcord.ui.View):
    def __init__(self, author, new_role, current_roles, user_balances):
        super().__init__()
        self.author = author
        self.new_role = new_role
        self.current_roles = current_roles
        self.user_balances = user_balances  # Added user_balances to store user balances

    @nextcord.ui.button(label="Yes! Change it up!", style=nextcord.ButtonStyle.green)
    async def confirm_button(self, button, interaction):
        logging.debug("Attempting to change roles.")
        if self.new_role is None:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return

        # Check if the user has enough tokens before proceeding
        token_cost = 100  # Assuming the cost for a role change
        if self.user_balances.get(self.author.id, 0) < token_cost:
            await interaction.response.send_message("Insufficient tokens for this role change.", ephemeral=True)
            return

        try:
            await self.author.remove_roles(*self.current_roles, reason="Role change requested")
            await self.author.add_roles(self.new_role, reason="Role change requested")
            self.user_balances[self.author.id] -= token_cost  # Deduct the token cost from the user's balance
            await interaction.response.edit_message(
                content=f"Your role has been changed successfully! {token_cost} tokens have been deducted.", view=None)
        except nextcord.Forbidden:
            logging.error("Bot lacks permissions to manage roles.")
            await interaction.response.send_message("I do not have the necessary permissions to change roles.",
                                                    ephemeral=True)
        except Exception as e:
            logging.error(f"Failed to change roles due to: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @nextcord.ui.button(label="Naaa nvm kthx", style=nextcord.ButtonStyle.red)
    async def cancel_button(self, button, interaction):
        await interaction.response.edit_message(content="Role change canceled.", view=None)


class LotteryTicketView(nextcord.ui.View):
    def __init__(self, interaction, user, server, lottery_system):
        super().__init__()
        self.interaction = interaction  # Store the interaction to modify the original response later
        self.user = user
        self.server = server
        self.lottery_system = lottery_system

    @nextcord.ui.button(label="Purchase 1 Ticket", style=nextcord.ButtonStyle.primary)
    async def purchase_single_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.purchase_tickets(1, interaction)

    @nextcord.ui.button(label="Purchase 5 Tickets", style=nextcord.ButtonStyle.primary)
    async def purchase_five_tickets(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.purchase_tickets(5, interaction)

    @nextcord.ui.button(label="Purchase 10 Tickets", style=nextcord.ButtonStyle.primary)
    async def purchase_ten_tickets(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.purchase_tickets(10, interaction)

    async def purchase_tickets(self, ticket_quantity, interaction):
        purchase_message = await self.lottery_system.buy_ticket(self.user.id, ticket_quantity)
        if not interaction.response.is_done():
            # Initial response to the interaction
            await interaction.response.send_message(f"{purchase_message}", ephemeral=True)
        else:
            # Edit the original message if a response has already been made
            await interaction.edit_original_message(content=f"{purchase_message}")


class LotterySystem:
    lottery_pot = 0  # Define as a class variable
    drawing_in_progress = False  # This can also be a class variable if only one draw can happen at any time across all instances

    def __init__(self, user_balances, user_tickets, client):
        self.user_balances = user_balances
        self.user_tickets = user_tickets
        self.client = client

    async def buy_ticket(self, user_id, ticket_quantity, ticket_cost=10):
        if self.drawing_in_progress:
            return "Lottery draw in progress, please wait."

        total_cost = ticket_cost * ticket_quantity
        if self.user_balances.get(user_id, 0) < total_cost:
            return f"Insufficient balance to buy {ticket_quantity} tickets."

        self.user_balances[user_id] -= total_cost
        self.user_tickets[user_id] = self.user_tickets.get(user_id, 0) + ticket_quantity

        LotterySystem.lottery_pot += total_cost  # Use class name to reference class variable

        if sum(self.user_tickets.values()) >= ticket_pot_threshold and not self.drawing_in_progress:
            return await self.draw_winner()

        return f"You bought {ticket_quantity} lottery tickets! You now have {self.user_tickets[user_id]} tickets."

    async def draw_winner(self):
        self.drawing_in_progress = True
        if not self.user_tickets:
            self.drawing_in_progress = False
            return "No tickets were bought in this round."

        winner = random.choice(list(self.user_tickets.keys()))
        winnings = LotterySystem.lottery_pot
        self.user_balances[winner] += winnings

        # Fetch the user object using the winner's ID
        winner_user = await self.client.fetch_user(winner)

        await self.send_winner_dm(winner, winnings)

        # Get the channel for lottery announcements
        lottery_channel = self.client.get_channel(lottery_announcement_channel_id)

        # Send a public announcement in the lottery channel
        await lottery_channel.send(
            f"🎉 Congratulations {winner_user.name}! 🎉 You won the lottery and got {winnings} tokens! 🥳")

        # Reset the lottery after declaring a winner
        self.reset_lottery()
        return f"Your purchase of tickets has made the lottery reach its threshhold and triggered the drawing. Hope it was you, bud."

    def reset_lottery(self):
        self.user_tickets.clear()
        LotterySystem.lottery_pot = 0  # Reset class variable
        self.drawing_in_progress = False

    async def send_winner_dm(self, winner_id, amount):
        try:
            user = await self.client.fetch_user(winner_id)
            await user.send(f"Congratulations! You have won {amount} in the lottery!")
        except Exception as e:
            print(f"Failed to send DM to {winner_id}: {str(e)}")


async def buy_item(interaction, author, guild, item_id, lottery_pot, user_balances, user_tickets, client):
    global epic_member_role_cost, rainbows_cost, name_change, server_announcement_cost, month_of_nitro_cost

    if item_id == 1:  # EPIC member Role
        role = guild.get_role(special_role_ids['epic_member'])
        if role:
            if role in author.roles:
                await interaction.response.send_message("You already have this role!", ephemeral=True)
            else:
                if user_balances[author.id] >= epic_member_role_cost:
                    try:
                        await author.add_roles(role)
                        user_balances[author.id] -= epic_member_role_cost
                        await interaction.response.send_message(f"Role granted successfully! {epic_member_role_cost} tokens have been deducted.", ephemeral=True)
                    except nextcord.Forbidden:
                        await interaction.response.send_message("Error: I do not have permission to assign roles.", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"An error occurred while assigning the role: {str(e)}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Insufficient tokens to purchase the EPIC member role. It costs {epic_member_role_cost} tokens.", ephemeral=True)
        else:
            await interaction.response.send_message("Error: Role not found.", ephemeral=True)

    elif item_id == 2:  # Color Change Role
        color_view = ColorSelectView(interaction, author, guild, user_balances)
        await interaction.response.send_message("Please choose a color:", view=color_view, ephemeral=True)

    elif item_id == 3:  # Name Change
        role = guild.get_role(special_role_ids['name_change'])
        if role:
            if role in author.roles:
                await interaction.response.send_message("You already have this role!", ephemeral=True)
            else:
                if user_balances[author.id] >= name_change:
                    try:
                        await author.add_roles(role)
                        user_balances[author.id] -= name_change
                        await interaction.response.send_message(f"Role for name change granted successfully! {name_change} tokens have been deducted.", ephemeral=True)
                    except nextcord.Forbidden:
                        await interaction.response.send_message("Error: I do not have permission to assign roles.", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"An error occurred while assigning the role: {str(e)}", ephemeral=True)
                else:
                    await interaction.response.send_message("Insufficient tokens for name change.", ephemeral=True)
        else:
            await interaction.response.send_message("Error: Role not found.", ephemeral=True)


    elif item_id == 4:  # Handling for Rainbows role

        role = guild.get_role(special_color_ids['rainbows'])

        if role:

            if role in author.roles:

                await interaction.response.send_message("You already have the Rainbows role!", ephemeral=True)

            else:

                # Check if the user has any color role

                current_color_roles = [r for r in author.roles if r.id in color_role_ids.values()]

                if current_color_roles:  # User has one or more color roles

                    # Prompt for confirmation before adding Rainbows and removing color roles

                    confirm_view = ConfirmView(author, role, current_color_roles, user_balances)

                    await interaction.response.send_message(

                        "You currently have a color role. Switch to the Rainbows role?",

                        view=confirm_view, ephemeral=True)

                else:

                    # No color roles, add Rainbows directly

                    if user_balances[author.id] >= rainbows_cost:

                        await author.add_roles(role)

                        user_balances[author.id] -= rainbows_cost

                        await interaction.response.send_message(

                            f"Rainbows role granted successfully! {rainbows_cost} tokens have been deducted.",

                            ephemeral=True)

                    else:

                        await interaction.response.send_message(

                            f"Insufficient tokens to purchase the Rainbows role. It costs {rainbows_cost} tokens.",

                            ephemeral=True)

        else:

            await interaction.response.send_message("Error: Role not found.", ephemeral=True)


    elif item_id == 5:  # Server Announcement
        role = guild.get_role(special_role_ids['server_announcement'])
        if role:
            if role in author.roles:
                await interaction.response.send_message("You already have this role!", ephemeral=True)
            else:
                if user_balances[author.id] >= server_announcement_cost:
                    try:
                        await author.add_roles(role)
                        user_balances[author.id] -= server_announcement_cost
                        await interaction.response.send_message(f"Role for server announcements granted successfully! {server_announcement_cost} tokens have been deducted. Use the command `/announcement` to make a server-wide announcement whenever you want.", ephemeral=True)
                    except nextcord.Forbidden:
                        await interaction.response.send_message("Error: I do not have permission to assign roles.", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"An error occurred while assigning the role: {str(e)}", ephemeral=True)
                else:
                    await interaction.response.send_message("Insufficient tokens for server announcement.", ephemeral=True)
        else:
            await interaction.response.send_message("Error: Role not found.", ephemeral=True)

    elif item_id == 6:  # Lottery Tickets
        lottery_view = LotteryTicketView(interaction, author, guild, LotterySystem(user_balances, user_tickets, client))
        await interaction.response.send_message("Select the number of tickets you want to purchase:", view=lottery_view, ephemeral=True)

    elif item_id == 7:  # Month of Nitro
        if user_balances[author.id] >= month_of_nitro_cost:
            admin_user_id = 899566604931706911  # Admin user ID
            admin_user = await client.fetch_user(admin_user_id)
            await admin_user.send(f"<@{author.id}> has purchased a Month of Nitro!")
            user_balances[author.id] -= month_of_nitro_cost
            await interaction.response.send_message("Thank you for purchasing a Month of Nitro! 2000 tokens have been deducted.", ephemeral=True)
        else:
            await interaction.response.send_message("Insufficient tokens to purchase a Month of Nitro.", ephemeral=True)

    elif item_id == 8:  # Name Emoji Modifier
        emoji_select_view = EmojiSelectView(interaction, author, guild, user_balances)
        await interaction.response.send_message("Select an emoji to add to your name:", view=emoji_select_view, ephemeral=True)

class EmojiSelectView(nextcord.ui.View):
    def __init__(self, interaction, author, guild, user_balances):
        super().__init__()
        self.interaction = interaction
        self.author = author
        self.guild = guild
        self.user_balances = user_balances

    @nextcord.ui.select(
        placeholder="Select an emoji...",
        min_values=1,
        max_values=1,
        options=[
            nextcord.SelectOption(label="The Hiker 🥾", value="🥾"),
            nextcord.SelectOption(label="The Adventurer ⛰️", value="⛰️"),
            nextcord.SelectOption(label="Exploding with Awesome 💥", value="💥"),
            nextcord.SelectOption(label="Fools Potato 🥔", value="🥔"),
            nextcord.SelectOption(label="The Partier 🥳", value="🥳"),
            nextcord.SelectOption(label="Love ❤️", value="❤️"),
            nextcord.SelectOption(label="I'm a cat 😺", value="😺"),
            nextcord.SelectOption(label="The Majestic 🦄", value="🦄")
        ]
    )
    async def select_callback(self, select, interaction):
        emoji = select.values[0]
        existing_emoji = re.search(r'\s*([\U0001F000-\U0001F9FF]+)\s*$', self.author.display_name)

        if existing_emoji:
            if f" {existing_emoji.group(1)}" == f" {emoji}":
                await interaction.response.send_message("You already have this emoji!", ephemeral=True)
                return
            confirm_view = ConfirmEmojiChangeView(interaction, self.author, self.guild, emoji, self.user_balances)
            await interaction.response.send_message(
                f"You currently have an emoji ({existing_emoji.group(1)}). Are you sure you want to change it to {emoji}?",
                view=confirm_view, ephemeral=True)
            return

        if self.user_balances.get(self.author.id, 0) >= emoji_cost:
            self.user_balances[self.author.id] -= emoji_cost  # Deduct tokens
            await self.apply_emoji_change(emoji, interaction)
        else:
            await interaction.response.send_message("Insufficient tokens to add this emoji.", ephemeral=True)

    async def apply_emoji_change(self, emoji, interaction):
        new_name = re.sub(r'\s*([\U0001F000-\U0001F9FF]+)\s*$', '', self.author.display_name)
        new_name += f" {emoji}"
        try:
            await self.author.edit(nick=new_name)
            await interaction.response.send_message(f"Your nickname has been updated to: {new_name}", ephemeral=True)
        except nextcord.Forbidden:
            await interaction.response.send_message("I don't have permission to change nicknames.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


class ConfirmEmojiChangeView(nextcord.ui.View):
    def __init__(self, interaction, author, guild, new_emoji, user_balances):
        super().__init__()
        self.interaction = interaction
        self.author = author
        self.guild = guild
        self.new_emoji = new_emoji
        self.user_balances = user_balances

    @nextcord.ui.button(label="Yes, change it!", style=nextcord.ButtonStyle.green)
    async def confirm_change(self, button, interaction):
        if self.user_balances.get(self.author.id, 0) >= emoji_cost:
            self.user_balances[self.author.id] -= emoji_cost  # Deduct tokens
            await EmojiSelectView(interaction, self.author, self.guild, self.user_balances).apply_emoji_change(
                self.new_emoji, interaction)
            try:
                await interaction.edit_original_message(content="Emoji has been changed successfully!", view=None)
            except nextcord.errors.InteractionResponded:
                # This block is optional and normally shouldn't be necessary unless other interactions can occur.
                print("Attempted to edit an already responded interaction.")
            self.stop()
        else:
            try:
                await interaction.response.send_message("Insufficient tokens after confirmation.", ephemeral=True)
            except nextcord.errors.InteractionResponded:
                await interaction.followup.send("Insufficient tokens after confirmation.", ephemeral=True)
            self.stop()

    @nextcord.ui.button(label="No, keep current!", style=nextcord.ButtonStyle.red)
    async def cancel_change(self, button, interaction):
        try:
            await interaction.edit_original_message(content="Emoji change canceled.", view=None)
        except nextcord.errors.InteractionResponded:
            print("Attempted to edit an already responded interaction.")
        self.stop()


async def show_shop_items(interaction, lottery_pot, user_balances, user_tickets, client):
    try:
        token_balance = user_balances.get(interaction.user.id, 0)
        embed = nextcord.Embed(
            title="🛒 Bird's Corner Store",
            description=f"Welcome, my esteemed customer :bird:! Feast your eyes upon the wares of my legendary bird emporium.\n\nCurrent token balance: {token_balance} tokens",
            color=nextcord.Color.gold()
        )
        file = nextcord.File('mystuff.gif', filename="mystuff.gif")
        embed.set_image(url="attachment://mystuff.gif")
        view = ItemSelectView(interaction, interaction.user, interaction.guild, lottery_pot, user_balances,
                              user_tickets, client)
        await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)
    except Exception as e:
        logging.error(f"Error in show_shop_items: {e}")
        try:
            await interaction.response.send_message("An error occurred while loading the shop items.", ephemeral=True)
        except nextcord.errors.InteractionResponded:
            logging.error("Failed to send error message due to InteractionResponded.")
