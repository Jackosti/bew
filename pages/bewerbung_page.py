"""
Страница отправки письма (Bewerbung Page)
Современный дизайн согласно фотографии
PyQt6 версия
"""
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QLineEdit,
    QTextEdit, QPushButton, QScrollArea, QFileDialog,
    QMessageBox, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QSizePolicy, QListWidget, QListWidgetItem,
    QMenu, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QPoint, QMimeData, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QDrag, QPainter, QPixmap, QPolygonF, QPen, QPainterPath, QTextOption
from PyQt6.QtCore import QPointF
import math
try:
    from pages.notification_widget import NotificationWidget
except ImportError:
    from notification_widget import NotificationWidget

# Импортируем функции из основного файла
# Используем ленивый импорт, чтобы избежать циклических зависимостей
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
            get_current_username,
            get_google_account_email, get_user_info, save_email_history,
            get_google_account_token, CURRENT_LANGUAGE,
            GOOGLE_OAUTH_AVAILABLE, save_autofill_data, load_autofill_data,
            save_attached_files, load_attached_files, delete_attached_file,
            get_email_history, save_email_draft
        )
        return {
            'get_current_username': get_current_username,
            'get_google_account_email': get_google_account_email,
            'get_user_info': get_user_info,
            'save_email_history': save_email_history,
            'get_google_account_token': get_google_account_token,
            'save_autofill_data': save_autofill_data,
            'load_autofill_data': load_autofill_data,
            'save_attached_files': save_attached_files,
            'load_attached_files': load_attached_files,
            'delete_attached_file': delete_attached_file,
            'get_email_history': get_email_history,
            'save_email_draft': save_email_draft,
            'CURRENT_LANGUAGE': CURRENT_LANGUAGE,
            'GOOGLE_OAUTH_AVAILABLE': GOOGLE_OAUTH_AVAILABLE
        }
    except ImportError:
        return {
            'get_current_username': lambda: None,
            'get_google_account_email': lambda *args, **kwargs: None,
            'get_user_info': lambda *args, **kwargs: None,
            'save_email_history': lambda *args, **kwargs: None,
            'get_google_account_token': lambda *args, **kwargs: None,
            'save_autofill_data': lambda *args, **kwargs: None,
            'load_autofill_data': lambda *args, **kwargs: {'email': '', 'lehrstelle': '', 'firma': ''},
            'save_attached_files': lambda *args, **kwargs: None,
            'load_attached_files': lambda *args, **kwargs: [],
            'delete_attached_file': lambda *args, **kwargs: None,
            'get_email_history': lambda *args, **kwargs: [],
            'save_email_draft': lambda *args, **kwargs: False,
            'CURRENT_LANGUAGE': 'ru',
            'GOOGLE_OAUTH_AVAILABLE': False
        }


class AILoadingWidget(QLabel):
    """Простой виджет загрузки AI - просто "..." в рамке ввода текста"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_animation()
        self.hide()
    
    def setup_ui(self):
        """Создает интерфейс виджета"""
        self.setText("...")
        self.setFont(QFont("Inter", 24, QFont.Weight.Medium))
        self.setStyleSheet("""
            QLabel {
                color: #A78BFA;
                background: transparent;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def setup_animation(self):
        """Настраивает анимацию точек"""
        self.dot_count = 1
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_dots)
        self.animation_timer.setInterval(500)  # 500ms между обновлениями
    
    def animate_dots(self):
        """Анимирует точки"""
        dots = "." * self.dot_count
        self.setText(dots)
        self.dot_count = (self.dot_count % 3) + 1  # 1, 2, 3, 1, 2, 3...
    
    def show_loading(self):
        """Показывает виджет загрузки в центре редактора текста"""
        # Ищем editor_container в родителе
        parent = self.parent()
        if parent:
            # Ищем editor_container
            editor_container = None
            for child in parent.findChildren(QFrame):
                if child.objectName() == "editorContainer":
                    editor_container = child
                    break
            
            if editor_container:
                # Позиционируем в центре контейнера редактора
                container_rect = editor_container.rect()
                self.setParent(editor_container)
                self.setGeometry(
                    container_rect.width() // 2 - 30,
                    container_rect.height() // 2 - 20,
                    60,
                    40
                )
        self.dot_count = 1
        self.animation_timer.start()
        self.show()
        self.raise_()
    
    def hide_loading(self):
        """Скрывает виджет загрузки"""
        self.animation_timer.stop()
        self.hide()


class IconLineEditContainer(QWidget):
    """Контейнер для QLineEdit с иконкой внутри"""
    def __init__(self, input_field, icon, parent=None):
        super().__init__(parent)
        self.input_field = input_field
        self.icon_widget = QLabel(icon, self)
        self.icon_widget.setFont(QFont("Segoe UI", 16))
        self.icon_widget.setStyleSheet("color: #9B9AA8; background: transparent;")
        self.icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(input_field)
        self.setLayout(layout)
        
        # Устанавливаем иконку после показа виджета
        QTimer.singleShot(100, self.update_icon_position)
    
    def update_icon_position(self):
        """Обновляет позицию иконки"""
        if self.width() > 0:
            self.icon_widget.setFixedSize(24, self.height())
            self.icon_widget.move(self.width() - 32, 0)
            self.icon_widget.raise_()
    
    def resizeEvent(self, event):
        """Переопределяем resizeEvent для обновления позиции иконки"""
        super().resizeEvent(event)
        self.update_icon_position()


class BewerbungPage(QWidget):
    """Страница отправки письма с современным дизайном (PyQt6)"""
    # Кэш иконок файлов (вынесен из методов для оптимизации)
    _FILE_ICON_MAP = {
        'pdf': ('📄', '#E14B4B'),
        'png': ('🖼', '#4A90E2'),
        'jpg': ('🖼', '#4A90E2'),
        'jpeg': ('🖼', '#4A90E2'),
        'doc': ('📝', '#2B579A'),
        'docx': ('📝', '#2B579A'),
        'txt': ('📃', '#666666'),
        'py': ('🐍', '#3776AB'),
    }
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.attached_files = []
        self.is_active = False
        self.ai_generated_pdf_path = None
        self.ai_loading_widget = None
        self._files_card_saved_height = None  # Для сохранения высоты карточки файлов
        
        # Кэш для оптимизации
        self._widget_cache = {}
        self._style_cache = {}
        
        # Инициализируем функции как None, загрузим позже
        self._tr = None
        self._funcs = None
        
        # Включаем drag & drop для всего виджета
        self.setAcceptDrops(True)
        
        self.setup_ui()
        
        # Инициализируем таймер автосохранения
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(False)
        self.auto_save_timer.setInterval(30000)
        
        # Таймер для debounce автосохранения полей (оптимизация)
        self.field_save_timer = QTimer()
        self.field_save_timer.setSingleShot(True)
        self.field_save_timer.setInterval(1000)
        self.field_save_timer.timeout.connect(self._save_fields_data)

        # Загружаем функции после создания UI (избегаем циклических зависимостей)
        QTimer.singleShot(0, self._load_functions)
        
        # Оптимизация: объединяем инициализацию в один таймер
        def delayed_init():
            self.update_char_count()
            self.update_last_sent_time()
        QTimer.singleShot(100, delayed_init)
    
    def activate(self):
        """Активирует страницу"""
        if not self.is_active:
            self.is_active = True
    
    def deactivate(self):
        """Деактивирует страницу"""
        if self.is_active:
            self.is_active = False
    
    def _load_functions(self):
        """Загружает функции после инициализации"""
        self._tr = get_tr()
        self._funcs = get_functions()
        self.load_draft_data()
        
        # Подключаем таймер автосохранения (метод auto_save уже определен)
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.timeout.connect(self.auto_save)
            self.auto_save_timer.start()
    
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
    
    def auto_save(self):
        """Автоматически сохраняет прикрепленные файлы и данные полей"""
        try:
            funcs = self._get_funcs()
            username = funcs.get('get_current_username')()
            if not username:
                return
            
            # Сохраняем прикрепленные файлы
            if hasattr(self, 'attached_files') and self.attached_files:
                save_files_func = funcs.get('save_attached_files')
                if save_files_func:
                    save_files_func(username, self.attached_files)
            
            # Сохраняем данные полей (email, должность, фирма)
            self.on_field_changed()
        except Exception as e:
            # Тихая ошибка - не показываем пользователю при автосохранении
            print(f"Ошибка автосохранения файлов: {e}")
    
    def update_texts(self):
        """Обновляет тексты на странице после смены языка"""
        # Перезагружаем функции для получения обновленного CURRENT_LANGUAGE
        self._tr = get_tr()
        # Обновляем все тексты, которые используют tr()
        # Основные элементы обновятся автоматически через tr(), но можно обновить и другие
        if hasattr(self, 'attach_btn'):
            self.attach_btn.setText(f"☁ {self.tr('attach_files')}")
        if hasattr(self, 'body_text'):
            if not self.body_text.toPlainText():
                self.body_text.setPlaceholderText(self.tr("letter_text_placeholder"))
    
    def setup_ui(self):
        """Создает интерфейс страницы отправки письма согласно фотографии"""
        # Главный контейнер с градиентным фоном
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Устанавливаем фон через менеджер тем (как в profile_page.py)
        from theme_manager import get_theme_manager
        theme_manager = get_theme_manager()
        theme = theme_manager.get_current_theme()
        colors = theme["colors"]
        
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
        
        # Заголовок и подзаголовок вверху (фон как остальной)
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent; border-radius: 0px;")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(24, 24, 24, 0)
        header_layout.setSpacing(8)
        header_widget.setLayout(header_layout)
        
        main_title = QLabel(self.tr("send_email"))
        main_title.setFont(QFont("Inter", 22, QFont.Weight.Bold))
        main_title.setStyleSheet("color: #2E2E38; background: transparent;")
        
        # Добавляем тень для заголовка
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(8)
        title_shadow.setXOffset(0)
        title_shadow.setYOffset(2)
        title_shadow.setColor(QColor(46, 46, 56, 30))
        main_title.setGraphicsEffect(title_shadow)
        header_layout.addWidget(main_title)
        
        # Подзаголовок удален
        
        main_layout.addWidget(header_widget)
        
        # Контент виджет (без ScrollArea чтобы не было ползунка)
        content_widget = QWidget()
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        content_widget.setLayout(content_layout)
        
        # === ЛЕВАЯ ПАНЕЛЬ: "Данные получателя" (с белой карточкой) ===
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel, 2)  # Левая панель уже (2)
        
        # === ПРАВАЯ ПАНЕЛЬ: "Текст письма" (с рамкой) - растянута по ширине ===
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, 15)  # Правая панель шире (15 вместо 13)
        
        main_layout.addWidget(content_widget)
    
    def create_left_panel(self):
        """Создает левую панель 'Данные получателя'"""
        # Контейнер для всей левой панели
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_main_layout = QVBoxLayout()
        left_main_layout.setContentsMargins(0, 0, 0, 0)
        left_main_layout.setSpacing(14)  # Уменьшено для компактности
        left_widget.setLayout(left_main_layout)
        
        # Карточка "Данные получателя" (идентично виджету "Файлы")
        left_card = QFrame()
        left_card.setObjectName("leftCard")
        # Устанавливаем размерную политику, чтобы карточка не влияла на размер других виджетов
        left_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        left_card.setStyleSheet("""
            QFrame#leftCard {
                background-color: #FAFAFE;
                border: none;
                border-radius: 18px;
                padding: 0px;
            }
        """)
        
        # Тень для карточки (лиловая) - как у "Файлы"
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(25)
        card_shadow.setXOffset(0)
        card_shadow.setYOffset(10)
        card_shadow.setColor(QColor(167, 139, 250, 20))
        left_card.setGraphicsEffect(card_shadow)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(12, 12, 12, 12)  # Как у "Файлы"
        card_layout.setSpacing(8)  # Как у "Файлы"
        left_card.setLayout(card_layout)
        
        # Заголовок с иконкой и кнопкой toggle (идентично "Файлы")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)  # Как у "Файлы"
        
        # Силуэт пользователя со сплошной заливкой (светло-фиолетовый)
        user_pixmap = QPixmap(24, 24)
        user_pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(user_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)  # Без обводки
        painter.setBrush(QColor(200, 180, 255))  # Светло-фиолетовая заливка
        # Рисуем силуэт: круг (голова) + трапеция (тело)
        # Голова (круг)
        painter.drawEllipse(8, 4, 8, 8)
        # Тело (трапеция)
        body_points = QPolygonF([
            QPointF(6, 14),
            QPointF(10, 20),
            QPointF(14, 20),
            QPointF(18, 14)
        ])
        painter.drawPolygon(body_points)
        painter.end()
        title_icon = QLabel()
        title_icon.setPixmap(user_pixmap)
        header_layout.addWidget(title_icon)
        
        # Текст рядом с эмодзи (как у "Файлы")
        self.recipient_data_title = QLabel(self.tr("recipient_data"))
        self.recipient_data_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))  # Как у "Файлы"
        self.recipient_data_title.setStyleSheet("color: #2E2E38; background: transparent;")
        header_layout.addWidget(self.recipient_data_title)
        
        header_layout.addStretch()  # Как у "Файлы"
        
        # Кнопка скрытия/показа (стрелка) - идентично "Файлы"
        self.recipient_data_toggle_btn = QPushButton("▲")
        self.recipient_data_toggle_btn.setObjectName("recipientDataToggleBtn")
        self.recipient_data_toggle_btn.setFixedSize(24, 24)
        self.recipient_data_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recipient_data_toggle_btn.setStyleSheet("""
            QPushButton#recipientDataToggleBtn {
                background: transparent;
                border: none;
                color: #6E6D7A;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#recipientDataToggleBtn:hover {
                color: #2E2E38;
                background: rgba(46, 46, 56, 0.05);
                border-radius: 4px;
            }
        """)
        self.recipient_data_toggle_btn.clicked.connect(self.toggle_recipient_data_visibility)
        header_layout.addWidget(self.recipient_data_toggle_btn)
        
        card_layout.addLayout(header_layout)
        
        # Контейнер для данных получателя (скрываемый) - идентично "Файлы"
        self.recipient_data_content_widget = QWidget()
        self.recipient_data_content_widget.setStyleSheet("background: transparent;")
        recipient_data_content_layout = QVBoxLayout()
        recipient_data_content_layout.setContentsMargins(0, 0, 0, 0)
        recipient_data_content_layout.setSpacing(8)  # Как у "Файлы"
        self.recipient_data_content_widget.setLayout(recipient_data_content_layout)
        
        # Должность с иконкой (без лейбла, эмодзи слева)
        position_group = self.create_input_group("", "💼", placeholder=self.tr("position_placeholder"), icon_left=True)
        self.lehrstelle_input = position_group['input']
        # Отключаем автодополнение и автозамену для поля ввода (комбинируем флаги)
        self.lehrstelle_input.setInputMethodHints(
            Qt.InputMethodHint.ImhNoPredictiveText | 
            Qt.InputMethodHint.ImhNoAutoUppercase |
            Qt.InputMethodHint.ImhPreferLowercase |
            Qt.InputMethodHint.ImhHiddenText
        )
        # Отключаем автозаполнение через свойство Qt
        self.lehrstelle_input.setProperty("autocomplete", "off")
        # Отключаем системную автозамену (IME) - более агрессивный метод
        self.lehrstelle_input.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, False)
        self.lehrstelle_input.textChanged.connect(self.on_field_changed)  # Автосохранение
        # Убираем ошибку при вводе текста
        def clear_lehrstelle_error():
            if hasattr(self.lehrstelle_input, '_has_error') and self.lehrstelle_input._has_error:
                if self.lehrstelle_input.text().strip():
                    self._clear_field_error(self.lehrstelle_input)
        self.lehrstelle_input.textChanged.connect(clear_lehrstelle_error)
        recipient_data_content_layout.addWidget(position_group['widget'])
        
        # Компания с иконкой (без лейбла, эмодзи слева)
        company_group = self.create_input_group("", "🏢", placeholder=self.tr("company_placeholder"), icon_left=True)
        self.firma_input = company_group['input']
        self.firma_input.textChanged.connect(self.on_field_changed)  # Автосохранение
        # Убираем ошибку при вводе текста
        def clear_firma_error():
            if hasattr(self.firma_input, '_has_error') and self.firma_input._has_error:
                if self.firma_input.text().strip():
                    self._clear_field_error(self.firma_input)
        self.firma_input.textChanged.connect(clear_firma_error)
        recipient_data_content_layout.addWidget(company_group['widget'])
        
        card_layout.addWidget(self.recipient_data_content_widget)
        
        # Добавляем карточку в основной layout
        left_main_layout.addWidget(left_card)
        
        # Виджет для прикрепления файлов слева
        files_left_widget = self.create_left_files_widget()
        # Добавляем с stretch=0, чтобы виджет не растягивался и сохранял свой размер
        left_main_layout.addWidget(files_left_widget, 0)
        
        # Виджет для дополнения к промпту AI
        ai_prompt_widget = self.create_ai_prompt_widget()
        # Устанавливаем размерную политику для виджета промпта, чтобы он не влиял на размер файлов
        ai_prompt_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        left_main_layout.addWidget(ai_prompt_widget, 0)
        
        # Статус сохранения внизу
        status_widget_bottom = QWidget()
        status_widget_bottom.setStyleSheet("background: transparent;")
        status_layout_bottom = QHBoxLayout()
        status_layout_bottom.setContentsMargins(0, 0, 0, 0)
        status_layout_bottom.setSpacing(6)
        status_widget_bottom.setLayout(status_layout_bottom)
        
        cloud_icon_bottom = QLabel("☁")
        cloud_icon_bottom.setFont(QFont("Segoe UI", 12))
        status_layout_bottom.addWidget(cloud_icon_bottom)
        
        # Удаляем старый статус сохранения (больше не нужен)
        # left_main_layout.addWidget(status_widget_bottom)
        left_main_layout.addStretch()
        
        return left_widget
    
    def create_input_group(self, label_text, icon, required=False, placeholder="", icon_inside=False, icon_position="right", show_label=False, icon_left=False):
        """Создает группу поля ввода с label, иконкой и input"""
        group = QWidget()
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(8)
        group.setLayout(group_layout)
        
        # Label с иконкой слева (только если show_label=True)
        if show_label and not icon_inside:
            label_layout = QHBoxLayout()
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.setSpacing(8)
            
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI", 14))
            icon_label.setStyleSheet("color: #A78BFA; background: transparent;")
            label_layout.addWidget(icon_label)
            
            label = QLabel(label_text)
            label.setFont(QFont("Inter", 13, QFont.Weight.Medium))
            label.setStyleSheet("color: #2E2E38; background: transparent;")
            label_layout.addWidget(label)
            
            if required:
                asterisk = QLabel("*")
                asterisk.setFont(QFont("Inter", 13, QFont.Weight.Bold))
                asterisk.setStyleSheet("color: #E14B4B; background: transparent;")
                label_layout.addWidget(asterisk)
            
            label_layout.addStretch()
            group_layout.addLayout(label_layout)
        elif show_label and icon_inside:
            # Для email - label без иконки, иконка будет внутри поля
            label_layout = QHBoxLayout()
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.setSpacing(8)
            
            label = QLabel(label_text)
            label.setFont(QFont("Inter", 13, QFont.Weight.Medium))
            label.setStyleSheet("color: #2E2E38; background: transparent;")
            label_layout.addWidget(label)
            
            if required:
                asterisk = QLabel("*")
                asterisk.setFont(QFont("Inter", 13, QFont.Weight.Bold))
                asterisk.setStyleSheet("color: #E14B4B; background: transparent;")
                label_layout.addWidget(asterisk)
            
            label_layout.addStretch()
            group_layout.addLayout(label_layout)
        
        # Input поле с иконкой внутри (если нужно)
        if icon_inside:
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder)
            # Увеличиваем padding справа для места под иконку
            input_field.setStyleSheet("""
                QLineEdit {
                    background: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    padding: 12px 40px 12px 16px;
                    font-size: 15px;
                    color: #2E2E38;
                }
                QLineEdit:focus {
                    background: #FFFFFF;
                    border: none;
                }
                QLineEdit::placeholder {
                    color: #B4B2C4;
                }
            """)
            
            # Используем специальный контейнер с иконкой
            input_container = IconLineEditContainer(input_field, icon)
            group_layout.addWidget(input_container)
        elif icon_left:
            # Поле с иконкой слева (снаружи поля)
            input_row = QHBoxLayout()
            input_row.setContentsMargins(0, 0, 0, 0)
            input_row.setSpacing(8)
            
            # Иконка слева
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI", 16))
            icon_label.setStyleSheet("color: #A78BFA; background: transparent;")
            icon_label.setFixedWidth(24)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Выравнивание по вертикали
            input_row.addWidget(icon_label)
            
            # Уменьшаем spacing для приближения текста к эмодзи
            input_row.setSpacing(5)  # Было 8, стало 5
            
            # Поле ввода
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder)
            input_field.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: 2px solid transparent;
                    border-radius: 12px;
                    padding: 12px 16px;
                    font-size: 16px;
                    color: #2E2E38;
                }
                QLineEdit:focus {
                    border: 2px solid transparent;
                }
                QLineEdit::placeholder {
                    color: #B4B2C4;
                    font-size: 9px;
                }
            """)
            input_row.addWidget(input_field, 1)
            group_layout.addLayout(input_row)
        else:
            # Обычное поле без иконки внутри
            input_field = QLineEdit()
            input_field.setPlaceholderText(placeholder)
            input_field.setStyleSheet("""
                QLineEdit {
                    background-color: #FFFFFF;
                    border: none;
                    border-radius: 12px;
                    padding: 12px 16px;
                    font-size: 16px;
                    color: #2E2E38;
                }
                QLineEdit:focus {
                    border: none;
                }
                QLineEdit::placeholder {
                    color: #B4B2C4;
                }
            """)
            group_layout.addWidget(input_field)
        
        return {'widget': group, 'input': input_field}
    
    def create_right_panel(self):
        """Создает правую панель 'Текст письма' с рамкой"""
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        
        right_main_layout = QVBoxLayout()
        right_main_layout.setContentsMargins(0, 0, 0, 0)
        right_main_layout.setSpacing(0)
        right_widget.setLayout(right_main_layout)
        
        # Рамка вокруг всего содержимого правой панели
        right_frame = QFrame()
        right_frame.setObjectName("rightPanelFrame")
        right_frame.setStyleSheet("""
            QFrame#rightPanelFrame {
                background-color: #FFFFFF;
                border: 1px solid rgba(167, 139, 250, 0.2);
                border-radius: 18px;
                padding: 20px;
            }
        """)
        # Убираем ограничения, чтобы виджет истории не обрезался
        right_frame.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        # Разрешаем виджетам выходить за границы рамки
        right_widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        # Тень для рамки (лиловая)
        frame_shadow = QGraphicsDropShadowEffect()
        frame_shadow.setBlurRadius(25)
        frame_shadow.setXOffset(0)
        frame_shadow.setYOffset(10)
        frame_shadow.setColor(QColor(167, 139, 250, 20))
        right_frame.setGraphicsEffect(frame_shadow)
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)  # Уменьшено для поднятия темы выше
        right_frame.setLayout(right_layout)
        
        # Email получателя с лейблом "Кому"
        email_row = QHBoxLayout()
        email_row.setContentsMargins(0, 0, 0, 0)
        email_row.setSpacing(10)
        
        # Лейбл "Кому:"
        try:
            to_text = self.tr("to")
        except:
            to_text = "Кому"
        email_label = QLabel(f"{to_text}:")
        email_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        email_label.setStyleSheet("color: #2E2E38; background: transparent;")
        email_label.setFixedWidth(50)
        email_row.addWidget(email_label)
        
        # Email поле (без эмодзи письма) с проверкой и галочкой
        email_group = self.create_input_group("", "", required=True, placeholder=self.tr("recipient_email_placeholder"), icon_inside=False)
        self.recipient_email_input = email_group['input']
        self.recipient_email_input.textChanged.connect(self.on_field_changed)
        # Оптимизация: debounce для проверки истории email
        self.email_history_timer = QTimer()
        self.email_history_timer.setSingleShot(True)
        self.email_history_timer.setInterval(500)  # 500ms задержка
        self.email_history_timer.timeout.connect(self.check_email_history)
        
        def on_email_changed():
            self.email_history_timer.stop()
            self.email_history_timer.start()
            self.validate_email()
        
        self.recipient_email_input.textChanged.connect(on_email_changed)
        
        # Контейнер для email с иконкой истории и галочкой справа
        email_container = QWidget()
        email_container.setStyleSheet("background: transparent;")
        email_container_layout = QHBoxLayout()
        email_container_layout.setContentsMargins(0, 0, 0, 0)
        email_container_layout.setSpacing(5)
        email_container.setLayout(email_container_layout)
        email_container_layout.addWidget(email_group['widget'], 1)
        
        # Галочка для валидного email (справа от поля)
        self.email_check_icon = QLabel("✓")
        self.email_check_icon.setFixedSize(24, 24)
        self.email_check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.email_check_icon.setStyleSheet("""
            QLabel {
                color: #10B981;
                background: transparent;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.email_check_icon.hide()
        email_container_layout.addWidget(self.email_check_icon)
        
        # Иконка предупреждения "!" для истории отправки (справа от поля)
        self.email_history_icon = QLabel("")
        self.email_history_icon.setFixedSize(24, 24)
        self.email_history_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.email_history_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.email_history_icon.setStyleSheet("""
            QLabel {
                color: #8B7CF6;
                background: rgba(139, 124, 246, 0.15);
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.email_history_icon.setText("!")
        self.email_history_icon.hide()
        # Обработчик клика для показа/скрытия встроенного виджета
        def icon_clicked(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.toggle_email_history_widget()
        self.email_history_icon.mousePressEvent = icon_clicked
        email_container_layout.addWidget(self.email_history_icon)
        
        # Сохраняем текст истории для виджета
        self.email_history_text = ""
        
        # Встроенный виджет истории (скрыт по умолчанию, внутри рамки "Текст письма")
        # Родитель будет установлен позже в create_right_panel на right_frame
        self.email_history_widget = QFrame()
        self.email_history_widget.setObjectName("emailHistoryWidget")
        self.email_history_widget.setStyleSheet("""
            QFrame#emailHistoryWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FAFAFE, stop:1 #EFEAF7);
                border: 1px solid rgba(139, 124, 246, 0.3);
                border-radius: 12px;
                padding: 0px;
            }
        """)
        # Не используем флаги окна, чтобы виджет был внутри рамки
        self.email_history_widget.hide()
        self.email_history_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        history_layout = QHBoxLayout()
        history_layout.setContentsMargins(12, 10, 12, 10)
        history_layout.setSpacing(10)
        
        # Иконка "!"
        history_icon = QLabel("!")
        history_icon.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        history_icon.setStyleSheet("""
            QLabel {
                color: #8B7CF6;
                background: rgba(139, 124, 246, 0.15);
                border-radius: 10px;
                padding: 4px 8px;
            }
        """)
        history_icon.setFixedSize(28, 28)
        history_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_layout.addWidget(history_icon)
        
        # Текст сообщения
        self.email_history_message = QLabel("")
        self.email_history_message.setFont(QFont("Inter", 9, QFont.Weight.Medium))  # Уменьшен размер
        self.email_history_message.setStyleSheet("""
            QLabel {
                color: #2E2E38;
                background: transparent;
            }
        """)
        self.email_history_message.setWordWrap(False)  # Отключаем перенос, чтобы текст растягивался
        history_layout.addWidget(self.email_history_message, 1)
        
        # Кнопка закрытия
        close_history_btn = QPushButton("×")
        close_history_btn.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        close_history_btn.setFixedSize(24, 24)
        close_history_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8B7CF6;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(139, 124, 246, 0.2);
            }
        """)
        close_history_btn.clicked.connect(self.email_history_widget.hide)
        history_layout.addWidget(close_history_btn)
        
        self.email_history_widget.setLayout(history_layout)
        
        email_row.addWidget(email_container, 1)
        right_layout.addLayout(email_row)
        
        # Уменьшаем отступ между email и темой (виджет истории позиционируется абсолютно)
        right_layout.addSpacing(-8)
        
        # Тема письма с лейблом "Тема:" - всегда на немецком
        subject_row = QHBoxLayout()
        subject_row.setContentsMargins(0, 0, 0, 0)
        subject_row.setSpacing(10)
        
        # Лейбл "Тема:"
        try:
            subject_text = self.tr("subject")
        except:
            subject_text = "Тема:"
        # Убираем двоеточие если оно уже есть в локализации
        if subject_text.endswith(":"):
            subject_label = QLabel(subject_text)
        else:
            subject_label = QLabel(f"{subject_text}:")
        subject_label.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        subject_label.setStyleSheet("color: #2E2E38; background: transparent;")
        subject_label.setFixedWidth(50)
        subject_row.addWidget(subject_label)
        
        from email_app import tr
        subject_placeholder = tr("email_subject_placeholder")
        subject_group = self.create_input_group("", "📌", placeholder=subject_placeholder)
        self.email_subject_input = subject_group['input']
        # Отключаем автодополнение и автозамену для поля темы письма
        self.email_subject_input.setInputMethodHints(
            Qt.InputMethodHint.ImhNoPredictiveText | 
            Qt.InputMethodHint.ImhNoAutoUppercase |
            Qt.InputMethodHint.ImhPreferLowercase |
            Qt.InputMethodHint.ImhHiddenText
        )
        self.email_subject_input.setProperty("autocomplete", "off")
        self.email_subject_input.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, False)
        # Флаг для отслеживания ручного редактирования темы
        self._subject_manually_edited = False
        self.email_subject_input.textChanged.connect(self._on_subject_changed)
        self.email_subject_input.textEdited.connect(lambda: setattr(self, '_subject_manually_edited', True))
        self.lehrstelle_input.textChanged.connect(self.update_email_subject)
        
        # Увеличиваем размер шрифта темы письма и padding для поднятия по высоте
        self.email_subject_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 14px 16px;
                font-size: 16px;
                color: #2E2E38;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: none;
            }
            QLineEdit::placeholder {
                color: #B4B2C4;
            }
        """)
        
        subject_row.addWidget(subject_group['widget'], 1)
        right_layout.addLayout(subject_row)
        
        # Контейнер для редактора с рамкой и счетчиком символов внизу (увеличенный размер)
        editor_container = QFrame()
        editor_container.setObjectName("editorContainer")
        editor_container.setStyleSheet("""
            QFrame#editorContainer {
                background-color: #FFFFFF;
                border: 1px solid rgba(167, 139, 250, 0.15);
                border-radius: 12px;
                padding: 0px;
                min-height: 450px;
            }
        """)
        
        # Тень для контейнера редактора (лиловая)
        editor_shadow = QGraphicsDropShadowEffect()
        editor_shadow.setBlurRadius(15)
        editor_shadow.setXOffset(0)
        editor_shadow.setYOffset(4)
        editor_shadow.setColor(QColor(167, 139, 250, 15))
        editor_container.setGraphicsEffect(editor_shadow)
        editor_container_layout = QVBoxLayout()
        editor_container_layout.setContentsMargins(0, 0, 0, 0)
        editor_container_layout.setSpacing(0)
        editor_container.setLayout(editor_container_layout)
        
        # Текстовый редактор (увеличенный размер, без рамки так как рамка у контейнера)
        # Используем минимальную и максимальную высоту для правильной работы скролла
        editor = QTextEdit()
        editor.setPlaceholderText(self.tr("letter_text_placeholder"))
        self.body_text = editor  # Сохраняем ссылку для автосохранения
        # Устанавливаем увеличенную высоту по умолчанию
        editor.setMinimumHeight(450)
        editor.setMaximumHeight(700)
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        editor.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                padding: 20px 20px 50px 20px;
                font-size: 13px;
                color: #2E2E38;
                line-height: 1.6;
                text-align: left;
                selection-background-color: rgba(167, 139, 250, 0.3);
                selection-color: #2E2E38;
            }
            QTextEdit::placeholder {
                color: #B4B2C4;
            }
            QScrollBar:vertical {
                background: rgba(230, 232, 236, 0.3);
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.5),
                    stop:1 rgba(200, 180, 240, 0.3));
                border-radius: 5px;
                min-height: 30px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.7),
                    stop:1 rgba(220, 200, 250, 0.5));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: rgba(214, 211, 240, 0.3);
                height: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(124, 131, 253, 0.4),
                    stop:1 rgba(214, 211, 240, 0.3));
                border-radius: 4px;
                min-width: 30px;
                margin: 1px;
            }
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(107, 114, 232, 0.5),
                    stop:1 rgba(196, 190, 232, 0.4));
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        # Оптимизация: debounce для обновления счетчика символов
        self.char_count_timer = QTimer()
        self.char_count_timer.setSingleShot(True)
        self.char_count_timer.setInterval(300)  # 300ms задержка
        self.char_count_timer.timeout.connect(self.update_char_count)
        
        def on_text_changed_debounced():
            self.char_count_timer.stop()
            self.char_count_timer.start()
        
        editor.textChanged.connect(on_text_changed_debounced)
        # Включаем контекстное меню для форматирования текста
        editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        editor.customContextMenuRequested.connect(self.show_text_format_menu)
        # Оптимизация выделения текста - отключаем обновление при выделении
        editor.setUpdatesEnabled(True)
        # Используем оптимизированную обработку событий
        editor.installEventFilter(self)
        # Включаем плавную прокрутку - скролл появляется автоматически при необходимости
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Плавная прокрутка - быстрее для удобства
        editor.verticalScrollBar().setSingleStep(5)
        editor.horizontalScrollBar().setSingleStep(5)
        
        # Убираем избыточную проверку скролла - QTextEdit сам управляет скроллом
        
        self.body_text = editor
        
        # Добавляем редактор в контейнер - он будет занимать доступное пространство
        editor_container_layout.addWidget(editor, 1)  # Растягивается
        
        # Счетчик символов ВНИЗУ СПРАВА в рамке редактора
        char_count_wrapper = QWidget(editor_container)
        char_count_wrapper.setStyleSheet("background: transparent;")
        char_count_wrapper.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        char_count_wrapper_layout = QHBoxLayout()
        char_count_wrapper_layout.setContentsMargins(0, 0, 12, 8)
        char_count_wrapper_layout.setSpacing(3)
        char_count_wrapper.setLayout(char_count_wrapper_layout)
        char_count_wrapper_layout.addStretch()
        
        self.char_count_number = QLabel("0")
        self.char_count_number.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.char_count_number.setStyleSheet("color: #9B9AA8; background: transparent;")
        char_count_wrapper_layout.addWidget(self.char_count_number)
        
        self.char_count_text = QLabel(self.tr("characters"))
        self.char_count_text.setFont(QFont("Inter", 11))
        self.char_count_text.setStyleSheet("color: #9B9AA8; background: transparent;")
        char_count_wrapper_layout.addWidget(self.char_count_text)
        
        # Оптимизация: объединяем позиционирование счетчика и AI виджета
        def update_positions():
            if char_count_wrapper.parent():
                char_count_wrapper.setGeometry(
                    editor_container.width() - 120, 
                    editor_container.height() - 35, 
                    110, 30
                )
            if ai_widget.parent():
                ai_widget.setGeometry(0, editor_container.height() - 56, 200, 48)
        
        QTimer.singleShot(100, update_positions)
        
        # AI кнопка с текстом внизу слева в рамке редактора
        ai_widget = QWidget(editor_container)
        ai_widget.setStyleSheet("background: transparent;")
        ai_layout = QHBoxLayout()
        ai_layout.setContentsMargins(12, 0, 0, 8)
        ai_layout.setSpacing(8)
        ai_widget.setLayout(ai_layout)
        
        # Кнопка с иконкой робота (минималистичная)
        ai_button = QPushButton()
        ai_button.setObjectName("aiButton")
        ai_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_button.setFixedSize(40, 40)
        
        # Создаем минималистичную иконку робота через QPainter
        robot_pixmap = QPixmap(24, 24)
        robot_pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(robot_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        robot_color = QColor(167, 139, 250)
        painter.setBrush(QColor(robot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 6, 16, 14, 2, 2)
        painter.drawRoundedRect(6, 2, 12, 4, 1, 1)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(8, 9, 3, 3)
        painter.drawEllipse(13, 9, 3, 3)
        painter.drawRoundedRect(9, 15, 6, 2, 1, 1)
        painter.end()
        
        robot_icon = QLabel(ai_button)
        robot_icon.setPixmap(robot_pixmap)
        robot_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        robot_icon.setGeometry(8, 8, 24, 24)
        
        ai_button.setStyleSheet("""
            QPushButton#aiButton {
                background: #EFEAF7;
                border: none;
                border-radius: 20px;
            }
            QPushButton#aiButton:hover {
                background: #E6DFF2;
            }
            QPushButton#aiButton:pressed {
                background: #DDD6ED;
            }
        """)
        ai_button.clicked.connect(self.generate_ai_text)
        ai_layout.addWidget(ai_button)
        
        tr = get_tr()
        ai_text_label = QLabel(self.tr("ai_generates_text") if hasattr(self, 'tr') else tr("ai_generates_text"))
        ai_text_label.setFont(QFont("Inter", 9))
        ai_text_label.setStyleSheet("color: #B4B2C4; background: transparent;")
        ai_text_label.setWordWrap(False)
        ai_layout.addWidget(ai_text_label)
        ai_layout.addStretch()
        
        # Обновляем позиции при изменении размера (оптимизировано)
        def on_container_resize(event):
            QFrame.resizeEvent(editor_container, event)
            update_positions()
        editor_container.resizeEvent = on_container_resize
        
        right_layout.addWidget(editor_container)
        
        # Секция вложений убрана - файлы теперь только слева
        
        # Нижняя панель с кнопками (ближе к рамке ввода текста)
        bottom_buttons = self.create_bottom_buttons()
        right_layout.addLayout(bottom_buttons)
        
        # Добавляем рамку в основной layout
        right_main_layout.addWidget(right_frame)
        
        # Устанавливаем родителя для виджета истории на right_frame
        if hasattr(self, 'email_history_widget'):
            self.email_history_widget.setParent(right_frame)
        
        return right_widget
    
    def create_attachments_section(self):
        """Создает секцию прикрепленных файлов (показывается только когда есть файлы)"""
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(12)
        section.setLayout(section_layout)
        
        # Контейнер для файлов в один ряд (горизонтально) с рамкой как на фото
        files_container = QFrame()
        files_container.setObjectName("filesContainer")
        files_container.setStyleSheet("""
            QFrame#filesContainer {
                background: #FAFAFE;
                border: none;
                border-radius: 16px;
                padding: 12px;
                min-height: 80px;
            }
        """)
        
        # Заголовок с иконкой скрепки
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(8)
        
        attach_icon = QLabel("🔗")
        attach_icon.setFont(QFont("Segoe UI", 14))
        attach_icon.setStyleSheet("color: #A78BFA; background: transparent;")
        header_layout.addWidget(attach_icon)
        
        attach_title = QLabel(f"{self.tr('attach_files')} (0)")
        attach_title.setFont(QFont("Inter", 13, QFont.Weight.Medium))
        attach_title.setStyleSheet("color: #2E2E38; background: transparent;")
        self.attach_title_label = attach_title
        header_layout.addWidget(attach_title)
        header_layout.addStretch()
        
        # Кнопка добавления файлов
        self.attach_btn = QPushButton("+")
        self.attach_btn.setFixedSize(32, 32)
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background: rgba(139, 124, 246, 0.15);
                color: #8B7CF6;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(139, 124, 246, 0.25);
                border-color: rgba(139, 124, 246, 0.5);
            }
        """)
        self.attach_btn.clicked.connect(self.attach_files)
        header_layout.addWidget(self.attach_btn)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(8)
        files_container.setLayout(files_layout)
        files_layout.addWidget(header_widget)
        
        # Горизонтальный layout для файлов
        files_horizontal_layout = QHBoxLayout()
        files_horizontal_layout.setContentsMargins(0, 0, 0, 0)
        files_horizontal_layout.setSpacing(8)
        
        self.files_horizontal_layout = files_horizontal_layout
        self.files_container = files_container
        
        files_widget = QWidget()
        files_widget.setLayout(files_horizontal_layout)
        files_layout.addWidget(files_widget)
        
        section_layout.addWidget(files_container)
        files_container.show()  # Показываем всегда, чтобы пользователь мог загружать файлы
        
        return section
    
    def create_bottom_buttons(self):
        """Создает нижнюю панель с кнопками (ближе к рамке ввода текста)"""
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        bottom.setContentsMargins(0, 8, 0, 0)
        
        # Время последней отправки слева
        self.last_sent_label = QLabel("")
        self.last_sent_label.setFont(QFont("Inter", 9))
        self.last_sent_label.setStyleSheet("color: #B4B2C4; background: transparent; opacity: 0.7;")
        bottom.addWidget(self.last_sent_label)
        
        bottom.addStretch()
        
        # Кнопка отправки (шире и светлее) - лиловый градиент
        self.send_btn = QPushButton(self.tr('send_email'))
        self.send_btn.setFixedHeight(40)
        self.send_btn.setFixedWidth(180)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B4A9F8, stop:1 #C2B6FA);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #C2B6FA, stop:1 #D0C4FC);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A78BFA, stop:1 #B4A9F8);
                color: #FFFFFF;
            }
        """)
        self.send_btn.clicked.connect(self.send_email)
        bottom.addWidget(self.send_btn)
        
        # Загружаем время последней отправки при создании
        QTimer.singleShot(100, self.update_last_sent_time)
        
        return bottom
    
    def create_file_widget(self, file_info):
        """Создает виджет карточки файла с форматом"""
        file_name = file_info['name'] if isinstance(file_info, dict) else os.path.basename(file_info)
        file_path = file_info.get('path', '') if isinstance(file_info, dict) else file_info
        file_size = file_info.get('size', '') if isinstance(file_info, dict) else ''
        
        # Получаем расширение файла
        file_ext = os.path.splitext(file_name)[1].lower().lstrip('.')
        if not file_ext and file_path:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        # Добавляем формат в конец названия если его там нет
        base_name = os.path.splitext(file_name)[0]
        if not file_name.upper().endswith(file_ext.upper()) and file_ext:
            display_name = f"{base_name}.{file_ext.upper()}"
        else:
            display_name = file_name
        
        # Определяем иконку по формату (используем кэш)
        icon_char, icon_color = self._FILE_ICON_MAP.get(file_ext, ('🔗', '#9A90B8'))
        
        file_widget = QFrame()
        file_widget.setObjectName("fileCard")
        file_widget.setStyleSheet("""
            QFrame#fileCard {
                background: #FFFFFF;
                border: none;
                border-radius: 14px;
                padding: 10px;
                min-width: 200px;
            }
            QFrame#fileCard:hover {
                border-color: #9A8CF0;
                background: #FAFAFE;
            }
        """)
        file_widget.setFixedHeight(60)
        file_widget.setMinimumWidth(180)
        file_widget.setMaximumWidth(220)
        
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(10)
        file_widget.setLayout(file_layout)
        
        # Иконка файла по формату (монохромная фиолетовая, того же цвета что и Данные получателя)
        file_icon = QLabel(icon_char)
        file_icon.setFont(QFont("Segoe UI", 28))
        file_icon.setStyleSheet("color: #C8B4FF; background: transparent;")  # Того же цвета что и иконка пользователя
        file_icon.setFixedSize(42, 42)
        file_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_layout.addWidget(file_icon)
        
        # Имя файла (с форматом) и размер
        file_info_widget = QWidget()
        file_info_layout = QVBoxLayout()
        file_info_layout.setContentsMargins(0, 0, 0, 0)
        file_info_layout.setSpacing(3)
        file_info_widget.setLayout(file_info_layout)
        
        name_label = QLabel(display_name)
        name_label.setFont(QFont("Inter", 11))
        name_label.setStyleSheet("color: #2E2E38; background: transparent;")
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(100)
        file_info_layout.addWidget(name_label)
        
        if file_size:
            # Преобразуем размер в строку если это число
            if isinstance(file_size, (int, float)):
                size_mb = file_size / (1024 * 1024)
                size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{file_size / 1024:.1f} KB"
            else:
                size_text = str(file_size)
            size_label = QLabel(size_text)
            size_label.setFont(QFont("Inter", 10))
            size_label.setStyleSheet("color: #9B9AA8; background: transparent;")
            file_info_layout.addWidget(size_label)
        
        file_layout.addWidget(file_info_widget)
        file_layout.addStretch()
        
        # Кнопка удаления (X) - с эмодзи и прозрачным фоном
        remove_btn = QPushButton("❌")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6E6D7A;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(110, 109, 122, 0.1);
                border-radius: 10px;
                color: #6E6D7A;
            }
        """)
        remove_btn.clicked.connect(lambda checked=False, fi=file_info: self.remove_file(fi))
        file_layout.addWidget(remove_btn)
        
        return file_widget
    
    def _clear_layout(self, layout):
        """Вспомогательный метод для очистки layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def update_files_list(self):
        """Обновляет список прикреплённых файлов в горизонтальном ряду (справа) и вертикальном (слева)"""
        file_count = len(self.attached_files)
        
        # Обновляем заголовки
        files_text = f"{self.tr('files')} ({file_count})"
        if hasattr(self, 'attach_title_label'):
            self.attach_title_label.setText(files_text)
        if hasattr(self, 'files_title_label'):
            self.files_title_label.setText(files_text)
        
        # Кнопка "+" всегда видна
        if hasattr(self, 'header_add_file_btn'):
            self.header_add_file_btn.show()
        
        # Обновляем правый список (горизонтальный)
        if hasattr(self, 'files_horizontal_layout') and self.files_horizontal_layout:
            self._clear_layout(self.files_horizontal_layout)
            if file_count > 0:
                for file_info in self.attached_files:
                    self.files_horizontal_layout.addWidget(self.create_file_widget(file_info))
        
        # Обновляем контейнер файлов
        if hasattr(self, 'files_container'):
            self.files_container.setVisible(file_count > 0)
        
        # Обновляем левый список (вертикальный)
        if hasattr(self, 'left_files_list'):
            self._clear_layout(self.left_files_list)
            for index, file_info in enumerate(self.attached_files):
                self.left_files_list.addWidget(self.create_left_file_widget(file_info, index))
            
            # Динамически изменяем размер виджета файлов
            if hasattr(self, 'files_scroll_area'):
                if file_count == 0:
                    self.files_scroll_area.setMaximumHeight(0)
                    self.files_scroll_area.hide()
                else:
                    self.files_scroll_area.show()
                    # Высота увеличивается до 4 файлов, потом фиксированная
                    if file_count <= 4:
                        calculated_height = file_count * 70  # ~70px на файл
                    else:
                        calculated_height = 280  # Максимум для 4 файлов, потом скролл
                    self.files_scroll_area.setMaximumHeight(calculated_height)
                    self.files_scroll_area.setMinimumHeight(min(calculated_height, 60))
                
                # Облачный плейсхолдер показываем только когда нет файлов
                if hasattr(self, 'add_file_btn'):
                    self.add_file_btn.setVisible(file_count == 0)
                    self.add_file_btn.setMinimumHeight(40)
                    self.add_file_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    def remove_file(self, file_info):
        """Удаляет файл из списка и из файловой системы"""
        file_path = file_info['path'] if isinstance(file_info, dict) else file_info
        self.attached_files = [f for f in self.attached_files if 
                             (f['path'] if isinstance(f, dict) else f) != file_path]
        
        # Удаляем файл из файловой системы при явном удалении
        username = self._get_funcs()['get_current_username']()
        if username and 'delete_attached_file' in self._get_funcs():
            self._get_funcs()['delete_attached_file'](username, file_path)
        
        self.update_files_list()
        # Автосохранение при удалении файлов
        self.on_field_changed()
    
    def show_file_context_menu(self, file_widget, file_info, position):
        """Показывает контекстное меню для файла (ПКМ)"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #E2DDF0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                color: #2E2E38;
            }
            QMenu::item:selected {
                background: #EFEAF7;
                color: #8B7CF6;
            }
        """)
        
        # Получаем индекс файла
        file_index = -1
        if hasattr(file_widget, 'file_index'):
            file_index = file_widget.file_index
        else:
            try:
                file_path = file_info['path'] if isinstance(file_info, dict) else file_info
                for i, f in enumerate(self.attached_files):
                    f_path = f['path'] if isinstance(f, dict) else f
                    if f_path == file_path:
                        file_index = i
                        break
            except:
                pass
        
        # Переместить вверх
        if file_index > 0:
            tr_func = get_tr()
            move_up_action = menu.addAction("↑ " + tr_func("up"))
            move_up_action.triggered.connect(lambda: self.move_file(file_index, file_index - 1))
        
        # Переместить вниз
        if file_index >= 0 and file_index < len(self.attached_files) - 1:
            tr_func = get_tr()
            move_down_action = menu.addAction("↓ " + tr_func("down"))
            move_down_action.triggered.connect(lambda: self.move_file(file_index, file_index + 1))
        
        if file_index > 0 or (file_index >= 0 and file_index < len(self.attached_files) - 1):
            menu.addSeparator()
        
        # Удалить
        delete_action = menu.addAction("🗑️ " + (self.tr("delete") if hasattr(self, 'tr') else "Удалить"))
        delete_action.triggered.connect(lambda: self.remove_file(file_info))
        
        # Показываем меню
        global_pos = file_widget.mapToGlobal(position)
        menu.exec(global_pos)
    
    def move_file(self, from_index, to_index):
        """Перемещает файл с одного индекса на другой"""
        if 0 <= from_index < len(self.attached_files) and 0 <= to_index < len(self.attached_files):
            file_item = self.attached_files.pop(from_index)
            self.attached_files.insert(to_index, file_item)
            self.update_files_list()
            self.on_field_changed()
    
    def remove_file_from_list(self, item):
        """Удаляет файл при двойном клике (старый метод для совместимости)"""
        # Метод больше не используется, так как мы используем сетку вместо списка
        pass
    
    def update_char_count(self):
        """Обновляет счётчик символов"""
        count = len(self.body_text.toPlainText())
        if hasattr(self, 'char_count_number'):
            self.char_count_number.setText(str(count))
        if hasattr(self, 'char_count_text'):
            self.char_count_text.setText(self.tr("characters"))
    
    def attach_files(self):
        """Прикрепляет файлы и автоматически сохраняет их в папку пользователя через save_attached_files"""
        # Разрешенные форматы файлов
        ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx'}
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("attach_files"),
            "",
            "Supported Files (*.pdf *.png *.jpg *.jpeg *.doc *.docx);;All Files (*.*)"
        )
        
        username = self._get_funcs()['get_current_username']()
        if not username:
            return
        
        # Фильтруем файлы по формату
        valid_files = []
        for file_path in files:
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in ALLOWED_EXTENSIONS:
                notification = NotificationWidget(self, self.tr("file_format_not_allowed", filename=os.path.basename(file_path)), is_success=False)
                notification.show_notification()
                continue
            
            if file_path not in [f['path'] if isinstance(f, dict) else f for f in self.attached_files]:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                size_mb = file_size / (1024 * 1024)
                size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{file_size / 1024:.1f} KB"
                
                # Добавляем файл в список (save_attached_files скопирует его в нужную папку)
                self.attached_files.append({
                    'path': file_path,
                    'name': file_name,
                    'size': file_size  # Сохраняем размер как число для save_attached_files
                })
                valid_files.append(file_path)
        
        if valid_files:
            self.update_files_list()
            # Автосохранение при добавлении файлов (сохраняет в БД и копирует в папку)
            self.on_field_changed()
    
    
    def check_email_history(self):
        """Проверяет историю отправки писем на введенный email (с принудительным обновлением кеша)"""
        if not hasattr(self, 'email_history_icon'):
            return
        
        email = self.recipient_email_input.text().strip().lower()
        
        # Если email пустой, скрываем иконку
        if not email:
            if hasattr(self, 'email_history_icon'):
                self.email_history_icon.hide()
            return
        
        # Получаем историю писем с принудительным обновлением кеша
        try:
            get_history_func = self._get_funcs()['get_email_history']
            # Вызываем с force_refresh=True для обновления кеша после удаления
            try:
                history = get_history_func(force_refresh=True)
            except TypeError:
                # Если функция не поддерживает force_refresh, вызываем обычным способом
                history = get_history_func()
            if not history:
                if hasattr(self, 'email_history_icon'):
                    self.email_history_icon.hide()
                return
            
            # Ищем письма на этот email (сравниваем в нижнем регистре)
            matching_emails = []
            for entry in history:
                # entry format: (id, sent_at, recipient_email, lehrstelle)
                if len(entry) >= 3:
                    recipient_email = entry[2]
                    if recipient_email and recipient_email.lower() == email:
                        matching_emails.append(entry)
            
            # Если нашли совпадения, показываем информацию
            if matching_emails:
                # Берем последнее отправленное письмо
                last_entry = matching_emails[0]  # История уже отсортирована по дате DESC
                sent_at = last_entry[1] if len(last_entry) > 1 else None
                lehrstelle = last_entry[3] if len(last_entry) > 3 else None
                
                # Форматируем дату
                if sent_at:
                    try:
                        if isinstance(sent_at, str):
                            # Парсим строку даты
                            from datetime import datetime
                            date_obj = datetime.strptime(sent_at, "%Y-%m-%d %H:%M:%S")
                            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
                        else:
                            formatted_date = str(sent_at)
                    except:
                        formatted_date = str(sent_at)
                else:
                    formatted_date = self.tr("unknown_date")
                
                # Формируем текст для диалога
                position_text = f" ({lehrstelle})" if lehrstelle else ""
                history_text = f"Письмо уже отправлялось на этот email {formatted_date}{position_text}"
                
                # Сохраняем текст истории и показываем иконку "!"
                if hasattr(self, 'email_history_icon'):
                    self.email_history_text = history_text
                    self.email_history_icon.show()
                    # Скрываем галочку когда показывается иконка истории
                    if hasattr(self, 'email_check_icon'):
                        self.email_check_icon.hide()
                    # Скрываем виджет если он был открыт
                    if hasattr(self, 'email_history_widget'):
                        self.email_history_widget.hide()
            else:
                # Нет совпадений - скрываем иконку
                if hasattr(self, 'email_history_icon'):
                    self.email_history_icon.hide()
                # Показываем галочку если email валидный
                self.validate_email()
        except Exception as e:
            # В случае ошибки просто скрываем иконку
            if hasattr(self, 'email_history_icon'):
                self.email_history_icon.hide()
            # Показываем галочку если email валидный
            self.validate_email()
    
    def validate_email(self):
        """Проверяет валидность email и показывает галочку"""
        if not hasattr(self, 'recipient_email_input') or not hasattr(self, 'email_check_icon'):
            return
        
        email = self.recipient_email_input.text().strip()
        
        # Простая проверка email (базовая валидация)
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(email_pattern, email))
        
        # Показываем галочку только если email валидный и нет иконки истории
        if is_valid and email:
            if hasattr(self, 'email_history_icon') and not self.email_history_icon.isVisible():
                self.email_check_icon.show()
            elif not hasattr(self, 'email_history_icon'):
                self.email_check_icon.show()
        else:
            self.email_check_icon.hide()
    
    def toggle_email_history_widget(self):
        """Показывает/скрывает встроенный виджет с информацией об истории отправки"""
        if not hasattr(self, 'email_history_text') or not self.email_history_text:
            return
        
        if self.email_history_widget.isVisible():
            self.email_history_widget.hide()
        else:
            self.email_history_message.setText(self.email_history_text)
            # Позиционируем виджет левее и выше иконки "!" внутри рамки
            def update_position():
                if self.email_history_icon.parent() and self.email_history_widget.parent():
                    # Получаем глобальные координаты иконки и right_frame
                    icon_global_pos = self.email_history_icon.mapToGlobal(QPoint(0, 0))
                    frame_global_pos = self.email_history_widget.parent().mapToGlobal(QPoint(0, 0))
                    
                    # Вычисляем локальные координаты иконки относительно right_frame
                    icon_x = icon_global_pos.x() - frame_global_pos.x()
                    icon_y = icon_global_pos.y() - frame_global_pos.y()
                    icon_width = self.email_history_icon.width()
                    
                    # Позиционируем левее и выше иконки (в локальных координатах относительно right_frame)
                    widget_width = 360  # Увеличена ширина, чтобы текст не заходил за рамки
                    widget_height = 50
                    x_pos = icon_x - widget_width - 10  # Левее на 10px
                    y_pos = icon_y - 5  # Выше на 5px
                    
                    # Убеждаемся, что виджет не выходит за границы рамки
                    if x_pos < 20:  # Учитываем padding рамки (20px)
                        x_pos = icon_x + icon_width + 10  # Если не помещается слева, показываем справа
                    
                    # Устанавливаем позицию в локальных координатах (относительно right_frame)
                    self.email_history_widget.setGeometry(x_pos, y_pos, widget_width, widget_height)
                    self.email_history_widget.raise_()  # Поверх всех виджетов в рамке
                    self.email_history_widget.show()
            
            QTimer.singleShot(10, update_position)
    
    def on_field_changed(self):
        """Обработчик изменения полей - запускает таймер для автосохранения (debounce)"""
        # Перезапускаем таймер - сохраним только после паузы в 1 секунду
        if hasattr(self, 'field_save_timer'):
            self.field_save_timer.stop()
            self.field_save_timer.start()
    
    def _save_fields_data(self):
        """Сохраняет данные полей и текста письма (вызывается через debounce)"""
        try:
            funcs = self._get_funcs()
            username = funcs.get('get_current_username')()
            if not username:
                return
            
            # Получаем значения полей
            recipient_email = ""
            lehrstelle = ""
            firma = ""
            body_text = ""
            
            if hasattr(self, 'recipient_email_input'):
                recipient_email = self.recipient_email_input.text().strip()
            if hasattr(self, 'lehrstelle_input'):
                lehrstelle = self.lehrstelle_input.text().strip()
            if hasattr(self, 'firma_input'):
                firma = self.firma_input.text().strip()
            if hasattr(self, 'body_text'):
                body_text = self.body_text.toPlainText().strip()
            
            # ВАЖНО: Сохраняем данные автозаполнения только если хотя бы одно поле не пустое
            # Если все поля пустые, save_autofill_data удалит запись из БД
            # Автосохранение работает только ПОСЛЕ того, как пользователь что-то написал
            if 'save_autofill_data' in funcs:
                funcs['save_autofill_data'](username, recipient_email, lehrstelle, firma, body_text)
        except Exception as e:
            # Тихая ошибка - не показываем пользователю при автосохранении
            print(f"Ошибка автосохранения данных: {e}")
    
    def _on_subject_changed(self):
        """Обработчик изменения темы - отслеживает ручное редактирование"""
        self.on_field_changed()
    
    def update_email_subject(self):
        """Обновляет тему письма на основе lehrstelle (только если не редактировалась вручную)"""
        if hasattr(self, 'email_subject_input') and hasattr(self, 'lehrstelle_input'):
            # Не обновляем, если пользователь редактировал тему вручную
            if hasattr(self, '_subject_manually_edited') and self._subject_manually_edited:
                return
            lehrstelle = self.lehrstelle_input.text().strip()
            if lehrstelle:
                # Обновляем тему при изменении lehrstelle только если она не редактировалась
                prefix = "Bewerbung um eine Lehrstelle als"
                current_text = self.email_subject_input.text().strip()
                # Обновляем только если тема пустая или содержит только префикс
                if not current_text or current_text.startswith(prefix):
                    self.email_subject_input.setText(f"{prefix} {lehrstelle}")
    
    def load_draft_data(self):
        """Загружает данные автозаполнения и прикрепленные файлы при открытии страницы"""
        username = self._get_funcs()['get_current_username']()
        if not username:
            # Если нет username, очищаем все поля
            if hasattr(self, 'recipient_email_input'):
                self.recipient_email_input.setText('')
            if hasattr(self, 'lehrstelle_input'):
                self.lehrstelle_input.setText('')
            if hasattr(self, 'firma_input'):
                self.firma_input.setText('')
            if hasattr(self, 'body_text'):
                self.body_text.setPlainText('')
            if hasattr(self, 'attached_files'):
                self.attached_files = []
                if hasattr(self, 'update_files_list'):
                    self.update_files_list()
            return
        
        # Сохраняем текущий username для проверки при следующих загрузках
        if not hasattr(self, '_last_loaded_username'):
            self._last_loaded_username = None
        
        # ВАЖНО: Если username изменился, очищаем все данные перед загрузкой новых
        if self._last_loaded_username and self._last_loaded_username != username:
            # Пользователь изменился - очищаем все поля
            if hasattr(self, 'recipient_email_input'):
                self.recipient_email_input.setText('')
            if hasattr(self, 'lehrstelle_input'):
                self.lehrstelle_input.setText('')
            if hasattr(self, 'firma_input'):
                self.firma_input.setText('')
            if hasattr(self, 'body_text'):
                self.body_text.setPlainText('')
            if hasattr(self, 'attached_files'):
                self.attached_files = []
                if hasattr(self, 'update_files_list'):
                    self.update_files_list()
        
        self._last_loaded_username = username
        
        # Устанавливаем тему письма по умолчанию при загрузке
        if hasattr(self, 'email_subject_input'):
            default_subject = "Bewerbung um eine Lehrstelle als"
            if not self.email_subject_input.text().strip():
                self.email_subject_input.setText(default_subject)
        
        # ВАЖНО: НЕ загружаем данные автозаполнения автоматически - поля должны быть пустые по умолчанию
        # Данные будут загружены только после успешной отправки письма или при явном сохранении
        # Автосохранение работает только ПОСЛЕ того, как пользователь что-то написал
        
        # Загружаем прикрепленные файлы (только если они есть)
        if 'load_attached_files' in self._get_funcs():
            try:
                loaded_files = self._get_funcs()['load_attached_files'](username)
                if loaded_files:
                    self.attached_files = []
                    base_dir = r"D:\it\bewerbung\saved_attachments"
                    user_files_dir = os.path.join(base_dir, username)
                    user_files_dir_normalized = os.path.normpath(user_files_dir)
                    
                    for file_info in loaded_files:
                        if isinstance(file_info, dict):
                            file_path = file_info.get('path', '')
                            file_name = file_info.get('name', '')
                            file_size = file_info.get('size', '')
                            
                            # ВАЖНО: Проверяем, что файл находится в папке текущего пользователя
                            if file_path:
                                file_path_normalized = os.path.normpath(file_path)
                                # Пропускаем файлы, которые не находятся в папке текущего пользователя
                                if not file_path_normalized.startswith(user_files_dir_normalized):
                                    continue
                            
                            # Проверяем, существует ли файл
                            if file_path and os.path.exists(file_path):
                                # Если размер не указан, вычисляем его
                                if not file_size or isinstance(file_size, str):
                                    try:
                                        size_bytes = os.path.getsize(file_path)
                                        size_mb = size_bytes / (1024 * 1024)
                                        file_size = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_bytes / 1024:.1f} KB"
                                    except:
                                        file_size = "0 KB"
                                
                                self.attached_files.append({
                                    'path': file_path,
                                    'name': file_name or os.path.basename(file_path),
                                    'size': file_size
                                })
                    # Обновляем список файлов в интерфейсе
                    if hasattr(self, 'update_files_list'):
                        self.update_files_list()
                else:
                    # Если файлов нет, очищаем список
                    self.attached_files = []
                    if hasattr(self, 'update_files_list'):
                        self.update_files_list()
            except Exception as e:
                print(f"[DEBUG] Ошибка при загрузке файлов: {e}")
                # При ошибке очищаем список
                self.attached_files = []
                if hasattr(self, 'update_files_list'):
                    self.update_files_list()
    
    def _mark_field_error(self, field):
        """Помечает поле ошибкой (красная обводка)"""
        if not field:
            return
        # Сохраняем оригинальный стиль
        if not hasattr(field, '_original_style'):
            field._original_style = field.styleSheet()
        
        # Создаем стиль ошибки - только светлая красная обводка, размер не меняется
        # Используем border: 2px solid transparent в оригинале, чтобы размер не менялся
        error_style = """
            QLineEdit {
                background-color: #FFFFFF;
                border: 2px solid #FFB3B3;
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 16px;
                color: #2E2E38;
            }
            QLineEdit:focus {
                border: 2px solid #FFB3B3;
                background-color: #FFFFFF;
            }
        """
        field.setStyleSheet(error_style)
        field._has_error = True
    
    def _clear_field_error(self, field):
        """Убирает ошибку с поля (возвращает оригинальный стиль)"""
        if not field or not hasattr(field, '_original_style'):
            return
        field.setStyleSheet(field._original_style)
        field._has_error = False
    
    def generate_ai_text(self):
        """Генерирует текст письма с помощью AI"""
        lehrstelle = self.lehrstelle_input.text().strip()
        firma = self.firma_input.text().strip()
        recipient_email = self.recipient_email_input.text().strip() if hasattr(self, 'recipient_email_input') else ""
        user_text = self.body_text.toPlainText().strip()
        
        # Валидация полей "Данные получателя" (без recipient_email)
        missing_fields = []
        if not lehrstelle:
            missing_fields.append(self.lehrstelle_input)
        if not firma:
            missing_fields.append(self.firma_input)
        
        if missing_fields:
            # Подсвечиваем незаполненные поля красной обводкой
            for field in missing_fields:
                self._mark_field_error(field)
            return
        
        # Получаем дополнительные данные пользователя
        additional_prompt = ""
        if hasattr(self, 'ai_prompt_text') and self.ai_prompt_text:
            additional_prompt = self.ai_prompt_text.toPlainText().strip()
        
        # Получаем данные пользователя (необязательно - если нет, используем значения по умолчанию)
        user_info = self._get_funcs()['get_user_info']()
        if not user_info:
            # Используем значения по умолчанию вместо ошибки
            user_info = ['', '', '', None, None, '', '', '']
        
        first_name = user_info[0] if len(user_info) > 0 else ''
        last_name = user_info[1] if len(user_info) > 1 else ''
        phone_number = user_info[2] if len(user_info) > 2 else ''
        current_status = user_info[6] if len(user_info) > 6 else ''
        about_me = user_info[7] if len(user_info) > 7 else (user_info[8] if len(user_info) > 8 else '')
        
        # Получаем уровень немецкого языка
        username = self._get_funcs()['get_current_username']()
        german_level = "B1 - Средний"  # По умолчанию
        if username:
            try:
                from email_app import DB_FILE
                import sqlite3
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT german_level FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result and result[0]:
                    german_level = result[0]
                conn.close()
            except:
                pass
        
        # Импортируем GroqAIThread
        from email_app import GroqAIThread
        
        # Создаем поток для генерации с дополнительным промптом и уровнем языка
        self.ai_thread = GroqAIThread(lehrstelle, firma, user_text, first_name, last_name, phone_number, current_status, about_me, additional_prompt, german_level)
        self.ai_thread.finished.connect(self.on_ai_generated)
        self.ai_thread.start()
        
        # Показываем встроенный виджет загрузки
        if not hasattr(self, 'ai_loading_widget') or self.ai_loading_widget is None:
            self.ai_loading_widget = AILoadingWidget(self)
        self.ai_loading_widget.show_loading()
    
    def on_ai_generated(self, success, text, pdf_path=''):
        """Обработчик завершения генерации AI"""
        # Скрываем виджет загрузки
        if hasattr(self, 'ai_loading_widget') and self.ai_loading_widget:
            self.ai_loading_widget.hide_loading()
            self.ai_loading_widget = None
        
        if success:
            # Очищаем текст от markdown форматирования и лишних отступов
            import re
            # Убираем **жирный** текст - заменяем на обычный
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            # Заменяем множественные переносы строк (\n\n\n) на одинарные \n
            text = re.sub(r'\n{3,}', '\n', text)
            # Убираем лишние пробелы в начале строк
            lines = text.split('\n')
            cleaned_lines = [line.lstrip() for line in lines]
            text = '\n'.join(cleaned_lines)
            # Просто устанавливаем текст
            self.body_text.setPlainText(text)
            # Прокручиваем к началу документа чтобы показать весь текст с задержкой для корректного отображения
            def scroll_to_start():
                cursor = self.body_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                self.body_text.setTextCursor(cursor)
                self.body_text.ensureCursorVisible()
            QTimer.singleShot(100, scroll_to_start)
            # Сохраняем путь к PDF файлу
            if pdf_path:
                self.ai_generated_pdf_path = pdf_path
            # Убрали notification - просто вставляем текст
        else:
            notification = NotificationWidget(self, text, is_success=False)
            notification.show_notification()
    
    def check_google_account(self):
        """Проверяет подключен ли Google аккаунт"""
        username = self._get_funcs()['get_current_username']()
        if not username:
            return False
        
        email = self._get_funcs()['get_google_account_email'](username)
        return email is not None
    
    def send_email(self):
        """Отправляет письмо"""
        recipient_email = self.recipient_email_input.text().strip()
        lehrstelle = self.lehrstelle_input.text().strip()
        firma = self.firma_input.text().strip()
        body_text = self.body_text.toPlainText().strip()
        
        if not recipient_email or not lehrstelle or not firma:
            # Просто возвращаем, не показываем notification
            return
        
        # Убрана проверка Google аккаунта - письмо можно отправлять без него
        # if not self.check_google_account():
        #     QMessageBox.warning(self, self.tr("error"), self.tr("google_account_required"))
        #     return
        
        self.do_send_email(body_text)
    
    def do_send_email(self, body_text):
        """Выполняет отправку письма"""
        recipient_email = self.recipient_email_input.text().strip()
        lehrstelle = self.lehrstelle_input.text().strip()
        firma = self.firma_input.text().strip()
        
        # Получаем Google credentials
        username = self._get_funcs()['get_current_username']()
        if not username:
            notification = NotificationWidget(self, self.tr("wrong_credentials"), is_success=False)
            notification.show_notification()
            return
        
        # Получаем данные пользователя для темы письма
        user_info = self._get_funcs()['get_user_info'](username)
        first_name = user_info[0] if user_info and len(user_info) > 0 else ''
        last_name = user_info[1] if user_info and len(user_info) > 1 else ''
        # Используем тему из поля, если она заполнена, иначе генерируем автоматически
        if hasattr(self, 'email_subject_input') and self.email_subject_input.text().strip():
            subject = self.email_subject_input.text().strip()
        else:
            # Всегда используем немецкий формат
            subject = f"Bewerbung um eine Lehrstelle als {lehrstelle}"
        
        # Если есть AI-сгенерированный PDF, создаем короткий текст для email
        email_body_text = body_text
        if hasattr(self, 'ai_generated_pdf_path') and self.ai_generated_pdf_path and os.path.exists(self.ai_generated_pdf_path):
            # Короткий текст для email
            email_body_text = f"""Sehr geehrte Damen und Herren

Anbei sende ich Ihnen meine Bewerbungsunterlagen für eine Lehrstelle als {lehrstelle}
Ich freue mich über die Möglichkeit, mich persönlich vorzustellen.

Freundliche Grüsse
{first_name} {last_name}"""
            # Добавляем PDF к вложениям
            attachments = [f['path'] if isinstance(f, dict) else f for f in self.attached_files]
            if self.ai_generated_pdf_path not in attachments:
                attachments.append(self.ai_generated_pdf_path)
        else:
            # Обычная отправка без PDF
            attachments = [f['path'] if isinstance(f, dict) else f for f in self.attached_files]
        
        # Пытаемся получить credentials для Gmail API
        try:
            if not self._get_funcs().get('GOOGLE_OAUTH_AVAILABLE', False):
                notification = NotificationWidget(self, "Gmail API не доступен. Установите необходимые библиотеки.", is_success=False)
                notification.show_notification()
                return
            
            token_json = self._get_funcs()['get_google_account_token'](username)
            if not token_json:
                notification = NotificationWidget(self, self.tr("google_account_not_connected"), is_success=False)
                notification.show_notification()
                return
            
            # Создаем credentials из token
            import json
            from google.oauth2.credentials import Credentials
            
            token_data = json.loads(token_json)
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/gmail.send'])
            )
            
            # Импортируем EmailThread
            from email_app import EmailThread
            
            # Создаем поток для отправки
            self.email_thread = EmailThread(
                smtp_server='',
                smtp_port=0,
                use_tls=False,
                sender_email='',
                sender_password='',
                recipient_email=recipient_email,
                subject=subject,
                body=email_body_text,
                attachments=attachments,
                use_gmail_api=True,
                credentials=credentials
            )
            self.email_thread.finished.connect(self.on_email_sent)
            self.email_thread.start()
            
            # Запускаем анимацию точек в кнопке
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(False)
                # Создаем таймер для анимации точек, если его еще нет
                if not hasattr(self, 'send_dots_timer'):
                    self.send_dots_timer = QTimer()
                    self.send_dots_timer.timeout.connect(self.animate_send_dots)
                    self.send_dots_count = 0
                self.send_dots_count = 0
                self.send_dots_timer.start(300)  # Обновление каждые 300ms
                self.animate_send_dots()  # Первый вызов сразу
            
        except Exception as e:
            # При ошибке останавливаем анимацию и возвращаем текст кнопки
            if hasattr(self, 'send_btn'):
                if hasattr(self, 'send_dots_timer'):
                    self.send_dots_timer.stop()
                self.send_btn.setText(self.tr('send_email'))
                self.send_btn.setEnabled(True)
    
    def animate_send_dots(self):
        """Анимирует точки в кнопке отправки"""
        if not hasattr(self, 'send_btn') or not hasattr(self, 'send_dots_count'):
            return
        
        dots = "." * ((self.send_dots_count % 3) + 1)  # 1, 2, 3 точки
        self.send_btn.setText(dots)
        self.send_dots_count = (self.send_dots_count + 1) % 3
    
    def update_last_sent_time(self):
        """Обновляет время последней отправки письма"""
        username = self._get_funcs()['get_current_username']()
        if not username:
            if hasattr(self, 'last_sent_label'):
                self.last_sent_label.setText("")
            return
        
        try:
            from email_app import DB_FILE
            import sqlite3
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sent_at FROM email_history 
                WHERE username = ? 
                ORDER BY sent_at DESC 
                LIMIT 1
            ''', (username,))
            result = cursor.fetchone()
            conn.close()
            
            if not hasattr(self, 'last_sent_label'):
                return
            
            if result and result[0]:
                try:
                    from datetime import datetime
                    if isinstance(result[0], str):
                        dt = datetime.strptime(result[0].split('.')[0], '%Y-%m-%d %H:%M:%S')
                    else:
                        dt = result[0]
                    
                    # Форматируем время: "12:34" для сегодня или "12.12.2024 12:34" для других дней
                    now = datetime.now()
                    if dt.date() == now.date():
                        time_str = dt.strftime('%H:%M')
                        self.last_sent_label.setText(f"{self.tr('last_sent')}: {time_str}")
                    else:
                        date_str = dt.strftime('%d.%m.%Y %H:%M')
                        self.last_sent_label.setText(f"{self.tr('last_sent')}: {date_str}")
                except Exception as e:
                    self.last_sent_label.setText("")
            else:
                    self.last_sent_label.setText("")
        except:
            if hasattr(self, 'last_sent_label'):
                self.last_sent_label.setText("")
    
    def animate_text_clear(self):
        """Очищает текст в редакторе письма после отправки"""
        if not hasattr(self, 'body_text'):
            return
        
        # Очищаем текст немедленно (исправление бага с неочищающимся текстом)
        self.body_text.setPlainText('')
        
        # Обновляем счетчик символов
        if hasattr(self, 'update_char_count'):
            self.update_char_count()
    
    def on_email_sent(self, success, message):
        """Обработчик завершения отправки письма"""
        if success:
            # Сохраняем в историю
            recipient_email = self.recipient_email_input.text().strip()
            lehrstelle = self.lehrstelle_input.text().strip()
            firma = self.firma_input.text().strip()
            self._get_funcs()['save_email_history'](recipient_email, lehrstelle)
            
            # Сохраняем данные формы ТОЛЬКО после успешной отправки
            username = self._get_funcs()['get_current_username']()
            if username and 'save_autofill_data' in self._get_funcs():
                self._get_funcs()['save_autofill_data'](username, recipient_email, lehrstelle, firma)
            
            # Обновляем время последней отправки
            self.update_last_sent_time()
            
            # Автосохранение файлов после отправки
            if username and self.attached_files:
                # Сохраняем прикрепленные файлы
                if 'save_attached_files' in self._get_funcs():
                    self._get_funcs()['save_attached_files'](username, self.attached_files)
            
            # Останавливаем анимацию точек и показываем галочку
            if hasattr(self, 'send_btn'):
                if hasattr(self, 'send_dots_timer'):
                    self.send_dots_timer.stop()
                self.send_btn.setText("✓")
                # Возвращаем текст кнопки через 2 секунды
                QTimer.singleShot(2000, lambda: self.send_btn.setText(self.tr('send_email')) if hasattr(self, 'send_btn') else None)
                self.send_btn.setEnabled(True)
            
            # Анимируем очистку текста в редакторе после показа галочки
            QTimer.singleShot(300, self.animate_text_clear)
        else:
            # При ошибке останавливаем анимацию и возвращаем текст кнопки
            if hasattr(self, 'send_btn'):
                if hasattr(self, 'send_dots_timer'):
                    self.send_dots_timer.stop()
                self.send_btn.setText(self.tr('send_email'))
                self.send_btn.setEnabled(True)
    
    def dragEnterEvent(self, event):
        """Обработчик события перетаскивания файлов"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Обработчик события отпускания файлов"""
        if event.mimeData().hasUrls():
            username = self._get_funcs()['get_current_username']()
            if not username:
                event.acceptProposedAction()
                return
            
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            user_files_dir = os.path.join("user_files", username)
            
            for file_path in files:
                if os.path.isfile(file_path):
                    if file_path not in [f['path'] if isinstance(f, dict) else f for f in self.attached_files]:
                        file_name = os.path.basename(file_path)
                        file_size = os.path.getsize(file_path)
                        size_mb = file_size / (1024 * 1024)
                        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{file_size / 1024:.1f} KB"
                        
                        # Копируем файл в папку пользователя
                        import shutil
                        import time
                        base_name, ext = os.path.splitext(file_name)
                        timestamp = int(time.time())
                        saved_file_name = f"{base_name}_{timestamp}{ext}"
                        saved_file_path = os.path.join(user_files_dir, saved_file_name)
                        
                        try:
                            os.makedirs(user_files_dir, exist_ok=True)
                            shutil.copy2(file_path, saved_file_path)
                            self.attached_files.append({
                                'path': saved_file_path,
                                'name': file_name,
                                'size': size_text
                            })
                        except Exception as e:
                            print(f"Ошибка при копировании файла {file_name}: {e}")
                            self.attached_files.append({
                                'path': file_path,
                                'name': file_name,
                                'size': size_text
                            })
            self.update_files_list()
            self.on_field_changed()  # Автосохранение
            event.acceptProposedAction()
    
    def toggle_text_format(self):
        """Переключает форматирование текста (жирный/курсив)"""
        cursor = self.body_text.textCursor()
        if cursor.hasSelection():
            # Получаем текущее форматирование
            fmt = cursor.charFormat()
            is_bold = fmt.fontWeight() == QFont.Weight.Bold
            
            # Переключаем жирный шрифт
            fmt.setFontWeight(QFont.Weight.Bold if not is_bold else QFont.Weight.Normal)
            cursor.setCharFormat(fmt)
            self.body_text.setTextCursor(cursor)
        else:
            # Если нет выделения, просто переключаем формат для следующего ввода
            fmt = self.body_text.currentCharFormat()
            is_bold = fmt.fontWeight() == QFont.Weight.Bold
            fmt.setFontWeight(QFont.Weight.Bold if not is_bold else QFont.Weight.Normal)
            self.body_text.setCurrentCharFormat(fmt)
            self.body_text.setFocus()
    
    def show_text_format_menu(self, position: QPoint):
        """Показывает контекстное меню форматирования при ПКМ на выделенном тексте"""
        # Проверяем, есть ли выделение текста
        cursor = self.body_text.textCursor()
        has_selection = cursor.hasSelection()
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid rgba(156, 137, 184, 0.3);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                color: #1F2937;
            }
            QMenu::item:selected {
                background: rgba(108, 77, 255, 0.15);
                color: #6C4DFF;
            }
        """)
        
        # Действия форматирования (только если есть выделение)
        if has_selection:
            bold_action = menu.addAction("B " + (self.tr("bold") if hasattr(self, 'tr') else "Жирный"))
            bold_action.triggered.connect(lambda: self.apply_format('bold'))
            
            italic_action = menu.addAction("I " + (self.tr("italic") if hasattr(self, 'tr') else "Курсив"))
            italic_action.triggered.connect(lambda: self.apply_format('italic'))
            
            underline_action = menu.addAction("U " + (self.tr("underline") if hasattr(self, 'tr') else "Подчеркнутый"))
            underline_action.triggered.connect(lambda: self.apply_format('underline'))
        
        menu.addSeparator()
        
        bullet_action = menu.addAction("• " + (self.tr("bullet_list") if hasattr(self, 'tr') else "Маркированный список"))
        bullet_action.triggered.connect(lambda: self.apply_format('bullet'))
        
        numbered_action = menu.addAction("1. " + (self.tr("numbered_list") if hasattr(self, 'tr') else "Нумерованный список"))
        numbered_action.triggered.connect(lambda: self.apply_format('numbered'))
        
        # Показываем меню в позиции клика (только если есть действия)
        if menu.actions():
            global_pos = self.body_text.mapToGlobal(position)
            menu.exec(global_pos)
    
    def show_format_menu(self):
        """Показывает меню форматирования (старый метод, оставлен для совместимости)"""
        # Перенаправляем на контекстное меню
        cursor = self.body_text.textCursor()
        if cursor.hasSelection():
            self.show_text_format_menu(QPoint(0, 0))
    
    def apply_format(self, format_type):
        """Применяет форматирование к выделенному тексту"""
        cursor = self.body_text.textCursor()
        fmt = cursor.charFormat()
        
        if format_type == 'bold':
            is_bold = fmt.fontWeight() == QFont.Weight.Bold
            fmt.setFontWeight(QFont.Weight.Bold if not is_bold else QFont.Weight.Normal)
        elif format_type == 'italic':
            fmt.setFontItalic(not fmt.fontItalic())
        elif format_type == 'underline':
            fmt.setUnderlineStyle(QFont.UnderlineStyle.SingleUnderline if fmt.underlineStyle() == QFont.UnderlineStyle.NoUnderline else QFont.UnderlineStyle.NoUnderline)
        elif format_type == 'bullet':
            # Добавляем маркер в начало строки
            if cursor.hasSelection():
                text = cursor.selectedText()
                lines = text.split('\n')
                formatted_lines = ['• ' + line if line and not line.startswith('• ') else line[2:] if line.startswith('• ') else line for line in lines]
                cursor.insertText('\n'.join(formatted_lines))
            else:
                cursor.insertText('• ')
        elif format_type == 'numbered':
            # Добавляем номер в начало строки
            if cursor.hasSelection():
                text = cursor.selectedText()
                lines = text.split('\n')
                formatted_lines = [f"{i+1}. {line}" if line and not any(line.startswith(f"{j}.") for j in range(1, 100)) else line for i, line in enumerate(lines)]
                cursor.insertText('\n'.join(formatted_lines))
            else:
                cursor.insertText('1. ')
        
        cursor.setCharFormat(fmt)
        self.body_text.setTextCursor(cursor)
        self.body_text.setFocus()
    
    def toggle_recipient_data_visibility(self):
        """Переключает видимость данных получателя (идентично toggle_files_visibility)"""
        if hasattr(self, 'recipient_data_content_widget') and hasattr(self, 'recipient_data_toggle_btn'):
            # Сохраняем текущий размер виджета файлов перед изменением
            files_height = None
            if hasattr(self, 'files_card') and self.files_card and self.files_card.isVisible():
                files_height = self.files_card.height()
                if files_height > 0:
                    self._files_card_saved_height = files_height
            
            if self.recipient_data_content_widget.isVisible():
                self.recipient_data_content_widget.hide()
                self.recipient_data_toggle_btn.setText("▼")
            else:
                self.recipient_data_content_widget.show()
                self.recipient_data_toggle_btn.setText("▲")
            
            # Восстанавливаем размер виджета файлов после изменения через таймер
            if hasattr(self, '_files_card_saved_height') and self._files_card_saved_height:
                QTimer.singleShot(10, self._restore_files_card_height)
    
    def _restore_files_card_height(self):
        """Восстанавливает сохраненную высоту карточки файлов"""
        if hasattr(self, 'files_card') and self.files_card and hasattr(self, '_files_card_saved_height'):
            saved_height = self._files_card_saved_height
            if saved_height and saved_height > 0:
                current_height = self.files_card.height()
                # Восстанавливаем минимальную высоту только если она изменилась значительно (более чем на 5px)
                if abs(current_height - saved_height) > 5:
                    self.files_card.setMinimumHeight(saved_height)
                    self.files_card.update()
    
    def _update_prompt_text_width(self):
        """Обновляет ширину переноса текста в виджете промпта на основе реальной ширины виджета"""
        if hasattr(self, 'ai_prompt_text') and self.ai_prompt_text and self.ai_prompt_text.isVisible():
            # Получаем реальную ширину виджета и устанавливаем её как ширину переноса
            width = self.ai_prompt_text.width()
            if width > 0:
                # Учитываем padding (12px слева и справа = 24px)
                text_width = width - 24
                if text_width > 0:
                    self.ai_prompt_text.setLineWrapColumnOrWidth(text_width)
    
    def toggle_files_visibility(self):
        """Переключает видимость списка файлов"""
        if hasattr(self, 'files_content_widget') and hasattr(self, 'files_toggle_btn'):
            if self.files_visible:
                self.files_content_widget.hide()
                self.files_toggle_btn.setText("▼")
                self.files_visible = False
            else:
                self.files_content_widget.show()
                self.files_toggle_btn.setText("▲")
                self.files_visible = True
    
    def create_left_files_widget(self):
        """Создает виджет для прикрепления файлов слева"""
        files_widget = QWidget()
        files_widget.setStyleSheet("background: transparent;")
        # Устанавливаем размерную политику, чтобы виджет растягивался по ширине и не менял размер при открытии/закрытии других виджетов
        files_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(8)  # Уменьшено для компактности
        files_widget.setLayout(files_layout)
        
        # Белая карточка для файлов
        self.files_card = QFrame()
        self.files_card.setObjectName("leftFilesCard")
        # Устанавливаем размерную политику для карточки, чтобы она не меняла размер
        self.files_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.files_card.setStyleSheet("""
            QFrame#leftFilesCard {
                background-color: #FAFAFE;
                border: none;
                border-radius: 18px;
                padding: 0px;
            }
        """)
        
        # Тень для карточки файлов (лиловая)
        files_shadow = QGraphicsDropShadowEffect()
        files_shadow.setBlurRadius(25)
        files_shadow.setXOffset(0)
        files_shadow.setYOffset(10)
        files_shadow.setColor(QColor(167, 139, 250, 20))
        self.files_card.setGraphicsEffect(files_shadow)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(12, 12, 12, 12)  # Уменьшено для компактности
        card_layout.setSpacing(8)  # Уменьшено для компактности
        self.files_card.setLayout(card_layout)
        
        # Заголовок с количеством файлов и стрелкой скрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        # Иконка документа монохромная (того же цвета что и Данные получателя)
        doc_pixmap = QPixmap(24, 24)
        doc_pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(doc_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(200, 180, 255), 2.5))  # Того же цвета что и иконка пользователя
        painter.setBrush(Qt.BrushStyle.NoBrush)  # Прозрачная заливка
        # Рисуем документ: прямоугольник с загнутым верхним правым углом
        # Создаем путь для формы документа
        doc_path = QPainterPath()
        # Основной прямоугольник (начинаем с левого верхнего угла, идем по часовой стрелке)
        doc_path.moveTo(5, 6)  # Левая верхняя точка
        doc_path.lineTo(16, 6)  # Правая верхняя точка (до загнутого угла)
        doc_path.lineTo(16, 9)  # Вниз до начала диагонали
        doc_path.lineTo(19, 6)  # Диагональ загнутого угла (вправо-вверх)
        doc_path.lineTo(19, 21)  # Вниз до правого нижнего угла
        doc_path.lineTo(5, 21)  # Влево до левого нижнего угла
        doc_path.closeSubpath()  # Замыкаем путь
        painter.drawPath(doc_path)
        painter.end()
        title_icon = QLabel()
        title_icon.setPixmap(doc_pixmap)
        header_layout.addWidget(title_icon)
        
        # Заголовок с количеством файлов
        self.files_title_label = QLabel(f"{self.tr('files')} (0)")
        self.files_title_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))  # Вернули 11px
        self.files_title_label.setStyleSheet("color: #2E2E38; background: transparent;")
        header_layout.addWidget(self.files_title_label)
        
        header_layout.addStretch()

        # Кнопка добавления файлов рядом с заголовком (с эмодзи и прозрачным фоном)
        self.header_add_file_btn = QPushButton("➕")
        self.header_add_file_btn.setFixedSize(24, 24)
        self.header_add_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_add_file_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6E6D7A;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(110, 109, 122, 0.08);
                border-radius: 12px;
                color: #6E6D7A;
            }
            QPushButton:pressed {
                background: rgba(110, 109, 122, 0.15);
                border-radius: 12px;
                color: #6E6D7A;
            }
        """)
        self.header_add_file_btn.clicked.connect(self.attach_files)
        # Кнопка всегда видна
        header_layout.addWidget(self.header_add_file_btn)
        
        # Кнопка скрытия/показа (стрелка) - минималистичная, черно-серая
        self.files_toggle_btn = QPushButton("▲")
        self.files_toggle_btn.setObjectName("filesToggleBtn")
        self.files_toggle_btn.setFixedSize(24, 24)
        self.files_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.files_toggle_btn.setStyleSheet("""
            QPushButton#filesToggleBtn {
                background: transparent;
                border: none;
                color: #6E6D7A;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#filesToggleBtn:hover {
                color: #2E2E38;
                background: rgba(46, 46, 56, 0.05);
                border-radius: 4px;
            }
        """)
        self.files_toggle_btn.clicked.connect(self.toggle_files_visibility)
        header_layout.addWidget(self.files_toggle_btn)
        
        card_layout.addLayout(header_layout)
        
        # Контейнер для файлов (скрываемый)
        self.files_content_widget = QWidget()
        self.files_content_widget.setStyleSheet("background: transparent;")
        files_content_layout = QVBoxLayout()
        files_content_layout.setContentsMargins(0, 0, 0, 0)
        files_content_layout.setSpacing(0)
        self.files_content_widget.setLayout(files_content_layout)
        
        # Кнопка добавления файлов внутри рамки (облако-плейсхолдер при отсутствии файлов)
        self.add_file_btn = QPushButton("☁️")
        self.add_file_btn.setMinimumHeight(40)
        self.add_file_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.add_file_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #8B7CF6;
                border: 1px dashed rgba(156, 137, 184, 0.45);
                border-radius: 14px;
                font-size: 22px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: #FAFAFE;
                border-color: rgba(139, 124, 246, 0.9);
                color: #9A8CF0;
            }
            QPushButton:pressed {
                background: #EFEAF7;
                border-color: #8B7CF6;
            }
        """)
        self.add_file_btn.clicked.connect(self.attach_files)
        files_content_layout.addWidget(self.add_file_btn)
        
        # Список файлов (вертикальный) с прокруткой
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(214, 211, 240, 0.25);
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(124, 131, 253, 0.35),
                    stop:1 rgba(214, 211, 240, 0.25));
                border-radius: 4px;
                min-height: 30px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(107, 114, 232, 0.45),
                    stop:1 rgba(196, 190, 232, 0.35));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        scroll_area.setMaximumHeight(280)  # Увеличено для 4 файлов без скролла
        scroll_area.setMinimumHeight(0)
        scroll_area.hide()
        self.files_scroll_area = scroll_area
        
        scroll_content = QWidget()
        self.left_files_list = QVBoxLayout()
        self.left_files_list.setContentsMargins(0, 0, 0, 0)
        self.left_files_list.setSpacing(4)
        scroll_content.setLayout(self.left_files_list)
        
        scroll_area.setWidget(scroll_content)
        files_content_layout.addWidget(scroll_area)
        
        # Добавляем контейнер файлов в карточку
        card_layout.addWidget(self.files_content_widget)
        
        # Флаг видимости файлов
        self.files_visible = True
        
        files_layout.addWidget(self.files_card)
        
        # Сохраняем исходную высоту карточки файлов после первого отображения
        QTimer.singleShot(200, lambda: self._save_files_card_height())
        
        return files_widget
    
    def _save_files_card_height(self):
        """Сохраняет текущую высоту карточки файлов"""
        if hasattr(self, 'files_card') and self.files_card and self.files_card.isVisible():
            height = self.files_card.height()
            if height > 0:
                self._files_card_saved_height = height
                # Устанавливаем минимальную высоту, чтобы layout не уменьшал виджет
                self.files_card.setMinimumHeight(height)
    
    def create_ai_prompt_widget(self):
        """Создает виджет для дополнения к промпту AI"""
        prompt_widget = QWidget()
        prompt_widget.setStyleSheet("background: transparent;")
        # Устанавливаем размерную политику для растягивания по ширине
        prompt_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        prompt_layout = QVBoxLayout()
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.setSpacing(6)  # Уменьшено для компактности
        prompt_widget.setLayout(prompt_layout)
        
        # Пастельная карточка для дополнения к промпту AI
        prompt_card = QFrame()
        prompt_card.setObjectName("aiPromptCard")
        # Устанавливаем размерную политику для растягивания по ширине
        prompt_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        prompt_card.setStyleSheet("""
            QFrame#aiPromptCard {
                background-color: #F8F5F0;
                border: none;
                border-radius: 18px;
                padding: 0px;
            }
        """)
        
        # Тень для карточки (лиловая)
        prompt_shadow = QGraphicsDropShadowEffect()
        prompt_shadow.setBlurRadius(25)
        prompt_shadow.setXOffset(0)
        prompt_shadow.setYOffset(10)
        prompt_shadow.setColor(QColor(167, 139, 250, 20))
        prompt_card.setGraphicsEffect(prompt_shadow)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(10, 8, 10, 8)  # Уменьшены вертикальные отступы
        card_layout.setSpacing(3)  # Уменьшено для компактности
        prompt_card.setLayout(card_layout)
        
        # Заголовок с иконкой волшебной палочки
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        # Иконка звезд полностью монохромная (✨)
        magic_icon = QLabel("✨")
        magic_icon.setFont(QFont("Segoe UI", 14))
        magic_icon.setStyleSheet("color: #6E6D7A; background: transparent;")  # Полностью монохромная
        header_layout.addWidget(magic_icon)
        
        # Текст заголовка
        prompt_title = QLabel("Дополнение к промпту AI")
        prompt_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        prompt_title.setStyleSheet("color: #2E2E38; background: transparent;")
        header_layout.addWidget(prompt_title)
        
        header_layout.addStretch()
        
        # Кнопка скрытия/показа (стрелка)
        self.ai_prompt_toggle_btn = QPushButton("▲")
        self.ai_prompt_toggle_btn.setObjectName("aiPromptToggleBtn")
        self.ai_prompt_toggle_btn.setFixedSize(24, 24)
        self.ai_prompt_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_prompt_toggle_btn.setStyleSheet("""
            QPushButton#aiPromptToggleBtn {
                background: transparent;
                border: none;
                color: #6E6D7A;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#aiPromptToggleBtn:hover {
                color: #2E2E38;
                background: rgba(46, 46, 56, 0.05);
                border-radius: 4px;
            }
        """)
        self.ai_prompt_toggle_btn.clicked.connect(self.toggle_ai_prompt_visibility)
        header_layout.addWidget(self.ai_prompt_toggle_btn)
        
        card_layout.addLayout(header_layout)
        
        # Контейнер для текстового поля (скрываемый)
        self.ai_prompt_content_widget = QWidget()
        self.ai_prompt_content_widget.setStyleSheet("background: transparent;")
        # Устанавливаем размерную политику для растягивания по ширине
        self.ai_prompt_content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        prompt_content_layout = QVBoxLayout()
        prompt_content_layout.setContentsMargins(0, 0, 0, 0)
        prompt_content_layout.setSpacing(3)  # Уменьшено для компактности
        self.ai_prompt_content_widget.setLayout(prompt_content_layout)
        
        # Текстовое поле для дополнения к промпту
        self.ai_prompt_text = QTextEdit()
        self.ai_prompt_text.setPlaceholderText("Добавьте детали, которые нужно учесть...")
        self.ai_prompt_text.setMinimumHeight(45)  # Уменьшено для компактности
        self.ai_prompt_text.setMaximumHeight(100)  # Уменьшено для компактности
        # Используем Expanding для горизонтального направления, чтобы текст использовал всю ширину
        self.ai_prompt_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Используем перенос по ширине виджета, чтобы текст использовал всю доступную ширину перед переносом
        self.ai_prompt_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.ai_prompt_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # Перенос по ширине виджета
        self.ai_prompt_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Отключаем горизонтальный скролл
        self.ai_prompt_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # Вертикальный скролл при необходимости
        self.ai_prompt_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 13px;
                color: #2E2E38;
            }
            QTextEdit:focus {
                border: none;
            }
            QTextEdit::placeholder {
                color: #B4B2C4;
            }
            QScrollBar:vertical {
                background: rgba(214, 211, 240, 0.25);
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(124, 131, 253, 0.35),
                    stop:1 rgba(214, 211, 240, 0.25));
                border-radius: 4px;
                min-height: 30px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(107, 114, 232, 0.45),
                    stop:1 rgba(196, 190, 232, 0.35));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)
        prompt_content_layout.addWidget(self.ai_prompt_text)
        
        card_layout.addWidget(self.ai_prompt_content_widget)
        
        # Флаг видимости
        self.ai_prompt_visible = True
        
        prompt_layout.addWidget(prompt_card)
        
        return prompt_widget
    
    def toggle_ai_prompt_visibility(self):
        """Переключает видимость секции дополнения к промпту AI"""
        if hasattr(self, 'ai_prompt_content_widget') and hasattr(self, 'ai_prompt_toggle_btn'):
            # Сохраняем текущий размер виджета файлов перед изменением
            files_height = None
            if hasattr(self, 'files_card') and self.files_card and self.files_card.isVisible():
                files_height = self.files_card.height()
                if files_height > 0:
                    self._files_card_saved_height = files_height
            
            if self.ai_prompt_visible:
                self.ai_prompt_content_widget.hide()
                self.ai_prompt_toggle_btn.setText("▼")
                self.ai_prompt_visible = False
            else:
                self.ai_prompt_content_widget.show()
                self.ai_prompt_toggle_btn.setText("▲")
                self.ai_prompt_visible = True
            
            # Восстанавливаем размер виджета файлов после изменения через таймер
            if hasattr(self, '_files_card_saved_height') and self._files_card_saved_height:
                QTimer.singleShot(10, self._restore_files_card_height)
    
    def create_left_file_widget(self, file_info, index=None):
        """Создает виджет файла для левого списка (вертикальный, с расширением и размером, с drag & drop)"""
        file_name = file_info['name'] if isinstance(file_info, dict) else os.path.basename(file_info)
        file_path = file_info.get('path', '') if isinstance(file_info, dict) else file_info
        file_size = file_info.get('size', '') if isinstance(file_info, dict) else ''
        
        # Получаем расширение файла
        file_ext = os.path.splitext(file_name)[1].lower().lstrip('.')
        if not file_ext and file_path:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        # Определяем иконку по формату (используем кэш)
        icon_char, icon_color = self._FILE_ICON_MAP.get(file_ext, ('🔗', '#9A90B8'))
        
        file_widget = QFrame()
        file_widget.setObjectName("leftFileCard")
        file_widget.setStyleSheet("""
            QFrame#leftFileCard {
                background: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame#leftFileCard:hover {
                border-color: #9A8CF0;
                background: #FAFAFE;
            }
        """)
        
        # Сохраняем индекс для drag & drop
        file_idx = index if index is not None else (self.attached_files.index(file_info) if file_info in self.attached_files else -1)
        file_widget.file_index = file_idx
        file_widget.file_info = file_info
        
        # Включаем drag & drop через mouse events
        file_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        file_widget._drag_start_pos = None
        
        # Включаем контекстное меню для файла
        file_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        file_widget.customContextMenuRequested.connect(lambda pos: self.show_file_context_menu(file_widget, file_info, pos))
        
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(6)
        file_widget.setLayout(file_layout)
        
        # Иконка файла (монохромная фиолетовая, того же цвета что и Данные получателя)
        file_icon = QLabel(icon_char)
        file_icon.setFont(QFont("Segoe UI", 22))
        file_icon.setStyleSheet("color: #C8B4FF; background: transparent;")  # Того же цвета что и иконка пользователя
        file_icon.setFixedSize(32, 32)
        file_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_icon.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        file_layout.addWidget(file_icon)
        
        # Информация о файле
        file_info_widget = QWidget()
        file_info_layout = QVBoxLayout()
        file_info_layout.setContentsMargins(0, 0, 0, 0)
        file_info_layout.setSpacing(1)  # Уменьшено для компактности
        file_info_widget.setLayout(file_info_layout)
        
        # Имя файла (фиксированная типографика - не меняется при изменении количества файлов)
        name_label = QLabel(file_name)
        name_label.setFont(QFont("Inter", 9, QFont.Weight.Medium))  # Фиксированный размер
        name_label.setStyleSheet("color: #2E2E38; background: transparent;")
        name_label.setWordWrap(False)  # Запрещаем перенос текста
        name_label.setFixedHeight(14)  # Фиксированная высота
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        # Обрезаем длинное имя файла
        if len(file_name) > 25:
            name_label.setText(file_name[:22] + "...")
        file_info_layout.addWidget(name_label)
        
        # Расширение и размер (фиксированная типографика)
        info_text = f".{file_ext.upper()}" if file_ext else ""
        if file_size:
            # Преобразуем размер в строку если это число
            if isinstance(file_size, (int, float)):
                size_mb = file_size / (1024 * 1024)
                size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{file_size / 1024:.1f} KB"
            else:
                size_text = str(file_size)
            info_text += f" • {size_text}"
        info_label = QLabel(info_text)
        info_label.setFont(QFont("Inter", 6))  # Фиксированный размер
        info_label.setStyleSheet("color: #B4B2C4; background: transparent;")
        info_label.setFixedHeight(10)  # Фиксированная высота
        info_label.setWordWrap(False)  # Запрещаем перенос текста
        info_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        file_info_layout.addWidget(info_label)
        
        file_layout.addWidget(file_info_widget, stretch=1)
        
        # Кнопка удаления (компактная) - с эмодзи и прозрачным фоном
        remove_btn = QPushButton("❌")
        remove_btn.setFixedSize(20, 20)  # Уменьшено для компактности
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6E6D7A;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(110, 109, 122, 0.1);
                border-radius: 10px;
                color: #6E6D7A;
            }
        """)
        remove_btn.clicked.connect(lambda checked=False, fi=file_info: self.remove_file(fi))
        file_layout.addWidget(remove_btn)
        
        # Переопределяем mouse events для drag & drop
        original_mouse_press = file_widget.mousePressEvent
        original_mouse_move = file_widget.mouseMoveEvent
        original_mouse_release = file_widget.mouseReleaseEvent
        
        def mouse_press_event(e):
            if e.button() == Qt.MouseButton.LeftButton:
                if not hasattr(file_widget, '_drag_start_pos'):
                    file_widget._drag_start_pos = None
                file_widget._drag_start_pos = e.pos()
                file_widget.setCursor(Qt.CursorShape.ClosedHandCursor)
                # Эффект "захвата" файла - полупрозрачный и приподнятый
                opacity_effect = QGraphicsOpacityEffect(file_widget)
                opacity_effect.setOpacity(0.6)
                file_widget.setGraphicsEffect(opacity_effect)
                file_widget.setStyleSheet("""
                    QFrame#leftFileCard {
                        background: #E8E0F5;
                        border: 1px solid rgba(167, 139, 250, 0.5);
                        border-radius: 8px;
                        padding: 6px;
                    }
                """)
            if original_mouse_press:
                original_mouse_press(e)
        
        def mouse_move_event(e):
            if hasattr(file_widget, '_drag_start_pos') and file_widget._drag_start_pos is not None:
                # Проверяем, что мышь переместилась достаточно далеко
                move_distance = (e.pos() - file_widget._drag_start_pos).manhattanLength()
                if move_distance > 10:
                    # Начинаем перетаскивание - обновляем позицию (с защитой от рекурсии)
                    if not hasattr(self, '_is_dragging') or not self._is_dragging:
                        self._is_dragging = True
                        try:
                            # Используем глобальную позицию для более точного определения
                            global_pos = file_widget.mapToGlobal(e.pos())
                            # Создаем QPoint из глобальной позиции
                            from PyQt6.QtCore import QPoint
                            global_point = QPoint(global_pos.x(), global_pos.y())
                            self._update_file_drag_position(file_widget, global_point)
                        except Exception as ex:
                            print(f"[DEBUG] Ошибка при drag & drop: {ex}")
                        finally:
                            self._is_dragging = False
            if original_mouse_move:
                original_mouse_move(e)
        
        def mouse_release_event(e):
            if hasattr(file_widget, '_drag_start_pos') and file_widget._drag_start_pos is not None:
                file_widget._drag_start_pos = None
                file_widget.setCursor(Qt.CursorShape.OpenHandCursor)
                # Возвращаем нормальную видимость - убираем эффект прозрачности
                file_widget.setGraphicsEffect(None)
                file_widget.setStyleSheet("""
                    QFrame#leftFileCard {
                        background: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 4px;
                    }
                    QFrame#leftFileCard:hover {
                        background: #FAFAFE;
                    }
                """)
            if original_mouse_release:
                original_mouse_release(e)
        
        file_widget.mousePressEvent = mouse_press_event
        file_widget.mouseMoveEvent = mouse_move_event
        file_widget.mouseReleaseEvent = mouse_release_event
        
        return file_widget
    
    def _update_file_drag_position(self, source_widget, global_pos):
        """Обновляет позицию файла при перетаскивании"""
        try:
            if not hasattr(self, 'files_scroll_area') or not self.files_scroll_area:
                return
            
            scroll_widget = self.files_scroll_area.widget()
            if not scroll_widget:
                return
            
            # Проверяем, что source_widget имеет нужные атрибуты
            if not hasattr(source_widget, 'file_index') or not hasattr(source_widget, 'file_info'):
                return
            
            # Получаем позицию курсора относительно scroll area
            try:
                if isinstance(global_pos, QPoint):
                    scroll_pos = self.files_scroll_area.mapFromGlobal(global_pos)
                else:
                    # Если передан QMouseEvent, используем его globalPos
                    scroll_pos = self.files_scroll_area.mapFromGlobal(global_pos)
            except:
                return
            
            # Находим все виджеты файлов и определяем новый индекс
            source_idx = source_widget.file_index
            if source_idx < 0 or source_idx >= len(self.attached_files):
                return
            
            # Проходим по всем виджетам файлов и находим, над каким находится курсор
            target_idx = source_idx
            if hasattr(self, 'left_files_list') and self.left_files_list:
                for i in range(self.left_files_list.count()):
                    item = self.left_files_list.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if hasattr(widget, 'file_index') and widget != source_widget:
                            try:
                                # Получаем позицию виджета относительно scroll area
                                widget_global_pos = widget.mapToGlobal(QPoint(0, 0))
                                widget_pos = self.files_scroll_area.mapFromGlobal(widget_global_pos)
                                widget_height = widget.height()
                                
                                # Проверяем, находится ли курсор над этим виджетом
                                if scroll_pos.y() >= widget_pos.y() and scroll_pos.y() <= widget_pos.y() + widget_height:
                                    target_idx = widget.file_index
                                    # Если перетаскиваем вниз, увеличиваем индекс
                                    if source_idx < widget.file_index:
                                        target_idx = widget.file_index + 1
                                    break
                            except:
                                continue
            
            # Перемещаем файл только если позиция изменилась и валидна
            if source_idx != target_idx and 0 <= target_idx <= len(self.attached_files):
                # Защита от множественных обновлений
                if hasattr(self, '_updating_drag') and self._updating_drag:
                    return
                self._updating_drag = True
                
                try:
                    file_item = self.attached_files.pop(source_idx)
                    # Корректируем индекс если удалили элемент выше целевого
                    if source_idx < target_idx:
                        target_idx -= 1
                    target_idx = max(0, min(target_idx, len(self.attached_files)))
                    self.attached_files.insert(target_idx, file_item)
                    self.update_files_list()
                    self.on_field_changed()
                finally:
                    self._updating_drag = False
        except Exception as ex:
            print(f"[DEBUG] Ошибка в _update_file_drag_position: {ex}")
    
    def eventFilter(self, obj, event):
        """Оптимизированная обработка событий для текстового редактора"""
        if obj == self.body_text:
            # Оптимизируем обработку событий выделения
            if event.type() == QEvent.Type.MouseMove:
                # Обновляем только при необходимости
                return False
        return super().eventFilter(obj, event)
