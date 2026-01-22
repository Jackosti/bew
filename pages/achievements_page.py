"""
Страница достижений (Achievements Page)
Полностью переработанный интерфейс с фокусом на текущей цели
"""
import sqlite3
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QScrollArea, QGraphicsDropShadowEffect, QProgressBar, QSizePolicy, QGridLayout, QDialog,
    QSpacerItem, QGraphicsView, QGraphicsScene, QGraphicsProxyWidget
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect, QEvent, QPoint, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QPixmap, QPolygon, QPainterPath, QIcon
import math

# ============================================================================
# UI helpers (hover lift, ticked progress, hover scale)
# ============================================================================

class HoverLiftFrame(QFrame):
    """Карточка, которая слегка приподнимается на hover (премиальный эффект)."""
    def __init__(self, *args, lift_px: int = 4, duration_ms: int = 140, parent=None, **kwargs):
        super().__init__(parent)
        self._lift_px = lift_px
        self._duration_ms = duration_ms
        self._base_pos = None
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(self._duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        if self._base_pos is None:
            self._base_pos = self.pos()
        self._anim.stop()
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(self._base_pos.x(), self._base_pos.y() - self._lift_px))
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._base_pos is None:
            self._base_pos = self.pos()
        self._anim.stop()
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(self._base_pos)
        self._anim.start()
        super().leaveEvent(event)


class HoverScaleButton(QPushButton):
    """Кнопка, которая чуть увеличивается на hover."""
    def __init__(self, *args, scale_px: int = 3, duration_ms: int = 140, **kwargs):
        super().__init__(*args, **kwargs)
        self._scale_px = scale_px
        self._duration_ms = duration_ms
        self._base_geo = None
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(self._duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        if self._base_geo is None:
            self._base_geo = self.geometry()
        g = self._base_geo
        bigger = QRect(g.x() - self._scale_px, g.y() - self._scale_px, g.width() + self._scale_px * 2, g.height() + self._scale_px * 2)
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(bigger)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._base_geo is None:
            self._base_geo = self.geometry()
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(self._base_geo)
        self._anim.start()
        super().leaveEvent(event)


class TickedProgressBar(QProgressBar):
    """Прогресс-бар с делениями и цифрами 1..target (для 10 писем)."""
    def __init__(self, target: int, parent=None):
        super().__init__(parent)
        self._target = max(1, int(target))
        self.setTextVisible(False)
        self.setRange(0, self._target)

    def paintEvent(self, event):
        super().paintEvent(event)
        # рисуем деления сверху поверх бара
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        # небольшие отступы, чтобы деления не упирались в скругления
        left = 10
        right = 10
        top = 2
        height = rect.height()
        usable_w = max(1, rect.width() - left - right)

        # Делаем деления более заметными и чуть темнее
        tick_pen = QPen(QColor(45, 27, 61, 110))
        tick_pen.setWidth(1)
        painter.setPen(tick_pen)

        # Деления 1..target
        for i in range(1, self._target + 1):
            x = rect.x() + left + int((i / self._target) * usable_w)
            painter.drawLine(x, rect.y() + top, x, rect.y() + height - top)

        painter.end()

# ============================================================================
# Premium CTA button (hover lift + shadow)
# ============================================================================

class PremiumCTAButton(QPushButton):
    """CTA-кнопка: hover -> лёгкий подъём + тень, pressed -> лёгкое вдавливание."""
    def __init__(self, *args, lift_px: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        self._lift_px = lift_px
        self._base_pos: Optional[QPoint] = None
        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(120)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMouseTracking(True)

    def _ensure_base_pos(self):
        if self._base_pos is None:
            self._base_pos = self.pos()

    def enterEvent(self, event):
        self._ensure_base_pos()
        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(22)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(60, 20, 100, 55))
        self.setGraphicsEffect(shadow)
        # Подъём
        if self._base_pos is not None:
            self._pos_anim.stop()
            self._pos_anim.setStartValue(self.pos())
            self._pos_anim.setEndValue(QPoint(self._base_pos.x(), self._base_pos.y() - self._lift_px))
            self._pos_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._ensure_base_pos()
        self.setGraphicsEffect(None)
        if self._base_pos is not None:
            self._pos_anim.stop()
            self._pos_anim.setStartValue(self.pos())
            self._pos_anim.setEndValue(self._base_pos)
            self._pos_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._ensure_base_pos()
        if self._base_pos is not None:
            self._pos_anim.stop()
            self.move(self._base_pos.x(), self._base_pos.y() + 1)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._ensure_base_pos()
        if self._base_pos is not None:
            self.move(self._base_pos)
        super().mouseReleaseEvent(event)

# ============================================================================
# Lazy imports and function getters
# ============================================================================

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
            get_current_username, get_email_history, get_friends,
            get_google_account_email, get_user_info, DatabaseConnection
        )
        return {
            'get_current_username': get_current_username,
            'get_email_history': get_email_history,
            'get_friends': get_friends,
            'get_google_account_email': get_google_account_email,
            'get_user_info': get_user_info,
            'DatabaseConnection': DatabaseConnection
        }
    except ImportError:
        return {
            'get_current_username': lambda: None,
            'get_email_history': lambda username=None, force_refresh=False: [],
            'get_friends': lambda username: [],
            'get_google_account_email': lambda username: None,
            'get_user_info': lambda username=None: None,
            'DatabaseConnection': None
        }

def create_monochrome_icon(icon_type: str, color: str = "#6B5A7A", size: int = 24) -> QPixmap:
    """Создает монохромную иконку для диалога достижений"""
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
    
    center_x, center_y = size // 2, size // 2
    
    if icon_type == "lock":
        # Замок
        # Корпус замка
        painter.setBrush(QBrush(QColor(color)))
        painter.drawRoundedRect(center_x - 6, center_y - 2, 12, 10, 2, 2)
        # Дужка замка
        painter.setBrush(QBrush())  # Без заливки
        painter.drawArc(center_x - 6, center_y - 6, 12, 8, 0, 180 * 16)
    elif icon_type == "check":
        # Галочка
        painter.setBrush(QBrush())
        painter.drawLine(center_x - 4, center_y, center_x - 1, center_y + 3)
        painter.drawLine(center_x - 1, center_y + 3, center_x + 4, center_y - 3)
    elif icon_type == "clock":
        # Часы
        painter.setBrush(QBrush())
        painter.drawEllipse(center_x - 6, center_y - 6, 12, 12)
        # Стрелки
        painter.drawLine(center_x, center_y, center_x, center_y - 3)
        painter.drawLine(center_x, center_y, center_x + 3, center_y)
    elif icon_type == "mail":
        # Конверт
        painter.setBrush(QBrush())  # без заливки
        painter.drawRoundedRect(center_x - 8, center_y - 5, 16, 10, 2, 2)
        painter.drawLine(center_x - 8, center_y - 5, center_x, center_y + 1)
        painter.drawLine(center_x + 8, center_y - 5, center_x, center_y + 1)
        painter.drawLine(center_x - 8, center_y + 5, center_x, center_y - 1)
        painter.drawLine(center_x + 8, center_y + 5, center_x, center_y - 1)
    
    painter.end()
    return pixmap

def create_achievement_icon(achievement_id: str, color: str, size: int = 32, transparent_background: bool = False) -> QPixmap:
    """Создает премиальную иконку для достижения (бейдж как на рефе).
    
    Args:
        achievement_id: ID достижения
        color: Цвет иконки
        size: Размер иконки
        transparent_background: Если True, фон будет прозрачным (без круга)
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center_x, center_y = size // 2, size // 2
    base = QColor(color)
    base_dark = QColor(max(0, base.red() - 25), max(0, base.green() - 25), max(0, base.blue() - 25))
    base_light = QColor(min(255, base.red() + 55), min(255, base.green() + 55), min(255, base.blue() + 55))

    # Внешнее кольцо (глянец) - только если не прозрачный фон
    if not transparent_background:
        outer_r = size // 2 - 1
        grad = QBrush(QColor(0, 0, 0))
        ring = QPen(QColor(255, 255, 255, 110), 2)
        painter.setPen(ring)
        painter.setBrush(QBrush(base))
        painter.drawEllipse(center_x - outer_r, center_y - outer_r, outer_r * 2, outer_r * 2)

        # Внутренний градиент
        inner_r = outer_r - 3
        g = QBrush(QColor(0, 0, 0))
        # QLinearGradient доступен через QBrush/QPainter без импорта класса: используем QBrush(QColor) + слой
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(base_dark))
        painter.drawEllipse(center_x - inner_r, center_y - inner_r, inner_r * 2, inner_r * 2)
        painter.setBrush(QBrush(base))
        painter.drawEllipse(center_x - inner_r + 2, center_y - inner_r + 2, inner_r * 2 - 4, inner_r * 2 - 4)

        # Хайлайт (блик)
        painter.setBrush(QBrush(QColor(255, 255, 255, 90)))
        painter.drawEllipse(center_x - inner_r + 4, center_y - inner_r + 3, inner_r, inner_r // 2 + 2)

    # Символ внутри (разные стили)
    # Если прозрачный фон, используем цвет достижения для символа, иначе белый
    if transparent_background:
        symbol_color = QColor(color)
    else:
        symbol_color = QColor(255, 255, 255, 235)
    painter.setPen(QPen(symbol_color, 2))
    painter.setBrush(QBrush(symbol_color))

    def draw_star(r: int):
        pts = []
        outer = r
        inner = int(r * 0.45)
        for i in range(10):
            angle = math.pi / 2 - (i * 2 * math.pi / 10)
            rr = outer if i % 2 == 0 else inner
            x = center_x + rr * math.cos(angle)
            y = center_y - rr * math.sin(angle)
            pts.append(QPoint(int(x), int(y)))
        painter.drawPolygon(QPolygon(pts))

    if achievement_id in ("first_step", "expert"):
        draw_star(int(size * 0.23))
    elif achievement_id == "dedicated":
        # "пламя" — более округлое
        path = QPainterPath()
        path.moveTo(center_x, center_y + int(size * 0.22))
        path.cubicTo(center_x - int(size * 0.18), center_y + int(size * 0.05),
                    center_x - int(size * 0.10), center_y - int(size * 0.22),
                    center_x, center_y - int(size * 0.24))
        path.cubicTo(center_x + int(size * 0.10), center_y - int(size * 0.22),
                    center_x + int(size * 0.18), center_y + int(size * 0.05),
                    center_x, center_y + int(size * 0.22))
        painter.drawPath(path)
    elif achievement_id == "professional":
        # "рост" — колонка + стрелка
        painter.drawRoundedRect(center_x - 9, center_y + 2, 5, 8, 2, 2)
        painter.drawRoundedRect(center_x - 2, center_y - 2, 5, 12, 2, 2)
        painter.drawRoundedRect(center_x + 5, center_y - 6, 5, 16, 2, 2)
        painter.drawLine(center_x + 9, center_y - 10, center_x + 14, center_y - 15)
        painter.drawLine(center_x + 14, center_y - 15, center_x + 14, center_y - 9)
        painter.drawLine(center_x + 14, center_y - 15, center_x + 8, center_y - 15)
    elif achievement_id == "master":
        # "корона" — проще и массивнее
        crown = QPainterPath()
        crown.moveTo(center_x - 12, center_y + 8)
        crown.lineTo(center_x - 10, center_y - 6)
        crown.lineTo(center_x - 3, center_y + 1)
        crown.lineTo(center_x, center_y - 10)
        crown.lineTo(center_x + 3, center_y + 1)
        crown.lineTo(center_x + 10, center_y - 6)
        crown.lineTo(center_x + 12, center_y + 8)
        crown.closeSubpath()
        painter.drawPath(crown)
        if not transparent_background:
            painter.setBrush(QBrush(base_light))
            painter.drawRoundedRect(center_x - 12, center_y + 6, 24, 6, 3, 3)
    else:
        draw_star(int(size * 0.20))
    
    painter.end()
    return pixmap

# ============================================================================
# Dialog for showing all completed achievements
# ============================================================================

class CompletedAchievementsDialog(QDialog):
    """Диалог для отображения всех завершённых достижений"""
    
    def __init__(self, completed: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Завершённые достижения")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Заголовок
        title = QLabel("Завершённые достижения")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title)
        
        # Список достижений
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        for achievement in completed:
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background: rgba(245, 240, 255, 0.6);
                    border-radius: 16px;
                    padding: 16px;
                }
            """)
            frame_layout = QHBoxLayout()
            frame_layout.setContentsMargins(0, 0, 0, 0)
            frame_layout.setSpacing(12)
            
            icon = QLabel(achievement['icon'])
            icon.setFont(QFont("Segoe UI", 24))
            frame_layout.addWidget(icon)
            
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(4)
            
            title_label = QLabel(achievement['title'])
            title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #2D1B3D; background: transparent;")
            text_layout.addWidget(title_label)
            
            desc = QLabel(achievement['description'])
            desc.setFont(QFont("Segoe UI", 12))
            desc.setStyleSheet("color: #6C4A8B; background: transparent;")
            text_layout.addWidget(desc)
            
            frame_layout.addLayout(text_layout)
            frame_layout.addStretch()
            
            # Монохромная иконка галочки вместо эмодзи
            check_pixmap = create_monochrome_icon("check", "#10B981", 24)
            check = QLabel()
            check.setPixmap(check_pixmap)
            check.setStyleSheet("background: transparent;")
            frame_layout.addWidget(check)
            
            frame.setLayout(frame_layout)
            content_layout.addWidget(frame)
        
        content_layout.addStretch()
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.setFont(QFont("Segoe UI", 12))
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A78BFA,
                    stop:1 #8B5CF6);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6,
                    stop:1 #7C3AED);
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class AchievementDetailDialog(QDialog):
    """Диалог для просмотра деталей достижения с затемнением и карточкой профиля"""
    
    def __init__(self, achievement: Dict, parent=None, achievements_page=None):
        super().__init__(parent)
        self.achievement = achievement
        self.achievements_page = achievements_page
        self.setup_ui()
    
    def setup_ui(self):
        """Создает интерфейс с затемнением и карточкой профиля (как в settings.py)"""
        # Полноэкранный диалог с прозрачным фоном
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Получаем размеры родительского окна
        parent_widget = self.parent()
        if parent_widget and isinstance(parent_widget, QWidget):
            parent_rect = parent_widget.geometry()
            self.setGeometry(parent_rect)
        else:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QGuiApplication
            app = QApplication.instance()
            if app:
                screens = QGuiApplication.screens()
                if screens:
                    screen = screens[0].geometry()
                    self.setGeometry(screen)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Затемнение фона как в settings.py
        self.overlay = None
        main_window = None
        if self.achievements_page and hasattr(self.achievements_page, 'main_window'):
            main_window = self.achievements_page.main_window
        elif parent_widget and isinstance(parent_widget, QWidget):
            # Ищем главное окно
            current = parent_widget
            while current:
                if hasattr(current, 'main_window') or (hasattr(current, 'window') and current.window() and current.window() != current):
                    main_window = current.window() if hasattr(current, 'window') else current
                    break
                current = current.parentWidget()
        
        if main_window:
            from PyQt6.QtWidgets import QFrame as QFrameOverlay
            self.overlay = QFrameOverlay(main_window)
            self.overlay.setGeometry(0, 0, main_window.width(), main_window.height())
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
            self.overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.overlay.setWindowOpacity(1.0)
            
            def close_on_overlay_click(a0=None):
                if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
                    self.accept()
            if self.overlay:
                self.overlay.mousePressEvent = close_on_overlay_click
                overlay_ref = self.overlay
                QTimer.singleShot(50, lambda: (overlay_ref.show(), overlay_ref.raise_()))
        
        # Прозрачный контейнер для карточки (без затемнения)
        transparent_widget = QWidget()
        transparent_widget.setStyleSheet("background: transparent;")
        
        # Клик на прозрачную область закрывает диалог
        def close_on_transparent_click(a0=None):
            if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
                self.accept()
        transparent_widget.mousePressEvent = close_on_transparent_click
        
        transparent_layout = QVBoxLayout()
        transparent_layout.setContentsMargins(0, 0, 0, 0)
        transparent_layout.setSpacing(0)
        transparent_widget.setLayout(transparent_layout)
        
        # Карточка профиля в центре (не закрывает диалог при клике)
        profile_card = self.create_profile_card()
        transparent_layout.addStretch()
        transparent_layout.addWidget(profile_card, alignment=Qt.AlignmentFlag.AlignCenter)
        transparent_layout.addStretch()
        
        main_layout.addWidget(transparent_widget)
    
    def showEvent(self, event):
        """Показываем overlay при показе диалога"""
        super().showEvent(event)
        if self.overlay:
            self.overlay.show()
            self.overlay.raise_()
    
    def closeEvent(self, event):
        """Удаляем overlay при закрытии диалога (как в settings.py)"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
        super().closeEvent(event)
    
    def accept(self):
        """Удаляем overlay при принятии диалога"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
        super().accept()
    
    def reject(self):
        """Удаляем overlay при отмене диалога"""
        if self.overlay:
            try:
                self.overlay.hide()
                self.overlay.deleteLater()
            except RuntimeError:
                pass
            self.overlay = None
        super().reject()
    
    def create_profile_card(self) -> QFrame:
        """Создает карточку профиля с информацией о достижении (виджет с кнопкой закрытия)"""
        card = QFrame()
        card.setFixedSize(500, 600)
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(250, 245, 255, 0.98));
                border-radius: 20px;
                border: 2px solid rgba(167, 139, 250, 0.3);
            }
        """)
        # Предотвращаем закрытие диалога при клике на карточку
        def ignore_click(a0=None):
            pass
        card.mousePressEvent = ignore_click
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 150))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200, 182, 226, 0.2);
                border: 2px solid rgba(167, 139, 250, 0.4);
                border-radius: 16px;
                color: #2D1B3D;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(200, 182, 226, 0.3);
                border-color: rgba(167, 139, 250, 0.6);
            }
        """)
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)
        
        card.setLayout(layout)
        
        # Баннер‑карточка награды: отдельный слой позади иконки, растянутый по ширине модалки
        achievement_id = self.achievement.get('id', '')
        card_name = None
        if achievement_id == 'first_step':
            card_name = 'familiar'
        elif achievement_id == 'dedicated':
            card_name = 'hacker'
        
        # Базовое значение, чтобы не было UnboundLocalError
        achievement_unlocked = self.achievement.get('unlocked', False)
        
        banner_frame = QFrame()
        banner_frame.setObjectName("achievementBanner")
        banner_frame.setFixedHeight(160)
        banner_frame.setStyleSheet("""
            QFrame#achievementBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(238, 233, 246, 0.95),
                    stop:1 rgba(207, 194, 230, 0.95));
                border-radius: 16px;
                border: none;
            }
        """)
        banner_layout = QVBoxLayout()
        banner_layout.setContentsMargins(0, 0, 0, 0)
        banner_layout.setSpacing(0)
        banner_frame.setLayout(banner_layout)
        
        # Фон‑карточка (Familiar/Hacker) как back‑layer
        background_label = QLabel(banner_frame)
        background_label.setStyleSheet("background: transparent; border-radius: 16px;")
        background_label.setScaledContents(True)
        banner_layout.addWidget(background_label)
        
        if card_name:
            try:
                from pathlib import Path
                # Определяем путь к карточке
                if card_name == 'familiar':
                    card_path = Path(__file__).parent.parent / 'frames' / 'Familiar.png'
                elif card_name == 'hacker':
                    card_path = Path(__file__).parent.parent / 'frames' / 'Hacker.png'
                else:
                    card_path = None
                
                # Перепроверяем статус достижения по количеству писем
                if self.achievements_page and hasattr(self.achievements_page, '_funcs'):
                    username = self.achievements_page._funcs['get_current_username']()
                    if username:
                        history = self.achievements_page._funcs['get_email_history'](username)
                        total_sent = len(history) if history else 0
                        if achievement_id == 'first_step':
                            achievement_unlocked = total_sent >= 1
                        elif achievement_id == 'dedicated':
                            achievement_unlocked = total_sent >= 10
                        elif achievement_id == 'professional':
                            achievement_unlocked = total_sent >= 25
                        elif achievement_id == 'expert':
                            achievement_unlocked = total_sent >= 50
                        elif achievement_id == 'master':
                            achievement_unlocked = total_sent >= 100
                
                if card_path and card_path.exists():
                    card_pixmap = QPixmap(str(card_path))
                    if not card_pixmap.isNull():
                        # Растягиваем баннер по всей ширине с обрезкой по краям
                        card_pixmap = card_pixmap.scaled(
                            440, 160,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        # При необходимости затемняем, если достижение ещё не получено
                        if not achievement_unlocked:
                            darkened = QPixmap(card_pixmap.size())
                            darkened.fill(QColor(0, 0, 0, 0))
                            painter = QPainter(darkened)
                            painter.setOpacity(0.3)
                            painter.drawPixmap(0, 0, card_pixmap)
                            painter.end()
                            card_pixmap = darkened
                        background_label.setPixmap(card_pixmap)
            except Exception as e:
                print(f"Ошибка загрузки карточки: {e}")
        
        # Иконка достижения поверх баннера (чистая, без фона)
        icon_pixmap = create_achievement_icon(
            achievement_id,
            self.achievement.get('icon_color', '#A78BFA'),
            80
        )
        icon_label = QLabel(banner_frame)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none; padding: 0;")
        
        # Если достижение не получено, иконка остаётся чистой, без обводок
        if not achievement_unlocked:
            icon_label.setStyleSheet("background: transparent; border: none; padding: 0;")
        
        # Центруем иконку по баннеру после того, как виджет будет отрисован
        def position_icon():
            w = banner_frame.width()
            h = banner_frame.height()
            if w > 0 and h > 0:
                size = 80
                icon_label.setGeometry(
                    (w - size) // 2,
                    (h - size) // 2,
                    size,
                    size,
                )
                icon_label.raise_()
        QTimer.singleShot(0, position_icon)
        
        layout.addWidget(banner_frame)
        
        # Название достижения
        title_label = QLabel(self.achievement['title'])
        title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title_label)
        
        # Описание достижения
        desc_label = QLabel(self.achievement['description'])
        desc_label.setFont(QFont("Segoe UI", 14))
        desc_label.setStyleSheet("color: #6C5A8B; background: transparent;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Информация о карточке профиля (если есть)
        card_name = None
        achievement_id = self.achievement.get('id', '')
        if achievement_id == 'first_step':
            card_name = 'Familiar'
        elif achievement_id == 'dedicated':
            card_name = 'Hacker'
        
        if card_name:
            card_info_label = QLabel(f"Награда: Карточка профиля \"{card_name}\"")
            card_info_label.setFont(QFont("Segoe UI", 12))
            card_info_label.setStyleSheet("color: #8A7A9A; background: transparent;")
            layout.addWidget(card_info_label)
        
        # Дата завершения (если достижение выполнено)
        if self.achievements_page:
            completion_date = self.achievements_page.get_achievement_completion_date(achievement_id)
            if completion_date:
                date_label = QLabel(f"Завершено: {completion_date}")
                date_label.setFont(QFont("Segoe UI", 11))
                date_label.setStyleSheet("color: #9A90B8; background: transparent;")
                layout.addWidget(date_label)
        
        layout.addStretch()
        
        return card

# ============================================================================
# Achievements Page
# ============================================================================

class AchievementsPage(QWidget):
    """Страница достижений с фокусом на текущей цели"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._tr = get_tr()
        self._funcs = get_functions()
        self.animation_timer = None
        self.setup_ui()
        self.load_achievements()

    def tr(self, key: str) -> str:
        """Обёртка для функции перевода (не конфликтует с QObject.tr)."""
        try:
            return self._tr(key)
        except Exception:
            return key
    
    def setup_ui(self):
        """Создает интерфейс с 4 карточками в сетке 2x2"""
        # Главный контейнер с градиентным фоном
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Устанавливаем градиентный фон (как у заголовка)
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
        
        # Заголовок (вынесен из контейнера с виджетами, фон продолжается как за виджетами)
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #EEE9F6, stop:0.4 #E2DBF2, stop:1 #CFC2E6);
            }
        """)
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(40, 40, 40, 0)
        header_layout.setSpacing(0)
        header_widget.setLayout(header_layout)
        
        title_label = QLabel(self.tr("achievements") or "Достижения")
        # Чуть меньше, но жирнее
        title_font = QFont("Segoe UI", 32, QFont.Weight.Black)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            QLabel {
                color: #2D1B3D;
                background: transparent;
                letter-spacing: -0.5px;
            }
        """)
        header_layout.addWidget(title_label)
        main_layout.addWidget(header_widget)
        
        # Контент виджет (фон продолжается)
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #EEE9F6, stop:0.4 #E2DBF2, stop:1 #CFC2E6);
            }
        """)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(40, 16, 40, 40)  # Уменьшен верхний отступ
        content_layout.setSpacing(24)
        content_widget.setLayout(content_layout)
        
        # Сетка 2x2 для карточек
        grid_layout = QGridLayout()
        # Чуть меньше расстояние по вертикали, чтобы нижний ряд был выше
        grid_layout.setVerticalSpacing(28)
        grid_layout.setHorizontalSpacing(24)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Сохраняем ссылки на места для карточек
        self.grid_layout = grid_layout
        self.content_widget = content_widget  # Сохраняем для позиционирования виджета "Почти достигнута!"
        content_layout.addLayout(grid_layout)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
    
    def load_achievements(self):
        """Загружает и отображает достижения пользователя"""
        username = self._funcs['get_current_username']()
        if not username:
            return
        
        # Получаем статистику пользователя
        history = self._funcs['get_email_history'](username)
        total_sent = len(history)
        
        # Только достижения, связанные с письмами
        all_achievements = [
            # Разные цвета, чтобы достижения не были все фиолетовыми
            {'id': 'first_step', 'title': 'Первый шаг', 'description': 'Отправьте первое письмо', 'icon': '✨', 'unlocked': total_sent >= 1, 'target': 1, 'icon_color': '#A78BFA', 'card': 'familiar'},
            {'id': 'dedicated', 'title': 'Преданность', 'description': 'Отправьте 10 писем', 'icon': '🔥', 'unlocked': total_sent >= 10, 'target': 10, 'icon_color': '#F97316', 'card': 'hacker'},      # оранжевый
            {'id': 'professional', 'title': 'Профессионал', 'description': 'Отправьте 25 писем', 'icon': '💼', 'unlocked': total_sent >= 25, 'target': 25, 'icon_color': '#22C55E'},              # зелёный
            {'id': 'expert', 'title': 'Эксперт', 'description': 'Отправьте 50 писем', 'icon': '⭐', 'unlocked': total_sent >= 50, 'target': 50, 'icon_color': '#0EA5E9'},                       # голубой
            {'id': 'master', 'title': 'Мастер', 'description': 'Отправьте 100 писем', 'icon': '👑', 'unlocked': total_sent >= 100, 'target': 100, 'icon_color': '#EC4899'},                     # розовый
        ]
        
        # Находим текущую активную цель (Преданность или следующая незавершённая)
        current_goal = None
        for ach in all_achievements:
            if not ach['unlocked']:
                current_goal = ach
                break
        
        # Если все разблокированы, показываем последнее
        if current_goal is None:
            current_goal = all_achievements[-1]
        
        # Находим следующее достижение (следующее ПОСЛЕ текущего)
        next_achievement = None
        if current_goal:
            current_index = None
            for i, ach in enumerate(all_achievements):
                if ach['id'] == current_goal['id']:
                    current_index = i
                    break
            if current_index is not None and current_index + 1 < len(all_achievements):
                next_achievement = all_achievements[current_index + 1]
        
        # Находим завершённые достижения
        completed = [a for a in all_achievements if a['unlocked']]
        
        # Выдача карточек за достижения
        self.grant_achievement_cards(username, all_achievements)
        
        # Подсчитываем общий прогресс
        unlocked_count = len(completed)
        total_count = len(all_achievements)
        progress_percent = int((unlocked_count / total_count) * 100) if total_count > 0 else 0
        
        # Очищаем сетку
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child:
                widget = child.widget()
                if widget:
                    widget.deleteLater()
        
        # 1. Главная цель - слева вверху (больше других, шире)
        if current_goal:
            main_card = self.create_main_goal_card(current_goal, total_sent)
            main_card.setFixedHeight(300)  # Еще больше по вертикали
            self.grid_layout.addWidget(main_card, 0, 0, 1, 1)
            
            # Создаем виджет "Почти достигнута!" если нужно (над виджетом, выходит за края)
            if hasattr(self, '_almost_widget_data') and self._almost_widget_data:
                data = self._almost_widget_data
                almost_widget = QLabel("Почти достигнута")
                # Бейдж внутри карточки, привязан к её правому верхнему углу
                almost_widget.setParent(main_card)
                almost_widget.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                almost_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                almost_widget.setStyleSheet(f"""
                    QLabel {{
                        color: white;
                        background: {data['icon_color']};
                        border-radius: 16px;
                        padding: 6px 18px;
                    }}
                """)
                almost_widget.setFixedSize(170, 32)
                almost_widget.show()
                
                # Позиционируем после отображения
                def position_almost():
                    if main_card.width() > 0 and main_card.height() > 0:
                        # Позиционируем внутри карточки, у правого верхнего угла
                        x = main_card.width() - almost_widget.width() - 12
                        y = 12
                        almost_widget.move(x, y)
                        almost_widget.raise_()
                
                QTimer.singleShot(200, position_almost)
                # Также при изменении размера карточки
                original_resize = main_card.resizeEvent
                def resize_with_almost(a0=None):
                    if original_resize:
                        original_resize(a0)
                    position_almost()
                main_card.resizeEvent = resize_with_almost
        
        # 2. Следующее достижение - справа вверху
        if next_achievement:
            next_card = self.create_next_level_card(next_achievement)
            next_card.setFixedHeight(280)  # Чуть больше по вертикали
            self.grid_layout.addWidget(next_card, 0, 1, 1, 1)
        
        # 3. Общий прогресс - слева внизу (шире)
        progress_card = self.create_overall_progress_card(unlocked_count, total_count, progress_percent, total_sent)
        progress_card.setFixedHeight(250)  # Одинаковый размер
        self.grid_layout.addWidget(progress_card, 1, 0, 1, 1)
        
        # 4. Завершённые достижения - справа внизу
        completed_card = self.create_completed_card(completed)
        completed_card.setFixedHeight(220)  # Чуть меньше по вертикали
        self.grid_layout.addWidget(completed_card, 1, 1, 1, 1)
        
        # Устанавливаем растяжение для левых колонок (увеличиваем ширину)
        self.grid_layout.setColumnStretch(0, 2)  # Левая колонка шире
        self.grid_layout.setColumnStretch(1, 1)  # Правая колонка уже
    
    def grant_achievement_cards(self, username: str, achievements: List[Dict]):
        """Выдает карточки за достижения: familiar за первое, hacker за второе"""
        if not username or not self._funcs['DatabaseConnection']:
            return
        
        try:
            with self._funcs['DatabaseConnection']() as conn:
                cursor = conn.cursor()

                # Гарантируем, что колонка granted_cards существует, чтобы не падать с ошибкой
                try:
                    cursor.execute("PRAGMA table_info(auth_users)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'granted_cards' not in columns:
                        cursor.execute('ALTER TABLE auth_users ADD COLUMN granted_cards TEXT')
                        conn.commit()
                except Exception:
                    # Если по какой-то причине не удалось проверить/добавить колонку — просто выходим
                    return
                
                # Проверяем, какие карточки уже выданы
                cursor.execute('SELECT granted_cards FROM auth_users WHERE username = ?', (username,))
                result = cursor.fetchone()
                granted_cards = []
                if result and result[0]:
                    try:
                        import json
                        granted_cards = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                    except:
                        granted_cards = []
                
                # Первое достижение - familiar
                first_achievement = achievements[0] if achievements else None
                if first_achievement and first_achievement.get('unlocked') and 'familiar' not in granted_cards:
                    granted_cards.append('familiar')
                
                # Второе достижение - hacker
                second_achievement = achievements[1] if len(achievements) > 1 else None
                if second_achievement and second_achievement.get('unlocked') and 'hacker' not in granted_cards:
                    granted_cards.append('hacker')
                
                # Сохраняем выданные карточки
                import json
                cursor.execute('UPDATE auth_users SET granted_cards = ? WHERE username = ?', 
                             (json.dumps(granted_cards), username))
                conn.commit()
        except Exception as e:
            print(f"Ошибка при выдаче карточек: {e}")
    
    def create_main_goal_card(self, achievement: Dict, total_sent: int) -> QFrame:
        """Создает главную карточку с текущей целью по образцу фото"""
        # Делать главную карточку визуально доминирующей (без hover lift)
        card = QFrame()
        card.setObjectName("mainGoalCard")
        card.setFixedHeight(300)  # Еще больше по вертикали
        # Роли фиолетового: primary (акцент), muted (фон), secondary (бейджи)
        primary = "#7C3AED"
        card.setStyleSheet("""
            QFrame#mainGoalCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(245, 240, 255, 0.92),
                    stop:0.45 rgba(231, 223, 255, 0.92),
                    stop:1 rgba(224, 214, 255, 0.92));
                border-radius: 20px;
                border: 1px solid rgba(124, 58, 237, 0.22);
                padding: 0px;
            }
        """)
        
        # Декоративные элементы будут добавлены через paintEvent если нужно
        
        # Вычисляем прогресс для виджета "Почти достигнута!"
        current = min(total_sent, achievement.get('target', 10))
        target = achievement.get('target', 10)
        progress_to_next = int((current / target) * 100) if target > 0 else 0
        icon_color = achievement.get('icon_color', '#A78BFA')  # Меньше оранжевого
        
        # Усиленная тень для главной карточки (доминирующая)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(34)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(124, 58, 237, 85))
        card.setGraphicsEffect(shadow)
        
        # Используем единый spacing для всего layout
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)  # Единый spacing
        
        # Контейнер для верхней части с абсолютным позиционированием виджета "Почти достигнута!"
        top_container = QFrame()
        top_container.setStyleSheet("background: transparent;")
        top_container_layout = QHBoxLayout()
        top_container_layout.setContentsMargins(0, 0, 0, 0)
        top_container_layout.setSpacing(14)
        
        # Иконка без круглого фона (чистая)
        icon_container = QFrame()
        icon_container.setFixedSize(52, 52)
        icon_container.setStyleSheet("background: transparent; border: none;")
        
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        # Используем кастомную иконку с цветом достижения (увеличена)
        icon_pixmap = create_achievement_icon(achievement.get('id', ''), icon_color, 48)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none; padding: 0;")
        icon_label.setFixedSize(52, 52)
        icon_layout.addWidget(icon_label)
        icon_container.setLayout(icon_layout)
        top_container_layout.addWidget(icon_container)
        
        # Заголовок с процентом выполнения (вертикально)
        title_container = QVBoxLayout()
        title_container.setContentsMargins(0, 0, 0, 0)
        title_container.setSpacing(6)
        
        title_label = QLabel(achievement['title'])
        # Увеличенный заголовок (главный)
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        title_container.addWidget(title_label)
        
        # Процент выполнения до следующего уровня (вертикально под заголовком)
        current = min(total_sent, achievement.get('target', 10))
        target = achievement.get('target', 10)
        progress_to_next = int((current / target) * 100) if target > 0 else 0
        
        # Делаем цвет светлее (добавляем прозрачность и осветляем)
        base_color = QColor(icon_color)
        # Осветляем цвет на 40% (было 30%)
        lighter_color = QColor(
            min(255, base_color.red() + int((255 - base_color.red()) * 0.4)),
            min(255, base_color.green() + int((255 - base_color.green()) * 0.4)),
            min(255, base_color.blue() + int((255 - base_color.blue()) * 0.4))
        )
        lighter_color_str = lighter_color.name()
        
        # Процент как данные (semi-bold)
        percent_label = QLabel(f"{progress_to_next}%")
        percent_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        percent_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background: {primary};
                border-radius: 10px;
                padding: 3px 8px;
            }}
        """)
        percent_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        title_container.addWidget(percent_label)
        
        top_container_layout.addLayout(title_container)
        top_container_layout.addStretch()
        top_container.setLayout(top_container_layout)
        
        layout.addWidget(top_container)
        
        # Виджет "Почти достигнута" только для достижения «Преданность» при прогрессе > 60%
        # Создадим его позже, после добавления карточки в сетку
        if progress_to_next > 60 and achievement.get('id') == 'dedicated':
            self._almost_widget_data = {
                'card': card,
                'icon_color': icon_color,
                'progress': progress_to_next
            }
        else:
            self._almost_widget_data = None
        
        # Отступ перед прогресс-баром (опускаем еще ниже)
        spacer_before_progress = QSpacerItem(0, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addItem(spacer_before_progress)
        
        # Прогресс
        current = min(total_sent, achievement.get('target', 10))
        target = achievement.get('target', 10)
        remaining = max(0, target - current)
        
        progress_container = QVBoxLayout()
        progress_container.setContentsMargins(0, 0, 0, 0)
        progress_container.setSpacing(8)

        # Подсказка над баром
        next_level_name = self.get_next_level_name(target)
        remaining_label = QLabel(
            f"Осталось {remaining} письма до уровня “{next_level_name}”"
            if remaining != 1
            else f"Осталось 1 письмо до уровня “{next_level_name}”"
        )
        # Текст делаем более второстепенным: чуть меньше контраст и обычный/medium вес
        remaining_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        remaining_label.setStyleSheet("color: rgba(45, 27, 61, 190); background: transparent;")
        progress_container.addWidget(remaining_label)

        # Прогресс-бар с делениями 1..target (цвет под цвет достижения)
        progress_bar = TickedProgressBar(target)
        progress_bar.setFixedHeight(22)  # Чуть больше по вертикали
        progress_bar.setValue(current)
        # Используем icon_color для прогресс-бара
        icon_color = achievement.get('icon_color', '#A78BFA')
        # Tooltip с точным текстом
        progress_bar.setToolTip(
            f"Осталось {remaining} письма до уровня “{next_level_name}”"
            if remaining != 1
            else f"Осталось 1 письмо до уровня “{next_level_name}”"
        )
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 11px;
                /* незаполненная часть светлая, но хорошо заметная даже при 0% */
                background-color: rgba(235, 230, 245, 0.95);
                height: 22px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {icon_color},
                    stop:1 {icon_color});
                border-radius: 11px;
            }}
        """)
        progress_container.addWidget(progress_bar)
        layout.addLayout(progress_container)
        
        # Отступ перед кнопкой (чистый спейсер без визуальных элементов)
        spacer = QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addItem(spacer)
        
        # CTA кнопка с иконкой + hover/active состояния
        if remaining > 0:
            # Считаем, сколько % добавит одно письмо до текущей цели
            before_pct = int((current / target) * 100) if target > 0 else 0
            after_pct = int((min(current + 1, target) / target) * 100) if target > 0 else 0
            delta_pct = max(0, after_pct - before_pct)

            cta_button = PremiumCTAButton(f"Отправить письмо (+{delta_pct}% к достижению)")
            cta_button.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
            cta_button.setFixedHeight(40)
            # Иконка слева (монохром)
            mail_pix = create_monochrome_icon("mail", "#FFFFFF", 18)
            cta_button.setIcon(QIcon(mail_pix))
            cta_button.setIconSize(QSize(18, 18))
            cta_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(124, 58, 237, 0.92),
                        stop:1 rgba(167, 139, 250, 0.92));
                    color: white;
                    border: none;
                    border-radius: 20px;
                    padding: 10px 18px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(124, 58, 237, 0.98),
                        stop:1 rgba(167, 139, 250, 0.98));
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(109, 40, 217, 0.98),
                        stop:1 rgba(124, 58, 237, 0.98));
                }
            """)
            cta_button.clicked.connect(self.on_send_email_clicked)
            layout.addWidget(cta_button)
        
        layout.addStretch()
        card.setLayout(layout)
        
        
        return card
    
    def get_next_level_name(self, current_target: int) -> str:
        """Возвращает название следующего уровня"""
        levels = {1: 'Преданность', 10: 'Профессионал', 25: 'Эксперт', 50: 'Мастер'}
        if current_target == 1:
            return 'Преданность'
        elif current_target == 10:
            return 'Профессионал'
        elif current_target == 25:
            return 'Эксперт'
        elif current_target == 50:
            return 'Мастер'
        return 'следующего уровня'
    
    def create_next_level_card(self, achievement: Dict) -> QFrame:
        """Создает карточку следующего уровня как в завершенные достижения"""
        # Второстепенная карточка: легче (без hover)
        card = QFrame()
        card.setObjectName("nextLevelCard")
        card.setFixedHeight(280)  # Чуть больше по вертикали
        card.setStyleSheet("""
            QFrame#nextLevelCard {
                background: rgba(255, 255, 255, 0.72);
                border-radius: 20px;
                border: 2px solid rgba(200, 182, 226, 0.3);
                padding: 0px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(108, 74, 139, 35))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 16)  # Меньше отступ сверху
        layout.setSpacing(10)
        
        # Заголовок (выше)
        title_label = QLabel("Следующий уровень")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title_label)
        
        # Виджет достижения (как в завершенные достижения) - объемнее и темнее
        achievement_frame = QFrame()
        achievement_frame.setStyleSheet("""
            QFrame {
                background: rgba(220, 210, 235, 0.95);
                border-radius: 12px;
                padding: 12px;
                border: 1px solid rgba(180, 160, 210, 0.4);
            }
        """)
        achievement_layout = QHBoxLayout()
        achievement_layout.setContentsMargins(0, 0, 0, 0)
        achievement_layout.setSpacing(10)
        
        # Получаем цвет иконки сначала
        icon_color = achievement.get('icon_color', '#A78BFA')
        
        # Иконка достижения (кастомная) - такого же размера, как в завершённых достижениях
        icon_pixmap = create_achievement_icon(achievement.get('id', ''), icon_color, 46)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        icon_label.setStyleSheet("background: transparent; border: none; padding: 0;")
        icon_label.setFixedSize(52, 52)
        achievement_layout.addWidget(icon_label)
        
        # Кликабельность всего виджета следующего уровня
        achievement_frame.mousePressEvent = lambda a0=None: self.show_achievement_detail(achievement)
        achievement_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        
        # Только название достижения (одним словом) с цветом иконки
        title = QLabel(achievement['title'])
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {icon_color}; background: transparent;")
        text_layout.addWidget(title)
        
        achievement_layout.addLayout(text_layout)
        achievement_layout.addStretch()
        
        achievement_frame.setLayout(achievement_layout)
        layout.addWidget(achievement_frame)
        
        # Превью новой карточки профиля
        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.5);
                border-radius: 12px;
                border: 1px solid rgba(200, 182, 226, 0.4);
                padding: 12px;
            }
        """)
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)
        
        # Заголовок превью
        preview_title = QLabel("Новая карточка профиля")
        preview_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        preview_title.setStyleSheet("color: #2D1B3D; background: transparent;")
        preview_layout.addWidget(preview_title)
        
        # Визуальное превью карточки
        card_preview = QFrame()
        card_preview.setFixedHeight(60)
        card_preview.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(238, 233, 246, 0.9), stop:1 rgba(207, 194, 230, 0.9));
                border-radius: 8px;
                border: 1px solid rgba(167, 139, 250, 0.3);
            }
        """)
        card_preview_layout = QHBoxLayout()
        card_preview_layout.setContentsMargins(8, 8, 8, 8)
        card_preview_layout.setSpacing(8)
        
        # Иконка карточки
        card_icon = QLabel("📇")
        card_icon.setFont(QFont("Segoe UI", 16))
        card_icon.setStyleSheet("background: transparent;")
        card_preview_layout.addWidget(card_icon)
        
        # Текст карточки
        card_text = QLabel("Профиль\nРасширенный")
        card_text.setFont(QFont("Segoe UI", 9))
        card_text.setStyleSheet("color: #6C4A8B; background: transparent;")
        card_preview_layout.addWidget(card_text)
        card_preview_layout.addStretch()
        
        card_preview.setLayout(card_preview_layout)
        preview_layout.addWidget(card_preview)
        
        # Убираем превью награды - она будет показываться в окне деталей
        # preview_frame.setLayout(preview_layout)
        # layout.addWidget(preview_frame)
        
        layout.addStretch()
        card.setLayout(layout)
        return card
    
    def toggle_next_level(self):
        """Переключает видимость следующего уровня (не используется)"""
        pass
    
    def get_previous_target(self, target: int) -> int:
        """Возвращает предыдущий целевой уровень"""
        levels = [1, 10, 25, 50, 100]
        for i, level in enumerate(levels):
            if level == target and i > 0:
                return levels[i - 1]
        return 0
    
    def create_overall_progress_card(self, unlocked: int, total: int, percent: int, total_sent: int) -> QFrame:
        """Создает карточку общего прогресса с круглым прогресс-баром"""
        from PyQt6.QtWidgets import QWidget as QWidgetBase
        from PyQt6.QtCore import QRectF
        
        class CircularProgressWidget(QWidgetBase):
            def __init__(self, percent, parent=None):
                super().__init__(parent)
                self.percent = percent
                # Чуть больше сам виджет
                self.setMinimumSize(190, 190)
                self.setMaximumSize(190, 190)
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Размеры (больше)
                size = min(self.width(), self.height())
                margin = 14
                rect = QRectF(margin, margin, size - 2*margin, size - 2*margin)
                
                # Фон окружности (обводка - тёмно-лиловая)
                bg_pen = QPen(QColor(167, 139, 250), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(bg_pen)
                painter.drawArc(rect, 0, 360 * 16)
                
                # Прогресс (лиловый, чуть светлее обводки)
                progress_pen = QPen(QColor(196, 181, 253), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(progress_pen)
                start_angle = 90 * 16  # Начинаем сверху
                span_angle = -int((self.percent / 100.0) * 360 * 16)
                painter.drawArc(rect, start_angle, span_angle)
                
                # Текст в центре: "X%" — делаем чуть более мягким по контрасту
                painter.setPen(QPen(QColor(91, 75, 122)))
                font = QFont("Segoe UI", 22, QFont.Weight.DemiBold)
                font.setStyleHint(QFont.StyleHint.Monospace)
                painter.setFont(font)
                painter.drawText(rect.adjusted(0, -10, 0, -10), Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")
                painter.setPen(QPen(QColor(108, 90, 139)))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
                painter.drawText(rect.adjusted(0, 30, 0, 30), Qt.AlignmentFlag.AlignCenter, "Общий прогресс")
        
        card = QFrame()
        card.setObjectName("overallProgressCard")
        card.setStyleSheet("""
            QFrame#overallProgressCard {
                background: rgba(255, 255, 255, 0.72);
                border-radius: 20px;
                border: 2px solid rgba(200, 182, 226, 0.3);
                padding: 0px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(108, 74, 139, 35))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel("Общий прогресс")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title_label)

        # Счетчики рядом (✔ ⏳ 🔒)
        # Вычисляем: completed/unlocked, in_progress, locked
        # in_progress: те, где уже есть прогресс (total_sent > prev_target), но еще не unlocked
        targets = [1, 10, 25, 50, 100]
        completed_count = unlocked
        in_progress_count = 0
        locked_count = 0
        for idx, t in enumerate(targets):
            if total_sent >= t:
                continue
            prev = targets[idx - 1] if idx > 0 else 0
            if total_sent > prev:
                in_progress_count += 1
            else:
                locked_count += 1

        stats_box = QFrame()
        stats_box.setStyleSheet("background: transparent;")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(10)

        def _stat_row(icon_type: str, label: str, value: int):
            row = QFrame()
            row.setStyleSheet("background: rgba(245, 240, 255, 0.65); border-radius: 12px;")
            row_l = QHBoxLayout()
            row_l.setContentsMargins(12, 10, 12, 10)
            row_l.setSpacing(10)
            icon_pixmap = create_monochrome_icon(icon_type, "#4B2D6D", 16)
            ic = QLabel()
            ic.setPixmap(icon_pixmap)
            ic.setStyleSheet("background: transparent;")
            row_l.addWidget(ic)
            txt = QLabel(f"{label}: {value}")
            txt.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            txt.setStyleSheet("background: transparent; color: #4B2D6D;")
            row_l.addWidget(txt)
            row_l.addStretch()
            row.setLayout(row_l)
            return row

        stats_layout.addWidget(_stat_row("check", "завершено", completed_count))
        stats_layout.addWidget(_stat_row("clock", "в процессе", in_progress_count))
        stats_layout.addWidget(_stat_row("lock", "заблокировано", locked_count))
        stats_box.setLayout(stats_layout)
        
        # Горизонтальный layout для прогресс-бара и списка достижений
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(12)  # Меньше расстояние, чтобы левее
        
        # Левая часть - круглый прогресс-бар
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        circular_progress = CircularProgressWidget(percent)
        # Круглый прогресс-бар располагаем выше по вертикали
        left_layout.addWidget(circular_progress, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Вместо длинного списка — компактные счетчики (как в макете)
        achievements_list_widget = stats_box
        
        main_content_layout.addLayout(left_layout)
        main_content_layout.addWidget(achievements_list_widget)
        # Оба блока подтягиваем вверх
        main_content_layout.setAlignment(left_layout, Qt.AlignmentFlag.AlignTop)
        main_content_layout.setAlignment(achievements_list_widget, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(main_content_layout)
        
        card.setLayout(layout)
        return card
    
    def show_achievement_detail(self, achievement: Dict):
        """Показывает детали достижения в диалоге"""
        parent_widget = self.main_window if self.main_window else self
        dialog = AchievementDetailDialog(achievement, parent_widget, self)
        dialog.exec()
    
    def create_completed_card(self, completed: List[Dict]) -> QFrame:
        """Создает карточку с завершёнными достижениями (меньше, с выдвигающимся контентом)"""
        card = QFrame()
        card.setObjectName("completedCard")
        card.setStyleSheet("""
            QFrame#completedCard {
                background: rgba(255, 255, 255, 0.72);
                border-radius: 20px;
                border: 2px solid rgba(200, 182, 226, 0.3);
                padding: 0px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(108, 74, 139, 35))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        # Заголовок в начале виджета чуть выше
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(10)
        
        # Заголовок (сверху выше, откреплен)
        title_label = QLabel("Завершённые достижения")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        layout.addWidget(title_label)
        
        # Показываем достижения как вертикальный список со скроллом
        # Для списка нам нужен полный список достижений, чтобы показать locked/active/completed
        username = self._funcs['get_current_username']()
        history = self._funcs['get_email_history'](username) if username else []
        total_sent = len(history)
        all_achievements = [
            {'id': 'first_step', 'title': 'Первый шаг', 'description': 'Отправьте первое письмо', 'unlocked': total_sent >= 1, 'target': 1, 'icon_color': '#A78BFA'},
            {'id': 'dedicated', 'title': 'Преданность', 'description': 'Отправьте 10 писем', 'unlocked': total_sent >= 10, 'target': 10, 'icon_color': '#F97316'},
            {'id': 'professional', 'title': 'Профессионал', 'description': 'Отправьте 25 писем', 'unlocked': total_sent >= 25, 'target': 25, 'icon_color': '#22C55E'},
            {'id': 'expert', 'title': 'Эксперт', 'description': 'Отправьте 50 писем', 'unlocked': total_sent >= 50, 'target': 50, 'icon_color': '#0EA5E9'},
        ]

        # ScrollArea с плавным скроллом
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: rgba(240, 235, 250, 0.5);
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(167, 139, 250, 0.6);
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(167, 139, 250, 0.8);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Контейнер для списка достижений
        list_container = QWidget()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(12)

        def make_tile(ach: Dict):
            tile = QFrame()
            unlocked = bool(ach.get('unlocked'))
            # Без обводки, прозрачный фон
            tile.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border-radius: 16px;
                    border: none;
                }
            """)
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            tile_shadow = QGraphicsDropShadowEffect()
            tile_shadow.setBlurRadius(18)
            tile_shadow.setXOffset(0)
            tile_shadow.setYOffset(6)
            tile_shadow.setColor(QColor(60, 20, 100, 30))
            tile.setGraphicsEffect(tile_shadow)

            tl = QHBoxLayout()
            tl.setContentsMargins(12, 12, 12, 12)
            tl.setSpacing(12)

            # Иконка без обводки
            icon = QLabel()
            icon.setPixmap(create_achievement_icon(ach.get('id', ''), ach.get('icon_color', '#A78BFA') if unlocked else "#9CA3AF", 46))
            icon.setFixedSize(52, 52)
            icon.setStyleSheet("background: transparent; border: none;")
            tl.addWidget(icon)

            # Текст справа от иконки
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(4)

            # Заголовок справа от иконки
            name = QLabel(ach.get('title', ''))
            name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            name.setStyleSheet("color: #2D1B3D; background: transparent; border: none;")
            text_layout.addWidget(name)

            # Дата завершения снизу (только если выполнено)
            if unlocked:
                completion_date = self.get_achievement_completion_date(ach.get('id', ''))
                if completion_date:
                    date_label = QLabel(f"Завершено: {completion_date}")
                    date_label.setFont(QFont("Segoe UI", 9))
                    date_label.setStyleSheet("color: #6C5A8B; background: transparent; border: none;")
                    text_layout.addWidget(date_label)
            # Если не выполнено, ничего не показываем

            tl.addLayout(text_layout)
            tl.addStretch()

            tile.setLayout(tl)

            def _click(a0=None, data=ach):
                self.show_achievement_detail(data)
            tile.mousePressEvent = _click
            return tile

        # Добавляем все достижения в вертикальный список
        for ach in all_achievements[:4]:
            tile = make_tile(ach)
            list_layout.addWidget(tile)

        list_layout.addStretch()
        list_container.setLayout(list_layout)
        scroll_area.setWidget(list_container)
        layout.addWidget(scroll_area)
        
        card.setLayout(layout)
        return card
    
    def toggle_completed(self):
        """Переключает видимость завершённых достижений (не используется)"""
        pass
    
    def show_all_completed(self, completed: List[Dict]):
        """Показывает диалог со всеми завершёнными достижениями"""
        dialog = CompletedAchievementsDialog(completed, self)
        dialog.exec()
    
    def get_achievement_completion_date(self, achievement_id: str) -> Optional[str]:
        """Получает дату завершения достижения"""
        username = self._funcs['get_current_username']()
        if not username:
            return None
        
        # Получаем историю писем
        history = self._funcs['get_email_history'](username)
        if not history:
            return None
        
        # Определяем целевое количество писем для достижения
        targets = {
            'first_step': 1,
            'dedicated': 10,
            'professional': 25,
            'expert': 50,
            'master': 100
        }
        
        target = targets.get(achievement_id)
        if not target:
            return None
        
        # Находим дату, когда было отправлено target-ное письмо
        if len(history) >= target:
            # Берем дату target-ного письма (индекс target-1)
            achievement_email = history[target - 1]
            if isinstance(achievement_email, dict):
                sent_at = achievement_email.get('sent_at') or achievement_email.get('date')
            else:
                sent_at = achievement_email[1] if len(achievement_email) > 1 else None
            
            if sent_at:
                try:
                    from datetime import datetime
                    if isinstance(sent_at, str):
                        if ' ' in sent_at:
                            date_str = sent_at.split(' ')[0]
                        else:
                            date_str = sent_at
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                        # Форматируем как "12 марта"
                        months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                                 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
                        return f"{dt.day} {months[dt.month - 1]}"
                except:
                    pass
        
        return None
    
    def show_achievement_details(self, achievement: Dict):
        """Показывает детали достижения"""
        from PyQt6.QtWidgets import QMessageBox
        
        completion_date = self.get_achievement_completion_date(achievement['id'])
        date_text = f"\nЗавершено: {completion_date}" if completion_date else ""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Детали достижения")
        msg.setText(f"<b>{achievement['title']}</b><br>{achievement['description']}{date_text}")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
    
    def on_send_email_clicked(self):
        """Обработчик клика на кнопку 'Отправить письмо'"""
        if self.main_window:
            # Переключаемся на страницу отправки писем (индекс 1)
            if hasattr(self.main_window, 'switch_page'):
                self.main_window.switch_page(1)
            elif hasattr(self.main_window, 'stacked_widget'):
                self.main_window.stacked_widget.setCurrentIndex(1)
    
    def check_profile_complete(self) -> bool:
        """Проверяет, заполнен ли профиль полностью"""
        user_info = self._funcs['get_user_info']()
        if not user_info or len(user_info) < 2:
            return False
        
        first_name, last_name = user_info[0], user_info[1]
        phone_number = user_info[2] if len(user_info) > 2 else ''
        
        username = self._funcs['get_current_username']()
        has_about_me = False
        if username and self._funcs['DatabaseConnection']:
            try:
                with self._funcs['DatabaseConnection']() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT about_me_profile FROM auth_users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        has_about_me = True
            except:
                pass
        
        return bool(first_name and last_name and phone_number and has_about_me)
    
    def refresh(self):
        """Обновляет страницу достижений"""
        self.load_achievements()
    
    def animate_progress_bar(self, progress_bar: QProgressBar, target_value: int):
        """Анимирует заполнение прогресс-бара"""
        try:
            anim = QPropertyAnimation(progress_bar, b"value")
            anim.setDuration(650)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(0)
            anim.setEndValue(int(target_value))
            anim.start()
            # держим ссылку, чтобы GC не убил анимацию
            if not hasattr(self, "_progress_anims"):
                self._progress_anims = []
            self._progress_anims.append(anim)
        except Exception:
            progress_bar.setValue(target_value)
    
    def showEvent(self, event):
        """Обновляет достижения при открытии страницы"""
        super().showEvent(event)
        QTimer.singleShot(100, self.load_achievements)
