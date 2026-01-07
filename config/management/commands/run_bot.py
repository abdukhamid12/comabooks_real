import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from config.models import Book, CustomUser, BookDedication, BookPageQuestion
from config.utils import generate_book_pdf, send_telegram_notification

class Command(BaseCommand):
    help = 'Run the Telegram Bot listener with auto-notification'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == 'YOUR_BOT_TOKEN_HERE':
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN not configured in settings.py'))
            return

        from django.contrib.auth import authenticate
        from django.contrib.auth.models import User
        import json
        import re

        self.stdout.write(self.style.SUCCESS('Bot started! Monitoring for new books and commands...'))
        
        offset = 0
        url = f"https://api.telegram.org/bot{token}"
        
        # User state tracking
        user_states = {}

        def send_msg(chat_id, text, buttons=None, hide_keyboard=False):
            payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
            if buttons:
                # Transpose if list is flat or wrap each item
                kb = []
                for row in buttons:
                    if isinstance(row, list):
                        kb.append(row)
                    else:
                        kb.append([row])
                
                reply_markup = {
                    'keyboard': kb,
                    'resize_keyboard': True,
                    'one_time_keyboard': True
                }
                payload['reply_markup'] = json.dumps(reply_markup)
            elif hide_keyboard:
                payload['reply_markup'] = json.dumps({'remove_keyboard': True})
            requests.post(f"{url}/sendMessage", data=payload, verify=False)

        # Main menu buttons
        MAIN_MENU_BUTTONS = [
            ["👤 Создать посвящение", "👥 Создать клиента"],
            ["📚 Изменить статус", "❓ Создать вопрос"],
            ["🚪 Выйти"]
        ]

        while True:
            try:
                # 1. Auto-send completed books
                unsent_books = Book.objects.filter(status='completed', is_notification_sent=False)
                for b in unsent_books:
                    try:
                        pb = generate_book_pdf(b)
                        send_telegram_notification(b, pb)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Auto-send error: {e}"))

                # 2. Check Updates
                response = requests.get(f"{url}/getUpdates", params={'offset': offset, 'timeout': 10}, verify=False)
                data = response.json()
                
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        offset = update['update_id'] + 1
                        if 'message' not in update: continue
                        
                        msg = update['message']
                        chat_id = msg.get('chat', {}).get('id')
                        text = msg.get('text', '').strip()
                        
                        state_info = user_states.get(chat_id, {'state': 'IDLE', 'data': {}, 'is_auth': False})
                        current_state = state_info['state']

                        # Global Cancel
                        if text == "❌ Отмена":
                            state_info['state'] = 'ADMIN_MENU' if state_info['is_auth'] else 'IDLE'
                            user_states[chat_id] = state_info
                            send_msg(chat_id, "Действие отменено.", buttons=MAIN_MENU_BUTTONS if state_info['is_auth'] else None)
                            continue

                        # Auth Check Commands
                        if text == '/start':
                            user_states[chat_id] = {'state': 'IDLE', 'data': {}, 'is_auth': False}
                            send_msg(chat_id, "👋 Привет! Используйте /admin для входа.", hide_keyboard=True)
                            continue
                        
                        if text == '/admin':
                            if state_info['is_auth']:
                                state_info['state'] = 'ADMIN_MENU'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "🔧 С возвращением! Выберите действие:", buttons=MAIN_MENU_BUTTONS)
                            else:
                                state_info['state'] = 'AWAITING_LOGIN'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "🔐 Введите логин администратора:", buttons=["❌ Отмена"])
                            continue

                        # State Machine
                        if current_state == 'AWAITING_LOGIN':
                            state_info['data']['login'] = text
                            state_info['state'] = 'AWAITING_PASSWORD'
                            user_states[chat_id] = state_info
                            send_msg(chat_id, "🔑 Введите пароль:", buttons=["❌ Отмена"])
                            
                        elif current_state == 'AWAITING_PASSWORD':
                            username = state_info['data']['login']
                            user = authenticate(username=username, password=text)
                            if user and user.is_staff:
                                state_info['state'] = 'ADMIN_MENU'
                                state_info['is_auth'] = True
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "✅ Вход выполнен!", buttons=MAIN_MENU_BUTTONS)
                            else:
                                # Retry logic: stay in auth flow but ask for login again
                                state_info['state'] = 'AWAITING_LOGIN'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "❌ Неверные данные. Попробуйте ввести логин еще раз:", buttons=["❌ Отмена"])

                        elif current_state == 'ADMIN_MENU':
                            if text == "👤 Создать посвящение":
                                state_info['state'] = 'CREATE_DED_NAME'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "✏️ Введите имя персонажа:", buttons=["❌ Отмена"])
                            elif text == "👥 Создать клиента":
                                state_info['state'] = 'CREATE_USER_NAME'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "👤 Введите логин для нового клиента:", buttons=["❌ Отмена"])
                            elif text == "📚 Изменить статус":
                                state_info['state'] = 'STATUS_SELECT_BOOK'
                                user_states[chat_id] = state_info
                                books = Book.objects.all().order_by('-created_at')[:10]
                                if not books:
                                    send_msg(chat_id, "Книг пока нет.", buttons=MAIN_MENU_BUTTONS)
                                    state_info['state'] = 'ADMIN_MENU'
                                else:
                                    book_btns = [[f"#{b.id}: {b.title}"] for b in books]
                                    book_btns.append(["❌ Отмена"])
                                    send_msg(chat_id, "📚 Выберите книгу для изменения статуса:", buttons=book_btns)
                            elif text == "❓ Создать вопрос":
                                state_info['state'] = 'CREATE_QUES_SELECT_DED'
                                user_states[chat_id] = state_info
                                deds = BookDedication.objects.all()
                                ded_btns = [["Все (Общий вопрос)"]]
                                for d in deds:
                                    ded_btns.append([f"#{d.id}: {d.name}"])
                                ded_btns.append(["❌ Отмена"])
                                send_msg(chat_id, "📚 Выберите человека (посвящение) для вопроса:", buttons=ded_btns)
                            elif text == "🚪 Выйти":
                                user_states[chat_id] = {'state': 'IDLE', 'data': {}, 'is_auth': False}
                                send_msg(chat_id, "🚪 Вы вышли из системы.", hide_keyboard=True)
                            else:
                                send_msg(chat_id, "Пожалуйста, используйте кнопки ниже:", buttons=MAIN_MENU_BUTTONS)

                        elif current_state == 'CREATE_DED_NAME':
                            state_info['data']['ded_name'] = text
                            state_info['state'] = 'CREATE_DED_TEXT'
                            user_states[chat_id] = state_info
                            send_msg(chat_id, f"📝 Введите текст посвящения для '{text}':", buttons=["❌ Отмена"])

                        elif current_state == 'CREATE_DED_TEXT':
                            name = state_info['data']['ded_name']
                            BookDedication.objects.create(name=name, text=text)
                            send_msg(chat_id, f"✅ Посвящение '{name}' успешно создано!", buttons=MAIN_MENU_BUTTONS)
                            state_info['state'] = 'ADMIN_MENU'
                            user_states[chat_id] = state_info

                        elif current_state == 'CREATE_USER_NAME':
                            if CustomUser.objects.filter(username=text).exists():
                                send_msg(chat_id, "⚠️ Логин занят. Введите другой:", buttons=["❌ Отмена"])
                            else:
                                state_info['data']['new_user_login'] = text
                                state_info['state'] = 'CREATE_USER_PASS'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, f"🔑 Теперь введите пароль для пользователя '{text}':", buttons=["❌ Отмена"])

                        elif current_state == 'CREATE_USER_PASS':
                            login = state_info['data']['new_user_login']
                            CustomUser.objects.create_user(username=login, password=text)
                            send_msg(chat_id, f"✅ Пользователь '{login}' создан!", buttons=MAIN_MENU_BUTTONS)
                            state_info['state'] = 'ADMIN_MENU'
                            user_states[chat_id] = state_info

                        elif current_state == 'STATUS_SELECT_BOOK':
                            match = re.search(r'#(\d+):', text)
                            if match:
                                book_id = int(match.group(1))
                                try:
                                    book = Book.objects.get(id=book_id)
                                    state_info['data']['target_book_id'] = book_id
                                    state_info['state'] = 'STATUS_UPDATE_VALUE'
                                    user_states[chat_id] = state_info
                                    send_msg(chat_id, f"Выберите новый статус для '{book.title}':", buttons=[["Черновик", "Завершено"], ["Напечатано", "❌ Отмена"]])
                                except Book.DoesNotExist:
                                    send_msg(chat_id, "❌ Книга не найдена. Попробуйте снова.")
                            else:
                                send_msg(chat_id, "⚠️ Пожалуйста, выберите книгу с помощью кнопок.")

                        elif current_state == 'STATUS_UPDATE_VALUE':
                            mapping = {"Черновик": "draft", "Завершено": "completed", "Напечатано": "printed"}
                            if text in mapping:
                                bid = state_info['data']['target_book_id']
                                book = Book.objects.get(id=bid)
                                book.status = mapping[text]
                                book.save()
                                send_msg(chat_id, f"✅ Статус книги '{book.title}' обновлен!", buttons=MAIN_MENU_BUTTONS)
                                state_info['state'] = 'ADMIN_MENU'
                                user_states[chat_id] = state_info
                            else:
                                send_msg(chat_id, "⚠️ Выберите статус кнопками.")

                        elif current_state == 'CREATE_QUES_SELECT_DED':
                            if text == "Все (Общий вопрос)":
                                state_info['data']['ques_ded_id'] = None
                                state_info['state'] = 'CREATE_QUES_TEXT'
                                user_states[chat_id] = state_info
                                send_msg(chat_id, "✏️ Введите текст общего вопроса:", buttons=["❌ Отмена"])
                            else:
                                match = re.search(r'#(\d+):', text)
                                if match:
                                    ded_id = int(match.group(1))
                                    try:
                                        d = BookDedication.objects.get(id=ded_id)
                                        state_info['data']['ques_ded_id'] = d.id
                                        state_info['state'] = 'CREATE_QUES_TEXT'
                                        user_states[chat_id] = state_info
                                        send_msg(chat_id, f"✏️ Введите текст вопроса для '{d.name}':", buttons=["❌ Отмена"])
                                    except BookDedication.DoesNotExist:
                                        send_msg(chat_id, "❌ Посвящение не найдено.")
                                else:
                                    send_msg(chat_id, "⚠️ Используйте кнопки для выбора.")

                        elif current_state == 'CREATE_QUES_TEXT':
                            did = state_info['data']['ques_ded_id']
                            ded = BookDedication.objects.get(id=did) if did else None
                            BookPageQuestion.objects.create(dedication=ded, quiz=text)
                            send_msg(chat_id, "✅ Вопрос успешно сохранен!", buttons=MAIN_MENU_BUTTONS)
                            state_info['state'] = 'ADMIN_MENU'
                            user_states[chat_id] = state_info

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Loop error: {e}"))
                time.sleep(2)
            time.sleep(0.3)
