from restaurant.models import Reservation, Table

def create_reservation(data, user=None):
    """Create a reservation with optional user."""
    reservation = Reservation(**data)
    if user and user.is_authenticated:
        reservation.customer = user
        if not reservation.email:
            reservation.email = user.email
    reservation.save()
    return reservation

def get_available_tables(date, time, guests):
    """Find available tables for given datetime and party size."""
    reserved_tables = Reservation.objects.filter(
        date=date, time=time
    ).values_list('table_id', flat=True)
    available = Table.objects.exclude(pk__in=reserved_tables).filter(capacity__gte=guests)
    return available
