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

@bot.command(name="legend", help="جلب تقرير شامل ومفصل للاعب")
async def legend_stats(ctx, player_tag: str):
    if not bot.coc_client:
        await ctx.send("❌ لم يتم الاتصال بـ Clash API بعد.")
        return

    if not player_tag.startswith("#"):
        player_tag = "#" + player_tag

    try:
        player = await bot.coc_client.get_player(player_tag)

        # تجهيز البطاقة الشاملة
        embed = discord.Embed(
            title=f"📊 التقرير الشامل للاعب: {player.name}",
            description=f"**التاغ:** `{player.tag}` | **مستوى الحساب:** {player.exp_level}",
            color=discord.Color.gold()
        )

        # 1. معلومات القرية الرئيسية والتاون هول
        embed.add_field(
            name="🏰 القواعد والمستويات",
            value=f"**Town Hall:** {player.town_hall}\n**Builder Hall:** {player.builder_hall if player.builder_hall else 'غير مبني'}",
            inline=True
        )

        # 2. معلومات الكؤوس
        league_name = player.league.name if player.league else "Unranked"
        embed.add_field(
            name="🏆 الكؤوس والدوري",
            value=f"**الدوري:** {league_name}\n**الكؤوس الحالية:** {player.trophies} 🏆\n**أعلى كؤوس:** {player.best_trophies} 🏆",
            inline=True
        )

        # 3. الكلان والرتبة
        if player.clan:
            role_map = {
                "member": "عضو (Member)",
                "admin": "كابتن (Elder)",
                "coLeader": "مساعد قائد (Co-Leader)",
                "leader": "قائد (Leader)"
            }
            role = role_map.get(player.role.value if hasattr(player.role, 'value') else str(player.role), str(player.role))
            embed.add_field(
                name="🛡️ الكلان",
                value=f"**الاسم:** {player.clan.name}\n**الرتبة:** {role}\n**التاغ:** `{player.clan.tag}`",
                inline=False
            )
        else:
            embed.add_field(name="🛡️ الكلان", value="لا ينتمي لأي كلان حالياً", inline=False)

        # 4. الأبطال ومستوياتهم
        heroes_list = []
        for hero in player.heroes:
            if hero.is_home_base:
                heroes_list.append(f"• **{hero.name}:** Lv. {hero.level}/{hero.max_level}")
        
        heroes_text = "\n".join(heroes_list) if heroes_list else "لا يوجد أبطال"
        embed.add_field(name="👑 مستويات الأبطال", value=heroes_text, inline=True)

        # 5. أداء الموسم والهجمات
        embed.add_field(
            name="⚔️ أداء الموسم الحالي",
            value=f"**الهجمات الناجحة:** {player.attack_wins}\n**الدفاعات الناجحة:** {player.defense_wins}\n**التبرعات الممنوحة:** {player.donations}\n**التبرعات المستلمة:** {player.received_donations}",
            inline=True
        )

        # 6. تفاصيل إضافية لدوري الأساطير (إذا كان في الأساطير)
        if player.league and player.league.name == "Legend League":
            legend_data = player.legend_statistics
            if legend_data and legend_data.current_season:
                embed.add_field(
                    name="📊 إحصائيات دوري الأساطير", 
                    value=f"**كؤوس الموسم الحالي:** {legend_data.current_season.trophies} 🏆\n**المركز العالمي:** #{legend_data.current_season.rank if legend_data.current_season.rank else 'N/A'}", 
                    inline=False
                )

        if player.clan and player.clan.badge:
            embed.set_thumbnail(url=player.clan.badge.url)

        await ctx.send(embed=embed)

    except coc.NotFound:
        await ctx.send(f"❌ لم يتم العثور على لاعب بالتاج: `{player_tag}`. تأكد من صحته!")
    except Exception as e:
        await ctx.send(f"⚠️ حدث خطأ أثناء جلب البيانات: {str(e)}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
