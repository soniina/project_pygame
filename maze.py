import csv
import os
from collections import deque
from math import ceil
import pygame as pg
import pygame_gui as pg_gui

fps = 15
game_score = 0
ENEMY_EVENT_TYPE = pg.USEREVENT + 1  # событие для врага
pg.time.set_timer(ENEMY_EVENT_TYPE, 0)

SOUND_EVENT_TYPE = pg.USEREVENT + 2  # событие для звукового эффекта при выигрыше/проигрыше
pg.time.set_timer(SOUND_EVENT_TYPE, 10)

# выбор уровня
print('\n' 
      'На выбор даётся 4 уровня (1, 2, 3, 4): чем больше номер уровня, тем он сложнее.\n'
      'Введите номер нужного вам уровня:')
level = input()
levels = {'1': {'width': 41, 'height': 31, 'hero_pos': (21, 0), 'chest_pos': (2, 28), 'enemy_pos': (1, 26),
                'scores_x': 850},
          '2': {'width': 41, 'height': 31, 'hero_pos': (17, 0), 'chest_pos': (38, 24), 'enemy_pos': (39, 26),
                'scores_x': 850},
          '3': {'width': 35, 'height': 23, 'hero_pos': (29, 0), 'chest_pos': (4, 20), 'enemy_pos': (2, 21),
                'scores_x': 750},
          '4': {'width': 31, 'height': 31, 'hero_pos': (0, 1), 'chest_pos': (28, 28), 'enemy_pos': (24, 29),
                'scores_x': 750}
          }
level_data = levels[level]


# класс лабиринта
class Maze:

    # его константы, переменные
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.coins_cells = []
        self.maze_board = []  # список-карта лабиринта
        with open(f"maze_{level}.txt") as maze_file:
            for line in maze_file:
                self.line = []
                for n in line.strip():
                    self.line.append(n)
                self.maze_board.append(self.line)
        self.graph = {}

        self.left = 5
        self.top = 5
        self.cell_size = 20

        self.wall_cell_im = pg.image.load("wall_cell.png").convert_alpha()
        self.wall_cell = pg.transform.scale(self.wall_cell_im, (20, 20))
        self.wall_cell.set_colorkey(self.wall_cell.get_at((0, 0)))

        self.grass_cell_im = pg.image.load("grass_cell.png").convert_alpha()
        self.grass_cell = pg.transform.scale(self.grass_cell_im, (20, 20))

        self.cell_image = {'1': self.wall_cell, '0': self.grass_cell, 'x': self.grass_cell}
        self.cell_colors = {'1': (0, 0, 0), '0': (0, 255, 0), 'x': (0, 255, 0)}

    # отрисовка: 0 из списка означает свободную клетку с травой (self.grass_cell), 1 - клетку со стеной (self.wall_cell)
    def render(self):
        for y in range(self.height):
            for x in range(self.width):
                cell = pg.Rect(x * self.cell_size + self.left, y * self.cell_size + self.top,  # заливка цветом
                               self.cell_size, self.cell_size)
                screen.fill(self.cell_colors[self.maze_board[y][x]], cell)
                screen.blit(self.cell_image[self.maze_board[y][x]], (x * self.cell_size + self.left,
                                                                     y * self.cell_size + self.top))

    # получения списка с координатами монет на поле
    def get_coins_cells(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.maze_board[y][x] == 'x':
                    self.coins_cells.append((x, y))
        return self.coins_cells

    # получение из данных координат на экране координаты клетки поля
    def get_cell(self, mouse_pos, direction):
        if direction == "down" and (mouse_pos[0] - 5) % 20 == 0:
            x = ceil((mouse_pos[0] - self.left - 5) / self.cell_size)
            y = ceil((mouse_pos[1] - self.top) / self.cell_size)
            return x, y
        if direction == "right" and (mouse_pos[1] - 5) % 20 == 0:
            x = ceil((mouse_pos[0] - self.left) / self.cell_size)
            y = ceil((mouse_pos[1] - self.top - 5) / self.cell_size)
            return x, y
        if direction == "left" and (mouse_pos[1] - 5) % 20 == 0:
            x = ceil((mouse_pos[0] - self.left - 15) / self.cell_size)
            y = ceil((mouse_pos[1] - self.top - 5) / self.cell_size)
            return x, y
        if direction == "up" and (mouse_pos[0] - 5) % 20 == 0:
            x = ceil((mouse_pos[0] - self.left - 5) / self.cell_size)
            y = ceil((mouse_pos[1] - self.top - 15) / self.cell_size)
            return x, y
        else:
            return 0, 0

    # проверка не является ли клетка с данными координатами на экране стеной
    def cell_is_free(self, pos, direction):
        if self.maze_board[self.get_cell(pos, direction)[1]][self.get_cell(pos, direction)[0]] in ['0', 'x']:
            return True
        else:
            return False

    # проверка не является ли данная клетка с данными координатами на поле стеной
    def cell_is_free_2(self, x, y):
        if self.maze_board[y][x] == '0':
            return True
        else:
            return False

    # получение всех возможных координат для следующего шага врага
    def get_next_cells(self, x, y):
        check_next_cell = lambda x, y: True if 0 <= x < self.width and 0 <= y < self.height and \
                                               self.cell_is_free_2(x, y) else False
        ways = [-1, 0], [0, -1], [1, 0], [0, 1]
        return [(x + dx, y + dy) for dx, dy in ways if check_next_cell(x + dx, y + dy)]

    # получение следующих координат пути для движения врага
    def find_next_step(self, start, target):
        queue = deque([target])
        visited = {target: None}
        for y, row in enumerate(self.maze_board):
            for x, col in enumerate(row):
                self.graph[(x, y)] = self.graph.get((x, y), []) + self.get_next_cells(x, y)
        while queue:
            cur_cell = queue.pop()
            if cur_cell == start:
                break
            next_cells = self.graph[cur_cell]
            for next_cell in next_cells:
                if next_cell not in visited:
                    queue.append(next_cell)
                    visited[next_cell] = cur_cell
        path_segment = visited[start]
        return path_segment


# класс главного героя
class Hero:

    # его константы. переменные
    def __init__(self, maze):
        self.maze = maze
        self.x = level_data['hero_pos'][0] * 20 + 5
        self.y = level_data['hero_pos'][1] * 20 + 5
        self.hero_down = pg.image.load("hero_down.png").convert_alpha()
        self.hero_up = pg.image.load("hero_up.png").convert_alpha()
        self.hero_left = pg.image.load("hero_left_right.png").convert_alpha()
        self.hero_right = pg.transform.flip(self.hero_left, True, False)
        self.hero = pg.transform.scale(self.hero_down, (20, 20))

    # отрисовка
    def render(self):
        self.hero_rect = self.hero.get_rect(topleft=(self.x, self.y))
        screen.blit(self.hero, self.hero_rect)

    # изменение координат на данные
    def set_position(self, position):
        self.x, self.y = position[0], position[1]

    # изменение изображения героя (поворот влево, вправо, вперед или назад)
    def set_images(self, image):
        self.hero = pg.transform.scale(image, (20, 20))

    # получение координат героя в данный момент
    def get_position(self):
        return self.x, self.y

    # получение положения и размера изображения героя
    def get_hero_rect(self):
        return self.hero_rect


# класс врага
class Enemy(pg.sprite.Sprite):

    # его константы, переменные
    def __init__(self, maze, hero):
        pg.sprite.Sprite.__init__(self)
        self.x = level_data['enemy_pos'][0] * 20 + 5
        self.y = level_data['enemy_pos'][1] * 20 + 5
        self.collide = False
        self.maze = maze
        self.hero = hero
        self.enemy = pg.image.load("enemy.png").convert_alpha()
        self.image = pg.transform.scale(self.enemy, (20, 17))
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

    # отрисовка
    def render(self):
        screen.blit(self.image, self.rect)

    # изменение положения, т.е. движение за героем
    def update(self):
        target = ((self.hero.get_position()[0] - 5) // 20, (self.hero.get_position()[1] - 5) // 20)
        start = ((self.x - 5) // 20, (self.y - 5) // 20)
        if start != target:
            next_x, next_y = self.maze.find_next_step(start, target)
            self.rect.x = next_x * 20 + 5
            self.rect.y = next_y * 20 + 5
            self.x, self.y = self.rect.x, self.rect.y

    # проверка столкновения героя и врага
    def check_collide(self):
        hero_rect = self.hero.get_hero_rect()
        if pg.Rect.colliderect(hero_rect, self.rect):
            self.collide = True
        return self.collide


# класс монеты
class Coin(pg.sprite.Sprite):

    # её константы, переменные
    def __init__(self, x, y, hero):
        super().__init__()
        self.hero = hero
        self.image = pg.transform.scale(pg.image.load("coin.png").convert_alpha(), (15, 15))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.coin_exists = True

    # проверка столкновения героя с монетой
    def check_collide(self, sound):
        global game_score
        hero_rect = self.hero.get_hero_rect()
        if self.coin_exists is True:
            if pg.Rect.colliderect(hero_rect, self.rect):
                self.coin_exists = False
                game_score += 1
                sound.play()
                self.kill()


# класс сундука
class Chest(pg.sprite.Sprite):

    # его константы, переменные
    def __init__(self, hero):
        super().__init__()
        self.hero = hero
        self.image = pg.transform.scale(pg.image.load("chest_full.png").convert_alpha(), (40, 35))
        self.rect = self.image.get_rect()
        self.rect.x = level_data['chest_pos'][0] * 20 - 5
        self.rect.y = level_data['chest_pos'][1] * 20 - 5
        self.chest_open = False

    # отрисовка
    def render(self):
        screen.blit(self.image, self.rect)

    # проверка столкновения героя с сундуком
    def check_collide(self, sound, game_over):
        global game_score
        hero_rect = self.hero.get_hero_rect()
        if self.chest_open is False:
            if pg.Rect.colliderect(hero_rect, self.rect):
                self.chest_open = True
                game_score += 15
                if game_over is False:
                    sound.play()
                self.image = pg.transform.scale(pg.image.load("chest_empty.png").convert_alpha(), (40, 35))


# класс игры (некоторые её функции)
class Game:

    # её константы, переменные
    def __init__(self, maze, hero, speed):
        self.maze = maze
        self.hero = hero
        self.speed = speed
        self.hero_image = None
        self.background_image = pg.image.load("background.jpg").convert()
        self.background = pg.transform.scale(self.background_image, (width, height))
        self.background_rect = self.background.get_rect(topleft=(0, 0))

    # отрисовка заднего фона
    def render_background(self):
        screen.blit(self.background, self.background_rect)

    # реализация движения главного героя с помощью стрелок на клавиатуре
    def move_hero(self):
        self.hero_image = self.hero.hero_down
        x, y = self.hero.get_position()
        bt = pg.key.get_pressed()
        direction = None
        if bt[pg.K_LEFT]:
            self.hero_image = self.hero.hero_left
            x -= self.speed
            direction = 'left'
        if bt[pg.K_RIGHT]:
            self.hero_image = self.hero.hero_right
            x += self.speed
            direction = 'right'
        if bt[pg.K_UP]:
            self.hero_image = self.hero.hero_up
            y -= self.speed
            direction = 'up'
        if bt[pg.K_DOWN]:
            self.hero_image = self.hero.hero_down
            y += self.speed
            direction = 'down'

        if self.maze.cell_is_free((x, y), direction):
            self.hero.set_position((x, y))
            self.hero.set_images(self.hero_image)


# класс кнопки для вкл/выкл звука
class Button_Sound:

    # её переменные
    def __init__(self):
        self.color = (76, 80, 82)
        self.file = "sound_on.png"

    # изменение переменных
    def change(self, color, file):
        self.color = color
        self.file = file

    # отрисовка кнопки
    def render(self):
        pg.draw.rect(screen, self.color, (1125, 555, 60, 60))
        sound_image = pg.image.load(self.file).convert_alpha()
        sound = pg.transform.scale(sound_image, (40, 40))
        screen.blit(sound, (1135, 565))


# функция для вывода текста на начальном меню
def start_screen():

    font = pg.font.Font('20008.ttf', 30)
    text_input_name = font.render("Введите ваше имя:", True, (71, 80, 82))
    screen.blit(text_input_name, (433, 200))

    font_message = pg.font.Font('20008.ttf', 12)
    message_1 = font_message.render("Нажмите ENTER после ввода имени,", True, (71, 80, 82))
    message_2 = font_message.render("а затем НАЧАТЬ ИГРУ", True, (71, 80, 82))
    screen.blit(message_1, (470, 280))
    screen.blit(message_2, (525, 295))


# функция для вывода текста с кол-вом монет во время игры
def scores():

    font = pg.font.Font('20008.ttf', 50)
    text_coins = font.render(f"Coins: {game_score}", True, (71, 80, 82))
    text_x_coins, text_y_coins = level_data['scores_x'], 100
    screen.blit(text_coins, (text_x_coins, text_y_coins))


# функция для вывода результата игры
def game_result(win, result):

    pg.draw.rect(screen, (78, 86, 125), (370, 75, 460, 210), 0)
    pg.draw.rect(screen, (180, 156, 109), (375, 80, 450, 200), 0)
    if win:
        font = pg.font.Font('20008.ttf', 80)
        text_y = 130
        text = font.render("Победа!", True, (110, 111, 132))
    else:
        font = pg.font.Font('20008.ttf', 65)
        text_y = 135
        text = font.render("Поражение", True, (110, 111, 132))
    text_x = width // 2 - text.get_width() // 2
    screen.blit(text, (text_x, text_y))

    font_result = pg.font.Font('20008.ttf', 30)
    text_result = font_result.render(f"Результат: {result}", True, (71, 80, 82))
    text_result_x = width // 2 - text_result.get_width() // 2
    screen.blit(text_result, (text_result_x, 300))


if __name__ == '__main__':
    pg.init()
    pg.display.set_caption('Maze')
    size = width, height = 1200, 630
    screen = pg.display.set_mode(size)

    clock = pg.time.Clock()
    manager = pg_gui.UIManager(size)

    # фоновая музыка для игры
    pg.mixer.music.load("background_music.mp3")
    pg.mixer.music.play(-1)
    pg.mixer.music.set_volume(0.9)

    # звуковые эффекты
    coin_sound = pg.mixer.Sound("coin.mp3")  # при сборе монет
    chest_open = pg.mixer.Sound("chest_open.mp3")  # при открытии сундука
    lose = pg.mixer.Sound("game_lose.mp3")  # при поражении
    win = pg.mixer.Sound("game_win.mp3")  # при победе
    pause = pg.mixer.Sound("pause.mp3")  # при включении паузы, т.е. при открытии меню
    unpause = pg.mixer.Sound("unpause.mp3")  # при выключении паузы, т.е. при закрытии меню
    [sound.set_volume(1.0) for sound in [coin_sound, chest_open, lose, win, pause, unpause]]

    # все кнопки и строка для ввода текста:
    start = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 80), (300, 100)),
        text='Начать игру', manager=manager, visible=False
    )
    input_name = pg_gui.elements.UITextEntryLine(
        relative_rect=pg.Rect((450, 240), (300, 100)),
        manager=manager, visible=False
    )
    name = None  # имя, введённое пользователем
    continue_unfinished_game = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 333), (300, 100)),
        text='Продолжить незавершенную игру', manager=manager, visible=False
    )
    results_table = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 453), (300, 100)),
        text='Таблица результатов', manager=manager,
        visible=False
    )
    continue_game = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 140), (300, 100)),
        text='Продолжить', manager=manager, visible=False
    )
    return_to_start = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 260), (300, 100)),
        text='Вернуться в начальное меню', manager=manager, visible=False
    )
    exit_game = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 380), (300, 100)),
        text='Выйти', manager=manager, visible=False
    )
    results_table_2 = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 355), (300, 100)),
        text='Таблица результатов', manager=manager,
        visible=False
    )
    exit_game_2 = pg_gui.elements.UIButton(
        relative_rect=pg.Rect((450, 473), (300, 100)),
        text='Выйти', manager=manager, visible=False
    )

    running = True
    start_screen_render = True  # показ начального меню
    menu_render = False  # показ меню при паузе
    game_result_render = False  # показ результата

    game_lose = False
    game_win = False
    game_over = False

    continue_unfinished = False  # проверка наличия незаконченной игры, которую можно продолжить
    # незаконченной игрой называется игра, прерванная нажатием кнопки 'Вернуться в начальное меню' во время паузы

    pause_time = 0  # время, проведённое в начальном меню
    start_time = 0  # время, проведённое в меню во время паузы
    start_time_list = [0]  # список, включающий в себя каждую секунду проведенную в начальном меню
    pause_time_list = []  # список, включающий в себя каждую секунду проведенную в меню во время паузы
    prev_pause_time = []  # список количеств секунд проведённых в меню во время паузы за все разы
    prev_start_time = []  # список количеств секунд проведённых в начальном меню за все разы
    game_time_list = []  # список, включающий в себя каждую секунду после победы или проигрыша
    game_time = None  # всё время игры

    clicks_on_sound = 1  # кол-во нажатий на кнопку для вкл/выкл звука

    maze = Maze(level_data['width'], level_data['height'])
    hero = Hero(maze)
    enemy = Enemy(maze, hero)

    coins = pg.sprite.Group()
    coins_cells = maze.get_coins_cells()  # список с координатами монет на поле
    for i in range(15):
        coin = Coin(coins_cells[i][0] * 20 + 7, coins_cells[i][1] * 20 + 7, hero)
        coins.add(coin)

    chest = Chest(hero)
    game = Game(maze, hero, 20)
    button_sound = Button_Sound()

    while running:
        for event in pg.event.get():

            if event.type == pg.QUIT:
                running = False

            if event.type == SOUND_EVENT_TYPE:
                if game_win:
                    win.play()
                    game_over = True
                elif game_lose:
                    lose.play()
                    game_over = True
                if game_over:
                    pg.time.set_timer(SOUND_EVENT_TYPE, 0)  # чтобы мелодия прозвучала только один раз

            if event.type == ENEMY_EVENT_TYPE:
                enemy.update()

            if event.type == pg.MOUSEMOTION:
                if 1125 <= event.pos[0] <= 1185 and 555 <= event.pos[1] <= 615:  # при наведение на кнопку вкл/выкл звук
                    if clicks_on_sound % 2 == 0:  # т.е. если звук выключен
                        button_sound.change((99, 104, 107), "sound_on.png")
                    else:
                        button_sound.change((99, 104, 107), "sound_off.png")
                elif clicks_on_sound % 2 == 0:  # т.е. если звук выключен и нет наведения на кнопку
                    button_sound.change((76, 80, 82), "sound_off.png")
                else:  # т.е. если звук включен и нет наведения на кнопку
                    button_sound.change((76, 80, 82), "sound_on.png")

            if event.type == pg.MOUSEBUTTONDOWN:
                if 1125 <= event.pos[0] <= 1185 and 555 <= event.pos[1] <= 615:  # при нажатии на кнопку вкл/выкл звука
                    if clicks_on_sound % 2 == 0:  # т.е. если звук включен
                        button_sound.change((76, 80, 82), "sound_off.png")
                        pg.mixer.music.set_volume(0.9)
                        [sound.set_volume(1.0) for sound in [coin_sound, chest_open, lose, win, pause, unpause]]
                    else:  # т.е. если звук выключен
                        button_sound.change((76, 80, 82), "sound_on.png")
                        pg.mixer.music.set_volume(0.0)
                        [sound.set_volume(0.0) for sound in [coin_sound, chest_open, lose, win, pause, unpause]]
                    clicks_on_sound += 1

            if event.type == pg.USEREVENT:
                if event.user_type == pg_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == start and name is not None and continue_unfinished is False:  # нажатие на кнопку 'Начать игру'  
                        # перед этим нужно обязательно ввести имя
                        start_screen_render = False
                        pg.time.set_timer(ENEMY_EVENT_TYPE, 300)  # разрешение врагу двигаться
                    # нажатие на кнопку 'Продолжить незаконченную игру' и проверка наличия такой игры
                    if event.ui_element == continue_unfinished_game and continue_unfinished is True:
                        start_screen_render = False
                        pg.time.set_timer(ENEMY_EVENT_TYPE, 300)
                    # нажатие на кнопку 'Таблица результатов'; она есть для каждого уровня
                    if event.ui_element == results_table or event.ui_element == results_table_2:
                        os.startfile(f"results_table_{level}.csv")
                    # нажатие на кнопку 'Таблица результатов' после получения результата
                    if event.ui_element == results_table_2:
                        running = False
                    if event.ui_element == continue_game:  # нажатие на кнопку 'Продолжить'
                        menu_render = False
                        unpause.play()
                        pg.time.set_timer(ENEMY_EVENT_TYPE, 300)
                    if event.ui_element == return_to_start:  # нажатие на кнопку 'Вернуться в начальное меню'
                        menu_render = False
                        start_screen_render = True
                        continue_unfinished = True
                        pg.mixer.music.rewind()  # включение фоновой музыки заново
                        pg.time.set_timer(ENEMY_EVENT_TYPE, 0)  # остановка движений врага
                    if event.ui_element == exit_game or event.ui_element == exit_game_2:  # нажатие на кнопку 'Выйти'
                        running = False

            if event.type == pg.KEYDOWN:
                # нажатие на кнопку 'Pause' на клавиатуре и проверка открытия лишь самой игры
                if event.key == pg.K_PAUSE and start_screen_render is False and game_result_render is False:
                    menu_render = True
                    pause.play()
                    pg.time.set_timer(ENEMY_EVENT_TYPE, 0)
                # нажатие на кнопку 'Enter' на клавиатуре, 'отправка' имени, очищение строки для ввода
                if event.key == pg.K_RETURN:
                    name = input_name.get_text()
                    input_name.set_text('')

            manager.process_events(event)

        # отрисовка начального меню
        if start_screen_render is True:
            game.render_background()
            start_screen()
            pg.mixer.music.unpause()

            # скрытие или показ нужных кнопок
            start.show()
            input_name.show()
            continue_unfinished_game.show()
            results_table.show()
            continue_game.hide()
            return_to_start.hide()
            exit_game.hide()
            button_sound.render()

            start_time_list.append(pg.time.get_ticks())  # добавление каждой секунды в список

        # отрисовка меню при паузе
        elif menu_render:
            game.render_background()
            pg.mixer.music.pause()

            # скрытие или показ нужных кнопок
            continue_game.show()
            return_to_start.show()
            exit_game.show()
            button_sound.render()

            pause_time_list.append(pg.time.get_ticks())  # добавление каждой секунды в список

        # отрисовка самой игры
        else:
            game.render_background()
            pg.mixer.music.unpause()

            # скрытие или показ нужных кнопок
            start.hide()
            input_name.hide()
            continue_unfinished_game.hide()
            results_table.hide()
            continue_game.hide()
            return_to_start.hide()
            exit_game.hide()
            button_sound.render()

            if start_time_list:
                start_time = start_time_list[-1] - start_time_list[0]
            if pause_time_list:
                pause_time = pause_time_list[-1] - pause_time_list[0] + 175
            pause_time_list, start_time_list = [], []

            if pause_time not in prev_pause_time:
                prev_pause_time.append(pause_time)
            if start_time not in prev_start_time:
                prev_start_time.append(start_time)
            time = float(pg.time.get_ticks() - sum(prev_start_time) - sum(prev_pause_time)) // 100 / 10

            scores()  # вывод текста с кол-вом набранных монет
            font = pg.font.Font('20008.ttf', 50)
            text_time = font.render(f"Time: {time}", True, (71, 80, 82))
            text_x_time, text_y_time = level_data['scores_x'], 220
            screen.blit(text_time, (text_x_time, text_y_time))
            text_sec = font.render(f"с", True, (71, 80, 82))
            screen.blit(text_sec, (text_x_time + 320, text_y_time))

            maze.render()
            chest.render()
            coins.draw(screen)
            game.move_hero()
            hero.render()

            for coin in coins:
                coin.check_collide(coin_sound)
            chest.check_collide(chest_open, game_score == 15)

            enemy.render()

            if game_score == 30:
                game_win = True
            if enemy.check_collide() is True:  # проверка столкновения героя и врага
                game_lose = True
            if game_win or game_lose:
                game_result_render = True
                game.render_background()
                pg.mixer.music.stop()

                # показ нужных кнопок
                exit_game_2.show()
                results_table_2.show()
                button_sound.render()

                if not game_time_list:
                    game_time_list.append(time)
                result = f"Coins = {game_score}, Time = {game_time_list[0]} c  ({name})"
                game_result(game_win, result)
                game_time = str(game_time_list[0])
                game_time = game_time.replace('.', ',')
                row = [name, str(game_score), game_time]
                file = open(f"results_table_{level}.csv").read()
                try:  # запись результата в файл
                    with open(f"results_table_{level}.csv", 'a', newline='\n') as csvfile:
                        writer = csv.writer(csvfile, delimiter=';')
                        row_str = ';'.join(row)
                        if row_str not in file:
                            writer.writerow(row)
                except PermissionError:
                    pass
        time_delta = clock.tick(60) / 1000.0
        manager.update(time_delta)
        manager.draw_ui(screen)

        clock.tick(fps)
        pg.display.flip()

    pg.quit()
