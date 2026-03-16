import json
import os
import random
import re
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

VK_TOKEN = os.getenv("VK_TOKEN")
VK_USER_ID = os.getenv("VK_USER_ID")
VK_CHAT_PEER_ID = os.getenv("VK_CHAT_PEER_ID")

PAYMENT_METHODS = {
    "cash": "Наличные",
    "card": "Карта",
    "online": "Онлайн",
    "bank": "Банковский перевод",
    "tinkoff": "Tinkoff",
    "sberbank": "Сбербанк",
    "yookassa": "ЮКасса",
    "robokassa": "Robokassa",
}

def clean_address(address: str) -> str:
    address = re.sub(r'^RU:\s*', '', address)
    address = address.replace("Point: ", "")
    return address.strip()

def format_message(data: dict) -> str:
    lines = []

    payment_raw = data.get("payment", "{}")
    try:
        payment = json.loads(payment_raw)
    except Exception:
        payment = {}

    order_id = payment.get("orderid", "—")
    lines.append(f"🛍 Новый заказ #{order_id}\n")

    name = payment.get("delivery_fio") or data.get("Name") or data.get("ma_name", "—")
    phone = data.get("Phone", "—")
    email = data.get("Email") or data.get("ma_email", "—")
    lines.append("👤 Покупатель")
    lines.append(name)
    lines.append(f"📞 {phone}")
    lines.append(f"✉️ {email}\n")

    products = payment.get("products", [])
    if products:
        lines.append("🛒 Товары")
        for product in products:
            try:
                name_part, price_part = product.split(", pc=")
                name_part = name_part.replace("&quot;", '"')
                lines.append(f"• {name_part} — {price_part} руб.")
            except Exception:
                lines.append(f"• {product}")

    subtotal = payment.get("subtotal", "")
    delivery_price = payment.get("delivery_price", 0)
    amount = payment.get("amount", "—")

    lines.append("")
    if subtotal and float(delivery_price) > 0:
        lines.append(f"💰 Товары: {subtotal} руб.")
        lines.append(f"🚚 Доставка: {delivery_price} руб.")
        lines.append(f"💵 Итого: {amount} руб.")
    else:
        lines.append(f"💰 Сумма: {amount} руб.")

    pay_method = data.get("paymentsystem", "—")
    pay_label = PAYMENT_METHODS.get(pay_method, pay_method)
    lines.append(f"💳 Оплата: {pay_label}")

    delivery = payment.get("delivery", "")
    address = payment.get("delivery_address", "")
    comment = payment.get("delivery_comment", "")

    if delivery:
        lines.append(f"\n📦 Доставка")
        lines.append(delivery)
        if address:
            lines.append(clean_address(address))

    if comment:
        lines.append(f"\n💬 Комментарий")
        lines.append(comment)

    return "\n".join(lines)


def send_vk_message(peer_id: str, text: str):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.131",
        "peer_id": peer_id,
        "message": text,
        "random_id": random.randint(1, 10**9),
    }
    response = requests.post(url, params=params)
    return response.json()


@app.post("/webhook")
async def tilda_webhook(request: Request):
    data = await request.form()
    data = dict(data)
    message = format_message(data)

    results = {}

    # Отправляем в личку администратору
    if VK_USER_ID:
        results["personal"] = send_vk_message(VK_USER_ID, message)

    # Отправляем в чат сотрудников
    if VK_CHAT_PEER_ID:
        results["chat"] = send_vk_message(VK_CHAT_PEER_ID, message)

    print(f"VK responses: {results}")
    return {"status": "ok", "vk_response": results}
