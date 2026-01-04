from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from .models import Book, BookPageAnswer, BookCover, BookPageQuestion
from .forms import BookForm, BookPageForm
from .utils import generate_book_pdf, send_telegram_notification
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
        form = BookPageForm(request.POST, request.FILES, instance=current_answer)
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


@login_required
def generate_pdf(request, book_id):
    book = get_object_or_404(Book, id=book_id, user=request.user)
    buffer = generate_book_pdf(book)
    filename = f"{book.title}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def finish_book(request, book_id):
    book = get_object_or_404(Book, id=book_id, user=request.user)
    if request.method == "POST":
        book.status = 'completed'
        book.save()
        
        # Send Telegram Notification
        try:
            pdf_buffer = generate_book_pdf(book)
            send_telegram_notification(book, pdf_buffer)
        except Exception as e:
            print(f"Error sending notification: {e}")
            # Don't block user flow if notification fails
            
    return redirect("dashboard")
