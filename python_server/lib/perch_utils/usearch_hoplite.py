import sqlite3
from typing import Any
from chirp.projects.hoplite import sqlite_usearch_impl
from ml_collections import config_dict
import numpy as np
from usearch import index as uindex


class SQLiteUsearchDBExt(sqlite_usearch_impl.SQLiteUsearchDB):
    """
    Extension of usearch hoplite db to add additional functionality.
    """

    def __init__(
        self,
        db_path: str,
        db: sqlite3.Connection,
        ui: uindex.Index,
        _ui_mem: uindex.Index,
        _ui_disk_view: uindex.Index,
        embedding_dim: int,
        embedding_dtype: type[Any] = np.float16,
    ):
        super().__init__(
            db_path, db, ui, _ui_mem, _ui_disk_view, embedding_dim, embedding_dtype
        )

    @classmethod
    def create(
        cls,
        db_path: str,
        usearch_cfg: config_dict.ConfigDict | None = None,
    ) -> "SQLiteUsearchDBExt":
        """
        Create a new SQLiteUsearchDBExt instance.
        """
        sqlite_usearch = super().create(db_path, usearch_cfg)
        return cls(
            db_path=db_path,
            db=sqlite_usearch.db,
            ui=sqlite_usearch.ui,
            _ui_mem=sqlite_usearch._ui_mem,
            _ui_disk_view=sqlite_usearch._ui_disk_view,
            embedding_dim=sqlite_usearch.embedding_dim,
            embedding_dtype=sqlite_usearch.embedding_dtype,
        )

    def remove_label(self, embedding_id: int, label: str):
        """
        Remove the label from the embedding id.
        """
        cursor = self._get_cursor()
        cursor.execute(
            "DELETE FROM hoplite_labels WHERE embedding_id = ? AND label = ?",
            (embedding_id, label),
        )
