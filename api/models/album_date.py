from django.db import models
from django.db.models import Q

from api.models.photo import Photo
from api.models.user import User, get_deleted_user


class VisibleAlbumDatePhotoManager(models.Manager):

    def get_queryset(self):
        return (super().get_queryset().filter(
            Q(photos__hidden=False)
            & Q(photos__aspect_ratio__isnull=False)
            & Q(photos__deleted=False)))


class AlbumDate(models.Model):
    title = models.CharField(blank=True,
                             null=True,
                             max_length=512,
                             db_index=True)
    date = models.DateField(db_index=True, null=True)
    photos = models.ManyToManyField(Photo)
    favorited = models.BooleanField(default=False, db_index=True)
    location = models.JSONField(blank=True, db_index=True, null=True)
    owner = models.ForeignKey(User,
                              on_delete=models.SET(get_deleted_user),
                              default=None)
    shared_to = models.ManyToManyField(User,
                                       related_name="album_date_shared_to")
    visible = VisibleAlbumDatePhotoManager()
    objects = models.Manager()

    class Meta:
        unique_together = ("date", "owner")

    def __str__(self):
        return "%d: %s" % (self.id, self.title)

    def ordered_photos(self):
        return self.photos.all().order_by("-exif_timestamp")


def get_or_create_album_date(date, owner):
    try:
        return AlbumDate.objects.get_or_create(date=date, owner=owner)[0]
    except AlbumDate.MultipleObjectsReturned:
        return AlbumDate.objects.filter(date=date, owner=owner).first()


def get_album_date(date, owner):
    try:
        return AlbumDate.objects.get(date=date, owner=owner)
    except Exception:
        return None


def get_album_nodate(owner):
    return AlbumDate.objects.get_or_create(date=None, owner=owner)[0]
