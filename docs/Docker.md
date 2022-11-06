# Docker support (Beta)

## Create Image

Docker image must be currently build by yourself.
With the vscode docker extension: Run the included docker build task.

## Run Container

1. Map volume `/app/config` to `yourhostpath`
2. Start container
3. Container will exit
4. `yourhostpath` will now contain the `config.json` and `customize.py`
5. Adjust these like described
6. Run again
