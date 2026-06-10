# pytest tests/
import os
import json
import unittest
from src.analyzer import AccessAnalyzer


class TestAccessAnalyzer(unittest.TestCase):
    """Набор тестов для проверки класса AccessAnalyzer."""

    def setUp(self) -> None:
        """Метод выполняется ПЕРЕД каждым тест-кейсом.

        Здесь мы готовим эталонные тестовые данные и временные пути к файлам.
        """
        self.reference_resources = ["server1", "server2", "db1", "db2", "api_v1", "unused_res"]
        self.analyzer = AccessAnalyzer(all_available_resources=self.reference_resources)

        # Тестовый набор пользователей (наш мини-датасет)
        self.test_data = {
            "alice": {"role": "admin", "resources": ["server1", "db1", "api_v1"]},
            "bob": {"role": "user", "resources": ["server1", "db2"]},
            "charlie": {"role": "user", "resources": ["server1", "db1", "api_v1"]},
            "eva": {"role": "guest", "resources": []},
            "jack": {"role": "user", "resources": ["db2"]}
        }

        # Пути к временным файлам для тестов
        self.valid_json_path = "test_valid.json"
        self.invalid_json_path = "test_invalid.json"
        self.output_report_path = "test_report.json"
        self.output_state_path = "test_state.json"

        # Создаем валидный JSON-файл для тестов
        with open(self.valid_json_path, "w", encoding="utf-8") as f:
            json.dump(self.test_data, f)

        # Создаем поврежденный JSON-файл
        with open(self.invalid_json_path, "w", encoding="utf-8") as f:
            f.write("{ 'broken_json': true, missing_quotes }")

    def tearDown(self) -> None:
        """Метод выполняется ПОСЛЕ каждого тест-кейса.

        Удаляет все временные файлы, чтобы не мусорить в проекте.
        """
        for path in [self.valid_json_path, self.invalid_json_path,
                     self.output_report_path, self.output_state_path]:
            if os.path.exists(path):
                os.remove(path)

    def test_load_users_from_generator_success(self):
        """Позитивный тест: успешная загрузка данных через генератор."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        self.assertEqual(len(self.analyzer.users_data), 5)
        self.assertIn("alice", self.analyzer.users_data)

    def test_find_top_n_resources(self):
        """Позитивный тест: поиск самых популярных ресурсов."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        # 'server1' есть у alice, bob, charlie (3 раза)
        # 'db1' есть у alice, charlie (2 раза)
        top_res = self.analyzer.find_top_n_resources(n=2)

        self.assertEqual(top_res[0], ("server1", 3))
        self.assertEqual(top_res[1], ("db1", 2))

    def test_find_unused_resources(self):
        """Позитивный тест: поиск неиспользуемых ресурсов из списка."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        unused = self.analyzer.find_unused_resources()
        # "server2" и "unused_res" никому не выданы
        self.assertIn("server2", unused)
        self.assertIn("unused_res", unused)
        self.assertNotIn("server1", unused)

    def test_calculate_average_resources(self):
        """Позитивный тест: расчет среднего количества ресурсов на пользователя."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        # Всего ресурсов: 3 (alice) + 2 (bob) + 3 (charlie) + 0 (eva) + 1 (jack) = 9
        # Пользователей: 5.  9 / 5 = 1.8
        avg = self.analyzer.calculate_average_resources_per_user()
        self.assertEqual(avg, 1.8)

    def test_find_users_with_zero_access(self):
        """Позитивный тест: поиск пользователей с нулевым доступом."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        zero_users = self.analyzer.find_users_with_zero_access()
        self.assertEqual(zero_users, ["eva"])

    def test_find_duplicate_permissions(self):
        """Позитивный тест: поиск дубликатов прав."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        duplicates = self.analyzer.find_duplicate_permissions()

        # У alice и charlie одинаковый набор прав: "api_v1, db1, server1"
        # Проверяем, что в значениях словаря дубликатов есть обе эти учетки
        found_group = False
        for users in duplicates.values():
            if "alice" in users and "charlie" in users:
                found_group = True
        self.assertTrue(found_group)

    def test_count_users_by_resource_prefix(self):
        """Позитивный тест: подсчет пользователей по префиксу ресурса."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        # Префикс 'server' есть у alice, bob, charlie (3 пользователя)
        count = self.analyzer.count_users_by_resource_prefix("server")
        self.assertEqual(count, 3)

    def test_serialization_state(self):
        """Позитивный тест: проверка полного сохранения и загрузки состояния (to/from dict)."""
        self.analyzer.load_users_from_generator(self.valid_json_path)

        # Сохраняем состояние в файл
        self.analyzer.save_state_to_file(self.output_state_path)
        self.assertTrue(os.path.exists(self.output_state_path))

        # Загружаем в новый пустой объект
        new_analyzer = AccessAnalyzer()
        new_analyzer.load_state_from_file(self.output_state_path)

        self.assertEqual(new_analyzer.all_available_resources, self.reference_resources)
        self.assertEqual(len(new_analyzer.users_data), 5)

    def test_export_analytical_report(self):
        """Позитивный тест: успешный экспорт отчета в JSON."""
        self.analyzer.load_users_from_generator(self.valid_json_path)
        self.analyzer.export_analytical_report(self.output_report_path)

        self.assertTrue(os.path.exists(self.output_report_path))
        with open(self.output_report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        self.assertIn("meta", report)
        self.assertIn("results", report)
        self.assertEqual(report["meta"]["total_users_analyzed"], 5)


    def test_read_non_existent_file(self):
        """Негативный тест: попытка чтения отсутствующего файла."""
        with self.assertRaises(FileNotFoundError):
            self.analyzer.load_users_from_generator("not_exist_file.json")

    def test_read_corrupted_json(self):
        """Негативный тест: попытка чтения поврежденного JSON файла."""
        with self.assertRaises(json.JSONDecodeError):
            self.analyzer.load_users_from_generator(self.invalid_json_path)

    def test_empty_database_analytics(self):
        """Граничное значение: аналитика на абсолютно пустых данных."""
        # Объект создан, но файлы не загружались (users_data пуст)
        self.assertEqual(self.analyzer.calculate_average_resources_per_user(), 0.0)
        self.assertEqual(self.analyzer.find_top_n_resources(5), [])
        self.assertEqual(self.analyzer.find_users_with_zero_access(), [])
        self.assertEqual(self.analyzer.find_duplicate_permissions(), {})


if __name__ == "__main__":
    unittest.main()