import os

import numpy as np
from django.db import models
from django.dispatch import receiver

from api.models.cluster import Cluster, get_unknown_cluster
from api.models.person import Person, get_unknown_person
from api.models.photo import Photo


class Face(models.Model):
    photo = models.ForeignKey(Photo,
                              related_name="faces",
                              on_delete=models.CASCADE,
                              blank=False,
                              null=True)
    image = models.ImageField(upload_to="faces", null=True)
    image_path = models.FilePathField()

    person = models.ForeignKey(Person,
                               on_delete=models.SET(get_unknown_person),
                               related_name="faces")

    cluster = models.ForeignKey(
        Cluster,
        related_name="faces",
        on_delete=models.SET(get_unknown_cluster),
        blank=True,
        null=True,
    )
    person_label_is_inferred = models.BooleanField(null=True, db_index=True)
    person_label_probability = models.FloatField(default=0.0, db_index=True)

    location_top = models.IntegerField()
    location_bottom = models.IntegerField()
    location_left = models.IntegerField()
    location_right = models.IntegerField()

    encoding = models.TextField()

    def __str__(self):
        return "%d" % self.id

    def get_encoding_array(self):
        return np.frombuffer(bytes.fromhex(self.encoding))


# From: https://stackoverflow.com/questions/16041232/django-delete-filefield
@receiver(models.signals.post_delete, sender=Face)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
