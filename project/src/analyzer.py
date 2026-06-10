"""Модуль анализатора прав доступа пользователей.

Содержит класс AccessAnalyzer, реализующий загрузку, хранение
и аналитическую обработку данных о пользователях и их правах доступа к ресурсам.
"""

import json
import logging
from collections import Counter, defaultdict
from typing import Generator, Dict, List, Any, Optional


logger = logging.getLogger(__name__)


class AccessAnalyzer:
    """Анализатор системы управления пользователями и правами доступа.

    Загружает данные пользователей из JSON-файла, хранит их в памяти
    и предоставляет набор аналитических методов: поиск популярных ресурсов,
    дублирующихся прав, пользователей без доступа и т.д.

    Attributes:
        _users_data (dict): Словарь пользователей, загруженных в память.
        _all_available_resources (list): Эталонный список всех ресурсов системы
            для поиска неиспользуемых.

    Example:
        >>> analyzer = AccessAnalyzer(all_available_resources=["server1", "db1"])
        >>> analyzer.load_users_from_generator("data/raw_users.json")
        >>> print(analyzer.find_top_n_resources(n=3))
    """

    def __init__(self, all_available_resources=None) -> None:
        """Инициализирует анализатор.

        Args:
            all_available_resources (list, optional): Эталонный список всех
                ресурсов системы. Используется в методе find_unused_resources.
                По умолчанию — пустой список.
        """
        self._users_data = {}
        self._all_available_resources = all_available_resources or []
        logger.info("Инициализирован объект AccessAnalyzer.")

    @property
    def users_data(self):
        """dict: Словарь загруженных пользователей (только для чтения)."""
        return self._users_data

    @property
    def all_available_resources(self):
        """list: Эталонный список всех ресурсов системы."""
        return self._all_available_resources

    @all_available_resources.setter
    def all_available_resources(self, resources):
        """Устанавливает эталонный список ресурсов.

        Args:
            resources (list): Новый список ресурсов в виде списка строк.

        Raises:
            ValueError: Если передан не список.
        """
        if not isinstance(resources, list):
            logger.error("Попытка установить некорректный тип для all_available_resources.")
            raise ValueError("Ресурсы должны быть переданы в виде списка строк.")
        self._all_available_resources = resources
        logger.debug(f"Обновлен список эталонных ресурсов: {len(resources)} элементов.")

    @staticmethod
    def read_data_generator(file_path: str) -> Generator[Dict, None, None]:
        """Генератор для построчного (поштучного) чтения пользователей из JSON-файла.

        Читает файл целиком (JSON-объект), но отдаёт записи по одной,
        не накапливая весь датасет в памяти в виде единого словаря.

        Args:
            file_path (str): Путь к JSON-файлу с данными пользователей.

        Yields:
            dict: Словарь вида ``{username: {role: ..., resources: [...]}}``.

        Raises:
            FileNotFoundError: Если файл по указанному пути не существует.
            json.JSONDecodeError: Если содержимое файла не является валидным JSON.

        Example:
            >>> for user in AccessAnalyzer.read_data_generator("data/raw_users.json"):
            ...     print(user)
        """
        logger.info(f"Начало потокового чтения файла: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for username, info in data.items():
                    yield {username: info}
        except FileNotFoundError:
            logger.error(f"Файл не найден: {file_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Файл поврежден или имеет неверный формат JSON: {file_path}")
            raise

    def load_users_from_generator(self, file_path: str) -> None:
        """Загружает данные пользователей в память через генератор.

        Очищает текущий словарь пользователей и заполняет его заново,
        используя read_data_generator для экономии памяти при чтении.

        Args:
            file_path (str): Путь к JSON-файлу с данными пользователей.

        Raises:
            FileNotFoundError: Если файл не найден.
            json.JSONDecodeError: Если JSON повреждён.
        """
        self._users_data.clear()
        for user_packet in self.read_data_generator(file_path):
            self._users_data.update(user_packet)
        logger.info(f"Успешно загружено {len(self._users_data)} пользователей в память для анализа.")

    def find_top_n_resources(self, n: int = 5) -> List[tuple]:
        """Находит топ-N самых популярных ресурсов по количеству пользователей.

        Args:
            n (int): Количество топовых ресурсов для возврата. По умолчанию 5.

        Returns:
            list[tuple]: Список пар ``(resource_name, count)``, отсортированных
                по убыванию популярности. Если данных нет — пустой список.

        Example:
            >>> analyzer.find_top_n_resources(n=3)
            [('server1', 42), ('db1', 31), ('api_v1', 28)]
        """
        logger.debug(f"Запрос топ-{n} популярных ресурсов.")
        resource_counter = Counter()
        for user_info in self._users_data.values():
            resource_counter.update(user_info.get("resources", []))
        return resource_counter.most_common(n)

    def find_unused_resources(self) -> List[str]:
        """Находит ресурсы, к которым ни один пользователь не имеет доступа.

        Сравнивает эталонный список all_available_resources с фактически
        используемыми ресурсами в загруженных данных.

        Returns:
            list[str]: Список ресурсов из all_available_resources, которые
                не встречаются ни у одного пользователя.
                Если all_available_resources не задан — возвращает пустой список.
        """
        logger.debug("Поиск неиспользуемых ресурсов.")
        used_resources = set()
        for user_info in self._users_data.values():
            used_resources.update(user_info.get("resources", []))
        unused = [res for res in self._all_available_resources if res not in used_resources]
        return unused

    def calculate_average_resources_per_user(self) -> float:
        """Вычисляет среднее количество ресурсов на одного пользователя.

        Returns:
            float: Среднее количество ресурсов, округлённое до 2 знаков.
                Возвращает ``0.0``, если база пользователей пуста.

        Example:
            >>> analyzer.calculate_average_resources_per_user()
            2.35
        """
        if not self._users_data:
            logger.warning("Расчет среднего количества ресурсов вызван для пустой базы пользователей.")
            return 0.0
        total_resources = sum(len(user_info.get("resources", [])) for user_info in self._users_data.values())
        avg = total_resources / len(self._users_data)
        return round(avg, 2)

    def find_users_with_zero_access(self) -> List[str]:
        """Находит пользователей, у которых список ресурсов пуст.

        Returns:
            list[str]: Список имён пользователей без назначенных ресурсов.
                Если таких нет — пустой список.
        """
        zero_users = [
            username for username, info in self._users_data.items()
            if not info.get("resources")
        ]
        return zero_users

    def find_duplicate_permissions(self) -> Dict[str, List[str]]:
        """Находит группы пользователей с одинаковыми наборами ресурсов.

        Сравнение ведётся по frozenset ресурсов, поэтому порядок элементов
        в списке ресурсов не важен.

        Returns:
            dict: Словарь, где ключ — строка с именами ресурсов через запятую
                (отсортированными), значение — список пользователей, у которых
                этот набор совпадает. Возвращаются только группы из 2+ человек.

        Example:
            >>> analyzer.find_duplicate_permissions()
            {'api_v1, db1, server1': ['alice', 'charlie']}
        """
        permissions_map = defaultdict(list)
        for username, info in self._users_data.items():
            resources_key = frozenset(info.get("resources", []))
            permissions_map[resources_key].append(username)
        duplicates = {
            ", ".join(sorted(list(res_set))): users
            for res_set, users in permissions_map.items()
            if len(users) > 1
        }
        return duplicates

    def count_users_by_resource_prefix(self, prefix: str) -> int:
        """Подсчитывает количество пользователей, имеющих доступ хотя бы к одному ресурсу с заданным префиксом.

        Args:
            prefix (str): Префикс для фильтрации ресурсов (например, ``"server"`` или ``"db"``).

        Returns:
            int: Число пользователей, у которых есть хотя бы один ресурс,
                начинающийся с указанного префикса.

        Example:
            >>> analyzer.count_users_by_resource_prefix("server")
            57
        """
        count = 0
        for user_info in self._users_data.values():
            has_prefix_access = any(
                res.startswith(prefix) for res in user_info.get("resources", [])
            )
            if has_prefix_access:
                count += 1
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует полное состояние объекта в словарь.

        Returns:
            dict: Словарь с ключами:
                - ``all_available_resources`` (list): эталонный список ресурсов;
                - ``users_data`` (dict): загруженные данные пользователей.

        Example:
            >>> state = analyzer.to_dict()
            >>> state.keys()
            dict_keys(['all_available_resources', 'users_data'])
        """
        logger.debug("Экспорт состояния объекта в dict.")
        return {
            "all_available_resources": self._all_available_resources,
            "users_data": self._users_data
        }

    def from_dict(self, state_dict: Dict[str, Any]) -> None:
        """Восстанавливает состояние объекта из словаря.

        Args:
            state_dict (dict): Словарь с ключами ``all_available_resources``
                и ``users_data``. Обычно получается из to_dict().

        Raises:
            ValueError: Если переданный аргумент не является словарём.
        """
        if not isinstance(state_dict, dict):
            logger.error("Неверный формат данных для восстановления состояния.")
            raise ValueError("Данные должны быть словарем.")
        self._all_available_resources = state_dict.get("all_available_resources", [])
        self._users_data.clear()
        self._users_data.update(state_dict.get("users_data", {}))
        logger.info("Состояние объекта успешно восстановлено из dict.")

    def save_state_to_file(self, file_path: str) -> None:
        """Сохраняет полное состояние объекта в JSON-файл.

        Использует to_dict() для получения состояния и записывает его
        в файл с отступами для читаемости.

        Args:
            file_path (str): Путь к файлу, в который будет записано состояние.

        Raises:
            Exception: При любой ошибке ввода-вывода.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
            logger.info(f"Полное состояние успешно сохранено в файл: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении состояния: {e}")
            raise

    def load_state_from_file(self, file_path: str) -> None:
        """Загружает состояние объекта из JSON-файла.

        Читает JSON-файл и передаёт его содержимое в from_dict().

        Args:
            file_path (str): Путь к JSON-файлу с сохранённым состоянием.

        Raises:
            FileNotFoundError: Если файл не найден.
            json.JSONDecodeError: Если содержимое файла повреждено.
            Exception: При любой другой ошибке ввода-вывода.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            self.from_dict(state_dict)
            logger.info(f"Полное состояние успешно загружено из файла: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке состояния: {e}")
            raise

    def export_analytical_report(self, file_path: str, top_n_count: int = 5, prefix_to_check: str = "server") -> None:
        """Формирует и сохраняет аналитический отчёт по всем задачам в JSON-файл.

        Структура отчёта:
            - ``meta``: метаинформация (количество проанализированных пользователей,
              описание);
            - ``results``: результаты всех аналитических методов:
                - ``top_popular_resources``: топ-N ресурсов по популярности;
                - ``unused_resources``: ресурсы без назначенных пользователей;
                - ``average_resources_per_user``: среднее число ресурсов на пользователя;
                - ``users_with_zero_access``: пользователи без ресурсов;
                - ``duplicate_permissions_groups``: группы с одинаковыми правами;
                - ``user_count_with_prefix_<prefix>``: число пользователей с ресурсами
                  по заданному префиксу.

        Args:
            file_path (str): Путь к файлу, в который будет записан отчёт.
            top_n_count (int): Количество топовых ресурсов. По умолчанию 5.
            prefix_to_check (str): Префикс ресурсов для подсчёта пользователей.
                По умолчанию ``"server"``.

        Raises:
            Exception: При ошибке записи файла.
        """
        logger.info(f"Формирование аналитического отчета в файл: {file_path}")
        report = {
            "meta": {
                "total_users_analyzed": len(self._users_data),
                "description": "Аналитический отчет по управлению пользователями и правами доступа"
            },
            "results": {
                "top_popular_resources": [
                    {"resource": res, "count": cnt} for res, cnt in self.find_top_n_resources(top_n_count)
                ],
                "unused_resources": self.find_unused_resources(),
                "average_resources_per_user": self.calculate_average_resources_per_user(),
                "users_with_zero_access": self.find_users_with_zero_access(),
                "duplicate_permissions_groups": self.find_duplicate_permissions(),
                f"user_count_with_prefix_{prefix_to_check}": self.count_users_by_resource_prefix(prefix_to_check)
            }
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=4)
            logger.info("Аналитический отчет успешно записан.")
        except Exception as e:
            logger.error(f"Не удалось записать аналитический отчет: {e}")