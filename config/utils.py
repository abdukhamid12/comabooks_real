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
        
        # 1. Background Color and Texture Simulation
        if template == 'dark':
            canvas.setFillColor(HexColor('#1a1a1a')) # Deep Onyx
            canvas.rect(0, 0, width, height, fill=True)
            # Subtle Grain/Fleck texture
            import random
            for _ in range(2000):
                x = random.uniform(0, width)
                y = random.uniform(0, height)
                size = random.uniform(0.1, 0.5)
                canvas.setFillColor(white, alpha=0.03)
                canvas.circle(x, y, size, stroke=0, fill=1)
                
        elif template == 'modern':
            # Soft Graduate background
            canvas.setFillColor(HexColor('#ffffff'))
            canvas.rect(0, 0, width, height, fill=True)
            # Modern geometric accent
            canvas.setFillColor(HexColor('#f3f4f6'))
            canvas.rect(width*0.7, 0, width*0.3, height, fill=True)
            canvas.setFillColor(HexColor('#3b82f6')) # Vibrant Indigo
            canvas.rect(0, height-15, width, 15, fill=True)
            
        elif template == 'classic':
            canvas.setFillColor(HexColor('#fdfaf6')) # Antique Cream
            canvas.rect(0, 0, width, height, fill=True)
            # Cloth/Linen texture simulation
            canvas.setStrokeColor(HexColor('#000000'), alpha=0.02)
            canvas.setLineWidth(0.5)
            # Vertical lines
            for x in range(0, int(width), 2):
                canvas.line(x, 0, x, height)
            # Horizontal lines
            for y in range(0, int(height), 2):
                canvas.line(0, y, width, y)
            
        # 2. Spine Shadow (Realistic Depth)
        for i in range(1, 40):
            alpha = (40 - i) / 100.0
            canvas.setFillColor(black, alpha=alpha)
            canvas.rect(i*0.8, 0, 1.2, height, stroke=0, fill=1)

        # 3. Decorative Borders (Multi-layered & Premium)
        if template == 'classic':
            # Double brown/gold frame
            canvas.setStrokeColor(HexColor('#4b3621')) # Deep Brown
            canvas.setLineWidth(1.5)
            canvas.rect(45, 45, width-90, height-90, stroke=1, fill=0)
            
            canvas.setStrokeColor(HexColor('#d4af37')) # Muted Gold
            canvas.setLineWidth(0.5)
            canvas.rect(50, 50, width-100, height-100, stroke=1, fill=0)
            
            # Corner accents
            c_size = 20
            canvas.setLineWidth(2)
            # Top Left
            canvas.line(45, height-45, 45+c_size, height-45)
            canvas.line(45, height-45, 45, height-45-c_size)
            # Top Right
            canvas.line(width-45, height-45, width-45-c_size, height-45)
            canvas.line(width-45, height-45, width-45, height-45-c_size)
            
        elif template == 'dark':
            # Gold Foil Frame Simulation
            canvas.setStrokeColor(HexColor('#ffd700')) # Bright Gold
            canvas.setLineWidth(1)
            # Outer frame
            canvas.rect(60, 60, width-120, height-120, stroke=1, fill=0)
            # Inner thin frame with some transparency for "glow"
            canvas.setStrokeColor(white, alpha=0.3)
            canvas.rect(62, 62, width-124, height-124, stroke=1, fill=0)

        canvas.restoreState()

    # Build Content
    story = []

    # Styles lookup
    cover_title_style = styles['CoverTitle']
    cover_sub_style = styles['CoverSubtitle']
    cover_auth_style = styles['CoverAuthor']

    # Refine Typography Padding/Leading
    cover_title_style.leading = 48
    cover_title_style.spaceAfter = 30
    
    if hasattr(book, 'cover_data') and book.cover_data.template == 'dark':
        cover_title_style.textColor = HexColor('#ffffff')
        cover_sub_style.textColor = HexColor('#bdc3c7')
        cover_auth_style.textColor = HexColor('#f1c40f') # Golden author name
    elif hasattr(book, 'cover_data') and book.cover_data.template == 'classic':
        cover_title_style.textColor = HexColor('#2c1810')
        cover_sub_style.textColor = HexColor('#5d4037')
        cover_auth_style.textColor = HexColor('#2c1810')
    elif hasattr(book, 'cover_data') and book.cover_data.template == 'modern':
        cover_title_style.alignment = TA_LEFT
        cover_sub_style.alignment = TA_LEFT
        cover_auth_style.alignment = TA_LEFT
        cover_title_style.leftIndent = 40
        cover_sub_style.leftIndent = 40
        cover_auth_style.leftIndent = 40

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
        
        # Add Image if exists (before text for better flow in this context)
        if page.image:
            try:
                available_width = 450
                img_path = page.image.path
                if os.path.exists(img_path):
                    im = RLImage(img_path)
                    img_width = im.drawWidth
                    img_height = im.drawHeight
                    
                    if img_width > available_width:
                        factor = available_width / img_width
                        im.drawWidth = available_width
                        im.drawHeight = img_height * factor
                    
                    content_elements.append(im)
                    content_elements.append(Spacer(1, 20)) 
            except Exception as e:
                print(f"Error adding image: {e}") 
        
        # Only Answer Text (Question removed as requested)
        content_elements.append(Paragraph(page.answer.replace('\n', '<br/>'), styles['AnswerText']))

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
