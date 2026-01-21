# Файл конфигурации для Email Sender
# ВАЖНО: Не публикуйте этот файл в открытых репозиториях!

# ============================================
# УЧЕТНЫЕ ДАННЫЕ ОТПРАВИТЕЛЯ
# ============================================
SENDER_EMAIL = "kornieienko.illia@gmail.com"  # ВАШ email адрес
SENDER_PASSWORD = "ldbf lxot uqwt sgvp"  # ВАШ пароль или пароль приложения

# ============================================
# НАСТРОЙКИ SMTP СЕРВЕРА
# ============================================
SMTP_SERVER = "smtp.gmail.com"  # Адрес SMTP сервера (Gmail, Outlook и т.д.)
SMTP_PORT = 587  # Порт SMTP (587 для TLS, 465 для SSL)
USE_TLS = True  # Использовать TLS шифрование

# ============================================
# НАСТРОЙКИ ПО УМОЛЧАНИЮ ДЛЯ ПИСЬМА
# ============================================
DEFAULT_SUBJECT = "Тестовое письмо"  # Тема письма по умолчанию
DEFAULT_BODY = "Это тестовое письмо, отправленное через Email Sender."  # Текст письма по умолчанию


# ============================================
# GROQ / AI НАСТРОЙКИ (БЕСПЛАТНО)
# ============================================
# Получите бесплатный API ключ на https://console.groq.com/
GROQ_API_KEY = "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"  # ВАШ API ключ от Groq (бесплатный)
GROQ_MODEL = "llama-3.3-70b-versatile"  # Модель AI (llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768, gemma2-9b-it)

# ============================================
# UI / APP CONSTANTS
# ============================================
APP_NAME = "Bewerbungs Studio"
LOGIN_SUBTITLE = "Создадим профиль за несколько секунд"
APPLICATIONS_STAT_LABEL = "Отправленных заявок"
APPLICATIONS_STAT_VALUE = "24"

# ============================================
# LOGIN SCREEN SETTINGS
# ============================================
LOGIN_IMAGE_URL = "https://i.pinimg.com/1200x/f3/bb/3f/f3bb3f793d185f25f1e2177e28fd7e88.jpg"
LOGIN_WELCOME_TEXT = "Welcome to\nBewerbungs Studio"
LOGIN_DESCRIPTION_TEXT = "Создавайте профессиональные Bewerbung письма\nс помощью AI и отправляйте их одним кликом."
LOGIN_FORM_TITLE = "USER LOGIN"
LOGIN_BUTTON_TEXT = "ВОЙТИ"
APP_VERSION = "v1.0.0"



