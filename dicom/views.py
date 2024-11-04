from io import BytesIO

import matplotlib.pyplot as plt
import pydicom
from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DicomFile
from .serializers import FileUploadSerializer

NUMBER_OF_POINTS = 80


class FileUploadView(APIView):
    @staticmethod
    def post(request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']
            try:
                d = pydicom.read_file(file)
                beams = [{
                    'name': b.get('BeamName'),
                    'index': j,
                    'control_points': [i for i in range(len(b.get('ControlPointSequence')))]
                } for j, b in enumerate(d.get("BeamSequence"))]
                serializer.validated_data['uploaded_by'] = User.objects.get_or_create(username='default')[0]
                obj = serializer.save()
                return Response(data={"beams": beams, 'uuid': obj.uuid})
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_leaf_boundaries(ds, control_point: int, beam_number: int):
    """
    :param control_point:
    :param dataset: dicom dataset
    :param beam_number:
    :param beam_limiting_device_position_sequence: usually 2
    :return: If beam_number is None, returns a list of all 31 beams with dictionaries for 'ASYMX', 'ASYMY' and 'MLCX'.
             Else return a single dictionary.
    """

    def get_jaw_leaf_list(d, bm, cp, beam_limiting_device_position):
        return d.get("BeamSequence")[bm][
            'ControlPointSequence'][cp][
            'BeamLimitingDevicePositionSequence'][beam_limiting_device_position][
            'LeafJawPositions']

    return {
        'ASYMX': get_jaw_leaf_list(ds, beam_number, control_point, 0),
        'ASYMY': get_jaw_leaf_list(ds, beam_number, control_point, 1),
        'MLCX': get_jaw_leaf_list(ds, beam_number, control_point, 2),
    }


def plot_control_point(request, file_uuid, beam: int, control_point: int, x_lim=None, y_lim=None,
                       image_ratio=0.8):
    ds = pydicom.dcmread(DicomFile.objects.get(uuid=file_uuid).file.path)

    bs = get_leaf_boundaries(ds, control_point, beam)
    x_max = max(bs["ASYMX"][0], bs["ASYMX"][1])
    x_min = min(bs["ASYMX"][0], bs["ASYMX"][1])
    x_diff = x_max - x_min
    y_max = max(bs["ASYMY"][0], bs["ASYMY"][1])
    y_min = min(bs["ASYMY"][0], bs["ASYMY"][1])
    y_diff = y_max - y_min
    plt.figure(figsize=(7, 7 * image_ratio))
    plt.xlim([-250, 250])
    plt.ylim([-250, 250])

    if x_lim is None:
        plt.xlim([x_min - x_diff * 0.1, x_max + x_diff * 0.1])
    else:
        plt.xlim(x_lim)
    if y_lim is None:
        plt.ylim([y_min - y_diff * 0.1, y_max + y_diff * 0.1])
    else:
        plt.ylim(y_lim)

    # vertical lines
    plt.axvline(x=x_min, color='b')
    plt.text(x_min - x_diff * 0.01, 0, 'Y1', rotation=90, horizontalalignment='right', verticalalignment='center')
    plt.axvline(x=x_max, color='b')
    plt.text(x_max + x_diff * 0.01, 0, 'Y2', rotation=90, horizontalalignment='left', verticalalignment='center')

    # horizontal lines
    plt.axhline(y=y_min, color='b')
    plt.text(50, y_min - y_diff * 0.01, 'X1', horizontalalignment='center', verticalalignment='top')
    plt.axhline(y=y_max, color='b')
    plt.text(50, y_max + y_diff * 0.01, 'X2', horizontalalignment='center', verticalalignment='bottom')

    # MLCX
    if int(len(list(bs["MLCX"])) / 2) != NUMBER_OF_POINTS:
        raise Exception(
            f"More or less than {NUMBER_OF_POINTS} leaf pairs were found: {int(len(list(bs['MLCX'])) / 2)}!")

    y = -200
    ys1 = []
    xs1 = []
    ys2 = []
    xs2 = []
    for i in range(NUMBER_OF_POINTS):
        ys1.append(y)
        ys2.append(-y)
        y += 5
        ys1.append(y)
        ys2.append(-y)
        xs1.append(bs["MLCX"][i])
        xs1.append(bs["MLCX"][i])
        xs2.append(bs["MLCX"][i + NUMBER_OF_POINTS])
        xs2.append(bs["MLCX"][i + NUMBER_OF_POINTS])

    plt.plot(xs1, ys1, color="g")
    plt.plot(xs2, ys2, color="g")
    plt.title(f'Beam: {beam}, Control point: {control_point}')

    # Step 2: Save the plot to an in-memory buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)

    # Step 3: Create an HTTP response with the image content
    return HttpResponse(buffer, content_type='image/png')
