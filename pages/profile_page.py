"""
Страница профиля (Profile Page)
PyQt6 версия
"""
import os
import sqlite3
import json
import threading
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QTextEdit, QPushButton, QScrollArea, QFileDialog,
    QMessageBox, QGraphicsDropShadowEffect, QDialog, QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QBrush, QPen, QTextOption
import math

# Импортируем функции из основного файла
# Используем ленивый импорт, чтобы избежать циклических зависимостей
def get_current_language():
    """Получает текущий язык"""
    try:
        from email_app import CURRENT_LANGUAGE
        return CURRENT_LANGUAGE
    except ImportError:
        return 'de'

def get_translations():
    """Получает словарь переводов (устаревшая функция, используйте tr() вместо этого)"""
    # TRANSLATIONS больше не существует, используется система из localization_manager
    return {}

def get_tr():
    """Получает функцию перевода"""
    try:
        from email_app import tr
        return tr
    except ImportError:
        def fallback_tr(key):
            return key
        return fallback_tr

def get_functions():
    """Получает необходимые функции и константы"""
    try:
        from email_app import (
            get_user_info, get_current_username, save_user_info,
            get_email_history, get_days_in_app, get_friends,
            get_google_account_email, get_user_online_status,
            set_user_online, save_google_account, save_attached_files,
            get_app_colors, DB_FILE, GOOGLE_OAUTH_AVAILABLE,
            authenticate_google_oauth, process_google_credentials,
            LoginScreen
        )
        return {
            'get_user_info': get_user_info,
            'get_current_username': get_current_username,
            'save_user_info': save_user_info,
            'get_email_history': get_email_history,
            'get_days_in_app': get_days_in_app,
            'get_friends': get_friends,
            'get_google_account_email': get_google_account_email,
            'get_user_online_status': get_user_online_status,
            'set_user_online': set_user_online,
            'save_google_account': save_google_account,
            'save_attached_files': save_attached_files,
            'get_app_colors': get_app_colors,
            'DB_FILE': DB_FILE,
            'GOOGLE_OAUTH_AVAILABLE': GOOGLE_OAUTH_AVAILABLE,
            'authenticate_google_oauth': authenticate_google_oauth,
            'process_google_credentials': process_google_credentials,
            'LoginScreen': LoginScreen
        }
    except ImportError:
        return {
            'get_user_info': lambda username=None: None,
            'get_current_username': lambda: None,
            'save_user_info': lambda *args, **kwargs: None,
            'get_email_history': lambda username=None, force_refresh=False: [],
            'get_days_in_app': lambda username=None: 0,
            'get_friends': lambda username: [],
            'get_google_account_email': lambda username: None,
            'get_user_online_status': lambda username: (False, None),
            'set_user_online': lambda username, is_online=True: None,
            'save_google_account': lambda *args, **kwargs: False,
            'save_attached_files': lambda *args, **kwargs: None,
            'get_app_colors': lambda: {},
            'DB_FILE': 'email_app.db',
            'GOOGLE_OAUTH_AVAILABLE': False,
            'authenticate_google_oauth': lambda: (None, None, 'Not available'),
            'process_google_credentials': lambda creds: (None, None, 'Not available'),
            'LoginScreen': None
        }

# Функция get_data_dialog удалена - данные теперь в настройках

from email_app import t, tr, get_current_language, set_language, get_localization_manager

def create_badge_icon(color: str = "#2D1B3D", size: int = 24) -> QPixmap:
    """Создает иконку бейджика (только звезда, без круга)"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    center_x, center_y = size // 2, size // 2
    
    # Только звезда без круга (без фиолетового фона)
    outer_radius = size // 2 - 2
    inner_radius = outer_radius * 0.4
    points = []
    for i in range(10):
        angle = math.pi / 2 - (i * 2 * math.pi / 10)
        r = outer_radius if i % 2 == 0 else inner_radius
        x = center_x + r * math.cos(angle)
        y = center_y - r * math.sin(angle)
        points.append(QPoint(int(x), int(y)))
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(QPen(QColor(color), 1))
    painter.drawPolygon(points)
    
    painter.end()
    return pixmap


class TabButtonWithArrow(QPushButton):
    """Вкладка-закладка с треугольником справа, лиловая, как на фото"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.hover_color = "#DDD6FE"  # Еще более светлый лиловый при наведении
        self.normal_color = "#C4B5FD"  # Еще более светлый лиловый нормальный
        self.current_color = self.normal_color
    
    def enterEvent(self, event):
        self.current_color = self.hover_color
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.current_color = self.normal_color
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # Рисуем основную часть вкладки (лиловая)
        # Треугольник справа, так как закладки выходят из-под рамки справа
        triangle_width = 8  # Уменьшен треугольник для меньших закладок
        tab_rect = QRect(0, 0, rect.width() - triangle_width, rect.height())
        painter.setBrush(QBrush(QColor(self.current_color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(tab_rect, 4, 4)  # Меньший радиус для меньших закладок
        
        # Рисуем треугольник справа (выходит из-под рамки и приклеен)
        triangle_points = [
            QPoint(rect.width() - triangle_width, 0),
            QPoint(rect.width(), rect.height() // 2),
            QPoint(rect.width() - triangle_width, rect.height())
        ]
        painter.drawPolygon(triangle_points)
        
        # Рисуем текст (иконка) - монохромная белая, увеличенный размер
        painter.setPen(QPen(QColor("#FFFFFF")))
        font = QFont("Segoe UI", 13, QFont.Weight.Bold)  # Увеличенный шрифт для лучшей видимости
        painter.setFont(font)
        triangle_width = 8
        text_rect = QRect(0, 0, rect.width() - triangle_width, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())


class OutlinedTextLabel(QLabel):
    """QLabel с черной обводкой текста"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(0, 0, 0, 255)
        self.text_color = QColor(255, 255, 255, 255)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Рисуем текст с обводкой (4 направления)
        font = self.font()
        painter.setFont(font)
        
        # Обводка в 4 направлениях
        painter.setPen(QPen(self.outline_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
            painter.drawText(self.rect().adjusted(dx, dy, dx, dy), Qt.AlignmentFlag.AlignCenter, self.text())
        
        # Основной текст
        painter.setPen(QPen(self.text_color))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class FrameSelectionDialog(QDialog):
    """Диалог выбора рамки профиля из предоставленных приложением"""
    def __init__(self, available_frames, parent=None, username=None):
        super().__init__(parent)
        self.available_frames = available_frames
        self.selected_frame = None
        self.username = username
        self.parent_page = parent  # Сохраняем ссылку на ProfilePage
        self.main_window = parent.main_window if parent and hasattr(parent, 'main_window') else None
        self.overlay = None
        self.setWindowTitle("Выбор карточки профиля")
        self.setFixedSize(1200, 800)  # Размер для сетки и правой панели
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
    
    def get_frame_description(self, frame_name):
        """Возвращает описание карточки по названию"""
        descriptions = {
            "Default": "Простая и элегантная карточка профиля по умолчанию. Чистый и минималистичный дизайн.",
            "Familiar": "Классический стиль для ежедневного использования. Универсальная карточка на все случаи жизни.",
            "first_letter_frame": "Особая рамка, разблокируемая за первое письмо. Символизирует начало вашего пути.",
            "ChatGPT Image 8 янв. 2026 г., 01_33_40": "Уникальная карточка с особенным дизайном. Создана с помощью искусственного интеллекта.",
        }
        # Проверяем точное совпадение
        if frame_name in descriptions:
            return descriptions[frame_name]
        # Попытка найти описание по частичному совпадению
        frame_lower = frame_name.lower()
        if "hacker" in frame_lower:
            return "Стильная карточка для программистов и любителей технологий. Темный и современный дизайн."
        elif "dreamy" in frame_lower or "cloud" in frame_lower:
            return "Парящие облака, мягкое свечение и пурпурный туман. Романтичная и мечтательная атмосфера."
        elif "familiar" in frame_lower:
            return "Классический стиль для ежедневного использования. Универсальная карточка на все случаи жизни."
        else:
            return "Уникальная карточка профиля с особенным дизайном. Выразите свою индивидуальность."
    
    def is_frame_unlocked(self, frame_path):
        """Проверяет, разблокирована ли рамка"""
        frame_name = Path(frame_path).stem
        frame_lower = frame_name.lower()
        
        # Первая рамка (first_letter_frame) разблокируется за первое письмо или достижение "Первый шаг"
        if frame_name == "first_letter_frame":
            if self.username:
                try:
                    # Импортируем функции для проверки истории
                    from email_app import get_email_history
                    history = get_email_history(self.username)
                    has_email = len(history) > 0
                    
                    # Также проверяем наличие достижения "Первый шаг"
                    try:
                        from email_app import get_user_achievements
                        achievements = get_user_achievements(self.username)
                        has_first_step = any(
                            ach.get('name') == 'Первый шаг' or 
                            ach.get('name') == 'First Step' or
                            ach.get('name') == 'Erster Schritt'
                            for ach in achievements
                        )
                        return has_email or has_first_step
                    except:
                        return has_email  # Разблокирована если есть хотя бы одно письмо
                except:
                    pass
            return False
        
        # Hacker карточка разблокируется только после получения достижения "Первый шаг"
        if "hacker" in frame_lower:
            if self.username:
                try:
                    # Проверяем наличие достижения "Первый шаг"
                    from email_app import get_user_achievements
                    achievements = get_user_achievements(self.username)
                    has_first_step = any(
                        ach.get('name') == 'Первый шаг' or 
                        ach.get('name') == 'First Step' or
                        ach.get('name') == 'Erster Schritt' or
                        ach.get('id') == 'first_step'
                        for ach in achievements
                    )
                    # Также проверяем наличие хотя бы одного письма
                    from email_app import get_email_history
                    history = get_email_history(self.username)
                    has_email = len(history) > 0
                    return has_first_step or has_email
                except:
                    # Если не удалось проверить, блокируем
                    return False
            return False
        
        # По умолчанию все остальные рамки разблокированы
        return True
    
    def setup_ui(self):
        """Создает интерфейс диалога в стиле приложения"""
        # Получаем цвета темы приложения
        from email_app import get_app_colors
        colors = get_app_colors()
        self.colors = colors  # Сохраняем для использования в других методах
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # Контейнер с фоном в стиле приложения (градиентный фон как в главном окне)
        container = QFrame()
        container.setObjectName("frameSelectionContainer")
        container.setStyleSheet(f"""
            QFrame#frameSelectionContainer {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.95),
                    stop:0.5 rgba(248, 242, 255, 0.95),
                    stop:1 rgba(240, 235, 255, 0.95));
                border-radius: 32px;
                border: 2px solid rgba(167, 139, 250, 0.3);
            }}
        """)
        
        # Добавляем тень для глубины
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(28, 28, 28, 28)
        container_layout.setSpacing(20)
        container.setLayout(container_layout)
        
        # Заголовок с кнопкой закрытия (в стиле приложения)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)
        
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        title = QLabel("Карточки профиля")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("Выберите и настройте вашу карточку профиля")
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setStyleSheet(f"color: {colors.get('text_secondary', '#8A7A9A')}; background: transparent;")
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        # Кнопка закрытия в стиле приложения
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {colors.get('button_secondary_bg', 'rgba(255, 255, 255, 0.1)')};
                border: 2px solid {colors.get('input_border', 'rgba(167, 139, 250, 0.4)')};
                border-radius: 18px;
                color: {colors['text_primary']};
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {colors.get('accent', 'rgba(167, 139, 250, 0.2)')};
                border-color: {colors.get('accent', 'rgba(167, 139, 250, 0.6)')};
            }}
        """)
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        # Фильтры
        filters_layout = QHBoxLayout()
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(12)
        
        self.filter_buttons = {}
        filter_names = ["Все", "Анимированные", "Минимал", "Сезонные", "Редкие"]
        self.current_filter = "Все"
        
        for filter_name in filter_names:
            btn = QPushButton(filter_name)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_selected = (filter_name == "Все")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'rgba(196, 181, 253, 0.3)' if is_selected else 'transparent'};
                    border: 2px solid {'rgba(167, 139, 250, 0.6)' if is_selected else 'rgba(167, 139, 250, 0.3)'};
                    border-radius: 8px;
                    color: {colors['text_primary']};
                    font-size: 13px;
                    font-weight: {'600' if is_selected else '500'};
                    padding: 0px 16px;
                }}
                QPushButton:hover {{
                    background: rgba(196, 181, 253, 0.2);
                    border-color: rgba(167, 139, 250, 0.5);
                }}
            """)
            btn.clicked.connect(lambda checked, name=filter_name: self.set_filter(name))
            filters_layout.addWidget(btn)
            self.filter_buttons[filter_name] = btn
        
        filters_layout.addStretch()
        container_layout.addLayout(filters_layout)
        
        # Основной контент: левая часть (сетка) и правая часть (превью)
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(24)
        
        # Получаем текущую выбранную рамку
        current_frame_path = None
        if self.parent_page and hasattr(self.parent_page, 'get_user_frame_path'):
            current_frame_path = self.parent_page.get_user_frame_path(self.username)
        elif self.username:
            try:
                from email_app import DB_FILE
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT frame_path FROM auth_users WHERE username = ?', (self.username,))
                result = cursor.fetchone()
                conn.close()
                # Если frame_path пустой или None, это означает default
                if result and result[0] and result[0].strip() and Path(result[0]).exists():
                    current_frame_path = result[0]
                # Если result[0] пустой или None, current_frame_path остается None (это default)
            except:
                pass
        
        # Левая часть - сетка карточек (3 колонки)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {colors.get('button_secondary_bg', 'rgba(255, 255, 255, 0.1)')};
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors.get('accent', 'rgba(167, 139, 250, 0.5)')};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors.get('accent', 'rgba(167, 139, 250, 0.7)')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        scroll_widget = QWidget()
        self.cards_grid = QGridLayout()
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(16)
        scroll_widget.setLayout(self.cards_grid)
        left_scroll.setWidget(scroll_widget)
        
        main_content_layout.addWidget(left_scroll, 2)  # Левая часть - 2/3 ширины
        
        # Правая часть - панель превью (1/3 ширины)
        self.preview_panel = self.create_preview_panel(colors, current_frame_path)
        main_content_layout.addWidget(self.preview_panel, 1)  # Правая часть - 1/3 ширины
        
        container_layout.addLayout(main_content_layout)
        
        # Сохраняем ссылки
        self.current_frame_path = current_frame_path
        
        # Заполняем сетку карточками
        self.populate_cards_grid(colors, current_frame_path)
        
        # Инициализируем превью текущей выбранной карточки
        if current_frame_path and current_frame_path != "default":
            self.update_preview(Path(current_frame_path).stem, current_frame_path)
        else:
            self.update_preview("Default", None)
        
        layout.addWidget(container)
    
    def create_preview_panel(self, colors, current_frame_path):
        """Создает правую панель с превью выбранной карточки"""
        preview_panel = QFrame()
        preview_panel.setObjectName("previewPanel")
        preview_panel.setFixedWidth(320)
        preview_panel.setStyleSheet(f"""
            QFrame#previewPanel {{
                background: transparent;
                border: none;
            }}
        """)
        
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(20)
        preview_panel.setLayout(preview_layout)
        
        # Превью карточки (большое изображение)
        self.preview_card_label = QLabel()
        self.preview_card_label.setFixedHeight(200)
        self.preview_card_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_card_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border-radius: 16px;
            }}
        """)
        self.preview_card_label.setScaledContents(False)
        preview_layout.addWidget(self.preview_card_label)
        
        # Название карточки
        self.preview_name_label = QLabel("Выберите карточку")
        self.preview_name_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.preview_name_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        preview_layout.addWidget(self.preview_name_label)
        
        # Описание карточки
        self.preview_desc_label = QLabel("")
        self.preview_desc_label.setFont(QFont("Segoe UI", 13))
        self.preview_desc_label.setWordWrap(True)
        self.preview_desc_label.setStyleSheet(f"color: {colors.get('text_secondary', '#8A7A9A')}; background: transparent; padding: 0px;")
        preview_layout.addWidget(self.preview_desc_label)
        
        preview_layout.addStretch()
        
        # Кнопка "Применить" внизу
        self.preview_select_btn = QPushButton("Применить")
        self.preview_frame_path = None  # Сохраняем путь к выбранной карточке для превью
        self.preview_select_btn.setFixedHeight(44)
        self.preview_select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_select_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(196, 181, 253, 0.4);
                border: 2px solid rgba(167, 139, 250, 0.6);
                border-radius: 12px;
                color: {colors['text_primary']};
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(196, 181, 253, 0.5);
                border-color: rgba(167, 139, 250, 0.8);
            }}
        """)
        self.preview_select_btn.hide()  # Скрыта по умолчанию
        preview_layout.addWidget(self.preview_select_btn)
        
        return preview_panel
    
    def populate_cards_grid(self, colors, current_frame_path):
        """Заполняет сетку карточками (2 колонки)"""
        # Очищаем сетку
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Добавляем карточку "Default" в сетку
        row = 0
        col = 0
        
        default_card = self.create_grid_card("Default", None, colors, current_frame_path, is_default=True)
        self.cards_grid.addWidget(default_card, row, col)
        col += 1
        
        # Добавляем все доступные рамки в сетку (2 колонки)
        for frame_path in self.available_frames:
            if col >= 2:
                col = 0
                row += 1
            
            is_unlocked = self.is_frame_unlocked(frame_path)
            frame_card = self.create_grid_card(Path(frame_path).stem, frame_path, colors, current_frame_path, is_unlocked)
            self.cards_grid.addWidget(frame_card, row, col)
            col += 1
    
    def create_grid_card(self, frame_name, frame_path, colors, current_frame_path, is_unlocked=True, is_default=False):
        """Создает карточку для сетки (компактная версия)"""
        # Определяем, выбрана ли эта карточка
        is_selected = False
        if is_default:
            is_selected = (current_frame_path is None or current_frame_path == "" or current_frame_path == "default")
        else:
            is_selected = (current_frame_path and str(frame_path) == str(current_frame_path))
        
        card = QFrame()
        card.setFixedSize(340, 180)  # Увеличен по горизонтали (было 280)
        card.setObjectName("gridCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Стиль карточки - белая обводка (толще для выбранной)
        if is_selected:
            border_color = "rgba(255, 255, 255, 1.0)"
            border_width = 3
        else:
            border_color = "rgba(255, 255, 255, 0.9)"
            border_width = 2
        
        if is_default:
            # Default карточка - белый фон с белой обводкой
            card.setStyleSheet(f"""
                QFrame#gridCard {{
                    background: rgba(255, 255, 255, 1.0);
                    border: {border_width}px solid {border_color};
                    border-radius: 16px;
                }}
            """)
            
            card_layout = QVBoxLayout()  # Вертикальный layout для названия
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(0)
            card.setLayout(card_layout)
            
            name_label = QLabel("Default")
            name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: #2D1B3D;
                    background: transparent;
                    border: none;
                }}
            """)
            card_layout.addWidget(name_label)
            card_layout.addStretch()
            
            # Клик на карточку для превью или применения
            def on_card_click_default(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    # Проверяем, не кликнули ли на label
                    label_rect = name_label.geometry()
                    if not label_rect.contains(e.pos()):
                        self.update_preview("Default", None)
            card.mousePressEvent = on_card_click_default
        else:
            # Карточка с изображением - белая обводка, прозрачный фон
            card.setStyleSheet(f"""
                QFrame#gridCard {{
                    border: {border_width}px solid {border_color};
                    border-radius: 16px;
                    background: transparent;
                }}
            """)
            
            # Загружаем изображение
            frame_pixmap = QPixmap(str(frame_path))
            if not frame_pixmap.isNull():
                # Масштабируем для карточки (увеличена ширина до 340)
                scaled_pixmap = frame_pixmap.scaled(340, 180, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                if scaled_pixmap.width() > 340 or scaled_pixmap.height() > 180:
                    x = (scaled_pixmap.width() - 340) // 2
                    y = (scaled_pixmap.height() - 180) // 2
                    scaled_pixmap = scaled_pixmap.copy(x, y, 340, 180)
                
                # Создаем закругленное изображение
                rounded_pixmap = QPixmap(340, 180)
                rounded_pixmap.fill(QColor(0, 0, 0, 0))
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(scaled_pixmap))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(0, 0, 340, 180, 16, 16)
                
                if not is_unlocked:
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Darken)
                    painter.fillRect(0, 0, 340, 180, QColor(0, 0, 0, 128))
                
                painter.end()
                
                image_label = QLabel(card)
                image_label.setPixmap(rounded_pixmap)
                image_label.setGeometry(0, 0, 340, 180)
                image_label.lower()
                image_label.setStyleSheet("border-radius: 16px;")
                image_label.show()
            
            # Используем абсолютное позиционирование для элементов
            # Layout не устанавливаем, используем setGeometry для позиционирования
            
            # Название слева сверху на полупрозрачной белой полоске (как на изображении)
            name_label = QLabel(frame_name, card)
            name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            name_label.setStyleSheet(f"""
                QLabel {{
                    background: rgba(255, 255, 255, 0.75);
                    color: #2D1B3D;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 12px;
                }}
            """)
            name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            name_label.setGeometry(12, 12, 200, 28)  # Слева сверху на полупрозрачной полоске
            name_label.show()
            name_label.raise_()
            
            # Замок для заблокированных (по центру карточки, поверх изображения)
            if not is_unlocked:
                lock_icon = QLabel("🔒", card)
                lock_icon.setObjectName("lockIcon")
                lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lock_icon.setFixedSize(36, 36)
                lock_icon.setStyleSheet("""
                    QLabel#lockIcon {
                        background: rgba(0, 0, 0, 0.7);
                        border-radius: 18px;
                        color: #FFFFFF;
                        font-size: 18px;
                        border: 2px solid rgba(255, 255, 255, 0.3);
                    }
                """)
                lock_icon.setGeometry(152, 72, 36, 36)  # По центру карточки (340/2 - 18)
                lock_icon.raise_()
                lock_icon.show()
            
            # Клик на карточку для превью (кнопка убрана, только в превью)
            if is_unlocked:
                def on_card_click(e):
                    if e.button() == Qt.MouseButton.LeftButton:
                        self.update_preview(frame_name, frame_path)
                card.mousePressEvent = on_card_click
        
        return card
    
    def set_filter(self, filter_name):
        """Устанавливает активный фильтр"""
        self.current_filter = filter_name
        # Обновляем стили кнопок фильтров
        for name, btn in self.filter_buttons.items():
            is_selected = (name == filter_name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'rgba(196, 181, 253, 0.3)' if is_selected else 'transparent'};
                    border: 2px solid {'rgba(167, 139, 250, 0.6)' if is_selected else 'rgba(167, 139, 250, 0.3)'};
                    border-radius: 8px;
                    color: {self.colors['text_primary']};
                    font-size: 13px;
                    font-weight: {'600' if is_selected else '500'};
                    padding: 0px 16px;
                }}
                QPushButton:hover {{
                    background: rgba(196, 181, 253, 0.2);
                    border-color: rgba(167, 139, 250, 0.5);
                }}
            """)
        # TODO: Обновить отображаемые карточки согласно фильтру
    
    def update_preview(self, frame_name, frame_path=None):
        """Обновляет превью выбранной карточки"""
        if frame_path and frame_path != "default":
            # Загружаем изображение для превью
            frame_pixmap = QPixmap(str(frame_path))
            if not frame_pixmap.isNull():
                # Масштабируем для превью
                scaled_pixmap = frame_pixmap.scaled(320, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                if scaled_pixmap.width() > 320 or scaled_pixmap.height() > 200:
                    x = (scaled_pixmap.width() - 320) // 2
                    y = (scaled_pixmap.height() - 200) // 2
                    scaled_pixmap = scaled_pixmap.copy(x, y, 320, 200)
                
                # Создаем закругленное изображение
                rounded_pixmap = QPixmap(320, 200)
                rounded_pixmap.fill(QColor(0, 0, 0, 0))
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(scaled_pixmap))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(0, 0, 320, 200, 16, 16)
                painter.end()
                
                self.preview_card_label.setPixmap(rounded_pixmap)
            else:
                self.preview_card_label.clear()
        else:
            # Default - показываем пустое превью или placeholder
            self.preview_card_label.clear()
            self.preview_card_label.setStyleSheet(f"""
                QLabel {{
                    background: rgba(255, 255, 255, 0.6);
                    border-radius: 16px;
                }}
            """)
        
        # Обновляем название
        self.preview_name_label.setText(frame_name)
        
        # Обновляем описание
        description = self.get_frame_description(frame_name)
        self.preview_desc_label.setText(description)
        
        # Показываем кнопку "Применить" и сохраняем путь к карточке
        # Правильно обрабатываем "default" - сохраняем как "default" для select_frame
        if frame_path is None or frame_path == "":
            self.preview_frame_path = "default"
        else:
            self.preview_frame_path = frame_path
        self.preview_select_btn.show()
        # Подключаем обработчик клика на кнопку "Применить"
        try:
            self.preview_select_btn.clicked.disconnect()  # Отключаем старые обработчики (если есть)
        except TypeError:
            pass  # Если обработчиков нет, это нормально
        self.preview_select_btn.clicked.connect(lambda: self.select_frame(self.preview_frame_path))
    
    def select_frame(self, frame_path):
        """Выбирает рамку и закрывает диалог"""
        # Обрабатываем "default" правильно
        if frame_path == "default" or frame_path is None:
            self.selected_frame = "default"
        else:
            self.selected_frame = frame_path
        # Закрываем диалог с результатом Accepted
        self.accept()
    
    def showEvent(self, event):
        """Создает overlay и центрирует диалог при показе"""
        super().showEvent(event)
        if self.main_window:
            # Создаем overlay для затемнения фона
            from PyQt6.QtWidgets import QWidget
            self.overlay = QWidget(self.main_window)
            self.overlay.setGeometry(0, 0, self.main_window.width(), self.main_window.height())
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.6);")
            self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            
            def close_on_overlay_click(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.reject()
            
            self.overlay.mousePressEvent = close_on_overlay_click
            self.overlay.show()
            self.overlay.raise_()
            
            # Центрируем диалог относительно главного окна
            parent_geometry = self.main_window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
            
            # Поднимаем диалог поверх overlay
            self.raise_()
            self.activateWindow()
    
    def closeEvent(self, event):
        """Удаляет overlay при закрытии"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except:
                pass
            self.overlay = None
        super().closeEvent(event)
    
    def accept(self):
        """Принимает диалог и удаляет overlay"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except:
                pass
            self.overlay = None
        super().accept()
    
    def reject(self):
        """Отменяет диалог и удаляет overlay"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except:
                pass
            self.overlay = None
        super().reject()


class ProfileEditDialog(QDialog):
    """Диалог редактирования профиля в стиле settings.py"""
    def __init__(self, profile_page, main_window, parent=None):
        from PyQt6.QtWidgets import QDialog
        super().__init__(parent)
        self.profile_page = profile_page
        self.main_window = main_window
        self.overlay = None
        self.setWindowTitle("Редактирование профиля")
        self.setFixedSize(500, 300)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
    
    def setup_ui(self):
        """Создает интерфейс диалога"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # Контейнер с фоном
        container = QFrame()
        container.setObjectName("profileEditContainer")
        container.setStyleSheet("""
            QFrame#profileEditContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 20px;
                border: 2px solid rgba(167, 139, 250, 0.6);
            }
        """)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(16)
        container.setLayout(container_layout)
        
        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        
        title = QLabel("Редактирование профиля")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2D1B3D; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 14px;
                color: #7C6A9B;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(156, 137, 184, 0.2);
            }
        """)
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        # Кнопки редактирования
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(12)
        
        # Кнопка изменения рамки
        change_frame_btn = QPushButton("🖼️ Изменить рамку профиля")
        change_frame_btn.setFixedHeight(50)
        change_frame_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_frame_btn.clicked.connect(self.change_frame)
        change_frame_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(167, 139, 250, 0.9),
                    stop:1 rgba(139, 92, 246, 0.9));
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(156, 128, 235, 0.95),
                    stop:1 rgba(128, 81, 231, 0.95));
            }
        """)
        buttons_layout.addWidget(change_frame_btn)
        
        # Кнопка изменения аватара
        change_avatar_btn = QPushButton("👤 Изменить аватар")
        change_avatar_btn.setFixedHeight(50)
        change_avatar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_avatar_btn.clicked.connect(self.change_avatar)
        change_avatar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(167, 139, 250, 0.9),
                    stop:1 rgba(139, 92, 246, 0.9));
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(156, 128, 235, 0.95),
                    stop:1 rgba(128, 81, 231, 0.95));
            }
        """)
        buttons_layout.addWidget(change_avatar_btn)
        
        # Кнопка редактирования "О себе"
        edit_about_btn = QPushButton("✏️ Редактировать О себе")
        edit_about_btn.setFixedHeight(50)
        edit_about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_about_btn.clicked.connect(self.edit_about_me)
        edit_about_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(167, 139, 250, 0.9),
                    stop:1 rgba(139, 92, 246, 0.9));
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(156, 128, 235, 0.95),
                    stop:1 rgba(128, 81, 231, 0.95));
            }
        """)
        buttons_layout.addWidget(edit_about_btn)
        
        container_layout.addLayout(buttons_layout)
        container_layout.addStretch()
        
        layout.addWidget(container)
    
    def showEvent(self, event):
        """Создает overlay и центрирует диалог при показе"""
        super().showEvent(event)
        if self.main_window:
            # Удаляем старый overlay если он есть
            if self.overlay:
                try:
                    self.overlay.deleteLater()
                except:
                    pass
            
            # Создаем overlay на главном окне
            self.overlay = QFrame(self.main_window)
            self.overlay.setGeometry(0, 0, self.main_window.width(), self.main_window.height())
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
            self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            
            def close_on_overlay_click(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.reject()
            
            self.overlay.mousePressEvent = close_on_overlay_click
            self.overlay.show()
            self.overlay.raise_()
            
            # Центрируем диалог относительно главного окна
            parent_geometry = self.main_window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
            
            # Поднимаем диалог поверх overlay
            self.raise_()
            self.activateWindow()
    
    def closeEvent(self, event):
        """Удаляет overlay при закрытии"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
        super().closeEvent(event)
    
    def reject(self):
        """Отменяет диалог и удаляет overlay"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
        super().reject()
    
    def change_frame(self):
        """Изменяет рамку профиля"""
        self.accept()
        if self.profile_page:
            self.profile_page.change_frame()
    
    def change_avatar(self):
        """Изменяет аватар"""
        self.accept()
        if self.profile_page:
            self.profile_page.change_avatar()
    
    def edit_about_me(self):
        """Редактирует О себе - открывает настройки для редактирования"""
        self.accept()
        if self.profile_page:
            # Просто открываем настройки, окно "данные" больше не используется
            if hasattr(self.profile_page, 'main_window') and self.profile_page.main_window:
                if hasattr(self.profile_page.main_window, 'show_settings'):
                    self.profile_page.main_window.show_settings()


class ProfilePage(QWidget):
    """Страница профиля"""
    # Сигнал для успешной авторизации Google (email, token)
    google_auth_success = pyqtSignal(str, str)
    # Сигнал для завершения OAuth (для обратной совместимости)
    signal_oauth_complete = pyqtSignal(str)
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window  # Ссылка на главное окно для переключения страниц
        self.last_sent_at = None  # Сохраняем дату последней отправки
        self.is_editing_name = False  # Флаг режима редактирования
        self.is_active = False  # Флаг активности страницы
        self.profile_highlight_overlay = None  # Overlay для подсветки профиля
        self.profile_card_highlighted = False  # Флаг подсветки карточки
        
        # Инициализируем функции как None, загрузим позже
        self._tr = None
        self._funcs = None
        # Загружаем функции перед setup_ui (нужны для создания UI)
        self._funcs = get_functions()
        self._tr = get_tr()
        
        self.setup_ui()
        # Не загружаем данные сразу - только при активации
        # Устанавливаем event filter для обработки кликов вне полей
        self.installEventFilter(self)
        # Подключаем сигналы OAuth к слотам
        self.google_auth_success.connect(self.on_google_auth_success)
        self.signal_oauth_complete.connect(self.on_oauth_complete)
        
        # Устанавливаем обработчик переключения окон
        if self.main_window:
            self.main_window.installEventFilter(self)
    
    def activate(self):
        """Активирует страницу - загружает данные"""
        if not self.is_active:
            self.is_active = True
            self.load_user_info()
            # Google аккаунт теперь в настройках
    
    def deactivate(self):
        """Деактивирует страницу"""
        if self.is_active:
            self.is_active = False
    
    
    def tr(self, key):
        """Обёртка для функции перевода"""
        if self._tr is None:
            self._tr = get_tr()
        return self._tr(key)
    
    def _get_funcs(self):
        """Получает функции, загружая их при необходимости"""
        if self._funcs is None:
            self._funcs = get_functions()
        return self._funcs

    def setup_ui(self):
        """Создает современный интерфейс профиля"""
        colors = self._get_funcs()['get_app_colors']()
        
        # Главный контейнер с прокруткой
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Контент виджет
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(24)
        layout.setContentsMargins(60, 50, 60, 50)
        content_widget.setLayout(layout)
        main_scroll.setWidget(content_widget)
        
        # Главный layout для scroll area
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Устанавливаем фон через менеджер тем
        from email_app import get_app_colors
        colors = get_app_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                font-family: "Inter", "Segoe UI", sans-serif;
                color: {colors['text_primary']};
            }}
        """)
        
        main_layout.addWidget(main_scroll)
        
        # === ЗАГОЛОВОК СЕКЦИИ ===
        header_container = QFrame()
        header_container.setObjectName("headerContainer")
        header_container.setStyleSheet("""
            QFrame#headerContainer {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_container.setLayout(header_layout)
        
        title_label = QLabel(self.tr("profile"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_font = QFont("Segoe UI", 36, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
            background: transparent;
                letter-spacing: -0.5px;
            }
        """)
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel(self.tr("manage_account_and_settings"))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        subtitle_label.setFont(QFont("Segoe UI", 13))
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #8A7A9A;
                background: transparent;
            }
        """)
        header_layout.addWidget(subtitle_label)
        layout.addWidget(header_container)
        
        # === ПРОФИЛЬНАЯ КАРТОЧКА (Аватар + Основная информация) ===
        profile_main_card = QFrame()
        profile_main_card.setObjectName("profileMainCard")
        profile_main_card.setCursor(Qt.CursorShape.PointingHandCursor)
        profile_main_card.setStyleSheet(f"""
            QFrame#profileMainCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 28px;
                border: 2px solid rgba(200, 182, 226, 0.4);
                padding: 0px;
            }}
            QFrame#profileMainCard:hover {{
                border: 2px solid rgba(200, 182, 226, 0.6);
            }}
        """)
        # Тень для главной карточки
        main_shadow = QGraphicsDropShadowEffect()
        main_shadow.setBlurRadius(30)
        main_shadow.setXOffset(0)
        main_shadow.setYOffset(8)
        main_shadow.setColor(QColor(108, 74, 139, 80))
        profile_main_card.setGraphicsEffect(main_shadow)
        # Карточка не кликабельна - только виджеты внутри
        profile_main_card.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Сохраняем ссылку на карточку для эффекта подсветки
        self.profile_main_card = profile_main_card
        self.is_edit_mode = False  # Флаг режима редактирования
        
        # Сохраняем исходный размер рамки, чтобы она не уменьшалась
        # Это будет установлено после первого отображения
        self.original_profile_card_size = None
        
        # Переопределяем resizeEvent для обновления маски и фона
        original_resize = profile_main_card.resizeEvent if hasattr(profile_main_card, 'resizeEvent') else None
        def resize_with_mask_and_background(event):
            if original_resize:
                original_resize(event)
            # Обновляем маску и фон сразу при изменении размера
            size = self.profile_main_card.size()
            if size.width() > 10 and size.height() > 10:
                # Обновляем маску сразу
                self._update_profile_card_mask()
                # Обновляем фон карточки при изменении размера (если есть рамка)
                if hasattr(self, '_current_frame_path') and self._current_frame_path:
                    QTimer.singleShot(10, lambda: self._apply_frame_background(self._current_frame_path))
        profile_main_card.resizeEvent = resize_with_mask_and_background
        
        # Добавляем showEvent для правильной инициализации при первом показе
        original_show = profile_main_card.showEvent if hasattr(profile_main_card, 'showEvent') else None
        def show_with_init(event):
            if original_show:
                original_show(event)
            # Обновляем маску и фон после показа
            QTimer.singleShot(50, lambda: (
                self._update_profile_card_mask(),
                self._update_profile_on_show()
            ))
        profile_main_card.showEvent = show_with_init
        
        profile_main_layout = QVBoxLayout()
        profile_main_layout.setContentsMargins(40, 35, 40, 35)
        profile_main_layout.setSpacing(28)
        profile_main_card.setLayout(profile_main_layout)
        
        # Горизонтальный контейнер для аватара и информации
        avatar_info_container = QHBoxLayout()
        avatar_info_container.setSpacing(32)
        avatar_info_container.setContentsMargins(0, 0, 0, 0)
        
        # === АВАТАР === (слева без рамки)
        avatar_section = QFrame()
        avatar_section.setObjectName("avatarSection")
        avatar_section.setStyleSheet("""
            QFrame#avatarSection {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        avatar_section_layout = QVBoxLayout()
        avatar_section_layout.setContentsMargins(0, 0, 0, 0)
        avatar_section_layout.setSpacing(0)
        avatar_section_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_section.setLayout(avatar_section_layout)
        
        # Контейнер для аватара с карандашом при наведении
        avatar_wrapper = QWidget()
        avatar_wrapper.setObjectName("avatarWrapper")
        avatar_wrapper.setFixedSize(160, 160)
        # Убираем фон у wrapper, чтобы не было фиолетового прямоугольника
        avatar_wrapper.setStyleSheet("""
            QWidget#avatarWrapper {
                background: transparent;
                border: none;
            }
        """)
        avatar_wrapper.setAutoFillBackground(False)  # Убираем автоматическую заливку фона
        avatar_wrapper_layout = QVBoxLayout()
        avatar_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        avatar_wrapper_layout.setSpacing(0)
        avatar_wrapper.setLayout(avatar_wrapper_layout)
        
        # Аватар - круглый (без фиолетового квадрата сзади)
        # Создаем полностью прозрачный контейнер
        self.avatar_background = QWidget()
        self.avatar_background.setFixedSize(160, 160)
        # Полностью прозрачный фон
        self.avatar_background.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        self.avatar_background.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.avatar_background.setAutoFillBackground(False)
        avatar_background_layout = QVBoxLayout()
        avatar_background_layout.setContentsMargins(0, 0, 0, 0)
        avatar_background_layout.setSpacing(0)
        self.avatar_background.setLayout(avatar_background_layout)
        
        # Аватар - круглый (градиент только на самом label, не на фоне)
        self.avatar_label = QLabel()
        self.avatar_label.setObjectName("avatarLabel")
        self.avatar_label.setFixedSize(140, 140)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Градиент только для самого аватара (когда нет изображения)
        self.avatar_label.setStyleSheet(f"""
            QLabel#avatarLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['accent']},
                    stop:1 {colors['accent_alt']});
                border-radius: 70px;
                border: none;
                color: white;
                font-size: 56px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
            }}
        """)
        self.avatar_label.setAutoFillBackground(False)
        avatar_background_layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setCursor(Qt.CursorShape.ArrowCursor)
        avatar_wrapper_layout.addWidget(self.avatar_background)
        
        # Статус сети на круглом аватаре (всегда видимый, немного левее от центра)
        self.avatar_status_indicator = QLabel(self.avatar_label)
        self.avatar_status_indicator.setObjectName("avatarStatusIndicator")
        self.avatar_status_indicator.setFixedSize(20, 20)
        self.avatar_status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_status_indicator.setStyleSheet(f"""
            QLabel#avatarStatusIndicator {{
                background: #86868B;
                border-radius: 10px;
                border: none;
                padding: 0px;
            }}
        """)
        
        # Абсолютное позиционирование статуса на аватаре (правее от центра)
        def update_status_position():
            if hasattr(self, 'avatar_status_indicator') and hasattr(self, 'avatar_label'):
                icon_size = 20
                avatar_size = 140  # Размер аватара
                # Позиционируем еще правее (примерно на 0.85 от левого края, внизу)
                icon_x = int(avatar_size * 0.85) - icon_size // 2
                icon_y = avatar_size - icon_size - 5  # Внизу
                self.avatar_status_indicator.setGeometry(icon_x, icon_y, icon_size, icon_size)
        
        # Переопределяем resizeEvent для обновления позиции статуса
        original_resize_label = self.avatar_label.resizeEvent
        def resize_with_status_label(event):
            original_resize_label(event) if original_resize_label else QLabel.resizeEvent(self.avatar_label, event)
            update_status_position()
        self.avatar_label.resizeEvent = resize_with_status_label
        
        # Устанавливаем начальную позицию
        QTimer.singleShot(0, update_status_position)
        
        # Карандаш для редактирования аватара (появляется при наведении в режиме редактирования)
        self.avatar_edit_icon = QLabel(self.avatar_label)
        self.avatar_edit_icon.setObjectName("avatarEditIcon")
        self.avatar_edit_icon.setFixedSize(40, 40)
        self.avatar_edit_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_edit_icon.setText("✎")  # Монохромная иконка карандаша
        self.avatar_edit_icon.setStyleSheet(f"""
            QLabel#avatarEditIcon {{
                background: rgba(255, 255, 255, 0.9);
                border-radius: 18px;
                border: 2px solid rgba(255, 255, 255, 0.5);
                color: #2D1B3D;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
            }}
        """)
        edit_icon_shadow = QGraphicsDropShadowEffect()
        edit_icon_shadow.setBlurRadius(12)
        edit_icon_shadow.setXOffset(0)
        edit_icon_shadow.setYOffset(3)
        edit_icon_shadow.setColor(QColor(0, 0, 0, 100))
        self.avatar_edit_icon.setGraphicsEffect(edit_icon_shadow)
        self.avatar_edit_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_edit_icon.mousePressEvent = lambda e: self.change_avatar()
        self.avatar_edit_icon.hide()  # Скрыт по умолчанию
        
        # Абсолютное позиционирование карандаша в правом нижнем углу аватара
        def update_edit_icon_position():
            if hasattr(self, 'avatar_edit_icon') and hasattr(self, 'avatar_label'):
                icon_size = 40
                avatar_size = 140  # Размер аватара
                icon_x = avatar_size - icon_size - 5
                icon_y = avatar_size - icon_size - 5
                self.avatar_edit_icon.setGeometry(icon_x, icon_y, icon_size, icon_size)
        
        # Переопределяем resizeEvent для обновления позиции карандаша
        original_resize_label_with_edit = self.avatar_label.resizeEvent
        def resize_with_edit_icon(event):
            resize_with_status_label(event)
            update_edit_icon_position()
        self.avatar_label.resizeEvent = resize_with_edit_icon
        
        # Устанавливаем начальную позицию
        QTimer.singleShot(0, update_edit_icon_position)
        
        # Устанавливаем event filter только для режима редактирования (клик на аватар)
        self.avatar_wrapper = avatar_wrapper
        avatar_section_layout.addWidget(avatar_wrapper, alignment=Qt.AlignmentFlag.AlignCenter)
        avatar_info_container.addWidget(avatar_section)
        
        # === ОСНОВНАЯ ИНФОРМАЦИЯ ===
        info_section = QFrame()
        info_section.setObjectName("infoSection")
        info_section.setStyleSheet("QFrame#infoSection { background: transparent; border: none; }")
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(20)
        info_section.setLayout(info_layout)
        
        # Никнейм с иконкой бейджика - горизонтальный layout
        nickname_container = QHBoxLayout()
        nickname_container.setContentsMargins(0, 0, 0, 0)
        nickname_container.setSpacing(12)
        
        self.nickname_label = QLabel()
        self.nickname_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.nickname_label.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.nickname_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        nickname_container.addWidget(self.nickname_label)
        
        # Иконка бейджика справа от username (без фиолетового фона)
        self.badge_icon_label = QLabel()
        # Используем белый цвет для звезды внутри, фон прозрачный
        badge_pixmap = create_badge_icon("#2D1B3D", 24)  # Тёмный цвет для видимости
        self.badge_icon_label.setPixmap(badge_pixmap)
        self.badge_icon_label.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.badge_icon_label.setFixedSize(24, 24)
        self.badge_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nickname_container.addWidget(self.badge_icon_label)
        
        # Добавляем контейнер с nickname и бейджем
        nickname_widget = QWidget()
        nickname_widget.setLayout(nickname_container)
        nickname_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_layout.addWidget(nickname_widget)
        
        # Статус онлайн/офлайн (перемещен выше, сразу после никнейма) - фиксированный размер
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Segoe UI", 13))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #86868B;
                background: transparent;
                font-weight: 500;
            }
        """)
        # Устанавливаем фиксированную высоту, чтобы не смещался при изменении layout
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_layout.addWidget(self.status_label)
        
        # Виджет "О себе" - редактируемый прямо на месте (перемещен выше, сразу после статуса)
        about_me_section = QFrame()
        about_me_section.setObjectName("aboutMeSection")
        about_me_section.setStyleSheet("QFrame#aboutMeSection { background: transparent; border: none; }")
        about_me_layout = QVBoxLayout()
        about_me_layout.setContentsMargins(0, 0, 0, 0)
        about_me_layout.setSpacing(4)  # Уменьшен spacing между заголовком и текстом
        # Фиксируем размер секции, чтобы она не меняла размер при переключении виджетов
        fixed_about_me_height = 50  # Уменьшена высота для более компактного вида
        about_me_section.setFixedHeight(fixed_about_me_height + 28)  # Уменьшена высота секции
        about_me_section.setMinimumHeight(fixed_about_me_height + 28)
        about_me_section.setMaximumHeight(fixed_about_me_height + 28)
        about_me_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        about_me_section.setLayout(about_me_layout)
        # Сохраняем ссылку на секцию для фиксации позиции
        self.about_me_section = about_me_section
        
        about_me_header = QHBoxLayout()
        about_me_header.setContentsMargins(0, 0, 0, 0)
        about_me_header.setSpacing(8)
        
        about_me_title = QLabel("О себе")
        about_me_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        about_me_title.setStyleSheet("color: #86868B; background: transparent;")
        about_me_header.addWidget(about_me_title)
        about_me_header.addStretch()
        
        # Счетчик символов справа в заголовке - показывается только в режиме редактирования
        self.about_me_counter = QLabel("0/110")
        self.about_me_counter.setObjectName("aboutMeCounter")
        self.about_me_counter.setFont(QFont("Segoe UI", 10))
        self.about_me_counter.setStyleSheet("color: #86868B; background: transparent;")
        self.about_me_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.about_me_counter.setFixedWidth(50)  # Фиксированная ширина, чтобы не вызывать смещение
        self.about_me_counter.hide()  # Скрыт по умолчанию, показывается только в режиме редактирования
        about_me_header.addWidget(self.about_me_counter)
        
        # Кнопка редактирования О себе - убрана, редактирование только в режиме редактирования профиля
        about_me_layout.addLayout(about_me_header)
        
        # Текст "О себе" - редактируемый напрямую без виджета (как на фото 2)
        # Используем QTextEdit, но делаем его прозрачным и без рамки - выглядит как обычный текст
        fixed_about_me_height = 50  # Высота для текста
        
        # Контейнер для текста
        about_me_container = QFrame()
        about_me_container.setFixedHeight(fixed_about_me_height)
        about_me_container.setMinimumHeight(fixed_about_me_height)
        about_me_container.setMaximumHeight(fixed_about_me_height)
        about_me_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        about_me_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Используем QTextEdit, но делаем его прозрачным и без рамки - выглядит как обычный текст
        self.about_me_input = QTextEdit(about_me_container)
        self.about_me_input.setFont(QFont("Segoe UI", 13))
        self.about_me_input.setReadOnly(True)  # По умолчанию только чтение (как обычный текст)
        # Прозрачный стиль без рамки - выглядит как обычный текст (как на фото 2)
        # Фиксируем размеры и отступы, чтобы не было смещения при изменении ReadOnly
        self.about_me_input.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #2D1B3D;
                font-size: 13px;
                padding: 0px;
                margin: 0px;
            }
            QTextEdit:focus {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        # Фиксируем размеры, чтобы не было смещения при изменении ReadOnly
        self.about_me_input.setFixedHeight(fixed_about_me_height)
        self.about_me_input.setMinimumHeight(fixed_about_me_height)
        self.about_me_input.setMaximumHeight(fixed_about_me_height)
        self.about_me_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.about_me_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.about_me_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.about_me_input.document().setMaximumBlockCount(3)  # Максимум 3 строки
        # Устанавливаем документные отступы в 0, чтобы не было смещения
        self.about_me_input.document().setDocumentMargin(0)
        # Подключаем сигнал изменения текста
        self.about_me_input.textChanged.connect(self.on_about_me_text_changed)
        
        # Layout для контейнера - фиксированные отступы, чтобы не было смещения
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        about_me_container.setLayout(container_layout)
        container_layout.addWidget(self.about_me_input)
        
        # Сохраняем ссылку на контейнер
        self.about_me_container = about_me_container
        self.about_me_label = None  # Больше не используем отдельный label
        
        # Добавляем контейнер в layout
        about_me_layout.addWidget(about_me_container, 0)
        
        
        # Кнопки сохранения/отмены убраны - используем виджет несохраненных изменений
        self.save_about_btn = None
        self.cancel_about_btn = None
        
        info_layout.addWidget(about_me_section)
        
        # Кнопка настроек (шестеренка) справа СВЕРХУ в рамке профиля
        settings_button_layout = QHBoxLayout()
        settings_button_layout.addStretch()
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.enter_edit_mode)
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(156, 137, 184, 0.2);
                border: 2px solid rgba(156, 137, 184, 0.4);
                border-radius: 18px;
                color: #2D1B3D;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(156, 137, 184, 0.3);
                border-color: rgba(156, 137, 184, 0.6);
            }}
        """)
        settings_button_layout.addWidget(self.settings_btn)
        
        # Добавляем в начало info_layout (сверху справа)
        info_layout.insertLayout(0, settings_button_layout)
        
        info_layout.addStretch()
        
        # Добавляем аватар и информацию в горизонтальный контейнер
        avatar_info_container.addWidget(info_section, 1)
        profile_main_layout.addLayout(avatar_info_container)
        
        # Разделитель
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setStyleSheet("""
            QFrame {
                background: rgba(200, 182, 226, 0.3);
                max-height: 1px;
                border: none;
            }
        """)
        profile_main_layout.addWidget(divider)
        
        # Кнопки сохранения/отмены для имени (скрыты по умолчанию)
        self.name_buttons_layout = QHBoxLayout()
        self.name_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.name_buttons_layout.setSpacing(12)
        self.name_buttons_layout.addStretch()
        
        self.cancel_name_button = QPushButton("Отмена")
        self.cancel_name_button.setObjectName("cancelNameButton")
        self.cancel_name_button.setFixedHeight(42)
        self.cancel_name_button.setFixedWidth(120)
        self.cancel_name_button.clicked.connect(self.cancel_edit_name)
        self.cancel_name_button.setStyleSheet(f"""
            QPushButton#cancelNameButton {{
                background-color: rgba(200, 182, 226, 0.2);
                border: 2px solid rgba(200, 182, 226, 0.4);
                border-radius: 12px;
                color: #6C4A8B;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#cancelNameButton:hover {{
                background-color: rgba(200, 182, 226, 0.35);
                border-color: rgba(200, 182, 226, 0.6);
            }}
        """)
        self.cancel_name_button.hide()
        self.name_buttons_layout.addWidget(self.cancel_name_button)
        
        self.save_name_button = QPushButton("Сохранить")
        self.save_name_button.setObjectName("saveNameButton")
        self.save_name_button.setFixedHeight(42)
        self.save_name_button.setFixedWidth(120)
        self.save_name_button.clicked.connect(self.save_name_changes_inline)
        self.save_name_button.setStyleSheet(f"""
            QPushButton#saveNameButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['accent']},
                    stop:1 {colors['accent_alt']});
                border: none;
                border-radius: 12px;
                color: white;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#saveNameButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['accent_alt']},
                    stop:1 {colors['accent']});
            }}
        """)
        save_shadow = QGraphicsDropShadowEffect()
        save_shadow.setBlurRadius(8)
        save_shadow.setXOffset(0)
        save_shadow.setYOffset(2)
        save_shadow.setColor(QColor(108, 74, 139, 80))
        self.save_name_button.setGraphicsEffect(save_shadow)
        self.save_name_button.hide()
        self.name_buttons_layout.addWidget(self.save_name_button)
        
        profile_main_layout.addLayout(self.name_buttons_layout)
        layout.addWidget(profile_main_card)
        
        # === СТАТИСТИКА (3 виджета: всего писем, достижения, дни в приложении) ===
        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 20, 0, 0)
        stats_row.setSpacing(24)
        
        # Всего писем
        total_emails_card = QFrame()
        total_emails_card.setObjectName("statCard")
        total_emails_card.setStyleSheet(f"""
            QFrame#statCard {{
                background: transparent;
                border: none;
                border-radius: 16px;
                padding: 20px 28px;
                min-height: 100px;
            }}
        """)
        total_emails_layout = QVBoxLayout()
        total_emails_layout.setContentsMargins(0, 0, 0, 0)
        total_emails_layout.setSpacing(6)
        total_emails_card.setLayout(total_emails_layout)
        
        total_emails_label = QLabel(self.tr("total_sent"))
        total_emails_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        total_emails_label.setStyleSheet("color: #9A90B8; background: transparent;")
        total_emails_layout.addWidget(total_emails_label)
        
        self.total_emails_value = QLabel("0")
        self.total_emails_value.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.total_emails_value.setStyleSheet("color: #6C4A8B; background: transparent;")
        total_emails_layout.addWidget(self.total_emails_value)
        
        stats_row.addWidget(total_emails_card)
        
        # Достижения
        achievements_stat_card = QFrame()
        achievements_stat_card.setObjectName("statCard")
        achievements_stat_card.setStyleSheet(f"""
            QFrame#statCard {{
                background: transparent;
                border: none;
                border-radius: 16px;
                padding: 20px 28px;
                min-height: 100px;
            }}
        """)
        achievements_stat_card.mousePressEvent = lambda e: self.open_achievements_page()
        achievements_stat_card.setCursor(Qt.CursorShape.PointingHandCursor)
        achievements_stat_layout = QVBoxLayout()
        achievements_stat_layout.setContentsMargins(0, 0, 0, 0)
        achievements_stat_layout.setSpacing(6)
        achievements_stat_card.setLayout(achievements_stat_layout)
        
        achievements_stat_label = QLabel(self.tr("achievements"))
        achievements_stat_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        achievements_stat_label.setStyleSheet("color: #9A90B8; background: transparent;")
        achievements_stat_layout.addWidget(achievements_stat_label)
        
        self.achievements_stat_value = QLabel("0/10")
        self.achievements_stat_value.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.achievements_stat_value.setStyleSheet("color: #6C4A8B; background: transparent;")
        achievements_stat_layout.addWidget(self.achievements_stat_value)
        
        stats_row.addWidget(achievements_stat_card, 1)  # Растягиваем
        
        # Дни в приложении (с огоньком если >3)
        days_card = QFrame()
        days_card.setObjectName("statCard")
        days_card.setStyleSheet(f"""
            QFrame#statCard {{
                background: transparent;
                border: none;
                border-radius: 16px;
                padding: 20px 28px;
                min-height: 100px;
            }}
        """)
        days_layout = QVBoxLayout()
        days_layout.setContentsMargins(0, 0, 0, 0)
        days_layout.setSpacing(6)
        days_card.setLayout(days_layout)
        
        days_label = QLabel(self.tr("days_in_app"))
        days_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        days_label.setStyleSheet("color: #9A90B8; background: transparent;")
        days_layout.addWidget(days_label)
        
        days_value_layout = QHBoxLayout()
        days_value_layout.setContentsMargins(0, 0, 0, 0)
        days_value_layout.setSpacing(4)
        
        self.days_value = QLabel("—")
        self.days_value.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.days_value.setStyleSheet("color: #6C4A8B; background: transparent;")
        days_value_layout.addWidget(self.days_value)
        
        self.fire_icon = QLabel("●")
        self.fire_icon.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.fire_icon.setStyleSheet("color: #6C4A8B; background: transparent;")
        self.fire_icon.hide()  # Скрываем по умолчанию
        days_value_layout.addWidget(self.fire_icon)
        days_value_layout.addStretch()
        
        days_layout.addLayout(days_value_layout)
        
        stats_row.addWidget(days_card, 1)  # Растягиваем
        
        stats_widget = QWidget()
        stats_widget.setLayout(stats_row)
        layout.addWidget(stats_widget)
        
        layout.addStretch()

    
    def mousePressEvent(self, event):
        """Обработчик клика мыши для отмены редактирования при клике вне полей"""
        if self.is_editing_name:
            # Получаем виджет под курсором
            widget_under_mouse = self.childAt(event.pos())
            
            # Проверяем, что клик был не на полях редактирования или кнопках
            clicked_on_edit_widget = False
            
            # Проверяем прямые клики на виджеты (если поля редактирования существуют)
            if widget_under_mouse and hasattr(self, 'first_name_input') and hasattr(self, 'last_name_input'):
                parent = widget_under_mouse
                while parent:
                    if (parent == self.first_name_input or 
                        parent == self.last_name_input or
                        parent == self.save_name_button or
                        parent == self.cancel_name_button):
                        clicked_on_edit_widget = True
                        break
                    parent = parent.parentWidget()
            
            # Проверяем геометрию
            if not clicked_on_edit_widget and hasattr(self, 'first_name_input') and hasattr(self, 'last_name_input'):
                if (self.first_name_input.geometry().contains(event.pos()) or
                    self.last_name_input.geometry().contains(event.pos()) or
                    self.save_name_button.geometry().contains(event.pos()) or
                    self.cancel_name_button.geometry().contains(event.pos())):
                    clicked_on_edit_widget = True
            
            if not clicked_on_edit_widget:
                # Убираем фокус с полей ввода (если они существуют)
                if hasattr(self, 'first_name_input'):
                    self.first_name_input.clearFocus()
                if hasattr(self, 'last_name_input'):
                    self.last_name_input.clearFocus()
                # Небольшая задержка, чтобы кнопки успели обработать клик
                QTimer.singleShot(50, self.cancel_edit_name)
        
        super().mousePressEvent(event)
    
    def update_google_status(self):
        """Обновляет статус Google аккаунта в UI (теперь только для настроек)"""
        # Google аккаунт перемещен в настройки, этот метод больше не используется в профиле
        pass
    
    def load_user_info(self):
        """Загружает информацию о пользователе"""
        user_info = self._get_funcs()['get_user_info']()
        if user_info:
            # Обрабатываем разное количество элементов (може быть 2-7, теперь с username и current_status)
            # Порядок в get_user_info: (first_name, last_name, phone_number, created_at, avatar_path, username, current_status)
            if len(user_info) >= 7:
                first_name, last_name, phone_number, created_at, avatar_path, username, current_status = user_info
            elif len(user_info) >= 6:
                first_name, last_name, phone_number, created_at, avatar_path, username = user_info
                current_status = ''
            elif len(user_info) >= 5:
                first_name, last_name, phone_number, created_at, avatar_path = user_info
                username = None
                current_status = ''
            elif len(user_info) >= 4:
                first_name, last_name, phone_number, created_at = user_info
                avatar_path = None
                username = None
                current_status = ''
            elif len(user_info) >= 3:
                first_name, last_name, phone_number = user_info
                created_at = None
                avatar_path = None
                username = None
                current_status = ''
            else:
                first_name, last_name = user_info
                phone_number = ''
                created_at = None
                avatar_path = None
                username = None
                current_status = ''
            
            # Если username не получен, получаем его отдельно
            if not username:
                username = self._get_funcs()['get_current_username']()
            
            print(f"[DEBUG] load_user_info: username={username}, avatar_path={avatar_path}, len(user_info)={len(user_info) if user_info else 0}")
            # Загружаем никнейм
            if hasattr(self, 'nickname_label'):
                username = self._get_funcs()['get_current_username']()
                if username:
                    self.nickname_label.setText(username)
                else:
                    self.nickname_label.setText(f"{first_name} {last_name}" if first_name or last_name else "—")
            
            # Обновляем всего писем
            if hasattr(self, 'total_emails_value'):
                username = user_info[5] if len(user_info) >= 6 else self._get_funcs()['get_current_username']()
                if username:
                    history = self._get_funcs()['get_email_history'](username)
                    total_sent = len(history)
                    self.total_emails_value.setText(str(total_sent))
                else:
                    self.total_emails_value.setText("0")
            
            # Обновляем достижения
            if hasattr(self, 'achievements_stat_value'):
                username = user_info[5] if len(user_info) >= 6 else self._get_funcs()['get_current_username']()
                if username:
                    history = self._get_funcs()['get_email_history'](username)
                    friends_count = len(self._get_funcs()['get_friends'](username))
                    total_sent = len(history)
                    
                    # Получаем информацию о Google аккаунте и профиле
                    has_google = self._get_funcs()['get_google_account_email'](username) is not None if username else False
                    user_info_full = self._get_funcs()['get_user_info'](username)
                    has_profile = False
                    if user_info_full and len(user_info_full) >= 2:
                        first_name, last_name = user_info_full[0], user_info_full[1]
                        phone_number = user_info_full[2] if len(user_info_full) > 2 else ''
                        if username:
                            conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                            cursor = conn.cursor()
                            try:
                                cursor.execute('SELECT about_me_profile FROM auth_users WHERE username = ?', (username,))
                                result = cursor.fetchone()
                                if result and result[0]:
                                    has_profile = True
                            except:
                                pass
                            conn.close()
                        has_profile = has_profile and bool(first_name and last_name and phone_number)
                    
                    unlocked = 0
                    if total_sent >= 1:
                        unlocked += 1
                    if friends_count >= 1:
                        unlocked += 1
                    if total_sent >= 10:
                        unlocked += 1
                    if total_sent >= 25:
                        unlocked += 1
                    if total_sent >= 50:
                        unlocked += 1
                    if total_sent >= 100:
                        unlocked += 1
                    unlocked += 1  # AI user (всегда разблокировано)
                    if has_google:
                        unlocked += 1
                    if has_profile:
                        unlocked += 1
                    
                    self.achievements_stat_value.setText(f"{unlocked}/10")
                else:
                    self.achievements_stat_value.setText("0/10")
            
            # Обновляем дни в приложении (с огоньком если >3)
            if hasattr(self, 'days_value'):
                username = user_info[5] if len(user_info) >= 6 else self._get_funcs()['get_current_username']()
                if username:
                    days = self._get_funcs()['get_days_in_app'](username)
                    self.days_value.setText(str(days))
                    # Показываем огонек если больше 3 дней
                    if hasattr(self, 'fire_icon'):
                        if days > 3:
                            self.fire_icon.show()
                        else:
                            self.fire_icon.hide()
                else:
                    self.days_value.setText("—")
                    if hasattr(self, 'fire_icon'):
                        self.fire_icon.hide()
            
            # Обновляем статус онлайн/офлайн
            if hasattr(self, 'status_label'):
                username = user_info[5] if len(user_info) >= 6 else self._get_funcs()['get_current_username']()
                if username:
                    is_online, last_seen = self._get_funcs()['get_user_online_status'](username)
                    status_text = self.tr("online") if is_online else self.tr("offline")
                    status_color = "#34d399" if is_online else "#86868B"
                    self.status_label.setText(f"● {status_text}")
                    self.status_label.setStyleSheet(f"color: {status_color}; background: transparent; font-size: 11px; font-weight: 500;")
            
            # Обновляем статус сети возле аватара
            if hasattr(self, 'avatar_status_indicator'):
                username = user_info[5] if len(user_info) >= 6 else self._get_funcs()['get_current_username']()
                if username:
                    is_online, last_seen = self._get_funcs()['get_user_online_status'](username)
                    status_color = "#34d399" if is_online else "#86868B"
                    self.avatar_status_indicator.setStyleSheet(f"""
                        QLabel#avatarStatusIndicator {{
                            background: {status_color};
                            border-radius: 10px;
                            border: none;
                            padding: 0px;
                        }}
                    """)
            
            if hasattr(self, 'phone_input'):
                # Сохраняем реальный номер для использования в update_phone_display
                self._real_phone_number = phone_number if phone_number else ''
                # Номер по умолчанию скрыт
                self.phone_is_visible = False
                # Обновляем отображение номера (скрытый по умолчанию)
                self.update_phone_display()
            
            # Google аккаунт теперь в настройках
            
            # Загружаем "О себе" из базы данных (отдельно от "Качества")
            if hasattr(self, 'about_me_label'):
                username = self._get_funcs()['get_current_username']()
                about_me_text = ''
                if username:
                    conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                    cursor = conn.cursor()
                    try:
                        # "О себе" хранится в отдельном поле about_me_profile
                        cursor.execute('SELECT about_me_profile FROM auth_users WHERE username = ?', (username,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            about_me_text = result[0]
                        # Если нет about_me_profile, используем старый about_me (для совместимости)
                        if not about_me_text:
                            cursor.execute('SELECT about_me FROM auth_users WHERE username = ?', (username,))
                            result = cursor.fetchone()
                            if result and result[0]:
                                about_me_text = result[0]
                    except Exception:
                        # Если поле не существует, создаем его
                        try:
                            cursor.execute('ALTER TABLE auth_users ADD COLUMN about_me_profile TEXT DEFAULT ""')
                            conn.commit()
                        except:
                            pass
                    conn.close()
                # Загружаем текст "О себе" в input (больше не используем label)
                if hasattr(self, 'about_me_input'):
                    self.about_me_input.setPlainText(about_me_text if about_me_text else self.tr("no_data"))
                    # Обновляем original_about_me_text для автосохранения
                    self.original_about_me_text = about_me_text if about_me_text else ""
            
            # Обновляем дату регистрации
            if hasattr(self, 'registration_date_label'):
                created_at_value = created_at
                if created_at_value:
                    try:
                        if isinstance(created_at_value, str):
                            if ' ' in created_at_value:
                                date_str = created_at_value.split(' ')[0]
                            else:
                                date_str = created_at_value
                            try:
                                reg_dt = datetime.strptime(date_str, '%Y-%m-%d')
                                formatted_date = reg_dt.strftime('%d.%m.%Y')
                            except:
                                try:
                                    reg_dt = datetime.strptime(date_str, '%d.%m.%Y')
                                    formatted_date = date_str
                                except:
                                    formatted_date = date_str
                        else:
                            formatted_date = created_at_value.strftime('%d.%m.%Y')
                        self.registration_date_label.setText(formatted_date)
                    except:
                        self.registration_date_label.setText(str(created_at_value) if created_at_value else "—")
                else:
                    self.registration_date_label.setText("—")
            
            # Обновляем дни в приложении
            if hasattr(self, 'profile_days_label'):
                username = self._get_funcs()['get_current_username']()
                days = self._get_funcs()['get_days_in_app'](username)
                days_text = str(days)
                if days >= 3:
                    days_text = f"{days}"
                    # Устанавливаем оранжевый цвет для стрика
                    self.profile_days_label.setStyleSheet(f"""
                        color: #FF6B35;
                        font-size: 26px;
                        font-weight: bold;
                        background: transparent;
                    """)
                else:
                    self.profile_days_label.setStyleSheet("color: #6C4A8B; background: transparent; font-size: 26px;")
                self.profile_days_label.setText(days_text)
            
            # Обновляем аватар
            # Убеждаемся, что avatar_path правильно извлечен
            if not avatar_path:
                # Если avatar_path не был извлечен, пытаемся получить его напрямую из БД
                if not username:
                    username = self._get_funcs()['get_current_username']()
                
                if username:
                    conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                    cursor = conn.cursor()
                    try:
                        cursor.execute('SELECT avatar_path FROM auth_users WHERE username = ?', (username,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            avatar_path = result[0]
                            print(f"[DEBUG] Аватар загружен из БД для {username}: {avatar_path}")
                        else:
                            print(f"[DEBUG] Аватар не найден в БД для {username}")
                    except Exception as e:
                        print(f"[DEBUG] Ошибка при загрузке аватара из БД: {e}")
                        import traceback
                        traceback.print_exc()
                    finally:
                        conn.close()
            else:
                print(f"[DEBUG] Аватар загружен из user_info для {username}: {avatar_path}")
            
            # Получаем рамку
            frame_path = self.get_user_frame_path(username) if username else None
            # Обновляем отображение с задержкой, чтобы карточка успела получить размер
            # Используем несколько попыток для надежности при загрузке
            self.update_avatar_display(avatar_path, first_name, last_name, frame_path)
            # Дополнительные попытки обновления для исправления бага с половиной карточки
            QTimer.singleShot(100, lambda: self.update_avatar_display(avatar_path, first_name, last_name, frame_path))
            QTimer.singleShot(300, lambda: self.update_avatar_display(avatar_path, first_name, last_name, frame_path))
            QTimer.singleShot(500, lambda: (
                self.update_avatar_display(avatar_path, first_name, last_name, frame_path),
                self._update_profile_card_mask() if hasattr(self, '_update_profile_card_mask') else None
            ))
            
            # Метки активности больше не отображаются в профиле
            
            # Обновляем счетчик достижений
            if hasattr(self, 'achievements_count_label'):
                self.update_achievements_count()
    
    # Методы редактирования "О себе" удалены по требованию пользователя
    
    def open_achievements_page(self):
        """Открывает страницу достижений"""
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.stacked_widget.setCurrentIndex(5)  # Индекс страницы достижений
    
    def update_achievements_count(self):
        """Обновляет счетчик разблокированных достижений"""
        if not hasattr(self, 'achievements_count_label'):
            return
        
        username = self._get_funcs()['get_current_username']()
        if not username:
            self.achievements_count_label.setText("0/10")
            return
        
        history = self._get_funcs()['get_email_history']()
        total_sent = len(history)
        friends_count = len(self._get_funcs()['get_friends'](username))
        has_google = self._get_funcs()['get_google_account_email'](username) is not None if username else False
        
        user_info = self._get_funcs()['get_user_info']()
        has_profile = False
        if user_info and len(user_info) >= 2:
            first_name, last_name = user_info[0], user_info[1]
            phone_number = user_info[2] if len(user_info) > 2 else ''
            if username:
                conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                cursor = conn.cursor()
                try:
                    cursor.execute('SELECT about_me_profile FROM auth_users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        has_profile = True
                except:
                    pass
                conn.close()
            has_profile = has_profile and bool(first_name and last_name and phone_number)
        
        unlocked = 0
        if total_sent >= 1:
            unlocked += 1
        if friends_count >= 1:
            unlocked += 1
        if total_sent >= 10:
            unlocked += 1
        if total_sent >= 25:
            unlocked += 1
        if total_sent >= 50:
            unlocked += 1
        if total_sent >= 100:
            unlocked += 1
        unlocked += 1  # AI user (всегда разблокировано)
        if has_google:
            unlocked += 1
        if has_profile:
            unlocked += 1
        
        self.achievements_count_label.setText(f"{unlocked}/10")
    
    def toggle_phone_visibility(self):
        """Переключает видимость номера телефона"""
        self.phone_is_visible = not self.phone_is_visible
        self.update_phone_display()
    
    def update_phone_display(self):
        """Обновляет отображение номера телефона (скрытый или полный)"""
        if hasattr(self, 'phone_input') and hasattr(self, 'show_phone_button'):
            # Используем сохраненный реальный номер или получаем из БД
            if not hasattr(self, '_real_phone_number'):
                user_info = self._get_funcs()['get_user_info']()
                if user_info and len(user_info) >= 3:
                    self._real_phone_number = user_info[2] if user_info[2] else ''
                else:
                    self._real_phone_number = ''
            
            phone_number = self._real_phone_number
            
            if phone_number:
                if self.phone_is_visible:
                    # Показываем полный номер
                    self.phone_input.setText(phone_number)
                    self.show_phone_button.setText(self.tr("hide_phone"))
                else:
                    # Показываем только последние 2 цифры (по умолчанию скрыт)
                    if len(phone_number) >= 2:
                        masked = "*" * (len(phone_number) - 2) + phone_number[-2:]
                    else:
                        masked = "*" * len(phone_number)
                    self.phone_input.setText(masked)
                    self.show_phone_button.setText(self.tr("show_phone"))
            else:
                self.phone_input.setText("")
                self.show_phone_button.setText(self.tr("show_phone"))
    
    def edit_name(self):
        """Включает режим редактирования имени"""
        # Редактирование имени теперь происходит в настройках
        # Открываем настройки с секцией "Данные"
        if hasattr(self, 'main_window') and self.main_window:
            if hasattr(self.main_window, 'show_settings'):
                self.main_window.show_settings()
                # Переключаем на секцию "Данные"
                if hasattr(self.main_window, 'settings_dialog') and self.main_window.settings_dialog:
                    if hasattr(self.main_window.settings_dialog, 'switch_section'):
                        self.main_window.settings_dialog.switch_section("data")
    
    def cancel_edit_name(self):
        """Отменяет редактирование и возвращает исходные значения"""
        # Если поля редактирования существуют (старый дизайн), обрабатываем их
        if hasattr(self, 'first_name_input') and hasattr(self, 'last_name_input'):
            user_info = self._get_funcs()['get_user_info']()
            if user_info:
                if len(user_info) >= 2:
                    first_name, last_name = user_info[0], user_info[1]
                else:
                    first_name, last_name = user_info
                self.first_name_input.setText(first_name)
                self.last_name_input.setText(last_name)
            
            # Убираем фокус и подсветку
            self.first_name_input.clearFocus()
            self.last_name_input.clearFocus()
            self.first_name_input.setStyleSheet(f"""
                QLineEdit {{
                    color: #6C4A8B;
                    background: transparent;
                    border: none;
                    padding: 0px;
                }}
            """)
            self.last_name_input.setStyleSheet(f"""
                QLineEdit {{
                    color: #6C4A8B;
                    background: transparent;
                    border: none;
                    padding: 0px;
                }}
            """)
            
            # Возвращаем в режим только чтения
            self.first_name_input.setReadOnly(True)
            self.last_name_input.setReadOnly(True)
            
            self.is_editing_name = False
            
            # Скрываем кнопки
            if hasattr(self, 'save_name_button'):
                self.save_name_button.hide()
            if hasattr(self, 'cancel_name_button'):
                self.cancel_name_button.hide()
        
        # Показываем кнопку показать/скрыть телефон обратно
        if hasattr(self, 'show_phone_button') and not self.is_editing_phone:
            self.show_phone_button.show()
    
    def edit_phone(self):
        """Включает режим редактирования телефона"""
        self.is_editing_phone = True
        
        # Сохраняем реальный номер перед редактированием
        if not hasattr(self, '_real_phone_number'):
            user_info = self._get_funcs()['get_user_info']()
            if user_info and len(user_info) >= 3:
                self._real_phone_number = user_info[2] if user_info[2] else ''
            else:
                self._real_phone_number = ''
        
        # Показываем реальный номер при редактировании
        self.phone_input.setText(self._real_phone_number)
        self.phone_input.setReadOnly(False)
        self.phone_input.setStyleSheet("""
            QLineEdit {
                color: #2D1B3D;
                background-color: rgba(240, 230, 250, 0.8);
                border: 2px solid rgba(200, 182, 226, 0.5);
                border-radius: 12px;
                padding: 8px 16px;
                font-size: 20px;
                font-weight: bold;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid #9C89B8;
            }
        """)
        
        # Скрываем кнопку показать/скрыть при редактировании
        if hasattr(self, 'show_phone_button'):
            self.show_phone_button.hide()
        
        self.save_phone_button.show()
        self.cancel_phone_button.show()
        self.phone_input.setFocus()
        self.phone_input.selectAll()
    
    def cancel_edit_phone(self):
        """Отменяет редактирование телефона"""
        # Восстанавливаем реальный номер
        if not hasattr(self, '_real_phone_number'):
            user_info = self._get_funcs()['get_user_info']()
            if user_info and len(user_info) >= 3:
                self._real_phone_number = user_info[2] if user_info[2] else ''
            else:
                self._real_phone_number = ''
        
        self.phone_input.clearFocus()
        self.phone_input.setStyleSheet("""
            QLineEdit {
                color: #2D1B3D;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.phone_input.setReadOnly(True)
        self.is_editing_phone = False
        self.save_phone_button.hide()
        self.cancel_phone_button.hide()
        
        # Показываем кнопку показать/скрыть обратно
        if hasattr(self, 'show_phone_button'):
            self.show_phone_button.show()
        
        # Обновляем отображение (номер будет скрыт)
        self.update_phone_display()
    
    def save_phone_changes(self):
        """Сохраняет изменения телефона"""
        phone_number = self.phone_input.text().strip()
        
        # Сохраняем реальный номер
        self._real_phone_number = phone_number
        
        # Получаем username
        username = self._get_funcs()['get_current_username']()
        if not username:
            QMessageBox.warning(self, self.tr("error"), "Не удалось определить пользователя")
            return
        
        # Загружаем текущие данные из БД, чтобы не потерять аватар и имя
        conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT first_name, last_name, avatar_path FROM auth_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            if result:
                first_name = result[0] if result[0] else ""
                last_name = result[1] if result[1] else ""
                avatar_path = result[2] if result[2] else None
            else:
                first_name = ""
                last_name = ""
                avatar_path = None
        except Exception as e:
            print(f"[DEBUG] Ошибка при загрузке данных пользователя: {e}")
            first_name = ""
            last_name = ""
            avatar_path = None
        finally:
            conn.close()
        
        # Сохраняем с номером телефона, сохраняя дату регистрации и аватар с явным указанием username
        self._get_funcs()['save_user_info'](first_name, last_name, phone_number, preserve_registration_date=True, avatar_path=avatar_path, username=username)
        
        # Также обновляем в auth_users, сохраняя аватар
        conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE auth_users 
                SET phone_number = ?, avatar_path = ?
                WHERE username = ?
            ''', (phone_number, avatar_path, username))
            conn.commit()
            print(f"[DEBUG] Телефон и аватар сохранены для {username}, аватар: {avatar_path}")
        except Exception as e:
            print(f"[DEBUG] Ошибка при сохранении телефона: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        # Сразу делаем номер скрытым после сохранения
        self.phone_is_visible = False
        
        self.phone_input.clearFocus()
        self.phone_input.setStyleSheet("""
            QLineEdit {
                color: #2D1B3D;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.phone_input.setReadOnly(True)
        self.is_editing_phone = False
        self.save_phone_button.hide()
        self.cancel_phone_button.hide()
        
        # Показываем кнопку показать/скрыть обратно
        if hasattr(self, 'show_phone_button'):
            self.show_phone_button.show()
        
        # Обновляем отображение (номер будет скрыт)
        self.update_phone_display()
    
    # Метод open_settings_with_data удален - окно "данные" больше не используется
    
    def update_about_me_widgets_size(self):
        """Обновляет размеры виджетов в контейнере 'О себе'"""
        # Больше не нужно, так как используем layout
        pass
    
    def enter_edit_mode(self):
        """Входит в режим редактирования профиля"""
        if self.is_edit_mode:
            self.exit_edit_mode()
            return
        
        self.is_edit_mode = True
        
        # Сохраняем исходный размер карточки профиля для правильного восстановления
        if self.original_profile_card_size is None:
            self.original_profile_card_size = self.profile_main_card.size()
        
        # Устанавливаем минимальный и максимальный размер, чтобы карточка не изменялась
        current_size = self.profile_main_card.size()
        if current_size.width() > 0 and current_size.height() > 0:
            self.profile_main_card.setMinimumSize(current_size)
            self.profile_main_card.setMaximumSize(current_size)
        
        # СОХРАНЯЕМ ИСХОДНЫЕ ЗНАЧЕНИЯ для отката изменений
        # Сохраняем исходную рамку профиля
        self.original_frame_path = getattr(self, '_current_frame_path', None) or ""
        # Сохраняем исходный аватар (путь к изображению аватара)
        username = self._get_funcs()['get_current_username']()
        if username:
            try:
                conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                cursor = conn.cursor()
                cursor.execute('SELECT avatar_path FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                self.original_avatar_path = result[0] if result and result[0] else None
                conn.close()
            except:
                self.original_avatar_path = None
        else:
            self.original_avatar_path = None
        
        # Убираем шестеренку
        self.settings_btn.hide()
        
        # Делаем "О себе" редактируемым (без смещения текста)
        if hasattr(self, 'about_me_input'):
            original_text = self.about_me_input.toPlainText()
            if original_text == "—" or original_text == self.tr("no_data"):
                original_text = ""
            self.original_about_me_text = original_text
            
            # Устанавливаем отступы документа в 0 ДО изменения ReadOnly
            self.about_me_input.document().setDocumentMargin(0)
            
            # Показываем счетчик (только в режиме редактирования)
            self.about_me_counter.show()
            self.update_about_me_counter()
            
            # Разрешаем редактирование
            self.about_me_input.setReadOnly(False)
            
            # Снова устанавливаем отступы документа в 0 после изменения ReadOnly
            self.about_me_input.document().setDocumentMargin(0)
            
            # Устанавливаем фокус с небольшой задержкой, чтобы layout успел стабилизироваться
            QTimer.singleShot(10, lambda: self.about_me_input.setFocus() if hasattr(self, 'about_me_input') else None)
        
        # Устанавливаем event filter для показа карандаша при наведении на аватар
        self.avatar_label.installEventFilter(self)
        self.avatar_wrapper.installEventFilter(self)
        
        # Создаем вкладки справа от рамки профиля
        self.create_edit_mode_tabs()
    
    def exit_edit_mode(self):
        """Выходит из режима редактирования и ОТКАТЫВАЕТ все изменения"""
        if not self.is_edit_mode:
            return
        
        self.is_edit_mode = False
        
        # ОТКАТЫВАЕМ ВСЕ ИЗМЕНЕНИЯ к исходным значениям
        
        # Откатываем рамку профиля и аватар
        username = self._get_funcs()['get_current_username']()
        if username:
            # Получаем данные пользователя для отката
            try:
                conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                cursor = conn.cursor()
                cursor.execute('SELECT first_name, last_name FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                first_name = result[0] if result and result[0] else ""
                last_name = result[1] if result and result[1] else ""
                
                # Откатываем рамку
                original_frame = getattr(self, 'original_frame_path', None) if hasattr(self, 'original_frame_path') else None
                # Восстанавливаем _current_frame_path к исходному значению
                self._current_frame_path = original_frame if original_frame else None
                
                # Откатываем аватар
                if hasattr(self, 'original_avatar_path'):
                    avatar_path = self.original_avatar_path
                    self._current_avatar_path = avatar_path
                else:
                    cursor.execute('SELECT avatar_path FROM auth_users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    avatar_path = result[0] if result and result[0] else None
                
                # Очищаем временные переменные
                self._pending_frame_path = None
                self._pending_avatar_path = None
                
                conn.close()
                
                # Восстанавливаем отображение с исходными значениями
                self.update_avatar_display(avatar_path, first_name, last_name, original_frame)
            except:
                pass
        
        # Откатываем текст "О себе"
        if hasattr(self, 'about_me_input') and hasattr(self, 'original_about_me_text'):
            original_text = self.original_about_me_text if self.original_about_me_text else "—"
            self.about_me_input.setPlainText(original_text)
            self.about_me_input.setReadOnly(True)
            self.about_me_input.document().setDocumentMargin(0)
            # Скрываем счетчик при выходе из режима редактирования
            self.about_me_counter.hide()
        
        # Восстанавливаем размер карточки профиля к исходному
        if self.original_profile_card_size:
            original_size = self.original_profile_card_size
            # Сбрасываем фиксированные размеры и восстанавливаем исходные
            self.profile_main_card.setMinimumSize(0, 0)
            self.profile_main_card.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX
            # Восстанавливаем исходный размер
            self.profile_main_card.resize(original_size)
        
        # Показываем шестеренку
        self.settings_btn.show()
        
        # Удаляем event filter для аватара
        if hasattr(self, 'avatar_label'):
            self.avatar_label.removeEventFilter(self)
        if hasattr(self, 'avatar_wrapper'):
            self.avatar_wrapper.removeEventFilter(self)
        # Скрываем карандаш
        if hasattr(self, 'avatar_edit_icon'):
            self.avatar_edit_icon.hide()
        
        # Удаляем вкладки
        self.remove_edit_mode_tabs()
    
    def save_edit_changes(self):
        """Сохраняет все изменения (рамка, аватар, О себе) при нажатии галочки"""
        if not self.is_edit_mode:
            return
        
        username = self._get_funcs()['get_current_username']()
        if not username:
            QMessageBox.warning(self, self.tr("error"), "Не удалось определить пользователя")
            return
        
        # Сохраняем рамку профиля
        pending_frame = getattr(self, '_pending_frame_path', None)
        current_frame_path = pending_frame if pending_frame is not None else (getattr(self, '_current_frame_path', None) or "")
        # Нормализуем значения для сравнения: None и "" считаются одинаковыми (обе означают default)
        current_normalized = "" if not current_frame_path else current_frame_path
        original_frame_path = getattr(self, 'original_frame_path', None)
        original_normalized = "" if not original_frame_path else original_frame_path
        if current_normalized != original_normalized:
            self.save_frame_to_db(username, current_normalized if current_normalized else "")
        
        # Сохраняем аватар (если был изменен)
        pending_avatar = getattr(self, '_pending_avatar_path', None)
        if pending_avatar:
            if self.save_avatar_to_db(username, pending_avatar):
                self._current_avatar_path = pending_avatar
                self.original_avatar_path = pending_avatar
        
        # Сохраняем текст "О себе"
        if hasattr(self, 'about_me_input'):
            current_text = self.about_me_input.toPlainText().strip()
            if current_text != getattr(self, 'original_about_me_text', ''):
                # Сохраняем в БД напрямую
                try:
                    conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                    cursor = conn.cursor()
                    cursor.execute('UPDATE auth_users SET about_me_profile = ? WHERE username = ?', (current_text, username))
                    conn.commit()
                    conn.close()
                    # Обновляем original_about_me_text после сохранения
                    self.original_about_me_text = current_text if current_text else ""
                except Exception as e:
                    QMessageBox.warning(self, self.tr("error"), f"Не удалось сохранить: {e}")
                    return
        
        # Выходим из режима редактирования
        self.is_edit_mode = False
        
        # Возвращаем "О себе" в режим просмотра
        if hasattr(self, 'about_me_input'):
            self.about_me_input.setReadOnly(True)
            self.about_me_input.document().setDocumentMargin(0)
            # Скрываем счетчик при сохранении
            self.about_me_counter.hide()
        
        # Восстанавливаем размер карточки профиля
        if self.original_profile_card_size:
            original_size = self.original_profile_card_size
            # Сбрасываем фиксированные размеры и восстанавливаем исходные
            self.profile_main_card.setMinimumSize(0, 0)
            self.profile_main_card.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX
            # Восстанавливаем исходный размер
            self.profile_main_card.resize(original_size)
        
        # Показываем шестеренку
        self.settings_btn.show()
        
        # Удаляем event filter для аватара
        if hasattr(self, 'avatar_label'):
            self.avatar_label.removeEventFilter(self)
        if hasattr(self, 'avatar_wrapper'):
            self.avatar_wrapper.removeEventFilter(self)
        # Скрываем карандаш
        if hasattr(self, 'avatar_edit_icon'):
            self.avatar_edit_icon.hide()
        
        # Удаляем вкладки
        self.remove_edit_mode_tabs()
        
        # Сообщение об успешном сохранении убрано по требованию пользователя
    
    def create_edit_mode_tabs(self):
        """Создает вкладки справа от рамки профиля в режиме редактирования"""
        # Закладки должны быть только в окне профиля, а не поверх всего остального
        if not hasattr(self, 'profile_main_card'):
            return
        
        # Контейнер для вкладок (только в окне профиля, не поверх всего)
        self.edit_tabs_container = QFrame(self.profile_main_card)
        self.edit_tabs_container.setObjectName("editTabsContainer")
        self.edit_tabs_container.setStyleSheet("""
            QFrame#editTabsContainer {
                background: transparent;
                border: none;
            }
        """)
        tabs_layout = QVBoxLayout()
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(4)  # Уменьшен spacing между закладками (было 8)
        self.edit_tabs_container.setLayout(tabs_layout)
        
        # Верхняя вкладка - перелистывание страницы (рамки) - лиловая с треугольником
        # Используем монохромные символы, увеличиваем размер иконки
        frame_tab = TabButtonWithArrow("◉", self.edit_tabs_container)  # Монохромная иконка рамки
        frame_tab.setFixedSize(42, 28)  # Уменьшен размер закладок (было 52x32)
        frame_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        frame_tab.clicked.connect(self.show_frame_selection)
        # Убираем тень у вкладок
        frame_tab.setGraphicsEffect(None)
        tabs_layout.addWidget(frame_tab)
        
        # Средняя вкладка - сохранение (галочка) - должна быть выше крестика
        save_tab = TabButtonWithArrow("✓", self.edit_tabs_container)  # Монохромная иконка галочки
        save_tab.setFixedSize(42, 28)  # Уменьшен размер закладок (было 52x32)
        save_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        save_tab.clicked.connect(self.save_edit_changes)  # Сохраняет все изменения
        # Убираем тень у вкладок
        save_tab.setGraphicsEffect(None)
        tabs_layout.addWidget(save_tab)
        
        # Нижняя вкладка - выход (лиловая с треугольником) - должна быть снизу
        exit_tab = TabButtonWithArrow("✕", self.edit_tabs_container)  # Монохромная иконка выхода
        exit_tab.setFixedSize(42, 28)  # Уменьшен размер закладок (было 52x32)
        exit_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_tab.clicked.connect(self.exit_edit_mode)  # Откатывает изменения
        # Убираем тень у вкладок
        exit_tab.setGraphicsEffect(None)
        tabs_layout.addWidget(exit_tab)
        
        # Позиционируем СПРАВА от карточки - закладки выходят из-под рамки справа и приклеены
        # Используем локальные координаты относительно profile_main_card
        card_right = self.profile_main_card.rect().right()
        card_top = self.profile_main_card.rect().top()
        
        # Позиционируем закладки СПРАВА от рамки, ближе к краю
        tab_width = 42  # Уменьшен размер закладок (было 52)
        tab_height = 28  # Уменьшен размер закладок (было 32)
        spacing = 4  # Уменьшен spacing между закладками (было 6)
        additional_exit_spacing = 20  # Дополнительный отступ для закладки выхода
        
        # Позиция для верхней закладки (рамки) - относительно карточки профиля
        # Сдвигаем закладки правее (уменьшаем отступ от правого края)
        frame_tab_x = max(0, card_right - tab_width - 2)  # Уменьшен отступ с 5 до 2 - закладки правее
        frame_tab_y = card_top + 10  # Поднята еще выше для лучшего баланса
        
        # Вычисляем позицию контейнера с учетом дополнительного отступа для нижней закладки (теперь 3 закладки)
        container_height = tab_height * 3 + spacing * 2 + additional_exit_spacing  # 3 закладки + 2 spacing между ними
        # Позиционируем контейнер так, чтобы нижняя закладка была ниже и не выходила за пределы
        container_y = frame_tab_y
        # Убеждаемся, что контейнер не выходит за нижний край карточки
        card_bottom = self.profile_main_card.rect().bottom()
        if container_y + container_height > card_bottom:
            container_y = max(card_top + 5, card_bottom - container_height - 5)
        self.edit_tabs_container.setGeometry(frame_tab_x, container_y, tab_width, container_height)
        
        # Убеждаемся, что закладки видны - поднимаем их выше других элементов
        self.edit_tabs_container.show()
        self.edit_tabs_container.raise_()  # Поднимаем закладки, чтобы они были видны поверх содержимого
    
    def remove_edit_mode_tabs(self):
        """Удаляет вкладки режима редактирования"""
        if hasattr(self, 'edit_tabs_container') and self.edit_tabs_container:
            try:
                self.edit_tabs_container.deleteLater()
                self.edit_tabs_container = None
            except:
                pass
    
    
    
    def open_settings_with_overlay(self):
        """Открывает настройки с затемнением как в friends_page"""
        if not hasattr(self, 'main_window') or not self.main_window:
            return
        
        # Создаем overlay на главном окне
        if hasattr(self, 'settings_overlay') and self.settings_overlay:
            try:
                self.settings_overlay.deleteLater()
            except:
                pass
        
        main_window = self.main_window
        self.settings_overlay = QFrame(main_window)
        self.settings_overlay.setGeometry(0, 0, main_window.width(), main_window.height())
        self.settings_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
        self.settings_overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.settings_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        def close_overlay(e):
            if e.button() == Qt.MouseButton.LeftButton:
                try:
                    if hasattr(self, 'settings_overlay') and self.settings_overlay:
                        self.settings_overlay.deleteLater()
                        self.settings_overlay = None
                    if hasattr(self.main_window, 'settings_dialog') and self.main_window.settings_dialog:
                        try:
                            self.main_window.settings_dialog.close()
                        except:
                            pass
                except RuntimeError:
                    pass
        
        self.settings_overlay.mousePressEvent = close_overlay
        self.settings_overlay.show()
        self.settings_overlay.raise_()
        
        # Открываем настройки
        if hasattr(self.main_window, 'show_settings'):
            self.main_window.show_settings()
            # Переключаем на секцию "Данные"
            if hasattr(self.main_window, 'settings_dialog') and self.main_window.settings_dialog:
                if hasattr(self.main_window.settings_dialog, 'switch_section'):
                    self.main_window.settings_dialog.switch_section("data")
            
            # Закрываем overlay при закрытии диалога
            def on_dialog_closed():
                if hasattr(self, 'settings_overlay') and self.settings_overlay:
                    try:
                        self.settings_overlay.deleteLater()
                        self.settings_overlay = None
                    except:
                        pass
            
            # Подключаемся к сигналу закрытия диалога если он есть
            try:
                if hasattr(self.main_window.settings_dialog, 'finished'):
                    self.main_window.settings_dialog.finished.connect(on_dialog_closed)
            except:
                pass
    
    def save_name_changes_inline(self):
        """Сохраняет изменения имени прямо в карточке"""
        # Если поля редактирования существуют (старый дизайн), обрабатываем их
        if hasattr(self, 'first_name_input') and hasattr(self, 'last_name_input'):
            first_name = self.first_name_input.text().strip()
            last_name = self.last_name_input.text().strip()
            
            if not first_name or not last_name:
                QMessageBox.warning(self, self.tr("error"), self.tr("name_surname_empty"))
                return
        
        # Получаем текущий номер телефона и аватар
        username = self._get_funcs()['get_current_username']()
        if not username:
            QMessageBox.warning(self, self.tr("error"), "Не удалось определить пользователя")
            return
        
        # Загружаем текущие данные из БД, чтобы не потерять аватар
        conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT phone_number, avatar_path FROM auth_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            if result:
                phone_number = result[0] if result[0] else ''
                avatar_path = result[1] if result[1] else None
            else:
                phone_number = ''
                avatar_path = None
        except Exception as e:
            print(f"[DEBUG] Ошибка при загрузке данных пользователя: {e}")
            phone_number = ''
            avatar_path = None
        finally:
            conn.close()
        
        # Сохраняем в базу данных, сохраняя дату регистрации и аватар с явным указанием username
        self._get_funcs()['save_user_info'](first_name, last_name, phone_number, preserve_registration_date=True, avatar_path=avatar_path, username=username)
        
        # Дополнительно сохраняем напрямую в БД для надежности, чтобы аватар точно сохранился
        conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE auth_users 
                SET first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?
                WHERE username = ?
            ''', (first_name, last_name, phone_number, avatar_path, username))
            conn.commit()
            print(f"[DEBUG] Данные пользователя сохранены для {username}, аватар: {avatar_path}")
        except Exception as e:
            print(f"[DEBUG] Ошибка при сохранении данных пользователя: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        # Получаем рамку
        frame_path = self.get_user_frame_path(username) if username else None
        
        # Обновляем аватар с новыми инициалами
        self.update_avatar_display(avatar_path, first_name, last_name, frame_path)
        
        # Убираем фокус и подсветку
        self.first_name_input.clearFocus()
        self.last_name_input.clearFocus()
        self.first_name_input.setStyleSheet(f"""
            QLineEdit {{
                color: #6C4A8B;
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        self.last_name_input.setStyleSheet(f"""
            QLineEdit {{
                color: #6C4A8B;
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        
        # Возвращаем в режим только чтения
        self.first_name_input.setReadOnly(True)
        self.last_name_input.setReadOnly(True)
        self.is_editing_name = False
        
        # Скрываем кнопки
        if hasattr(self, 'save_name_button'):
            self.save_name_button.hide()
        if hasattr(self, 'cancel_name_button'):
            self.cancel_name_button.hide()
        
        # Показываем кнопку показать/скрыть телефон обратно
        if hasattr(self, 'show_phone_button') and not self.is_editing_phone:
            self.show_phone_button.show()
        
        # Обновляем имя в сайдбаре, если есть доступ к главному окну
        if self.main_window and hasattr(self.main_window, 'sidebar_widget'):
            # Находим виджет с именем в сайдбаре
            for widget in self.main_window.sidebar_widget.findChildren(QLabel):
                if widget.objectName() == "userNameLabel":
                    widget.setText(f"{first_name} {last_name}")
                    break
    
    def save_avatar_to_db(self, username, avatar_path):
        """Сохраняет аватар в БД и инвалидирует кеш"""
        if not username or not avatar_path:
            return False
        
        conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
        cursor = conn.cursor()
        try:
            # Проверяем, существует ли колонка avatar_path
            cursor.execute("PRAGMA table_info(auth_users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'avatar_path' not in columns:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN avatar_path TEXT')
                conn.commit()
            
            # Сохраняем аватар
            cursor.execute('''
                UPDATE auth_users 
                SET avatar_path = ?
                WHERE username = ?
            ''', (avatar_path, username))
            conn.commit()
            
            # Инвалидируем кеш профиля
            try:
                from email_app import _profile_cache
                if username in _profile_cache:
                    del _profile_cache[username]
            except:
                pass
            
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def show_frame_selection(self):
        """Показывает диалог выбора рамки"""
        # Получаем список доступных рамок из папки frames
        frames_dir = Path("frames")
        if not frames_dir.exists():
            frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Получаем список всех рамок
        available_frames = list(frames_dir.glob("*.png"))
        
        if not available_frames:
            QMessageBox.information(self, "Рамки", "Нет доступных рамок. Добавьте изображения в папку 'frames'.")
            return
        
        # Получаем username для проверки разблокировки рамок
        username = self._get_funcs()['get_current_username']()
        
        # Создаем диалог выбора рамки
        dialog = FrameSelectionDialog(available_frames, self, username=username)
        if dialog.exec():
            selected_frame = dialog.selected_frame
            # Проверяем на None и на "default" - оба должны проходить
            if selected_frame is not None:
                username = self._get_funcs()['get_current_username']()
                if not username:
                    QMessageBox.warning(self, self.tr("error"), "Не удалось определить пользователя")
                    return
                
                # В режиме редактирования применяем рамку только визуально, без сохранения в БД
                # Сохранение произойдет при нажатии галочки
                # Если selected_frame это "default", сохраняем пустую строку
                if selected_frame == "default" or selected_frame == "" or selected_frame is None:
                    frame_to_apply = ""
                else:
                    frame_to_apply = str(selected_frame)
                
                # Сохраняем выбранную рамку во временную переменную для применения при нажатии галочки
                self._pending_frame_path = frame_to_apply
                
                # Получаем данные пользователя для отображения
                user_info = self._get_funcs()['get_user_info'](username)
                if user_info:
                    first_name = user_info[0] if user_info[0] else ""
                    last_name = user_info[1] if user_info[1] else ""
                    avatar_path = user_info[4] if len(user_info) > 4 and user_info[4] else None
                else:
                    first_name = ""
                    last_name = ""
                    avatar_path = None
                
                # Обновляем отображение аватара с новой рамкой ВИЗУАЛЬНО (без сохранения в БД)
                self._current_frame_path = frame_to_apply if frame_to_apply else None
                self.update_avatar_display(avatar_path, first_name, last_name, str(selected_frame) if selected_frame != "default" else None)
    
    # Метод toggle_edit_about_me удален - редактирование "О себе" теперь только в режиме редактирования профиля
    
    def save_about_me(self):
        """Сохраняет текст 'О себе'"""
        text = self.about_me_input.toPlainText().strip()
        username = self._get_funcs()['get_current_username']()
        if not username:
            QMessageBox.warning(self, self.tr("error"), "Не удалось определить пользователя")
            return
        
        # Сохраняем в БД
        try:
            conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
            cursor = conn.cursor()
            cursor.execute('UPDATE auth_users SET about_me_profile = ? WHERE username = ?', (text, username))
            conn.commit()
            conn.close()
            
            # Обновляем отображение и оригинальный текст
            if hasattr(self, 'about_me_input'):
                self.about_me_input.setPlainText(text if text else "—")
            self.original_about_me_text = text
            self.has_unsaved_changes = False
            
            # Скрываем виджет несохраненных изменений
            if hasattr(self, 'unsaved_changes_widget'):
                self.unsaved_changes_widget.hide()
        except Exception as e:
            QMessageBox.warning(self, self.tr("error"), f"Не удалось сохранить: {e}")
    
    def cancel_edit_about_me(self):
        """Отменяет редактирование 'О себе' - возвращаем в режим только чтения"""
        if hasattr(self, 'about_me_input'):
            # Возвращаем в режим только чтения (выглядит как обычный текст)
            self.about_me_input.setReadOnly(True)
            # Скрываем счетчик
            self.about_me_counter.hide()
        # Скрываем виджет несохраненных изменений
        if hasattr(self, 'unsaved_changes_widget'):
            self.unsaved_changes_widget.hide()
        self.has_unsaved_changes = False
    
    def on_about_me_text_changed(self):
        """Обработчик изменения текста 'О себе' - автоматически сохраняет с задержкой"""
        # Обновляем счетчик только в режиме редактирования (он показывается только в этом режиме)
        if hasattr(self, 'is_edit_mode') and self.is_edit_mode:
            self.update_about_me_counter()
        
        # Скрываем виджет несохраненных изменений (больше не нужен)
        if hasattr(self, 'unsaved_changes_widget'):
            self.unsaved_changes_widget.hide()
        
        # Автоматически сохраняем с задержкой (debounce)
        if not hasattr(self, 'about_me_save_timer'):
            self.about_me_save_timer = QTimer()
            self.about_me_save_timer.setSingleShot(True)
            self.about_me_save_timer.timeout.connect(self.auto_save_about_me)
        
        # Перезапускаем таймер при каждом изменении (задержка 1 секунда после последнего изменения)
        self.about_me_save_timer.stop()
        self.about_me_save_timer.start(1000)  # Сохраняем через 1 секунду после последнего изменения
    
    def auto_save_about_me(self):
        """Автоматически сохраняет текст 'О себе' ТОЛЬКО если НЕ в режиме редактирования"""
        # Автосохранение отключено в режиме редактирования - сохраняется только при нажатии галочки
        if self.is_edit_mode:
            return
        if hasattr(self, 'about_me_input') and not self.about_me_input.isReadOnly():
            current_text = self.about_me_input.toPlainText()
            # Сохраняем только если текст изменился
            if current_text != getattr(self, 'original_about_me_text', ''):
                self.save_about_me()
    
    def update_about_me_counter(self):
        """Обновляет счетчик символов для 'О себе' (вызывается только в режиме редактирования)"""
        text = self.about_me_input.toPlainText()
        char_count = len(text)
        max_chars = 110
        remaining = max_chars - char_count
        
        if char_count > max_chars:
            # Обрезаем текст
            self.about_me_input.setPlainText(text[:max_chars])
            char_count = max_chars
            remaining = 0
        
        self.about_me_counter.setText(f"{char_count}/{max_chars}")
        
        # Меняем цвет если приближаемся к лимиту
        if remaining < 20:
            self.about_me_counter.setStyleSheet("color: #EF4444; background: transparent;")
        else:
            self.about_me_counter.setStyleSheet("color: #86868B; background: transparent;")
    
    def show_unsaved_changes_widget(self):
        """Показывает виджет с вопросом сохранить или сбросить изменения"""
        if not hasattr(self, 'unsaved_changes_widget') or not self.unsaved_changes_widget:
            # Находим родительский контейнер профиля - используем главное окно для правильного позиционирования
            parent_widget = self.main_window if hasattr(self, 'main_window') and self.main_window else self
            
            self.unsaved_changes_widget = QFrame(parent_widget)
            self.unsaved_changes_widget.setObjectName("unsavedChangesWidget")
            self.unsaved_changes_widget.setStyleSheet("""
                QFrame#unsavedChangesWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.98),
                        stop:1 rgba(250, 245, 255, 0.98));
                    border: 2px solid rgba(200, 182, 226, 0.5);
                    border-radius: 16px;
                    padding: 16px;
                }
            """)
            
            widget_layout = QHBoxLayout()
            widget_layout.setContentsMargins(0, 0, 0, 0)
            widget_layout.setSpacing(16)
            
            warning_text = QLabel("У вас есть несохраненные изменения. Сохранить или сбросить?")
            warning_text.setFont(QFont("Segoe UI", 13))
            warning_text.setStyleSheet("color: #6C4A8B; background: transparent;")
            warning_text.setWordWrap(True)
            widget_layout.addWidget(warning_text, 1)
            
            reset_btn = QPushButton("Сброс")
            reset_btn.setFixedHeight(40)
            reset_btn.setFixedWidth(120)
            reset_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(200, 182, 226, 0.3);
                    border: 2px solid rgba(156, 137, 184, 0.4);
                    border-radius: 10px;
                    color: #6C4A8B;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(200, 182, 226, 0.5);
                    border-color: rgba(156, 137, 184, 0.6);
                }
            """)
            reset_btn.clicked.connect(self.reset_about_me_changes)
            widget_layout.addWidget(reset_btn)
            
            save_btn_widget = QPushButton("Сохранить")
            save_btn_widget.setFixedHeight(40)
            save_btn_widget.setFixedWidth(120)
            save_btn_widget.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #7A84F0, stop:1 #8B95FF);
                    border: none;
                    border-radius: 10px;
                    color: white;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #8B95FF, stop:1 #9CA5FF);
                }
            """)
            save_btn_widget.clicked.connect(self.save_about_me)
            widget_layout.addWidget(save_btn_widget)
            
            self.unsaved_changes_widget.setLayout(widget_layout)
            self.unsaved_changes_widget.hide()
        
        if self.has_unsaved_changes:
            # Позиционируем виджет под полем "О себе"
            if hasattr(self, 'about_me_input') and self.about_me_input.isVisible():
                about_me_global = self.about_me_input.mapToGlobal(self.about_me_input.rect().bottomLeft())
                if hasattr(self, 'main_window') and self.main_window:
                    parent_global = self.main_window.mapToGlobal(QPoint(0, 0))
                    x = about_me_global.x() - parent_global.x()
                    y = about_me_global.y() - parent_global.y() + 10
                    self.unsaved_changes_widget.setGeometry(x, y, 600, 70)
            self.unsaved_changes_widget.show()
            self.unsaved_changes_widget.raise_()
    
    def reset_about_me_changes(self):
        """Сбрасывает изменения 'О себе'"""
        self.about_me_input.setPlainText(self.original_about_me_text)
        self.update_about_me_counter()
        self.has_unsaved_changes = False
        if hasattr(self, 'unsaved_changes_widget'):
            self.unsaved_changes_widget.hide()
    
    def change_avatar_or_frame(self, event=None):
        """Метод больше не используется - аватар можно менять только через диалог 'Редактирование профиля'"""
        # Этот метод больше не вызывается - аватар можно менять только через show_profile_edit_dialog
        pass
    
    def change_avatar(self):
        """Открывает диалог выбора аватара"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("change_avatar_or_frame"))
        dialog.setFixedSize(400, 200)
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 20px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel(self.tr("what_to_change"))
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title)
        
        avatar_btn = QPushButton(self.tr("change_avatar"))
        avatar_btn.setFixedHeight(50)
        avatar_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A78BFA, stop:1 #8B5CF6);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:1 #A78BFA);
            }
        """)
        def change_avatar_and_close():
            dialog.accept()
            # Используем метод change_avatar, который открывает файловый диалог
            # Но нужно использовать тот, который находится дальше в коде (с event=None)
            QTimer.singleShot(100, lambda: self.change_avatar(None))
        avatar_btn.clicked.connect(change_avatar_and_close)
        layout.addWidget(avatar_btn)
        
        frame_btn = QPushButton(self.tr("change_frame"))
        frame_btn.setFixedHeight(50)
        frame_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A78BFA, stop:1 #8B5CF6);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:1 #A78BFA);
            }
        """)
        frame_btn.clicked.connect(lambda: (dialog.accept(), self.show_frame_selection()))
        layout.addWidget(frame_btn)
        
        cancel_btn = QPushButton(self.tr("cancel"))
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6C4A8B;
                border: 2px solid rgba(200, 182, 226, 0.4);
                border-radius: 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(200, 182, 226, 0.2);
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def change_avatar(self, event=None):
        """Открывает диалог выбора аватара"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            self.tr("select_image"), 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            # Получаем username
            username = self._get_funcs()['get_current_username']()
            if not username:
                # Пытаемся получить из user_info
                user_info = self._get_funcs()['get_user_info']()
                if user_info and len(user_info) >= 6:
                    username = user_info[5]
            
            if not username:
                QMessageBox.warning(self, self.tr("error"), "Не удалось определить пользователя")
                return
            
            # В режиме редактирования применяем аватар только визуально, без сохранения в БД
            # Сохранение произойдет при нажатии галочки
            if self.is_edit_mode:
                # Сохраняем путь к аватару во временную переменную для применения при нажатии галочки
                self._pending_avatar_path = file_path
                
                # Получаем данные пользователя для отображения
                user_info = self._get_funcs()['get_user_info'](username)
                if user_info:
                    first_name = user_info[0] if user_info[0] else ""
                    last_name = user_info[1] if user_info[1] else ""
                else:
                    first_name = ""
                    last_name = ""
                
                # Получаем рамку (текущую, возможно измененную)
                frame_path = getattr(self, '_current_frame_path', None) or self.get_user_frame_path(username)
                
                # Обновляем отображение аватара ВИЗУАЛЬНО (без сохранения в БД)
                self._current_avatar_path = file_path
                self.update_avatar_display(file_path, first_name, last_name, frame_path)
            else:
                # Вне режима редактирования сохраняем сразу в БД (старое поведение)
                if self.save_avatar_to_db(username, file_path):
                    # Получаем данные пользователя для отображения
                    user_info = self._get_funcs()['get_user_info'](username)
                    if user_info:
                        first_name = user_info[0] if user_info[0] else ""
                        last_name = user_info[1] if user_info[1] else ""
                    else:
                        first_name = ""
                        last_name = ""
                    
                    # Получаем рамку
                    frame_path = self.get_user_frame_path(username)
                    
                    # Обновляем отображение аватара
                    self.update_avatar_display(file_path, first_name, last_name, frame_path)
                    
                    # Перезагружаем информацию пользователя для обновления всех данных
                    QTimer.singleShot(100, self.load_user_info)
                else:
                    QMessageBox.warning(self, self.tr("error"), "Не удалось сохранить аватар")
    
    def change_frame(self):
        """Открывает диалог выбора рамки - вызывает show_frame_selection"""
        self.show_frame_selection()
    
    def get_user_frame_path(self, username):
        """Получает путь к рамке пользователя"""
        try:
            conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
            cursor = conn.cursor()
            cursor.execute('SELECT frame_path FROM auth_users WHERE username = ?', (username,))
            result = cursor.fetchone()
            conn.close()
            if result and result[0] and Path(result[0]).exists():
                return result[0]
        except:
            pass
        return None
    
    def save_frame_to_db(self, username, frame_path):
        """Сохраняет рамку в БД"""
        if not username:
            return False
        # Разрешаем пустую строку для "default"
        if frame_path is None:
            return False
        
        conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
        cursor = conn.cursor()
        try:
            # Проверяем, существует ли колонка frame_path
            cursor.execute("PRAGMA table_info(auth_users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'frame_path' not in columns:
                cursor.execute('ALTER TABLE auth_users ADD COLUMN frame_path TEXT')
                conn.commit()
            
            # Сохраняем рамку
            cursor.execute('''
                UPDATE auth_users 
                SET frame_path = ?
                WHERE username = ?
            ''', (frame_path, username))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_avatar_display(self, avatar_path=None, first_name="", last_name="", frame_path=None):
        """Обновляет отображение аватара и рамки профиля"""
        # Обновляем аватар (без фиолетового квадрата - полностью прозрачный фон)
        if hasattr(self, 'avatar_label') and hasattr(self, 'avatar_background'):
            # Убеждаемся, что фон аватара прозрачный
            self.avatar_background.setStyleSheet("""
                QWidget {
                    background: transparent;
                    border: none;
                }
            """)
            self.avatar_background.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Обновляем рамку профиля (белую карточку)
        if hasattr(self, 'profile_main_card'):
            # Получаем рамку если не передана
            if frame_path is None:
                username = self._get_funcs()['get_current_username']()
                if username:
                    frame_path = self.get_user_frame_path(username)
            
            # Сохраняем текущую рамку для использования в resizeEvent
            if frame_path and frame_path != "default" and frame_path != "":
                if Path(frame_path).exists():
                    self._current_frame_path = frame_path
                else:
                    self._current_frame_path = None
            else:
                self._current_frame_path = None
            
            # Проверяем, не является ли это "default"
            if frame_path == "default" or frame_path == "" or not frame_path:
                # Удаляем frame_background_label если есть
                if hasattr(self, 'frame_background_label'):
                    try:
                        self.frame_background_label.hide()
                        self.frame_background_label.deleteLater()
                    except:
                        pass
                    self.frame_background_label = None
                # Возвращаем белый фон по умолчанию (без border для отсутствия белых квадратиков)
                self.profile_main_card.setStyleSheet(f"""
                    QFrame#profileMainCard {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 rgba(255, 255, 255, 0.98),
                            stop:1 rgba(250, 245, 255, 0.98));
                        border-radius: 28px;
                        border: none;
                        padding: 0px;
                    }}
                """)
                # Обновляем маску после изменения фона
                QTimer.singleShot(10, self._update_profile_card_mask)
            elif frame_path and Path(frame_path).exists():
                # Используем новую логику - применяем фон
                self._apply_frame_background(frame_path)
            
            # Обновляем аватар
            if avatar_path and Path(avatar_path).exists():
                # Загружаем изображение
                pixmap = QPixmap(avatar_path)
                # Масштабируем до размера аватара с заполнением всего круга (обрезая при необходимости)
                pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                # Обрезаем до квадрата 140x140 из центра
                if pixmap.width() > 140 or pixmap.height() > 140:
                    x = (pixmap.width() - 140) // 2
                    y = (pixmap.height() - 140) // 2
                    pixmap = pixmap.copy(x, y, 140, 140)
                # Создаем круглую маску
                rounded = QPixmap(140, 140)
                rounded.fill(QColor(0, 0, 0, 0))
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(pixmap))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(0, 0, 140, 140)
                painter.end()
                self.avatar_label.setPixmap(rounded)
                self.avatar_label.setText("")
                # Убираем градиентный фон, когда есть изображение
                self.avatar_label.setStyleSheet("""
                    QLabel#avatarLabel {
                        background: transparent;
                        border: none;
                        border-radius: 70px;
                    }
                """)
            else:
                # Показываем фиолетовый круг с инициалами (только когда нет изображения)
                initials = ""
                if first_name and last_name:
                    initials = f"{first_name[0]}{last_name[0]}".upper()
                elif first_name:
                    initials = first_name[0].upper()
                self.avatar_label.setText(initials)
                self.avatar_label.setPixmap(QPixmap())
                # Возвращаем градиентный фон для инициалов
                colors = self._get_funcs()['get_app_colors']() if hasattr(self, '_get_funcs') else {}
                if not colors:
                    from email_app import get_app_colors
                    colors = get_app_colors()
                self.avatar_label.setStyleSheet(f"""
                    QLabel#avatarLabel {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 {colors.get('accent', '#A78BFA')},
                            stop:1 {colors.get('accent_alt', '#8B5CF6')});
                        border-radius: 70px;
                        border: none;
                        color: white;
                        font-size: 56px;
                        font-weight: bold;
                        margin: 0px;
                        padding: 0px;
                    }}
                """)
    
    def logout(self):
        """Выход из аккаунта с виджетом подтверждения"""
        from settings import LogoutConfirmDialog
        from PyQt6.QtWidgets import QDialog
        if self.main_window:
            dialog = LogoutConfirmDialog(self.main_window, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._execute_logout()
    
    def _execute_logout(self):
        """Выполняет выход из аккаунта"""
        # Сохраняем данные текущего пользователя перед выходом
        self.save_current_user_data()
        # Сохраняем прикрепленные файлы из BewerbungPage
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'bewerbung_page'):
            if hasattr(self.main_window.bewerbung_page, 'attached_files'):
                username = self._get_funcs()['get_current_username']()
                if username:
                    self._get_funcs()['save_attached_files'](username, self.main_window.bewerbung_page.attached_files)
        
        # Устанавливаем статус офлайн
        username = self._get_funcs()['get_current_username']()
        if username:
            self._get_funcs()['set_user_online'](username, False)
        
        # НЕ очищаем сохраненные данные пользователя (чтобы "Запомнить меня" работала)
        # clear_remembered_user() - убрано
        
        # Закрываем главное окно
        if self.main_window:
            self.main_window.close()
        
        # Открываем окно входа
        login_screen = self._get_funcs()['LoginScreen']()
        login_screen.show()
    
    def connect_google_account(self):
        """Подключает Google аккаунт через OAuth"""
        if not self._get_funcs()['GOOGLE_OAUTH_AVAILABLE']:
            QMessageBox.warning(self, self.tr("error"), self.tr("google_oauth_libraries_not_installed"))
            return
        
        # Проверяем наличие credentials.json или credential.json
        if not os.path.exists('credentials.json') and not os.path.exists('credential.json'):
            msg = QMessageBox(self)
            msg.setWindowTitle(self.tr("google_oauth_setup"))
            msg.setText(self.tr("credentials_json_required"))
            msg.setInformativeText(self.tr("credentials_json_instructions"))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            return
        
        # Начинаем OAuth процесс - используем run_local_server
        # Создаем виджет авторизации сразу
        
        # Создаем виджет авторизации вместо диалога
        # Сохраняем ссылку как атрибут для доступа из других методов
        self.auth_widget = QFrame(self)
        self.auth_widget.setObjectName("authWidget")
        self.auth_widget.setFixedSize(520, 380)
        colors = self._get_funcs()['get_app_colors']()
        self.auth_widget.setStyleSheet(f"""
            QFrame#authWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 24px;
                border: 2px solid rgba(200, 182, 226, 0.6);
            }}
        """)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.auth_widget.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(20)
        self.auth_widget.setLayout(layout)
        
        # Иконка Google
        google_icon = QLabel("🔐")
        google_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        google_icon.setFont(QFont("Segoe UI", 48))
        layout.addWidget(google_icon)
        
        title = QLabel(self.tr("connecting_google_account"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #6C4A8B; background: transparent;")
        layout.addWidget(title)
        
        info_label = QLabel(self.tr("auth_link_will_open"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #86868B; font-size: 13px; background: transparent; line-height: 1.5;")
        layout.addWidget(info_label)
        
        # Статус авторизации
        status_label = QLabel(self.tr("starting_authorization"))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("color: #6C4A8B; font-size: 12px; background: transparent; font-weight: 500;")
        layout.addWidget(status_label)
        
        # Позиционируем виджет по центру
        parent_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - self.auth_widget.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - self.auth_widget.height()) // 2
        self.auth_widget.move(x, y)
        self.auth_widget.raise_()
        self.auth_widget.show()
        
        # Запускаем OAuth в отдельном потоке
        def run_oauth_async():
            try:
                print(f"[DEBUG] ===== НАЧАЛО OAUTH =====")
                status_label.setText(self.tr("waiting_authorization"))
                
                # Вызываем authenticate_google_oauth - она использует run_local_server
                creds, _, error = self._get_funcs()['authenticate_google_oauth']()
                
                if error:
                    print(f"[DEBUG] ===== ОШИБКА OAUTH =====")
                    print(f"[DEBUG] Ошибка: {error}")
                    QTimer.singleShot(0, lambda: (
                        self.auth_widget.hide(),
                        QMessageBox.warning(self, self.tr("authorization_error"), self.tr("authorization_error_important", error=error))
                    ))
                    return
                
                if not creds:
                    print(f"[DEBUG] ОШИБКА: Credentials не получены")
                    QTimer.singleShot(0, lambda: (
                        self.auth_widget.hide(),
                        QMessageBox.warning(self, self.tr("error"), self.tr("failed_to_get_credentials"))
                    ))
                    return
                
                print(f"[DEBUG] ===== OAUTH ЗАВЕРШЕН УСПЕШНО =====")
                print(f"[DEBUG] Credentials получены")
                
                # Обрабатываем credentials
                creds_dict, email, error = self._get_funcs()['process_google_credentials'](creds)
                
                if error:
                    print(f"[DEBUG] Ошибка обработки credentials: {error}")
                    tr = get_tr()
                    QTimer.singleShot(0, lambda: (
                        self.auth_widget.hide(),
                        QMessageBox.warning(self, tr("error"), error)
                    ))
                    return
                
                print(f"[DEBUG] Email получен: {email}")
                
                # Получаем username в главном потоке
                username = self._get_funcs()['get_current_username']()
                print(f"[DEBUG] Сохранение Google аккаунта для username: {username}, email: {email}")
                
                if not username:
                    print(f"[DEBUG] ОШИБКА: username не определен!")
                    QTimer.singleShot(0, lambda: (
                        self.auth_widget.hide(),
                        QMessageBox.warning(self, self.tr("error"), self.tr("failed_to_determine_user"))
                    ))
                    return
                
                # Эмитируем сигнал с email и token для сохранения в GUI-потоке
                print(f"[DEBUG] ===== ЭМИССИЯ СИГНАЛА GOOGLE_AUTH_SUCCESS =====")
                print(f"[DEBUG] Email: {email}")
                print(f"[DEBUG] Token: {json.dumps(creds_dict)[:50]}...")
                self.google_auth_success.emit(email, json.dumps(creds_dict))
                
            except Exception as e:
                print(f"[DEBUG] Исключение в run_oauth_async: {e}")
                import traceback
                traceback.print_exc()
                QTimer.singleShot(0, lambda: (
                    self.auth_widget.hide(),
                    QMessageBox.warning(self, self.tr("error"), self.tr("oauth_error_general", error=str(e)))
                ))
        
        threading.Thread(target=run_oauth_async, daemon=True).start()
    
    def on_google_auth_success(self, email, token):
        """Обработчик сигнала успешной авторизации Google"""
        print(f"[DEBUG] ===== ОБРАБОТКА СИГНАЛА GOOGLE_AUTH_SUCCESS =====")
        print(f"[DEBUG] Email: {email}")
        print(f"[DEBUG] Token получен: {token[:50] if token else 'None'}...")
        
        # Скрываем виджет авторизации сразу
        if hasattr(self, 'auth_widget'):
            self.auth_widget.hide()
            print(f"[DEBUG] auth_widget скрыт")
        
        # Получаем username
        username = self._get_funcs()['get_current_username']()
        if not username:
            print(f"[DEBUG] ОШИБКА: username не определен!")
            QMessageBox.warning(self, self.tr("error"), self.tr("failed_to_determine_user"))
            return
        
        # Сохраняем в БД
        print(f"[DEBUG] Сохранение Google аккаунта в БД...")
        save_success = self._get_funcs()['save_google_account'](username, email, token)
        print(f"[DEBUG] Результат сохранения в БД: {save_success}")
        
        if not save_success:
            print(f"[DEBUG] ОШИБКА: Не удалось сохранить в БД!")
            QMessageBox.warning(self, self.tr("error"), self.tr("failed_to_save_account"))
            return
        
        # Обновляем UI
        QTimer.singleShot(0, lambda: self.update_google_status())
        QTimer.singleShot(0, lambda: self.load_user_info())
        
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'bewerbung_page'):
            QTimer.singleShot(0, lambda: self.main_window.bewerbung_page.check_google_account())
        
        QTimer.singleShot(0, lambda: self.update())
        QTimer.singleShot(0, lambda: self.repaint())
        
        print(f"[DEBUG] ===== ПРИВЯЗКА ЗАВЕРШЕНА УСПЕШНО =====")
        
        # Показываем виджет успешной авторизации вместо QMessageBox
        QTimer.singleShot(0, lambda: self.show_success_widget(email))
    
    def show_success_widget(self, email):
        """Показывает виджет успешной авторизации"""
        # Создаем виджет успеха
        success_widget = QFrame(self)
        success_widget.setObjectName("successWidget")
        success_widget.setFixedSize(450, 200)
        success_widget.setStyleSheet(f"""
            QFrame#successWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(156, 137, 184, 0.98),
                    stop:1 rgba(108, 74, 139, 0.98));
                border-radius: 20px;
                border: 2px solid rgba(167, 139, 250, 0.6);
            }}
        """)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        success_widget.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)
        success_widget.setLayout(layout)
        
        # Иконка успеха
        icon_label = QLabel("✓")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 48))
        icon_label.setStyleSheet("color: #34d399; background: transparent;")
        layout.addWidget(icon_label)
        
        # Заголовок
        title = QLabel("Аккаунт привязан")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(title)
        
        # Email
        email_label = QLabel(f"Email: {email}")
        email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        email_label.setFont(QFont("Segoe UI", 13))
        email_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); background: transparent;")
        layout.addWidget(email_label)
        
        # Текст
        info_label = QLabel(tr("can_send_emails_gmail"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setFont(QFont("Segoe UI", 11))
        info_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        layout.addWidget(info_label)
        
        # Позиционируем по центру
        parent_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - success_widget.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - success_widget.height()) // 2
        success_widget.move(x, y)
        success_widget.raise_()
        success_widget.show()
        
        # Автоматически скрываем через 3 секунды
        QTimer.singleShot(3000, lambda: success_widget.hide())
    
    def on_oauth_complete(self, email):
        """Обработчик сигнала завершения OAuth"""
        print(f"[DEBUG] ===== ОБРАБОТКА СИГНАЛА OAUTH =====")
        print(f"[DEBUG] Email: {email}")
        
        # Обновляем UI через QTimer.singleShot для безопасного обновления из другого потока (Google аккаунт теперь в настройках)
        QTimer.singleShot(0, lambda: self.load_user_info())
        
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'bewerbung_page'):
            QTimer.singleShot(0, lambda: self.main_window.bewerbung_page.check_google_account())
        
        QTimer.singleShot(0, lambda: self.update())
        QTimer.singleShot(0, lambda: self.repaint())
        
        print(f"[DEBUG] ===== ПРИВЯЗКА ЗАВЕРШЕНА УСПЕШНО =====")
        
        # Показываем виджет успешной авторизации вместо QMessageBox
        QTimer.singleShot(0, lambda: self.show_success_widget(email))
    
    def disconnect_google_account(self):
        """Отключает или меняет Google аккаунт"""
        username = self._get_funcs()['get_current_username']()
        if not username:
            return
        
        # Получаем текущий email
        current_email = self._get_funcs()['get_google_account_email'](username)
        
        if current_email:
            # Показываем виджет выбора вместо QMessageBox
            self.show_account_management_widget(current_email, username)
        else:
            # Если аккаунт не подключен, просто запускаем подключение
            self.connect_google_account()
    
    def show_account_management_widget(self, email, username):
        """Показывает виджет управления аккаунтом"""
        # Создаем виджет
        management_widget = QFrame(self)
        management_widget.setObjectName("accountManagementWidget")
        management_widget.setFixedSize(480, 320)  # Увеличена высота
        management_widget.setStyleSheet(f"""
            QFrame#accountManagementWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(229, 217, 242, 0.98),
                    stop:1 rgba(200, 182, 226, 0.98));
                border-radius: 24px;
                border: 2px solid rgba(167, 139, 250, 0.6);
            }}
        """)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 60))
        management_widget.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)
        management_widget.setLayout(layout)
        
        # Заголовок
        tr = get_tr()
        title = QLabel(tr("manage_account"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #6C4A8B; background: transparent;")
        layout.addWidget(title)
        
        # Email
        email_label = QLabel(f"{tr('current_account')}: {email}")
        email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        email_label.setFont(QFont("Segoe UI", 12))
        email_label.setStyleSheet("color: #86868B; background: transparent;")
        layout.addWidget(email_label)
        
        # Текст
        info_label = QLabel(tr("what_do_you_want_to_do"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setFont(QFont("Segoe UI", 13))
        info_label.setStyleSheet("color: #4A2C6B; background: transparent; margin-top: 10px;")
        layout.addWidget(info_label)
        
        # Кнопки
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(18)  # Увеличен отступ между кнопками
        
        # Кнопка "Отключить аккаунт"
        disconnect_btn = QPushButton(tr("disconnect_account"))
        disconnect_btn.setFixedHeight(44)
        disconnect_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.1);
                color: #ef4444;
                border: 2px solid rgba(239, 68, 68, 0.3);
                border-radius: 12px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.5);
            }
        """)
        
        def on_disconnect():
            management_widget.hide()
            management_widget.deleteLater()
            self._get_funcs()['save_google_account'](username, None, None)
            QTimer.singleShot(0, lambda: self.load_user_info())
            # Показываем виджет успешного отключения
            self.show_disconnect_success_widget()
        
        disconnect_btn.clicked.connect(on_disconnect)
        buttons_layout.addWidget(disconnect_btn)
        
        # Кнопка "Сменить аккаунт"
        change_btn = QPushButton(tr("change_account"))
        change_btn.setFixedHeight(44)
        change_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(167, 139, 250, 0.9),
                    stop:1 rgba(108, 74, 139, 0.9));
                color: white;
                border: 2px solid rgba(167, 139, 250, 0.5);
                border-radius: 12px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(156, 137, 184, 0.95),
                    stop:1 rgba(98, 64, 129, 0.95));
                border-color: rgba(167, 139, 250, 0.7);
            }
        """)
        
        def on_change():
            management_widget.hide()
            management_widget.deleteLater()
            self._get_funcs()['save_google_account'](username, None, None)
            QTimer.singleShot(0, lambda: self.update_google_status())
            # Запускаем подключение нового аккаунта
            QTimer.singleShot(300, self.connect_google_account)
        
        change_btn.clicked.connect(on_change)
        buttons_layout.addWidget(change_btn)
        
        # Кнопка "Отмена"
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #86868B;
                border: 2px solid rgba(156, 137, 184, 0.3);
                border-radius: 12px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(156, 137, 184, 0.1);
                border-color: rgba(156, 137, 184, 0.5);
            }
        """)
        
        def on_cancel():
            management_widget.hide()
            management_widget.deleteLater()
        
        cancel_btn.clicked.connect(on_cancel)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        # Позиционируем по центру
        parent_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - management_widget.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - management_widget.height()) // 2
        management_widget.move(x, y)
        management_widget.raise_()
        management_widget.show()
    
    def show_disconnect_success_widget(self):
        """Показывает виджет успешного отключения"""
        success_widget = QFrame(self)
        success_widget.setObjectName("disconnectSuccessWidget")
        success_widget.setFixedSize(400, 160)
        success_widget.setStyleSheet(f"""
            QFrame#disconnectSuccessWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 20px;
                border: 2px solid rgba(167, 139, 250, 0.6);
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 60))
        success_widget.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        success_widget.setLayout(layout)
        
        # Иконка
        icon_label = QLabel("✓")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 36))
        icon_label.setStyleSheet("color: #34d399; background: transparent;")
        layout.addWidget(icon_label)
        
        # Текст
        text_label = QLabel("Google аккаунт успешно отключен от вашего профиля.")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setFont(QFont("Segoe UI", 12))
        text_label.setStyleSheet("color: #4A2C6B; background: transparent;")
        layout.addWidget(text_label)
        
        # Позиционируем по центру
        parent_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - success_widget.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - success_widget.height()) // 2
        success_widget.move(x, y)
        success_widget.raise_()
        success_widget.show()
        
        # Автоматически скрываем через 2 секунды
        QTimer.singleShot(2000, lambda: success_widget.hide())
    
    def save_current_user_data(self):
        """Сохраняет данные текущего пользователя перед выходом"""
        try:
            user_info = self._get_funcs()['get_user_info']()
            if user_info and len(user_info) >= 6:
                username = user_info[5]
                if username:
                    # Получаем текущие данные из БД
                    conn = sqlite3.connect(self._get_funcs()['DB_FILE'])
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT first_name, last_name, phone_number, avatar_path 
                        FROM auth_users 
                        WHERE username = ?
                    ''', (username,))
                    result = cursor.fetchone()
                    
                    if result:
                        # Обновляем данные в auth_users
                        first_name, last_name, phone_number, avatar_path = result
                        # Получаем актуальные данные из user
                        current_user = self._get_funcs()['get_user_info']()
                        if current_user:
                            first_name = current_user[0] if current_user[0] else first_name
                            last_name = current_user[1] if current_user[1] else last_name
                            phone_number = current_user[2] if current_user[2] else phone_number
                            avatar_path = current_user[4] if len(current_user) > 4 and current_user[4] else avatar_path
                            
                            cursor.execute('''
                                UPDATE auth_users 
                                SET first_name = ?, last_name = ?, phone_number = ?, avatar_path = ?
                                WHERE username = ?
                            ''', (first_name, last_name, phone_number, avatar_path, username))
                            conn.commit()
                    conn.close()
        except Exception as e:
            print(f"Ошибка при сохранении данных пользователя: {e}")
    
    def eventFilter(self, obj, event):
        """Обработчик событий для показа карандаша при наведении и клика на аватар в режиме редактирования"""
        
        if hasattr(self, 'avatar_label') and (obj == self.avatar_label or obj == self.avatar_wrapper):
            # В режиме редактирования показываем карандаш при наведении
            if hasattr(self, 'is_edit_mode') and self.is_edit_mode:
                if event.type() == QEvent.Type.Enter:
                    # Показываем карандаш
                    if hasattr(self, 'avatar_edit_icon'):
                        self.avatar_edit_icon.show()
                    # Делаем аватар кликабельным
                    if hasattr(self, 'avatar_label'):
                        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
                elif event.type() == QEvent.Type.Leave:
                    # Скрываем карандаш
                    if hasattr(self, 'avatar_edit_icon'):
                        self.avatar_edit_icon.hide()
                    # Возвращаем обычный курсор
                    if hasattr(self, 'avatar_label'):
                        self.avatar_label.setCursor(Qt.CursorShape.ArrowCursor)
                elif event.type() == QEvent.Type.MouseButtonPress:
                    # При клике на аватар в режиме редактирования - открываем диалог выбора
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.change_avatar()
                        return True
        return super().eventFilter(obj, event)
    
    def _apply_frame_background(self, frame_path):
        """Применяет фон рамки к карточке профиля (новая логика)"""
        if not hasattr(self, 'profile_main_card') or not frame_path or not Path(frame_path).exists():
            return
        
        try:
            # Получаем размер карточки
            card_size = self.profile_main_card.size()
            # Если размер еще не установлен, пробуем получить из geometry
            if card_size.width() <= 10 or card_size.height() <= 10:
                card_rect = self.profile_main_card.geometry()
                if not card_rect.isEmpty():
                    card_size = card_rect.size()
                # Если все еще нет размера, используем минимальный размер
                if card_size.width() <= 10 or card_size.height() <= 10:
                    card_size = QSize(600, 400)  # Размер по умолчанию
            
            # Загружаем и масштабируем изображение
            frame_pixmap = QPixmap(str(frame_path))
            if frame_pixmap.isNull():
                return
            
            # Масштабируем изображение
            scaled_pixmap = frame_pixmap.scaled(
                card_size.width(), 
                card_size.height(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Обрезаем по центру если нужно
            if scaled_pixmap.width() > card_size.width() or scaled_pixmap.height() > card_size.height():
                x = (scaled_pixmap.width() - card_size.width()) // 2
                y = (scaled_pixmap.height() - card_size.height()) // 2
                scaled_pixmap = scaled_pixmap.copy(x, y, card_size.width(), card_size.height())
            
            # Создаем закругленное изображение
            rounded_pixmap = QPixmap(card_size.width(), card_size.height())
            rounded_pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(scaled_pixmap))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, card_size.width(), card_size.height(), 28, 28)
            painter.end()
            
            # Удаляем старый label если есть
            if hasattr(self, 'frame_background_label') and self.frame_background_label:
                try:
                    self.frame_background_label.deleteLater()
                except:
                    pass
            
            # Создаем новый QLabel для отображения фона
            self.frame_background_label = QLabel(self.profile_main_card)
            self.frame_background_label.setPixmap(rounded_pixmap)
            self.frame_background_label.setGeometry(0, 0, card_size.width(), card_size.height())
            self.frame_background_label.lower()  # Под содержимым
            self.frame_background_label.setScaledContents(False)
            self.frame_background_label.show()
            
            # Устанавливаем прозрачный фон для карточки
            self.profile_main_card.setStyleSheet(f"""
                QFrame#profileMainCard {{
                    background: transparent;
                    border-radius: 28px;
                    border: none;
                    padding: 0px;
                }}
            """)
            
            # Обновляем маску
            QTimer.singleShot(10, self._update_profile_card_mask)
        except Exception as e:
            print(f"Ошибка при применении фона: {e}")
    
    def _update_profile_card_mask(self):
        """Обновляет маску карточки профиля для закругленных углов"""
        if not hasattr(self, 'profile_main_card') or not self.profile_main_card:
            return
        try:
            from PyQt6.QtGui import QRegion, QPainterPath
            size = self.profile_main_card.size()
            if size.width() > 10 and size.height() > 10:
                # Создаем закругленную область через QPainterPath
                path = QPainterPath()
                path.addRoundedRect(0, 0, size.width(), size.height(), 28, 28)
                # Преобразуем путь в полигон и создаем регион
                polygon = path.toFillPolygon()
                region = QRegion(polygon)
                self.profile_main_card.setMask(region)
                # Также обновляем маску для frame_background_label если он есть
                if hasattr(self, 'frame_background_label') and self.frame_background_label:
                    try:
                        bg_size = self.frame_background_label.size()
                        if bg_size.width() > 10 and bg_size.height() > 10:
                            bg_path = QPainterPath()
                            bg_path.addRoundedRect(0, 0, bg_size.width(), bg_size.height(), 28, 28)
                            bg_polygon = bg_path.toFillPolygon()
                            bg_region = QRegion(bg_polygon)
                            self.frame_background_label.setMask(bg_region)
                    except:
                        pass
        except Exception as e:
            pass  # Игнорируем ошибки маски
    
    def _update_profile_on_show(self):
        """Обновляет профиль при показе карточки - исправляет баг с половиной карточки"""
        if not hasattr(self, 'profile_main_card'):
            return
        # Проверяем размер карточки
        size = self.profile_main_card.size()
        if size.width() > 10 and size.height() > 10:
            # Обновляем фон если есть рамка
            if hasattr(self, '_current_frame_path') and self._current_frame_path:
                self._apply_frame_background(self._current_frame_path)
            # Обновляем маску
            self._update_profile_card_mask()
    
    def update_texts(self):
        """Обновляет тексты при смене языка"""
        # Обновляем заголовок профиля
        for widget in self.findChildren(QLabel):
            text = widget.text()
            if text == "Профиль" or text == "Profil":
                widget.setText(self.tr("profile"))
            elif text == "Ваше имя" or text == "Ihr Name":
                widget.setText(self.tr("your_name"))
            elif text == "Номер телефона" or text == "Telefonnummer":
                widget.setText(self.tr("phone_number"))
            elif text == "Последняя отправка" or text == "Letzte Sendung":
                widget.setText(self.tr("last_sent"))
            elif text == "Самая популярная вакансия" or text == "Beliebteste Stelle":
                widget.setText(self.tr("popular_position"))
            elif text == self.tr("no_sent") or text in ["Нет отправок", "Keine Sendungen", "No Sent"]:
                widget.setText(self.tr("no_sent"))
            elif text == self.tr("no_data") or text in ["Нет данных", "Keine Daten", "No Data"]:
                widget.setText(self.tr("no_data"))
            elif "Дата регистрации" in text or "Registrierungsdatum" in text:
                widget.setText(self.tr("registration_date"))
            elif "Дней в приложении" in text or "Tage in der App" in text:
                widget.setText(self.tr("days_in_app"))
            elif "Активность" in text or "Aktivität" in text:
                widget.setText(self.tr("activity"))
            elif "Цель недели" in text or "Wochenziel" in text:
                widget.setText(self.tr("week_goal"))
        # Обновляем кнопки
        for widget in self.findChildren(QPushButton):
            text = widget.text()
            if text == "Отмена" or text == "Abbrechen":
                widget.setText(self.tr("cancel"))
            elif text == "Сохранить" or text == "Speichern":
                widget.setText(self.tr("save"))
            elif text == "Выйти" or text == "Abmelden":
                widget.setText(self.tr("logout"))
        
        # Обновляем tooltip кнопки редактирования
        for widget in self.findChildren(QPushButton):
            if widget.toolTip() == "Редактировать имя" or widget.toolTip() == "Name bearbeiten":
                widget.setToolTip(self.tr("edit"))
        
        # Обновляем метки активности
        if hasattr(self, 'activity_label'):
            history = self._get_funcs()['get_email_history']()
            total_sent = len(history)
            self.update_activity_labels(total_sent)
        
        # Обновляем кнопку показа/скрытия номера телефона
        if hasattr(self, 'show_phone_button'):
            if self.phone_is_visible:
                self.show_phone_button.setText(self.tr("hide_phone"))
            else:
                self.show_phone_button.setText(self.tr("show_phone"))
        
        # Перезагружаем информацию пользователя для обновления дней в приложении
        self.load_user_info()
    
    def update_activity_realtime(self):
        """Обновляет активность в реальном времени"""
        history = self._get_funcs()['get_email_history'](force_refresh=True)  # Принудительно обновляем
        total_sent = len(history)
        self.update_activity_labels(total_sent)
    
    def update_activity_labels(self, total_sent):
        """Обновляет метки активности с переводами"""
        if hasattr(self, 'activity_label'):
            self.activity_label.setText(f"{self.tr('total_sent_label')}: {total_sent}")
        if hasattr(self, 'activity_stats_label') and self.activity_stats_label.parent():
            # Обновляем только если метка уже существует и добавлена в layout
            history = self._get_funcs()['get_email_history']()
