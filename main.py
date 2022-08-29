import os
import time
import index
import discord

from discord_slash import SlashCommand
from discord.ext import commands, tasks
from utils import timef, db_news_channels
from discord.ext.commands import has_permissions, CheckFailure

bot = commands.Bot(command_prefix="!")
slash = SlashCommand(bot, sync_commands=True)

db = db_news_channels.Database()
db.create_tables()


@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))
    live_news.start()


@slash.slash(name="help", description="Show bot info")
async def info(ctx):
    await ctx.send(
        'Thank you for inviting me to this server.\nPlease note that the events reported on Universal Awareness may '
        'be misleading and it is up to your independent thinking skills to determine what is true.''\n\nI am still in '
        'development. Please activate me using !news-setup',
        hidden=True)


@slash.slash(name="ping", description="Execute a ping")
async def ping(ctx):
    i = time.perf_counter()
    ping_msg = await ctx.defer(hidden=True)
    f = time.perf_counter()
    await ctx.send(content=f"Pong! {round(bot.latency * 1000)}ms\nAPI: {round((f - i) * 1000)}ms", hidden=True)


@slash.slash(name="guild", description="Show guild")
async def guild(ctx):
    await ctx.send(('Guild Name: ' + ctx.guild.name + '\nGuild ID: ' + str(ctx.guild.id)), hidden=True)


@bot.command(name="global-message")
async def global_message(ctx):
    await ctx.message.delete()
    if ctx.author.id == 296447016555249664:
        inquire = await ctx.channel.send('Enter message:')

        def check(m):
            return ctx.author == m.author

        msg = await bot.wait_for('message', timeout=60.0, check=check)
        await msg.delete()
        await inquire.delete()
        channels = db.fetch("SELECT channel_id FROM news_channels")
        for entry in channels:
            channel_id = list(entry.values())[0]
            channel = bot.get_channel(int(channel_id))
            embed = discord.Embed(description=msg.content, color=0x8C00FF)
            embed.set_author(name='Global Message from Developer')
            embed.timestamp = timef.time_index()
            await channel.send(embed=embed)
        await ctx.channel.send('Message sent to all guilds', delete_after=5)
    else:
        await ctx.channel.send("Sorry {}, you do not have permissions to do that!".format(ctx.message.author),
                               delete_after=5)


@bot.command(name="check-database")
async def database_check(ctx):
    await ctx.message.delete()
    if ctx.author.id == 296447016555249664:
        embed = discord.Embed(color=0x8C00FF)
        embed.set_author(name='Current news-channel database')
        news_database = db.fetch("SELECT * FROM news_channels")
        count = 0
        for entry in news_database:
            count += 1
            values = list(entry.values())
            embed.add_field(name="Guild ID", value=values[0], inline=True)
            embed.add_field(name="Channel ID", value=values[1], inline=True)
            embed.add_field(name="Created At", value=values[2], inline=True)
        embed.set_footer(text='Counted ' + str(count) + " entries in database")
        await ctx.channel.send(embed=embed)
    else:
        await ctx.channel.send("Sorry {}, you do not have permissions to do that!".format(ctx.message.author),
                               delete_after=5)


@bot.command(name="news-setup")
@has_permissions(manage_channels=True)
async def news_setup(ctx):
    await ctx.message.delete()
    inquire = await ctx.channel.send('Enter channel name:')

    def check(m):
        return ctx.author == m.author

    msg = await bot.wait_for('message', timeout=60.0, check=check)
    await inquire.delete()
    for channel in ctx.guild.channels:
        if channel.name == msg.content:
            guild_id = str(ctx.guild.id)
            channel_id = str(channel.id)
            db.execute(
                "REPLACE INTO news_channels (guild_id, channel_id) "
                "VALUES (?, ?)",
                (guild_id, channel_id)
            )
            await msg.delete()
            await ctx.channel.send('News channel has been set to #' + msg.content)


@news_setup.error
async def news_setup_error(ctx, error):
    await ctx.message.delete()
    if isinstance(error, CheckFailure):
        text = "Sorry {}, you do not have permissions to do that!".format(ctx.message.author)
        await ctx.channel.send(text)


@tasks.loop(seconds=index.read_json("loop_delay"))
async def live_news():
    request = index.main()

    if request is not None:

        title = request[0]
        link = request[1]
        location = request[2]
        source = request[3]
        color = request[4]
        img = request[5]
        vid = request[6]
        date = request[7]

        embed = discord.Embed(
            url=link,
            description=title,
            color=discord.Color.from_rgb(color[0], color[1], color[2])
        )

        embed.set_author(name=location, url=source)
        # embed.set_footer(text = 'Developed by Atomikku')
        embed.timestamp = date

        if img:
            embed.set_image(url=img)

        if vid:
            embed.add_field(name='Twitter Video', value=f"[Warning: May be graphic. Proceed at your own risk]({vid})")

        if os.path.exists("utils/type.png"):
            index.pretty_print("!", timef.time_cst() + "Checks approved, sending to all indexed guilds...")
            channels = db.fetch("SELECT channel_id FROM news_channels")
            for entry in channels:
                channel_id = list(entry.values())[0]
                channel = bot.get_channel(int(channel_id))
                file = discord.File("utils/type.png", filename="type.png")
                embed.set_thumbnail(url="attachment://type.png")
                await channel.send(file=file, embed=embed)
            os.remove("utils/type.png")
        else:
            index.pretty_print("-", timef.time_cst() + "Thumbnail not found, skipping...")
            channels = db.fetch("SELECT channel_id FROM news_channels")
            for entry in channels:
                channel_id = list(entry.values())[0]
                channel = bot.get_channel(int(channel_id))
                await channel.send(embed=embed)

    else:
        index.pretty_print("-", timef.time_cst() + "Found no news... waiting " + str(
            index.read_json("loop_delay")) + " seconds to try again...")


bot.run(os.environ['TOKEN'])
