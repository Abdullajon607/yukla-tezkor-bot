import logging
import os
import asyncio
import uuid
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.chat_action import ChatActionSender
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, DOWNLOAD_DIR, BASE_DIR
from extractors.universal_loader import get_universal_media
from database import init_db, get_file_id, save_file_id
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
session = AiohttpSession(timeout=600)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Bir vaqtning o'zida nechta yuklash jarayoni ishlashi mumkinligini belgilaymiz.
# Ko'proq odam bir vaqtda ishlashi va qotib qolmasligi uchun uni 15 ga oshiramiz.
download_semaphore = asyncio.Semaphore(15)

# YouTube sifatini tanlash uchun CallbackData Factory
class YouTubeCallback(CallbackData, prefix="yt"):
    quality: str
    vid: str

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "•Salom men Tezkor Yukla botman.!\n\n"
        "•Instagram - post, reels, stores;\n"
        "•TikTok - suv belgisiz videolar;\n"
        "•YouTube - video, shorts, audio;\n"
        "•Pinterest - rasm, video;\n"
        "•Snapchat - video;\n"
        "•Threads - rasm, video;",
        parse_mode=ParseMode.MARKDOWN
    )

# YouTube uchun alohida handler
@dp.message(F.text.regexp(r'https?://(?:www\.)?(?:youtube\.com/|youtu\.be/)'))
async def handle_youtube_link(message: types.Message):
    url = message.text
    wait_msg = await message.answer("⏳")

    # Mavjud formatlarni olish
    formats_info = await asyncio.to_thread(get_yt_formats, url)
    
    if not formats_info.get("status"):
        await wait_msg.edit_text(f"⚠️ Xatolik: {formats_info.get('error', 'Noma`lum xato')}")
        return

    # Agar bu Shorts video bo'lsa, tugmalarsiz to'g'ridan-to'g'ri 720p da yuklaymiz
    if formats_info.get("is_short"):
        await wait_msg.edit_text("⏳ **Shorts video yuklanmoqda...**", parse_mode=ParseMode.MARKDOWN)
        
        async with ChatActionSender(bot=bot, chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO):
            async with download_semaphore:
                result = await asyncio.to_thread(download_yt_by_quality, url=url, quality='720p')
            
            if result.get("status"):
                try:
                    video_file = types.FSInputFile(result["file_path"])
                    await message.answer_video(video=video_file, caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.")
                    await wait_msg.delete()
                except Exception as e:
                    logger.error(f"YouTube Shorts videosini yuborishda xato: {e}")
                    await wait_msg.edit_text("❌ Videoni yuborishda xatolik yuz berdi.")
                finally:
                    if os.path.exists(result["file_path"]):
                        os.remove(result["file_path"])
            else:
                await wait_msg.edit_text(f"⚠️ Xatolik: {result.get('error', 'Noma`lum xato')}")
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
    try:
        await query.message.edit_caption(caption="⏳ **Tanlangan sifatda yuklanmoqda...**", parse_mode=ParseMode.MARKDOWN)
    except:
        await query.message.edit_text("⏳ **Tanlangan sifatda yuklanmoqda...**", parse_mode=ParseMode.MARKDOWN)
    
    url = f"https://youtu.be/{callback_data.vid}"
    quality = callback_data.quality
    
    action = ChatAction.UPLOAD_VIDEO if quality != 'audio' else ChatAction.UPLOAD_DOCUMENT
    
    async with ChatActionSender(bot=bot, chat_id=query.from_user.id, action=action):
        async with download_semaphore:
            result = await asyncio.to_thread(download_yt_by_quality, url, quality)
            
        if result.get("status"):
            try:
                file_input = types.FSInputFile(result["file_path"])
                caption = "✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi."
                
                if quality == 'audio': await query.message.answer_audio(audio=file_input, caption=caption)
                else: await query.message.answer_video(video=file_input, caption=caption)
                
                await query.message.delete()
            except Exception as e:
                logger.error(f"YouTube faylini yuborishda xato: {e}")
                await query.message.answer("❌ Faylni yuborishda xatolik yuz berdi.")
            finally:
                if os.path.exists(result["file_path"]):
                    os.remove(result["file_path"])
        else:
            await query.message.edit_text(f"⚠️ **Xatolik:** {result.get('error', 'Noma`lum xato')}", parse_mode=ParseMode.MARKDOWN)

# Barcha qo'llab-quvvatlanadigan platformalar uchun universal handler
@dp.message(F.text.regexp(r'https?://(?:www\.)?(?:instagram\.com/|tiktok\.com/|vm\.tiktok\.com/|vt\.tiktok\.com/|pinterest\.com/|pin\.it/|snapchat\.com/|threads\.net/)'))
async def handle_universal(message: types.Message):
    url = message.text
    
    # Avval bazadan tekshiramiz
    cached_file = get_file_id(url)
    if cached_file:
        file_id, media_type = cached_file
        try:
            if media_type == "video":
                await message.answer_video(
                    video=file_id,
                    caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif media_type == "photo":
                await message.answer_photo(
                    photo=file_id,
                    caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif media_type == "audio":
                await message.answer_audio(
                    audio=file_id,
                    caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.",
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
                    total = len(urls)
                    
                    first_file_id = None
                    first_media_type = None
                    
                    # aiohttp yordamida haqiqiy asinxron va yashin tezligidagi yuklovchi
                    async def _download_media(m_url, m_type):
                        ext = "mp4" if m_type == 'video' else "jpg"
                        fname = f"insta_{uuid.uuid4().hex[:6]}.{ext}"
                        fpath = os.path.join(DOWNLOAD_DIR, fname)
                        async with aiohttp.ClientSession() as http_session:
                            async with http_session.get(m_url) as r:
                                r.raise_for_status()
                                with open(fpath, 'wb') as f:
                                    async for chunk in r.content.iter_chunked(1024*1024): # 1 MB dan tortish (Tezlik uchun)
                                        f.write(chunk)
                        return fpath

                    for idx, media in enumerate(urls):
                        try:
                            caption = "✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi."
                            sent_msg = None
                            
                            try:
                                # 1-USUL: YASHIN TEZLIGI (Telegram serverining o'ziga havolani beramiz)
                                if media['type'] == 'video':
                                    sent_msg = await message.answer_video(video=media['url'], caption=caption, parse_mode=ParseMode.MARKDOWN)
                                else:
                                    sent_msg = await message.answer_photo(photo=media['url'], caption=caption, parse_mode=ParseMode.MARKDOWN)
                            except Exception as direct_err:
                                # 2-USUL: Agar Telegram to'g'ridan-to'g'ri o'qiy olmasa, kompyuterga tortib keyin yuboramiz
                                logger.info(f"Direct URL xato qildi, kompyuter orqali yuborilmoqda...")
                                file_path = await _download_media(media['url'], media['type'])
                                media_input = types.FSInputFile(file_path)
                                
                                if media['type'] == 'video':
                                    sent_msg = await message.answer_video(video=media_input, caption=caption, parse_mode=ParseMode.MARKDOWN)
                                else:
                                    sent_msg = await message.answer_photo(photo=media_input, caption=caption, parse_mode=ParseMode.MARKDOWN)
                                    
                                # Xotira to'lmasligi uchun kompyuterga tushgan faylni srazu o'chiramiz
                                os.remove(file_path)

                            # Bazaga birinchi media ID sini kesh qilish
                            if sent_msg:
                                if media['type'] == 'video' and idx == 0 and sent_msg.video:
                                    first_file_id = sent_msg.video.file_id
                                    first_media_type = "video"
                                elif media['type'] == 'photo' and idx == 0 and sent_msg.photo:
                                    first_file_id = sent_msg.photo[-1].file_id
                                    first_media_type = "photo"
                        except Exception as e:
                            logger.error(f"{idx+1}-mediani yuborishda xato: {e}")
                            
                    await wait_msg.delete()
                    
                    # Agar post 1 ta rasmdan iborat bo'lsa, bazaga kesh qilamiz
                    if total == 1 and first_file_id:
                        save_file_id(url, first_file_id, first_media_type)
                else:
                    # Boshqa platformalar (YouTube, TikTok, va hk. - yt-dlp dan keladi)
                    file_path = result["file_path"]
                    ext = file_path.split('.')[-1].lower()
                    media_input = types.FSInputFile(file_path)
                    
                    sent_msg = None
                    media_type = "document"
                    
                    if ext in ['mp4', 'mkv', 'webm', 'mov']:
                        sent_msg = await message.answer_video(video=media_input, caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.", parse_mode=ParseMode.MARKDOWN)
                        media_type = "video"
                    elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                        sent_msg = await message.answer_photo(photo=media_input, caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.", parse_mode=ParseMode.MARKDOWN)
                        media_type = "photo"
                    elif ext in ['mp3', 'm4a', 'wav']:
                        sent_msg = await message.answer_audio(audio=media_input, caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.", parse_mode=ParseMode.MARKDOWN)
                        media_type = "audio"
                    else:
                        sent_msg = await message.answer_document(document=media_input, caption="✅ **Tayyor!**\n\n🚀 @Yukla_Tezkor_Bot orqali yuklandi.", parse_mode=ParseMode.MARKDOWN)

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

async def main():
    logger.info("Bot ishga tushmoqda...")
    init_db()  # Bot ishga tushishidan oldin bazani tayyorlash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")