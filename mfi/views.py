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
                print(f"######################################################################")
                print(f"-----------------------------Start------------------------------------")
                print(f"######################################################################")
                analyzer = CellAnalyzer(form.cleaned_data['file'])
                print(f"######################################################################")
                print(f"-------------------------------1--------------------------------------")
                print(f"######################################################################")
                analyzer.load_image()
                print(f"######################################################################")
                print(f"-------------------------------2--------------------------------------")
                print(f"######################################################################")
                analyzer.detect_scale_bar_and_calculate_size()
                print(f"######################################################################")
                print(f"-------------------------------3--------------------------------------")
                print(f"######################################################################")
                analyzer.extract_channels()
                print(f"######################################################################")
                print(f"-------------------------------4--------------------------------------")
                print(f"######################################################################")
                analyzer.find_largest_cell()
                print(f"######################################################################")
                print(f"-------------------------------5--------------------------------------")
                print(f"######################################################################")
                analyzer.calculate_mfi()
                print(f"######################################################################")
                print(f"-------------------------------6--------------------------------------")
                print(f"######################################################################")
                xls_filename = analyzer.create_report()

                with open(xls_filename, 'rb') as f:
                    response = HttpResponse(
                        f.read(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{Path(xls_filename).name}"'

                # ✅ Clean only files inside 'tempfiles' (keep the folder)
                temp_dir = Path('tempfiles')
                for file in temp_dir.glob('*'):
                    try:
                        file.unlink()

                    except Exception as e:
                        print(f"Could not delete {file}: {e}")
                print(f"Directory tempfiles cleared")
                print(f"######################################################################")
                print(f"-----------------------------End--------------------------------------")
                print(f"######################################################################")

                return response
            except Exception as e:
                form.add_error('file', f'Something went wrong: {e}')
    else:
        form = FileForm()
    return render(request, template_name='mfi/index.html', context={'form': form,})
