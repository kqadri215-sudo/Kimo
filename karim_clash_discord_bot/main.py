import os
import asyncio
import discord
from discord.ext import commands
import coc
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COC_EMAIL = os.getenv("COC_EMAIL")
COC_PASSWORD = os.getenv("COC_PASSWORD")

# إعدادات البوت والصلاحيات
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# إنشاء عميل Clash of Clans
coc_client = coc.Client()

@bot.event
async def on_ready():
    # تسجيل الدخول لـ CoC API عند بدء التشغيل
    try:
        await coc_client.login(COC_EMAIL, COC_PASSWORD)
        print("Connected to Clash of Clans API!")
    except Exception as e:
        print(f"CoC Login Error: {e}")

    print(f"Logged in as {bot.user.name}")
    print("Bot is ready!")

@bot.command(name="legend", help="جلب إحصائيات دوري الأساطير للاعب باستخدام Tag")
async def legend_stats(ctx, player_tag: str):
    # تنظيف التاج
    if not player_tag.startswith("#"):
        player_tag = "#" + player_tag

    try:
        player = await coc_client.get_player(player_tag)

        # إنشاء بطاقة إحصائيات احترافية (Embed)
        embed = discord.Embed(
            title=f"🏆 Ranked / Legend League Stats: {player.name}",
            description=f"**Tag:** `{player.tag}` | **Town Hall:** {player.town_hall}",
            color=discord.Color.gold()
        )

        if player.league and player.league.name == "Legend League":
            legend_data = player.legend_statistics
            
            embed.add_field(name="🥇 الكؤوس الحالية", value=f"{player.trophies} 🏆", inline=True)
            embed.add_field(name="⚔️ الهجمات الفائزة", value=f"{player.attack_wins}", inline=True)
            embed.add_field(name="🛡️ الدفاعات الفائزة", value=f"{player.defense_wins}", inline=True)

            if legend_data:
                current_season = legend_data.current_season
                best_season = legend_data.best_season
                
                if current_season:
                    embed.add_field(
                        name="📊 الموسم الحالي", 
                        value=f"**الكؤوس:** {current_season.trophies} 🏆\n**المركز:** #{current_season.rank if current_season.rank else 'N/A'}", 
                        inline=False
                    )
                
                if best_season:
                    embed.add_field(
                        name="⭐ أفضل رقم قياسي", 
                        value=f"**الكؤوس:** {best_season.trophies} 🏆\n**المركز:** #{best_season.rank}", 
                        inline=False
                    )
        else:
            embed.add_field(name="🏆 الكؤوس الحالية", value=f"{player.trophies} 🏆", inline=True)
            embed.add_field(name="⚠️ تنبيه", value="هذا اللاعب ليس في دوري الأساطير (Legend League) حالياً.", inline=False)

        if player.clan:
            embed.set_footer(text=f"Clan: {player.clan.name} ({player.clan.tag})", icon_url=player.clan.badge.url if player.clan.badge else None)

        await ctx.send(embed=embed)

    except coc.NotFound:
        await ctx.send(f"❌ لم يتم العثور على لاعب بهذا الـ Tag: `{player_tag}`. تأكد من صحته!")
    except Exception as e:
        await ctx.send(f"⚠️ حدث خطأ أثناء جلب البيانات: {str(e)}")

# تشغيل البوت
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
