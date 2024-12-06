from datetime import timedelta
from typing import Annotated, List, Optional, Tuple
from fastapi import Depends, FastAPI, HTTPException, Response, status, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
import numpy as np
from python_server.lib.all_species_codes import get_all_species_codes
from python_server.lib.perch_utils.annotate import AnnotatePossibleExamples
from python_server.lib.perch_utils.classify import (
    ClassifyFromLabels,
    ExamineClassifications,
    SearchClassifications,
    get_classifier_params_path,
    get_eval_metrics_path,
)
from python_server.lib.perch_utils.explore_annotations import ExploreAnnotations
from python_server.lib.perch_utils.legacy_labels import LegacyLabels
from python_server.lib.perch_utils.search import (
    GatherPossibleExamples,
)
from python_server.lib.perch_utils.summary import get_summary
from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt

from hoplite.agile.classifier import LinearClassifier

from .lib.perch_utils.embeddings import convert_legacy_tfrecords

from .lib.perch_utils.projects import load_hoplite_db, setup_hoplite_db

from .lib.auth import (
    authenticate_user,
    convert_eval_metrics_to_json,
    create_access_token,
    get_current_user,
    get_db,
    hash_password,
)
from .lib.models import (
    AnnotatedRecording,
    ClassifierRunResponse,
    PossibleExampleResponse,
    Project,
    RecordingsSummary,
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
WAREHOUSE_PATH = "data/warehouse"
CLASSIFIER_PARAMS_PATH = "data/classifier_params"
PRECOMPUTE_CLASSIFY_PATH = "data/precompute_classify"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = AccountsDB()
db.create_db_and_tables()
projects = db.get_all_projects()

hoplite_dbs: dict[int, SQLiteUsearchDBExt] = {}

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
    if not (
        filename.startswith(PRECOMPUTE_SEARCH_DIR)
        or filename.startswith(PRECOMPUTE_CLASSIFY_PATH)
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    return FileResponse(filename)


@app.post("/gather_possible_examples")
async def gather_possible_examples(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    species_codes: List[str],
    call_types: List[str],
    num_examples_per_target: int,
    num_targets: int,
    background_tasks: BackgroundTasks,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]  # + [c.id for c in project.contributors]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    def gather_examples():
        hoplite_db = load_hoplite_db(project_id)
        accounts_db = AccountsDB()
        gatherer = GatherPossibleExamples(
            db=accounts_db,
            hoplite_db=hoplite_db,
            precompute_search_dir=PRECOMPUTE_SEARCH_DIR,
            target_path=TARGET_EXAMPLES_DIR,
            project_id=project_id,
        )
        gatherer.get_possible_examples(
            species_codes, call_types, num_examples_per_target, num_targets
        )
        print("Finished gathering examples")

    background_tasks.add_task(gather_examples)
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
        hoplite_db=hoplite_db,
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
        hoplite_db=hoplite_db,
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


@app.get("/recordings_summary", response_model=RecordingsSummary)
async def recordings_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")
    summary = get_summary(project_id, db, get_hoplite_db(project_id))
    print(summary)
    return summary


@app.post("/classify")
async def classify_recordings(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    background_tasks: BackgroundTasks,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    def classify_worker():
        hoplite_db = load_hoplite_db(project_id)
        accounts_db = AccountsDB()
        classifier = ClassifyFromLabels(
            db=accounts_db,
            hoplite_db=hoplite_db,
            project_id=project_id,
            warehouse_path=WAREHOUSE_PATH,
            classifier_params_path=CLASSIFIER_PARAMS_PATH,
        )
        ice_table = classifier.create_iceberg_table()
        classifier.threaded_classify(
            ice_table, batch_size=8192, max_workers=12, table_size=500_000_000
        )
        print("Finished classifying")

    background_tasks.add_task(classify_worker)
    return {"message": "Started to classify recordings", "success": True}


@app.post("/search_classified")
async def search_classified_recordings(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    logit_ranges: Tuple[Tuple[float, float], ...],
    num_per_range: int,
    classified_datetime: str,
    max_logits: bool,
    background_tasks: BackgroundTasks,
    labels: Optional[List[str]] = None,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    # check to make sure that logit_ranges is a list of lists of length 2
    for logit_range in logit_ranges:
        if len(logit_range) != 2:
            raise HTTPException(
                status_code=400,
                detail="Logit ranges must be a list of lists of length 2",
            )

    def search_worker():
        hoplite_db = load_hoplite_db(project_id)
        accounts_db = AccountsDB()
        examine_classified = SearchClassifications(
            db=accounts_db,
            hoplite_db=hoplite_db,
            classify_datetime=classified_datetime,
            project_id=project_id,
            warehouse_path=WAREHOUSE_PATH,
            precompute_classify_path=PRECOMPUTE_CLASSIFY_PATH,
            classifier_params_path=CLASSIFIER_PARAMS_PATH,
        )
        examine_classified.precompute_classify_results(
            logit_ranges=logit_ranges,
            labels=labels,
            num_per_label=num_per_range,
            max_logits=max_logits,
        )
        print("Finished searching")

    background_tasks.add_task(search_worker)
    return {"message": "Started to search classified recordings", "success": True}


@app.get("/get_classifier_runs")
async def get_run_classifiers(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    runs = db.get_classifier_runs(project_id)
    if len(runs) == 0:
        return {"message": "No classifier runs found"}

    runs_response: List[ClassifierRunResponse] = []
    for run in runs:
        if run.id is None:
            raise HTTPException(status_code=400)
        eval_metrics_npz = np.load(
            get_eval_metrics_path(CLASSIFIER_PARAMS_PATH, run.id)
        )
        eval_metrics = convert_eval_metrics_to_json(eval_metrics_npz)
        classes = LinearClassifier.load(
            str(get_classifier_params_path(CLASSIFIER_PARAMS_PATH, run.id))
        ).classes
        runs_response.append(
            ClassifierRunResponse(
                id=run.id,
                datetime=run.datetime,
                project_id=run.project_id,
                eval_metrics=eval_metrics,
                classes=classes,
            )
        )
    return runs_response


@app.get("/get_classifier_results")
async def get_classifier_results(
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: int,
    classifier_run_id: int,
):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    allowed_users = [project.owner_id]
    if current_user.id not in allowed_users:
        raise HTTPException(status_code=403, detail="Forbidden")

    hoplite_db = get_hoplite_db(project_id)

    examine_classify = ExamineClassifications(
        db=db,
        hoplite_db=hoplite_db,
        project_id=project_id,
        precompute_classify_path=PRECOMPUTE_CLASSIFY_PATH,
        classifier_run_id=classifier_run_id,
    )
    return examine_classify.get_classifier_results()
