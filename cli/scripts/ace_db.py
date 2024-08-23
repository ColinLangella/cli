import json
import sqlite3
from typing import Union
import util
import string
import random
from dataclasses import dataclass
from datetime import datetime


"""
Use a dataclass to store the raw and processed inputs from the user
"""


@dataclass
class Task:
    task_id: str = None
    task_type: str = None
    task_status: str = None
    task_context: str = None
    started_at: datetime = None
    finished_at: datetime = None
    time_taken: float = None


@dataclass
class DerivedFields:
    cluster_nodes: list = None
    l_schema: str = None
    l_table: str = None
    key: str = None
    cols: list = None
    conn_params: list = None
    database: str = None
    node_list: list = None
    host_map: dict = None
    table_list: list = None


@dataclass
class TableDiffTask():
    # Unprocessed fields
    _table_name: str  # Required
    _dbname: str
    _nodes: str

    # User-specified, validated fields
    cluster_name: str  # Required
    block_rows: int
    max_cpu_ratio: float
    output: str
    batch_size: int
    quiet_mode: bool

    # For table-diff, the diff_file_path is
    # obtained after the run of table-diff,
    # and is not mandatory
    diff_file_path: str = None

    scheduler: Task = Task()

    # Task specific parameters
    scheduler.task_type = "table-diff"
    scheduler.task_status = "RUNNING"
    scheduler.started_at = datetime.now()

    # Derived fields
    fields: DerivedFields = DerivedFields()


@dataclass
class TableRepairTask():
    # Unprocessed fields
    _table_name: str
    _dbname: str

    # Mandatory fields
    cluster_name: str

    # For table-repair, the diff_file_path is
    # mandatory, as it is used to repair the
    # tables
    diff_file_path: str
    source_of_truth: str

    # Task-specific parameters
    scheduler: Task = Task()
    scheduler.task_type = "table-repair"
    scheduler.task_status = "RUNNING"
    scheduler.started_at = datetime.now()

    # Optional fields
    quiet_mode: bool = False
    dry_run: bool = False
    generate_report: bool = False
    upsert_only: bool = False

    # Derived fields
    fields: DerivedFields = DerivedFields()


@dataclass
class RepsetDiffTask():
    # Unprocessed fields
    _dbname: str
    _nodes: str

    # Mandatory fields
    cluster_name: str
    repset_name: str

    # Optional fields
    # Non-default members since the handler method will fill in the
    # default values
    block_rows: int
    max_cpu_ratio: float
    output: str
    batch_size: int 
    quiet_mode: bool
    nodes: str

    # Task-specific parameters
    scheduler: Task = Task()
    scheduler.task_type = "repset-diff"
    scheduler.task_status = "RUNNING"
    scheduler.started_at = datetime.now()

    # Derived fields
    fields: DerivedFields = DerivedFields()


sqlite_db = util.MY_LITE
local_db_conn = sqlite3.connect(sqlite_db, check_same_thread=False)

ace_tasks_sql = """
CREATE TABLE IF NOT EXISTS ace_tasks (
  task_id           TEXT        PRIMARY KEY,
  task_type         TEXT        NOT NULL,
  cluster_name      TEXT        NOT NULL,
  schema            TEXT        NOT NULL,
  table_name        TEXT        NOT NULL,
  task_status       TEXT        NOT NULL,
  task_context      TEXT,
  diff_file_path    TEXT,
  started_at        TEXT,
  finished_at       TEXT,
  time_taken        DOUBLE
);
"""


def generate_task_id(length=8):
    return "".join(
        random.choice(string.ascii_lowercase + string.digits + string.ascii_uppercase)
        for _ in range(length)
    )


def create_ace_tasks_table():
    try:
        c = local_db_conn.cursor()
        c.execute(ace_tasks_sql)
        local_db_conn.commit()
    except Exception as e:
        util.fatal_sql_error(e, ace_tasks_sql, "create_ace_tasks_table()")


def create_ace_task(task: Union[TableDiffTask, TableRepairTask]):
    try:
        c = local_db_conn.cursor()
        sql = """
                INSERT INTO ace_tasks (task_id, task_type, cluster_name, schema,
                table_name, task_status, task_context, diff_file_path,
                started_at, finished_at, time_taken)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              """
        c.execute(
            sql,
            (
                task.scheduler.task_id,
                task.scheduler.task_type,
                task.cluster_name,
                task.fields.l_schema,
                task.fields.l_table,
                task.scheduler.task_status,
                task.scheduler.task_context,
                task.diff_file_path,
                task.scheduler.started_at,
                task.scheduler.finished_at,
                task.scheduler.time_taken,
            ),
        )
        local_db_conn.commit()
    except Exception as e:
        util.fatal_sql_error(e, sql, "create_ace_task()")


def get_ace_task_by_id(task_id) -> dict:
    c = local_db_conn.cursor()
    sql = "SELECT * FROM ace_tasks WHERE task_id = ?"

    # We are using a paramterised query here, so there's no
    # need to explicitly sanitise the input
    c.execute(sql, (task_id,))
    row = c.fetchone()

    if not row:
        return None

    colnames = [desc[0] for desc in c.description]

    task_details = {}

    for colname, value in zip(colnames, row):
        if colname == "task_context":
            task_details[colname] = json.loads(value)
        else:
            task_details[colname] = value

    return task_details


def update_ace_task(td_task: TableDiffTask):
    try:
        c = local_db_conn.cursor()
        sql = """
                UPDATE ace_tasks SET
                task_status = ?,
                task_context = ?,
                diff_file_path = ?,
                started_at = ?,
                finished_at = ?,
                time_taken = ?
                WHERE task_id = ?
              """
        c.execute(
            sql,
            (
                td_task.scheduler.task_status,
                json.dumps(td_task.scheduler.task_context),
                td_task.diff_file_path,
                td_task.scheduler.started_at.isoformat(timespec="milliseconds"),
                td_task.scheduler.finished_at.isoformat(timespec="milliseconds"),
                td_task.scheduler.time_taken,
                td_task.scheduler.task_id,
            ),
        )
        local_db_conn.commit()
    except Exception as e:
        util.fatal_sql_error(e, sql, "update_ace_task()")


def cleanup_ace_tasks():
    try:
        c = local_db_conn.cursor()
        sql = "DELETE FROM ace_tasks"
        c.execute(sql)
        local_db_conn.commit()
    except Exception as e:
        util.fatal_sql_error(e, sql, "cleanup_ace_tasks()")


def drop_ace_tasks_table():
    try:
        c = local_db_conn.cursor()
        sql = "DROP TABLE IF EXISTS ace_tasks"
        c.execute(sql)
        local_db_conn.commit()
    except Exception as e:
        util.fatal_sql_error(e, sql, "drop_ace_tasks_table()")