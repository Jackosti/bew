"""
Friends System
Production-ready implementation with soft lilac and milky-white color palette
Optimized for performance with clean scalable architecture
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QApplication, QGraphicsDropShadowEffect,
    QScrollArea, QDialog, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QObject, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QPixmap, QPainter, QBrush, QPen, QCursor, QMouseEvent, QRegion
)
import math

# ============================================================================
# Lazy imports and function getters
# ============================================================================

def get_tr():
    """Получает функцию перевода"""
    try:
        # Убеждаемся, что локализация инициализирована
        from email_app import get_localization_manager, tr
        # Принудительно инициализируем менеджер, если еще не инициализирован
        get_localization_manager()
        return tr
    except Exception as e:
        # В случае ошибки возвращаем функцию, которая пытается получить перевод
        def fallback_tr(key):
            try:
                from email_app import tr as real_tr
                return real_tr(key)
            except:
                return key
        return fallback_tr

def get_functions():
    """Получает необходимые функции и константы"""
    try:
        from email_app import (
            get_current_username, get_friends, get_friend_requests,
            get_outgoing_friend_requests, send_friend_request,
            accept_friend_request, reject_friend_request, remove_friend,
            get_friend_stats, get_days_in_app, get_user_info,
            DB_FILE, CURRENT_LANGUAGE
        )
        return {
            'get_current_username': get_current_username,
            'get_friends': get_friends,
            'get_friend_requests': get_friend_requests,
            'get_outgoing_friend_requests': get_outgoing_friend_requests,
            'send_friend_request': send_friend_request,
            'accept_friend_request': accept_friend_request,
            'reject_friend_request': reject_friend_request,
            'remove_friend': remove_friend,
            'get_friend_stats': get_friend_stats,
            'get_days_in_app': get_days_in_app,
            'get_user_info': get_user_info,
            'DB_FILE': DB_FILE,
            'CURRENT_LANGUAGE': CURRENT_LANGUAGE
        }
    except ImportError as e:
        import traceback
        traceback.print_exc()
        return {
            'get_current_username': lambda: None,
            'get_friends': lambda username: [],
            'get_friend_requests': lambda username: [],
            'get_outgoing_friend_requests': lambda username: [],
            'send_friend_request': lambda u1, u2: (False, 'import_error'),
            'accept_friend_request': lambda u1, u2: (False, 'import_error'),
            'reject_friend_request': lambda u1, u2: None,
            'remove_friend': lambda u1, u2: None,
            'get_friend_stats': lambda username: 0,
            'get_days_in_app': lambda username=None: 0,
            'get_user_info': lambda username=None: None,
            'DB_FILE': 'email_app.db',
            'CURRENT_LANGUAGE': 'de'
        }
    except Exception as e:
        print(f"[DEBUG] get_functions: Неожиданная ошибка - {e}")
        import traceback
        traceback.print_exc()
        return {
            'get_current_username': lambda: None,
            'get_friends': lambda username: [],
            'get_friend_requests': lambda username: [],
            'get_outgoing_friend_requests': lambda username: [],
            'send_friend_request': lambda u1, u2: (False, 'import_error'),
            'accept_friend_request': lambda u1, u2: (False, 'import_error'),
            'reject_friend_request': lambda u1, u2: None,
            'remove_friend': lambda u1, u2: None,
            'get_friend_stats': lambda username: 0,
            'get_days_in_app': lambda username=None: 0,
            'get_user_info': lambda username=None: None,
            'DB_FILE': 'email_app.db',
            'CURRENT_LANGUAGE': 'de'
        }

# Initialize functions
_funcs = get_functions()
get_current_username = _funcs['get_current_username']
get_friends = _funcs['get_friends']
get_friend_requests = _funcs['get_friend_requests']
get_outgoing_friend_requests = _funcs['get_outgoing_friend_requests']
send_friend_request = _funcs['send_friend_request']
accept_friend_request = _funcs['accept_friend_request']
reject_friend_request = _funcs['reject_friend_request']
remove_friend = _funcs['remove_friend']
get_friend_stats = _funcs['get_friend_stats']
get_days_in_app = _funcs['get_days_in_app']
get_user_info = _funcs['get_user_info']
DB_FILE = _funcs['DB_FILE']
CURRENT_LANGUAGE = _funcs['CURRENT_LANGUAGE']

# Инициализируем функцию перевода с принудительной инициализацией локализации
tr = get_tr()
# Принудительно инициализируем локализацию при загрузке модуля
try:
    from email_app import get_localization_manager
    get_localization_manager()  # Убеждаемся, что локализация загружена
except:
    pass

# ============================================================================
# Color Palette - Soft Lilac and Milky White
# ============================================================================
COLORS = {
    'bg_primary': '#F5F0FF',      # Soft lilac background
    'bg_secondary': '#FFFFFF',      # Milky white
    'bg_hover': '#F0E8FF',         # Light hover
    'bg_active': '#E8DDFF',        # Active state
    'border': '#E0D0F0',            # Soft border
    'border_hover': '#D4C0E8',      # Border on hover
    'text_primary': '#4A2C6B',     # Dark lilac text
    'text_secondary': '#8B7AA3',   # Secondary text
    'text_tertiary': '#B8A9C8',    # Tertiary text
    'accent': '#9C7BFF',            # Accent purple
    'accent_hover': '#8B6BEF',      # Accent hover
    'online': '#43B581',             # Online green
    'offline': '#747F8D',            # Offline grey
    'success': '#43B581',            # Success green
    'danger': '#F04747',             # Danger red
    'shadow': 'rgba(156, 123, 255, 0.15)',  # Soft shadow
}

# ============================================================================
# Utility Functions
# ============================================================================

def create_rounded_avatar(pixmap: QPixmap, size: int) -> QPixmap:
    """Создает круглый аватар из pixmap"""
    rounded = QPixmap(size, size)
    rounded.fill(QColor(0, 0, 0, 0))
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(pixmap))
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return rounded

def get_user_avatar_path(username: str) -> Optional[str]:
    """Получает путь к аватару пользователя"""
    try:
        user_info = get_user_info(username)
        if user_info:
            # Структура user_info: (first_name, last_name, phone_number, created_at, avatar_path, username, current_status)
            # avatar_path находится на индексе 4
            if isinstance(user_info, (list, tuple)) and len(user_info) > 4:
                avatar_path = user_info[4]  # avatar_path
                if avatar_path and Path(avatar_path).exists():
                    return avatar_path
            elif isinstance(user_info, dict):
                avatar_path = user_info.get('avatar_path') or user_info.get('avatar')
                if avatar_path and Path(avatar_path).exists():
                    return avatar_path
    except Exception as e:
        import traceback
        traceback.print_exc()
    return None

def get_user_frame_path(username: str) -> Optional[str]:
    """Получает путь к рамке пользователя"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT frame_path FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0] and Path(result[0]).exists():
            return result[0]
    except Exception as e:
        pass
    return None

def get_user_about_me(username: str) -> str:
    """Получает описание профиля пользователя"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT about_me FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
    except:
        pass
    return ''

def convert_user_info_tuple_to_dict(user_info_tuple) -> Dict[str, Any]:
    """Преобразует кортеж из get_user_info в словарь"""
    if not user_info_tuple:
        return {}
    if isinstance(user_info_tuple, dict):
        return user_info_tuple
    # Кортеж: (first_name, last_name, phone_number, created_at, avatar_path, username, current_status)
    return {
        'first_name': user_info_tuple[0] if len(user_info_tuple) > 0 else '',
        'last_name': user_info_tuple[1] if len(user_info_tuple) > 1 else '',
        'phone_number': user_info_tuple[2] if len(user_info_tuple) > 2 else '',
        'created_at': user_info_tuple[3] if len(user_info_tuple) > 3 else None,
        'avatar_path': user_info_tuple[4] if len(user_info_tuple) > 4 else None,
        'username': user_info_tuple[5] if len(user_info_tuple) > 5 else '',
        'current_status': user_info_tuple[6] if len(user_info_tuple) > 6 else '',
        'is_online': user_info_tuple[6] == 'online' if len(user_info_tuple) > 6 else False
    }

def get_common_friends(username1: str, username2: str) -> List[Dict[str, Any]]:
    """Получает список общих друзей между двумя пользователями"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Получаем точные username из базы
        cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username1,))
        user1_result = cursor.fetchone()
        if not user1_result:
            conn.close()
            return []
        exact_username1 = user1_result[0]
        
        cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username2,))
        user2_result = cursor.fetchone()
        if not user2_result:
            conn.close()
            return []
        exact_username2 = user2_result[0]
        
        # Получаем друзей первого пользователя
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN user1_username = ? THEN user2_username
                    ELSE user1_username
                END as friend_username
            FROM friendships
            WHERE (user1_username = ? OR user2_username = ?)
            AND status = 'accepted'
        ''', (exact_username1, exact_username1, exact_username1))
        friends1 = {row[0] for row in cursor.fetchall()}
        
        # Получаем друзей второго пользователя
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN user1_username = ? THEN user2_username
                    ELSE user1_username
                END as friend_username
            FROM friendships
            WHERE (user1_username = ? OR user2_username = ?)
            AND status = 'accepted'
        ''', (exact_username2, exact_username2, exact_username2))
        friends2 = {row[0] for row in cursor.fetchall()}
        
        # Находим общих друзей
        common_friends_usernames = friends1.intersection(friends2)
        
        if not common_friends_usernames:
            conn.close()
            return []
        
        # Получаем информацию об общих друзьях
        placeholders = ','.join(['?'] * len(common_friends_usernames))
        cursor.execute(f'''
            SELECT username, first_name, last_name
            FROM auth_users
            WHERE username IN ({placeholders})
        ''', tuple(common_friends_usernames))
        
        common_friends = []
        for row in cursor.fetchall():
            common_friends.append({
                'username': row[0],
                'first_name': row[1] or '',
                'last_name': row[2] or ''
            })
        
        conn.close()
        return common_friends
    except Exception as e:
        return []

def get_user_registration_date(username: str) -> str:
    """Получает дату регистрации пользователя"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT created_at FROM auth_users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            reg_date = result[0]
            try:
                if isinstance(reg_date, str):
                    if ' ' in reg_date:
                        date_str = reg_date.split(' ')[0]
                    else:
                        date_str = reg_date
                    reg_dt = datetime.strptime(date_str, '%Y-%m-%d')
                    return reg_dt.strftime('%d.%m.%Y')
                else:
                    return reg_date.strftime('%d.%m.%Y')
            except:
                return str(reg_date)
    except:
        pass
    return '—'

# ============================================================================
# Custom Tab Button with Text-Width Underline
# ============================================================================

class CustomTabButton(QPushButton):
    """Кастомная кнопка вкладки с подчеркиванием точно по ширине текста"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._underline_color = COLORS['accent']
        self.setCheckable(True)
        self.setFixedHeight(50)
        
    def paintEvent(self, event):
        """Переопределяем отрисовку для подчеркивания по ширине текста"""
        super().paintEvent(event)
        
        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Получаем метрики текста
            font_metrics = self.fontMetrics()
            text_rect = font_metrics.boundingRect(self.text())
            
            # Вычисляем позицию текста (центрированный)
            button_rect = self.rect()
            text_x = (button_rect.width() - text_rect.width()) // 2
            text_y = (button_rect.height() + text_rect.height()) // 2
            
            # Рисуем подчеркивание точно под текстом
            underline_y = button_rect.height() - 2  # 2px от низа
            underline_height = 3
            
            pen = QPen(QColor(self._underline_color))
            pen.setWidth(underline_height)
            painter.setPen(pen)
            painter.drawLine(
                text_x,
                underline_y,
                text_x + text_rect.width(),
                underline_y
            )
            painter.end()

# ============================================================================
# Context Menu Widget
# ============================================================================

class FriendContextMenu(QFrame):
    """Контекстное меню для друга"""
    view_profile = pyqtSignal()
    remove_friend = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(240)
        self.setup_ui()
        
    def setup_ui(self):
        """Создает интерфейс меню"""
        # Фон темнее, без черных краев, полностью закругленное
        menu_bg = "#E8DDFF"  # Темнее чем было
        
        # Текст темнее для лучшей читаемости
        menu_text_color = "#2D1B3D"  # Еще темнее для лучшей читаемости
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {menu_bg};
                border: none;
                border-radius: 16px;
            }}
            QPushButton {{
                border-radius: 12px;
            }}
            QPushButton:first-child {{
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            QPushButton:last-child {{
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
        """)
        
        # Убираем прозрачность
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(156, 123, 255, 100))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # Профиль
        view_btn = QPushButton(tr('view_profile'))
        view_btn.setFixedHeight(36)
        view_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {menu_text_color};
                text-align: left;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
            }}
        """)
        def on_view_clicked():
            self.hide()
            self.view_profile.emit()
        view_btn.clicked.connect(on_view_clicked)
        layout.addWidget(view_btn)
        
        # Separator
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {COLORS['border']}; margin: 2px 0;")
        layout.addWidget(separator)
        
        # Удалить из друзей
        remove_btn = QPushButton(tr('remove_friend'))
        remove_btn.setFixedHeight(36)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: #D84040;
                text-align: left;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(240, 71, 71, 0.1);
            }}
        """)
        def on_remove_clicked():
            self.hide()
            self.remove_friend.emit()
        remove_btn.clicked.connect(on_remove_clicked)
        layout.addWidget(remove_btn)

class RequestContextMenu(QFrame):
    """Контекстное меню для запроса на дружбу"""
    view_profile = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(240)
        self.setup_ui()
        
    def setup_ui(self):
        """Создает интерфейс меню"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_active']};
                border: none;
                border-radius: 8px;
                padding: 4px;
            }}
            QPushButton:first-child {{
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QPushButton:last-child {{
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(156, 123, 255, 80))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Профиль
        view_btn = QPushButton(tr('view_profile'))
        view_btn.setFixedHeight(32)
        view_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_primary']};
                text-align: left;
                padding: 8px 12px;
                border-radius: 0px;
                font-size: 15px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
            }}
        """)
        def on_view_clicked():
            self.hide()
            self.view_profile.emit()
        view_btn.clicked.connect(on_view_clicked)
        layout.addWidget(view_btn)

# ============================================================================
# Friend Profile Widget
# ============================================================================

class FriendProfileWidget(QFrame):
    """Мини-профиль друга"""
    closed = pyqtSignal()
    
    def __init__(self, friend_data: Dict[str, Any], parent=None, friends_page=None):
        super().__init__(parent)
        self.friend_data = friend_data
        self.friends_page = friends_page  # ссылка на FriendsPage для открытия профилей/диалогов
        self.setup_ui()
    
    def get_friend_first_achievement(self, username: str) -> Optional[Dict]:
        """Получает первое достижение друга"""
        try:
            from email_app import get_email_history
            history = get_email_history(username)
            total_sent = len(history) if history else 0
            
            if total_sent >= 1:
                return {'id': 'first_step', 'icon_color': '#A78BFA'}
            return None
        except:
            return None
        
    def setup_ui(self):
        """Создает интерфейс профиля"""
        self.setFixedSize(1200, 580)
        # Фон карточки профиля светлее чем bg_primary (будет использоваться в левой части)
        lighter_bg = "#FAF5FF"  # Чуть светлее чем bg_primary
        # Фон карточки профиля (как в Discord)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: none;
                border-radius: 20px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(156, 123, 255, 100))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # Main content: две панели (слева - профиль, справа - общие друзья)
        main_content = QHBoxLayout()
        main_content.setContentsMargins(40, 0, 0, 0)  # Отступ слева, чтобы был виден фон окна
        main_content.setSpacing(0)
        
        # Left: Profile Card (карточка профиля как задний фон, как в Discord)
        profile_card = QFrame()
        profile_card.setStyleSheet(f"""
            QFrame {{
                background: {lighter_bg};
                border: none;
                border-bottom-left-radius: 20px;
            }}
        """)
        profile_card_layout = QVBoxLayout()
        profile_card_layout.setContentsMargins(40, 30, 40, 40)
        profile_card_layout.setSpacing(0)
        
        # Content внутри карточки профиля
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(40)
        
        # Left: Avatar с карточкой профиля сзади (layered effect)
        avatar_container = QVBoxLayout()
        avatar_container.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        username = self.friend_data.get('username', '')
        avatar_path = get_user_avatar_path(username)
        is_online = self.friend_data.get('is_online', False)
        
        # Карточка профиля сзади аватара (layered effect)
        profile_card_back = QFrame()
        profile_card_back.setFixedSize(200, 240)
        
        # Получаем frame_path друга
        friend_frame_path = get_user_frame_path(username)
        
        # Если есть рамка, используем её как фон, иначе используем стандартный фон
        if friend_frame_path and Path(friend_frame_path).exists():
            try:
                # Загружаем и масштабируем изображение рамки
                frame_pixmap = QPixmap(str(friend_frame_path))
                if not frame_pixmap.isNull():
                    # Масштабируем изображение
                    scaled_pixmap = frame_pixmap.scaled(
                        200, 240,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    # Обрезаем по центру если нужно
                    if scaled_pixmap.width() > 200 or scaled_pixmap.height() > 240:
                        x = (scaled_pixmap.width() - 200) // 2
                        y = (scaled_pixmap.height() - 240) // 2
                        scaled_pixmap = scaled_pixmap.copy(x, y, 200, 240)
                    
                    # Создаем закругленное изображение
                    rounded_pixmap = QPixmap(200, 240)
                    rounded_pixmap.fill(QColor(0, 0, 0, 0))
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setBrush(QBrush(scaled_pixmap))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(0, 0, 200, 240, 16, 16)
                    painter.end()
                    
                    # Устанавливаем прозрачный фон для карточки
                    profile_card_back.setStyleSheet(f"""
                        QFrame {{
                            background: transparent;
                            border-radius: 16px;
                            border: none;
                        }}
                    """)
                    
                    # Создаем QLabel для отображения фона рамки
                    frame_background_label = QLabel(profile_card_back)
                    frame_background_label.setPixmap(rounded_pixmap)
                    frame_background_label.setGeometry(0, 0, 200, 240)
                    frame_background_label.lower()  # Под содержимым
                    frame_background_label.setScaledContents(False)
                    frame_background_label.show()
                else:
                    # Если не удалось загрузить, используем стандартный фон
                    profile_card_back.setStyleSheet(f"""
                        QFrame {{
                            background: {lighter_bg};
                            border-radius: 16px;
                            border: none;
                        }}
                    """)
            except Exception as e:
                # В случае ошибки используем стандартный фон
                profile_card_back.setStyleSheet(f"""
                    QFrame {{
                        background: {lighter_bg};
                        border-radius: 16px;
                        border: none;
                    }}
                """)
        else:
            # Если нет рамки, используем стандартный фон
            profile_card_back.setStyleSheet(f"""
                QFrame {{
                    background: {lighter_bg};
                    border-radius: 16px;
                    border: none;
                }}
            """)
        
        # Тень для карточки
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setXOffset(0)
        card_shadow.setYOffset(4)
        card_shadow.setColor(QColor(156, 123, 255, 60))
        profile_card_back.setGraphicsEffect(card_shadow)
        
        # Layout для карточки
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Контейнер для аватара с индикатором статуса (поверх карточки)
        avatar_wrapper = QFrame(profile_card_back)
        avatar_wrapper.setFixedSize(140, 140)
        avatar_wrapper.setStyleSheet("background: transparent;")
        avatar_wrapper.move(30, 20)  # Позиционируем аватар поверх карточки
        avatar_wrapper_layout = QVBoxLayout()
        avatar_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        avatar_wrapper_layout.setSpacing(0)
        
        # Аватар без фона
        avatar_label = QLabel(avatar_wrapper)
        avatar_label.setFixedSize(140, 140)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        avatar_pixmap = None
        if avatar_path and Path(avatar_path).exists():
            try:
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    if pixmap.width() > 140 or pixmap.height() > 140:
                        x = (pixmap.width() - 140) // 2
                        y = (pixmap.height() - 140) // 2
                        pixmap = pixmap.copy(x, y, 140, 140)
                    avatar_pixmap = create_rounded_avatar(pixmap, 140)
                else:
                    raise Exception("Invalid pixmap")
            except Exception as e:
                avatar_path = None
        
        if avatar_pixmap:
            avatar_label.setPixmap(avatar_pixmap)
        else:
            # Инициалы
            initials = ""
            if self.friend_data.get('first_name') and self.friend_data.get('last_name'):
                initials = f"{self.friend_data['first_name'][0]}{self.friend_data['last_name'][0]}".upper()
            elif self.friend_data.get('first_name'):
                initials = self.friend_data['first_name'][0].upper()
            
            avatar_label.setText(initials)
            avatar_label.setStyleSheet(f"""
                QLabel {{
                    border-radius: 70px;
                    background: {COLORS['accent']};
                    color: white;
                    font-size: 56px;
                    font-weight: bold;
                }}
            """)
        
        avatar_wrapper_layout.addWidget(avatar_label)
        
        # Индикатор статуса (зеленый/серый круг) в правом нижнем углу
        status_indicator = QLabel(avatar_wrapper)
        status_indicator.setFixedSize(20, 20)
        status_color = COLORS['online'] if is_online else COLORS['offline']
        status_indicator.setStyleSheet(f"""
            QLabel {{
                background: {status_color};
                border-radius: 10px;
                border: 3px solid {COLORS['bg_secondary']};
            }}
        """)
        
        # Размещаем индикатор поверх аватара
        status_indicator.move(120, 120)  # Правый нижний угол (140-20=120)
        status_indicator.raise_()
        status_indicator.show()
        
        avatar_wrapper.setLayout(avatar_wrapper_layout)
        
        # Информация профиля на карточке (только username под аватаром)
        card_info_layout = QVBoxLayout()
        card_info_layout.setContentsMargins(15, 175, 15, 15)  # Отступ сверху для аватара (увеличен)
        card_info_layout.setSpacing(8)
        card_info_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Username на карточке (только он)
        card_username_label = QLabel(f"@{username}")
        card_username_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        card_username_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        card_username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_info_layout.addWidget(card_username_label)
        
        card_info_layout.addStretch()
        card_layout.addLayout(card_info_layout)
        profile_card_back.setLayout(card_layout)
        
        avatar_container.addWidget(profile_card_back, alignment=Qt.AlignmentFlag.AlignHCenter)
        content.addLayout(avatar_container)
        
        # Right: Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(18)
        
        # Name с иконкой достижения (только имя и фамилия, без username)
        name_container = QHBoxLayout()
        name_container.setContentsMargins(0, 0, 0, 0)
        name_container.setSpacing(10)
        
        name_label = QLabel(f"{self.friend_data.get('first_name', '')} {self.friend_data.get('last_name', '')}")
        name_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        name_container.addWidget(name_label)
        
        # Иконка достижения справа от имени (если есть)
        friend_achievements = self.get_friend_first_achievement(username)
        if friend_achievements:
            achievement_icon = QLabel()
            try:
                from pages.achievements_page import create_achievement_icon
                icon_pixmap = create_achievement_icon(
                    friend_achievements.get('id', ''),
                    friend_achievements.get('icon_color', '#A78BFA'),
                    24,
                    transparent_background=True  # Прозрачный фон без круга
                )
                achievement_icon.setPixmap(icon_pixmap)
                achievement_icon.setFixedSize(28, 28)
                achievement_icon.setStyleSheet("background: transparent; border: none; padding: 0;")
                name_container.addWidget(achievement_icon)
            except ImportError:
                pass
        
        name_container.addStretch()
        name_widget = QWidget()
        name_widget.setLayout(name_container)
        info_layout.addWidget(name_widget)
        
        # Separator
        separator1 = QFrame()
        separator1.setFixedHeight(2)
        separator1.setStyleSheet(f"background: {COLORS['border']};")
        info_layout.addWidget(separator1)
        
        # About Me
        about_me = get_user_about_me(username)
        if about_me:
            about_header = QLabel(tr("about_me"))
            about_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            about_header.setStyleSheet(f"color: {COLORS['text_primary']}; margin-top: 8px; background: transparent;")
            info_layout.addWidget(about_header)
            
            about_label = QLabel(about_me)
            about_label.setFont(QFont("Segoe UI", 13))
            about_label.setWordWrap(True)
            about_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_secondary']};
                    padding: 10px 14px;
                    background: {lighter_bg};
                    border-radius: 12px;
                    border-left: 3px solid {COLORS['accent']};
                }}
            """)
            about_label.setMaximumHeight(100)
            info_layout.addWidget(about_label)
        
        # Separator
        separator2 = QFrame()
        separator2.setFixedHeight(2)
        separator2.setStyleSheet(f"background: {COLORS['border']};")
        info_layout.addWidget(separator2)
        
        # Registration date
        reg_date = get_user_registration_date(username)
        reg_label = QLabel(f"{tr('registration_date')}: {reg_date}")
        reg_label.setFont(QFont("Segoe UI", 10))
        reg_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; padding: 4px 0;")
        info_layout.addWidget(reg_label)
        
        info_layout.addStretch()
        content.addLayout(info_layout)
        
        profile_card_layout.addLayout(content)
        profile_card.setLayout(profile_card_layout)
        main_content.addWidget(profile_card)
        
        # Right: Common Friends Panel (панель с общими друзьями)
        try:
            from email_app import get_current_username
            current_username = get_current_username()
            if current_username:
                common_friends = get_common_friends(current_username, username)
                common_friends_count = len(common_friends)
            else:
                common_friends = []
                common_friends_count = 0
        except:
            common_friends = []
            common_friends_count = 0
        
        # Правая часть - только текст и аватарки, без виджетов
        right_content = QVBoxLayout()
        right_content.setContentsMargins(40, 30, 40, 40)
        right_content.setSpacing(20)
        
        # Заголовок "Активность"
        activity_header = QLabel("Активность")
        activity_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        activity_header.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        right_content.addWidget(activity_header)
        
        # Количество отправленных писем и последняя отправка
        messages_count = get_friend_stats(username)
        last_sent_str = ""
        try:
            from email_app import get_email_history
            history = get_email_history(username)
            if history:
                # history[0] - последняя отправка (отсортировано по DESC)
                entry = history[0]
                # Формат: (id, sent_at, recipient_email, lehrstelle)
                sent_at = entry[1] if len(entry) > 1 else None
                if sent_at:
                    try:
                        dt = datetime.strptime(sent_at, "%Y-%m-%d %H:%M:%S")
                        last_sent_str = dt.strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        last_sent_str = str(sent_at)
        except Exception:
            last_sent_str = ""
        messages_text = QLabel(f"✉ Отправлено писем: {messages_count}")
        messages_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        messages_text.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; padding: 0;")
        right_content.addWidget(messages_text)
        
        if last_sent_str:
            last_sent_label = QLabel(f"Последняя отправка: {last_sent_str}")
        else:
            last_sent_label = QLabel("Последняя отправка: —")
        last_sent_label.setFont(QFont("Segoe UI", 11))
        last_sent_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; padding-top: 2px;")
        right_content.addWidget(last_sent_label)
        
        right_content.addSpacing(16)
        
        # Заголовок "Общие друзья"
        friends_header = QLabel(f"{common_friends_count} общих друзей")
        # Делаем заголовок чуть менее массивным, чтобы весь блок казался компактнее
        friends_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        friends_header.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        right_content.addWidget(friends_header)
        
        # Список общих друзей - кликабельные виджеты
        if common_friends_count == 0:
            empty_text = QLabel("Нет общих друзей")
            empty_text.setFont(QFont("Segoe UI", 12))
            empty_text.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; padding: 0;")
            right_content.addWidget(empty_text)
        else:
            for friend in common_friends:
                # Кликабельный виджет для каждого общего друга
                friend_widget = QFrame()
                friend_widget.setCursor(Qt.CursorShape.PointingHandCursor)
                friend_widget.setStyleSheet(f"""
                    QFrame {{
                        background: transparent;
                        border: none;
                        border-radius: 8px;
                        padding: 8px;
                    }}
                    QFrame:hover {{
                        background: {COLORS['bg_hover']};
                    }}
                """)
                
                friend_layout = QHBoxLayout()
                # Блок общих друзей делаем компактнее: меньше высота и отступы
                friend_layout.setSpacing(6)
                friend_layout.setContentsMargins(0, 2, 0, 2)
                
                # Контейнер для аватара со статусом
                avatar_container = QFrame()
                avatar_container.setFixedSize(44, 44)
                avatar_container.setStyleSheet("background: transparent; border: none;")
                
                # Аватарка (увеличена с 40 до 48)
                friend_username = friend.get('username', '')
                avatar_path = get_user_avatar_path(friend_username)
                
                # Получаем статус онлайн для общего друга
                is_online = False
                try:
                    from email_app import get_user_info
                    friend_info_tuple = get_user_info(friend_username)
                    if friend_info_tuple:
                        friend_info_dict = convert_user_info_tuple_to_dict(friend_info_tuple)
                        is_online = friend_info_dict.get('is_online', False)
                except:
                    pass
                
                avatar_label = QLabel(avatar_container)
                avatar_label.setFixedSize(40, 40)
                avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                avatar_label.move(2, 2)
                
                if avatar_path and Path(avatar_path).exists():
                    try:
                        pixmap = QPixmap(avatar_path)
                        if not pixmap.isNull():
                            pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                            if pixmap.width() > 40 or pixmap.height() > 40:
                                x = (pixmap.width() - 40) // 2
                                y = (pixmap.height() - 40) // 2
                                pixmap = pixmap.copy(x, y, 40, 40)
                            rounded = create_rounded_avatar(pixmap, 40)
                            avatar_label.setPixmap(rounded)
                        else:
                            raise Exception("Invalid pixmap")
                    except:
                        # Fallback на инициалы
                        initials = ""
                        if friend.get('first_name'):
                            initials = friend['first_name'][0].upper()
                        avatar_label.setText(initials)
                        avatar_label.setStyleSheet(f"""
                            QLabel {{
                                border-radius: 20px;
                                background: {COLORS['accent']};
                                color: white;
                                font-size: 18px;
                                font-weight: bold;
                            }}
                        """)
                else:
                    # Инициалы
                    initials = ""
                    if friend.get('first_name'):
                        initials = friend['first_name'][0].upper()
                    avatar_label.setText(initials)
                    avatar_label.setStyleSheet(f"""
                        QLabel {{
                            border-radius: 20px;
                            background: {COLORS['accent']};
                            color: white;
                            font-size: 16px;
                            font-weight: bold;
                        }}
                    """)
                
                # Индикатор статуса сети (зеленый/серый круг) в правом нижнем углу
                status_indicator = QLabel(avatar_container)
                status_indicator.setFixedSize(12, 12)
                status_color = COLORS['online'] if is_online else COLORS['offline']
                status_indicator.setStyleSheet(f"""
                    QLabel {{
                        background: {status_color};
                        border-radius: 6px;
                        border: 2px solid {COLORS['bg_secondary']};
                    }}
                """)
                # Позиционируем в правом нижнем углу более компактного контейнера
                status_indicator.move(44 - 14, 44 - 14)
                status_indicator.raise_()
                status_indicator.show()
                
                friend_layout.addWidget(avatar_container)
                
                # Имя и username - просто текст
                friend_name = f"{friend.get('first_name', '')} {friend.get('last_name', '')}".strip()
                if not friend_name:
                    friend_name = friend_username
                
                name_text = QLabel(friend_name)
                name_text.setFont(QFont("Segoe UI", 13))
                name_text.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
                friend_layout.addWidget(name_text)
                
                friend_layout.addStretch()
                friend_widget.setLayout(friend_layout)
                
                # Обработчик клика для открытия профиля общего друга
                def create_click_handler(friend_data):
                    def on_click(event):
                        if event.button() == Qt.MouseButton.LeftButton:
                            try:
                                from email_app import get_user_info
                                friend_info_tuple = get_user_info(friend_data.get('username', ''))
                                if friend_info_tuple:
                                    friend_info = convert_user_info_tuple_to_dict(friend_info_tuple)
                                    if self.friends_page and hasattr(self.friends_page, 'show_friend_profile'):
                                        # Открываем профиль общего друга
                                        QTimer.singleShot(0, lambda info=friend_info: self.friends_page.show_friend_profile(info))
                            except Exception as e:
                                import traceback
                                traceback.print_exc()
                    return on_click
                
                friend_widget.mousePressEvent = create_click_handler(friend)
                right_content.addWidget(friend_widget)
        
        right_content.addStretch()
        
        # Простой виджет-контейнер для правой части (без фона)
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_widget.setLayout(right_content)
        main_content.addWidget(right_widget)
        
        layout.addLayout(main_content)
    
    def _create_common_friend_widget(self, friend_data: Dict[str, Any], profile_username: str) -> QFrame:
        """Создает виджет друга в списке общих друзей"""
        friend_frame = QFrame()
        friend_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        friend_frame.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }}
            QFrame:hover {{
                background: {COLORS['bg_hover']};
            }}
        """)
        
        friend_layout = QHBoxLayout()
        friend_layout.setContentsMargins(8, 8, 8, 8)
        friend_layout.setSpacing(12)
        
        # Аватар
        avatar_label = QLabel()
        avatar_label.setFixedSize(40, 40)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        friend_username = friend_data.get('username', '')
        avatar_path = get_user_avatar_path(friend_username)
        
        if avatar_path and Path(avatar_path).exists():
            try:
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    if pixmap.width() > 40 or pixmap.height() > 40:
                        x = (pixmap.width() - 40) // 2
                        y = (pixmap.height() - 40) // 2
                        pixmap = pixmap.copy(x, y, 40, 40)
                    rounded = create_rounded_avatar(pixmap, 40)
                    avatar_label.setPixmap(rounded)
                else:
                    raise Exception("Invalid pixmap")
            except:
                # Fallback на инициалы
                initials = ""
                if friend_data.get('first_name'):
                    initials = friend_data['first_name'][0].upper()
                avatar_label.setText(initials)
                avatar_label.setStyleSheet(f"""
                    QLabel {{
                        border-radius: 20px;
                        background: {COLORS['accent']};
                        color: white;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                """)
        else:
            # Инициалы
            initials = ""
            if friend_data.get('first_name'):
                initials = friend_data['first_name'][0].upper()
            avatar_label.setText(initials)
            avatar_label.setStyleSheet(f"""
                QLabel {{
                    border-radius: 20px;
                    background: {COLORS['accent']};
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
        
        friend_layout.addWidget(avatar_label)
        
        # Имя и username
        name_layout = QVBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(2)
        
        friend_name = f"{friend_data.get('first_name', '')} {friend_data.get('last_name', '')}".strip()
        if not friend_name:
            friend_name = friend_username
        
        name_label = QLabel(friend_name)
        name_label.setFont(QFont("Segoe UI", 13))
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none; padding: 0;")
        name_layout.addWidget(name_label)
        
        username_label = QLabel(f"@{friend_username}")
        username_label.setFont(QFont("Segoe UI", 11))
        username_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; padding: 0;")
        name_layout.addWidget(username_label)
        
        friend_layout.addLayout(name_layout)
        friend_layout.addStretch()
        
        friend_frame.setLayout(friend_layout)
        
        # Обработчики кликов
        def on_mouse_press(event: QMouseEvent):
            """Обрабатывает клики мыши"""
            if event.button() == Qt.MouseButton.LeftButton:
                # ЛКМ - открываем профиль друга
                try:
                    from email_app import get_user_info
                    friend_info_tuple = get_user_info(friend_username)
                    if friend_info_tuple:
                        friend_info = convert_user_info_tuple_to_dict(friend_info_tuple)
                        if self.friends_page and hasattr(self.friends_page, 'show_friend_profile'):
                            # Открываем после выхода из обработчика, чтобы не удалять overlay во время клика
                            QTimer.singleShot(0, lambda info=friend_info: self.friends_page.show_friend_profile(info))
                except Exception as e:
                    import traceback
                    traceback.print_exc()
            elif event.button() == Qt.MouseButton.RightButton:
                # ПКМ - показываем контекстное меню
                try:
                    from email_app import get_current_username, get_user_info
                    current_username = get_current_username()
                    if not current_username:
                        return
                    
                    # Создаем контекстное меню (только parent)
                    menu = FriendContextMenu(self)
                    
                    # Подключаем сигналы
                    def on_view_profile():
                        friend_info_tuple = get_user_info(friend_username)
                        if friend_info_tuple:
                            friend_info = convert_user_info_tuple_to_dict(friend_info_tuple)
                            if self.friends_page and hasattr(self.friends_page, 'show_friend_profile'):
                                QTimer.singleShot(0, lambda info=friend_info: self.friends_page.show_friend_profile(info))
                    
                    def on_remove_friend():
                        friend_info_tuple = get_user_info(friend_username)
                        friend_info = convert_user_info_tuple_to_dict(friend_info_tuple) if friend_info_tuple else None
                        if friend_info and self.friends_page and hasattr(self.friends_page, 'show_remove_dialog'):
                            # Открываем confirm-диалог удаления в FriendsPage (там уже вся логика обновлений)
                            QTimer.singleShot(0, lambda info=friend_info: self.friends_page.show_remove_dialog(info))
                    
                    menu.view_profile.connect(on_view_profile)
                    menu.remove_friend.connect(on_remove_friend)
                    
                    menu_pos = friend_frame.mapToGlobal(event.pos())
                    menu.move(menu_pos)
                    menu.show()
                except Exception as e:
                    import traceback
                    traceback.print_exc()
        
        friend_frame.mousePressEvent = on_mouse_press
        
        return friend_frame

# ============================================================================
# Friend Card Widget
# ============================================================================

class FriendCard(QFrame):
    """Карточка друга"""
    context_menu_requested = pyqtSignal(QPoint)
    profile_requested = pyqtSignal()
    
    def __init__(self, friend_data: Dict[str, Any], show_status: bool = True, parent=None):
        super().__init__(parent)
        self.friend_data = friend_data
        self.show_status = show_status
        self.setup_ui()
    
    def get_friend_first_achievement(self, username: str) -> Optional[Dict]:
        """Получает первое достижение друга"""
        try:
            from email_app import get_email_history
            history = get_email_history(username)
            total_sent = len(history) if history else 0
            
            if total_sent >= 1:
                return {'id': 'first_step', 'icon_color': '#A78BFA'}
            return None
        except:
            return None
        
    def setup_ui(self):
        """Создает интерфейс карточки"""
        # Карточку делаем чуть компактнее по высоте, но сохраняем "ощущение массы"
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 0.3);
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QFrame:hover {{
                background: rgba(255, 255, 255, 0.4);
                border: 1px solid {COLORS['border_hover']};
            }}
        """)
        
        layout = QHBoxLayout()
        # Немного уменьшаем внутренние отступы и расстояния, чтобы карточка казалась ниже (~15‑20%)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Avatar container with status indicator (круг возле аватара)
        avatar_container = QFrame()
        # Контейнер под аватар делаем немного больше, чтобы сам аватар стал крупнее
        avatar_container.setFixedSize(56, 56)
        avatar_container.setStyleSheet("background: transparent; border: none;")
        
        username = self.friend_data.get('username', '')
        avatar_path = get_user_avatar_path(username)
        is_online = self.friend_data.get('is_online', False)
        
        avatar_label = QLabel(avatar_container)
        # Увеличиваем сам аватар примерно на 10–15%
        avatar_label.setFixedSize(48, 48)
        avatar_label.move(4, 4)  # Смещаем влево чтобы справа было место для статуса
        
        if avatar_path and Path(avatar_path).exists():
            try:
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    if pixmap.width() > 48 or pixmap.height() > 48:
                        x = (pixmap.width() - 48) // 2
                        y = (pixmap.height() - 48) // 2
                        pixmap = pixmap.copy(x, y, 48, 48)
                    rounded = create_rounded_avatar(pixmap, 48)
                    avatar_label.setPixmap(rounded)
                else:
                    raise Exception("Invalid pixmap")
            except Exception as e:
                avatar_path = None  # Fallback to initials
        else:
            initials = ""
            if self.friend_data.get('first_name') and self.friend_data.get('last_name'):
                initials = f"{self.friend_data['first_name'][0]}{self.friend_data['last_name'][0]}".upper()
            elif self.friend_data.get('first_name'):
                initials = self.friend_data['first_name'][0].upper()
            avatar_label.setText(initials)
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_label.setStyleSheet(f"""
                QLabel {{
                    border-radius: 24px;
                    background: {COLORS['accent']};
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    border: none;
                }}
            """)
        
        # Статус сети как круг возле аватара (снизу справа)
        status_indicator = QLabel(avatar_container)
        # Увеличиваем индикатор онлайна на 30–50%
        status_indicator.setFixedSize(16, 16)
        # Цвета статуса — строго заданные монохромные
        status_color = "#10B981" if is_online else "#9CA3AF"
        status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                border-radius: 8px;
                border: 2px solid {COLORS['bg_primary']};
            }}
        """)
        # Позиционируем в правом нижнем углу контейнера
        status_indicator.move(56 - 16, 56 - 16)
        status_indicator.raise_()
        status_indicator.show()
        
        layout.addWidget(avatar_container)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(f"{self.friend_data.get('first_name', '')} {self.friend_data.get('last_name', '')}")
        name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none; padding: 0;")
        info_layout.addWidget(name_label)
        
        # Username без иконки достижения (иконка только в профиле друга при просмотре)
        username_label = QLabel(f"@{username}")
        username_label.setFont(QFont("Segoe UI", 11))
        username_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; padding: 0;")
        info_layout.addWidget(username_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Menu button
        menu_btn = QPushButton("⋯")
        menu_btn.setFixedSize(28, 28)
        menu_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
                background: {COLORS['bg_hover']};
                border-radius: 8px;
            }}
        """)
        menu_btn.clicked.connect(lambda: self.context_menu_requested.emit(menu_btn.mapToGlobal(menu_btn.rect().bottomRight())))
        layout.addWidget(menu_btn)
        
        # Right-click context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested.emit)

# ============================================================================
# Request Card Widget
# ============================================================================

class RequestCard(QFrame):
    """Карточка запроса на дружбу"""
    accepted = pyqtSignal(str)
    rejected = pyqtSignal(str)
    profile_requested = pyqtSignal(dict)
    context_menu_requested = pyqtSignal(QPoint)
    
    def __init__(self, request_data: Dict[str, Any], is_outgoing: bool = False, parent=None):
        super().__init__(parent)
        self.request_data = request_data
        self.is_outgoing = is_outgoing
        self.setup_ui()
        
        # Right-click context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested.emit)
        
    def setup_ui(self):
        """Создает интерфейс карточки"""
        if self.is_outgoing:
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['bg_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 12px;
                }}
            """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Avatar
        avatar_label = QLabel()
        size = 36 if self.is_outgoing else 40
        avatar_label.setFixedSize(size, size)
        
        username = self.request_data.get('username', '')
        avatar_path = get_user_avatar_path(username)
        
        if avatar_path and Path(avatar_path).exists():
            try:
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    if pixmap.width() > size or pixmap.height() > size:
                        x = (pixmap.width() - size) // 2
                        y = (pixmap.height() - size) // 2
                        pixmap = pixmap.copy(x, y, size, size)
                    rounded = create_rounded_avatar(pixmap, size)
                    avatar_label.setPixmap(rounded)
                else:
                    raise Exception("Invalid pixmap")
            except Exception as e:
                avatar_path = None  # Fallback to initials
        else:
            initials = ""
            if self.request_data.get('first_name') and self.request_data.get('last_name'):
                initials = f"{self.request_data['first_name'][0]}{self.request_data['last_name'][0]}".upper()
            elif self.request_data.get('first_name'):
                initials = self.request_data['first_name'][0].upper()
            avatar_label.setText(initials)
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_label.setStyleSheet(f"""
                QLabel {{
                    border-radius: {size // 2}px;
                    background: {COLORS['accent']};
                    color: white;
                    font-weight: bold;
                    font-size: {size // 3}px;
                }}
            """)
        
        layout.addWidget(avatar_label)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(f"{self.request_data.get('first_name', '')} {self.request_data.get('last_name', '')}")
        name_label.setFont(QFont("Segoe UI", 12 if self.is_outgoing else 13, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none; padding: 0;")
        info_layout.addWidget(name_label)
        
        username_label = QLabel(f"@{username}")
        username_label.setFont(QFont("Segoe UI", 10 if self.is_outgoing else 11))
        username_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; padding: 0;")
        info_layout.addWidget(username_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Buttons
        if self.is_outgoing:
            # Cancel button (эмодзи креста, видимый)
            cancel_btn = QPushButton("❌")
            cancel_btn.setFixedSize(32, 32)
            cancel_btn.setToolTip(tr("cancel"))
            cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['danger']};
                    border: none;
                    border-radius: 8px;
                    font-size: 20px;
                }}
                QPushButton:hover {{
                    background: rgba(240, 71, 71, 0.15);
                    color: #D84040;
                }}
            """)
            cancel_btn.clicked.connect(lambda: self.rejected.emit(username))
            layout.addWidget(cancel_btn)
            
            # При клике на виджет открываем профиль
            def on_card_clicked(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.profile_requested.emit(self.request_data)
            
            self.mousePressEvent = on_card_clicked
        else:
            buttons_layout = QHBoxLayout()
            buttons_layout.setSpacing(8)
            
            accept_btn = QPushButton(tr("accept"))
            accept_btn.setFixedHeight(30)
            accept_btn.setFixedWidth(90)
            accept_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['success']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #3AA372;
                }}
            """)
            accept_btn.clicked.connect(lambda: self.accepted.emit(username))
            buttons_layout.addWidget(accept_btn)
            
            reject_btn = QPushButton(tr("reject"))
            reject_btn.setFixedHeight(30)
            reject_btn.setFixedWidth(90)
            reject_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['danger']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #D84040;
                }}
            """)
            reject_btn.clicked.connect(lambda: self.rejected.emit(username))
            buttons_layout.addWidget(reject_btn)
            
            layout.addLayout(buttons_layout)

# ============================================================================
# Main Friends Page
# ============================================================================

class FriendsPage(QWidget):
    """Главная страница друзей"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.is_active = False
        self.context_menu = None
        self.profile_overlay = None
        self.profile_widget = None
        self.remove_dialog = None
        self.add_dialog = None
        self.current_tab = 'online'
        self.friends_cache = []
        self._cached_username = None  # Кеш для username
        self._search_timer = None  # Таймер для дебаунсинга поиска
        self.setup_ui()
        
    def setup_ui(self):
        """Создает интерфейс страницы"""
        # Убеждаемся, что локализация инициализирована перед созданием UI
        try:
            from email_app import get_localization_manager
            get_localization_manager()
        except:
            pass
        
        # Устанавливаем фон через менеджер тем (как в profile_page.py)
        from email_app import get_app_colors
        colors = get_app_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['main_window_bg_start']},
                    stop:0.4 {colors['main_window_bg_mid']},
                    stop:1 {colors['main_window_bg_end']});
                font-family: "Segoe UI", "Inter", sans-serif;
                color: {colors['text_primary']};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # Top bar with icon, title, tabs and add button (как на фото)
        top_bar = QFrame()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20, 0, 20, 0)
        top_layout.setSpacing(0)
        
        # Иконка и заголовок "Друзья" + стрелка вниз (слева, как на фото)
        icon_container = QHBoxLayout()
        icon_container.setSpacing(8)
        icon_container.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        icon_container.setContentsMargins(0, 0, 0, 0)
        
        # Иконка двух фигур (монохромная, простой символ)
        icon_label = QLabel("●")
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 14px; background: transparent; color: {COLORS['accent']}; padding: 0; border: none; font-weight: bold;")
        icon_container.addWidget(icon_label)
        
        # Текст "Друзья" (такой же цвет и размер как у вкладок, но жирным)
        self.title_label = QLabel(tr("friends"))
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; padding: 0; border: none;")
        icon_container.addWidget(self.title_label)
        
        # Стрелка вниз (chevron, светло-серая)
        chevron_label = QLabel("▼")
        chevron_label.setFixedSize(12, 12)
        chevron_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chevron_label.setStyleSheet(f"font-size: 10px; background: transparent; color: {COLORS['text_secondary']}; padding: 0; border: none;")
        icon_container.addWidget(chevron_label)
        
        icon_widget = QWidget()
        icon_widget.setStyleSheet("background: transparent; border: none;")
        icon_widget.setLayout(icon_container)
        top_layout.addWidget(icon_widget)
        
        # Отступ между иконкой и вкладками
        top_layout.addSpacing(24)
        
        # Tabs (в центре, как на фото)
        self.tab_online = QPushButton(tr("online"))
        self.tab_online.setObjectName("friendsTab")
        self.tab_online.setCheckable(True)
        self.tab_online.setChecked(True)
        self.tab_online.clicked.connect(lambda: self.switch_tab('online'))
        
        self.tab_all = QPushButton(tr("all"))
        self.tab_all.setObjectName("friendsTab")
        self.tab_all.setCheckable(True)
        self.tab_all.clicked.connect(lambda: self.switch_tab('all'))
        
        self.tab_pending = QPushButton(tr("pending"))
        self.tab_pending.setObjectName("friendsTab")
        self.tab_pending.setCheckable(True)
        self.tab_pending.clicked.connect(lambda: self.switch_tab('pending'))
        
        top_layout.addWidget(self.tab_online)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.tab_all)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.tab_pending)
        top_layout.addSpacing(16)
        
        # Add friend button (вместе с вкладками, темнее)
        self.add_btn = QPushButton(tr("add_friend"))
        self.add_btn.setCheckable(False)
        self.add_btn.setFixedHeight(36)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: #9C7BFF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #8B6BEF;
            }}
        """)
        self.add_btn.clicked.connect(self.show_add_friend_dialog)
        
        top_layout.addWidget(self.add_btn)
        
        # Растягиваем пространство справа
        top_layout.addStretch()
        
        top_bar.setLayout(top_layout)
        layout.addWidget(top_bar)
        
        self.update_tab_styles()
        
        # Search bar (в стиле из фото - с фоном, иконкой слева, текст слева)
        self.search_frame = QFrame()
        self.search_frame.setFixedHeight(65)
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(20, 12, 20, 12)
        search_layout.setSpacing(0)
        search_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Контейнер для поля поиска с фоном, обводкой и закругленными углами
        search_container = QFrame()
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        search_container_layout = QHBoxLayout()
        search_container_layout.setContentsMargins(12, 0, 12, 0)
        search_container_layout.setSpacing(6)
        search_container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Иконка поиска внутри поля (слева, прозрачная, чуть больше)
        # Создаем простую иконку лупы с прозрачным центром
        search_icon_pixmap = QPixmap(18, 18)
        search_icon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(search_icon_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#8B7AA3"), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(Qt.GlobalColor.transparent))
        # Рисуем круг (линза) с прозрачным центром
        painter.drawEllipse(2, 2, 10, 10)
        # Рисуем ручку (диагональная линия)
        painter.drawLine(10, 10, 16, 16)
        painter.end()
        
        search_icon = QLabel()
        search_icon.setFixedSize(18, 18)
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_icon.setPixmap(search_icon_pixmap)
        search_icon.setStyleSheet("background: transparent; border: none;")
        search_container_layout.addWidget(search_icon)
        
        # Поле поиска с текстом слева возле иконки, по центру по высоте
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search"))
        self.search_input.setFixedHeight(40)
        self.search_input.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                font-size: 15px;
                color: {COLORS['text_primary']};
                padding: 0;
                margin: 0;
            }}
            QLineEdit:focus {{
                background: transparent;
            }}
            QLineEdit::placeholder {{
                color: #8B7AA3;
            }}
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_container_layout.addWidget(self.search_input, stretch=1)
        search_container.setLayout(search_container_layout)
        
        search_layout.addWidget(search_container, stretch=1)
        self.search_frame.setLayout(search_layout)
        # Убираем фиолетовую линию снизу
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.search_frame)
        
        # Content area with scroll (прозрачная, чтобы был виден gradient)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_secondary']};
                width: 10px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: transparent;")
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(8)
        self.content_widget.setLayout(self.content_layout)
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        # Status messages
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background: {COLORS['accent']};
                padding: 12px 18px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self.status_label)
        
        # Load data
        QTimer.singleShot(100, self.activate)
    
    def update_tab_styles(self):
        """Обновляет стили вкладок - при выборе только жирным, размер как при наведении"""
        style_normal = f"""
            QPushButton#friendsTab {{
                background: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 14px;
                font-weight: 500;
                /* уменьшаем высоту вкладок примерно на 30–40% */
                padding: 6px 14px;
                min-height: 26px;
                border-radius: 8px;
            }}
            QPushButton#friendsTab:hover {{
                color: #3A1C5B;
                background: {COLORS['bg_hover']};
                border-radius: 10px;
                font-size: 14px;
                padding: 6px 14px;
                min-height: 26px;
            }}
        """
        style_checked = f"""
            QPushButton#friendsTab {{
                background: transparent;
                border: 1px solid #B89CC8;
                border-radius: 8px;
                color: {COLORS['text_primary']};
                font-size: 14px;
                font-weight: 700;
                padding: 6px 14px;
                min-height: 26px;
            }}
            QPushButton#friendsTab:hover {{
                background: {COLORS['bg_hover']};
                color: #3A1C5B;
                border: 1px solid {COLORS['border_hover']};
                border-radius: 10px;
                font-size: 14px;
                padding: 6px 14px;
                min-height: 26px;
            }}
        """
        # Применяем стили в зависимости от состояния
        self.tab_online.setStyleSheet(style_checked if self.tab_online.isChecked() else style_normal)
        self.tab_all.setStyleSheet(style_checked if self.tab_all.isChecked() else style_normal)
        self.tab_pending.setStyleSheet(style_checked if self.tab_pending.isChecked() else style_normal)
    
    def update_texts(self):
        """Обновляет тексты при смене языка"""
        # Обновляем заголовок
        if hasattr(self, 'title_label'):
            self.title_label.setText(tr("friends"))
        
        # Обновляем вкладки
        if hasattr(self, 'tab_online'):
            self.tab_online.setText(tr("online"))
        if hasattr(self, 'tab_all'):
            self.tab_all.setText(tr("all"))
        if hasattr(self, 'tab_pending'):
            self.tab_pending.setText(tr("pending"))
        
        # Обновляем кнопку добавления друга
        if hasattr(self, 'add_btn'):
            self.add_btn.setText(tr("add_friend"))
        
        # Обновляем placeholder поиска
        if hasattr(self, 'search_input'):
            self.search_input.setPlaceholderText(tr("search"))
    
    def switch_tab(self, tab_name: str):
        """Переключает вкладки"""
        self.current_tab = tab_name
        self.tab_online.setChecked(tab_name == 'online')
        self.tab_all.setChecked(tab_name == 'all')
        self.tab_pending.setChecked(tab_name == 'pending')
        self.update_tab_styles()
        # Показываем строку поиска (она скрыта только в окне добавления)
        if hasattr(self, 'search_frame'):
            self.search_frame.show()
        self.load_current_tab()
    
    def get_current_username_safe(self):
        """Безопасное получение текущего username с кешированием"""
        # Используем кеш, чтобы не делать лишние запросы
        if hasattr(self, '_cached_username') and self._cached_username:
            return self._cached_username
        
        try:
            username = get_current_username()
            if username:
                self._cached_username = username
                return username
        except Exception as e:
            pass
        
        # Пробуем получить напрямую из базы данных
        try:
            import sqlite3
            from email_app import DB_FILE, get_machine_id
            machine_id = get_machine_id()
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM remembered_users WHERE machine_id = ?', (machine_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                self._cached_username = result[0]
                return result[0]
        except Exception as e:
            pass
        
        return None
    
    def load_current_tab(self):
        """Загружает текущую вкладку"""
        if self.current_tab == 'online':
            self.load_online_friends()
        elif self.current_tab == 'all':
            self.load_all_friends()
        elif self.current_tab == 'pending':
            self.load_pending_requests()
    
    def clear_content(self):
        """Очищает контент"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def load_online_friends(self):
        """Загружает друзей онлайн"""
        self.clear_content()
        
        current_username = self.get_current_username_safe()
        if not current_username:
            self.show_empty_state(tr("please_login"))
            return
        
        friends = get_friends(current_username)
        # Отладка: проверяем что возвращает функция
        if not friends:
            # Проверяем есть ли вообще друзья в базе (для отладки)
            try:
                import sqlite3
                from email_app import DB_FILE
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user1_username, user2_username, status
                    FROM friendships
                    WHERE (user1_username = ? OR user2_username = ?)
                ''', (current_username, current_username))
                all_relations = cursor.fetchall()
                conn.close()
                # Если есть отношения, но не accepted - показываем сообщение
            except:
                pass
            self.show_empty_state(tr("no_friends"))
            return
        
        self.friends_cache = friends
        online_friends = [f for f in friends if f.get('is_online', False)]
        
        search_text = self.search_input.text().strip().lower()
        if search_text:
            online_friends = [f for f in online_friends if 
                            search_text in f.get('first_name', '').lower() or
                            search_text in f.get('last_name', '').lower() or
                            search_text in f.get('username', '').lower()]
        
        if not online_friends:
            empty_label = QLabel(tr("no_online_friends"))
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 8px 0; background: transparent; font-size: 13px;")
            self.content_layout.addWidget(empty_label)
        else:
            # Header with count (лиловая тема)
            header = QLabel(f"{tr('online')} — {len(online_friends)}")
            header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            header.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 8px 0; background: transparent;")
            self.content_layout.addWidget(header)
            for friend in online_friends:
                card = FriendCard(friend, show_status=False)
                card.context_menu_requested.connect(lambda pos, f=friend: self.show_context_menu(pos, f))
                card.profile_requested.connect(lambda f=friend: self.show_friend_profile(f))
                self.content_layout.addWidget(card)
        
        self.content_layout.addStretch()
    
    def load_all_friends(self):
        """Загружает всех друзей"""
        self.clear_content()
        
        current_username = self.get_current_username_safe()
        if not current_username:
            self.show_empty_state(tr("please_login"))
            return
        
        # Incoming requests
        incoming_requests = get_friend_requests(current_username)
        friends = get_friends(current_username)
        
        # Отладка: если нет друзей, проверяем статус в БД
        if not friends:
            try:
                import sqlite3
                from email_app import DB_FILE
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                # Проверяем все отношения
                cursor.execute('''
                    SELECT user1_username, user2_username, status
                    FROM friendships
                    WHERE (user1_username = ? OR user2_username = ?)
                ''', (current_username, current_username))
                all_relations = cursor.fetchall()
                # Если есть отношения, но статус не 'accepted', они не покажутся
                # Нужно проверить что статус правильный
                conn.close()
            except:
                pass
        
        self.friends_cache = friends
        
        search_text = self.search_input.text().strip().lower()
        if search_text:
            friends = [f for f in friends if 
                      search_text in f.get('first_name', '').lower() or
                      search_text in f.get('last_name', '').lower() or
                      search_text in f.get('username', '').lower()]
            incoming_requests = [r for r in incoming_requests if
                                search_text in r.get('first_name', '').lower() or
                                search_text in r.get('last_name', '').lower() or
                                search_text in r.get('username', '').lower()]
        
        # Incoming requests section
        if incoming_requests:
            requests_header = QLabel(tr("friend_requests"))
            requests_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            requests_header.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 6px 0; background: transparent;")
            self.content_layout.addWidget(requests_header)
            
            for request in incoming_requests:
                card = RequestCard(request, is_outgoing=False)
                card.accepted.connect(self.accept_request)
                card.rejected.connect(self.reject_request)
                card.context_menu_requested.connect(lambda pos, r=request: self.show_request_context_menu(pos, r))
                self.content_layout.addWidget(card)
            
            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet(f"background: {COLORS['border']}; margin: 8px 0;")
            self.content_layout.addWidget(separator)
        
        # Friends section
        online_count = len([f for f in friends if f.get('is_online', False)])
        total_count = len(friends)
        
        if not friends and not incoming_requests:
            self.show_empty_state(tr("no_friends"))
        else:
            if friends:
                friends_header = QLabel(f"Всего друзей — {total_count}")
                friends_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                friends_header.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 6px 0; background: transparent;")
                self.content_layout.addWidget(friends_header)
                
                for friend in friends:
                    card = FriendCard(friend, show_status=True)
                    card.context_menu_requested.connect(lambda pos, f=friend: self.show_context_menu(pos, f))
                    card.profile_requested.connect(lambda f=friend: self.show_friend_profile(f))
                    self.content_layout.addWidget(card)
        
        self.content_layout.addStretch()
    
    def load_pending_requests(self):
        """Загружает исходящие запросы"""
        self.clear_content()
        
        current_username = self.get_current_username_safe()
        if not current_username:
            self.show_empty_state(tr("please_login"))
            return
        
        outgoing_requests = get_outgoing_friend_requests(current_username)
        
        search_text = self.search_input.text().strip().lower()
        if search_text:
            outgoing_requests = [r for r in outgoing_requests if
                                search_text in r.get('first_name', '').lower() or
                                search_text in r.get('last_name', '').lower() or
                                search_text in r.get('username', '').lower()]
        
        if not outgoing_requests:
            self.show_empty_state(tr("no_requests"))
        else:
            for request in outgoing_requests:
                card = RequestCard(request, is_outgoing=True)
                card.rejected.connect(self.cancel_request)
                card.profile_requested.connect(lambda f=request: self.show_friend_profile(f))
                card.context_menu_requested.connect(lambda pos, r=request: self.show_request_context_menu(pos, r))
                self.content_layout.addWidget(card)
        
        self.content_layout.addStretch()
    
    def show_empty_state(self, message: str):
        """Показывает пустое состояние"""
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; padding: 8px 0; background: transparent;")
        self.content_layout.addWidget(label)
    
    def _on_search_text_changed(self, text: str):
        """Обработчик изменения текста поиска с дебаунсингом"""
        # Отменяем предыдущий таймер если он есть
        if self._search_timer:
            self._search_timer.stop()
        
        # Создаем новый таймер с задержкой 300ms для дебаунсинга
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(lambda: self.filter_friends(text))
        self._search_timer.start(300)  # Задержка 300ms
    
    def filter_friends(self, text: str):
        """Фильтрует друзей"""
        self.load_current_tab()
    
    def show_context_menu(self, pos: QPoint, friend: Dict[str, Any]):
        """Показывает контекстное меню для друга"""
        try:
            if self.context_menu:
                self.context_menu.deleteLater()
        except RuntimeError:
            pass
        
        self.context_menu = FriendContextMenu(self)
        self.context_menu.view_profile.connect(lambda: self.show_friend_profile(friend))
        self.context_menu.remove_friend.connect(lambda: self.show_remove_dialog(friend))
        
        # Позиционируем меню прямо под курсором и возле него
        # Получаем глобальную позицию курсора
        cursor_pos = QCursor.pos()
        # Меню должно быть прямо под курсором и справа от него
        menu_x = cursor_pos.x() + 2  # Немного вправо от курсора
        menu_y = cursor_pos.y() + 2  # Прямо под курсором
        self.context_menu.move(menu_x, menu_y)
        self.context_menu.show()
        
        # Close on outside click
        QTimer.singleShot(100, lambda: QApplication.instance().installEventFilter(
            MenuEventFilter(self.context_menu)
        ))
    
    def show_request_context_menu(self, pos: QPoint, request: Dict[str, Any]):
        """Показывает контекстное меню для запроса на дружбу"""
        try:
            if hasattr(self, 'request_context_menu') and self.request_context_menu:
                self.request_context_menu.deleteLater()
        except RuntimeError:
            pass
        
        self.request_context_menu = RequestContextMenu(self)
        self.request_context_menu.view_profile.connect(lambda: self.show_friend_profile(request))
        
        # Позиционируем меню прямо под курсором и возле него
        # Получаем глобальную позицию курсора
        cursor_pos = QCursor.pos()
        menu_x = cursor_pos.x() + 2  # Немного вправо от курсора
        menu_y = cursor_pos.y() + 2  # Прямо под курсором
        self.request_context_menu.move(menu_x, menu_y)
        self.request_context_menu.show()
        
        # Close on outside click
        QTimer.singleShot(100, lambda: QApplication.instance().installEventFilter(
            MenuEventFilter(self.request_context_menu)
        ))
    
    def show_friend_profile(self, friend: Dict[str, Any]):
        """Показывает профиль друга"""
        try:
            if self.profile_overlay:
                self.profile_overlay.deleteLater()
        except RuntimeError:
            pass
        self.profile_overlay = None
        
        # Overlay на главном окне, чтобы затемнить весь экран включая сайдбар
        if self.main_window:
            main_window = self.main_window
            # Создаем overlay на главном окне
            self.profile_overlay = QFrame(main_window)
            self.profile_overlay.setGeometry(0, 0, main_window.width(), main_window.height())
            self.profile_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
            self.profile_overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.profile_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            
            self.profile_overlay.show()
            self.profile_overlay.raise_()
            
            # Profile widget
            try:
                self.profile_widget = FriendProfileWidget(friend, self.profile_overlay, friends_page=self)
                
                # Обработчик клика на overlay - закрывает окно только если клик вне виджета профиля
                def close_overlay(e):
                    if e.button() == Qt.MouseButton.LeftButton:
                        # Получаем глобальные координаты клика
                        global_click_pos = self.profile_overlay.mapToGlobal(e.pos())
                        # Получаем глобальную геометрию виджета профиля
                        widget_global_pos = self.profile_widget.mapToGlobal(QPoint(0, 0))
                        widget_global_rect = QRect(widget_global_pos, self.profile_widget.size())
                        # Проверяем, что клик был вне виджета
                        if not widget_global_rect.contains(global_click_pos):
                            try:
                                if self.profile_overlay:
                                    self.profile_overlay.deleteLater()
                                    self.profile_overlay = None
                            except RuntimeError:
                                pass
                
                self.profile_overlay.mousePressEvent = close_overlay
                
                def close_profile():
                    try:
                        if self.profile_overlay:
                            self.profile_overlay.deleteLater()
                            self.profile_overlay = None
                    except RuntimeError:
                        pass
                
                self.profile_widget.closed.connect(close_profile)
                self.profile_widget.move(
                    (self.profile_overlay.width() - self.profile_widget.width()) // 2,
                    (self.profile_overlay.height() - self.profile_widget.height()) // 2
                )
                self.profile_widget.show()
                self.profile_widget.raise_()
            except RuntimeError as e:
                pass
        else:
            # Fallback на старый способ, если main_window не доступен
            self.profile_overlay = QFrame(self)
            self.profile_overlay.setGeometry(0, 0, self.width(), self.height())
            self.profile_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
            
            self.profile_overlay.show()
            
            self.profile_widget = FriendProfileWidget(friend, self.profile_overlay)
            self.profile_widget.friends_page = self
            self.profile_widget.closed.connect(lambda: self.profile_overlay.deleteLater() if self.profile_overlay else None)
            self.profile_widget.move(
                (self.profile_overlay.width() - self.profile_widget.width()) // 2,
                (self.profile_overlay.height() - self.profile_widget.height()) // 2
            )
            self.profile_widget.show()
            self.profile_widget.raise_()
            
            # Обработчик клика на overlay - закрывает окно только если клик вне виджета профиля
            def close_overlay(e):
                if e.button() == Qt.MouseButton.LeftButton:
                    # Получаем глобальные координаты клика
                    global_click_pos = self.profile_overlay.mapToGlobal(e.pos())
                    # Получаем глобальную геометрию виджета профиля
                    widget_global_pos = self.profile_widget.mapToGlobal(QPoint(0, 0))
                    widget_global_rect = QRect(widget_global_pos, self.profile_widget.size())
                    # Проверяем, что клик был вне виджета
                    if not widget_global_rect.contains(global_click_pos):
                        try:
                            if self.profile_overlay:
                                self.profile_overlay.deleteLater()
                                self.profile_overlay = None
                        except RuntimeError:
                            pass
            
            self.profile_overlay.mousePressEvent = close_overlay
    
    def show_remove_dialog(self, friend: Dict[str, Any]):
        """Показывает диалог удаления друга"""
        if self.context_menu:
            try:
                self.context_menu.hide()
                self.context_menu.deleteLater()
            except RuntimeError:
                pass
            self.context_menu = None
        
        if self.remove_dialog:
            try:
                if self.remove_dialog.isVisible():
                    self.remove_dialog.hide()
                self.remove_dialog.deleteLater()
            except RuntimeError:
                pass
            self.remove_dialog = None
        
        # Create dialog
        dialog = QFrame(self)
        dialog.setFixedSize(400, 160)
        dialog.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 2px solid {COLORS['border']};
                border-radius: 16px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(156, 123, 255, 80))
        dialog.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        message = QLabel(tr("remove_friend_confirm"))
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; background: transparent;")
        layout.addWidget(message)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()
        
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {COLORS['bg_hover']};
            }}
        """)
        cancel_btn.clicked.connect(dialog.deleteLater)
        buttons.addWidget(cancel_btn)
        
        confirm_btn = QPushButton(tr("confirm"))
        confirm_btn.setFixedHeight(38)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #D84040;
            }}
        """)
        confirm_btn.clicked.connect(lambda: (self.remove_friend_action(friend['username']), dialog.deleteLater()))
        buttons.addWidget(confirm_btn)
        
        layout.addLayout(buttons)
        dialog.setLayout(layout)
        
        dialog.move(
            (self.width() - dialog.width()) // 2,
            (self.height() - dialog.height()) // 2
        )
        dialog.show()
        dialog.raise_()
        self.remove_dialog = dialog
    
    def show_add_friend_dialog(self):
        """Показывает встроенный виджет добавления друга"""
        # Скрываем строку поиска
        if hasattr(self, 'search_frame'):
            self.search_frame.hide()
        # Переключаемся на вкладку "Все" чтобы показать форму добавления
        self.current_tab = 'all'
        self.tab_all.setChecked(True)
        self.tab_online.setChecked(False)
        self.tab_pending.setChecked(False)
        self.update_tab_styles()
        # Очищаем контент и показываем виджет добавления
        self.clear_content()
        
        # Заголовок (еще меньше)
        title = QLabel(tr("add_friend"))
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; padding: 20px 0 4px 0;")
        self.content_layout.addWidget(title)
        
        # Описание (еще меньше)
        desc = QLabel(tr("add_friend_description"))
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; padding: 0 0 20px 0;")
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)
        
        # Контейнер для формы (кнопка внутри рамки ввода)
        form_container = QFrame()
        form_container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
            }}
        """)
        form_layout = QHBoxLayout()
        form_layout.setContentsMargins(12, 0, 12, 0)
        form_layout.setSpacing(8)
        form_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Поле ввода (внутри рамки, больше по высоте)
        username_input = QLineEdit()
        username_input.setPlaceholderText(tr("add_friend_description"))
        username_input.setFixedHeight(60)
        username_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                background: transparent;
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_secondary']};
            }}
        """)
        form_layout.addWidget(username_input, stretch=1)
        
        # Кнопка отправки (шире, чтобы текст был виден, неактивна по умолчанию)
        send_btn = QPushButton(tr("send_friend_request"))
        send_btn.setFixedHeight(36)
        send_btn.setFixedWidth(180)
        send_btn.setEnabled(False)  # Неактивна по умолчанию
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: #B8A5FF;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #A895EF;
            }}
            QPushButton:pressed {{
                background: #9B8AE0;
            }}
            QPushButton:disabled {{
                background: {COLORS['border']};
                color: {COLORS['text_secondary']};
            }}
        """)
        form_layout.addWidget(send_btn)
        
        # Активация кнопки при вводе текста
        def on_text_changed(text):
            send_btn.setEnabled(bool(text.strip()))
        
        username_input.textChanged.connect(on_text_changed)
        
        form_container.setLayout(form_layout)
        
        # Сообщение об ошибке/успехе (просто текст, не виджет)
        error_label = QLabel()
        error_label.setWordWrap(True)
        error_label.setTextFormat(Qt.TextFormat.RichText)  # Включаем поддержку HTML
        error_label.hide()
        error_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 13px; background: transparent; padding: 8px 0;")
        
        def on_send():
            username = username_input.text().strip()
            error_label.hide()
            
            # Сбрасываем стиль на нормальный
            form_container.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['bg_secondary']};
                    border: 1px solid {COLORS['accent']};
                    border-radius: 8px;
                }}
            """)
            
            # Проверка на пустое поле
            if not username:
                error_label.setText(tr("fill_all_fields") if hasattr(tr, '__call__') else "Заполните все поля")
                error_label.show()
                form_container.setStyleSheet(f"""
                    QFrame {{
                        background: {COLORS['bg_secondary']};
                        border: 2px solid {COLORS['danger']};
                        border-radius: 8px;
                    }}
                """)
                return
            
            # Получаем текущего пользователя
            current_username = self.get_current_username_safe()
            if not current_username:
                error_label.setText(tr("please_login") if hasattr(tr, '__call__') else "Пожалуйста, войдите в систему")
                error_label.show()
                form_container.setStyleSheet(f"""
                    QFrame {{
                        background: {COLORS['bg_secondary']};
                        border: 2px solid {COLORS['danger']};
                        border-radius: 8px;
                    }}
                """)
                return
            
            # Проверка на добавление самого себя
            if username.lower() == current_username.lower():
                error_label.setText(tr("cannot_add_self") if hasattr(tr, '__call__') else "Нельзя добавить самого себя")
                error_label.show()
                form_container.setStyleSheet(f"""
                    QFrame {{
                        background: {COLORS['bg_secondary']};
                        border: 2px solid {COLORS['danger']};
                        border-radius: 8px;
                    }}
                """)
                return
            
            # Проверяем существование пользователя перед отправкой запроса
            # (эта проверка уже есть в send_friend_request, но делаем для быстрой обратной связи)
            try:
                import sqlite3
                from email_app import DB_FILE
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username,))
                user_exists = cursor.fetchone()
                conn.close()
                
                if not user_exists:
                    error_label.setText(tr("user_not_found") if hasattr(tr, '__call__') else f"Пользователь '{username}' не найден")
                    error_label.show()
                    form_container.setStyleSheet(f"""
                        QFrame {{
                            background: {COLORS['bg_secondary']};
                            border: 2px solid {COLORS['danger']};
                            border-radius: 8px;
                        }}
                    """)
                    return
            except Exception as e:
                # Продолжаем выполнение, так как send_friend_request тоже проверит
                pass
            
            # Отправляем запрос (используем точный username из базы, если он был найден)
            try:
                # Импортируем функцию напрямую
                from email_app import send_friend_request as send_request_func
                result = send_request_func(current_username, username.strip())
                
                if isinstance(result, tuple) and len(result) == 2:
                    success, error_code = result
                else:
                    success = False
                    error_code = "error_occurred"
            except Exception as e:
                import traceback
                traceback.print_exc()
                success = False
                error_code = "error_occurred"
            
            if success:
                # Получаем никнейм пользователя (username)
                try:
                    import sqlite3
                    from email_app import DB_FILE
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute('SELECT username FROM auth_users WHERE username = ? COLLATE NOCASE', (username,))
                    user_info = cursor.fetchone()
                    conn.close()
                    
                    if user_info:
                        display_name = user_info[0]  # Используем username (никнейм)
                    else:
                        display_name = username
                except:
                    display_name = username
                
                # Показываем сообщение об успехе (ник жирным через HTML)
                success_message = f"Получилось! Запрос дружбы отправлен <b>{display_name}</b>"
                error_label.setText(success_message)
                error_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 13px; background: transparent; padding: 8px 0; font-weight: 600;")
                error_label.show()
                
                # Зеленая обводка рамки
                form_container.setStyleSheet(f"""
                    QFrame {{
                        background: {COLORS['bg_secondary']};
                        border: 2px solid {COLORS['success']};
                        border-radius: 8px;
                    }}
                """)
                
                username_input.clear()
                send_btn.setEnabled(False)  # Деактивируем кнопку после отправки
                
                # Сохраняем ссылку на обработчик для последующего отключения
                def on_text_changed_after_success(text):
                    if text.strip():
                        error_label.hide()
                        form_container.setStyleSheet(f"""
                            QFrame {{
                                background: {COLORS['bg_secondary']};
                                border: 1px solid {COLORS['accent']};
                                border-radius: 8px;
                            }}
                        """)
                        # Отключаем этот обработчик после первого срабатывания
                        try:
                            username_input.textChanged.disconnect(on_text_changed_after_success)
                        except:
                            pass
                
                # Подключаем обработчик для очистки сообщения при вводе
                username_input.textChanged.connect(on_text_changed_after_success)
                
                # НЕ переключаем вкладку - остаемся на текущей
            else:
                # Показываем понятное сообщение об ошибке в зависимости от кода ошибки
                
                # Получаем функцию перевода
                try:
                    from email_app import tr as tr_func
                    use_tr = True
                except:
                    use_tr = False
                
                error_messages = {
                    "user_not_found": tr_func("user_not_found") if use_tr else f"Пользователь '{username}' не найден",
                    "cannot_add_self": tr_func("cannot_add_self") if use_tr else "Нельзя добавить самого себя",
                    "already_friends": tr_func("already_friends") if use_tr else "Вы уже друзья",
                    "request_already_sent": tr_func("request_already_sent") if use_tr else "Запрос уже отправлен",
                    "database_error": "Ошибка базы данных. Убедитесь, что база данных инициализирована правильно.",
                    "import_error": "Ошибка импорта модулей. Перезапустите приложение.",
                    "error_occurred": "Произошла ошибка при отправке запроса. Проверьте консоль для деталей."
                }
                
                error_msg = error_messages.get(error_code)
                if not error_msg:
                    # Если код ошибки неизвестен, показываем его
                    error_msg = f"Ошибка: {error_code}" if error_code else "Произошла неизвестная ошибка"
                
                error_label.setText(error_msg)
                error_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 13px; background: transparent; padding: 8px 0;")
                error_label.show()
                # Красная обводка рамки
                form_container.setStyleSheet(f"""
                    QFrame {{
                        background: {COLORS['bg_secondary']};
                        border: 2px solid {COLORS['danger']};
                        border-radius: 8px;
                    }}
                """)
        
        send_btn.clicked.connect(on_send)
        username_input.returnPressed.connect(on_send)
        
        self.content_layout.addWidget(form_container)
        self.content_layout.addWidget(error_label)
        self.content_layout.addStretch()
        
        username_input.setFocus()
    
    def send_friend_request(self, username: str):
        """Отправляет запрос на дружбу"""
        current_username = self.get_current_username_safe()
        if not current_username:
            self.show_status(tr("please_login"), is_error=True)
            return
        
        if username == current_username:
            self.show_status(tr("cannot_add_self"), is_error=True)
            return
        
        success, message = send_friend_request(current_username, username)
        if success:
            self.show_status(message, is_error=False)
            self.load_current_tab()
        else:
            self.show_status(message, is_error=True)
    
    def accept_request(self, username: str):
        """Принимает запрос на дружбу"""
        current_username = self.get_current_username_safe()
        if current_username:
            success, message = accept_friend_request(current_username, username)
            if success:
                self.show_status(message, is_error=False)
                # Обновляем текущую вкладку
                QTimer.singleShot(300, self.load_current_tab)
            else:
                self.show_status(message, is_error=True)
    
    def reject_request(self, username: str):
        """Отклоняет запрос на дружбу"""
        current_username = self.get_current_username_safe()
        if current_username:
            reject_friend_request(current_username, username)
            self.load_all_friends()
    
    def cancel_request(self, username: str):
        """Отменяет исходящий запрос"""
        current_username = self.get_current_username_safe()
        if current_username:
            reject_friend_request(current_username, username)
            self.load_pending_requests()
    
    def remove_friend_action(self, username: str):
        """Удаляет друга"""
        current_username = self.get_current_username_safe()
        if current_username:
            remove_friend(current_username, username)
            self.show_status(tr("friend_removed"), is_error=False)
            self.load_current_tab()
    
    def show_status(self, message: str, is_error: bool = False):
        """Показывает статусное сообщение"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background: {COLORS['danger'] if is_error else COLORS['success']};
                padding: 12px 18px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
            }}
        """)
        self.status_label.show()
        QTimer.singleShot(3000 if not is_error else 5000, self.status_label.hide)
    
    def activate(self):
        """Активирует страницу"""
        self.is_active = True
        self.load_current_tab()
    
    def deactivate(self):
        """Деактивирует страницу"""
        self.is_active = False

# ============================================================================
# Event Filter for Context Menu
# ============================================================================

class MenuEventFilter(QObject):
    """Фильтр событий для закрытия меню при клике вне его"""
    def __init__(self, menu: QFrame):
        super().__init__()
        self.menu = menu
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.menu and self.menu.isVisible():
                global_pos = event.globalPosition().toPoint()
                menu_rect = QRect(self.menu.mapToGlobal(QPoint(0, 0)), self.menu.size())
                if not menu_rect.contains(global_pos):
                    self.menu.hide()
                    QApplication.instance().removeEventFilter(self)
                    return True
        return False
