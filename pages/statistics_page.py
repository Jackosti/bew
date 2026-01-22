"""
Страница статистики - отдельный модуль
"""
from datetime import datetime, timedelta
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QProgressBar,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QRect
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen

# Импорты из основного файла
from email_app import tr, get_current_language, get_app_colors

# Импортируем функции и константы из email_app (избегаем циклического импорта)
# Используем локальные импорты внутри функций для избежания циклических зависимостей


# Глобальная переменная для языка (будет обновляться)
CURRENT_LANGUAGE = 'de'

class ClipboardIconWidget(QWidget):
    """Кастомный виджет для иконки клипборда с двумя линиями"""
    
    def __init__(self, parent=None, color="#4A90E2"):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(40, 40)  # Увеличено с 32x32
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Клипборд - прямоугольник с закругленными углами
        pen = QPen(self.color, 2.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))  # Белая заливка внутри
        
        # Основной прямоугольник клипборда (увеличен пропорционально)
        clipboard_rect = QRect(6, 9, 28, 24)
        painter.drawRoundedRect(clipboard_rect, 2, 2)
        
        # Верхняя часть клипа (закругленная)
        clip_rect = QRect(11, 4, 18, 8)
        painter.drawRoundedRect(clip_rect, 3, 3)
        
        # Две линии внутри клипборда
        line_pen = QPen(self.color, 1.8)
        painter.setPen(line_pen)
        # Первая линия
        painter.drawLine(11, 17, 29, 17)
        # Вторая линия
        painter.drawLine(11, 22, 29, 22)


class CalendarIconWidget(QWidget):
    """Кастомный виджет для иконки календаря - монохромная с прозрачной внутренней частью"""
    
    def __init__(self, parent=None, color="#4A90E2"):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(40, 40)  # Увеличено
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Календарь - прямоугольник с закругленными углами
        pen = QPen(self.color, 2.5)
        painter.setPen(pen)
        # Прозрачная заливка внутри (без заливки)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        
        # Основной прямоугольник календаря (внешний контур)
        calendar_rect = QRect(6, 10, 28, 24)
        painter.drawRoundedRect(calendar_rect, 3, 3)
        
        # Верхняя часть календаря (заголовок) - только нижняя граница
        header_line_pen = QPen(self.color, 1.8)
        painter.setPen(header_line_pen)
        # Горизонтальная линия, разделяющая заголовок и основную часть
        painter.drawLine(6, 18, 34, 18)
        
        # Две вертикальные линии для разделения дней (только в основной части)
        line_pen = QPen(self.color, 1.5)
        painter.setPen(line_pen)
        # Первая вертикальная линия
        painter.drawLine(15, 18, 15, 34)
        # Вторая вертикальная линия
        painter.drawLine(25, 18, 25, 34)
        
        # Горизонтальная линия для разделения недель
        painter.drawLine(6, 24, 34, 24)


class CustomCalendarWidget(QWidget):
    """Современный календарь в стиле Apple - переделан с нуля"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calendar_stats = {}
        self.current_date = datetime.now().date()
        # Обновляем CURRENT_LANGUAGE из локализации
        global CURRENT_LANGUAGE
        CURRENT_LANGUAGE = get_current_language()
        self.setup_ui()
        self.update_display()
    
    def setup_ui(self):
        """Создает чистый календарь с нуля"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # Главный контейнер - белый фон с легким эффектом Glassmorphism (без границ)
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 16px;
                border: none;
            }
        """)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container.setLayout(container_layout)
        
        # Светлый лиловый фон заголовка (растянут до краев) - еще более прозрачно и светло
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(232, 213, 255, 0.5), stop:1 rgba(240, 229, 255, 0.5));
                border-radius: 16px 16px 0px 0px;
            }
        """)
        header.setFixedHeight(80)  # Увеличено для растяжения
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(8)
        header.setLayout(header_layout)
        
        # Верхняя строка: навигация и месяц/год
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        
        # Стрелка влево (кликабельная) - с еще более светлым прозрачным светло-фиолетовым фоном
        from PyQt6.QtWidgets import QPushButton
        self.left_arrow_btn = QPushButton("‹")
        self.left_arrow_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.left_arrow_btn.setStyleSheet("""
            QPushButton {
                color: #5E548A;
                background-color: rgba(232, 213, 255, 0.3);
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(232, 213, 255, 0.5);
                border-radius: 4px;
            }
        """)
        self.left_arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.left_arrow_btn.clicked.connect(self.prev_month)
        top_row.addWidget(self.left_arrow_btn)
        
        # Месяц и год - темно-фиолетовый текст на светлом лиловом фоне (чуть меньше, как дни недели)
        self.month_label = QLabel()
        self.month_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))  # Уменьшен размер
        self.month_label.setStyleSheet("color: #5E548A; background: transparent; border: none;")  # Темно-фиолетовый
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.month_label, stretch=1)
        
        # Иконка календаря (монохромная темно-фиолетовая)
        calendar_icon = QLabel("📅")
        calendar_icon.setFont(QFont("Segoe UI", 14))
        calendar_icon.setStyleSheet("color: #5E548A; background: transparent; border: none;")  # Темно-фиолетовый
        top_row.addWidget(calendar_icon)
        
        # Стрелка вправо (кликабельная) - с еще более светлым прозрачным светло-фиолетовым фоном
        self.right_arrow_btn = QPushButton("›")
        self.right_arrow_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.right_arrow_btn.setStyleSheet("""
            QPushButton {
                color: #5E548A;
                background-color: rgba(232, 213, 255, 0.3);
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(232, 213, 255, 0.5);
                border-radius: 4px;
            }
        """)
        self.right_arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.right_arrow_btn.clicked.connect(self.next_month)
        top_row.addWidget(self.right_arrow_btn)
        
        header_layout.addLayout(top_row)
        
        # Дни недели - горизонтально, растянуты до границ, белый текст на градиентном фоне
        weekdays_layout = QHBoxLayout()
        weekdays_layout.setContentsMargins(0, 0, 0, 0)
        weekdays_layout.setSpacing(0)
        
        self.weekday_labels = []
        # Используем локализованные дни недели
        weekdays_short = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        if CURRENT_LANGUAGE == 'ru':
            weekdays_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        elif CURRENT_LANGUAGE == 'en':
            weekdays_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for day in weekdays_short:
            label = QLabel(day)
            label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            # Еще более светлый прозрачный светло-фиолетовый фон для дней недели
            label.setStyleSheet("color: #5E548A; background-color: rgba(232, 213, 255, 0.3); border: none; border-radius: 4px;")  # Еще светлее
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            weekdays_layout.addWidget(label)
            self.weekday_labels.append(label)
        
        header_layout.addLayout(weekdays_layout)
        container_layout.addWidget(header)
        
        # Сетка дней - белый фон с легким эффектом Glassmorphism (без границ)
        days_frame = QFrame()
        days_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 0px 0px 16px 16px;
                border: none;
            }
        """)
        self.days_grid = QGridLayout()
        self.days_grid.setContentsMargins(12, 12, 12, 12)
        self.days_grid.setSpacing(8)
        self.days_grid.setVerticalSpacing(12)
        
        for row in range(6):
            self.days_grid.setRowMinimumHeight(row, 38)  # Увеличено для растяжения
        
        days_frame.setLayout(self.days_grid)
        container_layout.addWidget(days_frame)
        
        # Создаем ячейки
        self.day_labels = []
        self.heart_labels = []
        self.day_containers = []
        
        for row in range(6):
            row_labels = []
            heart_row = []
            container_row = []
            for col in range(7):
                # Контейнер - явно прозрачный фон, без фиолетовых квадратов
                cont = QWidget()
                cont.setStyleSheet("background: transparent; border: none;")
                cont_layout = QVBoxLayout()
                cont_layout.setContentsMargins(0, 0, 0, 0)
                cont_layout.setSpacing(4)
                cont.setLayout(cont_layout)
                
                # Метка дня - темно-синий/фиолетовый текст для контраста
                day_lbl = QLabel()
                day_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
                day_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                day_lbl.setFixedSize(28, 28)
                day_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                day_lbl.setStyleSheet("""
                    QLabel {
                        color: #2D1B3D;
                        background: transparent;
                        border: none;
                    }
                """)
                cont_layout.addWidget(day_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
                
                # Сердечко - показывается на датах с письмами
                heart = QLabel("♥")
                heart.setFont(QFont("Segoe UI", 7))
                heart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                heart.setStyleSheet("color: #FF69B4; background: transparent; margin-top: 2px;")
                heart.hide()
                cont_layout.addWidget(heart, alignment=Qt.AlignmentFlag.AlignCenter)
                
                self.days_grid.addWidget(cont, row, col)
                row_labels.append(day_lbl)
                heart_row.append(heart)
                container_row.append(cont)
            
            self.day_labels.append(row_labels)
            self.heart_labels.append(heart_row)
            self.day_containers.append(container_row)
        
        layout.addWidget(container)
    
    def update_display(self):
        """Обновляет отображение календаря - упрощенная версия"""
        today = datetime.now().date()
        # Используем self.current_date для отображения выбранного месяца
        display_date = self.current_date
        
        # Обновляем заголовок
        month_keys = ['month_january', 'month_february', 'month_march', 'month_april', 
                     'month_may', 'month_june', 'month_july', 'month_august', 
                     'month_september', 'month_october', 'month_november', 'month_december']
        
        # Обновляем CURRENT_LANGUAGE перед использованием
        global CURRENT_LANGUAGE
        try:
            from email_app import CURRENT_LANGUAGE as EMAIL_APP_LANG
            CURRENT_LANGUAGE = EMAIL_APP_LANG
        except:
            CURRENT_LANGUAGE = get_current_language()
        
        month_name = tr(month_keys[display_date.month - 1])
        
        self.month_label.setText(f"{month_name} {display_date.year}")
        
        # Выделяем текущий день недели - темно-фиолетовый текст на светлом лиловом фоне
        if hasattr(self, 'weekday_labels') and len(self.weekday_labels) > 0:
            current_weekday = today.weekday() if display_date.month == today.month and display_date.year == today.year else None
            for i, weekday_label in enumerate(self.weekday_labels):
                if current_weekday is not None and i == current_weekday:
                    weekday_label.setStyleSheet("color: #5E548A; background-color: rgba(255, 255, 255, 0.5); border-radius: 6px; border: none; font-weight: bold;")
                else:
                    weekday_label.setStyleSheet("color: #5E548A; background: transparent; border: none;")  # Темно-фиолетовый
        
        # Очищаем все ячейки
        for row in range(6):
            for col in range(7):
                if row < len(self.day_containers) and col < len(self.day_containers[row]):
                    self.day_containers[row][col].setStyleSheet("background: transparent; border: none;")
                if row < len(self.day_labels) and col < len(self.day_labels[row]):
                    self.day_labels[row][col].setText("")
                    self.day_labels[row][col].setStyleSheet("""
                        QLabel {
                            color: #2D1B3D;
                            background: transparent;
                            border: none;
                        }
                    """)
                    self.day_labels[row][col].setFixedSize(28, 28)
                    self.day_labels[row][col].setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                if row < len(self.heart_labels) and col < len(self.heart_labels[row]):
                    self.heart_labels[row][col].hide()
        
        # Получаем первый день месяца (используем display_date)
        first_day = display_date.replace(day=1)
        first_weekday = first_day.weekday()
        
        # Количество дней в месяце
        if display_date.month == 12:
            next_month = display_date.replace(year=display_date.year + 1, month=1, day=1)
        else:
            next_month = display_date.replace(month=display_date.month + 1, day=1)
        last_day = next_month - timedelta(days=1)
        days_in_month = last_day.day
        
        # Находим лучший день (день с максимальным количеством заявок)
        best_day_count = 0
        if self.calendar_stats:
            best_day_count = max(self.calendar_stats.values()) if self.calendar_stats.values() else 0
        
        # Заполняем календарь
        day_num = 1
        for row in range(6):
            for col in range(7):
                if row == 0 and col < first_weekday:
                    continue
                elif day_num > days_in_month:
                    break
                
                label = self.day_labels[row][col]
                heart = self.heart_labels[row][col]
                container = self.day_containers[row][col]
                
                label.setText(str(day_num))
                
                try:
                    check_date = display_date.replace(day=day_num)
                except ValueError:
                    continue
                
                count = self.calendar_stats.get(check_date, 0)
                is_today = (day_num == today.day and check_date.month == today.month and check_date.year == today.year)
                is_weekend = (col == 5 or col == 6)
                is_best_day = (count == best_day_count and count > 0 and not is_today)
                
                # Очищаем tooltip
                container.setToolTip("")
                label.setToolTip("")
                
                if is_today:
                    # Сегодня - обводка только вокруг числа, сердце вне обводки
                    container.setFixedSize(28, 28)
                    container.setStyleSheet("background: transparent; border: none;")
                    label.setStyleSheet("""
                        QLabel {
                            color: #2D1B3D;
                            background: transparent;
                            border: 2px solid #B8A8F5;
                            border-radius: 14px;
                            font-weight: bold;
                        }
                    """)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    if count > 0:
                        heart.show()
                        container.setToolTip(f"{count} {tr('applications') if count > 1 else tr('application_singular')}")
                        label.setToolTip(f"{count} {tr('applications') if count > 1 else tr('application_singular')}")
                    else:
                        heart.hide()
                elif is_weekend:
                    # Выходные - приглушенно-красные или розовые без подложек
                    container.setFixedSize(28, 28)
                    container.setStyleSheet("background: transparent; border: none;")
                    label.setStyleSheet("""
                        QLabel {
                            color: #E57373;
                            background: transparent;
                            border: none;
                        }
                    """)
                    if count > 0:
                        heart.show()
                        container.setToolTip(f"{count} {tr('applications') if count > 1 else tr('application_singular')}")
                        label.setToolTip(f"{count} {tr('applications') if count > 1 else tr('application_singular')}")
                    else:
                        heart.hide()
                elif count > 0:
                    # Есть письма - показываем сердце, чистый фон БЕЗ фиолетовых квадратов
                    container.setFixedSize(28, 28)
                    container.setStyleSheet("background: transparent; border: none;")
                    label.setStyleSheet("""
                        QLabel {
                            color: #2D1B3D;
                            background: transparent;
                            border: none;
                        }
                    """)
                    heart.show()
                    # Добавляем tooltip с количеством заявок
                    tooltip_text = f"{count} {tr('applications') if count > 1 else tr('application_singular')}"
                    if is_best_day:
                        tooltip_text += " ⭐"
                    container.setToolTip(tooltip_text)
                    label.setToolTip(tooltip_text)
                else:
                    # Обычный день - чистый фон БЕЗ фиолетовых квадратов
                    container.setFixedSize(28, 28)
                    container.setStyleSheet("background: transparent; border: none;")
                    label.setStyleSheet("""
                        QLabel {
                            color: #2D1B3D;
                            background: transparent;
                            border: none;
                        }
                    """)
                    heart.hide()
                
                day_num += 1
    
    def set_calendar_stats(self, stats):
        """Устанавливает статистику для отображения"""
        self.calendar_stats = stats
        self.update_display()
    
    def check_and_update(self):
        """Проверяет, изменился ли день или месяц, и обновляет календарь"""
        today = datetime.now().date()
        if today != self.current_date or today.month != self.current_date.month:
            self.update_display()
    
    def prev_month(self):
        """Переключает на предыдущий месяц"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self.update_display()
    
    def next_month(self):
        """Переключает на следующий месяц"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        self.update_display()
    
    def update_language(self):
        """Обновляет дни недели при смене языка"""
        global CURRENT_LANGUAGE
        try:
            from email_app import CURRENT_LANGUAGE as EMAIL_APP_LANG
            CURRENT_LANGUAGE = EMAIL_APP_LANG
        except:
            CURRENT_LANGUAGE = get_current_language()
        
        # Используем локализованные дни недели
        weekdays_short = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        if CURRENT_LANGUAGE == 'ru':
            weekdays_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        elif CURRENT_LANGUAGE == 'en':
            weekdays_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for i, label in enumerate(self.weekday_labels):
            if i < len(weekdays_short):
                label.setText(weekdays_short[i])
        
        # Обновляем заголовок месяца
        self.update_display()


class StatisticsPage(QWidget):
    """Страница статистики"""
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.last_sent_at = None
        self.last_update_date = datetime.now().date()
        self.is_active = False
        # Обновляем CURRENT_LANGUAGE из email_app
        self._update_imports()
        self.setup_ui()
        # Таймер для обновления календаря при смене дня/месяца
        self.calendar_update_timer = QTimer()
        self.calendar_update_timer.timeout.connect(self.update_calendar_display)
        # Таймер для обновления статистики при смене дня/месяца (проверяем каждую минуту)
        self.stats_update_timer = QTimer()
        self.stats_update_timer.timeout.connect(self.check_and_update_stats)
    
    def _update_imports(self):
        """Обновляет импорты из email_app для избежания циклических зависимостей"""
        global CURRENT_LANGUAGE
        try:
            from email_app import CURRENT_LANGUAGE as EMAIL_APP_LANG
            CURRENT_LANGUAGE = EMAIL_APP_LANG
        except:
            pass
    
    def activate(self):
        """Активирует страницу - загружает данные и запускает таймеры"""
        if not self.is_active:
            self.is_active = True
            # Вызываем update_calendar_display сразу после активации
            QTimer.singleShot(200, self.update_calendar_display)
            self.load_statistics()
            # Запускаем таймеры только когда страница активна
            self.calendar_update_timer.start(60000)  # Проверяем каждую минуту
        self.stats_update_timer.start(60000)  # Проверяем каждую минуту для реального времени
    
    def deactivate(self):
        """Деактивирует страницу - останавливает таймеры"""
        if self.is_active:
            self.is_active = False
            self.calendar_update_timer.stop()
            self.stats_update_timer.stop()
    
    def check_and_update_stats(self):
        """Проверяет, изменился ли день, и обновляет статистику"""
        if not self.is_active:
            return
        current_date = datetime.now().date()
        if current_date != self.last_update_date:
            self.last_update_date = current_date
            # Добавляем легкую анимацию при обновлении
            self.animate_statistics_update()
            self.load_statistics()
    
    def animate_statistics_update(self):
        """Легкая анимация обновления статистики"""
        # Анимация fade-in для трекеров
        trackers = [
            self.total_apps_tracker, self.avg_per_day_tracker, 
            self.this_month_tracker, self.last_sent_tracker
        ]
        for tracker in trackers:
            if tracker:
                # Создаем анимацию прозрачности
                animation = QPropertyAnimation(tracker, b"windowOpacity")
                animation.setDuration(300)
                animation.setStartValue(0.3)
                animation.setEndValue(1.0)
                animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                animation.start()
    
    def refresh_statistics(self):
        """Публичный метод для обновления статистики извне"""
        self.load_statistics()
    
    def setup_ui(self):
        """Создает интерфейс статистики"""
        colors = get_app_colors()
        
        # Создаем скроллируемую область для оконного режима
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Плавный скролл
        scroll_area.verticalScrollBar().setSingleStep(5)
        scroll_area.horizontalScrollBar().setSingleStep(5)
        scroll_area.verticalScrollBar().setPageStep(20)
        scroll_area.horizontalScrollBar().setPageStep(20)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(167, 139, 250, 0.5);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(167, 139, 250, 0.7);
            }
        """)
        
        # Контейнер для контента
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 30, 40, 30)
        content_widget.setLayout(layout)
        
        scroll_area.setWidget(content_widget)
        
        # Устанавливаем фон через менеджер тем (как в profile_page.py)
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
        
        # Главный layout для скролла
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
        
        # Сохраняем ссылку на layout для добавления виджетов
        self.content_layout = layout
        
        # Заголовок
        self.title_label = QLabel(tr("statistics"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_font = QFont("Inter", 22, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"""
            color: #2E2E38;
            margin-bottom: 20px; 
            background: transparent;
        """)
        layout.addWidget(self.title_label)
        
        # ГЛАВНЫЙ LAYOUT: слева контент, справа календарь
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(20)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # ЛЕВАЯ КОЛОНКА: Виджет "Сегодня" с целью недели внутри
        left_column = QVBoxLayout()
        left_column.setSpacing(20)
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Карточка "Сегодня: X" - с градиентом слева фиолетовый, направо белый
        self.today_card = QFrame()
        self.today_card.setObjectName("todayCard")
        self.today_card.setStyleSheet("""
            QFrame#todayCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B8A8F5, stop:1 #FFFFFF);
                border-radius: 20px;
                border: none;
                padding: 0px;
            }
        """)
        today_layout = QVBoxLayout()
        today_layout.setContentsMargins(20, 18, 20, 18)
        today_layout.setSpacing(0)
        self.today_card.setLayout(today_layout)
        
        # Градиентный фон сверху (фиолетовый слева, белый справа) - с текстом "x заявка сегодня"
        gradient_section = QFrame()
        gradient_section.setFixedHeight(80)  # Высота градиента
        gradient_section.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)
        gradient_layout = QHBoxLayout()
        gradient_layout.setContentsMargins(0, 0, 0, 0)
        gradient_layout.setSpacing(12)
        gradient_section.setLayout(gradient_layout)
        
        # Белый квадрат с числом x внутри
        number_box = QFrame()
        number_box.setFixedSize(56, 56)  # Размер квадрата
        number_box.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: none;
            }
        """)
        # Добавляем большую тень для 3D эффекта
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)  # Больше тени
        shadow.setXOffset(0)
        shadow.setYOffset(4)  # Больше смещение для 3D
        shadow.setColor(QColor(0, 0, 0, 60))  # Темнее тень
        number_box.setGraphicsEffect(shadow)
        
        number_layout = QVBoxLayout()
        number_layout.setContentsMargins(0, 0, 0, 0)
        number_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number_box.setLayout(number_layout)
        
        # Число x в белом квадрате
        self.today_count_label = QLabel("0")
        self.today_count_label.setFont(QFont("Inter", 32, QFont.Weight.Bold))  # Размер числа
        self.today_count_label.setStyleSheet("color: #3D2B5D; background: transparent;")  # Темнее
        self.today_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number_layout.addWidget(self.today_count_label)
        gradient_layout.addWidget(number_box)
        
        # Текст "заявка сегодня" - на градиенте справа (без фиолетового фона сзади)
        self.today_header_label = QLabel("заявка сегодня")  # Будет обновляться динамически
        self.today_header_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.today_header_label.setStyleSheet("color: #3D2B5D; background: transparent;")  # Темнее
        gradient_layout.addWidget(self.today_header_label)
        gradient_layout.addStretch()
        
        today_layout.addWidget(gradient_section)
        
        # Внутри виджета "Сегодня" - виджет "Цель недели" (белый) - ложится на прогресс-бар
        self.week_goal_card = QFrame()
        self.week_goal_card.setObjectName("weekGoalCard")
        self.week_goal_card.setStyleSheet("""
            QFrame#weekGoalCard {
                background-color: rgba(255, 255, 255, 1.0);
                border-radius: 16px;
                border: none;
                padding: 0px;
            }
        """)
        # Используем относительное позиционирование для наложения элементов
        self.week_goal_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        week_goal_layout = QVBoxLayout()
        week_goal_layout.setContentsMargins(16, 14, 16, 14)
        week_goal_layout.setSpacing(12)
        self.week_goal_card.setLayout(week_goal_layout)
        
        # Текст "Цель недели" снизу
        week_goal_header = QLabel(tr("week_goal"))
        week_goal_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        week_goal_header.setStyleSheet("color: #3D2B5D; background: transparent;")  # Темнее
        week_goal_layout.addWidget(week_goal_header)
        
        # Контейнер для прогресс-бара
        progress_wrapper = QWidget()
        progress_wrapper.setFixedHeight(50)  # Высота для прогресс-бара
        progress_wrapper.setStyleSheet("background: transparent;")
        progress_wrapper_layout = QVBoxLayout()
        progress_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        progress_wrapper_layout.setSpacing(0)
        progress_wrapper.setLayout(progress_wrapper_layout)
        
        # Прогресс-бар с фиолетовым цветом и текстом "x/7 заявок" внутри - увеличен по вертикали
        progress_container = QHBoxLayout()
        progress_container.setContentsMargins(0, 0, 0, 0)
        progress_container.setSpacing(0)
        
        # Кастомный виджет для прогресс-бара с текстом внутри
        class ProgressBarWithText(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setFixedHeight(32)
                self.setStyleSheet("background: transparent;")
                
                layout = QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
                self.setLayout(layout)
                
                self.progress_bar = QProgressBar()
                self.progress_bar.setMinimum(0)
                self.progress_bar.setMaximum(7)
                self.progress_bar.setValue(0)
                self.progress_bar.setFormat("")
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: none;
                        border-radius: 10px;
                        background-color: rgba(245, 245, 245, 0.8);
                        height: 32px;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #B8A8F5,
                            stop:1 #A394F0);
                        border-radius: 10px;
                    }
                """)
                layout.addWidget(self.progress_bar)
                
                # Текст поверх прогресс-бара
                self.text_label = QLabel("0/7 заявок", self)
                self.text_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                self.text_label.setStyleSheet("color: #3D2B5D; background: transparent;")
                self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            def resizeEvent(self, event):
                super().resizeEvent(event)
                if self.progress_bar and self.text_label:
                    progress_rect = self.progress_bar.geometry()
                    self.text_label.setGeometry(progress_rect)
            
            def setValue(self, value):
                self.progress_bar.setValue(value)
            
            def setText(self, text):
                self.text_label.setText(text)
        
        self.progress_with_text = ProgressBarWithText(progress_wrapper)
        self.week_progress = self.progress_with_text.progress_bar
        self.progress_text_label = self.progress_with_text.text_label
        progress_wrapper_layout.addWidget(self.progress_with_text)
        week_goal_layout.addWidget(progress_wrapper)
        
        # Текст "Осталось X заявок · Y дней" (темнее, числа жирным)
        self.week_status_label = QLabel("")
        self.week_status_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.week_status_label.setStyleSheet("color: #3D2B5D; background: transparent;")  # Темнее
        self.week_status_label.setTextFormat(Qt.TextFormat.RichText)  # Поддержка HTML
        week_goal_layout.addWidget(self.week_status_label)
        
        today_layout.addWidget(self.week_goal_card)
        left_column.addWidget(self.today_card)
        
        # Общая статистика - 4 карточки в одной группе (с полу-фиолетовым фоном)
        general_stats_container = QFrame()
        general_stats_container.setObjectName("generalStatsContainer")
        general_stats_container.setStyleSheet("""
            QFrame#generalStatsContainer {
                background-color: rgba(184, 168, 245, 0.15);
                border-radius: 20px;
                border: none;
                padding: 20px;
            }
        """)
        general_stats_layout = QVBoxLayout()
        general_stats_layout.setSpacing(20)
        general_stats_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок секции
        self.trackers_title = QLabel(tr("general_stats"))
        self.trackers_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.trackers_title.setStyleSheet("color: #2E2E38; background: transparent; margin-bottom: 12px;")
        general_stats_layout.addWidget(self.trackers_title)
        
        # Одна строка: 2 карточки (убрали виджеты последней активности, так как они справа)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        cards_row.setContentsMargins(0, 0, 0, 0)
        
        # Карточка 1: Всего отправлено
        self.total_apps_tracker = self.create_stat_card(tr("total_sent_label"), "0", "applications", tr("total_sent_all_time"))
        cards_row.addWidget(self.total_apps_tracker)
        
        # Карточка 2: В среднем в день
        self.avg_per_day_tracker = self.create_stat_card(tr("avg_per_day"), "0", "average", "")
        cards_row.addWidget(self.avg_per_day_tracker)
        
        general_stats_layout.addLayout(cards_row)
        
        general_stats_container.setLayout(general_stats_layout)
        left_column.addWidget(general_stats_container)
        
        # Контейнер для левой колонки (без max-width)
        left_column_widget = QWidget()
        left_column_widget.setLayout(left_column)
        main_content_layout.addWidget(left_column_widget, stretch=1)
        
        # ПРАВАЯ КОЛОНКА: Календарь, последняя отправка, популярная должность
        right_column = QVBoxLayout()
        right_column.setSpacing(20)
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Календарь
        self.calendar_card = QFrame()
        self.calendar_card.setObjectName("calendarCard")
        self.calendar_card.setFixedWidth(320)  # Вернули стандартную ширину
        self.calendar_card.setStyleSheet("""
            QFrame#calendarCard {
                background-color: transparent;
                border-radius: 0px;
                border: none;
                padding: 0px;
            }
        """)
        calendar_layout = QVBoxLayout()
        calendar_layout.setContentsMargins(0, 0, 0, 0)
        calendar_layout.setSpacing(0)
        self.calendar_card.setLayout(calendar_layout)
        
        # Кастомный виджет календаря (растянут по вертикали)
        self.calendar_widget = CustomCalendarWidget()
        self.calendar_widget.setFixedSize(300, 280)  # Стандартная ширина, увеличенная высота
        calendar_layout.addWidget(self.calendar_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        right_column.addWidget(self.calendar_card)
        
        # Вызываем update_calendar_display сразу после создания календаря
        QTimer.singleShot(150, self.update_calendar_display)
        
        # Карточка последней отправки (снизу календаря) - показываем название должности
        self.last_card = QFrame()
        self.last_card.setObjectName("lastCard")
        self.last_card.setFixedWidth(320)  # Стандартная ширина
        self.last_card.setStyleSheet("""
            QFrame#lastCard {
                background-color: rgba(255, 255, 255, 1.0);
                border-radius: 20px;
                border: 1px solid rgba(200, 200, 200, 0.2);
                padding: 0px;
            }
        """)
        last_layout = QVBoxLayout()
        last_layout.setContentsMargins(16, 14, 16, 14)
        last_layout.setSpacing(8)
        self.last_card.setLayout(last_layout)
        
        # Импортируем ClickableLabel локально
        from email_app import ClickableLabel
        self.last_sent_label = ClickableLabel("—")
        self.last_sent_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.last_sent_label.setStyleSheet("""
            color: #1D1D1F;
            background: transparent;
            padding: 0px;
        """)
        self.last_sent_label.setWordWrap(True)
        self.last_sent_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.last_sent_label.clicked.connect(self.on_last_sent_clicked)
        last_layout.addWidget(self.last_sent_label)
        
        # Показываем дату/время последней отправки
        self.last_date_label = QLabel("—")
        self.last_date_label.setFont(QFont("Segoe UI", 11))
        self.last_date_label.setStyleSheet("color: #86868B; background: transparent; padding: 0px; margin: 0px;")
        last_layout.addWidget(self.last_date_label)
        
        right_column.addWidget(self.last_card)
        
        # Карточка "Инсайты" (как в правой колонке на макете)
        self.popular_card = QFrame()
        self.popular_card.setObjectName("popularCard")
        self.popular_card.setFixedWidth(320)
        self.popular_card.setStyleSheet("""
            QFrame#popularCard {
                background-color: rgba(255, 255, 255, 0.98);
                border-radius: 20px;
                border: 1px solid rgba(200, 200, 200, 0.2);
                padding: 0px;
            }
        """)
        popular_layout = QVBoxLayout()
        popular_layout.setContentsMargins(16, 16, 16, 16)
        popular_layout.setSpacing(10)
        self.popular_card.setLayout(popular_layout)
        
        # Заголовок "Инсайты" с иконкой лампочки
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)
        
        insights_icon = QLabel("💡")
        insights_icon.setFont(QFont("Segoe UI", 16))
        insights_icon.setStyleSheet("background: transparent;")
        header_row.addWidget(insights_icon)
        
        insights_title = QLabel(tr("insights") if tr("insights") != "insights" else "Инсайты")
        insights_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        insights_title.setStyleSheet("color: #1D1D1F; background: transparent;")
        header_row.addWidget(insights_title)
        header_row.addStretch()
        popular_layout.addLayout(header_row)
        
        # Основной инсайт: самая частая должность
        self.popular_lehrstelle_label = QLabel("—")
        self.popular_lehrstelle_label.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.popular_lehrstelle_label.setStyleSheet("""
            color: #1D1D1F;
            background: transparent;
            padding: 0px;
        """)
        self.popular_lehrstelle_label.setWordWrap(True)
        popular_layout.addWidget(self.popular_lehrstelle_label)
        
        # Подпись под основной должностью
        self.popular_label = QLabel(tr("popular_position"))
        self.popular_label.setFont(QFont("Segoe UI", 11))
        self.popular_label.setStyleSheet("color: #86868B; background: transparent; padding: 0px; margin: 0px;")
        popular_layout.addWidget(self.popular_label)
        
        # Текст "Последняя активность была X дней назад"
        self.last_activity_insight = QLabel("—")
        self.last_activity_insight.setFont(QFont("Segoe UI", 11))
        self.last_activity_insight.setStyleSheet("color: #86868B; background: transparent; padding-top: 6px;")
        self.last_activity_insight.setWordWrap(True)
        popular_layout.addWidget(self.last_activity_insight)
        
        right_column.addWidget(self.popular_card)
        
        # Контейнер для правой колонки
        right_column_widget = QWidget()
        right_column_widget.setLayout(right_column)
        main_content_layout.addWidget(right_column_widget)
        
        layout.addLayout(main_content_layout)
        
        # ВТОРИЧНЫЕ ЭЛЕМЕНТЫ: Календарь и последняя отправка
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(20)
        secondary_layout.setContentsMargins(0, 0, 0, 0)
        secondary_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Левая колонка - календарь (уменьшенный)
        self.calendar_card = QFrame()
        self.calendar_card.setObjectName("calendarCard")
        self.calendar_card.setFixedWidth(320)
        self.calendar_card.setStyleSheet("""
            QFrame#calendarCard {
                background-color: transparent;
                border-radius: 0px;
                border: none;
                padding: 0px;
            }
        """)
        calendar_layout = QVBoxLayout()
        calendar_layout.setContentsMargins(0, 0, 0, 8)
        calendar_layout.setSpacing(2)
        self.calendar_card.setLayout(calendar_layout)
        
        # Кастомный виджет календаря (уменьшенный)
        self.calendar_widget = CustomCalendarWidget()
        self.calendar_widget.setFixedSize(300, 220)  # Уменьшено
        
        calendar_layout.addWidget(self.calendar_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        secondary_layout.addWidget(self.calendar_card)
        
        # Вызываем update_calendar_display сразу после создания календаря
        QTimer.singleShot(150, self.update_calendar_display)
        
        # Правая колонка - карточка последней отправки
        right_column = QVBoxLayout()
        right_column.setSpacing(0)
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Карточка последней отправки
        self.last_card = QFrame()
        self.last_card.setObjectName("lastCard")
        self.last_card.setFixedWidth(300)
        self.last_card.setStyleSheet("""
            QFrame#lastCard {
                background-color: rgba(255, 255, 255, 1.0);
                border-radius: 20px;
                border: 1px solid rgba(200, 200, 200, 0.2);
                padding: 0px;
            }
        """)
        last_layout = QVBoxLayout()
        last_layout.setContentsMargins(16, 14, 16, 14)
        last_layout.setSpacing(8)
        self.last_card.setLayout(last_layout)
        
        # Импортируем ClickableLabel локально
        from email_app import ClickableLabel
        self.last_sent_label = ClickableLabel("—")
        self.last_sent_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        self.last_sent_label.setStyleSheet("""
            color: #1D1D1F;
            background: transparent;
            padding: 0px;
        """)
        self.last_sent_label.setWordWrap(True)
        self.last_sent_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.last_sent_label.clicked.connect(self.on_last_sent_clicked)
        last_layout.addWidget(self.last_sent_label)
        
        self.last_label = QLabel(tr("last_activity"))
        self.last_label.setFont(QFont("Segoe UI", 11))
        self.last_label.setStyleSheet("color: #86868B; background: transparent; padding: 0px; margin: 0px;")
        last_layout.addWidget(self.last_label)
        
        right_column.addWidget(self.last_card)
        
        # Контейнер для правой колонки
        right_column_widget = QWidget()
        right_column_widget.setLayout(right_column)
        secondary_layout.addWidget(right_column_widget)
        
        layout.addStretch()
    
    def create_health_tracker(self, title, value, icon_type):
        """Создает трекер в стиле Apple Health с использованием нового цвета"""
        colors = get_app_colors()
        # Чередуем цвета для разнообразия
        color_map = {
            "applications": colors['accent'],
            "average": colors['accent_teal'],
            "month": colors['accent'],
            "week": colors['accent_teal'],
            "days": colors['accent'],
            "activity": colors['accent_teal']
        }
        accent_color = color_map.get(icon_type, colors['accent'])
        
        tracker_card = QFrame()
        tracker_card.setObjectName("healthTracker")
        tracker_card.setStyleSheet(f"""
            QFrame#healthTracker {{
                background-color: rgba(255, 255, 255, 1.0);
                border-radius: 18px;
                border: 1px solid rgba(200, 200, 200, 0.2);
                padding: 0px;
            }}
        """)
        tracker_layout = QVBoxLayout()
        tracker_layout.setContentsMargins(14, 14, 14, 14)
        tracker_layout.setSpacing(8)
        tracker_card.setLayout(tracker_layout)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11))
        title_label.setStyleSheet(f"color: #86868B; background: transparent;")
        tracker_layout.addWidget(title_label)
        
        # Значение с цветным акцентом
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 24, QFont.Weight.DemiBold))
        value_label.setStyleSheet(f"color: {accent_color}; background: transparent;")
        value_label.setObjectName(f"trackerValue_{icon_type}")
        tracker_layout.addWidget(value_label)
        
        return tracker_card
    
    def create_stat_card(self, title, value, icon_type, subtitle=""):
        """Создает унифицированную карточку статистики с иконкой"""
        # Цветовая система: фиолетовый только для действий, серый для вторичного
        accent_color_map = {
            "applications": "#4A90E2",  # Синий для объема
            # Для "В среднем в день" иконку делаем монохромной (серой),
            # а цвет числа будем управлять отдельно при обновлении статистики.
            "average": "#4B5563",
            "month": "#4A90E2",         # Синий для объема
            "week": "#86868B",          # Серый для вторичного (последняя активность)
        }
        accent_color = accent_color_map.get(icon_type, "#86868B")
        
        tracker_card = QFrame()
        tracker_card.setObjectName("statCard")
        tracker_card.setFixedHeight(135)  # Чуть меньше по вертикали
        tracker_card.setStyleSheet("""
            QFrame#statCard {
                background-color: rgba(255, 255, 255, 1.0);
                border-radius: 14px;
                border: none;
                padding: 0px;
            }
        """)
        
        tracker_layout = QVBoxLayout()
        tracker_layout.setContentsMargins(14, 50, 14, 14)  # Симметричные отступы
        tracker_layout.setSpacing(6)  # Увеличен spacing для равномерности
        tracker_card.setLayout(tracker_layout)
        
        # Иконка - абсолютно позиционированная (симметрично)
        icon_top_margin = 14
        icon_left_margin = 14
        
        if icon_type == "applications":
            icon_widget = ClipboardIconWidget(tracker_card, accent_color)
            icon_widget.move(icon_left_margin, icon_top_margin)
            icon_widget.raise_()
        elif icon_type == "month":
            icon_widget = CalendarIconWidget(tracker_card, accent_color)
            icon_widget.move(icon_left_margin, icon_top_margin)
            icon_widget.raise_()
        else:
            icon_label = QLabel(tracker_card)
            icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            if icon_type == "average":
                icon_label.setText("✓")
                icon_label.setFixedSize(40, 40)
                icon_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
                # Монохромная иконка: всегда серый цвет
                icon_label.setStyleSheet("color: #4B5563; background: transparent;")
            elif icon_type == "week":
                icon_label.setText("★")
                icon_label.setFixedSize(40, 40)
                icon_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
                icon_label.setStyleSheet(f"color: {accent_color}; background: transparent;")
            
            icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            icon_label.move(icon_left_margin, icon_top_margin)
            icon_label.raise_()
        
        # Значение - симметрично и равномерно
        value_container = QHBoxLayout()
        value_container.setContentsMargins(0, 0, 0, 0)
        value_container.setSpacing(4)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Inter", 24, QFont.Weight.Bold))  # Немного уменьшено для симметрии
        value_label.setStyleSheet(f"color: {accent_color}; background: transparent; padding: 0px;")
        value_label.setObjectName(f"trackerValue_{icon_type}")
        value_label.setWordWrap(False)
        value_container.addWidget(value_label)
        
        # Иконка для среднего в день (будет обновляться динамически) - справа от главной цифры
        if icon_type == "average":
            # Создаем иконку (монохромную стрелку вверх или вниз)
            avg_icon_label = QLabel("")
            avg_icon_label.setFixedSize(24, 24)
            avg_icon_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            avg_icon_label.setStyleSheet(f"color: {accent_color}; background: transparent;")
            avg_icon_label.setObjectName("avgIconLabel")
            avg_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_container.addWidget(avg_icon_label)
        
        tracker_layout.addLayout(value_container)
        
        # Заголовок (только если title не пустой)
        if title:
            title_label = QLabel(title)
            title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))  # Немного увеличен для читаемости
            title_label.setStyleSheet("color: #86868B; background: transparent; padding: 0px;")  # Серый для вторичного
            # Для "applications" типа делаем subtitle в одну строку с title
            if icon_type == "applications" and subtitle:
                title_label.setText(f"{title} {subtitle}")
                title_label.setWordWrap(False)  # В одну строку
            else:
                title_label.setWordWrap(True)
            title_label.setMinimumHeight(16)  # Минимальная высота для симметрии
            tracker_layout.addWidget(title_label)
        
        # Подзаголовок (если есть) - создаем пустой label для динамического обновления
        if (subtitle or icon_type == "average") and not (icon_type == "applications" and subtitle):
            subtitle_label = QLabel(subtitle if subtitle else "")
            subtitle_label.setFont(QFont("Segoe UI", 9))  # Немного увеличен
            subtitle_label.setStyleSheet("color: #86868B; background: transparent; padding: 0px;")
            subtitle_label.setObjectName("")  # Пустое имя для поиска
            subtitle_label.setMinimumHeight(14)  # Минимальная высота для симметрии
            tracker_layout.addWidget(subtitle_label)
        
        tracker_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Убираем ограничение ширины для равномерного распределения
        
        return tracker_card
    
    def load_statistics(self):
        """Загружает статистику пользователя"""
        # Импортируем функции локально для избежания циклических зависимостей
        from email_app import get_email_history, get_email_stats_by_date, get_most_popular_lehrstelle
        
        history = get_email_history()
        
        # Загружаем статистику для календаря (оптимизировано с кешированием)
        self.calendar_stats = get_email_stats_by_date()
        # Обновляем отображение календаря только если нужно
        if not hasattr(self, '_last_calendar_update') or \
           (datetime.now() - self._last_calendar_update).total_seconds() > 60:
            self.update_calendar_display()
            self._last_calendar_update = datetime.now()
        
        total_count = len(history)
        
        # Обновляем карточку "Сегодня"
        today_py = datetime.now().date()
        today_count = self.calendar_stats.get(today_py, 0)
        if hasattr(self, 'today_count_label'):
            self.today_count_label.setText(str(today_count))
        if hasattr(self, 'today_header_label'):
            # Правильная форма слова "заявка сегодня" / "заявки сегодня"
            if today_count == 1:
                self.today_header_label.setText("заявка сегодня")
            elif today_count in [2, 3, 4]:
                self.today_header_label.setText("заявки сегодня")
            else:
                self.today_header_label.setText("заявок сегодня")
            # Обновляем позицию текста (теперь он в goal_header_row, не нужно move)
        
        # Обновляем прогресс-бар недели с цветами и эмоциональным статусом
        if hasattr(self, 'week_progress'):
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            # Считаем количество отправок за текущую неделю из истории
            week_count = 0
            for h in history:
                try:
                    dt = datetime.strptime(h[1], '%Y-%m-%d %H:%M:%S')
                    if dt.date() >= week_start:
                        week_count += 1
                except:
                    pass
            
            week_count = min(week_count, 7)
            self.week_progress.setValue(week_count)
            
            # Обновляем текст внутри прогресс-бара
            if hasattr(self, 'progress_with_text'):
                self.progress_with_text.setText(f"{week_count}/7 {tr('applications')}")
                self.progress_with_text.setValue(week_count)
            
            # Эмоциональный статус и текст "Осталось X заявок · Y дней" (темно-фиолетовый, числа жирным)
            remaining = 7 - week_count
            days_until_sunday = 7 - today.weekday() - 1  # Дней до конца недели (воскресенье)
            if days_until_sunday < 0:
                days_until_sunday = 0
            # Сколько в среднем нужно в день до конца недели
            daily_needed = float(remaining) / days_until_sunday if days_until_sunday > 0 else float(remaining)
            # Определяем статус цели (green / yellow / red)
            status_color = "#16A34A"  # green
            if daily_needed > 2.5:
                status_color = "#DC2626"  # red
            elif daily_needed > 1.5:
                status_color = "#EA580C"  # yellow

            # Подсвечиваем карточку цели недели в зависимости от статуса
            if hasattr(self, "week_goal_card"):
                self.week_goal_card.setStyleSheet(f"""
                    QFrame#weekGoalCard {{
                        background-color: rgba(255, 255, 255, 1.0);
                        border-radius: 16px;
                        border: 1px solid {status_color}33;
                        padding: 0px;
                    }}
                """)
            
            if hasattr(self, 'week_status_label'):
                # Текст "Осталось X заявок · Y дней" с жирными числами
                if remaining > 0:
                    # Используем HTML для жирных чисел
                    remaining_text = tr("remaining_applications").format(count=remaining)
                    days_text = tr("days_left").format(count=days_until_sunday)
                    # Заменяем числа на жирные
                    import re
                    remaining_text = re.sub(r'(\d+)', r'<b>\1</b>', remaining_text)
                    days_text = re.sub(r'(\d+)', r'<b>\1</b>', days_text)
                    # Добавляем подсказку по темпу (≈ N заявок в день)
                    pace_hint = ""
                    if daily_needed > 0:
                        pace_hint = f" · <span style='color:{status_color};'><b>~{daily_needed:.1f}</b> заявок в день</span>"
                    status_text = f"{remaining_text} · {days_text}{pace_hint}"
                    self.week_status_label.setText(status_text)
                else:
                    status_text = "🎉 " + tr("excellent_pace")
                    self.week_status_label.setText(status_text)
        
        # Обновляем трекеры в стиле Apple Health
        if hasattr(self, 'total_apps_tracker'):
            value_label = self.total_apps_tracker.findChild(QLabel, "trackerValue_applications")
            if value_label:
                value_label.setText(str(total_count))
        
        # Среднее в день - с сравнением с прошлой неделей (стрелка)
        if history and hasattr(self, 'avg_per_day_tracker'):
            if len(history) > 0:
                try:
                    first_date = datetime.strptime(history[-1][1], '%Y-%m-%d %H:%M:%S').date()
                    today_date = datetime.now().date()
                    days_diff = (today_date - first_date).days + 1
                    if days_diff > 0:
                        avg = total_count / days_diff
                    else:
                        avg = total_count if total_count > 0 else 0.0
                    
                    value_label = self.avg_per_day_tracker.findChild(QLabel, "trackerValue_average")
                    if value_label:
                        # Цвет числа зависит от тренда: зелёный / оранжевый / красный
                        trend_color = "#16A34A"  # green
                        # diff посчитается ниже, но базово показываем значением по умолчанию
                        value_label.setText(f"{avg:.1f}")
                    
                    # Сравнение с прошлой неделей
                    today = datetime.now().date()
                    week_start = today - timedelta(days=today.weekday())
                    last_week_start = week_start - timedelta(days=7)
                    last_week_end = week_start - timedelta(days=1)
                    
                    # Считаем среднее за прошлую неделю
                    last_week_count = 0
                    for h in history:
                        try:
                            dt = datetime.strptime(h[1], '%Y-%m-%d %H:%M:%S')
                            if last_week_start <= dt.date() <= last_week_end:
                                last_week_count += 1
                        except:
                            pass
                    
                    last_week_avg = last_week_count / 7 if last_week_count > 0 else 0.0
                    
                    # Обновляем иконку и подпись справа от главной цифры
                    diff = avg - last_week_avg
                    icon_label = self.avg_per_day_tracker.findChild(QLabel, "avgIconLabel")
                    # Рассчитываем относительное изменение в %
                    change_percent = 0.0
                    if last_week_avg > 0:
                        change_percent = (avg - last_week_avg) / last_week_avg * 100.0

                    # Определяем цвет тренда и текст сравнения
                    comparison_text = ""
                    if change_percent > 5:
                        trend_color = "#16A34A"  # green
                        comparison_text = f"на {abs(change_percent):.0f}% больше прошлой недели"
                    elif change_percent < -5:
                        trend_color = "#DC2626"  # red
                        comparison_text = f"на {abs(change_percent):.0f}% меньше прошлой недели"
                    else:
                        trend_color = "#F97316"  # neutral / orange
                        comparison_text = "примерно как на прошлой неделе"

                    # Обновляем цвет числа
                    if value_label:
                        value_label.setStyleSheet(f"color: {trend_color}; background: transparent; padding: 0px;")

                    if icon_label:
                        # Монохромная иконка: только форма стрелки меняется, цвет всегда серый
                        if diff > 0:
                            icon_label.setText("↑")
                        elif diff < 0:
                            icon_label.setText("↓")
                        else:
                            icon_label.setText("")
                        icon_label.setStyleSheet("color: #4B5563; background: transparent;")
                    
                    # Обновляем подзаголовок снизу текстом сравнения
                    subtitle_labels = self.avg_per_day_tracker.findChildren(QLabel)
                    for label in subtitle_labels:
                        # Ищем label без objectName (подзаголовок)
                        if not label.objectName() and label != icon_label:
                            label.setText(comparison_text)
                            break
                            
                except Exception as e:
                    print(f"Ошибка расчета среднего в день: {e}")
        
        # В этом месяце - оптимизировано через calendar_stats
        if hasattr(self, 'this_month_tracker'):
            today = datetime.now()
            month_count = sum(count for date_key, count in self.calendar_stats.items() 
                            if date_key.month == today.month and date_key.year == today.year)
            value_label = self.this_month_tracker.findChild(QLabel, "trackerValue_month")
            if value_label:
                value_label.setText(str(month_count))
        
        # Карточки последней активности убраны из общей статистики (они справа)
        
        if history:
            # Формат: (id, sent_at, recipient_email, lehrstelle)
            # history[0] - последняя отправка (отсортировано по DESC)
            entry_id, last_sent_at, recipient_email, lehrstelle = history[0]
            self.last_sent_at = last_sent_at
            try:
                dt = datetime.strptime(last_sent_at, '%Y-%m-%d %H:%M:%S')
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                # Показываем название должности в виджете последней отправки - обновляем все виджеты
                from email_app import ClickableLabel
                # Находим все ClickableLabel в last_card виджетах
                last_cards = self.findChildren(QFrame, "lastCard")
                for last_card in last_cards:
                    # Ищем last_sent_label внутри каждого last_card
                    last_sent_labels = last_card.findChildren(ClickableLabel)
                    for label in last_sent_labels:
                        if label.text() == "—" or label.text() == tr("no_sent") or label.text() != lehrstelle:
                            label.setText(lehrstelle if lehrstelle else tr("no_sent"))
                            label.setStyleSheet("""
                                color: #1D1D1F;
                                background: transparent;
                                padding: 0px;
                            """)
                            label.setCursor(Qt.CursorShape.PointingHandCursor)
                            label.setToolTip(tr("click_to_go_to_application"))
                
                # Также обновляем self.last_sent_label если он существует
                if hasattr(self, 'last_sent_label'):
                    self.last_sent_label.setText(lehrstelle if lehrstelle else tr("no_sent"))
                    self.last_sent_label.setStyleSheet("""
                        color: #1D1D1F;
                        background: transparent;
                        padding: 0px;
                    """)
                    self.last_sent_label.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.last_sent_label.setToolTip(tr("click_to_go_to_application"))
                
                # Показываем дату/время отдельно - обновляем все last_date_label виджеты
                last_date_labels = self.findChildren(QLabel)
                for label in last_date_labels:
                    # Проверяем, что это last_date_label (по тексту или по родителю)
                    if label.parent() and hasattr(label.parent(), 'objectName') and label.parent().objectName() == "lastCard":
                        # Проверяем, что это не last_sent_label и не last_label
                        if label.text() == "—" or (label.text() and ("." in label.text() or ":" in label.text())):
                            label.setText(formatted_date)
                # Также обновляем self.last_date_label если он существует
                if hasattr(self, 'last_date_label'):
                    self.last_date_label.setText(formatted_date)
            except Exception as e:
                print(f"Ошибка обновления последней активности: {e}")
                # Обновляем все виджеты даже при ошибке
                from email_app import ClickableLabel
                last_cards = self.findChildren(QFrame, "lastCard")
                for last_card in last_cards:
                    last_sent_labels = last_card.findChildren(ClickableLabel)
                    for label in last_sent_labels:
                        label.setText(lehrstelle if lehrstelle else tr("no_sent"))
                        label.setStyleSheet("""
                            color: #1D1D1F;
                            background: transparent;
                            padding: 0px;
                        """)
                        label.setCursor(Qt.CursorShape.PointingHandCursor)
                        label.setToolTip(tr("click_to_go_to_application"))
                if hasattr(self, 'last_sent_label'):
                    self.last_sent_label.setText(lehrstelle if lehrstelle else tr("no_sent"))
                    self.last_sent_label.setStyleSheet("""
                        color: #1D1D1F;
                        background: transparent;
                        padding: 0px;
                    """)
                    self.last_sent_label.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.last_sent_label.setToolTip(tr("click_to_go_to_application"))
                # Обновляем все last_date_label виджеты
                last_date_labels = self.findChildren(QLabel)
                for label in last_date_labels:
                    if label.parent() and hasattr(label.parent(), 'objectName') and label.parent().objectName() == "lastCard":
                        if label.text() == "—" or (label.text() and ("." in label.text() or ":" in label.text())):
                            label.setText(last_sent_at if last_sent_at else "—")
                if hasattr(self, 'last_date_label'):
                    self.last_date_label.setText(last_sent_at if last_sent_at else "—")
                # Обновляем инсайт "Последняя активность была X дней назад"
                if hasattr(self, "last_activity_insight"):
                    days_diff = (datetime.now().date() - dt.date()).days
                    if days_diff == 0:
                        text = tr("last_activity_today") if tr("last_activity_today") != "last_activity_today" else "Последняя активность сегодня"
                    elif days_diff == 1:
                        text = tr("last_activity_yesterday") if tr("last_activity_yesterday") != "last_activity_yesterday" else "Последняя активность была вчера"
                    else:
                        text = tr("last_activity_days_ago").format(count=days_diff) \
                            if tr("last_activity_days_ago") != "last_activity_days_ago" \
                            else f"Последняя активность была {days_diff} дней назад"
                    self.last_activity_insight.setText(text)
        else:
            # Обновляем все виджеты при отсутствии истории
            from email_app import ClickableLabel
            last_cards = self.findChildren(QFrame, "lastCard")
            for last_card in last_cards:
                last_sent_labels = last_card.findChildren(ClickableLabel)
                for label in last_sent_labels:
                    label.setText(tr("no_sent"))
                    label.setCursor(Qt.CursorShape.ArrowCursor)
                    label.setToolTip("")
            if hasattr(self, 'last_sent_label'):
                self.last_sent_label.setText(tr("no_sent"))
                self.last_sent_at = None
                self.last_sent_label.setCursor(Qt.CursorShape.ArrowCursor)
                self.last_sent_label.setToolTip("")
            # Обновляем все last_date_label виджеты
            last_date_labels = self.findChildren(QLabel)
            for label in last_date_labels:
                if label.parent() and hasattr(label.parent(), 'objectName') and label.parent().objectName() == "lastCard":
                    if label.text() == "—" or (label.text() and ("." in label.text() or ":" in label.text())):
                        label.setText("—")
            if hasattr(self, 'last_date_label'):
                self.last_date_label.setText("—")
            if hasattr(self, "last_activity_insight"):
                self.last_activity_insight.setText(
                    tr("no_activity_yet") if tr("no_activity_yet") != "no_activity_yet" else "Активность пока не зафиксирована"
                )
        
        # Обновляем популярную вакансию
        popular_lehrstelle, popular_count = get_most_popular_lehrstelle()
        if hasattr(self, 'popular_lehrstelle_label'):
            if popular_lehrstelle:
                # Название должности крупным шрифтом, а "(X раз)" справа, чуть больше
                main_text = f"{popular_lehrstelle}"
                count_text = f"({popular_count} {tr('times')})"
                # Используем HTML для разного стиля - в одну строку
                self.popular_lehrstelle_label.setText(f"{main_text} <span style='color: #B0B0B0; font-size: 13px;'>{count_text}</span>")
                self.popular_lehrstelle_label.setTextFormat(Qt.TextFormat.RichText)
            else:
                self.popular_lehrstelle_label.setText(tr("no_data"))
                self.popular_lehrstelle_label.setTextFormat(Qt.TextFormat.PlainText)
    
    def eventFilter(self, obj, event):
        """Обработчик событий"""
        return super().eventFilter(obj, event)
    
    def update_calendar_display(self):
        """Обновляет отображение календаря с отметками дат отправок"""
        if not self.is_active:
            return
        if not hasattr(self, 'calendar_stats'):
            from email_app import get_email_stats_by_date
            self.calendar_stats = get_email_stats_by_date()
        
        # Проверяем, изменился ли день или месяц
        if hasattr(self, 'calendar_widget'):
            self.calendar_widget.check_and_update()
        
        # Устанавливаем статистику для календаря
        if hasattr(self, 'calendar_widget'):
            self.calendar_widget.set_calendar_stats(self.calendar_stats)
        
        # Количество отправленных сегодня теперь обновляется в load_statistics через today_count_label
    
    def on_last_sent_clicked(self):
        """Обработчик клика по дате последней отправки"""
        if self.last_sent_at and self.main_window:
            self.main_window.switch_to_history_and_highlight(self.last_sent_at)
    
    def update_texts(self):
        """Обновляет тексты при смене языка"""
        # Обновляем заголовок
        if hasattr(self, 'title_label'):
            self.title_label.setText(tr("statistics"))
        
        # Обновляем заголовок секции трекеров
        if hasattr(self, 'trackers_title'):
            self.trackers_title.setText(tr("general_stats"))
        
        # Обновляем метки карточек
        if hasattr(self, 'last_label'):
            self.last_label.setText(tr("last_activity"))
        if hasattr(self, 'popular_label'):
            self.popular_label.setText(tr("popular_position"))
        
        # Обновляем заголовки трекеров
        if hasattr(self, 'total_apps_tracker'):
            trackers = [
                (self.total_apps_tracker, "total_sent_label", "total_sent_all_time"),
                (self.avg_per_day_tracker, "avg_per_day", ""),
                (self.this_month_tracker, "this_month", ""),
                (self.last_sent_tracker, "last_activity", ""),
            ]
            for tracker, tr_key, subtitle_key in trackers:
                if tracker:
                    labels = tracker.findChildren(QLabel)
                    for label in labels:
                        obj_name = label.objectName()
                        if not obj_name.startswith("trackerValue_") and obj_name != "avgIconLabel":
                            # Это заголовок или подзаголовок
                            if subtitle_key and subtitle_key in label.text():
                                label.setText(tr(subtitle_key))
                            elif tr_key:
                                # Проверяем, является ли это заголовком (не числом)
                                try:
                                    float(label.text())
                                except:
                                    if label.text() in [tr("total_sent_label"), tr("avg_per_day"), tr("this_month"), tr("last_activity"), tr("total_sent_all_time")] or not label.text().isdigit():
                                        label.setText(tr(tr_key))
        
        # Обновляем календарь при смене языка
        if hasattr(self, 'calendar_widget'):
            self.calendar_widget.update_language()
        self.update_calendar_display()
        
        # Перезагружаем статистику для обновления всех элементов
        if not hasattr(self, '_last_stats_update') or \
           (datetime.now() - self._last_stats_update).total_seconds() > 5:
            self.load_statistics()
            self._last_stats_update = datetime.now()





