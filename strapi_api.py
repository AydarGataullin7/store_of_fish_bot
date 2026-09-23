import requests


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_products(strapi_url, token):
    url = f'{strapi_url}/api/products'
    response = requests.get(url, headers=get_headers(token))
    response.raise_for_status()
    return response.json()['data']


def get_product(strapi_url, token, document_id):
    url = f'{strapi_url}/api/products/{document_id}'
    params = {'populate': 'picture'}
    response = requests.get(url, headers=get_headers(token), params=params)
    response.raise_for_status()
    return response.json()['data']


def get_image_bytes(image_url):
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content


def get_or_create_cart(strapi_url, token, chat_id):
    url = f'{strapi_url}/api/carts'
    response = requests.get(
        url,
        headers=get_headers(token),
        params={'filters[telegram_id][$eq]': chat_id}
    )
    response.raise_for_status()
    carts = response.json()['data']
    if carts:
        return carts[0]
    data = {"data": {"telegram_id": chat_id}}
    response = requests.post(url, headers=get_headers(token), json=data)
    response.raise_for_status()
    return response.json()['data']


def add_to_cart(strapi_url, token, cart_document_id, product_document_id):
    url = f'{strapi_url}/api/cart-items'
    data = {
        "data": {
            "quantity": 1,
            "cart": cart_document_id,
            "product": product_document_id,
        }
    }
    response = requests.post(url, headers=get_headers(token), json=data)
    response.raise_for_status()
    return response.json()


def get_cart(strapi_url, token, chat_id):
    url = f'{strapi_url}/api/carts'
    response = requests.get(
        url,
        headers=get_headers(token),
        params={'filters[telegram_id][$eq]': chat_id}
    )
    response.raise_for_status()
    carts = response.json()['data']
    if not carts:
        return None
    cart_document_id = carts[0]['documentId']
    url = f'{strapi_url}/api/carts/{cart_document_id}'
    params = {'populate': 'cart_items.product'}
    response = requests.get(url, headers=get_headers(token), params=params)
    response.raise_for_status()
    return response.json()['data']


def delete_cart_item(strapi_url, token, cart_item_document_id):
    url = f'{strapi_url}/api/cart-items/{cart_item_document_id}'
    response = requests.delete(url, headers=get_headers(token))
    response.raise_for_status()


def create_client(strapi_url, token, email, chat_id):
    url = f'{strapi_url}/api/clients'
    data = {
        "data": {
            "email": email,
            "telegram_id": chat_id,
        }
    }
    response = requests.post(url, headers=get_headers(token), json=data)
    response.raise_for_status()
    return response.json()
