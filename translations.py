"""
Модуль локализации для Bewerbung Studio
Использует JSON файлы из папки locales/
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List

class TranslationManager:
    """Менеджер переводов приложения"""
    
    def __init__(self, locales_dir: str = "locales"):
        self.locales_dir = Path(locales_dir)
        self.current_language = "de"  # Язык по умолчанию
        self.translations: Dict[str, Dict[str, str]] = {}
        self.meta: Dict = {}
        
        # Загружаем переводы при инициализации
        self._load_all_translations()
    
    def _load_all_translations(self):
        """Загружает все доступные переводы"""
        if not self.locales_dir.exists():
            print(f"⚠️ Папка {self.locales_dir} не найдена!")
            return
        
        # Загружаем meta.json
        meta_path = self.locales_dir / "meta.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                self.meta = json.load(f)
                self.current_language = self.meta.get('default_language', 'de')
        
        # Загружаем все языковые файлы
        for lang_file in self.locales_dir.glob("*.json"):
            if lang_file.name == "meta.json" or lang_file.name == "base_keys.json":
                continue
            
            lang_code = lang_file.stem  # de, en, ru
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
                print(f"✅ Загружен язык: {lang_code}")
            except Exception as e:
                print(f"❌ Ошибка загрузки {lang_file}: {e}")
    
    def get(self, key: str, **kwargs) -> str:
        """
        Получает перевод по ключу
        
        Args:
            key: Ключ перевода (например, 'login_title')
            **kwargs: Параметры для форматирования строки
        
        Returns:
            Переведенная строка или ключ, если перевод не найден
        """
        # Получаем перевод для текущего языка
        translation = self.translations.get(self.current_language, {}).get(key)
        
        # Если не найден, пробуем fallback язык
        if translation is None:
            fallback_lang = self.meta.get('fallback_language', 'de')
            translation = self.translations.get(fallback_lang, {}).get(key)
        
        # Если всё равно не найден, возвращаем ключ
        if translation is None:
            print(f"⚠️ Перевод не найден: {key} (язык: {self.current_language})")
            return key
        
        # Форматируем строку если есть параметры
        try:
            if kwargs:
                return translation.format(**kwargs)
            return translation
        except KeyError as e:
            print(f"⚠️ Ошибка форматирования перевода {key}: {e}")
            return translation
    
    def set_language(self, lang_code: str) -> bool:
        """
        Устанавливает текущий язык
        
        Args:
            lang_code: Код языка (de, en, ru)
        
        Returns:
            True если язык установлен успешно
        """
        if lang_code in self.translations:
            self.current_language = lang_code
            print(f"✅ Язык изменен на: {lang_code}")
            return True
        else:
            print(f"❌ Язык {lang_code} не найден!")
            return False
    
    def get_current_language(self) -> str:
        """Возвращает код текущего языка"""
        return self.current_language
    
    def get_available_languages(self) -> List[Dict[str, str]]:
        """
        Возвращает список доступных языков
        
        Returns:
            Список словарей с информацией о языках
        """
        languages = []
        meta_languages = self.meta.get('languages', {})
        
        for lang_code in self.translations.keys():
            lang_info = meta_languages.get(lang_code, {})
            languages.append({
                'code': lang_code,
                'name': lang_info.get('name', lang_code.upper()),
                'native_name': lang_info.get('native_name', lang_code.upper()),
                'flag': lang_info.get('flag', '🌐')
            })
        
        return languages
    
    def reload(self):
        """Перезагружает все переводы (полезно для разработки)"""
        self.translations.clear()
        self._load_all_translations()


# Создаем глобальный экземпляр менеджера
_manager = TranslationManager()


# Публичные функции для удобства использования
def t(key: str, **kwargs) -> str:
    """
    Получает перевод по ключу (короткая версия)
    
    Примеры:
        t('login_title')
        t('email_sent_success', email='test@example.com')
    """
    return _manager.get(key, **kwargs)


def tr(key: str, **kwargs) -> str:
    """
    Получает перевод по ключу (альтернативная версия)
    
    Примеры:
        tr('login_title')
        tr('error_occurred', error='Connection failed')
    """
    return _manager.get(key, **kwargs)


def set_language(lang_code: str) -> bool:
    """
    Устанавливает текущий язык приложения
    
    Args:
        lang_code: Код языка (de, en, ru)
    
    Returns:
        True если язык установлен успешно
    """
    return _manager.set_language(lang_code)


def get_current_language() -> str:
    """Возвращает код текущего языка"""
    return _manager.get_current_language()


def get_available_languages() -> List[Dict[str, str]]:
    """Возвращает список доступных языков"""
    return _manager.get_available_languages()


def reload_translations():
    """Перезагружает все переводы"""
    _manager.reload()


# Примеры использования
if __name__ == "__main__":
    print("=== Тест модуля локализации ===\n")
    
    # Показываем доступные языки
    print("Доступные языки:")
    for lang in get_available_languages():
        print(f"  {lang['flag']} {lang['code']}: {lang['native_name']} ({lang['name']})")
    
    print(f"\nТекущий язык: {get_current_language()}\n")
    
    # Тестируем переводы на разных языках
    for lang_code in ['de', 'en', 'ru']:
        set_language(lang_code)
        print(f"\n--- {lang_code.upper()} ---")
        print(f"Заголовок входа: {t('login_title')}")
        print(f"Кнопка входа: {t('login_button')}")
        print(f"С параметром: {t('email_sent_success', email='test@example.com')}")
    
    # Тест несуществующего ключа
    print(f"\nНесуществующий ключ: {t('nonexistent_key')}")