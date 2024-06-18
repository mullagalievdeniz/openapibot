from aiogram import *
import openai
import aiomysql
from google.cloud import storage
from buttons import markup


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


@dp.message_handler(lambda message: message.text == "GPT-Vision")
async def hi_reply(message: types.Message):
    await message.reply("Режим Vison включён, отправь мне фото")
    


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





