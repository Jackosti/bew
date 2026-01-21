"""
Виджет данных пользователя (DataWidget)
Версия для использования в настройках
"""
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QTextEdit, QPushButton, QScrollArea, QProgressBar, QComboBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QFont, QColor, QRegularExpressionValidator

# Импортируем функции из основного файла
def get_current_language():
    """Получает текущий язык"""
    try:
        from localization_manager import get_current_language as get_lang
        return get_lang()
    except ImportError:
        return 'de'

def get_user_info():
    """Получает информацию о пользователе"""
    try:
        from email_app import get_user_info
        return get_user_info()
    except ImportError:
        return None

def get_current_username():
    """Получает текущее имя пользователя"""
    try:
        from email_app import get_current_username
        return get_current_username()
    except ImportError:
        return None

def save_user_info(first_name, last_name, phone_number, preserve_registration_date=False):
    """Сохраняет информацию о пользователе"""
    try:
        from email_app import save_user_info
        return save_user_info(first_name, last_name, phone_number, preserve_registration_date)
    except ImportError:
        return None

def tr(key):
    """Получает перевод"""
    try:
        from email_app import tr
        return tr(key)
    except ImportError:
        return key

def get_DB_FILE():
    """Получает путь к файлу базы данных"""
    try:
        from email_app import DB_FILE
        return DB_FILE
    except ImportError:
        return 'email_app.db'


class DataWidget(QWidget):
    """Виджет данных пользователя (без диалоговых свойств)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phone_is_visible = False
        self.is_editing_status = False
        self.used_in_email_fields = {}
        self.setup_ui()
    
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
            return False, tr("phone_format_incorrect_plus49")
        elif cleaned.startswith("0"):
            if len(cleaned) >= 10 and len(cleaned) <= 13 and cleaned[1:].isdigit():
                return True, ""
            return False, tr("phone_format_incorrect_0")
        elif cleaned.startswith("49"):
            if len(cleaned) >= 11 and len(cleaned) <= 14 and cleaned[2:].isdigit():
                return True, ""
            return False, tr("phone_format_incorrect_49")
        return False, tr("phone_format_use_prefix")
    
    def setup_ui(self):
        """Создает интерфейс виджета"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(24)
        self.setLayout(main_layout)
        
        # Заголовок с индикатором заполненности
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(16)
        
        title_label = QLabel(tr("data"))
        title_label.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
                background: transparent;
                letter-spacing: -0.5px;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
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
                border: 1px solid #E4DEFF;
                border-radius: 20px;
            }
        """)
        info_card_layout = QVBoxLayout()
        info_card_layout.setContentsMargins(24, 20, 24, 20)
        info_card_layout.setSpacing(18)
        info_card.setLayout(info_card_layout)
        
        # Заголовок секции
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
        
        # Бейдж "используется в письме" рядом с заголовком
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
        self.first_name_input.setToolTip(tr("enter_first_name_tooltip"))
        self.first_name_input.setMinimumHeight(50)
        self.first_name_input.setStyleSheet("""
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
        self.last_name_input.setToolTip(tr("enter_last_name_tooltip"))
        self.last_name_input.setMinimumHeight(50)
        self.last_name_input.setStyleSheet("""
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
        last_name_container.addWidget(self.last_name_input)
        name_container.addLayout(last_name_container, stretch=1)
        
        info_card_layout.addLayout(name_container)
        
        # Номер телефона с скрытием
        phone_container = QVBoxLayout()
        phone_container.setSpacing(8)
        
        phone_header_layout = QHBoxLayout()
        phone_label_layout = QHBoxLayout()
        phone_header = QLabel(f"📞 {tr('phone_number')}")
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
        phone_validator = QRegularExpressionValidator(QRegularExpression(r'^[\+\s\-\(\)0-9]*$'))
        self.phone_input_dialog.setValidator(phone_validator)
        self.phone_input_dialog.setReadOnly(True)
        self.phone_input_dialog.setMinimumHeight(44)
        placeholder_phone = "+49 151 12345678"
        self.phone_input_dialog.setPlaceholderText(placeholder_phone)
        tooltip_phone = tr("enter_phone_tooltip")
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
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                color: #6C4DFF;
                font-size: 13px;
                font-weight: 600;
                padding: 12px 18px;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
                border-color: #E4DEFF;
            }
        """)
        phone_display_layout.addWidget(self.show_phone_button)
        phone_container.addLayout(phone_display_layout)
        
        # Кнопки сохранения/отмены для телефона
        self.phone_buttons_layout = QHBoxLayout()
        self.phone_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.phone_buttons_layout.setSpacing(10)
        self.phone_buttons_layout.addStretch()
        
        edit_phone_btn = QPushButton("✏️")
        edit_phone_btn.setFixedSize(40, 40)
        edit_phone_btn.setToolTip(tr("edit_phone"))
        edit_phone_btn.clicked.connect(self.edit_phone_dialog)
        edit_phone_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 159, 67, 0.15);
                border: 1.5px solid rgba(255, 169, 77, 0.3);
                border-radius: 10px;
                color: #FF9F43;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 159, 67, 0.25);
                border-color: rgba(255, 169, 77, 0.5);
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
                border: 1.5px solid #DAD2FF;
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
        
        main_layout.addWidget(info_card)
        
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
                border: 1px solid #E4DEFF;
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
        additional_section_title = QLabel(f"⚡ {tr('additional_info')}")
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
        
        # Род занятий (Beruf)
        beruf_container = QVBoxLayout()
        beruf_container.setSpacing(8)
        
        beruf_header_layout = QHBoxLayout()
        beruf_header = QLabel(f"📁 {tr('occupation')}")
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
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self.status_label.setWordWrap(True)
        beruf_display_layout.addWidget(self.status_label, stretch=1)
        
        # Кнопка редактирования в хедере
        edit_status_btn = QPushButton("✏️")
        edit_status_btn.setFixedSize(40, 40)
        edit_status_btn.setToolTip(tr("edit"))
        edit_status_btn.clicked.connect(self.edit_status)
        edit_status_btn.setStyleSheet("""
            QPushButton {
                background-color: #FAF9FE;
                border: 1.5px solid #DAD2FF;
                border-radius: 10px;
                color: #6C4DFF;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
                border-color: #E4DEFF;
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
                border: 1.5px solid #6C4DFF;
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
        self.status_input.hide()
        beruf_container.addWidget(self.status_input)
        
        # Кнопки для статуса
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
                border: 1.5px solid #DAD2FF;
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
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                padding: 12px 16px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border: 1.5px solid #6C4DFF;
                background-color: #FFFFFF;
            }
            QTextEdit:hover {
                border-color: #E4DEFF;
            }
        """)
        additional_card_layout.addWidget(self.about_me_input)
        
        # Виджет уровня немецкого языка
        german_level_label = QLabel(tr("german_level"))
        german_level_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        german_level_label.setStyleSheet("color: #4B3F72; background: transparent;")
        additional_card_layout.addWidget(german_level_label)
        
        self.german_level_combo = QComboBox()
        levels = [
            ("A1", tr("german_level_a1"), "#FF9F43"),
            ("A2", tr("german_level_a2"), "#FFA94D"),
            ("B1", tr("german_level_b1"), "#6C4DFF"),
            ("B2", tr("german_level_b2"), "#8B5CF6"),
            ("C1", tr("german_level_c1"), "#A78BFA"),
            ("C2", tr("german_level_c2"), "#C4B5FD")
        ]
        for level_code, level_text, color in levels:
            self.german_level_combo.addItem(f"{level_code} - {level_text.split(' - ')[-1] if ' - ' in level_text else level_text}")
        
        default_index = next((i for i, (code, _, _) in enumerate(levels) if code == "B1"), 2)
        self.german_level_combo.setCurrentIndex(default_index)
        
        self.german_level_combo.setMinimumHeight(50)
        self.german_level_combo.setStyleSheet("""
            QComboBox {
                background-color: #FAF9FE;
                border: 1.5px solid #DAD2FF;
                border-radius: 12px;
                padding: 14px 18px;
                color: #4B3F72;
                font-size: 14px;
                font-weight: 500;
            }
            QComboBox:focus {
                border: 1.5px solid #6C4DFF;
                background-color: #FFFFFF;
            }
            QComboBox:hover {
                border-color: #6C4DFF;
                background-color: #FFFFFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 40px;
                background: transparent;
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
                border: 1.5px solid #E4DEFF;
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
        
        main_layout.addWidget(additional_card)
        
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
        main_layout.addLayout(buttons_layout)
    
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
            if len(user_info) >= 7:
                status_text = user_info[6] if user_info[6] else ''
                self.status_label.setText(status_text if status_text else tr("no_data"))
            else:
                self.status_label.setText(tr("no_data"))
        
        # Обновляем отображение телефона
        self.update_phone_display_dialog()
        
        # Загружаем "о себе" и уровень языка из базы данных
        username = get_current_username()
        if username:
            conn = sqlite3.connect(get_DB_FILE())
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT about_me, german_level FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result:
                    if result[0]:
                        self.about_me_input.setPlainText(result[0])
                    if result[1] and hasattr(self, 'german_level_combo'):
                        level_text = result[1]
                        index = self.german_level_combo.findText(level_text)
                        if index >= 0:
                            self.german_level_combo.setCurrentIndex(index)
            except:
                try:
                    cursor.execute('SELECT about_me FROM auth_users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        self.about_me_input.setPlainText(result[0])
                except:
                    pass
            conn.close()
        
        # Обновляем заполненность профиля
    
    def update_phone_display_dialog(self):
        """Обновляет отображение номера телефона"""
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
        """Переключает видимость номера телефона"""
        self.phone_is_visible = not self.phone_is_visible
        self.update_phone_display_dialog()
    
    def edit_phone_dialog(self):
        """Включает режим редактирования телефона"""
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
        """Отменяет редактирование телефона"""
        if not hasattr(self, '_real_phone_number'):
            user_info = get_user_info()
            if user_info and len(user_info) >= 3:
                self._real_phone_number = user_info[2] if user_info[2] else ''
            else:
                self._real_phone_number = ''
        
        self.phone_input_dialog.clearFocus()
        self.phone_input_dialog.setReadOnly(True)
        self.phone_input_dialog.setMinimumHeight(44)
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
        """Сохраняет изменения телефона с валидацией"""
        phone_number = self.phone_input_dialog.text().strip()
        
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
        
        self.phone_error_label.hide()
        self._real_phone_number = phone_number
        
        user_info = get_user_info()
        if user_info:
            first_name = user_info[0] if len(user_info) > 0 else ""
            last_name = user_info[1] if len(user_info) > 1 else ""
            save_user_info(first_name, last_name, phone_number, preserve_registration_date=True)
            
            username = user_info[5] if len(user_info) > 5 else None
            if username:
                conn = sqlite3.connect(get_DB_FILE())
                cursor = conn.cursor()
                cursor.execute('UPDATE auth_users SET phone_number = ? WHERE username = ?', (phone_number, username))
                conn.commit()
                conn.close()
        
        self.phone_input_dialog.clearFocus()
        self.phone_input_dialog.setReadOnly(True)
        self.phone_input_dialog.setMinimumHeight(44)
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
        
        # Сохраняем статус и "о себе"
        username = get_current_username()
        if username:
            conn = sqlite3.connect(get_DB_FILE())
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
            try:
                from email_app import _profile_cache
                if username in _profile_cache:
                    del _profile_cache[username]
            except:
                pass
        
        # Обновляем заполненность профиля

