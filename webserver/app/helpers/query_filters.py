import re
from sqlalchemy.sql import select
from app.helpers.db import Base

FILTERS = [
    'ne',
    'eq',
    'lt',
    'gt',
    'lte',
    'gte',
]


def parse_query_params(model: Base, query_params: list):
    """
    We aim to convert query strings in models fields
    to be used as filters
    """
    current_query = select(model)
    for qp_f, qp_v in query_params.items():
        added = False
        for k in FILTERS:
            if re.findall(f'.+__{k}$', qp_f):
                field = qp_f.replace(f'__{k}', '')
                if k == 'ne':
                    current_query = current_query.where(getattr(model, field) != qp_v)
                if k == 'eq':
                    current_query = current_query.where(getattr(model, field) == qp_v)
                if k == 'gt':
                    current_query = current_query.where(getattr(model, field) > qp_v)
                if k == 'lt':
                    current_query = current_query.where(getattr(model, field) < qp_v)
                if k == 'gte':
                    current_query = current_query.where(getattr(model, field) >= qp_v)
                if k == 'lte':
                    current_query = current_query.where(getattr(model, field) <= qp_v)
                added = True
                break
        if not added:
            current_query = current_query.where(getattr(model, qp_f) == qp_v)

    return current_query

