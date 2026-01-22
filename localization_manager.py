"""
Новый менеджер локализации с JSON поддержкой
- Использует locales/ директорию с JSON файлами
- base_keys.json как единственный источник истины для ключей
- Автоматическое обнаружение языков
- Валидация синхронизации ключей
- Fallback на немецкий (de) по умолчанию
- Загрузка языка пользователя из БД при логине
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Callable, List, Set
from collections import OrderedDict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('localization.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('LocalizationManager')


def get_DB_FILE():
    """Получает путь к файлу базы данных, избегая циклических импортов"""
    try:
        from email_app import DB_FILE
        return DB_FILE
    except ImportError:
        return 'email_app.db'


class LocalizationManager:
    """
    Менеджер локализации с JSON поддержкой
    
    Особенности:
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
        
        logger.info(f"LocalizationManager initialized. Current language: {self._current_language}")
        logger.info(f"Available languages: {list(self._available_languages.keys())}")
    
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
                    logger.info(f"Loaded meta.json: {len(self._available_languages)} languages")
            except Exception as e:
                logger.error(f"Error loading meta.json: {e}")
                self._available_languages = {}
    
    def _load_base_keys(self):
        """Загружает base_keys.json - единственный источник истины для ключей"""
        base_keys_path = self.locales_dir / "base_keys.json"
        if not base_keys_path.exists():
            logger.error(f"base_keys.json not found at {base_keys_path}")
            return
        
        try:
            with open(base_keys_path, 'r', encoding='utf-8') as f:
                base_keys = json.load(f)
                self._base_keys = set(base_keys.keys())
                logger.info(f"Loaded base_keys.json: {len(self._base_keys)} keys")
        except Exception as e:
            logger.error(f"Error loading base_keys.json: {e}")
    
    def _auto_discover_languages(self):
        """Автоматически обнаруживает доступные языки из папки locales/"""
        if not self.locales_dir.exists():
            logger.error(f"Locales directory not found: {self.locales_dir}")
            return
        
        # Ищем все JSON файлы кроме base_keys.json и meta.json
        json_files = list(self.locales_dir.glob("*.json"))
        json_files = [f for f in json_files if f.name not in ['base_keys.json', 'meta.json']]
        
        for json_file in json_files:
            lang_code = json_file.stem  # Имя файла без расширения
            if lang_code in ['base_keys', 'meta']:
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    self._translations[lang_code] = translations
                    logger.info(f"Auto-discovered language: {lang_code} ({len(translations)} keys)")
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
    
    def _validate_all_languages(self):
        """Валидирует, что все языки содержат те же ключи, что и base_keys.json"""
        if not self._base_keys:
            logger.warning("No base keys loaded, skipping validation")
            return
        
        for lang_code, translations in self._translations.items():
            lang_keys = set(translations.keys())
            missing = self._base_keys - lang_keys
            extra = lang_keys - self._base_keys
            
            if missing:
                logger.warning(f"Language {lang_code} is missing {len(missing)} keys: {list(missing)[:10]}")
            if extra:
                logger.warning(f"Language {lang_code} has {len(extra)} extra keys: {list(extra)[:10]}")
            
            if not missing and not extra:
                logger.info(f"Language {lang_code} is fully synchronized with base_keys.json")
    
    def get_current_language(self) -> str:
        """Возвращает текущий язык"""
        return self._current_language
    
    def set_language(self, language_code: str, save_to_db: bool = True):
        """
        Устанавливает язык приложения
        
        Args:
            language_code: Код языка ('ru', 'de', 'en', и т.д.)
            save_to_db: Сохранять ли язык в базу данных
        """
        if language_code not in self._translations:
            logger.warning(f"Language {language_code} not found, using default: {self.DEFAULT_LANGUAGE}")
            language_code = self.DEFAULT_LANGUAGE
        
        if self._current_language != language_code:
            old_lang = self._current_language
            self._current_language = language_code
            logger.info(f"Language changed from {old_lang} to {language_code}")
            
            # Сохраняем в базу данных, если нужно
            if save_to_db:
                self._save_language_to_db(language_code)
            
            # Уведомляем все зарегистрированные callbacks
            self._notify_callbacks()
    
    def _save_language_to_db(self, language_code: str):
        """Сохраняет язык в базу данных"""
        try:
            from email_app import get_current_username
            
            username = get_current_username()
            if not username:
                return
            
            conn = sqlite3.connect(get_DB_FILE())
            cursor = conn.cursor()
            
            # Проверяем наличие колонки language
            try:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN language TEXT DEFAULT "de"')
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Колонка уже существует
            
            # Обновляем язык пользователя
            cursor.execute(
                'UPDATE auth_users SET language = ? WHERE username = ?',
                (language_code, username)
            )
            conn.commit()
            conn.close()
            
            logger.info(f"Language {language_code} saved to database for user {username}")
            
        except Exception as e:
            logger.error(f"Error saving language to database: {e}")
    
    def load_language_from_db(self, username: Optional[str] = None) -> Optional[str]:
        """
        Загружает язык пользователя из базы данных
        
        Args:
            username: Имя пользователя (если None, пытается получить текущего)
        
        Returns:
            Код языка или None если не найден
        """
        try:
            if username is None:
                from email_app import get_current_username
                username = get_current_username()
            
            if not username:
                return None
            
            conn = sqlite3.connect(get_DB_FILE())
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT language FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    lang = result[0]
                    if lang in self._translations:
                        logger.info(f"Loaded language {lang} from database for user {username}")
                        return lang
            except sqlite3.OperationalError:
                pass  # Колонка не существует
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading language from database: {e}")
        
        return None
    
    def t(self, key: str, **kwargs) -> str:
        """
        Получает перевод для ключа (главная функция)
        
        Args:
            key: Ключ перевода
            **kwargs: Параметры для форматирования строки
        
        Returns:
            Переведенная строка или ключ, если перевод не найден
        """
        # Пытаемся получить перевод для текущего языка
        translation = self._get_translation(key, self._current_language)
        
        # Если не найден, используем fallback на немецкий
        if translation is None or translation == "":
            translation = self._get_translation(key, self.FALLBACK_LANGUAGE)
            if translation is None or translation == "":
                # Если и fallback не помог, логируем и возвращаем ключ
                logger.warning(f"Translation key '{key}' not found in {self._current_language} or {self.FALLBACK_LANGUAGE}")
                return key
        
        # Форматирование строки с параметрами
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format parameter {e} in key '{key}'")
            except Exception as e:
                logger.warning(f"Error formatting key '{key}': {e}")
        
        return translation
    
    def _get_translation(self, key: str, language_code: str) -> Optional[str]:
        """Получает перевод для ключа и языка"""
        translations = self._translations.get(language_code, {})
        return translations.get(key)
    
    def register_callback(self, callback: Callable[[], None]):
        """
        Регистрирует callback для обновления UI при смене языка
        
        Args:
            callback: Функция без параметров, которая обновит UI
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.debug(f"Registered language change callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
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
                logger.error(f"Error in language change callback: {e}")
    
    def get_available_languages(self) -> Dict[str, Dict]:
        """
        Возвращает словарь доступных языков с метаданными
        
        Returns:
            Dict с ключами кодов языков и значениями с метаданными
        """
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
        """
        Валидирует файл языка на соответствие base_keys.json
        
        Returns:
            Dict с результатами валидации
        """
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


# Глобальный экземпляр менеджера
_manager: Optional[LocalizationManager] = None


def get_localization_manager() -> LocalizationManager:
    """Возвращает глобальный экземпляр менеджера локализации"""
    global _manager
    if _manager is None:
        _manager = LocalizationManager()
    return _manager


def t(key: str, **kwargs) -> str:
    """
    Глобальная функция для получения перевода (главная функция)
    
    Args:
        key: Ключ перевода
        **kwargs: Параметры для форматирования строки
    
    Returns:
        Переведенная строка
    """
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


# Для обратной совместимости - tr() теперь алиас для t()
def tr(key: str, **kwargs) -> str:
    """Алиас для t() для обратной совместимости"""
    return t(key, **kwargs)
