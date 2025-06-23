import time, os, random, sys, math
FIFO_PATH, GRID_SIZE, CASE_SIZE_M, DELAY_BETWEEN_STEPS, SIMULATION_STEPS = "sae24_signal_pipe", 16, 0.5, 1.0, 300
MICROS_POS, K_FACTOR = { 1: (0.25, 0.25), 2: (0.25, 7.75), 3: (7.75, 7.75) }, 1000.0
CHANCE_TO_CONTINUE_DIRECTION = 0.75

def calculate_distance(p1, p2): return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
def calculate_amplitude(src_pos, mic_pos):
    dist = calculate_distance(src_pos, mic_pos)
    return K_FACTOR / (dist**2) if dist > 0.1 else K_FACTOR / (0.1**2)

def grid_to_meters(i, j):
    x = i * CASE_SIZE_M + (CASE_SIZE_M / 2)
    y = j * CASE_SIZE_M + (CASE_SIZE_M / 2)
    return (x, y)

def get_next_human_like_pos(current_i, current_j, last_move):
    straight_moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    potential_next_i, potential_next_j = current_i + last_move[0], current_j + last_move[1]
    is_last_move_valid = (0 <= potential_next_i < GRID_SIZE) and (0 <= potential_next_j < GRID_SIZE)
    if last_move != (0, 0) and is_last_move_valid and random.random() < CHANCE_TO_CONTINUE_DIRECTION:
        next_i, next_j, chosen_move = potential_next_i, potential_next_j, last_move
    else:
        while True:
            chosen_move = random.choice(straight_moves * 4 + diagonal_moves)
            next_i, next_j = current_i + chosen_move[0], current_j + chosen_move[1]
            if (0 <= next_i < GRID_SIZE) and (0 <= next_j < GRID_SIZE): break
    return (next_i, next_j), chosen_move

def main():
    print("Émetteur (Humain 16x16) prêt. En attente...")
    try:
        with open(FIFO_PATH, 'wb') as fifo:
            print("Récepteur connecté. Démarrage...")
            current_i, current_j = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
            last_move = (0, 0)
            for step in range(1, SIMULATION_STEPS + 1):
                pos_meters = grid_to_meters(current_i, current_j)
                amplitudes = [calculate_amplitude(pos_meters, MICROS_POS[k]) for k in sorted(MICROS_POS.keys())]
                data_string = f"{amplitudes[0]:.4f}:{amplitudes[1]:.4f}:{amplitudes[2]:.4f}\n"
                fifo.write(data_string.encode('utf-8'))
                fifo.flush()
                print(f"--> Step {step}/{SIMULATION_STEPS}: Case ({current_i},{current_j}) -> Coords ({pos_meters[0]:.2f}, {pos_meters[1]:.2f})")
                (current_i, current_j), last_move = get_next_human_like_pos(current_i, current_j, last_move)
                time.sleep(DELAY_BETWEEN_STEPS)
    except (FileNotFoundError, BrokenPipeError, KeyboardInterrupt): print("\nArrêt de l'émetteur.")
    finally: print("Simulation terminée."); sys.exit(0)

if __name__ == "__main__":
    main()
