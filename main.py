import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageFilter, ImageOps
import pytesseract

# Включаем логирование для отладки
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и главное меню."""
    keyboard = [
        [InlineKeyboardButton("Конвертировать", callback_data='convert'),
         InlineKeyboardButton("OCR (Текст с фото)", callback_data='ocr')],
        [InlineKeyboardButton("Пикселизировать", callback_data='pixelate'),
         InlineKeyboardButton("Черно-белое", callback_data='grayscale')],
        [InlineKeyboardButton("Метаданные", callback_data='metadata'),
         InlineKeyboardButton("Изменить размер", callback_data='resize')],
        [InlineKeyboardButton("Повернуть", callback_data='rotate'),
         InlineKeyboardButton("Размыть", callback_data='blur')],
        [InlineKeyboardButton("Резкость", callback_data='sharpen'),
         InlineKeyboardButton("Отзеркалить", callback_data='flip')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Привет! Я бот для обработки изображений. Выбери опцию и отправь мне фото.',
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на инлайн-кнопки."""
    query = update.callback_query
    await query.answer()
    choice = query.data
    context.user_data['choice'] = choice

    if choice == 'convert':
        keyboard = [
            [InlineKeyboardButton("PNG", callback_data='png'),
             InlineKeyboardButton("JPEG", callback_data='jpeg')],
            [InlineKeyboardButton("BMP", callback_data='bmp'),
             InlineKeyboardButton("GIF", callback_data='gif')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="В какой формат конвертировать?", reply_markup=reply_markup)
    elif choice in ['png', 'jpeg', 'bmp', 'gif']:
        context.user_data['choice'] = 'convert_format' # Cпециальный ключ для конвертации
        context.user_data['conversion_format'] = choice
        await query.edit_message_text(text=f"Отлично, конвертирую в {choice.upper()}. Теперь отправь мне фото.")
    elif choice == 'resize':
        await query.edit_message_text(text="Отправь мне новый размер в формате `ширина высота` (например, `800 600`).")
    elif choice == 'rotate':
        await query.edit_message_text(text="На сколько градусов повернуть? (например, `90`).")
    elif choice == 'flip':
        keyboard = [
            [InlineKeyboardButton("Горизонтально", callback_data='flip_horizontal')],
            [InlineKeyboardButton("Вертикально", callback_data='flip_vertical')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Как отзеркалить?", reply_markup=reply_markup)
    else:
        await query.edit_message_text(text=f"Выбрано: {choice}. Теперь отправь мне фото.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения для опций, требующих ввода."""
    choice = context.user_data.get('choice')
    if not choice:
        await start(update, context)
        return

    if choice == 'resize':
        try:
            width, height = map(int, update.message.text.split())
            context.user_data['resize_dims'] = (width, height)
            await update.message.reply_text(f"Установлен размер {width}x{height}. Теперь отправьте фото.")
        except (ValueError, IndexError):
            await update.message.reply_text("Неверный формат. Отправь `ширина высота` (например, `800 600`).")
    elif choice == 'rotate':
        try:
            angle = float(update.message.text)
            context.user_data['rotate_angle'] = angle
            await update.message.reply_text(f"Установлен угол поворота {angle}°. Теперь отправьте фото.")
        except ValueError:
            await update.message.reply_text("Неверный формат. Отправь число (например, `90`).")
    else:
        await update.message.reply_text("Я ожидаю фото для этой команды, а не текст.")


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает полученное изображение."""
    choice = context.user_data.get('choice')
    if not choice:
        await update.message.reply_text("Сначала выбери опцию в меню.")
        return

    file_id = update.message.photo[-1].file_id
    new_file = await context.bot.get_file(file_id)
    # download_to_drive возвращает объект Path, который нужно преобразовать в строку
    file_path = str(await new_file.download_to_drive())

    try:
        img = Image.open(file_path)
        output_path = "processed_image.png" # Имя по умолчанию

        if choice == 'convert_format':
            conversion_format = context.user_data.get('conversion_format')
            output_path = f"converted_image.{conversion_format}"
            if conversion_format == 'jpeg' and img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(output_path)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=open(output_path, 'rb'))
        elif choice == 'ocr':
            text = pytesseract.image_to_string(img, lang='rus+eng')
            await update.message.reply_text(text if text else "Текст не найден.")
            return # Не отправляем фото обратно
        elif choice == 'pixelate':
            img_small = img.resize((32, 32), resample=Image.Resampling.BILINEAR)
            result = img_small.resize(img.size, Image.Resampling.NEAREST)
            result.save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'grayscale':
            ImageOps.grayscale(img).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'metadata':
            info_dict = {"Формат": img.format, "Размер": img.size, "Режим": img.mode}
            info_str = "\n".join([f"{k}: {v}" for k, v in info_dict.items()])
            await update.message.reply_text(f"Метаданные изображения:\n{info_str}")
            return
        elif choice == 'blur':
            img.filter(ImageFilter.BLUR).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'sharpen':
            img.filter(ImageFilter.SHARPEN).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'flip_horizontal':
            ImageOps.mirror(img).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'flip_vertical':
            ImageOps.flip(img).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'resize' and 'resize_dims' in context.user_data:
            img.resize(context.user_data['resize_dims']).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        elif choice == 'rotate' and 'rotate_angle' in context.user_data:
            img.rotate(context.user_data['rotate_angle'], expand=True).save(output_path)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
        else:
            # Если пришло фото, а нужных данных для обработки (например, размера) нет
            await update.message.reply_text("Пожалуйста, сначала укажите параметры (например, размер или угол).")
            return

    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего изображения.")
    finally:
        # Очистка
        if os.path.exists(file_path):
            os.remove(file_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        # Сбрасываем состояние
        context.user_data.clear()


def main() -> None:
    """Запуск бота."""
    if not BOT_TOKEN:
        logger.error("Переменная окружения BOT_TOKEN не найдена!")
        return

    # Используем новый ApplicationBuilder
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_image))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()