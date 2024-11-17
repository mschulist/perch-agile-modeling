from chirp.projects.hoplite import sqlite_usearch_impl


class SQLiteUsearchDBExt(sqlite_usearch_impl.SQLiteUsearchDB):
    """
    Extension of usearch hoplite db to add additional functionality.
    """

    def remove_label(self, embedding_id: int, label: str):
        """
        Remove the label from the embedding id.
        """
        cursor = self._get_cursor()
        cursor.execute(
            "DELETE FROM hoplite_labels WHERE embedding_id = ? AND label = ?",
            (embedding_id, label),
        )
