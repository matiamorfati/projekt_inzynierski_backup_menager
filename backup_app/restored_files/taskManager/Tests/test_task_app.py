#komenda do uruchomienia testu: python -m unittest discover -s Tests
#komenda na konretny test: python -m unittest Tests.test_task_app 

import unittest
from TaskManager.task_app import TaskApp

#Atrapa tasklist sprawdazmy tylko czy taskapp przechowuje referencje do niej
class FakeTaskList:
    pass


class TestTaskApp(unittest.TestCase):

    def test_init_stores_task_list(self):
        #Tworzymy atrape listy zadan
        fake_list = FakeTaskList()

        #przekazujemy j do taskapp
        app = TaskApp(fake_list)

        #sprawdzamy czy taskapp zapamietal przekazana liste zadn
        self.assertIs(app.task_list, fake_list)


if __name__ == "__main__":
    unittest.main()
