from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentType
import openai
import aiomysql
from buttons import markup
import json
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import os
import base64
from aiogram.types import ContentType
from aiogram.utils import executor


TOKEN = ''
OPENAI_TOKEN = ''


PHOTO_SAVE_PATH = './photos'
AUDIO_SAVE_PATH  =  './audios'

if not os.path.exists(PHOTO_SAVE_PATH):
    os.makedirs(PHOTO_SAVE_PATH)

if not os.path.exists(AUDIO_SAVE_PATH):
    os.makedirs(AUDIO_SAVE_PATH)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

class ImageForm(StatesGroup):
    description = State()

openai_client = openai.AsyncOpenAI(api_key=OPENAI_TOKEN)



@dp.message_handler(commands = ['start', 'help'])
async def start(message: types.Message):
    await message.reply('Привет!\nЯ бот на основе ИИ', reply_markup=markup)


@dp.message_handler()
async def default_handler(message: types.Message):
    m = await bot.send_message(message.chat.id, '⌛')
    answer = await generate_text(quest=message.text, model='gpt4o', id=message.from_user.id)
    await bot.delete_message(message.chat.id, m.message_id)
    await message.reply(answer)


@dp.message_handler(lambda message: message.text == "GPT-Vision")
async def hi_reply(message: types.Message):
    await message.reply("Просто отправь мне фото!")


@dp.message_handler(lambda message: message.text == "Сгенерировать изображение")
async def get_image_desc(message: types.Message):
    await ImageForm.description.set()
    await message.reply('Напишите описание для генерации картинки')

@dp.message_handler(state = ImageForm.description)
async def send_image(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    m = await bot.send_message(message.chat.id, 'Начинаем генерировать изображение ⌛')
    answer = await generate_image(data['description'])
    await bot.delete_message(message.chat.id, m.message_id)
    await bot.send_message(message.chat.id, answer)


@dp.message_handler(content_types=ContentType.PHOTO)
async def handle_photo(message: types.Message):
    m = await bot.send_message(message.chat.id, '⌛')
    photo = message.photo[-1]
    caption = message.caption if message.caption else None
    photo_path = os.path.join(PHOTO_SAVE_PATH, f"{photo.file_id}.jpg")
    await photo.download(destination_file=photo_path)
    base64_image = await encode_image(photo_path)
    answer = await vision(base64_image, caption)
    await bot.delete_message(message.chat.id, m.message_id)
    await message.reply(answer)
    

@dp.message_handler(content_types=ContentType.VOICE)
async def handle_voice(message: types.Message):
    m = await bot.send_message(message.chat.id, '⌛ Обработка голосового сообщения')
    voice = message.voice
    voice_path = os.path.join(AUDIO_SAVE_PATH, f"{voice.file_id}.ogg")
    await voice.download(destination_file=voice_path)
    answer = await make_transcription(voice_path)
    await bot.delete_message(message.chat.id, m.message_id)
    await message.reply(answer)

async def generate_image(prompt: str) -> str:
    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url


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
                "content": [
            {
                "type": "text",
                "text": text
            },
            {
                "type": "image_url",
                "image_url": {
                "url": f"data:image/jpeg;base64,{s3_url}"
                }
            }
            ]
        }
    ])
    return response.choices[0].message.content


async def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')


async def make_transcription(audio_path):
    audio_file = open(audio_path,  "rb")
    response  = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file= audio_file,
        response_format="text"
        )
    return response.text


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)