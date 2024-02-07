from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, update
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from app.helpers.db import BaseModel, db
from app.models.datasets import Datasets
from app.helpers.keycloak import Keycloak
from app.exceptions import DBError


class Requests(db.Model, BaseModel):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    description = Column(String(2048))

    # This will be a FK or a Keycloak UUID. Something to track a user
    requested_by = Column(String(64), nullable=False)
    project_name = Column(String(64), nullable=False)
    status = Column(String(32), default='pending')
    proj_start = Column(DateTime(timezone=False), nullable=False)
    proj_end = Column(DateTime(timezone=False), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), onupdate=func.now())

    dataset_id = Column(Integer, ForeignKey(Datasets.id, ondelete='CASCADE'))
    dataset = relationship("Datasets")

    def __init__(self,
                 title:str,
                 project_name:str,
                 dataset:Datasets,
                 requested_by:str,
                 proj_start:datetime,
                 proj_end:datetime,
                 description:str='',
                 created_at:datetime=datetime.now()
        ):
        self.title = title
        self.description = description
        self.project_name = project_name
        # Not sure how to track the dataset yet, as DAR provider will have different IDs from the internal ones
        self.dataset = dataset
        self.requested_by = requested_by
        self.proj_start = proj_start
        self.proj_end = proj_end
        self.created_at = created_at
        self.updated_at = datetime.now()

    def approve(self):
        """
        Method to orchestrate the Keycloak objects creation
        """
        session = db.session
        global_kc_client = Keycloak()

        admin_global_policy = global_kc_client.get_role('Administrator')
        system_global_policy = global_kc_client.get_role('System')
        global_kc_client.create_client(self.project_name)

        kc_client = Keycloak(self.project_name)

        scopes = ["can_admin_dataset","can_exec_task", "can_admin_task", "can_access_dataset"]
        created_scopes = []
        for scope in scopes:
            created_scopes.append(kc_client.create_scope(scope))

        ds = session.get(Datasets, self.dataset_id)

        resource = kc_client.create_resource({
            "name": f"{ds["id"]}-{ds["name"]}",
            "owner": {"id": kc_client.client_id, "name": self.project_name},
            "displayName": f"{ds.id} {ds.name}",
            "scopes": created_scopes,
            "uris": []
        })

        policies = []
        # Create admin policy
        policies.append(kc_client.create_policy({
            "name": f"{ds.id} - {ds.name} Admin Policy",
            "description": f"List of users allowed to administrate the {ds.name} dataset",
            "logic": "POSITIVE",
            "roles": [{"id": admin_global_policy["id"], "required": False}]
        }, "/role"))
        # Create system policy
        policies.append(kc_client.create_policy({
            "name": f"{ds.id} - {ds.name} System Policy",
            "description": f"List of users allowed to perform automated actions on the {ds.name} dataset",
            "logic": "POSITIVE",
            "roles": [{"id": system_global_policy["id"], "required": False}]
        }, "/role"))
        # Create the requester's policy
        user_policy = kc_client.create_policy({
            "name": f"{ds.id} - {ds.name} User {self.requested_by} Policy",
            "description": f"User specific permission to perform actions on the {ds.name} dataset",
            "logic": "POSITIVE",
            "decisionStrategy": "UNANIMOUS",
            "type": "user",
            "users": [self.requested_by]
        }, "/user")
        # Admin permission
        kc_client.create_permission({
            "name": f"{ds.id}-{ds.name} Administation Permission",
            "description": "List of policies that will allow certain users or roles to administrate the dataset",
            "type": "resource",
            "logic": "POSITIVE",
            "decisionStrategy": "AFFIRMATIVE",
            "policies": [pol["id"] for pol in policies],
            "resources": [resource["_id"]],
            "scopes": [scope["id"] for scope in created_scopes]
        })
        # User permission
        kc_client.create_permission({
            "name": f"{ds.id}-{ds.name} User {self.requested_by} Permission",
            "description": "List of policies that will allow certain users or roles to administrate the dataset",
            "type": "resource",
            "logic": "POSITIVE",
            "decisionStrategy": "AFFIRMATIVE",
            "policies": [user_policy["id"]],
            "resources": [resource["_id"]],
            "scopes": [scope["id"] for scope in created_scopes]
        })

        try:
            query = update(Requests).where(Requests.id == self.id).values(status='approved')
            session.execute(query)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise DBError(f"Failed to approve request {self.id}") from exc
