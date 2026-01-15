
class Task:
    def __init__(self, title, description, priority, status="todo"):
        self.id = None
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status

    #oznacza zadanie jako ukończone
    def mark_done(self):
        self.status = "done"

    #zwraca słownik reprezentujący zadanie
    def as_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
        }
    
    #formatuje zadanie do wyświetlenia w konsoli
    def format_for_console(self):
        if self.id is not None:
            prefix = f"[{self.id}] "
        else:
            prefix = ""
        return f"{prefix}{self.title} | {self.description} | priorytet: {self.priority} | status: {self.status}"
