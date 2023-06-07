import matplotlib.pyplot as plt

def on_close(_):
    global closed
    closed = True

def init_graphs():
    global closed
    global fig
    global rotation_ax
    global rotation_r
    global rotation_theta

    closed = False
    fig = plt.figure()
    fig.canvas.mpl_connect('close_event', on_close)

    # Rotation diagram
    rotation_ax = plt.subplot(projection='polar')
    rotation_r = []
    rotation_theta = []

    rotation_ax.grid(True)
    rotation_ax.plot(rotation_theta, rotation_r)

    # Show graphs
    plt.show(block=False)

def update_graphs():
    if closed: return
    fig.canvas.draw()
    fig.canvas.flush_events()

def append_rotation_data(theta: float, r: float):
    global rotation_theta
    global rotation_r
    rotation_theta = rotation_theta[-20:]
    rotation_r = rotation_r[-20:]

    rotation_theta.append(theta)
    rotation_r.append(r)
    
    if closed: return
    rotation_ax.clear()
    rotation_ax.plot(rotation_theta, rotation_r)
