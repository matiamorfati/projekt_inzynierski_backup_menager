from TaskManager.task_db_manager import TaskDbManager
from TaskManager.task_list import TaskList
from TaskManager.task_app import TaskApp

def main():
    db = TaskDbManager("tasks.db")
    task_list = TaskList(db)
    app = TaskApp(task_list)
    app.run()


if __name__ == "__main__":
    main()
