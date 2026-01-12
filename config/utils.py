import io
import os
import requests
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, SimpleDocTemplate, Paragraph, Spacer, PageBreak, 
    KeepTogether, Image as RLImage, PageTemplate, Frame, NextPageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import google.generativeai as genai
import json

def split_text_by_words(text, limit=250):
    words = text.split()
    chunks = []
    for i in range(0, len(words), limit):
        chunks.append(" ".join(words[i:i+limit]))
    return chunks

def generate_book_pdf(book):
    # Register Font
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
    try:
        pdfmetrics.registerFont(TTFont('Arial', font_path))
        font_name = 'Arial'
    except Exception:
        font_name = 'Helvetica'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CoverTitle', fontName=font_name, fontSize=36, leading=42, alignment=TA_CENTER, textColor=black, spaceAfter=20))
    styles.add(ParagraphStyle(name='CoverSubtitle', fontName=font_name, fontSize=24, leading=30, alignment=TA_CENTER, textColor=HexColor('#555555'), spaceAfter=50))
    styles.add(ParagraphStyle(name='CoverAuthor', fontName=font_name, fontSize=18, leading=24, alignment=TA_CENTER, textColor=HexColor('#333333')))
    styles.add(ParagraphStyle(name='AnswerText', fontName=font_name, fontSize=14, leading=20, alignment=TA_JUSTIFY, spaceAfter=20))

    # Cover Page Renderer
    def on_cover_page(canvas, doc):
        canvas.saveState()
        template = 'classic'
        if hasattr(book, 'cover_data'):
            template = book.cover_data.template
            
        width, height = A4
        
        # 1. Background
        if template == 'dark':
            canvas.setFillColor(HexColor('#1a1a1a'))
            canvas.rect(0, 0, width, height, fill=True)
        elif template == 'modern':
            canvas.setFillColor(HexColor('#FDFBF7')) 
            canvas.rect(0, 0, width, height, fill=True)
        elif template == 'classic':
            canvas.setFillColor(HexColor('#fdfaf6'))
            canvas.rect(0, 0, width, height, fill=True)
            
        # 2. Spine Shadow
        for i in range(1, 40):
            alpha = (40 - i) / 100.0
            canvas.setFillColor(black, alpha=alpha)
            canvas.rect(i*0.8, 0, 1.2, height, stroke=0, fill=1)

        # 3. Decorative Borders
        if template == 'classic':
            canvas.setStrokeColor(HexColor('#4b3621'))
            canvas.setLineWidth(1.5)
            canvas.rect(45, 45, width-90, height-90, stroke=1, fill=0)
        elif template == 'dark':
            canvas.setStrokeColor(HexColor('#ffd700'))
            canvas.setLineWidth(1)
            canvas.rect(60, 60, width-120, height-120, stroke=1, fill=0)

        canvas.restoreState()

    story = []

    # Dedicated Cover Styles
    cover_title_style = ParagraphStyle(name='CoverTitleDedicated', fontName=font_name, fontSize=36, leading=48, alignment=TA_CENTER, textColor=black, spaceAfter=30)
    cover_sub_style = ParagraphStyle(name='CoverSubtitleDedicated', fontName=font_name, fontSize=24, leading=30, alignment=TA_CENTER, textColor=HexColor('#555555'), spaceAfter=50)
    cover_auth_style = ParagraphStyle(name='CoverAuthorDedicated', fontName=font_name, fontSize=18, leading=24, alignment=TA_CENTER, textColor=HexColor('#333333'))

    if hasattr(book, 'cover_data') and book.cover_data.template == 'dark':
        cover_title_style.textColor = HexColor('#ffffff')
        cover_sub_style.textColor = HexColor('#bdc3c7')
        cover_auth_style.textColor = HexColor('#f1c40f') 
    elif hasattr(book, 'cover_data') and book.cover_data.template == 'classic':
        cover_title_style.textColor = HexColor('#2c1810')
        cover_sub_style.textColor = HexColor('#5d4037')
        cover_auth_style.textColor = HexColor('#2c1810')

    # Cover Content
    story.append(Spacer(1, 3.2*inch))
    story.append(Paragraph(book.title.upper(), cover_title_style))
    if book.subtitle:
        story.append(Paragraph(book.subtitle, cover_sub_style))
    story.append(Spacer(1, 2.2*inch))
    story.append(Paragraph(f"АВТОР: {book.author.upper()}", cover_auth_style))
    
    if book.dedication:
        story.append(Spacer(1, 0.4*inch))
        story.append(Paragraph(f"ДЛЯ: {book.dedication.name.upper()}", cover_auth_style))
    
    story.append(PageBreak())

    # Pages Content
    pages = book.pages.all()
    for page in pages:
        content_elements = []
        
        # 1. Answer Text
        if page.answer:
            answer_text = page.answer.replace('\n', '<br/>')
            content_elements.append(Paragraph(answer_text, styles['AnswerText']))
        
        # 2. Image (on same page if possible)
        if page.image:
            try:
                img_path = page.image.path
                if os.path.exists(img_path):
                    width_A4, height_A4 = A4
                    avail_w = width_A4 - 2*72
                    im = RLImage(img_path)
                    img_w = im.drawWidth
                    img_h = im.drawHeight
                    
                    # Scale to fit width
                    scale = avail_w / img_w
                    im.drawWidth = avail_w
                    im.drawHeight = img_h * scale
                    
                    content_elements.append(Spacer(1, 10))
                    content_elements.append(im)
            except Exception as e:
                print(f"Error adding image: {e}")

        if content_elements:
            story.append(KeepTogether(content_elements))
            story.append(PageBreak())

    # Build PDF
    doc.build(story, onFirstPage=on_cover_page)
    buffer.seek(0)
    return buffer

def send_telegram_notification(book, pdf_buffer, target_chat_id=None):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = target_chat_id or settings.TELEGRAM_ADMIN_CHAT_ID
    
    if not token or not chat_id or token == 'YOUR_BOT_TOKEN_HERE':
        print("Telegram settings not configured.")
        return

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    
    # Reset buffer pos just in case
    pdf_buffer.seek(0)
    
    files = {
        'document': (f'{book.title}.pdf', pdf_buffer, 'application/pdf')
    }
    
    caption = (
        f"📘 *Новая книга на проверку!*\n\n"
        f"**Название:** {book.title}\n"
        f"**Автор:** {book.author}\n"
        f"**Пользователь:** {book.user.username}\n"
        f"**Время отправки:** {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"**Статус:** {book.get_status_display()}"
    )
    
    data = {
        'chat_id': chat_id,
        'caption': caption,
        'parse_mode': 'Markdown'
    }
    
    try:
        # verify=False used to bypass local SSL issues on Windows dev environment
        response = requests.post(url, data=data, files=files, verify=False)
        response.raise_for_status()
        print("Telegram notification sent successfully.")
        # Mark as sent
        book.is_notification_sent = True
        book.save()
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")


def generate_questions_ai(dedication_name, dedication_text, count=5, api_key=None):
    if not api_key:
        print("AI generation skipped: No API key provided.")
        return []

    try:
        genai.configure(api_key=api_key)
        # Using gemini-flash-latest which exists in your models list
        model = genai.GenerativeModel('gemini-flash-latest')
        
        prompt = (
            f"Ты — дружелюбный помощник по созданию подарочных книг. Твоя задача — придумать простые и теплые вопросы для автора книги, "
            f"которые помогут ему вспомнить добрые истории про человека по имени **{dedication_name}**. "
            f"Вот что автор написал об этом человеке: \"{dedication_text}\".\n\n"
            f"Сгенерируй {count} простых и душевных вопросов.\n"
            f"ПРАВИЛА:\n"
            f"1. Вопросы должны быть короткими и понятными (например: 'Вспомни твой любимый момент с {dedication_name}', 'Какое качество в {dedication_name} тебя больше всего восхищает?').\n"
            f"2. Используй имя {dedication_name} в вопросах.\n"
            f"3. Вопросы должны быть про личные воспоминания, чувства и общие приключения.\n"
            f"4. НЕ используй заумных слов. Представь, что ты общаешься с другом.\n\n"
            f"Верни ответ ТОЛЬКО в формате JSON массива строк.\n"
            f"Пример: [\"Вопрос 1\", \"Вопрос 2\"]"
        )
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean potential markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        questions = json.loads(text)
        return questions
    except Exception as e:
        print(f"Error generating questions with AI: {e}")
        # Try fallback models if primary fails
        if "404" in str(e) or "429" in str(e):
            for model_name in ['gemini-pro-latest', 'gemini-2.0-flash']:
                try:
                    print(f"DEBUG: Trying fallback model: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    if text.startswith("```json"): text = text[7:]
                    if text.endswith("```"): text = text[:-3]
                    return json.loads(text.strip())
                except:
                    pass
        return []


def enhance_answer_ai(question, answer, api_key=None):
    if not api_key or not answer:
        return answer

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        
        prompt = (
            f"Ты — помощник писателя. Тебе дали короткий ответ на вопрос для книги воспоминаний. "
            f"Твоя задача — сделать этот ответ более красивым, эмоциональным и развернутым, сохранив основной смысл и факты.\n\n"
            f"Вопрос: {question}\n"
            f"Короткий ответ: {answer}\n\n"
            f"Требования к тексту:\n"
            f"1. Сделай текст более литературным и плавным.\n"
            f"2. Если ответ слишком короткий, добавь немного атмосферы, подходящей по смыслу.\n"
            f"3. Пиши от первого лица (как автор ответа).\n"
            f"4. НЕ добавляй выдуманных фактов, которых нет в ответе, просто раскрась имеющиеся.\n\n"
            f"Верни ТОЛЬКО улучшенный текст (без пояснений и кавычек)."
        )
        
        response = model.generate_content(prompt)
        enhanced_text = response.text.strip()
        
        if len(enhanced_text) > 5: # basic sanity check
            return enhanced_text
        return answer
    except Exception as e:
        print(f"Error enhancing answer with AI: {e}")
        return answer
