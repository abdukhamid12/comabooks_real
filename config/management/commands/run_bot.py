import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from config.models import Book
from config.utils import generate_book_pdf, send_telegram_notification

class Command(BaseCommand):
    help = 'Run the Telegram Bot listener'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == 'YOUR_BOT_TOKEN_HERE':
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN not configured in settings.py'))
            return

        try:
            # Send completed books on startup
            admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
            books = Book.objects.filter(status='completed').order_by('-created_at')
            if books.exists():
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={'chat_id': admin_chat_id, 'text': f"🚀 Bot started! Sending {books.count()} completed books..."},
                    verify=False
                )
                for book in books:
                    self.stdout.write(f"Sending book on startup: {book.title}")
                    try:
                        pdf_buffer = generate_book_pdf(book)
                        send_telegram_notification(book, pdf_buffer, target_chat_id=admin_chat_id)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error sending {book.title} on startup: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send startup books: {e}"))
        
        self.stdout.write(self.style.SUCCESS('Waiting for /start command...'))
        
        offset = 0
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        
        # Simple polling loop
        while True:
            try:
                # verify=False for local dev environment
                response = requests.get(url, params={'offset': offset, 'timeout': 30}, verify=False)
                data = response.json()
                
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        offset = update['update_id'] + 1
                        
                        if 'message' in update:
                            msg = update['message']
                            chat_id = msg.get('chat', {}).get('id')
                            text = msg.get('text', '')
                            
                            # Log incoming
                            self.stdout.write(f"Received '{text}' from {chat_id}")
                            
                            if text.strip() == '/start':
                                # Security check: Only allow configured admin
                                # Convert both to string for comparison
                                if str(chat_id) != str(settings.TELEGRAM_ADMIN_CHAT_ID):
                                    self.stdout.write(self.style.WARNING(f"Unauthorized access attempt from {chat_id}"))
                                    requests.post(
                                        f"https://api.telegram.org/bot{token}/sendMessage",
                                        data={'chat_id': chat_id, 'text': "⛔ Access Denied."},
                                        verify=False
                                    )
                                    continue

                                self.stdout.write(self.style.SUCCESS(f"Authorized /start from {chat_id}"))
                                
                                # Send Welcome Message
                                requests.post(
                                    f"https://api.telegram.org/bot{token}/sendMessage",
                                    data={'chat_id': chat_id, 'text': "📚 Sending all completed books..."},
                                    verify=False
                                )
                                
                                # Fetch Completed Books
                                books = Book.objects.filter(status='completed').order_by('-created_at')
                                count = books.count()
                                
                                if count == 0:
                                    requests.post(
                                        f"https://api.telegram.org/bot{token}/sendMessage",
                                        data={'chat_id': chat_id, 'text': "No completed books found."},
                                        verify=False
                                    )
                                
                                for book in books:
                                    self.stdout.write(f"Sending book: {book.title}")
                                    try:
                                        pdf_buffer = generate_book_pdf(book)
                                        send_telegram_notification(book, pdf_buffer, target_chat_id=chat_id)
                                    except Exception as e:
                                        self.stdout.write(self.style.ERROR(f"Error sending {book.title}: {e}"))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Polling error: {e}"))
                time.sleep(5)
            
            time.sleep(1)
