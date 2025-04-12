import subprocess
import os
import time
from ai_module.fanControl import run_knn_model

def run_shell_command(command):
    """
    Run a shell command and print its output.
    """
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(result.stderr)
    else:
        print(result.stdout)

def clean_docker_and_database():
    """
    Stop and remove all Docker containers, volumes, and reset the PostgreSQL database.
    """
    print("Cleaning Docker containers and resetting the database...")
    
    run_shell_command("docker stop $(docker ps -q)")
    run_shell_command("docker rm $(docker ps -a -q)")

    run_shell_command("docker volume prune -f")
    run_shell_command("docker network prune -f")
    run_shell_command("docker rmi $(docker images -q)")
    run_shell_command("""
        docker exec -it <your_postgres_container_name> psql -U postgres -c "DROP DATABASE IF EXISTS iot_db;"
    """)

    run_shell_command("""
        docker exec -it <your_postgres_container_name> psql -U postgres -c "CREATE DATABASE iot_db;"
    """)

def setup_environment():
    """
    Set up Docker container, virtual environment, install dependencies, and set up the database.
    """
    print("Setting up Docker container and environment...")
    os.chdir('backend')
    run_shell_command("open -a Docker")
    run_shell_command("python -m venv docker_env")
    run_shell_command("source docker_env/bin/activate")
    run_shell_command("docker compose up -d db")
    run_shell_command("pip install -r requirements.txt")
    run_shell_command("python setup_database.py")
    time.sleep(10) 

def main():
    clean_docker_and_database()
    setup_environment()
    model = run_knn_model()

if __name__ == "__main__":
    main()