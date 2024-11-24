from datetime import timedelta
from typing import Annotated, List
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm

from python_server.lib.all_species_codes import get_all_species_codes
from python_server.lib.perch_utils.annotate import AnnotatePossibleExamples
from python_server.lib.perch_utils.explore_annotations import ExploreAnnotations
from python_server.lib.perch_utils.legacy_labels import LegacyLabels
from python_server.lib.perch_utils.search import GatherPossibleExamples

from .lib.perch_utils.embeddings import convert_legacy_tfrecords

from .lib.perch_utils.projects import load_hoplite_db, setup_hoplite_db

from .lib.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    hash_password,
)
from .lib.models import (
    AnnotatedRecording,
    PossibleExampleResponse,
    Project,
    Token,
    User,
    UserResponse,
)
from .lib.db import AccountsDB
import dotenv
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 180

PRECOMPUTE_SEARCH_DIR = "data/precompute_search"
TARGET_EXAMPLES_DIR = "data/target_examples"


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = AccountsDB()

projects = db.get_all_projects()

hoplite_dbs = {}

for project in projects:
    if project.id is None:
        continue
    hoplite_dbs[project.id] = load_hoplite_db(project.id)


def get_hoplite_db(project_id: int):
    if project_id not in hoplite_dbs:
        hoplite_dbs[project_id] = load_hoplite_db(project_id)
    return hoplite_dbs[project_id]


@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(name=current_user.name, email=current_user.email)


@app.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@app.post("/create_project")
async def create_project(
    current_user: Annotated[User, Depends(get_current_user)],
    name: str,
    description: str,
):
    p = Project(name=name, description=description, owner_id=current_user.id)
    project = db.create_project(p)
    return project


@app.post("/add_user")
async def add_user(name: str, email: str, password: str):
    hashed_password = hash_password(password)
    user = User(name=name, email=email, hashed_password=hashed_password)
    db.add_user(user)
    return user


@app.get("/my_projects")
async def my_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AccountsDB, Depends(get_db)],
):
    user = db.session.merge(current_user)
    return user.owned_projects


@app.post("/create_project_db")
async def create_project_db(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    dataset_base_path: str,
    dataset_fileglob: str,
    model_choice: str = "perch_8",
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    success = setup_hoplite_db(
        project_id, dataset_base_path, dataset_fileglob, model_choice
    )

    if not success:
        raise HTTPException(status_code=400, detail="DB already exists")
    return {"success": success}


@app.post("/create_project_db_legacy")
async def create_project_db_legacy(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    embeddings_path: str,
    db_type: str,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        success = convert_legacy_tfrecords(project_id, embeddings_path, db_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=400, detail="DB already exists")
    return {"success": success}


@app.post("/get_next_possible_example", response_model=PossibleExampleResponse | dict)
async def get_next_possible_example(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
):
    """
    Given a user and project (that they are a part of), get the next possible example to annotate.

    We will return the {audio, image, possible_label, score, filename, timestamp_s} of the next possible example.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # TODO: fix the allowed users
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)
    annotate = AnnotatePossibleExamples(
        db=db,
        hoplite_db=hoplite_db,
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
        project_id=project_id,
    )
    possible_example_response = annotate.get_next_possible_example_with_data()
    if not possible_example_response:
        return {"message": "No more possible examples"}
    return possible_example_response


@app.get("/get_file")
async def get_file(filename: str):
    # TODO: Check if the file is in the precompute search dir
    # for security reasons
    return FileResponse(filename)


@app.post("/gather_possible_examples")
async def gather_possible_examples(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    species_codes: List[str],
    call_types: List[str],
    num_examples_per_target: int,
    num_targets: int,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # TODO: fix the allowed users
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)
    gatherer = GatherPossibleExamples(
        db=db,
        hoplite_db=hoplite_db,
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
        target_path=TARGET_EXAMPLES_DIR,
        project_id=project_id,
    )
    gatherer.get_possible_examples(
        species_codes, call_types, num_examples_per_target, num_targets
    )
    return {"message": "Started to gather target recordings", "success": True}


@app.post("/annotate_example")
async def annotate_example(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    embedding_id: int,
    labels: List[str],
):
    """
    Given a user and project (that they are a part of), annotate an example with the given labels.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)

    annotate = AnnotatePossibleExamples(
        db=db,
        hoplite_db=hoplite_db,
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
        project_id=project_id,
    )
    annotate.annotate_possible_example_by_embedding_id(
        embedding_id, labels, current_user.name
    )
    return {"message": "Annotated example", "success": True}


@app.get("/get_label_summary")
async def get_label_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)

    explore = ExploreAnnotations(
        db=db,
        hoplite_db=hoplite_db,  # type: ignore
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
        project_id=project_id,
        provenance=current_user.name,
    )
    label_summary = explore.get_annotations_summary()
    return label_summary


@app.get("/get_annotations_by_label", response_model=List[AnnotatedRecording])
async def get_annotations_by_label(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    label: str,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)

    explore = ExploreAnnotations(
        db=db,
        hoplite_db=hoplite_db,  # type: ignore
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
        project_id=project_id,
        provenance=current_user.name,
    )
    annotations = explore.get_annotations_by_label(label)
    return annotations


@app.post("/relabel_example")
async def relabel_example(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    embedding_id: int,
    labels: List[str],
):
    """
    Given a user and project (that they are a part of), relabel an example with the given labels.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)

    explore = ExploreAnnotations(
        db=db,
        hoplite_db=hoplite_db,  # type: ignore
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
        project_id=project_id,
        provenance=current_user.name,
    )

    explore.change_annotation(embedding_id, labels)
    return {"message": "Relabeled example", "success": True}


@app.post("/add_legacy_labels")
async def add_legacy_labels(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    label_dir: str,
):
    """
    Given a user and project (that they are a part of), add legacy labels to the project.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)

    legacy_labels = LegacyLabels(
        db=db,
        hoplite_db=hoplite_db,
        label_dir=label_dir,
        project_id=project_id,
        annotator=current_user.name,
        precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
    )
    legacy_labels.add_labels_to_new_db()


@app.get("/all_species_codes")
async def all_species_codes():
    codes = get_all_species_codes()
    return {"species_codes": codes}


@app.get("/old_target_codes")
async def old_target_codes(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")
    

    return {
        "old_target_codes": ["ALDERFLYCATCHER", "AMERICANROBIN", "AMERICANWOODCOCK"]
    }
