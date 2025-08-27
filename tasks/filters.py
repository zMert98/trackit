from datetime import datetime, timedelta

from rest_framework import filters


class DateFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        param_filter = request.query_params.get("date")
        tomorrow = (datetime.today() + timedelta(days=1)).date()
        today = datetime.today().date()

        if param_filter == "planned":
            return queryset.filter(planned_date__gt=tomorrow)
        elif param_filter == "today":
            return queryset.filter(planned_date=today)
        elif param_filter == "not sorted":
            return queryset.filter(planned_date=None)
        return queryset
