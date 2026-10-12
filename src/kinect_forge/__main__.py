import multiprocessing

from kinect_forge.cli import app

if __name__ == "__main__":
    # The GUI runs the Kinect in a spawned child process (sensors/process_sensor.py).
    # In a PyInstaller bundle that child is this executable again, and
    # freeze_support() is what routes it to the worker instead of the CLI.
    multiprocessing.freeze_support()
    app()
