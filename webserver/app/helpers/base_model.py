from datetime import datetime
from flask import request
from flask_sqlalchemy.pagination import QueryPagination
from sqlalchemy import create_engine, Column
from sqlalchemy.orm import Relationship, declarative_base
from flask_sqlalchemy import SQLAlchemy
from app.helpers.exceptions import InvalidDBEntry, InvalidRequest
from app.helpers.const import build_sql_uri


engine = create_engine(build_sql_uri())
Base = declarative_base()
db = SQLAlchemy(model_class=Base)


# Another helper class for common methods
class BaseModel():
    @classmethod
    def _query(cls) -> QueryPagination:
        try:
            page = int(request.values.get("page", '1'))
            per_page = int(request.values.get("per_page", '25'))
        except ValueError as ve:
            raise InvalidRequest("page and per_page parameters should be integers") from ve

        return cls.query.paginate(page=page, per_page=per_page)

    def sanitized_dict(self) -> dict[str, bool|int|str]:
        """
        Based on the list of column names, conditionally render the values
        in a dictionary
        """
        jsonized = {}
        for field in self._get_fields_name():
            val = getattr(self, field)
            match val:
                case int() | bool() | None:
                    jsonized[field] = val
                case datetime():
                    jsonized[field] = val.strftime("%Y-%m-%d %H:%M:%S")
                case BaseModel():
                    pass
                case _:
                    jsonized[field] = str(val)
        return jsonized

    def add(self, commit=True):
        db.session.add(self)
        db.session.flush()
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        db.session.delete(self)
        db.session.flush()
        if commit:
            db.session.commit()

    @classmethod
    def get_all(cls) -> list[dict]:
        obj_list = cls._query()
        jsonized = []
        for obj in obj_list.items:
            jsonized.append(obj.sanitized_dict())
        return obj_list

    @classmethod
    def _get_fields(cls) -> list[Column]:
        return cls.__table__.columns._all_columns

    @classmethod
    def _get_fields_name(cls) -> list[str]:
        return [col.name for col in cls._get_fields()]

    @classmethod
    def is_field_required(cls, attribute: Column) -> bool:
        """
        Generalized check for a column to be required in a request body
        The column, to be required, needs to:
            - not be nullable
            - not have a default value
            - not be a primary key (e.g. id is not allowed as a request body)
        """
        return not (attribute.nullable or attribute.primary_key or attribute.server_default is not None)

    @classmethod
    def _get_required_fields(cls):
        return [f.name for f in cls._get_fields() if cls.is_field_required(f)]

    @classmethod
    def validate(cls, data:dict):
        """
        Make sure we have all required fields. Set to None if missing
        """
        if not data:
            raise InvalidDBEntry(f"No usable data found for table {cls.__tablename__}")
        valid = data.copy()
        for k, v in data.items():
            field = getattr(cls, k, None)
            if field is None or isinstance(v, dict) or isinstance(v, list) or isinstance(field.property, Relationship):
                continue
            if getattr(cls, k).nullable:
                valid[k] = v
            elif v is None:
                raise InvalidDBEntry(f"Field {k} has invalid value")
        for req_field in cls._get_required_fields():
            if req_field not in list(valid.keys()):
                raise InvalidDBEntry(f"Field \"{req_field}\" missing")
        return valid
