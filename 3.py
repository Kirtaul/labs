# selftrain_fast.py
from fast_board import FastBoard, WHITE, BLACK
from dqn_agent import DQNAgent
import numpy as np


def play_episode(agent: DQNAgent, max_steps=200):
    board = FastBoard()
    board.reset()
    done = False
    steps = 0

    last_s = None
    last_a = None

    while not done and steps < max_steps:
        steps += 1

        # --- ход белых (случайный) ---
        white_moves = board.get_valid_moves(WHITE)
        if not white_moves:
            if last_s is not None:
                agent.store(last_s, last_a, +1.0, None, True)
            break

        mv = white_moves[np.random.randint(len(white_moves))]
        board.move_piece(mv[0], mv[1])

        if board.check_win() == WHITE:
            if last_s is not None:
                agent.store(last_s, last_a, -1.0, None, True)
            break

        # --- ход чёрных (DQN) ---
        move, s_vec, a_vec = agent.select_action(board)
        if move is None:
            if last_s is not None:
                agent.store(last_s, last_a, -1.0, None, True)
            break

        (sr, sc), (er, ec) = move
        board.move_piece(move[0], move[1])

        reward = 0.1 * (sr - er)
        winner = board.check_win()

        if winner == BLACK:
            reward += 1.0
            agent.store(s_vec, a_vec, reward, None, True)
            break
        else:
            agent.store(s_vec, a_vec, reward, board.grid.copy(), False)

        last_s = s_vec
        last_a = a_vec

        agent.train_step()
        agent.step += 1


def main():
    agent = DQNAgent()

    EPISODES = 20000
    for ep in range(1, EPISODES + 1):
        play_episode(agent)
        if ep % 500 == 0:
            print("Эпизод", ep)
            agent.save()

    agent.save()


if __name__ == "__main__":
    main()
