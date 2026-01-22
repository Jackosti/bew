"""
Модуль настроек приложения
Содержит SettingsDialog и SettingsSaveNotification
"""

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, QPointF, QEvent, QLineF, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush, QPen, QLinearGradient, QIcon, QPixmap
from PyQt6.QtWidgets import QGraphicsColorizeEffect

from email_app import t, tr, get_current_language, set_language, get_localization_manager

# Импортируем функции из email_app (избегаем циклического импорта)
import email_app


class LanguageItemDelegate(QStyledItemDelegate):
    """Кастомный делегат для элементов языка без разделителей"""
    def paint(self, painter, option, index):
        # Убираем стандартную отрисовку разделителей
        option.showDecorationSelected = False
        # Убираем границы
        if hasattr(option, 'rect'):
            # Рисуем фон без границ
            # В PyQt6 используем правильные константы состояния
            from PyQt6.QtWidgets import QStyle
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QColor("#E8E0F5"))
            elif option.state & QStyle.StateFlag.State_MouseOver:
                painter.fillRect(option.rect, QColor("#F5F0FF"))
            else:
                painter.fillRect(option.rect, QColor("#FFFFFF"))
        
        # Рисуем текст без разделителей
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            painter.setPen(QColor("#2D1B3D"))
            painter.setFont(QFont("Segoe UI", 14))
            painter.drawText(option.rect.adjusted(16, 0, -16, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
    
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), size.height())


class LogoutConfirmDialog(QDialog):
    """Диалог подтверждения выхода в лиловой теме"""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.settings_dialog = parent  # Сохраняем ссылку на настройки, если они открыты
        self.overlay = None
        self.settings_overlay = None  # Overlay для затемнения окна настроек
        self.setup_ui()
    
    def setup_ui(self):
        """Создает интерфейс диалога"""
        self.setWindowTitle(tr("logout"))
        # Растягиваем диалог по диагонали
        self.setFixedSize(400, 180)
        # Диалог поверх всех окон приложения, но не поверх системных окон
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Основной контейнер
        container = QFrame()
        container.setObjectName("logoutDialogContainer")
        container.setStyleSheet("""
            QFrame#logoutDialogContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(240, 232, 250, 0.98),
                    stop:1 rgba(248, 242, 255, 0.98));
                border-radius: 16px;
                border: 2px solid rgba(156, 137, 184, 0.3);
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        container.setLayout(layout)
        
        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        
        title = QLabel(tr("logout"))
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #6C5A8B; background: transparent;")
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
        layout.addLayout(header_layout)
        
        # Текст подтверждения (меньше, чтобы помещался в одну строку)
        confirm_label = QLabel(tr("logout_confirm"))
        confirm_label.setWordWrap(False)  # Отключаем перенос текста
        confirm_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        confirm_label.setFont(QFont("Inter", 11))  # Уменьшаем размер шрифта
        confirm_label.setStyleSheet("""
            QLabel {
                color: #6C5A8B;
                background: transparent;
            }
        """)
        layout.addWidget(confirm_label)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setFixedHeight(44)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 182, 226, 0.6);
                color: #6C5A8B;
                border: 1px solid rgba(156, 137, 184, 0.4);
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(200, 182, 226, 0.8);
            }
        """)
        buttons_layout.addWidget(cancel_btn)
        
        logout_btn = QPushButton(tr("logout"))
        logout_btn.setFixedHeight(44)
        logout_btn.setMinimumWidth(120)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.accept)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9B8AB8,
                    stop:1 #B5A5D0);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #AB9AC8,
                    stop:1 #C5B5E0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B7AA8,
                    stop:1 #A595C0);
            }
        """)
        buttons_layout.addWidget(logout_btn)
        
        layout.addLayout(buttons_layout)
        
        # Основной layout для диалога
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container)
        self.setLayout(main_layout)
    
    def showEvent(self, event):
        """Создает overlay и центрирует диалог при показе"""
        super().showEvent(event)
        # Overlay диалога выхода должен затемнять и главное окно, и окно настроек
        # Если настройки открыты, создаем overlay на главном окне поверх overlay настроек
        # и также затемняем само окно настроек
        if self.main_window:
            # Удаляем старый overlay если он есть
            self._remove_overlay()
            
            # Создаем overlay на главном окне для затемнения всего приложения
            # Этот overlay будет поверх overlay настроек (если они открыты)
            self.overlay = QFrame(self.main_window)
            self.overlay.setGeometry(0, 0, self.main_window.width(), self.main_window.height())
            # Если настройки открыты: overlay настроек (0.7) уже затемняет главное окно,
            # наш overlay добавит дополнительное затемнение (0.3), создавая полное затемнение главного окна
            # Если настройки не открыты: только overlay диалога (0.7) для достаточного затемнения
            overlay_alpha = 0.3 if self.settings_dialog else 0.7
            self.overlay.setStyleSheet(f"background-color: rgba(0, 0, 0, {overlay_alpha});")
            self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            
            def close_on_overlay_click(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.reject()
            
            self.overlay.mousePressEvent = close_on_overlay_click
            self.overlay.show()
            self.overlay.raise_()
            
            # Если настройки открыты, также затемняем само окно настроек
            # Используем контейнер настроек для overlay, чтобы покрыть все окно без черных квадратиков
            if self.settings_dialog and hasattr(self.settings_dialog, 'container'):
                # Создаем overlay на контейнере настроек, чтобы покрыть все окно
                # Контейнер уже имеет правильные закругленные углы и покрывает все окно
                container = self.settings_dialog.container
                self.settings_overlay = QFrame(container)
                # Используем геометрию контейнера, чтобы покрыть все окно
                self.settings_overlay.setGeometry(0, 0, container.width(), container.height())
                # Затемняем окно настроек отдельным overlay с теми же закругленными углами, что и контейнер
                self.settings_overlay.setStyleSheet("""
                    background-color: rgba(0, 0, 0, 0.7);
                    border-radius: 28px;
                """)
                self.settings_overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
                self.settings_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                
                def close_on_settings_overlay_click(e):
                    if e.button() == Qt.MouseButton.LeftButton:
                        self.reject()
                
                self.settings_overlay.mousePressEvent = close_on_settings_overlay_click
                self.settings_overlay.show()
                self.settings_overlay.raise_()
            else:
                self.settings_overlay = None
            
            # Центрируем диалог относительно главного окна
            parent_geometry = self.main_window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
            
            # Поднимаем диалог поверх всех overlay'ев
            self.raise_()
            self.activateWindow()
    
    def closeEvent(self, event):
        """Удаляет overlay при закрытии"""
        self._remove_overlay()
        super().closeEvent(event)
    
    def reject(self):
        """Отменяет диалог и удаляет overlay"""
        self._remove_overlay()
        super().reject()
    
    def accept(self):
        """Принимает диалог и удаляет overlay"""
        self._remove_overlay()
        super().accept()
    
    def _remove_overlay(self):
        """Удаляет overlay"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
        
        # Удаляем overlay окна настроек, если он есть
        if self.settings_overlay:
            try:
                self.settings_overlay.hide()
                self.settings_overlay.deleteLater()
            except RuntimeError:
                pass
            self.settings_overlay = None


class ThemePreviewDialog(QDialog):
    """Диалог предпросмотра темы отключен."""
    def __init__(self, theme_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("theme_preview"))
        self.setFixedSize(520, 220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel(tr("theme_preview"))
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #6C4A8B; background: transparent;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Функция тем отключена"), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()


class ThemePreviewWidget(QWidget):
    """
    Theme preview widget - uses the EXACT same theme colors as real theme.
    This ensures preview matches exactly what user will see.
    Uses paintEvent to render preview, but uses theme colors from ThemeManager.
    """
    def __init__(self, theme_id, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self.setMinimumHeight(500)
        self.setMinimumWidth(900)
    
    def paintEvent(self, event):
        """Отрисовывает предпросмотр темы - мини-версию приложения"""
        return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        colors = {}
        
        # Фон всего предпросмотра
        grad = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomRight()))
        grad.setColorAt(0, QColor(colors['main_window_bg_start']))
        grad.setColorAt(0.5, QColor(colors['main_window_bg_mid']))
        grad.setColorAt(1, QColor(colors['main_window_bg_end']))
        painter.fillRect(rect, grad)
        
        # Сайдбар (левая панель)
        sidebar_width = rect.width() * 0.25
        sidebar_rect = QRect(0, 0, int(sidebar_width), rect.height())
        sidebar_grad = QLinearGradient(QPointF(sidebar_rect.topLeft()), QPointF(sidebar_rect.bottomLeft()))
        sidebar_grad.setColorAt(0, QColor(colors['sidebar_bg_start']))
        sidebar_grad.setColorAt(1, QColor(colors['sidebar_bg_end']))
        painter.fillRect(sidebar_rect, sidebar_grad)
        
        # Разделитель сайдбара
        divider_rect = QRect(int(sidebar_width - 1), 0, 1, rect.height())
        painter.fillRect(divider_rect, QColor(colors['sidebar_border']))
        
        # Дата и время в сайдбаре
        date_y = 30
        painter.setPen(QPen(QColor(colors['sidebar_text'])))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(20, date_y, int(sidebar_width - 40), 20, 
                        Qt.AlignmentFlag.AlignLeft, "Вторник")
        painter.drawText(20, date_y + 20, int(sidebar_width - 40), 20,
                        Qt.AlignmentFlag.AlignLeft, "6 января")
        painter.drawText(20, date_y + 40, int(sidebar_width - 40), 20,
                        Qt.AlignmentFlag.AlignLeft, "18:25")
        
        # Навигационные кнопки в сайдбаре
        nav_y = date_y + 80
        nav_items = [
            ("Профиль", True),  # Активный
            ("Друзья", False),
            ("Статистика", False),
            ("Письма", False),
            ("История", False),
            ("Достижения", False)
        ]
        
        for i, (name, is_active) in enumerate(nav_items):
            nav_rect = QRect(10, nav_y + i * 45, int(sidebar_width - 20), 40)
            
            if is_active:
                # Активный элемент
                active_bg = QColor(colors['nav_button_active_bg'])
                painter.fillRect(nav_rect, active_bg)
                painter.setPen(QPen(QColor(colors['sidebar_text_hover'])))
            else:
                painter.setPen(QPen(QColor(colors['sidebar_text'])))
            
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium if is_active else QFont.Weight.Normal))
            painter.drawText(nav_rect.adjusted(15, 0, -15, 0),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        
        # Настройки внизу сайдбара
        settings_y = rect.height() - 50
        settings_rect = QRect(10, settings_y, int(sidebar_width - 20), 40)
        painter.setPen(QPen(QColor(colors['sidebar_text'])))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(settings_rect.adjusted(15, 0, -15, 0),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Настройки")
        
        # Основная область (профиль)
        main_x = int(sidebar_width)
        main_rect = QRect(main_x, 0, int(rect.width() - sidebar_width), rect.height())
        
        # Заголовок профиля
        header_y = 50
        painter.setPen(QPen(QColor(colors['text_primary'])))
        painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        painter.drawText(main_x + 60, header_y, int(rect.width() - sidebar_width - 120), 40,
                        Qt.AlignmentFlag.AlignLeft, "Профиль")
        
        painter.setPen(QPen(QColor(colors['text_secondary'])))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(main_x + 60, header_y + 40, int(rect.width() - sidebar_width - 120), 25,
                        Qt.AlignmentFlag.AlignLeft, "Управление вашим аккаунтом и настройками")
        
        # Карточка профиля
        card_y = header_y + 90
        card_width = int(rect.width() - sidebar_width - 120)
        card_height = 200
        card_rect = QRect(main_x + 60, card_y, card_width, card_height)
        
        # Фон карточки
        card_bg = QColor(colors['card_bg'])
        painter.setBrush(QBrush(card_bg))
        painter.setPen(QPen(QColor(colors['card_border']), 1))
        painter.drawRoundedRect(card_rect, 16, 16)
        
        # Аватар
        avatar_x = main_x + 80
        avatar_y = card_y + 30
        avatar_size = 80
        avatar_rect = QRect(avatar_x, avatar_y, avatar_size, avatar_size)
        avatar_grad = QLinearGradient(QPointF(avatar_rect.topLeft()), QPointF(avatar_rect.bottomRight()))
        avatar_grad.setColorAt(0, QColor(colors['accent']))
        avatar_grad.setColorAt(1, QColor(colors['accent_alt']))
        painter.setBrush(QBrush(avatar_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(avatar_rect)
        
        # Буква в аватаре
        painter.setPen(QPen(QColor(colors['button_primary_text'])))
        painter.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        painter.drawText(avatar_rect, Qt.AlignmentFlag.AlignCenter, "K")
        
        # Имя пользователя
        name_x = avatar_x + avatar_size + 20
        name_y = avatar_y
        painter.setPen(QPen(QColor(colors['text_primary'])))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(name_x, name_y, card_width - (name_x - main_x - 60) - 20, 30,
                        Qt.AlignmentFlag.AlignLeft, "kostriol")
        
        # Статус онлайн
        status_y = name_y + 30
        painter.setBrush(QBrush(QColor(colors['success_text'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(name_x, status_y, 8, 8)
        painter.setPen(QPen(QColor(colors['text_secondary'])))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(name_x + 15, status_y - 2, 100, 20,
                        Qt.AlignmentFlag.AlignLeft, "В сети")
        
        # О себе
        about_y = status_y + 30
        painter.setPen(QPen(QColor(colors['text_secondary'])))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.drawText(name_x, about_y, card_width - (name_x - main_x - 60) - 20, 20,
                        Qt.AlignmentFlag.AlignLeft, "О себе")
        
        painter.setPen(QPen(QColor(colors['text_primary'])))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(name_x, about_y + 20, card_width - (name_x - main_x - 60) - 20, 30,
                        Qt.AlignmentFlag.AlignLeft, "teamfachigkeit")
        
        # Статистика
        stats_y = card_y + card_height + 30
        stats_width = card_width
        stats_height = 100
        stats_rect = QRect(main_x + 60, stats_y, stats_width, stats_height)
        
        # Три колонки статистики
        stat_width = stats_width // 3
        stat_items = [
            ("Всего отправок", "5"),
            ("Достижения", "5/10"),
            ("Дней в приложении", "39")
        ]
        
        for i, (label, value) in enumerate(stat_items):
            stat_x = main_x + 60 + i * stat_width
            stat_rect = QRect(stat_x, stats_y, stat_width - 20, stats_height)
            
            # Значение
            painter.setPen(QPen(QColor(colors['text_primary'])))
            painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            painter.drawText(stat_rect.adjusted(0, 0, 0, -40),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, value)
            
            # Метка
            painter.setPen(QPen(QColor(colors['text_secondary'])))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(stat_rect.adjusted(0, 50, 0, 0),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, label)
        
        # Декоративные листья для зеленой темы
        if self.theme_id == "green_gray":
            self.draw_leaves(painter, main_rect)
    
    def draw_leaves(self, painter, rect):
        """Рисует декоративные листья для зеленой темы"""
        painter.save()
        
        leaf_color = QColor(76, 175, 80, 100)
        painter.setBrush(QBrush(leaf_color))
        painter.setPen(QPen(QColor(56, 142, 60, 120), 1))
        
        leaf_size = 20
        
        # Листья в разных местах
        self.draw_leaf(painter, rect.width() * 0.15, rect.height() * 0.15, leaf_size, 45)
        self.draw_leaf(painter, rect.width() * 0.85, rect.height() * 0.2, leaf_size * 0.8, -30)
        self.draw_leaf(painter, rect.width() * 0.2, rect.height() * 0.8, leaf_size * 0.9, 60)
        self.draw_leaf(painter, rect.width() * 0.9, rect.height() * 0.75, leaf_size * 0.7, -45)
        
        painter.restore()
    
    def draw_leaf(self, painter, x, y, size, rotation):
        """Рисует один лист"""
        painter.save()
        painter.translate(x, y)
        painter.rotate(rotation)
        
        path = QPainterPath()
        path.addEllipse(-size/2, -size/3, size, size * 0.67)
        small_path = QPainterPath()
        small_path.addEllipse(-size/4, -size/6, size/2, size/3)
        path = path.subtracted(small_path)
        painter.drawPath(path)
        
        painter.setPen(QPen(QColor(56, 142, 60, 80), 1.5))
        painter.drawLine(QLineF(0, -size/3, 0, size/3))
        
        painter.restore()


class SettingsSaveNotification(QWidget):
    """Анимированное уведомление о сохранении настроек"""
    def __init__(self, parent=None, message=None):
        if message is None:
            message = tr("settings_saved")
        super().__init__(parent)
        self.message = message
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        """Создает интерфейс уведомления"""
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        self.setLayout(layout)
        
        # Иконка успеха
        icon_label = QLabel("✓")
        icon_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        icon_label.setStyleSheet("color: #6C4DFF; background: transparent;")
        layout.addWidget(icon_label)
        
        # Текст
        text_label = QLabel(self.message)
        text_label.setFont(QFont("Inter", 13, QFont.Weight.Medium))
        text_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(text_label)
        
        # Стили для виджета
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:1 #FAF9FE);
                border: 1.5px solid #DAD2FF;
                border-radius: 14px;
            }
        """)
        
        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(108, 77, 255, 40))
        self.setGraphicsEffect(shadow)
        
        self.setFixedHeight(56)
        self.setFixedWidth(280)
        
    def setup_animation(self):
        """Настраивает анимацию появления и исчезновения"""
        # Начальная позиция (вне экрана справа)
        if self.parent():
            parent_rect = self.parent().geometry()
            self.start_x = parent_rect.width()
            self.end_x = parent_rect.width() - self.width() - 20
            self.y_pos = parent_rect.height() - self.height() - 20
        else:
            self.start_x = 1000
            self.end_x = 700
            self.y_pos = 700
            
        self.move(self.start_x, self.y_pos)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Анимация появления (выезд справа)
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(350)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_animation.setStartValue(QPoint(self.start_x, self.y_pos))
        self.slide_animation.setEndValue(QPoint(self.end_x, self.y_pos))
        
        # Анимация исчезновения (fade-out)
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.hide)
        
    def show_notification(self):
        """Показывает уведомление с анимацией"""
        if self.parent():
            parent_rect = self.parent().geometry()
            self.start_x = parent_rect.width()
            self.end_x = parent_rect.width() - self.width() - 20
            self.y_pos = parent_rect.height() - self.height() - 20
            self.slide_animation.setStartValue(QPoint(self.start_x, self.y_pos))
            self.slide_animation.setEndValue(QPoint(self.end_x, self.y_pos))
        
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Запускаем анимацию появления
        self.slide_animation.start()
        
        # Автоматически скрываем через 3 секунды
        QTimer.singleShot(3000, self.hide_notification)
        
    def hide_notification(self):
        """Скрывает уведомление с анимацией"""
        self.fade_animation.start()


class SettingsDialog(QDialog):
    """Диалог настроек в стиле приложения"""
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle(tr("settings"))
        self.setFixedSize(1400, 900)
        self.current_section = "general"
        self.selected_language = get_current_language()
        self.has_unsaved_changes = False
        self.search_input = None
        self.overlay = None  # Overlay для затемнения фона
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
        self.setup_animation()
    
    
    def setup_animation(self):
        """Настраивает анимацию появления"""
        self.setWindowOpacity(0.0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def create_monochrome_icon(self, icon_type, color="#6B5A7A", size=20):
        """Создает монохромную иконку для кнопок навигации"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        brush = QBrush(QColor(color))
        painter.setBrush(brush)
        
        # Простые монохромные иконки для настроек
        if icon_type == "general":
            # Иконка настроек (шестеренка)
            painter.setBrush(QBrush())  # Без заливки
            painter.drawEllipse(6, 6, 8, 8)
            painter.drawLine(10, 2, 10, 6)
            painter.drawLine(10, 14, 10, 18)
            painter.drawLine(2, 10, 6, 10)
            painter.drawLine(14, 10, 18, 10)
            # Диагональные линии
            painter.drawLine(4, 4, 6, 6)
            painter.drawLine(14, 4, 12, 6)
            painter.drawLine(16, 16, 14, 14)
            painter.drawLine(4, 16, 6, 14)
        elif icon_type == "data":
            # Иконка данных (график)
            painter.setBrush(QBrush())  # Без заливки
            painter.drawLine(4, 15, 7, 11)
            painter.drawLine(7, 11, 11, 13)
            painter.drawLine(11, 13, 15, 7)
            # Точки на графике
            painter.setBrush(brush)
            painter.drawEllipse(6, 10, 2, 2)
            painter.drawEllipse(10, 12, 2, 2)
            painter.drawEllipse(14, 6, 2, 2)
        elif icon_type == "account":
            # Иконка аккаунта (профиль)
            painter.drawEllipse(6, 4, 8, 8)
            painter.drawLine(5, 14, 15, 14)
        elif icon_type == "security":
            # Иконка безопасности (щит)
            path = QPainterPath()
            path.moveTo(10, 2)
            path.lineTo(4, 4)
            path.lineTo(4, 10)
            path.quadTo(4, 14, 10, 18)
            path.quadTo(16, 14, 16, 10)
            path.lineTo(16, 4)
            path.closeSubpath()
            painter.setBrush(QBrush())  # Без заливки
            painter.drawPath(path)
            # Замок внутри
            painter.drawRect(8, 10, 4, 5)
            painter.drawLine(8, 10, 10, 8)
            painter.drawLine(12, 10, 10, 8)
        elif icon_type == "language":
            # Иконка языка (глобус)
            painter.setBrush(QBrush())  # Без заливки
            painter.drawEllipse(4, 4, 12, 12)
            # Меридианы
            painter.drawLine(10, 4, 10, 16)
            # Параллели
            painter.drawArc(4, 8, 12, 4, 0, 180 * 16)
            painter.drawArc(4, 10, 12, 4, 0, -180 * 16)
        elif icon_type == "logout":
            # Иконка выхода (дверь)
            painter.setBrush(QBrush())  # Без заливки
            painter.drawRect(4, 4, 8, 12)
            # Ручка двери
            painter.setBrush(brush)
            painter.drawEllipse(10, 8, 2, 2)
            # Стрелка выхода
            painter.drawLine(12, 10, 16, 10)
            painter.drawLine(14, 8, 16, 10)
            painter.drawLine(14, 12, 16, 10)
        
        painter.end()
        return QIcon(pixmap)
    
    def showEvent(self, event):
        """Показывает диалог с анимацией и затемнением фона"""
        super().showEvent(event)
        
        # Создаем overlay для затемнения фона (как в friends_page.py)
        if self.main_window:
            try:
                if self.overlay:
                    self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
            
            # Создаем overlay на главном окне, чтобы затемнить весь экран включая сайдбар
            self.overlay = QFrame(self.main_window)
            self.overlay.setGeometry(0, 0, self.main_window.width(), self.main_window.height())
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
            self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            # Устанавливаем начальную прозрачность для поддержки анимации
            self.overlay.setWindowOpacity(1.0)
            
            def close_on_overlay_click(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.close()
            
            self.overlay.mousePressEvent = close_on_overlay_click
            self.overlay.show()
            self.overlay.raise_()
        
        # Простая анимация появления (только fade)
        self.animation.start()
        if hasattr(self, 'container'):
            self.container.setStyleSheet("""
                QFrame#settingsDialogContainer {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FAF9FE, stop:0.5 #F5F0FF, stop:1 #FAF9FE);
                    border-radius: 28px;
                }
            """)
        QApplication.instance().installEventFilter(self)
    
    def closeEvent(self, event):
        """Закрывает диалог с анимацией и удаляет overlay"""
        if self.has_unsaved_changes:
            # Показываем предупреждение о несохраненных изменениях
            event.ignore()
            return
        
        # Флаг для предотвращения повторного вызова cleanup
        if not hasattr(self, '_closing'):
            self._closing = True
        else:
            event.ignore()
            return
        
        # Анимируем затемнение и закрытие одновременно
        def cleanup():
            """Удаляет overlay после завершения анимации"""
            if self.overlay:
                try:
                    self.overlay.hide()
                    self.overlay.deleteLater()
                except RuntimeError:
                    pass
                self.overlay = None
            self.hide()
            QApplication.instance().removeEventFilter(self)
            if self.main_window and hasattr(self.main_window, 'central_widget'):
                self.main_window.central_widget.setGraphicsEffect(None)
            self._closing = False
        
        # Анимация диалога (только fade)
        self.animation.setDirection(QPropertyAnimation.Direction.Backward)
        self.animation.finished.connect(cleanup)
        
        # Анимация overlay (если он есть) - синхронно с диалогом
        if self.overlay:
            # Убеждаемся, что overlay видим и имеет правильную прозрачность
            self.overlay.show()
            self.overlay.setWindowOpacity(1.0)
            
            self.overlay_animation = QPropertyAnimation(self.overlay, b"windowOpacity")
            self.overlay_animation.setDuration(300)
            self.overlay_animation.setStartValue(1.0)
            self.overlay_animation.setEndValue(0.0)
            self.overlay_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.overlay_animation.start()
        
        # Запускаем анимацию диалога одновременно
        self.animation.start()
        event.ignore()
    
    def setup_ui(self):
        """Создает интерфейс настроек с сайдбаром"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Контейнер с фоном
        container = QFrame()
        self.container = container
        container.setObjectName("settingsDialogContainer")
        container.setStyleSheet(f"""
            QFrame#settingsDialogContainer {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FAF9FE, stop:0.5 #F5F0FF, stop:1 #FAF9FE);
                border-radius: 28px;
            }}
        """)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(0)
        container.setLayout(container_layout)
        self.container_layout = container_layout
        
        # Заголовок с кнопкой закрытия (как на фотографии - заголовок слева вверху)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(tr("settings"))
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: #2D1B3D; background: transparent;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        close_button = QPushButton("✕")
        close_button.setFixedSize(32, 32)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(167, 139, 250, 0.2);
                border: none;
                border-radius: 16px;
                color: #8B7FA8;
                font-size: 18px;
                font-weight: normal;
            }}
            QPushButton:hover {{
                background-color: rgba(167, 139, 250, 0.35);
            }}
        """)
        header_layout.addWidget(close_button)
        container_layout.addLayout(header_layout)
        
        # Контент с сайдбаром
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 24, 0, 0)
        content_layout.setSpacing(24)
        
        # Сайдбар
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar, 1)
        
        # Контент (белая область с закругленными углами, как на фотографии)
        content_wrapper = QFrame()
        content_wrapper.setObjectName("contentWrapper")
        content_wrapper.setStyleSheet("""
            QFrame#contentWrapper {
                background: #FFFFFF;
                border-radius: 20px;
            }
        """)
        content_wrapper_layout = QVBoxLayout()
        content_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        content_wrapper_layout.setSpacing(0)
        content_wrapper.setLayout(content_wrapper_layout)
        
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: transparent;
                border: none;
            }
        """)
        content_wrapper_layout.addWidget(self.content_stack)
        content_layout.addWidget(content_wrapper, 4)
        
        container_layout.addLayout(content_layout)
        
        # Инициализируем секции
        self.init_sections()
        
        main_layout.addWidget(container)
    
    def create_sidebar(self):
        """Создает сайдбар с категориями настроек"""
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setStyleSheet("""
            QFrame#settingsSidebar {
                background: rgba(245, 240, 250, 0.95);
                border: none;
                border-radius: 16px;
            }
        """)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(8)
        sidebar.setLayout(sidebar_layout)
        
        # Поиск
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_settings"))
        self.search_input.textChanged.connect(self.filter_settings)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 1.0);
                border: 2px solid rgba(167, 139, 250, 0.25);
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
                color: #4B3F72;
            }
            QLineEdit:focus {
                background: rgba(255, 255, 255, 1.0);
                border: 2px solid rgba(167, 139, 250, 0.5);
            }
            QLineEdit:hover {
                border: 2px solid rgba(167, 139, 250, 0.35);
            }
        """)
        search_layout.addWidget(self.search_input)
        sidebar_layout.addLayout(search_layout)
        sidebar_layout.addSpacing(12)
        
        # Кнопки категорий с монохромными иконками
        categories = [
            ("general", "general", tr("general")),
            ("data", "data", tr("data")),
            ("account", "account", tr("account_and_security")),
            ("security", "security", tr("security")),
            ("language", "language", tr("language_setting")),
        ]
        
        self.sidebar_buttons = {}
        for section_id, icon_type, title in categories:
            # Создаем кнопку с иконкой и текстом
            btn = QPushButton(title)
            btn.setObjectName(f"sidebarBtn_{section_id}")
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, sid=section_id: self.switch_section(sid))
            
            # Устанавливаем монохромную иконку
            btn.setIcon(self.create_monochrome_icon(icon_type, "#6B5A7A"))
            btn.setIconSize(QPixmap(20, 20).size())
            
            btn.setStyleSheet(f"""
                QPushButton#sidebarBtn_{section_id} {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    font-family: "Inter", "Segoe UI", sans-serif;
                    color: #6C4A8B;
                    font-size: 15px;
                    padding: 12px 18px;
                    padding-left: 14px;
                }}
                QPushButton#sidebarBtn_{section_id}:hover {{
                    background: rgba(167, 139, 250, 0.2);
                    color: #4B3F72;
                }}
                QPushButton#sidebarBtn_{section_id}::icon {{
                    margin-right: 8px;
                }}
            """)
            sidebar_layout.addWidget(btn)
            self.sidebar_buttons[section_id] = btn
        
        sidebar_layout.addStretch()
        
        # Кнопка выхода с иконкой (отдельно внизу, как на фотографии)
        logout_button = QPushButton(tr("logout"))
        logout_button.setObjectName("logoutButton")
        logout_button.setFixedHeight(48)
        logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_button.clicked.connect(self.logout_from_settings)
        
        # Устанавливаем монохромную иконку выхода
        logout_button.setIcon(self.create_monochrome_icon("logout", "#6B5A7A"))
        logout_button.setIconSize(QPixmap(20, 20).size())
        
        logout_button.setStyleSheet("""
            QPushButton#logoutButton {
                background: transparent;
                border: none;
                border-radius: 10px;
                text-align: left;
                font-family: "Inter", "Segoe UI", sans-serif;
                color: #6C4A8B;
                font-size: 15px;
                padding: 12px 18px;
                padding-left: 18px;
            }
            QPushButton#logoutButton:hover {
                background: rgba(167, 139, 250, 0.2);
                color: #4B3F72;
            }
            QPushButton#logoutButton::icon {
                margin-right: 8px;
            }
        """)
        sidebar_layout.addWidget(logout_button)
        
        return sidebar
    
    def switch_section(self, section_id):
        """Переключает секцию настроек"""
        if self.has_unsaved_changes:
            return  # Блокируем переключение при несохраненных изменениях
            
        self.current_section = section_id
        
        # Маппинг секций к типам иконок
        icon_types = {
            "general": "general",
            "data": "data",
            "account": "account",
            "security": "security",
            "language": "language"
        }
        
        # Подсвечиваем активную кнопку и обновляем иконки
        for sid, btn in self.sidebar_buttons.items():
            icon_type = icon_types.get(sid, "general")
            if sid == section_id:
                # Активная кнопка - темная иконка
                btn.setIcon(self.create_monochrome_icon(icon_type, "#4B3F72"))
                btn.setStyleSheet(f"""
                    QPushButton#sidebarBtn_{sid} {{
                        background: rgba(167, 139, 250, 0.3);
                        border: none;
                        border-radius: 10px;
                        text-align: left;
                        font-family: "Inter", "Segoe UI", sans-serif;
                        color: #4B3F72;
                        font-size: 15px;
                        padding: 12px 18px;
                        padding-left: 14px;
                    }}
                    QPushButton#sidebarBtn_{sid}:hover {{
                        background: rgba(167, 139, 250, 0.3);
                    }}
                    QPushButton#sidebarBtn_{sid}::icon {{
                        margin-right: 8px;
                    }}
                """)
            else:
                # Неактивная кнопка - светлая иконка
                btn.setIcon(self.create_monochrome_icon(icon_type, "#6B5A7A"))
                btn.setStyleSheet(f"""
                    QPushButton#sidebarBtn_{sid} {{
                        background: transparent;
                        border: none;
                        border-radius: 10px;
                        text-align: left;
                        font-family: "Inter", "Segoe UI", sans-serif;
                        color: #6C4A8B;
                        font-size: 15px;
                        padding: 12px 18px;
                        padding-left: 14px;
                    }}
                    QPushButton#sidebarBtn_{sid}:hover {{
                        background: rgba(167, 139, 250, 0.2);
                        color: #4B3F72;
                    }}
                    QPushButton#sidebarBtn_{sid}::icon {{
                        margin-right: 8px;
                    }}
                """)
        # Переключаем контент
        if hasattr(self, 'content_stack'):
            if section_id == "general":
                self.content_stack.setCurrentIndex(0)
            elif section_id == "language":
                self.content_stack.setCurrentIndex(1)
            elif section_id == "data":
                self.content_stack.setCurrentIndex(2)
                if hasattr(self, 'data_widget_ref') and self.data_widget_ref:
                    if hasattr(self.data_widget_ref, 'load_data'):
                        self.data_widget_ref.load_data()
            elif section_id == "account":
                self.content_stack.setCurrentIndex(3)
            elif section_id == "security":
                self.content_stack.setCurrentIndex(4)
    
    def init_sections(self):
        """Инициализирует секции настроек"""
        # Секция "Основное"
        general_widget = self.create_general_section()
        self.content_stack.addWidget(general_widget)
        
        # Секция "Language & Time"
        language_widget = self.create_language_section()
        self.content_stack.addWidget(language_widget)

        # Секция "Данные"
        data_widget = self.create_data_section()
        self.content_stack.addWidget(data_widget)
        
        # Секция "Аккаунт"
        account_widget = self.create_account_section()
        self.content_stack.addWidget(account_widget)
        
        # Секция "Безопасность"
        security_widget = self.create_security_section()
        self.content_stack.addWidget(security_widget)
        
        # Выбираем первую секцию
        self.switch_section("general")
    
    def create_general_section(self):
        """Создает секцию основных настроек"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        widget.setLayout(layout)
        
        # Заголовок секции (как на фотографии)
        title = QLabel(tr("general"))
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title)
        
        # Подзаголовок
        subtitle = QLabel(tr("settings"))
        subtitle.setFont(QFont("Segoe UI", 13))
        subtitle.setStyleSheet("color: #8A7A9A; background: transparent;")
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        # Контент секции (пока пустой, как на фотографии)
        layout.addStretch()
        
        return widget
    
    def create_language_section(self):
        """Создает секцию выбора языка в стиле Discord"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        widget.setLayout(layout)
        
        # Карточка с молочно-белым фоном
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet("""
            QFrame#settingsCard {
                background: #FAF9FE;
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)
        card.setLayout(card_layout)
        
        # Заголовок
        title = QLabel("Language & Time")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Normal))
        title.setStyleSheet("color: #4B3F72; background: transparent;")
        card_layout.addWidget(title)
        
        # Инструкция
        instruction_label = QLabel("Выберите язык\nChoose the language you want Discord to display.")
        instruction_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Normal))
        instruction_label.setStyleSheet("color: #6C4A8B; background: transparent;")
        instruction_label.setWordWrap(True)
        card_layout.addWidget(instruction_label)
        
        # Dropdown для выбора языка с флагами
        self.language_combo = QComboBox()
        self.language_combo.setFixedHeight(50)
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Добавляем языки с эмодзи флагов
        languages = [
            ("ru", "🇷🇺", "Русский"),
            ("de", "🇩🇪", "Deutsch"),
            ("en", "🇬🇧", "English")
        ]
        
        current_lang = get_current_language()
        current_index = 0
        
        for i, (code, flag_emoji, lang_name) in enumerate(languages):
            # Используем формат с эмодзи флагами
            display_text = f"{flag_emoji} {lang_name}"
            self.language_combo.addItem(display_text, code)
            if code == current_lang:
                current_index = i
        
        # Устанавливаем кастомный делегат для убирания разделителей
        delegate = LanguageItemDelegate(self.language_combo)
        self.language_combo.setItemDelegate(delegate)
        
        self.language_combo.setCurrentIndex(current_index)
        self.language_combo.currentIndexChanged.connect(self.on_language_combo_changed)
        
        # Стилизация dropdown в стиле Discord
        self.language_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                color: #2D1B3D;
                font-size: 14px;
                font-weight: normal;
                font-family: "Segoe UI", sans-serif;
            }
            QComboBox:hover {
                background-color: #F5F0FF;
            }
            QComboBox:focus {
                background-color: #FFFFFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #8B7FA8;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: none;
                border-radius: 8px;
                selection-background-color: transparent;
                selection-color: #2D1B3D;
                padding: 4px;
                margin: 2px;
                outline: none;
                show-decoration-selected: 0;
            }
            QComboBox QAbstractItemView::item {
                padding: 12px 16px;
                border: none;
                border-top: none;
                border-bottom: none;
                border-left: none;
                border-right: none;
                border-radius: 6px;
                margin: 2px;
                min-height: 20px;
                background: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F5F0FF;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #E8E0F5;
                border: none;
            }
            QComboBox QAbstractItemView::item:checked {
                background-color: #E8E0F5;
                border: none;
            }
        """)
        
        card_layout.addWidget(self.language_combo)
        
        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        
        return widget
    
    def create_theme_section(self):
        """Секция тем удалена."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        notice = QLabel("Раздел тем удален из приложения.")
        notice.setStyleSheet("color: #6C4A8B; background: transparent;")
        layout.addWidget(notice)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_theme_card(self, title, description, theme_id, is_selected=False):
        """Создает заглушку карточки темы (темы отключены)."""
        card = QFrame()
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addWidget(QLabel("Темы отключены"))
        card.setLayout(card_layout)
        return card
    
    def show_theme_preview_dialog(self, theme_id):
        """Темы отключены."""
        return
    
    def apply_theme(self, theme_id):
        """Темы отключены."""
        return
    
    def apply_theme_to_main_window(self):
        """Темы отключены."""
        return
    
    def update_theme_cards(self):
        """Темы отключены."""
        return
    
    def show_theme_editor(self):
        """Темы отключены."""
        return
    
    def create_data_section(self):
        """Создает секцию данных пользователя"""
        try:
            from pages.data_widget import DataWidget
            data_widget = DataWidget(parent=self)
            
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            widget.setLayout(layout)
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("""
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
            
            scroll.setWidget(data_widget)
            layout.addWidget(scroll)
            
            self.data_widget_ref = data_widget
            
            return widget
        except Exception as e:
            # Ошибка при создании секции данных - не выводим в консоль
            pass
            widget = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            error_label = QLabel(tr("error_loading_data_section"))
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: #EF4444; font-size: 14px; padding: 20px;")
            layout.addWidget(error_label)
            return widget
    
    def create_account_section(self):
        """Создает секцию данных аккаунта"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        widget.setLayout(layout)
        
        # Белая карточка
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setStyleSheet("""
            QFrame#settingsCard {
                background: #FAF9FE;
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)
        card.setLayout(card_layout)
        
        # Заголовок
        title = QLabel(tr("account_and_security"))
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Normal))
        title.setStyleSheet("color: #4B3F72; background: transparent;")
        card_layout.addWidget(title)
        
        # Разделитель убран по требованию
        
        card_layout.addSpacing(16)
        
        # Дата регистрации
        reg_date_title = QLabel(tr("registration_date"))
        reg_date_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Normal))
        reg_date_title.setStyleSheet("color: #4B3F72; background: transparent;")
        card_layout.addWidget(reg_date_title)
        
        username = email_app.get_current_username()
        reg_date = email_app.get_user_registration_date(username) if username else None
        if reg_date:
            try:
                from datetime import datetime
                if isinstance(reg_date, str):
                    dt = datetime.strptime(reg_date, '%Y-%m-%d %H:%M:%S')
                else:
                    dt = reg_date
                reg_date_str = dt.strftime('%d.%m.%Y')
            except:
                reg_date_str = str(reg_date)
        else:
            reg_date_str = tr("unknown_date") if hasattr(tr, '__call__') and tr("unknown_date") != "unknown_date" else "Неизвестно"
        
        reg_date_label = QLabel(reg_date_str)
        reg_date_label.setFont(QFont("Segoe UI", 12))
        reg_date_label.setStyleSheet("color: #6C4A8B; background: transparent;")
        card_layout.addWidget(reg_date_label)
        
        card_layout.addSpacing(20)
        
        # Google аккаунт
        google_title = QLabel("Google аккаунт")
        google_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Normal))
        google_title.setStyleSheet("color: #4B3F72; background: transparent;")
        card_layout.addWidget(google_title)
        
        self.google_info_label_settings = QLabel(tr("not_connected"))
        self.google_info_label_settings.setFont(QFont("Segoe UI", 12))
        self.google_info_label_settings.setStyleSheet("color: #6C4A8B; background: transparent;")
        card_layout.addWidget(self.google_info_label_settings)
        
        google_buttons_layout = QHBoxLayout()
        google_buttons_layout.setSpacing(12)
        
        self.connect_google_btn_settings = QPushButton("Подключить Google")
        self.connect_google_btn_settings.setFixedHeight(44)
        self.connect_google_btn_settings.clicked.connect(self.connect_google_from_settings)
        self.connect_google_btn_settings.setStyleSheet("""
            QPushButton {
                background: #9C89B8;
                border: none;
                border-radius: 12px;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #6C4A8B;
            }
        """)
        google_buttons_layout.addWidget(self.connect_google_btn_settings)
        
        self.disconnect_google_btn_settings = QPushButton("Отключить")
        self.disconnect_google_btn_settings.setFixedHeight(44)
        self.disconnect_google_btn_settings.clicked.connect(self.disconnect_google_from_settings)
        self.disconnect_google_btn_settings.hide()
        self.disconnect_google_btn_settings.setStyleSheet("""
            QPushButton {
                background: rgba(200, 182, 226, 0.6);
                border: 2px solid rgba(200, 182, 226, 0.4);
                border-radius: 12px;
                color: #6C4A8B;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(200, 182, 226, 0.8);
            }
        """)
        google_buttons_layout.addWidget(self.disconnect_google_btn_settings)
        
        card_layout.addLayout(google_buttons_layout)
        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        
        # Загружаем статус Google аккаунта
        QTimer.singleShot(100, self.load_google_status)
        
        return widget
    
    def create_security_section(self):
        """Создает секцию безопасности"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        widget.setLayout(layout)
        
        # Белая карточка
        card = QFrame()
        card.setObjectName("securityCard")
        card.setStyleSheet("""
            QFrame#securityCard {
                background: #FAF9FE;
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        card.setLayout(card_layout)
        
        # Заголовок
        security_title = QLabel(tr("security_title"))
        security_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Normal))
        security_title.setStyleSheet("color: #4B3F72; background: transparent;")
        card_layout.addWidget(security_title)
        
        # Разделитель убран по требованию
        
        # Настройка: Блокировка экрана при бездействии
        screen_lock_layout = QHBoxLayout()
        screen_lock_layout.setSpacing(12)
        
        screen_lock_label = QLabel("Блокировка экрана при бездействии")
        screen_lock_label.setFont(QFont("Segoe UI", 13))
        screen_lock_label.setStyleSheet("color: #4B3F72; background: transparent;")
        screen_lock_label.setWordWrap(True)
        screen_lock_layout.addWidget(screen_lock_label, 1)
        
        self.screen_lock_checkbox = QCheckBox()
        self.screen_lock_checkbox.setChecked(False)
        self.screen_lock_checkbox.stateChanged.connect(self.mark_unsaved_changes)
        self.screen_lock_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(156, 137, 184, 0.4);
                border-radius: 6px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #A78BFA;
                border-color: #8B5CF6;
            }
        """)
        screen_lock_layout.addWidget(self.screen_lock_checkbox)
        card_layout.addLayout(screen_lock_layout)
        
        # Описание настройки
        description_label = QLabel("При включении этой опции приложение будет автоматически блокироваться после 15 минут бездействия для защиты ваших данных.")
        description_label.setFont(QFont("Segoe UI", 12))
        description_label.setStyleSheet("color: #86868B; background: transparent; padding-left: 0px;")
        description_label.setWordWrap(True)
        card_layout.addWidget(description_label)
        
        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        
        return widget
    
    def eventFilter(self, obj, event):
        """Обработчик событий для закрытия при клике вне рамки"""
        if event.type() == QEvent.Type.MouseButtonPress:
            # Проверяем, что клик был вне диалога
            if obj == QApplication.instance():
                if hasattr(self, 'container') and self.isVisible():
                    container_global_pos = self.container.mapToGlobal(QPoint(0, 0))
                    container_rect = QRect(container_global_pos, self.container.size())
                    click_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                    if not container_rect.contains(click_pos):
                        if self.has_unsaved_changes:
                            # Показываем предупреждение
                            return True
                        self.close()
                        return True
        return super().eventFilter(obj, event)
    
    def show_language_dialog(self):
        """Показывает современный диалог выбора языка (для обратной совместимости)"""
        # Переключаемся на секцию языка
        self.switch_section("language")
    
    def change_language(self, language_code, dialog=None):
        """Выбирает язык"""
        manager = get_localization_manager()
        
        self.selected_language = language_code
        current_lang_name = manager.get_language_display_name(language_code)
        
        if hasattr(self, 'language_display'):
            self.language_display.setText(current_lang_name)
        
        if dialog:
            dialog.close()
        
        self.mark_unsaved_changes()
    
    def on_language_combo_changed(self, index):
        """Обработчик изменения языка в выпадающем списке"""
        if hasattr(self, 'language_combo'):
            language_code = self.language_combo.itemData(index)
            if language_code and language_code != get_current_language():
                self.selected_language = language_code
                self.mark_unsaved_changes()
    
    def mark_unsaved_changes(self):
        """Отмечает наличие несохраненных изменений"""
        self.has_unsaved_changes = True
        if hasattr(self, 'save_button'):
            self.save_button.show()
        if hasattr(self, 'sidebar_buttons'):
            for btn in self.sidebar_buttons.values():
                btn.setEnabled(False)
        self.show_unsaved_changes_widget()
    
    def show_unsaved_changes_widget(self):
        """Показывает виджет с вопросом сохранить или сбросить изменения"""
        if not hasattr(self, 'unsaved_changes_widget') or not self.unsaved_changes_widget:
            self.unsaved_changes_widget = QFrame(self.container)
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
            
            warning_text = QLabel(tr("unsaved_changes_warning") if hasattr(tr, '__call__') and tr("unsaved_changes_warning") != "unsaved_changes_warning" else "У вас есть несохраненные изменения. Сохранить или сбросить?")
            warning_text.setFont(QFont("Segoe UI", 13))
            warning_text.setStyleSheet("color: #6C4A8B; background: transparent;")
            warning_text.setWordWrap(True)
            widget_layout.addWidget(warning_text, 1)
            
            reset_btn = QPushButton(tr("reset") if hasattr(tr, '__call__') and tr("reset") != "reset" else "Сбросить")
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
            reset_btn.clicked.connect(self.reset_changes)
            widget_layout.addWidget(reset_btn)
            
            save_btn_widget = QPushButton(tr("save") if hasattr(tr, '__call__') and tr("save") != "save" else "Сохранить")
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
            save_btn_widget.clicked.connect(self.save_settings)
            widget_layout.addWidget(save_btn_widget)
            
            self.unsaved_changes_widget.setLayout(widget_layout)
            self.unsaved_changes_widget.hide()
            
            if hasattr(self, 'container_layout'):
                self.container_layout.addWidget(self.unsaved_changes_widget)
        
        if hasattr(self, 'unsaved_changes_widget'):
            self.unsaved_changes_widget.show()
            self.unsaved_changes_widget.raise_()
    
    def reset_changes(self):
        """Сбрасывает несохраненные изменения"""
        self.has_unsaved_changes = False
        self.selected_language = get_current_language()
        if hasattr(self, 'language_combo'):
            current_lang = get_current_language()
            for i in range(self.language_combo.count()):
                if self.language_combo.itemData(i) == current_lang:
                    self.language_combo.setCurrentIndex(i)
                    break
        
        # Сбрасываем чекбокс блокировки экрана
        if hasattr(self, 'screen_lock_checkbox'):
            self.screen_lock_checkbox.setChecked(False)
        
        if hasattr(self, 'unsaved_changes_widget'):
            self.unsaved_changes_widget.hide()
        if hasattr(self, 'save_button'):
            self.save_button.hide()
        
        if hasattr(self, 'sidebar_buttons'):
            for btn in self.sidebar_buttons.values():
                btn.setEnabled(True)
    
    def save_settings(self):
        """Сохраняет настройки"""
        # Сохраняем язык, если он был изменен
        if hasattr(self, 'selected_language') and self.selected_language:
            if self.selected_language != get_current_language():
                set_language(self.selected_language, save_to_db=True)
                
                if self.main_window:
                    self.main_window.update_all_texts()
                    QTimer.singleShot(1500, lambda: self.main_window.update_all_texts() if self.main_window else None)
        
        self.has_unsaved_changes = False
        if hasattr(self, 'save_button'):
            self.save_button.hide()
        if hasattr(self, 'unsaved_changes_widget'):
            self.unsaved_changes_widget.hide()
        if hasattr(self, 'sidebar_buttons'):
            for btn in self.sidebar_buttons.values():
                btn.setEnabled(True)
        
        # Показываем уведомление
        save_message = tr("settings_saved") if hasattr(tr, '__call__') and tr("settings_saved") != "settings_saved" else "Настройки сохранены"
        if not hasattr(self, 'save_notification') or self.save_notification is None:
            self.save_notification = SettingsSaveNotification(self, save_message)
        else:
            self.save_notification.message = save_message
            if self.save_notification.layout().itemAt(1):
                self.save_notification.layout().itemAt(1).widget().setText(save_message)
        
        self.save_notification.show_notification()
        
        # Если язык изменился, перезапускаем окно настроек для применения изменений
        if hasattr(self, 'selected_language') and self.selected_language and self.selected_language != get_current_language():
            QTimer.singleShot(4500, lambda: (self.close() if self else None, self.main_window.show_settings() if self.main_window else None))
        else:
            QTimer.singleShot(4000, self.close)
    
    def filter_settings(self, text):
        """Полнофункциональный поиск в настройках"""
        search_text = text.lower().strip()
        
        # Если поиск пустой, показываем все
        if not search_text:
            for btn in self.sidebar_buttons.values():
                btn.setVisible(True)
            return
        
        # Ключевые слова для поиска по секциям
        search_keywords = {
            "general": ["general", "основное", "общее", "allgemein"],
            "language": ["language", "язык", "sprache", "lang", "time", "время", "zeit"],
            "data": ["data", "данные", "профиль", "profil"],
            "account": ["account", "аккаунт", "google", "регистрация", "registration"],
            "security": ["security", "безопасность", "sicherheit", "история", "history", "предупреждения", "warnings"]
        }
        
        # Фильтруем кнопки сайдбара
        visible_sections = []
        for section_id, btn in self.sidebar_buttons.items():
            btn_text = btn.text().lower()
            keywords = search_keywords.get(section_id, [])
            
            # Проверяем соответствие
            if (search_text in btn_text or 
                any(keyword in search_text for keyword in keywords) or
                any(search_text in keyword for keyword in keywords)):
                btn.setVisible(True)
                visible_sections.append(section_id)
            else:
                btn.setVisible(False)
        
        # Переключаемся на первую видимую секцию
        if visible_sections and self.current_section not in visible_sections:
            self.switch_section(visible_sections[0])
    
    def load_google_status(self):
        """Загружает статус Google аккаунта"""
        username = email_app.get_current_username()
        if username:
            google_email = email_app.get_google_account_email(username)
            if google_email:
                self.google_info_label_settings.setText(f"{tr('connected') if hasattr(tr, '__call__') and tr('connected') != 'connected' else 'Подключено'}: {google_email}")
                self.connect_google_btn_settings.hide()
                self.disconnect_google_btn_settings.show()
            else:
                self.google_info_label_settings.setText(tr("not_connected"))
                self.connect_google_btn_settings.show()
                self.disconnect_google_btn_settings.hide()
    
    def connect_google_from_settings(self):
        """Подключает Google аккаунт из настроек"""
        if self.main_window and hasattr(self.main_window, 'profile_page'):
            self.main_window.profile_page.connect_google_account()
            QTimer.singleShot(500, self.load_google_status)
    
    def disconnect_google_from_settings(self):
        """Отключает Google аккаунт из настроек"""
        if self.main_window and hasattr(self.main_window, 'profile_page'):
            self.main_window.profile_page.disconnect_google_account()
            QTimer.singleShot(500, self.load_google_status)
    
    def logout_from_settings(self):
        """Выход из аккаунта из настроек с диалогом подтверждения"""
        if not self.main_window:
            return
        
        # Создаем диалог подтверждения
        dialog = LogoutConfirmDialog(self.main_window, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Закрываем настройки
            self.close()
            # Выполняем выход напрямую, без повторного показа диалога
            self.main_window._execute_logout()
