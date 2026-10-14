from .models import VehicleMake, VehicleModel


def resolve_vehicle_model(model_name, make_name):
    """Return the catalog model for a make/model pair, creating it if needed."""
    if not model_name or not make_name:
        return None

    make_name = make_name.strip()
    model_name = model_name.strip()
    if not make_name or not model_name:
        return None

    make, _ = VehicleMake.objects.get_or_create(
        name__iexact=make_name, defaults={"name": make_name}
    )
    model, _ = VehicleModel.objects.get_or_create(
        name__iexact=model_name,
        fkMaker=make,
        defaults={"name": model_name},
    )
    return model


def update_vehicle(vehicle, vehicle_model, data):
    """Apply supplied vehicle details and save only when something changed."""
    changed = False
    vehicle_number = data.get("vehicle_number", "").strip().upper()
    if vehicle_number and vehicle.vehicle_number != vehicle_number:
        vehicle.vehicle_number = vehicle_number
        changed = True
    if vehicle_model and vehicle.vehicle_model_id != vehicle_model.id:
        vehicle.vehicle_model = vehicle_model
        changed = True
    for field in ("year", "chassis_number", "engine_number"):
        value = data.get(field, "").strip()
        if value and getattr(vehicle, field) != value:
            setattr(vehicle, field, value)
            changed = True
    if changed:
        vehicle.save()
