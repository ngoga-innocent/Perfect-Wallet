import django_filters

from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    transaction_type = django_filters.ChoiceFilter(
        field_name="transaction_type",
        choices=Transaction.TransactionType.choices,
    )

    account = django_filters.NumberFilter(
        field_name="account_id",
    )

    destination_account = django_filters.NumberFilter(
        field_name="destination_account_id",
    )

    category = django_filters.CharFilter(
        field_name="category",
        lookup_expr="iexact",
    )

    date_from = django_filters.DateFilter(
        field_name="transaction_date",
        lookup_expr="date__gte",
    )

    date_to = django_filters.DateFilter(
        field_name="transaction_date",
        lookup_expr="date__lte",
    )

    min_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="gte",
    )

    max_amount = django_filters.NumberFilter(
        field_name="amount",
        lookup_expr="lte",
    )

    class Meta:
        model = Transaction
        fields = [
            "transaction_type",
            "account",
            "destination_account",
            "category",
            "date_from",
            "date_to",
            "min_amount",
            "max_amount",
        ]