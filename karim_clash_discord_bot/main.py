import os
import discord
from discord.ext import commands
import coc
from dotenv import load_dotenv

# تحميل المتغيرات
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COC_EMAIL = os.getenv("COC_EMAIL")
COC_PASSWORD = os.getenv("COC_PASSWORD")

# إعدادات الديسكورد
intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.coc_client = None

    async def setup_hook(self):
        # إنشاء وتسجيل دخول عميل كلاش بعد فتح الـ asyncio event loop
        try:
            self.coc_client = coc.Client()
            await self.coc_client.login(COC_EMAIL, COC_PASSWORD)
            print("Successfully logged into Clash of Clans API!")
        except Exception as e:
            print(f"CoC Login Exception: {e}")

    async def close(self):
        if self.coc_client:
            await self.coc_client.close()
        await super().close()

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bot connected as: {bot.user.name}")
    print("Bot is ready to use!")

@bot.command(name="legend", help="جلب إحصائيات دوري الأساطير للاعب")
async def legend_stats(ctx, player_tag: str):
    if not bot.coc_client:
        await ctx.send("❌ لم يتم الاتصال بـ Clash API بعد.")
        return

    if not player_tag.startswith("#"):
        player_tag = "#" + player_tag

    try:
        player = await bot.coc_client.get_player(player_tag)

        embed = discord.Embed(
            title=f"🏆 Ranked / Legend League: {player.name}",
            description=f"**Tag:** `{player.tag}` | **Town Hall:** {player.town_hall}",
            color=discord.Color.gold()
        )

        embed.add_field(name="🥇 الكؤوس الحالية", value=f"{player.trophies} 🏆", inline=True)
        embed.add_field(name="⚔️ الهجمات الفائزة", value=f"{player.attack_wins}", inline=True)
        embed.add_field(name="🛡️ الدفاعات الفائزة", value=f"{player.defense_wins}", inline=True)

        if player.league and player.league.name == "Legend League":
            legend_data = player.legend_statistics
            if legend_data and legend_data.current_season:
                embed.add_field(
                    name="📊 الموسم الحالي", 
                    value=f"**الكؤوس:** {legend_data.current_season.trophies} 🏆", 
                    inline=False
                )
        else:
            embed.add_field(name="⚠️ تنبيه", value="اللاعب ليس في دوري الأساطير حالياً.", inline=False)

        if player.clan:
            embed.set_footer(text=f"Clan: {player.clan.name} ({player.clan.tag})")

        await ctx.send(embed=embed)

    except coc.NotFound:
        await ctx.send(f"❌ لم يتم العثور على لاعب بالتاج: `{player_tag}`")
    except Exception as e:
        await ctx.send(f"⚠️ حدث خطأ: {str(e)}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
