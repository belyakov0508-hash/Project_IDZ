"""Конфигурация pytest для корректного разрешения путей.

Добавляет корневую директорию проекта в sys.path,
чтобы импорт вида ``from src.analyzer import ...``
работал при запуске pytest из любого места.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))