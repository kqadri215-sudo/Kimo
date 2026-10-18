import os
import re
import io
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
API_BASE = os.getenv("CLASHKING_API_BASE", "https://api.clashk.ing").rstrip("/")
BRAND = os.getenv("BRAND_NAME", "Karim Clash").strip() or "Karim Clash"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("karim-clash-bot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Image helpers ---------------------------------------------------------

WIDTH = 1600
BG = (24, 29, 43)
PANEL = (39, 46, 64)
PANEL_ALT = (49, 57, 77)
GOLD = (255, 197, 65)
WHITE = (247, 248, 252)
MUTED = (175, 186, 205)
GREEN = (91, 205, 132)
RED = (239, 111, 111)
STAR_ON = (255, 230, 123)
STAR_OFF = (83, 91, 111)

def load_font(size: int, bold: bool = False):
    candidates = []
    if os.name == "nt":
        candidates += [
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()

F_TITLE = load_font(43, True)
F_SUB = load_font(23, True)
F_SECTION = load_font(28, True)
F_CARD = load_font(24, True)
F_SMALL = load_font(17, False)
F_TINY = load_font(15, False)

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def format_signed(value):
    n = safe_int(value)
    return f"{n:+d}" if n > 0 else str(n)

def stars_text(stars):
    stars = max(0, min(3, safe_int(stars)))
    return stars

def draw_star(draw, cx, cy, outer, fill, outline=None):
    import math
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = outer if i % 2 == 0 else outer * 0.45
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(pts, fill=fill, outline=outline or fill)

def clean_name(value, max_len=22):
    if not value:
        return "Unknown opponent"
    value = str(value).replace("\n", " ").strip()
    return value if len(value) <= max_len else value[: max_len - 1] + "…"

def draw_battle_card(draw, x, y, w, h, battle, defense=False):
    # Each card is deliberately self-contained so missing fields don't break rendering.
    card_bg = (53, 61, 81) if not defense else (48, 55, 74)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=17, fill=card_bg, outline=(76, 86, 111), width=2)

    trophy = safe_int(battle.get("trophies", 0))
    trophy_color = GREEN if trophy > 0 else RED if trophy < 0 else MUTED
    sign = format_signed(trophy)
    draw.text((x + 17, y + 10), sign, font=F_CARD, fill=trophy_color)
    draw.text((x + w - 44, y + 12), "🏆", font=F_SMALL, fill=GOLD)

    stars = stars_text(battle.get("stars", 0))
    star_y = y + 57
    start_x = x + 27
    for i in range(3):
        draw_star(draw, start_x + i * 31, star_y, 12, STAR_ON if i < stars else STAR_OFF)

    opponent = battle.get("opponent") or {}
    opponent_name = clean_name(opponent.get("name", "Unknown opponent"), 18)
    th = opponent.get("townHallLevel")
    line = f"{opponent_name}" + (f"  TH{th}" if th else "")
    draw.text((x + 15, y + h - 33), line, font=F_TINY, fill=WHITE)
    destruction = battle.get("destructionPercentage")
    if destruction is not None:
        draw.text((x + w - 15, y + h - 33), f"{safe_int(destruction)}%", font=F_TINY, fill=MUTED, anchor="ra")

def create_battle_image(player_tag, day, data):
    attacks = data.get("attacks") or []
    defenses = data.get("defenses") or []
    # Game data can contain more than 8 records; show all while keeping image readable.
    cols = 4
    rows = max(2, (max(len(attacks), len(defenses), 1) + cols - 1) // cols)
    card_w, card_h = 350, 112
    gap_x, gap_y = 16, 13
    side_padding = 42
    section_gap = 34
    section_w = cols * card_w + (cols - 1) * gap_x
    width = side_padding * 2 + section_w
    header_h = 220
    section_header_h = 58
    height = header_h + 2 * (section_header_h + rows * card_h + max(0, rows - 1) * gap_y) + section_gap + 48
    height = max(700, height)

    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    # Header
    draw.rounded_rectangle((25, 22, width - 25, 167), radius=28, fill=PANEL, outline=(87, 99, 127), width=2)
    draw.text((side_padding, 42), BRAND, font=F_TITLE, fill=GOLD)
    draw.text((side_padding, 100), "LEGEND LEAGUE • BATTLE REPORT", font=F_SUB, fill=WHITE)
    draw.text((width - side_padding, 52), f"DAY  {day}", font=F_SUB, fill=MUTED, anchor="ra")
    draw.text((width - side_padding, 100), f"PLAYER  {player_tag}", font=F_SMALL, fill=WHITE, anchor="ra")

    atk_total = safe_int(data.get("attackTrophies", sum(safe_int(a.get("trophies")) for a in attacks)))
    def_total = safe_int(data.get("defenseTrophies", sum(safe_int(d.get("trophies")) for d in defenses)))
    total = safe_int(data.get("trophies", atk_total + def_total))

    # Totals strip
    strip_y = 178
    draw.rounded_rectangle((25, strip_y, width - 25, strip_y + 48), radius=15, fill=(31, 37, 54))
    draw.text((side_padding, strip_y + 9), f"ATTACKS  {format_signed(atk_total)} 🏆", font=F_SUB, fill=GREEN)
    draw.text((width // 2, strip_y + 9), f"TOTAL  {format_signed(total)} 🏆", font=F_SUB, fill=GOLD, anchor="mm")
    draw.text((width - side_padding, strip_y + 9), f"DEFENSES  {format_signed(def_total)} 🏆", font=F_SUB, fill=RED, anchor="ra")

    y0 = header_h
    for label, records, is_defense in [
        ("ATTACKS", attacks, False),
        ("DEFENSES", defenses, True),
    ]:
        color = RED if is_defense else GREEN
        draw.rounded_rectangle((side_padding - 5, y0, width - side_padding + 5, y0 + 46), radius=13, fill=PANEL_ALT)
        draw.text((side_padding + 10, y0 + 7), f"{label}  •  {len(records)} battles", font=F_SECTION, fill=color)
        if not records:
            draw.text((side_padding + 10, y0 + 62), "No records returned for this day.", font=F_SMALL, fill=MUTED)
        for i, battle in enumerate(records):
            row, col = divmod(i, cols)
            x = side_padding + col * (card_w + gap_x)
            y = y0 + section_header_h + row * (card_h + gap_y)
            draw_battle_card(draw, x, y, card_w, card_h, battle, defense=is_defense)
        y0 += section_header_h + rows * card_h + max(0, rows - 1) * gap_y + section_gap

    footer_y = height - 35
    draw.text((width // 2, footer_y), "Data provided by ClashKing API • Not affiliated with Supercell", font=F_TINY, fill=MUTED, anchor="mm")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

# --- ClashKing API ---------------------------------------------------------

TAG_RE = re.compile(r"^#?[0289PYLQGRJCUV]{3,15}$", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

async def fetch_legend_day(tag: str, day: str):
    normalized_tag = tag.strip().upper()
    if not TAG_RE.fullmatch(normalized_tag):
        raise ValueError("Player Tag غير صحيح. تأكد أنه مثل #ABC123 أو #2PP.")
    normalized_tag = normalized_tag.lstrip("#")
    if not DATE_RE.fullmatch(day):
        raise ValueError("التاريخ لازم يكون بصيغة YYYY-MM-DD.")
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise ValueError("التاريخ غير صالح. استخدم YYYY-MM-DD.")

    url = f"{API_BASE}/v2/player/{quote(normalized_tag, safe='')}/legend/{day}/battlelog"
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers={"User-Agent": f"{BRAND}/1.0"}) as response:
            if response.status == 404:
                raise LookupError("ما لقيت بيانات لهذا اللاعب والتاريخ. ممكن اليوم غير مكتمل أو ما انحفظت بياناته.")
            if response.status == 400:
                body = await response.text()
                raise ValueError(f"الـ API رفض الطلب أو التاريخ. {body[:250]}")
            if response.status == 429:
                raise RuntimeError("مصدر البيانات طلب الانتظار بسبب كثرة الطلبات. جرّب بعد دقيقة.")
            if response.status >= 500:
                raise RuntimeError("مصدر البيانات غير متاح مؤقتًا. جرّب لاحقًا.")
            if response.status != 200:
                body = await response.text()
                raise RuntimeError(f"خطأ من مصدر البيانات ({response.status}): {body[:200]}")
            data = await response.json(content_type=None)
            if not isinstance(data, dict):
                raise RuntimeError("وصلت استجابة غير متوقعة من مصدر البيانات.")
            return normalized_tag, data

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        log.info("Logged in as %s; synced %s slash commands", bot.user, len(synced))
    except Exception:
        log.exception("Failed to sync slash commands")
    log.info("Bot is ready.")

@bot.tree.command(name="legend", description="Create a custom Legend League battle-log image")
@app_commands.describe(
    tag="Clash of Clans player tag, e.g. #ABC123",
    day="Legend day in YYYY-MM-DD format; defaults to yesterday (UTC)",
)
async def legend(interaction: discord.Interaction, tag: str, day: str = ""):
    if not day.strip():
        day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    await interaction.response.defer(thinking=True)
    try:
        normalized_tag, data = await fetch_legend_day(tag, day)
        image_buffer = create_battle_image(normalized_tag, day, data)
        filename = f"legend-{normalized_tag}-{day}.png"
        file = discord.File(fp=image_buffer, filename=filename)
        attacks = len(data.get("attacks") or [])
        defenses = len(data.get("defenses") or [])
        embed = discord.Embed(
            title=f"{BRAND} • Legend League",
            description=f"Player `{normalized_tag}` • Day `{day}`\nAttacks: **{attacks}** | Defenses: **{defenses}**",
            color=discord.Color.gold(),
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text="Data: ClashKing API • Historical data may be incomplete")
        await interaction.followup.send(embed=embed, file=file)
    except ValueError as exc:
        await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
    except LookupError as exc:
        await interaction.followup.send(f"ℹ️ {exc}", ephemeral=True)
    except Exception:
        log.exception("Error while handling /legend")
        await interaction.followup.send(
            "صار خطأ أثناء جلب البيانات أو إنشاء الصورة. جرّب مرة ثانية لاحقًا.",
            ephemeral=True,
        )

@bot.tree.command(name="about", description="Show bot data-source information")
async def about(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"**{BRAND}** creates Legend League battle-log images using the public "
        "[ClashKing API](https://api.clashk.ing/docs). Historical records depend on what the API has collected. "
        "This project is unofficial and is not affiliated with Supercell.",
        ephemeral=True,
    )

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and set your bot token.")

bot.run(DISCORD_TOKEN)
