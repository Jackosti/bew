"""
Менеджер тем приложения
Управляет темами оформления и их применением
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtGui import QColor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('ThemeManager')


def get_DB_FILE():
    """Получает путь к файлу базы данных, избегая циклических импортов"""
    try:
        from email_app import DB_FILE
        return DB_FILE
    except ImportError:
        return 'email_app.db'


class ThemeManager:
    """
    Менеджер тем приложения
    
    Особенности:
    - Загрузка тем из конфигурации
    - Сохранение выбранной темы
    - Применение тем к приложению
    """
    
    DEFAULT_THEME = 'default'
    
    def __init__(self):
        """Инициализация менеджера тем"""
        self.current_theme_id = self.DEFAULT_THEME
        self.themes = self._load_themes()
        self._load_current_theme()
    
    def _load_themes(self) -> Dict[str, Dict[str, Any]]:
        """Загружает доступные темы"""
        themes = {
            'default': self._get_default_theme(),
            'dark': self._get_dark_theme(),
            'light': self._get_light_theme(),
        }
        return themes
    
    def _get_default_theme(self) -> Dict[str, Any]:
        """Возвращает стандартную тему (светло-лиловая)"""
        return {
            'id': 'default',
            'name': 'Lavender',
            'colors': {
                # Фоны главного окна (градиент) - светло-лиловый
                'main_window_bg_start': '#F5F0FF',
                'main_window_bg_mid': '#F5F0FF',
                'main_window_bg_end': '#F5F0FF',
                
                # Фоны компонентов
                'sidebar_bg': '#E8D5FF',
                'content_bg': '#F5F0FF',
                'input_bg': '#F5F0FF',
                'card_bg': '#FFFFFF',
                
                # Текст
                'text_primary': '#3D2B5D',
                'text_secondary': '#5E548A',
                'text_tertiary': '#7D6B8F',
                'input_text': '#3D2B5D',
                'button_primary_text': '#FFFFFF',
                'button_secondary_text': '#5E548A',
                'error_text': '#DC3545',
                
                # Границы и линии
                'card_border': '#D8C5F0',
                'input_border': '#C0A8E8',
                'input_border_focus': '#A78BFA',
                'border_color': '#D8C5F0',
                'border_light': '#E0CDF7',
                'separator_color': '#D8C5F0',
                
                # Кнопки
                'button_primary_bg': '#A78BFA',
                'button_primary_hover': '#B99DFF',
                'button_secondary_bg': '#E0CDF7',
                'button_secondary_hover': '#D8C5F0',
                
                # Специальные цвета (акценты)
                'accent': '#A78BFA',
                'accent_alt': '#B99DFF',
                'accent_color': '#A78BFA',
                'accent_hover': '#B99DFF',
                'error_bg': 'rgba(220, 53, 69, 0.1)',
                'success_color': '#28A745',
                'warning_color': '#FFC107',
                'info_color': '#17A2B8',
            }
        }
    
    def _get_dark_theme(self) -> Dict[str, Any]:
        """Возвращает темную тему"""
        return self._get_default_theme()
    
    def _get_light_theme(self) -> Dict[str, Any]:
        """Возвращает светлую тему"""
        return {
            'id': 'light',
            'name': 'Light',
            'colors': {
                # Фоны главного окна (градиент)
                'main_window_bg_start': '#f8f9fa',
                'main_window_bg_mid': '#ffffff',
                'main_window_bg_end': '#f8f9fa',
                
                # Фоны компонентов
                'sidebar_bg': '#e9ecef',
                'content_bg': '#ffffff',
                'input_bg': '#f8f9fa',
                'card_bg': '#ffffff',
                
                # Текст
                'text_primary': '#212529',
                'text_secondary': '#6c757d',
                'text_tertiary': '#adb5bd',
                'input_text': '#212529',
                'button_primary_text': '#ffffff',
                'button_secondary_text': '#6c757d',
                'error_text': '#dc3545',
                
                # Границы и линии
                'card_border': '#dee2e6',
                'input_border': '#dee2e6',
                'input_border_focus': '#a78bfa',
                'border_color': '#dee2e6',
                'border_light': '#e9ecef',
                'separator_color': '#dee2e6',
                
                # Кнопки
                'button_primary_bg': '#e94560',
                'button_primary_hover': '#ff6b7a',
                'button_secondary_bg': '#e9ecef',
                'button_secondary_hover': '#dee2e6',
                
                # Специальные цвета (акценты)
                'accent': '#a78bfa',
                'accent_alt': '#e94560',
                'accent_color': '#e94560',
                'accent_hover': '#ff6b7a',
                'error_bg': 'rgba(220, 53, 69, 0.1)',
                'success_color': '#28a745',
                'warning_color': '#ffc107',
                'info_color': '#17a2b8',
            }
        }
    
    def _load_current_theme(self):
        """Загружает текущую тему из БД"""
        try:
            import sqlite3
            db_file = get_DB_FILE()
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Получаем сохраненную тему
            cursor.execute('SELECT theme FROM app_preferences LIMIT 1')
            result = cursor.fetchone()
            
            if result and result[0]:
                theme_id = result[0]
                if theme_id in self.themes:
                    self.current_theme_id = theme_id
            
            conn.close()
        except Exception as e:
            logger.warning(f"Не удалось загрузить тему из БД: {e}")
            self.current_theme_id = self.DEFAULT_THEME
    
    def set_theme(self, theme_id: str) -> bool:
        """
        Устанавливает текущую тему
        
        Args:
            theme_id: ID темы
            
        Returns:
            True если тема установлена, False если тема не найдена
        """
        if theme_id not in self.themes:
            logger.warning(f"Тема '{theme_id}' не найдена")
            return False
        
        self.current_theme_id = theme_id
        
        # Сохраняем в БД
        try:
            import sqlite3
            db_file = get_DB_FILE()
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Убедимся, что таблица существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_preferences (
                    id INTEGER PRIMARY KEY,
                    theme TEXT DEFAULT 'default'
                )
            ''')
            
            # Проверяем, есть ли уже запись
            cursor.execute('SELECT COUNT(*) FROM app_preferences')
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.execute('INSERT INTO app_preferences (theme) VALUES (?)', (theme_id,))
            else:
                cursor.execute('UPDATE app_preferences SET theme = ?', (theme_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Не удалось сохранить тему в БД: {e}")
        
        return True
    
    def get_current_theme(self) -> Dict[str, Any]:
        """Возвращает текущую тему"""
        return self.themes.get(self.current_theme_id, self.themes[self.DEFAULT_THEME])
    
    def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает тему по ID"""
        return self.themes.get(theme_id)
    
    def apply_theme_to_app(self, app: Optional[QApplication] = None):
        """Применяет текущую тему к приложению"""
        if app is None:
            app = QApplication.instance()
        
        if app is None:
            logger.warning("QApplication не инициализировано")
            return
        
        theme = self.get_current_theme()
        colors = theme['colors']
        
        # Создаем глобальный stylesheet для приложения
        stylesheet = self._generate_stylesheet(colors)
        app.setStyleSheet(stylesheet)
    
    def _generate_stylesheet(self, colors: Dict[str, str]) -> str:
        """Генерирует stylesheet для темы"""
        return f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.5 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                color: {colors['text_primary']};
            }}
            
            QWidget {{
                background-color: {colors['content_bg']};
                color: {colors['text_primary']};
            }}
            
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
            }}
            
            QPushButton {{
                background-color: {colors['button_primary_bg']};
                color: {colors['button_primary_text']};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {colors['button_primary_hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {colors['button_primary_bg']};
                opacity: 0.9;
            }}
            
            QLineEdit {{
                background-color: {colors['input_bg']};
                color: {colors['input_text']};
                border: 1px solid {colors['input_border']};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QLineEdit:focus {{
                border: 2px solid {colors['input_border_focus']};
            }}
            
            QComboBox {{
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['input_border']};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
            }}
            
            QScrollBar:vertical {{
                background-color: {colors['sidebar_bg']};
                width: 8px;
                border: none;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {colors['border_light']};
                border-radius: 4px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['text_secondary']};
            }}
            
            QScrollBar:horizontal {{
                background-color: {colors['sidebar_bg']};
                height: 8px;
                border: none;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {colors['border_light']};
                border-radius: 4px;
                min-width: 20px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {colors['text_secondary']};
            }}
            
            QFrame {{
                background-color: {colors['content_bg']};
                color: {colors['text_primary']};
                border: none;
            }}
            
            QTabWidget {{
                background-color: {colors['content_bg']};
                color: {colors['text_primary']};
            }}
            
            QTabBar::tab {{
                background-color: {colors['sidebar_bg']};
                color: {colors['text_primary']};
                padding: 4px 12px;
                border: none;
            }}
            
            QTabBar::tab:selected {{
                background-color: {colors['accent_color']};
                color: {colors['text_primary']};
            }}
            
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.5 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                color: {colors['text_primary']};
            }}
        """


# Глобальный экземпляр менеджера тем
_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Возвращает глобальный экземпляр менеджера тем"""
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager
