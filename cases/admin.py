from django.contrib import admin
from .models import School, Student, Case, CaseEvent, Appointment

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('code', 'age', 'grade_level', 'school')
    search_fields = ('code',)
    list_filter = ('school', 'grade_level')

admin.site.register(School)
admin.site.register(Case)
admin.site.register(CaseEvent)
admin.site.register(Appointment) 