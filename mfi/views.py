from pathlib import Path

from django import forms
from django.http import HttpResponse
from django.shortcuts import render

from .MFI_total_noGUI_EasyOCR import CellAnalyzer


class FileForm(forms.Form):
    file = forms.FileField()


def mfi(request):
    if request.method == "POST":
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                analyzer = CellAnalyzer(form.cleaned_data['file'])
                analyzer.load_image()
                analyzer.detect_scale_bar_and_calculate_size()
                analyzer.extract_channels()
                analyzer.find_largest_cell()
                analyzer.calculate_mfi()
                xls_filename = analyzer.create_report()

                with open(xls_filename, 'rb') as f:
                    response = HttpResponse(
                        f.read(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{Path(xls_filename).name}"'

                return response
            except Exception as e:
                form.add_error('file', f'Something went wrong: {e}')
    else:
        form = FileForm()
    return render(request, template_name='mfi/index.html', context={'form': form})
