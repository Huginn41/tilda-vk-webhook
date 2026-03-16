import json
import os
import random
import re
import requests
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

VK_TOKEN = os.getenv("VK_TOKEN")
VK_RECIPIENTS = os.getenv("VK_RECIPIENTS", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

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

def get_recipients():
    return [int(uid.strip()) for uid in VK_RECIPIENTS.split(",") if uid.strip()]

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


def send_vk_message(peer_id: int, text: str):
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
    # Проверка секретного ключа
    secret = request.headers.get("X-Webhook-Secret", "")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.form()
    data = dict(data)
    message = format_message(data)

    recipients = get_recipients()
    for user_id in recipients:
        send_vk_message(user_id, message)

    return {"status": "ok", "sent_to": len(recipients)}
