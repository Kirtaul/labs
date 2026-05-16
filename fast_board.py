# fast_board.py
import numpy as np

EMPTY = 0
WHITE = 1
BLACK = 2

class FastBoard:
    def __init__(self):
        self.grid = np.zeros((6, 6), dtype=np.int8)

    def reset(self):
        self.grid[:] = 0
        # белые слева
        for r in range(6):
            self.grid[r, 0] = WHITE
        # чёрные снизу
        for c in range(6):
            self.grid[5, c] = BLACK

    def copy(self):
        b = FastBoard()
        b.grid = self.grid.copy()
        return b

    def get_valid_moves(self, color):
        moves = []
        if color == WHITE:
            for r in range(6):
                if self.grid[r, 0] == WHITE:
                    # вправо
                    if self.grid[r, 1] == EMPTY:
                        moves.append(((r, 0), (r, 1)))
                for c in range(1, 6):
                    if self.grid[r, c] == WHITE:
                        # вправо
                        if c < 5 and self.grid[r, c+1] == EMPTY:
                            moves.append(((r, c), (r, c+1)))
                        # вверх
                        if r > 0 and self.grid[r-1, c] == EMPTY:
                            moves.append(((r, c), (r-1, c)))
                        # вниз
                        if r < 5 and self.grid[r+1, c] == EMPTY:
                            moves.append(((r, c), (r+1, c)))

        else:  # BLACK
            for c in range(6):
                if self.grid[5, c] == BLACK:
                    # вверх
                    if self.grid[4, c] == EMPTY:
                        moves.append(((5, c), (4, c)))
                for r in range(0, 5):
                    if self.grid[r, c] == BLACK:
                        # вверх
                        if r > 0 and self.grid[r-1, c] == EMPTY:
                            moves.append(((r, c), (r-1, c)))
                        # вправо
                        if c < 5 and self.grid[r, c+1] == EMPTY:
                            moves.append(((r, c), (r, c+1)))
                        # влево
                        if c > 0 and self.grid[r, c-1] == EMPTY:
                            moves.append(((r, c), (r, c-1)))

        return moves

    def move_piece(self, start, end):
        sr, sc = start
        er, ec = end
        piece = self.grid[sr, sc]
        self.grid[sr, sc] = EMPTY
        self.grid[er, ec] = piece

    def check_win(self):
        # белые выигрывают, если дошли до правой границы
        if np.any(self.grid[:, 5] == WHITE):
            return WHITE
        # чёрные выигрывают, если дошли до верхней границы
        if np.any(self.grid[0, :] == BLACK):
            return BLACK
        return None
