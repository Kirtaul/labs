import sys
import pygame as pg
import pickle
import os
import time
import pyautogui
from constants import *
from board import Board
from ui import *
from utils import load_users, save_users
from dqn_agent import DQNAgent


class Game:
    def __init__(self):
        self.screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pg.display.set_caption("Доджем")
        init_images()
        try:
            icon = pg.image.load(ICON_IMG)
            pg.display.set_icon(icon)
        except:
            pass

        self.clock = pg.time.Clock()
        self.running = True
        self.state = LOGIN   # начинаем с экрана логина

        # Игровые объекты
        self.board = Board()
        # DQN-агент играет за чёрных
        self.agent = DQNAgent(color='black')

        # Состояние игры
        self.current_color = 'white'
        self.game_over = False
        self.winner = None
        self.selected_piece = None
        self.valid_moves = []
        self.moving_piece = None  # (sr, sc, er, ec, progress, piece_type)
        self.save_message_timer = 0

        # Флаги "раздумья" бота
        self.bot_thinking = False
        self.bot_move_start = 0

        # Для обучения агента
        self.last_state_vec = None
        self.last_action_vec = None

        # Пользователи
        self.users = load_users()
        self.current_user = None

        # Поля ввода для логина/регистрации
        self.login_username = TextInput(330, 300, 300, 50, 'Имя пользователя')
        self.login_password = TextInput(330, 400, 300, 50, 'Пароль', is_password=True)
        self.register_username = TextInput(330, 250, 300, 50, 'Имя пользователя')
        self.register_password = TextInput(330, 350, 300, 50, 'Пароль', is_password=True)
        self.register_confirm = TextInput(330, 450, 300, 50, 'Подтвердите пароль', is_password=True)

        self.login_error = ''
        self.register_error = ''

    def run(self):
        while self.running:
            if self.state == LOGIN:
                self.handle_login()
            elif self.state == REGISTER:
                self.handle_register()
            elif self.state == MENU:
                self.handle_menu()
            elif self.state == RULES:
                self.handle_rules()
            elif self.state == GAME:
                self.handle_game()
            pg.display.flip()
            self.clock.tick(60)

        # перед выходом сохраняем опыт агента
        try:
            self.agent.experience.save()
        except Exception as e:
            print("Ошибка сохранения опыта агента:", e)

        pg.quit()
        sys.exit()

    # ---------- Обработчики состояний ----------
    def handle_login(self):
        login_btn, register_btn = draw_login_screen(
            self.screen, self.login_username, self.login_password, self.login_error
        )

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            self.login_username.handle_event(event)
            if self.login_password.handle_event(event):
                # Enter в поле пароля
                self.try_login()

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if login_btn.collidepoint(event.pos):
                    self.try_login()
                elif register_btn.collidepoint(event.pos):
                    self.state = REGISTER
                    self.register_error = ''
                    self.register_username.text = ''
                    self.register_password.text = ''
                    self.register_confirm.text = ''

    def try_login(self):
        username = self.login_username.get_text()
        password = self.login_password.get_text()
        if username in self.users and self.users[username]['password'] == password:
            self.current_user = username
            self.state = MENU
            self.login_error = ''
        else:
            self.login_error = 'Неверное имя или пароль'

    def handle_register(self):
        reg_btn, back_btn = draw_register_screen(
            self.screen, self.register_username, self.register_password,
            self.register_confirm, self.register_error
        )

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            self.register_username.handle_event(event)
            self.register_password.handle_event(event)
            if self.register_confirm.handle_event(event):
                self.try_register()

            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if reg_btn.collidepoint(event.pos):
                    self.try_register()
                elif back_btn.collidepoint(event.pos):
                    self.state = LOGIN
                    self.login_error = ''
                    self.login_username.text = ''
                    self.login_password.text = ''

    def try_register(self):
        username = self.register_username.get_text()
        password = self.register_password.get_text()
        confirm = self.register_confirm.get_text()

        if not username:
            self.register_error = 'Введите имя пользователя'
        elif username in self.users:
            self.register_error = 'Имя уже занято'
        elif not password:
            self.register_error = 'Введите пароль'
        elif password != confirm:
            self.register_error = 'Пароли не совпадают'
        else:
            self.users[username] = {'password': password}
            save_users(self.users)
            self.current_user = username
            self.state = MENU
            self.register_error = ''

    def handle_menu(self):
        start_rect, rules_rect, load_game_rect, exit_rect, logout_btn = draw_menu(self.screen, self.current_user)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if logout_btn and logout_btn.collidepoint(pos):
                    self.current_user = None
                    self.state = LOGIN
                    self.login_username.text = ''
                    self.login_password.text = ''
                elif start_rect.collidepoint(pos):
                    self.state = GAME
                    self.reset_game()
                elif rules_rect.collidepoint(pos):
                    self.state = RULES
                elif load_game_rect.collidepoint(pos) and os.path.exists(SAVE_FILE):
                    if self.load_game():
                        self.state = GAME
                elif exit_rect.collidepoint(pos):
                    self.running = False

    def handle_rules(self):
        back_rect = draw_rules(self.screen)
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    self.state = MENU

    def handle_game(self):
        # Логика ходов: если не конец игры и нет анимации
        if not self.game_over and not self.moving_piece:
            if self.current_color == 'white':
                self.handle_player_turn()
            else:
                self.handle_bot_turn()

        self.update_animation()
        self.draw_game()

        # Уменьшаем таймер сообщения о сохранении
        if self.save_message_timer > 0:
            self.save_message_timer -= 1

        if self.game_over:
            self.show_game_over()

    # ---------- Игровая логика ----------
    def handle_player_turn(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.state = MENU
                    self.reset_game()
                elif event.key == pg.K_s and (pg.key.get_mods() & pg.KMOD_CTRL):
                    self.save_game()
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                x, y = event.pos
                col = x // CELL_SIZE
                row = y // CELL_SIZE
                if 0 <= row < 6 and 0 <= col < 6:
                    piece = self.board.get_piece(row, col)
                    if piece == 'ww' and self.current_color == 'white':
                        self.selected_piece = (row, col)
                        self.valid_moves = self.board.get_valid_moves(row, col, 'white')
                    elif self.selected_piece and (row, col) in self.valid_moves:
                        self.start_move(self.selected_piece, (row, col))
                        self.selected_piece = None
                        self.valid_moves = []
                    else:
                        self.selected_piece = None
                        self.valid_moves = []

    def handle_bot_turn(self):
        # ход DQN-агента за чёрных
        if not self.bot_thinking:
            self.bot_thinking = True
            self.bot_move_start = time.time()
        elif time.time() - self.bot_move_start > BOT_THINKING_TIME:
            move, state_vec, action_vec = self.agent.select_action(self.board)
            if move:
                self.last_state_vec = state_vec
                self.last_action_vec = action_vec
                self.start_move(move[0], move[1])
            else:
                # нет ходов — считаем, что агент проиграл
                if self.last_state_vec is not None and self.last_action_vec is not None:
                    self.agent.update(self.last_state_vec, self.last_action_vec, -1.0, None, True)
                    self.last_state_vec = None
                    self.last_action_vec = None
                self.check_no_moves()
            self.bot_thinking = False

    def start_move(self, start, end):
        """Начать анимацию перемещения фишки."""
        sr, sc = start
        er, ec = end
        piece = self.board.get_piece(sr, sc)
        # Убираем фишку с доски (она будет нарисована отдельно во время анимации)
        self.board.grid[sr][sc] = '--'
        self.moving_piece = (sr, sc, er, ec, 0.0, piece)
        try:
            pg.mixer.music.load(SOUND_FILE)
            pg.mixer.music.play()
        except:
            pass

    def update_animation(self):
        if self.moving_piece:
            sr, sc, er, ec, progress, piece = self.moving_piece
            progress += 0.1  # скорость анимации
            if progress >= 1.0:
                # Завершение анимации
                self.board.grid[er][ec] = piece
                self.moving_piece = None
                self.winner = self.board.check_win()

                # --- награда для DQN-агента, если ходил чёрный ---
                if piece == 'bb' and self.last_state_vec is not None and self.last_action_vec is not None:
                    # плотная награда: продвижение вверх (чёрные идут к r=0)
                    delta_row = sr - er  # >0 если двинулся вверх
                    reward = 0.1 * delta_row

                    # крупная награда/штраф за конец игры
                    if self.winner in ('black', '_black'):
                        reward += 1.0
                        done = True
                        next_board = None
                    elif self.winner in ('white', '_white'):
                        reward -= 1.0
                        done = True
                        next_board = None
                    else:
                        done = False
                        next_board = self.board

                    self.agent.update(self.last_state_vec, self.last_action_vec, reward, next_board, done)
                    if done:
                        self.last_state_vec = None
                        self.last_action_vec = None
                # --- конец блока награды ---

                if self.winner:
                    self.game_over = True
                else:
                    self.current_color = 'black' if self.current_color == 'white' else 'white'
                    self.check_no_moves()  # проверяем, есть ли ходы у следующего игрока
            else:
                self.moving_piece = (sr, sc, er, ec, progress, piece)

    def check_no_moves(self):
        """Если у текущего игрока нет ходов, игра заканчивается победой соперника."""
        if not self.board.has_any_move(self.current_color):
            # награда агенту за ситуацию "нет ходов"
            if self.last_state_vec is not None and self.last_action_vec is not None:
                if self.current_color == 'white':
                    # белые не могут ходить -> победа чёрных
                    reward = 1.0
                else:
                    # чёрные не могут ходить -> поражение чёрных
                    reward = -1.0
                self.agent.update(self.last_state_vec, self.last_action_vec, reward, None, True)
                self.last_state_vec = None
                self.last_action_vec = None

            self.game_over = True
            self.winner = '_white' if self.current_color == 'white' else '_black'

    def draw_game(self):
        draw_board(self.screen)
        if self.selected_piece and not self.moving_piece and self.current_color == 'white':
            sr, sc = self.selected_piece
            pg.draw.rect(self.screen, RED, (sc*CELL_SIZE, sr*CELL_SIZE, CELL_SIZE, CELL_SIZE), 5)
            draw_valid_moves(self.screen, self.valid_moves)
        draw_pieces(self.screen, self.board, self.moving_piece)
        draw_save_message(self.screen, self.save_message_timer)
        if self.bot_thinking:
            draw_thinking_message(self.screen)

    def show_game_over(self):
        """Показывает диалог окончания игры."""
        if self.winner == 'white':
            msg = 'Победили белые. Начать новую игру?'
        elif self.winner == 'black':
            msg = 'Победили чёрные. Начать новую игру?'
        elif self.winner == '_white':
            msg = 'Нет ходов! Победили белые. Начать новую игру?'
        elif self.winner == '_black':
            msg = 'Нет ходов! Победили чёрные. Начать новую игру?'
        else:
            msg = 'Игра окончена. Начать новую игру?'

        result = pyautogui.confirm(text=msg, title='Игра окончена', buttons=['OK', 'Cancel'])
        if result == 'Cancel':
            self.state = MENU
        self.reset_game()

    def reset_game(self):
        self.board.reset()
        self.current_color = 'white'
        self.game_over = False
        self.winner = None
        self.selected_piece = None
        self.valid_moves = []
        self.moving_piece = None
        self.bot_thinking = False
        self.last_state_vec = None
        self.last_action_vec = None

    def save_game(self):
        """Сохраняет текущее состояние в файл."""
        state = {
            'board': self.board.grid,
            'current_color': self.current_color,
            'game_over': self.game_over,
            'winner': self.winner
        }
        try:
            with open(SAVE_FILE, 'wb') as f:
                pickle.dump(state, f)
            self.save_message_timer = 120  # 2 секунды при 60 fps
        except Exception as e:
            print("Ошибка сохранения:", e)

    def load_game(self):
        """Загружает состояние из файла."""
        if not os.path.exists(SAVE_FILE):
            return False
        try:
            with open(SAVE_FILE, 'rb') as f:
                state = pickle.load(f)
            self.board.grid = state['board']
            self.current_color = state['current_color']
            self.game_over = state['game_over']
            self.winner = state['winner']
            self.selected_piece = None
            self.valid_moves = []
            self.moving_piece = None
            self.bot_thinking = False
            self.last_state_vec = None
            self.last_action_vec = None
            return True
        except Exception as e:
            print("Ошибка загрузки:", e)
            return False
