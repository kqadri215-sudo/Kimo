# Karim Clash — Discord Legend League Bot

بوت Discord بلغة Python يستقبل Player Tag ويطلب سجل يوم محدد من Legend League من ClashKing API، ثم ينشئ صورة PNG بتصميم مخصص باسم **Karim Clash**.

> تنبيه: بيانات Legend League التاريخية تأتي من ClashKing API، وهي خدمة تجمع البيانات من خلال الاستعلام الدوري عن واجهات اللعبة. قد لا تتوفر بيانات كل لاعب أو كل يوم. البوت لا يستطيع استعادة سجل لم يتم جمعه مسبقًا. اذكر ClashKing كمصدر للبيانات، وهذا المشروع غير تابع لـ Supercell.

## الأوامر

- `/legend tag:#PLAYER day:YYYY-MM-DD` — ينشئ صورة سجل يوم محدد.
- `/legend tag:#PLAYER` — يستخدم يوم أمس بتوقيت UTC افتراضيًا.
- `/about` — يعرض معلومات مصدر البيانات.

## 1. إنشاء بوت Discord

1. افتح https://discord.com/developers/applications
2. اختر **New Application** وسمّه `Karim Clash`.
3. من تبويب **Bot** أنشئ البوت وانسخ **Token**. لا ترسل هذا الرمز لأي شخص ولا ترفعه إلى GitHub.
4. من **OAuth2 → URL Generator** اختر:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Attach Files`, `Embed Links`
5. افتح رابط الدعوة الذي تم توليده وأضف البوت إلى سيرفرك.

لا يحتاج هذا المشروع إلى تفعيل Message Content Intent.

## 2. التشغيل محليًا للاختبار

تحتاج Python 3.11 أو أحدث.

### Windows PowerShell

```powershell
cd karim_clash_discord_bot
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

ضع Token البوت في `DISCORD_TOKEN` واحفظ الملف، ثم شغّل:

```powershell
python main.py
```

إذا ظهرت رسالة `Bot is ready` افتح Discord واكتب `/legend`. قد يستغرق ظهور أوامر Slash بضع لحظات بعد أول تشغيل.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

## 3. الاستضافة 24/7 باستخدام Docker

يمكنك استخدام أي استضافة تدعم Docker وعمليات Worker طويلة التشغيل. لا تستخدم استضافة serverless قصيرة العمر لهذا البوت، لأنه يحتاج اتصال Gateway دائمًا مع Discord.

### خيارات عامة

- خادم VPS مع Docker: تحكم أكبر، لكنك مسؤول عن تحديث النظام وتشغيل الخدمة.
- منصة استضافة تدعم Docker Worker: أسهل، لكن تحقق من السعر وسياسة التشغيل المستمر قبل الاختيار.

### نشر على VPS باستخدام Docker

1. ثبّت Docker وDocker Compose على الخادم.
2. ارفع ملفات المشروع إلى الخادم.
3. أنشئ ملف `.env` يحتوي على `DISCORD_TOKEN` و`BRAND_NAME=Karim Clash`.
4. شغّل:

```bash
docker build -t karim-clash-bot .
docker run -d --name karim-clash-bot --restart unless-stopped --env-file .env karim-clash-bot
```

لمشاهدة السجلات:

```bash
docker logs -f karim-clash-bot
```

لإيقافه:

```bash
docker stop karim-clash-bot
```

للتحديث، أوقف الحاوية واحذفها، ارفع الملفات الجديدة، ثم أعد البناء والتشغيل.

## 4. استضافة عبر Render

يوجد ملف `render.yaml` كقالب إرشادي. أنشئ خدمة Worker من مستودع المشروع مع Docker، ثم أضف متغير البيئة `DISCORD_TOKEN` من لوحة التحكم. تأكد من اختيار خطة تدعم التشغيل المستمر؛ توافر الخطط والأسعار يتغير وقد لا تكون الخطة المجانية مناسبة لبوت 24/7.

لا تضع Token داخل ملف `render.yaml` أو داخل الكود.

## 5. كيف تعمل بيانات Legend League؟

يستخدم البوت endpoint العام التالي:

`GET https://api.clashk.ing/v2/player/{playerTag}/legend/{day}/battlelog`

الاستجابة المتوقعة تتضمن بيانات اليوم مثل `attackTrophies`, `defenseTrophies`, `trophies`, `attacks` و`defenses`. كل سجل قد يحتوي النجوم ونسبة التدمير واسم الخصم والكؤوس.

المصدر والتوثيق:
- https://api.clashk.ing/docs
- https://github.com/ClashKingInc/ClashKingAPI

إذا أعاد المصدر `404`، فهذا يعني غالبًا أن بيانات اللاعب/اليوم غير موجودة أو غير متاحة؛ جرّب يومًا آخر. لا يعني ذلك بالضرورة أن اللاعب لم يهاجم.

## 6. ملاحظات مهمة

- التاريخ بصيغة `YYYY-MM-DD`.
- اليوم الافتراضي هو أمس حسب UTC، لتقليل احتمال طلب يوم لم يكتمل.
- الصورة تعرض كل السجلات التي ترجعها الخدمة؛ إذا رجع المصدر أقل من 8 هجمات أو دفاعات، لن يخترع البوت سجلات إضافية.
- لا تستخدم أسماء أو أصول اللعبة بطريقة توحي بأن البوت رسمي.
- عند ظهور خطأ، افحص `docker logs` أو نافذة الطرفية.
