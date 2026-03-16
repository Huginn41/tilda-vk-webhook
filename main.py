from fastapi import FastAPI, Request
from dotenv import load_dotenv
import requests
import os
import random

load_dotenv()

app = FastAPI()

VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_USER_ID = os.getenv("VK_USER_ID")


def send_vk_message(text: str):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.131",
        "user_id": VK_USER_ID,  # личка конкретному пользователю
        "message": text,
        "random_id": random.randint(1, 10**9),
    }
    response = requests.post(url, params=params)
    return response.json()


@app.post("/webhook")
async def tilda_webhook(request: Request):
    data = await request.form()
    data = dict(data)

    # Формируем сообщение из полей формы
    message_lines = ["📬 Новая заявка с сайта!"]
    for key, value in data.items():
        message_lines.append(f"{key}: {value}")

    message = "\n".join(message_lines)
    result = send_vk_message(message)

    return {"status": "ok", "vk_response": result}