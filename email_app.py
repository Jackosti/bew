import sys
import sqlite3
import hashlib
import json
import os
import shutil
import secrets
import base64
import atexit
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen
from io import BytesIO
from typing import Dict, Optional, Callable, List, Set
# Ленивая загрузка PIL для оптимизации времени запуска
_PIL_Image = None
_PIL_ImageEnhance = None
_PIL_ImageFilter = None

def _get_pil_modules():
    """Ленивая загрузка PIL модулей"""
    global _PIL_Image, _PIL_ImageEnhance, _PIL_ImageFilter
    if _PIL_Image is None:
        from PIL import Image as _PIL_Image_module, ImageEnhance as _PIL_ImageEnhance_module, ImageFilter as _PIL_ImageFilter_module
        _PIL_Image = _PIL_Image_module
        _PIL_ImageEnhance = _PIL_ImageEnhance_module
        _PIL_ImageFilter = _PIL_ImageFilter_module
    return _PIL_Image, _PIL_ImageEnhance, _PIL_ImageFilter
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import threading

from PyQt6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGraphicsBlurEffect,
    QGraphicsColorizeEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
    QGraphicsView,
    QRubberBand,
    QSlider,
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QDate, QPoint, QObject, QRegularExpression, QEvent
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QTextCharFormat, QRegularExpressionValidator, QPainter, QBrush, QPen, QMouseEvent, QClipboard, QCursor, QTransform, QIcon, QPainterPath

import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Google OAuth imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pickle
    GOOGLE_OAUTH_AVAILABLE = True
    
    # Google OAuth SCOPES
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.send"
    ]
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False
    SCOPES = []

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

import config

# Система локализации
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('localization.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
_localization_logger = logging.getLogger('LocalizationManager')


class LocalizationManager:
    """
    Менеджер локализации с JSON поддержкой
    - base_keys.json как единственный источник истины
    - Автоматическое обнаружение языков из папки locales/
    - Валидация синхронизации ключей
    - Fallback на de если ключ отсутствует
    - Загрузка языка пользователя из БД
    """

    DEFAULT_LANGUAGE = 'de'
    FALLBACK_LANGUAGE = 'de'  # Fallback всегда на немецкий

    def __init__(self):
        """Инициализация менеджера локализации"""
        self.locales_dir = Path(__file__).parent / "locales"
        self._current_language = self.DEFAULT_LANGUAGE
        self._translations: Dict[str, Dict[str, str]] = {}
        self._callbacks: List[Callable[[], None]] = []
        self._base_keys: Set[str] = set()
        self._available_languages: Dict[str, Dict] = {}

        # Загружаем метаданные языков
        self._load_meta()

        # Загружаем base_keys.json
        self._load_base_keys()

        # Автоматически обнаруживаем и загружаем языки
        self._auto_discover_languages()

        # Валидируем все языки
        self._validate_all_languages()

        _localization_logger.info(
            "LocalizationManager initialized. Current language: %s",
            self._current_language
        )
        _localization_logger.info(
            "Available languages: %s",
            list(self._available_languages.keys())
        )

    def _load_meta(self):
        """Загружает метаданные языков из meta.json"""
        meta_path = self.locales_dir / "meta.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    self._available_languages = meta.get('languages', {})
                    self.DEFAULT_LANGUAGE = meta.get('default_language', 'de')
                    self.FALLBACK_LANGUAGE = meta.get('fallback_language', 'de')
                    self._current_language = self.DEFAULT_LANGUAGE
                    _localization_logger.info(
                        "Loaded meta.json: %s languages",
                        len(self._available_languages)
                    )
            except Exception as e:
                _localization_logger.error("Error loading meta.json: %s", e)
                self._available_languages = {}

    def _load_base_keys(self):
        """Загружает base_keys.json - единственный источник истины для ключей"""
        base_keys_path = self.locales_dir / "base_keys.json"
        if not base_keys_path.exists():
            _localization_logger.error("base_keys.json not found at %s", base_keys_path)
            return

        try:
            with open(base_keys_path, 'r', encoding='utf-8') as f:
                base_keys = json.load(f)
                self._base_keys = set(base_keys.keys())
                _localization_logger.info(
                    "Loaded base_keys.json: %s keys",
                    len(self._base_keys)
                )
        except Exception as e:
            _localization_logger.error("Error loading base_keys.json: %s", e)

    def _auto_discover_languages(self):
        """Автоматически обнаруживает доступные языки из папки locales/"""
        if not self.locales_dir.exists():
            _localization_logger.error("Locales directory not found: %s", self.locales_dir)
            return

        json_files = list(self.locales_dir.glob("*.json"))
        json_files = [f for f in json_files if f.name not in ['base_keys.json', 'meta.json']]

        for json_file in json_files:
            lang_code = json_file.stem
            if lang_code in ['base_keys', 'meta']:
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    self._translations[lang_code] = translations
                    _localization_logger.info(
                        "Auto-discovered language: %s (%s keys)",
                        lang_code,
                        len(translations)
                    )
            except Exception as e:
                _localization_logger.error("Error loading %s: %s", json_file, e)

    def _validate_all_languages(self):
        """Валидирует, что все языки содержат те же ключи, что и base_keys.json"""
        if not self._base_keys:
            _localization_logger.warning("No base keys loaded, skipping validation")
            return

        for lang_code, translations in self._translations.items():
            lang_keys = set(translations.keys())
            missing = self._base_keys - lang_keys
            extra = lang_keys - self._base_keys

            if missing:
                _localization_logger.warning(
                    "Language %s is missing %s keys: %s",
                    lang_code,
                    len(missing),
                    list(missing)[:10]
                )
            if extra:
                _localization_logger.warning(
                    "Language %s has %s extra keys: %s",
                    lang_code,
                    len(extra),
                    list(extra)[:10]
                )

            if not missing and not extra:
                _localization_logger.info(
                    "Language %s is fully synchronized with base_keys.json",
                    lang_code
                )

    def get_current_language(self) -> str:
        """Возвращает текущий язык"""
        return self._current_language

    def set_language(self, language_code: str, save_to_db: bool = True):
        """Устанавливает язык приложения"""
        if language_code not in self._translations:
            _localization_logger.warning(
                "Language %s not found, using default: %s",
                language_code,
                self.DEFAULT_LANGUAGE
            )
            language_code = self.DEFAULT_LANGUAGE

        if self._current_language != language_code:
            old_lang = self._current_language
            self._current_language = language_code
            _localization_logger.info("Language changed from %s to %s", old_lang, language_code)

            if save_to_db:
                self._save_language_to_db(language_code)

            self._notify_callbacks()

    def _save_language_to_db(self, language_code: str):
        """Сохраняет язык в базу данных"""
        try:
            username = get_current_username()
            if not username:
                return

            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            try:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN language TEXT DEFAULT "de"')
                conn.commit()
            except sqlite3.OperationalError:
                pass

            cursor.execute(
                'UPDATE auth_users SET language = ? WHERE username = ?',
                (language_code, username)
            )
            conn.commit()
            conn.close()

            _localization_logger.info(
                "Language %s saved to database for user %s",
                language_code,
                username
            )

        except Exception as e:
            _localization_logger.error("Error saving language to database: %s", e)

    def load_language_from_db(self, username: Optional[str] = None) -> Optional[str]:
        """Загружает язык пользователя из базы данных"""
        try:
            if username is None:
                username = get_current_username()

            if not username:
                return None

            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            try:
                cursor.execute('SELECT language FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                conn.close()

                if result and result[0]:
                    lang = result[0]
                    if lang in self._translations:
                        _localization_logger.info(
                            "Loaded language %s from database for user %s",
                            lang,
                            username
                        )
                        return lang
            except sqlite3.OperationalError:
                pass

            conn.close()

        except Exception as e:
            _localization_logger.error("Error loading language from database: %s", e)

        return None

    def t(self, key: str, **kwargs) -> str:
        """Получает перевод для ключа (главная функция)"""
        translation = self._get_translation(key, self._current_language)

        if translation is None or translation == "":
            translation = self._get_translation(key, self.FALLBACK_LANGUAGE)
            if translation is None or translation == "":
                _localization_logger.warning(
                    "Translation key '%s' not found in %s or %s",
                    key,
                    self._current_language,
                    self.FALLBACK_LANGUAGE
                )
                return key

        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except KeyError as e:
                _localization_logger.warning("Missing format parameter %s in key '%s'", e, key)
            except Exception as e:
                _localization_logger.warning("Error formatting key '%s': %s", key, e)

        return translation

    def _get_translation(self, key: str, language_code: str) -> Optional[str]:
        """Получает перевод для ключа и языка"""
        translations = self._translations.get(language_code, {})
        return translations.get(key)

    def register_callback(self, callback: Callable[[], None]):
        """Регистрирует callback для обновления UI при смене языка"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]):
        """Удаляет callback из списка"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self):
        """Уведомляет все зарегистрированные callbacks о смене языка"""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                _localization_logger.error("Error in language change callback: %s", e)

    def get_available_languages(self) -> Dict[str, Dict]:
        """Возвращает словарь доступных языков с метаданными"""
        result = {}
        for lang_code, meta in self._available_languages.items():
            if lang_code in self._translations:
                result[lang_code] = meta
        return result

    def get_language_display_name(self, lang_code: str) -> str:
        """Возвращает отображаемое имя языка с флагом"""
        if lang_code in self._available_languages:
            meta = self._available_languages[lang_code]
            flag = meta.get('flag', '')
            native_name = meta.get('native_name', lang_code)
            return f"{flag} {native_name}"
        return lang_code

    def validate_language_file(self, lang_code: str) -> Dict[str, any]:
        """Валидирует файл языка на соответствие base_keys.json"""
        if lang_code not in self._translations:
            return {"valid": False, "error": f"Language {lang_code} not found"}

        lang_keys = set(self._translations[lang_code].keys())
        missing = self._base_keys - lang_keys
        extra = lang_keys - self._base_keys

        return {
            "valid": len(missing) == 0 and len(extra) == 0,
            "missing_keys": list(missing),
            "extra_keys": list(extra),
            "total_keys": len(lang_keys),
            "base_keys_count": len(self._base_keys)
        }


_localization_manager: Optional[LocalizationManager] = None


def get_localization_manager() -> LocalizationManager:
    """Возвращает глобальный экземпляр менеджера локализации"""
    global _localization_manager
    if _localization_manager is None:
        _localization_manager = LocalizationManager()
    return _localization_manager


def t(key: str, **kwargs) -> str:
    """Глобальная функция для получения перевода (главная функция)"""
    return get_localization_manager().t(key, **kwargs)


def get_current_language() -> str:
    """Возвращает текущий язык"""
    return get_localization_manager().get_current_language()


def set_language(language_code: str, save_to_db: bool = True):
    """Устанавливает язык приложения"""
    get_localization_manager().set_language(language_code, save_to_db)


def register_language_callback(callback: Callable[[], None]):
    """Регистрирует callback для обновления UI при смене языка"""
    get_localization_manager().register_callback(callback)


def tr(key: str, **kwargs) -> str:
    """Алиас для t() для обратной совместимости"""
    return t(key, **kwargs)


# Для обратной совместимости - будет обновляться при инициализации
CURRENT_LANGUAGE = 'de'


def init_localization():
    """Инициализирует систему локализации"""
    global CURRENT_LANGUAGE

    manager = get_localization_manager()
    CURRENT_LANGUAGE = manager.get_current_language()
    return manager


try:
    _ = init_localization()
except Exception as e:
    print(f"Ошибка инициализации локализации: {e}")
    pass


def save_language_to_db(language):
    """Сохраняет язык в базу данных"""
    set_language(language, save_to_db=True)

# Класс для кликабельного QLabel
class ClickableLabel(QLabel):
    """QLabel с поддержкой клика и визуальной обратной связи"""
    clicked = pyqtSignal()
    
    def __init__(self, text=""):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        # Проверяем, не является ли это "О приложении" - для него не меняем цвет текста
        text = self.text()
        is_about = text == tr("about_title")
        if text != tr("no_sent") and not is_about:
            self.setStyleSheet("""
                color: #9C89B8;
                background: rgba(200, 182, 226, 0.2);
                padding: 4px;
                border-radius: 8px;
            """)
        elif is_about:
            # Для "О приложении" меняем только фон виджета, сохраняя оригинальный цвет текста
            # Получаем оригинальный цвет из property или используем дефолтный
            original_color = self.property("originalColor") or "#a78bfa"
            self.setStyleSheet(f"""
                color: {original_color};
                background: rgba(200, 182, 226, 0.2);
                padding: 4px;
                border-radius: 8px;
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if self.text() != tr("no_sent"):
            self.setStyleSheet("""
                color: #6C4A8B;
                background: transparent;
                padding: 4px;
                border-radius: 8px;
            """)
        super().leaveEvent(event)

# Основная цветовая палитра приложения (без переключения тем)
APP_COLORS = {
    "main_window_bg_start": "#F5F0FF",
    "main_window_bg_mid": "#F5F0FF",
    "main_window_bg_end": "#F5F0FF",
    "sidebar_bg": "#E8D5FF",
    "content_bg": "#F5F0FF",
    "input_bg": "#F5F0FF",
    "card_bg": "#FFFFFF",
    "text_primary": "#3D2B5D",
    "text_secondary": "#5E548A",
    "text_tertiary": "#7D6B8F",
    "input_text": "#3D2B5D",
    "button_primary_text": "#FFFFFF",
    "button_secondary_text": "#5E548A",
    "error_text": "#DC3545",
    "card_border": "#D8C5F0",
    "input_border": "#C0A8E8",
    "input_border_focus": "#A78BFA",
    "border_color": "#D8C5F0",
    "border_light": "#E0CDF7",
    "separator_color": "#D8C5F0",
    "button_primary_bg": "#A78BFA",
    "button_primary_hover": "#B99DFF",
    "button_secondary_bg": "#E0CDF7",
    "button_secondary_hover": "#D8C5F0",
    "accent": "#A78BFA",
    "accent_alt": "#B99DFF",
    "accent_color": "#A78BFA",
    "accent_hover": "#B99DFF",
    "error_bg": "rgba(220, 53, 69, 0.1)",
    "success_color": "#28A745",
    "warning_color": "#FFC107",
    "info_color": "#17A2B8",
    "accent_teal": "#3DB8A8",
}


def get_app_colors() -> Dict[str, str]:
    """Возвращает копию базовой цветовой палитры."""
    return dict(APP_COLORS)

# Инициализация базы данных
DB_FILE = "email_app.db"
LOG_FILE = "email_history.txt"

# Кеш для оптимизации производительности
_history_cache = None
_history_cache_time = None
_stats_cache = None
_stats_cache_time = None
_profile_cache = {}  # Кеш профилей: {username: {data, timestamp}}
_autofill_cache = {}  # Кеш автозаполнения: {username: {data, timestamp}}
CACHE_TIMEOUT = 5  # секунд
PROFILE_CACHE_TIMEOUT = 300  # 5 минут для профилей

# Оптимизация: Кеш для часто используемых данных
_username_cache = None
_username_cache_time = None
_machine_id_cache = None
_table_schema_cache = {}  # Кеш схем таблиц
USERNAME_CACHE_TIMEOUT = 60  # 1 минута для username

# Оптимизация: Контекстный менеджер для подключений к БД
class DatabaseConnection:
    """Контекстный менеджер для подключений к базе данных с оптимизациями"""
    _connection = None
    _connection_lock = threading.Lock()
    
    @classmethod
    def get_connection(cls):
        """Получает соединение с БД (с переиспользованием)"""
        with cls._connection_lock:
            if cls._connection is None:
                cls._connection = sqlite3.connect(
                    DB_FILE,
                    check_same_thread=False,
                    timeout=10.0
                )
                # Оптимизации SQLite
                cls._connection.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging для лучшей производительности
                cls._connection.execute("PRAGMA synchronous=NORMAL")  # Баланс между производительностью и надежностью
                cls._connection.execute("PRAGMA cache_size=-64000")  # Кеш 64MB
                cls._connection.execute("PRAGMA foreign_keys=ON")
                cls._connection.row_factory = sqlite3.Row  # Для доступа по имени колонок
            return cls._connection
    
    @classmethod
    def close_connection(cls):
        """Закрывает соединение"""
        with cls._connection_lock:
            if cls._connection is not None:
                cls._connection.close()
                cls._connection = None
    
    def __enter__(self):
        self.conn = self.get_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Не закрываем соединение, оставляем его открытым для переиспользования
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()
        return False
    
    @classmethod
    def execute_query(cls, query, params=(), fetch_one=False, fetch_all=False, commit=False):
        """Удобный метод для выполнения запросов"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            return cursor
        except Exception as e:
            conn.rollback()
            raise e

def init_database():
    """Инициализирует базу данных с поддержкой множественных профилей"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Таблица авторизации пользователей (основная таблица профилей)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone_number TEXT,
            avatar_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем индексы для быстрого поиска
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON auth_users(username)')
    except:
        pass
    
    # Миграция: добавляем колонки если их нет (для обновления со старой версии)
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN last_login TIMESTAMP')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN language TEXT DEFAULT "de"')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN is_online INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN google_email TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN google_token TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN frame_path TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN last_seen TIMESTAMP')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN current_status TEXT DEFAULT ""')
    except:
        pass
    
    conn.commit()
    
    # Таблица друзей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_username TEXT NOT NULL,
            user2_username TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_username) REFERENCES auth_users(username) ON DELETE CASCADE,
            FOREIGN KEY (user2_username) REFERENCES auth_users(username) ON DELETE CASCADE,
            UNIQUE(user1_username, user2_username)
        )
    ''')
    
    # Индексы для быстрого поиска друзей
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_friendships_user1 ON friendships(user1_username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_friendships_user2 ON friendships(user2_username)')
    except:
        pass
    
    conn.commit()
    
    # Таблица истории отправки (привязана к username - изолирована для каждого профиля)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            lehrstelle TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES auth_users(username) ON DELETE CASCADE
        )
    ''')
    
    # Добавляем колонку username если её нет (миграция)
    try:
        cursor.execute('ALTER TABLE email_history ADD COLUMN username TEXT')
    except:
        pass
    
    # Добавляем индекс для быстрого поиска по username
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_history_username ON email_history(username)')
    except:
        pass
    
    # Таблица автозаполнения (привязана к username - изолирована для каждого профиля)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS autofill_data (
            username TEXT PRIMARY KEY,
            email TEXT,
            lehrstelle TEXT,
            firma TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES auth_users(username) ON DELETE CASCADE
        )
    ''')
    
    # Миграция: добавляем колонку username если её нет (для обновления со старой версии)
    try:
        cursor.execute('ALTER TABLE autofill_data ADD COLUMN username TEXT')
    except:
        pass
    
    # Добавляем индекс
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_autofill_username ON autofill_data(username)')
    except:
        pass
    
    # Таблица для сохранения списка прикрепленных файлов (привязана к username)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_attachments (
            username TEXT PRIMARY KEY,
            attachments_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES auth_users(username) ON DELETE CASCADE
        )
    ''')
    
    # Таблица для черновиков писем (облачное хранение для каждого аккаунта)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            recipient_email TEXT,
            lehrstelle TEXT,
            firma TEXT,
            body_text TEXT,
            attached_files_json TEXT,
            use_ai INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES auth_users(username) ON DELETE CASCADE
        )
    ''')
    
    # Миграция: добавляем колонку attached_files_json если её нет
    try:
        cursor.execute('ALTER TABLE email_drafts ADD COLUMN attached_files_json TEXT')
        conn.commit()
    except:
        pass  # Колонка уже существует
    
    # Миграция: добавляем колонку use_ai если её нет
    try:
        cursor.execute('ALTER TABLE email_drafts ADD COLUMN use_ai INTEGER DEFAULT 0')
        conn.commit()
    except:
        pass  # Колонка уже существует
    
    # Миграция: преобразуем таблицу для поддержки множественных черновиков
    try:
        cursor.execute("PRAGMA table_info(email_drafts)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Проверяем, есть ли колонка id
        if 'id' not in column_names:
            # Создаем новую таблицу с id
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_drafts_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    recipient_email TEXT,
                    lehrstelle TEXT,
                    firma TEXT,
                    body_text TEXT,
                    attached_files_json TEXT,
                    use_ai INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES auth_users(username) ON DELETE CASCADE
                )
            ''')
            
            # Копируем данные из старой таблицы
            cursor.execute('SELECT * FROM email_drafts')
            old_rows = cursor.fetchall()
            
            # Получаем индексы колонок
            old_column_names = [col[1] for col in columns_info]
            username_idx = old_column_names.index('username') if 'username' in old_column_names else None
            email_idx = old_column_names.index('recipient_email') if 'recipient_email' in old_column_names else None
            lehr_idx = old_column_names.index('lehrstelle') if 'lehrstelle' in old_column_names else None
            firma_idx = old_column_names.index('firma') if 'firma' in old_column_names else None
            body_idx = old_column_names.index('body_text') if 'body_text' in old_column_names else None
            files_idx = old_column_names.index('attached_files_json') if 'attached_files_json' in old_column_names else None
            ai_idx = old_column_names.index('use_ai') if 'use_ai' in old_column_names else None
            
            for row in old_rows:
                cursor.execute('''
                    INSERT INTO email_drafts_new (username, recipient_email, lehrstelle, firma, body_text, attached_files_json, use_ai)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row[username_idx] if username_idx is not None else '',
                    row[email_idx] if email_idx is not None else '',
                    row[lehr_idx] if lehr_idx is not None else '',
                    row[firma_idx] if firma_idx is not None else '',
                    row[body_idx] if body_idx is not None else '',
                    row[files_idx] if files_idx is not None else '[]',
                    row[ai_idx] if ai_idx is not None else 0
                ))
            
            # Удаляем старую таблицу и переименовываем новую
            cursor.execute('DROP TABLE email_drafts')
            cursor.execute('ALTER TABLE email_drafts_new RENAME TO email_drafts')
            conn.commit()
    except Exception as e:
        pass  # Ошибка миграции, продолжаем работу
    
    conn.commit()
    conn.close()

def get_user_info(username=None):
    """Получает информацию о пользователе с кешированием (привязано к username) - ОПТИМИЗИРОВАНО"""
    global _profile_cache, _table_schema_cache
    
    if not username:
        username = get_current_username()
        if not username:
            return None
    
    # Проверяем кеш
    now = datetime.now()
    if username in _profile_cache:
        cached_data, cache_time = _profile_cache[username]
        if (now - cache_time).total_seconds() < PROFILE_CACHE_TIMEOUT:
            return cached_data
    
    # Загружаем из БД с оптимизированным подключением
    try:
        # Кешируем информацию о схеме таблицы
        table_name = 'auth_users'
        if table_name not in _table_schema_cache:
            with DatabaseConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(auth_users)")
                columns = [row[1] for row in cursor.fetchall()]
                _table_schema_cache[table_name] = columns
        else:
            columns = _table_schema_cache[table_name]
        
        has_current_status = 'current_status' in columns
        
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            if has_current_status:
                cursor.execute('SELECT first_name, last_name, phone_number, avatar_path, created_at, current_status FROM auth_users WHERE username = ?', (username,))
            else:
                cursor.execute('SELECT first_name, last_name, phone_number, avatar_path, created_at FROM auth_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if result:
                # Поддерживаем оба формата: tuple и Row
                if isinstance(result, sqlite3.Row):
                    if has_current_status:
                        user_info = (
                            result['first_name'],
                            result['last_name'],
                            result['phone_number'] if result['phone_number'] else '',
                            result['created_at'] if result['created_at'] else None,
                            result['avatar_path'] if result['avatar_path'] else None,
                            username,
                            result['current_status'] if result['current_status'] else ''
                        )
                    else:
                        user_info = (
                            result['first_name'],
                            result['last_name'],
                            result['phone_number'] if result['phone_number'] else '',
                            result['created_at'] if result['created_at'] else None,
                            result['avatar_path'] if result['avatar_path'] else None,
                            username,
                            ''
                        )
                else:
                    # Оригинальный формат (tuple)
                    if has_current_status:
                        user_info = (
                            result[0],  # first_name
                            result[1],  # last_name
                            result[2] if result[2] else '',  # phone_number
                            result[4] if result[4] else None,  # created_at
                            result[3] if result[3] else None,  # avatar_path
                            username,  # username
                            result[5] if result[5] else ''  # current_status
                        )
                    else:
                        user_info = (
                            result[0],  # first_name
                            result[1],  # last_name
                            result[2] if result[2] else '',  # phone_number
                            result[4] if result[4] else None,  # created_at
                            result[3] if result[3] else None,  # avatar_path
                            username,  # username
                            ''  # current_status (по умолчанию пусто)
                        )
                # Сохраняем в кеш
                _profile_cache[username] = (user_info, now)
                return user_info
    except Exception as e:
        print(f"Ошибка получения информации о пользователе: {e}")
    
    return None

def get_current_username():
    """Получает текущий username пользователя из remembered_users для текущего компьютера (с кешированием)"""
    global _username_cache, _username_cache_time
    
    # Проверяем кеш
    if _username_cache is not None and _username_cache_time is not None:
        elapsed = (datetime.now() - _username_cache_time).total_seconds()
        if elapsed < USERNAME_CACHE_TIMEOUT:
            return _username_cache
    
    # Загружаем из БД
    machine_id = get_machine_id()
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM remembered_users WHERE machine_id = ?', (machine_id,))
            result = cursor.fetchone()
            if result:
                username = result[0] if isinstance(result, tuple) else result['username']
                # Обновляем кеш
                _username_cache = username
                _username_cache_time = datetime.now()
                return username
    except Exception as e:
        print(f"Ошибка получения username: {e}")
    
    _username_cache = None
    _username_cache_time = None
    return None

def get_machine_id():
    """Получает уникальный ID машины (ПК) с кешированием"""
    global _machine_id_cache
    
    # Кеш сохраняется на время работы приложения
    if _machine_id_cache is not None:
        return _machine_id_cache
    
    import uuid
    import platform
    
    # Пытаемся получить MAC адрес сетевой карты
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                        for elements in range(0,2*6,2)][::-1])
        hostname = platform.node()
        # Комбинируем для уникальности
        machine_id = f"{hostname}_{mac}"
    except:
        # Fallback на hostname
        try:
            machine_id = platform.node()
        except:
            machine_id = "unknown_pc"
    
    _machine_id_cache = machine_id
    return machine_id

def set_user_online(username, is_online=True):
    """Устанавливает статус онлайн/офлайн для пользователя - ОПТИМИЗИРОВАНО"""
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Проверяем и добавляем колонки если нужно (только один раз)
            table_name = 'auth_users'
            if table_name in _table_schema_cache:
                columns = _table_schema_cache[table_name]
            else:
                cursor.execute("PRAGMA table_info(auth_users)")
                columns = [row[1] for row in cursor.fetchall()]
                _table_schema_cache[table_name] = columns
            
            if 'is_online' not in columns:
                try:
                    cursor.execute('ALTER TABLE auth_users ADD COLUMN is_online INTEGER DEFAULT 0')
                    cursor.execute('ALTER TABLE auth_users ADD COLUMN last_seen TIMESTAMP')
                    conn.commit()
                    # Обновляем кеш схемы
                    _table_schema_cache[table_name].extend(['is_online', 'last_seen'])
                except:
                    pass
            
            cursor.execute('''
                UPDATE auth_users 
                SET is_online = ?, last_seen = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (1 if is_online else 0, username))
            conn.commit()
    except Exception as e:
        print(f"Ошибка установки статуса онлайн: {e}")

def save_google_account(username, google_email, google_token):
    """Сохраняет Google аккаунт для пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем наличие колонок
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN google_email TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN google_token TEXT')
    except:
        pass
    
    # Проверяем, существует ли пользователь
    cursor.execute('SELECT username FROM auth_users WHERE username = ?', (username,))
    user_exists = cursor.fetchone()
    if not user_exists:
        conn.close()
        return False
    
    # Удаляем старый аккаунт kornieienko.illia@gmail.com если есть
    cursor.execute('''
        UPDATE auth_users 
        SET google_email = NULL, google_token = NULL 
        WHERE google_email LIKE '%kornieienko.illia%' 
           OR google_email = 'kornieienko.illia@gmail.com'
    ''')
    
    # Сохраняем новый аккаунт
    cursor.execute('''
        UPDATE auth_users 
        SET google_email = ?, google_token = ?
        WHERE username = ?
    ''', (google_email, google_token, username))
    
    # Проверяем, что обновление прошло успешно
    rows_affected = cursor.rowcount
    
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_google_account_email(username):
    """Получает Google email пользователя"""
    if not username:
        return None
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT google_email FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if result and result[0]:
            return result[0]
        else:
            # Проверяем через token
            cursor.execute('SELECT google_token FROM auth_users WHERE username = ?', (username,))
            token_result = cursor.fetchone()
            if token_result and token_result[0]:
                try:
                    token_data = json.loads(token_result[0])
                    email = token_data.get('email', '')
                    if email:
                        # Если email найден в token, но не в колонке, обновляем колонку
                        cursor.execute('UPDATE auth_users SET google_email = ? WHERE username = ?', (email, username))
                        conn.commit()
                        return email
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        conn.close()
    
    return None

def get_google_account_token(username):
    """Получает Google token пользователя"""
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT google_token FROM auth_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            if result and result[0]:
                if isinstance(result, sqlite3.Row):
                    return result['google_token']
                return result[0]
    except:
        pass
    
    return None

def get_google_credentials(username):
    """Получает и обновляет Google credentials для пользователя"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return None
    
    token_json = get_google_account_token(username)
    if not token_json:
        return None
    
    try:
        creds_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Обновляем токен если истек
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Сохраняем обновленный токен
            creds_dict = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'email': creds_data.get('email', '')
            }
            save_google_account(username, creds_dict.get('email', ''), json.dumps(creds_dict))
        
        return creds
    except Exception as e:
        print(f"Ошибка получения credentials: {e}")
        return None

# Глобальная переменная для хранения кода авторизации
_oauth_code = None
_oauth_error = None

class ThreadingHTTPServer(threading.Thread):
    """HTTP сервер в отдельном потоке"""
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.daemon = True
    
    def run(self):
        self.server.serve_forever()
    
    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()

class OAuthHandler(BaseHTTPRequestHandler):
    """Обработчик для получения OAuth кода через localhost"""
    def do_GET(self):
        global _oauth_code, _oauth_error
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            _oauth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            # Отправляем успешный ответ браузеру
            success_html = '''
            <html>
            <head>
                <title>Success</title>
                <meta http-equiv="refresh" content="3;url=about:blank">
            </head>
            <body style="font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <h1 style="color: #34d399; font-size: 32px;">Authorization successful!</h1>
                <p style="font-size: 18px; margin-top: 20px;">You can close this window and return to the application.</p>
                <p style="font-size: 14px; margin-top: 10px; opacity: 0.8;">This window will close automatically...</p>
            </body>
            </html>
            '''
            self.wfile.write(success_html.encode('utf-8'))
            # Небольшая задержка перед закрытием соединения
            import time
            time.sleep(0.5)
        elif 'error' in query_params:
            _oauth_error = query_params['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f'''
            <html>
            <head><title>Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #ef4444;">Authorization Error</h1>
                <p>{_oauth_error}</p>
            </body>
            </html>
            '''.encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            waiting_html = '''
            <html>
            <head><title>Waiting</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>Waiting for authorization...</h1>
            </body>
            </html>
            '''
            self.wfile.write(waiting_html.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Отключаем логирование

def authenticate_google_oauth():
    """Выполняет OAuth авторизацию Google используя run_local_server"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return None, None, "Google OAuth библиотеки не установлены"
    
    try:
        # Проверяем оба варианта названия файла
        creds_file = None
        if os.path.exists('credentials.json'):
            creds_file = 'credentials.json'
        elif os.path.exists('credential.json'):
            creds_file = 'credential.json'
        
        if not creds_file:
            return None, None, "Файл credentials.json или credential.json не найден. Пожалуйста, создайте OAuth 2.0 credentials в Google Cloud Console."
        
        # Проверяем структуру файла
        try:
            with open(creds_file, 'r', encoding='utf-8') as f:
                creds_data = json.load(f)
                # Проверяем, что файл содержит правильную структуру
                if 'installed' not in creds_data and 'web' not in creds_data:
                    return None, None, "Неверная структура credentials.json. Файл должен содержать ключ 'installed' или 'web'."
        except json.JSONDecodeError:
            return None, None, "Ошибка чтения credentials.json. Файл должен быть в формате JSON."
        except Exception as e:
            return None, None, f"Ошибка проверки credentials.json: {str(e)}"
        
        # Используем InstalledAppFlow - он автоматически выберет redirect_uri из JSON
        flow = InstalledAppFlow.from_client_secrets_file(
            creds_file,
            SCOPES
        )
        
        # run_local_server автоматически выберет порт и redirect_uri из JSON
        # port=0 означает автоматический выбор свободного порта
        creds = flow.run_local_server(port=0)
        
        return creds, None, None
    except Exception as e:
        error_str = str(e)
        # Проверяем специфические ошибки
        if "403" in error_str or "access_denied" in error_str.lower():
            return None, None, (
                "Ошибка 403: Приложение в режиме тестирования\n\n"
                "Если вы уже добавили email в тестовые пользователи:\n\n"
                "1. Проверьте, что email добавлен правильно:\n"
                "   - Должен быть точно тот же email, который вы используете\n"
                "   - Без пробелов до/после\n"
                "   - Убедитесь, что нажали 'Save'\n\n"
                "2. Подождите 1-2 минуты после сохранения\n\n"
                "3. Попробуйте использовать режим 'Production':\n"
                "   - Перейдите: https://console.cloud.google.com/apis/credentials/consent\n"
                "   - В разделе 'Publishing status' выберите 'Production'\n"
                "   - Для личного использования это допустимо без верификации\n\n"
                "4. Очистите кеш браузера или используйте режим инкогнито\n\n"
                "5. Попробуйте подключить снова через приложение"
            )
        if "deleted_client" in error_str or "invalid_client" in error_str or "401" in error_str:
            # Получаем Client ID из файла для отображения в ошибке
            try:
                with open(creds_file, 'r', encoding='utf-8') as f:
                    creds_data = json.load(f)
                    client_data = creds_data.get('installed') or creds_data.get('web', {})
                    client_id = client_data.get('client_id', 'не найден')
            except:
                client_id = 'не найден'
            
            error_type = "удален (deleted_client)" if "deleted_client" in error_str else "не найден (invalid_client)"
            
            return None, None, (
                f"Ошибка: OAuth клиент {error_type}\n\n"
                f"Client ID в файле: {client_id}\n\n"
                f"Правильный Client ID должен быть:\n"
                f"181774815394-rvbhpsn1q34i4tlc2clp6in73u64vclp.apps.googleusercontent.com\n\n"
                f"Решение:\n"
                f"1. Удалите старый OAuth клиент в Google Cloud Console\n"
                f"2. Создайте новый OAuth 2.0 Client ID (Desktop app)\n"
                f"3. ВАЖНО: Сразу после создания нажмите 'DOWNLOAD JSON'\n"
                f"4. Переименуйте скачанный файл в credential.json\n"
                f"5. Замените старый файл новым\n\n"
                f"Нельзя просто изменить Client ID - нужен полный файл\n"
                f"с правильным client_secret!"
            )
        # Проверяем ошибку 400 invalid_request
        if "400" in error_str or "invalid_request" in error_str.lower():
            return None, None, (
                "Ошибка 400: Неверный запрос (invalid_request)\n\n"
                "Проблема: redirect_uri не настроен правильно\n\n"
                "Решение:\n"
                "1. Перейдите в Google Cloud Console:\n"
                "   https://console.cloud.google.com/apis/credentials\n\n"
                "2. Откройте ваш OAuth клиент (Desktop client)\n\n"
                "3. Найдите раздел 'Authorized redirect URIs'\n\n"
                "4. Убедитесь, что добавлен:\n"
                "   urn:ietf:wg:oauth:2.0:oob\n\n"
                "5. Если его нет - добавьте и сохраните\n\n"
                "6. Удалите http://localhost из списка (если есть)\n\n"
                "7. Попробуйте подключить снова"
            )
        return None, None, f"Ошибка OAuth: {error_str}"

def process_google_credentials(creds):
    """Обрабатывает полученные credentials и возвращает данные для сохранения"""
    if not creds:
        return None, None, "Credentials не получены"
    
    try:
        # Получаем email пользователя через OAuth2 userinfo
        email = ''
        try:
            userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {creds.token}'}
            response = requests.get(userinfo_url, headers=headers)
            
            if response.status_code == 200:
                userinfo = response.json()
                email = userinfo.get('email', '')
        except Exception:
            email = ''
        
        # Сохраняем credentials
        creds_dict = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'email': email
        }
        
        # Сохраняем token.json файл для удобства
        try:
            token_file = 'token.json'
            with open(token_file, 'w', encoding='utf-8') as f:
                json.dump(creds_dict, f, indent=2)
        except Exception:
            pass
        
        return creds_dict, email, None
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_str = str(e)
        
        # Проверяем специфические ошибки
        if "403" in error_str or "access_denied" in error_str.lower() or "testing" in error_str.lower():
            return None, None, (
                "Ошибка 403: Приложение в режиме тестирования\n\n"
                "Если вы уже добавили email в тестовые пользователи:\n\n"
                "1. Проверьте, что email добавлен правильно:\n"
                "   - Должен быть точно тот же email, который вы используете\n"
                "   - Без пробелов до/после\n"
                "   - Убедитесь, что нажали 'Save'\n\n"
                "2. Подождите 1-2 минуты после сохранения\n\n"
                "3. Попробуйте использовать режим 'Production':\n"
                "   - Перейдите: https://console.cloud.google.com/apis/credentials/consent\n"
                "   - В разделе 'Publishing status' выберите 'Production'\n"
                "   - Для личного использования это допустимо без верификации\n\n"
                "4. Очистите кеш браузера или используйте режим инкогнито\n\n"
                "5. Попробуйте подключить снова через приложение"
            )
        if "deleted_client" in error_str.lower() or "401" in error_str:
            return None, None, "deleted_client: OAuth клиент удален или неверен. Проверьте Client ID в credentials.json"
        return None, None, f"Ошибка завершения OAuth: {error_str}"

def get_user_online_status(username):
    """Получает статус онлайн пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT is_online, last_seen FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return bool(result[0]) if result[0] is not None else False, result[1]
    except:
        pass
    conn.close()
    return False, None

def send_friend_request(user1_username, user2_username):
    """Отправляет запрос на дружбу
    
    Returns:
        tuple: (success: bool, error_code: str)
        success - True если запрос отправлен успешно
        error_code - код ошибки или "request_sent" при успехе
    """
    # Убеждаемся, что база данных инициализирована
    try:
        init_database()
    except Exception:
        pass
    
    if not user1_username or not user2_username:
        return False, "user_not_found"
    
    # Нормализуем usernames (убираем пробелы)
    user1_username = user1_username.strip()
    user2_username = user2_username.strip()
    
    if not user1_username or not user2_username:
        return False, "user_not_found"
    
    # Проверка на добавление самого себя (регистронезависимо)
    if user1_username.lower() == user2_username.lower():
        return False, "cannot_add_self"
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Получаем точный username для user1 (отправителя)
        cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (user1_username,))
        user1_result = cursor.fetchone()
        if not user1_result:
            conn.close()
            return False, "user_not_found"
        exact_user1_username = user1_result[0]
        
        # Проверяем, что пользователь существует (регистронезависимо через COLLATE NOCASE)
        cursor.execute('SELECT id, username FROM auth_users WHERE username = ? COLLATE NOCASE', (user2_username,))
        user_result = cursor.fetchone()
        if not user_result:
            conn.close()
            return False, "user_not_found"
        
        # Получаем точный username из базы (на случай различий в регистре)
        exact_username = user_result[1]
        
        # Проверяем, не существует ли уже запрос или дружба
        cursor.execute('''
            SELECT id, status FROM friendships 
            WHERE (user1_username = ? AND user2_username = ?) 
               OR (user1_username = ? AND user2_username = ?)
        ''', (exact_user1_username, exact_username, exact_username, exact_user1_username))
        existing = cursor.fetchone()
        if existing:
            status = existing[1] if len(existing) > 1 else None
            conn.close()
            if status == 'accepted':
                return False, "already_friends"
            elif status == 'pending':
                return False, "request_already_sent"
        
        # Отправляем запрос с точными username из базы
        cursor.execute('''
            INSERT INTO friendships (user1_username, user2_username, status)
            VALUES (?, ?, 'pending')
        ''', (exact_user1_username, exact_username))
        conn.commit()
        conn.close()
        return True, "request_sent"
        
    except sqlite3.IntegrityError:
        # Проверяем, не дубликат ли это
        try:
            # Получаем точные username снова
            cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (user1_username,))
            user1_result = cursor.fetchone()
            if not user1_result:
                conn.close()
                return False, "user_not_found"
            exact_user1_username = user1_result[0]
            
            cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (user2_username,))
            user2_result = cursor.fetchone()
            if not user2_result:
                conn.close()
                return False, "user_not_found"
            exact_username = user2_result[0]
            
            cursor.execute('''
                SELECT status FROM friendships 
                WHERE (user1_username = ? AND user2_username = ?) 
                   OR (user1_username = ? AND user2_username = ?)
            ''', (exact_user1_username, exact_username, exact_username, exact_user1_username))
            existing = cursor.fetchone()
            if existing:
                status = existing[0] if existing else None
                conn.close()
                if status == 'accepted':
                    return False, "already_friends"
                elif status == 'pending':
                    return False, "request_already_sent"
        except Exception:
            pass
        conn.close()
        return False, "request_already_sent"
    except Exception:
        if conn:
            try:
                conn.close()
            except:
                pass
        # Возвращаем более информативный код ошибки
        error_msg = str(e)
        if "no such table" in error_msg.lower():
            return False, "database_error"
        elif "foreign key" in error_msg.lower():
            return False, "user_not_found"
        else:
            return False, "error_occurred"

def accept_friend_request(user1_username, user2_username):
    """Принимает запрос на дружбу"""
    if not user1_username or not user2_username:
        return False, tr("request_not_found")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Получаем точные username из базы
        cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (user1_username,))
        user1_result = cursor.fetchone()
        if not user1_result:
            conn.close()
            return False, tr("request_not_found")
        exact_user1 = user1_result[0]
        
        cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (user2_username,))
        user2_result = cursor.fetchone()
        if not user2_result:
            conn.close()
            return False, tr("request_not_found")
        exact_user2 = user2_result[0]
        
        # Обновляем статус на accepted
        cursor.execute('''
            UPDATE friendships 
            SET status = 'accepted'
            WHERE ((user1_username = ? AND user2_username = ?) 
                OR (user1_username = ? AND user2_username = ?))
                AND status = 'pending'
        ''', (exact_user1, exact_user2, exact_user2, exact_user1))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return True, tr("request_accepted")
        else:
            conn.close()
            return False, tr("request_not_found")
    except Exception as e:
        conn.close()
        return False, tr("request_not_found")

def reject_friend_request(user1_username, user2_username):
    """Отклоняет запрос на дружбу"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM friendships
        WHERE ((user1_username = ? AND user2_username = ?) 
            OR (user1_username = ? AND user2_username = ?))
            AND status = 'pending'
    ''', (user1_username, user2_username, user2_username, user1_username))
    
    conn.commit()
    conn.close()
    return True

def remove_friend(user1_username, user2_username):
    """Удаляет друга"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM friendships
        WHERE ((user1_username = ? AND user2_username = ?) 
            OR (user1_username = ? AND user2_username = ?))
    ''', (user1_username, user2_username, user2_username, user1_username))
    
    conn.commit()
    conn.close()
    return True

def get_friends(username):
    """Получает список друзей пользователя (оптимизировано с JOIN)"""
    if not username:
        return []
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            
            # Получаем точный username из базы (на случай различий в регистре)
            cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username,))
            user_result = cursor.fetchone()
            if not user_result:
                return []
            exact_username = user_result[0] if isinstance(user_result, tuple) else user_result['username']
            
            # Оптимизированный запрос с JOIN вместо N+1 запросов
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN f.user1_username = ? THEN f.user2_username
                        ELSE f.user1_username
                    END as friend_username,
                    u.first_name,
                    u.last_name,
                    u.avatar_path,
                    u.is_online,
                    u.last_seen
                FROM friendships f
                JOIN auth_users u ON (
                    CASE 
                        WHEN f.user1_username = ? THEN u.username = f.user2_username
                        ELSE u.username = f.user1_username
                    END
                )
                WHERE (f.user1_username = ? OR f.user2_username = ?) 
                    AND f.status = 'accepted'
            ''', (exact_username, exact_username, exact_username, exact_username))
            
            rows = cursor.fetchall()
            friends = []
            for row in rows:
                if isinstance(row, sqlite3.Row):
                    friends.append({
                        'username': row['friend_username'],
                        'first_name': row['first_name'] or '',
                        'last_name': row['last_name'] or '',
                        'avatar_path': row['avatar_path'],
                        'is_online': bool(row['is_online']) if row['is_online'] is not None else False,
                        'last_seen': row['last_seen']
                    })
                else:
                    friends.append({
                        'username': row[0],
                        'first_name': row[1] or '',
                        'last_name': row[2] or '',
                        'avatar_path': row[3],
                        'is_online': bool(row[4]) if row[4] is not None else False,
                        'last_seen': row[5]
                    })
            
            return friends
    except Exception as e:
        print(f"Ошибка получения друзей: {e}")
        return []

def get_friend_requests(username):
    """Получает список входящих запросов на дружбу (оптимизировано с JOIN)"""
    if not username:
        return []
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            
            # Получаем точный username из базы
            cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username,))
            user_result = cursor.fetchone()
            if not user_result:
                return []
            exact_username = user_result[0] if isinstance(user_result, tuple) else user_result['username']
            
            # Оптимизированный запрос с JOIN вместо N+1 запросов
            cursor.execute('''
                SELECT 
                    f.user1_username,
                    u.first_name,
                    u.last_name,
                    u.avatar_path,
                    u.is_online,
                    u.last_seen
                FROM friendships f
                JOIN auth_users u ON u.username = f.user1_username
                WHERE f.user2_username = ? AND f.status = 'pending'
            ''', (exact_username,))
            
            rows = cursor.fetchall()
            requests = []
            for row in rows:
                if isinstance(row, sqlite3.Row):
                    requests.append({
                        'username': row['user1_username'],
                        'first_name': row['first_name'] or '',
                        'last_name': row['last_name'] or '',
                        'avatar_path': row['avatar_path'],
                        'is_online': bool(row['is_online']) if row['is_online'] is not None else False,
                        'last_seen': row['last_seen']
                    })
                else:
                    requests.append({
                        'username': row[0],
                        'first_name': row[1] or '',
                        'last_name': row[2] or '',
                        'avatar_path': row[3],
                        'is_online': bool(row[4]) if row[4] is not None else False,
                        'last_seen': row[5]
                    })
            
            return requests
    except Exception as e:
        print(f"Ошибка получения запросов на дружбу: {e}")
        return []

def get_outgoing_friend_requests(username):
    """Получает список исходящих запросов на дружбу (которые я отправил) (оптимизировано с JOIN)"""
    if not username:
        return []
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            
            # Получаем точный username из базы
            cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username,))
            user_result = cursor.fetchone()
            if not user_result:
                return []
            exact_username = user_result[0] if isinstance(user_result, tuple) else user_result['username']
            
            # Оптимизированный запрос с JOIN вместо N+1 запросов
            cursor.execute('''
                SELECT 
                    f.user2_username,
                    u.first_name,
                    u.last_name,
                    u.avatar_path,
                    u.is_online,
                    u.last_seen
                FROM friendships f
                JOIN auth_users u ON u.username = f.user2_username
                WHERE f.user1_username = ? AND f.status = 'pending'
            ''', (exact_username,))
            
            rows = cursor.fetchall()
            requests = []
            for row in rows:
                if isinstance(row, sqlite3.Row):
                    requests.append({
                        'username': row['user2_username'],
                        'first_name': row['first_name'] or '',
                        'last_name': row['last_name'] or '',
                        'avatar_path': row['avatar_path'],
                        'is_online': bool(row['is_online']) if row['is_online'] is not None else False,
                        'last_seen': row['last_seen']
                    })
                else:
                    requests.append({
                        'username': row[0],
                        'first_name': row[1] or '',
                        'last_name': row[2] or '',
                        'avatar_path': row[3],
                        'is_online': bool(row[4]) if row[4] is not None else False,
                        'last_seen': row[5]
                    })
            
            return requests
    except Exception as e:
        print(f"Ошибка получения исходящих запросов на дружбу: {e}")
        return []

def get_friend_stats(username):
    """Получает статистику друга (количество отправленных заявок)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM email_history WHERE username = ?', (username,))
    result = cursor.fetchone()
    count = result[0] if result else 0
    
    conn.close()
    return count

def save_autofill_data(username, email='', lehrstelle='', firma='', body_text=''):
    """Сохраняет данные автозаполнения для аккаунта с кешированием (привязано к username)"""
    global _autofill_cache
    
    if not username:
        username = get_current_username()
        if not username:
            return  # Не можем сохранить без username
    
    # ВАЖНО: Проверяем, что username существует в базе пользователей
    conn_check = sqlite3.connect(DB_FILE)
    cursor_check = conn_check.cursor()
    cursor_check.execute('SELECT username FROM auth_users WHERE username = ?', (username,))
    user_exists = cursor_check.fetchone()
    conn_check.close()
    if not user_exists:
        return  # Не сохраняем данные для несуществующего пользователя
    
    # ВАЖНО: Если все поля пустые, удаляем запись из БД (не сохраняем пустые данные)
    email = email.strip() if email else ''
    lehrstelle = lehrstelle.strip() if lehrstelle else ''
    firma = firma.strip() if firma else ''
    body_text = body_text.strip() if body_text else ''
    
    if not email and not lehrstelle and not firma and not body_text:
        # Все поля пустые - удаляем запись из БД
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM autofill_data WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        # Очищаем кеш
        if username in _autofill_cache:
            del _autofill_cache[username]
        return  # Не сохраняем пустые данные
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем, существует ли колонка body_text
    cursor.execute("PRAGMA table_info(autofill_data)")
    columns = [column[1] for column in cursor.fetchall()]
    has_body_text = 'body_text' in columns
    
    if not has_body_text:
        # Добавляем колонку body_text если её нет
        try:
            cursor.execute('ALTER TABLE autofill_data ADD COLUMN body_text TEXT')
            conn.commit()
        except:
            pass  # Колонка уже существует или другая ошибка
    
    # Обновляем или вставляем данные
    if has_body_text or 'body_text' in [col[1] for col in cursor.execute("PRAGMA table_info(autofill_data)").fetchall()]:
        cursor.execute('''
            INSERT OR REPLACE INTO autofill_data (username, email, lehrstelle, firma, body_text, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (username, email, lehrstelle, firma, body_text))
    else:
        cursor.execute('''
            INSERT OR REPLACE INTO autofill_data (username, email, lehrstelle, firma, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (username, email, lehrstelle, firma))
    
    conn.commit()
    conn.close()
    
    # Обновляем кеш
    autofill_data = {'email': email, 'lehrstelle': lehrstelle, 'firma': firma, 'body_text': body_text}
    _autofill_cache[username] = (autofill_data, datetime.now())

def load_autofill_data(username=None):
    """Загружает данные автозаполнения для аккаунта с кешированием (привязано к username)"""
    global _autofill_cache
    
    if not username:
        username = get_current_username()
        if not username:
            return {'email': '', 'lehrstelle': '', 'firma': ''}
    
    # Проверяем кеш
    now = datetime.now()
    if username in _autofill_cache:
        cached_data, cache_time = _autofill_cache[username]
        if (now - cache_time).total_seconds() < PROFILE_CACHE_TIMEOUT:
            return cached_data
    
    # Загружаем из БД с оптимизированным подключением
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Проверяем, существует ли колонка body_text (кешируем схему таблицы)
            table_name = 'autofill_data'
            if table_name not in _table_schema_cache:
                cursor.execute("PRAGMA table_info(autofill_data)")
                columns = [column[1] for column in cursor.fetchall()]
                _table_schema_cache[table_name] = columns
            else:
                columns = _table_schema_cache[table_name]
            has_body_text = 'body_text' in columns
            
            if has_body_text:
                cursor.execute('SELECT email, lehrstelle, firma, body_text FROM autofill_data WHERE username = ?', (username,))
            else:
                cursor.execute('SELECT email, lehrstelle, firma FROM autofill_data WHERE username = ?', (username,))
            result = cursor.fetchone()
    except Exception as e:
        print(f"Ошибка загрузки данных автозаполнения: {e}")
        return {'email': '', 'lehrstelle': '', 'firma': '', 'body_text': ''}
    
    if result:
        autofill_data = {
            'email': result[0] if result[0] else '',
            'lehrstelle': result[1] if result[1] else '',
            'firma': result[2] if result[2] else '',
            'body_text': result[3] if has_body_text and len(result) > 3 else ''
        }
        # Сохраняем в кеш
        _autofill_cache[username] = (autofill_data, now)
        return autofill_data
    
    # Если данных нет, возвращаем пустые значения
    autofill_data = {'email': '', 'lehrstelle': '', 'firma': '', 'body_text': ''}
    _autofill_cache[username] = (autofill_data, now)
    return autofill_data

def save_attached_files(username, attached_files):
    """Сохраняет список прикрепленных файлов для аккаунта с физическим копированием файлов в D:/it/bewerbung/saved_attachments/"""
    if not username:
        username = get_current_username()
        if not username:
            return
    
    if not attached_files:
        return
    
    # Разрешенные форматы файлов
    ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx'}
    
    # Создаем папку для сохранения файлов пользователя в D:\it\bewerbung\saved_attachments\
    base_dir = r"D:\it\bewerbung\saved_attachments"
    user_files_dir = os.path.join(base_dir, username)
    os.makedirs(user_files_dir, exist_ok=True)
    
    saved_files = []
    
    # Копируем файлы в папку пользователя
    for file_info in attached_files:
        if isinstance(file_info, dict):
            original_path = file_info.get('path', '')
            file_name = file_info.get('name', os.path.basename(original_path))
            file_size = file_info.get('size', 0)
        else:
            original_path = file_info
            file_name = os.path.basename(original_path)
            file_size = os.path.getsize(original_path) if os.path.exists(original_path) else 0
        
        if not original_path or not os.path.exists(original_path):
            continue
        
        # Проверяем формат файла
        _, ext = os.path.splitext(file_name)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            continue
        
        # Преобразуем file_size в число если это строка
        try:
            if isinstance(file_size, str):
                file_size = int(file_size)
            else:
                file_size = int(file_size) if file_size else 0
        except (ValueError, TypeError):
            # Если не удалось преобразовать, получаем размер из файла
            try:
                file_size = os.path.getsize(original_path) if os.path.exists(original_path) else 0
            except:
                file_size = 0
        
        # Ограничение размера: 25MB
        if file_size > 25 * 1024 * 1024:
            continue
        
        # Копируем файл в папку пользователя с уникальным именем (timestamp_original_name.ext)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name, ext = os.path.splitext(file_name)
        saved_file_name = f"{timestamp}_{base_name}{ext}"
        saved_file_path = os.path.join(user_files_dir, saved_file_name)
        
        try:
            shutil.copy2(original_path, saved_file_path)
            saved_files.append({
                'name': file_name,
                'path': saved_file_path,  # Сохраняем путь к скопированному файлу
                'size': file_size,
                'original_path': original_path  # Сохраняем оригинальный путь для совместимости
            })
        except Exception as e:
            # Если не удалось скопировать, сохраняем оригинальный путь
            saved_files.append({
                'name': file_name,
                'path': original_path,
                'size': file_size
            })
    
    if saved_files:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Сохраняем список файлов как JSON
        attachments_json = json.dumps(saved_files)
        cursor.execute('''
            INSERT OR REPLACE INTO saved_attachments (username, attachments_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (username, attachments_json))
        
        conn.commit()
        conn.close()

def load_attached_files(username=None):
    """Загружает список прикрепленных файлов для аккаунта из D:/it/bewerbung/saved_attachments/"""
    if not username:
        username = get_current_username()
        if not username:
            return []
    
    # Сначала проверяем базу данных с оптимизированным подключением
    saved_files = []
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT attachments_json FROM saved_attachments WHERE username = ?', (username,))
            result = cursor.fetchone()
            if result and result[0]:
                try:
                    saved_files = json.loads(result[0])
                except:
                    saved_files = []
    except Exception as e:
        print(f"Ошибка загрузки прикрепленных файлов: {e}")
    
    # Проверяем наличие файлов в папке и обновляем список
    base_dir = r"D:\it\bewerbung\saved_attachments"
    user_files_dir = os.path.join(base_dir, username)
    
    if os.path.exists(user_files_dir):
        # Проверяем каждый файл из сохраненного списка
        valid_files = []
        for file_info in saved_files:
            file_path = file_info.get('path', '')
            if file_path and os.path.exists(file_path):
                valid_files.append(file_info)
        saved_files = valid_files
    
    return saved_files

def delete_attached_file(username, file_path):
    """Удаляет файл из папки пользователя при явном удалении вложения"""
    if not username:
        username = get_current_username()
        if not username:
            return False
    
    try:
        # Удаляем файл из файловой системы
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем запись из базы данных с оптимизированным подключением
        try:
            with DatabaseConnection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT attachments_json FROM saved_attachments WHERE username = ?', (username,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    try:
                        saved_files = json.loads(result[0])
                        # Удаляем файл из списка
                        saved_files = [f for f in saved_files if f.get('path', '') != file_path]
                        # Обновляем базу данных
                        attachments_json = json.dumps(saved_files)
                        cursor.execute('''
                            UPDATE saved_attachments 
                            SET attachments_json = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE username = ?
                        ''', (attachments_json, username))
                        conn.commit()
                        return True
                    except Exception as e:
                        print(f"Ошибка обновления базы данных при удалении файла: {e}")
                        return False
                return True
        except Exception as e:
            print(f"Ошибка удаления файла из базы данных: {e}")
            return False
    except Exception as e:
        print(f"Ошибка при удалении файла {file_path}: {e}")
        return False

def save_email_draft(username, recipient_email='', lehrstelle='', firma='', body_text='', attached_files=None, use_ai=False):
    """Сохраняет черновик письма для аккаунта (привязано к username)"""
    if not username:
        username = get_current_username()
        if not username:
            return False
    
    if attached_files is None:
        attached_files = []
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем наличие колонок и добавляем их если нужно
    try:
        cursor.execute("PRAGMA table_info(email_drafts)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        if 'attached_files_json' not in column_names:
            cursor.execute('ALTER TABLE email_drafts ADD COLUMN attached_files_json TEXT')
            conn.commit()
        
        if 'use_ai' not in column_names:
            cursor.execute('ALTER TABLE email_drafts ADD COLUMN use_ai INTEGER DEFAULT 0')
            conn.commit()
    except Exception as e:
        pass
    
    # Сохраняем список файлов как JSON
    attached_files_json = json.dumps(attached_files) if attached_files else '[]'
    
    # Проверяем наличие колонки id и created_at
    try:
        cursor.execute("PRAGMA table_info(email_drafts)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        has_id = 'id' in column_names
        has_created_at = 'created_at' in column_names
        has_updated_at = 'updated_at' in column_names
        
        if not has_created_at:
            try:
                cursor.execute('ALTER TABLE email_drafts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                conn.commit()
            except:
                pass
        
        if not has_updated_at:
            try:
                cursor.execute('ALTER TABLE email_drafts ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                conn.commit()
            except:
                pass
    except Exception as e:
        pass
    
    # Вставляем новый черновик (поддерживаем множественные черновики)
    cursor.execute('''
        INSERT INTO email_drafts (username, recipient_email, lehrstelle, firma, body_text, attached_files_json, use_ai, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''', (username, recipient_email, lehrstelle, firma, body_text, attached_files_json, 1 if use_ai else 0))
    
    conn.commit()
    conn.close()
    return True

def load_email_drafts(username=None):
    """Загружает черновики писем для аккаунта (привязано к username)"""
    if not username:
        username = get_current_username()
        if not username:
            return []
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем наличие колонок
    cursor.execute("PRAGMA table_info(email_drafts)")
    columns_info = cursor.fetchall()
    column_names = [col[1] for col in columns_info]
    
    has_attached_files = 'attached_files_json' in column_names
    has_use_ai = 'use_ai' in column_names
    
    # Проверяем наличие колонки id
    has_id = 'id' in column_names
    has_created_at = 'created_at' in column_names
    has_updated_at = 'updated_at' in column_names
    
    # Формируем SELECT запрос в зависимости от наличия колонок
    if has_attached_files and has_use_ai:
        if has_id and has_updated_at:
            cursor.execute('''
                SELECT id, recipient_email, lehrstelle, firma, body_text, attached_files_json, use_ai, created_at, updated_at
                FROM email_drafts WHERE username = ?
                ORDER BY updated_at DESC
            ''', (username,))
        else:
            cursor.execute('''
                SELECT recipient_email, lehrstelle, firma, body_text, attached_files_json, use_ai
                FROM email_drafts WHERE username = ?
            ''', (username,))
    elif has_attached_files:
        if has_id and has_updated_at:
            cursor.execute('''
                SELECT id, recipient_email, lehrstelle, firma, body_text, attached_files_json, NULL, created_at, updated_at
                FROM email_drafts WHERE username = ?
                ORDER BY updated_at DESC
            ''', (username,))
        else:
            cursor.execute('''
                SELECT recipient_email, lehrstelle, firma, body_text, attached_files_json, NULL
                FROM email_drafts WHERE username = ?
            ''', (username,))
    else:
        if has_id and has_updated_at:
            cursor.execute('''
                SELECT id, recipient_email, lehrstelle, firma, body_text, NULL, NULL, created_at, updated_at
                FROM email_drafts WHERE username = ?
                ORDER BY updated_at DESC
            ''', (username,))
        else:
            cursor.execute('''
                SELECT recipient_email, lehrstelle, firma, body_text, NULL, NULL
                FROM email_drafts WHERE username = ?
            ''', (username,))
    
    results = cursor.fetchall()
    conn.close()
    
    drafts = []
    for result in results:
        # Определяем смещение индексов в зависимости от наличия id
        offset = 1 if has_id and has_updated_at else 0
        
        attached_files = []
        if has_attached_files:
            attached_idx = 4 + offset if has_id and has_updated_at else 4
            if len(result) > attached_idx and result[attached_idx]:
                try:
                    attached_files = json.loads(result[attached_idx])
                except:
                    attached_files = []
        
        draft = {
            'email': result[0 + offset] if len(result) > 0 + offset and result[0 + offset] else '',
            'recipient_email': result[0 + offset] if len(result) > 0 + offset and result[0 + offset] else '',
            'lehrstelle': result[1 + offset] if len(result) > 1 + offset and result[1 + offset] else '',
            'firma': result[2 + offset] if len(result) > 2 + offset and result[2 + offset] else '',
            'body_text': result[3 + offset] if len(result) > 3 + offset and result[3 + offset] else '',
            'attached_files': attached_files,
        }
        
        if has_id and has_updated_at:
            draft['id'] = result[0]
            draft['created_at'] = result[7] if len(result) > 7 else None
            draft['updated_at'] = result[8] if len(result) > 8 else None
        
        if has_use_ai:
            use_ai_idx = 5 + offset if has_id and has_updated_at else 5
            draft['use_ai'] = bool(result[use_ai_idx]) if len(result) > use_ai_idx and result[use_ai_idx] is not None else False
        
        drafts.append(draft)
    
    return drafts

def get_user_registration_date(username=None):
    """Получает дату регистрации пользователя (привязана к username)"""
    if not username:
        username = get_current_username()
    
    if not username:
        # Fallback для обратной совместимости
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT created_at FROM user ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
        except sqlite3.OperationalError:
            result = None
        conn.close()
        if result and result[0]:
            return result[0]
        return None
    
    # Получаем дату регистрации из auth_users по username
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT created_at FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
    except sqlite3.OperationalError:
        result = None
    conn.close()
    if result and result[0]:
        return result[0]
    return None

def get_days_in_app(username=None):
    """Вычисляет количество дней в приложении (привязано к username)"""
    reg_date = get_user_registration_date(username)
    if not reg_date:
        return 0
    try:
        if isinstance(reg_date, str):
            # Парсим дату из строки
            if ' ' in reg_date:
                date_str = reg_date.split(' ')[0]
            else:
                date_str = reg_date
            # Пробуем разные форматы
            try:
                reg_dt = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                try:
                    reg_dt = datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    return 0
        else:
            reg_dt = reg_date
        days = (datetime.now() - reg_dt).days
        return max(0, days)
    except:
        return 0

def hash_password(password):
    """Хеширует пароль используя PBKDF2 (более безопасно, чем SHA-256)"""
    # Генерируем случайную соль
    salt = secrets.token_bytes(16)
    # Используем PBKDF2 с 100,000 итерациями
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Сохраняем соль и ключ вместе (соль:ключ в base64)
    return base64.b64encode(salt + key).decode('utf-8')

def verify_password(password, password_hash):
    """Проверяет пароль используя PBKDF2"""
    try:
        # Декодируем из base64
        decoded = base64.b64decode(password_hash.encode('utf-8'))
        salt = decoded[:16]  # Первые 16 байт - соль
        stored_key = decoded[16:]  # Остальное - ключ
        
        # Вычисляем ключ для введенного пароля
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        
        # Сравниваем ключи (постоянное время сравнения для безопасности)
        return secrets.compare_digest(stored_key, key)
    except:
        # Fallback для старых паролей (SHA-256)
        old_hash = hashlib.sha256(password.encode()).hexdigest()
        return old_hash == password_hash

def save_auth_user(username, password, first_name, last_name, phone_number='', avatar_path=None, language=None):
    """Сохраняет или создает пользователя с авторизацией (с кешированием)"""
    global _profile_cache, CURRENT_LANGUAGE
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем и добавляем колонки если их нет
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        conn.commit()
    except:
        pass  # Колонка уже существует
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN language TEXT DEFAULT "ru"')
        conn.commit()
    except:
        pass  # Колонка уже существует
    
    # Используем текущий язык если не указан
    if language is None:
        language = CURRENT_LANGUAGE
    
    password_hash = hash_password(password)
    
    # Проверяем, существует ли пользователь
    cursor.execute('SELECT id FROM auth_users WHERE username = ?', (username,))
    existing = cursor.fetchone()
    
    if existing:
        # Обновляем существующего пользователя
        # Проверяем наличие колонок через pragma
        cursor.execute("PRAGMA table_info(auth_users)")
        columns = [row[1] for row in cursor.fetchall()]
        has_updated_at = 'updated_at' in columns
        has_language = 'language' in columns
        
        if has_updated_at and has_language:
            cursor.execute('''
                UPDATE auth_users 
                SET password_hash = ?, first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?, language = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (password_hash, first_name, last_name, phone_number, avatar_path, language, username))
        elif has_updated_at:
            cursor.execute('''
                UPDATE auth_users 
                SET password_hash = ?, first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (password_hash, first_name, last_name, phone_number, avatar_path, username))
        elif has_language:
            cursor.execute('''
                UPDATE auth_users 
                SET password_hash = ?, first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?, language = ?
                WHERE username = ?
            ''', (password_hash, first_name, last_name, phone_number, avatar_path, language, username))
        else:
            # Если колонок нет, обновляем без них
            cursor.execute('''
                UPDATE auth_users 
                SET password_hash = ?, first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?
                WHERE username = ?
            ''', (password_hash, first_name, last_name, phone_number, avatar_path, username))
    else:
        # Создаем нового пользователя
        cursor.execute("PRAGMA table_info(auth_users)")
        columns = [row[1] for row in cursor.fetchall()]
        has_language = 'language' in columns
        
        if has_language:
            cursor.execute('''
                INSERT INTO auth_users (username, password_hash, first_name, last_name, phone_number, avatar_path, language, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (username, password_hash, first_name, last_name, phone_number, avatar_path, language))
        else:
            cursor.execute('''
                INSERT INTO auth_users (username, password_hash, first_name, last_name, phone_number, avatar_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (username, password_hash, first_name, last_name, phone_number, avatar_path))
    
    conn.commit()
    conn.close()
    
    # Инвалидируем кеш профиля
    if username in _profile_cache:
        del _profile_cache[username]

def verify_auth_user(username, password):
    """Проверяет авторизацию пользователя и обновляет last_login"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем наличие колонки language
    cursor.execute("PRAGMA table_info(auth_users)")
    columns = [row[1] for row in cursor.fetchall()]
    has_language = 'language' in columns
    
    if has_language:
        cursor.execute('SELECT password_hash, first_name, last_name, phone_number, avatar_path, created_at, language FROM auth_users WHERE username = ?', (username,))
    else:
        cursor.execute('SELECT password_hash, first_name, last_name, phone_number, avatar_path, created_at FROM auth_users WHERE username = ?', (username,))
    
    result = cursor.fetchone()
    
    if result and verify_password(password, result[0]):
        # Обновляем время последнего входа
        cursor.execute('UPDATE auth_users SET last_login = CURRENT_TIMESTAMP WHERE username = ?', (username,))
        conn.commit()
        
        # Инвалидируем кеш профиля
        global _profile_cache
        if username in _profile_cache:
            del _profile_cache[username]
        
        conn.close()
        
        user_data = {
            'first_name': result[1],
            'last_name': result[2],
            'phone_number': result[3] or '',
            'avatar_path': result[4],
            'created_at': result[5]
        }
        
        # Добавляем язык если колонка существует
        if has_language and len(result) > 6:
            user_data['language'] = result[6] or 'ru'
        else:
            user_data['language'] = 'ru'
        
        return user_data
    conn.close()
    return None

def save_remembered_user(username, password):
    """Сохраняет данные пользователя для автозаполнения (привязано к компьютеру/IP)"""
    global _username_cache, _username_cache_time
    machine_id = get_machine_id()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Создаем таблицу для запомненных пользователей, если её нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS remembered_users (
            machine_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Сохраняем данные для этого компьютера
    cursor.execute('''
        INSERT OR REPLACE INTO remembered_users (machine_id, username, password, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (machine_id, username, password))
    
    conn.commit()
    conn.close()
    
    # Обновляем кеш сразу с новым username, чтобы избежать проблем при быстром переключении аккаунтов
    _username_cache = username
    _username_cache_time = datetime.now()

def load_remembered_user():
    """Загружает сохраненные данные пользователя для текущего компьютера"""
    machine_id = get_machine_id()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Создаем таблицу, если её нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS remembered_users (
            machine_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Загружаем данные для этого компьютера
    cursor.execute('SELECT username, password FROM remembered_users WHERE machine_id = ?', (machine_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'username': result[0],
            'password': result[1]
        }
    return None

def clear_remembered_user():
    """Удаляет сохраненные данные пользователя для текущего компьютера"""
    global _username_cache, _username_cache_time
    machine_id = get_machine_id()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM remembered_users WHERE machine_id = ?', (machine_id,))
    conn.commit()
    conn.close()
    
    # Очищаем кеш после удаления записи
    _username_cache = None
    _username_cache_time = None

def save_user_info(first_name, last_name, phone_number='', preserve_registration_date=True, avatar_path=None, username=None):
    """Сохраняет информацию о пользователе в auth_users (привязано к username)"""
    global _profile_cache
    
    if not username:
        username = get_current_username()
        if not username:
            return  # Не можем сохранить без username
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Проверяем и добавляем колонку updated_at если её нет
    try:
        cursor.execute('ALTER TABLE auth_users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        conn.commit()
    except:
        pass  # Колонка уже существует
    
    # Получаем текущий аватар, если нужно сохранить
    # ВАЖНО: Если avatar_path не передан (None), сохраняем существующий аватар, чтобы не потерять его
    old_avatar_path = None
    if preserve_registration_date:
        cursor.execute('SELECT avatar_path FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if result and result[0]:
            old_avatar_path = result[0]
    
    # Используем новый аватар, если он передан, иначе сохраняем старый
    # Это гарантирует, что при сохранении других данных (имя, телефон) аватар не потеряется
    final_avatar_path = avatar_path if avatar_path is not None else old_avatar_path
    
    # Проверяем наличие колонки updated_at через pragma
    cursor.execute("PRAGMA table_info(auth_users)")
    columns = [row[1] for row in cursor.fetchall()]
    has_updated_at = 'updated_at' in columns
    
    # Обновляем данные в auth_users
    if has_updated_at:
        cursor.execute('''
            UPDATE auth_users 
            SET first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
        ''', (first_name, last_name, phone_number, final_avatar_path, username))
    else:
        # Если колонки updated_at нет, обновляем без неё
        cursor.execute('''
            UPDATE auth_users 
            SET first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?
            WHERE username = ?
        ''', (first_name, last_name, phone_number, final_avatar_path, username))
    
    conn.commit()
    conn.close()
    
    # Инвалидируем кеш профиля
    if username in _profile_cache:
        del _profile_cache[username]

def save_email_history(recipient_email, lehrstelle, username=None):
    """Сохраняет историю отправки email (привязана к username)"""
    global _history_cache, _history_cache_time, _stats_cache, _stats_cache_time
    
    if not username:
        username = get_current_username()
        if not username:
            # Если нет username, пытаемся получить из user таблицы
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
    
    # Проверяем, это первое письмо? (оптимизировано - проверяем через COUNT)
    is_first_email = False
    if username:
        try:
            with DatabaseConnection() as check_conn:
                check_cursor = check_conn.cursor()
                check_cursor.execute('SELECT COUNT(*) FROM email_history WHERE username = ?', (username,))
                result = check_cursor.fetchone()
                count = result[0] if result else 0
                is_first_email = count == 0
        except:
            pass  # Если ошибка, просто не выдаем рамку
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute('INSERT INTO email_history (username, recipient_email, lehrstelle) VALUES (?, ?, ?)',
                               (username, recipient_email, lehrstelle))
            else:
                # Fallback для обратной совместимости
                cursor.execute('INSERT INTO email_history (recipient_email, lehrstelle) VALUES (?, ?)',
                               (recipient_email, lehrstelle))
            conn.commit()
            
            # Если это первое письмо, даем рамку за достижение
            if is_first_email and username:
                try:
                    # Путь к рамке по умолчанию (изображение из описания пользователя)
                    # Пользователь должен будет добавить это изображение в папку frames/
                    default_frame_path = os.path.join('frames', 'first_letter_frame.png')
                    # Если файл существует, сохраняем его как рамку пользователя
                    if os.path.exists(default_frame_path):
                        # Проверяем, существует ли колонка frame_path
                        cursor.execute("PRAGMA table_info(auth_users)")
                        columns = [row[1] for row in cursor.fetchall()]
                        if 'frame_path' not in columns:
                            cursor.execute('ALTER TABLE auth_users ADD COLUMN frame_path TEXT')
                            conn.commit()
                        
                        # Сохраняем рамку
                        cursor.execute('UPDATE auth_users SET frame_path = ? WHERE username = ?', 
                                     (default_frame_path, username))
                        conn.commit()
                except Exception as e:
                    import traceback
                    traceback.print_exc()
    except Exception as e:
        print(f"Ошибка сохранения истории email: {e}")
        import traceback
        traceback.print_exc()
    
    # Инвалидируем кеш
    _history_cache = None
    _history_cache_time = None
    _stats_cache = None
    _stats_cache_time = None
    
    # Также записываем в txt файл
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        now = datetime.now()
        f.write(f"{now.strftime('%d.%m.%Y %H:%M:%S')} | {recipient_email} | {lehrstelle}\n")

def get_email_history(username=None, force_refresh=False):
    """Получает историю email с кешированием для оптимизации (привязана к username)"""
    global _history_cache, _history_cache_time
    now = datetime.now()
    
    if not username:
        username = get_current_username()
        if not username:
            # Если нет username, пытаемся получить из user таблицы
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
    
    # Проверяем кеш только если не принудительное обновление
    if not force_refresh and _history_cache is not None and _history_cache_time is not None:
        if (now - _history_cache_time).total_seconds() < CACHE_TIMEOUT:
            return _history_cache
    
    # Загружаем из БД - добавляем id для возможности удаления (ОПТИМИЗИРОВАНО)
    try:
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            if username:
                cur.execute(
                    "SELECT id, sent_at, recipient_email, lehrstelle FROM email_history WHERE username = ? ORDER BY sent_at DESC",
                    (username,)
                )
            else:
                # Fallback для обратной совместимости
                cur.execute(
                    "SELECT id, sent_at, recipient_email, lehrstelle FROM email_history ORDER BY sent_at DESC"
                )
            rows = cur.fetchall()
    except Exception as e:
        print(f"Ошибка получения истории email: {e}")
        return []
    
    # Обновляем кеш
    _history_cache = rows
    _history_cache_time = now
    return rows

def delete_email_history_entry(entry_id, username=None):
    """Удаляет отдельную запись из истории email"""
    global _history_cache, _history_cache_time
    
    if not username:
        username = get_current_username()
        if not username:
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
            else:
                return False
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Удаляем запись по id и username для безопасности
            if username:
                cursor.execute('DELETE FROM email_history WHERE id = ? AND username = ?', (entry_id, username))
            else:
                cursor.execute('DELETE FROM email_history WHERE id = ?', (entry_id,))
            conn.commit()
    except Exception as e:
        print(f"Ошибка удаления записи из истории: {e}")
        return False
    
    # Инвалидируем кеш
    global _history_cache, _history_cache_time
    _history_cache = None
    _history_cache_time = None
    
    return True

def clear_email_history(username=None):
    """Удаляет всю историю email для пользователя (привязана к username)"""
    global _history_cache, _history_cache_time, _stats_cache, _stats_cache_time
    
    if not username:
        username = get_current_username()
        if not username:
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
            else:
                return False
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute('DELETE FROM email_history WHERE username = ?', (username,))
            else:
                cursor.execute('DELETE FROM email_history')
            conn.commit()
    except Exception as e:
        print(f"Ошибка очистки истории email: {e}")
    
    # Очищаем txt файл истории
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write('')  # Очищаем файл
    except Exception as e:
        print(f"Ошибка при очистке txt файла истории: {e}")
    
    # Инвалидируем кеш
    _history_cache = None
    _history_cache_time = None
    _stats_cache = None
    _stats_cache_time = None
    
    return True

def get_email_stats_by_date(username=None):
    """Получает статистику отправок по датам с кешированием (привязана к username)"""
    global _stats_cache, _stats_cache_time
    now = datetime.now()
    
    if not username:
        username = get_current_username()
        if not username:
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
    
    # Проверяем кеш
    if _stats_cache is not None and _stats_cache_time is not None:
        if (now - _stats_cache_time).total_seconds() < CACHE_TIMEOUT:
            return _stats_cache
    
    # Загружаем из БД с оптимизированным подключением
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute("SELECT sent_at FROM email_history WHERE username = ?", (username,))
            else:
                cursor.execute("SELECT sent_at FROM email_history")
            rows = cursor.fetchall()
        
        stats = {}
        for row in rows:
            sent_at = row[0] if isinstance(row, (tuple, list)) else row['sent_at']
            try:
                dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
                date_key = dt.date()
                stats[date_key] = stats.get(date_key, 0) + 1
            except:
                try:
                    date_key = datetime.strptime(sent_at.split()[0], '%Y-%m-%d').date()
                    stats[date_key] = stats.get(date_key, 0) + 1
                except:
                    pass
        
        # Обновляем кеш
        _stats_cache = stats
        _stats_cache_time = now
        return stats
    except Exception as e:
        print(f"Ошибка получения статистики по датам: {e}")
        return {}

def get_most_popular_lehrstelle(username=None):
    """Получает самую популярную вакансию (lehrstelle) из истории (привязана к username)"""
    if not username:
        username = get_current_username()
        if not username:
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
    
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute("""
                    SELECT lehrstelle, COUNT(*) as count 
                    FROM email_history 
                    WHERE username = ?
                    GROUP BY lehrstelle 
                    ORDER BY count DESC 
                    LIMIT 1
                """, (username,))
            else:
                cursor.execute("""
                    SELECT lehrstelle, COUNT(*) as count 
                    FROM email_history 
                    GROUP BY lehrstelle 
                    ORDER BY count DESC 
                    LIMIT 1
                """)
            result = cursor.fetchone()
            if result:
                if isinstance(result, sqlite3.Row):
                    return result['lehrstelle'], result['count']
                return result[0], result[1]  # lehrstelle, count
            return None, 0
    except Exception as e:
        print(f"Ошибка получения популярной вакансии: {e}")
        return None, 0

def get_applications_count(username=None):
    """Получает количество заявок (привязано к username)"""
    if not username:
        username = get_current_username()
        if not username:
            user_info = get_user_info()
            if user_info and len(user_info) > 5:
                username = user_info[5]
    
    try:
        with DatabaseConnection() as conn:
            cur = conn.cursor()
            if username:
                cur.execute("SELECT COUNT(*) FROM email_history WHERE username = ?", (username,))
            else:
                cur.execute("SELECT COUNT(*) FROM email_history")
            result = cur.fetchone()
            if result:
                if isinstance(result, sqlite3.Row):
                    return result[0]
                return result[0]
            return 0
    except Exception as e:
        print(f"Ошибка получения количества заявок: {e}")
        return 0

class GroqAIThread(QThread):
    """Поток для генерации текста через Groq AI (бесплатный)"""
    finished = pyqtSignal(bool, str, str)  # success, text, pdf_path
    
    def __init__(self, lehrstelle, firma, user_text, first_name, last_name, phone_number='', current_status='', about_me='', additional_prompt='', german_level='B1 - Средний'):
        super().__init__()
        self.lehrstelle = lehrstelle
        self.firma = firma
        self.user_text = user_text
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.current_status = current_status
        self.about_me = about_me
        self.additional_prompt = additional_prompt
        self.german_level = german_level
        self.pdf_path = None
    
    def run(self):
        if not GROQ_AVAILABLE:
            self.finished.emit(False, tr("groq_not_installed"), '')
            return
        
        if not hasattr(config, 'GROQ_API_KEY') or config.GROQ_API_KEY == "your-groq-api-key-here":
            self.finished.emit(False, tr("groq_api_key_not_set"), '')
            return
        
        try:
            client = Groq(api_key=config.GROQ_API_KEY)
            
            # Формируем информацию о besuche из текстового поля
            besuche_text = ""
            if self.current_status:
                # AI будет использовать текст как есть и адаптировать его для письма
                besuche_text = self.current_status
            else:
                # Если в настройках указано, что сейчас нет школы/курсов,
                # формулируем это позитивно как активную подготовку к Lehrstelle
                besuche_text = (
                    f"Zurzeit nutze ich meine Zeit gezielt, um meine Fähigkeiten zu verbessern "
                    f"und mich intensiv auf eine Lehrstelle im Bereich {self.lehrstelle} vorzubereiten."
                )
            
            prompt = f"""Ты — профессиональный консультант по карьере. Твоя задача — написать убедительное письмо на вакансию (Lehrstelle).

КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
- Имя: {self.first_name} {self.last_name}
- Навыки и опыт: {self.about_me if self.about_me else 'мотивация, надежность, работа в команде'}
- Текущий статус: {besuche_text}
- Уровень немецкого: {self.german_level}
- Телефон: {self.phone_number if self.phone_number else 'не указан'}

ЦЕЛЬ: Подать заявку на позицию "{self.lehrstelle}" в компанию "{self.firma}".

ДОПОЛНИТЕЛЬНЫЕ ПОЖЕЛАНИЯ: {self.additional_prompt if self.additional_prompt else 'нет'}

СТИЛЬ: Вежливый, современный, лаконичный (в стиле Telegram).

КРИТИЧЕСКИ ВАЖНО - СТРУКТУРА ПИСЬМА:
1. В самом начале письма (ПЕРЕД "Sehr geehrte Damen und Herren") должна быть строка:
   "Bewerbung um eine Lehrstelle als {self.lehrstelle}"
   
2. Затем приветствие: "Sehr geehrte Damen und Herren"

3. В тексте письма НЕ используй markdown форматирование, пиши обычный текст

4. Структура:
   - Почему я подхожу (интерес к компании, профессии, опыт) - выдели ключевые моменты жирным
   - Призыв к действию (предложение встречи)

Составь профессиональное и привлекательное письмо для Bewerbung (заявки на обучение) на немецком языке.

ВАЖНО: Используй этот пример письма как образец стиля и структуры. Каждое письмо должно быть уникальным, но похожим по структуре:
"Sehr geehrte Damen und Herren

Schon seit meiner Kindheit interessiere ich mich für Computer, Technik und alles Digitale. Besonders spannend finde ich, wie automatisierte Systeme und Plattformen in der Industrie funktionieren und Daten zur Steuerung von Prozessen genutzt werden. Als ich las, dass Kistler Instrumente AG in Winterthur weltweit führend ist in Mess- und Sensortechnik zur Erfassung von Druck, Kraft, Drehmoment und Beschleunigung, und dabei moderne Technologien in hochkomplexen Produkten einsetzt, war ich sofort motiviert, mich bei Ihnen um eine Lehrstelle zu bewerben.

Ich möchte gern eine Ausbildung als Informatiker EFZ in der Fachrichtung Plattformentwicklung machen, weil ich grossen Spass daran habe, Programme zu entwickeln, technische Probleme zu lösen und stabile Plattformen mitzugestalten. Ich habe bereits praktische Erfahrungen gesammelt – ich durfte einen Schnuppertag machen und habe erlebt, wie vielseitig und spannend Informatik ist. Auch zu Hause programmiere ich regelmässig: ich habe Bots für Discord und Telegram entwickelt, Webseiten erstellt und mit verschiedenen Programmiersprachen gearbeitet – vor allem mit Python, aber auch ein bisschen mit Java und C++. In der Ukraine habe ich zusätzlich Programmierkurse besucht, wo ich meine Kenntnisse weiter vertiefen konnte. Ich liebe alles, was mit dieser Tätigkeit zu tun hat, und möchte meine Leidenschaft zum Beruf machen.

Ich bin sehr motiviert, lerne schnell und arbeite gerne im Team. Ich denke logisch, bleibe ruhig bei Problemen und suche immer nach der besten Lösung. Meine Stärken sind Motivation, Zielstrebigkeit, Konzentration und Teamfähigkeit. Momentan besuche ich einen Tag pro Woche die Schule und mache vier Tage Praktikum im Rahmen von Job PLUS. Davor war ich in der Schule und habe auch Deutschkurse besucht, wie Sie meinem Lebenslauf entnehmen können.

Ich arbeite ständig an mir selbst – ich trainiere im Fitnessstudio und verbessere meine Selbstdisziplin. Bei Kistler Instrumente AG möchte ich mich nicht nur weiterentwickeln und viel Neues lernen, sondern auch aktiv zum Erfolg der Firma beitragen, von erfahrenen Fachleuten lernen und an spannenden Plattform- und Systemprojekten mitarbeiten. Ich freue mich darauf, Teil eines modernen und innovativen Teams zu sein, das technologische Qualität und Präzision verbindet.

Gerne freue ich mich auf ein persönliches Gespräch oder die Möglichkeit, Sie beim Probeschnuppern von meiner Motivation zu überzeugen.

Mit freundlichen Grüssen
Illia Kornieienko"

СТРУКТУРА ПИСЬМА (следуй примеру выше, но делай каждое письмо УНИКАЛЬНЫМ):
ВАЖНО: Фокус на ЛИЧНОСТИ пользователя, а не на профессии. Название "{self.lehrstelle}" упомяни максимум 2-3 раза.
КРИТИЧЕСКИ ВАЖНО: НЕ используй одни и те же слова/фразы дважды (Motivation, Teamarbeit, neue Herausforderungen, weiterentwickeln, wertvolles Mitglied, interessiert an den Möglichkeiten, positive Einstellung и т.д.). Используй СИНОНИМЫ.
КРИТИЧЕСКИ ВАЖНО: НЕ используй "красивые слова" и литературные фразы ("Ich erinnere mich noch genau an den Moment..."). Письмо должно быть ДЕЛОВЫМ и ПРОФЕССИОНАЛЬНЫМ. Пиши прямо и конкретно.
КРИТИЧЕСКИ ВАЖНО: Письмо должно быть МАКСИМУМ 2500 символов. Пиши КОРОТКО и ПО ДЕЛУ.

1. Приветствие: "Sehr geehrte Damen und Herren" или "Sehr geehrte Frau ..." или "Sehr geehrter Herr ..."

2. Первый абзац: Личная история и интерес к сфере (ФОКУС НА ПОЛЬЗОВАТЕЛЕ + КОНКРЕТИКА)
   - Личная история пользователя: что его привело к этой сфере? (используй информацию из "{self.about_me if self.about_me else 'нет'}" и "{self.user_text if self.user_text else 'нет'}")
   - КОНКРЕТНО: Что именно в этой профессии привлекает? (для Grafikdesigner: Layouts gestalten, Logos entwickeln; для Informatiker: Programmieren, Systeme entwickeln - конкретные задачи, НЕ общие фразы)
   - Кратко упомяни интерес к фирме {self.firma} (1-2 предложения, не растягивай)

3. Второй абзац: Опыт, навыки и качества пользователя (ФОКУС НА ЧЕЛОВЕКЕ, БЕЗ ПОВТОРОВ)
   - Какой опыт есть у пользователя? (навыки, практика, Schnupperlehre - только если указано)
   - Качества и сильные стороны: {self.about_me if self.about_me else 'мотивация, надежность, работа в команде'} - встрой естественно с КОНКРЕТНЫМИ примерами, используй РАЗНЫЕ слова (не "Motivation", а "Begeisterung" или "Leidenschaft")
   - Почему пользователь подходящий человек? (фокус на ЛИЧНОСТИ, а не на профессии, используй РАЗНЫЕ формулировки)
   - НЕ повторяй название "{self.lehrstelle}" здесь - пиши про человека
   - НЕ используй слова, которые уже упомянул выше - используй СИНОНИМЫ

4. Третий абзац: Текущая ситуация и активность пользователя
   - Что делает сейчас? ({besuche_text} - адаптируй профессионально, фокус на активности пользователя)
   - Что делал до этого? (кратко, если релевантно)
   - НЕ повторяй слова из предыдущих абзацев

5. Четвертый абзац: Работа над собой и развитие
   - Работа над улучшением (спорт, саморазвитие) - только если указано или логично вытекает из "{besuche_text}"
   - Используй РАЗНЫЕ слова для выражения похожих идей

6. Пятый абзац: Желание развиваться в компании
   - Развитие в {self.firma}, привнести страсть/навыки, быть частью команды
   - Фокус на том, что ПОЛЬЗОВАТЕЛЬ может привнести, а не на общих фразах про профессию
   - КОНКРЕТНО: какие конкретные задачи/проекты интересуют? (не "neue Herausforderungen", а конкретные примеры)
   - НЕ повторяй слова из предыдущих абзацев

7. Заключение: Предложение встречи
   "Gerne freue ich mich auf ein persönliches Gespräch oder die Möglichkeit, Sie beim Probeschnuppern von meiner Motivation zu überzeugen."

8. Подпись:
   "Mit freundlichen Grüssen"
   {self.first_name} {self.last_name}
   {f"Telefon: {self.phone_number}" if self.phone_number else ""}

ИНФОРМАЦИЯ ДЛЯ ИСПОЛЬЗОВАНИЯ:
- Должность (Lehrstelle als): {self.lehrstelle}
- Компания (Firma): {self.firma}
- Имя: {self.first_name}
- Фамилия: {self.last_name}
- Номер телефона: {self.phone_number if self.phone_number else 'не указан'}
- Текущий статус: {besuche_text}
- Качества и навыки: {self.about_me if self.about_me else 'нет дополнительной информации'}
- Дополнительная информация от пользователя: {self.user_text if self.user_text else 'нет'}
{f"- ДОПОЛНИТЕЛЬНЫЙ ПРОМПТ ОТ ПОЛЬЗОВАТЕЛЯ (обязательно учти это в письме): {self.additional_prompt}" if self.additional_prompt else ""}

ТРЕБОВАНИЯ:
- Письмо должно быть ЕСТЕСТВЕННЫМ, ПЕРСОНАЛЬНЫМ и ПРИВЛЕКАТЕЛЬНЫМ
- На немецком языке
- Следуй структуре примера выше строго
- ВАЖНО: Каждое письмо должно быть УНИКАЛЬНЫМ - варьируй формулировки, но сохраняй структуру
- КРИТИЧЕСКИ ВАЖНО - ОГРАНИЧЕНИЕ ДЛИНЫ: Письмо должно быть МАКСИМУМ 2500 символов (включая пробелы). Пиши КОРОТКО и ПО ДЕЛУ. Избегай длинных предложений и лишних слов. Каждое предложение должно нести конкретную информацию.

КРИТИЧЕСКИ ВАЖНО - НИКАКОЙ ВЫДУМКИ:
- Удали любые упоминания о конкретных проектах или опыте, которых нет в исходном тексте пользователя (например, создание дискорд-ботов, знание специфических языков программирования или работа в конкретных программах), если об этом прямо не написано в предоставленной информации
- Фокус на личностных качествах: Вместо выдуманного технического опыта сделай упор на мотивацию, готовность учиться, коммуникабельность и интерес к сфере (на основе того, что предоставлено пользователем)
- Адаптация под профессию: Если пользователь пишет на {self.lehrstelle}, используй общие фразы, подходящие для этой сферы, без указания специфических достижений, которые требуют подтверждения
- Языковой барьер: Учти, что пользователь сейчас учит язык (уровень: {self.german_level}), поэтому текст должен быть грамотным и профессиональным, но не слишком перегруженным сложными академическими конструкциями, чтобы он звучал естественно для этого уровня. Адаптируй сложность текста под указанный уровень языка
- Проверка фактов: Оставь только те данные, которые указаны: имя ({self.first_name}), фамилия ({self.last_name}), город (если указан), текущий курс обучения ({besuche_text}) и качества/хобби ({self.about_me if self.about_me else 'нет дополнительной информации'})
- КРИТИЧЕСКИ ВАЖНО - ЗАПРЕТ НА ПОВТОРЫ СЛОВ И ФРАЗ: НИКОГДА не используй одно и то же слово или фразу дважды для выражения одной идеи. Например, если ты упомянул "Motivation" или "Teamarbeit" или "neue Herausforderungen" - НЕ используй эти слова снова. Вместо этого используй СИНОНИМЫ или РАЗНЫЕ формулировки: вместо "Motivation" - "Begeisterung", "Leidenschaft", "Interesse", "Engagement"; вместо "Teamarbeit" - "Zusammenarbeit", "im Team", "gemeinsam arbeiten"; вместо "neue Herausforderungen" - "spannende Aufgaben", "abwechslungsreiche Projekte", "vielfältige Tätigkeiten". Каждое качество или идея должны быть выражены РАЗНЫМИ словами в разных частях письма.
- КРИТИЧЕСКИ ВАЖНО - ЗАПРЕТ НА КОНКРЕТНЫЕ ПОВТОРЯЮЩИЕСЯ ФРАЗЫ: НИКОГДА не используй эти фразы более одного раза: "weiterentwickeln", "wertvolles Mitglied", "interessiert an den Möglichkeiten", "positive Einstellung". Если нужно выразить похожую идею - используй СИНОНИМЫ: вместо "weiterentwickeln" - "lernen", "verbessern", "ausbauen"; вместо "wertvolles Mitglied" - "Teil des Teams", "Beitrag leisten"; вместо "interessiert an den Möglichkeiten" - "begeistert von", "fasziniert von"; вместо "positive Einstellung" - "optimistisch", "zuversichtlich", "engagiert".
- Избегай повторов мыслей: не дублируй одни и те же идеи в разных абзацах. Каждую важную мысль сформулируй ОДИН раз, используя разные формулировки для похожих идей.
- КРИТИЧЕСКИ ВАЖНО - НЕ ПОВТОРЯЙ НАЗВАНИЕ LEHRSTELLE: Название профессии "{self.lehrstelle}" упомяни максимум 2-3 раза за всё письмо (в начале при указании цели и возможно один раз в середине). НЕ пиши его в каждом абзаце. Вместо повторения названия профессии, пиши больше про ЛИЧНОСТЬ пользователя: его мотивацию, качества, личную историю, что его привлекает, что он уже делает.
- КОНКРЕТИКА ПО ПРОФЕССИИ (но без названия Lehrstelle): Добавь конкретные детали о том, что именно в этой профессии привлекает пользователя. Например, для Grafikdesigner: конкретные задачи (Layouts gestalten, Logos entwickeln, Farbkonzepte erstellen), для Informatiker: конкретные технологии или проекты. НО не повторяй название "{self.lehrstelle}" - используй описательные фразы типа "in diesem Bereich", "in dieser Tätigkeit", "als Designer/Informatiker" максимум 1-2 раза.
- ФОКУС НА ПОЛЬЗОВАТЕЛЕ, а не на профессии: Больше пиши про самого человека ({self.first_name} {self.last_name}): его личную историю, интересы, мотивацию, качества, опыт, что он делает сейчас. Меньше общих фраз про профессию "{self.lehrstelle}" - упомяни её 2-3 раза, но основное внимание удели ЛИЧНОСТИ и МОТИВАЦИИ пользователя.
- Качества и сильные стороны из блока данных ("{self.about_me if self.about_me else 'нет дополнительной информации'}") упоминай максимально ОДИН раз. Встраивай их естественно в текст с коротким, конкретным примером, но не перечисляй те же качества ещё раз другими словами.
- Избегай «учебниковых» общих фраз. Не пиши предложения вроде "Grafikdesign ist wichtig für Kommunikation und Marketing" или других слишком общих утверждений. Вместо этого формулируй КОНКРЕТНО: что именно нравится пользователю, какие ситуации он переживал, что он уже делает или будет делать. Используй конкретные примеры, а не общие утверждения.
- Пытайся делать формулировки короче и содержательнее, избегай длинных фраз без новой информации.
- УБЕРИ ВСЕ ОБЩИЕ ФРАЗЫ: Не используй шаблонные фразы типа "ich bin motiviert", "ich arbeite gerne im Team", "ich suche neue Herausforderungen" - они звучат как из учебника. Вместо этого опиши КОНКРЕТНО: что именно мотивирует пользователя, как он работает в команде (примеры), какие конкретные задачи его интересуют.
- КРИТИЧЕСКИ ВАЖНО - ЗАПРЕТ НА "КРАСИВЫЕ СЛОВА" И ЛИТЕРАТУРНЫЕ ФРАЗЫ: НЕ используй литературные, "красивые" фразы, которые звучат как сочинение, а не как Bewerbung. ЗАПРЕЩЕНО использовать фразы типа: "Ich erinnere mich noch genau an den Moment...", "Seit meiner Kindheit träume ich...", "Es war immer mein Traum...", "Mit großer Begeisterung...", "Mit voller Überzeugung...". Письмо должно быть ДЕЛОВЫМ и ПРОФЕССИОНАЛЬНЫМ, а не литературным. Пиши прямо и конкретно, без "красивых" оборотов. Используй простой, но профессиональный стиль.

- Начни с ЛИЧНОЙ ИСТОРИИ пользователя ({self.first_name} {self.last_name}) и его интересов - фокус на ЧЕЛОВЕКЕ, а не на профессии. Название "{self.lehrstelle}" упомяни максимум 2-3 раза за всё письмо.
- КОНКРЕТИКА ПО ПРОФЕССИИ: Добавь конкретные детали о том, что именно в этой профессии привлекает (конкретные задачи, проекты, технологии), но НЕ используй название "{self.lehrstelle}" повторно. Используй описательные фразы.
- Покажи конкретный интерес к компании {self.firma} (кратко, 1-2 предложения, не растягивай)
- Используй информацию о текущем статусе "{besuche_text}" - адаптируй её профессионально, но точно, фокус на АКТИВНОСТИ пользователя
- Включи качества и навыки из "{self.about_me if self.about_me else 'нет'}" естественным образом, только то, что указано, и без повторов. Больше пиши про ЛИЧНОСТЬ пользователя, его мотивацию, качества, что он делает. Используй РАЗНЫЕ слова для выражения похожих идей.
- Если пользователь добавил дополнительную информацию "{self.user_text if self.user_text else 'нет'}", обязательно используй её - это важная часть ЛИЧНОЙ ИСТОРИИ
{f"- ОБЯЗАТЕЛЬНО учти дополнительный промпт от пользователя: {self.additional_prompt}" if self.additional_prompt else ""}
- Покажи мотивацию, надежность, желание работать в команде (на основе указанных качеств), но БЕЗ повторяющихся слов. Используй СИНОНИМЫ: вместо "Motivation" - "Begeisterung", "Leidenschaft", "Interesse"; вместо "Teamarbeit" - "Zusammenarbeit", "im Team"; вместо "neue Herausforderungen" - "spannende Aufgaben", "vielfältige Projekte". Фокус на КОНКРЕТНЫХ качествах пользователя, а не на общих фразах.
- Упомяни работу над собой и развитие (только если это указано в предоставленной информации либо логично вытекает из текущего статуса "{besuche_text}")
- Закончи предложением встречи или Probeschnuppern
- Сделай письмо максимально персонализированным и привлекательным, но честным. Больше про ПОЛЬЗОВАТЕЛЯ, меньше про профессию.
- Используй естественный, но профессиональный язык, подходящий для уровня {self.german_level}
- Письмо должно звучать искренне и мотивированно, но БЕЗ "красивых слов" и литературных фраз
- ВАЖНО: Каждое новое письмо должно отличаться от предыдущих - используй разные формулировки, но сохраняй структуру и стиль примера
- КРИТИЧЕСКИ ВАЖНО: НЕ повторяй название "{self.lehrstelle}" в каждом абзаце. Упомяни его 2-3 раза максимум. Вместо этого пиши больше про ЛИЧНОСТЬ, МОТИВАЦИЮ и КАЧЕСТВА пользователя.
- КРИТИЧЕСКИ ВАЖНО: НЕ используй одни и те же слова/фразы дважды. Каждое качество или идея должны быть выражены РАЗНЫМИ словами. Проверь письмо: если видишь "Motivation", "Teamarbeit", "neue Herausforderungen", "weiterentwickeln", "wertvolles Mitglied", "interessiert an den Möglichkeiten", "positive Einstellung" дважды - замени на синонимы.
- КРИТИЧЕСКИ ВАЖНО: НЕ используй литературные, "красивые" фразы типа "Ich erinnere mich noch genau an den Moment...", "Seit meiner Kindheit träume ich...". Письмо должно быть ДЕЛОВЫМ и ПРОФЕССИОНАЛЬНЫМ. Пиши прямо и конкретно.
- КРИТИЧЕСКИ ВАЖНО: Письмо должно быть МАКСИМУМ 2500 символов. Пиши КОРОТКО и ПО ДЕЛУ, без лишних слов и длинных предложений.

Составь полный текст письма в стиле примера выше, но сделай его уникальным. ВАЖНО: Письмо должно быть МАКСИМУМ 2500 символов. Пиши КОРОТКО и ПО ДЕЛУ, без лишних слов."""
            
            response = client.chat.completions.create(
                model=getattr(config, 'GROQ_MODEL', 'llama-3.1-70b-versatile'),
                messages=[
                    {"role": "system", "content": "Ты профессиональный помощник для составления Bewerbung писем на немецком языке. Пиши коротко, деловым стилем, без 'красивых слов'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800  # Ограничение для ~2500 символов
            )
            
            # Безопасная обработка ответа
            if not response or not hasattr(response, 'choices') or not response.choices:
                self.finished.emit(False, "❌ Ошибка: AI не вернул ответ. Попробуйте еще раз.", '')
                return
            
            if len(response.choices) == 0 or not hasattr(response.choices[0], 'message'):
                self.finished.emit(False, "❌ Ошибка: Неверный формат ответа от AI. Попробуйте еще раз.", '')
                return
            
            if not hasattr(response.choices[0].message, 'content') or not response.choices[0].message.content:
                self.finished.emit(False, "❌ Ошибка: AI вернул пустой ответ. Попробуйте еще раз.", '')
                return
            
            generated_text = response.choices[0].message.content.strip()
            
            if not generated_text:
                self.finished.emit(False, "❌ Ошибка: AI сгенерировал пустой текст. Попробуйте еще раз.", '')
                return
            
            # Создаем PDF файл (ленивая загрузка reportlab)
            pdf_path = ''
            try:
                # Ленивая загрузка reportlab для оптимизации времени запуска
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import mm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.enums import TA_JUSTIFY
                import tempfile
                import os
                
                # Создаем временный PDF файл
                temp_dir = tempfile.gettempdir()
                pdf_filename = f"bewerbung_{self.first_name}_{self.last_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_path = os.path.join(temp_dir, pdf_filename)
                
                # Создаем PDF документ
                doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                                      rightMargin=30*mm, leftMargin=30*mm,
                                      topMargin=30*mm, bottomMargin=30*mm)
                
                # Стили (улучшенные - меньший размер текста)
                styles = getSampleStyleSheet()
                normal_style = ParagraphStyle(
                    'CustomNormal',
                    parent=styles['Normal'],
                    fontSize=9,  # Уменьшен размер шрифта
                    leading=12,  # Уменьшен межстрочный интервал
                    alignment=TA_JUSTIFY,
                    spaceAfter=10,
                    fontName='Helvetica'
                )
                
                # Стиль для заголовков (если есть)
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading2'],
                    fontSize=12,
                    leading=16,
                    spaceAfter=8,
                    fontName='Helvetica-Bold'
                )
                
                # Стиль для даты
                date_style = ParagraphStyle(
                    'CustomDate',
                    parent=styles['Normal'],
                    fontSize=10,
                    leading=14,
                    alignment=2,  # Выравнивание по правому краю
                    spaceAfter=12,
                    fontName='Helvetica'
                )
                
                # Получаем текущую дату в формате "Zürich, день месяц год"
                # datetime уже импортирован в начале файла
                now = datetime.now()
                # Немецкие названия месяцев
                months_de = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                            'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
                date_str = f"Zürich, {now.day}. {months_de[now.month - 1]} {now.year}"
                
                # Разбиваем текст на параграфы
                story = []
                
                # Добавляем дату в самом верху
                story.append(Paragraph(date_str, date_style))
                story.append(Spacer(1, 8))
                
                paragraphs = generated_text.split('\n\n')
                
                for para in paragraphs:
                    if para.strip():
                        # Определяем, является ли параграф заголовком (короткий и в верхнем регистре или с двоеточием)
                        is_title = len(para.strip()) < 50 and (para.strip().isupper() or ':' in para.strip())
                        # Заменяем переносы строк на <br/>
                        para_text = para.replace('\n', '<br/>')
                        # Обрабатываем markdown форматирование (**текст** -> жирный)
                        import re
                        para_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', para_text)
                        # Используем соответствующий стиль
                        style_to_use = title_style if is_title else normal_style
                        story.append(Paragraph(para_text, style_to_use))
                        story.append(Spacer(1, 4))  # Уменьшен отступ между параграфами
                
                # Собираем PDF
                doc.build(story)
                
            except Exception as e:
                print(f"Ошибка создания PDF: {e}")
                # Если не удалось создать PDF, продолжаем без него
                pdf_path = ''
            
            self.finished.emit(True, generated_text, pdf_path)
            
        except Exception as e:
            error_msg = str(e)
            
            # Обработка специфических ошибок Groq
            if "401" in error_msg or "invalid_api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                self.finished.emit(False, 
                    "❌ Неверный API ключ Groq.\n\n"
                    "Получите бесплатный ключ на https://console.groq.com/\n"
                    "И добавьте его в config.py")
            elif "429" in error_msg or "rate_limit" in error_msg.lower():
                self.finished.emit(False, 
                    "❌ Превышен лимит запросов. Подождите немного и попробуйте снова.\n"
                    "Groq предоставляет бесплатный доступ, но с ограничениями по частоте запросов.")
            else:
                self.finished.emit(False, f"❌ Ошибка при генерации текста через Groq AI:\n{error_msg}")

class EmailThread(QThread):
    """Поток для отправки email через SMTP или Gmail API"""
    finished = pyqtSignal(bool, str)
    
    def __init__(self, smtp_server, smtp_port, use_tls, sender_email, 
                 sender_password, recipient_email, subject, body, attachments=None, use_gmail_api=False, credentials=None):
        super().__init__()
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_tls = use_tls
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        self.use_gmail_api = use_gmail_api
        self.credentials = credentials
    
    def run(self):
        if self.use_gmail_api and self.credentials and GOOGLE_OAUTH_AVAILABLE:
            # Отправка через Gmail API
            try:
                service = build('gmail', 'v1', credentials=self.credentials)
                
                # Создаем сообщение
                msg = MIMEMultipart()
                msg['To'] = self.recipient_email
                msg['Subject'] = self.subject
                
                msg.attach(MIMEText(self.body, 'plain', 'utf-8'))
                
                # Прикрепляем файлы
                for file_path in self.attachments:
                    try:
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                    except Exception as e:
                        print(f"Ошибка при прикреплении файла {file_path}: {e}")
                
                # Кодируем сообщение в base64url
                raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
                
                # Отправляем через Gmail API
                message = {'raw': raw_message}
                service.users().messages().send(userId='me', body=message).execute()
                
                self.finished.emit(True, f"Email успешно отправлен на {self.recipient_email} через Gmail!")
            except HttpError as e:
                error_str = str(e)
                error_code = e.resp.status if hasattr(e, 'resp') else None
                
                # Обработка специфических ошибок Gmail API
                if error_code == 403:
                    if "accessNotConfigured" in error_str or "Gmail API has not been used" in error_str or "is disabled" in error_str:
                        # Извлекаем project ID из ошибки, если есть
                        import re
                        project_match = re.search(r'project (\d+)', error_str)
                        project_id = project_match.group(1) if project_match else "ваш проект"
                        
                        error_msg = (
                            "❌ Gmail API не включен в вашем проекте Google Cloud\n\n"
                            f"Проект: {project_id}\n\n"
                            "Решение:\n"
                            "1. Перейдите в Google Cloud Console:\n"
                            f"   https://console.cloud.google.com/apis/api/gmail.googleapis.com/overview?project={project_id}\n\n"
                            "2. Нажмите кнопку 'Enable' (Включить)\n\n"
                            "3. Подождите 1-2 минуты для активации\n\n"
                            "4. Попробуйте отправить письмо снова\n\n"
                            "Если вы только что включили API, подождите несколько минут,\n"
                            "чтобы изменения вступили в силу."
                        )
                        self.finished.emit(False, error_msg)
                    elif "insufficientPermissions" in error_str or "insufficient authentication" in error_str:
                        self.finished.emit(False, 
                            "❌ Недостаточно прав для отправки писем\n\n"
                            "Проблема: У вашего аккаунта нет прав на отправку писем через Gmail API.\n\n"
                            "Решение:\n"
                            "1. Отключите Google аккаунт в профиле\n"
                            "2. Подключите его заново, убедившись, что вы дали все необходимые разрешения")
                    else:
                        self.finished.emit(False, f"❌ Ошибка Gmail API (403): {error_str}")
                elif error_code == 401:
                    self.finished.emit(False, 
                        "❌ Ошибка авторизации Gmail API\n\n"
                        "Проблема: Токен доступа истек или недействителен.\n\n"
                        "Решение:\n"
                        "1. Отключите Google аккаунт в профиле\n"
                        "2. Подключите его заново")
                else:
                    self.finished.emit(False, f"❌ Ошибка Gmail API ({error_code if error_code else 'неизвестно'}): {error_str}")
            except Exception as e:
                self.finished.emit(False, f"❌ Произошла ошибка при отправке через Gmail:\n{str(e)}")
        else:
            # Отправка через SMTP (старый способ)
            try:
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = self.recipient_email
                msg['Subject'] = self.subject
                
                msg.attach(MIMEText(self.body, 'plain', 'utf-8'))
                
                # Прикрепляем файлы
                for file_path in self.attachments:
                    try:
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
                    except Exception as e:
                        print(f"Ошибка при прикреплении файла {file_path}: {e}")
                
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
                
                self.finished.emit(True, f"Email успешно отправлен на {self.recipient_email}!")
            except smtplib.SMTPAuthenticationError:
                self.finished.emit(False, "Ошибка аутентификации! Проверьте логин и пароль.")
            except smtplib.SMTPException as e:
                self.finished.emit(False, f"Ошибка отправки email: {str(e)}")
            except Exception as e:
                self.finished.emit(False, f"Произошла ошибка: {str(e)}")

class LoginScreen(QMainWindow):
    """Двухпанельный экран входа в стиле прикрепленного изображения"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("login_title"))
        # Убираем фиксированный размер для растягивания по ширине
        self.setMinimumSize(1200, 720)
        self.resize(1600, 720)
        self.setup_ui()
        self.prefill_user()
        self.apply_theme()
        self.update_datetime()
        # Обновление даты/времени каждую секунду
        self.datetime_timer = QTimer()
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)
        # Загружаем изображение после показа окна
        QTimer.singleShot(100, self.load_image)
        # Устанавливаем позиции элементов после показа окна
        QTimer.singleShot(150, self.update_overlay_positions)

    def load_image(self):
        """Загружает изображение из URL и затемняет его через Pillow"""
        try:
            image_url = config.LOGIN_IMAGE_URL
            with urlopen(image_url) as response:
                image_data = response.read()
            
            # Открываем изображение через Pillow (ленивая загрузка)
            Image, ImageEnhance, _ = _get_pil_modules()
            pil_image = Image.open(BytesIO(image_data))
            
            # Затемняем изображение (brightness 0.4 = 40% яркости)
            enhancer = ImageEnhance.Brightness(pil_image)
            darkened_image = enhancer.enhance(0.78)
            
            # Конвертируем обратно в bytes
            img_byte_arr = BytesIO()
            darkened_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Загружаем затемненное изображение в QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(img_byte_arr.getvalue())
            
            # Сохраняем оригинальное изображение
            self.original_pixmap = pixmap
            
            # Устанавливаем изображение на полный экран
            self.update_image_size()
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            # Устанавливаем placeholder, если не удалось загрузить
            self.image_label.setText(tr("image_not_loaded"))
            self.image_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 14px;")


    def update_image_size(self):
        """Обновляет размер изображения на полный экран с улучшенным качеством"""
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            # Получаем размеры окна
            window_width = self.width()
            window_height = self.height()
            
            if window_width > 0 and window_height > 0:
                # Получаем device pixel ratio для Retina дисплеев
                device_pixel_ratio = self.devicePixelRatio()
                
                # Вычисляем целевые размеры с учетом DPR для лучшего качества
                target_width = int(window_width * device_pixel_ratio)
                target_height = int(window_height * device_pixel_ratio)
                
                # Используем высококачественное масштабирование с сохранением пропорций
                # KeepAspectRatioByExpanding заполняет всю область, обрезая при необходимости
                scaled_pixmap = self.original_pixmap.scaled(
                    target_width, 
                    target_height,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Устанавливаем device pixel ratio для четкости на Retina дисплеях
                scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
                self.image_label.setPixmap(scaled_pixmap)
        
        # Обновляем позиции элементов поверх изображения
        self.update_overlay_positions()
    
    def update_overlay_positions(self):
        """Обновляет позиции элементов поверх изображения"""
        if hasattr(self, 'form_card') and hasattr(self, 'central_widget'):
            # Растягиваем форму по ширине с отступами (40% ширины окна, минимум 400, максимум 700)
            form_width = max(400, min(int(self.central_widget.width() * 0.4), 700))
            # Используем сохраненную высоту или вычисляем один раз
            if not hasattr(self, '_form_height'):
                form_height = self.form_card.sizeHint().height()
                if form_height == 0:
                    form_height = 320  # Фиксированная высота по умолчанию
                self._form_height = form_height
            else:
                form_height = self._form_height  # Используем сохраненную высоту
            
            x = (self.central_widget.width() - form_width) // 2
            y = (self.central_widget.height() - form_height) // 2
            # Устанавливаем размер формы с возможностью растягивания по ширине
            self.form_card.setMinimumWidth(form_width)
            self.form_card.setFixedHeight(form_height)
            self.form_card.setGeometry(x, y, form_width, form_height)
            
            # Обновляем позицию метки ошибки (над виджетом, не влияет на размеры)
            if hasattr(self, 'error_label') and self.error_label.isVisible():
                # Фиксированные размеры - не меняются при повторных вызовах
                error_width = 400  # Увеличена ширина
                error_height = 80  # Фиксированная высота (достаточно для текста)
                error_x = x + (form_width - error_width) // 2
                error_y = y - error_height - 20  # 20px отступ над виджетом
                # Устанавливаем фиксированные размеры
                self.error_label.setFixedSize(error_width, error_height)
                self.error_label.setGeometry(error_x, error_y, error_width, error_height)
                self.error_label.raise_()
                # Убеждаемся, что текст виден - применяем стиль напрямую в стиле приложения
                self.error_label.setStyleSheet("""
                    QLabel#errorLabel {
                        color: #FFFFFF;
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #f97316, stop:1 #dc2626);
                        padding: 14px 20px;
                        border-radius: 14px;
                        font-size: 13px;
                        font-weight: 600;
                        border: 2px solid rgba(251, 146, 60, 0.7);
                    }
                """)
            # Убираем тень для минималистичного стиля
                # Убеждаемся, что виджет виден
                self.error_label.show()
                self.error_label.update()
                self.error_label.repaint()
        
        # Обновляем позицию даты (верхний левый угол)
        if hasattr(self, 'datetime_label'):
            margin = 40
            self.datetime_label.move(margin, margin)
        
        # Обновляем позицию кнопки языка (верхний правый угол)
        if hasattr(self, 'language_button') and hasattr(self, 'central_widget'):
            margin = 40
            self.language_button.move(
                self.central_widget.width() - self.language_button.width() - margin,
                margin
            )
        

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # Главный layout - изображение на весь экран
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central.setLayout(main_layout)

        # Светлый фиолетово-белый фон
        central.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #EEE9F6, stop:0.4 #E2DBF2, stop:1 #CFC2E6);
                font-family: "Inter", "Segoe UI", sans-serif;
            }
        """)
        
        # Убираем изображение - используем только градиентный фон
        self.image_label = QLabel()
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        main_layout.addWidget(self.image_label)
        
        # Сохраняем ссылку на центральный виджет для позиционирования
        self.central_widget = central

        # Дата и время в верхнем левом углу (поверх всего) - улучшенный стиль
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("datetimeLabel")
        self.datetime_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.datetime_label.setParent(central)
        self.datetime_label.raise_()
        self.datetime_label.setFixedSize(280, 60)  # Увеличена высота для двух строк
        self.datetime_label.move(25, 25)

        # Кнопка переключения языка в верхнем правом углу (увеличена)
        self.language_button = QPushButton('DE' if CURRENT_LANGUAGE == 'de' else 'RU')
        self.language_button.setObjectName("languageButton")
        self.language_button.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.language_button.setFixedSize(60, 40)  # Увеличена кнопка
        self.language_button.setParent(central)
        self.language_button.raise_()
        self.language_button.clicked.connect(self.toggle_language)

        # Форма входа в минималистичном стиле без теней
        self.form_card = QFrame()
        self.form_card.setObjectName("formCard")
        self.form_card.setParent(central)
        self.form_card.raise_()
        
        # Убираем тень для минималистичного стиля
        
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        form_layout.setContentsMargins(40, 40, 40, 40)
        self.form_card.setLayout(form_layout)
        
        # Заголовок формы
        title_label = QLabel(tr("login_title"))
        title_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
                background: transparent;
                padding: 0px;
                margin-bottom: 8px;
            }
        """)
        form_layout.addWidget(title_label)
        
        # Подзаголовок (будет обновляться при переключении режимов)
        self.subtitle_label = QLabel(tr("welcome_back"))
        self.subtitle_label.setFont(QFont("Segoe UI", 13))
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #8A7A9A;
                background: transparent;
                padding: 0px;
                margin-bottom: 24px;
            }
        """)
        form_layout.addWidget(self.subtitle_label)
        
        form_layout.addSpacing(8)

        # Поля для регистрации (скрыты по умолчанию)
        self.first_name_entry = QLineEdit()
        self.first_name_entry.setObjectName("nameInput")
        self.first_name_entry.setPlaceholderText(tr("first_name"))
        self.first_name_entry.setFixedHeight(56)
        form_layout.addWidget(self.first_name_entry)
        self.first_name_entry.hide()
        
        self.last_name_entry = QLineEdit()
        self.last_name_entry.setObjectName("nameInput")
        self.last_name_entry.setPlaceholderText(tr("last_name"))
        self.last_name_entry.setFixedHeight(56)
        form_layout.addWidget(self.last_name_entry)
        self.last_name_entry.hide()
        
        # Поле никнейма
        self.username_entry = QLineEdit()
        self.username_entry.setObjectName("nameInput")
        self.username_entry.setPlaceholderText(tr("username"))
        self.username_entry.setFixedHeight(56)
        form_layout.addWidget(self.username_entry)
        
        # Отступ между полями
        form_layout.addSpacing(12)

        # Поле пароля
        self.password_entry = QLineEdit()
        self.password_entry.setObjectName("nameInput")
        self.password_entry.setPlaceholderText(tr("password"))
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setFixedHeight(56)
        form_layout.addWidget(self.password_entry)

        # Чекбокс "Запомнить меня"
        self.remember_me_checkbox = QCheckBox(tr("remember_me"))
        self.remember_me_checkbox.setObjectName("rememberMeCheckbox")
        form_layout.addWidget(self.remember_me_checkbox)

        form_layout.addSpacing(12)  # Уменьшено с 20 до 12

        # Статистика (увеличена высота для огонька) - скрыта на странице входа
        self.stat_card = QFrame()
        self.stat_card.setObjectName("statCard")
        self.stat_card.setFixedHeight(90)  # Увеличена высота (длина)
        self.stat_card.setMinimumWidth(280)  # Минимальная ширина для огонька
        stat_layout = QVBoxLayout()
        stat_layout.setContentsMargins(18, 12, 18, 12)
        stat_layout.setSpacing(5)
        self.stat_card.setLayout(stat_layout)
        
        self.stat_value = QLabel()
        self.stat_value.setObjectName("statValue")
        self.stat_value.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.stat_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_layout.addWidget(self.stat_value)
        
        self.stat_label = QLabel("")  # Будет обновляться в update_stat_display
        self.stat_label.setObjectName("statLabel")
        self.stat_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Normal))
        self.stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_layout.addWidget(self.stat_label)
        
        form_layout.addWidget(self.stat_card)
        self.stat_card.hide()  # Скрываем по умолчанию на странице входа

        form_layout.addSpacing(12)  # Уменьшено с 20 до 12

        # Метка для отображения ошибок (поверх виджета, не влияет на размеры)
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        # Делаем метку дочерним элементом central_widget для абсолютного позиционирования поверх всего
        self.error_label.setParent(central)
        self.error_label.raise_()
        # Устанавливаем фиксированный размер (не меняется)
        self.error_label.setFixedSize(400, 80)  # Увеличена ширина
        # Применяем стиль в стиле приложения
        self.error_label.setStyleSheet("""
            QLabel#errorLabel {
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f97316, stop:1 #dc2626);
                padding: 14px 20px;
                border-radius: 14px;
                font-size: 13px;
                font-weight: 600;
                border: 2px solid rgba(251, 146, 60, 0.7);
            }
        """)

        # Переключатель между входом и регистрацией
        self.is_register_mode = False
        self.mode_switch_label = QLabel()
        self.mode_switch_label.setObjectName("modeSwitchLabel")
        self.mode_switch_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_switch_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_switch_label.mousePressEvent = self.toggle_mode
        
        # Кнопка входа/регистрации
        self.login_button = QPushButton(tr("login_button"))
        self.login_button.setObjectName("loginButton")
        self.login_button.setFixedHeight(52)
        self.login_button.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self.on_login)
        
        # Убираем тень для минималистичного стиля
        
        # Элементы будут добавлены в правильном порядке в update_mode_ui()
        # Пока добавляем их временно, порядок будет исправлен
        form_layout.addWidget(self.mode_switch_label)
        form_layout.addWidget(self.login_button)
        
        # Обновляем переключатель режима (он переставит элементы при необходимости)
        self.update_mode_ui()
        
        # Анимация появления формы
        self.form_card.setWindowOpacity(0.0)
        fade_animation = QPropertyAnimation(self.form_card, b"windowOpacity")
        fade_animation.setDuration(400)
        fade_animation.setStartValue(0.0)
        fade_animation.setEndValue(1.0)
        fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(100, fade_animation.start)

    def resizeEvent(self, event):
        """Обработчик изменения размера окна"""
        super().resizeEvent(event)
        if hasattr(self, 'image_label'):
            QTimer.singleShot(50, self.update_image_size)
        # Обновляем позицию ошибки при изменении размера
        if hasattr(self, 'error_label') and self.error_label.isVisible():
            QTimer.singleShot(50, self.update_overlay_positions)

    def toggle_language(self):
        """Переключает язык интерфейса"""
        global CURRENT_LANGUAGE
        # Переключаем язык через новую систему локализации
        current = get_current_language()
        new_lang = 'de' if current == 'ru' else 'ru'
        set_language(new_lang, save_to_db=True)
        CURRENT_LANGUAGE = new_lang
        self.language_button.setText('DE' if CURRENT_LANGUAGE == 'de' else 'RU')
        self.update_ui_texts()
        # Язык будет сохранен при входе/регистрации, здесь не сохраняем
    
    def toggle_mode(self, event=None):
        """Переключает между режимом входа и регистрации"""
        self.is_register_mode = not self.is_register_mode
        self.update_mode_ui()
    
    def update_mode_ui(self):
        """Обновляет UI в зависимости от режима"""
        form_layout = self.form_card.layout()
        
        # Удаляем кнопку и переключатель из layout для перестановки
        form_layout.removeWidget(self.login_button)
        form_layout.removeWidget(self.mode_switch_label)
        
        if self.is_register_mode:
            # Режим регистрации
            self.login_button.setText(tr("register_button"))
            self.setWindowTitle(tr("register_title"))
            self.mode_switch_label.setText(tr("have_account"))
            # Обновляем подзаголовок
            if hasattr(self, 'subtitle_label'):
                self.subtitle_label.setText(tr("create_new_account"))
            
            # Показываем поля имени и фамилии
            self.first_name_entry.show()
            self.last_name_entry.show()
            
            # Добавляем отступ между фамилией и никнеймом в режиме регистрации
            username_index = form_layout.indexOf(self.username_entry)
            if username_index > 0:
                # Проверяем, нет ли уже spacing перед username_entry
                prev_item = form_layout.itemAt(username_index - 1)
                if not (prev_item and prev_item.spacerItem()):
                    form_layout.insertSpacing(username_index, 8)
            
            # Скрываем "Запомнить меня" и статистику в режиме регистрации
            if hasattr(self, 'remember_me_checkbox'):
                self.remember_me_checkbox.hide()
            if hasattr(self, 'stat_card'):
                self.stat_card.hide()
            
            # Порядок для регистрации: переключатель -> кнопка (переключатель выше кнопки)
            form_layout.addSpacing(8)  # Отступ перед переключателем
            form_layout.addWidget(self.mode_switch_label)
            form_layout.addSpacing(4)  # Отступ
            # Увеличиваем кнопку регистрации
            self.login_button.setFixedHeight(52)
            self.login_button.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            form_layout.addWidget(self.login_button)
        else:
            # Режим входа
            self.login_button.setText(tr("login_button"))
            self.setWindowTitle(tr("login_title"))
            self.mode_switch_label.setText(tr("no_account"))
            # Обновляем подзаголовок
            if hasattr(self, 'subtitle_label'):
                self.subtitle_label.setText(tr("welcome_back"))
            
            # Скрываем поля имени и фамилии
            self.first_name_entry.hide()
            self.last_name_entry.hide()
            
            # Убираем отступ между фамилией и никнеймом (если был добавлен)
            # Находим и удаляем spacing перед username_entry
            username_index = form_layout.indexOf(self.username_entry)
            if username_index > 0:
                item = form_layout.itemAt(username_index - 1)
                if item and item.spacerItem():
                    form_layout.removeItem(item)
            
            # Показываем "Запомнить меня" в режиме входа
            if hasattr(self, 'remember_me_checkbox'):
                self.remember_me_checkbox.show()
            # Скрываем статистику на странице входа (нельзя считать до входа)
            if hasattr(self, 'stat_card'):
                self.stat_card.hide()
            
            # Порядок для входа: переключатель -> кнопка
            form_layout.addSpacing(8)  # Отступ перед переключателем
            form_layout.addWidget(self.mode_switch_label)
            form_layout.addSpacing(4)  # Отступ
            # Размер кнопки входа
            self.login_button.setFixedHeight(52)
            self.login_button.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            form_layout.addWidget(self.login_button)
        
        # Обновляем стиль переключателя
        self.mode_switch_label.setStyleSheet("""
            QLabel#modeSwitchLabel {
                color: #6C4A8B;
                background: transparent;
                padding: 12px 0px;
                font-size: 13px;
                font-weight: 500;
            }
            QLabel#modeSwitchLabel:hover {
                color: #A78BFA;
            }
        """)
    
    def update_ui_texts(self):
        """Обновляет тексты интерфейса при смене языка"""
        self.username_entry.setPlaceholderText(tr("username"))
        self.password_entry.setPlaceholderText(tr("password"))
        self.remember_me_checkbox.setText(tr("remember_me"))
        self.first_name_entry.setPlaceholderText(tr("first_name"))
        self.last_name_entry.setPlaceholderText(tr("last_name"))
        self.update_mode_ui()  # Обновляем режим
        # Обновляем метку статистики
        self.update_stat_label()

    def update_datetime(self):
        """Обновляет дату и время в стиле приложения"""
        now = datetime.now()
        # Улучшенный стиль: дата и время в более читаемом формате
        weekday_keys = [
            "weekday_monday", "weekday_tuesday", "weekday_wednesday", "weekday_thursday",
            "weekday_friday", "weekday_saturday", "weekday_sunday"
        ]
        weekday = tr(weekday_keys[now.weekday()])
        date_str = now.strftime("%d.%m.%Y")
        date_str = f"{weekday}, {date_str}"
        
        time_str = now.strftime("%H:%M:%S")  # Добавляем секунды для более точного отображения
        # Улучшенный формат с разделителем
        self.datetime_label.setText(f"{date_str}\n{time_str}")

    def apply_theme(self):
        """
        Apply base palette styles for LoginScreen.
        """
        colors = get_app_colors()
        
        # Use theme colors instead of hardcoded values
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                font-family: "Inter", "Segoe UI", sans-serif;
            }}
            
            QLabel#imageLabel {{
                background: transparent;
            }}
            
            QLabel#datetimeLabel {{
                color: {colors['text_secondary']};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                padding: 12px 16px;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 500;
                border: 1px solid {colors['card_border']};
            }}
            
            QLabel#errorLabel {{
                color: {colors['error_text']};
                background: {colors['error_bg']};
                padding: 14px 20px;
                border-radius: 14px;
                font-size: 13px;
                font-weight: 600;
                border: 2px solid rgba(251, 146, 60, 0.7);
            }}
            
            QFrame#formCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                border-radius: 20px;
                border: 1px solid {colors['card_border']};
            }}
            
            QLineEdit#nameInput {{
                background-color: {colors['input_bg']};
                color: {colors['input_text']};
                border: 1px solid {colors['input_border']};
                border-radius: 16px;
                padding: 18px 22px;
                font-size: 14px;
                font-weight: 500;
            }}
            
            QLineEdit#nameInput:focus {{
                border: 2px solid {colors['input_border_focus']};
            }}
            
            QLineEdit#nameInput::placeholder {{
                color: {colors['text_tertiary']};
            }}
            
            QFrame#statCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                border: 1px solid {colors['card_border']};
                border-radius: 16px;
            }}
            
            QLabel#statValue {{
                color: {colors['text_primary']};
                background: transparent;
            }}
            
            QLabel#statLabel {{
                color: {colors['text_secondary']};
                background: transparent;
                font-size: 12px;
            }}
            
            QPushButton#loginButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['button_primary_bg']}, 
                    stop:1 {colors['accent_alt']});
                border: none;
                color: {colors['button_primary_text']};
                border-radius: 16px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            
            QPushButton#loginButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['button_primary_hover']}, 
                    stop:1 {colors['accent']});
            }}
            
            QPushButton#loginButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['button_primary_bg']}, 
                    stop:1 {colors['accent_alt']});
                opacity: 0.9;
            }}
            
            QPushButton#loginButton:disabled {{
                background-color: {colors['button_secondary_bg']};
                color: {colors['text_tertiary']};
            }}
            
            QCheckBox#rememberMeCheckbox {{
                color: {colors['text_primary']};
                background: transparent;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 0px;
            }}
            
            QCheckBox#rememberMeCheckbox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {colors['input_border']};
                border-radius: 6px;
                background-color: {colors['input_bg']};
            }}
            
            QCheckBox#rememberMeCheckbox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['accent']}, 
                    stop:1 {colors['accent_alt']});
                border-color: {colors['accent']};
            }}
            
            QCheckBox#rememberMeCheckbox::indicator:hover {{
                border-color: {colors['accent']};
            }}
            
            QPushButton#languageButton {{
                background: {colors['button_secondary_bg']};
                color: {colors['button_secondary_text']};
                border: 1px solid {colors['input_border']};
                border-radius: 12px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton#languageButton:hover {{
                background: {colors['button_secondary_hover']};
                border-color: {colors['accent']};
            }}
            QPushButton#languageButton:pressed {{
                background: {colors['button_secondary_hover']};
                opacity: 0.9;
            }}
        """
        )

    def prefill_user(self):
        """Заполняет поля данными из сохраненного пользователя"""
        remembered = load_remembered_user()
        if remembered:
            self.username_entry.setText(remembered.get('username', ''))
            self.password_entry.setText(remembered.get('password', ''))
            self.remember_me_checkbox.setChecked(True)
        self.refresh_stat()

    def refresh_stat(self):
        """Обновляет статистику - показывает дни в приложении"""
        username = get_current_username()
        days = get_days_in_app(username)
        self.stat_value.setText(str(days))
        # Обновляем метку
        self.update_stat_label()
        # Добавляем огонек если дней >= 3
        if days >= 3:
            fire_emoji = "🔥"
            self.stat_value.setText(f"{fire_emoji} {days}")
    
    def update_stat_label(self):
        """Обновляет метку статистики при смене языка"""
        if hasattr(self, 'stat_label'):
            self.stat_label.setText(tr("days_in_app"))

    def show_error(self, message):
        """Показывает ошибку над виджетом (не влияет на размеры других элементов)"""
        if hasattr(self, 'error_label'):
            self.error_label.setText(message)
            # Применяем стиль в стиле приложения
            self.error_label.setStyleSheet("""
                QLabel#errorLabel {
                    color: #FFFFFF;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f97316, stop:1 #dc2626);
                    padding: 14px 20px;
                    border-radius: 14px;
                    font-size: 13px;
                    font-weight: 600;
                    border: 2px solid rgba(251, 146, 60, 0.7);
                }
            """)
            # Убираем тень для минималистичного стиля
            
            # Анимация появления ошибки
            self.error_label.setWindowOpacity(0.0)
            self.error_label.show()
            self.error_label.raise_()
            
            fade_animation = QPropertyAnimation(self.error_label, b"windowOpacity")
            fade_animation.setDuration(300)
            fade_animation.setStartValue(0.0)
            fade_animation.setEndValue(1.0)
            fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_animation.start()
            
            # Обновляем позицию ошибки с небольшой задержкой для правильного позиционирования
            QTimer.singleShot(50, self.update_overlay_positions)
            # Скрываем ошибку через 5 секунд с анимацией
            def hide_error():
                if hasattr(self, 'error_label') and self.error_label.isVisible():
                    fade_out = QPropertyAnimation(self.error_label, b"windowOpacity")
                    fade_out.setDuration(300)
                    fade_out.setStartValue(1.0)
                    fade_out.setEndValue(0.0)
                    fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
                    fade_out.finished.connect(lambda: self.error_label.hide() if hasattr(self, 'error_label') else None)
                    fade_out.start()
            QTimer.singleShot(5000, hide_error)
    
    def on_login(self):
        global _profile_cache, CURRENT_LANGUAGE
        
        # Скрываем предыдущие ошибки
        if hasattr(self, 'error_label'):
            self.error_label.hide()
        
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()
        
        if self.is_register_mode:
            # Режим регистрации
            first_name = self.first_name_entry.text().strip()
            last_name = self.last_name_entry.text().strip()
            
            if not username or not password or not first_name or not last_name:
                self.show_error(tr("fill_all_fields"))
                return
            
            # Валидация имени (минимум 2 буквы)
            if len(first_name) < 2:
                self.show_error(tr("name_min_length"))
                return
            
            # Валидация фамилии (минимум 1 буква)
            if len(last_name) < 1:
                self.show_error(tr("lastname_min_length"))
                return
            
            # Проверяем, не существует ли уже пользователь
            user_data = verify_auth_user(username, password)
            if user_data:
                self.show_error(tr("user_exists"))
                return
            
            # Регистрируем нового пользователя (сохраняем текущий язык)
            save_auth_user(username, password, first_name, last_name, language=CURRENT_LANGUAGE)
            
            # КРИТИЧНО: Сохраняем "Запомнить меня" для этого компьютера ПЕРЕД созданием EmailApp
            # Это гарантирует, что get_current_username() вернет правильный username
            if self.remember_me_checkbox.isChecked():
                save_remembered_user(username, password)
            else:
                clear_remembered_user()
            
            # Инвалидируем кеш профиля для старого и нового пользователя
            _profile_cache.clear()  # Очищаем весь кеш профиля, чтобы избежать смешивания данных
            
            self.login_button.setEnabled(False)
            self.login_button.setText(tr("loading"))
            QTimer.singleShot(1500, lambda: self._finish_login(first_name, last_name, username))
        else:
            # Режим входа
            if not username or not password:
                error_msg = tr("enter_username_password")
                self.show_error(error_msg)
                return
            
            # Проверяем авторизацию через БД
            user_data = verify_auth_user(username, password)
            
            if not user_data:
                # Пользователь не найден или неверный пароль
                self.show_error(tr("wrong_credentials"))
                return
            
            # Пользователь найден, используем его данные
            first = user_data['first_name']
            last = user_data['last_name']
            phone_number = user_data.get('phone_number', '') or ''
            avatar_path = user_data.get('avatar_path')
            
            # Загружаем сохраненный язык пользователя из БД через новый менеджер
            manager = get_localization_manager()
            saved_language = manager.load_language_from_db(username)
            if saved_language:
                manager.set_language(saved_language, save_to_db=False)
                CURRENT_LANGUAGE = saved_language
            else:
                # Если язык не сохранен, используем язык по умолчанию (de)
                CURRENT_LANGUAGE = manager.get_current_language()
            
            # Обновляем язык интерфейса ПЕРЕД сохранением
            self.language_button.setText('DE' if CURRENT_LANGUAGE == 'de' else ('RU' if CURRENT_LANGUAGE == 'ru' else 'EN'))
            self.update_ui_texts()
            
            # КРИТИЧНО: Сохраняем "Запомнить меня" для этого компьютера ПЕРЕД созданием EmailApp
            # Это гарантирует, что get_current_username() вернет правильный username
            if self.remember_me_checkbox.isChecked():
                save_remembered_user(username, password)
            else:
                clear_remembered_user()
            
            # Инвалидируем кеш профиля для старого и нового пользователя
            _profile_cache.clear()  # Очищаем весь кеш профиля, чтобы избежать смешивания данных
            
            self.login_button.setEnabled(False)
            self.login_button.setText(tr("loading"))
            QTimer.singleShot(1500, lambda: self._finish_login(first, last, username))

    def _finish_login(self, first, last, username):
        """Завершает вход и открывает главное окно"""
        # КРИТИЧНО: Убеждаемся, что кеш username обновлен ПЕРЕД созданием EmailApp
        # Это гарантирует, что get_current_username() вернет правильный username
        global _username_cache, _username_cache_time, _profile_cache, _history_cache, _stats_cache
        
        # Принудительно очищаем все кеши перед созданием нового окна
        _username_cache = None
        _username_cache_time = None
        _profile_cache.clear()
        _history_cache = None
        _stats_cache = None
        
        # Язык уже загружен и применен в on_login, просто открываем главное окно
        self.main_window = EmailApp()
        self.main_window.show()
        self.close()


# Импорт SettingsDialog перенесен внутрь функции show_settings для избежания циклического импорта


class AvatarCropDialog(QDialog):
    """Диалог для обрезки аватара в стиле Discord"""
    
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.original_pixmap = QPixmap(image_path) if image_path else None
        self.scale_factor = 1.0
        self.rotation = 0
        self.image_offset = QPoint(0, 0)
        self.processed_pixmap = None
        self.setup_ui()
        if self.original_pixmap:
            self.update_preview()
    
    def setup_ui(self):
        """Создает интерфейс диалога в стиле приложения"""
        self.setWindowTitle(tr("edit_image"))
        self.setFixedSize(450, 550)
        # Убираем стандартные рамки Windows
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(167, 139, 250, 0.95),
                    stop:1 rgba(139, 120, 220, 0.98));
                border-radius: 24px;
                border: 2px solid rgba(167, 139, 250, 0.5);
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        # Область предпросмотра с круглой обрезкой
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(200, 200)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 3px solid rgba(167, 139, 250, 0.6);
                border-radius: 100px;
                background-color: rgba(240, 235, 250, 0.5);
            }
        """)
        layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Область для редактирования изображения
        self.image_label = QLabel()
        self.image_label.setMinimumSize(400, 220)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: rgba(230, 220, 235, 0.5);
                border-radius: 12px;
                border: 2px solid rgba(167, 139, 250, 0.2);
            }
        """)
        # Добавляем обработчики для перетаскивания изображения
        self.image_label.mousePressEvent = self.mouse_press_event
        self.image_label.mouseMoveEvent = self.mouse_move_event
        self.image_label.mouseReleaseEvent = self.mouse_release_event
        self.drag_start_pos = None
        self.image_offset = QPoint(0, 0)
        layout.addWidget(self.image_label)
        
        # Слайдер для масштабирования
        scale_layout = QHBoxLayout()
        scale_layout.setSpacing(10)
        
        scale_min_label = QLabel("🔍")
        scale_min_label.setFixedSize(20, 20)
        scale_layout.addWidget(scale_min_label)
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setMinimum(50)
        self.scale_slider.setMaximum(200)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        scale_layout.addWidget(self.scale_slider)
        
        scale_max_label = QLabel("🔍")
        scale_max_label.setFixedSize(20, 20)
        scale_layout.addWidget(scale_max_label)
        
        # Кнопка поворота
        rotate_button = QPushButton("↻")
        rotate_button.setFixedSize(30, 30)
        rotate_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(167, 139, 250, 0.3);
                border: none;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(167, 139, 250, 0.5);
            }
        """)
        rotate_button.clicked.connect(self.rotate_image)
        scale_layout.addWidget(rotate_button)
        
        layout.addLayout(scale_layout)
        
        # Кнопки действий
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        reset_button = QPushButton(tr("reset"))
        reset_button.setStyleSheet("""
            QPushButton {
                color: rgba(255, 255, 255, 0.7);
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        reset_button.clicked.connect(self.reset_image)
        buttons_layout.addWidget(reset_button)
        
        buttons_layout.addStretch()
        
        cancel_button = QPushButton(tr("cancel"))
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.3);
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        submit_button = QPushButton(tr("send_email"))
        submit_button.setStyleSheet("""
            QPushButton {
                background-color: #9C89B8;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8A7A9A;
            }
        """)
        submit_button.clicked.connect(self.accept)
        buttons_layout.addWidget(submit_button)
        
        layout.addLayout(buttons_layout)
    
    def update_preview(self):
        """Обновляет предпросмотр в реальном времени"""
        if not self.original_pixmap:
            return
        
        # Масштабируем изображение
        pixmap = self.original_pixmap.copy()
        
        # Применяем масштаб
        if self.scale_factor != 1.0:
            size = pixmap.size()
            new_size = size * self.scale_factor
            pixmap = pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Применяем поворот
        if self.rotation != 0:
            transform = QTransform()
            transform.rotate(self.rotation)
            pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        
        # Сохраняем обработанное изображение для обрезки
        self.processed_pixmap = pixmap
        
        # Отображаем в области редактирования с учетом смещения
        label_size = self.image_label.size()
        scaled = pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Создаем pixmap для отображения с учетом смещения
        display_pixmap = QPixmap(label_size)
        display_pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(display_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Вычисляем позицию с учетом смещения
        base_x = (label_size.width() - scaled.width()) // 2
        base_y = (label_size.height() - scaled.height()) // 2
        draw_x = base_x + self.image_offset.x()
        draw_y = base_y + self.image_offset.y()
        
        # Ограничиваем смещение, чтобы изображение не уходило слишком далеко
        max_offset_x = scaled.width() // 2
        max_offset_y = scaled.height() // 2
        draw_x = max(-max_offset_x, min(draw_x, label_size.width() - scaled.width() + max_offset_x))
        draw_y = max(-max_offset_y, min(draw_y, label_size.height() - scaled.height() + max_offset_y))
        
        painter.drawPixmap(draw_x, draw_y, scaled)
        painter.end()
        self.image_label.setPixmap(display_pixmap)
        
        # Обновляем круглый предпросмотр в реальном времени
        self.update_circular_preview(pixmap)
    
    def update_circular_preview(self, pixmap):
        """Обновляет круглый предпросмотр"""
        # Обрезаем изображение по кругу
        size = min(pixmap.width(), pixmap.height())
        x = (pixmap.width() - size) // 2
        y = (pixmap.height() - size) // 2
        
        cropped = pixmap.copy(x, y, size, size)
        
        # Создаем круглую маску
        rounded = QPixmap(size, size)
        rounded.fill(QColor(0, 0, 0, 0))
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(cropped))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        
        # Масштабируем до размера предпросмотра
        scaled = rounded.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
    
    def on_scale_changed(self, value):
        """Обработчик изменения масштаба - обновление в реальном времени"""
        self.scale_factor = value / 100.0
        self.update_preview()
    
    def mouse_press_event(self, event):
        """Обработчик нажатия мыши для перетаскивания"""
        self.drag_start_pos = event.pos()
    
    def mouse_move_event(self, event):
        """Обработчик перемещения мыши для перетаскивания"""
        if self.drag_start_pos:
            delta = event.pos() - self.drag_start_pos
            self.image_offset += delta
            self.drag_start_pos = event.pos()
            self.update_preview()
    
    def mouse_release_event(self, event):
        """Обработчик отпускания мыши"""
        self.drag_start_pos = None
    
    def rotate_image(self):
        """Поворачивает изображение на 90 градусов"""
        self.rotation = (self.rotation + 90) % 360
        self.update_preview()
    
    def reset_image(self):
        """Сбрасывает изменения"""
        self.scale_factor = 1.0
        self.rotation = 0
        self.image_offset = QPoint(0, 0)
        self.scale_slider.setValue(100)
        self.update_preview()
    
    def get_cropped_image_path(self):
        """Возвращает путь к обрезанному изображению"""
        if not hasattr(self, 'processed_pixmap') or not self.processed_pixmap:
            if not self.original_pixmap:
                return None
            # Применяем все преобразования
            pixmap = self.original_pixmap.copy()
            
            if self.scale_factor != 1.0:
                size = pixmap.size()
                new_size = size * self.scale_factor
                pixmap = pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            if self.rotation != 0:
                transform = QTransform()
                transform.rotate(self.rotation)
                pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        else:
            pixmap = self.processed_pixmap
        
        # Вычисляем область обрезки с учетом смещения
        label_size = self.image_label.size()
        scaled = pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Вычисляем центр обрезки с учетом смещения
        # Переводим смещение из координат label в координаты scaled изображения
        scale_x = scaled.width() / label_size.width() if label_size.width() > 0 else 1
        scale_y = scaled.height() / label_size.height() if label_size.height() > 0 else 1
        
        # Центр label
        label_center_x = label_size.width() // 2
        label_center_y = label_size.height() // 2
        
        # Позиция центра с учетом смещения
        offset_center_x = label_center_x + self.image_offset.x()
        offset_center_y = label_center_y + self.image_offset.y()
        
        # Переводим в координаты scaled изображения
        base_x = (label_size.width() - scaled.width()) // 2
        base_y = (label_size.height() - scaled.height()) // 2
        
        crop_center_x = (offset_center_x - base_x) * scale_x
        crop_center_y = (offset_center_y - base_y) * scale_y
        
        # Обрезаем по кругу из центра с учетом смещения
        crop_size = min(scaled.width(), scaled.height())
        x = int(crop_center_x - crop_size // 2)
        y = int(crop_center_y - crop_size // 2)
        
        # Ограничиваем координаты
        x = max(0, min(x, scaled.width() - crop_size))
        y = max(0, min(y, scaled.height() - crop_size))
        
        cropped = scaled.copy(x, y, crop_size, crop_size)
        
        # Сохраняем во временный файл
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_path = temp_file.name
        temp_file.close()
        cropped.save(temp_path)
        return temp_path

class DataDialog(QDialog):
    """Улучшенный диалог с данными пользователя с блочной структурой и UX-улучшениями"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("data"))
        self.setFixedSize(1100, 950)  # Увеличен размер для новых блоков
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.phone_is_visible = False
        self.is_editing_status = False
        self.used_in_email_fields = {}  # Словарь полей, используемых в письме
        self.setup_ui()
        self.setup_animation()
    
    def validate_german_phone(self, phone):
        """Валидация немецкого формата телефона"""
        if not phone:
            return True, ""
        # Удаляем все пробелы и дефисы
        cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        # Проверяем формат: +49 или 0 в начале, затем цифры
        if cleaned.startswith("+49"):
            if len(cleaned) >= 12 and len(cleaned) <= 15 and cleaned[3:].isdigit():
                return True, ""
            return False, "Некорректный формат. Пример: +49 151 12345678"
        elif cleaned.startswith("0"):
            if len(cleaned) >= 10 and len(cleaned) <= 13 and cleaned[1:].isdigit():
                return True, ""
            return False, "Некорректный формат. Пример: 0151 12345678"
        elif cleaned.startswith("49"):
            if len(cleaned) >= 11 and len(cleaned) <= 14 and cleaned[2:].isdigit():
                return True, ""
            return False, "Некорректный формат. Пример: 49 151 12345678"
        return False, "Некорректный формат. Используйте +49 или 0 в начале"
    
    def get_soft_skills_suggestions(self):
        """Возвращает предложения Soft Skills для автозаполнения"""
        lang = get_current_language()
        if lang == 'de':
            return [
                "Teamfähigkeit", "Kommunikationsfähigkeit", "Zuverlässigkeit",
                "Eigeninitiative", "Lernbereitschaft", "Flexibilität",
                "Problemlösungsfähigkeit", "Organisationsfähigkeit", "Kreativität",
                "Verantwortungsbewusstsein", "Zeitmanagement", "Stressresistenz"
            ]
        elif lang == 'ru':
            return [
                "Командная работа", "Коммуникабельность", "Надежность",
                "Инициативность", "Обучаемость", "Гибкость",
                "Решение проблем", "Организаторские способности", "Креативность",
                "Ответственность", "Тайм-менеджмент", "Стрессоустойчивость"
            ]
        else:  # en
            return [
                "Teamwork", "Communication", "Reliability",
                "Initiative", "Willingness to learn", "Flexibility",
                "Problem-solving", "Organizational skills", "Creativity",
                "Responsibility", "Time management", "Stress resistance"
            ]
    
    def get_lehrstelle_tips(self):
        """Возвращает подсказки для Lehrstelle (что важно работодателю)"""
        lang = get_current_language()
        if lang == 'de':
            return "💡 Tipp: Erwähnen Sie Ihre Motivation, praktische Erfahrungen und warum Sie sich für diese Ausbildung interessieren."
        elif lang == 'ru':
            return "💡 Совет: Упомяните вашу мотивацию, практический опыт и почему вас интересует это обучение."
        else:  # en
            return "💡 Tip: Mention your motivation, practical experience, and why you're interested in this training."
    
    
    def setup_ui(self):
        """Создает интерфейс диалога в футуристичном стиле Telegram/Discord"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Контейнер с градиентным фоном в футуристичном стиле
        container = QFrame()
        container.setObjectName("dataDialogContainer")
        
        # Тень для контейнера
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(108, 77, 255, 30))
        container.setGraphicsEffect(shadow)
        
        container.setStyleSheet("""
            QFrame#dataDialogContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F0ECF8,
                    stop:1 #E8E0F5);
                border-radius: 28px;
                border: none;
            }
        """)
        
        # Внутренний виджет для скролла
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(32, 28, 32, 32)
        container_layout.setSpacing(24)
        scroll_widget.setLayout(container_layout)
        
        # Создаем область прокрутки
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #E8E0F5;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.6),
                    stop:1 rgba(108, 77, 255, 0.4));
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.8),
                    stop:1 rgba(108, 77, 255, 0.6));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        
        # Создаем основной layout для контейнера
        container_main_layout = QVBoxLayout()
        container_main_layout.setContentsMargins(0, 0, 0, 0)
        container_main_layout.setSpacing(0)
        container.setLayout(container_main_layout)
        
        # Добавляем скролл в контейнер
        container_main_layout.addWidget(scroll_area)
        
        # Заголовок с кнопкой закрытия и индикатором заполненности
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(16)
        
        title_label = QLabel(tr("data"))
        title_label.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
                background: transparent;
                letter-spacing: -0.5px;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Индикатор заполненности убран по требованию
        
        close_button = QPushButton("✕")
        close_button.setFixedSize(40, 40)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 107, 107, 0.15);
                border: 1.5px solid rgba(255, 107, 107, 0.3);
                border-radius: 20px;
                color: #FF6B6B;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 107, 0.25);
                border-color: rgba(255, 107, 107, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(255, 107, 107, 0.2);
            }
        """)
        header_layout.addWidget(close_button)
        container_layout.addLayout(header_layout)
        
        # Секция: Основная информация (карточка с тенью)
        info_card = QFrame()
        info_card.setObjectName("infoCard")
        
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setXOffset(0)
        card_shadow.setYOffset(4)
        card_shadow.setColor(QColor(108, 77, 255, 12))
        info_card.setGraphicsEffect(card_shadow)
        
        info_card.setStyleSheet("""
            QFrame#infoCard {
                background: #FFFFFF;
                border: none;
                border-radius: 20px;
            }
        """)
        info_card_layout = QVBoxLayout()
        info_card_layout.setContentsMargins(24, 20, 24, 20)
        info_card_layout.setSpacing(18)
        info_card.setLayout(info_card_layout)
        
        # Заголовок секции с иконкой и отметкой "используется в письме"
        section_header = QHBoxLayout()
        section_header.setContentsMargins(0, 0, 0, 8)
        section_title = QLabel(tr('main_info'))
        section_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        section_title.setStyleSheet("""
            QLabel {
                color: #4B3F72;
                background: transparent;
                letter-spacing: -0.3px;
            }
        """)
        section_header.addWidget(section_title)
        
        # Бейдж "используется в письме"
        used_badge = QLabel(tr("used_in_email"))
        used_badge.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        used_badge.setStyleSheet("""
            QLabel {
                color: #6C4DFF;
                background: rgba(108, 77, 255, 0.1);
                border-radius: 8px;
                padding: 4px 10px;
            }
        """)
        section_header.addWidget(used_badge)
        section_header.addStretch()
        info_card_layout.addLayout(section_header)
        
        # Имя и фамилия в одну строку
        name_container = QHBoxLayout()
        name_container.setSpacing(12)
        name_container.setContentsMargins(0, 0, 0, 0)
        
        # Имя
        first_name_container = QVBoxLayout()
        first_name_container.setSpacing(8)
        first_name_label_layout = QHBoxLayout()
        first_name_label = QLabel(tr("first_name"))
        first_name_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        first_name_label.setStyleSheet("color: #4B3F72; background: transparent;")
        first_name_label_layout.addWidget(first_name_label)
        
        first_name_label_layout.addStretch()
        first_name_container.addLayout(first_name_label_layout)
        
        self.first_name_input = QLineEdit()
        self.first_name_input.setFont(QFont("Inter", 14))
        placeholder_text = "Max" if get_current_language() == 'de' else "Макс" if get_current_language() == 'ru' else "Max"
        self.first_name_input.setPlaceholderText(placeholder_text)
        self.first_name_input.setToolTip("Введите ваше имя. Это поле используется в письме." if get_current_language() == 'ru' else "Enter your first name. This field is used in the email." if get_current_language() == 'en' else "Geben Sie Ihren Vornamen ein. Dieses Feld wird im Brief verwendet.")
        self.first_name_input.setMinimumHeight(50)
        self.first_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                background-color: #FFFFFF;
            }
        """)
        first_name_container.addWidget(self.first_name_input)
        name_container.addLayout(first_name_container, stretch=1)
        
        # Фамилия
        last_name_container = QVBoxLayout()
        last_name_container.setSpacing(8)
        last_name_label_layout = QHBoxLayout()
        last_name_label = QLabel(tr("last_name"))
        last_name_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        last_name_label.setStyleSheet("color: #4B3F72; background: transparent;")
        last_name_label_layout.addWidget(last_name_label)
        
        last_name_label_layout.addStretch()
        last_name_container.addLayout(last_name_label_layout)
        
        self.last_name_input = QLineEdit()
        self.last_name_input.setFont(QFont("Inter", 14))
        placeholder_text = "Mustermann" if get_current_language() == 'de' else "Иванов" if get_current_language() == 'ru' else "Smith"
        self.last_name_input.setPlaceholderText(placeholder_text)
        self.last_name_input.setToolTip("Введите вашу фамилию. Это поле используется в письме." if get_current_language() == 'ru' else "Enter your last name. This field is used in the email." if get_current_language() == 'en' else "Geben Sie Ihren Nachnamen ein. Dieses Feld wird im Brief verwendet.")
        self.last_name_input.setMinimumHeight(50)
        self.last_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                background-color: #FFFFFF;
            }
        """)
        last_name_container.addWidget(self.last_name_input)
        name_container.addLayout(last_name_container, stretch=1)
        
        info_card_layout.addLayout(name_container)
        
        # Номер телефона с скрытием (перемещен в основную секцию)
        phone_container = QVBoxLayout()
        phone_container.setSpacing(8)
        
        phone_header_layout = QHBoxLayout()
        phone_label_layout = QHBoxLayout()
        phone_header = QLabel(tr('phone_number'))
        phone_header.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        phone_header.setStyleSheet("color: #4B3F72; background: transparent; padding: 0px;")
        phone_label_layout.addWidget(phone_header)
        
        phone_label_layout.addStretch()
        phone_header_layout.addLayout(phone_label_layout)
        phone_header_layout.addStretch()
        
        phone_display_layout = QHBoxLayout()
        phone_display_layout.setContentsMargins(0, 0, 0, 0)
        phone_display_layout.setSpacing(12)
        
        # Контейнер для поля телефона и сообщения об ошибке
        phone_input_container = QVBoxLayout()
        phone_input_container.setSpacing(4)
        
        self.phone_input_dialog = QLineEdit()
        self.phone_input_dialog.setFont(QFont("Inter", 14))
        # Более гибкий валидатор для немецкого формата
        phone_validator = QRegularExpressionValidator(QRegularExpression(r'^[\+\s\-\(\)0-9]*$'))
        self.phone_input_dialog.setValidator(phone_validator)
        self.phone_input_dialog.setReadOnly(True)
        self.phone_input_dialog.setMinimumHeight(44)
        placeholder_phone = "+49 151 12345678" if get_current_language() == 'de' else "+49 151 12345678" if get_current_language() == 'en' else "+49 151 12345678"
        self.phone_input_dialog.setPlaceholderText(placeholder_phone)
        tooltip_phone = "Введите номер телефона в немецком формате. Пример: +49 151 12345678 или 0151 12345678. Это поле используется в письме." if get_current_language() == 'ru' else "Enter phone number in German format. Example: +49 151 12345678 or 0151 12345678. This field is used in the email." if get_current_language() == 'en' else "Geben Sie die Telefonnummer im deutschen Format ein. Beispiel: +49 151 12345678 oder 0151 12345678. Dieses Feld wird im Brief verwendet."
        self.phone_input_dialog.setToolTip(tooltip_phone)
        
        # Метка для отображения ошибки валидации
        self.phone_error_label = QLabel()
        self.phone_error_label.setFont(QFont("Inter", 10))
        self.phone_error_label.setStyleSheet("color: #FF6B6B; background: transparent; padding-left: 4px;")
        self.phone_error_label.hide()
        phone_input_container.addWidget(self.phone_input_dialog)
        phone_input_container.addWidget(self.phone_error_label)
        self.phone_input_dialog.setStyleSheet("""
            QLineEdit {
                background-color: #FAF9FE;
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 1.5px solid #6C4DFF;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border-color: #E4DEFF;
            }
        """)
        phone_display_layout.addLayout(phone_input_container, stretch=1)
        
        self.show_phone_button = QPushButton(tr("show_phone"))
        self.show_phone_button.setFixedHeight(44)
        self.show_phone_button.setFixedWidth(120)
        self.show_phone_button.clicked.connect(self.toggle_phone_visibility_dialog)
        self.show_phone_button.setStyleSheet("""
            QPushButton {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                color: #6C4DFF;
                font-size: 13px;
                font-weight: 600;
                padding: 12px 18px;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
            }
        """)
        phone_display_layout.addWidget(self.show_phone_button)
        phone_container.addLayout(phone_display_layout)
        
        # Кнопки сохранения/отмены для телефона
        self.phone_buttons_layout = QHBoxLayout()
        self.phone_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.phone_buttons_layout.setSpacing(10)
        self.phone_buttons_layout.addStretch()
        
        edit_phone_btn = QPushButton(tr("edit"))
        edit_phone_btn.setFixedSize(40, 40)
        edit_phone_btn.setToolTip(tr("edit_phone"))
        edit_phone_btn.clicked.connect(self.edit_phone_dialog)
        edit_phone_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 159, 67, 0.15);
                border: none;
                border-radius: 10px;
                color: #FF9F43;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 159, 67, 0.25);
            }
        """)
        phone_header_layout.addWidget(edit_phone_btn)
        phone_container.addLayout(phone_header_layout)
        phone_container.addLayout(phone_display_layout)
        
        self.cancel_phone_button = QPushButton(tr("cancel"))
        self.cancel_phone_button.setFixedHeight(36)
        self.cancel_phone_button.setFixedWidth(100)
        self.cancel_phone_button.clicked.connect(self.cancel_edit_phone_dialog)
        self.cancel_phone_button.setStyleSheet("""
            QPushButton {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                color: #8E8AAE;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
            }
        """)
        self.cancel_phone_button.hide()
        self.phone_buttons_layout.addWidget(self.cancel_phone_button)
        
        self.save_phone_button = QPushButton(tr("save"))
        self.save_phone_button.setFixedHeight(36)
        self.save_phone_button.setFixedWidth(100)
        self.save_phone_button.clicked.connect(self.save_phone_dialog)
        self.save_phone_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C4DFF,
                    stop:1 #6F4EF6);
                border: none;
                border-radius: 12px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5A3FE0,
                    stop:1 #5A3FE0);
            }
        """)
        self.save_phone_button.hide()
        self.phone_buttons_layout.addWidget(self.save_phone_button)
        
        phone_container.addLayout(self.phone_buttons_layout)
        info_card_layout.addLayout(phone_container)
        
        container_layout.addWidget(info_card)
        
        # Секция: Дополнительная информация (карточка с тенью)
        additional_card = QFrame()
        additional_card.setObjectName("additionalCard")
        
        additional_shadow = QGraphicsDropShadowEffect()
        additional_shadow.setBlurRadius(20)
        additional_shadow.setXOffset(0)
        additional_shadow.setYOffset(4)
        additional_shadow.setColor(QColor(108, 77, 255, 12))
        additional_card.setGraphicsEffect(additional_shadow)
        
        additional_card.setStyleSheet("""
            QFrame#additionalCard {
                background: #FFFFFF;
                border: none;
                border-radius: 20px;
            }
        """)
        additional_card_layout = QVBoxLayout()
        additional_card_layout.setContentsMargins(24, 20, 24, 20)
        additional_card_layout.setSpacing(18)
        additional_card.setLayout(additional_card_layout)
        
        # Заголовок секции с иконкой
        additional_header = QHBoxLayout()
        additional_header.setContentsMargins(0, 0, 0, 8)
        additional_section_title = QLabel(tr('additional_info'))
        additional_section_title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        additional_section_title.setStyleSheet("""
            QLabel {
                color: #4B3F72;
                background: transparent;
                letter-spacing: -0.3px;
            }
        """)
        additional_header.addWidget(additional_section_title)
        additional_header.addStretch()
        additional_card_layout.addLayout(additional_header)
        
        # Род занятий (Beruf) - точно как виджет номера телефона
        beruf_container = QVBoxLayout()
        beruf_container.setSpacing(8)
        
        beruf_header_layout = QHBoxLayout()
        beruf_header = QLabel(tr('occupation'))
        beruf_header.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        beruf_header.setStyleSheet("color: #4B3F72; background: transparent; padding: 0px;")
        beruf_header_layout.addWidget(beruf_header)
        beruf_header_layout.addStretch()
        
        beruf_display_layout = QHBoxLayout()
        beruf_display_layout.setContentsMargins(0, 0, 0, 0)
        beruf_display_layout.setSpacing(12)
        
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Inter", 14))
        self.status_label.setMinimumHeight(44)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self.status_label.setWordWrap(True)
        beruf_display_layout.addWidget(self.status_label, stretch=1)
        
        # Кнопка редактирования в хедере (как у телефона)
        edit_status_btn = QPushButton(tr("edit"))
        edit_status_btn.setFixedSize(40, 40)
        edit_status_btn.setToolTip(tr("edit"))
        edit_status_btn.clicked.connect(self.edit_status)
        edit_status_btn.setStyleSheet("""
            QPushButton {
                background-color: #FAF9FE;
                border: none;
                border-radius: 10px;
                color: #6C4DFF;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
            }
        """)
        beruf_header_layout.addWidget(edit_status_btn)
        beruf_container.addLayout(beruf_header_layout)
        beruf_container.addLayout(beruf_display_layout)
        
        self.status_input = QLineEdit()
        self.status_input.setFont(QFont("Inter", 14))
        self.status_input.setPlaceholderText(tr("status_placeholder"))
        self.status_input.setMinimumHeight(44)
        self.status_input.setStyleSheet("""
            QLineEdit {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                background-color: #FFFFFF;
            }
        """)
        self.status_input.hide()
        beruf_container.addWidget(self.status_input)
        
        # Кнопки для статуса (как у телефона)
        self.status_buttons_layout = QHBoxLayout()
        self.status_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.status_buttons_layout.setSpacing(10)
        self.status_buttons_layout.addStretch()
        
        self.cancel_status_button = QPushButton(tr("cancel"))
        self.cancel_status_button.setFixedHeight(36)
        self.cancel_status_button.setFixedWidth(100)
        self.cancel_status_button.clicked.connect(self.cancel_edit_status)
        self.cancel_status_button.setStyleSheet("""
            QPushButton {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                color: #8E8AAE;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
            }
        """)
        self.cancel_status_button.hide()
        self.status_buttons_layout.addWidget(self.cancel_status_button)
        
        self.save_status_button = QPushButton(tr("save"))
        self.save_status_button.setFixedHeight(36)
        self.save_status_button.setFixedWidth(100)
        self.save_status_button.clicked.connect(self.save_status_dialog)
        self.save_status_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C4DFF,
                    stop:1 #6F4EF6);
                border: none;
                border-radius: 12px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5A3FE0,
                    stop:1 #5A3FE0);
            }
        """)
        self.save_status_button.hide()
        self.status_buttons_layout.addWidget(self.save_status_button)
        
        beruf_container.addLayout(self.status_buttons_layout)
        additional_card_layout.addLayout(beruf_container)
        
        # О себе
        about_me_label = QLabel(tr("qualities"))
        about_me_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        about_me_label.setStyleSheet("color: #4B3F72; background: transparent;")
        additional_card_layout.addWidget(about_me_label)
        
        self.about_me_input = QTextEdit()
        self.about_me_input.setFont(QFont("Inter", 14))
        self.about_me_input.setPlaceholderText(tr("qualities_placeholder"))
        self.about_me_input.setMinimumHeight(70)
        self.about_me_input.setMaximumHeight(100)
        self.about_me_input.setStyleSheet("""
            QTextEdit {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
                line-height: 1.6;
            }
            QTextEdit:focus {
                background-color: #FFFFFF;
            }
            QTextEdit:hover {
                background-color: #FFFFFF;
            }
        """)
        additional_card_layout.addWidget(self.about_me_input)
        
        # Виджет уровня немецкого языка
        german_level_label = QLabel(tr("german_level"))
        german_level_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        german_level_label.setStyleSheet("color: #4B3F72; background: transparent;")
        additional_card_layout.addWidget(german_level_label)
        
        # Улучшенный виджет выбора уровня языка с иконками
        self.german_level_combo = QComboBox()
        levels = [
            ("A1", tr("german_level_a1"), "#FF9F43"),  # Оранжевый для A1
            ("A2", tr("german_level_a2"), "#FFA94D"),  # Светло-оранжевый для A2
            ("B1", tr("german_level_b1"), "#6C4DFF"),  # Фиолетовый для B1
            ("B2", tr("german_level_b2"), "#8B5CF6"),  # Светло-фиолетовый для B2
            ("C1", tr("german_level_c1"), "#A78BFA"),  # Лавандовый для C1
            ("C2", tr("german_level_c2"), "#C4B5FD")   # Светло-лавандовый для C2
        ]
        for level_code, level_text, color in levels:
            self.german_level_combo.addItem(f"{level_code} - {level_text.split(' - ')[-1] if ' - ' in level_text else level_text}")
        
        # Устанавливаем B1 по умолчанию
        default_index = next((i for i, (code, _, _) in enumerate(levels) if code == "B1"), 2)
        self.german_level_combo.setCurrentIndex(default_index)
        
        self.german_level_combo.setMinimumHeight(50)
        self.german_level_combo.setStyleSheet("""
            QComboBox {
                background-color: #FAF9FE;
                border: none;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QComboBox:focus {
                background-color: #FFFFFF;
            }
            QComboBox:hover {
                background-color: #FFFFFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 40px;
                background: transparent;
                border-radius: 0 12px 12px 0;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #6C4DFF;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: none;
                border-radius: 12px;
                selection-background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(108, 77, 255, 0.15),
                    stop:1 rgba(108, 77, 255, 0.25));
                selection-color: #6C4DFF;
                padding: 6px;
                margin: 4px;
            }
            QComboBox QAbstractItemView::item {
                padding: 10px 14px;
                border-radius: 8px;
                margin: 2px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(108, 77, 255, 0.1);
            }
        """)
        additional_card_layout.addWidget(self.german_level_combo)
        
        container_layout.addWidget(additional_card)
        
        # Дата регистрации (внизу)
        reg_date_card = QFrame()
        reg_date_card.setObjectName("regDateCard")
        
        reg_shadow = QGraphicsDropShadowEffect()
        reg_shadow.setBlurRadius(15)
        reg_shadow.setXOffset(0)
        reg_shadow.setYOffset(3)
        reg_shadow.setColor(QColor(108, 77, 255, 12))
        reg_date_card.setGraphicsEffect(reg_shadow)
        
        reg_date_card.setStyleSheet("""
            QFrame#regDateCard {
                background: #FAF9FE;
                border: none;
                border-radius: 16px;
            }
        """)
        reg_date_card_layout = QVBoxLayout()
        reg_date_card_layout.setContentsMargins(22, 18, 22, 18)
        reg_date_card_layout.setSpacing(10)
        reg_date_card.setLayout(reg_date_card_layout)
        
        reg_date_label = QLabel(tr('registration_date'))
        reg_date_label.setFont(QFont("Inter", 11, QFont.Weight.Normal))  # Уменьшен размер и вес
        reg_date_label.setStyleSheet("color: #B5A9C2; background: transparent;")  # Менее контрастный цвет
        reg_date_card_layout.addWidget(reg_date_label)
        
        self.reg_date_display = QLabel("—")
        self.reg_date_display.setFont(QFont("Inter", 12, QFont.Weight.Normal))  # Уменьшен размер и вес
        self.reg_date_display.setStyleSheet("color: #9A8FA8; background: transparent;")  # Менее контрастный цвет
        reg_date_card_layout.addWidget(self.reg_date_display)
        container_layout.addWidget(reg_date_card)
        
        # Кнопка сохранения
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 16, 0, 0)
        buttons_layout.addStretch()
        
        save_btn = QPushButton(tr("save"))
        save_btn.setFixedHeight(52)
        save_btn.setFixedWidth(180)
        save_btn.clicked.connect(self.save_data)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        save_btn_shadow = QGraphicsDropShadowEffect()
        save_btn_shadow.setBlurRadius(15)
        save_btn_shadow.setXOffset(0)
        save_btn_shadow.setYOffset(4)
        save_btn_shadow.setColor(QColor(108, 77, 255, 30))
        save_btn.setGraphicsEffect(save_btn_shadow)
        
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6C4DFF,
                    stop:1 #6F4EF6);
                border: none;
                border-radius: 14px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 15px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: #5A3FE0;
            }
            QPushButton:pressed {
                background: #5A3FE0;
            }
        """)
        buttons_layout.addWidget(save_btn)
        container_layout.addLayout(buttons_layout)
        
        # Сохраняем ссылку на scroll_widget для доступа
        self.scroll_widget = scroll_widget
        
        main_layout.addWidget(container)
        self.container = container
    
    def eventFilter(self, obj, event):
        """Обработчик событий для закрытия при клике вне рамки"""
        if event.type() == QEvent.Type.MouseButtonPress:
            if hasattr(self, 'container'):
                # Проверяем, был ли клик вне контейнера
                if obj != self.container and not self.container.geometry().contains(event.globalPosition().toPoint()):
                    # Преобразуем глобальную позицию в локальную для контейнера
                    container_global_pos = self.container.mapToGlobal(QPoint(0, 0))
                    container_rect = QRect(container_global_pos, self.container.size())
                    if not container_rect.contains(event.globalPosition().toPoint()):
                        self.close()
                        return True
        return super().eventFilter(obj, event)
    
    def setup_animation(self):
        """Настраивает анимацию появления"""
        self.setWindowOpacity(0.0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def showEvent(self, event):
        """Показывает диалог с анимацией"""
        super().showEvent(event)
        self.animation.start()
        # Загружаем данные
        self.load_data()
        # Устанавливаем обработчик кликов вне рамки
        QApplication.instance().installEventFilter(self)
    
    def load_data(self):
        """Загружает данные пользователя"""
        user_info = get_user_info()
        if user_info:
            if len(user_info) >= 2:
                self.first_name_input.setText(user_info[0] if user_info[0] else '')
                self.last_name_input.setText(user_info[1] if user_info[1] else '')
            if len(user_info) >= 3:
                self._real_phone_number = user_info[2] if user_info[2] else ''
            else:
                self._real_phone_number = ''
            if len(user_info) >= 4:
                # Загружаем дату регистрации
                created_at = user_info[3]
                if hasattr(self, 'reg_date_display'):
                    if created_at:
                        try:
                            if isinstance(created_at, str):
                                date_obj = datetime.strptime(created_at.split()[0], '%Y-%m-%d')
                            else:
                                date_obj = created_at
                            formatted_date = date_obj.strftime('%d.%m.%Y')
                            self.reg_date_display.setText(formatted_date)
                        except:
                            self.reg_date_display.setText(str(created_at) if created_at else "—")
                    else:
                        self.reg_date_display.setText("—")
            if len(user_info) >= 7:
                status_text = user_info[6] if user_info[6] else ''
                self.status_label.setText(status_text if status_text else tr("no_data"))
            else:
                self.status_label.setText(tr("no_data"))
        
        # Обновляем отображение телефона (скрытый по умолчанию)
        self.update_phone_display_dialog()
        
        # Загружаем "о себе" и уровень языка из базы данных
        username = get_current_username()
        if username:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT about_me, german_level FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result:
                    if result[0]:
                        self.about_me_input.setPlainText(result[0])
                    if result[1] and hasattr(self, 'german_level_combo'):
                        # Устанавливаем уровень языка
                        level_text = result[1]
                        index = self.german_level_combo.findText(level_text)
                        if index >= 0:
                            self.german_level_combo.setCurrentIndex(index)
            except:
                try:
                    # Если колонки german_level еще нет, просто загружаем about_me
                    cursor.execute('SELECT about_me FROM auth_users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        self.about_me_input.setPlainText(result[0])
                except:
                    pass
            conn.close()
    
    def update_phone_display_dialog(self):
        """Обновляет отображение номера телефона в диалоге"""
        if hasattr(self, 'phone_input_dialog') and hasattr(self, 'show_phone_button'):
            phone_number = getattr(self, '_real_phone_number', '')
            
            if phone_number:
                if self.phone_is_visible:
                    self.phone_input_dialog.setText(phone_number)
                    self.show_phone_button.setText(tr("hide_phone"))
                else:
                    if len(phone_number) >= 2:
                        masked = "*" * (len(phone_number) - 2) + phone_number[-2:]
                    else:
                        masked = "*" * len(phone_number)
                    self.phone_input_dialog.setText(masked)
                    self.show_phone_button.setText(tr("show_phone"))
            else:
                self.phone_input_dialog.setText("")
                self.show_phone_button.setText(tr("show_phone"))
    
    def toggle_phone_visibility_dialog(self):
        """Переключает видимость номера телефона в диалоге"""
        self.phone_is_visible = not self.phone_is_visible
        self.update_phone_display_dialog()
    
    def edit_phone_dialog(self):
        """Включает режим редактирования телефона в диалоге"""
        if not hasattr(self, '_real_phone_number'):
            user_info = get_user_info()
            if user_info and len(user_info) >= 3:
                self._real_phone_number = user_info[2] if user_info[2] else ''
            else:
                self._real_phone_number = ''
        
        self.phone_input_dialog.setText(self._real_phone_number)
        self.phone_input_dialog.setReadOnly(False)
        self.phone_input_dialog.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 2px solid #A78BFA;
                border-radius: 12px;
                padding: 20px 24px;
                color: #2D1B3D;
                font-size: 18px;
                min-height: 32px;
            }
        """)
        # Подключаем валидацию при вводе
        self.phone_input_dialog.textChanged.connect(self.validate_phone_input)
        self.show_phone_button.hide()
        self.save_phone_button.show()
        self.cancel_phone_button.show()
        self.phone_input_dialog.setFocus()
        self.phone_input_dialog.selectAll()
    
    def validate_phone_input(self):
        """Валидирует телефон при вводе"""
        phone_number = self.phone_input_dialog.text().strip()
        if not phone_number:
            self.phone_error_label.hide()
            return
        
        is_valid, error_msg = self.validate_german_phone(phone_number)
        if not is_valid:
            self.phone_error_label.setText(error_msg)
            self.phone_error_label.show()
            self.phone_input_dialog.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 2px solid #FF6B6B;
                    border-radius: 12px;
                    padding: 20px 24px;
                    color: #2D1B3D;
                    font-size: 18px;
                    min-height: 32px;
                }
            """)
        else:
            self.phone_error_label.hide()
            self.phone_input_dialog.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 2px solid #34D399;
                    border-radius: 12px;
                    padding: 20px 24px;
                    color: #2D1B3D;
                    font-size: 18px;
                    min-height: 32px;
                }
            """)
    
    def cancel_edit_phone_dialog(self):
        """Отменяет редактирование телефона в диалоге"""
        if not hasattr(self, '_real_phone_number'):
            user_info = get_user_info()
            if user_info and len(user_info) >= 3:
                self._real_phone_number = user_info[2] if user_info[2] else ''
            else:
                self._real_phone_number = ''
        
        self.phone_input_dialog.clearFocus()
        self.phone_input_dialog.setReadOnly(True)
        self.phone_input_dialog.setMinimumHeight(44)  # Возвращаем исходный размер
        # Отключаем валидацию при отмене
        try:
            self.phone_input_dialog.textChanged.disconnect(self.validate_phone_input)
        except:
            pass
        self.phone_error_label.hide()
        self.phone_input_dialog.setStyleSheet("""
            QLineEdit {
                background-color: #FAF9FE;
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 1.5px solid #6C4DFF;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border-color: #E4DEFF;
            }
        """)
        self.save_phone_button.hide()
        self.cancel_phone_button.hide()
        self.show_phone_button.show()
        self.phone_is_visible = False
        self.update_phone_display_dialog()
    
    def save_phone_dialog(self):
        """Сохраняет изменения телефона в диалоге с валидацией"""
        phone_number = self.phone_input_dialog.text().strip()
        
        # Валидация немецкого формата
        is_valid, error_msg = self.validate_german_phone(phone_number)
        if not is_valid:
            self.phone_error_label.setText(error_msg)
            self.phone_error_label.show()
            self.phone_input_dialog.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 2px solid #FF6B6B;
                    border-radius: 12px;
                    padding: 20px 24px;
                    color: #2D1B3D;
                    font-size: 18px;
                    min-height: 32px;
                }
            """)
            return
        
        # Скрываем ошибку, если валидация прошла
        self.phone_error_label.hide()
        self._real_phone_number = phone_number
        
        user_info = get_user_info()
        if user_info:
            first_name = user_info[0] if len(user_info) > 0 else ""
            last_name = user_info[1] if len(user_info) > 1 else ""
            save_user_info(first_name, last_name, phone_number, preserve_registration_date=True)
            
            username = user_info[5] if len(user_info) > 5 else None
            if username:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('UPDATE auth_users SET phone_number = ? WHERE username = ?', (phone_number, username))
                conn.commit()
                conn.close()
        
        self.phone_input_dialog.clearFocus()
        self.phone_input_dialog.setReadOnly(True)
        self.phone_input_dialog.setMinimumHeight(44)  # Возвращаем исходный размер
        self.phone_input_dialog.setStyleSheet("""
            QLineEdit {
                background-color: #FAF9FE;
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 1.5px solid #6C4DFF;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border-color: #E4DEFF;
            }
        """)
        self.save_phone_button.hide()
        self.cancel_phone_button.hide()
        self.show_phone_button.show()
        self.phone_is_visible = False
        self.update_phone_display_dialog()
    
    def edit_status(self):
        """Включает режим редактирования статуса"""
        self.is_editing_status = True
        current_status = self.status_label.text()
        if current_status == tr("no_data"):
            current_status = ""
        self.status_input.setText(current_status)
        self.status_label.hide()
        self.status_input.show()
        self.save_status_button.show()
        self.cancel_status_button.show()
        self.status_input.setFocus()
        self.status_input.selectAll()
    
    def cancel_edit_status(self):
        """Отменяет редактирование статуса"""
        user_info = get_user_info()
        status_text = ""
        if user_info and len(user_info) >= 7:
            status_text = user_info[6] if user_info[6] else ''
        
        self.status_label.setText(status_text if status_text else tr("no_data"))
        self.status_input.hide()
        self.status_label.show()
        self.save_status_button.hide()
        self.cancel_status_button.hide()
        self.is_editing_status = False
    
    def save_status_dialog(self):
        """Сохраняет изменения статуса"""
        current_status = self.status_input.text().strip()
        self.status_label.setText(current_status if current_status else tr("no_data"))
        self.status_input.hide()
        self.status_label.show()
        self.save_status_button.hide()
        self.cancel_status_button.hide()
        self.is_editing_status = False
    
    def save_data(self):
        """Сохраняет данные пользователя"""
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        phone_number = getattr(self, '_real_phone_number', '')
        current_status = self.status_input.text().strip() if self.is_editing_status else self.status_label.text()
        if current_status == tr("no_data"):
            current_status = ""
        about_me = self.about_me_input.toPlainText().strip()
        
        # Сохраняем имя и фамилию
        save_user_info(first_name, last_name, phone_number, preserve_registration_date=True)
        
        # Progress bar удален из интерфейса
        
        # Сохраняем статус и "о себе"
        username = get_current_username()
        if username:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            try:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN current_status TEXT DEFAULT ""')
                conn.commit()
            except:
                pass
            try:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN about_me TEXT DEFAULT ""')
                conn.commit()
            except:
                pass
            # Сохраняем уровень немецкого языка
            german_level = self.german_level_combo.currentText() if hasattr(self, 'german_level_combo') else "B1 - Средний"
            try:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN german_level TEXT DEFAULT "B1 - Средний"')
                conn.commit()
            except:
                pass
            cursor.execute('UPDATE auth_users SET current_status = ?, about_me = ?, german_level = ? WHERE username = ?', (current_status, about_me, german_level, username))
            conn.commit()
            conn.close()
            
            # Инвалидируем кеш
            global _profile_cache
            if username in _profile_cache:
                del _profile_cache[username]
        
        self.close()
        if self.parent():
            self.parent().load_user_info()
    
    
    def closeEvent(self, event):
        """Закрывает диалог с анимацией"""
        self.animation.setDirection(QPropertyAnimation.Direction.Backward)
        self.animation.finished.connect(self.hide)
        self.animation.start()
        event.ignore()
        # Удаляем обработчик
        QApplication.instance().removeEventFilter(self)

# Импортируем StatisticsPage из отдельного файла
from pages.statistics_page import StatisticsPage
# FriendsPage импортируем лениво, чтобы избежать циклической зависимости


class EmailApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bewerbungs Studio")
        self.setFixedSize(1700, 950)  # Увеличена ширина и высота для лучшего первого впечатления
        
        # Загружаем язык пользователя при входе
        global CURRENT_LANGUAGE, _username_cache, _username_cache_time
        
        # КРИТИЧНО: Принудительно обновляем кеш username из БД, чтобы избежать использования старого кеша
        # Это гарантирует, что при быстром переключении аккаунтов мы получим правильный username
        _username_cache = None
        _username_cache_time = None
        
        username = get_current_username()
        if username:
            # Сохраняем username в объекте для использования в других компонентах
            self.current_username = username
            self.username = username  # Дублируем для совместимости
            
            # Оптимизированное получение языка с использованием DatabaseConnection
            try:
                with DatabaseConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT language FROM auth_users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result and result[0] and result[0] in ['ru', 'de', 'en']:
                        CURRENT_LANGUAGE = result[0] if isinstance(result, tuple) else result['language']
            except:
                pass
            
            # КРИТИЧНО: Перед установкой статуса онлайн для нового пользователя
            # переводим все остальные аккаунты в офлайн, чтобы избежать ситуации,
            # когда несколько аккаунтов показываются как онлайн одновременно
            try:
                with DatabaseConnection() as conn:
                    cursor = conn.cursor()
                    # Переводим все аккаунты в офлайн, кроме текущего
                    cursor.execute('''
                        UPDATE auth_users 
                        SET is_online = 0, last_seen = CURRENT_TIMESTAMP
                        WHERE username != ?
                    ''', (username,))
                    conn.commit()
            except Exception as e:
                print(f"Ошибка при переводе других аккаунтов в офлайн: {e}")
            
            # Устанавливаем статус онлайн для текущего пользователя
            set_user_online(username, True)
        else:
            # Если не получили через get_current_username, пробуем другие способы
            self.current_username = None
            self.username = None
        
        # КРИТИЧНО: Очищаем кеш профиля ПЕРЕД созданием страниц, чтобы они загрузили свежие данные
        global _profile_cache, _history_cache, _stats_cache
        _profile_cache.clear()
        _history_cache = None
        _stats_cache = None
        
        # Ленивая загрузка для производительности
        self.setup_ui()
        # Применяем тему сразу (синхронно) чтобы избежать конфликтов и мерцания
        self.apply_theme()
        QTimer.singleShot(50, self.update_datetime)
        # Фон теперь устанавливается через градиент в setup_ui, load_background больше не нужен
    
    def create_monochrome_icon(self, icon_type, color="#a78bfa", size=20):
        """Создает монохромную иконку для кнопок навигации"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Используем более светлый цвет (как у логотипа)
        icon_color = QColor(color)
        pen = QPen(icon_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        brush = QBrush(icon_color)
        painter.setBrush(brush)
        
        # Улучшенные монохромные иконки (симметричные и равномерные)
        if icon_type == "profile":
            # Иконка профиля (голова и плечи, фиолетовые, голова от туловища отдалена)
            center_x = size // 2
            # Голова (симметрично по центру, отдалена от туловища)
            head_size = 7
            painter.drawEllipse(center_x - head_size // 2, 4, head_size, head_size)
            # Плечи/туловище (залито, симметрично)
            from PyQt6.QtCore import QRectF
            painter.drawArc(QRectF(center_x - 7, 14, 14, 7), 0, 180 * 16)  # Туловище залито
        elif icon_type == "friends":
            # Иконка друзей (два силуэта с залитым туловищем, симметрично, голова от туловища отдалена)
            from PyQt6.QtCore import QRectF
            center_x = size // 2
            head_size = 5
            # Первый силуэт (сзади, левее) - симметрично
            first_head_x = center_x - 6
            painter.drawEllipse(first_head_x - head_size // 2, 3, head_size, head_size)
            # Туловище (залито, фиолетовое)
            painter.drawArc(QRectF(first_head_x - 6, 12, 12, 7), 0, 180 * 16)
            # Второй силуэт (впереди, правее - перекрывает первый) - симметрично
            second_head_x = center_x + 2
            painter.drawEllipse(second_head_x - head_size // 2, 4, head_size, head_size)
            # Туловище (залито, фиолетовое)
            painter.drawArc(QRectF(second_head_x - 6, 13, 12, 7), 0, 180 * 16)
        elif icon_type == "statistics":
            # Иконка статистики (3 тонкие палочки, больше, отдалены: маленькая, самая большая, средняя)
            center_x = size // 2
            painter.setBrush(brush)  # С заливкой для палочек
            base_y = size - 2  # Базовая линия внизу
            bar_width = 2  # Тонкие палочки (меньше жирности)
            spacing = 4  # Расстояние между палочками
            
            # Маленькая палочка (первая, слева) - симметрично
            bar1_x = center_x - 5 - spacing
            painter.drawRect(bar1_x, base_y - 5, bar_width, 5)
            # Самая большая палочка (вторая, по центру) - симметрично
            bar2_x = center_x - bar_width // 2
            painter.drawRect(bar2_x, base_y - 12, bar_width, 12)
            # Средняя палочка (третья, справа) - симметрично
            bar3_x = center_x + 5
            painter.drawRect(bar3_x, base_y - 7, bar_width, 7)
        elif icon_type == "bewerbung":
            # Иконка письма (конверт с линиями текста внутри - более подходящая)
            center_x = size // 2
            # Конверт (прямоугольник с клапаном) - симметрично
            envelope_width = 12
            envelope_height = 9
            envelope_x = center_x - envelope_width // 2
            envelope_y = 6
            
            # Основной конверт (залит)
            painter.drawRect(envelope_x, envelope_y + 3, envelope_width, envelope_height)
            # Треугольный клапан конверта (симметрично)
            path = QPainterPath()
            path.moveTo(envelope_x, envelope_y + 3)
            path.lineTo(center_x, envelope_y + 7)  # Центр клапана
            path.lineTo(envelope_x + envelope_width, envelope_y + 3)
            path.closeSubpath()
            painter.drawPath(path)
            # Три горизонтальные линии текста внутри конверта
            text_pen = QPen(icon_color)
            text_pen.setWidth(1)
            painter.setPen(text_pen)
            painter.setBrush(QBrush())  # Без заливки для линий
            painter.drawLine(envelope_x + 2, envelope_y + 10, envelope_x + 10, envelope_y + 10)   # Первая строка
            painter.drawLine(envelope_x + 2, envelope_y + 12, envelope_x + 9, envelope_y + 12)   # Вторая строка
            painter.drawLine(envelope_x + 2, envelope_y + 14, envelope_x + 7, envelope_y + 14)   # Третья строка (короче)
        elif icon_type == "history":
            # Иконка истории (часы меньше, стрелки больше и белее)
            center_x, center_y = size // 2, size // 2
            # Заполненный круг часов (меньше размер)
            clock_radius = (size - 8) // 2 - 2  # Меньше на 2 пикселя
            painter.setBrush(brush)  # С заливкой цветом иконки
            painter.setPen(pen)
            painter.drawEllipse(center_x - clock_radius, center_y - clock_radius, 
                               clock_radius * 2, clock_radius * 2)
            # Стрелки часов белые и больше
            white_color = QColor("white")
            white_pen = QPen(white_color)
            white_pen.setWidth(2)
            white_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(white_pen)
            painter.setBrush(QBrush())  # Без заливки для стрелок
            # Минутная стрелка (длинная, больше - указывает вверх)
            painter.drawLine(center_x, center_y, center_x, center_y - 6)
            # Часовая стрелка (короткая, больше - указывает вправо)
            painter.drawLine(center_x, center_y, center_x + 4, center_y)
            # Центральная точка белая (используем int для координат)
            painter.setBrush(QBrush(white_color))
            painter.drawEllipse(center_x - 1, center_y - 1, 3, 3)
        elif icon_type == "achievements":
            # Иконка достижений (звезда шире, внутренняя область шире)
            center_x, center_y = size // 2, size // 2
            outer_radius = 9  # Внешний радиус для ширины звезды
            inner_radius = 3.5  # Увеличен внутренний радиус для более широкой внутренней области
            import math
            points = []
            for i in range(10):
                angle = math.pi / 2 - (i * 2 * math.pi / 10)
                if i % 2 == 0:
                    radius = outer_radius
                else:
                    radius = inner_radius
                x = center_x + radius * math.cos(angle)
                y = center_y - radius * math.sin(angle)
                points.append(QPoint(int(x), int(y)))
            painter.drawPolygon(points)
        elif icon_type == "settings":
            # Иконка настроек (шестеренка/зубчатое колесо)
            painter.setBrush(QBrush())  # Без заливки
            center_x, center_y = size // 2, size // 2
            import math
            # Рисуем зубчатое колесо
            outer_radius = 8
            inner_radius = 4
            num_teeth = 8
            path = QPainterPath()
            for i in range(num_teeth * 2):
                angle = i * math.pi / num_teeth
                if i % 2 == 0:
                    radius = outer_radius
                else:
                    radius = inner_radius
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)
            # Центральный круг
            painter.drawEllipse(center_x - 2, center_y - 2, 4, 4)
        
        painter.end()
        return QIcon(pixmap)
    
    def setup_ui(self):
        """Создает интерфейс с боковой панелью"""
        # Главный контейнер с фоном
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Устанавливаем градиентный фон через базовую палитру
        colors = get_app_colors()
        
        main_widget.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
            }}
        """)
        
        # Фоновое изображение больше не используется - используем градиент
        # Оставляем background_label для совместимости, но скрываем его
        self.background_label = QLabel(main_widget)
        self.background_label.setObjectName("backgroundLabel")
        self.background_label.hide()  # Скрываем, так как используем градиент
        
        # Затемнение в области боковой панели
        self.sidebar_overlay = QLabel(main_widget)
        self.sidebar_overlay.setObjectName("sidebarOverlay")
        self.sidebar_overlay.lower()
        
        # Layout для фонового изображения
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)
        
        # Боковая панель
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        # Комфортная ширина под секции и отступы
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout()
        # Рекомендованные внутренние отступы и ритм
        sidebar_layout.setContentsMargins(18, 24, 18, 18)
        sidebar_layout.setSpacing(6)
        sidebar.setLayout(sidebar_layout)
        
        # Включаем отслеживание мыши для сайдбара
        sidebar.setMouseTracking(True)
        
        # Верхний блок "бренд/профиль"
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        
        # Логотип с буквой "B"
        logo_label = QLabel()
        logo_label.setFixedSize(40, 40)
        logo_label.setStyleSheet("""
            QLabel {
                background-color: #a78bfa;
                border-radius: 10px;
                color: white;
                font-size: 22px;
                font-weight: bold;
            }
        """)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setText("B")
        header_layout.addWidget(logo_label)
        
        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(2)
        
        # Название "Berwik"
        app_name_label = QLabel("Berwik")
        app_name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        app_name_label.setStyleSheet("color: #4B3F72; background: transparent;")
        title_block.addWidget(app_name_label)
        
        # Небольшая подпись (опционально, можно оставить пустой)
        app_subtitle_label = QLabel("")
        app_subtitle_label.setObjectName("sidebarSubtitleLabel")
        app_subtitle_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        app_subtitle_label.setStyleSheet("color: rgba(75, 63, 114, 0.7); background: transparent;")
        app_subtitle_label.setFixedHeight(12)
        title_block.addWidget(app_subtitle_label)
        
        header_layout.addLayout(title_block)
        
        sidebar_layout.addLayout(header_layout)
        
        # Разделитель после верхнего блока
        header_divider = QFrame()
        header_divider.setObjectName("sidebarDivider")
        header_divider.setFrameShape(QFrame.Shape.HLine)
        header_divider.setFrameShadow(QFrame.Shadow.Plain)
        header_divider.setFixedHeight(1)
        header_divider.setStyleSheet("QFrame#sidebarDivider { background-color: rgba(75, 63, 114, 0.12); border: none; }")
        sidebar_layout.addSpacing(14)
        sidebar_layout.addWidget(header_divider)
        sidebar_layout.addSpacing(10)
        
        # Кнопки навигации с монохромными иконками
        # Структура меню:
        # ОСНОВНОЕ: Профиль, Друзья, Письма
        # АКТИВНОСТЬ: Статистика, Достижения, История
        icon_size_val = 22
        text_size = 16
        item_height = 46
        
        def _add_section_label(text: str):
            label = QLabel(text)
            label.setObjectName("sidebarSectionLabel")
            label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            label.setStyleSheet(
                "QLabel#sidebarSectionLabel {"
                "  color: rgba(75, 63, 114, 0.65);"
                "  letter-spacing: 0.8px;"
                "  background: transparent;"
                "  padding: 8px 6px 4px 6px;"
                "}"
            )
            sidebar_layout.addWidget(label)
        
        _add_section_label("ОСНОВНОЕ")
        
        self.profile_button = QPushButton(tr('profile'))
        self.profile_button.setObjectName("navButton")
        self.profile_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.profile_button.setFixedHeight(item_height)
        self.profile_button.setIcon(self.create_monochrome_icon("profile", color="#a78bfa", size=icon_size_val))
        self.profile_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.profile_button.clicked.connect(lambda: self._optimized_switch_page(0))
        self.profile_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.profile_button)
        
        self.friends_button = QPushButton(tr('friends'))
        self.friends_button.setObjectName("navButton")
        self.friends_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.friends_button.setFixedHeight(item_height)
        # Иконка друзей - два силуэта (поменяли местами с достижениями)
        self.friends_button.setIcon(self.create_monochrome_icon("friends", color="#a78bfa", size=icon_size_val))
        self.friends_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.friends_button.clicked.connect(lambda: self._optimized_switch_page(4))
        self.friends_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.friends_button)
        
        # Бейдж для "Друзья" (по умолчанию скрыт)
        self.friends_badge = QLabel(self.friends_button)
        self.friends_badge.setObjectName("navBadge")
        self.friends_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.friends_badge.setFixedHeight(18)
        self.friends_badge.setMinimumWidth(18)
        self.friends_badge.setStyleSheet(
            "QLabel#navBadge {"
            "  background-color: #7C3AED;"
            "  color: white;"
            "  border-radius: 9px;"
            "  padding: 0 6px;"
            "  font-size: 10px;"
            "  font-weight: 700;"
            "}"
        )
        self.friends_badge.hide()
        self.friends_button.installEventFilter(self)
        
        # Письма (Bewerbung) - теперь первым после расстояния
        self.bewerbung_button = QPushButton(tr('bewerbung'))
        self.bewerbung_button.setObjectName("navButton")
        self.bewerbung_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.bewerbung_button.setFixedHeight(item_height)
        self.bewerbung_button.setIcon(self.create_monochrome_icon("bewerbung", color="#a78bfa", size=icon_size_val))
        self.bewerbung_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.bewerbung_button.clicked.connect(lambda: self._optimized_switch_page(1))
        self.bewerbung_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.bewerbung_button)
        
        sidebar_layout.addSpacing(10)
        _add_section_label("АКТИВНОСТЬ")
        
        self.statistics_button = QPushButton(tr('statistics'))
        self.statistics_button.setObjectName("navButton")
        self.statistics_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.statistics_button.setFixedHeight(item_height)
        self.statistics_button.setIcon(self.create_monochrome_icon("statistics", color="#a78bfa", size=icon_size_val))
        self.statistics_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.statistics_button.clicked.connect(lambda: self._optimized_switch_page(3))
        self.statistics_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.statistics_button)
        
        self.achievements_button = QPushButton(tr('achievements'))
        self.achievements_button.setObjectName("navButton")
        self.achievements_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.achievements_button.setFixedHeight(item_height)
        # Иконка достижений - звезда (поменяли местами с друзьями)
        self.achievements_button.setIcon(self.create_monochrome_icon("achievements", color="#a78bfa", size=icon_size_val))
        self.achievements_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.achievements_button.clicked.connect(lambda: self._optimized_switch_page(5))
        self.achievements_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.achievements_button)
        
        # История - теперь последняя перед настройками
        self.history_button = QPushButton(tr('history'))
        self.history_button.setObjectName("navButton")
        self.history_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.history_button.setFixedHeight(item_height)
        self.history_button.setIcon(self.create_monochrome_icon("history", color="#a78bfa", size=icon_size_val))
        self.history_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.history_button.clicked.connect(lambda: self._optimized_switch_page(2))
        self.history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.history_button)
        
        self.nav_buttons = [
            self.profile_button,
            self.friends_button,
            self.bewerbung_button,  # Письма - поменяли местами с историей
            self.statistics_button,
            self.achievements_button,
            self.history_button,  # История - поменяли местами с письмами
        ]
        
        # Добавляем blur эффекты к кнопкам навигации (по умолчанию без blur)
        self.nav_buttons_blur_effects = []
        for button in self.nav_buttons:
            button_blur = QGraphicsBlurEffect()
            button_blur.setBlurRadius(0)  # Без blur по умолчанию
            button.setGraphicsEffect(button_blur)
            self.nav_buttons_blur_effects.append(button_blur)
        
        # Настройки - одна кнопка внизу (прозрачная)
        sidebar_layout.addStretch()  # Отступ перед настройками
        
        # Визуальный разделитель перед footer-элементом
        footer_divider = QFrame()
        footer_divider.setObjectName("sidebarFooterDivider")
        footer_divider.setFrameShape(QFrame.Shape.HLine)
        footer_divider.setFrameShadow(QFrame.Shadow.Plain)
        footer_divider.setFixedHeight(1)
        footer_divider.setStyleSheet("QFrame#sidebarFooterDivider { background-color: rgba(75, 63, 114, 0.12); border: none; }")
        sidebar_layout.addWidget(footer_divider)
        sidebar_layout.addSpacing(10)
        
        self.settings_button = QPushButton(tr('settings'))
        self.settings_button.setObjectName("footerNavButton")
        self.settings_button.setFont(QFont("Segoe UI", text_size, QFont.Weight.Normal))
        self.settings_button.setFixedHeight(item_height)
        self.settings_button.setIcon(self.create_monochrome_icon("settings", color="#a78bfa", size=icon_size_val))
        self.settings_button.setIconSize(QPixmap(icon_size_val, icon_size_val).size())
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setStyleSheet("""
            QPushButton#footerNavButton {
                background-color: transparent;
                color: #4B3F72;
                border: none;
                border-radius: 14px;
                text-align: left;
                padding: 12px 14px;
                font-size: 15px;
                font-weight: 500;
                outline: none;
            }
            QPushButton#footerNavButton:hover {
                background-color: rgba(124, 58, 237, 0.08);
                color: #4B3F72;
            }
            QPushButton#footerNavButton:pressed {
                background-color: rgba(124, 58, 237, 0.12);
            }
            QPushButton#footerNavButton:focus {
                border: 1px solid rgba(124, 58, 237, 0.35);
            }
            QPushButton#footerNavButton::icon {
                margin-right: 12px;
                width: 22px;
                height: 22px;
            }
        """)
        sidebar_layout.addWidget(self.settings_button)
        
        # Кнопка выхода убрана - теперь она в настройках
        
        
        # Сохраняем ссылку на sidebar для плашки стримера
        self.sidebar_widget = sidebar
        
        main_layout.addWidget(sidebar)
        
        # Контейнер для центральной области
        content_container = QWidget()
        content_container.setObjectName("contentContainer")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_container.setLayout(content_layout)
        
        # Центральная область с переключаемыми страницами (поверх фона)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stackedWidget")
        content_layout.addWidget(self.stacked_widget)
        
        # Страница профиля (первая) - импортируем из отдельного файла
        from pages.profile_page import ProfilePage
        self.profile_page = ProfilePage(main_window=self)
        self.stacked_widget.addWidget(self.profile_page)
        
        # Страница Bewerbung (импортируем из отдельного файла)
        from pages.bewerbung_page import BewerbungPage
        self.bewerbung_page = BewerbungPage(main_window=self)
        self.stacked_widget.addWidget(self.bewerbung_page)
        
        # Страница History (импортируем из отдельного файла)
        from pages.history_page import HistoryPage as HistoryPageImported
        self.history_page = HistoryPageImported(main_window=self)
        self.stacked_widget.addWidget(self.history_page)
        
        # Страница Statistics
        self.statistics_page = StatisticsPage(main_window=self)
        self.stacked_widget.addWidget(self.statistics_page)
        
        # Страница Friends
        # Ленивый импорт FriendsPage для избежания циклической зависимости
        from pages.friends_page import FriendsPage
        self.friends_page = FriendsPage(main_window=self)
        self.stacked_widget.addWidget(self.friends_page)
        
        # Страница Achievements
        from pages.achievements_page import AchievementsPage
        self.achievements_page = AchievementsPage(main_window=self)
        self.stacked_widget.addWidget(self.achievements_page)
        
        # Настройки теперь отдельное окно, не добавляем в stacked_widget
        self.settings_dialog = None
        
        # Связываем обновление статистики с отправкой письма
        if hasattr(self.bewerbung_page, 'on_email_sent'):
            # Сохраняем оригинальный обработчик
            original_handler = self.bewerbung_page.on_email_sent
            def wrapped_handler(success, message):
                original_handler(success, message)
                if success:
                    # Обновляем статистику после успешной отправки
                    QTimer.singleShot(500, self.statistics_page.refresh_statistics)
                    # Обновляем достижения после успешной отправки
                    if hasattr(self, 'achievements_page'):
                        QTimer.singleShot(600, self.achievements_page.refresh)
            self.bewerbung_page.on_email_sent = wrapped_handler
        
        # По умолчанию открываем Профиль (индекс 0)
        self.stacked_widget.setCurrentIndex(0)
        
        # КРИТИЧНО: Принудительно обновляем все страницы СРАЗУ после создания, чтобы они загрузили данные нового пользователя
        # Это гарантирует, что при быстром переключении аккаунтов страницы получат правильные данные
        # Делаем это ПОСЛЕ установки текущей страницы, но ДО активации
        self._refresh_all_pages_after_login()
        
        # Активируем страницу по умолчанию (это загрузит данные профиля)
        if hasattr(self, 'profile_page'):
            self.profile_page.activate()
        
        # Убеждаемся, что blur эффекты применены к кнопкам перед обновлением стилей
        if hasattr(self, 'nav_buttons_blur_effects'):
            for i, blur_effect in enumerate(self.nav_buttons_blur_effects):
                if self.nav_buttons[i].graphicsEffect() != blur_effect:
                    self.nav_buttons[i].setGraphicsEffect(blur_effect)
                    blur_effect.setBlurRadius(1)
        
        self.update_button_styles(0)
        
        main_layout.addWidget(content_container, 1)
        
        # Сохраняем ссылку на главный виджет
        self.main_widget = main_widget
        self.sidebar_widget = sidebar
        self.sidebar_normal_width = 280
        self.sidebar_expanded_width = 300
        
        # Blur эффект для страниц отключен для производительности
        # self.pages_blur_effect = QGraphicsBlurEffect()
        # self.pages_blur_effect.setBlurRadius(0)
        # self.stacked_widget.setGraphicsEffect(self.pages_blur_effect)
        
        # Анимация для выдвижения сайдбара
        self.sidebar_animation = QPropertyAnimation(sidebar, b"minimumWidth")
        self.sidebar_animation.setDuration(200)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Устанавливаем event filter после создания всех атрибутов
        sidebar.installEventFilter(self)
        
        # Первичное позиционирование бейджей
        self._position_nav_badges()
    
    def _add_button_animation(self, button):
        """Добавляет плавную анимацию для кнопки"""
        # Добавляем transition эффект через стили
        current_style = button.styleSheet()
        if "transition" not in current_style.lower():
            button.setStyleSheet(current_style + """
            QPushButton {
                    transition: all 0.2s ease;
            }
        """)
        
    def toggle_language(self):
        """Переключает язык интерфейса"""
        global CURRENT_LANGUAGE
        # Переключаем язык через новую систему локализации
        current = get_current_language()
        new_lang = 'de' if current == 'ru' else 'ru'
        set_language(new_lang, save_to_db=True)
        CURRENT_LANGUAGE = new_lang
        self.language_button.setText('DE' if CURRENT_LANGUAGE == 'de' else 'RU')
        self.update_ui_texts()
        
        # Сохраняем язык в БД для текущего пользователя
        username = get_current_username()
        if username:
            # Получаем данные пользователя для сохранения языка
            user_info = get_user_info(username)
            if user_info:
                first_name = user_info[0] if len(user_info) > 0 else ''
                last_name = user_info[1] if len(user_info) > 1 else ''
                phone_number = user_info[2] if len(user_info) > 2 else ''
                avatar_path = user_info[4] if len(user_info) > 4 else None
                # Получаем пароль из remembered_users для сохранения
                machine_id = get_machine_id()
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT password FROM remembered_users WHERE machine_id = ?', (machine_id,))
                result = cursor.fetchone()
                conn.close()
                if result:
                    password = result[0]
                    save_auth_user(username, password, first_name, last_name, phone_number, avatar_path, language=CURRENT_LANGUAGE)
    
    def _refresh_all_pages_after_login(self):
        """Принудительно обновляет все страницы после входа в новый аккаунт"""
        # КРИТИЧНО: Очищаем кеш профиля перед обновлением, чтобы страницы загрузили свежие данные
        # (Кеш уже очищен в __init__, но очищаем еще раз для надежности)
        global _profile_cache, _history_cache, _stats_cache
        _profile_cache.clear()
        _history_cache = None
        _stats_cache = None
        
        # КРИТИЧНО: Принудительно обновляем username кеш, чтобы страницы получили правильный username
        global _username_cache, _username_cache_time
        _username_cache = None
        _username_cache_time = None
        # Вызываем get_current_username() чтобы обновить кеш из БД
        current_username = get_current_username()
        
        # Обновляем профиль (загружает данные для текущего пользователя)
        if hasattr(self, 'profile_page'):
            self.profile_page.load_user_info()
        # Обновляем друзей (загружает друзей текущего пользователя)
        if hasattr(self, 'friends_page'):
            self.friends_page.load_current_tab()
        # Обновляем историю (загружает историю текущего пользователя)
        if hasattr(self, 'history_page'):
            if hasattr(self.history_page, 'refresh_history'):
                self.history_page.refresh_history()
        # Обновляем статистику (загружает статистику текущего пользователя)
        if hasattr(self, 'statistics_page'):
            if hasattr(self.statistics_page, 'refresh_statistics'):
                self.statistics_page.refresh_statistics()
    
    def update_ui_texts(self):
        """Обновляет тексты интерфейса при смене языка"""
        self.profile_button.setText(tr('profile'))
        self.statistics_button.setText(tr('statistics'))
        self.friends_button.setText(tr('friends'))
        self.bewerbung_button.setText(tr('bewerbung'))
        self.history_button.setText(tr('history'))
        if hasattr(self, 'settings_button'):
            self.settings_button.setText(tr('settings'))
        # Кнопка выхода убрана - теперь она в настройках
        # Обновляем тексты на страницах
        if hasattr(self, 'profile_page'):
            self.profile_page.load_user_info()
        if hasattr(self, 'bewerbung_page'):
            self.bewerbung_page.update_texts()
        if hasattr(self, 'history_page'):
            self.history_page.update_texts()
        if hasattr(self, 'statistics_page'):
            self.statistics_page.update_texts()
        if hasattr(self, 'friends_page'):
            self.friends_page.update_texts()
    
    def update_all_texts(self):
        """Обновляет все тексты в приложении после смены языка"""
        self.update_ui_texts()
        # Обновляем язык кнопки
        lang_text = {'de': 'DE', 'ru': 'RU', 'en': 'EN'}.get(CURRENT_LANGUAGE, 'DE')
        self.language_button.setText(lang_text)
    
    def logout(self):
        """Выход из аккаунта с виджетом подтверждения"""
        from settings import LogoutConfirmDialog
        from PyQt6.QtWidgets import QDialog
        dialog = LogoutConfirmDialog(self, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._execute_logout()
    
    def _execute_logout(self):
        """Выполняет выход из аккаунта - ОПТИМИЗИРОВАНО"""
        
        # Устанавливаем статус офлайн
        username = get_current_username()
        if username:
            set_user_online(username, False)
        
        # Очищаем кеши при выходе для освобождения памяти
        global _profile_cache, _history_cache, _stats_cache, _username_cache, _username_cache_time
        _profile_cache.clear()
        _history_cache = None
        _stats_cache = None
        # КРИТИЧНО: Очищаем кеш username ПЕРЕД очисткой БД, чтобы избежать race condition
        _username_cache = None
        _username_cache_time = None
        
        # Очищаем запись из БД для текущего компьютера, чтобы при следующем входе не было конфликта
        # Это не влияет на "Запомнить меня", так как данные сохраняются в другом месте
        try:
            machine_id = get_machine_id()
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM remembered_users WHERE machine_id = ?', (machine_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка при очистке remembered_users: {e}")
        
        # Сохраняем данные текущего пользователя перед выходом
        try:
            user_info = get_user_info()
            if user_info and len(user_info) >= 6:
                username = user_info[5]
                if username:
                    # Получаем актуальные данные из user
                    current_user = get_user_info()
                    if current_user:
                        first_name = current_user[0] if current_user[0] else ''
                        last_name = current_user[1] if current_user[1] else ''
                        phone_number = current_user[2] if len(current_user) > 2 and current_user[2] else ''
                        avatar_path = current_user[4] if len(current_user) > 4 and current_user[4] else None
                        
                        # Обновляем данные в auth_users
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE auth_users 
                            SET first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?
                            WHERE username = ?
                        ''', (first_name, last_name, phone_number, avatar_path, username))
                        conn.commit()
                        conn.close()
        except Exception as e:
            print(f"Ошибка при сохранении данных пользователя: {e}")
        
        # НЕ очищаем сохраненные данные пользователя (чтобы "Запомнить меня" работала)
        # clear_remembered_user() - убрано
        
        # Закрываем главное окно
        self.close()
        
        # Открываем окно входа
        login_screen = LoginScreen()
        login_screen.show()
    
    def show_settings(self):
        """Открывает диалог настроек"""
        try:
            # Закрываем предыдущий диалог, если он открыт
            if hasattr(self, 'settings_dialog') and self.settings_dialog:
                try:
                    if self.settings_dialog.isVisible():
                        self.settings_dialog.close()
                    self.settings_dialog.deleteLater()
                except:
                    pass
                self.settings_dialog = None
            
            # Создаем новый диалог (ленивый импорт для избежания циклического импорта)
            try:
                from settings import SettingsDialog
            except ImportError as import_error:
                # Ошибка импорта - не выводим в консоль, чтобы не открывать окно Python
                raise
            
            self.settings_dialog = SettingsDialog(main_window=self, parent=self)
            
            # Добавляем эффект блюра к главному окну (если возможно)
            if hasattr(self, 'central_widget'):
                blur_effect = QGraphicsBlurEffect()
                blur_effect.setBlurRadius(8)
                self.central_widget.setGraphicsEffect(blur_effect)
            
            # Центрируем окно относительно главного окна
            parent_geometry = self.geometry()
            dialog_geometry = self.settings_dialog.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2
            self.settings_dialog.move(x, y)
            
            # Показываем диалог (анимация внутри showEvent)
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            self.settings_dialog.setFocus()
        except Exception as e:
            # Ошибка открытия настроек - не выводим в консоль
            pass
    
    def update_user_name_display(self):
        """Обновляет отображение имени пользователя"""
        user_info = get_user_info()
        if user_info and len(user_info) >= 2:
            first_name, last_name = user_info[0], user_info[1]
            display_name = f"{first_name} {last_name}"
            
            # Обновляем в сайдбаре
            for widget in self.sidebar_widget.findChildren(QLabel):
                if widget.objectName() == "userNameLabel":
                    widget.setText(display_name)
                    break
    
    
    def _optimized_switch_page(self, index):
        """Оптимизированное переключение страниц с ленивой загрузкой"""
        # Используем QTimer для отложенного выполнения, чтобы не блокировать UI
        QTimer.singleShot(0, lambda: self.switch_page(index))
    
    def switch_page(self, index):
        """Переключает страницы - ОПТИМИЗИРОВАНО"""
        current_index = self.stacked_widget.currentIndex()
        
        # Деактивируем только текущую страницу (оптимизация)
        pages = [
            (0, 'profile_page'),
            (1, 'bewerbung_page'),
            (2, 'history_page'),
            (3, 'statistics_page'),
            (4, 'friends_page'),
            (5, 'achievements_page'),
        ]
        
        # Деактивируем только текущую активную страницу
        for page_index, page_attr in pages:
            if page_index == current_index and hasattr(self, page_attr):
                page = getattr(self, page_attr)
                if hasattr(page, 'deactivate'):
                    page.deactivate()
                break
        
        # Активируем выбранную страницу
        for page_index, page_attr in pages:
            if page_index == index and hasattr(self, page_attr):
                page = getattr(self, page_attr)
                if hasattr(page, 'activate'):
                    page.activate()
                break
        
        # Настройки теперь отдельное окно, не нужно активировать
        
        self.stacked_widget.setCurrentIndex(index)
        self.update_button_styles(index)
    
    def switch_to_history_and_highlight(self, sent_at):
        """Переключается на страницу History и выделяет запись по дате"""
        self.switch_page(2)
        # Выделяем строку после небольшой задержки, чтобы таблица успела загрузиться
        QTimer.singleShot(150, lambda: self.history_page.highlight_last_entry(sent_at))
    
    def update_button_styles(self, active_index):
        """Обновляет стили кнопок навигации в современном стиле"""
        # Маппинг индексов страниц к индексам кнопок в nav_buttons
        # Порядок страниц: 0=profile, 1=bewerbung, 2=history, 3=statistics, 4=friends, 5=achievements
        # Порядок кнопок: 0=profile, 1=friends, 2=bewerbung, 3=statistics, 4=achievements, 5=history
        page_to_button_index = {
            0: 0,  # profile -> кнопка 0
            1: 2,  # bewerbung -> кнопка 2 (исправлено)
            2: 5,  # history -> кнопка 5 (исправлено)
            3: 3,  # statistics -> кнопка 3
            4: 1,  # friends -> кнопка 1
            5: 4,  # achievements -> кнопка 4
        }
        
        # Маппинг кнопок к типам иконок (порядок: profile, friends, bewerbung, statistics, achievements, history)
        # Порядок изменен: письма и история поменялись местами
        icon_types = ["profile", "friends", "bewerbung", "statistics", "achievements", "history"]
        
        # Определяем индекс активной кнопки
        active_button_index = page_to_button_index.get(active_index, -1)
        
        for i, button in enumerate(self.nav_buttons):
            # Сохраняем blur эффект перед изменением стилей
            current_blur = button.graphicsEffect()
            blur_radius = current_blur.blurRadius() if current_blur else 2
            
            if i == active_button_index:
                # Активная кнопка: pill + accent bar
                icon_color = "#5B21B6"
                if i < len(icon_types):
                    button.setIcon(self.create_monochrome_icon(icon_types[i], icon_color, size=22))
                    button.setIconSize(QPixmap(22, 22).size())
                button.setStyleSheet(
                    """
                    QPushButton#navButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(124, 58, 237, 0.22),
                            stop:1 rgba(167, 139, 250, 0.16));
                        color: #4B3F72;
                        border-radius: 14px;
                        border: none;
                        border-left: 4px solid #7C3AED; /* вертикальный индикатор */
                        text-align: left;
                        padding: 12px 14px;
                        font-size: 16px;
                        font-weight: 600;
                        outline: none;
                    }
                    QPushButton#navButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(124, 58, 237, 0.26),
                            stop:1 rgba(167, 139, 250, 0.20));
                        outline: none;
                        border: none;
                        border-left: 4px solid #7C3AED;
                    }
                    QPushButton#navButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(124, 58, 237, 0.30),
                            stop:1 rgba(167, 139, 250, 0.24));
                        outline: none;
                        border: none;
                        border-left: 4px solid #7C3AED;
                    }
                    QPushButton#navButton:focus {
                        border: 1px solid rgba(124, 58, 237, 0.35);
                        border-left: 4px solid #7C3AED;
                    }
                    QPushButton#navButton::icon {
                        margin-right: 12px;
                        width: 22px;
                        height: 22px;
                    }
                """
                )
            else:
                # Неактивная кнопка (чуть темнее для читаемости)
                icon_color = "#7C3AED"
                if i < len(icon_types):
                    button.setIcon(self.create_monochrome_icon(icon_types[i], icon_color, size=22))
                    button.setIconSize(QPixmap(22, 22).size())
                button.setStyleSheet(
                    """
                    QPushButton#navButton {
                        background-color: transparent;
                        color: #4B3F72;
                        border: none;
                        border-radius: 14px;
                        text-align: left;
                        padding: 12px 14px;
                        font-size: 16px;
                        font-weight: 500;
                        outline: none;
                    }
                    QPushButton#navButton:hover {
                        background-color: rgba(124, 58, 237, 0.08);
                        color: #4B3F72;
                        outline: none;
                        border: none;
                    }
                    QPushButton#navButton:pressed {
                        background-color: rgba(124, 58, 237, 0.12);
                        outline: none;
                        border: none;
                    }
                    QPushButton#navButton:focus {
                        border: 1px solid rgba(124, 58, 237, 0.30);
                    }
                    QPushButton#navButton::icon {
                        margin-right: 12px;
                        width: 22px;
                        height: 22px;
                    }
                """
                )
            
            # Восстанавливаем blur эффект после изменения стилей
            if current_blur:
                current_blur.setBlurRadius(blur_radius)
            elif hasattr(self, 'nav_buttons_blur_effects') and i < len(self.nav_buttons_blur_effects):
                # Если эффект был потерян, восстанавливаем его
                if not button.graphicsEffect():
                    button.setGraphicsEffect(self.nav_buttons_blur_effects[i])
                    self.nav_buttons_blur_effects[i].setBlurRadius(blur_radius)
    
    def apply_theme(self):
        """Применяет базовую палитру и обновляет виджеты."""
        colors = get_app_colors()
        central = self.centralWidget()
        if central:
            central.setStyleSheet(f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {colors['main_window_bg_start']},
                        stop:0.4 {colors['main_window_bg_mid']},
                        stop:1 {colors['main_window_bg_end']});
                }}
            """)

        if hasattr(self, 'stacked_widget') and self.stacked_widget:
            self.update_button_styles(self.stacked_widget.currentIndex())

        if hasattr(self, 'stacked_widget'):
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if widget:
                    widget.update()
    
    
    def load_background(self):
        """Метод больше не используется - фон теперь устанавливается через градиент"""
        # Фон теперь устанавливается через градиент в setup_ui
        pass
    
    def update_background_size(self):
        """Метод больше не используется - фон теперь устанавливается через градиент"""
        # Фон теперь устанавливается через градиент, этот метод больше не нужен
        pass
                    
    
    def eventFilter(self, obj, event):
        """Обработчик событий для интерактивного сайдбара"""
        # Переукладка бейджа при изменении размера кнопки "Друзья"
        if hasattr(self, 'friends_button') and obj == getattr(self, 'friends_button', None):
            if event.type() == QEvent.Type.Resize:
                self._position_nav_badges()

        if hasattr(self, 'sidebar_widget') and obj == self.sidebar_widget:
            if event.type() == QEvent.Type.Enter:
                self.on_sidebar_enter()
            elif event.type() == QEvent.Type.Leave:
                self.on_sidebar_leave()
        return super().eventFilter(obj, event)

    def _position_nav_badges(self):
        """Позиционирует бейджи справа внутри пунктов меню."""
        if hasattr(self, 'friends_badge') and getattr(self, 'friends_badge', None) and hasattr(self, 'friends_button'):
            badge = self.friends_badge
            button = self.friends_button
            right_padding = 12
            x = max(0, button.width() - badge.width() - right_padding)
            y = max(0, (button.height() - badge.height()) // 2)
            badge.move(x, y)

    def set_friends_badge(self, count):
        """Показывает/скрывает бейдж на пункте 'Друзья'."""
        if not hasattr(self, 'friends_badge') or self.friends_badge is None:
            return
        if count is None or count <= 0:
            self.friends_badge.hide()
            return
        text = str(count) if int(count) < 100 else "99+"
        self.friends_badge.setText(text)
        self.friends_badge.adjustSize()
        # Минимальная "пилюля"
        self.friends_badge.setFixedHeight(18)
        self.friends_badge.setMinimumWidth(18)
        self.friends_badge.show()
        self._position_nav_badges()
    
    def on_sidebar_enter(self):
        """Обработчик наведения мыши на сайдбар - отключен"""
        # Анимация отключена
        pass
    
    def on_sidebar_leave(self):
        """Обработчик ухода мыши с сайдбара - отключен"""
        # Анимация отключена
        pass
    
    
    def resizeEvent(self, event):
        """Обработчик изменения размера окна"""
        super().resizeEvent(event)
        # Градиентный фон автоматически масштабируется, дополнительных действий не требуется
    
    def update_datetime(self):
        """Обновляет отображение даты и времени"""
        now = datetime.now()
        # Красивый формат: "Понедельник, 15 января" и время "14:30"
        weekday_keys = [
            "weekday_monday", "weekday_tuesday", "weekday_wednesday", "weekday_thursday",
            "weekday_friday", "weekday_saturday", "weekday_sunday"
        ]
        month_genitive_keys = [
            "month_january_genitive", "month_february_genitive", "month_march_genitive",
            "month_april_genitive", "month_may_genitive", "month_june_genitive",
            "month_july_genitive", "month_august_genitive", "month_september_genitive",
            "month_october_genitive", "month_november_genitive", "month_december_genitive"
        ]
        
        weekday = tr(weekday_keys[now.weekday()])
        day = now.day
        month = tr(month_genitive_keys[now.month - 1])
        time_str = now.strftime("%H:%M")
        
        # Форматируем красиво: день недели на первой строке, дата и время на второй
        datetime_text = f"{weekday}\n{day} {month}  {time_str}"
        # Обновляем datetime_label только если он существует (удален из сайдбара)
        if hasattr(self, 'datetime_label') and self.datetime_label is not None:
            self.datetime_label.setText(datetime_text)
        
        # Обновление каждую секунду для реального времени
        QTimer.singleShot(1000, self.update_datetime)


def cleanup_resources():
    """Очищает ресурсы при завершении приложения"""
    # Закрываем соединение с БД
    DatabaseConnection.close_connection()
    
    # Очищаем кеши
    global _profile_cache, _history_cache, _stats_cache, _username_cache, _table_schema_cache
    _profile_cache.clear()
    _history_cache = None
    _stats_cache = None
    _username_cache = None
    _table_schema_cache.clear()


def main():
    # Инициализируем базу данных
    init_database()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Регистрируем очистку ресурсов при выходе
    atexit.register(cleanup_resources)
    
    # Создаем экран входа
    login = LoginScreen()
    login.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
