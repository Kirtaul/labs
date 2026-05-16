# dqn_agent.py
import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

WEIGHTS_FILE = "dqn_weights.pth"


class DQNNet(nn.Module):
    def __init__(self, input_dim=40, hidden=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1)
        )

    def forward(self, x):
        return self.net(x)


class DQNAgent:
    def __init__(self, lr=1e-3, gamma=0.99, epsilon_start=1.0, epsilon_end=0.05, epsilon_decay=20000):
        self.gamma = gamma
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.step = 0

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.net = DQNNet().to(self.device)
        self.target = DQNNet().to(self.device)
        self.target.load_state_dict(self.net.state_dict())

        self.optim = optim.Adam(self.net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

        self.replay = []
        self.capacity = 200_000
        self.batch = 64

        if os.path.exists(WEIGHTS_FILE):
            self.net.load_state_dict(torch.load(WEIGHTS_FILE, map_location=self.device))
            self.target.load_state_dict(self.net.state_dict())
            print("Загружены веса DQN")

    def save(self):
        torch.save(self.net.state_dict(), WEIGHTS_FILE)
        print("Веса сохранены")

    def epsilon(self):
        return self.epsilon_end + (self.epsilon_start - self.epsilon_end) * np.exp(-self.step / self.epsilon_decay)

    def encode_state(self, board):
        return board.grid.flatten().astype(np.float32)

    def encode_action(self, move):
        (sr, sc), (er, ec) = move
        return np.array([sr/5, sc/5, er/5, ec/5], dtype=np.float32)

    def select_action(self, board):
        moves = board.get_valid_moves(2)  # BLACK
        if not moves:
            return None, None, None

        state_vec = self.encode_state(board)

        if np.random.rand() < self.epsilon():
            move = moves[np.random.randint(len(moves))]
            return move, state_vec, self.encode_action(move)

        q_values = []
        for mv in moves:
            sa = np.concatenate([state_vec, self.encode_action(mv)])
            sa_t = torch.tensor(sa, dtype=torch.float32, device=self.device)
            with torch.no_grad():
                q_values.append(self.net(sa_t).item())

        best = int(np.argmax(q_values))
        move = moves[best]
        return move, state_vec, self.encode_action(move)

    def store(self, s, a, r, next_board_grid, done):
        if len(self.replay) >= self.capacity:
            self.replay.pop(0)
        self.replay.append((s, a, r, next_board_grid, done))

    def train_step(self):
        if len(self.replay) < self.batch:
            return

        batch_idx = np.random.choice(len(self.replay), self.batch, replace=False)
        batch = [self.replay[i] for i in batch_idx]

        s_list, a_list, r_list, ns_grid_list, d_list = zip(*batch)

        # Q(s,a)
        sa_batch = np.stack([np.concatenate([s_list[i], a_list[i]]) for i in range(self.batch)])
        sa_batch = torch.tensor(sa_batch, dtype=torch.float32, device=self.device)
        q_pred = self.net(sa_batch).squeeze(1)

        targets = []
        for i in range(self.batch):
            if d_list[i] or ns_grid_list[i] is None:
                targets.append(r_list[i])
            else:
                # восстановим доску
                from fast_board import FastBoard, BLACK
                b = FastBoard()
                b.grid = ns_grid_list[i].copy()

                next_moves = b.get_valid_moves(BLACK)
                if not next_moves:
                    targets.append(r_list[i])
                else:
                    q_next = []
                    for mv in next_moves:
                        a_vec = self.encode_action(mv)
                        sa = np.concatenate([b.grid.flatten().astype(np.float32), a_vec])
                        sa_t = torch.tensor(sa, dtype=torch.float32, device=self.device)
                        q_next.append(self.target(sa_t).item())
                    targets.append(r_list[i] + self.gamma * max(q_next))

        q_target = torch.tensor(targets, dtype=torch.float32, device=self.device)

        loss = self.loss_fn(q_pred, q_target)
        self.optim.zero_grad()
        loss.backward()
        self.optim.step()

        if self.step % 500 == 0:
            self.target.load_state_dict(self.net.state_dict())
