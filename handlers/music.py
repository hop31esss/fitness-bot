from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.callback_query(F.data == "gym_music")
async def gym_music_menu(callback: CallbackQuery):
    """Меню музыки для тренировок"""
    text = (
        "🎵 *Музыка для зала*\n\n"
        "Правильная музыка может увеличить вашу производительность на 15%! 🚀\n\n"
        "Выберите тип тренировки или настроение:\n\n"
        "💪 *Для силовых тренировок* - мотивирующая, энергичная\n"
        "🏃 *Для кардио* - ритмичная, поддерживающая темп\n"
        "🧘 *Для растяжки* - спокойная, расслабляющая\n"
        "🔥 *Для настроения* - подборки под разное состояние"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💪 Силовые", callback_data="music_power"),
        InlineKeyboardButton(text="🏃 Кардио", callback_data="music_cardio")
    )
    builder.row(
        InlineKeyboardButton(text="🧘 Растяжка", callback_data="music_stretch"),
        InlineKeyboardButton(text="🔥 По настроению", callback_data="music_mood")
    )
    builder.row(
        InlineKeyboardButton(text="🎧 Платформы", callback_data="music_platforms"),
        InlineKeyboardButton(text="📊 BPM калькулятор", callback_data="music_bpm")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "music_power")
async def music_power(callback: CallbackQuery):
    """Музыка для силовых тренировок"""
    text = (
        "💪 *Музыка для силовых тренировок*\n\n"
        "*Идеальный BPM:* 130-150\n"
        "*Жанры:* Трэп, Хардстайл, Метал, Рок\n\n"
        
        "🎧 *Подборки на Яндекс.Музыке:*\n"
        "• [Для силовых тренировок](https://music.yandex.ru/playlists/90666ffb-78e2-f9f9-6ef2-cc92db20089b?utm_source=web&utm_medium=copy_link)\n"
        "• [Heavy Workout](https://music.yandex.ru/playlists/0ec87c4e-131c-defc-b376-aa07e76a626e?utm_source=web&utm_medium=copy_link)\n"\
        
        "🎵 *Подборки на Spotify:*\n"
        "• [Power Workout](https://open.spotify.com/playlist/37i9dQZF1DX76Wlfdnj7AP)\n"
        "• [Beast Mode](https://open.spotify.com/playlist/37i9dQZF1DX9XIFQuFvzM4)\n"
        "• [Heavy Metal Workout](https://open.spotify.com/playlist/37i9dQZF1DX1KN7YrOIxQD)\n\n"
        
        "🍎 *Подборки на Apple Music:*\n"
        "• [Hip-Hop Workout](https://music.apple.com/us/playlist/hip-hop-workout/pl.4c62f568a0d64293a9c362037175c09b)\n"
        "• [GYMFLOW](https://music.apple.com/us/playlist/gymflow/pl.ae7c5093e09e49bcb60ec2a1fa2eec24)\n\n"
        
        "🎯 *Топ-5 треков для жима лежа:*\n"
        "1. Eminem - 'Till I Collapse\n"
        "2. Metallica - Enter Sandman\n"
        "3. Kanye West - Power\n"
        "4. Disturbed - Down With The Sickness\n"
        "5. DMX - X Gon' Give It To Ya"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Яндекс.Музыка", url="https://music.yandex.ru"),
        InlineKeyboardButton(text="🔗 Spotify", url="https://open.spotify.com")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Apple Music", url="https://music.apple.com"),
        InlineKeyboardButton(text="🎧 Следующий раздел", callback_data="music_cardio")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="gym_music"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "music_cardio")
async def music_cardio(callback: CallbackQuery):
    """Музыка для кардио"""
    text = (
        "🏃 *Музыка для кардио тренировок*\n\n"
        "*Идеальный BPM:* 160-180 (бег), 120-140 (велосипед)\n"
        "*Жанры:* Электроника, Поп, Хип-хоп, Данс\n\n"
        
        "🎧 *Подборки на Яндекс.Музыке:*\n"
        "• [Running 2024](https://music.yandex.ru/playlists/e7c4d31c-d10e-4ae6-c325-53d5d3cddd65)\n"
        "• [Jogging Hits](https://music.yandex.ru/album/39665838)\n\n"
        
        "🎵 *Подборки на Spotify:*\n"
        "• [Cardio](https://open.spotify.com/playlist/37i9dQZF1DX1ewVhAJ17m4)\n"
        "• [Running Songs](https://open.spotify.com/playlist/37i9dQZF1DX1s9knjP51Oa)\n"
        "• [Ultimate Workout](https://open.spotify.com/playlist/37i9dQZF1DX76Wlfdnj7AP)\n\n"
        
        "🍎 *Подборки на Apple Music:*\n"
        "• [Cardio Workout](https://music.apple.com/us/curator/apple-music-fitness/1558256909)\n"
        "• [Running Motivation](https://music.apple.com/us/playlist/runners-high/pl.5a4bf230c2e849ffa65605c6e8067bea)\n\n"
        
        "🎯 *Топ-5 треков для бега:*\n"
        "1. Survivor - Eye of the Tiger\n"
        "2. Avicii - Levels\n"
        "3. David Guetta - Titanium\n"
        "4. Macklemore - Can't Hold Us\n"
        "5. The Weeknd - Blinding Lights\n\n"
        
        "💡 *Совет:* Подбирайте музыку под темп бега - 180 BPM для 180 шагов в минуту!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Яндекс.Музыка", url="https://music.yandex.ru"),
        InlineKeyboardButton(text="🔗 Spotify", url="https://open.spotify.com")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Apple Music", url="https://music.apple.com"),
        InlineKeyboardButton(text="🎧 Следующий раздел", callback_data="music_stretch")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="gym_music"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "music_stretch")
async def music_stretch(callback: CallbackQuery):
    """Музыка для растяжки и заминки"""
    text = (
        "🧘 *Музыка для растяжки и заминки*\n\n"
        "*Идеальный BPM:* 60-90\n"
        "*Жанры:* Лоу-фай, Эмбиент, Классика, Инструментал\n\n"
        
        "🎧 *Подборки на Яндекс.Музыке:*\n"
        "• [Растяжка](https://music.yandex.ru/album/32858369)\n"
        "• [Йога](https://music.yandex.ru/artist/12259755)\n"
        "• [Lo-Fi](https://music.yandex.ru/playlists/ar.31ed6a63-9d12-4463-bf97-15953bf2da42)\n\n"
        
        "🎵 *Подборки на Spotify:*\n"
        "• [Yoga & Meditation](https://open.spotify.com/playlist/37i9dQZF1DX9uKNf5jGX6m)\n"
        "• [Lo-Fi Beats](https://open.spotify.com/playlist/37i9dQZF1DWWQRwui0ExPn)\n"
        "• [Peaceful Piano](https://open.spotify.com/playlist/37i9dQZF1DX4sWSpwq3LiO)\n\n"
        
        "🍎 *Подборки на Apple Music:*\n"
        "• [After Workout](https://music.apple.com/us/playlist/pure-yoga/pl.6e7eb6c06bcd40ec982e24d6af0cd59a)\n"
        "• [Restorative Yoga](https://music.apple.com/us/playlist/restorative-yoga/pl.fc00030a195147a49bd218cc61a28fb8)\n\n"
        
        "🎯 *Топ-5 треков для растяжки:*\n"
        "1. Marconi Union - Weightless\n"
        "2. Ludovico Einaudi - Nuvole Bianche\n"
        "3. Bonobo - Kerala\n"
        "4. Ólafur Arnalds - Saman\n"
        "5. Tycho - Awake\n\n"
        
        "💡 *Совет:* Используйте спокойную музыку для снижения кортизола после тренировки."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Яндекс.Музыка", url="https://music.yandex.ru"),
        InlineKeyboardButton(text="🔗 Spotify", url="https://open.spotify.com")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Apple Music", url="https://music.apple.com"),
        InlineKeyboardButton(text="🎧 Следующий раздел", callback_data="music_mood")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="gym_music"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "music_mood")
async def music_mood(callback: CallbackQuery):
    """Музыка по настроению"""
    text = (
        "🔥 *Музыка по настроению*\n\n"
        "Выберите музыку под ваше текущее состояние:\n\n"
        
        "⚡ *Нет энергии?* - Мотивирующая музыка\n"
        "• [Energy Boost](https://music.yandex.ru/playlists/e5de4f96-2d96-6551-ec56-da672b74b5e8)\n"
        "• Треки с быстрым темпом и мощными басами\n\n"
        
        "😤 *Злой/Агрессивный?* - Тяжелая музыка\n"
        "• [Anger Release](https://music.yandex.ru/playlists/f77feb1c-d989-2781-5a47-7df7cb708f56)\n"
        "• Метал, Хардкор, Трэп\n\n"
        
        "😔 *Грустный?* - Эмоциональная музыка\n"
        "• [Emotional Workout](https://music.yandex.ru/playlists/4cebd30d-9e95-6434-cd8a-f32294872301)\n"
        "• Альтернативный рок, Эмо\n\n"
        
        "🎯 *Топ подборок по настроению:*\n"
        "1. *Утро понедельника* - Энергичная музыка\n"
        "2. *Предсоревновательная* - Агрессивная\n"
        "3. *Вечерняя тренировка* - Расслабляющая\n"
        "4. *Выходной день* - Разнообразная\n\n"
        
        "💡 *Совет:* Создайте свои плейлисты для разных настроений!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚡ Нет энергии", callback_data="music_energy"),
        InlineKeyboardButton(text="😤 Агрессивный", callback_data="music_angry")
    )
    builder.row(
        InlineKeyboardButton(text="😔 Грустный", callback_data="music_sad"),
        InlineKeyboardButton(text="🎉 Счастливый", callback_data="music_happy")
    )
    builder.row(
        InlineKeyboardButton(text="🎧 Платформы", callback_data="music_platforms"),
        InlineKeyboardButton(text="📊 BPM калькулятор", callback_data="music_bpm")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="gym_music"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔴 Яндекс.Музыка", url="https://music.yandex.ru"),
        InlineKeyboardButton(text="🟢 Spotify", url="https://open.spotify.com")
    )
    builder.row(
        InlineKeyboardButton(text="🟣 Apple Music", url="https://music.apple.com"),
        InlineKeyboardButton(text="⚫ SoundCloud", url="https://soundcloud.com")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="gym_music"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "music_bpm")
async def music_bpm(callback: CallbackQuery):
    """BPM калькулятор для тренировок"""
    text = (
        "📊 *BPM калькулятор для тренировок*\n\n"
        "BPM (Beats Per Minute) - удары в минуту\n\n"
        
        "🎯 *Рекомендованные BPM:*\n"
        "• Разминка: 100-120 BPM\n"
        "• Силовые тренировки: 130-150 BPM\n"
        "• Кардио (бег): 160-180 BPM\n"
        "• Кардио (велосипед): 120-140 BPM\n"
        "• Интервальные тренировки: 140-160 BPM\n"
        "• Растяжка/заминка: 60-90 BPM\n\n"
        
        "🔧 *Как найти BPM трека:*\n"
        "1. Используйте приложения: BPM Counter, Tap BPM\n"
        "2. В Spotify есть встроенный анализ BPM\n"
        "3. Сайты: songbpm.com, tunebat.com\n\n"
        
        "💡 *Советы по подбору музыки:*\n"
        "1. *Для жима лежа:* 140-150 BPM - мощный ритм\n"
        "2. *Для приседаний:* 130-140 BPM - устойчивый темп\n"
        "3. *Для бега:* 170-180 BPM - под шаги (90 шагов/нога)\n"
        "4. *Для велотренажера:* 120-130 BPM - под педалирование\n\n"
        
        "🎧 *Готовые подборки по BPM:*\n"
        "• [130-140 BPM Workout](https://music.yandex.ru/album/5595641)\n"
        "• [150-160 BPM Running](https://music.yandex.ru/album/16325377/track/85497103)\n"
        "• [170-180 BPM Sprint](https://music.yandex.ru/album/8840203)"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎧 Подборка 130 BPM", callback_data="music_bpm130"),
        InlineKeyboardButton(text="🎧 Подборка 150 BPM", callback_data="music_bpm150")
    )
    builder.row(
        InlineKeyboardButton(text="🎧 Подборка 170 BPM", callback_data="music_bpm170"),
        InlineKeyboardButton(text="📱 BPM приложения", callback_data="music_bpm_apps")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="gym_music"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Обработчики для настроения
@router.callback_query(F.data.startswith("music_"))
async def handle_music_mood(callback: CallbackQuery):
    """Обработчик музыки по настроению"""
    moods = {
        "music_energy": ("⚡ Музыка для энергии", "Быстрые треки, электроника, поп"),
        "music_angry": ("😤 Агрессивная музыка", "Метал, хардкор, трэп"),
        "music_sad": ("😔 Эмоциональная музыка", "Альтернативный рок, эмо, инди"),
        "music_happy": ("🎉 Веселая музыка", "Поп, фанк, диско, ретро"),
        "music_bpm130": ("🎧 Подборка 130-140 BPM", "Для силовых тренировок"),
        "music_bpm150": ("🎧 Подборка 150-160 BPM", "Для интервальных тренировок"),
        "music_bpm170": ("🎧 Подборка 170-180 BPM", "Для бега и кардио"),
        "music_bpm_apps": ("📱 Приложения для BPM", "BPM Counter, Tap BPM, SongBPM")
    }
    
    mood_data = moods.get(callback.data)
    if mood_data:
        title, description = mood_data
        await callback.answer(f"{title}: {description}")
    else:
        await callback.answer("Музыкальная подборка 🎵")