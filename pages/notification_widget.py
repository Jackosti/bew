"""
Всплывающий виджет для уведомлений в стиле приложения
"""
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QColor


class NotificationWidget(QFrame):
    """Всплывающий виджет уведомления в стиле приложения"""
    
    def __init__(self, parent=None, message="", is_success=True):
        super().__init__(parent)
        self.parent_widget = parent
        self.is_success = is_success
        self.setup_ui(message)
        self.setup_animation()
    
    def setup_ui(self, message):
        """Создает интерфейс виджета"""
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(350)
        
        # Контейнер с фоном
        container = QFrame()
        container.setObjectName("notificationContainer")
        container.setStyleSheet("""
            QFrame#notificationContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98), stop:1 rgba(250, 248, 252, 0.98));
                border: 2px solid rgba(108, 77, 255, 0.3);
                border-radius: 16px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        container.setLayout(layout)
        
        # Иконка и текст
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Иконка
        icon_label = QLabel("✓" if self.is_success else "✕")
        icon_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        icon_label.setStyleSheet(f"""
            color: {'#34d399' if self.is_success else '#E14B4B'};
            background: transparent;
        """)
        icon_label.setFixedSize(32, 32)
        content_layout.addWidget(icon_label)
        
        # Текст сообщения
        message_label = QLabel(message)
        message_label.setFont(QFont("Inter", 13, QFont.Weight.Medium))
        message_label.setStyleSheet("color: #2D1B3D; background: transparent;")
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)
        
        layout.addLayout(content_layout)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        
        # Добавляем тень
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(shadow)
        
        self.adjustSize()
    
    def setup_animation(self):
        """Настраивает анимацию появления и исчезновения"""
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def show_notification(self):
        """Показывает уведомление с анимацией"""
        if self.parent_widget:
            # Находим главное окно приложения
            widget = self.parent_widget
            while widget and hasattr(widget, 'parent') and widget.parent():
                widget = widget.parent()
                if hasattr(widget, 'geometry') and hasattr(widget, 'width'):
                    break
            
            # Позиционируем в центре окна
            if widget and hasattr(widget, 'geometry'):
                parent_rect = widget.geometry()
                x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
                y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
                self.move(x, y)
            elif self.parent_widget:
                # Fallback: позиционируем относительно родителя
                parent_rect = self.parent_widget.geometry()
                x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
                y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
                self.move(x, y)
        
        self.show()
        self.raise_()
        self.activateWindow()
        self.opacity_animation.start()
        
        # Автоматически скрываем через 3 секунды
        QTimer.singleShot(3000, self.hide_notification)
    
    def hide_notification(self):
        """Скрывает уведомление с анимацией"""
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.finished.connect(self.deleteLater)
        self.opacity_animation.start()


