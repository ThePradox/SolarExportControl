# Docker support (Beta)

## Create Image

Docker image must be currently build by yourself.
With the vscode docker extension: Run the included docker build task.

## Run Container

1. Map volume `/app/config` to `yourhostpath`
2. (Optional): Set Environment variable APPARGS to [arguments](../README.md#arguments)
3. Start container
4. Container will exit
5. `yourhostpath` will now contain the `config.json` and `customize.py`
6. Adjust these like described
7. Run again
