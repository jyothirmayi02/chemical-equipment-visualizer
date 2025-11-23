import io
import pandas as pd
from django.http import FileResponse, HttpResponseBadRequest
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from reportlab.pdfgen import canvas

from .models import Dataset
from .serializers import DatasetSerializer


class HelloView(APIView):
    #permission_classes = [permissions.AllowAny]  # no auth needed to test
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"message": "API is working!"})

class UploadCSVView(APIView):
    #permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]


    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # Read CSV using pandas
        try:
            df = pd.read_csv(file_obj)
        except Exception as e:
            return Response({'error': f'Invalid CSV: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        # EXPECTED COLUMNS: Equipment Name, Type, Flowrate, Pressure, Temperature
        required_cols = ['Equipment Name', 'Type', 'Flowrate', 'Pressure', 'Temperature']
        for col in required_cols:
            if col not in df.columns:
                return Response({'error': f'Missing column: {col}'}, status=status.HTTP_400_BAD_REQUEST)

        # Compute statistics
        total_count = len(df)
        avg_flowrate = df['Flowrate'].mean()
        avg_pressure = df['Pressure'].mean()
        avg_temperature = df['Temperature'].mean()
        type_distribution = df['Type'].value_counts().to_dict()

        summary = {
            'total_count': int(total_count),
            'average_flowrate': float(avg_flowrate),
            'average_pressure': float(avg_pressure),
            'average_temperature': float(avg_temperature),
            'type_distribution': type_distribution,
        }

        preview_rows = df.head(10).to_dict(orient='records')

        # Save original file in storage
        file_obj.seek(0)  # reset pointer
        saved_path = default_storage.save(f"uploads/{file_obj.name}", ContentFile(file_obj.read()))

        dataset = Dataset.objects.create(
            name=file_obj.name,
            original_file=saved_path,
            summary=summary,
            preview_rows=preview_rows
        )

        serializer = DatasetSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DatasetListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        datasets = Dataset.objects.all()
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data)


class DatasetDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            dataset = Dataset.objects.get(pk=pk)
            serializer = DatasetSerializer(dataset)
            return Response(serializer.data)
        except Dataset.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class DatasetPDFReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            dataset = Dataset.objects.get(pk=pk)
        except Dataset.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)

        p.drawString(100, 800, f"Dataset Report: {dataset.name}")
        p.drawString(100, 780, f"Uploaded at: {dataset.uploaded_at.strftime('%Y-%m-%d %H:%M')}")

        summary = dataset.summary
        y = 750
        p.drawString(100, y, f"Total Equipment Count: {summary['total_count']}")
        y -= 20
        p.drawString(100, y, f"Average Flowrate: {summary['average_flowrate']:.2f}")
        y -= 20
        p.drawString(100, y, f"Average Pressure: {summary['average_pressure']:.2f}")
        y -= 20
        p.drawString(100, y, f"Average Temperature: {summary['average_temperature']:.2f}")
        y -= 40
        p.drawString(100, y, "Equipment Type Distribution:")
        y -= 20
        for t, c in summary['type_distribution'].items():
            p.drawString(120, y, f"{t}: {c}")
            y -= 20

        p.showPage()
        p.save()
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=True, filename='dataset_report.pdf')

