from django.contrib.auth.decorators import login_required
import base64, uuid
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import BookCoverForm


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