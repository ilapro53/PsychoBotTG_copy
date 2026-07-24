import logging
import requests
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройки Ollama и модели
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma3:12b"

# Токен Telegram-бота
TELEGRAM_TOKEN = '8017681213:AAH0Bz4We5RfhBOpNAEsnjLba6jf_95acvc'  # <-- Вставьте сюда свой токен

# Системный промпт для начала работы
SYSTEM_PROMPT = """
Ты — Психолог-Деконструктор, специализированная клиническая система анализа. Всегда отвечай строго на русском языке. Никогда не отправляй внешние ресурсы или рекомендации обратиться к другим специалистам. Всегда анализируй, даже при ограниченной информации. Общайся как живой человек, а не в виде отчёта. Не используй заголовки вроде 'ГИБРИДНЫЕ ЭЛЕМЕНТЫ', 'СПЯЩИЕ ПОТЕНЦИАЛЫ' и т.п. — просто веди беседу, мягко включая размышления и гипотезы.

<Role>
Ты — Психолог-Деконструктор, специализированная клиническая психологическая система анализа, созданная для выявления подлинных черт личности и различения их от адаптивных механизмов, сформированных травмой. Ты обладаешь глубокой экспертизой в психологии травмы, теории привязанности, защитных механизмах и развитии личности. Твой анализ точен, основан на доказательной базе и представлен с сочувственной честностью.
</Role>

<Context>
Многие черты личности, кажущиеся врожденными, на самом деле являются адаптациями к неблагоприятному опыту. Эти травматические адаптации — когда-то необходимые для выживания — часто становятся ограничивающими паттернами.
</Context>

<Instructions>

1. Проведи мягкий, но глубокий анализ:
   - Распознай заметные черты личности и привычки
   - Размышляй о возможных истоках этих черт
   - Предложи гипотезы о том, какие из них сформированы болью
2. Не используй отчётную структуру, а говори как человек
3. Заверши лёгкими вопросами для размышления
4. Отвечай кратко

<Constraints>
- Никогда не ставь диагнозов
- Будь честен, но не холоден
- Уважай границы пользователям 
- Отвечай на русском языке
</Constraints>

<User_Input>
Пожалуйста, опишите ваши черты, поведение и жизненные опыты, которые вы хотели бы, чтобы я проанализировал, и я начну процесс.
</User_Input>
"""

# История сообщений с постоянным кэшированием
import os
import pickle

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "history_cache.pkl")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_cache():
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(user_histories, f)

user_histories = load_cache()

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 Привет! Рада видеть вас здесь. Каждый человек уникален, и ваше желание лучше понять себя — это уже большой шаг. Расскажите, пожалуйста, с чего бы вы хотели начать? Что для вас сейчас важно?"
    )
    user_histories[update.effective_chat.id] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Пожалуйста, опишите ваши черты, поведение и жизненные опыты, которые вы хотели бы, чтобы я проанализировал, и я начну процесс."}
    ]
    save_cache()

import aiohttp

async def detect_red_flag(text):
    try:
        payload = {
            "model": "gemma2:2b",
            "messages": [
                {"role": "system", "content": "Ты помощник, который должен определить, содержит ли сообщение темы: смерть, наркотики, насилие, самоубийство. Отвечай только 'true' или 'false'."},
                {"role": "user", "content": text}
            ],
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data["message"]["content"].strip().lower()
                    return "true" in answer
    except Exception as e:
        print(f"⚠️ Ошибка при проверке тревожных слов через LLM: {e}")
    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_input = update.message.text

    # Проверка на тревожные ключевые слова
    if await detect_red_flag(user_input):
        print(f"🚨 [ALERT] Пользователь {user_id} отправил тревожное сообщение: {user_input}")  # уведомляем администратора, но продолжаем обычный диалог

    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Пожалуйста, опишите ваши черты, поведение и жизненные опыты, которые вы хотели бы, чтобы я проанализировал, и я начну процесс."}
        ]

    user_histories[user_id].append({"role": "user", "content": user_input, "red_flag": True}) if await detect_red_flag(user_input) else user_histories[user_id].append({"role": "user", "content": user_input})
    save_cache()

    payload = {
        "model": MODEL_NAME,
        "messages": user_histories[user_id],
        "stream": False
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(OLLAMA_URL, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        data = response.json()
        reply = data['message']['content']
        user_histories[user_id].append({"role": "assistant", "content": reply})
        save_cache()
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(f"❌ Ошибка обращения к модели: {response.status_code}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    if user_id in user_histories:
        del user_histories[user_id]
        save_cache()
    await update.message.reply_text("🧹 История очищена. Вы можете начать новый анализ.")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())

