from django.urls import path
from .views import UploadCSVView, DatasetListView, DatasetDetailView, DatasetPDFReportView, HelloView 

urlpatterns = [
    path('upload/', UploadCSVView.as_view(), name='upload_csv'),
    path('datasets/', DatasetListView.as_view(), name='dataset_list'),
    path('datasets/<int:pk>/', DatasetDetailView.as_view(), name='dataset_detail'),
    path('datasets/<int:pk>/report/', DatasetPDFReportView.as_view(), name='dataset_pdf'),
    path('hello/', HelloView.as_view(), name='hello'),
]
