from django import forms
from django.http import JsonResponse, FileResponse
from django.shortcuts import render, get_object_or_404

from .MFI_total_noGUI_EasyOCR import CellAnalyzer
from .models import Mfi


class FileForm(forms.ModelForm):
    class Meta:
        model = Mfi
        fields = ['file']


def mfi_form(request):
    if request.method == "POST":
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                mfi_object = form.save()
                t = CellAnalyzer(uuid=mfi_object.uuid)
                t.daemon = True
                t.start()
                return JsonResponse(status=200, data={'uuid': mfi_object.uuid})

            except Exception as e:
                return JsonResponse(status=400, data={"error": str(e)})
        else:
            return JsonResponse(status=400, data={"error": 'form invalid'})
    else:
        form = FileForm()
    return render(request, template_name='mfi/index.html', context={'form': form})


def mfi_status(request, uuid: str):
    return render(request, 'mfi/status.html', {'mfi': Mfi.objects.get(uuid=uuid)})


def mfi_download(request, uuid: str):
    mfi = get_object_or_404(Mfi, pk=uuid)
    return FileResponse(
        mfi.file_output.open(),
        as_attachment=True,
        filename=mfi.file_output.name
    )
