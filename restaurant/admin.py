from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import MenuCategory, MenuItem, Cart, CartItem, Order, OrderItem, Inventory, Table, Reservation


@admin.action(description='Export selected orders to CSV')
def export_to_csv(modeladmin, request, queryset):
    """Admin action to export orders as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Customer', 'Email', 'Total', 'Status', 'Payment Status', 'Payment Method', 'Created'])
    for order in queryset:
        writer.writerow([
            order.id,
            order.user.get_full_name() or order.user.username,
            order.user.email,
            order.total,
            order.get_status_display(),
            order.get_payment_status_display(),
            order.get_payment_method_display() if order.payment_method else '',
            order.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    return response


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'available_status', 'image_preview')
    list_filter = ('category', 'stock')
    list_editable = ('price', 'stock')
    search_fields = ('name', 'description')
    readonly_fields = ('image_preview',)

    def available_status(self, obj):
        return obj.available
    available_status.boolean = True
    available_status.short_description = 'Available'

    def image_preview(self, obj):
        return obj.admin_image_preview()
    image_preview.short_description = 'Preview'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at', 'item_count', 'total_display')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'

    def total_display(self, obj):
        return f"${obj.total:.2f}"
    total_display.short_description = 'Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'item', 'quantity', 'subtotal_display')
    list_filter = ('cart__user',)
    search_fields = ('item__name',)

    def subtotal_display(self, obj):
        return f"${obj.subtotal:.2f}"
    subtotal_display.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'status', 'payment_status', 'payment_method', 'total_display', 'item_count')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('id', 'user__username', 'user__email', 'notes')
    readonly_fields = ('created_at',)
    actions = [export_to_csv]
    list_editable = ('status', 'payment_status')  # Quick status updates

    def total_display(self, obj):
        return f"${obj.total:.2f}"
    total_display.short_description = 'Total'

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item', 'quantity', 'price', 'subtotal_display')
    list_filter = ('order__status',)
    search_fields = ('item__name', 'order__id')

    def subtotal_display(self, obj):
        return f"${obj.subtotal:.2f}"
    subtotal_display.short_description = 'Subtotal'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'alert_threshold', 'needs_restock', 'last_updated')
    list_filter = ('alert_threshold',)
    search_fields = ('item__name',)

    def needs_restock(self, obj):
        return obj.needs_restock()
    needs_restock.boolean = True
    needs_restock.short_description = 'Needs Restock'


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'capacity')
    list_filter = ('capacity',)
    search_fields = ('number',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'date', 'time', 'guests', 'table', 'customer')
    list_filter = ('date', 'time', 'guests')
    search_fields = ('name', 'email', 'customer__username')
    date_hierarchy = 'date'