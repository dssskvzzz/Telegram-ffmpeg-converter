import json
import os
import subprocess
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputFile
import subprocess

with open("conf.json", "r") as f:
    config = json.load(f)

bot = Bot(token=config["token"])
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
print("Bot is running")
print(f"ID input channel:", config["input_channel"])
print(f"ID output channel:", config["output_channel"])
class SongInfo(StatesGroup):
    name = State()
    artist = State()
    lyrics = State()
    photo = State()


@dp.message_handler(content_types=types.ContentType.AUDIO, chat_type='channel', chat_id=config['input_channel'])
async def process_audio(message: types.Message, state: FSMContext):
    print("Audio has been sended!")
    await message.reply("⏳ One moment please...")
    file_id = message.audio.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_content = await bot.download_file(file_path)
    with open("audio.mp3", "wb") as f:
        f.write(file_content.getvalue())
    async with state.proxy() as data:
        data['audio'] = "audio.mp3"
    await SongInfo.name.set()
    await message.reply(config["name_question"])


@dp.message_handler(state=SongInfo.name)
async def process_name(message: types.Message, state: FSMContext):
    print("Song name has been sended! Name: `"+message.text+"`")
    async with state.proxy() as data:
        data['name'] = message.text
    await SongInfo.next()
    await message.reply(config["author_question"])


@dp.message_handler(state=SongInfo.artist)
async def process_artist(message: types.Message, state: FSMContext):
    print("Song artist has been sended! Artist: `"+message.text+"`")
    async with state.proxy() as data:
        data['artist'] = message.text
    await SongInfo.next()
    await message.reply(config["lyrics_question"])


@dp.message_handler(state=SongInfo.lyrics)
async def process_lyrics(message: types.Message, state: FSMContext):
    print("Song lyrics has been sended! Lyrics: `"+message.text+"`")
    async with state.proxy() as data:
        data['lyrics'] = message.text
    await SongInfo.next()
    await message.reply(config["photo_question"])


@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.TEXT], state=SongInfo.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.content_type == types.ContentType.PHOTO:
        print("Photo has been sended")
        await message.reply(config["hold_on_question"])
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_content = await bot.download_file(file_path)
        with open("photo.jpg", "wb") as f:
            f.write(file_content.getvalue())
        async with state.proxy() as data:
            data['photo'] = "photo.jpg"
        await state.finish()
        artist = data['artist']
        lyrics = data['lyrics'].replace("\n"," ")
        title = data['name']
        output_name = artist+'-'+title
        command1 = f'ffmpeg -i {config["audio_path"]} -map 0:a:0 -c:a libmp3lame -b:a 128k -ar 44100 output.mp3'
        command2 = f'''ffmpeg -i photo.jpg -i {config["cover_path"]} -filter_complex "[0:v]scale='min(512\,iw)':min'(512\,ih)',format=rgba[v];[1:v]scale='iw/4':-1[wm];[v][wm]overlay=W-w-10:H-h-10" output.png'''
        command3 = config['command'].format(
            title=title, artist=artist, lyrics=lyrics, output_name=output_name
        )
        print(command3)
        subprocess.run(command1)
        subprocess.run(command2)
        subprocess.run(command3, shell=True)
        await bot.send_audio(chat_id=config['channel_id'], audio=InputFile(f"{output_name}.mp3"))
        os.remove("output.mp3")
        os.remove(f"{output_name}.mp3")
        os.remove("output.png")
        os.remove("photo.jpg")
        os.remove("audio.mp3")
    if message.content_type == types.ContentType.TEXT:
        print("Photo has been skipped")
        await message.reply(config["hold_on_question"])
        async with state.proxy() as data:
            data['photo'] = None
        await state.finish()
        artist = data['artist']
        lyrics = data['lyrics'].replace("\n"," ")
        title = data['name']
        output_name = artist+'-'+title
        command1 = f'ffmpeg -i {config["audio_path"]} -map 0:a:0 -c:a libmp3lame -b:a 128k -ar 44100 output.mp3'
        command3 = config['commandskip'].format(
            title=title, artist=artist, lyrics=lyrics, output_name=output_name
        )
        print(command3)
        subprocess.run(command1)
        subprocess.run(command3, shell=True)
        await bot.send_audio(chat_id=config['output_channel'], audio=InputFile(f"{output_name}.mp3"))
        os.remove("output.mp3")
        os.remove(f"{output_name}.mp3")
        os.remove("audio.mp3")

if __name__ == '__main__':
    executor.start_polling(dp)