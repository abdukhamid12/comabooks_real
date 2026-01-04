from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from .models import Book, BookPageAnswer, BookCover, BookPageQuestion
from .forms import BookForm, BookPageForm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
import os
from django.conf import settings

def home(request):
    return render(request, "home.html")

@login_required
def dashboard(request):
    books = Book.objects.filter(user=request.user)
    return render(request, "books/dashboard.html", {"books": books})


@login_required
def create_book(request):
    if request.method == "POST":
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.user = request.user
            book.save()
            
            # Create Cover with selected template
            template_style = form.cleaned_data.get('template', 'classic')
            BookCover.objects.create(
                book=book,
                title=book.title,
                author_book=book.author,
                template=template_style
            )
            
            return redirect("edit_pages", book.id)
    else:
        form = BookForm()
    return render(request, "books/create_book.html", {"form": form})


@login_required
def edit_pages(request, book_id):
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # Get questions
    if book.dedication:
        questions = book.dedication.questions.all()
    else:
        questions = BookPageQuestion.objects.filter(dedication__isnull=True)
    
    # Determine active question
    question_id = request.GET.get('q')
    if question_id:
        active_question = get_object_or_404(BookPageQuestion, id=question_id)
    else:
        active_question = questions.first()

    # Get existing answer if any
    try:
        current_answer = BookPageAnswer.objects.get(book=book, quiz=active_question.quiz)
    except (BookPageAnswer.DoesNotExist, AttributeError):
        current_answer = None

    if request.method == "POST":
        form = BookPageForm(request.POST, instance=current_answer)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.book = book
            answer.user = request.user
            answer.quiz = active_question.quiz
            answer.save()
            
            # Redirect to next question
            next_question = questions.filter(id__gt=active_question.id).first()
            if next_question:
                return redirect(f"{request.path}?q={next_question.id}")
            else:
                return redirect('dashboard') # Or finish page
    else:
        form = BookPageForm(instance=current_answer)

    return render(request, "books/edit_pages.html", {
        "book": book, 
        "questions": questions, 
        "active_question": active_question,
        "form": form
    })


@login_required
def add_page(request, book_id):
    # Deprecated for new flow, but keeping for compatibility or direct access
    return redirect("edit_pages", book_id)


from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Frame, PageTemplate, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

@login_required
def generate_pdf(request, book_id):
    book = get_object_or_404(Book, id=book_id, user=request.user)
    
    # Register Font
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
    pdfmetrics.registerFont(TTFont('Arial', font_path))

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
    styles.add(ParagraphStyle(name='CoverTitle', fontName='Arial', fontSize=36, leading=42, alignment=TA_CENTER, textColor=black, spaceAfter=20))
    styles.add(ParagraphStyle(name='CoverSubtitle', fontName='Arial', fontSize=24, leading=30, alignment=TA_CENTER, textColor=HexColor('#555555'), spaceAfter=50))
    styles.add(ParagraphStyle(name='CoverAuthor', fontName='Arial', fontSize=18, leading=24, alignment=TA_CENTER, textColor=HexColor('#333333')))
    styles.add(ParagraphStyle(name='ChapterTitle', fontName='Arial', fontSize=24, leading=28, spaceAfter=20, textColor=HexColor('#2c3e50')))
    styles.add(ParagraphStyle(name='QuestionText', fontName='Arial', fontSize=16, leading=20, spaceBefore=10, spaceAfter=15, textColor=HexColor('#8e44ad')))
    styles.add(ParagraphStyle(name='AnswerText', fontName='Arial', fontSize=14, leading=20, alignment=TA_JUSTIFY, spaceAfter=20))

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
            # Adjust text colors for dark theme later manually or via style switch, 
            # but simpler to just use a lighter box or standard styling for simplicity now
            # For now, let's just do background. 
            # Validating text color against background is complex in Platypus flow unless we use different styles.
            # Let's keep text black on cover for Classic, but maybe White for Dark? 
            # To change text color dynamically, we'd need dynamic styles.
            
        elif template == 'modern':
            # Gradient-ish background (solid for PDF simplicity)
            canvas.setFillColor(HexColor('#e0e7ff')) # Light Blue/Purple
            canvas.rect(0, 0, width, height, fill=True)
            
        elif template == 'classic':
            canvas.setFillColor(HexColor('#f4f1ea')) # Cream
            canvas.rect(0, 0, width, height, fill=True)
            # Add Border
            canvas.setStrokeColor(HexColor('#8e44ad'))
            canvas.setLineWidth(4)
            canvas.rect(30, 30, width-60, height-60)

        canvas.restoreState()

    # Build Content
    story = []

    # -- Dynamic styles based on template for Cover Text --
    # We can't easily change the style definition mid-stream for just one paragraph without defining multiple,
    # so we will assume standard dark text is fine for Classic/Modern. 
    # For Dark theme, we might want white text.
    
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
        # Group Question and Answer to keep together
        # And ensure one Q per page (by adding PageBreak after)
        
        qa_block = [
            Paragraph(page.quiz, styles['QuestionText']),
            Paragraph(page.answer.replace('\n', '<br/>'), styles['AnswerText'])
        ]
        
        story.append(KeepTogether(qa_block))
        story.append(PageBreak())

    # Build
    doc.build(story, onFirstPage=on_cover_page)
    buffer.seek(0)
    
    filename = f"{book.title}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def finish_book(request, book_id):
    book = get_object_or_404(Book, id=book_id, user=request.user)
    if request.method == "POST":
        book.status = 'completed'
        book.save()
    return redirect("dashboard")
