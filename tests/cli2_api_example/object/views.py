from rest_framework import permissions, serializers, viewsets
from .models import Object


class ObjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Object
        fields = ('id', 'name', 'data')


class ObjectViewSet(viewsets.ModelViewSet):
    queryset = Object.objects.all()
    serializer_class = ObjectSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if name := self.request.GET.get('name'):
            qs = qs.filter(name=name)
        return qs
