from aiogram import *
import openai
import aiomysql
from google.cloud import storage
from buttons import markup
import json

TOKEN = ''
OPENAI_TOKEN = ''
BUCKET_NAME = ''
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

openai_client = openai.AsyncOpenAI(api_key=OPENAI_TOKEN)
storage_client = storage.Client()


@dp.message_handler(commands = ['start', 'help'])
async def start(message: types.Message):
    await message.reply('Привет!\nЯ бот на основе ИИ', reply_markup=markup)


@dp.message_handler():
async def default_handler(message: types.Message):
    answer = await generate_text(quest=message.text, model='gpt4o', id=message.from_user.id)


@dp.message_handler(lambda message: message.text == "GPT-Vision")
async def hi_reply(message: types.Message):
    await message.reply("Режим Vison включён, отправь мне фото")
    


async def get_data_from_context(id: int):
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'user',
        'password': 'pass',
        'db': 'context',
    }
    connection = await aiomysql.connect(**db_config)
    try:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT data FROM context WHERE id = %s", (id,))
            result = await cursor.fetchone()
            if result:
                data = json.loads(result[0])
                if len(data) > 6:
                    del data[0]
                    del data[1]
                return data
            else:
                data.append({"role": "system", "content": "You are a helpful assistant."})
                return data
    finally:
        connection.close()


async def save_context(id: int, data: list):
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'user',
        'password': 'pass',
        'db': 'context',
    }
    connection  = await aiomysql.connect(**db_config)
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE context SET data = %s WHERE id = %s",
                (data, id)
            )
            await connection.commit()
    finally:
        connection.close()




async def generate_text(quest, model, id) -> str:
    history = await get_data_from_context(id)
    history.append({"role": "user", "content": quest})
    response  = await openai_client.chat.completions.create(
        model = model,
        messages=history
    )
    result = response.choices[0].message.content
    context_part = {"role": "assistant",  "content":  result}
    history.append(context_part)
    await save_context(id, history)
    return result
    


async def vision(s3_url: str, text: str) -> str:
    text = text if text is not None else 'Что на этой картинке?'
    response = await openai_client.chat.completions.create(
        model='gpt-4-vision-preview',
        messages=[
    {
                "role": "user",
                "content": text
            },
            {
                "role": "user",
                "content": {
                    "type": "image_url",
                    "image_url": s3_url
                }
            }
        ]
    )
    return response.choices[0].message.content


async def upload_image(file, file_id) -> str:
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f'images/{file_id}.jpg')
    blob.upload_from_file(file)
    return blob.public_url





