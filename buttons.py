from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


btn1 = KeyboardButton('GPT-Vision')
btn2 = KeyboardButton('FIle Analyse')

markup = ReplyKeyboardMarkup(resize_keyboard=None)
markup.add(btn1, btn2)
