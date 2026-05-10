import logging
import os
import asyncio
import uuid
import aiohttp
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.chat_action import ChatActionSender
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

from config import BOT_TOKEN, DOWNLOAD_DIR, BASE_DIR, HEADERS, ADMIN_IDS
from extractors.universal_loader import get_universal_media
from database import init_db, get_file_id, save_file_id, add_user, get_all_users, get_users_count
from extractors.youtube_utils import get_yt_formats, download_yt_by_quality

# Professional Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "bot.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Katta fayllar va albomlar yuborishda uzilish bo'lmasligi uchun kutish vaqtini (timeout) uzaytiramiz
# PythonAnywhere bepul tarifi uchun avtomatik proksi sozlamasi (Kompyuteringizda xato bermaydi)
PROXY_URL = "http://proxy.server:3128" if "PYTHONANYWHERE_SITE" in os.environ else None

# Standart Telegram API serveridan foydalanamiz
session = AiohttpSession(proxy=PROXY_URL, timeout=300) # Timeoutni optimallashtiramiz
bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# Global variables to store bot info (fetched once at startup)
BOT_USERNAME = None
BOT_FULL_NAME = None

# Bir vaqtning o'zida ishlov berish limitini biroz oshiramiz (Serverga qarab 10-20 ideal)
download_semaphore = asyncio.Semaphore(15) 

# YouTube sifatini tanlash uchun CallbackData Factory
class YouTubeCallback(CallbackData, prefix="yt"):
    quality: str
    vid: str

# Admin uchun reklama yuborish holatlari
class AdminStates(StatesGroup):
    waiting_for_reklama = State()

# Yordam xabarining matni
HELP_MESSAGE_TEXT = (
    "❓ **Yordam bo'limi**\n\n"
    "Men hozircha faqat quyidagi platformalardan video yuklab bera olaman:\n"
    "🔹 **Instagram** (Reels, Post, Story)\n"
    "🔹 **YouTube** (Video, Shorts, Audio)\n\n"
    "Iltimos, Instagram yoki YouTube'dan video linkini yuboring!"
)

async def download_file_async(url: str, m_type: str) -> str:
    """Media fayllarni asinxron yuklab olish uchun universal yordamchi funksiya"""
    ext = "mp4" if m_type == 'video' else "jpg"
    fname = f"media_{uuid.uuid4().hex[:6]}.{ext}"
    fpath = os.path.join(DOWNLOAD_DIR, fname)
    
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url, headers=HEADERS, proxy=PROXY_URL, timeout=300) as r:
                r.raise_for_status() # HTTP xatolarini tekshirish
                with open(fpath, 'wb') as f:
                    async for chunk in r.content.iter_chunked(1024*1024): # 1 MB chunks
                        f.write(chunk)
        return fpath
    except aiohttp.ClientError as e:
        logger.error(f"Faylni yuklashda tarmoq xatosi: {e}")
        raise # Xatoni yuqoriga uzatish
    except Exception as e:
        logger.error(f"Faylni yuklashda noma'lum xato: {e}")
        raise # Xatoni yuqoriga uzatish

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id) # Foydalanuvchini bazaga qo'shish

    reply_markup = None
    # Admin tugmasi (faqat adminlar uchun)
    if message.from_user.id in ADMIN_IDS:
        builder = InlineKeyboardBuilder()
        builder.button(text="⚙️ Admin Panel", callback_data="admin_panel")
        reply_markup = builder.as_markup()

    await message.answer(
        f"👋 Salom {message.from_user.full_name}!\n\n"
        f"🚀 **{BOT_FULL_NAME}**ga xush kelibsiz.\n"
        "Menga video linkini yuboring",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# /help buyrug'i yuborilganda ishlaydigan handler
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(HELP_MESSAGE_TEXT, parse_mode=ParseMode.MARKDOWN)

# Yordam tugmasi bosilganda ishlaydigan handler
@dp.callback_query(F.data == "help_command")
async def handle_help_button(query: types.CallbackQuery):
    await query.message.edit_text(
        "❓ **Yordam bo'limi**\n\n"
        "Men hozircha faqat quyidagi platformalardan video yuklab bera olaman:\n"
        "🔹 **Instagram** (Reels, Post, Story)\n"
        "🔹 **YouTube** (Video, Shorts, Audio)\n\n"
        "Iltimos, Instagram yoki YouTube'dan video linkini yuboring!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=query.message.reply_markup # Tugmalarni saqlab qolish
    )
    await query.answer() # Callback query ni yopish

# Admin tugmasi bosilganda ishlaydigan handler
@dp.callback_query(F.data == "admin_panel")
async def handle_admin_button(query: types.CallbackQuery):
    if query.from_user.id in ADMIN_IDS:
        count = get_users_count()
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Reklama tarqatish", callback_data="start_reklama")
        builder.adjust(1)
        
        await query.message.edit_text(
            f"⚙️ **Admin Panel**\n\n👤 Foydalanuvchilar soni: {count} ta",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
    else:
        await query.answer("Siz admin emassiz!", show_alert=True)
    await query.answer() # Callback query ni yopish

@dp.callback_query(F.data == "start_reklama")
async def start_reklama(query: types.CallbackQuery, state: FSMContext):
    if query.from_user.id in ADMIN_IDS:
        await query.message.answer("📣 Reklama xabarini yuboring (Matn, rasm, video yoki boshqa).\n\nBekor qilish uchun /cancel yuboring.")
        await state.set_state(AdminStates.waiting_for_reklama)
    await query.answer()

@dp.message(AdminStates.waiting_for_reklama)
async def process_reklama(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Reklama bekor qilindi.")
        return

    users = get_all_users()
    success = 0
    failed = 0
    
    status_msg = await message.answer(f"🚀 Reklama yuborish boshlandi: {len(users)} ta foydalanuvchiga...")
    
    for user_id in users:
        try:
            # Har qanday xabarni (rasm, video, matn) formatini buzmasdan nusxalash
            await message.copy_to(chat_id=user_id)
            success += 1
            # Telegram limitlariga tushib qolmaslik uchun kichik tanaffus
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        f"✅ **Reklama tarqatish yakunlandi!**\n\n"
        f"🟢 Yuborildi: {success}\n"
        f"🔴 Xatolik (botni bloklagan): {failed}",
        parse_mode=ParseMode.MARKDOWN
    )
    await state.clear()

# YouTube uchun alohida handler
@dp.message(F.text.regexp(r'(https?://(?:www\.)?(?:youtube\.com/|youtu\.be/)[^\s]+)'))
async def handle_youtube_link(message: types.Message):
    # Xabar ichidan YouTube linkini qidirib topamiz
    match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/|youtu\.be/)[^\s]+)', message.text)
    if not match:
        return
    url = match.group(1)
    
    wait_msg = await message.answer("⏳")

    # Mavjud formatlarni olish
    formats_info = await asyncio.to_thread(get_yt_formats, url)
    
    if not formats_info.get("status"):
        await wait_msg.edit_text(f"⚠️ Xatolik: {formats_info.get('error', 'Noma`lum xato')}")
        return

    # Agar bu Shorts video bo'lsa, tugmalarsiz to'g'ridan-to'g'ri 720p da yuklaymiz
    # Foydalanuvchi talabiga binoan: Shorts uchun faqat audio yuklash tugmasini chiqaramiz
    if formats_info.get("is_short"):
        builder = InlineKeyboardBuilder()
        vid = formats_info.get("vid")
        builder.button(
            text="🎵 Audio (m4a)",
            callback_data=YouTubeCallback(quality='audio', vid=vid).pack()
        )
        builder.adjust(1) # Faqat bitta tugma
        
        await wait_msg.delete() # Eski kutish xabarini o'chiramiz
        caption_text = f"**Shorts video:** `{formats_info['title']}`\n\nFaqat audio yuklab olishingiz mumkin:"
        await message.answer(text=caption_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)
        return

    # Oddiy videolar uchun sifat tanlash tugmalarini yasaymiz
    builder = InlineKeyboardBuilder()
    vid = formats_info.get("vid")
    for fmt in formats_info["formats"]:
        quality = fmt['quality']
        text = f"🎬 {quality}" if quality != 'audio' else "🎵 Audio (m4a)"
        
        builder.button(
            text=text,
            callback_data=YouTubeCallback(quality=quality, vid=vid).pack()
        )
    
    builder.adjust(2) # Har qatorda 2 ta tugma
    
    await wait_msg.delete() # Eski kutish xabarini o'chiramiz
    caption_text = f"**Video:** `{formats_info['title']}`\n\nYuklab olish uchun formatni tanlang:"
    
    if formats_info.get("thumbnail"):
        try:
            await message.answer_photo(
                photo=formats_info["thumbnail"],
                caption=caption_text,
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Rasm yuborishda xatolik (Matn yuborilmoqda): {e}")
            await message.answer(text=caption_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(text=caption_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

# YouTube sifatini tanlash tugmasi bosilganda ishlaydigan handler
@dp.callback_query(YouTubeCallback.filter())
async def handle_youtube_quality(query: types.CallbackQuery, callback_data: YouTubeCallback):
    status_text = "⏳ **Tanlangan sifatda yuklanmoqda...**"
    
    if query.message.caption or query.message.photo:
        await query.message.edit_caption(caption=status_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await query.message.edit_text(text=status_text, parse_mode=ParseMode.MARKDOWN)
    
    url = f"https://youtu.be/{callback_data.vid}"
    quality = callback_data.quality
    
    action = ChatAction.UPLOAD_VIDEO if quality != 'audio' else ChatAction.UPLOAD_DOCUMENT
    
    async with ChatActionSender(bot=bot, chat_id=query.from_user.id, action=action):
        async with download_semaphore:
            result = await asyncio.to_thread(download_yt_by_quality, url, quality)
            
        if result.get("status"):
            try:
                file_size = os.path.getsize(result["file_path"]) / (1024 * 1024)
                if file_size > 50:
                    await query.message.edit_text(f"⚠️ **Fayl juda katta ({file_size:.1f} MB)**. Limit 50MB.", parse_mode=ParseMode.MARKDOWN)
                    return

                file_input = types.FSInputFile(result["file_path"])
                caption = f"🚀 @{BOT_USERNAME} orqali yuklandi."
                
                if quality == 'audio': await query.message.answer_audio(audio=file_input, caption=caption)
                else: await query.message.answer_video(video=file_input, caption=caption)
                
                await query.message.delete()
            except Exception as e:
                logger.error(f"YouTube faylini yuborishda xato: {e}")
                await query.message.answer("❌ Faylni yuborishda xatolik yuz berdi.")
            finally:
                if os.path.exists(result["file_path"]):
                    try:
                        os.remove(result["file_path"])
                    except Exception as e:
                        logger.error(f"Faylni o'chirishda xatolik: {e}")
        else:
            await query.message.edit_text(f"⚠️ **Xatolik:** {result.get('error', 'Noma`lum xato')}", parse_mode=ParseMode.MARKDOWN)

# Barcha qo'llab-quvvatlanadigan platformalar uchun universal handler
@dp.message(F.text.regexp(r'(https?://(?:www\.)?(?:instagram\.com/|tiktok\.com/|vm\.tiktok\.com/|vt\.tiktok\.com/|pinterest\.com/|pin\.it/|snapchat\.com/|threads\.net/)[^\s]+)'))
async def handle_universal(message: types.Message):
    # Xabar ichidan qo'llab-quvvatlanadigan linkni qidirib topamiz
    match = re.search(r'(https?://(?:www\.)?(?:instagram\.com/|tiktok\.com/|vm\.tiktok\.com/|vt\.tiktok\.com/|pinterest\.com/|pin\.it/|snapchat\.com/|threads\.net/)[^\s]+)', message.text)
    if not match:
        return
    
    url = match.group(1)
    logger.info(f"Universal handler triggered for URL: {url}")
    
    # Avval bazadan tekshiramiz
    cached_file = get_file_id(url)
    if cached_file:
        file_id, media_type = cached_file
        caption = f"🚀 @{BOT_USERNAME} orqali yuklandi."
        try:
            if media_type == "video":
                await message.answer_video(
                    video=file_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif media_type == "photo":
                await message.answer_photo(
                    photo=file_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif media_type == "audio":
                await message.answer_audio(
                    audio=file_id,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        except Exception as e:
            logger.error(f"Keshdan yuborishda xato, qayta yuklanadi: {e}")
            
    # Yuklash statusini ko'rsatish
    async with ChatActionSender.upload_document(bot=bot, chat_id=message.chat.id):
        wait_msg = await message.answer("⏳ **Yuklanmoqda...**", parse_mode=ParseMode.MARKDOWN)
        
        # Navbat bilan yuklash (Semaphore). Agar 3 ta odam yuklayotgan bo'lsa, 4-odam kutib turadi
        async with download_semaphore:
            result = await asyncio.to_thread(get_universal_media, url)
        
        if result["status"]:
            try:
                if "media_urls" in result:
                    # Karusel yoki yagona post (Ketma-ket yuklash va yuborish)
                    urls = result["media_urls"]
                    media_group = []
                    caption = f"🚀 @{BOT_USERNAME} orqali yuklandi."
                    
                    for idx, media in enumerate(urls):
                        media_caption = caption if idx == 0 else ""
                        if media['type'] == 'video':
                            media_group.append(types.InputMediaVideo(media=media['url'], caption=media_caption, parse_mode=ParseMode.MARKDOWN))
                        else:
                            media_group.append(types.InputMediaPhoto(media=media['url'], caption=media_caption, parse_mode=ParseMode.MARKDOWN))
                    
                    try:
                        sent_messages = await message.answer_media_group(media=media_group)
                        await wait_msg.delete()
                        
                        # Keshga saqlash (birinchi media uchun)
                        if sent_messages and len(urls) == 1:
                            first_msg = sent_messages[0]
                            if first_msg.video:
                                save_file_id(url, first_msg.video.file_id, "video")
                            elif first_msg.photo:
                                save_file_id(url, first_msg.photo[-1].file_id, "photo")
                                
                    except Exception as e:
                        logger.error(f"MediaGroup yuborishda xato (Direct): {e}. Fayllarni yuklab ko'ramiz...")
                        # Agar direct link o'tmasa, bitta-bitta yuborish mantiqi saqlanadi (eskicha usul)
                        await wait_msg.edit_text("⚠️ To'g'ridan-to'g'ri yuborib bo'lmadi, qayta ishlanmoqda...", parse_mode=ParseMode.MARKDOWN)
                        
                        first_file_id = None
                        first_media_type = None
                        
                        for idx, media in enumerate(urls):
                            try:
                                current_caption = caption if idx == 0 else ""
                                file_path = await download_file_async(media['url'], media['type'])
                                media_input = types.FSInputFile(file_path)
                                
                                sent_msg = None
                                if media['type'] == 'video':
                                    sent_msg = await message.answer_video(video=media_input, caption=current_caption, parse_mode=ParseMode.MARKDOWN)
                                else:
                                    sent_msg = await message.answer_photo(photo=media_input, caption=current_caption, parse_mode=ParseMode.MARKDOWN)
                                
                                # Bazaga birinchi media ID sini kesh qilish
                                if sent_msg:
                                    if media['type'] == 'video' and idx == 0 and sent_msg.video:
                                        first_file_id = sent_msg.video.file_id
                                        first_media_type = "video"
                                    elif media['type'] == 'photo' and idx == 0 and sent_msg.photo:
                                        first_file_id = sent_msg.photo[-1].file_id
                                        first_media_type = "photo"
                            except Exception as download_send_err:
                                logger.error(f"{idx+1}-mediani yuklash/yuborishda xato: {download_send_err}")
                                await message.answer(f"❌ {idx+1}-mediani yuklash/yuborishda xatolik yuz berdi.")
                            finally:
                                if 'file_path' in locals() and os.path.exists(file_path):
                                    os.remove(file_path)
                        
                        await wait_msg.delete() # Delete the "re-processing" message
                        
                        # Agar post 1 ta rasmdan iborat bo'lsa, bazaga kesh qilamiz (for fallback)
                        if len(urls) == 1 and first_file_id:
                            save_file_id(url, first_file_id, first_media_type)
                else:
                    # Boshqa platformalar (YouTube, TikTok, va hk. - yt-dlp dan keladi)
                    file_path = result["file_path"]
                    file_size = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size > 50:
                        await wait_msg.edit_text(f"⚠️ **Fayl juda katta ({file_size:.1f} MB)**. Limit 50MB.", parse_mode=ParseMode.MARKDOWN)
                        return

                    ext = file_path.split('.')[-1].lower()
                    media_input = types.FSInputFile(file_path)
                    
                    sent_msg = None
                    media_type = "document"
                    caption = f"🚀 @{BOT_USERNAME} orqali yuklandi."
                    
                    if ext in ['mp4', 'mkv', 'webm', 'mov']:
                        sent_msg = await message.answer_video(video=media_input, caption=caption, parse_mode=ParseMode.MARKDOWN)
                        media_type = "video"
                    elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                        sent_msg = await message.answer_photo(photo=media_input, caption=caption, parse_mode=ParseMode.MARKDOWN)
                        media_type = "photo"
                    elif ext in ['mp3', 'm4a', 'wav']:
                        sent_msg = await message.answer_audio(audio=media_input, caption=caption, parse_mode=ParseMode.MARKDOWN)
                        media_type = "audio"
                    else:
                        sent_msg = await message.answer_document(document=media_input, caption=caption, parse_mode=ParseMode.MARKDOWN)

                    await wait_msg.delete()
                    
                    # Yagona faylni bazaga kesh qilish
                    if sent_msg:
                        file_id = None
                        if media_type == "video" and sent_msg.video: file_id = sent_msg.video.file_id
                        elif media_type == "photo" and sent_msg.photo: file_id = sent_msg.photo[-1].file_id
                        elif media_type == "audio" and sent_msg.audio: file_id = sent_msg.audio.file_id
                        elif media_type == "document" and sent_msg.document: file_id = sent_msg.document.file_id
                        
                        if file_id:
                            save_file_id(url, file_id, media_type)
            except Exception as e:
                logger.error(f"Telegramga yuborishda xato: {e}")
                await wait_msg.edit_text("❌ Telegramga yuborishda xatolik yuz berdi (Fayl hajmi katta yoki format mos kelmadi).")
            finally:
                # Faylni o'chirish (Serverni to'ldirib yubormaslik uchun)
                if "file_path" in result and os.path.exists(result["file_path"]):
                    try:
                        os.remove(result["file_path"])
                    except Exception as e:
                        logger.error(f"Faylni o'chirishda xatolik yuz berdi: {e}")
        else:
            error_msg = result.get("error", "Noma'lum xatolik")
            logger.warning(f"Yuklash xatosi (Terminal uchun): {error_msg}")
            await wait_msg.edit_text(f"⚠️ **Xatolik:** {error_msg}", parse_mode=ParseMode.MARKDOWN)

@dp.message()
async def handle_unknown_messages(message: types.Message):
    """Tushunarsiz xabarlar yoki linklar kelganda javob qaytarish"""
    await message.answer(
        "😔 Kechirasiz, bu xabarni yoki linkni tanimadim.\n\n"
        "Iltimos, faqat qo'llab-quvvatlanadigan platformalar (Instagram, YouTube, TikTok, Pinterest, va hk) linklarini yuboring."
    )

async def ping_handler(request):
    return web.Response(text="Bot muvaffaqiyatli ishlamoqda 🚀")

async def main():
    logger.info("Bot ishga tushmoqda...")
    init_db()  # Bot ishga tushishidan oldin bazani tayyorlash
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Render.com uchun qalbaki veb-server ishga tushiramiz
    # Bot info ni bir marta yuklab olamiz
    global BOT_USERNAME, BOT_FULL_NAME
    bot_info = await bot.get_me()
    BOT_USERNAME = bot_info.username
    BOT_FULL_NAME = bot_info.full_name
    app = web.Application()
    app.router.add_get('/', ping_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server port {port} da ishga tushdi...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")