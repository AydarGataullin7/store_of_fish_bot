import os
import redis
from dotenv import load_dotenv

from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import strapi_api

_database = None
strapi_url = None
strapi_token = None
redis_host = None
redis_port = None
redis_password = None


def start(update, context):
    products = strapi_api.get_products(strapi_url, strapi_token)
    keyboard = []
    for product in products:
        button = InlineKeyboardButton(product['name'], callback_data=product['documentId'])
        keyboard.append([button])
    keyboard.append([InlineKeyboardButton('Моя корзина', callback_data='my_cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.effective_message.reply_text('Please choose', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(update, context):
    document_id = update.callback_query.data
    if document_id == 'my_cart':
        return handle_cart(update, context)
    product = strapi_api.get_product(strapi_url, strapi_token, document_id)
    picture_url = product['picture']['url']
    image_url = f'{strapi_url}{picture_url}'
    image_bytes = strapi_api.get_image_bytes(image_url)
    update.callback_query.message.delete()
    keyboard = [
        [InlineKeyboardButton('Назад', callback_data='back')],
        [InlineKeyboardButton('Добавить в корзину', callback_data=f'add_to_cart_{document_id}')],
        [InlineKeyboardButton('Моя корзина', callback_data=f'my_cart')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(
        chat_id=update.callback_query.message.chat_id,
        photo=image_bytes,
        caption=f'{product["name"]}\n\n{product["description"]}\n\nЦена: {product["price"]} руб.',
        reply_markup=reply_markup
    )
    return "HANDLE_DESCRIPTION"


def handle_description(update, context):
    callback_data = update.callback_query.data
    chat_id = update.callback_query.message.chat_id
    if callback_data == 'back':
        update.callback_query.message.delete()
        start(update, context)
    elif callback_data.startswith('add_to_cart_'):
        product_document_id = callback_data.replace('add_to_cart_', '')
        cart = strapi_api.get_or_create_cart(strapi_url, strapi_token, chat_id)
        strapi_api.add_to_cart(strapi_url, strapi_token, cart['documentId'], product_document_id)
        update.callback_query.answer()
        update.callback_query.message.reply_text("Товар добавлен в корзину")
        return "HANDLE_DESCRIPTION"
    elif callback_data == 'my_cart':
        cart = strapi_api.get_cart(strapi_url, strapi_token, chat_id)
        text = "Ваша корзина: \n\n"
        total = 0
        for item in cart['cart_items']:
            product = item['product']
            name = product['name']
            price = product['price']
            quantity = item['quantity']
            subtotal = price * quantity
            total += subtotal
            text += f"- {name} - {quantity} x {price} руб. \n"
        update.callback_query.answer()
        update.callback_query.message.reply_text(text)
        return "HANDLE_CART"
    return "HANDLE_MENU"


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_email
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def handle_cart(update, context):
    callback_data = update.callback_query.data
    chat_id = update.callback_query.message.chat_id

    if callback_data == 'checkout':
        update.callback_query.answer()
        update.callback_query.message.reply_text('Введите ваш email:')
        return "WAITING_EMAIL"
    elif callback_data == 'back_to_menu':
        update.callback_query.message.delete()
        start(update, context)
        return "HANDLE_MENU"
    elif callback_data.startswith('remove_'):
        cart_item_document_id = callback_data.replace('remove_', '')
        strapi_api.delete_cart_item(strapi_url, strapi_token, cart_item_document_id)
        update.callback_query.message.delete()

    cart = strapi_api.get_cart(strapi_url, strapi_token, chat_id)

    if not cart or not cart['cart_items']:
        update.callback_query.answer()
        update.callback_query.message.reply_text('Корзина пуста')
        return "HANDLE_CART"

    text = "Ваша корзина:\n\n"
    keyboard = []
    total = 0

    for item in cart['cart_items']:
        product = item['product']
        name = product['name']
        price = product['price']
        quantity = item['quantity']
        subtotal = price * quantity
        total += subtotal
        text += f"- {name} - {quantity} x {price} руб.\n"

        button = InlineKeyboardButton(
            f'Удалить {name}',
            callback_data=f'remove_{item["documentId"]}'
        )
        keyboard.append([button])

    text += f"\nИтого: {total} руб."
    keyboard.append([InlineKeyboardButton('Оплатить', callback_data='checkout')])
    keyboard.append([InlineKeyboardButton('В меню', callback_data='back_to_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    update.callback_query.answer()

    return "HANDLE_CART"


def handle_email(update, context):
    email = update.message.text
    chat_id = update.message.chat_id
    strapi_api.create_client(strapi_url, strapi_token, email, chat_id)
    print("EMAIL:", email)
    update.message.reply_text(f'Спасибо! Ваш email: {email}')
    return "START"


def get_database_connection():
    global _database
    if _database is None:
        _database = redis.Redis(host=redis_host, port=redis_port, password=redis_password)
    return _database


if __name__ == '__main__':
    load_dotenv()
    strapi_url = os.getenv('STRAPI_URL')
    strapi_token = os.getenv('STRAPI_TOKEN')
    token = os.getenv("TELEGRAM_TOKEN")
    redis_host = os.getenv("DATABASE_HOST")
    redis_port = os.getenv("DATABASE_PORT")
    redis_password = os.getenv("DATABASE_PASSWORD")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
