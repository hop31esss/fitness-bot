from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date
import logging

from database.base import db

router = Router()
logger = logging.getLogger(__name__)

async def init_workout_tables():
    """Создание таблиц для тренировок"""
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Таблица workout_sessions создана")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                exercise_type TEXT DEFAULT 'strength',
                sets INTEGER,
                reps INTEGER,
                weight REAL,
                duration INTEGER,
                distance REAL,
                notes TEXT,
                order_num INTEGER
            )
        """)
        logger.info("✅ Таблица workout_exercises создана")
        await db.execute("""
            ALTER TABLE workout_exercises ADD COLUMN completed BOOLEAN DEFAULT FALSE
        """)
        logger.info("✅ Колонка 'completed' добавлена")
        
    except Exception as e:
        # Если колонка уже существует - игнорируем ошибку
        if "duplicate column name" not in str(e):
            logger.error(f"❌ Ошибка: {e}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {e}")
        return False

class WorkoutSessionStates(StatesGroup):
    choosing_exercise_type = State()
    entering_exercise_name = State()
    entering_sets = State()
    choosing_reps_method = State()  # НОВОЕ: выбор метода ввода повторений
    entering_set_data = State()
    entering_set_reps = State()      # НОВОЕ: ввод повторений по подходам
    entering_reps = State()          # для одинаковых повторений
    choosing_weight_method = State()  # выбор метода ввода веса
    entering_set_weights = State()    # ввод веса по подходам
    entering_weight = State()         # для одного веса
    entering_duration = State()
    entering_distance = State()

@router.callback_query(F.data == "start_workout")
async def start_workout(callback: CallbackQuery, state: FSMContext):
    await init_workout_tables()
    
    user_id = callback.from_user.id
    today = date.today().isoformat()
    current_time = datetime.now().strftime("%H:%M")
    
    try:
        await db.execute(
            "INSERT INTO workout_sessions (user_id, date, start_time) VALUES (?, ?, ?)",
            (user_id, today, current_time)
        )
        result = await db.fetch_one("SELECT last_insert_rowid() as id")
        session_id = result['id']
        await state.update_data(session_id=session_id, exercises=[])
        await show_workout_menu(callback.message, state)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await callback.message.answer("❌ Ошибка создания тренировки")
    await callback.answer()

async def show_workout_menu(message, state: FSMContext):
    """Показать меню тренировки с деталями"""
    data = await state.get_data()
    exercises = data.get('exercises', [])
    
    text = "🏋️ *ТЕКУЩАЯ ТРЕНИРОВКА*\n\n"
    
    if exercises:
        text += "*Упражнения:*\n"
        for i, ex in enumerate(exercises, 1):
            if ex['type'] == 'strength':
                text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps_display']} ({ex['weight_display']})\n"
                
                # Детали по подходам (если нужно)
                if 'set_data' in ex:
                    details = ""
                    for j, s in enumerate(ex['set_data'], 1):
                        weight = f"{s['weight']} кг" if s['weight'] else "б/в"
                        details += f"   {j}. {weight} × {s['reps']}\n"
                    text += details
                    
            elif ex['type'] == 'cardio':
                text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
            else:  # stretch
                text += f"{i}. {ex['name']}: {ex['duration']} мин (растяжка)\n"
        text += "\n"
    else:
        text += "Пока нет упражнений. Добавьте первое!\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_to_workout")
    )
    builder.row(
        InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ ТРЕНИРОВКУ", callback_data="finish_workout"),
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_workout")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

async def save_exercise_from_set_data(state: FSMContext, message: Message):
    """Сохранить упражнение из данных по подходам"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type'],
        'sets': data['sets'],
        'set_data': data['set_data']
    }
    
    # Формируем отображение
    weight_values = [s['weight'] for s in data['set_data'] if s['weight'] is not None]
    reps_values = [s['reps'] for s in data['set_data']]
    
    if weight_values:
        min_w = min(weight_values)
        max_w = max(weight_values)
        weight_display = f"{min_w}-{max_w} кг" if min_w != max_w else f"{min_w} кг"
    else:
        weight_display = "б/в"
    
    if len(set(reps_values)) == 1:
        reps_display = str(reps_values[0])
    else:
        min_r = min(reps_values)
        max_r = max(reps_values)
        reps_display = f"{min_r}-{max_r}"
    
    exercise['weight_display'] = weight_display
    exercise['reps_display'] = reps_display
    
    # Добавляем к списку упражнений
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    # Сохраняем в БД (усреднённые данные)
    session_id = data['session_id']
    order_num = len(exercises)
    
    try:
        if exercise['type'] == 'strength':
            avg_weight = sum(weight_values) / len(weight_values) if weight_values else None
            avg_reps = sum(reps_values) / len(reps_values)
            
            await db.execute("""
                INSERT INTO workout_exercises 
                (session_id, exercise_name, exercise_type, sets, reps, weight, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, exercise['name'], 'strength', 
                  exercise['sets'], avg_reps, avg_weight,
                  order_num))
                  
        logger.info(f"✅ Упражнение {exercise['name']} сохранено")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения упражнения: {e}")    

@router.callback_query(F.data == "add_to_workout")
async def add_to_workout(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ СИЛОВОЕ", callback_data="ex_type_strength"),
        InlineKeyboardButton(text="🏃 КАРДИО", callback_data="ex_type_cardio")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_workout")
    )
    await callback.message.edit_text("Выберите тип упражнения:", reply_markup=builder.as_markup())
    await state.set_state(WorkoutSessionStates.choosing_exercise_type)
    await callback.answer()

@router.callback_query(F.data.startswith("ex_type_"))
async def process_exercise_type(callback: CallbackQuery, state: FSMContext):
    ex_type = callback.data.replace("ex_type_", "")
    await state.update_data(current_exercise_type=ex_type)
    await callback.message.edit_text("Введите название упражнения:")
    await state.set_state(WorkoutSessionStates.entering_exercise_name)
    await callback.answer()

@router.message(WorkoutSessionStates.entering_exercise_name)
async def process_exercise_name(message: Message, state: FSMContext):
    await state.update_data(exercise_name=message.text.strip())
    data = await state.get_data()
    if data['current_exercise_type'] == 'strength':
        await message.answer("Введите количество подходов:")
        await state.set_state(WorkoutSessionStates.entering_sets)
    else:
        await message.answer("Введите длительность (мин):")
        await state.set_state(WorkoutSessionStates.entering_duration)

@router.message(WorkoutSessionStates.entering_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов - начинаем ввод данных по подходам"""
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
        
        # Инициализируем данные для подходов
        set_data = []
        for i in range(sets):
            set_data.append({'weight': None, 'reps': None})
        
        await state.update_data(
            sets=sets,
            set_data=set_data,
            current_set=1
        )
        
        # Начинаем с первого подхода - спрашиваем вес
        await message.answer(
            f"⚖️ *Подход 1 из {sets}*\n\n"
            f"Введите вес (кг) или '-' если без веса:"
        )
        await state.set_state(WorkoutSessionStates.entering_set_data)
        
    except ValueError:
        await message.answer("❌ Введите число")
@router.callback_query(F.data == "weight_one")
async def weight_one_method(callback: CallbackQuery, state: FSMContext):
    """Ввод одного веса для всех подходов"""
    await callback.message.edit_text(
        "⚖️ Введите вес (кг) для всех подходов или '-' если без веса:"
    )
    await state.set_state(WorkoutSessionStates.entering_weight)
    await callback.answer()

@router.callback_query(F.data == "reps_same")
async def reps_same_method(callback: CallbackQuery, state: FSMContext):
    """Одинаковые повторения для всех подходов"""
    await callback.message.edit_text(
        "🔄 Введите количество повторений (одинаково для всех подходов):"
    )
    await state.set_state(WorkoutSessionStates.entering_reps)
    await callback.answer()

@router.callback_query(F.data == "reps_each")
async def reps_each_method(callback: CallbackQuery, state: FSMContext):
    """Разные повторения для каждого подхода"""
    data = await state.get_data()
    sets = data['sets']
    
    await state.update_data(current_set=1, reps_list=[])
    await callback.message.edit_text(
        f"🔄 *Подход 1 из {sets}*\n\n"
        f"Введите количество повторений для первого подхода:"
    )
    await state.set_state(WorkoutSessionStates.entering_set_reps)
    await callback.answer()

@router.callback_query(F.data == "weight_each")
async def weight_each_method(callback: CallbackQuery, state: FSMContext):
    """Ввод веса для каждого подхода"""
    data = await state.get_data()
    sets = data['sets']
    
    await state.update_data(current_set=1, weights=[])
    await callback.message.edit_text(
        f"⚖️ *Подход 1 из {sets}*\n\n"
        f"Введите вес для первого подхода (или '-' без веса):"
    )
    await state.set_state(WorkoutSessionStates.entering_set_weights)
    await callback.answer()

@router.message(WorkoutSessionStates.entering_set_data)
async def process_set_data(message: Message, state: FSMContext):
    """Обработка ввода данных для текущего подхода (сначала вес, потом повторения)"""
    data = await state.get_data()
    current_set = data['current_set']
    total_sets = data['sets']
    set_data = data['set_data']
    
    # Проверяем, что сейчас вводим - вес или повторения
    current_entry = set_data[current_set-1]
    
    # Если вес ещё не введён
    if current_entry['weight'] is None:
        # Сохраняем вес
        if message.text == '-':
            current_entry['weight'] = None
        else:
            try:
                weight = float(message.text)
                current_entry['weight'] = weight
            except ValueError:
                await message.answer("❌ Введите число или '-'")
                return
        
        # Спрашиваем повторения
        await message.answer(
            f"🔄 *Подход {current_set} из {total_sets}*\n\n"
            f"Введите количество повторений:"
        )
        
    else:
        # Сохраняем повторения
        try:
            reps = int(message.text)
            if reps <= 0:
                raise ValueError
            current_entry['reps'] = reps
            
            # Обновляем данные
            set_data[current_set-1] = current_entry
            await state.update_data(set_data=set_data)
            
            # Переходим к следующему подходу или завершаем
            if current_set < total_sets:
                current_set += 1
                await state.update_data(current_set=current_set)
                
                # Спрашиваем вес для следующего подхода
                await message.answer(
                    f"⚖️ *Подход {current_set} из {total_sets}*\n\n"
                    f"Введите вес (кг) или '-' если без веса:"
                )
            else:
                # Все подходы введены - сохраняем упражнение
                await save_exercise_from_set_data(state, message)
                await show_workout_menu(message, state)
                
        except ValueError:
            await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_set_reps)
async def process_set_reps(message: Message, state: FSMContext):
    """Обработка повторений для текущего подхода"""
    data = await state.get_data()
    current_set = data['current_set']
    total_sets = data['sets']
    reps_list = data.get('reps_list', [])
    
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        reps_list.append(reps)
        await state.update_data(reps_list=reps_list)
        
        # Если есть еще подходы
        if current_set < total_sets:
            current_set += 1
            await state.update_data(current_set=current_set)
            await message.answer(
                f"🔄 *Подход {current_set} из {total_sets}*\n\n"
                f"Введите количество повторений для {current_set}-го подхода:"
            )
        else:
            # Все повторения введены, теперь спрашиваем про вес
            await ask_weight_method(message, state)
            
    except ValueError:
        await message.answer("❌ Введите число")
async def ask_weight_method(message: Message, state: FSMContext):
    """Спрашивает про способ ввода веса"""
    data = await state.get_data()
    sets = data['sets']
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ОДИН ВЕС", callback_data="weight_one"),
        InlineKeyboardButton(text="📊 ПО ПОДХОДАМ", callback_data="weight_each")
    )
    
    await message.answer(
        f"⚖️ *Ввод веса*\n\n"
        f"У вас {sets} подходов. Как вводить вес?\n\n"
        f"• Один вес - одинаковый для всех подходов\n"
        f"• По подходам - разный вес для каждого",
        reply_markup=builder.as_markup()
    )
    await state.set_state(WorkoutSessionStates.choosing_weight_method)

@router.message(WorkoutSessionStates.entering_set_weights)
async def process_set_weight(message: Message, state: FSMContext):
    """Обработка веса для текущего подхода"""
    data = await state.get_data()
    current_set = data['current_set']
    total_sets = data['sets']
    weights = data.get('weights', [])
    
    # Сохраняем вес текущего подхода
    if message.text == '-':
        weights.append(None)
    else:
        try:
            weight = float(message.text)
            weights.append(weight)
        except ValueError:
            await message.answer("❌ Введите число или '-'")
            return
    
    await state.update_data(weights=weights)
    
    # Если есть еще подходы
    if current_set < total_sets:
        current_set += 1
        await state.update_data(current_set=current_set)
        await message.answer(
            f"⚖️ *Подход {current_set} из {total_sets}*\n\n"
            f"Введите вес для {current_set}-го подхода:"
        )
    else:
        # Все веса введены, теперь повторения
        await state.update_data(weight_method='each')
        await message.answer(
            f"🔄 *Повторения*\n\n"
            f"Введите количество повторений для всех подходов (одинаково):"
        )
        await state.set_state(WorkoutSessionStates.entering_reps)

@router.message(WorkoutSessionStates.entering_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений (одинаковых для всех подходов)"""
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        await state.update_data(reps=reps)
        
        # Проверяем метод ввода веса
        data = await state.get_data()
        if data.get('weight_method') == 'each':
            # Уже есть все веса
            await save_exercise_with_weights(state, message)
        else:
            # Будем вводить один вес
            await message.answer("⚖️ Введите вес (кг) или '-'")
            await state.set_state(WorkoutSessionStates.entering_weight)
            
    except ValueError:
        await message.answer("❌ Введите число")



async def save_exercise_with_weights(state: FSMContext, message: Message): #noqa
    """Сохранить упражнение с разными весами по подходам"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type'],
        'sets': data['sets'],
        'reps': data['reps'],
        'weights': data.get('weights', [])
    }
    
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    # Сохраняем в базу (пока упрощенно - сохраняем средний вес)
    session_id = data['session_id']
    order_num = len(exercises)
    
    # Вычисляем средний вес для отображения
    weights = [w for w in data.get('weights', []) if w]
    avg_weight = sum(weights) / len(weights) if weights else None
    
    await db.execute("""
        INSERT INTO workout_exercises 
        (session_id, exercise_name, exercise_type, sets, reps, weight, order_num)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, exercise['name'], 'strength', 
          exercise['sets'], exercise['reps'], avg_weight,
          order_num))
    
    # Показываем детали
    weight_details = ""
    if weights:
        weight_details = "\n*Вес по подходам:*\n"
        for i, w in enumerate(weights, 1):
            w_text = f"{w} кг" if w else "б/в"
            weight_details += f"  {i}. {w_text}\n"
    
    await message.answer(
        f"✅ *Упражнение добавлено!*\n\n"
        f"🏋️ {exercise['name']}\n"
        f"📊 {exercise['sets']}×{exercise['reps']}\n"
        f"{weight_details}"
    )
    
    await show_workout_menu(message, state)

@router.message(WorkoutSessionStates.entering_reps)
async def process_reps(message: Message, state: FSMContext):
    try:
        reps = int(message.text)
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг) или '-'")
        await state.set_state(WorkoutSessionStates.entering_weight)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_weight)
async def process_weight(message: Message, state: FSMContext):
    weight = None if message.text == '-' else float(message.text)
    await state.update_data(weight=weight)
    await save_exercise(state, message)
    await show_workout_menu(message, state)

@router.message(WorkoutSessionStates.entering_duration)
async def process_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
        await state.update_data(duration=duration)
        data = await state.get_data()
        if data['current_exercise_type'] == 'cardio':
            await message.answer("Введите дистанцию (км):")
            await state.set_state(WorkoutSessionStates.entering_distance)
        else:
            await save_exercise(state, message)
            await show_workout_menu(message, state)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_distance)
async def process_distance(message: Message, state: FSMContext):
    try:
        distance = float(message.text.replace(',', '.'))
        await state.update_data(distance=distance)
        await save_exercise(state, message)
        await show_workout_menu(message, state)
    except ValueError:
        await message.answer("❌ Введите число")

async def save_exercise(state: FSMContext, message: Message):
    """Сохранить упражнение с учетом разных повторений"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type'],
        'sets': data['sets']
    }
    
    # Сохраняем повторения (список или одно значение)
    if 'reps_list' in data:
        exercise['reps_list'] = data['reps_list']
        # Для отображения покажем диапазон
        min_reps = min(data['reps_list'])
        max_reps = max(data['reps_list'])
        reps_display = f"{min_reps}-{max_reps}" if min_reps != max_reps else str(min_reps)
        exercise['reps_display'] = reps_display
        exercise['reps'] = data['reps_list'][0]  # для БД возьмем первое значение (можно сохранять все)
    else:
        exercise['reps'] = data['reps']
        exercise['reps_display'] = str(data['reps'])
    
    # Сохраняем вес (список или одно значение)
    if 'weights' in data:
        exercise['weights'] = data['weights']
        weights = [w for w in data['weights'] if w]
        if weights:
            min_w = min(weights)
            max_w = max(weights)
            weight_display = f"{min_w}-{max_w} кг" if min_w != max_w else f"{min_w} кг"
        else:
            weight_display = "б/в"
        exercise['weight_display'] = weight_display
    else:
        exercise['weight'] = data.get('weight')
        weight_display = f"{data.get('weight')} кг" if data.get('weight') else "б/в"
        exercise['weight_display'] = weight_display
    
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    # Сохраняем в БД (упрощенно - для сложных случаев нужно менять структуру БД)
    session_id = data['session_id']
    order_num = len(exercises)
    
    try:
        if exercise['type'] == 'strength':
            # Сохраняем усредненные данные (пока так)
            avg_weight = None
            if 'weights' in exercise:
                w = [w for w in exercise['weights'] if w]
                avg_weight = sum(w) / len(w) if w else None
            else:
                avg_weight = exercise.get('weight')
            
            avg_reps = None
            if 'reps_list' in exercise:
                avg_reps = sum(exercise['reps_list']) / len(exercise['reps_list'])
            else:
                avg_reps = exercise.get('reps')
            
            await db.execute("""
                INSERT INTO workout_exercises 
                (session_id, exercise_name, exercise_type, sets, reps, weight, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, exercise['name'], 'strength', 
                  exercise['sets'], avg_reps, avg_weight,
                  order_num))
        else:
            # кардио и растяжка без изменений
            pass
            
        logger.info(f"✅ Упражнение {exercise['name']} сохранено")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения упражнения: {e}")
        
from services.stats_updater import update_user_stats
@router.callback_query(F.data == "finish_workout")
async def finish_workout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    session_id = data['session_id']
    await db.execute(
        "UPDATE workout_sessions SET end_time = ? WHERE id = ?",
        (datetime.now().strftime("%H:%M"), session_id)
    )
    await callback.message.edit_text(
        "✅ *Тренировка завершена!*\n\n💪 Отличная работа!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
        ).as_markup()
    )
    await update_user_stats(callback.from_user.id)
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_workout")
async def cancel_workout(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Тренировка отменена")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "back_to_workout")
async def back_to_workout(callback: CallbackQuery, state: FSMContext):
    await show_workout_menu(callback.message, state)
    await callback.answer()