from django.urls import path

from .views import (
    BulkDeletePhotosView,
    BulkDownloadPhotosView,
    CompressPhotosView,
    DeletePhotoView,
    ListPhotosView,
    PhotoGalleryView,
    ReorderPhotosView,
    UpdatePhotoView,
    UploadPhotosView,
)

app_name = 'photos'

urlpatterns = [
    # Gallery admin
    path('gallery/',               PhotoGalleryView.as_view(),      name='gallery'),
    path('gallery/bulk-delete/',   BulkDeletePhotosView.as_view(),  name='bulk_delete'),
    path('gallery/bulk-download/', BulkDownloadPhotosView.as_view(), name='bulk_download'),
    path('gallery/compress/',      CompressPhotosView.as_view(),    name='compress'),

    # Per-object endpoints (camera widget)
    path('<int:ct_id>/<int:object_id>/',                           ListPhotosView.as_view(),    name='list'),
    path('<int:ct_id>/<int:object_id>/upload/',                    UploadPhotosView.as_view(),  name='upload'),
    path('<int:ct_id>/<int:object_id>/update/',                    UpdatePhotoView.as_view(),   name='update'),
    path('<int:ct_id>/<int:object_id>/reorder/',                   ReorderPhotosView.as_view(), name='reorder'),
    path('<int:ct_id>/<int:object_id>/delete/<int:photo_id>/',     DeletePhotoView.as_view(),   name='delete'),
]
