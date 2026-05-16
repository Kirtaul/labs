import pickle
import os

EXPERIENCE_FILE = "experience.pkl"


class ExperienceBuffer:
    def __init__(self, capacity=100000):
        self.capacity = capacity
        self.buffer = []
        self.position = 0
        self.load()

    def add(self, transition):
        # transition: (state_vec, action_vec, reward, next_state_vec, done)
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.position] = transition
        self.position = (self.position + 1) % self.capacity

    def __len__(self):
        return len(self.buffer)

    def save(self):
        try:
            with open(EXPERIENCE_FILE, "wb") as f:
                pickle.dump(self.buffer, f)
        except Exception as e:
            print("Ошибка сохранения опыта:", e)

    def load(self):
        if not os.path.exists(EXPERIENCE_FILE):
            return
        try:
            with open(EXPERIENCE_FILE, "rb") as f:
                self.buffer = pickle.load(f)
            self.position = len(self.buffer) % self.capacity
        except Exception as e:
            print("Ошибка загрузки опыта:", e)
