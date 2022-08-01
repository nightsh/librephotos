import math

import numpy as np

from api.models.cluster import UNKNOWN_CLUSTER_ID, Cluster, get_unknown_cluster
from api.models.face import Face
from api.models.person import Person, get_or_create_person, get_unknown_person
from api.models.user import User


class ClusterManager:

    @staticmethod
    def get_global_data_count():
        return Face.objects.count()

    @staticmethod
    def try_add_cluster(user: User, cluster_id: int,
                        faces: list[Face]) -> list[Cluster]:
        added_clusters: list[Cluster] = []
        known_faces: list[Face] = []
        face_ids_by_cluster: dict[int, list[int]] = dict()
        unknown_faces: list[Face] = []
        unknown_ids: list[int] = []
        encoding_by_person: dict[int, list[np.ndarray]] = dict()

        face: Face
        new_cluster: Cluster
        unknown_cluster: Cluster = get_unknown_cluster()
        unknown_person: Person = get_unknown_person()
        for face in faces:
            if (face.person.name == "unknown"
                    or face.person.name == Person.UNKNOWN_PERSON_NAME
                    or face.person_label_is_inferred is True):
                unknown_faces.append(face)
                unknown_ids.append(face.id)
            else:
                known_faces.append(face)
        if len(known_faces) == 0:
            new_cluster: Cluster
            new_person: Person
            if cluster_id == UNKNOWN_CLUSTER_ID:
                new_cluster = unknown_cluster
                new_person = unknown_person
            else:
                new_person = get_or_create_person(name="Unknown " +
                                                  str(cluster_id + 1),
                                                  cluster_owner=user)
                new_person.kind = Person.KIND_CLUSTER
                new_person.cluster_owner = user
                new_person.save()
                new_cluster = Cluster.get_or_create_cluster_by_id(
                    user, cluster_id)
                new_cluster.name = "Cluster " + str(cluster_id)

            new_cluster.person = new_person
            encoding_by_person[new_cluster.person.id] = []
            new_cluster.save()
            added_clusters.append(new_cluster)

            for face in unknown_faces:
                encoding_by_person[new_cluster.person.id].append(
                    face.get_encoding_array())
            Face.objects.filter(id__in=unknown_ids).update(
                cluster=new_cluster,
                person=new_person,
                person_label_is_inferred=None)
        else:
            clusters_by_person: dict[int, Cluster] = dict()
            mean_encoding_by_cluster: dict[int, list[np.ndarray]] = dict()
            idx: int = 0
            for face in known_faces:
                if face.person.id not in clusters_by_person.keys():
                    print("adding new cluster: {}".format(idx + 1))
                    idx = idx + 1
                    new_cluster = Cluster.get_or_create_cluster_by_name(
                        user, "Cluster " + str(cluster_id) + "-" + str(idx))
                    new_cluster.cluster_id = cluster_id
                    new_cluster.person = face.person
                    clusters_by_person[new_cluster.person.id] = new_cluster
                    added_clusters.append(new_cluster)
                    encoding_by_person[face.person.id] = []
                    face_ids_by_cluster[new_cluster.id] = []
                else:
                    print("using existing cluster")
                    new_cluster = clusters_by_person[face.person.id]
                encoding_by_person[face.person.id].append(
                    face.get_encoding_array())
                face_ids_by_cluster[new_cluster.id].append(face.id)
            for new_cluster in added_clusters:
                Face.objects.filter(
                    id__in=face_ids_by_cluster[new_cluster.id]).update(
                        cluster=new_cluster, person_label_is_inferred=False)

            # Set initial metadata on the split clusters based on known faces
            for new_cluster in added_clusters:
                new_cluster.set_metadata(
                    encoding_by_person[new_cluster.person.id])
                mean_encoding_by_cluster[
                    new_cluster.id] = new_cluster.get_mean_encoding_array()

            # Clear the face IDs list to prepare for processing the unknown faces
            for new_cluster in added_clusters:
                face_ids_by_cluster[new_cluster.id] = []

            # Loop over all unknown faces and find the closest "known" cluster
            for face in unknown_faces:
                closest_cluster: Cluster
                min_distance: np.float64 = np.Infinity
                encoding = face.get_encoding_array()
                for new_cluster in added_clusters:
                    distance = math.dist(
                        encoding, mean_encoding_by_cluster[new_cluster.id])
                    if distance < min_distance:
                        closest_cluster = new_cluster
                        min_distance = distance
                face_ids_by_cluster[closest_cluster.id].append(face.id)
                encoding_by_person[closest_cluster.person.id].append(encoding)
            for new_cluster in added_clusters:
                if new_cluster.person is unknown_person:
                    Face.objects.filter(
                        id__in=face_ids_by_cluster[new_cluster.id]).update(
                            cluster=new_cluster,
                            person_label_is_inferred=None,
                            person=new_cluster.person,
                    )
                else:
                    Face.objects.filter(
                        id__in=face_ids_by_cluster[new_cluster.id]).update(
                            cluster=new_cluster,
                            person_label_is_inferred=True,
                            person=new_cluster.person,
                    )

        # Update statistics again and save everything, since we've added more faces
        for new_cluster in added_clusters:
            new_cluster.set_metadata(encoding_by_person[new_cluster.person.id])
            new_cluster.save()

        return added_clusters
