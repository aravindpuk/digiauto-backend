from rest_framework import serializers

from garage.models import Branch, Garage


class GarageSerializer(serializers.ModelSerializer):
    # Accept lat/lng from Flutter
    latitude  = serializers.FloatField()
    longitude = serializers.FloatField()

    class Meta:
        model  = Garage
        fields = ["name", "email", "mobile", "latitude", "longitude"]

    def create(self, validated_data):
        user = self.context["user"]

        # Create garage
        garage = Garage.objects.create(**validated_data)

        # Auto-create a default main branch with same coordinates
        branch = Branch.objects.create(
            garage    = garage,
            name      = "Main Branch",
            latitude  = validated_data.get("latitude"),
            longitude = validated_data.get("longitude"),
        )

        # Assign user to this branch
        user.branches.add(branch)
        user.save()

        return garage, branch


class BranchSerializer(serializers.ModelSerializer):
    garage_name = serializers.CharField(source="garage.name", read_only=True)

    class Meta:
        model  = Branch
        fields = ["id", "name", "garage_name", "latitude", "longitude"]