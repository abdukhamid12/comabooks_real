import io
import os
import requests
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

def generate_book_pdf(book):
    # Register Font
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
    # Check if font exists, otherwise fallback to default or log warning
    # Assuming it exists based on previous code
    try:
        pdfmetrics.registerFont(TTFont('Arial', font_path))
        font_name = 'Arial'
    except Exception:
        font_name = 'Helvetica' # Fallback

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
    styles.add(ParagraphStyle(name='ChapterTitle', fontName=font_name, fontSize=24, leading=28, spaceAfter=20, textColor=HexColor('#2c3e50')))
    styles.add(ParagraphStyle(name='QuestionText', fontName=font_name, fontSize=16, leading=20, spaceBefore=10, spaceAfter=15, textColor=HexColor('#8e44ad')))
    styles.add(ParagraphStyle(name='AnswerText', fontName=font_name, fontSize=14, leading=20, alignment=TA_JUSTIFY, spaceAfter=20))

    # Cover Page Renderer
    def on_cover_page(canvas, doc):
        canvas.saveState()
        template = 'classic'
        if hasattr(book, 'cover_data'):
            template = book.cover_data.template
            
        width, height = A4
        
        if template == 'dark':
            canvas.setFillColor(HexColor('#1a1a1a'))
            canvas.rect(0, 0, width, height, fill=True)
            
        elif template == 'modern':
            canvas.setFillColor(HexColor('#e0e7ff'))
            canvas.rect(0, 0, width, height, fill=True)
            
        elif template == 'classic':
            canvas.setFillColor(HexColor('#f4f1ea'))
            canvas.rect(0, 0, width, height, fill=True)
            canvas.setStrokeColor(HexColor('#8e44ad'))
            canvas.setLineWidth(4)
            canvas.rect(30, 30, width-60, height-60)

        canvas.restoreState()

    # Build Content
    story = []

    # Styles lookup
    cover_title_style = styles['CoverTitle']
    cover_sub_style = styles['CoverSubtitle']
    cover_auth_style = styles['CoverAuthor']

    if hasattr(book, 'cover_data') and book.cover_data.template == 'dark':
        cover_title_style.textColor = white
        cover_sub_style.textColor = HexColor('#cccccc')
        cover_auth_style.textColor = white

    # Cover Content
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph(book.title, cover_title_style))
    if book.subtitle:
        story.append(Paragraph(book.subtitle, cover_sub_style))
    
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"Автор: {book.author}", cover_auth_style))
    
    if book.dedication:
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"Посвящается: {book.dedication.name}", cover_auth_style))
    
    story.append(PageBreak())

    # Pages Content
    pages = book.pages.all()
    for page in pages:
        content_elements = [
            Paragraph(page.quiz, styles['QuestionText']),
            Paragraph(page.answer.replace('\n', '<br/>'), styles['AnswerText'])
        ]
        
        # Add Image if exists
        if page.image:
            try:
                # Calculate simple aspect ratio scaling to fit on page width (roughly)
                # A4 width is ~595pt. Margins are 72+72=144. Content width = 451.
                available_width = 450
                img_path = page.image.path
                if os.path.exists(img_path):
                    im = RLImage(img_path)
                    
                    # Manual aspect ratio calculation (basic)
                    # Reportlab Image usually handles this if we set one dimension logic, 
                    # but simple scaling safer:
                    # Let's just set width to available width if it's too big, or keep original if small
                    # Ideally we read image size first. RLImage does that.
                    
                    img_width = im.drawWidth
                    img_height = im.drawHeight
                    
                    if img_width > available_width:
                        factor = available_width / img_width
                        im.drawWidth = available_width
                        im.drawHeight = img_height * factor
                    
                    content_elements.insert(1, im) # Insert after Question
                    content_elements.insert(2, Spacer(1, 10)) # Spacer after image
            except Exception as e:
                print(f"Error adding image: {e}") 
                pass # Skip image if error

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
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
