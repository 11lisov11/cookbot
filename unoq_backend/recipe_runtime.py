from .models import RecipeRuntimeStatus


class RecipeRuntime:
    def __init__(self):
        self.status = RecipeRuntimeStatus()

    def start(self, recipe_id: str, total_steps: int) -> None:
        self.status = RecipeRuntimeStatus(
            active_recipe_id=recipe_id,
            running=True,
            paused=False,
            aborted=False,
            current_step=0,
            total_steps=total_steps,
            last_message="started",
        )

    def step_started(self, index: int) -> None:
        self.status.current_step = index
        self.status.last_message = f"step_{index}_started"

    def complete(self) -> None:
        self.status.running = False
        self.status.paused = False
        self.status.last_message = "complete"

    def pause(self) -> RecipeRuntimeStatus:
        if self.status.running:
            self.status.paused = True
            self.status.running = False
            self.status.last_message = "paused"
        return self.status

    def resume(self) -> RecipeRuntimeStatus:
        if self.status.active_recipe_id and self.status.paused and not self.status.aborted:
            self.status.running = True
            self.status.paused = False
            self.status.last_message = "resumed"
        return self.status

    def abort(self) -> RecipeRuntimeStatus:
        self.status.running = False
        self.status.paused = False
        self.status.aborted = True
        self.status.last_message = "aborted"
        return self.status

