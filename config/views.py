from django.contrib.auth.decorators import login_required
import base64, uuid
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import BookCoverForm, BookPageAnswerForm
from .models import BookPageQuestion, BookPageAnswer


@login_required
def home(request):
    return render(request, 'index/index.html')


def create_cover(request):
    if request.method == "POST":
        form = BookCoverForm(request.POST)
        if form.is_valid():
            book_cover = form.save(commit=False)

            image_data = request.POST.get('cover_image')
            if image_data:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
                book_cover.cover_image = ContentFile(base64.b64decode(imgstr), name=f"cover.{ext}")

            book_cover.save()
            messages.success(request, "Обложка успешно сохранена!")  # ✔ исправлено: добавлен request
            return redirect('create_cover')

        return render(request, "book_cover/create.html", {"form": form})

    else:
        form = BookCoverForm()
        return render(request, "book_cover/create.html", {"form": form})

@login_required
def answer_question(request, question_id):
    question = get_object_or_404(BookPageQuestion, id=question_id)

    if request.method == 'POST':
        form = BookPageAnswerForm(request.POST, request.FILES)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.user = request.user
            answer.quiz = question
            answer.save()
            return redirect('answer_question', question_id=question.id)
    else:
        form = BookPageAnswerForm()

    return render(request, 'book_pages/answer_questions.html', {
        'form': form,
        'question': question,
    })
