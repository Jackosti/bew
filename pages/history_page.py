"""
Страница истории писем (History Page)
Современный дизайн в стиле окна письма
PyQt6 версия
"""
import os
import hashlib
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QScrollArea, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QGraphicsDropShadowEffect, QAbstractItemView, QLineEdit, QDialog, QDateEdit,
    QCheckBox, QToolButton, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QDate, QPropertyAnimation, QEasingCurve, QPoint, QRect, QEvent
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QPixmap, QPen, QBrush, QKeySequence, QShortcut
from PyQt6.QtSvg import QSvgRenderer

# Импортируем функции из основного файла
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
    """Получает необходимые функции"""
    try:
        from email_app import (
            get_current_username, get_email_history, clear_email_history, delete_email_history_entry
        )
        return {
            'get_current_username': get_current_username,
            'get_email_history': get_email_history,
            'clear_email_history': clear_email_history,
            'delete_email_history_entry': delete_email_history_entry
        }
    except ImportError:
        return {
            'get_current_username': lambda: None,
            'get_email_history': lambda *args, **kwargs: [],
            'clear_email_history': lambda *args, **kwargs: False,
            'delete_email_history_entry': lambda *args, **kwargs: False
        }


class HistoryPage(QWidget):
    """Страница истории писем с современным дизайном (PyQt6)"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_active = False  # Флаг активности страницы
        
        # Инициализируем функции
        self._tr = None
        self._funcs = None
        
        # Состояние для bulk actions
        self.selected_rows = set()  # Множество выбранных строк (индексы)
        self.bulk_toolbar = None  # Панель инструментов для bulk actions
        
        # Боковая панель деталей
        self.details_panel = None
        self.details_panel_animation = None
        
        # Состояние фильтров для localStorage
        self.filter_chips_container = None
        self.filter_chips = []  # Список активных фильтр-чипсов
        
        # Состояние для hover эффектов
        self.current_hovered_row = -1
        
        self.setup_ui()
        
        # Загружаем функции после создания UI
        QTimer.singleShot(0, self._load_functions)
        
        # Загружаем сохранённые фильтры из localStorage
        QTimer.singleShot(100, self._load_saved_filters)
        
        # Настраиваем горячие клавиши
        self._setup_keyboard_shortcuts()
    
    def activate(self):
        """Активирует страницу - загружает данные"""
        if not self.is_active:
            self.is_active = True
        self.load_history()
    
    def deactivate(self):
        """Деактивирует страницу"""
        if self.is_active:
            self.is_active = False
    
    def _load_functions(self):
        """Загружает функции после инициализации"""
        self._tr = get_tr()
        self._funcs = get_functions()
        self.load_history()
    
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
    
    def _load_saved_filters(self):
        """Загружает сохранённые фильтры из localStorage"""
        # Пока фильтры не сохраняются в localStorage, просто инициализируем их
        # В будущем это может быть расширено для сохранения фильтров между сессиями
        pass
    
    def _save_filters_to_storage(self):
        """Сохраняет фильтры в localStorage"""
        # Пока фильтры не сохраняются в localStorage
        # В будущем это может быть расширено для сохранения фильтров между сессиями
        pass
    
    def _setup_keyboard_shortcuts(self):
        """Настраивает горячие клавиши для страницы"""
        # Можно добавить горячие клавиши для общих операций
        # Например: Delete для удаления, Ctrl+C для копирования и т.д.
        pass
    
    def get_avatar_color(self, email):
        """Генерирует постоянный цвет для аватара на основе email"""
        # Список красивых цветов для аватаров (светлее)
        colors = [
            "#D0406B",  # Розовый (светлее)
            "#7D40C0",  # Фиолетовый (светлее)
            "#4A60C0",  # Синий (светлее)
            "#4A8BC0",  # Голубой (светлее)
            "#4AC08B",  # Бирюзовый (светлее)
            "#7DC040",  # Салатовый (светлее)
            "#C08B40",  # Желтый (светлее)
            "#C06B40",  # Оранжевый (светлее)
            "#C04A55",  # Коралловый (светлее)
            "#8B40C0",  # Лавандовый (светлее)
        ]
        # Генерируем хеш из email для постоянного цвета
        hash_value = int(hashlib.md5(email.encode()).hexdigest(), 16)
        return colors[hash_value % len(colors)]
    
    def create_avatar_widget(self, email):
        """Создает виджет аватара с силуэтом человека"""
        avatar_label = QLabel()
        avatar_label.setFixedSize(40, 40)
        
        # Получаем цвет для этого email
        color = self.get_avatar_color(email)
        
        # Рисуем аватар на pixmap
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Белый круглый фон (заметный, с легким оттенком)
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))  # Белый непрозрачный
        painter.setPen(QPen(QColor(240, 235, 250, 255), 1))  # Легкая рамка
        painter.drawEllipse(1, 1, 38, 38)
        
        # Дополнительный легкий цветной фон (тонкий круг внутри)
        color_obj = QColor(color)
        bg_color = QColor(color_obj.red(), color_obj.green(), color_obj.blue(), 15)  # Очень прозрачный цветной фон
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawEllipse(4, 4, 32, 32)
        
        # Цветной силуэт человека (слегка прозрачный и светлее)
        color_obj = QColor(color)
        # Добавляем прозрачность (альфа-канал около 210 - чуть прозрачный)
        silhouette_color = QColor(color_obj.red(), color_obj.green(), color_obj.blue(), 210)
        painter.setBrush(QBrush(silhouette_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        
        # Голова (чуть отдалена от туловища)
        painter.drawEllipse(14, 8, 12, 12)  # Голова
        
        # Туловище (растянуто по горизонтали)
        painter.drawEllipse(8, 22, 24, 14)  # Тело растянуто
        
        painter.end()
        avatar_label.setPixmap(pixmap)
        avatar_label.setStyleSheet("background: transparent; border-radius: 20px;")
        
        return avatar_label
    
    def setup_ui(self):
        """Создает улучшенный интерфейс страницы истории"""
        # Главный контейнер с градиентным фоном
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Устанавливаем градиентный фон
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #EEE9F6, stop:0.4 #E2DBF2, stop:1 #CFC2E6);
                font-family: "Inter", "Segoe UI", sans-serif;
            }
        """)
        
        # Scroll area для прокрутки контента
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QScrollBar:vertical {
                background: rgba(200, 182, 226, 0.2);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(156, 137, 184, 0.5);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(156, 137, 184, 0.7);
            }
        """)
        
        # Контент виджет
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(40, 35, 40, 40)  # Уменьшен верхний отступ для большего пространства
        content_layout.setSpacing(20)  # Уменьшен spacing
        content_widget.setLayout(content_layout)
        
        # Заголовок страницы
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel(self.tr("history") if hasattr(self, 'tr') else "История")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
                background: transparent;
                letter-spacing: -0.5px;
            }
        """)
        header_layout.addWidget(title)
        content_layout.addLayout(header_layout)
        
        # Основная белая карточка с улучшенным дизайном
        main_card = QFrame()
        main_card.setObjectName("mainCard")
        main_card.setStyleSheet("""
            QFrame#mainCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 24px;
                border: 2px solid rgba(200, 182, 226, 0.3);
            }
        """)
        
        # Тень для карточки
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(40)
        card_shadow.setXOffset(0)
        card_shadow.setYOffset(8)
        card_shadow.setColor(QColor(108, 74, 139, 60))
        main_card.setGraphicsEffect(card_shadow)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(36, 32, 36, 32)  # Увеличены отступы внутри карточки
        card_layout.setSpacing(24)
        main_card.setLayout(card_layout)
        
        # Панель поиска и фильтров
        filters_layout = QHBoxLayout()
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(12)
        
        # Контейнер для поля поиска в стиле окна друзья
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E0D0F0;
                border-radius: 8px;
            }
        """)
        search_container_layout = QHBoxLayout()
        search_container_layout.setContentsMargins(12, 0, 12, 0)
        search_container_layout.setSpacing(6)
        search_container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Иконка поиска (монохромная, полупрозрачная)
        search_icon_pixmap = QPixmap(18, 18)
        search_icon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(search_icon_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#8B7AA3"), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        # Рисуем круг (линза)
        painter.drawEllipse(2, 2, 10, 10)
        # Рисуем ручку
        painter.drawLine(10, 10, 16, 16)
        painter.end()
        
        search_icon = QLabel()
        search_icon.setFixedSize(18, 18)
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_icon.setPixmap(search_icon_pixmap)
        search_icon.setStyleSheet("background: transparent; border: none;")
        search_container_layout.addWidget(search_icon)
        
        # Поле поиска
        self.search_input = QLineEdit()
        # Более понятный плейсхолдер: что именно можно искать
        self.search_input.setPlaceholderText(
            self.tr("search_by_email_position_date")
            if hasattr(self, "tr") and self.tr("search_by_email_position_date") != "search_by_email_position_date"
            else "Поиск по email, должности или дате"
        )
        self.search_input.setFixedHeight(40)
        self.search_input.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                font-size: 15px;
                color: #4A2C6B;
                padding: 0;
                margin: 0;
            }
            QLineEdit:focus {
                background: transparent;
            }
            QLineEdit::placeholder {
                color: #8B7AA3;
            }
        """)
        self.search_input.textChanged.connect(self.filter_history)
        search_container_layout.addWidget(self.search_input, stretch=1)
        
        # Иконки-подсказки справа от поля поиска (📧 💼 📅)
        hints_container = QWidget()
        hints_container.setStyleSheet("background: transparent;")
        hints_layout = QHBoxLayout()
        hints_layout.setContentsMargins(0, 0, 0, 0)
        hints_layout.setSpacing(4)
        
        email_hint = QLabel("📧")
        email_hint.setFont(QFont("Segoe UI", 12))
        email_hint.setStyleSheet("background: transparent; opacity: 0.5;")
        email_hint.setToolTip("Email")
        hints_layout.addWidget(email_hint)
        
        position_hint = QLabel("💼")
        position_hint.setFont(QFont("Segoe UI", 12))
        position_hint.setStyleSheet("background: transparent; opacity: 0.5;")
        position_hint.setToolTip("Должность")
        hints_layout.addWidget(position_hint)
        
        date_hint = QLabel("📅")
        date_hint.setFont(QFont("Segoe UI", 12))
        date_hint.setStyleSheet("background: transparent; opacity: 0.5;")
        date_hint.setToolTip("Дата")
        hints_layout.addWidget(date_hint)
        
        hints_container.setLayout(hints_layout)
        search_container_layout.addWidget(hints_container)
        search_container.setLayout(search_container_layout)
        
        filters_layout.addWidget(search_container, stretch=1)
        
        # Кнопка "Фильтры" (лиловая прозрачная с монохромной иконкой)
        filters_btn = QPushButton()
        filters_btn.setFixedHeight(40)
        filters_btn.setFixedWidth(120)
        
        # Создаем иконку фильтра (монохромная, полупрозрачная)
        filter_icon_pixmap = QPixmap(16, 16)
        filter_icon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(filter_icon_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#8B7AA3"), 2, Qt.PenStyle.SolidLine))
        # Рисуем воронку/фильтр (три горизонтальные линии)
        painter.drawLine(3, 4, 13, 4)
        painter.drawLine(4, 8, 12, 8)
        painter.drawLine(5, 12, 11, 12)
        painter.end()
        
        filter_icon = QLabel()
        filter_icon.setFixedSize(16, 16)
        filter_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_icon.setPixmap(filter_icon_pixmap)
        filter_icon.setStyleSheet("background: transparent; border: none;")
        
        filters_btn_layout = QHBoxLayout()
        filters_btn_layout.setContentsMargins(8, 0, 8, 0)
        filters_btn_layout.setSpacing(6)
        filters_btn_layout.addWidget(filter_icon)
        
        filters_btn_text = QLabel(self.tr("filters") if hasattr(self, 'tr') else "Фильтры")
        filters_btn_text.setStyleSheet("background: transparent; border: none; color: #4A2C6B; font-size: 14px; font-weight: 500;")
        filters_btn_layout.addWidget(filters_btn_text)
        filters_btn.setLayout(filters_btn_layout)
        
        filters_btn.setStyleSheet("""
            QPushButton {
                background: rgba(156, 123, 255, 0.15);
                border: 1px solid rgba(156, 123, 255, 0.3);
                border-radius: 8px;
                color: #4A2C6B;
            }
            QPushButton:hover {
                background: rgba(156, 123, 255, 0.25);
                border: 1px solid rgba(156, 123, 255, 0.4);
            }
            QPushButton:pressed {
                background: rgba(156, 123, 255, 0.35);
                border: 1px solid rgba(156, 123, 255, 0.5);
            }
        """)
        filters_btn.clicked.connect(self.show_filters_dialog)
        filters_layout.addWidget(filters_btn)
        
        # Кнопка "Удалить" (лиловая прозрачная с монохромной иконкой)
        delete_btn = QPushButton()
        delete_btn.setFixedHeight(40)
        delete_btn.setFixedWidth(120)
        
        # Создаем иконку удаления (монохромная, полупрозрачная)
        delete_icon_pixmap = QPixmap(16, 16)
        delete_icon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(delete_icon_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#8B7AA3"), 2, Qt.PenStyle.SolidLine))
        # Рисуем корзину
        painter.drawRect(4, 6, 8, 7)  # Корпус корзины
        painter.drawLine(5, 5, 6, 3)  # Ручка слева
        painter.drawLine(11, 5, 10, 3)  # Ручка справа
        painter.drawLine(3, 4, 13, 4)  # Верхняя линия
        painter.end()
        
        delete_icon = QLabel()
        delete_icon.setFixedSize(16, 16)
        delete_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delete_icon.setPixmap(delete_icon_pixmap)
        delete_icon.setStyleSheet("background: transparent; border: none;")
        
        delete_btn_layout = QHBoxLayout()
        delete_btn_layout.setContentsMargins(8, 0, 8, 0)
        delete_btn_layout.setSpacing(6)
        delete_btn_layout.addWidget(delete_icon)
        
        delete_btn_text = QLabel(self.tr("delete") if hasattr(self, 'tr') else "Удалить")
        delete_btn_text.setStyleSheet("background: transparent; border: none; color: #4A2C6B; font-size: 14px; font-weight: 500;")
        delete_btn_layout.addWidget(delete_btn_text)
        delete_btn.setLayout(delete_btn_layout)
        
        delete_btn.setStyleSheet("""
            QPushButton {
                background: rgba(156, 123, 255, 0.15);
                border: 1px solid rgba(156, 123, 255, 0.3);
                border-radius: 8px;
                color: #4A2C6B;
            }
            QPushButton:hover {
                background: rgba(156, 123, 255, 0.25);
                border: 1px solid rgba(156, 123, 255, 0.4);
            }
            QPushButton:pressed {
                background: rgba(156, 123, 255, 0.35);
                border: 1px solid rgba(156, 123, 255, 0.5);
            }
        """)
        delete_btn.clicked.connect(self.clear_history)
        filters_layout.addWidget(delete_btn)
        
        card_layout.addLayout(filters_layout)
        
        # Контейнер для фильтр-чипсов (показывается когда есть активные фильтры)
        self.filter_chips_container = QWidget()
        self.filter_chips_container.setStyleSheet("background: transparent;")
        filter_chips_layout = QHBoxLayout()
        filter_chips_layout.setContentsMargins(0, 8, 0, 0)
        filter_chips_layout.setSpacing(8)
        filter_chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.filter_chips_container.setLayout(filter_chips_layout)
        self.filter_chips_container.hide()  # Скрыт по умолчанию
        card_layout.addWidget(self.filter_chips_container)
        
        # Сохраняем состояние фильтров
        self.filter_date_from = None
        self.filter_date_to = None
        self.filter_email = None
        self.filter_position = None
        
        # Разделитель
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: rgba(156, 137, 184, 0.2); max-height: 1px; border: none;")
        card_layout.addWidget(divider)
        
        # Таблица истории (улучшенный стиль)
        self.history_table = QTableWidget()
        # Добавляем колонку для чекбоксов
        self.history_table.setColumnCount(4)  # Чекбокс + Дата + Email + Должность
        # Локализация заголовков таблицы (пустая первая колонка для чекбоксов)
        header_labels = ["", self.tr("date_time"), self.tr("recipient_email"), self.tr("position")]
        self.history_table.setHorizontalHeaderLabels(header_labels)
        # Скрываем заголовок первой колонки (чекбоксы)
        self.history_table.horizontalHeader().hideSection(0)
        
        # Улучшенные стили заголовков (sticky header)
        self.history_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(245, 243, 250, 0.98),
                    stop:1 rgba(240, 235, 250, 0.98));
                color: #6C4A8B;
                padding: 16px 20px;
                border: none;
                border-bottom: 2px solid rgba(156, 137, 184, 0.3);
                font-weight: 600;
                font-size: 14px;
            }
        """)
        self.history_table.horizontalHeader().setDefaultSectionSize(200)
        # Делаем заголовок sticky (липким при скролле)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        # Включаем sticky header через setSectionResizeMode
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        # Улучшенные стили таблицы:
        # - без "липкого" выделения
        # - строка подсвечивается на hover как кликабельная
        self.history_table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: none;
                gridline-color: rgba(200, 182, 226, 0.2);
                font-size: 14px;
                selection-background-color: transparent;
                selection-color: #4B3F72;
            }
            QTableWidget::item {
                padding: 8px 16px 8px 16px;
                color: #4B3F72;
                border-bottom: 1px solid rgba(200, 182, 226, 0.15);
                background: transparent;
            }
            QTableWidget::item:selected {
                background: transparent;
                color: #4B3F72;
            }
            QTableWidget::item:hover {
                background: #F4F2FF;
            }
            QTableWidget::row {
                background: transparent;
            }
            QTableWidget::row:selected {
                background: transparent;
            }
        """)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False)
        self.history_table.setAlternatingRowColors(False)  # Убираем чередование цветов
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Включаем множественный выбор для bulk actions
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        
        # Уменьшенная высота строк для более компактного вида
        self.history_table.verticalHeader().setDefaultSectionSize(64)  # Чуть больше для чекбоксов и действий
        # Курсор "рука" поверх строк, чтобы было понятно, что они кликабельны
        self.history_table.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Обработчик hover для строк (показываем действия при наведении)
        self.history_table.setMouseTracking(True)
        self.history_table.viewport().setMouseTracking(True)
        # Используем eventFilter для отслеживания hover на строках
        self.history_table.viewport().installEventFilter(self)
        self.current_hovered_row = -1  # Текущая строка под курсором
        
        card_layout.addWidget(self.history_table)
        
        # Bulk actions toolbar (показывается когда выбраны элементы)
        self.bulk_toolbar = QFrame()
        self.bulk_toolbar.setStyleSheet("""
            QFrame {
                background: rgba(156, 123, 255, 0.1);
                border: 1px solid rgba(156, 123, 255, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        self.bulk_toolbar.hide()
        bulk_layout = QHBoxLayout()
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setSpacing(12)
        
        bulk_selected_label = QLabel("Выбрано: 0")
        bulk_selected_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        bulk_selected_label.setStyleSheet("color: #4A2C6B; background: transparent;")
        bulk_layout.addWidget(bulk_selected_label)
        self.bulk_selected_label = bulk_selected_label
        
        bulk_delete_btn = QPushButton("Удалить выбранные")
        bulk_delete_btn.setFixedHeight(32)
        bulk_delete_btn.setStyleSheet("""
            QPushButton {
                background: #DC2626;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #B91C1C;
            }
        """)
        bulk_delete_btn.clicked.connect(self._delete_selected)
        bulk_layout.addWidget(bulk_delete_btn)
        
        bulk_export_btn = QPushButton("Экспорт (CSV)")
        bulk_export_btn.setFixedHeight(32)
        bulk_export_btn.setStyleSheet("""
            QPushButton {
                background: rgba(156, 123, 255, 0.2);
                color: #4A2C6B;
                border: 1px solid rgba(156, 123, 255, 0.4);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(156, 123, 255, 0.3);
            }
        """)
        bulk_export_btn.clicked.connect(self._export_selected)
        bulk_layout.addWidget(bulk_export_btn)
        
        bulk_layout.addStretch()
        
        bulk_clear_btn = QPushButton("✕")
        bulk_clear_btn.setFixedSize(28, 28)
        bulk_clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8B7DA8;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #4A2C6B;
            }
        """)
        bulk_clear_btn.clicked.connect(self._clear_selection)
        bulk_layout.addWidget(bulk_clear_btn)
        
        self.bulk_toolbar.setLayout(bulk_layout)
        card_layout.addWidget(self.bulk_toolbar)
        
        # Пагинация (внизу таблицы)
        pagination_widget = QWidget()
        pagination_widget.setStyleSheet("background: transparent;")
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 16, 0, 0)
        pagination_layout.setSpacing(12)
        pagination_widget.setLayout(pagination_layout)
        
        # Текст с количеством записей
        self.pagination_info = QLabel()
        self.pagination_info.setFont(QFont("Segoe UI", 12))
        self.pagination_info.setStyleSheet("color: #8B7DA8; background: transparent;")
        pagination_layout.addWidget(self.pagination_info)
        
        pagination_layout.addStretch()
        
        # Кнопки навигации
        self.first_page_btn = QPushButton("⏮")
        self.first_page_btn.setFixedSize(32, 32)
        self.first_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.first_page_btn.clicked.connect(lambda: self.go_to_page(1))
        
        self.prev_page_btn = QPushButton("◀")
        self.prev_page_btn.setFixedSize(32, 32)
        self.prev_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_page_btn.clicked.connect(self.prev_page)
        
        # Номер страницы (текст или инпут)
        self.page_info_label = QLabel("1")
        self.page_info_label.setFixedSize(40, 32)
        self.page_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_info_label.setStyleSheet("""
            QLabel {
                background: rgba(156, 123, 255, 0.2);
                border: 1px solid rgba(156, 123, 255, 0.4);
                border-radius: 8px;
                color: #4A2C6B;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        
        self.next_page_btn = QPushButton("▶")
        self.next_page_btn.setFixedSize(32, 32)
        self.next_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_page_btn.clicked.connect(self.next_page)
        
        self.last_page_btn = QPushButton("⏭")
        self.last_page_btn.setFixedSize(32, 32)
        self.last_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        
        # Стили для кнопок пагинации
        pagination_btn_style = """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(200, 182, 226, 0.4);
                border-radius: 8px;
                color: #8B7DA8;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(200, 182, 226, 0.2);
                border-color: rgba(156, 123, 255, 0.5);
                color: #4A2C6B;
            }
            QPushButton:pressed {
                background: rgba(156, 123, 255, 0.15);
            }
        """
        
        self.first_page_btn.setStyleSheet(pagination_btn_style)
        self.prev_page_btn.setStyleSheet(pagination_btn_style)
        self.next_page_btn.setStyleSheet(pagination_btn_style)
        self.last_page_btn.setStyleSheet(pagination_btn_style)
        
        pagination_layout.addWidget(self.first_page_btn)
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.next_page_btn)
        pagination_layout.addWidget(self.last_page_btn)
        
        card_layout.addWidget(pagination_widget)
        
        # Сохраняем все записи для фильтрации
        self.all_history = []
        # Настройки пагинации
        self.items_per_page = 15  # Максимум 15 записей на странице
        self.current_page = 1
        self.filtered_history = []  # Отфильтрованные записи для отображения
        self.current_page_history = []  # Записи, показанные на текущей странице
        
        # Empty state виджет (показывается когда нет истории)
        self.empty_state_widget = QWidget()
        self.empty_state_widget.setStyleSheet("background: transparent;")
        empty_layout = QVBoxLayout()
        empty_layout.setContentsMargins(0, 40, 0, 40)
        empty_layout.setSpacing(16)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("📭")
        empty_icon.setFont(QFont("Segoe UI", 64))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("background: transparent;")
        empty_layout.addWidget(empty_icon)
        
        empty_title = QLabel("История пуста")
        empty_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        empty_title.setStyleSheet("color: #2D1B3D; background: transparent;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        
        empty_text = QLabel("Ваши первые заявки появятся здесь автоматически после отправки.")
        empty_text.setFont(QFont("Segoe UI", 14))
        empty_text.setStyleSheet("color: #8B7DA8; background: transparent;")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setWordWrap(True)
        empty_layout.addWidget(empty_text)
        
        self.empty_state_widget.setLayout(empty_layout)
        self.empty_state_widget.hide()
        card_layout.addWidget(self.empty_state_widget)
        
        content_layout.addWidget(main_card)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Клик по строке открывает детали письма в боковой панели
        self.history_table.cellClicked.connect(self.on_row_clicked)
        
        # Hover эффекты для строк (показываем действия при наведении)
        self.history_table.setMouseTracking(True)
        self.history_table.viewport().setMouseTracking(True)
    
    def load_history(self):
        """Загружает историю писем"""
        username = self._get_funcs()['get_current_username']()
        if not username:
            return
        
        history = self._get_funcs()['get_email_history'](username)
        
        # Сохраняем все записи для фильтрации
        self.all_history = history
        
        # Сбрасываем на первую страницу при загрузке
        self.current_page = 1
        
        # Отображаем историю
        self._display_history(history)
    
    def _display_history(self, history):
        """Отображает список истории в таблице с пагинацией"""
        # Сохраняем отфильтрованную историю
        self.filtered_history = history
        
        # Вычисляем пагинацию
        total_items = len(history)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        
        # Ограничиваем текущую страницу
        if self.current_page > total_pages:
            self.current_page = total_pages
        
        # Вычисляем диапазон для текущей страницы
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        
        # Получаем записи для текущей страницы и запоминаем их
        page_history = history[start_idx:end_idx]
        self.current_page_history = page_history
        
        # Показываем/скрываем empty state
        if len(page_history) == 0:
            self.history_table.hide()
            self.empty_state_widget.show()
            return
        else:
            self.history_table.show()
            self.empty_state_widget.hide()
        
        # Отображаем записи страницы
        self.history_table.setRowCount(len(page_history))
        
        for row, row_data in enumerate(page_history):
            # Проверяем формат данных (может быть с id или без)
            if len(row_data) == 4:
                entry_id, sent_at, recipient_email, lehrstelle = row_data
            else:
                # Старый формат без id
                sent_at, recipient_email, lehrstelle = row_data
                entry_id = None
            
            # Колонка 0: Чекбокс для bulk selection
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox {
                    background: transparent;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #8B7DA8;
                    border-radius: 4px;
                    background: white;
                }
                QCheckBox::indicator:checked {
                    background: #9C7BFF;
                    border-color: #9C7BFF;
                }
            """)
            checkbox.stateChanged.connect(lambda state, r=row: self._on_checkbox_changed(r, state))
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout()
            checkbox_layout.setContentsMargins(8, 0, 0, 0)
            checkbox_layout.addWidget(checkbox)
            checkbox_widget.setLayout(checkbox_layout)
            self.history_table.setCellWidget(row, 0, checkbox_widget)
            
            # Дата и время (третичный текст - самый мелкий и светлый)
            try:
                if isinstance(sent_at, str):
                    dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
                else:
                    dt = sent_at
                date_str = dt.strftime('%d.%m.%Y · %H:%M')
            except:
                date_str = str(sent_at)
            
            date_item = QTableWidgetItem(date_str)
            date_item.setFont(QFont("Segoe UI", 10))  # Меньший размер
            date_item.setForeground(QColor("#A8A0B8"))  # Светло-серый (третичный)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.history_table.setItem(row, 1, date_item)
            
            # Email с аватаром (основной фокус - жирный, крупный)
            email_widget = QWidget()
            email_layout = QHBoxLayout()
            email_layout.setContentsMargins(8, 6, 8, 6)
            email_layout.setSpacing(12)
            
            # Аватар
            avatar = self.create_avatar_widget(recipient_email)
            email_layout.addWidget(avatar)
            
            # Email текст - ЖИРНЫЙ, основной цвет, главный фокус
            email_label = QLabel(recipient_email)
            email_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))  # Крупнее и жирнее
            email_label.setStyleSheet("color: #2D1B3D; background: transparent;")  # Темнее, контрастнее
            email_layout.addWidget(email_label)
            email_layout.addStretch()
            
            # Действия при hover (Copy, Delete) - справа от email
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)
            
            copy_btn = QToolButton()
            copy_btn.setFixedSize(28, 28)
            copy_btn.setText("📋")
            copy_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    opacity: 0;
                }
                QToolButton:hover {
                    background: rgba(156, 123, 255, 0.15);
                    border-radius: 6px;
                    opacity: 1;
                }
            """)
            copy_btn.clicked.connect(lambda checked, eid=entry_id, email=recipient_email, pos=lehrstelle, date=date_str: self._copy_row_data(eid, email, pos, date))
            copy_btn.setToolTip("Скопировать все")
            copy_btn.setObjectName(f"copy_btn_{row}")
            actions_layout.addWidget(copy_btn)
            
            delete_btn = QToolButton()
            delete_btn.setFixedSize(28, 28)
            delete_btn.setText("🗑")
            delete_btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    opacity: 0;
                }
                QToolButton:hover {
                    background: rgba(220, 38, 38, 0.15);
                    border-radius: 6px;
                    opacity: 1;
                }
            """)
            delete_btn.clicked.connect(lambda checked, eid=entry_id: self._delete_single_entry(eid))
            delete_btn.setToolTip("Удалить")
            delete_btn.setObjectName(f"delete_btn_{row}")
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            actions_widget.setObjectName(f"actions_{row}")
            email_layout.addWidget(actions_widget)
            
            email_widget.setLayout(email_layout)
            email_widget.setStyleSheet("background: transparent;")
            self.history_table.setCellWidget(row, 2, email_widget)
            
            # Должность (вторичный текст - средний размер, светлее)
            position_widget = QWidget()
            position_layout = QHBoxLayout()
            position_layout.setContentsMargins(8, 6, 8, 6)
            position_layout.setSpacing(0)
            
            position_label = QLabel(lehrstelle)
            position_label.setFont(QFont("Segoe UI", 12))  # Средний размер
            position_label.setStyleSheet("color: #6C5A8B; background: transparent;")  # Вторичный цвет
            position_layout.addWidget(position_label)
            position_layout.addStretch()
            
            position_widget.setLayout(position_layout)
            position_widget.setStyleSheet("background: transparent;")
            self.history_table.setCellWidget(row, 3, position_widget)
        
        # Устанавливаем ширины столбцов
        self.history_table.setColumnWidth(0, 40)  # Чекбоксы
        self.history_table.setColumnWidth(1, 200)  # Дата
        # Колонки email и должности растягиваются автоматически (Stretch)
        
        # Обновляем информацию о пагинации
        self.update_pagination_info(total_items, start_idx + 1, end_idx, total_pages)
    
    def filter_history(self):
        """Фильтрует историю по поисковому запросу и фильтрам"""
        search_text = self.search_input.text().lower().strip()
        
        # Применяем все фильтры
        filtered = []
        for row_data in self.all_history:
            # Проверяем формат данных
            if len(row_data) == 4:
                entry_id, sent_at, recipient_email, lehrstelle = row_data
            else:
                sent_at, recipient_email, lehrstelle = row_data
                entry_id = None
            
            # Фильтр по дате
            if self.filter_date_from or self.filter_date_to:
                try:
                    if isinstance(sent_at, str):
                        dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
                    else:
                        dt = sent_at
                    date_only = dt.date()
                    
                    if self.filter_date_from and date_only < self.filter_date_from:
                        continue
                    if self.filter_date_to and date_only > self.filter_date_to:
                        continue
                except:
                    pass  # Если не удалось распарсить дату, пропускаем проверку
            
            # Фильтр по email
            if self.filter_email and self.filter_email.lower() not in recipient_email.lower():
                continue
            
            # Фильтр по должности
            if self.filter_position and self.filter_position.lower() not in lehrstelle.lower():
                continue
            
            # Поисковый запрос (ищет во всех полях)
            if search_text:
                try:
                    if isinstance(sent_at, str):
                        dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
                    else:
                        dt = sent_at
                    date_str = dt.strftime('%d.%m.%Y в %H:%M')
                except:
                    date_str = str(sent_at)
                
                if not (search_text in recipient_email.lower() or 
                       search_text in lehrstelle.lower() or 
                       search_text in date_str.lower()):
                    continue
            
            filtered.append(row_data)
        
            # Сбрасываем на первую страницу при фильтрации
            self.current_page = 1
            self._display_history(filtered)
    
    def show_filters_dialog(self):
        """Показывает диалог фильтров"""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("filters") if hasattr(self, 'tr') else "Фильтры")
        dialog.setFixedSize(480, 420)
        
        # Тень для диалога
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(108, 74, 139, 80))
        dialog.setGraphicsEffect(shadow)
        
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 1.0),
                    stop:1 rgba(250, 245, 255, 1.0));
                border-radius: 20px;
                border: 2px solid rgba(200, 182, 226, 0.4);
            }
            QLabel {
                color: #4A2C6B;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
            }
            QDateEdit {
                background: #FFFFFF;
                border: 1.5px solid #E0D0F0;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                color: #4A2C6B;
                min-height: 20px;
            }
            QDateEdit:focus {
                border: 1.5px solid rgba(156, 123, 255, 0.6);
                background: rgba(250, 245, 255, 1.0);
            }
            QDateEdit::drop-down {
                border: none;
                padding-right: 10px;
            }
            QLineEdit {
                background: #FFFFFF;
                border: 1.5px solid #E0D0F0;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                color: #4A2C6B;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1.5px solid rgba(156, 123, 255, 0.6);
                background: rgba(250, 245, 255, 1.0);
            }
            QLineEdit::placeholder {
                color: #9D8DB0;
            }
            QPushButton {
                background: rgba(156, 123, 255, 0.15);
                border: 1.5px solid rgba(156, 123, 255, 0.3);
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                color: #4A2C6B;
                min-height: 20px;
            }
            QPushButton:hover {
                background: rgba(156, 123, 255, 0.25);
                border: 1.5px solid rgba(156, 123, 255, 0.5);
            }
            QPushButton:pressed {
                background: rgba(156, 123, 255, 0.35);
                border: 1.5px solid rgba(156, 123, 255, 0.6);
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)
        
        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Иконка фильтра
        filter_icon_label = QLabel("🔽")
        filter_icon_label.setFont(QFont("Segoe UI", 20))
        filter_icon_label.setStyleSheet("background: transparent;")
        header_layout.addWidget(filter_icon_label)
        
        title = QLabel(self.tr("filters") if hasattr(self, 'tr') else "Фильтры")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #4A2C6B; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Разделитель
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet("background: rgba(156, 137, 184, 0.2); max-height: 1px; border: none;")
        main_layout.addWidget(divider1)
        
        # Форма фильтров
        form_layout = QVBoxLayout()
        form_layout.setSpacing(18)
        
        # Дата от
        date_from_container = QVBoxLayout()
        date_from_container.setSpacing(6)
        date_from_label = QLabel("📅 Дата от:")
        date_from_container.addWidget(date_from_label)
        date_from = QDateEdit()
        date_from.setCalendarPopup(True)
        date_from.setDate(QDate.currentDate().addYears(-1))
        date_from.setDisplayFormat("dd.MM.yyyy")
        if self.filter_date_from:
            date_from.setDate(QDate(self.filter_date_from.year, self.filter_date_from.month, self.filter_date_from.day))
        date_from_container.addWidget(date_from)
        form_layout.addLayout(date_from_container)
        
        # Дата до
        date_to_container = QVBoxLayout()
        date_to_container.setSpacing(6)
        date_to_label = QLabel("📅 Дата до:")
        date_to_container.addWidget(date_to_label)
        date_to = QDateEdit()
        date_to.setCalendarPopup(True)
        date_to.setDate(QDate.currentDate())
        date_to.setDisplayFormat("dd.MM.yyyy")
        if self.filter_date_to:
            date_to.setDate(QDate(self.filter_date_to.year, self.filter_date_to.month, self.filter_date_to.day))
        date_to_container.addWidget(date_to)
        form_layout.addLayout(date_to_container)
        
        # Email
        email_container = QVBoxLayout()
        email_container.setSpacing(6)
        email_label = QLabel("📧 Email:")
        email_container.addWidget(email_label)
        email_filter = QLineEdit()
        email_filter.setPlaceholderText("Введите email для поиска...")
        if self.filter_email:
            email_filter.setText(self.filter_email)
        email_container.addWidget(email_filter)
        form_layout.addLayout(email_container)
        
        # Должность
        position_container = QVBoxLayout()
        position_container.setSpacing(6)
        position_label = QLabel("💼 Должность:")
        position_container.addWidget(position_label)
        position_filter = QLineEdit()
        position_filter.setPlaceholderText("Введите должность для поиска...")
        if self.filter_position:
            position_filter.setText(self.filter_position)
        position_container.addWidget(position_filter)
        form_layout.addLayout(position_container)
        
        main_layout.addLayout(form_layout)
        
        # Разделитель
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet("background: rgba(156, 137, 184, 0.2); max-height: 1px; border: none;")
        main_layout.addWidget(divider2)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(lambda: self.clear_filters(dialog))
        buttons_layout.addWidget(clear_btn)
        
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("✖ Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("✓ Применить")
        apply_btn.setStyleSheet(apply_btn.styleSheet() + """
            QPushButton {
                background: rgba(156, 123, 255, 0.2);
                border: 1.5px solid rgba(156, 123, 255, 0.4);
            }
            QPushButton:hover {
                background: rgba(156, 123, 255, 0.3);
                border: 1.5px solid rgba(156, 123, 255, 0.6);
            }
        """)
        apply_btn.clicked.connect(lambda: self.apply_filters(
            dialog, 
            date_from.date().toPyDate() if date_from.date().isValid() else None,
            date_to.date().toPyDate() if date_to.date().isValid() else None,
            email_filter.text().strip(), position_filter.text().strip()
        ))
        buttons_layout.addWidget(apply_btn)
        
        main_layout.addLayout(buttons_layout)
        dialog.setLayout(main_layout)
        dialog.exec()
    
    def apply_filters(self, dialog, date_from, date_to, email_filter, position_filter):
        """Применяет выбранные фильтры"""
        self.filter_date_from = date_from if date_from else None
        self.filter_date_to = date_to if date_to else None
        self.filter_email = email_filter if email_filter else None
        self.filter_position = position_filter if position_filter else None
        dialog.accept()
        # Сохраняем фильтры в localStorage
        self._save_filters_to_storage()
        # Обновляем фильтр-чипсы
        self._update_filter_chips()
        self.filter_history()
    
    def clear_filters(self, dialog):
        """Очищает все фильтры"""
        self.filter_date_from = None
        self.filter_date_to = None
        self.filter_email = None
        self.filter_position = None
        dialog.accept()
        # Очищаем localStorage
        self._save_filters_to_storage()
        # Обновляем фильтр-чипсы
        self._update_filter_chips()
        self.current_page = 1  # Сбрасываем на первую страницу
        self.filter_history()
    
    def _update_filter_chips(self):
        """Обновляет отображение фильтр-чипсов"""
        # Очищаем старые чипсы
        layout = self.filter_chips_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.filter_chips = []
        
        # Добавляем чипсы для активных фильтров
        if self.filter_position:
            chip = self._create_filter_chip(self.filter_position, "position")
            layout.addWidget(chip)
            self.filter_chips.append(chip)
        
        if self.filter_email:
            chip = self._create_filter_chip(self.filter_email, "email")
            layout.addWidget(chip)
            self.filter_chips.append(chip)
        
        if self.filter_date_from or self.filter_date_to:
            date_str = ""
            if self.filter_date_from and self.filter_date_to:
                date_str = f"{self.filter_date_from.strftime('%d.%m.%Y')} - {self.filter_date_to.strftime('%d.%m.%Y')}"
            elif self.filter_date_from:
                date_str = f"от {self.filter_date_from.strftime('%d.%m.%Y')}"
            elif self.filter_date_to:
                date_str = f"до {self.filter_date_to.strftime('%d.%m.%Y')}"
            if date_str:
                chip = self._create_filter_chip(date_str, "date")
                layout.addWidget(chip)
                self.filter_chips.append(chip)
        
        # Показываем/скрываем контейнер
        if len(self.filter_chips) > 0:
            self.filter_chips_container.show()
        else:
            self.filter_chips_container.hide()
    
    def _create_filter_chip(self, text, filter_type):
        """Создает фильтр-чип с кнопкой удаления"""
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame {
                background: rgba(156, 123, 255, 0.15);
                border: 1px solid rgba(156, 123, 255, 0.3);
                border-radius: 16px;
                padding: 4px 8px;
            }
        """)
        chip_layout = QHBoxLayout()
        chip_layout.setContentsMargins(6, 2, 2, 2)
        chip_layout.setSpacing(6)
        
        # Иконка в зависимости от типа фильтра
        icon_text = "💼" if filter_type == "position" else ("📧" if filter_type == "email" else "📅")
        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("background: transparent; font-size: 12px;")
        chip_layout.addWidget(icon_label)
        
        # Текст фильтра
        text_label = QLabel(text)
        text_label.setFont(QFont("Segoe UI", 11))
        text_label.setStyleSheet("color: #4A2C6B; background: transparent;")
        chip_layout.addWidget(text_label)
        
        # Кнопка удаления
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(18, 18)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8B7DA8;
                font-size: 12px;
                border-radius: 9px;
            }
            QPushButton:hover {
                background: rgba(156, 123, 255, 0.2);
                color: #4A2C6B;
            }
        """)
        
        def remove_filter():
            if filter_type == "position":
                self.filter_position = None
            elif filter_type == "email":
                self.filter_email = None
            elif filter_type == "date":
                self.filter_date_from = None
                self.filter_date_to = None
            self._save_filters_to_storage()
            self._update_filter_chips()
            self.filter_history()
        
        remove_btn.clicked.connect(remove_filter)
        chip_layout.addWidget(remove_btn)
        
        chip.setLayout(chip_layout)
        return chip

    def on_row_clicked(self, row, column):
        """Открывает детали письма в боковой панели при клике по строке"""
        # Игнорируем клик по чекбоксу (колонка 0)
        if column == 0:
            return
        
        if row < 0 or row >= len(self.current_page_history):
            return
        row_data = self.current_page_history[row]
        # Поддерживаем оба формата (с id и без)
        if len(row_data) == 4:
            entry_id, sent_at, recipient_email, lehrstelle = row_data
        else:
            sent_at, recipient_email, lehrstelle = row_data
            entry_id = None

        # Нормализуем дату
        try:
            if isinstance(sent_at, str):
                dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
            else:
                dt = sent_at
            date_str = dt.strftime('%d.%m.%Y · %H:%M')
        except Exception:
            date_str = str(sent_at)

        # Открываем боковую панель вместо диалога
        self._show_details_panel(entry_id, recipient_email, lehrstelle, date_str, sent_at)
    
    def update_pagination_info(self, total_items, start_item, end_item, total_pages):
        """Обновляет информацию о пагинации"""
        # Текст с диапазоном записей
        if total_items > 0:
            info_text = f"Показано {start_item}–{end_item} из {total_items}"
        else:
            info_text = "Показано 0 из 0"
        self.pagination_info.setText(info_text)
        
        # Обновляем номер страницы
        self.page_info_label.setText(str(self.current_page))
        
        # Обновляем состояние кнопок
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)
        self.last_page_btn.setEnabled(self.current_page < total_pages)
        
        # Визуально отключаем кнопки
        disabled_style = """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(200, 182, 226, 0.2);
                border-radius: 8px;
                color: #B8A9C8;
                font-size: 14px;
            }
        """
        enabled_style = """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(200, 182, 226, 0.4);
                border-radius: 8px;
                color: #8B7DA8;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(200, 182, 226, 0.2);
                border-color: rgba(156, 123, 255, 0.5);
                color: #4A2C6B;
            }
            QPushButton:pressed {
                background: rgba(156, 123, 255, 0.15);
            }
        """
        
        self.first_page_btn.setStyleSheet(enabled_style if self.current_page > 1 else disabled_style)
        self.prev_page_btn.setStyleSheet(enabled_style if self.current_page > 1 else disabled_style)
        self.next_page_btn.setStyleSheet(enabled_style if self.current_page < total_pages else disabled_style)
        self.last_page_btn.setStyleSheet(enabled_style if self.current_page < total_pages else disabled_style)
    
    def go_to_page(self, page):
        """Переходит на указанную страницу"""
        total_items = len(self.filtered_history)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        
        if 1 <= page <= total_pages:
            self.current_page = page
            self._display_history(self.filtered_history)
    
    def prev_page(self):
        """Переходит на предыдущую страницу"""
        if self.current_page > 1:
            self.go_to_page(self.current_page - 1)
    
    def next_page(self):
        """Переходит на следующую страницу"""
        total_items = len(self.filtered_history)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        
        if self.current_page < total_pages:
            self.go_to_page(self.current_page + 1)
    
    def go_to_last_page(self):
        """Переходит на последнюю страницу"""
        total_items = len(self.filtered_history)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        self.go_to_page(total_pages)
    
    def clear_history(self):
        """Удаляет всю историю"""
        from pages.notification_widget import NotificationWidget
        reply = QMessageBox.question(
            self,
            self.tr("confirm"),
            self.tr("are_you_sure"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            username = self._get_funcs()['get_current_username']()
            if username and 'clear_email_history' in self._get_funcs():
                success = self._get_funcs()['clear_email_history'](username)
                if success:
                    notification = NotificationWidget(self, self.tr("history_cleared"), is_success=True)
                    notification.show_notification()
                    self.load_history()
                else:
                    notification = NotificationWidget(self, self.tr("error"), is_success=False)
                    notification.show_notification()
    
    def highlight_last_entry(self, sent_at):
        """Выделяет последнюю запись по дате (не используется, так как убрали выделение)"""
        # Метод оставлен для совместимости, но не делает ничего, так как убрали выделение
        pass
    
    def delete_entry(self, entry_id):
        """Удаляет отдельную запись из истории"""
        from pages.notification_widget import NotificationWidget
        reply = QMessageBox.question(
            self,
            self.tr("confirm"),
            self.tr("delete_entry_confirm") if hasattr(self, 'tr') and self.tr("delete_entry_confirm") != "delete_entry_confirm" else "Удалить эту запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            username = self._get_funcs()['get_current_username']()
            if username and 'delete_email_history_entry' in self._get_funcs():
                success = self._get_funcs()['delete_email_history_entry'](entry_id, username)
                if success:
                    notification = NotificationWidget(self, self.tr("entry_deleted") if hasattr(self, 'tr') and self.tr("entry_deleted") != "entry_deleted" else "Запись удалена", is_success=True)
                    notification.show_notification()
                    self.load_history()
                else:
                    notification = NotificationWidget(self, self.tr("error"), is_success=False)
                    notification.show_notification()

    # =========================
    # Дополнительные методы UX
    # =========================

    def _show_details_panel(self, entry_id, recipient_email, lehrstelle, date_str, sent_at):
        """Показывает боковую панель с деталями письма (slide‑in справа)."""
        # Закрываем предыдущую панель, если есть
        self._hide_details_panel()

        self.details_panel = QFrame(self)
        self.details_panel.setFixedWidth(420)
        self.details_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-left: 2px solid rgba(156, 123, 255, 0.3);
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(-6)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.details_panel.setGraphicsEffect(shadow)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок с кнопкой закрытия
        header = QHBoxLayout()
        header.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200, 182, 226, 0.2);
                border: none;
                border-radius: 14px;
                color: #2D1B3D;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(200, 182, 226, 0.3);
            }
        """)
        close_btn.clicked.connect(self._hide_details_panel)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Название (должность)
        title = QLabel(lehrstelle or recipient_email)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2D1B3D; background: transparent;")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Дата и время
        date_label = QLabel(date_str)
        date_label.setFont(QFont("Segoe UI", 12))
        date_label.setStyleSheet("color: #8B7DA8; background: transparent;")
        layout.addWidget(date_label)

        # Разделитель
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: rgba(156, 137, 184, 0.2); max-height: 1px; border: none;")
        layout.addWidget(divider)

        # Email получателя
        email_title = QLabel("Email получателя:")
        email_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        email_title.setStyleSheet("color: #6C5A8B; background: transparent;")
        layout.addWidget(email_title)

        email_value = QLabel(recipient_email)
        email_value.setFont(QFont("Segoe UI", 12))
        email_value.setStyleSheet("color: #2D1B3D; background: transparent;")
        email_value.setWordWrap(True)
        layout.addWidget(email_value)

        # Статус (пока заглушка)
        status_title = QLabel("Статус доставки:")
        status_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        status_title.setStyleSheet("color: #6C5A8B; background: transparent; margin-top: 8px;")
        layout.addWidget(status_title)

        status_value = QLabel("Отправлено")
        status_value.setFont(QFont("Segoe UI", 12))
        status_value.setStyleSheet("color: #16A34A; background: transparent;")
        layout.addWidget(status_value)

        # Тело письма / лог (пока подсказка)
        body_title = QLabel("Содержимое:")
        body_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        body_title.setStyleSheet("color: #6C5A8B; background: transparent; margin-top: 8px;")
        layout.addWidget(body_title)

        body_hint = QLabel(
            self.tr("email_body_preview_unavailable")
            if hasattr(self, "tr") and self.tr("email_body_preview_unavailable") != "email_body_preview_unavailable"
            else "Содержимое письма и лог отправки появятся здесь в следующих версиях."
        )
        body_hint.setWordWrap(True)
        body_hint.setFont(QFont("Segoe UI", 11))
        body_hint.setStyleSheet(
            "color: #8B7DA8; background: rgba(156, 123, 255, 0.05); padding: 10px; border-radius: 8px;"
        )
        layout.addWidget(body_hint)

        layout.addStretch()
        self.details_panel.setLayout(layout)

        # Геометрия и анимация
        parent_rect = self.rect()
        self.details_panel.setGeometry(parent_rect.width(), 0, 420, parent_rect.height())
        self.details_panel.show()
        self.details_panel.raise_()

        self.details_panel_animation = QPropertyAnimation(self.details_panel, b"pos")
        self.details_panel_animation.setDuration(220)
        self.details_panel_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.details_panel_animation.setStartValue(QPoint(parent_rect.width(), 0))
        self.details_panel_animation.setEndValue(QPoint(parent_rect.width() - 420, 0))
        self.details_panel_animation.start()

    def _hide_details_panel(self):
        """Скрывает боковую панель деталей, если она есть."""
        if not getattr(self, "details_panel", None):
            return

        parent_rect = self.rect()
        anim = QPropertyAnimation(self.details_panel, b"pos")
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.setStartValue(self.details_panel.pos())
        anim.setEndValue(QPoint(parent_rect.width(), 0))

        def _cleanup():
            if self.details_panel:
                self.details_panel.hide()
                self.details_panel.deleteLater()
                self.details_panel = None

        anim.finished.connect(_cleanup)
        anim.start()

    def _on_checkbox_changed(self, row: int, state: int):
        """Обновляет множество выбранных строк при изменении чекбокса."""
        if state == Qt.CheckState.Checked.value:
            self.selected_rows.add(row)
        else:
            self.selected_rows.discard(row)
        self._update_bulk_toolbar()

    def _update_bulk_toolbar(self):
        """Показывает/скрывает тулбар bulk‑действий."""
        count = len(getattr(self, "selected_rows", set()))
        if count > 0:
            self.bulk_selected_label.setText(f"Выбрано: {count}")
            self.bulk_toolbar.show()
        else:
            self.bulk_toolbar.hide()

    def _clear_selection(self):
        """Снимает выделение со всех строк и чекбоксов."""
        self.selected_rows.clear()
        for row in range(self.history_table.rowCount()):
            w = self.history_table.cellWidget(row, 0)
            if not w:
                continue
            cb = w.findChild(QCheckBox)
            if cb:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._update_bulk_toolbar()

    def _delete_selected(self):
        """Удаляет все выбранные записи из истории."""
        if not getattr(self, "selected_rows", set()):
            return

        reply = QMessageBox.question(
            self,
            self.tr("confirm") if hasattr(self, "tr") else "Подтверждение",
            f"Удалить {len(self.selected_rows)} выбранных записей?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        username = self._get_funcs()["get_current_username"]()
        deleted = 0
        if username and "delete_email_history_entry" in self._get_funcs():
            for row in sorted(self.selected_rows):
                if row < len(self.current_page_history):
                    data = self.current_page_history[row]
                    if len(data) == 4:
                        entry_id = data[0]
                        if self._get_funcs()["delete_email_history_entry"](entry_id, username):
                            deleted += 1

        from pages.notification_widget import NotificationWidget
        if deleted:
            NotificationWidget(self, f"Удалено записей: {deleted}", is_success=True).show_notification()
            self.selected_rows.clear()
            self._update_bulk_toolbar()
            self.load_history()
        else:
            NotificationWidget(self, self.tr("error"), is_success=False).show_notification()

    def _export_selected(self):
        """Экспортирует выбранные записи в CSV."""
        if not getattr(self, "selected_rows", set()):
            return

        try:
            import csv

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить как CSV",
                f"history_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Дата", "Email получателя", "Должность"])
                for row in sorted(self.selected_rows):
                    if row < len(self.current_page_history):
                        data = self.current_page_history[row]
                        if len(data) == 4:
                            _, sent_at, recipient_email, lehrstelle = data
                        else:
                            sent_at, recipient_email, lehrstelle = data
                        writer.writerow([sent_at, recipient_email, lehrstelle])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать CSV: {e}")

    def _copy_row_data(self, entry_id, email: str, position: str, date: str):
        """Копирует данные одной строки в буфер обмена."""
        text = f"Email: {email}\nДолжность: {position}\nДата: {date}"
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _delete_single_entry(self, entry_id):
        """Удаляет одну запись (обёртка над delete_entry)."""
        if entry_id:
            self.delete_entry(entry_id)

