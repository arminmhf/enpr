# طراحی «لایه نامرئی انگلیسی» برای Claude Code — نقد و معماری

> خلاصه یک‌خطی: ایده درست است، ولی **«Skill» ابزار اشتباهی برای یک رفتار همیشه‌روشن است**، و **correction به‌تنهایی speaking را بهتر نمی‌کند**. معماری درست = hook (قطعی) + قوانین کوتاه + لاگ خام + review دسته‌ای با retry از جملات خود کاربر.

---

## ۰. فرض اصلی که اشتباه است

دو فرض در ایده فعلی مشکل دارند:

**۱. «این یک Skill است.»** طبق مستندات رسمی Claude Code، Skill‌ها on-demand هستند: فقط `description` آن‌ها همیشه در context است و بدنه وقتی لود می‌شود که Claude تشخیص دهد مرتبط است. هیچ تضمینی نیست که روی *هر* prompt اجرا شود — و دقیقاً وقتی کاربر غرق کار است (prompt درباره باگ است، نه انگلیسی) احتمال trigger شدنش کمتر است. رفتار همیشه‌روشن باید از جایی بیاید که **قطعی** است:

| مکانیزم | قطعی؟ | هزینه context | قابل toggle | مناسب برای |
|---|---|---|---|---|
| Skill (auto) | ❌ | کم | — | دستورات on-demand (`/english:review`) |
| `~/.claude/CLAUDE.md` | ✅ لود می‌شود | هر session | ❌ (باید فایل را ویرایش کرد) | ساده‌ترین نسخه دستی |
| Output style | ✅ | system prompt | ✅ ولی با بقیه output styleها انحصاری است | اگر output style دیگری استفاده نمی‌کنی |
| **SessionStart hook** | ✅ | یک‌بار در هر session + بعد از compact | ✅ با فایل mode | قوانین کامل |
| **UserPromptSubmit hook** | ✅ هر prompt | باید خیلی کوچک باشد (تجمعی است) | ✅ | یادآوری یک‌خطی + **لاگ قطعی prompt** |

**۲. «Claude در حین کار، pattern را تشخیص بدهد و در memory ذخیره کند.»** این غیرقابل‌اعتماد و پرهزینه است: Claude وسط یک task چندمرحله‌ای باید یک Edit اضافه روی فایل profile بزند (permission prompt، حواس‌پرتی، فراموش‌کردن بعد از compact، ثبت ناسازگار). راه درست: **hook هر prompt را به‌صورت قطعی و با صفر توکن لاگ کند** و تحلیل pattern **دسته‌ای** و فقط وقتی کاربر خواست (`/english:review`) انجام شود. تشخیص pattern از روی ۲۰۰ جمله خیلی دقیق‌تر از قضاوت لحظه‌ای روی یک جمله است.

---

## A. نقد محصول

**آیا English production را بهتر می‌کند؟** فقط writing را، و آن هم کم. خواندن یک correction یعنی *دریافت* ورودی — همان مهارتی که کاربر در آن C1 است. تحقیقات SLA (output hypothesis سوین، تفاوت recast و prompt در corrective feedback) نشان می‌دهد uptake وقتی رخ می‌دهد که یادگیرنده **خودش شکل درست را تولید کند**، نه وقتی شکل درست را ببیند. پس correction لازم است ولی کافی نیست؛ حلقه باید با «دوباره خودت بگو» بسته شود.

**بزرگ‌ترین ضعف:** هیچ‌چیز در طراحی فعلی speaking را تمرین نمی‌دهد. تایپ prompt، writing آهسته و قابل‌ویرایش است؛ speaking تولید real-time است. A2 بودن speaking در کنار C1 بودن reading یعنی مشکل **automaticity** است، نه دانش.

**ارزان‌ترین راه حل برای speaking:** promptها را **دیکته کنی** (dictation سیستم‌عامل، Whisper، یا ورودی صوتی اگر نسخه Claude Code تو دارد). همین یک تغییر، هر prompt را از writing به speaking تبدیل می‌کند و correctionها روی *گفتار* تو می‌آیند. این از هر feature دیگری در این سند اثر بیشتری دارد و صفر خط کد است.

**چرا کاربر بعد از چند روز رها می‌کند:**
1. **False positive** — یک correction اشتباه یا «سلیقه‌ای» اعتماد را از بین می‌برد؛ بعد از آن همه ✎ها نادیده گرفته می‌شوند.
2. **نویز** — اگر تقریباً در هر پاسخ چیزی باشد، به banner blindness می‌رسی.
3. **ناپایداری** — Skill گاهی trigger می‌شود گاهی نه؛ بعد از compact رفتار عوض می‌شود.
4. **عدم احساس پیشرفت** — correction می‌بیند ولی هیچ‌وقت نمی‌فهمد چیزی را «یاد گرفته».
5. **verbosity** — Claude دوست دارد توضیح بدهد؛ پنج خط توضیح grammar بعد از یک bug fix یعنی uninstall.
6. **هزینه نگهداری** — اگر profile را باید دستی مدیریت کرد.

**آیا correction مداوم frustration می‌آورد؟** بله، اگر rate-limit نشود. اهرم اصلی «threshold عددی» نیست، **بودجه** است: حداکثر یک خط، اکثر پاسخ‌ها بدون خط، و هیچ‌وقت وقتی کاربر عجله دارد.

**آیا پاسخ فارسی exposure را کم می‌کند؟** برای این کاربر مهم نیست. گلوگاه input نیست (C1 reading)؛ کاربر هر روز ساعت‌ها docs و کد انگلیسی می‌خواند. پاسخ فارسی بار شناختی را کم می‌کند تا ذهن روی کار بماند. ولی دو قاعده لازم است:
- اصطلاحات فنی، identifierها، پیام‌های خطا **ترجمه نشوند**.
- **هرچه وارد repo می‌شود انگلیسی بماند** (کد، کامنت، commit، PR). بدون این قاعده، فارسی به commit messageها نشت می‌کند — باگ واقعی.

---

## B. Learning design

**مکانیزم درست برای C1 passive / A2 active:** نه آموزش، بلکه **retrieval تحت فشار زمانی** + **chunkها**. کسی که سریع حرف می‌زند قاعده grammar اجرا نمی‌کند؛ قطعه‌های آماده (`I want you to…`, `could you check whether…`, `it looks like…`) را بازیابی می‌کند. پس هر correction باید یک **chunk قابل استفاده مجدد** تحویل دهد، نه یک قاعده انتزاعی.

**Active recall چقدر وارد workflow شود؟** **صفر** در حین کار. هر چیزی که جواب بخواهد، interruption است. Recall فقط در `/english:review` (اختیاری، ۲ دقیقه).

**توضیح grammar کی؟** فقط وقتی:
- همان pattern دوباره تکرار شد (hint ≤ ۸ کلمه فارسی کنار ✎)، یا
- در review (یک خط قاعده برای هر pattern).
هیچ‌وقت پاراگراف.

**Spaced repetition بدون مزاحمت — ایده کلیدی: promptهای خود کاربر تست هستند.** وقتی `want you to + verb` در Active است، Claude در هر prompt حواسش به آن است. کاربر هر روز ده‌ها بار این ساختار را *طبیعتاً* تولید می‌کند. هر بار درست → شاهد mastery؛ هر بار غلط → ✎ با `(تکرار)`. هیچ flashcardی لازم نیست؛ فاصله‌گذاری را خود کار واقعی ایجاد می‌کند. Review فقط حساب‌وکتاب را انجام می‌دهد و pattern را Active → Mastered می‌برد.

**تبدیل passive به active:** «جمله خودت را دوباره بساز». در review، Claude *معنی* یکی از جملات غلط قبلی کاربر را (به فارسی) و context فنی را نشان می‌دهد و کاربر باید جمله انگلیسی را — ترجیحاً با صدای بلند — تولید کند. جمله‌ها مال خود کاربر و درباره پروژه خود اوست؛ هیچ تمرین generic‌ای این‌قدر relevant نیست.

---

## C. UX — «کار اول، یادگیری در پس‌زمینه»

```
تو:      I want you check why the login test fail after the refactor
Claude:  [کار را انجام می‌دهد، به فارسی گزارش می‌دهد]
         ...
         تست fail می‌شد چون mock مربوط به `AuthService` بعد از refactor هنوز مسیر قدیمی را import می‌کرد. اصلاحش کردم و همه تست‌ها پاس می‌شوند.

         ✎ `want you check` → `want you to check` · `fail` → `fails`
```

اصول:
- **جایگاه ثابت**: همیشه آخرین خط پیام نهایی، با علامت ثابت `✎`. چشم یاد می‌گیرد کجا را نگاه کند یا نکند.
- **فقط fragment**، نه کل جمله. diff کوچک = پردازش در یک نگاه.
- **دو علامت**: `→` = غلط. `≈` = قابل‌فهم ولی غیرطبیعی. تفاوت grammar و naturalness در یک کاراکتر — بدون برچسب و توضیح.
- **بدون تعریف، بدون «انگلیسی‌ات عالی بود!»**؛ نبودِ ✎ خودش یعنی درست بود.
- **voice کاربر حفظ می‌شود**: `fix this shit, it completely broken` → `✎ \`it completely broken\` → \`it's completely broken\`` — فحش می‌ماند، فقط فعل اضافه می‌شود.
- **هیچ‌وقت قبل یا وسط کار** و هیچ‌وقت درخواست «دوباره بنویس».
- Progress فقط در review: «`want you to` → Mastered ✓». یک سیگنال پیشرفت واقعی ارزش ده نمودار را دارد.

---

## D. معماری روی قابلیت‌های واقعی Claude Code

بر اساس مستندات فعلی (skills, hooks, plugins, memory, output-styles در code.claude.com/docs):

- **SKILL.md چه دارد؟** فقط دستورهای on-demand. با `disable-model-invocation: true` تا Claude خودش آن‌ها را اجرا نکند (review هزینه دارد و باید انتخاب کاربر باشد). با `` !`command` `` داده (profile، لاگ) قبل از رسیدن به Claude تزریق می‌شود — بدون tool call اضافه.
- **قوانین correction کجا؟** یک فایل (`rules.md`) که **SessionStart hook** یک‌بار در هر session (و دوباره بعد از compact) تزریق می‌کند. ~۹۰۰ توکن، یک‌بار.
- **UserPromptSubmit hook**: (۱) prompt را لاگ می‌کند (قطعی، صفر توکن)، (۲) یک خط یادآوری + حداکثر ۵ Active pattern تزریق می‌کند (~۵۰–۸۰ توکن). این تزریق در transcript تجمع پیدا می‌کند، پس باید ریز بماند — به همین دلیل کل قوانین را هر بار تزریق نمی‌کنیم.
- **Memory کجا؟** فایل، **global/user-level** در `~/.claude/enpr/`:
  - انگلیسی ویژگی *کاربر* است، نه پروژه.
  - project-level یعنی فایل وارد repo تیم می‌شود و هم‌تیمی‌ها ناگهان پاسخ فارسی می‌گیرند — anti-pattern جدی.
  - از auto-memory خود Claude Code استفاده نکن: per-project است و Claude تصمیم می‌گیرد چه بنویسد؛ اینجا قطعیت می‌خواهیم.
- **Context bloat؟** فقط `## Active` (≤۵ خط) به هر prompt می‌رود. Watching، Mastered و لاگ هرگز خودکار لود نمی‌شوند؛ فقط در review.
- **فقط recurring mistakes ذخیره شوند؟** در profile بله. لاگ خام جداست چون ماده خام تحلیل است (و حجمش محدود: ۲۰۰۰ خط، بعد archive با سقف).
- **چه چیزهایی ذخیره نشوند:** کد، stack trace، متن paste‌شده، secretها (redact می‌شوند)، promptهای فارسی، slash commandها، typoها، لیست vocabulary، سطح CEFR به‌عنوان قاعده، نام مشتری/اطلاعات محرمانه پروژه در profile.
- **Slash command لازم است؟** سه تا کافی است: `/english:on`، `/english:off`، `/english:review`. Modeهای light/normal برای مدل قابل‌تفکیک نیستند (Claude فرق «کمی بیشتر correction» را پایدار اجرا نمی‌کند). Practice برای V2.
- **Global یا project؟** Global، به‌صورت **plugin** (hookها + skillها + rules یکجا، نصب با یک دستور، آپدیت با git).
- **جلوگیری از verbosity:** فرمت دقیق و یک‌خطی با مثال، «default = هیچ»، فهرست صریح «Never»، و یادآوری per-prompt که کلمه «at most one» را تکرار می‌کند. مدل‌ها از قالب دقیق بهتر از توصیه «کوتاه باش» پیروی می‌کنند.

```
enpr/
├── .claude-plugin/marketplace.json
└── plugins/english/
    ├── .claude-plugin/plugin.json
    ├── rules.md                  ← قوانین (SessionStart تزریق می‌کند)
    ├── hooks/hooks.json          ← SessionStart + UserPromptSubmit
    ├── scripts/enpr.py           ← لاگ، mode، استخراج Active
    └── skills/
        ├── on/SKILL.md           → /english:on
        ├── off/SKILL.md          → /english:off
        └── review/SKILL.md       → /english:review

~/.claude/enpr/                   ← state کاربر (خارج از هر repo)
├── mode                          on | off
├── profile.md                    Active (≤5, تزریق می‌شود) / Watching / Mastered
├── prompts.jsonl                 لاگ بررسی‌نشده
└── archive.jsonl                 لاگ بررسی‌شده (سقف‌دار)
```

مقایسه با ساختار پیشنهادی تو: `rules/` با ۵ فایل → یک فایل (Claude ۵ فایل قانون را با هم لود نمی‌کند و تقسیمش فقط نگهداری را سخت می‌کند). `commands/` → skillها (commandها در skillها ادغام شده‌اند). `english-stats` → حذف (stats بی‌معنی است؛ review همان progress را نشان می‌دهد).

---

## E. Anti-patterns (کارهایی که نباید بکند)

1. اصلاح typo، نقطه‌گذاری، حروف بزرگ.
2. اضافه‌کردن article به promptهای تلگرافی (`fix login bug` درست است).
3. polish کردن یا رسمی‌کردن لحن؛ حذف فحش؛ «Could you please…».
4. correction متنی که مال کاربر نیست: کد، لاگ، stack trace، پیام خطا، متن paste شده، نام فایل.
5. بیش از یک خط feedback؛ پاراگراف grammar؛ لیست bullet.
6. feedback قبل یا وسط کار، یا اجازه دادن به آن که کیفیت task را کم کند.
7. درخواست از کاربر برای بازنویسی/تکرار در workflow عادی.
8. تعریف و تشویق («انگلیسی‌ات عالی شده!»).
9. آموزش vocabulary یا توضیح اصطلاحات فنی که کاربر هر روز می‌بیند.
10. گزارش «different» به‌عنوان «wrong».
11. نشت فارسی به commit message، کامنت، PR، یا فایل‌های repo.
12. نوشتن در فایل profile وسط task.
13. ذخیره state در repo پروژه، یا ذخیره secret/کد در لاگ.
14. feedback وقتی کاربر زیر فشار است (prod down).
15. تمرین generic («What did you do last weekend?»).

---

## F. معماری بهبودیافته (خلاصه)

**سه لایه، هرکدام با مکانیزم مناسب خودش:**

1. **Capture (قطعی، نامرئی):** UserPromptSubmit hook → لاگ prose کاربر (بدون کد/secret).
2. **Nudge (همیشه، ریز):** قوانین یک‌بار در session + یک خط per-prompt با Active patterns → حداکثر یک ✎ در انتهای پاسخ.
3. **Consolidate (اختیاری، ۲–۵ دقیقه):** `/english:review` → تحلیل دسته‌ای، به‌روزرسانی profile (Active→Mastered)، retry drill از جملات خود کاربر، archive.

حلقه adaptive: review مشخص می‌کند چه چیزی Active باشد → hook آن را به هر prompt می‌برد → Claude روی همان چیزها حساس‌تر است → promptهای بعدی شاهد mastery هستند → review بعدی promote می‌کند. یعنی «adaptive learning» که تو برای V3 گذاشته بودی، با همین ۳ تکه در V1 به‌دست می‌آید.

---

## G. Specification نسخه V1

**هدف:** کاربر بدون تغییر workflow، انگلیسی می‌نویسد (یا دیکته می‌کند)، پاسخ فارسی می‌گیرد، و گاهی یک خط feedback پرارزش؛ و با review اختیاری، الگوهای تکراری‌اش را می‌بیند و فعالانه تمرین می‌کند.

**رفتار:**
- پاسخ‌های نثری به فارسی؛ اصطلاحات فنی دست‌نخورده؛ خروجی‌های repo انگلیسی.
- prompt فارسی → پاسخ فارسی، بدون feedback، بدون لاگ.
- حداکثر یک ✎ در انتهای پیام نهایی turn؛ default = هیچ.

**Triggerها:**
- SessionStart (`startup|resume|clear|compact`) → تزریق `rules.md` اگر mode=on.
- UserPromptSubmit → لاگ + یادآوری یک‌خطی (یا پیام OFF).
- `/english:on`، `/english:off`، `/english:review [quick]` — فقط دستی.

**Priority:** Active patterns > ساختار جمله (to-infinitive، فاعل حذف‌شده، ترتیب سؤال/سؤال غیرمستقیم) > زمان/فرم فعل/مطابقه > calque حرف اضافه > chunk غیرطبیعی پرتکرار > article (فقط اگر Active باشد) > vocabulary (هرگز در V1).

**نقد ranking تو:** ranking بر اساس *دسته* (grammar، articles، …) معیار اشتباهی است؛ معیار درست **تکرار × اثر روی فهم × آمادگی یادگیری** است. مثلاً articles برای فارسی‌زبان پرتکرارترین خطاست (فارسی article ندارد) ولی کم‌اثر و دیر-اکتسابی است؛ اگر هر article اصلاح شود، نصف ✎ها article خواهد بود و نویز می‌شود. برعکس، «natural phrasing / collocation» که تو رتبه ۷–۸ دادی، برای *speaking* از grammar مهم‌تر است چون fluency از chunkها می‌آید. پس: ساختار و chunkهای پرتکرار بالا، articles پایین مگر pattern شود.

**Correction rules / Learning threshold:** به‌جای مقیاس ۰–۵ (مدل نمی‌تواند پایدار به جمله نمره بدهد و دقت کاذب است)، یک **قاعده سه‌شرطی + بودجه**:
1. خطای واقعی ساختاری یا chunk پرتکرار غیرطبیعی؛
2. یک توسعه‌دهنده native دقیق آن را غلط/واضحاً غیرطبیعی بداند — نه «من طور دیگری می‌گفتم»؛
3. typo/نقطه‌گذاری/سبک تلگرافی/لحن/متن غیرکاربر نباشد.
+ حداکثر یک خط، حداکثر دو fragment، skip در شرایط فشار.
عملاً سطوح ۰–۲ تو = «نمایش نده» و ۳–۵ = «نمایش بده»؛ فقط مرز را به‌صورت معیار کیفی تعریف کردیم.

**Pattern detection:** دسته‌ای در review. pattern = ≥۳ وقوع (≥۲ برای خطای ساختاری). Mastered = Active بوده + ≥۳ استفاده درست اخیر بدون خطای جدید. در session، تکرار با `(تکرار)` علامت می‌خورد (از روی context همان session).

**Memory strategy:** بالا (بخش D). Active ≤ ۵ خط ≤ ۱۰۰ کاراکتر؛ تنها چیزی که per-prompt می‌رود.

**Output format:**
```
✎ `wrong fragment` → `fixed fragment` · راهنمای فارسی ≤۸ کلمه (اختیاری)
✎ `make a research` ≈ `do some research`
✎ `want you check` → `want you to check` (تکرار)
```

**Failure modes و پاسخ طراحی:**
| خرابی | جلوگیری |
|---|---|
| correction غلط/سلیقه‌ای | شرط ۲ + «Different is not wrong» + `≈` جدا از `→` |
| نویز زیاد | default=هیچ، یک خط، skip تحت فشار |
| فراموشی قوانین در session طولانی | تزریق مجدد بعد از compact + یادآوری per-prompt |
| فارسی در commit | قاعده صریح «repo = English» |
| correction روی لاگ/کد | قاعده + فیلتر لاگ در hook |
| secret در لاگ | redact + فقط local در `~/.claude` |
| hook خراب کار را متوقف کند | اسکریپت همیشه exit 0 و timeout ۱۰ ثانیه |
| لاگ بی‌نهایت | سقف ۲۰۰۰ خط + archive با سقف ۳۰۰۰ |
| کاربر review نکند | `/english:on` وقتی ≥۴۰ prompt جمع شده، یک‌خطی پیشنهاد می‌دهد؛ ✎ بدون review هم کار می‌کند |

**نمونه interactionها:**

```
> fix the login bug and check if there is any other bugs related to authentication
[کار…] باگ لاگین در `session.ts` بود: توکن refresh بعد از expire دوباره ذخیره نمی‌شد. دو مشکل مرتبط دیگر هم در `authMiddleware` پیدا و اصلاح کردم…
✎ `there is any other bugs` → `there are any other bugs`
```
```
> Can you take a look at this?
[کار…] — بدون ✎ (طبیعی است)
```
```
> prod is down!! why this endpoint return 500
[کار…] — بدون ✎ (فشار؛ با وجود دو خطا)
```
```
> I want to know the reason of this behavior
[کار…]
✎ `the reason of this behavior` ≈ `why this is happening`
```
```
> fix this shit, it completely broken
[کار…]
✎ `it completely broken` → `it's completely broken`
```
```
> /english:review
الگوهای اصلی این هفته:
1. want/need + you + **to** + فعل — ۹ بار (مثال تو: "I need you fix the migration" → "I need you to fix the migration")
2. فاعل حذف‌شده — ۶ بار ("is not working after deploy" → "it's not working after deploy")
✓ `there is/are` → Mastered (۱۱ بار درست از review قبلی)
تمرین ۱/۳ — با صدای بلند بگو، بعد تایپ کن:
«ازش بخواه دلیل fail شدن تست‌های CI رو پیدا کنه» (context: pipeline امروز)
```

---

## نسخه‌بندی پیشنهادی (جابه‌جایی نسبت به roadmap تو)

- **V1:** پاسخ فارسی + ✎ + **لاگ قطعی + profile + `/english:review` با retry drill** + on/off. (pattern tracking بدون review بی‌ارزش است؛ retry بدون آن، speaking را تکان نمی‌دهد. «adaptive» عملاً با حلقه Active در V1 حاضر است.) + توصیه dictation.
- **V2:** `/english:practice` context-aware (از `git diff`/task جاری: «این تغییر را در ۲ جمله توضیح بده»، «commit message را خودت بنویس» — commit message واقعی‌ترین تمرین writing است)، speaking drill با محدودیت زمان، ۲–۳ آیتم warm-up اختیاری در review از Mastered قدیمی (spaced).
- **V3:** فقط اگر V1/V2 واقعاً استفاده شدند: روند زمانی خطاها، تنظیم خودکار سخت‌گیری بر اساس نرخ خطا، ارزیابی گفتار از transcript صوتی.
- **حذف:** modeهای light/normal، `english-stats`، profile با سطح CEFR.

---

## H. اگر برای خودم می‌ساختم

**حذف می‌کردم:**
- «Skill» به‌عنوان هسته؛ چهار mode؛ threshold عددی ۰–۵؛ `rules/` چندفایلی؛ stats؛ ثبت pattern توسط Claude وسط کار؛ سطح CEFR در profile؛ هر آموزش vocabulary.

**اضافه می‌کردم:**
- **Hook برای capture قطعی** و تزریق ریز per-prompt.
- **Retry از جملات خود کاربر** (تنها مکانیزمی که passive را active می‌کند).
- **Mastered** به‌عنوان تنها سیگنال پیشرفت — بر اساس شواهد از promptهای واقعی.
- **Dictation به‌جای تایپ** — بزرگ‌ترین اهرم برای A2 speaking، بدون هزینه.
- قاعده «repo = English» و redact کردن secret.

**کاملاً متفاوت طراحی می‌کردم:**
- **Pattern detection:** از «inline و لحظه‌ای» به «دسته‌ای و شواهدمحور».
- **Spaced repetition:** از «سیستم flashcard» به «کار روزمره خودش تست است».
- **معیار correction:** از «دسته grammar» به «تکرار × اثر × chunk قابل استفاده مجدد»، و articles از اولویت بالا به «فقط اگر pattern شد».
- **هدف محصول:** از «اصلاح انگلیسی» به «خودکارسازی ۲۰–۳۰ ساختار پرتکرار در گفتار کاری». این عدد کوچک و قابل‌اندازه‌گیری است و بیشترِ خطاهای واقعی کاربر را پوشش می‌دهد.

---

## پیاده‌سازی فازهای بعدی (V2 + بخش‌های مفید V3)

### چه چیزی اضافه شد

| قابلیت | کجا | چرا این شکل |
|---|---|---|
| `/english:practice` | `skills/practice` | ۳ تمرین کوتاه از کار واقعی: `git diff`، commitهای اخیر و آخرین درخواست‌های خودت در همین پروژه. هر Active pattern حداقل یک تمرین دارد که مجبورت می‌کند همان ساختار را بسازی (مثلاً برای `want you to` تمرین «از هم‌تیمی بخواه…»). اول با صدای بلند، بعد ارسال؛ ✎ حداکثر ۲ خط + یک نسخه طبیعی هم‌اندازه جواب خودت + فقط یک retry. |
| Spaced re-check | `enpr.py due` + review | الگوی Mastered فراموش نمی‌شود: بعد از ۷، ۲۱، ۶۰ و ۱۵۰ روز دوباره چک می‌شود. اول از promptهای واقعی‌ات: اگر در این فاصله ساختار را درست به کار برده باشی، بدون سؤال پاس می‌شود. فقط اگر شاهدی نباشد یک سؤال تولیدی می‌آید. Fail → برگشت به Active. تاریخ‌ها را script حساب می‌کند، نه مدل. |
| Progress tracking | `enpr.py record` / `trend` | هر review تعداد خطا و استفاده درست هر pattern را ثبت می‌کند. روند به‌صورت «خطا در هر ۱۰۰ prompt» نمایش داده می‌شود (`want-to: 20 → 5`)، چون تعداد مطلق به تعداد promptها وابسته است. |
| Nudge روزانه | UserPromptSubmit | حداکثر یک بار در روز، وقتی ۴۰ prompt جمع شده یا re-check موعدش رسیده، یک خط فارسی پیشنهاد review. وقتی تحت فشاری نمایش داده نمی‌شود. این جواب «کاربر review نمی‌کند» در جدول failure modeهاست. |
| Tests | `tests/test_enpr.py` | لاگ و فیلتر secret، حالت off، تزریق Active، زمان‌بندی due، nudge یک‌بار در روز، trend. |

### چیزهایی که عمداً ساخته نشدند

- **سخت‌گیری خودکار (adaptive strictness):** همان مشکل modeهای light/normal را دارد؛ مدل «کمی سخت‌گیرتر» را پایدار اجرا نمی‌کند. سازگاری واقعی سیستم همین است که چه چیزی در Active باشد. این قطعی است و از شواهد می‌آید.
- **ارزیابی تلفظ یا گفتار صوتی:** Claude Code صدا را تحلیل نمی‌کند. فقط متن دیکته‌شده را می‌بیند، که برای grammar گفتاری کافی است.
- **تمرین commit message وسط workflow** (اینکه Claude قبل از commit بگوید «خودت بنویس»): interruption است. در `/english:practice commit` هست، هر وقت خودت بخواهی.
- **Dashboard یا نمودار:** یک خط trend در review کافی است. هر چیز بیشتر یعنی ابزار آموزش زبان، که دقیقاً چیزی است که نمی‌خواستیم.

### چرخه کامل

```
کار روزمره ──(hook: لاگ + ✎)──▶ prompts.jsonl
     ▲                                  │
     │                     /english:review (یا nudge)
     │                                  ▼
 Active patterns ◀── profile.md ◀── تحلیل دسته‌ای + record در history
 (هر prompt)          │                 │
     ▲                │ Mastered + تاریخ │ retry از جملات خودت
     │                ▼                  ▼
/english:practice ◀── re-check در ۷/۲۱/۶۰/۱۵۰ روز
(تمرین هدفمند روی Active)
```
