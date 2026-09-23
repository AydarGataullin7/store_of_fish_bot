import requests


def get_headers(strapi_token):
    return {
        "Authorization": f"Bearer {strapi_token}",
        "Content-Type": "application/json",
    }


def get_products(strapi_url, strapi_token):
    url = f'{strapi_url}/api/products'
    strapi_response = requests.get(url, headers=get_headers(strapi_token))
    strapi_response.raise_for_status()
    return strapi_response.json()['data']


def get_product(strapi_url, strapi_token, document_id):
    url = f'{strapi_url}/api/products/{document_id}'
    query_params = {'populate': 'picture'}
    strapi_response = requests.get(
        url, headers=get_headers(strapi_token), params=query_params
    )
    strapi_response.raise_for_status()
    return strapi_response.json()['data']


def get_image_bytes(image_url):
    image_response = requests.get(image_url)
    image_response.raise_for_status()
    return image_response.content


def get_or_create_cart(strapi_url, strapi_token, chat_id):
    url = f'{strapi_url}/api/carts'
    strapi_response = requests.get(
        url,
        headers=get_headers(strapi_token),
        params={'filters[telegram_id][$eq]': chat_id}
    )
    strapi_response.raise_for_status()
    found_carts = strapi_response.json()['data']
    if found_carts:
        return found_carts[0]
    request_body = {"data": {"telegram_id": chat_id}}
    strapi_response = requests.post(
        url, headers=get_headers(strapi_token), json=request_body
    )
    strapi_response.raise_for_status()
    return strapi_response.json()['data']


def add_to_cart(strapi_url, strapi_token, cart_document_id, product_document_id):
    url = f'{strapi_url}/api/cart-items'
    request_body = {
        "data": {
            "quantity": 1,
            "cart": cart_document_id,
            "product": product_document_id,
        }
    }
    strapi_response = requests.post(
        url, headers=get_headers(strapi_token), json=request_body
    )
    strapi_response.raise_for_status()
    return strapi_response.json()


def get_cart(strapi_url, strapi_token, chat_id):
    url = f'{strapi_url}/api/carts'
    strapi_response = requests.get(
        url,
        headers=get_headers(strapi_token),
        params={'filters[telegram_id][$eq]': chat_id}
    )
    strapi_response.raise_for_status()
    found_carts = strapi_response.json()['data']
    if not found_carts:
        return None
    cart_document_id = found_carts[0]['documentId']
    url = f'{strapi_url}/api/carts/{cart_document_id}'
    query_params = {'populate': 'cart_items.product'}
    strapi_response = requests.get(
        url, headers=get_headers(strapi_token), params=query_params
    )
    strapi_response.raise_for_status()
    return strapi_response.json()['data']


def delete_cart_item(strapi_url, strapi_token, cart_item_document_id):
    url = f'{strapi_url}/api/cart-items/{cart_item_document_id}'
    strapi_response = requests.delete(url, headers=get_headers(strapi_token))
    strapi_response.raise_for_status()


def create_client(strapi_url, strapi_token, email, chat_id):
    url = f'{strapi_url}/api/clients'
    request_body = {
        "data": {
            "email": email,
            "telegram_id": chat_id,
        }
    }
    strapi_response = requests.post(
        url, headers=get_headers(strapi_token), json=request_body
    )
    strapi_response.raise_for_status()
    return strapi_response.json()
