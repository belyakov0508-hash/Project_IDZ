import os
import logging
from src.analyzer import AccessAnalyzer

def setup_logging():
    """Настраивает глобальное логирование для всего приложения."""
    # Определяем путь к лог-файлу в корне проекта (на уровень выше папки src)
    log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.log"))

    logging.basicConfig(
        level=logging.DEBUG,  # Общий уровень перехвата (DEBUG поймает и INFO, и DEBUG)
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            # Логируем строго в файл с кодировкой utf-8
            logging.FileHandler(log_path, encoding="utf-8")
        ]
    )

    # Создаем логгер для текущего файла main.py
    logger = logging.getLogger(__name__)
    logger.info("Приложение запущено. Логирование успешно настроено.")
    return logger


# =========================================================================
# ТОЧКА ВХОДА В ПРОГРАММУ
# =========================================================================
def main():
    # Инициализируем логирование
    logger = setup_logging()

    # Относительные пути к файлам данных (выходим из src/ в корень, затем в data/)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(base_dir, "data")

    # Пути к конкретным файлам
    raw_data_file = os.path.join(data_dir, "raw_users.json")
    report_file = os.path.join(data_dir, "report.json")
    state_file = os.path.join(data_dir, "state.json")

    # Проверяем, существует ли папка data. Если нет — создаем ее
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.warning(f"Папка {data_dir} отсутствовала и была создана.")

    # Проверяем, положили ли вы сгенерированный нейросетью файл
    if not os.path.exists(raw_data_file):
        logger.error(f"Исходный файл данных не найден по пути: {raw_data_file}")
        print(f"Ошибка: Пожалуйста, положите ваш JSON-файл от нейросети в: {raw_data_file}")
        return

    print("--- Старт аналитической системы ---")

    # 1. Задаем эталонный список ресурсов для поиска неиспользуемых (из задания)
    reference_resources = [
        "server1", "server2", "server3", "server4",
        "db1", "db2", "db3", "api_v1", "api_v2", "unused_test_hub"
    ]

    # 2. Создаем экземпляр анализатора
    analyzer = AccessAnalyzer(all_available_resources=reference_resources)

    # 3. Загружаем данные пользователей через ленивый генератор
    try:
        analyzer.load_users_from_generator(raw_data_file)
    except Exception as e:
        logger.critical(f"Не удалось загрузить данные: {e}")
        print("Критическая ошибка при чтении данных. Проверьте app.log.")
        return

    # 4. Демонстрируем работу аналитических методов в консоли (опционально)
    print(f"Успешно загружено пользователей: {len(analyzer.users_data)}")
    print(f"Среднее количество ресурсов на пользователя: {analyzer.calculate_average_resources_per_user()}")

    top_3 = analyzer.find_top_n_resources(n=3)
    print(f"Топ-3 популярных ресурса: {top_3}")

    zero_access = analyzer.find_users_with_zero_access()
    print(f"Пользователей с нулевым доступом: {len(zero_access)}")

    # 5. Экспортируем официальный аналитический отчет в report.json
    print("\nФормирование аналитического отчета...")
    analyzer.export_analytical_report(
        file_path=report_file,
        top_n_count=5,
        prefix_to_check="server"
    )

    # 6. Тестируем сериализацию полного состояния (to_dict / from_dict)
    print("Сохранение полного состояния объекта...")
    analyzer.save_state_to_file(state_file)

    print("Проверка восстановления состояния из файла...")
    new_analyzer = AccessAnalyzer()
    new_analyzer.load_state_from_file(state_file)
    print(f"Состояние успешно восстановлено! Загружено записей: {len(new_analyzer.users_data)}")

    print("\n--- Работа программы успешно завершена ---")
    print(f"Результаты и логи сохранены в корневой папке проекта.")


if __name__ == "__main__":
    main()