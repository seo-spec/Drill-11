from pico2d import load_image, get_canvas_width
from time import perf_counter
from transitions import Machine
from sdl2 import (SDL_GetKeyboardState, SDL_NUM_SCANCODES, SDL_SCANCODE_SPACE,
                  SDL_SCANCODE_LEFT, SDL_SCANCODE_RIGHT)

class autoRun:
    """Automatic running state; Boy's machine delegates its callbacks here."""

    def __init__(self, boy):
        self.boy = boy
        self.started_at = None

    def enter(self):
        boy = self.boy
        boy.reset_idle_timer()
        self.started_at = boy.last_update
        boy.move_dir = boy.face_dir
        self.keep_in_bounds()

    def keep_in_bounds(self):
        boy = self.boy
        half_width = boy.HALF_WIDTH * boy.AUTO_RUN_SCALE
        left, right = half_width, get_canvas_width() - half_width
        if right <= left:
            boy.x = get_canvas_width() / 2
        elif boy.x <= left:
            boy.x, boy.move_dir = left, 1
        elif boy.x >= right:
            boy.x, boy.move_dir = right, -1
        boy.face_dir = boy.move_dir


    def update(self):
        boy = self.boy
        elapsed = perf_counter() - boy.last_update
        boy.x += boy.move_dir * boy.AUTO_RUN_SPEED * elapsed
        self.keep_in_bounds()
        boy.animate_idle()


class Boy:
    FRAMES_PER_SECOND = 10
    FRAME_COUNT = 8
    SLEEP_DELAY = 5.0
    RUN_SPEED = 200.0  # Pixels per second.
    HALF_WIDTH = 50
    AUTO_RUN_SPEED = RUN_SPEED * 2
    AUTO_RUN_SCALE = 1.5
    AUTO_RUN_DURATION = 5.0

    def __init__(self):
        self.x, self.y = 400, 90
        self.frame = 0
        self.face_dir = 1
        self.move_dir = 0
        self.image = load_image('animation_sheet.png')
        self.machine = Machine(
            model=self,
            states=['IDLE', 'RUN', 'SLEEP'],
            initial='IDLE',
            auto_transitions=False,
        )
        # Internal transition updates the animation while remaining in IDLE.
        self.machine.add_transition('tick', 'IDLE', None, after='animate_idle')
        self.machine.add_transition('tick', 'RUN', None, after='run')
        self.machine.add_transition('tick', 'SLEEP', None)
        self.machine.add_transition('start_running', ['IDLE', 'SLEEP'], 'RUN',
                                    after='reset_idle_timer')
        self.machine.add_transition('stop_running', 'RUN', 'IDLE',
                                    after='reset_idle_timer')
        self.machine.add_transition('fall_asleep', 'IDLE', 'SLEEP',
                                    after='enter_sleep')
        self.machine.add_transition('wake_up', 'SLEEP', 'IDLE',
                                    after='reset_idle_timer')
        self.last_update = perf_counter()
        self.animation_time = 0.0
        self.idle_since = self.last_update
        self.space_was_down = False

    def update(self):
        # main.py already pumps SDL events; inspect keys without consuming them.
        keys = SDL_GetKeyboardState(None)
        space_down = bool(keys[SDL_SCANCODE_SPACE])
        self.move_dir = int(bool(keys[SDL_SCANCODE_RIGHT])) - int(bool(keys[SDL_SCANCODE_LEFT]))
        if self.state == 'SLEEP':
            if self.move_dir:
                self.face_dir = self.move_dir
                self.start_running()
            elif space_down and not self.space_was_down:
                self.wake_up()
        else:
            if self.move_dir:
                self.face_dir = self.move_dir
                if self.state == 'IDLE':
                    self.start_running()
            elif self.state == 'RUN':
                self.stop_running()

            if any(keys[i] for i in range(SDL_NUM_SCANCODES)):
                self.idle_since = perf_counter()
            elif self.state == 'IDLE' and perf_counter() - self.idle_since >= self.SLEEP_DELAY:
                self.fall_asleep()
        self.space_was_down = space_down
        self.tick()

    def enter_sleep(self):
        self.frame = 0

    def reset_idle_timer(self):
        self.idle_since = perf_counter()
        self.last_update = self.idle_since
        self.animation_time = 0.0
        self.frame = 0

    def animate_idle(self):
        now = perf_counter()
        self.animation_time += now - self.last_update
        self.last_update = now
        self.frame = int(self.animation_time * self.FRAMES_PER_SECOND) % self.FRAME_COUNT

    def run(self):
        elapsed = perf_counter() - self.last_update
        self.x += self.move_dir * self.RUN_SPEED * elapsed
        self.x = max(self.HALF_WIDTH,
                     min(get_canvas_width() - self.HALF_WIDTH, self.x))
        self.animate_idle()

    def draw(self):
        if self.state == 'SLEEP':
            # Rotate toward the back so the face points up in either direction.
            sleep_angle = self.face_dir * 3.141592653589793 / 2
            self.image.clip_composite_draw(
                0, 300 if self.face_dir == 1 else 200, 100, 100,
                sleep_angle, '', self.x, self.y - 25, 100, 100)
        elif self.state == 'RUN':
            self.image.clip_draw(self.frame * 100,
                                 100 if self.face_dir == 1 else 0,
                                 100, 100, self.x, self.y)
        elif self.face_dir == 1:
            self.image.clip_draw(self.frame * 100, 300, 100, 100, self.x, self.y)
        else:
            self.image.clip_draw(self.frame * 100, 200, 100, 100, self.x, self.y)
