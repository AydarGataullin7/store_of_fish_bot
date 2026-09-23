import os
import redis
from dotenv import load_dotenv
import requests

from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

_database = None

def start(update, context):
    url = 'http://localhost:1337/api/products'
    headers = {"Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"}
    response = requests.get(url, headers=headers)
    products = response.json()['data']
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
    url = f'http://localhost:1337/api/products/{document_id}?populate=picture'
    headers = {"Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"}
    response = requests.get(url, headers=headers)
    product = response.json()['data']
    picture_url = product['picture']['url']
    image_url = f'http://localhost:1337{picture_url}'
    image_response = requests.get(image_url)
    image_bytes = image_response.content
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
        url = 'http://localhost:1337/api/carts'
        headers = {
            "Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}",
            "Content-Type": "application/json",
        }
        data = {
            "data": {
                "telegram_id": chat_id,
            }
        }
        response = requests.get(url, headers=headers, params={'filters[telegram_id][$eq]': chat_id})
        carts = response.json()['data']
        if not carts:
            response = requests.post(url, headers=headers, json=data)
            cart = response.json()['data']
            update.callback_query.answer()
            update.callback_query.message.reply_text("Корзина создана")
        else:
            cart = carts[0]
            update.callback_query.answer()
            update.callback_query.message.reply_text("Корзина уже существует")
        cart_document_id = cart['documentId']
        cart_item_url = 'http://localhost:1337/api/cart-items'
        cart_item_data = {
            "data": {
            "quantity": 1,
            "cart": cart_document_id,
            "product": product_document_id,
            }
        }
        response = requests.post(cart_item_url, headers=headers, json=cart_item_data)
        update.callback_query.message.reply_text("Товар добавлен в корзину")
        return "HANDLE_DESCRIPTION"

    elif callback_data == 'my_cart':
        url = 'http://localhost:1337/api/carts'
        headers = {"Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"}
        response = requests.get(url, headers=headers, params={'filters[telegram_id][$eq]': chat_id})
        carts = response.json()['data']
        cart_document_id = carts[0]['documentId']
        url = f'http://localhost:1337/api/carts/{cart_document_id}?populate=cart_items.product'
        response = requests.get(url, headers=headers)
        cart = response.json()['data']
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
        url = f'http://localhost:1337/api/cart-items/{cart_item_document_id}'
        headers = {"Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"}
        requests.delete(url, headers=headers)
        update.callback_query.message.delete()

    url = 'http://localhost:1337/api/carts'
    headers = {"Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"}
    response = requests.get(url, headers=headers, params={'filters[telegram_id][$eq]': chat_id})
    carts = response.json()['data']

    if not carts:
        update.callback_query.answer()
        update.callback_query.message.reply_text('Корзина пуста')
        return "HANDLE_CART"

    cart_document_id = carts[0]['documentId']
    url = f'http://localhost:1337/api/carts/{cart_document_id}?populate=cart_items.product'
    response = requests.get(url, headers=headers)
    cart = response.json()['data']

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
    url = 'http://localhost:1337/api/clients'
    headers = {
        "Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}",
        "Content-Type": "application/json",
    }
    data = {
        "data": {
            "email": email,
            "telegram_id": chat_id,
        }
    }
    response = requests.post(url, headers=headers, json=data)
    print("EMAIL:", email)
    update.message.reply_text(f'Спасибо! Ваш email: {email}')
    return "START"

def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv("DATABASE_PASSWORD")
        database_host = os.getenv("DATABASE_HOST")
        database_port = os.getenv("DATABASE_PORT")
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
