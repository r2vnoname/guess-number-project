import sqlite3
import random
import os

# ================================================================
# ШАГ 1: НАСТРОЙКА БАЗЫ ДАННЫХ
# ================================================================
DB_NAME = "game_history.db"

def init_database():
    """
    Создаёт таблицу attempts, если она ещё не существует.
    Поля таблицы:
      - id: уникальный номер попытки
      - game_id: номер игры (одна игра = много попыток)
      - secret_number: загаданное число (от 1 до 100)
      - guess: догадка игрока
      - hint: подсказка программы ('higher', 'lower' или 'correct')
      - attempt_number: номер попытки внутри игры (1, 2, 3...)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            secret_number INTEGER NOT NULL,
            guess INTEGER NOT NULL,
            hint TEXT NOT NULL,
            attempt_number INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def get_next_game_id():
    """
    Вспомогательная функция: вычисляет номер следующей игры.
    Запрашивает максимальный game_id из базы и прибавляет 1.
    Если таблица пуста — возвращает 1.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(game_id) FROM attempts")
    result = cursor.fetchone()[0]
    conn.close()
    return 1 if result is None else result + 1


def save_attempt(game_id, secret, guess, hint, attempt_number):
    """
    Сохраняет одну попытку в базу данных.
    Параметры:
      - game_id: номер текущей игры
      - secret: загаданное число
      - guess: число, которое ввёл игрок
      - hint: подсказка ('higher', 'lower', 'correct')
      - attempt_number: порядковый номер попытки
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attempts (game_id, secret_number, guess, hint, attempt_number)
        VALUES (?, ?, ?, ?, ?)
    ''', (game_id, secret, guess, hint, attempt_number))
    conn.commit()
    conn.close()


# ================================================================
# ШАГ 2: АЛГОРИТМ ПОЛУЧЕНИЯ ПОДСКАЗКИ (вспомогательный)
# ================================================================
def get_hint(secret, guess):
    """
    Сравнивает загаданное число с догадкой игрока.
    Возвращает:
      - 'higher' — если нужно загадать число больше
      - 'lower'  — если нужно загадать число меньше
      - 'correct' — если игрок угадал
    """
    if guess < secret:
        return 'higher'
    elif guess > secret:
        return 'lower'
    else:
        return 'correct'


# ================================================================
# ШАГ 3: АЛГОРИТМ АНАЛИЗА ЭФФЕКТИВНОСТИ ИГРОКА
# ================================================================
def analyze_performance(secret_number, player_attempts):
    """
    Это главный аналитический алгоритм проекта.
    Он выполняет следующие операции:
    1. Запрашивает из базы ВСЕ прошлые игры с ТЕМ ЖЕ загаданным числом.
    2. Для каждой игры вычисляет количество попыток.
    3. Считает:
       - Среднее количество попыток у всех игроков.
       - Минимальное количество попыток (лучший результат).
       - Сравнивает результат текущего игрока со средним.
    Возвращает словарь с результатами анализа.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем все завершённые игры с таким же загаданным числом,
    # группируем по game_id и считаем количество попыток в каждой
    cursor.execute('''
        SELECT game_id, COUNT(*) as tries
        FROM attempts
        WHERE secret_number = ? AND game_id != (
            SELECT MAX(game_id) FROM attempts
        )
        GROUP BY game_id
    ''', (secret_number,))

    past_games = cursor.fetchall()
    conn.close()

    # Если никто раньше не играл с этим числом — статистики нет
    if not past_games:
        return {
            "total_games": 0,
            "average": None,
            "best": None,
            "player_attempts": player_attempts,
            "verdict": "Это первая игра с данным числом! Вы — первопроходец."
        }

    # Извлекаем список количества попыток для каждой прошлой игры
    attempts_list = [row[1] for row in past_games]

    # Вычисляем статистические показатели
    avg = sum(attempts_list) / len(attempts_list)
    best = min(attempts_list)

    # Сравниваем игрока со средним значением (это и есть "советник")
    if player_attempts < avg:
        verdict = f"Отлично! Ваш результат ({player_attempts}) ЛУЧШЕ среднего ({avg:.1f}). Так держать!"
    elif player_attempts == avg:
        verdict = f"Вы сыграли ровно на среднем уровне ({avg:.1f} попыток)."
    else:
        verdict = f"Ваш результат ({player_attempts}) ХУЖЕ среднего ({avg:.1f}). Попробуйте стратегию бинарного поиска!"

    return {
        "total_games": len(past_games),
        "average": round(avg, 1),
        "best": best,
        "player_attempts": player_attempts,
        "verdict": verdict
    }


# ================================================================
# ШАГ 4: ОСНОВНОЙ ИГРОВОЙ ЦИКЛ
# ================================================================
def play_game():
    """
    Проводит одну игру "Угадай число".
    1. Генерирует случайное число от 1 до 100.
    2. Даёт игроку неограниченное число попыток с подсказками.
    3. Сохраняет ВСЕ попытки в базу данных.
    4. После завершения запускает алгоритм анализа.
    """
    secret = random.randint(1, 100)
    game_id = get_next_game_id()
    attempt_num = 0
    guessed = False

    print("\n" + "=" * 50)
    print(f"  ИГРА #{game_id}: Я загадал число от 1 до 100. Угадайте!")
    print("=" * 50)

    while not guessed:
        # Защита от некорректного ввода
        try:
            guess = int(input("  Ваше число: "))
        except ValueError:
            print("  Пожалуйста, введите целое число!")
            continue

        if guess < 1 or guess > 100:
            print("  Число должно быть от 1 до 100!")
            continue

        attempt_num += 1
        hint = get_hint(secret, guess)

        # Сохраняем попытку в БД
        save_attempt(game_id, secret, guess, hint, attempt_num)

        # Подсказываем игроку
        if hint == 'higher':
            print(f"  ↟ Попытка {attempt_num}: Загаданное число БОЛЬШЕ {guess}")
        elif hint == 'lower':
            print(f"  ↡ Попытка {attempt_num}: Загаданное число МЕНЬШЕ {guess}")
        else:
            print(f"  ★ Попытка {attempt_num}: ВЫ УГАДАЛИ! Это число {secret}.")
            guessed = True

    return game_id, secret, attempt_num


def show_analysis(game_id, secret, player_attempts):
    """
    Выводит на экран результаты алгоритма анализа.
    """
    print("\n" + "─" * 50)
    print("  АНАЛИЗ ЭФФЕКТИВНОСТИ (ИИ-Советник)")
    print("─" * 50)

    stats = analyze_performance(secret, player_attempts)

    print(f"  Загаданное число: {secret}")
    print(f"  Ваш результат: {player_attempts} попыток")
    print(f"  ─────────────────────────────")

    if stats["total_games"] == 0:
        print(f"  {stats['verdict']}")
    else:
        print(f"  Сыграно игр с этим числом: {stats['total_games']}")
        print(f"  Средний результат игроков: {stats['average']} попыток")
        print(f"  Лучший результат: {stats['best']} попыток")
        print(f"  ─────────────────────────────")
        print(f"  {stats['verdict']}")

    print("─" * 50)


def show_top_players():
    """
    Дополнительный алгоритм: показывает ТОП-5 самых эффективных игр
    (с наименьшим количеством попыток) за всё время.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT game_id, secret_number, COUNT(*) as tries
        FROM attempts
        WHERE hint = 'correct'
        GROUP BY game_id
        ORDER BY tries ASC
        LIMIT 5
    ''')
    results = cursor.fetchall()
    conn.close()

    if not results:
        print("\n  Нет завершённых игр для статистики.")
        return

    print("\n" + "─" * 50)
    print("  ТОП-5 ЛУЧШИХ ИГР (Зал славы)")
    print("─" * 50)
    for i, (game_id, secret, tries) in enumerate(results, 1):
        print(f"  {i}. Игра #{game_id}: число {secret} угадано за {tries} попыток")
    print("─" * 50)


# ================================================================
# ШАГ 5: ГЛАВНОЕ МЕНЮ ПРОГРАММЫ
# ================================================================
def main():
    """Главная функция: инициализация БД и главное меню."""
    init_database()
    print("\n╔══════════════════════════════════════╗")
    print("║   УГАДАЙ ЧИСЛО с ИИ-СОВЕТНИКОМ v1.0 ║")
    print("╚══════════════════════════════════════╝")

    while True:
        print("\n  МЕНЮ:")
        print("  1. Сыграть в игру")
        print("  2. Показать ТОП-5 лучших игр")
        print("  3. Выход")
        choice = input("  Ваш выбор: ")

        if choice == '1':
            game_id, secret, attempts = play_game()
            show_analysis(game_id, secret, attempts)
            input("\n  Нажмите Enter для продолжения...")

        elif choice == '2':
            show_top_players()
            input("\n  Нажмите Enter для продолжения...")

        elif choice == '3':
            print("\n  Спасибо за игру! До свидания.")
            break

        else:
            print("  Неверный ввод. Попробуйте снова.")


# Точка входа в программу
if __name__ == "__main__":
    main()
