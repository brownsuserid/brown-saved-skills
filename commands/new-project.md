# Set up a new Development Project
To set up a new development project, follow the steps below in sequence.  
Complete all steps in their exact order and nothing more.

Create a to-do list for yourself for these items in sequence:
1. Ask the user to describe the project they are starting and whether it will be Python, Node or something esle.
2. Create a new private github repo named {$ARGUMENTS}, with a "master" and an "initial-code" branch.  Master is the default.
3. If this is a Python Project:
   a. Initialize UV (already installed) which will also create a new virtual environment (uv init)
   b. Use uv to add and install these packages {$ARGUMENTS}  
   c. Install pytest (with coverage), ruff and bandit[toml] as dev dependencies using uv
4. Create an initial README.md in the root of the project
5. Create an initial placeholder Roadmap.md in a /plans folder where we will keep our detailed roadmap items for this project.
6. Create a /docs and /docs/architecture folder for storing documentation
7. Create initial .gitignore (including typical python ignores)
8. Create an ultra-concise initial claude.md for this project (noting use of UV if this is a python project)
9. Commit locally into ths "initial-code" branch