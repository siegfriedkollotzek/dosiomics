from django import forms
from django.http import HttpResponse
from django.shortcuts import render


class FileForm(forms.Form):
    file = forms.FileField()


def mfi(request):
    if request.method == "POST":
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            return HttpResponse("Filegoesherre")
    else:
        form = FileForm()
    return render(request, template_name='mfi/index.html', context={'form': form})
