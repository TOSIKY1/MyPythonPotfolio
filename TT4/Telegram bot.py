import telebot
import os
from dotenv import load_dotenv
from openai import OpenAI

# Загрузка токена бота из переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация клиента YandexGPT (с вашими данными)
client = OpenAI(
    api_key=os.getenv('api_key'),
    base_url=os.getenv('base_url'),
    project=os.getenv('project')
)
# ID вашего сохранённого промпта
PROMPT_ID = "fvt279spj77bscaasngi"

# Хранилище истории диалога для каждого пользователя (по user_id)
user_histories = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Это твой ИИ-помощник. Напиши что-нибудь, и я отвечу.")

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_id = message.from_user.id
    user_text = message.text

    # Получаем историю для этого пользователя или создаём новую
    if user_id not in user_histories:
        user_histories[user_id] = []

    history = user_histories[user_id]

    # Добавляем сообщение пользователя в историю
    history.append({"role": "user", "content": user_text})

    try:
        # Отправляем запрос к YandexGPT
        response = client.responses.create(
            prompt={"id": PROMPT_ID},
            input=history,   # передаём всю историю
        )

        # --- ИЗВЛЕЧЕНИЕ ОТВЕТА ---
        # Пытаемся получить текст из разных возможных форматов
        if hasattr(response, 'output') and response.output:
            # Если output — список объектов
            if isinstance(response.output, list) and len(response.output) > 0:
                first_output = response.output[0]
                # Если у объекта есть content[0].text (как в OpenAI Responses API)
                if hasattr(first_output, 'content') and isinstance(first_output.content, list) and len(first_output.content) > 0:
                    assistant_reply = first_output.content[0].text
                else:
                    # Если это просто строка или другой объект
                    assistant_reply = str(first_output)
            else:
                assistant_reply = str(response.output)
        elif hasattr(response, 'choices') and response.choices:
            # Стандартный формат OpenAI chat.completions
            assistant_reply = response.choices[0].message.content
        else:
            # На случай, если формат совсем другой — выводим для отладки
            assistant_reply = f"Неизвестный формат ответа: {response}"
            print("Ответ от API:", response)

        # Отправляем ответ пользователю
        bot.reply_to(message, assistant_reply)

        # Добавляем ответ ассистента в историю
        history.append({"role": "assistant", "content": assistant_reply})

        # (Опционально) Ограничиваем историю, чтобы не превысить лимит токенов
        # if len(history) > 20:   # храним последние 20 сообщений
        #     history = history[-20:]
        #     user_histories[user_id] = history

    except Exception as e:
        error_msg = f"⚠️ Произошла ошибка: {e}"
        bot.reply_to(message, error_msg)
        print(f"Ошибка для пользователя {user_id}: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()