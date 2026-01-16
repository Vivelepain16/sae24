import time, os, random, sys, math

# Configuration constants
FIFO_PATH = "sae24_signal_pipe"
GRID_SIZE = 16                   # 16x16 grid room
CASE_SIZE_M = 0.5                # 0.5 meters
DELAY_BETWEEN_STEPS = 1.0
SIMULATION_STEPS = 300

# Microphone positions (meters)
MICROS_POS = { 
    1: (0.25, 0.25),    # Bottom-left corner
    2: (0.25, 7.75),    # Top-left corner  
    3: (7.75, 7.75)     # Top-right corner
}

K_FACTOR = 1000.0                     # Amplitude scaling factor
CHANCE_TO_CONTINUE_DIRECTION = 0.75   # 75% chance to continue straight

def calculate_distance(p1, p2):
    # Calculate Euclidean distance between two points
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_amplitude(src_pos, mic_pos):
    # Calculate signal amplitude using inverse square law
    dist = calculate_distance(src_pos, mic_pos)
    # Avoid division by zero with minimum distance of 0.1m
    return K_FACTOR / (dist**2) if dist > 0.1 else K_FACTOR / (0.1**2)

def grid_to_meters(i, j):
    # Convert grid coordinates to real-world meters
    # Centers position in the middle of each grid cell
    x = i * CASE_SIZE_M + (CASE_SIZE_M / 2)
    y = j * CASE_SIZE_M + (CASE_SIZE_M / 2)
    return (x, y)

def get_next_human_like_pos(current_i, current_j, last_move):
    
    # Define possible movement directions
    straight_moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]      # 4 cardinal directions
    diagonal_moves = [(1, 1), (-1, 1), (1, -1), (-1, -1)]    # 4 diagonal directions
    
    # Calculate potential next position if continuing current direction
    potential_next_i, potential_next_j = current_i + last_move[0], current_j + last_move[1]
    is_last_move_valid = (0 <= potential_next_i < GRID_SIZE) and (0 <= potential_next_j < GRID_SIZE)
    
    # 75% chance to continue in same direction if valid
    if last_move != (0, 0) and is_last_move_valid and random.random() < CHANCE_TO_CONTINUE_DIRECTION:
        next_i, next_j, chosen_move = potential_next_i, potential_next_j, last_move
    else:
        # Choose random direction
        while True:
            # Weight straight moves 4x more than diagonal moves
            chosen_move = random.choice(straight_moves * 4 + diagonal_moves)
            next_i, next_j = current_i + chosen_move[0], current_j + chosen_move[1]
            # Ensure new position is within grid boundaries
            if (0 <= next_i < GRID_SIZE) and (0 <= next_j < GRID_SIZE): 
                break
    
    return (next_i, next_j), chosen_move

def main():
    # Main simulation loop
    print("Émetteur (Humain 16x16) prêt. En attente...")
    
    try:
        # Open named pipe for data transmission
        with open(FIFO_PATH, 'wb') as fifo:
            print("Récepteur connecté. Démarrage...")
            
            # Initialize random starting position
            current_i, current_j = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
            last_move = (0, 0)
            
            # Main simulation loop
            for step in range(1, SIMULATION_STEPS + 1):
                # Convert grid position to real-world coordinates
                pos_meters = grid_to_meters(current_i, current_j)
                
                # Calculate signal amplitudes for each microphone
                amplitudes = [calculate_amplitude(pos_meters, MICROS_POS[k]) for k in sorted(MICROS_POS.keys())]
                
                # Format data as colon-separated string
                data_string = f"{amplitudes[0]:.4f}:{amplitudes[1]:.4f}:{amplitudes[2]:.4f}\n"
                
                # Send data through pipe
                fifo.write(data_string.encode('utf-8'))
                fifo.flush()
                
                # Debug output showing current step and position
                print(f"--> Step {step}/{SIMULATION_STEPS}: Case ({current_i},{current_j}) -> Coords ({pos_meters[0]:.2f}, {pos_meters[1]:.2f})")
                
                # Calculate next position with human-like movement
                (current_i, current_j), last_move = get_next_human_like_pos(current_i, current_j, last_move)
                
                # Wait before next step
                time.sleep(DELAY_BETWEEN_STEPS)
                
    except (FileNotFoundError, BrokenPipeError, KeyboardInterrupt): 
        print("\nArrêt de l'émetteur.")
    finally: 
        print("Simulation terminée.")
        sys.exit(0)

if __name__ == "__main__":
    main()
