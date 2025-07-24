

import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from PIL import Image, ImageFilter, ImageOps
import pytesseract

BOT_TOKEN = os.environ.get("BOT_TOKEN") #  Лучше использовать переменные окружения

def start(update: Update, context: CallbackContext) -> None:
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
    update.message.reply_text('Привет! Я бот для обработки изображений. Отправь мне фото, а затем выбери, что с ним сделать. Или выбери опцию:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия на инлайн-кнопки."""
    query = update.callback_query
    query.answer()
    context.user_data['choice'] = query.data

    if query.data == 'convert':
        keyboard = [
            [InlineKeyboardButton("PNG", callback_data='png'),
             InlineKeyboardButton("JPEG", callback_data='jpeg')],
            [InlineKeyboardButton("BMP", callback_data='bmp'),
             InlineKeyboardButton("GIF", callback_data='gif')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="В какой формат конвертировать?", reply_markup=reply_markup)
    elif query.data in ['png', 'jpeg', 'bmp', 'gif']:
        context.user_data['conversion_format'] = query.data
        query.edit_message_text(text=f"Отлично, конвертирую в {query.data.upper()}. Теперь отправь мне фото.")
    elif query.data == 'resize':
         query.edit_message_text(text="Отправь мне новый размер в формате `ширина высота` (например, `800 600`).")
    elif query.data == 'rotate':
        query.edit_message_text(text="На сколько градусов повернуть? (например, `90`).")
    elif query.data == 'flip':
        keyboard = [
            [InlineKeyboardButton("Горизонтально", callback_data='flip_horizontal')],
            [InlineKeyboardButton("Вертикально", callback_data='flip_vertical')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="Как отзеркалить?", reply_markup=reply_markup)
    else:
        query.edit_message_text(text=f"Выбрано: {query.data}. Теперь отправь мне фото.")


def handle_image(update: Update, context: CallbackContext) -> None:
    """Обрабатывает полученное изображение."""
    if 'choice' not in context.user_data:
        update.message.reply_text("Сначала выбери опцию в меню.")
        return

    file_id = update.message.photo[-1].file_id
    new_file = context.bot.get_file(file_id)
    file_path = new_file.download()

    try:
        img = Image.open(file_path)
        choice = context.user_data.get('choice')

        if choice in ['png', 'jpeg', 'bmp', 'gif']:
            output_path = f"converted_image.{choice}"
            # Для форматов, которые не поддерживают RGBA (как JPEG), конвертируем в RGB
            if choice == 'jpeg' and img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(output_path)
            context.bot.send_document(chat_id=update.effective_chat.id, document=open(output_path, 'rb'))
            os.remove(output_path)
        elif choice == 'ocr':
            # Убедитесь, что tesseract установлен и указан путь к нему, если нужно
            # Для Termux может потребоваться: pytesseract.pytesseract.tesseract_cmd = '/data/data/com.termux/files/usr/bin/tesseract'
            text = pytesseract.image_to_string(img, lang='rus+eng')
            update.message.reply_text(text if text else "Текст не найден.")
        elif choice == 'pixelate':
            img_small = img.resize((32, 32), resample=Image.BILINEAR)
            result = img_small.resize(img.size, Image.NEAREST)
            output_path = "pixelated.png"
            result.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
        elif choice == 'grayscale':
            gray_img = ImageOps.grayscale(img)
            output_path = "grayscale.png"
            gray_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
        elif choice == 'metadata':
            info_dict = {
                "Формат": img.format,
                "Размер": img.size,
                "Режим": img.mode,
            }
            info_str = "\n".join([f"{k}: {v}" for k, v in info_dict.items()])
            update.message.reply_text(f"Метаданные изображения:\n{info_str}")
        elif choice == 'blur':
            blurred_img = img.filter(ImageFilter.BLUR)
            output_path = "blurred.png"
            blurred_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
        elif choice == 'sharpen':
            sharpened_img = img.filter(ImageFilter.SHARPEN)
            output_path = "sharpened.png"
            sharpened_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
        elif choice == 'flip_horizontal':
            flipped_img = ImageOps.mirror(img)
            output_path = "flipped_h.png"
            flipped_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
        elif choice == 'flip_vertical':
            flipped_img = ImageOps.flip(img)
            output_path = "flipped_v.png"
            flipped_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
        # Этот блок должен быть здесь, чтобы обрабатывать изображения после ввода текста
        elif choice == 'resize' and 'resize_dims' in context.user_data:
            resized_img = img.resize(context.user_data['resize_dims'])
            output_path = "resized.png"
            resized_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
            del context.user_data['resize_dims']
        elif choice == 'rotate' and 'rotate_angle' in context.user_data:
            rotated_img = img.rotate(context.user_data['rotate_angle'], expand=True)
            output_path = "rotated.png"
            rotated_img.save(output_path)
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(output_path, 'rb'))
            os.remove(output_path)
            del context.user_data['rotate_angle']


    finally:
        os.remove(file_path) # Удаляем временный файл
        # Не сбрасываем choice, если ожидаем текстовый ввод
        if choice not in ['resize', 'rotate']:
             if 'choice' in context.user_data:
                del context.user_data['choice']


def handle_text(update: Update, context: CallbackContext) -> None:
    """Обрабатывает текстовые сообщения для опций, требующих ввода."""
    if 'choice' not in context.user_data:
        # Можно просто игнорировать или отправить подсказку
        start(update, context) # Показываем меню, если команда не выбрана
        return

    choice = context.user_data.get('choice')

    if choice == 'resize':
        try:
            width, height = map(int, update.message.text.split())
            context.user_data['resize_dims'] = (width, height)
            update.message.reply_text(f"Установлен размер {width}x{height}. Теперь отправьте фото.")
        except (ValueError, IndexError):
            update.message.reply_text("Неверный формат. Отправь `ширина высота` (например, `800 600`).")
    elif choice == 'rotate':
        try:
            angle = float(update.message.text)
            context.user_data['rotate_angle'] = angle
            update.message.reply_text(f"Установлен угол поворота {angle}°. Теперь отправьте фото.")
        except ValueError:
            update.message.reply_text("Неверный формат. Отправь число (например, `90`).")
    else:
        update.message.reply_text("Я ожидаю фото для этой команды, а не текст.")


def main() -> None:
    """Запуск бота."""
    if not BOT_TOKEN:
        print("Переменная окружения BOT_TOKEN не найдена!")
        return

    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.command, handle_image))


    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

