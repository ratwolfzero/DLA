import numpy as np
import matplotlib.pyplot as plt
from numba import njit
from matplotlib.animation import FuncAnimation
import time
from tqdm import tqdm

# Parameters
radius = 150
grid_size = 2 * radius + 1
num_particles = 15000
max_attempts = 150000
spawn_radius_margin = 20

# Grid setup
dla_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
center = grid_size // 2
dla_grid[center, center] = 0  # Seed in the center

# Figure setup
fig, ax = plt.subplots()
ax.set_xticks([])
ax.set_yticks([])
ax.set_facecolor("black")
fig.patch.set_facecolor("black")

# Colormap
plasma_cmap = plt.get_cmap("plasma")
plasma_cmap.set_bad(color="black")  # NaN areas are black
im = ax.imshow(dla_grid, cmap=plasma_cmap, origin="lower", vmin=0, vmax=grid_size // 2)
cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Euclidean Distance from Center", color="white")
cbar.ax.yaxis.set_tick_params(color="white")
plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")

@njit(fastmath=True)
def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

@njit(fastmath=True)
def is_inside_circle(x, y, radius):
    return x * x + y * y < radius * radius

@njit(fastmath=True)
def random_walk(x, y, grid_size):
    # Precompute movement directions
    direction_table = np.array([
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (-1, 1), (1, -1), (-1, -1)
    ], dtype=np.int8)
    dx, dy = direction_table[np.random.randint(8)]
    return clamp(x + dx, 0, grid_size - 1), clamp(y + dy, 0, grid_size - 1)

@njit
def is_near_aggregated(x, y, grid):
    """Vectorized check for neighboring aggregated pixels."""
    neighbors = grid[max(0, x - 1):min(grid.shape[0], x + 2), 
                     max(0, y - 1):min(grid.shape[1], y + 2)]
    return np.any(neighbors >= 0)

@njit
def compute_spawn_radius(grid, center, margin):
    nonzero_x, nonzero_y = np.where(~np.isnan(grid))
    if len(nonzero_x) == 0:
        return margin
    max_dist_sq = np.max((nonzero_x - center) ** 2 + (nonzero_y - center) ** 2)
    return np.sqrt(max_dist_sq) + margin

@njit(fastmath=True)
def compute_euclidean_distance_sq(x, y, center):
    """Return squared Euclidean distance to avoid unnecessary sqrt calls."""
    return (x - center) ** 2 + (y - center) ** 2
    
@njit(fastmath=True)
def spawn_particle(center, spawn_radius, grid_size):
    """Spawn a particle near the computed radius."""
    angle = np.random.uniform(0, 2 * np.pi)
    x = int(center + spawn_radius * np.cos(angle))
    y = int(center + spawn_radius * np.sin(angle))
    return clamp(x, 0, grid_size - 1), clamp(y, 0, grid_size - 1)

@njit(fastmath=True)
def perform_random_walk(x, y, center, grid, max_attempts):
    """Perform a random walk until aggregation or max attempts reached."""
    attempts = 0
    while attempts < max_attempts:
        if not is_inside_circle(x - center, y - center, grid.shape[0] // 2):
            return None
        if is_near_aggregated(x, y, grid):
            return x, y
        x, y = random_walk(x, y, grid.shape[0])
        attempts += 1
    return None

# Initialize progress bar
pbar = tqdm(total=num_particles)

# Animation update function
def update(frame):
    # Compute dynamic spawn radius
    if not plt.fignum_exists(fig.number):
       pbar.close()
       return

    spawn_radius = compute_spawn_radius(dla_grid, center, spawn_radius_margin)
    spawn_radius = min(spawn_radius, grid_size // 2 - 1)

    # Spawn and simulate a particle
    x, y = spawn_particle(center, spawn_radius, grid_size)
    result = perform_random_walk(x, y, center, dla_grid, max_attempts)

    if result is not None:
        x, y = result
        color = np.sqrt(compute_euclidean_distance_sq(x, y, center))
        dla_grid[x, y] = color  # Update the data matrix

        # Directly update the pixel buffer instead of redrawing the whole image
        im_array = im.get_array()
        im_array[x, y] = color
        im.set_array(im_array)  # Apply the change

    # Update progress bar
    pbar.update(1)

    # Stop animation when complete
    if frame == num_particles - 1:
        pbar.close()
        print(f"Simulation complete! Time taken: {time.time() - start_time:.2f} seconds.")

start_time = time.time()

# Run animation
try:
    ani = FuncAnimation(fig, update, frames=num_particles, interval=1, repeat=False)
    plt.show()
finally:
    pbar.close()

